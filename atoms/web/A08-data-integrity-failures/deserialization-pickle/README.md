# deserialization-pickle — Insecure deserialization

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

A minimal Flask lab for classic insecure deserialization — remote code execution through Python's `pickle`. The app is a "user preferences" page: it stores your preferences in a `prefs` cookie, serialized with **pickle** (Python's built-in object serializer) and base64-encoded. On every request it base64-decodes the cookie and calls `pickle.loads` on the bytes to rebuild the preferences. But you control your own cookie — and pickle does not store just an object's *data*, it stores *instructions for rebuilding it*, including which function to call. A crafted cookie whose `__reduce__` names `os.system` makes `pickle.loads` run that function while unpickling. The same page that renders your saved theme runs the attacker's command.

This is A08 — Software and Data Integrity Failures: the app trusts a serialized blob that crossed a trust boundary and reconstructs it with a format that carries behavior. It reaches the same ceiling as `command-injection-basic` — remote code execution — but by a different cause: there a shell executes attacker input; here the *deserializer itself* executes behavior embedded in the bytes. The fix is not to validate or sign the cookie — it is to change the **format**: JSON carries data only, never behavior, so `json.loads` has no code path to run. The one and only difference between `vulnerable/` and `fixed/` is `pickle` vs `json`.

> **Theory primer:** Read [PortSwigger: Insecure deserialization](https://portswigger.net/web-security/deserialization)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.

Python's own docs make the point bluntly: the [`pickle` module is "not secure"](https://docs.python.org/3/library/pickle.html) — "only unpickle data you trust."

## Run

From the repo root:

```bash
./atom up deserialization-pickle
```

- Vulnerable app: <http://127.0.0.1:8020/>
- Fixed app: <http://127.0.0.1:8120/>

Stop with `./atom down deserialization-pickle`. If you prefer raw Docker: `cd atoms/A08-data-integrity-failures/deserialization-pickle && docker compose up --build`.

## What to read next

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — step-by-step exploitation via Burp Suite.
2. [`DIFF.md`](./DIFF.md) — commented diff between `vulnerable/` and `fixed/`.

## Fixed version

The patched app on port 8120 serves the same "user preferences" page and reads the same `prefs` cookie — but (de)serializes it as JSON instead of pickle. Replay the exploit from `WALKTHROUGH.md` against it: the same malicious cookie that runs a command on the vulnerable app does nothing here — `json.loads` rejects the pickle bytes, the page still renders `Theme: light`, and no command runs (the `/tmp/pwned` marker is never created). The one and only change from `vulnerable/` is the serialization format; see [`DIFF.md`](./DIFF.md).
