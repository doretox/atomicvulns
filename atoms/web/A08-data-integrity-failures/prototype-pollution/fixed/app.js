const http = require("http");

// --- In-memory settings for the app (no database) ---
// Preferences the user can edit. Nested on purpose so the merge must RECURSE --
// which is exactly where the bug lives.
const settings = { theme: "light", notifications: { email: true } };

function isObject(value) {
  return typeof value === "object" && value !== null;
}

// Recursively merge `source` into `target`, descending into nested objects.
// FIXED: refuse the three keys that reach a shared prototype before descending.
// "__proto__" is the DIRECT door to Object.prototype. "constructor"/"prototype"
// are the INDIRECT door: constructor.prototype is the same shared parent, so
// guarding only "__proto__" is bypassable (see DIFF note). Skipping all three
// keeps the merge writing only real, own data keys of the target object.
function merge(target, source) {
  for (const key of Object.keys(source)) {
    if (key === "__proto__" || key === "constructor" || key === "prototype") {
      continue;
    }
    if (isObject(source[key])) {
      if (!(key in target)) {
        target[key] = {};
      }
      merge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

function readBody(req, callback) {
  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", () => callback(body));
}

function sendJson(res, status, obj) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(obj));
}

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/settings") {
    readBody(req, (body) => {
      let incoming;
      try {
        incoming = JSON.parse(body); // explicit parse: "__proto__" arrives as an OWN key
      } catch (e) {
        return sendJson(res, 400, { error: "invalid JSON" });
      }
      merge(settings, incoming); // SINK: deep-merge untrusted JSON into the settings
      return sendJson(res, 200, settings);
    });
    return;
  }
  if (req.method === "GET" && req.url === "/me") {
    // A brand-new, empty object standing for a default, UNPRIVILEGED session.
    // The attacker never touches this object. But if Object.prototype was polluted,
    // `user.isAdmin` is now INHERITED as true -- proof of GLOBAL contamination.
    const user = {};
    return sendJson(res, 200, { admin: user.isAdmin === true });
  }
  return sendJson(res, 404, { error: "not found" });
});

const HOST = process.env.HOST || "127.0.0.1";
server.listen(5000, HOST);
