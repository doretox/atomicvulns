# xxe-basic — XML External Entity (XXE) injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic, in-band XXE. The app is a "contact importer": you paste a contact card as XML, the server parses it and echoes the imported contact's name back to you. The parser resolves **external entities**, so a document whose `DOCTYPE` declares a `SYSTEM` entity pointing at `file:///etc/passwd` makes that entity expand to the file's contents — and the app hands them back in the `name` field. The same feature that imports `Ada Lovelace` reads arbitrary files off the server.

This is the repo's first atom in A05 — Security Misconfiguration. The root cause fits A05 exactly: a parser feature — external-entity resolution — that should be off is on. Mechanically XXE is an *injection*: untrusted input reaching an engine (the XML parser) that does more than intended — the same shape as `sqli-union-basic` and `command-injection-basic`, where the engine is a SQL database and a shell. Here the engine is the XML parser, and the bug and the fix are a single parser setting. The impact is the same as `path-traversal-basic` — arbitrary file disclosure, `/etc/passwd` and the app's own files — reached through a different door.

> **Theory primer:** Read [PortSwigger: XML external entity (XXE) injection](https://portswigger.net/web-security/xxe)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Library note — why lxml, not the standard library

Python's standard-library XML parser (`xml.etree.ElementTree`) does **not** resolve external entities, so an atom built on it would not be vulnerable. This lab uses **`lxml`**, the popular third-party parser, which *can*. In `lxml` 5.3.0 the bare default is safe — it refuses an undefined external entity — so the vulnerable app **opts in** by building its parser with `resolve_entities=True, load_dtd=True`. That is the realistic anti-pattern: a developer enables entity/DTD processing for legitimate reasons and inherits external-entity resolution with it. The fix turns those flags back off. See [`DIFF.md`](./DIFF.md) for the full reasoning, including why `defusedxml` is named but not used.

## Run

From the repo root:

```bash
./atom up xxe-basic
```

- Vulnerable app: <http://127.0.0.1:8018/>
- Fixed app: <http://127.0.0.1:8118/>

Stop with `./atom down xxe-basic`. If you prefer raw Docker: `cd atoms/A05-security-misconfiguration/xxe-basic && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8118 serves the same feature against the same input. Its parser disables external-entity resolution and DTD loading (`resolve_entities=False, load_dtd=False`), so a `SYSTEM` entity is never resolved. Replay every payload from `WALKTHROUGH.md` against it: the benign contact still imports as `Ada Lovelace`, but every `file://` payload comes back with an **empty** name — no file contents. The one and only change from `vulnerable/` is that parser configuration; see [`DIFF.md`](./DIFF.md).
