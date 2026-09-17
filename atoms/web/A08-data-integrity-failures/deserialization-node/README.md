# deserialization-node — Insecure deserialization

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Node.js API for classic insecure deserialization — remote code execution through the **`node-serialize`** library. The app is a "user preferences" API: it stores your preferences in a `prefs` cookie, serialized with `node-serialize` (an npm package) and base64-encoded. On every request it base64-decodes the cookie and calls `serialize.unserialize` on the string to rebuild the preferences. But you control your own cookie — and `node-serialize` does not deserialize just *data*: it can serialize JavaScript **functions**, and on `unserialize` it rebuilds a function by running **`eval`** on its source. A crafted cookie carrying a function tagged `_$$ND_FUNC$$_` whose body ends in `()` (a self-invoking function) makes `unserialize` run that code the moment it deserializes. The same request that reads your saved theme runs the attacker's command.

This is A08 — Software and Data Integrity Failures: the app trusts a serialized blob that crossed a trust boundary and reconstructs it with a format that carries behavior. It is the **Node face** of the flaw that `deserialization-pickle` shows in Python — same class, same ceiling (remote code execution), same kind of fix (a behavior-carrying format → a data-only one), but a different ecosystem and a different mechanism: there the dangerous deserializer is Python's stdlib `pickle` (triggered by `__reduce__`); here it is an npm package, `node-serialize` (triggered by an `eval`'d `_$$ND_FUNC$$_` function). The fix is not to validate or sign the cookie — it is to change the **format**: JSON carries data only, so `JSON.parse` has no code path to run. The one and only difference between `vulnerable/` and `fixed/` is `serialize.unserialize` vs `JSON.parse` — and the dependency that choice drags in.

> **Theory primer:** Read [PortSwigger: Insecure deserialization](https://portswigger.net/web-security/deserialization)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — Node.js, node-serialize as the object of study

This is a Node.js atom rather than Python/Flask, because insecure deserialization in Node is idiomatic to the JavaScript ecosystem: the danger arrives as an npm package that can (de)serialize functions. The server uses the built-in `http` module directly — no Express, no framework; the cookie is parsed by hand. The **only** runtime dependency is `node-serialize`, and it lives **only on the vulnerable side** — it is the object of study, pinned to an exact version and visible in `package.json`. The `fixed/` app has **zero** runtime dependencies: `JSON.parse` is stdlib. Note that `node-serialize` has no patched release — the fix is not "upgrade the library," it is to **stop using it** and go back to a data-only format. So `package.json` and the `Dockerfile` differ between the two sides (the vulnerable one installs `node-serialize`; the fixed one installs nothing), and that difference is part of the lesson. The base image is pinned by tag *and* digest.

## API only — no HTML, no browser

This atom has no web UI: no templates, no landing page, every response is JSON. That is deliberate — this deserialization flaw lives in a cookie that a JSON API reads and rebuilds, and this atom models one. You drive it entirely from **Burp Suite (Repeater)** or `curl`; there is no browser track. The JavaScript here runs on the **server** (Node), and the proof of execution is a side effect on the server — a marker file — read with `docker compose exec`, not something you see in the HTTP response. `WALKTHROUGH.md` works exclusively from Burp.

## Run

From the repo root:

```bash
./atom up deserialization-node
```

- Vulnerable API: `http://127.0.0.1:8027`
- Fixed API: `http://127.0.0.1:8127`

There is no landing page — the single endpoint is `GET /`, which sets the `prefs` cookie on the first visit and reads it back on every request (see `WALKTHROUGH.md`). Stop with `./atom down deserialization-node`. If you prefer raw Docker: `cd atoms/A08-data-integrity-failures/deserialization-node && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8127 serves the same "user preferences" feature and reads the same `prefs` cookie — but (de)serializes it as JSON (`JSON.stringify` / `JSON.parse`) instead of `node-serialize`, and drops the dependency entirely. Replay the exploit from `WALKTHROUGH.md` against it: the same malicious cookie that runs a command on the vulnerable app does nothing here — `JSON.parse` rebuilds only data (never a function, never an `eval`), the response is still `{"theme":"light"}`, and no command runs (the `/tmp/pwned` marker is never created). A benign cookie round-trips identically on both apps; only the `_$$ND_FUNC$$_` payload separates them. The one and only change from `vulnerable/` is the serialization format; see [`DIFF.md`](./DIFF.md). This is **A08 — Software and Data Integrity Failures**: never deserialize untrusted data with a format that carries behavior.
