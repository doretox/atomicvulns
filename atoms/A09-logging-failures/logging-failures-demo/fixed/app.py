import os
import logging
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")

# How many consecutive failures against one account raise a brute-force WARNING.
BRUTE_FORCE_THRESHOLD = 5

# In-memory per-account failure counter: email -> consecutive failures. Ephemeral lab state, like
# session-fixation's SESSIONS dict. Reset on a successful login. Dummy data (CLAUDE.md §8).
FAILURES = {}

# A dedicated SECURITY logger, separate from Werkzeug's generic HTTP access log. It writes
# structured, timestamped lines to the container's output (captured by `docker compose logs`),
# legible to a human and parseable by a machine (a SIEM). A dedicated logger + handler is used so
# this does NOT touch Werkzeug's logger -- the generic access log must keep appearing on BOTH
# sides, so the contrast is "security-absent vs security-present", not "no-log vs log".
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
security_log = logging.getLogger("security")
security_log.setLevel(logging.INFO)
security_log.addHandler(_handler)
security_log.propagate = False


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
        FAILURES.pop(email, None)  # a success clears the account's failure streak
        return jsonify({"authenticated": True})
    # FIXED: record the FACT of the authentication failure as a structured SECURITY event --
    # the event, the targeted account, the source IP, the timestamp -- and NEVER the SECRET (the
    # attempted password is not logged). This does NOT block the attempt: no lockout, no
    # rate-limit -- the login still returns 401 and the attacker may keep trying. A09 is about
    # VISIBILITY (detection), not prevention. After a burst against one account, WARN loudly.
    ip = request.remote_addr
    security_log.info("authentication failure account=%s ip=%s", email, ip)
    FAILURES[email] = FAILURES.get(email, 0) + 1
    if FAILURES[email] == BRUTE_FORCE_THRESHOLD:
        security_log.warning("possible brute-force against %s from %s (%d failures)",
                             email, ip, FAILURES[email])
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
