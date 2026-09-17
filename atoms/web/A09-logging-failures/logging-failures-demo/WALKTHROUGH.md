# Walkthrough — logging-failures-demo

The app is a small account API with one route that matters: `POST /login`. It checks an email and password against a stored hash and answers `200` (authenticated) or `401` (wrong). The login is correct — parameterized query, properly hashed passwords, a clean `401`. The flaw is what happens *around* the `401`: on the vulnerable side, an authentication failure is recorded **nowhere** that means anything to security. So when an attacker runs a **brute-force** against one account, the attack leaves no trail — it is invisible. This atom's proof is not something appearing on screen; it is the **contrast between two logs** produced by the *same* attack: the vulnerable side is blind, the fixed side sees.

The track is **Burp Suite** — you drive the brute-force burst against `POST /login` with **Intruder** (or a repeated **Repeater** request). The proof is read **outside** Burp, in the server's own output: `docker compose logs vulnerable` versus `docker compose logs fixed`. There is no browser — the proof is log text, not a screen.

## 1. Context

A small account API on `127.0.0.1:8038` (vulnerable) and `127.0.0.1:8138` (fixed):

- `GET /` — a JSON banner. Not the target.
- `POST /login` — JSON `{"email", "password"}`. Verifies against the stored password hash; returns `200 {"authenticated": true}` or `401 {"authenticated": false}`. This is the target of the brute-force and the one place the two sides differ.

This atom is **A09 — Security Logging and Monitoring Failures**: the category about being able to *know* an attack happened — to detect it, respond, and reconstruct it later. It is the odd one out in this repo: there is no payload that makes a marker file appear, nothing leaks, no account is taken over. The whole lesson is what the vulnerable side *fails to write down*.

Terms, defined once:

- **Brute-force / credential stuffing.** A **brute-force** login attack tries **many passwords** against one account until one works — hammering `victim@lab` with `123456`, `password`, `qwerty`, and so on. **Credential stuffing** is its cousin: replaying **leaked** email:password pairs against many accounts, betting on password reuse. Both produce the same observable signal — **a burst of authentication failures** — and that signal is exactly what a security log needs to capture.
- **Security event.** An occurrence a security team needs to know about: an authentication failure, a denied access, a privilege change, a sensitive action. It is distinct from an ordinary *operational* event (some request arrived). This atom is about one security event: the **authentication failure**.
- **Security log / audit trail.** The record of **who did what, when, and from where** — the history of security events. It is what a responder reads during an incident and what a forensic analyst uses afterward to reconstruct what happened. Treated as evidence, it is an **audit trail**.
- **Structured log.** A log line with **clear fields**, legible to a human *and* parseable by a machine — a **SIEM** (Security Information and Event Management: the platform that aggregates logs and fires alerts). `... WARNING security authentication failure account=victim@lab ip=10.0.0.5` has identifiable fields (`account=`, `ip=`) a tool can filter, count, and alert on. A loose sentence (`"login failed"`) helps neither.
- **Access log vs security log — the key distinction.** The **access log** records **every request** generically: source IP, timestamp, method, path, status (`10.0.0.5 - - [...] "POST /login" 401`). It captures the **transport**, and is blind to security: it does not know **which account** a `POST /login` targeted (the email is in the *body*, not the URL), it does not classify the `401` as an authentication failure (to it, a status is a status), and it does not **aggregate** ("this is the twentieth `401` from the same source against the same account"). The **security log** records the **events that matter**, with the context that makes them actionable: the event, the target account, the source, and — summed up — the pattern (`possible brute-force`).
- **Detection vs prevention.** **Prevention** *blocks* an attack (rate-limiting, account lockout, a WAF). **Detection** *sees* it (the security log plus an alert). They are different, complementary defenses — you want both. **A09 is about detection**: the ability to *know*. This atom fixes the blindness (detection); it does **not** add a block (prevention).
- **Why you never log the secret.** The security log records the **fact** of a failure (that one happened, to which account, from which IP, when) — **never the secret** (the attempted password, tokens, PII). A log is read by many people, replicated, and retained for a long time; writing a password into it turns the log itself into a credential leak (which is *also* an A09 failure). Log the **fact**, not the **secret**.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py) and read the failure path of `login()`:

