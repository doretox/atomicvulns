import os
from urllib.parse import urlparse
import requests
from flask import Flask, request, render_template, abort

app = Flask(__name__)

# Deny-by-default allowlist of vetted destinations, matched on the PARSED host (not a substring
# of the raw URL). 169.254.169.254 (and anything not explicitly vetted) is never requested, so
# the metadata endpoint is unreachable through this feature.
ALLOWED_HOSTS = {"api.github.com"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/fetch", methods=["POST"])
def fetch():
    url = request.form.get("url", "")
    # FIXED: validate the destination against a deny-by-default allowlist BEFORE fetching.
    # Same SSRF defense family as ssrf-basic (04) and ssrf-blind-oob (16); the host is the
    # load-bearing check. http is allowed as a scheme on purpose -- so the refusal is
    # attributable to the HOST allowlist alone, not to a scheme filter (the metadata endpoint
    # is http, and "we blocked http" would be the wrong lesson).
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        abort(403)  # in-band visible refusal, like ssrf-basic (04) -- this atom is NOT blind
    try:
        r = requests.get(url, timeout=5)
        body, status = r.text, r.status_code
    except requests.RequestException as exc:
        body, status = f"Request error: {exc}", None
    return render_template("result.html", url=url, body=body, status=status)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
