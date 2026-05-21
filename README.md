<p align="center">
  <img src="docs/assets/banner.svg" alt="atomicvulns — one vuln per app. nothing more." width="100%">
</p>

<!-- Badges — initial placeholders; more to come (CI, coverage, release, etc.) -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Status](https://img.shields.io/badge/status-early%20development-orange)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![OWASP Top 10](https://img.shields.io/badge/OWASP-Top%2010%202021-red)

> ⚠️ **Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.**

**Read this in other languages:** [Português (Brasil)](./README.pt-BR.md)

## What is atomicvulns?

`atomicvulns` is a collection of *atomic* web applications — each one tiny, isolated, and focused on **a single vulnerability** from the OWASP Top 10. Every atom ships with the vulnerable app, the fixed version, a commented diff between the two, and a hands-on walkthrough of the exploit.

This is **not** another DVWA or Juice Shop. Monolithic vulnerable apps already exist. What sets atomicvulns apart is *radical atomism*: one app per flaw, fast to read, fast to explore. You map code cause → request/response → exploit without having to understand an entire application first.

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
