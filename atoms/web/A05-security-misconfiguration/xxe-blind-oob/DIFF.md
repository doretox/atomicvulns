# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is the parser the `POST /import` view builds (comments abbreviated):

```diff
 @app.route("/import", methods=["POST"])
 def import_batch():
     xml = request.data
-    # VULNERABLE: parser RESOLVES EXTERNAL ENTITIES, loads DTDs, reaches the NETWORK ...
-    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)  # dangerous
+    # FIXED: external-entity resolution and DTD loading OFF -- the two flags that are the cause ...
+    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=False)  # hardened
     try:
         etree.fromstring(xml, parser)
     except etree.XMLSyntaxError:
         pass
     return jsonify(status="received")
```

`requirements.txt`, the `Dockerfile` (including the line that plants the dummy `/app/secret.txt`), and the `oob-listener` service are byte-for-byte identical between the two versions. The bug lives entirely in the parser flags.

## What changed

One edit, in `app.py`: the flags passed to `etree.XMLParser`. The vulnerable version sets `resolve_entities=True, load_dtd=True`; the fixed version sets both to `False`. `no_network=False` is **unchanged** — both versions keep it. Nothing else moves: the `request.data`, the `try/except`, the `etree.fromstring`, and the untouched `return jsonify(status="received")` are identical. This is a *logic-different* fix — the same code path, the dangerous parser features switched off — and, crucially, the response line does not change: **the fix hardens the parser, never the response.**

## Why this fixes the bug

The class is: the parser resolves entities the attacker declares, so an external parameter entity pointing at `http://…` makes the parser **fetch** the attacker's DTD, which then drives a further request that carries a server file out. Disabling external-entity resolution (`resolve_entities=False`) and DTD processing (`load_dtd=False`) means the `<!ENTITY % ext SYSTEM …>` declaration is never acted on and `%ext;` is never expanded into a fetch. In this lab the observable result is that the `oob-listener` records **no** callback for the fixed app — the parser reaches for nothing. The benign document (no `DOCTYPE`, no entities) parses and acknowledges exactly as before; only the dangerous capability is gone.

## Both flags are load-bearing — the minimal fix

The fix flips **two** flags, and both are necessary. This was confirmed by running the pinned parser (`lxml==5.3.0`, `libxml2` 2.12.9) against the attack payload under each configuration:

| Parser config | External DTD fetched? |
|---|---|
| `resolve_entities=True,  load_dtd=True` (vulnerable) | **yes** — the OOB callback fires |
| `resolve_entities=False, load_dtd=True` | **yes** — DTD loading alone still fetches it |
| `resolve_entities=True,  load_dtd=False` | **yes** — entity resolution alone still fetches it |
| `resolve_entities=False, load_dtd=False` (fixed) | **no** — the callback never fires |

Turning off only one flag leaves a path that still retrieves the DTD, so the fix must disable **both** external-entity resolution and DTD loading. That is the minimal change that closes the cause.

**Why `no_network` is *not* the fix.** Setting `no_network=True` alone also stops the callback — but that is the wrong lesson. Blocking the network is an egress control layered *on top of* an unchanged XXE: the parser would still resolve external entities, still read `file://` resources, still be vulnerable in any deployment where the network is reachable (which is most of them). The fix has to be at **entity resolution**, which is why the diff changes the two entity flags and deliberately leaves `no_network=False` — the same value the vulnerable app had. With entity and DTD resolution off, the parser resolves no external reference at all, so network access is moot; leaving it unchanged keeps the diff pointed squarely at the cause instead of hiding it behind a firewall flag.

## Hiding the echo is not a fix

