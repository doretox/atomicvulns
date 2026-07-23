# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is the parser the `POST /import` view builds (comments abbreviated):

```diff
 @app.route("/import", methods=["POST"])
 def import_contact():
     xml = request.form.get("xml", "")
-    # VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES ...
-    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=True)  # dangerous
+    # FIXED: parse with external-entity resolution and DTD loading DISABLED ...
+    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)  # hardened
     try:
         doc = etree.fromstring(xml.encode("utf-8"), parser)
         name = doc.findtext("name") or ""
     except etree.XMLSyntaxError as exc:
         return render_template("result.html", name=None, error=str(exc))
     return render_template("result.html", name=name, error=None)
```

The templates (`index.html`, `result.html`), the `Dockerfile` (including the line that plants the dummy `/app/secret.txt`), and `requirements.txt` are byte-for-byte identical between the two versions. The bug lives entirely in two parser flags.

## What changed

One edit, in `app.py`: the flags passed to `etree.XMLParser`. The vulnerable version sets `resolve_entities=True, load_dtd=True`; the fixed version sets both to `False`. `no_network=True` is unchanged — both versions keep it. Nothing else moves: the `try/except`, the `findtext("name")`, the template render, and every other file are the same. This is a *configuration-different* fix — the same code path, the dangerous parser features switched off — the smallest possible expression of "one setting is the whole bug".

## Why this fixes the bug

The class is: the parser resolves entities the attacker declares in the document, so a `SYSTEM` entity pointing at `file:///…` expands to that file's contents, which the app echoes back in `<name>`. Disabling external-entity resolution (`resolve_entities=False`) and DTD processing (`load_dtd=False`) means the `<!ENTITY x SYSTEM …>` declaration is never acted on and `&x;` is never expanded into a file read. In this lab the observable result is that `<name>` comes back **empty** — the reference resolves to nothing — so no file contents are disclosed. The benign contact (no `DOCTYPE`, no entities) parses and imports exactly as before; only the dangerous capability is gone.

## lxml, not the standard library

Python's standard library ships `xml.etree.ElementTree`, and it does **not** resolve external entities — feed it this atom's payload and the entity is simply never expanded. An atom built on it would not be vulnerable at all. That is why this lab uses **`lxml`**, the popular third-party parser (chosen in real projects for speed and XPath), which *can* resolve external entities. The vulnerability is a property of *which parser you use and how you configure it*, not of "parsing XML".

This is the same honest move as two earlier atoms: `jwt-key-confusion` (modern PyJWT refuses the naive algorithm confusion, so that atom hand-rolls the broken check) and `session-fixation` (Flask's signed-cookie session resists fixation by design, so that atom models a manual server-side session). In each case the default tool already mitigates the naive bug, so the atom models the real-world component where the vulnerability actually lives — here, an `lxml` parser told to resolve entities.

## The lxml default — this version is safe, so the app opts in

You might expect the vulnerable app to just use lxml's default parser and be done. It cannot, and the reason is worth stating honestly. In the pinned version (**lxml 5.3.0, libxml2 2.12.9**) the bare default is *safe*: `etree.fromstring(xml)` raises `Entity 'x' not defined` on our payload, because it does not act on the DTD's entity declaration. So the vulnerable app **opts in**, building `etree.XMLParser(resolve_entities=True, load_dtd=True)`.

That opt-in is the realistic anti-pattern. A developer turns on entity/DTD processing — to expand legitimate in-document entities, or by copying an old snippet — and inherits external-entity resolution along with it. (A subtle detail confirmed by running this version: `resolve_entities=True` is lxml's *documented* default value, yet passing it **explicitly** is what makes libxml2 substitute the external entity here, while the bare default does not. Either way, the app's explicit configuration is what opens the hole.)

The durable rule does not depend on the version: **never resolve external entities in untrusted XML.** Which parser configuration is dangerous is version-specific, so this atom's behavior was confirmed by running the exact pinned version — never assumed. If you bump `lxml`, re-check.

## defusedxml — mentioned, not applied

The name that comes up for XML hardening in Python is **`defusedxml`**. This atom deliberately does not use it. `defusedxml` is the right tool for the *standard library*, but its **`lxml` support is deprecated** — the project's own guidance is to configure `lxml` directly (turn off entity resolution, DTD loading, and network access on the parser), which is exactly what `fixed/app.py` does. So `defusedxml` is named here, not applied: the same "name the real-world control, keep the diff to the one change it teaches" move that `ssrf-cloud-metadata` makes with IMDSv2.

## This atom is file disclosure, not SSRF

Both parsers keep `no_network=True` (lxml's default). That confines entity resolution to local files: a `file://` entity reads a file, but an `http://` entity is **not** fetched — point one at a URL and `<name>` comes back empty (verified). So this atom stays firmly in **arbitrary file disclosure** and never issues a network request. Keeping `no_network=True` in the vulnerable app is deliberate: it guarantees the lesson is a clean file read and cannot accidentally drift into a server-side request.

## The echo is escaped on purpose

`result.html` renders the imported name inside `<pre>{{ name }}</pre>` with Jinja autoescaping on (no `|safe`, no `Markup`, no `render_template_string`). When the "name" is a file full of `<`/`>` — or an attacker sends a name of `<script>alert(1)</script>` — it comes back as `&lt;script&gt;alert(1)&lt;/script&gt;` in the page source: text, not markup. This is deliberate. Displaying the disclosed file must not become a second vulnerability (reflected XSS / HTML injection). The one bug here is the XXE — the parser resolving an external entity — and how the result is shown is not part of it. The fix does not touch the template; the two versions' templates are byte-identical.

## No billion-laughs DoS

A separate XXE-adjacent hazard is the "billion laughs" attack: nested entities that expand exponentially and exhaust memory. That is a *different* vector from the file read this atom teaches, and it is kept off the table: lxml's default (`huge_tree=False`) caps entity amplification, so a billion-laughs payload is rejected with `Maximum entity amplification factor exceeded` and the container stays up — the `except XMLSyntaxError` renders a controlled error page. The one and only vulnerability here is external-entity resolution.
