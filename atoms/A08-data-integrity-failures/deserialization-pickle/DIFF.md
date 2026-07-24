# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is the (de)serialization format — `pickle` becomes `json` (comments abbreviated):

```diff
-import pickle
+import json
 ...
     if cookie is None:
-        # First visit: serialize the default prefs (pickle + base64) and set the cookie.
-        raw = base64.b64encode(pickle.dumps(DEFAULT_PREFS)).decode()
+        # First visit: serialize the default prefs (JSON + base64) and set the cookie.
+        raw = base64.b64encode(json.dumps(DEFAULT_PREFS).encode()).decode()
         resp = make_response(render_template("index.html", theme=DEFAULT_PREFS["theme"]))
         resp.set_cookie("prefs", raw)
         return resp
-    # VULNERABLE: ... passed straight to pickle.loads ... -> code execution on load ...
+    # FIXED: ... JSON carries DATA ONLY ... json.loads cannot execute code ...
     try:
-        prefs = pickle.loads(base64.b64decode(cookie))  # RCE: attacker bytes -> code on load
+        prefs = json.loads(base64.b64decode(cookie))  # JSON: data only; no code path on load
         theme = prefs["theme"]
     except Exception:
         theme = DEFAULT_PREFS["theme"]
```

Everything else is byte-for-byte identical between the two versions: the `os`/`base64` imports, `DEFAULT_PREFS`, the first-visit branch that sets the cookie, the `try/except` that falls back to the default theme, `render_template`, `__main__`, the `Dockerfile`, `requirements.txt`, and `templates/index.html`. The bug lives entirely in the format the cookie is (de)serialized with.

## What changed

Three lines, all the same swap: the import (`pickle` → `json`), the line that *writes* the default cookie (`pickle.dumps` → `json.dumps(...).encode()`), and the line that *reads* it back (`pickle.loads` → `json.loads`). The dangerous one is the read — `pickle.loads` on the attacker-controlled cookie. The write is only there so each app reads the format it wrote; dumping the app's *own* trusted dict is harmless. This is a *logic-different* fix isolated to the serialization format — the smallest possible expression of "the format is the whole bug".

The `try/except Exception` around the read is **identical in both versions** and is not the fix. It exists so a malformed cookie degrades to the default preferences instead of a 500. On the vulnerable app it has a chilling side effect: after `pickle.loads` executes the attacker's command, the reconstructed value is not a dict, so `prefs["theme"]` raises and the except quietly falls back — the page renders a normal `Theme: light` while the command has already run. The RCE is silent.

## Why this fixes the bug

The class is: `pickle.loads` rebuilds whatever object the bytes describe, and pickle bytes can describe "call this function" — so untrusted bytes become code. `json.loads` has no such power: JSON's grammar produces only primitives — objects/dicts, arrays/lists, strings, numbers, booleans, null. No JSON construct names a Python callable, so there is no code path to reach. Feed the fixed app the same malicious pickle cookie and `json.loads` simply raises on the non-JSON bytes; the command never runs. The benign case is unchanged — the default `{"theme": "light"}` round-trips through JSON exactly as it did through pickle.

## The cause is the format, not "validate the cookie"

It is tempting to file this under "untrusted input — validate it". But look at the payload: disassembled, it is *well-formed* pickle (`PROTO`, `STACK_GLOBAL` resolving `posix.system`, the reduce that calls it). There is no malformed byte to reject, no metacharacter to strip — the exploit rides entirely inside valid, spec-compliant pickle. You cannot "sanitize" your way out, because the danger is not bad data; it is that the format *executes* the data it is given. Proof of isolation: the benign default cookie renders `Theme: light` identically on both apps; only a cookie whose pickle carries a `__reduce__` separates them, and it separates them because `pickle.loads` runs it while `json.loads` cannot.

## Data vs. behavior

This is the whole lesson, so state it plainly. A **data** format (JSON) describes *values*: after `json.loads` you hold a dict, a list, a string — inert. A **behavior** format (pickle) describes *how to reconstruct an object*, and reconstruction can include calling arbitrary functions (that is exactly what `__reduce__` is for). Deserializing untrusted input with a behavior format hands the attacker a function call. The durable rule: **never deserialize untrusted data with a format that can carry behavior** — pickle, `PyYAML`'s `yaml.load` without `SafeLoader`, and the native serializers of other languages all share this shape. When the data crosses a trust boundary, use a data-only format.

## Signing the cookie is not the fix

An experienced reader has a fix ready: "the cookie was tampered with — sign it with an HMAC (a keyed hash that detects tampering) so a forged one is rejected." It is worth being precise about why this atom does *not* do that.

Signing does help *something*: it makes the cookie tamper-evident, so a forged pickle is rejected before it reaches `loads` — it raises the bar for *this* delivery path. But it closes the **symptom** (tampering with *this* cookie), not the **cause**. The dangerous operation — `pickle.loads` on data that crossed a trust boundary — is still there, guarded rather than removed. If the signing key ever leaks it is instant RCE again (keys do leak — `ssti-jinja` discloses a Flask `SECRET_KEY` straight out of the app's config). And if those bytes reach `pickle.loads` by any other route — a cache, a message queue, an uploaded file, a second endpoint — the signature on the cookie protects none of it. You are relying on key secrecy to make an unsafe primitive safe, when you could just remove the unsafe primitive.

So signing is defense-in-depth, not the root fix. Changing the format is the root fix: JSON cannot execute, key or no key, path or no path. Python's own `pickle` docs draw exactly this line — "consider signing data with hmac if you need to ensure that it has not been tampered with", but "safer serialization formats such as json may be more appropriate if you are processing untrusted data". This atom is processing untrusted data, so it changes the format. (Same move as the "named, not applied" notes in `ssrf-cloud-metadata`, `xxe-basic`, and `ssti-jinja`: name the control the reader would reach for, and show why it is not the fix here.)

## The impact is RCE — like command injection, by a different cause

The finding is Remote Code Execution: a tampered cookie runs arbitrary commands on the server. That is the same ceiling as `command-injection-basic`, which is worth pausing on, because the two are alike in impact and nothing else. There, the app builds a shell command string out of user input and a shell parses it — the fix is to stop invoking a shell (argument list, no `shell=True`). Here nothing builds a command; the deserializer reconstructs an object and runs the behavior embedded in the bytes — the fix is to stop using a behavior-carrying format. Same impact, different category (A03 vs. A08), different mechanism, different fix. "One atom, one vulnerability" is about the *cause*, not the impact — just as two atoms can both end in file disclosure by different roots, these two both end in RCE by different roots.
