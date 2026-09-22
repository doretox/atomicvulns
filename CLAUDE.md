# CLAUDE.md — Briefing do Projeto

> Este documento é o ponto de partida para qualquer sessão do Claude Code neste repositório. Leia-o antes de gerar código, estrutura de pastas ou documentação. Mantenha-o atualizado conforme o projeto evolui.

---

## 1. Visão geral

**Nome:** `atomicvulns`

**O que é:** uma coleção de aplicações web *atômicas* — cada uma minúscula, isolada, e focada em **uma única vulnerabilidade** do OWASP Top 10. Cada átomo entrega: a app vulnerável, a versão corrigida, um diff comentado entre as duas, e walkthrough didático do exploit.

**O que NÃO é:** não é um DVWA/Juice Shop concorrente. Apps vulneráveis monolíticas já existem. O diferencial deste projeto é o *atomismo radical*: uma app por falha, rápida de ler, rápida de explorar.

**Público-alvo:** estudantes de pentest e AppSec que já sabem o básico de HTTP e terminal, usam (ou estão aprendendo a usar) Burp Suite, e querem mapear *código causal → request/response → exploit* sem precisar entender uma aplicação inteira primeiro. O tom do material assume alguém que vai aplicar isso na carreira de pentest.

**Mantenedor:** projeto solo, médio/longo prazo.

**Arquivos complementares:** ver [`atoms/web/ROADMAP.md`](./atoms/web/ROADMAP.md) e [`atoms/api/ROADMAP.md`](./atoms/api/ROADMAP.md) para os planos ordenados de cada série e seus checklists de progresso.

---

## 2. Princípios fundamentais (não negociáveis)

1. **Um átomo = uma vulnerabilidade.** Se precisar de duas, são dois átomos.
2. **Mínimo código possível.** Se o handler vulnerável passa de ~30 linhas, provavelmente está fazendo coisa demais. O objetivo é que o estudante *leia e entenda rápido*, sem precisar navegar por múltiplos arquivos ou camadas de abstração.
3. **Vulnerável e corrigido vivem lado a lado.** Todo átomo tem uma pasta `vulnerable/` e uma `fixed/` com o mesmo endpoint, mesma feature — só o fix muda.
4. **Walkthrough reproduzível.** Todo exploit documentado deve funcionar *exatamente* como descrito. O mantenedor valida manualmente via Burp antes de qualquer merge.
5. **Segurança do estudante vem antes de tudo.** App intencionalmente vulnerável NUNCA bindа em `0.0.0.0` por padrão. Sempre `127.0.0.1`. Sempre com aviso no README.
6. **Didático > realista.** Quando houver conflito entre "mais fiel ao mundo real" e "mais claro pro iniciante", vence o claro.
7. **Burp é a ferramenta principal, UI é só contexto.** A exploração acontece no Burp; a UI existe pra o aluno entender a feature simulada antes de ir pro Repeater.

---

## 3. Stack técnica

### 3.1. A stack é lei por série

A stack não é escolha por átomo — é **lei da série**. Cada série adota a stack que serve à sua classe de vulnerabilidades, e isso é uma decisão de arquitetura do mantenedor, tomada quando a série nasce, não um gosto do átomo. Dentro de uma série, usa-se a stack dela.

Hoje o repo tem duas séries, cada uma com a sua:

- **Série web** (`atoms/web/`): **Python 3.11+ com Flask.** Escolha por legibilidade didática, cobertura ampla do OWASP Top 10, e stdlib rico (sqlite3, subprocess, pickle — todos úteis pra ilustrar classes de falha).
- **Série API** (`atoms/api/`): **TypeScript / Express / `tsx`**, containerizado — `tsx` é o entrypoint que roda o átomo dentro do container. Escolha pela stack idiomática de APIs modernas e pelo backbone da série ser o OWASP API Security Top 10.

A stack de uma série futura é decisão de arquitetura — definida ao criar a série, não reaberta átomo a átomo.

### 3.2. Exceção: linguagem idiomática à vulnerabilidade

