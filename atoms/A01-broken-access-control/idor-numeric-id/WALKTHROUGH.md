# Walkthrough — idor-numeric-id

## 1. Context

The app exposes a small "private notes" feature. The home page tells you who you're logged in as and links you to your own note; clicking it sends `GET /notes/1` and the server renders the note body in a plain HTML block. Three users are seeded: alice (id 1), bob (id 2), carol (id 3). Each owns exactly one note, and the note IDs happen to match the owner IDs (1, 2, 3) — that's seed convenience, not a property the app relies on.

This is the first atom in the project that is **not input-driven**. In `sqli-union-basic` and `xss-reflected` you crafted a payload — a SQL fragment, an HTML tag — and the server mishandled it. There is no payload here. The "exploit" is changing one number in a URL from `1` to `2`. The vulnerability isn't in how the app *processes* input; it's in code the app *never wrote* — the missing check that the requested note actually belongs to you.

Get used to this shape. A large fraction of bug-bounty IDOR/BOLA findings are exactly this: the request is well-formed, the input is legitimate, the app obediently returns data the caller has no business reading.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/notes/<id>` view is short:

```python
@app.route("/notes/<int:note_id>")
def view_note(note_id):
    note = next((n for n in NOTES if n["id"] == note_id), None)
    if note is None:
        abort(404)
    # VULNERABLE: no ownership check — any caller can view any note by id.
    return render_template("note.html", note=note)
```

Read it twice. Nothing concatenates user input into a dangerous sink. There's no template filter doing something risky. The function looks up a note by primary key and returns it. The bug is **what isn't there**: no comparison between `note["owner_id"]` and the calling user's id. The function trusts that "if you asked for note N, you must be allowed to see note N" — and that assumption is exactly what an attacker breaks.

Two things to internalize from this shape:

- **`grep` for the keywords that exist in injection bugs (`f"`, `%s`, `|safe`, `Markup`, `eval`) won't find IDOR.** This class shows up as the *absence* of code, and absence doesn't grep. Audit by tracing requests: pick an endpoint that returns user-scoped data, ask "where is the ownership check", and if the answer is "nowhere", you have a finding.
- **The fix is a single explicit check on the server.** Not "use a UUID instead of an integer", not "rate-limit", not "remove the ID from the URL". Those are obfuscation. You'll see the UUID variant fail in atom 11 (`idor-uuid-guessable`). For now, hold the rule: **the server must verify, on every request, that the caller is allowed to access the requested object.**

## 3. How auth works in this lab

Real auth (login forms, session cookies, password hashing) is out of scope for an IDOR lab — it would triple the code size and teach a different lesson. The `session-fixation` atom (15) is the right place for the full ceremony.

Here we fake it with a single header: **`X-User-ID`**. Whatever integer the client sends, the app treats as "the logged-in user". If the header is absent, the app defaults to `1` so the UI is clickable without you setting anything up.

Two consequences worth holding in your head before you start exploiting:

- **The header is self-asserted.** Nothing prevents you from claiming to be user `2` or `99`. In a real app that would be a separate bug (broken authentication, atom 15) — but here we're not even pretending to verify identity. The "session" is whatever you say it is.
- **Whether the app *uses* that claimed identity for authorization is a different question.** The vulnerable version reads `X-User-ID` for the home page (so it can greet you by name) but ignores it inside `/notes/<id>`. That's the bug. Step 4 below makes the distinction concrete.

## 4. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8003/>, click **View my note**, then in **Proxy → HTTP history** find the `GET /notes/1` request and **Send to Repeater**.

The browser doesn't send `X-User-ID` on its own (it's not a standard header). The default in `app.py` makes the app behave as if you sent `X-User-ID: 1`. To make every request explicit and easy to vary in the steps below, **add the header manually in Repeater** the first time:

```
X-User-ID: 1
```

Now every request you send from this Repeater tab carries the header explicitly, and you can edit it like any other line.

Unlike SQL injection or XSS, **none of the steps below use URL encoding or special characters** — you're changing integers in a URL and an integer in a header. That's it. If you find yourself reaching for `%20` or backslashes here, you're overthinking the bug.

### Step 1 — Read your own note

Request line in Repeater:

```
GET /notes/1 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 1
```

Response: status 200, page renders alice's note ("Bank PIN: 4231"). The response also shows `Note id: 1 · Owner id: 1` so you can see who actually owns the record. This is your baseline — the legitimate request, exactly as the feature was designed.

### Step 2 — Read someone else's note

Change one character on the request line: `1` → `2`. Leave the header alone.

```
GET /notes/2 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 1
```

Response: status 200, page renders bob's note ("Confidential meeting Friday 2pm"). The response panel confirms `Owner id: 2` — you, claiming to be user 1, just read content owned by user 2. That's the IDOR. The server returned the data because nothing in the code path forbids it.

