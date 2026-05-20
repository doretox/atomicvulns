# Contributing to atomicvulns

**Read this in other languages:** [Português (Brasil)](./CONTRIBUTING.pt-BR.md)

Thanks for your interest. This document explains how to contribute effectively.

## What kinds of contributions are welcome

- **New atoms** that follow the atomism principle: one vulnerability per app (see [CLAUDE.md §2](./CLAUDE.md))
- **Translations** of existing atom content (PT-BR, or new languages)
- **Improvements to walkthroughs and DIFFs** — clarity, accuracy, pedagogical value
- **Wrapper script (`./atom`) improvements**
- **CI and infrastructure work** listed under "Infraestrutura e governança" in [ROADMAP.md](./ROADMAP.md)
- **Bug fixes in lab infrastructure** (compose, networking, wrapper)

## What is NOT welcome

- "Fixing" the vulnerabilities in atoms — they're intentional
- Atoms that bundle multiple vulnerabilities — violates atomism; split them
- Heavy-framework rewrites (Django instead of Flask, TypeScript instead of Python) — the project picked its stack on purpose (see CLAUDE.md §3)
- Performance optimizations — lab apps are intentionally simple, not fast
- UI improvements beyond the minimum HTML the project allows (see CLAUDE.md §3.3)

## Before opening an issue

- **Design discussion or proposal:** open a Discussion, not an Issue
- **New atom proposal:** check [ROADMAP.md](./ROADMAP.md) first — it may already be planned. If not, open a Discussion to propose
- **Bug in lab infrastructure** (wrapper, compose, networking): open an Issue with reproduction steps
- **Security issue:** see [SECURITY.md](./SECURITY.md)

## How to propose a new atom

1. Check [ROADMAP.md](./ROADMAP.md) for the atom you want to build, or for the next available slot
2. Open a Discussion to confirm scope and approach with the maintainer
3. Once aligned, follow the workflow in [CLAUDE.md §10](./CLAUDE.md). This project is built with Claude Code, but you don't need it — the same template and conventions apply to human contributors
4. The atom must include: working `vulnerable/` + `fixed/` versions, `WALKTHROUGH.md` (EN+PT), `DIFF.md` (EN+PT), `README.md` (EN+PT), `docker-compose.yml`, and the Theory primer block linking PortSwigger Academy (see [CLAUDE.md §5](./CLAUDE.md))

## Workflow

1. Fork the repo
2. Create a feature branch: `feat/atom-id`, `docs/...`, `fix/...`, etc.
3. Commit using [Conventional Commits](https://www.conventionalcommits.org/) (see [CLAUDE.md §6](./CLAUDE.md) for examples)
4. Open a Pull Request against `main`
5. Wait for review. The maintainer validates every atom manually via Burp before merge, which can take from a day to a couple of weeks depending on availability. Be patient; this is a personal project.

## Style

- **Python:** PEP 8. No formal linter — the codebase is tiny, judgment beats tooling
- **Markdown:** wrap lines around 80 chars where reasonable; don't fight the wrap when prose flows better long
- **Commit messages:** Conventional Commits in English (`feat(scope): ...`, `docs: ...`, etc.)
- **Documentation language:** English code, English + PT-BR docs, synchronized in the same commit (see [CLAUDE.md §7](./CLAUDE.md))

## License

By contributing, you agree your contributions are licensed under the project's [MIT License](./LICENSE).
