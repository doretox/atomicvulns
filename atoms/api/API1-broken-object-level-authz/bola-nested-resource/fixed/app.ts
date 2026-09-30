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

// --- Stores: the parent resource ---
// People are OPERATORS of a store -- they work there; they are not the store. Every
// operator of a store legitimately sees all of that store's orders (that is the feature).
const STORES: Record<string, { operators: string[] }> = {
  harbor: { operators: ["dana"] },          // dana (you) operates exactly one store
  meadow: { operators: ["alice"] },
  summit: { operators: ["bob", "carol"] },
};

function operates(user: string, storeId: string): boolean {
  // The parent check: "does this user operate this store?"
  return STORES[storeId]?.operators.includes(user) ?? false;
}

// --- In-memory store (no database) ---
type Order = {
  id: number;
  storeId: string;    // the store this order belongs to -- the data needed to authorize is right here
  customer: string;   // buyer's name on the order -- the PII
  address: string;    // delivery address -- obviously fake
  item: string;
  amount: string;
};

// Order ids are ONE global counter shared by every store (1001..1012), so a store's own
// ids have gaps -- the gaps are other stores' orders. Same twelve orders as the previous
// atoms (ids, items, amounts, addresses), redistributed across three stores: harbor 3,
// meadow 4, summit 5. Buyer names are new: buyers are the public, operators are staff.
const ORDERS: Record<number, Order> = {
  1001: { id: 1001, storeId: "summit", customer: "Priya Shah",  address: "12 Example Ave, Springfield", item: "Mechanical keyboard",     amount: "$89.00"  },
  1002: { id: 1002, storeId: "meadow", customer: "Marcus Webb", address: "7 Sample St, Rivertown",      item: "Noise-cancelling headset", amount: "$199.00" },
  1003: { id: 1003, storeId: "summit", customer: "Priya Shah",  address: "12 Example Ave, Springfield", item: "USB-C hub",                amount: "$42.50"  },
  1004: { id: 1004, storeId: "harbor", customer: "Elena Ruiz",  address: "90 Placeholder Rd, Lakeside", item: "4K monitor",               amount: "$329.00" },
  1005: { id: 1005, storeId: "summit", customer: "Priya Shah",  address: "12 Example Ave, Springfield", item: "Laptop stand",             amount: "$55.00"  },
  1006: { id: 1006, storeId: "meadow", customer: "Marcus Webb", address: "7 Sample St, Rivertown",      item: "Webcam",                   amount: "$75.00"  },
  1007: { id: 1007, storeId: "meadow", customer: "Theo Okafor", address: "3 Testing Blvd, Faketon",     item: "Wireless mouse",           amount: "$29.90"  },
  1008: { id: 1008, storeId: "harbor", customer: "Priya Shah",  address: "12 Example Ave, Springfield", item: "Desk mat",                 amount: "$19.00"  },
  1009: { id: 1009, storeId: "meadow", customer: "Elena Ruiz",  address: "90 Placeholder Rd, Lakeside", item: "Standing desk",            amount: "$589.00" },
  1010: { id: 1010, storeId: "summit", customer: "Priya Shah",  address: "12 Example Ave, Springfield", item: "Monitor arm",              amount: "$120.00" },
  1011: { id: 1011, storeId: "harbor", customer: "Marcus Webb", address: "7 Sample St, Rivertown",      item: "HDMI cable",               amount: "$12.99"  },
  1012: { id: 1012, storeId: "summit", customer: "Priya Shah",  address: "12 Example Ave, Springfield", item: "Ergonomic chair",          amount: "$420.00" },
};

function ordersOf(storeId: string): Order[] {
  return Object.values(ORDERS).filter((o) => o.storeId === storeId);   // the store's scope
}

app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});

app.get("/stores/:storeId/orders", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);
  if (!operates(caller, req.params.storeId)) return res.sendStatus(403);
  res.json(ordersOf(req.params.storeId));   // correctly scoped: only this store's orders
});

app.get("/stores/:storeId/orders/:orderId", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);                        // AUTHENTICATION
  if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
  // FIXED: the order is looked up INSIDE the authorized store, not in the global collection --
  // an order from another store is simply not found, the same 404 as an id that never existed.
  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));
  if (!order) return res.sendStatus(404);
  res.json(order);
});

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";   // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
