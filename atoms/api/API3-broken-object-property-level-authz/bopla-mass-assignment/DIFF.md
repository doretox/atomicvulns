# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ in exactly one place — the line that writes the record in `PATCH /users/:handle`, plus the comment above it. `POST /login`, the authentication helpers, the ownership guard, the `USERS` seed, the `TOKENS` map, the imports, the `204` that ends the handler, the entire `GET /admin/users` route, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). The change is one write projection.

## The fix — an allow-list on the write, not the request body

```diff
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);
-  // VULNERABLE: the ownership check above is right -- this IS your record. But the write
-  // merges the WHOLE request body into the record, so every property the body names is set,
-  // is_admin included. Authorization applies to each property written, not only to the object.
-  USERS.set(req.params.handle, { ...user, ...req.body });
+  // FIXED: the write names the one field the caller may set -- an allow-list, not the request
+  // body. is_admin is not in the list, so a body that carries it changes nothing; a field added
+  // to User later stays caller-unwritable until someone deliberately names it here.
+  USERS.set(req.params.handle, { ...user, displayName: typeof req.body?.displayName === "string" ? req.body.displayName : user.displayName });
   res.sendStatus(204);                                           // no content: nothing to echo back
```

Both twins call the same `USERS.set` on the same base record (`...user`). What differs is **who decides the rest of the object**. In the vulnerable line, `...req.body` lets the request decide: every property the body names is written, so `{"is_admin":true}` lands as surely as `{"displayName":"..."}`. In the fixed line the handler decides: one field is named, and nothing else can reach the record whatever the body carries.

**Read the fix for what it authorizes.** The handler already authorized the **object**: the ownership guard one line above (`if (req.params.handle !== caller) return res.sendStatus(403)`) makes sure this record is the caller's own. What it never did was authorize the **properties** that the write sets. The fix extends authorization down to the field grain on the write side: it decides, explicitly, which properties a request may change. That is the whole of BOPLA's write face — authorization is owed not only to the object but to each field written into it.

> **The vulnerable handler asks the request which properties to write; the fixed one already knows — and `is_admin` was never among them.**

A note on the `typeof` test in that line: `req.body` is `any`, so without it a body like `{"displayName": {"x": 1}}` would store a non-string in a field typed `string` — a lie about the record's shape that TypeScript cannot catch at a JSON boundary. Naming the field *and* accepting only its type is the honest minimum of "only this may come in"; it is part of naming the field, not a separate lesson about input validation.

## Allow-list, not deny-list — fail closed, not fail open

An allow-list is not the only write projection that stops today's attack. A deny-list would also work *today*:

```ts
// CONSIDERED AND REJECTED -- a deny-list on the write: strip the known-bad field from the body.
const { is_admin, ...rest } = req.body ?? {};
USERS.set(req.params.handle, { ...user, ...rest });
```

It removes `is_admin` from the body, and the escalation in the walkthrough does not happen. But it **fails open**: the day someone adds a second privileged field to `User` — an `is_staff`, a `plan`, a `creditBalance` — that field becomes writable on its own, because nobody remembered to add it to the deny-list. The allow-list **fails closed**: a new field stays caller-unwritable until someone deliberately names it in the write.

The difference is not stylistic — it is the direction a mistake runs. Add a privileged field and forget to touch the handler:

| Write projection | today (`{"is_admin":true}`) | tomorrow (`{"is_staff":true}`) |
|---|---|---|
| **spread** (`...req.body`) — the vulnerable build | writes `is_admin` | **also writes** `is_staff` |
| **deny-list** (`const {is_admin, ...rest} = req.body`) | blocks `is_admin` | **writes** `is_staff` (fails open) |
| **allow-list** (`displayName` named) — the fix | blocks | **still blocks** (fails closed) |

At scale this projection becomes an **input schema** — an update DTO (Data Transfer Object), a declarative validator — defining in one place which fields each role may write, rather than an object literal inlined in the handler. That is the same idea one grain larger; this atom keeps it to the one line so the diff stays on the lesson.

## The write is the request's shape, until it isn't

`USERS.set(req.params.handle, { ...user, ...req.body })` reads as "update the record with what the client sent," and that is exactly the trap: it writes *everything the client happened to send*, not what the caller is cleared to change. The two were the same object only because nobody decided otherwise. `...user` carries the stored record in as the base, and `...req.body` pours the request over it — last writer wins, and the request is always last. The fixed handler breaks that accident apart: the new record is built from a deliberate list, and a property reaches the store only if the list names it.

One behaviour worth recording, because it is the question an attentive reader asks of any object merge in Node: a body of `{"__proto__":{"polluted":1}}` **does not** pollute `Object.prototype` here — both `JSON.parse` and object spread create the key as an own data property, so it lands as an inert field on the record and the global prototype is untouched (verified against the running container: `({}).polluted` stays `undefined`, `Object.keys({})` stays empty, and the admin route keeps answering `403`).

