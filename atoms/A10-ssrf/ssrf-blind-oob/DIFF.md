# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is a destination gate around the fetch in `POST /ping`:

```diff
 import os
+from urllib.parse import urlparse
 import requests
 from flask import Flask, request, render_template

 app = Flask(__name__)

+# Deny-by-default allowlist of vetted webhook destinations, matched on the PARSED host (not a
+# substring of the raw URL). In this air-gapped lab the host is not actually reachable (no real
+# egress), so legitimate use is conceptual; what the lab demonstrates is that a non-vetted
+# destination (the oob-listener, or any internal/external host) is never fetched.
+ALLOWED_HOSTS = {"hooks.example.com"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/ping", methods=["POST"])
 def ping():
     url = request.form.get("url", "")
-    # VULNERABLE: fire a server-side request to an attacker-controlled URL and reveal nothing
-    # about the result. The outbound request happens (this is full SSRF); the response below
-    # is generic: no fetched body, no fetched status, no error surfaced. The SSRF is real, it
-    # is merely BLIND, so it must be detected out-of-band (see the oob-listener service).
-    try:
-        requests.get(url, timeout=5)  # server-side request to the attacker-chosen destination
-    except Exception:
-        pass  # swallow everything: surfacing the error would leak an in-band oracle
+    # FIXED: gate the outbound request on the allowlist BEFORE fetching. A destination that is
+    # not explicitly permitted is never requested, so the server cannot be coerced into reaching
+    # arbitrary destinations (internal or external). Same SSRF defense family as ssrf-basic (04);
+    # the host is the load-bearing check. The response below is left byte-identical to the
+    # vulnerable version on purpose: the fix gates the REQUEST, never the response.
+    parsed = urlparse(url)
+    if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:
+        try:
+            requests.get(url, timeout=5)
+        except Exception:
+            pass
     return "Test ping sent."  # generic: says nothing about whether or what was fetched
```

Everything else — `GET /`, the shared imports, the footer, `requirements.txt`, the `Dockerfile`, and the template — is byte-for-byte identical between the two versions. Note especially the line that **did not change**: `return "Test ping sent."`. The response is the same in both apps.

## What changed

Three edits, all in `app.py`:

- A new import: `urllib.parse.urlparse`.
- A constant `ALLOWED_HOSTS` with the only hostnames the feature is willing to reach.
- A gate wrapping the fetch: parse the URL once, and only call `requests.get` if the scheme is `https` **and** the parsed host is on the allowlist. Anything else is simply never fetched.

This is a *logic-different* fix — added code, not a changed value — the same shape as the access-control and JWT atoms, and as `ssrf-basic` before it. What is **not** in the diff is the response: `return "Test ping sent."` is untouched, because the fix operates on the request, not on what the user is told.

## Why this fixes the bug

The class is: **the server issues a request to a destination the attacker controls.** The remediation validates that destination *before* making the request, against a deny-by-default allowlist. A URL that is not explicitly vetted never reaches `requests.get`, so the server cannot be coerced into reaching arbitrary hosts — internal or external. The check runs on `urlparse(url).hostname`, the host the HTTP client would actually connect to, not on a substring of the raw string.

The rest of this file is about the traps specific to *blind* SSRF, where the fix is easy to get subtly wrong.

## Leaving the response generic is not a defense

It is tempting to think the blindness itself protects you — the app already says nothing, so what is there to exploit? But the response is generic in the **vulnerable** app *and* in the **fixed** app, and one of them is exploitable. The identical, untouched `return "Test ping sent."` line in the diff makes this concrete: the response was never the control. Hiding the output removes your *in-band* confirmation; it does nothing to stop the server from making the request. The fix has to act on the **destination**, which is exactly what the response does not touch.

## Allowlist, not a blocklist of private ranges

A natural-looking alternative is to block "bad" destinations — private IP ranges, `localhost`, `169.254.169.254`, and so on. For blind SSRF specifically, that is not enough. A blocklist of private ranges stops you from reaching an **internal** target (it blocks the impact), but it does **not** stop an out-of-band callback to an **external** host — a Collaborator on the public internet is not in any private range. So detection still works, and the server can still be driven to reach attacker-chosen external destinations. An **allowlist** rejects everything that is not explicitly vetted — internal *and* external — so it cuts off both the detection and the impact. That is why the fix is a positive list.

