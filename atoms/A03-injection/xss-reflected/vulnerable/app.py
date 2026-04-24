import os
from flask import Flask, request, render_template

app = Flask(__name__)

POSTS = [
    {"title": "Getting started with Flask", "snippet": "A beginner-friendly intro to the micro-framework."},
    {"title": "Why type hints saved my weekend", "snippet": "A short case study on refactoring with mypy."},
    {"title": "Reading HTTP with Burp Suite", "snippet": "Walkthrough of Proxy, Repeater, and the tab history."},
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = [p for p in POSTS if q.lower() in p["title"].lower()]
    return render_template("search.html", q=q, results=results)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
