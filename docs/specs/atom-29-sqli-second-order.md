# Spec — Átomo 29: `sqli-second-order`

> Documento de especificação para o Claude Code implementar o átomo `sqli-second-order` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A03 (Injection)**: a pasta `atoms/A03-injection/` já contém `sqli-union-basic`, `sqli-blind-boolean`, `sqli-blind-time`, `xss-reflected`, `xss-stored`, `command-injection-basic`, `ssti-jinja`, `xss-dom`, `nosql-injection-mongo` e `ldap-injection`. O 29 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo**.
>
> **É SINGLE-CONTAINER — segue o molde dos SQLi irmãos (`sqli-union-basic` 01, `sqli-blind-boolean` 06, `sqli-blind-time` 07).** SQLite é um **arquivo embutido no processo** (não um servidor à parte, como o Mongo do 22 ou o OpenLDAP do 28), então **NÃO há datastore externo**: cada lado (`vulnerable`/`fixed`) é **um container Flask com seu próprio `lab.db` efêmero**, semeado no boot por `init_db()`. O `docker-compose.yml` tem **dois serviços** (vulnerable + fixed), molde exato do 01 — **sem** serviço de datastore, **sem** healthcheck/`depends_on`, **sem** rede nomeada.
>
> **A lição em uma linha:** parametrizar o input no ponto de **ENTRADA** não te protege se você o **desparametriza no ponto de USO**. No **second-order SQL injection**, o payload é **GUARDADO** por um caminho seguro (um cadastro com query parametrizada — nada acontece ali) e **DISPARA depois**, quando um **SEGUNDO fluxo** lê aquele valor de volta do banco e o **concatena cru** numa nova query. O dado que já estava "dentro de casa" é tratado como confiável no segundo uso — e é aí que injeta. A raiz é **CONCATENAR NA 2ª QUERY** um valor não-confiável (todo dado lido do banco é input não-confiável de novo), não "o cadastro foi inseguro". O fix é **parametrizar TAMBÉM o segundo ponto de uso**.
>
> **NÃO existe "Saída B" (ferramenta-que-resiste) aqui** — e o motivo é mais afiado que nos átomos de datastore. A ferramenta de defesa (query parametrizada com placeholder `?` do `sqlite3`) **EXISTE, é idiomática, e o próprio app já a usa em TODO lugar** (cadastro, login, e até na leitura que relê o username). O bug é **especificamente não usá-la na 2ª query** (a `UPDATE`, montada por f-string). Isso reforça a lição: parametrizar na entrada **não** basta — o antipadrão é a concatenação **no ponto de uso**, e o fix é o mesmo placeholder `?` aplicado ali também. **NÃO inventar uma Saída B.**
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha primária Burp; **AQUI a decisão de forma é API-only JSON — justificada** na Nota de planning 3 e em "Renderização"; §3.4 — SQLite embutido, sem datastore externo; §4 — pasta/categoria já existe; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A03 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`**, dados fake, SQLite efêmero, payload benigno; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (o **SQLi de PRIMEIRA ordem**, molde canônico de código Flask+SQLite single-container + estrutura de doc + o mental model "input reescreve a estrutura da query"; o contraste **01 ↔ 29** é o eixo do átomo) e os **`sqli-blind-boolean` (06)** e **`sqli-blind-time` (07)** (voz/estrutura da família SQLi; confirmam o padrão SQLite + parametrização; citáveis).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `app.py`, seed — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A03 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver a política de foreshadow). Justificativa do ROADMAP para este átomo: *"SQLi sofisticado onde o payload é guardado em um ponto e triggado em outro. Exige os SQLis anteriores internalizados."*
>
> **A categoria A03 JÁ EXISTE — o 29 reaproveita a pasta.** `atoms/A03-injection/` já existe e já hospeda os três SQLi (01/06/07), os XSS (×3), command injection, SSTI, o NoSQLi e o LDAP injection. **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A03-injection/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A03-injection/sqli-second-order/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A03 — Injection"**.
>
> **Rótulo A03 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Second-order SQL injection é **A03 — Injection** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria do SQLi de primeira ordem e das outras injections. **NÃO** relatar em que número injection caía em edições antigas — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A03 — Injection.** Explicar **por que** é injection (dado não-confiável cai no parser de SQL, que o trata como **sintaxe** de comando em vez de dado inerte) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar a versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase. **CRÍTICO (FORESHADOW, §5):** o átomo se descreve **isolado**. **NÃO** anunciar versão/release, **NÃO** situar o átomo numa fase (abrir/fechar/ordinal/"penúltimo"), **NÃO** foreshadowar átomos futuros (a posição vive só no `ROADMAP.md`). Esta spec é commitada no repo público, então **a própria spec nasce limpa**: onde precisar situar posição, aponta para o `ROADMAP.md`; nas frases que proíbem foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).

## Nota de planning 3 — convenções ATUAIS: API-only JSON (justificado), Burp-only, abertura seca

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **API-only JSON — DECISÃO DE FORMA (delegada a mim pelo brief; justificada; confirmável na Fase 2).** O `CLAUDE.md` §3.3 põe o HTML mínimo com form como **default**, e a decisão API-only "por átomo" quando a vuln é intrinsecamente de API. Aqui a escolha é **API-only JSON**, e o motivo NÃO é que second-order SQLi "só faz sentido em API" (não é o caso — poderia ser form) — é que **este átomo tem TRÊS fluxos** (registro, login, change-password) **encadeados por sessão** numa **cadeia de múltiplas requests**, o que é **naturalmente API-shaped** (§3.3 lista fluxos de auth/REST multi-step como família API-only, molde do `nosql-injection-mongo` 22 e do `ldap-injection` 28). Justificativa concreta:
>   1. A **prova** é uma **resposta HTTP** (o login-como-admin passando), **não** uma página renderizada — não há execução client-side, então HTML só "contextualizaria", e uma cadeia de 3 fluxos autenticados **não** é uma "feature única pra ver no browser".
>   2. Mantém o átomo **mínimo**: sem 3+ templates Jinja, sem ruído de render — o que importa é a **cadeia request/response no Repeater**.
>   3. Bônus didático: em corpo **JSON** o payload `admin'--` viaja **literal** (`"username": "admin'--"`), **sem** os `%20`/encoding-gymnastics que o `01` precisou ensinar — mantém o foco no *second-order*, não no encoding (que já é lição do `01`).
>   4. Consistente com a convenção recente para átomos de fluxo autenticado (22/28 são API-only JSON).
>   - **O "molde dos irmãos 01/06/07" que o brief pede aplica-se à ESTRUTURA single-container SQLite** (`import sqlite3` + `DB_PATH` + `init_db()` + `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)`), **NÃO** obriga o HTML: a forma de render é delegada e aqui é JSON. **Se o mantenedor preferir forms** por consistência estrita da família SQLi, é um flip localizado (trocar `jsonify` por `render_template` + templates mínimos) — **registrar como confirmável, não bloqueante**.
> - **Burp-only — SEM trilha browser** (`CLAUDE.md` §3.3/§5). O vetor é o **corpo JSON** no Repeater; a prova é a **resposta do login-como-vítima**. **NÃO** há execução client-side (não é a exceção client-side do `xss-dom` 21 — não usar). Trilha 100% Burp (Repeater), `curl` como equivalente.
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa os dois fluxos (um cadastro que grava seguro; um change-password que relê e concatena) e a falha (o valor relido vira sintaxe SQL na 2ª query). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** second-order SQL injection (a.k.a. stored SQL injection), first-order/in-band SQL injection, query parametrizada / placeholder (`?`), sink, source, trust boundary, stacked queries — dar a expansão/definição na estreia.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** ("Second-order SQL injection"), **NÃO** o motor ("...em SQLite"/"...em Flask"). O **slug** (`sqli-second-order`) já qualifica a variante; nenhum "SQLite"/"Flask" no H1. O motor aparece no **corpo**, não no H1.
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem TODOS os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Plantar o payload`). A única exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A03 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — single-container, SQLite embutido, banco EFÊMERO e GRAVÁVEL

> **SQLite embutido, molde do `sqli-union-basic` (01).** Cada lado é **um** container Flask com **seu próprio** `lab.db` — **NÃO** há datastore compartilhado (diferente dos átomos de Mongo/OpenLDAP). O schema + seed vivem em `init_db()` dentro do `app.py` (via `conn.executescript(...)`, molde do 01), guardado por `if os.path.exists(DB_PATH): return`. O `docker-compose.yml` é **dois serviços** (molde exato do 01) — **sem** healthcheck, **sem** `depends_on`, **sem** rede nomeada, **sem** imagem de seed.
>
> **DIFERENÇA operacional relevante vs 01/06/07: o banco é GRAVÁVEL.** Os SQLi irmãos são **read-only** (só `SELECT`). Aqui o `POST /register` faz `INSERT` e o `POST /change-password` faz `UPDATE` — o lab **escreve** no `lab.db`. Consequências a cravar:
> - **Banco EFÊMERO por container** (`CLAUDE.md` §8): o `lab.db` vive no filesystem do container, **sem volume persistente**. Um `./atom down <id> && ./atom up <id>` recria o container ⇒ **re-semeia limpo**. Como o exploit **muta** o banco (a senha do `admin` muda), **re-rodar o ataque do zero exige recriar o container** (ou o baseline "senha original do admin" já não vale). **Cravar isso no WALKTHROUGH** (nota operacional: "pra repetir, derrube e suba o átomo — o banco reseta").
> - **Cada lado tem seu próprio banco** (não compartilham) — então mutar o `vulnerable` **não** afeta o `fixed`. Rodar o ataque nos dois lados é independente.
> - **§8:** dados fake, bind **só** `127.0.0.1`, sem PII, payload benigno (subverte a query, não faz ops destrutivas — ver "Payload-prova").

---

## Identidade

- **ID:** `sqli-second-order`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A03 — Injection**. Pasta `atoms/A03-injection/` (**JÁ EXISTE — o 29 reaproveita**). Confirmado contra o `ROADMAP.md` ("A03 Injection") e o `CLAUDE.md` §4. Em prosa, usar o nome da classe — **"Second-order SQL injection"** — e a categoria — **"A03 — Injection"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A03-injection/sqli-second-order/`
- **Número sequencial:** 29
- **Porta vulnerable:** `127.0.0.1:8029`
- **Porta fixed:** `127.0.0.1:8129`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos.
- **Topologia:** **SINGLE-CONTAINER por lado** — dois serviços (`vulnerable` + `fixed`), cada um com seu `lab.db` efêmero embutido. **Sem** datastore externo. Molde do `sqli-union-basic` (01).
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos** (§5 foreshadow).
- **Branch de trabalho:** `atom/sqli-second-order`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de SQL injection** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/sql-injection`** (a página-classe de SQL injection, que **cobre a seção "Second-order SQL injection"**; título/grafia esperados **"SQL injection"** no texto do link). **A seção de second-order pode ter âncora própria** (candidato a confirmar por fetch: `#second-order-sql-injection` ou similar) — **se a âncora for estável, linkar direto nela**; **se instável, linkar a página-classe** `.../sql-injection`. **NÃO inventar URL — confirmar por fetch na Fase 2.** Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# sqli-second-order — Second-order SQL injection`** — `id` + nome canônico da **classe** em inglês. **SEM** "SQLite"/"Flask" no H1. Grafia canônica exata (maiúsculas de "Second-order SQL injection") **confirmável na Fase 2** casando com o título/seção da página PortSwigger; **preservar o nome em inglês também no README PT**. *(Sinônimo "stored SQL injection" é mencionável no corpo — a própria PortSwigger o registra — mas o H1 segue o slug: "Second-order SQL injection".)*

