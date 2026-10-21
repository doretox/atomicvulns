# Walkthrough — auth-predictable-token

## 1. Context

A profile API serves `GET /users/:handle`: it authenticates the caller with a Bearer token, checks that the record is the caller's own, and returns the profile — including a private `email`. The ownership check is right — you only read your own profile. The flaw is one layer below it, in the token the login hands out: it is not a random value but **your username, encoded in base64url**, and authentication resolves it by *decoding* it and trusting the name. That is **Broken Authentication** — **API2:2023** in the OWASP API Security Top 10.

This atom is a turn in the series. The first seven asked, seven ways, **"may you do this?"** — whose object is it, may you call this function, which fields may you see or set — and every one of them trusted the token to say who *you* are. This one asks the question underneath: **are you really who you say you are?** That is the line between **authentication** — proving *who you are* — and **authorization** — proving *that you may*. An **opaque token** is a credential that carries no readable meaning: only the server, holding a record of it, can say whose it is. The vulnerable token here is the opposite of opaque, and that is the whole bug. **Impersonation** is presenting yourself as another user; you will do it to `alice` by rebuilding her token from her name.

This is an **API — there is no browser track.** Every request below is a block you paste into **Burp Repeater** (which resends a single request so you can edit and observe it). The `base64` command-line tool reads and builds the tokens. If you haven't wired up Burp yet, the same requests run under `curl`. That is the whole toolset.

## 2. Spot the bug

Open [`vulnerable/app.ts`](./vulnerable/app.ts). The one function to read is `authenticate` — not a route, the authentication helper itself:

```ts
function issueToken(user: string): string {
  return Buffer.from(user).toString("base64url");           // VULNERABLE: the name, encoded -- not entropy
}

function authenticate(req: express.Request): string | null {
  // VULNERABLE: decode the token and trust whoever it spells.
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return Buffer.from(token, "base64url").toString("utf8") || null;
}
```

The login mints the token by running the username through `base64url` — a reversible **encoding**, not encryption: there is no key and no secret, anyone can compute it both ways. Authentication then does the inverse, decoding the token back into a name and trusting it. So the audit question is not BOLA's *"where is the ownership check?"* (it is present, on the route, and it is correct) — it is **"is the token unpredictable to someone who did not receive it?"** The answer: no. The token *is* the name. Whoever knows a handle can produce that handle's token.

- **The contrast with the earlier seven is in the code.** The fixed build — and every atom before this one — uses the **same** `base64url`, but over `randomBytes(24)` instead of the name, and **stores** the result in a `token -> user` map to resolve by lookup. Same encoding, opposite source, opposite resolution. The token string looks the same; what changed is where it comes from and how it is read.
- **The route is not the bug.** `GET /users/:handle` has a correct ownership guard; it trusts the `caller` that `authenticate` returns, as any route must. The betrayal is *inside* `authenticate`, where that caller is conjured out of the token. Don't go looking for a missing check on the route — there isn't one.

## 3. How auth works in this lab — open your own token

`POST /login` takes a username and returns a Bearer token. It asks for no password: a deliberate lab shortcut, not the bug. Point Burp at the vulnerable API on `127.0.0.1:8208` and log in as yourself.

> `Method: POST · Logging in as: clancy (you)`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8208
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`:

```json
{"token":"Y2xhbmN5"}
```

Now look hard at that token, because it is the whole lesson. It is not random — log in again and you get the *same* string, every time. Decode it:

```bash
echo -n Y2xhbmN5 | base64 -d
```

→ `clancy`. **It is not opaque — it is your name.** No secret, no entropy: the "token" is a transparent envelope with your handle inside it. A real opaque token (which the fixed build issues) would decode to random bytes, not a word.

- **Encoding note:** `clancy` (6 bytes) encodes to `Y2xhbmN5` with no padding, so `base64` and `base64url` produce the same string here and `base64 -d` reads it straight back. Not every handle is this tidy — the next step hits the padding case with `alice`.

This step is **discovery**: you have only *read* what your own token is. You haven't forged anything yet. The next step builds someone else's.

## 4. Exploit — three movements, and the climax is one swapped header

Point Burp at the vulnerable API on `127.0.0.1:8208`, still logged in as `clancy`.

**Movement one — the baseline.** Ask for `alice`'s profile with your own token:

> `Method: GET · Target: alice (not yours) · Isolates: ownership exists and bites — your real identity is not alice`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8208
Authorization: Bearer Y2xhbmN5
```

Response — **`403`**, body `Forbidden`. **Read that `403` carefully: the route has an ownership check and it works.** You, as `clancy`, cannot read `alice`'s profile. Keep this result — it is what proves, in Step 5, that this is not BOLA.

**Movement two — forge the victim's token.** The token is the name in base64url, and the victim's name is the public handle `alice`. Build it:

```bash
echo -n alice | base64
```

→ `YWxpY2U=`.

> **The padding, once, in full (this is the one place it matters).** `alice` (5 bytes) encodes to 7 base64 characters **plus one `=` padding**, so `echo -n alice | base64` gives `YWxpY2U=` (with the `=`), while the canonical **base64url** form — the one the server itself would mint — drops the padding: `YWxpY2U`. **The server accepts both:** Node's base64url decoder tolerates the `=`, so `YWxpY2U` and `YWxpY2U=` both decode to `alice`. For these lowercase handles the two encodings differ *only* in that trailing `=` — never in the `+`/`/` characters, which none of these bytes produce. If a handle ever did produce `+` or `/`, `base64` and `base64url` would genuinely diverge and you'd use `basenc --base64url` instead. Here, either string works.

