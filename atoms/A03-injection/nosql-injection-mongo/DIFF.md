# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in exactly one place — the `login` route — and the change is a single type guard. `GET /` (the warning banner), the imports, the MongoDB connection, the `Dockerfile`, and `requirements.txt` are identical between the two versions, as are the shared `mongo/` image and its seed. (This atom is API-only — there are no templates.)

## The fix — force the type

```diff
 @app.route("/login", methods=["POST"])
 def login():
     body = request.get_json(silent=True) or {}
     username = body.get("username")
     password = body.get("password")
-    # VULNERABLE: username/password go straight into the query filter. A MongoDB
-    # query is a DOCUMENT, not a string. If password arrives as an object like
-    # {"$ne": null} instead of a string, it becomes a Mongo OPERATOR ("not equal"),
-    # so the filter matches any user with a password and the login succeeds without
-    # it. The input didn't inject syntax into a string -- it changed the value's type.
+    # FIXED: force the type -- username and password must be strings. An object
+    # carrying an operator (e.g. {"$ne": null}) is rejected before it can reach the
+    # query filter, so it can never become query structure.
+    if not isinstance(username, str) or not isinstance(password, str):
+        return jsonify({"error": "username and password must be strings"}), 400
     user = users.find_one({"username": username, "password": password})
     if user:
         return jsonify({"authenticated": True, "user": user["username"]})
     return jsonify({"authenticated": False}), 401
```

The fixed view refuses any `username` or `password` that isn't a string. An object — the only thing that can carry a Mongo operator — is rejected with `400` before the query runs, so it can never become query structure. That single guard closes the injection: the class is "untrusted input reaches a query filter as an operator," and forcing the value to a scalar is exactly its negation.

The fix **rejects** rather than coerces. `str(password)` would also stop the operator — the object would become the harmless string `"{'$ne': None}"` — but it would silently accept a malformed request and paper over the attacker's intent. Rejecting says "this field must be a string" and stops there; it is the honest fix.

## Why this fixes the bug

A MongoDB query is a document, and `pymongo` sends whatever `dict` you hand it to the server as that document. The vulnerable app builds the filter from raw input, so an attacker who sends an object instead of a string gets that object placed into the query *as an operator*. The fixed app guarantees both values are scalars before the filter is built, so the filter can only ever be `{"username": "<a string>", "password": "<a string>"}` — two literal equality matches, with no room for an operator. The benign case is unchanged: a real string credential round-trips exactly as before.

## Parameterizing or escaping is not the fix

An experienced reader has a fix ready: "it's injection — parameterize the query, or escape the input, like you would for SQL." It is worth being precise about why that misses here.

Parameterizing is what closes SQL injection: the vulnerable SQLi app splices input into a *string* of SQL text (`f"... WHERE username = '{username}'"`), and a bound parameter (`"... = ?", (username,)`) keeps the command and the data separate so no character in the input can become SQL syntax. But there is no string of query text here to splice into. `pymongo` never concatenates — it passes your `dict` to the server *as a document*, which is already the moral equivalent of a parameterized query: the data is structurally separate from any command. And it is *still* vulnerable, because the injection was never about syntax inside a string. It is about **type**: the attacker replaced a scalar with an object, and the driver forwarded that object faithfully — operator and all. Escaping has nothing to bite on (there is no metacharacter in a string; the value *is* an object), and the parameterization that saves you from SQLi has no analog that catches a value changing type. The fix has to be one step earlier: guarantee the value is a scalar. (Same move as the "named, not applied" notes in `ssti-jinja` and `deserialization-pickle`: name the control the reader reaches for, and show why it is not the fix here.)

## A `$`-key blocklist is not the fix either

The next instinct is to keep the object but scrub it: "just strip any key that starts with `$`." That is a blocklist, and blocklists chase the *shape* of the attack instead of its cause — operators hide in nested objects, arrays, and dotted keys; operators exist that your list doesn't name; encodings vary. You stay one bypass behind. The root is a **type whitelist**, not a key blocklist: require the value to be a string, and it no longer matters what keys an object *would* have carried, because no object gets through at all. Whitelisting the type closes the cause; blocklisting keys patches a symptom.

## Type confusion — scalar vs. object

State the cause plainly. The app expected a **scalar** — a single value, a string: "the password equals this." What it accepted was an **object** — `{"$ne": null}` — which MongoDB reads as *structure*: an operator describing how to match, not a value to match. The whole bug is that the input was allowed to change type, from the scalar the code assumed to an object the query engine interprets. Forcing the type closes it at the root: with a string guaranteed, there is no object, so there is no operator.

One orthogonal note, because it is a tempting tangent: **hashing the password is not the NoSQL-injection fix.** Even an app that stores a bcrypt hash and looks the user up by username first is still injectable *in the username filter* — send `{"username": {"$ne": null}}` and `find_one` returns the first user in the collection and logs you in as them. Hashing protects the password at rest; it does nothing about an operator reaching a query filter. (This atom keeps plaintext passwords precisely so the canonical `password: {"$ne": null}` shape is the whole story — the fix is the type guard, not the storage format.)

## The impact is an auth bypass — like SQL injection, by a different cause

The finding is an authentication bypass: a crafted login logs you in as `admin` without the password, which is account takeover. That is the same ceiling as an auth bypass through SQL injection — and the two are worth holding side by side, because they are alike in impact and category and nothing else. Both are **A03 — Injection**; both subvert the query the login runs. But SQLi injects *syntax* into a *string* the app concatenates, and its fix is a parameterized query; this injects an *operator* by changing a value's *type* in a document the driver already passes faithfully, and its fix is to force the type. Same ceiling, same category, different mechanism, different fix. "One atom, one vulnerability" is about the *cause*, not the impact — `sqli-union-basic` and this atom can both end in a subverted query and a bypassed login, by two different roots.
