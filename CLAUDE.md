# CLAUDE.md — Briefing do Projeto

> Este documento é o ponto de partida para qualquer sessão do Claude Code neste repositório. Leia-o antes de gerar código, estrutura de pastas ou documentação. Mantenha-o atualizado conforme o projeto evolui.

---

## 1. Visão geral

**Nome:** `atomicvulns`

**O que é:** uma coleção de aplicações web *atômicas* — cada uma minúscula, isolada, e focada em **uma única vulnerabilidade** do OWASP Top 10. Cada átomo entrega: a app vulnerável, a versão corrigida, um diff comentado entre as duas, e walkthrough didático do exploit.

**O que NÃO é:** não é um DVWA/Juice Shop concorrente. Apps vulneráveis monolíticas já existem. O diferencial deste projeto é o *atomismo radical*: uma app por falha, rápida de ler, rápida de explorar.

**Público-alvo:** pentesters júnior (incluindo estudantes de pentest/AppSec) que já sabem o básico de HTTP e terminal, usam (ou estão aprendendo a usar) Burp Suite, e querem mapear *código causal → request/response → exploit* sem precisar entender uma aplicação inteira primeiro. O tom do material assume alguém que vai aplicar isso na carreira de pentest.

**Mantenedor:** projeto solo, médio/longo prazo.

**Arquivo complementar:** ver [`ROADMAP.md`](./ROADMAP.md) para o plano ordenado de implementação e checklist de progresso.

---

## 2. Princípios fundamentais (não negociáveis)

1. **Um átomo = uma vulnerabilidade.** Se precisar de duas, são dois átomos.
2. **Mínimo código possível.** Se a view vulnerável passa de ~30 linhas, provavelmente está fazendo coisa demais. O objetivo é que o estudante *leia e entenda rápido*, sem precisar navegar por múltiplos arquivos ou camadas de abstração.
3. **Vulnerável e corrigido vivem lado a lado.** Todo átomo tem uma pasta `vulnerable/` e uma `fixed/` com o mesmo endpoint, mesma feature — só o fix muda.
4. **Walkthrough reproduzível.** Todo exploit documentado deve funcionar *exatamente* como descrito. O mantenedor valida manualmente via Burp antes de qualquer merge.
5. **Segurança do estudante vem antes de tudo.** App intencionalmente vulnerável NUNCA bindа em `0.0.0.0` por padrão. Sempre `127.0.0.1`. Sempre com aviso no README.
6. **Didático > realista.** Quando houver conflito entre "mais fiel ao mundo real" e "mais claro pro iniciante", vence o claro.
7. **Burp é a ferramenta principal, UI é só contexto.** A exploração acontece no Burp; a UI existe pra o aluno entender a feature simulada antes de ir pro Repeater.

---

## 3. Stack técnica

### 3.1. Linguagem padrão: Python 3.11+ com Flask

Escolha por legibilidade didática, cobertura ampla do Top 10, e stdlib rico (sqlite3, subprocess, pickle — todos úteis pra ilustrar classes de falha).

### 3.2. Exceção à regra Python

Node.js + Express é permitido **apenas quando a vulnerabilidade é idiomática de JavaScript** e perde sentido pedagógico em Python. Na prática, isso cobre essencialmente:

- Prototype pollution
- Alguns casos específicos de NoSQL injection com MongoDB nativo
- Deserialization em Node (quando o objetivo é mostrar o ecossistema JS)

Nenhuma outra exceção sem discussão explícita. Evitar virar zoológico poliglota.

### 3.3. Rendering e interação com a aplicação

**Filosofia:** o pentester trabalha no Burp. A UI existe apenas para *contextualizar* a feature simulada — nunca para ser o meio de exploração. O aluno abre no browser uma vez pra entender "o que essa app faz", e dali em diante migra pro Burp Repeater/Intruder como faria num pentest real.

**Padrão: HTML mínimo server-rendered com Jinja2.**

Regras do HTML de cada átomo:

