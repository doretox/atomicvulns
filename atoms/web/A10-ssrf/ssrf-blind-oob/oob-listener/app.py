import os
import logging
from flask import Flask, request

logging.basicConfig(level=logging.INFO)  # ensure INFO lines reach docker compose logs
app = Flask(__name__)


# oob-listener: a dumb out-of-band sink. It logs every inbound request so the student can
# confirm, via `docker compose logs oob-listener`, that the vulnerable server reached out.
# Self-hosted, air-gapped analog of a public interaction server (e.g. Burp Collaborator).
# TRIPWIRE, not a target: it holds no secret and is reachable ONLY from inside the Docker
# network (no host port). Reaching it at all is the whole proof.
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch(path):
    app.logger.info("OOB HIT path=/%s from=%s", path, request.remote_addr)
    return "ok"


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=80)
