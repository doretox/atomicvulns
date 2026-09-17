# Spec — Átomo 26: `prototype-pollution`

> Documento de especificação para o Claude Code implementar o átomo `prototype-pollution` do projeto `atomicvulns`. **Posição na ordem de implementação vive no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A08 (Software and Data Integrity Failures)**: a pasta `atoms/A08-data-integrity-failures/` já contém `deserialization-pickle` (20). O 26 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e a pasta do 20 via `ls`). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER, molde do `01 sqli-union-basic` / `20 deserialization-pickle`** — só `vulnerable` + `fixed`, **sem** serviço extra, **sem** datastore, sem listener, sem rede especial. A app guarda config em memória (um objeto JS); a prova vive inteira na **resposta HTTP do próprio alvo**.
>
> **⚠️ STACK NOVA — PRIMEIRO átomo em Node.js do projeto** (os 25 anteriores são Python/Flask). Decisão **TRAVADA** (não redecidir): **Node.js (imagem base LTS PINADA por tag/digest), servidor com o módulo `http` PURO (sem Express, sem framework), corpo da request lido e passado por `JSON.parse` EXPLÍCITO, e o deep-merge ESCRITO À MÃO (sem lib de merge).** Motivo: a falha fica **VISÍVEL NA FONTE** e self-contained — mesma filosofia do `19 ssti-jinja`/`20 deserialization-pickle` (não esconder a vuln no `node_modules`, como o 20 não a escondeu numa lib). **IDEALMENTE zero dependências de runtime**; `package.json` presente só pra **pinar o engine Node**, no mesmo espírito de pinagem dos átomos Python. **Justificativa da exceção Python→Node (`CLAUDE.md` §3.2):** prototype pollution é uma das poucas vulns **idiomáticas de JavaScript** — a `prototype chain` e o `Object.prototype` compartilhado só existem em JS; a falha **perde sentido pedagógico em Python** (que não tem esse modelo de herança por protótipo). O `CLAUDE.md` §3.2 lista "Prototype pollution" explicitamente entre as exceções permitidas. **NÃO alterar o `CLAUDE.md`** — se emergir convenção Node que valha codificar, ela é **PROPOSTA** na seção final desta spec (o mantenedor decide depois).
>
> **A lição em uma linha:** em JavaScript quase todo objeto herda de um pai compartilhado, o `Object.prototype`; ler uma propriedade que o objeto não tem faz o motor subir a cadeia e buscar no pai. A chave `__proto__` é a porta pro pai. Um deep-merge recursivo de JSON não-confiável que desce por `__proto__` não escreve no objeto — escreve no `Object.prototype` **COMPARTILHADO**. A partir daí, **TODO** objeto do processo (inclusive os criados depois, que o atacante nunca tocou) herda aquela propriedade. O estrago vem quando outro código lê uma propriedade assumindo ausência (ex.: `if (user.isAdmin)`) e ela agora existe, **envenenada**. O fix é o merge **RECUSAR** as chaves perigosas.
>
> **§3.3 — trilha Burp-only, SEM a exceção client-side de browser (como o `20 deserialization-pickle` e o `24 open-redirect`, diferente do `21 xss-dom`/`23 csrf-basic`).** Prototype pollution aqui se prova na **REQUEST/RESPOSTA**: montar o `POST /settings` com o payload `__proto__` no **Repeater** (`curl` como equivalente), e ver a contaminação num `GET` de outro endpoint (a resposta muda de "não-admin" pra "admin"). **NÃO** há execução no browser (nenhum script roda no cliente — o JS que importa roda no **servidor** Node), **NÃO** há cookie anexado, **NÃO** há vítima com browser. O ato **definidor** da vuln (o merge descer por `__proto__` e mutar o `Object.prototype` global) é **inteiramente server-side e visível na resposta**. **NÃO usar** a exceção client-side nem qualquer "trilha browser".
>
> Leia junto com o `CLAUDE.md` **atual** (§3.2 — a regra de stack "Node.js só pra vulns idiomaticamente JS", que **autoriza** este átomo; §3.3 — **trilha Burp-only**, e por que **aqui não há** exceção de browser; §3.4 — storage segue a superfície do bug: sem banco; §3.6 — dependências mínimas: idealmente **zero** deps de runtime; §4 — pasta/categoria A08 **já existe**; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, **definir termo técnico na 1ª ocorrência — ATENÇÃO REDOBRADA (1º átomo JS, o leitor pode só saber Python)**, situar em A08 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind `127.0.0.1`** e **ISOLAMENTO**; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico single-container e estrutura de WALKTHROUGH/DIFF), o **`mass-assignment` (25) publicado** (o molde de **VOZ atual** + **API-only** JSON sem HTML + a nota **"mencionável, não aplicada"** — allowlist; é o molde de voz mais próximo), o **`bola-rest` (12) publicado** (o molde **API-only canônico** — estrutura de endpoints JSON, conta/estado em memória, sem HTML), e o **`deserialization-pickle` (20) publicado** — **SÓ pro CONTRASTE A08 (duas faces)** e pra confirmar que o **impacto DIFERE**: 20 = **RCE**; 26 = **corrupção de objeto compartilhado (NÃO RCE por padrão)**.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `package.json`, `Dockerfile`, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A08 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). A justificativa do ROADMAP para este átomo, na parte **não-foreshadow**, é: *"A única vuln que realmente só faz sentido em JS."* (e a marca de ser o primeiro átomo em Node.js — que é **fato de stack**, não foreshadow).
>
> **A categoria A08 JÁ EXISTE — o 26 reaproveita a pasta.** Diferente do `20 deserialization-pickle`, que **criou** `atoms/A08-data-integrity-failures/`, o 26 **não cria pasta**: ela já existe e hospeda `deserialization-pickle` (20). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade) e confirmado por `ls`: `A08-data-integrity-failures/`** (forma abreviada kebab; a categoria OWASP 2021 completa é "Software and Data Integrity Failures", mas o nome de pasta encurta pra `data-integrity-failures`, o padrão que o repo já usa — `A07-auth-failures`, `A10-ssrf`). Pasta final: **`atoms/A08-data-integrity-failures/prototype-pollution/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A08 — Software and Data Integrity Failures"** por extenso.
>
> **Rótulo A08 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Prototype pollution é **A08 — Software and Data Integrity Failures** no OWASP Top 10 2021 (a edição que o projeto segue), mapeada ali via **CWE-1321 (Improperly Controlled Modification of Object Prototype Attributes ('Prototype Pollution'))** — *candidato, confirmar por fetch na Fase 2* (ver "Theory primer" e o risco #12). **NÃO** relatar em que número/edição a categoria caía antes nem histórico de edições — é ruído proibido pela regra atual. **Situar apenas: isto é A08 — Software and Data Integrity Failures (CWE-1321).** Explicar **por que** é integridade de dados (a app trata um blob JSON não-confiável como se fosse seguro pra mesclar num objeto, e a operação de merge **corrompe a integridade** de uma estrutura de dados **compartilhada por todo o processo** — o `Object.prototype`) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec; e a DISCIPLINA DE FORESHADOW (a spec nasce limpa)

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase.
>
> **CRÍTICO (FORESHADOW, `CLAUDE.md` §5) — atenção redobrada, e esta spec É commitada no repo público, então a própria spec nasce limpa:** o átomo (e esta spec) se descreve **isolado**. **PROIBIDO** — no conteúdo do átomo E nesta spec — dizer que este átomo **"abre a fase"/"primeiro da fase"/"próxima fase"/"próximo átomo"**, nomear **milestone** ou **versão de release**, ou foreshadowar átomos futuros (nem por número, nem por slug, nem por descrição). **ATENÇÃO ESPECIAL:** como este é o 1º átomo Node, há tentação de gesticular pra "a outra face de deserialization em Node" ou "outros átomos JS que virão" — **PROIBIDO** (nem por número, nem por nome, nem por descrição). Que a posição deste átomo no `ROADMAP.md` **calhe** de abrir uma fase é **trabalho de release do mantenedor** — não é assunto do átomo nem desta spec. Onde precisar situar posição, **aponta para o `ROADMAP.md`**; nas frases que **proíbem** foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados). **Átomos publicados (o `20 deserialization-pickle`, o `12 bola-rest`, o `25 mass-assignment`, o `01`) e o `ROADMAP.md` são citáveis à vontade.** *(Mesmo cuidado do 20, que abriu a A08 e fechou a Fase 4 sem jamais anunciar isso no conteúdo.)*

## Nota de planning 3 — convenções ATUAIS + STACK NOVA (Node): Burp-only SEM browser, abertura seca, título=classe, A08 sem arqueologia, `http` puro

> Seguir o `CLAUDE.md` **atual**. Pontos a fixar:
>
> - **§3.2 — STACK NOVA autorizada (Node.js).** Prototype pollution é idiomática de JS (a exceção que o §3.2 lista nominalmente). A app é **Node.js + módulo `http` puro** — **SEM Express, SEM framework, SEM lib de merge, idealmente SEM deps de runtime**. O corpo é lido à mão e passado por **`JSON.parse` explícito**; o **deep-merge é escrito à mão**. Isso mantém a vuln **visível na fonte** (não escondida num `node_modules`) — a mesma filosofia dos átomos Python de manter a falha em ~30 linhas legíveis (`CLAUDE.md` §2).
> - **§3.3 — Burp-only, SEM exceção client-side (como o 20/24, diferente do 21/23).** A trilha é **só Burp Suite** (+ `curl` como equivalente). Prototype pollution **aqui** é **server-side observável**: a prova é (a) o `POST /settings` com o payload `__proto__` montado no **Repeater**, e (b) o `GET` do endpoint do objeto fresco mudando de "não-admin" pra "admin". **CUIDADO com o nome:** "prototype pollution" **também** existe como vuln **client-side** (poluir o `Object.prototype` do browser). **NÃO é este átomo.** Aqui o JS que importa roda no **servidor** (Node), a poluição é do `Object.prototype` do **processo Node**, e a prova é a **resposta HTTP** — **NÃO** há JS executando no browser, **NÃO** há cookie anexado, **NÃO** existe "trilha browser" nem exceção client-side. **NÃO criar seção de exploração via browser.**
> - **API-only (sem HTML), molde do `12 bola-rest`/`25 mass-assignment`.** Prototype pollution modelada como endpoint REST puro é **naturalmente API-only** (`CLAUDE.md` §3.3 — a decisão é por átomo: se a vuln só faz sentido em contexto de API, não se força frontend). Sem `templates/`, sem HTML, sem browser; respostas em `application/json` (via `JSON.stringify` + header `Content-Type`). Ver "Renderização".
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (config/preferências que recebem JSON e são mescladas) e a falha (o deep-merge desce por `__proto__`). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5) — ATENÇÃO REDOBRADA (1º átomo JS).** O leitor pode **só conhecer Python**. Os conceitos JS têm que ser explicados **DO ZERO** na 1ª ocorrência: **prototype** (o objeto-pai de onde outro objeto herda propriedades), **prototype chain** (a cadeia de pais que o motor percorre ao ler uma propriedade), **`Object.prototype`** (o pai no topo, do qual quase todo objeto herda — compartilhado por todo o processo), **`__proto__`** (a propriedade acessória que aponta pro prototype de um objeto — a "porta" pro pai), **deep merge** (mesclar recursivamente um objeto de origem noutro de destino, descendo em objetos aninhados), **prototype pollution** (a falha em si). Clareza é **prioridade** — mais do que nos átomos Python, porque o repo inteiro até aqui é Python.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** (candidato "Prototype pollution"), **NÃO** o stack ("...em Node"/"...em JavaScript"/"...com `__proto__`"). O **slug** (`prototype-pollution`) já é a classe — **não** qualifica variante (não é `prototype-pollution-server`). O motor/mecanismo (Node, `http`, `JSON.parse`, o merge) aparece no **corpo**, não no H1.
> - **A08 sem arqueologia** (Nota de planning 1).

---

## Identidade

- **ID:** `prototype-pollution`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A08 — Software and Data Integrity Failures** (via **CWE-1321**, *candidato, confirmar por fetch*). Pasta `atoms/A08-data-integrity-failures/` (**JÁ EXISTE — o 26 reaproveita**; o 20 a criou). Confirmado contra o `ROADMAP.md` ("A08 Data Integrity Failures") e o `CLAUDE.md` §4. Em prosa (README/WALKTHROUGH/DIFF) usar o nome da classe — **"Prototype pollution"** — e a categoria por extenso — **"A08 — Software and Data Integrity Failures"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A08-data-integrity-failures/prototype-pollution/`
- **Número sequencial:** 26
- **Porta `vulnerable`:** `127.0.0.1:8026` (TRAVADO)
- **Porta `fixed`:** `127.0.0.1:8126` (TRAVADO)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o servidor Node no `0.0.0.0` dentro do container); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos single-container 01/12/20/25, adaptado pro Node (`server.listen(5000, process.env.HOST || "127.0.0.1")`).
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM** serviço extra, listener, datastore, mock, ou rede especial. Molde do 01/20/25. Estado (a config/settings) em memória (um objeto JS), mutável de processo único (restart zera **e** reseta a poluição — ver "Prova").
- **Tipo de átomo:** **API-only** (sem HTML, sem `templates/`, sem browser) — molde do `bola-rest` (12)/`mass-assignment` (25). Respostas `application/json`.
- **Stack:** **Node.js LTS (pinado por tag/digest) + stdlib (`http`, `JSON`).** `http` puro, **sem** Express/framework; `JSON.parse` explícito; deep-merge à mão. **IDEALMENTE zero dependências de runtime.** `package.json` presente **só pra pinar o engine Node** (campo `engines`). Ver "Biblioteca / stack" e "O container".
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos, e ZERO menção de "abrir" fase ou de átomos JS futuros** (§5 foreshadow, Nota de planning 2).
- **Branch de trabalho:** `atom/prototype-pollution`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato; confirmar por fetch na Fase 2):** ver a seção "Theory primer". A PortSwigger **tem** página conceitual limpa de prototype pollution — "PortSwigger primeiro" (`CLAUDE.md` §5) vale **sem desvio**; **confirmar a URL exata e a grafia do H1 por fetch na Fase 2** (candidato `https://portswigger.net/web-security/prototype-pollution`). **NÃO inventar URL/grafia.**
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# prototype-pollution — Prototype pollution`** — `id` + nome canônico da **classe** em inglês (a forma que a PortSwigger usa na página). **SEM** "Node"/"JavaScript"/"`__proto__`" no H1. **CONFIRMAR a grafia exata na Fase 2** (casar com o título da página do primer). **Preservar o nome em inglês também no README PT.**

