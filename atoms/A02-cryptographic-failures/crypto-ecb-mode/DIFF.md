# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in exactly one thing: the **cipher mode**. The vulnerable side encrypts the badge with AES-ECB; the fixed side uses AES-GCM. That change touches the padding import, `issue_badge`, and `read_badge` — nothing else. `GET /`, `POST /login`, `GET /me`, the `email=...&role=...` parse, and the ports are byte-identical. And unlike `crypto-weak-hash`, the two sides share an **identical** `requirements.txt` (see below).

## The fix — swap the mode

```diff
 import os
 from Crypto.Cipher import AES
-from Crypto.Util.Padding import pad, unpad
 from flask import Flask, request, jsonify
```

```diff
 def issue_badge(email, role):
     plaintext = f"email={email}&role={role}".encode()
-    cipher = AES.new(KEY, AES.MODE_ECB)
-    return cipher.encrypt(pad(plaintext, AES.block_size)).hex()
+    cipher = AES.new(KEY, AES.MODE_GCM)
+    ct, tag = cipher.encrypt_and_digest(plaintext)
+    return (cipher.nonce + tag + ct).hex()


 def read_badge(token):
-    cipher = AES.new(KEY, AES.MODE_ECB)
-    plaintext = unpad(cipher.decrypt(bytes.fromhex(token)), AES.block_size)
+    raw = bytes.fromhex(token)
+    nonce, tag, ct = raw[:16], raw[16:32], raw[32:]
+    cipher = AES.new(KEY, AES.MODE_GCM, nonce=nonce)
+    plaintext = cipher.decrypt_and_verify(ct, tag)
     return dict(kv.split("=", 1) for kv in plaintext.decode().split("&"))
```

`AES.MODE_ECB` — deterministic, block-independent, and unauthenticated — becomes `AES.MODE_GCM`, an authenticated mode. On write, `encrypt_and_digest` returns an authentication **tag** and the cipher generates a fresh **nonce**, both packed alongside the ciphertext. On read, `decrypt_and_verify` recomputes the tag and **raises** if a single byte was altered — so the spliced badge is rejected in the `except` handler (`400`) before the role is ever parsed. ECB needed PKCS#7 padding (`pad`/`unpad`); GCM is a stream mode and needs none, so that import goes away. The endpoints around the cipher never changed. That is the whole fix.

## The cause is the mode, not the key or AES

The bug is not "the key is weak" and not "AES is broken." The key is a dummy constant, **identical on both sides**, and the attack never touches it — the forge is pure block rearrangement. AES itself is sound: the fixed side is the *same* AES with the *same* key, and the attack dies. What changed is only *how the blocks are chained and authenticated* — the mode. Reaching for a longer key or a different cipher would fix nothing.

## "Just switch to CBC" is not the fix

The tempting read: *the problem was the leaking pattern and the clean cut-and-paste, so switch ECB for CBC and both go away.* Half right, and worth being honest about. CBC (Cipher Block Chaining) XORs each plaintext block with the previous ciphertext block before encrypting, so identical plaintext blocks no longer produce identical ciphertext — the pattern **stops leaking** (no more penguin) — and the blocks are no longer independent, so the clean copy-a-block-verbatim splice **stops working**. That is a real improvement, not a trap.

But it is not the fix, because CBC leaves the badge **unauthenticated**. Nothing about CBC lets the server *detect* that a token was altered — the ciphertext still carries no proof of integrity, so a tampered badge remains tamperable by other means. Leaving ECB is **necessary but not sufficient**. The deeper lesson: a hand-encrypted authority token with no authentication is fragile in *any* mode. The answer is not a different unauthenticated mode — it is an **authenticated** one (AEAD: GCM, or CCM), where a tag proves the ciphertext is exactly what the server issued. Confidentiality was never the missing property; integrity was.

## Deterministic vs. randomized — the nonce

ECB has no IV or nonce, so it is **deterministic**: the same plaintext always encrypts to the same ciphertext. That is precisely what leaks the pattern (identical blocks show through) and what lets an attacker recognize and reuse a block. GCM takes a unique **nonce** per message, so the same plaintext encrypts differently every time — issue the same badge twice and the two tokens share no bytes. Determinism is a property of the mode, and it is half of why ECB is unsafe for anything structured.

## The two sides share dependencies

Unlike `crypto-weak-hash`, whose fix pulled in a new library (`bcrypt`), here `vulnerable/requirements.txt` and `fixed/requirements.txt` are **identical**:

```
Flask==3.0.0
pycryptodome==3.21.0
```

Both ECB and GCM come from the same `pycryptodome` already in use. The fix is a one-line mode change in the code, not a dependency — a good reminder that fixing a crypto flaw is usually about *using the primitive correctly*, not installing something new.

## Impact, and the contrast with `crypto-weak-hash`

The impact is token forgery leading to privilege escalation: a badge that decrypts to `role=admin`, minted with no admin credential and no key. It is not RCE, and it is not key recovery — the ceiling is whatever the forged role unlocks.

This atom's sibling, [`crypto-weak-hash`](../crypto-weak-hash/), is also **A02 — Cryptographic Failures**, and both "look like crypto." But they are opposites in mechanism, and the contrast is the lesson:

| | `crypto-weak-hash` | `crypto-ecb-mode` |
|---|---|---|
| Primitive / artifact | a one-way **hash** (MD5) of a stored password | a reversible **cipher** (AES) in a broken **mode** (ECB) |
| What the attacker does | **recovers** the original password (the input) | **forges** a new plaintext (rearranges blocks) |
| Technique | **rainbow table** — pre-compute hash→password | **cut-and-paste** — splice ciphertext blocks |
| Is the key/secret broken? | the password is recovered by mass guessing | **no** — the key is never touched |
| Root cause | wrong **primitive** (fast, unsalted hash) | wrong **mode** (deterministic independent blocks + no authentication) |
| The fix | swap the primitive (fast hash → slow salted KDF) | swap the mode (ECB → authenticated AEAD/GCM) |

One recovers a secret by pre-computing; the other forges by rearranging structure. It also shares its *goal* — forging an authority token to escalate — with the JWT atoms [`jwt-none-alg`](../jwt-none-alg/) and [`jwt-key-confusion`](../jwt-key-confusion/): there the forge attacks the token's signature, here it attacks the token's encryption mode. Same category, different surface.
