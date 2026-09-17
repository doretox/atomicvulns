import os
import sqlite3
import bcrypt
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")


def store_hash(password):
    # FIXED: bcrypt is a purpose-built password KDF -- deliberately SLOW (a tunable cost/work
    # factor) and SALTED (bcrypt.gensalt() embeds a unique random salt in every hash). Because
    # each hash is salted, NO pre-computed rainbow table applies to it -- the attacker would
    # need a separate table per salt, which is infeasible. And the slowness raises the cost of
    # any live guessing (dictionary/brute) too. Salt AND slowness together, from one primitive.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify(password, stored):
    # bcrypt.checkpw re-derives using the salt embedded in `stored` and compares in constant time.
    return bcrypt.checkpw(password.encode(), stored.encode())


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login with {\"username\": \"...\", \"password\": \"...\"}. "
                "Work from Burp Repeater.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Parameterized query: the login logic is correct. No SQL injection here.
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row and verify(password, row["password_hash"]):
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        """
    )
    # Seed: admin's weak password is stored as a SALTED bcrypt hash. Dummy data (CLAUDE.md §8).
    # The hash is never exposed over HTTP -- the attack assumes it leaked in a DB dump.
    seed = [("admin", "adm1n"), ("alice", "alice-lab-pw"), ("bob", "bob-lab-pw")]
    for username, pw in seed:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, store_hash(pw)),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
