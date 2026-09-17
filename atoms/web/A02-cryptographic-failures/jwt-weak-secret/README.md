# jwt-weak-secret — JWT weak signing secret (brute-forced)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for the second kind of JWT failure: a signing secret weak enough to brute-force. The API signs its tokens with HS256 and **verifies them correctly** — there is no `alg:none` branch, the `algorithms=["HS256"]` allowlist is enforced, a tampered signature is rejected with `401`. None of the cryptography is broken. The one flaw is the **value** of the secret: it is a dictionary word. An attacker captures a legitimate token, brute-forces the HS256 secret against a wordlist, and — holding the key — forges a token with `role: admin` that the server accepts as genuine, because it *is* genuine: signed with the real key.

This is the sibling of [`jwt-none-alg`](../jwt-none-alg/), and the contrast is the lesson. There, **the lock didn't lock** — the server skipped signature verification when the token asked it to (`alg:none`). Here, **the lock locks, correctly — but the key was written on a sticky note.** In `jwt-none-alg` you *strip* the signature off; here you *re-make* it, perfectly valid, with the stolen secret. "Signed" is not "secure": a signature is only as strong as its key, and a key pulled from a wordlist is no key at all. `jwt-none-alg` even points here — its walkthrough names *"weak shared secrets that survive a brute-force"* as another way to lose the same game. This atom is that game.

> **Theory primer:** Read [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters. (Its "Brute-forcing secret keys" section is this atom.)

## Stack note — no database

Like `jwt-none-alg`, this atom keeps its data in plain Python structures rather than a database. A weak secret doesn't depend on the storage layer — the JWT is stateless, and the server keeps only the `SECRET` it verifies with. The surface is kept minimal so the one weak value is obvious.

## API only — no HTML, no browser

There is no web UI: no templates, no landing page, every response is JSON. JWT bugs live in API contexts — bytes you craft and send on `Authorization: Bearer ...`. You drive this atom from **Burp Suite (Repeater)** and a **terminal** — the crack and the forge happen at the terminal, the way they would in a real engagement. There is no browser track; `WALKTHROUGH.md` works from Burp plus the terminal.

## Authentication, simulated

Real authentication (passwords, hashing, login sessions) is out of scope — that belongs in a dedicated authentication atom. This lab fakes it with `POST /login`, which returns an **HS256-signed JWT** carrying `{"sub": "...", "role": "user"}`. There is no password, and **`role` is always `user`** — the server never mints an admin token. That is the whole point: you can't log in as admin, you have to *forge* it. Three endpoints:

- `POST /login` — get a legitimate `role: user` token.
- `GET /api/profile` — any valid token; returns your claims (your baseline, and where you capture the JWT).
- `GET /admin/users` — requires `role: admin`; your `user` token gets `403`, a forged `admin` token gets `200`.

## Run

From the repo root:

```bash
./atom up jwt-weak-secret
```

- Vulnerable API: `http://127.0.0.1:8013`
- Fixed API: `http://127.0.0.1:8113`

There is no landing page — the entry point is `POST /login` (see `WALKTHROUGH.md`). Stop with `./atom down jwt-weak-secret`. If you prefer raw Docker: `cd atoms/A02-cryptographic-failures/jwt-weak-secret && docker compose up --build`.

The atom ships a small curated `wordlist-sample.txt` (~1000 common passwords) at its root for the crack step — see the walkthrough.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation: Burp captures and replays the token, the terminal cracks the secret (John the Ripper) and forges the admin token. No browser track.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8113 is **byte-identical except for one line** — the `SECRET` constant. It swaps the weak `changeme123` for a 43-character, high-entropy value from `secrets.token_urlsafe(32)`. Same algorithm, same verification, same endpoints. Run the same John the Ripper crack against a token from the fixed app and it finds nothing (the strong secret is in no wordlist); replay the admin token you forged against the vulnerable app and it returns **401** (the signature no longer matches). The security lived entirely in the value of the secret — not in one line of logic.
