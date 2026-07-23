import os
import json
from flask import Flask, Response

app = Flask(__name__)

# Fake IMDS. Serves the minimal surface an SSRF attacker walks: the role name, then the
# credentials JSON. Credentials are the AWS-documented EXAMPLE values -- OBVIOUSLY FAKE, no
# real secret. IMDSv1-style (plain GET, no PUT token) ON PURPOSE: that reachability is what
# the SSRF exploits, and IMDSv2 is the "mentionable, not applied" hardening (see DIFF).
ROLE = "app-instance-role"

CREDS = {
    "Code": "Success",
    "LastUpdated": "2026-07-23T00:00:00Z",
    "Type": "AWS-HMAC",
    "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",  # ASIA... == temporary/STS creds (what IMDS returns)
    "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "Token": "IQoJb3JpZ2luX2VjEXAMPLEtokenEXAMPLEtokenEXAMPLEtokenEXAMPLE=",
    "Expiration": "2026-07-23T06:00:00Z",
}


@app.route("/latest/meta-data/iam/security-credentials/")
def role_list():
    return Response(ROLE + "\n", mimetype="text/plain")  # the attacker learns the role name


@app.route("/latest/meta-data/iam/security-credentials/<role>")
def role_creds(role):
    if role != ROLE:
        return Response("", status=404)
    # AccessKeyId / SecretAccessKey / Token -- the loot. Pretty-printed like the real IMDS.
    return Response(json.dumps(CREDS, indent=2) + "\n", mimetype="application/json")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=80)
