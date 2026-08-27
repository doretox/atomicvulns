# cors-wildcard — Cross-origin resource sharing (CORS) misconfiguration

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal lab for a mistake that is everywhere in APIs: a **CORS** policy that hands the response to *any* site, with the victim's cookies attached. The victim origin is a tiny JSON API — log in, get a session cookie, and `GET /account` returns your private account data as long as you hold the cookie. That endpoint is correct: it requires the cookie and returns the data to the person it belongs to. The flaw is a response *policy* wrapped around it.

To see why that matters you need one browser rule. An **origin** is the triple scheme + host + port (`http://victim.localhost:8034`). The **Same-Origin Policy (SOP)** is the rule that lets a script on one origin *send* a request to another origin but forbids it from *reading* the response — it is what stops a script on `evil.com` from calling `bank.com` (where you are logged in) and reading your account page. **CORS (Cross-Origin Resource Sharing)** is how a server can relax that on purpose, by response headers: `Access-Control-Allow-Origin` names which origin may read the response, and `Access-Control-Allow-Credentials: true` adds "…including when the request carried the victim's cookies." These headers are an *instruction to the browser*, not a lock on the server — the server always returns the body; CORS only tells the browser whether to hand that body to the calling script.

This victim gets the policy wrong in the most common way: it reads the request's `Origin` header and **reflects it straight back** into `Access-Control-Allow-Origin`, together with `Access-Control-Allow-Credentials: true`. So it answers "yes, you may read this, with the victim's cookies" to *whatever origin asks* — including the attacker's. A victim who is logged in and then visits the attacker's page has their browser make a **credentialed** cross-origin `fetch` (`credentials: 'include'`) to `/account`; the browser attaches the victim's cookie, the server replies with the reflected policy, and the browser hands the private response to the attacker's script. Cross-origin data theft, and the attacker never knew the password or touched the cookie.

The slug says "wildcard," but the literal `Access-Control-Allow-Origin: *` is a red herring here: the browser **refuses** to expose a credentialed response when the header is `*`, so `*` leaks only public data. The vector that reaches *authenticated* data is **origin reflection** — echoing a specific origin, which the browser *does* accept together with credentials. So the fix is not "reflect one origin" (reflecting *is* the bug) and not the wildcard — it is an **exact-match allowlist** of origins you actually trust (or no CORS headers at all, if the endpoint has no cross-origin consumer).

> **Theory primer:** Read [PortSwigger: Cross-origin resource sharing (CORS)](https://portswigger.net/web-security/cors)
> before working through this atom — it covers reflecting the `Origin` header into
> `Access-Control-Allow-Origin` and the role of `Access-Control-Allow-Credentials`,
> which is exactly this flaw. The atoms in this repo show *how* a vulnerability
> happens in code; the Academy explains *what* it is and why it matters.

This atom sits in **A05 — Security Misconfiguration**, alongside its siblings [`xxe-basic`](../xxe-basic/), [`xxe-blind-oob`](../xxe-blind-oob/), and [`debug-enabled`](../debug-enabled/). The contrast is the point: the XXE atoms are a misconfigured *XML parser* and `debug-enabled` is a misconfigured *framework/deployment*; this is a misconfigured *HTTP response policy*. And it is the mirror image of [`csrf-basic`](../../A01-broken-access-control/csrf-basic/): both break the Same-Origin Policy at the origin boundary, but in opposite directions. CSRF breaks the **send** side — it makes the victim's browser *fire* a state-changing request the attacker cannot read (a blind write). This breaks the **read** side — it lets the attacker *read* an authenticated response the SOP should have hidden (exfiltration). Send versus read: the two halves of the SOP.

## Stack note — two origins, browser-driven, no server-to-server link

Two origins, three services: the **victim** (a `vulnerable` and a `fixed` copy) and the **attacker** page. They never talk to each other on the backend — the victim's browser makes every cross-origin request — so there is no internal network, no `depends_on`, and no healthcheck. Distinct hostnames give genuinely distinct origins: the victim is `victim.localhost` (`:8034` vulnerable, `:8134` fixed) and the attacker is `attacker.localhost` (`:8234`). All of them resolve to `127.0.0.1` (browsers map `*.localhost` to loopback), so the Docker bindings stay on `127.0.0.1` — local-only — while the browser still sees three separate sites. The victim's session cookie is `SameSite=None; Secure` so the browser attaches it on the attacker's credentialed cross-origin fetch; `Secure` works over plain HTTP because `*.localhost` is a *secure context* (loopback). `vulnerable` and `fixed` share the `victim.localhost` host, so they use distinct cookie names (`session_vuln` / `session_fixed`) to keep their logins apart, since cookies ignore the port — plumbing, not a security difference.

## The browser is the proof — and `curl` is not

You drive this atom from a **browser** (with Burp as a supporting lens), because CORS is enforced by the *browser*, not the server. Point `curl` or Burp Repeater at `/account` and you will read the private body every time — even on the fixed app — because they are not browsers and simply ignore the CORS headers. That is not the exploit; it is only the **tell**. Burp is still useful: send `/account` with an `Origin:` header and you will see the vulnerable app *reflect* it back with `Access-Control-Allow-Credentials: true` — the signature of the misconfiguration. But the impact — a script on another origin actually *reading* the victim's data — only reproduces in a real browser, which is where the walkthrough runs it.

## Run

From the repo root:

```bash
./atom up cors-wildcard
```

- Vulnerable victim API: `http://victim.localhost:8034` (bound to `127.0.0.1:8034`)
- Fixed victim API: `http://victim.localhost:8134` (bound to `127.0.0.1:8134`)
- Attacker page: `http://attacker.localhost:8234` (bound to `127.0.0.1:8234`)

Use the `*.localhost` hostnames in the browser (not the bare `127.0.0.1` ports) — the distinct hostnames are what make the origins cross-origin. Stop with `./atom down cors-wildcard`. If you prefer raw Docker: `cd atoms/A05-security-misconfiguration/cors-wildcard && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step by step: log in as the victim, see the vulnerable app reflect the attacker's origin in Burp, then open the attacker page in the browser and watch its script read the victim's private account data cross-origin. Then the same page against the fixed app is blocked by the browser with a CORS error.
2. [`DIFF.md`](./DIFF.md) — the one-policy diff between `vulnerable/` and `fixed/`, and why "check the Origin ends with our domain," "just drop credentials," and "use `*`" are not the fix.

## Fixed version

The patched API on port 8134 replaces origin reflection with an **exact-match allowlist**: it echoes `Access-Control-Allow-Origin` only when the request's `Origin` is exactly one of the origins it trusts (a stand-in legitimate partner). An untrusted origin — the attacker's — gets no CORS header at all, so the browser blocks the cross-origin read and the attacker's script sees a CORS error, not the data. `GET /account` still returns the same data to the logged-in victim, and the request still reaches the server with the cookie attached — the browser simply refuses to hand the response to a script from an origin the server did not allow. See [`DIFF.md`](./DIFF.md) for why the fix is an allowlist rather than reflecting a "specific" origin, dropping credentials, or the wildcard.
