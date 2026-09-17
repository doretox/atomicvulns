# jwt-none-alg — JWT alg=none signature bypass

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for the canonical JWT signature-bypass bug. The app authenticates with HS256-signed tokens, but its decode helper has a leftover branch that accepts tokens whose `alg` header reads `"none"` — an unsigned token format the JWT spec defines for "no integrity needed". An attacker rewrites the header to `alg=none`, flips `role` to `admin`, drops the signature, and the server happily reads the forged claims as authentic.

This is the first atom in the project where the bug is a **cryptographic configuration failure**, not an input or logic failure. None of the cryptography is broken — the server just chose, on one branch, to do *no* cryptography. The vulnerability is the gap between "looks like a security boundary" and "is a security boundary".

> **Theory primer:** Read [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## API-only with a context page

Most JWT bugs only make sense in API contexts — there's no form to fill, no link to click, just bytes you craft and send on `Authorization: Bearer ...`. This atom keeps that shape. The home page (`/`) exists only to issue you a starter token (signed under the seed user `alice`, role `user`) so you have something to inspect before forging. Real exploitation happens against `/admin` and `/me` from Burp Repeater. There is no login form — authentication ceremony is out of scope here, the same way it was in `idor-numeric-id`.

## Run

From the repo root:

```bash
./atom up jwt-none-alg
```

- Vulnerable app: <http://127.0.0.1:8005/>
- Fixed app: <http://127.0.0.1:8105/>

Stop with `./atom down jwt-none-alg`. If you prefer raw Docker: `cd atoms/A02-cryptographic-failures/jwt-none-alg && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary). Includes an "Anatomy of a JWT" primer for the first time you decode one by hand.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8105 keeps the exact same routes and the exact same SECRET, so a token issued by the vulnerable app is accepted by the fixed app and vice versa — what differs is which tokens get rejected. Replay the forged `alg=none` token from `WALKTHROUGH.md` against `GET /admin` on port 8105: same bytes, same path, response is **401 Unauthorized** instead of the admin panel. The fix is one line of code.
