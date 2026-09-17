# Spec — Átomo 27: `deserialization-node`

> Documento de especificação para o Claude Code implementar o átomo `deserialization-node` do projeto `atomicvulns`. **Posição na ordem de implementação vive no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A08 (Software and Data Integrity Failures)**: a pasta `atoms/A08-data-integrity-failures/` já hospeda `deserialization-pickle` (20) e `prototype-pollution` (26). O 27 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e a pasta existente via `ls`). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER, molde do `01 sqli-union-basic` / `20 deserialization-pickle` / `26 prototype-pollution`** — só `vulnerable` + `fixed`, **sem** serviço extra, **sem** datastore, sem listener, sem rede especial.
>
> **⚠️ STACK Node.js — o SEGUNDO átomo Node do repo** (o `26 prototype-pollution` foi o primeiro; os demais são Python/Flask). Decisão **TRAVADA** (não redecidir): **Node.js (imagem base LTS PINADA por tag+digest, molde do 26), servidor com o módulo `http` PURO (sem Express, sem framework), corpo/cookie lidos e tratados à mão.** A **única** diferença de infra em relação ao 26: o `26` tinha **zero** dependências de runtime; o `27` tem **UMA** dep de runtime **no `vulnerable`** — a lib `node-serialize` — porque **a lib É o objeto de estudo** (o desserializador perigoso deste ecossistema chega como **package npm**, não na stdlib). O **`fixed` volta a ZERO deps** (usa `JSON.parse`, stdlib). Consequência direta e proposital: `package.json` e `Dockerfile` **DIFEREM** entre `vulnerable` e `fixed` (o vulnerable tem `node-serialize` em `dependencies` + `RUN npm install`; o fixed não tem nem um nem outro) — e **essa diferença faz parte da lição** (o desserializador perigoso é uma dependência, não a stdlib). Isso **diverge** do 20 (pickle/json ambos stdlib → `requirements.txt` idêntico) e do 26 (zero deps → `Dockerfile`/`package.json` idênticos). **Justificativa da exceção Python→Node (`CLAUDE.md` §3.2):** deserialization em Node é um dos casos **nominais** que o §3.2 lista ("Deserialization em Node — quando o objetivo é mostrar o ecossistema JS"). O ponto pedagógico é **exatamente** mostrar que a mesma classe (insecure deserialization) se materializa **em cada ecossistema com um mecanismo próprio** — em Python via `pickle`/`__reduce__` (stdlib), em Node via `node-serialize`/`_$$ND_FUNC$$_` (npm). **NÃO alterar o `CLAUDE.md`** — se emergir convenção Node que valha codificar, ela é **PROPOSTA** na seção final desta spec (o mantenedor decide depois).
>
> **A lição em uma linha:** desserializar dado não-confiável com um formato/lib que carrega **COMPORTAMENTO** (não só dados) executa código do atacante. A lib **`node-serialize`** serializa funções JavaScript e, ao desserializar, faz **`eval`** delas; uma função marcada para **auto-invocar** roda **no momento do `unserialize`** — **RCE (Remote Code Execution)**. O fix é usar um formato que só carrega **DADOS** (JSON via `JSON.parse`).
>
> **§3.3 — trilha Burp-only, SEM exceção client-side de browser (como o `20 deserialization-pickle` e o `26 prototype-pollution`, diferente do `21 xss-dom`/`23 csrf-basic`).** Deserialization em Node é **server-side**: a prova é o **efeito observável no servidor** (o marcador `/tmp/pwned`), lido via `docker compose exec`, **não** o browser. **NÃO** há execução no browser (nenhum script roda no cliente — o JS que importa roda no **servidor** Node). **NÃO criar seção de exploração via browser.**
>
> Leia junto com o `CLAUDE.md` **atual** (§3.2 — a exceção de stack que **autoriza** este átomo, com "deserialization em Node" listada nominalmente; §3.3 — **trilha Burp-only** e **API-only**, e por que **aqui não há** exceção de browser; §3.6 — dependências mínimas: **só** `node-serialize` no vulnerable, **zero** no fixed; §4 — pasta/categoria A08 **já existe**; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo técnico na 1ª ocorrência, situar em A08 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`** e **ISOLAMENTO, ATENÇÃO DOBRADA porque o exploit é RCE**; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico single-container), o **`deserialization-pickle` (20) publicado — o GÊMEO** (o átomo é o paralelo Node desta falha; o **contraste com ele é o eixo do átomo**; leia app.py vulnerable+fixed, WALKTHROUGH, DIFF, README EN+PT), e o **`prototype-pollution` (26) publicado — o único precedente NODE do repo** (molde de: Node `http` puro, API-only, base pinada por tag+digest, `ENV HOST=0.0.0.0` + bind `127.0.0.1` no compose, a nota de stack, a **voz atual** e o **§7 PT com headers traduzidos**).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `package.json`, `Dockerfile`, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A08 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). A justificativa do ROADMAP para este átomo, na parte **não-foreshadow**, é: *"par natural com `deserialization-pickle` (átomo 20), mas no ecossistema Node."*
>
> **A categoria A08 JÁ EXISTE — o 27 reaproveita a pasta.** Diferente do `20 deserialization-pickle`, que **criou** `atoms/A08-data-integrity-failures/`, o 27 **não cria pasta**: ela já existe e hospeda `deserialization-pickle` (20) e `prototype-pollution` (26). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade) e confirmado por `ls`: `A08-data-integrity-failures/`** (forma abreviada kebab; a categoria OWASP 2021 completa é "Software and Data Integrity Failures", mas o nome de pasta encurta pra `data-integrity-failures`, o padrão que o repo já usa — `A07-auth-failures`, `A10-ssrf`). Pasta final: **`atoms/A08-data-integrity-failures/deserialization-node/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A08 — Software and Data Integrity Failures"** por extenso.
>
> **Rótulo A08 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Insecure deserialization é **A08 — Software and Data Integrity Failures** no OWASP Top 10 2021 (a edição que o projeto segue). **NÃO** relatar em que número/edição a categoria caía antes, nem histórico de edições — é ruído proibido pela regra atual (o `20 deserialization-pickle`, o gêmeo, já foi escrito sob ela e **não** conta edições). **Situar apenas: isto é A08 — Software and Data Integrity Failures.** Explicar **por que** é integridade de dados (a app trata um cookie serializado, que cruzou uma fronteira de confiança, como seguro pra reconstruir, e o formato/lib reconstrói **comportamento** — código do atacante) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec; e a DISCIPLINA DE FORESHADOW (a spec nasce limpa)

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase.
>
> **CRÍTICO (FORESHADOW, `CLAUDE.md` §5) — e esta spec É commitada no repo público (é o 1º commit da Fase 2), então a própria spec nasce limpa:** o átomo (e esta spec) se descreve **isolado**. **PROIBIDO** — no conteúdo do átomo E nesta spec — nomear átomos **não publicados** (por número, slug ou descrição), citar **posição/ordinal de fase**, **release**, **milestone**, ou dizer que o átomo **"abre" ou "fecha" fase**. Onde precisar situar posição, **aponta para o `ROADMAP.md`**; nas frases que **proíbem** foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados). **Átomos publicados (o `20 deserialization-pickle`, o `26 prototype-pollution`, o `01`) e o `ROADMAP.md` são citáveis à vontade.** *(Mesmo cuidado do 20 e do 26, que jamais anunciaram sua posição no conteúdo.)*

## Nota de planning 3 — convenções ATUAIS + STACK Node: Burp-only SEM browser, API-only, abertura seca, título=classe, A08 sem arqueologia, `http` puro, headers PT traduzidos

> Seguir o `CLAUDE.md` **atual**. Pontos a fixar:
>
> - **§3.2 — STACK Node autorizada.** Deserialization em Node é um dos casos **nominais** do §3.2 ("Deserialization em Node — quando o objetivo é mostrar o ecossistema JS"). A app é **Node.js + módulo `http` puro** — **SEM Express, SEM framework**. A **única** dep de runtime é `node-serialize` **no vulnerable** (o objeto de estudo); o **fixed tem zero deps** (usa `JSON.parse`). Isso mantém o desserializador perigoso **visível** (a lib nomeada, uma linha de `require`), não escondido atrás de uma abstração.
> - **§3.3 — Burp-only, SEM exceção client-side (como o 20/26).** A trilha é **só Burp Suite** (+ `curl` como equivalente). Deserialization em Node é **server-side observável**: a prova é o **marcador no servidor** (`/tmp/pwned`), lido via `docker compose exec`. **NÃO** há JS executando no browser (o JS que importa roda no **servidor** Node). **NÃO criar seção de exploração via browser.**
> - **API-only (sem HTML), molde do `26 prototype-pollution`.** Deserialization modelada como endpoint puro é naturalmente API-only. Sem `templates/`, sem HTML, sem browser; respostas em `application/json` (via `JSON.stringify` + header `Content-Type`). A superfície é o **header `Cookie`** (didático: input não é só formulário — é o cookie que o usuário controla; espelha o cookie-pickle do 20). Ver "Renderização".
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (preferências num cookie serializado) e a falha (o cookie é desserializado com uma lib que dá `eval` em funções). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** serialização/desserialização, `node-serialize`, o marcador `_$$ND_FUNC$$_`, `eval`, IIFE (immediately-invoked function expression — função que se auto-invoca), RCE, base64, JSON — dar a expansão/definição na estreia. Como este é o 2º átomo Node (o leitor pode só conhecer Python/Flask), manter a clareza que o `26` estabeleceu, mas **sem** repetir a explicação inteira de prototype chain (que era do 26) — aqui os conceitos JS relevantes são **funções como valores de primeira classe** e **`eval`**, não a herança por protótipo.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** (candidato "Insecure deserialization"), **NÃO** o stack ("...em Node"/"...em JavaScript"/"...com node-serialize"). O **slug** (`deserialization-node`) qualifica a variante/ecossistema — isso é OK (como `deserialization-pickle`). O motor (Node, `node-serialize`, `_$$ND_FUNC$$_`) aparece no **corpo**, não no H1. **Consequência esperada e correta:** o H1 (classe) é **idêntico ao do `20 deserialization-pickle`** — ambos são "Insecure deserialization"; o **slug** carrega o ecossistema, que é onde os dois se distinguem. Isso não é colisão — é a regra "título=classe" funcionando (dois átomos da mesma classe, ecossistemas diferentes).
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7, regra atual).** No `README.pt-BR.md`, `WALKTHROUGH.pt-BR.md` e `DIFF.pt-BR.md`, **todo** header de seção (`##`/`###`) é traduzido (termos técnicos seguem em inglês DENTRO do header). A **única** exceção é o **h1 do README**, idêntico ao EN. Sinal de tradução não aplicada: um header byte-idêntico ao par EN. (O `26` já segue isto — usar como molde: "Nota de stack", "API only — sem HTML, sem browser", "Como rodar", "O que ler a seguir", "Versão fixed".)
> - **A08 sem arqueologia** (Nota de planning 1).

---

## Identidade

