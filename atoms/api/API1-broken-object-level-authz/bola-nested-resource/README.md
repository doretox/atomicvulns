# bola-nested-resource — Broken Object Level Authorization (BOLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal TypeScript/Express REST API for BOLA (Broken Object Level Authorization) — the name API security gives an IDOR (insecure direct object reference) that lives in a REST endpoint, and API1:2023, the #1 risk in the OWASP API Security Top 10. This one serves a **nested resource**: an object addressed *through its parent* in the path, here `GET /stores/:storeId/orders/:orderId` — an order (the child) asked for inside a store (the parent). The endpoint authenticates the Bearer token, and then it does something the two companion atoms in this category never did: it **checks authorization**. It asks whether the caller operates the store named in the path and answers `403` when they don't. Then it looks the order up in the platform-wide collection and returns it, without ever comparing the order's own store to the one it just authorized.

So the lesson here is not that authorization was missing. It is that **a check can be real, can reject real requests, and still guard the wrong thing**. Two questions look like one when both take a store as their subject: *"do you operate this store?"* and *"does this order belong to this store?"*. The handler answers the first and never asks the second. Nothing was hidden from it, either — every order carries its own `storeId`, and you can watch the mismatch come back in the response body: `"storeId":"meadow"` on a request whose path said `harbor`.

That inverts the premise of the other two. `bola-sequential-id` and `bola-uuid-leaked` both put the bug in a detail handler with **no** object-level check at all — an omission, with nothing beside it that a reviewer could mistake for authorization. Here the omission has company: a genuine `403` sits immediately above the buggy lookup and makes the handler look covered. It is also the repo's first nested resource — no other published route, web or API, takes two path parameters.

> **Theory primer:** Read [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — in-memory data, no database

Stores and orders live in plain TypeScript `Record`s, not a database. BOLA doesn't depend on the storage layer: the bug is an authorization question the handler never asks, and that sits *above* whatever persistence you choose — so the data layer is kept minimal and the missing question stays obvious. The `token -> user` map is in memory too — restart the container and every issued token is gone, so log in again and continue.

## API only — no HTML, no browser

There are no templates, no landing page, and no UI: every successful response is JSON. That's deliberate — BOLA lives in REST APIs, and this atom models one. You drive it entirely from **Burp Suite** (Repeater to edit and resend a single request) or from `curl`. There is no browser track; [`WALKTHROUGH.md`](./WALKTHROUGH.md) works exclusively from Burp.

## Authentication, simulated

`POST /login` takes a username and returns an **opaque Bearer token** — a random value the server stores and resolves back to a user, like an OAuth2 opaque access token or a server-side session id, and explicitly *not* a JWT (there is nothing encoded inside it to read or tamper with). It asks for **no password, and that is a deliberate lab shortcut, not the vulnerability**: password handling would multiply the code and teach a different lesson.

What the shortcut does *not* do is weaken authentication. Authentication here **is enforced**: a missing, malformed, or unknown token gets `401` on every protected endpoint. The token is crypto-strong (`randomBytes`), genuinely server-issued, and the attack never decodes, alters, or forges it — it stays valid and yours from the first request to the last. Nor is the store check window dressing: ask for a store you don't operate and you get `403`, in the vulnerable build exactly as in the fixed one. What's missing is the third thing — any check that the order you asked for belongs to the store that was authorized.

## Stores, operators, and orders

People here are **operators** of a store: they work there, they are not the store. Three stores are seeded, and their slugs are public names, no more secret than a shop sign:

| Store | Operators | Orders |
|---|---|---|
| `harbor` | `clancy` — the attacker (you) | `1004`, `1008`, `1011` |
| `meadow` | `alice` | `1002`, `1006`, `1007`, `1009` |
| `summit` | `bob`, `carol` | `1001`, `1003`, `1005`, `1010`, `1012` |

The twelve order ids run `1001`–`1012` on **one global counter shared by the whole platform**, so any single store's ids have gaps — and the gaps are other stores' orders. Each order carries the buyer's name, delivery address, item, and amount. Buyers are the public (`Priya Shah`, `Marcus Webb`, `Elena Ruiz`, `Theo Okafor`); operators are staff; the two sets never overlap.

**Operators of the same store legitimately share its orders** — `bob` and `carol` both operate `summit` and see the same five orders, and you see every `harbor` order, whoever bought it. That sharing is the feature, not the flaw. What is *not* the feature is reading order `1009` in `meadow` through `/stores/harbor/...`.

## Run

From the repo root:

```bash
./atom up bola-nested-resource
```

- Vulnerable API: `http://127.0.0.1:8203`
- Fixed API: `http://127.0.0.1:8303`

There is no landing page — the entry point is `POST /login` (see [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Stop with `./atom down bola-nested-resource`. If you prefer raw Docker: `cd atoms/api/API1-broken-object-level-authz/bola-nested-resource && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8303 serves the same back-office feature against the same seed, and it changes **one line: where the order is looked up**. Instead of searching the platform-wide collection, the handler searches the authorized store's own orders — the same scope the list endpoint one route above was already using. Replay the walkthrough against it: `harbor`'s own orders still return `200`, a store you don't operate still returns `403`, and order `1009` asked for through `harbor` now returns **`404`** — the very same `404` as an id that was never seeded. [`DIFF.md`](./DIFF.md) works through why the parent answers `403` while the child answers `404`, and why the fix moved the lookup instead of adding a predicate to the guard.
