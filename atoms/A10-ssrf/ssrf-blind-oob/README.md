# ssrf-blind-oob — Blind SSRF (out-of-band)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for blind SSRF. The app is a "webhook tester": you register a URL and the server sends it a test ping — a background HTTP request fired as a side effect. The result of that request is never shown back to you. Whatever the server reaches, the response is always the same generic `Test ping sent.` The server never validates which URL it is asked to reach, so the same feature that pings a legitimate webhook can be pointed at any host the server's network can see — you just never get to read what comes back.

This is the second SSRF atom, and the sibling of `ssrf-basic`. There, the server fetched your URL **and handed you the response body** — you read an internal service directly, in-band. Here the response tells you nothing. That does **not** mean the SSRF is gone: the server still makes the request you asked for. It only means you have lost the channel to *read* the result. So how do you prove the request happened? You point the server at a listener you control and watch the callback arrive **out-of-band**. Blind does not mean absent; it means you confirm it elsewhere.

> **Theory primer:** Read [PortSwigger: Blind SSRF](https://portswigger.net/web-security/ssrf/blind)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Blind is not in-band — and it is not absent

Keep this straight, because it *is* the lesson. Blind SSRF is not a weaker SSRF; it is the **same** server-side request capability, minus the convenient echo. The request happening is the vulnerability. Whether the response reflects it is a *separate axis* — only how easy it is to confirm. `ssrf-basic` gave you both request and read; here you have the request and **no** read channel, so detection moves out-of-band. The beginner trap this atom isolates is "no output, so no SSRF" — false. You will make the server reach a destination you chose and prove it, without ever reading a byte of what it fetched.

## Lab structure — three containers

Like `ssrf-basic`, this is a multi-container lab. Three services come up under one `docker-compose.yml`:

- **`vulnerable`** — the broken webhook tester, published on `127.0.0.1:8016`.
- **`fixed`** — the patched version, published on `127.0.0.1:8116`.
- **`oob-listener`** — a dumb out-of-band sink. It logs every request it receives and returns `ok`. It is a **tripwire, not a target**: it holds no secret, and reaching it *at all* is the whole proof. It is **not** published to the host (no `ports:` entry); it is reachable only from inside the Docker networks the lab creates, and you observe it through `docker compose logs oob-listener`.

The `vulnerable` and `fixed` apps live on **separate** Docker networks; both share a network with `oob-listener`. So the listener is reachable from each app, but the apps cannot reach each other — the same isolation `ssrf-basic` uses. This matters for the fix: `fixed` can still reach the listener at the network layer; when it produces **no** callback, that is the application code refusing, not the network.

**Why embed a listener at all?** In a real engagement you would detect blind SSRF with an external interaction server — Burp Collaborator, `interactsh`, a DNS/HTTP catcher you own on the internet. This lab is self-contained and isolated by design (`127.0.0.1` only), so it cannot depend on reaching a third-party service. The `oob-listener` is a self-hosted, air-gapped stand-in for that external sink — the "Collaborator" you would normally use, brought inside the lab.

## The response is blind on purpose

The generic `Test ping sent.` reveals nothing about the fetch — no fetched body, no fetched status, no error. That blindness is the defining trait of the atom, not an accident: if the response leaked what it fetched, this would be in-band SSRF (`ssrf-basic`), not blind. The response is identical in the vulnerable **and** the fixed app — so you cannot tell them apart from the response, which is precisely why you look out-of-band.

One honest caveat: a *timing* side-channel is inherent to any blind SSRF — a reachable host answers fast, an unresponsive one stalls until the request times out. That is real, but it is coarse and noisy, and it is not the channel this atom teaches. The reliable proof here is the out-of-band callback in the listener log.

## Run

From the repo root:

```bash
./atom up ssrf-blind-oob
```

- Vulnerable app: <http://127.0.0.1:8016/>
- Fixed app: <http://127.0.0.1:8116/>
- OOB listener: not published — reachable only through the vulnerable or fixed app, observed via `docker compose logs oob-listener`.

Stop with `./atom down ssrf-blind-oob`. If you prefer raw Docker: `cd atoms/A10-ssrf/ssrf-blind-oob && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite + logs (primary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8116 serves the same feature and returns the **same** `Test ping sent.` for every input — the response never changes. What changes is behind it: before fetching, the fixed app validates the destination against a deny-by-default allowlist of vetted hosts, matched on the parsed host (not a substring of the raw URL). Replay the attack from `WALKTHROUGH.md` against it: the response is byte-identical to the vulnerable app's, but the `oob-listener` log shows **no** new hit — the request to the non-vetted destination was never sent. The fix is a **positive list**, not a blocklist of "bad" ranges: a blocklist of private IPs would stop you reaching an internal target but would not stop an out-of-band callback to an external host, so it would not stop *detection*; an allowlist rejects anything unvetted, internal or external. The control is in the application, not the network plumbing — the listener is still reachable from `fixed`; it just refuses to reach it.
