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
-    conn.execute(query).fetchone()  # result intentionally ignored — response is uniform
+    conn.execute(
+        "SELECT username FROM users WHERE username = ? AND password = ?",
+        (username, password),
+    ).fetchone()  # result intentionally ignored — response is uniform
     conn.close()
     return render_template("result.html")
```

The `templates/` files are identical in both versions — the bug lives entirely in `app.py`. The uniform `Login attempt processed.` response is preserved verbatim in the fixed version, on purpose; see the note below.

## What changed

The f-string SQL concatenation was replaced with a parameterized query: the statement keeps two literal `?` placeholders, and `username` and `password` are passed separately as a tuple. The vulnerable code had to build a SQL text string from raw input; the fixed code never does. Note that `.fetchone()` and the uniform `render_template("result.html")` are unchanged — the response was already identical on every outcome, and it stays that way.

## Why this fixes the bug

When the SQLite driver sees a statement with `?` placeholders, it parses the SQL text first — without any parameter value — and only afterward binds each input as a literal data value into the pre-parsed statement. The entire timing payload — the closing quote, the `CASE`, the recursive CTE, the cross join, the `--` comment — arrives as the *value* of `username`. It is stored, compared against the `username` column, matches nothing, and is never parsed as SQL. Nothing the attacker sends becomes work the engine performs, so there is no controllable delay left to measure.

Run any payload from the walkthrough against the fixed app on port 8107: every one returns `Login attempt processed.` instantly, including the unconditional Step 1 probe that stalled for seconds against the vulnerable version. Escaping or blacklisting characters is a losing game — the only fix is to never splice user input into SQL text.

## A note on the uniform response

It is tempting to read the flat `Login attempt processed.` message as part of the fix. It is not — and that distinction is the whole point of this atom.

Flattening the response was a legitimate **anti-enumeration** measure: with one neutral message, an attacker can't tell "valid user, wrong password" from "no such user." It is good practice, and it did remove the boolean oracle that [`sqli-blind-boolean`](../sqli-blind-boolean/) relied on. But it never touched the injection. That atom's `DIFF.md` said so in as many words — that flattening the two responses is "a workaround, not a mitigation," because "any other observable difference (**response time**, downstream side effect, log line, second-order behavior) would re-introduce the oracle through a different door." This atom *is* that door. The vulnerable app here is precisely "what if a developer applied that tempting workaround but never parameterized the query?" — and the answer is that timing reopens the oracle.

So the uniform message stays in the fixed version, exactly as in the vulnerable one. It was never the bug; the injection was. The parallel to `sqli-blind-boolean` is exact: there, the fix kept the two different messages and the attacker simply lost control of which one appeared; here, the fix keeps the one uniform message and the attacker loses the timing channel. What changes between vulnerable and fixed is never whether an oracle could exist — it is whether an attacker can inject something that drives it.

## The trilogy — one root cause, one fix, three exploits

This is the third atom whose fix is this same two-line change. The diff is structurally identical to the ones in [`sqli-union-basic`](../sqli-union-basic/DIFF.md) and [`sqli-blind-boolean`](../sqli-blind-boolean/DIFF.md): a concatenated SQL string becomes a parameterized statement, and the bug closes.

Across the three, the exploitation technique changed completely with what the attacker could observe — data straight in the body (`UNION`), a one-bit signal in the body (boolean oracle), then pure latency (time). The vulnerability and its correction did not change at all. Parameterized queries close every one of those channels at once, because they remove the single precondition all three depend on: user input becoming SQL syntax. One root cause, one fix, three exploits.
