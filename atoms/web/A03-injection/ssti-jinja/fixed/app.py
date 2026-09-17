import os
from flask import Flask, request, render_template, render_template_string

app = Flask(__name__)
# Dummy lab secret. Flask uses SECRET_KEY to SIGN session cookies; leaking it lets an attacker
# forge sessions. Obviously fake -- never a real secret (see CLAUDE.md security rules).
app.config["SECRET_KEY"] = "dev-secret-CHANGEME-not-a-real-secret"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/greet")
def greet():
    name = request.args.get("name", "world")
    # FIXED: the name is passed as DATA via the name= variable, never concatenated into the
    # template source. Jinja2 fills the {{ name }} placeholder with the escaped value and does
    # NOT re-evaluate it, so {{7*7}} comes back literal. Canonical SSTI fix: keep input OUT of
    # the template; pass it as data.
    return render_template_string(
        "<!doctype html><title>Greeting</title>"
        "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
        "<h1>Hello, {{ name }}!</h1>"                     # {{ name }} placeholder filled from data
        '<p><a href="/">&larr; Back</a></p>',
        name=name,                                        # name passed as DATA, never sewn in
    )


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
