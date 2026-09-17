# sqli-second-order — Second-order SQL injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask + SQLite lab for second-order SQL injection. The app has two flows. Registration — `POST /register` — stores a username through a **safe, parameterized** `INSERT`, so a SQL payload in the username is written as a literal value and nothing happens. Later, an authenticated change-password flow — `POST /change-password` — re-reads that username from the database and **concatenates it raw** into a second query, an `UPDATE`. So a payload username planted at registration lies dormant in the table and detonates in the *second* flow: it rewrites which row the `UPDATE` hits, letting an attacker change another account's password.

The lesson is that parameterizing the input at the **entry point** does not protect you if you de-parameterize it at the **point of use**. The registration query was never the problem — it is safe. The bug is that a value read back from the database is trusted just because it came from the database, and **every read from the database is untrusted input again**. The fix is not to sanitize or validate the username at registration — it is to **parameterize the second query too**, so the re-read value is bound as data and can never become SQL syntax.

> **Theory primer:** Read [PortSwigger: Second-order SQL injection](https://portswigger.net/web-security/sql-injection#second-order-sql-injection)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — embedded SQLite, writable and ephemeral

Like the other SQL injection atoms (`sqli-union-basic` and its blind siblings), this atom embeds SQLite as a file inside the process — there is no external datastore, and each side (`vulnerable` and `fixed`) runs as a single container with its own `lab.db`, seeded on boot. One difference matters: those atoms are read-only (`SELECT`), but this one **writes** — `POST /register` does an `INSERT` and `POST /change-password` does an `UPDATE`. The database is **ephemeral**: it lives inside the container with no persistent volume. Because the exploit mutates the database (it changes another account's password), **to run the attack again from scratch, tear the atom down and back up** — `./atom down sqli-second-order && ./atom up sqli-second-order` recreates the container and reseeds a clean database; otherwise the seeded baseline no longer holds. The apps depend only on `Flask`; `sqlite3` is in the standard library, and the session cookie uses Flask's built-in signing.

## API only — no HTML, no browser

This atom has no web UI: no templates, no landing page, every response is JSON. You drive it entirely from **Burp Suite (Repeater)** or `curl`, and the proof is a login response — nothing executes in a browser. `WALKTHROUGH.md` works exclusively from Burp.

## Run

From the repo root:

```bash
./atom up sqli-second-order
```

- Vulnerable API: `http://127.0.0.1:8029`
- Fixed API: `http://127.0.0.1:8129`

`GET /` returns a warning banner; the flows are `POST /register`, `POST /login` and `POST /change-password` (see `WALKTHROUGH.md`). Stop with `./atom down sqli-second-order`. If you prefer raw Docker: `cd atoms/A03-injection/sqli-second-order && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8129 serves the same three flows against the same seed data. It changes one thing — the `UPDATE` in `POST /change-password` binds the re-read username as a parameter (`WHERE username = ?`) instead of concatenating it — and nothing else. Replay the walkthrough against it: registering the `admin'--` username and running change-password now updates only the attacker's *own* row, so logging in as `admin` with the attacker's new password returns `401`, and `admin`'s original password still works.
