import express from "express";
import { randomBytes } from "node:crypto";

const app = express();
app.use(express.json());   // Express 5 bundles express.json() but does NOT mount it --
                           // without this line req.body is undefined and POST /login 400s.

// --- Simulated identity: an opaque, server-side token; users own their own profile ---
// Each user owns exactly the record keyed by their own handle; ownership is handle == caller.
// Next to the one public field (displayName) the record carries two server-side fields:
// passwordHash -- a dummy, bcrypt-shaped string the passwordless login never reads -- and
// is_admin, an internal role flag. Neither is meant to leave the server.
// A Map, as in the series' other user stores: Map.get() types the record as User | undefined.
type User = { displayName: string; passwordHash: string; is_admin: boolean };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park",  passwordHash: "$2b$12$DUMMYsaltFORlabUSEonlyDUMMYhashNOTaREALpasswordCLANCY", is_admin: false }],  // attacker (you) -- reads his own record
  ["alice",  { displayName: "Alice Nguyen", passwordHash: "$2b$12$DUMMYsaltFORlabUSEonlyDUMMYhashNOTaREALpassword.ALICE", is_admin: false }],  // the other account -- exists only to make GET /users/alice a 403
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
  // FIXED: the response names the fields the caller may see -- an allow-list, not the stored
  // object. A field added to User later stays server-side until someone deliberately exposes it.
  res.json({ handle: req.params.handle, displayName: user.displayName });
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