A stack é lei da série, mas há uma única exceção — e ela vale **dentro de qualquer série**: quando a vulnerabilidade é idiomática de outra linguagem e perde o sentido pedagógico na stack da série, o átomo usa a linguagem da falha. É exceção **por-vuln, não por-preferência**.

O caso canônico é a série web abrindo mão de Python por Node.js + Express quando a falha só existe no ecossistema JavaScript:

- Prototype pollution
- Alguns casos específicos de NoSQL injection com MongoDB nativo
- Deserialization em Node (quando o objetivo é mostrar o ecossistema JS)

Nenhuma outra exceção sem discussão explícita. A regra existe pra não virar zoológico poliglota — não pra reabrir a stack ao gosto do átomo.

### 3.3. Rendering e interação com a aplicação

**Escopo desta seção:** as regras de rendering abaixo governam a **série web**, onde cada átomo tem uma UI mínima só pra dar contexto à feature. A **série API** (`atoms/api/`) é **API-only por natureza** — respostas JSON, sem Jinja, sem `templates/`, sem browser track —, exatamente como a subseção "Átomos naturalmente de API" descreve abaixo; a diferença é que na série API isso é a regra, não a exceção. Não se inventa UI pra átomo de API.

**Filosofia:** o pentester trabalha no Burp. A UI existe apenas para *contextualizar* a feature simulada — nunca para ser o meio de exploração. O aluno abre no browser uma vez pra entender "o que essa app faz", e dali em diante migra pro Burp Repeater/Intruder como faria num pentest real.

**Padrão da série web: HTML mínimo server-rendered com Jinja2.**

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

Átomos da série API tipicamente usam um store em memória (como o `bola-rest`), recorrendo a um banco só quando a vuln exige.

### 3.5. Containerização

Vale igual para as duas séries — o mecanismo de container é agnóstico de stack:

- **Docker Compose por átomo.** Cada átomo — web ou API — tem seu próprio `docker-compose.yml`.
- **Bind obrigatório em `127.0.0.1`** nas portas publicadas.
- **Wrapper simples na raiz** (`./atom` script em Bash ou Python) para UX: `./atom up <id>`, `./atom down <id>`, `./atom list`, `./atom doctor`. O `./atom` descobre as duas séries sob `atoms/` e mantém os IDs de átomo únicos no repo inteiro.

### 3.6. Dependências mínimas

Cada átomo deve rodar com o menor conjunto de dependências possível. Se o átomo é de SSRF, não precisa ter ORM. Se é de SQLi, não precisa ter Celery. **Regra: só inclua a lib se ela serve à demonstração da falha ou ao fix.**

**Herança de toolchain na série API.** Um átomo novo da série API herda a imagem base e as versões de dependência do átomo de referência da série (§10.5) — a fonte da verdade é executável: leia o `package.json` e o `Dockerfile` dele, não uma tabela nesta doc. Versão sempre **exata** (nunca `^`, `~`, `x`; nunca `latest` em tag de imagem). Subir toolchain é decisão de **corte de release**, coordenada na série inteira — não se sobe versão no meio de um átomo. Se um átomo precisar divergir do toolchain de referência, a divergência e o motivo ficam registrados **na spec daquele átomo**, não aqui.

---

## 4. Estrutura do repositório

O repo tem **duas séries** sob `atoms/`, cada uma organizada pela sua própria edição do OWASP Top 10 e com o seu `ROADMAP.md` dentro. A **série web** segue a OWASP Top 10 2021 (categorias `A01`…`A10`); a **série API** segue a OWASP API Security Top 10 2023 (categorias `API1`…`API10`). Em ambas, cada categoria é uma pasta e os átomos moram dentro.

