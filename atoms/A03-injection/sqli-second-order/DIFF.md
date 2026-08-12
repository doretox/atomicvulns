# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` are byte-identical except the `UPDATE` in the `POST /change-password` view — the atom's single change:

```diff
     conn = db()
     # The logged-in user's username is READ BACK from the DB (parameterized read).
     uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
-    # VULNERABLE: the username re-read from the DB is concatenated straight into the
-    # UPDATE. It was STORED safely (parameterized) at registration, so it was never
-    # treated as untrusted here -- but a value read back from the DB is untrusted
-    # input again. Note `new_password` (fresh input) IS parameterized; only the
-    # re-read value is spliced in -- so a payload username rewrites WHICH row this hits.
-    query = f"UPDATE users SET password = ? WHERE username = '{uname}'"
-    conn.execute(query, (new_password,))
+    # FIXED: the username re-read from the DB is bound as a parameter, exactly like
+    # every other query in this app. A value read back from the DB is untrusted input
+    # again -- so it goes through a placeholder, never into SQL text. The payload is
+    # matched as a literal value; the UPDATE hits only the caller's own row.
+    conn.execute(
+        "UPDATE users SET password = ? WHERE username = ?", (new_password, uname)
+    )
```

## What changed

The re-read username stops being concatenated into the SQL text and becomes a bound parameter. Look at the two values in that one `UPDATE`: `new_password` — fresh input from this request — was **already** a `?` placeholder on both sides. Only `uname` — the value read back from the database — moves, from an f-string splice (`WHERE username = '{uname}'`) to a placeholder (`WHERE username = ?`). Everything else in the app is identical between the two versions: registration, login, the read-back `SELECT`, the schema and seed, the session — all of it was, and remains, parameterized.

## Why this fixes the bug

With a placeholder, the SQLite driver parses the `UPDATE` **first**, without the value, and only then binds `uname` as a literal data value in the pre-parsed statement. The metacharacters in `admin'--` — the `'` and the `--` — stay inside the string-literal slot; they can no longer close the quote and comment out the rest. The `WHERE` matches the row whose username is *exactly* the string `admin'--` (the attacker's own row), so change-password does what it should: it changes the caller's own password and nobody else's. In the vulnerable version the value was already inside the SQL text by the time the engine saw it, so the engine had to parse `'--` as syntax and the `WHERE` collapsed to `username = 'admin'`.

## The cause is the second query, not the registration

The bug is **not** that registration was insecure — it is not. The `INSERT` is parameterized, and a payload username is stored as inert text; attacking `/register` directly does nothing. The cause is that the **second** query concatenates a value read back from the database. Parameterizing that query neutralizes it because the re-read value becomes literal data, never syntax — so the `WHERE` matches exactly the intended row and there is nothing to restructure. The mental model to keep: **every read from the database is untrusted input again**. A value does not become safe by having passed through your own tables; it entered as attacker input and it re-enters the trust boundary every time you read it.

## "I already parameterized registration" / "just sanitize the username" is not the fix

Two reflexes lead the wrong way, and both are worth naming:

- *"I parameterized the registration, so I'm safe."* Parameterizing the **entry** protects the entry query. It does nothing for a **later** query that concatenates the value at its point of use — the protection does not travel with the data.
- *"Just sanitize/validate the username at registration — forbid quotes and `--`."* That is a blocklist in the wrong place. It chases the *shape* of the payload (alternate encodings, characters you didn't list, other code paths that write to the table), and it leaves the concatenating query untouched. It is also brittle against usernames that legitimately contain symbols.

The fix is to treat the re-read value as untrusted **at the point of use** and bind it as a parameter. Then it does not matter what characters it contains, because none of them is ever parsed as SQL.

## Same class as first-order SQL injection — what changes is the timing

This is the same vulnerability class, engine, and fix as first-order SQL injection ([`sqli-union-basic`](../sqli-union-basic/)): untrusted input concatenated into a query, run by the same SQLite parser, fixed by a parameterized query. What differs is **when** the input reaches the parser — and that is the whole reason this is a separate atom.

| | First-order SQL injection (`sqli-union-basic`) | Second-order SQL injection (this atom) |
|---|---|---|
| Order | First (in-band) | Second (stored) |
| Where the payload enters | Concatenated into the query of its own request | Stored through a **parameterized** path (registration), as a literal value |
| When it fires | The same request | A **later, different** request — the second flow re-reads the value and concatenates it |
| Why it slips by | It doesn't — the payload acts in the flow you are testing | The entry point tests as safe (registration is parameterized; a naive probe there does nothing) — the bomb sleeps in the database |
| Engine | SQLite's SQL parser | The **same** SQLite SQL parser |
| The fix | Parameterize the query | Parameterize the query **of the second use too** |

The lesson of `sqli-union-basic` — *never concatenate untrusted input into a query* — was right but incomplete. It has to include *and every value read back from the database is untrusted input again*. Here, one query in a second flow forgot that, even though every other query in the same app parameterizes correctly.
