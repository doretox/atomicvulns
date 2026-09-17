# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py` for the `/profile` view:

```diff
 @app.route("/profile")
 def profile():
     username = request.args.get("username", "")
-    # VULNERABLE: user input concatenated into SQL string
-    query = f"SELECT username, bio, joined_at FROM users WHERE username = '{username}'"
     conn = sqlite3.connect(DB_PATH)
-    rows = conn.execute(query).fetchall()
+    rows = conn.execute(
+        "SELECT username, bio, joined_at FROM users WHERE username = ?", (username,)
+    ).fetchall()
     conn.close()
-    return render_template("profile.html", rows=rows, query=query, username=username)
+    return render_template("profile.html", rows=rows, username=username)
```

The `profile.html` template also loses the "Executed query" debug block in the fixed version (the `query` variable is no longer passed to the template).

## What changed

The f-string SQL concatenation was replaced with a parameterized query: the statement keeps a literal `?` placeholder and the `username` value is passed separately as a one-tuple. The vulnerable debug block — which echoed the executed SQL back to the page — was also removed, because it has no reason to exist in the fixed version (and would leak nothing of interest anyway since the SQL no longer contains the input).

## Why this fixes the bug

When the SQLite driver sees a statement with a `?` placeholder, it sends the SQL text and the parameter values to the engine as *separate* arguments. The engine parses the SQL first — without the parameter value — and only then binds `username` as a literal data value in the pre-parsed statement. No matter what characters the input contains (`'`, `--`, `UNION`, `;`, newlines, etc.), they stay inside the string-literal slot and are never reinterpreted as SQL syntax.

The vulnerable version has the opposite model: the input is already part of the SQL text by the time the engine sees it, so the engine *must* parse it as code. Escaping or blacklisting characters is a losing game — the only fix is to never splice user input into SQL text.
