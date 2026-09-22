# Walkthrough — bola-sequential-id

## 1. Context

A small e-commerce **orders API** serves one order through `GET /orders/:id`, authenticating the caller with a Bearer token but never checking whose order it is. That is **BOLA (Broken Object Level Authorization)** — the #1 risk in the OWASP API Security Top 10 (**API1:2023**), and the API-shaped face of IDOR (insecure direct object reference): the same missing-check bug as the web atoms `idor-numeric-id` and `bola-rest`, now in TypeScript/Express at the scale of a real collection.

Each order carries the customer's name, delivery address, item, and amount. You are `dana`, and you own exactly one order. By the end you will have read the personal data on all eleven orders you don't own, using your own valid token and changing nothing but the id.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it) or, later, drive from **Burp Intruder** (which replays one request across a list of values). If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts). The vulnerable handler is short:

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  const order = ORDERS[Number(req.params.id)];
  if (!order) return res.sendStatus(404);
  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
  // order.owner is the caller. Authenticated is not authorized for THIS object.
  res.json(order);                                          // BOLA -- no object-level check
});
```

Read it twice. It calls `authenticate()`, so a missing or invalid token is rejected with `401`, and by the time you reach `res.json`, the request is *genuinely authenticated*. Then it looks the order up by id and returns it. The bug is **what isn't there**: no comparison between `order.owner` and `caller`. The handler trusts that "if you're logged in and you asked for order N, you may see order N."

Two things worth internalizing from this shape:

- **It calls `authenticate()`, and that is exactly what disarms a hurried reviewer** — "there's auth on the endpoint, looks fine." But authenticating and authorizing are different questions. This handler *resolves* the caller — it even stores the result in `caller` — and then asks nothing about whether the order is theirs. Now look at the list endpoint in the same file: `GET /orders` filters `ORDERS` by `o.owner === caller`. The developer clearly *knew* how to scope to the owner; they just didn't do it on the by-id endpoint. **That asymmetry — list scoped, detail unscoped — is the signature of real-world BOLA.**
- **This class doesn't `grep`.** There's no dangerous string to search for — no template sink, no `eval`, no concatenated query. You find it by reading each endpoint that returns a user-scoped object and asking "where does this check the caller owns it?" — and here the answer is nowhere.

## 3. How auth works in this lab

`POST /login` takes a username and returns an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It asks for no password: that is a deliberate lab shortcut, not part of the bug. The token is *opaque* — a value that carries no readable structure, unlike a JWT (JSON Web Token) whose payload you could decode — so there is nothing inside it to inspect or tamper with anyway.

Two things to hold in mind before you start:

- **Authentication is genuinely enforced.** A missing or invalid token gets `401`. You'll confirm this in Step 2.
- **Whether that authenticated identity is used to *authorize* a specific object is a separate question** — and the vulnerable `/orders/:id` doesn't use it. That gap is the bug.

One discipline for the whole walkthrough: **the attack never touches the token.** You don't decode it, alter it, or forge it — you log in as yourself and send the token exactly as issued. It stays valid and yours from start to finish. The target is the endpoint, not the token.

## 4. Baseline — capture your token and see the correct scope

Point Burp at the vulnerable API on `127.0.0.1:8201` and work from Repeater.

> **The tokens below are from one real session.** `POST /login` mints a fresh random token each time, so **yours will differ** — copy your own from each login response and use it in the `Authorization` header. The ids are stable (seeded), and the chain is identical either way.

Log in as yourself, `dana`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8201
Content-Type: application/json

{"user": "dana"}
```

Response — `200`, a token that is yours for the rest of the session (shown as `<dana-token>` below):

```json
{"token": "CtzOeigH7E6XnvXbLY15XzHXUKb-eGsa"}
```

Log in a second time as a victim, `alice`, and keep that token too (shown as `<alice-token>`) — you'll need it once, in the next step:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8201
Content-Type: application/json

