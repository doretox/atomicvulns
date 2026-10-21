import express from "express";

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

function issueToken(user: string): string {
  return Buffer.from(user).toString("base64url");           // VULNERABLE: the name, encoded -- not entropy
}

function authenticate(req: express.Request): string | null {
  // VULNERABLE: decode the token and trust whoever it spells.
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return Buffer.from(token, "base64url").toString("utf8") || null;
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
