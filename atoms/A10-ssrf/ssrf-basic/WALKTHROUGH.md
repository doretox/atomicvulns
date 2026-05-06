# Walkthrough — ssrf-basic

## 1. Context

The app exposes a "URL preview" feature. You paste a URL on `/`, the form submits a `GET /fetch?url=<url>` request, and the server uses the `requests` library to fetch that URL and renders the response body back to you inside a `<pre>` block. It's the same pattern Slack, Discord, GitHub, and most chat apps use when you share a link — the server-side preview generator.

The default value in the form is `https://api.github.com/zen`, which is a real, public endpoint that returns a single short line of plain text (a Zen of GitHub quote) — perfect for confirming the feature works before you start changing the URL into something interesting.

## 2. About this lab's environment

There's a third container in this atom besides `vulnerable/` and `fixed/`: **`internal/`**. It is a fake "corporate admin dashboard" that returns a page full of obviously-private-looking data — API keys, a database connection string, a JWT signing key, and a small users table. None of that data is real; the whole service exists only to stand in for "an internal service the attacker shouldn't be able to see".

What matters for the exploitation is *how it is reachable*:

- **No port mapping.** Look at [`docker-compose.yml`](./docker-compose.yml) — `vulnerable` and `fixed` each publish a port to `127.0.0.1` on your host, but `internal` has no `ports:` line at all. `curl http://localhost/` from your host will not reach it; opening it in your browser will not reach it.
- **Same Docker network as `vulnerable` (and as `fixed`, separately).** Inside the Docker network the lab creates, `internal` is reachable at the hostname `internal` on port 80. The `vulnerable` container, also on that network, can resolve `internal` by name and `requests.get("http://internal/")` will succeed from inside it.

That asymmetry is the entire premise of the lab. You, attacking from your host, can't talk to `internal`. The vulnerable app, sitting one network hop closer, can. The exploit will be: get the app to do that talk on your behalf, and hand you the response.

In a real engagement this maps directly to a corporate VPC, a Kubernetes pod network, or an EC2 instance with reach into a private subnet. You're outside; the SSRF target is inside; the vulnerable app is the bridge.

## 3. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/fetch` view is short:

```python
@app.route("/fetch")
def fetch():
    url = request.args.get("url", "")
    if not url:
        return render_template("index.html")
    # VULNERABLE: server-side request to attacker-controlled URL, no allowlist.
    try:
        response = requests.get(url, timeout=5)
        content, status = response.text, response.status_code
    except requests.RequestException as exc:
        content, status = f"Request error: {exc}", None
    return render_template("preview.html", url=url, content=content, status=status)
```

The query parameter `url` flows straight into `requests.get(url, ...)`. There is no parsing, no allowlist, no scheme check, no DNS resolution check, no host check. Whatever URL the client sends, the server fetches.

> ### Server-side: a new threat shape
>
> **Stop and re-read this section after the exploit, even if it makes sense now.** It's the most important conceptual step in the atom.
>
> In `sqli-union-basic`, `xss-reflected`, and `idor-numeric-id`, the attacker's payload was processed *locally by the app*: a SQL fragment that the app executed against its database, an HTML tag that the app rendered into its own response, an integer that the app looked up in its own data. The app ran one program, on one machine.
>
> SSRF moves the locus of action *out of the app's process* and onto the **network the server is sitting on**. The attacker's payload is now a *URL*, and the server is the one making an outbound HTTP request *to that URL*. Three concrete consequences flow from this:
>
> 1. **Reach.** The attacker's reach equals the server's reach. Anything the server's network sees — internal services, cloud metadata endpoints, neighboring containers, databases bound to localhost — is now within the attacker's reach. Network segmentation that was protecting these targets from the public internet was never protecting them from the app you've compromised.
> 2. **Identity.** The outbound request comes from the *server*, not from you. Egress firewalls that allow the server to reach internal hosts let your request through. AWS IAM roles attached to the EC2 instance authenticate the server's request to the metadata service — and now to your request. Whatever credentials the server implicitly carries become yours, for the duration of one fetched URL.
> 3. **Visibility to defense.** A WAF watching ingress sees a clean `GET /fetch?url=...` with no malicious payload. The actual "attack" is the *outbound* request the server then makes. Tooling that only watches the ingress path misses SSRF entirely; tooling that watches egress sees a request to a private IP from a service that has no business making that request.
>
> Holding onto these three points changes how you read code. In a code review, every `requests.get(...)`, `urllib.urlopen(...)`, image loader, webhook caller, OAuth callback, PDF/screenshot generator, and SSO redirect handler is a candidate SSRF sink — and the question is "does the URL this thing fetches come, even partially, from someone who isn't the server itself?"

