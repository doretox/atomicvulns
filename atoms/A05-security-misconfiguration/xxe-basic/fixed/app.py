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
    # FIXED: parse with external-entity resolution and DTD loading DISABLED
    # (resolve_entities=False, load_dtd=False). A SYSTEM entity is never resolved, so file://
    # payloads cannot read server files -- the echoed <name> comes back empty. This is the
    # canonical XXE defense for an lxml app: turn off the dangerous parser features.
    # (defusedxml's lxml support is deprecated; hardening the parser directly is the advice.)
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)  # hardened
    try:
        doc = etree.fromstring(xml.encode("utf-8"), parser)
        name = doc.findtext("name") or ""
    except etree.XMLSyntaxError as exc:
        return render_template("result.html", name=None, error=str(exc))
    return render_template("result.html", name=name, error=None)  # name autoescaped in a <pre>


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
