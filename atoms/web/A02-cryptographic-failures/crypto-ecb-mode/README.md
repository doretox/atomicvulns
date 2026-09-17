# crypto-ecb-mode — Encryption with an insecure mode of operation

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for the classic block-cipher **mode** failure. The app hands you a session **badge** — a token carrying your identity and role — that it encrypts with **AES in ECB mode**. AES is a *block cipher*: it encrypts fixed-size 16-byte blocks, and a **mode of operation** is the rule for chaining those blocks across a longer message. ECB (Electronic Codebook) is the naive one — it encrypts each 16-byte block *independently* with the same key. Two consequences follow, and both are exploitable: identical plaintext blocks become identical ciphertext blocks (the pattern leaks), and — because the blocks are independent — you can **cut and paste** ciphertext blocks between badges to forge a plaintext the server never issued. You escalate `role=user` to `role=admin` without ever knowing the key.

This is the sibling of [`crypto-weak-hash`](../crypto-weak-hash/), and the contrast is the lesson. Both are **A02 — Cryptographic Failures** and both "look like crypto," but there you attack a one-way *hash* of a stored password and **recover** the input by pre-computation (a rainbow table); here you attack a reversible *cipher* in a broken *mode* and **forge** a new plaintext by rearranging blocks — nothing is recovered and the key is never broken. It also shares its goal — forging an authority token to escalate privilege — with the JWT atoms [`jwt-none-alg`](../jwt-none-alg/) and [`jwt-key-confusion`](../jwt-key-confusion/): there the forge attacks the token's *signature*; here it attacks the token's *encryption mode*. The fix is not "switch ECB for CBC" — it is an **authenticated** mode (AES-GCM) that detects any tampered block and rejects the badge.

> **Theory primer:** Read [OWASP: Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
> before working through this atom — its "Cipher Modes" section is the lesson:
> avoid ECB, prefer authenticated modes (GCM). The atoms in this repo show *how* a
> vulnerability happens in code; the cheat sheet explains *what* secure encryption
> looks like and why it matters. (PortSwigger's Web Security Academy, this repo's
> usual primer source, has no conceptual page on cipher modes, so this atom points
> to OWASP's canonical guidance instead.)

## Stack note — single-container, no database, identical dependencies

Each side is a single Flask container with no datastore: the badge is self-contained (the server encrypts your identity and role into it), so there is nothing to seed and no session to persist — the same stateless shape as the JWT atoms. And unlike `crypto-weak-hash`, whose fix pulled in a new library, here `vulnerable/` and `fixed/` share an **identical** `requirements.txt` (Flask + pycryptodome). The fix is one line of code — the cipher mode — not a dependency.

## API only — no HTML, no browser

There is no web UI: no templates, every response is JSON. You drive this atom entirely from **Burp Suite (Repeater + Decoder)** — read the badge from a login response, cut and rearrange its ciphertext blocks, and replay it. The proof is the HTTP response (`GET /me` answering as admin). There is no offline tool — nothing is cracked, the key is never touched — and no browser track.

The badge is **hex-encoded**, so each 16-byte block is exactly 32 hex characters. Block boundaries line up on the character, which keeps the cut-and-paste doable by hand in Repeater — no Base64 round-trip needed.

## Run

From the repo root:

```bash
./atom up crypto-ecb-mode
```

- Vulnerable API: `http://127.0.0.1:8032`
- Fixed API: `http://127.0.0.1:8132`

There is no landing page beyond a JSON banner at `/` — the entry points are `POST /login` (get a badge) and `GET /me` (spend it), documented in `WALKTHROUGH.md`. Stop with `./atom down crypto-ecb-mode`. If you prefer raw Docker: `cd atoms/A02-cryptographic-failures/crypto-ecb-mode && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation in Burp: see the pattern leak (two identical ciphertext blocks), lift an `admin` block out of a login response, splice it over the `user` block, and watch `GET /me` treat the forged badge as admin. Then the same badge is rejected under GCM. No browser.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8132 encrypts the badge with **AES-GCM**, an authenticated mode — same key, same endpoints, only the mode changes. GCM adds a fresh per-message **nonce** (so two identical badges no longer look identical — the pattern stops leaking) and an authentication **tag** that binds the ciphertext. The spliced badge that logged you in as admin on 8032 fails the tag check and is rejected with `400` **before the role is ever read**. See [`DIFF.md`](./DIFF.md) for why "just switch to CBC" is a real but partial improvement — not the fix — and why the problem was never the key or AES itself.
