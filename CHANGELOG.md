# Changelog

All notable changes to atomicvulns will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-09-11

Full OWASP Top 10 2021 Coverage (Phase 7 of the ROADMAP, and the 1.0 milestone). Eight atoms closing the remaining Top 10 categories — pure cryptographic failures, insecure design, the rest of security misconfiguration, vulnerable components, the rest of authentication failures, and logging and monitoring — and with them the repository now covers all ten 2021 categories, A01 through A10. This phase adds: weak password hashing broken with a rainbow table and ECB block cut-and-paste (A02); a TOCTOU withdrawal race won with a single-packet attack (A04); Flask debug mode reachable for RCE and CORS origin reflection leaking authenticated data (A05); a real dependency CVE whose entire fix is a version bump, not a code change (A06); a clock-seeded reset token predicted for account takeover (A07); and the atypical closer where the flaw is the absence of a security log and the proof is the contrast between two logs, not something appearing (A09). Recurring lessons here — a security fix is not always in your code (it can be a dependency version), and detection is a distinct discipline from prevention. Each atom isolates one flaw with vulnerable/ and fixed/ side by side, Burp-first walkthroughs, and bilingual docs (EN + PT-BR).

### Added

- Added atom 31: `crypto-weak-hash` — Insecure password storage (weak hashing): a login app stores the admin's password as an unsalted MD5 digest, so a hash leaked in a database dump is recovered offline with a pre-computed rainbow table (rtgen/rtsort/rcrack) and replayed to log in as the victim; the fix swaps the primitive for bcrypt — slow and salted, a primitive against which no rainbow table can even be built (A02 Cryptographic Failures, CWE-916).
- Added atom 32: `crypto-ecb-mode` — Encryption with an insecure mode of operation: a login app issues a session badge carrying `role=user` encrypted with AES-ECB, a deterministic mode that encrypts each 16-byte block independently, so identical plaintext blocks leak as identical ciphertext blocks and whole blocks can be cut and pasted between badges — the attacker aligns `admin` into its own block via a chosen email, lifts that ciphertext block from the login response, splices it over the `user` block, and GET /me treats the forged badge as admin without ever touching the key; the fix swaps the mode for authenticated AES-GCM, whose per-message nonce removes the determinism and whose authentication tag makes the tampered badge fail verification and be rejected before the role is read (A02 Cryptographic Failures, CWE-327, CWE-353).
- Added atom 33: `debug-enabled` — Debug mode enabled in a reachable environment: a Flask app runs with `app.run(debug=True)` and the Werkzeug debugger PIN disabled, so any unhandled exception — a malformed value crashing an ordinary route — renders Werkzeug's interactive debug page, which leaks source, local variables and file paths (information disclosure) and embeds a console that runs arbitrary Python in the server process; the attacker triggers the exception, lifts the per-process console secret from the debug page HTML, and sends one HTTP request that executes a command on the server (RCE — `id` returns `uid=0(root)`), all from Burp Repeater; the fix is `debug=False` — and, in production, serving behind a real WSGI server instead of the development server — which turns the same exception into a generic 500 with no traceback and no console (A05 Security Misconfiguration, CWE-489, CWE-215).
- Added atom 34: `cors-wildcard` — Cross-origin resource sharing (CORS) misconfiguration: an authenticated JSON API returns the logged-in user's private account data, but its CORS policy reflects the request's `Origin` back in `Access-Control-Allow-Origin` together with `Access-Control-Allow-Credentials: true`, so any origin may read the response with the victim's cookies — a victim who visits the attacker's page has the browser make a credentialed cross-origin `fetch` to `/account` and hand the private data to the attacker's script (cross-origin exfiltration, proven in a real browser because CORS is a browser control that `curl`/Burp ignore); the literal `*` wildcard is a red herring — the browser refuses `*` together with credentials, so it leaks only public data, and the authenticated vector is origin reflection — and the fix replaces reflection with an exact-match allowlist of trusted origins (the read side of the Same-Origin Policy, the mirror of the send side in `csrf-basic`) (A05 Security Misconfiguration, CWE-942, CWE-346).
- Added atom 35: `race-condition-basic` — Time-of-check to time-of-use (TOCTOU) race condition: an account API's `POST /withdraw` reads the balance, checks `balance >= amount` in Python, then writes the debit as three separate steps, so twenty identical, byte-for-byte legitimate withdrawals fired simultaneously with Burp's Turbo Intruder (single-packet attack) all read the full balance and pass the check before any of them writes — all debit, driving the balance to `-1900` from a starting `100` (a violated business invariant, with no malicious input; only the concurrency differs); the fix makes the check-and-act atomic in one conditional `UPDATE` the database serializes per row (`UPDATE ... SET balance = balance - :amount WHERE id = 1 AND balance >= :amount`, checking `rowcount`), letting exactly one withdrawal through — not "check again" (same window) and not just an application lock (single-process only); multi-container Flask + PostgreSQL (A04 Insecure Design, CWE-362).
- Added atom 36: `cve-demo` — Using a component with a known vulnerability: a Flask config API loads a YAML request body with `yaml.full_load` — the loader PyYAML itself documented as the safe way to load a full document — but pins `PyYAML 5.3.1`, a version carrying the public CVE-2020-14343, whose `full_load` can still be tricked through the `python/object/new` tag into rebuilding arbitrary Python objects, so a crafted YAML document taken straight from the public advisory runs a command on the server (remote code execution — `touch /tmp/pwned` created as root, proven with `docker compose exec`); uniquely in the repo the `app.py` is byte-identical between `vulnerable/` and `fixed/` — the whole flaw and the whole fix are one line in `requirements.txt`, bumping PyYAML to 5.4.1, where the library moved the dangerous constructors out of the loader so the same code and the same payload are refused with a `ConstructorError` and no marker is created; the diff is the dependency version, not the code — and not `yaml.safe_load`, which is the orthogonal code-level lesson of `deserialization-pickle` (A06 Vulnerable and Outdated Components, CWE-1104, CWE-502).
- Added atom 37: `weak-password-reset` — Predictable password-reset token: a forgot-password flow issues a reset token — a temporary credential whose holder may set a new password — but generates it with Python's `random` module seeded from the clock (`random.seed(int(time.time()))`), a PRNG (the Mersenne Twister) that is deterministic from its seed, so an attacker requests the victim's reset, reads the server time from the response's `Date` header, reproduces the seed and runs the same sequence to regenerate the exact token, then resets the victim's password and logs in as her (account takeover); no crypto is broken and nothing is injected — the secret is simply predictable — and the fix swaps the generator for a CSPRNG (`secrets.token_urlsafe`, the same generator `session-fixation` uses for its session ids), single-use and short-lived, so the predicted token no longer matches and `POST /reset` refuses it as unknown before single-use or expiry ever apply; the two sides' `requirements.txt` stay identical, the whole diff being one standard-library module (`random` → `secrets`) (A07 Identification and Authentication Failures, CWE-640, CWE-330).
- Added atom 38: `logging-failures-demo` — Missing security logging of authentication failures: a minimal login API rejects wrong passwords correctly (`200`/`401`), but the vulnerable side records nothing security-relevant on the failure path, so a brute-force burst leaves only Werkzeug's generic HTTP access log — which carries no target account (the email is in the body), no event classification and no aggregation — and the attack is invisible as an attack; the fixed side adds a dedicated structured security logger that writes one line per failure (event, target account, source IP, timestamp — never the attempted password) and a `WARNING` naming a possible brute-force once five consecutive failures against one account accumulate, without blocking the login (detection, not prevention — every attempt still returns `401`); uniquely in the repo the proof is not something appearing but the contrast between `docker compose logs vulnerable` (blind) and `docker compose logs fixed` (the security trail plus the alert) under the same burst, and the whole diff is the logging in `app.py` — the login is byte-identical and `requirements.txt` unchanged, since `logging` is standard library (A09 Security Logging and Monitoring Failures, CWE-778, CWE-223).