---

## Classe de vulnerabilidade

**Prototype pollution — um deep-merge de JSON não-confiável escreve no `Object.prototype` COMPARTILHADO, e todo objeto do processo herda o campo envenenado.** Uma app tem uma feature de **config/preferências**: o cliente manda um corpo JSON com campos de configuração, e o app **mescla** (deep-merge) esses campos na config atual — descendo recursivamente em objetos aninhados. O jeito ingênuo de escrever esse merge desce, pra cada chave do JSON, no destino correspondente. A falha: quando a chave é **`__proto__`**, o destino correspondente **não é uma propriedade do objeto — é o protótipo dele** (o objeto-pai de onde ele herda). Descer ali e escrever significa **mutar o `Object.prototype`**, o pai compartilhado por **todo** objeto do processo. A partir daí, qualquer objeto — inclusive um recém-criado e vazio, que o atacante nunca tocou — **herda** o campo que o atacante plantou.

**Antes de qualquer coisa, os conceitos de JavaScript (definir DO ZERO — este é o 1º átomo JS do repo):**

- **prototype (protótipo):** em JavaScript, um objeto não guarda só as suas próprias propriedades — ele tem um **objeto-pai**, o *prototype*, de onde **herda** outras propriedades. Se você lê `obj.x` e `obj` não tem um `x` próprio, o motor **sobe** pro prototype e procura `x` lá.
- **prototype chain (cadeia de protótipos):** essa busca não para no primeiro pai — ela sobe uma **cadeia** de pais (`obj` → prototype de `obj` → prototype do prototype → ...) até achar a propriedade ou chegar ao fim. É a **prototype chain**.
- **`Object.prototype`:** no **topo** dessa cadeia, pra quase todo objeto, está um único objeto compartilhado: o **`Object.prototype`**. Um `{}` literal herda dele. `Object.prototype` é **um só** no processo inteiro — **todos** os objetos comuns compartilham esse mesmo pai. É isso que torna a falha global.
- **`__proto__`:** cada objeto expõe uma propriedade acessória chamada **`__proto__`** que **aponta pro seu prototype**. Ler `obj.__proto__` devolve o pai; escrever nele troca/edita o pai. Pra um `{}` comum, `obj.__proto__` **é** o `Object.prototype`. `__proto__` é, literalmente, a **porta pro pai compartilhado**.
- **deep merge:** "mesclar" (merge) dois objetos é copiar os campos de um (a origem) pro outro (o destino). **Deep merge** é fazer isso **recursivamente**: quando um campo é ele próprio um objeto, o merge **desce** e mescla os campos internos, em vez de substituir o objeto inteiro. É um padrão comuníssimo (settings, config, defaults + overrides).
- **prototype pollution (a falha):** um deep-merge que, ao descer pela chave `__proto__`, acaba escrevendo no `Object.prototype` compartilhado em vez de num campo do objeto de destino. O atacante **"polui" o protótipo** — planta uma propriedade no pai de todos os objetos.

**O nome vem disso:** o atacante *polui* (`pollute`) o *protótipo* (`prototype`) — injeta uma propriedade no `Object.prototype`, que **contamina** todo objeto que herdar dele (ou seja, quase todos).

### A lição-coração

> **"Em JavaScript quase todo objeto herda de um pai compartilhado, o `Object.prototype`: ler uma propriedade que o objeto não tem faz o motor subir a cadeia e buscar no pai. A chave `__proto__` é a porta pro pai. Um deep-merge recursivo de JSON não-confiável que desce por `__proto__` não escreve no objeto — escreve no `Object.prototype` COMPARTILHADO. A partir daí, TODO objeto do processo (inclusive os criados depois, que o atacante nunca tocou) herda aquela propriedade. O estrago vem quando outro código lê uma propriedade assumindo ausência (ex.: `if (user.isAdmin)`) e ela agora existe, envenenada. O fix é o merge RECUSAR as chaves perigosas."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** Mesclar config é uma feature **legítima e comum**: o cliente manda campos, o servidor mescla nos defaults. O erro não é aceitar JSON; é o **como** o merge desce. Quando o dev escreve um deep-merge ingênuo, ele *pensa* que está descendo em campos do objeto de config — mas nada no código **impõe** que a chave seja um campo comum. Quando a chave é `__proto__`, "descer no destino" quer dizer **descer no protótipo compartilhado**, e "escrever" quer dizer **mutar o `Object.prototype`**. O atacante não quebra sintaxe nem engana autenticação: ele manda um JSON **perfeitamente bem-formado** onde a chave de topo é `__proto__`. O bug é o merge tratar `__proto__` como um campo qualquer em que se pode descer.

### Sub-lição 1 — o fix é GUARDAR AS CHAVES no merge, NÃO "validar o input"

