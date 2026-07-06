# path-traversal-basic — Path Traversal

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic path traversal. A "file viewer" joins the `file` query parameter onto a base directory with `os.path.join(BASE_DIR, file)` and `open()`s the result, returning the file's contents in the response. Nothing confines that path to the base directory, so an attacker who sends `file=../../../../etc/passwd` walks out of the folder and reads an arbitrary file off the server — its contents come straight back on the page. This is **A01, not injection**: nothing becomes code, a legitimate-looking filename simply steers the app to a resource outside its scope. It is the mechanic twin of `command-injection-basic` — both end at `/etc/passwd`, but by opposite routes. There you made the app *run a command* (`cat`); here you make the app *open a file*, using the read-a-file capability it already had, just pointed out of its own yard. One is execution, the other is navigation — and because this one only reads, its impact is **arbitrary file read** (source, config, credentials), not the remote code execution of its twin.

> **Theory primer:** Read [PortSwigger: Path traversal](https://portswigger.net/web-security/file-path-traversal)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Stack note — files on disk, no database

Unlike `sqli-union-basic`, this atom has no database. Its "data" is a handful of real text files in a `files/` directory (`notes.txt`, `readme.txt`) that the app is meant to serve. That directory is the whole point: it gives the legitimate baseline (read a file the app offers) and the sandbox the attacker escapes from. The loot here isn't a table — it's the filesystem itself. The storage choice in each atom follows the surface of the bug.

## Run

From the repo root:

```bash
./atom up path-traversal-basic
```

- Vulnerable app: <http://127.0.0.1:8010/>
- Fixed app: <http://127.0.0.1:8110/>

Stop with `./atom down path-traversal-basic`. If you prefer raw Docker: `cd atoms/A01-broken-access-control/path-traversal-basic && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary) and browser (secondary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8110 serves the same file viewer. It resolves the requested path with `os.path.realpath` and confirms the result still sits inside the base directory (`path.startswith(base + os.sep)`) before opening it — otherwise it returns **404**. Run every payload from `WALKTHROUGH.md` against it: `../../../../etc/passwd`, the absolute `/etc/passwd`, and `../app.py` all come back **404**, while `notes.txt` still returns 200. One check kills every traversal route — the proof they were the same bug.