## [0.6.0] - 2026-08-14

Rare but Deadly (Phase 6 of the ROADMAP). Five atoms covering what shows up rarely and does enormous damage when it does, and the phase that brings Node.js into the repo: prototype pollution writing onto the shared `Object.prototype` through a deep merge, insecure deserialization in Node as the JavaScript face of the pickle atom, LDAP injection rewriting a search filter through an unescaped metacharacter, second-order SQL injection planted in one flow and detonated in another, and blind XXE confirmed out-of-band. Two lessons recur here — injection sinks live in query languages well beyond SQL, and a payload's effect need not land in the request that carried it. Each atom isolates one flaw with vulnerable/ and fixed/ side by side, Burp-first walkthroughs, and bilingual docs (EN + PT-BR).

### Added

- Added atom 26: `prototype-pollution` — Prototype pollution: a hand-written deep-merge of untrusted JSON descends through the `__proto__` key and writes onto the shared `Object.prototype`, so `{"__proto__":{"isAdmin":true}}` poisons every object in the process — a brand-new, untouched object at `GET /me` inherits `isAdmin` and is treated as admin; the fix guards the merge against the `__proto__`, `constructor`, and `prototype` keys (A08 Software and Data Integrity Failures, CWE-1321).
- Added atom 27: `deserialization-node` — Insecure deserialization: an attacker-controlled cookie deserialized with Node's `node-serialize` library carries a `_$$ND_FUNC$$_`-tagged function that the library `eval`s on unserialize; a self-invoking function body runs during unserialize, giving remote code execution — the Node face of the flaw `deserialization-pickle` shows in Python; the fix changes the format to JSON (`JSON.parse`, data only) and drops the dependency (A08 Software and Data Integrity Failures).
- Added atom 28: `ldap-injection` — LDAP injection: a corporate login concatenates untrusted input straight into an LDAP search filter (`(&(uid=...)(userPassword=...))`), so an unescaped metacharacter rewrites it — sending `*` as the password turns the password check into the presence test `(userPassword=*)`, matching `admin` and logging in without the password; the fix escapes the RFC 4515 metacharacters (`escape_filter_chars`) in every untrusted value before the filter is built (A03 Injection).
- Added atom 29: `sqli-second-order` — Second-order SQL injection: a username stored through a safe parameterized `INSERT` at registration is later re-read from the database and concatenated raw into a second query (the change-password `UPDATE`), so a payload username (`admin'--`) planted at registration lies dormant and detonates in the second flow — rewriting the `UPDATE`'s `WHERE` to change another account's password (account takeover) while the entry point itself tests as safe; the fix parameterizes the second query too, because every value read back from the database is untrusted input again (A03 Injection).
- Added atom 30: `xxe-blind-oob` — Blind XXE (out-of-band): a bulk-import endpoint parses untrusted XML with an lxml parser that resolves external entities and is allowed to reach the network, but never echoes anything back — so the XXE is confirmed out-of-band: a declared external parameter entity makes the parser fetch an attacker-hosted DTD (the callback lands on an embedded listener), and that DTD rides the same channel to exfiltrate an app-server file in a second request; same parser-misconfiguration cause and fix as `xxe-basic`, differing only in the confirmation channel (in-band → out-of-band); the fix disables external-entity resolution and DTD loading, both flags load-bearing (A05 Security Misconfiguration).

