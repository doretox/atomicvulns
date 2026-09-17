# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py` for the `/view` view:

```diff
     filename = request.args.get("file", "")
-    # VULNERABLE: user input joined onto the base dir and opened directly —
-    # nothing confines the resolved path to BASE_DIR
-    path = os.path.join(BASE_DIR, filename)
+    # FIXED: resolve the real path, then confirm it stays inside BASE_DIR
+    base = os.path.realpath(BASE_DIR)
+    path = os.path.realpath(os.path.join(base, filename))
+    if not path.startswith(base + os.sep):
+        abort(404)
     try:
         with open(path) as f:
             content = f.read()
     except OSError:
         # missing/unreadable file: operational hygiene, orthogonal to the
         # vuln and the fix, identical in both versions
         abort(404)
-    return render_template("result.html", filename=filename, path=path, content=content)
+    return render_template("result.html", filename=filename, content=content)
```

`fixed/templates/result.html` also drops the "Resolved path" echo (`<pre>{{ path }}</pre>`) — an incidental change, the same way `command-injection-basic`'s fixed version drops its "Executed command" echo. Note what does *not* change: the `try/except OSError: abort(404)` and the `with open(path)` line are identical in both versions (they appear as unchanged context in the diff), so the only security-relevant change is the confinement of the resolved path.

## What changed

The bare `os.path.join(BASE_DIR, filename)` + `open()` — which opened whatever path the input resolved to — was replaced with a resolve-then-confirm step:

- `base = os.path.realpath(BASE_DIR)` — the canonical, absolute form of the allowed directory.
- `path = os.path.realpath(os.path.join(base, filename))` — the canonical form of the *requested* path, with every `../` collapsed and any absolute component resolved.
- `if not path.startswith(base + os.sep): abort(404)` — the containment check: unless the resolved path sits inside `base`, refuse.

The vulnerable version also echoed the assembled path to the page; that is gone in the fixed version, which has no unconfined path worth showing.

## Why this fixes the bug

`os.path.realpath` does the work the vulnerable version skipped: it *resolves* the path. `../../../../etc/passwd` collapses to `/etc/passwd`; the absolute `/etc/passwd` resolves to `/etc/passwd`; `../app.py` collapses to `/app/app.py`. Whatever tricks the input used to point outside the folder, after `realpath` you are looking at the single real file it names. The prefix check then asks the only question that matters — *is that file inside the directory I'm allowed to serve?* — and refuses when it isn't. Both the relative and the absolute vector from the walkthrough resolve to `/etc/passwd`, which is not under `/app/files/`, so both get the same `abort(404)`. One check, every route closed.

Two details earn their keep:

- **`realpath`, not `abspath`.** `os.path.abspath` collapses `..` lexically but does not follow symlinks; `os.path.realpath` resolves symlinks too, closing a symlink-in-the-base escape. For this lab either would block the payloads, but `realpath` is the robust default.
- **`base + os.sep`, not just `base`.** Checking `path.startswith(base)` alone would wrongly accept a sibling directory: with `base = /app/files`, the string `/app/files-secret/x` *does* start with `/app/files`. Appending the separator (`/app/files/`) makes the check mean "inside this directory" rather than "shares this prefix". (`os.path.commonpath([base, path]) == base` is an even more robust way to express the same intent.)

It returns **404**, not 403 — and unlike `idor-numeric-id`, which returns **403** for a real object the caller may not access, that difference is deliberate. Here a rejected traversal and a genuinely missing in-base file (a typo like `nope.txt`) both return 404, so the two failure modes are indistinguishable: the attacker cannot use the status code to map which paths escape the sandbox versus which simply don't exist. 403 would confirm existence; 404 confirms nothing.

## Blocklisting `../` is a losing game

A tempting "fix" is to reject or strip the dangerous sequence — delete `../` from the input. Step 2 of the walkthrough already shows why that fails: the absolute path `/etc/passwd` reaches the same file with **zero `../`** in it. And even against relative traversal a string filter loses — `..%2f` (percent-encoded, which Werkzeug decodes back to `../`), `....//` (strip the inner `../` and `../` is what's left), `..\` on Windows, double-encoding. The root cause is not the `../` token; it is that the resolved path is never confined. As long as you filter the *input string* instead of confining the *resolved path*, escaping and blocklisting are a losing game — the same lesson `sqli-union-basic` teaches about escaping quotes and `command-injection-basic` about escaping shell metacharacters. The transferable rule across all three: **validate the result against what's allowed (here, a location under the base dir), not the input against what's forbidden.**

## `os.path.basename` and `send_from_directory` — simpler tools with a role

Two other approaches are worth knowing, neither of which is the general fix but both of which have a place:

- **`os.path.basename(filename)`** throws away every directory component, leaving just the final name (`../../etc/passwd` → `passwd`, `/etc/passwd` → `passwd`), so a traversal can never climb. It is simpler than resolve-and-confirm — and it is a legitimate *alternative* fix **when the app never needs subdirectories**. The moment the feature must serve `docs/readme.txt`, `basename` breaks it, and `realpath` + prefix check is the way. This atom uses the general fix so it holds regardless of the file layout.
- **`send_from_directory(directory, filename)`** is Flask's built-in file server, and it performs exactly this containment check for you (resolving the path and refusing anything outside `directory`). In real Flask code, prefer it to a hand-rolled `open()`. We hand-roll here only because the feature renders the contents *inline* in a `<pre>` rather than sending the file as a download — so we do by hand the same check `send_from_directory` would do internally.

## A01, not A03 — this is access control

The injection atoms all have the shape "input became code": SQL (`sqli-union-basic`), HTML/JS (the XSS atoms), shell (`command-injection-basic`). This one does not. Nothing the attacker sends is ever parsed or executed — a legitimate-looking filename simply steers the app to a *resource outside its intended scope*. That is Broken Access Control, and it is why the atom lives in A01.

It is the same shape as `idor-numeric-id`, the other A01 atom: there, changing a numeric ID (`/notes/1` → `/notes/2`) reaches an object that isn't yours; here, navigating the filesystem (`notes.txt` → `../../etc/passwd`) reaches a file that isn't yours. Both are "the app handed you a resource that wasn't meant for you," and both fixes are the check that was missing — an ownership check there, a confinement check here. Contrast that with `command-injection-basic`, its mechanic twin: there your input became a *command* (code); here it becomes a *location* (a path). Same destination (`/etc/passwd`), opposite mechanism — execution versus navigation — and opposite category (A03 versus A01).

## The bug lives in app.py (the inverse of the XSS pair)

Here `vulnerable/app.py` and `fixed/app.py` differ — the missing confinement is in the Python code, and the templates (bar the incidental "Resolved path" echo) are the same. That is the mirror image of `xss-stored` and `xss-reflected`, where `app.py` was byte-identical between versions and the bug lived entirely in the template. Same audit lens, different location: for path traversal you read the code for file-handling calls (`open`, `os.path.join`, `send_file`) and ask what confines the path; for XSS you read the templates for `|safe`. Knowing which file to open is half the audit.