```
atomicvulns/
├── CLAUDE.md                      # este arquivo
├── README.md                      # inglês, público
├── README.pt-BR.md                # português, público BR
├── LICENSE
├── atom                           # wrapper CLI (executável) — descobre as duas séries
├── Makefile                       # atalhos equivalentes ao wrapper
├── atoms/
│   ├── web/                       # série web — Python 3.11+/Flask
│   │   ├── ROADMAP.md             # plano ordenado da série web
│   │   ├── A01-broken-access-control/
│   │   │   ├── idor-numeric-id/
│   │   │   ├── idor-uuid-guessable/
│   │   │   ├── bola-rest/
│   │   │   ├── path-traversal-basic/
│   │   │   ├── csrf-basic/
│   │   │   ├── open-redirect/
│   │   │   └── mass-assignment/
│   │   ├── A02-cryptographic-failures/
│   │   │   ├── crypto-weak-hash/
│   │   │   ├── crypto-ecb-mode/
│   │   │   ├── jwt-none-alg/
│   │   │   ├── jwt-weak-secret/
│   │   │   └── jwt-key-confusion/
│   │   ├── A03-injection/
│   │   │   ├── sqli-union-basic/
│   │   │   ├── sqli-blind-boolean/
│   │   │   ├── sqli-blind-time/
│   │   │   ├── sqli-second-order/
│   │   │   ├── nosql-injection-mongo/
│   │   │   ├── command-injection-basic/
│   │   │   ├── ldap-injection/
│   │   │   ├── xss-reflected/
│   │   │   ├── xss-stored/
│   │   │   ├── xss-dom/
│   │   │   └── ssti-jinja/
│   │   ├── A04-insecure-design/
│   │   │   └── race-condition-basic/
│   │   ├── A05-security-misconfiguration/
│   │   │   ├── debug-enabled/
│   │   │   ├── cors-wildcard/
│   │   │   ├── xxe-basic/
│   │   │   └── xxe-blind-oob/
│   │   ├── A06-vulnerable-components/
│   │   │   └── cve-demo/
│   │   ├── A07-auth-failures/
│   │   │   ├── weak-password-reset/
│   │   │   └── session-fixation/
│   │   ├── A08-data-integrity-failures/
│   │   │   ├── deserialization-pickle/
│   │   │   ├── deserialization-node/
│   │   │   └── prototype-pollution/
│   │   ├── A09-logging-failures/
│   │   │   └── logging-failures-demo/
│   │   └── A10-ssrf/
│   │       ├── ssrf-basic/
│   │       ├── ssrf-blind-oob/
│   │       └── ssrf-cloud-metadata/
│   └── api/                       # série API — TypeScript/Express/tsx
│       ├── ROADMAP.md             # plano ordenado da série API
│       ├── API1-broken-object-level-authz/
│       │   └── <atom-id>/         # ex.: bola-sequential-id — ver api/ROADMAP.md
│       ├── API2-broken-authentication/
│       └── ...                    # API3…API10 (OWASP API Security Top 10 2023)
└── docs/
    ├── assets/                    # imagens públicas (banner do README, etc.)
    │   └── banner.svg
    ├── specs/                     # specs de átomo, por série
    │   ├── web/                   # specs da série web
    │   └── api/                   # specs da série API
    └── templates/                 # templates de spec, por série
        ├── ATOM-SPEC-TEMPLATE-WEB.md
        └── ATOM-SPEC-TEMPLATE-API.md
```

**Nota sobre categorização:** a série web segue a OWASP Top 10 2021 e a série API a OWASP API Security Top 10 2023 — a edição estável mais atual de cada. Se surgir uma nova edição durante o projeto, revisamos o mapeamento sem reescrever os átomos — só movemos as pastas.

---

## 5. Anatomia de um átomo

Todo átomo é um par de gêmeos `vulnerable/` + `fixed/` lado a lado, mais a documentação bilíngue (README, DIFF, WALKTHROUGH em EN e PT) e o `docker-compose.yml` que sobe os dois. **A forma é a mesma nas duas séries** — os gêmeos, o diff limpo entre eles, os docs, o compose. O que muda é o *conteúdo* de `vulnerable/`/`fixed/`, que segue a stack da série.

**Série web (Python/Flask)** — `atoms/web/A0X-<categoria>/<id>/`:

```
atoms/web/A03-injection/sqli-union-basic/
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

**Série API (TypeScript/Express/tsx)** — `atoms/api/APIX-<categoria>/<id>/`: mesma forma, mas `vulnerable/` e `fixed/` são build-contexts Docker self-contained em TypeScript (cada um com seu `package.json` e `tsconfig.json`, sem módulo compartilhado) e **sem `templates/`**, porque a série é API-only:

```
atoms/api/API1-broken-object-level-authz/bola-sequential-id/
├── README.md                      # inglês — visão geral, como rodar
├── README.pt-BR.md                # português — mesma visão geral
├── docker-compose.yml             # sobe vulnerable + fixed lado a lado
├── vulnerable/
│   ├── Dockerfile
│   ├── app.ts                     # app Express mínima, vulnerável
│   ├── package.json
│   └── tsconfig.json
├── fixed/
│   ├── Dockerfile
│   ├── app.ts                     # mesma app, fix aplicado
│   ├── package.json
│   └── tsconfig.json
├── DIFF.md                        # inglês — diff comentado linha a linha
├── DIFF.pt-BR.md                  # português — mesmo diff
├── WALKTHROUGH.md                 # Burp/curl — API-only, sem browser track
├── WALKTHROUGH.pt-BR.md           # português — mesmo walkthrough
└── burp/                          # opcional: requests exportados do Burp
    └── example-request.txt