**Movement three — impersonation.** Resend the *same* `GET /users/alice`, changing **only** the `Authorization` header to the forged token:

> `Method: GET · Target: alice · Isolates: same URL, same correct guard — only who the token claims you are changed`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8208
Authorization: Bearer YWxpY2U
```

Response — **`200`**:

```json
{"handle":"alice","displayName":"Alice Nguyen","email":"alice@secret.example"}
```

Same URL, same route, the same correct ownership guard — and the opposite answer. You are reading `alice`'s private email. You did not slip past the guard; you **satisfied** it, because you forged the identity it compares against. The caller it saw was `alice`, so `handle === caller` held, and it served you her record.

> **The ownership check was right both times — all you changed was the name the token spells, and a token that spells your name is a name anyone can spell.**

## 5. Step — What the vuln is NOT

A well-formed Bearer token reading a record behind a correct ownership check is easy to misread. Two readings to take apart firmly, and a third worth a sentence — and you already hold all the evidence.

**"This is BOLA — I read an object that wasn't mine because a check was missing."** This is the misreading to kill, so weigh it most. Go back to the baseline in Step 4: `GET /users/alice` with your **own** token answered **`403`**. The ownership check is present and it bites. You did **not** read `alice`'s object through a missing authorization check — you **became** `alice`, and then the authorization, working correctly, handed you her object. Authorization right, authentication broken. In BOLA the identity is real and the check is absent; here the check is correct and the **identity is false**. (It is the same ownership guard `bfla-method-based` and `bopla-excessive-exposure` use, compared before any lookup — [`DIFF.md`](./DIFF.md) carries the status-code argument.)

**"This is token theft — you intercepted or replayed `alice`'s session."** You intercepted nothing. There was no network sniff, no stolen cookie, no captured token *resent*. You **built** `alice`'s token from scratch, out of her **handle** — which is public (it appears at login, across the platform). It is fabrication from public data, not theft of a secret. The difference matters: against theft you rotate the leaked token; against this there is nothing to rotate — every token is derivable.

**A third, smaller misreading: "it's weak crypto — the token uses a bad hash or cipher."** base64url is **not** cryptography — it is encoding. There is no key, no algorithm to break, only an envelope to open. The flaw is not that the crypto is weak; it is that there is **no secret at all**. That is why *signing* the token (giving it integrity) is not the lesson — see the fix.

Put it together. The profile route has **no authorization bug** — its ownership check is correct, and the baseline `403` proved it. The flaw is prior: the **token does not prove identity**, because anyone can produce it from a public name. You did not read a foreign object (not BOLA), steal a credential (not replay), or break crypto (there is none). You **forged the identity**.

## 6. Step — Impact

**Total impersonation of any user whose handle you know.** Handles are public — they appear at login and across the platform. For *each* one, you derive the token and authenticate as that user, reaching whatever their session reaches; here, their private `email`. The attack is not limited to one victim: it is a master key cut from a name.

The system's authorization becomes worthless without being wrong. Every check the earlier seven atoms taught — object, function, property — keeps running correctly and **serves the attacker**, because to the server he *is* the victim. That is what makes this class so severe: it does not knock down a wall, it forges the badge that opens all of them. And it is **not revocable**: the vulnerable build keeps no token state, so there is nothing to invalidate — while a handle exists, its token is derivable, and a restart changes nothing.

What the impact is **not**:

- **Not privilege escalation.** There is no admin and no role here. You become *another ordinary user*, not a superuser.
- **Not RCE or a database dump.** You read one profile at a time — the identity you forged. The finding is impersonation plus the victim's private datum, and that is enough.
- **Not an authorization bypass.** The authorization *worked*; it merely authorized a false identity. What was bypassed is **authentication**.

## 7. Why the fix works (port 8308)

Point Burp at the fixed API on `127.0.0.1:8308` and log in there as `clancy` — each build keeps its own token map, so you need a fresh token.

```
POST /login HTTP/1.1
Host: 127.0.0.1:8308
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, and the token is **random** this time (shown as `<clancy-token>`; yours will differ):

```json
{"token":"DEH8P81by76S571D2QtUsQCx36XykFha"}
```

Decode it and nothing legible comes out — `echo -n <clancy-token> | base64 -d` is 24 bytes of binary, not a name. The token went **opaque**. Your self-read still works:

> `Method: GET · Target: clancy (yours) · Isolates: the feature is intact — the owner still reads his own profile`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8308
Authorization: Bearer <clancy-token>
```

Response — **`200`**, `{"handle":"clancy","displayName":"Clancy Park","email":"clancy@mail.example"}`.

Now repeat the forge. `echo -n alice | base64` still produces `YWxpY2U=`, but send it:

> `Method: GET · Target: alice · Isolates: the forged token is unknown to the server now`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8308
Authorization: Bearer YWxpY2U
```

Response — **`401`**, body `Unauthorized`. The server does not recognize the token: it was never issued, so it is not in the `token -> user` map, and there is no identity *inside* it to decode. **The token no longer says who you are — only the server's record does.** The ownership `403` and the missing-token `401` are unchanged: `GET /users/alice` with `clancy`'s real token is still `403`, and no token is still `401` with `WWW-Authenticate: Bearer`.

The fix is the authentication block: `randomBytes` and a stored binding at login, `TOKENS.get` at resolution. [`DIFF.md`](./DIFF.md) works through it — why identity must not travel inside the token at all, why the change touches three inseparable points rather than one line, and why *signing* the token (the tempting near-fix) blocks this exploit yet keeps the identity in the token and so solves the wrong problem.

The walkthrough ends here. The finding is an identity forged from a public name; the fix is a token the client cannot author.
