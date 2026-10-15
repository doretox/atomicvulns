# Walkthrough — bopla-excessive-exposure

## 1. Context

A profile API serves `GET /users/:handle`: it authenticates the caller with a Bearer token, checks that the record is the caller's own, and returns it. The ownership check is right — you can read only your own profile — but the handler then serializes the **whole stored record**, so two server-side fields come back with it: `passwordHash` and `is_admin`. That is **BOPLA (Broken Object Property Level Authorization)** — **API3:2023** in the OWASP API Security Top 10 — in its read face, what the industry calls **excessive data exposure**: the response returns properties the caller should not see. **Property-level authorization** is the access check applied to an object's individual fields, below the object as a whole.

This is the series' first atom at the **property** grain, and the contrast with its neighbours is the point. The three API1 atoms asked a question about the **object** — *is this object yours?* The two API5 atoms asked about the **function** — *may you invoke this operation?* This atom asks about the **field**: *does the response return only the fields this caller may see?* Here the answer is no — it returns `displayName`, and also `passwordHash` and `is_admin`.

There is nothing to stage and no second actor. You are `clancy`, and you read your **own** profile — fully authorized at the object level — and the internal fields are already in the body. The "technique" is reading the raw response in Repeater, which is exactly the reflex that separates a pentester from someone who trusts the UI.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it). If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts). The one handler to read is `GET /users/:handle`:

```ts
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  // VULNERABLE: the ownership check above is right -- this IS your record. But the response
  // spreads the WHOLE stored object, so every server-side field rides along with the public
  // one. Authorization applies to each property returned, not only to the object.
  res.json({ handle: req.params.handle, ...user });
});
```

The asymmetry is **inside one handler**, not between two. The ownership check (`if (req.params.handle !== caller) return res.sendStatus(403)`) is present and correct — it lets you read only your own record. One line below it, `res.json({ handle: req.params.handle, ...user })` spreads the entire stored object into the response. The record carries three fields — `displayName`, `passwordHash`, `is_admin` — and the spread ships all three. So the audit question here is not BOLA's *"where does this check the caller owns the object?"* (it does, and it passes), and not BFLA's *"does authorization cover every method?"* — it is **"does the response return only the fields this caller may see?"** The answer: no.

- **The ownership check is not the flaw — it inverts the sibling atom.** In `bfla-method-based`, this very `GET` was the *living proof* that the ownership check worked. Here the same guard is still correct and still passes; the flaw is new and sits one line below it, in what gets serialized.
- **This class doesn't `grep`.** There is no dangerous string to search for — no `eval`, no concatenated query. You find it by reading what each handler returns and asking whether every field in the response is one the caller is allowed to see.

## 3. How auth works in this lab

`POST /login` takes a username and returns an **opaque Bearer token** — a random string the server stores in a `token -> user` map and resolves on every request. It asks for no password: that is a deliberate lab shortcut, not part of the bug. The token is *opaque* — a value carrying no readable structure, unlike a JWT (JSON Web Token) whose payload you could decode — so there is nothing inside it to inspect or tamper with anyway.

Two things to hold in mind before you start:

- **Authentication is genuinely enforced.** A missing or invalid token gets `401` with a `WWW-Authenticate: Bearer` challenge. You'll confirm this in Step 5.
- **Ownership is checked, and it passes for your own record.** `req.params.handle === caller` lets you read the record keyed by your handle and refuses anyone else's. That check is correct; it is not where the bug is.

One discipline for the whole walkthrough: **the attack never touches the token.** You don't decode it, alter it, or forge it — you log in as yourself and send the token exactly as issued. It stays valid and `clancy`'s from start to finish. And the `passwordHash` the response leaks is **not** what the login reads: login takes no password at all, and the hash is dummy stored-side data. The target is what the response serializes, not the token and not the password.

## 4. Baseline = Exploit — log in and read your own profile

Point Burp at the vulnerable API on `127.0.0.1:8206` and work from Repeater.

> **The token below is from one real session.** `POST /login` mints a fresh random token each time, so **yours will differ** — copy your own from the login response into the `Authorization` header. The handle is stable (seeded), so that you can paste verbatim.

Log in as yourself, `clancy`:

> `Method: POST · Logging in as: clancy (you)`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8206
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, a token that is yours for the rest of the session (shown as `<clancy-token>` below):

```json
{"token":"B4s3jvY0EveEUjKJ9H_Wb8dm7tJrJtdy"}
```

Now read your own profile — the record you are fully entitled to:

