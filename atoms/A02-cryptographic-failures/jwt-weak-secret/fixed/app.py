import os
import jwt
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# HS256 signing secret. The verification logic below is correct and byte-identical in
# both vulnerable/ and fixed/ — the whole security of this atom rests on the strength
# of this one value. See DIFF.md.
SECRET = "jlui6jbnFeh9_BXEPw4wUaF1UwEfZ2R9uaSkVqDoWuk"  # FIXED: strong, high-entropy (secrets.token_urlsafe(32)); not in any wordlist

# Admin-only directory. Benign fake data: no PII, no secrets, and never the SECRET.
USERS = [
    {"user": "alice", "role": "user"},
    {"user": "bob", "role": "user"},
    {"user": "carol", "role": "admin"},
]


def decode(token):
    # HS256 as a positive, closed allowlist: no alg:none branch, no branch on the
    # header. Byte-identical to jwt-none-alg (05)'s FIXED decode — the algorithm is
    # handled correctly here. What differs between vulnerable/ and fixed/ is only the
    # SECRET the token is signed and verified with (see the SECRET constant / DIFF.md).
    return jwt.decode(token, SECRET, algorithms=["HS256"])


def authenticate():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        abort(401)
    try:
        return decode(auth.split(" ", 1)[1].strip())
    except jwt.PyJWTError:
        abort(401)


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "alice")  # no password — auth ceremony out of scope
    token = jwt.encode({"sub": user, "role": "user"}, SECRET, algorithm="HS256")
    return jsonify({"token": token})  # role is always "user"; /login never mints admin


@app.route("/api/profile")
def profile():
    claims = authenticate()
    return jsonify({"sub": claims.get("sub"), "role": claims.get("role")})


@app.route("/admin/users")
def admin_users():
    claims = authenticate()
    if claims.get("role") != "admin":
        abort(403)
    return jsonify(USERS)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
