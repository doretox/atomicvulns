# DIFF — vulnerable vs. fixed

The fix is one thing: make the check-and-act **atomic**. The vulnerable app reads the balance, checks it in Python, then writes the debit — three separate steps with a gap between the check and the write. The fixed app folds the check into the write as a single conditional `UPDATE` that the database serializes per row. Everything else — `GET /`, `GET /balance`, `POST /reset`, the per-request connection, `requirements.txt`, the `Dockerfile` — is identical, so the atomicity of the debit is the *only* difference between the two apps.

## The change — `app.py`

```diff
-import time
 ...
 @app.route("/withdraw", methods=["POST"])
 def withdraw():
     amount = (request.get_json(silent=True) or {}).get("amount")
     conn = db()
     try:
         cur = conn.cursor()
-        cur.execute("SELECT balance FROM accounts WHERE id = 1")   # 1. read
-        balance = cur.fetchone()[0]
-        if balance < amount:                     # 2. check, in Python (maybe stale)
-            return jsonify({"error": "insufficient funds"}), 409
-        time.sleep(0.1)                           # crutch: widen the window
-        cur.execute(                              # 3. write -- no guard in SQL
-            "UPDATE accounts SET balance = balance - %s WHERE id = 1", (amount,)
-        )
+        cur.execute(                              # decide AND write, atomically
+            "UPDATE accounts SET balance = balance - %s WHERE id = 1 AND balance >= %s",
+            (amount, amount),
+        )
+        if cur.rowcount == 0:                     # 0 rows changed => didn't cover it
+            return jsonify({"error": "insufficient funds"}), 409
         conn.commit()
         cur.execute("SELECT balance FROM accounts WHERE id = 1")
         return jsonify({"withdrew": amount, "balance": cur.fetchone()[0]})
     finally:
         conn.close()
```

The vulnerable version's guard is a Python `if` on a value read one statement earlier; the `UPDATE` that follows carries no condition. The fixed version moves the guard **into** the `UPDATE`'s `WHERE` clause and reads `cur.rowcount` to learn what happened. The `time` import goes with the sleep — there is no separate step left to wait in.

## Why this fixes the bug

`UPDATE ... WHERE id = 1 AND balance >= amount` makes the database do the deciding and the writing in one indivisible step. To run it, Postgres takes a **row lock** on account 1 — only one transaction may hold it at a time — evaluates `balance >= amount` against the row's **current** committed value, and writes, then releases the lock for the next transaction. So when twenty requests arrive together, Postgres lines them up on that lock: the first sees `100`, debits to `0`, and its `rowcount` is `1`; every one after it, re-checking `balance >= 100` under the lock against the now-current `0`, matches no row, changes nothing, and its `rowcount` is `0` — a `409`. The condition can never be evaluated against a value that a concurrent write is about to invalidate, because the write *is* the same locked statement. No gap, no window, no race.

## The cause is non-atomicity — not "missing validation," not a "missing guard"

The tempting misreading is that the vulnerable app "forgot to check the balance." It did not. `if balance < amount: return 409` is right there, and it works: run one withdrawal at a time and the app correctly refuses to overdraw — the baseline in `WALKTHROUGH.md` shows the second sequential withdrawal getting a `409` on the vulnerable app, identical to the fixed one. The guard exists and enforces the rule sequentially. What it does not do is stay **atomic** with the write it guards: the check runs on a value that a concurrent request can make stale before the write lands. Isolation proof: a single, non-concurrent withdrawal behaves identically on both apps; only the concurrent burst separates them. The cause is the non-atomic check-then-act, nothing else — which is why this is a *design* flaw (A04), not a forgotten line.

## Trap: "just check again"

The instinct is to re-read the balance and re-check it immediately before the write:

```python
# STILL VULNERABLE -- do not do this
cur.execute("SELECT balance FROM accounts WHERE id = 1")
if cur.fetchone()[0] < amount:
    return jsonify({"error": "insufficient funds"}), 409
cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = 1", (amount,))
```

