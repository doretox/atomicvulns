# idor-uuid-guessable — Insecure Direct Object Reference (guessable UUID)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for IDOR where the object id is a UUID. The app serves private receipts through `GET /receipt/<uuid>`, and the developer treats the "unguessable" UUID as the access control — whoever has the link sees the receipt, and nothing else guards it. The view never checks whether the receipt belongs to the caller, so it is the exact same bug as `idor-numeric-id`: a missing ownership check. Swapping the integer id for a UUID changed how hard the id is to *guess*, not whether the server *checks* who is asking.

This atom is the maturation of `idor-numeric-id`, and it lands two lessons of equal weight. **First:** a hard-to-guess identifier is not an access control — even a perfectly random UUIDv4 is readable by anyone who obtains the id, because the missing check, not the id's shape, was always the bug. **Second:** this id isn't even unpredictable — it is a UUIDv1, which packs a timestamp and the host's node, so with a stable clock sequence it is *reconstructible* from data the app already exposes (a receipt of your own to recover the generator's fingerprint, plus the victim's microsecond `issued_at` shown on the dashboard). The fix that matters is the ownership check; switching to UUIDv4 is defense-in-depth, not the correction.

> **Theory primer:** Read [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — no database

Like `idor-numeric-id`, this atom keeps its data in a plain Python dict rather than SQLite. IDOR doesn't depend on the storage layer: the bug is a missing authorization check above whichever store you use. The surface is kept minimal so the missing line is obvious. The storage choice in each atom follows the surface of the bug — not the other way around.

## Authentication, simulated

Real authentication (login forms, sessions, password hashing) is out of scope here — that ceremony belongs in a dedicated authentication atom. This lab fakes "who is logged in" with a single header, `X-User-ID`, reusing the convention from `idor-numeric-id`. Two users are seeded, with explicit roles:

- `mallory` — the attacker (you). The default caller when the header is absent, and the one who mints her own receipt.
- `alice` — the victim. Her receipt is seeded at startup — the target you should not be able to read.

## Run

From the repo root:

```bash
./atom up idor-uuid-guessable
```

- Vulnerable app: <http://127.0.0.1:8011/>
- Fixed app: <http://127.0.0.1:8111/>

Stop with `./atom down idor-uuid-guessable`. If you prefer raw Docker: `cd atoms/A01-broken-access-control/idor-uuid-guessable && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary) and browser (secondary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8111 serves the same receipts feature. It adds one line — an ownership check that returns **403 Forbidden** unless the receipt belongs to the calling `X-User-ID` — and, as defense-in-depth, mints ids with `uuid4` instead of the reconstructible `uuid1`. Replay the walkthrough against it: reading your own receipt as its owner returns 200, but reading it as anyone else returns 403, and the reconstruction can't even begin against a v4 id. The dashboard still exposes `issued_at` exactly as before — proof that the metadata leak was never the bug; the ownership check makes it inert.
