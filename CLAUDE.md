# CLAUDE.md — Briefing do Projeto

> Este documento é o ponto de partida para qualquer sessão do Claude Code neste repositório. Leia-o antes de gerar código, estrutura de pastas ou documentação. Mantenha-o atualizado conforme o projeto evolui.

---

## 1. Visão geral

**Nome:** `atomicvulns`

**O que é:** uma coleção de aplicações web *atômicas* — cada uma minúscula, isolada, e focada em **uma única vulnerabilidade** do OWASP Top 10. Cada átomo entrega: a app vulnerável, a versão corrigida, um diff comentado entre as duas, e walkthrough didático do exploit.

**O que NÃO é:** não é um DVWA/Juice Shop concorrente. Apps vulneráveis monolíticas já existem. O diferencial deste projeto é o *atomismo radical*: uma app por falha, rápida de ler, rápida de explorar.

**Público-alvo:** estudantes de pentest e AppSec que já sabem o básico de HTTP e terminal, usam (ou estão aprendendo a usar) Burp Suite, e querem mapear *código causal → request/response → exploit* sem precisar entender uma aplicação inteira primeiro. O tom do material assume alguém que vai aplicar isso na carreira de pentest.

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

**Trilha de exploração.** A trilha primária é sempre Burp Suite (Repeater), com curl como equivalente quando útil. NÃO incluir uma "trilha browser secundária" que apenas reencena o ataque com menos controle — é redundante. Exceção: quando o browser É a demonstração da vulnerabilidade (execução client-side — XSS e afins), o browser faz parte da trilha primária, não de uma secundária.

**Como a divisão funciona nesses átomos client-side:** o Burp **planta e manipula** as requests (a parte que ensina a profissão — controle cru do payload, encoding, Repeater) e o **browser observa a execução** (o `alert` disparando, o cookie chegando no listener). Quando atacante e vítima são partes diferentes (ex.: stored XSS, onde o atacante planta e a vítima dispara), essa divisão de ferramentas espelha o próprio modelo do ataque.

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
└── docs/
    ├── assets/                    # imagens públicas (banner do README, etc.)
    │   └── banner.svg
    └── templates/                 # template de spec pra novos átomos
        └── ATOM-SPEC-TEMPLATE.md
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
├── WALKTHROUGH.md                 # inglês — Burp primário; browser só quando é a prova
├── WALKTHROUGH.pt-BR.md           # português — mesmo walkthrough
└── burp/                          # opcional: requests exportados do Burp
    └── example-request.txt
