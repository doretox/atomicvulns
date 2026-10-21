import express from "express";
import { randomBytes } from "node:crypto";

const app = express();
app.use(express.json());   // Express 5 bundles express.json() but does NOT mount it --
                           // without this line req.body is undefined and POST /login 400s.

// --- Simulated identity: a token minted at login; users read their own profile ---
// Each user owns exactly the record keyed by their own handle; ownership is handle == caller.
// email is private account data -- the owner may read it; nobody else should reach it.
// There is no is_admin and no passwordHash here: this atom is about WHO the caller is,
// not what role they hold (that is API5) nor which fields serialize (that is API3).
type User = { displayName: string; email: string };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park",  email: "clancy@mail.example" }],    // attacker (you) -- reads his OWN profile for the baseline
  ["alice",  { displayName: "Alice Nguyen", email: "alice@secret.example" }],   // the impersonated victim -- her token is never issued to you
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

// Ownership-guarded profile read. IDENTICAL in both builds -- this guard is NOT the bug.
// It compares the URL's handle against the caller that authenticate() returned. The guard is
// correct; in the vulnerable build the caller it trusts is forgeable, one layer up.
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  res.json({ handle: req.params.handle, displayName: user.displayName, email: user.email });
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
