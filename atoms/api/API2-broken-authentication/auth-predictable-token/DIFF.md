# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` and `fixed/app.ts` differ only in the **authentication block** — how the token is minted and how it is resolved. `POST /login`'s handler, the entire `GET /users/:handle` route (ownership guard and all), the `USERS` seed, the imports apart from one, the bootstrap, the `listen` footer, the `Dockerfile`, `package.json`, `package-lock.json`, and `tsconfig.json` are byte-identical between the two versions (and there are no templates — this atom is API-only). This is the first atom in the series whose diff touches that block at all; in every earlier one it was untouched, crypto-strong infrastructure.

## The fix — an opaque token resolved by lookup, not a name read out of the token

```diff
+import { randomBytes } from "node:crypto";
 ...
+const TOKENS = new Map<string, string>();                   // opaque token -> username (in-memory; NOT a JWT)

 function issueToken(user: string): string {
-  return Buffer.from(user).toString("base64url");           // VULNERABLE: the name, encoded -- not entropy
+  const token = randomBytes(24).toString("base64url");      // crypto-strong opaque value
+  TOKENS.set(token, user);                                  // bind token -> identity, server-side
+  return token;
 }

 function authenticate(req: express.Request): string | null {
-  // VULNERABLE: decode the token and trust whoever it spells.
+  // Authentication only: resolve the Bearer token to a username, or null.
   const header = req.header("authorization") ?? "";
   const token = header.startsWith("Bearer ") ? header.slice(7) : "";
-  return Buffer.from(token, "base64url").toString("utf8") || null;
+  return TOKENS.get(token) ?? null;
 }
```

In the vulnerable build the identity travels **inside** the token: `issueToken` encodes the name, `authenticate` decodes it back, and whoever controls the token controls the identity. In the fixed build the token is an **opaque pointer**: `randomBytes(24)` carries no identity, `issueToken` stores the `token -> user` binding, and `authenticate` resolves it by **lookup**. The two functions do the same job — turn a token into a username — but one *reads the answer off the token* and the other *asks a record the server kept*.

**Read the fix for what it changes: the origin of identity.** The point is not a stronger token. It is moving where identity comes from — out of the token, where the client can author it, into a server-side record, where only the server can. The token stops **asserting** who you are and starts **referencing** an assertion the server made at login. That is why `randomBytes`: an opaque pointer cannot be derived from a handle, because there is nothing inside to decode — only something to look up, and looking up a token no one registered returns nobody (`401`).

> **Identity that travels inside the token is identity the client can author; the fix does not harden the token, it stops reading identity from it.**

## Why the diff touches three points, and why they are inseparable

The change is not one line, and that is deliberate — it is the nature of the class, not a relaxation of "one atom = one vulnerability." The diff moves three things: (i) how `issueToken` mints the token, (ii) how `authenticate` resolves it, and (iii) the presence of the `TOKENS` map. They are three faces of a single decision — *does identity come from the token's content (decode) or from a stored binding (lookup)?* — and they cannot be separated coherently. An opaque token (iii + i) **requires** lookup (ii), because there is no identity inside to decode; a self-describing token (the vulnerable build) **dispenses with** `TOKENS`, because the identity already rides in it. Change one without the others and the logic doesn't hold: a `TOKENS.get` with no `TOKENS.set` authenticates nobody; a `randomBytes` token with no lookup loses the identity entirely. The lesson is **one** — a forgeable identity — expressed, by construction, as a generate/store/resolve trio.

The earlier diffs in this series were one line because the lesson was one projection (a single `res.json`, a single `USERS.set`). Here the lesson is a **mechanism** — how identity is born and resolved — and a mechanism has parts. It is not wider by carelessness; it is wider because the flaw is more fundamental.

## Signing the token looks like the fix — and isn't

A tempting near-fix stops the forge without moving identity out of the token: **sign it**, so a client can't fabricate one.

```ts
// CONSIDERED AND REJECTED -- sign the token so it can't be forged, but keep the identity inside it.
import { createHmac, timingSafeEqual } from "node:crypto";
const SECRET = "changeme";
function issueToken(user: string): string {
  const body = Buffer.from(user).toString("base64url");
  const sig = createHmac("sha256", SECRET).update(user).digest("base64url");
  return `${body}.${sig}`;                                   // name.signature -- still self-describing
}
function authenticate(req: express.Request): string | null {
  const raw = (req.header("authorization") ?? "").replace(/^Bearer /, "");
  const [body, sig] = raw.split(".");
  if (!body || !sig) return null;
  const user = Buffer.from(body, "base64url").toString("utf8");
  const expected = createHmac("sha256", SECRET).update(user).digest("base64url");
  const a = Buffer.from(sig), b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  return user;                                               // verified -- but identity still came from the token
}
```

