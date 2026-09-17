# nosql-injection-mongo — NoSQL Injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask + MongoDB lab for NoSQL injection. A JSON login endpoint — `POST /login` — takes a `username` and `password` and builds a MongoDB query to find the matching user: `find_one({"username": username, "password": password})`. The catch is that a MongoDB query is not a string of SQL — it is a **document**, an object whose values can be plain scalars *or* operators. The endpoint drops whatever the client sent straight into that document, so if `password` arrives as the object `{"$ne": null}` ("not equal to null") instead of a string, it becomes a Mongo **operator**: the filter now matches any user with a password, and you log in as `admin` without ever knowing it.

The lesson is that the root cause is **type confusion**, not string syntax. The app expected a scalar (a string) and got an object, and the driver passed that object through faithfully as query structure. This is why the SQL injection reflex — "it's injection, just parameterize it" — misses here: `pymongo` never concatenates a string, so it is *already* the moral equivalent of a parameterized query, and it is still vulnerable. The fix is not to escape or parameterize; it is to **force the type** — reject anything that isn't a string before it can reach the query.

> **Theory primer:** Read [PortSwigger: NoSQL injection](https://portswigger.net/web-security/nosql-injection)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — a real MongoDB

Unlike the SQL injection atoms (`sqli-union-basic` and its blind siblings), which embed SQLite as a file inside the process, this atom needs a real database *server*: MongoDB. So the lab runs **three containers** — one shared `mongo`, plus `vulnerable` and `fixed`, both reading the same seeded data. The `mongo` service has **no host port**: it is reachable only on the compose's internal network (`mongodb://mongo:27017/`), never published to your machine — only the two apps bind to `127.0.0.1`. The `users` collection is seeded on first boot with two fake users (`admin`, `alice`) whose passwords are stored in plaintext — a lab simplification; password hashing is orthogonal to the NoSQL injection fix (see `DIFF.md`).

## API only — no HTML, no browser

This atom has no web UI: no templates, no landing page, every response is JSON. That is deliberate — the attack vector *is* the JSON request body. A MongoDB operator like `{"$ne": null}` is a nested object, and only JSON carries a nested object into the app; an HTML form or a query string would arrive as a plain string (Flask's `request.form`/`request.args` never build a nested object — the `password[$ne]=` trick is Express/PHP behavior, not Flask). So you drive this atom entirely from **Burp Suite (Repeater)** or `curl`; there is no browser track, and the proof is the login response itself. `WALKTHROUGH.md` works exclusively from Burp.

## Run

From the repo root:

```bash
./atom up nosql-injection-mongo
```

- Vulnerable API: `http://127.0.0.1:8022`
- Fixed API: `http://127.0.0.1:8122`

`GET /` returns a warning banner; the entry point is `POST /login` (see `WALKTHROUGH.md`). The `mongo` container is never published — only the two apps are. Stop with `./atom down nosql-injection-mongo`. If you prefer raw Docker: `cd atoms/A03-injection/nosql-injection-mongo && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8122 serves the same login against the same seeded MongoDB. It adds one guard — `username` and `password` must be strings, or the request is rejected with **400** — and changes nothing else. Replay the walkthrough against it: real string credentials still log in with `200`, and the `{"$ne": null}` payload that bypassed the vulnerable app now returns `400`, because an object can never reach the query filter.
