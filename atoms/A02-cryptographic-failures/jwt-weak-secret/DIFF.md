# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in **exactly one line** — the `SECRET` constant. Every other byte is identical: the imports, the `decode`/`authenticate` helpers, all three routes, the `algorithms=["HS256"]` verification, the `Dockerfile`, and `requirements.txt`. There are no templates (this atom is API-only). The `wordlist-sample.txt` at the atom root is an attack asset, not part of either app.

## The fix — a stronger value

```diff
 # HS256 signing secret. The verification logic below is correct and byte-identical in
 # both vulnerable/ and fixed/ — the whole security of this atom rests on the strength
 # of this one value. See DIFF.md.
-SECRET = "changeme123"  # VULNERABLE: weak, guessable, sits in any password wordlist
+SECRET = "jlui6jbnFeh9_BXEPw4wUaF1UwEfZ2R9uaSkVqDoWuk"  # FIXED: strong, high-entropy (secrets.token_urlsafe(32)); not in any wordlist
```

The weak `changeme123` becomes a 43-character value from `secrets.token_urlsafe(32)` — 32 bytes of CSPRNG output, base64url-encoded. It is a fixed literal, not `SECRET = secrets.token_urlsafe(32)`: generating it per process start would rotate the key on every restart and invalidate live tokens. One strong value, pinned.

That is the entire change. Run the same `john --wordlist=wordlist-sample.txt jwt.txt` against a token from the fixed app and it returns `0 password hashes cracked, 1 left` — the strong secret is in no wordlist, and 32 random bytes are not brute-forceable at all. The admin token forged with `changeme123` gets `401` on the fixed app, because the HMAC no longer matches.

## The fix changes a value, not code — a diff this repo hasn't seen

Every atom's fix so far has been one of two shapes. In the A01 atoms (`idor-numeric-id`, `bola-rest`, …) and in `jwt-none-alg`, `app.py` differs in a **route or helper** — a check added, a branch removed; the bug and the fix live in *code*. In the reflected-XSS pair, `app.py` is **identical** and the difference lives in a template (a `|safe` filter). This atom is a third kind: `app.py` differs, but **only in a constant** — not one line of logic changes.

That is the lesson, sitting in the diff itself. The `decode` is correct and untouched. No endpoint moves. The remediation was not to *do* something differently — it was to *choose a better value*. **The security lived entirely in the secret, not in the code around it.** A one-line diff, and the line is data.

## Contrast with `jwt-none-alg` — and why its lesson wasn't enough

`jwt-none-alg`'s fix *removed* code: four lines, the `alg:none` branch that skipped verification. This fix removes and adds no logic at all — it swaps one literal.

Look at this atom's `decode`:

```python
def decode(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

That is **byte-for-byte `jwt-none-alg`'s _fixed_ `decode`.** This atom starts where that one ended — the algorithm lesson already learned: a positive `algorithms=` allowlist, no branch on the header. And it still falls, because the *key* is guessable. `jwt-none-alg` taught *"looks-like-crypto is not is-crypto"* — a `jwt.decode` wrapped in `SECRET` and `algorithms=` only looks like a boundary if some path skips verification. This atom sharpens it to the case where nothing is skipped: correct verification is still not a boundary if the secret is weak. **05 = the lock was bypassable (the algorithm); 13 = the lock runs, but the key defending it is weak.** Both are "looks like a boundary, isn't one" — one aimed at the algorithm, the other at the key.

`jwt-none-alg`'s walkthrough even named this in advance: *"weak shared secrets that survive a brute-force"* were listed as another way to lose the same game. This atom is that flavor, made real. The takeaway: getting the algorithm right (the 05 fix) is **necessary but not sufficient** — a JWT is only as trustworthy as the secret behind the signature. "Signed" is not "secure."

The runtime says so too. PyJWT 2.12 emits `InsecureKeyLengthWarning` for the 11-byte `changeme123` on every sign and verify; with the 43-byte fixed secret the warning is gone. The library flags a short key — it just doesn't refuse one.

## The strong secret is visible in `fixed/app.py` — why that doesn't break the lesson

The fixed secret is hardcoded in the repo, in plain sight. That does not weaken the demonstration, for one reason: **the attack model is "attacker holds a token and a wordlist," not "attacker reads your source."** In a real deployment the source is not public; the attacker starts from a captured JWT and tries to recover the key from it. The lesson is that recovering a *high-entropy* key from the token is infeasible — and that stays true whether or not the value is printed here. The lab hardcodes both secrets, weak and strong, so the atom has stable, inspectable values to reproduce.

A production fix would also do one thing this atom deliberately doesn't: move the secret out of source entirely, into an environment variable or a secrets manager. That is a separate concern (secret management), and folding it in would blur the one axis this atom isolates — *entropy*. So both versions hardcode, and only the value changes. Mentionable, not applied.

## `403`, not `404`

`GET /admin/users` returns **`403`** for a valid non-admin token — the honest status: "authenticated, but not allowed." There is no enumeration oracle to hide here: the endpoint is a fixed resource, not an object indexed by a sequential id. (That was `bola-rest`'s reason for choosing `404` — sequential ids, where a `403` would confirm an object exists. No such id exists in this atom, so `403` is right; don't copy the `404` reflexively.)

## This is A02 — the flaw is a value, and it doesn't `grep`

The bug isn't parsed input or a missing check — it's a low-entropy key protecting an HMAC signature, recovered by brute force. That is a **Cryptographic Failure (A02)**, the same category as `jwt-none-alg`. And like its sibling it doesn't `grep`: there is no dangerous call to search for — `jwt.decode(..., algorithms=["HS256"])` is exactly what a *correct* implementation looks like. You catch it by reading the one thing greps skip: the value of the key. Ask of every signing secret, "could this be in a wordlist?" — and here the answer is yes.
