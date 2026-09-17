import os
import base64
import json
from flask import Flask, request, render_template, make_response

app = Flask(__name__)
DEFAULT_PREFS = {"theme": "light"}


@app.route("/")
def index():
    cookie = request.cookies.get("prefs")
    if cookie is None:
        # First visit: serialize the default prefs (JSON + base64) and set the cookie.
        raw = base64.b64encode(json.dumps(DEFAULT_PREFS).encode()).decode()
        resp = make_response(render_template("index.html", theme=DEFAULT_PREFS["theme"]))
        resp.set_cookie("prefs", raw)
        return resp
    # FIXED: prefs are (de)serialized as JSON, which carries DATA ONLY, never behavior. A malicious
    # cookie can at worst produce a weird dict; json.loads cannot execute code. Root fix: change the
    # FORMAT (data, not behavior) -- not "sign the cookie" (see DIFF for why signing is a patch).
    try:
        prefs = json.loads(base64.b64decode(cookie))  # JSON: data only; no code path on load
        theme = prefs["theme"]
    except Exception:
        theme = DEFAULT_PREFS["theme"]
    return render_template("index.html", theme=theme)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
