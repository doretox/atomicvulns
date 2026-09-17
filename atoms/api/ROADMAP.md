# ROADMAP.md — atomicvulns API

> Checklist vivo da série **API**. Marque `[x]` conforme concluir cada átomo.
> Fonte da verdade para o próximo átomo a implementar.
>
> **Backbone:** OWASP API Security Top 10 — 2023.

---

## Como usar este arquivo

- **Ordem é proposital.** Cada átomo é pré-requisito conceitual do próximo,
  salvo quando marcado independente.
- **Fases são marcos publicáveis.** Ao fechar uma fase, o repo ganha uma
  release.
- **Numeração própria, do 01.** A série API conta do zero, independente do web.
- **Range de portas dedicado:** `vulnerable` em `82NN`, `fixed` em `83NN`,
  onde `NN` é a sequência da série (átomo 01 → 8201/8301). Não renumere átomos
  publicados.
- **Categoria ≠ número de build.** A pasta usa o código OWASP (`API1`…`API10`);
  o número de build (01–20) é a ordem de implementação e governa a porta.

Legenda:
- `[ ]` — pendente
- `[~]` — em progresso (branch `atom/<id>` aberta)
- `[x]` — concluído e em `main`
- `[s]` — pulado (com justificativa no comentário)

---

## Premissas da série

- **Stack:** TypeScript / Express / `tsx`, containerizado via Docker Compose e
  dirigido pelo wrapper `./atom`.
- **Anatomia:** `vulnerable/` + `fixed/` como build-contexts Docker
  self-contained (`package.json` + `tsconfig` próprios em cada um).
- **Auth:** token opaco via `POST /login`, replicado por átomo (sem módulo
  compartilhado).
- **Prova sem payload:** classes sem sink (API4, API6, API9, API10) provam por
  Trigger — o walkthrough executa uma ação com efeito observável.
- **Documentação:** EN + PT-BR sincronizados; Theory primer obrigatório por
  átomo.

---

## Fase 1 — Authorization: Object & Function

**Objetivo:** os dois primeiros níveis de authorization — qual objeto se
acessa (BOLA) e qual função se invoca (BFLA).

**Milestone:** `v1.1 — API Object & Function Authz`

- [ ] **01.** `bola-sequential-id` — **API1** Broken Object Level Authorization
  - Átomo-bandeira e átomo de referência de estilo da série (primeiro TS).
    Exploit base: trocar o ID de objeto na request.
  - *Dependências:* nenhuma. Portas 8201/8301.

- [ ] **02.** `bola-uuid-leaked` — **API1** Broken Object Level Authorization
  - ID não-adivinhável (UUID) que vaza por outro endpoint. Isola a causa:
    BOLA é check ausente, não ID adivinhável.
  - *Dependências:* átomo 01.

- [ ] **03.** `bola-nested-resource` — **API1** Broken Object Level Authorization
  - Recurso aninhado (`/users/{id}/orders/{oid}`): check do objeto-pai passa,
    do objeto-filho falta.
  - *Dependências:* átomos 01–02.

- [ ] **04.** `bfla-admin-function` — **API5** Broken Function Level Authorization
  - User comum invoca endpoint admin-only sem check de role (priv-esc vertical).
  - *Dependências:* átomos 01–03.

- [ ] **05.** `bfla-method-based` — **API5** Broken Function Level Authorization
  - `GET` permitido; `DELETE`/`PUT` no mesmo path não checado. O check depende
    do método e falta em um deles.
  - *Dependências:* átomo 04.

---

## Fase 2 — Authorization: Property & Authentication

**Objetivo:** authz no nível de propriedade (BOPLA, split leitura/escrita),
depois a passagem para authentication.

**Milestone:** `v1.2 — API Property Authz & Auth`

- [ ] **06.** `bopla-excessive-exposure` — **API3** Broken Object Property Level Authorization
  - Face de leitura: o `GET` devolve propriedades que deveria ocultar
    (`password_hash`, `is_admin`, campos internos).
  - *Dependências:* átomos 01–05.

- [ ] **07.** `bopla-mass-assignment` — **API3** Broken Object Property Level Authorization
  - Face de escrita: o `PATCH` aceita propriedades que deveria rejeitar
    (`{"is_admin": true}` num update de perfil).
  - *Dependências:* átomo 06.

- [ ] **08.** `auth-predictable-token` — **API2** Broken Authentication
  - Token opaco previsível emitido no login; forja do token de outro usuário
    em uma request.
  - *Dependências:* átomo 01.