- **Tamanho:** `templates/index.html` tem no máximo 20–40 linhas. Sem exceção injustificada.
- **Conteúdo obrigatório:**
  - Banner fixo no topo: `⚠️ Intentionally vulnerable. Run locally only.`
  - Um `<form>` ou link mínimo que dispara o request vulnerável (pra o aluno ver a feature em ação).
  - Rodapé com a dica: `Open with Burp proxy enabled, interact once, then work from Burp Repeater.`
- **CSS:** até 5 linhas inline num `<style>` — apenas o suficiente pra não parecer quebrado. Sem frameworks, sem classes utilitárias, sem paleta de cores.
- **JavaScript:** proibido por padrão. Única exceção: átomos onde JS *é* o código causal da falha (DOM XSS, prototype pollution, postMessage issues). Nesses, JS cru, sem framework, mantido no mínimo absoluto.
- **Dependências de frontend:** zero. Nenhum React, Vue, Alpine, HTMX, bootstrap, tailwind. Se o Claude Code propuser qualquer framework de UI, rejeitar.

**Átomos naturalmente de API — sem HTML:**

Algumas classes são intrinsecamente API-only. Nestes átomos, não existe `templates/index.html`. O walkthrough assume interação direta via Burp ou curl. Categorias típicas:

- JWT (todas as variantes)
- BOLA em REST
- Mass assignment
- NoSQL injection quando modelada como endpoint REST puro

A decisão é por átomo: se a vulnerabilidade só faz sentido em contexto de API, não se força um frontend artificial.

**Walkthrough — duas trilhas, sempre nesta ordem:**

Todo `WALKTHROUGH.md` (e sua versão PT) tem duas seções de exploração:

1. **Trilha principal — via Burp Suite.** Request e response crus, passo a passo no Repeater, tal como o pentester real trabalharia. Esta é a trilha que ensina a profissão.
2. **Trilha secundária — via browser** (opcional, quando houver UI). Mostra a mesma exploração feita clicando na UI, pra quem ainda não configurou o Burp. Serve como primeira experiência de baixa fricção — quebra a barreira de entrada e deixa o aluno *sentir* o impacto (alert pipocando no XSS, dado de outro usuário aparecendo no IDOR).

Em átomos API-only, a trilha secundária não existe — só a principal, via Burp/curl.

### 3.4. Banco de dados

- **SQLite** por padrão (zero setup, arquivo local, realista o suficiente pra SQLi).
- **MongoDB** apenas em átomos de NoSQL injection.
- **PostgreSQL/MySQL** só se a vuln depende de uma feature específica daquele SGBD (ex: `pg_sleep`, `LOAD_FILE`).

### 3.5. Containerização

- **Docker Compose por átomo.** Cada átomo tem seu próprio `docker-compose.yml`.
- **Bind obrigatório em `127.0.0.1`** nas portas publicadas.
- **Wrapper simples na raiz** (`./atom` script em Bash ou Python) para UX: `./atom up <id>`, `./atom down <id>`, `./atom list`, `./atom doctor`.

### 3.6. Dependências mínimas

Cada átomo deve rodar com o menor conjunto de dependências possível. Se o átomo é de SSRF, não precisa ter ORM. Se é de SQLi, não precisa ter Celery. **Regra: só inclua a lib se ela serve à demonstração da falha ou ao fix.**

---

## 4. Estrutura do repositório

Átomos organizados por categoria do OWASP Top 10 (edição 2021). Cada categoria é uma pasta, e os átomos daquela categoria moram dentro.

