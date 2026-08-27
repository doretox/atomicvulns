# Walkthrough — cors-wildcard

The target is a small JSON API. You log in, the server sets a **session cookie**, and `GET /account` returns your private account data as long as your browser sends that cookie. The endpoint is correct — it requires the cookie and returns the data to its owner. The flaw is the **CORS** policy wrapped around it: the server reads the request's `Origin` header and reflects it straight back in `Access-Control-Allow-Origin`, together with `Access-Control-Allow-Credentials: true`. That tells the browser "any site may read this response, with the victim's cookies." So a page on another site can make the victim's browser fetch `/account` — with the victim's cookie attached — and *read* the private response. The victim never approved it, and the attacker never knew the password or touched the cookie.

## 1. Context

`GET /account` returns data that belongs to one logged-in user. To see what goes wrong you need one browser rule and the mechanism that relaxes it.

An **origin** is the triple **scheme + host + port** — `http://victim.localhost:8034` and `http://attacker.localhost:8234` are different origins (different host and port), and `http://victim.localhost:8034` and `http://victim.localhost:8134` are different origins too (different port). The **Same-Origin Policy (SOP)** is the browser rule that lets a script on one origin *send* a request to another origin but forbids it from *reading* the response. It is what stops a script on `evil.com` from calling `bank.com`, where you are logged in, and reading your account page. (Its other half — *sending* a cross-origin request you cannot read — is what [`csrf-basic`](../../A01-broken-access-control/csrf-basic/) abuses. This atom is the read half.)

**CORS (Cross-Origin Resource Sharing)** is how a server deliberately relaxes the SOP so chosen origins *can* read its responses. It works through **response headers**, and it is an instruction to the *browser*, not a lock on the server: the server always returns the body; CORS only tells the browser whether to hand that body to the script that called. Two headers matter here:

- **`Access-Control-Allow-Origin`** (ACAO) — names which origin may read the response. It can be a specific origin, or the wildcard `*` ("any origin").
- **`Access-Control-Allow-Credentials: true`** (ACAC) — adds "…even when the request carried credentials," i.e. the victim's cookies. Without it, the browser blocks the script from reading a response to a **credentialed request** — a `fetch(url, { credentials: 'include' })`, which tells the browser to attach the target's cookies to a cross-origin call.

One more term for later: a **preflight** is an extra `OPTIONS` request the browser sends *before* certain "non-simple" cross-origin requests (custom methods or headers) to ask permission. A plain `GET` with no custom headers — like the one this attack uses — is a "simple request" and triggers **no** preflight; the browser sends it directly and then checks the ACAO/ACAC on the response before exposing it.

Three services, none of which talk to each other on the backend — the victim's browser makes every cross-origin request:

- `vulnerable` victim — `http://victim.localhost:8034/`
- `fixed` victim — `http://victim.localhost:8134/`
- `attacker` page — `http://attacker.localhost:8234/` (a **different origin** from the victim)

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

Audit question: *the server names which origin may read the response — how does it decide?* It doesn't. It echoes back **whatever `Origin` the request sent**, and adds `Access-Control-Allow-Credentials: true`. That is "yes, you may read this, with the victim's cookies" to *any* origin that asks. (The fix, foreshadowed: decide with an exact-match allowlist, not a mirror.)

## 3. The tell — the reflected origin (in Burp)

Before touching the browser, confirm the misconfiguration on the wire. Proxy through Burp and send `GET /account` to Repeater, adding one header — the attacker's origin (`curl` shown here as the equivalent):

```
$ curl -i -H "Origin: http://attacker.localhost:8234" \
       -H "Cookie: session_vuln=eyJ1c2VyIjoiZGVtbyJ9.apA98A.QK1fX5MSe2HOdyfjCKHq1VPRfeQ" \
       http://victim.localhost:8034/account
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://attacker.localhost:8234
Access-Control-Allow-Credentials: true
Content-Type: application/json

{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

The response reflects the exact origin you sent — `Access-Control-Allow-Origin: http://attacker.localhost:8234` — and adds `Access-Control-Allow-Credentials: true`. Send a different `Origin` and it mirrors that one too: the server approves *every* origin. That is the tell.

**But the tell is not the proof, and here is why.** Look again: `curl` printed the private body. So did Burp. They read `/account` regardless of any CORS header — because they are not browsers and simply ignore CORS. CORS is a rule the *browser* enforces on scripts; it is not an access control on the server. Pasting a cookie into `curl` and reading the response is not the exploit — there is no victim, no cross-origin script being allowed or denied. The vulnerability is that a **browser** will hand this response to a **script on another origin**, and that only reproduces in a browser.

## 4. Exploitation (in the browser)

The exploit needs a logged-in victim whose browser then visits the attacker's page. Drive a real browser (proxied through Burp if you want to watch the traffic).

### Log the victim in

The victim origin is a JSON API with no login form, so establish the session the way a logged-in victim would have one — from the victim's own origin. Browse to `http://victim.localhost:8034/` (you will see the JSON banner), open the DevTools **Console**, and log in with a same-origin request:

```js
await fetch('/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=demo&password=demo',
  credentials: 'include',
});
```

The server responds `Set-Cookie: session_vuln=...; Secure; HttpOnly; Path=/; SameSite=None`. Your browser now holds the victim's session cookie for `victim.localhost`. `SameSite=None` is what lets the browser attach it on a cross-origin request later; `Secure` is accepted over plain HTTP because `*.localhost` is a *secure context*. Confirm the same-origin read works (this is the ordinary, intended use):

