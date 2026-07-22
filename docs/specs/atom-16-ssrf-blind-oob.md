# Spec — Átomo 16: `ssrf-blind-oob`

> Documento de especificação para o Claude Code implementar o décimo-sexto átomo do projeto `atomicvulns` (Fase 4 — "Server-side Avançado", milestone `v0.4.0`). Este átomo **ABRE a Fase 4** (é o 1º dos cinco átomos da fase — `16 ssrf-blind-oob`, `17 ssrf-cloud-metadata`, `18 xxe-basic`, `19 ssti-jinja`, `20 deserialization-pickle`; confirmado no `ROADMAP.md`) e **NÃO muda de eixo**: é a **continuação do arco de SSRF (A10)** que começou no átomo 04 (`ssrf-basic`). É o **SEGUNDO átomo A10 do repo** e o **átomo-irmão do 04**. É também o **primeiro átomo infra-pesado desde o 04**: **volta à topologia MULTI-CONTAINER** que só o `ssrf-basic` usou até agora (a trilogia JWT — 05/13/14 — e o `session-fixation` da Fase 3 eram single-app).
>
> **A lição em uma linha:** você pode ter SSRF completo mesmo quando a aplicação **NÃO devolve nada útil** na resposta. A vulnerabilidade é o servidor fazer uma requisição para um destino controlado pelo atacante — a **VISIBILIDADE da resposta é um eixo SEPARADO (ortogonal)**. *Blind* (cego) não significa **ausente**; significa que você tem que **DETECTAR out-of-band**. O fix é a mesma família do `ssrf-basic`: **VALIDAR o destino (allowlist deny-by-default)** antes de buscar.
>
> Leia junto com `CLAUDE.md` (Seções 3.3 — este átomo **TEM HTML e trilha dupla**, NÃO é API-only; §5 — passo "o que a vuln NÃO é" obrigatório e política de referência cross-átomo; §6 — didático > realista; §8 — segurança, **bind `127.0.0.1` e ISOLAMENTO entre átomos**, crítico aqui por causa do multi-container; §10.5 — leitura de referência; e a seção "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), `ROADMAP.md`, e — como **referência viva e primária** — o átomo **`ssrf-basic` (04) INTEIRO** (README, WALKTHROUGH, DIFF, os três diretórios `vulnerable/`/`fixed/`/`internal/`, e principalmente o `docker-compose.yml`). O 04 é o **átomo-irmão** e a referência de "como SSRF se ensina aqui"; o `sqli-union-basic` (01) é o molde canônico de HTML/Jinja2 mínimo; o `atom-15-session-fixation.md` é o **formato de spec mais recente** (este documento o segue).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, `oob-listener/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Nota de planning 1 — posição na Fase 4: 16 ABRE a Fase 4 (confirmado; sem discrepância)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A Fase 4 ("Server-side Avançado", `v0.4.0`) tem **cinco** átomos — **`16 ssrf-blind-oob`**, `17 ssrf-cloud-metadata`, `18 xxe-basic`, `19 ssti-jinja`, `20 deserialization-pickle` — e o **16 é o primeiro**, marcado `[ ]` (os anteriores, 01–15, já `[x]` em `main`). **Logo o 16 é o phase-opener da Fase 4.**
>
> **Segundo átomo A10 do repo.** O `ROADMAP.md` lista `ssrf-blind-oob` sob "A10 SSRF", explicitamente como *"Variante do 04: SSRF sem resposta direta, usando canal out-of-band"*. A pasta `atoms/A10-ssrf/` **já existe** (criada pelo `ssrf-basic` na Fase 1); o 16 mora em `atoms/A10-ssrf/ssrf-blind-oob/`, **ao lado** de `atoms/A10-ssrf/ssrf-basic/`. O átomo **17** (`ssrf-cloud-metadata`) é o próximo A10 e vem logo depois — **não-publicado**, portanto tratado apenas **conceitualmente** neste átomo (ver "Contraste com o arco / escopo" e a **política de foreshadow**), nunca por número/conteúdo.

## Nota de planning 2 — versionamento/release fica FORA desta spec

> O 16 **abre** a Fase 4 (não fecha nada), então **não dispara** uma release por si só (a release `v0.4.0` fecha a fase, lá no átomo 20). De todo modo, versionamento/CHANGELOG/tag/anúncio é **trabalho de release do mantenedor**, não de átomo — não entra nesta spec nem no conteúdo do átomo (`CLAUDE.md` §10.4). O átomo se descreve como "átomo 16, o que abre a Fase 4", **sem** anunciar release nem foreshadowar os átomos seguintes da fase (ver "Política de foreshadow").

---

## Identidade

- **ID:** `ssrf-blind-oob`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A10 — Server-Side Request Forgery (SSRF)**. Pasta `atoms/A10-ssrf/` (**já existe**, criada pelo `ssrf-basic`). Confirmado contra o `ROADMAP.md` ("A10 SSRF"). **Segundo átomo desta categoria no repo** (o primeiro é o `ssrf-basic`, 04). Em prosa (README/DIFF) usar o nome completo — **"Server-Side Request Forgery (SSRF)"** — como o 04 já faz.
- **Pasta:** `atoms/A10-ssrf/ssrf-blind-oob/`
- **Número sequencial:** 16
- **Porta vulnerable:** `127.0.0.1:8016`
- **Porta fixed:** `127.0.0.1:8116`
- **Listener OOB (`oob-listener`):** **INTERNO-ONLY, SEM porta no host** (só alcançável pela rede do compose, observado por `docker compose logs`). **Só `8016` e `8116` ficam expostas.** (Ver "Wiring do listener" e "O container".)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos 01–15 e, na parte multi-container, **idêntico ao 04**.
- **Fase / milestone:** Fase 4, `v0.4.0`. **Primeiro átomo da Fase 4 — phase-opener** (ver Nota de planning 1). Versionamento/release **fora desta spec** (Nota de planning 2).
- **Branch de trabalho:** `atom/ssrf-blind-oob`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **específica de Blind SSRF** na PortSwigger Web Security Academy — candidato `https://portswigger.net/web-security/ssrf/blind`. **Preferir a página blind-específica** (o 04 usou a página geral `https://portswigger.net/web-security/ssrf`; o 16 usa a de *blind*). **Confirmar por fetch na Fase 2, não inventar** — se a página blind-específica não existir com framing "what is X?", perguntar ao mantenedor (fallback: página geral de SSRF). Ver seção "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7):** candidato `# ssrf-blind-oob — Blind SSRF (out-of-band)` — segue o padrão dos irmãos (`id` + nome canônico da vuln em inglês; ex. `ssrf-basic — Server-Side Request Forgery (basic)`). Texto exato / qualificador confirmável na Fase 2; **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**Blind SSRF (out-of-band).** Uma app web com uma feature que **dispara uma requisição HTTP para uma URL fornecida pelo usuário** como **efeito colateral**, e cujo **RESULTADO NÃO é mostrado** de volta. O servidor bate na URL e devolve um sucesso/erro **genérico**, sem corpo útil, sem status do recurso buscado, sem eco. É o *flavor* natural do *blind*: a requisição server-side acontece (SSRF completo), mas o atacante **não tem canal de leitura** in-band.

Como o servidor **não valida o destino**, a mesma feature que "avisa" uma URL legítima também pode ser apontada para **qualquer destino que a rede do servidor alcance**. Só que — diferente do `ssrf-basic` — o atacante **não vê** o que o servidor buscou. Então como provar que o SSRF aconteceu? **Apontando o servidor para um listener que o próprio atacante controla e observando o callback chegar out-of-band.** A prova não é "li um segredo"; é **"fiz o servidor sair pra fora e capturei o hit"**.

### A lição-coração

> **"Você pode ter SSRF completo mesmo quando a aplicação NÃO devolve nada útil na resposta. A vulnerabilidade é o servidor fazer uma requisição para um destino controlado pelo atacante — a VISIBILIDADE da resposta é um eixo SEPARADO. *Blind* não significa ausente; significa que você tem que DETECTAR out-of-band."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** No `ssrf-basic` (04), o corpo da resposta **refletia o conteúdo buscado** — você **VIA** o resultado (lia o serviço interno, o "prêmio"). No blind, a app busca a sua URL mas devolve **um sucesso genérico, SEM corpo útil**. Você não lê nada. A requisição **aconteceu** (é SSRF de verdade), mas o único jeito de saber é observar o callback num sink que você controla.

**Sub-lição (cravar): a diferença entre TER e NÃO TER a vuln NÃO é o corpo refletir conteúdo — é o servidor fazer a requisição para um destino que você escolhe.** A visibilidade da resposta é **ORTOGONAL**. Muito iniciante acha *"sem output = sem SSRF"*; este átomo isola exatamente esse engano. A requisição **acontecer** (a vuln de verdade) é **INDEPENDENTE** de a resposta **refleti-la** (que é só o quão fácil é confirmar). A habilidade toda que se ensina é: **PROVAR que a requisição aconteceu quando você não pode ver o resultado dela.**

### DISTINÇÃO CENTRAL — BLIND vs IN-BAND (a lição que separa quem entende)

Blind SSRF **NÃO é** um SSRF "mais fraco" — é a **MESMA capacidade de requisição server-side**, só que **sem o eco conveniente**. Cravar no WALKTHROUGH (passo "o que a vuln É e o que a detecção exige") e no DIFF:

| | **IN-BAND / BASIC (átomo 04)** | **BLIND (átomo 16 — ESTE)** |
|---|---|---|
| O servidor busca a URL do atacante? | **sim** (é o SSRF) | **sim** (é o mesmo SSRF) |
| O servidor devolve o conteúdo buscado? | **sim** — o body reflete o recurso | **não** — resposta genérica, sem eco |
| Canal de detecção | **ler o body** da resposta (in-band) | **interação out-of-band** (o callback) |
| Você tem... | requisição **E** leitura | requisição, **NENHUM** canal de leitura |
| Prova do exploit | "li o dashboard interno" | "fiz o servidor sair pra fora e capturei o hit" |

**A frase-regra:** *a REQUISIÇÃO acontecer (a vuln de verdade) é INDEPENDENTE de a RESPOSTA refleti-la (que é só o quão fácil é confirmar).* Confundir os dois leva o aluno a "sem output = sem SSRF" — o engano exato que este átomo desmonta.

**ENQUADRAMENTO CONCRETO NO LAB — tripwire vs alvo (cravar):**

- No `ssrf-basic`, o serviço interno (`internal`) era **O ALVO** — o prêmio alcançado e **lido** (dashboard com API keys fake).
- No 16, o listener (`oob-listener`) é uma **TRIPWIRE, não um alvo**. Um endpoint burro que só registra *"fui contatado"*. O aluno **NÃO lê prêmio nenhum** — ele apenas **CONFIRMA que a requisição escapou**. (Reachear serviço interno com segredo / metadata de cloud é escopo do **17**, ver "Contraste com o arco / escopo".)

### Contraste com o arco (eixo A10 — continuidade, NÃO mudança)

O contraste **principal e explícito** é com o **04** (`ssrf-basic`, **JÁ PUBLICADO** — citável à vontade, `CLAUDE.md` §5). É a **espinha** do átomo:

- **04 (in-band):** `GET /fetch?url=<url>` → o servidor busca **E devolve o body** (template `preview.html` mostra conteúdo + status). Detecção fácil: **leia a resposta**. Estrutura: **tem** `preview.html`; **surfacea** o erro do fetch.
- **16 (blind):** `POST /ping` com `url` → o servidor busca **e não devolve nada** sobre o resultado (resposta genérica `Test ping sent.`). Detecção: **out-of-band** (log do `oob-listener`). Estrutura: **NÃO tem** template de resultado (não há o que ecoar); **engole** o erro (surfaceá-lo seria um oráculo in-band).

A **mesma primitiva** de requisição server-side; a diferença é o **canal de leitura** (presente no 04, ausente no 16). Essa continuidade — mesma classe, mesmo fix (validar o destino), eco removido — é o que faz do 16 o átomo-irmão do 04.

### Por que A10 (SSRF)

Blind SSRF é **SSRF** — a superfície é idêntica à do 04 (o servidor faz uma requisição outbound para um destino que o atacante controla). O que muda é **só a visibilidade da resposta**, que é ortogonal à classe. Coerente com o eixo server-side da Fase 4 e com o arco A10 aberto pelo 04.

---

## Uma vuln só — a resposta é CEGA de propósito, o listener é tripwire, o fix é allowlist CORRETA, sem XSS

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o servidor **fazer o fetch outbound SEM validar o destino**. Garantias (todas validar na Fase 2):

- **A CEGUEIRA É DE PROPÓSITO (moldura travada).** A resposta genérica do vulnerable revela **ZERO** sobre o resultado do fetch — **sem body buscado, sem status distinguível do recurso, sem erro surfaceado, sem oráculo de timing óbvio**. Essa cegueira é o **traço definidor** do átomo, NÃO um acidente. Espelha o *"a senha é trivial de propósito"* do 15: aqui, *"a resposta é cega de propósito"*. **Se vazasse o conteúdo/status buscado, seria SSRF in-band (átomo 04), não blind.** O DIFF **deve** notar isso.
- **O listener NÃO guarda segredo — é TRIPWIRE, não alvo.** Retorna `"ok"` trivial, loga o hit, e é **interno-only** (sem porta no host). Não é um segundo alvo; reachear serviço interno com prêmio / metadata de cloud é escopo do **17**.
- **O fix é uma allowlist CORRETA (deny-by-default), NÃO um blocklist bypassável.** Este é o ponto mais fácil de estragar (espelha o *"o id tem que ser FORTE; a vuln é a NÃO-REGENERAÇÃO"* do 15): a validação decide sobre o **host parseado** (`urlparse(...).hostname`), **não** por match de substring do raw URL, e é **positiva** (deny-by-default). Um filtro bypassável transformaria o átomo silenciosamente numa lição de *"SSRF filter bypass"* (tópico diferente e mais avançado). A vuln DESTE átomo é a **AUSÊNCIA de validação de destino**; o fix, quando presente, é **robusto**. Cravar.
- **Autoescape do Jinja LIGADO (default), sem XSS.** O `index.html` é essencialmente estático (form). Se a Fase 2 optar por refletir a URL submetida no HTML, **DEVE** passar por `{{ }}` (escapado) — **sem** `|safe`, **sem** `Markup`, **sem** `render_template_string`. **Sem XSS acidental.**
- **O fetch TEM timeout** (`timeout=5`, como o 04) → **sem** unbounded-consumption/DoS como segunda falha.
- **Sem banco, sem segunda superfície:** nenhum `SESSIONS`/`CREDENTIALS`/SQLite; nenhum segredo/PII real; a única peça extra é o `oob-listener` (tripwire).

---

## A decisão estrutural — LISTENER OOB EMBARCADO (a "Saída B" do 16): por quê (TRAVADA)

**O ponto que faz o átomo existir** — e é da **mesma família honesta** da "Saída B" do 14 (PyJWT mitiga → verify hand-rolled) e do 15 (`flask.session` resiste → sessão manual), mas aqui é uma **ruga de INFRA, não de biblioteca**:

A detecção de blind SSRF no mundo real depende de um **serviço de interação out-of-band** — Burp Collaborator, `interactsh`, um catcher de DNS/HTTP na internet. Mas o `atomicvulns` é **isolado por design** (bind `127.0.0.1`, isolamento entre átomos, `CLAUDE.md` §8) e **não pode ter um exploit que dependa de alcançar `burpcollaborator.net`** (o aluno pode estar offline, sem Collaborator configurado, atrás de egress filtering, ou simplesmente sem conta Burp Pro). **Não dá pra publicar um lab cujo exploit exige um serviço externo de terceiros.**

**A saída TRAVADA — o átomo EMBARCA o próprio sink OOB:** um container **`oob-listener`** interno que faz o papel do *"Collaborator do atacante"*, **inteiramente dentro da rede do compose**. O WALKTHROUGH/README **DEVE** explicar **POR QUE** o listener é embarcado (o lab é isolado e auto-contido; engagements reais usam Collaborator/`interactsh`; aqui a gente entrega um **análogo self-hosted** do sink OOB). Deixar isso **EXPLÍCITO**.

*(Paralelo direto com 14/15: lá a ferramenta/mecanismo padrão da linguagem mitigava o bug ingênuo, então o átomo modelava o anti-padrão real. Aqui o **ambiente** padrão de detecção (um Collaborator externo) é indisponível num lab isolado, então o átomo **embarca** o análogo. Em todos: "a coisa que o mundo real usaria não está disponível/não serve no lab isolado — então modelamos o equivalente honesto localmente". Registrar esse paralelo no DIFF.)*

---

## Decisões de infra JÁ TRAVADAS — implemente conforme, NÃO reabra

1. **PROTOCOLO DO LISTENER: HTTP-only.** A infra serve ao **core**, não compete com ele. DNS pingback só teria valor com egress filtering (que o lab isolado não tem) e ensinaria **resolver de DNS no Docker**, não SSRF. A nuance de DNS — *"em engagement real, o pingback de DNS costuma ser o sinal mais confiável por causa de filtro de egress (o servidor pode não conseguir abrir uma conexão HTTP de saída, mas quase sempre consegue resolver um nome)"* — vai **DOCUMENTADA em prosa** no WALKTHROUGH, **sem construir a infra**.
2. **CANAL DE OBSERVAÇÃO: `docker compose logs`, igual ao 04.** O listener **loga cada hit recebido**; o aluno confirma o SSRF pelos logs do compose. **SEM status page, SEM porta HTTP no host** pro listener.
   - **Atribuição causal: um PATH FIXO reconhecível** no payload — **`/proof-ssrf-16`** — dá o *"botei ISSO, ISSO apareceu no log"*. **SEM nonce dinâmico** — o lab isolado não tem concorrência de payloads nem ruído que justifiquem fidelidade-Collaborator. Path fixo entrega a causalidade limpa com zero maquinaria a mais.
3. **LISTENER INTERNO-ONLY:** alcançável **APENAS** pelo container `vulnerable` (e, pela rede, pelo `fixed`) via rede do compose, observado por log. **NÃO expõe porta no host** (`CLAUDE.md` §8: só 8016/8116 bindados em `127.0.0.1`).

---

## WIRING DO LISTENER — **DECISÃO SINALIZADA** (o único item não pré-travado)

Depois de ler o `docker-compose.yml`, o `internal/` e os Dockerfiles do `ssrf-basic`, defino a seguir o wiring, **conformando à convenção que o 04 já cravou** (não invento topologia nova).

> **WIRING — o que escolhi e por quê:**
> - **(a) Nome do serviço/container:** **`oob-listener`** (descritivo; **evita "collaborator"**, termo carimbado da Burp que confundiria). Vira o hostname DNS `oob-listener` na rede do compose — o payload do ataque é `http://oob-listener/proof-ssrf-16` (hyphen é label DNS válido; funciona como host de URL).
> - **(b) Porta interna:** **80** — espelha o `internal/` do 04 (`app.run(..., port=80)`, `EXPOSE 80`). Assim o payload não carrega porta explícita (`http://oob-listener/...`, porta 80 implícita), mais limpo no walkthrough.
> - **(c) Convenção de diretório:** **`oob-listener/`** — espelha o `internal/` do 04 (nome-do-diretório == nome-do-serviço). Contém `app.py`, `Dockerfile`, `requirements.txt` (sem `templates/`, como o `internal/`).
> - **(d) Wiring da rede (espelhando EXATAMENTE o 04):** `vulnerable` → rede `lab-vulnerable`; `fixed` → rede `lab-fixed`; **`oob-listener` → AMBAS** (`lab-vulnerable` **e** `lab-fixed`). Só `vulnerable`/`fixed` publicam porta no host.
>
> **POR QUE `oob-listener` nas DUAS redes (a parte não-óbvia):** é a mesma isolação do 04 (vulnerable e fixed **não se enxergam**; ambos enxergam o listener) **E** é a construção **HONESTA** do contraste do fixed. Se o listener estivesse só em `lab-vulnerable`, a **ausência de hit** no fixed seria confundida com **inalcançabilidade de rede** — um fix no-op (ou um container quebrado) **também** não geraria hit, e a prova ficaria confundida. Pondo o listener **também** em `lab-fixed`, o fixed **CONSEGUE** alcançar o listener pela rede, mas o **allowlist barra a requisição ANTES de ela sair** — então a ausência de hit é atribuível ao **CÓDIGO**, não à topologia. É **literalmente a nota do 04**: *"the internal container is still reachable from the fixed container at the network layer — the fix is in the application code, not in the network plumbing."*

Esboço do `docker-compose.yml` (candidato — a Fase 2 gera o real; **NÃO gerar agora**):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8016:5000"
    networks:
      - lab-vulnerable
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8116:5000"
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

---

## Feature e endpoints — app web "webhook tester" (TEM HTML, molde web clássico)

Uma app web mínima com uma feature de **"enviar um ping de teste para uma webhook URL"**: o servidor bate na URL fornecida como **efeito colateral** e **não conta nada** sobre o resultado. É o *flavor* natural do blind (deliberadamente **sem eco**, diferente do 04, que mostrava o conteúdo). Molde de render **confirmado contra o `ssrf-basic`**: o 04 é HTML (tem `templates/index.html`), então o 16 **espelha** (tem HTML, trilha dupla).

- **`GET /`** — serve o form (campo de URL). Banner de aviso, dica de Burp. Renderiza `templates/index.html`.
- **`POST /ping`** — o servidor faz uma requisição HTTP GET para a URL fornecida (`request.form["url"]`).
  - **VULNERABLE:** busca **SEM validar** o destino e devolve resposta **genérica** (`"Test ping sent."`), **NADA** sobre o conteúdo/status do que buscou.
  - **FIXED:** valida o destino (allowlist deny-by-default) e **só busca destinos vetados**; destino não permitido → **não faz a requisição** e devolve a **MESMA** resposta genérica (ver "A resposta é idêntica nos dois — decisão SINALIZADA").

> **DECISÃO SINALIZADA — nome do endpoint e flavor.** O prompt travou o método (**POST**, via `request.form["url"]`) e ofereceu latitude no nome (*"POST /fetch (ou o nome que casar com o flavor)"*) e no flavor (*"webhook ping / avise esta URL / verificar callback"*). **Escolhi:** flavor **"webhook tester"**, rota **`POST /ping`**. Justificativa: (1) *webhook test/ping* é a superfície de blind SSRF **mais reconhecível e real** do mundo (registra uma URL, "envia um teste", o servidor bate nela e te dá um ack genérico sem eco); (2) `/ping` **nomeia a ação** e lê naturalmente com um resultado cego (você "pinga", não espera um corpo de volta) — enquanto `/fetch` (do 04) sugere **retrieval**, o que brigaria com a cegueira; (3) descartei o flavor "health/uptime checker" **de propósito**, porque ele naturalmente vazaria um oráculo up/down (semi-blind), quebrando a cegueira total que o átomo exige. **Fallback aceitável:** `POST /fetch` (paralelo direto ao 04) — o prompt usou `/fetch` como placeholder no checklist; a Fase 2/mantenedor pode manter `/fetch` se preferir o paralelismo literal com o 04. Uso `/ping` no resto desta spec.

> **DECISÃO SINALIZADA — POST (não GET, diferente do 04).** O 04 usa `GET /fetch?url=` (é um "preview", idempotente, leitura). O 16 usa **`POST /ping`** com `request.form["url"]` (travado pelo prompt): um **"ping" é um efeito colateral mutável** (dispara uma ação), o que casa com o flavor E produz naturalmente uma resposta cega, sem eco. Divergência do 04 **deliberada e pedagógica**; registrar no DIFF/WALKTHROUGH.

**Não há serviço interno com segredo neste átomo.** O `oob-listener` é a **única** peça extra e é **tripwire, não alvo**.

---

## A resposta CEGA é de propósito — e é IDÊNTICA nos dois (moldura travada + decisão SINALIZADA)

A resposta genérica do vulnerable revela **ZERO** sobre o resultado do fetch. Essa **cegueira** é o traço definidor do átomo, NÃO um acidente. O DIFF **DEVE** notar: *"a resposta é genérica de propósito; se vazasse o conteúdo/status buscado, seria SSRF in-band (átomo 04), não blind"*.

> **DECISÃO SINALIZADA (reconciliação de uma tensão interna do prompt) — a resposta é IDÊNTICA nas DUAS versões; o fix NÃO usa `400 Destination not allowed`.**
>
> O **esboço de código** do fix no prompt mostrava `return "Destination not allowed.", 400` no caminho rejeitado. Mas a **PROVA-CHAVE**, a **ENCENAÇÃO** (passo 3) e os **riscos #3/#4** do prompt dizem, repetida e explicitamente, que a resposta do fixed pro payload do listener é *"mesma resposta genérica, MAS o log do listener NÃO mostra hit"* e que *"o corpo da resposta é idêntico/genérico nos dois — provando que em blind SSRF você TEM que olhar out-of-band, e que o fix é sobre o destino, não sobre a resposta"*.
>
> Essas duas coisas **se contradizem**: se o fixed devolvesse um `400 Destination not allowed` distinto, (a) o corpo **não** seria idêntico ao do vulnerable, e (b) o aluno **conseguiria** confirmar o bloqueio **pela resposta** — exatamente o oposto da lição "você TEM que olhar out-of-band". O prompt me mandou *"ajustar a forma exata pra mínimo e correto"*, então **reconcilio a favor da intenção explícita e repetida (a PROVA-CHAVE)**: o fixed **gateia o fetch** e devolve a **MESMA** `"Test ping sent."` — o `400` do esboço fica **superado**. Assim:
> - a resposta é **byte-idêntica** nas duas versões → o aluno **não consegue** distinguir vulnerable de fixed pela resposta → ele **precisa** olhar o canal OOB (o log). Isso ensina visceralmente "blind ⇒ out-of-band";
> - o diff é **puramente o gate de destino** (a linha `return "Test ping sent."` fica **intocada**) → prova que a resposta **nunca foi o controle**;
> - materializa a **nota obrigatória #1 do DIFF** ("deixar a resposta genérica não é defesa"): a resposta já é genérica **nos dois**, e um deles é vulnerável — logo a cegueira **não é** um controle de segurança.
>
> **Nota:** essa é a **única divergência estrutural** do fixed em relação ao 04 (o 04 dá `abort(403)`, visível, porque é in-band; o 16 gateia o fetch e mantém a resposta cega **nos dois**, porque é blind). Divergência **pedagogicamente motivada**; cravar no DIFF. *(Se o mantenedor preferir o `400` explícito, a Fase 2 troca — mas perde a prova "resposta idêntica ⇒ olhe OOB". Recomendo fortemente a resposta idêntica.)*

---

## O código — o coração no fetch

Imports (vulnerable):

```python
import os
import requests
from flask import Flask, request, render_template
```

### `vulnerable/app.py` — busca sem validar, resposta cega (candidato — Fase 2 gera o real)

```python
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ping", methods=["POST"])
def ping():
    url = request.form.get("url", "")
    # VULNERABLE: fire a server-side request to an attacker-controlled URL and reveal NOTHING
    # about the result. The outbound request happens (this is full SSRF); the response below is
    # generic -- no fetched body, no fetched status, no error surfaced. The SSRF is real; it is
    # merely BLIND, so it must be detected out-of-band (see the oob-listener service).
    try:
        requests.get(url, timeout=5)  # server-side request to the attacker-chosen destination
    except Exception:
        pass  # swallow everything: surfacing the error would leak an in-band oracle
    return "Test ping sent."  # generic -- says nothing about whether/what was fetched


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — valida o destino antes, resposta IDÊNTICA (candidato — Fase 2 gera o real)

```python
import os
from urllib.parse import urlparse
import requests
from flask import Flask, request, render_template

app = Flask(__name__)

# Deny-by-default allowlist of vetted webhook destinations. Matched on the PARSED host, not a
# substring of the raw URL. In this air-gapped lab the host is not actually reachable (no real
# egress), so legitimate use is CONCEPTUAL; what the lab demonstrates is that a NON-vetted
# destination (the oob-listener, or any internal/external host) is never fetched.
ALLOWED_HOSTS = {"hooks.example.com"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ping", methods=["POST"])
def ping():
    url = request.form.get("url", "")
    # FIXED: gate the outbound request on the allowlist BEFORE fetching. A destination that is
    # not explicitly permitted is never requested, so the server cannot be coerced into reaching
    # arbitrary destinations -- internal OR external. Same SSRF defense family as ssrf-basic (04).
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:
        try:
            requests.get(url, timeout=5)
        except Exception:
            pass
    return "Test ping sent."  # IDENTICAL generic response to the vulnerable version: the fix
                              # gates the REQUEST, never the response (blindness is not a control).


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `oob-listener/app.py` — tripwire: loga o hit, retorna "ok" (candidato — Fase 2 gera o real)

```python
import os
import logging
from flask import Flask, request

logging.basicConfig(level=logging.INFO)  # ensure INFO lines reach docker compose logs
app = Flask(__name__)


# oob-listener: a dumb out-of-band sink. It logs every inbound request so the student can
# confirm, via `docker compose logs oob-listener`, that the vulnerable server reached out.
# Self-hosted, air-gapped analog of a public interaction server (e.g. Burp Collaborator).
# TRIPWIRE, not a target: it holds no secret and is reachable ONLY from inside the Docker
# network (no host port). Reaching it at all is the whole proof.
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch(path):
    app.logger.info("OOB HIT path=/%s from=%s", path, request.remote_addr)
    return "ok"


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=80)
```

**Notas de implementação (validar na Fase 2):**

- **Alinhamento com o 04:** o estilo do fixed (parse com `urlparse`, checar `scheme`/`hostname` contra uma allowlist positiva, deny-by-default) é **o mesmo do `ssrf-basic/fixed/app.py`** — mostrando que a defesa **generaliza pelo arco**. A **única** diferença estrutural: o 04 dá `abort(403)`; o 16 **gateia o fetch** e mantém a resposta genérica (ver "A resposta é idêntica").
- **`except Exception: pass` (engolir o erro) é divergência DELIBERADA do 04** (que faz `except requests.RequestException as exc:` e **mostra** o erro). Surfacear o erro criaria um **oráculo in-band** (connect-refused vs timeout vs sucesso distinguiria destinos alcançáveis de inalcançáveis), **de-blindando** parcialmente o átomo. Blind ⇒ engolir. Registrar no DIFF.
- **`timeout=5`** (espelha o 04): obrigatório pra não empilhar unbounded-consumption/DoS como segunda vuln. Valor imaterial (o esboço do prompt usou `3`); mantenho `5` por consistência com o irmão.
- **Logging do listener:** `logging.basicConfig(level=logging.INFO)` + `app.logger.info(...)` garante que a linha **`OOB HIT path=/proof-ssrf-16 from=...`** chegue ao `docker compose logs` (com `python -u` no CMD do Dockerfile, sem buffering). **Fallback:** o access log do próprio werkzeug já mostra o path (`"GET /proof-ssrf-16 HTTP/1.1" 200`), mas a linha explícita `OOB HIT` é greppável e inequívoca. **Validar na Fase 2 que a linha aparece de fato nos logs.**
- **`is_allowed_destination(url)` como helper:** o esboço do prompt usava um helper. Mantive **inline** (como o 04) pra o diff ficar mínimo e o gate ficar num ponto só; a Fase 2 pode extrair um helper se ajudar a legibilidade — irrelevante à lição.
- **Prefill do form alinhado à allowlist:** o `index.html` pré-preenche `https://hooks.example.com/webhook-test` (o mesmo host da `ALLOWED_HOSTS`). Efeito: no vulnerable, o prefill busca e **falha silenciosa** (host não resolve no lab / sem egress) → resposta genérica → **demonstra a cegueira já no baseline**; no fixed, o prefill **passa** o allowlist (vetado + `https`), mostrando que a allowlist é **positiva** (permite o vetado, barra o resto). O **ataque** é trocar pra `http://oob-listener/proof-ssrf-16`.

---

## O fix e o tipo de diff

**Fix:** **VALIDAR o destino (allowlist deny-by-default)** antes do fetch — **mesma família de defesa** de SSRF do `ssrf-basic`, mostrando que a defesa **generaliza pelo arco**. Tipo de diff: **lógica-diferente** (código **adicionado** no handler do fetch) — o mesmo TIPO dos A01, dos JWT e do próprio `ssrf-basic` (código presente), **NÃO** valor-diferente (13) nem app-idêntico (par XSS). Diff no ponto do fetch.

Diff colável (candidato — Fase 2 gera o real):

```diff
 import os
+from urllib.parse import urlparse
 import requests
 from flask import Flask, request, render_template

 app = Flask(__name__)

+# Deny-by-default allowlist of vetted webhook destinations. Matched on the PARSED host.
+ALLOWED_HOSTS = {"hooks.example.com"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/ping", methods=["POST"])
 def ping():
     url = request.form.get("url", "")
-    # VULNERABLE: fire a server-side request to an attacker-controlled URL and reveal NOTHING...
-    try:
-        requests.get(url, timeout=5)
-    except Exception:
-        pass
+    # FIXED: gate the outbound request on the allowlist BEFORE fetching...
+    parsed = urlparse(url)
+    if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:
+        try:
+            requests.get(url, timeout=5)
+        except Exception:
+            pass
     return "Test ping sent."
```

**O CONTRASTE é o diff (obrigatório):** busca-sem-validar (vulnerable) vs valida-o-destino-antes-de-buscar (fixed), com a **MESMA resposta genérica nos dois**. A linha `return "Test ping sent."` fica **intocada** — o fix é sobre o **DESTINO** (se a requisição sai), não sobre esconder/mostrar conteúdo.

### Notas obrigatórias no `DIFF.md`

1. **"Deixar a resposta genérica" NÃO é defesa.** A resposta já é genérica (é blind) **nas DUAS versões**, e uma delas continua vulnerável — logo a cegueira **não impede** o servidor de fazer a requisição, e a detecção OOB continua funcionando. **Cegueira não é controle de segurança; o fix é validar o DESTINO.** (A linha de resposta idêntica no diff prova isso visualmente.)
2. **Allowlist deny-by-default > blocklist de faixas privadas, PARA O CASO BLIND.** Um filtro que só **bloqueia faixas privadas** impede o **IMPACTO** (alcançar alvo interno) mas **NÃO** impede um **callback OOB para um Collaborator EXTERNO** (que é um IP público, não uma faixa privada) — ou seja, **não impede a DETECÇÃO**, e o blind SSRF continua explorável pra fora. Uma **allowlist** bloqueia **QUALQUER** destino não vetado (interno **OU** externo), então corta **tanto a detecção quanto o impacto**. Explicar essa distinção — é o coração do "por que allowlist" no caso blind.
3. **RUGA DO LAB (ser honesto — evita ensinar errado).** No mundo real o Collaborator é **EXTERNO**; um filtro "bloqueia-privado" **NÃO** o bloquearia e a detecção **ainda passaria**. Neste lab isolado o sink OOB (`oob-listener`) é **NECESSARIAMENTE interno**, então a mesma allowlist que barra destinos internos **também** barra o nosso sink — **um artefato do lab, NÃO uma propriedade universal**. Deixar EXPLÍCITO que *"o fix não mata a detecção blind **sempre**; aqui ele mata porque nosso sink é interno; lá fora, contra um Collaborator externo, só uma allowlist (não um blocklist-de-privados) mataria"*.
4. **`abort(403)` do 04 vs resposta-idêntica do 16 (por que divergem).** O 04 (in-band) rejeita **visível** (`403`), porque a resposta dele já carrega informação; o 16 (blind) **gateia o fetch** e mantém a resposta **genérica nos dois**, porque revelar o bloqueio pela resposta contradiria a lição "olhe out-of-band". Mesma família de fix (validar destino), forma adaptada à cegueira.
5. **O fix é allowlist CORRETA, não blocklist bypassável.** Decide sobre `urlparse(...).hostname` (o host real que o cliente HTTP vai conectar), **não** por match de substring — então `http://oob-listener@hooks.example.com/` (userinfo), `http://2130706433/` (IP decimal), `http://hooks.example.com.evil.tld/` etc. **falham** (o host parseado não está na allowlist). Se o fix fosse um blocklist ingênuo, o átomo viraria silenciosamente "SSRF filter bypass" — **outro** tópico. A vuln aqui é a **AUSÊNCIA** de validação; o fix é **robusto**.
6. **Por que o listener é embarcado (Saída B).** O sink OOB do mundo real (Collaborator/`interactsh`) é externo e indisponível num lab isolado; o átomo embarca um análogo self-hosted (`oob-listener`) pra o exploit ser reproduzível sem dependência externa. Registrar (é a mesma disciplina de honestidade do 14/15).

---

## Encenação — ATOR ÚNICO, dois passos (o aluno é o pentester sondando)

Diferente do 15 (dois atores — atacante e vítima), o blind SSRF tem **UM ator**: o **pentester sondando o endpoint**. O modelo mental é em **dois passos** e o WALKTHROUGH **deixa EXPLÍCITO**. No Burp (trilha principal):

1. **DISPARAR o payload.** `POST /ping` com `url=http://oob-listener/proof-ssrf-16`. A resposta é genérica (`"Test ping sent."`) — o Burp **NÃO mostra nada útil**, **ILUSTRANDO a cegueira**.
2. **CONFIRMAR out-of-band.** `docker compose logs oob-listener` → ver **`OOB HIT path=/proof-ssrf-16`**. **ESTA é a confirmação que o corpo da resposta não pôde dar.**
3. **Repetir contra o FIXED (8116).** Mesma resposta genérica, **MAS o log do listener NÃO mostra hit** → o fix barrou a requisição pro destino não-permitido.

**PROVA-CHAVE (cravar, mostrar explicitamente):** o **vulnerable produz hit** no log do listener; o **fixed NÃO produz**. O **corpo da resposta é idêntico/genérico nos dois** — provando que em blind SSRF você **TEM** que olhar **out-of-band**, e que o fix é sobre o **destino**, não sobre a resposta.

**Baseline que já ensina a cegueira:** antes do payload do listener, submeter o prefill benigno (`https://hooks.example.com/webhook-test`) → resposta genérica → *"você não faz ideia se funcionou"*. Essa é a cegueira, de cara. Depois, o payload do listener dá a **MESMA** resposta genérica, mas agora o log confirma. (No lab isolado não há in-band baseline possível — a primeira confirmação de que o mecanismo funciona **é** o hit OOB.)

---

## A trilha — Burp principal + browser secundária (trilha dupla, `CLAUDE.md` §3.3)

O 16 **volta ao molde HTML de trilha dupla** (o 04 já era assim; espelhar). O Burp é a trilha **principal** porque é onde o pentester **planta e manipula** o payload cru (controle da URL, do encoding, do método) — a parte que ensina a profissão — enquanto a **confirmação** vem dos logs do compose (o análogo do "olhar o Collaborator").

- **Trilha principal — Burp (Repeater) + `docker compose logs`.** Cada request é um bloco colável. O aluno controla o `POST /ping` no Repeater e **confirma o SSRF nos logs** do `oob-listener`. Não é a exceção-XSS do §3.3 (não precisa de JS rodando no browser); a "prova" é o **hit no log OOB**, que o par Burp+logs entrega perfeitamente.
- **Trilha secundária — browser (opcional, baixa fricção).** Abrir `/`, submeter o form uma vez, ver `"Test ping sent."` (a cegueira num relance) e então checar `docker compose logs oob-listener` pra ver o hit. Mesmo papel de sempre: primeira experiência sem atrito. **Sem JS.**

**Nota de prosa obrigatória (DNS OOB, sem construir):** documentar que, em engagement real, **o pingback de DNS costuma ser o sinal mais confiável** (o egress filtering pode bloquear uma conexão HTTP de saída, mas o servidor quase sempre consegue **resolver** um nome, e essa resolução chega ao Collaborator). Aqui o lab usa **HTTP** por ser isolado e por o foco ser SSRF, não resolver de DNS — a nuance vai **em prosa**, sem infra de DNS.

---

## Walkthrough — estrutura e beats

Trilha principal **Burp + logs**, secundária **browser**. Ids/hosts são placeholders da execução real capturada na Fase 2. Estrutura de beats (molde do 04, com a cegueira e a detecção OOB explícitas):

> **Abertura — plantar a lição.** Tease: *no `ssrf-basic` você apontava o servidor pra um host interno e LIA o que ele te trouxe. Aqui a app bate na sua URL mas não te conta nada — resposta genérica, sem corpo, sem status. Sem output. Então acabou, não tem SSRF? Não. O SSRF está lá, completo — você só não pode LER o resultado in-band. Você vai PROVAR que a requisição aconteceu de outro jeito: apontando o servidor pra um listener que você observa, e capturando o callback out-of-band.*

1. **Context.** App web "webhook tester": `GET /` (form de URL), `POST /ping` (o servidor bate na URL como efeito colateral e devolve só um ack genérico). Isto é **A10 — Blind SSRF (out-of-band)**. **Um ator: você, o pentester.** Trilha: Burp + `docker compose logs` (principal) + browser (secundária).
2. **Spot the bug.** Mostrar `vulnerable/app.py` — o `POST /ping`. `request.form["url"]` flui direto pra `requests.get(url, ...)`, sem parsing, sem allowlist, sem checagem de destino. Igual ao 04 **nesse ponto**. A diferença: a resposta é `"Test ping sent."` — genérica, **sem eco**. Pergunta de auditoria: *"o servidor faz a requisição pra um destino que EU escolho?"* → **sim**. *"Eu consigo LER o resultado?"* → **não**. Esse é o blind SSRF. Foreshadow do fix: **validar o destino (allowlist)**.
3. **Blind vs in-band (a distinção central).** Contrastar explicitamente com o **04** (publicado): lá o `preview.html` mostrava o body buscado (você lia o dashboard interno); aqui **não existe** template de resultado — não há o que ecoar. **A requisição acontecer é a vuln; a resposta refleti-la é só conveniência.** *Blind ≠ ausente.*
4. **Sobre este lab — o listener embarcado.** Explicar o `oob-listener`: um sink OOB **tripwire** (loga o hit, não guarda segredo), interno-only. **POR QUE embarcado:** detecção de blind SSRF no mundo real usa Collaborator/`interactsh` (externos); o lab é isolado e auto-contido, então embarca o análogo. Nota de prosa: DNS pingback é o sinal mais confiável em engagement real (egress filtering) — aqui usamos HTTP por simplicidade e isolamento.
5. **The attack (o núcleo — VALIDAR RODANDO).** Dois passos:
   - **5a — DISPARAR:** no Repeater, `POST /ping` com `url=http://oob-listener/proof-ssrf-16`. Resposta: `200`, corpo `"Test ping sent."`. **O Burp não te diz nada** — essa é a cegueira, ao vivo.
   - **5b — CONFIRMAR OOB:** `docker compose logs oob-listener` → **`OOB HIT path=/proof-ssrf-16`**. **A requisição aconteceu.** O corpo da resposta não pôde provar; o log OOB provou. *"Botei `/proof-ssrf-16`, `/proof-ssrf-16` apareceu no log"* — atribuição causal limpa (path fixo).
6. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **NÃO é "sem output = sem SSRF" (a grande).** A resposta não revelou nada, e o SSRF é real (o hit OOB prova). **Cegueira ≠ ausência.**
   - **NÃO é "a resposta genérica é uma defesa".** Ela é genérica **de propósito** (é blind), e o servidor **continua** fazendo a requisição. Esconder o output não impede o SSRF.
   - **NÃO é in-band (contraste com o 04).** No 04 você **lê** o recurso; aqui você **detecta** o callback. Mesma primitiva, canal de leitura diferente (ausente).
   - **O que É (prova):** o servidor faz uma requisição pra um destino **que você escolhe** (`http://oob-listener/...`), e você **prova out-of-band** (o hit no log). A **única** correção é **validar o destino** (a fixed: allowlist, o hit some) — **não** esconder a resposta.
7. **Impact (honesto — sem overclaim).** **Blind SSRF: o servidor pode ser coagido a fazer requisições outbound arbitrárias pra destinos que o atacante escolhe, SEM o atacante ver a resposta.** Por si só (escopo do 16), é a **detecção da primitiva** — provar que o servidor sai pra fora sob seu comando. O impacto **escala** quando o SSRF alcança **serviços internos** ou **metadata de cloud** (roubo de credencial) — mas **essa escalada é assunto separado do arco de SSRF** (ver "Contraste com o arco / escopo"). **NÃO é RCE.** Sem overclaim.
8. **Why the fix works (porta 8116).** Repetir contra o `fixed/`:
   - **5a idêntico:** `POST /ping` com `url=http://oob-listener/proof-ssrf-16` → resposta `200`, `"Test ping sent."` — **exatamente igual** ao vulnerable (a resposta não mudou).
   - **5b:** `docker compose logs oob-listener` → **NENHUM** hit novo. O fix **gateou o fetch**: `http://oob-listener/...` não está na allowlist (nem é `https`), então a requisição **nunca saiu**.
   - **Prova-chave:** o corpo da resposta é **idêntico** nos dois; a **única** diferença observável é o **hit no log** (presente no vulnerable, ausente no fixed). Em blind SSRF, **é assim que você confirma tanto a vuln quanto o fix — out-of-band.**
   - **A lição do diff:** o fix **acrescenta** o gate de destino (allowlist, parse-then-check) **antes** do fetch; a resposta fica intocada. **Allowlist deny-by-default**, não blocklist (forward pro `DIFF.md`, notas #2/#3/#5).

**Trilha browser (secundária, opcional)** logo após a principal: submeter o form, ver o ack genérico, checar o log. **Sem** seção de exercícios/variações (`CLAUDE.md` §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## Impacto honesto

Blind SSRF: o servidor pode ser coagido a fazer **requisições outbound arbitrárias** pra destinos que o atacante escolhe, **SEM** o atacante ver a resposta. Por si só (escopo do 16), é **detecção da primitiva**. O impacto real **ESCALA** quando o SSRF alcança serviços internos ou metadata de cloud (roubo de credencial) — mas essa **escalada é assunto separado do arco de SSRF**; o 16 prova a primitiva (o callback confirmado). **NÃO é RCE.** Sem overclaim.

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Arco de SSRF (A10):** `04 (ssrf-basic, in-band — lê a resposta)` → `16 (blind — detecta OOB)`. O contraste com o **04** é a **ESPINHA** do átomo: o 04 dava o eco da resposta (confirmação fácil); o 16 **remove o eco** e força **detecção OOB**. **Referenciar o 04 (JÁ PUBLICADO) à vontade**, conforme a política de cross-atom reference (`CLAUDE.md` §5) — contraste explícito ancora a lição em algo que o aluno abre e valida.

**LIMITE DE ESCOPO (crítico p/ não colidir com o próximo A10):**
- **atom 16 = PROVAR que o SSRF cego existe, via OOB.** Ponto final é o **callback confirmado no log**.
- **Escalar pra alvo interno / metadata de cloud (`169.254.169.254`) / roubo de credencial NÃO é escopo do 16.** Manter o 16 na **primitiva de detecção**. O `oob-listener` é **tripwire**, não alvo; não há segredo pra ler.

**POLÍTICA DE FORESHADOW (crítico — evitar a dívida que o 05 gerou).** O 16 **ABRE** a Fase 4 (não fecha nada), mas **EVITE dívida de foreshadow** (o problema que o átomo 05 gerou referenciando 13/14 **por número**). Enunciar o limite de escopo **CONCEITUALMENTE** — *"escalar o SSRF pra alcançar serviços internos ou metadata de cloud e roubar credenciais é um passo separado do que este átomo cobre"* — **SEM** comprometer o **número/conteúdo** de nenhum átomo não-publicado. **PROIBIDO** (`CLAUDE.md` §5): referenciar ou foreshadowar `ssrf-cloud-metadata` (17) ou qualquer átomo da Fase 4 por número ou por nome; anunciar a Fase 4 ou a release `v0.4.0` no conteúdo do átomo. Na dúvida, **mantém conceitual** (a lição fica completa ancorada no conceito, não num átomo futuro; se a variante tem página na PortSwigger Academy, é lá que se manda o aluno aprofundar).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln (a que responde "what is X?"), **não** a página de listagem de labs. **Confirmar a URL por fetch na Fase 2 — não inventar** (se não confirmar, perguntar ao mantenedor).

- **Preferência:** a página **específica de Blind SSRF** — candidato **`https://portswigger.net/web-security/ssrf/blind`**. O 04 usou a página **geral** (`https://portswigger.net/web-security/ssrf`); o 16 usa a de **blind** (mais específica, casa com a lição). **Confirmar por fetch na Fase 2.**
- **Fallback (se a página blind-específica não existir com framing "what is X?"):** a página geral de SSRF (a mesma do 04) — mas **preferir a blind-específica** se existir. Se em dúvida, **perguntar ao mantenedor**.
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7 — ex. "Blind SSRF" / "Server-side request forgery (SSRF)", exatamente como a PortSwigger nomear a página).

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (form de URL — não API-only), **autoescape do Jinja LIGADO** (default). Garantir que a **ÚNICA** superfície é o blind SSRF:

- **Sem XSS:** o `index.html` é essencialmente estático; se a Fase 2 refletir a URL submetida, passa por `{{ }}` (escapado) — **sem** `|safe`/`Markup`/`render_template_string`.
- **Fetch com timeout** (`timeout=5`) → **sem** unbounded-consumption/DoS como segunda falha.
- **Listener NÃO guarda segredo** (tripwire) e é **interno-only** (sem porta no host) → **não** é segundo alvo (reachear alvo interno/metadata é escopo separado).
- **Fix é allowlist CORRETA** (deny-by-default, parse-then-check host) → **não** é blocklist bypassável (senão o átomo vira "SSRF filter bypass", outro tópico).
- **`POST /ping` retorna string genérica** (sem template de resultado); erro do fetch é **engolido** (sem oráculo in-band).

**NOTA sobre "funcionalidade legítima" (didático > realista, `CLAUDE.md` §6):** no lab isolado **não há destino externo real** pra alcançar (sem egress confiável), então a allowlist do fixed é **deny-by-default** e o uso legítimo é **CONCEITUAL** (documentado). O foco do WALKTHROUGH é o **ataque** (apontar pro `oob-listener` interno) e o **fix barrando-o**. Uma allowlist num "webhook tester" é reconhecidamente um pouco artificial (a feature existe justamente pra bater na URL do usuário) — mas o átomo demonstra o **padrão de defesa** (validar destino contra lista positiva), coerente com o arco A10; registrar essa artificialidade em prosa.

---

## HTML — `templates/index.html` (mínimo, molde do repo; sem template de resultado)

Molde do `ssrf-basic`/`sqli-union-basic`: `<!doctype>`, banner de aviso obrigatório, ≤40 linhas, ≤5 linhas de CSS inline, **sem** frameworks, **sem** JS, dica de Burp no rodapé. **NÃO há `preview.html`/template de resultado** (diferente do 04) — a resposta cega é uma **string genérica**, e a ausência do template de resultado **materializa a cegueira** (não há o que ecoar). Templates **idênticos** entre vulnerable e fixed (o diff vive só no `app.py`). Candidato (Fase 2 finaliza o texto exato):

**`templates/index.html`** (~19 linhas):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Webhook Tester</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Webhook Tester</h1>
<p>Register a webhook URL and the server sends it a test ping &mdash; a background request. The result is not shown back to you.</p>
<form method="post" action="/ping">
  <label>Webhook URL: <input type="url" name="url" size="48" value="https://hooks.example.com/webhook-test" autofocus></label>
  <button type="submit">Send test ping</button>
</form>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- Copy **front-loada a cegueira**: *"The result is not shown back to you."*
- Form pré-preenchido com `https://hooks.example.com/webhook-test` (webhook benigno, casa com a `ALLOWED_HOSTS` do fixed). O **ataque** é trocar por `http://oob-listener/proof-ssrf-16`.
- `POST /ping` **não** re-renderiza template — devolve `"Test ping sent."` (string). *(Fase 2 pode, se quiser, re-renderizar `index.html` com uma flash message neutra — sem refletir resultado de fetch; irrelevante à lição, mas mantém a cegueira.)*

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` (**com** `COPY templates`, como o 04/`idor-numeric-id`); `oob-listener` usa o Dockerfile do `internal/` do 04 (**sem** `COPY templates`, `EXPOSE 80`). Só Flask (+ `requests` no vulnerable/fixed) via pip — sem `apt`, sem banco.

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** (idêntico ao `ssrf-basic/vulnerable/Dockerfile`):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

**`oob-listener/Dockerfile`** (idêntico ao `ssrf-basic/internal/Dockerfile`):

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

`docker-compose.yml`: ver "Wiring do listener" (três services; só `vulnerable`/`fixed` publicam porta, bind **só** `127.0.0.1`; `oob-listener` nas duas redes, **sem** porta no host).

---

## Bibliotecas

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos, espelham o 04):**

```
Flask==3.0.0
requests==2.32.3
```

- **`oob-listener/requirements.txt` (espelha o `internal/` do 04 — só Flask, o listener não faz request outbound):**

```
Flask==3.0.0
```

- `os`, `logging`, `urllib.parse` são **stdlib** (não vão no `requirements`).
- **Sem pin behavior-critical:** a vuln (fetch sem validar destino) é **agnóstica de versão** — é lógica de aplicação pura (diferente dos JWT, onde a versão do PyJWT **era** o objeto de estudo, `CLAUDE.md` §8.7). Os pins são só reprodutibilidade, coerentes com o 04.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A10 — SSRF** (`atoms/A10-ssrf/`, já existe) | ROADMAP lista `ssrf-blind-oob` em A10, "Variante do 04". **Segundo átomo A10** (o 1º é o 04). |
| Posição na Fase 4 | **Primeiro — ABRE a Fase 4** | ROADMAP: **16**/17/18/19/20; os 01–15 já `[x]`. Phase-opener. |
| Eixo | **CONTINUIDADE — arco A10/SSRF** (NÃO muda de eixo) | Irmão do 04; mesma classe, eco removido. |
| Nome / classe | **Blind SSRF (out-of-band)** | O servidor busca a URL do atacante mas não devolve o resultado; detecção OOB. |
| Lição-coração | **"SSRF completo mesmo sem output; a requisição é a vuln, a visibilidade da resposta é ortogonal; blind ⇒ detectar OOB"** | A requisição acontecer é independente de a resposta refleti-la. |
| Distinção central | **BLIND vs IN-BAND** (mesma primitiva, sem canal de leitura) | O engano vizinho: "sem output = sem SSRF". Isolar. |
| Enquadramento no lab | **listener = TRIPWIRE, não alvo** (contra o `internal` do 04, que era ALVO) | O aluno confirma que a requisição escapou; não lê prêmio. |
| Decisão estrutural | **Listener OOB EMBARCADO** (`oob-listener`, container interno) | Collaborator/`interactsh` são externos e indisponíveis num lab isolado — "Saída B" (mesma família honesta do 14/15). |
| Protocolo do listener | **HTTP-only** | DNS pingback só valeria com egress filtering (ausente no lab) e ensinaria DNS, não SSRF. Nuance de DNS vai em prosa. |
| Canal de observação | **`docker compose logs oob-listener`** (igual ao 04) | Sem status page, sem porta no host. Path **fixo** `/proof-ssrf-16` (sem nonce) → causalidade limpa. |
| Tipo de átomo | **Com HTML, trilha dupla** (Burp+logs principal, browser secundária) | Espelha o 04 (que é HTML). A prova é o hit no log — Burp+logs entregam; sem JS. |
| Feature | **App web "webhook tester"** (`/`, `/ping`) | Superfície de blind SSRF mais real (webhook test/ping, ack genérico sem eco). |
| Endpoint / método | **`POST /ping`** (`request.form["url"]`) — **SINALIZADO** | Método POST travado pelo prompt; nome `/ping` casa com o flavor (fallback `/fetch`, paralelo ao 04). |
| Resposta do vulnerable | **genérica `"Test ping sent."`**, sem body/status/erro | A cegueira é o traço definidor. Se vazasse conteúdo, seria in-band (04). |
| Resposta do fixed | **IDÊNTICA** (`"Test ping sent."`), fetch gateado — **SINALIZADO** | Reconcilia a tensão do prompt: PROVA-CHAVE exige resposta idêntica; o `400` do esboço fica superado. Força "olhe OOB". |
| Fix (único eixo) | **Validar o destino (allowlist deny-by-default)** antes do fetch | Mesma família do 04; a defesa generaliza pelo arco. `abort(403)` do 04 → gate-do-fetch no 16 (blind). |
| Diff | **Lógica-diferente** (código adicionado no `/ping`) | Tipo dos A01/JWT/04; **não** valor-diferente (13) nem app-idêntico (par XSS). |
| Tratamento de erro | **`except Exception: pass`** (engolir) — diverge do 04 | Surfacear erro = oráculo in-band (de-blinda). Blind ⇒ engolir. |
| Listener | **catch-all, loga `OOB HIT path=/... from=...`, retorna `"ok"`, porta 80, interno-only** | Tripwire greppável; sem segredo; sem porta no host. |
| Wiring de rede | **`vulnerable`→`lab-vulnerable`; `fixed`→`lab-fixed`; `oob-listener`→AMBAS** | Espelha o 04. Listener em `lab-fixed` = ausência-de-hit atribuível ao CÓDIGO, não à rede. |
| HTML | **só `index.html`** (form), **sem template de resultado** | A ausência de eco materializa a cegueira (diferente do `preview.html` do 04). |
| Bibliotecas | **`Flask==3.0.0` + `requests==2.32.3`** (vuln/fixed); **`Flask==3.0.0`** (listener) | Espelha o 04. Pin não behavior-critical (SSRF é agnóstico de versão). |
| Impacto | **detecção da primitiva blind SSRF.** Não RCE. Escalada (interno/metadata) = escopo separado. | Honesto; sem overclaim; sem colidir com o próximo A10. |
| Theory primer | **PortSwigger Blind SSRF** (`/web-security/ssrf/blind`, confirmar por fetch) | Página blind-específica; o 04 usou a geral. Não inventar. |
| Foreshadow | **ZERO por número/nome**; limite de escopo **conceitual** | Evita a dívida do 05 (referenciar átomo futuro por número). |
| Portas | **8016 / 8116** (bind só `127.0.0.1`); listener **sem porta no host** | `CLAUDE.md` §8. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–8 são os centrais; 9–12 são higiene técnica / topologia. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /`** → serve o form (campo de URL, banner, dica de Burp). Template mínimo renderiza.
2. **`POST /ping` com `url=http://oob-listener/proof-ssrf-16`** → **VULNERABLE:** resposta genérica (`200`, `"Test ping sent."`), **E** `docker compose logs oob-listener` mostra **`OOB HIT path=/proof-ssrf-16`**. **Capturar o hit.**
3. **O ATAQUE (item central — VALIDAR RODANDO):** submeter a URL do listener no vulnerable → **confirmar o callback no log**. É a prova de detecção blind: o body não disse nada; o log OOB confirmou. **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** ids/responses/logs.
4. **FIXED (8116):** `POST /ping` com a **MESMA** URL do listener → **mesma resposta genérica** (`200`, `"Test ping sent."`), **MAS** o log do listener **NÃO** mostra hit novo (o fix gateou o fetch pro destino não-permitido). **Capturar a AUSÊNCIA.** Confirmar que o corpo da resposta é **byte-idêntico** ao do vulnerable.
5. **Robustez do fix (allowlist CORRETA, não blocklist):** a validação decide sobre `urlparse(...).hostname`, **não** por match de substring. Testar bypasses → **ainda barrados**: `http://oob-listener@hooks.example.com/proof-ssrf-16` (userinfo → host parseado é `oob-listener`? confirmar; na verdade `urlparse` retorna o host **depois** do `@`, então este resolve pra `hooks.example.com` — testar as duas ordens), `http://2130706433/` (IP decimal), `http://hooks.example.com.evil.test/`, `http://oob-listener:80/proof-ssrf-16`. Confirmar que **só** `https://hooks.example.com/...` passa. (Mantém o átomo com **uma vuln só**, não vira "SSRF filter bypass".)
6. **Cegueira é real:** confirmar que a resposta do **VULNERABLE** não revela nada do resultado — **sem body buscado, sem status distinguível** (sempre `200 "Test ping sent."`), **sem erro surfaceado** (engolido), **sem oráculo de timing óbvio**. *(Nota honesta: um side-channel de **duração** — alcançável-rápido vs inalcançável-lento-até-o-timeout — é inerente a QUALQUER blind SSRF e não é "óbvio" nem é o canal ensinado; o canal ensinado/confiável é o **callback OOB**. Documentar em prosa, sem overclaim de cegueira perfeita.)*
7. **Listener é tripwire, não alvo:** sem segredo, retorna `"ok"` trivial, alcançável **só** pela rede interna, **NÃO** exposto em porta do host. Confirmar que o `oob-listener` **não tem** mapeamento de porta pro host no compose. Confirmar que a linha **`OOB HIT`** aparece de fato em `docker compose logs oob-listener` (nível de log/`python -u`).
8. **Uma vuln só:** autoescape do Jinja ligado (se refletir URL, escapada); fetch com `timeout=5` (sem DoS); sem outra falha empilhada; fix é allowlist correta (não blocklist). A **única** superfície é o fetch sem validação de destino.
9. **Topologia multi-container espelha o 04:** nomes de serviço (`vulnerable`/`fixed`/`oob-listener`), esquema de porta interna (listener em 80), wiring de rede (`oob-listener` nas duas redes; `vulnerable`/`fixed` isolados) e convenção de diretório (`oob-listener/` == nome do serviço) **conformam** ao `docker-compose.yml`/`internal/` do 04. Confirmar lendo o 04. O `oob-listener` é o análogo do `internal` do 04, reaproveitado como **sink OOB** (tripwire) em vez de **alvo** (com prêmio).
10. **Primer PortSwigger** (página de **Blind SSRF**, `/web-security/ssrf/blind`) **confirmado por fetch**. Se não existir com framing "what is X?", perguntar ao mantenedor (fallback: página geral de SSRF, a do 04). Não inventar.
11. **Higiene:** portas **8016/8116** bind **só** `127.0.0.1`; `oob-listener` **interno-only** (sem `ports:`). `Flask==3.0.0`+`requests==2.32.3` instalam limpo no `python:3.11-slim`. `./atom up ssrf-blind-oob` sobe sem erro. **Validar via `docker exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`).
12. **`app.py` vulnerable × fixed:** confirmar por `diff` que a mudança é **só** a validação de destino no handler do `/ping` (ausente vs presente: import `urlparse` + `ALLOWED_HOSTS` + gate `if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:` envolvendo o fetch), e que **a linha `return "Test ping sent."` é intocada** e o resto (`GET /`, imports comuns, rodapé) e o **template** são **byte-idênticos**. Diff **lógica-diferente**.

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** validar a cadeia de ataque rodando (itens 2–4); confirmar a URL do primer por fetch (item 10); confirmar que o `OOB HIT` aparece nos logs (item 7); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo **abre a Fase 4** e **continua o arco A10** aberto pelo 04. Cada beat deve poder ser lido com o **`ssrf-basic` (04) aberto ao lado** — é o átomo-irmão e a referência viva de "como SSRF se ensina aqui". **Abrir e fechar** na lição-coração: *a requisição server-side pra um destino que você escolhe é a vuln; a visibilidade da resposta é ortogonal; blind ⇒ detectar OOB.* E na distinção **blind ≠ in-band ≠ ausente**.
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`ssrf-basic` (04) INTEIRO** (README, WALKTHROUGH, DIFF, `vulnerable/`, `fixed/`, `internal/`, e principalmente o `docker-compose.yml` — a topologia multi-container e o wiring de rede); `sqli-union-basic` (01, referência canônica — HTML/Jinja2/Dockerfile/tom); esta spec. Ler o 04 **não é pra copiar** — é pra **conformar** à convenção multi-container (nomes de serviço, porta interna, rede, diretório) que ele já cravou.
- **A SAÍDA B (listener embarcado) é o coração estrutural:** explicar **por quê** o sink OOB é embarcado (Collaborator/`interactsh` são externos e indisponíveis num lab isolado; o átomo entrega o análogo self-hosted). Sem isso o aluno não entende por que existe um terceiro container. Cravar no DIFF e no WALKTHROUGH — mesma disciplina honesta do 14/15.
- **A prova é o hit (não) aparecer no log (risco #3).** Capturar a cadeia real: vulnerable → `OOB HIT path=/proof-ssrf-16` no log; fixed → **sem** hit; resposta genérica **idêntica** nos dois. **Se não bater rodando, PARAR e avisar — NÃO inventar** logs/responses.
- **Uma vuln só:** resposta cega de propósito (nas duas versões — a cegueira não é o controle); listener é tripwire (sem segredo, interno-only); fix é allowlist **correta** (parse-then-check host, deny-by-default, **não** blocklist bypassável); fetch com timeout; autoescape ligado; sem XSS. A **única** superfície é o fetch sem validação de destino.
- **Ator único, dois passos:** rotular no WALKTHROUGH **DISPARAR** (o payload, resposta cega) e **CONFIRMAR OOB** (o log). Diferente do 15 (dois atores), aqui é o pentester sozinho sondando.
- **Impacto honesto:** **detecção da primitiva** blind SSRF. Escalada (alvo interno / metadata de cloud / roubo de credencial) é **escopo separado do arco** — enunciar **conceitualmente**, **NÃO** por número/nome de átomo futuro. **NÃO** RCE. Sem overclaim.
- **Política de referência cross-átomo:** OK citar o **04 à vontade** (publicado; o contraste in-band vs blind é a espinha). **PROIBIDO** referenciar/foreshadowar `ssrf-cloud-metadata` (17) ou qualquer átomo não-publicado/fase futura por número ou nome; **NÃO** anunciar a Fase 4 nem a release `v0.4.0` no conteúdo do átomo. O 16 **abre** a fase, mas o conteúdo do átomo fica **conceitual** sobre "o que vem depois".
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico em EN e PT (`ssrf-blind-oob — Blind SSRF (out-of-band)`, texto exato confirmável na Fase 2). Termos técnicos (SSRF, blind, in-band, out-of-band / OOB, payload, callback, listener, sink, tripwire, allowlist, deny-by-default, blocklist, egress, DNS pingback, Collaborator, webhook) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (Blind SSRF), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — preferir a página blind-específica; se não houver, perguntar ao mantenedor.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 16: `ssrf-blind-oob` — blind SSRF confirmed out-of-band via an embedded listener (A10 Server-Side Request Forgery). `` (padrão das linhas dos átomos anteriores).
- **ROADMAP.md:** marcar o átomo 16 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline (form) → ataque (payload do listener → hit no log) → contraste (o que a vuln NÃO é) → fixed (mesma resposta, **sem** hit). Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8016` (vulnerable), `127.0.0.1:8116` (fixed). `oob-listener` **interno-only**. Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre a URL do primer, a forma exata do H1, o nome do endpoint (`/ping` vs `/fetch`), a resposta do fixed (idêntica vs `400`), ou se a cadeia de ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato único, se você quiser um pointer de recall rápido independente do spec/DIFF:**

- **`ssrf-atoms-embedded-oob-listener`** — *"O arco de SSRF (A10) usa topologia multi-container: `ssrf-basic` (04) tem um serviço `internal` (ALVO, lido in-band); `ssrf-blind-oob` (16) tem um `oob-listener` (TRIPWIRE, sink OOB embarcado — análogo self-hosted do Burp Collaborator, porque o lab é isolado e não pode depender de um Collaborator externo). Ambos: serviço extra nas DUAS redes (`lab-vulnerable`+`lab-fixed`), sem porta no host; observação por `docker compose logs`. No 16 o fix é allowlist deny-by-default (parse-then-check host), e a resposta do vulnerable e do fixed é IDÊNTICA/genérica — a prova é o hit (não) aparecer no log, não o corpo da resposta."* — tipo `project`/`reference`.

**Ressalva:** esse fato já vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, salvo se você quiser o recall rápido fora do spec. Sua decisão.
