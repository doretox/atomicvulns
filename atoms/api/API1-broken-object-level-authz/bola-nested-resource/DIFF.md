# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ in exactly one place — the line that looks the order up in `GET /stores/:storeId/orders/:orderId`, plus the comment above it. `POST /login`, `GET /stores/:storeId/orders`, the `STORES` table, `operates()`, `ordersOf()`, the seed, the imports, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). So are all three of the handler's guards: the `401`, the `403`, and the existence check that returns `404` are the same bytes in both builds. The fix does not edit a single guard — it changes what reaches the last one.

## The fix — the lookup moves inside the parent's scope

```diff
   if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
-  // VULNERABLE: the lookup is GLOBAL. The caller operates :storeId, but order.storeId is
-  // never compared to it -- an order from ANY store comes back.
-  const order = ORDERS[Number(req.params.orderId)];
+  // FIXED: the order is looked up INSIDE the authorized store, not in the global collection --
+  // an order from another store is simply not found, the same 404 as an id that never existed.
+  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));
   if (!order) return res.sendStatus(404);
   res.json(order);
```

The vulnerable line asks the platform-wide collection for an id. The fixed line asks *this store's orders* for an id. In SQL the same move is `SELECT … WHERE id = ?` becoming `SELECT … WHERE store_id = ? AND id = ?`: the child is fetched **through** the parent, and the parent is the one the request has already authorized.

**No information was missing — the question was.** Every order carries its own `storeId`, and the vulnerable build even serialized it into the response, so you could watch `"storeId":"meadow"` come back from a path that said `harbor`. The data needed to authorize correctly sat inside the object the whole time. What the fix adds is not a field, not a join, not a new concept — it is the act of *asking*.

It asks with machinery that was already in the file. The predicate doing the work is `o.storeId === storeId`, and it lives in `ordersOf()`:

```ts
function ordersOf(storeId: string): Order[] {
  return Object.values(ORDERS).filter((o) => o.storeId === storeId);   // the store's scope
}
```

That helper is present in the **vulnerable** twin too, unchanged, and the list route immediately above already called it. So the fix invents nothing and authorizes nothing by magic: the store-scope predicate the application already had is finally applied on the one route that was skipping it.

## Not found, rather than found and refused

The consequence worth naming precisely: in the fixed build, another store's order **is never materialized**. The `find()` walks the authorized store's scope, doesn't see the id, and returns `undefined`. There is no point in the handler where a `meadow` order sits in a variable called `order` while the code decides what to do with it.

Contrast the two companion atoms. In `bola-sequential-id` and `bola-uuid-leaked`, `fixed/app.ts` looks the object up in the global collection exactly as its vulnerable twin does, gets the other user's order in hand, and *then* refuses it in the guard — `if (!order || order.owner !== caller) return res.sendStatus(404);`. Fetch, then reject. Here the order is reversed: scope first, so there is nothing left to reject.

Both shapes close the hole, and the difference matters for a reason beyond taste. Fetch-then-reject puts the whole weight on a guard that a later refactor can weaken and a new code path can forget; a scoped lookup makes the wrong object unreachable from that code path at all. Whenever the data layer can express the parent — a `WHERE` clause, a relation, a repository handle already bound to the tenant — pushing the parent into the query is the more durable of the two.

## The existence guard didn't move

`if (!order) return res.sendStatus(404);` and `res.json(order);` are the same bytes in both twins, and that is worth a pause. The previous two atoms reached indistinguishability *by editing the guard* — collapsing existence and ownership into one condition with one exit. Here indistinguishability falls out of the lookup instead: "not this store's" and "doesn't exist anywhere" both arrive at the guard as the same `undefined`, so they cannot produce different responses even in principle. Same end state, reached from the other side.

## Why this isn't the previous atoms' fix — and that is the point

`bola-sequential-id` fixed its handler by **adding a predicate to the guard after the lookup**. `bola-uuid-leaked` then copied that fix character for character and made the identity its whole thesis: the id type changed, the discovery changed, the walkthrough changed, and the correction did not.

This atom deliberately breaks that streak. Its bug has a different shape — a check that is *present and aimed at the parent*, rather than a check that is absent — so the repair has a different shape too: **move the lookup into the parent's scope** instead of adding a second predicate after it. Three atoms in a row with the same patch would be a sign that the third one didn't need to exist. The transferable lesson is not "the fix is always one predicate on one guard." It is: **authorize the object you are about to return.**

Notice also what the fix leaves alone: the parent check. `operates(caller, req.params.storeId)` was correct and is still necessary — delete it and any operator could read any store's orders through that store's own path, which is a different and larger hole. The fix **adds the question that was missing**; it does not replace the one that was already there.

## Three status codes, one criterion

The corrected handler answers three different rejections with two different codes, and read out of context that looks like inconsistency. It isn't. There is one criterion, applied to two different kinds of object.

**The criterion: is the target's existence itself sensitive?** RFC 9110 (HTTP Semantics) sets out both options and leaves the choice to the server. §15.5.4 defines the honest refusal: *"The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it,"* and adds that *"an origin server that wishes to 'hide' the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found)."* §15.5.5 defines the other side: `404` means the origin server *"did not find a current representation for the target resource or is not willing to disclose that one exists."* Refuse openly, or conceal existence — the standard offers both and asks which one the resource needs.

