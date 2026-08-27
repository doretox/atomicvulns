import os

from flask import Flask, render_template

app = Flask(__name__)

# The attacker site serves a page whose JavaScript makes a CREDENTIALED cross-origin
# fetch to the victim's /account and shows whatever it can read. The attacker origin
# (attacker.localhost) is a DIFFERENT site from the victim (victim.localhost), which is
# what makes the fetch cross-origin. The attacker never talks to the victim itself --
# the victim's browser makes every cross-origin request.
TARGETS = {
    "vuln": "http://victim.localhost:8034/account",
    "fixed": "http://victim.localhost:8134/account",
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
