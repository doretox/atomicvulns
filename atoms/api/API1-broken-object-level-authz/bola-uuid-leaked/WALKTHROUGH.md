# Walkthrough — bola-uuid-leaked

## 1. Context

A small e-commerce **orders API** serves one order through `GET /orders/:id`, authenticating the caller with a Bearer token but never checking whose order it is. That is **BOLA (Broken Object Level Authorization)** — the #1 risk in the OWASP API Security Top 10 (**API1:2023**), and the API-shaped face of IDOR (insecure direct object reference). Here the order id is a **UUID (Universally Unique Identifier) v4** — a 128-bit random value — not a small integer.

The premise, in one sentence: **the UUID of one of alice's orders has reached you through a channel outside the app** — a support call, a screenshot, a shared link — the way ids circulate in the real world. The application leaks no id of its own; you simply *hold* one that isn't yours. You are `dana`, and you own exactly one order. By the end you will have read the personal data on an order you don't own, using your own valid token and a UUID you were handed.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it) or, later, drive from **Burp Intruder** (which replays one request across a list of values). If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts). The vulnerable handler is short:

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  const order = ORDERS[req.params.id];                      // string key (UUID) -- no Number() coercion
  if (!order) return res.sendStatus(404);
  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
  // order.owner is the caller. Authenticated is not authorized for THIS object.
  res.json(order);                                          // BOLA -- no object-level check
});
```

Read it twice. It calls `authenticate()`, so a missing or invalid token is rejected with `401`, and by the time you reach `res.json`, the request is *genuinely authenticated*. Then it looks the order up by id and returns it. The bug is **what isn't there**: no comparison between `order.owner` and `caller`. The handler trusts that "if you're logged in and you asked for order X, you may see order X" — and it treats holding the UUID as proof you may. It isn't.

Two things worth internalizing from this shape:

- **It calls `authenticate()`, and that is exactly what disarms a hurried reviewer** — "there's auth on the endpoint, looks fine." But authenticating and authorizing are different questions. This handler *resolves* the caller — it even stores the result in `caller` — and then asks nothing about whether the order is theirs. Now look at the list endpoint in the same file: `GET /orders` filters `ORDERS` by `o.owner === caller`. The developer clearly *knew* how to scope to the owner; they just didn't do it on the by-id endpoint. **That asymmetry — list scoped, detail unscoped — is the signature of real-world BOLA.** This is the identical handler shape as the companion atom `bola-sequential-id`; the UUID key changed nothing about the bug.
- **This class doesn't `grep`.** There's no dangerous string to search for — no template sink, no `eval`, no concatenated query. You find it by reading each endpoint that returns a user-scoped object and asking "where does this check the caller owns it?" — and here the answer is nowhere.

## 3. How auth works in this lab

`POST /login` takes a username and returns an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It asks for no password: that is a deliberate lab shortcut, not part of the bug. The token is *opaque* — a value that carries no readable structure, unlike a JWT (JSON Web Token) whose payload you could decode — so there is nothing inside it to inspect or tamper with anyway.

Three things to hold in mind before you start:

- **Authentication is genuinely enforced.** A missing or invalid token gets `401`. You'll confirm this in Step 2.
- **Whether that authenticated identity is used to *authorize* a specific object is a separate question** — and the vulnerable `/orders/:id` doesn't use it. That gap is the bug.
- **The UUID is the *order id*, not the token.** The attack never touches the token: you don't decode it, alter it, or forge it — you log in as yourself and send the token exactly as issued. What is a UUID here is the object identifier in the path; that is the axis under test.

## 4. Baseline — capture your token and see the correct scope

Point Burp at the vulnerable API on `127.0.0.1:8202` and work from Repeater.

> **The token below is from one real session.** `POST /login` mints a fresh random token each time, so **yours will differ** — copy your own from each login response and use it in the `Authorization` header. The order UUIDs are stable (hardcoded in the seed), so those you can paste verbatim.

Log in as yourself, `dana`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8202
Content-Type: application/json

{"user": "dana"}
```

Response — `200`, a token that is yours for the rest of the session (shown as `<dana-token>` below):

