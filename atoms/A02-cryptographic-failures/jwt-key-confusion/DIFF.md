# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in **one place — the `verify` helper** (plus the four stdlib imports and the one helper it needed). Every other byte is identical: the shared imports, `authenticate`, all four routes (`/login`, `/jwks`, `/api/profile`, `/admin/users`), the `USERS` data, how the RSA keys are loaded, the `Dockerfile`, and `requirements.txt`. Both services ship the **same** committed keypair (`keys/private.pem`, `keys/public.pem`), byte-for-byte. There are no templates (this atom is API-only).

```diff
 import os
-import json
-import hmac
-import hashlib
-import base64
 import jwt
 from flask import Flask, request, jsonify, abort
@@
-def _b64url_decode(seg):
-    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))
-
-
 def verify(token):
-    # VULNERABLE: the server reads alg from the token's OWN header and picks the
-    # verification family from it. RS256 -> RSA-verify with the public key (safe, correct).
-    # HS256 -> HMAC-verify using the SAME public-key bytes as the secret (!). ...
-    alg = jwt.get_unverified_header(token).get("alg")
-    if alg == "HS256":
-        header_b64, payload_b64, sig_b64 = token.split(".")
-        signing_input = f"{header_b64}.{payload_b64}".encode()
-        expected = hmac.new(PUBLIC_KEY_PEM, signing_input, hashlib.sha256).digest()
-        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
-            raise ValueError("bad HS256 signature")
-        return json.loads(_b64url_decode(payload_b64))
-    if alg == "RS256":
-        return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
-    raise ValueError("unsupported alg")
+    # FIXED: stop asking the token which algorithm to use. Pin RS256 and let PyJWT enforce
+    # it — a token with alg:HS256 is rejected (HS256 isn't in the allowlist). ...
+    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
```

The vulnerable `verify` reads the token's own `alg` header and branches to a validator; the fixed `verify` deletes the branch and pins the algorithm, letting PyJWT enforce it. The four stdlib imports and the `_b64url_decode` helper existed only to hand-roll the HS256 branch — they go with it.

## The same fix shape as `jwt-none-alg`

This is the core of the diff, so start here. `jwt-none-alg`'s fix *removed* a branch — the `if header["alg"] == "none"` escape hatch that skipped verification. This fix removes a branch too — the `if alg == "HS256"` path that verified with the wrong algorithm — and pins the allowlist. **Both fixes are the same move: stop letting the token's `alg` decide how the token is validated.**

`jwt-none-alg`'s rule is unchanged here:

> Pass `algorithms=` as a positive list of exactly the algorithms this endpoint should accept, and never branch off `header["alg"]` to choose how to validate. The header is data, not policy.

The vulnerable `verify` violates that rule literally — its first line is `jwt.get_unverified_header(token).get("alg")`, and the whole function is the branch that follows. The fix is one line, and it is the same line `jwt-none-alg`'s fix landed on: `jwt.decode(token, KEY, algorithms=[...])`, with the algorithm decided by the server, before the token is read.

`jwt-none-alg`'s own walkthrough named this attack in advance — *"algorithm-confusion attacks where the server is tricked into using the wrong key"* — as another way to lose the same game. This atom is that flavor, made real. The only difference is the mechanism: `jwt-none-alg` skips verification (`none`); this atom runs verification, but with the wrong algorithm family.

## Contrast with `jwt-weak-secret` — code, not a value; and nothing is weak

`jwt-weak-secret`'s fix changed a **value** — a weak secret for a strong one — without touching one line of logic. This fix changes **code**: it deletes a branch. That's the visible difference, but the deeper one is this: in `jwt-weak-secret` something was genuinely *weak* (the secret had no entropy), and the attack was to *guess* it. Here **nothing is weak** — the RSA key is a strong 2048-bit key, the forged signature verifies for real, HMAC-SHA256 is sound — and it still falls. The attacker guesses nothing; they use the *public* key, exactly as published, under an algorithm the server should never have accepted. That is what makes key confusion the most insidious of the three.

## Why the vulnerable server verifies by hand (and why it has to)

A fair question: why does the vulnerable `verify` hand-roll an HMAC with `hmac`/`hashlib` instead of just calling PyJWT? Because **modern PyJWT blocks this attack by default, and a naive call would not be vulnerable.** Passing an RSA public key (a PEM containing `-----BEGIN PUBLIC KEY-----`) to an HMAC algorithm raises:

```
jwt.exceptions.InvalidKeyError: The specified key is an asymmetric key or x509
certificate and should not be used as an HMAC secret.
```

So `jwt.decode(token, public_key_pem, algorithms=["HS256", "RS256"])` — the "obvious" vulnerable version — would abort on the HS256 path, not confirm the forgery. To reproduce the real bug on a patched library, the server has to bypass that guard, which is exactly what hand-rolling the HMAC does.

This is not a strawman. Key confusion lives, in the wild, in precisely this kind of code: home-grown auth middleware, JWT libraries in other languages that lack this guard, and wrappers that branch on `alg` to "support both RS256 and HS256." **The library's refusal is itself the lesson** — modern libraries mitigate this, and the bug survives in whoever re-implements verification by hand. (The same refusal is why the forge in `WALKTHROUGH.md` can't be a PyJWT one-liner either: the attacker hand-rolls the HMAC too.)

## The asymmetry collapse, visible in the code

Look at where `PUBLIC_KEY_PEM` appears in the vulnerable `verify`. It's in **both** branches:

- under `RS256`, as the RSA **verification key** — harmless, correct, exactly what it's for;
- under `HS256`, as the **HMAC secret** — catastrophic, because to verify an HMAC is to be able to sign one.

Same constant, same bytes, two branches, two completely different security meanings. That is the whole vulnerability sitting in two lines: the moment the server agreed to treat a public verification key as a shared secret, the asymmetry that made the key safe to publish collapsed.

## This is A02 — and it doesn't `grep`

Like its JWT siblings, the bug isn't a dangerous call you can search for. `jwt.decode(token, key, algorithms=["RS256"])` — the fixed line — is exactly what *correct* code looks like. There is no `eval`, no string-built SQL, no `|safe`. The bug is the hand-written branch beside it, and the misplaced trust inside it. You catch it by reading the verification logic and asking one question: **"who chooses the algorithm — the server, or the token?"** If the answer is the token, you have found it. The RSA and the HMAC are both intact; the root cause is a **logic error**, not broken cryptography — which is why this sits in A02 (Cryptographic Failures) as a *cryptographic-configuration* failure, the same shelf as `jwt-none-alg`.

## `403`, not `404`

`GET /admin/users` returns **`403`** for a valid non-admin token — "authenticated, but not allowed." There's no enumeration oracle to hide: the endpoint is a fixed resource, not an object indexed by a sequential id. (That was `bola-rest`'s reason for `404`; no such id exists here, so `403` is the honest status. Don't copy the `404` reflexively.)

## `/jwks` publishes the public key on purpose — and the fix leaves it alone

Serving the RSA public key at `/jwks` is **correct and by design**: clients need it to verify tokens, and a public key is safe to publish. It is *not* the bug, and the fix does not touch it — the key stays the same, still 2048-bit, still served. The bug was never publishing the key; it was the vulnerable server later accepting that same key as an HMAC secret. The bytes `/jwks` serves are the exact bytes the vulnerable HS256 branch feeds to `hmac.new`, which is why the forgery matches — the attack's entire "same bytes" premise. The fix closes the branch that misused the key, not the endpoint that publishes it.
