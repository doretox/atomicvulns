# bopla-mass-assignment — Broken Object Property Level Authorization (BOPLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal TypeScript/Express REST API for BOPLA (Broken Object Property Level Authorization), API3:2023 in the OWASP API Security Top 10, in its **write face** — what the industry calls *mass assignment* (or *auto-binding*). Authorization applies at the level of an object's individual **properties**, not only to the object as a whole. The API lets you update your **own** profile through `PATCH /users/:handle`, and it checks ownership correctly — you can only write the record keyed by your own handle. But the handler then merges the **whole request body** into that record, so a key the profile form never offered — `is_admin` — is written just as readily as the one it did offer, `displayName`.

The lesson is that **being authorized for an object is not being authorized to set every field on it**. You are fully entitled to edit this record — it is yours — and the write still accepts a property you were never allowed to control. So the audit question here is **"is the write scoped to the fields this caller may set?"**, not "whose object is it?" (that is BOLA) and not "may you invoke this operation?" (that is BFLA). The proof is deliberately *not* the write's own response: `PATCH` answers `204 No Content` in **both** builds, with nothing in the body to mistake for evidence. What proves the escalation is reading the state through a different door — `GET /admin/users`, an admin-only route that is **correctly guarded** and answers `403` before the write and `200` after it.

This is the second atom at the **property** grain, and the mirror of its sibling `bopla-excessive-exposure`. There, the sin spread the stored record **into the response** (`...user` going out); here it spreads the request body **into the record** (`...req.body` coming in). Same root — trusting a whole object — in two directions, which is exactly why OWASP keeps the read side and the write side in one category.

> **Theory primer:** Read [PortSwigger: Mass assignment vulnerabilities](https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — in-memory store, no database

Users live in a TypeScript `Map`, each record holding two fields: `displayName` (the one field a user may edit) and `is_admin` (an internal role flag that decides who may call the admin route). There is no database: mass assignment doesn't depend on the storage layer, because the bug is in how the handler *builds the object it writes*, above whatever store holds the records. The `token -> user` map is in memory too.

## State — this atom writes, and the order matters

Unlike its read-side sibling, this atom **changes state**: `PATCH /users/:handle` rewrites the record. That has two consequences for working through it. First, the steps have an order — the admin route answers `403` **before** the write and `200` **after** it, and that transition *is* the proof, so asking it too late costs you the baseline. Second, nothing is permanent: `./atom down bopla-mass-assignment && ./atom up bopla-mass-assignment` restores the seed — the forged `is_admin` reverts to `false` (the admin route answers `403` again) and the issued tokens are gone (log in again). Each twin keeps its own seed, so a write on 8207 is invisible on 8307.

## API only — no HTML, no browser

There are no templates, no landing page, and no UI: responses are JSON, or a bare status with no content. That's deliberate — the thing under test is an API, and this atom models nothing else. You drive it entirely from **Burp Suite** (Repeater to edit and resend a single request) or from `curl`. There is no browser track; [`WALKTHROUGH.md`](./WALKTHROUGH.md) works exclusively from Burp.

## Authentication, simulated

`POST /login` takes a username and returns an **opaque Bearer token** — a random value the server stores and resolves back to a user, like an OAuth2 opaque access token or a server-side session id, and explicitly *not* a JWT (there is nothing encoded inside it to read or tamper with). It asks for **no password, and that is a deliberate lab shortcut, not the vulnerability**.

What the shortcut does *not* do is weaken authentication. Authentication here **is enforced**: a missing, malformed, or unknown token gets `401` with a `WWW-Authenticate: Bearer` challenge, in the vulnerable build exactly as in the fixed one. The token is crypto-strong (`randomBytes`), genuinely server-issued, and the attack never decodes, alters, or forges it — it stays valid and yours from the first request to the last. That detail carries weight here: your **identity** never changes during the exploit. What changes is the **state** the server reads when it decides whether you are an administrator.

## Users and records

Two users are seeded, each the owner of exactly one record — the one keyed by their own handle:

- `clancy` — the attacker (you). Owns the `clancy` record, the one you edit in the exploit.
- `alice` — exists only to make `PATCH /users/alice` a `403`, proving the ownership check works. Her record is never written in the walkthrough, and she never logs in.

Each record holds two fields: `displayName` (`"Clancy Park"`, `"Alice Nguyen"` in the seed) — the one field a profile update is meant to set; and `is_admin` — an internal role flag, **`false` for both**. **No administrator is seeded.** That is the point: the only admin this lab ever has is the one the bug creates.

## Three routes, nothing more

- `POST /login` — body `{"user":"<name>"}`, returns `{"token":"<opaque>"}`; an unknown user gets `400`.
- `PATCH /users/:handle` — update a profile. An ownership check lets you write only your own record (`403` for anyone else's). The **vulnerable** build then merges the whole request body into the record, so `{"is_admin":true}` is written; the **fixed** build writes an allow-list of one field, so the same body changes nothing but the display name. Both answer `204 No Content`.
- `GET /admin/users` — admin-only, read-only, and **byte-identical in both builds**. It reads the caller's role from the store and returns the list of handles, or `403` to a non-admin. This route is *not* the bug: its guard is correct, and it is the instrument that proves whether the write landed.

There is no `GET /users/:handle`, no public user list, and no `GET /me` — the only window onto the state is that admin door, which is deliberate: what matters is not seeing the field, it is seeing what the field *does*. There is also no promotion endpoint; nothing in this API is meant to grant the admin role at all.

## Run

From the repo root:

```bash
./atom up bopla-mass-assignment
```

- Vulnerable API: `http://127.0.0.1:8207`
- Fixed API: `http://127.0.0.1:8307`

There is no landing page — the entry point is `POST /login` (see [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Stop with `./atom down bopla-mass-assignment`. If you prefer raw Docker: `cd atoms/api/API3-broken-object-property-level-authz/bopla-mass-assignment && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8307 serves the same profile route against the same seed, and it changes **one line: what the handler writes**. Instead of merging the whole request body into the record, it names the one field the caller may set — an **allow-list** (whitelist). Replay the walkthrough against it and the striking part is how little the surface changes: `PATCH /users/clancy` with `{"displayName":"Clancy Parked","is_admin":true}` still answers `204 No Content` with an empty body — *the identical response* — and your display name really is updated. But `GET /admin/users` still answers `403`, because the `is_admin` in your body was never written. Same write, same status, dead effect. The ownership check and the `401` are unchanged too. [`DIFF.md`](./DIFF.md) works through why an allow-list (which fails closed) is the fix and a deny-list (which fails open) is not.