## [0.5.0] - 2026-07-29

Client-side & NoSQL (Phase 5 of the ROADMAP). Five atoms covering the client side and data stores beyond SQL: DOM-based XSS through a client-side sink, NoSQL injection via an operator smuggled into a MongoDB filter, CSRF forging a state-changing request on an auto-attached cookie, an open redirect to a user-controlled destination, and mass assignment escalating a user to admin. Two recurring A01 lessons close here — the server decides, not the input, and allowlist over blocklist. Each atom isolates one flaw with vulnerable/ and fixed/ side by side, Burp-first walkthroughs, and bilingual docs (EN + PT-BR).

### Added

- Added atom 21: `xss-dom` — DOM-based Cross-Site Scripting: client-side JavaScript reads an attacker-controlled URL fragment (`location.hash`) and writes it to `innerHTML`, so a crafted fragment executes in the victim's browser without ever reaching the server (A03 Injection).
- Added atom 22: `nosql-injection-mongo` — NoSQL Injection: a login endpoint passes untrusted JSON straight into a MongoDB query filter, so an object carrying an operator (`{"$ne": null}`) instead of a string logs in as admin without the password (A03 Injection).
- Added atom 23: `csrf-basic` — Cross-Site Request Forgery (CSRF): a state-changing POST authorizes on the session cookie the browser attaches automatically, so an auto-submitting form on another site forges an authenticated email change (account takeover); the fix is a per-session anti-CSRF token the attacker cannot read across origins (A01 Broken Access Control).
- Added atom 24: `open-redirect` — Open Redirect: after login the app redirects to a user-controlled `next` parameter with no validation, so `next=http://evil.example` (or the protocol-relative `//evil.example`) sends the victim off-site; the fix is a server-side structural allowlist that permits only internal paths (A01 Broken Access Control, CWE-601).
- Added atom 25: `mass-assignment` — Mass Assignment: a profile-update endpoint copies every field of the client's JSON onto the account (`account.update(data)`), so adding `"role": "admin"` escalates a normal user to admin; the fix is a server-side field allowlist that accepts only name and email (A01 Broken Access Control, CWE-915).

