# xss-stored — Stored Cross-Site Scripting

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for stored (persistent) XSS. A guestbook saves each visitor's comment to SQLite and renders every saved comment back to all later visitors through a Jinja template that marks the comment body as `|safe`, disabling the autoescape that would normally encode `<`, `>`, `&`, `'`, and `"`. A `<script>` planted once — by one visitor, in a single `POST` — runs in the browser of every visitor who later opens the page, with no link to click and no attacker present. To make the impact concrete, `GET /` also sets a non-HttpOnly `session` cookie that the walkthrough's final payload exfiltrates to a one-line listener.

> **Theory primer:** Read [PortSwigger: Stored cross-site scripting (XSS)](https://portswigger.net/web-security/cross-site-scripting/stored)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up xss-stored
```

- Vulnerable app: <http://127.0.0.1:8008/>
- Fixed app: <http://127.0.0.1:8108/>

Stop with `./atom down xss-stored`. If you prefer raw Docker: `cd atoms/A03-injection/xss-stored && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation: plant the payload via Burp Suite (primary track), then watch it fire in the browser (mandatory — Burp doesn't execute JavaScript).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8108 serves the same guestbook against the same seed comments, and still sets the same `session` cookie — that cookie was never the bug. It drops the `|safe` filter so the comment body flows through Jinja's default autoescape. Plant any payload from `WALKTHROUGH.md` and reload: the page renders it as literal text (angle brackets visible on screen, nothing executed), and the cookie-exfil listener stays silent. Same root cause and same one-line fix as [`xss-reflected`](../xss-reflected/) — only the delivery (persisted, third-party victim) changed.
