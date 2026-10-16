# Walkthrough — bopla-mass-assignment

## 1. Context

A profile API serves `PATCH /users/:handle`: it authenticates the caller with a Bearer token, checks that the record is the caller's own, and updates it. The ownership check is right — you can write only your own profile — but the handler then merges the **whole request body** into the stored record, so any property the body names is set, including one the profile form never offered: `is_admin`. That is **BOPLA (Broken Object Property Level Authorization)** — **API3:2023** in the OWASP API Security Top 10 — in its write face, what the industry calls **mass assignment** (also *auto-binding*): the handler binds request properties straight onto the internal object, so the request ends up able to set fields the developer never meant to expose. **Property-level write authorization** is the access check applied to each field a request is allowed to change, below the object as a whole.

This is the second atom at the **property** grain, and the mirror of the first. Its sibling `bopla-excessive-exposure` asked: *does the response return only the fields you may **see**?* This one asks: *may the request **set** only the fields you may write?* Same root — trusting a whole object — pointed in the opposite direction.

One thing to settle before you start, because the whole atom turns on it: **the write will not tell you whether it worked.** `PATCH` answers `204 No Content` here, in both builds, with nothing in the body. You will prove the effect by reading the state somewhere else.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it). If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts). The one handler to read is `PATCH /users/:handle`:

```ts
app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  // VULNERABLE: the ownership check above is right -- this IS your record. But the write
  // merges the WHOLE request body into the record, so every property the body names is set,
  // is_admin included. Authorization applies to each property written, not only to the object.
  USERS.set(req.params.handle, { ...user, ...req.body });
  res.sendStatus(204);                                           // no content: nothing to echo back
});
```

The asymmetry is **inside one handler**. The ownership check (`if (req.params.handle !== caller) return res.sendStatus(403)`) is present and correct — it lets you write only your own record. One line below it, `USERS.set(req.params.handle, { ...user, ...req.body })` builds the new record by spreading the stored one and then **the entire request body** over it. Whatever the body names wins. The record carries two fields — `displayName` and `is_admin` — and the body can set either. So the audit question here is not BOLA's *"where does this check the caller owns the object?"* (it does, and it passes), and not BFLA's *"may the caller invoke this operation?"* — it is **"is the write scoped to the fields this caller may set?"** The answer: no.

- **The mirror of the sibling atom, in the code itself.** In `bopla-excessive-exposure` the offending line was `res.json({ handle, ...user })` — the whole record going **out**. Here it is `USERS.set(handle, { ...user, ...req.body })` — the whole body coming **in**. One object crosses the boundary unexamined; only the direction changed.
- **This class doesn't `grep`.** There is no dangerous string to search for. You find it by reading what each handler writes and asking whether every property it can set is one the caller is allowed to control.

## 3. How auth works in this lab — and the admin door, already guarded

`POST /login` takes a username and returns an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It asks for no password: that is a deliberate lab shortcut, not part of the bug. The token is *opaque* — a value carrying no readable structure, unlike a JWT (JSON Web Token) whose payload you could decode — so there is nothing inside it to inspect or tamper with anyway.

Two things to hold in mind:

- **Authentication is genuinely enforced.** A missing or invalid token gets `401` with a `WWW-Authenticate: Bearer` challenge, on all three routes.
- **Ownership is checked, and it passes for your own record.** `req.params.handle === caller` lets you write the record keyed by your handle and refuses anyone else's. That check is correct; it is not where the bug is.

One discipline for the whole walkthrough: **the attack never touches the token.** You don't decode it, alter it, or forge it — you log in as yourself and send the token exactly as issued. It stays valid and `clancy`'s from start to finish. Your identity never changes; what will change is the **state** the server reads when it decides what you are allowed to do.

Now meet the instrument you will prove things with. The lab has an administrative route, `GET /admin/users`, and it checks the caller's role before answering. Point Burp at the vulnerable API on `127.0.0.1:8207`, log in as yourself, and knock on that door first.

