# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ in exactly one place — the guard that follows the order lookup in `GET /orders/:id`. `POST /login`, `GET /orders`, the helpers, the imports, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). The change is one object-level authorization check.

## The fix — existence and ownership become one guard

```diff
 app.get("/orders/:id", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
   const order = ORDERS[req.params.id];                      // string key (UUID) -- no Number() coercion
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

## The two fixes, side by side — the correction is id-agnostic

This atom's whole reason to exist is a proof by identity with `bola-sequential-id`: same seed, same surface, same fix, changing only the identifier type (a sequential integer there, a random UUID here). Put the two fixed guards next to each other and the added line is the same bytes:

```
# bola-sequential-id  (fixed/app.ts)                 # bola-uuid-leaked  (fixed/app.ts)
  const order = ORDERS[Number(req.params.id)];          const order = ORDERS[req.params.id];
  if (!order || order.owner !== caller) ... 404;        if (!order || order.owner !== caller) ... 404;
```

The one line that differs is the *lookup* above the guard — `Number(req.params.id)` becomes `req.params.id`, because a UUID key needs no numeric coercion — and that line is identical between *this atom's own* `vulnerable/` and `fixed/`, so it is not part of the fix. The fix itself — the ownership predicate, its shared `sendStatus(404)` exit, comment and all — is copied from `bola-sequential-id` without changing a character.

That is the point, and it is worth stating flatly: **the id type changed, the discovery changed, the whole walkthrough changed; the correction changed nothing.** If the id's format were the cause of the bug, the fix would have had to change with it. It didn't — the ownership check neither knows nor cares whether the id is `1007` or `edec4558-…`.

## One guard, one exit — the indistinguishability is structural

Existence and ownership run through a single condition — `!order || order.owner !== caller` — sharing **one** `return res.sendStatus(404)`. "Doesn't exist" and "exists but isn't yours" hit the same line, return the same status, and emit the same body — not because someone remembered to make the two responses match, but **by construction**: there is only one rejection path, so there is only one thing it can say. `bola-sequential-id`'s [`DIFF.md`](../bola-sequential-id/DIFF.md) works through why one-guard-one-exit matters in full; this atom inherits that structure verbatim rather than re-deriving it.

## 404, not 403

The fixed handler returns **`404`** for an order the caller doesn't own, byte-for-byte identical to the `404` for an id that was never seeded — you can confirm it against the fixed API, where a real order you don't own and an invented UUID come back the same status, body, and length. The full argument for choosing `404` over `403` — the GitHub-private-repo precedent, RFC 9110, and when `403` is the legitimate choice — lives in `bola-sequential-id`'s [`DIFF.md`](../bola-sequential-id/DIFF.md); it is inherited here by reference, not reopened.

One honest nuance, and it cuts *for* the thesis. In `bola-sequential-id` the `404` was doing double duty: with contiguous integer ids, a `403` would have been an enumeration oracle (walk the numbers, and the `403`-vs-`404` split maps which ids exist). With random UUIDs that pressure all but vanishes — there is no space to walk. Yet the fixed build keeps `404` unchanged, because the fix was copied wholesale and `404` is the conservative default that is never wrong. The remediation did not bend to the id format — which is, once more, the entire lesson.

## What the fix does *not* do — the id stays a UUID

Notice what the diff does not touch: the id. It does **not** swap the UUID for anything, does not reshape it, does not add a second layer of obscurity. Two things are in play and only one is the bug. The **id's format** governs *discovery* — how expensive it is to obtain a valid id. The **missing check** governs *access* — whether a non-owner who holds an id can read it. A stronger id only raises the cost of discovery; it never restores the check. So reshaping the id fixes the wrong axis: the attacker who already holds one (a leak, a shared link, a log line) sails straight past it, and you are left with the same BOLA behind a longer identifier.

The web atom `idor-uuid-guessable` makes the complementary half of this point from the opposite direction: its ids are **UUIDv1**, which carry a timestamp and the host's MAC and can be reconstructed from metadata the app publishes — proof that "unguessable" was never automatically true of a UUID. This atom holds the id genuinely out of reach (a **UUIDv4**, handed in from outside) and shows the flaw survives regardless. Guessable or not, the identifier's shape is not the access control. The transferable rule the web atoms `idor-numeric-id` and `bola-rest` teach holds here unchanged: **fix the missing check, don't reshape the identifier.**

## The mirrored seed is deliberate — and it is not an enumeration corpus

The twelve orders, four users, uneven 6/3/2/1 split, and every name, address, item, and amount are copied from `bola-sequential-id` object for object; only the id type changed. This is deliberate, not laziness. The thesis is a controlled experiment, and a controlled experiment changes **one** variable: if the seed also differed, two things would have moved (the id *and* the data) and the comparison would prove nothing. Holding the data fixed and varying only the identifier is what isolates the id's format as the thing under test.

One consequence to state outright, so the mirror isn't misread: the twelve orders are here **by mirroring, not because a bigger corpus helps an attacker**. With UUIDs the corpus size is irrelevant — the search space is the same whether the store holds two objects or two million, because you cannot walk ~2¹²² of randomness. In `bola-sequential-id`, twelve contiguous ids were an enumeration target; here, twelve UUIDs are twelve needles in an astronomically large haystack. More orders would not make them easier to find.

## The list endpoint already scopes — the asymmetry is the BOLA

`GET /orders` is *identical* in both versions, and in both it filters correctly: `Object.values(ORDERS).filter((o) => o.owner === caller)`. The developer knew how to scope a response to its owner — they did it on the collection. They just didn't do it on the single-object endpoint. That asymmetry — **list scoped, item unscoped** — is exactly how BOLA shows up in real codebases, and it's why the list staying correct in the fixed version isn't a second fix: it was never broken. It is also why the `GET /orders` list can safely return the caller's own id: showing you *your* UUID leaks nothing about anyone else's, so the store never hands an attacker a foothold. The one bug lived in `GET /orders/:id`, and the one-predicate guard is the whole repair.

## The token is opaque, and the attack never touches it

The Bearer token is an opaque random string (`randomBytes(24).toString("base64url")`) resolved server-side through the `TOKENS` map — a stand-in for an OAuth2 opaque access token or a session id, not a JWT. Nothing in the attack inspects, decodes, tampers with, or forges it; `dana` logs in as herself and sends her own token, unchanged, throughout. Keep the two axes apart: the value that became a UUID is the **order id**, not the token. A weak or forgeable token would be a *second* vulnerability (broken authentication); keeping it crypto-strong holds this atom to exactly one bug. The token isn't the vulnerability; the endpoint is.

## This is BOLA — IDOR in an API, and it lives in app.ts

Nothing the caller sends is parsed or executed; a legitimate id simply reaches an object outside the caller's scope. That is Broken Object Level Authorization — **API1:2023**, the #1 risk in the OWASP API Security Top 10 — and it is IDOR wearing an API's clothes, the same shape as the web atoms `idor-numeric-id` and `bola-rest` and the same class as the API atom `bola-sequential-id`: supply an id, and the server hands you an object it never checked was yours. Like all of them, the bug lives in `app.ts`, not in any template (there are none), and it doesn't `grep`: there's no dangerous string to find. You catch it by reading each endpoint that returns a user-scoped object and asking "where does this check the caller owns it?" — and noticing, here, that a working `authenticate()` call was quietly mistaken for that check.
