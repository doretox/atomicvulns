# bfla-admin-function — Broken Function Level Authorization (BFLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal TypeScript/Express REST API for BFLA (Broken Function Level Authorization), API5:2023 in the OWASP API Security Top 10. Function-level authorization is the check that asks *"may you invoke this operation at all?"* — a different question from *"is this object yours?"*, which is the object-level kind. The API exposes one admin function, `POST /admin/users/:handle/promote`, which grants the admin role to the account named in the path. The endpoint authenticates the Bearer token — an invalid token gets `401` — and then performs the promotion without ever checking that the caller is an admin, so any logged-in member can run it.

This is where the series changes axis. The three API1 atoms — `bola-sequential-id`, `bola-uuid-leaked`, and `bola-nested-resource` — were all BOLA (Broken Object Level Authorization): each served order records, and each turned on whether the requested order was within the caller's reach. BOLA protects **instances**; BFLA protects **capabilities**. Nobody else's record is read here. A plain member invokes a function reserved for administrators — **vertical privilege escalation**, reaching functionality above your own privilege level, where the API1 atoms showed the horizontal kind: reaching data that belongs to a peer. The lesson is that **a valid token proves who is calling, not that the caller may run this function**.

The admin path here is simply known. Admin routes follow predictable names, the OpenAPI spec (the machine-readable description of an API's routes) is often public, and the front-end bundle — the JavaScript a web app ships to every browser — carries paths for screens a regular user never sees. In real BFLA, finding the endpoint is almost never the hard part, so this atom declares it rather than staging a discovery. The vulnerability is not that the path is reachable; it is that invoking the function never checks your role. `bola-uuid-leaked` also started from a declared premise — an order UUID that reached the attacker from outside — but there the premise *was* the lesson. Here it is economy: it removes a step real BFLA rarely has, so the atom spends its time on the invocation.

> **Theory primer:** Read [PortSwigger: Access control vulnerabilities and privilege escalation](https://portswigger.net/web-security/access-control)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — in-memory store, no database

Users live in a TypeScript `Map`, each carrying a single boolean, `is_admin` — the role the missing check should have read. There is no database: BFLA doesn't depend on the storage layer, because the bug is a check absent *above* whatever store holds the roles, so the store is kept minimal and the absence stays obvious. The `token -> user` map is in memory too.

## State — promotions are real, and in memory

This is the first atom in the series whose attacked endpoint writes: a promotion really sets `is_admin` to `true` on the target, and the change lasts as long as the container runs. Nothing in the walkthrough depends on that accumulated state — run its steps twice and the statuses and bodies come back the same. Each twin keeps its own seed, so a promotion on 8204 changes nothing on 8304. `./atom down bfla-admin-function && ./atom up bfla-admin-function` brings back the original seed, with `carol` the only admin — and every issued token gone, so log in again.

## API only — no HTML, no browser

There are no templates, no landing page, and no UI: every successful response is JSON. That's deliberate — the function under test is an API endpoint, and this atom models nothing else. You drive it entirely from **Burp Suite** (Repeater to edit and resend a single request) or from `curl`. There is no browser track; [`WALKTHROUGH.md`](./WALKTHROUGH.md) works exclusively from Burp.

## Authentication, simulated

`POST /login` takes a username and returns an **opaque Bearer token** — a random value the server stores and resolves back to a user, like an OAuth2 opaque access token or a server-side session id, and explicitly *not* a JWT (there is nothing encoded inside it to read or tamper with). It asks for **no password, and that is a deliberate lab shortcut, not the vulnerability**: password handling would multiply the code and teach a different lesson.

What the shortcut does *not* do is weaken authentication. Authentication here **is enforced**: a missing, malformed, or unknown token gets `401` on the admin endpoint, in the vulnerable build exactly as in the fixed one. The token is crypto-strong (`randomBytes`), genuinely server-issued, and the attack never decodes, alters, or forges it — it stays valid and yours from the first request to the last. What's missing is not authentication; it is the function-level check on top of it — whether the authenticated caller holds the role the function requires.

## Users and roles

Four users are seeded, each with one role flag:

- `clancy` — the attacker (you). A plain member: `is_admin: false`.
- `alice` — the primary victim, also a plain member: the account `clancy` promotes in the exploit.
- `bob` — a plain member, the target of `carol`'s legitimate promotion in the fixed build.
- `carol` — the only administrator in the seed (`is_admin: true`), there so the fixed build can show the function still working for someone allowed to run it.

The users have no names, emails, or addresses — nothing a response could leak. That is on purpose: there is no third-party data here to mistake for an object read.

## Two routes, nothing more

- `POST /login` — body `{"user":"<name>"}`, returns `{"token":"<opaque>"}`; an unknown user gets `400`.
- `POST /admin/users/:handle/promote` — the admin function. The target goes in the path; no body needed. Success is `200` with `{"handle":"<target>","is_admin":true}`; an unknown target gets `404`.

There is no read route — no `GET /me`, no user listing, no demote — and that is a choice, not an omission. The admin function changes state and returns only what it wrote: the handle you sent and a literal `true`, never another user's record. With no third-party data coming back, there is nothing to read as *"I saw something that wasn't mine"* — the BOLA reflex the API1 atoms trained — and the attack stays on the axis of the operation. The price is stated plainly: a promotion's effect is real, but it is **not observable through the API**. The success body comes back byte-identical whether the target was a member or already an admin, and no route reads a role back, so from outside a `200` tells you only that the function ran.

## Run

From the repo root:

```bash
./atom up bfla-admin-function
```

- Vulnerable API: `http://127.0.0.1:8204`
- Fixed API: `http://127.0.0.1:8304`

There is no landing page — the entry point is `POST /login` (see [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Stop with `./atom down bfla-admin-function`. If you prefer raw Docker: `cd atoms/api/API5-broken-function-level-authz/bfla-admin-function && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8304 serves the same admin function against the same seed, and it adds **one guard**: before anything else, the handler checks that the caller is an admin and refuses with **`403`** if not. Nothing else changes. Replay the walkthrough against it: `clancy` promoting `alice` now gets `403`, returned before any write; `carol`, the seeded admin, promoting `bob` still gets `200`, so the feature works for whoever may run it; and a missing or bad token still gets `401`. The role check runs before the target is even looked up, so a non-admin gets the same `403` for a handle that doesn't exist. Note the status: `403`, not the `404` the API1 atoms return for an order outside your scope. There, the `404` made *"not yours"* indistinguishable from *"doesn't exist"*; here the protected thing is a single, known function, with no existence to hide — [`DIFF.md`](./DIFF.md) works through why.
