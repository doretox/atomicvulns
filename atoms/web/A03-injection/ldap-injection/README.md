# ldap-injection — LDAP injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask + OpenLDAP lab for LDAP injection. A corporate-style login endpoint — `POST /login` — takes a `user` and a `password` and authenticates them against an LDAP directory: it builds a search filter and considers you logged in if the search returns anyone — `(&(uid=<user>)(userPassword=<password>))`. The catch is that an LDAP search filter is not inert text — it is **structure** (RFC 4515), and characters like `*`, `(`, `)` and `\` are *syntax*, not data. The endpoint pastes whatever the client sent straight into that filter, so those metacharacters are interpreted as filter logic. Send `*` as the password and the filter becomes `(&(uid=admin)(userPassword=*))` — "an `admin` that simply *has* a password" — and you log in as `admin` without knowing it.

The lesson is that the root cause is **concatenating untrusted input into the filter without escaping it**: the value stops being a value and becomes filter structure. The fix is not to validate or blocklist "weird" characters — it is to **escape the RFC 4515 metacharacters** (`escape_filter_chars`) in every untrusted value before the filter is built, so `*` `(` `)` `\` turn into literal data (`\2a` `\28` `\29` `\5c`) and the filter stays the one the code intended.

> **Theory primer:** Read [PortSwigger: LDAP injection](https://portswigger.net/kb/issues/00100500_ldap-injection)
> before working through this atom, and skim the [OWASP LDAP Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LDAP_Injection_Prevention_Cheat_Sheet.html)
> for the defense. The atoms in this repo show *how* a vulnerability happens in
> code; those references explain *what* it is and why it matters.

## Stack note — a real OpenLDAP directory

Unlike the SQL injection atoms (`sqli-union-basic` and its blind siblings), which embed SQLite as a file inside the process, this atom needs a real directory *server*: OpenLDAP. So the lab runs **three containers** — one shared `ldap`, plus `vulnerable` and `fixed`, both querying the same seeded directory. The `ldap` service has **no host port**: it is reachable only on the compose's internal network (`ldap://ldap:389`), never published to your machine — only the two apps bind to `127.0.0.1`. The apps talk to it with **`ldap3`**, a pure-Python LDAP client (chosen over `python-ldap` so there is no native `libldap`/build toolchain to install). The directory is seeded with two fake users (`admin`, `jdoe`) whose passwords are stored in plaintext — a lab simplification so the naive `(userPassword=<value>)` match works; password storage is orthogonal to the LDAP injection fix (see `DIFF.md`). The apps bind as a **low-privilege service account** (`cn=svc`), not the directory admin, so the bypass you will see is LDAP injection and not an over-privileged connection.

## API only — no HTML, no browser

This atom has no web UI: no templates, no landing page, every response is JSON. You drive it entirely from **Burp Suite (Repeater)** or `curl`, and the proof is the login response itself — nothing executes in a browser. `WALKTHROUGH.md` works exclusively from Burp.

## Run

From the repo root:

```bash
./atom up ldap-injection
```

- Vulnerable API: `http://127.0.0.1:8028`
- Fixed API: `http://127.0.0.1:8128`

`GET /` returns a warning banner; the entry point is `POST /login` (see `WALKTHROUGH.md`). The `ldap` container is never published — only the two apps are. Stop with `./atom down ldap-injection`. If you prefer raw Docker: `cd atoms/A03-injection/ldap-injection && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (API-only; no browser track).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8128 serves the same login against the same directory. It adds one thing — `escape_filter_chars` around `user` and `password` before the filter is built — and changes nothing else. Replay the walkthrough against it: the real string credential still logs in with `200`, and the `*` payload that bypassed the vulnerable app now returns `401`, because the metacharacter is escaped to the literal `\2a` and can no longer be filter structure.
