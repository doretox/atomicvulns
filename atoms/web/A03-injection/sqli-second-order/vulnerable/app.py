import os
import sqlite3
from flask import Flask, request, jsonify, session

app = Flask(__name__)
# Lab dummy: signs the session cookie only. Orthogonal to the vuln; identical
# on both sides. NOT the object of study.
app.secret_key = os.environ.get("SECRET_KEY", "changeme")
DB_PATH = os.environ.get("DB_PATH", "lab.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    # Banner only -- POST /change-password is where this atom's lesson lives (see WALKTHROUGH).
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /register, POST /login, then POST /change-password. "
                "Work from Burp Repeater.",
    })


@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")
    conn = db()
    # SAFE (parameterized): even a SQL payload in `username` is stored as a literal
    # VALUE here -- nothing executes. This is the "plant" step of a second-order bug.
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()
    return jsonify({"registered": True})


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")
    conn = db()
    # SAFE (parameterized): login is NOT the injectable surface in this atom.
    row = conn.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?", (username, password)
    ).fetchone()
    conn.close()
    if row:
        session["uid"] = row["id"]
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


@app.route("/change-password", methods=["POST"])
def change_password():
    uid = session.get("uid")
    if not uid:
        return jsonify({"error": "not authenticated"}), 401
    body = request.get_json(silent=True) or {}
    new_password = body.get("new_password", "")
    conn = db()
    # The logged-in user's username is READ BACK from the DB (parameterized read).
    uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
    # VULNERABLE: the username re-read from the DB is concatenated straight into the
    # UPDATE. It was STORED safely (parameterized) at registration, so it was never
    # treated as untrusted here -- but a value read back from the DB is untrusted
    # input again. Note `new_password` (fresh input) IS parameterized; only the
    # re-read value is spliced in -- so a payload username rewrites WHICH row this hits.
    query = f"UPDATE users SET password = ? WHERE username = '{uname}'"
    conn.execute(query, (new_password,))
    conn.commit()
    conn.close()
    return jsonify({"updated": True})


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        INSERT INTO users (username, password) VALUES
            ('admin', 'admin-lab-pw'),
            ('alice', 'alice-lab-pw'),
            ('bob',   'bob-lab-pw');
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