```python
    if row and check_password_hash(row["password_hash"], password):
        return jsonify({"authenticated": True})
    # (nothing here)
    return jsonify({"authenticated": False}), 401
```

The audit question is **not** "is the login wrong?" — it is not; it rejects the wrong password with a clean `401`, exactly as it should. The question is **"when this returns `401`, what does the system record about the event?"** The answer: nothing security-relevant. A wrong password *is* a security event — someone failed to authenticate as `email` from some source IP — but no security line is written. The only thing that survives is the web server's generic access log, which cannot name the targeted account and cannot tell an attack from a typo. The fix (section 7) does not touch the login; it *adds* the missing record.

## 3. Baseline — the login works, identically

First, so you know what "normal" is. Point Burp at `127.0.0.1:8038` (vulnerable). A correct login:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8038
Content-Type: application/json

{"email": "victim@lab", "password": "victim-lab-pw"}
```

```
HTTP/1.1 200 OK
{"authenticated":true}
```

A single wrong password:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8038
Content-Type: application/json

{"email": "victim@lab", "password": "hunter2"}
```

```
HTTP/1.1 401 UNAUTHORIZED
{"authenticated":false}
```

Both responses are **identical on the fixed side (8138)**. One isolated `401` is routine — a user mistyping — not an alarm. The story only changes when the failures come in a **burst**.

## 4. The attack — the same burst, and the two logs

### Step 1 — Run the brute-force burst (Burp Intruder), vulnerable side

Send the `POST /login` request to **Intruder**. Mark the password value as the single payload position (Sniper):

```
POST /login HTTP/1.1
Host: 127.0.0.1:8038
Content-Type: application/json

{"email": "victim@lab", "password": "§123456§"}
```

Load a list of common passwords as the payload set — the kind of list a real brute-force uses:

```
123456
password
12345678
qwerty
123456789
letmein
football
iloveyou
admin
welcome
... (20 in all)
```

Start the attack. All twenty responses come back `401` — the list does not contain `victim@lab`'s real password, so the burst never succeeds. That is fine: this atom is not about *stopping* the attack, it is about *seeing* it. (A repeated Repeater send, or Turbo Intruder, does the same job.)

### Step 2 — Read the vulnerable log: blind

```
$ docker compose logs vulnerable
```

```
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "GET / HTTP/1.1" 200 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:27] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:27] "POST /login HTTP/1.1" 401 -
   ... (twenty identical "POST /login 401" lines in all)
```

That is the whole record of the attack. Twenty `401`s, all identical. Nothing here says which account was targeted (the email was in the body, which the access log never sees), nothing labels these as authentication failures, and nothing aggregates them into "an attack." Twenty break-in attempts against `victim@lab` are indistinguishable from twenty people fat-fingering their own password. A monitoring pipeline keyed on security events gets **nothing**, because nothing security-relevant was emitted.

