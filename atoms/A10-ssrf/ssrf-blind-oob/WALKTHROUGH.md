# Walkthrough — ssrf-blind-oob

You are going to make the server reach a host of your choosing and **prove** it did — without ever reading a single byte of what it fetched. In `ssrf-basic` the server handed you the response and you read an internal service directly. Here the server tells you nothing: every request gets the same `Test ping sent.` back. That is not the SSRF being absent; it is the SSRF being **blind**. You will confirm it out-of-band, by watching a callback land on a listener you control.

There is one actor in this atom: you, the pentester, probing the endpoint. The primary track is Burp Repeater (to fire the request) plus `docker compose logs` (to catch the callback).

## 1. Context

The app is a "webhook tester". On `/` there is a form with a URL field; submitting it sends `POST /ping`, and the server fires a background `GET` at that URL as a side effect — the way an app "sends a test event to your webhook". The response is always the same:

```
Test ping sent.
```

No fetched body, no status, no error — nothing about what the server actually reached. That is the whole point: this feature is **blind**.

## 2. About this lab's environment

Three containers come up together (see [`docker-compose.yml`](./docker-compose.yml)):

- `vulnerable` (published on `127.0.0.1:8016`) and `fixed` (`127.0.0.1:8116`) — the webhook tester, broken and patched.
- `oob-listener` — a dumb **out-of-band sink**. It logs every request it receives and returns `ok`. It is a **tripwire, not a target**: it holds no secret. It is **not** published to the host — no `ports:` entry — so `curl http://oob-listener/` from your laptop will not reach it. It is reachable only from inside the Docker networks, at the hostname `oob-listener` on port 80.

`vulnerable` and `fixed` sit on **separate** Docker networks; both share a network with `oob-listener`. So each app can reach the listener, but the apps cannot reach each other. You observe the listener through its logs:

```bash
docker compose logs oob-listener
```

The listener records the source IP of each hit (`from=...`), which lets you tell a callback from `vulnerable` apart from one from `fixed`.

**Why is the listener here at all?** In a real engagement you would use an external interaction server — Burp Collaborator, `interactsh`, a catcher you own on the internet. This lab is self-contained and bound to `127.0.0.1`, so it cannot depend on reaching a third party. The `oob-listener` is a self-hosted, air-gapped stand-in for that external sink. Everything you do against it, you would do against Collaborator in the field.

## 3. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/ping` view is short:

```python
@app.route("/ping", methods=["POST"])
def ping():
    url = request.form.get("url", "")
    # VULNERABLE: fire a server-side request to an attacker-controlled URL and reveal nothing ...
    try:
        requests.get(url, timeout=5)  # server-side request to the attacker-chosen destination
    except Exception:
        pass  # swallow everything: surfacing the error would leak an in-band oracle
    return "Test ping sent."  # generic: says nothing about whether or what was fetched
```

The form value `url` flows straight into `requests.get(url, ...)`. No parsing, no allowlist, no host check — whatever URL you send, the server fetches. Two audit questions:

- *Does the server make a request to a destination I choose?* — **yes**. That is the SSRF.
- *Can I read the result?* — **no**. The response is a fixed string; the exception is swallowed. That is what makes it **blind**.

Both answers matter, and they are independent. The first is the vulnerability; the second is only how hard it is to confirm.

## 4. Exploitation via Burp Suite + logs (primary track)

Point your browser at Burp, visit <http://127.0.0.1:8016/>, submit the form once to capture the traffic, then right-click the `POST /ping` request in **Proxy → HTTP history** and **Send to Repeater**.

### A note on encoding

The form body is `application/x-www-form-urlencoded`, so `&`, `=`, `+`, and spaces inside the value must be percent-encoded (a literal space breaks the request; `&` would start a new field). The URLs in this lab contain none of those — `http://oob-listener/proof-ssrf-16` travels fine as-is. If you want a no-thinking option, select the value in Repeater and press **Ctrl+U** to URL-encode it.

### Step 1 — Baseline: meet the blindness

Send the default value first. Body:

```
url=https://hooks.example.com/webhook-test
```

Response: `200 OK`, body `Test ping sent.` The webhook host does not resolve inside the lab, so the fetch failed — but you cannot tell. The response you would get if it had *succeeded* is identical. **Sit with that: the response cannot distinguish success from failure. That is blind SSRF, and it is the reason the rest of this walkthrough lives in the logs, not in the response.**

### Step 2 — Fire the payload

Now point the server at the listener. Body:

```
url=http://oob-listener/proof-ssrf-16
```

Request in Repeater:

```
POST /ping HTTP/1.1
Host: 127.0.0.1:8016
Content-Type: application/x-www-form-urlencoded
Content-Length: 37

url=http://oob-listener/proof-ssrf-16
```

Response:

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 15
Connection: close