It **works against this exploit**: an attacker who only knows the name `alice` cannot produce the HMAC without `SECRET`, so a bare `base64url("alice")` is rejected (type-checked and verified against a prototype: a legitimately issued token resolves, an unsigned forge does not). But it solves the **wrong problem**. The identity still travels in the token, now with integrity bolted on. The real fix is more basic: identity should not be derivable from the token at all — the opaque server-side binding is the correction, not patching a self-describing token with a signature. Signing trades "anyone can forge" for "whoever holds the secret can forge, and the token is now a hand-rolled JWT," inheriting all the key- and algorithm-management surface the opaque token simply doesn't have. It also drags the atom into a different class — signatures, algorithm confusion, expiry — which is a separate conversation. The foil is here to close that door on purpose.

At scale, "opaque token + lookup" is what session frameworks do (a random session id mapped to a server-side record); JWTs solve the same problem the other way, with signed claims and their own set of pitfalls. This atom names the principle — identity must not be derivable — not a library; no JWT or HMAC dependency enters the fix (the block above is illustrative only, and `fixed/` imports nothing but `randomBytes`).

## The `401` the vulnerable build cannot give

One behaviour is worth recording because it is the symptom of the whole class. What counts as a "bad token" differs between the builds, and the difference *is* the vulnerability.

In the fixed build, every unregistered token gets `401` — a lookup miss. The category "credentials present but **not recognized**" exists. In the vulnerable build, that category barely does: the server decodes anything and trusts it, so a token that decodes to a **non-empty** string is accepted as *that identity*. A "bad" token therefore lands as:

- an **empty** decode (`""`, `Bearer !!!`, no header) → `null` → **`401`** — the only honest `401` the vulnerable build gives, and it exists by accident of the `|| null`, not by recognizing invalidity;
- a decode to a **non-owner** handle (`base64url("alice")` against `/users/clancy`, or non-UTF-8 bytes like `Bearer ////`) → **`403`** (ownership);
- a decode to a **non-seeded** handle equal to the path (`Bearer Zm9v` = `"foo"` against `/users/foo`) → **`404`**.

So the absence of an honest `401` for "unrecognized token" is the symptom: in the vulnerable build there *is* no unrecognized token — every non-empty decode is recognized as somebody. **A server that never says "I don't know you" is a server that recognizes anyone.** (Verified against the running containers: fixed `Bearer YWxpY2U` → `401`; vulnerable `Bearer YWxpY2U` → `200` against `/users/alice`, `403` against `/users/clancy`. No garbage token ever produces `500` — the decode is total, turning invalid bytes into the U+FFFD replacement character rather than throwing.)

## Status codes — inherited, with one new symptom

The status codes on `GET /users/:handle` are the series' own, not re-argued here:

- **A foreign read → `403`.** `GET /users/alice` with `clancy`'s real token is refused by the ownership guard, which compares the path handle to the caller **before any lookup** — so it reveals no existence and is no enumeration oracle. Same guard, same reasoning as `bfla-method-based`; its [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md) carries the full account, RFC 9110 §15.5.4 and the series' single criterion for `403` vs `404`.
- **A missing or invalid token → `401`** with a `WWW-Authenticate: Bearer` challenge (RFC 9110 §15.5.2); the `403` carries none, because that caller is already authenticated. Also inherited; see the same [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md).

The new argument is the one above: in the vulnerable build the `401` for a *present but unrecognized* credential is missing, because the build recognizes every credential. That is not a status-code style choice — it is the fingerprint of the bug.

## This is Broken Authentication — a forgeable identity

Nothing the caller sends is parsed or executed. A well-formed Bearer token, behind a correct ownership check, reads a profile — and the token proves nothing, because anyone can build it from a public handle. That is **Broken Authentication** — **API2:2023** in the OWASP API Security Top 10. Reading it as BOLA points you at the wrong place (the ownership check is present and correct — `GET /users/alice` with your own token is `403`); reading it as token theft misdescribes the method (nothing was intercepted — the token was fabricated from a name); reading it as weak crypto misses that there is no crypto at all — base64url is encoding, not a cipher. The flaw is prior to all of them: the mechanism that proves identity can be produced by anyone, so every correct authorization check in the system ends up serving the attacker, who *is* the victim as far as the server can tell. The impact is **total impersonation** of any known handle plus access to that user's private data, and it is **not revocable** — a token the server never stored is one it cannot invalidate. Like the rest of the series, the bug lives in `app.ts` and doesn't `grep`: you catch it by asking, of the token, *is this unpredictable to someone who did not receive it?* — and noticing that a correct ownership check was quietly trusted to stand on an identity that anyone can forge.
