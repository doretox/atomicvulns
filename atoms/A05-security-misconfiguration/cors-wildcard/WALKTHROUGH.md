# Walkthrough — cors-wildcard

The target is a small API. You log in through its portal, the server sets a **session cookie**, and `GET /account` returns your private account data as long as your browser sends that cookie. The endpoint is correct — it requires the cookie and returns the data to its owner. The flaw is the **CORS** policy wrapped around it: the server reads the request's `Origin` header and reflects it straight back in `Access-Control-Allow-Origin`, together with `Access-Control-Allow-Credentials: true`. That tells the browser "any origin may read this response, with the victim's cookies." So a page on a **hostile sibling subdomain** — `evil.lab.localhost`, a compromised or taken-over subdomain of the victim's own site — can make the victim's browser fetch `/account` with the victim's cookie attached and *read* the private response. The victim never approved it, and the attacker never knew the password or touched the cookie.

## 1. Context

`GET /account` returns data that belongs to one logged-in user. To see what goes wrong you need one browser rule and the mechanism that relaxes it.

An **origin** is the triple **scheme + host + port** — `http://api.lab.localhost:8034` and `http://evil.lab.localhost:8234` are different origins (different host and port). Two origins are **same-site** when they share the same registrable domain (here `lab.localhost`) even if the subdomain differs, and **cross-origin** whenever the scheme, host, *or* port differs. So `api.lab.localhost` and `evil.lab.localhost` are **cross-origin** (different host) but **same-site** (both under `lab.localhost`) — hold onto that; it is why the attack works in a modern browser (below).

The **Same-Origin Policy (SOP)** is the browser rule that lets a script on one origin *send* a request to another origin but forbids it from *reading* the response. It is what stops a script on `evil.com` from calling `bank.com`, where you are logged in, and reading your account page. (Its other half — *sending* a cross-origin request you cannot read — is what [`csrf-basic`](../../A01-broken-access-control/csrf-basic/) abuses. This atom is the read half.)

**CORS (Cross-Origin Resource Sharing)** is how a server deliberately relaxes the SOP so chosen origins *can* read its responses. It works through **response headers**, and it is an instruction to the *browser*, not a lock on the server: the server always returns the body; CORS only tells the browser whether to hand that body to the script that called. Two headers matter here:

- **`Access-Control-Allow-Origin`** (ACAO) — names which origin may read the response. It can be a specific origin, or the wildcard `*` ("any origin").
- **`Access-Control-Allow-Credentials: true`** (ACAC) — adds "…even when the request carried credentials," i.e. the victim's cookies. Without it, the browser blocks the script from reading a response to a **credentialed request** — a `fetch(url, { credentials: 'include' })`, which tells the browser to attach the target's cookies to a cross-origin call.

One more term for later: a **preflight** is an extra `OPTIONS` request the browser sends *before* certain "non-simple" cross-origin requests (custom methods or headers) to ask permission. A plain `GET` with no custom headers — like the one this attack uses — is a "simple request" and triggers **no** preflight; the browser sends it directly and then checks the ACAO/ACAC on the response before exposing it.

**Why a sibling subdomain, not `evil.com`.** Modern browsers now **partition third-party cookies by top-level site** — Firefox's Total Cookie Protection is on by default, and third-party cookies are being removed elsewhere. A *purely* cross-site read (`evil.com` fetching `bank.com`) no longer carries the victim's cookie at all, so it would fail before CORS even mattered. Framing the attacker as a **same-site sibling** (`evil.lab.localhost` vs `api.lab.localhost`) keeps the cookie flowing — the request is still cross-*origin*, so CORS still governs the read — which isolates the lesson on the CORS policy and makes the exploit reproduce in today's browsers, Firefox included.

Three services, none of which talk to each other on the backend — the victim's browser makes every cross-origin request:

- `vulnerable` victim — `http://api.lab.localhost:8034/`
- `fixed` victim — `http://api.lab.localhost:8134/`
- `attacker` page — `http://evil.lab.localhost:8234/` (a hostile **sibling** of the victim)

Because CORS is enforced by the browser, that is where you exploit; Burp is a supporting lens that shows the misconfiguration on the wire.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). `GET /account` is ordinary and correct:

```python
@app.route("/account")
def account():
    if "user" not in session:
        return jsonify({"error": "not logged in"}), 403
    return jsonify(ACCOUNT)
```

It requires the session cookie and returns the data. The bug is the policy attached to *every* response:

```python
@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin        # reflection: the bug
        resp.headers["Access-Control-Allow-Credentials"] = "true"   # ...with the victim's cookies
    return resp
```

