# Walkthrough — bfla-method-based

## 1. Context

A profile API serves two routes on one path: `GET /users/:handle` reads an account's profile, and `PATCH /users/:handle` edits its display name. Both authenticate the caller with a Bearer token, but only the `GET` checks that the record is yours; the `PATCH` writes without that check, so any logged-in user can edit anyone's record. That is **BFLA (Broken Function Level Authorization)** — **API5:2023** in the OWASP API Security Top 10. **Function-level authorization** is the access check attached to an *operation* — a (method, path) pair — rather than to an object; **method-based BFLA** is when that check is present on one method of a path and missing on another.

This is the series' second atom on that axis, and the contrast with its neighbours is the whole point. The three API1 atoms asked a question about the **object** — *is this order yours?* in `bola-sequential-id` and `bola-uuid-leaked`, *does it belong to this store?* in `bola-nested-resource` — and answered it on every route that served the object. `bfla-admin-function` asked about the **function** — *may you invoke this operation at all?* — and never asked it. This atom asks about the **method**: *does authorization cover every method of this path?* Here the answer is no — it covers `GET`, not `PATCH`.

Finding the write is not a challenge to stage: you already edit your own profile with `PATCH /users/:handle`, so you simply point that same `PATCH` at someone else's handle. And there is no legitimate cross-user read to muddy the picture — each account owns exactly one record, the one keyed by its own handle, so a `GET` for a record that isn't yours is *correctly* refused. You are `clancy`. By the end you will have edited another user's record with your own valid token, and proved the change by having the victim read it back.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it). If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts) and read the two `/users/:handle` handlers next to each other. The `GET` guards the record with an ownership check; the `PATCH`, on the same path, does not:

```ts
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  res.json({ handle: req.params.handle, displayName: user.displayName });
});

app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
  // VULNERABLE: the GET handler on this same path guards the record with an ownership
  // check; this PATCH handler has none. Authorization belongs to (method + path), not to
  // the path -- guarding the read left the write on the same resource wide open.
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);                               // unknown target user
  user.displayName = req.body?.displayName ?? user.displayName;        // state change -- not a read
  res.json({ handle: req.params.handle, displayName: user.displayName }); // the state delta, echoed input
});
```

Both authenticate the same way, so a missing or invalid token gets `401` on either. The asymmetry is one line: `GET` has `if (req.params.handle !== caller) return 403`, and `PATCH` does not. So the audit question here is not BOLA's *"where does this check the caller owns the object?"*, and not `bfla-admin-function`'s *"where does this check the caller's role?"* — it is **"does authorization cover every method of this path?"** The answer: it covers `GET`, and it does not cover `PATCH`.

- **The check is present and correct — on one method.** This is not an absent check pointed nowhere; the ownership check is right there in `GET`, and it works. The gap is that it was written for one method and the other was left bare.
- **This class doesn't `grep`.** There is no dangerous string to search for — no `eval`, no concatenated query. You find it by listing the methods a path accepts and checking that each one carries the authorization the resource needs.

## 3. How auth works in this lab

`POST /login` takes a username and returns an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It asks for no password: that is a deliberate lab shortcut, not part of the bug. The token is *opaque* — a value carrying no readable structure, unlike a JWT (JSON Web Token) whose payload you could decode — so there is nothing inside it to inspect or tamper with anyway.

Two things to hold in mind before you start:

- **Authentication is genuinely enforced.** A missing or invalid token gets `401` on both routes. You'll confirm this in Step 2.
- **Whether the record is the caller's own is a separate check** — an **ownership check**, `req.params.handle === caller`. The `GET` makes it; the vulnerable `PATCH` does not. That is the one difference between the two methods.

One discipline for the whole walkthrough: **the attack never touches the token.** You don't decode it, alter it, or forge it — you log in as yourself and send the token exactly as issued. It stays valid and `clancy`'s from start to finish. The target is the method, not the token.

## 4. Baseline — log in and watch ownership work on `GET`

Point Burp at the vulnerable API on `127.0.0.1:8205` and work from Repeater.

> **The token below is from one real session.** `POST /login` mints a fresh random token each time, so **yours will differ** — copy your own from the login response into the `Authorization` header. The handles are stable (seeded), so those you can paste verbatim.