```
atomicvulns/
├── CLAUDE.md                      # este arquivo
├── ROADMAP.md                     # plano ordenado e checklist de progresso
├── README.md                      # inglês, público
├── README.pt-BR.md                # português, público BR
├── LICENSE
├── atom                           # wrapper CLI (executável)
├── Makefile                       # atalhos equivalentes ao wrapper
├── atoms/
│   ├── A01-broken-access-control/
│   │   ├── idor-numeric-id/
│   │   ├── idor-uuid-guessable/
│   │   ├── bola-rest/
│   │   ├── path-traversal-basic/
│   │   ├── csrf-basic/
│   │   ├── open-redirect/
│   │   └── mass-assignment/
│   ├── A02-cryptographic-failures/
│   │   ├── crypto-weak-hash/
│   │   ├── crypto-ecb-mode/
│   │   ├── jwt-none-alg/
│   │   ├── jwt-weak-secret/
│   │   └── jwt-key-confusion/
│   ├── A03-injection/
│   │   ├── sqli-union-basic/
│   │   ├── sqli-blind-boolean/
│   │   ├── sqli-blind-time/
│   │   ├── sqli-second-order/
│   │   ├── nosql-injection-mongo/
│   │   ├── command-injection-basic/
│   │   ├── ldap-injection/
│   │   ├── xss-reflected/
│   │   ├── xss-stored/
│   │   ├── xss-dom/
│   │   └── ssti-jinja/
│   ├── A04-insecure-design/
│   │   └── race-condition-basic/
│   ├── A05-security-misconfiguration/
│   │   ├── debug-enabled/
│   │   ├── cors-wildcard/
│   │   ├── xxe-basic/
│   │   └── xxe-blind-oob/
│   ├── A06-vulnerable-components/
│   │   └── cve-demo/
│   ├── A07-auth-failures/
│   │   ├── weak-password-reset/
│   │   └── session-fixation/
│   ├── A08-data-integrity-failures/
│   │   ├── deserialization-pickle/
│   │   ├── deserialization-node/
│   │   └── prototype-pollution/
│   ├── A09-logging-failures/
│   │   └── logging-failures-demo/
│   └── A10-ssrf/
│       ├── ssrf-basic/
│       ├── ssrf-blind-oob/
│       └── ssrf-cloud-metadata/
├── docs/
│   ├── contributing.md
│   ├── atom-template/             # template pra criar novos átomos
│   └── validation-checklist.md
└── .github/
    └── workflows/                 # CI: build containers, smoke test
```

**Nota sobre categorização:** seguimos a OWASP Top 10 de 2021 (edição estável mais atual). Se surgir uma nova edição durante o projeto, revisamos o mapeamento sem reescrever os átomos — só movemos as pastas.

---

## 5. Anatomia de um átomo

Cada pasta de átomo em `atoms/A0X-<categoria>/<id>/` contém obrigatoriamente:

```
atoms/A03-injection/sqli-union-basic/
├── README.md                      # inglês — visão geral, como rodar
├── README.pt-BR.md                # português — mesma visão geral
├── docker-compose.yml             # sobe vulnerable + fixed lado a lado
├── vulnerable/
│   ├── Dockerfile
│   ├── app.py                     # app Flask mínima, vulnerável
│   ├── requirements.txt
│   └── templates/                 # HTML mínimo (omitido em átomos API-only)
│       └── index.html
├── fixed/
│   ├── Dockerfile
│   ├── app.py                     # mesma app, fix aplicado
│   ├── requirements.txt
│   └── templates/
│       └── index.html
├── DIFF.md                        # inglês — diff comentado linha a linha
├── DIFF.pt-BR.md                  # português — mesmo diff
├── WALKTHROUGH.md                 # inglês — trilha Burp (principal) + browser (opcional)
├── WALKTHROUGH.pt-BR.md           # português — mesmo walkthrough
└── burp/                          # opcional: requests exportados do Burp
    └── example-request.txt
```

### Portas convencionadas

Cada átomo recebe um número sequencial de implementação (ver `ROADMAP.md`):

- `vulnerable/` expõe em `127.0.0.1:80NN`
- `fixed/` expõe em `127.0.0.1:81NN`

Onde `NN` é o número do átomo na ordem de implementação (átomo 01 → 8001/8101, átomo 15 → 8015/8115).

---

## 6. Convenções de nomenclatura

### IDs de átomo

Formato: `<categoria>-<variante>-<qualificador>` (a pasta pai já diz o A0X, então o ID não repete).

Exemplos:
- `sqli-union-basic` (dentro de `A03-injection/`)
- `sqli-blind-boolean`
- `xss-reflected`
- `ssrf-basic` (dentro de `A10-ssrf/`)
- `idor-numeric-id` (dentro de `A01-broken-access-control/`)
- `jwt-none-alg` (dentro de `A02-cryptographic-failures/`)