Now the three cases, side by side:

- **A store you don't operate → `403`.** `GET /stores/meadow/orders/1009` with clancy's token. A store's existence is not a secret: `meadow` is a shop, its slug is a public name, and the atom's README lists all three. Hiding it would protect nothing, so the honest answer is the right one — the store is there and you don't operate it.
- **A store that doesn't exist → `403` as well.** `GET /stores/lagoon/orders/1009` returns the same `Forbidden`, because `operates()` asks about a **link**, not about existence: "do you operate this store?" And "no" is equally true of a store that exists without you and of a store that isn't there at all. Since store existence isn't sensitive, one answer for both costs nothing and keeps the check to a single line. This is the criterion being applied, not a concession to convenience: there is nothing here that needs hiding.
- **An order from another store → `404`.** `GET /stores/harbor/orders/1009` on the fixed build. Here the same criterion comes out the other way, because an *order's* existence **is** sensitive. The ids are one global counter, so a `403` for "exists in another store" against a `404` for "exists nowhere" would hand the caller an **enumeration oracle** — a difference in the responses that maps which objects exist without reading any of them. Sweep `1001`, `1002`, `1003`… through your own store's path and that split draws you the other stores' order volume, cadence, and growth. A uniform `404` closes the oracle, and preserves the indistinguishability the two companion atoms established: not-this-store's and never-existed come back byte-identical, `Not Found` either way.

The same question — *is existence sensitive?* — therefore yields `403` for the parent and `404` for the child, because a shop and an order are not the same kind of secret. Neither code is the "right" one with the other as a compromise: the status code is a property of the object being protected, not a habit of the handler.

Two details hold the argument together. **The parent check runs before the lookup**, so a caller who doesn't operate the store gets `403` without any order being consulted — the `403` therefore leaks nothing at all about orders, and the oracle could only ever have existed *inside* a store the caller legitimately operates, which is exactly where the `404` closes it. And the `404` is genuinely uniform: on the fixed build, `1009` (another store's), `1001` (a third store's), and `1013` (never seeded) all come back `404` with the same nine-byte `Not Found`.

`bola-sequential-id`'s [`DIFF.md`](../bola-sequential-id/DIFF.md) carries the rest of this argument — the private-GitHub-repository precedent, and the rule of thumb for choosing between the two codes — and it is inherited here by reference rather than retold.

## What grew, and why

This atom is bigger than its two predecessors, and every extra line is the new entity: `STORES` (the stores and the operator-to-store links), `operates()` to ask about them, `ordersOf()` to scope by them, and `storeId` on the order where `owner` used to be. That is the price of the variant, not decoration. Without a real parent there is no nested resource, and without a parent worth authorizing there is no check to mistake for the right one.

The seed is mirrored from the previous atoms **in part, on purpose**: the same twelve orders on ids `1001`–`1012`, the same items, amounts, and addresses, redistributed three/four/five across the stores, with new buyer names. You should recognize the data and see that only the authorization structure moved. That is a different use of the mirror than `bola-uuid-leaked` made, where the mirror had to be total because identity *was* the thesis; here the thesis is contrast, so the mirror is partial by design.

One deliberate detail in the seed: the buyers — `Priya Shah`, `Marcus Webb`, `Elena Ruiz`, `Theo Okafor` — share no name with any operator. Buyers are the public, operators are staff. An order whose buyer carried an operator's name would whisper a second axis of ownership, person-owns-order, and this atom depends on the reader accepting that the thing which owns an order is the **store**. Which is also why every operator of a store reads all of that store's orders, and why that is the feature: `bob` and `carol` both operate `summit`, both see its five orders, and neither is exploiting anything.

## The token is opaque, and the attack never touches it

The Bearer token is an opaque random string (`randomBytes(24).toString("base64url")`) resolved server-side through the `TOKENS` map — a stand-in for an OAuth2 opaque access token or a session id, not a JWT. Nothing in the attack inspects, decodes, tampers with, or forges it: `clancy` logs in as himself and sends his own token, unchanged, throughout. That is the point of a crypto-strong opaque token here. His identity is solid and legitimately his, and the parent check reads that identity correctly on every single request — so the only thing left to explain the cross-store read is the question nobody asked. A weak or forgeable token would be a *second* vulnerability (broken authentication); keeping it strong holds this atom to exactly one bug.

## This is BOLA — the check was present and pointed elsewhere

Nothing the caller sends is parsed or executed. Two legitimate ids, combined in a legitimate request under a legitimate token, reach an object outside the caller's scope. That is Broken Object Level Authorization — **API1:2023**, the #1 risk in the OWASP API Security Top 10 — and it is IDOR wearing an API's clothes, the same class as `bola-sequential-id` and `bola-uuid-leaked`. What differs is where the gap sits. In those two, the detail route asked nothing about the object, and the audit question that finds them is "where does this check the caller owns it?" Here that question has an answer — `operates()`, right there in the handler, doing real work — and the answer is the wrong one, because it is about the parent. So for a nested resource the audit question turns one notch sharper: **does the object I am about to return belong to the parent I just authorized?** A handler can pass the first question and fail the second, and it will not `grep` either way.
