import os
from urllib.parse import urlparse
from flask import Flask, request, redirect, render_template

app = Flask(__name__)


def safe_next(target, fallback="/dashboard"):
    # Allowlist by STRUCTURE: the SERVER decides where a redirect may go. A legitimate
    # `next` in a login flow is always an in-site path; there is no reason to send the
    # user to another host. Accept only an internal path -- no scheme, no host -- and
    # refuse anything else, falling back to a safe internal default.
    if not target:
        return fallback
    t = target.replace("\\", "/")          # browsers treat "\" like "/"; normalize before parsing
    if not t.startswith("/") or t.startswith("//"):
        return fallback                     # not an internal path, or protocol-relative "//host"
    parsed = urlparse(t)
    if parsed.scheme or parsed.netloc:
        return fallback                     # any scheme or host present -> external -> refuse
    return target


@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Demo auth: the seeded user logs in with demo/demo. Auth is not the point -- it
        # just establishes a "successful login" so the redirect fires. No session is kept:
        # an open redirect does not depend on any cookie.
        if request.form.get("username") == "demo" and request.form.get("password") == "demo":
            # FIXED: the SERVER decides the destination. safe_next() accepts only an internal
            # path; anything with a host (http://, //host, a "\" trick, or a userinfo "@") is
            # refused and falls back to a safe internal default -- so `next` can only pick
            # AMONG our own paths.
            next_url = safe_next(request.form.get("next"))
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