Sempre em inglês, sempre kebab-case, sempre descritivo. IDs são globalmente únicos no repo — não há dois átomos com o mesmo ID, mesmo em pastas diferentes.

### Commits

Convenção: [Conventional Commits](https://www.conventionalcommits.org/) em inglês.

Exemplos:
- `feat(sqli-union-basic): add vulnerable and fixed versions`
- `docs(xss-reflected): add pt-BR walkthrough`
- `fix(ssrf-basic): correct port binding to 127.0.0.1`

### Branches

- `main`: protegida, só merge via PR.
- `atom/<id>`: branch de trabalho por átomo.

---

## 7. Idioma da documentação

Regras claras para evitar inconsistência:

| Artefato | Idioma |
|---|---|
| Código, comentários no código | Inglês |
| Nomes de arquivos, pastas, variáveis, rotas | Inglês |
| Commit messages | Inglês |
| README raiz do repo | Inglês (`README.md`) + paralelo PT (`README.pt-BR.md`) |
| README de cada átomo | Inglês + paralelo PT |
| WALKTHROUGH e DIFF de cada átomo | Inglês + paralelo PT |
| Issues, PRs, discussões no GitHub | Inglês |
| Este documento (CLAUDE.md) e ROADMAP.md | Português (briefing interno do mantenedor) |

**Termos técnicos não se traduzem** mesmo nos textos em português. Use "SQL injection", "payload", "bypass", "blind", "out-of-band", "sink", "source", "sanitize", etc. O pentester brasileiro precisa aprender o vocabulário em inglês — é o vocabulário do mercado.

**Sincronização:** ao editar uma versão da doc, o Claude Code deve atualizar a contraparte no mesmo commit. Nunca deixar PT e EN dessincronizados.

---

## 8. Segurança — regras obrigatórias

Toda app deste repositório é **intencionalmente vulnerável**. As regras abaixo são inegociáveis:

1. **Bind em `127.0.0.1` por padrão** em todo `docker-compose.yml` e em todo `app.run()`.
2. **Banner de aviso** no topo de todo README e toda página HTML: `⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.`
3. **Sem credenciais reais.** Usuários fake, dados fake, chaves dummy óbvias (`secret = "changeme"`).
4. **Sem código malicioso real.** Payloads de exploit são demonstrativos (alert, leitura de `/etc/passwd` dummy, etc.), nunca payloads destrutivos ou com C2.
5. **Sem dependências com vulns conhecidas não relacionadas ao átomo.** Se o átomo é de SQLi, as outras libs devem estar em versão atual. Não queremos CVE "de brinde".
6. **CI bloqueia merge** se algum container bindar em `0.0.0.0` (linter dedicado em `.github/workflows/`).

---

## 9. Roadmap e ordem de implementação

O plano ordenado completo, com fases e checklist, vive no arquivo [`ROADMAP.md`](./ROADMAP.md).

**Resumo:** ~38 átomos planejados, organizados em 7 fases de 5 átomos cada. A Fase 1 (MVP) cobre as 5 vulnerabilidades mais comuns do dia a dia de um pentester. Cada fase concluída é um marco publicável.

Esta seção do CLAUDE.md não é atualizada a cada átomo concluído — isso é papel do `ROADMAP.md`.

---

## 10. Fluxo de trabalho com Claude Code

### 10.1. O que o Claude Code deve fazer sem perguntar

- Seguir a estrutura de pastas definida na Seção 4.
- Respeitar o template de átomo da Seção 5 (todos os arquivos obrigatórios).
- Criar HTML mínimo conforme Seção 3.3 (≤40 linhas, banner, dica de Burp, sem frameworks).
- Escrever código em inglês, docs na dupla PT+EN.
- Bindar em `127.0.0.1` em todo compose.
- Manter PT e EN das docs sincronizadas no mesmo commit.
- Estruturar todo WALKTHROUGH com trilha Burp como principal e trilha browser como secundária.
- Consultar `ROADMAP.md` para confirmar qual é o próximo átomo, quando em dúvida.

### 10.2. O que o Claude Code deve perguntar antes de fazer

- Qual átomo criar, se o mantenedor não especificou e o `ROADMAP.md` tem mais de um "próximo" possível.
- Se há dúvida sobre a *forma* da vulnerabilidade no átomo (ex: SQLi via GET ou POST? autenticado ou não?).
- Se um átomo deve ser API-only (sem HTML), quando a decisão não for óbvia pela categoria.
- Quando for alterar o CLAUDE.md, o ROADMAP.md, o Makefile, ou o wrapper `./atom`.

### 10.3. O que o Claude Code NÃO deve fazer

- Criar átomos que misturam duas vulnerabilidades.
- Inventar variantes não listadas no roadmap sem discussão.
- Traduzir termos técnicos no texto em português.
- Adicionar dependência pesada (frameworks de front-end, ORMs, filas) a um átomo que não precisa.
- Adicionar CSS elaborado, JS não essencial, ou qualquer framework de UI no HTML dos átomos.
- Tornar a UI o meio principal de exploração no walkthrough — a trilha principal é SEMPRE Burp.
- Assumir que o exploit funciona. Todo átomo deve ser validado manualmente pelo mantenedor via Burp.

### 10.4. Formato de entrega de um novo átomo

Quando o Claude Code gera um átomo novo, a entrega inclui:

1. Todos os arquivos obrigatórios da Seção 5.
2. Um comando único para o mantenedor validar: `./atom up <id>` seguido dos passos exatos do walkthrough.
3. Uma nota ao final listando o que o mantenedor precisa verificar manualmente antes de dar merge.
4. Proposta de marcação no `ROADMAP.md` movendo o átomo de "próximo" para "concluído" (o mantenedor confirma após validar).

---

## 11. Checklist de validação antes de merge

Todo átomo passa por este checklist manual antes de ir pro `main`:

- [ ] `./atom up <id>` sobe sem erro.
- [ ] Versão vulnerável expõe a falha exatamente como descrito no walkthrough.
- [ ] Versão corrigida bloqueia o payload do walkthrough.
- [ ] Exploit reproduzido com sucesso no Burp, request/response capturados.
- [ ] `DIFF.md` reflete fielmente a diferença entre `vulnerable/` e `fixed/`.
- [ ] README do átomo (PT e EN) tem banner de aviso de segurança.
- [ ] HTML (se existir) respeita limite de ~40 linhas e não tem frameworks.
- [ ] WALKTHROUGH tem trilha Burp como principal.
- [ ] Todas as portas bindam em `127.0.0.1`.
- [ ] PT e EN estão sincronizados (mesma informação, mesma estrutura).
- [ ] Sem credenciais reais, sem dados sensíveis de clientes.
- [ ] Átomo marcado como concluído em `ROADMAP.md`.

---

## 12. O que NÃO entra no projeto

Para manter o escopo saudável:

- **Vulnerabilidades de infraestrutura pura** (configuração de nginx, kernel, etc.) — foco é AppSec.
- **Técnicas de pós-exploração** (persistência, lateral movement) — fora do escopo.
- **Payloads prontos para copia-e-cola em alvos reais** — os exemplos são didáticos, não armamento.
- **Frameworks de CTF** (pontuação, ranking, bandeira) — este projeto é laboratório, não competição.
- **Tooling de scanner automatizado** — o estudante aprende fazendo à mão.
- **Frontend rico** (React, Vue, etc.) — a UI é contexto, não produto.

---

## 13. Licença e atribuição

- Licença: MIT.
- Atribuição obrigatória se alguém forkar pra material didático.
- Referências acadêmicas e OWASP devidamente creditadas em cada átomo.

---

## 14. Estado deste documento

Este arquivo evolui com o projeto. Toda mudança estrutural (novo padrão, nova convenção, nova regra) é refletida aqui no mesmo PR que a introduz. Se o Claude Code observa conflito entre o que está aqui e o que foi pedido na sessão, ele para e pergunta.

**Última revisão:** dia de criação do repositório.
**Responsável:** mantenedor (Jose Renato).
