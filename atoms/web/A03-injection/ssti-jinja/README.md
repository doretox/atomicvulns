# ssti-jinja — Server-side template injection (SSTI)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic, in-band Server-Side Template Injection (SSTI). The app is a "personalized greeting": you send a `name` and it echoes `Hello, <name>!`. To build that greeting, the code sews your `name` straight into the template source and hands it to Jinja2 — Flask's template engine — through `render_template_string`. Because Jinja2 compiles whatever text it is given, a `name` that contains a `{{ ... }}` expression is *evaluated*, not displayed: `{{7*7}}` comes back as `49`, and `{{config}}` dumps Flask's configuration — including the `SECRET_KEY` that signs session cookies. The same feature that greets `Ada` reads the app's own secret.

This is A03 — Injection. Mechanically it is the same shape as `sqli-union-basic` and `command-injection-basic`: untrusted input reaching an engine that does more than intended — only the engine changes. There the engine is a SQL database and a shell; here it is the template engine. The bug is not "using Jinja2" (every Flask app does) — it is *where the input goes*: sewn into the template source (as code) instead of passed as data. The fix passes the name as data, and the one and only difference between `vulnerable/` and `fixed/` is that.

> **Theory primer:** Read [PortSwigger: Server-side template injection](https://portswigger.net/web-security/server-side-template-injection)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up ssti-jinja
```

- Vulnerable app: <http://127.0.0.1:8019/>
- Fixed app: <http://127.0.0.1:8119/>

Stop with `./atom down ssti-jinja`. If you prefer raw Docker: `cd atoms/A03-injection/ssti-jinja && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8119 serves the same greeting. It passes the name as data — `render_template_string("...Hello, {{ name }}!...", name=name)` — so Jinja2 fills the `{{ name }}` placeholder with the escaped value and never re-evaluates it. Replay every payload from `WALKTHROUGH.md` against it: `Ada` still greets as `Hello, Ada!`, but `{{7*7}}` comes back literal (`Hello, {{7*7}}!`) and `{{config}}` never dumps the `SECRET_KEY`. The one and only change from `vulnerable/` is passing the name as data instead of sewing it into the template source; see [`DIFF.md`](./DIFF.md).
