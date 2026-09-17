import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Flask, request, jsonify

app = Flask(__name__)
# Dummy fixed key -- this is a lab; the KEY is NOT the vuln (CLAUDE.md §8.3). The attack below
# never touches the key: it forges a badge by rearranging ciphertext blocks. 16-byte AES key.
KEY = b"atomicvulns-lab!"


def issue_badge(email, role):
    plaintext = f"email={email}&role={role}".encode()
    # VULNERABLE: AES-ECB. Each 16-byte block is encrypted INDEPENDENTLY with the same key, so
    # identical plaintext blocks -> identical ciphertext blocks (the pattern leaks), and blocks
    # can be CUT and REARRANGED across badges to forge a plaintext without knowing the key. The
    # mode is the flaw -- see fixed/ for the authenticated mode that detects tampering.
    cipher = AES.new(KEY, AES.MODE_ECB)
    return cipher.encrypt(pad(plaintext, AES.block_size)).hex()


def read_badge(token):
    cipher = AES.new(KEY, AES.MODE_ECB)
    plaintext = unpad(cipher.decrypt(bytes.fromhex(token)), AES.block_size)
    return dict(kv.split("=", 1) for kv in plaintext.decode().split("&"))


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login with {\"email\": \"...\", \"password\": \"...\"} to get a badge, "
                "then GET /me with 'Authorization: Bearer <badge>'. Work from Burp Repeater.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    # Simulated auth (JWT-sibling pattern): the password is not verified -- it is orthogonal to
    # the vuln. The role is ALWAYS "user"; the server never mints an admin badge. You forge it.
    return jsonify({"badge": issue_badge(email, "user")})


@app.route("/me")
def me():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return jsonify({"error": "missing or malformed Authorization header"}), 401
    try:
        fields = read_badge(auth.split(" ", 1)[1].strip())
    except Exception:
        return jsonify({"error": "invalid badge"}), 400
    if fields.get("role") == "admin":
        return jsonify({"email": fields.get("email"), "role": "admin",
                        "admin_area": "internal admin dashboard (dummy lab content)"})
    return jsonify({"email": fields.get("email"), "role": fields.get("role")})


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
