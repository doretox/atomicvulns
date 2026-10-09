# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ in exactly one place — one guard inserted into `POST /admin/users/:handle/promote`, between the authentication check and the target lookup, plus the comment above it. `POST /login`, the `USERS` seed, the `TOKENS` map, the helpers, the imports, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). So is the rest of the handler: the `401`, the target lookup, its `404`, the write, and the response are the same bytes in both builds. The change is one function-level authorization check.

## The fix — the caller's role is checked right after authentication, before the target lookup

```diff
 app.post("/admin/users/:handle/promote", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
-  // VULNERABLE: the caller is authenticated, but the handler never checks the caller's
-  // ROLE. Promoting a user to admin is an admin-only function; here ANY authenticated
-  // user can invoke it. Authenticated is not authorized to PERFORM this operation.
+  // FIXED: function-level authorization. Promoting is an admin-only capability, so the
+  // caller's ROLE is checked right after authentication -- a non-admin is refused 403
+  // BEFORE the target is ever looked up, so the gate leaks nothing about who exists.
+  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
   const target = USERS.get(req.params.handle);
   if (!target) return res.sendStatus(404);                  // unknown target user
   target.is_admin = true;                                   // state change -- not a read
   res.json({ handle: req.params.handle, is_admin: true });  // the state delta, not third-party data
 });
```

The fixed handler runs the promotion only when the caller is an administrator. Everything that decision needs was already in the vulnerable build: `caller` held the authenticated handle, and every user in the seed already carried an `is_admin` flag. The vulnerable handler simply never consulted either one before acting.

**Read the predicate for what it asks.** `USERS.get(caller)?.is_admin` asks one question — *is the caller an admin?* — and its only input is `caller`, the identity `authenticate()` has just resolved from the token. The target is not an argument of that question, and it could not be: the guard sits on the line above `const target = USERS.get(req.params.handle)`, so when the decision is made the target has not been looked up yet. Whether `:handle` names `alice`, the caller himself, or an account that was never seeded, the guard receives the same input and gives the same answer. **The fix adds no check about the target at all — it asks only whether the caller may run the function.**

The position is part of the fix. Function-level authorization sits right beside authentication, on the line after it, not as an afterthought once the operation is already under way: the first guard establishes who is calling, the second whether that caller may invoke this function, and only then does the handler touch the account it operates on. It is the same ordering discipline `bola-nested-resource` uses — there, `operates()` checks the parent store before any order is looked up; here, the role check runs before any user is.

**The compiler insists on the `?.`.** `Map.get` is declared as returning `V | undefined`, so `USERS.get(caller)` is typed `User | undefined` even though, at runtime, `caller` is always a seeded handle (`POST /login` only issues tokens to users in `USERS`). The `?.` is therefore required: replace it with a plain `.` and `tsc` reports `TS2532: Object is possibly 'undefined'`. The same signature types `target` as `User | undefined`, which is why the unchanged `if (!target)` guard is required in both twins — remove it and `target.is_admin = true` fails with `TS18048: 'target' is possibly 'undefined'`. Both errors come from `Map.get`'s signature, not from `noUncheckedIndexedAccess`: the flag stays on, inherited from the series, but switching it off changes neither error. And were the `?.` ever to short-circuit, `!undefined` is `true` and the guard refuses — the check fails closed.

## Three questions, three fixes

The three API1 atoms fixed their handlers in two shapes; this atom adds a third. Side by side, each line taken from its atom's `fixed/app.ts`:

```ts
// bola-sequential-id, bola-uuid-leaked — a predicate on the object, AFTER the lookup
  if (!order || order.owner !== caller) return res.sendStatus(404);

// bola-nested-resource — the lookup itself, moved INTO the authorized parent's scope
  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));

// bfla-admin-function — a guard on the caller's role, BEFORE the lookup
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
```

- **`bola-sequential-id` and `bola-uuid-leaked`** ask *is this object yours?* The fixed handler fetches the order from the global collection exactly as its vulnerable twin does, then refuses it unless `order.owner` is the caller — a predicate of ownership, added to the guard after the lookup.
- **`bola-nested-resource`** asks *does it belong to this store?* Its fix adds no predicate to any guard; it moves the lookup into `ordersOf(req.params.storeId)`, the scope of the store the request has already authorized, so another store's order is never found.
- **This atom** asks *may you invoke this operation?* Its fix adds a guard on the caller's role, ahead of the lookup.

After the lookup, inside it, before it. In both API1 shapes the check is made against the order — its `owner`, or the `storeId` that `ordersOf()` filters on. Here no field of the target is consulted, because the question is not about the target. None of the three is *the* authorization fix; each is the fix for its own question. What transfers is the method: authorize the operation you are about to run, on the axis that operation requires — the object's owner, the object's parent, or the caller's role.

## The response is not third-party data

`res.json({ handle: req.params.handle, is_admin: true })` is built from two things, and neither is read from the target: `handle` is the path parameter the caller sent, echoed back, and `is_admin: true` is a literal in the source. The user the handler looked up is written to — `target.is_admin = true` — and never serialized. Compare `res.json(order)` in the API1 atoms, where the response *was* the stored record: buyer name, delivery address, item, amount. Here there is no such record to return; a user in the seed carries one field, `is_admin`, and nothing else.

That is deliberate, and it is what keeps the atom on its axis. An admin function that returned someone else's record would invite the BOLA reading — *I saw data that wasn't mine* — and the class would be misfiled. A function that changes state and answers only with the caller's own input and a constant leaves one explanation for the `200`: the function ran for a caller who should not have been able to run it.

## The write is real, and the API can't show it