- **ID:** `deserialization-node`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A08 — Software and Data Integrity Failures**. Pasta `atoms/A08-data-integrity-failures/` (**JÁ EXISTE — o 27 reaproveita**; o 20 a criou, o 26 já a reaproveitou). Confirmado contra o `ROADMAP.md` ("A08 Data Integrity Failures") e o `CLAUDE.md` §4. Em prosa (README/WALKTHROUGH/DIFF) usar o nome da classe — **"Insecure deserialization"** — e a categoria por extenso — **"A08 — Software and Data Integrity Failures"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A08-data-integrity-failures/deserialization-node/`
- **Número sequencial:** 27
- **Porta `vulnerable`:** `127.0.0.1:8027` (TRAVADO)
- **Porta `fixed`:** `127.0.0.1:8127` (TRAVADO)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o servidor Node no `0.0.0.0` dentro do container); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão do `26` (`server.listen(5000, process.env.HOST || "127.0.0.1")`). **§8 atenção dobrada (RCE): o binding local não é opcional aqui — o exploit executa comando no container.**
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM** serviço extra, listener, datastore, mock, ou rede especial. Molde do 01/20/26.
- **Tipo de átomo:** **API-only** (sem HTML, sem `templates/`, sem browser) — molde do `26 prototype-pollution`. Respostas `application/json`. A superfície é o header `Cookie`.
- **Stack:** **Node.js LTS (pinado por tag+digest, molde do 26) + módulo `http` puro.** **Dep de runtime:** `node-serialize` (versão pinada exata) **SÓ no `vulnerable`**; **`fixed` sem deps** (`JSON.parse` é stdlib). Ver "Biblioteca / stack" e "O container".
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos, e ZERO menção de "abrir/fechar" fase** (§5 foreshadow, Nota de planning 2).
- **Branch de trabalho:** `atom/deserialization-node`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato; confirmar por fetch na Fase 2):** **MESMA página-classe do `20 deserialization-pickle`** — a página **conceitual de Insecure deserialization** na PortSwigger Web Security Academy ("what is X?"), **NÃO** a listagem de labs. Candidato (já confirmado e publicado no 20): **`https://portswigger.net/web-security/deserialization`** (título da página: **"Insecure deserialization"**). **Confirmar a URL e a grafia do H1 por fetch na Fase 2** e **casar exatamente com o 20** (é a mesma classe). **NÃO inventar.** Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# deserialization-node — Insecure deserialization`** — `id` + nome canônico da **classe** em inglês (a forma que a PortSwigger usa na página). **SEM** "Node"/"JavaScript"/"node-serialize" no H1 (o slug já carrega o ecossistema). **CONFIRMAR a grafia exata na Fase 2** casando com o título da página do primer **e** com o H1 já publicado do `20` ("Insecure deserialization"). **Preservar o nome em inglês também no README PT.**

---

## Classe de vulnerabilidade

**Insecure deserialization — RCE via `node-serialize` (`serialize.unserialize`) em dado não-confiável.** Uma app web guarda as **preferências do usuário** (**user preferences**) num **cookie** serializado com a lib **`node-serialize`** e codificado em **base64**. A superfície é o header `Cookie` — e o usuário controla o próprio cookie. A app lê o cookie, base64-decoda, e faz **`serialize.unserialize`** na string. A lib `node-serialize` **serializa funções JavaScript** — e, no `unserialize`, quando reconhece uma função, faz **`eval`** dela. Um cookie forjado com uma função marcada para **auto-invocar** (uma **IIFE** — *immediately-invoked function expression*, função que se chama sozinha) faz o `eval` **rodar a função na hora do `unserialize`** — antes de a app usar o resultado pra qualquer coisa. Resultado: **execução de comando no servidor (RCE)** a partir de um cookie.

**Os conceitos, definidos na estreia (2º átomo Node — o leitor pode só saber Python):**

- **serialização / desserialização:** transformar um objeto em memória numa string/bytes (para guardar ou enviar) e reconstruir o objeto a partir dela. Padrão comuníssimo — settings, sessões, filas.
- **`node-serialize`:** uma lib (package **npm**, não stdlib) que serializa e desserializa objetos JavaScript. **Diferente do JSON**, ela sabe serializar **funções** — e, ao desserializar, precisa reconstruí-las.
- **o marcador `_$$ND_FUNC$$_`:** o jeito que a `node-serialize` codifica uma função é como uma **string** com o prefixo `_$$ND_FUNC$$_` seguido do corpo-fonte da função. No `unserialize`, ela detecta esse prefixo e reconstrói a função dando **`eval`** no corpo.
- **`eval`:** a função do JavaScript que **executa** uma string como código. É o executor: dar `eval` numa string controlada pelo atacante = rodar o código do atacante.
- **IIFE (immediately-invoked function expression):** uma função que se **auto-invoca** — escrever `function(){ ... }()` (com o `()` no final) faz a função rodar **imediatamente** ao ser avaliada. Se o corpo que a `node-serialize` vai dar `eval` termina em `()`, a função **executa no exato momento do `unserialize`**.
- **RCE (Remote Code Execution):** execução de comandos arbitrários no servidor.
- **base64:** codificação de binário/texto num alfabeto seguro pra transporte (aqui, pra caber num cookie).

### A lição-coração

> **"Desserializar dado não-confiável com um formato/lib que carrega COMPORTAMENTO (não só dados) executa código do atacante. A lib `node-serialize` serializa funções JavaScript e, ao desserializar, faz `eval` delas; uma função marcada para auto-invocar roda no momento do `unserialize` — RCE. O fix é usar um formato que só carrega DADOS (JSON via `JSON.parse`)."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** Guardar preferências num cookie serializado é uma feature **legítima e comum**. O erro não é aceitar um cookie; é o **formato/lib** com que ele é reconstruído. A `node-serialize` codifica uma função como uma **string** que começa com **`_$$ND_FUNC$$_`** e carrega o **corpo-fonte** da função. No `unserialize`, ao ver esse prefixo, a lib **reconstrói a função dando `eval` no corpo** (na prática, algo como `eval("(" + corpo + ")")`). Um atacante monta um cookie cujo valor é `_$$ND_FUNC$$_function(){ ... }()` — com o **`()` no final** (uma IIFE). Quando o `unserialize` dá `eval` nesse corpo, a função **se auto-invoca imediatamente** e o comando embutido roda **dentro** do `unserialize`, antes de a app tocar no resultado. **Não há bug de lógica na app**; é a `node-serialize` fazendo **o que ela faz** (reconstruir comportamento serializado). O único erro da app foi **dar dado não-confiável pro `unserialize`**.

Um detalhe que reforça o perigo: a função do atacante alcança **tudo que o processo Node alcança** — `require("child_process").execSync(...)` roda um comando de shell, sem a app **nunca** ter importado `child_process`. É o formato/lib, não a app, que dá esse poder.

### Sub-lição (cravar)

A diferença entre `vulnerable` e `fixed` **NÃO é "validar o input"** nem **"assinar o cookie"** — é o **FORMATO/lib**. `node-serialize` reconstrói **comportamento** (dá `eval` em funções na desserialização); `JSON.parse` carrega **só dados** (no pior caso, um objeto estranho; **nunca** produz uma função nem chama `eval`). **Bug pontual: o formato/lib de (de)serialização.** Esta é a sub-lição que o passo "o que a vuln NÃO é" (§5) tem que blindar: o aluno não pode sair achando que "o cookie foi adulterado, então é só assinar" nem que "é um bug de validação". O que separa vulnerable de fixed é **`serialize.unserialize` vs `JSON.parse`**.

### Por que A08 (Software and Data Integrity Failures)

A categoria A08 é sobre **confiar em dados/código cuja integridade não foi verificada** — assumir que um blob que cruzou uma fronteira de confiança é seguro pra ser processado/reconstruído. Desserializar dado não-confiável é **o exemplo canônico**: a app trata o cookie (dado que o usuário controla) como um objeto confiável e o **reconstrói** com uma lib que carrega comportamento. É uma **falha de integridade de dados** → **A08**. É a **mesma raiz** do `20 deserialization-pickle` (ver "Contraste com o 20"), num ecossistema diferente.

---

## Contraste com o `20 deserialization-pickle` (CRÍTICO — é a RAZÃO DE O ÁTOMO EXISTIR)

O 27 é o **paralelo Node** do `20 deserialization-pickle` (Python). **Ambos são A08, insecure deserialization, MESMO teto de impacto (RCE), MESMO tipo de fix (formato-com-comportamento → formato-só-dado).** O que **DIFERE** — e justifica dois átomos — é **ECOSSISTEMA e MECANISMO**. Cravar isto no WALKTHROUGH e no DIFF, em **tabela EN e PT**:

| Eixo | `deserialization-pickle` (20) | `deserialization-node` (27) |
|---|---|---|
| **Runtime / formato** | Python, `pickle` (stdlib) | Node.js, `node-serialize` (lib npm) |
| **Onde mora o executor** | `pickle.loads` (biblioteca padrão) | `serialize.unserialize` (dependência npm) |
| **Gatilho de código no dado** | objeto com `__reduce__` → chama a função no unpickle | função com `_$$ND_FUNC$$_` → `eval` no unserialize |
| **Fix** | trocar formato: `pickle` → JSON | trocar formato: `unserialize` → `JSON.parse` |
| **Impacto** | RCE | RCE |

**Enquadramento EXPLÍCITO (cravar):** *"a **MESMA classe** se materializa **diferente em cada ecossistema** — Python traz o desserializador perigoso na **stdlib** (`pickle`); em Node ele chega como **package npm** (`node-serialize`). Este átomo é o **rosto Node** da falha que o `deserialization-pickle` mostra em Python."* O átomo ganha existência no **ECOSSISTEMA + MECANISMO**, **NÃO** no impacto (que coincide).

**"Um átomo = uma vuln" é sobre a CAUSA (`CLAUDE.md` §2).** Apesar do **mesmo impacto** (RCE) e do **mesmo tipo de fix** (trocar o formato), a **causa concreta** — **qual desserializador** e **qual gatilho** — é o objeto de estudo, e é **diferente**: `pickle.loads` reconstruindo via `__reduce__` (Python/stdlib) vs `serialize.unserialize` dando `eval` num `_$$ND_FUNC$$_` (Node/npm). Citar o `20` (publicado) **à vontade** — o aluno abre os dois e vê **a mesma classe em dois ecossistemas**.

> **Nota sobre o contraste — este é TIGHT, diferente do 26↔20.** No `26 prototype-pollution`, o contraste com o 20 era **FROUXO** (o **impacto diferia**: RCE vs subversão de authz), então "um átomo = uma vuln" se sustentava facilmente pelo impacto. **Aqui o contraste é APERTADO:** o impacto **coincide** (RCE) **e** o tipo de fix coincide (trocar formato). Por isso a justificativa precisa apoiar **forte** no **ecossistema + mecanismo** (a causa concreta), e o WALKTHROUGH/DIFF têm que deixar **explícito** que não é "o 20 de novo em JavaScript" — é a mesma classe **materializada por um mecanismo próprio do ecossistema Node** (a lib npm, o marcador `_$$ND_FUNC$$_`, o `eval`). Este é o ponto mais delicado do átomo — não o subestimar.

---

## Uma vuln só — o foco é o `serialize.unserialize`; a prova é BENIGNA; SEM assinar o cookie; SEM 2ª superfície

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é **`serialize.unserialize` em dado não-confiável** (o cookie). Garantias e sutilezas (todas validar na Fase 2):

