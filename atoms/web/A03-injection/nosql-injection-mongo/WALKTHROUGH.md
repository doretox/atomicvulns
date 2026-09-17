# Walkthrough — nosql-injection-mongo

## 1. Context

The app is a JSON login API. You `POST /login` a `username` and `password`, and the server looks the user up in MongoDB with a single query — `find_one({"username": username, "password": password})`. If a document matches, you're authenticated.

The detail that makes it exploitable is what a MongoDB query *is*. In SQL a query is a string of text. In MongoDB a query is a **document** — an object of field/value pairs — and a value can be either a plain **scalar** (a string or number: "this field equals this value") or an **operator** (a special `$`-prefixed key like `$ne`, "not equal", that describes *how* to match rather than a value to match). This atom is **NoSQL injection**: interfering with the query an app sends to a NoSQL database. On the OWASP Top 10 it sits under **A03 — Injection**, the same category as SQL injection — untrusted input reaching a query interpreter that treats it as structure, not inert data. The vulnerable endpoint drops your raw input straight into the query document, so you can smuggle an operator into the slot where it expected a string.

This atom is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater**; the same requests run under `curl`. The proof is the login response itself — nothing executes in a browser. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The login view is short:

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    # VULNERABLE: username/password go straight into the query filter...
    user = users.find_one({"username": username, "password": password})
    if user:
        return jsonify({"authenticated": True, "user": user["username"]})
    return jsonify({"authenticated": False}), 401
```

`request.get_json()` parses the body into a Python `dict`, and JSON nests — so `password` is whatever the client put there: a string *or* a nested object. Both values go straight into the filter document handed to `find_one`. Ask the auditor's question: *this `password` I control lands inside a query filter — what if I make it an object with an operator instead of a string?* Then the object becomes query structure.

Notice there's nothing to `grep` for the way you'd grep an f-string SQL concatenation — `pymongo` never builds a string of query text. You catch this by reading each query whose filter takes request input and asking "is this value forced to be a scalar?" Here it isn't.

## 3. Exploitation via Burp Suite

Point Burp at the vulnerable API on `127.0.0.1:8022` and work from Repeater. (The seeded passwords are visible in `mongo/mongo-init.js`, so the baseline can use a real one; the attack won't need it.)

### Baseline — the login working normally

A real string credential authenticates:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8022
Content-Type: application/json

{"username": "admin", "password": "s3cr3t-admin-pw"}
```

Response — `200`:

```json
{"authenticated": true, "user": "admin"}
```

The feature works, with strings. Hold onto that shape: a string in `password` means "the password field equals this exact value."

### Step 1 — Swap the string for an operator

Instead of the string password, send an **object** carrying an operator — `{"$ne": null}`, "not equal to null." `$ne` doesn't match a literal value; it matches any document whose `password` is anything other than `null`. Since every seeded user has a (non-null) password, it matches them all — and you pin the username to `admin`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8022
Content-Type: application/json

{"username": "admin", "password": {"$ne": null}}
```

Response — `200`:

```json
{"authenticated": true, "user": "admin"}
```

You logged in as `admin` without the password. The filter the app actually ran was `{"username": "admin", "password": {"$ne": null}}` — you pinned the username to `admin` and told Mongo "any password but null," and the admin document matched. Nothing here is a string trick; the payload is a perfectly valid JSON object. (`{"$gt": ""}` — "greater than the empty string" — logs you in the same way, for the same reason.)

The lab is isolated — the apps bind to `127.0.0.1` and the `mongo` container has no host port at all — and the payload is benign: it only subverts a lookup (`find_one`) to prove the bypass, writing and dropping nothing. The seeded users are fake.

## 4. What the vuln is NOT

The exploit is quick, and it can steer you toward the wrong fix. Kill the wrong conclusions.

**It is not SQL injection.** There is no quote to break out of, no `UNION`, no `OR 1=1`, no command string at all — the payload is a valid JSON object. Prove it: send the classic SQL payload as the *string* password —

```
POST /login HTTP/1.1
Host: 127.0.0.1:8022
Content-Type: application/json

{"username": "admin", "password": "' OR 1=1 --"}
```

— and it fails:

```json
{"authenticated": false}
```

`401`. There is no SQL and no concatenation for it to break; `find_one` just looks for a user whose password is literally the string `' OR 1=1 --`, finds none, and rejects you. What logs you in is the *object*, never a string.

**It is not a bug about escaping.** There is no dangerous character inside a string to escape — the vector is the *type* of the value (an object), not a metacharacter within a value.

**It is not missing parameterization.** This is the trap for anyone who knows SQLi. `pymongo` never splices your input into a string of query text; it passes the `dict` to the server *as a document* — which is exactly what "parameterized" means in the SQL world: data kept separate from command. And it is *still* vulnerable, because the injection isn't syntax inside a string — it's a value that changed type, from the scalar the app expected to an object the driver faithfully forwards as an operator. The parameterization that closes SQL injection has no analog that catches this.

What it *is*: **type confusion.** The app expected a scalar (a string) and got an object, and the object became query structure. The only fix is to force the type — reject anything that isn't a string before it reaches the query (§6).

## 5. Impact

Authentication bypass — account takeover. You logged in as `admin` without a credential, which grants everything `admin` can reach in the victim's context. That is the same ceiling as an auth bypass through SQL injection (`sqli-union-basic` and its blind siblings subvert a SQL query to the same end; this subverts a Mongo query), reached by a different mechanism. It is not RCE here — MongoDB's JavaScript operators (`$where`) can escalate NoSQL injection further in some apps, but this atom models the auth-bypass face and claims no more.

## 6. Why the fix works

Run the same requests against the fixed API on port **8122** (see [`DIFF.md`](./DIFF.md) for the change).

The `{"$ne": null}` payload is rejected:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8122
Content-Type: application/json

{"username": "admin", "password": {"$ne": null}}
```

Response — `400`:

```json
{"error": "username and password must be strings"}
```

The fixed view checks the type before the query: `username` and `password` must be `str`, or it returns `400`. An object never reaches `find_one`, so it can never become an operator.

And the feature is untouched: the real string credential (`{"username": "admin", "password": "s3cr3t-admin-pw"}`) still returns `200` on 8122, exactly as on the vulnerable app. The feature is identical; only the object payload separates the two. The fix forces the *type* — it doesn't escape, doesn't parameterize (`pymongo` already does), and doesn't blocklist `$`-keys. [`DIFF.md`](./DIFF.md) walks through why each of those alternatives misses.