Log in as yourself, `clancy`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8205
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, a token that is yours for the rest of the session (shown as `<clancy-token>` below):

```json
{"token":"B4s3jvY0EveEUjKJ9H_Wb8dm7tJrJtdy"}
```

> `Method: GET · Target: clancy (yours) · Isolates: reading your own record is allowed`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"handle":"clancy","displayName":"Clancy Park"}
```

Now try to read the other seeded account, `alice`, with the same token:

> `Method: GET · Target: alice (not yours) · Isolates: the ownership check refuses a foreign read`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — **`403`**, body `Forbidden`. The server **knows how to check ownership**, and it refuses: `alice`'s record is not yours to read. Hold on to this response — it is what will separate this flaw from both of its look-alikes.

## 5. Step 1 — Write another user's record through the unguarded method (BFLA confirmed)

Same token, same path, same foreign record — change only the method, from `GET` to `PATCH`, and send a new display name:

> `Method: PATCH · Target: alice (not yours) · Isolates: the write has no ownership check`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "pwned by clancy"}
```

Response — **`200`**:

```json
{"handle":"alice","displayName":"pwned by clancy"}
```

The **same URL** that refused your *read* a moment ago (`GET /users/alice` → `403`) accepted your *write* (`PATCH /users/alice` → `200`). You edited a record that is **not yours**, with your own valid token, by **changing nothing but the HTTP verb**. What explains the success is not an object of yours and not a forged identity — it is that **this method was left unprotected**. That is the **BFLA**: authorization applies to a (method, path) pair, and guarding the `GET` never guarded the `PATCH`.

**Read the response carefully, because it is a trap.** The `200` proves the authorization was **bypassed** — the server accepted and ran the write for a non-owner. It does **not** prove that `alice`'s record visibly changed: the body only reflects the value *you* sent (`displayName` is your input echoed back, `handle` is what you put in the path). An endpoint that ignored `:handle` entirely and just returned your input would answer identically. And you can't confirm the change another way, because `GET /users/alice` with your token is `403`. The write is real, but from the attacker's side it is **unobservable through the API** — the same trap `bfla-admin-function` carried. The proof of the change comes in Step 3, from a different direction: the victim reading her own record.

## 6. Step 2 — What the vuln is NOT

A legitimate request with a legitimate token is easy to misread two ways. Name both and take them apart, with three requests, all sent with your unchanged `<clancy-token>`.

**"This is `bfla-admin-function` again — an endpoint with no check."** It isn't:

> `Method: GET · Target: alice (not yours) · Isolates: there IS working authorization on this path`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — **`403`**. Unlike the admin atom, where the attacked function had no authorization at all, this path *does* carry a working check — the server refuses a foreign read. The authorization is not absent; it is just not on every method.

Now the write, for contrast, same foreign target:

> `Method: PATCH · Target: alice (not yours) · Isolates: same path, same record, different method — and it passes`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>

{"displayName": "again"}
```

Response — **`200`**. Between this request and the one above it, only the **method** changed, and the verdict flipped.

**"This is BOLA — I reached an object that wasn't mine."** It isn't that either:

> `Method: GET · Target: clancy (yours) · Isolates: the 403 above was ownership working, not "GET is always blocked"`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — **`200`**, your own record. So the `403` on `GET /users/alice` was not "`GET` is blocked here" — it was the ownership check doing its job: `200` for your own record, `403` for someone else's. The object-level authorization is **present and correct**. If this were BOLA, that check would be broken or missing on the read; it is neither. The one thing missing is the same check on `PATCH`.

One more, to close off the last misreading — that this is a broken-authentication problem. Drop the header entirely:

> `Method: PATCH · Target: alice · Token: none · Isolates: authentication is enforced — no identity, no action`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8205
```

Response — **`401`**, body `Unauthorized`, with a `WWW-Authenticate: Bearer` header. (Corrupt the token by changing a character and you get `401` too.) You were authenticated as `clancy`, correctly and continuously, through every other request — this is not broken identity and not impersonation.

