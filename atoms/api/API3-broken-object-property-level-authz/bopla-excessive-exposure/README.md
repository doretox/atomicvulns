# bopla-excessive-exposure — Broken Object Property Level Authorization (BOPLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal TypeScript/Express REST API for BOPLA (Broken Object Property Level Authorization), API3:2023 in the OWASP API Security Top 10, in its **read face** — what the industry calls *excessive data exposure*. Authorization applies at the level of an object's individual **properties**, not only to the object as a whole. The API lets you read your **own** profile through `GET /users/:handle`, and it checks ownership correctly — you can only read the record keyed by your own handle. But the handler then serializes the **whole stored object**, so two server-side fields you were never meant to see — `passwordHash` and `is_admin` — ride back in the response alongside the one public field, `displayName`.

The lesson is that **being authorized for an object is not being authorized for every field in it**. You are fully entitled to this record — it is yours — and the response still hands you properties you may not see. So the audit question here is **"does the response return only the fields this caller may see?"**, not "whose object is it?" (that is BOLA) and not "may you invoke this operation?" (that is BFLA). Read it as BOLA and you look in the wrong place: you are reading your **own** record, and `GET` for someone else's record is correctly refused with `403`. The object-level check is present and works; the flaw lives one line below it, in the serialization.

This is the series' first atom at the **property** grain. The three API1 atoms — `bola-sequential-id`, `bola-uuid-leaked`, `bola-nested-resource` — turned on the **object** (*whose object is this?*). The two API5 atoms — `bfla-admin-function`, `bfla-method-based` — turned on the **function/operation** (*may you invoke this? / does authorization cover every method?*). This one descends one grain further, to the **field**. It also inverts its sibling `bfla-method-based`: there the `GET /users/:handle` handler was the *living proof* of a correct ownership check; here the very same `GET`, with the same ownership guard still on top, is the vulnerable one — the flaw is new and sits below the guard, in what the response serializes.

> **Theory primer:** Read [PortSwigger: Information disclosure vulnerabilities](https://portswigger.net/web-security/information-disclosure)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — in-memory store, no database

Users live in a TypeScript `Map`, each record holding three fields: `displayName` (public), `passwordHash` and `is_admin` (both server-side). There is no database: BOPLA doesn't depend on the storage layer, because the bug is in what the handler *serializes* above whatever store holds the records — so the store is kept minimal and the leak stays obvious. The `token -> user` map is in memory too.

## State — read-only, nothing changes

Unlike the two BFLA atoms, whose attacked endpoint wrote, this atom only **reads**: `GET /users/:handle` never mutates anything. Every request is idempotent and deterministic, and no step depends on another's order. The `token -> user` map grows with each login, but the profiles never change. `./atom down bopla-excessive-exposure && ./atom up bopla-excessive-exposure` clears the issued tokens (log in again); the seeded profiles are the same either way.

## API only — no HTML, no browser

There are no templates, no landing page, and no UI: every successful response is JSON. That's deliberate — the thing under test is an API, and this atom models nothing else. You drive it entirely from **Burp Suite** (Repeater to edit and resend a single request) or from `curl`. There is no browser track; [`WALKTHROUGH.md`](./WALKTHROUGH.md) works exclusively from Burp. This matters to the lesson: in a real app a UI might hide these fields from the screen, but the filtering has to be server-side — the raw response is what a pentester reads, and here there is no UI at all.

## Authentication, simulated

`POST /login` takes a username and returns an **opaque Bearer token** — a random value the server stores and resolves back to a user, like an OAuth2 opaque access token or a server-side session id, and explicitly *not* a JWT (there is nothing encoded inside it to read or tamper with). It asks for **no password, and that is a deliberate lab shortcut, not the vulnerability**; and the `passwordHash` in each record is **dummy stored-side data, never read by the login and not a real credential**.

What the shortcut does *not* do is weaken authentication. Authentication here **is enforced**: a missing, malformed, or unknown token gets `401` with a `WWW-Authenticate: Bearer` challenge, in the vulnerable build exactly as in the fixed one. The token is crypto-strong (`randomBytes`), genuinely server-issued, and the attack never decodes, alters, or forges it — it stays valid and yours from the first request to the last. What's missing is not authentication, and not the ownership check either; it is the property-level filtering on the response.

## Users and records

Two users are seeded, each the owner of exactly one record — the one keyed by their own handle:

- `clancy` — the attacker (you). Owns the `clancy` record, the one you read in the exploit.
- `alice` — exists only to make `GET /users/alice` a `403`, proving the ownership check works. Her record is never read successfully in the walkthrough.

Each record holds three fields: `displayName` (`"Clancy Park"`, `"Alice Nguyen"` in the seed) — public; `passwordHash` — a dummy, bcrypt-shaped string, server-side; and `is_admin` — an internal role flag, **`false` for both**. There is no admin role in this atom: the point is that the internal fields come back *at all*, not that any value is special.

## Two routes, nothing more

- `POST /login` — body `{"user":"<name>"}`, returns `{"token":"<opaque>"}`; an unknown user gets `400`.
- `GET /users/:handle` — read a profile. An ownership check returns the record only to its owner (`403` for anyone else's). The **vulnerable** build then serializes the whole object, so the response includes `passwordHash` and `is_admin`; the **fixed** build serializes an allow-list, so it returns only `{"handle":"<handle>","displayName":"<value>"}`.

There is no `PATCH`, no list route, and no `GET /me`. One point worth stating plainly: the vulnerable self-read is both the baseline and the exploit — you ask for your own profile, fully authorized, and the internal fields are already in the body. The proof needs no second actor and no second request.

## Run

From the repo root:

```bash
./atom up bopla-excessive-exposure
```

- Vulnerable API: `http://127.0.0.1:8206`
- Fixed API: `http://127.0.0.1:8306`

There is no landing page — the entry point is `POST /login` (see [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Stop with `./atom down bopla-excessive-exposure`. If you prefer raw Docker: `cd atoms/api/API3-broken-object-property-level-authz/bopla-excessive-exposure && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8306 serves the same profile route against the same seed, and it changes **one line: what the response serializes**. Instead of spreading the whole stored object, the handler names the fields the caller may see — an **allow-list** (whitelist). Replay the walkthrough against it: `GET /users/clancy` with your own token still returns `200`, but the body is now exactly `{"handle":"clancy","displayName":"Clancy Park"}` — `passwordHash` and `is_admin` are gone. The ownership check and the `401` are unchanged: `GET /users/alice` with your token still gets `403`, and a missing or bad token still gets `401`. [`DIFF.md`](./DIFF.md) works through why an allow-list (which fails closed) is the fix and a deny-list (which fails open) is not.
