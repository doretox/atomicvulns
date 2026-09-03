# race-condition-basic — Time-of-check to time-of-use (TOCTOU) race condition

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask + PostgreSQL lab for a flaw that hides in ordinary business logic: an account API whose `POST /withdraw` **reads** your balance, **checks** in Python that it covers the amount, and then **writes** the debit — as three separate steps. Between the check and the write there is a sliver of time. Fire one withdrawal at a time and nothing goes wrong. Fire twenty withdrawals of the whole balance *at the same instant* and all twenty read the full balance, all twenty pass the check before any of them writes, and all twenty debit. You withdraw twenty times money that only covered one withdrawal, and the balance runs negative.

Nothing about the attacker's request is malicious. It is **byte-for-byte identical** to a legitimate withdrawal — a normal amount the balance can cover. The only difference between ordinary use and the attack is **concurrency**: many copies of the same request arriving together. This is a **race condition** of the **time-of-check to time-of-use (TOCTOU)** kind — the truth you checked (the balance covers it) is stale by the moment you act on it (you debit), because another request changed the balance in the gap between the two. The fix is *not* "check again" — a second check has the same gap. It is to make the check-and-act **atomic**: let the database decide *and* write in a single statement it serializes per row.

> **Theory primer:** Read [PortSwigger: Race conditions](https://portswigger.net/web-security/race-conditions)
> before working through this atom — it covers time-of-check to time-of-use flaws,
> the "limit overrun" pattern (its own example is withdrawing cash in excess of an
> account balance, exactly this lab), and the single-packet attack you use to win
> the race. The atoms in this repo show *how* a vulnerability happens in code; the
> Academy explains *what* it is and why it matters.

This atom sits in **A04 — Insecure Design**. The bug is not input turning into code (that is injection — and here there is no malicious input at all), nor a missing owner check, nor a weak crypto primitive. It is a defect in the **design of the flow**: "decide from a value, then act on that value" was built as two separate steps without guaranteeing they happen indivisibly, so concurrent requests slip between them and break a business invariant (never withdraw past the balance). That absence of malicious input is what sets this atom apart from every earlier one. In [`sqli-union-basic`](../../A03-injection/sqli-union-basic/) and the other injection atoms the request carries a payload; in [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) it carries a swapped number. Here the request carries **nothing different** — only its timing does.

## Stack note — a real PostgreSQL, and threads

The lab runs **three containers**: one shared `db` (PostgreSQL) plus `vulnerable` and `fixed`, both reading the same seeded account. The `db` service has **no host port** — it is reachable only on the compose's internal network (`db:5432`), never published to your machine; only the two apps bind to `127.0.0.1`. The `accounts` table is seeded on first boot with one fake account (`id = 1`, `balance = 100`) — lab data. Two choices make the race faithful and reproducible: the datastore is **PostgreSQL, not SQLite** (SQLite serializes writes behind a whole-database lock, which would *hide* the race — Postgres gives real per-row concurrency), and Flask runs **multi-threaded** (`threaded=True`), because genuine concurrency is a prerequisite for a race to exist at all. Each request opens its own database connection, so twenty simultaneous withdrawals become twenty concurrent database sessions.

## The proof is a number — and you need Burp's Turbo Intruder

You drive this atom from **Burp**, but with one tool beyond the usual: **Turbo Intruder** (a free extension from the BApp Store). The attack is concurrency, and neither Repeater (one request at a time) nor the standard Intruder wins a race reliably — the network *serializes* the requests, so the first debit lands before the second even checks. Turbo Intruder's **single-packet attack** makes N requests arrive together, neutralizing that jitter. This is a deliberate, declared departure from the repo's usual "vanilla Burp" track, and it is necessary: a race only reproduces with genuinely simultaneous requests. The proof is a single unambiguous **number** — the final balance, negative on the vulnerable app and correct on the fixed one.

## Run

From the repo root:

```bash
./atom up race-condition-basic
```

- Vulnerable API: `http://127.0.0.1:8035`
- Fixed API: `http://127.0.0.1:8135`

`GET /` returns a warning banner; the entry point is `POST /withdraw` with a JSON body `{"amount": 100}`, `POST /reset` restores the balance to 100 between attempts, and `GET /balance` shows the current number. The `db` container is never published — only the two apps are. Stop with `./atom down race-condition-basic`. If you prefer raw Docker: `cd atoms/A04-insecure-design/race-condition-basic && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step by step: confirm the guard works one request at a time, then fire a burst of identical withdrawals with Turbo Intruder and watch the balance go to `-1900`. Then the same burst against the fixed app lets exactly one through.
2. [`DIFF.md`](./DIFF.md) — the one-operation diff between `vulnerable/` and `fixed/`, and why "check again," an application-level lock, and `SERIALIZABLE` are the wrong, partial, or heavier answers next to the conditional `UPDATE`.

## Fixed version

The patched app on port 8135 serves the same withdrawal against the same seeded database. It changes one thing: the debit becomes a single **conditional `UPDATE`** — `UPDATE accounts SET balance = balance - :amount WHERE id = 1 AND balance >= :amount` — and it checks how many rows changed (`rowcount`): 1 means it debited, 0 means the balance did not cover it (`409`). The condition and the write are now the *same* statement, which Postgres serializes per row: it locks the row, re-checks `balance >= amount` against the current value, and writes, with no gap for another request to slip into. There is no separate read, so there is no sleep. Replay the walkthrough against it: a single withdrawal still works identically, but the concurrent burst now lets **exactly one** withdrawal succeed and the balance lands at `0`.
