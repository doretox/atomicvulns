import os
import secrets

from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# --- Simulated identity: an opaque, server-side session token ---
USERS = {"mallory", "alice"}   # mallory = attacker (you); alice = victim
TOKENS = {}                    # opaque token -> username (in-memory; NOT a JWT)


def _issue_token(user):
    token = secrets.token_urlsafe(24)   # opaque random value; a server-side session token
    TOKENS[token] = user
    return token


def _authenticate():
    # Authentication only: resolve the Bearer token to a user, or 401.
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    user = TOKENS.get(token)
    if user is None:
        abort(401)
    return user


# --- In-memory store (no database, like idor-numeric-id / idor-uuid-guessable) ---
# Order ids are a single GLOBAL sequence, so adjacent ids belong to different
# users: mallory owns 40 and 42, alice owns 41 -- the gap mallory sees in her list.
ORDERS = {
    40: {"id": 40, "owner": "mallory", "item": "Wireless mouse", "amount": "$29.90"},
    41: {"id": 41, "owner": "alice",   "item": "Standing desk",  "amount": "$589.00"},
    42: {"id": 42, "owner": "mallory", "item": "USB-C cable",    "amount": "$12.99"},
}


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user")
    if user not in USERS:
        abort(400)
    return jsonify({"token": _issue_token(user)})


@app.route("/api/orders")
def list_orders():
    caller = _authenticate()
    # Correctly scoped: only the caller's own orders.
    return jsonify([o for o in ORDERS.values() if o["owner"] == caller])


@app.route("/api/orders/<int:order_id>")
def get_order(order_id):
    _authenticate()   # require a valid token (401 otherwise) -- AUTHENTICATION only
    order = ORDERS.get(order_id)
    if order is None:
        abort(404)
    # VULNERABLE: the request is authenticated, but the order is returned WITHOUT
    # checking that order["owner"] is the authenticated caller. Being authenticated
    # is not being authorized for THIS object. (BOLA -- no object-level check.)
    return jsonify(order)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
