const http = require("http");
// FIXED: no node-serialize dependency at all -- JSON is a data-only format (stdlib).

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
      // First visit: serialize the default prefs (JSON + base64) and set the cookie.
      const raw = Buffer.from(JSON.stringify(DEFAULT_PREFS)).toString("base64");
      return sendJson(res, 200, DEFAULT_PREFS, { "Set-Cookie": `prefs=${raw}; Path=/` });
    }
    // FIXED: the cookie is (de)serialized as JSON, which carries DATA ONLY, never behavior.
    // JSON.parse can at worst produce a weird object; it never builds a function, never
    // evals. Root fix: change the FORMAT (data, not behavior) -- not "sign the cookie"
    // (see DIFF for why signing is only a patch).
    let prefs;
    try {
      prefs = JSON.parse(Buffer.from(cookie, "base64").toString());
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
