# idor-numeric-id — Insecure Direct Object Reference (numeric ID)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic IDOR. The app serves private notes through `GET /notes/<id>`. A simulated `X-User-ID` header tells the app which user is "logged in", but the view function never checks whether the requested note belongs to that user — anyone can read anyone else's note by changing a single digit in the URL.

This is the first atom in the project that is **not input-driven**. There is no malicious payload to craft — the exploit is literally counting `1, 2, 3`. The vulnerability lives in code that *isn't there* (the missing ownership check), not in code that mishandles a string.

> **Theory primer:** Read [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — no database

Unlike `sqli-union-basic`, this atom keeps its data in a plain Python list rather than SQLite. IDOR doesn't depend on the storage layer: the bug is a missing authorization check above whichever store you use. The surface is kept minimal so the missing line is obvious. The storage choice in each atom follows the surface of the bug — not the other way around.

## Authentication, simulated

Real authentication (login forms, sessions, password hashing) is out of scope here — the `session-fixation` atom (15) is the right place for that ceremony. This lab fakes "who is logged in" with a single header: `X-User-ID`. If absent, the app defaults to `1` (alice) so the UI works without you setting anything up. Three users are seeded:

- `1` — alice — note titled "Banking"
- `2` — bob — note titled "Meeting"
- `3` — carol — note titled "Card"

## Run

From the repo root:

```bash
./atom up idor-numeric-id
```

- Vulnerable app: <http://127.0.0.1:8003/>
- Fixed app: <http://127.0.0.1:8103/>

Stop with `./atom down idor-numeric-id`. If you prefer raw Docker: `cd atoms/A01-broken-access-control/idor-numeric-id && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary) and browser (secondary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8103 serves the same feature against the same seed notes. Repeat every request from `WALKTHROUGH.md` against it — your own note (`/notes/1` with `X-User-ID: 1`) returns 200, but any cross-user combination (e.g. `/notes/2` while authenticated as `1`) returns **403 Forbidden** instead of leaking content.
