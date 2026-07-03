import os
import subprocess
from flask import Flask, request, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ping")
def ping():
    host = request.args.get("host", "")
    # FIXED: argument list, no shell — host can never be parsed as shell syntax
    try:
        result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        # timeout: operational hygiene (orthogonal to the vuln/fix), same in both versions
        output = "command timed out after 10s"
    return render_template("result.html", host=host, output=output)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
