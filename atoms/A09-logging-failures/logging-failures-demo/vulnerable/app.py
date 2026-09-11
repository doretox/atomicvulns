import os
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login {email, password}. Then run a burst of failed logins and compare "
                "`docker compose logs vulnerable` with `docker compose logs fixed`. Work from "
                "Burp Repeater / Intruder.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Parameterized query + werkzeug hash check: the login logic is CORRECT and IDENTICAL on
    # both sides. No SQL injection, no bypass. Wrong password -> 401, exactly as it should.
    row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return jsonify({"authenticated": True})
    # VULNERABLE: the authentication FAILURE path records NOTHING security-relevant. A wrong
    # password IS a security event -- someone failed to authenticate as `email` from
    # `request.remote_addr` -- but the app emits no security log line. All that survives is
    # Werkzeug's generic HTTP access line ("POST /login" 401), which carries no account (the email
    # is in the body, not the URL), does not classify the 401 as an authentication failure, and
    # does not aggregate: a 20-request brute-force looks exactly like 20 users mistyping. The
    # attack leaves no security trail -- it is invisible AS AN ATTACK: nothing is logged, so
    # nothing can alert, and a responder or forensic analyst later has nothing to reconstruct.
    # Fix: emit a structured security event on this path, and WARN on a burst. See fixed/, DIFF.md.
    return jsonify({"authenticated": False}), 401


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        """
    )
    # Seed dummy lab users, passwords stored with a DECENT salted hash (werkzeug's default KDF) --
    # NOT to study password storage (that is crypto-weak-hash), just so the ONLY difference between
    # the two sides is the security logging. The brute-force targets victim@lab; its real password
    # is NOT in the attacker's wordlist, so the burst never succeeds. Dummy data (CLAUDE.md §8).
    seed = [("victim@lab", "victim-lab-pw"), ("user@lab", "user-lab-pw")]
    for email, pw in seed:
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                     (email, generate_password_hash(pw)))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    # threaded=False, kept IDENTICAL on both sides so the only difference is the logging, not the
    # server model. (On the fixed side the failure counter is global mutable state; serving one
    # request at a time keeps it deterministic under a burst. Flask defaults to threaded=True, so
    # this is set explicitly.)
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, threaded=False)
