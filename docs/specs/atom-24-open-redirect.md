# Spec — Átomo 24: `open-redirect`

> Documento de especificação para o Claude Code implementar o átomo `open-redirect` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A01 (Broken Access Control)**: a pasta `atoms/A01-broken-access-control/` já contém `idor-numeric-id` (03), `path-traversal-basic` (10), `idor-uuid-guessable` (11), `bola-rest` (12) e `csrf-basic` (23). O 24 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão das irmãs, ex.: a pasta do `csrf-basic`). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER, molde do `01 sqli-union-basic` / `19 ssti-jinja`** — só `vulnerable` + `fixed`, **sem** serviço extra, **sem** datastore, sem listener, sem rede especial. Diferente do multi-container do `csrf-basic` (23), aqui não há site do atacante nem terceiro serviço: a prova vive inteira na **resposta HTTP do próprio alvo**.
>
> **A lição em uma linha:** o app recebe uma URL de destino num parâmetro (aqui `next`, no fluxo de login — o padrão de "voltar pra onde você estava") e **redireciona o usuário pra lá SEM validar que o destino é do próprio site**. O atacante monta um link que **parece** do alvo — `alvo/login?next=https://evil.example` — a vítima confia no domínio do alvo, clica, loga, e o app a **joga pra FORA**, no site do atacante. A raiz: **confiança CEGA num destino controlado pelo usuário**. O fix é o **SERVIDOR** decidir pra onde pode redirecionar (**allowlist**) — não o parâmetro; no caso do `next` de login, só permitir **PATHS INTERNOS** (o app não tem motivo legítimo de mandar pra outro domínio).
>
> **§3.3 — trilha Burp-only, E AQUI SEM a exceção client-side de browser (diferença deliberada em relação ao `21 xss-dom` e ao `23 csrf-basic`).** O open redirect se prova na **RESPOSTA HTTP** — o header **`Location`** de um `302` apontando pra fora —, montando a request no **Repeater** (`curl` como equivalente). **NÃO** há execução no browser (nenhum script roda), **NÃO** há cookie anexado, **NÃO** há vítima com browser que precise reproduzir o mecanismo. O ato **definidor** da vuln (o servidor emitir um `Location` externo a partir de um destino controlado pelo usuário) é **inteiramente server-side e visível na resposta**. Logo **NÃO usar** a exceção client-side nem qualquer "trilha browser". (A navegação real do browser até o destino é comportamento-padrão de web que se **descreve**, não algo que precise de um browser pra "provar" — ver "Payload-prova" e "WALKTHROUGH".)
>
> **NÃO há "Saída B" no sentido de "a ferramenta padrão resiste ao bug ingênuo"** (como havia no `14`/`15`/`18`/`23`): `redirect(next)` é **diretamente** mal-usável — basta o dev confiar no parâmetro. **MAS há um eixo técnico que É o risco central e DEVE ser provado por probe ANTES de escrever:** o comportamento do `redirect()`/Werkzeug na versão fixada — **quais** payloads de fato produzem um `Location` externo (o `http://evil.example` óbvio **e** o `//evil.example` protocol-relative). Ver a seção **"NÃO há Saída B — mas o comportamento do `redirect()` é o RISCO CENTRAL (probe)"** e o risco #2.
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha Burp-only**, e por que **aqui não há** exceção de browser; §4 — pasta/categoria A01; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo técnico na 1ª ocorrência, situar em A01 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind `127.0.0.1`**, destino benigno; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico de HTML/Jinja2 mínimo, single-container, estrutura de WALKTHROUGH/DIFF), o **`ssti-jinja` (19) publicado** (o **molde estrutural mais próximo**: single-container + HTML + Burp-only + convenções novas; a nota "mencionável, não aplicada" do DIFF), o **`csrf-basic` (23) publicado** (o **CONTRASTE central** — os dois em A01, os dois no contexto de login/sessão e "dirigem" a vítima, MAS o CSRF dispara uma ação de mudança-de-estado **NO ALVO** com o cookie anexado; o open redirect só **manda a vítima pra FORA**, sem ação no alvo e sem cookie), e a família **A01** publicada (`idor-numeric-id` 03, `path-traversal-basic` 10, `idor-uuid-guessable` 11, `bola-rest` 12 = molde de átomo A01). Dos dois publicados mais recentes — **`csrf-basic` (23)** e **`nosql-injection-mongo` (22)** — tirar a **VOZ/estrutura ATUAL** (abertura seca, termo definido, título=classe, spec nasce limpa). **ATENÇÃO: do 23 NÃO copiar a exceção de browser / a "trilha browser" — aqui é Burp-only puro.**
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A01 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). Justificativa do ROADMAP para este átomo: *"simples, mas frequente em bug bounty como parte de chains (ex: OAuth stealing)."*
>
> **A categoria A01 JÁ EXISTE — o 24 reaproveita a pasta.** Como fez o `csrf-basic` (23), e diferente dos átomos que criaram categoria nova, o 24 **não cria pasta**: `atoms/A01-broken-access-control/` já existe e hospeda `idor-numeric-id` (03), `path-traversal-basic` (10), `idor-uuid-guessable` (11), `bola-rest` (12) e `csrf-basic` (23). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A01-broken-access-control/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A01-broken-access-control/open-redirect/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A01 — Broken Access Control"**.
>
> **Rótulo A01 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Open redirect é **A01 — Broken Access Control** no OWASP Top 10 2021 (a edição que o projeto segue), mapeado ali via **CWE-601 (URL Redirection to Untrusted Site — "Open Redirect")**. **NÃO** relatar em que número/edição a falha caía antes nem histórico de edições — é ruído proibido pela regra atual. **Situar apenas: isto é A01 — Broken Access Control (CWE-601).** Explicar **por que** é access control (o app executa uma ação — redirecionar o usuário — para um destino **fora** do que deveria permitir, porque não impõe controle nenhum sobre o destino; a decisão de "pra onde este app pode mandar o usuário" foi delegada ao input) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec; e a DISCIPLINA DE FORESHADOW (a spec nasce limpa)

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase.
>
> **CRÍTICO (FORESHADOW, `CLAUDE.md` §5) — e esta spec É commitada no repo público, então a própria spec nasce limpa:** o átomo (e esta spec) se descreve **isolado**. **NÃO** anunciar versão/release, **NÃO** dizer "abre/fecha a fase"/"quarto da fase"/"próxima fase", **NÃO** foreshadowar átomos futuros (nem por número, nem por slug, nem por descrição). Onde precisar situar posição, **aponta para o `ROADMAP.md`**; nas frases que **proíbem** foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados). **Átomos publicados (a família A01 03/10/11/12 e o 23; e os recentes 22/23 pra voz) e o `ROADMAP.md` são citáveis à vontade.** O encadeamento phishing/OAuth que aparece em "Impacto" é **descrição da CLASSE**, não referência a átomo futuro.

## Nota de planning 3 — convenções ATUAIS: Burp-only SEM exceção de browser, abertura seca, título=classe, A01 sem arqueologia

> Seguir o `CLAUDE.md` **atual**. Pontos a fixar:
>
> - **§3.3 — Burp-only, SEM exceção client-side (a diferença deliberada em relação ao 21/23).** A trilha é **só Burp Suite** (+ `curl` como equivalente). O open redirect é **server-side observável**: a prova é o header **`Location`** do `302` na resposta, montada no **Repeater**. **NÃO** há JS executando (não é o `21 xss-dom`), **NÃO** há cookie anexado por um browser (não é o `23 csrf-basic`) — logo **NÃO** existe "trilha browser" nem exceção client-side aqui. **NÃO criar seção de exploração via browser.** *(Cuidado: vários READMEs publicados ainda dizem `via Burp Suite (primary) and browser (secondary)` — resíduo do estilo antigo. No 24, o "What to read next" diz só Burp — sem `and browser (secondary)`. E do 23 especificamente, NÃO copiar a trilha browser / a nota "curl não forja": aqui curl/Repeater **é** a prova.)*
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (login com `next`, o "voltar pra onde você estava") e a falha (o `redirect(next)` confia num destino do usuário). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** open redirect, o parâmetro `next` / `returnUrl` (o destino "de volta"), path relativo (`/dashboard`) vs URL absoluta (`https://host/...`), URL **protocol-relative** (`//host` — sem esquema; o browser resolve como `https://host`), header `Location`, allowlist vs blocklist — dar a expansão/definição na estreia. O átomo é pra quem **não** conhece a vuln.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** ("Open Redirect"), **NÃO** o stack ("...em Flask"/"...via `next`"/"...no Werkzeug"). O **slug** (`open-redirect`) qualifica o átomo — OK (como `sqli-union-basic`). O mecanismo (`redirect`, `next`, `urlparse`, Werkzeug) aparece no **corpo**, não no H1.
> - **A01 sem arqueologia** (Nota de planning 1).

