# Changelog

All notable changes to atomicvulns will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added atom 26: `prototype-pollution` — Prototype pollution: a hand-written deep-merge of untrusted JSON descends through the `__proto__` key and writes onto the shared `Object.prototype`, so `{"__proto__":{"isAdmin":true}}` poisons every object in the process — a brand-new, untouched object at `GET /me` inherits `isAdmin` and is treated as admin; the fix guards the merge against the `__proto__`, `constructor`, and `prototype` keys (A08 Software and Data Integrity Failures, CWE-1321).
- Added atom 27: `deserialization-node` — Insecure deserialization: an attacker-controlled cookie deserialized with Node's `node-serialize` library carries a `_$$ND_FUNC$$_`-tagged function that the library `eval`s on unserialize; a self-invoking function body runs during unserialize, giving remote code execution — the Node face of the flaw `deserialization-pickle` shows in Python; the fix changes the format to JSON (`JSON.parse`, data only) and drops the dependency (A08 Software and Data Integrity Failures).

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

[Unreleased]: https://github.com/doretox/atomicvulns/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/doretox/atomicvulns/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/doretox/atomicvulns/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/doretox/atomicvulns/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/doretox/atomicvulns/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/doretox/atomicvulns/releases/tag/v0.1.0