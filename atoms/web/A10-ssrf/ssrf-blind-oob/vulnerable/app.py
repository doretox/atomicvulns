import os
import requests
from flask import Flask, request, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ping", methods=["POST"])
def ping():
    url = request.form.get("url", "")
    # VULNERABLE: fire a server-side request to an attacker-controlled URL and reveal nothing
    # about the result. The outbound request happens (this is full SSRF); the response below
    # is generic: no fetched body, no fetched status, no error surfaced. The SSRF is real, it
    # is merely BLIND, so it must be detected out-of-band (see the oob-listener service).
    try:
        requests.get(url, timeout=5)  # server-side request to the attacker-chosen destination
    except Exception:
        pass  # swallow everything: surfacing the error would leak an in-band oracle
    return "Test ping sent."  # generic: says nothing about whether or what was fetched


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