---

## Classe de vulnerabilidade

**Second-order SQL injection — o payload é plantado por um caminho seguro e detona depois, quando um segundo fluxo relê o dado do banco e o concatena cru.** Um app tem dois fluxos: **(1)** um **cadastro** que grava um `username` no banco por query **parametrizada** — o `username` entra por um placeholder `?`, então gravar um `username` malicioso **não causa dano nenhum ali** (é dado literal na tabela); **(2)** um **segundo fluxo autenticado** (change-password) que **lê o `username` de volta do banco** para o usuário logado e o **concatena cru** (f-string) numa nova query (`UPDATE`). É esse **segundo uso** que injeta: o valor que já estava "dentro de casa" é tratado como confiável, mas **todo dado lido do banco é input não-confiável de novo**. O payload, dormente na tabela desde o cadastro, vira **sintaxe SQL** quando concatenado na 2ª query — reescrevendo **qual linha** o `UPDATE` atinge.

O eixo é o **tempo** e o **ponto de disparo**, não uma classe nova de SQLi: a causa continua sendo **concatenar input não-confiável numa query** (a mesma do `sqli-union-basic` 01). O que muda é que a **entrada** (o cadastro) é **segura** e o **disparo** acontece **depois, noutro fluxo**.

### A lição-coração

> **"Parametrizar o input no ponto de ENTRADA não te protege se você o desparametriza no ponto de USO. No second-order SQL injection, o payload é GUARDADO por um caminho seguro (cadastro com query parametrizada — nada acontece ali) e DISPARA depois, quando um SEGUNDO fluxo LÊ aquele valor do banco e o CONCATENA cru numa nova query. O dado que já estava 'dentro de casa' é tratado como confiável no segundo uso — e é aí que injeta. A raiz é concatenar na 2ª query um valor não-confiável (todo dado lido do banco é input não-confiável de novo), NÃO 'o cadastro foi inseguro'. O fix é parametrizar TAMBÉM o segundo ponto de uso."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH)

- **Os dois tempos.** *Tempo 1 (plantar, inócuo):* o cadastro faz `INSERT ... VALUES (?, ?)` — o `username` vai por placeholder, o driver o trata como **dado**, e um `username` cheio de metacaracteres SQL é gravado **literal**, sem executar nada. *Tempo 2 (detonar, dano):* o change-password relê esse `username` do banco e o **cola** (f-string) na string de um `UPDATE` — agora o valor está **dentro do texto SQL** antes de o motor parsear, então o motor o parseia como **código**.
- **Por que o ponto de entrada parece (e testa como) seguro.** Um teste ingênuo no cadastro — mandar `' OR 1=1--` no `username` e ver o que acontece — **não faz nada**: a resposta é um cadastro normal, o valor entrou literal. O `INSERT` é parametrizado; **não há injection na entrada**. A "bomba" fica **dormindo** na tabela. Um scanner/tester que só olha o fluxo de cadastro **não vê nada**.
- **O `trust boundary` que o app erra.** *Trust boundary* (fronteira de confiança) é a linha entre o que é **input não-confiável** (o que vem de fora) e o que o código trata como **dado interno confiável**. O bug conceitual: o app **reassume confiança** num valor **só porque ele veio do próprio banco** — como se "estar no banco" o tornasse seguro. Mas o valor **entrou** como input do atacante (no cadastro); relê-lo não o "lava". **Toda leitura do banco é input não-confiável de novo** e cruza o trust boundary de volta pra dentro.
- **Como o payload reescreve a 2ª query.** A 2ª query monta `UPDATE users SET password = ? WHERE username = '{uname}'` com `uname` **relido** do banco. Se `uname` for `admin'--`, a concatenação vira `... WHERE username = 'admin'--'`: a aspa fecha o literal cedo, `--` comenta o resto, e o `WHERE` passa a casar `username = 'admin'` — **outra linha**, não a do atacante. O `UPDATE` que devia mexer só na conta do atacante é **redirecionado** para a conta `admin`. (Nota `sqlite3`: é subversão do **WHERE da própria query** — **um único statement** —, **não** stacked query; ver "O ataque" e risco #7.)

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e da nota #2 do DIFF)

**A defesa NÃO é "sanitizar/validar o `username` no cadastro" nem "parametrizei na entrada, tô seguro" — é PARAMETRIZAR a query do SEGUNDO fluxo.** Este é o mal-entendido que o átomo desarma. Duas intuições erradas do aluno experiente:

1. *"Já parametrizei o cadastro, então estou protegido."* — **Não.** Parametrizar na **entrada** protege a query da **entrada**. Não faz **nada** pela query do **ponto de uso** posterior, que concatena o valor relido. A proteção não "viaja" com o dado.
2. *"É só sanitizar/validar o `username` no cadastro (proibir aspas, `--`)."* — **Remédio no lugar errado e frágil.** Bloquear charset na entrada é jogo de gato-e-rato (encodings, campos que legitimamente têm símbolos, outros caminhos que gravam no banco), e não corrige a causa: a **2ª query concatena**. O **fix de causa** é **parametrizar a 2ª query** — aí o valor relido vira **dado literal** no `WHERE`, nunca sintaxe, **não importa** o que ele contém.

### Por que A03 (Injection)

Second-order SQL injection é **A03 — Injection**, a mesma categoria do SQLi de primeira ordem. O eixo de injection é: **dado não-confiável cai num interpretador que o trata como código/estrutura, não como dado inerte.** O interpretador aqui é o **parser de SQL** do SQLite, e o dado (o `username` relido) vira **sintaxe** de comando. A única diferença para o `01` é **quando** o dado cruza pro interpretador: no `01`, na mesma request; aqui, numa request **posterior**, depois de ter dormido no banco. Mesma família, mesma causa (concatenação de input não-confiável numa query), mesmo motor (parser SQL). Situar em **A03 — Injection**, **sem** contar edições antigas.

---

## Contraste com o `sqli-union-basic` (01) — CENTRAL (é a razão de o átomo existir)

O **01** é o **SQLi de primeira ordem** e o contraste que **justifica** o átomo. Os dois são **A03 — Injection**, **SQLi**, **mesmo motor** (SQLite / o mesmo parser SQL) e — o ponto — **MESMO fix** (query parametrizada). O que **DIFERE** e justifica dois átomos é o **TEMPO** e o **ponto de disparo**: no `01`, o payload **entra e explode na MESMA request**, na query daquela request; no `29`, o payload é **PLANTADO** numa request (inócuo — entrada parametrizada) e **DISPARA numa request POSTERIOR e DIFERENTE**, quando o app **relê** o dado do banco e concatena. Cravar no WALKTHROUGH e no DIFF (tabela + prosa).

Enquadramento explícito a cravar: *"primeira ordem = entra e detona no mesmo fluxo; segunda ordem = planta agora, detona depois, noutro fluxo — o ponto de entrada parece seguro (e um teste ingênuo no cadastro passa), mas a bomba estava dormindo no banco."*

| Eixo | SQL injection — 1ª ordem (`01`) | Second-order SQL injection (`29`) |
|---|---|---|
| **Categoria OWASP** | A03 — Injection | A03 — Injection |
| **Ordem** | Primeira (in-band) | Segunda (stored) |
| **Onde o payload entra** | Direto na query do **próprio** fluxo (o parâmetro é concatenado ali mesmo) | **Guardado no banco** por um caminho **parametrizado** (o cadastro) — entra como **dado literal** |
| **Quando dispara** | Na **mesma** request | Numa request **posterior e diferente** (o 2º fluxo relê o valor e concatena) |
| **Por que passa despercebido** | **Não passa** — é óbvio no fluxo (o payload age na hora) | **O ponto de entrada parece e testa como seguro** (o cadastro é parametrizado; um probe ingênuo na entrada não faz nada) — a bomba dorme no banco |
| **Motor / interpretador** | Parser SQL do SQLite | **O mesmo** parser SQL do SQLite |
| **O fix** | Parametrizar a query (bind vars separam comando de dado) | Parametrizar a query **do SEGUNDO uso também** (a leitura do banco é input não-confiável de novo) |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante):** o `01` ensina *"nunca concatene input numa query"*. O aluno pode internalizar isso como *"logo, parametrizei a query que recebe o input e acabou"*. O `29` mostra o **furo** dessa leitura: você parametrizou a **entrada**, mas há uma **segunda** query, num **outro** fluxo, que **relê e concatena** — e essa nunca viu o placeholder. A lição do `01` estava certa mas **incompleta**: *"nunca concatene input não-confiável numa query"* precisa incluir *"e todo dado lido do banco é input não-confiável de novo"*. O `01` é pré-requisito conceitual (a mecânica de aspa/`--` que quebra o literal é a mesma); o `29` estende no eixo tempo/ponto-de-uso.

