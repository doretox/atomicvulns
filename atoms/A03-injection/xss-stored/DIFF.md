# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/templates/index.html` and `fixed/templates/index.html`:

```diff
-<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
+<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body }}</li>
```

The `app.py` files are identical in both versions — the bug lives entirely in the template, the same shape as `xss-reflected`.

## What changed

The `|safe` filter was removed from the `{{ comment.body }}` expression. In Jinja, `|safe` marks a value as already-trusted HTML and tells the renderer to skip autoescape. Without it, Jinja's default autoescape engages and encodes `<`, `>`, `&`, `'`, and `"` into their HTML entities (`&lt;`, `&gt;`, `&amp;`, `&#39;`, `&#34;`) before the value is written into the response. `author` and `created_at` next to it were already escaped (no `|safe`) and are unchanged — the body was the only sink, so the fix is the only `|safe` in the file.

## Why this fixes the bug

A comment is stored verbatim — the parameterized `INSERT` was never the problem — and the danger is purely in how it is rendered back. With autoescape on, the stored `<script>alert(document.domain)</script>` reaches every visitor's browser as the literal string `&lt;script&gt;alert(document.domain)&lt;/script&gt;`: visible to the reader as text, inert to the HTML parser as markup. The cookie-exfil payload from Step 3 lands as text too — no `fetch` runs, the listener stays silent. Payloads that try to open a tag, close one, break out of an attribute, or wire up an event handler all lose their teeth at the template, whatever exact characters they use.

## Same fix as `xss-reflected`, reformulated

This is the same one-line change as [`xss-reflected`](../xss-reflected/DIFF.md): a `|safe`-marked expression loses the filter and falls back to Jinja's autoescape. Same sink, same defense, same class. The audit reflex is identical: `grep -rn '|safe' templates/` (plus `Markup(` and `{% autoescape false %}`) surfaces every spot where escaping has been turned off, and each hit is a candidate XSS sink. If you internalized the reflected fix, you already know this one.

## Same fix, bigger blast radius

It is tempting to file stored XSS as "reflected, but worse." Mechanically it is the *same* bug — unescaped output — with a *different delivery*, and that is exactly why the fix is the same: the root cause is identical. But the delivery is what makes stored more dangerous, and the one-line fix removes that same root cause in a far larger setting:

- **Reflected** needs the victim to click an attacker-crafted link carrying the payload in the URL — that is social engineering, and it hits one victim per click.
- **Stored** needs the victim to do nothing but visit a page they already trust. The payload is persisted server-side and re-served to *every* visitor, *every* time, until someone deletes it — no link, no lure, no attacker present.

The same line of code closes both. The lesson rhymes with the SQLi trilogy's "one root cause, one fix, N exploits": here it is one root cause (unescaped output), one fix (autoescape), two delivery models (reflected and stored).

## A note on HttpOnly — defense-in-depth, not the fix

The app sets the session cookie without the `HttpOnly` flag, in *both* versions. You might expect the fixed app to add it — and it deliberately does not. Two reasons:

- **It is not the fix.** Marking the cookie `HttpOnly` would stop `document.cookie` from reading it, which would defeat the *specific* cookie-theft payload in Step 3 even if the XSS were still present. But the XSS would still be there: the attacker could deface the page, make authenticated requests as the victim, log keystrokes, or read the DOM. `HttpOnly` shrinks the blast radius of one payload; it does not close the hole. The hole is closed by escaping the output.
- **One variable at a time.** Keeping exactly one difference between `vulnerable/` and `fixed/` (the `|safe`) makes it unambiguous which change closes the XSS. Adding `HttpOnly` to the fixed version as well would blur that.

`HttpOnly` is still worth setting in real applications — a valuable second layer that limits the damage if an XSS ever slips through. It just belongs in the "defense-in-depth" column, next to a Content-Security-Policy, not in the "this is the fix" column. The fix is, and remains, escaping untrusted data on output.
