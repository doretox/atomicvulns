# sqli-blind-time — Blind SQL Injection (time-based)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for time-based blind SQL injection. A login endpoint concatenates the `username` and `password` POST fields into a SQL string — but the response is *always the same page* (`Login attempt processed.`), whether the credentials are valid or not. There is no body oracle: a developer flattened the two messages to stop username enumeration, which killed the boolean-based channel but left the injection in place. The only thing that still varies is **time**. By injecting a condition that triggers an expensive SQLite computation *only when it is true*, the attacker reads alice's stored password (`wonderland`) one character at a time off the response latency — without it, or any response difference but the clock, ever appearing on the page.

> **Theory primer:** Read [PortSwigger: Blind SQL injection](https://portswigger.net/web-security/sql-injection/blind)
> before working through this atom — in particular the section on
> triggering time delays. The atoms in this repo show *how* a
> vulnerability happens in code; the Academy explains *what* it is
> and why it matters.

## Run

From the repo root:

```bash
./atom up sqli-blind-time
```

- Vulnerable app: <http://127.0.0.1:8007/>
- Fixed app: <http://127.0.0.1:8107/>

Stop with `./atom down sqli-blind-time`. If you prefer raw Docker: `cd atoms/A03-injection/sqli-blind-time && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (Repeater → Intruder), reading the latency column as the oracle.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8107 serves the same login feature against the same seed users, and keeps the same uniform `Login attempt processed.` response — that flattened message was legitimate anti-enumeration, not the bug. It uses a parameterized query, so every payload from `WALKTHROUGH.md` returns instantly, including the unconditional Step 1 probe: with no controllable delay, the timing channel is gone. Same root cause and same fix as [`sqli-union-basic`](../sqli-union-basic/) and [`sqli-blind-boolean`](../sqli-blind-boolean/) — only what the attacker can observe changed.
