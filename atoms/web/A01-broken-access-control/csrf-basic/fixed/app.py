import os
import secrets
from flask import Flask, render_template, request, redirect, session, abort

app = Flask(__name__)
app.secret_key = "changeme"  # dummy dev-only key (CLAUDE.md §8.3)

# IDENTICAL session-cookie security config to vulnerable/ (SameSite=None; Secure)
# -- only SESSION_COOKIE_NAME differs (plumbing, so the two targets on 127.0.0.1
# don't share a login; see vulnerable/app.py). The anti-CSRF token below is the
# ONLY security difference between the two apps.
app.config.update(
    SESSION_COOKIE_NAME="session_fixed",
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# The single demo user's account state, in memory -- CSRF needs no datastore.
ACCOUNT = {"email": "demo@example.com"}


def csrf_token():
    # One unguessable secret per session (the "synchronizer token"), stored
    # server-side in the session and handed out only in this server's own forms.
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.route("/login", methods=["POST"])
def login():
    # Trivial fake login -- the credential is not the object of study.
    if request.form.get("username") == "demo" and request.form.get("password") == "demo":
        session["user"] = "demo"
    return redirect("/")


@app.route("/")
def index():
    if "user" not in session:
        return render_template("login.html")
    # Embed the per-session token as a hidden field in THIS server's own form.
    return render_template("account.html", email=ACCOUNT["email"], csrf_token=csrf_token())


@app.route("/email", methods=["POST"])
def change_email():
    if "user" not in session:
        return "Not logged in", 403
    # FIXED: verify INTENT with the anti-CSRF token. It was placed in this server's
    # form and must come back in the request BODY. An attacker on another origin
    # cannot READ it (the Same-Origin Policy forbids reading our response), so cannot
    # supply it -- even though the browser still attaches the session cookie to the
    # forged POST. The cookie riding along is not enough: intent must be proven.
    token = session.get("csrf_token")
    if not token or request.form.get("csrf_token") != token:
        abort(403)
    ACCOUNT["email"] = request.form.get("email", "")
    return redirect("/")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
