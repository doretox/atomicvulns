# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is how the login destination (`next`) is chosen before the redirect (comments abbreviated):

```diff
 import os
+from urllib.parse import urlparse
 from flask import Flask, request, redirect, render_template

 app = Flask(__name__)


+def safe_next(target, fallback="/dashboard"):
+    # Allowlist by STRUCTURE: accept only an internal path -- no scheme, no host ...
+    if not target:
+        return fallback
+    t = target.replace("\\", "/")          # browsers treat "\" like "/"; normalize before parsing
+    if not t.startswith("/") or t.startswith("//"):
+        return fallback                     # not an internal path, or protocol-relative "//host"
+    parsed = urlparse(t)
+    if parsed.scheme or parsed.netloc:
+        return fallback                     # any scheme or host present -> external -> refuse
+    return target
+
+
 @app.route("/", methods=["GET"])
 @app.route("/login", methods=["GET", "POST"])
 def login():
     if request.method == "POST":
         ...
         if request.form.get("username") == "demo" and request.form.get("password") == "demo":
-            next_url = request.form.get("next", "/dashboard")
-            # VULNERABLE: redirect to a user-controlled destination with NO check ...
+            # FIXED: the SERVER decides the destination via safe_next() -- internal path only ...
+            next_url = safe_next(request.form.get("next"))
             return redirect(next_url)
```

Everything else is byte-for-byte identical between the two versions: the login form handling, the credential check, the `return redirect(next_url)` line itself, `GET /dashboard`, `__main__`, the `Dockerfile`, `requirements.txt`, and both templates (`login.html`, `dashboard.html`). The bug — and the fix — live entirely in how `next_url` is computed.

## What changed

The vulnerable version assigns `next_url = request.form.get("next", "/dashboard")` — the raw, client-supplied value — and hands it straight to `redirect()`. The fixed version routes it through `safe_next()` first: `next_url = safe_next(request.form.get("next"))`. That is a *logic-different* fix — a new server-side validation step, plus the `urllib.parse` import it uses. The `redirect(next_url)` call is unchanged; what changed is that `next_url` is now the **server's** decision, not the client's.

## Why this fixes the bug

`safe_next()` is an allowlist of *structure*. It accepts a destination only if it is a plain internal path:

- normalize backslashes to `/` first, because browsers treat `\` like `/` (so `/\evil.example` would behave like `//evil.example`);
- require a single leading `/` and reject a leading `//` (a protocol-relative `//host` is another site);
- parse it and reject anything with a `scheme` or a `netloc` (host) — an absolute URL like `http://evil.example` or `https://demo@evil.example` has both.

Anything that is not a clean internal path falls back to `/dashboard`. So `next=/dashboard` and `next=/settings` pass through unchanged, while `http://evil.example`, `//evil.example`, `/\evil.example`, and `https://demo@evil.example` all collapse to `/dashboard`. The redirect can now only land on one of our own pages.

## The cause is trusting the destination, not the redirect itself

Redirecting after login is a normal, wanted feature — that is not the bug. The bug is trusting a *user-controlled* value as the destination. Proof of isolation: send `next=/dashboard` to both apps and both return `Location: /dashboard`; the legitimate feature is identical. Only an *external* `next` diverges — the vulnerable app emits it verbatim, the fixed app refuses it. Nothing about "using `redirect()`" is wrong; the fix is deciding the destination on the server.

## Allowlist of structure, not a blocklist of strings

The tempting quick fix is to *inspect the string* — "reject `next` if it starts with `http://`" or "allow it only if it starts with `https://our-site.com`". That is a blocklist, and it loses. A short tour of what slips past it:

- **`//evil.example`** — protocol-relative, no `http://` to match; the browser still resolves it to `https://evil.example`.
- **`https://our-site.com.evil.example`** — an allowlist prefix check on `https://our-site.com` matches, but the real host is `evil.example` (our name is just a subdomain label of theirs).
- **`https://our-site.com@evil.example`** — everything before `@` is *userinfo*, not the host; the check matches `https://our-site.com`, the browser goes to `evil.example`.
- **`/\evil.example`** and other backslash tricks — browsers fold `\` into `/`, so this behaves like `//evil.example`, but a naive string check (and even some URL parsers) treat `\` literally and miss it.
- **percent-encoding** (`%2f%2fevil.example`, …) — more spellings of the same thing for a substring filter to overlook.

Against an attacker inventing spellings, string-matching is an endless game of catch-up. The durable fix is structural: instead of asking "does this string look dangerous?", ask "is this destination one of *our own paths* — no scheme, no host?". That is what `safe_next()` does (and why it normalizes `\` before parsing, then relies on `urlparse` rather than substring checks). The blocklist is named here to show why it fails; it is **not** applied.

## Why an internal path is enough here

This atom restricts `next` to internal paths because a login "return you to where you were" has no legitimate reason to point at another domain — so path-only covers 100% of the real use and closes the attack. That is not universal. If an app genuinely had to redirect to *known external* destinations — cross-domain SSO, a payment gateway, an OAuth callback — the equivalent fix would be an allowlist of **hosts**: a closed list of permitted external destinations, matched by exact host equality (not prefix, not substring). Same principle — the server decides from a fixed set — a different allowlist. That host-allowlist is mentioned for that case; this app does not need it and does not use it.

## Impact: low alone, dangerous as a chain link

By itself an open redirect discloses nothing, runs nothing, and changes nothing on the target — it only relocates the browser, so in isolation it rates low. Its real value is as a *link in a chain*:

- **Phishing credibility.** The lure link begins on the trusted domain; the victim vets that domain and only afterward is bounced to the attacker's look-alike. The trusted origin is what sells the attack.
- **Token theft in OAuth / SSO.** Where a `redirect_uri` or a post-login return is under-validated, an open redirect can steer an authorization code or token to the attacker's destination.

Contrast this with `csrf-basic`, the other A01 atom set in a login/session context: CSRF makes the target *act* on the victim's behalf — a state-changing request the target executes because the browser attaches the victim's session cookie automatically. An open redirect does the opposite: it makes the target *send the victim away*, performs no action on the target, and needs no cookie at all. One abuses the target's trust in the victim's cookie; the other abuses the victim's trust in the target's domain. This atom proves the redirect off-site; the chained escalations above are the class's reach — described, not built.
