# Walkthrough — race-condition-basic

The target is a small account API. `POST /withdraw` does the most ordinary thing: it reads your balance, checks that it covers the amount you asked for, and — if it does — debits it. Three steps. Between the step that *checks* ("does the balance cover it?") and the step that *acts* ("debit it") there is a gap in time: a moment where the decision "you may withdraw" has been made but the debit has not happened yet. Run one withdrawal and nothing goes wrong. Fire twenty withdrawals of the whole balance *at once* and all twenty read the full balance, all twenty pass the check before any of them debits — and all twenty debit. You withdraw twenty times money that only covered one. You injected nothing and forged nothing: you sent the same legitimate request, only simultaneously.

## 1. Context

`POST /withdraw` moves money based on a balance it reads first. To see what goes wrong you need a few terms, defined from scratch.

A **race condition** is a situation where two or more flows of execution run at the same time and the outcome depends on the **order or timing** in which they reach the steps — run them one at a time and the result is always right, but run them together and they interfere. The name is literal: two flows racing for the same resource, and who gets to each step first changes the result. The stretch of code that **reads and then modifies shared state** — here, read the balance and debit it — is the **critical section**; a race is two flows inside it at once, stepping on each other.

This particular race is a **TOCTOU** — **time-of-check to time-of-use**. You *check* a condition (the time of check — "does the balance cover it?") and then *act* on it (the time of use — "debit"). If the state changes between the check and the use, you acted on a truth that had already gone **stale**. The interval between the check and the act is the **window**, and the wider it is, the easier it is for another flow to slip into it.

The fix, named ahead of time, is **atomicity**: an operation is *atomic* when it is **indivisible** — it happens whole or not at all, and no other flow can observe or interleave a state in the middle of it. The three-step read-check-write is *not* atomic (there are two points where another flow gets in); a single database statement that decides *and* writes in one go *is*.

This is **A04 — Insecure Design**: the flaw is in the shape of the flow, not a typo or a forgotten line.

The lab is three services on an internal network: `db` (a shared PostgreSQL, no host port), and the two apps — `vulnerable` at `http://127.0.0.1:8035/` and `fixed` at `http://127.0.0.1:8135/`. The app is **multi-threaded**, so requests really do run concurrently, and each request opens its own database connection. You drive the attack from **Burp**, with the **Turbo Intruder** extension — Section 4 explains why the ordinary tools cannot win a race.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). `POST /withdraw` reads, checks, then writes — three separate steps:

```python
cur.execute("SELECT balance FROM accounts WHERE id = 1")  # 1. read
balance = cur.fetchone()[0]
if balance < amount:  # 2. check, in Python, on a value that may be stale
    return jsonify({"error": "insufficient funds"}), 409
time.sleep(0.1)       # didactic crutch -- widens a window that already exists
cur.execute(          # 3. write -- no guard in SQL; the check lived back in Python
    "UPDATE accounts SET balance = balance - %s WHERE id = 1", (amount,)
)
conn.commit()
```

Audit question: *between deciding the balance covers the amount and actually debiting it, could another request change the balance?* Yes — nothing holds the row between the `SELECT` and the `UPDATE`. The guard `if balance < amount` is there, and it is correct; it just runs on a value read a moment earlier, and the write trusts that now-stale decision. The `UPDATE` itself carries **no** condition — the check lived back in Python, one step removed from the write it was supposed to protect.

The `time.sleep(0.1)` is a **didactic crutch**, and worth being upfront about: it widens a window that **already exists** so the race reproduces every single time. The flaw is real without it — the gap between a `SELECT` and a later `UPDATE` is there whether or not you sleep in it; the sleep just makes it wide enough to hit by hand. More on that once you have seen the race (Section 4), and on why the fix makes the sleep irrelevant (Section 7).

## 3. Baseline — the guard works one request at a time

Before the race, prove the guard is not simply missing. Reset the balance to 100 and withdraw twice, one after the other:

