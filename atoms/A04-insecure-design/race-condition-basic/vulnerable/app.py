import os
import time

import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)


def db():
    # A fresh connection per request: N concurrent requests get N concurrent DB
    # sessions. Sharing one connection across threads would serialize them and
    # hide the race. Postgres' default max_connections (100) covers the burst.
    return psycopg2.connect(os.environ["DATABASE_URL"])


@app.route("/")
def index():
    return jsonify(
        {
            "warning": "⚠️ Intentionally vulnerable. Run locally only. "
            "Never expose to the internet or a shared network.",
            "hint": 'POST /withdraw with a JSON body: {"amount": 100}. Fire many '
            "at once from Burp's Turbo Intruder. POST /reset restores the balance.",
        }
    )


@app.route("/balance")
def balance():
    # Read-only: lets you watch the final number after a burst. Not the feature
    # under test, and not the vulnerability.
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM accounts WHERE id = 1")
        return jsonify({"balance": cur.fetchone()[0]})
    finally:
        conn.close()


@app.route("/withdraw", methods=["POST"])
def withdraw():
    amount = (request.get_json(silent=True) or {}).get("amount")
    conn = db()
    try:
        cur = conn.cursor()
        # VULNERABLE: check-then-act in THREE separate steps -- read, check, write.
        # Between the check (step 2) and the write (step 3) there is a time gap.
        # Under concurrency, N requests all read the full balance and all pass the
        # check BEFORE any of them writes, so all of them debit -- the balance runs
        # past zero. The guard EXISTS; it just is not atomic with the write. That
        # non-atomicity is the whole bug (see DIFF.md).
        cur.execute("SELECT balance FROM accounts WHERE id = 1")  # 1. read
        balance = cur.fetchone()[0]
        if balance < amount:  # 2. check, in Python, on a value that may be stale
            return jsonify({"error": "insufficient funds"}), 409
        # DIDACTIC CRUTCH: widens a window that already exists so the race
        # reproduces every time. The flaw is real without it (see WALKTHROUGH.md);
        # the fix closes the window regardless of timing, making the sleep moot.
        time.sleep(0.1)
        cur.execute(  # 3. write -- no guard in SQL; the check lived back in Python
            "UPDATE accounts SET balance = balance - %s WHERE id = 1", (amount,)
        )
        conn.commit()
        cur.execute("SELECT balance FROM accounts WHERE id = 1")
        return jsonify({"withdrew": amount, "balance": cur.fetchone()[0]})
    finally:
        conn.close()


@app.route("/reset", methods=["POST"])
def reset():
    # Lab convenience: restore the balance between attempts. A single atomic
    # UPDATE -- not part of the modeled feature, and not the vulnerability.
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE accounts SET balance = 100 WHERE id = 1")
        conn.commit()
        cur.execute("SELECT balance FROM accounts WHERE id = 1")
        return jsonify({"balance": cur.fetchone()[0]})
    finally:
        conn.close()


if __name__ == "__main__":
    # threaded=True: real concurrency is a prerequisite for the race to exist.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, threaded=True)
