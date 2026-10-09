# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ in exactly one place — one guard inserted into `PATCH /users/:handle`, between the authentication check and the record lookup, plus the comment above it. `POST /login`, `GET /users/:handle`, the `USERS` seed, the `TOKENS` map, the helpers, the imports, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). So is the rest of the `PATCH` handler: the `401`, the lookup, its `404`, the write, and the response are the same bytes in both builds. The change is one ownership check, added to the method that was missing it.

## The fix — the `GET`'s ownership check, now on `PATCH` too

```diff
 app.patch("/users/:handle", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
-  // VULNERABLE: the GET handler on this same path guards the record with an ownership
-  // check; this PATCH handler has none. Authorization belongs to (method + path), not to
-  // the path -- guarding the read left the write on the same resource wide open.
+  // FIXED: the same ownership check the GET handler already has, now on PATCH too --
+  // authorization covers every method of the path, not just the one the dev remembered.
+  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);                               // unknown target user
   user.displayName = req.body?.displayName ?? user.displayName;        // state change -- not a read
   res.json({ handle: req.params.handle, displayName: user.displayName }); // the state delta, echoed input
 });
```

The fixed `PATCH` writes only when the record is the caller's own. Nothing new was invented to make that decision: the guard it adds is **byte-identical** to the one `GET /users/:handle` already carries —

```ts
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
```

— the same line, now on the method it was missing from. The authorization was never a property of the *path*; it is a property of each **(method, path)** pair, and the vulnerable build had written it for one method and left the other bare. **The fix invents nothing: it carries the `GET` handler's ownership guard onto the `PATCH` handler, so the question the read already asked is finally asked by the write.**

**Read the predicate for what it asks.** `req.params.handle !== caller` compares two things — the handle in the path and `caller`, the identity `authenticate()` just resolved from the token — and it is a plain string comparison, not a lookup: the record is never consulted to make the decision. The guard sits on the line above `const user = USERS.get(req.params.handle)`, so when it runs, the record has not been fetched yet. That ordering is part of the fix, and it is the same discipline `bola-nested-resource` uses — there, `operates()` checks the parent store before any order is looked up; here, ownership is checked before any record is.

## Four fixes, four questions

The two API1 ownership atoms, the nested-resource atom, and the admin-function atom fixed their handlers in three shapes; this atom reuses the first shape's *content* on a new axis. Side by side, each line taken from its atom's `fixed/app.ts`:

```ts
// bola-sequential-id, bola-uuid-leaked — a predicate on the object, AFTER the lookup
  if (!order || order.owner !== caller) return res.sendStatus(404);

// bola-nested-resource — the lookup itself, moved INTO the authorized parent's scope
  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));

// bfla-admin-function — a guard on the caller's role, BEFORE the lookup
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);

// bfla-method-based — the GET handler's ownership guard, now on the PATCH it was missing from
  if (req.params.handle !== caller) return res.sendStatus(403);
```

- **`bola-sequential-id` and `bola-uuid-leaked`** ask *is this object yours?* The fixed handler fetches the order from the global collection exactly as its vulnerable twin does, then refuses it unless `order.owner` is the caller — a predicate of ownership, added to the guard after the lookup.
- **`bola-nested-resource`** asks *does it belong to this store?* Its fix adds no predicate to any guard; it moves the lookup into `ordersOf(req.params.storeId)`, the scope of the store the request has already authorized, so another store's order is never found.
- **`bfla-admin-function`** asks *may you invoke this operation?* Its fix adds a guard on the caller's **role**, ahead of the lookup, and no field of the target enters the decision.
- **This atom** asks a question about neither the object alone nor the role: *is authorization on every method of this path?* Its fix answers it by copying the `GET`'s ownership check onto the `PATCH`.

The content of this atom's check is object-level — the same *"is this record mine?"* the API1 atoms taught, and the reason the fix compares a handle to the caller rather than reading a role. But the *gap* it closes is not an object-level gap; it is a **method** left uncovered. None of the four is *the* authorization fix: each answers its own question. What transfers is the method — authorize the operation you are about to run, on the axis that operation requires — and the audit question that catches this one: *does every method of this path carry the authorization the resource needs?*

## The response is not third-party data

`res.json({ handle: req.params.handle, displayName: user.displayName })` looks like it returns the record, but on a write it reflects only what the caller just sent: `handle` is the path parameter echoed back, and `user.displayName` was set one line earlier to `req.body?.displayName` — the attacker's own input. So the `200` in the walkthrough's Step 1 proves exactly one thing: the **bypass** — the server accepted and ran the write for a non-owner. It does **not** prove that `alice`'s stored record changed in any particular way; an endpoint that ignored `:handle` and echoed the body back would answer identically. The proof that the write landed comes not from this response but from the victim reading her own record (next section).

This matters because it keeps the class clear. A `PATCH` that answered with the target's *prior* data would hand the attacker a foreign record in the response — and that reading, *"I got back data that wasn't mine,"* is BOLA, the wrong axis. Here nothing of `alice`'s comes back that the attacker did not send, so the only thing the `200` can mean is that a method ran that should have refused him.

## The write is real, and the victim can show it

`user.displayName = req.body?.displayName ?? user.displayName` really mutates the record's entry in the `Map`, and the change holds for as long as the process runs. But the attacker cannot see it through the API: the `PATCH` response only echoes his input, and `GET /users/:handle` refuses him a record that isn't his with `403`. There is no route that returns another user's record to him — which is exactly right, since that read is the thing the `GET` correctly protects.

