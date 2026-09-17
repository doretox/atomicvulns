import os
import sqlite3
from flask import Flask, request, render_template

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/profile")
def profile():
    username = request.args.get("username", "")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT username, bio, joined_at FROM users WHERE username = ?", (username,)
    ).fetchall()
    conn.close()
    return render_template("profile.html", rows=rows, username=username)


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            bio TEXT NOT NULL,
            joined_at TEXT NOT NULL
        );
        CREATE TABLE secrets (
            user_id INTEGER NOT NULL,
            password_hash TEXT NOT NULL,
            api_key TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        INSERT INTO users (username, bio, joined_at) VALUES
            ('alice', 'Coffee lover and trail runner.', '2023-01-15'),
            ('bob',   'Full-time dad, part-time sysadmin.', '2023-04-02'),
            ('carol', 'Building things on the internet.', '2023-09-20');
        INSERT INTO secrets (user_id, password_hash, api_key) VALUES
            (1, '$2b$12$fakehashfakehashfakehashfakeha', 'sk_test_alice_fakekey_aaaa1111'),
            (2, '$2b$12$otherhashotherhashotherhashoth', 'sk_test_bob_fakekey_bbbb2222'),
            (3, '$2b$12$carolhashcarolhashcarolhashcar', 'sk_test_carol_fakekey_cccc3333');
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