This just moves the window; it does not close it. Between that second `SELECT` and the `UPDATE` there is the same kind of gap, and concurrent requests fall into it exactly as before. You can add a third check and a fourth — each one still has a gap between *it* and the write. The number of checks is not the problem; the fact that the check and the write are **separate operations** is. Only making them one atomic operation removes the window.

## Trap: an application lock works in one process — but does not scale

A real, honest partial answer is to wrap the critical section in an application-level lock:

```python
LOCK = threading.Lock()
...
with LOCK:                       # only one thread in the critical section at a time
    # read, check, write
```

This **works** — in a single process. It is genuine mutual exclusion: only one thread enters the read-check-write at a time, so the thread-versus-thread race disappears, and against this atom's single-process Flask server it would hold. Be precise about why it is not the general fix: it does not scale past **one process**. Run the app under multiple workers, or on two servers behind a load balancer, and each process has its **own** `threading.Lock` in its own memory — they do not share it — so two requests handled by two processes are unsynchronized and the race comes back. The conditional `UPDATE` pushes the mutual exclusion down to the **database**, the one point every process already shares, which is why it is the idiomatic and scalable fix. The lock is a legitimate fix for a single process, not a wrong idea — just one that stops working the moment you scale out.

## The sleep is a didactic crutch — the fix makes it moot

The `time.sleep(0.1)` in the vulnerable app is a **named crutch**, not the vulnerability. It widens a window that already exists — the gap between a `SELECT` and a later `UPDATE` is inherent to reading, checking, and writing in separate steps — so that the demo reproduces the full `−1900` every run instead of a timing-dependent partial overshoot. Remove it and the flaw is still real; it is just harder to hit reliably by hand. The fixed app has no sleep because it has no separate step to wait in: the conditional `UPDATE` closes the window regardless of timing. If you were skeptical that the fix only "wins" because it is faster, add the same `time.sleep(0.1)` before the conditional `UPDATE` in the fixed app and run the burst again — it still lets exactly one withdrawal through. The correctness is the atomicity, not the speed.

## `SERIALIZABLE` also fixes it — the conditional `UPDATE` is just the minimal fix

To be complete and honest: the conditional `UPDATE` is not the *only* correct fix. Running the original read-check-write inside a transaction at the **`SERIALIZABLE`** isolation level also closes the race — Postgres detects that the concurrent transactions cannot be ordered consistently and aborts one with a serialization error, so the loser must retry. That is a legitimate, correct approach, and the right one when the critical section spans several statements that cannot be collapsed into one. Here it would be heavier than the problem needs: it means catching the serialization failure and looping to retry. The conditional `UPDATE` is the minimal, most direct fix — one statement, no retry loop — which is why the atom uses it. Both are correct; the single-statement fix is simply the smallest one that does the job.

## The impact is a violated business invariant — and there is no malicious input

The race drives the account into a state the business rules forbid: a negative balance, a withdrawal past the balance, a limit overrun in any shape (redeeming one voucher many times, spending a gift card twice, overselling stock). No overclaim — this is not code execution and not credential theft; the ceiling is the inconsistent state the race produces. What most sharply distinguishes this class from the others in this repo is that **there is no malicious input at all**. Every earlier atom's exploit changes *something* about the request; this one changes only its timing:

| Atom | What the attacker's request carries |
|---|---|
| [`sqli-union-basic`](../../A03-injection/sqli-union-basic/) and the injection atoms | a **payload** — the input carries syntax or code |
| [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) | a **swapped number** (`/notes/1` → `/notes/2`) — legitimate data, but different |
| [`mass-assignment`](../../A01-broken-access-control/mass-assignment/) | an **extra field** in the body (`"is_admin": true`) |
| [`cors-wildcard`](../../A05-security-misconfiguration/cors-wildcard/) | a **forged header** (the attacker's `Origin:`) |
| **`race-condition-basic`** (this atom) | **nothing** — byte-for-byte a legitimate withdrawal; only the concurrency differs |

The rule of thumb: a race condition is not a bad request, it is a bad *schedule*. The defense is not to inspect the request harder — it is legitimate — but to make the state change that acts on it **atomic**.
