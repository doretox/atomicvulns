import os
from lxml import etree
from flask import Flask, request, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/import", methods=["POST"])
def import_contact():
    xml = request.form.get("xml", "")
    # VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES
    # (resolve_entities=True). A DOCTYPE with a SYSTEM entity (file://) is expanded, so an
    # attacker-defined entity reads a server file and its contents come back in the echoed
    # <name>. The bug is this parser config, not the import logic. no_network=True keeps it
    # to file:// (local file read), never the network -- arbitrary file disclosure, not SSRF.
    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=True)  # dangerous
    try:
        doc = etree.fromstring(xml.encode("utf-8"), parser)
        name = doc.findtext("name") or ""
    except etree.XMLSyntaxError as exc:
        return render_template("result.html", name=None, error=str(exc))
    return render_template("result.html", name=name, error=None)  # name autoescaped in a <pre>


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