Audit question: *the server names which origin may read the response — how does it decide?* It doesn't. It echoes back **whatever `Origin` the request sent**, and adds `Access-Control-Allow-Credentials: true`. That is "yes, you may read this, with the victim's cookies" to *any* origin that asks — including a sibling subdomain that has been compromised. (The fix, foreshadowed: decide with an exact-match allowlist, not a mirror.)

## 3. The tell — the reflected origin (in Burp)

Before touching the browser, confirm the misconfiguration on the wire. Proxy your browser through Burp, log in once at `http://api.lab.localhost:8034/`, then send the `GET /account` request to **Repeater**. Add one header — the attacker sibling's origin — and resend:

```
GET /account HTTP/1.1
Host: api.lab.localhost:8034
Origin: http://evil.lab.localhost:8234
Cookie: session_vuln=eyJ1c2VyIjoiZGVtbyJ9...

HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://evil.lab.localhost:8234
Access-Control-Allow-Credentials: true
Content-Type: application/json

{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

The response reflects the exact origin you sent — `Access-Control-Allow-Origin: http://evil.lab.localhost:8234` — and adds `Access-Control-Allow-Credentials: true`. Change the `Origin` to anything else and it mirrors that one too: the server approves *every* origin. That is the tell. (The same request from the command line, if you prefer: `curl -i -H "Origin: http://evil.lab.localhost:8234" -H "Cookie: session_vuln=..." http://api.lab.localhost:8034/account`.)

**But the tell is not the proof, and here is why.** Look again: Repeater printed the private body. So would `curl`. They read `/account` regardless of any CORS header — because they are not browsers and simply ignore CORS. CORS is a rule the *browser* enforces on scripts; it is not an access control on the server. Replaying the request in Repeater with a cookie you hold is not the exploit — there is no victim, no cross-origin script being allowed or denied. The vulnerability is that a **browser** will hand this response to a **script on another origin**, and that only reproduces in a browser.

## 4. Exploitation (in the browser)

The exploit needs a logged-in victim whose browser then visits the sibling's page. Drive a real browser (proxied through Burp if you want to watch the traffic).

### Log the victim in

Browse to the victim portal at `http://api.lab.localhost:8034/`. It is a small HTML page — a warning banner and two buttons. Click **Log in (demo)**: the page fires an in-page `fetch('/login', …)` and shows

```
Logged in. Now click “View my account”.
```

The server set `Set-Cookie: session_vuln=...; Secure; HttpOnly; Path=/; SameSite=None`, so your browser now holds the victim's session cookie for `api.lab.localhost`. `SameSite=None` is what lets the browser attach it on a cross-origin request later; `Secure` is accepted over plain HTTP because `*.lab.localhost` is a *secure context*. Click **View my account** — the page fetches `/account` same-origin and shows your private data:

```
{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

This is the ordinary, intended use: you, on the victim's own origin, reading your own account.

### Visit the sibling's page

Now, still logged in, browse to the attacker sibling at `http://evil.lab.localhost:8234/attack-vuln`. Its only content is a script that makes the credentialed cross-origin fetch:

```js
fetch("http://api.lab.localhost:8034/account", { credentials: "include" })
  .then(r => r.text())
  .then(body => { document.getElementById("loot").textContent = body; })
  .catch(e => { document.getElementById("loot").textContent = "CORS error: " + e; });
```

The page renders the victim's private data — read from another origin:

