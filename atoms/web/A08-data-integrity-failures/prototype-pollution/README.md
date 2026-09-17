# prototype-pollution — Prototype pollution

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Node.js REST API for a classic **Prototype pollution**. The app stores your preferences: you send a JSON body of config fields to `POST /settings` and it *deep-merges* them into the current settings — recursing into nested objects. In JavaScript almost every object inherits from a shared parent, `Object.prototype`; reading a property an object doesn't have makes the engine walk up to that parent, and an object's `__proto__` key is the door to it. The bug is that the merge descends through *any* key of your JSON — including `__proto__`. Send `{"__proto__":{"isAdmin":true}}` and the merge, instead of writing a field of the settings, writes onto the `Object.prototype` **shared by every object in the process**. The proof is at an endpoint that says nothing about settings: `GET /me` builds a brand-new, empty user object and checks `if (user.isAdmin)` — and now, though you never touched that object, it reports admin.

The lesson is that a deep-merge of untrusted JSON must **refuse the keys that reach a shared prototype**, not descend through them. This is **A08 — Software and Data Integrity Failures** (CWE-1321, "Improperly Controlled Modification of Object Prototype Attributes ('Prototype Pollution')"): a blob of untrusted data corrupts the integrity of a data structure shared by the whole process — the parent of every object. It shares the category with `deserialization-pickle`, the repo's other A08 atom, but the **impact differs**: there the deserializer *executes* embedded behavior (remote code execution); here nothing executes by default — the attacker poisons a shared object and *other* code trusts it, subverting authorization logic. The fix is server-side — the merge **guards the three keys** that reach a prototype (`__proto__`, `constructor`, `prototype`) and skips them. The one and only difference between `vulnerable/` and `fixed/` is that guard.

> **Theory primer:** Read [PortSwigger: Prototype pollution](https://portswigger.net/web-security/prototype-pollution)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — Node.js, no framework, no dependencies

This is the repo's first atom in **Node.js** rather than Python/Flask — prototype pollution is a JavaScript-idiomatic flaw (the shared `Object.prototype` and the prototype chain only exist in JS). The server uses the built-in `http` module directly: no Express, no framework, no merge library, **zero runtime dependencies**. The request body is read by hand and passed through an explicit `JSON.parse`, and the deep-merge is **written by hand** — so the one bad line is visible in the source, not buried in `node_modules`. `package.json` exists only to pin the Node `engines`; the base image is pinned by tag *and* digest.

## API only — no HTML, no browser

This atom has no web UI: no templates, no landing page, every response is JSON. That is deliberate — this prototype pollution lives in a JSON API that merges a request body into an object, and this atom models one. You drive it entirely from **Burp Suite (Repeater)** or `curl`; there is no browser track. Note that "prototype pollution" *also* exists as a client-side (browser) flaw — this atom is **not** that: the JavaScript here runs on the **server** (Node), the poisoned `Object.prototype` belongs to the Node process, and the proof is the HTTP response. `WALKTHROUGH.md` works exclusively from Burp.

## Run

From the repo root:

```bash
./atom up prototype-pollution
```

- Vulnerable API: `http://127.0.0.1:8026`
- Fixed API: `http://127.0.0.1:8126`

There is no landing page — the endpoints are `POST /settings` and `GET /me` (see `WALKTHROUGH.md`). Polluting `Object.prototype` is global to the process and **persists** until the process restarts, so capture the clean baseline (`GET /me` → `{"admin":false}`) **before** attacking. A restart (`./atom down prototype-pollution` then `up`, or `docker compose restart vulnerable`) resets the pollution. Stop with `./atom down prototype-pollution`. If you prefer raw Docker: `cd atoms/A08-data-integrity-failures/prototype-pollution && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8126 serves the same settings feature. Its merge **guards the three prototype-reaching keys** — `if (key === "__proto__" || key === "constructor" || key === "prototype") continue;` — and changes nothing else. Replay the walkthrough against it: `POST /settings` with `{"__proto__":{"isAdmin":true}}` is accepted (`200`), but the `__proto__` key is skipped, so `Object.prototype` is untouched and `GET /me` keeps returning `{"admin":false}`. A benign merge (`{"theme":"dark"}`) behaves identically on both apps; only the `__proto__` payload separates them. The one and only change from `vulnerable/` is that key guard; see [`DIFF.md`](./DIFF.md). This is **A08 — Software and Data Integrity Failures**: the merge must refuse the keys that reach a shared prototype.
