import os

from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# --- In-memory account for the logged-in user (no database) ---
# The demo account IS "you". It starts as a normal user; only the server should
# ever be able to promote it. name/email are the fields a profile form edits.
account = {"name": "Demo User", "email": "demo@example.com", "role": "user"}


@app.route("/profile", methods=["POST"])
def update_profile():
    data = request.get_json(silent=True) or {}
    # VULNERABLE: copy EVERY field from the client's JSON straight into the account.
    # This works for the legitimate fields (name, email), but it also copies any
    # extra field the client adds -- including "role", which the profile form never
    # offered. The CLIENT, not the server, decides which attributes get set.
    account.update(data)
    return jsonify(account)


@app.route("/profile")
def get_profile():
    return jsonify(account)   # shows name, email, role -- proves what the update changed


@app.route("/admin")
def admin():
    # The escalation made concrete: this admin-only view answers only when the
    # account is an admin; a normal user gets 403.
    if account["role"] != "admin":
        abort(403)
    return jsonify({"message": "Admin area", "note": "admin-only content"})


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