```json
{"token": "owYzeYEn_oJ89HfQ0IRQy6tIrfxFOSXc"}
```

Now list your own orders with your token:

```
GET /orders HTTP/1.1
Host: 127.0.0.1:8202
Authorization: Bearer <dana-token>
```

Response — `200`, and note it contains **only your one order**:

```json
[{"id":"edec4558-0cf5-4462-aaba-308229ff6c4f","owner":"dana","customer":"Dana Lee","address":"3 Testing Blvd, Faketon","item":"Wireless mouse","amount":"$29.90"}]
```

That single item is the proof the API **knows exactly who you are** and scopes you correctly. Read it back to confirm the feature works — `GET /orders/edec4558-0cf5-4462-aaba-308229ff6c4f` with your Bearer returns `200` and your own order. And notice what your list does **not** give you: it hands you only *your* UUID, and one UUID says nothing about any other. Unlike a sequential counter, where seeing `1007` tells you `1006` and `1008` exist, this list gives you zero leverage on anyone else's id. The app volunteers nothing.

One legitimate cross-check for later. In this lab you also control alice's login, so log in as her and read the leaked order with **her** token — this is what *authorized* access to it looks like:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8202
Content-Type: application/json

{"user": "alice"}
```

```
GET /orders/376d2491-7bc1-44ea-b1f2-81cf7a34af58 HTTP/1.1
Host: 127.0.0.1:8202
Authorization: Bearer <alice-token>
```

Response — `200`, alice's order. Keep it next to you; in the next step the exact same object comes back to *your* token. (In a real engagement you wouldn't have alice's token — only the leaked id and your own token. This login is just the lab's way of showing the authorized baseline.)

## 5. Step 1 — Read the leaked order (BOLA confirmed)

You were handed, from outside the app, the UUID of one of alice's orders: `376d2491-7bc1-44ea-b1f2-81cf7a34af58`. You did **not** guess it and you did **not** reconstruct it — it *leaked* (a support call, a screenshot, a shared link).

Ask for it with your own, unchanged `<dana-token>`:

```
GET /orders/376d2491-7bc1-44ea-b1f2-81cf7a34af58 HTTP/1.1
Host: 127.0.0.1:8202
Authorization: Bearer <dana-token>
```

Response — `200`:

```json
{"id":"376d2491-7bc1-44ea-b1f2-81cf7a34af58","owner":"alice","customer":"Alice Nguyen","address":"12 Example Ave, Springfield","item":"Mechanical keyboard","amount":"$89.00"}
```

You read another user's order — **with their name and delivery address** — using your own valid token, supplying an id that isn't yours. That is the **BOLA**. Nothing here is a payload; the request is valid by every protocol rule, a WAF (web application firewall) sees nothing wrong, and authentication "passed." Authorization for the object was simply never consulted. The random UUID protected nothing: the instant you *held* a valid id, the missing check served it.

Look at what just happened across two requests. That same `376d2491-…` came back `200` to `<alice-token>` in the baseline *and* `200` to `<dana-token>` now. The server **resolved two different identities correctly** — `authenticate()` returned `alice` on one request and `dana` on the other — and **handed the same object to both**, because the identity, though known, never enters the access decision. That is exactly where BOLA lives.

## 6. Step 2 — What the vuln is NOT, and the Intruder inversion

The exploit is a legitimate request with a legitimate token, so it is easy to misread. This step pins down the real cause, then names a trap the previous atom sets for you.

**It is not broken identity, and not the id format.** Send `GET /orders/376d2491-…` with **no `Authorization` header** — you get `401`; authentication works. Send `GET /orders` again with your `<dana-token>` — `200`, correctly scoped to your one order. Send `GET /orders/376d2491-…` with that same `<dana-token>` — `200`, alice's order. The same token gives correct scope in one handler and no scope in the other, so this is not impersonation: you were `dana` the whole time, and the list endpoint scoped you correctly. It is a check that *exists* in `GET /orders` and is *missing* in `GET /orders/:id`. The companion atom `bola-sequential-id` walks this auth-versus-authz isolation request by request; the point that matters here is what it could only *assert* and this atom *demonstrates*: a non-guessable id would only make discovery more expensive — it would never put the check back. Here the id genuinely is non-guessable, and the read happened anyway.

Now the trap. In `bola-sequential-id` the impact beat was **enumeration**: send `GET /orders/§id§` to **Burp Intruder** (the tool that replays a request while substituting a value from a list), sweep the contiguous range `1001`–`1012`, and the whole collection falls out. Try the analogous move here — **knowing up front that nobody finds a UUID by brute force** (the space is ~2¹²²; this is to see what happens, not a serious attempt to enumerate):

- **(a)** In Repeater, invent a UUID — say `ffffffff-ffff-4fff-8fff-ffffffffffff` — and send it with your valid `<dana-token>`:

  ```
  GET /orders/ffffffff-ffff-4fff-8fff-ffffffffffff HTTP/1.1
  Host: 127.0.0.1:8202
  Authorization: Bearer <dana-token>
  ```

  Response — `404`. A valid token does not conjure objects, and the app never reveals which UUIDs are real; a blind guess just misses.
- **(b)** Send `GET /orders/§id§` to Intruder and point it at a batch of random UUIDs. Every single one comes back `404` — a flat wall of them, exactly the image `bola-sequential-id` produced when you swept its *fixed* build.

And here is the inversion, stated plainly: in `bola-sequential-id`, a wall of `404` in Intruder meant the app was **fixed** (the ownership check rejecting you). Here the very same wall comes from the **vulnerable** app, and it means only *"I didn't find a real id."* The check is still absent — feed the endpoint the one real id you were handed (`376d2491-…`) and it serves alice's order, PII and all. **The Intruder screen doesn't tell you whether the app is fixed — a wall of 404s is "didn't find," not "nothing to find."**

That the id resists brute force might make you wonder whether "unguessable UUID" is a defense at all — and there is a fair objection worth answering. The web atom `idor-uuid-guessable` shows an attacker *reconstructing* a victim's UUID and reading their record, which looks like a counter-example. It isn't, and the difference is the UUID **version**. Those ids are **UUIDv1**, which embeds the timestamp and the host's MAC address and can be rebuilt from metadata the application itself publishes; the ids here are **UUIDv4**, ~122 bits from a CSPRNG (cryptographically secure pseudo-random number generator) with nothing inside to reconstruct from. The two atoms prove one thesis from opposite ends: a UUID is not automatically unguessable (v1 can be rebuilt), and even when it genuinely is (v4, handed to you from outside), the missing check still serves the object. That atom teaches this as one lesson among several and needs the id to have *been* reconstructible; here the unguessable id is the whole point. Either way, **the id's format fixes nothing — guessable or not.**

So the cause is the absent object-level authorization on the detail route — not the token, not your identity, not whether the id can be guessed. The Step 1 read succeeded through the same missing check as `bola-sequential-id`; the UUID changed only the *cost of discovery* (from trivial to infeasible), not the *access*.

## 7. Why the fix works (port 8302)

Point Burp at the fixed API on `127.0.0.1:8302` and log in there (each build keeps its own token map), then repeat the reads:

- `GET /orders/376d2491-…` (the leaked order) with your `<dana-token>` → **`404`**. The order exists, but it isn't yours, so the ownership guard refuses it.
- `GET /orders/edec4558-0cf5-4462-aaba-308229ff6c4f` (your own order) with your `<dana-token>` → `200`. Owners still read their own orders. Authentication is still enforced: no token or a bad token still gets `401`.
- **`404`, not something that leaks:** the `404` for an order you don't own is byte-for-byte the `404` for an id that was never seeded — `GET /orders/ffffffff-ffff-4fff-8fff-ffffffffffff` returns the same status, body, and length. The fixed build tells a real order and an invented id apart to *nobody*.
- **The fix left the id a UUID.** The patch reshaped nothing about the id, because the id's shape was never the problem — the missing check was. It is the same one-predicate guard `bola-sequential-id` uses, unchanged; [`DIFF.md`](./DIFF.md) sets the two fixes side by side.

The walkthrough ends here. The finding is the cross-user read of a leaked id; the fix is one predicate on one guard. There is nothing left to exfiltrate and no variation worth adding — to go deeper on the class, the theory primer's PortSwigger page is the place.
