# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is the block that runs *after* the credential check in `POST /login`:

```diff
     if CREDENTIALS.get(user) != password:
         abort(401)  # trivial credential check — the password is not the object of study
-    # VULNERABLE: authenticate the CURRENT session, keeping the SAME session_id. The id that
-    # existed before login (possibly attacker-planted) now identifies an AUTHENTICATED session.
-    # No new id when the privilege level changes (anonymous -> authenticated) = session fixation.
+    # FIXED: authenticate, then REGENERATE the session id. Rebind the now-authenticated session
+    # onto a NEW id and discard the old one, so any id that existed before login (possibly
+    # attacker-planted) can never become authenticated. This regeneration is the whole fix.
     sess["authenticated"] = True
     sess["user"] = user
-    return redirect("/account")  # cookie unchanged — the pre-login sid is now authenticated
+    new_sid = secrets.token_urlsafe(32)
+    SESSIONS[new_sid] = sess          # rebind the (now-authenticated) session onto a NEW id
+    del SESSIONS[sid]                 # discard the old (possibly planted) id
+    resp = redirect("/account")
+    resp.set_cookie("session_id", new_sid, httponly=True, samesite="Lax")
+    return resp
```

Everything else — the imports, `SESSIONS`, `CREDENTIALS`, `current_session`, `GET /`, `GET /account`, the footer, and **both templates** — is byte-for-byte identical between the two versions.

## What changed

Note the two lines that *didn't* change: `sess["authenticated"] = True` and `sess["user"] = user`. Authenticating the session is the same in both versions. What the fix **adds** is everything around the id:

- `new_sid = secrets.token_urlsafe(32)` — mint a brand-new session id.
- `SESSIONS[new_sid] = sess` — rebind the now-authenticated session object onto that new id.
- `del SESSIONS[sid]` — discard the old id entirely, so it identifies nothing.
- `resp.set_cookie("session_id", new_sid, ...)` — hand the new id to the client.

The vulnerable version does none of this; it just returns, and the cookie the client already holds — the pre-login id — is now an authenticated session. This is a *logic-different* fix: not a changed value, but added code — the same shape as the access-control atoms, where the fix is the code that was missing.

## Why this fixes the bug

The class is: **an authenticated session is identified by something that existed before authentication.** The remediation is its exact negation: **issue a new session id at the moment the privilege level changes** (anonymous → authenticated), and drop the old one. Any id an attacker could have planted before login is discarded the instant the victim authenticates, so it never names an authenticated session. That's the whole fix — one regeneration, at one moment.

Notice what is *not* in the diff. The ids were already strong. The cookie already had `HttpOnly` and `SameSite`. The login check, the templates, the storage — all unchanged. None of that was the bug, and none of it needed to move.

## Fixation is not hijacking

The neighbouring bug this is most often confused with is session *hijacking*, and the difference is the whole point of the atom:

- **Hijacking** *steals* a session id that is **already authenticated** — after login, via sniffing, XSS reading the cookie, malware. The attacker takes something that exists.
- **Fixation** *supplies* a session id **before** authentication and lets the victim authenticate it. The attacker gives something and waits.

Direction (take vs give) and timing (after vs before). The attacker in a fixation attack never reads the victim's authenticated cookie — they held the id since before the victim logged in. That is why the fix is **regeneration**, which specifically kills fixation: even an attacker who holds the pre-login id loses it the moment the id rotates at login.

## Why a manual server-side session, not `flask.session`

The vulnerable app rolls its own session store (`SESSIONS` dict + opaque `session_id` cookie) instead of using Flask's built-in `session`. That is deliberate, and it's the honest part of the atom.

Flask's `session` is a **signed client-side cookie**: the session data is serialized, signed with `SECRET_KEY`, and stored in the cookie itself. There is no server-side id to fixate, and the cookie's value *changes* the moment you log in (it now encodes `authenticated: True, user: alice`, re-signed) — so it regenerates by nature. An attacker can't plant a value that becomes authenticated, because forging that value would require the `SECRET_KEY` (a different bug entirely). **A session-fixation atom built on `flask.session` would not be vulnerable.**

Session fixation lives in the other, more common shape: a **server-side session with an opaque id in the cookie** (`PHPSESSID`, `JSESSIONID`, and every framework that stores sessions server-side). Those must **rotate the id on login**, and forgetting to is the bug. This atom models that shape so the missing rotation is visible. It's the same honest move you see when a library already mitigates a class: the default tool resists the bug, so the bug survives in code that manages sessions by hand — which is exactly where it lives in the wild.

## Cookie flags don't fix this

A tempting "fix" is to harden the cookie: `HttpOnly`, `Secure`, `SameSite`. Resist it. Those flags defend against cookie **theft** (hijacking) — and the vulnerable app **already sets `HttpOnly` and `SameSite`**, yet it is fully exploitable. Fixation never reads the victim's cookie, so protecting the cookie's confidentiality touches nothing. (`Secure` is left off only because the lab runs over plain HTTP; in production you'd set it, but it is just as orthogonal to fixation.) The durable fix is regenerating the id, full stop — which is why the flags are identical in both versions and stay out of the diff.

## The session id is strong in both versions

`secrets.token_urlsafe(32)` mints the id in the vulnerable app *and* the fixed app — 256 bits of entropy, unguessable in either. This matters: if the id were weak, the atom would carry **two** bugs (a predictable id *and* non-regeneration), and a reader might "fix" the wrong one. The id here is strong; the only bug is that the vulnerable app lets a legitimately-issued id survive the anonymous → authenticated transition. Regeneration — not more entropy — is the fix.

## A note on migration

The fix rebinds the *same session object* onto a new id (`SESSIONS[new_sid] = sess; del SESSIONS[sid]`) rather than building a fresh one. Here there is no pre-login state worth keeping beyond the two flags we just set, so it makes little difference. In a real app you would carry over benign pre-login state (a cart, a locale, a CSRF token) onto the new id — but **never the id itself**. Regenerating the identifier while preserving the session is exactly what "session id regeneration" means.
