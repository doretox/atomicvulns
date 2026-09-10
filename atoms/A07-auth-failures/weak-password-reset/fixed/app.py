import os
import time
import secrets
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")

# A reset token is a short-lived credential, not a standing one: expire it quickly.
TOKEN_TTL = 15 * 60  # seconds

# In-memory reset-token store: token -> {"email": ..., "expires_at": ...}. Ephemeral lab state,
# like session-fixation's SESSIONS dict -- a short-lived reset token does not need a database.
# Dummy data (CLAUDE.md §8).
RESET_TOKENS = {}


def make_reset_token():
    # FIXED: secrets.token_urlsafe(32) draws from a CSPRNG (os.urandom) -- roughly 256 bits of
    # UNPREDICTABLE entropy, with no seed the attacker can reproduce. Nothing in the response
    # (the Date header or anything else) narrows the search space. This is the SAME generator
    # session-fixation uses for its session ids. The token is unguessable by design. The
    # single-use and short expiry (see /reset) are the rest of a well-managed token -- defense in
    # depth -- but the DECISIVE change against a PREDICTED token is simply that it is unpredictable.
    return secrets.token_urlsafe(32)


def deliver_token(email, token):
    # Stand-in for out-of-band delivery (email). A real app emails a reset link and NEVER returns
    # the token over HTTP; this lab prints it to the server log so you can play the legitimate
    # user and read it from the "inbox". The ATTACK never reads this line -- it PREDICTS the token.
    print(f"[reset-email] to={email} token={token}", flush=True)


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /forgot {email} -> the reset token is 'emailed' (printed to the server "
                "log). POST /reset {token, new_password}. POST /login {email, password}. "
                "Work from Burp Repeater.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Parameterized query: the login logic is correct. No SQL injection here.
    row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


@app.route("/forgot", methods=["POST"])
def forgot():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row:
        token = make_reset_token()
        RESET_TOKENS[token] = {"email": email, "expires_at": time.time() + TOKEN_TTL}
        deliver_token(email, token)
    # Generic response either way: leaks neither the token nor whether the account exists.
    return jsonify({"message": "If that account exists, a reset link has been sent."})


@app.route("/reset", methods=["POST"])
def reset():
    body = request.get_json(silent=True) or {}
    token = body.get("token", "")
    new_password = body.get("new_password", "")
    # Single-use: pop the token so it cannot be replayed. Expiry: reject a token past its TTL.
    # These harden a token that is ALREADY unpredictable; against a PREDICTED token they never
    # even come into play -- an unknown token simply is not in the store and is rejected right here.
    entry = RESET_TOKENS.pop(token, None)
    if not entry or entry["expires_at"] < time.time():
        return jsonify({"reset": False}), 400
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                 (generate_password_hash(new_password), entry["email"]))
    conn.commit()
    conn.close()
    return jsonify({"reset": True})


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
    # Seed two users with dummy lab passwords, stored with a DECENT salted hash (werkzeug's
    # default KDF) -- NOT to study password storage, just so the ONLY flaw is the reset-token
    # generator. Dummy data (CLAUDE.md §8).
    seed = [("victim@lab", "victim-lab-pw"), ("attacker@lab", "attacker-lab-pw")]
    for email, pw in seed:
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                     (email, generate_password_hash(pw)))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    # Single-threaded (threaded=False). `random` is global process state, so in the vulnerable
    # app two overlapping /forgot requests could interleave seed()/choice() and desync the tokens;
    # serving one request at a time avoids that. Kept identical on both sides so the ONLY
    # difference between them is the token generator, not the server model. Flask's app.run
    # defaults to threaded=True, so this must be set explicitly.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, threaded=False)
