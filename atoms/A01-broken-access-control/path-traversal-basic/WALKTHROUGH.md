# Walkthrough — path-traversal-basic

## 1. Context

The app is a "file viewer." You type a filename on `/`, the form submits a `GET /view?file=<name>` request, and the server reads that file from its `files/` directory and shows you the contents — the kind of "open a document" feature you find in help centers and admin panels everywhere.

Like `command-injection-basic`, this one is worked entirely in Burp. The file is read on the server and its contents come straight back in the HTTP response, so there is nothing to execute in a browser — you see `/etc/passwd` right there in the Repeater response pane. The browser track in section 5 is a convenience, not a requirement.

And keep that atom in mind, because you are about to reach the **same destination** — `/etc/passwd` — by the **opposite route**. In `command-injection-basic` you made the app *run a command* of yours. Here you will make the app *open a file* of yours. One is execution; the other is navigation. Hold that contrast; section 4 closes on it.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/view` view builds its path like this:

```python
filename = request.args.get("file", "")
# VULNERABLE: user input joined onto the base dir and opened directly —
# nothing confines the resolved path to BASE_DIR
path = os.path.join(BASE_DIR, filename)
with open(path) as f:
    content = f.read()
```

The `filename` comes straight from the query string and is joined onto `BASE_DIR` (`/app/files`), then handed to `open()`. There is no dangerous "sink" in the injection sense — no shell, no SQL engine, no template. The app just opens the file the path points at. The bug is the thing that **isn't there**: no check that the resolved path stays *inside* `BASE_DIR`. `os.path.join` does not collapse `..`, and `open()` happily follows `../` back up the tree, so the caller decides where the app reads from.

This is a different audit lens than the injection atoms. There you grep for a dangerous call (`shell=True`, `f"...SELECT`, `|safe`). Here you find file-handling endpoints — `open(`, `os.path.join(`, `send_file(` — and ask one question: **what confines this path to the allowed directory?** When the answer is "nothing", you have a finding.

```bash
grep -rn 'open(\|os.path.join(\|send_file(' .
```

Two things the app does *right*, so you don't confuse them with the bug:

- **The contents are HTML-escaped.** `result.html` renders `<pre>{{ content }}</pre>` through Jinja's default autoescape (no `|safe`). If it didn't, reading a file that contains `<script>...` would turn the file's contents into live HTML — a reflected XSS stacked on top of the path traversal. Escaping keeps this atom to exactly one bug. It is *not* the path-traversal fix.
- **The 404 on a bad path is hygiene, not defense.** `try/except OSError: abort(404)` means a wrong `../` count or a typo returns a clean 404 instead of a 500 stack trace. It is orthogonal to the vulnerability and the fix, and identical in both versions — a *successful* traversal returns 200 with the file, nowhere near that path.

The `/view` view also echoes the assembled path back in a debug `<pre>` ("Resolved path"), which makes this lab easy to follow — you watch your filename become a filesystem path. In a real app you'd infer the path shape from behavior.

## 3. How the app serves files

The app is meant to serve only the files in its own `files/` directory — `notes.txt` and `readme.txt`, listed on the home page. That is the "allowed" set: the legitimate feature never needs anything else. The exploit makes the app serve files from *outside* that directory. Use the "Resolved path" block on each result page to watch exactly which path the app opened — it is the clearest window into the traversal.

## 4. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8010/>, submit `notes.txt` through the form once to capture the traffic, then right-click the `GET /view?file=notes.txt` request in **Proxy → HTTP history** and choose **Send to Repeater**.

### Baseline — the tool doing its job

Send the captured request as-is and read the response. The "Resolved path" block shows `/app/files/notes.txt`, and the contents are the seed file:

```
Resolved path:
/app/files/notes.txt

Contents:
Project notes
-------------
- Ship the file viewer demo.
- Ask design for the new icon.
- Nothing secret here — this is just seed content.
```

That is the feature working as intended — it served a file it offers. Now steer it out of the folder.

### A note on URL encoding

The traps of the injection atoms are gone here. There are no spaces and no `&` in these payloads, and `.` and `/` travel raw in a query-string *value* — so `?file=../../../../etc/passwd` goes on the wire exactly as written, no encoding needed. (In `command-injection-basic` a space had to be `%20` and `&&` had to be `%26%26`; none of that applies.)

