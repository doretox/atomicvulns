# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is a destination gate around the fetch in `POST /fetch` (comments abbreviated):

```diff
 import os
+from urllib.parse import urlparse
 import requests
-from flask import Flask, request, render_template
+from flask import Flask, request, render_template, abort

 app = Flask(__name__)

+# Deny-by-default allowlist of vetted destinations, matched on the PARSED host.
+ALLOWED_HOSTS = {"api.github.com"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/fetch", methods=["POST"])
 def fetch():
     url = request.form.get("url", "")
-    # VULNERABLE: fetch an attacker-controlled URL and return the response body verbatim...
+    # FIXED: validate the destination against a deny-by-default allowlist BEFORE fetching...
+    parsed = urlparse(url)
+    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
+        abort(403)
     try:
         r = requests.get(url, timeout=5)
         body, status = r.text, r.status_code
     except requests.RequestException as exc:
         body, status = f"Request error: {exc}", None
     return render_template("result.html", url=url, body=body, status=status)
```

The templates (`index.html`, `result.html`), the `Dockerfile`, and `requirements.txt` are byte-for-byte identical between the two versions. The bug lives entirely in the absence of destination validation around `requests.get`.

## What changed

Three edits, all in `app.py`:

- New imports: `urllib.parse.urlparse`, plus `abort` from `flask`.
- A constant `ALLOWED_HOSTS` with the only host the feature is willing to reach.
- A gate before `requests.get`: parse the URL once, and reject anything whose scheme isn't `http`/`https` **or** whose parsed host isn't on the allowlist. Rejected requests return `403 Forbidden`.

This is a *logic-different* fix — added code, not a changed value — the same shape as `ssrf-basic` and `ssrf-blind-oob` before it. What is **not** in the diff: the `try/except/return` that fetches and echoes the body is untouched. The fix acts on the **request** (whether the fetch happens), not on the response.

## Why this fixes the bug

The class is: the server issues a request to a destination the attacker controls, and here it hands back the body — so pointing it at `169.254.169.254` returns the instance's IAM credentials. The remediation validates that destination *before* the request, against a deny-by-default allowlist. `http://169.254.169.254/…` is not on the list, so it never reaches `requests.get`, and the metadata endpoint is unreachable through this feature. The check runs on `urlparse(url).hostname` — the host the HTTP client would actually connect to — not on a substring of the raw string.

## Allowlist, not a blocklist of the link-local range

The tempting alternative is to block the "bad" address: `169.254.169.254`, or the whole `169.254.0.0/16` link-local range. Don't. A blocklist loses to the bypasses SSRF blocklists always lose to:

- alternate IP encodings — decimal (`2852039166`), hex (`0xa9fea9fe`), octal, IPv6-mapped (`[::ffff:169.254.169.254]`) — all reach the same host but dodge a dotted-decimal string filter;
- redirects: a vetted-looking host answers `302 → http://169.254.169.254/…` and the client follows;
- DNS rebinding: an attacker-controlled name resolves to the link-local address at fetch time;
- userinfo/authority confusion: the real host hidden after an `@`.

An allowlist rejects everything that is not explicitly vetted — the link-local address included — without having to enumerate the evasions. This is the same shape the whole SSRF arc uses: `ssrf-basic` and `ssrf-blind-oob` both defend with a positive list, and `ssrf-blind-oob`'s DIFF spells out why a blocklist leaks. Allowlists win because they are finite and decide on intent; blocklists are infinite and decide on guesses.

## IMDSv2 — mentioned, not applied

There is a second, cloud-side defense this atom deliberately does **not** implement: **IMDSv2**. The real metadata service was hardened so that reading credentials requires a session token obtained with a `PUT` request first — a plain `GET` SSRF cannot obtain one — and it stamps responses with `hop-limit=1`, so a request *proxied through the app* (one hop further than the instance itself) is dropped. Either mechanism blunts this exact SSRF.

