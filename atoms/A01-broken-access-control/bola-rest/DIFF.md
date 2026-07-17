# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ in exactly one route — `get_order`. `POST /login`, `GET /api/orders`, the helpers, the imports, the `Dockerfile`, and `requirements.txt` are identical between the two versions (and there are no templates — this atom is API-only). The change is one object-level authorization check.

## The fix — object-level authorization

```diff
 @app.route("/api/orders/<int:order_id>")
 def get_order(order_id):
-    _authenticate()   # require a valid token (401 otherwise) -- AUTHENTICATION only
+    caller = _authenticate()
     order = ORDERS.get(order_id)
     if order is None:
         abort(404)
-    # VULNERABLE: the request is authenticated, but the order is returned WITHOUT
-    # checking that order["owner"] is the authenticated caller. Being authenticated
-    # is not being authorized for THIS object. (BOLA -- no object-level check.)
+    # FIXED: object-level authorization -- serve the order only to its owner.
+    # 404 (not 403) so "exists but not yours" is indistinguishable from "doesn't
+    # exist": with sequential ids, a 403 would be an enumeration oracle.
+    if order["owner"] != caller:
+        abort(404)
     return jsonify(order)
```

The fixed view compares the order's `owner` to the authenticated caller and refuses a mismatch. That single conditional closes the BOLA: the class is "the server returns a user-scoped object without checking the caller owns it," and the remediation is exactly its negation.

## Authenticated ≠ authorized — you can see it in the diff

Look at the first changed line: `_authenticate()` became `caller = _authenticate()`. That is the whole lesson in one edit.

Both versions authenticate — both call `_authenticate()`, both reject a missing or invalid token with `401`. The vulnerable version calls it purely for that side effect and **throws the identity away**; it never uses *who* the caller is. The fixed version **keeps** the identity and checks the object against it. Authentication answers "who are you?"; authorization answers "is this object yours?" The bug was never that the first question went unasked — it was that the answer went unused.

This is why "there's auth on the endpoint" is false comfort during a review, and why BOLA is so common: the authentication is right there, doing its job, and it lulls you past the missing authorization sitting next to it.

## 404, not 403 — the enumeration oracle

The fixed view returns **`404`** for an order the caller doesn't own — not `403` — and a genuinely missing id returns `404` too. The two are deliberately indistinguishable.

Why not `403`? Because the ids are **sequential**. A `403` announces "this order exists, but it's not yours"; walk the integers and `403`-vs-`404` becomes an **enumeration oracle** that maps every order in the system — exactly the reconnaissance an attacker wants before a BOLA. Returning `404` for both "not yours" and "doesn't exist" leaks nothing: the attacker can't even tell which ids are real.

This is where the sibling atoms differ, and the difference is instructive:

- **`idor-uuid-guessable` returns `403`**, and that is fine there — its ids are UUIDs, a non-enumerable space. A `403`/`404` oracle over 122 random bits is useless; you can't walk it. Its DIFF even said so in advance: *"A 403 here does confirm the receipt exists; if that mattered, 404 would be the defense-in-depth choice."* Here it matters.
- **`idor-numeric-id` returns `403` with sequential ids** — so it carries the same latent oracle. It isn't wrong: it was the first, simplest statement of the missing-check lesson and chose the semantically honest status (`403 Forbidden` — "a real object, not for you"), because leaking existence wasn't its point. This atom, modeling a REST API where enumeration is the signature move, makes the oracle the point — so it chooses `404`.
- **`path-traversal-basic` returns `404`** too, but for a different reason: there the rejected "resource" is a path *outside* the app's domain, and `404` refuses to confirm anything exists out there. Here the object is genuinely the app's — `404` hides that it exists, on purpose.

Rule of thumb (extending `idor-uuid-guessable`'s): return **`403`** when admitting the object exists is acceptable — or the ids aren't enumerable; return **`404`** when existence itself leaks. Sequential ids make existence leak.

## Reshaping the id is a losing game

Notice what the fix does *not* change: the id. Order 41 is still a plain sequential integer, sitting in the URL, handed to clients by the list endpoint. `idor-uuid-guessable` already made this case about its own fix — that swapping the integer for a UUID would be *"obfuscation... theater,"* that hiding or randomizing an id "only changes how hard the bug is to *find*." In an API the point is sharper still: the id is public *by contract* — REST clients are supposed to hold and pass ids — so "hide the id" isn't even a coherent option. The only defense is authorization. The transferable rule, the same one `idor-numeric-id` and `idor-uuid-guessable` teach: **fix the missing check, don't reshape the identifier.**

## The list endpoint already scopes — the asymmetry is the BOLA

`GET /api/orders` is *identical* in both versions, and in both it filters correctly: `[o for o in ORDERS.values() if o["owner"] == caller]`. The developer knew how to scope a response to its owner — they did it on the collection. They just didn't do it on the single-object endpoint. That asymmetry — **list scoped, item unscoped** — is exactly how BOLA shows up in real codebases, and it's why the list staying correct in the fixed version isn't a second fix: it was never broken. The one bug lived in `get_order`, and the one-line check is the whole repair.

## The token is opaque, and the attack never touches it

The Bearer token is an opaque random string resolved server-side through the `TOKENS` map — a stand-in for an OAuth2 opaque access token or a session id, not a JWT. Nothing in the attack inspects, decodes, tampers with, or forges it; mallory logs in as herself and sends her own token, unchanged, throughout. That is the point of an opaque token here: it is solid and legitimately hers, so the only thing left to explain the cross-user read is the missing authorization. The token isn't the vulnerability; the endpoint is.

## This is BOLA — IDOR in an API, and it lives in app.py

Nothing the caller sends is parsed or executed; a legitimate id simply reaches an object outside the caller's scope. That is Broken Access Control (A01 on the web, **API1:2023** on the API list), the same shape as `idor-numeric-id` and `idor-uuid-guessable` — there you change a number or reconstruct a UUID, here you read your id off the API and ask for the neighbor, and all three fixes are the ownership check that was missing. Like both siblings, the bug lives in `app.py`, not in any template (there are none), and it doesn't `grep`: there's no `f"`, `|safe`, or `eval` to find. You catch it by reading each endpoint that returns a user-scoped object and asking "where does this check the caller owns it?" — and noticing, here, that a working `_authenticate()` call was quietly mistaken for that check.
