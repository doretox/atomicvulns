# DIFF — vulnerable vs. fixed

The fix is one thing: a per-session **anti-CSRF token** (a "synchronizer token"), added by hand — no framework, no `Flask-WTF`. The server generates a secret per session, embeds it as a hidden field in its own email form, and requires it back in the `POST /email` body. Everything else is unchanged; in particular the session-cookie security config is **identical** on both sides (`SameSite=None; Secure`), so the token is the *only* security difference between the two apps.

## The change — `app.py`

```diff
 import os
+import secrets
-from flask import Flask, render_template, request, redirect, session
+from flask import Flask, render_template, request, redirect, session, abort

 app.config.update(
-    SESSION_COOKIE_NAME="session_vuln",
+    SESSION_COOKIE_NAME="session_fixed",
     SESSION_COOKIE_SAMESITE="None",
     SESSION_COOKIE_SECURE=True,
 )

+def csrf_token():
+    # One unguessable secret per session, stored server-side in the session.
+    if "csrf_token" not in session:
+        session["csrf_token"] = secrets.token_urlsafe(32)
+    return session["csrf_token"]

 @app.route("/")
 def index():
     if "user" not in session:
         return render_template("login.html")
-    return render_template("account.html", email=ACCOUNT["email"])
+    return render_template("account.html", email=ACCOUNT["email"], csrf_token=csrf_token())

 @app.route("/email", methods=["POST"])
 def change_email():
     if "user" not in session:
         return "Not logged in", 403
+    token = session.get("csrf_token")
+    if not token or request.form.get("csrf_token") != token:
+        abort(403)
     ACCOUNT["email"] = request.form.get("email", "")
     return redirect("/")
```

`SESSION_COOKIE_NAME` differs (`session_vuln` vs `session_fixed`) for a non-security reason: both targets live on `127.0.0.1`, and cookies ignore the port, so a single cookie name would be shared between ports 8023 and 8123. Distinct names keep the two logins separate. The two security attributes — `SESSION_COOKIE_SAMESITE="None"` and `SESSION_COOKIE_SECURE=True` — are byte-identical on both sides.

## The change — `templates/account.html`

```diff
 <form method="post" action="/email">
+  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
   <label>New email: <input type="email" name="email" autofocus></label>
   <button type="submit">Update email</button>
 </form>
```

The server's own form now carries the token. `login.html`, the rest of `account.html`, the `Dockerfile`, and `requirements.txt` are byte-for-byte identical between the two apps.

## Why this fixes the bug

The vulnerable `POST /email` asked only *"is there a valid session cookie?"* — and the browser attaches that cookie to any request to the site, including one a hostile page triggers. The fixed `POST /email` also asks *"does the request carry the session's secret token?"*. The legitimate form has it (the server put it there); the forged request from another site does not, because **the attacker cannot read the token to include it**. The Same-Origin Policy lets the attacker's page *send* a request to the target but forbids it from *reading* the target's response — so it can never see the hidden field, and can never fill it in. `secrets.token_urlsafe(32)` makes the token unguessable, so it cannot be brute-forced either.

## The token goes in the request, not (only) the cookie

This is the crux, and it is worth stating precisely. The forged request **already carries the session cookie** — the browser attaches it automatically because `SameSite=None`. So "does it have the session cookie?" cannot be the test that stops CSRF: the answer is *yes* for the forged request too. What separates a real request from a forged one is a value that must be **actively supplied in the request body** — something the attacker would have to *read* to include, and the Same-Origin Policy stops them from reading it.

There is a subtlety in *where* the reference token lives. In this implementation it is stored in the session, which in Flask means it rides inside the signed session cookie — so the token, too, travels on the forged request. That is fine, because the check does not compare the cookie to itself: it compares the token in the **request body** (`request.form.get("csrf_token")`) against the session's copy. The forged request supplies the cookie (for free, via the browser) but *not* the body token — and the body token is the half the attacker cannot produce. The defense works by demanding something the attacker would have to **read**, not something the browser sends on its own.

## Three legitimate CSRF defenses, in three layers

Earlier atoms in this repo pair the real fix with a note naming a *wrong* or partial defense — a filter, a signature, server-side escaping — that looks right but misses. **CSRF is different: it has three genuinely legitimate defenses, at three different layers, and this note names all three honestly.**

- **Anti-CSRF token (synchronizer token) — application layer.** *This is what the fix applies.* It verifies **intent**: only a page served by the site itself carries the token, and the attacker cannot read it (SOP), so cannot forge a complete request. It works in any browser and does not depend on the transport or on cookie attributes.
- **`SameSite=Lax` / `Strict` — cookie layer.** This is the browser default this app turned *off*. It tells the browser not to attach the cookie on cross-site requests at all — real defense-in-depth, not a patch. But it depends on the browser honoring it, and some legitimate flows (cross-site embeds, some SSO) need `SameSite=None`, at which point this layer is gone. That is exactly the situation this atom models.
- **`Origin` / `Referer` check — server layer.** The server verifies the request came from its own origin. A valid, cheap alternative — but it depends on those headers being present and trustworthy (privacy tools and some proxies strip or alter them), so it is usually a complement rather than the sole control.

All three are legitimate, and in production you layer them (a token *and* `SameSite=Lax` *and*, often, an `Origin` check). This atom applies the **token** because it is the portable one and the one that verifies intent directly, and keeps `SameSite=None` on both sides precisely so the token — not the cookie attribute — is visibly what closes the hole.

## The cookie config is identical — the token is the only security delta

Look at what is *not* in this diff: any change to `SESSION_COOKIE_SAMESITE` or `SESSION_COOKIE_SECURE`. Both apps run `SameSite=None; Secure`. The fixed app does **not** close the hole by re-tightening `SameSite` to `Lax`; it closes it with the token, while leaving the loosened cookie in place. That isolates the lesson: with the cookie config held constant, the forged `POST` still arrives *with the session cookie* on both apps — it succeeds on the vulnerable one and returns `403` on the fixed one — so the token, and only the token, is what made the difference. The benign, legitimate flow is untouched: submitting the target's own form (which carries the token) updates the email on both apps.

## The impact is account takeover — and it is not XSS

The forged request changes the account's recovery email to one the attacker controls, which turns a "forgot password" into an account takeover. The class it is most often confused with is XSS — both involve "another site" — so the contrast is worth drawing sharply:

| | **XSS** (`xss-reflected` / `xss-stored` / `xss-dom`) | **CSRF** (this atom) |
|---|---|---|
| Where attacker code runs | **inside** the target's origin | on the **attacker's** origin (no code on the target) |
| Can it read the target's response? | **yes** — same origin, reads cookies, DOM, body | **no** — the SOP forbids reading cross-origin; the attack is **blind** |
| What it achieves | read **and** write in the target's context | **trigger** a state-changing action, fire-and-forget |
| OWASP category | A03 — Injection | A01 — Broken Access Control |

The rule of thumb: **XSS runs inside the target and reads everything; CSRF fires from outside and is blind.** CSRF cannot read data (the SOP blinds it) and does not run code on the server — it forces a state change the victim did not intend. That is why it is **A01 — Broken Access Control**: the server authorized a privileged action on identity alone (a valid session), without verifying the user meant it.
