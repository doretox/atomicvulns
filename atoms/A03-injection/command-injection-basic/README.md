# command-injection-basic — OS Command Injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic OS command injection. A "network ping tool" concatenates the `host` query parameter into a shell command string (`ping -c 1 <host>`) and runs it through `subprocess.run(shell=True)`, returning the output in the response. Because a shell parses the assembled string, an attacker who appends a shell metacharacter — `host=127.0.0.1; whoami` — gets a second command executed on the server and its output back on the page. The shell is a new sink: where `sqli-union-basic` fed input to a SQL engine, this feeds it to `/bin/sh`, and the impact escalates from data exfiltration to remote code execution on the host.

> **Theory primer:** Read [PortSwigger: OS command injection](https://portswigger.net/web-security/os-command-injection)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

## Run

From the repo root:

```bash
./atom up command-injection-basic
```

- Vulnerable app: <http://127.0.0.1:8009/>
- Fixed app: <http://127.0.0.1:8109/>

Stop with `./atom down command-injection-basic`. If you prefer raw Docker: `cd atoms/A03-injection/command-injection-basic && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite (primary).
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8109 serves the same ping tool. It swaps the shell string for an argument list — `subprocess.run(["ping", "-c", "1", host])` — so `host` is always a single, inert argument and never reaches a shell to be parsed. Run every payload from `WALKTHROUGH.md` against it: each one comes back as `ping: <host>: Name or service not known`, with no injected command executed and nothing leaked.
