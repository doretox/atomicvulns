import os

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = "changeme"  # dummy dev-only key (CLAUDE.md §8.3)

# Session-cookie config. SameSite=None so the browser attaches this cookie on the
# attacker's CREDENTIALED cross-origin fetch; Secure is required by SameSite=None and
# works over plain HTTP because *.localhost is a secure context (loopback origins are
# treated as trustworthy). This block is IDENTICAL in fixed/ -- only SESSION_COOKIE_NAME
# differs, so vulnerable (:8034) and fixed (:8134), both on api.lab.localhost, do not
# share a login, since cookies ignore the port. The CORS policy in add_cors() below is
# the ONLY security difference between the two apps.
app.config.update(
    SESSION_COOKIE_NAME="session_vuln",
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# The single demo user's PRIVATE account data, in memory -- no datastore needed. All
# dummy (CLAUDE.md §8): the point is that it is data only the logged-in victim should read.
ACCOUNT = {"user": "demo", "email": "demo@example.com", "balance": "USD 42,000.00"}


@app.route("/")
def index():
    # A minimal HTML portal. It is IDENTICAL in vulnerable/ and fixed/, so it is NOT part
    # of the security diff (the only delta is the CORS policy + the cookie name). It lets
    # you log in and read your own account from this page via in-page fetch, so the browser
    # never navigates onto the raw JSON API (whose JSON viewer's CSP would block those
    # fetches). /login and /account stay JSON. There is no injectable input here.
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    # Trivial fake login -- the credential is not the object of study. It establishes the
    # victim's session so GET /account has a cookie to require.
    if request.form.get("username") == "demo" and request.form.get("password") == "demo":
        session["user"] = "demo"
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401


@app.route("/account")
def account():
    # ORDINARY, CORRECT endpoint: it REQUIRES the session cookie and returns the logged-in
    # user's private data. The authentication works -- the flaw is NOT here. What lets an
    # attacker read this response from another origin is the CORS policy in add_cors().
    if "user" not in session:
        return jsonify({"error": "not logged in"}), 403
    return jsonify(ACCOUNT)


@app.after_request
def add_cors(resp):
    # VULNERABLE: reflect back WHATEVER Origin asked, and allow credentials. This tells
    # the browser "yes, THIS origin may READ the response WITH the victim's cookies" --
    # and because we echo whatever we are given, that is EVERY origin. Reflection (not the
    # literal *) is the authenticated-theft vector: the browser REFUSES
    # Access-Control-Allow-Origin: * together with Access-Control-Allow-Credentials: true,
    # so a reflected SPECIFIC origin is how the misconfiguration actually reaches
    # authenticated data. Written by hand so the cause is visible in the code; the fix is
    # an exact-match allowlist. See ../fixed/app.py.
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin  # reflection: the bug
        resp.headers["Access-Control-Allow-Credentials"] = "true"  # ...with the victim's cookies
    return resp


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
