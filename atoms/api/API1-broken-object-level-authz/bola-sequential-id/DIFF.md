# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ in exactly one place — the guard that follows the order lookup in `GET /orders/:id`. `POST /login`, `GET /orders`, the helpers, the imports, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). The change is one object-level authorization check.

## The fix — existence and ownership become one guard

```diff
 app.get("/orders/:id", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
   const order = ORDERS[Number(req.params.id)];
-  if (!order) return res.sendStatus(404);
-  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
-  // order.owner is the caller. Authenticated is not authorized for THIS object.
-  res.json(order);                                          // BOLA -- no object-level check
+  // FIXED: existence and ownership are ONE guard with ONE exit -- a missing order and
+  // someone else's order both hit the same sendStatus(404), so "doesn't exist" and
+  // "not yours" are byte-identical by construction (a 403 here would be an enumeration oracle).
+  if (!order || order.owner !== caller) return res.sendStatus(404);
+  res.json(order);
 });
```

The fixed handler returns the order only when it exists **and** belongs to the caller. That single predicate closes the BOLA: the class is "the server returns a user-scoped object without checking the caller owns it," and the remediation is exactly its negation.

## One guard, one exit — the indistinguishability is structural

Read what the fix actually did to the control flow. The vulnerable version had two separate exits: `if (!order) return sendStatus(404)` for a missing order, and then `res.json(order)` for everything else — including someone else's order. The fix **collapses existence and ownership into a single condition** — `!order || order.owner !== caller` — sharing **one** `return res.sendStatus(404)`.

That collapse is the whole point. "Doesn't exist" and "exists but isn't yours" now run through the same line, return the same status, and emit the same body — not because someone remembered to make the two responses match, but **by construction**: there is only one rejection path, so there is only one thing it can say. Object-level authorization here is a guard condition *at the same level as existence* — not an optional check bolted on after the object is in hand. Write it as one guard and the enumeration oracle (next section) cannot exist; write it as a second `if` with its own `403` exit and you have to remember to keep the two responses identical, forever.

## 404, not 403 — the enumeration oracle

The fixed handler returns **`404`** for an order the caller doesn't own — not `403` — and a genuinely missing id returns `404` too. The two are deliberately indistinguishable, and with these ids that indistinguishability is the fix's second job, not a stylistic afterthought.

Why not `403`? Because the ids are **sequential**. A `403` announces "this order exists, but it's not yours"; a `404` for a missing id says "there's nothing here." Hand an attacker both and, walking the contiguous integers `1000, 1001, 1002, …`, the `403`-vs-`404` split becomes an **enumeration oracle** — a map of exactly which ids are real, built without ever reading an order's contents. Returning `404` for both "not yours" and "doesn't exist" leaks nothing: the attacker can't even tell which ids exist. You can confirm it against the fixed API — `GET /orders/1001` (a real order you don't own) and `GET /orders/1013` (never seeded) come back byte-for-byte identical.

This is a recognized, standards-backed move, not a trick:

- **A private repository on GitHub returns `404`, not `403`**, to anyone without access — precisely so the response doesn't confirm the repo exists. Same move: hide **existence**, not just **contents**.
- **RFC 9110 (HTTP Semantics) provides for the swap explicitly.** In **§15.5.4 (403 Forbidden)** it states that *"an origin server that wishes to 'hide' the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found),"* and **§15.5.5 (404 Not Found)** confirms a server may use `404` when it *"is not willing to disclose that one exists."* Hiding existence behind a `404` is a use the standard anticipates, not an abuse of it.
- **`403` is the legitimate choice when the object's existence is not sensitive.** This is a real fork, not a right-versus-wrong: `404`-as-oracle-defense is correct *here* because the ids are enumerable and existence leaks. In a context where admitting an object exists is harmless, `403` — semantically clearer, "it's there and it's not for you" — is perfectly correct. RFC 9110 offers both; the choice turns on **whether existence is sensitive**, and sequential ids make it sensitive. Rule of thumb: **`404`** when existence itself leaks; **`403`** when admitting existence is fine.

## What the fix does *not* do — the id stays sequential

Notice what the diff does not touch: the id. Order `1001` is still a plain contiguous integer, still in the URL, still handed to clients by the list endpoint. The fix does **not** swap it for a UUID, does not randomize it, does not hide it. That is deliberate, and it is half the lesson.

Two things are in play and only one is the bug. The **sequential id** governs *discovery* — contiguous integers make the neighbors cheap to find. The **missing check** governs *access* — it is what lets a non-owner read the object at all. A non-guessable id would only raise the cost of discovery; it would never restore the check. So reshaping the id fixes the wrong axis: the attacker who already holds an id (the list endpoint hands you one) sails straight past it, and you're left with the same BOLA behind a longer number. The transferable rule, the same one the web atoms `idor-numeric-id` and `bola-rest` teach: **fix the missing check, don't reshape the identifier.**

## The list endpoint already scopes — the asymmetry is the BOLA

`GET /orders` is *identical* in both versions, and in both it filters correctly: `Object.values(ORDERS).filter((o) => o.owner === caller)`. The developer knew how to scope a response to its owner — they did it on the collection. They just didn't do it on the single-object endpoint. That asymmetry — **list scoped, item unscoped** — is exactly how BOLA shows up in real codebases, and it's why the list staying correct in the fixed version isn't a second fix: it was never broken. The one bug lived in `GET /orders/:id`, and the one-predicate guard is the whole repair.

## The token is opaque, and the attack never touches it

The Bearer token is an opaque random string (`randomBytes(24).toString("base64url")`) resolved server-side through the `TOKENS` map — a stand-in for an OAuth2 opaque access token or a session id, not a JWT. Nothing in the attack inspects, decodes, tampers with, or forges it; `dana` logs in as herself and sends her own token, unchanged, throughout. That is the point of a crypto-strong opaque token here: it is solid and legitimately hers, so the only thing left to explain the cross-user read is the missing authorization. A weak or forgeable token would be a *second* vulnerability (broken authentication); keeping it strong holds this atom to exactly one bug. The token isn't the vulnerability; the endpoint is.

## This is BOLA — IDOR in an API, and it lives in app.ts

Nothing the caller sends is parsed or executed; a legitimate id simply reaches an object outside the caller's scope. That is Broken Object Level Authorization — **API1:2023**, the #1 risk in the OWASP API Security Top 10 — and it is IDOR wearing an API's clothes, the same shape as the web atoms `idor-numeric-id` and `bola-rest`: change a number, and the server hands you an object it never checked was yours. Like both, the bug lives in `app.ts`, not in any template (there are none), and it doesn't `grep`: there's no dangerous string to find. You catch it by reading each endpoint that returns a user-scoped object and asking "where does this check the caller owns it?" — and noticing, here, that a working `authenticate()` call was quietly mistaken for that check.
