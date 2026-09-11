# DIFF — vulnerable vs. fixed

The login is **identical** on both sides — same parameterized query, same `check_password_hash`, same `200`/`401`. `diff vulnerable/app.py fixed/app.py` shows only four things, all of them logging: the `import logging`, the security-logger setup, one line that resets the failure counter on success, and the enriched failure branch. `requirements.txt` and `Dockerfile` are byte-identical. This is a different *kind* of diff from every other atom: nothing about the app's behavior changes — the fix only makes the existing behavior **visible**.

## The fix — add the security log that was missing

```diff
 import os
+import logging
 import sqlite3
 from flask import Flask, request, jsonify
 from werkzeug.security import generate_password_hash, check_password_hash

 app = Flask(__name__)
 DB_PATH = os.environ.get("DB_PATH", "lab.db")
+
+# How many consecutive failures against one account raise a brute-force WARNING.
+BRUTE_FORCE_THRESHOLD = 5
+
+# In-memory per-account failure counter: email -> consecutive failures. Reset on success.
+FAILURES = {}
+
+# A dedicated SECURITY logger, separate from Werkzeug's generic HTTP access log, writing
+# structured lines to the container's output. A dedicated logger + propagate=False leaves
+# Werkzeug's logger untouched, so the access log still appears on BOTH sides.
+_handler = logging.StreamHandler()
+_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
+security_log = logging.getLogger("security")
+security_log.setLevel(logging.INFO)
+security_log.addHandler(_handler)
+security_log.propagate = False
 ...
     if row and check_password_hash(row["password_hash"], password):
+        FAILURES.pop(email, None)  # a success clears the account's failure streak
         return jsonify({"authenticated": True})
-    # (nothing here — the authentication failure is recorded nowhere security-relevant)
+    # Record the FACT of the failure -- event, account, source IP, timestamp -- NEVER the secret.
+    ip = request.remote_addr
+    security_log.info("authentication failure account=%s ip=%s", email, ip)
+    FAILURES[email] = FAILURES.get(email, 0) + 1
+    if FAILURES[email] == BRUTE_FORCE_THRESHOLD:
+        security_log.warning("possible brute-force against %s from %s (%d failures)",
+                             email, ip, FAILURES[email])
     return jsonify({"authenticated": False}), 401
```

That is the whole change. The failure path — which on the vulnerable side just returns `401` — now emits a structured **security event** for every failure, and once five failures against one account accumulate, a `WARNING` that names the pattern. Nothing else moves: the query, the hash check, the status codes, `init_db`, the seed, and the `threaded=False` server model are the same on both sides.

This is a different *kind* of diff from the rest of the repo. In `deserialization-pickle` the diff is a logic change (`pickle` → `json`); in `debug-enabled` it is a flag (`debug=True` → `False`); in `cve-demo` it is a dependency version in `requirements.txt`. Here the code's behavior is untouched — the login does exactly what it did — and the fix only **adds observability**. The vulnerability is not a wrong line; it is a **missing** one.

## The cause is the missing security log, not a bug in the login

It is tempting to read "the attack is invisible" and hunt for the mistake in `login()`. There is none: the login is correct and **byte-for-byte identical** on both sides. Proof of isolation: a legitimate login returns `200` and an isolated wrong password returns `401` on **both** sides — the feature is the same. Run the *same* brute-force burst against both and the only thing that differs is the record it leaves:

- `docker compose logs vulnerable` → twenty identical `"POST /login" 401` access lines. No account, no "authentication failure", no threshold. **Blind.**
- `docker compose logs fixed` → the same access lines, **plus** a `INFO security authentication failure account=victim@lab ip=…` line per attempt, **plus** a `WARNING … possible brute-force against victim@lab … (5 failures)` at the fifth. **It sees.**

The difference is 100% the security logging. There is nothing to "sanitize" in the login — the same login, with the security log added, makes the same attack visible.

