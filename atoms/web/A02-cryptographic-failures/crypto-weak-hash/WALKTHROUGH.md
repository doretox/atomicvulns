# Walkthrough — crypto-weak-hash

The app is a login API: you send a username and password, it re-hashes the password and compares it to the hash it stored at signup. The login logic is correct. The problem is the primitive it chose to store with: MD5, no salt. A hash is one-way — you don't decrypt an MD5 — but MD5 is a fast, general-purpose hash, and without a salt the same password always yields the same digest. So, given a hash pulled from a leaked database dump, you recover the original password with a pre-computed table of hash→password (a rainbow table). With the password, you log in as the victim.

The track is **a terminal** — build the rainbow table and crack the hash with RainbowCrack — plus **Burp Suite (Repeater)** to prove the recovered password logs in. Cracking a hash is something Burp can't do, so, the same way a browser runs JavaScript for a client-side bug, the tool that does that part of the job joins the primary track. There is no browser.

## 1. Context

A small login API on `127.0.0.1:8031` (vulnerable) and `127.0.0.1:8131` (fixed):

- `GET /` — a JSON banner. Not the target.
- `POST /login` — JSON `{"username", "password"}`. Looks the user up, re-hashes the submitted password, compares it to the stored hash, and returns `200 {"authenticated": true}` or `401 {"authenticated": false}`.

This atom is **A02 — Cryptographic Failures**: the primitive chosen to protect the stored secret is the wrong one.

Terms, defined once:

- **Hash / one-way function.** MD5 maps a password to a fixed 128-bit digest. There is no inverse — you cannot "decrypt" a hash. So you don't invert it; you attack by *trial*: guess a candidate password, hash it, compare to the target. Match means you found the password.
- **Salt.** A unique random value mixed into the password before hashing, so the *same* password produces *different* hashes. Without a salt, `md5("adm1n")` is always the same digest — which is exactly what makes a pre-computed table reusable.
- **Rainbow table.** A pre-computed table that maps hashes back to passwords across an entire keyspace. It's a **time-memory tradeoff**: storing every hash→password pair would cost too much memory, and recomputing every guess for every crack would cost too much time, so a rainbow table pre-computes *chains* of hashes and stores only their endpoints — you pay the heavy pre-computation once, then look up fast.
- **Dictionary attack.** The other way to guess in bulk: hash a list of likely passwords. (That's how the sibling [`jwt-weak-secret`](../jwt-weak-secret/) cracks its secret.)
- **Password KDF (key derivation function).** A hash *purpose-built* for passwords — deliberately **slow**, with a tunable **cost / work factor**, and a salt built in. `bcrypt` is one; it's the fix here.

The starting point is a **premise**: assume you already hold the `users` table from a database dump — however it leaked. The app never returns the hash over HTTP; pulling it out of the app would be a *different* vulnerability. The dumped `admin` row is:

```
admin:d9da8170e8bc9f27b2d32a6c9a6c697d
```

That 32-hex value is an unsalted MD5. From here, everything is offline.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). Storage and verification:

```python
def store_hash(password):
    return hashlib.md5(password.encode()).hexdigest()

def verify(password, stored):
    return hashlib.md5(password.encode()).hexdigest() == stored
```

The login logic is *correct* — it re-hashes the submitted password and compares, and the lookup query is parameterized (no SQL injection). The bug is not a missing check or a broken comparison. The bug is the **primitive**: `md5(...)`, with no salt. The audit question isn't "does it verify?" — it does. It's "is MD5, unsalted, the right thing to store a password with?" — and it is not: fast plus unsalted means a leaked hash is recoverable from a pre-computed table.

## 3. Exploitation — recover the password with a rainbow table

