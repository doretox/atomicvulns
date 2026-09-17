# DIFF — vulnerable vs. fixed

The fix is one thing: replace **origin reflection** with an **exact-match allowlist**. The vulnerable app echoes back whatever `Origin` the request sent; the fixed app sets `Access-Control-Allow-Origin` only when the request's origin is exactly one it trusts. Everything else is unchanged — `GET /account`, `POST /login`, the account data, and the session-cookie config (`SameSite=None; Secure`) are all identical — so the CORS policy is the *only* security difference between the two apps.

## The change — `app.py`

```diff
+ALLOWED_ORIGINS = {"http://partner.lab.localhost:9000"}
+
 @app.after_request
 def add_cors(resp):
     origin = request.headers.get("Origin")
-    if origin:
-        resp.headers["Access-Control-Allow-Origin"] = origin        # reflect ANY origin
-        resp.headers["Access-Control-Allow-Credentials"] = "true"
+    if origin in ALLOWED_ORIGINS:                                   # exact match only
+        resp.headers["Access-Control-Allow-Origin"] = origin
+        resp.headers["Access-Control-Allow-Credentials"] = "true"
     return resp
```

`SESSION_COOKIE_NAME` also differs (`session_vuln` vs `session_fixed`) for a non-security reason: both victims live on `api.lab.localhost`, and cookies ignore the port, so a single cookie name would be shared between `:8034` and `:8134`. Distinct names keep the two logins apart. The two security-relevant cookie attributes — `SESSION_COOKIE_SAMESITE="None"` and `SESSION_COOKIE_SECURE=True` — are identical on both sides, and `GET /account`, `POST /login`, the imports, the account data, the `Dockerfile`, and `requirements.txt` are byte-for-byte identical.

## Why this fixes the bug

The vulnerable policy answered "yes, you may read this response, with the victim's cookies" to *whatever origin asked*, because it mirrored the request's `Origin` into `Access-Control-Allow-Origin`. The fixed policy answers that only for an origin it was told to trust. When the hostile sibling's origin (`http://evil.lab.localhost:8234`) is not in `ALLOWED_ORIGINS`, the response carries **no `Access-Control-Allow-Origin` header at all**, and the browser refuses to hand the response to the attacker's script.

The point to hold onto: the request still reaches the server. On the fixed app the credentialed fetch still arrives with the victim's cookie, and the server still returns the private data (`200`). What the browser refuses to do is *read* that response on behalf of a script from an origin the server did not allow. The defense is not stopping the request — it is declining to *authorize the read*, by naming exactly who may perform it.

## Reflection is the cause — not "missing authentication," not "sensitive data"

The most common misreading is that the endpoint "forgot to authenticate." It did not: `GET /account` requires the session cookie and returns the data only to a logged-in user — the victim's own same-origin read proves the auth works. It is also not that the data is "too sensitive to return" — the endpoint is *supposed* to return it, to its owner. The flaw is the response *policy* that tells the browser to let **any origin** read that response, cookies and all. Isolation proof: read `/account` same-origin on both apps and you get identical data; only the *cross-origin* read differs — the vulnerable app hands it to the attacker's script, the fixed app does not. The cause is the CORS policy, nothing else.

## Trap: "just trust our own subdomain family"

The reflection lets in a *sibling* — `evil.lab.localhost` is a subdomain of the same site as the victim. So the tempting half-fix is to trust the family: accept any origin under `lab.localhost`.

```python
# STILL VULNERABLE -- do not do this
if origin and origin.endswith(".lab.localhost"):
    resp.headers["Access-Control-Allow-Origin"] = origin
```

This is exactly the mistake. **Not every sibling subdomain is trustworthy.** `http://evil.lab.localhost:8234` ends with `.lab.localhost` — so it passes — and it is the attacker: a compromised, forgotten, or taken-over subdomain of your own site is precisely the origin you must *not* hand credentialed responses to. "Trust the whole family" waves the hostile sibling straight in. Suffix checks are fragile on top of that — without a leading dot, `http://evil-lab.localhost` also ends with `lab.localhost`; a crafted host like `http://lab.localhost.evil.example` is built to fool a careless contains-check. The test has to be an **exact match** against a set of full origins (`origin in ALLOWED_ORIGINS`) — you name the specific siblings you trust (here `partner.lab.localhost`), you do not trust the family.

## Trap: "just drop the credentials"

Another partial fix is to keep reflecting the origin but stop sending `Access-Control-Allow-Credentials: true`. This is an improvement, and worth being precise about: without that header the browser will **not** expose a *credentialed* response to a cross-origin script, so the *authenticated* theft in this atom stops — the cookie no longer buys the attacker the response. But you are still reflecting every origin, so any **public** (unauthenticated) data the endpoint returns still leaks to any site. It treats the symptom (credentialed reads) while leaving the root — reflecting any origin — in place. The root fix is the allowlist.

## The wildcard `*` is not the vector

The slug is `cors-wildcard`, and the instinct is that the danger is `Access-Control-Allow-Origin: *`. But the literal `*` does **not** work for authenticated theft: the browser refuses to expose a credentialed response when the header is `*`, so a `fetch(..., {credentials:'include'})` against a `*` policy fails to read the body. `*` leaks only *public* data. That refusal is exactly *why* origin reflection exists — echoing a **specific** origin produces a header the browser *will* accept together with credentials. So "just use `*`" is not even a working attack for authenticated data, and understanding that is what points you at the real vector: reflection.

## Don't add CORS you don't need — the honest surface fix

There is a simpler fix than an allowlist, when it applies: if an endpoint has **no** legitimate cross-origin consumer, it should send **no** CORS headers at all, and the SOP protects it for free. That is genuinely correct advice — not a trap. This atom models the other case, where the API *does* have a real cross-origin partner (`ALLOWED_ORIGINS` stands in for it), so removing CORS entirely would break a legitimate integration. There the fix is not "delete CORS" but "configure it correctly" — an exact-match allowlist naming the origins you actually trust. Both are right; which one applies depends on whether the endpoint is meant to be read cross-origin at all.

## The impact is exfiltration — and it is the mirror of CSRF

The vulnerable policy lets a script on another origin — here a hostile sibling subdomain (`evil.lab.localhost`) — **read** the victim's authenticated response cross-origin. No overclaim: it is a read, not a write; the attacker cannot change the account, and there is no code execution. The realistic setting is a compromised or taken-over subdomain of the same organization (a staple of bug-bounty reports). The class it mirrors is CSRF — both break the Same-Origin Policy at the origin boundary — so the contrast is worth drawing sharply:

| | **CSRF** (`csrf-basic`) | **CORS misconfiguration** (this atom) |
|---|---|---|
| Which half of the SOP | the **send** side — the browser fires a cross-site request | the **read** side — the browser exposes a cross-origin response |
| What the attacker achieves | **trigger** a state-changing action, blind (cannot read the reply) | **read** an authenticated response (exfiltration) |
| The victim's cookie | attached automatically to the forged request (`SameSite=None`) | attached to the credentialed `fetch` (`credentials:'include'`) |
| Root cause | trusts the cookie as proof of **intent** | CORS policy **reflects any origin** with credentials |
| Fix | per-session anti-CSRF token (attacker cannot read it) | exact-match **allowlist** of trusted origins |
| OWASP category | A01 — Broken Access Control | A05 — Security Misconfiguration |

The rule of thumb: **CSRF fires a request from outside and is blind; a CORS misconfiguration lets outside code read the reply.** Send versus read — the two halves of the Same-Origin Policy, broken in opposite directions.
