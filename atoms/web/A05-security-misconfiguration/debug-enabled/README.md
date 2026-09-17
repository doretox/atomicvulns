# debug-enabled — Debug mode enabled in a reachable environment

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for one of the most common — and most devastating — deployment mistakes: leaving **debug mode** on where an attacker can reach it. The app has an ordinary route that takes a value, turns it into a number, and looks up an item. Send it a value that is not a number and the route throws an **unhandled exception**. On a normally configured server that would be a dull `500`. But this app runs with `app.run(debug=True)`, Flask's development mode — and in that mode **Werkzeug** (the HTTP library that ships underneath Flask and provides its built-in development server and error page) does not hide the error. It renders an interactive **debug page**: the full **traceback** (Python's error report — the call stack, the local variables, and the source lines around the failure), served straight back to you.

That page is two problems at once. First, it **leaks** your source code, your variables, and server file paths — **information disclosure** on its own. Second, it embeds an interactive **console**: a field that runs **arbitrary Python inside the server process** — **RCE (Remote Code Execution)**. The console is nominally guarded by a **PIN** printed in the server log, but the PIN is *derived from machine data* (username, machine-id, MAC) and is derivable by a determined attacker — an obstacle, not a wall — and here it is switched **off** outright (`WERKZEUG_DEBUG_PIN=off`, a realistic "make debugging easier" setting). So the whole attack is: send a request that crashes the route, land on the debug page, read the console's secret out of the page, and issue one more request that runs a command on the server.

The fix is not "set the PIN" and not "catch the exception" — both leave the development debugger exposed. It is `debug=False`. In production the built-in **development server** should not be used at all: you serve the app behind a real **WSGI** (Web Server Gateway Interface — the standard plug between a Python app and a production server) server such as Gunicorn or uWSGI, which has no debugger. The route logic never changes; the same bad input still throws — it just becomes a generic `500` with no traceback and no console.

This atom sits in **A05 — Security Misconfiguration**, alongside its siblings [`xxe-basic`](../xxe-basic/) and [`xxe-blind-oob`](../xxe-blind-oob/). The contrast is the point: those are a misconfigured *XML parser* (a dangerous default left on); this is a misconfigured *framework/deployment* (a development feature left reachable). Its RCE ceiling matches [`command-injection-basic`](../../A03-injection/command-injection-basic/) and [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/) — but by a different door: there the attacker's **data becomes code** (stitched into a shell, or carried as behavior into a deserializer); here **nothing of the attacker's becomes code** — the execution console was already sitting there, exposed by a config flag, and the attacker just types into it. The exception is only the doorbell.

> **Theory primer:** Read [PortSwigger: Information disclosure](https://portswigger.net/web-security/information-disclosure)
> before working through this atom — it names "failing to disable debugging and
> diagnostic features" and "overly verbose error messages" as sources of disclosure,
> which is exactly the debug page's first half. The atoms in this repo show *how* a
> vulnerability happens in code; the Academy explains *what* it is and why it matters.
> (The Academy covers the information-disclosure side; the interactive-console RCE that
> the exposed debugger also enables is shown here in the atom.)

## Stack note — single-container, no database, identical dependencies

Each side is a single Flask container with no datastore: there is nothing to seed — the app only exposes one route that crashes on bad input, so there is no user, session, or data. And the two sides share an **identical** `requirements.txt`: the fix is one flag in the code (`debug=True` → `debug=False`, plus dropping the `WERKZEUG_DEBUG_PIN=off` line), not a dependency. `Werkzeug` is **pinned explicitly** (`==3.1.8`) next to `Flask==3.1.3` because the interactive debugger — the whole point of this atom — is Werkzeug's, and its console protocol is version-specific; pinning keeps the lab reproducible.

## API only — no HTML, no browser

There is no web UI and no templates: every normal response is JSON. The interface that teaches the lesson is the **Werkzeug debug page**, which the framework renders on its own whenever the app throws — a hand-written page would add nothing. You drive this atom entirely from **Burp Suite (Repeater)**: crash the route, read the debug page in the response, lift the console secret out of its HTML, and send the request that runs a command — the command's output comes back in the HTTP response. The console was born to be clicked in a browser, but it reproduces better in Repeater (raw control of the query parameters and the secret), and the proof is server-side, so there is no browser track.

## Run

From the repo root:

```bash
./atom up debug-enabled
```

- Vulnerable API: `http://127.0.0.1:8033`
- Fixed API: `http://127.0.0.1:8133`

There is no landing page beyond a JSON banner at `/`; the trigger route is `GET /items/<idx>` (try `/items/0`, then `/items/abc`), documented in `WALKTHROUGH.md`. Stop with `./atom down debug-enabled`. If you prefer raw Docker: `cd atoms/A05-security-misconfiguration/debug-enabled && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation in Burp: crash the route, watch the debug page leak your source and paths, lift the console secret, and run `id` on the server (`uid=0(root)`) straight from the HTTP response. Then the same requests against the fixed app return a bare `500`. No browser.
2. [`DIFF.md`](./DIFF.md) — the one-flag diff between `vulnerable/` and `fixed/`, and why "set the PIN" and "catch the exception" are not the fix.

## Fixed version

The patched API on port 8133 runs with `debug=False`. The same malformed input still throws — the route is unchanged — but the response is a generic `500 Internal Server Error` with no traceback and no console, and there is no `WERKZEUG_DEBUG_PIN=off`. The request that ran `id` on 8033 gets a bare `500` here: no debug page to read a secret from, no console to reach. See [`DIFF.md`](./DIFF.md) for why the real fix is turning off debug mode (and, in production, serving behind a real WSGI server) rather than trying to lock the debugger down.
