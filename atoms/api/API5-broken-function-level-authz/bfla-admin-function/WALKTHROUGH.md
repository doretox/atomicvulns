# Walkthrough — bfla-admin-function

## 1. Context

An admin API serves `POST /admin/users/:handle/promote`, which grants the admin role to the account named in the path. It authenticates the caller with a Bearer token and then performs the promotion without checking that the caller is an admin. That is **BFLA (Broken Function Level Authorization)** — **API5:2023** in the OWASP API Security Top 10. **Function-level authorization** is the check that asks whether the caller may invoke an operation at all, whatever it operates on; without it, a plain member runs an administrator's function, which is **vertical privilege escalation** — reaching a capability above your own privilege level.

This is where the series changes axis. The three API1 atoms asked about the **instance**: *is this object yours?* in `bola-sequential-id` and `bola-uuid-leaked`, *does it belong to this store?* in `bola-nested-resource`. This atom asks about the **capability**: *may you invoke this operation?* — and the vulnerable build never asks.

The admin path is simply known — admin routes follow predictable names, OpenAPI specs (machine-readable descriptions of an API's routes) are often public, and front-end bundles ship paths for screens a member never sees — so finding the endpoint is not the challenge; invoking it without the role is. You are `clancy`, a plain member. By the end you will have run the admin-only function with your own valid token, on someone else's account and on your own.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it). If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts). The vulnerable handler is short:

```ts
app.post("/admin/users/:handle/promote", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  // VULNERABLE: the caller is authenticated, but the handler never checks the caller's
  // ROLE. Promoting a user to admin is an admin-only function; here ANY authenticated
  // user can invoke it. Authenticated is not authorized to PERFORM this operation.
  const target = USERS.get(req.params.handle);
  if (!target) return res.sendStatus(404);                  // unknown target user
  target.is_admin = true;                                   // state change -- not a read
  res.json({ handle: req.params.handle, is_admin: true });
});
```

Read it twice. It calls `authenticate()`, so a missing or invalid token is rejected with `401`, and from the next line on the request is *genuinely authenticated* — the handler even holds the result in `caller`. Then it looks up the target, sets its `is_admin` to `true`, and answers. The bug is **what isn't there**: nothing compares the caller's role to the role this function requires. Past the `401` line, `caller` is never read again.

- **The audit question is new.** In the API1 atoms the question was about the object: "where does this check that the caller owns the order?" in `bola-sequential-id` and `bola-uuid-leaked`, "where does this check that the order belongs to the authorized store?" in `bola-nested-resource`. Here there is no object to ask about. The question is **"where does this endpoint check that the caller may invoke this function?"** — and the answer is nowhere.
- **It calls `authenticate()`, and that is exactly what disarms a hurried reviewer** — "there's auth on the endpoint, looks fine." It is the trap of the API1 atoms on a new axis. There, the handler knew who you were and never tied the object to you — to its owner, or to the store you were authorized for. Here it knows who you are and never checks what you are allowed to do.
- **This class doesn't `grep`.** There's no dangerous string to search for — no template sink, no `eval`, no concatenated query. You find it by reading each privileged operation and asking where it checks the caller's role.

## 3. How auth works in this lab

`POST /login` takes a username and returns an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It asks for no password: that is a deliberate lab shortcut, not part of the bug. The token is *opaque* — a value that carries no readable structure, unlike a JWT (JSON Web Token) whose payload you could decode — so there is nothing inside it to inspect or tamper with anyway.

Two things to hold in mind before you start:

- **Authentication is genuinely enforced.** A missing or invalid token gets `401`. You'll confirm this in Step 3.
- **Whether the caller's role is checked to authorize the *function* is a separate question** — and the vulnerable handler never asks it. Each user in the seed carries one role flag, `is_admin`; that flag is what the missing check should have read.

You can see `clancy` is a plain member in the seed — `["clancy", { is_admin: false }]` in `app.ts` — and the fixed build confirms it from the outside: the same call there is refused `403`. The vulnerable build never says so, because it never checks.

One discipline for the whole walkthrough: **the attack never touches the token.** You don't decode it, alter it, or forge it — you log in as yourself and send the token exactly as issued. It stays valid and `clancy`'s from start to finish. The target is the function, not the token.

## 4. Baseline — log in as a plain member

Point Burp at the vulnerable API on `127.0.0.1:8204` and work from Repeater.

> **The token below is from one real session.** `POST /login` mints a fresh random token each time, so **yours will differ** — copy your own from the login response into the `Authorization` header. The handles are stable (seeded), so those you can paste verbatim.

Log in as yourself, `clancy`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8204
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, a token that is yours for the rest of the session (shown as `<clancy-token>` below):

```json
{"token":"ylZa7AnzAM7czgZ0tjYZVGjGVN8eJw-j"}
```

That is the whole baseline. The API authenticates `clancy` perfectly; he simply isn't an admin. There is no read route to show a scope here — the surface is two routes, and the other one is the admin function you call next.

## 5. Step 1 — Run the admin function as a plain member (BFLA confirmed)

Ask the admin function to promote `alice`, another plain member, with your own unchanged `<clancy-token>`. The target goes in the path; there is no body:

```
POST /admin/users/alice/promote HTTP/1.1
Host: 127.0.0.1:8204
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"handle":"alice","is_admin":true}
```

You invoked an **admin function** — granting the admin role to an account — as a **plain member**, with your own valid token. The account it acted on is not yours, and you have no relationship with `alice`; what explains the success is not an object of yours and not a forged identity, but that **the function itself was unprotected**. That is the **BFLA**, and it is **vertical** escalation: you exercised a power above your level, rather than reading a peer's data. Nothing here is a payload; the request is valid by every protocol rule, a WAF (web application firewall) sees nothing wrong, and authentication "passed."