---

## Identidade

- **ID:** `open-redirect`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A01 — Broken Access Control** (via **CWE-601**). Pasta `atoms/A01-broken-access-control/` (**JÁ EXISTE — o 24 reaproveita**). Confirmado contra o `ROADMAP.md` ("A01 Broken Access Control") e o `CLAUDE.md` §4. Em prosa (README/WALKTHROUGH/DIFF) usar o nome da classe — **"Open Redirect"** — e a categoria — **"A01 — Broken Access Control"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A01-broken-access-control/open-redirect/`
- **Número sequencial:** 24
- **Porta `vulnerable`:** `127.0.0.1:8024` (TRAVADO)
- **Porta `fixed`:** `127.0.0.1:8124` (TRAVADO)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos single-container 01/19.
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM** serviço extra, listener, datastore, mock, ou rede especial. Molde do 01/19. (Diferente do 23, que era multi-container com o site do atacante — aqui não há terceiro serviço.)
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos** (§5 foreshadow).
- **Branch de trabalho:** `atom/open-redirect`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato + a ressalva; confirmar por fetch na Fase 2):** ver a seção "Theory primer". **Ponto de atenção:** a PortSwigger **não tem** uma página conceitual limpa "What is an open redirect?" no nível dos outros tópicos (SQLi/XSS/SSRF/CSRF); open redirect aparece **dentro** de DOM-based vulnerabilities e de OAuth. **NÃO inventar URL — confirmar por fetch na Fase 2** e, se não houver página conceitual limpa na PortSwigger, **propor a melhor fonte conceitual (OWASP) e avisar o mantenedor**.
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# open-redirect — Open Redirect`** — `id` + nome canônico da **classe** em inglês (forma paralela às irmãs: `12` usa "Broken Object Level Authorization (BOLA)", `23` usa "Cross-Site Request Forgery (CSRF)"; aqui a classe não tem acrônimo consagrado, então o H1 é só o nome). **SEM** "Flask"/"next"/"Werkzeug" no H1. *(Alternativa de grafia: "Open Redirection", que é como a PortSwigger nomeia no material DOM-based. Confirmar na Fase 2 e casar com a grafia da fonte do primer escolhida; **preservar o nome em inglês também no README PT**.)*

---

## Classe de vulnerabilidade

**Open Redirect — o app redireciona o usuário pra um destino controlado pelo input, sem validar que o destino é do próprio site.** Uma app com login tem o padrão "voltar pra onde você estava": ela carrega uma URL de destino num parâmetro (**`next`** — em outras apps `returnUrl`, `redirect_to`, `continue`), e depois do login **redireciona** o usuário pra `next`. O redirect é feito emitindo um `302` com o header **`Location: <next>`** — e o browser segue pra lá. A falha: o servidor manda o browser pra **qualquer** destino que o `next` disser, **inclusive um domínio externo**, porque **nunca checa** que o destino é interno.

O atacante monta um link que **parece** do alvo — o domínio na barra de endereço **é** o do alvo — mas com `next` apontando pra fora: `http://alvo/login?next=https://evil.example`. A vítima confia no domínio do alvo, clica, faz login normalmente, e o app a **redireciona pra `evil.example`** — o site do atacante. O erro é o servidor tratar um **destino controlado pelo usuário** como um destino confiável.

### A lição-coração

> **"O app recebe uma URL de destino num parâmetro (aqui `next`, no fluxo de login) e redireciona o usuário pra lá SEM validar que o destino é do próprio site. O atacante monta um link que parece do alvo — `alvo/login?next=https://evil.example` — a vítima confia no domínio do alvo, clica, loga, e o app a joga pra FORA, no site do atacante. A raiz: confiança CEGA num destino controlado pelo usuário. O fix é o SERVIDOR decidir pra onde pode redirecionar (allowlist) — não o parâmetro; no caso do `next` de login, só permitir PATHS INTERNOS (o app não tem motivo legítimo de mandar pra outro domínio)."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** O redirect é uma feature **legítima e comum**: depois do login, "te levo de volta pra `/dashboard`". O destino legítimo é sempre um **path interno** (`/dashboard`, `/settings`) — relativo ao próprio site. A vuln nasce quando o dev deixa o **valor cru** do `next` virar o `Location`, sem perguntar "esse destino é do meu site?". Aí um `next` que é uma **URL absoluta** (`https://evil.example`) ou **protocol-relative** (`//evil.example`) faz o `Location` apontar pra **outro host**, e o browser sai do alvo.

### Sub-lição CRÍTICA — o fix é ALLOWLIST DE ESTRUTURA, não BLOCKLIST DE STRING

