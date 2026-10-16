import express from "express";
import { randomBytes } from "node:crypto";

const app = express();
app.use(express.json());   // Express 5 bundles express.json() but does NOT mount it --
                           // without this line req.body is undefined and POST /login 400s.

// --- Simulated identity: an opaque, server-side token; users own their own profile ---
// Each user owns exactly the record keyed by their own handle; ownership is handle == caller.
// displayName is the one field a user may edit. is_admin is an internal role flag: it decides
// who may call GET /admin/users, and a profile update must never accept it from the body.
// NOBODY is seeded as an admin -- the only admin this lab can have is one the bug creates.
// A Map, as in the series' other user stores: Map.get() types the record as User | undefined.
type User = { displayName: string; is_admin: boolean };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park",  is_admin: false }],   // attacker (you) -- updates his OWN record
  ["alice",  { displayName: "Alice Nguyen", is_admin: false }],   // the other account -- exists only to make PATCH /users/alice a 403
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

app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  // VULNERABLE: the ownership check above is right -- this IS your record. But the write
  // merges the WHOLE request body into the record, so every property the body names is set,
  // is_admin included. Authorization applies to each property written, not only to the object.
  USERS.set(req.params.handle, { ...user, ...req.body });
  res.sendStatus(204);                                           // no content: nothing to echo back
});

// Admin-only, read-only, and IDENTICAL in both builds -- this guard is NOT the bug. It reads
// the caller's role from the STORE (the state the PATCH above writes), not from the token (which
// the attack never touches), so it reflects who the caller IS NOW, not who logged in.
app.get("/admin/users", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
  res.json([...USERS.keys()]);   // handles only -- no record fields in the body
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
