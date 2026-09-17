import express from "express";
import { randomBytes } from "node:crypto";

const app = express();
app.use(express.json());   // Express 5 bundles express.json() but does NOT mount it --
                           // without this line req.body is undefined and POST /login 400s.

// --- Simulated identity: an opaque, server-side token ---
const USERS = new Set(["dana", "alice", "bob", "carol"]);   // dana = attacker (you)
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
// Order ids are a single GLOBAL, contiguous counter from 1001 to 1012, so adjacent
// orders belong to different owners. dana (you) owns only 1007; the other 11 split
// UNEVENLY between alice (6), bob (3) and carol (2).
type Order = {
  id: number;
  owner: string;      // login handle of the owner -- what an authorization check compares
  customer: string;   // customer name on the order -- the PII
  address: string;    // delivery address -- obviously fake
  item: string;
  amount: string;
};

const ORDERS: Record<number, Order> = {
  1001: { id: 1001, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Mechanical keyboard",     amount: "$89.00"  },
  1002: { id: 1002, owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Noise-cancelling headset", amount: "$199.00" },
  1003: { id: 1003, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "USB-C hub",                amount: "$42.50"  },
  1004: { id: 1004, owner: "carol", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "4K monitor",               amount: "$329.00" },
  1005: { id: 1005, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Laptop stand",             amount: "$55.00"  },
  1006: { id: 1006, owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Webcam",                   amount: "$75.00"  },
  1007: { id: 1007, owner: "dana",  customer: "Dana Lee",     address: "3 Testing Blvd, Faketon",     item: "Wireless mouse",           amount: "$29.90"  },  // attacker (you)
  1008: { id: 1008, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Desk mat",                 amount: "$19.00"  },
  1009: { id: 1009, owner: "carol", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "Standing desk",            amount: "$589.00" },
  1010: { id: 1010, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Monitor arm",              amount: "$120.00" },
  1011: { id: 1011, owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "HDMI cable",               amount: "$12.99"  },
  1012: { id: 1012, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Ergonomic chair",          amount: "$420.00" },
};

app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});

app.get("/orders", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);
  // Correctly scoped: only the caller's own orders.
  res.json(Object.values(ORDERS).filter((o) => o.owner === caller));
});

app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  const order = ORDERS[Number(req.params.id)];
  if (!order) return res.sendStatus(404);
  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
  // order.owner is the caller. Authenticated is not authorized for THIS object.
  res.json(order);                                          // BOLA -- no object-level check
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
