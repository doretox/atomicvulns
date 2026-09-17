# xss-reflected — Reflected Cross-Site Scripting

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic reflected XSS. A "post search" endpoint echoes the `q` query parameter back into the response page through a Jinja template that marks the value as `|safe`, disabling the autoescape that would normally encode `<`, `>`, `&`, `'`, and `"`. Any HTML or `<script>` the attacker sends in `q` runs in the browser under the app's origin.

> **Theory primer:** Read [PortSwigger: Reflected cross-site scripting (XSS)](https://portswigger.net/web-security/cross-site-scripting/reflected)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up xss-reflected
```

- Vulnerable app: <http://127.0.0.1:8002/>
- Fixed app: <http://127.0.0.1:8102/>

Stop with `./atom down xss-reflected`. If you prefer raw Docker: `cd atoms/A03-injection/xss-reflected && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8102 serves the same feature against the same seed posts. Run every payload from `WALKTHROUGH.md` against it — the page should render the payload as literal text (angle brackets visible on screen, nothing executed), never as live HTML or JavaScript.
