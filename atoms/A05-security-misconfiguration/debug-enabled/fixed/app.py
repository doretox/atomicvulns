import os

from flask import Flask, jsonify

app = Flask(__name__)
# Keep the benign JSON response byte-identical on both sides: debug mode would otherwise
# pretty-print JSON, and we want the ONLY observable difference to be how an unhandled
# exception is handled. Orthogonal to the vuln; identical in vulnerable/ and fixed/.
app.json.compact = True
ITEMS = ["alpha", "bravo", "charlie"]  # dummy data (CLAUDE.md §8) -- content is irrelevant


@app.route("/")
def index():
    return jsonify(
        {
            "warning": "⚠️ Intentionally vulnerable. Run locally only. "
            "Never expose to the internet or a shared network.",
            "hint": "GET /items/<idx> with a number; a malformed idx crashes the app. "
            "Work from Burp Repeater.",
        }
    )


@app.route("/items/<idx>")
def get_item(idx):
    # Ordinary route logic: convert the path segment to an int and look up an item.
    # A malformed idx ("abc") raises ValueError; an out-of-range int raises IndexError.
    # There is intentionally NO try/except here -- the unhandled exception is only the
    # TRIGGER, not the vuln. What matters is how the server renders an unhandled exception:
    # that is set by the debug flag in the __main__ block below, and it is the ONLY thing
    # that differs between the vulnerable and fixed apps.
    return jsonify({"item": ITEMS[int(idx)]})


if __name__ == "__main__":
    # FIXED: debug=False -- no interactive debugger, no console. The SAME malformed idx still
    # raises an exception, but it becomes a GENERIC 500 ("Internal Server Error") with no
    # traceback and no console, and there is no WERKZEUG_DEBUG_PIN=off. In production, this
    # development server should not be used at all: serve the app behind a real WSGI server
    # (Gunicorn/uWSGI), which has no debugger. The route logic is unchanged.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=False)
