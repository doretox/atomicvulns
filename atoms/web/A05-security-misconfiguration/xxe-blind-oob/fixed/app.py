import os
from lxml import etree
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/import", methods=["POST"])
def import_batch():
    xml = request.data
    # FIXED: turn off external-entity resolution AND DTD loading -- the two flags that ARE the
    # cause. Both are load-bearing: with only resolve_entities=False the DTD is still loaded and
    # the external parameter entity is still fetched; with only load_dtd=False entity resolution
    # still fetches it. Off together, the attacker DTD is never retrieved -- no OOB callback, no
    # exfil. no_network is left as the vulnerable app had it (False) on purpose: blocking the
    # network would stop THIS channel but is not the XXE fix (the parser would still resolve
    # entities); the fix is at entity resolution. The response is byte-identical to the vulnerable
    # version -- the fix hardens the PARSER, never the response.
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=False)  # hardened
    try:
        etree.fromstring(xml, parser)
    except etree.XMLSyntaxError:
        pass
    return jsonify(status="received")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