- [ ] **09.** `auth-no-lockout` — **API2** Broken Authentication
  - Login sem lockout nem throttle: credential stuffing / brute force.
  - *Dependências:* nenhuma.

- [ ] **10.** `oauth-client-cred-unverified` — **API2** Broken Authentication
  - Gateway valida a presença do client credential mas não o conteúdo.
  - *Dependências:* átomos 08–09.

---

## Fase 3 — Resource Abuse & Business Logic

**Objetivo:** abuso por limite e automação. Primeiros átomos puramente Trigger.

**Milestone:** `v1.3 — API Resource & Business Abuse`

- [ ] **11.** `resource-unbounded-param` — **API4** Unrestricted Resource Consumption
  - Parâmetro sem cap (`?limit=1000000`, batch ilimitado): uma request consome
    recurso desproporcional.
  - *Dependências:* nenhuma.

- [ ] **12.** `resource-no-rate-limit` — **API4** Unrestricted Resource Consumption
  - Ausência de rate limit: abuso por volume de requests.
  - *Dependências:* átomo 11.

- [ ] **13.** `business-flow-scalping` — **API6** Unrestricted Access to Sensitive Business Flows
  - Fluxo de negócio sensível (estoque limitado, cupom) sem anti-automação,
    abusado por script.
  - *Dependências:* átomos 11–12.

---

## Fase 4 — Server-side, Posture & Consumption

**Objetivo:** SSRF, postura de configuração, inventário e consumo de terceiros.
Fecha o Top 10 de API.

**Milestone:** `v2.0 — Full OWASP API Top 10 Coverage`

- [ ] **14.** `ssrf-url-param` — **API7** Server-Side Request Forgery
  - SSRF via parâmetro de URL.
  - *Dependências:* nenhuma.

- [ ] **15.** `ssrf-webhook` — **API7** Server-Side Request Forgery
  - SSRF via URL de callback/webhook chamada server-side.
  - *Dependências:* átomo 14.

- [ ] **16.** `misconfig-verbose-errors` — **API8** Security Misconfiguration
  - Input malformado dispara stack trace verboso vazando internals.
  - *Dependências:* nenhuma.

- [ ] **17.** `misconfig-actuator-exposed` — **API8** Security Misconfiguration
  - Endpoint de debug/actuator exposto, dumpando config/env.
  - *Dependências:* átomo 16.

- [ ] **18.** `misconfig-permissive-cors` — **API8** Security Misconfiguration
  - CORS credentialed cross-origin: reflexão de `Origin` com
    `Allow-Credentials: true`.
  - *Dependências:* átomo 16.

- [ ] **19.** `inventory-shadow-version` — **API9** Improper Inventory Management
  - Versão antiga não-documentada no ar (`/v1/` vulnerável ao lado de `/v2/`
    corrigido).
  - *Dependências:* nenhuma.

- [ ] **20.** `unsafe-consumption-upstream` — **API10** Unsafe Consumption of APIs
  - A API confia sem validar na resposta de um upstream de terceiro; a resposta
    envenenada é injetada no consumer. Requer um terceiro serviço (o upstream).
  - *Dependências:* nenhuma.

---

## Cobertura

| Categoria | Átomos |
|---|---|
| API1 — Broken Object Level Authorization | `bola-sequential-id`, `bola-uuid-leaked`, `bola-nested-resource` |
| API2 — Broken Authentication | `auth-predictable-token`, `auth-no-lockout`, `oauth-client-cred-unverified` |
| API3 — Broken Object Property Level Authorization | `bopla-excessive-exposure`, `bopla-mass-assignment` |
| API4 — Unrestricted Resource Consumption | `resource-unbounded-param`, `resource-no-rate-limit` |
| API5 — Broken Function Level Authorization | `bfla-admin-function`, `bfla-method-based` |
| API6 — Unrestricted Access to Sensitive Business Flows | `business-flow-scalping` |
| API7 — Server-Side Request Forgery | `ssrf-url-param`, `ssrf-webhook` |
| API8 — Security Misconfiguration | `misconfig-verbose-errors`, `misconfig-actuator-exposed`, `misconfig-permissive-cors` |
| API9 — Improper Inventory Management | `inventory-shadow-version` |
| API10 — Unsafe Consumption of APIs | `unsafe-consumption-upstream` |

---

## Versionamento

| Fase | Milestone |
|---|---|
| Fase 1 | `v1.1` |
| Fase 2 | `v1.2` |
| Fase 3 | `v1.3` |
| Fase 4 | `v2.0` |

---

**Última atualização do plano:** criação do documento.
