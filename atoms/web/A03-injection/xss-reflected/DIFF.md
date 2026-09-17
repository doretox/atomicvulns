# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/templates/search.html` and `fixed/templates/search.html`:

```diff
-<h1>Results for: {{ q|safe }}</h1>
+<h1>Results for: {{ q }}</h1>
```

The `app.py` files are identical in both versions — the bug lives entirely in the template.

## What changed

The `|safe` filter was removed from the `{{ q }}` expression. In Jinja, `|safe` marks a value as already-trusted HTML and tells the renderer to bypass autoescape. Without it, Jinja's default autoescape engages and encodes `<`, `>`, `&`, `'`, and `"` into their HTML entities (`&lt;`, `&gt;`, `&amp;`, `&#39;`, `&#34;`) before the value is written into the response.

## Why this fixes the bug

When autoescape is on and the value flows through a regular `{{ q }}` expression, every character that could *shift the HTML parse* becomes an entity. The attacker's `<script>alert(1)</script>` arrives at the browser as the literal string `&lt;script&gt;alert(1)&lt;/script&gt;` — visible to the user as text, invisible to the HTML parser as markup. Payloads that try to open a new tag, close an existing one, break out of an attribute, or invoke an event handler all lose their teeth at the template layer, regardless of the exact characters used.

## Contrast with `sqli-union-basic`

In `sqli-union-basic` the sink sits in `app.py`: the vulnerable line is the f-string that builds the SQL statement, and reviewing the view function alone is enough to spot it. In `xss-reflected` the source is still in `app.py` (the `request.args.get("q", ...)` call), but the sink is in `templates/search.html` (the `|safe`-marked expression). The source→sink path crosses files, which is the normal shape for web apps: any serious source-review in a Flask project has to read templates, not just view functions. A cheap high-signal first pass is `grep -rn '|safe' templates/` (plus `Markup(`, plus `autoescape=false`) — every hit is a candidate XSS sink.
