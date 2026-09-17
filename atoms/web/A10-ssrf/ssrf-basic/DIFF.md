# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`:

```diff
 import os
+from urllib.parse import urlparse
 import requests
-from flask import Flask, request, render_template
+from flask import Flask, request, render_template, abort

 app = Flask(__name__)

+ALLOWED_HOSTS = {"api.github.com", "wikipedia.org"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/fetch")
 def fetch():
     url = request.args.get("url", "")
     if not url:
         return render_template("index.html")
-    # VULNERABLE: server-side request to attacker-controlled URL, no allowlist.
+    parsed = urlparse(url)
+    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
+        abort(403)
     try:
         response = requests.get(url, timeout=5)
         content, status = response.text, response.status_code
     except requests.RequestException as exc:
         content, status = f"Request error: {exc}", None
     return render_template("preview.html", url=url, content=content, status=status)
```

The templates are identical in both versions — the bug lives entirely in the absence of validation around `requests.get`.

## What changed

Three edits, all in `app.py`:

- A new import: `urllib.parse.urlparse`, plus `abort` from `flask`.
- A constant `ALLOWED_HOSTS` with the only two hostnames the feature is willing to fetch.
- A two-line gate inserted before the `requests.get` call: parse the URL once, and reject anything whose scheme isn't `https` or whose hostname isn't in the allowlist. Rejected requests return `403 Forbidden`.

## Why this fixes the bug

The fix is a **positive list**: only `https://api.github.com/...` and `https://wikipedia.org/...` are allowed through. Anything else — `http://internal/`, `http://169.254.169.254/`, `file:///etc/passwd`, `gopher://...`, or just a different domain — fails the check and never reaches `requests.get`. The decision is "is this URL on the small list of things we accept?", and the answer is yes only when the URL was on the list to begin with.

The check happens **after** parsing with `urlparse`, not by string-matching the raw `url` argument. That matters: `https://api.github.com.evil.tld/` and `https://api.github.com@evil.tld/` and `https://EVIL.com/?x=api.github.com` would all pass a naive `if "api.github.com" in url` test but fail this one — `urlparse(...).hostname` returns the actual hostname the HTTP client will connect to (`api.github.com.evil.tld`, `evil.tld`, `evil.com`), which is what we compare against.

The check is also **content-type agnostic** — it runs on the request URL, not on the response. The `internal` service in this lab serves `text/plain` for legibility, but the fix would behave identically if `internal` started returning HTML, JSON, binary, or anything else: URLs are rejected before the fetch happens, and nothing about the response is ever inspected. Worth stating explicitly so a future change to the internal service's format is never confused with a regression in the fix.

## Why a blocklist is not the fix

A natural-looking alternative is to **block** known-bad inputs instead of allowing known-good ones — strings like `internal`, `localhost`, `127.0.0.1`, `169.254.169.254`, or RFC 1918 IP ranges. Don't. Blocklists for SSRF lose to bypasses repeatedly:

- DNS resolution at fetch time can return a private IP for a public-looking hostname (DNS rebinding, or simply an attacker-controlled domain whose A record points at `127.0.0.1`).
- IPv6 (`::1`, `[::ffff:127.0.0.1]`) and alternate IPv4 representations (`2130706433`, `017700000001`, `0x7f000001`) sneak past string filters that only know the dotted-decimal form.
- Redirects: the URL you check resolves to a public host, returns a `302` to `http://169.254.169.254/`, and your HTTP client follows. The check ran on the wrong URL.
- URL parsers and HTTP clients sometimes disagree on which substring is "the host" — userinfo, IPv6 brackets, trailing dots, percent-encoded characters in the authority all create gaps.

The takeaway is shape, not technique: **allowlists are finite and decide on intent; blocklists are infinite and decide on guesses.**

## Contrast with previous atoms

This is the second atom whose fix *adds* code rather than removing it (the first was `idor-numeric-id`). In `sqli-union-basic` and `xss-reflected`, the fix was deleting a single bad construct — the f-string SQL build, the `|safe` filter. In `idor-numeric-id` the fix was an explicit ownership check that should have been there. Here it's a different kind of "missing check": the IDOR check answers "does this caller own this object?", a property of *who is asking*; the SSRF check answers "is this URL on the small set of things we'll fetch?", a property of *what is being asked for*. Same family — bug as absence — but the question being missing is different. Knowing which kind of question is missing is most of finding bugs in this family during a code review.
