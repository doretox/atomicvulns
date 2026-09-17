# open-redirect — Open Redirect

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for a classic Open Redirect. The app has a login form with the common "return you to where you were" pattern: the destination rides in a `next` parameter (`/login?next=/dashboard`), and after a successful login the server redirects you there — a `302` with `Location: <next>`. The bug is that it redirects to *whatever* `next` says, without checking the destination is one of its own pages. An attacker crafts a link that looks like the target — `http://127.0.0.1:8024/login?next=http://evil.example` — the victim trusts the target's domain, logs in normally, and the app throws them off-site to the attacker. The proof is in the response: the `302`'s `Location` header points at `evil.example`.

This is A01 — Broken Access Control (CWE-601, "URL Redirection to Untrusted Site"). The failed control is over *where the app may send the user*: it should only redirect within itself, but it hands that decision to user input and sends the victim out. The fix is server-side and structural — the **server** decides the destination with an allowlist. A legitimate login `next` is always an internal path, so `safe_next()` accepts only a path (no scheme, no host, no protocol-relative `//host`, no `\` trick) and otherwise falls back to a safe internal default. The one and only difference between `vulnerable/` and `fixed/` is that check.

> **Theory primer:** Read [OWASP: Unvalidated Redirects and Forwards Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the cheat sheet explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up open-redirect
```

- Vulnerable app: <http://127.0.0.1:8024/>
- Fixed app: <http://127.0.0.1:8124/>

Log in with `demo` / `demo`. Stop with `./atom down open-redirect`. If you prefer raw Docker: `cd atoms/A01-broken-access-control/open-redirect && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite. The proof is the `Location` header of the `302` in the response (Repeater, or `curl -i` without `-L`); no browser is needed.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8124 serves the same login and the same `next` feature. It passes `next` through `safe_next()` before redirecting: an internal path like `/dashboard` or `/settings` is honored, but anything carrying a host — `http://evil.example`, the protocol-relative `//evil.example`, a backslash `/\evil.example`, or a userinfo `https://demo@evil.example` — is refused and falls back to `/dashboard`. Replay every payload from `WALKTHROUGH.md`: `next=/dashboard` still returns `Location: /dashboard` on both apps, but the external destinations the vulnerable app emits verbatim now come back as `Location: /dashboard`. The one and only change from `vulnerable/` is that server-side structural check; see [`DIFF.md`](./DIFF.md). This is **A01 — Broken Access Control**: the server let user input pick a destination it should have constrained to its own pages.
