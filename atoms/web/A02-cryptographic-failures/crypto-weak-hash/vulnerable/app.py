import os
import hashlib
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")


def store_hash(password):
    # VULNERABLE: MD5 is a fast, general-purpose hash, used here with NO salt. It is the
    # WRONG PRIMITIVE for passwords. A hash is one-way (you cannot decrypt it), but a fast,
    # unsalted hash is trivially RECOVERABLE once it leaks: the same password always yields
    # the same digest, so an attacker can pre-compute a hash->password table once (a rainbow
    # table) and reuse it against any unsalted hash. The login logic below is correct -- the
    # flaw is entirely this choice of primitive. Fix: a slow, salted password KDF (see fixed/).
    return hashlib.md5(password.encode()).hexdigest()


def verify(password, stored):
    # Re-hash the submitted password with the same primitive and compare. Correct verification
    # against the WRONG primitive.
    return hashlib.md5(password.encode()).hexdigest() == stored


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
    # Seed: admin's weak password is stored as an UNSALTED MD5 digest. Dummy data (CLAUDE.md §8).
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
