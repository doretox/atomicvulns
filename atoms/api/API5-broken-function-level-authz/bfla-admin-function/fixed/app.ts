import express from "express";
import { randomBytes } from "node:crypto";

const app = express();
app.use(express.json());   // Express 5 bundles express.json() but does NOT mount it --
                           // without this line req.body is undefined and POST /login 400s.

// --- Simulated identity: an opaque, server-side token; users carry a role ---
// is_admin is the capability axis this atom is about. Promoting a user to admin is an
// admin-only function. clancy (you) is a plain member; carol is the one seeded admin,
// so the fixed build has a legitimate caller to show the function still works.
// A Map, not a plain object: Map.get() never walks the prototype chain, so a :handle of
// "__proto__" or "constructor" is just an unknown user -- never Object.prototype.
type User = { is_admin: boolean };
const USERS = new Map<string, User>([
  ["clancy", { is_admin: false }],   // attacker (you) -- a plain member
  ["alice",  { is_admin: false }],   // primary victim -- promoted in the exploit
  ["bob",    { is_admin: false }],   // target of carol's legitimate promotion in the fixed build
  ["carol",  { is_admin: true  }],   // the one legitimate administrator
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

app.post("/admin/users/:handle/promote", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
  // FIXED: function-level authorization. Promoting is an admin-only capability, so the
  // caller's ROLE is checked right after authentication -- a non-admin is refused 403
  // BEFORE the target is ever looked up, so the gate leaks nothing about who exists.
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
  const target = USERS.get(req.params.handle);
  if (!target) return res.sendStatus(404);                  // unknown target user
  target.is_admin = true;                                   // state change -- not a read
  res.json({ handle: req.params.handle, is_admin: true });  // the state delta, not third-party data
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
