import os
from flask import Flask, request, redirect, render_template

app = Flask(__name__)


@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Demo auth: the seeded user logs in with demo/demo. Auth is not the point -- it
        # just establishes a "successful login" so the redirect fires. No session is kept:
        # an open redirect does not depend on any cookie.
        if request.form.get("username") == "demo" and request.form.get("password") == "demo":
            next_url = request.form.get("next", "/dashboard")
            # VULNERABLE: redirect to a user-controlled destination with NO check that it
            # points inside our own site. Whatever the client puts in `next` becomes the
            # Location header -- including an external site (http://evil.example, or the
            # protocol-relative //evil.example a naive http:// blocklist would miss).
            return redirect(next_url)
        return render_template("login.html", next=request.form.get("next", "/dashboard"), error=True)
    # GET: show the login form, prefilling `next` from the query string
    # ("return to where you were").
    return render_template("login.html", next=request.args.get("next", "/dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")   # minimal "logged in" landing (the internal `next` target)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
