# Spec — Átomo 23: `csrf-basic`

> Documento de especificação para o Claude Code implementar o átomo `csrf-basic` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A01 (Broken Access Control)**: a pasta `atoms/A01-broken-access-control/` já contém `idor-numeric-id` (03), `path-traversal-basic` (10), `idor-uuid-guessable` (11) e `bola-rest` (12). O 23 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão das irmãs, ex.: a pasta do `idor-numeric-id`). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É MULTI-CONTAINER — TRÊS serviços: `vulnerable` + `fixed` + `attacker`.** O terceiro serviço é o **site do atacante** (a origem cross-site de onde a request forjada parte). **DIVERGÊNCIA CRÍTICA do molde do `nosql-injection-mongo` (22):** lá os apps compartilhavam um **datastore** por uma rede interna; **aqui os três serviços NÃO se falam** — quem faz TODAS as requests cross-site é o **browser da vítima**. Logo **NÃO há rede interna (`networks:`), NÃO há `depends_on`, NÃO há healthcheck**: cada serviço só publica o **próprio binding no host** e é alcançado pelo browser.
>
> **A lição em uma linha:** o browser anexa os **cookies de sessão** de um site **automaticamente** em TODA request pra aquele site — não importa **quem** disparou a request. A vítima está logada no alvo (tem o cookie de sessão). O atacante, de **OUTRO site**, faz o browser da vítima disparar — escondido — uma request de **mudança-de-estado** pro alvo (um `<form>` que auto-submete). O browser **gruda o cookie da vítima** nessa request forjada, e o servidor, se só checa *"tem cookie de sessão válido?"*, executa a ação **como se a vítima tivesse pedido**. A raiz: o cookie prova **QUEM** você é, **NÃO QUE você QUIS** aquilo. O fix é um **token anti-CSRF** — um segredo por sessão que o servidor põe nos **próprios** forms e exige de volta no `POST`; o atacante, noutro site, **não consegue LER** esse token (a **Same-Origin Policy** proíbe), então não monta a request completa.
>
> **É um caso "SAÍDA B" (CRÍTICO — a vuln ingênua está mitigada por um DEFAULT moderno do browser).** Como no `14 jwt-key-confusion` (PyJWT recusa a key confusion ingênua), no `15 session-fixation` (`flask.session` resiste à fixation ingênua) e no `18 xxe-basic` (a stdlib `ElementTree` não resolve entidade externa), aqui a ferramenta padrão — **o browser** — **já mitiga** o bug ingênuo: o default **`SameSite=Lax`** faz o browser **NÃO anexar** o cookie de sessão numa `POST` cross-site. Então o CSRF clássico com cookie default **NÃO dispara**. Pra a vuln **viver de verdade**, o átomo modela as **condições reais** onde ela ainda ocorre: (a) **duas origens genuinamente cross-site**, e (b) o alvo **afrouxando** o cookie pra **`SameSite=None`** (misconfig REAL — apps embutidos cross-site, SSO/iframe, ou cargo-cult fazem isso). A Fase 2 **DEVE PROVAR por probe, num browser headless, ANTES de escrever**, que a dança inteira funciona (risco #2). **NÃO assumir; se não reproduzir sem HTTPS, PARAR e avisar** — o átomo inteiro depende disso.
>
> **DUAS DECISÕES DE PLATAFORMA FICAM ABERTAS (não são preferência editorial — são comportamento de browser que só se sabe testando).** Nesta fase de spec, o candidato está **registrado**, mas o item fica marcado **"VOCÊ DECIDE / CONFIRME NA FASE 2 — PROPOR O QUE FUNCIONAR"** (ver a seção dedicada **"Duas decisões abertas"**): **(1)** o **par de origens cross-site** (candidato: alvo `127.0.0.1`, atacante `127.0.0.2`), e **(2)** a **anticolisão de cookie** por porta (candidato: nomes de cookie distintos por alvo). **NÃO fechar agora.**
>
> **§3.3 — trilha primária Burp, MAS este átomo usa a EXCEÇÃO client-side (como o `21 xss-dom`): o BROWSER está na trilha PRINCIPAL.** O que **DEFINE** CSRF é o browser **anexar o cookie da vítima sozinho** numa request cross-site — e **curl NÃO forja isso** (você grudando o cookie à mão é só uma request autenticada normal, ver Nota de planning 3-A). O **Burp APOIA**: mostra que o `POST` não exige token nem checa Origin, e que a request forjada **carrega o cookie**. *(A razão da exceção **difere** do 21: lá o browser era a prova porque **JS executa**; aqui é porque o browser **anexa o cookie cross-site sozinho** — Nota de planning 3-A.)*
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha Burp **com a EXCEÇÃO client-side** deste átomo; §4 — pasta/categoria A01; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A01 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind loopback** e **ISOLAMENTO** dos três serviços, dados fake, payload benigno; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico de HTML/Jinja2 mínimo/estrutura), o **`xss-dom` (21)** publicado (o **molde da EXCEÇÃO de browser** e da **técnica de validação headless**; e o **CONTRASTE central** — XSS roda script DENTRO da origem do alvo e LÊ tudo; CSRF dispara de OUTRA origem e é CEGO), o **`session-fixation` (15)** publicado (contexto de **sessão/cookie** — o CSRF assume a vítima logada; e o contraste "não é bug de sessão/auth"), a família **A01** publicada (`bola-rest` 12 = molde de app com sessão/cookie e de átomo A01; `idor-numeric-id` 03, `path-traversal-basic` 10, `idor-uuid-guessable` 11 = molde de átomo A01 de lógica), e os **dois publicados mais recentes — `xss-dom` (21)** e **`nosql-injection-mongo` (22)** (a **VOZ/estrutura ATUAL**: abertura seca, termo definido, título=classe, spec nasce limpa; do 22, o **molde de compose multi-serviço** — MAS aqui **sem rede interna nem healthcheck**, ver acima).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, `attacker/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A01 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). Justificativa do ROADMAP para este átomo: *"precisa de contexto de sessão já internalizado (fase 3)."*
>
> **A categoria A01 JÁ EXISTE — o 23 reaproveita a pasta.** Diferente do `15 session-fixation` (criou `A07-*`), do `18 xxe-basic` (criou `A05-*`) e do `20 deserialization-pickle` (criou `A08-*`), o 23 **não cria categoria**: `atoms/A01-broken-access-control/` já existe e já hospeda `idor-numeric-id` (03), `path-traversal-basic` (10), `idor-uuid-guessable` (11) e `bola-rest` (12). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A01-broken-access-control/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A01-broken-access-control/csrf-basic/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A01 — Broken Access Control"**.
>
> **Rótulo A01 SEM arqueologia (`CLAUDE.md` §5, regra atual).** CSRF é **A01 — Broken Access Control** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria das irmãs IDOR/BOLA/path-traversal. **NÃO** relatar em que número/edição CSRF caía antes (era categoria própria em edições antigas; **não contar isso** — é ruído histórico proibido pela regra atual). **Situar apenas: isto é A01 — Broken Access Control.** Explicar **por que** CSRF é access control (o servidor autoriza uma ação de mudança-de-estado com base **só em QUEM** — a sessão válida — sem verificar que o usuário **QUIS** aquela ação; a decisão de acesso ignora a **intenção**) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar a versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase. **CRÍTICO (FORESHADOW, §5):** o átomo se descreve **isolado**. **NÃO** anunciar versão/release, **NÃO** dizer "abre a fase"/"terceiro da fase"/"próxima fase", **NÃO** foreshadowar átomos futuros (a posição vive só no `ROADMAP.md`). **Esta spec é commitada no repo público, então a própria spec nasce limpa**: onde precisar situar posição, aponta para o `ROADMAP.md`; nas frases que proíbem foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados). **Átomos publicados (02/08/15/21/22 e a família A01 03/10/11/12) e o `ROADMAP.md` são citáveis à vontade.**

## Nota de planning 3 — convenções ATUAIS: EXCEÇÃO client-side (browser na trilha PRINCIPAL), abertura seca, título=classe

> Seguir o `CLAUDE.md` **atual**. Pontos a fixar:
>
> - **§3.3 — EXCEÇÃO client-side: o browser é trilha PRINCIPAL (como o 21), o Burp APOIA.** CSRF é definido pelo **browser anexar o cookie de sessão da vítima automaticamente numa request cross-site**. Isso **só acontece num browser real** — daí o browser estar na trilha principal (a prova). O Burp **inspeciona e prova a rede** (que o `POST` forjado carrega o cookie e não tem token nem check de Origin) e pode **replayar** a request forjada — mas o ato **definidor** (o cookie ser anexado sozinho a partir de outra origem) é do **browser**. **Trilha principal única** (Burp + browser); **SEM** "trilha browser secundária" redundante (proibida pela §3.3 atual). *(Detalhe na Nota de planning 3-A.)*
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (troca de e-mail autenticada) e a falha (o `POST` confia só no cookie de sessão). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** CSRF, cross-site (vs cross-origin), cookie de sessão, `SameSite`, Same-Origin Policy (SOP), token anti-CSRF (synchronizer token), request de mudança-de-estado, secure context / potentially trustworthy — dar a expansão/definição na estreia. O átomo é pra quem **não** conhece a vuln.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** ("Cross-Site Request Forgery (CSRF)"), **NÃO** o stack ("...em Flask"/"...via SameSite"/"...com cookie"). O **slug** (`csrf-basic`) qualifica a variante — isso é OK (como `sqli-union-basic`). O mecanismo (`SameSite`/`SESSION_COOKIE_*`/synchronizer token) aparece no **corpo**, não no H1.
> - **A01 sem arqueologia** (Nota de planning 1).

## Nota de planning 3-A — o papel do Burp aqui DIVERGE: curl NÃO forja CSRF; o Burp APOIA/PROVA, o browser é a PROVA

> **Sinalizado — sutileza importante pra Fase 2.** Nos átomos server-side (SQLi, NoSQLi, SSTI, etc.) a trilha é Burp Repeater porque o vetor e a prova vivem na request/resposta que **você** monta. **No CSRF isso NÃO se aplica, e a razão É a própria lição:** o que caracteriza o ataque é o **browser da vítima anexar o cookie de sessão dela sozinho** numa request disparada por **outra origem**. Se você abre o Repeater, cola o cookie de sessão à mão e manda o `POST`, isso **NÃO é CSRF** — é só uma **request autenticada normal** (você já tinha o cookie; nenhuma vítima foi enganada; nenhuma origem cruzou). **curl/Repeater não conseguem reproduzir o mecanismo** porque não há vítima com um browser anexando o cookie automaticamente a partir de um site hostil.
>
> Logo o papel do Burp aqui é de **APOIO dentro da trilha principal**:
>
> 1. **INSPECIONAR** o `POST /email` do alvo na resposta/`vulnerable/app.py` — mostrar que ele checa **só** `if 'user' in session` (o cookie), **sem** token e **sem** check de Origin/Referer.
> 2. **PROVAR na rede** que a request forjada disparada pelo browser **carrega o cookie de sessão** (SameSite=None) e **não carrega token** — a foto exata de por que o servidor aceita no vulnerable e por que o fixed dá 403.
>
> Quem **planta e dispara** a request forjada é o **browser** (abrindo a página do atacante, que auto-submete o form cross-site); quem **observa** o efeito (o e-mail da conta mudar) é o **browser**. Cravar no WALKTHROUGH que **curl não é a prova aqui** (risco #6) — é o inverso didático do `nosql-injection-mongo` (22, Burp-only): lá o browser não participava; aqui o browser **é** o que reproduz a vuln. *(Registrar essa divergência explicitamente — Burp inspeciona/prova, browser reproduz.)*

## Nota de planning 4 — topologia multi-container SEM comunicação server-to-server (diverge do 22)

> **TRÊS serviços, mas eles NÃO se comunicam entre si.** O molde de "compose com 3 serviços" vem do `nosql-injection-mongo` (22), mas a semelhança **para aí**. No 22 o `mongo` era um **datastore compartilhado** que `vulnerable`/`fixed` alcançavam **por nome numa rede interna** (`mongodb://mongo:27017`), com `depends_on` e (possível) healthcheck de readiness. **Aqui não há nada disso:** o `attacker` **não** conversa com `vulnerable`/`fixed` no backend — é o **browser da vítima** que faz **todas** as requests cross-site (abre a página do atacante, e o form dela dispara o `POST` pro alvo). Os três serviços são **ilhas**; o único "cabo" entre eles é o **browser**.
>
> **Consequências (LOCKED):**
> - **SEM `networks:`** — nenhuma rede interna compartilhada. Cada serviço só precisa do próprio `ports:` no host.
> - **SEM `depends_on`, SEM healthcheck** — os serviços não dependem uns dos outros pra subir; não há readiness a esperar.
> - **Cada serviço publica o próprio binding no host** e é alcançado pelo browser via `http://<origem>:<porta>`.
> - **§8 — todos os três em loopback, local-only.** Os alvos em `127.0.0.1` (8023/8123); o atacante na origem do **item 1** (candidato `127.0.0.2:8080`). Ver "Duas decisões abertas" (item 1) e "§8 / isolamento".

