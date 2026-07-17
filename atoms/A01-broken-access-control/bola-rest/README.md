# bola-rest — Broken Object Level Authorization (BOLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask REST API for BOLA (Broken Object Level Authorization) — the name the API-security world gives IDOR when it lives in a REST endpoint, and [API1:2023](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/), the #1 risk in the OWASP API Security Top 10. The API serves order records through `GET /api/orders/<id>`. Every request carries an opaque Bearer token, and the endpoint does authenticate it — an invalid token gets `401` — but it never checks that the requested order belongs to the caller. So any logged-in user reads any user's order just by changing the id in the path. It is the exact same bug as `idor-numeric-id` and `idor-uuid-guessable`: a missing object-level authorization check.

The lesson is that **being authenticated is not being authorized**. A valid token proves *who you are*; it says nothing about whether *this* object is yours. And where the two sibling IDOR atoms taught that reshaping the id — a UUID, a random value — is not access control, this one closes the arc: in a REST API the id is *public by design*. It is in the path, it is a sequential integer, and the client is handed its own ids by `GET /api/orders`. There is nothing to guess and nothing to reconstruct, so object-level authorization is the only line of defense there could be — and it is absent. The fix leaves the sequential id untouched and adds one line: compare the order's owner to the caller.

> **Theory primer:** Read [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — no database

Like `idor-numeric-id` and `idor-uuid-guessable`, this atom keeps its data in a plain Python dict rather than a database. BOLA doesn't depend on the storage layer: the bug is a missing authorization check above whichever store you use. The surface is kept minimal so the missing line is obvious.

## API only — no HTML, no browser

Unlike the sibling atoms, this one has no web UI: no templates, no landing page, every response is JSON. That is deliberate — BOLA lives in REST APIs, and this atom models one. You drive it entirely from **Burp Suite (Repeater)** or `curl`; there is no browser track. `WALKTHROUGH.md` works exclusively from Burp.

## Authentication, simulated

Real authentication (passwords, hashing, login sessions) is out of scope here — that belongs in a dedicated authentication atom. This lab fakes it with `POST /login`, which takes a username and returns an **opaque Bearer token**: a random value the server stores and resolves back to a user (like an OAuth2 opaque access token or a server-side session id — *not* a JWT). Two users are seeded:

- `mallory` — the attacker (you). She logs in as herself and gets her own token.
- `alice` — the victim, whose order is seeded at startup — the one you should not be able to read.

The token is genuine and server-issued, and the attack never inspects, decodes, or forges it — it stays valid throughout. What is missing is not authentication; it is the object-level authorization check on top of it.

## Run

From the repo root:

```bash
./atom up bola-rest
```

- Vulnerable API: `http://127.0.0.1:8012`
- Fixed API: `http://127.0.0.1:8112`

There is no landing page — the entry point is `POST /login` (see `WALKTHROUGH.md`). Stop with `./atom down bola-rest`. If you prefer raw Docker: `cd atoms/A01-broken-access-control/bola-rest && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8112 serves the same orders feature. It adds one line — an object-level authorization check that returns **404** unless the order belongs to the calling token's user — and changes nothing else, keeping the sequential integer id exactly as public as before (reshaping the id was never the fix). Replay the walkthrough against it: reading your own order returns 200, reading anyone else's returns **404**, and because a rejected non-owner request and a genuinely missing id both return 404, the status code gives an attacker nothing to enumerate with.
