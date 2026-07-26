# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/templates/index.html` and `fixed/templates/index.html`:

```diff
 // The fragment is never sent to the server -- source = location.hash.
-// VULNERABLE sink: innerHTML parses the string as HTML and fires embedded event
-// handlers (e.g. <img src=x onerror=...>), so a crafted fragment runs attacker JS.
+// FIXED sink: textContent writes the string as literal text; the browser never
+// parses it as HTML, so <img src=x onerror=...> shows up as inert characters.
 function render() {
   var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
-  document.getElementById("result").innerHTML = "You searched for: " + q;
+  document.getElementById("result").textContent = "You searched for: " + q;
 }
```

One property assignment changes: `innerHTML` → `textContent`. Everything else is byte-for-byte identical between the two versions — the `app.py`, the rest of `index.html` (the form, the `<script>` structure, the `render()` logic, the `hashchange` listener), the `Dockerfile`, and `requirements.txt`. The bug lives entirely in that one client-side sink.

## What changed

The vulnerable page writes the search term into the page with `element.innerHTML`; the fixed page writes it with `element.textContent`. Both read the same source the same way — `new URLSearchParams(location.hash.slice(1)).get("q")` — and both build the same string, `"You searched for: " + q`. The only difference is which DOM property receives it.

## Why this fixes the bug

`innerHTML` and `textContent` differ in one decisive way: what they do with markup in the string.

- **`innerHTML`** treats its string as **HTML source**. The browser parses it, builds the DOM it describes, and wires up any event handlers it finds. Feed it `<img src=x onerror=alert(document.domain)>` and you get a real `<img>` element whose `onerror` runs — attacker JavaScript, executed.
- **`textContent`** treats its string as **literal text**. The browser makes a single text node and shows the characters as-is; it never parses them as HTML. The same `<img src=x onerror=...>` becomes the visible text `&lt;img src=x onerror=...&gt;` on screen — no element, no handler, nothing to run.

Swapping the sink removes the parse step, and with it every markup-based payload at once — a broken image, an `<svg onload>`, a tag that breaks out of context — regardless of the exact characters used. The benign case is untouched: `#q=laptop` renders `You searched for: laptop` either way.

## Nothing changes on the server

Look at what is *not* in this diff: `app.py`. The two apps run byte-identical server code — a single route that returns `render_template("index.html")` with no data. **The server does not participate in this vulnerability at all: it never receives the payload and it never renders it.** The malicious term lives in the URL fragment, which the browser never sends; the server hands back the same static page whether the fragment is benign, malicious, or absent. The cause and the fix both live 100% in the client-side JavaScript.

This is worth stating plainly, because it is different from the other two XSS atoms. In `xss-reflected` and `xss-stored` the `app.py` files are also identical and the bug is also "in the template" — but there the server still *holds the source*: it receives the `?q=` query or the `POST` body, and the sink is a Jinja expression the server evaluates while rendering. Here the server never sees the input, and the sink is JavaScript the server emits verbatim and never runs. The proof is direct — send `#q=laptop` to both apps and both render `You searched for: laptop`; only a markup payload separates them, and only in the browser.

## Escaping on the server is not the fix

The instinct for any XSS is "escape the output" — turn on Jinja's autoescape, HTML-escape the value, add a Content-Security-Policy (CSP) header. For a *reflected* or *stored* bug that is exactly right, because the server renders the tainted data. Here it reaches nothing:

- The payload arrives through `location.hash`, which **never leaves the browser**. Jinja renders a page that never contained the search term, so there is nothing for it to escape. Autoescape is already on in this app — and it is irrelevant, because no user input flows through a server-side template variable.
- A server can only defend data it can see, and this data it cannot see. The defense has to sit where the data is actually *used* — the client-side sink — which is exactly what swapping to `textContent` does.

A CSP is still worth having as **defense-in-depth**: a strict policy can blunt what an XSS achieves even if one slips through. But it is not the root fix (and a loose policy would not stop an inline `onerror` at all). The root fix is to stop handing attacker-controlled data to a sink that parses HTML.

## `textContent` writes data; `innerHTML` builds behavior

The deeper lesson is the one that separates data from code everywhere: `textContent` writes **data** — the exact characters, inert — while `innerHTML` asks the browser to **build and run behavior** out of those characters (elements, and the event handlers attached to them). The fix picks the API that cannot execute.

If a real feature genuinely needs to render user-supplied *HTML* (a rich-text comment, say), the answer is not `innerHTML` on raw input but a dedicated HTML sanitizer — DOMPurify, for example — that strips dangerous markup before it reaches the DOM. This lab does not need that: a search result is plain text, so the fix is simply `textContent`, with no dependency added. Sanitizing is the tool for "must render HTML"; `textContent` is the tool for "only ever needs text," and choosing text when text is all you need is the smaller, safer move.

## The impact is XSS — same ceiling as reflected and stored, different cause

The payload runs arbitrary JavaScript in the page's origin, in the victim's browser: session-cookie theft, authenticated requests as the victim, DOM rewriting, page exfiltration. That is the same ceiling as [`xss-reflected`](../xss-reflected/) and [`xss-stored`](../xss-stored/) — all three are cross-site scripting, and all three run attacker JavaScript in the victim's browser. What differs is the cause and where the fix lives: reflected and stored are the server writing tainted data into its HTML output (fixed by escaping on the server); this is client-side JavaScript writing tainted data into a DOM sink (fixed on the client). Same class, same impact, different bug — which is why it is its own atom, with its own fix.
