import os

from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# Shared MongoDB, seeded with a `users` collection (see mongo/mongo-init.js).
# Read-only here: every route only queries, never writes.
users = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017/")).labdb.users


@app.route("/")
def index():
    # Banner only -- the vulnerability lives in POST /login (see WALKTHROUGH.md).
    return jsonify(
        {
            "warning": "⚠️ Intentionally vulnerable. Run locally only. "
            "Never expose to the internet or a shared network.",
            "hint": 'POST /login with a JSON body: {"username": "...", '
            '"password": "..."}. Work from Burp Repeater.',
        }
    )


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    # VULNERABLE: username/password go straight into the query filter. A MongoDB
    # query is a DOCUMENT, not a string. If password arrives as an object like
    # {"$ne": null} instead of a string, it becomes a Mongo OPERATOR ("not equal"),
    # so the filter matches any user with a password and the login succeeds without
    # it. The input didn't inject syntax into a string -- it changed the value's type.
    user = users.find_one({"username": username, "password": password})
    if user:
        return jsonify({"authenticated": True, "user": user["username"]})
    return jsonify({"authenticated": False}), 401


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