```

### Portas convencionadas

Cada átomo recebe um número sequencial de implementação (ver `ROADMAP.md`):

- `vulnerable/` expõe em `127.0.0.1:80NN`
- `fixed/` expõe em `127.0.0.1:81NN`

Onde `NN` é o número do átomo na ordem de implementação (átomo 01 → 8001/8101, átomo 15 → 8015/8115).

### Padrões didáticos do walkthrough

**Vulns de lógica precisam de um passo "o que a vuln NÃO é".**

Em átomos de injection (SQLi, XSS, command injection), o exploit *é* um payload — a demonstração já carrega o significado. Em vulns de lógica (IDOR, BOLA, mass assignment, race condition, session fixation), o exploit é dado legítimo: trocar um número, reordenar uma chamada, mudar um campo. Isso cria risco do aluno internalizar a forma errada do bug — por exemplo, achar que IDOR é "fingir ser outro usuário" em vez de "ausência de check de autorização".

A solução: incluir um passo no walkthrough que isole a causa real, frequentemente demonstrando o que a vuln *não é*. Exemplo do átomo `idor-numeric-id`: depois do exploit padrão (mudar `/notes/1` pra `/notes/2`), o walkthrough mantém o path em `/notes/1` mas muda `X-User-ID` de `1` pra `2` — a resposta continua sendo a nota da Alice. Prova que IDOR não é "fingir ser outro user", é ausência total de check.

Esse passo de contraste é obrigatório em todo átomo onde o exploit possa ser confundido com um conceito vizinho.

O walkthrough termina onde a falha foi mostrada e o fix explicado. Não inclua seção de exercícios ou variações adicionais — esse papel cabe à PortSwigger Web Security Academy (referenciada no Theory primer e na seção "Recommended approach" dos READMEs raiz).

**Abertura direta, sem encenação.** O WALKTHROUGH entra direto na mecânica da vulnerabilidade — a primeira frase situa a feature e a falha, não um personagem. Nada de preâmbulo de encenação ("você é o pentester, trabalhando sozinho" e afins): o aluno já sabe que é ele operando.

**Defina todo termo técnico não-óbvio na primeira ocorrência.** O átomo é escrito pra quem ainda não conhece a vuln. Na primeira vez que uma sigla ou termo novo aparece, dê a expansão ali mesmo (ex.: "DTD (Document Type Definition)"). Termos de mercado que o pentester aprende em inglês seguem em inglês (payload, sink, source) — mas ganham definição na estreia quando não forem óbvios.

**Situe a vuln na categoria OWASP Top 10 atual (2021), sem arqueologia.** Nomeie a categoria vigente (ex.: "A05 — Security Misconfiguration") quando ela ancora a lição. NÃO relate em que número a categoria caía em edições antigas ("era A4 em 2017" e afins) — é ruído histórico que não ajuda o aluno a explorar a falha.

### Referências cross-átomo

Cada átomo é uma unidade auto-contida. Pode referenciar outros átomos por nome ou número, mas APENAS átomos já publicados em `atoms/` no momento da escrita.

NÃO referencie átomos planejados mas ainda não-publicados, mesmo que estejam no ROADMAP. Foreshadowing pedagógico do tipo "o próximo átomo vai mostrar X" ou "o átomo Y explora outra forma disso" cria expectativa de timeline e link em potencial quebrado se o roadmap evoluir.

Quando a tentação for citar uma vuln ou variante que ainda não virou átomo, prefira:

- **Generalizar a lição.** Em vez de "o átomo `xss-dom` vai mostrar que esse payload falha lá", escreva "em DOM-based XSS — onde o sink está em JavaScript pós-load — esse mesmo payload falha". A lição fica completa, ancorada no conceito, não no átomo.
- **Linkar a PortSwigger Academy.** Se a variante já tem página na Academy, é o lugar certo pra mandar o aluno aprofundar.
- **Realocar pro `ROADMAP.md`.** Foreshadowing genuíno de "o projeto vai cobrir X" mora no ROADMAP, não no átomo.

Referências a átomos JÁ PUBLICADOS são bem-vindas — contraste explícito ("diferente do `idor-numeric-id`, aqui o sink é...") ancora a lição em algo que o aluno consegue abrir e validar imediatamente.

### Theory primer obrigatório

Todo átomo DEVE incluir, no início do `README.md` e `README.pt-BR.md` do átomo (logo após o título e a descrição de uma linha, ANTES da seção "How to run" / "Como rodar"), um bloco de Theory primer linkando pra página específica da vulnerabilidade na PortSwigger Web Security Academy.

Formato em `README.md`:

```markdown
> **Theory primer:** Read [PortSwigger: <Nome da vuln>](<URL exata>)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato em `README.pt-BR.md`:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: <Nome da vuln>](<URL exata>)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

A URL DEVE ser a página de introdução conceitual da vuln na Academy (tipicamente a que começa com "What is X?"), NÃO a página de listagem de labs. Ao gerar um átomo novo, o Claude Code deve buscar a URL real e nunca inventar — se não conseguir verificar, deve perguntar ao mantenedor.

Para o "<Nome da vuln>" no link, use a forma apresentada pela própria PortSwigger na página (ex.: "SQL injection", "Reflected cross-site scripting", "IDOR", "Server-side request forgery (SSRF)"). NÃO traduza pra PT mesmo no README PT — a página linkada é em inglês, e manter o nome em inglês evita a confusão de "liguei no link e a página tem outro nome".

---

## 6. Convenções de nomenclatura

### IDs de átomo

Formato: `<categoria>-<variante>-<qualificador>` (a pasta pai já diz o A0X, então o ID não repete).

Exemplos:
- `sqli-union-basic` (dentro de `A03-injection/`)
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

**Título h1 do `README.pt-BR.md` é idêntico ao do `README.md`** (sem tradução). O resto do documento — tagline/descrição, parágrafos, headers de seção — é traduzido normalmente. Razão: o nome canônico de uma classe de vulnerabilidade circula em inglês na comunidade de segurança ("Reflected Cross-Site Scripting", "Server-Side Request Forgery"); preservar no título evita ambiguidade terminológica, mantém consistência com IDs de átomo (que já são em inglês) e elimina a tentação de inventar uma tradução por átomo.