- **API-only → sem HTML, sem autoescape/rendering a considerar** (é JSON). Elimina de origem qualquer XSS acidental — nenhum valor é refletido em contexto HTML.
- **A prova de RCE é BENIGNA e contida (§8, atenção dobrada).** O payload roda um comando que **PROVA execução sem dano** (`touch /tmp/pwned`) — a prova é **"executou"**, não "causou dano". **NÃO** usar payload destrutivo (nada de `rm`, nada de rede/reverse shell, nada que saia do container). Ver "Prova de RCE".
- **`fixed` = trocar o FORMATO (JSON via `JSON.parse`), NÃO validar/assinar.** O fix é **estrutural** (formato que não executa). O fixed **não** valida o payload, **não** assina o cookie com HMAC, **não** faz blocklist de `_$$ND_FUNC$$_` — isso seria a **defesa-armadilha** da nota #3 do DIFF, não a correção. Ver "O fix" e DIFF nota #3.
- **Nenhum dos dois apps ASSINA o cookie.** O cookie `prefs` do vulnerable é `node-serialize`+base64 **cru** (sem assinatura); o do fixed é JSON+base64 **cru**. Isso é **de propósito**: a ausência de assinatura é o que faz o aluno experiente pensar "é só assinar" — e a nota #3 do DIFF **desarma** essa intuição (assinar fecha o sintoma, não a causa). Se o vulnerable assinasse, a nota #3 perderia o gancho.
- **Sem banco, sem 2ª superfície, sem 2ª dependência no fixed.** Nenhum datastore, nenhuma lib extra além de `node-serialize` **no vulnerable**; nenhum PII real. A **única** superfície é o cookie `prefs` chegando ao `serialize.unserialize`.
- **`serialize.serialize` do default NÃO é a vuln.** A app **serializa** as prefs default dela própria pra setar o cookie inicial — isso é **dado confiável saindo**, inofensivo. A vuln é **exclusivamente** `serialize.unserialize` em dado **não-confiável** (o cookie que volta do cliente). Cravar essa assimetria (serialize de dado próprio = ok; unserialize de dado do atacante = RCE).

---

## Flavor — COOKIE DE PREFERÊNCIAS SERIALIZADO (TRAVADO)

App **API-only** de **preferências do usuário** que guarda as prefs num **cookie** serializado com `node-serialize`+base64. **Superfície = o header `Cookie`** (didático: input não é só formulário — é qualquer coisa que o usuário controla, e o usuário controla o próprio cookie). Espelha **diretamente** o cookie-pickle do `20` — de propósito: o paralelo Python↔Node fica visível já no formato do átomo. **O ponto NÃO é a UI** (não há UI); é o cookie.

### Fluxo (endpoint único `GET /`)

- **`GET /` sem cookie `prefs`:** a app cria um objeto de preferências default (`{ theme: "light" }`), **serializa** (vulnerable: `serialize.serialize`+base64; fixed: `JSON.stringify`+base64), **seta** no cookie `prefs`, e responde o JSON das prefs (ex.: `{"theme":"light"}`).
- **`GET /` com cookie `prefs`:** a app base64-decoda o cookie e **desserializa** (vulnerable: `serialize.unserialize`; fixed: `JSON.parse`), e responde o JSON com o tema.
  - **VULNERABLE:** `serialize.unserialize` direto na string do cookie → um cookie malicioso (função `_$$ND_FUNC$$_` auto-invocável) **executa código** na desserialização.
  - **FIXED:** `JSON.parse` na string → **só dados**; um cookie malicioso no máximo dá erro de parse/objeto estranho, **nunca executa**.
- **O ataque:** o atacante **substitui** o cookie `prefs` por um payload `node-serialize` malicioso (uma função `_$$ND_FUNC$$_` auto-invocável → `require("child_process").execSync("touch /tmp/pwned")`) base64-encodado. No próximo `GET /`, o `serialize.unserialize` **executa** o comando.

**Cada versão LÊ o formato que ESCREVE** (vulnerable: `node-serialize`+base64 nos dois lados; fixed: JSON+base64 nos dois lados). O **contraste `serialize.unserialize` vs `JSON.parse` é o diff.**

**Sem form / sem 2º endpoint.** A app **só lê/seta** as prefs no `GET /`; o cookie é setado automaticamente no 1º request. **NÃO** adicionar endpoint pra "mudar tema" (seria 2ª superfície). O aluno interage tampereando o cookie no Burp — é o que espelha o mundo real (um cookie serializado que "você não deveria editar", editado assim mesmo).

> **NUANCE do node-serialize a cravar (difere do pickle do 20 — CONFIRMAR NA FASE 2).** Para **dados puros** (um objeto sem funções), a saída de `serialize.serialize({theme:"light"})` é **idêntica** à de `JSON.stringify` (`{"theme":"light"}`). Consequência dupla:
> 1. **O cookie baseline (benigno) é indistinguível entre vulnerable e fixed** — os dois decodam pro mesmo `{"theme":"light"}` e fazem **round-trip idêntico**. Isso é a prova de isolamento mais forte: só o payload `_$$ND_FUNC$$_` separa os dois lados (diferente do `20`, onde já o **baseline** revelava bytes de pickle `\x80\x04` na rede).
> 2. **O "tell" do formato NÃO está no baseline na rede** — decodar o cookie limpo mostra texto JSON-looking, não um marcador. O **tell é o código-fonte** (a app chama `serialize.unserialize`, não `JSON.parse`) e o **payload** (a string `_$$ND_FUNC$$_`, que é onde o poder da lib aparece). O WALKTHROUGH tem que situar isso: **o perigo da `node-serialize` fica dormente em dados; só acorda quando uma função é serializada.** É um ponto pedagógico honesto e forte — não escondê-lo.

---

## Prova de RCE — CONTIDA e INOFENSIVA (TRAVADO; §8 atenção dobrada) — **DECISÃO SINALIZADA**

### Comando-prova escolhido: **`touch /tmp/pwned`** (marcador de arquivo) — MESMO do `20`, de propósito

A função embutida no payload roda **`require("child_process").execSync("touch /tmp/pwned")`**. A prova de que o RCE ocorreu é o **efeito observável**: o arquivo **`/tmp/pwned` existe no container do vulnerable** e **NÃO existe no do fixed**.

- **Caminho do marcador:** `/tmp/pwned`.
- **Comando-prova exato:** `touch /tmp/pwned`.
- **Check da prova (via `docker compose exec`):** `docker compose exec vulnerable ls -la /tmp/pwned` → existe; no fixed → `No such file or directory`. **Idêntico ao `20`** (mesmo marcador, mesmo check) — de propósito, pra o paralelo Python↔Node ser palpável: **mesma prova, mesmo teto (RCE), gatilho diferente**.

**Por que espelhar o `20` (marcador + `docker compose exec ls`):** check **binário e limpo** (existe/não-existe), arquivo **vazio** (máximo benigno: nada lido, nada destruído, nada de rede), marcador "pwned" universalmente reconhecível em treino de segurança.

> **Sobre a "cor" `id`-nos-logs do 20 — NÃO porta limpo pro Node (SINALIZADO).** No `20`, `os.system("id")` imprimia `uid=0(root)...` no **stdout do container** porque `os.system` **herda** o stdout do processo. Em Node, **`child_process.execSync("id")` CAPTURA o stdout** (retorna um Buffer) — **não** imprime no log por padrão. Portar essa cor exigiria `execSync("id", { stdio: "inherit" })` ou um `console.log(execSync("id").toString())`, ou seja, **mais máquina no payload**. **DECISÃO:** a prova primária é o **marcador `/tmp/pwned`** (binário, limpo); a cor `id`-nos-logs **fica de fora por padrão** (não paga o custo de complicar o payload). A Fase 2 pode adicionar `{ stdio: "inherit" }` se quiser a cor — decisão do mantenedor, **não** bloqueante.

**Regras §8 (RCE — atenção dobrada), a cravar no WALKTHROUGH (espelhar o "What this really is" do `20`):**

- O comando é **benigno**: `touch` cria um arquivo **vazio** — não lê, não apaga, não escreve conteúdo, **não faz rede**, **não sai do container**.
- **PROIBIDO** payload destrutivo (`rm`, fork bomb), rede (reverse shell, `curl` pra fora), ou qualquer coisa que escape o container. O objetivo é **DEMONSTRAR execução**, com o **mínimo efeito**.
- O container é **isolado e descartável**; o RCE fica **contido** no container do átomo; portas bind **só** `127.0.0.1`. O WALKTHROUGH deixa **explícito** que é um lab isolado e o payload é uma **prova de conceito benigna** — exatamente o enquadramento do `20` ("harmless here because isolated container; on a real target this is RCE — keep payloads demonstrative, never `rm -rf`/reverse shell").

### Validação da prova (DECISÃO-ABERTA / CONFIRME NA FASE 2)

A memória `validating-atoms-via-docker-exec` cobre o check do marcador em `/tmp`: **host-port reachability from the sandbox varies** — tentar a porta host primeiro; se não alcançar, dirigir a app **de dentro do container**. Proposta para a Fase 2:

- **Disparar o ataque:** `curl -i http://127.0.0.1:8027/ -H 'Cookie: prefs=<base64-do-payload>'` (host). Fallback (se a porta host não for alcançável do sandbox): `docker compose exec vulnerable curl ...` ou `docker compose exec vulnerable node -e "require('http').get(...)"` de dentro do container.
- **Checar o marcador:** `docker compose exec vulnerable ls -la /tmp/pwned` (existe no vulnerable; ausente no fixed) — o `26` usou `docker exec` pra HTTP; aqui é o `ls` do marcador, ainda mais simples. **Propor o que funcionar na Fase 2 e capturar a saída real.** **Se não reproduzir, PARAR e avisar — NÃO inventar.**

---

## O código — o coração no `serialize.unserialize`

O arquivo do servidor (`app.js`, paralelo ao `app.py` dos átomos Python) **DIFERE** entre `vulnerable` e `fixed`; o delta é o **formato/lib de (de)serialização** (`node-serialize` ↔ JSON) — o import, o serialize do default, e o desserialize do cookie. O resto (o servidor `http`, o parser de cookie à mão, o `sendJson`, o handler, o `listen`) é **byte-idêntico**.

