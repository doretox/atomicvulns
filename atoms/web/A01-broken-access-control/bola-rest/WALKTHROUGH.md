# Walkthrough — bola-rest

## 1. Context

The app is a small e-commerce **orders API**. Each order has an owner, an item, and an amount, and you read one through `GET /api/orders/<id>`. Requests authenticate with a Bearer token you get from `POST /login`. The developer's mental model is "a client only ever sees its own orders" — and the list endpoint, `GET /api/orders`, does exactly that. The single-order endpoint forgot to.

You are going to read another user's order using **your own, perfectly valid token** — by reading an id the API itself handed you and asking for the neighbor. Then you'll see the endpoint never checks whose order it is at all: any id you hold, authenticated as yourself, was always enough. This is **BOLA — Broken Object Level Authorization**, the [#1 risk in the OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/), and it is IDOR wearing an API's clothes — the same missing-check bug as `idor-numeric-id` and `idor-uuid-guessable`.

This atom is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater**; if you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The vulnerable view is short:

```python
@app.route("/api/orders/<int:order_id>")
def get_order(order_id):
    _authenticate()   # require a valid token (401 otherwise) -- AUTHENTICATION only
    order = ORDERS.get(order_id)
    if order is None:
        abort(404)
    # VULNERABLE: the request is authenticated, but the order is returned WITHOUT
    # checking that order["owner"] is the authenticated caller.
    return jsonify(order)
```

Read it twice. It calls `_authenticate()`, so a missing or invalid token is rejected with `401`, and by the time you reach the `return`, the request is *genuinely authenticated*. Then it looks the order up by id and returns it. The bug is **what isn't there**: no comparison between `order["owner"]` and the caller. The function trusts that "if you're logged in and you asked for order N, you may see order N." That trust is the whole vulnerability.

Two things worth internalizing from this shape:

- **It has `_authenticate()`, and that is exactly what disarms a hurried reviewer** — "there's auth on the endpoint, looks fine." But authenticating and authorizing are different questions. The endpoint answers *"who are you?"* and never asks *"is this order yours?"*. Now look at the list endpoint in the same file — `GET /api/orders` filters `ORDERS` by `owner == caller`. The developer clearly *knew* how to scope to the owner; they just didn't do it on the by-id endpoint. **That asymmetry — list scoped, detail unscoped — is the signature of real-world BOLA.**
- **This class doesn't `grep`.** There's no `f"`, `|safe`, or `eval` to search for. You find it by reading each endpoint that returns a user-scoped object and asking "where does this check the caller owns it?" — and here the answer is nowhere.

## 3. How auth works in this lab

Real authentication (passwords, hashing, sessions) is out of scope — that ceremony belongs in a dedicated authentication atom. This lab fakes it with `POST /login`: send a username, get back an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It is not a JWT; there is nothing encoded in it to read or tamper with.

Two things to hold in mind before you start:

- **Authentication is genuinely enforced.** A missing or invalid token gets `401`. You'll confirm this in Step 3.
- **Whether that authenticated identity is used to *authorize* a specific object is a separate question** — and the vulnerable `/api/orders/<id>` doesn't use it. That gap is the bug.

One discipline for the whole walkthrough: **the attack never touches the token.** You don't decode it, tamper with it, or forge it — you log in as yourself and use the token exactly as issued. It stays valid and yours from start to finish. The target is the endpoint, not the token.

## 4. Exploitation via Burp Suite

Point Burp at the vulnerable API on `127.0.0.1:8012` and work from Repeater.

> **The token and ids below are from one real session.** `POST /login` mints a fresh random token each time, so **your token will differ** — copy your own from the login response and use it in the `Authorization` header throughout. The ids are stable (they're seeded), and the chain is identical either way.

### Baseline — the API working normally

Log in as yourself, mallory:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8012
Content-Type: application/json

{"user": "mallory"}
```

Response — `200`, a token that is yours for the rest of the session:

```json
{"token": "jXTGkJXWukSCs-zsD7QhkFYW1GKUMPKl"}
```

(Shown as `<mallory-token>` below.) Now list your own orders:

```
GET /api/orders HTTP/1.1
Host: 127.0.0.1:8012
Authorization: Bearer <mallory-token>
```

Response — `200`, and note it contains **only your orders**:

```json
[{"amount":"$29.90","id":40,"item":"Wireless mouse","owner":"mallory"},
 {"amount":"$12.99","id":42,"item":"USB-C cable","owner":"mallory"}]
```

Read one of your own back to confirm the feature works — `GET /api/orders/40` with your Bearer returns `200` and your order. The API does what it promises.

### Step 1 — Infer the neighbor's id

Look again at your own list: you own orders **40** and **42**. The ids are small sequential integers, and there is a **hole at 41** — an id sitting right between two you own. Order ids are a single global sequence, so that gap belongs to *someone else's* order.

There is nothing to guess and nothing to reconstruct here. The API handed you your ids in plain sight, and the missing one is one integer away. (Contrast `idor-uuid-guessable`, where the id *looked* random and you had to rebuild it from a timestamp — here the id is just the interface.)

### Step 2 — Read the victim's order (BOLA confirmed)

Ask for order 41 — the gap — with your own, unchanged token:

```
GET /api/orders/41 HTTP/1.1
Host: 127.0.0.1:8012
Authorization: Bearer <mallory-token>
```

Response — `200`:

```json
{"amount":"$589.00","id":41,"item":"Standing desk","owner":"alice"}
```

That is the BOLA. You read alice's order — her item, her amount — authenticated the whole time as yourself, having done nothing but ask for an id the API gave you. Nothing here is a payload; the request is valid by every protocol rule, a WAF sees nothing wrong, and authentication "passed." Authorization for the object was simply never consulted.

(An id that doesn't exist — say `39` or `999` — returns `404`. In the vulnerable app the status even distinguishes "exists" from "doesn't," but that hardly matters when a hit hands you the whole object anyway.)

### Step 3 — Prove the bug is missing authorization, not an auth failure or a guessable id

The exploit is quick, and it can mislead you into two wrong conclusions. Kill both.

**(a) It is not an authentication failure.** Take the request that just worked — `GET /api/orders/41` with your Bearer, `200`, alice's order — and vary only the token:

- Remove the `Authorization` header entirely → **`401`**.
- Corrupt the token (flip one character) → **`401`**.
- Restore your valid token → **`200`**, alice's order again.

Authentication works *perfectly* — it rejects the missing token and the bad token. And yet, with your genuine token, you read alice's order. So the failure is not authentication: you were correctly identified as mallory the entire time. What's missing is authorization — being authenticated as mallory was never checked against the order's owner. **Being authenticated is not being authorized.**

Contrast `idor-numeric-id`, where the endpoint ignored the caller's identity entirely — changing the header changed nothing. Here the endpoint *does* read the token, to authenticate; it just throws that identity away instead of authorizing with it. That is the more common, more realistic shape — and the auth/authz distinction is only visible *because* there is real authentication here, which the self-asserted-header siblings didn't have.

**(b) It is not about the id being guessable.** You didn't guess or reconstruct anything — `GET /api/orders` handed you your ids and the hole at 41 pointed straight at the target. In a REST API, ids are *public by design*: clients are supposed to hold and pass them; that's the contract. So the remedy is not to make the id a UUID or a random value — `idor-uuid-guessable` already proved that reshaping the id is theater. The proof is in the fix (§7): the patched app keeps the sequential id **untouched** and only adds the ownership check. The id's shape was never the problem; the absent object-level authorization was.

One root cause under both: there is no object-level authorization check.

## 5. Why this is BOLA, and why the id was never the point

In `idor-uuid-guessable` we said that reshaping the id — swapping an integer for a UUID — was *"obfuscation... theater,"* that it "only changes how hard the bug is to *find*." This atom removes even the obfuscation: in an API the id is public by contract — the listing hands you your own, and the neighbor is the next integer. There is nothing left to hide behind, so authorization is the only thing that could protect the object. The token proves you're you; it says nothing about whose order this is.

| Atom (A01) | Object reached by… | The id is… | Missing check |
|---|---|---|---|
| `idor-numeric-id` | changing an id (`/notes/1` → `/notes/2`) | sequential integer | ownership (is the note yours?) |
| `idor-uuid-guessable` | reconstructing and using the UUID | reconstructible UUIDv1 | ownership (is the receipt yours?) |
| `bola-rest` | reading your own id off the API and asking for the neighbor | **sequential integer, public by API design** | **object-level authorization (is the order yours?)** |
| `path-traversal-basic` | navigating the filesystem (`notes.txt` → `../../etc/passwd`) | file path | confinement (did the path stay in the folder?) |

The three IDOR/BOLA atoms share the exact same cause and the exact same fix — check the object's owner against the caller. They differ only in the id's shape and how much authentication surrounds it: `idor-numeric-id` counts, `idor-uuid-guessable` reconstructs, and here the id is simply public while real authentication makes "authenticated ≠ authorized" impossible to miss. `path-traversal-basic` is the same A01 family by a different axis (confining a path rather than owning an object).

## 6. Impact

Horizontal privilege escalation: you read another same-level user's order — her item, her amount, her purchase. That is the honest ceiling. **It is not RCE, and not vertical escalation** — you gained no code execution and no elevated role. BOLA sits at #1 of the OWASP API Security Top 10 because it is ubiquitous and high-impact in real APIs, where order/account objects often carry PII that *chains* into further attacks — but the finding in this atom is the cross-user read itself.

## 7. Why the fix works

Run the chain against the fixed API on port **8112** (see [`DIFF.md`](./DIFF.md) for the change). Log in as mallory there — a fresh token, because the fixed app is a separate process — and:

- **Read the neighbor, `GET /api/orders/41`, with your valid token → `404`.** You hold a perfectly good token and are still refused, because the fixed view compares `order["owner"]` to the caller before returning. This single check closes the BOLA.
- **Read your own, `GET /api/orders/40` → `200`.** Owners still get their own orders.
- **Authentication is still enforced** — no token or a bad token still gets `401`.

Two things the fix deliberately does *not* do. It doesn't reshape the id — order 41 is still a plain sequential integer, because the id was never the problem. And it returns **`404`, not `403`**. A `403` would confirm the order exists ("it's there, but not for you"); with sequential ids that is an enumeration oracle — walk the integers and `403`-vs-`404` maps every order in the system. The fixed app returns `404` for a non-owner *and* for a genuinely missing id — indistinguishable, so the status leaks nothing. Prove it: `GET /api/orders/999` (nonexistent) and `GET /api/orders/41` (exists, not yours) come back byte-for-byte identical. (`idor-numeric-id` and `idor-uuid-guessable` return `403`; [`DIFF.md`](./DIFF.md) explains why that was fine for them and why sequential ids in an API change the answer here.)