**The response is not an object read.** The body holds only what the operation wrote: the `handle` is the one you put in the path, and `is_admin: true` is a literal the handler always returns, whatever the target. There is no name, no address, no private record of `alice` in it — that she is a plain member is something you read in the seed, not in the response. That is deliberate: this admin function changes state instead of returning someone's data, so nothing comes back that you could mistake for "I read what wasn't mine" — the BOLA reflex the API1 atoms trained. The write is real, but no route reads a role back, so from outside the `200` tells you only that the function ran.

Note what the function never asked about `alice`: anything beyond whether the handle exists. It would take any target, and Step 2 proves it with the limit case.

## 6. Step 2 — Promote yourself: the target doesn't matter

Same token, same function; this time the target is your own handle:

```
POST /admin/users/clancy/promote HTTP/1.1
Host: 127.0.0.1:8204
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"handle":"clancy","is_admin":true}
```

The endpoint promoted a stranger in Step 1 and promotes you now, with the same indifference. Whose account the target is never enters the decision. That indifference to the target is the signature of BFLA, and the sign that the axis under attack is **the operation**, not the instance.

## 7. Step 3 — What the vuln is NOT

The exploit is a legitimate request with a legitimate token, so it is easy to misread. Two steps pin down the real cause.

**(a) It is not about whose object it is.** Read the Step 2 request the BOLA way. If this flaw were about reaching an object beyond your scope, nothing would be wrong there: the record is `clancy`'s own, and he is touching only himself. And still the call should never have been allowed, because **promoting is an admin function**, whoever the target is. That request is unimpeachable as an object access and it is still the flaw — so the axis is not the object.

**(b) It is not an authentication failure.** Send the Step 1 request with **no `Authorization` header** at all:

```
POST /admin/users/alice/promote HTTP/1.1
Host: 127.0.0.1:8204
```

Response — **`401`**, body `Unauthorized`. Authentication works: with no identity, the function doesn't run. (Corrupt the token by changing or adding a character and you get `401` too.) You were authenticated as `clancy`, correctly and continuously, in Steps 1 and 2 — this is not broken identity and not impersonation.

Hold (a) and (b) together. Authentication is present and working: the server knows exactly who is calling. The object is irrelevant: the flaw is just as present on your own record. What's missing sits between knowing who you are and running the operation — the check that the caller holds the role the function requires. That is BFLA: not BOLA, not broken authentication.

> **The endpoint never cared whose account the target was, because the flaw was never about the target — it was about who is allowed to run the function at all.**

## 8. Why the fix works (port 8304)

Point Burp at the fixed API on `127.0.0.1:8304` and log in there as `clancy` — each build keeps its own token map and its own seed, so you need a fresh token, and nothing you did on 8204 carries over. Then replay your chain from Steps 1 and 2. It stops at its first request:

- `POST /admin/users/alice/promote` with your `<clancy-token>` → **`403`**, body `Forbidden`. The handler now checks the caller's role right after authenticating and refuses there: the target lookup and the write below it never run, so `alice` is never promoted.

Nothing further in the chain gets through:

- `POST /admin/users/clancy/promote` → **`403`** as well. Promoting yourself is refused for exactly the same reason, because the target was never part of the question.
- `POST /admin/users/nobody/promote`, a handle that was never seeded → **`403`**, not `404`. The role check runs before the target is looked up, so a non-admin learns nothing about which accounts exist.

The function still works for whoever may run it. Log in on 8304 with `{"user": "carol"}` — `carol` is the seeded admin — and promote `bob` with her token:

```
POST /admin/users/bob/promote HTTP/1.1
Host: 127.0.0.1:8304
Authorization: Bearer <carol-token>
```

Response — `200`:

```json
{"handle":"bob","is_admin":true}
```

The fix didn't break the feature; it restricted who can invoke it. No token or a bad token still gets `401`.

**`403`, not `404`.** The API1 atoms answer `404` for an order outside your scope; here the non-admin gets an honest `403`. The endpoint is known by premise, so there is no existence to hide, and `403` tells the truth: you are authenticated, and your role is not enough for this operation. [`DIFF.md`](./DIFF.md) carries the full argument — RFC 9110 §15.5.4, the series' single criterion for choosing between the two, and why the enumeration-oracle argument (a difference in responses that would let an attacker map which ids exist) behind the order `404` in `bola-sequential-id` and `bola-nested-resource` doesn't apply to a known function.

## 9. Impact — a role flag anyone can write

The impact is proved by the two builds together, each showing the half that is true in it.

- **The vulnerable half: anyone can write the flag.** It is already on the table, with no new request. In Steps 1 and 2, `clancy`, a plain member, set `is_admin: true` on `alice` and on his own record — on whichever account he named, himself included.
- **What the vulnerable build cannot show: that the flag is worth anything.** No role is checked anywhere in it — `is_admin` is written and never read — so no response from 8204 changes because of those writes, and this walkthrough doesn't pretend one does.
- **The fixed half: the flag governs the function.** Set the two requests from the previous section side by side: `carol` promoting `bob` gets `200`, `clancy` promoting `alice` gets `403`. The role check runs before the target is looked up, so the target takes no part in the decision; the only thing separating the `200` from the `403` is the caller's `is_admin`. In the fixed build, that flag decides who may run the function.

Put the halves together: **the role flag is what governs the admin capability, and in the vulnerable build any authenticated member can write it** — for any account, his own included. That is the vertical privilege escalation, proved without a single extra route.

The walkthrough ends here. The finding is a plain member running an admin-only function with his own valid token, on any account he names; the fix is one role check, placed ahead of the target lookup. To go deeper on the class, the theory primer's PortSwigger page is the place.
