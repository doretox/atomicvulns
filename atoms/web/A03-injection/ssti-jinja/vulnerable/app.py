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
    # VULNERABLE: the name is concatenated INTO the template source with an f-string, so Jinja2
    # (Flask's template engine) treats it as template code, not data. An injected {{ ... }}
    # expression is EVALUATED: {{7*7}} -> 49; {{config}} -> Flask's config, including SECRET_KEY.
    return render_template_string(
        "<!doctype html><title>Greeting</title>"
        "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
        f"<h1>Hello, {name}!</h1>"                        # name is IN the template source -> SSTI
        '<p><a href="/">&larr; Back</a></p>'
    )


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
