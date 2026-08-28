import os

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = "changeme"  # dummy dev-only key (CLAUDE.md §8.3)

# IDENTICAL session-cookie config to vulnerable/ (SameSite=None; Secure) -- only
# SESSION_COOKIE_NAME differs, so vulnerable (:8034) and fixed (:8134), both on
# victim.localhost, do not share a login, since cookies ignore the port. That name is
# plumbing, NOT a security change. The CORS policy in add_cors() below is the ONLY
# security difference between the two apps.
app.config.update(
    SESSION_COOKIE_NAME="session_fixed",
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# The single demo user's PRIVATE account data, in memory -- no datastore needed. All
# dummy (CLAUDE.md §8): the point is that it is data only the logged-in victim should read.
ACCOUNT = {"user": "demo", "email": "demo@example.com", "balance": "USD 42,000.00"}

# Exact-match allowlist of the origins this API actually trusts to read its responses
# cross-origin -- here, one legitimate partner site. It is NOT run in this lab; it stands
# in for a real cross-origin consumer of the API. The point is that the API DOES need
# some CORS (so the fix is not "delete CORS"), but it names SPECIFIC trusted origins --
# and the attacker's origin is not one of them.
ALLOWED_ORIGINS = {"http://partner.localhost:9000"}


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
    # FIXED: only echo the Origin if it is EXACTLY in the allowlist. An untrusted origin
    # (the attacker) gets NO CORS header at all, so the browser blocks the cross-origin
    # read. Exact match is the point -- NOT origin.endswith("partner.localhost")/substring
    # (bypassable with evil-partner.localhost or partner.localhost.evil.com), NOT dropping
    # credentials while still reflecting (public data would still leak to any origin), and
    # NOT the literal * (which the browser refuses together with credentials anyway). The
    # trusted partner still works; the attacker's origin is not in the set, so it cannot
    # read the response.
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
