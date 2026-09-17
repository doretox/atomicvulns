import os
import uuid
from datetime import datetime, timezone

from flask import Flask, abort, render_template, request

app = Flask(__name__)

# --- Simulated identity (same convention as idor-numeric-id) ---
ATTACKER = "mallory"   # you; the default caller when X-User-ID is absent
VICTIM = "alice"       # the victim; her receipt is seeded at import


def _new_receipt_id():
    # FIXED (defense-in-depth): a v4 UUID comes from a CSPRNG and embeds no
    # timestamp or node, so it cannot be reconstructed from exposed metadata.
    # This is NOT the fix that matters -- see view_receipt below.
    return uuid.uuid4()


# --- In-memory store (no database, like idor-numeric-id) ---
RECEIPTS = {}   # str(uuid) -> {"id", "owner", "item", "amount", "issued_at"}


def _add_receipt(owner, item, amount):
    u = _new_receipt_id()
    issued_at = datetime.now(timezone.utc)
    RECEIPTS[str(u)] = {"id": str(u), "owner": owner, "item": item,
                        "amount": amount, "issued_at": issued_at}
    return RECEIPTS[str(u)]


# Seed the victim's receipt at import.
_add_receipt(VICTIM, "Noise-cancelling headphones", "$1,299.00")


@app.route("/")
def index():
    caller = request.headers.get("X-User-ID", ATTACKER)
    overview = sorted(RECEIPTS.values(), key=lambda r: r["issued_at"])
    return render_template("index.html", caller=caller, overview=overview)


@app.route("/receipt", methods=["POST"])
def create_receipt():
    caller = request.headers.get("X-User-ID", ATTACKER)
    r = _add_receipt(caller, "Mechanical keyboard", "$499.00")
    return render_template("receipt.html", receipt=r)


@app.route("/receipt/<uuid:receipt_id>")
def view_receipt(receipt_id):
    caller = request.headers.get("X-User-ID", ATTACKER)
    r = RECEIPTS.get(str(receipt_id))
    if r is None:
        abort(404)
    # FIXED (the fix that matters): serve the receipt only to its owner. This
    # single check closes the IDOR even if the id scheme had stayed v1 and the
    # dashboard kept leaking issued_at -- obscurity was never the access control.
    if r["owner"] != caller:
        abort(403)
    return render_template("receipt.html", receipt=r)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