The instinct after seeing `xxe-basic` (which *did* echo the file back) is: "the problem was the value coming back in the response, so just stop returning it." That instinct is wrong, and this atom is built to prove it. The `/import` app **already** returns nothing but `{"status":"received"}` — it never echoes — and it is fully vulnerable: the parser resolves the entity and reaches out regardless of what the response says. Hiding output removes your *in-band* confirmation; it does nothing to the parser. The response line (`return jsonify(status="received")`) is byte-identical in both versions precisely to make this concrete — it was never the control. The fix has to act on the **parser**, which is exactly what the response does not touch.

## Same bug as xxe-basic, different channel

`xxe-basic` (in-band) and this atom (blind, out-of-band) are the same vulnerability class with the same fix. What differs is the channel:

| | `xxe-basic` (in-band) | `xxe-blind-oob` (blind / out-of-band) |
|---|---|---|
| Category | A05 — Security Misconfiguration | A05 — Security Misconfiguration (the same) |
| Cause | parser resolves external entities / DTD | the **same** |
| Channel | in-band — the value comes back in the response | out-of-band — the parser's request to the listener |
| What you observe | the file on the HTTP response | the hit arriving in the listener log |
| Fix | `resolve_entities=False, load_dtd=False` | the **same** |

The hinge is a single parser flag: **`no_network`**. `xxe-basic`'s vulnerable parser keeps `no_network=True`, so the entity resolves only `file://` — a local file read, echoed back in-band. This atom's vulnerable parser sets `no_network=False`, so the parser reaches the **network**; with the response mute, the proof becomes the out-of-band callback. Same cause, same fix — the vulnerable app's one different flag is what turns an in-band file read into an out-of-band channel. That is why these are two atoms: the cause is one bug, but the confirmation channel is the thing worth studying twice.

## lxml, not the standard library

Python's standard library ships `xml.etree.ElementTree`, and it does **not** resolve external entities — feed it this payload and the entity is simply never expanded. An atom built on it would not be vulnerable at all. That is why this lab uses **`lxml`** (over `libxml2`), the popular third-party parser (chosen in real projects for speed and XPath), which *can* resolve external entities. The vulnerability is a property of *which parser you use and how you configure it*, not of "parsing XML" — the same honest move `xxe-basic` makes. Because that behaviour is version-specific, the parser is pinned and the out-of-band fetch was confirmed by running the exact version; if you bump `lxml`, re-check.

## defusedxml — mentioned, not applied

The name that comes up for XML hardening in Python is **`defusedxml`**. This atom deliberately does not use it. `defusedxml` is the right tool for the *standard library*, but its **`lxml` support is deprecated** — the project's own guidance is to configure `lxml` directly (turn off entity resolution and DTD loading on the parser), which is exactly what `fixed/app.py` does. So `defusedxml` is named here, not applied.

## Why the listener is embedded

The atom ships its own out-of-band sink (`oob-listener`) rather than telling you to point payloads at a real interaction server. Detecting blind XXE in the field depends on an **external** service you control — Burp Collaborator, `interactsh`, a DNS/HTTP catcher on the internet. This lab is isolated by design (bound to `127.0.0.1`, no dependency on the outside world), so its exploit cannot require reaching a third party. Embedding a self-hosted, air-gapped analog of that sink is what lets the attack be reproduced offline, by anyone, with nothing but `docker compose logs`. The listener is **infrastructure, orthogonal to the vulnerability** — it holds no secret and is not the object of study; the file that exfiltrates is the vulnerable app's own. It is the same discipline `ssrf-blind-oob` uses, and the file it plants (`/app/secret.txt`) lives in both the vulnerable and fixed images so a fixed-side no-leak is attributable to the parser, not a missing file.

## No billion-laughs DoS

A separate XXE-adjacent hazard is the "billion laughs" attack: nested entities that expand exponentially and exhaust memory. That is a *different* vector from the out-of-band channel this atom teaches, and it is kept off the table: `lxml`'s default (`huge_tree=False`, which neither version changes) caps entity amplification, so a billion-laughs payload is rejected with `Maximum entity amplification factor exceeded` and the container stays up. The one and only vulnerability here is external-entity resolution reaching the network.
