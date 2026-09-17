# logging-failures-demo — Missing security logging of authentication failures

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for the one vulnerability class where **the flaw is something that does *not* happen**. The app is a tiny login API: `POST /login` takes an email and a password, checks them against a stored password hash, and answers `200 {"authenticated": true}` or `401 {"authenticated": false}`. The login is correct — a parameterized query, properly hashed passwords, a clean `401` for a wrong password. Now point a **brute-force** at it — an attacker hammering one account with password after password. Each failed attempt *is* a **security event** (something a security team needs to know about), but on the vulnerable side the failure path records **nothing** security-relevant. All that survives is the web server's generic HTTP **access log** — one line per request (method, path, status, source IP), which captures the *transport*, not the security meaning: it carries no target account (the email is in the body, not the URL), never labels the `401` an authentication failure, and never aggregates. Twenty break-in attempts look exactly like twenty users mistyping. The attack happens and nobody sees it.

This is **A09 — Security Logging and Monitoring Failures**: the category about being able to *know* an attack happened — to detect it, respond to it, and reconstruct it afterward. Unlike every other atom in this repo, the proof is **not something appearing** — no marker file, no leaked data, no account takeover. It is the **contrast between two logs**: run the *same* brute-force burst against both sides and compare `docker compose logs`. The vulnerable side is **blind** (only the generic access log); the fixed side adds a **structured security log** line for every failure — legible to a human and parseable by a machine — and a clear **brute-force WARNING** once the failures cross a threshold. The fix is to *generate the security log that is missing*: it logs the **fact** of each failure (the event, the target account, the source IP, the timestamp) and **never the secret** (the attempted password stays out of the log). It is **not** rate-limiting — the fixed side **detects and records** the attack, it does not **block** it (every attempt still returns `401`). A09 is about **visibility, not prevention**.

> **Theory primer:** Read [OWASP: A09:2021 – Security Logging and Monitoring Failures](https://owasp.org/Top10/2021/A09_2021-Security_Logging_and_Monitoring_Failures/)
> before working through this atom. The atoms in this repo show *how* a
> vulnerability happens in code; OWASP explains *what* this category is and
> why it matters. (Unlike most atoms, the primer here is OWASP rather than the
> PortSwigger Web Security Academy: the Academy organises its topics by
> exploitable vulnerability *class*, and logging-and-monitoring is a
> detection/observability category it has no dedicated concept page for.)

For the practical side — which events to record and, just as important, what to keep *out* of a log — the [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) is the companion reference: it lists authentication failures among the events to log, and passwords, session tokens, and secrets among the data to exclude.

## Stack note — single-container SQLite, and the two sides share dependencies

Each side is a single Flask container with its own ephemeral `lab.db`, seeded at boot with two users — there is no separate datastore. On the fixed side the per-account failure counter lives in an in-memory dict (a short-lived counter does not need a database), the same shape [`session-fixation`](../../A07-auth-failures/session-fixation/) uses for its session store. The fix changes nothing in `requirements.txt`: `logging` is standard library, so the two sides' dependencies are byte-identical and the whole difference is the security logging in `app.py`. (Contrast [`cve-demo`](../../A06-vulnerable-components/cve-demo/), where the entire diff was one line of `requirements.txt`; here the diff is code.)

## API only — no HTML, no browser

There is no web UI: no templates, every response is JSON. You drive this atom from **Burp Suite** — send the brute-force burst against `POST /login` with **Intruder** (or a repeated **Repeater** request): a list of wrong passwords against one account. The proof is read **outside** Burp, in the server output: compare `docker compose logs vulnerable` (blind) with `docker compose logs fixed` (the security trail plus the WARNING). There is no browser track — the proof is log text, not a screen.

## The login is correct — on purpose

The login is **identical on both sides** and correct: a parameterized query (no SQL injection), a proper salted password hash (`werkzeug.security.generate_password_hash`, not MD5/SHA-1 — password *storage* is a different atom, [`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/)), and a clean `200`/`401`. This lab carries exactly one flaw: the vulnerable side does not **log** the authentication failure. The fixed side adds only that logging — it does **not** add rate-limiting or a lockout, and it does **not** log the attempted password. Detection, not prevention; the fact, not the secret.

## Run

From the repo root:

```bash
./atom up logging-failures-demo
```

- Vulnerable API: `http://127.0.0.1:8038`
- Fixed API: `http://127.0.0.1:8138`

`GET /` returns a JSON banner; the target route is `POST /login`. To see the vulnerability, run a burst of failed logins against one account and compare the two sides' logs:

```bash
docker compose logs vulnerable   # blind: only generic "POST /login 401" access lines
docker compose logs fixed        # sees it: a security line per failure + a brute-force WARNING
```

Stop with `./atom down logging-failures-demo`. If you prefer raw Docker: `cd atoms/A09-logging-failures/logging-failures-demo && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step via Burp Suite: run the same brute-force burst against both sides and read the two logs side by side — the vulnerable one blind, the fixed one with the security trail and the WARNING. Primary track, no browser.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8138 serves the **same** login — same query, same hash check, same `200`/`401` — but on the failure path it emits a structured security event (`authentication failure account=… ip=…`, never the password) and, after five consecutive failures against one account, a `WARNING … possible brute-force …`. Repeat the burst against it: every attempt still returns `401` — the attack is **not blocked** — but now each failure is on the record and the WARNING names the account and the source. The same attack that was invisible on 8038 is visible and investigable on 8138. The change is pure **observability**: detection, not prevention. See [`DIFF.md`](./DIFF.md).