The one account that *can* read `alice`'s record is `alice`. Logged in as herself, `GET /users/alice` returns `200` with the `displayName` the attacker planted — in the vulnerable build, `"pwned by clancy"` rather than the seed `"Alice Nguyen"`; in the fixed build, still `"Alice Nguyen"`, because the write was refused before it ran. The same protected `GET` that proves the ownership check works is also the instrument that proves the write happened. Each twin keeps its own seed, so an edit on 8205 is invisible on 8305.

*(On the types: `USERS.get(req.params.handle)` is `User | undefined` from `Map.get`'s own signature — not from `noUncheckedIndexedAccess`, which is on but not what forces it — so the `if (!user)` guard is required in both twins; remove it and `user.displayName` fails with `TS18048: 'user' is possibly 'undefined'`. The added ownership guard needs no such care: `req.params.handle !== caller` is a string comparison, with no `Map.get` and therefore no `?.`, unlike `bfla-admin-function`'s role guard.)*

## 403, not 404 — one criterion, a check before the lookup

A non-owner gets **`403`** from the fixed `PATCH`, and the `GET` answers a foreign read the same way — not the `404` the three API1 atoms return for an order outside the caller's scope. That is not an exception to the series; it is the series' one criterion applied to a check of a different shape.

**The criterion.** `bola-sequential-id`'s [`DIFF.md`](../../API1-broken-object-level-authz/bola-sequential-id/DIFF.md) closes its status-code discussion with a rule of thumb — *`404` when existence itself leaks; `403` when admitting existence is fine* — and `bola-nested-resource`'s [`DIFF.md`](../../API1-broken-object-level-authz/bola-nested-resource/DIFF.md) puts it as a question: *is the target's existence itself sensitive?* RFC 9110 (HTTP Semantics) provides for both answers in §15.5.4 (403 Forbidden):

> The 403 (Forbidden) status code indicates that the server understood
> the request but refuses to fulfill it. […]
>
> If authentication credentials were provided in the request, the
> server considers them insufficient to grant access. […]
>
> An origin server that wishes to "hide" the current existence of a
> forbidden target resource MAY instead respond with a status code of
> 404 (Not Found).

The `404` is a `MAY`: an option for a server that has an existence worth hiding, not a default.

**Why `404` does not transfer here.** In `bola-sequential-id` and `bola-nested-resource` the ownership check runs *after* the lookup, on an order fetched from an enumerable, contiguous id space (`1001`–`1012`); there, a `403` for "exists, but not yours" beside a `404` for "doesn't exist" would be an enumeration oracle — a difference in the responses that maps which ids exist without reading any of them — so the criterion gives `404`. (`bola-uuid-leaked` keeps that `404` by inheriting the fix, its id space no longer walkable.) This atom's check is a different shape: `req.params.handle !== caller` runs *before* any lookup and compares the path handle to the caller's own. It fires identically for a record that exists and one that was never seeded — both are simply "not yours" — so it never consults, and never reveals, whether the target exists. There is no oracle to close, and nothing to hide behind a `404`. By the same criterion, the honest answer is `403`.

And `403` is honest in the RFC's own terms: credentials *were* provided — a valid token, genuinely the caller's — and the server considers them insufficient for this record, which is exactly the second quoted sentence. `401` stays where it was, for a missing or invalid token; per §15.5.2 the server generating a `401` *"MUST send a WWW-Authenticate header field … containing at least one challenge"* — here `Bearer` — and the `403` carries none, because the caller is already authenticated and there is nothing to ask for. The one `404` left in the code — `if (!user)` for an unknown target — is unchanged in both twins, but in the fixed build it sits behind the ownership guard, which only the caller's own (always-seeded) handle clears, so it cannot fire there; the vulnerable build, lacking the guard, is the only place `PATCH /users/nobody` reaches that `404`.

**Rule of thumb — one criterion, the series': is the target's existence sensitive (or even revealed)?** Yes → **`404`**, which makes "not authorized" indistinguishable from "doesn't exist": the order in `bola-sequential-id` and `bola-nested-resource`, where an enumerable id space would turn a `403` into an oracle. No → an honest **`403`**: the store in `bola-nested-resource` (a public slug), the admin function in `bfla-admin-function` (a known capability), and here, where the check compares identities before any lookup and so discloses no existence at all. RFC 9110 offers both; the shape of the check — what it reads, and when — chooses, not the atom.

## This is BFLA — authorization on a method, not on a path

Nothing the caller sends is parsed or executed. A legitimate request, under a legitimate token, writes a record through a method that never checked whether the record was the caller's — while the `GET` on the very same path checks exactly that and refuses. That is Broken Function Level Authorization — **API5:2023** in the OWASP API Security Top 10 — in its method-based form, and its impact is **horizontal**: a plain user editing a peer's record, where `bfla-admin-function` showed the vertical kind, a plain user reaching an admin's capability. Reading it as BOLA points you at the wrong place: the object-level ownership check is present and *correct* on `GET`, and the flaw is not that it is wrong but that it does not cover `PATCH`. Like the rest of the series, the bug lives in `app.ts` and doesn't `grep`: there is no dangerous string to find. You catch it by listing the methods a path accepts and asking, of each one, *does this carry the authorization the resource needs?* — and noticing, here, that the read did and the write did not.