**"Um átomo = uma vuln" se refere à CAUSA, não ao teto de impacto** (`CLAUDE.md` §2). A causa aqui é **concatenar input não-confiável numa query** (a mesma do `01`); o **objeto de estudo** é o *second-order* — o dado que dorme no banco e o **trust boundary reassumido** no 2º uso. Citar `01` (e, para voz de família, `06`/`07`) à vontade — todos publicados; o aluno abre e valida imediatamente.

---

## Flavor — cadastro seguro + segundo fluxo que relê o username (`POST /register` → `POST /login` → `POST /change-password`) — TRAVADO

Um app com **dois fluxos** encadeados por um login mínimo:

1. **REGISTRO (`POST /register`, TRAVADO como parametrizado).** Grava um novo usuário: `INSERT INTO users (username, password) VALUES (?, ?)` — o `username` entra por **placeholder `?`**. Gravar um `username` malicioso **NÃO causa dano nenhum aqui** (isto é **essencial e travado** — se o cadastro também concatenasse, seria 1ª ordem e o átomo perderia a razão de existir). É o **tempo 1** (plantar).
2. **LOGIN (`POST /login`, higiene — parametrizado nos DOIS lados).** Autentica: `SELECT id FROM users WHERE username = ? AND password = ?` — **parametrizado**, **não** é a superfície injetável. Serve para **(a)** dar o estado de sessão que o 2º fluxo exige e **(b)** ser o **mecanismo de prova** (logar como a vítima com a senha nova). *(Contraste didático citável: nos irmãos `06`/`07`, o `/login` **era** o SQLi de 1ª ordem; aqui ele é **higiene parametrizada** — um probe de `' OR 1=1--` no login/cadastro deste átomo **não acha nada**. Reforça "o ponto de entrada testa como seguro".)*
3. **SEGUNDO FLUXO AUTENTICADO (`POST /change-password`, a ÚNICA superfície injetável).** Para o usuário **logado**, **relê o `username` do banco** (`SELECT username FROM users WHERE id = ?` — leitura parametrizada) e monta a 2ª query **concatenando** esse valor relido: `UPDATE users SET password = ? WHERE username = '{uname}'`. O `new_password` (input **fresco** desta 2ª request) entra **parametrizado** (`?`) — **só o `uname` relido é concatenado**. É o **tempo 2** (detonar).

**Superfície injetável = UMA só:** a concatenação do `uname` **relido** no `UPDATE` do `/change-password`. `POST /register`, `POST /login` e a **leitura** que relê o username são **todos parametrizados** (higiene, **idêntica nos dois lados**). `GET /` é só o banner.

- **API-only JSON** (Nota de planning 3): corpos e respostas em `application/json` via `jsonify`. Sem HTML, sem `templates/`, sem browser.
- **Detalhe TRAVADO essencial:** que o `new_password` (input fresco) seja **parametrizado** enquanto o `uname` (relido) é **concatenado**, no **mesmo** `UPDATE`, é **deliberado e central** — prova que o perigo **não é input fresco** (esse está tratado), é o **valor relido do banco** tratado como confiável. Cravar isso no DIFF e no WALKTHROUGH.

### Estado/sessão — mínimo, higiene idêntica nos dois lados (CANDIDATO; CONFIRME NA FASE 2)

O 2º fluxo é "autenticado" — precisa de um mínimo de estado pra saber **qual usuário é**. O andaime de sessão é **higiene, ortogonal à vuln, e deve ser IDÊNTICO nos dois lados**. **Requisito duro (pra não virar 2ª vuln):** o estado **liga o fluxo à identidade do PRÓPRIO usuário logado** — o `/change-password` **NÃO** aceita um `id`/`username`-alvo vindo da request (isso seria um **IDOR/auth-bypass acidental**, uma 2ª vuln). O atacante age sobre **seu próprio** `username` relido — é o **payload no próprio username dele** que faz o `UPDATE` escapar pra outra linha, não a escolha de um alvo.

- **Candidato primário (recomendado): sessão assinada do Flask (cookie de sessão).** `POST /login` faz `session["uid"] = row["id"]`; `POST /change-password` lê `uid = session.get("uid")` (401 se ausente) e relê o username por esse `uid`. **Tamper-proof** (assinado pela `SECRET_KEY`) ⇒ **sem IDOR** (o cliente não escolhe de quem é o `uid`). Mínimo (~3 linhas), **idêntico** nos dois lados, **zero dependência extra** (sessão é nativa do Flask). No Burp: captura-se o `Set-Cookie` do login e leva-se o `Cookie` para a request de change-password no Repeater — padrão e realista.
  - **`SECRET_KEY` é dummy óbvio** (`changeme`, `CLAUDE.md` §8.3) e **orthogonal higiene** (só assina o cookie de sessão; **idêntica nos dois lados**; **não** é o objeto de estudo — análogo às notas "hashing/design é ortogonal" dos irmãos de datastore). **Não** modelar segurança de sessão aqui.
- **Fallback (se o cookie atrapalhar a didática no Repeater):** um **token opaco** devolvido pelo login e mapeado server-side (dict em memória) para o `uid`. Mais código (armazém de token) e estado que reseta no restart — só se o cookie incomodar. **NÃO** usar um token que seja o `id` cru/adivinhável (viraria IDOR).
- **CONFIRME NA FASE 2:** que o mecanismo escolhido **(a)** liga o 2º fluxo ao **próprio** usuário (sem IDOR), **(b)** é **byte-idêntico** entre `vulnerable` e `fixed`, e **(c)** fecha a cadeia login→change-password no Repeater sem fricção.

---

## O ataque (dois tempos) + a prova

**Cenário travado; a STRING EXATA do payload e a forma da 2ª query são candidatos confirmados por probe (Fase 2).** Semente inclui uma **conta-vítima** `admin` cujo efeito colateral vira a prova.

**Tempo 1 — plantar (inócuo).** Registrar um usuário cujo **`username` é um payload SQL**:

```
POST /register    {"username": "admin'--", "password": "attackerpw"}
→ {"registered": true}
```

O `INSERT` é parametrizado: `admin'--` é gravado **literal**, como um nome de usuário qualquer (a UNIQUE constraint aceita — `admin'--` ≠ `admin`). **Nada explode.** **Prova de que o plantio não fez nada:** logar como `admin` com a senha **original** semeada continua funcionando — o `admin` está intacto:

```
POST /login    {"username": "admin", "password": "admin-lab-pw"}
→ {"authenticated": true}          # admin ainda tem a senha original
```

**Tempo 2 — detonar.** Logar como o **usuário-payload** e acionar o 2º fluxo:

```
POST /login             {"username": "admin'--", "password": "attackerpw"}
→ {"authenticated": true}          # + Set-Cookie: session=...  (uid = id do atacante)

POST /change-password   (Cookie: session=...)   {"new_password": "pwned123"}
→ {"updated": true}
```

O servidor relê o `username` do usuário logado (`admin'--`) e monta a 2ª query.

- **`vulnerable` (8029):** `UPDATE users SET password = ? WHERE username = 'admin'--'` → efetivo `UPDATE users SET password = 'pwned123' WHERE username = 'admin'` (o `--'` vira comentário). **A senha do `admin` é trocada** para `pwned123`. O `UPDATE`, que devia mexer só na conta do atacante, foi **redirecionado** para a conta `admin`.
- **`fixed` (8129):** `UPDATE users SET password = ? WHERE username = ?` com `("pwned123", "admin'--")`. O valor relido vira **literal**: casa **só** a linha cujo `username` é literalmente `admin'--` (a do próprio atacante). **O `admin` fica intacto.**

**Tempo 3 — a prova (leitura read-only, NÃO injetável).** Logar como `admin` com a senha **nova**:

```
POST /login    {"username": "admin", "password": "pwned123"}
→ vulnerable: {"authenticated": true}     # o atacante trocou a senha do admin → takeover
→ fixed:      {"authenticated": false}    # o ataque não escapou; admin inalterado
```

Corroborando: no `vulnerable`, `admin` + senha **original** agora dá `false` (mudou); no `fixed`, `admin` + senha **original** ainda dá `true` (inalterado).

### DECISÃO-ABERTA / CONFIRME NA FASE 2 (probe — NÃO travar; registrar candidato + "proponha o que funcionar")

1. **A STRING EXATA do payload + a forma da 2ª query.** **CRÍTICO (`sqlite3`):** `cursor.execute()` **NÃO permite múltiplos statements numa chamada** (proíbe **stacked queries** — o `'; DROP ...`); só `executescript()` permitiria (e a app **não** usa `executescript` nas queries de request). Então o payload **NÃO é stacked-query** — é **subversão do WHERE/da lógica da PRÓPRIA query** (um único `UPDATE`).
   - **Candidato primário: `username = "admin'--"`** (comentar o resto e redirecionar o `WHERE` para a conta `admin` — takeover de UMA conta-alvo específica; **consistente com o `01`**, que usou o primitivo `alice' --`). **VALIDAR:** confirmar que, com o `?` de `new_password` **antes** do ponto de injeção, o `sqlite3` aceita **um** placeholder e o `--'` final vira comentário — **um único statement**, sem erro.
   - **Fallback documentado: `username = "x' OR '1'='1"`** → `... WHERE username = 'x' OR '1'='1'` → o `UPDATE` atinge **todas as linhas** (reset de senha em massa). Mais dramático, porém menos cirúrgico (muda todo mundo, inclusive o atacante). Usar **só** se o `admin'--` não reproduzir cirurgicamente.
   - **Protocolo:** montar, **DISPARAR** e confirmar **capturando a query REAL montada** (logar o `filt`/`query`) **e o efeito no banco** (a senha do `admin` mudou). Se a forma canônica não reproduzir com `execute`, **registrar honestamente e usar a que reproduz** (subversão de WHERE) — **NÃO inventar stacked-query que o driver bloqueia**. **Se NADA reproduzir, PARAR e avisar o mantenedor.**
