import os
from flask import Flask, render_template

app = Flask(__name__)

# The attacker site serves pages that auto-submit a forged cross-site POST to the
# target's /email. Both targets live on 127.0.0.1; this site is a DIFFERENT site
# (127.0.0.2), which is what makes the request cross-site. The attacker never talks
# to the targets itself -- the victim's browser makes every request.
TARGETS = {
    "vuln": "http://127.0.0.1:8023/email",
    "fixed": "http://127.0.0.1:8123/email",
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/attack-vuln")
def attack_vuln():
    return render_template("attack.html", target=TARGETS["vuln"])


@app.route("/attack-fixed")
def attack_fixed():
    return render_template("attack.html", target=TARGETS["fixed"])


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
