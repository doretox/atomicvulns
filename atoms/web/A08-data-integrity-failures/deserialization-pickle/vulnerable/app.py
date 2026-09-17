import os
import base64
import pickle
from flask import Flask, request, render_template, make_response

app = Flask(__name__)
DEFAULT_PREFS = {"theme": "light"}


@app.route("/")
def index():
    cookie = request.cookies.get("prefs")
    if cookie is None:
        # First visit: serialize the default prefs (pickle + base64) and set the cookie.
        raw = base64.b64encode(pickle.dumps(DEFAULT_PREFS)).decode()
        resp = make_response(render_template("index.html", theme=DEFAULT_PREFS["theme"]))
        resp.set_cookie("prefs", raw)
        return resp
    # VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to pickle.loads.
    # pickle reconstructs arbitrary objects, executing any __reduce__ the bytes carry -- a crafted
    # cookie -> code execution on the server. Untrusted data must never reach pickle.loads.
    try:
        prefs = pickle.loads(base64.b64decode(cookie))  # RCE: attacker bytes -> code on load
        theme = prefs["theme"]
    except Exception:
        theme = DEFAULT_PREFS["theme"]
    return render_template("index.html", theme=theme)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