2. **Como a prova fica observável.** O dano do `UPDATE` injetado **não aparece** na resposta HTTP do `/change-password` (ela só diz `{"updated": true}`). A prova é o **tempo 3** — a **3ª leitura** que revela o efeito colateral:
   - **Candidato primário: logar como `admin` com a senha nova** (`POST /login`) → `true` no vulnerable, `false` no fixed. **Observável 100% por HTTP**, sem infra extra. O `/login` é **parametrizado** (read-only, **não** injetável) — a prova não introduz 2ª superfície.
   - **Corroboração/fallback: `docker exec` no SQLite** (`SELECT username, password FROM users WHERE username='admin'`) — memória `validating-atoms-via-docker-exec` (portas host podem não ser alcançáveis do sandbox; cair pra dirigir o app/DB de dentro do container). Read-only, não injetável.
   - **CONFIRME NA FASE 2** a forma de tornar o efeito visível **sem** virar 2ª superfície injetável.

---

## Payload-prova — BENIGNA E OBSERVÁVEL (§8)

A prova é o **EFEITO do second-order**, não um dump de dado:

- **Baseline:** o 2º fluxo com um usuário **NORMAL** (registrar `normaluser`/`pw`, logar, `change-password`) só afeta a **própria** conta — `admin` intacto, **idêntico nos dois lados**. (Mesmos passos do ataque; **só o `username` muda** — deixa o contraste cristalino.)
- **Ataque:** o usuário-**payload** (`admin'--`) aciona o 2º fluxo e o efeito **ESCAPA** — no `vulnerable`, a senha do `admin` muda (o `UPDATE` foi redirecionado). No `fixed`, o **MESMO** usuário-payload aciona o 2º fluxo e **NADA escapa** (o payload vira valor literal; só a linha do próprio atacante seria afetada).
- **Benigno (§8):** subverte um `UPDATE` **dentro do lab** (dados fake, SQLite efêmero por container) pra **provar o redirecionamento pela 3ª leitura**. **SEM RCE** — é subversão de query. **Sem** ops destrutivas fora do escopo do lab (o `UPDATE` troca uma senha fake numa tabela fake; nada de `DROP`/exfil de sistema). **Não overclamar.**
- O lab é **isolado** (bind **só** `127.0.0.1`; containers descartáveis; banco efêmero re-semeado a cada `up` limpo). O WALKTHROUGH deixa **explícito** que é um lab local e o takeover é uma **prova de conceito benigna**.

---

## O código — o coração nas DUAS queries (a de entrada, segura; a de uso, o bug)

