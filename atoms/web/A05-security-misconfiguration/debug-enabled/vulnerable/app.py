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
    # VULNERABLE: debug=True turns on Werkzeug's INTERACTIVE DEBUGGER. Any unhandled exception
    # is rendered as an interactive web page that leaks source, local variables and file paths
    # (information disclosure) AND embeds a console that runs ARBITRARY PYTHON in this server
    # process (RCE). WERKZEUG_DEBUG_PIN=off removes the PIN "lock" on that console -- a
    # realistic "make debugging easier" misconfiguration. The route logic above is fine; the
    # flaw is entirely this development mode being reachable. Fix: debug=False -- and, in
    # production, serve behind a real WSGI server (Gunicorn/uWSGI), not this development
    # server. See ../fixed/app.py.
    os.environ["WERKZEUG_DEBUG_PIN"] = "off"
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)