## [0.4.0] - 2026-07-26

Server-side & Advanced (Phase 4 of the ROADMAP). Five atoms covering server-side attack surface and injection into engines beyond the database: blind and cloud-metadata SSRF, XXE file disclosure, server-side template injection, and insecure deserialization to remote code execution. Each atom isolates one flaw with vulnerable/ and fixed/ side by side, Burp-first walkthroughs, and bilingual docs (EN + PT-BR).

### Added

- Added atom 16: `ssrf-blind-oob` — Blind SSRF, confirmed out-of-band via an embedded listener (A10 SSRF).
- Added atom 17: `ssrf-cloud-metadata` — SSRF against the cloud metadata endpoint (169.254.169.254), stealing IAM credentials (A10 SSRF).
- Added atom 18: `xxe-basic` — XML External Entity (XXE) injection: arbitrary file disclosure via an lxml parser that resolves external entities (A05 Security Misconfiguration).
- Added atom 19: `ssti-jinja` — Server-side template injection (SSTI): user input sewn into a Jinja2 template is evaluated by the engine, disclosing the Flask config and SECRET_KEY (A03 Injection).
- Added atom 20: `deserialization-pickle` — Insecure deserialization: an attacker-controlled cookie deserialized with Python's pickle executes embedded behavior via `__reduce__`, giving remote code execution (A08 Software and Data Integrity Failures).

## [0.3.0] - 2026-07-20

Access Control & Authentication (Phase 3 of the ROADMAP). Five atoms spanning access control and identity: guessable-UUID and REST BOLA object-level flaws, the JWT trilogy completed with weak-secret and key-confusion, and session fixation. Each atom isolates one flaw with vulnerable/ and fixed/ side by side, Burp-first walkthroughs, and bilingual docs (EN + PT-BR).

### Added

- Added atom 11: `idor-uuid-guessable` — Insecure Direct Object Reference (guessable UUID) (A01 Broken Access Control).
- Added atom 12: `bola-rest` — Broken Object Level Authorization (BOLA) in a REST API (A01 Broken Access Control).
- Added atom 13: `jwt-weak-secret` — JWT weak signing secret, brute-forced (A02 Cryptographic Failures).
- Added atom 14: `jwt-key-confusion` — JWT algorithm confusion, RS256 → HS256 (A02 Cryptographic Failures).
- Added atom 15: `session-fixation` — session id not regenerated at login (A07 Identification and Authentication Failures).

