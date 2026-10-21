# auth-predictable-token — Broken Authentication

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal TypeScript/Express REST API for **Broken Authentication**, API2:2023 in the OWASP API Security Top 10. The API lets you read your **own** account profile through `GET /users/:handle`, guarded by an ownership check — you only see the record keyed by your own handle, and asking for anyone else's is `403`. Authentication is by Bearer token, minted at `POST /login`. The flaw is in the token itself: it is not a random value but **your username, encoded in base64url**. base64url is reversible encoding, not a secret — so anyone who knows another user's handle can reconstruct that user's token from the name alone and authenticate **as them**.

The first seven atoms in this series each asked a question about **authorization** — *may you do this?* — and trusted the token to say who "you" are. This atom turns the light onto that assumption and asks the prior question: **are you really who you say you are?** That is the difference between **authentication** (proving *who you are*) and **authorization** (proving *that you may*). The target is the one mechanism the earlier seven left untouched on purpose — the token — and the audit question is **"is the token unpredictable to someone who did not receive it?"** Here it is not: the token *is* the name.

Read carefully where the bug is **not**. The ownership check on `GET /users/:handle` is correct — `clancy`, with his own token, asking for `GET /users/alice`, gets `403`. This is not a missing authorization check (that would be BOLA), and you do not steal a token (there is nothing to intercept). You **forge an identity**: you build `alice`'s token out of her public handle, send the same request with it, and the ownership guard — doing exactly its job — approves you, because the caller it compares against is now `alice`. The guard you can see is right; the lie enters one layer up, in how the token is resolved.

> **Theory primer:** Read [PortSwigger: Authentication vulnerabilities](https://portswigger.net/web-security/authentication)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — in-memory store, no database

Users live in a TypeScript `Map`, each record holding two fields: `displayName` and `email` — the private account datum this atom protects. There is no database: a predictable token doesn't depend on the storage layer, because the bug is in how the login *mints* the token and how authentication *resolves* it, above whatever store holds the users. In the fixed build a second `token -> user` map lives in memory too; the vulnerable build keeps no such map at all (it has nothing to store — it just decodes).

## State — the atom only reads; tokens are the only moving part

This atom **reads**: `GET /users/:handle` never changes a user record, so the steps have no order to respect and nothing to reset between them. The only moving part is the token, and the two builds treat it differently on restart. `./atom down auth-predictable-token && ./atom up auth-predictable-token` empties the fixed build's token map, so every issued token becomes `401` — log in again. The vulnerable build has **no token state to clear**: `base64url("alice")` is a valid token before the restart and after it, forever, because nothing on the server backs it. A token the server never recorded is one it can never revoke.

## API only — no HTML, no browser

There are no templates, no landing page, and no UI: responses are JSON, or a bare status with no content. That's deliberate — the thing under test is an API, and this atom models nothing else. You drive it entirely from **Burp Suite** (Repeater to edit and resend a single request) or from `curl`, plus the `base64` command-line tool to read and build tokens. There is no browser track; [`WALKTHROUGH.md`](./WALKTHROUGH.md) works exclusively from Burp.

## Authentication, simulated — and this is where the bug lives

`POST /login` takes a username and returns a Bearer token. It asks for **no password, and that is a deliberate lab shortcut, not the vulnerability** — do not confuse the two. The passwordless login is stage furniture; the flaw is the **shape of the token the login hands back**. In the vulnerable build, `issueToken("clancy")` is `Buffer.from("clancy").toString("base64url")` — the name, encoded, with no randomness and nothing stored. Authentication then *decodes* the token and trusts whatever name it spells. So authentication here does **not** prove who you are: anyone who can spell a handle can present that handle's token.

Contrast that with every earlier atom in the series, where the token was crypto-strong (`randomBytes`), server-issued, and the attack never touched it. Here the attack is *only* the token. The fixed build restores the series' real token: a random, opaque value the server stores at login and resolves by lookup, carrying no identity inside it to forge.

## Users and records

Two users are seeded, each the owner of exactly one record — the one keyed by their own handle:

- `clancy` — the attacker (you). You log in as `clancy`, read your own profile for the baseline, and then forge `alice`.
- `alice` — the impersonated victim. Her token is **never issued to you**; you build it from her handle. She never logs in.

Each record holds `displayName` (`"Clancy Park"`, `"Alice Nguyen"` in the seed) and `email` — `clancy@mail.example` and `alice@secret.example`, reserved `.example` domains, no real data. The `email` is the private datum: the owner may read it, nobody else should reach it, and `alice`'s email arriving in *your* response is the proof. There is **no `is_admin` and no password** on these records — this atom is about *who the caller is*, not what role they hold.

## Two routes, nothing more

- `POST /login` — body `{"user":"<name>"}`, returns `{"token":"<token>"}`; an unknown user gets `400`. The handler is byte-identical in both builds; only the `issueToken` it calls differs.
- `GET /users/:handle` — read a profile. It authenticates the caller, checks ownership (`403` for anyone else's record), and returns `{"handle", "displayName", "email"}`. This route is **byte-identical in both builds**: the ownership guard is correct, and it is *not* the bug. What differs between the builds is only who `authenticate` says the caller is.

There is no `GET /me`, no admin route, no `PATCH`, no user list. Two routes is the whole surface: one to get a token, one to read a profile behind a correct ownership check.

## Run

From the repo root:

```bash
./atom up auth-predictable-token
```

- Vulnerable API: `http://127.0.0.1:8208`
- Fixed API: `http://127.0.0.1:8308`

There is no landing page — the entry point is `POST /login` (see [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Stop with `./atom down auth-predictable-token`. If you prefer raw Docker: `cd atoms/api/API2-broken-authentication/auth-predictable-token && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8308 serves the same profile route against the same seed, and it changes the **authentication block**: the login mints a random, opaque token (`randomBytes(24)`) and **stores** the `token -> user` binding, and `authenticate` resolves it by **lookup** instead of decoding it. Replay the walkthrough against it and the forge dies at the door: `base64url("alice")` now answers `401`, because that string was never issued and the server does not recognize it — the token no longer says who you are, only the server's record does. Your own self-read still answers `200`, the ownership `403` and the missing-token `401` are unchanged. [`DIFF.md`](./DIFF.md) works through why the identity must not travel inside the token at all — and why *signing* the token (the tempting near-fix) solves the wrong problem.
