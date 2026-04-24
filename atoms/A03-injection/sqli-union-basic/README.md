# sqli-union-basic — UNION-based SQL Injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic UNION-based SQL injection. A "user profile lookup" endpoint concatenates the `username` query parameter into a SQL string, letting an attacker append a `UNION SELECT` and exfiltrate rows from a sibling `secrets` table (password hashes, API keys) that the feature never intended to expose.

## Run

From the repo root:

```bash
./atom up sqli-union-basic
```

- Vulnerable app: <http://127.0.0.1:8001/>
- Fixed app: <http://127.0.0.1:8101/>

Stop with `./atom down sqli-union-basic`. If you prefer raw Docker: `cd atoms/A03-injection/sqli-union-basic && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary) and browser (secondary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8101 serves the same feature against the same seed data. Run every payload from `WALKTHROUGH.md` against it — each one should return either an empty table or Alice's single legitimate row, never the exfiltrated secrets.
