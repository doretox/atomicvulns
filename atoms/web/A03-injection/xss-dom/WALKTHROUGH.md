# Walkthrough — xss-dom

The page runs a search entirely in the browser. You put a term in the URL fragment — `#q=...`, the part of a URL after the `#` — and a small script already on the page reads it and writes `You searched for: <term>` onto the page. The term never leaves the browser: the fragment is the one part of a URL that the browser does **not** send in the HTTP request. So the server returns the same static page every time and never sees what you searched for; the term enters the page only afterward, when the page's own JavaScript reads the fragment and drops it into the document with `innerHTML`. `innerHTML` asks the browser to *parse* that string as HTML — including any event handler it carries. Put an `<img src=x onerror=...>` in the fragment and the browser builds the element, the image fails to load, the `onerror` fires, and your JavaScript runs.

## 1. Context

`GET /` serves a one-field search page. There is no search endpoint on the server: you type a term (or edit the URL) and the result is rendered client-side. This is **DOM-based XSS**, an injection bug (OWASP **A03 — Injection**) — cross-site scripting where the whole path from attacker-controlled input to the dangerous operation runs in the browser's own JavaScript, never touching the server. Two terms name the ends of that path: the **source** is where the untrusted input comes from (here `location.hash`, the URL fragment), and the **sink** is the dangerous operation it flows into (here `innerHTML`, which parses HTML). The **fragment** — everything after `#` in a URL — is the crux: browsers keep it client-side and never place it in the HTTP request, so the server is blind to it.

No database, no second service: the `vulnerable` app is on `127.0.0.1:8021`, the `fixed` app on `127.0.0.1:8121`. Because the sink is client-side JavaScript, the browser is where you exploit and observe; Burp is a second lens that reads the delivered script and proves, on the wire, that your payload never reaches the server.

## 2. Spot the bug

Open [`vulnerable/templates/index.html`](./vulnerable/templates/index.html). The whole bug is the inline script:

```javascript
function render() {
  var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
  document.getElementById("result").innerHTML = "You searched for: " + q;
}
window.addEventListener("hashchange", render);
render();
```

`q` is read straight from `location.hash` — the URL fragment, which you control — and concatenated into `...result").innerHTML`. Audit question: *my input flows into `innerHTML`, which parses its string as HTML and runs any event handler in it?* — yes. That is the sink. `render()` runs on load and again on every `hashchange`, so editing the fragment re-renders. Note what is **not** here: [`vulnerable/app.py`](./vulnerable/app.py) just calls `render_template("index.html")` with no data — the server never receives, stores, or renders the search term. Source and sink are both in the browser. (The fix, foreshadowed: send the term to a sink that writes text instead of parsing HTML.)

The cheap first-pass grep for this class is a DOM sink fed from the URL:

```bash
grep -rn 'innerHTML\|document.write\|location.hash' .
```

## 3. Exploitation (in the browser)

The sink is client-side JavaScript, so the exploit runs in a browser — Burp cannot execute JavaScript. Open the vulnerable app with your browser proxied through Burp (that captures the traffic for Section 4), but the payload goes in the URL, not through a Burp request.

### Baseline — the feature

Navigate to `http://127.0.0.1:8021/#q=laptop`. The page renders:

```html
<p id="result">You searched for: laptop</p>
```

`laptop` came from the fragment and the page's script rendered it. Ordinary search behavior.

### Build the payload — an event handler, not `<script>`

The obvious payload — `<script>alert(document.domain)</script>` — does **not** work here, and understanding why is half the lesson. When you assign to `innerHTML` after load, the browser parses the string and builds the DOM, but by HTML rule it does **not** execute a `<script>` inserted that way. (Try `#q=<script>alert(1)</script>`: nothing happens, and if you inspect the result element the `<script>` is sitting there in the DOM — parsed and inserted, never run. The `xss-reflected` and `xss-stored` atoms each noted in passing that this exact payload would "silently do nothing" in DOM-based XSS — this is that atom.) You need JavaScript that runs **without** a script tag: an element with an inline event handler. The classic is an image with a broken source:

```
<img src=x onerror=alert(document.domain)>
```

The browser builds the `<img>`, tries to load `src=x`, fails, and fires `onerror` — running your code.

### Fire it

Navigate to:

```
http://127.0.0.1:8021/#q=<img src=x onerror=alert(document.domain)>
```

