# DIFF — vulnerable vs. fixed

`vulnerable/app.js` and `fixed/app.js` differ in exactly one place — the `merge` function guards the keys that reach a prototype before descending (its doc-comment changes too, and the now-wrong inline note on the recurse line is dropped; comments abbreviated):

```diff
 function merge(target, source) {
   for (const key of Object.keys(source)) {
+    // FIXED: refuse the three keys that reach a shared prototype before descending.
+    if (key === "__proto__" || key === "constructor" || key === "prototype") {
+      continue;
+    }
     if (isObject(source[key])) {
       if (!(key in target)) {
         target[key] = {};
       }
       merge(target[key], source[key]);
     } else {
       target[key] = source[key];
     }
   }
   return target;
 }
```

Everything else is byte-for-byte identical between the two versions: the seeded `settings`, `isObject`, `readBody`, `sendJson`, the `POST /settings` and `GET /me` handlers, the `http` server and `listen`, the `Dockerfile`, and `package.json` (there are no templates — this atom is API-only). The bug — and the fix — live entirely in which keys the merge descends through.

## What changed

The vulnerable `merge` descends into `target[key]` for every key whose value is an object, no exceptions. When the key is `__proto__`, `target[key]` is not a field — it is the object's prototype, `Object.prototype` — so the recursion writes onto the parent shared by every object in the process. The fixed `merge` adds a guard at the top of the loop: `if (key === "__proto__" || key === "constructor" || key === "prototype") continue;`. Those three keys are skipped, so the loop only ever descends into and writes real, own data keys of the target. That is a *surgical* fix — three lines that map straight onto the cause: the flaw is the merge descending through keys that reach the prototype, and the guard refuses exactly those keys.

## Why this fixes the bug — and why it is NOT "validate the input"

The cause is **which keys the merge walks**, not the content of the input. `{"__proto__":{"isAdmin":true}}` is perfectly well-formed JSON with a legitimate value — there is no malformed syntax to reject, no strange character to escape. Nothing about the *data* is wrong; what is wrong is that the merge treats `__proto__` as a key it can descend through. So the fix is not "sanitize the body" or "validate the input" — it is the merge **refusing** the keys that reach a shared prototype.

Proof of isolation: send the benign `{"theme":"dark"}` merge to both apps and both return `{"theme":"dark","notifications":{"email":true}}` and keep `GET /me` at `{"admin":false}`. The feature is identical. Only the `__proto__` payload diverges — the vulnerable app pollutes `Object.prototype` (so the untouched object at `GET /me` inherits `isAdmin`), the fixed app skips the key and leaves the prototype alone. Deep-merging a JSON body was never the bug; descending through a key that reaches the prototype was.

## Why three keys, not just `__proto__`

The tempting quick fix is to guard the one obvious key — "just skip `__proto__`." That loses, because `__proto__` is not the only door to the shared parent. `constructor.prototype` reaches the same place: for a plain object, `settings.constructor` is the `Object` function, and `Object.prototype` **is** the very object being poisoned. So the payload

```json
{"constructor":{"prototype":{"isAdmin":true}}}
```

pollutes `Object.prototype` just as effectively as the `__proto__` payload — the merge descends `settings.constructor` → `.prototype` → and writes `isAdmin` there — **without ever using the `__proto__` key**. A guard that blocks only `__proto__` leaves this back door wide open. That is why the durable guard names all **three** keys: `__proto__` (the direct door) plus `constructor` and `prototype` (the indirect door through `constructor.prototype`). This `constructor.prototype` bypass is described here as the reason for the three-key guard; the walkthrough demonstrates only the `__proto__` payload.

## Naming the key is a patch; the structural defense is different

The three-key guard is a *blocklist of keys* — it works, and it is the minimal change that isolates the fix in this diff, but it is still "chase the forbidden thing." The defense that removes the possibility at the root is **structural** — it changes *what kind of object* holds untrusted data, so there is nothing to pollute or nothing that trusts the polluted parent:

- **`Object.create(null)`** creates an object with **no prototype** — no parent, no `Object.prototype` in its chain. There is nothing to pollute through it, and reading `obj.__proto__` on it is just an ordinary (absent) property, not a door to a shared parent.
- **`Map`** is JavaScript's real dictionary (true key→value storage), where `__proto__` is just an inoffensive string key like any other, not a magic accessor. Holding user-controlled data in a `Map` instead of a plain object closes the vector.
- **`Object.hasOwn(obj, key)`** (or `Object.prototype.hasOwnProperty.call`) checks only an object's *own* property when reading, ignoring anything inherited from the prototype. An `if (Object.hasOwn(user, "isAdmin"))` is not fooled by a poisoned prototype.

These are the real target in production. This atom applies the key guard so the diff stays a surgical one — the same structure on both sides, the guard the only delta — and names the structural defenses here without applying them. (Note that "sign the blob" — the HMAC-style patch that `deserialization-pickle` warns against — does *not* apply here: there is no serialized blob being trusted. The parallel to that atom is at the level of *structure*, not authentication: both fix the cause by removing an unsafe primitive rather than guarding it.)

## Impact: global contamination, and how it differs from `deserialization-pickle`

The impact is **global contamination of `Object.prototype`** → subversion of any code that reads an inherited property assuming it is absent. This lab's example is an authorization bypass: `GET /me` builds a fresh, unprivileged object and it reports admin. The pollution persists in the process until a restart and affects objects created after the attack.

Both this atom and `deserialization-pickle` are **A08 — Software and Data Integrity Failures**: untrusted data corrupts something the app then trusts. But the **impact differs**, which is why they are two atoms and not one:

- **`deserialization-pickle`** — the deserializer *executes* behavior embedded in the bytes; the ceiling is **remote code execution**.
- **prototype pollution** — nothing executes by default; the attacker *corrupts a shared object* and *other* code trusts it, subverting logic/authorization. The ceiling here is **not RCE** — escalating prototype pollution to code execution needs specific *gadgets* in surrounding libraries or the runtime, which is out of scope for this atom.

Same category, same "untrusted data breaks integrity" root, different mechanism and different ceiling. "One atom = one vulnerability" is about the *cause*: poisoning a shared prototype through a merge has nothing to do with reconstructing a behavior-carrying format. This atom proves the authorization bypass; the RCE escalation is the class's reach in the wild, described not built.