## "Just add a lockout / rate-limit" is a real defense — but it is not this atom's fix

Show this atom to a reviewer and the reflex is immediate: *"lock the account, or throttle the source IP, after N failures."*

That is **true** and worth doing — rate-limiting and lockout are genuine defense-in-depth against brute-force. But they are **prevention** — they *block* the attack — and this atom is about **detection**: being able to *see* it. The fixed side deliberately does **not** block: every one of the twenty attempts still returns `401`, and the attacker could keep going. Adding a lockout would change the lesson to "the login needed a block," which is a different category (a design/prevention flaw) and would bury the A09 point.

The two are not in conflict — you want detection *and* prevention — but they do not substitute for each other, and this atom fixes the one that was missing: **visibility**. The trap to avoid: a reader who walks away thinking "so the fix is rate-limiting" has missed A09 entirely — they would have blocked *this* attack while staying blind to the next one, and to everything a lockout does not catch. (This is the same layered-honesty shape as the salt note in `crypto-weak-hash`, the `safe_load` note in `cve-demo`, or the single-use/expiry note in `weak-password-reset`: the named control has real value, but it is not this atom's root fix.)

## Log the fact, never the secret

Notice which fields the security line carries: the **event** (`authentication failure`), the **account** (`account=victim@lab`), the **source** (`ip=…`), and a **timestamp**. It does **not** carry a `password=` field. That omission is deliberate and it matters: a log is read by many people, shipped to a SIEM, and retained for a long time, so writing the attempted password into it would turn the log itself into a credential dump — the *opposite* anti-pattern, and **also** an A09 failure (sensitive data in logs). Log the **fact**, not the **secret**. (A fuller audit trail would also record login *successes* — who authenticated, when, from where — not just failures; this lab logs the failure path because that is where the lesson lives, but the same "fact, not secret" rule applies to every event you record.)

## The proof is the absence — and how that sets this atom apart

Every other atom in this repo proves its vulnerability by making **something happen**: a marker file appears, rows leak, an account is taken over. This one is the opposite — the vulnerable side's "result" is that **nothing is recorded**, and you see it only by contrast with the fixed side. "One atom, one vulnerability" is about the **cause**, and the cause here is an *absent* security log. The axes that keep this atom distinct from its neighbours:

| Axis | The neighbour | `logging-failures-demo` (38) |
|---|---|---|
| Form of the proof (vs **every** prior atom) | something **appears** — a `/tmp/pwned` marker (`cve-demo`, `deserialization-pickle`), leaked rows (`sqli-union-basic`), a takeover (`weak-password-reset`) | the **absence** of a trail on the vulnerable side vs the trail on the fixed side — the **contrast of two `docker compose logs`** under the same attack |
| Prevention (rate-limiting / lockout) | **block** the brute-force — the attack stops | **see** the brute-force — record each failure + WARN at the threshold; the attack is **not** blocked (`401`s continue). Detection, not prevention |
| Logging the secret (the opposite A09 anti-pattern) | a log that stores the attempted password / tokens / PII — a leak via the log | the log stores the **fact** (event, account, IP, time), **never** the secret |
| The credential (vs `weak-password-reset`, 37) | the auth secret is **predictable** — a flaw in how it is generated (A07) | authentication is **correct**; the failure simply is not **recorded** as a security event (A09) |

## The impact is blindness

The ceiling here is **not knowing**. On the vulnerable side the brute-force runs and surfaces nowhere a monitoring system would catch: no alert, nothing for incident response to open, no trail for a forensic analyst to reconstruct **what** happened, **when**, or **from where**. A09 is, bluntly, "how long until you find out you were breached" — and real-world reports measure that dwell time in **months**. One consequence follows plainly: in the real world one of those brute-force attempts eventually lands, and with no record, nobody investigates. That the guess eventually succeeds is a *different* category — a weak password, or a missing lockout — so the focus stays where the flaw is: on **visibility**.