```
$ curl -s -X POST 127.0.0.1:8035/reset
{"balance":100}
$ curl -s -X POST -H 'Content-Type: application/json' -d '{"amount":100}' 127.0.0.1:8035/withdraw
{"balance":0,"withdrew":100}
$ curl -s -X POST -H 'Content-Type: application/json' -d '{"amount":100}' 127.0.0.1:8035/withdraw
{"error":"insufficient funds"}
```

The first withdrawal succeeds (balance 100 → 0); the second, over a balance of 0, is refused with `409`. The vulnerable app **rejects** the over-withdrawal — sequentially. Run the identical sequence against the fixed app on `:8135` and you get the identical result. So the difference between the two apps is *not* the guard: both have it, both enforce it one request at a time. Only concurrency will separate them.

## 4. Exploitation (in Burp, with Turbo Intruder)

**Why the ordinary tools cannot win.** Repeater sends one request at a time — there is never a second flow to race. The standard Intruder can send in parallel, but the network **serializes** the requests: even a few microseconds of jitter mean one arrives, reads, checks, and *writes* before the next one reads — and once the first debit commits, the guard on the second correctly refuses it. To land several requests inside the window *before any of them writes*, they have to arrive **together**.

That is the **single-packet attack**: a technique (PortSwigger's) that makes N requests hit the server at the same instant, neutralizing network jitter. Over HTTP/2 it packs the final bytes of 20–30 requests into a single TCP packet; over HTTP/1.1 — which this Flask dev server speaks — Turbo Intruder uses the equivalent **last-byte synchronization**: it sends all but the final byte of each request, holds them at a *gate*, then releases the last bytes together. Either way, the requests complete at once. Install **Turbo Intruder** from Burp's **BApp Store** (Extensions → BApp Store) — this is the one extension the atom needs, and the reason is the lesson itself: a race only reproduces with genuinely simultaneous requests.

Open **Turbo Intruder** from Burp's top menu and choose **Run script** — its window opens pre-filled with an `example.com`, port `443`, `https` example. Correct those connection fields for this atom: set **Host** to `127.0.0.1`, **Port** to `8035`, and **Protocol** to `http`. Paste the request into the request panel and the script into the script panel. The request is just the legitimate withdrawal:

```
POST /withdraw HTTP/1.1
Host: 127.0.0.1:8035
Content-Type: application/json
Content-Length: 15

{"amount": 100}
```

For the script panel, use the gate-based race script below. Paste **only the script body** — from the `def queueRequests` line onward — and **not** the surrounding code fence: a stray backtick pasted in makes Turbo Intruder fail with `SyntaxError: expecting BACKQUOTE`.

```
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           engine=Engine.THREADED)
    for i in range(20):
        engine.queue(target.req, gate='race1')
    engine.openGate('race1')

def handleResponse(req, interesting):
    table.add(req)
```

Reset the balance first (`POST /reset` → `{"balance":100}`), then run the attack. Every one of the 20 rows in Turbo Intruder's results table comes back **`200`**, each body a successful `{"balance":...,"withdrew":100}`. Read the final number:

```
$ curl -s 127.0.0.1:8035/balance
{"balance":-1900}
```

Twenty withdrawals of 100 each succeeded from an account that held **100**: `100 − 20×100 = −1900`. The business invariant — never withdraw past the balance — is shattered, and every request that did it was a perfectly legitimate withdrawal. Everything here is benign and local: a fake account, a dummy balance, everything on loopback, nothing destructive.

**Back to the sleep.** It widened the window to a reliable ~100 ms, so all twenty `SELECT`s land before the first `UPDATE` commits — which is why you get the full `−1900` every run instead of an unpredictable partial overshoot. Take the sleep out and the window collapses to microseconds; the race still happens (it is real), it just stops being a sure thing in a demo. The point is the **window**, not the sleep — and the fix closes the window no matter how wide it is.

## 5. What the vuln is NOT

The request is an ordinary withdrawal, so isolate what actually went wrong:

- **NOT malicious input or injection.** The request is **byte-for-byte identical** to a legitimate withdrawal — a normal amount the balance can cover. The only difference is that twenty copies arrived at once. This is the axis that sets this atom apart from every earlier one: in the injection atoms the attacker's request carries a payload, in [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) it carries a swapped number — here it carries nothing different, only different *timing*.
- **NOT missing validation.** The vulnerable app **does** check `balance >= amount`; the guard exists. Section 3 proves it works sequentially, identically on both apps.
- **NOT a missing guard or limit.** The guard is right there. The flaw is **temporal** — the window between check and write — not the absence of a check.
- **NOT a one-off code bug.** It is a **design** flaw (A04): a non-atomic check-then-act is a *pattern*, not a typo or a single forgotten line.
- **NOT fixable by "checking again."** Re-reading and re-checking just before the write leaves the same kind of window between that second check and the write. Adding checks does not close the gap; only atomicity does.

What it **is**: a check-then-act split into separate steps, with a window between the check and the write that concurrent, legitimate requests fall into together — each passing the check before any writes, so all of them write, past the limit the check was supposed to enforce.

## 6. Impact

**A violated business invariant.** The concurrent requests drive the account into a state the rules forbid: a **negative balance**, a withdrawal past the balance, the same limit overrun in any shape — redeeming one voucher many times, spending a gift card twice, buying more stock than exists. No overclaim: this is not code execution and not credential theft. The ceiling is exactly the inconsistent state the race produces — here, `−1900` where the floor was `0`. In the real world that is money moved that should not have been, and it is a staple of bug-bounty reports against payment, coupon, and balance flows.

## 7. Why the fix works

Now confirm the fix — with one caveat about the setup. **Both apps share the same `accounts` table** in the same `db` container, so `GET /balance` reflects whatever the last burst left, no matter which app received it. To test the fixed app cleanly you must therefore do two things: **reset the balance on `:8135`** (`POST /reset` to `http://127.0.0.1:8135/reset` → `{"balance":100}`) *before* the burst, and **change the Port in the Turbo Intruder window from `8035` to `8135`** — otherwise the burst still lands on the vulnerable app and you will see `−1900` in `/balance` even though you meant to point at the fixed one.

With the balance reset and the port set to `8135`, run the **same** 20-request script. Now the results table shows exactly **one** `200` and nineteen `409`s, and the balance lands where it should:

```
$ curl -s 127.0.0.1:8135/balance
{"balance":0}
```

That combination — one `200`, nineteen `409`s, and a final balance of `0` on `:8135` — is the proof the fix holds: one withdrawal succeeded from a balance of 100, and every other was correctly refused. The fix ([`fixed/app.py`](./fixed/app.py)) makes the check-and-act a single, indivisible statement:

```python
cur.execute(
    "UPDATE accounts SET balance = balance - %s WHERE id = 1 AND balance >= %s",
    (amount, amount),
)
if cur.rowcount == 0:
    return jsonify({"error": "insufficient funds"}), 409
conn.commit()
```

Two terms to make that precise. A **transaction** is a group of database operations the database treats as one unit, with rules about what concurrent transactions see of each other. The **conditional `UPDATE`** puts the check *inside* the write — `WHERE id = 1 AND balance >= amount` — so the database, not Python, decides and writes at the same instant. When Postgres runs it, it takes a **row lock** — a guarantee that only one transaction touches that row at a time, which is **mutual exclusion** — re-checks `balance >= amount` against the row's **current** value, and writes, all as one step. `rowcount` reports the outcome: `1` debited, `0` means the condition failed and nothing changed.

There is no read-check-write gap, so there is no window to race. The twenty requests still arrive together and the server is still multi-threaded; Postgres simply serializes them on the row. The first sees `100`, debits to `0`, returns `200`. Each of the others, re-checking `balance >= 100` under the lock against the now-current `0`, fails, changes nothing, and returns `409`. And because the atomicity lives in that one statement, timing is irrelevant — this is why the vulnerable app's `sleep` has no counterpart here: there is no separate step to widen.

Note what did **not** change: `GET /`, `POST /reset`, `GET /balance`, the database connection, and the imports (bar the now-unused `time`) are byte-for-byte identical, and the app is just as multi-threaded. The only difference is the **atomicity** of the debit. See [`DIFF.md`](./DIFF.md) for the one-operation change and why "check again," an application-level lock, and `SERIALIZABLE` are the wrong, partial, or heavier answers next to the conditional `UPDATE`.
