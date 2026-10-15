# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ in exactly one place — the line that serializes the response in `GET /users/:handle`, plus the comment above it. `POST /login`, the authentication helpers, the ownership guard, the `USERS` seed, the `TOKENS` map, the imports, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). So is the rest of the handler: the `401`, the `403`, the lookup, and its `404` are the same bytes in both builds. The change is one response projection.

## The fix — an allow-list, not the stored object

```diff
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);
-  // VULNERABLE: the ownership check above is right -- this IS your record. But the response
-  // spreads the WHOLE stored object, so every server-side field rides along with the public
-  // one. Authorization applies to each property returned, not only to the object.
-  res.json({ handle: req.params.handle, ...user });
+  // FIXED: the response names the fields the caller may see -- an allow-list, not the stored
+  // object. A field added to User later stays server-side until someone deliberately exposes it.
+  res.json({ handle: req.params.handle, displayName: user.displayName });
```

The vulnerable line spreads the whole record (`...user`), so `displayName`, `passwordHash`, and `is_admin` all ship. The fixed line names one field — `displayName` — so nothing else can leave, whatever the record holds.

**Read the fix for what it authorizes.** The handler already authorized the **object**: the ownership guard one line above (`if (req.params.handle !== caller) return res.sendStatus(403)`) makes sure this record is the caller's own. What it never did was authorize the **properties** of that object. The fix extends authorization down to the field grain: it decides, explicitly, which properties the response may carry. That is the whole of BOPLA's read face — authorization is owed not only to the object but to each field returned from it.

> **`...user` serializes the object the store holds; the allow-list serializes the object the caller is cleared to read — BOPLA is the distance between the two.**

## Allow-list, not deny-list — fail closed, not fail open

An allow-list is not the only projection that removes the two fields. A deny-list would also work *today*:

```ts
// CONSIDERED AND REJECTED -- a deny-list (blacklist): strip the known-bad fields.
const { passwordHash, is_admin, ...safe } = user;
res.json({ handle: req.params.handle, ...safe });
```

It strips `passwordHash` and `is_admin`, and the response comes out clean. But it **fails open**: the day someone adds a new server-side field to `User` — an `internalNote`, a `resetToken` — that field leaks on its own, because nobody remembered to add it to the deny-list. The allow-list **fails closed**: a new field stays server-side until someone deliberately names it in the response.

The difference is not stylistic — it is the direction a mistake runs. Add a field and forget to touch the response:

| Projection | today (3 fields) | tomorrow (+ a new `internalNote`) |
|---|---|---|
| **spread** (`...user`) — the vulnerable build | leaks `passwordHash` + `is_admin` | **also leaks** `internalNote` |
| **deny-list** (`const {passwordHash, is_admin, ...safe} = user`) | clean | **leaks** `internalNote` (fails open) |
| **allow-list** (`{ displayName }`) — the fix | clean | **still clean** (fails closed) |

At scale this projection becomes a shared **serializer** or **DTO** (Data Transfer Object) — one place that defines each entity's public shape — rather than an object literal inlined in the handler. That is the same idea one grain larger; this atom keeps it to the one line so the diff stays on the lesson.

## The response is the stored object, until it isn't

`res.json({ handle: req.params.handle, ...user })` reads as "return the record," and that is exactly the trap: it returns *everything the record happens to hold*, not what the caller is cleared to read. The two were the same object only because nobody decided otherwise. `handle` is the path parameter echoed back (the `Map` key, not a field of `User`), and `...user` pours in whatever `User` carries — here three fields, two of them internal. The fixed handler breaks that accident apart: the response is now built from a deliberate list, and a field reaches the client only if the list names it.

*(On the types: `USERS.get(req.params.handle)` is `User | undefined` from `Map.get`'s own signature, so the `if (!user)` guard is kept byte-identical in both twins. It is only **type-forced** in the fixed build, where `user.displayName` dereferences `user`; in the vulnerable build, spreading `User | undefined` is a no-op TypeScript accepts, so the guard is hygiene there, not a compiler requirement. Either way it is unreachable at runtime: the ownership guard above it only lets through the caller's own, always-seeded handle. No `?.` appears anywhere — the ownership guard is a string comparison.)*

## Status codes — inherited, not re-argued

Nothing about the status codes is new here, so this atom borrows the argument rather than repeating it:

- **A foreign read → `403`.** `GET /users/alice` with `clancy`'s token is refused by the ownership guard, which compares the path handle to the caller **before any lookup** — so it reveals no existence and is no enumeration oracle. This is the same guard, and the same reasoning, as `bfla-method-based`; its [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md) carries the full account — RFC 9110 §15.5.4 and the series' single criterion for `403` vs `404`.
- **A missing or invalid token → `401`** with a `WWW-Authenticate: Bearer` challenge (RFC 9110 §15.5.2); the `403` carries none, because the caller is already authenticated. Also inherited; see the same `bfla-method-based` [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md).

The one `404` in the handler (`if (!user)`) is unchanged in both twins and unreachable at runtime, because the ownership guard only admits the caller's own seeded handle. This atom has fewer reachable status codes than `bfla-method-based` — there is no write, no `PATCH`, and no path that reaches a foreign record past the guard.

## This is BOPLA — authorization on a property, not just on an object

Nothing the caller sends is parsed or executed. A legitimate request, under a legitimate token, reads the caller's **own** record — correctly authorized at the object level — and the response hands back fields the caller may not see. That is Broken Object Property Level Authorization — **API3:2023** in the OWASP API Security Top 10 — in its read face, *excessive data exposure*. Reading it as BOLA points you at the wrong place: the object-level ownership check is present and *correct* (`GET /users/alice` is `403`), and the flaw is not that it is wrong but that authorization never descended to the fields the response serializes. The impact is **information disclosure** — internal schema recon (a named `is_admin`, a named `passwordHash`) and an exposed credential artifact (a password hash that, in a real system, enables offline cracking), not privilege escalation (`is_admin` comes back `false`, and nothing writes it) and not cracking here (the login is passwordless and the hash is dummy). Like the rest of the series, the bug lives in `app.ts` and doesn't `grep`: there is no dangerous string to find. You catch it by reading what each handler returns and asking, of each field, *is this one the caller is allowed to see?* — and noticing, here, that a correct ownership check was quietly mistaken for the whole of authorization.
