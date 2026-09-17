# ssrf-cloud-metadata — Cloud metadata SSRF (IAM credential theft)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for the highest-impact SSRF target in the cloud. The app exposes a "Fetch from URL" feature — you submit a URL, the server fetches it, and hands you back the response body. The server never validates which URL it is asked to fetch, so the same feature that previews `https://api.github.com/zen` can be pointed at `http://169.254.169.254/` — the **cloud metadata endpoint** (the IMDS) that every AWS/GCP/Azure instance carries. A plain, unauthenticated `GET` there returns the instance's **IAM session credentials**, and the app echoes them straight back to you.

This is the third SSRF atom, and it closes the arc that `ssrf-basic` and `ssrf-blind-oob` opened. In `ssrf-basic` the server fetched your URL and handed you the body of a generic internal service; in `ssrf-blind-oob` the response told you nothing and you confirmed the request out-of-band. Here the mechanism is the same as `ssrf-basic` — fetch and show, in-band — but the *target* is the one that pays and the *impact* is credential theft. The escalation over `ssrf-basic` is not the visibility (both are in-band); it is the **target** (the metadata endpoint) and the **impact** (IAM credential theft leading to cloud account takeover). Same primitive, aimed at the crown jewel.

> **Theory primer:** Read [PortSwigger: Server-side request forgery (SSRF)](https://portswigger.net/web-security/ssrf)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

For the target side, AWS documents the service this atom mocks: [Use instance metadata to manage your EC2 instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html). The `iam/security-credentials/<role>` path returns the instance role's **temporary** security credentials, with no authentication — which is exactly what an SSRF into `169.254.169.254` walks off with.

## Lab structure — three containers

This is a multi-container atom, like the other two SSRF atoms. Three services come up under one `docker-compose.yml`:

- **`vulnerable`** — the broken "Fetch from URL" app, published on `127.0.0.1:8017`.
- **`fixed`** — the patched version, published on `127.0.0.1:8117`.
- **`metadata-mock`** — a fake IMDS answering at the **real link-local IP `169.254.169.254`** — the exact address the metadata service uses on a real AWS/GCP/Azure instance, so the payload you type is identical to the real one. It serves the minimal surface an SSRF attacker walks: the IAM role name, then the role's credentials as JSON. **The credentials are the AWS-documented `…EXAMPLE` placeholder values — obviously fake, no real secret.** It is **not** published to the host (no `ports:` entry); `curl http://169.254.169.254/` from your laptop will not reach it. It is reachable only from inside the Docker network the lab creates. There is no database; the only state is the mock's static, fake credentials.

**A note on the topology.** The other two SSRF atoms put their extra service on *two* Docker networks and reach it by DNS name. This atom instead pins the mock at the fixed IP `169.254.169.254` — because that exact IP *is* the lesson. A single address can only live in one subnet, so all three containers share **one** network here. What matters is preserved: the mock is reachable from **both** `vulnerable` and `fixed` at the network layer, so when the fixed app refuses, that refusal is its **application code** (the allowlist) — not the network — exactly as in `ssrf-basic`.

## Run

From the repo root:

```bash
./atom up ssrf-cloud-metadata
```

- Vulnerable app: <http://127.0.0.1:8017/>
- Fixed app: <http://127.0.0.1:8117/>
- Metadata mock: not published — reachable only through the vulnerable or fixed app, at `http://169.254.169.254/`.

Stop with `./atom down ssrf-cloud-metadata`. If you prefer raw Docker: `cd atoms/A10-ssrf/ssrf-cloud-metadata && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8117 validates the destination **before** fetching, against a deny-by-default allowlist of vetted hosts, matched on the parsed host (`urllib.parse.urlparse(...).hostname`), not a substring of the raw URL. Replay every payload from `WALKTHROUGH.md` against it: a legitimate `https://api.github.com/zen` still returns the same body as before, but every URL pointing at `http://169.254.169.254/…` returns **403 Forbidden** instead of fetching — no role name, no credentials. The `metadata-mock` container is still reachable from the `fixed` container at the network layer; the fix is in the application code, not the network plumbing. The fix is a **positive list**, not a blocklist of `169.254.0.0/16`: a blocklist loses to decimal/hex/IPv6-mapped IPs, userinfo tricks, redirects, and DNS rebinding, while an allowlist rejects anything unvetted. See [`DIFF.md`](./DIFF.md) for why, and for the note on IMDSv2 — the cloud-side hardening this atom describes but does not apply.
