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
    # FIXED: resolve the real path, then confirm it stays inside BASE_DIR
    base = os.path.realpath(BASE_DIR)
    path = os.path.realpath(os.path.join(base, filename))
    if not path.startswith(base + os.sep):
        abort(404)
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
        # missing/unreadable file: operational hygiene, orthogonal to the
        # vuln and the fix, identical in both versions
        abort(404)
    return render_template("result.html", filename=filename, content=content)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
