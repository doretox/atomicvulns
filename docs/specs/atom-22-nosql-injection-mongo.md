# Spec — Átomo 22: `nosql-injection-mongo`

> Documento de especificação para o Claude Code implementar o átomo `nosql-injection-mongo` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A03 (Injection)**: a pasta `atoms/A03-injection/` já contém `sqli-union-basic`, `sqli-blind-boolean`, `sqli-blind-time`, `xss-reflected`, `xss-stored`, `command-injection-basic`, `ssti-jinja` e `xss-dom`. O 22 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos, ex.: a pasta do `sqli-union-basic`). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É MULTI-CONTAINER — o PRIMEIRO átomo do repo com um DATASTORE de verdade.** MongoDB é um **servidor** (não um arquivo embutido como o SQLite dos irmãos SQLi), então o compose tem **TRÊS serviços**: um `mongo` **compartilhado** + `vulnerable` + `fixed`. O molde de topologia multi-serviço vem dos átomos publicados `ssrf-blind-oob` (16) e `ssrf-cloud-metadata` (17) — um serviço extra **construído**, **sem porta no host**, alcançável **por nome** na rede interna do compose.
>
> **A lição em uma linha:** no **NoSQL injection** do MongoDB, uma query **NÃO é uma string — é um objeto/documento**. O app espera que `username`/`password` sejam **strings** e os joga direto no **filtro** da query. O atacante manda, no lugar de uma string, um **objeto** carregando um **operador** do Mongo — `{"password": {"$ne": null}}` (*"password diferente de `null`"*). A query vira `find_one({username:"admin", password:{$ne:null}})` e casa com o usuário `admin` **sem saber a senha**. A raiz é **CONFUSÃO DE TIPO**: esperava-se um escalar, entrou um objeto, e o objeto virou **estrutura/operador** da query. O fix é **forçar o TIPO** — garantir que o valor é `string` antes de chegar na query.
>
> **NÃO há "Saída B" aqui** (como no `19 ssti-jinja` e no `20 deserialization-pickle`). O `pymongo` **não coage tipo**: ele passa o `dict` **fielmente** como documento de query, então o código ingênuo (`find_one({...})` com o input cru) é **diretamente** o bug — não existe uma ferramenta padrão que "resista" e obrigue a modelar um componente especial. O átomo é **uso-direto-do-antipadrão**. **NÃO inventar uma Saída B.** (Confirmar por probe o comportamento `get_json()`/`pymongo` na Fase 2 antes de escrever — risco #3.)
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha primária Burp; **AQUI é API-only e SEM exceção de browser**: o vetor é editar o corpo JSON no Repeater e ver o login passar, **não** há execução no browser — Nota de planning 3; §3.4 — datastore: **MongoDB** é a exceção explícita para NoSQL; §4 — pasta/categoria; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A03 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind `127.0.0.1`** nos apps, o **Mongo SEM porta no host**, dados fake, payload benigno; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** e os irmãos **`sqli-blind-boolean` (06)** e **`sqli-blind-time` (07)** publicados (o **CONTRASTE central**: mesma classe A03, mesmo teto de bypass/subversão de query, **mecanismo e fix DIFERENTES** — ver "Contraste com o SQLi"; citáveis à vontade), o **`bola-rest` (12)** (molde do átomo **API-only** — sem `templates/`, respostas `jsonify`, corpo JSON no `POST`, trilha 100% Burp Repeater), e os **dois publicados mais recentes — `xss-dom` (21)** e **`deserialization-pickle` (20)** (a **VOZ/estrutura ATUAL**: abertura seca, termo definido, título=classe, "sem Saída B", padrão da nota **"mencionável, não aplicada"**). **ATENÇÃO: NÃO copiar do `xss-dom` (21) a exceção de browser / trilha browser** — lá a prova exige JavaScript executando no cliente; **aqui é Burp-only** (o vetor e a prova vivem no corpo JSON da request e na resposta do login).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, `mongo/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml`, `mongo-init.js` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A03 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). Justificativa do ROADMAP para este átomo: *"contraparte moderna do SQLi, com sintaxe própria (`$ne`, `$gt`). Único átomo da fase que introduz MongoDB."*
>
> **A categoria A03 JÁ EXISTE — o 22 reaproveita a pasta.** Diferente do `15 session-fixation` (criou `A07-*`), do `18 xxe-basic` (criou `A05-*`) e do `20 deserialization-pickle` (criou `A08-*`), o 22 **não cria categoria**: `atoms/A03-injection/` já existe e já hospeda os quatro átomos de injection "clássica" (SQLi ×3, command injection), os três XSS e o SSTI. **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A03-injection/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A03-injection/nosql-injection-mongo/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A03 — Injection"**.
>
> **Rótulo A03 SEM arqueologia (`CLAUDE.md` §5, regra atual).** NoSQL injection é **A03 — Injection** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria do SQLi. **NÃO** relatar em que número injection caía em edições antigas (era A1 em 2017; **não contar isso** — é ruído histórico proibido pela regra atual). **Situar apenas: isto é A03 — Injection.** Explicar **por que** NoSQLi é injection (dado não-confiável cai num interpretador/motor de query que o trata como **estrutura/operador**) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar a versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase. **CRÍTICO (FORESHADOW, §5):** o átomo se descreve **isolado**. **NÃO** anunciar versão/release, **NÃO** dizer "abre a fase"/"segundo da fase"/"próxima fase", **NÃO** foreshadowar átomos futuros (a posição vive só no `ROADMAP.md`). Esta spec é commitada no repo público, então **a própria spec nasce limpa**: onde precisar situar posição, aponta para o `ROADMAP.md`; nas frases que proíbem foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).

## Nota de planning 3 — convenções ATUAIS: API-only, **Burp-only, SEM exceção de browser**