## [0.2.0] - 2026-07-06

Injection Deep Dive (Phase 2 of the ROADMAP). Five atoms deepening the injection classes and bridging into access control: the SQLi trilogy completed with its blind pair (boolean- and time-based), stored XSS, OS command injection, and path traversal.

### Added

- Added atom 06: `sqli-blind-boolean` — Blind SQL injection (boolean-based) (A03 Injection).
- Added atom 07: `sqli-blind-time` — Blind SQL injection (time-based) (A03 Injection).
- Added atom 08: `xss-stored` — Stored Cross-Site Scripting (A03 Injection).
- Added atom 09: `command-injection-basic` — OS Command Injection (A03 Injection).
- Added atom 10: `path-traversal-basic` — Path traversal (A01 Broken Access Control).

## [0.1.0] - 2026-05-21

First public release — MVP Pentester (Phase 1 of the ROADMAP).

### Added

- Added atom 01: `sqli-union-basic` — UNION-based SQL Injection (A03 Injection).
- Added atom 02: `xss-reflected` — Reflected Cross-Site Scripting (A03 Injection).
- Added atom 03: `idor-numeric-id` — Insecure Direct Object Reference (numeric ID) (A01 Broken Access Control).
- Added atom 04: `ssrf-basic` — Server-Side Request Forgery (basic) (A10 SSRF).
- Added atom 05: `jwt-none-alg` — JWT alg=none signature bypass (A02 Cryptographic Failures).

- Added `./atom` wrapper CLI for atom lifecycle (`up`, `down`, `list`, `doctor`).
- Added `Makefile` with shortcuts equivalent to the wrapper.
- Added per-atom `docker-compose.yml`, binding every container to `127.0.0.1`.
- Added repository scaffolding: bilingual root READMEs (EN + PT-BR), banner asset (`docs/assets/banner.svg`), atom spec template (`docs/templates/ATOM-SPEC-TEMPLATE.md`), `.gitignore`, `.gitattributes`, MIT `LICENSE`.

- Added `CLAUDE.md` — project briefing and contributor conventions.
- Added `ROADMAP.md` — ordered implementation plan (7 phases, ~38 atoms) plus a transversal "Infraestrutura e governança" track.
- Added `SECURITY.md` / `SECURITY.pt-BR.md` — security policy with intentional-vulnerability disclaimer, scope of legitimate reports, and GitHub Security Advisories as the report channel.
- Added `CONTRIBUTING.md` / `CONTRIBUTING.pt-BR.md` — contribution guide.

- Established Theory primer requirement: every atom README links to its corresponding PortSwigger Web Security Academy page.
- Established cross-atom reference policy: atoms only reference already-published atoms; forward references to planned atoms live in `ROADMAP.md`.
- Established port convention: vulnerable on `127.0.0.1:80NN`, fixed on `127.0.0.1:81NN`, where `NN` is the atom's sequence number.
- Established mandatory `127.0.0.1` binding for every lab container, validated manually in PR review.
- Established bilingual documentation requirement: every atom ships EN + PT-BR versions of `README.md`, `WALKTHROUGH.md`, and `DIFF.md`, kept in sync within the same commit.
- Established Burp Suite as the primary exploration path in every walkthrough; UI is context only.

[Unreleased]: https://github.com/doretox/atomicvulns/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/doretox/atomicvulns/compare/v0.6.0...v1.0.0
[0.6.0]: https://github.com/doretox/atomicvulns/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/doretox/atomicvulns/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/doretox/atomicvulns/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/doretox/atomicvulns/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/doretox/atomicvulns/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/doretox/atomicvulns/releases/tag/v0.1.0