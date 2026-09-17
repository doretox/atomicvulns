const http = require("http");
const serialize = require("node-serialize");

// --- In-memory default preferences (no database) ---
const DEFAULT_PREFS = { theme: "light" };

// Read one cookie by name from the request header (hand-written, no framework).
function getCookie(req, name) {
  const header = req.headers.cookie || "";
  for (const part of header.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    if (part.slice(0, eq).trim() === name) return part.slice(eq + 1).trim();
  }
  return undefined;
}

function sendJson(res, status, obj, extraHeaders) {
  res.writeHead(status, { "Content-Type": "application/json", ...(extraHeaders || {}) });
  res.end(JSON.stringify(obj));
}

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/") {
    const cookie = getCookie(req, "prefs");
    if (!cookie) {
      // First visit: serialize the default prefs (node-serialize + base64) and set the cookie.
      const raw = Buffer.from(serialize.serialize(DEFAULT_PREFS)).toString("base64");
      return sendJson(res, 200, DEFAULT_PREFS, { "Set-Cookie": `prefs=${raw}; Path=/` });
    }
    // VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to
    // serialize.unserialize. node-serialize encodes a JS function as a string tagged
    // "_$$ND_FUNC$$_" and eval()s that source on unserialize; a function body ending in
    // "()" self-invokes right there -- a crafted cookie -> code execution on the server.
    let prefs;
    try {
      prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString());
    } catch (e) {
      prefs = DEFAULT_PREFS;
    }
    const theme = prefs && typeof prefs.theme === "string" ? prefs.theme : DEFAULT_PREFS.theme;
    return sendJson(res, 200, { theme });
  }
  return sendJson(res, 404, { error: "not found" });
});

const HOST = process.env.HOST || "127.0.0.1";
server.listen(5000, HOST);