O fix é **server-side** (no `app.py`) — como no `01`. O `app.py` **DIFERE** entre os lados **em uma única linha lógica**: a 2ª query (o `UPDATE` do `/change-password`). Todo o resto — `GET /` banner, `POST /register` (parametrizado), `POST /login` (parametrizado), a **leitura** que relê o username (parametrizada), o schema/seed, a sessão — é **IDÊNTICO** nos dois lados.

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma o comportamento do `sqlite3` por probe (placeholder + comentário num único statement), e captura a query real montada e o efeito no banco.** Assinatura exata das queries, o seed, e o mecanismo de sessão são itens de confirmação (riscos #7/#9).

### `vulnerable/app.py` — a 2ª query concatena o valor relido (candidato)

```python
import os
import sqlite3
from flask import Flask, request, jsonify, session

app = Flask(__name__)
# Lab dummy: signs the session cookie only. Orthogonal to the vuln; identical
# in the fixed version. NOT the object of study.
app.secret_key = os.environ.get("SECRET_KEY", "changeme")
DB_PATH = os.environ.get("DB_PATH", "lab.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    # Banner only -- the vuln lives in POST /change-password (see WALKTHROUGH).
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /register, POST /login, then POST /change-password. "
                "Work from Burp Repeater.",
    })


@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")
    conn = db()
    # SAFE (parameterized): even a SQL payload in `username` is stored as a literal
    # VALUE here -- nothing executes. This is the "plant" step of a second-order bug.
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()
    return jsonify({"registered": True})


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")
    conn = db()
    # SAFE (parameterized): login is NOT the injectable surface in this atom.
    row = conn.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?", (username, password)
    ).fetchone()
    conn.close()
    if row:
        session["uid"] = row["id"]
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


@app.route("/change-password", methods=["POST"])
def change_password():
    uid = session.get("uid")
    if not uid:
        return jsonify({"error": "not authenticated"}), 401
    body = request.get_json(silent=True) or {}
    new_password = body.get("new_password", "")
    conn = db()
    # The logged-in user's username is READ BACK from the DB (parameterized read).
    uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
    # VULNERABLE: the username re-read from the DB is concatenated straight into the
    # UPDATE. It was STORED safely (parameterized) at registration, so it was never
    # treated as untrusted here -- but a value read back from the DB is untrusted
    # input again. Note `new_password` (fresh input) IS parameterized; only the
    # re-read value is spliced in -- so a payload username rewrites WHICH row this hits.
    query = f"UPDATE users SET password = ? WHERE username = '{uname}'"
    conn.execute(query, (new_password,))
    conn.commit()
    conn.close()
    return jsonify({"updated": True})


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        INSERT INTO users (username, password) VALUES
            ('admin', 'admin-lab-pw'),
            ('alice', 'alice-lab-pw'),
            ('bob',   'bob-lab-pw');
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — MESMO código, com a 2ª query PARAMETRIZADA (candidato)

Só o `/change-password` muda; tudo o mais é idêntico:

```python
@app.route("/change-password", methods=["POST"])
def change_password():
    uid = session.get("uid")
    if not uid:
        return jsonify({"error": "not authenticated"}), 401
    body = request.get_json(silent=True) or {}
    new_password = body.get("new_password", "")
    conn = db()
    uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
    # FIXED: the username re-read from the DB is bound as a parameter, exactly like
    # every other query in this app. A value read back from the DB is untrusted input
    # again -- so it goes through a placeholder, never into SQL text. The payload is
    # matched as a literal value; the UPDATE hits only the caller's own row.
    conn.execute(
        "UPDATE users SET password = ? WHERE username = ?", (new_password, uname)
    )
    conn.commit()
    conn.close()
    return jsonify({"updated": True})
```

- **O diff é a 2ª query (o `UPDATE` do `/change-password`).** `f"... WHERE username = '{uname}'"` (concatenado) → `"... WHERE username = ?"` com `uname` no tuple de parâmetros. **O `app.py` DIFERE** só nesse ponto.
- **`register`, `login`, a leitura que relê o username, o schema/seed, a sessão: IDÊNTICOS** nos dois lados. O cadastro **sempre** foi parametrizado — **a entrada nunca foi o problema**.
- **`new_password` é parametrizado nos DOIS lados** (input fresco, sempre tratado). O único valor que o `vulnerable` concatena é o `uname` **relido** — o coração da lição.
- **Higiene tolerante:** `get_json(silent=True) or {}` + `.get(..., "")`. Ortogonal ao bug. (Confirmar na Fase 2 que corpo ausente/inválido não quebra os fluxos.)

---

## O fix e o tipo de diff

**Fix:** **parametrizar a 2ª query** (a do ponto de USO/leitura) — trocar a concatenação `f"... WHERE username = '{uname}'"` por um placeholder `"... WHERE username = ?"` com `uname` passado como parâmetro. Tipo de diff: **lógica-diferente** no ponto da 2ª query (valor relido **concatenado** → valor relido **passado como parâmetro**). O valor relido vira **dado literal**; o `WHERE` volta a casar exatamente a linha pretendida; o redirecionamento falha.

Diff colável (candidato — a Fase 2 gera o real):

```diff
     uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
-    # VULNERABLE: the username re-read from the DB is concatenated straight into the
-    # UPDATE. A value read back from the DB is untrusted input again.
-    query = f"UPDATE users SET password = ? WHERE username = '{uname}'"
-    conn.execute(query, (new_password,))
+    # FIXED: the re-read username is bound as a parameter, exactly like every other
+    # query in this app. It is matched as a literal value, never SQL syntax.
+    conn.execute(
+        "UPDATE users SET password = ? WHERE username = ?", (new_password, uname)
+    )
```

**O CONTRASTE é o diff:** o vulnerable concatena o valor **relido** no `UPDATE` (vira sintaxe); o fixed o **parametriza** (vira dado). A única mudança é o placeholder no `WHERE` da 2ª query.

### Notas obrigatórias no `DIFF.md`

1. **A CAUSA é CONCATENAR NA 2ª QUERY um valor não-confiável, NÃO "o cadastro foi inseguro".** Enquadrar honesto: o cadastro é **seguro** (parametrizado); o bug é a **2ª query** colar o valor **relido** do banco. Parametrizar a 2ª query **neutraliza** porque o valor relido vira **dado literal** — nunca sintaxe —, então o `WHERE` casa exatamente a linha pretendida e não há como reestruturar a query. **CURTA e direta.**
2. **"MAS EU JÁ PARAMETRIZEI NO CADASTRO / É SÓ SANITIZAR NA ENTRADA" NÃO É O FIX — nota-ADVERTÊNCIA "mencionável, não aplicada"** (molde das notas dos irmãos):
   - **(a) Nomear as duas intuições.** *"Parametrizei o registro, tô seguro"* e *"é só sanitizar/validar o `username` no cadastro (proibir aspa, `--`)"*.
   - **(b) Mostrar por que falham.** Parametrizar/sanitizar na **ENTRADA** protege a query da **entrada** — não faz nada pela query do **ponto de uso**, que concatena o valor relido; a proteção **não viaja com o dado**. Sanitizar charset na entrada é ainda **frágil e no lugar errado** (encodings, símbolos legítimos, outros caminhos que gravam no banco).
   - **(c) Cravar o fix real:** **toda leitura do banco é input não-confiável de novo**; o fix é **parametrizar no ponto de uso** (a 2ª query). **CURTA** (intuição + porquê), **NÃO** seção gigante.
3. **CONTRASTE com o `01` (mesma classe/motor/fix; o que muda é ordem/tempo).** Referir a tabela da seção "Contraste". Mesma classe (A03, SQLi), mesmo motor (parser SQL do SQLite), **mesmo fix** (query parametrizada); **o que difere é o TEMPO e o ponto de disparo** (1ª ordem = entra e detona no mesmo fluxo; 2ª ordem = planta agora, detona depois, noutro fluxo). "Um átomo = uma vuln" = a **causa** (concatenação de input não-confiável), não o teto. **Sem foreshadow** (não nomear átomo/variante futura; outras faces do second-order ficam em UMA linha de descrição da classe).

---

## Biblioteca / stack

- **App (`vulnerable`/`fixed`): Flask + `sqlite3` (stdlib).** `requirements.txt` **idêntico** entre os dois, **só Flask** (pinado como nos irmãos):

```
Flask==3.0.0
```

  - `Flask==3.0.0` casa com os irmãos SQLi (01/06/07). `sqlite3` é **stdlib** — sem dependência extra. **Sem** ORM, sem `requests`, sem 2ª lib (`CLAUDE.md` §3.6). A **sessão** usa o mecanismo **nativo** do Flask (sem `Flask-Session` nem dep extra).
  - **CONFIRME NA FASE 2** o comportamento do `sqlite3` quanto a **múltiplos statements** (`execute` **proíbe** stacked queries; `executescript` permite mas **não** é usado nas queries de request) — **decide a forma do payload** (risco #7): subversão de WHERE, **não** stacked-query.
- **Single-container, molde do `01`.** SQLite **efêmero** (seed no boot via `init_db()`; **sem** volume persistente). `Dockerfile` molde dos SQLi irmãos, **mas SEM `COPY templates`** (API-only — molde do `28`): `FROM python:3.11-slim`, `pip install -r requirements.txt` (Flask), `COPY app.py`, `ENV HOST=0.0.0.0`, `CMD ["python", "-u", "app.py"]`. **Confirmar por probe** que `Flask==3.0.0` instala em `python:3.11-slim` como wheel puro, sem toolchain (trivial — os irmãos já provam).

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY JSON** (o vetor é o **corpo JSON** no Repeater; decisão de forma justificada na Nota de planning 3). Garantir que a **ÚNICA** vuln é o `/change-password` **concatenar** o `username` **relido** na 2ª query:

- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`. Sem HTML ⇒ sem autoescape/XSS acidental.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (molde do `22`/`28`): *"⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network."* + dica de trabalhar pelo Burp Repeater. **O `GET /` não é injetável.**
- **A ÚNICA vuln é o `/change-password`** (a concatenação do `uname` relido). `POST /register`, `POST /login` e a **leitura** que relê o username são **parametrizados** — **higiene idêntica nos dois lados**, **NÃO** superfícies injetáveis. **SEM** 2ª superfície, **SEM Saída B** (o placeholder `?` do `sqlite3` existe e o app o usa em todo lugar; o bug é **não** usá-lo na 2ª query — **NÃO inventar** uma ferramenta-que-resiste).
- **O `fixed` muda SÓ a 2ª query** (concatenação → placeholder). `GET /`, `register`, `login`, a leitura relida, `Dockerfile`, `requirements.txt`, schema/seed e sessão são **idênticos** entre os lados.
- **A sutileza que NÃO pode enfraquecer a lição:** o fixed **parametriza a 2ª query**, **NÃO** sanitiza/valida o `username` no cadastro (a defesa-armadilha da nota #2), **NÃO** mexe no cadastro (que já era seguro). A sessão/`SECRET_KEY`, o parse tolerante, o schema/seed são **higiene idêntica** nos dois lados — ortogonais à vuln.
- **A sessão NÃO pode introduzir 2ª vuln:** liga o 2º fluxo ao **próprio** usuário logado (sem IDOR — o `/change-password` não aceita alvo da request); tamper-proof; idêntica nos dois lados. `SECRET_KEY` dummy é ortogonal.

---

## WALKTHROUGH — abertura seca; Burp-only; headers PT traduzidos

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa os **dois fluxos** e a falha (o valor relido vira sintaxe SQL na 2ª query). Trilha **100% Burp (Repeater)**, `curl` como equivalente; **SEM trilha browser**.

**Abertura (candidato — plantar a lição, seco):**

> *O app tem dois fluxos. Um cadastro grava seu usuário com uma query parametrizada — mandar um payload SQL no `username` aqui não faz nada, ele é gravado literal. Um segundo fluxo, o troca-senha, faz o oposto: relê seu `username` do banco e o **cola** cru na string de um `UPDATE`. O detalhe que torna isso explorável: o valor relido é tratado como confiável só porque veio do próprio banco — mas ele entrou como o que **você** digitou no cadastro. O payload, dormente na tabela desde o registro, vira sintaxe SQL na 2ª query e reescreve **qual linha** o `UPDATE` atinge. Você planta agora e detona depois, num fluxo diferente.*

Beats (molde do `01`/`06`/`07` publicados — abertura seca, seções numeradas `## 1..6`; adaptar a forma request-no-Repeater com corpo JSON, sem browser):

1. **Context.** Dois fluxos: `POST /register` (parametrizado, grava) e `POST /change-password` (relê o `username` e concatena no `UPDATE`); um `POST /login` mínimo os liga. **Definir na estreia:** **second-order SQL injection** (a.k.a. *stored SQL injection* — o payload é gravado por um caminho e disparado por outro), **first-order/in-band SQL injection** (payload entra e detona na mesma request — o `01`), **query parametrizada / placeholder `?`** (o driver separa o texto SQL do dado), **sink** (onde o valor vira SQL — aqui, a 2ª query), **source** (de onde o valor não-confiável vem — aqui, a **leitura do banco**, não a request direta), **trust boundary** (a linha entre input não-confiável e dado interno confiável — que o app erra ao reassumir confiança num valor só porque veio do banco), **stacked queries** (vários statements numa chamada — **não** é o que este átomo usa). Isto é **A03 — Injection**. Portas: `vulnerable` `127.0.0.1:8029`, `fixed` `127.0.0.1:8129`. Trilha 100% Burp/curl (API-only, sem browser). **Nota operacional:** o banco é gravável e efêmero — pra repetir do zero, `./atom down` + `up` reseta.
2. **Spot the bug.** Mostrar **OS DOIS pontos**: (a) `POST /register` — `INSERT ... VALUES (?, ?)`, **parametrizado** — e **explicitar que atacá-lo direto NÃO faz nada** (o `username` vira dado literal; um `' OR 1=1--` no cadastro é gravado como texto); (b) `POST /change-password` — a leitura parametrizada que relê o `username`, seguida do `UPDATE` que o **concatena** (`f"... WHERE username = '{uname}'"`), com o `new_password` **parametrizado** ao lado. **O tell é o contraste entre os dois** (e entre o `uname` concatenado e o `new_password` parametrizado, na **mesma** query). Pergunta de auditoria: *"esse `username` que EU escolhi no cadastro é **relido** e **colado** na 2ª query — e se eu registrar um `username` que seja um payload?"* Foreshadow do fix: **parametrizar a 2ª query também**.
3. **Exploitation (Repeater — o payload no corpo JSON; a prova é a resposta do login-como-vítima).**
   - **Baseline (feature benigna, dois lados):** registrar `normaluser`/`pw`, logar, `change-password` com `new_password=x` → só a conta do `normaluser` muda; `admin` intacto (logar `admin`+senha original → `true`). **Mesmos passos do ataque, só o `username` muda.**
   - **Tempo 1 — plantar:** `POST /register {"username":"admin'--","password":"attackerpw"}` → `{"registered": true}`. **Mostrar que o plantio NÃO explodiu:** `admin` + senha original ainda dá `true`.
   - **Tempo 2 — detonar:** logar como `admin'--` (Set-Cookie), depois `POST /change-password {"new_password":"pwned123"}` com o cookie → `{"updated": true}`. **Mostrar o `UPDATE` real montado** (capturado na Fase 2) e por que o `--'` redireciona o `WHERE` pra `admin`.
   - **Tempo 3 — a prova:** `POST /login {"username":"admin","password":"pwned123"}` → `{"authenticated": true}` (takeover do admin). Corroborar por `docker exec` no SQLite se útil.
   - **§8 (cravar):** lab **isolado** (bind só `127.0.0.1`; container descartável; banco efêmero); payload **benigno** — subverte um `UPDATE` numa tabela fake pra provar o redirecionamento pela 3ª leitura; **sem** RCE, **sem** ops destrutivas. Num alvo real, second-order SQLi vai de takeover de conta a manipulação de dados — **manter os payloads demonstrativos**.
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **(a) NÃO é bug do cadastro / da escrita.** O `INSERT` é parametrizado e seguro; atacar o cadastro **direto** não faz nada. A escrita nunca foi o problema.
   - **(b) NÃO é "sanitizar input na entrada".** Sanitizar/validar o `username` no cadastro é remédio **no lugar errado** (e frágil); o fix é **parametrizar a 2ª query**. Parametrizar na entrada **não viaja** com o dado até o ponto de uso.
   - **(c) NÃO é SQLi de primeira ordem (`01`).** O payload **não explode na entrada**; dorme no banco e detona no **2º uso**, noutro fluxo. O ponto de entrada **testa como seguro**.
   - **Prova de isolamento (cravar):** um usuário com `username` **NORMAL** passa pelos **dois** fluxos sem nada escapar, **nos dois lados**; só o `username`-**PAYLOAD**, no `vulnerable`, subverte a 2ª query — e no `fixed` **nem ele**.
5. **Impact (honesto — sem overclaim).** **Subversão da 2ª query → modificação de dados que o fluxo não deveria tocar** — aqui, **takeover de conta** (o atacante troca a senha do `admin` e loga como ele). Escopo = **o que a 2ª query permite** (um `UPDATE` com `WHERE` reescrito): takeover de UMA conta-alvo (`admin'--`) ou reset em massa (`OR '1'='1`). É subversão de query no 2º fluxo. **Sem overclaim:** **não é RCE**; o teto é o que o `UPDATE` permite. A classe second-order tem **outras faces** (o payload relido pode cair num `SELECT`/`INSERT` e exfiltrar/alterar outros dados) — **descrição de UMA linha da classe**, **sem** modelar nem foreshadowar.
6. **Why the fix works (porta 8129).** Repetir contra o `fixed/`:
   - A **MESMA** cadeia (registrar `admin'--` → logar → `change-password`) → o `UPDATE` parametrizado casa **só** a linha do próprio atacante; o `admin` fica **intacto**. Prova: `POST /login {"username":"admin","password":"pwned123"}` → `{"authenticated": false}`; `admin` + senha original ainda dá `true`.
   - **Prova de isolamento:** o baseline honesto (usuário normal) se comporta **idêntico** nos dois lados; só o **payload** separa `vulnerable` (escapa) de `fixed` (não escapa).
   - **A lição do diff:** o fix **parametriza a 2ª query**. Parametrizar/sanitizar na **entrada NÃO é o fix** (nota #2 — a proteção não viaja com o dado; sanitizar charset é frágil e no lugar errado); mesma classe/motor/fix do `01`, o que muda é **ordem/tempo** (nota #3).

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado; a trilha é Burp/curl). Requests/responses são placeholders da execução real capturada na Fase 2 (o `UPDATE` real montado; a string exata de payload travada por probe).

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5)

Reforço do beat 4, porque em vuln de **lógica/tempo** (o exploit é dado legítimo — um `username` que é payload, e reordenar dois fluxos) o aluno pode internalizar a forma errada (achar que é bug do cadastro, ou 1ª ordem):

- **(a) NÃO é bug do cadastro/da escrita** — o `INSERT` é parametrizado e seguro; atacar o cadastro direto não faz nada.
- **(b) NÃO é sanitização de input na entrada** — sanitizar no cadastro é remédio no lugar errado (e frágil); o fix é **parametrizar a 2ª query**.
- **(c) NÃO é SQLi de primeira ordem (`01`)** — o payload não explode na entrada; dorme no banco e detona no 2º uso, noutro fluxo.
- **Prova de isolamento:** `username` normal → nada escapa, nos dois lados; só o `username`-payload, no `vulnerable`, subverte a 2ª query — e no `fixed` nem ele.

---

## Impacto honesto

**Subversão da 2ª query no segundo fluxo → modificação de dados que não deveriam ser tocados (takeover de conta).** O atacante planta um `username`-payload no cadastro (inócuo), e no 2º fluxo o valor relido reescreve o `WHERE` do `UPDATE`, redirecionando-o para outra conta (`admin`) — troca a senha dela e loga como ela. Poder disso: **acesso não autorizado** ao que a conta comprometida acessa (no contexto da vítima). **Sem overclaim:** o finding é **subversão de query / takeover de conta** — **NÃO** inflar pra RCE (não há execução de código), **NÃO** afirmar dump irrestrito. O teto é **o que a 2ª query permite** (um `UPDATE` com `WHERE` reescrito). A classe second-order tem **outras faces** (o valor relido caindo em `SELECT`/`INSERT`) — **UMA linha** de descrição da classe, **sem** modelar nem foreshadowar. A **prova do lab é benigna** (a resposta do login-como-vítima). Sem foreshadow.

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A03 — átomo dentro de família publicada; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`sqli-union-basic` (01)** — o contraste **central** (seção dedicada + tabela). Mesma A03, mesmo motor (parser SQL do SQLite), **mesmo fix** (query parametrizada); **o que difere é o tempo/ponto de disparo** (1ª ordem vs 2ª ordem). O `01` é **pré-requisito conceitual** (a mecânica aspa/`--` que quebra o literal é a mesma). Referência pra **trás**, permitida.
- **`sqli-blind-boolean` (06)` / `sqli-blind-time` (07)`** — voz/estrutura da família SQLi; confirmam o padrão SQLite + parametrização. Citáveis: nos dois, o `/login` **era** o SQLi (1ª ordem); aqui o `/login` é **higiene parametrizada** — contraste que reforça "o ponto de entrada testa como seguro". Referências pra **trás**, permitidas.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5; e esta spec é pública):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante futura** por número, nome, slug **OU** descrição — inclusive os próximos átomos (a posição vive **só** no `ROADMAP.md`), **outras faces do second-order** modeladas como átomo futuro, ou a posição/ordinal/release de fase.
- **PROIBIDO anunciar posição de fase (abrir/fechar/ordinal/"penúltimo"), versão/release, ou a sequência de átomos/stacks ao redor.** O átomo — **e esta spec** — se descreve **isolado**. Nas frases que proíbem foreshadow, manter a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).
- **Que o second-order tenha outras faces** (o valor relido caindo num `SELECT`/`INSERT`, ou blind second-order) é, no máximo, **descrição conceitual de UMA LINHA** ("second-order SQLi tem outras faces além do takeover via `UPDATE` — o padrão é o mesmo: dado relido do banco virando sintaxe SQL num 2º uso") — **sem** nomear átomo/variante futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 29 vai até **subversão da 2ª query via `username`-payload relido → takeover de conta** (o finding), provado pela 3ª leitura. **Uma vuln, uma causa (concatenar input não-confiável — o valor relido — na 2ª query; todo dado lido do banco é input não-confiável de novo), um fix (parametrizar a 2ª query, no servidor).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL/âncora por fetch na Fase 2 — NÃO inventar.**