---

## Duas decisões abertas — VOCÊ DECIDE / CONFIRME NA FASE 2 (PROPOR O QUE FUNCIONAR)

> Estas **NÃO** são preferências editoriais nem decisões de design a redecidir — são **comportamento de browser que só se conhece testando**. Nesta fase de spec, o **candidato está registrado**; a **validação empírica e a escolha final são da Fase 2** (probe num browser headless real, risco #2). O objetivo de cada item está **TRAVADO**; o que fica aberto é **qual valor concreto** o realiza.

### Item 1 — o PAR DE ORIGENS cross-site (objetivo TRAVADO; valor a CONFIRMAR)

**Objetivo travado:** duas origens que o browser trate como **SITES DIFERENTES** (condição cross-site, pra o `SameSite` do cookie importar), com o **`Secure`** que o `SameSite=None` exige **FUNCIONANDO sobre HTTP loopback SEM HTTPS/certificado**.

**Candidato primário (do briefing):** alvo `127.0.0.1` (`vulnerable` :8023, `fixed` :8123), atacante **`127.0.0.2`** (:8080). Raciocínio (a **confirmar** — não assumir): dois IPs distintos são **sites diferentes** (IP não tem registrable domain que os colapse), e todo `127.0.0.0/8` é **potentially trustworthy** (secure context) no Linux, então `Secure` sobre HTTP deve valer para ambos. Docker no Linux publica em `127.0.0.2` normalmente (todo `127.0.0.0/8` é loopback).

**Candidato alternativo a testar:** alvo `127.0.0.1`, atacante acessado como **`localhost`** (com o binding Docker permanecendo **`127.0.0.1:8080:5000`**, e o aluno acessando `http://localhost:8080`). Vantagem: o binding continua no **literal `127.0.0.1`** (não desvia da convenção §8 nem do parser do wrapper — ver §8/isolamento). Desvantagem: é um **footgun** — se o aluno acessar o atacante por `127.0.0.1:8080` (mesmo site do alvo) em vez de `localhost:8080`, o demo quebra; e o `./atom` imprimiria `http://127.0.0.1:8080` (a URL que **quebra** o demo).

**Trade-off a pesar na Fase 2:** o candidato primário (`127.0.0.2`) evita o footgun (o atacante simplesmente **não aparece** no `./atom`, documentado no README, como o `mongo` do 22) ao **custo** de o binding divergir do literal `127.0.0.1` (justificado no §8 — ainda é loopback). O alternativo (`localhost`) honra o literal `127.0.0.1` mas cria a URL-armadilha.

**O que a Fase 2 tem que PROVAR (risco #2), rodando num browser headless real:** (a) o par escolhido é **cross-site**; (b) o alvo **SETA** o cookie `SameSite=None; Secure` sobre HTTP loopback; (c) uma `POST` cross-site da origem do atacante **CARREGA** esse cookie pro alvo. **PROPOR o par que funcionar.** **Se NENHUM par loopback simples funcionar sem HTTPS, PARAR e avisar o mantenedor** — o átomo inteiro depende disso.

### Item 2 — a ANTICOLISÃO de cookie por porta (config de SEGURANÇA TRAVADA; a plumbing a CONFIRMAR)

**O problema (plumbing de lab, NÃO de segurança):** cookie **não distingue porta**. Os dois alvos moram no **mesmo host** `127.0.0.1` (só a porta difere: 8023 vs 8123), então um cookie setado por `127.0.0.1:8023` também é **enviado** pra `127.0.0.1:8123` — `vulnerable` e `fixed` **colidiriam** de cookie/login (logar num "contamina" o outro; e a request forjada pro fixed poderia carregar o cookie do vulnerable).

**Candidato de solução (do briefing):** **nomes de cookie de sessão distintos por alvo** — `session_vuln` no `vulnerable`, `session_fixed` no `fixed` (Flask: `SESSION_COOKIE_NAME`). Assim cada app lê **só** o próprio cookie; não colidem.

**Latitude (é decisão de IMPLEMENTAÇÃO, não de design):** se ao validar você achar uma abordagem **mais limpa**, **PROPOR antes de aplicar** — **desde que** (i) a **config de SEGURANÇA do cookie** (`SameSite=None; Secure`) permaneça **IDÊNTICA** entre os dois lados, e (ii) o **token anti-CSRF siga sendo o ÚNICO delta de segurança** entre `vulnerable` e `fixed`. *(Separar alvos por host distinto — ex.: fixed em `127.0.0.3` — resolveria a colisão, mas DIVERGE das portas TRAVADAS `127.0.0.1:8023`/`127.0.0.1:8123` e não é preferido.)*

---

## Identidade

- **ID:** `csrf-basic`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A01 — Broken Access Control**. Pasta `atoms/A01-broken-access-control/` (**JÁ EXISTE — o 23 reaproveita**). Confirmado contra o `ROADMAP.md` ("A01 Broken Access Control") e o `CLAUDE.md` §4. Em prosa, usar o nome da classe — **"Cross-Site Request Forgery (CSRF)"** — e a categoria — **"A01 — Broken Access Control"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A01-broken-access-control/csrf-basic/`
- **Número sequencial:** 23
- **Porta `vulnerable`:** `127.0.0.1:8023` (TRAVADO)
- **Porta `fixed`:** `127.0.0.1:8123` (TRAVADO)
- **Origem do `attacker`:** a CONFIRMAR — **item 1** (candidato `127.0.0.2:8080`).
- **Bind:** **loopback** em todo `docker-compose.yml` (`CLAUDE.md` §8.1). Os alvos **só** em `127.0.0.1`. O atacante na origem do item 1 (também loopback — todo `127.0.0.0/8` é local-only). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a loopback pelo compose — mesmo padrão dos irmãos. Ver "§8 / isolamento" para a justificativa de desvio do literal `127.0.0.1` (item 1).
- **Topologia:** **MULTI-CONTAINER — TRÊS serviços:** `vulnerable` + `fixed` + `attacker`. **Eles NÃO se comunicam server-to-server** (o browser media todas as requests cross-site) → **SEM rede interna, SEM `depends_on`, SEM healthcheck** (Nota de planning 4). Cada serviço só publica o próprio binding no host.
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos** (§5 foreshadow).
- **Branch de trabalho:** `atom/csrf-basic`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de CSRF** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/csrf`** (título/grafia esperados: **"Cross-site request forgery (CSRF)"**). **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# csrf-basic — Cross-Site Request Forgery (CSRF)`** — `id` + nome canônico da **classe** em inglês (forma paralela às irmãs: `12` usa "Broken Object Level Authorization (BOLA)", `21` usa "DOM-based Cross-Site Scripting"). **SEM** "Flask"/"SameSite"/"cookie" no H1 (o slug já carrega "basic"). Grafia canônica exata **confirmável na Fase 2** (casar com o título da página PortSwigger); **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**Cross-Site Request Forgery (CSRF) — o servidor confia no cookie como prova de INTENÇÃO.** Uma app com login e uma ação autenticada de **mudança-de-estado** (uma request que **altera** algo no servidor — aqui, trocar o e-mail da conta). O servidor identifica a sessão por um **cookie de sessão** (um valor que o browser guarda para aquele site e **reenvia automaticamente** em toda request pra ele). O endpoint da ação (`POST /email`) checa **só** *"existe um cookie de sessão válido?"* — ou seja, **QUEM** está pedindo — e executa.

O atacante, hospedado em **outro site** (uma origem cross-site — um site diferente do alvo), serve uma página com um `<form>` que **auto-submete** um `POST /email` pro alvo, com o e-mail dele. A vítima — **logada no alvo** — abre a página do atacante; o browser dela, obedecendo a regra de "reenviar o cookie do alvo em toda request pro alvo", **anexa o cookie de sessão da vítima** na request forjada. O servidor vê um cookie válido e **troca o e-mail** — **como se a vítima tivesse pedido**. A vítima nunca pediu; o atacante nunca soube a senha nem leu o cookie. O erro é o servidor tratar **"tem cookie de sessão"** como **"o usuário QUIS esta ação"**.

### A lição-coração

> **"O browser anexa os cookies de um site AUTOMATICAMENTE em toda request pra aquele site, não importa QUEM disparou a request. A vítima está logada no alvo (tem o cookie de sessão). O atacante, de OUTRO site, faz o browser da vítima disparar — escondido — uma request de mudança-de-estado pro alvo (um `<form>` que auto-submete). O browser gruda o cookie da vítima nessa request forjada, e o servidor, se só checa 'tem cookie de sessão válido?', executa a ação como se a vítima tivesse pedido. A raiz: o cookie prova QUEM você é, NÃO QUE você QUIS aquilo. O fix é um token anti-CSRF — um segredo por sessão que o servidor põe nos PRÓPRIOS forms e exige de volta no POST; o atacante, noutro site, não consegue LER esse token (a Same-Origin Policy proíbe), então não monta a request completa."**

### Sub-lição CRÍTICA — DUAS CAMADAS de defesa: `SameSite` (nível-COOKIE, do browser) vs token (nível-APLICAÇÃO)

Cravar (é o coração da sub-lição e da nota #1 do DIFF): **CSRF tem defesa em duas camadas distintas, e o átomo mostra as duas.**

- **`SameSite` — nível-COOKIE, imposto pelo BROWSER.** `SameSite` é um atributo do cookie que diz ao **browser** quando anexar o cookie em requests cross-site. O default moderno **`SameSite=Lax`** faz o browser **NÃO** anexar o cookie de sessão numa `POST` cross-site — o que **sozinho já bloqueia o CSRF ingênuo** (por isso este átomo é "Saída B" — ver adiante). Este app **DESLIGOU** essa proteção pondo **`SameSite=None`** (dizendo ao browser "anexe o cookie mesmo cross-site"). Essa é a **condição** que faz a vuln reviver.
- **Token anti-CSRF — nível-APLICAÇÃO, imposto pelo SERVIDOR.** O **fix** deste átomo é o **synchronizer token pattern**: o servidor gera um segredo por sessão, embute nos **próprios** forms, e **exige de volta** no `POST`. Ele verifica **INTENÇÃO** (só quem viu o form do próprio site tem o token), **independe do transporte e do browser**, e funciona **mesmo com o cookie afrouxado pra `SameSite=None`** — porque o atacante, noutra origem, **não consegue LER** o token (a SOP proíbe ler a resposta cross-origin), então não monta a request completa, ainda que o cookie viaje junto.

**O ponto:** o átomo mantém o `SameSite=None` (a camada-cookie desligada) **idêntico nos dois lados** e aplica **só o token** no fixed — isolando que **a correção é o TOKEN**, não "religar o `SameSite` pra `Lax`". As duas camadas são defesas **reais e somáveis** (defense-in-depth) — o DIFF nomeia ambas (nota #1) —, mas o átomo aplica o token porque é o **portável** e o que **verifica intenção**.

### Por que A01 (Broken Access Control)

CSRF é **A01 — Broken Access Control**. A01 é, no fundo, o servidor **permitir uma ação fora do que o usuário deveria poder disparar naquele contexto**. Nas irmãs IDOR/BOLA (03/11/12) a falha é a **ausência de um check de autorização** sobre um objeto — o atacante usa a **própria** identidade pra alcançar o objeto de **outro** user. No CSRF o check de autenticação até **passa** (a vítima **está** logada, o cookie **é** válido) — o buraco é que o servidor decide executar uma ação de **mudança-de-estado** com base **só em QUEM** (a sessão), **sem verificar que o usuário QUIS aquela ação**. É uma falha de controle de acesso no eixo da **intenção**: a request atravessa a fronteira de "o que este site deveria poder mandar o usuário fazer noutro site". Situar em **A01 — Broken Access Control**, explicar o **porquê** (autorizar mudança-de-estado por identidade, ignorando intenção), **sem** contar edições antigas.

---

## SAÍDA B — a vuln ingênua está mitigada por um DEFAULT do browser (TRAVADO; crítico)

Este é o eixo que **não pode enfraquecer**. O CSRF "de livro" (um cookie de sessão comum, uma `POST` forjada de qualquer site) **NÃO dispara mais** num browser moderno, porque o default **`SameSite=Lax`** faz o browser **não anexar** o cookie de sessão numa `POST` cross-site. Se o átomo modelasse o caso ingênuo, o aluno veria o ataque **falhar** e concluiria — errado — que "CSRF não existe mais" ou que "o Flask já protege".

Pra a vuln **viver de verdade**, o átomo modela as **condições reais** onde o CSRF ainda ocorre (e ocorre — em apps embutidos cross-site, fluxos SSO/iframe, APIs consumidas de outra origem, ou config cargo-cult que afrouxa o cookie sem entender):

1. **Duas origens genuinamente cross-site** (item 1) — pra a request ser de fato cross-site e o `SameSite` importar.
2. **O alvo afrouxa o cookie pra `SameSite=None; Secure`** (misconfig REAL) — dizendo ao browser "anexe meu cookie mesmo em request cross-site". É o que reabre a porta.

**Paralelo honesto com o arco (citável — são publicados):** como no `14 jwt-key-confusion` (a lib padrão recusava o ataque ingênuo), no `15 session-fixation` (`flask.session` resistia à fixation ingênua) e no `18 xxe-basic` (a stdlib não resolvia entidade externa), aqui a **ferramenta padrão** (o browser, com `SameSite=Lax`) **já mitiga** o bug ingênuo, e o átomo **modela o componente/config onde a vuln realmente vive**. **NÃO** é "uso-direto-do-antipadrão" (como o `19`/`20`/`21`/`22`) — há a ruga do default que resiste.

**A Fase 2 DEVE PROVAR a dança inteira por probe, num browser headless real, ANTES de escrever** (risco #2): o par de origens é cross-site (item 1), o alvo seta `SameSite=None; Secure` sobre HTTP loopback, e a `POST` cross-site **carrega** o cookie. **Não assumir.** Se não reproduzir sem HTTPS, **PARAR e avisar** — o átomo depende disso.

---

## Contraste — com XSS (02/08/21), com session-fixation (15) e com a família A01 (03/10/11/12)

O que justifica o átomo e ancora o passo "o que a vuln NÃO é". Cravar no WALKTHROUGH e no DIFF:

### Contraste CENTRAL — CSRF vs XSS (o mal-entendido nº 1: "cross-site" ≠ "cross-site scripting")

| Eixo | **XSS** (`02` reflected / `08` stored / `21` DOM) | **CSRF** (`23`) |
|---|---|---|
| **Onde o código roda** | script do atacante executa **DENTRO da origem do alvo** | **nenhum** código do atacante roda no alvo; o `<form>` roda na origem **do atacante** |
| **O atacante LÊ a resposta do alvo?** | **SIM** — mesmo-origem: lê cookies, DOM, corpo, tudo | **NÃO** — a **SOP** proíbe ler a resposta cross-origin; o ataque é **CEGO** |
| **O que o atacante consegue** | ler **e** escrever no contexto do alvo (roubo de sessão, exfil) | só **disparar** uma ação de mudança-de-estado (fire-and-forget) |
| **Precisa da vítima logada?** | não necessariamente | **SIM** — o ataque explora o cookie **da sessão da vítima** |
| **Categoria OWASP** | A03 — Injection | A01 — Broken Access Control |

**A frase-regra:** *XSS roda DENTRO do alvo e LÊ tudo; CSRF dispara de FORA e é CEGO.* Confundir os dois leva o aluno a "explicar" CSRF como "o atacante rouba o cookie" ou "lê a resposta" — **nada disso**: no CSRF o atacante **nunca** toca o cookie nem lê a resposta; ele só faz o **browser da vítima** disparar a ação, às cegas. Usar o `xss-dom` (21, publicado) como âncora: lá o JS do atacante roda no contexto do alvo e lê o DOM; aqui **não há** código no alvo, e a SOP **cega** o atacante.

### Contraste com `session-fixation` (15) — não é bug de sessão/auth

O `15` (publicado) é sobre o **ciclo de vida** da sessão (o servidor não regenera o session id no login) — o atacante acaba **DENTRO** da sessão da vítima. No CSRF a sessão é **perfeitamente válida e íntegra**; o atacante **nunca** entra nela nem lê nada dela — ele só a **usa como carona** (o cookie viaja sozinho) pra disparar **uma** ação. **Não é** login bypass, **não é** sequestro de sessão, **não é** id previsível. A sessão está certa; o buraco é a **intenção**.

### Contraste com a família A01 (03/10/11/12) — mesma categoria, eixo diferente

IDOR/BOLA (03/11/12): **ausência** de check de autorização; o atacante usa a **própria** identidade pra ler o objeto de **outro**. `path-traversal-basic` (10): o atacante sai do diretório permitido. No CSRF o check de autenticação **passa** (a vítima está logada) — o que falta é verificar a **intenção** de uma ação de mudança-de-estado. Mesma categoria A01 (o servidor executa algo que não deveria naquele contexto), **eixo distinto** (intenção, não ausência de check nem escopo de path). Citar a família (publicada) pra ancorar "por que A01".

---

## Flavor — troca de e-mail (`POST /email`) — TRAVADO

Cenário canônico de CSRF: **troca de e-mail da conta → account takeover via reset de senha.** O alvo (`vulnerable` e `fixed`) tem:

- **`POST /login`** — estabelece a sessão da vítima (usuário fake semeado; qualquer credencial demo correta loga). Define `session["user"]`.
- **`GET /`** — se não logado, mostra um **form de login** mínimo; se logado, mostra a **conta** (o e-mail atual, pra observar a mudança) e o **form LEGÍTIMO de troca de e-mail**. No `vulnerable`, o form **NÃO tem token**; no `fixed`, tem um **hidden field** com o token anti-CSRF.
- **`POST /email`** — troca o e-mail da conta. **É A ÚNICA VULN.** O `vulnerable` checa **só** o cookie de sessão; o `fixed` valida o **token** antes da ação.

**Estado da conta EM MEMÓRIA (SEM datastore).** CSRF não precisa de banco — um `dict`/variável do módulo pro user demo basta (`ACCOUNT = {"email": ...}`). A mudança de e-mail muta esse estado server-side; o `GET /` o exibe (a prova).

**O site do ATACANTE** serve uma página HTML maliciosa com um `<form>` que **auto-submete** um `POST /email` cross-site pro alvo. Deve permitir demonstrar **tanto o sucesso** contra o `vulnerable` (:8023) **quanto o 403** contra o `fixed` (:8123) — candidato: **duas rotas/páginas** (`/attack-vuln` e `/attack-fixed`), cada uma apontando o `action` do form pro alvo respectivo. **O atacante NÃO tem vuln própria** — é só o palco de onde a request cross-site parte.

**Superfície = `POST /email` confiando no cookie como prova de intenção.** `GET /` e `POST /login` **não são a vuln**. Uma única ação injetável; **sem** segunda superfície.

---

## Payload-prova — ACCOUNT TAKEOVER (TRAVADO; §8)

A página do atacante auto-submete uma `POST /email` cross-site pro alvo, trocando o e-mail da conta pra um valor **benigno controlado pelo atacante** (candidato: **`attacker@evil.example`** — `.example` é TLD reservado, dado fake, §8).

- **No `vulnerable` (:8023):** a request forjada carrega o cookie de sessão (SameSite=None) → o servidor checa só o cookie → **o e-mail da conta MUDA** → **account takeover** (o atacante agora controla o e-mail de recuperação; um "esqueci a senha" mandaria o reset pra ele). **A prova é o E-MAIL DA CONTA MUDAR.**
- **No `fixed` (:8123):** a **MESMA** request forjada → **403**. **O mecanismo-chave a cravar:** a request forjada **CARREGA o cookie de sessão** (SameSite=None — ele viaja igual), mas **FALHA MESMO ASSIM** — porque o token tem que vir no **CORPO** da request (algo que o atacante precisa **SUPRIR ativamente** e **NÃO consegue LER** via SOP). **O cookie viajar junto NÃO basta.**

**Impacto honesto (sem overclaim):** account takeover via troca de e-mail forçada (→ reset de senha). O lab **não implementa** o reset (seria segunda feature) — o WALKTHROUGH **descreve** a cadeia (e-mail trocado → reset pro atacante); a **prova** é a mudança do e-mail. §8: valor benigno, dados fake, tudo loopback, nada destrutivo.

---

## O código — o coração no `POST /email` do `app.py`

O fix é **SERVER-SIDE** (no `app.py` do alvo), como no SQLi/NoSQLi. O `app.py` dos alvos **DIFERE** entre `vulnerable` e `fixed`; o **único delta de segurança é o token**. A config de cookie (`SameSite=None; Secure`) é **idêntica** nos dois (só o **nome** difere — plumbing do item 2). O `attacker/app.py` é o mesmo palco nos dois cenários.

### `vulnerable/app.py` — o `POST /email` checa SÓ o cookie de sessão (candidato — Fase 2 gera o real)

```python
import os
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "changeme-vuln"  # dummy dev-only key (CLAUDE.md §8.3)

# Cookie config. SameSite=None deliberately relaxes the browser-level protection
# (the default Lax would block the cross-site POST): this is the misconfig that
# makes CSRF fire. Secure works over plain HTTP because 127.0.0.1 is a secure
# context (loopback). This block is IDENTICAL in fixed -- only the NAME differs
# (item 2 plumbing, so vuln:8023 and fixed:8123 on 127.0.0.1 don't share a cookie).
app.config.update(
    SESSION_COOKIE_NAME="session_vuln",
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# Single demo user's account state, in memory -- no datastore needed for CSRF.
ACCOUNT = {"email": "demo@example.com"}


@app.route("/login", methods=["POST"])
def login():
    if request.form.get("username") == "demo" and request.form.get("password") == "demo":
        session["user"] = "demo"
    return redirect("/")


@app.route("/")
def index():
    if "user" not in session:
        return render_template("login.html")
    return render_template("account.html", email=ACCOUNT["email"])


@app.route("/email", methods=["POST"])
def change_email():
    # VULNERABLE: the ONLY check is "is there a valid session cookie?" -- i.e. WHO you
    # are. It never verifies the authenticated user INTENDED this request: no anti-CSRF
    # token, no Origin/Referer check. The browser attaches the session cookie
    # automatically on any request to this site, so a POST forged from another origin
    # sails through as if the user had asked for it.
    if "user" not in session:
        return "Not logged in", 403
    ACCOUNT["email"] = request.form.get("email", "")
    return redirect("/")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — MESMO código, com o synchronizer token à mão (candidato)

```python
import os
import secrets
from flask import Flask, render_template, request, redirect, session, abort

app = Flask(__name__)
app.secret_key = "changeme-fixed"  # dummy dev-only key

# IDENTICAL security config to vulnerable (SameSite=None; Secure) -- the token is the
# ONLY security delta. Only the cookie NAME differs (item 2 plumbing).
app.config.update(
    SESSION_COOKIE_NAME="session_fixed",
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

ACCOUNT = {"email": "demo@example.com"}


def csrf_token():
    # One secret per session (synchronizer token), stored server-side in the session.
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.route("/login", methods=["POST"])
def login():
    if request.form.get("username") == "demo" and request.form.get("password") == "demo":
        session["user"] = "demo"
    return redirect("/")


@app.route("/")
def index():
    if "user" not in session:
        return render_template("login.html")
    # Embed the per-session token as a hidden field in THIS server's own form.
    return render_template("account.html", email=ACCOUNT["email"], csrf_token=csrf_token())


@app.route("/email", methods=["POST"])
def change_email():
    if "user" not in session:
        return "Not logged in", 403
    # FIXED: verify INTENT with the anti-CSRF token. It was put into this server's form
    # and must come back in the request BODY. An attacker on another origin cannot READ
    # it (the Same-Origin Policy forbids reading our response), so cannot supply it --
    # even though the browser still attaches the session cookie to the forged POST.
    token = session.get("csrf_token")
    if not token or request.form.get("csrf_token") != token:
        abort(403)
    ACCOUNT["email"] = request.form.get("email", "")
    return redirect("/")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `attacker/app.py` — o palco cross-site, SEM vuln própria (candidato)

```python
import os
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")  # links to the two attack pages


@app.route("/attack-vuln")
def attack_vuln():
    return render_template("attack.html", target="http://127.0.0.1:8023/email")


@app.route("/attack-fixed")
def attack_fixed():
    return render_template("attack.html", target="http://127.0.0.1:8123/email")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### Notas de implementação (validar/decidir na Fase 2)

- **Sessão via `flask.session` (candidato).** O cookie de sessão assinado do Flask basta (guarda `user` e, no fixed, `csrf_token`). O estado da conta (`ACCOUNT["email"]`) é **module-level** (server-side), **não** na sessão — pra a mudança persistir e ser observável. Não é preciso store server-side de sessão (o átomo não é sobre o ciclo da sessão — isso é o `15`).
- **O `POST /email` lê `request.form` (form-urlencoded), NÃO JSON.** O CSRF clássico usa um `<form>` HTML, cujo `POST` é `application/x-www-form-urlencoded` — uma "simple request" que **não dispara preflight CORS** e portanto **é enviada cross-origin com o cookie**. Um `fetch` com JSON dispararia preflight (outra história/vuln). **Confirmar na Fase 2** que a stack (form → `request.form`) reproduz o ataque.
- **Token no `session` (fixed): o cookie carrega a cópia de referência.** O token vive no cookie de sessão assinado — que **viaja** na request forjada (SameSite=None). Por isso o check compara o token do **corpo** (`request.form`) contra o do **cookie** (`session`): a metade que o atacante **não consegue suprir** é a do corpo (ele não leu o form — SOP). O guard `if not token or ...` rejeita quando não há token na sessão (defensivo). **Confirmar o ciclo do token na Fase 2** (a vítima vê o form em `GET /` antes do fluxo legítimo, então o token existe).
- **Auto-submit da página do atacante** (candidato): `<body onload="document.forms[0].submit()">` — JS mínimo de plumbing (não é a vuln; é a entrega, como um CSRF PoC real). **JS permitido só pra isso**, no mínimo absoluto (§3.3 — não é a superfície causal; a causa é server-side no `POST /email`).
- **Banner de aviso (§8) em TODA página HTML** — inclusive as do atacante (a página flasha antes do auto-submit, mas o banner fica). Confirmar na Fase 2.

---

## O fix e o tipo de diff

**Fix:** **synchronizer token pattern à mão**, server-side — `secrets.token_urlsafe` gerado por sessão, embutido como **hidden field** no form do próprio alvo (`GET /`), e **validado** no `POST /email` (`request.form.get("csrf_token") == session.get("csrf_token")` → **403** se faltar/não bater, **ANTES** da ação). **SEM Flask-WTF** — mostrar o mecanismo cru, sem dependência (ethos do repo, como o HMAC à mão do `20`). Tipo de diff: **lógica-diferente** — a lógica do token no `app.py` (gerar + embed + validar) mais o hidden field no template.

**Config de cookie IDÊNTICA nos dois lados** (`SameSite=None; Secure`; só o **nome** difere — plumbing do item 2). O **ÚNICO delta de SEGURANÇA é o token** — isolando que a correção é o **TOKEN**, não "religar o `SameSite` pra `Lax`".

Diff colável (candidato — a Fase 2 gera o real; recortes do `app.py`):

```diff
+import secrets
 from flask import Flask, render_template, request, redirect, session
+from flask import abort
 ...
+def csrf_token():
+    if "csrf_token" not in session:
+        session["csrf_token"] = secrets.token_urlsafe(32)
+    return session["csrf_token"]
+
 @app.route("/")
 def index():
     if "user" not in session:
         return render_template("login.html")
-    return render_template("account.html", email=ACCOUNT["email"])
+    return render_template("account.html", email=ACCOUNT["email"], csrf_token=csrf_token())

 @app.route("/email", methods=["POST"])
 def change_email():
     if "user" not in session:
         return "Not logged in", 403
+    token = session.get("csrf_token")
+    if not token or request.form.get("csrf_token") != token:
+        abort(403)
     ACCOUNT["email"] = request.form.get("email", "")
     return redirect("/")
```

(No template: o `fixed/templates/account.html` ganha `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">` dentro do form; o resto do HTML e o `login.html` são idênticos.)

### Notas obrigatórias no `DIFF.md`

1. **OS TRÊS FIXES LEGÍTIMOS — a paisagem HONESTA (CRÍTICO; é a distinção que esta nota deve deixar explícita).** *(Contraste explícito com a nota "mencionável, não aplicada" dos átomos anteriores — `19` sandbox, `20` HMAC/assinatura, `21` escape-no-servidor/CSP —, que nomeava uma defesa **ERRADA/remendo**. **Aqui NÃO é "um fix certo + armadilhas": os TRÊS são legítimos**, em camadas diferentes.)* Nomear os três, **uma linha cada**, com honestidade:
   - **TOKEN anti-CSRF (synchronizer)** — nível-**APLICAÇÃO**. É o que **APLICAMOS**. Verifica **INTENÇÃO**; o atacante não lê o token (SOP), então não monta a request; funciona em **qualquer browser**, independe de transporte.
   - **`SameSite=Lax`/`Strict`** — nível-**COOKIE**. É o **DEFAULT** que este app **desligou**. Manda o browser **NÃO** anexar o cookie em request cross-site. Defense-in-depth **REAL** (não remendo), mas **depende do browser** e alguns fluxos legítimos precisam afrouxar pra `None` — e aí some.
   - **Checagem de Origin/Referer** — nível-**SERVIDOR**. O servidor confere se a request veio da própria origem. Alternativa **válida e barata**, mas depende de os headers estarem **presentes/confiáveis** (proxies/privacidade às vezes removem) — costuma ser **COMPLEMENTO**.
   - **Fechar:** CSRF tem **três controles legítimos em camadas diferentes**; o átomo aplica o **token** porque é o **portável** e o que **verifica intenção**, e nomeia os outros dois como defesas reais que se **SOMAM** (defense-in-depth).
2. **O TOKEN VAI NA REQUEST, NÃO (só) NO COOKIE — o cerne.** O cookie de sessão **VIAJA junto** na request forjada (`SameSite=None`), então **"ter o cookie" não pode ser a checagem**. O token funciona porque precisa ser **SUPRIDO ativamente no corpo** (ou header) — algo que o atacante **não consegue LER** (SOP proíbe ler a resposta/form cross-origin) e portanto **não inclui**. **Cravar:** a defesa é exigir **algo que o atacante teria que LER**, não algo que o **browser manda sozinho**. *(Sutileza a explicar: no fixed o token também mora no cookie de sessão — que viaja —, mas o check compara o token do CORPO contra o do cookie; a metade impossível pro atacante é a do corpo.)*
3. **IMPACTO: account takeover (troca de e-mail → reset de senha). CONTRASTE: NÃO é XSS.** O impacto é subverter uma ação de mudança-de-estado sem o consentimento da vítima → **account takeover**. **Cravar o contraste com XSS** (tabela da seção "Contraste"): XSS roda **dentro** da origem do alvo e **LÊ** tudo; CSRF dispara de **fora** e é **CEGO** (a SOP proíbe ler a resposta cross-origin). O atacante **nunca** lê o cookie nem a resposta — só **dispara** a ação. **Sem overclaim** (não é leitura de dado, não é comprometimento do servidor). **Sem foreshadow.**

---

## Biblioteca / topologia

- **Alvos (`vulnerable`/`fixed`):** **Flask + stdlib** (`secrets` pro token). `requirements.txt`: **só Flask** (pin candidato **`Flask==3.0.0`** — casando com os irmãos; **confirmar** que instala em `python:3.11-slim` por probe na Fase 2). **SEM datastore** — estado da conta em memória.
- **Atacante:** **Flask mínimo** servindo a(s) página(s) maliciosa(s). **Sem vuln própria**, sem dependência extra.
- **TRÊS Dockerfiles** (`vulnerable`, `fixed`, `attacker`), molde dos irmãos (**com** `COPY templates`). `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé; `ENV HOST=0.0.0.0` no Dockerfile (forwarding do Docker), exposição host restrita a loopback pelo compose.

**`docker-compose.yml`** (candidato — 3 serviços; **SEM rede interna, SEM `depends_on`, SEM healthcheck**; a Fase 2 gera o real e confirma o item 1):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8023:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8123:5000"
  attacker:
    build: ./attacker
    ports:
      - "127.0.0.2:8080:5000"   # item 1 (candidato A). Candidato B: "127.0.0.1:8080:5000" acessado como http://localhost:8080
```

- **Sem `networks:`, sem `depends_on`, sem healthcheck** — os três serviços **não se falam** (Nota de planning 4). O browser media todas as requests cross-site.
- **§8:** todos os bindings em **loopback**. Alvos **só** em `127.0.0.1`. Atacante na origem do item 1 (candidato `127.0.0.2` — ainda loopback; ver "§8 / isolamento").

---

## §8 / isolamento — os três serviços em loopback; a justificativa de desvio do literal `127.0.0.1`

- **Alvos:** `127.0.0.1:8023` (vulnerable) e `127.0.0.1:8123` (fixed) — literal `127.0.0.1`, sem desvio.
- **Atacante (item 1, candidato A — `127.0.0.2:8080`):** **JUSTIFICATIVA DE DESVIO do literal `127.0.0.1` (§8).** Qualquer `127.x.x.x` está em **`127.0.0.0/8`**, que é **loopback** — **local-only, inacessível de fora da máquina** (não roteável na rede). Bindar o atacante em `127.0.0.2` **honra o espírito do §8** (nada exposto à rede/internet) mesmo divergindo do **literal** `127.0.0.1`. **CONFIRMAR na Fase 2** que a origem escolhida do atacante **não é alcançável de fora** (é loopback) e que o Docker no host de validação (Fedora/Linux) publica em `127.0.0.2` (todo `127.0.0.0/8` é loopback no Linux por default).
- **O atacante pode NÃO aparecer no wrapper `./atom` (registrar).** O `parse_ports` do wrapper casa **só** o literal `127\.0\.0\.1` (regex em `atom`, `port_pat`). Com o candidato A (`127.0.0.2`), o atacante **não é listado** por `./atom up csrf-basic` — como o `mongo` do `22` (que não tinha porta no host). **Documentar a URL do atacante no README/WALKTHROUGH.** *(Com o candidato B — binding literal `127.0.0.1:8080` acessado como `localhost` — o wrapper listaria `http://127.0.0.1:8080`, que é a URL que QUEBRA o demo; ver o trade-off no item 1.)*
- **CI linter de port-binding (ROADMAP, ainda não existe) — flag pro mantenedor.** O linter planejado valida `ports:` em `127.0.0.1`. Um binding em `127.0.0.2` (candidato A) exigiria o linter aceitar `127.0.0.0/8` **ou** tratar este átomo como **desvio documentado**. Não é bloqueante agora (o linter não existe), mas **registrar** pro mantenedor decidir junto com o item 1.

---

## WALKTHROUGH — abertura seca; browser na trilha PRINCIPAL (§3.3 EXCEÇÃO client-side)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (troca de e-mail autenticada) e a falha (o `POST /email` confia só no cookie de sessão como prova de intenção). Trilha **principal única**: **browser + Burp juntos** — o **browser** reproduz o ataque (loga no alvo → abre a página do atacante → o form auto-submete → o browser anexa o cookie → e-mail trocado); o **Burp APOIA** (mostra que o `POST` forjado carrega o cookie e não tem token; que o endpoint não checa Origin). **NÃO** criar uma "trilha browser secundária" (proibida pela §3.3 atual).

**Abertura (candidato — plantar a lição, seco):**

> *A app tem uma conta com um e-mail e um form pra trocá-lo: você está logado, preenche o novo e-mail, e o `POST /email` atualiza a conta. O servidor sabe que é você porque o browser mandou o **cookie de sessão** — o valor que ele guardou no seu login e **reenvia sozinho** em toda request pra este site. O problema: o browser reenvia esse cookie **não importa quem disparou a request**. Um site do atacante pode ter um `<form>` escondido que dispara, do browser da **vítima**, um `POST /email` pra este alvo — e o browser vai **grudar o cookie de sessão da vítima** nessa request forjada. O servidor vê um cookie válido e troca o e-mail, **como se a vítima tivesse pedido**. Ela nunca pediu; o atacante nunca soube a senha.*

Beats (molde do 21/22 publicado — abertura seca, seções numeradas `## 1..7`):

1. **Context.** Feature: troca de e-mail autenticada. Definir na estreia: **CSRF** (Cross-Site Request Forgery — forçar o browser da vítima a disparar uma request de mudança-de-estado pra um site onde ela está logada), **cross-site** (uma origem/site diferente do alvo; distinguir de cross-**origin** se útil), **cookie de sessão** (o valor que o browser reenvia automaticamente pra o site), **`SameSite`** (o atributo que diz ao browser quando anexar o cookie cross-site; default `Lax`), **request de mudança-de-estado** (uma que **altera** algo no servidor), **Same-Origin Policy (SOP)** (a regra que impede uma origem de **ler** a resposta de outra), **token anti-CSRF / synchronizer token** (o segredo por sessão que o servidor exige de volta). Isto é **CSRF**, sob **A01 — Broken Access Control**. Topologia: `vulnerable` (:8023), `fixed` (:8123), e o **site do atacante** (origem do item 1); as duas **origens cross-site** e o cookie **`SameSite=None`** (a condição que faz a vuln viver — Saída B). Trilha: browser (reproduz) + Burp (apoia/prova a rede).
2. **Spot the bug.** Mostrar o `POST /email` do `vulnerable/app.py` — o check é **só** `if "user" in session` (o cookie). Pergunta de auditoria: *"esse endpoint muda estado e só confere QUEM está logado — ele confere que o usuário QUIS esta request específica? Tem token? Checa Origin?"* → **não**. Foreshadow do fix: exigir um segredo que **só quem viu o form do próprio site** teria.
3. **Exploitation (browser reproduz; a prova é o e-mail mudar).**
   - **Baseline (feature benigna):** logar no alvo (`POST /login`), abrir `GET /` — a conta mostra `demo@example.com` e o form legítimo. Trocar o e-mail pelo form normal funciona (é o uso legítimo). *(No Burp: notar o cookie de sessão sendo setado no login — `SameSite=None; Secure`.)*
   - **Montar a página do atacante:** um `<form action="http://127.0.0.1:8023/email" method="POST">` com `<input type="hidden" name="email" value="attacker@evil.example">` e auto-submit no load. Explicar por que **form** (e não `fetch`/JSON): o `POST` de form é "simple request", vai cross-origin **com o cookie**, sem preflight CORS.
   - **Disparar:** com a vítima **logada** no alvo, abrir a página do atacante (origem do item 1) → o form **auto-submete** → o browser dispara o `POST /email` pro alvo e **anexa o cookie de sessão da vítima** → recarregar `GET /` no alvo mostra o e-mail agora **`attacker@evil.example`** → **account takeover**.
   - **§8 (cravar):** lab **isolado** (tudo loopback); e-mail **benigno** (`.example`), dado fake, nada destrutivo.
4. **O papel do BURP (APOIO dentro da trilha principal — inspecionar e PROVAR a rede; Nota de planning 3-A).**
   - **Inspecionar o endpoint:** ler no `POST /email` que só há o check do cookie — **sem token, sem Origin check**.
   - **PROVAR na rede:** no HTTP history, a request forjada disparada pelo browser **carrega o cookie de sessão** (`Cookie: session_vuln=...`) e **não tem** campo de token. Essa é a foto de por que o servidor aceita.
   - **Cravar que curl NÃO é a prova (risco #6):** se você colar o cookie à mão num `POST` do Repeater/curl, isso é só uma **request autenticada normal** — não houve vítima nem origem cruzada. **O que caracteriza CSRF é o browser anexar o cookie sozinho a partir do site do atacante** — por isso a prova é **browser-mediada**.
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa:
   - **NÃO é XSS.** Nenhum código do atacante roda no alvo; o atacante **nunca lê** a resposta do alvo (a **SOP** proíbe ler cross-origin) — o ataque é **CEGO** (fire-and-forget). "Cross-site" aqui ≠ "cross-site scripting". *(Contraste com `21`/`08`/`02`, publicados: lá o script roda DENTRO do alvo e lê tudo.)*
   - **NÃO é o atacante roubar/ler o cookie.** O atacante **nunca** possui nem lê o cookie de sessão; o **browser da vítima** o anexa sozinho. *(Prova: no Burp o cookie está na request forjada, mas a página/JS do atacante nunca o leu — SOP.)*
   - **NÃO é bug de sessão/auth nem login bypass.** A sessão é **válida**, a vítima **está** logada. O buraco é a **INTENÇÃO** — o servidor autoriza a mudança-de-estado por identidade, sem verificar que o user a quis. *(Contraste com `15`, publicado: fixation mexe no ciclo da sessão; aqui a sessão está certa.)*
   - **O que É (prova):** o servidor executa uma ação de mudança-de-estado confiando **só no cookie** (QUEM), sem verificar **INTENÇÃO** (QUE você quis). A correção é exigir um **token** que o atacante não consegue **LER**.
6. **Impact (honesto — sem overclaim).** **Account takeover** via troca de e-mail forçada → o atacante controla o e-mail de recuperação → um reset de senha vai pra ele. É **subverter uma ação privilegiada sem o consentimento da vítima**, às **cegas** (a SOP impede ler a resposta). **Não** é leitura de dado, **não** é comprometimento do servidor. Sem overclaim, sem foreshadow.
7. **Why the fix works (porta 8123).** Repetir contra o `fixed/`:
   - A **MESMA** página do atacante (agora apontando pro :8123) → o browser dispara o `POST /email` e **AINDA anexa o cookie de sessão** (SameSite=None, igual) → mas o servidor responde **403**: o **token está ausente** do corpo. O atacante não conseguiu **LER** o token (a SOP impede ler o form/resposta do alvo cross-origin), então não o incluiu. **Cravar: o cookie AINDA viajou junto — esse é o ponto** (nota #2 do DIFF: ter o cookie não basta; o token tem que ser suprido no corpo).
   - **Prova de isolamento:** o fluxo **LEGÍTIMO** (a vítima usa o form real do alvo, que **tem** o token) funciona nos **DOIS** lados. Só a request **forjada/sem-token** separa `vulnerable` de `fixed`.
   - **A lição do diff:** o fix é o **token** (nota #1 — um dos três controles legítimos; verifica intenção, é portável); o token vai na **request**, não (só) no cookie (nota #2); impacto = account takeover, **não** XSS (nota #3). A config de cookie (`SameSite=None; Secure`) é **idêntica** nos dois — o único delta é o token.

**Sem** seção de exercícios/variações e **sem** "trilha browser secundária" (`CLAUDE.md` §5/§3.3). Payloads/screens/prova (o e-mail mudando; o 403) são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**Account takeover via CSRF** — troca forçada do e-mail da conta → controle do e-mail de recuperação → reset de senha capturável pelo atacante. Mesmo espírito das irmãs A01 (subverter uma ação/objeto privilegiado sem autorização real), no eixo da **intenção**. **Sem overclaim:** CSRF é sobre **ações de mudança-de-estado que a vítima não pediu** — **não** é leitura de dado (a **SOP cega o atacante**: ele não lê a resposta cross-origin), **não** é execução de código no alvo (isso é XSS), **não** é comprometimento do servidor. A **prova do lab** é o e-mail mudar (vulnerable) e o 403 (fixed); a cadeia até o takeover completo (reset de senha) é **descrita, não armada** (§8 — o lab não implementa o reset). **Sem foreshadow.**

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (form de login + página de conta com o form de troca de e-mail; e a página do atacante — não API-only; e o browser é **obrigatório** pra provar o mecanismo, §3.3 exceção client-side). Garantir que a **ÚNICA** lição é o `POST /email` confiar no cookie de sessão como prova de **intenção**:

- **`GET /` e `POST /login` NÃO são a vuln.** São só o palco (mostrar a conta, estabelecer a sessão). A **única** superfície é o `POST /email`.
- **O `fixed` muda SÓ a lógica do token** (gerar + embed + validar). A config de cookie (`SameSite=None; Secure`) é **IDÊNTICA** nos dois lados; só o **nome** difere (plumbing anticolisão, item 2). O **token é o único delta de segurança**.
- **A página do atacante NÃO tem vuln.** É o palco cross-site; sem segunda superfície injetável.
- **Sem datastore, sem segunda superfície, sem segredo real** (`secret_key` dummy). Estado da conta em memória.
- **SAÍDA B → PROVAR por probe (risco #2)** a dança `SameSite=None`/cross-site/`Secure`-sobre-loopback num browser headless real **ANTES de escrever**, incluindo o par de origens (item 1). Se não reproduzir sem HTTPS, **PARAR e avisar**.

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/csrf`** — a página conceitual de CSRF (título/grafia esperados: **"Cross-site request forgery (CSRF)"**, abertura "What is CSRF?"). É a página de introdução da vuln, não a de labs.
- **Texto do link:** **"Cross-site request forgery (CSRF)"** — a forma que a própria PortSwigger usa. Preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo dos irmãos).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A01 — Broken Access Control** (`atoms/A01-broken-access-control/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `csrf-basic` em A01; `CLAUDE.md` §4 fixa a pasta. Situar em A01 **sem arqueologia**. |
| Posição na fase | Ver `ROADMAP.md` | A posição/ordinal/release vivem só no ROADMAP. Spec e conteúdo nascem **limpos** (foreshadow §5). |
| Topologia | **MULTI-CONTAINER — 3 serviços** (`vulnerable` + `fixed` + `attacker`) | O atacante é a origem cross-site. **NÃO** se falam server-to-server → **sem rede interna/`depends_on`/healthcheck** (diverge do 22). |
| "Saída B" (ferramenta-que-resiste) | **SIM — existe** (como no 14/15/18) | O default `SameSite=Lax` do browser bloqueia o CSRF ingênuo; o átomo modela as condições reais (2 origens cross-site + cookie `SameSite=None`). **NÃO** é uso-direto-do-antipadrão. |
| **Item 1 — par de origens** | **ABERTO — VOCÊ DECIDE/CONFIRME NA FASE 2** (candidato: alvo `127.0.0.1`, atacante `127.0.0.2`) | Comportamento de browser (cross-site + cookie anexado + Secure-sobre-HTTP-loopback) só se sabe testando. **PROPOR o que funcionar**; se nada simples sem HTTPS, PARAR. |
| **Item 2 — anticolisão de cookie** | **ABERTO — CONFIRME NA FASE 2** (candidato: nomes distintos `session_vuln`/`session_fixed`) | Cookie não distingue porta; alvos colidem em `127.0.0.1`. Plumbing de impl (latitude), desde que config de segurança idêntica e token o único delta. |
| Lição-coração | **O browser anexa o cookie de sessão sozinho em request cross-site; o servidor confia nisso como prova de INTENÇÃO. Fix = token que verifica intenção e o atacante não consegue LER (SOP).** | O bug é confiar em QUEM (cookie), não em QUE você QUIS (intenção). |
| Sub-lição — duas camadas | **`SameSite` (nível-cookie, browser, desligado aqui) vs token (nível-app, servidor, o fix)** | Isola que a correção é o token, não "religar SameSite". Ambas são defesas reais (nota #1). |
| Flavor — **TRAVADO** | **Troca de e-mail** (`POST /email`) → account takeover via reset | Cenário canônico de CSRF; mudança-de-estado clara; estado da conta em memória. |
| Payload-prova — **TRAVADO** | **`POST /email` forjado → e-mail vira `attacker@evil.example`** (vulnerable); **403** (fixed) | Prova = e-mail mudar (takeover). Benigno, `.example`, fake, loopback (§8). |
| Código vulnerable | **`POST /email` checa só `if "user" in session`** (o cookie), sem token, sem Origin | O cookie viaja sozinho → request forjada passa. |
| Código fixed | **synchronizer token à mão** (`secrets.token_urlsafe`, embed no form, validar no `POST`) | Verifica intenção; atacante não lê o token (SOP). Sem Flask-WTF (mecanismo cru). |
| Config de cookie vuln × fixed | **IDÊNTICA** (`SameSite=None; Secure`); só o **nome** difere (item 2) | O token é o **único** delta de segurança; isola que o fix é o token. |
| `app.py` vuln × fixed | **DIFERE — a lógica do token** (gerar + embed + validar) | O delta é o token; Dockerfile/requirements idênticos. |
| Trilha | **browser (PRINCIPAL, reproduz) + Burp (APOIA/prova)** | §3.3 exceção client-side: o cookie ser anexado cross-site **sozinho** só num browser; curl não forja (Nota 3-A). **Sem** trilha secundária. |
| Bibliotecas | **`Flask==3.0.0`** (pin candidato) + stdlib `secrets` | Sem datastore, sem dep extra. Confirmar install em `python:3.11-slim`. |
| Impacto | **Account takeover** (troca de e-mail → reset). CEGO (SOP). | Honesto; não é leitura/RCE/servidor. Sem overclaim, sem foreshadow. |
| Theory primer | **PortSwigger CSRF** (`/web-security/csrf`, confirmar por fetch) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. |
| Título (H1) | **`csrf-basic — Cross-Site Request Forgery (CSRF)`** (classe, sem stack) | `CLAUDE.md` §5. Slug carrega "basic"; H1 sem "Flask"/"SameSite"/"cookie". |
| Foreshadow | **ZERO pra frente** | `CLAUDE.md` §5. Não nomear átomos não-publicados/posição de fase/release. Publicados (02/08/15/21/22, A01 03/10/11/12) e ROADMAP OK. |
| Portas | **8023 / 8123** (alvos, bind `127.0.0.1`); atacante = item 1 | `CLAUDE.md` §8. Multi-container. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–6 são os centrais; 7–12 são higiene/isolamento. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes — **exceto os itens 1 e 2 (marcados VOCÊ DECIDE), que fecham na Fase 2.**

1. **Baseline (os dois lados).** `POST /login` estabelece a sessão; `GET /` mostra a conta e o form; a troca de e-mail **LEGÍTIMA** (pelo form real) funciona nos **DOIS** lados.
2. **O PROBE CRÍTICO (Saída B + item 1 — VALIDAR RODANDO num browser headless; VOCÊ DECIDE o par).** Confirmar **qual par de origens loopback** o browser trata como **cross-site**, que o alvo **SETA** o cookie `SameSite=None; Secure` sobre HTTP loopback, **E** que uma `POST` cross-site da origem do atacante **CARREGA** esse cookie pro alvo. **PROPOR o par que funcionar.** **Se NADA simples funcionar sem HTTPS, PARAR e avisar** — o átomo inteiro depende disso.
3. **O ATAQUE (browser PRINCIPAL — VALIDAR RODANDO).** Vítima logada abre a página do atacante → `POST` forjada → o **e-mail da conta MUDA** no `vulnerable` (:8023). **CAPTURAR** a cadeia real (login → cookie → página do atacante → e-mail trocado). **Se não reproduzir, PARAR e avisar — NÃO inventar** prova.
4. **FIXED (VALIDAR RODANDO).** A **MESMA** `POST` forjada → **403** (token ausente); e-mail da conta **INALTERADO**. **CAPTURAR.** Confirmar que o **cookie de sessão ESTÁ presente** na request forjada, mas o **campo do token está ausente** (o cerne da nota #2).
5. **Prova de isolamento.** O fluxo do **form LEGÍTIMO (com token)** funciona nos **dois** lados; só a request **forjada/sem-token** separa `vulnerable` de `fixed`.
6. **curl NÃO forja CSRF.** Um curl/Repeater com o cookie colado à mão é só uma **request autenticada normal**, **não** CSRF — confirmar que a demo é **browser-mediada** e **registrar por que curl não é a prova** aqui (Nota 3-A).
7. **Uma vuln só.** Só `POST /email`; `GET /` e `POST /login` **não** são a vuln; o `fixed` muda **só** o token; a página do atacante **não** tem vuln.
8. **Topologia/§8.** Três serviços; alvos `127.0.0.1` (8023/8123), atacante na origem do item 1 (loopback, local-only — **confirmar inalcançável de fora**); serviços **não** precisam de rede interna/`depends_on`/healthcheck; o atacante **pode não aparecer** no `./atom` (registrar). Flag do CI linter (§8/isolamento).
9. **Config de cookie byte-idêntica de SEGURANÇA** entre `vulnerable` e `fixed` (`SameSite=None; Secure` nos dois; a anticolisão do item 2 — ex. nomes distintos — é **plumbing**); o **ÚNICO delta de segurança** no `app.py` é a **lógica do token**.
10. **§8.** Valor de e-mail **benigno** (`attacker@evil.example`), dados fake, loopback; nada destrutivo; `secret_key` dummy.
11. **Diff `app.py` alvo-vuln × alvo-fixed:** só a **lógica do token** (gerar + embed + validar). `Dockerfile`/`requirements.txt` idênticos. `./atom up csrf-basic` sobe os três sem erro. *(Validação: a prova exige um **browser real** com **cookies + requests cross-site**; não observável por `curl`/`docker exec`. Reaproveitar/estender a técnica headless da memória `validating-client-side-xss-atoms-headless` — aqui com **PERSISTÊNCIA de cookie entre navegações**: login → cookie → página do atacante → conferir o e-mail trocado. A prova é uma **mudança de estado** (o e-mail), lida via `--dump-dom` do `GET /` do alvo — **não** um `alert` que trava headless. Candidato: `--user-data-dir` persistente entre invocações, ou um browser scriptado via CDP/Playwright; mecanismo exato **decidir na Fase 2**.)*
12. **Theory primer** confirmado **por fetch** (`/web-security/csrf`, título "Cross-site request forgery (CSRF)"). Se em dúvida, perguntar ao mantenedor. **Não inventar.** Confirmar a **grafia exata do H1**.

**Bloqueante remanescente:** o **item 1** (par de origens) e o **item 2** (anticolisão) são decisões que **fecham na Fase 2** por probe — não são pendências de design, são "propor o que funcionar rodando". **Pendências de Fase 2 (não bloqueantes agora):** provar a dança SameSite/cross-site/Secure-sobre-loopback (item 2 do checklist); capturar o ataque no vulnerable e o 403 no fixed (itens 3–4); confirmar a URL/H1 do primer por fetch (item 12); confirmar o pin do Flask por probe; gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **"Saída B"** (a ferramenta padrão — o browser com `SameSite=Lax` — resiste ao CSRF ingênuo), então o átomo **modela as condições reais** onde a vuln vive (2 origens cross-site + cookie `SameSite=None`). Cada beat deve poder ser lido com o **`xss-dom` (21)** aberto ao lado (o **CONTRASTE** — XSS lê dentro do alvo; CSRF é cego de fora — e o **molde da exceção de browser/headless**), o **`session-fixation` (15)** ao lado (contexto de sessão; "não é bug de sessão") e a família **A01** (03/10/11/12) ao lado (molde de átomo A01). **Abrir e fechar** na lição-coração: *o browser anexa o cookie sozinho; o servidor confia nisso como intenção; o fix é um token que verifica intenção e o atacante não consegue LER.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`01` INTEIRO** (molde HTML/estrutura), **`21` INTEIRO** (exceção de browser, técnica headless, contraste XSS↔CSRF), **`15`** (sessão/cookie, contraste), **`12`/`03`/`10`/`11`** (molde A01 e app com sessão/cookie), **`22`** (VOZ atual + molde de compose multi-serviço — MAS **sem** rede interna/healthcheck aqui). **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar "trilha browser secundária", encenação, nem arqueologia OWASP.
- **HÁ Saída B (crítico):** **NÃO** modelar o CSRF ingênuo (ele **falha** sob `SameSite=Lax` default) — modelar as condições reais. **PROVAR por probe num browser headless ANTES de escrever** (risco #2). **Se não reproduzir sem HTTPS, PARAR e avisar.**
- **A prova é o e-mail mudar no BROWSER (riscos #3/#4).** Não observável por `curl`/`docker exec` isolado — precisa de **browser real** com cookies e requests cross-site. Capturar: vulnerable → forjada → e-mail trocado; fixed → mesma forjada → 403, e-mail intacto (com o **cookie presente** e o **token ausente**). **Se não bater rodando, PARAR e avisar — NÃO inventar** prova/screens.
- **curl NÃO é a prova (Nota 3-A, risco #6):** cookie colado à mão = request autenticada normal, não CSRF. O que caracteriza CSRF é o **browser anexar o cookie sozinho a partir do site do atacante**. Registrar por que curl não reproduz.
- **A sutileza que NÃO pode enfraquecer a lição:** o **fixed aplica o TOKEN**, **NÃO** "religa o `SameSite` pra `Lax`" (a config de cookie fica **idêntica**, `SameSite=None`, nos dois lados). O token é o **único delta de segurança** — isso isola que a correção é o token. As outras duas defesas (SameSite/Origin) são **legítimas** e nomeadas na nota #1 (defense-in-depth), **não** aplicadas como "o fix".
- **O cerne (nota #2):** o **cookie viaja junto** na request forjada; por isso "ter o cookie" não pode ser a checagem. O token funciona porque tem que ser **suprido no corpo** — algo que o atacante **não consegue LER** (SOP). Cravar.
- **Uma vuln só:** foco no `POST /email` confiar no cookie. `GET /`/`POST /login` não são a vuln; a página do atacante não tem vuln; sem datastore; sem segunda superfície. `secret_key` dummy.
- **Abertura seca + trilha browser-principal (Burp apoia):** WALKTHROUGH entra direto na mecânica; **sem** encenação; **sem** trilha browser secundária. Rotular os beats: **context (definir CSRF/cross-site/SameSite/SOP/cookie-auto-anexado/token; as duas origens)** → **spot the bug (`POST /email` só checa o cookie)** → **exploitation (browser: login → página do atacante → e-mail trocado)** → **papel do Burp (prova que a forjada carrega o cookie e não tem token; curl não forja)** → **o que a vuln NÃO é (não é XSS/roubo-de-cookie/bug-de-sessão)** → **impacto (account takeover, cego)** → **fixed (mesma forjada → 403; cookie ainda viajou)**.
- **Impacto honesto:** **account takeover**, **cego** (SOP). **Sem overclaim** (não é leitura/RCE/servidor), **sem foreshadow**.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é confiar no cookie como intenção; **não é XSS** (nenhum código no alvo; SOP cega o atacante), **não é roubo de cookie** (o browser anexa sozinho), **não é bug de sessão/auth** (a sessão é válida; o buraco é a intenção).
- **Contraste (cravar):** tabela CSRF↔XSS (central); prosa com `15` (não é sessão) e a família A01 (mesma categoria, eixo intenção). Citar publicados (02/08/15/21/22, A01 03/10/11/12) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** CSRF, cross-site (vs cross-origin), cookie de sessão, `SameSite`, request de mudança-de-estado, Same-Origin Policy (SOP), token anti-CSRF / synchronizer token, secure context / potentially trustworthy.
- **A01 sem arqueologia:** situar em **A01 — Broken Access Control**, explicar **por que** (autorizar mudança-de-estado por identidade, ignorando intenção), **sem** contar edições antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `csrf-basic — Cross-Site Request Forgery (CSRF)`. "Flask"/"SameSite"/"cookie" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **21** (contraste XSS + molde de exceção/headless), **15** (sessão), **A01 03/10/11/12** (categoria), **22** (molde compose), todos publicados. **PROIBIDO** referenciar/foreshadowar **qualquer átomo não-publicado/categoria futura** por número, nome **ou** descrição — inclusive posição/ordinal de fase e release. **A própria spec nasce limpa** (é commitada no repo público): onde precisar situar posição, apontar pro `ROADMAP.md`; nas frases que proíbem foreshadow, manter a proibição **genérica**.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT**. Termos técnicos (CSRF, cross-site, cookie, `SameSite`, SOP, token, payload, session) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (CSRF), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 23: `csrf-basic` — Cross-Site Request Forgery (CSRF): a state-changing POST trusts only the session cookie the browser attaches automatically, so a cross-site auto-submitting form forges an authenticated email change (account takeover); the fix is a per-session anti-CSRF token the attacker cannot read (A01 Broken Access Control). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 23 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline → ataque (e-mail trocado) no vulnerable → 403 no fixed, **num browser real** com persistência de cookie. Provar via Burp que a forjada carrega o cookie e não tem token.
- **Portas:** `127.0.0.1:8023` (vulnerable), `127.0.0.1:8123` (fixed); atacante = item 1. Bind loopback. Multi-container, **sem rede interna**.
- Se houver dúvida sobre o par de origens (item 1), a anticolisão (item 2), a URL/H1 do primer, o pin do Flask, ou se o ataque não reproduzir no browser, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos multi-origem/client-side):

- **`csrf-cookie-proves-who-not-intent`** — *"O átomo `csrf-basic` (23) entra em A01 (reaproveita `atoms/A01-broken-access-control/`): CSRF via `POST /email` que checa só `if 'user' in session` (o cookie). MULTI-CONTAINER (vulnerable :8023 + fixed :8123 + attacker), mas os 3 NÃO se falam (browser media) → SEM rede interna/depends_on/healthcheck (diverge do compose do 22). É SAÍDA B: `SameSite=Lax` default do browser bloqueia o CSRF ingênuo, então o átomo modela as condições reais — 2 origens cross-site + cookie `SameSite=None; Secure` (Secure sobre HTTP funciona porque loopback é secure context). Fix = synchronizer token à mão (`secrets.token_urlsafe` em `session`, hidden field no form, validar no POST); a config de cookie é IDÊNTICA nos dois lados (token = único delta de segurança). Cerne: o cookie VIAJA na forjada (SameSite=None), então a defesa é exigir o token no CORPO — o atacante não LÊ (SOP). DUAS decisões de plataforma abertas confirmadas por probe na Fase 2: (1) par de origens loopback cross-site (candidato 127.0.0.1 vs 127.0.0.2; 127.0.0.2 não aparece no `./atom` — regex só casa 127.0.0.1); (2) anticolisão de cookie por porta (candidato nomes distintos session_vuln/session_fixed). Prova = e-mail mudar (takeover) num BROWSER real com persistência de cookie (curl NÃO forja CSRF — cookie colado à mão é request autenticada normal); técnica headless com --dump-dom lendo o e-mail (não alert). Contraste com XSS (21): XSS roda DENTRO do alvo e LÊ; CSRF dispara de FORA e é CEGO. Três fixes legítimos em camadas (token/SameSite/Origin) — nota #1 do DIFF, diferente da nota 'defesa errada' dos átomos anteriores. Só Flask==3.0.0 + stdlib secrets; sem datastore."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão.
