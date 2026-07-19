# session-fixation — Session fixation

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for session fixation. The app has a login form and a protected `/account` page, and it tracks who you are with a server-side session: an opaque `session_id` travels in a cookie while the session data lives on the server (the classic `PHPSESSID` / `JSESSIONID` pattern). When you log in, the vulnerable app authenticates *the session you already had* without issuing a new `session_id` — so an id that existed **before** login (one an attacker could have planted) now identifies an **authenticated** session.

This is not an input-driven bug — there is no payload to craft. The attacker **gives** the victim a session id instead of stealing one: they grab an anonymous `session_id` from the server, plant it in the victim's browser **before** login, let the victim log in with **their own** correct password, and then ride that now-authenticated session with the id they already knew. They never learn the password. The whole bug is a single missing step: the server never **regenerates** the session id when the privilege level changes from anonymous to authenticated.

> **Theory primer:** Read [OWASP: Session fixation](https://owasp.org/www-community/attacks/Session_fixation)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; OWASP explains *what*
> it is and why it matters.

*Session fixation doesn't have a dedicated page in the PortSwigger Academy (the primer source used across these atoms), so this one points to OWASP, which covers it conceptually.*

## Fixation is not hijacking

Keep the distinction straight, because it *is* the lesson. **Hijacking steals an already-authenticated session id** — after login, via sniffing, XSS, malware. **Fixation plants an id before login** and lets the victim authenticate it. Different direction (the attacker *gives*, doesn't take) and different timing (before, not after). The attacker never reads the victim's authenticated cookie — they held the id since before the victim ever logged in. Cookie-theft defenses (`HttpOnly`, `Secure`) therefore do **not** fix fixation; the fix is to regenerate the id at login. See [`DIFF.md`](./DIFF.md).

## Stack note — no database

Sessions live in a plain Python dict (`SESSIONS = {session_id: {...}}`), not a database — session fixation is about the session's *lifecycle*, not the storage layer. Crucially, the app does **not** use Flask's built-in `session`: that is a signed client-side cookie with no server-side id to fix, and it regenerates by design, so fixation cannot live there. This lab models the server-side session pattern (an opaque id in the cookie) where session fixation actually occurs. See [`DIFF.md`](./DIFF.md) for why the choice of mechanism matters.

## Authentication, simulated

Real authentication (password hashing, rate limiting, MFA) is out of scope — it would teach a different lesson. One seeded credential, checked with a plain string comparison:

- `alice` / `password123`

The password is deliberately trivial: it is not the object of study. The *only* thing that differs between the vulnerable and fixed apps is what happens to the `session_id` at login — nothing about the password or the login check.

The pages print the current `session_id` on screen. Real apps don't do that; it is surfaced here only so you can watch, at a glance, whether the id changes across login (it doesn't, in the vulnerable app — that's the bug). In a real engagement you would read it from the cookie in Burp or DevTools.

## Run

From the repo root:

```bash
./atom up session-fixation
```

- Vulnerable app: <http://127.0.0.1:8015/>
- Fixed app: <http://127.0.0.1:8115/>

Stop with `./atom down session-fixation`. If you prefer raw Docker: `cd atoms/A07-auth-failures/session-fixation && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary) and browser (secondary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8115 serves the same feature. Repeat the attack chain from `WALKTHROUGH.md` against it: you can still grab an anonymous `session_id` and log in with it, but the moment the victim authenticates, the server issues a **new** id and discards the old one — so the id you planted is never authenticated, and replaying it against `/account` returns a redirect to the login page instead of the account. The only change is that one regeneration at login.
