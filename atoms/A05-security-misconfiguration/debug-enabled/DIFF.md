# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in exactly one place: the `__main__` block that starts the server. The vulnerable side runs with `debug=True` and switches the debugger PIN off; the fixed side runs with `debug=False`. Nothing else changes — the imports, `app.json.compact = True`, the `GET /` banner, the `GET /items/<idx>` route, and the `Dockerfile` are byte-identical, and the two `requirements.txt` are identical too. The whole vulnerability, and the whole fix, is one flag.

## The fix — turn off debug mode

```diff
 if __name__ == "__main__":
-    # VULNERABLE: debug=True exposes Werkzeug's interactive debugger (console -> RCE);
-    # WERKZEUG_DEBUG_PIN=off unlocks that console. The dev mode is the flaw, not the route.
-    os.environ["WERKZEUG_DEBUG_PIN"] = "off"
-    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)
+    # FIXED: debug=False -- no interactive debugger, no console. Same exception -> generic 500.
+    # In production, serve behind a real WSGI server (Gunicorn/uWSGI), not this dev server.
+    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=False)
```

(Comments abbreviated.) `debug=True` turns on Werkzeug's interactive debugger — the error page *and* the console that runs arbitrary Python in the server process. `WERKZEUG_DEBUG_PIN=off` removes the one lock in front of that console. `debug=False` removes both: an unhandled exception now becomes a generic `500` with no traceback and no console, and there is no PIN line because there is no debugger to unlock. The route that throws is untouched.

One identical line on both sides is worth calling out because it is easy to misread: `app.json.compact = True`. Debug mode also makes Flask *pretty-print* JSON, so without this line the benign `GET /items/0` response would look different on the two sides (indented vs. compact). Pinning compact output on both keeps the benign response byte-identical, so the **only** observable difference between the apps is what an unhandled exception becomes. It is orthogonal to the vuln and identical in both files.

## The cause is the exposed dev mode, not "the route forgot to handle the error"

It is tempting to read the crash as the bug: `int("abc")` throws, so the route should have caught it. But the exception is only the **trigger**, not the vulnerability. Proof of isolation: send the same `GET /items/abc` to the fixed app — it throws the *identical* `ValueError` and returns a bare `500`. Same exception, no debug page, no console. What differs is not whether the route throws; it is what the server *does* with a throw, and that is set entirely by the debug flag.

This matters because the obvious "fix" — wrap the route in `try/except` — is a trap (below).

## "Just catch the exception" is not the fix

An `errorhandler` or a `try/except` around `int(idx)` would stop *this* traceback from rendering. But it treats the symptom, not the cause: the interactive debugger is still on. The **next** unhandled exception — from another route, another input, a bug you have not written yet — renders the debug page and reopens the console. You would be playing whack-a-mole with error sites while leaving the execution console armed. The debugger must be *off*, not merely unreached by one code path.

## "Just set the PIN" is not the fix

The other reflex: the console is guarded by a PIN, so turn the PIN on. Be precise about what that buys. The PIN does raise the bar a little — but it is **derived from machine data**: the username, a machine id (`/etc/machine-id` or the boot id), and the MAC address, hashed together. The debug page itself leaks several of those inputs (your username appears in the file paths in every traceback), and the rest are stable and sometimes obtainable, so a determined attacker can *derive* the PIN. It is an obstacle, not a wall. And more fundamentally: a **development** console has no business being reachable in a deployed environment at all. Turning the PIN on locks — badly — a door that should not exist here. Leaving `debug=True` is the mistake; `debug=False` removes the door.

(This is the same shape as the layered-honesty notes elsewhere in the repo — the salt in `crypto-weak-hash`, CBC in `crypto-ecb-mode`: the named control has *some* value, but it is not the root fix.)

## Serving in production — a real WSGI server

One more thing, and this one is **not** a trap — it is legitimate deployment context. `app.run()` starts Werkzeug's built-in **development server**, which prints, on every boot, `WARNING: This is a development server. Do not use it in a production deployment.` The minimal fix for this atom is `debug=False`. The complete deployment practice is to not use the development server at all: run the app behind a real **WSGI** server (Gunicorn, uWSGI), which has no debugger and no development server to expose. `debug=False` closes the vulnerability; serving behind a WSGI server is how you avoid being one flag away from it in the first place.

## The two sides share dependencies

Unlike `crypto-weak-hash`, whose fix pulled in a new library (`bcrypt`), here `vulnerable/requirements.txt` and `fixed/requirements.txt` are **identical**:

```
Flask==3.0.0
Werkzeug==3.1.8
```

`Werkzeug` is Flask's own dependency — you do not install it separately — but it is pinned **explicitly** here on purpose. The interactive debugger and its console protocol (the `__debugger__`/`cmd`/`frm`/`s` request, where the `SECRET` sits in the page) are Werkzeug's, and they are version-specific; pinning the exact version keeps the exploit in `WALKTHROUGH.md` reproducible. The fix is a one-flag code change, not a dependency change — a reminder that a devastating misconfiguration can be, and often is, a single line of config.

## The impact is information disclosure + RCE — like 09/20, by a different cause

Two findings: the debug page leaks source, variables, and paths (information disclosure), and its console runs arbitrary Python (RCE). RCE is the ceiling — the same ceiling as [`command-injection-basic`](../../A03-injection/command-injection-basic/) and [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/), which is worth pausing on, because the three are alike in impact and nothing else. "One atom, one vulnerability" is about the **cause**, not the impact:

| | `command-injection-basic` (09) | `deserialization-pickle` (20) | `debug-enabled` (33) |
|---|---|---|---|
| Category | **A03 — Injection** | **A08 — Data Integrity Failures** | **A05 — Security Misconfiguration** |
| Surface | user input in a shell command | a `pickle` cookie | an unhandled exception + the exposed debugger |
| Who executes | the **shell** (`/bin/sh -c`) | the **deserializer** (`pickle.loads`) | the framework's **dev console** (Werkzeug) |
| Attacker input becomes code? | yes — stitched into the command | ~yes — the bytes carry behavior | **no** — the console was already open |
| Root cause | app builds a shell command from input | `pickle.loads` on untrusted bytes | dev mode (debugger) left reachable |
| The fix | drop the shell (argument list) | change the format (JSON) | `debug=False` (+ real WSGI in prod) |

The sharp point is the fourth row: in 09 the attacker's data is stitched into a command, in 20 it is bytes that *carry* behavior — in both, something of the attacker's becomes code. In 33 nothing of the attacker's becomes code. The execution console was already there, exposed by a configuration flag; the exception is only the doorbell that opens the page. Same loot (RCE), three completely different doors — and here the door is a deployment setting, not a line of application logic.