One encoding fact is worth knowing, and it matters for the fix. `..%2f` is the percent-encoded form of `../`, and Werkzeug decodes `%2f` back to `/` in a query value — so `file=..%2f..%2fetc%2fpasswd` arrives as `../../etc/passwd` and behaves identically. That is exactly the trick that slips past a naïve filter which only blocks the literal string `../` (see `DIFF.md`). The browser form encodes `/` to `%2f` on submit and the server decodes it right back — same result. If you ever want Burp to encode a value for you, select it and press **Ctrl+U**.

Each step below shows a **Payload** (decoded, for reading) and a **Request line** (ready to paste into Repeater).

### Step 1 — Confirm the traversal

Climb out of the folder with `../` and read a file the app never meant to serve.

```
Payload:       ../../../../etc/passwd
Request line:  GET /view?file=../../../../etc/passwd HTTP/1.1
               Host: 127.0.0.1:8010
```

Response — the "Resolved path" block shows your filename became a path that walks up the tree, and the contents are the container's entire `/etc/passwd`:

```
Resolved path:
/app/files/../../../../etc/passwd

Contents:
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/run/ircd:/usr/sbin/nologin
_apt:x:42:65534::/nonexistent:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
```

Your input was not a confined filename; it was a **route through the filesystem**. `os.path.join("/app/files", "../../../../etc/passwd")` becomes `/app/files/../../../../etc/passwd`, and `open()` lets the OS resolve the `..` right up to the root.