**Sincronização:** ao editar uma versão da doc, o Claude Code deve atualizar a contraparte no mesmo commit. Nunca deixar PT e EN dessincronizados.

---

## 8. Segurança — regras obrigatórias

Toda app deste repositório é **intencionalmente vulnerável**. As regras abaixo são inegociáveis:

1. **Bind em `127.0.0.1` por padrão** em todo `docker-compose.yml` e em todo `app.run()`.
2. **Banner de aviso** no topo de todo README e toda página HTML: `⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.`
3. **Sem credenciais reais.** Usuários fake, dados fake, chaves dummy óbvias (`secret = "changeme"`).
4. **Sem código malicioso real.** Payloads de exploit são demonstrativos (alert, leitura de `/etc/passwd` dummy, etc.), nunca payloads destrutivos ou com C2.
5. **Sem dependências com vulns conhecidas não relacionadas ao átomo.** Se o átomo é de SQLi, as outras libs devem estar em versão atual. Não queremos CVE "de brinde".
6. **Bind em `127.0.0.1` é convenção obrigatória do projeto**, validada manualmente em revisão de PR. Automatizar essa checagem via CI está previsto no `ROADMAP.md` (seção "Infraestrutura e governança").
7. **Atualizações de dependência são manuais.** Dependabot está desativado. A revisão acontece ao fim de cada release de fase, com smoke test dos átomos antes do merge. Razão: algumas dependências têm versões intencionalmente pinadas porque o comportamento dessas versões É o objeto de estudo do átomo (ex: PyJWT no `jwt-none-alg`); atualizações automatizadas quebrariam o invariante educacional do projeto.

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
- Estruturar todo WALKTHROUGH com a trilha Burp primária; o browser faz parte da trilha principal SÓ em classes client-side (XSS e afins), onde a prova exige JavaScript executando.
- Consultar `ROADMAP.md` para confirmar qual é o próximo átomo, quando em dúvida.
- Ler o átomo de referência e os átomos concluídos da mesma categoria antes de gerar código novo (ver 10.5).

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

### 10.5. Leitura obrigatória de referência antes de gerar código novo

Antes de criar qualquer átomo, o Claude Code DEVE ler, nesta ordem:

1. **Este `CLAUDE.md` na íntegra** — regras e convenções.
2. **`ROADMAP.md`** — confirmar qual é o próximo átomo e suas dependências conceituais.
3. **`atoms/A03-injection/sqli-union-basic/` — átomo de referência canônico.** Define o padrão real (não só o teórico) de:
   - Estilo de código Flask + Jinja2 + SQLite
   - Tamanho e estrutura do `app.py` vulnerável e corrigido
   - Forma do `docker-compose.yml` e dos `Dockerfile`
   - Profundidade, tom e formato do `WALKTHROUGH.md` (trilha Burp primária; browser só quando é a prova)
   - Granularidade e comentários do `DIFF.md`
   - Estilo dos READMEs de átomo (PT e EN)
4. **Átomos já concluídos da mesma categoria OWASP**, se existirem. Ex.: ao criar uma nova variante de XSS, ler antes os átomos XSS já publicados; ao criar uma segunda variante de SQLi, ler antes `sqli-union-basic`.

O objetivo **não é copiar** — é manter consistência de estilo, densidade didática e estrutura entre átomos. Convenções escritas capturam a forma; a referência captura o tom.

Se o Claude Code detectar conflito entre o código de um átomo existente e este `CLAUDE.md`, ele **para e pergunta** qual é a fonte da verdade. Regra geral: o `CLAUDE.md` vence, mas o refinamento pode justificar atualizar este documento.

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

## Memória de projeto

Gravar memória de projeto (arquivos em `.claude/projects/.../memory/`, incluindo o `MEMORY.md`) é decisão do mantenedor, não do Claude Code — mesma regra de "o Claude Code recomenda, o mantenedor decide" que vale para commits e merges.

- O Claude Code **nunca grava nem edita memória por conta própria**, nem mesmo um lembrete factual. Se achar que algo vale registrar, **propõe**: descreve a memória (nome + conteúdo curto) e espera o "pode gravar" do mantenedor.
- Isso vale para toda memória — fato pontual, débito, regra de método, qualquer uma. Não há categoria que o Claude Code possa gravar sem pedir; a decisão é sempre do mantenedor.
- Uma vez aprovada, a memória segue as convenções do repo (concisa, factual, verdadeira, de escopo estreito).