import os
import jwt
from flask import Flask, request, render_template, abort

app = Flask(__name__)
SECRET = "atomicvulns-demo-secret-do-not-use"


def decode(token):
    header = jwt.get_unverified_header(token)
    if header.get("alg") == "none":
        # TODO: remove after local testing — accepts unsigned tokens
        return jwt.decode(token, options={"verify_signature": False})
    return jwt.decode(token, SECRET, algorithms=["HS256"])


def authenticate():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        abort(401)
    try:
        return decode(auth.split(" ", 1)[1].strip())
    except jwt.PyJWTError:
        abort(401)


@app.route("/")
def index():
    username, role = "alice", "user"
    token = jwt.encode({"sub": username, "role": role}, SECRET, algorithm="HS256")
    return render_template("index.html", token=token, username=username, role=role)


@app.route("/me")
def me():
    claims = authenticate()
    body = f"sub={claims.get('sub')}\nrole={claims.get('role')}\n"
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/admin")
def admin():
    claims = authenticate()
    if claims.get("role") != "admin":
        abort(403)
    return render_template("admin.html", username=claims.get("sub"))


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
