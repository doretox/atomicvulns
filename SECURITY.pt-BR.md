# Política de Segurança

**Este documento em outros idiomas:** [English](./SECURITY.md)

## Este é um projeto intencionalmente vulnerável

As aplicações em `atoms/` são deliberadamente quebradas para fins educacionais. **Não reporte as vulnerabilidades dos átomos como problemas de segurança** — toda falha é intencional e está documentada no `WALKTHROUGH.md` e no `DIFF.md` do átomo.

Se você não tem certeza se um comportamento é feature intencional do lab ou bug real, confira o `WALKTHROUGH.md` do átomo primeiro. Se o comportamento estiver descrito lá, é o lab.

## O que conta como problema de segurança aqui

Os seguintes são reports legítimos:

- Vulnerabilidades no script wrapper (`./atom`) que possam afetar o host rodando os labs
- Misconfigurations de bind de rede — qualquer coisa bindando em `0.0.0.0` em vez de `127.0.0.1` (ver [CLAUDE.md §8](./CLAUDE.md))
- Caminhos de container escape na infraestrutura do lab em si
- Contaminação cruzada entre átomos — o container de um átomo alcançando a rede de outro quando não deveria
- Riscos de supply chain nas dependências de build do wrapper ou da infraestrutura compartilhada
- Issues em CI ou tooling do repositório (quando existirem)

## Permissão para testar

Você está explicitamente autorizado a testar o wrapper, a infraestrutura e o pipeline de build em busca de problemas que se enquadrem nas categorias acima. Testar os átomos em si é o uso pretendido do projeto, então não precisa de permissão pra isso.

Não teste infraestrutura do atomicvulns que não seja este repositório (ex.: qualquer coisa em um domínio tipo `atomicvulns.com` se vier a existir). O projeto é o código deste repositório, ponto.

## Como reportar

Use **[GitHub Security Advisories](https://github.com/doretox/atomicvulns/security/advisories/new)** para abrir um report privado. Isso mantém a discussão fora do issue tracker público até o fix entrar.

Se essa interface não estiver disponível por algum motivo, abra uma issue normal com o título prefixado por "Security:" e **sem detalhes técnicos** — vou mover para um canal privado.

Inclua:

- Descrição curta do issue e do impacto
- Passos de reprodução (comandos, requests, comportamento esperado vs. atual)
- O SHA do commit que você testou

## O que esperar

- Reconhecimento em alguns dias
- Disclosure público coordenado quando o fix estiver em produção
- Crédito nas release notes, se quiser

## O que NÃO esperar

- Bug bounty — este é um projeto educacional gratuito
- Fixes para "vulnerabilidades" dentro dos labs — elas *são* o lab

## Uso responsável

Os átomos existem pra ensinar. Rodar eles em infraestrutura que você não é dono, deployar em redes públicas, ou usar técnicas aprendidas aqui contra sistemas sem autorização é ilegal na maioria das jurisdições e contra o espírito deste projeto.
