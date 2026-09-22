# bola-sequential-id — Broken Object Level Authorization (BOLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal TypeScript/Express REST API for BOLA (Broken Object Level Authorization) — the name API security gives an IDOR (insecure direct object reference) that lives in a REST endpoint, and [API1:2023](https://owasp.github.io/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/), the #1 risk in the OWASP API Security Top 10. The API serves order records through `GET /orders/:id`. Every request carries an opaque Bearer token, and the endpoint does authenticate it — an invalid token gets `401` — but it never checks that the requested order belongs to the caller. Twelve orders sit behind the contiguous ids `1001`–`1012` and you own exactly one of them, so changing the id in the path hands you somebody else's: their name, their delivery address, what they bought and what they paid.

The lesson is that **being authenticated is not being authorized**. A valid token proves *who you are*; it says nothing about whether *this* object is yours. Two separate things make the read happen, and keeping them apart is the point of the atom: the **sequential id** is what makes discovery cheap — knowing one id, you can deduce its neighbors — while the **missing ownership check** is what makes the request succeed. Only the second one is the vulnerability, and the fix touches only the second: the ids stay exactly as sequential and as public as before. The web atom `bola-rest` already made the core case for this class in Flask; this one scales it — four users, twelve orders carrying personal data, and an enumeration that walks the entire collection in one pass.

> **Theory primer:** Read [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — in-memory store, no database

Orders live in a plain TypeScript `Record`, not a database. BOLA doesn't depend on the storage layer: the bug is a missing authorization check *above* whichever store you use, so the store is kept minimal and the missing check stays obvious. The `token -> user` map is in memory too — restart the container and every issued token is gone, so log in again and continue.

## API only — no HTML, no browser

There are no templates, no landing page, and no UI: every successful response is JSON. That's deliberate — BOLA lives in REST APIs, and this atom models one. You drive it entirely from **Burp Suite** (Repeater to edit and resend a single request, Intruder to replay one request across a list of values) or from `curl`. There is no browser track; [`WALKTHROUGH.md`](./WALKTHROUGH.md) works exclusively from Burp.

## Authentication, simulated

`POST /login` takes a username and returns an **opaque Bearer token** — a random value the server stores and resolves back to a user, like an OAuth2 opaque access token or a server-side session id, and explicitly *not* a JWT (there is nothing encoded inside it to read or tamper with). It asks for **no password, and that is a deliberate lab shortcut, not the vulnerability**: password handling would multiply the code and teach a different lesson.

What the shortcut does *not* do is weaken authentication. Authentication here **is enforced**: a missing, malformed, or unknown token gets `401` on every protected endpoint. The token is crypto-strong (`randomBytes`), genuinely server-issued, and the attack never decodes, alters, or forges it — it stays valid and yours from the first request to the last. What's missing is not authentication; it is the object-level authorization check on top of it.

Four users are seeded:

- `dana` — the attacker (you). Owns exactly **one** order, `1007`.
- `alice`, `bob`, `carol` — the victims. They split the other **eleven** orders unevenly: six, three, and two.

## Run

From the repo root:

```bash
./atom up bola-sequential-id
```

- Vulnerable API: `http://127.0.0.1:8201`
- Fixed API: `http://127.0.0.1:8301`

There is no landing page — the entry point is `POST /login` (see [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Stop with `./atom down bola-sequential-id`. If you prefer raw Docker: `cd atoms/api/API1-broken-object-level-authz/bola-sequential-id && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8301 serves the same orders feature against the same seed. It adds **one predicate to one guard** — the order is returned only if it exists *and* belongs to the calling token's user — and changes nothing else, id format included. Replay the walkthrough against it: your own order still returns `200`, and every other id returns **`404`**, the very same `404` an id that was never seeded returns. Because "not yours" and "doesn't exist" come out identical, the status code gives an attacker nothing to enumerate with.
