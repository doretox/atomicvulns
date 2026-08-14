# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in exactly one thing: the **hashing primitive**. The vulnerable side stores and verifies with unsalted MD5; the fixed side uses bcrypt. That change touches `store_hash`, `verify`, the import, and the seed's comment — nothing else. `GET /`, the `POST /login` flow, the parameterized query, the schema, and the ports are byte-identical. The only other difference is in `requirements.txt` (see below).

## The fix — swap the primitive

```diff
 import os
-import hashlib
 import sqlite3
+import bcrypt
 from flask import Flask, request, jsonify
```

```diff
 def store_hash(password):
-    # VULNERABLE: MD5 is a fast, general-purpose hash, used here with NO salt. It is the
-    # WRONG PRIMITIVE for passwords. [...] a fast, unsalted hash is trivially RECOVERABLE.
-    return hashlib.md5(password.encode()).hexdigest()
+    # FIXED: bcrypt is a purpose-built password KDF -- deliberately SLOW (a tunable cost/work
+    # factor) and SALTED (bcrypt.gensalt() embeds a unique random salt in every hash). [...]
+    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


 def verify(password, stored):
-    return hashlib.md5(password.encode()).hexdigest() == stored
+    return bcrypt.checkpw(password.encode(), stored.encode())
```

`hashlib.md5(...).hexdigest()` — a fast, general-purpose hash with no salt — becomes `bcrypt.hashpw(..., bcrypt.gensalt())`, a slow, salted password KDF, verified with `bcrypt.checkpw`. The seed stores whatever `store_hash` returns, so on the fixed side the admin row is a bcrypt hash instead of an MD5; the login logic around it never changed. That is the whole fix.

## The cause is the primitive, not the algorithm

The bug is not "MD5 is broken." It is using a *fast, general-purpose* hash to store a password. Reaching for a different fast hash does not fix it — see the next two sections. bcrypt neutralizes the attack because of *what kind of function it is*: slow by design, and salted by design.

## "Just add a salt to the MD5" is not the fix

The tempting read: *the problem was the pre-computed table, so salt the hash and the table is useless.* Half right. A salt does defeat the rainbow table — a per-hash salt makes every stored hash unique, so no single pre-computed table applies. But that kills a **symptom**, not the **cause**. Salted MD5 is still *fast*: an attacker switches to a dictionary or brute-force attack, hashing guesses live — billions per second — against your salted hash, and a weak password still falls. The cause is the *speed*.

To be clear, the salt is not a trap or a mistake — it is a legitimate, necessary ingredient, and a proper password KDF already includes one (bcrypt salts every hash automatically; so does Argon2). The point is that a salt *alone*, bolted onto a fast hash, is not enough. A purpose-built KDF gives you salt **and** slowness together — which is why the fix is a new primitive, not a patch on the old one.

## "Use SHA-256, it isn't broken like MD5" is not the fix

Wrong for the same reason. SHA-256 has no known collision weakness — but it is a fast, general-purpose hash, just like MD5. Stored unsalted, a SHA-256 password hash falls to the exact same rainbow-table attack; salted, it still falls to a live dictionary attack, because it's fast. "Stronger" in the collision-resistance sense is not the property you need. The property you need is *slow and salted* — a password KDF (bcrypt, Argon2, scrypt, PBKDF2).

## The fixed side has nothing to attack — by inspection

You don't re-run the crack against the fixed hash to prove the fix; you can see it by inspection. The stored value is a salted bcrypt hash (`$2b$12$...`), not a 32-hex MD5 — an MD5 rainbow table wouldn't even accept it. And RainbowCrack cannot target bcrypt at all: `rtgen` only builds tables for unsalted hashes (`lm`, `ntlm`, `md5`, `sha1`, `sha256` — no bcrypt), because pre-computation is meaningless under a per-hash salt. There is no table to generate, and nothing to look the hash up in. The rainbow table isn't *slower* against bcrypt — it is *inapplicable*.

## The two sides differ in dependencies

Unusually for this repo, `vulnerable/requirements.txt` and `fixed/requirements.txt` are not identical:

```diff
 Flask==3.0.0
+bcrypt==4.2.1
```

The vulnerable side hashes with the standard library (`hashlib`, no dependency). The fixed side brings one library — `bcrypt` — because the fix *is* the primitive, and the right primitive is a purpose-built KDF you pull in, not something you hand-roll. The heart of the diff is still the `app.py` change; the dependency line just follows it.

## Impact, and the contrast with `jwt-weak-secret`

The impact is credential recovery leading to account takeover: the recovered password is the victim's real one, and reused passwords carry the compromise to other systems. It is not RCE.

This atom's sibling, [`jwt-weak-secret`](../jwt-weak-secret/), is also **A02 — Cryptographic Failures**, and also cracks a cryptographic artifact offline. But it differs on every other axis, and the contrast is the lesson:

| | `jwt-weak-secret` | `crypto-weak-hash` |
|---|---|---|
| Artifact cracked offline | a **signing secret** (HMAC key) | a stored **password hash** |
| What the crack gives you | the key → **forge** your own tokens | the victim's **real password** → log in as them |
| Property broken | integrity / authenticity | confidentiality of the stored secret |
| Technique | **dictionary** — hash each guess live | **rainbow table** — pre-compute the work once |
| The fix | swap a weak **value** (the secret) | swap the **primitive** (fast unsalted hash → slow salted KDF) |

One cracks a secret to *forge*; the other recovers a password to *impersonate*. One hashes guesses live; the other pre-computes the work up front. Same category, opposite in cause, consequence, and technique.
