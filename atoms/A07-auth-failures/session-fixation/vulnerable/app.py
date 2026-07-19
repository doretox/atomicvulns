import os
import secrets
from flask import Flask, request, redirect, render_template, make_response, abort

app = Flask(__name__)

# In-memory server-side session store: {session_id: {"authenticated": bool, "user": str|None}}.
# Models the classic server-side session pattern (PHP's PHPSESSID, Java's JSESSIONID): an
# OPAQUE session id travels in the cookie, the session data stays on the server. We do NOT use
# flask.session on purpose — its signed client-side cookie has no server-side id to fix and
# regenerates by design, so session fixation cannot live there (see DIFF.md).
SESSIONS = {}

# DUMMY lab credential — trivial by design. The password is NOT the object of study; auth is
# simplified so the ONLY variable is what happens to the session id at login. Plaintext is
# intentional here (CLAUDE.md §8.3), not a second vulnerability.
CREDENTIALS = {"alice": "password123"}


def current_session():
    # Return (sid, session_dict) for the request's cookie, issuing a fresh ANONYMOUS session
    # if the cookie is missing or unknown to the server. The server only honors ids it issued
    # (it does not adopt arbitrary client-supplied ids), and the id is unguessable
    # (secrets.token_urlsafe) in BOTH versions — the bug is non-regeneration, not a weak id.
    sid = request.cookies.get("session_id")
    if not sid or sid not in SESSIONS:
        sid = secrets.token_urlsafe(32)
        SESSIONS[sid] = {"authenticated": False, "user": None}
    return sid, SESSIONS[sid]


@app.route("/")
def index():
    sid, sess = current_session()
    resp = make_response(render_template("index.html", sid=sid, sess=sess))
    resp.set_cookie("session_id", sid, httponly=True, samesite="Lax")
    return resp


@app.route("/login", methods=["POST"])
def login():
    sid, sess = current_session()
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    if CREDENTIALS.get(user) != password:
        abort(401)  # trivial credential check — the password is not the object of study
    # VULNERABLE: authenticate the CURRENT session, keeping the SAME session_id. The id that
    # existed before login (possibly attacker-planted) now identifies an AUTHENTICATED session.
    # No new id when the privilege level changes (anonymous -> authenticated) = session fixation.
    sess["authenticated"] = True
    sess["user"] = user
    return redirect("/account")  # cookie unchanged — the pre-login sid is now authenticated


@app.route("/account")
def account():
    sid = request.cookies.get("session_id")
    sess = SESSIONS.get(sid) if sid else None
    if not sess or not sess["authenticated"]:
        return redirect("/")  # not an authenticated session -> back to the login page
    return render_template("account.html", sid=sid, user=sess["user"])


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
