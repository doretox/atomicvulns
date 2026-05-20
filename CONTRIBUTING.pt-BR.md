# Contribuindo com o atomicvulns

**Este documento em outros idiomas:** [English](./CONTRIBUTING.md)

Obrigado pelo interesse. Este documento explica como contribuir de forma efetiva.

## Que tipos de contribuição são bem-vindos

- **Átomos novos** que sigam o princípio de atomismo: uma vulnerabilidade por app (ver [CLAUDE.md §2](./CLAUDE.md))
- **Traduções** de conteúdo existente (PT-BR ou idiomas novos)
- **Melhorias em walkthroughs e DIFFs** — clareza, precisão, valor pedagógico
- **Melhorias no script wrapper (`./atom`)**
- **Trabalho de CI e infraestrutura** listado em "Infraestrutura e governança" no [ROADMAP.md](./ROADMAP.md)
- **Bug fixes na infraestrutura dos labs** (compose, networking, wrapper)

## O que NÃO é bem-vindo

- "Consertar" as vulnerabilidades dos átomos — elas são intencionais
- Átomos que combinam múltiplas vulnerabilidades — viola o atomismo; separe em átomos diferentes
- Reescritas com framework pesado (Django em vez de Flask, TypeScript em vez de Python) — o projeto escolheu a stack de propósito (ver CLAUDE.md §3)
- Otimizações de performance — apps de lab são intencionalmente simples, não rápidas
- Melhorias de UI além do mínimo de HTML que o projeto permite (ver CLAUDE.md §3.3)

## Antes de abrir uma issue

- **Discussão de design ou proposta:** abra uma Discussion, não uma Issue
- **Proposta de átomo novo:** confira o [ROADMAP.md](./ROADMAP.md) primeiro — pode já estar planejado. Se não estiver, abra uma Discussion para propor
- **Bug na infraestrutura dos labs** (wrapper, compose, networking): abra uma Issue com passos de reprodução
- **Issue de segurança:** ver [SECURITY.md](./SECURITY.md)

## Como propor um átomo novo

1. Confira o [ROADMAP.md](./ROADMAP.md) pelo átomo que você quer construir, ou pelo próximo slot disponível
2. Abra uma Discussion para alinhar escopo e abordagem com o mantenedor
3. Uma vez alinhado, siga o workflow da [CLAUDE.md §10](./CLAUDE.md). Este projeto é construído com Claude Code, mas você não precisa usar — o mesmo template e convenções valem para contribuidores humanos
4. O átomo deve incluir: versões `vulnerable/` + `fixed/` funcionais, `WALKTHROUGH.md` (EN+PT), `DIFF.md` (EN+PT), `README.md` (EN+PT), `docker-compose.yml` e o bloco Theory primer linkando a PortSwigger Academy (ver [CLAUDE.md §5](./CLAUDE.md))

## Fluxo

1. Forke o repo
2. Crie uma feature branch: `feat/atom-id`, `docs/...`, `fix/...`, etc.
3. Commit usando [Conventional Commits](https://www.conventionalcommits.org/) (ver [CLAUDE.md §6](./CLAUDE.md) para exemplos)
4. Abra um Pull Request contra `main`
5. Aguarde a revisão. O mantenedor valida todo átomo manualmente via Burp antes do merge, o que pode levar de um dia a algumas semanas dependendo da disponibilidade. Tenha paciência; este é um projeto pessoal.

## Estilo

- **Python:** PEP 8. Sem linter formal — a codebase é minúscula, julgamento vale mais que ferramenta
- **Markdown:** quebra de linha por volta dos 80 caracteres quando razoável; não force a quebra quando a prosa flui melhor com linha longa
- **Mensagens de commit:** Conventional Commits em inglês (`feat(scope): ...`, `docs: ...`, etc.)
- **Idioma da documentação:** código em inglês, docs em inglês + PT-BR, sincronizadas no mesmo commit (ver [CLAUDE.md §7](./CLAUDE.md))

## Licença

Ao contribuir, você concorda que sua contribuição seja licenciada sob a [Licença MIT](./LICENSE) do projeto.
