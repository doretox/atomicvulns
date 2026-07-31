# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in exactly one place — how `POST /profile` chooses which fields to write onto the account (comments abbreviated):

```diff
 account = {"name": "Demo User", "email": "demo@example.com", "role": "user"}

+# The SERVER decides which fields a profile update may set (allowlist of fields).
+ALLOWED_FIELDS = {"name", "email"}
+

 @app.route("/profile", methods=["POST"])
 def update_profile():
     data = request.get_json(silent=True) or {}
-    # VULNERABLE: copy EVERY field from the client's JSON straight into the account ...
-    account.update(data)
+    # FIXED: allowlist of FIELDS -- only name/email are copied; role and anything else ignored ...
+    for field in ALLOWED_FIELDS:
+        if field in data:
+            account[field] = data[field]
     return jsonify(account)
```

Everything else is byte-for-byte identical between the two versions: the imports, the seeded `account`, `GET /profile`, `GET /admin`, `__main__`, the `Dockerfile`, and `requirements.txt` (there are no templates — this atom is API-only). The bug — and the fix — live entirely in how `POST /profile` selects fields.

## What changed

The vulnerable version does `account.update(data)` — it merges the entire parsed JSON (`data`, whatever the client sent) into the account dict, so *every* key becomes an attribute. The fixed version introduces `ALLOWED_FIELDS = {"name", "email"}` and copies only those: `for field in ALLOWED_FIELDS: if field in data: account[field] = data[field]`. That is a *logic-different* fix — the blind merge is replaced by an explicit, server-defined field selection. The `request.get_json(silent=True) or {}` line is unchanged; what changed is what the code does with the parsed body.

## Why this fixes the bug

`ALLOWED_FIELDS` is an allowlist of the attributes the user is permitted to set. The loop walks the *allowlist*, not the input, so a key the client sends that isn't on the list is never touched — it cannot reach the account at all. `name` and `email` update as before; `role`, `is_admin`, or anything else in the JSON is silently ignored. The server, not the client, now decides which attributes a profile update may write. That is the whole repair: the class is "the app binds request fields onto an object without choosing which the user may set," and the allowlist is exactly its negation.

The `if field in data` guard keeps the feature's partial-update behavior: a field absent from the JSON is left at its current value, so a request that sends only `name` updates only `name`. Proof of isolation: send the legitimate `{"name", "email"}` update to both apps and both return the same account; only the extra `role` field diverges — the vulnerable app writes it, the fixed app drops it. Accepting a JSON profile update was never the bug; letting the client decide which fields it sets was.

## Allowlist of fields, not a blocklist of field names

The tempting quick fix is to inspect the input for the dangerous key — "if the JSON has `role`, delete it" or "reject the request when `role` is present." That is a blocklist, and it loses. A short tour of why:

- **You must remember every dangerous field, forever.** `role` is the obvious one, but the same account object might carry `is_admin`, `is_staff`, `verified`, `email_verified`, `credits`, `balance`, `owner` — miss one and it stays writable.
- **Every field added to the model later is a new hole.** A blocklist doesn't know about the `is_superuser` someone adds next sprint; it silently starts letting it through. An allowlist ignores it for free — anything not named is dropped by default.
- **Variations slip past a naive key check:** nesting (`{"account": {"role": "admin"}}`), alternate spellings, casing.

The durable fix is structural. Instead of asking "does the input contain a dangerous field?", ask "is this field one the user is allowed to set?" — enumerate the *permitted* fields (`name`, `email`) and copy only those. Everything off the list is dropped, including fields that don't exist yet. The blocklist is named here to show why it fails; it is **not** applied.

This is the same allowlist-vs-blocklist lesson as `open-redirect`, the other A01 atom where the server must decide rather than trust the input. There the server decides the redirect *destination* (accept only an internal path; don't blocklist `http://`); here it decides the writable *fields* (accept only `name`/`email`; don't blocklist `role`). Same shape — enumerate what is allowed, don't chase what is forbidden — a different surface.

## Mass assignment is most famous in ORMs

This atom models mass assignment with a bare `dict.update()` so the bug is one visible line. In the wild it is most notorious one layer down, in ORM-backed frameworks. An **ORM** (Object-Relational Mapping — a library that maps an object's attributes to database columns) often offers a convenience that builds or updates a record straight from the request parameters — `Model(**params)`, `record.update(params)`, a `create(request.POST)`. When the whole parameter bag is passed in, an extra key like `role` or `is_admin` becomes a written *column*, persisted to the database — the classic "autobinding" bug behind a number of well-known advisories. The mechanism is identical to what you see here (the code trusts the *shape* of the input and binds it wholesale onto an object), and so is the fix: an allowlist of settable attributes, which frameworks package as "strong parameters," "permitted attributes," or "fillable/guarded" lists. This atom uses a plain dict and no ORM on purpose — the same lesson, with nothing between you and the one bad line. The ORM is described here, not introduced.

## Impact: vertical privilege escalation

The impact is **vertical privilege escalation**: a normal `user` becomes an `admin`, and the admin-only `GET /admin` opens (`403` → `200`). That is the honest ceiling — **not RCE, not a server takeover**; you gained an application role, not code execution. Two contrasts place it within A01:

- **vs `open-redirect`** (the other "the server decides" A01 atom): both hand the server a decision the client had usurped, and both fix it with a server-side allowlist. There the input controls the redirect *destination*; here it controls which *fields* get written. Same lesson, different surface.
- **vs IDOR / BOLA** (`idor-numeric-id`, `idor-uuid-guessable`, `bola-rest`): those are *horizontal* — you read *another* user's object because an ownership check is missing. This is *vertical* — you write *your own* object with a field that grants privilege, because field selection is missing. Different axis of the same A01 category: there the absent control is "is this object yours?"; here it is "is this field yours to set?".

In real systems the same one-line flaw writes whatever sensitive attribute the object carries — `is_admin`, `verified`, `credits`, the `owner` of a record — which is why mass assignment is its own entry in the OWASP API Security Top 10. This atom proves the role escalation; those wider writes are the class's reach, described not built.