`target.is_admin = true` really mutates the user's entry in the `Map`, and the change holds for as long as the process runs. Nothing in the API reads it back. The surface is two routes, `POST /login` and the admin function, and neither returns a role. And the success body is deterministic: the same bytes whether the target was a plain member or already an admin — promote `alice` twice and the two responses are byte-identical. From outside, a `200` says only that the function ran.

In the vulnerable build `is_admin` is written and never read. In the fixed build it has exactly one reader, the added guard — so the evidence that the flag governs anything comes from the fixed twin's behavior (`carol` gets `200`, `clancy` gets `403`), never from observing the flag through the API.

## 403, not 404 — one criterion, a different kind of target

The fixed handler refuses a non-admin with **`403`**, where the three API1 atoms answer `404` for an order outside the caller's scope. That is not an exception to the series, and it is not a new rule. It is the series' one criterion, applied to a target of a different kind.

**The criterion.** `bola-sequential-id`'s [`DIFF.md`](../../API1-broken-object-level-authz/bola-sequential-id/DIFF.md) closes its status-code discussion with a rule of thumb — *`404` when existence itself leaks; `403` when admitting existence is fine* — and `bola-nested-resource`'s [`DIFF.md`](../../API1-broken-object-level-authz/bola-nested-resource/DIFF.md) puts the same rule as a question: *is the target's existence itself sensitive?* RFC 9110 (HTTP Semantics) provides for both answers in §15.5.4 (403 Forbidden):

> The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it. […]
>
> If authentication credentials were provided in the request, the server considers them insufficient to grant access. […]
>
> An origin server that wishes to "hide" the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found).

The `404` is a `MAY`: an option for a server that has an existence worth hiding, not a default.

**Where the API1 atoms land.**

- **In `bola-sequential-id` and `bola-nested-resource`, an order's existence is sensitive.** Order ids are contiguous integers, `1001`–`1012` — in `bola-nested-resource`, one global counter shared by every store. A `403` for "exists, but not yours" (or "exists, but in another store") beside a `404` for "doesn't exist" would be an enumeration oracle: a difference in the responses that maps which ids exist without reading any of them. The criterion gives `404`.
- **`bola-uuid-leaked` keeps the same `404` by inheriting the fix, not under fresh pressure.** Its ids are random UUIDs, the oracle pressure *"all but vanishes"*, and its DIFF keeps `404` as *"the conservative default that is never wrong."*
- **`bola-nested-resource` also applies the criterion the other way.** In the same handler, a store's slug is a public name, its existence is not sensitive, and a store you don't operate gets `403`. The honest `403` is already series precedent.
- **In all three, the authorization target is an object** — an order or a store, an instance addressed by an id or a slug in the path.

**Here the target is a capability.** What the guard protects is a single, named function, not an instance in an id-space, and the existence of that function is a premise of this atom: the admin path is simply known — predictable names, an OpenAPI spec that is often public, a front-end bundle that ships it. There is no id-space to sweep and no existence to hide; a `404` would conceal nothing the attacker doesn't already have, and would contradict the premise the atom starts from. The criterion therefore gives `403`, as it did for the store.

And `403` is the honest answer, in the RFC's own terms. Credentials *were* provided — a valid token, genuinely `clancy`'s — and the server considers them insufficient for this function, which is exactly the case the second quoted sentence describes. `401` stays where it was, for a missing or invalid token, so the two codes keep authentication and function-level authorization apart. The headers draw the same line: per §15.5.2, the server generating a `401` *"MUST send a WWW-Authenticate header field"* with at least one challenge — here, `Bearer` — and the `403` carries none. The credentials were never the problem, only what they are allowed to do.

**The denial is not an oracle, by construction.** The guard runs before the target lookup, so a non-admin gets the same `403` for `alice`, for himself, and for a handle that was never seeded. It discloses one fact — that the caller is not an admin — and that is a fact about his own account, which he already knows. The `404` for an unknown handle survives the fix, but only past the gate, so only an admin can reach it — and knowing which accounts exist is legitimately an admin's business.

**Rule of thumb — one criterion, the series': is the target's existence sensitive?** Yes → **`404`**, which makes "not authorized" indistinguishable from "doesn't exist": the order in `bola-sequential-id` and `bola-nested-resource`, where an enumerable id-space would turn a `403` into an oracle. No → an honest **`403`**: the store in `bola-nested-resource`, and the admin function here, where what the caller lacks is a role, not knowledge of a secret. `bola-uuid-leaked` doesn't contradict the rule — with UUIDs the oracle pressure all but vanished, and the `404` stayed as the inherited conservative default. RFC 9110 offers both; the nature of the target chooses, not the atom.

## This is BFLA — authenticated, never authorized for the function

Nothing the caller sends is parsed or executed. A legitimate request, under a legitimate token, invokes a function above the caller's privilege level. That is Broken Function Level Authorization — **API5:2023** in the OWASP API Security Top 10 — and its impact is vertical privilege escalation: a plain member exercising an administrator's capability, where the API1 atoms showed the horizontal kind. Same root as BOLA, different axis: there, the handler knew who you were and never checked the order against its owner or its authorized store; here, it knows who you are and never checks what you may do. The opaque, crypto-strong token is untouched by the attack and by the fix alike — `authenticate()` and its `401` are the same bytes in both twins, because the bug was never there. And like the API1 atoms, the bug lives in `app.ts` and doesn't `grep`: there is no dangerous string to find. You catch it by reading each privileged operation and asking *where does this endpoint check that the caller may invoke this function?* — and noticing, here, that a working authentication check was standing in for an authorization check nobody wrote.
