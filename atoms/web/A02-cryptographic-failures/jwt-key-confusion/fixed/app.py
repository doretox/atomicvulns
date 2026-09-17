import os
import jwt
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# Fixed DUMMY lab RSA keypair (2048-bit). NEVER a real key — committed only because this
# is an intentionally-vulnerable lab (CLAUDE.md §8.3). Same keypair in vulnerable/ and
# fixed/. The private key signs; the public key is published at /jwks and is exactly the
# secret an attacker forges with under HS256 (see DIFF.md).
_KEYS = os.path.join(os.path.dirname(__file__), "keys")
PRIVATE_KEY_PEM = open(os.path.join(_KEYS, "private.pem"), "rb").read()
PUBLIC_KEY_PEM = open(os.path.join(_KEYS, "public.pem"), "rb").read()

# Admin-only directory. Benign fake data: no PII, no secrets, and never a key.
USERS = [
    {"user": "alice", "role": "user"},
    {"user": "bob", "role": "user"},
    {"user": "carol", "role": "admin"},
]


def verify(token):
    # FIXED: stop asking the token which algorithm to use. Pin RS256 and let PyJWT enforce
    # it — a token with alg:HS256 is rejected (HS256 isn't in the allowlist). Same shape as
    # jwt-none-alg's fix: don't branch on the token's alg; declare the allowlist, let the
    # library impose it. The public key is now only ever a *verification* key, never an
    # HMAC secret.
    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])


def authenticate():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        abort(401)
    try:
        return verify(auth.split(" ", 1)[1].strip())
    except Exception:
        abort(401)


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "alice")  # no password — auth ceremony out of scope
    token = jwt.encode({"sub": user, "role": "user"}, PRIVATE_KEY_PEM, algorithm="RS256")
    return jsonify({"token": token})  # role is always "user"; /login never mints admin


@app.route("/jwks")
def jwks():
    # Publishing the RSA PUBLIC key is correct and by design: clients verify tokens with
    # it. This is NOT the bug. The bug is the vulnerable server later accepting this same
    # key as an HMAC secret. The bytes served here are the exact bytes the HS256 branch
    # HMACs with — that is what makes the forgery match.
    return PUBLIC_KEY_PEM, 200, {"Content-Type": "application/x-pem-file"}


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
