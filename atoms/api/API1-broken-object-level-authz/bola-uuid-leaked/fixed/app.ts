import express from "express";
import { randomBytes } from "node:crypto";

const app = express();
app.use(express.json());   // Express 5 bundles express.json() but does NOT mount it --
                           // without this line req.body is undefined and POST /login 400s.

// --- Simulated identity: an opaque, server-side token ---
const USERS = new Set(["clancy", "alice", "bob", "carol"]); // clancy = attacker (you)
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

// --- In-memory store (no database) ---
type Order = {
  id: string;         // UUID v4 (was number in bola-sequential-id) -- the ONLY type change
  owner: string;      // login handle of the owner -- what an authorization check compares
  customer: string;   // customer name on the order -- the PII
  address: string;    // delivery address -- obviously fake
  item: string;
  amount: string;
};

// Object ids are fixed UUID v4 strings, hardcoded (never generated at boot) so the
// walkthrough can cite them literally. Unlike bola-sequential-id's 1001..1012 counter,
// nothing about one id reveals another -- the id space is not walkable. Same twelve
// orders, same owners/data as bola-sequential-id; ONLY the id type changed.
const ORDERS: Record<string, Order> = {
  "376d2491-7bc1-44ea-b1f2-81cf7a34af58": { id: "376d2491-7bc1-44ea-b1f2-81cf7a34af58", owner: "alice",  customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Mechanical keyboard",     amount: "$89.00"  }, // was 1001 -- LEAKED to clancy in the walkthrough
  "3ee14e8a-ff76-495f-9e1f-d282ae469916": { id: "3ee14e8a-ff76-495f-9e1f-d282ae469916", owner: "bob",    customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Noise-cancelling headset", amount: "$199.00" }, // was 1002
  "04320e8a-75d1-4c5b-ae31-abfe1ffb212b": { id: "04320e8a-75d1-4c5b-ae31-abfe1ffb212b", owner: "alice",  customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "USB-C hub",                amount: "$42.50"  }, // was 1003
  "bd840141-342e-4d8f-9c62-46e2dace56ef": { id: "bd840141-342e-4d8f-9c62-46e2dace56ef", owner: "carol",  customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "4K monitor",               amount: "$329.00" }, // was 1004
  "faba81a1-83bf-4031-bd4a-c5cb1fe503f9": { id: "faba81a1-83bf-4031-bd4a-c5cb1fe503f9", owner: "alice",  customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Laptop stand",             amount: "$55.00"  }, // was 1005
  "e1df436b-566f-4640-8a07-b07a382bf940": { id: "e1df436b-566f-4640-8a07-b07a382bf940", owner: "bob",    customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Webcam",                   amount: "$75.00"  }, // was 1006
  "edec4558-0cf5-4462-aaba-308229ff6c4f": { id: "edec4558-0cf5-4462-aaba-308229ff6c4f", owner: "clancy", customer: "Omar Haddad",  address: "3 Testing Blvd, Faketon",     item: "Wireless mouse",           amount: "$29.90"  }, // was 1007 -- attacker (you)
  "21f0ebc8-15c8-424e-80e5-3c5aa0cf8b9b": { id: "21f0ebc8-15c8-424e-80e5-3c5aa0cf8b9b", owner: "alice",  customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Desk mat",                 amount: "$19.00"  }, // was 1008
  "bf587c3c-b25f-4533-ba15-21d3b8d21baa": { id: "bf587c3c-b25f-4533-ba15-21d3b8d21baa", owner: "carol",  customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "Standing desk",            amount: "$589.00" }, // was 1009
  "d17f8d55-bf75-45e3-a312-856293086997": { id: "d17f8d55-bf75-45e3-a312-856293086997", owner: "alice",  customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Monitor arm",              amount: "$120.00" }, // was 1010
  "93e1f9e0-277e-4c5b-a1fc-4acff50cb828": { id: "93e1f9e0-277e-4c5b-a1fc-4acff50cb828", owner: "bob",    customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "HDMI cable",               amount: "$12.99"  }, // was 1011
  "0b089ce7-756c-467b-98e0-f5facd72f561": { id: "0b089ce7-756c-467b-98e0-f5facd72f561", owner: "alice",  customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Ergonomic chair",          amount: "$420.00" }, // was 1012
};

app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});

app.get("/orders", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  // Correctly scoped: only the caller's own orders.
  res.json(Object.values(ORDERS).filter((o) => o.owner === caller));
});

app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
  const order = ORDERS[req.params.id];                      // string key (UUID) -- no Number() coercion
  // FIXED: existence and ownership are ONE guard with ONE exit -- a missing order and
  // someone else's order both hit the same sendStatus(404), so "doesn't exist" and
  // "not yours" are byte-identical by construction (a 403 here would be an enumeration oracle).
  if (!order || order.owner !== caller) return res.sendStatus(404);
  res.json(order);
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
