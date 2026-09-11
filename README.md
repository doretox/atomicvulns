<p align="center">
  <img src="docs/assets/banner.svg" alt="atomicvulns — one vuln per app. nothing more." width="100%">
</p>

<!-- Badges -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Release](https://img.shields.io/github/v/release/doretox/atomicvulns)](https://github.com/doretox/atomicvulns/releases/latest)
![Atoms](https://img.shields.io/badge/atoms-38-blue)
![OWASP Top 10](https://img.shields.io/badge/OWASP-Top%2010%202021-red)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

> ⚠️ **Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.**

**Read this in other languages:** [Português (Brasil)](./README.pt-BR.md)

## What is atomicvulns?

> **Milestone — v1.0:** atomicvulns now covers **all ten OWASP Top 10 2021 categories (A01–A10)**, across **38 atoms**. See the [v1.0 release](https://github.com/doretox/atomicvulns/releases/tag/v1.0.0).

`atomicvulns` is a collection of *atomic* web applications — each one tiny, isolated, and focused on **a single vulnerability** from the OWASP Top 10. Every atom ships with the vulnerable app, the fixed version, a commented diff between the two, and a hands-on walkthrough of the exploit.

This is **not** another DVWA or Juice Shop. Monolithic vulnerable apps already exist. What sets atomicvulns apart is *radical atomism*: one app per flaw, fast to read, fast to explore. You map code cause → request/response → exploit without having to understand an entire application first.

## Coverage

All ten OWASP Top 10 2021 categories are covered — 38 atoms in total:

| Category | Atoms |
|---|---|
| **A01 — Broken Access Control** | `idor-numeric-id`, `path-traversal-basic`, `idor-uuid-guessable`, `bola-rest`, `csrf-basic`, `open-redirect`, `mass-assignment` |
| **A02 — Cryptographic Failures** | `jwt-none-alg`, `jwt-weak-secret`, `jwt-key-confusion`, `crypto-weak-hash`, `crypto-ecb-mode` |
| **A03 — Injection** | `sqli-union-basic`, `xss-reflected`, `sqli-blind-boolean`, `sqli-blind-time`, `xss-stored`, `command-injection-basic`, `ssti-jinja`, `xss-dom`, `nosql-injection-mongo`, `ldap-injection`, `sqli-second-order` |
| **A04 — Insecure Design** | `race-condition-basic` |
| **A05 — Security Misconfiguration** | `xxe-basic`, `xxe-blind-oob`, `debug-enabled`, `cors-wildcard` |
| **A06 — Vulnerable and Outdated Components** | `cve-demo` |
| **A07 — Identification and Authentication Failures** | `session-fixation`, `weak-password-reset` |
| **A08 — Software and Data Integrity Failures** | `deserialization-pickle`, `prototype-pollution`, `deserialization-node` |
| **A09 — Security Logging and Monitoring Failures** | `logging-failures-demo` |
| **A10 — Server-Side Request Forgery (SSRF)** | `ssrf-basic`, `ssrf-blind-oob`, `ssrf-cloud-metadata` |

## Target audience

Pentest students and AppSec learners who already know the basics of HTTP and the terminal, use (or are learning to use) **Burp Suite**, and want a focused lab where each exercise is short enough to finish in one sitting. The material is written for someone who will apply this in a pentest career — Burp is the primary tool, the UI is just context.

## Running an atom

Each atom lives in its own folder under `atoms/A0X-<category>/<atom-id>/` and ships with a `docker-compose.yml`. A root wrapper script, `./atom`, drives them:

```bash
./atom list                 # show all available atoms
./atom up <atom-id>         # start the vulnerable + fixed pair
./atom down <atom-id>       # stop and remove containers
./atom doctor               # sanity-check your local setup
```

For example, to start the first atom:

```bash
./atom up sqli-union-basic
# vulnerable → http://127.0.0.1:8001
# fixed      → http://127.0.0.1:8101
```

Every atom binds to `127.0.0.1` only. **Never** change that — these apps are intentionally broken.

## Documentation

- **[ROADMAP.md](./ROADMAP.md)** — ordered implementation plan and progress checklist.
- **[CLAUDE.md](./CLAUDE.md)** — *for contributors:* project briefing, conventions, and ground rules.

## License

Released under the [MIT License](./LICENSE). If you fork this repository for educational material, attribution is required.
