# sqli-blind-boolean — Blind SQL Injection (boolean-based)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for boolean-based blind SQL injection. A login endpoint concatenates the `username` and `password` POST fields into a SQL string. The response body never echoes data back — it only renders one of two pages, `Welcome, <user>!` or `Invalid credentials.` — but those two states form a binary oracle. By injecting conditions that flip the oracle, the attacker extracts data one bit at a time, character by character, until alice's stored password (`wonderland`) is recovered without it ever appearing in a response.

> **Theory primer:** Read [PortSwigger: Blind SQL injection](https://portswigger.net/web-security/sql-injection/blind)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up sqli-blind-boolean
```

- Vulnerable app: <http://127.0.0.1:8006/>
- Fixed app: <http://127.0.0.1:8106/>

Stop with `./atom down sqli-blind-boolean`. If you prefer raw Docker: `cd atoms/A03-injection/sqli-blind-boolean && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary) and browser (secondary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8106 serves the same login feature against the same seed users. It still returns `Welcome, <user>!` for correct credentials and `Invalid credentials.` for everything else — that asymmetry is legitimate login behavior, not the bug. Run every payload from `WALKTHROUGH.md` against it: each one returns `Invalid credentials.`, including the Step 1 login bypass. The attacker has lost control over the oracle even though the oracle is still there.
