import os
from lxml import etree
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/import", methods=["POST"])
def import_batch():
    xml = request.data  # raw XML body (Content-Type: application/xml)
    # VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES, loads DTDs,
    # and is allowed to reach the NETWORK (no_network=False). A DOCTYPE that declares an external
    # parameter entity pointing at an attacker-hosted DTD makes the parser FETCH that DTD -- an
    # outbound request to a destination the attacker chose. Nothing about the entity is echoed:
    # the response below is a generic ack. The XXE is real, it is merely BLIND, so it is confirmed
    # out-of-band (see the oob-listener service). The bug is this parser config, not the import
    # logic. Same cause as xxe-basic; the parser-config delta is no_network=False -- that flag is
    # what lets the parser reach the network, turning an in-band file read into an OOB channel.
    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)  # dangerous
    try:
        etree.fromstring(xml, parser)  # parsing resolves the external entity -> OOB fetch
    except etree.XMLSyntaxError:
        pass  # swallow: surfacing the parse error would leak an in-band oracle
    return jsonify(status="received")  # generic: says nothing about what the parser resolved


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