Put it together. Object-level authorization is **present, correct, and applied — on `GET`**: it refuses the foreign record and serves your own. The `PATCH` over the *same* record, by the *same* user, **never passes through it**. The flaw is not that the ownership check is wrong (not BOLA), and not that the method has no authorization at all (not the admin atom) — it is that the check **does not cover every method of the path**. The question to ask of a path is *"is authorization on every method?"*, not *"whose object is it?"*.

> **One URL answered the read safely and the write wide open — because authorization attaches to the pair (method, path), and guarding the GET never guards the PATCH.**

## 7. Step 3 — Impact: the victim reads the planted value

The `200` in Step 1 bypassed authorization, but its body was your own input echoed back, and `GET /users/alice` with your token is `403` — so from where you sit, nothing confirms the record actually changed. The proof uses only what already exists — the protected `GET` and `POST /login`, no new route, no change to the seed: the one person allowed to read `alice`'s record is **`alice`**. Log in as her (the seed already has her — it is just one more `POST /login`):

> `Method: POST · Logging in as: alice (the victim) · Isolates: get the owner's own token`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8205
Content-Type: application/json

{"user": "alice"}
```

Response — `200` with `alice`'s token (shown as `<alice-token>`). Now have her read her own profile:

> `Method: GET · Target: alice (hers) · Token: alice · Isolates: the owner reads her record and finds the attacker's value`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <alice-token>
```

Response — **`200`**:

```json
{"handle":"alice","displayName":"pwned by clancy"}
```

**This is the proof.** `alice`, reading her own record through the authorized `GET`, finds the `displayName` that `clancy` wrote — `"pwned by clancy"`, not the seed value `"Alice Nguyen"`. The write in Step 1 was real all along; it simply wasn't observable from the attacker's side. The same protected `GET` that was the living proof of correct authorization (Steps 1 and 2) now doubles as the verification instrument, and the loop closes without a single extra route.

The impact, stated honestly: this is **horizontal** — a plain user edited another plain user's record through the unguarded method, while the `GET` on the same path refuses a foreign read. It is not vertical (no role is gained — there is no admin here) and not RCE. Where `bfla-admin-function` reached *above* its privilege level, this reaches *sideways*, to a peer's record, through a method nobody guarded.

## 8. Why the fix works (port 8305)

Point Burp at the fixed API on `127.0.0.1:8305` and log in there as `clancy` — each build keeps its own token map and its own seed, so you need a fresh token, and nothing you did on 8205 carries over. Replay the exploit:

> `Method: PATCH · Target: alice (not yours) · Isolates: the GET's ownership check, now on PATCH too`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8305
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "pwned by clancy"}
```

Response — **`403`**, body `Forbidden`. The `PATCH` now runs the same ownership check the `GET` already had, right after authenticating and **before** the record is looked up — so the write below it never runs, and `alice`'s record is untouched. Have `alice` read it to confirm: `GET /users/alice` with her token returns `{"handle":"alice","displayName":"Alice Nguyen"}`, the seed value, because nothing was ever written.

The fix didn't break the feature; it restricted it to the owner. Editing your **own** record still works — no admin account is needed, because the legitimate path is simply you editing yourself:

> `Method: PATCH · Target: clancy (yours) · Isolates: the owner can still edit his own record`

```
PATCH /users/clancy HTTP/1.1
Host: 127.0.0.1:8305
Authorization: Bearer <clancy-token>

{"displayName": "My New Name"}
```

Response — `200` with `{"handle":"clancy","displayName":"My New Name"}`. The `GET` is unchanged (`200` for your own record, `403` for a foreign one), and a missing or bad token still gets `401` with its `WWW-Authenticate: Bearer` challenge; the `403`s carry none, because you were already authenticated and there is nothing to ask for.

**`403`, not `404`.** A non-owner gets an honest `403`, not a `404` that would pretend the record isn't there. The ownership check compares the path handle to the caller before any lookup, so it reveals no existence to hide — unlike the API1 atoms, where an order's `404` hid its existence from an enumerable id space. [`DIFF.md`](./DIFF.md) carries the full argument — RFC 9110 §15.5.4 and the series' single criterion for choosing between the two.

The walkthrough ends here. The finding is a plain user editing another user's record with his own valid token, on a method that was never guarded; the fix is one ownership check, copied from the `GET` onto the `PATCH`. To go deeper on the class, the theory primer's PortSwigger page is the place.
