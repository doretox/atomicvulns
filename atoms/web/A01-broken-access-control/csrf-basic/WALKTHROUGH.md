# Walkthrough — csrf-basic

The target is an account page with one action: change the recovery email. You log in, type a new email, and `POST /email` updates the account. The server knows it is you because your browser sent the **session cookie** — the value it stored at login and re-sends automatically on every request to this site. That automatic re-send is the whole problem: the browser attaches the cookie no matter *which site* caused the request. A page on another site can contain a hidden `<form>` that fires a `POST /email` at this target from the victim's browser, and the browser will attach the victim's session cookie to it. The server sees a valid cookie and changes the email — as if the victim had asked. The victim never asked, and the attacker never knew the password or read the cookie.

## 1. Context

`POST /email` is a **state-changing request** — one that alters something on the server (here, the account's recovery email). The server authorizes it by checking one thing: is there a valid **session cookie**? This is **CSRF (Cross-Site Request Forgery)**: an attacker makes the victim's browser fire a state-changing request at a site the victim is logged in to, riding the victim's session. Two terms name the setup. **Cross-site** means the request originates from a *different site* than the target (a different registrable host — here `127.0.0.2` versus the target's `127.0.0.1`). The **Same-Origin Policy (SOP)** is the browser rule that lets one origin *send* a request to another but forbids it from *reading* the response — which is why CSRF is a blind, fire-and-forget attack: the attacker triggers the action but never sees the result.

There is one condition to make this fire. A cookie's **`SameSite`** attribute tells the browser when to attach it on cross-site requests; the modern default, `SameSite=Lax`, will **not** attach a cookie on a cross-site `POST`, which stops naive CSRF on its own. This target loosens its cookie to `SameSite=None` (the misconfiguration that reopens the hole — common in cross-site embeds and copy-pasted cookie settings). `SameSite=None` requires the `Secure` flag, which normally means HTTPS only; it works here over plain HTTP because `127.0.0.1` is a *secure context* (loopback origins are treated as trustworthy).

Three services, none of which talk to each other — the victim's browser makes every cross-site request:

- `vulnerable` target — `http://127.0.0.1:8023/`
- `fixed` target — `http://127.0.0.1:8123/`
- `attacker` site — `http://127.0.0.2:8080/` (a **different site** from the targets, still loopback)

Because the defining act of CSRF is the browser attaching the cookie on its own, the browser is where you exploit; Burp is a supporting lens that shows the forged request on the wire.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The whole bug is the authorization check on `POST /email`:

```python
@app.route("/email", methods=["POST"])
def change_email():
    if "user" not in session:
        return "Not logged in", 403
    ACCOUNT["email"] = request.form.get("email", "")
    return redirect("/")
```

The only gate is `if "user" not in session` — *is there a valid session cookie?* Audit question: *this endpoint changes state, and it checks only **who** is logged in — does it check that the user **intended** this specific request?* No token, no `Origin`/`Referer` check. The cookie proves identity, and the browser attaches it to any request to this site — including one a hostile page triggers. (The fix, foreshadowed: require a secret that only a page served by this site could contain.)

At login the server sets the session cookie with the loosened attributes:

```
Set-Cookie: session_vuln=...; Secure; HttpOnly; Path=/; SameSite=None
```

`SameSite=None` is the green light for the browser to attach this cookie on cross-site requests.

## 3. Exploitation (in the browser)

The defining act — the browser attaching the victim's cookie to a cross-site request — only happens in a browser, so this is where you exploit. Proxy the browser through Burp to capture the traffic for Section 4.

### Baseline — the feature

Open `http://127.0.0.1:8023/`, log in with `demo` / `demo`. The account page shows the current state and the legitimate change form:

```
Logged in as demo. Recovery email: demo@example.com
```

Change the email with the form and it updates — ordinary, intended use. The victim is now a logged-in user with a live session cookie.

### The attacker's page

The `attacker` service serves a page whose only content is a hidden form that submits itself on load. `http://127.0.0.2:8080/attack-vuln` is:

```html
<body onload="document.forms[0].submit()">
<form action="http://127.0.0.1:8023/email" method="POST">
  <input type="hidden" name="email" value="attacker@evil.example">
</form>
</body>
```