**How many `../`?** The base is `/app/files`, two levels below `/`, so the *minimum* to reach `/etc/passwd` is `../../etc/passwd` (two). This step sends four. The extras are harmless — `..` at `/` just stays at `/` (the root's parent is the root) — and on a real target you rarely know the exact depth, so overshooting is the habit. Both `../../etc/passwd` and `../../../../etc/passwd` read the same file.

### Step 2 — It's not the `../`: the path just isn't confined

The natural wrong conclusion is "the app should have blocked the `../`." It shouldn't matter whether you use `../` at all — the path is simply not confined to the folder. Prove it with a payload that contains **no `../` whatsoever**: an absolute path.

```
Payload:       /etc/passwd
Request line:  GET /view?file=/etc/passwd HTTP/1.1
               Host: 127.0.0.1:8010
```

Response — the **same** `/etc/passwd` contents as Step 1, but look at the resolved path:

```
Resolved path:
/etc/passwd
```

The base directory is *gone*. `os.path.join("/app/files", "/etc/passwd")` returns `/etc/passwd` — when a component is absolute, `os.path.join` discards everything before it. You reached the exact same file without a single `../`.

Sit with that. A developer who "fixes" this by stripping `../` from the input has done nothing: `/etc/passwd` sails straight through. The bug was never the `../` token — it is that the app opens whatever path the input resolves to, with no check that it landed inside the folder. That is why blocklisting is a losing game, and why the real fix (section 6) *resolves the path and confirms the destination* instead of scrubbing characters. In `command-injection-basic` the parallel lesson was "escaping metacharacters is a losing game — drop the shell"; here it is "filtering `../` is a losing game — confine the path."

### Step 3 — Read beyond /etc/passwd: the app's own source

`/etc/passwd` proves you escaped the folder. To prove the reach is *arbitrary*, read something that matters — the application's own source code:

```
Payload:       ../app.py
Request line:  GET /view?file=../app.py HTTP/1.1
               Host: 127.0.0.1:8010
```

Response — the running server's source, straight off disk:

```
Resolved path:
/app/files/../app.py

Contents:
import os
from flask import Flask, request, render_template, abort

app = Flask(__name__)
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
...
    path = os.path.join(BASE_DIR, filename)
    with open(path) as f:
        content = f.read()
...
```

Notice this took only **one** `../` — `app.py` lives in `/app`, one level above `/app/files`, while `/etc/passwd` needed two (and Step 1 overshot to four). The number of `../` depends on where the target sits relative to the base: you are *walking the tree* and counting steps to your destination. That is the whole mental model — navigation, not incantation.

(One aside that ties back to section 2: in the raw Burp response the `"` characters in the source show up as `&#34;` — that is the app HTML-escaping the file contents, exactly the hygiene we flagged. It is harmless here, and your browser renders them back to `"`.)

**What this really is.** Here the file is read inside a throwaway, isolated container, so dumping `/etc/passwd` or the app's source as `root` is harmless — that isolation is the safety net for this lab. On a real target this is **arbitrary file read**: source code, `.env` files, config, SSH keys, cloud credentials — anything the server process can read. It is read-only (unlike its twin), but a leaked credential or a leaked source tree routinely *chains* into deeper compromise. Keep your payloads demonstrative — read a file, print a passwd; there is no reason to reach for anything destructive, and no need to dump sensitive files like `/etc/shadow` gratuitously just because `root` can.

### Why this is path traversal, not command injection

You just read `/etc/passwd` — the same file `command-injection-basic` handed you. But nothing here executed. The distinction is the whole point of this atom:

> In `command-injection-basic` you made the app **run a command** of yours. Here you made the app **open a file** of yours — using the very capability it already had (opening files), just pointed outside its own yard. One is **execution**; the other is **navigation**. Both handed you `/etc/passwd`, but by opposite routes: command injection *ran `cat` for you*; path traversal made the app *itself be* the `cat`. In command injection you had to **invoke** `cat`; here the vulnerable file viewer already **is** a read-a-file-and-print-it machine — you only redirected it out of its folder. **The app *is* `cat`.**

|  | command injection | path traversal (this atom) |
|---|---|---|
| The app... | **executes** a program | **opens and reads** a file |
| Your input becomes | a **command** | a **path / filename** |
| You gain the power to | run **anything** (RCE) | read **any file** (read-only) |
| `/etc/passwd` comes out because | you told it to **execute** `cat /etc/passwd` | you **navigated** to it with `../` |
| The original feature was | run a `ping` | serve a file |
| OWASP category | A03 — Injection | A01 — Broken Access Control |

That last row is why this atom lives in **Broken Access Control**, not Injection: nothing became code, a filename simply steered the app to a resource outside its scope. It is the same shape as `idor-numeric-id` — there you changed a numeric ID (`/notes/1` → `/notes/2`) to read another user's note; here you navigate the filesystem (`notes.txt` → `../../etc/passwd`) to read a file that isn't yours to see. In both, the app handed you something that wasn't meant for you, and in both the fix is the check that was missing — an ownership check there, a confinement check here.

## 5. Exploitation via browser (secondary track, optional)

The same payloads work straight from the address bar — no Burp required:

1. <http://127.0.0.1:8010/view?file=../../../../etc/passwd>
2. `http://127.0.0.1:8010/view?file=/etc/passwd`
3. <http://127.0.0.1:8010/view?file=../app.py>

The browser does **not** normalize `../` in the query string (it only collapses dot-segments in the URL *path*), so these travel through intact; the form encodes `/` to `%2f` on submit and the server decodes it back. Use this for the first read-through; switch to Burp when you want byte-level control over the payload, which is how you'd work a real target — and it's the only place the `..%2f` encoding trick from section 4 is visible.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short, the fixed `/view` view resolves the requested path to its canonical form and confirms it stays inside the base directory before opening it:

```python
base = os.path.realpath(BASE_DIR)
path = os.path.realpath(os.path.join(base, filename))
if not path.startswith(base + os.sep):
    abort(404)
```

`os.path.realpath` collapses every `../` (and resolves an absolute component) down to a real, canonical path; the prefix check then confirms that path still sits under `/app/files/`. Replay every payload from section 4 against <http://127.0.0.1:8110/view>:

- `file=notes.txt` → **200**, the file (it's inside the base).
- `file=../../../../etc/passwd` → **404** (resolves to `/etc/passwd`, outside the base).
- `file=/etc/passwd` → **404** (resolves to `/etc/passwd`, outside the base).
- `file=../app.py` → **404** (resolves to `/app/app.py`, outside the base).

One check, and *every* route — relative, absolute, encoded — comes back 404, while the legitimate file still serves. That is the proof the two vectors from Steps 1 and 2 were the same bug: confinement was missing, and adding it closes all of them at once. Note it returns **404**, not 403 — unlike `idor-numeric-id`, which returns 403 for a real object you may not access. Here a rejected path and a genuinely missing file both return 404, so an attacker can't even tell which paths escape the sandbox. Trying to *blocklist* `../` would be a losing game (`..%2f`, `....//`, and the plain absolute `/etc/passwd` all defeat it); `DIFF.md` also covers `os.path.basename` as a simpler alternative when the app needs no subdirectories, and Flask's `send_from_directory`, which does this containment check for you.
