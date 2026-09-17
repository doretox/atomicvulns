import os

from flask import Flask, render_template

app = Flask(__name__)

# The attacker site serves a page whose JavaScript makes a CREDENTIALED cross-origin
# fetch to the victim's /account and shows whatever it can read. The attacker origin
# (evil.lab.localhost) is a hostile SIBLING subdomain of the victim (api.lab.localhost):
# a DIFFERENT origin, so CORS still governs the read, but the SAME site (both under
# lab.localhost), so the browser's third-party-cookie partitioning does NOT strip the
# victim's cookie from the request -- think a compromised/forgotten subdomain or a
# subdomain takeover. The attacker never talks to the victim itself; the victim's browser
# makes every cross-origin request.
TARGETS = {
    "vuln": "http://api.lab.localhost:8034/account",
    "fixed": "http://api.lab.localhost:8134/account",
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/attack-vuln")
def attack_vuln():
    return render_template("attack.html", target=TARGETS["vuln"], which="vulnerable")


@app.route("/attack-fixed")
def attack_fixed():
    return render_template("attack.html", target=TARGETS["fixed"], which="fixed")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
