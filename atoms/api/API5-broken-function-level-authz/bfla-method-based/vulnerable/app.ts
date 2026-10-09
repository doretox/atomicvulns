import express from "express";
import { randomBytes } from "node:crypto";

const app = express();
app.use(express.json());   // Express 5 bundles express.json() but does NOT mount it --
                           // without this line req.body is undefined and POST /login 400s.

// --- Simulated identity: an opaque, server-side token; users own their own profile ---
// Each user owns exactly the record keyed by their own handle. displayName is an ordinary,
// editable field -- NOT a privilege flag (that would collide with bfla-admin-function and the
// future bopla- atoms, and blur which axis this atom teaches). Ownership here is handle == caller.
// A Map, not a plain object: PATCH writes THROUGH a path-string lookup, so an object literal
// would expose prototype pollution (__proto__/constructor); Map.get() never walks the chain.
type User = { displayName: string };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park"  }],   // attacker (you) -- owns this record
  ["alice",  { displayName: "Alice Nguyen" }],   // victim -- owns this record; edited in the exploit
]);
const TOKENS = new Map<string, string>();                   // opaque token -> username (in-memory; NOT a JWT)

function issueToken(user: string): string {
  const token = randomBytes(24).toString("base64url");      // crypto-strong opaque value
  TOKENS.set(token, user);
  return token;
}

function authenticate(req: express.Request): string | null {
  // Authentication only: resolve the Bearer token to a username, or null.
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return TOKENS.get(token) ?? null;
}

app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});

app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  res.json({ handle: req.params.handle, displayName: user.displayName });
});

app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
  // VULNERABLE: the GET handler on this same path guards the record with an ownership
  // check; this PATCH handler has none. Authorization belongs to (method + path), not to
  // the path -- guarding the read left the write on the same resource wide open.
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);                               // unknown target user
  user.displayName = req.body?.displayName ?? user.displayName;        // state change -- not a read
  res.json({ handle: req.params.handle, displayName: user.displayName }); // the state delta, echoed input
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