## 4. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8004/>, click **Preview** with the default `https://api.github.com/zen` URL once to capture the traffic, then right-click the `GET /fetch?url=...` request in **Proxy → HTTP history** and choose **Send to Repeater**.

### A note on URL encoding

Same parser rule as the previous atoms: the HTTP request line is `METHOD SP URI SP VERSION`, so any **literal space inside the URI breaks the request** with `400 Bad Request`. Encode every space as `%20`. The other characters in URLs you'll send here (`:`, `/`, `?`, `=`, `.`) are all legal in a query string per RFC 3986 and travel fine as-is.

The URLs in this lab don't contain spaces, so for once you barely need to think about encoding. If you want a no-thinking option, paste the decoded URL into Repeater, select the value of `url=`, press **Ctrl+U**, and Burp will percent-encode anything that needs it (`/` → `%2F`, `:` → `%3A`, etc.). Both forms hit the app as the same string after URL-decoding.

### Step 1 — Confirm the feature works

Payload:

```
url=https://api.github.com/zen
```

Request line in Repeater:

```
GET /fetch?url=https://api.github.com/zen HTTP/1.1
Host: 127.0.0.1:8004
```

Response: status `200`, the `<pre>` block contains a single short line of plain text — a Zen of GitHub quote like `Approachable is better than simple.` (the actual quote varies between requests). The `HTTP status` field on the page reads `200`. This is your baseline — the legitimate use of the feature, exactly as designed. Note one quiet but important detail: **Burp shows the response as if your browser fetched `https://api.github.com/zen`, but your browser didn't. The server did, and forwarded the body back to you.** Sit with that — it's the entire mechanism of SSRF in one round-trip.

### Step 2 — Pivot to the internal network

Now change the URL to `http://internal/`. That's a hostname your laptop can't resolve and a host your laptop can't reach. The vulnerable app's container, however, sits on a Docker network where `internal` is a real DNS name pointing at the third container.

Payload:

```
url=http://internal/
```

Request line in Repeater:

```
GET /fetch?url=http://internal/ HTTP/1.1
Host: 127.0.0.1:8004
```

Response: status `200`. The `<pre>` block now contains the internal admin dashboard — including the `API_KEY_PROD`, `DATABASE_URL`, and other obviously private-looking values. **You just read the contents of a host that, from your laptop's perspective, doesn't exist.** The vulnerable app crossed the network boundary on your behalf and handed back what it found.

Note: the internal service responds in `text/plain`. Internal corporate endpoints often do — think `/metrics`, `/health`, config dumps. The leak is the same; the format just makes it more legible in raw HTTP tools like Burp.

Confirm the asymmetry by hand: in another terminal, run `curl http://localhost/` or `curl http://internal/` from your host. Neither resolves; the internal service is invisible to you directly. The only path to it is through the SSRF.

### Step 3 — Enumerate further inside

The dashboard page links to `/users`. Repeat with the deeper path:

Payload:

```
url=http://internal/users
```

Request line in Repeater:

```
GET /fetch?url=http://internal/users HTTP/1.1
Host: 127.0.0.1:8004
```

Response: the internal users table (id, name, email, role) for three fake employees. Same mechanism as step 2, different endpoint. The point: once you have SSRF reach into a host, you don't get just one page — you get the whole HTTP surface of that host. In a real internal service that often means admin endpoints with no authentication (because "the only callers are inside the network"), Prometheus/metrics endpoints leaking infrastructure detail, undocumented `/debug` routes, and so on. Map the surface the same way you would on any other web target — only now the target is something you weren't supposed to be able to reach.

### What you've just demonstrated, in one sentence

