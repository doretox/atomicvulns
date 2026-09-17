import os
from flask import Flask, request, render_template, abort

app = Flask(__name__)

USERS = {"1": "alice", "2": "bob", "3": "carol"}
NOTES = [
    {"id": 1, "owner_id": 1, "title": "Banking", "content": "Bank PIN: 4231"},
    {"id": 2, "owner_id": 2, "title": "Meeting", "content": "Confidential meeting Friday 2pm"},
    {"id": 3, "owner_id": 3, "title": "Card",    "content": "Credit card ending in 8821"},
]


@app.route("/")
def index():
    user_id = request.headers.get("X-User-ID", "1")
    username = USERS.get(user_id, "unknown")
    return render_template("index.html", user_id=user_id, username=username)


@app.route("/notes/<int:note_id>")
def view_note(note_id):
    note = next((n for n in NOTES if n["id"] == note_id), None)
    if note is None:
        abort(404)
    # VULNERABLE: no ownership check — any caller can view any note by id.
    return render_template("note.html", note=note)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
