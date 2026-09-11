<p align="center">
  <img src="docs/assets/banner.svg" alt="atomicvulns — one vuln per app. nothing more." width="100%">
</p>

<!-- Badges -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Release](https://img.shields.io/github/v/release/doretox/atomicvulns)](https://github.com/doretox/atomicvulns/releases/latest)
![Atoms](https://img.shields.io/badge/atoms-38-blue)
![OWASP Top 10](https://img.shields.io/badge/OWASP-Top%2010%202021-red)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

> ⚠️ **Código intencionalmente vulnerável. Rode apenas localmente. Nunca exponha à internet ou a uma rede compartilhada.**

**Este README em outros idiomas:** [English](./README.md)

## O que é o atomicvulns?

> **Marco — v1.0:** o atomicvulns agora cobre **todas as dez categorias do OWASP Top 10 2021 (A01–A10)**, em **38 átomos**. Veja a [release v1.0](https://github.com/doretox/atomicvulns/releases/tag/v1.0.0).

`atomicvulns` é uma coleção de aplicações web *atômicas* — cada uma minúscula, isolada e focada em **uma única vulnerabilidade** do OWASP Top 10. Todo átomo entrega a app vulnerável, a versão corrigida, um diff comentado entre as duas e um walkthrough prático do exploit.

Este projeto **não** é mais um DVWA ou Juice Shop. Apps vulneráveis monolíticas já existem. O diferencial do atomicvulns é o *atomismo radical*: uma app por falha, rápida de ler, rápida de explorar. Você mapeia código causal → request/response → exploit sem precisar entender uma aplicação inteira antes.

## Cobertura

Todas as dez categorias do OWASP Top 10 2021 estão cobertas — 38 átomos no total:

| Categoria | Átomos |
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

## Público-alvo

Estudantes de pentest e de AppSec que já sabem o básico de HTTP e terminal, usam (ou estão aprendendo a usar) **Burp Suite**, e querem um laboratório focado onde cada exercício é curto o suficiente para terminar de uma sentada. O material é escrito para quem vai aplicar isso na carreira de pentest — Burp é a ferramenta principal, a UI é só contexto.

## Rodando um átomo

Cada átomo vive em sua própria pasta sob `atoms/A0X-<categoria>/<atom-id>/` e vem com um `docker-compose.yml`. Um script wrapper na raiz, `./atom`, dirige os átomos:

```bash
./atom list                 # lista todos os átomos disponíveis
./atom up <atom-id>         # sobe o par vulnerable + fixed
./atom down <atom-id>       # para e remove os containers
./atom doctor               # checagem básica do ambiente local
```

Por exemplo, para subir o primeiro átomo:

```bash
./atom up sqli-union-basic
# vulnerable → http://127.0.0.1:8001
# fixed      → http://127.0.0.1:8101
```

Todo átomo faz bind apenas em `127.0.0.1`. **Nunca** altere isso — essas apps são intencionalmente quebradas.

## Documentação

- **[ROADMAP.md](./ROADMAP.md)** — plano ordenado de implementação e checklist de progresso.
- **[CLAUDE.md](./CLAUDE.md)** — *para contribuidores:* briefing do projeto, convenções e regras de base.

## Licença

Publicado sob a [Licença MIT](./LICENSE). Se você forkar este repositório para material didático, atribuição é obrigatória.
