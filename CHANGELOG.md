# Changelog

All notable changes to atomicvulns will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/doretox/atomicvulns/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/doretox/atomicvulns/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/doretox/atomicvulns/releases/tag/v0.1.0