An alert box pops up showing `127.0.0.1` — `document.domain`, the origin the script runs in. Your JavaScript executed inside the app's page. Look at what `innerHTML` did to the DOM — the result paragraph now holds a real image element, not text:

```html
<p id="result">You searched for: <img src="x" onerror="alert(document.domain)"></p>
```

That is exactly why the handler ran: the string was *parsed into an element*, not written as characters. Anything the page can do in the browser — read cookies on this origin, make requests as the logged-in user, rewrite the DOM, exfiltrate the page — this script can now do too.

The alert is benign: a dialog box, nothing read or sent, nothing leaving the browser, in an isolated local lab. On a real target this is real XSS; keep payloads demonstrative (an `alert`), never a keylogger or a live exfiltration.

## 4. What Burp shows — and what it doesn't

DOM XSS is driven from the browser, but Burp is not idle — it proves the defining fact of the class. In **Proxy → HTTP history**:

**The vulnerable sink ships in the response.** Find the `GET /` request and read its response body: the inline `<script>` with `innerHTML = "You searched for: " + q` is right there, delivered verbatim to the browser. The server ships the vulnerable code — it just never runs it.

**Your payload is never in a request.** This is the key one. After navigating to `/#q=<img src=x onerror=alert(document.domain)>`, look at every request Burp captured. The request line is:

```
GET / HTTP/1.1
```

Not `GET /#q=<img...>`, not `GET /?q=<img...>` — just `GET /`. The fragment is **gone**: the browser stripped it before sending. The server's own log agrees —

```
"GET / HTTP/1.1" 200 -
```

— no fragment, no payload. That absence *is* the proof that this is DOM-based, not reflected or stored: there is no request carrying your payload for the server to reflect or store, and (in practice) none for Burp to intercept and tamper with. The payload lived and ran entirely in the browser. It is also why the real-world exploit is a crafted **link**, not a crafted request: the attacker sends the victim a URL with the payload in the fragment.

## 5. What the vuln is NOT

Same `alert`, same class as the other XSS atoms — so isolate what is actually different:

- **NOT reflected XSS.** In `xss-reflected` the server takes `?q=...` from the request and echoes it into the HTML it renders — the payload is in the request, and the *server's* response carries it back. Here the response is a fixed static page that echoes nothing, because your term (in the fragment) never reached the server. Section 4 showed it: the request was a bare `GET /`.
- **NOT stored XSS.** Nothing is persisted. There is no database, and the payload does not survive a reload unless it is back in the fragment. It lives only in the URL you are on.
- **NOT a server-side escaping bug.** This is the trap. The reflex is "it's XSS — escape the output, turn on Jinja autoescape, add a CSP." None of that reaches this bug, because the dangerous data never passes through the server: the page Jinja rendered is clean and static, and Jinja never sees the fragment. The defense has to live where the data is *used* — in the client-side JavaScript.

What it **is**: client-side JavaScript reads a source you control (`location.hash`) and passes it to a sink that parses HTML (`innerHTML`). The only fix is a sink that writes text instead — on the client.

## 6. Impact

**Cross-site scripting: arbitrary JavaScript in the victim's browser, under the page's origin.** The attacker delivers a link — `http://target/#q=<payload>` — and anyone who opens it runs the attacker's script in that page's context: stealing session cookies, making authenticated requests as the victim, reading or rewriting the DOM, exfiltrating page contents. Same ceiling as `xss-reflected` and `xss-stored` (JavaScript in the victim's browser), reached by a different cause — a client-side DOM sink instead of the server's HTML output. No overclaim: this runs in the victim's browser, not on the server; the server here is never even touched.

## 7. Why the fix works

Point the browser at the fixed app on **8121** and repeat the exploit with the *same* URL, `http://127.0.0.1:8121/#q=<img src=x onerror=alert(document.domain)>`. No alert. The page renders:

```html
<p id="result">You searched for: &lt;img src=x onerror=alert(document.domain)&gt;</p>
```

The payload is printed on screen as literal text — angle brackets and all — not built into an element. See [`DIFF.md`](./DIFF.md) for the one-line change: the fixed script reads the same fragment the same way and only swaps the sink, `innerHTML` → `textContent`. `textContent` writes the string as characters and never parses it as HTML, so there is no `<img>`, no `onerror`, nothing to run. The benign search is unchanged — `#q=laptop` renders `You searched for: laptop` on both apps — and the fix is exactly one thing: the client-side sink. Nothing on the server changed, because nothing on the server was ever the problem.