> `Method: GET · Target: clancy (yours) · Isolates: your own record comes back with internal fields attached`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8206
Authorization: Bearer <clancy-token>
```

Response — **`200`**:

```json
{"handle":"clancy","displayName":"Clancy Park","passwordHash":"$2b$12$DUMMYsaltFORlabUSEonlyDUMMYhashNOTaREALpasswordCLANCY","is_admin":false}
```

**This is the proof, and it is self-contained.** You asked for your **own** profile, fully authorized, and the response carried `passwordHash` and `is_admin` — server-side fields that should never have left the server. There was no payload, no second actor, and no second request: the baseline read *is* the exploit, and the "exploit" is reading the raw body in Repeater. That is the honest contrast with `bfla-method-based`: there, the `200` from the write was your own input echoed back, so it proved nothing on its own, and the proof needed the victim reading her record afterwards. Here the self-read proves it directly — the leaked fields are in the body that came back to **you**, from the record that is **yours**.

## 5. Step — What the vuln is NOT

A legitimate request with a legitimate token is easy to misread. Two readings to take apart firmly, and a third as a principle.

**"This is BOLA — I read data that wasn't mine."** It isn't. Try the other seeded account with your own token:

> `Method: GET · Target: alice (not yours) · Isolates: the ownership check exists and bites`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8206
Authorization: Bearer <clancy-token>
```

Response — **`403`**, body `Forbidden`. The object-level authorization is present and correct: you did **not** read someone else's object — you read your **own**. The problem is not access to a foreign object; it is the **content of your own object**. (This `403` is the same ownership guard `bfla-method-based` used, compared before any lookup — [`DIFF.md`](./DIFF.md) carries the full status-code argument.)

**"This is weak crypto."** It isn't the lesson here. Look again at the Step 4 body — no new request needed: what matters is that `passwordHash` is **in the response at all**, not how strong the hash is. Whatever the algorithm, that field should never have left the server. Weak hashing is a different class; here the axis is **exposure**.

A third misreading worth naming as a principle: **client-side control is not control.** In a real app a UI might omit these fields from the screen — but a pentester reads the raw response regardless, so the filtering has to be server-side. There is no UI in this atom at all, and that is exactly the point: the only thing standing between the internal fields and the client is what the handler chooses to serialize.

Put it together. You are **fully authorized for the object** — it is your record, and the ownership check approves it — and the response **still** handed you fields you may not see. The flaw is not reading a foreign object (not BOLA), not the strength of the hash (not weak crypto), and not the UI (there is none). It is the response **returning too many properties**.

> **Owning the object was never the same as being cleared for every field on it — and the raw body shipped all of them, because the only authorization in the path stopped at the object.**

## 6. Step — Impact

Two real impacts, neither inflated:

- **Internal schema recon.** The response exposes the **shape** of the server-side record — that an `is_admin` field exists, that a `passwordHash` exists, and what they are named. Even with `is_admin` coming back `false`, the attacker learns the field exists and how it is spelled: a map of the internal model, useful material for later attacks. This is **information disclosure**.
- **An exposed credential artifact.** The `passwordHash` is an artifact that should **never** appear in a response. In a real system a leaked hash enables **offline cracking** — guessing passwords against the hash off the server, with no rate limit in the way.

What the impact is **not**:

- **Not privilege escalation.** `is_admin` comes back `false`; nobody becomes an admin, and nothing here writes the flag. The leak is of the **field** and the **pattern** (the whole object serialized), not of any value.
- **Not password cracking, here.** The login is passwordless and the `passwordHash` is dummy — there is no real password to crack. The lesson is **exposure**, not hash quality; a stronger hash would still be a field that should never have shipped.

## 7. Why the fix works (port 8306)

Point Burp at the fixed API on `127.0.0.1:8306` and log in there as `clancy` — each build keeps its own token map, so you need a fresh token. Read your profile again:

> `Method: GET · Target: clancy (yours) · Isolates: the allow-list — only the public fields come back`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8306
Authorization: Bearer <clancy-token>
```

Response — **`200`**:

```json
{"handle":"clancy","displayName":"Clancy Park"}
```

The internal fields (`passwordHash`, `is_admin`) are **gone**; the feature — reading your own profile — still works. The fix replaced the whole-object spread with an **allow-list**: the response names the fields the caller may see, so anything else stays server-side by default.

Nothing else changed. The ownership check and the `401` are untouched:

- `GET /users/alice` with your `<clancy-token>` → **`403`**, body `Forbidden` — same as the vulnerable build.
- `GET /users/clancy` with **no** `Authorization` header → **`401`**, body `Unauthorized`, with a `WWW-Authenticate: Bearer` header. (Corrupt the token by changing a character and you get `401` too.)

The single line between the two builds is what the response serializes. [`DIFF.md`](./DIFF.md) works through it — why an allow-list (which fails closed) is the fix and a deny-list (which fails open) is not, and why these status codes follow the series' criterion.

The walkthrough ends here. The finding is the internal fields riding back in a self-read you were fully authorized to make; the fix is one line, naming the fields the response may carry. To go deeper on the class, the theory primer's PortSwigger page is the place.