- **Candidato:** **`https://portswigger.net/web-security/sql-injection`** — a página-classe de SQL injection, que **contém a seção "Second-order SQL injection"** (a PortSwigger a trata como uma seção da página-classe, não uma página própria). **Se a seção tiver âncora estável** (candidato a confirmar por fetch: algo como `#second-order-sql-injection`), **linkar direto na âncora**; **se a âncora for instável, linkar a página-classe** `.../sql-injection`. É a página de introdução conceitual, não a de labs.
- **Texto do link:** **"SQL injection"** — a forma apresentada pela própria PortSwigger (casa com os irmãos SQLi 01/06/07, que já linkam essa página-classe). Preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7).
- **Grafia do H1:** casar com o título/seção da página — candidato **"Second-order SQL injection"**. Confirmar por fetch na Fase 2.
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `sqli-union-basic`).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A03 — Injection** (`atoms/A03-injection/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `sqli-second-order` em A03; `CLAUDE.md` §4 fixa a pasta. Situar em A03 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Topologia | **SINGLE-CONTAINER por lado** — 2 serviços (vulnerable + fixed), SQLite embutido, sem datastore externo | Molde do `01`. SQLite é arquivo embutido; cada lado tem seu `lab.db` efêmero. |
| Banco | **SQLite efêmero, GRAVÁVEL** (`INSERT` no register, `UPDATE` no change-password) | Seed no boot via `init_db()`; sem volume; recria/reseta a cada `up` limpo. Diferente dos irmãos read-only. |
| Lição-coração | **Parametrizar na entrada não protege o ponto de uso; o payload dorme no banco e detona no 2º fluxo que relê e concatena; fix = parametrizar a 2ª query.** | A causa é concatenar o valor **relido** na 2ª query; todo dado lido do banco é input não-confiável de novo. |
| Sub-lição crítica | **A defesa NÃO é sanitizar/validar o username no cadastro nem "parametrizei na entrada" — é parametrizar a 2ª query** | Desarma as duas intuições erradas. A proteção não viaja com o dado; sanitizar charset é frágil e no lugar errado. |
| Contraste central | **`01` (SQLi 1ª ordem)** — mesma A03/motor/**fix**; o que muda é **ordem/tempo** (entra-e-detona vs planta-e-detona-depois) | Justifica o átomo. "Um átomo = uma vuln" = causa (concatenação de input não-confiável), não teto. |
| Contraste de apoio | **`06`/`07`** — voz de família; no `/login` deles o SQLi era 1ª ordem, aqui o `/login` é higiene parametrizada | Reforça "o ponto de entrada testa como seguro". |
| Tipo de átomo | **API-only JSON** (sem HTML, sem templates, sem browser) | 3 fluxos + sessão + cadeia multi-request = API-shaped (§3.3; molde 22/28). Prova = resposta HTTP. **Confirmável (flip pra form é localizado).** |
| Trilha | **100% Burp (Repeater) / curl; SEM browser** | Prova = resposta do login-como-vítima (não execução client-side). **NÃO** usar a exceção de browser do 21. |
| Flavor — **TRAVADO** | **Cadastro parametrizado (plantar) + login mínimo + change-password que relê e concatena (detonar)** | Dois tempos. A ÚNICA superfície injetável é a 2ª query (`UPDATE` do change-password). |
| Sessão — **candidato, confirmar** | **Sessão assinada do Flask** (`session["uid"]` no login; lida no change-password) | Tamper-proof ⇒ sem IDOR; mínima; idêntica nos dois lados; sem dep extra. `SECRET_KEY=changeme` dummy ortogonal. Fallback: token opaco mapeado server-side. |
| Payload-prova — **conceito TRAVADO, string = probe** | **`username = "admin'--"` + change-password → senha do `admin` trocada → login-como-admin passa** | Loga como a vítima. **String confirmada por probe (risco #7), capturando o `UPDATE` real; fallback `x' OR '1'='1` (mass update); se nada reproduzir, PARAR e avisar.** |
| Compat. `sqlite3.execute` | **Subversão de WHERE (um statement), NÃO stacked-query** | `execute()` proíbe múltiplos statements; `executescript` não é usado. Payload = comentar/subverter o WHERE do próprio `UPDATE`. |
| `new_password` na 2ª query | **Parametrizado (`?`) nos DOIS lados; só o `uname` relido é concatenado no vulnerable** | Prova que o perigo não é input fresco (tratado), é o valor **relido** tratado como confiável. |
| Código vulnerable | **`query = f"UPDATE users SET password = ? WHERE username = '{uname}'"`** (uname relido, concatenado) | O valor relido vira sintaxe → reescreve qual linha o `UPDATE` atinge → takeover. |
| Código fixed | **`conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, uname))`** | O valor relido vira dado literal; o `UPDATE` casa só a linha do próprio atacante. |
| `app.py` vulnerable × fixed | **DIFERE** só na 2ª query (concatenação → placeholder) | O fix vive no servidor, no ponto de uso (como o `01`). |
| Fix (único eixo) | **Parametrizar a 2ª query (a do ponto de uso), com placeholder `?`** | Correção na raiz (concatenação do valor relido). Não sanitizar/validar na entrada; não mexer no cadastro (já seguro). |
| Diff | **Lógica-diferente** — o placeholder no `WHERE` da 2ª query | A linha perigosa é o f-string com o `uname` relido; o fix é parametrizar. |
| Sanitizar/validar na entrada | **Mencionar, NÃO aplicar** (nota #2) | Remédio no lugar errado e frágil; a proteção não viaja com o dado. A raiz é parametrizar o 2º uso. |
| "Já parametrizei o cadastro" | **Mencionar, NÃO aplicar** (nota #2) | Parametrizar a entrada não protege o ponto de uso posterior. |
| Bibliotecas | **`Flask==3.0.0`** (sqlite3 stdlib; sessão nativa do Flask) | Molde dos irmãos SQLi. Sem ORM/dep extra. |
| Banner | **Obrigatório, num `GET /` JSON de aviso** (API-only) | `CLAUDE.md` §8.2. `GET /` não injetável; única superfície é `POST /change-password`. |
| Impacto | **Subversão de query / takeover de conta.** Sem RCE, sem dump irrestrito. | Honesto; teto = o que o `UPDATE` permite. Sem foreshadow. |
| Theory primer | **PortSwigger "SQL injection"** (`/web-security/sql-injection`, seção Second-order; confirmar âncora por fetch) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. Casa com os irmãos. |
| Título (H1) | **`sqli-second-order — Second-order SQL injection`** (classe, sem stack) | `CLAUDE.md` §5. Sem "SQLite"/"Flask" no H1. Grafia final casa com o primer. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública) | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release/outras faces do second-order como átomo futuro. |
| Portas | **8029 / 8129** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container por lado. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si** (molde dos irmãos SQLi, **mas API-only → SEM `COPY templates`**):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

`app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py` (idêntico aos irmãos). `init_db()` chamado no boot (seed embutido; **sem** arquivo de schema separado — `executescript` dentro do `app.py`, molde do `01`).

**`docker-compose.yml`** (molde EXATO do `01` — dois serviços, **sem** datastore, **sem** healthcheck/`depends_on`/rede; apps bind **só** `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8029:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8129:5000"
```

- **§8:** ambos publicam porta **só** em `127.0.0.1`. Sem datastore externo, sem rede nomeada. Banco efêmero por container (recria/reseta a cada `up` limpo).
- **Confirmar na Fase 2** (risco #11) que `./atom up sqli-second-order` sobe os dois e a cadeia register→login→change-password funciona de primeira.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes de design — exceto onde marcado "DECISÃO ABERTA".

1. **Registro parametrizado grava o `username`-payload SEM efeito:** `POST /register {"username":"admin'--",...}` grava literal; **atacar o cadastro direto não faz nada** (logar `admin`+senha original ainda dá `true`). **VALIDAR** nos dois lados.
2. **Login/cadastro NÃO são injetáveis:** `POST /login` e `POST /register` são parametrizados nos **dois** lados; um probe `' OR 1=1--` no login/cadastro **não acha nada**. **VALIDAR.**
3. **Baseline (o 2º fluxo com usuário normal):** registrar `normaluser`/`pw`, logar, `change-password` → só a própria conta muda; `admin` intacto; **idêntico nos dois lados**. **VALIDAR.**
4. **O ATAQUE (central — VALIDAR RODANDO):** `username`-payload + logar + `change-password` → subverte a 2ª query no **vulnerable** (8029): a senha do `admin` muda. **CAPTURAR a query REAL montada** (logar o `UPDATE`) + o **efeito no banco** + a request/response. **Se não reproduzir, PARAR e avisar — NÃO inventar.**
5. **FIXED:** a **MESMA** cadeia → **nada escapa** no **fixed** (8129): só a linha do próprio atacante seria afetada; o `admin` fica intacto (`admin`+senha original ainda dá `true`; `admin`+`pwned123` dá `false`). **CAPTURAR.**
6. **Prova de isolamento:** usuário normal → nada escapa, **idêntico** nos dois lados; só o **payload** separa vulnerable de fixed.
7. **String exata do payload + comportamento do `sqlite3` (probe):** confirmar que `execute()` **proíbe stacked queries** (⇒ o payload é **subversão de WHERE**, não `'; ...`) e que o `admin'--` reproduz com **um** placeholder (`new_password`) **antes** do ponto de injeção e o `--'` final como comentário — **um único statement**. Fallback `x' OR '1'='1` (mass update). **Se nada reproduzir cirurgicamente, PARAR e avisar — NÃO inventar stacked-query.**
8. **A prova fica observável sem virar 2ª superfície:** o takeover é provado pela **3ª leitura** (`POST /login` como `admin` com a senha nova — parametrizado, read-only, **não** injetável) e/ou por `docker exec` no SQLite (memória `validating-atoms-via-docker-exec`). **Confirmar.**
9. **Sessão mínima sem 2ª vuln:** o mecanismo (candidato: sessão assinada do Flask) liga o 2º fluxo ao **próprio** usuário logado; o `/change-password` **NÃO** aceita `id`/`username`-alvo da request (**sem IDOR/auth-bypass**); **byte-idêntico** nos dois lados; `SECRET_KEY` dummy ortogonal. **CONFIRMAR** que fecha a cadeia no Repeater (cookie do login → change-password).
10. **Uma vuln só:** **só** `POST /change-password` (a concatenação do `uname` relido) é injetável; `register`/`login`/a leitura relida são parametrizados (higiene); `GET /` é só banner. **SEM** 2ª superfície, **SEM Saída B**. Confirmar por `diff` que o `fixed` muda **só** a 2ª query.
11. **Compose + instalação:** `./atom up sqli-second-order` sobe os dois serviços; `Flask==3.0.0` instala em `python:3.11-slim` como wheel puro (sqlite3 stdlib); a cadeia funciona de primeira. Banco efêmero recria a cada `up` limpo.
12. **§8 — payload benigno + isolamento:** o takeover é provado **pela resposta do login-como-vítima**; **NADA** destrutivo (o `UPDATE` troca uma senha fake numa tabela fake; sem `DROP`/exfil de sistema; sem stacked-query); dados semeados **fake** (sem PII); apps bind **só** `127.0.0.1` (8029/8129); banco efêmero; lab contido.
13. **Theory primer** confirmado **por fetch** (PortSwigger "SQL injection", `/web-security/sql-injection`, seção Second-order — âncora estável ou página-classe); confirmar a **grafia exata do H1** contra a página. **Não inventar.**
14. **Diff é só a 2ª query:** o **ÚNICO** delta funcional entre `vulnerable/app.py` e `fixed/app.py` é a parametrização do `UPDATE` no `/change-password` (concatenação → placeholder). `GET /`, `register`, `login`, a leitura relida, `Dockerfile`, `requirements.txt`, schema/seed e sessão **idênticos**. Confirmar por `diff`.

