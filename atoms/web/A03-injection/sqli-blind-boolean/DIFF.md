# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py` for the `/login` view:

```diff
 @app.route("/login", methods=["POST"])
 def login():
     username = request.form.get("username", "")
     password = request.form.get("password", "")
-    # VULNERABLE: user input concatenated into SQL string
-    query = (
-        f"SELECT username FROM users "
-        f"WHERE username = '{username}' AND password = '{password}'"
-    )
     conn = sqlite3.connect(DB_PATH)
-    row = conn.execute(query).fetchone()
+    row = conn.execute(
+        "SELECT username FROM users WHERE username = ? AND password = ?",
+        (username, password),
+    ).fetchone()
     conn.close()
```

The `templates/` files are identical in both versions — the bug lives entirely in `app.py`. The two response strings (`Welcome, <user>!` and `Invalid credentials.`) are preserved verbatim in the fixed version, on purpose; see the note at the end of this file.

## What changed

The f-string SQL concatenation was replaced with a parameterized query: the statement keeps two literal `?` placeholders, and `username` and `password` are passed separately as a tuple. The vulnerable code had to build a SQL text string from raw input; the fixed code never does — it hands the SQL text and the values to the driver as two separate arguments.

## Why this fixes the bug

When the SQLite driver sees a statement with `?` placeholders, it sends the SQL text and the parameter values to the engine as *separate* arguments. The engine parses the SQL first — without any parameter value — and only afterward binds each input as a literal data value into the pre-parsed statement. No matter what characters either input contains (`'`, `--`, `OR`, `SELECT`, parentheses, newlines, etc.), they stay inside their respective string-literal slots and are never reinterpreted as SQL syntax.

The vulnerable version has the opposite model: the input is already part of the SQL text by the time the engine sees it, so the engine *must* parse it as code. Escaping or blacklisting characters is a losing game — the only fix is to never splice user input into SQL text.

## A note on the oracle

A natural-looking second fix would be to make the response identical on success and failure — render `Login attempt processed.` in both cases, eliminate the asymmetry, and the attacker has no oracle to lean on. That's a workaround, not a mitigation. It hides the symptom while leaving the injection intact: any other observable difference (response time, downstream side effect, log line, second-order behavior) would re-introduce the oracle through a different door.

**Blind SQLi is not mitigated by flattening the two responses — that's a fragile workaround. The mitigation is to remove the injection. Once the input is parameterized, the oracle is no longer something the attacker can control.**

For that reason, the fixed `result.html` in this atom keeps `Welcome, <user>!` and `Invalid credentials.` verbatim. Different responses on different outcomes are normal login behavior. What changes between vulnerable and fixed is not whether the oracle exists — it's whether an attacker can inject a condition that steers it.

## Contrast with `sqli-union-basic`

The diff above looks structurally identical to the one in [`sqli-union-basic`](../sqli-union-basic/DIFF.md): a single concatenated SQL string becomes a parameterized statement, and the bug closes. Two atoms, two exfiltration shapes (`UNION` data leak vs. boolean oracle inference), one fix. That is the lesson worth taking from this pair: the variety in SQL injection lives in the *channel* the attacker exfiltrates through, not in the root cause. Parameterized queries close every channel at once because they remove the precondition (user input becoming SQL syntax) that all of them depend on.