Test ping sent.
```

The response is, once again, `Test ping sent.` — byte-for-byte the same as the baseline. Burp shows you **nothing** about whether the server reached the listener. If you stopped here, you could not claim the SSRF fired. So don't stop here.

The `/proof-ssrf-16` path is a fixed, recognizable marker: you chose it, so when it turns up in the listener's log you know *this* request put it there.

### Step 3 — Confirm out-of-band (the proof)

Read the listener's log:

```bash
docker compose logs oob-listener
```

```
oob-listener-1  | INFO:app:OOB HIT path=/proof-ssrf-16 from=192.168.32.2
oob-listener-1  | INFO:werkzeug:192.168.32.2 - - [22/Jul/2026 18:40:24] "GET /proof-ssrf-16 HTTP/1.1" 200 -
```

There it is. The server made the request you asked for — to a host your laptop cannot even reach — and the callback landed on your listener. `from=192.168.32.2` is the `vulnerable` container's address on the shared network (yours will differ; check `docker inspect`), so you know the vulnerable app made this hit, not something else. **This is the confirmation the response body could not give you.** The baseline in Step 1 produced no such line — it never reached the listener — so the single `/proof-ssrf-16` hit is unambiguously yours.

That is the entire blind-SSRF skill: prove the request happened when you cannot see its result.

**A note on DNS.** This lab uses an HTTP callback because it is simple and self-contained. In the field, the out-of-band signal is often a **DNS** pingback rather than HTTP: egress filtering may stop the server from opening an outbound HTTP connection, but it can almost always still *resolve a name*, and that lookup reaches your interaction server. Same idea — a request escaping to a sink you control — over a channel more likely to survive filtering. Burp Collaborator and `interactsh` catch both.

## 5. What the vuln is NOT

Because the exploit produces no visible loot, it is easy to draw the wrong lesson. Nail down what this is *not*:

- **Not "no output, so no SSRF."** The response revealed nothing, yet the SSRF is real — the log proves it. Blindness is not absence. This is the misconception the atom exists to kill.
- **Not "the generic response is a defense."** The response is generic *on purpose* (it is blind), and the server still made the request. Hiding the output does not stop the SSRF; it only removes your in-band confirmation.
- **Not in-band SSRF.** In `ssrf-basic` you *read* the fetched resource in the response; here you *detect* the callback out-of-band. Same server-side request primitive, different (absent) read channel.
- **What it *is*:** the server issues a request to a destination **you choose** (`http://oob-listener/...`), and you prove it out-of-band. The only fix that addresses this is validating the destination — not hiding the response, which is already hidden.

## 6. Impact

Blind SSRF means the server can be coerced into making arbitrary outbound requests to destinations the attacker picks, without the attacker seeing the response. On its own, that is what this atom demonstrates: **detection of the primitive** — proof that the server will reach out on your command.

The listener here is a tripwire, not a prize; it holds nothing to steal. This atom stops at the primitive — the confirmed callback, proof that the server made a request you chose. That is the honest ceiling: it is not RCE, and nothing here should be over-claimed beyond "I made the server reach a destination I picked, and I proved it out-of-band".

## 7. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed `/ping` view validates the destination against a deny-by-default allowlist *before* fetching, matched on the parsed host:

```python
parsed = urlparse(url)
if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:
    try:
        requests.get(url, timeout=5)
    except Exception:
        pass
return "Test ping sent."
```

Replay Step 2 against <http://127.0.0.1:8116/ping>:

```
POST /ping HTTP/1.1
Host: 127.0.0.1:8116
Content-Type: application/x-www-form-urlencoded
Content-Length: 37

url=http://oob-listener/proof-ssrf-16
```

Response: `200 OK`, body `Test ping sent.` — **byte-identical to the vulnerable app's response.** Now read the log:

```bash
docker compose logs oob-listener
```

There is **no new hit** from the fixed container (no line `from=<fixed-ip>`). The destination `http://oob-listener/...` is not on the allowlist (and is not `https`), so the request was never sent. The response is the same in both apps; the only observable difference is the callback that does not happen. In blind SSRF, that is exactly how you confirm the fix — the same way you confirmed the bug: out-of-band.

Two things worth checking, because they are the point of the fix:

- **It is an allowlist, not a blocklist.** A blocklist of private IP ranges would stop you reaching an internal target — but it would *not* stop an out-of-band callback to an external host, so it would not stop detection. An allowlist rejects everything unvetted, internal or external. (In this air-gapped lab the sink happens to be internal, so a blocklist would incidentally block it too — but that is a lab artifact, not a property you can rely on in the field. See [`DIFF.md`](./DIFF.md).)
- **It decides on the parsed host, not a substring.** `https://hooks.example.com@oob-listener/` looks like it contains the allowed host, but `urlparse(...).hostname` is `oob-listener` — the part after the `@` — so it is rejected. Decimal-IP forms (`http://2130706433/`), suffix tricks (`http://hooks.example.com.evil.test/`), and explicit ports (`http://oob-listener:80/`) all fail the same way: the host the HTTP client would actually connect to is not on the list.

The control lives in the application, not the network — `fixed` can still reach `oob-listener` at the network layer; it simply refuses to.
