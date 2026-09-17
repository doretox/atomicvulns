import os
import time
import random
import string
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")

# Token alphabet and length for the reset-token generator. The attacker's predictor must
# mirror these exactly (same alphabet, same length) to reproduce the token.
ALPHABET = string.ascii_letters + string.digits
TOKEN_LEN = 32

# In-memory reset-token store: token -> email. Ephemeral lab state, like session-fixation's
# SESSIONS dict -- a short-lived reset token does not need a database. Dummy data (CLAUDE.md §8).
RESET_TOKENS = {}


def make_reset_token():
    # VULNERABLE: the reset token is a TEMPORARY CREDENTIAL -- whoever presents it may set a new
    # password for the account. It is generated with Python's `random`, a PRNG (the Mersenne
    # Twister), SEEDED WITH THE CURRENT TIME. `random` is deterministic from its seed, and the
    # seed here is int(time.time()) -- the server's clock in whole seconds, a value the attacker
    # reads straight off this response's Date header. Re-seed with that integer, run the same
    # random.choice() calls, and you regenerate the SAME token, byte for byte. The secret is not
    # secret. NOTE two things this line depends on: nothing may consume the RNG between seed()
    # and the loop below (any random.* call in between would desync the sequence), and we re-seed
    # on EVERY request, so each token is independently reproducible. Fix: a CSPRNG. See fixed/.
    random.seed(int(time.time()))
    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))


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
        RESET_TOKENS[token] = email  # no single-use, no expiry: the flaw here is the GENERATOR
        deliver_token(email, token)
    # Generic response either way: leaks neither the token nor whether the account exists.
    return jsonify({"message": "If that account exists, a reset link has been sent."})


@app.route("/reset", methods=["POST"])
def reset():
    body = request.get_json(silent=True) or {}
    token = body.get("token", "")
    new_password = body.get("new_password", "")
    # Act on the OWNER of the token -- never on a user id taken from the body (that would be IDOR).
    # The whole flow is correct: whoever holds a valid token may set the password. The only flaw
    # is that the token is predictable.
    email = RESET_TOKENS.get(token)
    if not email:
        return jsonify({"reset": False}), 400
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                 (generate_password_hash(new_password), email))
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