```js
await (await fetch('/account', { credentials: 'include' })).json();
// {balance: 'USD 42,000.00', email: 'demo@example.com', user: 'demo'}
```

### Visit the attacker's page

Now, still logged in, browse to the attacker's page at `http://attacker.localhost:8234/attack-vuln`. Its only content is a script that makes the credentialed cross-origin fetch:

```js
fetch("http://victim.localhost:8034/account", { credentials: "include" })
  .then(r => r.text())
  .then(body => { document.getElementById("loot").textContent = body; })
  .catch(e => { document.getElementById("loot").textContent = "CORS error: " + e; });
```

The page renders the victim's private data — read from another origin:

```
Data read cross-origin from http://victim.localhost:8034/account:
{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

That is the attack. The victim's browser attached the `victim.localhost` cookie to the cross-origin request (`credentials: 'include'`), the server returned the private data with the reflected CORS policy, and the browser — obeying that policy — handed the response to the **attacker's** script. The attacker read the victim's account balance and recovery email without ever knowing the password or reading the cookie.

Everything here is benign and local: a fake account with a dummy balance, everything on loopback, nothing destructive.

## 5. What the vuln is NOT

The `/account` request looks legitimate, so isolate what actually went wrong:

- **NOT missing authentication.** The endpoint requires the cookie and checks it — the victim's own same-origin read in Section 4 proves auth works. What the flaw exposes is the *read of the response* to another origin. Proof of isolation: log in on the fixed app (`:8134`) and read `/account` same-origin and you get the identical data — only the *cross-origin* read differs between the two apps.
- **NOT CSRF.** [`csrf-basic`](../../A01-broken-access-control/csrf-basic/) makes the browser *send* a state-changing request the attacker cannot read — a blind write. Here the attacker *reads* authenticated data. Opposite directions across the same Same-Origin Policy: send versus read.
- **NOT "the `*` is the danger."** The literal `Access-Control-Allow-Origin: *` does **not** work for authenticated theft — the browser refuses to expose a credentialed response when the header is `*`, so `*` leaks only public data. The vector is **origin reflection**: echoing a *specific* origin, which the browser accepts together with credentials. Reflection exists precisely to get around the `*`-plus-credentials refusal.
- **NOT injection or a bug in the endpoint's code.** `/account` is logically correct — it authenticates and returns the right data. The flaw is the CORS **policy** (a configuration), which is why this is **A05 — Security Misconfiguration**, not an application logic bug.
- **NOT a server-side leak.** `curl` and Burp read the response no matter what (Section 3) — CORS never stops them. What the misconfiguration breaks is the protection the *browser* would have given the victim: refusing to hand a cross-origin response to a hostile script.

What it **is**: the server instructs the browser (via the reflected CORS headers) to let *any* origin read the authenticated response, so a script on the attacker's page reads the victim's private data. The fix is an exact-match allowlist of origins the server actually trusts.

## 6. Impact

**Cross-origin exfiltration of authenticated data.** Any origin the victim visits while logged in can read whatever `/account` returns — here the account balance and recovery email; in the real world, any private endpoint with this policy (profile, messages, tokens, keys). No overclaim: this is a **read**, not a write — the attacker cannot *change* the account (that is the other half of the SOP, the write side that `csrf-basic` covers), and it is not code execution on the server. The ceiling is exactly what the authenticated endpoint returns.

## 7. Why the fix works

Point the attacker page at the fixed victim: with a session established at `http://victim.localhost:8134/` the same way as in Section 4 (its cookie is `session_fixed`), browse to `http://attacker.localhost:8234/attack-fixed`. The page shows:

```
Data read cross-origin from http://victim.localhost:8134/account:
CORS error: TypeError: Failed to fetch
```

and the browser console spells out why:

```
Access to fetch at 'http://victim.localhost:8134/account' from origin
'http://attacker.localhost:8234' has been blocked by CORS policy: No
'Access-Control-Allow-Origin' header is present on the requested resource.
```

The attacker's script got **nothing**. Look closely at what happened, because it is the crux: the request **still reached the server**. The fixed victim logged `GET /account HTTP/1.1" 200` and returned the private data — the browser had attached the `session_fixed` cookie and the server answered exactly as before. What changed is that the response carried **no `Access-Control-Allow-Origin` for the attacker's origin**, so the browser refused to hand the body to the script. The cookie rode along and the server answered; the browser blocked the *read*.

The fixed app replaces reflection with an **exact-match allowlist** ([`fixed/app.py`](./fixed/app.py)):

```python
ALLOWED_ORIGINS = {"http://partner.localhost:9000"}

@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp
```

The fix is **not** "delete CORS": a legitimate partner origin still needs to read this API, and it still can. Confirm with the tell — the allowlisted partner is reflected, the attacker is not:

```
$ curl -s -D - -o /dev/null -H "Origin: http://partner.localhost:9000" http://victim.localhost:8134/account
Access-Control-Allow-Origin: http://partner.localhost:9000
Access-Control-Allow-Credentials: true

$ curl -s -D - -o /dev/null -H "Origin: http://attacker.localhost:8234" http://victim.localhost:8134/account
HTTP/1.1 200 OK
        # no Access-Control-Allow-Origin at all — the browser blocks the attacker's read
```

Note what did **not** change: the session cookie is `SameSite=None; Secure` on both apps, and `/account` is byte-for-byte identical. The CORS policy is the *only* security difference — which isolates that the fix is the allowlist, not something about the endpoint or the cookie. See [`DIFF.md`](./DIFF.md) for the one-policy change and why "check the `Origin` ends with our domain," "just drop the credentials," and "use `*`" are not the fix.
