# DIFF — vulnerable vs. fixed

Unified diff between `vulnerable/app.py` and `fixed/app.py` for the `/notes/<id>` view:

```diff
 @app.route("/notes/<int:note_id>")
 def view_note(note_id):
+    user_id = request.headers.get("X-User-ID", "1")
     note = next((n for n in NOTES if n["id"] == note_id), None)
     if note is None:
         abort(404)
-    # VULNERABLE: no ownership check — any caller can view any note by id.
+    if str(note["owner_id"]) != user_id:
+        abort(403)
     return render_template("note.html", note=note)
```

The templates and the home-page view are identical in both versions — the bug lives entirely in the missing check inside `view_note`.

## What changed

Two lines of logic were added to the fixed version:

- `user_id = request.headers.get("X-User-ID", "1")` — pulls the caller's claimed identity out of the request, with the same default the home page uses.
- `if str(note["owner_id"]) != user_id: abort(403)` — the explicit ownership check. `note["owner_id"]` is an integer in the seed and `user_id` came from a header as a string, so the comparison casts to a common type. A real codebase would normalize types higher up; the cast is shown inline here so the comparison is visible in one place.

The `# VULNERABLE` comment was deleted because the line it described is gone.

## Why this fixes the bug

Notice what is *not* in the diff. The IDs are still numeric and still incrementing. The URL is still `/notes/1`, `/notes/2`, `/notes/3`. The note table is the same. The header is still self-asserted. None of that is the fix — and none of that needed to change.

The fix is a single conditional. The class of vulnerability is "the server returns a user-scoped object without checking that the caller is the owner". The remediation is exactly its negation: "the server returns a user-scoped object only after checking that the caller is the owner". Anything else — UUIDs, signed tokens, hidden URLs, rate limits — leaves that conditional missing and only changes how hard the bug is to *find*.

## Contrast with `sqli-union-basic` and `xss-reflected`

In the previous two atoms, the bug was a single line of *bad* code: the f-string SQL build, the `|safe` filter. Removing or replacing that line was the fix. Here there is no bad line to remove — the fix is *adding* code that should have been there. That's why grep-style auditing finds injection bugs but misses access-control ones: there's no telltale string to search for. You find IDOR by reading endpoints and asking, for each one that returns user-scoped data, "where does this code verify ownership?" When the answer is "nowhere", the finding is in front of you.
