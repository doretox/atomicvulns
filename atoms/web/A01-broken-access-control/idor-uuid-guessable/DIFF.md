# DIFF — vulnerable vs. fixed

`vulnerable/app.py` and `fixed/app.py` differ; the templates, `Dockerfile`, and `requirements.txt` are identical between the two versions. The change has two parts, and they are not equal — one is *the* fix, the other is defense-in-depth.

## The fix that matters — an ownership check

The security-relevant change is one conditional in the `/receipt/<uuid>` view:

```diff
 @app.route("/receipt/<uuid:receipt_id>")
 def view_receipt(receipt_id):
+    caller = request.headers.get("X-User-ID", ATTACKER)
     r = RECEIPTS.get(str(receipt_id))
     if r is None:
         abort(404)
-    # VULNERABLE: no ownership check -- any caller who holds (or reconstructs)
-    # the id reads the receipt. The unguessable-looking UUID is treated as the
-    # access control; it is not one.
+    # FIXED (the fix that matters): serve the receipt only to its owner.
+    if r["owner"] != caller:
+        abort(403)
     return render_template("receipt.html", receipt=r)
```

The fixed view reads the caller's claimed identity (`X-User-ID`, the same self-asserted header the rest of the app uses) and compares it to `r["owner"]` before returning the receipt. Mismatch → `403 Forbidden`. That single conditional closes the IDOR: the class is "the server returns a user-scoped object without checking the caller owns it," and the remediation is exactly its negation.

## Defense-in-depth — a non-reconstructible id

The second change swaps the id generator, and drops the machinery the old one needed:

```diff
-def _new_receipt_id():
-    return uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)
+def _new_receipt_id():
+    return uuid.uuid4()
```

`uuid1` embedded a timestamp and the host `node` and, with a stable `clock_seq`, was reconstructible from the `issued_at` the dashboard leaks (see [`WALKTHROUGH.md`](./WALKTHROUGH.md), Steps 2–4). `uuid4` is drawn from a CSPRNG and embeds neither, so the reconstruction has nothing to work from. With the old generator gone, the `_NODE`/`_CLOCK_SEQ` constants and the `_issued_at_from` helper go with it (the fixed `_add_receipt` stamps `issued_at = datetime.now(timezone.utc)` instead of deriving it from the id).

## Why the check alone is enough — and the generator swap alone is not

This is the heart of the two-layer lesson, and the DIFF has to be honest about it:

- **The ownership check fixes the bug by itself.** You could keep `uuid1` *and* keep the dashboard leaking `issued_at`, and the attack would still fail — the reconstructed id now returns `403`, because the server finally checks who is asking. Obscurity was never the control; the check is.
- **The generator swap does not fix the bug by itself.** Keep the missing check and only switch to `uuid4`, and anyone who *obtains* a valid id — a shared link, a `Referer` header, a log line, browser history — still reads the receipt. Step 5 of the walkthrough proves the endpoint never even looks at identity. `uuid4` closes the *reconstruction* route (Layer 2); it does nothing about *access* (Layer 1).

So the fix ships both, in priority order: the check is the correction; `uuid4` is defense-in-depth that removes an unnecessary source of predictability. Reach for the check first.

## Reshaping the id is a losing game on its own

`idor-numeric-id`, the direct sibling, already said this about its own fix: changing the integer to a UUID would be *"obfuscation... theater,"* and "UUIDs, signed tokens, hidden URLs, rate limits ... only change how hard the bug is to *find*." This atom is that claim made concrete — the id *is* a UUID and the bug is untouched — with a twist: the UUIDv1 wasn't even hard to find, because it carried its own timestamp and node. The transferable rule, the same one `sqli-union-basic` teaches about escaping and `path-traversal-basic` about blocklisting `../`: **fix the missing check, don't reshape the identifier.** Hiding or randomizing the id only changes the cost of finding it; it never adds the authorization that isn't there.

## 403, not 404 — and why that differs from path-traversal-basic

The fixed view returns **403 Forbidden**: the receipt is a real object of the app that this caller isn't authorized to see, so "forbidden" is the honest status — the same choice `idor-numeric-id` makes. Contrast `path-traversal-basic`, which returns **404** for a rejected traversal: there the "resource" is a path *outside* the app's domain, and 404 refuses to confirm whether anything exists there. The rule of thumb: return 403 when the object is yours-to-know-exists-but-not-to-read; return 404 when admitting existence would itself leak. A 403 here does confirm the receipt exists; if that mattered, 404 would be the defense-in-depth choice — but we keep 403 for consistency with the sibling IDOR, because here the existence isn't the sensitive part, the contents are.

## The dashboard leak is the environment, not a second bug

The `GET /` dashboard exposes every receipt's `owner` and microsecond `issued_at`, and it is **identical in the fixed version** — deliberately. Over-precise timestamps in a listing are the realistic soil the reconstruction grows in (default datetime serialization leaks microseconds all the time), but they are not the vulnerability under study, and the atom keeps exactly one bug. Leaving the leak in place in the fixed app proves the point: with the ownership check present (and `uuid4` on top), the same `issued_at` is inert. Coarsening it to seconds would be reasonable extra hardening, but it is not the fix and isn't applied here.

(One more line of hygiene, in both versions: the templates autoescape everything, including the attacker-controlled `X-User-ID` echoed on the dashboard. That escaping is not the IDOR fix either — it just keeps an unescaped header from stacking a reflected XSS on top, so the atom stays at exactly one bug.)

## This is IDOR — the same bug as idor-numeric-id, and it lives in app.py

Nothing the attacker sends is parsed or executed; a legitimate id simply reaches an object outside the caller's scope. That is Broken Access Control (A01), the same shape as `idor-numeric-id` — there you change a number, here you reconstruct a UUID, and both fixes are the ownership check that was missing. Like both A01 siblings, the bug lives in `app.py`, not the templates, and it doesn't `grep`: there's no `f"`, `|safe`, or `eval` to search for. You find it by reading each endpoint that returns a user-scoped object and asking "where does this check the caller owns it?" — and noticing, here, that a UUID in the URL was quietly mistaken for that check.