Pause here for a second. The request is *valid* by every protocol-level rule: well-formed line, valid path, valid integer, all headers in order. A WAF watching for "malicious input" sees nothing. Authentication "passed" (such as it is). Authorization was never consulted. This is why IDOR is so common in bug-bounty reports — the request looks fine.

### Step 3 — Confirm the pattern

```
GET /notes/3 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 1
```

Response: carol's note ("Credit card ending in 8821"). One more data point that the bug isn't specific to bob — it's universal. Any note id in the seed is reachable from any caller.

In a real engagement this is the step where you write up the finding: enumerate the range, capture three or four cross-user reads to establish the pattern, and stop. You don't need to read every note in the database to prove the bug — three is plenty.

### Step 4 — Prove the bug is "missing check", not "wrong identity"

Now keep the path on `/notes/1` (alice's note) and change *only the header* to claim a different user:

```
GET /notes/1 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 2
```

Response: status 200, alice's note again. Owner id: 1. **Nothing about the response changed when you became "bob".**

Sit with that for a moment. If the bug were "the app trusts the caller's claimed identity for authorization", then changing `X-User-ID` from `1` to `2` should change *something* — a different note, a different error, anything. It doesn't, because the `/notes/<id>` view never reads the header at all. There's nothing to spoof. The "fix" isn't "validate the header better"; the header was never part of the decision in the first place.

The bug is precisely: **the authorization decision is missing**, not "the authorization decision uses bad inputs". A correct server-side check (see section 6) reads the caller's id, compares it to `note["owner_id"]`, and rejects mismatches. Whether the caller is honest about their identity is then a separate concern (and a separate atom).

## 5. Exploitation via browser (secondary track, optional)

For steps 1–3, the same exploit works directly in the browser address bar — no Burp required:

1. <http://127.0.0.1:8003/notes/1>
2. <http://127.0.0.1:8003/notes/2>
3. <http://127.0.0.1:8003/notes/3>

The default `X-User-ID: 1` kicks in (because the browser sends no such header), so all three render as "alice viewing the note". This is the gentlest possible first-pass: it removes any doubt that the URL itself is the entire exploit.

Step 4 doesn't have a browser equivalent — browsers don't let you set arbitrary request headers from the address bar. That's why Burp is the primary track: it makes the *missing-check vs wrong-identity* distinction visible. In a real engagement, every IDOR you report should look like step 4, not just step 2 — replay the request under different "identities" and document that authorization is unaffected. That's how relevance to scope is proven.

## 6. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short, the fixed `/notes/<id>` view reads `X-User-ID` and compares it to `note["owner_id"]` before returning the note — if they don't match, the request is rejected with `403 Forbidden`:

```python
user_id = request.headers.get("X-User-ID", "1")
note = next((n for n in NOTES if n["id"] == note_id), None)
if note is None:
    abort(404)
if str(note["owner_id"]) != user_id:
    abort(403)
return render_template("note.html", note=note)
```

Replay every request from section 4 against <http://127.0.0.1:8103/>:

- Step 1 (`/notes/1` with `X-User-ID: 1`): 200, your note.
- Step 2 (`/notes/2` with `X-User-ID: 1`): **403 Forbidden**.
- Step 3 (`/notes/3` with `X-User-ID: 1`): **403 Forbidden**.
- Step 4 (`/notes/1` with `X-User-ID: 2`): **403 Forbidden**.

Note what the fix does *not* do: it doesn't change the IDs from integers to UUIDs, doesn't hide them from the URL, doesn't add a token, doesn't rate-limit. None of those are authorization — they're obfuscation. The only line that matters is the explicit comparison; everything else is theater.

## 7. Try it yourself

1. **Enumerate beyond the seed.** Try `GET /notes/4` against the vulnerable app (with any `X-User-ID`). What happens? Now `GET /notes/0` and `GET /notes/-1`. Get used to the response shapes — 200 vs 404 vs 403 — they're how you map an IDOR's blast radius without leaking real data.
2. **Argue why UUIDs wouldn't fix this.** Suppose the app rebuilt the seed with UUID IDs (`/notes/4f1a-...-9b3d`). Step 2 would no longer work by hand because you can't guess the next UUID. Does that mean the bug is fixed? Try to write the answer in two sentences before reading the next atom in this category (`idor-uuid-guessable`, atom 11) — the answer is "no", and the *why* is what makes that atom worth doing.
3. **What about a POST endpoint?** Imagine `POST /notes/<id>/delete` with the same missing check. Walk through what changes in your exploitation steps and what stays the same. (Hint: very little changes — the class of bug is method-agnostic. The Burp request changes verb, the impact changes from "read leak" to "data destruction", and that's it.)