> **The token below is from one real session.** `POST /login` mints a fresh random token each time, so **yours will differ** — copy your own from the login response into the `Authorization` header. The handles are stable (seeded), so you can paste those verbatim.

> `Method: POST · Logging in as: clancy (you)`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8207
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, a token that is yours for the rest of the session (shown as `<clancy-token>` below):

```json
{"token":"S2_AYQTHKg0bsER7kLkXKFMCDOu8YSrw"}
```

> `Method: GET · Target: /admin/users · Isolates: the admin function is guarded — and you are not an admin`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
```

Response — **`403`**, body `Forbidden`.

**Read that `403` carefully, because it is half the lesson.** The admin route asked the right question — *is this caller an administrator?* — and refused you. The function **is** protected, in the vulnerable build, right now. Keep this result; Step 4 comes back to it.

One design note while you are here: there is no route that reads your own record back. The admin door is the only window onto the state, and that is on purpose — what matters is not seeing the field, it is seeing what the field *does*.

## 4. Exploit — three movements, and the `204` is not the proof

**Movement one — the write.** Send the profile update the feature offers, and add one key the form never had:

> `Method: PATCH · Target: clancy (yours) · Isolates: a field the profile form never offered goes in beside the one it did`

```
PATCH /users/clancy HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "Clancy Parked", "is_admin": true}
```

Response — **`204 No Content`**, and the body is empty. Not `{}` — empty: no `Content-Type`, no `Content-Length`, nothing.

**Do not read that as success at setting `is_admin`.** A `204` says the server carried out the request; it says nothing about *what* it wrote. The fixed build answers this exact request with this exact `204` and writes nothing of the sort. If you stop here, you have learned nothing — and that trap is the reason this atom exists.

**Movement two — the proof.** Go back to the door that just refused you, with the same token, unchanged:

> `Method: GET · Target: /admin/users · Isolates: the door that answered 403 in Step 3 now opens`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
```

Response — **`200`**:

```json
["clancy","alice"]
```

Same request, same token, same guard — and the opposite answer.

**Movement three — name the effect.** You forged `is_admin` through a profile update, and the privileged function now accepts you. Note precisely what happened and what did not: the admin route did not fail, break, or get bypassed. It asked whether you are an administrator, read the answer from the store, and the store now says yes — because the `PATCH` put it there. The body of that `200` is not the prize; it is two handles you already knew. The prize is the **status**: a function that refused you now serves you.

That is the technique worth keeping from this atom, beyond the bug itself: **an observable effect is proved by reading the state through another path, never by the write's own answer.**

> **A write that answers `204` proves nothing about what it wrote — the proof was the admin door: `403` a minute ago, open now.**

## 5. Step — What the vuln is NOT

A legitimate request, with a legitimate token, writing a record you own, is easy to misread. Two readings to take apart firmly, and a third worth a sentence.

**"This is BOLA — I wrote something that wasn't mine."** It isn't. Try the other seeded account with your own token:

> `Method: PATCH · Target: alice (not yours) · Isolates: ownership exists and bites — you only write your own record`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"is_admin": true}
```

Response — **`403`**, body `Forbidden`. Alice's record is untouched. The object-level authorization is present and correct: you did **not** write someone else's object — you wrote your **own**. The problem is not which object the write reached; it is **which field** the write accepted. (This is the same ownership guard `bfla-method-based` uses, compared before any lookup — [`DIFF.md`](./DIFF.md) points at the full status-code argument.)

**"This is BFLA — I invoked an admin function I shouldn't have."** This is the misreading to kill, and the evidence is already in your hands. Go back to Step 3: that same route, with that same token, answered **`403`**. Its guard was there, it asked the right question, and it refused you. It is still asking the same question now — nothing about the route changed between the `403` and the `200`, and nothing in the fixed build changes it either, where this route is **byte-identical**. What changed is the answer the store gives it.

Hold the two cases apart, because they are different bugs with the same door:

- In **BFLA** — the `bfla-admin-function` atom — the privileged function has **no role check at all** (or the wrong one), so an ordinary member walks in. The fix is to add the check.
- Here the check **exists, is correct, and works**. Nobody walked past it. The caller satisfied it, because the caller wrote the very role it consults. **The guard you can see is right; the breach is upstream, in the `PATCH`.**

If you go looking for the bug in `GET /admin/users`, you will not find it — there is nothing wrong there.

**A third, smaller misreading: "it's just a field echoed back at me."** Nothing came back at all — the write answered `204` with an empty body. What was demonstrated was a privilege, not a value in a response.

Put it together. You are **fully authorized for the object** (it is your record, and ownership approves), and the privileged function is **correctly guarded** (its `403` proved that before you touched anything) — and you still became an administrator. The flaw is not writing a foreign object (not BOLA), not an unprotected function (not BFLA), and not an echo. It is the write **accepting too many properties**.

## 6. Step — Impact

**Privilege escalation, real and verified.** `clancy` starts as `is_admin: false`, no administrator exists in the seed at all, and one profile update makes him one. The administrative access is not inferred from the write's response — it is demonstrated by the route that refused him a minute earlier and now answers. In a real system, that one extra key in the body is the distance between an ordinary account and the admin console.

The honest contrast with the sibling atom: in `bopla-excessive-exposure` the same `is_admin` field leaked **outward** with the value `false`, and the impact was reconnaissance — nobody became an admin. Here the same field is written **inward**, and the impact is escalation you can verify. One field, two faces of one category.

What the impact is **not**:

- **Not a data breach.** The `200` returns `["clancy","alice"]` — handles, no record fields. Nothing sensitive left the server; the admin route is deliberately thin.
- **Not an authentication bypass.** The token is the same legitimate token throughout; it was never forged, replayed, or decoded.
- **Not bigger than it is.** The administrator in this lab can list handles, and that is all the atom needs. The finding is the *access*, not what sits behind the door.

## 7. Why the fix works (port 8307)

Point Burp at the fixed API on `127.0.0.1:8307` and log in there as `clancy` — each build keeps its own token map, so you need a fresh token. Then run the **same three requests**, in the same order.

First the baseline:

> `Method: GET · Target: /admin/users · Isolates: same starting point — you are not an admin here either`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8307
Authorization: Bearer <clancy-token>
```

Response — **`403`**, body `Forbidden`. Same as the vulnerable build.

Then the write that escalated you before:

> `Method: PATCH · Target: clancy (yours) · Isolates: the identical request, the identical response`

```
PATCH /users/clancy HTTP/1.1
Host: 127.0.0.1:8307
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "Clancy Parked", "is_admin": true}
```

Response — **`204 No Content`**, empty body. **Identical.** The fixed build gives you nothing to distinguish it by: not the status, not the body, not a header.

Then the door:

> `Method: GET · Target: /admin/users · Isolates: the thermometer that does not move`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8307
Authorization: Bearer <clancy-token>
```

Response — **`403`**, body `Forbidden`.

**Same write, same status, dead effect.** The fixed handler names the one field a caller may set — an **allow-list** — so the `displayName` you sent was written and the `is_admin` was simply not part of the write. The feature still works; the escalation is gone. And notice what the fix did *not* touch: the ownership check still answers `403` for `PATCH /users/alice`, a missing or bad token still gets `401` with `WWW-Authenticate: Bearer`, and `GET /admin/users` is the same bytes it always was.

The single line between the two builds is what the handler writes. [`DIFF.md`](./DIFF.md) works through it — why an allow-list (which fails closed) is the fix and a deny-list (which fails open) is not, why `204` is the right status for a write whose response should prove nothing, and why these other status codes follow the series' criterion.

The walkthrough ends here. The finding is a privilege flag set through an ordinary profile update you were fully authorized to make; the fix is one line, naming the field the write may carry.
