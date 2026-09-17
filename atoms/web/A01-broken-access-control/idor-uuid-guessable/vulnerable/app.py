import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from flask import Flask, abort, render_template, request

app = Flask(__name__)

# --- Simulated identity (same convention as idor-numeric-id) ---
ATTACKER = "mallory"   # you; the default caller when X-User-ID is absent
VICTIM = "alice"       # the victim; her receipt is seeded at import

# --- UUIDv1 generator with a STABLE node + clock_seq for the whole process ---
# RFC 4122 recommends initializing the clock sequence with a random value and
# then persisting it, so a spec-faithful generator (and most non-stdlib
# libraries) keeps node + clock_seq stable. Python's uuid.uuid1() deliberately
# does NOT -- it draws a fresh random clock_seq on every call, an accidental
# mitigation we bypass here to model the RFC-faithful (reconstructible) behavior.
_NODE = uuid.getnode()               # stable per process (the container's MAC)
_CLOCK_SEQ = random.getrandbits(14)  # drawn ONCE at import, then stable

# 100ns intervals between the UUID (Gregorian) epoch 1582-10-15 and 1970-01-01.
_UUID_EPOCH_100NS = 0x01b21dd213814000
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _new_receipt_id():
    return uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)


def _issued_at_from(u):
    # Derive issued_at from the id's OWN timestamp so the exposed field and the
    # id describe one instant. Integer math (no float) preserves microseconds.
    unix_us = (u.time - _UUID_EPOCH_100NS) // 10
    return _UNIX_EPOCH + timedelta(microseconds=unix_us)


# --- In-memory store (no database, like idor-numeric-id) ---
RECEIPTS = {}   # str(uuid) -> {"id", "owner", "item", "amount", "issued_at"}


def _add_receipt(owner, item, amount):
    u = _new_receipt_id()
    issued_at = _issued_at_from(u)
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
    r = RECEIPTS.get(str(receipt_id))
    if r is None:
        abort(404)
    # VULNERABLE: no ownership check -- any caller who holds (or reconstructs)
    # the id reads the receipt. The unguessable-looking UUID is treated as the
    # access control; it is not one.
    return render_template("receipt.html", receipt=r)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