```
Data read cross-origin from http://api.lab.localhost:8034/account:
{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

That is the attack. The victim's browser attached the `api.lab.localhost` cookie to the cross-origin request (`credentials: 'include'`, and the cookie was *not* stripped because the two are same-site), the server returned the private data with the reflected CORS policy, and the browser — obeying that policy — handed the response to the **sibling's** script. A compromised subdomain read the victim's account balance and recovery email without ever knowing the password or reading the cookie.

Everything here is benign and local: a fake account with a dummy balance, everything on loopback, nothing destructive.

## 5. What the vuln is NOT

The `/account` request looks legitimate, so isolate what actually went wrong:

- **NOT missing authentication.** The endpoint requires the cookie and checks it — the victim's own same-origin read in Section 4 proves auth works. What the flaw exposes is the *read of the response* by another origin. Proof of isolation: log in on the fixed app (`:8134`) and read `/account` same-origin and you get the identical data — only the *cross-origin* read differs between the two apps.
- **NOT CSRF.** [`csrf-basic`](../../A01-broken-access-control/csrf-basic/) makes the browser *send* a state-changing request the attacker cannot read — a blind write. Here the attacker *reads* authenticated data. Opposite directions across the same Same-Origin Policy: send versus read.
- **NOT "the `*` is the danger."** The literal `Access-Control-Allow-Origin: *` does **not** work for authenticated theft — the browser refuses to expose a credentialed response when the header is `*`, so `*` leaks only public data. The vector is **origin reflection**: echoing a *specific* origin, which the browser accepts together with credentials. Reflection exists precisely to get around the `*`-plus-credentials refusal.
- **NOT injection or a bug in the endpoint's code.** `/account` is logically correct — it authenticates and returns the right data. The flaw is the CORS **policy** (a configuration), which is why this is **A05 — Security Misconfiguration**, not an application logic bug.
- **NOT a server-side leak.** `curl` and Burp read the response no matter what (Section 3) — CORS never stops them. What the misconfiguration breaks is the protection the *browser* would have given the victim: refusing to hand a cross-origin response to a hostile script.

What it **is**: the server instructs the browser (via the reflected CORS headers) to let *any* origin read the authenticated response, so a script on a hostile sibling subdomain reads the victim's private data. The fix is an exact-match allowlist of origins the server actually trusts.

## 6. Impact

**Cross-origin exfiltration of authenticated data.** Any origin the victim visits while logged in can read whatever `/account` returns — here the account balance and recovery email; in the real world, any private endpoint with this policy (profile, messages, tokens, keys). The realistic setting is the one modeled here: a **hostile sibling subdomain** — a subdomain of the same organization that has been compromised, left running as forgotten staging, or seized through a subdomain takeover — turning an over-broad "trust our own domains" CORS policy into a data leak. That is a staple of bug-bounty reports. No overclaim: this is a **read**, not a write — the attacker cannot *change* the account (that is the other half of the SOP, the write side that `csrf-basic` covers), and it is not code execution on the server. The ceiling is exactly what the authenticated endpoint returns.

## 7. Why the fix works

Point the attacker page at the fixed victim: with a session established at `http://api.lab.localhost:8134/` the same way as in Section 4 (its cookie is `session_fixed`), browse to `http://evil.lab.localhost:8234/attack-fixed`. The page shows:

```
Data read cross-origin from http://api.lab.localhost:8134/account:
CORS error: TypeError: Failed to fetch
```

and the browser console spells out why:

```
Access to fetch at 'http://api.lab.localhost:8134/account' from origin
'http://evil.lab.localhost:8234' has been blocked by CORS policy: No
'Access-Control-Allow-Origin' header is present on the requested resource.
```

The attacker's script got **nothing**. Look closely at what happened, because it is the crux: the request **still reached the server**. The fixed victim logged `GET /account HTTP/1.1" 200` and returned the private data — the browser had attached the `session_fixed` cookie (same-site, as before) and the server answered exactly as before. What changed is that the response carried **no `Access-Control-Allow-Origin` for the attacker's origin**, so the browser refused to hand the body to the script. The cookie rode along and the server answered; the browser blocked the *read*.

The fixed app replaces reflection with an **exact-match allowlist** ([`fixed/app.py`](./fixed/app.py)):

```python
ALLOWED_ORIGINS = {"http://partner.lab.localhost:9000"}

@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp
```

The fix is **not** "delete CORS": a legitimate *sibling* — `partner.lab.localhost` — still needs to read this API, and it still can. That is the sharpened lesson: **not every sibling subdomain is trustworthy; you name the exact ones, you do not reflect the whole family.** Confirm with the tell — the allowlisted partner is reflected, the hostile sibling is not:

```
$ curl -s -D - -o /dev/null -H "Origin: http://partner.lab.localhost:9000" http://api.lab.localhost:8134/account
Access-Control-Allow-Origin: http://partner.lab.localhost:9000
Access-Control-Allow-Credentials: true

$ curl -s -D - -o /dev/null -H "Origin: http://evil.lab.localhost:8234" http://api.lab.localhost:8134/account
HTTP/1.1 403 FORBIDDEN
        # no Access-Control-Allow-Origin at all — the browser blocks the sibling's read
```

Note what did **not** change: the session cookie is `SameSite=None; Secure` on both apps, and `/account` is byte-for-byte identical. The CORS policy is the *only* security difference — which isolates that the fix is the allowlist, not something about the endpoint or the cookie. See [`DIFF.md`](./DIFF.md) for the one-policy change and why "trust our own subdomain family," "just drop the credentials," and "use `*`" are not the fix.
