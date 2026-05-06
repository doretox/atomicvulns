# ssrf-basic — Server-Side Request Forgery (basic)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic SSRF. The app exposes a "URL preview" feature — paste a URL, the server fetches it, and you get the response body back, like a chat app showing a preview when you share a link. The server never validates which URL it is asked to fetch, so the same feature an attacker uses to preview `https://api.github.com/zen` also works to reach `http://internal/` — a host on a private Docker network that the attacker can't touch directly.

This is the first atom in the project where the **server itself** is the one making the outbound request. In `sqli-union-basic`, `xss-reflected`, and `idor-numeric-id` the attacker sent a payload that the app processed locally. In SSRF the attacker sends a *URL*, and the app turns around and makes an HTTP request *to that URL* on its own. The threat shape changes: now the attacker's reach equals the server's reach — internal services, cloud metadata endpoints, anything the server's network can see.

> **Theory primer:** Read [PortSwigger: Server-side request forgery (SSRF)](https://portswigger.net/web-security/ssrf)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Lab structure — three containers

This is also the first multi-container atom. Three services come up under one `docker-compose.yml`:

- **`vulnerable`** — the broken URL preview app, published on `127.0.0.1:8004`.
- **`fixed`** — the patched version, published on `127.0.0.1:8104`.
- **`internal`** — a fake "corporate admin dashboard" returning made-up API keys, database URLs, and a small users table. **It is part of this lab, not a real system.** It is intentionally not published to the host (no `ports:` entry); it can only be reached from inside the Docker networks the lab creates. Trying to open it directly from your browser (e.g. `curl http://localhost`) will not work — that's the whole point. The `internal` service is the target of the SSRF; reaching it through the vulnerable app is what the walkthrough demonstrates.

The `vulnerable` and `fixed` apps live on **separate** Docker networks; both share the network with `internal`. So `internal` is reachable from each app, but the apps cannot reach each other — keeps the lesson clean.

## Run

From the repo root:

```bash
./atom up ssrf-basic
```

- Vulnerable app: <http://127.0.0.1:8004/>
- Fixed app: <http://127.0.0.1:8104/>
- Internal service: not published — only reachable through the vulnerable or fixed app.

Stop with `./atom down ssrf-basic`. If you prefer raw Docker: `cd atoms/A10-ssrf/ssrf-basic && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary) and browser (secondary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8104 enforces an explicit allowlist of hosts (`api.github.com`, `wikipedia.org`) and requires `https`. Replay every payload from `WALKTHROUGH.md` against it: the legitimate preview of `https://api.github.com/zen` returns the same content as before, but every URL pointing at `http://internal/` (or any other host) returns **403 Forbidden** instead of fetching the resource. The `internal` container is still reachable from the `fixed` container at the network layer — the fix is in the application code, not in the network plumbing.