## The lab wrinkle: our sink is internal

Be honest about a detail this lab cannot avoid. In the real world, the out-of-band sink (Collaborator, `interactsh`) is **external**, so a "block private ranges" filter would *not* block it and detection would still succeed — which is exactly why a blocklist is insufficient. In this air-gapped lab the sink (`oob-listener`) is **necessarily internal**, so the same allowlist that blocks internal targets also happens to block our sink. Do not over-learn from that coincidence: the fix does not "kill blind-SSRF detection" in general. Here it blocks the callback only because our sink is internal; against a real external Collaborator, only an allowlist — not a private-range blocklist — would stop the callback.

## `abort(403)` in `ssrf-basic` vs an identical response here

`ssrf-basic` rejects a disallowed URL with `abort(403)` — a visible refusal. That is fine there: the app is in-band, its response already carries information, so a distinct error changes nothing about the lesson. This atom deliberately does **not** do that. It gates the fetch and returns the **same** `Test ping sent.` whether the destination was allowed or not. If the fixed app answered differently for a blocked destination, you could confirm the block from the response — contradicting the whole point that blind SSRF is confirmed out-of-band. Same defense family (validate the destination), form adapted to blindness: the response stays constant, and the only thing that changes is whether the callback happens.

For the same reason, the vulnerable app swallows the fetch exception (`except Exception: pass`) instead of surfacing it the way `ssrf-basic` does. Surfacing "connection refused" vs "timeout" vs "ok" would be an *in-band oracle* that partially de-blinds the atom. (A coarse **timing** side-channel — a reachable host answers fast, an unresponsive one stalls until the 5-second timeout — is inherent to any blind SSRF and cannot be fully removed; it is not the channel this atom teaches. The out-of-band callback is.)

## The allowlist is correct, not a bypassable blocklist

The check decides on `urlparse(url).hostname`, so it resists the usual evasions — and this matters, because a *bypassable* filter would quietly turn this atom into an "SSRF filter bypass" lesson (a different, more advanced topic). Verified against the fixed app:

| Payload | Parsed host | Result |
|---|---|---|
| `https://hooks.example.com/proof-ssrf-16` | `hooks.example.com` | allowed (the vetted destination) |
| `http://oob-listener/proof-ssrf-16` | `oob-listener` | blocked (not vetted; also not `https`) |
| `http://2130706433/` | `2130706433` | blocked (decimal-IP form is not a vetted host) |
| `http://hooks.example.com.evil.test/` | `hooks.example.com.evil.test` | blocked (suffix trick: full host is not vetted) |
| `http://oob-listener:80/proof-ssrf-16` | `oob-listener` | blocked (port is stripped from the host) |
| `https://hooks.example.com@oob-listener/` | `oob-listener` | blocked (userinfo trick: real host is after the `@`) |

The last row is the important one: the string `hooks.example.com` appears in the URL, so a naive `if "hooks.example.com" in url` test would pass it — and let the request reach `oob-listener`. Parsing first and comparing `hostname` defeats it, because `urlparse` returns the host the client will actually connect to. The bug in this atom is the **absence** of destination validation; the fix, when present, has to be robust — otherwise it is not really a fix.

## Why the listener is embedded

The atom ships its own out-of-band sink (`oob-listener`) rather than telling you to point payloads at a real interaction server. That is the honest structural move of this atom. Detecting blind SSRF in the field depends on an **external** service you control — Burp Collaborator, `interactsh`, a DNS/HTTP catcher on the internet. This lab is isolated by design (bound to `127.0.0.1`, no dependency on the outside world), so its exploit cannot require reaching a third party. Embedding a self-hosted, air-gapped analog of that sink is what lets the attack be reproduced offline, by anyone, with nothing but `docker compose logs`. It is the same discipline you see when a library or environment already provides something the real world relies on: rather than fake it away, the atom models the honest local equivalent.
