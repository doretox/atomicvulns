# weak-password-reset — Predictable password-reset token

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for a password-reset flow whose token is **predictable**. When a user forgets their password, the app issues a **reset token** — a secret string it "emails" to the account owner — and whoever presents that token may set a new password. The token is a **temporary credential**: holding it *is* the authorization to change the password. The flow itself is correct. The flaw is how the token is generated: with Python's `random` module, **seeded from the clock** (`random.seed(int(time.time()))`). `random` is a PRNG (pseudo-random number generator) — deterministic from its seed — and the seed is the server's time in whole seconds, a value the attacker reads straight off the HTTP `Date` response header. Re-seed with it, run the same generator, and you reproduce the victim's token byte-for-byte, reset her password, and log in as her. No crypto is broken and nothing is injected — the secret simply isn't secret.

This is the sibling of [`session-fixation`](../session-fixation/), and the contrast is the lesson. Both are **A07 — Identification and Authentication Failures**, and both turn on a credential that identifies a user without ever being stolen. But there the session id is *strong* (`secrets.token_urlsafe`) and the bug is its **lifecycle** — it survives the login; here the reset token is *weak* — **predictable** — and that predictability **is** the bug. (Session fixation's own "what it is NOT" note says a weak, predictable id "would be a different bug"; this atom is that bug.) The fix is not a stronger flow or a longer token — it is a different **generator**: `secrets.token_urlsafe`, a CSPRNG (cryptographically secure PRNG), plus single-use and a short expiry.

> **Theory primer:** Read [PortSwigger: Vulnerabilities in other authentication mechanisms](https://portswigger.net/web-security/authentication/other-mechanisms)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — single-container SQLite, and the two sides share dependencies

Each side is a single Flask container with its own ephemeral `lab.db`, seeded at boot with two users — there is no separate datastore. Reset tokens live in an in-memory dict (a short-lived token does not need a database), the same shape `session-fixation` uses for its session store. Unlike `crypto-weak-hash`, whose fix pulls in a library, the fix here changes nothing in `requirements.txt`: `random` and `secrets` are both standard library, so the two sides' dependencies are byte-identical and the whole difference is one generator in `app.py`.

## API only — no HTML, no browser

There is no web UI: no templates, every response is JSON. You drive this atom from **Burp Suite (Repeater)** — request the victim's reset, read the `Date` header, run a short **local predictor script** that reproduces the token (the one thing Burp can't do — the same way a browser runs JavaScript for a client-side bug, the tool that reproduces the token joins the primary track), reset the password, and log in as the victim. There is no browser track; the proof is the login response.

## The passwords are hashed properly — on purpose

The seeded users' passwords are stored with a decent salted hash (`werkzeug.security.generate_password_hash`), not MD5/SHA-1. That is deliberate: password *storage* is a different atom ([`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/)), and this lab must carry exactly one flaw — the reset-token generator. The login and the reset flow are correct; only the token is predictable.

## Run

From the repo root:

```bash
./atom up weak-password-reset
```

- Vulnerable API: `http://127.0.0.1:8037`
- Fixed API: `http://127.0.0.1:8137`

There is no landing page beyond a JSON banner at `/` — the entry points are `POST /forgot`, `POST /reset`, and `POST /login` (see `WALKTHROUGH.md`). Stop with `./atom down weak-password-reset`. If you prefer raw Docker: `cd atoms/A07-auth-failures/weak-password-reset && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite: request the victim's reset, predict the token from the `Date` header, reset the password, and log in as the victim. Primary track, no browser.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8137 serves the **same** flow — same endpoints, same "email" delivery, same login — but generates the reset token with `secrets.token_urlsafe(32)`, a CSPRNG, and makes it single-use with a short expiry. Repeat the attack against it: the `Date` header still tells you the second, but re-seeding `random` no longer reproduces anything — the token came from `os.urandom`, not a clock-seeded PRNG — so `POST /reset` rejects every predicted token and the takeover fails. The predicted token is refused as unknown *before* single-use or expiry ever apply: the decisive change is the unpredictable generator. See [`DIFF.md`](./DIFF.md).