A request that looks, at the ingress layer, like `GET /fetch?url=...` with no payload of any kind, caused the server to read internal data and return it to you. Nothing in the request was "malicious" in the SQLi/XSS sense. The whole exploit lives in *which URL* the server agreed to fetch.

## 5. Exploitation via browser (secondary track, optional)

The same three URLs pasted directly into the browser address bar:

1. <http://127.0.0.1:8004/fetch?url=https://api.github.com/zen>
2. <http://127.0.0.1:8004/fetch?url=http://internal/>
3. <http://127.0.0.1:8004/fetch?url=http://internal/users>

The browser URL-encodes the inner `://` and `/` characters (or doesn't — most modern browsers leave them readable in the address bar) and the rendered page shows the fetched response inside a `<pre>` block. This is the gentlest first-pass: the URL bar by itself proves that you can read internal-only content through the vulnerable app.

Switch to Burp for everything after the first feel — the Repeater workflow makes it much faster to iterate on URLs and to inspect raw response bytes (which matters when the internal service returns binary, JSON, or unusual content types that the browser would try to render rather than display).

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short, the fixed `/fetch` view parses the URL with `urllib.parse.urlparse`, then rejects anything whose scheme isn't `https` or whose hostname isn't in a small allowlist (`api.github.com`, `wikipedia.org`):

```python
parsed = urlparse(url)
if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
    abort(403)
response = requests.get(url, timeout=5)
```

Replay every URL from section 4 against <http://127.0.0.1:8104/fetch>:

- Step 1 (`https://api.github.com/zen`): 200, quote returned as before.
- Step 2 (`http://internal/`): **403 Forbidden**. (Two reasons: `http` isn't `https`, and `internal` isn't in the allowlist. Either alone would block it.)
- Step 3 (`http://internal/users`): **403 Forbidden**, same reason.

Notice what the fix does *not* do. It doesn't disconnect the `fixed` container from the network where `internal` lives — they're still on the same Docker network and the OS-level reachability is unchanged. It doesn't add a network policy, a firewall rule, or a sidecar proxy. The `fixed` container could in principle still reach `internal`; it just refuses to. The control is in the application, not in the plumbing. That's the right place for it: in production you do want defense-in-depth network segmentation, but you cannot rely on it to compensate for an application that will fetch arbitrary URLs on demand.

The fix is also deliberately a **positive list**, not a negative one. A blocklist version would try to keep up with `internal`, `localhost`, `127.*`, `169.254.*`, RFC 1918 ranges, IPv6 loopback, alternative IPv4 representations, DNS rebinding, redirect-following, and more — and lose to the next bypass anyway. Atom 16 (`ssrf-blind-oob`) walks through several of those bypasses on a more realistic blocklist defense; for now, hold the rule that allowlists win because they are finite.

## 7. Try it yourself

1. **Try a few "almost-allowed" hostnames against the fixed app.** Send `?url=https://api.github.com.evil.tld/`, `?url=https://API.GITHUB.com/`, `?url=https://api.github.com@internal/`. For each one, predict whether it will be blocked and why before you press Send. The point of the exercise is not to find a bypass (the allowlist as written holds) but to internalize *which* part of the URL parser the check ran on. Look up `urlparse(...).hostname` behavior for each and see whether your prediction matches.
2. **Probe the host's loopback through the vulnerable app.** Try `?url=http://127.0.0.1:5000/` against the vulnerable app. What you'll get is the vulnerable app talking to *itself* on its container's loopback — interesting because it shows that "the server's loopback" is now part of the attacker's reach (in real life this is how attackers reach admin interfaces and metrics endpoints bound to localhost-only). Try `?url=http://127.0.0.1:5000/fetch?url=http://internal/` and reason about what happens (hint: the inner `?` and `=` matter; URL-encode them as `%3F` and `%3D` if you want the inner request to survive parsing).
3. **Stage the cloud-metadata variant in your head.** AWS EC2 instances expose a metadata service at `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` that returns temporary IAM credentials to anything inside the instance. If this app were running on EC2, what would `?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/` return through the vulnerable endpoint, and what would an attacker do with the response? Atom 17 (`ssrf-cloud-metadata`) makes this concrete on a real-shaped metadata mock; for now, the point is just to see why SSRF is rated as high-impact in cloud environments without you needing the actual cloud setup in front of you.
