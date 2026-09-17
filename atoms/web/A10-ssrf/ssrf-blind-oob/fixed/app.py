import os
from urllib.parse import urlparse
import requests
from flask import Flask, request, render_template

app = Flask(__name__)

# Deny-by-default allowlist of vetted webhook destinations, matched on the PARSED host (not a
# substring of the raw URL). In this air-gapped lab the host is not actually reachable (no real
# egress), so legitimate use is conceptual; what the lab demonstrates is that a non-vetted
# destination (the oob-listener, or any internal/external host) is never fetched.
ALLOWED_HOSTS = {"hooks.example.com"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ping", methods=["POST"])
def ping():
    url = request.form.get("url", "")
    # FIXED: gate the outbound request on the allowlist BEFORE fetching. A destination that is
    # not explicitly permitted is never requested, so the server cannot be coerced into reaching
    # arbitrary destinations (internal or external). Same SSRF defense family as ssrf-basic (04);
    # the host is the load-bearing check. The response below is left byte-identical to the
    # vulnerable version on purpose: the fix gates the REQUEST, never the response.
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:
        try:
            requests.get(url, timeout=5)
        except Exception:
            pass
    return "Test ping sent."  # generic: says nothing about whether or what was fetched


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
