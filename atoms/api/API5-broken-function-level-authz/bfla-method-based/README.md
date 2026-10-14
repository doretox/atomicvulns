# bfla-method-based — Broken Function Level Authorization (BFLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal TypeScript/Express REST API for BFLA (Broken Function Level Authorization), API5:2023 in the OWASP API Security Top 10. Authorization applies to a **(method, path)** pair, not to a path. The API guards `GET /users/:handle` with an ownership check — you read only your own profile — but leaves `PATCH /users/:handle`, the very same path, with no such check, so any logged-in user can edit anyone's record. Both methods authenticate the Bearer token — an invalid one gets `401` — and then the write proceeds without ever asking whether the record is yours.

The check that `GET` has and `PATCH` lacks is an **ownership** check — object-level, the same *"is this record mine?"* the API1 atoms turned on. But that is only the *content* of the missing check; the axis of the vulnerability is the **method**. So the audit question here is **"does authorization cover every method of this path?"**, not "whose object is it?". Read it as BOLA (Broken Object Level Authorization) and you look in the wrong place: the ownership check is present and *correct* on `GET` — it returns `403` when you ask for someone else's record, `200` when you ask for your own — and the flaw is only that it does not cover `PATCH`.

This is the series' second BFLA. Its sibling `bfla-admin-function` (also API5) showed a function with **no** authorization at all — a plain member invoking an admin-only operation, which is **vertical** privilege escalation. Here a check exists and works on one method of a path and is simply missing on another: a developer guarded the read, assumed the resource was protected, and left the write open. The three API1 atoms asked a question about the object — *"is this order yours?"* in `bola-sequential-id` and `bola-uuid-leaked`, *"does it belong to this store?"* in `bola-nested-resource` — and answered it on every route that served the object. This atom answers the ownership question on `GET` and forgets to ask it on `PATCH`. The reach is **horizontal** — editing a peer's record, not gaining a higher role — and the lesson is that **a check on one method of a path never guards the others**.

> **Theory primer:** Read [PortSwigger: Access control vulnerabilities and privilege escalation](https://portswigger.net/web-security/access-control)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — in-memory store, no database

Users live in a TypeScript `Map`, each holding a single editable field, `displayName`. There is no database: BFLA doesn't depend on the storage layer, because the bug is a missing check *above* whatever store holds the records, so the store is kept minimal and the gap stays obvious. The `token -> user` map is in memory too.

## State — the edit is real, and in memory

`PATCH` really writes: it changes the target's `displayName`, and the change lasts as long as the container runs. But that change is **not observable to the attacker through the API** — the `PATCH` response only echoes the value you sent, and `GET /users/:handle` refuses a record that isn't yours with `403`. What makes the change visible is the **victim** reading her own record: log in as `alice` and `GET /users/alice` returns the `displayName` that `clancy` wrote. Each twin keeps its own seed, so an edit on 8205 changes nothing on 8305. `./atom down bfla-method-based && ./atom up bfla-method-based` brings back the original seed — and every issued token with it, so log in again.

## API only — no HTML, no browser

There are no templates, no landing page, and no UI: every successful response is JSON. That's deliberate — the thing under test is an API, and this atom models nothing else. You drive it entirely from **Burp Suite** (Repeater to edit and resend a single request) or from `curl`. There is no browser track; [`WALKTHROUGH.md`](./WALKTHROUGH.md) works exclusively from Burp.

## Authentication, simulated

`POST /login` takes a username and returns an **opaque Bearer token** — a random value the server stores and resolves back to a user, like an OAuth2 opaque access token or a server-side session id, and explicitly *not* a JWT (there is nothing encoded inside it to read or tamper with). It asks for **no password, and that is a deliberate lab shortcut, not the vulnerability**: password handling would multiply the code and teach a different lesson.

What the shortcut does *not* do is weaken authentication. Authentication here **is enforced**: a missing, malformed, or unknown token gets `401` on both routes, in the vulnerable build exactly as in the fixed one. The token is crypto-strong (`randomBytes`), genuinely server-issued, and the attack never decodes, alters, or forges it — it stays valid and yours from the first request to the last. What's missing is not authentication; it is the ownership check on the `PATCH` method — a check the `GET` method on the same path already has.

## Users and records

Two users are seeded, each the owner of exactly one record — the one keyed by their own handle:

- `clancy` — the attacker (you). Owns the `clancy` record.
- `alice` — the victim. Owns the `alice` record, the one `clancy` edits in the exploit.

Each record holds a single editable field, `displayName` (`"Clancy Park"`, `"Alice Nguyen"` in the seed) — an ordinary profile field, **not** a privilege flag. There is no admin role in this atom: ownership is simply *the handle in the path equals the caller*, and the fixed build shows the feature still works by letting you edit your **own** record.

## Three routes, nothing more

- `POST /login` — body `{"user":"<name>"}`, returns `{"token":"<opaque>"}`; an unknown user gets `400`.
- `GET /users/:handle` — read a profile. **Correct in both builds:** an ownership check returns the record only to its owner (`200` with `{"handle":"<handle>","displayName":"<value>"}`), and `403` for anyone else's.
- `PATCH /users/:handle` — edit the display name. The **vulnerable** build omits the ownership check that `GET` has, so it writes any record. Success is `200` with `{"handle":"<handle>","displayName":"<value>"}`; an unknown target gets `404`.

There is no list route, no `GET /me`, and no delete. One point worth stating plainly: the `PATCH` `200` confirms the **bypass** — the write was accepted for a non-owner — but its body just echoes the `displayName` you sent, so it is not by itself proof that the record changed. The proof is the victim reading her own record through the authorized `GET`, where the planted value comes back.

## Run

From the repo root:

```bash
./atom up bfla-method-based
```

- Vulnerable API: `http://127.0.0.1:8205`
- Fixed API: `http://127.0.0.1:8305`

There is no landing page — the entry point is `POST /login` (see [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Stop with `./atom down bfla-method-based`. If you prefer raw Docker: `cd atoms/api/API5-broken-function-level-authz/bfla-method-based && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8305 serves the same two user routes against the same seed, and it adds **one guard** to `PATCH`, between the authentication check and the record lookup: the same ownership check `GET` already has — refuse with **`403`** unless the handle in the path is the caller's own. Nothing else changes. Replay the walkthrough against it: `clancy` editing `alice` now gets `403`, returned before any write, so `alice`'s record is untouched; `clancy` editing his **own** record still gets `200`, so the feature works for whoever owns the record; and a missing or bad token still gets `401`. The ownership check runs before the lookup, so a non-owner gets the same `403` for a handle that doesn't exist. Note the status: `403`, not the `404` the API1 atoms return for an order outside your scope — there the `404` hid an order's existence from an enumerable id space; here the check compares the path handle to the caller before any lookup, so it reveals no existence to hide. [`DIFF.md`](./DIFF.md) works through why.
