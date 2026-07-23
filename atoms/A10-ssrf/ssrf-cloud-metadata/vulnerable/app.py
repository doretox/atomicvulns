import os
import requests
from flask import Flask, request, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/fetch", methods=["POST"])
def fetch():
    url = request.form.get("url", "")
    # VULNERABLE: fetch an attacker-controlled URL and return the response body verbatim.
    # No destination validation: the server reaches ANY host its network sees -- including the
    # cloud metadata endpoint (169.254.169.254), whose IAM credentials come straight back in
    # the response. SSRF weaponized for credential theft.
    try:
        r = requests.get(url, timeout=5)
        body, status = r.text, r.status_code
    except requests.RequestException as exc:
        body, status = f"Request error: {exc}", None
    return render_template("result.html", url=url, body=body, status=status)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