> Seguir o `CLAUDE.md` **atual**. Divergências concretas a fixar:
>
> - **API-only (`CLAUDE.md` §3.3).** O vetor é o **corpo JSON** de `POST /login` — o payload é um **objeto** aninhado, que só existe em JSON. **Sem `templates/`, sem `render_template`, sem browser.** Respostas em `application/json` via `jsonify`. Molde direto do **`bola-rest` (12)**, o átomo API-only publicado (adaptar a estrutura de WALKTHROUGH: request-baseline no Repeater, sem UI-baseline). **DIDÁTICO E DE CORREÇÃO:** um `<form>` HTML **NÃO reproduz** a vuln — `request.form`/`request.args` entregam **strings** no Flask; o clássico `password[$ne]=` é comportamento de Express/PHP, **não** de Flask. O vetor JSON **não é estético**: é **onde a vuln se manifesta nessa stack**. (Confirmar por probe na Fase 2 — risco #6.)
> - **Burp-only — SEM trilha browser, e SEM a exceção client-side do `xss-dom` (21).** No 21, a prova exigia **JavaScript executando no browser**, então o browser entrava na trilha principal. **Aqui NÃO há execução client-side**: o payload é montado no **corpo JSON** no Repeater, e a prova é a **resposta do login** (`authenticated: true` como `admin`). A trilha é **100% Burp (Repeater)**, com `curl` como equivalente. **NÃO usar a exceção de browser; NÃO criar trilha browser.**
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (login que recebe JSON) e a falha (o input vira operador de query). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** NoSQL injection, operador (`$ne`), documento/filtro de query, confusão de tipo, escalar — dar a expansão/definição na estreia. O átomo é pra quem **não** conhece a vuln.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** ("NoSQL Injection"), **NÃO** o motor ("...em MongoDB"/"...via `$ne`"/"...com pymongo"). O **slug** (`nosql-injection-mongo`) qualifica a variante — isso é OK (como `sqli-union-basic`). O motor (MongoDB/`$ne`/`pymongo`) aparece no **corpo**, não no H1.
> - **A03 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — topologia multi-container e o SEED do Mongo (primeiro datastore de verdade)

> **Primeiro átomo com um datastore-servidor.** Todos os átomos anteriores ou não têm storage, ou usam **SQLite** (arquivo embutido no processo — os SQLi 01/06/07). MongoDB é um **serviço à parte**, então este é o **primeiro compose multi-serviço com um banco compartilhado**. O precedente de topologia é o **`ssrf-blind-oob` (16)** e o **`ssrf-cloud-metadata` (17)**: um serviço extra que é **`build:`-ado**, **sem `ports:`** (só rede interna), alcançável **por nome** pelos apps. Aqui o serviço extra é o `mongo`, e ele é **compartilhado** por `vulnerable` e `fixed` (parte da lição: **mesmo banco, mesmos dados; só o tratamento de input difere** — ambos os apps só **leem**, `find_one`, nada destrutivo, então compartilhar é seguro, §8).
>
> **§8 — o Mongo NÃO tem porta no host.** Só `vulnerable` (`127.0.0.1:8022`) e `fixed` (`127.0.0.1:8122`) publicam porta, **só** em `127.0.0.1`. O `mongo` fica **exclusivamente** na rede interna do compose (`mongodb://mongo:27017/…`), inacessível do host. Isso **evita** um daemon de banco aberto na máquina do aluno.
>
> **SEED via script em `/docker-entrypoint-initdb.d/` — mecanismo LOCKED; a ENTREGA do script precisa de decisão na Fase 2 (SINALIZADO).** A imagem oficial do Mongo roda qualquer `*.js` colocado em `/docker-entrypoint-initdb.d/` **no primeiro init** (data dir vazio). O `mongo-init.js` semeia a coleção `users`. **Como o arquivo chega lá** tem duas vias, e há um risco de ambiente conhecido:
> - **(via A — RECOMENDADA, à prova de SELinux) imagem `mongo` fina `build:`-ada.** Um `mongo/Dockerfile` = `FROM mongo:<tag>` + `COPY mongo-init.js /docker-entrypoint-initdb.d/`. **Casa com o precedente do repo** (o `oob-listener` do 16 e o `metadata-mock` do 17 são serviços **construídos**, não imagens off-the-shelf com bind mount) e **elimina o bind mount**.
> - **(via B — mais simples, mas ARRISCADA neste host) bind mount** do `mongo-init.js` para `/docker-entrypoint-initdb.d/` no `docker-compose.yml`. **RISCO REGISTRADO:** a validação roda em **Fedora com SELinux**, que **bloqueia bind mounts** para dentro de containers (a memória de validação do projeto documenta isso — *"Fedora SELinux blocks bind mounts, even `:z`"*). Se a Fase 2 for por bind mount, **confirmar** que o seed carrega sob SELinux; se não carregar, cair na via A.
>
> **Recomendação:** implementar a **via A** (imagem `mongo` `build:`-ada com `COPY`), que é a única garantida no host de validação e segue o precedente do repo. O mecanismo pedido ("`mongo-init.js` em `/docker-entrypoint-initdb.d/`") é **preservado** — só muda **como** o arquivo aterrissa lá. **Decisão final: CONFIRMAR NA FASE 2** (risco #8). Sem volume persistente: o seed re-roda a cada `up` limpo (dados efêmeros de lab; restart re-semeia).

---

## Identidade

- **ID:** `nosql-injection-mongo`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A03 — Injection**. Pasta `atoms/A03-injection/` (**JÁ EXISTE — o 22 reaproveita**). Confirmado contra o `ROADMAP.md` ("A03 Injection") e o `CLAUDE.md` §4. Em prosa, usar o nome da classe — **"NoSQL Injection"** — e a categoria — **"A03 — Injection"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A03-injection/nosql-injection-mongo/`
- **Número sequencial:** 22
- **Porta vulnerable:** `127.0.0.1:8022`
- **Porta fixed:** `127.0.0.1:8122`
- **Serviço `mongo`:** **SEM porta no host** — só rede interna do compose, alcançável por `mongodb://mongo:27017/…`.
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers dos apps rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos. O `mongo` **não** publica porta.
- **Topologia:** **MULTI-CONTAINER — TRÊS serviços:** `mongo` (compartilhado, sem porta no host) + `vulnerable` + `fixed`. Molde de rede do `ssrf-blind-oob` (16) / `ssrf-cloud-metadata` (17) — serviço extra `build:`-ado, sem `ports:`, por nome na rede interna. **Ambos os apps leem o MESMO `mongo` semeado.**
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos** (§5 foreshadow).
- **Branch de trabalho:** `atom/nosql-injection-mongo`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de NoSQL injection** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/nosql-injection`** (título/grafia esperados: **"NoSQL injection"**; abertura conceitual com operadores `$ne`/`$gt` e a distinção operator-injection vs syntax-injection). **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# nosql-injection-mongo — NoSQL Injection`** — `id` + nome canônico da **classe** em inglês (forma paralela à dos irmãos: `01` usa "SQL Injection (UNION-based)", `12` usa "Broken Object Level Authorization (BOLA)"). **SEM** "MongoDB"/"`$ne`"/"pymongo" no H1 (o slug já carrega "mongo"). Grafia canônica exata **confirmável na Fase 2** (casar com o título da página PortSwigger — pode ser "NoSQL injection"); **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**NoSQL injection no MongoDB — uma query é um DOCUMENTO, não uma string.** Um endpoint de login recebe `username`/`password` e monta um **filtro de query** — o documento que descreve *quais* registros casar. O app espera que os dois campos sejam **strings** (valores escalares) e os joga **direto** no filtro: `find_one({"username": username, "password": password})`. O `pymongo` (o driver Python do MongoDB) **não é** um construtor de string SQL — ele serializa o `dict` Python **como documento** e o envia ao servidor. Então, se `password` chega **não** como a string `"senha"` mas como o **objeto** `{"$ne": null}`, o filtro vira `{username:"admin", password:{$ne:null}}` — e `$ne` é um **operador** do Mongo (*"$ne" = "not equal"*, "diferente de"). O servidor casa qualquer documento cujo `password` seja **diferente de `null`** — ou seja, **qualquer usuário com senha** — e o login de `admin` passa **sem a senha**. O input não injetou *sintaxe* numa string: injetou uma **estrutura** (um operador) trocando o **tipo** do valor.

### A lição-coração

> **"No NoSQL injection do MongoDB, uma query NÃO é uma string — é um objeto/documento. O app espera que `username`/`password` sejam STRINGS e os joga direto no filtro da query. O atacante manda, no lugar de uma string, um OBJETO carregando um OPERADOR do Mongo: `{"password": {"$ne": null}}` ('password diferente de null'). A query vira `find_one({username:"admin", password:{$ne:null}})` e casa com o usuário admin — login como admin SEM saber a senha. A raiz é CONFUSÃO DE TIPO: esperava-se um escalar, entrou um objeto, e o objeto virou ESTRUTURA/OPERADOR da query. O fix é forçar o TIPO — garantir que o valor é string antes de chegar na query."**

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas #1/#3 do DIFF)

**A raiz NÃO é "escapar" nem "parametrizar" — é o TIPO do input.** Este é o mal-entendido que o átomo desarma. O `pymongo` **não concatena string**: ele já passa o valor como parte de um **documento** — no sentido do SQL, isso é o equivalente a uma query **"parametrizada"** (o valor não é interpolado num texto de comando). **E mesmo assim é vulnerável**, porque a injeção **não é por sintaxe de string** (quebrar aspas, comentar o resto, `UNION`) — é por **tipo/estrutura**: o atacante troca um **escalar** (string) por um **objeto** que o driver passa fielmente, e esse objeto **é** um operador de query. A defesa que salva do SQLi (parametrizar/bind vars) **não tem análogo que pegue isto** — o `pymongo` já é "parametrizado" e continua vulnerável. A correção mora **um passo antes da query**: **garantir o tipo** (o valor tem que ser `string`); um objeto/operador **nunca** pode alcançar o filtro.

### Por que A03 (Injection)

NoSQL injection é **A03 — Injection**, a mesma categoria do SQLi. O eixo de injection é: **dado não-confiável cai num interpretador que o trata como código/estrutura, não como dado inerte.** No SQLi o "interpretador" é o **parser de SQL**, e o dado vira **sintaxe** de comando. No NoSQLi do Mongo o "interpretador" é o **motor de avaliação de query** do MongoDB, e o dado vira **estrutura de documento** — um **operador** (`$ne`, `$gt`, `$regex`, `$where`). Mesma família (input não-confiável → interpretador que o executa), **mesmo teto de impacto** neste átomo (subverter a query → bypass de autenticação) — só muda **o que** é injetado (estrutura/operador, não sintaxe de string) e, por consequência, **onde mora o fix** (forçar o tipo, não parametrizar). Situar em **A03 — Injection**, **sem** contar edições antigas.

---

## Contraste com o SQLi (`01`/`06`/`07`) — CRÍTICO (é o que justifica o átomo existir)

Os quatro são **A03 — Injection** (dado não-confiável vira lógica de query) e têm o **MESMO teto** (subversão da query / bypass de autenticação). O que **DIFERE** — e o que faz o 22 não ser "o SQLi de novo" — é **o que é injetado** e **onde mora o fix**. Cravar no WALKTHROUGH e no DIFF (tabela + prosa):

| Eixo | SQL injection (`01`/`06`/`07`) | NoSQL injection (`22`) |
|---|---|---|
| **Categoria OWASP** | A03 — Injection | A03 — Injection |
| **Teto de impacto** | subversão da query (exfil / bypass de auth) | subversão da query (**bypass de auth**) — mesmo teto |
| **O que é injetado** | **SINTAXE** dentro de uma **STRING** SQL (quebra de aspas, `UNION`, `OR 1=1`) | um **OPERADOR** que troca o **TIPO** do valor (escalar → objeto): `{"$ne": null}` |
| **Como a query é construída** | **CONCATENAÇÃO** de string (`f"... WHERE username = '{u}'"`) | o `pymongo` passa um **`dict` como DOCUMENTO** de query — **sem concatenar string** |
| **O fix** | query **PARAMETRIZADA** (bind vars: `execute("... = ?", (u,))`) | **FORÇAR O TIPO** (rejeitar não-string antes da query) |
| **A parametrização do SQL mapeia aqui?** | — | **NÃO** — o `pymongo` **já é** parametrizado (passa o `dict` fielmente) e **continua vulnerável** |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante):** a **parametrização** que fecha o SQLi **NÃO MAPEIA** aqui. No SQLi, o bug é o valor ser **interpolado numa string de comando**; parametrizar separa "comando" de "dado" e mata a injeção. No NoSQLi do Mongo **não há string de comando pra interpolar** — o `pymongo` já entrega o valor como parte de um documento (o análogo de "parametrizado"), e a injeção acontece **por o valor mudar de tipo** (string → objeto-operador). Então o instinto "é injection, é só parametrizar/escapar como no SQLi" **erra o alvo**. O fix certo é **de tipo**, não de sintaxe. *(Comparar com o código real dos irmãos: `01` vulnerable concatena — `f"SELECT ... WHERE username = '{username}'"`; `01` fixed parametriza — `execute("... WHERE username = ?", (username,))`. O `22` **já nasce** no equivalente do "fixed do SQLi" — dict/documento, sem concatenar — e **ainda assim** é vulnerável. Essa é a foto que justifica o átomo.)*

**"Um átomo = uma vuln" se refere à CAUSA, não ao teto de impacto** (`CLAUDE.md` §2). Assim como a trilogia SQLi (01/06/07) é "uma causa, três canais de exfil", o `22` é a **mesma família de injection por teto de impacto, mas de causa/mecanismo/fix distintos** do SQLi. Citar `01`/`06`/`07` (publicados) à vontade — o aluno abre os dois e compara: *"mesmo teto (subverter a query), mas o que entra aqui é um operador que troca o tipo, e o fix é forçar o tipo, não parametrizar."*

---

## Flavor — login que recebe JSON (`POST /login`) — TRAVADO

Um endpoint de **login** que recebe o corpo em **JSON**. `request.get_json()` parseia `{"username":"admin","password":{"$ne":null}}` num **`dict` aninhado**, e o `password` (agora um **objeto**, não uma string) cai **direto** no filtro da query. **Superfície = o corpo JSON de `POST /login`.** Uma única rota injetável; **sem** segundo endpoint, **sem** segunda superfície.

**Por que JSON (didático E de correção — não é escolha estética):**

- **`<form>` HTML NÃO reproduz.** `request.form.get("password")` no Flask entrega **sempre uma string** — não há como um `<input>` de formulário virar um objeto aninhado. Um form transformaria o payload `{"$ne":null}` na **string literal** `'{"$ne":null}'`, que casaria (ou não) como um **valor**, nunca como operador. Por isso o átomo é **API-only** (sem HTML): o vetor **exige** um corpo JSON.
- **Query-string também NÃO reproduz.** `request.args.get("password")` também entrega **string**. O clássico `password[$ne]=` que vira objeto é comportamento de **Express (Node)/PHP** (que fazem parsing de bracket-notation em query/form), **NÃO** de Flask. Registrar isso: numa stack Node, o mesmo bug aparece via form/query; **em Flask, é via JSON** — e é por isso que o átomo modela o vetor JSON.
- **Consequência:** o vetor JSON é **onde a vuln se manifesta nessa stack**. Confirmar por probe (Fase 2, risco #3/#6): que `get_json()` entrega o `dict` **aninhado**, que o `pymongo` trata `{"$ne":null}` como **operador** (não como match literal num campo chamado `"$ne"`), e que `request.form`/`request.args` **não** reproduzem (entregam string).

---

## Payload-prova — BYPASS DE AUTENTICAÇÃO (TRAVADO; §8)

**Payload primário:** `{"username":"admin","password":{"$ne":null}}` → **loga como `admin` sem a senha.**

- `username:"admin"` é uma **string** (casa o documento do `admin`); `password:{"$ne":null}` é um **objeto/operador** (`$ne` = "not equal") que casa **qualquer** valor de `password` **diferente de `null`**. Como o `admin` tem senha (string, não-null), o filtro casa o `admin` e o login passa **sem conhecer a senha**.
- **A prova é a RESPOSTA de login:** no `vulnerable` (8022) → `authenticated: true` / usuário `admin`; a **mesma** request no `fixed` (8122) → **`400`** (guard de tipo rejeita o não-string). **CONFIRMAR NA FASE 2 rodando** (risco #2/#4): capturar request/response reais dos dois lados. **Se não reproduzir, PARAR e avisar — NÃO inventar** a prova.

**Variante de cor (registrar, opcional):** `{"username":"admin","password":{"$gt":""}}` — `$gt` ("greater than") com `""` casa qualquer string de `password` maior que a string vazia (i.e., qualquer senha não-vazia). **Equivalente** ao `$ne:null` como bypass. **`$ne` é o operador canônico e mais claro** — usar como primário; `$gt:""` só como cor.

**Foco no bypass de auth.** Outras faces do NoSQLi — extração cega via `$regex` (adivinhar a senha caractere-a-caractere), injeção de JavaScript server-side via `$where` — são **descrição de UMA LINHA da CLASSE** (ver "Impacto honesto"). **NÃO modelar, NÃO foreshadowar** como átomo futuro.

**Regras §8, a cravar no WALKTHROUGH:**

- O payload é **benigno**: subverte a query pra **provar o bypass pela resposta de login** — **NADA** destrutivo (sem `drop`, sem `update`, sem `$where` com JS, sem escrita). Só um `find_one` que casa demais.
- Dados semeados são **fake** (usuário `admin` + um usuário comum, senhas dummy plaintext). Sem PII, sem segredo real.
- O lab é **isolado** (apps bind **só** `127.0.0.1`; o `mongo` **sem porta no host**; containers descartáveis). O WALKTHROUGH deixa **explícito** que é um lab local e o bypass é uma **prova de conceito benigna**.

---

## O código — o coração no `find_one` do `app.py`

O fix é **server-side** (no `app.py`) — como no SQLi (01), **diferente** do `xss-dom` (21), onde o fix vivia no `<script>` do template. O `app.py` **DIFERE** entre os lados (o guard de tipo vive no servidor).

### `vulnerable/app.py` — o `find_one` recebe o input cru (candidato — Fase 2 gera o real)

```python
import os
from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)
users = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017/")).labdb.users


@app.route("/")
def index():
    # Banner only -- the vuln lives in POST /login (see WALKTHROUGH).
    return jsonify({
        "warning": "Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login with a JSON body {\"username\": ..., \"password\": ...}. "
                "Work from Burp Repeater.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    # VULNERABLE: username/password go straight into the query filter. If password
    # is an object like {"$ne": null}, it becomes a Mongo OPERATOR ("not equal"),
    # not a value to match -- the filter matches any user with a password, so the
    # login succeeds without knowing it. A query here is a DOCUMENT, not a string.
    user = users.find_one({"username": username, "password": password})
    if user:
        return jsonify({"authenticated": True, "user": user["username"]})
    return jsonify({"authenticated": False}), 401
```

### `fixed/app.py` — MESMO código, com um GUARD DE TIPO antes da query (candidato)

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    # FIXED: force the type -- username and password must be strings. An object
    # carrying an operator (e.g. {"$ne": null}) is REJECTED before it can reach the
    # query filter, so it can never become query structure.
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "username and password must be strings"}), 400
    user = users.find_one({"username": username, "password": password})
    if user:
        return jsonify({"authenticated": True, "user": user["username"]})
    return jsonify({"authenticated": False}), 401
```

- **REJEITAR (`400`), NÃO coagir com `str()`.** Coagir (`str(password)`) **mascararia** a intenção do atacante (o objeto viraria a string `"{'$ne': None}"` e "funcionaria" silenciosamente); **rejeitar é o fix honesto** — diz "esse campo tem que ser uma string" e para ali. O DIFF explica a escolha.
- **O diff é o guard `isinstance`.** Só a rota `login` muda; o `GET /` (banner), os imports, a conexão com o `mongo`, `Dockerfile` e `requirements.txt` são **idênticos** entre os lados. **O `app.py` DIFERE** (o fix vive no servidor — como no 01, inverso do par XSS/DOM).
- **`get_json(silent=True) or {}`**: parse tolerante; corpo ausente/inválido → `{}` → `username`/`password` viram `None`. No `vulnerable`, `find_one({"username": None, "password": None})` simplesmente não casa (retorna `401`); no `fixed`, `None` não é `str` → `400`. Higiene, ortogonal ao bug. (Confirmar na Fase 2.)

---

## O fix e o tipo de diff

**Fix:** **forçar o TIPO** — `isinstance(...) == str` para `username` **e** `password`, rejeitando (`400`) qualquer não-string **antes** da query. Tipo de diff: **lógica-diferente** — o guard adicionado no `app.py`. Um objeto/operador **nunca** alcança o filtro.

Diff colável (candidato — a Fase 2 gera o real):

```diff
 @app.route("/login", methods=["POST"])
 def login():
     body = request.get_json(silent=True) or {}
     username = body.get("username")
     password = body.get("password")
-    # VULNERABLE: username/password go straight into the query filter. If password
-    # is an object like {"$ne": null}, it becomes a Mongo OPERATOR, not a value to
-    # match -- the filter matches any user, so login succeeds without the password.
+    # FIXED: force the type -- username and password must be strings. An object
+    # carrying an operator (e.g. {"$ne": null}) is REJECTED before it reaches the
+    # query filter, so it can never become query structure.
+    if not isinstance(username, str) or not isinstance(password, str):
+        return jsonify({"error": "username and password must be strings"}), 400
     user = users.find_one({"username": username, "password": password})
     if user:
         return jsonify({"authenticated": True, "user": user["username"]})
     return jsonify({"authenticated": False}), 401
```

**O CONTRASTE é o diff:** o vulnerable passa o input cru ao filtro (um objeto vira operador); o fixed **exige string** antes de chegar lá. A única mudança é o guard de tipo.

### Notas obrigatórias no `DIFF.md`

1. **PARAMETRIZAR / ESCAPAR NÃO É O FIX AQUI (nota-ADVERTÊNCIA curta e didática — "mencionável, não aplicada").** Enquadrar no molde do `19 ssti-jinja` ("a sandbox não é o fix") / `20 deserialization-pickle` (HMAC) / `21 xss-dom` (escapar no servidor não é o fix):
   - **(a) Nomear a intuição.** O aluno experiente vai pensar: *"é injection — é só parametrizar / escapar, como no SQLi."*
   - **(b) Mostrar que ERRA O ALVO.** Não há **concatenação de string** a parametrizar: o `pymongo` **já** passa o `dict` **fielmente** como documento de query (é o análogo do "parametrizado" do SQL) — e é **exatamente por isso** que o operador chega inteiro. A injeção é por **TIPO/estrutura**, não por sintaxe de string. **A parametrização do SQL não tem análogo que pegue isto.**
   - **(c) Cravar o fix real:** garantir o **tipo** (o valor tem que ser `string`), um passo antes da query. **CURTA** (a intuição + o porquê), **NÃO** uma seção gigante.
2. **BLOCKLIST DE CHAVES `$` NÃO É O FIX (remendo — curta).**
   - **(a) Nomear a intuição.** *"É só remover as chaves que começam com `$` do input."*
   - **(b) Mostrar que é blocklist frágil.** Blocklist persegue **formas** do ataque (aninhamento profundo, operadores fora da lista, variações de encoding), sempre um passo atrás. A raiz é **whitelist de TIPO**: o valor **tem que ser string** — aí não importa que chave o objeto teria, porque **nenhum** objeto passa. Whitelist de tipo fecha na causa; blocklist de chave remenda o sintoma.
3. **CONFUSÃO DE TIPO — escalar vs objeto (a causa em uma frase).** O perigo é o input **MUDAR DE TIPO** — de **escalar** (string, o que o app espera) para **objeto** (o que o driver interpreta como estrutura/operador de query). Forçar `string` fecha **na raiz**: sem objeto, não há operador. *(Nota curta e ortogonal: **hashing de senha NÃO é o fix de NoSQLi**. Um app que hasheia a senha e busca **por username** ainda pode ser NoSQLi **no filtro do username** — ex.: `{"username":{"$ne":null}}` casa o **primeiro** usuário da coleção e loga como ele. O hashing protege a senha em repouso, **não** o filtro de query. Mencionar, **NÃO** aplicar.)*
4. **IMPACTO: bypass de autenticação (account takeover); contraste com o SQLi.** Mesmo teto do bypass via SQLi (subverter a query pra logar sem credencial), por **mecanismo distinto** (operador que troca o tipo, não sintaxe numa string) e **fix distinto** (forçar o tipo, não parametrizar). Referir a tabela da seção "Contraste com o SQLi". **Sem foreshadow** (não nomear átomo/variante futura; outras faces do NoSQLi ficam em UMA linha de descrição da classe).

---

## Biblioteca / topologia

- **Apps (`vulnerable`/`fixed`): Flask + pymongo.** `requirements.txt` **idêntico** entre os dois:

```
Flask==3.0.0
pymongo==<pin a CONFIRMAR na Fase 2>
```

  - `Flask==3.0.0` casa com os irmãos. **`pymongo`**: registrar um pin de uma release estável 4.x (candidato a confirmar: `pymongo==4.6.1`). **NÃO é behavior-critical no sentido do `jwt-none-alg`**: a semântica de `{"$ne":null}` como operador é **comportamento do servidor MongoDB**, estável entre versões de driver — o pin é higiene, não invariante educacional. **Confirmar por probe** (Fase 2) que o pin escolhido trata `{"$ne":null}` como operador (não como match literal).
  - **Sem `requests`, sem ORM, sem 2ª dependência.** `pymongo` puro. **Dockerfile dos dois apps idêntico entre si** (com `pymongo` no `requirements.txt`; **sem** `COPY templates` — API-only). **Confirmar por probe** que `pymongo`/`Flask` instalam em `python:3.11-slim` (provavelmente wheel puro, sem toolchain — confirmar na Fase 2, risco #8).
- **Serviço `mongo` (compartilhado):** imagem **oficial** do MongoDB, **tag estável pinada** (candidato a confirmar: `mongo:7.0`). **SEM porta no host** (só rede interna). Alcançável pelos apps por **nome** — `MONGO_URL=mongodb://mongo:27017/` (o db `labdb`, coleção `users`). Entrega do seed: ver Nota de planning 4 (**via A recomendada**: `mongo/Dockerfile` = `FROM mongo:7.0` + `COPY mongo-init.js /docker-entrypoint-initdb.d/`).
- **Seed (`mongo-init.js`):** semeia a coleção `users` com um **`admin`** + um **usuário comum** (candidato: `alice`), **senhas PLAINTEXT** (simplificação de lab — ver "uma vuln só"; hashing seria uma 2ª preocupação ortogonal, nota #3 do DIFF). Candidato:

```javascript
// Seeded on first init. Plaintext passwords: lab simplification (see README /
// DIFF note #3 -- hashing is orthogonal to the NoSQLi fix). Fake data (CLAUDE.md §8).
db = db.getSiblingDB("labdb");
db.users.insertMany([
  { username: "admin", password: "s3cr3t-admin-pw" },
  { username: "alice", password: "alice-pw" }
]);
```

  - **Ambos os apps leem o MESMO `mongo` semeado** — é parte da lição (mesmo banco, mesmos dados; só o tratamento de input difere). Ambos só **leem** (`find_one`); nada escreve/dropa (§8). **Confirmar na Fase 2** (risco #10) que os dois apps enxergam o mesmo `admin`.
  - **Dado fake óbvio** (`CLAUDE.md` §8.3): usuário/senha dummy, sem PII, sem segredo real. A senha plaintext do `admin` é **visível no seed** (o aluno pode lê-la) — o **baseline** do walkthrough a usa pra mostrar a feature funcionando; o **ataque** loga **sem** ela.

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY** (o vetor é o **corpo JSON** no Repeater; `CLAUDE.md` §3.3 lista NoSQL como categoria naturalmente API-only quando modelada como endpoint REST). Garantir que a **ÚNICA** vuln é o `/login` aceitar um valor não-confiável que vira operador:

- **NÃO usar `<form>` HTML** — form vira **string** e **NÃO reproduz** a vuln (ver "Flavor"). **Sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (mais coerente com átomo API-only que um HTML mínimo; o `bola-rest` não tinha banner por não ter `GET /`, mas aqui o mantenedor pediu o banner explícito). Texto: *"Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network."* + dica de trabalhar pelo Burp Repeater. **O `GET /` não é injetável** — é só o banner; a única superfície é o `POST /login`.
- **A ÚNICA vuln é o `/login`.** **SEM** segundo endpoint injetável, **SEM** segunda superfície. **SEM Saída B** (o `pymongo` não coage tipo → o código ingênuo é diretamente o bug; **MAS confirmar por probe** o comportamento `get_json()`/`pymongo` antes de escrever — risco #3).
- **O `fixed` muda SÓ o guard de tipo** no `/login`. `GET /`, conexão, `Dockerfile`, `requirements.txt`, o serviço `mongo` e o seed são **idênticos** entre os lados.
- **Senha-no-filtro (plaintext) é simplificação NECESSÁRIA** pro shape canônico do bypass (`password` casado direto na query). Registrar como **ortogonal**: hashing **não** é o fix de NoSQLi (nota #3 do DIFF).

---

## WALKTHROUGH — abertura seca; Burp-only (`CLAUDE.md` §3.3, SEM exceção browser)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (login que recebe JSON) e a falha (o input vira operador de query). Trilha **100% Burp (Repeater)**, `curl` como equivalente; **SEM trilha browser** (a prova é a resposta do login, não execução no cliente — Nota de planning 3).

**Abertura (candidato — plantar a lição, seco):**

> *A app é um login que recebe as credenciais em JSON. Ela monta uma query no MongoDB pra achar o usuário: `find_one({"username": ..., "password": ...})`. O detalhe que a torna explorável: no MongoDB uma query **não é uma string de comando — é um documento**, um objeto com campos e (opcionalmente) **operadores**. O `/login` joga o que você mandou **direto** nesse documento. Se você mandar, no lugar da string da senha, o objeto `{"$ne": null}` — "diferente de null" —, o filtro passa a casar **qualquer** usuário com senha, e você loga como `admin` sem jamais saber a senha dele.*

Beats (molde do `20`/`21` publicado — abertura seca, seções numeradas `## 1..7`; adaptar do `bola-rest` (12) a forma request-baseline no Repeater, sem browser):

1. **Context.** Login que recebe JSON; `POST /login` monta `find_one({"username":..., "password":...})` no MongoDB. Definir na estreia: **NoSQL injection** (injection contra um banco NoSQL — aqui MongoDB — onde o input não-confiável vira **estrutura/operador** da query, não sintaxe de string), **filtro/documento de query** (o objeto que descreve *quais* registros casar — no Mongo é um documento, não uma string SQL), **operador** (uma chave especial do Mongo como `$ne` = "not equal"/"diferente de", que muda *como* o campo é comparado em vez de casar um valor literal), **escalar** (um valor único — string/número —, o que o campo *deveria* receber). Isto é **NoSQL injection**, sob **A03 — Injection**. Topologia: `mongo` compartilhado (sem porta no host) + `vulnerable` em `127.0.0.1:8022` + `fixed` em `127.0.0.1:8122`. Trilha 100% Burp/curl (API-only, sem browser).
2. **Spot the bug.** Mostrar a view vulnerable — `user = users.find_one({"username": username, "password": password})`, com `username`/`password` vindos direto de `request.get_json()`. Pergunta de auditoria: *"esse `password` que EU controlo cai num filtro de query — e se, no lugar de uma string, eu mandar um objeto com um operador?"* → o objeto vira **estrutura** da query. Grep barato pra esta classe: procurar input de request caindo direto num filtro de query (ex.: `grep -rn 'find_one\|find(' .` e ver se o valor veio do corpo sem checagem de tipo). Foreshadow do fix: **garantir o tipo** antes da query.
3. **Exploitation (Repeater — o payload é um OBJETO no corpo JSON; a prova é a resposta do login).**
   - **Baseline (feature benigna):** `POST /login` com `{"username":"admin","password":"s3cr3t-admin-pw"}` (a senha real, semeada — visível no `mongo-init.js`) → `authenticated: true`, usuário `admin`. O login funciona **com strings**. Bloco colável:
     ```
     POST /login HTTP/1.1
     Host: 127.0.0.1:8022
     Content-Type: application/json

     {"username": "admin", "password": "s3cr3t-admin-pw"}
     ```
   - **Montar o payload-objeto:** no lugar da **string** da senha, um **objeto** carregando um operador: `{"password": {"$ne": null}}`. Explicar `$ne` (`"not equal"` — casa qualquer valor **diferente** de `null`).
   - **Disparar:** `POST /login` com `{"username":"admin","password":{"$ne":null}}` → `authenticated: true`, usuário `admin` — **login como `admin` sem a senha**. Bloco:
     ```
     POST /login HTTP/1.1
     Host: 127.0.0.1:8022
     Content-Type: application/json

     {"username": "admin", "password": {"$ne": null}}
     ```
   - **§8 (cravar):** lab **isolado** (apps bind só `127.0.0.1`; `mongo` sem porta no host); o payload é **benigno** — só subverte o `find_one` pra provar o bypass pela resposta, **sem** escrita/drop. Num alvo real, NoSQLi vai de bypass de auth a extração de dados — **manter os payloads demonstrativos**.
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta o mal-entendido vizinho (o SQLi):
   - **NÃO é SQL injection de sintaxe.** Não há **quebra de aspas**, `UNION`, `OR 1=1`, nem string de comando: o payload é um **objeto JSON válido**, não sintaxe injetada num texto. *(Prova: mandar `' OR 1=1 --` como a **string** de `password` **não** loga — não há SQL nem concatenação; o que loga é o **objeto** `{"$ne":null}`.)*
   - **NÃO é um bug de escape.** Escapar caracteres (aspas, etc.) não faz sentido: o vetor não é um caractere perigoso numa string, é o **tipo** do valor (um objeto).
   - **NÃO é falta de parametrização.** O `pymongo` **JÁ** passa o valor como parte de um **documento** — o equivalente do "parametrizado" do SQL — e **mesmo assim** o operador passou. A parametrização que fecha o SQLi **não alcança** isto, porque a injeção é por **tipo/estrutura**, não por sintaxe de string.
   - **O que É:** **confusão de tipo** — o app esperava um **escalar** (string) e recebeu um **objeto**, que o driver passou fielmente e o Mongo interpretou como **operador**. A **única** correção é **forçar o tipo** (rejeitar não-string) antes da query.
5. **Impact (honesto — sem overclaim).** **Bypass de autenticação → account takeover:** logar como `admin` sem a senha dá acesso a tudo que o `admin` acessa (dado protegido no contexto da vítima). É o **mesmo teto** do bypass via SQLi, por **mecanismo distinto**. A classe NoSQLi tem **outras faces** — extração cega via `$regex`, injeção de JS server-side via `$where` — **descrição de UMA linha da classe**, **sem modelar nem foreshadowar**. Sem overclaim (não é RCE aqui), sem foreshadow.
6. **Why the fix works (porta 8122).** Repetir contra o `fixed/`:
   - A **MESMA** request (`{"username":"admin","password":{"$ne":null}}`) → **`400`** ("username and password must be strings"): o guard de tipo rejeita o **não-string** **antes** da query. Sem bypass.
   - **Prova de isolamento:** o baseline **com strings** (`{"username":"admin","password":"s3cr3t-admin-pw"}`) → `authenticated: true` **igual** nos dois lados. A **feature é idêntica**; só o **payload-objeto** separa o vulnerable do fixed.
   - **A lição do diff:** o fix **força o tipo** (rejeita não-string). **Parametrizar/escapar NÃO é o fix** (nota #1 — o `pymongo` já é "parametrizado" e ainda passou o operador); **blocklist de `$` é remendo** (nota #2 — a raiz é whitelist de tipo); **confusão de tipo** (nota #3 — escalar vs objeto). Mesmo teto do SQLi, mecanismo/fix diferentes (nota #4).

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado; a trilha é Burp/curl). Requests/responses são placeholders da execução real capturada na Fase 2. (Tokens não há; senhas são as semeadas, fixas no seed.)

---

## Impacto honesto

**Bypass de autenticação (account takeover).** O atacante loga como `admin` **sem a senha**, mandando um operador (`{"$ne":null}`) no lugar da string de senha; o filtro casa o `admin` e o login passa. Poder disso: **acesso ao que o `admin` acessa** — dado protegido, ações privilegiadas, no contexto da vítima. É o **mesmo teto** do bypass via SQL injection, por **mecanismo distinto** (operador que troca o tipo do valor, não sintaxe numa string de comando). **Sem overclaim:** neste átomo o finding é o **bypass de auth** — **não** inflar pra RCE (a injeção de JS via `$where`, que *poderia* levar a execução, **não** é modelada aqui). A classe NoSQLi tem **outras faces** (extração cega via `$regex`; `$where` com JS) — **UMA linha** de descrição da classe, **sem** modelar nem foreshadowar. A **prova do lab é benigna** (a resposta do login); a escalada é **descrita**, não armada (§8).

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A03 — átomo dentro de família publicada; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`sqli-union-basic` (01), `sqli-blind-boolean` (06), `sqli-blind-time` (07)** — o contraste **central** (seção dedicada + tabela). Mesma categoria (A03), mesmo teto (subverter a query / bypass de auth), **mecanismo e fix diferentes** (sintaxe-em-string + parametrizar vs operador-que-troca-o-tipo + forçar o tipo). **A parametrização que salva do SQLi não mapeia aqui** — é o ponto que justifica o átomo. Referência pra **trás**, permitida.
- **`bola-rest` (12)** — precedente do átomo **API-only** (banner/estrutura, corpo JSON no `POST`, trilha 100% Burp Repeater, sem browser). Molde de **forma**, não de conteúdo.
- **`command-injection-basic` (09), `ssti-jinja` (19)** — família "dado não-confiável cai num interpretador que o executa" (injection, A03). Citáveis **opcionalmente** pra ancorar que NoSQLi é injection e o eixo é input → interpretador; **não** central. O contraste que importa é com o SQLi.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5; e esta spec é pública):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante futura** por número, nome, slug **OU** descrição — inclusive os próximos átomos (a posição vive **só** no `ROADMAP.md`), **outras faces do NoSQLi** modeladas como átomo futuro, ou a posição/ordinal/release de fase.
- **PROIBIDO anunciar "abre a fase"/"segundo da fase"/"próxima fase"/versão.** O átomo — **e esta spec** — se descreve **isolado**. Nas frases que proíbem foreshadow, manter a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).
- **Que o NoSQLi tenha outras faces** (extração cega via `$regex`, JS via `$where`, o `{"$ne":null}` no filtro de **username**) é, no máximo, **descrição conceitual de UMA LINHA** ("o NoSQLi tem outras faces além do bypass de auth — o padrão é o mesmo: input não-confiável virando operador/estrutura de query") — **sem** nomear átomo/variante futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 22 vai até **bypass de autenticação via `{"$ne":null}` no filtro de `password`** (o finding), provado pela resposta do login. **Uma vuln, uma causa (confusão de tipo: input não-confiável vira operador de query), um fix (forçar o tipo, no servidor).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/nosql-injection`** — a página conceitual de NoSQL injection (título/grafia esperados **"NoSQL injection"**; abertura "What is NoSQL injection?" com os tipos — **syntax injection** vs **operator injection** — e os operadores `$ne`/`$gt`/`$where`/`$regex` como exemplos). É a página de introdução da vuln, não a de labs.
- **Texto do link:** **"NoSQL injection"** — a forma apresentada pela própria PortSwigger. Preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `sqli-union-basic`/`bola-rest`).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A03 — Injection** (`atoms/A03-injection/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `nosql-injection-mongo` em A03; `CLAUDE.md` §4 fixa a pasta. Situar em A03 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Topologia | **MULTI-CONTAINER — 3 serviços:** `mongo` (compartilhado, sem porta no host) + vulnerable + fixed | 1º datastore-servidor do repo. Molde de rede do `ssrf-blind-oob` (16)/`ssrf-cloud-metadata` (17). |
| Datastore | **MongoDB** (imagem oficial, tag estável — candidato `mongo:7.0`, confirmar) | `CLAUDE.md` §3.4: MongoDB é a exceção explícita para NoSQL. Sem porta no host (§8). |
| Entrega do seed | **Via A (recomendada): imagem `mongo` `build:`-ada com `COPY mongo-init.js /docker-entrypoint-initdb.d/`** | À prova de SELinux (memória de validação: bind mount bloqueado no host Fedora); casa com o precedente "serviço extra é build" do 16/17. Via B (bind mount) = fallback arriscado. **Confirmar na Fase 2.** |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe** (como no 19/20/21) | `pymongo` não coage tipo → passa o `dict` fielmente → o código ingênuo é diretamente o bug. **NÃO inventar Saída B.** |
| Lição-coração | **NoSQLi: a query é um DOCUMENTO; o input vira OPERADOR trocando o TIPO (escalar→objeto); fix = forçar o tipo, no servidor.** | O bug é **confusão de tipo**, não sintaxe de string. |
| Sub-lição crítica | **Parametrizar/escapar NÃO é o fix; `pymongo` já é "parametrizado" e ainda é vulnerável** | Desarma o instinto "é injection, é só parametrizar como no SQLi". A injeção é por tipo/estrutura. |
| Contraste central | **SQLi (01/06/07)** — mesma A03, mesmo teto, mecanismo/fix DIFERENTES | Justifica o átomo. "Um átomo = uma vuln" = causa, não teto de impacto. A parametrização do SQL **não mapeia**. |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | O vetor é o **corpo JSON**; form/query-string entregam string no Flask e **não** reproduzem. Molde do `bola-rest` (12). |
| Trilha | **100% Burp (Repeater) / curl; SEM browser** | Prova = resposta do login (não execução client-side). **NÃO** usar a exceção de browser do 21. |
| Flavor — **TRAVADO** | **Login JSON** (`POST /login`, corpo `{"username":...,"password":...}`) | `get_json()` entrega `dict` aninhado; o objeto no `password` vira operador. Superfície = o corpo JSON. |
| Payload-prova — **TRAVADO (confirmar exato na Fase 2)** | **`{"username":"admin","password":{"$ne":null}}`** (`$gt:""` como cor) | Loga como `admin` sem senha. `$ne` é o operador canônico e mais claro. Prova = resposta do login. |
| Código vulnerable | **`users.find_one({"username": username, "password": password})`** (input cru) | Objeto no `password` vira operador → casa qualquer usuário → bypass. |
| Código fixed | **Guard `if not isinstance(username, str) or not isinstance(password, str): return ..., 400`** | Força o tipo; um objeto/operador nunca alcança a query. **Rejeitar (400), NÃO coagir com `str()`.** |
| `app.py` vulnerable × fixed | **DIFERE** (só o guard de tipo na rota `login`) | O fix vive no servidor (como o 01, inverso do par XSS/DOM). |
| Fix (único eixo) | **Forçar o TIPO (rejeitar não-string) antes da query** | Correção na raiz (confusão de tipo). Não parametrizar, não blocklist de `$`. |
| Diff | **Lógica-diferente** — o guard `isinstance` no `app.py` | A linha perigosa é o `find_one` com input cru; o fix é o guard antes dela. |
| Parametrizar/escapar | **NÃO aplicar** (nota #1, "mencionável, não aplicada") | `pymongo` já é "parametrizado" e ainda é vulnerável; sem análogo que pegue tipo. Como sandbox (19)/HMAC (20)/escape-no-servidor (21). |
| Blocklist de `$` | **Mencionar, NÃO aplicar** (nota #2) | Remendo frágil (aninhamento/variações); a raiz é whitelist de tipo. |
| Hashing de senha | **Mencionar, NÃO aplicar** (nota #3) | Ortogonal ao NoSQLi (protege senha em repouso, não o filtro). Filtro de username ainda seria injetável. |
| Seed | **`admin` + usuário comum (`alice`), senhas PLAINTEXT fake** | Plaintext = simplificação necessária pro shape do bypass (password casado no filtro). Sem PII/segredo (§8). |
| Banco compartilhado | **Um `mongo`, lido pelos DOIS apps (só `find_one`, nada escreve)** | Parte da lição: mesmo banco/dados; só o tratamento de input difere. Seguro (só leitura, §8). |
| Bibliotecas | **`Flask==3.0.0` + `pymongo==<pin a confirmar>`** | Sem ORM/`requests`. `pymongo` não é behavior-critical (semântica do operador é do servidor Mongo). Confirmar pin/instalação. |
| Banner | **Obrigatório, num `GET /` JSON de aviso** (API-only) | `CLAUDE.md` §8.2. `GET /` não injetável; única superfície é `POST /login`. |
| Impacto | **Bypass de auth / account takeover.** Mesmo teto do SQLi, mecanismo/fix distintos. | Honesto; **não** inflar pra RCE. Sem foreshadow. |
| Theory primer | **PortSwigger "NoSQL injection"** (`/web-security/nosql-injection`, confirmar por fetch) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Título (H1) | **`nosql-injection-mongo — NoSQL Injection`** (classe, sem stack) | `CLAUDE.md` §5. Slug carrega a variante; H1 não leva "MongoDB"/"`$ne`"/"pymongo". |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública) | `CLAUDE.md` §5. Não nomear próximos átomos (só no `ROADMAP.md`)/posição/release/outras faces do NoSQLi como átomo futuro. |
| Portas | **8022 / 8122** (apps, bind só `127.0.0.1`); `mongo` **sem porta no host** | `CLAUDE.md` §8. Multi-container. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si** (molde dos irmãos, **API-only → SEM `COPY templates`**; **com `pymongo`** via `requirements.txt`):

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

`app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py` (idêntico aos irmãos).

**`mongo/Dockerfile`** (via A recomendada — Nota de planning 4; candidato, tag a confirmar):

```dockerfile
FROM mongo:7.0
COPY mongo-init.js /docker-entrypoint-initdb.d/
```

**`docker-compose.yml`** (candidato — 3 serviços; `mongo` **sem porta no host**; apps bind **só** `127.0.0.1`; rede interna compartilhada — molde do 16/17; a Fase 2 gera o real):

```yaml
services:
  mongo:
    build: ./mongo
    networks:
      - lab
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8022:5000"
    environment:
      - MONGO_URL=mongodb://mongo:27017/
    depends_on:
      - mongo
    networks:
      - lab
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8122:5000"
    environment:
      - MONGO_URL=mongodb://mongo:27017/
    depends_on:
      - mongo
    networks:
      - lab

networks:
  lab:
```

- **§8:** só `vulnerable`/`fixed` publicam porta, **só** em `127.0.0.1`. O `mongo` **não** tem `ports:` — inacessível do host.
- **`depends_on` não espera o Mongo ficar *pronto*** (só *iniciado*). O app deve **tolerar** o Mongo ainda subindo (o `MongoClient` do `pymongo` conecta lazy/reconecta; a 1ª request pode precisar de um retry). **Confirmar na Fase 2** (risco #8) que `./atom up nosql-injection-mongo` sobe os 3 e o login funciona após o Mongo semear. Se preciso, um healthcheck/retry mínimo — **decidir na Fase 2**, mantendo o código mínimo.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–7 são os centrais; 8–12 são higiene técnica. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **Baseline (feature funciona):** `POST /login` com credenciais válidas em **string** (`{"username":"admin","password":"s3cr3t-admin-pw"}`) → `authenticated: true` / `admin` nos **dois** lados.
2. **O ATAQUE (central — VALIDAR RODANDO):** `POST /login` com `{"username":"admin","password":{"$ne":null}}` → loga como `admin` (sem senha) no **vulnerable** (8022). **CAPTURAR request/response reais.** **Se não reproduzir, PARAR e avisar — NÃO inventar.**
3. **O MECANISMO (probe):** `get_json()` entrega o `dict` **aninhado** e o `pymongo` trata `{"$ne":null}` como **OPERADOR** (não como match literal num campo `"$ne"`). Confirmar rodando (e travar o payload exato).
4. **FIXED:** a **MESMA** request (`{"$ne":null}`) → **`400`** (guard `isinstance` rejeita o não-string); sem bypass. **CAPTURAR.** Baseline em string no fixed → `authenticated: true` (a feature segue).
5. **Prova de isolamento:** credenciais válidas **em string** funcionam **idêntico** nos dois lados; só o **payload-objeto** separa vulnerable de fixed.
6. **O vetor é JSON:** confirmar que **form/urlencoded NÃO reproduz** (`request.form`/`request.args` entregam **string** no Flask) — reforça por que o átomo é JSON/API-only. (`' OR 1=1 --` como string também **não** loga — não é SQL.)
7. **Uma vuln só:** **só** `POST /login` é injetável; `GET /` é só o banner (não injetável); **sem** 2º endpoint; o `fixed` muda **só** o guard de tipo. Confirmar que o WALKTHROUGH **não** empilha outra vuln.
8. **Topologia / rede / seed / §8:**
   - o serviço `mongo` **NÃO** tem porta no host (só rede interna); os apps bindam **só** `127.0.0.1` (8022/8122).
   - **entrega do seed sob SELinux (memória de validação):** implementar a **via A** (imagem `mongo` `build:`-ada com `COPY`), à prova de bind-mount-bloqueado no host Fedora; se optar pela via B (bind mount), **confirmar** que o seed carrega. Confirmar que `Flask`/`pymongo` instalam em `python:3.11-slim` (provável wheel puro, sem toolchain).
   - **readiness:** `depends_on` só espera *iniciar*; confirmar que o app tolera o Mongo subindo (retry/lazy connect) e que o login passa após o seed. `./atom up nosql-injection-mongo` sobe os **3** serviços sem erro.
9. **§8 — payload benigno:** o bypass é provado **pela resposta do login**; **NADA** destrutivo (sem `drop`/`update`/`$where`-JS/escrita); dados semeados **fake**; lab contido.
10. **Mongo compartilhado:** os **dois** apps leem o **MESMO** banco semeado (mesmo `admin`); ambos só **leem** (`find_one`). Confirmar que o db/coleção que os apps abrem (`labdb.users`) é o que o `mongo-init.js` semeia.
11. **`app.py` vulnerable × fixed:** o **ÚNICO** delta é o guard de tipo (`isinstance`) na rota `login`. `GET /`, imports, conexão, `Dockerfile`, `requirements.txt`, `mongo/` e o seed **idênticos** entre os lados. Confirmar por `diff`.
12. **Theory primer** confirmado **por fetch** (PortSwigger "NoSQL injection", `/web-security/nosql-injection`). Confirmar a **grafia exata do H1** ("NoSQL Injection" vs "NoSQL injection") contra a página. Se em dúvida, perguntar ao mantenedor. **Não inventar.**

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** reproduzir o ataque (itens 2–4); travar o payload exato e o comportamento `get_json()`/`pymongo` (item 3); decidir a entrega do seed sob SELinux (item 8, **via A recomendada**); confirmar a URL/H1 do primer por fetch (item 12); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é a **contraparte NoSQL do SQLi** e é **uso-direto-do-antipadrão** (sem Saída B). Cada beat deve poder ser lido com o **`sqli-union-basic` (01)** aberto ao lado, e a diferença ("mesmo teto — subverter a query —, mas aqui o que entra é um **operador** que troca o **tipo**, e o fix é **forçar o tipo**, não parametrizar; e o `pymongo` **já** é 'parametrizado' e ainda assim passou") deve estar visível na linha em discussão. **Abrir e fechar** na lição-coração: *a query é um documento; o input vira operador por confusão de tipo; o fix é garantir o tipo, no servidor.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`01` INTEIRO** (contraste central + molde de código/estrutura), **`06`/`07`** (os outros SQLi — mesmo teto, canais distintos; o contraste é a família), **`12` INTEIRO** (molde **API-only**: banner num `GET /`, corpo JSON no `POST`, `jsonify`, trilha 100% Burp Repeater, **sem** browser), **`20`/`21` publicados** (VOZ/estrutura atual — abertura seca, termo definido, título=classe, "sem Saída B", nota "mencionável não aplicada"). **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar do `21` a **exceção de browser / trilha browser** (aqui é Burp-only), nem encenação.
- **NÃO há Saída B (crítico):** o `pymongo` **não coage tipo** — passa o `dict` fielmente como documento —, então o `find_one({...})` com o input cru é **diretamente** o bug. **NÃO** inventar uma ruga de "a ferramenta padrão resiste". **MAS confirmar por probe** (`get_json()`/`pymongo`) **antes** de escrever (risco #3).
- **A prova é a RESPOSTA do login (riscos #2/#4), no Burp/curl — NÃO no browser.** Não há execução client-side. Capturar a cadeia real: vulnerable → `{"$ne":null}` → `authenticated: true` como `admin`; fixed → mesma request → `400`. **Se não bater rodando, PARAR e avisar — NÃO inventar** prova.
- **§8:** payload **benigno** (bypass provado pela resposta, **sem** escrita/drop/JS); apps bind **só** `127.0.0.1`; **`mongo` SEM porta no host**; dados semeados **fake**; lab contido. Enquadrar explicitamente no WALKTHROUGH.
- **A sutileza que NÃO pode enfraquecer a lição:** o **fixed força o TIPO** (rejeita não-string), **NÃO** parametriza (já é), **NÃO** faz blocklist de `$`, **NÃO** coage com `str()`. A defesa vive **um passo antes da query**, garantindo que o valor é escalar.
- **Uma vuln só:** foco no `find_one` com input cru no `POST /login`. `GET /` é **só** o banner (não injetável). **Sem** 2ª superfície, **sem** 2º endpoint injetável. O `fixed` muda **só** o guard de tipo.
- **API-only, Burp-only:** sem `templates/`, sem `render_template`, sem browser. Respostas `jsonify`. Banner obrigatório num `GET /` JSON. Trilha 100% Burp Repeater (`curl` equivalente). **NÃO** criar trilha browser (a prova é a resposta do login).
- **Abertura seca:** WALKTHROUGH entra direto na mecânica; **sem** encenação. Rotular os beats: **context (definir NoSQLi/filtro-documento/operador/escalar)** → **spot the bug (`find_one` com input cru)** → **exploitation (baseline string; payload-objeto `{"$ne":null}`; resposta do login)** → **o que a vuln NÃO é (não é SQLi de sintaxe/escape/parametrização)** → **impacto (bypass de auth)** → **fixed (mesma request → `400`; guard de tipo)**.
- **Impacto honesto:** **bypass de auth / account takeover**; **não** inflar pra RCE. Mesmo teto do SQLi, mecanismo/fix distintos. Sem overclaim, sem foreshadow.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é **confusão de tipo** (escalar→objeto→operador); **não é** SQLi de sintaxe (sem quebra de aspas/`UNION`/string de comando), **não é** bug de escape, **não é** falta de parametrização (o `pymongo` já é "parametrizado" e ainda passou o operador — a parametrização do SQL **não mapeia**).
- **Contraste com o SQLi (cravar):** tabela + prosa; mesma A03, mesmo teto, mecanismo/fix diferentes; **a parametrização do SQL não mapeia aqui**. Citar `01`/`06`/`07` (publicados) à vontade — mostrar que o `22` já nasce no equivalente do "fixed do SQLi" (dict/documento) e **ainda assim** é vulnerável.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** NoSQL injection, filtro/documento de query, operador (`$ne`), escalar, confusão de tipo.
- **A03 sem arqueologia:** situar em **A03 — Injection**, explicar **por que** NoSQLi é injection (input → motor de query que o trata como estrutura/operador), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `nosql-injection-mongo — NoSQL Injection`. "MongoDB"/"`$ne`"/"pymongo" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **01/06/07** (contraste SQLi central), **12** (molde API-only) e **opcionalmente 09/19** (família injection), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase e outras faces do NoSQLi como átomo futuro. **Manter as proibições genéricas** (sem listar nomes de átomos não-publicados). **Esta spec é pública — a própria spec nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`nosql-injection-mongo — NoSQL Injection`, grafia exata confirmável na Fase 2). Termos técnicos (NoSQL injection, operator, `$ne`/`$gt`, query filter/document, type confusion, payload, bypass, account takeover) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (NoSQL injection), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 22: `nosql-injection-mongo` — NoSQL Injection: a login endpoint passes untrusted JSON straight into a MongoDB query filter, so an object carrying an operator ({"$ne": null}) instead of a string logs in as admin without the password (A03 Injection). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 22 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline (string) → payload-objeto `{"$ne":null}` → `admin` no vulnerable → `400` no fixed. Portas host podem não ser alcançáveis do sandbox — ver a memória `validating-atoms-via-docker-exec` (fallback: `docker exec` + `python http.client` de dentro do container). **Sem** browser (a prova é a resposta do login).
- **Portas:** `127.0.0.1:8022` (vulnerable), `127.0.0.1:8122` (fixed). Bind **só** `127.0.0.1`. **`mongo` sem porta no host.** Multi-container (3 serviços).
- Se houver dúvida sobre a URL/H1 do primer, o payload exato que dispara, o comportamento `get_json()`/`pymongo`, a entrega do seed sob SELinux, ou se o ataque não reproduzir, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pro primeiro átomo com datastore-servidor):

- **`nosql-injection-mongo-type-confusion`** — *"O átomo `nosql-injection-mongo` (22, A03, reaproveita `atoms/A03-injection/`): NoSQLi via `users.find_one({"username": username, "password": password})` com o input cru de `request.get_json()`. Payload = OBJETO no lugar da string: `{"username":"admin","password":{"$ne":null}}` loga como admin sem a senha (o `$ne` vira operador). Raiz = CONFUSÃO DE TIPO (escalar→objeto→operador), NÃO sintaxe de string. Fix = guard de tipo no servidor (`isinstance(...) == str`, rejeita `400`), NÃO parametrizar (o `pymongo` já passa o dict fielmente = 'parametrizado' e ainda é vulnerável — nota-armadilha #1, como sandbox(19)/HMAC(20)/escape-no-servidor(21)). API-only (form/query-string entregam string no Flask e NÃO reproduzem; `password[$ne]=` é Express/PHP), Burp-only (prova = resposta do login, sem browser — NÃO usar a exceção do 21). Primeiro átomo multi-container com datastore de verdade: 3 serviços (mongo compartilhado SEM porta no host + vulnerable 8022 + fixed 8122), molde de rede do ssrf 16/17; seed via imagem mongo build-ada com COPY mongo-init.js (via A, à prova de SELinux) — NÃO bind mount. Contraste central = SQLi 01/06/07 (mesmo teto, mecanismo/fix diferentes; a parametrização não mapeia)."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão. *(Ortogonal: a lição de validação client-side/DOM headless — memória `validating-client-side-xss-atoms-headless` — **não se aplica** a este átomo, que é Burp-only sem browser; a memória relevante aqui é `validating-atoms-via-docker-exec`.)*
