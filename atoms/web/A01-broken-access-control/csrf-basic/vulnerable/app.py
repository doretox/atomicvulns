import os
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "changeme"  # dummy dev-only key (CLAUDE.md §8.3)

# Session-cookie security config. SameSite=None deliberately relaxes the
# browser-level CSRF protection: the modern default, SameSite=Lax, would stop the
# cross-site POST on its own. Secure is required by SameSite=None and works over
# plain HTTP because 127.0.0.1 is a secure context (loopback). This block is
# IDENTICAL in fixed/ -- only SESSION_COOKIE_NAME differs, so the two targets on
# 127.0.0.1 (ports 8023 and 8123) don't share a login, since cookies ignore the
# port. The anti-CSRF token is the ONLY security difference between the two apps.
app.config.update(
    SESSION_COOKIE_NAME="session_vuln",
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# The single demo user's account state, in memory -- CSRF needs no datastore.
ACCOUNT = {"email": "demo@example.com"}


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
    return render_template("account.html", email=ACCOUNT["email"])


@app.route("/email", methods=["POST"])
def change_email():
    # VULNERABLE: the ONLY check is "is there a valid session cookie?" -- i.e. WHO
    # you are. It never verifies the authenticated user INTENDED this request: no
    # anti-CSRF token, no Origin/Referer check. The browser attaches the session
    # cookie automatically on every request to this site, so a POST forged from
    # another origin sails through as if the user had asked for it.
    if "user" not in session:
        return "Not logged in", 403
    ACCOUNT["email"] = request.form.get("email", "")
    return redirect("/")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
