import os
import sqlite3
from flask import Flask, request, render_template, make_response, redirect, url_for

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")


@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    comments = conn.execute(
        "SELECT author, body, created_at FROM comments ORDER BY id DESC"
    ).fetchall()
    conn.close()
    resp = make_response(render_template("index.html", comments=comments))
    # Fake session cookie — gives the cookie-theft payload something concrete to steal.
    # Deliberately NOT HttpOnly so document.cookie can read it (the demo would be empty otherwise).
    resp.set_cookie("session", "fake-session-token-abc123")
    return resp


@app.route("/comment", methods=["POST"])
def comment():
    author = request.form.get("author", "")
    body = request.form.get("body", "")
    conn = sqlite3.connect(DB_PATH)
    # Parameterized insert: storing the payload is NOT the bug (no SQLi here).
    # The bug is rendering it unescaped on the way OUT (see templates/index.html).
    conn.execute("INSERT INTO comments (author, body) VALUES (?, ?)", (author, body))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (date('now'))
        );
        INSERT INTO comments (author, body, created_at) VALUES
            ('alice', 'Love this little guestbook. Clean and simple!',     '2026-06-21'),
            ('bob',   'Greetings from the sysadmin team. Nice work here.', '2026-06-23');
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
