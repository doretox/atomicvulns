# DIFF — vulnerable vs. fixed

The change is the (de)serialization format — `node-serialize` becomes JSON. In `app.js` that is three edits (the import, the line that *writes* the default cookie, and the line that *reads* it back), and because the dangerous deserializer is a *dependency*, the change also touches `package.json` and the `Dockerfile`.

`app.js` (comments abbreviated):

```diff
 const http = require("http");
-const serialize = require("node-serialize");
+// FIXED: no node-serialize dependency at all -- JSON is a data-only format (stdlib).
 ...
     if (!cookie) {
-      // First visit: serialize the default prefs (node-serialize + base64) and set the cookie.
-      const raw = Buffer.from(serialize.serialize(DEFAULT_PREFS)).toString("base64");
+      // First visit: serialize the default prefs (JSON + base64) and set the cookie.
+      const raw = Buffer.from(JSON.stringify(DEFAULT_PREFS)).toString("base64");
       return sendJson(res, 200, DEFAULT_PREFS, { "Set-Cookie": `prefs=${raw}; Path=/` });
     }
-    // VULNERABLE: ... passed straight to serialize.unserialize ... "_$$ND_FUNC$$_" -> eval -> RCE ...
+    // FIXED: ... JSON carries DATA ONLY ... JSON.parse never builds a function, never evals ...
     let prefs;
     try {
-      prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString());
+      prefs = JSON.parse(Buffer.from(cookie, "base64").toString());
     } catch (e) {
       prefs = DEFAULT_PREFS;
     }
```

`package.json` — the vulnerable app declares the dependency; the fixed app has none:

```diff
   "engines": {
     "node": ">=22 <23"
-  },
-  "dependencies": {
-    "node-serialize": "0.0.4"
   }
 }
```

`Dockerfile` — the vulnerable image installs it; the fixed image installs nothing:

```diff
 COPY package.json .
-# node-serialize is the object of study (the dangerous deserializer of this ecosystem).
-RUN npm install --omit=dev
+# No `npm install`: zero runtime dependencies (http + JSON are stdlib).
 COPY app.js .
```

Everything else is byte-for-byte identical between the two versions: in `app.js`, the `http` server, `DEFAULT_PREFS`, the hand-written `getCookie` and `sendJson`, the first-visit branch that sets the cookie, the `try/catch` that falls back to the default theme, the `theme` fallback line, the `GET /` handler, the 404, and the `listen`; and the base image, `WORKDIR`, `ENV HOST`, `EXPOSE`, and `CMD` in the `Dockerfile`. There are no templates — this atom is API-only. The bug lives entirely in the format the cookie is (de)serialized with.

## What changed

In `app.js`, three lines, all the same swap: the import (`node-serialize` → gone), the line that *writes* the default cookie (`serialize.serialize` → `JSON.stringify`), and the line that *reads* it back (`serialize.unserialize` → `JSON.parse`). The dangerous one is the read — `serialize.unserialize` on the attacker-controlled cookie. The write is only there so each app reads the format it wrote; serializing the app's *own* trusted dict is harmless. This is a *logic-different* fix isolated to the serialization format.

The `try/catch Exception` around the read is **identical in both versions** and is not the fix. It exists so a malformed cookie degrades to the default preferences instead of crashing the request. On the vulnerable app it has a chilling side effect: after `serialize.unserialize` runs the attacker's function, the reconstructed value has no string `theme`, so the handler falls back and answers a normal `{"theme":"light"}` while the command has already run. The RCE is silent in-band; the only trace is the side effect on the server.

The dependency edits (`package.json`, `Dockerfile`) are not incidental — they *are* part of the fix, and the next notes explain why.

## Why this fixes the bug — and why it is NOT "validate the input"

The cause is the **format**, not the content of the cookie. The malicious payload is *well-formed* `node-serialize` — a valid object whose `rce` value is a string beginning with `_$$ND_FUNC$$_`. There is no malformed byte to reject, no metacharacter to strip; the exploit rides entirely inside valid, spec-compliant data. You cannot "sanitize" your way out, because the danger is not bad data — it is that the format *rebuilds behavior* (a function) and `eval`s it. So the fix is not "validate the cookie" or "block the `_$$ND_FUNC$$_` string"; it is to stop using a format that can carry behavior.