Cravar (é o coração da nota #1 do DIFF): a defesa **NÃO** é "validar/sanitizar o input". O JSON malicioso é **JSON perfeitamente VÁLIDO** — `{"__proto__":{"isAdmin":true}}` é um objeto JSON bem-formado, com um valor legítimo. Não há sintaxe quebrada pra rejeitar, não há caractere estranho pra escapar. O que separa `vulnerable` de `fixed` é o **merge recusar as chaves perigosas** — o servidor decide que `__proto__` (e as outras) **nunca** são chaves em que se desce. É um bug de **como a estrutura é percorrida**, não de conteúdo do input.

### Sub-lição 2 — POR QUE a superfície é o `JSON.parse` (sutileza-chave, explicar)

Uma sutileza que **explica por que o vetor existe** e vale explicar: o path do `__proto__` só funciona porque **`JSON.parse` cria `__proto__` como uma propriedade de dados PRÓPRIA (own data key)**. Isso é diferente de um object-literal escrito no código, `{ __proto__: ... }`, onde `__proto__` é tratado como um **setter especial** da linguagem (ele *define o prototype* do literal) e **não vira uma chave própria** — então um loop de merge sobre um literal **nunca veria** `__proto__` como chave. Mas o dado do atacante **não** é um literal escrito por um dev — é **texto** que passa por `JSON.parse`, e o parser define `__proto__` como uma **chave de dados normal e enumerável**. Por isso o loop do merge (`Object.keys(source)` / `for...in`) **enxerga** `__proto__` e desce por ela. **É por isso que a superfície é o JSON** (dado não-confiável parseado), e não uma estrutura montada em código. *(Confirmar rodando na Fase 2 — risco #6 — que `Object.keys(JSON.parse('{"__proto__":{}}'))` inclui `__proto__`; é semântica estável do JS/Node, mas validar mesmo assim.)*

### Por que A08 (Software and Data Integrity Failures)

A categoria A08 é sobre **confiar em dados/código cuja integridade não foi verificada** — assumir que um blob de dados que cruzou uma fronteira de confiança é seguro pra ser processado. Prototype pollution é uma **falha de integridade de dados**: a app pega um JSON não-confiável e o mescla numa estrutura, mas a operação de merge **corrompe a integridade de uma estrutura de dados COMPARTILHADA por todo o processo** — o `Object.prototype`. Não é que um objeto específico ficou errado; é que o **pai de todos os objetos** ficou adulterado, e a partir daí a integridade de **qualquer** leitura de propriedade herdada está comprometida. Situar em **A08 — Software and Data Integrity Failures (CWE-1321)**, explicar o **porquê** (integridade de uma estrutura compartilhada corrompida por dado não-confiável), **sem** contar edições antigas.

---

## Contraste com o `20 deserialization-pickle` (justifica coexistir na mesma A08)

O que ancora que o 26 não é "o 20 de novo". Cravar no WALKTHROUGH e no DIFF. Ambos são **A08 — Software and Data Integrity Failures** (integrity failure), mas são vulns **DIFERENTES**, com **impacto DIFERENTE**:

| Eixo | `deserialization-pickle` (20) | `prototype-pollution` (26) |
|---|---|---|
| **Categoria OWASP** | A08 — Software and Data Integrity Failures | A08 — Software and Data Integrity Failures |
| **O que o dado não-confiável faz** | bytes **desserializados**; o **DESEMPACOTADOR executa** comportamento embutido | um objeto **COMPARTILHADO** (`Object.prototype`) é **corrompido**; outro código **CONFIA** nele |
| **Mecanismo** | `pickle.loads` reconstrói e **roda** a função do `__reduce__` | deep-merge desce por `__proto__` e **muta** o protótipo global |
| **Impacto** | **RCE** (execução de comando no servidor) | **subversão de lógica/authz** (SEM execução por padrão) |
| **Fix** | trocar o **FORMATO** (JSON — dados, não comportamento) | o merge **recusar** as chaves perigosas |

**A diferença de IMPACTO é o ponto (contraste mais FROUXO que 09↔20 — aqui o impacto NÃO coincide).** No 20 o desempacotador **executa** → RCE. No 26 **nada executa por padrão**: o atacante corrompe uma estrutura compartilhada, e o dano só aparece quando **outro código** lê uma propriedade herdada assumindo que ela não existe (`if (user.isAdmin)`) e ela agora existe, envenenada — **subversão de lógica/autorização**, não execução. **Causa, mecanismo e IMPACTO diferentes; só a CATEGORIA (A08) coincide.** *"Duas faces do A08."* **"Um átomo = uma vuln" se refere à CAUSA** (`CLAUDE.md` §2): a causa aqui (mutar um protótipo compartilhado via merge) não tem nada a ver com a causa do 20 (desserializar formato-com-comportamento). Citar o 20 (publicado) no contraste **sem forçar** — o vínculo é a categoria, não o impacto.

---

## Uma vuln só — o foco é o merge sem guarda; a prova é o objeto fresco; SEM RCE, SEM 2ª superfície

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o **deep-merge recursivo sem guarda de chaves perigosas**. Garantias e sutilezas (todas validar na Fase 2):

- **A única superfície é o corpo JSON do `POST /settings`** chegando ao merge. `GET /me` (a prova) e o merge benigno (a feature) **não** são a vuln — são o palco.
- **SEM RCE.** O átomo prova **corrupção de objeto compartilhado → subversão de authz** (`GET /me` vira admin), **não** execução de comando. RCE via prototype pollution existe no mundo real, mas **exige gadgets específicos** de libs/ambiente (uma cadeia onde uma propriedade herdada envenenada acaba num `child_process`/template/etc.) — isso é **fora do escopo**, quebraria a atomicidade (seriam dois átomos). O impacto honesto é a subversão de lógica. Ver "Impacto honesto".
- **O fixed GUARDA as 3 chaves no merge, NÃO troca de estrutura.** A correção aplicada é a **guarda de chaves** (`__proto__`/`constructor`/`prototype`) no merge. Trocar pra `Object.create(null)`/`Map`/`Object.hasOwn` é a **defesa estrutural mais robusta** — mas é a **nota-mencionável-não-aplicada** (nota #3 do DIFF), **não** o que o átomo aplica. Manter o fixed com a **mesma estrutura** do vulnerable + a guarda isola o diff na guarda. Ver "O fix".
- **Sem datastore, sem 2ª dependência, sem 2ª superfície.** Nenhum banco, nenhuma lib de merge, nenhuma dep de runtime (idealmente). A config vive em memória.
- **API-only → sem HTML, sem autoescape/rendering a considerar** (é JSON). Elimina de origem qualquer XSS acidental (nenhum valor é refletido em contexto HTML). Ver "Renderização".

---

## Flavor — MERGE DE PREFERÊNCIAS (TRAVADO)

App **API-only** que guarda **config/preferências** em memória. Dois endpoints:

- **`POST /settings`** — recebe um corpo JSON do usuário e faz **deep-merge** nos settings da app. **É AQUI QUE A VULN MORA** (o merge recursivo sem guarda no `vulnerable`; com a guarda das 3 chaves no `fixed`). Responde os settings atualizados (JSON). **Superfície = o corpo JSON** (didático: input não é só formulário — é qualquer coisa que o usuário controla, aqui um corpo de request mesclado numa estrutura).
- **`GET /me`** (nome sensato à escolha; `/me` é o candidato) — **NÃO relacionado aos settings.** Cria um **objeto NOVO E VAZIO** representando um usuário/sessão **default SEM privilégio**, e checa `if (freshObj.isAdmin)` → responde admin/não-admin (JSON, ex.: `{"admin": false}`). **Este endpoint é a prova.**

**O ataque:** `{"__proto__":{"isAdmin":true}}` no `POST /settings`; depois o `GET /me` responde **admin**. **O PONTO CENTRAL:** esse objeto fresco do `/me` **NUNCA foi tocado pelo atacante** — o atacante mexeu em `/settings`, um endpoint completamente diferente. É a **prova de contaminação GLOBAL** (o `Object.prototype` foi envenenado, e o objeto novo herda o veneno), **não** de "editei os settings". Se a prova fosse "os settings agora têm `isAdmin`", seria confundível com mass assignment (25) — daí o objeto fresco e **desconectado** ser essencial.

**Estado em memória, SEM datastore (`CLAUDE.md` §3.4 — o storage segue a superfície do bug: prototype pollution não depende de storage, é o merge que corrompe o protótipo do processo).** Os `settings` são um objeto no módulo, seedado no import, mutável de processo único (restart zera **e** reseta a poluição). Notar como o 12/25 notaram pros seus stores.

**Sem autenticação real (candidato).** O `GET /me` não precisa de login: ele **cria** um objeto de sessão default (sem privilégio) a cada request — a demo é justamente "um usuário default, sem privilégio nenhum, vira admin sem nunca ter tocado no endpoint que o promoveu". Auth real (senha, sessão) está **fora de escopo** (mesmo atalho do 12/25). *(Não transformar o `/me` numa superfície de auth — ele é o **objeto-prova**, não um fluxo de login.)*

**Settings seedados com um objeto ANINHADO (candidato).** Pra o deep-merge ter onde **descer recursivamente** (senão o "deep" do merge não aparece), os settings default começam com pelo menos um objeto aninhado — ex.: `{ theme: "light", notifications: { email: true } }`. Assim um merge benigno (`{"notifications":{"email":false}}`) exercita a recursão de forma legítima, e o payload `__proto__` exercita a **mesma** recursão de forma maligna. Confirmar na Fase 2.

**Superfície = o merge no `POST /settings`.** `GET /me` (a prova) e o merge benigno **NÃO são a vuln** — são o palco. Uma única superfície: a guarda (ausente) de chaves no merge. **Sem** segunda superfície, **sem** datastore, **sem** lib.

---

## Prova — CONTIDA E OBSERVÁVEL (TRAVADO; §8)

A prova é o endpoint do **objeto fresco** (`GET /me`) virar **admin DEPOIS** do ataque, tendo sido **não-admin ANTES**. Flag **benigna** `isAdmin` (nada destrutivo, nada de rede, nada fora do container).

- **Baseline LIMPO (ANTES do ataque, os dois lados):** `GET /me` → `{"admin": false}` (o objeto fresco não tem `isAdmin`; `undefined` é falsy). **Idêntico** no `vulnerable` (:8026) e no `fixed` (:8126). **Capturar isto PRIMEIRO.**
- **O ataque (no `vulnerable`, :8026):** `POST /settings` com `{"__proto__":{"isAdmin":true}}` → o merge desce por `__proto__` e faz `Object.prototype.isAdmin = true` → `GET /me` agora → **`{"admin": true}`** (o objeto fresco **herda** `isAdmin` do protótipo poluído). **A prova é o objeto fresco — intocado pelo atacante — respondendo admin.**
- **No `fixed` (:8126):** o **MESMO** payload → o merge **recusa** a chave `__proto__` (não desce por ela) → `Object.prototype` **intacto** → `GET /me` segue **`{"admin": false}`**. E um merge benigno (`{"theme":"dark"}`) **ainda funciona** (a feature funciona) nos dois lados.

**ATENÇÃO À ORDEM (crítico — a poluição é GLOBAL e PERSISTE).** Poluir o `Object.prototype` é **global no processo** e **persiste** até o restart — não há "des-poluir" no fluxo normal. Consequência pra ordem de captura no WALKTHROUGH: **capturar o baseline LIMPO (`GET /me` → não-admin) ANTES do ataque.** Depois do ataque, o processo do `vulnerable` fica **sujo** até o restart. **Documentar explicitamente:** *"restart do container reseta a poluição"* (`./atom down`/`up`, ou `docker compose restart vulnerable`) — pra re-rodar o baseline limpo. Isso **molda a ordem** dos beats do walkthrough (baseline → ataque, sem "voltar" no meio).

**§8:** valores **benignos** — `isAdmin: true` é um valor benigno (não é payload destrutivo, não faz rede, não sai do container). Tudo loopback. A poluição fica **contida no processo Node do container** e some no restart. Nada destrutivo.

---

## O código — o coração no deep-merge sem guarda

O fix é **SERVER-SIDE** (no código do servidor Node), como no 20/25. O arquivo do servidor **DIFERE** entre `vulnerable` e `fixed`; o **único delta é a guarda de chaves no merge**. `Dockerfile` e `package.json` são **idênticos** entre os dois lados (não há templates — API-only; não há deps — idealmente).

> **Sobre o candidato de código abaixo:** é **candidato** — a Fase 2 gera o real e **valida rodando** (riscos #1–#11). O nome do arquivo é **`app.js`** (paralelo ao `app.py` dos átomos Python). O ponto travado é o **desenho**: `http` puro, `JSON.parse` explícito, deep-merge à mão, a guarda das 3 chaves como único delta.

### `vulnerable/app.js` — deep-merge recursivo SEM guarda (candidato — Fase 2 gera o real)

```javascript
const http = require("http");

// --- In-memory settings for the app (no database) ---
// Preferences the user can edit. Nested on purpose so the merge must RECURSE --
// which is exactly where the bug lives.
const settings = { theme: "light", notifications: { email: true } };

function isObject(value) {
  return typeof value === "object" && value !== null;
}

// Recursively merge `source` into `target`, descending into nested objects.
// VULNERABLE: nothing stops the key "__proto__". Because `source` came from
// JSON.parse, "__proto__" is a real OWN key, so the loop reaches it. For a normal
// object, target["__proto__"] is not a field -- it is the object's PROTOTYPE,
// i.e. Object.prototype, the parent shared by EVERY object in the process.
// Descending there and writing mutates Object.prototype globally.
function merge(target, source) {
  for (const key of Object.keys(source)) {
    if (isObject(source[key])) {
      if (!(key in target)) {
        target[key] = {};
      }
      merge(target[key], source[key]); // for key "__proto__": recurses into Object.prototype
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

function readBody(req, callback) {
  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", () => callback(body));
}

function sendJson(res, status, obj) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(obj));
}

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/settings") {
    readBody(req, (body) => {
      let incoming;
      try {
        incoming = JSON.parse(body); // explicit parse: "__proto__" arrives as an OWN key
      } catch (e) {
        return sendJson(res, 400, { error: "invalid JSON" });
      }
      merge(settings, incoming); // SINK: deep-merge untrusted JSON into the settings
      return sendJson(res, 200, settings);
    });
    return;
  }
  if (req.method === "GET" && req.url === "/me") {
    // A brand-new, empty object standing for a default, UNPRIVILEGED session.
    // The attacker never touches this object. But if Object.prototype was polluted,
    // `user.isAdmin` is now INHERITED as true -- proof of GLOBAL contamination.
    const user = {};
    return sendJson(res, 200, { admin: user.isAdmin === true });
  }
  return sendJson(res, 404, { error: "not found" });
});

const HOST = process.env.HOST || "127.0.0.1";
server.listen(5000, HOST);
```

### `fixed/app.js` — MESMA função + guarda das 3 chaves (candidato — Fase 2 gera o real)

```javascript
// ... (idêntico ao vulnerable, EXCETO a função merge) ...

// FIXED: refuse the three keys that reach a shared prototype before descending.
// "__proto__" is the DIRECT door to Object.prototype. "constructor"/"prototype"
// are the INDIRECT door: constructor.prototype is the same shared parent, so
// guarding only "__proto__" is bypassable (see DIFF note). Skipping all three
// keeps the merge writing only real, own data keys of the target object.
function merge(target, source) {
  for (const key of Object.keys(source)) {
    if (key === "__proto__" || key === "constructor" || key === "prototype") {
      continue;
    }
    if (isObject(source[key])) {
      if (!(key in target)) {
        target[key] = {};
      }
      merge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}
```

**O CONTRASTE é o diff:** o `merge` do `vulnerable` (sem guarda) vs o do `fixed` (as 3 linhas de guarda `if (key === ... ) continue;` no topo do loop). Todo o resto (`settings`, `isObject`, `readBody`, `sendJson`, os handlers, o `listen`) é **byte-idêntico**.

### Notas de implementação (validar/decidir na Fase 2)

- **A forma do merge — `!(key in target)` (candidato, ESCOLHIDO por honestidade da nota #2 do DIFF).** O merge desce sempre que `source[key]` é objeto, criando `target[key]={}` só se a chave **não existir** em `target` (via `key in target`, que consulta a prototype chain). **Por que essa forma e não a clássica `isObject(source[key]) && isObject(target[key])`:** com essa forma, **tanto** `__proto__` **quanto** `constructor.prototype` poluem se desguardados — o que torna a **nota #2 do DIFF HONESTA** (guardar só `__proto__` é de fato burlável **neste merge**). A forma clássica (`&& isObject(target[key])`) bloquearia o path do `constructor` por acidente (`target["constructor"]` é uma **função**, e `isObject(função)` é `false`), o que tornaria a nota #2 **enganosa** pra este átomo. **DECISÃO:** usar a forma `!(key in target)` **e VALIDAR RODANDO na Fase 2** (risco #3 e #11) que: (a) `__proto__` polui; (b) `constructor.prototype` **também** poluiria se só `__proto__` fosse guardado; (c) as 3 chaves guardadas bloqueiam ambos. Se a Fase 2 preferir a forma clássica, **então** a nota #2 tem que ser reescrita pra não afirmar bypass demonstrável — mas a forma `!(key in target)` é a preferida **exatamente** pra manter a nota honesta. **NÃO deixar a nota #2 afirmar um bypass que o merge do átomo não sofre.**
- **`Object.keys(source)` vs `for...in` (candidato: `Object.keys`).** `Object.keys` retorna só as chaves **próprias** — e `JSON.parse('{"__proto__":{}}')` cria `__proto__` como chave própria (sub-lição 2), então `Object.keys` **enxerga** `__proto__` (é o vetor). Vantagem sobre `for...in`: **depois** de o processo ser poluído, `for...in` sobre qualquer objeto passaria a enumerar também o `isAdmin` **herdado** do protótipo sujo, sujando merges subsequentes; `Object.keys` (só próprias) evita esse ruído. Confirmar na Fase 2 (risco #6) que `Object.keys(JSON.parse('{"__proto__":{}}'))` inclui `__proto__` — semântica estável, mas validar.
- **`readBody` + `JSON.parse` explícito com `try/catch` (candidato — higiene idêntica nos dois lados).** O corpo é lido à mão e passado por `JSON.parse` **explícito** (decisão travada). O `try/catch` (400 em JSON inválido) é **higiene operacional idêntica nos dois lados**, ortogonal à vuln — evita derrubar o processo Node com um corpo malformado (um `throw` não-capturado no callback do `end` **mataria o servidor**, péssimo pra um lab). Consequência prática pro walkthrough: o `POST /settings` **precisa** de corpo JSON válido (e, na prática, `Content-Type: application/json` é boa higiene no Repeater, ainda que o parse aqui não dependa do header). Confirmar na Fase 2.
- **`GET /me` — `user.isAdmin === true` (candidato).** Comparar com `=== true` (em vez de só `if (user.isAdmin)`) deixa a resposta binária e limpa (`{"admin": true|false}`) e evita ambiguidade de *truthiness*. Antes da poluição, `user.isAdmin` é `undefined` → `false`; depois, o protótipo poluído entrega `true`. O texto exato da resposta é latitude de Fase 2 (dado benigno, §8 — **sem** segredo real, **sem** `flag{}`/CTF, `CLAUDE.md` §12).
- **A poluição NÃO aparece na resposta do `/settings`.** `JSON.stringify(settings)` serializa só as propriedades **próprias** de `settings` — e a poluição foi no `Object.prototype`, não em `settings`. Então a resposta do `POST /settings` continua "normal" (`{"theme":...,"notifications":...}`), **sem** mostrar `isAdmin`. Isso **reforça** a lição: o `/settings` parece inocente; a prova está no `/me`. Confirmar na Fase 2 (risco #3).
- **Estado mutável de processo único + poluição persistente.** Após o ataque no `vulnerable`, o `Object.prototype` fica poluído **até o restart**. Fazer o **baseline LIMPO ANTES** do ataque (a ordem natural) evita precisar "resetar" no meio; notar que restart zera (para re-rodar). Higiene de lab, como o 20/25 notaram.
- **Sem HTML, sem `templates/`** (API-only). Ver "Renderização" e "O container".

---

## O fix e o tipo de diff

**Fix:** **guardar as três chaves mágicas no merge, server-side** — no topo do loop do `merge`, **pular** (`continue`) as chaves `__proto__`, `constructor` e `prototype`. Tipo de diff: **cirúrgico** — a introdução das 3 linhas de guarda. O resto (a estrutura `settings`, `isObject`, `readBody`, `sendJson`, os handlers do `http`, o `listen`) é **byte-idêntico**. A guarda é o delta, e ela liga **causa↔fix**: a causa é o merge descer por chaves que alcançam o protótipo; o fix é o merge **recusar** exatamente essas chaves.

Diff colável (candidato — a Fase 2 gera o real; recorte da função `merge`):

```diff
 function merge(target, source) {
   for (const key of Object.keys(source)) {
+    // FIXED: refuse the three keys that reach a shared prototype.
+    if (key === "__proto__" || key === "constructor" || key === "prototype") {
+      continue;
+    }
     if (isObject(source[key])) {
       if (!(key in target)) {
         target[key] = {};
       }
       merge(target[key], source[key]);
     } else {
       target[key] = source[key];
     }
   }
   return target;
 }
```

**O CONTRASTE é o diff (obrigatório):** o `merge` **sem** guarda (vulnerable) vs **com** a guarda das 3 chaves (fixed). **A única mudança é o merge recusar as chaves perigosas.** O resto do arquivo é idêntico.

### Notas obrigatórias no `DIFF.md`

1. **A causa é o merge DESCER por chaves perigosas, NÃO "validar/sanitizar o input" (nota "mencionável, não aplicada" — molde 19/20/21/24/25).** O JSON malicioso `{"__proto__":{"isAdmin":true}}` é **JSON perfeitamente VÁLIDO** — não há sintaxe quebrada nem caractere estranho pra rejeitar. **Prova de isolamento:** um merge **benigno** (`{"theme":"dark"}`) funciona **igual** nos dois apps (a feature é idêntica); só o payload com `__proto__` separa os dois — o vulnerable polui (o `GET /me` vira admin), o fixed não. **Cravar a assimetria fina:** não é bug de input malformado; é bug de **como a estrutura é percorrida** (o merge desce por uma chave que alcança o protótipo compartilhado). A defesa é o servidor **recusar** essas chaves no merge, não filtrar conteúdo.
2. **POR QUE as TRÊS chaves e não só `__proto__` (nomear a intuição, mostrar o bypass, cravar).** Nomear a intuição errada: *"é só bloquear `__proto__`"*. Mostrar **por que isso é BURLÁVEL**: `constructor.prototype` **também** chega no pai compartilhado — o payload `{"constructor":{"prototype":{"isAdmin":true}}}` desce `settings.constructor` (a função `Object`) → `.prototype` (que **é** o `Object.prototype`) e polui **igual**, sem nunca usar a chave `__proto__`. Então uma guarda que bloqueia **só** `__proto__` deixa a porta dos fundos aberta. **Cravar:** por isso a guarda robusta recusa as **três** — `__proto__` (a porta direta), `constructor` e `prototype` (a porta indireta via `constructor.prototype`). **DECISÃO TRAVADA:** o `constructor.prototype` é **CITADO nesta nota** como o motivo de guardar as três — **NÃO é exploitado no walkthrough** (o walkthrough demonstra só o payload `__proto__`). Mesmo espírito das notas #2 do 25/17/18/19 (nomear a intuição fraca, mostrar por que quebra). *(Ver a nota de implementação "A forma do merge" — a forma `!(key in target)` é escolhida justamente pra este bypass ser REAL neste merge, mantendo a nota honesta; a Fase 2 valida rodando.)*
3. **A defesa ROBUSTA de produção é ESTRUTURAL — nota-mencionável-NÃO-aplicada (molde 17 IMDSv2 / 18 defusedxml / 19 sandbox / 20 HMAC / 25 allowlist).** A guarda de chaves (o que o átomo aplica) é uma **blocklist de chaves** — ela funciona, mas é o mesmo espírito de "caçar o proibido". A defesa **estrutural** (o alvo real em produção) **remove a possibilidade de raiz**:
   - **`Object.create(null)`** — cria um objeto **SEM protótipo** (sem pai). Não há `Object.prototype` na cadeia dele → **nada pra poluir** por aquele objeto; e ler `obj.__proto__` nele é só uma propriedade comum, não a porta pro pai.
   - **`Map`** — o dicionário **real** do JS (chave→valor de verdade), onde `__proto__` é só uma **string inofensiva** como qualquer outra chave, não um acessor mágico. Guardar dados controlados pelo usuário num `Map` (em vez de num objeto comum) fecha o vetor.
   - **`Object.hasOwn(obj, k)`** (ou `Object.prototype.hasOwnProperty.call`) — ao **ler**, checar só a propriedade **própria**, ignorando o que veio do protótipo. Um `if (Object.hasOwn(user, "isAdmin"))` não é enganado por um protótipo poluído.
   - **Nomear esses como o alvo REAL** e explicar que a **blocklist de chave** (a guarda das 3) é um **remendo** que funciona pra este vetor mas continua guardando um padrão frágil (um objeto comum mesclado com dado não-confiável). **NÃO aplicar** no átomo (o fix aplicado é a guarda; a estrutura fica igual pra isolar o diff). *(HMAC-style/assinatura **não** entra aqui — não há blob assinado; a analogia com a nota #3 do 20 é o **formato/estrutura**, não a assinatura.)*
4. **IMPACTO + CONTRASTE com o 20 (mesma A08, impacto DIFERENTE).** **Contaminação GLOBAL do `Object.prototype` → subversão de lógica/authz:** qualquer código que leia uma propriedade herdada assumindo ausência (`if (user.isAdmin)`) é subvertido — o exemplo do lab é o `GET /me` virar admin. **CONTRASTE com o `20 deserialization-pickle`:** ambos A08 (integrity failure), mas o **impacto DIFERE** — o 20 é **RCE** (o desempacotador executa); o 26 é **corrupção de objeto compartilhado** (outro código confia nele), **SEM execução por padrão**. **Sem overclaim:** o átomo prova a subversão de authz (`GET /me` → admin); **NÃO** é RCE (isso exigiria gadgets específicos de libs/ambiente — fora do escopo). Teto **diferente** do 20.

---

## Biblioteca / stack

- **Runtime:** **Node.js LTS, imagem base PINADA por tag/digest** (`CLAUDE.md` §8.5 — sem CVE "de brinde"; e o espírito de pinagem dos átomos Python). Candidato de base: uma tag LTS estável do `node` slim (ex.: `node:20-bookworm-slim` ou a LTS vigente na Fase 2) **+ digest `@sha256:...`** pra reprodutibilidade. **Confirmar a tag LTS exata e o digest na Fase 2** — NÃO cravar sem verificar.
- **Dependências de runtime: IDEALMENTE ZERO** (`CLAUDE.md` §3.6). `http` e `JSON` são **stdlib** do Node. **Sem** Express, **sem** lib de merge (`lodash.merge`/`deepmerge`/etc.), **sem** body-parser — tudo à mão. Isso mantém a vuln **na fonte**, não no `node_modules` (a filosofia do §2/§3.6, e o paralelo direto do 20 que não escondeu a falha numa lib).
- **`package.json` — só pra pinar o engine Node** (candidato — idêntico nos dois lados):

```json
{
  "name": "prototype-pollution",
  "version": "1.0.0",
  "private": true,
  "engines": { "node": ">=20 <21" }
}
```

  Sem `dependencies` (zero deps). Sem `package-lock.json` necessário (não há deps a travar). O `engines` **documenta** a versão-alvo; a **pinagem efetiva** é a tag/digest da imagem base (que é o que roda). **Confirmar o range exato do `engines` (casar com a LTS da imagem base) na Fase 2.**
- **Comportamento estável, mas VALIDAR (probe = validação §11, risco #6).** A semântica que o átomo usa — `JSON.parse` criar `__proto__` como own key, e a recursão do merge mutar o `Object.prototype` global — é **estável** no JS/Node (não é version-dependent como o PyJWT do 14/lib do 18). **Ainda assim, confirmar RODANDO na Fase 2** (na versão pinada) que: (a) `Object.keys(JSON.parse('{"__proto__":{}}'))` inclui `__proto__`; (b) o merge polui `Object.prototype`; (c) um objeto fresco `{}` herda o campo poluído. **Gate:** "não reproduziu → PARA e avisa, não inventa."

---

## WALKTHROUGH — abertura seca, trilha Burp-only (SEM browser)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (config/preferências que recebem JSON e são mescladas) e a falha (o deep-merge desce por `__proto__` e muta o protótipo compartilhado). Trilha **ÚNICA: Burp** (`curl` como equivalente — POST/GET simples com corpo JSON; a prova é a resposta do `GET /me`). **NÃO** criar seção de browser (o JS roda no **servidor** Node, não no cliente). **DEFINIR do zero os conceitos JS na 1ª ocorrência** (1º átomo JS — o leitor pode só saber Python).

**Abertura (candidato — plantar a lição, seco):**

> *A app guarda as suas preferências: você manda um JSON com campos de config e ela **mescla** esses campos nos settings atuais, descendo recursivamente em objetos aninhados — um `deep merge`. Em JavaScript, quase todo objeto herda de um pai compartilhado chamado `Object.prototype`, e a chave `__proto__` de um objeto é a porta pra esse pai. O problema: o merge desce por qualquer chave do seu JSON — inclusive `__proto__`. Mande `{"__proto__":{"isAdmin":true}}` e o merge, em vez de escrever num campo dos settings, escreve no `Object.prototype` **compartilhado por todo objeto do processo**. A prova está num endpoint que nem fala de settings: o `GET /me` cria um objeto de usuário novo e vazio e checa `if (user.isAdmin)` — e agora, embora você nunca tenha tocado nesse objeto, ele responde admin.*

Beats (molde do 20/25 publicado — abertura seca, seções numeradas `## 1..6`, Burp-only, API-only):

1. **Context.** Feature: `POST /settings` recebe JSON e faz deep-merge nos settings; `GET /me` cria um objeto de sessão default e checa `isAdmin`. **Definir na estreia (DO ZERO):** **prototype** (objeto-pai de onde se herda propriedades), **prototype chain** (a cadeia de pais percorrida ao ler uma propriedade), **`Object.prototype`** (o pai no topo, compartilhado por todo objeto do processo), **`__proto__`** (a porta pro pai de um objeto), **deep merge** (mesclar recursivamente, descendo em objetos aninhados), **prototype pollution** (a falha). Isto é **Prototype pollution**, sob **A08 — Software and Data Integrity Failures (CWE-1321)**. Topologia: `vulnerable` (:8026), `fixed` (:8126), single-container, API-only, **Node.js** (`http` puro). Trilha: **Burp/curl** — a prova é a resposta.
2. **Spot the bug.** Mostrar a função `merge` do `vulnerable` — o loop que desce por **cada** chave do JSON, sem recusar nenhuma. Pergunta de auditoria: *"esse merge desce por QUALQUER chave — inclusive `__proto__`? E `__proto__` do objeto de destino é um campo dele, ou é o protótipo compartilhado?"* → é o protótipo. Explicar a sub-lição 2 na estreia: o `JSON.parse` entrega `__proto__` como **chave própria** (por isso o loop a enxerga). Foreshadow do fix: o merge **recusar** `__proto__` (e as outras portas pro pai).
3. **Exploitation via Burp Suite (a prova é a resposta).**
   - **Baseline LIMPO (capturar PRIMEIRO — a poluição persiste):** `GET /me` → `{"admin": false}` (objeto fresco, sem `isAdmin`); e um merge **benigno** `POST /settings` com `{"theme":"dark"}` → `200`, feature funciona. Idêntico no vulnerable e no fixed. Bloco colável no Repeater (request-line + `Content-Type: application/json` + corpo). Equivalente `curl`. **Cravar a ordem:** baseline **antes** do ataque, porque poluir é global e persiste até o restart.
   - **Montar o payload:** o corpo JSON `{"__proto__":{"isAdmin":true}}`. Explicar: a chave de topo `__proto__` faz o merge descer no protótipo compartilhado, e `isAdmin: true` é escrito lá.
   - **Disparar (o ataque, no vulnerable :8026):** `POST /settings` com `{"__proto__":{"isAdmin":true}}` → `200`. **Nota:** a resposta do `/settings` parece **normal** (não mostra `isAdmin`) — a serialização só vê as propriedades próprias de `settings`; a poluição foi no protótipo. **Provar:** `GET /me` agora → **`{"admin": true}`**. **A prova é o objeto fresco do `/me` — que o atacante nunca tocou — virar admin** (contaminação global, não edição de settings).
   - **§8 (cravar):** valor **benigno** (`isAdmin: true`), tudo loopback; a poluição fica contida no processo Node do container e some no restart; nada destrutivo, nada de rede.
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa:
   - **NÃO é "editei os settings".** Você não escreveu `isAdmin` **nos settings** — a prova é o `GET /me`, um endpoint que **nem fala de settings** e cria um objeto **novo e vazio**. Ele vira admin porque o **pai compartilhado** (`Object.prototype`) foi envenenado, não porque os settings mudaram. *(Contraste com o `mass-assignment` (25), publicado: lá o atacante escreve um campo extra **no próprio objeto** que ele está atualizando; aqui o atacante envenena o **protótipo global**, e um objeto **terceiro e intocado** herda o veneno.)*
   - **NÃO é o `deserialization-pickle` (20), e NÃO é RCE.** Ambos são A08, mas aqui **nada executa por padrão** — o atacante **corrompe uma estrutura compartilhada**, e o dano aparece quando **outro código** confia nela. No 20 o desempacotador **executa** → RCE; aqui é subversão de lógica/authz. **Mesma categoria, impacto diferente.** *(Ver "Contraste com o 20".)*
   - **NÃO é bug de validação.** O JSON `{"__proto__":{"isAdmin":true}}` é **JSON válido** — não há input malformado pra rejeitar. Não dá pra "sanitizar" o conteúdo; é o **merge descer por uma chave que alcança o protótipo** que executa a falha. *(Ver DIFF nota #1.)*
   - **O que É (prova):** o merge desce por `__proto__` e muta o `Object.prototype` **compartilhado**; todo objeto do processo (inclusive o `{}` fresco do `/me`) herda o campo. A correção é o merge **recusar** as chaves que alcançam o protótipo (`__proto__`, `constructor`, `prototype`).
5. **Impact (honesto — sem overclaim).** **Contaminação GLOBAL do `Object.prototype`** → qualquer código que leia uma propriedade herdada assumindo ausência é subvertido; o exemplo do lab é o **bypass de authz** (`GET /me` vira admin). A poluição **persiste no processo** até o restart. **Sem overclaim:** é subversão de lógica/authz **no processo**, **NÃO** RCE por padrão (RCE via prototype pollution existe, mas exige **gadgets** específicos de libs/ambiente — fora do escopo deste átomo). **Teto diferente do `20 deserialization-pickle`** (que é RCE).
6. **Why the fix works (porta 8126).** Repetir contra o `fixed/`:
   - **O MESMO payload** (`{"__proto__":{"isAdmin":true}}`) → o merge **recusa** a chave `__proto__` (não desce por ela) → `Object.prototype` **intacto** → `GET /me` segue **`{"admin": false}`**. **Confirmar que o merge benigno (`{"theme":"dark"}`) ainda funciona** (a feature não quebra).
   - **Prova de isolamento:** o merge benigno funciona **idêntico** nos dois lados; só o payload `__proto__` separa `vulnerable` de `fixed`.
   - **A lição do diff:** o fix é a **guarda das 3 chaves** no merge (nota #1 — não é validar input; nota #2 — por que **três** e não só `__proto__`: `constructor.prototype` também alcança o pai); a defesa **estrutural** de produção (`Object.create(null)`/`Map`/`Object.hasOwn`) é **mencionada, não aplicada** (nota #3); **impacto honesto** = contaminação global → subversão de authz, contraste com o 20 (mesma A08, mas RCE lá, não aqui) (nota #4).

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Payloads/responses (o `{"admin": true}` no `GET /me` pós-ataque) são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**Prototype pollution — contaminação global de objeto compartilhado → subversão de lógica/authz, sem overclaim.** O átomo prova **uma** coisa: um `POST /settings` com `{"__proto__":{"isAdmin":true}}` envenena o `Object.prototype` do processo, e um objeto **novo e intocado** (o `{}` do `GET /me`) passa a **herdar** `isAdmin: true` — um `if (user.isAdmin)` que assumia ausência é subvertido. Isso é **corrupção de uma estrutura de dados compartilhada por todo o processo**, com impacto de **subversão de lógica/autorização** (o exemplo do lab é o bypass de authz). A poluição **persiste** até o restart.

**Sem overclaim:** o átomo **NÃO** demonstra RCE. Prototype pollution **pode** escalar pra RCE no mundo real, mas **só com gadgets específicos** — uma cadeia onde uma propriedade herdada envenenada acaba fluindo pra um sink perigoso de alguma lib/ambiente (`child_process`, um template engine, `require`, etc.). Isso depende do ecossistema em volta e **não** é uma propriedade da falha isolada; incluir seria **empilhar** um segundo mecanismo (quebrando "um átomo = uma vuln"). **Teto diferente do `20 deserialization-pickle`** (RCE por causa própria). O valor da classe está em quão **silenciosa e global** ela é: uma única chave num JSON contamina **todo** objeto do processo, e o dano brota longe do ponto de injeção, em qualquer leitura de propriedade herdada que assumia ausência. Isso é **descrição da CLASSE**, **NÃO** uma chain armada neste átomo. **Sem foreshadow** (§5 / Nota de planning 2 — nada de "abre a fase" nem menção a átomos/versões futuras nem a "a outra face em Node").

---

## Renderização / "um átomo = uma vuln"

**API-only, respostas JSON via `JSON.stringify` + `Content-Type: application/json`** — **sem HTML, sem templates** (`CLAUDE.md` §3.3 — prototype pollution modelada como REST puro é naturalmente API-only; molde do 12/25), logo **sem risco de XSS acidental**: nenhum valor é refletido em contexto HTML. Isso **elimina de origem** a preocupação de reflected XSS.

Garantir que a **ÚNICA** lição é o merge sem guarda:

- **`GET /me` NÃO é a vuln.** É só o palco/prova: cria um objeto fresco e mostra se ele herdou `isAdmin`. A **única** superfície é o merge (ausente de guarda) no `POST /settings`.
- **O `fixed` muda SÓ o merge** (as 3 linhas de guarda). Todo o resto (`settings`, `isObject`, `readBody`, `sendJson`, os handlers, o `listen`) é **byte-idêntico**. A **guarda de chaves é o único delta**.
- **SUTILEZA (crítica): o `fixed` GUARDA as 3 chaves no merge, NÃO troca de estrutura** (`Object.create(null)`/`Map`/`Object.hasOwn`) — essa é a **defesa-mencionável-não-aplicada** da nota #3 do DIFF. Trocar de estrutura no fixed **desalinharia** o diff (deixaria de ser "a guarda") e é deliberadamente **descrito, não aplicado**.
- **Sem datastore, sem lib de merge, sem 2ª superfície, sem segredo real.** Estado em memória; sem auth real (candidato) — reforça que a vuln é o merge, não a identidade. O conteúdo do `/me` é benigno óbvio (§8, sem `flag{}`/CTF).
- **Sem HTML → sem autoescape a considerar.** A saída é `application/json` (`JSON.stringify`), não HTML. Nenhuma reflexão em contexto de marcação.

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` — molde do `bola-rest` (12)/`mass-assignment` (25) (**API-only → SEM `COPY templates`**), adaptado pro Node. Só o runtime Node — **sem `npm install`** (zero deps de runtime), **sem** `apt`, **sem** banco.

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** (candidato — idênticos entre si; a Fase 2 fixa a tag/digest LTS):

```dockerfile
# Pin the LTS base by tag AND digest in Phase 2 (e.g. node:20-bookworm-slim@sha256:...).
FROM node:20-bookworm-slim
WORKDIR /app
COPY package.json .
# No `npm install`: zero runtime dependencies (http + JSON are stdlib).
COPY app.js .
# Override default host (127.0.0.1) so Docker's port forwarding can reach Node.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["node", "app.js"]
```

**`docker-compose.yml`** (candidato — molde do 01/12/20/25, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8026:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8126:5000"
```

**Sem `networks:`, sem serviço extra, sem `depends_on`, sem healthcheck, sem `COPY templates`.** Molde simples do 01/20 menos os templates (API-only, como o 12/25), com o runtime trocado pra Node. **§8:** bind **só** `127.0.0.1` (8026/8126).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **A PortSwigger TEM página conceitual limpa de prototype pollution** — diferente do `mass-assignment` (25), aqui **não há desvio**: "PortSwigger primeiro" (`CLAUDE.md` §5) vale direto. Candidato (confirmar por fetch): **`https://portswigger.net/web-security/prototype-pollution`** (título esperado **"Prototype pollution"**, framing "What is prototype pollution?").
- **Confirmar por fetch na Fase 2** (risco #12): a **URL exata**, a **grafia do H1** ("Prototype pollution", casando com a página), e o **CWE** (candidato **CWE-1321** — "Improperly Controlled Modification of Object Prototype Attributes ('Prototype Pollution')") e o mapeamento **A08:2021**. **NÃO inventar** URL/grafia/CWE.
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7), casando com a grafia exata da página.
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo dos irmãos 01/20/25).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A08 — Software and Data Integrity Failures** (`atoms/A08-data-integrity-failures/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `prototype-pollution` em A08; `CLAUDE.md` §4 fixa a pasta (o 20 a criou). CWE-1321 (confirmar). Situar em A08 **sem arqueologia**. |
| Posição na fase | Ver `ROADMAP.md` | A posição/ordinal/release vivem só no ROADMAP. Spec e conteúdo nascem **limpos** (foreshadow §5); **ZERO** menção de "abrir" fase ou de átomos JS futuros (Nota de planning 2). |
| **Stack** | **Node.js LTS (pinado tag+digest) + `http` puro + `JSON.parse` explícito + deep-merge à mão; ZERO deps de runtime; `package.json` só pra `engines`** | 1º átomo Node. `CLAUDE.md` §3.2 autoriza (prototype pollution é idiomática de JS). §3.6/§2: vuln **na fonte**, não no `node_modules` (paralelo ao 20). |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Molde do 01/20/25. Sem serviço extra, sem datastore. Estado em memória. |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | REST puro; molde do 12/25. JSON via `JSON.stringify` → sem XSS acidental. |
| Trilha | **Burp-only (+ curl), SEM browser** | §3.3 atual. A prova é a request/resposta (server-side; o JS roda no **servidor** Node). **SEM** exceção client-side (como o 20/24). CUIDADO: prototype pollution client-side existe, **não é este átomo**. |
| Lição-coração | **Deep-merge de JSON não-confiável desce por `__proto__` e muta o `Object.prototype` COMPARTILHADO; todo objeto (inclusive os frescos) herda o veneno. Fix: o merge RECUSAR as chaves perigosas.** | A raiz é o merge percorrer uma chave que alcança o protótipo compartilhado. |
| Sub-lição 1 | **O fix é GUARDAR AS CHAVES, não "validar o input"** | O JSON malicioso é JSON VÁLIDO; não há o que sanitizar. É um bug de como a estrutura é percorrida. |
| Sub-lição 2 | **A superfície é o `JSON.parse`: ele cria `__proto__` como own key** (≠ object-literal, onde `__proto__` é setter e não vira chave) | Por isso o loop do merge enxerga `__proto__` e desce por ela. Validar rodando (risco #6). |
| Por que A08 | **Corrupção da integridade de uma estrutura COMPARTILHADA (`Object.prototype`) por dado não-confiável** | Integrity failure: outro código confia numa estrutura adulterada. CWE-1321. |
| Contraste central | **`deserialization-pickle` (20)** — mesma A08, impacto DIFERENTE (RCE lá; corrupção de objeto compartilhado aqui, sem RCE) | "Duas faces do A08." Contraste FROUXO (o impacto não coincide). Citar o 20 sem forçar. |
| Flavor — **TRAVADO** | **Merge de preferências** (`POST /settings` deep-merge JSON) + `GET /me` (objeto fresco vazio, `if (isAdmin)`) | Superfície = o merge. A prova = o objeto fresco INTOCADO virar admin (contaminação global, não edição de settings). |
| Prova — **TRAVADO** | **`GET /me` vira `{"admin": true}` DEPOIS do ataque, era `false` ANTES** | Objeto fresco nunca tocado pelo atacante. Flag benigna `isAdmin`. Capturar baseline LIMPO ANTES (poluição persiste). |
| Ordem de captura | **Baseline limpo ANTES do ataque; restart reseta a poluição** | Poluir `Object.prototype` é global e persiste até restart. Molda a ordem dos beats. |
| Código vulnerable | **`merge(target, source)` recursivo SEM guarda** (`Object.keys` + `!(key in target)`) | Desce por `__proto__` → muta `Object.prototype`. Forma `!(key in target)` escolhida pra o bypass de `constructor` ser REAL (nota #2 honesta). |
| Código fixed | **MESMA função + `if (key === "__proto__" || "constructor" || "prototype") continue`** | Guarda as 3 chaves no topo do loop. Único delta. |
| Fix (único eixo) | **Guardar as 3 chaves mágicas no merge** | Blocklist de chaves; a defesa estrutural (`Object.create(null)`/`Map`/`hasOwn`) é mencionada-não-aplicada (nota #3). |
| Diff | **Cirúrgico** — as 3 linhas de guarda; resto byte-idêntico | Causa↔fix: o merge recusa exatamente as chaves que alcançam o protótipo. |
| Por que 3 chaves | **`constructor.prototype` também alcança o pai** — guardar só `__proto__` é burlável | Nota #2. Cravar o bypass (citado, NÃO exploitado no walkthrough). |
| Impacto | **Contaminação global → subversão de lógica/authz.** NÃO RCE por padrão (exige gadgets — fora de escopo). | Honesto; teto DIFERENTE do 20. Sem overclaim, sem foreshadow. |
| Theory primer | **PortSwigger Prototype pollution** (`/web-security/prototype-pollution`, confirmar por fetch) | Página conceitual "what is X?" existe (sem desvio, ≠ 25). Não inventar. Nome em inglês no PT. |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. Definir conceitos JS do zero (1º átomo JS). |
| Título (H1) | **`prototype-pollution — Prototype pollution`** (classe, sem stack) | `CLAUDE.md` §5. Sem "Node"/"JavaScript"/"`__proto__`". Slug = classe (não qualifica variante). Grafia confirmável na Fase 2. |
| Foreshadow | **ZERO pra frente + ZERO "abrir" fase + ZERO "outra face em Node"** | `CLAUDE.md` §5 / Nota de planning 2. Publicados (01, 12, 20, 25) e ROADMAP OK. |
| Portas | **8026 / 8126** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–7 são os centrais; 8–12 são higiene/isolamento. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **Servidor sobe; merge benigno funciona.** `./atom up prototype-pollution` sobe os dois sem erro. `POST /settings` com uma chave **benigna** (`{"theme":"dark"}`, `+ Content-Type: application/json`) → `200`, settings atualizados; a feature funciona nos dois lados (8026 e 8126).
2. **Baseline LIMPO capturado ANTES do ataque.** `GET /me` → `{"admin": false}` no vulnerable e no fixed, **antes** de qualquer payload malicioso. **Capturar isto primeiro** (a poluição persiste).
3. **O ATAQUE (central — VALIDAR RODANDO).** `POST /settings` com `{"__proto__":{"isAdmin":true}}` no **vulnerable** (8026) → `GET /me` passa a `{"admin": true}`. **CAPTURAR a cadeia real** (request/response de cada passo). Confirmar também que a resposta do `POST /settings` **não** mostra `isAdmin` (só própria de `settings`). **Se não reproduzir, PARAR e avisar — NÃO inventar** prova.
4. **FIXED (VALIDAR RODANDO).** O **MESMO** payload no **fixed** (8126) → `GET /me` segue `{"admin": false}` (a chave `__proto__` é recusada). **CAPTURAR.** Confirmar que o merge benigno (`{"theme":"dark"}`) **ainda funciona** no fixed (a feature não quebra).
5. **Prova de isolamento.** O merge benigno (`{"theme":"dark"}`) mescla **idêntico** nos dois lados; só o payload `__proto__` separa `vulnerable` de `fixed`.
6. **Probe determinístico (§11, NÃO risco de versão) — VALIDAR RODANDO.** Confirmar na versão pinada: (a) `Object.keys(JSON.parse('{"__proto__":{}}'))` inclui `__proto__` (own key); (b) a recursão do merge muta `Object.prototype` global; (c) um objeto fresco `{}` herda o campo poluído. Semântica estável do JS/Node, mas **validar mesmo assim**; **gate: "não reproduziu → PARA e avisa, não inventa".**
7. **Uma vuln só.** A única falha é o merge sem guarda no `POST /settings`; `GET /me` é palco/prova; o `fixed` muda **só** a guarda de chaves. Sem datastore, sem lib de merge, sem 2ª superfície. O `/me` não é auth real.
8. **§8.** bind **só** `127.0.0.1` (8026/8126); single-container; flag benigna (`isAdmin`, sem `flag{}`/CTF, `CLAUDE.md` §12); nada destrutivo, nada de rede, nada fora do container. A poluição fica contida no processo Node do container.
9. **Persistência da poluição.** Confirmar que o processo do vulnerable fica **sujo** após o ataque (o `GET /me` continua admin até o restart) e que **restart reseta** (`./atom down`/`up` ou `docker compose restart vulnerable`). Isso **molda a ORDEM da captura** (baseline antes).
10. **Diff = só a guarda.** Confirmar por `diff` que a **única** mudança entre `vulnerable/app.js` e `fixed/app.js` é a guarda das 3 chaves no `merge`, e que o resto do arquivo + `Dockerfile` + `package.json` são **byte-idênticos**. **Sem `templates/`, Dockerfile sem `COPY templates`, sem HTML** (API-only). **Validar via `docker exec` + `curl`/cliente HTTP de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`).
11. **Fix recusa as TRÊS chaves (`__proto__`/`constructor`/`prototype`) — VALIDAR RODANDO.** Confirmar que: (a) no **vulnerable**, `{"constructor":{"prototype":{"isAdmin":true}}}` **também** polui (justifica a nota #2 e a escolha da forma `!(key in target)` do merge); (b) no **fixed**, tanto `__proto__` quanto `constructor.prototype` são **recusados** (o `GET /me` segue não-admin pros dois). **DECISÃO:** o `constructor.prototype` é **CITADO na nota #2 do DIFF, NÃO exploitado no walkthrough** — mas **validar rodando** que o bypass é real no merge, senão a nota #2 fica enganosa (nesse caso, reescrever a nota ou ajustar a forma do merge). **Se a forma do merge não sofrer o bypass de `constructor`, PARAR e reconciliar — NÃO deixar a nota afirmar um bypass inexistente.**
12. **Theory primer + H1 + CWE por fetch.** Confirmar por fetch a **URL** do primer (PortSwigger `/web-security/prototype-pollution`), a **grafia do H1** ("Prototype pollution"), e o **CWE** (candidato **CWE-1321**) + mapeamento **A08:2021**. **NÃO inventar** URL/grafia/CWE.

**Bloqueante remanescente:** nenhum de decisão de design. **Pendências de Fase 2 (não bloqueantes agora):** fixar a tag/digest LTS da imagem base Node e o range do `engines`; reproduzir o ataque no vulnerable e o bloqueio no fixed (itens 3–4); validar o probe determinístico (item 6) e o bypass de `constructor` no merge (item 11); confirmar URL/H1/CWE do primer por fetch (item 12); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **uso-direto-do-antipadrão** (deep-merge ingênuo de JSON não-confiável) — sem "Saída B", sem ferramenta-que-resiste; o dev escreve o merge à mão e ele desce por `__proto__`. Cada beat deve poder ser lido com o **`mass-assignment` (25)** aberto ao lado (o molde de **voz atual** + API-only + a nota "mencionável não aplicada") e o **`bola-rest` (12)** ao lado (o molde **API-only canônico** de endpoints JSON com estado em memória). **Abrir e fechar** na lição-coração: *o merge desce por `__proto__` e muta o protótipo compartilhado; todo objeto herda o veneno; o fix é o merge recusar as chaves perigosas.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`sqli-union-basic` (01) INTEIRO** (molde canônico de estrutura/WALKTHROUGH/DIFF), **`mass-assignment` (25) publicado** (VOZ atual + API-only + nota mencionável-não-aplicada), **`bola-rest` (12) publicado** (molde API-only JSON, estado em memória, sem HTML), **`deserialization-pickle` (20) publicado** (SÓ pro contraste A08 — impacto DIFERE). **Seguir o `CLAUDE.md` ATUAL** — Burp-only, abertura seca, título=classe, A08 sem arqueologia.
- **STACK NOVA (Node) — travada:** `http` puro (sem Express/framework), `JSON.parse` explícito, deep-merge à mão, **zero deps de runtime** (idealmente), `package.json` só pra `engines`, imagem base LTS **pinada por tag+digest**. A vuln fica **na fonte** (não no `node_modules`) — a filosofia do §2/§3.6 e o paralelo do 20. **NÃO** introduzir lib de merge, **NÃO** usar Express.
- **Burp-only, SEM browser (como o 20/24):** a prova é a request/resposta — o `POST /settings` no Repeater, o `{"admin": true}` no `GET /me`. **NÃO** criar seção de browser. **CUIDADO com o nome:** "prototype pollution" também é uma vuln **client-side** (browser); **este átomo NÃO é isso** — o JS roda no **servidor** Node, a poluição é do processo Node, a prova é HTTP. `curl` como equivalente (POST/GET com corpo JSON; `Content-Type: application/json` no Repeater).
- **API-only (molde do 12/25):** sem `templates/`, sem HTML, respostas `application/json` via `JSON.stringify`. Dockerfile **sem `COPY templates`**. No "What to read next" do README, **só Burp** — sem `and browser (secondary)`.
- **A prova é o objeto FRESCO (riscos #2/#3):** capturar baseline limpo (`GET /me` → não-admin) **ANTES**; depois o ataque no vulnerable → `GET /me` vira admin; o fixed → segue não-admin. **A ORDEM importa** (poluir é global e persiste; restart reseta). **Se não bater rodando, PARAR e avisar — NÃO inventar** prova.
- **A sutileza que NÃO pode enfraquecer a lição:** o fix é **guardar as 3 chaves no merge** (`__proto__`/`constructor`/`prototype`), **NÃO** trocar de estrutura. A defesa estrutural (`Object.create(null)`/`Map`/`Object.hasOwn`) é a **nota #3 mencionável-não-aplicada** (molde 17/18/19/20/25). Trocar de estrutura desalinharia o diff.
- **POR QUE três chaves (nota #2):** `constructor.prototype` também chega no pai compartilhado; guardar só `__proto__` é burlável. **Cravar o bypass** (citado na nota, **NÃO** exploitado no walkthrough — decisão travada). A forma `!(key in target)` do merge é escolhida pra o bypass ser **real neste merge** (nota honesta) — **validar rodando** (risco #11); se não for real, reconciliar a nota, **não** afirmar bypass inexistente.
- **Uma vuln só:** foco no merge sem guarda. `GET /me` é palco/prova; sem auth real reforça que a vuln é o merge, não a identidade. Sem datastore, sem lib de merge, sem 2ª superfície.
- **Abertura seca + trilha Burp-only:** WALKTHROUGH entra direto na mecânica; **sem** encenação; **sem** seção browser. `curl` como equivalente. Rotular os beats: **context (definir prototype/prototype chain/`Object.prototype`/`__proto__`/deep merge DO ZERO)** → **spot the bug (merge sem guarda; `JSON.parse` entrega `__proto__` como own key)** → **exploitation (baseline limpo → payload `__proto__` → `GET /me` vira admin, objeto fresco intocado)** → **o que a vuln NÃO é (não é "editei settings" / não é o 20 / não é RCE / não é bug de validação)** → **impacto (contaminação global → subversão de authz, persiste até restart)** → **fixed (mesmo payload → merge recusa `__proto__`, `GET /me` segue não-admin; benigno ainda funciona)**.
- **Impacto honesto:** **contaminação global → subversão de lógica/authz**, direta e concreta (`GET /me` vira admin). **Sem overclaim** (NÃO RCE por padrão — RCE exige gadgets, fora de escopo). **Teto diferente do 20.** **Sem foreshadow.**
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é o merge descer por chaves que alcançam o protótipo; **não é "editei os settings"** (a prova é o objeto fresco intocado; contraste com o 25, que escreve no próprio objeto), **não é o 20 / não é RCE** (mesma A08, impacto diferente), **não é bug de validação** (o JSON é válido).
- **DEFINIR termo na 1ª ocorrência — ATENÇÃO REDOBRADA (1º átomo JS, `CLAUDE.md` §5):** prototype, prototype chain, `Object.prototype`, `__proto__`, deep merge, prototype pollution — **todos DO ZERO**, porque o leitor pode só saber Python. Clareza é prioridade.
- **A08 sem arqueologia:** situar em **A08 — Software and Data Integrity Failures (CWE-1321)**, explicar **por que** (corrupção de integridade de estrutura compartilhada por dado não-confiável), **sem** contar edições antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `prototype-pollution — Prototype pollution`. "Node"/"JavaScript"/"`__proto__`" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **20** (contraste A08 — impacto difere), **25** (voz + contraste "não editei o próprio objeto"), **12** (molde API), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar **qualquer átomo não-publicado/categoria futura** por número, nome **ou** descrição — inclusive posição/ordinal de fase, release, milestone, "abrir fase", e **QUALQUER** menção de "a outra face em Node"/"próximos átomos JS"/"próxima fase". **A própria spec nasce limpa** (é commitada no repo público): onde precisar situar posição, apontar pro `ROADMAP.md`; nas frases que proíbem foreshadow, manter a proibição **genérica**.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT**. Termos técnicos (prototype pollution, prototype, prototype chain, `Object.prototype`, `__proto__`, deep merge, payload, sink) **não** se traduzem no PT — mas ganham **definição na estreia** (§5).
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (Prototype pollution), **confirmar a URL por fetch na Fase 2** (existe página conceitual limpa — sem desvio, ≠ 25). Nome da página preservado em inglês no PT. **Não inventar.**
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 26: `prototype-pollution` — Prototype pollution: a hand-written deep-merge of untrusted JSON descends through the `__proto__` key and writes onto the shared `Object.prototype`, so `{"__proto__":{"isAdmin":true}}` poisons every object in the process — a brand-new, untouched object at `GET /me` inherits `isAdmin` and is treated as admin; the fix guards the merge against the `__proto__`, `constructor`, and `prototype` keys (A08 Software and Data Integrity Failures, CWE-1321). `` (padrão das linhas dos átomos anteriores; grafia do CWE a confirmar por fetch). **NÃO** cortar a versão/taggear/anunciar release; **NÃO** mencionar "abre a fase"/próximos átomos.
- **ROADMAP.md:** marcar o átomo 26 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline limpo (`GET /me` não-admin) → ataque (`__proto__`, `GET /me` admin) no vulnerable → bloqueio no fixed (`__proto__` recusado, `GET /me` não-admin; benigno ainda funciona), via Burp/`curl`. Validar via `docker exec` + `curl`/cliente HTTP de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8026` (vulnerable), `127.0.0.1:8126` (fixed). Bind **só** em `127.0.0.1`. Single-container.
- Se houver dúvida sobre a tag/digest LTS do Node, o range do `engines`, a URL/grafia do primer, o CWE exato, a forma do merge (e o bypass de `constructor`), o wiring das rotas, ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Propostas (não aplicar; só registrar pro mantenedor decidir)

> Regra do repo: o Claude Code **propõe**, o mantenedor **decide** (`CLAUDE.md` §10.2 e "Memória de projeto"). Nada abaixo é aplicado nesta spec.

### (a) Convenção Node no `CLAUDE.md` (se a stack se provar reusável)

Este é o **primeiro** átomo Node do repo (fato de stack). A convenção de stack que este átomo estabeleceu **poderia** ser codificada no `CLAUDE.md` (§3.2/§4 ou uma subseção de stack) — o mantenedor decide se/quando. Convenção candidata a registrar:

- Runtime Node.js LTS, imagem base **pinada por tag+digest**.
- **`http` puro sem framework** por padrão (Express só se a vuln for idiomática do Express e perder sentido sem ele — mesma lógica da exceção Python→Node do §3.2).
- **Deep-merge / parsing à mão** quando a vuln vive nesse código (manter na fonte, não no `node_modules`).
- **`package.json` só pra pinar `engines`**; **zero deps de runtime** por padrão.
- Nome do arquivo do servidor: **`app.js`** (paralelo ao `app.py` dos átomos Python).

**NÃO alterar o `CLAUDE.md` agora** — isto é proposta. O mantenedor decide se/quando codificar.

### (b) Memória candidata (opcional — decisão do mantenedor)

Não gravei nada (o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido:**

- **`node-atom-stack-pattern`** — *"Átomos idiomaticamente-JS (1º: `prototype-pollution` 26) usam Node.js LTS pinado por tag+digest, servidor com módulo `http` PURO (sem Express/framework), corpo lido à mão + `JSON.parse` explícito, lógica-alvo escrita à mão (ex.: deep-merge), `package.json` só pra pinar `engines`, ZERO deps de runtime. Filosofia: vuln VISÍVEL NA FONTE, não escondida no `node_modules` (paralelo ao 20 pickle). API-only (sem HTML), single-container, bind 127.0.0.1. Justificativa da exceção Python→Node: `CLAUDE.md` §3.2 (só vulns idiomáticas de JS)."* — tipo `project`.

**Ressalva (lean):** esse fato vai ficar **registrado nesta spec commitada e no DIFF/README** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). A memória só vale se for técnica **reusável de verdade** — e isso ainda não está confirmado. Proponho **não** gravar por ora, a menos que você queira o pointer antecipado. **Sua decisão.**