This runs at your terminal, with [RainbowCrack](https://en.wikipedia.org/wiki/RainbowCrack): `rtgen` builds tables, `rtsort` sorts them, `rcrack` looks a hash up. The password space we're attacking is small: `adm1n` is five characters, all lowercase letters and digits — the `loweralpha-numeric` charset. That's 36⁵ = 60,466,176 candidates, small enough for a rainbow table to cover the *whole keyspace*. No wordlist needed — this catches passwords that aren't clean dictionary words.

### Step 1 — Build the rainbow table (watch the pre-computation)

`rtgen` pre-computes the table for MD5 over that keyspace. This is the expensive part — and the whole point of the tradeoff: you pay up front, once, to turn every later crack into a fast lookup.

```
rtgen md5 loweralpha-numeric 5 5 0 3800 40000 0
```

That's: hash `md5`, charset `loweralpha-numeric`, length `5` to `5`, table index `0`, chains `3800` long, `40000` of them.

```
rainbow table md5_loweralpha-numeric#5-5_0_3800x40000_0.rt parameters
hash algorithm:         md5
charset name:           loweralpha-numeric
charset data:           abcdefghijklmnopqrstuvwxyz0123456789
charset length:         36
plaintext length range: 5 - 5
reduce offset:          0x00000000
plaintext total:        60466176

sequential starting point begin from 0 (0x0000000000000000)
generating...
40000 of 40000 rainbow chains generated (0 m 5.4 s)
```

A single table covers only ~86% of the keyspace — chains collide and merge, and no one table gets past that ceiling. To close the gap you generate a few tables that each use a *different reduction function*, selected by the **table index** (the `0` above). Repeat with index 1 through 4:

```
rtgen md5 loweralpha-numeric 5 5 1 3800 40000 0
rtgen md5 loweralpha-numeric 5 5 2 3800 40000 0
rtgen md5 loweralpha-numeric 5 5 3 3800 40000 0
rtgen md5 loweralpha-numeric 5 5 4 3800 40000 0
```

Each prints a stepped `reduce offset` — `0x00010000`, `0x00020000`, … — the knob that makes its chains independent of the others, so the five together cover well over 99.9%:

```
reduce offset:          0x00010000
40000 of 40000 rainbow chains generated (0 m 5.8 s)
```

Five small tables, pre-computed.

### Step 2 — Sort the tables

`rcrack` needs the tables sorted for fast lookup:

```
rtsort .
```

### Step 3 — Crack the hash

Now the payoff of the tradeoff — look the dumped hash up:

```
rcrack . -h d9da8170e8bc9f27b2d32a6c9a6c697d
```

```
5 rainbow tables found
...
plaintext of d9da8170e8bc9f27b2d32a6c9a6c697d is adm1n

statistics
----------------------------------------------------------------
plaintext found:                             1 of 1
total time:                                  0.38 s
...
result
----------------------------------------------------------------
d9da8170e8bc9f27b2d32a6c9a6c697d  adm1n  hex:61646d316e
```

The pre-computation took seconds; the lookup took **0.38 s**. The admin's password is `adm1n`. You did not decrypt the hash — MD5 has no inverse — you recovered the original password by pre-computing the keyspace and looking it up.

### Step 4 — Log in as the victim (Burp)

Point Burp at `127.0.0.1:8031` and send the recovered credential from Repeater:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8031
Content-Type: application/json

{"username": "admin", "password": "adm1n"}
```

Response — `200`:

```json
{"authenticated":true}
```

Account taken over. The leaked hash became the live password, and the password logged you in.

> This is a local lab: both apps bind to `127.0.0.1`, the data is dummy (`adm1n` is an obviously fake password, the users are fake), and the crack ran entirely offline on your own machine. Nothing here leaves the box, and nothing is destructive.

## 4. What the vuln is NOT

Four wrong conclusions to kill.

**It is not that `adm1n` was a weak password.** A short password *helps* (the keyspace is small), but the flaw this atom isolates is the *storage*. The proof is categorical: the fixed side stores the **same** password `adm1n` — and the rainbow table recovers nothing there (next section). Same password, different outcome: the difference is 100% the primitive.

**It is not that you "decrypted" the hash.** MD5 is one-way; it has no inverse. You recovered the password by pre-computing candidate→hash pairs and looking the target up — a keyspace search, not decryption.

**It is not that "MD5 has collisions."** MD5's collision weakness is irrelevant here — you didn't find a collision, you found the *original* password. SHA-256, which has no known collisions, stored unsalted would fall exactly the same way, because it is just as *fast*. The cause is a fast, unsalted primitive — not MD5's specific brokenness.

**It is not information disclosure or injection.** No app bug leaked the hash (nothing returns it), and no input became code (the query is parameterized). The dump is the assumed starting point; the one flaw is the storage primitive.

## 5. Impact

Credential recovery leading to account takeover. From a leaked hash you recover the victim's *real* password and log in as them — here, the administrator. And because people reuse passwords, a password recovered from one system's dump often opens accounts on *other* systems. It is **not RCE** — no code execution — and the ceiling is whatever the recovered credential unlocks. But for a stored credential, "recovered" is the whole ballgame: the secret the hash was supposed to protect is now in the attacker's hands.

## 6. Why the fix works

Run the same attack against the fixed API on port **8131** (see [`DIFF.md`](./DIFF.md)). Its `users` table, dumped, stores the admin as bcrypt:

```
admin:$2b$12$P5nBP/bbDFwHcd1aR6UEneKKcUXJNOvBN4wZ24d0G3FkYG9BT4yWu
```

The rainbow table is not *slower* here — it is **inapplicable**, and you can see that by inspection, without running a crack:

- The stored value is a **salted** bcrypt hash (`$2b$...`, 60 characters), not a 32-hex MD5. `rcrack` against an MD5 table wouldn't even accept it.
- More fundamentally, **RainbowCrack cannot target bcrypt at all**. Its `rtgen` only builds tables for unsalted hashes — run it with no arguments and the menu is:

```
hash algorithms implemented:
    lm HashLen=8 PlaintextLen=0-7
    ntlm HashLen=16 PlaintextLen=0-15
    md5 HashLen=16 PlaintextLen=0-15
    sha1 HashLen=20 PlaintextLen=0-20
    sha256 HashLen=32 PlaintextLen=0-20
```

  No bcrypt. And that is not an omission: pre-computation is *meaningless* under a per-hash salt. The salt makes every hash unique, so there is no single hash→password table to build — you'd need a separate table for every possible salt. There is nothing to generate, so there is nothing to look the hash up in.

Two honest caveats, so you don't over-read this. The salt defeats *pre-computation* — rainbow tables — categorically. bcrypt *also* helps against the other technique: its deliberate slowness (a tunable cost factor, `$12$` in the hash above) makes a live dictionary or brute-force attack far more expensive per guess. Salt and slowness together, from one primitive — that's the point.

The isolation proof: log in with the correct password on **both** ports and you get an identical `200` — the login works the same on each side. Only the offline crack differs, and that difference traces purely to the storage primitive.

The fix is one thing: swap the primitive. Not "a stronger hash" (SHA-256 is just as fast), not "just a salt" (a salt alone on a fast hash still loses to a dictionary), not "more validation." A slow, salted password KDF. See [`DIFF.md`](./DIFF.md) for the diff and why those two trap fixes don't hold.
