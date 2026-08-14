# crypto-weak-hash — Insecure password storage (weak hashing)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for the most common password-storage failure: the app stores each user's password as an **unsalted MD5 digest**. A hash is one-way — you cannot decrypt it — but MD5 is a *fast, general-purpose* hash, and used without a salt the same password always produces the same digest. That is the wrong primitive for passwords: once a hash leaks (say, in a database dump), it is trivially **recoverable**. You don't invert the hash — you guess passwords, hash them, and compare, at scale. This atom does it with a **rainbow table**: a pre-computed hash→password table that covers an entire keyspace. The recovered password logs you straight in as the victim.

This is the sibling of [`jwt-weak-secret`](../jwt-weak-secret/), and the contrast is the lesson. Both crack a cryptographic artifact offline — but there you crack a *signing secret* (by dictionary) to **forge** your own tokens; here you recover a *stored password* (by rainbow table) to **log in as the real user**. Different artifact, different consequence, different technique: a signing secret is integrity, a stored password hash is confidentiality; a dictionary attack hashes each guess live, a rainbow table pre-computes the work once. The fix is not "a stronger hash" and not "just add a salt" — it is a different **primitive**: bcrypt, a slow, salted password KDF (key derivation function).

> **Theory primer:** Read [OWASP: Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
> before working through this atom. The atoms in this repo show *how* a
> vulnerability happens in code; the cheat sheet explains *what* secure
> password storage is — slow, salted KDFs — and why it matters. (PortSwigger's
> Web Security Academy, this repo's usual primer source, is attack-focused and
> has no conceptual page on password storage, so this atom points to OWASP's
> canonical guidance instead.)

## Stack note — single-container SQLite, and the two sides differ in dependencies

Each side is a single Flask container with its own ephemeral `lab.db`, seeded at boot — there is no separate datastore. One thing is unusual for this repo: `vulnerable/` and `fixed/` do **not** share a `requirements.txt`. The vulnerable side hashes with the standard library (`hashlib`); the fixed side adds one dependency — `bcrypt`. The fix *is* the primitive, and the primitive brings a library.

## API only — no HTML, no browser

There is no web UI: no templates, every response is JSON. You drive this atom from **Burp Suite (Repeater)** to prove the login, and a **terminal** to run the offline crack with RainbowCrack (`rtgen` / `rtsort` / `rcrack`) — the same split you'd use in a real engagement, because cracking a hash is something Burp can't do. There is no browser track.

## The starting point — a leaked hash

The attack assumes you already hold the `users` table from a **database dump** — however it leaked. The app never exposes the hash over HTTP (that would be a second, separate vulnerability); `WALKTHROUGH.md` hands you the dumped `admin:<md5>` line as the starting point. From there, everything is offline.

## Run

From the repo root:

```bash
./atom up crypto-weak-hash
```

- Vulnerable API: `http://127.0.0.1:8031`
- Fixed API: `http://127.0.0.1:8131`

There is no landing page beyond a JSON banner at `/` — the entry point is `POST /login` (see `WALKTHROUGH.md`). Stop with `./atom down crypto-weak-hash`. If you prefer raw Docker: `cd atoms/A02-cryptographic-failures/crypto-weak-hash && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation: Burp confirms the login, the terminal builds a rainbow table (you watch `rtgen` do the pre-computation) and recovers the password, then the recovered password logs you in. No browser track.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched API on port 8131 stores the **same** password (`adm1n`) as a **salted bcrypt hash** (`$2b$...`) instead of an unsalted MD5. Same login logic, same endpoints — only the storage primitive changes. Against a bcrypt hash the rainbow table is not "slower," it is **inapplicable**: a salted hash has no pre-computed table to build (RainbowCrack doesn't even offer bcrypt), so there is nothing to look the hash up in. bcrypt is also deliberately slow, raising the cost of *any* guessing attack. See [`DIFF.md`](./DIFF.md) for why "just add a salt" and "use SHA-256" are both the wrong fix.
