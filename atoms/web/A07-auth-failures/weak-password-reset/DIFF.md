# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in one thing: the **reset-token generator**, and the token lifecycle that follows from it. The vulnerable side generates the token with `random` seeded from the clock; the fixed side uses `secrets`, and makes the token single-use and short-lived. That touches the import, the generator, and the two lines that store and look up the token. `GET /`, `POST /login`, the parameterized queries, the schema, the seed, the "email" delivery, and the ports are byte-identical. `requirements.txt` is identical too (see the last section).

## The fix — swap the generator

```diff
 import os
 import time
-import random
-import string
+import secrets
 import sqlite3
```

```diff
 def make_reset_token():
-    # VULNERABLE: ... random, a PRNG (the Mersenne Twister), SEEDED WITH THE CURRENT TIME ...
-    # the seed here is int(time.time()) ... a value the attacker reads off this response's
-    # Date header. Re-seed with that integer, run the same random.choice() calls, and you
-    # regenerate the SAME token, byte for byte. The secret is not secret ...
-    random.seed(int(time.time()))
-    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))
+    # FIXED: secrets.token_urlsafe(32) draws from a CSPRNG (os.urandom) -- ~256 bits of
+    # UNPREDICTABLE entropy, with no seed the attacker can reproduce ... This is the SAME
+    # generator session-fixation uses for its session ids. The token is unguessable by design.
+    return secrets.token_urlsafe(32)
```

The token's lifecycle follows: the fixed side stores an expiry with the token and consumes it on use.

```diff
     if row:
         token = make_reset_token()
-        RESET_TOKENS[token] = email  # no single-use, no expiry: the flaw here is the GENERATOR
+        RESET_TOKENS[token] = {"email": email, "expires_at": time.time() + TOKEN_TTL}
         deliver_token(email, token)
```

```diff
 def reset():
     ...
-    email = RESET_TOKENS.get(token)
-    if not email:
+    entry = RESET_TOKENS.pop(token, None)            # single-use: consumed on lookup
+    if not entry or entry["expires_at"] < time.time():   # expiry: reject a token past its TTL
         return jsonify({"reset": False}), 400
```

`random.seed(int(time.time()))` + `random.choice(...)` — a PRNG seeded with a value the attacker reads off the `Date` header — becomes `secrets.token_urlsafe(32)`, a CSPRNG whose output no response narrows down. Around it, the token becomes single-use (`pop`) and short-lived (`expires_at`). That is the whole fix.

## The cause is the generator, not a missing check

The bug is not "the flow forgot to authenticate," and it is not "the flow forgot to check the owner." The reset flow authenticates correctly — by possession of the token, which is exactly how forgot-password works — and it acts on the *token's owner*, never on a user id from the request body (so it is **not** IDOR: the token is the secret, not an object's id). The one flaw is that the secret is **predictable**: a PRNG (`random`, the Mersenne Twister) seeded with the clock produces a token anyone can reproduce from the `Date` header. In CWE terms this is a weak password-recovery mechanism (CWE-640) whose root is a predictable seed in a PRNG (CWE-337) — insufficiently random values (CWE-330). The isolation proof: the legitimate self-service reset works identically on both sides; only *predicting the victim's token* separates them, and on the fixed side that prediction fails because `secrets` produced a token the attacker cannot regenerate.

## "Just make the token longer" is not the fix

The tempting read: *the token was guessed, so make it longer and it can't be.* Wrong — the token was never *guessed*, it was **reproduced**. Once you re-seed `random` with the second from the `Date` header, you run the generator forward and produce the *entire* token, however long it is. A 32-character clock-seeded token and a 128-character clock-seeded token fall to the identical script; the extra characters are just as determined by the seed. Length adds entropy only when the generator is unpredictable to begin with. The weakness is predictability, not size.

## "Use random with a better seed" is not the fix

The next tempting read: *the seed was the problem — seed it with something unpredictable and `random` is fine.* Still wrong. `random` (the Mersenne Twister) is **not a security generator under any seed**. Even seeded well, its internal state is recoverable from enough outputs, and its whole future sequence is then reproducible — it was built for statistical quality, not unpredictability, and the Python docs say so outright. And if you reach for `os.urandom` to seed it, you are already holding cryptographic entropy: the correct move is to use `secrets` (built for exactly this), not to nurse `random`. The answer is a different *kind* of generator — a CSPRNG — not a better-seeded PRNG.

## Single-use and expiry are the finish, not the fix

The fixed side also makes the token single-use (`pop`) and short-lived (`expires_at`). Be careful how you read that.

Single-use and expiry are **legitimate and necessary** properties of a well-made reset token — defense in depth. A token should be usable once (so a used token can't be replayed) and briefly (so a leaked token rots fast). A complete fix includes them, and the fixed side does.

**But they are not what defeats this attack, and they are not the central flaw.** The central flaw is predictability. An *unpredictable* token that never expired would still be vastly safer than a *predictable* one, because the attacker could never regenerate it in the first place. Watch where the predicted token dies on the fixed side: at `POST /reset`, rejected as an **unknown token** — it was never in the store, because `secrets` generated something else. Expiry and single-use are never even consulted; there is nothing to expire. Add an expiry to the *vulnerable* side and the attack still works: the attacker predicts the token and uses it immediately, well inside any window.

So name both, but keep them straight. A reader who walks away thinking "the fix was to add an expiry" has missed the lesson: they would have bolted an expiry onto a still-**predictable** token, and the attacker would still reproduce it and spend it inside the window. The axis is unpredictability; single-use and expiry are the honest finish on an already-unguessable token. (Same layered honesty as the `salt` note in `crypto-weak-hash` or the `PIN` note in `debug-enabled`: the named defense is real, but it is not the root fix *here*.)

## Impact, and the contrast with the neighbours

The impact is account takeover: the attacker sets the victim's password and logs in as her. It is not RCE; the ceiling is control of the account whose reset was predicted — which, on a real target, is any account the attacker can request a reset for.

This atom sits one axis away from three neighbours, and the contrasts are the lesson:

| Neighbour | Its axis | `weak-password-reset` (this atom) |
|---|---|---|
| [`session-fixation`](../session-fixation/) — also **A07** | the **session**: the id is *strong* (`secrets`), the flaw is its **lifecycle** — it survives the login | the **reset credential**: the token is *predictable* (`random`-seeded), and the predictability **is** the flaw — the fix even lands on the same `secrets` generator 15 already uses |
| [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) / [`idor-uuid-guessable`](../../A01-broken-access-control/idor-uuid-guessable/) | swap an **object's id** and reach another user's resource past a **missing access-control check** | the predictable token is **not** an object id — it is the authentication **secret**; predicting it *is* becoming the victim, not slipping past a guard |
| [`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/) / [`crypto-ecb-mode`](../../A02-cryptographic-failures/crypto-ecb-mode/) | **crack** a crypto artifact offline (rainbow table; block cut-and-paste) | nothing is cracked — the token is **reproduced** because the generator is predictable; a flaw of authentication *design* (A07), not a crypto *primitive* (A02) |

## The two sides share dependencies

Unlike `crypto-weak-hash`, whose fix pulls in a library (`bcrypt`), the fix here adds nothing to `requirements.txt`:

```
Flask==3.1.3
```

— byte-identical on both sides. `random` and `secrets` are both in the Python standard library, so swapping one for the other changes only `app.py`. The right tool for an unguessable secret was already in the box; the vulnerable side just reached for the wrong module.
