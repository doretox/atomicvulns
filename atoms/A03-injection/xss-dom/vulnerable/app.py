import os

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    # Serves a static page. The search is done entirely client-side (see
    # templates/index.html): the server never receives the search term, so
    # nothing here is user-controlled and there is no server-side sink.
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
