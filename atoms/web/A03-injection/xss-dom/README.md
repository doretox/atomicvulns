# xss-dom — DOM-based Cross-Site Scripting

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for DOM-based XSS. The page runs a client-side search: JavaScript already on the page reads the search term from the URL fragment (`location.hash`, the part after `#`) and writes it into the page with `innerHTML`. The fragment is never sent in the HTTP request, so the server hands back a clean, static page and never sees the term — the whole source→sink flow lives in the browser. A crafted fragment like `#q=<img src=x onerror=alert(document.domain)>` makes `innerHTML` parse the string as HTML and fire the `onerror` handler, running attacker JavaScript in the victim's browser. The fix is one client-side line: write the term with `textContent`, which never parses HTML.

> **Theory primer:** Read [PortSwigger: DOM-based cross-site scripting (XSS)](https://portswigger.net/web-security/cross-site-scripting/dom-based)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up xss-dom
```

- Vulnerable app: <http://127.0.0.1:8021/>
- Fixed app: <http://127.0.0.1:8121/>

Stop with `./atom down xss-dom`. If you prefer raw Docker: `cd atoms/A03-injection/xss-dom && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation. The browser plants the payload in the URL fragment and runs it; Burp Suite reads the vulnerable script off the served response and proves the fragment never reaches the server (both mandatory — the sink is client-side JavaScript, which Burp can't execute).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8121 serves the byte-identical page and reads the same fragment the same way — it only swaps the sink from `innerHTML` to `textContent`. Point your browser at it, navigate to any payload from `WALKTHROUGH.md`, and the term shows up as literal text (`<img src=x onerror=...>` printed on screen, angle brackets and all), nothing executes. Nothing on the server changes — the vulnerability and the fix live entirely in the client-side JavaScript. Same class as [`xss-reflected`](../xss-reflected/) and [`xss-stored`](../xss-stored/), and the same impact (JavaScript in the victim's browser); but there the sink is the server's HTML output and the fix escapes on the server, while here the sink is a client-side DOM write and the fix is client-side.