It is a plain HTML form `POST` (content type `application/x-www-form-urlencoded`) — a "simple request" that the browser sends cross-site **with cookies** and no CORS preflight. That is why the attack uses a form and not a JSON `fetch` (which would trigger a preflight the target hasn't allowed).

### Fire it

With the victim still logged in at `127.0.0.1:8023`, open the attacker page at `http://127.0.0.2:8080/attack-vuln`. The form auto-submits; the browser fires `POST /email` at the target and — because the cookie is `SameSite=None` — attaches the victim's session cookie to that cross-site request. Reload the target's account page:

```
Logged in as demo. Recovery email: attacker@evil.example
```

The recovery email is now the attacker's. **Account takeover:** whoever controls the recovery address can trigger a password reset and receive it. The victim only opened a page on another site.

Everything here is benign and local: a fake account, an `@evil.example` address (a reserved TLD), everything on loopback, nothing destructive.

## 4. What Burp shows (and why `curl` can't)

CSRF is driven from the browser, but Burp proves the mechanics. In **Proxy → HTTP history**, find the forged `POST /email` the attacker page triggered:

```
POST /email HTTP/1.1
Host: 127.0.0.1:8023
Cookie: session_vuln=eyJ1c2VyIjoiZGVtbyJ9...
Content-Type: application/x-www-form-urlencoded

email=attacker@evil.example
```

Two facts, together, are the whole vulnerability. **The session cookie is present** — the browser attached it automatically, even though the request came from `127.0.0.2`. **There is no token** in the body: just `email=...`. The server checked only the cookie, so the forged request was authorized. (Confirmed at the network layer with the browser's own cookie accounting: on the forged request, `session_vuln` is reported as sent, with no blocked reason.)

**Why `curl` is not the proof.** It is tempting to "reproduce" this from the Repeater or `curl`. It doesn't work as CSRF:

```
$ curl -X POST -d "email=x@evil.example" http://127.0.0.1:8023/email
Not logged in                       # HTTP 403 — no session cookie

$ curl -X POST -H "Cookie: session_vuln=<paste>" -d "email=x@evil.example" \
       http://127.0.0.1:8023/email
                                     # HTTP 302 — email changed
```

The second call works, but it is not CSRF: *you* pasted a cookie you already had. There is no victim, no other site, nothing tricked. CSRF is precisely the part `curl` cannot do — make a *victim's* browser attach *their* cookie to a request *the attacker* triggered from *another origin*. That only happens in a browser, which is why the exploit is browser-driven and Burp only observes.

## 5. What the vuln is NOT

The exploit is a legitimate-looking request, so isolate what actually went wrong:

- **NOT XSS.** No attacker code runs on the target. The attacker's form runs on the *attacker's* origin, fires a request, and — by the Same-Origin Policy — **cannot read the response**. The attack is blind: it changes state, it does not read data. "Cross-site" here is not "cross-site scripting." (In [`xss-reflected`](../../A03-injection/xss-reflected/), [`xss-stored`](../../A03-injection/xss-stored/), and [`xss-dom`](../../A03-injection/xss-dom/), attacker script runs *inside* the target's origin and can read everything; CSRF is the opposite — outside, and blind.)
- **NOT the attacker stealing the cookie.** The attacker never has, reads, or copies the session cookie. The victim's *browser* attaches it, on its own, to a request the attacker merely triggered. Section 4 showed the cookie present on the forged request while the attacker's page never touched it.
- **NOT a broken session or a login bypass.** The session is perfectly valid and the victim genuinely logged in. Unlike [`session-fixation`](../../A07-auth-failures/session-fixation/), where the flaw is in the session's lifecycle, here the session is correct. The hole is **intent**: the server treated "holds a valid session cookie" as "the user wanted this action."

What it **is**: the server authorizes a state-changing action on the cookie alone — *who* you are — without checking *that you meant it*. The fix requires proof of intent the attacker cannot supply.

## 6. Impact

**Account takeover via a forced state change.** The forged `POST` changes the account's recovery email to one the attacker controls; a subsequent "forgot password" sends the reset to the attacker. More broadly, any state-changing action guarded only by the session cookie — change email, change password, transfer funds, add an admin — can be triggered from a page the victim merely visits. No overclaim: CSRF is about *actions the victim did not intend*, not data theft — the Same-Origin Policy blinds the attacker to the response — and it runs in the victim's browser, not on the server.

## 7. Why the fix works

Point the attacker page at the fixed target: open `http://127.0.0.2:8080/attack-fixed` (its form posts to `127.0.0.1:8123/email`) with the victim logged in at `127.0.0.1:8123`. The forged request returns:

```
Forbidden
```

An HTTP `403`, and the account email is **unchanged** (`demo@example.com`). Look closely at that `403`: it is Flask's default "Forbidden" page, **not** the `"Not logged in"` message from Section 4's cookieless `curl`. That distinction is the point — the forged request **passed** the session check (the cookie *was* attached, `SameSite=None` as always), and was then rejected by the *token* check. On the wire the forged request still carries `Cookie: session_fixed=...` and a body of just `email=attacker@evil.example` — the cookie rode along exactly as before; what is missing is the token.

The fixed target adds a per-session **anti-CSRF token** (a "synchronizer token"): a secret generated server-side, stored in the session, and embedded as a hidden field in the target's own email form. `POST /email` now requires it in the body and compares it to the session's copy. The legitimate flow still works — the victim's own form carries the token, so submitting it sends `csrf_token=...&email=...` and the change succeeds (verified: the fixed target's real form updates the email to a new value with no `403`). The forged request fails because the attacker **cannot read the token**: it lives in the target's HTML form, and the Same-Origin Policy forbids the attacker's page from reading a cross-origin response. The cookie the browser sends for free is not enough; the token has to be *supplied*, and only a page from the target's own origin has it.

Note what did **not** change: the cookie config is `SameSite=None; Secure` on both sides. The token is the *only* security difference — which proves the fix is the token, not re-tightening `SameSite`. See [`DIFF.md`](./DIFF.md) for the change and for the three legitimate CSRF defenses (the token, `SameSite`, and an `Origin`/`Referer` check) and how they layer.