```

### Portas convencionadas

Cada átomo recebe um número sequencial de implementação **dentro da sua série** (ver o `ROADMAP.md` da série). Cada série tem um **range de portas dedicado**, pra web e API rodarem lado a lado sem colisão:

- **Série web:** `vulnerable/` em `127.0.0.1:80NN`, `fixed/` em `127.0.0.1:81NN`.
- **Série API:** `vulnerable/` em `127.0.0.1:82NN`, `fixed/` em `127.0.0.1:83NN`.

Onde `NN` é o número do átomo na ordem de implementação da **sua** série (web átomo 01 → 8001/8101; API átomo 01 → 8201/8301). Cada série conta do próprio 01 — não se renumera nada.

### Padrões didáticos do walkthrough

**Vulns de lógica precisam de um passo "o que a vuln NÃO é".**

Em átomos de injection (SQLi, XSS, command injection), o exploit *é* um payload — a demonstração já carrega o significado. Em vulns de lógica (IDOR, BOLA, mass assignment, race condition, session fixation), o exploit é dado legítimo: trocar um número, reordenar uma chamada, mudar um campo. Isso cria risco do aluno internalizar a forma errada do bug — por exemplo, achar que IDOR é "fingir ser outro usuário" em vez de "ausência de check de autorização".

A solução: incluir um passo no walkthrough que isole a causa real, frequentemente demonstrando o que a vuln *não é*. Exemplo do átomo `idor-numeric-id`: depois do exploit padrão (mudar `/notes/1` pra `/notes/2`), o walkthrough mantém o path em `/notes/1` mas muda `X-User-ID` de `1` pra `2` — a resposta continua sendo a nota da Alice. Prova que IDOR não é "fingir ser outro user", é ausência total de check.

Esse passo de contraste é obrigatório em todo átomo onde o exploit possa ser confundido com um conceito vizinho.

O walkthrough termina onde a falha foi mostrada e o fix explicado. Não inclua seção de exercícios ou variações adicionais — esse papel cabe à PortSwigger Web Security Academy (referenciada no Theory primer e na seção "Recommended approach" dos READMEs raiz).

**Abertura direta, sem encenação.** O WALKTHROUGH entra direto na mecânica da vulnerabilidade — a primeira frase situa a feature e a falha, não um personagem. Nada de preâmbulo de encenação ("você é o pentester, trabalhando sozinho" e afins): o aluno já sabe que é ele operando.

**Elenco consistente na série API.** A série API reusa o mesmo elenco entre átomos, pra o aluno não reaprender personagem a cada lab: `dana` é a atacante / o usuário que você controla, e `alice` é a vítima principal; vítimas adicionais entram conforme o átomo precisar. `dana` é **feminino** — nos docs PT a concordância referente a ela é feminina (`a atacante`, `você mesma`, `dela`); o masculino genérico (`o dono`, `o usuário`) continua certo quando descreve o **papel**, não a pessoa.

**Defina todo termo técnico não-óbvio na primeira ocorrência.** O átomo é escrito pra quem ainda não conhece a vuln. Na primeira vez que uma sigla ou termo novo aparece, dê a expansão ali mesmo (ex.: "DTD (Document Type Definition)"). Termos de mercado que o pentester aprende em inglês seguem em inglês (payload, sink, source) — mas ganham definição na estreia quando não forem óbvios.

**Situe a vuln na Top 10 vigente da sua série, sem arqueologia.** Nomeie a categoria da edição atual do Top 10 da série quando ela ancora a lição — na série web, OWASP Top 10 2021, categorias A0X (ex.: "A05 — Security Misconfiguration"); na série API, OWASP API Security Top 10 2023, categorias APIX (ex.: "API8 — Security Misconfiguration"). NÃO relate em que número a categoria caía em edições antigas ("era A4 em 2017" e afins) — é ruído histórico que não ajuda o aluno a explorar a falha.

**O título nomeia a classe da vulnerabilidade, não a tecnologia.** O H1 usa o nome canônico da *classe* (ex.: "Server-side template injection (SSTI)"), não o stack onde ela foi demonstrada ("...em Jinja2"). O motor/lib/framework é detalhe de implementação: aparece no corpo do walkthrough e do DIFF, onde o mecanismo é explicado — nunca no título. Razão: o título deve ser reconhecível e transferível para qualquer pentester procurando a classe, independente da stack. (O *slug* do átomo pode qualificar a variante/motor — `ssti-jinja` — como todo slug do repo: `sqli-union-basic`, `jwt-none-alg`.)

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

Formato: `<categoria>-<variante>-<qualificador>` (a pasta pai já diz o código de categoria — A0X na web, APIX na API —, então o ID não repete).

Exemplos:
- `sqli-union-basic` (dentro de `A03-injection/`)
- `xss-reflected`
- `ssrf-basic` (dentro de `A10-ssrf/`)
- `idor-numeric-id` (dentro de `A01-broken-access-control/`)
- `jwt-none-alg` (dentro de `A02-cryptographic-failures/`)

Sempre em inglês, sempre kebab-case, sempre descritivo. IDs são globalmente únicos no repo — não há dois átomos com o mesmo ID, mesmo em pastas diferentes.

### Commits

Mensagens em inglês. Duas formas coexistem, por tipo de mudança:

**Commit que introduz um átomo** (é o subject do squash-merge do PR do átomo):

```
atom <NN>: <id> — <Nome da classe da vuln>
```

O `(#<PR>)` é acrescentado automaticamente pelo GitHub no squash-merge — não o escreva à mão. Ex.: `atom 25: mass-assignment — Mass Assignment (#37)`. O `<NN>` é o número sequencial do átomo (o mesmo das portas); o `<id>` é o slug da pasta; o `<Nome da classe da vuln>` é o nome canônico da classe (o mesmo do h1 do README, sem qualificar a stack).

**Todo o resto** (docs, refactor, fix, chore): [Conventional Commits](https://www.conventionalcommits.org/), com escopo curto. Exemplos:
- `docs(changelog): release v0.5.0`
- `docs(roadmap): mark atom 25 (mass-assignment) done`
- `refactor(walkthrough): drop redundant browser track, Burp-only default`

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

**Headers de seção são traduzidos em TODA doc PT** — `README.pt-BR.md`, `WALKTHROUGH.pt-BR.md` e `DIFF.pt-BR.md`. A única exceção é o h1 do README, coberto pela regra acima. Termos técnicos seguem em inglês DENTRO do header traduzido: `### Passo 1 — Confirmar o injection point`, `## Por que o fix funciona`, `### Baseline — limpo, capturado primeiro`. Sinal de tradução não aplicada: um header de seção byte-idêntico ao do arquivo EN.

**Sincronização:** ao editar uma versão da doc, o Claude Code deve atualizar a contraparte no mesmo commit. Nunca deixar PT e EN dessincronizados.

---

## 8. Segurança — regras obrigatórias

Toda app deste repositório é **intencionalmente vulnerável**. As regras abaixo são inegociáveis:

1. **Bind em `127.0.0.1` por padrão** em todo `docker-compose.yml` e no bind do servidor de cada app (Flask `app.run(...)`, Express `app.listen(...)`).
2. **Banner de aviso** no topo de todo README e toda página HTML: `⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.`
3. **Sem credenciais reais.** Usuários fake, dados fake, chaves dummy óbvias (`secret = "changeme"`).
4. **Sem código malicioso real.** Payloads de exploit são demonstrativos (alert, leitura de `/etc/passwd` dummy, etc.), nunca payloads destrutivos ou com C2.
5. **Sem dependências com vulns conhecidas não relacionadas ao átomo.** Se o átomo é de SQLi, as outras libs devem estar em versão atual. Não queremos CVE "de brinde".
6. **Bind em `127.0.0.1` é convenção obrigatória do projeto**, validada manualmente em revisão de PR. Automatizar essa checagem via CI está previsto no `ROADMAP.md` (seção "Infraestrutura e governança").
7. **Atualizações de dependência são manuais.** Dependabot está desativado. A revisão acontece ao fim de cada release de fase, com smoke test dos átomos antes do merge. Razão: algumas dependências têm versões intencionalmente pinadas porque o comportamento dessas versões É o objeto de estudo do átomo (ex: PyJWT no `jwt-none-alg`); atualizações automatizadas quebrariam o invariante educacional do projeto.

---

## 9. Roadmap e ordem de implementação

O plano ordenado completo da série web, com fases e checklist, vive no arquivo [`atoms/web/ROADMAP.md`](./atoms/web/ROADMAP.md).

**Resumo:** ~38 átomos planejados, organizados em 7 fases de 5 átomos cada. A Fase 1 (MVP) cobre as 5 vulnerabilidades mais comuns do dia a dia de um pentester. Cada fase concluída é um marco publicável.

O plano ordenado da série API vive em [`atoms/api/ROADMAP.md`](./atoms/api/ROADMAP.md).

Esta seção do CLAUDE.md não é atualizada a cada átomo concluído — isso é papel do `ROADMAP.md`.

---

## 10. Fluxo de trabalho com Claude Code

### 10.1. O que o Claude Code deve fazer sem perguntar

- Seguir a estrutura de pastas definida na Seção 4.
- Respeitar o template de átomo da Seção 5 (todos os arquivos obrigatórios).
- Para átomos da série web: criar HTML mínimo conforme Seção 3.3 (≤40 linhas, banner, dica de Burp, sem frameworks).
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
- Adicionar CSS elaborado, JS não essencial, ou qualquer framework de UI no HTML dos átomos da série web.
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
3. **`atoms/web/A03-injection/sqli-union-basic/` — átomo de referência canônico da série web.** (A série API tem o seu próprio átomo de referência de estilo: `atoms/api/API1-broken-object-level-authz/bola-sequential-id/`.) Define o padrão real (não só o teórico) de:
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
- [ ] Nenhum header de seção (`##`/`###`/`####`) do arquivo PT é byte-idêntico ao par EN (o h1 do README é a única exceção).
- [ ] Sem credenciais reais, sem dados sensíveis de clientes.
- [ ] Átomo marcado como concluído em `ROADMAP.md`.
- [ ] O rodapé de links do `CHANGELOG.md` tem uma linha de compare para cada versão, e o `[Unreleased]` aponta da última release cortada até HEAD.

---

## 12. Release de fim de fase

Cada fase concluída do `ROADMAP.md` (os átomos `[x]` da fase em `main`) vira uma release versionada. É trabalho de mantenedor, pós-merge — nenhum átomo individual corta release. O procedimento, em ordem:

1. **Promover o CHANGELOG.** O bloco `## [Unreleased]` (que acumulou as linhas `### Added` dos átomos da fase) vira `## [X.Y.0] - <data>` (data real via `date +%Y-%m-%d`, nunca inventada). Acima das linhas `### Added` — que se movem inalteradas —, escrever um parágrafo-resumo da fase no estilo dos resumos anteriores: o arco da fase e o fio condutor dos átomos, fechando com a frase-padrão "Each atom isolates one flaw with vulnerable/ and fixed/ side by side, Burp-first walkthroughs, and bilingual docs (EN + PT-BR)." Recriar um `## [Unreleased]` vazio no topo.

2. **Atualizar o rodapé de links do CHANGELOG.** Adicionar a linha da nova versão e reapontar o Unreleased — o `[Unreleased]` passa a comparar de `vX.Y.0...HEAD`, e uma linha nova `[X.Y.0]` compara de `<versão anterior>...vX.Y.0`. Cada versão cortada tem a sua linha de `compare`; o `[Unreleased]` aponta sempre da última release até `HEAD`. (É o que o checklist da Seção 11 verifica.)

3. **Merge da promoção do CHANGELOG** como um PR próprio (`docs(changelog): release vX.Y.0`), squash, antes de taggear — a tag tem que apontar pro commit que já contém o CHANGELOG promovido.

4. **Tag anotada.** `git tag -a vX.Y.0 -m "vX.Y.0 — <Nome da fase>"`, apontando pro commit de merge na `main`. Sempre anotada (nunca leve). O push da tag é **explícito** (`git push origin vX.Y.0`) — não vai junto de um push normal.

5. **GitHub release.** `gh release create vX.Y.0 --title "vX.Y — <Nome da fase>" --notes-file <arquivo> --latest`. As notas são **mais ricas que o CHANGELOG**: título da fase, uma seção "New atoms" com um bullet por átomo (id + classe + 1 linha), uma seção "What this phase covers" narrando os arcos, a frase-padrão de fechamento, e um `Full changelog:` com o link de `compare`. Copiar o formato do `gh release view` da release anterior.

**Convenções de nomenclatura, para consistência com o histórico:**
- **Tag:** semver completo — `vX.Y.0` (ex.: `v0.6.0`).
- **Título do release e da tag anotada:** forma de fase — `vX.Y — <Nome da fase>` (ex.: `v0.6 — Rare but Deadly`), não o semver seco.
- **`Full changelog:`** no rodapé das notas: sempre presente.

A revisão manual de dependências (Seção 8, regra 7) acontece aqui, no fim da fase, com smoke test dos átomos antes do merge da release.

---

## 13. O que NÃO entra no projeto

Para manter o escopo saudável:

- **Vulnerabilidades de infraestrutura pura** (configuração de nginx, kernel, etc.) — foco é AppSec.
- **Técnicas de pós-exploração** (persistência, lateral movement) — fora do escopo.
- **Payloads prontos para copia-e-cola em alvos reais** — os exemplos são didáticos, não armamento.
- **Frameworks de CTF** (pontuação, ranking, bandeira) — este projeto é laboratório, não competição.
- **Tooling de scanner automatizado** — o estudante aprende fazendo à mão.
- **Frontend rico** (React, Vue, etc.) — a UI é contexto, não produto.

---

## 14. Licença e atribuição

- Licença: MIT.
- Atribuição obrigatória se alguém forkar pra material didático.
- Referências acadêmicas e OWASP devidamente creditadas em cada átomo.

---

## 15. Estado deste documento

Este arquivo evolui com o projeto. Toda mudança estrutural (novo padrão, nova convenção, nova regra) é refletida aqui no mesmo PR que a introduz. Se o Claude Code observa conflito entre o que está aqui e o que foi pedido na sessão, ele para e pergunta.

**Última revisão:** 2026-09-17.
**Responsável:** mantenedor (Jose Renato).

## Memória de projeto

Gravar memória de projeto (arquivos em `.claude/projects/.../memory/`, incluindo o `MEMORY.md`) é decisão do mantenedor, não do Claude Code — mesma regra de "o Claude Code recomenda, o mantenedor decide" que vale para commits e merges.

- O Claude Code **nunca grava nem edita memória por conta própria**, nem mesmo um lembrete factual. Se achar que algo vale registrar, **propõe**: descreve a memória (nome + conteúdo curto) e espera o "pode gravar" do mantenedor.
- Isso vale para toda memória — fato pontual, débito, regra de método, qualquer uma. Não há categoria que o Claude Code possa gravar sem pedir; a decisão é sempre do mantenedor.
- Uma vez aprovada, a memória segue as convenções do repo (concisa, factual, verdadeira, de escopo estreito).