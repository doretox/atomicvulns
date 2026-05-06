import os
from flask import Flask, Response

app = Flask(__name__)

DASHBOARD = """\
Internal Admin Dashboard

This service lives on the corporate internal network and must never
be exposed to the public internet.

API_KEY_PROD     = sk_live_a1b2c3d4e5f6g7h8i9j0
API_KEY_STAGE    = sk_test_z9y8x7w6v5u4t3s2r1q0
DATABASE_URL     = postgres://admin:hunter2@db.internal:5432/prod
JWT_SIGNING_KEY  = changeme-internal-jwt-987654321
SMTP_RELAY       = smtp.internal:25 (no auth)

See also: /users
"""

USERS = """\
Internal Users

id  name             email                 role
1   Alice Anderson   alice@example.corp    admin
2   Bob Brown        bob@example.corp      operator
3   Carol Chen       carol@example.corp    auditor
"""


@app.route("/")
def dashboard():
    return Response(DASHBOARD, mimetype="text/plain")


@app.route("/users")
def users():
    return Response(USERS, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=80)
