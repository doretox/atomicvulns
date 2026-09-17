import os

from flask import Flask, request, jsonify
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.utils.conv import escape_filter_chars

app = Flask(__name__)

# Connection settings come from the environment (see docker-compose.yml). The app
# binds as a low-privilege service account -- NOT the directory admin -- that is
# allowed to search the userPassword attribute, then decides auth by whether the
# search matched. (See DIFF.md on why a real design would BIND as the user.)
LDAP_URL = os.environ.get("LDAP_URL", "ldap://ldap:389")
BIND_DN = os.environ.get("LDAP_BIND_DN", "cn=svc,dc=example,dc=com")
BIND_PW = os.environ.get("LDAP_BIND_PW", "svc-bind-pw")
PEOPLE_DN = os.environ.get("LDAP_PEOPLE_DN", "ou=people,dc=example,dc=com")

server = Server(LDAP_URL, get_info=ALL)


@app.route("/")
def index():
    # Banner only -- the vulnerability lives in POST /login (see WALKTHROUGH.md).
    return jsonify(
        {
            "warning": "⚠️ Intentionally vulnerable. Run locally only. "
            "Never expose to the internet or a shared network.",
            "hint": 'POST /login with a JSON body: {"user": "...", '
            '"password": "..."}. Work from Burp Repeater.',
        }
    )


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "")
    password = body.get("password", "")
    # FIXED: escape the RFC 4515 filter metacharacters in every untrusted value
    # before building the filter. * ( ) \ become literal data (\2a \28 \29 \5c),
    # so user/password are matched as VALUES, never interpreted as filter
    # structure. The filter is always the intended (&(uid=<v>)(userPassword=<v>)).
    filt = f"(&(uid={escape_filter_chars(user)})(userPassword={escape_filter_chars(password)}))"
    print("LDAP search filter:", filt, flush=True)
    conn = Connection(server, BIND_DN, BIND_PW, auto_bind=True)
    conn.search(PEOPLE_DN, filt, search_scope=SUBTREE, attributes=["uid"])
    if conn.entries:
        return jsonify({"authenticated": True, "uid": str(conn.entries[0].uid)})
    return jsonify({"authenticated": False}), 401


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