Cravar (é o coração da nota #1 do DIFF): a defesa **NÃO** é caçar padrões perigosos na string do `next` ("começa com `https://alvo.com`?", "contém `http://`?"). Blocklist de string **quebra de mil formas** (ver a nota #1 e "Payload-prova"). A defesa robusta é **allowlist de ESTRUTURA**: *o destino é um **path** do meu site — sem esquema, sem host?* Se sim, aceita; qualquer coisa com host, recusa. O **servidor** decide o destino; o input só escolhe **entre destinos internos**. É o mesmo espírito do arco Injection (input como **dado** vs input como **código**): aqui, o `next` é tratado como um **path a validar contra a estrutura do próprio site**, não como um destino a confiar.

### Por que A01 (Broken Access Control)

Open redirect é **A01 — Broken Access Control** (CWE-601 — **CWE** = Common Weakness Enumeration, o catálogo padrão de classes de fraqueza; a entrada 601 é "URL Redirection to Untrusted Site"). A01 é, no fundo, o servidor **permitir algo fora do que deveria** naquele contexto. Nas irmãs IDOR/BOLA (03/11/12) falta um **check de autorização** sobre um objeto; no `path-traversal-basic` (10) o request **sai** do diretório permitido; no `csrf-basic` (23) o servidor autoriza uma ação de mudança-de-estado sem verificar a **intenção**. No open redirect, a decisão que falha é **"pra onde este app pode mandar o usuário"**: o app deveria só redirecionar pra **dentro de si mesmo**, mas delega essa decisão ao input e acaba mandando a vítima pra **fora** — atravessando a fronteira do que o próprio site deveria poder fazer com a navegação do usuário. Situar em **A01 — Broken Access Control (CWE-601)**, explicar o **porquê** (controle ausente sobre o destino de uma ação — o redirect), **sem** contar edições antigas.

---

## NÃO há "Saída B" — mas o comportamento do `redirect()`/Werkzeug é o RISCO CENTRAL (probe)

Este é o eixo técnico que **não pode ser assumido**. Duas coisas distintas, não confundir:

**(1) NÃO há "Saída B" (a ferramenta padrão NÃO resiste ao bug ingênuo).** Nos átomos `14`/`15`/`18`/`23`, a ferramenta padrão **já mitigava** o bug ingênuo (PyJWT recusava a key confusion; `flask.session` resistia à fixation; a stdlib não resolvia entidade externa; o browser com `SameSite=Lax` não anexava o cookie cross-site), então o átomo tinha que modelar as condições reais onde a vuln vive. **Aqui não existe essa ruga:** `redirect()` é a função-padrão do Flask e é **diretamente** mal-usável — basta o dev passar o `next` cru. O átomo é **injeção direta de destino**, como o `19 ssti-jinja` era injeção direta (o dev costura o input), **sem** ferramenta-que-resiste. **NÃO inventar uma Saída B.**

**(2) MAS o comportamento exato do `redirect()`/Werkzeug É o risco central, e DEVE ser provado por probe ANTES de escrever (risco #2).** `redirect(location)` do Werkzeug seta o `Location` e devolve um `302` — mas **qual string exata** vai no `Location` para cada payload depende da versão do Werkzeug (ex.: versões antigas "autocorrigiam" um `Location` relativo pra absoluto via `autocorrect_location_header`; versões atuais passam o valor **como está**). O átomo precisa **capturar a resposta real** — o `Location` exato que sai — na versão fixada. Especificamente, confirmar por probe:

- **`next=http://evil.example`** → o `302` sai com `Location: http://evil.example` (destino externo explícito). **Esperado que saia** — `redirect()` não valida destino.
- **`next=//evil.example`** (protocol-relative) → o `302` sai com `Location: //evil.example` (como está, na versão atual) — que um browser resolve como `https://evil.example` (externo). **Esse é o payload que costuma passar quando um `http://` óbvio é barrado** por uma blocklist ingênua. Confirmar o `Location` exato que a versão fixada emite (pode ser `//evil.example` como está, ou uma forma autocorrigida).

**PROVAR rodando (risco #2) qual(is) payload(s) de fato produzem um `Location` externo na versão fixada, e travar o payload exato + a resposta capturada antes de escrever o WALKTHROUGH.** Se a versão do Werkzeug barrar/transformar algum payload de forma inesperada, **registrar qual passa** e ajustar o payload-prova. **NÃO assumir; NÃO inventar** a resposta.

---

## Contraste — com `csrf-basic` (23) e a família A01 (03/10/11/12)

O que ancora o passo "o que a vuln NÃO é". Cravar no WALKTHROUGH e no DIFF:

### Contraste CENTRAL — Open Redirect vs CSRF (`23`, publicado): "manda pra fora" vs "age no alvo"

Os dois são A01, os dois vivem num contexto de **login/sessão** e envolvem a vítima **clicando num link do atacante**. É fácil confundir. A diferença é a essência:

| Eixo | **CSRF** (`23`) | **Open Redirect** (`24`) |
|---|---|---|
| **O que acontece no ALVO** | uma **ação de mudança-de-estado** é executada (trocar o e-mail da conta) | **nada** — o alvo só emite um `302`; nenhuma ação, nenhum dado alterado |
| **O cookie de sessão importa?** | **SIM** — o ataque depende do browser anexar o cookie da vítima na request forjada | **NÃO** — o redirect não depende de cookie nenhum; funciona logado ou não |
| **Pra onde a vítima vai** | fica **no alvo** (a ação roda lá) | é **jogada pra FORA**, pro site do atacante |
| **A prova** | o **estado mudar** no alvo (e-mail trocado) | o header **`Location`** do `302` apontando pra fora |
| **A trilha** | **browser** (o cookie anexado sozinho só num browser real) | **Burp/curl** (o `Location` é server-side, visível na resposta) |

**A frase-regra:** *CSRF faz o alvo AGIR (com o cookie da vítima); open redirect só MANDA a vítima pra FORA (sem tocar o alvo).* Confundir os dois leva o aluno a "explicar" open redirect como "o atacante rouba a sessão" ou "faz uma ação no alvo" — **nada disso**: no open redirect o alvo não faz nada além de responder `302`, e o cookie é **irrelevante**. Usar o `csrf-basic` (23, publicado) como âncora: lá o cookie era a história inteira; aqui o cookie **não participa**.

### Contraste com a família A01 (03/10/11/12) — mesma categoria, eixo diferente

IDOR/BOLA (03/11/12): **ausência** de check de autorização sobre um **objeto** (o atacante lê o objeto de outro). `path-traversal-basic` (10): o atacante **sai** do diretório permitido no filesystem. No open redirect não há objeto de outro user nem filesystem — o que falta é o controle sobre o **destino de um redirect**: o app deveria mandar o usuário só pra **dentro de si**, e manda pra fora. Mesma categoria A01 (o servidor faz algo fora do escopo permitido), **eixo distinto** (destino de navegação, não ownership nem path de arquivo). Citar a família (publicada) pra ancorar "por que A01".

---

## Flavor — `next` no login (`GET /login?next=…` → `POST /login` → `redirect(next)`) — TRAVADO

Cenário canônico de open redirect: o parâmetro **`next`** no fluxo de login (o padrão "voltar pra onde você estava"). O alvo (`vulnerable` e `fixed`) tem:

- **`GET /login`** — mostra o **form de login** mínimo. Lê o `next` da query string (`?next=<destino>`, default `/dashboard`) e o carrega num **hidden field** do form (pra sobreviver ao `POST`).
- **`POST /login`** — se as credenciais demo baterem (usuário fake `demo`/`demo`), o login "tem sucesso" e o servidor **redireciona pra `next`** — **É AQUI QUE A VULN MORA** (`redirect(next)` sem validação no `vulnerable`; `redirect(safe_next(next))` no `fixed`). Credencial errada → re-exibe o form.
- **`GET /dashboard`** — página mínima de "logado" (o **destino interno legítimo**; é onde o baseline `next=/dashboard` cai). Não precisa checar auth — não é a lição; é só o palco pra o redirect interno ter um lugar pra chegar.

**Estado em memória, SEM datastore, SEM sessão persistida (candidato).** O login é **stateless**: bate a credencial demo → redireciona. **Não** precisa de `session`/`SECRET_KEY` — e isso é **didaticamente bom**, porque reforça o contraste com o `csrf-basic` (23): o open redirect **não depende de cookie nenhum**. *(Latitude de Fase 2: se preferir setar `session["user"]` pra "mais realista", é aceitável, MAS é plumbing ortogonal à vuln — o redirect fira igual com ou sem sessão. Não transformar a sessão em superfície. Se setar sessão, usar `SECRET_KEY` dummy óbvia, `CLAUDE.md` §8.3, e notar que é palco, não a vuln.)*

**Superfície = o `next` que vira `Location` no `redirect`.** `GET /login` (o form), a checagem de credencial e o `GET /dashboard` **NÃO são a vuln** — são o palco. Uma única superfície: o destino do redirect. **Sem** segunda superfície, **sem** datastore.

**A credencial demo é um atalho de auth fora de escopo** (como o token opaco do `12` ou o `X-User-ID` self-asserted do `03`): existe só pra estabelecer "login bem-sucedido → redirect". A força da senha **não é a lição** — a lição é o destino do redirect.

---

## Payload-prova — REDIRECT PRA FORA (TRAVADO; §8)

O atacante usa `http://alvo/login?next=<destino externo>`; após o login, o `302` leva a vítima pra fora. **A prova é a RESPOSTA HTTP: o header `Location`** apontando pro destino externo.

- **No `vulnerable` (:8024):** `POST /login` com credencial demo válida e `next=http://evil.example` → **`302` com `Location: http://evil.example`** (aponta pra fora). No `fixed`, o mesmo → um `Location` **interno seguro** (ou `400`). **A prova é o header `Location`.**
- **PEGADINHA CRÍTICA A TRAVAR — o payload protocol-relative.** Além do `http://evil.example` óbvio, travar também **`//evil.example`** (URL **protocol-relative** — sem esquema; o browser a resolve como `https://evil.example`). É o payload que **costuma passar** quando um filtro barra o `http://` mas esquece o `//`. **CONFIRMAR NA FASE 2, por probe** (risco #2), qual(is) desses de fato saem com `Location` externo na versão fixada do Werkzeug/Flask, e **capturar a resposta real** de cada um. **Travar o payload exato antes de escrever.**

**Por que Burp/curl bastam como prova (sem browser).** A vuln **é** o app emitir um `Location` externo a partir de um `next` controlado pelo usuário — e isso é **inteiramente visível na resposta HTTP** (o `302` + o `Location`). A navegação do browser até `evil.example` é comportamento-padrão de web (o browser segue o `Location`; um `//host` protocol-relative resolve pro esquema atual → `https://host`) — a gente **descreve** isso, não precisa de um browser pra "provar". Diferente do `21 xss-dom` (onde a prova exigia JS **executando**) e do `23 csrf-basic` (onde a prova exigia o browser **anexar o cookie sozinho**): aqui não há execução nem cookie; **o `Location` na resposta é a prova completa**.

**§8:** destino **benigno** — **`evil.example`** (`.example` é TLD reservado por RFC, não resolve pra lugar nenhum real; dado fake). O app **nunca** conecta em `evil.example` (só emite o `Location`); nada é buscado, nada é seguido pelo lab. Tudo loopback, nada destrutivo.

---

## O código — o coração no `redirect(next)`

O fix é **SERVER-SIDE** (no `app.py` do alvo), como no SQLi/SSTI. O `app.py` **DIFERE** entre `vulnerable` e `fixed`; o **único delta é a validação do `next`**. `Dockerfile`, `requirements.txt` e os templates são **idênticos** entre os dois lados.

### `vulnerable/app.py` — `redirect(next)` sem validação (candidato — Fase 2 gera o real)

```python
import os
from flask import Flask, request, redirect, render_template

app = Flask(__name__)


@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Demo auth: the seeded user logs in with demo/demo. Auth is not the point --
        # it just establishes a "successful login" so the redirect fires.
        if request.form.get("username") == "demo" and request.form.get("password") == "demo":
            next_url = request.form.get("next", "/dashboard")
            # VULNERABLE: redirect to a user-controlled destination with NO check that it
            # points inside our own site. Whatever the client puts in `next` becomes the
            # Location header -- including an external site (http://evil.example or the
            # protocol-relative //evil.example).
            return redirect(next_url)
        return render_template("login.html", next=request.form.get("next", "/dashboard"), error=True)
    # GET: show the form, prefilling next from the query string ("return to where you were").
    return render_template("login.html", next=request.args.get("next", "/dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")   # minimal "you're logged in" landing (baseline target)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — allowlist de ESTRUTURA (só path interno) (candidato — Fase 2 gera o real)

```python
import os
from urllib.parse import urlparse
from flask import Flask, request, redirect, render_template

app = Flask(__name__)


def safe_next(target, fallback="/dashboard"):
    # Allowlist by STRUCTURE: the SERVER decides where a redirect may go. A legitimate
    # `next` in a login flow is always an in-site path; there is no reason to send the
    # user to another host. Accept only an internal path -- no scheme, no host --,
    # and refuse anything else (falling back to a safe internal default).
    if not target:
        return fallback
    t = target.replace("\\", "/")          # browsers treat "\" like "/"; normalize first
    if not t.startswith("/") or t.startswith("//"):
        return fallback                     # not an internal path, or protocol-relative "//host"
    parsed = urlparse(t)
    if parsed.scheme or parsed.netloc:
        return fallback                     # any scheme or host present -> external -> refuse
    return target


@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "demo" and request.form.get("password") == "demo":
            # FIXED: the SERVER decides the destination. An internal path is honored; anything
            # with a host (or protocol-relative "//host", or a "\" trick) is refused and falls
            # back to a safe internal default. The `next` param can only pick AMONG our own paths.
            return redirect(safe_next(request.form.get("next")))
        return render_template("login.html", next=request.form.get("next", "/dashboard"), error=True)
    return render_template("login.html", next=request.args.get("next", "/dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### Notas de implementação (validar/decidir na Fase 2)

- **Wiring das rotas (candidato — confirmar na Fase 2).** `/` e `/login` no mesmo handler (GET mostra o form; POST /login faz o redirect); `GET /dashboard` é o landing. O essencial **TRAVADO**: o sink é `redirect(<next controlado pelo usuário>)` no POST de login bem-sucedido, **sem** validação no `vulnerable`. A forma exata (rotas, default `/dashboard` vs `/`, hidden field vs reler da query) é plumbing de Fase 2.
- **`next` no `POST` vem do CORPO (hidden field), prefill no `GET` vem da query (candidato).** `GET /login?next=/x` prefila o hidden `next`; o `POST` lê `request.form.get("next")`. *(Alternativa aceitável: reler `next` da query string no POST — `request.values`. Confirmar na Fase 2; o essencial é o `next` ser controlado pelo usuário e virar o `Location`.)*
- **A allowlist do `fixed` DEVE barrar as variações, não só o `http://` óbvio (risco #4).** Confirmar rodando que `safe_next` recusa: `http://evil.example` (esquema+host), `//evil.example` (protocol-relative), `https://demo@evil.example` (userinfo), e as variações com **backslash** `/\evil.example` (o browser trata `\` como `/`; `urlparse` **não** normaliza, por isso o `.replace("\\", "/")` vem **antes**). E que **aceita** paths internos legítimos (`/dashboard`, `/settings`). Cravar: a defesa é **estrutural** (é um path nosso?), não caça-string.
- **Fallback do `fixed` (candidato `/dashboard`).** Quando o `next` não é um path interno seguro, cair num **destino interno padrão** (`/dashboard`). *(Alternativa aceitável, `CLAUDE.md`-neutra: responder `400`. Confirmar na Fase 2; o fallback-interno preserva a feature — um `next` interno legítimo continua funcionando — e dá o contraste mais limpo no WALKTHROUGH: `Location` interno vs externo.)*
- **`redirect()` não segue nada** — só seta o `Location` e devolve o `302`. O lab **nunca** conecta em `evil.example`. Confirmar que o `curl` de validação **não** usa `-L` (não seguir o redirect) — a prova é o header, não a navegação.
- **Banner de aviso (§8) em TODA página HTML** (`login.html` e `dashboard.html`). Confirmar na Fase 2.

---

## O fix e o tipo de diff

**Fix:** **allowlist de estrutura, server-side** — validar que o `next` é um **path interno** (sem esquema, sem host, não protocol-relative, sem truque de backslash) antes de redirecionar; senão, cair num destino interno seguro (candidato `/dashboard`) ou `400`. Tipo de diff: **lógica-diferente** — a introdução do `safe_next` + o `redirect(safe_next(next))` no lugar de `redirect(next)`. O resto (`import` base, o form, a checagem de credencial, o `GET /dashboard`, o `__main__`, os templates) é **byte-idêntico**. O `import` extra (`from urllib.parse import urlparse`) e a função `safe_next` são o delta.

Diff colável (candidato — a Fase 2 gera o real; recortes do `app.py`):

```diff
 import os
+from urllib.parse import urlparse
 from flask import Flask, request, redirect, render_template

 app = Flask(__name__)


+def safe_next(target, fallback="/dashboard"):
+    if not target:
+        return fallback
+    t = target.replace("\\", "/")
+    if not t.startswith("/") or t.startswith("//"):
+        return fallback
+    parsed = urlparse(t)
+    if parsed.scheme or parsed.netloc:
+        return fallback
+    return target
+
 @app.route("/", methods=["GET"])
 @app.route("/login", methods=["GET", "POST"])
 def login():
     if request.method == "POST":
         if request.form.get("username") == "demo" and request.form.get("password") == "demo":
-            next_url = request.form.get("next", "/dashboard")
-            return redirect(next_url)                       # user-controlled destination, unchecked
+            return redirect(safe_next(request.form.get("next")))   # server decides: internal path only
         return render_template("login.html", next=request.form.get("next", "/dashboard"), error=True)
     return render_template("login.html", next=request.args.get("next", "/dashboard"))
```

**O CONTRASTE é o diff (obrigatório):** `redirect(<next cru>)` (vulnerable) vs `redirect(safe_next(<next>))` (fixed). **A única mudança é quem decide o destino** — o input (vulnerable) ou o servidor validando a estrutura (fixed).

### Notas obrigatórias no `DIFF.md`

1. **ALLOWLIST DE ESTRUTURA, NÃO BLOCKLIST DE STRING (nota "mencionável, não aplicada" — molde 19/20/21).** Nomear a intuição errada: *"é só checar se o `next` começa com `https://alvo.com`"* ou *"bloquear `http://`"*. Mostrar **por que a blocklist QUEBRA**:
   - **`https://alvo.com.evil.example`** — o prefixo `https://alvo.com` **casa**, mas o host real é `evil.example` (o `alvo.com` virou um rótulo de subdomínio do atacante).
   - **`https://alvo.com@evil.example`** — o `alvo.com` é o **userinfo** (usuário), o host é `evil.example`; "começa com `https://alvo.com`" **casa**, mas vai pra fora.
   - **`//evil.example`** — **protocol-relative**: não tem `http://`/`https://` pra bloquear, e ainda assim o browser resolve pra `https://evil.example`.
   - **`/\evil.example`** e variações com **backslash** — o browser trata `\` como `/` (`/\evil.example` ≈ `//evil.example`), mas muitos filtros/parsers não normalizam.
   - **encoding** (`%2f%2fevil.example`) e afins.
   - **Cravar:** contra string-matching o atacante tem infinitas formas; a defesa robusta é **allowlist de ESTRUTURA** — *o destino é um **path** do meu site (sem esquema, sem host, não protocol-relative)?* — não caça-padrões. **A blocklist é DESCRITA, não aplicada** (mesmo espírito do sandbox do 19, do `defusedxml` mencionado, das notas "defesa mais fraca/errada, não aplicada" dos átomos anteriores). O átomo aplica a **allowlist estrutural**.
2. **POR QUE PATH INTERNO BASTA AQUI (e quando NÃO bastaria).** O `next` de login **não tem motivo legítimo** de ir pra outro domínio → **só-path-interno cobre 100% do uso legítimo e fecha o ataque**. **Nota curta, mencionável não aplicada:** se o app **precisasse** redirecionar pra domínios externos **conhecidos** (SSO cross-domain, gateway de pagamento, retorno de OAuth), o fix seria uma **allowlist de HOSTS** (uma **lista fechada** de destinos externos permitidos) — mencionar como a variante pra **esse** caso, **NÃO aplicar** (o nosso app não precisa; forçar host-allowlist aqui seria over-engineering e turvaria a lição).
3. **IMPACTO HONESTO + CONTRASTE.** **Baixo sozinho** — não vaza dado, não executa nada, não muda estado no alvo. **Real como ELO de corrente:** (a) dá **credibilidade a phishing** — o link começa no **domínio confiável** do alvo, então a vítima confia antes de ser jogada pra fora; (b) vira **roubo de token** em fluxos **OAuth/SSO** onde o `redirect_uri`/retorno é mal-validado (o token de autorização acaba entregue no destino do atacante). **Descrição da CLASSE** (o encadeamento típico), **SEM modelar uma chain** neste átomo (§8 — sem armar o roubo de token). **Contraste com o `csrf-basic` (23):** CSRF dispara uma **ação NO ALVO** (com o cookie da vítima anexado); open redirect só **MANDA a vítima pra FORA** (nenhuma ação, nenhum cookie no alvo). **Sem overclaim** — o átomo prova o redirect pra fora; a escalada (phishing/OAuth) é **descrita, não armada**.

---

## Biblioteca / mecanismo

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask.** `os` e `urllib.parse` são **stdlib** (o fix usa `urlparse`). **Sem banco, sem `requests`, sem segunda dependência.** Single-container, sem datastore.
- **O pin é BEHAVIOR-RELEVANTE aqui (diferente do "pin normal" do 19).** O comportamento do `redirect()`/Werkzeug — **qual `Location` exato sai** para cada payload (o `//evil.example` como está vs autocorrigido) — é o **eixo técnico do átomo** e **muda entre versões** do Werkzeug. **Confirmar por probe na versão fixada, ANTES de escrever** (risco #2), qual payload produz um `Location` externo e **capturar a resposta real**. Candidato de pin `Flask==3.0.0` (que traz o Werkzeug correspondente — casando com os irmãos 01/12/19); **confirmar** que instala em `python:3.11-slim` (wheel) e que o `redirect()` se comporta como o WALKTHROUGH descreve.

---

## WALKTHROUGH — abertura seca, trilha Burp-only (SEM browser)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (login com `next`, o "voltar pra onde você estava") e a falha (o `redirect(next)` confia num destino do usuário). Trilha **ÚNICA: Burp** (`curl` como equivalente — GET/POST simples; a prova é o header `Location` na resposta). **NÃO** criar seção de browser, **NÃO** usar exceção client-side.

**Abertura (candidato — plantar a lição, seco):**

> *A app tem um login com o padrão "voltar pra onde você estava": a URL de destino vem num parâmetro `next` (`/login?next=/dashboard`), e depois de um login bem-sucedido o servidor te redireciona pra lá. O problema: ele redireciona pra **qualquer** destino que o `next` disser, sem checar que é do próprio site. Um atacante monta um link que **parece** do alvo — `http://127.0.0.1:8024/login?next=http://evil.example` — a vítima confia no domínio, loga normalmente, e o app a joga pra **fora**, no site do atacante. A prova está na resposta: o header `Location` do `302` aponta pra `evil.example`.*

Beats (molde do 19/23 publicado — abertura seca, seções numeradas `## 1..6`, Burp-only):

1. **Context.** Feature: login com `next` (o "voltar pra onde você estava"). Definir na estreia: **open redirect** (o app redireciona pra um destino controlado pelo usuário sem validar que é interno), **`next`/`returnUrl`** (o parâmetro que carrega o destino "de volta"), **path relativo** (`/dashboard`) vs **URL absoluta** (`https://host/...`), **URL protocol-relative** (`//host` — sem esquema; o browser resolve pro esquema atual → `https://host`), header **`Location`** (o header do `302` que diz ao browser pra onde ir). Isto é **Open Redirect**, sob **A01 — Broken Access Control (CWE-601)**. Topologia: `vulnerable` (:8024), `fixed` (:8124), single-container. Trilha: **Burp/curl** — a prova é o `Location` na resposta.
2. **Spot the bug.** Mostrar o `POST /login` do `vulnerable/app.py` — no sucesso, `return redirect(request.form.get("next"))`, **sem** validação. Pergunta de auditoria: *"esse redirect confia no `next` do usuário — ele checa que o destino é do meu site?"* → **não**. Foreshadow do fix: o **servidor** decidir o destino (só path interno), não o parâmetro.
3. **Exploitation via Burp Suite (a prova é o header `Location`).**
   - **Baseline (feature benigna):** `POST /login` com credencial demo válida e `next=/dashboard` → `302` com `Location: /dashboard` (**path interno** — o uso legítimo do "voltar pra onde você estava"). Equivalente: `curl -i -d 'username=demo&password=demo&next=/dashboard' http://127.0.0.1:8024/login` (sem `-L` — ler o header, não seguir).
   - **Montar o payload externo:** trocar `next` por `http://evil.example`. No Repeater, mandar `POST /login` com `username=demo&password=demo&next=http://evil.example`.
   - **Disparar (o ataque):** a resposta é `302` com **`Location: http://evil.example`** — o app manda a vítima pra **fora**. **A prova é o header.** *(Como o link começa em `http://127.0.0.1:8024/login?...`, a vítima vê o domínio do alvo e confia — a essência do open redirect.)*
   - **A pegadinha protocol-relative:** trocar `next` por `//evil.example` → o `302` sai com `Location: //evil.example` (a versão fixada emite [CONFIRMAR NA FASE 2 o `Location` exato]). Um browser resolve `//host` pro esquema atual → `https://evil.example` (externo). **É o payload que passa quando um filtro barra só o `http://`.**
   - **§8 (cravar):** destino **benigno** (`evil.example`, TLD reservado), tudo loopback; o app **nunca** conecta em `evil.example` (só emite o `Location`).
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa:
   - **NÃO é XSS.** Nenhum script é injetado nem executado; o servidor só emite um header `Location` (um `302`). Não há sink de HTML/JS. *(Contraste com os átomos de XSS publicados — lá o payload é script executando; aqui é um header de redirect.)*
   - **NÃO é CSRF.** Nenhuma ação de mudança-de-estado roda no alvo, nenhum cookie é anexado nem importa. O redirect só **manda a vítima pra fora**. *(Contraste com o `csrf-basic` (23), publicado: lá o cookie da vítima era anexado e o alvo executava a troca de e-mail; aqui o alvo não faz nada além de responder `302`, e o cookie é irrelevante.)*
   - **NÃO é um redirect legítimo.** A app **não deveria** mandar o usuário pra outro host nesse fluxo — um `next` legítimo é sempre um path interno. **Prova de isolamento:** `next=/dashboard` (path interno) volta `Location: /dashboard` **idêntico** no vulnerable e no fixed; só o destino **externo** separa os dois.
   - **O que É (prova):** o servidor confia num **destino controlado pelo usuário** e emite um `Location` **externo**. A correção é o **servidor** decidir o destino — allowlist de **estrutura** (só path interno).
5. **Impact (honesto — sem overclaim).** **Baixo isolado:** não vaza dado, não executa nada, não muda estado no alvo. **Real como elo de corrente:** dá **credibilidade a phishing** (o link começa no domínio confiável do alvo antes de jogar a vítima pra fora) e, em fluxos **OAuth/SSO** com retorno/`redirect_uri` mal-validado, pode virar **roubo de token**. É **descrição da classe** — o átomo prova o **redirect pra fora**; a escalada é **descrita, não armada** (§8). **Sem overclaim** (não inflar pra "account takeover" direto).
6. **Why the fix works (porta 8124).** Repetir contra o `fixed/`:
   - **Os MESMOS payloads externos** (`http://evil.example` **e** `//evil.example`) → o fixed **recusa o host externo** e cai no destino interno seguro (`Location: /dashboard`) [ou `400`, se essa for a escolha de Fase 2]. **Confirmar que o `//evil.example` também é barrado** — não só o `http://` óbvio (o cerne da nota #1: allowlist de estrutura pega os dois).
   - **Prova de isolamento:** `next=/dashboard` (path interno legítimo) funciona **idêntico** nos dois lados (`Location: /dashboard`). Só o destino externo separa `vulnerable` de `fixed`.
   - **A lição do diff:** o fix é **allowlist de estrutura** (nota #1 — não blocklist de string); **path interno basta aqui** (nota #2 — host-allowlist só se precisasse de externos conhecidos); **impacto honesto** = elo de phishing/OAuth, **não** ação no alvo como o CSRF (nota #3).

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Payloads/responses (o `Location` externo; o `Location` interno no fixed) são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**Open redirect — baixo isolado, perigoso como elo de corrente.** Sozinho, o átomo prova **uma** coisa: o app emite um `Location` externo a partir de um destino controlado pelo usuário. **Não** vaza dado, **não** executa código, **não** muda estado no alvo (contraste direto com o `csrf-basic` 23, onde a ação rodava no alvo). O valor real da classe está no **encadeamento**: (a) **phishing** com credibilidade — o link começa no **domínio confiável** do alvo, o que baixa a guarda da vítima antes de ela ser jogada pro site do atacante; (b) **roubo de token** em fluxos **OAuth/SSO** onde o retorno é mal-validado — o open redirect vira o veículo pra desviar um código/token de autorização pro atacante. Isso é **descrição da CLASSE** (por que a indústria trata open redirect como bug de bug bounty apesar do impacto isolado baixo), **NÃO** uma chain armada neste átomo. **Sem overclaim:** a **prova do lab** é o `Location` externo; a escalada é **descrita, não armada** (§8 — sem modelar OAuth nem phishing real). **Sem foreshadow.**

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (form de login + uma landing mínima de "logado" — não API-only; **e o browser NÃO é necessário pra provar**: a prova é o header `Location`, §3.3 Burp-only). Garantir que a **ÚNICA** lição é o `redirect` confiar no `next`:

- **`GET /login`, a checagem de credencial e `GET /dashboard` NÃO são a vuln.** São só o palco (mostrar o form, estabelecer "login bem-sucedido", dar um destino interno pra o baseline cair). A **única** superfície é o destino do redirect (o `next`).
- **O `fixed` muda SÓ a validação do `next`** (o `safe_next` + o `redirect(safe_next(...))`). Todo o resto (form, credencial, `/dashboard`, templates) é **byte-idêntico**. O **`next`-validation é o único delta**.
- **Sem datastore, sem sessão como superfície, sem segredo real.** Estado em memória; login stateless (candidato) — o que **reforça** que o open redirect não depende de cookie (contraste com o 23). Se a Fase 2 optar por setar `session` pra realismo, `SECRET_KEY` dummy e a sessão é **palco**, não a vuln.
- **`redirect()` não segue nada** — só emite o `Location`. O app nunca conecta no destino externo. Sem segunda superfície (nada de SSRF acidental — o `redirect` é o browser que segue, não o servidor).

---

## HTML — `templates/` (mínimo, molde do 01; `login.html` + `dashboard.html`)

Molde do `sqli-union-basic` / `ssti-jinja`: `<!doctype>`, banner de aviso **obrigatório**, ≤40 linhas cada, ≤5 linhas de CSS inline, **sem** frameworks, **sem** JS, dica de Burp no rodapé. Os templates são **byte-idênticos** entre `vulnerable` e `fixed` (o diff vive só no `app.py`).

- **`templates/login.html`** (~20–25 linhas): banner de aviso; um `<form method="post" action="/login">` com `<input name="username">`, `<input name="password" type="password">`, um **`<input type="hidden" name="next" value="{{ next }}">`** (carrega o `next` pro POST), o botão de submit, e (se `error`) uma linha de "invalid credentials"; rodapé com a dica de Burp. O campo `next` é o que o aluno manipula.
- **`templates/dashboard.html`** (~12–15 linhas): banner de aviso; uma linha "You are logged in." (a landing interna — o destino do baseline `next=/dashboard`). Mínimo absoluto.
- **Sem JS, sem framework** (`CLAUDE.md` §3.3). CSS mínimo inline. Banner em **toda** página (`CLAUDE.md` §8.2).

*(A Fase 2 finaliza o texto exato; o essencial: o `next` chega ao POST via hidden field, e o `dashboard` existe pra o redirect interno ter onde cair.)*

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` — molde do `sqli-union-basic`/`ssti-jinja` (**com** `COPY templates`). Só Flask via pip — sem `apt`, sem banco. `urllib.parse` é stdlib (nada a instalar pro fix).

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** (candidato — idênticos entre si):

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

**`docker-compose.yml`** (candidato — molde do 01/19, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8024:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8124:5000"
```

**Sem `networks:`, sem serviço extra, sem `depends_on`, sem healthcheck.** Molde simples do 01/19. (Diferente do 23, que tinha três serviços.)

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Ressalva importante (a razão de este primer precisar de decisão do mantenedor):** a PortSwigger **não tem** uma página conceitual de topo "What is an open redirect?" no nível de SQLi/XSS/SSRF/CSRF. Open redirect aparece na Academy **dentro** de outros temas — principalmente **DOM-based open redirection** (no material de DOM-based vulnerabilities) e como peça de **OAuth authentication**. Nenhuma delas é um "what is X?" limpo e stack-neutro pra um open redirect **server-side** como o deste átomo.
- **Candidatos a confirmar por fetch na Fase 2 (ranqueados):**
  1. **OWASP — "Unvalidated Redirects and Forwards Cheat Sheet"** (OWASP Cheat Sheet Series). É a fonte conceitual mais **limpa e stack-neutra** pra um open redirect server-side, e alinhada ao mapeamento CWE-601/A01. **Candidato preferido** se a PortSwigger não tiver página conceitual limpa. URL a confirmar por fetch (provavelmente sob `cheatsheetseries.owasp.org/...`) — **NÃO cravar sem fetch**.
  2. **PortSwigger — a página de open redirection** (dentro de DOM-based), se ao fetch ela tiver um framing conceitual utilizável. **Ressalva:** é DOM-específica; o nosso átomo é **server-side** — se ela ancorar a lição em DOM, pode confundir. Avaliar no fetch.
- **DECISÃO PENDENTE PRO MANTENEDOR (Fase 2):** confirmar por fetch qual fonte usar. Se a PortSwigger não tiver página conceitual limpa (o esperado), **propor a OWASP Cheat Sheet e avisar** — é um desvio consciente da preferência "PortSwigger primeiro" do `CLAUDE.md` §5, justificado pela ausência de página conceitual limpa na Academy pra esta classe. **NÃO inventar URL nem grafia.**
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7), casando com a grafia exata da fonte escolhida.
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo dos irmãos).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A01 — Broken Access Control** (`atoms/A01-broken-access-control/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `open-redirect` em A01; `CLAUDE.md` §4 fixa a pasta. CWE-601. Situar em A01 **sem arqueologia**. |
| Posição na fase | Ver `ROADMAP.md` | A posição/ordinal/release vivem só no ROADMAP. Spec e conteúdo nascem **limpos** (foreshadow §5). |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Molde do 01/19. Sem serviço extra, sem datastore. (Diferente do multi-container do 23.) |
| Trilha | **Burp-only (+ curl), SEM browser** | §3.3 atual. A prova é o header `Location` (server-side). **SEM** exceção client-side (diferente do 21/23) — não há JS executando nem cookie anexado. |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe aqui** | `redirect()` é diretamente mal-usável (dev confia no `next`). Injeção direta de destino, como o 19. **NÃO inventar Saída B.** |
| Risco central técnico | **Comportamento do `redirect()`/Werkzeug (qual `Location` sai) — provar por PROBE** | O `Location` exato de cada payload (o `//evil.example` como está vs autocorrigido) muda por versão. Confirmar rodando ANTES de escrever (risco #2). |
| Lição-coração | **O app confia num destino controlado pelo usuário e redireciona pra fora; o fix é o SERVIDOR decidir (allowlist de estrutura, só path interno).** | A raiz é confiança cega no `next`. |
| Sub-lição | **Allowlist de ESTRUTURA, não blocklist de string** | Blocklist quebra (subdomínio, `@` userinfo, `//`, backslash, encoding); estrutura (é um path nosso?) não. |
| Por que A01 | **Controle ausente sobre o destino de uma ação (o redirect)** — CWE-601 | O app deveria só mandar o usuário pra dentro de si; delega ao input e manda pra fora. |
| Flavor — **TRAVADO** | **`next` no login** (`GET /login?next=…` → `POST /login` → `redirect(next)`) | Cenário canônico ("voltar pra onde você estava"); superfície = o `next`. Usuário demo fake; estado em memória, sem datastore. |
| Payload-prova — **TRAVADO** | **`next=http://evil.example` → `Location` externo** (vulnerable); interno/`400` (fixed). **Travar também `//evil.example`** (protocol-relative). | Prova = o header `Location`. Benigno (`evil.example` reservado), loopback (§8). Payloads exatos confirmados por probe (risco #2). |
| Código vulnerable | **`return redirect(request.form.get("next"))`** (sem validação) | O destino cru do usuário vira o `Location`. |
| Código fixed | **`redirect(safe_next(next))`** — allowlist de estrutura via `urlparse` (sem esquema/host/`//`/`\`), fallback interno | O servidor decide; só path interno passa. Estrutural, não caça-string. |
| Fallback do fixed | **Destino interno padrão (`/dashboard`)** | Preserva a feature (next interno legítimo funciona) e dá o contraste mais limpo. Alternativa `400` aceitável (confirmar Fase 2). |
| `app.py` vuln × fixed | **DIFERE — a validação do `next`** (`safe_next` + o wrap do `redirect`) | O delta é o `next`-validation; Dockerfile/requirements/templates idênticos. |
| Sessão/cookie | **Não é a vuln — login stateless (candidato)** | O open redirect não depende de cookie (reforça o contraste com o 23). Sessão, se usada, é palco (`SECRET_KEY` dummy). |
| Bibliotecas | **`Flask==3.0.0`** (pin **behavior-relevante**) + stdlib `urllib.parse` | Sem datastore, sem dep extra. O comportamento do `redirect()`/Werkzeug É o eixo — confirmar por probe. |
| Impacto | **Baixo isolado; elo de chain (phishing/OAuth).** NÃO ação no alvo (contraste com 23). | Honesto; escalada descrita, não armada. Sem overclaim, sem foreshadow. |
| Theory primer | **PENDENTE — provável OWASP "Unvalidated Redirects and Forwards Cheat Sheet"** (PortSwigger não tem página conceitual limpa) | Confirmar por fetch na Fase 2; se PortSwigger não tiver "what is X?" limpo, propor OWASP e avisar. Não inventar. Nome em inglês no PT. |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. |
| Título (H1) | **`open-redirect — Open Redirect`** (classe, sem stack) | `CLAUDE.md` §5. Sem "Flask"/"next"/"Werkzeug". Grafia confirmável na Fase 2. |
| Foreshadow | **ZERO pra frente** | `CLAUDE.md` §5. Não nomear átomos não-publicados/posição de fase/release. Publicados (A01 03/10/11/12 e 23; recentes 22/23) e ROADMAP OK. |
| Portas | **8024 / 8124** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–5 são os centrais; 6–9 são higiene/isolamento. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **Baseline (os dois lados).** `POST /login` com credencial demo válida e **`next=/dashboard`** (path interno) → após o login, `302` com **`Location` interno** (`/dashboard`) — o uso legítimo do "voltar pra onde você estava" — **idêntico** no vulnerable (8024) e no fixed (8124).
2. **O PROBE TÉCNICO (VALIDAR RODANDO — risco central).** Quais payloads de `next` de fato redirecionam pra **FORA** na versão fixada do Werkzeug/Flask: **`http://evil.example`** E **`//evil.example`** (protocol-relative). **Travar o(s) payload(s) que saem e CAPTURAR o `Location` exato** de cada um. Se o comportamento do Werkzeug barrar/transformar algum, **registrar qual passa** e ajustar o payload-prova. **NÃO assumir; NÃO inventar.**
3. **O ATAQUE (VALIDAR RODANDO).** `POST /login` com credencial válida e `next=<payload externo>` no **vulnerable** (8024) → `302` com **`Location: <destino externo>`**. **CAPTURAR** a request/response reais (o header `Location` é a prova). `curl -i` sem `-L`. **Se não reproduzir, PARAR e avisar — NÃO inventar** prova.
4. **FIXED (VALIDAR RODANDO).** O **MESMO** payload externo → o fixed **NÃO** redireciona pra fora (`Location` interno seguro, ex.: `/dashboard`, ou `400`). **CAPTURAR.** Confirmar que **`//evil.example` também é barrado** (não só o `http://` óbvio), e que os truques de **backslash** (`/\evil.example`) e **`@` userinfo** (`https://demo@evil.example`) são recusados. Confirmar que um path interno legítimo (`/settings`) é **aceito**.
5. **Prova de isolamento.** `next=/dashboard` (path interno legítimo) funciona **idêntico** nos dois lados; só o destino **externo** separa `vulnerable` de `fixed`.
6. **Uma vuln só.** Só o `redirect` do `next`; `GET /login`, a checagem de credencial e `GET /dashboard` **não** são a vuln; o `fixed` muda **só** a validação do `next`. Sem datastore, sem segunda superfície. O `redirect()` **não** segue o destino (sem SSRF acidental — quem segue é o browser).
7. **§8.** Destino **benigno** (`evil.example`, TLD reservado — não resolve, nunca é conectado pelo lab); portas **8024/8124** bind **só** `127.0.0.1`; nada destrutivo; se houver `SECRET_KEY`, é dummy óbvia.
8. **`app.py` vulnerable × fixed:** confirmar por `diff` que a **única** mudança é a **validação do `next`** (`import urlparse` + `safe_next` + `redirect(safe_next(...))`), e que o resto (form, credencial, `/dashboard`, `__main__`) e os **templates** (`login.html`, `dashboard.html`) e o `Dockerfile`/`requirements.txt` são **idênticos**. `./atom up open-redirect` sobe os dois sem erro. **Validar via `docker exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`).
9. **Theory primer + H1.** Confirmar a fonte do primer **por fetch** (provável OWASP "Unvalidated Redirects and Forwards Cheat Sheet"; checar se a PortSwigger tem página conceitual limpa — se não, propor OWASP e **avisar o mantenedor**). **NÃO inventar** URL/grafia. Confirmar a **grafia exata do H1** (`Open Redirect` vs `Open Redirection`).

**Bloqueante remanescente:** nenhum de decisão de design. **Pendências de Fase 2 (não bloqueantes agora):** o **probe técnico** (item 2 — qual payload sai, e o `Location` exato) é o risco central e **fecha rodando**; capturar o ataque no vulnerable e o bloqueio no fixed (itens 3–4); confirmar a fonte/URL/H1 do primer por fetch (item 9, com a decisão OWASP-vs-PortSwigger pro mantenedor); confirmar o pin do Flask/Werkzeug por probe; gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **injeção direta de destino** — sem Saída B, sem ferramenta-que-resiste; o dev confia no `next`. Cada beat deve poder ser lido com o **`ssti-jinja` (19)** aberto ao lado (o molde single-container/HTML/Burp-only/voz atual, e a nota "mencionável, não aplicada") e o **`csrf-basic` (23)** ao lado (o **CONTRASTE central** — CSRF age no alvo com o cookie; open redirect só manda pra fora). **Abrir e fechar** na lição-coração: *o app confia num destino do usuário e redireciona pra fora; o fix é o servidor decidir (allowlist de estrutura, só path interno).*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`sqli-union-basic` (01) INTEIRO** (molde canônico HTML/estrutura), **`ssti-jinja` (19) publicado** (molde estrutural mais próximo: single-container + HTML + Burp-only + convenções novas; a nota "mencionável, não aplicada"), **`csrf-basic` (23) publicado** (o CONTRASTE central; **MAS NÃO copiar a exceção de browser / a trilha browser / a nota "curl não forja" — aqui é Burp-only puro**), a família **A01** (03/10/11/12, molde de átomo A01). **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar trilha browser, encenação, nem arqueologia OWASP.
- **NÃO há Saída B (crítico), MAS provar o comportamento do `redirect()` por probe (risco #2):** `redirect()` é diretamente mal-usável (não há ferramenta-que-resiste). **Mas o `Location` exato que sai pra cada payload muda por versão do Werkzeug** — **confirmar rodando ANTES de escrever** qual payload produz `Location` externo (o `http://` óbvio E o `//evil.example`), e **capturar a resposta real**. **Se não reproduzir como descrito, PARAR e avisar — NÃO inventar** responses.
- **Burp-only, SEM browser (a diferença deliberada em relação ao 21/23):** a prova é o header `Location` na resposta — visível no Repeater/`curl -i` (sem `-L`). **NÃO** criar seção de browser, **NÃO** usar exceção client-side. A navegação real do browser até o destino (e a resolução de `//host` pro esquema atual) é **descrita**, não "provada" por um browser. No "What to read next" do README, **só Burp** — sem `and browser (secondary)`.
- **A prova é o `Location` (riscos #3/#4):** capturar a cadeia real: vulnerable → `Location` externo; fixed → `Location` interno (ou `400`), com o `//evil.example` também barrado. **Se não bater rodando, PARAR e avisar — NÃO inventar** prova.
- **A sutileza que NÃO pode enfraquecer a lição:** o fix é **allowlist de ESTRUTURA** (é um path nosso, sem host?), **NÃO** blocklist de string (`começa com https://alvo.com`, `bloquear http://`) — que quebra por subdomínio (`alvo.com.evil.example`), `@` userinfo (`alvo.com@evil.example`), protocol-relative (`//evil.example`), backslash (`/\evil.example`) e encoding. A blocklist é **DESCRITA, não aplicada** (nota #1 do DIFF, molde 19/20/21). O `fixed` normaliza `\`→`/` **antes** do `urlparse` (o `urlparse` não normaliza backslash).
- **Path interno basta AQUI (nota #2):** o `next` de login não tem motivo de ir pra outro domínio → só-path-interno cobre 100% do legítimo. Se precisasse de externos conhecidos (SSO/OAuth/pagamento), o fix seria **allowlist de HOSTS** (lista fechada) — **mencionar, não aplicar**.
- **Uma vuln só:** foco no `redirect` confiar no `next`. `GET /login`/credencial/`GET /dashboard` são palco; login stateless (candidato) reforça que não depende de cookie. Sem datastore, sem 2ª superfície. `redirect()` não segue nada (sem SSRF acidental).
- **Abertura seca + trilha Burp-only:** WALKTHROUGH entra direto na mecânica; **sem** encenação; **sem** seção browser. `curl -i` (sem `-L`) como equivalente. Rotular os beats: **context (definir open redirect/`next`/path vs URL absoluta/protocol-relative/`Location`)** → **spot the bug (`redirect(next)` sem validação)** → **exploitation (baseline interno → payload externo → o `Location` externo; a pegadinha `//evil.example`)** → **o que a vuln NÃO é (não é XSS/CSRF/redirect legítimo)** → **impacto (baixo isolado; elo de phishing/OAuth)** → **fixed (mesmo payload → recusa o host, cai interno; `//evil.example` também barrado)**.
- **Impacto honesto:** **baixo isolado; elo de chain** (phishing/OAuth). **Sem overclaim** (não inflar pra "account takeover" direto — a escalada é **descrita, não armada**). **Sem foreshadow.**
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é confiar no destino do usuário; **não é XSS** (nenhum script; só um `Location`), **não é CSRF** (nenhuma ação/cookie no alvo — contraste com o 23), **não é redirect legítimo** (a app não deveria mandar pra outro host).
- **Contraste (cravar):** tabela Open Redirect↔CSRF (central, com o 23 publicado); prosa com a família A01 (mesma categoria, eixo diferente). Citar publicados (A01 03/10/11/12, 23) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** open redirect, `next`/`returnUrl`, path relativo vs URL absoluta, URL protocol-relative (`//host`), header `Location`, allowlist vs blocklist, CWE (na estreia do CWE-601).
- **A01 sem arqueologia:** situar em **A01 — Broken Access Control (CWE-601)**, explicar **por que** (controle ausente sobre o destino do redirect), **sem** contar edições antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `open-redirect — Open Redirect`. "Flask"/"next"/"Werkzeug" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **23** (contraste CSRF), a família **A01 03/10/11/12** (categoria), e os recentes **22/23** (voz), todos publicados. **PROIBIDO** referenciar/foreshadowar **qualquer átomo não-publicado/categoria futura** por número, nome **ou** descrição — inclusive posição/ordinal de fase e release. **A própria spec nasce limpa** (é commitada no repo público): onde precisar situar posição, apontar pro `ROADMAP.md`; nas frases que proíbem foreshadow, manter a proibição **genérica**. O encadeamento phishing/OAuth é **descrição da classe**, não átomo futuro.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT**. Termos técnicos (open redirect, `next`, `Location`, protocol-relative, allowlist, blocklist, payload, redirect) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): **confirmar a fonte por fetch na Fase 2** (provável OWASP "Unvalidated Redirects and Forwards Cheat Sheet"; se a PortSwigger não tiver página conceitual limpa, propor OWASP e **avisar o mantenedor** — desvio consciente do "PortSwigger primeiro", justificado). Nome da página preservado em inglês no PT. **Não inventar.**
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 24: `open-redirect` — Open Redirect: after login the app redirects to a user-controlled `next` parameter with no validation, so `next=http://evil.example` (or the protocol-relative `//evil.example`) sends the victim off-site; the fix is a server-side structural allowlist that permits only internal paths (A01 Broken Access Control, CWE-601). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 24 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–9; reproduzir baseline (interno) → ataque (`Location` externo) no vulnerable → bloqueio no fixed (interno/`400`, com `//evil.example` também barrado), via Burp/`curl -i`. Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8024` (vulnerable), `127.0.0.1:8124` (fixed). Bind **só** em `127.0.0.1`. Single-container.
- Se houver dúvida sobre a fonte/URL/grafia do primer, o payload exato que sai no probe, o wiring das rotas, o pin do Flask/Werkzeug, ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos de redirect/URL-validation):

- **`open-redirect-allowlist-structure-not-blocklist`** — *"O átomo `open-redirect` (24) entra em A01 (reaproveita `atoms/A01-broken-access-control/`; CWE-601): `POST /login` bem-sucedido faz `redirect(request.form.get('next'))` sem validar o destino → `next=http://evil.example` (ou o protocol-relative `//evil.example`) manda a vítima pra fora. SINGLE-CONTAINER (vulnerable :8024 + fixed :8124), sem datastore, login stateless (o open redirect NÃO depende de cookie — contraste com o csrf-basic 23). BURP-ONLY SEM exceção de browser (diferente do 21/23): a prova é o header `Location` do 302 na resposta (curl -i sem -L). SEM Saída B, MAS o `Location` exato que o `redirect()`/Werkzeug emite pra `//evil.example` (como está vs autocorrigido) muda por versão — PROVAR por probe antes de escrever. Fix = allowlist de ESTRUTURA server-side (`safe_next` via urlparse: sem esquema/netloc/`//`, normalizar `\`→`/` ANTES do urlparse; fallback interno `/dashboard`), NÃO blocklist de string (que quebra por subdomínio `alvo.com.evil.example`, `@` userinfo, protocol-relative, backslash, encoding). Path interno basta aqui; host-allowlist só se precisasse de externos conhecidos (OAuth/SSO) — mencionado, não aplicado. Impacto baixo isolado, elo de chain (phishing/OAuth token theft) — descrito, não armado. Theory primer PENDENTE: PortSwigger não tem página conceitual limpa de open redirect (só DOM-based/OAuth) → provável OWASP 'Unvalidated Redirects and Forwards Cheat Sheet', confirmar por fetch. Só Flask==3.0.0 + stdlib urllib.parse."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão.
