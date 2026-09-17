import os
import requests
from flask import Flask, request, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/fetch")
def fetch():
    url = request.args.get("url", "")
    if not url:
        return render_template("index.html")
    # VULNERABLE: server-side request to attacker-controlled URL, no allowlist.
    try:
        response = requests.get(url, timeout=5)
        content, status = response.text, response.status_code
    except requests.RequestException as exc:
        content, status = f"Request error: {exc}", None
    return render_template("preview.html", url=url, content=content, status=status)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
