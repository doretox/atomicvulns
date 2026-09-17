# Spec — Átomo 25: `mass-assignment`

> Documento de especificação para o Claude Code implementar o átomo `mass-assignment` do projeto `atomicvulns`. **Posição na ordem de implementação vive no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A01 (Broken Access Control)**: a pasta `atoms/A01-broken-access-control/` já contém `idor-numeric-id` (03), `path-traversal-basic` (10), `idor-uuid-guessable` (11), `bola-rest` (12), `csrf-basic` (23) e `open-redirect` (24). O 25 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão das irmãs, ex.: a pasta do `open-redirect`). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER, molde do `01 sqli-union-basic` / `24 open-redirect`** — só `vulnerable` + `fixed`, **sem** serviço extra, **sem** datastore, sem listener, sem rede especial. A conta demo vive **em memória** (um `dict`); a prova vive inteira na **resposta HTTP do próprio alvo**.
>
> **A lição em uma linha:** o app pega os campos que vieram na request e os **despeja EM BLOCO** num objeto (`account.update(<json do cliente>)`), **sem escolher QUAIS campos o usuário pode setar**. Funciona pros campos legítimos (`name`, `email`), mas o atacante **ADICIONA** um campo que nunca esteve no formulário — `role: "admin"` — e como o código copia tudo cegamente, esse campo entra junto e **vira privilégio**. A raiz: **confiança na FORMA do input** — o servidor deixa o **CLIENTE** decidir QUAIS atributos tocar, quando essa decisão é do **SERVIDOR**. O fix é o servidor definir explicitamente o conjunto de campos aceitáveis (**allowlist de campos**): só `name` e `email` entram, o resto é ignorado.
>
> **§3.3 — trilha Burp-only, E AQUI SEM a exceção client-side de browser (como no `24 open-redirect`, diferente do `21 xss-dom`/`23 csrf-basic`).** Mass assignment se prova na **REQUEST/RESPOSTA**: montar o `POST /profile` com o campo extra no **Repeater** (`curl` como equivalente), e ver o privilégio escalado no `GET /profile` (o `role` virou `admin`) e no `GET /admin` (que passou de `403` a `200`). **NÃO** há execução no browser (nenhum script roda), **NÃO** há cookie anexado, **NÃO** há vítima com browser que precise reproduzir o mecanismo. O ato **definidor** da vuln (o servidor copiar cegamente um campo controlado pelo cliente pra dentro do objeto) é **inteiramente server-side e visível na resposta**. Logo **NÃO usar** a exceção client-side nem qualquer "trilha browser".
>
> **NÃO há "Saída B" no sentido de "a ferramenta padrão resiste ao bug ingênuo"** (como havia no `14`/`15`/`18`/`23`): `dict.update(<json>)` é **diretamente** mal-usável — basta o dev confiar na forma do input; não há ORM com strong-params, nem schema-validation, nem nada "resistindo". **E, diferente do `24`, o comportamento técnico aqui NÃO é version-dependent:** `dict.update()` e `request.get_json()` são semântica **determinística e estável** de Python (o `update` copia **todas** as chaves do dict de origem; o `get_json` parseia o corpo JSON num dict). Não há surpresa de versão a resolver. **MESMO ASSIM, confirmar por probe** (validação de geração, `CLAUDE.md` §11) que o campo extra **de fato entra** no `vulnerable` e é **ignorado** no `fixed`, e **capturar a cadeia real** — ver "NÃO há Saída B — e o comportamento é DETERMINÍSTICO (probe = validação §11)" e o risco #2.
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha Burp-only**, e por que **aqui não há** exceção de browser; §3.4 — storage segue a superfície do bug: sem banco; §4 — pasta/categoria A01; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo técnico na 1ª ocorrência, situar em A01 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind `127.0.0.1`**, valores benignos; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico single-container e estrutura de WALKTHROUGH/DIFF), o **`open-redirect` (24) publicado** (o **CONTRASTE que AMARRA** — os dois são "allowlist server-side", o 24 de **DESTINO**, o 25 de **CAMPOS**; a mesma lição de A01 "o servidor decide, não o input", em superfícies diferentes; a mesma nota **allowlist-vs-blocklist**; e o molde estrutural: single-container + Burp-only + voz atual), o **`bola-rest` (12) publicado** (o molde de **átomo de API JSON** com conta/usuário em memória, sem HTML; e o **CONTRASTE** — BOLA = acessar objeto de OUTRO user, mass assignment = escalar privilégio no PRÓPRIO objeto via campo extra), e a família **A01** publicada (`idor-numeric-id` 03, `path-traversal-basic` 10, `idor-uuid-guessable` 11 = molde de átomo A01, eixo "o servidor permite algo fora do escopo"). Dos dois publicados mais recentes — **`open-redirect` (24)** e **`csrf-basic` (23)** — tirar a **VOZ/estrutura ATUAL** (abertura seca, termo definido, título=classe, spec nasce limpa). **ATENÇÃO: do 23 NÃO copiar a exceção de browser / a "trilha browser" — aqui é Burp-only puro, como o 24.**
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A01 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). A justificativa do ROADMAP para este átomo, na parte **não-foreshadow**, é: *"falha comum em APIs REST que aceitam JSON direto em ORM."*
>
> **A categoria A01 JÁ EXISTE — o 25 reaproveita a pasta.** Como fizeram o `csrf-basic` (23) e o `open-redirect` (24), e diferente dos átomos que criaram categoria nova, o 25 **não cria pasta**: `atoms/A01-broken-access-control/` já existe e hospeda `idor-numeric-id` (03), `path-traversal-basic` (10), `idor-uuid-guessable` (11), `bola-rest` (12), `csrf-basic` (23) e `open-redirect` (24). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A01-broken-access-control/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A01-broken-access-control/mass-assignment/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A01 — Broken Access Control"**.
>
> **Rótulo A01 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Mass assignment é **A01 — Broken Access Control** no OWASP Top 10 2021 (a edição que o projeto segue), mapeado ali via **CWE-915 (Improperly Controlled Modification of Dynamically-Determined Object Attributes** — o nome padrão de mass assignment). **NÃO** relatar em que número/edição a falha caía antes nem histórico de edições — é ruído proibido pela regra atual. **Situar apenas: isto é A01 — Broken Access Control (CWE-915).** Explicar **por que** é access control (o app executa uma modificação — setar um atributo do objeto, `role` — que o usuário **não deveria poder controlar**, porque o servidor não impõe controle nenhum sobre **quais** atributos o input pode tocar; a decisão de "quais campos deste objeto o usuário pode modificar" foi delegada ao input) é legítimo; contar edições **não**. *(Confirmar por fetch na Fase 2 o número exato do CWE — 915, ou o pai **CWE-913** — e o mapeamento A01:2021; ver "Theory primer" e o risco #9. NÃO inventar a grafia.)*

## Nota de planning 2 — versionamento/release fica FORA desta spec; e a DISCIPLINA DE FORESHADOW (a spec nasce limpa)

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase.
>
> **CRÍTICO (FORESHADOW, `CLAUDE.md` §5) — atenção redobrada, e esta spec É commitada no repo público, então a própria spec nasce limpa:** o átomo (e esta spec) se descreve **isolado**. **PROIBIDO** — no conteúdo do átomo E nesta spec — dizer que este átomo **"fecha a fase"/"fecha a categoria"/"último átomo"/"último da fase"/"próxima fase"**, nomear **milestone** ou **versão de release**, ou foreshadowar átomos futuros (nem por número, nem por slug, nem por descrição). Que a posição deste átomo no `ROADMAP.md` **calhe** de encerrar algo é **trabalho de release do mantenedor** — não é assunto do átomo nem desta spec. Onde precisar situar posição, **aponta para o `ROADMAP.md`**; nas frases que **proíbem** foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados). **Átomos publicados (a família A01 03/10/11/12, o 23 e o 24; e os recentes 23/24 pra voz) e o `ROADMAP.md` são citáveis à vontade.** O contexto de **ORM** que aparece em "O fix e o tipo de diff" (nota #2) é **descrição da CLASSE** (onde a falha é icônica), **não** referência a átomo futuro. *(Mesmo cuidado do 20, que encerrou a Fase 4 sem jamais anunciar isso no conteúdo.)*

## Nota de planning 3 — convenções ATUAIS: Burp-only SEM exceção de browser, abertura seca, título=classe, A01 sem arqueologia

> Seguir o `CLAUDE.md` **atual**. Pontos a fixar:
>
> - **§3.3 — Burp-only, SEM exceção client-side (como o 24, a diferença deliberada em relação ao 21/23).** A trilha é **só Burp Suite** (+ `curl` como equivalente). Mass assignment é **server-side observável**: a prova é (a) o `POST /profile` com o campo extra montado no **Repeater**, (b) o `GET /profile` mostrando `role: "admin"`, (c) o `GET /admin` que passou de `403` a `200`. **NÃO** há JS executando (não é o `21 xss-dom`), **NÃO** há cookie anexado por um browser (não é o `23 csrf-basic`) — logo **NÃO** existe "trilha browser" nem exceção client-side aqui. **NÃO criar seção de exploração via browser.**
> - **API-only (sem HTML), molde do `12 bola-rest`.** O `CLAUDE.md` §3.3 lista **"Mass assignment"** explicitamente entre as classes **naturalmente API-only** ("átomos naturalmente de API — sem HTML"). Sem `templates/`, sem `render_template`, sem browser; respostas em `application/json` via `jsonify`. Ver "Renderização / 'um átomo = uma vuln'".
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (atualização de perfil que recebe JSON) e a falha (o `account.update(<json>)` copia todos os campos). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** mass assignment (também "object injection" / "autobinding"), allowlist de campos (o conjunto explícito de campos que o servidor deixa o cliente setar), campo privilegiado/sensível (um campo que concede privilégio ou cruza uma fronteira de confiança se setado pelo usuário — `role`, `is_admin`, `verified`, `credits`), privilege escalation (aqui **vertical**: `user → admin`), ORM (Object-Relational Mapping — biblioteca que mapeia objetos pra linhas/colunas do banco), CWE (Common Weakness Enumeration, na estreia do CWE-915) — dar a expansão/definição na estreia. O átomo é pra quem **não** conhece a vuln.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** ("Mass Assignment"), **NÃO** o stack ("...em Flask"/"...via JSON"/"...com `role`"). O **slug** (`mass-assignment`) qualifica o átomo — OK (como `open-redirect`). O mecanismo (`account.update`, `get_json`, `role`) aparece no **corpo**, não no H1.
> - **A01 sem arqueologia** (Nota de planning 1).

---

## Identidade

- **ID:** `mass-assignment`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A01 — Broken Access Control** (via **CWE-915**). Pasta `atoms/A01-broken-access-control/` (**JÁ EXISTE — o 25 reaproveita**). Confirmado contra o `ROADMAP.md` ("A01 Broken Access Control") e o `CLAUDE.md` §4. Em prosa (README/WALKTHROUGH/DIFF) usar o nome da classe — **"Mass Assignment"** — e a categoria — **"A01 — Broken Access Control"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A01-broken-access-control/mass-assignment/`
- **Número sequencial:** 25
- **Porta `vulnerable`:** `127.0.0.1:8025` (TRAVADO)
- **Porta `fixed`:** `127.0.0.1:8125` (TRAVADO)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos single-container 01/12/24.
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM** serviço extra, listener, datastore, mock, ou rede especial. Molde do 01/24. Estado em memória (um `dict` de conta).
- **Tipo de átomo:** **API-only** (sem HTML, sem `templates/`, sem browser) — `CLAUDE.md` §3.3 lista "Mass assignment" como categoria naturalmente API-only. Molde do `bola-rest` (12). Respostas `application/json`.
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos, e ZERO menção de "fechar" fase/categoria** (§5 foreshadow, Nota de planning 2).
- **Branch de trabalho:** `atom/mass-assignment`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato + a ressalva; confirmar por fetch na Fase 2):** ver a seção "Theory primer". **Ponto de atenção:** mass assignment na PortSwigger aparece **dentro** do material de **API testing** (não é um "What is X?" de topo como SQLi/XSS/SSRF). **NÃO inventar URL — confirmar por fetch na Fase 2** e, se não houver página conceitual limpa na PortSwigger, **propor a melhor fonte (OWASP API Security Top 10) e avisar o mantenedor** — mesmo procedimento do open-redirect (24).
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# mass-assignment — Mass Assignment`** — `id` + nome canônico da **classe** em inglês (forma paralela às irmãs: `24` usa "Open Redirect"; a classe não tem acrônimo consagrado como BOLA/CSRF, então o H1 é só o nome). **SEM** "Flask"/"JSON"/"role" no H1. **CONFIRMAR a grafia exata na Fase 2** (casar com a fonte do primer: "Mass Assignment" é a grafia OWASP/PortSwigger). **Preservar o nome em inglês também no README PT.**

---

## Classe de vulnerabilidade

**Mass Assignment — o app faz *bind* em bloco dos campos da request num objeto, sem escolher quais campos o usuário pode setar.** Uma app tem uma feature de **atualização de perfil**: o cliente manda um corpo JSON com os campos da conta, e o app salva. O jeito preguiçoso de implementar isso é pegar o dict inteiro que veio no corpo e **despejá-lo no objeto da conta de uma vez** — `account.update(request.get_json())`. Funciona lindamente pros campos legítimos que o formulário oferece (`name`, `email`). A falha: o `update` copia **todas** as chaves do JSON, **inclusive as que não estavam no formulário**. O atacante adiciona ao JSON um **campo privilegiado** — `role: "admin"` — e, como o código copia tudo cegamente, esse campo entra na conta junto com os legítimos.

**Mass assignment** (também chamado de **"object injection"** ou **"autobinding"**) é exatamente esse padrão: o framework/código **liga automaticamente** os campos do input aos atributos de um objeto/modelo, **em massa**, sem uma lista do que o usuário tem permissão de setar. O nome vem de "atribuir (*assign*) em massa (*mass*)": um único `update`/`bind` seta muitos atributos de uma vez, a partir de dados que o cliente controla.

### A lição-coração

> **"O app pega os campos que vieram na request e os despeja EM BLOCO num objeto, sem escolher QUAIS campos o usuário pode setar. Funciona pros campos legítimos (`name`, `email`), mas o atacante ADICIONA um campo que não estava no formulário — `role: "admin"` — e como o código copia tudo cegamente, esse campo entra junto e vira privilégio. A raiz: confiança na FORMA do input — o servidor deixa o CLIENTE decidir QUAIS atributos tocar, quando essa decisão é do SERVIDOR. O fix é o servidor definir explicitamente o conjunto de campos aceitáveis (allowlist de campos): só `name` e `email` entram, o resto é ignorado."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** Atualizar o perfil é uma feature **legítima e comum**: o cliente manda os campos, o servidor salva. O erro não é aceitar JSON; é o **como**. Quando o dev escreve `account.update(<json>)`, ele está dizendo "seja qual for o conjunto de campos que o cliente mandar, aplique todos". O formulário oferece só `name` e `email`, então o dev *pensa* que só esses chegam — mas nada no código **impõe** isso. O atacante não precisa quebrar sintaxe nem enganar autenticação: só **acrescenta uma chave** (`"role": "admin"`) a um JSON perfeitamente bem-formado. A chave extra é **dado válido**; o bug é o servidor tratá-la como um campo que ele tem permissão de setar.

### Sub-lição CRÍTICA — o fix é ALLOWLIST DE CAMPOS, não BLOCKLIST DE CAMPO

Cravar (é o coração da nota #1 do DIFF): a defesa **NÃO** é caçar o campo perigoso no input ("veio `role`? então remove" / "rejeita se o JSON tiver `role`"). Isso é **blocklist**, e **quebra**: você teria que lembrar de **todo** campo perigoso pra sempre (`role`, `is_admin`, `is_staff`, `verified`, `credits`, `balance`, `email_verified`, ...), cada **campo novo** que alguém adicionar ao modelo vira um **buraco potencial** que ninguém lembrou de blocar, e variações (aninhamento, nomes alternativos) escapam. A defesa robusta é **allowlist de CAMPOS**: o servidor lista **explicitamente** os campos que o usuário **PODE** tocar (`name`, `email`), e **só esses** entram — qualquer outro é **ignorado por padrão**. O **servidor** decide quais atributos o input pode setar; o input só escolhe **valores para campos permitidos**. É o mesmo espírito do arco Injection (input como **dado**, não como **código/estrutura**): aqui, o input é tratado como **valores para um conjunto fixo de campos**, não como um mapa livre de "quais atributos tocar".

**Ligação EXPLÍCITA com o `open-redirect` (24, publicado).** Os dois átomos são a **mesma lição de A01 em superfícies diferentes**: *"o SERVIDOR decide, não o input"*. No `24`, o input controla o **DESTINO** de um redirect, e o fix é uma **allowlist de estrutura** (só path interno). Aqui, o input controla **QUAIS CAMPOS** de um objeto são setados, e o fix é uma **allowlist de campos** (só `name`/`email`). E a armadilha é idêntica nos dois: a intuição de **blocklist** (lá "bloquear `http://`", aqui "remover `role`") **quebra** porque o atacante tem infinitas variações; a **allowlist** (lá "é um path nosso?", aqui "é um campo que o user pode setar?") fecha o caso porque **enumera o permitido** em vez de caçar o proibido.

### Por que A01 (Broken Access Control)

Mass assignment é **A01 — Broken Access Control** (CWE-915 — **CWE** = Common Weakness Enumeration, o catálogo padrão de classes de fraqueza; a entrada 915 é "Improperly Controlled Modification of Dynamically-Determined Object Attributes"). A01 é, no fundo, o servidor **permitir algo fora do que deveria** naquele contexto. Nas irmãs IDOR/BOLA (03/11/12) falta um **check de autorização** sobre um objeto (o atacante **lê** um objeto que não é dele); no `path-traversal-basic` (10) o request **sai** do diretório permitido; no `open-redirect` (24) o servidor **manda** o usuário pra um destino fora do site; no `csrf-basic` (23) o servidor autoriza uma ação sem verificar a **intenção**. No mass assignment, a decisão que falha é **"quais atributos deste objeto o usuário pode modificar"**: o app deveria deixar o usuário setar só `name`/`email`, mas delega essa decisão ao input e acaba deixando ele **escrever `role`** — um atributo que só o servidor deveria controlar. É controle de acesso a **nível de propriedade do objeto**: o usuário modifica um campo fora do que lhe é autorizado. Situar em **A01 — Broken Access Control (CWE-915)**, explicar o **porquê** (controle ausente sobre **quais campos** o input pode escrever), **sem** contar edições antigas.

---

## NÃO há "Saída B" — e o comportamento de `.update()`/`get_json()` é DETERMINÍSTICO (probe = validação §11, não risco version-dependent como o 24)

Este é o eixo técnico. Duas coisas distintas, não confundir:

**(1) NÃO há "Saída B" (a ferramenta padrão NÃO resiste ao bug ingênuo).** Nos átomos `14`/`15`/`18`/`23`, a ferramenta padrão **já mitigava** o bug ingênuo (PyJWT recusava a key confusion; `flask.session` resistia à fixation; a stdlib não resolvia entidade externa; o browser com `SameSite=Lax` não anexava o cookie cross-site), então o átomo tinha que modelar as condições reais onde a vuln vive. **Aqui não existe essa ruga:** `dict.update(<json>)` é **diretamente** mal-usável — basta o dev copiar o input cru pra dentro do objeto. **Não há ORM com strong-params, não há schema-validation, não há nada "resistindo".** O átomo é **atribuição direta de campos** (o dev despeja o input), como o `24 open-redirect` era injeção direta de destino e o `19 ssti-jinja` era injeção direta, **sem** ferramenta-que-resiste. **NÃO inventar uma Saída B** (ex.: NÃO introduzir um ORM só pra "ter" o mecanismo idiomático — ver a nota #2 do DIFF: o ORM é **mencionado como contexto**, não introduzido; a lição fica mais nítida com o `dict.update()` cru).

**(2) MAS confirmar o comportamento por probe (validação §11) — E a diferença HONESTA em relação ao `24`.** No `24`, o comportamento do `redirect()`/Werkzeug (**qual `Location` exato sai** pra cada payload) **mudava entre versões** — era um risco técnico genuíno que **tinha que ser resolvido rodando** antes de escrever. **Aqui não.** `dict.update(other)` copia **todas** as chaves de `other` (semântica de Python, determinística e estável entre versões); `request.get_json()` parseia o corpo JSON num `dict`. Não há surpresa de versão. Logo o "probe" deste átomo **não** resolve uma incerteza técnica — é **validação de geração** (`CLAUDE.md` §11): confirmar **rodando** que

- no `vulnerable`, `POST /profile` com `{"name":..., "email":..., "role":"admin"}` **de fato** faz o `role` entrar na conta (visível no `GET /profile`) e o `GET /admin` passar a responder `200`;
- no `fixed`, o **mesmo** payload deixa o `role` **inalterado** (`user`), e o `GET /admin` segue `403`;
- no `fixed`, `name`/`email` legítimos **ainda atualizam** (a feature funciona).

**Capturar a cadeia real** (request/response de cada passo) e **travar** os blocos antes de escrever o WALKTHROUGH. Se algo não reproduzir como descrito (ex.: `get_json()` exigindo `Content-Type` e devolvendo `None` — resolvido com `silent=True or {}`, ver "O código"), **registrar e ajustar** — **NÃO assumir; NÃO inventar** a resposta. A honestidade aqui: esse probe é **fácil e determinístico**, não o quebra-cabeça de versão do `24` — mas continua **obrigatório** por §11, e a prova capturada é o que vai pro WALKTHROUGH.

---

## Contraste — com `open-redirect` (24), com IDOR/BOLA (03/11/12), e com injection

O que ancora o passo "o que a vuln NÃO é". Cravar no WALKTHROUGH e no DIFF:

### Contraste que AMARRA — Mass Assignment vs Open Redirect (`24`, publicado): a MESMA lição A01 em superfícies diferentes

Os dois são A01, os dois têm a **mesma raiz** (o servidor confia numa decisão que era dele e delega ao input) e o **mesmo formato de fix** (allowlist server-side + a nota "allowlist, não blocklist"). A diferença é **o que o input controla**:

| Eixo | **Open Redirect** (`24`) | **Mass Assignment** (`25`) |
|---|---|---|
| **O input controla…** | o **DESTINO** de um redirect (`next`) | **QUAIS CAMPOS** de um objeto são setados (o JSON) |
| **A confiança cega é em…** | um destino controlado pelo usuário | a **forma/os campos** do input |
| **O que o servidor deveria decidir** | pra onde pode redirecionar | quais atributos o user pode escrever |
| **O fix (allowlist server-side)** | só **paths internos** (allowlist de estrutura) | só **campos permitidos** `name`/`email` (allowlist de campos) |
| **A blocklist que quebra** | caçar `http://`/host na string | caçar `role`/`is_admin` no input |
| **A prova** | o header `Location` externo na resposta | o `role` virar `admin` (`GET /profile`) e o `GET /admin` responder |

**A frase-regra:** *nos dois, o servidor delegou ao input uma decisão que era do servidor; a defesa é o servidor enumerar o permitido (allowlist), não caçar o proibido (blocklist).* Usar o `open-redirect` (24, publicado) como âncora — o aluno pode abrir os dois lado a lado e ver o **mesmo padrão** de A01 em duas superfícies (destino vs campos).

### Contraste com IDOR/BOLA (`03`/`11`/`12`, publicados): objeto de OUTRO user vs escalada no PRÓPRIO objeto

É o contraste que o passo "o que a vuln NÃO é" carrega. É fácil confundir "acessei algo que não devia" com "escalei privilégio", mas o eixo é diferente:

| Eixo | **IDOR / BOLA** (`03`/`11`/`12`) | **Mass Assignment** (`25`) |
|---|---|---|
| **Qual objeto** | de **OUTRO** usuário | o **SEU PRÓPRIO** |
| **O atacante…** | **LÊ** um objeto fora do seu escopo | **ESCREVE** um atributo que não deveria controlar |
| **A escalada é…** | **horizontal** (dado de outro user do mesmo nível) | **vertical** (`user → admin`) |
| **O que falta no código** | check de **dono** (ownership) | **seleção de campos** (allowlist) |

**A frase-regra:** *IDOR/BOLA = ler o objeto de OUTRO (falta o check de dono); mass assignment = escrever no SEU objeto um campo que te dá privilégio (falta a seleção de campos).* Confundir os dois leva o aluno a "explicar" mass assignment como "acessei a conta de outro" — **não é**: você mexe **na sua própria conta**, e o problema é que ela deixou você escrever um campo (`role`) que só o servidor deveria setar.

### Contraste com injection — não injeta sintaxe, adiciona um campo válido

Mass assignment **não é injection**: o atacante **não** injeta sintaxe (nada de `' OR 1=1`, `<script>`, `{{7*7}}`, `; id`) nem quebra um parser. Ele manda um JSON **perfeitamente bem-formado** e só **acrescenta uma chave a mais**. O campo extra é **dado válido**, não código. Onde injection é "input vira código/estrutura", mass assignment é "input escreve num campo que não deveria" — a fronteira violada é de **autorização de campo**, não de parsing. Ancora o "o que a vuln NÃO é".

---

## Flavor — atualização de perfil (`POST /profile` recebe JSON → `account.update`) — TRAVADO

Cenário canônico de mass assignment: um endpoint de **atualização de perfil** que recebe JSON. O alvo (`vulnerable` e `fixed`) tem **uma conta demo em memória** (o "usuário logado" — a conta **é você**), começando com `role: "user"`, e três rotas:

- **`POST /profile`** — atualiza a conta do usuário logado com o JSON recebido. **É AQUI QUE A VULN MORA** (`account.update(<json>)` sem selecionar campos no `vulnerable`; allowlist de `name`/`email` no `fixed`). Responde a conta atualizada (JSON).
- **`GET /profile`** — mostra os campos da conta (`name`, `email`, `role`) — **é a prova** de que o `POST` mudou o `role`. (Ver a sua própria conta, incluindo o `role`, é normal; é o seu objeto — **não** é vazamento de dado de outro user; ver "Renderização".)
- **`GET /admin`** — só responde `200` (com um conteúdo admin-only demo) se `account["role"] == "admin"`; senão `403`. **Torna a escalada CONCRETA e observável:** antes do ataque, `403`; depois, `200`.

**Estado em memória, SEM datastore, SEM banco (`CLAUDE.md` §3.4 — o storage segue a superfície do bug: mass assignment não depende da camada de storage, é seleção-de-campos ausente acima de qualquer store).** A conta é um `dict` global no `app.py`, seedado no import, mutável de processo único (restart zera). Notar como o `12` notou pro seu store.

**Sem autenticação real (candidato — a conta demo É "você").** Como só há **uma** conta (a escalada é **vertical**, no próprio objeto — não há um segundo usuário a distinguir), **não é preciso** login nem token: a conta demo **representa o usuário logado**. Auth real (senha, sessão) está **fora de escopo** — é o mesmo atalho do login `demo`/`demo` do `24` e do `POST /login` sem senha do `12`. *(Latitude de Fase 2: se preferir setar `session["user"]` pra "mais realista", é aceitável, MAS é plumbing ortogonal à vuln — o `update` cego escala igual com ou sem sessão. Não transformar a sessão em superfície. Se setar sessão, usar `SECRET_KEY` dummy óbvia, `CLAUDE.md` §8.3, e notar que é palco, não a vuln.)*

**Superfície = o `account.update(<json>)` no `POST /profile`.** `GET /profile` (a prova) e `GET /admin` (a escalada concreta) e o "login" (se houver) **NÃO são a vuln** — são o palco. Uma única superfície: a seleção (ausente) de campos no update. **Sem** segunda superfície, **sem** datastore, **sem** ORM.

---

## Payload-prova — ESCALADA DE PRIVILÉGIO (TRAVADO; §8)

O atacante adiciona ao JSON de atualização de perfil um campo que o formulário nunca ofereceu — `role: "admin"` — e, no `vulnerable`, o `update` cego o copia pra conta. **A prova é a cadeia: o `role` vira `admin` (no `GET /profile`) E o `GET /admin` passa a responder.**

- **Baseline (feature benigna, os dois lados):** `POST /profile` com `{"name": "New Name", "email": "new@example.com"}` → atualiza os campos legítimos; `role` continua `"user"`; `GET /profile` mostra `role: "user"`; `GET /admin` → `403`. **Idêntico** no `vulnerable` (:8025) e no `fixed` (:8125).
- **O ataque (no `vulnerable`, :8025):** `POST /profile` com `{"name": "New Name", "email": "new@example.com", "role": "admin"}` → o `account.update()` cego copia o `role` também → `GET /profile` mostra **`role: "admin"`** → `GET /admin` agora → **`200`** (o conteúdo admin-only). **A prova é o `role` escalado + o `GET /admin` respondendo.**
- **No `fixed` (:8125):** o **MESMO** payload → o `role` é **IGNORADO** (a conta segue `role: "user"`), `GET /admin` segue **`403`**. E `name`/`email` legítimos **ainda atualizam** (a feature funciona).

**Por que Burp/curl bastam como prova (sem browser).** A vuln **é** o servidor copiar cegamente um campo controlado pelo cliente pra dentro do objeto — e isso é **inteiramente visível na resposta HTTP**: o `GET /profile` devolve `role: "admin"`, o `GET /admin` devolve `200`. Não há JS executando (não é o `21`), não há cookie que um browser precise anexar sozinho (não é o `23`) — **a request/resposta no Repeater é a prova completa.** *(O `POST /profile` precisa de `Content-Type: application/json` pro `get_json()` parsear o corpo — incluir o header no bloco do Repeater; ver "O código".)*

**§8:** valores **benignos** — `name`/`email` fake (`new@example.com`), `role: "admin"` é um valor benigno (não é payload destrutivo). O conteúdo admin-only do `GET /admin` é **dado fake óbvio** (sem segredo real). Tudo loopback, nada destrutivo.

---

## O código — o coração no `account.update(<json>)`

O fix é **SERVER-SIDE** (no `app.py` do alvo), como no `12`/`24`. O `app.py` **DIFERE** entre `vulnerable` e `fixed`; o **único delta é a seleção de campos no `POST /profile`**. `Dockerfile` e `requirements.txt` são **idênticos** entre os dois lados (não há templates — API-only).

### `vulnerable/app.py` — `account.update(<json>)` sem selecionar campos (candidato — Fase 2 gera o real)

```python
import os

from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# --- In-memory account for the logged-in user (no database) ---
# The demo account IS "you". It starts as a normal user; only the server should
# ever be able to promote it. name/email are the fields the profile form edits.
account = {"name": "Demo User", "email": "demo@example.com", "role": "user"}


@app.route("/profile", methods=["POST"])
def update_profile():
    data = request.get_json(silent=True) or {}
    # VULNERABLE: copy EVERY field from the client's JSON straight into the account.
    # This works for the legitimate fields (name, email), but it also copies any
    # extra field the client adds -- including "role", which the profile form never
    # offered. The CLIENT, not the server, decides which attributes get set.
    account.update(data)
    return jsonify(account)


@app.route("/profile")
def get_profile():
    return jsonify(account)   # shows name, email, role -- proves what the update changed


@app.route("/admin")
def admin():
    # The escalation made concrete: this admin-only view answers only when the
    # account is an admin; a normal user gets 403.
    if account["role"] != "admin":
        abort(403)
    return jsonify({"message": "Admin area", "note": "admin-only content"})


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — allowlist de CAMPOS (só `name`/`email`) (candidato — Fase 2 gera o real)

```python
import os

from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# --- In-memory account for the logged-in user (no database) ---
account = {"name": "Demo User", "email": "demo@example.com", "role": "user"}

# The SERVER decides which fields a profile update may set (allowlist of fields).
ALLOWED_FIELDS = {"name", "email"}


@app.route("/profile", methods=["POST"])
def update_profile():
    data = request.get_json(silent=True) or {}
    # FIXED: allowlist of FIELDS -- only the attributes the user is allowed to set
    # (name, email) are copied. "role" and any other field in the JSON are ignored,
    # because the SERVER decides which attributes the client may touch, not the input.
    for field in ALLOWED_FIELDS:
        if field in data:
            account[field] = data[field]
    return jsonify(account)


@app.route("/profile")
def get_profile():
    return jsonify(account)


@app.route("/admin")
def admin():
    if account["role"] != "admin":
        abort(403)
    return jsonify({"message": "Admin area", "note": "admin-only content"})


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### Notas de implementação (validar/decidir na Fase 2)

- **`get_json(silent=True) or {}` (candidato — molde do `12`).** Usar `silent=True` + `or {}` (o mesmo padrão do `login` do `bola-rest`) evita um `500`/`415` quando o corpo não é JSON válido ou falta o `Content-Type` — é **higiene operacional idêntica nos dois lados**, ortogonal à vuln (a vuln é copiar **todas** as chaves do dict que chegar). Consequência prática pro walkthrough: o `POST /profile` **precisa** de `Content-Type: application/json` pra o corpo ser parseado — incluir no bloco do Repeater. Confirmar na Fase 2.
- **A allowlist do `fixed` — `for field in ALLOWED_FIELDS: if field in data` (candidato).** Itera sobre o **conjunto permitido** (não sobre o input), então campos fora do conjunto **nunca** são tocados. Atualização **parcial** preservada (campo ausente no JSON → valor atual mantido), casando o baseline. *(Alternativa aceitável, `CLAUDE.md`-neutra: `account["name"] = data.get("name", account["name"]); account["email"] = data.get("email", account["email"])` — as duas linhas explícitas. O loop sobre `ALLOWED_FIELDS` é preferido por nomear a **allowlist** como um objeto de primeira classe — que **é** a lição — e por escalar visivelmente, mas as duas são equivalentes. Confirmar na Fase 2.)*
- **`GET /admin` — gate por `role` (candidato).** `abort(403)` se `account["role"] != "admin"`; senão devolve um conteúdo admin-only **fake e óbvio** (`{"message": "Admin area", ...}`). O `403` vs `200` é o sinal observável da escalada. Texto exato do conteúdo é latitude de Fase 2 (dado fake, §8 — **sem** segredo real, **sem** `flag{}`/CTF, `CLAUDE.md` §12).
- **O `role` é serializado no `GET /profile`** (é a prova — o aluno vê `role: "admin"`). Isso **não** é vazamento: é a **própria conta** do usuário (o objeto dele). Ver "Renderização".
- **Estado mutável de processo único.** O `POST /profile` **muta** a conta em memória; após o ataque no `vulnerable`, o `role` **fica** `"admin"` até o restart (ou até um `POST /profile` com `{"role":"user"}` no `vulnerable`). Fazer o **baseline ANTES** do ataque no walkthrough (a ordem natural: `403` primeiro, `200` depois) evita precisar resetar no meio. Notar que restart zera o estado (para re-rodar). Higiene de lab, como o `12` notou pro `TOKENS`.
- **Erros via `abort()` cru** (padrão Flask): o **status code é o sinal do exploit** (`200`/`403`); o corpo do erro é imaterial pra lição e **não reflete input** (sem XSS). Consistente com o `12`.
- **Sem HTML, sem `templates/`, sem `render_template`** (API-only). Ver "Renderização" e "O container".

---

## O fix e o tipo de diff

**Fix:** **allowlist de campos, server-side** — no `POST /profile`, copiar **só** os campos permitidos (`name`, `email`) do JSON pra conta; qualquer outro campo (`role`, etc.) é **ignorado**. Tipo de diff: **lógica-diferente** — a introdução do `ALLOWED_FIELDS` + a troca do `account.update(data)` pelo loop de allowlist. O resto (imports, a conta seedada, `GET /profile`, `GET /admin`, o `__main__`) é **byte-idêntico**. A constante `ALLOWED_FIELDS` e o loop são o delta.

Diff colável (candidato — a Fase 2 gera o real; recortes do `app.py`, comentários abreviados):

```diff
 import os

 from flask import Flask, request, jsonify, abort

 app = Flask(__name__)

 account = {"name": "Demo User", "email": "demo@example.com", "role": "user"}

+# The SERVER decides which fields a profile update may set (allowlist of fields).
+ALLOWED_FIELDS = {"name", "email"}
+

 @app.route("/profile", methods=["POST"])
 def update_profile():
     data = request.get_json(silent=True) or {}
-    # VULNERABLE: copy EVERY field from the client's JSON straight into the account ...
-    account.update(data)
+    # FIXED: allowlist of FIELDS -- only name/email are copied; role and anything else ignored ...
+    for field in ALLOWED_FIELDS:
+        if field in data:
+            account[field] = data[field]
     return jsonify(account)
```

**O CONTRASTE é o diff (obrigatório):** `account.update(data)` (vulnerable) vs o loop sobre `ALLOWED_FIELDS` (fixed). **A única mudança é quem decide quais campos entram** — o input (vulnerable, "todos") ou o servidor via allowlist (fixed, "só `name`/`email`"). O `GET /profile`, o `GET /admin`, a conta e os imports são idênticos.

### Notas obrigatórias no `DIFF.md`

1. **ALLOWLIST DE CAMPOS, NÃO BLOCKLIST (nota "mencionável, não aplicada" — molde 19/20/21/24).** Nomear a intuição errada: *"é só remover `role` do input"* ou *"rejeitar se vier `role`"*. Mostrar **por que a blocklist QUEBRA**:
   - você tem que lembrar de **TODO** campo perigoso pra **sempre** (`role`, `is_admin`, `is_staff`, `verified`, `credits`, `balance`, `email_verified`, ...);
   - **cada campo novo** que alguém adicionar ao modelo/objeto vira um **buraco potencial** que ninguém lembrou de blocar;
   - **variações** escapam: aninhamento (`{"account": {"role": "admin"}}`), nomes alternativos, capitalização, etc.
   - **Cravar:** contra "caçar o campo proibido", o atacante e a evolução do modelo têm infinitas formas; a defesa robusta é **allowlist de CAMPOS** — *o servidor enumera os campos que o user PODE tocar (`name`/`email`), e só esses entram; o resto é ignorado por padrão*. **A blocklist é DESCRITA, não aplicada** (mesmo espírito das notas "defesa mais fraca/errada, não aplicada" dos átomos anteriores). O átomo aplica a **allowlist de campos**. **Ligação EXPLÍCITA com o `open-redirect` (24, publicado):** é a **mesma** dicotomia allowlist-vs-blocklist de A01 — lá o servidor decide o **destino** (só path interno), aqui decide os **campos** (só `name`/`email`); os dois "o servidor enumera o permitido, não caça o proibido".
2. **MASS ASSIGNMENT É ICÔNICO EM ORMs (contexto honesto, SEM depender de um).** Nota curta: a falha é famosa em frameworks com **ORM** (Object-Relational Mapping — a lib que mapeia objetos pras colunas do banco), porque ali o objeto mapeia **direto** pras colunas, então um campo extra no bind vira uma **coluna escrita** no banco — o `create`/`update` "de conveniência" que aceita o hash de params inteiro (o autobinding de frameworks web com ORM é o exemplo clássico). **Aqui a gente modela a MESMA falha com um `dict` em memória** (o `account.update()` cego), **sem** ORM, pra a lição ficar **visível a olho nu** (`CLAUDE.md` §3.6 — só a lib que serve à demonstração; o ORM turvaria o `update` de uma linha). O princípio é **idêntico**: confiar na **forma** do input. **Mencionar o contexto ORM, NÃO introduzir um.** *(Isto é descrição da CLASSE, não foreshadow de átomo — Nota de planning 2.)*
3. **IMPACTO + CONTRASTE.** **Escalada de privilégio (vertical, `user → admin`)** via um campo que o user não deveria poder setar. **Direto e concreto:** o `GET /admin`, que dava `403`, passa a responder `200`. **CONTRASTE:** com o `open-redirect` (24) — os dois "allowlist server-side" (destino vs campos), a mesma lição A01 "o servidor decide, não o input"; com IDOR/BOLA (03/11/12) — lá o atacante **lê** o objeto de **OUTRO** user (escalada **horizontal**, falta o check de dono), aqui ele **escreve** no **próprio** objeto um campo que dá privilégio (escalada **vertical**, falta a seleção de campos). Mesma A01, eixos distintos. **Sem overclaim:** é escalada de privilégio **no app** (`user → admin`), **não** RCE nem takeover de servidor — o átomo prova o `role` escalar e o `GET /admin` abrir.

---

## Biblioteca / mecanismo

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask.** `os` é **stdlib**; `request`/`jsonify`/`abort` vêm do Flask. **Sem banco, sem `requests`, sem ORM, sem segunda dependência.** Single-container, sem datastore. **Não introduzir ORM** (a falha é modelada com o `dict.update()` cego — ver a nota #2 do DIFF).
- **O pin NÃO é behavior-relevante aqui (diferente do `24`).** O comportamento do `dict.update()`/`request.get_json()` é **determinístico e estável** entre versões (não depende do Werkzeug como o `redirect()` do `24`). Candidato de pin `Flask==3.0.0` (casando com os irmãos 01/12/24); **confirmar** que instala em `python:3.11-slim` (wheel) e que o `get_json()`/`update()` se comportam como o WALKTHROUGH descreve (probe = validação §11; ver risco #2). Se preferir alinhar ao pin exato do átomo publicado mais recente, checar o `requirements.txt` do `24` na Fase 2.

---

## WALKTHROUGH — abertura seca, trilha Burp-only (SEM browser)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (atualização de perfil que recebe JSON) e a falha (o `account.update(<json>)` copia todos os campos). Trilha **ÚNICA: Burp** (`curl` como equivalente — POST/GET simples com corpo JSON; a prova é o `role` no `GET /profile` e o status do `GET /admin`). **NÃO** criar seção de browser, **NÃO** usar exceção client-side.

**Abertura (candidato — plantar a lição, seco):**

> *A app tem uma atualização de perfil: você manda um JSON com os campos da sua conta e ela salva. Mande `{"name": "...", "email": "..."}` e seu nome e e-mail mudam. O problema: o handler copia **todos** os campos do JSON direto pra sua conta — então, se você acrescentar `"role": "admin"`, um campo que o formulário nunca ofereceu, ele é copiado também, e você vira admin. A prova está na resposta: o `GET /profile` passa a mostrar `role: admin`, e o `GET /admin` — que dava `403` — passa a responder.*

Beats (molde do `24`/`12` publicado — abertura seca, seções numeradas `## 1..6`, Burp-only, API-only):

1. **Context.** Feature: atualização de perfil via JSON. Definir na estreia: **mass assignment** (o app faz bind em bloco dos campos da request num objeto sem escolher quais o user pode setar; também "object injection"/"autobinding"), **allowlist de campos** (o conjunto explícito de campos que o servidor deixa o cliente setar), **campo privilegiado/sensível** (`role`/`is_admin`/... — concede privilégio se setado pelo user; só o servidor deveria setar), **privilege escalation** (aqui **vertical**, `user → admin`), **ORM** (na estreia, quando aparecer o contexto). Isto é **Mass Assignment**, sob **A01 — Broken Access Control (CWE-915)**. A conta demo começa com `role: "user"`. Topologia: `vulnerable` (:8025), `fixed` (:8125), single-container, API-only. Trilha: **Burp/curl** — a prova é a resposta.
2. **Spot the bug.** Mostrar o `POST /profile` do `vulnerable/app.py` — `account.update(request.get_json(...))`, **sem** selecionar campos. Pergunta de auditoria: *"esse update escolhe QUAIS campos o cliente pode setar — ou aplica todos?"* → aplica todos. Foreshadow do fix: o **servidor** listar os campos aceitáveis (allowlist), não copiar o input inteiro.
3. **Exploitation via Burp Suite (a prova é a resposta).**
   - **Baseline (feature benigna):** `POST /profile` com `{"name": "New Name", "email": "new@example.com"}` (+ `Content-Type: application/json`) → `200`, conta atualizada; `GET /profile` → `role: "user"`; `GET /admin` → `403`. Bloco colável no Repeater (request-line + `Content-Type` + corpo JSON). Equivalente `curl`.
   - **Montar o payload:** acrescentar a chave `"role": "admin"` ao JSON. No Repeater, `POST /profile` com `{"name": "New Name", "email": "new@example.com", "role": "admin"}`.
   - **Disparar (o ataque):** `GET /profile` agora mostra **`role: "admin"`** (o `update` cego copiou o campo extra) → `GET /admin` agora → **`200`** (o conteúdo admin-only). **A prova é o `role` escalado + o `GET /admin` respondendo.**
   - **§8 (cravar):** valores **benignos** (`name`/`email` fake, `role: "admin"` benigno), tudo loopback; nada destrutivo.
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa:
   - **NÃO é IDOR/BOLA.** Você **não** acessou o objeto de **outro** usuário — mexeu **na sua própria conta**. A escalada é **vertical** (`user → admin`), não horizontal (ler o dado de um vizinho). *(Contraste com o `bola-rest` (12) e os IDOR 03/11, publicados: lá o buraco era o **check de dono** ausente sobre o objeto **de outro**; aqui é a **seleção de campos** ausente no **seu próprio** objeto.)*
   - **NÃO é injection.** Você **não** injetou sintaxe (nada de `' OR 1=1`, `<script>`, `{{7*7}}`, `; id`); mandou um JSON **bem-formado** e só **acrescentou uma chave**. O campo extra é **dado válido**, não código. *(Contraste com os átomos de injection publicados — lá o payload é input virando código/estrutura; aqui é um campo a mais.)*
   - **NÃO é auth bypass.** Você **não** derrotou autenticação nem forjou sessão — a conta é **legitimamente sua**. O buraco é a **atribuição cega**: o servidor deixou você escrever um campo (`role`) que só ele deveria controlar. **Prova de isolamento:** o update legítimo (só `name`/`email`) funciona **idêntico** no `vulnerable` e no `fixed`; só o **campo extra** `role` separa os dois.
   - **O que É (prova):** o servidor confia na **forma** do input e deixa o **cliente** decidir quais atributos setar. A correção é o **servidor** decidir — allowlist de **campos** (só `name`/`email`).
5. **Impact (honesto — sem overclaim).** **Escalada de privilégio vertical** (`user → admin`) via um campo que o user não deveria poder setar. **Direto e concreto:** o `GET /admin`, que dava `403`, passa a responder `200`. **Sem overclaim:** é escalada **no app** (`user → admin`), **não** RCE nem takeover de servidor. Em apps reais o mesmo padrão escreve outros campos sensíveis (`credits`, `verified`, `is_staff`, o `owner` de um recurso) — **descrição da classe**, não algo armado neste átomo (§8).
6. **Why the fix works (porta 8125).** Repetir contra o `fixed/`:
   - **O MESMO payload** (`{"name": ..., "email": ..., "role": "admin"}`) → o fixed **ignora o `role`** (a conta segue `role: "user"`), `GET /admin` segue **`403`**. **Confirmar que `name`/`email` legítimos ainda atualizam** (a feature funciona) — o fix não quebra o uso legítimo.
   - **Prova de isolamento:** o update legítimo (só `name`/`email`) funciona **idêntico** nos dois lados; só o campo extra `role` separa `vulnerable` de `fixed`.
   - **A lição do diff:** o fix é **allowlist de campos** (nota #1 — não blocklist "remover `role`"; a mesma dicotomia do `24`); a falha é **icônica em ORMs**, modelada aqui com `dict` cru (nota #2); **impacto honesto** = escalada vertical `user→admin`, contraste com IDOR/BOLA (horizontal, objeto de outro) e com o `24` (allowlist de destino) (nota #3).

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Payloads/responses (o `role: "admin"` no `GET /profile`, o `200` no `GET /admin`) são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**Mass Assignment — escalada de privilégio direta e concreta, sem overclaim.** O átomo prova **uma** coisa: acrescentando `role: "admin"` a um JSON de atualização de perfil, o `update` cego copia o campo e a conta **vira admin** — o `GET /admin`, antes `403`, passa a `200`. Isso é **escalada de privilégio vertical** (`user → admin`) no app. **NÃO** é RCE, **NÃO** é takeover de servidor, **NÃO** é leitura de objeto de outro user (contraste direto com IDOR/BOLA 03/11/12, que é horizontal). O valor da classe está em quão **onipresente e barata** ela é: qualquer endpoint que faça bind em bloco de JSON num objeto (perfil, config, pedido, conta) sem selecionar campos deixa o cliente escrever atributos sensíveis (`role`, `is_admin`, `verified`, `credits`, `owner`) — por isso mass assignment é um item próprio no OWASP API Security Top 10. Isso é **descrição da CLASSE**, **NÃO** uma chain armada neste átomo. **Sem overclaim:** a **prova do lab** é o `role` escalar e o `GET /admin` abrir; os outros campos sensíveis são **descritos, não armados** (§8). **Sem foreshadow** (§5 / Nota de planning 2 — nada de "fecha a categoria/fase" nem menção a átomos/versões futuras).

---

## Renderização / "um átomo = uma vuln"

**API-only, respostas JSON via `jsonify`** — **sem templates** (`CLAUDE.md` §3.3 lista "Mass assignment" como naturalmente API-only; molde do `12 bola-rest`), logo **sem risco de XSS acidental**: nenhum valor (`name`/`email`) é refletido em contexto HTML (a saída é `application/json`, não HTML). Isso **elimina de origem** a preocupação de reflected XSS que os átomos com HTML precisam tratar com autoescape.

Garantir que a **ÚNICA** lição é o `POST /profile` copiar campos cegamente:

- **`GET /profile` e `GET /admin` (e o "login", se houver) NÃO são a vuln.** São só o palco: `GET /profile` prova a mudança (mostra `role`), `GET /admin` torna a escalada concreta e observável (`403`→`200`). A **única** superfície é a seleção (ausente) de campos no update.
- **O `role` no `GET /profile` NÃO é vazamento.** É a **própria conta** do usuário (o seu objeto) — ver a sua própria `role` é normal e é a **prova** do exploit. Não é dado de **outro** user (isso seria IDOR/BOLA, outro eixo). Uma vuln só.
- **O `fixed` muda SÓ a seleção de campos** (o `ALLOWED_FIELDS` + o loop). Todo o resto (imports, conta, `GET /profile`, `GET /admin`, `__main__`) é **byte-idêntico**. A **seleção-de-campos é o único delta**.
- **Sem datastore, sem ORM, sem sessão como superfície, sem segredo real.** Estado em memória; sem auth real (candidato) — reforça que a vuln é a atribuição cega, não a identidade. Se a Fase 2 optar por `session` pra realismo, `SECRET_KEY` dummy e a sessão é **palco**, não a vuln. O conteúdo do `GET /admin` é fake óbvio (§8, sem `flag{}`/CTF).
- **Erros via `abort()` cru** (padrão Flask): o status code (`200`/`403`) é o sinal; o corpo não reflete input (sem XSS). Consistente com o `12`.

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` — molde do `bola-rest` (12) (**API-only → SEM `COPY templates`**). Só Flask via pip — sem `apt`, sem banco, sem ORM. `os` é stdlib.

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** (candidato — idênticos entre si):

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

**`docker-compose.yml`** (candidato — molde do 01/12/24, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8025:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8125:5000"
```

**Sem `networks:`, sem serviço extra, sem `depends_on`, sem healthcheck, sem `COPY templates`.** Molde simples do 01/24 menos os templates (API-only, como o 12).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Ressalva importante (a razão de este primer precisar de decisão do mantenedor):** a PortSwigger cobre mass assignment **dentro** do material de **API testing** ("Testing for mass assignment vulnerabilities" / "excessive properties"), **não** numa página conceitual de topo "What is mass assignment?" no nível de SQLi/XSS/SSRF. Pode servir como primer se, ao fetch, tiver framing conceitual utilizável.
- **Candidatos a confirmar por fetch na Fase 2 (ranqueados):**
  1. **PortSwigger — a seção de mass assignment no material de API testing.** Preferida pelo `CLAUDE.md` §5 ("PortSwigger primeiro"), **se** ao fetch tiver um framing conceitual limpo. URL a confirmar por fetch — **NÃO cravar sem fetch**.
  2. **OWASP API Security Top 10 — a página de Mass Assignment.** No API Top 10 **2019** era **API6:2019 — Mass Assignment**; na edição **2023** foi absorvida em **API3:2023 — Broken Object Property Level Authorization (BOPLA)** (que junta mass assignment + excessive data exposure). É a fonte conceitual mais **stack-neutra** e alinhada ao mapeamento CWE-915/A01. **Candidato preferido** se a PortSwigger não tiver página conceitual limpa. URL a confirmar por fetch (provavelmente sob `owasp.org/API-Security/…`) — **NÃO cravar sem fetch**.
- **DECISÃO PENDENTE PRO MANTENEDOR (Fase 2):** confirmar por fetch qual fonte usar. Se a PortSwigger não tiver página conceitual limpa, **propor a OWASP API Security e avisar** — desvio consciente da preferência "PortSwigger primeiro" do `CLAUDE.md` §5, justificado pela ausência de página conceitual de topo pra esta classe (mesmo procedimento do `open-redirect` 24). **NÃO inventar URL nem grafia.**
- **Confirmar também por fetch** (risco #9): o número exato do **CWE** (915, ou o pai **CWE-913**) e o mapeamento **A01:2021**; e a grafia do nome da classe pro H1 ("Mass Assignment").
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7), casando com a grafia exata da fonte escolhida.
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo dos irmãos).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A01 — Broken Access Control** (`atoms/A01-broken-access-control/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `mass-assignment` em A01; `CLAUDE.md` §4 fixa a pasta. CWE-915. Situar em A01 **sem arqueologia**. |
| Posição na fase | Ver `ROADMAP.md` | A posição/ordinal/release vivem só no ROADMAP. Spec e conteúdo nascem **limpos** (foreshadow §5); **ZERO** menção de "fechar" fase/categoria (Nota de planning 2). |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Molde do 01/24. Sem serviço extra, sem datastore. Estado em memória. |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | `CLAUDE.md` §3.3 lista "Mass assignment" como naturalmente API-only. Molde do `12`. JSON via `jsonify` → sem XSS acidental. |
| Trilha | **Burp-only (+ curl), SEM browser** | §3.3 atual. A prova é a request/resposta (server-side). **SEM** exceção client-side (como o 24; diferente do 21/23) — não há JS executando nem cookie anexado. |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe aqui** | `dict.update(<json>)` é diretamente mal-usável (sem ORM/schema-validation resistindo). Atribuição direta de campos, como o 24/19. **NÃO inventar Saída B; NÃO introduzir ORM.** |
| Risco central técnico | **NÃO é version-dependent** (diferente do 24). `dict.update()`/`get_json()` são determinísticos. | O probe é **validação §11** (confirmar o campo extra entrar no vuln e ser ignorado no fixed; capturar a cadeia), **não** resolução de incerteza de versão. Honesto: fácil, mas obrigatório. |
| Lição-coração | **O app despeja o JSON inteiro no objeto; o atacante adiciona `role:"admin"` e escala. O fix é o SERVIDOR listar os campos aceitáveis (allowlist de campos).** | A raiz é confiança na forma do input. |
| Sub-lição | **Allowlist de CAMPOS, não blocklist ("remover `role`")** | Blocklist quebra (todo campo perigoso pra sempre; campo novo = buraco; variações/aninhamento). Allowlist enumera o permitido. Mesma dicotomia do `24`. |
| Por que A01 | **Controle ausente sobre QUAIS campos o input pode escrever** — CWE-915 | O user modifica um atributo (`role`) fora do que lhe é autorizado; controle de acesso a nível de propriedade do objeto. |
| Flavor — **TRAVADO** | **Atualização de perfil** (`POST /profile` JSON → `account.update`); `GET /profile` (prova); `GET /admin` (`403`→`200`, escalada concreta) | Cenário canônico; superfície = o `update` cego. Conta demo em memória (`role:"user"`), sem datastore, sem auth real (candidato). |
| Payload-prova — **TRAVADO** | **`POST /profile` com `role:"admin"` extra → `role` escala (`GET /profile`) e `GET /admin` → `200`** (vulnerable); ignorado, `403` (fixed). | Prova = a cadeia na resposta. Valores benignos, loopback (§8). Confirmado por probe (validação §11, risco #2). |
| Código vulnerable | **`account.update(request.get_json(silent=True) or {})`** (sem selecionar campos) | O JSON inteiro do cliente vira atributos do objeto. |
| Código fixed | **`for field in ALLOWED_FIELDS: if field in data: account[field] = data[field]`** — allowlist de campos (`{"name","email"}`) | O servidor decide os campos; só `name`/`email` entram. Alternativa (duas linhas `.get`) aceitável; o loop nomeia a allowlist. |
| `GET /admin` | **`403` se `role != "admin"`, senão `200` (conteúdo admin-only fake)** | Torna a escalada concreta/observável. Conteúdo fake óbvio (§8, sem `flag{}`/CTF). |
| `app.py` vuln × fixed | **DIFERE — a seleção de campos no `POST /profile`** (`ALLOWED_FIELDS` + loop vs `account.update`) | O delta é a seleção de campos; Dockerfile/requirements idênticos; sem templates. |
| Sessão/cookie | **Não é a vuln — sem auth real (candidato)** | Só uma conta (escalada vertical no próprio objeto); login não distingue nada. Sessão, se usada, é palco (`SECRET_KEY` dummy). |
| Bibliotecas | **`Flask==3.0.0`** (pin **NÃO** behavior-relevante) + stdlib | Sem datastore, sem ORM, sem dep extra. `update()`/`get_json()` determinísticos. Confirmar wheel/pin na Fase 2. |
| Impacto | **Escalada de privilégio vertical (`user→admin`).** NÃO RCE, NÃO leitura de objeto de outro (contraste IDOR/BOLA). | Honesto, direto (`GET /admin` abre). Outros campos sensíveis descritos, não armados. Sem overclaim, sem foreshadow. |
| Theory primer | **PENDENTE — PortSwigger (API testing) OU OWASP API Security (API3:2023 BOPLA / API6:2019 Mass Assignment)** | PortSwigger cobre em API testing, não em "what is X?" de topo. Confirmar por fetch; se não houver página limpa, propor OWASP e avisar. Não inventar. Nome em inglês no PT. |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. |
| Título (H1) | **`mass-assignment — Mass Assignment`** (classe, sem stack) | `CLAUDE.md` §5. Sem "Flask"/"JSON"/"role". Grafia confirmável na Fase 2. |
| Foreshadow | **ZERO pra frente + ZERO "fechar" fase/categoria** | `CLAUDE.md` §5 / Nota de planning 2. Não nomear átomos não-publicados/posição de fase/release/milestone. Publicados (A01 03/10/11/12, 23, 24) e ROADMAP OK. |
| Portas | **8025 / 8125** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–5 são os centrais; 6–9 são higiene/isolamento. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **Baseline (os dois lados).** `POST /profile` com `{"name": "New Name", "email": "new@example.com"}` (+ `Content-Type: application/json`) → `200`, conta atualizada; `GET /profile` mostra `role: "user"`; `GET /admin` → `403`. **Idêntico** no vulnerable (8025) e no fixed (8125).
2. **O PROBE (VALIDAR RODANDO — validação §11, NÃO risco de versão).** Confirmar que o `account.update()`/`get_json()` do **vulnerable** de fato **copia o campo extra** (`role`) pra conta, e que o **fixed** o **ignora**. Determinístico (semântica de Python) — mas capturar a cadeia real e **travar o comportamento exato** antes de escrever. Confirmar o detalhe do `get_json(silent=True) or {}` (que falta de `Content-Type` → `{}`, não `500`). **NÃO assumir; NÃO inventar.**
3. **O ATAQUE (VALIDAR RODANDO).** `POST /profile` com `{"name": ..., "email": ..., "role": "admin"}` no **vulnerable** (8025) → `GET /profile` mostra `role: "admin"` → `GET /admin` → `200` (conteúdo admin-only). **CAPTURAR** a cadeia real (request/response de cada passo). **Se não reproduzir, PARAR e avisar — NÃO inventar** prova.
4. **FIXED (VALIDAR RODANDO).** O **MESMO** payload → `role` **IGNORADO** (segue `user`); `GET /admin` → `403`. **CAPTURAR.** Confirmar que `name`/`email` legítimos **ainda atualizam** no fixed (a feature funciona).
5. **Prova de isolamento.** O update legítimo (só `name`/`email`) funciona **idêntico** nos dois lados; só o campo extra `role` separa `vulnerable` de `fixed`.
6. **Uma vuln só.** Só o `account.update()` do `POST /profile`; `GET /profile`, `GET /admin` e o login (se houver) **não** são a vuln; o `fixed` muda **só** a seleção de campos. Sem datastore, sem ORM, sem segunda superfície. O `role` no `GET /profile` é a própria conta (não vazamento de outro user).
7. **§8.** Valores **benignos** (`name`/`email` fake, `role:"admin"` benigno, conteúdo admin-only fake — **sem** `flag{}`/CTF, `CLAUDE.md` §12); portas **8025/8125** bind **só** `127.0.0.1`; nada destrutivo; se houver `SECRET_KEY` (sessão opcional), é dummy óbvia.
8. **`app.py` vulnerable × fixed:** confirmar por `diff` que a **única** mudança é a **seleção de campos** no `POST /profile` (`ALLOWED_FIELDS` + o loop vs `account.update(data)`), e que o resto (imports, conta seedada, `GET /profile`, `GET /admin`, `__main__`) e o `Dockerfile`/`requirements.txt` são **idênticos**. **Sem `templates/`, Dockerfile sem `COPY templates`, `app.py` sem `render_template`** (API-only). `./atom up mass-assignment` sobe os dois sem erro. **Validar via `docker exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`).
9. **Theory primer + H1 + CWE.** Confirmar a fonte do primer **por fetch** (PortSwigger API testing mass assignment; se não houver página conceitual limpa, propor OWASP API Security — API3:2023 BOPLA / API6:2019 Mass Assignment — e **avisar o mantenedor**). Confirmar por fetch o **CWE exato** (915 vs o pai 913) e o mapeamento **A01:2021**, e a **grafia do H1** ("Mass Assignment"). **NÃO inventar** URL/grafia.

**Bloqueante remanescente:** nenhum de decisão de design. **Pendências de Fase 2 (não bloqueantes agora):** o probe (item 2 — determinístico, valida rodando) fecha fácil; capturar o ataque no vulnerable e o bloqueio no fixed (itens 3–4); confirmar a fonte/URL/H1/CWE do primer por fetch (item 9, com a decisão OWASP-vs-PortSwigger pro mantenedor); confirmar o pin do Flask por probe; gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **atribuição direta de campos** — sem Saída B, sem ferramenta-que-resiste; o dev despeja o input inteiro no objeto. Cada beat deve poder ser lido com o **`open-redirect` (24)** aberto ao lado (o **CONTRASTE que amarra** — a mesma lição A01 "o servidor decide, não o input"; allowlist server-side; a mesma nota allowlist-vs-blocklist — lá o **destino**, aqui os **campos**) e o **`bola-rest` (12)** ao lado (o molde de **átomo API JSON** com conta em memória; e o **contraste** — BOLA lê objeto de outro/horizontal, mass assignment escreve no próprio/vertical). **Abrir e fechar** na lição-coração: *o app despeja o JSON no objeto; o fix é o servidor listar os campos aceitáveis (allowlist de campos).*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`sqli-union-basic` (01) INTEIRO** (molde canônico de estrutura/WALKTHROUGH/DIFF), **`open-redirect` (24) publicado** (o CONTRASTE que amarra + molde single-container/Burp-only/voz atual + a nota allowlist-vs-blocklist), **`bola-rest` (12) publicado** (molde API-only JSON com conta/usuário em memória, sem HTML, sem browser; e o contraste horizontal-vs-vertical), a família **A01** (03/10/11, molde de átomo A01). **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar trilha browser (nem do 23), encenação, nem arqueologia OWASP.
- **NÃO há Saída B (crítico), e o probe é DETERMINÍSTICO (honesto — diferente do 24):** `dict.update(<json>)` é diretamente mal-usável (sem ORM/schema-validation resistindo). O comportamento do `update()`/`get_json()` **não** é version-dependent (semântica de Python estável) — diferente do `redirect()`/Werkzeug do `24`. O probe é **validação §11**: confirmar rodando que o campo extra entra no vuln e é ignorado no fixed, e **capturar a cadeia real**. **Se não reproduzir como descrito, PARAR e avisar — NÃO inventar** responses. **NÃO introduzir ORM** só pra "ter" o mecanismo idiomático — o ORM é **mencionado como contexto** (nota #2 do DIFF), não usado.
- **Burp-only, SEM browser (como o 24, a diferença deliberada em relação ao 21/23):** a prova é a request/resposta — o `POST /profile` no Repeater, o `role` no `GET /profile`, o status do `GET /admin`. **NÃO** criar seção de browser, **NÃO** usar exceção client-side. `curl` como equivalente (POST/GET com corpo JSON; lembrar do `Content-Type: application/json`).
- **API-only (molde do 12):** sem `templates/`, sem `render_template`, respostas `application/json` via `jsonify`. Dockerfile **sem `COPY templates`**. No "What to read next" do README, **só Burp** — sem `and browser (secondary)`.
- **A prova é a cadeia (riscos #3/#4):** capturar vulnerable → `role` escala + `GET /admin` `200`; fixed → `role` ignorado + `GET /admin` `403`, com `name`/`email` ainda atualizando. **Se não bater rodando, PARAR e avisar — NÃO inventar** prova.
- **A sutileza que NÃO pode enfraquecer a lição:** o fix é **allowlist de CAMPOS** (o servidor lista `name`/`email`), **NÃO** blocklist ("remover `role`"/"rejeitar se vier `role`") — que quebra por ter que lembrar de todo campo perigoso pra sempre, por cada campo novo do modelo virar buraco, e por variações/aninhamento. A blocklist é **DESCRITA, não aplicada** (nota #1 do DIFF, molde 19/20/21/24). **Ligação EXPLÍCITA com a allowlist-vs-blocklist do `24`** (destino vs campos).
- **Mass assignment é icônico em ORMs (nota #2, contexto honesto):** a falha é famosa em frameworks com ORM (o objeto mapeia direto pras colunas; um campo extra vira coluna escrita). Aqui modelamos a MESMA falha com um `dict` cru (o `update` cego), **sem** ORM, pra a lição ficar visível a olho nu. **Mencionar o contexto ORM, NÃO introduzir um** (`CLAUDE.md` §3.6). Isto é descrição da CLASSE, não foreshadow.
- **Uma vuln só:** foco no `account.update()` cego. `GET /profile`/`GET /admin`/login são palco; sem auth real (candidato) reforça que a vuln é a atribuição cega. O `role` no `GET /profile` é a própria conta (não vazamento). Sem datastore, sem ORM, sem 2ª superfície.
- **Abertura seca + trilha Burp-only:** WALKTHROUGH entra direto na mecânica; **sem** encenação; **sem** seção browser. `curl` como equivalente. Rotular os beats: **context (definir mass assignment/allowlist de campos/campo privilegiado/privilege escalation/ORM)** → **spot the bug (`account.update(<json>)` sem selecionar campos)** → **exploitation (baseline `name`/`email` → payload com `role:"admin"` → `role` escala + `GET /admin` abre)** → **o que a vuln NÃO é (não é IDOR/BOLA / não é injection / não é auth bypass)** → **impacto (escalada vertical `user→admin`)** → **fixed (mesmo payload → `role` ignorado, `GET /admin` `403`; `name`/`email` ainda atualizam)**.
- **Impacto honesto:** **escalada de privilégio vertical** (`user→admin`), direta e concreta (`GET /admin` abre). **Sem overclaim** (não inflar pra RCE/takeover de servidor — outros campos sensíveis são **descritos, não armados**). **Sem foreshadow.**
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é a atribuição cega de campos; **não é IDOR/BOLA** (não é objeto de outro user — é o próprio; vertical, não horizontal — contraste com 03/11/12), **não é injection** (não injeta sintaxe; adiciona um campo válido), **não é auth bypass** (a conta é legitimamente sua; o buraco é a atribuição cega).
- **Contraste (cravar):** tabela Mass Assignment↔Open Redirect (o que amarra, com o 24 publicado); tabela Mass Assignment↔IDOR/BOLA (horizontal-vs-vertical, com 03/11/12); prosa "não é injection". Citar publicados (A01 03/10/11/12, 23, 24) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** mass assignment (object injection/autobinding), allowlist de campos, campo privilegiado/sensível, privilege escalation (vertical), ORM, CWE (na estreia do CWE-915).
- **A01 sem arqueologia:** situar em **A01 — Broken Access Control (CWE-915)**, explicar **por que** (controle ausente sobre quais campos o input escreve), **sem** contar edições antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `mass-assignment — Mass Assignment`. "Flask"/"JSON"/"role" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **24** (contraste que amarra), **12** (molde API + contraste horizontal/vertical), a família **A01 03/10/11** (categoria), e os recentes **23/24** (voz), todos publicados. **PROIBIDO** referenciar/foreshadowar **qualquer átomo não-publicado/categoria futura** por número, nome **ou** descrição — inclusive posição/ordinal de fase, release, milestone, e **QUALQUER** menção de "fechar" fase/categoria/"último átomo"/"próxima fase". **A própria spec nasce limpa** (é commitada no repo público): onde precisar situar posição, apontar pro `ROADMAP.md`; nas frases que proíbem foreshadow, manter a proibição **genérica**. O contexto ORM (nota #2) é **descrição da classe**, não átomo futuro.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT**. Termos técnicos (mass assignment, object injection, autobinding, allowlist, blocklist, privilege escalation, ORM, payload, `role`) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): **confirmar a fonte por fetch na Fase 2** (PortSwigger API testing mass assignment; se não houver página conceitual limpa, propor OWASP API Security — API3:2023 BOPLA / API6:2019 Mass Assignment — e **avisar o mantenedor**, desvio consciente do "PortSwigger primeiro", justificado). Nome da página preservado em inglês no PT. **Não inventar.**
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 25: `mass-assignment` — Mass Assignment: a profile-update endpoint copies every field of the client's JSON into the account (`account.update(...)`), so adding `"role": "admin"` escalates a normal user to admin; the fix is a server-side field allowlist that accepts only name/email (A01 Broken Access Control, CWE-915). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release; **NÃO** mencionar "fecha a categoria/fase".
- **ROADMAP.md:** marcar o átomo 25 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–9; reproduzir baseline (`role:user`, `GET /admin` `403`) → ataque (`role:admin`, `GET /admin` `200`) no vulnerable → bloqueio no fixed (`role` ignorado, `403`, `name`/`email` ainda atualizam), via Burp/`curl`. Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8025` (vulnerable), `127.0.0.1:8125` (fixed). Bind **só** em `127.0.0.1`. Single-container.
- Se houver dúvida sobre a fonte/URL/grafia do primer, o CWE exato, o wiring das rotas, o pin do Flask, ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos de field-binding/authorization):

- **`mass-assignment-allowlist-fields-not-blocklist`** — *"O átomo `mass-assignment` (25) entra em A01 (reaproveita `atoms/A01-broken-access-control/`; CWE-915): `POST /profile` faz `account.update(request.get_json(silent=True) or {})` sem selecionar campos → um JSON com `role:"admin"` extra escala a conta demo de `user` pra `admin` (prova: `GET /profile` mostra `role:admin`, `GET /admin` passa de `403` a `200`). SINGLE-CONTAINER (vulnerable :8025 + fixed :8125), API-only (molde do bola-rest 12, sem HTML), conta em memória (dict), sem datastore, sem auth real (uma conta = 'você'; escalada vertical no próprio objeto). BURP-ONLY SEM exceção de browser (como o 24): a prova é a request/resposta. SEM Saída B (dict.update é diretamente mal-usável; sem ORM) — e o probe é DETERMINÍSTICO (dict.update/get_json são semântica estável de Python), diferente do risco version-dependent do 24; validar rodando por §11. Fix = allowlist de CAMPOS server-side (`ALLOWED_FIELDS={'name','email'}`, loop `for field in ALLOWED_FIELDS`), NÃO blocklist ('remover role' — quebra: todo campo perigoso pra sempre, campo novo=buraco, aninhamento). Contraste que AMARRA com o open-redirect 24 (os dois 'allowlist server-side' — destino vs campos, a mesma lição A01 'o servidor decide, não o input'); contraste com IDOR/BOLA 03/11/12 (lê objeto de OUTRO/horizontal vs escreve no PRÓPRIO/vertical). Icônico em ORMs (mencionado, não introduzido). Impacto: escalada vertical user→admin, sem overclaim (não RCE). Theory primer PENDENTE: PortSwigger cobre em API testing (não 'what is X' de topo) → provável OWASP API Security (API3:2023 BOPLA / API6:2019 Mass Assignment), confirmar por fetch. Só Flask==3.0.0 + stdlib, pin NÃO behavior-relevante."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão.