So why isn't it in the diff? Because IMDSv2 is a property of the **metadata service** — cloud/infrastructure configuration — not of `vulnerable/app.py`. This project's form is a diff *in the application code*, and the application-level fix for "the app fetches any URL" is to validate the destination, which is what `fixed/app.py` does. IMDSv2 is real, it is where this attack gets much harder in the field, and on a real instance you should enforce it (and set the instance's metadata `hop-limit` appropriately) — but it is defense on the **target's** side: named here, not applied in the diff. This is the same move `jwt-weak-secret` makes with its "secret management … mentionable, not applied" note — name the real-world control that lives outside the app's code, and keep the atom's diff to the one change it teaches.

## Visible refusal here vs the identical response in `ssrf-blind-oob`

`ssrf-blind-oob` returns a **byte-identical** response whether it fetched or not — on purpose, because it is *blind*: if the fixed app answered differently, you could confirm the block from the response, contradicting its whole "confirm it out-of-band" lesson. This atom does the opposite: `fixed` answers with a visible `403`. That is correct here because this atom is **in-band** — the response already carries information (it echoes the fetched body), so a distinct `403` changes nothing about the lesson and reads naturally, exactly like `ssrf-basic`'s `abort(403)`. Same defense family (validate the destination); the *form of the refusal* follows the channel: blind → identical, in-band → visible.

## The echo is escaped on purpose

`result.html` renders the fetched body inside a `<pre>{{ body }}</pre>` with Jinja autoescaping on (no `|safe`, no `Markup`, no `render_template_string`). Point the app at a body full of `<`/`>` and it comes back as `&lt;`/`&gt;` in the page source. This is deliberate: showing fetched content must not become a second vulnerability (reflected XSS / HTML injection). The one vulnerability here is the SSRF — the server fetching a destination it should not. How the body is displayed is not part of the bug, and the fix does not touch it.

## The allowlist is correct, not a bypassable blocklist

A *bypassable* filter would quietly turn this atom into an "SSRF filter bypass" lesson (a different, more advanced topic), so the fix decides on the parsed host and resists the usual evasions. Verified against the fixed app:

| Payload (body `url=`) | Parsed host | Result |
|---|---|---|
| `https://api.github.com/zen` | `api.github.com` | allowed (the vetted host) |
| `http://169.254.169.254/latest/meta-data/…` | `169.254.169.254` | 403 (not vetted — the real defense) |
| `http://2852039166/…` (decimal) | `2852039166` | 403 |
| `http://0xa9fea9fe/…` (hex) | `0xa9fea9fe` | 403 |
| `http://[::ffff:169.254.169.254]/…` | `::ffff:169.254.169.254` | 403 |
| `http://api.github.com@169.254.169.254/…` (userinfo) | `169.254.169.254` | 403 |

The last row is the one to hold onto: the string `api.github.com` is present, so `if "api.github.com" in url` would pass it and let the request reach the metadata endpoint. `urlparse(...).hostname` returns the real host — the part after the `@` — which is not on the list.

One honest limit, in the same "mentioned, not applied" spirit as IMDSv2: `requests.get` follows redirects by default, so a gate-only fix would still follow a `302` to `169.254.169.254` *if a vetted host issued it*. In this lab that is not reachable — the vetted host is benign and does not redirect to the metadata endpoint, and any non-vetted redirector is rejected at the gate because its own host isn't on the list. Production code that must be airtight would also pin `allow_redirects=False` (or re-validate every hop); this atom keeps the diff to the destination gate and notes the redirect hardening here rather than stacking it into the code.

## A note on the topology (why one network)

`ssrf-basic` and `ssrf-blind-oob` put their extra service on two Docker networks and reach it by DNS name, which keeps `vulnerable` and `fixed` on separate networks. This atom pins the mock at the fixed IP `169.254.169.254` — the whole point is that the payload is identical to a real target's — and a single address can only live in one subnet, so all three containers share one network here. That is a deliberate divergence, and it is inert to the lesson: the property that matters is preserved — the mock is reachable from **both** `vulnerable` and `fixed` at the network layer, so the fixed app's `403` is attributable to its **code** (the allowlist refusing), not to an unreachable network. The only thing lost is L3 separation between `vulnerable` and `fixed`, which carries no lesson: neither app ever initiates traffic to the other, and you only reach them through the host ports.
