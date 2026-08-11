# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in exactly two places — one added import and the line that builds the search filter. `GET /` (the warning banner), the LDAP connection and the service-account bind, the response handling, the `Dockerfile`, and `requirements.txt` are identical between the two versions, as are the shared `ldap/` image and its seed. (This atom is API-only — there are no templates.)

## The fix — escape the filter metacharacters

```diff
+from ldap3.utils.conv import escape_filter_chars
 ...
     user = body.get("user", "")
     password = body.get("password", "")
-    # VULNERABLE: user/password are concatenated straight into the LDAP search
-    # filter. ... the metacharacters * ( ) \ are syntax, not data ...
-    filt = f"(&(uid={user})(userPassword={password}))"
+    # FIXED: escape the RFC 4515 filter metacharacters in every untrusted value
+    # before building the filter. * ( ) \ become literal data (\2a \28 \29 \5c) ...
+    filt = f"(&(uid={escape_filter_chars(user)})(userPassword={escape_filter_chars(password)}))"
     print("LDAP search filter:", filt, flush=True)
     conn = Connection(server, BIND_DN, BIND_PW, auto_bind=True)
     conn.search(PEOPLE_DN, filt, search_scope=SUBTREE, attributes=["uid"])
```

The vulnerable view concatenates `user` and `password` straight into the filter string. The fixed view runs each value through `escape_filter_chars` first, which replaces the RFC 4515 metacharacters `*`, `(`, `)`, `\` (and NUL) with their escape sequences `\2a`, `\28`, `\29`, `\5c` before they reach the filter. A `*` sent as the password is then no longer the wildcard that turns `(userPassword=<value>)` into a presence test — it becomes the literal search `(userPassword=\2a)`, matching only an account whose password is literally the one-character string `*` (there is none), so the login is refused. The value is matched as a value again. It escapes **both** `user` and `password`: both are attacker-controlled and both land in the filter, so both are escaped at the point of use.

## Why this fixes the bug

An LDAP search filter is structure, and `ldap3` sends the filter string you hand it to the directory verbatim — it does not escape interpolated values for you. The vulnerable app builds the filter from raw input, so a metacharacter in the input becomes filter syntax. The fixed app guarantees every untrusted value is escaped before the filter is assembled, so the filter can only ever be the intended `(&(uid=<literal>)(userPassword=<literal>))` — two literal equality tests, with no room for a wildcard or a grafted-on clause. The benign case is unchanged: a real credential contains no metacharacters, so escaping is a no-op and it round-trips exactly as before. The root cause was never the character the attacker typed; it was concatenating untrusted input into the filter *as structure*, and escaping at the point of use is exactly its negation.

## Validating or blocklisting characters is not the fix

An experienced reader has a fix ready: "it's user input in a query — just restrict the characters, forbid `*` and parentheses in the `user` field." Whether you frame it as a blocklist of bad characters or an allowlist of good ones, it is the wrong shape. Policing the input's character set chases the form of the attack: alternate encodings, a metacharacter you forgot (`\`, NUL), a field that legitimately contains symbols, the next input you didn't think to filter. You stay one bypass behind, and you break real data that happens to contain a symbol.

Escaping is different in kind: it says "whatever this value contains, treat all of it as data," and it lives at the **point of use** — the moment the value is placed into the filter — so there is nothing to keep up to date and no legitimate input it rejects. Escape at the sink; don't try to sanitize the source. (Same shape as the "named, not applied" notes in `ssti-jinja` and `nosql-injection-mongo`: name the control the reader reaches for, and show why it is not the fix.)

## The honest design is a bind, not "the search matched"

One design note, because it is the tempting deeper fix and this atom deliberately leaves it alone. Deciding auth by *searching* `(&(uid=...)(userPassword=...))` and trusting that a match means a valid login is fragile on its own — it is what lets a filter trick become an auth bypass. Real LDAP authentication is a **bind**: the app connects to the directory *as the user's own DN* with the supplied password, and whether that bind succeeds *is* the password check. The injection in this atom — a metacharacter in the search filter — cannot produce a bypass against a bind, because the directory verifies the password itself instead of counting search hits.

So why keep the fragile design and only escape? Because switching to a bind changes the *design*, not the *vulnerability*. This atom isolates one flaw — untrusted input concatenated into a filter — and its minimal negation is to escape that input. Rewriting the login to bind would fix the injection only as a side effect of replacing the whole mechanism, which is exactly the kind of change that blurs what the lesson is. Name the better design; keep the diff to the cause. (Same spirit as the "hashing is orthogonal" note in `nosql-injection-mongo`.)

## Same class as the Mongo NoSQL injection — opposite fix

The finding is an authentication bypass: a crafted login as `admin` without the password, which is account takeover. That is the same ceiling as an auth bypass through SQL injection or NoSQL injection — and this atom is worth holding next to `nosql-injection-mongo` (22), because they are alike in impact and category and *nothing else*.

| Axis | SQL injection (`sqli-union-basic`) | NoSQL injection (`nosql-injection-mongo`) | LDAP injection (this atom) |
|---|---|---|---|
| Category | A03 — Injection | A03 — Injection | A03 — Injection |
| Query language | SQL — a string of commands | a MongoDB query — a JSON document | an LDAP search filter — a string (RFC 4515) |
| How input becomes structure | syntax spliced into a string (`' OR 1=1 --`) | type change: a string becomes an object carrying an operator (`{"$ne": null}`) | metacharacters in a concatenated filter string (`*` `(` `)` `\`) |
| The fix | parameterize (bind variables) | force the type (reject non-strings) | escape the RFC 4515 metacharacters |
| Is escaping the input the fix? | — | **no** — nothing to escape; the injection was a *type* | **yes** — the value carried filter *syntax* |

Read that last row across. In the Mongo atom, escaping is precisely *not* the fix: the injection was a value that changed type into an operator, there was no string to escape, and the fix was to force the type. Here the injection is a metacharacter inside a string the app concatenated, so escaping is *exactly* the fix. Same class — untrusted input becoming query structure in a query language that isn't SQL — but *how* the input becomes structure decides the remedy, and the remedy that missed in 22 is the one that lands here. "One atom, one vulnerability" is about the cause, not the impact: `sqli-union-basic`, `nosql-injection-mongo`, and this atom can all end in a subverted query and a bypassed login, by three different roots.