Proof of isolation: the benign default cookie renders `{"theme":"light"}` identically on both apps — in fact it is the *same base64 string* on both, because `node-serialize` and JSON produce identical output for pure data. Only a cookie whose value carries a `_$$ND_FUNC$$_` function separates them, and it separates them because `serialize.unserialize` `eval`s it while `JSON.parse` cannot.

## Data vs. behavior — and why the fix drops the dependency

This is the whole lesson, so state it plainly. A **data** format (JSON) describes *values*: after `JSON.parse` you hold an object, an array, a string — inert. The `_$$ND_FUNC$$_` payload, parsed as JSON, is just an object with a harmless string field. A **behavior** format (`node-serialize`) describes *how to reconstruct an object*, and reconstruction can include rebuilding a **function** — which it does by `eval`-ing its source. Deserializing untrusted input with a behavior format hands the attacker code execution. The durable rule: **never deserialize untrusted data with a format that can carry behavior**.

Here that dangerous format is not the standard library — it is an npm package, `node-serialize`. So the fix is not "upgrade the library": `node-serialize` has no patched release, and even if it did, a library whose *job* is to (de)serialize functions is the wrong tool for untrusted input. The fix **removes the dependency** and goes back to `JSON` (stdlib). That is why the fixed app's `package.json` has no `dependencies` and its `Dockerfile` has no `npm install` — the whole unsafe capability is gone, not patched. (In `deserialization-pickle`, the dangerous deserializer is Python's stdlib `pickle`, which you cannot "uninstall" — so there the fix swaps the serialization *function*. Same idea — a data-only format — expressed as each ecosystem allows: swap the function in Python, drop the package in Node.)

## Signing the cookie is not the fix

An experienced reader has a fix ready: "the cookie was tampered with — sign it with an HMAC (a keyed hash that detects tampering) so a forged one is rejected." It is worth being precise about why this atom does *not* do that.

Signing does help *something*: it makes the cookie tamper-evident, so a forged payload is rejected before it reaches `unserialize` — it raises the bar for *this* delivery path. But it closes the **symptom** (tampering with *this* cookie), not the **cause**. The dangerous operation — `serialize.unserialize` on data that crossed a trust boundary — is still there, guarded rather than removed. If the signing key ever leaks it is instant RCE again. And if those bytes reach `serialize.unserialize` by any other route — a cache, a message queue, an uploaded file, a second endpoint — the signature on the cookie protects none of it. You are relying on key secrecy to make an unsafe primitive safe, when you could just remove the unsafe primitive.

So signing is defense-in-depth, not the root fix. Changing the format is the root fix: `JSON.parse` cannot execute, key or no key, path or no path. (Same move as the "named, not applied" notes in `ssrf-cloud-metadata`, `xxe-basic`, and `ssti-jinja`: name the control the reader would reach for, and show why it is not the fix here — and the same symptom-vs-cause line `deserialization-pickle` draws about HMAC.)

## The impact is RCE — same class as `deserialization-pickle`, by a different mechanism

The finding is Remote Code Execution: a tampered cookie runs arbitrary commands on the server. That is the same ceiling as `deserialization-pickle`, and the two are worth putting side by side — because they are the **same class of vulnerability** (insecure deserialization, A08 — Software and Data Integrity Failures) reached by a **different concrete cause**:

| Axis | `deserialization-pickle` | `deserialization-node` (this atom) |
|---|---|---|
| **Runtime / format** | Python, `pickle` (stdlib) | Node.js, `node-serialize` (npm package) |
| **Where the executor lives** | `pickle.loads` (standard library) | `serialize.unserialize` (npm dependency) |
| **Code trigger in the data** | object with `__reduce__` → calls the function on unpickle | function with `_$$ND_FUNC$$_` → `eval`'d on unserialize |
| **Fix** | change format: `pickle` → JSON | change format: `unserialize` → `JSON.parse` |
| **Impact** | RCE | RCE |

Same impact, same category, same *kind* of fix (a behavior-carrying format → a data-only one) — and yet two atoms, not one. "One atom = one vulnerability" is about the *cause*, and the cause here is concrete: *which* deserializer runs, and *what* in the data triggers it. In Python the dangerous deserializer ships in the standard library and fires through `__reduce__`; in Node it arrives as an npm package and fires through an `eval`'d `_$$ND_FUNC$$_` function. The same class materializes through a mechanism native to each ecosystem — this atom is the Node face of the flaw `deserialization-pickle` shows in Python.