Note what this is *not*: it is **not** "no log." The generic HTTP access log is right there. It is the log at the **wrong altitude** — transport, not security. That distinction is the whole atom. (The source IP shows as `172.22.0.1` because, behind Docker, that is the gateway the app sees; the point is the *field*, not the value — a real deployment behind a proxy would record the client's address from `X-Forwarded-For`.)

### Step 3 — Run the same burst against the fixed side (8138)

Repeat Step 1 against `127.0.0.1:8138` — the same request, the same password list:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8138
Content-Type: application/json

{"email": "victim@lab", "password": "§123456§"}
```

Every response is again `401`. The fixed side does **not** lock the account or throttle the source — the attack runs to completion exactly as before. What changes is only what gets written down.

### Step 4 — Read the fixed log: it sees

```
$ docker compose logs fixed
```

```
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "GET / HTTP/1.1" 200 -
fixed-1  | 2026-09-11 15:03:30,071 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,249 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,438 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,610 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,786 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 2026-09-11 15:03:30,786 WARNING security possible brute-force against victim@lab from 172.22.0.1 (5 failures)
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
   ... (the INFO security line repeats for each of the twenty attempts; the WARNING fires once, at the fifth)
```

Same attack, same twenty `401`s — but now every failure is on the record as a **security event**: the event (`authentication failure`), the **target account** (`account=victim@lab`), the **source** (`ip=172.22.0.1`), and a **timestamp**. And once five failures against one account pile up, a `WARNING` names the pattern outright: `possible brute-force against victim@lab from 172.22.0.1`. This is what a responder or a SIEM needs — it turns a wall of identical `401`s into a named, attributable, alertable attack.

Two things to notice. First, the generic access log is **still there** — the same lines as the vulnerable side. The security log was *added alongside* it; the contrast is security-absent versus security-present, not no-log versus log. Second, the attempted passwords (`123456`, `qwerty`, …) appear **nowhere** in the log. The record is the fact — failure, account, source, time — never the secret.

> This is a local lab: both apps bind to `127.0.0.1`, the users and passwords are dummy (`victim@lab`, obviously fake lab passwords), and the "attack" is a burst of wrong-password logins from a list — nothing here is destructive and nothing leaves the box. The burst never even guesses the password; that is not the point.

## 5. What the vuln is NOT

Five wrong conclusions to kill. Each keeps this atom distinct from a neighbour.

**It is NOT rate-limiting (or a lockout).** The fixed side **detects and records** the brute-force; it does **not block** it — every one of the twenty attempts still returns `401`, and the attacker could keep going. Locking the account or throttling the IP would be a fine *additional* defense, but it is **prevention** — a different thing. Adding it here would change the lesson to "the login needed a lockout," which is not this flaw. The hole is the **blindness**, not the missing lock.

**It is NOT logging the secret.** The fix records the **event** — failure, account, IP, timestamp — and never the attempted password. Writing the password into the log is the *opposite* anti-pattern: it turns the log into a credential leak, and it is **also** an A09 failure. Log the fact, not the secret.

**It is NOT a bug in the login.** The login works and is **byte-for-byte identical** on both sides (same parameterized query, same `check_password_hash`, same `200`/`401`). It rejects wrong passwords correctly. The flaw is that it is **blind** to the attack — it leaves no security record of it.

**It is NOT like the other atoms.** Everywhere else in this repo you prove the vulnerability by making *something happen* — a marker file, leaked rows, a takeover. Here the proof is the **absence** of a trail on the vulnerable side versus the trail on the fixed side: the *same* attack, one log blind and one that sees. The attacker's "win" on the vulnerable side is precisely that **nothing was recorded**.

**It is NOT about stopping the brute-force.** The burst need not guess the password at all — all twenty attempts fail, and the lesson is complete. The point is not to prevent the attack; it is to *see* that it happened. (Making the burst succeed would slide the focus onto "weak password" or "no lockout" — different categories.)

What it **is**, surgically: a security event — a burst of authentication failures against one account — happens and is **not recorded**. The vulnerable side is blind (only the generic access log); the fixed side sees (a structured security line per failure, plus a WARNING at the threshold). The fix generates the missing security log — logging the fact, never the secret, and without blocking the attack.

## 6. Impact

Blindness. On the vulnerable side the brute-force runs and appears **nowhere** a monitoring system would catch: nobody is alerted, the incident-response team has nothing to investigate, and a forensic analyst later has no trail to reconstruct **what** happened, **when**, or **from where**. A09 is, bluntly, "how long until you find out you were breached" — and real-world reports measure that dwell time in **months**. The ceiling of the damage is *not knowing*: in the real world one of those brute-force attempts eventually lands, and with no record, nobody investigates. (That the guess eventually succeeds is a different category — weak password, or a missing lockout; here the point stays on visibility.)

## 7. Why the fix works (port 8138)

You already saw it in Step 4: the **same** attack, now visible. The fixed side changes nothing about the login — same query, same hash check, same `200`/`401`, and the burst still runs to completion unblocked — it only **adds the security log** on the failure path: a structured line per failure (`authentication failure account=… ip=…`), and a `WARNING … possible brute-force …` once five failures against one account accumulate. That is enough to detect the attack and investigate it: which account, which source, when, how many.

The isolation proof: the login (and the generic access log) is identical on both ports; only the security logging separates them. The change is pure **observability** — detection, not prevention, and the fact, not the secret. See [`DIFF.md`](./DIFF.md) for the line-by-line diff and why "just add a lockout" and "just log the attempt" are both the wrong reading of the fix.
