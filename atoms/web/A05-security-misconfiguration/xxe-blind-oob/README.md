# xxe-blind-oob — Blind XXE (out-of-band)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for **blind XXE**. The app is a bulk XML importer: you `POST` an XML document to `/import`, the server parses it, and it always answers the same generic `{"status": "received"}` — it never echoes anything from the document back. The parser resolves **external entities**, so a document whose `DOCTYPE` declares an external entity pointing at a server *you* control makes the parser reach out to it — an outbound request the app never meant to make. Because the response is mute, you cannot read anything in-band. So you confirm the vulnerability **out-of-band**: you point the entity at a listener you control and watch the callback arrive. The same external-entity resolution then lets you exfiltrate a server-side file over that channel.

This is the second atom in A05 — Security Misconfiguration, and the blind sibling of `xxe-basic`. There, the server parsed your XML **and echoed a field back** — you read `/etc/passwd` straight off the response, in-band. Here the response tells you nothing. That does **not** mean the XXE is gone: the parser still resolves the external entity you declared and still reaches out. It only means you have lost the channel to *read* the result in the response. So how do you prove it happened? You make the parser call home to a listener you control, and confirm it **out-of-band**. Blind does not mean absent; it means you confirm it elsewhere.

> **Theory primer:** Read [PortSwigger: Blind XXE](https://portswigger.net/web-security/xxe/blind)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Blind is not in-band — and it is not absent

Keep this straight, because it *is* the lesson. Blind XXE is not a weaker XXE; it is the **same** parser misconfiguration — external-entity resolution left on — minus the convenient echo. The parser resolving your external entity is the vulnerability. Whether the response reflects the result is a *separate axis*: only how easy it is to confirm. `xxe-basic` gave you the resolved value in the response; here you have the resolution and **no** read channel, so detection moves out-of-band. The beginner trap this atom isolates is "no echo, so nothing leaks" — false, and the fix that follows from it (hide the echo) is not a fix at all: the app already hides everything and is still vulnerable. The only fix is at the **parser**.

## Same bug as xxe-basic, different channel

`xxe-basic` (atom 18, in-band) and this atom (blind, out-of-band) share the **same root cause** — an `lxml` parser configured to resolve external entities and load DTDs — and the **same fix** — turn those two parser features off. What differs is the channel:

| | `xxe-basic` (in-band) | `xxe-blind-oob` (blind / out-of-band) |
|---|---|---|
| Cause | parser resolves external entities / DTD | the **same** |
| Channel | in-band — the value comes back in the response | out-of-band — the parser's request to a listener |
| What you observe | the file on the HTTP response | the hit arriving in the listener log |
| Fix | disable external-entity resolution and DTD loading | the **same** |

The one parser-config difference that opens the out-of-band channel is a single flag — `no_network` — covered in [`DIFF.md`](./DIFF.md).

## Lab structure — three containers

Like the SSRF out-of-band atom (`ssrf-blind-oob`), this is a multi-container lab. Three services come up under one `docker-compose.yml`:

- **`vulnerable`** — the broken importer, published on `127.0.0.1:8030`.
- **`fixed`** — the patched version, published on `127.0.0.1:8130`.
- **`oob-listener`** — a dumb out-of-band sink. It serves the attacker DTD and logs every request it receives. It is a **tripwire, not a target**: it holds no secret, and reaching it *at all* is the proof. It is **not** published to the host (no `ports:` entry); it is reachable only from inside the Docker networks the lab creates, and you observe it through `docker compose logs oob-listener`.

The `vulnerable` and `fixed` apps live on **separate** Docker networks; both share a network with `oob-listener`. So the listener is reachable from each app, but the apps cannot reach each other. This matters for the fix: `fixed` can still reach the listener at the network layer; when it produces **no** callback, that is the parser refusing to resolve the entity, not the network blocking it.

**Why embed a listener at all?** In a real engagement you would detect blind XXE with an external interaction server — Burp Collaborator, `interactsh`, a DNS/HTTP catcher you own on the internet. This lab is self-contained and isolated by design (`127.0.0.1` only), so it cannot depend on reaching a third party. The `oob-listener` is a self-hosted, air-gapped stand-in for that external sink — the "Collaborator" you would normally use, brought inside the lab. Every callback stays on your machine.

## The response is blind on purpose

The generic `{"status": "received"}` reveals nothing — no parsed value, no error. That blindness is the defining trait of the atom, not an accident: if the response leaked the resolved entity, this would be in-band XXE (`xxe-basic`). The response is **byte-identical** in the vulnerable and the fixed app, and for a benign document and the attack payload alike — so you cannot tell any of them apart from the response, which is precisely why you look out-of-band.

## Run

From the repo root:

```bash
./atom up xxe-blind-oob
```

- Vulnerable app: <http://127.0.0.1:8030/import> (`POST` XML)
- Fixed app: <http://127.0.0.1:8130/import> (`POST` XML)
- OOB listener: not published — reachable only through the vulnerable or fixed app, observed via `docker compose logs oob-listener`.

Stop with `./atom down xxe-blind-oob`. If you prefer raw Docker: `cd atoms/A05-security-misconfiguration/xxe-blind-oob && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite + logs (primary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Library note — why lxml, and why it is pinned

Python's standard-library XML parser (`xml.etree.ElementTree`) does **not** resolve external entities, so an atom built on it would not be vulnerable. This lab uses **`lxml`** (over `libxml2`), the popular third-party parser, which *can* — and whose exact behaviour is version-specific. The vulnerable app builds its parser with `resolve_entities=True, load_dtd=True, no_network=False`; the pinned `lxml==5.3.0` (libxml2 2.12.9) fetches the external DTD and fires the out-of-band request under that configuration. The behaviour was confirmed by running the pinned version, not assumed; if you bump `lxml`, re-check. See [`DIFF.md`](./DIFF.md) for the full reasoning, including why `defusedxml` is named but not used.

## Fixed version

The patched app on port 8130 serves the same endpoint and returns the **same** `{"status": "received"}` for every input — the response never changes. What changes is behind it: the parser is built with `resolve_entities=False, load_dtd=False`, so the external entity is never resolved and the attacker's DTD is never fetched. Replay the attack from `WALKTHROUGH.md` against it: the response is byte-identical to the vulnerable app's, but the `oob-listener` log shows **no** new hit — the callback never happens. The fix is at the **parser**, not the response and not the network: the listener is still reachable from `fixed`; the hardened parser simply never reaches for it. See [`DIFF.md`](./DIFF.md).
