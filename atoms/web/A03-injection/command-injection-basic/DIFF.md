# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py` for the `/ping` view:

```diff
 @app.route("/ping")
 def ping():
     host = request.args.get("host", "")
-    # VULNERABLE: user input concatenated into a shell command string
-    cmd = f"ping -c 1 {host}"
     try:
-        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
+        # FIXED: argument list, no shell — host can never be parsed as shell syntax
+        result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=10)
         output = result.stdout + result.stderr
     except subprocess.TimeoutExpired:
         # timeout: operational hygiene (orthogonal to the vuln/fix), same in both versions
         output = "command timed out after 10s"
-    return render_template("result.html", host=host, command=cmd, output=output)
+    return render_template("result.html", host=host, output=output)
```

`fixed/templates/result.html` also drops the "Executed command" echo (`<pre>{{ command }}</pre>`) — an incidental change, the same way `sqli-union-basic`'s fixed version drops its query debug block. Note what does *not* change: the `try/except subprocess.TimeoutExpired` and the `timeout=10` are identical in both versions (they appear as unchanged context in the diff), so the only security-relevant change is the sink itself — a shell string became an argument list.

## What changed

The single string handed to a shell was replaced with an argument list: `subprocess.run(f"ping -c 1 {host}", shell=True)` became `subprocess.run(["ping", "-c", "1", host])` (with `shell=True` gone, defaulting to `False`). `host` is no longer spliced into a string that a shell parses — it is one element of the argument vector. The vulnerable version also assembled a `cmd` string and echoed it to the page; both are gone in the fixed version, which has no single shell line to show.

## Why this fixes the bug

With an argument list and no shell, Python calls `execvp("ping", ["ping", "-c", "1", host])` and the kernel executes `ping` directly. **No `/bin/sh -c` is spawned**, so nothing ever parses `;`, `|`, `&&`, or `$(...)` as syntax. `host` reaches `ping` as one opaque argument — the destination operand. `127.0.0.1; whoami` becomes a literal "hostname" that `ping` passes to `getaddrinfo`, which fails:

```
ping: 127.0.0.1; whoami: Name or service not known
```

The metacharacters are inert text. This is the exact analogue of the parameterized query in `sqli-union-basic`: there, the `?` placeholder makes the SQL engine parse the statement *first* and bind the value as inert data; here, the argument list makes the OS run exactly one program with the input as an inert argument. Both fixes are the same idea — separate code from data, keep the interpreter out of the loop. The vulnerable version has the opposite model: the input is already part of a program by the time the shell sees it, so the shell *must* parse it as code.

## Blocklisting metacharacters is a losing game

A tempting "fix" is to strip the dangerous character — reject or delete `;`. Step 2 of the walkthrough already shows why that fails: `|`, `&&`, and `$(...)` all reach a second command just as well, and there are more (`||`, backticks, newlines, redirections...). The root cause is not one character; it is that a shell is parsing attacker input as code. As long as the input is spliced into a shell command, escaping and blocklisting are a losing game — the same lesson `sqli-union-basic` teaches about escaping quotes. The only robust fix is to remove the shell.

## Input validation — defense-in-depth, not the fix

An allowlist — accept only hostname/IP characters, e.g. `^[a-zA-Z0-9.-]+$`, reject everything else — would also block these payloads. It is worth having, but as a *second layer*, not the fix, for the same reasons `xss-stored` files `HttpOnly` under defense-in-depth:

- **It is not the root fix.** An allowlist is a blocklist turned inside out, and incomplete allowlists become bypasses; the transferable lesson is "separate code from data," not "enumerate the good characters." The argument-list fix closes the hole regardless of what the input contains.
- **One variable at a time.** The fixed app changes exactly one thing — the sink — so it is unambiguous which change closes the injection. Stacking an allowlist on top would blur that, the same way adding `HttpOnly` to the fixed XSS app would.

The allowlist does earn a concrete, non-redundant role, though: even with the shell gone, a `host` beginning with `-` (say `-f`, a `ping` flood flag) would be read by `ping` as an *option* rather than a destination — **argument injection**, a narrower issue than command injection but still unwanted. An allowlist that forbids a leading `-` closes that gap too. So: the argument list is the fix; the allowlist is a worthwhile extra layer that also happens to shut the argument-injection door.

## The bug lives in app.py (the inverse of the XSS pair)

Here `vulnerable/app.py` and `fixed/app.py` differ — the dangerous sink is in the Python code, and the templates (bar the incidental command echo) are the same. That is the mirror image of `xss-stored` and `xss-reflected`, where `app.py` was byte-identical between versions and the bug lived entirely in the template. Same audit lens, opposite location: for command injection you read the code for `subprocess` / `os.system` calls with `shell=True`; for XSS you read the templates for `|safe`. Knowing which file to open is half the audit.