> **Sobre o candidato de código abaixo:** é **candidato** — a Fase 2 gera o real e **valida rodando** (riscos #1–#13). O nome do arquivo é **`app.js`** (molde do 26). O ponto travado é o **desenho**: `http` puro, cookie/serialize à mão, `serialize.unserialize` (vulnerable) vs `JSON.parse` (fixed) como o delta.

### `vulnerable/app.js` — `serialize.unserialize` direto no cookie (RCE) (candidato — Fase 2 gera o real)

```javascript
const http = require("http");
const serialize = require("node-serialize");

// --- In-memory default preferences (no database) ---
const DEFAULT_PREFS = { theme: "light" };

// Read one cookie by name from the request header (hand-written, no framework).
function getCookie(req, name) {
  const header = req.headers.cookie || "";
  for (const part of header.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    if (part.slice(0, eq).trim() === name) return part.slice(eq + 1).trim();
  }
  return undefined;
}

function sendJson(res, status, obj, extraHeaders) {
  res.writeHead(status, { "Content-Type": "application/json", ...(extraHeaders || {}) });
  res.end(JSON.stringify(obj));
}

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/") {
    const cookie = getCookie(req, "prefs");
    if (!cookie) {
      // First visit: serialize the default prefs (node-serialize + base64) and set the cookie.
      const raw = Buffer.from(serialize.serialize(DEFAULT_PREFS)).toString("base64");
      return sendJson(res, 200, DEFAULT_PREFS, { "Set-Cookie": `prefs=${raw}; Path=/` });
    }
    // VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to
    // serialize.unserialize. node-serialize encodes a JS function as a string tagged
    // "_$$ND_FUNC$$_" and eval()s that source on unserialize; a function body ending in
    // "()" self-invokes right there -- a crafted cookie -> code execution on the server.
    let prefs;
    try {
      prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString());
    } catch (e) {
      prefs = DEFAULT_PREFS;
    }
    const theme = prefs && typeof prefs.theme === "string" ? prefs.theme : DEFAULT_PREFS.theme;
    return sendJson(res, 200, { theme });
  }
  return sendJson(res, 404, { error: "not found" });
});

const HOST = process.env.HOST || "127.0.0.1";
server.listen(5000, HOST);
```

### `fixed/app.js` — JSON (só dados), ZERO deps (candidato — Fase 2 gera o real)

```javascript
const http = require("http");
// FIXED: no node-serialize dependency at all -- JSON is a data-only format (stdlib).

const DEFAULT_PREFS = { theme: "light" };

// ... getCookie / sendJson byte-identical to vulnerable ...

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/") {
    const cookie = getCookie(req, "prefs");
    if (!cookie) {
      // First visit: serialize the default prefs (JSON + base64) and set the cookie.
      const raw = Buffer.from(JSON.stringify(DEFAULT_PREFS)).toString("base64");
      return sendJson(res, 200, DEFAULT_PREFS, { "Set-Cookie": `prefs=${raw}; Path=/` });
    }
    // FIXED: the cookie is (de)serialized as JSON, which carries DATA ONLY, never behavior.
    // JSON.parse can at worst produce a weird object; it never builds a function, never
    // evals. Root fix: change the FORMAT (data, not behavior) -- not "sign the cookie"
    // (see DIFF for why signing is only a patch).
    let prefs;
    try {
      prefs = JSON.parse(Buffer.from(cookie, "base64").toString());
    } catch (e) {
      prefs = DEFAULT_PREFS;
    }
    const theme = prefs && typeof prefs.theme === "string" ? prefs.theme : DEFAULT_PREFS.theme;
    return sendJson(res, 200, { theme });
  }
  return sendJson(res, 404, { error: "not found" });
});

const HOST = process.env.HOST || "127.0.0.1";
server.listen(5000, HOST);
```

### Notas de implementação (validar/decidir na Fase 2)

- **RCE dispara DENTRO do `unserialize`; o `try/catch` + fallback tornam a resposta BENIGNA (molde do 20 — "RCE silencioso").** O payload IIFE roda o `execSync` **dentro** do `serialize.unserialize` e retorna (o `touch` já disparou). O objeto reconstruído provavelmente **não tem** `theme` string, então o fallback `prefs.theme || DEFAULT_PREFS.theme` faz a resposta ser `{"theme":"light"}` — **idêntica à baseline**. Ou seja: **a página parece normal enquanto `/tmp/pwned` foi criado** — deserialization RCE é **invisível in-band**; a única pista é o efeito colateral. Isto **espelha o refinamento que o `20` adotou** (o `try/except`→default, que deixa o RCE silencioso). **O `try/catch` + o fallback de `theme` são higiene IDÊNTICA nos dois lados** (ortogonal à vuln): evitam derrubar/quebrar a resposta com um cookie malformado, e mantêm o **diff isolado** ao `serialize.unserialize` ↔ `JSON.parse` (+ o `serialize`/`JSON.stringify` do default + o import). **Confirmar na Fase 2** que: (a) o `execSync` roda dentro do `unserialize`; (b) a resposta sai `{"theme":"light"}` (benigna); (c) o `try/catch`+fallback são byte-idênticos nos dois `app.js`.
- **Parser de cookie à mão (`getCookie`) — higiene idêntica nos dois lados.** `http` puro não tem parser de cookie; `req.headers.cookie` é uma string tipo `prefs=abc; other=def`. O `getCookie` é umas linhas, **ortogonal à vuln**, **byte-idêntico** nos dois (como o `readBody`/`sendJson` do 26). Confirmar na Fase 2 que ele extrai o `prefs` limpo.
- **`serialize.serialize` do default é inofensivo (dado próprio).** A app serializa o **seu** `DEFAULT_PREFS` (dado confiável) pra setar o cookie inicial. A vuln é **só** o `unserialize` do cookie que **volta** do cliente. Cravar a assimetria (serialize de dado próprio = ok; unserialize de dado do atacante = RCE) — o paralelo exato do `pickle.dumps` inofensivo vs `pickle.loads` perigoso do 20.
- **Cookie value é base64** (alfabeto `A-Za-z0-9+/=`): **todos** são `cookie-octet` válidos (RFC 6265) — `+`, `/`, `=` viajam limpos num cookie. O aluno **cola o base64 direto** como valor do cookie `prefs`. **Confirmar na Fase 2** que o round-trip do cookie é limpo; se algum char incomodar, `base64url` (que troca `+/` por `-_`) é o fallback — a app teria que decodar o mesmo alfabeto nos dois lados. *(O `20` confirmou que o base64 padrão viaja limpo no cookie `prefs`; esperar o mesmo aqui.)*
- **`GET /` responde JSON** (`Content-Type: application/json`), **API-only** — sem template, sem HTML (molde do 26). O `Set-Cookie` no 1º request seta o cookie serializado; o branch com-cookie desserializa e responde `{"theme": ...}`.

---

## O fix e o tipo de diff

**Fix:** trocar o **FORMATO/lib** de (de)serialização — **`node-serialize` → JSON**. Tipo de diff: **lógica-diferente** — muda o formato usado pra (de)serializar as prefs. O diff toca **três pontos no `app.js`**, todos o mesmo swap de formato:

1. o **import** (`const serialize = require("node-serialize");` → removido; o fixed não importa nada além de `http`),
2. o **serialize** do default (set do cookie: `serialize.serialize(DEFAULT_PREFS)` → `JSON.stringify(DEFAULT_PREFS)`),
3. o **deserialize** do cookie (leitura: `serialize.unserialize(...)` → `JSON.parse(...)`).

A linha **perigosa** é o `serialize.unserialize`; o `serialize` do default só mantém cada app auto-consistente. O resto do `app.js` (`http`, `getCookie`, `sendJson`, o handler, o `try/catch`+fallback, o `listen`) é **byte-idêntico**.

**ALÉM do `app.js`, o diff toca `package.json` e `Dockerfile` (DIVERGE do 20 e do 26 — cravar):** como o desserializador perigoso é uma **dependência npm** (não a stdlib), o `vulnerable/package.json` tem `node-serialize` em `dependencies` e o `vulnerable/Dockerfile` tem `RUN npm install`; o `fixed/package.json` **não tem `dependencies`** e o `fixed/Dockerfile` **não tem `npm install`** (zero deps, `JSON.parse` é stdlib). **Isso é proposital e faz parte da lição:** o fix não é "atualizar a `node-serialize`" (não há versão corrigida dela — ver "Biblioteca / stack") — é **parar de usá-la** e voltar a um formato só-dado. **Diferente do `20`** (pickle e json são **ambos** stdlib → `requirements.txt` idêntico) **e do `26`** (zero deps → `Dockerfile`/`package.json` idênticos): aqui a diferença de dependência **é** parte do diff, e o DIFF tem que explicá-la (nota #2).

Diff colável do `app.js` (candidato — a Fase 2 gera o real):

```diff
 const http = require("http");
-const serialize = require("node-serialize");
+// FIXED: no node-serialize dependency at all -- JSON is a data-only format (stdlib).
 ...
     if (!cookie) {
-      // First visit: serialize the default prefs (node-serialize + base64) and set the cookie.
-      const raw = Buffer.from(serialize.serialize(DEFAULT_PREFS)).toString("base64");
+      // First visit: serialize the default prefs (JSON + base64) and set the cookie.
+      const raw = Buffer.from(JSON.stringify(DEFAULT_PREFS)).toString("base64");
       return sendJson(res, 200, DEFAULT_PREFS, { "Set-Cookie": `prefs=${raw}; Path=/` });
     }
-    // VULNERABLE: ... serialize.unserialize ... "_$$ND_FUNC$$_" -> eval -> code on load ...
+    // FIXED: ... JSON carries DATA ONLY ... JSON.parse never evals, never builds a function ...
     let prefs;
     try {
-      prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString());
+      prefs = JSON.parse(Buffer.from(cookie, "base64").toString());
     } catch (e) {
       prefs = DEFAULT_PREFS;
     }
```

**O CONTRASTE é o diff (obrigatório):** `serialize.unserialize` (dá `eval` em comportamento) vs `JSON.parse` (só dados). **A mudança é o formato/lib de (de)serialização** (no `app.js`) **e** a dependência que ele arrasta (no `package.json`/`Dockerfile`).

### Notas obrigatórias no `DIFF.md`

1. **A causa é o FORMATO/lib que reconstrói COMPORTAMENTO, NÃO "validar/sanitizar o cookie".** Prova de isolamento: um cookie **benigno** (as prefs default serializadas) faz **round-trip idêntico** nos dois apps (a **feature é idêntica** — e, como `node-serialize` de dado puro == JSON, o cookie baseline é **literalmente o mesmo** nos dois lados; ver a NUANCE no Flavor); só um cookie com **função `_$$ND_FUNC$$_`** separa os dois — o vulnerable **executa** (`/tmp/pwned` aparece), o fixed **não** (`JSON.parse` no máximo dá erro/objeto estranho). **Cravar a assimetria fina:** o payload `node-serialize` é **`node-serialize` perfeitamente VÁLIDO** — não é input malformado; não há o que "sanitizar". O formato **em si** dá `eval` em comportamento embutido em dado bem-formado.
2. **Dados vs comportamento — e por que o fix é TROCAR A LIB, não atualizá-la/filtrá-la.** Explicar **"dados vs comportamento"**: `node-serialize` reconstrói **funções** (inclui **execução** via `eval` do corpo `_$$ND_FUNC$$_`); `JSON.parse` só produz **tipos primitivos** (objeto/array/string/número/bool/null) — **nunca** uma função, **nunca** um `eval`, **não há caminho de código**. A correção é **estrutural** (trocar pra um formato que não executa). **Cravar também a dimensão de dependência:** o desserializador perigoso aqui é uma **lib npm** (`node-serialize`), não a stdlib — o fix **remove a dependência** (o fixed tem zero deps), não "atualiza pra uma versão segura". *(Contraste honesto com o `20`, onde o `pickle` é stdlib e não dá pra "remover a dependência" — lá o fix é trocar a **função** de serialização; aqui é trocar a **lib** por stdlib. Mesma ideia — formato só-dado — expressa conforme o ecossistema.)*
3. **HMAC / ASSINAR O COOKIE NÃO É O FIX (nota-ADVERTÊNCIA curta, mas DIDÁTICA — mesma nota #3 do `20`).** Enquadrar assim, explicitamente:
   - **(a) Nomear a intuição.** O aluno experiente vai pensar: *"o cookie foi adulterado — é só assiná-lo com HMAC (hash autenticado) pra impedir a adulteração"*.
   - **(b) Reconhecer o que isso resolve — e o que NÃO.** Assinar torna o cookie **tamper-evidente**: um cookie forjado é **rejeitado**, então **eleva a barra** pra ESTE vetor. **Mas fecha o SINTOMA (a adulteração DAQUELE cookie), não a CAUSA.** A operação perigosa — `serialize.unserialize` em dado que cruzou a fronteira de confiança — **continua lá**. Se a chave de assinatura **vazar**, ou se dado não-confiável alcançar o `unserialize` por **qualquer outro caminho** (outro endpoint, uma fila, um cache, um arquivo), é **RCE de novo, na hora**.
   - **(c) Cravar SINTOMA vs CAUSA.** Assinar é **mitigação/defense-in-depth** que **guarda** um primitivo inseguro; a **correção de causa** é **remover** o primitivo inseguro — trocar o **FORMATO/lib** (JSON, que não executa). **CURTA** (a intuição + o porquê), enquadrada como *"isto NÃO é o fix, e aqui está o motivo"* — mesmo espírito da nota #3 do `20` e das notas "mencionável, não aplicada" dos irmãos.
4. **O impacto é RCE; contraste com o `20` (a tabela — mesma classe/impacto, ecossistema+mecanismo diferentes).** Incluir a **tabela** de "Contraste com o 20" (EN e PT). Cravar: **mesmo teto (RCE), mesmo tipo de fix (trocar formato), mas ecossistema (Python/stdlib vs Node/npm) e mecanismo (`__reduce__`/unpickle vs `_$$ND_FUNC$$_`/eval) diferentes** — a mesma classe materializada por um mecanismo próprio do ecossistema. "Um átomo = uma vuln" é sobre a **causa** concreta, não o impacto. **Sem foreshadow** (não nomear átomos/variantes não publicados).

---

## Biblioteca / stack

- **Runtime:** **Node.js LTS, imagem base PINADA por tag+digest** (`CLAUDE.md` §8.5; molde do `26`). Candidato: reusar a **mesma base do `26`** — `node:22-bookworm-slim@sha256:f32b81066cde10a75dbac96646099533316d94bac4150c55da1636e1f0ffdc46` (Node 22 "Jod" LTS). **Confirmar/re-pinar o digest vigente na Fase 2** (digests podem ser superados) — NÃO cravar sem verificar; se o digest do `26` ainda for o corrente, reusar mantém consistência.
- **Dependência de runtime — SÓ no `vulnerable`: `node-serialize` (versão PINADA exata).** É o **objeto de estudo** — o desserializador perigoso deste ecossistema. Candidato de versão: **`node-serialize@0.0.4`** (a versão associada ao RCE conhecido da lib — a lib está **sem manutenção** e **não tem versão corrigida**, o que é *em si* parte da lição: o fix não é "atualizar", é "parar de usar"). **CONFIRMAR RODANDO na Fase 2** (risco #6) que a versão pinada reproduz o `eval` do `_$$ND_FUNC$$_` — é lib de terceiro, **version-dependent**, **NÃO assumir**. Pinar **exato** (`"node-serialize": "0.0.4"`, sem `^`/`~`); considerar `package-lock.json` pra travar a árvore transitiva (**confirmar na Fase 2** que `node-serialize@0.0.4` **não** arrasta deps transitivas com CVE "de brinde", `CLAUDE.md` §8.5 — se arrastar, decidir o pin/lock).
- **`fixed`: ZERO dependências de runtime.** `http` e `JSON` são **stdlib** do Node. **Sem** `node-serialize`, **sem** framework, **sem** lib de nada — `JSON.parse`/`JSON.stringify` bastam.
- **`package.json` — DIFERE entre os lados:**

`vulnerable/package.json` (candidato):

```json
{
  "name": "deserialization-node",
  "version": "1.0.0",
  "private": true,
  "engines": { "node": ">=22 <23" },
  "dependencies": { "node-serialize": "0.0.4" }
}
```

`fixed/package.json` (candidato — sem `dependencies`):

```json
{
  "name": "deserialization-node",
  "version": "1.0.0",
  "private": true,
  "engines": { "node": ">=22 <23" }
}
```

  O `engines` documenta a versão-alvo (casar o range com a LTS da base, como o `26` fez com `>=22 <23`); a **pinagem efetiva** do runtime é a tag/digest da imagem base. **Confirmar o range na Fase 2.**
- **Comportamento version-dependent — VALIDAR (probe = validação §11, risco #6).** Diferente do `20` (onde `pickle.loads`/`__reduce__` é semântica **estável** da stdlib), aqui o gatilho é o comportamento de uma **lib de terceiro** (`node-serialize`) numa **versão específica**. **Confirmar RODANDO na Fase 2** (na versão pinada) que: (a) `serialize.serialize` de um objeto com função embute o marcador `_$$ND_FUNC$$_`; (b) `serialize.unserialize` de um payload com uma função `_$$ND_FUNC$$_` **auto-invocável** (IIFE, corpo terminando em `()`) **executa** o comando no `unserialize`. **Gate:** "não reproduziu → PARA e avisa, não inventa."

---

## WALKTHROUGH — abertura seca, trilha Burp-only (+ script/`curl` equivalente)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (preferências num cookie serializado) e a falha (o cookie é desserializado com `node-serialize`, que dá `eval` em funções embutidas). Trilha **ÚNICA: Burp** (montar o payload `node-serialize` — um script Node curto é o jeito real; `curl` pra mandar o cookie é equivalente). **NÃO** criar seção de browser. **DEFINIR os termos na 1ª ocorrência** (serialização/desserialização, `node-serialize`, `_$$ND_FUNC$$_`, `eval`, IIFE, RCE, base64, JSON).

**Abertura (candidato — plantar a lição, seco):**

> *A app guarda as suas preferências num cookie chamado `prefs`. Por baixo, ela **serializa** o objeto de preferências com a lib **`node-serialize`** — uma biblioteca (package npm) que transforma um objeto JavaScript em string e reconstrói o objeto a partir dela — e base64-encoda o resultado no cookie. A cada request, ela lê o `prefs`, base64-decoda, e faz `serialize.unserialize` na string pra reconstruir as prefs. O problema: **você controla o seu cookie**. E a `node-serialize` não sabe reconstruir só dados — ela sabe reconstruir **funções**, e faz isso dando **`eval`** no corpo-fonte da função. Um cookie forjado com uma função que se auto-invoca faz o `unserialize` **rodar o código que você escolher** — comando no servidor.*

Beats (molde do `20`/`26` publicado — abertura seca, seções numeradas `## 1..6`, Burp-only, API-only):

1. **Context.** App "user preferences": `GET /` seta o cookie `prefs` (`node-serialize`+base64) e responde `{"theme":"light"}`. Definir na estreia: **serialização/desserialização**, **`node-serialize`** (lib npm que (de)serializa objetos JS, incluindo funções), **`_$$ND_FUNC$$_`** (o marcador que a lib usa pra codificar uma função como string), **`eval`** (executa uma string como código), **IIFE** (função que se auto-invoca, `function(){...}()`), **RCE**, **base64**. Isto é **Insecure deserialization**, sob **A08 — Software and Data Integrity Failures**. Sem banco, sem segundo serviço: `vulnerable` em `127.0.0.1:8027`, `fixed` em `127.0.0.1:8127`. API-only, Node.js (`http` puro). Trilha: Burp/`curl` — a prova é o marcador no servidor.
2. **Spot the bug.** Mostrar `vulnerable/app.js` — a linha `prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString())`. O cookie **vem do cliente** (o aluno controla). Explicar o mecanismo: `node-serialize` reconstrói **funções** dando `eval` no corpo marcado com `_$$ND_FUNC$$_`; um corpo terminando em `()` (IIFE) roda **no `unserialize`**. Pergunta de auditoria: *"esses bytes vêm do meu cookie, que EU controlo — e o `unserialize` vai dar `eval` numa função que eu embutir?"* → **sim**. **Cravar a NUANCE (ver Flavor):** decodar o cookie baseline mostra `{"theme":"light"}` — **texto JSON-looking**, indistinguível de JSON; o "tell" do formato **não está no baseline na rede**, está no **código** (a app chama `serialize.unserialize`) e no **payload** (o `_$$ND_FUNC$$_`). O perigo da `node-serialize` fica **dormente em dados; só acorda quando uma função é serializada**. Foreshadow do fix: **trocar o formato** — usar um que só carregue dados.
3. **Exploitation via Burp Suite.**
   - **Baseline:** configurar o Proxy, visitar `http://127.0.0.1:8027/`. A app **seta o cookie `prefs`** e responde `{"theme":"light"}` (feature funciona). Base64-decodar o valor do cookie → mostra `{"theme":"light"}` (JSON-looking — a NUANCE acima). O aluno **vê a feature** e entende que o tell não está aqui.
   - **Montar o payload (script Node curto — jeito real):** um script que monta a string `node-serialize` com uma função `_$$ND_FUNC$$_` **auto-invocável** que roda `require("child_process").execSync("touch /tmp/pwned")`, e base64-encoda pro cookie. Ex. (candidato — a Fase 2 gera o real e captura a string):
     ```javascript
     const serialize = require("node-serialize");
     const payload = {
       // node-serialize will eval this function's source on unserialize; the trailing ()
       // makes it self-invoke (an IIFE), so the command runs during unserialize.
       rce: function () {
         require("child_process").execSync("touch /tmp/pwned");
       },
     };
     let s = serialize.serialize(payload);
     s = s.replace('}"', '}()"'); // append () to the serialized function body so it auto-invokes
     console.log(Buffer.from(s).toString("base64"));
     ```
     Explicar o que o script faz: `serialize.serialize` embute a função como `_$$ND_FUNC$$_function(){...}`; acrescentar `()` ao final do corpo transforma em IIFE (auto-invocação); base64 encoda pro cookie. **A montagem do `()` é version-dependent — a Fase 2 confirma a string exata rodando (risco #6).**
   - **Disparar (Repeater):** pegar o `GET /` no Repeater, **substituir o valor do cookie `prefs`** pelo base64 do script, enviar. O `serialize.unserialize` do servidor dá `eval` na função e ela **se auto-invoca** — `execSync("touch /tmp/pwned")` roda **durante** o `unserialize`.
   - **PROVAR a execução (efeito observável — a resposta NÃO é a prova):** `docker compose exec vulnerable ls -la /tmp/pwned` → o arquivo **existe**. **Deixar claro:** o RCE dispara **dentro** do `serialize.unserialize`, **antes** de a app fazer qualquer coisa com o resultado — a resposta sai `{"theme":"light"}` **normal** (RCE silencioso in-band, como o 20). A prova é o **marcador**, não o corpo da resposta.
   - **§8 (cravar):** container **isolado e descartável**; `touch` **benigno** (arquivo vazio, sem dano, sem rede, sem sair do container). Num alvo real isso é **RCE** — controle do host. **Manter os payloads demonstrativos**; **nunca** `rm -rf`, reverse shell, ou algo destrutivo — nem num container. *(Espelhar o "What this really is" do `20`.)*
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **NÃO é "cookie adulterável genérico" (assinar NÃO resolve).** Assinar o cookie **eleva a barra** pra este vetor (o cookie forjado é rejeitado), mas **não** toca a causa: `serialize.unserialize` em dado não-confiável continua sendo RCE — se a chave vazar ou o dado chegar por outro caminho, RCE de novo. A causa é o **FORMATO/lib**, não a autenticação do cookie. *(Sintoma vs causa — ver DIFF nota #3.)*
   - **NÃO é bug de validação.** O payload `node-serialize` é **`node-serialize` válido** — não há input malformado pra rejeitar. Não dá pra "sanitizar"; é o formato que dá `eval`. *(Ver DIFF nota #1.)*
   - **NÃO é "o `deserialization-pickle` (20) de novo em JavaScript".** É a **MESMA classe** (insecure deserialization, A08) e o **mesmo teto** (RCE), mas a **causa concreta é outra**: lá o desserializador é `pickle.loads` (stdlib do Python) e o gatilho é `__reduce__`; aqui o desserializador é `serialize.unserialize` (lib **npm**) e o gatilho é a função `_$$ND_FUNC$$_` dada `eval`. **A mesma classe se materializa com um mecanismo próprio de cada ecossistema** — este átomo é o **rosto Node** da falha. *(Ver "Contraste com o 20" — a tabela.)*
   - **O que É (prova):** `serialize.unserialize` reconstrói uma função que **VOCÊ** embutiu e dá `eval` nela — RCE — porque o **formato/lib carrega comportamento**. A **única** correção é usar um formato que só carrega **dados** (JSON via `JSON.parse`).
   - **Prova de isolamento (cravar):** um cookie **benigno** (preferência legítima serializada) faz round-trip **idêntico** nos dois lados (e, como `node-serialize` de dado puro == JSON, é **literalmente o mesmo** cookie); só o payload `_$$ND_FUNC$$_` separa vulnerable de fixed.
5. **Impact (honesto — sem overclaim).** **RCE (Remote Code Execution):** o atacante executa comandos arbitrários no servidor via um cookie malicioso desserializado. É o **impacto máximo** — **mesmo teto do `deserialization-pickle` (20)**, por **mecanismo distinto** (`node-serialize`/`eval` vs `pickle`/`__reduce__`). Sem overclaim, sem foreshadow.
6. **Why the fix works (porta 8127).** Repetir contra o `fixed/`:
   - O **MESMO cookie malicioso** → `JSON.parse` na string → **não executa** (dá erro de parse ou, no máximo, um objeto estranho); nada roda.
   - **Prova-chave:** `docker compose exec fixed ls -la /tmp/pwned` → **`No such file or directory`**. O `touch` **nunca** rodou no fixed. No vulnerable rodou; no fixed não — **mesmo cookie, execução vs nada**.
   - **A lição do diff:** o fix troca o **formato/lib** (`node-serialize`→JSON), que só carrega **dados**, e **remove a dependência** (o fixed tem zero deps). **Trocar-o-formato** (notas #1/#2); **assinar NÃO é o fix** (nota #3 — sintoma vs causa); **RCE por mecanismo diferente do 20** (nota #4). A feature (`{"theme":"light"}` no uso benigno) fica **intacta**.

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3). Payloads/responses/marcador são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**RCE (Remote Code Execution) via insecure deserialization.** O atacante substitui o cookie `prefs` por um payload `node-serialize` malicioso; no `serialize.unserialize`, o servidor dá `eval` na função embutida e ela se auto-invoca — comando arbitrário no host. É o **impacto máximo**. **Mesmo teto do `deserialization-pickle` (20)**, mas **mecanismo distinto** (lib npm que dá `eval` em função serializada vs stdlib que chama a função do `__reduce__`). **Sem overclaim** (não inflar pra "comprometimento total da infra" — é RCE no container do app, o que já é o topo). **Sem foreshadow** (não citar átomos/variantes/categorias não publicadas).

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A08 já povoada — contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`deserialization-pickle` (20)** — o contraste **central** (seção dedicada + tabela). **Mesma classe, mesmo impacto (RCE), mesmo tipo de fix; ecossistema (Python/stdlib vs Node/npm) e mecanismo (`__reduce__`/unpickle vs `_$$ND_FUNC$$_`/eval) diferentes.** É o **eixo do átomo** — o 27 é o rosto Node da falha que o 20 mostra em Python. Citar à vontade.
- **`prototype-pollution` (26)** — o outro A08, e o **precedente Node** do repo. Citável como **molde de stack** (Node `http` puro, API-only, base pinada por tag+digest) e, se útil, pra situar que **A08 tem faces de impacto diferentes** (o 26 é subversão de authz, o 20 e o 27 são RCE) — mas **sem forçar**; o contraste que **importa** aqui é o 20 (a mesma classe, o gêmeo).

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante não publicada** por número, nome **OU** descrição.
- **PROIBIDO anunciar posição/ordinal de fase, release, milestone, ou "abrir/fechar" fase.** O átomo se descreve **isolado** (Nota de planning 2). Onde precisar situar posição, apontar pro `ROADMAP.md`.
- **Que a superfície de deserialization exista em outros ecossistemas/formatos é, no máximo, descrição conceitual GENÉRICA de UMA LINHA** ("outros formatos/libs que carregam comportamento têm o mesmo problema") — **sem** nomear átomo/linguagem/variante não publicada. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 27 vai até **RCE via `serialize.unserialize`** do cookie (o finding), provado pelo marcador benigno. **Uma vuln, uma causa (o formato/lib), um fix (JSON).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **MESMA página-classe do `20 deserialization-pickle`** (é a mesma classe — insecure deserialization). Candidato (já confirmado e publicado no 20): **`https://portswigger.net/web-security/deserialization`** (título da página: **"Insecure deserialization"**, framing "What is insecure deserialization?"). **Confirmar por fetch na Fase 2** que a URL e a grafia do H1 seguem valendo, e **casar exatamente com o `20`**.
- **Secundário (opcional):** o marcador do problema neste ecossistema é a própria `node-serialize` sem manutenção — o CVE associado à lib pode ser citado como marcador concreto (candidato **CVE-2017-5941**, *confirmar por fetch na Fase 2 — NÃO inventar/afirmar sem verificar*), paralelo a como o `26` citou o **CWE-1321**. Opcional; o primário PortSwigger é o obrigatório. Se a grafia/numeração do CVE não for confirmável, **omitir** (não inventar). *(O `20` não liderou por CWE/CVE — manter isto leve, não é obrigatório.)*
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7 — "Insecure deserialization", exatamente como a PortSwigger nomear a página).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `20`/`26`).

---

## Renderização / "um átomo = uma vuln"

**API-only, respostas JSON via `JSON.stringify` + `Content-Type: application/json`** — **sem HTML, sem templates** (molde do `26`), logo **sem risco de XSS acidental** (nenhum valor refletido em contexto HTML). Garantir que a **ÚNICA** lição é o `serialize.unserialize` em dado não-confiável:

- **`GET /` é o único endpoint** (seta o cookie no 1º request; desserializa nos seguintes). **Sem** form, **sem** 2º endpoint, **sem** 2ª superfície.
- **O `fixed` troca SÓ o formato/lib** (`node-serialize`→JSON no `app.js`; e a dependência que ele arrasta, no `package.json`/`Dockerfile`). Todo o resto do `app.js` (`http`, `getCookie`, `sendJson`, o handler, o `try/catch`+fallback, o `listen`) é **byte-idêntico**.
- **SUTILEZA (crítica): o `fixed` troca o FORMATO/lib (JSON), NÃO valida/assina.** A correção é **estrutural** (formato que não executa) — **não** "validar o payload", **não** "assinar o cookie", **não** blocklist de `_$$ND_FUNC$$_` (isso seria a defesa-armadilha da nota #3, não a correção). **Nenhum dos apps assina o cookie** (senão a nota #3 perde o gancho).
- **Sem banco, sem 2ª superfície, sem assinatura/segredo.** A **única** superfície é o cookie `prefs` chegando ao `serialize.unserialize`.
- **Comando-prova benigno e contido** (§8). O RCE fica no container do átomo.

---

## O container

`Dockerfile` **DIFERE** entre `vulnerable` e `fixed` (diverge do `20`/`26`, onde eram idênticos) — porque o desserializador perigoso é uma **dependência npm** só do vulnerable. Adaptado pro Node (molde do `26`), **API-only → SEM `COPY templates`**. **§8:** bind **só** `127.0.0.1` — não-negociável aqui (o exploit é RCE).

**`vulnerable/Dockerfile`** (candidato — a Fase 2 fixa/re-pina a tag+digest LTS):

```dockerfile
# Pinned LTS base by tag AND digest (Node 22 "Jod" LTS) -- reuse the 26 base; confirm/re-pin in Phase 2.
FROM node:22-bookworm-slim@sha256:f32b81066cde10a75dbac96646099533316d94bac4150c55da1636e1f0ffdc46
WORKDIR /app
COPY package.json .
# node-serialize is the object of study (the dangerous deserializer of this ecosystem).
RUN npm install --omit=dev
COPY app.js .
# Override default host (127.0.0.1) so Docker's port forwarding can reach Node.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["node", "app.js"]
```

**`fixed/Dockerfile`** (candidato — SEM `npm install`, zero deps, molde exato do `26`):

```dockerfile
# Pinned LTS base by tag AND digest (Node 22 "Jod" LTS) -- reuse the 26 base; confirm/re-pin in Phase 2.
FROM node:22-bookworm-slim@sha256:f32b81066cde10a75dbac96646099533316d94bac4150c55da1636e1f0ffdc46
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

> **Nota (a divergência de Dockerfile É a lição, cravar no DIFF nota #2).** O `20` tinha `requirements.txt` idêntico (pickle/json ambos stdlib) e o `26` tinha `Dockerfile`/`package.json` idênticos (zero deps). Aqui **não**: o vulnerable **instala** `node-serialize`, o fixed **não instala nada**. Essa diferença **é** parte do diff e do ensino — o desserializador perigoso é uma **dependência**, e o fix a **remove**.

**`docker-compose.yml`** (candidato — molde do 01/20/26, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8027:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8127:5000"
```

**Sem `networks:`, sem serviço extra, sem `depends_on`, sem healthcheck, sem `COPY templates`.** Molde simples do 26 com as portas do 27. **§8:** bind **só** `127.0.0.1` (8027/8127).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A08 — Software and Data Integrity Failures** (`atoms/A08-data-integrity-failures/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `deserialization-node` em A08; `CLAUDE.md` §4 fixa a pasta (o 20 a criou, o 26 reaproveitou). Situar em A08 **sem arqueologia**. |
| Posição na fase | Ver `ROADMAP.md` | A posição/ordinal/release vivem só no ROADMAP. Spec e conteúdo nascem **limpos** (foreshadow §5); **ZERO** menção de "abrir/fechar" fase (Nota de planning 2). |
| **Stack** | **Node.js LTS (pinado tag+digest, molde 26) + `http` puro; `node-serialize` (pinado) SÓ no vulnerable; fixed ZERO deps (`JSON.parse`)** | 2º átomo Node. `CLAUDE.md` §3.2 autoriza (deserialization em Node é caso nominal). A lib npm É o objeto de estudo. |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Molde do 01/20/26. Sem serviço extra, sem datastore. |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | Cookie como superfície; molde do 26. JSON via `JSON.stringify` → sem XSS acidental. |
| Trilha | **Burp-only (+ script Node/curl), SEM browser** | §3.3 atual. Server-side; a prova é o marcador, não o browser (como 20/26). |
| Lição-coração | **Formato/lib que carrega comportamento (`node-serialize` dá `eval` em função `_$$ND_FUNC$$_`) executa código no unserialize; fix = formato só-dado (JSON).** | O bug é o **FORMATO/lib**, não "validar/assinar o cookie". |
| Contraste central | **`deserialization-pickle` (20)** — MESMA classe/impacto (RCE)/tipo de fix; ecossistema+mecanismo diferentes | É o eixo. Contraste TIGHT (impacto coincide) → justificar forte no ecossistema+mecanismo. "Um átomo = uma vuln" = causa, não impacto. |
| Flavor — **TRAVADO** | **Cookie de preferências serializado** (`GET /`, cookie `prefs` `node-serialize`+base64) | Input não-confiável não é só form — é o cookie. Espelha o cookie-pickle do 20. API-only; o ponto é o cookie. |
| Nuance node-serialize | **Dado puro serializa == JSON → cookie baseline idêntico nos dois lados e JSON-looking na rede** | Isolamento mais forte que o 20 (lá o baseline já revelava pickle); o "tell" é o código+payload, não o baseline. Confirmar na Fase 2. |
| Comando-prova — **SINALIZADO** | **`touch /tmp/pwned`** (marcador; MESMO do 20) | Prova binária e limpa (existe/não), arquivo vazio (máximo benigno, §8). `id`-nos-logs do 20 NÃO porta (execSync captura stdout) — fora por padrão. |
| Código vulnerable | **`serialize.unserialize(Buffer.from(cookie,"base64").toString())`** | Dado não-confiável → `eval` da função embutida → RCE. |
| Código fixed | **`JSON.parse(Buffer.from(cookie,"base64").toString())`** | JSON só carrega dados; sem `eval`, sem função, sem caminho de execução. |
| Resposta pós-unserialize malicioso | **`{"theme":"light"}` benigno** (RCE silencioso, via `try/catch`+fallback idêntico nos dois) | A prova é o **marcador**, não a resposta. Espelha o refinamento "RCE invisível in-band" do 20. |
| Fix (único eixo) | **Trocar o FORMATO/lib (`node-serialize`→JSON)** | Correção **estrutural**, não validar/assinar (defesa-armadilha da nota #3). |
| Diff | **Lógica-diferente** — import + serialize + unserialize (no `app.js`) **+ `package.json`/`Dockerfile`** (a dep que o vulnerable arrasta) | A linha perigosa é `serialize.unserialize`; a divergência de dependência É parte do diff (nota #2). |
| Dockerfile/package.json | **DIFEREM** (vulnerable: `node-serialize` + `npm install`; fixed: zero deps, sem `npm install`) | Diverge do 20 (stdlib idêntico) e do 26 (zero deps idêntico). O desserializador perigoso é uma dependência; o fix a remove. |
| HMAC / assinar cookie | **NÃO aplicar** (nota-advertência #3, sintoma vs causa) | Eleva a barra, mas não remove o primitivo inseguro. Mesma nota #3 do 20. |
| Assinatura/segredo | **Nenhum** (cookie cru, sem assinatura) | O cookie cru é o que dá o gancho da nota #3. |
| Renderização | **API-only, JSON; sem HTML/templates/browser** | Sem autoescape a considerar; sem XSS acidental. |
| Bibliotecas | **`node-serialize@0.0.4` (candidato, pinado exato) no vulnerable; fixed sem deps** | Version-dependent — CONFIRMAR RODANDO na Fase 2 que reproduz o `_$$ND_FUNC$$_` eval. Lib sem versão corrigida (parte da lição: fix = parar de usar, não atualizar). |
| Impacto | **RCE.** Mesmo teto do 20, mecanismo distinto. | Honesto; sem overclaim; sem foreshadow. |
| Theory primer | **PortSwigger Insecure deserialization** (`/web-security/deserialization`, MESMA página do 20; confirmar por fetch e casar com o 20) | Página conceitual "what is X?". CVE-2017-5941 opcional (confirmar/omitir). Não inventar. Nome em inglês no PT. |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. |
| Título (H1) | **`deserialization-node — Insecure deserialization`** (classe, sem stack; **idêntico ao H1 do 20** — mesma classe, slug distingue) | `CLAUDE.md` §5. Slug carrega "node"; H1 não. Grafia confirmável na Fase 2. |
| Headers PT | **Traduzidos em TODA doc PT** (exceto h1 do README) | `CLAUDE.md` §7 (regra atual). Molde do 26. |
| Foreshadow | **ZERO pra frente + ZERO posição/ordinal/release + ZERO "abrir/fechar" fase** | `CLAUDE.md` §5 / Nota de planning 2. Publicados (01, 20, 26) e ROADMAP OK. Spec nasce limpa. |
| Portas | **8027 / 8127** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. §8 atenção dobrada (RCE). |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora, só listar)

Itens 1–7 são os centrais; 8–13 são higiene/isolamento. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /`** (sem cookie `prefs`) → a app **seta** o cookie `prefs` (`node-serialize`+base64 no vulnerable; JSON+base64 no fixed) e responde `{"theme":"light"}`. Sobe sem erro (`./atom up deserialization-node`).
2. **Feature funciona:** `GET /` (com o cookie default) → lê as prefs, responde o tema (nos dois apps, 8027 e 8127).
3. **O ATAQUE (central — VALIDAR RODANDO):** montar o payload `node-serialize` (função `_$$ND_FUNC$$_` auto-invocável → `require("child_process").execSync("touch /tmp/pwned")`), base64, pôr no cookie `prefs`, `GET /` no **vulnerable** (8027) → o comando **EXECUTA** (`/tmp/pwned` criado dentro do container). **Capturar** o payload, o request e a prova reais. **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** responses/prova.
4. **FIXED (8127 — VALIDAR RODANDO):** o **MESMO** cookie malicioso → `JSON.parse` **NÃO executa** (erro de parse ou objeto inócuo); **`/tmp/pwned` NÃO é criado**. **Capturar a diferença** (`ls` no vulnerable vs no fixed).
5. **Prova de isolamento:** o cookie **benigno** (prefs default) → `{"theme":"light"}` (feature idêntica nos dois). Confirmar a NUANCE: `node-serialize` de dado puro == JSON → o cookie baseline é **idêntico** entre vulnerable e fixed e **JSON-looking** na rede. Confirmar que o payload `node-serialize` é **válido** (não malformado) — a lição da nota #1.
6. **A versão pinada de `node-serialize` reproduz o `_$$ND_FUNC$$_` eval (PROBE — version-dependent, VALIDAR RODANDO):** confirmar na versão pinada (`node-serialize@0.0.4` candidato) que (a) `serialize.serialize` de objeto com função embute `_$$ND_FUNC$$_`; (b) `serialize.unserialize` de uma função `_$$ND_FUNC$$_` **auto-invocável** (IIFE) **executa** no `unserialize`; (c) a string exata do payload (o `()` acrescentado). **É lib de terceiro — NÃO assumir.** **Gate: "não reproduziu → PARA e avisa, não inventa."** Se `0.0.4` não reproduzir, achar/registrar a versão que reproduz e re-pinar (documentar).
7. **Uma vuln só:** API-only (sem HTML → sem XSS); **sem banco**; **sem 2ª superfície**; **sem assinatura/segredo**; fixed usa **JSON** (não valida/assina). Confirmar que o WALKTHROUGH **não** empilha outra vuln.
8. **§8 (RCE — atenção dobrada):** o comando **NÃO** é destrutivo, **NÃO** faz rede, **NÃO** sai do container. Container **isolado**. Bind **só** `127.0.0.1` (8027/8127). Confirmar o enquadramento "lab isolado + prova benigna" no WALKTHROUGH.
9. **Validação do marcador por `docker compose exec`:** `docker compose exec vulnerable ls -la /tmp/pwned` (existe) vs `docker compose exec fixed ls -la /tmp/pwned` (ausente). Disparo do ataque via `curl` do host; **fallback** (memória `validating-atoms-via-docker-exec`): dirigir de dentro do container se a porta host não for alcançável do sandbox. Propor o que funcionar; capturar a saída real.
10. **Cookie round-trip base64:** o base64 (com `+`/`/`/`=`) viaja limpo no cookie `prefs`; se não, cair pra `base64url` (nos dois lados). Confirmar que o aluno cola o base64 direto no Repeater.
11. **`serialize`↔`unserialize` no vulnerable / `JSON.stringify`↔`JSON.parse` no fixed:** confirmar que cada app **lê o formato que escreve**, e que a resposta pós-ataque sai `{"theme":"light"}` (RCE silencioso via `try/catch`+fallback idêntico). Confirmar que o `serialize.serialize` do default (dado próprio) é inofensivo.
12. **Primer PortSwigger (deserialization)** confirmado **por fetch** (`/web-security/deserialization`), grafia do H1 casando com o `20`. **CVE-2017-5941** (opcional) confirmado por fetch **ou omitido** — não inventar. Se em dúvida, perguntar ao mantenedor.
13. **Diff = só o desserializador (+ a dep que ele arrasta):** confirmar por `diff` que a **única** mudança no `app.js` é o formato/lib (`require` do `node-serialize`, `serialize.serialize`, `serialize.unserialize` ↔ `JSON.stringify`/`JSON.parse`), e que o resto do `app.js` é **byte-idêntico**; e que o `package.json`/`Dockerfile` **diferem** exatamente na dependência `node-serialize` + `RUN npm install` (vulnerable) vs zero (fixed). **Sem `templates/`, sem HTML** (API-only). Re-pinar/confirmar o digest da base Node e o range do `engines`. Confirmar que `node-serialize@0.0.4` **não** arrasta deps transitivas com CVE "de brinde" (`CLAUDE.md` §8.5); se arrastar, decidir o pin/lock.

**Bloqueante remanescente:** nenhum de decisão de design. **Pendências de Fase 2 (não bloqueantes agora):** reproduzir o ataque no vulnerable e o bloqueio no fixed (itens 3–4); validar a versão de `node-serialize` que reproduz o `_$$ND_FUNC$$_` eval e a string exata do payload (item 6); confirmar/re-pinar o digest da base Node; confirmar a URL do primer por fetch e a grafia do H1 casando com o 20, e decidir o CVE opcional (item 12); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **uso-direto-do-antipadrão** — sem "Saída B", sem ferramenta-que-resiste; o dev passa dado não-confiável direto pro `serialize.unserialize`. Cada beat deve poder ser lido com o **`deserialization-pickle` (20)** aberto ao lado (o **gêmeo** — o eixo do átomo é o contraste com ele) e o **`prototype-pollution` (26)** ao lado (o molde de **stack Node** + API-only + voz atual + §7 PT). **Abrir e fechar** na lição-coração: *o formato/lib carrega comportamento; `serialize.unserialize` de dado não-confiável dá `eval` numa função e executa; o fix é trocar pra um formato que só carrega dados (JSON).*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`sqli-union-basic` (01) INTEIRO** (molde canônico single-container), **`deserialization-pickle` (20) INTEIRO** (o gêmeo — app.py vulnerable+fixed, WALKTHROUGH, DIFF, README EN+PT; o contraste é o eixo), **`prototype-pollution` (26) INTEIRO** (o precedente Node — app.js, package.json, Dockerfile, compose, WALKTHROUGH, DIFF, README; molde de stack e §7 PT). **Seguir o `CLAUDE.md` ATUAL** — Burp-only, abertura seca, título=classe, A08 sem arqueologia, headers PT traduzidos.
- **STACK Node — travada:** `http` puro (sem Express/framework), cookie/serialize à mão, base Node LTS **pinada por tag+digest** (reusar/confirmar a do 26). **Diferente do 26:** o vulnerable tem **UMA** dep (`node-serialize`, pinada exata) e **`RUN npm install`** no Dockerfile; o fixed tem **zero** deps e **nenhum** `npm install`. A lib npm **É** o objeto de estudo — não escondê-la, nomeá-la.
- **CONTRASTE COM O 20 é o eixo (cravar — o ponto mais delicado):** tabela (EN e PT) no WALKTHROUGH e no DIFF; enquadramento explícito "a mesma classe se materializa por um mecanismo próprio de cada ecossistema; este é o rosto Node". O contraste é **TIGHT** (impacto E tipo de fix coincidem) — apoiar **forte** no ecossistema+mecanismo (a causa concreta), deixando claro que **não** é "o 20 de novo em JS". "Um átomo = uma vuln" é **causa**, não impacto (`CLAUDE.md` §2). Citar o 20 (publicado) à vontade.
- **A prova é o marcador `/tmp/pwned` (riscos #3/#4/#9).** Capturar a cadeia real: vulnerable → `unserialize` dá `eval` → `touch` executa → arquivo existe; fixed → `JSON.parse` não executa → arquivo não existe. **Se não bater rodando, PARAR e avisar — NÃO inventar** prova/responses. A prova **não** é o corpo da resposta (sai `{"theme":"light"}` benigno); é o **efeito colateral** (marcador via `docker compose exec`).
- **§8 ATENÇÃO DOBRADA (RCE):** comando **benigno e contido** (`touch`); bind **só** `127.0.0.1`; container **isolado**; **nada** destrutivo/rede/fora-do-container. Enquadrar explicitamente no WALKTHROUGH (espelhar o 20).
- **A sutileza que NÃO pode enfraquecer a lição:** o **fixed troca o FORMATO/lib (JSON)**, **NÃO** "valida o payload" nem "assina o cookie" (filtro/assinatura = defesa-armadilha da nota #3; a correção é **estrutural**). **Nenhum dos apps assina o cookie** (senão a nota #3 perde o gancho).
- **Uma vuln só:** foco no `serialize.unserialize` de dado não-confiável. API-only (sem XSS). Sem banco, sem 2ª superfície, sem segredo. `serialize.serialize` do próprio default é inofensivo — a vuln é só o `unserialize` do cookie.
- **NUANCE do node-serialize (cravar no WALKTHROUGH):** dado puro serializa == JSON → o cookie baseline é idêntico entre os lados e JSON-looking na rede; o "tell" do formato está no **código** (a chamada `serialize.unserialize`) e no **payload** (`_$$ND_FUNC$$_`), não no baseline. O perigo fica **dormente em dados; só acorda quando uma função é serializada**. Não esconder — é honesto e forte.
- **Version-dependent (risco #6):** o gatilho é o comportamento de uma **lib de terceiro** numa **versão específica** (diferente do `pickle` stdlib estável do 20). **VALIDAR RODANDO** que a versão pinada reproduz o `_$$ND_FUNC$$_` eval e capturar a string exata do payload. **Não assumir; não inventar.**
- **Abertura seca + trilha Burp-only:** WALKTHROUGH entra direto na mecânica; **sem** encenação; **sem** seção browser. Script Node curto pra montar o payload (mundo real); `curl` equivalente pra mandar o cookie. Rotular os beats: **baseline (feature; o tell não está aqui)** → **spot the bug (`serialize.unserialize`; a nuance)** → **montar payload (`_$$ND_FUNC$$_` IIFE)** → **disparar + provar (marcador)** → **o que a vuln NÃO é (não é cookie-adulterável / não é validação / não é "o 20 de novo em JS")** → **impacto (RCE)** → **fixed (mesmo cookie, sem execução; JSON)**.
- **Impacto honesto:** **RCE.** Mesmo teto do 20, mecanismo distinto. Sem overclaim, sem foreshadow.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é o **FORMATO/lib** (`node-serialize` dá `eval` em comportamento), não "cookie adulterável" (assinar não resolve — sintoma vs causa), não bug de validação (o payload é `node-serialize` válido), não "o `deserialization-pickle` (20) de novo em JavaScript" (mesma classe/impacto, mecanismo/ecossistema diferentes). Prova de isolamento: cookie benigno round-trips idêntico; só o `_$$ND_FUNC$$_` separa.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** serialização/desserialização, `node-serialize`, `_$$ND_FUNC$$_`, `eval`, IIFE, RCE, base64, JSON.
- **A08 sem arqueologia:** situar em **A08 — Software and Data Integrity Failures**, explicar **por que** (integridade de dados: reconstruir dado não-confiável com um formato/lib que carrega comportamento), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `deserialization-node — Insecure deserialization`. "Node"/"node-serialize"/"JavaScript" no corpo, não no H1. É **esperado e correto** que o H1 (classe) coincida com o do `20` — o slug distingue o ecossistema.
- **Headers PT traduzidos (`CLAUDE.md` §7, regra atual):** em `README.pt-BR.md`, `WALKTHROUGH.pt-BR.md`, `DIFF.pt-BR.md`, **todo** header de seção traduzido (termos técnicos em inglês DENTRO do header); a única exceção é o h1 do README. Molde do 26. Checar: nenhum header PT byte-idêntico ao par EN (fora o h1).
- **Política de referência cross-átomo:** OK citar **20** (contraste central — o gêmeo), **26** (molde de stack Node + outro A08), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar **qualquer átomo não-publicado/categoria futura** por número, nome **ou** descrição — inclusive posição/ordinal de fase, release, milestone, "abrir/fechar fase". **A própria spec nasce limpa** (é commitada no repo público): onde precisar situar posição, apontar pro `ROADMAP.md`; nas frases que proíbem foreshadow, manter a proibição **genérica**.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`deserialization-node — Insecure deserialization`, grafia exata confirmável na Fase 2, casando com o 20). Termos técnicos (`node-serialize`, `_$$ND_FUNC$$_`, `eval`, deserialization, RCE, base64, JSON, payload, cookie) **não** se traduzem no PT — mas ganham **definição na estreia** (§5).
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (Insecure deserialization, MESMA página do 20), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** e casar a grafia com o 20 — não inventar. CVE-2017-5941 opcional (confirmar/omitir).
- **"What to read next" Burp-only:** o README referencia o WALKTHROUGH **só como Burp Suite (API-only; sem trilha browser)** — sem `and browser (secondary)` (molde do 26).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 27: `deserialization-node` — Insecure deserialization: an attacker-controlled cookie deserialized with Node's `node-serialize` library carries a `_$$ND_FUNC$$_`-tagged function that the library `eval`s on unserialize; a self-invoking function body runs during unserialize, giving remote code execution — the Node face of the flaw `deserialization-pickle` shows in Python; the fix changes the format to JSON (`JSON.parse`, data only) and drops the dependency (A08 Software and Data Integrity Failures). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release; **NÃO** mencionar posição/próximos átomos.
- **ROADMAP.md:** marcar o átomo 27 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–13; reproduzir baseline → payload (`_$$ND_FUNC$$_` IIFE) → marcador no vulnerable → marcador ausente no fixed, via Burp/`curl` + `docker compose exec`.
- **Portas:** `127.0.0.1:8027` (vulnerable), `127.0.0.1:8127` (fixed). Bind **só** `127.0.0.1`. Single-container. §8 atenção dobrada (RCE).
- Se houver dúvida sobre a versão de `node-serialize` que reproduz o CVE, a string exata do payload IIFE, o digest da base Node, o range do `engines`, o round-trip do cookie, a URL/grafia do primer, o CVE opcional, ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Propostas (não aplicar; só registrar pro mantenedor decidir)

> Regra do repo: o Claude Code **propõe**, o mantenedor **decide** (`CLAUDE.md` §10.2 e "Memória de projeto"). Nada abaixo é aplicado nesta spec.

### (a) Convenção Node no `CLAUDE.md` (se a stack se provar reusável)

Este é o **segundo** átomo Node do repo (o `26` foi o primeiro — fato de stack). Com dois átomos Node, o padrão de stack começa a se firmar e **poderia** ser codificado no `CLAUDE.md` (§3.2/§4 ou uma subseção de stack) — o mantenedor decide se/quando. Convenção candidata (a mesma que o `26` propôs, agora com um 2º ponto de dados, **mais** o refinamento das deps):

- Runtime Node.js LTS, imagem base **pinada por tag+digest**.
- **`http` puro sem framework** por padrão (Express só se a vuln for idiomática do Express).
- **Parsing/lógica-alvo à mão** quando a vuln vive nesse código (manter na fonte).
- **`package.json` só pra `engines` + zero deps de runtime POR PADRÃO** — **exceto** quando a **lib é o objeto de estudo** (como o `node-serialize` aqui): aí a dep entra **pinada exata**, **só no `vulnerable`**, e o **`fixed` volta a zero deps**; `Dockerfile`/`package.json` divergem entre os lados nesse caso.
- Nome do arquivo do servidor: **`app.js`**.

**NÃO alterar o `CLAUDE.md` agora** — isto é proposta. O mantenedor decide se/quando codificar.

### (b) Memória candidata (opcional — decisão do mantenedor)

Não gravei nada (o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido** (útil pra futuros átomos A08/deserialization/Node):

- **`deserialization-node-format-not-validation`** — *"O átomo `deserialization-node` (27) é o rosto Node do `deserialization-pickle` (20): RCE via `serialize.unserialize(base64_decode(cookie))` num cookie `prefs`, usando a lib npm `node-serialize`. Gatilho = uma função com o marcador `_$$ND_FUNC$$_` que a lib dá `eval` no unserialize; um corpo terminando em `()` (IIFE) auto-invoca → `require('child_process').execSync('touch /tmp/pwned')`. Fix = trocar o formato pra JSON (`JSON.parse`, só dados) E remover a dependência (fixed = zero deps). MESMA classe/impacto (RCE)/tipo de fix que o 20; DIFERE em ecossistema (Node/npm vs Python/stdlib) e mecanismo (`_$$ND_FUNC$$_`/eval vs `__reduce__`/unpickle) — 'um átomo=uma vuln' é a CAUSA concreta, não o impacto. NÃO é validar/assinar (nota-armadilha #3, igual ao 20). Prova = marcador `/tmp/pwned` via `docker compose exec` (resposta sai `{theme:light}` benigna; RCE silencioso). node-serialize é version-dependent (candidato 0.0.4, sem versão corrigida) — validar rodando. Dockerfile/package.json DIVERGEM (vulnerable instala node-serialize; fixed zero deps) — a dep É parte do diff."* — tipo `project`.

**Ressalva (lean):** esse fato vai ficar **registrado nesta spec commitada e no DIFF/README** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer antecipado. **Sua decisão.**
