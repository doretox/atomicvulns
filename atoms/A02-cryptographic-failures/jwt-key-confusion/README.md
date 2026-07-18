# jwt-key-confusion — JWT algorithm confusion (RS256 → HS256)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for the third kind of JWT failure: **algorithm confusion**. The API signs its tokens with **RS256** — asymmetric crypto, where a **private** key signs and a **public** key verifies — and publishes that public key at `GET /jwks`, exactly as a real service would so clients can verify tokens. **Nothing here is weak.** The RSA key is a robust 2048-bit key; the signature is mathematically sound. The one flaw is that the server decides *how* to verify each token by trusting the `alg` field the **token itself** declares: `alg:RS256` → verify with RSA, `alg:HS256` → HMAC-verify **using that same public key as the secret**. Because the public key is public, an attacker forges an `alg:HS256` token with `role: admin`, HMAC-signs it with the public key's exact bytes, and the server accepts it — the signature matches, because it is made with the very key the server verifies with.

This atom **closes the JWT trilogy**, and it is a sibling of both earlier JWT atoms — in two different ways:

- [`jwt-none-alg`](../jwt-none-alg/) — **the lock didn't lock** (`alg:none`, verification skipped).
- [`jwt-weak-secret`](../jwt-weak-secret/) — **the lock locked, but the key was on a sticky note** (HS256, dictionary secret, brute-forced).
- **This atom — the lock locks, the key is strong, the signature checks out — and it still opens**, because the server lets the *token* choose the algorithm.

It shares its **fix shape** with `jwt-none-alg`: both bugs are the server trusting the token's `alg`, and both fixes are the same move — stop branching on the header, pin the algorithm allowlist, and let the library impose it. The header is data, not policy. It shares its **impact** with `jwt-weak-secret`: vertical privilege escalation (`role: user` → forged `role: admin`). What changes is the mechanism — in `jwt-weak-secret` something was *weak*; here nothing is. Key confusion is not broken cryptography (the RSA and the HMAC are both intact); it is a **logic error** in how the verification was written.

> **Theory primer:** Read [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt#jwt-algorithm-confusion)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters. (Its "JWT algorithm confusion" section is this atom.)

## Stack note — no database

Like both JWT siblings, this atom keeps its data in plain Python structures rather than a database. Algorithm confusion doesn't depend on the storage layer — the JWT is stateless, and the server keeps only the RSA keypair it signs and verifies with. The surface is kept minimal so the one alg-controlled branch is obvious.

## API only — no HTML, no browser

There is no web UI: no templates, no landing page, every response is JSON (except `GET /jwks`, which serves the public key as PEM). JWT bugs live in API contexts — bytes you craft and send on `Authorization: Bearer ...`. You drive this atom from **Burp Suite (Repeater)** and a **terminal** — the forge happens at the terminal, the way it would in a real engagement. There is no browser track; `WALKTHROUGH.md` works from Burp plus the terminal.

## Authentication, simulated

Real authentication (passwords, hashing, login sessions) is out of scope. This lab fakes it with `POST /login`, which returns an **RS256-signed JWT** carrying `{"sub": "...", "role": "user"}`. There is no password, and **`role` is always `user`** — the server never mints an admin token. That is the whole point: you can't log in as admin, you have to *forge* it. Four endpoints:

- `POST /login` — get a legitimate `role: user` token (signed with the RSA private key).
- `GET /jwks` — the RSA **public** key, in PEM. Public by design (clients verify with it) — and the attacker's forging material.
- `GET /api/profile` — any valid token; returns your claims (your baseline, and where you capture the JWT).
- `GET /admin/users` — requires `role: admin`; your `user` token gets `403`, a forged `admin` token gets `200`.

## Keys — a DUMMY lab RSA pair

The atom ships a **fixed, committed 2048-bit RSA keypair** (in `vulnerable/keys/` and `fixed/keys/`, byte-identical). It is a **DUMMY lab key — never a real one.** The private key is committed *only* because this is an intentionally-vulnerable lab; a fixed pair keeps the walkthrough deterministic (you get the exact tokens shown). Never reuse it for anything real. Only the **public** key is ever served (`/jwks`); the private key never leaves the process.

## Run

From the repo root:

```bash
./atom up jwt-key-confusion
```

- Vulnerable API: `http://127.0.0.1:8014`
- Fixed API: `http://127.0.0.1:8114`

There is no landing page — the entry point is `POST /login` (see `WALKTHROUGH.md`). Stop with `./atom down jwt-key-confusion`. If you prefer raw Docker: `cd atoms/A02-cryptographic-failures/jwt-key-confusion && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation: Burp logs in, captures the token, and grabs the public key; the terminal forges the admin token; Burp replays it. No browser track.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8114 is **byte-identical except for the `verify` helper** (and the imports it needs). Instead of reading the token's `alg` and branching, it pins `jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])` and lets PyJWT enforce it — the exact same fix shape as `jwt-none-alg`. Replay the forged `alg:HS256` token against `GET /admin/users` on port 8114 and it returns **401** (HS256 isn't in the allowlist); a legitimate RS256 token still gets `200` on `/api/profile` and `403` on `/admin/users`. Same keypair, same endpoints — the token just no longer gets to choose how it's verified.