*(On the types: `USERS.get(req.params.handle)` is `User | undefined` from `Map.get`'s own signature, so the `if (!user)` guard is kept byte-identical in both twins. It is only **type-forced** in the fixed build, where `user.displayName` dereferences `user` inside the ternary; in the vulnerable build the `any` that `req.body` carries washes out the type of the whole object literal, so the compiler accepts the write even without the guard — the same looseness that makes the bug possible also silences the check on it. Either way the guard is unreachable at runtime: the ownership guard above only lets through the caller's own, always-seeded handle.)*

## The admin route is identical in both builds — and that is the point

`GET /admin/users` does not appear in this diff. It is the same bytes in `vulnerable/` and `fixed/`:

```ts
app.get("/admin/users", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
  res.json([...USERS.keys()]);   // handles only -- no record fields in the body
});
```

That guard is **correct**, and it is worth being precise about why, because the route is where the exploit becomes visible and it would be easy to blame it. The predicate asks one question — *is the caller an administrator?* — and it answers from `USERS`, the store, not from the token. In the vulnerable build it refuses `clancy` with `403` before the write and admits him with `200` after it; in the fixed build it refuses him both times. The route never changed its mind about anything: the store changed underneath it.

That line is, byte for byte, the role check that `bfla-admin-function` adds as its *fix* — the atom whose whole lesson is a privileged function with no role check at all. Here the function has one, it works, and the caller still gets in, because he wrote the role the check consults. **The guard you can see is right; the breach is upstream, in the `PATCH`.** The two bugs share a door and nothing else: BFLA is a function that doesn't ask, this is a function that asks and is answered with a forged role. Looking for the flaw in this handler will find nothing, and that is by design.

Two smaller choices in that route, both deliberate: it is **read-only**, so it can be used as an instrument without changing what it measures; and it serializes **handles only** — never a record field — so proving the escalation never depends on the response leaking anything.

## Status codes — 204 is new here, 403 and 401 are inherited

**The write answers `204 No Content` — in both twins — and that is a design decision, not a shortcut.** RFC 9110 (HTTP Semantics) §15.3.5 defines `204` as the server having successfully fulfilled the request with no additional content to send, and is explicit that "a 204 response is terminated by the end of the header section; it cannot contain content." It is the one success status that *cannot* echo. That is precisely why this atom uses it: a response body on a write is the attacker's own input coming back, and mistaking it for proof is the most expensive misreading in this class. With `204`, both builds answer identically and neither tells you what it stored, so the only way to learn the effect is to read the state through another route.

This diverges, on purpose, from `bfla-method-based`, whose `PATCH` answers `200` with a JSON body — and whose [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md) spells out that the body is the caller's echoed input and proves nothing about the stored record. This atom takes that conclusion and puts it in the status line: if the echo cannot prove it, let there be no echo.

The rest is inherited and not re-argued here:

- **A foreign write → `403`.** `PATCH /users/alice` with `clancy`'s token is refused by the ownership guard, which compares the path handle to the caller **before any lookup** — so it reveals no existence and is no enumeration oracle. Same guard, same reasoning as `bfla-method-based`; its [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md) carries the full account, RFC 9110 §15.5.4 and the series' single criterion for `403` vs `404`.
- **A missing or invalid token → `401`** with a `WWW-Authenticate: Bearer` challenge (RFC 9110 §15.5.2); the `403` carries none, because the caller is already authenticated. Also inherited; see the same [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md).
- **The non-admin `403` from `GET /admin/users`** is the same honest refusal: credentials present, considered insufficient for this function, whose existence is a premise rather than a secret.

The one `404` in the `PATCH` (`if (!user)`) is unchanged in both twins and unreachable at runtime, because the ownership guard only admits the caller's own seeded handle — `PATCH /users/nobody` answers `403`, not `404`.

## This is BOPLA — authorization on a property you write

Nothing the caller sends is parsed or executed. A legitimate request, under a legitimate token, updates the caller's **own** record — correctly authorized at the object level — and the write accepts a property the caller was never allowed to control. That is Broken Object Property Level Authorization — **API3:2023** in the OWASP API Security Top 10 — in its write face, *mass assignment*. Reading it as BOLA points you at the wrong place (the ownership check is present and correct — `PATCH /users/alice` is `403`); reading it as BFLA points you at the wrong handler (the admin route's role check is present and correct — it refused the same caller minutes earlier). The flaw is that authorization never descended to the fields the write sets. The impact is **privilege escalation**, verified rather than assumed: no administrator exists in the seed, and the bug makes one. Like the rest of the series, the bug lives in `app.ts` and doesn't `grep`: there is no dangerous string to find. You catch it by reading what each handler writes and asking, of each property, *is this one the caller is allowed to set?* — and noticing, here, that a correct ownership check was quietly mistaken for the whole of authorization.
