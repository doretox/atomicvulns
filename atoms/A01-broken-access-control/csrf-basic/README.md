# csrf-basic — Cross-Site Request Forgery (CSRF)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for Cross-Site Request Forgery (CSRF). The target is a logged-in account page with a "change recovery email" action: `POST /email` updates the account, and the server authorizes it by checking one thing — is there a valid session cookie? The browser attaches that cookie automatically to *every* request to the target, no matter which site triggered it. So a page on a **different site** (the `attacker` service) can host a hidden, auto-submitting `<form>` that fires a `POST /email` at the target; the victim's browser attaches their session cookie to that forged request, and the server changes the email as if the victim had asked — an account takeover (the attacker now controls the password-reset address). The cookie proves *who* you are, not *that you meant it*. The fix is a per-session anti-CSRF token the server puts in its own form and requires back in the request body: an attacker on another origin cannot read it (the Same-Origin Policy forbids reading a cross-origin response), so cannot forge the complete request — even though the cookie still rides along.

The naive version of this bug no longer fires: the modern browser default `SameSite=Lax` refuses to attach the session cookie to a cross-site `POST`, stopping it on its own. So the lab models the real-world conditions where CSRF still happens: two genuinely different sites, and a session cookie loosened to `SameSite=None` (the misconfiguration you meet in cross-site embeds and cargo-culted cookie settings).

> **Theory primer:** Read [PortSwigger: Cross-site request forgery (CSRF)](https://portswigger.net/web-security/csrf)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up csrf-basic
```

- Vulnerable target: <http://127.0.0.1:8023/>
- Fixed target: <http://127.0.0.1:8123/>
- Attacker site: <http://127.0.0.2:8080/> — a **different site** from the targets

`./atom up` prints only the two `127.0.0.1` targets; the attacker is on `127.0.0.2` (still loopback — `127.0.0.0/8` is local-only, never reachable off the host), so open it at the URL above. Log in to a target with `demo` / `demo`.

Stop with `./atom down csrf-basic`. If you prefer raw Docker: `cd atoms/A01-broken-access-control/csrf-basic && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation. The browser is where CSRF happens: it attaches the victim's cookie to the forged cross-site request on its own, which `curl` cannot reproduce (a cookie you paste by hand is just a normal authenticated request). Burp is a supporting lens that shows, on the wire, that the forged `POST` carries the session cookie and no token.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched target on port 8123 is byte-identical except for one thing: a per-session anti-CSRF token, generated server-side, embedded as a hidden field in its own email form, and required in the `POST /email` body. The session-cookie config is unchanged (`SameSite=None; Secure` on both sides) — the token is the *only* security difference, which isolates that the fix is the token, not re-tightening `SameSite`. Point the attacker page at the fixed target and the same forged `POST` returns `403`: the browser still attaches the session cookie, but the request has no token, and the attacker could not read one because the Same-Origin Policy blocks reading the target's form. The legitimate flow — the target's own form, which carries the token — still works on both sides. This is **A01 — Broken Access Control**: the server authorized a state-changing action from *whoever held a valid session*, without verifying the user *intended* it.
