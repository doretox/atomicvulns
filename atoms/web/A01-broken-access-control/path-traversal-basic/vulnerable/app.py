import os
from flask import Flask, request, render_template, abort

app = Flask(__name__)
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/view")
def view():
    filename = request.args.get("file", "")
    # VULNERABLE: user input joined onto the base dir and opened directly —
    # nothing confines the resolved path to BASE_DIR
    path = os.path.join(BASE_DIR, filename)
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
        # missing/unreadable file: operational hygiene, orthogonal to the
        # vuln and the fix, identical in both versions
        abort(404)
    return render_template("result.html", filename=filename, path=path, content=content)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