{"user": "alice"}
```

Now list your own orders with your token:

```
GET /orders HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <dana-token>
```

Response — `200`, and note it contains **only your one order**:

```json
[{"id":1007,"owner":"dana","customer":"Dana Lee","address":"3 Testing Blvd, Faketon","item":"Wireless mouse","amount":"$29.90"}]
```

That single item is the proof the API **knows exactly who you are** and scopes you correctly. Read it back to confirm the feature works — `GET /orders/1007` with your Bearer returns `200` and your own order.

Finally, one legitimate cross-check for later. Ask for order `1001` with the **`<alice-token>`** — alice owns it, so this is what *authorized* access to `1001` looks like:

```
GET /orders/1001 HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <alice-token>
```

Response — `200`, alice's order. Keep it next to you; in the next step the exact same object comes back to *your* token.

## 5. Step 1 — Read another owner's order (BOLA confirmed)

Your own list handed you id `1007`. Ids are a single **global, contiguous counter**, so `1001`…`1012` all exist and belong to other customers. There is nothing to guess and nothing to reconstruct — you read your id and looked at the neighbors.

Ask for `1001` with your own, unchanged `<dana-token>`:

```
GET /orders/1001 HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <dana-token>
```

Response — `200`:

```json
{"id":1001,"owner":"alice","customer":"Alice Nguyen","address":"12 Example Ave, Springfield","item":"Mechanical keyboard","amount":"$89.00"}
```

You read another user's order — **with their name and delivery address** — using your own valid token, changing only the id. That is the **BOLA**. Nothing here is a payload; the request is valid by every protocol rule, a WAF (web application firewall) sees nothing wrong, and authentication "passed." Authorization for the object was simply never consulted.

Look at what just happened across two requests. That same `1001` came back `200` to `<alice-token>` in the baseline *and* `200` to `<dana-token>` now. The server **resolved two different identities correctly** — `authenticate()` returned `alice` on one request and `dana` on the other — and **handed the same object to both**, because the identity, though known, never enters the access decision. That is exactly where BOLA lives.

## 6. Step 2 — What the vuln is NOT

The exploit is a legitimate request with a legitimate token, so it is easy to misread. Three requests pin down the real cause by isolating what it is *not*.

**(a) It is not an authentication failure.** Send `GET /orders/1001` with **no `Authorization` header** at all:

```
GET /orders/1001 HTTP/1.1
Host: 127.0.0.1:8201
```

Response — **`401`**. Authentication works: with no identity, nothing comes out. (Corrupt the token by flipping a character and you get `401` too.)

**(b) The same token scopes correctly elsewhere.** Send `GET /orders` with your `<dana-token>` again — `200`, only order `1007`. The very token that just read alice's order produces a perfectly scoped answer here.

**(c) The same token gets no scope on the detail route.** Send `GET /orders/1001` with that same `<dana-token>` — `200`, alice's order, exactly as in Step 1.

Hold (b) and (c) side by side: **the same token gives correct scope in one handler and no scope in the other.** So this is not broken identity and not impersonation — you were authenticated as `dana` the whole time, and the list endpoint scoped you correctly. It is a check that *exists* in `GET /orders` and is *missing* in `GET /orders/:id`. The cause is the absent object-level authorization on the detail route — not the token, not your identity, not the shape of the id. (A non-guessable id would only make discovery more expensive; it would not put the check back.)

Contrast the web atom `idor-numeric-id`, where the endpoint ignored the caller's asserted identity entirely — there was no real authentication to speak of. Here the endpoint *does* authenticate, resolving a genuine identity, and then throws it away at authorization time. That is the more common, more realistic shape, and the auth-versus-authz distinction is only this sharp *because* the authentication underneath is real.

## 7. Step 3 — Enumerate the whole collection (Intruder)

One cross-user read is a finding; the collection is the impact. Send `GET /orders/1001` to **Burp Intruder** — the tool that repeats a request while substituting one value from a list, here the id. Mark the id as the payload position:

```
GET /orders/§1001§ HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <dana-token>
```

Set the payload type to **Numbers**, range `1001`–`1012`, step `1`, and start the attack. Your `<dana-token>` stays fixed across every request.

**The whole collection comes back:** twelve `200` responses, eleven of them orders that aren't yours — the names, addresses, and purchases of **alice, bob, and carol**. That is the jump from "one object leaked" to "**the collection leaked**": a single missing check, replayed across a contiguous id range, empties the database of everyone's personal data. A screenshot of the Intruder results table, with the customer and address fields in view, is the finding.

## 8. Why the fix works — the flat wall of 404s

Repeat the **same Intruder sweep** — Numbers `1001`–`1012`, your `<dana-token>` — against the fixed API on `127.0.0.1:8301`:

- **Only `1007` comes back `200`** (your own order). The other eleven are all **`404`**, identical to one another — same status, same body. That **flat wall of `404`** in the Intruder results is the proof the fix works: where the vulnerable sweep leaked eleven customers, this one leaks nothing.
- `GET /orders/1007` with your `<dana-token>` still returns `200` — owners still read their own orders. Authentication is still enforced: no token or a bad token still gets `401`.
- **`404`, not `403`:** the `404` for an order you don't own is byte-for-byte the `404` for an id that was never seeded — `GET /orders/1013` returns the same thing. So there is **no enumeration oracle**: an attacker can't even tell which ids are real. ([`DIFF.md`](./DIFF.md) carries the full argument — the GitHub precedent, RFC 9110, and when `403` is the legitimate choice.)
- **The fix left the id sequential.** Order `1001` is still a plain contiguous integer; the patch reshaped nothing about the id, because the id's shape was never the problem — the missing check was.

> The same missing check doesn't leak an order: it leaks the collection — every customer's name, address, and purchase. The token proves you're you; it says nothing about whose order this is.

The walkthrough ends here. The finding is the cross-user read and the enumeration that scales it; the fix is one predicate on one guard. There is nothing left to exfiltrate and no variation worth adding — to go deeper on the class, the theory primer's PortSwigger page is the place.
