# mass-assignment — Mass Assignment

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask REST API for a classic **Mass Assignment**. The app has a profile-update endpoint: you send a JSON body with your account fields and it saves them — `POST /profile` with `{"name": "...", "email": "..."}` changes your name and email. The bug is that the handler copies *every* field of the JSON straight onto your account (`account.update(data)`), not only the ones the form offered. So if you add `"role": "admin"` — a field the profile form never had — it is copied too, and your account becomes an admin. The proof is on the wire: `GET /profile` now reports `role: admin`, and `GET /admin`, which returned `403` before, now answers `200`.

The lesson is that the **server**, not the client, must decide which fields a request may set. Trusting the *shape* of the input — binding whatever keys arrive straight onto the object — is the whole bug. This is **A01 — Broken Access Control** (CWE-915, "Improperly Controlled Modification of Dynamically-Determined Object Attributes"; its parent CWE-913 is one of the CWEs OWASP maps to A01:2021): the control that is missing is over *which attributes the user may modify* — you should be able to set `name`/`email`, but the app lets you write `role`, a field only the server should control. The OWASP API Security Top 10 tracks the same flaw as [API3:2023 — Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/) (which absorbed the former standalone "Mass Assignment" risk). The fix is server-side and structural — an **allowlist of fields**: the server names the fields the user may set (`name`, `email`) and copies only those; `role` and everything else are ignored. The one and only difference between `vulnerable/` and `fixed/` is that field selection.

> **Theory primer:** Read [PortSwigger: Mass assignment](https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — no database

Like `bola-rest`, this atom keeps its state in a plain Python dict rather than a database. Mass assignment doesn't depend on the storage layer — the bug is the blind field copy above whatever store you use. There is deliberately **no ORM** here: an ORM is where this flaw is most famous (an extra field becomes a written database column), but this atom models the same flaw with a bare `dict.update()` so the one bad line is visible to the naked eye. See `DIFF.md`.

## API only — no HTML, no browser

This atom has no web UI: no templates, no landing page, every response is JSON. That is deliberate — mass assignment lives in APIs that bind request bodies onto objects, and this atom models one. You drive it entirely from **Burp Suite (Repeater)** or `curl`; there is no browser track. `WALKTHROUGH.md` works exclusively from Burp — the proof is the response (the `role` in `GET /profile`, the status of `GET /admin`).

## Run

From the repo root:

```bash
./atom up mass-assignment
```

- Vulnerable API: `http://127.0.0.1:8025`
- Fixed API: `http://127.0.0.1:8125`

There is no landing page — the endpoints are `POST /profile`, `GET /profile`, and `GET /admin` (see `WALKTHROUGH.md`). The account lives in memory, so a restart (`./atom down mass-assignment` then `up`) resets it to a fresh `role: user` if you want to replay the baseline. Stop with `./atom down mass-assignment`. If you prefer raw Docker: `cd atoms/A01-broken-access-control/mass-assignment && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8125 serves the same profile feature. It adds an **allowlist of fields** — `ALLOWED_FIELDS = {"name", "email"}` — and copies only those from the JSON, changing nothing else. Replay the walkthrough against it: `POST /profile` with `{"name": ..., "email": ..., "role": "admin"}` still updates your name and email but **ignores `role`**, so `GET /profile` keeps `role: user` and `GET /admin` keeps returning `403`. A legitimate `name`/`email` update behaves identically on both apps; only the extra `role` field separates them. The one and only change from `vulnerable/` is that server-side field allowlist; see [`DIFF.md`](./DIFF.md). This is **A01 — Broken Access Control**: the server, not the client, decides which fields may be set.
