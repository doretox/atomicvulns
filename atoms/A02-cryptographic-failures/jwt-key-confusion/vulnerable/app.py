import os
import json
import hmac
import hashlib
import base64
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


def _b64url_decode(seg):
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def verify(token):
    # VULNERABLE: the server reads alg from the token's OWN header and picks the
    # verification family from it. RS256 -> RSA-verify with the public key (safe, correct).
    # HS256 -> HMAC-verify using the SAME public-key bytes as the secret (!). The public
    # key is public (served at /jwks), so under HS256 anyone can forge. This alg-controlled
    # branch is the whole bug. (PyJWT refuses an asymmetric key as an HMAC secret, so the
    # HS256 branch is hand-rolled — which is exactly where key confusion lives in the wild.)
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(PUBLIC_KEY_PEM, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            raise ValueError("bad HS256 signature")
        return json.loads(_b64url_decode(payload_b64))
    if alg == "RS256":
        return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
    raise ValueError("unsupported alg")


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
