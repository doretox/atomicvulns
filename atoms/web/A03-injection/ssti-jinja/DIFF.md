# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py`. The only change is how the `name` enters the `GET /greet` render (comments abbreviated):

```diff
 @app.route("/greet")
 def greet():
     name = request.args.get("name", "world")
-    # VULNERABLE: the name is concatenated INTO the template source with an f-string ...
+    # FIXED: the name is passed as DATA via the name= variable, never concatenated in ...
     return render_template_string(
         "<!doctype html><title>Greeting</title>"
         "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
-        f"<h1>Hello, {name}!</h1>"                        # name is IN the template source -> SSTI
-        '<p><a href="/">&larr; Back</a></p>'
+        "<h1>Hello, {{ name }}!</h1>"                     # {{ name }} placeholder filled from data
+        '<p><a href="/">&larr; Back</a></p>',
+        name=name,                                        # name passed as DATA, never sewn in
     )
```

Everything else is byte-for-byte identical between the two versions: the imports, the `SECRET_KEY` config line, the `GET /` view, the static skeleton of the greeting (doctype, banner, back link), `__main__`, the `Dockerfile`, `requirements.txt`, and `templates/index.html`. The bug lives entirely in that one render call.

## What changed

`render_template_string` is called in both versions — the function is the same. The difference is its argument. The vulnerable version builds the `<h1>` with an **f-string** (`f"<h1>Hello, {name}!</h1>"`), so Python pastes the `name` into the template *source* before Jinja2 compiles it. The fixed version uses a **placeholder** (`"<h1>Hello, {{ name }}!</h1>"`) and passes the value separately (`name=name`), so the `name` reaches Jinja2 as *data*, not as part of the template text. This is a *logic-different* fix isolated to one line — the smallest possible expression of "where the input goes is the whole bug".

## Why this fixes the bug

The class is: attacker input becomes part of the template source, so the engine compiles and evaluates any `{{ ... }}` expression the attacker writes. `{{7*7}}` evaluates to `49`; `{{config}}` renders Flask's config object, which includes the `SECRET_KEY`. When the name is passed as data instead, Jinja2 substitutes it into the `{{ name }}` slot as a literal value — HTML-escaping it and never re-parsing it as template code. So `{{7*7}}` comes back as the literal text `{{7*7}}`, and `{{config}}` never reads the config. The benign `Ada` renders identically either way; only the evaluation is gone.

## The cause is *where the input goes*, not "using Jinja2"

Every Flask app renders Jinja2 templates — that is not the bug. The bug is that the vulnerable version puts untrusted input into the template *source* (as code) rather than passing it as data. The proof of isolation is direct: send `name=Ada` to both apps and both return exactly `Hello, Ada!` — the greeting logic is identical. Only when the name carries a `{{ ... }}` expression do they diverge: the vulnerable app evaluates it, the fixed app returns it literal. Nothing in the route logic differs; the entire difference is that one render call.

## Input as code vs. input as data

The two versions call the **same function**, so this atom is not "`render_template_string` is dangerous, use something else". `render_template_string` is safe when the template is a fixed string and the user value is passed as a keyword argument — which is exactly the fixed version. The dangerous move is *composing the template out of the input*: an f-string (or `"..." + name`, or `.format(name)`) makes the input part of the source, and the engine then treats it as code. Keeping user input out of the template text — passing it as data through a `{{ placeholder }}` — is the durable rule. Escaping or blocklisting `{{`/`}}` in the input is the losing game SQL injection taught: filters get bypassed. The only fix is structural: never splice user input into template source.

## A sandbox is not the fix

Jinja2 ships a `SandboxedEnvironment` that tries to *contain* what a rendered expression can reach (blocking access to some attributes and builtins). It comes up as a way to "make SSTI safe", but it is a weaker, historically bypassed defense — sandbox escapes are a recurring theme, and hardening one is a moving target. This atom deliberately does not use it: the real fix is to not inject in the first place (input as data), not to let the injection happen and try to fence it in. `SandboxedEnvironment` is named here, not applied.

## The impact is disclosure; RCE is a different bug

This atom stops at the second rung of the SSTI ladder: `{{7*7}}` confirms evaluation, `{{config}}` discloses the `SECRET_KEY`. That key signs Flask's session cookies, so leaking it lets an attacker forge sessions — disclosure with a path to account takeover, not remote code execution. SSTI as a *class* can escalate from expression evaluation to command execution through Python's object hierarchy, but that is a separate finding and this atom does not build it. The `SECRET_KEY` here (`dev-secret-CHANGEME-not-a-real-secret`) is an obviously fake lab placeholder set identically in both apps — so the fixed app not leaking it is attributable to the input being data (never evaluated), not to the key being absent.

## Sewing input into the source also reflects raw HTML

Because the vulnerable version makes the name part of the template *text*, a name like `<b>x</b>` is emitted as raw markup (it renders bold) — that is reflected cross-site scripting (XSS), a different class from the template evaluation this atom teaches (`xss-reflected` covers reflected XSS directly). Both share one root cause — input sewn into the source — so the fix closes both at once: passing the name as data means Jinja2 autoescapes it (`<b>` becomes `&lt;b&gt;`) *and* never evaluates it. This atom's lesson is the evaluation (SSTI); the raw-HTML reflection is noted here, not pursued.