**Bloqueante remanescente:** nenhum de decisão de vuln. **DECISÕES ABERTAS de Fase 2 (probe, não bloqueiam a spec):** a string exata do payload + comportamento do `sqlite3` (item 7); o mecanismo de sessão (item 9); a forma da prova observável (item 8); a URL/âncora/H1 do primer por fetch (item 13); a forma final (API-only vs form — recomendação API-only, flip localizado se o mantenedor preferir). **Protocolo:** registrar candidato, **disparar**, confirmar rodando; se não reproduzir, ajustar dentro do escopo travado; se travar de vez, **PARAR e avisar — NÃO inventar**.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **o `01` no eixo do tempo** — mesma classe, mesmo motor, **mesmo fix**, mas o payload **planta agora e detona depois**, num 2º fluxo que relê o dado do banco e concatena. Cada beat deve poder ser lido com o **`01` aberto ao lado**, e a diferença ("1ª ordem = entra e detona no mesmo fluxo; 2ª ordem = planta no cadastro parametrizado (inócuo) e detona no change-password que relê e concatena — o ponto de entrada testa como seguro, mas a bomba dormia no banco") deve estar visível na linha em discussão. **Abrir e fechar** na lição-coração: *parametrizar na entrada não protege o ponto de uso; toda leitura do banco é input não-confiável de novo; o fix é parametrizar a 2ª query.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`01` INTEIRO** (SQLi 1ª ordem — molde canônico de código Flask+SQLite single-container, estrutura de doc, o padrão "input reescreve a query" e o fix por query parametrizada; o contraste 01↔29 é o eixo), **`06`/`07`** (voz/estrutura da família SQLi; confirmam SQLite + parametrização; o `/login`-como-SQLi deles contrasta com o `/login`-higiene daqui). **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar encenação; **headers de seção traduzidos em TODA doc PT** (§7); título = classe sem stack.
- **NÃO há Saída B (crítico):** o placeholder `?` do `sqlite3` **existe e o app o usa em todo lugar** (cadastro, login, a leitura relida) — o bug é **especificamente não usá-lo na 2ª query** (`UPDATE` por f-string). **NÃO** inventar uma ruga de "a ferramenta padrão resiste". Isso **reforça** a lição: parametrizar na entrada não basta; o antipadrão é a concatenação **no ponto de uso**.
- **A prova é a RESPOSTA do login-como-vítima (riscos #4/#5/#8), no Burp/curl — NÃO no browser.** Não há execução client-side. Capturar a cadeia real: vulnerable → payload plantado (inócuo) → detonado → a senha do `admin` muda → login-como-admin passa; fixed → mesma cadeia → nada escapa. **Capturar também o `UPDATE` real montado** (logar). **Se não bater rodando, PARAR e avisar — NÃO inventar** prova nem payload.
- **§8:** payload **benigno** (subverte um `UPDATE` numa tabela fake pra provar o redirecionamento pela 3ª leitura; **sem** RCE, sem ops destrutivas, sem stacked-query); apps bind **só** `127.0.0.1`; dados semeados **fake**; banco efêmero por container; lab contido. Enquadrar explicitamente no WALKTHROUGH (incluindo a **nota operacional**: pra repetir do zero, `./atom down` + `up` reseta o banco).
- **A sutileza que NÃO pode enfraquecer a lição:** o **fixed parametriza a 2ª query**, **NÃO** sanitiza/valida o `username` no cadastro (nota #2), **NÃO** mexe no cadastro (já seguro). O `new_password` é parametrizado nos **dois** lados (input fresco, tratado); só o `uname` **relido** é concatenado no vulnerable — o coração da lição. A sessão/`SECRET_KEY`, o parse tolerante, o schema/seed são **higiene idêntica** nos dois lados.
- **Uma vuln só:** foco na 2ª query montada por concatenação crua do valor **relido** no `POST /change-password`. `register`/`login`/a leitura relida são parametrizados (higiene). `GET /` é **só** banner. **Sem** 2ª superfície, **sem** 2º endpoint injetável. O `fixed` muda **só** a 2ª query.
- **A sessão NÃO pode virar 2ª vuln (risco #9):** liga o 2º fluxo ao **próprio** usuário; o `/change-password` **não** aceita alvo da request (sem IDOR); tamper-proof; idêntica nos dois lados. Candidato: sessão assinada do Flask. `SECRET_KEY` dummy é ortogonal (não modelar segurança de sessão).
- **API-only, Burp-only:** sem `templates/`, sem `render_template`, sem browser. Respostas `jsonify`. Banner obrigatório num `GET /` JSON. Trilha 100% Burp Repeater (`curl` equivalente). **NÃO** criar trilha browser. **A forma API-only é recomendação justificada** (Nota de planning 3); se o mantenedor preferir form (consistência estrita da família SQLi), é um flip localizado — **registrar, não bloquear**.
- **Abertura seca:** WALKTHROUGH entra direto na mecânica; **sem** encenação. Rotular os beats: **context (definir second-order/first-order/parametrização/sink/source/trust boundary/stacked queries)** → **spot the bug (os DOIS pontos: cadastro parametrizado inócuo + 2ª query que concatena o relido)** → **exploitation (baseline; tempo 1 plantar inócuo; tempo 2 detonar; tempo 3 a prova)** → **o que a vuln NÃO é (não é bug do cadastro; não é sanitização na entrada; não é 1ª ordem)** → **impacto (subversão de query / takeover)** → **fixed (mesma cadeia → nada escapa; parametrizar a 2ª query)**.
- **PONTO PEDAGÓGICO OBRIGATÓRIO:** o WALKTHROUGH DEVE fazer o aluno **VER** que atacar o cadastro **diretamente** não funciona (a query de registro é parametrizada) — pra a lição "o perigo é a **LEITURA** do banco, não a escrita" ficar cristalina. Mostrar o registro do payload resultando em **ZERO efeito imediato** é parte **central** da narrativa, não um detalhe. Se o cadastro também concatenasse, seria 1ª ordem e o átomo perderia a razão de existir.
- **Impacto honesto:** **subversão de query / takeover de conta**; **não** inflar pra RCE nem dump irrestrito. Mesmo motor do `01`, o que muda é ordem/tempo. Sem overclaim, sem foreshadow.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que a causa é **concatenar o valor relido na 2ª query** (todo dado lido do banco é input não-confiável de novo); **não é** bug do cadastro/escrita (o `INSERT` é seguro), **não é** sanitização de input na entrada (o fix é parametrizar a 2ª query), **não é** 1ª ordem (o payload dorme no banco e detona no 2º uso).
- **Contraste com o `01` (cravar):** tabela (2 colunas: 01/29) + prosa; mesma A03/motor/**fix**, o que muda é **ordem/tempo**; o `01` é pré-requisito conceitual. Citar `01`/`06`/`07` (publicados) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** second-order SQL injection (a.k.a. stored SQL injection), first-order/in-band SQL injection, query parametrizada / placeholder (`?`), sink, source, trust boundary, stacked queries.
- **A03 sem arqueologia:** situar em **A03 — Injection**, explicar **por que** é injection (input → parser SQL que o trata como sintaxe), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `sqli-second-order — Second-order SQL injection`. "SQLite"/"Flask" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **01** (contraste central + molde de código/doc), **06/07** (voz de família), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase, a sequência de átomos ao redor, e outras faces do second-order como átomo futuro. **Manter as proibições genéricas** (sem listar nomes de átomos não-publicados). **Esta spec é pública — a própria spec nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`sqli-second-order — Second-order SQL injection`, grafia exata confirmável na Fase 2). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (SQL injection, second-order, payload, parameterized query, placeholder, sink, source, trust boundary, takeover) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (SQL injection), nome da página preservado em inglês no PT. **Confirmar a URL/âncora por fetch na Fase 2** — não inventar.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 29: `sqli-second-order` — Second-order SQL injection: a username registered through a safe parameterized INSERT is later re-read from the DB and concatenated raw into a second query (a change-password UPDATE), so a payload username planted at registration detonates in the second flow — rewriting which row the UPDATE hits and taking over another account (A03 Injection). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 29 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–14; reproduzir baseline → plantar (inócuo) → detonar → `admin` tomado no vulnerable → nada escapa no fixed, capturando o `UPDATE` real. Portas host podem não ser alcançáveis do sandbox — ver a memória `validating-atoms-via-docker-exec` (fallback: `docker exec` + dirigir o app/DB de dentro do container). **Sem** browser (a prova é a resposta do login).
- **Commits sem trailer `Co-Authored-By`** (memória `commit-no-coauthor-trailer` — a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8029` (vulnerable), `127.0.0.1:8129` (fixed). Bind **só** `127.0.0.1`. Single-container por lado (2 serviços, sem datastore).
- Se houver dúvida sobre a string exata do payload, o comportamento do `sqlite3` (stacked queries), o mecanismo de sessão, a forma da prova, ou a URL/âncora/H1 do primer, ou se o ataque não reproduzir, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF:**

- **`sqli-second-order-reread-concat`** — *"O átomo `sqli-second-order` (29, A03, reaproveita `atoms/A03-injection/`): second-order SQL injection single-container Flask+SQLite (molde do 01). Dois fluxos: `POST /register` grava o username por `INSERT ... VALUES (?, ?)` PARAMETRIZADO (plantar, inócuo — atacar o cadastro direto não faz nada); `POST /change-password` (autenticado por sessão Flask) RELÊ o username do banco e o CONCATENA cru numa 2ª query `f\"UPDATE users SET password = ? WHERE username = '{uname}'\"` (detonar). Só o `uname` relido é concatenado; o `new_password` fresco é parametrizado nos dois lados. Payload = `username='admin'--'` → o `UPDATE` vira `... WHERE username='admin'` (o `--'` comenta o resto) → troca a senha do `admin` (takeover), provado logando como admin com a senha nova. NÃO stacked-query (sqlite3.execute proíbe múltiplos statements) — é subversão de WHERE. Fix = parametrizar a 2ª query (`WHERE username = ?`), no servidor — NÃO sanitizar/validar o username no cadastro (nota-armadilha #2: a proteção não viaja com o dado; charset-blocklist é frágil), NÃO 'parametrizei na entrada tô seguro'. Sem Saída B (o placeholder `?` existe e o app o usa em todo lugar; o bug é não usá-lo na 2ª query). API-only JSON, Burp-only (prova = resposta HTTP, sem browser). Single-container: 2 serviços (vulnerable 8029 + fixed 8129), SQLite efêmero GRAVÁVEL por container (register INSERT + change-password UPDATE); `./atom down/up` reseta o banco. Sessão Flask assinada liga o 2º fluxo ao próprio usuário (sem IDOR). Contraste central = 01 (SQLi 1ª ordem): mesma A03/motor/FIX, o que muda é ordem/tempo (entra-e-detona vs planta-e-detona-depois; o ponto de entrada testa como seguro)."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão. *(Ortogonal: a memória relevante na Fase 2 é `validating-atoms-via-docker-exec` — o fallback de dirigir o app/DB de dentro do container; a de datastore-compose e as de client-side/headless **não se aplicam** — este átomo é single-container SQLite e Burp-only sem browser.)*
