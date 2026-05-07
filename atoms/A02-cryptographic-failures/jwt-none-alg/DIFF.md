# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. Only the `decode` helper changes; routes, templates, and the `SECRET` constant are byte-identical.

```diff
 def decode(token):
-    header = jwt.get_unverified_header(token)
-    if header.get("alg") == "none":
-        # TODO: remove after local testing — accepts unsigned tokens
-        return jwt.decode(token, options={"verify_signature": False})
     return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Four lines deleted. No lines added.

## What changed

The vulnerable `decode` had a branch that inspected the token's header and skipped signature verification when the header advertised `alg=none`. The fix is to delete the branch — the function now always verifies the signature under HS256, with no header-driven escape hatch.

The `# TODO: remove after local testing` comment went out with the lines it described. That comment was the realistic shape of this kind of CVE: a debug shortcut that survived past the testing it was meant for and reached production. Future code reviewers should treat any `verify_signature: False` (in PyJWT) — or the equivalent in other JWT libraries — as a hard finding wherever it appears in an authenticated path.

## Why this fixes the bug

Three reinforcing reasons:

- **The fix removes the branch, not the symptom.** A naive alternative would be to keep the branch and add a `header.get("alg") in BLOCKED_ALGS` guard. That would still let the token's header pick which validator runs — the deeper bug from §5 of the walkthrough — and would lose to case-insensitive comparison, Unicode escapes, and the broader class of algorithm-confusion attacks that don't involve `none` at all.
- **`algorithms=["HS256"]` is a positive list, decided server-side, before the token is read.** PyJWT compares the token's `alg` claim against this list and rejects anything not in it. `none` isn't there, so unsigned tokens fail before any signature work begins. The list is a property of *this endpoint* (this server, this code path), not of *this token* — that asymmetry is what closes the confused-deputy hole.
- **`SECRET` is now non-negotiable.** PyJWT's `NoneAlgorithm.prepare_key` raises `InvalidKeyError` if any non-`None` key is passed to it, and its `verify()` always returns `False`. So even if an attacker tried to coerce the algorithm path to `none` despite the allowlist, the underlying library would refuse to "verify" a none-signed token in any way that returns `True`. The library's own hardening backstops the application's allowlist — defense in depth, not defense in this exact line.

## Why "block alg=none" is not the fix

A natural-but-wrong remediation looks like:

```python
header = jwt.get_unverified_header(token)
if header.get("alg") == "none":
    abort(401)
return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Three reasons not to do this:

- **Case sensitivity and Unicode.** `"NONE"`, `"None"`, `"nOnE"`, and `"none"` all decode through to the same algorithm in some JWT parsers but skip the string-equality check in this guard. Real bypasses against this exact pattern have been published for several JWT libraries.
- **It still branches off `header["alg"]`.** The server is still letting the token's header steer behavior, just with one fewer permitted value. The pattern survives; only the alphabet shrinks.
- **It only addresses `none`.** Other ways the attacker can manipulate `alg` to subvert validation — weak secrets that fall to brute-force, and algorithm-confusion attacks where the server is tricked into using the wrong key — don't involve `none` at all. A blocklist that targets `none` specifically protects against exactly one bypass and zero of the related ones.

The general rule for JWT decode calls: pass `algorithms=` as a positive list of exactly the algorithms this endpoint should accept, and never branch off `header["alg"]` to choose how to validate.

## Contrast with previous atoms

This is the third atom in the project where the fix is *removing* code rather than adding it (the first two were `sqli-union-basic`, where the `f"…{username}…"` SQL build was deleted; and `xss-reflected`, where the `|safe` filter was deleted). In `idor-numeric-id` and `ssrf-basic`, the fix added a missing check. Here the bug isn't a missing check — there is a check, the HS256 verification on line 5 of the diff. The bug is the *escape hatch* that lets the attacker route around it. Removing the escape hatch leaves only the check.

A way to read this family in code reviews: when you see a JWT decode wrapped in any kind of conditional that keys off the token itself — `if header.get("alg") == ...`, `if "Bearer " in auth`, `if claims.get("kid") in trusted_kids` — pause and ask "what value is the conditional reading, and who controls that value?" If the answer is "the attacker", the conditional is at best load-bearing and at worst the whole bug.
