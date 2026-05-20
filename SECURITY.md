# Security Policy

**Read this in other languages:** [Português (Brasil)](./SECURITY.pt-BR.md)

## This is an intentionally vulnerable project

The applications under `atoms/` are deliberately broken for educational purposes. **Do not report the vulnerabilities in atoms as security issues** — every flaw is intentional and documented in the atom's `WALKTHROUGH.md` and `DIFF.md`.

If you're unsure whether a given behavior is an intentional lab feature or a real bug, check the atom's `WALKTHROUGH.md` first. If the behavior is described there, it's the lab.

## What counts as a security issue here

The following are legitimate to report:

- Vulnerabilities in the wrapper script (`./atom`) that could affect the host running the labs
- Network bind misconfigurations — anything binding to `0.0.0.0` instead of `127.0.0.1` (see [CLAUDE.md §8](./CLAUDE.md))
- Container escape paths in the lab infrastructure itself
- Cross-contamination between atoms — one atom's container reaching another's network when it shouldn't
- Supply-chain risks in build dependencies of the wrapper or shared infrastructure
- Issues in CI or repository tooling (once present)

## Permission to test

You're explicitly authorized to probe the wrapper, infrastructure, and build pipeline for issues falling under the categories above. Probing the atoms themselves is the intended use of the project, so no permission needed there.

Do not probe atomicvulns infrastructure that isn't this repo (e.g. anything on a domain like `atomicvulns.com` if one exists). The project is the code in this repository, period.

## How to report

Use **[GitHub Security Advisories](https://github.com/doretox/atomicvulns/security/advisories/new)** to open a private report. This keeps the discussion off the public issue tracker until a fix is in place.

If that interface isn't available for any reason, open a regular issue with the title prefixed by "Security:" and **no technical details** — I'll move it to a private channel.

Please include:

- A short description of the issue and its impact
- Reproduction steps (commands, requests, expected vs. actual behavior)
- The commit SHA you tested against

## What to expect

- Acknowledgement within a few days
- Coordinated public disclosure once the fix is in place
- Credit in the release notes, if you want it

## What not to expect

- A bug bounty — this is a free educational project
- Fixes for "vulnerabilities" inside the labs themselves — those *are* the lab

## Responsible use

The atoms exist to teach. Running them on infrastructure you don't own, deploying them on public networks, or using techniques learned here against systems without authorization is illegal in most jurisdictions and against the spirit of this project.
