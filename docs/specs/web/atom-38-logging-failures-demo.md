# Spec — Átomo 38: `logging-failures-demo`

> Documento de especificação para o Claude Code implementar o átomo `logging-failures-demo` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo **ABRE uma categoria que NÃO EXISTE ainda — A09 (Security Logging and Monitoring Failures)**: a pasta `atoms/A09-*` **não está no disco** e **deve ser criada** (nome confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos `A0X-<categoria-kebab>` — ver Nota de planning 1). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER** — dois serviços (`vulnerable` + `fixed`), cada lado **um container Flask** com um **SQLite embutido** (`lab.db`) semeado no boot, molde do `weak-password-reset` (37) / `crypto-weak-hash` (31). Precisa de estado (usuários semeados + um contador de falhas), mas **NÃO** de concorrência nem de datastore externo — então SQLite embutido pros usuários + um **dict em memória** pro contador é o **candidato recomendado** (ver Nota de planning 4).
>
> **O QUE TORNA ESTE ÁTOMO ATÍPICO ENTRE TODOS OS ANTERIORES (o coração — cravar):** a falha **NÃO é explorável** no sentido dos outros átomos. **Não há payload** que crie um marcador `/tmp/pwned`, **não há dado** que vaze, **não há takeover**. A falha é uma **AUSÊNCIA**: quando um ataque acontece — aqui, um **brute-force** de login (o atacante martelando senha atrás de senha contra uma conta) —, o app **NÃO registra nada útil**, então o ataque fica **INVISÍVEL**: ninguém detecta, ninguém responde, e um forense depois não tem rastro pra reconstruir. **A "prova" NÃO é algo aparecendo — é o CONTRASTE ENTRE DOIS LOGS.** No `vulnerable`, a mesma rajada de brute-force passa em **silêncio** (só o log de acesso HTTP genérico do Werkzeug, que não distingue um login falho de segurança de qualquer outro `401`); no `fixed`, cada falha vira **uma linha de log de segurança estruturada**, e após um limiar de falhas consecutivas um **WARNING claro de brute-force** — o ataque fica **VISÍVEL**. A demonstração é rodar a **MESMA rajada** nos dois lados e comparar os dois `docker compose logs`.
>
> **A lição em uma linha:** quando um ataque acontece, o app precisa **REGISTRAR o evento de segurança**, senão o ataque fica **invisível** — ninguém detecta, ninguém responde, o forense não tem rastro. O `vulnerable` **não loga** as falhas de autenticação (só o log de acesso HTTP genérico, onde um login falho some no ruído); o `fixed` **loga cada falha** de forma estruturada (timestamp, conta-alvo, IP — o **FATO**, nunca a senha) e, após um limiar de falhas consecutivas, emite um **WARNING** de brute-force. O **mesmo** ataque: no `vulnerable` é invisível, no `fixed` é visível e investigável. O fix é **GERAR o log de segurança que não existe** — **não** bloquear o ataque (isso é rate-limiting, outra defesa) e **não** logar o segredo (a senha tentada não vai no log).
>
> **OS TRÊS ENQUADRAMENTOS QUE NÃO PODEM DESLIZAR (cravar nos beats "o que a vuln NÃO é" e nas notas do DIFF):** **(1) NÃO é rate-limiting/lockout** — o `fixed` **DETECTA e REGISTRA** o brute-force; **NÃO necessariamente BLOQUEIA**. A09 é sobre **VISIBILIDADE**, não prevenção. Rate-limiting/lockout é defesa **complementar** (defense-in-depth, honestidade-em-camadas), mas o furo aqui é a **CEGUEIRA**, não a falta de trava. **(2) NÃO é logar demais / logar o segredo** — o anti-padrão OPOSTO e perigoso é logar dados sensíveis (a senha tentada, tokens, PII), que também é uma vuln A09. O `fixed` loga o **EVENTO** (que houve uma falha, para qual conta, de qual IP) **SEM** logar a senha. **Logar o FATO, não o SEGREDO.** **(3) A PROVA É A AUSÊNCIA** — no `vulnerable`, o "sucesso" do atacante é que **NADA acontece**: nenhum log de segurança, nenhum alerta. A demonstração tem que deixar isso palpável (o log genérico/cego do `vulnerable` ao lado do log rico do `fixed`), **NÃO** um marcador aparecendo.
>
> **REQUISITO DIDÁTICO (crítico — este átomo é DENSO de vocabulário de observabilidade/detecção que o iniciante não tem):** o WALKTHROUGH e o README **DEVEM definir DO ZERO, na 1ª ocorrência**, assumindo que o aluno não conhece nenhum: **brute-force / credential stuffing** (tentar muitas senhas/credenciais contra uma conta); **evento de segurança** (uma ocorrência que o time de segurança quer saber — falha de autenticação, acesso negado, ação sensível); **log de segurança / trilha de auditoria** (o registro de QUEM fez O QUÊ, QUANDO, de ONDE — distinto do log de acesso HTTP genérico); **log estruturado** (uma linha com campos claros pra máquina e humano lerem); **detecção vs prevenção** (VER um ataque vs BLOQUEAR um ataque — A09 é sobre ver); **a diferença entre log de ACESSO (todo request) e log de SEGURANÇA (eventos que importam)**; **por que NÃO logar o segredo** (a senha tentada não vai no log). Definir com clareza de iniciante — **NÃO** assumir familiaridade. Ver "O MECANISMO em detalhe" e a Nota de planning 3.
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha BURP**: a rajada de brute-force é HTTP (Intruder/Turbo Intruder ou uma rajada de N `POST /login`), e a **"leitura" da prova é o `docker compose logs` dos dois lados; SEM browser** — não há execução client-side; §3.4 — **SQLite** por padrão; §4 — **criação da categoria nova A09** (a pasta não existe — confirmar o nome contra o §4); §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, **definir termo na 1ª ocorrência**, situar em A09 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`**, dados fake; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referências vivas** — o **`weak-password-reset` (37) INTEIRO** (o **MOLDE quase-exato** da app: single-container SQLite com usuários semeados e senhas hasheadas com werkzeug, API-only JSON, `GET /` banner + `POST /login`; **aqui o `POST /login` é o alvo do brute-force**, e o diff é sobre o **LOGGING** em volta dele; e o `print(..., flush=True)` do 37 como stand-in de entrega mostra o padrão de escrever no stdout que o `docker compose logs` lê), o **`crypto-weak-hash` (31) INTEIRO** (o mesmo molde single-container SQLite + usuários hasheados + API-only), o **`session-fixation` (15)** (o molde do **dict em memória** pro estado efêmero — lá o `SESSIONS`, aqui o **contador de falhas por conta**), o **`cve-demo` (36)** (o **PRECEDENTE de átomo ATÍPICO** — "mais demonstrativo do que explorável", que caiu pro **fallback OWASP** no primer por ausência de página conceitual limpa na PortSwigger; **é o molde mais próximo de como estruturar um átomo que não é um exploit clássico**), o **`race-condition-basic` (35)** (voz atual), e o **`sqli-union-basic` (01)** (molde canônico single-container Flask + estrutura de doc). **O ATÍPICO:** **NÃO** há um átomo-irmão de "prova por ausência". O contraste conceitual é com **TODOS** os anteriores — neles a prova era algo **APARECENDO** (um marcador `/tmp/pwned`, um dado vazado, um takeover); aqui a prova é o **CONTRASTE de logs** (um cego, um que vê). Esse é o beat central. Pode citar átomos publicados (01–37) como contraste.
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `app.py`, seed — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e CRIAÇÃO da categoria A09 (nova)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). Justificativa do ROADMAP para este átomo: *"átomo atípico, mais demonstrativo do que explorável. Mostra como a ausência de log deixa ataque invisível."*
>
> **A categoria A09 NÃO EXISTE ainda — o 38 CRIA a pasta.** `atoms/A09-*` **não está no disco** (o `ls atoms/` lista A01, A02, A03, A04, A05, A06, A07, A08, A10 — **falta a A09**). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A09-logging-failures/`.** A árvore do repo no `CLAUDE.md` §4 fixa **`A09-logging-failures/`** com `logging-failures-demo/` dentro. Note que a **categoria OWASP 2021 completa é "Security Logging and Monitoring Failures"**, mas o **nome de pasta encurta pra `logging-failures`** — **exatamente o padrão já usado no repo**, onde `A07-auth-failures/` encurta "Identification and Authentication Failures", `A08-data-integrity-failures/` encurta "Software and Data Integrity Failures", `A06-vulnerable-components/` encurta "Vulnerable and Outdated Components", e `A10-ssrf/` encurta "Server-Side Request Forgery". Ou seja: o nome de pasta é a **forma abreviada kebab** que o `CLAUDE.md` §4 já cravou; a **prosa (README/WALKTHROUGH/DIFF) nomeia a categoria por extenso — "A09 — Security Logging and Monitoring Failures"**. Pasta final: **`atoms/A09-logging-failures/logging-failures-demo/`** — a Fase 2 cria a pasta de categoria e a do átomo.
>
> **SINALIZO a abreviação explicitamente pro mantenedor conferir.** O brief que abriu esta fase propôs dois candidatos — `A09-logging-failures/` e `A09-security-logging-failures/`; o `CLAUDE.md` §4 usa a forma **encurtada** `A09-logging-failures/`. Sigo o **`CLAUDE.md` §4 como fonte da verdade** (§10.5: "o `CLAUDE.md` vence"), **exatamente como o `cve-demo` (36) seguiu pra `A06-vulnerable-components`** e o `session-fixation` (15) pra `A07-auth-failures`. Se o mantenedor preferir a grafia longa, é um **flip localizado** (renomear a pasta de categoria) — mas o default desta spec é o que o §4 escreve. **CONFIRMAR na revisão.**
>
> **Rótulo A09 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Não registrar um evento de segurança quando um ataque acontece é **A09 — Security Logging and Monitoring Failures** no OWASP Top 10 2021 (a edição que o projeto segue). **NÃO** relatar em que número/categoria essa classe caía em edições antigas do OWASP Top 10 — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A09 — Security Logging and Monitoring Failures.** Explicar **por que** é A09 (a falha está na **ausência de observabilidade de segurança** — o app não registra o evento —, não num controle de acesso ausente nem numa injeção — ver "Por que A09") é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW (atenção REDOBRADA)

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4, §12). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW (lei do projeto, `CLAUDE.md` §5; e esta spec é pública/commitada → nasce limpa) — ATENÇÃO REDOBRADA.** **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec**: situar o átomo por **ordinal de fase**, **milestone**, **release/versão** (`v0.x`/`v1.0` etc.), ou como **abertura/encerramento** de qualquer coisa — **INCLUSIVE** "o último átomo", "o que fecha a fase", "completa o Top 10", "o único átomo de A09", "o que abre A09", ou qualquer referência a **outros átomos futuros**. Este átomo, por posição no plano, é uma **tentação natural** de enquadrar como fechamento/conclusão de cobertura — **NÃO fazer isso em lugar nenhum** (é trabalho de release do mantenedor, fora do átomo). Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não-publicados**, **sem postular átomo futuro** (nada de "um próximo átomo vai mostrar outra falha de log"). **A posição vive SÓ no `ROADMAP.md`.** Confirmo aqui apenas o **número (38)**, o **slug (`logging-failures-demo`)** e a **categoria (A09)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo. **Pode citar átomos publicados (01–37)** à vontade (`CLAUDE.md` §5) — em especial o `37` (molde da app + o `POST /login`), o `31` (molde), o `15` (dict em memória), o `36` (precedente de átomo atípico), o `35` (voz atual).

## Nota de planning 3 — convenções ATUAIS: Burp (justificado) + docker logs, abertura seca, requisito didático, a forma B1 e os três enquadramentos

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **Trilha BURP — JUSTIFICADA (`CLAUDE.md` §3.3 — Burp é a ferramenta principal).** O "ataque" é **dirigível por HTTP**: uma **rajada de brute-force** — N `POST /login` contra uma conta com senhas erradas — no **Repeater** (uma a uma) ou no **Intruder/Turbo Intruder** (a lista de senhas de uma vez). A **"leitura" da prova** é fora do Burp: o `docker compose logs vulnerable` e o `docker compose logs fixed` (o equivalente ao `docker compose exec` do marcador no `cve-demo` (36), ou ao `docker compose logs` do "inbox" no `weak-password-reset` (37) — o passo out-of-band que o Burp não faz). **SEM browser** — não há execução client-side; a prova é **texto de log**, não uma tela.
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (uma app com login) e a falha (o caminho da falha de autenticação **não registra nada de segurança**, então um brute-force passa invisível). **NADA** de encenação ("você é o pentester" e afins).
> - **REQUISITO DIDÁTICO — definir CADA termo DO ZERO na 1ª ocorrência (`CLAUDE.md` §5 + o brief).** Este átomo é denso de **vocabulário de observabilidade/detecção**: **brute-force/credential stuffing**, **evento de segurança**, **log de segurança/trilha de auditoria**, **log estruturado**, **detecção vs prevenção**, **log de acesso vs log de segurança**, **por que não logar o segredo**. Ver a lista completa e as definições candidatas em "O MECANISMO em detalhe".
> - **A FORMA DA DEMONSTRAÇÃO — B1 (TRAVADO): contraste lado a lado dos logs.** O WALKTHROUGH roda a **MESMA rajada** de brute-force nos dois lados e mostra os dois `docker compose logs` em sequência. No `vulnerable`: log de acesso genérico (linhas de `401` que não dizem nada de segurança) → ataque INVISÍVEL. No `fixed`: a trilha estruturada + o WARNING. A prova é a **COMPARAÇÃO** (mesmo ataque, um lado cego, outro que vê). **NÃO** fazer o brute-force **ACERTAR** uma senha (isso é a forma **B2, descartada** — desliza o foco pra "senha fraca / faltou rate-limit"). O impacto **MENCIONA em UMA frase** que no mundo real uma dessas tentativas acerta e sem log ninguém investiga — **SEM** mover o foco pra o takeover. O foco é a **VISIBILIDADE**.
> - **OS TRÊS ENQUADRAMENTOS (cravar):** não-rate-limit; não-logar-segredo; a-prova-é-a-ausência (detalhados no topo e na "Sub-lição CRÍTICA").
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** — **missing security logging of authentication failures** —, **NÃO** o motor ("...em Flask"/"...em Python"/"...com `logging`"). O **slug** (`logging-failures-demo`) já qualifica a variante. "Flask"/"Python"/"`logging`" aparecem no **corpo**, não no H1. Candidato de H1 em "Identidade".
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Rodar a rajada de brute-force`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A09 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — topologia single-container: SQLite embutido (usuários) + dict em memória (contador); sem concorrência

> **Precisa de estado, mas NÃO de concorrência nem de datastore externo.** A app tem **usuários** semeados (a vítima do brute-force + um segundo) e, no `fixed`, um **contador de falhas** por conta. **NÃO** precisa de concorrência/corrida (diferente do `race-condition-basic`, 35). Então:
>
> - **CANDIDATO RECOMENDADO — SINGLE-CONTAINER com SQLite embutido pros usuários**, molde **exato** do `weak-password-reset` (37) / `crypto-weak-hash` (31): cada lado é **um** container Flask com seu próprio `lab.db` efêmero, criado e semeado no boot por um `init_db()` (sem datastore externo, sem bind mount de seed, sem `depends_on`/healthcheck/rede nomeada). O `docker-compose.yml` tem **dois serviços** (`vulnerable` + `fixed`), bind **só** `127.0.0.1`.
> - **O contador de falhas vive num dict em memória** (`FAILURES = {}` → `email -> nº de falhas consecutivas`), molde do `SESSIONS`/`RESET_TOKENS` em dict do `session-fixation` (15) / `weak-password-reset` (37) — estado efêmero de curta vida, um dict basta. **Reset no sucesso** (um login bem-sucedido zera a sequência daquela conta). **Só existe no `fixed`** (o `vulnerable` não conta nada).
> - **Onde vivem os usuários.** Os **usuários** (email + `password_hash`) moram no SQLite (molde do 37) — **hasheados decentemente** (`werkzeug.security.generate_password_hash`) pra **NÃO** introduzir a vuln de storage do 31 "de brinde" (§8.5). Aqui a app **não** troca senha nem persiste nada além do seed — o SQLite é escolhido por **consistência com o molde** e por deixar o login uma **query parametrizada realista** (um dict de usuários também funcionaria; SQLite casa com os irmãos). A senha **não** é o foco; o **logging** é.
> - **Concorrência / server model.** O brute-force é uma **sequência** de requests (Repeater/Intruder), não uma corrida. O contador é estado global mutável; sob rajada concorrente (Turbo Intruder), incrementos poderiam interleavar. **Candidato: `threaded=False` nos DOIS lados** (molde do 37 — mantém o contador determinístico E mantém o **server model IDÊNTICO** entre `vulnerable` e `fixed`, pra o **único** diff continuar sendo o **logging**). **CONFIRMAR o comportamento do contador sob a rajada na Fase 2** (item aberto — não trava a spec).
> - **§8:** bind **só** `127.0.0.1` (8038/8138); usuários/senhas **dummy**; nada real. O SQLite é local ao container, efêmero.

---

## Decisões abertas — VOCÊ DECIDE / CONFIRME NA FASE 2 (PROPOR O QUE FUNCIONAR)

> O **objetivo** de cada item está **TRAVADO**; o que fica aberto é **qual valor/forma concreta** o realiza. O Item 1 é **comportamento de plataforma (o logging aparecer de fato no `docker compose logs`, e o log de acesso genérico coexistir com o de segurança) que só se conhece TESTANDO** — um **probe de comportamento sério**, não preferência editorial.

### Item 1 (O NÓ TÉCNICO) — o CONTRASTE dos logs tem que ser PALPÁVEL rodando (objetivo TRAVADO; a saída a PROVAR RODANDO)

**O problema.** A lição só existe se, rodando a **mesma rajada** nos dois lados, o `docker compose logs vulnerable` **genuinamente não mostra nada de segurança** (só o log de acesso HTTP genérico) e o `docker compose logs fixed` **mostra a trilha estruturada + o WARNING**. Três rugas a resolver **rodando**:

- **O log de segurança do `fixed` tem que APARECER no `docker compose logs`.** Por default, o `logging` do Python pode não emitir no nível/stream esperado, e o `app.logger` do Flask fica em `WARNING` sem config. **Candidato recomendado:** um **logger dedicado** `logging.getLogger("security")` com um `StreamHandler` próprio e nível `INFO` (ou `logging.basicConfig(level=logging.INFO, ...)`), escrevendo linhas com timestamp/nível/campos. O `Dockerfile` já roda `python -u` (unbuffered, molde dos irmãos) → as linhas saem na hora. **PROVAR** que as linhas de segurança aparecem no `docker compose logs fixed`.
- **O log de ACESSO genérico do Werkzeug tem que APARECER nos DOIS lados** (senão o contraste vira "log-nenhum vs log", que é fraco e desonesto — o certo é **segurança-ausente vs segurança-presente**). O servidor de dev do Flask (Werkzeug) já emite linhas de acesso (`... "POST /login HTTP/1.1" 401 -`) por default. **PROVAR** que elas aparecem no `vulnerable` **e** no `fixed`, e que a config de logging do `fixed` **NÃO as suprime** (por isso o logger dedicado, que não mexe no logger do Werkzeug, é o candidato mais seguro — confirmar). **Cravar:** o `vulnerable` **NÃO** é "log-nenhum"; ele tem o log de acesso genérico — o que ele **não** tem é o log de **segurança**.
- **A rajada separa os lados de forma legível.** Rodar N (candidato ≥ 20) `POST /login` errados contra a mesma conta nos dois lados; capturar os dois `docker compose logs` **reais**. **PROVAR** que o `vulnerable` mostra só os `401` genéricos (sem conta/IP-como-evento/limiar) e o `fixed` mostra as linhas de segurança + o WARNING no limiar.

**O que a Fase 2 tem que PROVAR (rodando de verdade):** que a mesma rajada de brute-force, nos dois lados, produz um `docker compose logs vulnerable` **cego** (só acesso genérico) e um `docker compose logs fixed` **rico** (a trilha estruturada por falha + o WARNING de brute-force no limiar), que a **senha tentada NÃO aparece** em lugar nenhum do log do `fixed`, e que o `fixed` **NÃO bloqueia** o login (os `401` continuam saindo — detecção, não prevenção). **CAPTURAR os dois logs reais.** **PROPOR o que funcionar.** **Se o contraste NÃO for palpável rodando (ex.: o log de segurança não aparece, ou o log de acesso some), ajustar a config de logging DENTRO do escopo travado (o `vulnerable` não loga segurança; o `fixed` loga o evento estruturado + WARNING, sem bloquear e sem logar a senha) e PROVAR; se NADA reproduzir, PARAR e avisar o mantenedor — NÃO inventar as linhas de log.**

### Itens de forma (candidato registrado; a Fase 2 confirma pela via mais didática)

- **Item 2 — o LIMIAR do WARNING.** Candidato **recomendado: 5 falhas consecutivas na mesma conta**. Baixo o bastante pra a rajada cruzá-lo cedo e o aluno ver o WARNING claramente; alto o bastante pra não disparar num typo isolado. Confirmar na Fase 2. **Disparar o WARNING uma vez no cruzamento** (`count == LIMIAR`) é o candidato (evita spam de WARNING); alternativa registrada: re-avisar a cada N. Confirmar.
- **Item 3 — o FORMATO da linha de log de segurança.** Candidato **recomendado: linha estruturada `key=value` via `logging` do Python** (timestamp · nível · logger `security` · evento · `account=` · `ip=`), a via mais legível num `docker compose logs` de terminal e paralela ao estilo `key=value` que o repo já usa (o `[reset-email] to=... token=...` do 37). Alternativa registrada: **JSON por linha** (`{"ts":..,"level":..,"event":"auth_failure","account":..,"ip":..}`) — mais "SIEM-ready", menos legível a olho. **Recomendo o `key=value`**; confirmar a via mais palpável na Fase 2. **Sem a senha em nenhum formato.**
- **Item 4 — ONDE/COMO o contador vive e a CHAVE.** Candidato **recomendado: dict em memória `FAILURES` chaveado por CONTA (`email`)** — o "N falhas consecutivas na **mesma conta**" do brief sai natural; **reset no sucesso** (`FAILURES.pop(email, None)`). A linha **por-falha** registra **conta E IP**; o **limiar** é sobre a conta. Alternativa registrada: chavear por `(conta, IP)` (mais preciso pra credential stuffing distribuído) — mais complexo, provavelmente desnecessário pra a demo de um atacante só. **Recomendo chave por conta.** Confirmar na Fase 2.
- **Item 5 — o tamanho da rajada e a via.** Candidato: **N ≥ 20** `POST /login` errados contra `victim@lab`. Via: **Intruder/Turbo Intruder** (lista de senhas) no WALKTHROUGH; uma **rajada programática** (loop `curl`/`http.client`) pode ser usada na **validação** pra capturar os logs reais de forma reprodutível. Confirmar na Fase 2. **Garantir que a lista de senhas NÃO contém a senha real do seed** (senão a rajada acertaria — B2, descartado).
- **Item 6 — o log vai pro stdout/stderr (pra o `docker compose logs`).** Candidato **recomendado: SIM** — as linhas de segurança e as de acesso vão pro stdout/stderr do container (ambos capturados por `docker compose logs`). É **como a prova é lida**. Confirmar na Fase 2 (parte do Item 1).
- **Item 7 — o `fixed` loga sucessos também?** Candidato **recomendado: NÃO no core** — o `fixed` loga a **falha** (o evento relevante pra este átomo) + o **WARNING**; o reset do contador no sucesso acontece **sem** uma linha de sucesso, pra manter o `fixed` mínimo (`CLAUDE.md` §2). Uma trilha de auditoria real também loga sucessos (quem entrou, quando, de onde) — isso vira **UMA frase** na nota do DIFF (o que uma trilha completa inclui), **não** código. Confirmar na Fase 2.

---

## Identidade

- **ID:** `logging-failures-demo`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A09 — Security Logging and Monitoring Failures**. Pasta `atoms/A09-logging-failures/` (**NÃO EXISTE — o 38 CRIA**; nome abreviado kebab, ver Nota de planning 1). Confirmado contra o `ROADMAP.md` ("A09 Logging Failures") e o `CLAUDE.md` §4. Em prosa, usar o nome da **classe** — **missing security logging of authentication failures** — e a categoria por extenso — **"A09 — Security Logging and Monitoring Failures"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A09-logging-failures/logging-failures-demo/` (Fase 2 cria a pasta de categoria e a do átomo)
- **Número sequencial:** 38
- **Porta `vulnerable`:** `127.0.0.1:8038` (TRAVADO)
- **Porta `fixed`:** `127.0.0.1:8138` (TRAVADO)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos.
- **Topologia:** **SINGLE-CONTAINER por lado** — dois serviços (`vulnerable` + `fixed`), **SQLite embutido** por lado (`lab.db` semeado no boot) + **dict em memória** pro contador (só no `fixed`). Molde do `weak-password-reset` (37) / `crypto-weak-hash` (31).
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/abertura/encerramento** (§5 foreshadow — atenção redobrada, Nota 2).
- **Branch de trabalho:** `atom/logging-failures-demo`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** ver seção "Theory primer". **PortSwigger PRIMEIRO** — mas a Academy **provavelmente não tem** uma página conceitual limpa dedicada a logging/monitoring (o foco dela são vuln-classes exploráveis; A09 é de **observabilidade**). **FALLBACK OWASP (provável):** a página do **A09:2021** no site do OWASP Top 10 e/ou o **OWASP Logging Cheat Sheet**. **NÃO inventar URL/grafia — confirmar TODAS por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. **Mesmo desvio consciente do `cve-demo` (36)** — avisar o mantenedor.
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# logging-failures-demo — Missing security logging of authentication failures`** — `id` + nome canônico da **classe** em inglês. **SEM** "Flask"/"Python"/"`logging`" no H1 (o slug já qualifica; o motor fica no corpo). *(Alternativas registradas: `Insufficient security logging of authentication failures`, ou a forma mais ampla `Missing security logging and monitoring`.)* Recomendo **"Missing security logging of authentication failures"** por nomear o **defeito exato** (o evento de segurança que **não** é registrado) e ser a forma mais reconhecível/transferível pra um pentester procurando a classe. Grafia canônica exata **confirmável na Fase 2**; **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**Missing security logging of authentication failures — um ataque roda sem deixar rastro, então ninguém o vê.** Uma app mínima tem **login**: `POST /login {email, password}` compara a senha com o hash guardado e responde `200` (autenticado) ou `401` (falhou). O login está **correto** — query parametrizada, hash decente, `401` pra senha errada. Mas quando um atacante roda um **brute-force** (tentar muitas senhas contra uma conta), cada `401` no `vulnerable` é **silencioso**: o app **não registra o evento de segurança**. O que sobra é o **log de acesso HTTP genérico** do servidor (uma linha por request, tipo `"POST /login" 401`) — que **não distingue** um login falho de segurança de qualquer outro `401`, não carrega a **conta-alvo** (o email vai no corpo, não na URL), não classifica o evento como segurança, e não **agrega** (vinte `401` seguidos parecem vinte usuários errando a senha). O ataque **não aparece** em nenhum lugar que um sistema de monitoração pegaria: ninguém detecta, ninguém é alertado, e um forense depois não tem rastro. A falha **não é** no login (ele funciona); é a **AUSÊNCIA de um log de segurança** no caminho da falha. O fix **não** é bloquear o ataque (isso é rate-limiting, outra defesa) nem logar a senha (isso é outra vuln): é **GERAR o log de segurança que não existe** — uma linha estruturada por falha (o **FATO**: evento, conta, IP, timestamp) e um **WARNING** de brute-force após um limiar.

### A lição-coração

> **"Quando um ataque acontece — aqui, um brute-force martelando o login de uma conta — o app precisa REGISTRAR o evento de segurança, senão o ataque fica INVISÍVEL: ninguém detecta, ninguém responde, e um forense depois não tem rastro. O `vulnerable` não loga as falhas de autenticação (só o log de acesso HTTP genérico, onde um login falho some no ruído); o `fixed` loga cada falha de forma estruturada (timestamp, conta-alvo, IP — o FATO, nunca a senha) e, após um limiar de falhas consecutivas, emite um WARNING de brute-force. O mesmo ataque: no `vulnerable` é invisível, no `fixed` é visível e investigável. O fix é GERAR o log de segurança que não existe — não bloquear o ataque (isso é rate-limiting, outra defesa) e não logar o segredo (a senha tentada não vai no log)."**

**+ MECANISMO:** um **evento de segurança** é uma ocorrência que o time de segurança quer saber (uma falha de autenticação, um acesso negado, uma ação sensível). O **log de ACESSO** (todo request, genérico — método, path, status, IP) e o **log de SEGURANÇA** (os eventos que importam, com contexto — QUEM/O QUÊ/QUANDO/DE ONDE) estão em **altitudes diferentes**: o de acesso registra o **transporte** (um `POST /login` deu `401`), o de segurança registra o **significado** (uma falha de autenticação contra `victim@lab` vinda de tal IP — e, repetida, um brute-force). **N falhas seguidas na mesma conta é um sinal óbvio de ataque — mas só existe se você logar.** **+ SUB-LIÇÃO:** a causa é a **AUSÊNCIA DE LOG DE SEGURANÇA** (A09), **NÃO** a falta de rate-limit (detecção ≠ prevenção) e **NÃO** um bug no login (o login funciona; ele só não deixa rastro do ataque).

### O MECANISMO em detalhe (o coração do WALKTHROUGH — DEFINIR CADA PEÇA NA ESTREIA)

O átomo assume que o aluno **não conhece nenhum** destes conceitos. Definir do zero, na 1ª ocorrência:

- **Brute-force / credential stuffing.** **Brute-force** de login é tentar **muitas senhas** contra uma conta até uma funcionar (martelar `victim@lab` com `password1`, `123456`, `qwerty`... um atrás do outro). **Credential stuffing** é o primo: tentar **credenciais vazadas** (pares email:senha de outros vazamentos) contra muitas contas, apostando no reuso de senha. Os dois geram o mesmo sinal observável: **uma rajada de falhas de autenticação**. É esse sinal que o log de segurança precisa capturar.
- **Evento de segurança.** Uma **ocorrência que o time de segurança quer saber**: uma falha de autenticação, um acesso negado, uma mudança de privilégio, uma ação sensível (reset de senha, exclusão de dados). É o "algo relevante pra segurança aconteceu" — distinto de um evento **operacional** genérico (um request qualquer chegou). O átomo trata de **um** evento de segurança: a **falha de autenticação**.
- **Log de segurança / trilha de auditoria (audit trail).** O **registro de QUEM fez O QUÊ, QUANDO, e DE ONDE** — o histórico dos eventos de segurança. É o que um responder lê durante um incidente e o que um forense usa depois pra reconstruir o que houve. Uma **trilha de auditoria** é esse log tratado como evidência: append-only, com contexto suficiente pra responsabilizar (accountability). Distinto do **log de acesso** (abaixo).
- **Log estruturado.** Uma linha de log com **campos claros** — legível por um **humano** e parseável por uma **máquina** (um SIEM — Security Information and Event Management, a plataforma que agrega logs e dispara alertas). Ex.: `... WARNING security authentication failure account=victim@lab ip=10.0.0.5` — cada campo (`account=`, `ip=`) é identificável, então uma ferramenta consegue filtrar/contar/alertar sem adivinhar. O oposto é uma frase solta (`"login falhou"`) que nem humano nem máquina aproveitam bem.
- **Detecção vs prevenção.** **Prevenção** é **BLOQUEAR** um ataque (rate-limiting, lockout de conta, WAF). **Detecção** é **VER** que o ataque está acontecendo (o log de segurança + o alerta). São defesas **diferentes e complementares**: você quer as duas. **A09 é sobre DETECÇÃO** — a capacidade de **saber**. Este átomo conserta a **cegueira** (a detecção), **não** adiciona uma trava (a prevenção).
- **Log de ACESSO vs log de SEGURANÇA (a distinção-chave).** O **log de acesso** registra **todo request** de forma genérica: IP de origem, timestamp, método, path, status (`10.0.0.5 - - [...] "POST /login" 401`). É **transporte** — ótimo pra operação (tráfego, latência, erros HTTP), **cego pra segurança**: não sabe **qual conta** um `POST /login` mirou (o email vai no **corpo**, não na URL), não classifica o `401` como "falha de autenticação" (pra ele é só um status), e não **agrega** ("isto é o 20º `401` da mesma origem contra a mesma conta"). O **log de segurança** registra os **eventos que importam** com o **contexto** que os torna acionáveis: o evento (`authentication failure`), a conta-alvo, a origem, e — somando — o **padrão** (`possible brute-force`). O `vulnerable` tem só o de acesso; o `fixed` **acrescenta** o de segurança. **A cegueira do `vulnerable` NÃO é "log-nenhum" — é o log na altitude ERRADA.**
- **Por que NÃO logar o segredo.** O log de segurança registra o **FATO** (que houve uma falha, para qual conta, de qual IP, quando) — **NUNCA o SEGREDO** (a senha tentada, tokens, PII). Logar o segredo é o **anti-padrão OPOSTO e perigoso**: transforma o log — que costuma ser lido por muita gente, replicado, e retido por muito tempo — num **vazamento** de credenciais (e é **também** uma vuln A09, "logging sensível"). Se a app logasse a senha tentada, um brute-force encheria o log de senhas reais de quem digitou errado a sua no lugar do email de outro, ou de senhas reais tentadas contra a conta certa. **Regra: logar o FATO, não o SEGREDO.**

**O ponto contraintuitivo a cravar:** o login **faz exatamente o que deveria** — rejeita a senha errada com `401`. O atacante **não burla** nada; ele só **tenta muito**. O furo não é que o `401` está errado (está certo); é que o `401` **não vira um evento de segurança registrado**. Por isso "consertar o login" não é a questão (o login está certo): a correção é **acrescentar a observabilidade** — fazer o caminho da falha **contar a história** (o evento, a conta, a origem) e **gritar** quando a história vira um ataque (o limiar → WARNING).

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas do DIFF)

> **A causa é a AUSÊNCIA DE LOG DE SEGURANÇA (A09), NÃO a falta de rate-limit e NÃO um bug no login. (1) NÃO é rate-limiting/lockout: o `fixed` DETECTA e REGISTRA o brute-force; NÃO necessariamente BLOQUEIA — os `401` continuam saindo. A09 é VISIBILIDADE, não prevenção; rate-limit/lockout é uma defesa COMPLEMENTAR (defense-in-depth), legítima mas ORTOGONAL, não o fix. (2) NÃO é logar o segredo: o `fixed` loga o EVENTO (falha, conta, IP, timestamp), NUNCA a senha tentada — logar o segredo é o anti-padrão OPOSTO, também A09. Logar o FATO, não o SEGREDO. (3) A PROVA É A AUSÊNCIA: no `vulnerable`, o "sucesso" do atacante é que NADA de segurança é registrado — a demonstração é o CONTRASTE de dois logs (um cego, um que vê), NÃO um marcador aparecendo. O login é IDÊNTICO e correto nos dois lados; o único diff é o logging de segurança no caminho da falha.**

### Por que A09 (Security Logging and Monitoring Failures)

O bug **não é** "input virou código" (injection — A03: o login não costura input num sink; a query é parametrizada), **não é** "faltou um check de dono / troquei um id" (A01/IDOR), **não é** "a credencial é adivinhável" (A07 — o token/senha aqui não é o objeto; a senha é hasheada decentemente e o login rejeita corretamente), **não é** "faltou bloquear o ataque" (rate-limit/lockout é **prevenção**, uma defesa **diferente**). É **"quando um evento de segurança aconteceu (uma rajada de falhas de autenticação), o app não o registrou, então o ataque ficou invisível pra detecção, resposta e forense"** — uma falha de **observabilidade de segurança**. No Web Top 10 2021 isso é **A09 — Security Logging and Monitoring Failures**, que cobre explicitamente **eventos auditáveis (logins, falhas de login) não registrados** e **ataques não detectados por falta de logging/alerting**. Situar em **A09 — Security Logging and Monitoring Failures**, **sem** contar edições antigas. Explicar **por que** é A09 (a falha está na **ausência do registro do evento** — a app não vê o ataque —, não num controle de acesso, numa injeção, ou numa trava ausente) é a lição. **A09 é a categoria sobre SABER que os outros nove aconteceram** — a capacidade de detectar, responder e reconstruir.

---

## Contraste — o eixo que DEFINE a identidade (o que separa este átomo de TODOS os anteriores)

Este átomo **não tem um irmão** de "prova por ausência" — ele é o **atípico**. O que o distingue de todo o resto é **onde mora a lição** e **qual é a prova**: a prova **não é algo aparecendo**; é o **CONTRASTE de dois logs** (um cego, um que vê). Cravar no WALKTHROUGH e no DIFF, ou o átomo se confunde com "faltou rate-limit" ou "senha fraca". **"Um átomo = uma vuln" se refere à CAUSA** (`CLAUDE.md` §2):

| Eixo | O vizinho conceitual | `logging-failures-demo` (38) |
|---|---|---|
| **A forma da PROVA (vs TODOS os anteriores)** | a prova é algo **APARECENDO** — um marcador `/tmp/pwned` no `cve-demo` (36) / `deserialization-pickle` (20), um dado vazando no `sqli-union-basic` (01), um takeover (logar como a vítima) no `weak-password-reset` (37) | a prova é a **AUSÊNCIA de rastro** no `vulnerable` **vs** a trilha no `fixed` — o **CONTRASTE de dois `docker compose logs`** sob o mesmo ataque. A "vitória" do atacante no `vulnerable` é que **NADA** de segurança é registrado |
| **Prevenção (rate-limiting / lockout)** | **BLOQUEAR** o brute-force — travar a conta, throttle por IP: o ataque **para** | **VER** o brute-force — registrar cada falha + WARNING no limiar: o ataque **fica visível**, mas o `fixed` **não o bloqueia** (os `401` continuam). **Detecção, não prevenção** — a09 é visibilidade. Rate-limit é defesa complementar, ORTOGONAL (honestidade-em-camadas) |
| **Logar o segredo (o anti-padrão OPOSTO)** | um log que grava a **senha tentada** / tokens / PII — um **vazamento** via log (também A09) | o log grava o **FATO** (evento, conta, IP, timestamp), **NUNCA** a senha. **Logar o FATO, não o SEGREDO** |
| **A credencial (vs `weak-password-reset`, 37)** | o segredo de autenticação é **adivinhável** (o token de reset previsível) — A07, uma falha no **desenho da autenticação** | a autenticação está **correta** (rejeita a senha errada); a falha é que a rejeição **não é REGISTRADA** como evento de segurança — A09, uma falha de **observabilidade**. Mesmo `POST /login` como pivô, causa oposta |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante):** em todo átomo anterior, o aluno **provava** a vuln fazendo **algo acontecer** (um marcador, um dado, um takeover). Aqui, o "algo" é **NADA acontecer** — e é justamente isso o problema. A demonstração inverte o hábito: você roda o **mesmo** ataque nos dois lados e a lição está no que o `vulnerable` **deixou de dizer**. O aluno abre os dois logs e vê: *"mesmo ataque — um lado é cego (não sei que fui atacado), o outro vê (a trilha + o alerta me dizem quem, o quê, quando, de onde)."* Citar átomos publicados (01–37) como contraste é bem-vindo (`CLAUDE.md` §5) — é o que ancora o "atípico".

---

## Uma vuln só — o login está correto e IDÊNTICO; a única falha é a AUSÊNCIA de log de segurança

Invariante inegociável do átomo (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é a **ausência de log de segurança** no caminho da falha de autenticação. Para garantir isso:

- **O login está CORRETO e é IDÊNTICO nos dois lados.** Mesmo `SELECT ... WHERE email = ?` (parametrizado — **sem SQLi**), mesmo `check_password_hash` (werkzeug — **sem bypass**), mesmo `200`/`401`. **NÃO** modelar SQLi no login, **NÃO** modelar senha fraca/hash fraco (seria a vuln do 31), **NÃO** modelar um bypass de autenticação. O login **funciona** — ele só é **cego** ao ataque.
- **O `fixed` NÃO adiciona rate-limit/lockout.** Ele **não trava** o login: cada tentativa do brute-force continua respondendo `401` (o ataque **não** é bloqueado — só **registrado**). Se a Fase 2 quiser mostrar lockout, é **SÓ na nota de honestidade-em-camadas** (defense-in-depth), **NÃO no código**. **Cravar:** detecção, não prevenção.
- **O `fixed` NÃO loga a senha tentada.** A linha de segurança registra o evento, a conta, o IP, o timestamp — **nunca** a senha. Logar o segredo seria **outra** vuln A09.
- **A senha dos usuários é guardada com um hash DECENTE.** `werkzeug.security.generate_password_hash` (KDF salted, o default do werkzeug) — **NÃO** MD5/SHA1 cru. Deliberado: **não** introduzir a vuln de storage do `crypto-weak-hash` (31) "de brinde" (§8.5). A senha **não** é o objeto de estudo; o **logging** é.
- **Sem 2ª vuln.** Sem injection (query parametrizada), sem IDOR, sem falha de hash, sem rate-limit adicionado, sem senha logada. **Único diff `vulnerable`↔`fixed`: o logging de segurança no caminho da falha de autenticação (a linha estruturada por falha + o contador + o WARNING no limiar).**

---

## Flavor — login sob brute-force, um lado cego (TRAVADO — B1)

Cenário canônico de A09: uma app com **login**, atacada por um **brute-force**, com um lado que **não registra** e um que **registra**.

- **APP (Flask, API-only JSON, `vulnerable` :8038 / `fixed` :8138):**
  - **`POST /login`** — `{"email": ..., "password": ...}`; compara com o `password_hash` do usuário (`werkzeug.check_password_hash`, query parametrizada). Responde `{"authenticated": true}` (`200`) ou `{"authenticated": false}` (`401`). **É o alvo do brute-force** e o **eixo do diff**: no `vulnerable`, o caminho da falha **não loga nada de segurança**; no `fixed`, loga a linha estruturada + incrementa o contador + emite o WARNING no limiar.
  - **`GET /`** — banner JSON de aviso (molde do 37/31/API-only) + dica de uso (`POST /login`; depois comparar `docker compose logs vulnerable` com `docker compose logs fixed` após a rajada; trabalhar do Burp Repeater/Intruder). **Banner de aviso** (`CLAUDE.md` §8.2) vive no README e no `GET /` JSON.
- **SEM HTML** (categoria naturalmente API-only — o alvo é um endpoint de login REST puro, e a prova é texto de log), como o `crypto-weak-hash` (31) / `weak-password-reset` (37). **Sem** `templates/index.html`. **COM datastore** (SQLite pros usuários; dict pro contador no `fixed` — Nota 4).
- **Usuários semeados (dummy):** `victim@lab` (o alvo do brute-force) e um segundo (`user@lab`), senhas de lab hasheadas com werkzeug. A senha real do seed **não** entra na lista de senhas da rajada (a rajada **não acerta** — B1).

**O ATAQUE (resumo; detalhe em "A prova"):** o atacante dispara uma **rajada de N (≥ 20) `POST /login`** contra `victim@lab` com senhas **erradas** (brute-force). No `vulnerable`, cada `401` é **silencioso** (só o log de acesso genérico) — o ataque passa **INVISÍVEL**. No `fixed`, cada falha gera uma **linha de log de segurança** (timestamp · nível · `authentication failure` · `account=victim@lab` · `ip=...` — **nunca** a senha), e após o **limiar** (candidato: 5 falhas consecutivas) sobe pra um **WARNING** (candidato: `possible brute-force against victim@lab from <IP> (5 failures)`). **A rajada NÃO acerta a senha** (B1; B2 descartado). **A PROVA é o CONTRASTE dos dois `docker compose logs`.**

---

## A prova — o CONTRASTE de dois logs (TRAVADO — B1)

**Cadeia (TRAVADA):**

- **(baseline, idêntico nos dois lados)** um login legítimo funciona: `POST /login {victim@lab, victim-lab-pw}` → `200 {"authenticated": true}`; um login falho **isolado** → `401 {"authenticated": false}`. A feature funciona igual nos dois lados.
- **(o ataque, rodado nos DOIS lados)** a **mesma** rajada de N `POST /login` errados contra `victim@lab` (Intruder/Turbo Intruder com uma lista de senhas). Nos dois lados, **todas** respondem `401` (a rajada não acerta — o `fixed` **não bloqueia**; os `401` saem igual).
- **(a leitura — a PROVA)** comparar os dois logs:
  - **`docker compose logs vulnerable`** → só o **log de acesso genérico** (uma parede de `... "POST /login HTTP/1.1" 401 -`, todas iguais): sem conta, sem classificação de segurança, sem limiar. **O ataque é INVISÍVEL** (indistinguível de N usuários errando a senha; nada que um monitor pegaria).
  - **`docker compose logs fixed`** → as **mesmas** linhas de acesso **MAIS** a **trilha de segurança** (uma linha estruturada por falha: evento, `account=victim@lab`, `ip=...` — **sem a senha**) **MAIS** o **WARNING** de brute-force no limiar. **O ataque é VISÍVEL e investigável.**
- **A "vitória" do atacante no `vulnerable`** é que **NADA** de segurança foi registrado — ninguém sabe que houve um ataque. **A diferença é 100% o logging de segurança** — o login, o ataque, e o log de acesso genérico são idênticos nos dois lados.

### A mecânica da leitura (o CONTRASTE — a ferramenta central; probe de comportamento na Fase 2)

A "ferramenta" fora do Burp é o `docker compose logs` dos dois serviços (o equivalente ao `docker compose exec`/marcador do 36 ou ao `docker compose logs`/"inbox" do 37 — o passo out-of-band que o Burp não faz). Saída **candidata** (placeholder — a Fase 2 captura as linhas reais rodando; ver Item 1):

`docker compose logs vulnerable` (após a rajada) — **cego**:

```
vulnerable-1  | 172.18.0.1 - - [11/Sep/2026 13:50:01] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.18.0.1 - - [11/Sep/2026 13:50:01] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.18.0.1 - - [11/Sep/2026 13:50:01] "POST /login HTTP/1.1" 401 -
...  (N linhas iguais -- nada diz "ataque", "victim@lab", ou "brute-force")
```

`docker compose logs fixed` (após a MESMA rajada) — **vê**:

```
fixed-1  | 172.18.0.1 - - [11/Sep/2026 13:50:01] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 13:50:01,101 INFO security authentication failure account=victim@lab ip=172.18.0.1
fixed-1  | 172.18.0.1 - - [11/Sep/2026 13:50:01] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 13:50:01,150 INFO security authentication failure account=victim@lab ip=172.18.0.1
...
fixed-1  | 2026-09-11 13:50:01,503 WARNING security possible brute-force against victim@lab from 172.18.0.1 (5 failures)
...
```

**Mecânica (a explicar no WALKTHROUGH, do zero):** o `vulnerable` só tem o **log de acesso** do Werkzeug (transporte — método/status/IP), que **não** carrega a conta (o email vai no corpo) nem classifica o `401` como evento de segurança nem agrega. O `fixed` **acrescenta** um **log de segurança** (um logger dedicado que emite uma linha estruturada por falha) e um **contador** por conta que, no limiar, emite o **WARNING**. **O IP** vem de `request.remote_addr` — na topologia Docker isso costuma ser o **gateway da rede do container** (ex.: `172.18.0.1`); o ponto didático é que **o campo existe** (o log registra a **origem**), não o valor exato (numa app real atrás de um proxy, honraria `X-Forwarded-For` — mencionar de leve, **sem** virar 2ª preocupação). **A forma exata (formato/limiar/aparição no `docker compose logs`) a CONFIRMAR rodando** (Item 1) — se o contraste não for palpável, ajustar a config de logging dentro do escopo travado e **provar**; **se NADA reproduzir, PARAR e avisar** — **NÃO inventar** as linhas de log.

### Prova de isolamento (o que traça a diferença PURO ao logging)

- **Login legítimo + login falho isolado, IDÊNTICOS nos dois lados:** `200` pra a senha certa, `401` pra uma errada — **igual** no `vulnerable` **e** no `fixed`. A **feature (e o log de acesso genérico) é idêntica**.
- **A rajada de brute-force:** no `vulnerable`, o `docker compose logs` **não mostra nada de segurança** (só os `401` genéricos); no `fixed`, mostra a **trilha estruturada + o WARNING**. A diferença é **100% o logging de segurança** no caminho da falha — o resto (login, `401`, log de acesso) é idêntico. **Cravar:** não há o que "consertar" no login; o mesmo login, com o log de segurança acrescentado, deixa o ataque **visível**. **O logging É a diferença.**

---

## O código — o coração no LOGGING do caminho da falha (candidatos)

O fio condutor: **o login NÃO muda entre os lados; o logging de segurança no caminho da falha muda.** O `POST /login`, o `init_db`, o seed e o `GET /` têm a **mesma** forma nos dois lados — só o **caminho da falha de autenticação** (o ramo do `401`) ganha, no `fixed`, a linha estruturada + o contador + o WARNING.

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma que o contraste dos logs é palpável (Item 1), captura os dois `docker compose logs` reais, e PROVA a demonstração rodando.**

### `vulnerable/app.py` — o caminho da falha NÃO registra nada de segurança (candidato)

```python
import os
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login {email, password}. Then run a burst of failed logins and compare "
                "`docker compose logs vulnerable` with `docker compose logs fixed`. Work from "
                "Burp Repeater / Intruder.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Parameterized query + werkzeug hash check: the login logic is CORRECT and IDENTICAL to the
    # fixed side. No SQL injection, no bypass. Wrong password -> 401, exactly as it should.
    row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return jsonify({"authenticated": True})
    # VULNERABLE: the authentication FAILURE path records NOTHING security-relevant. A wrong
    # password IS a security event -- someone failed to authenticate as `email` from
    # `request.remote_addr` -- but the app emits no security log line. All that survives is
    # Werkzeug's generic HTTP access line ("POST /login" 401), which carries no account (the email
    # is in the body, not the URL), does not classify the 401 as an authentication failure, and
    # does not aggregate: a 20-request brute-force looks exactly like 20 users mistyping. The
    # attack leaves no security trail -- it is invisible AS AN ATTACK: nothing is logged, so
    # nothing can alert, and a responder or forensic analyst later has nothing to reconstruct.
    # Fix: emit a structured security event on this path, and WARN on a burst. See fixed/, DIFF.md.
    return jsonify({"authenticated": False}), 401


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        """
    )
    # Seed dummy lab users, passwords stored with a DECENT salted hash (werkzeug's default KDF) --
    # NOT to study password storage (that is crypto-weak-hash), just so the ONLY difference between
    # the two sides is the security logging. The brute-force targets victim@lab; its real password
    # is NOT in the attacker's wordlist, so the burst never succeeds. Dummy data (CLAUDE.md §8).
    seed = [("victim@lab", "victim-lab-pw"), ("user@lab", "user-lab-pw")]
    for email, pw in seed:
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                     (email, generate_password_hash(pw)))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    # threaded=False, kept IDENTICAL on both sides so the only difference is the logging, not the
    # server model. (On the fixed side the failure counter is global mutable state; serving one
    # request at a time keeps it deterministic under a burst. Flask defaults to threaded=True, so
    # this is set explicitly. Confirm the counter's behavior under the burst in Phase 2.)
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, threaded=False)
```

### `fixed/app.py` — o caminho da falha registra o evento estruturado + contador + WARNING (candidato)

Muda **só** o **caminho da falha de autenticação** (o ramo do `401`): acrescenta o logger de segurança, o contador por conta, e o WARNING no limiar. Todo o resto (`GET /`, a query/hash-check do login, `init_db`, o seed, o server model) é **idêntico** ao `vulnerable`.

```python
import os
import logging
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")

# How many consecutive failures against one account raise a brute-force WARNING (Item 2).
BRUTE_FORCE_THRESHOLD = 5

# In-memory per-account failure counter: email -> consecutive failures. Ephemeral lab state, like
# session-fixation's SESSIONS dict. Reset on a successful login. Dummy data (CLAUDE.md §8).
FAILURES = {}

# A dedicated SECURITY logger, separate from Werkzeug's generic HTTP access log. It writes
# structured, timestamped lines to the container's output (captured by `docker compose logs`),
# legible to a human and parseable by a machine (a SIEM). A dedicated logger + handler is used so
# this does NOT touch Werkzeug's logger -- the generic access log must keep appearing on BOTH
# sides, so the contrast is "security-absent vs security-present", not "no-log vs log" (Item 1).
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
security_log = logging.getLogger("security")
security_log.setLevel(logging.INFO)
security_log.addHandler(_handler)
security_log.propagate = False


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login {email, password}. Then run a burst of failed logins and compare "
                "`docker compose logs vulnerable` with `docker compose logs fixed`. Work from "
                "Burp Repeater / Intruder.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # IDENTICAL login logic to the vulnerable side: parameterized query, werkzeug hash check.
    row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        FAILURES.pop(email, None)              # a success clears the account's failure streak
        return jsonify({"authenticated": True})
    # FIXED: record the FACT of the authentication failure as a structured SECURITY event --
    # the event, the targeted account, the source IP, the timestamp -- and NEVER the SECRET (the
    # attempted password is not logged). This does NOT block the attempt: no lockout, no
    # rate-limit -- the login still returns 401 and the attacker may keep trying. A09 is about
    # VISIBILITY (detection), not prevention. After a burst against one account, WARN loudly.
    ip = request.remote_addr
    security_log.info("authentication failure account=%s ip=%s", email, ip)
    FAILURES[email] = FAILURES.get(email, 0) + 1
    if FAILURES[email] == BRUTE_FORCE_THRESHOLD:
        security_log.warning("possible brute-force against %s from %s (%d failures)",
                             email, ip, FAILURES[email])
    return jsonify({"authenticated": False}), 401


# init_db() and the __main__ block are IDENTICAL to vulnerable/ (same schema, same seed, same
# threaded=False server model) -- the ONLY difference between the two apps is the logging above.
```

- **O CONTRASTE PRINCIPAL é o ramo do `401`:** no `vulnerable`, `return jsonify(...), 401` **e nada mais**; no `fixed`, a **linha de segurança** + o **contador** + o **WARNING** no limiar, e **então** o mesmo `401`. Esse é o eixo do átomo.
- **O tipo de diff é ATÍPICO — OBSERVABILIDADE ACRESCENTADA** (ver "O fix e o tipo de diff").
- **Item 1 (probe):** confirmar rodando que as linhas de segurança **aparecem** no `docker compose logs fixed` e que o **log de acesso genérico do Werkzeug aparece nos dois lados** (o logger dedicado + `propagate = False` é o candidato pra não mexer no Werkzeug — provar).
- **Item 7 (candidato):** o `fixed` loga a **falha** + o **WARNING**; **não** loga o sucesso (mantém o `fixed` mínimo). Uma trilha completa também logaria sucessos — vira **uma frase** na nota do DIFF, não código.

### `requirements.txt` — IDÊNTICOS nos dois lados (candidato)

```
# vulnerable/requirements.txt   E   fixed/requirements.txt  (mesmo conteúdo)
Flask==3.0.0
```

**Os requirements são IDÊNTICOS** — o delta é o **logging de segurança no `app.py`** (o `fixed` importa e usa o `logging` da **stdlib**), **NÃO** uma dependência. `logging`, `sqlite3`, `os` são **stdlib**; `werkzeug` (o hash de senha) **vem com o Flask**. **Nada a instalar a mais no `fixed`** — o fix é código (observabilidade), não uma lib. (Se a Fase 2 confirmar que nada além do Flask é preciso, os dois `requirements.txt` ficam byte-idênticos.)

---

## O fix e o tipo de diff

**Fix:** **acrescentar o log de segurança que não existe** — no caminho da falha de autenticação, emitir uma **linha estruturada por falha** (o FATO: evento, conta, IP, timestamp) e, após um **limiar** de falhas consecutivas na mesma conta, um **WARNING** de brute-force. Tipo de diff **ATÍPICO**: **não** é lógica-de-negócio-diferente (como o `pickle`→`json` do 20), **não** é uma flag (como o `debug` do 33), **não** é versão-de-dependência (como o bump do 36). É **OBSERVABILIDADE ACRESCENTADA** — o **mesmo comportamento** (o login rejeita a senha errada com `401`, igual), agora **VISÍVEL** (a rejeição vira um evento de segurança registrado). O diff **adiciona** linhas (o logger + o contador + o ramo enriquecido do `401`); **não altera** o comportamento do login.

Diff colável (candidato — a Fase 2 gera o real):

```diff
 import os
+import logging
 import sqlite3
 from flask import Flask, request, jsonify
 from werkzeug.security import generate_password_hash, check_password_hash

 app = Flask(__name__)
 DB_PATH = os.environ.get("DB_PATH", "lab.db")
+
+BRUTE_FORCE_THRESHOLD = 5
+FAILURES = {}                 # email -> consecutive failures (in-memory; reset on success)
+
+_handler = logging.StreamHandler()
+_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
+security_log = logging.getLogger("security")
+security_log.setLevel(logging.INFO)
+security_log.addHandler(_handler)
+security_log.propagate = False
 ...
     if row and check_password_hash(row["password_hash"], password):
+        FAILURES.pop(email, None)              # a success clears the streak
         return jsonify({"authenticated": True})
+    # Record the FACT (event, account, IP, timestamp) -- NEVER the attempted password.
+    ip = request.remote_addr
+    security_log.info("authentication failure account=%s ip=%s", email, ip)
+    FAILURES[email] = FAILURES.get(email, 0) + 1
+    if FAILURES[email] == BRUTE_FORCE_THRESHOLD:
+        security_log.warning("possible brute-force against %s from %s (%d failures)",
+                             email, ip, FAILURES[email])
     return jsonify({"authenticated": False}), 401
```

**O CONTRASTE é o LOGGING no caminho da falha** (+ o contador/alerta). **Nenhuma** linha da **lógica de autenticação** muda (a query, o hash-check, o `200`/`401` são idênticos).

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é a AUSÊNCIA DE LOG DE SEGURANÇA (A09), NÃO um bug no login.** O login **funciona** e é **IDÊNTICO** nos dois lados (mesma query parametrizada, mesmo `check_password_hash`, mesmo `200`/`401`); ele só é **cego** ao ataque — o caminho da falha não deixa rastro. O diff **isola o LOGGING**, não a autenticação. **Prova de isolamento:** a mesma rajada, o `docker compose logs vulnerable` cego (só `401` genéricos) vs o `docker compose logs fixed` com a trilha + o WARNING — a diferença é **100% o logging**.
2. **NOTA-ENQUADRAMENTO "não é rate-limiting" (honestidade-em-camadas — CRÍTICA, sem virar o fix).** Enquadrar assim, explicitamente:
   - **(a) Nomear a intuição.** Um leitor pensa: *"então trava a conta / faz throttle por IP depois de N tentativas."*
   - **(b) Reconhecer que é VERDADE — e é defense-in-depth.** Rate-limiting/lockout é uma defesa **legítima e desejável** contra brute-force. Você quer **as duas** (prevenção **e** detecção).
   - **(c) MAS é PREVENÇÃO, ORTOGONAL a este átomo.** O `fixed` **DETECTA e REGISTRA**; **não BLOQUEIA** (os `401` continuam). A09 é **VISIBILIDADE**. Adicionar rate-limit **mudaria a lição** pra "faltou trava" (uma falha de desenho/prevenção), matando a lição do A09.
   - **(d) Os dois são VERDADEIROS e não se anulam.** Um leitor que saia daqui achando "o fix é rate-limiting" **perdeu** a lição: teria **bloqueado este** ataque mas continuado **cego** ao próximo (e a tudo que a trava não pega). **Cravar:** o eixo é a **VISIBILIDADE**; rate-limit é o complemento honesto, não a causa **deste** átomo. *(Mesma honestidade-em-camadas das notas-armadilha do 31 (o salt)/36 (o `safe_load`)/37 (uso-único/expiração): a defesa nomeada tem valor, mas não é o fix de causa deste átomo.)* **CURTA.**
3. **NOTA "não logar o segredo" (o anti-padrão OPOSTO — também A09).** O log correto registra o **EVENTO** (falha, conta, IP, timestamp), **NUNCA** a senha tentada / tokens / PII. Logar o segredo transforma o log num **vazamento** (o log é lido por muitos, replicado, retido) — é a **outra** face do A09. **Cravar o "logar o FATO, não o SEGREDO".** (No código: a linha de segurança tem `account=` e `ip=`, e **não** tem `password=`.)
4. **A PROVA é a AUSÊNCIA / o contraste.** Diferente de todo átomo anterior (onde a prova era algo **aparecendo** — um marcador, um dado, um takeover), aqui a prova é o **mesmo ataque** produzindo um log **cego** (`vulnerable`) e um log **que vê** (`fixed`). A "vitória" do atacante no `vulnerable` é que **nada** foi registrado. *(Uma trilha de auditoria completa também logaria os **sucessos** de login, não só as falhas — mencionar en passant, sem virar escopo.)*
5. **Impacto (honesto — sem overclaim).** Um ataque roda **SEM SER DETECTADO** — resposta a incidente e forense ficam **cegas**; o A09 é "quanto tempo até você saber que foi invadido" (relatórios reais falam em **meses** de dwell time). **UMA frase de consequência:** no mundo real, uma dessas tentativas eventualmente **acerta**, e sem log **ninguém investiga** — **SEM** mover o foco pra o takeover (a lição é a **cegueira**, não o comprometimento). **Sem foreshadow.**

---

## Biblioteca / stack

- **`vulnerable/` e `fixed/`: Flask + stdlib.** `logging`, `sqlite3`, `os` são **stdlib** (não vão no requirements); `werkzeug.security` (o hash de senha) **vem com o Flask**. A "vuln" vive na **ausência** de uso do `logging` no `vulnerable` (e o fix é **usá-lo** no `fixed`) — não numa dependência.
- **Os `requirements.txt` são IDÊNTICOS** nos dois lados (candidato: só `Flask==3.0.0`). O delta é o **logging no `app.py`**. **Contraste com o `cve-demo` (36)** (onde o diff era **uma linha no `requirements.txt`**, a versão da lib): aqui o `requirements.txt` é idêntico, e o diff é **código de observabilidade** no `app.py`.
- **SQLite embutido** (Nota 4) pros **usuários**; **dict em memória** pro **contador** (só no `fixed`). **SEM** ORM, `requests`, Postgres, MongoDB, ou 2ª dependência. `CLAUDE.md` §3.6.
- **O Flask (e qualquer dep) em versão ATUAL** — **sem** CVE "de brinde" (`CLAUDE.md` §8.5). `Flask==3.0.0` casa com os irmãos; confirmar que instala.
- **SEM SAÍDA B clássica.** A ausência de log **é** a "vuln"; não há uma ferramenta padrão que "resiste" ao ataque (como uma query parametrizada resistiria à SQLi). O `logging` é a ferramenta **certa** (o fix), não um default que por acaso resiste. **O probe é o CONTRASTE ser palpável no `docker compose logs`** (Item 1). **NÃO inventar uma Saída B** — declarar que não há.

---

## §8 / isolamento — o app em loopback, dados dummy, nada destrutivo

- **Bind só `127.0.0.1`** (8038/8138) no `docker-compose.yml` (`CLAUDE.md` §8.1). SQLite local ao container, efêmero.
- **Usuários/senhas dummy** (`victim@lab`/`user@lab`, senhas de lab óbvias), hasheadas decentemente. **Nada real** (§8.3). Sem credenciais reais, sem dados de cliente.
- **Sem código malicioso** (§8.4): o "ataque" é uma **rajada de `POST /login`** com senhas erradas de uma lista de lab — nada destrutivo, nada de rede/C2. A rajada **não acerta** (B1). O impacto é **cegueira**, não RCE/takeover.
- **Banner de aviso** (§8.2) no README (PT+EN) e no `GET /` JSON.

---

## WALKTHROUGH — abertura seca; Burp + docker logs; DENSO EM DEFINIÇÕES; ATÍPICO; headers PT traduzidos

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (uma app com login) e a falha (o caminho da falha de autenticação **não registra nada de segurança**, então um brute-force passa invisível). Trilha **Burp (Repeater/Intruder) + `docker compose logs`**: a rajada é HTTP, a prova é o **contraste dos dois logs**. **SEM browser.**

**Abertura (candidato — plantar a lição, seco):**

> *A app tem uma feature banal: login. `POST /login` com um email e uma senha, e ela responde `200` se a senha bate ou `401` se não bate. O login está correto — query parametrizada, senha hasheada, `401` pra senha errada. Agora imagine um atacante martelando essa conta com senha atrás de senha — um brute-force. O que a app registra sobre isso? No `vulnerable`, nada de segurança: cada `401` é silencioso, e o único rastro é o log de acesso HTTP genérico, que não sabe qual conta foi mirada nem que aquilo foi um ataque. Vinte tentativas de invasão parecem vinte usuários errando a senha. O ataque acontece e ninguém vê. A prova deste átomo não é algo aparecendo — é o contraste entre dois logs: o do `vulnerable`, cego, e o do `fixed`, que registra cada falha e grita "brute-force" quando elas se acumulam.*

Beats (molde do 36/37 — abertura seca, seções numeradas `## 1..N`; a rajada no Burp + a leitura no `docker compose logs`; **sem browser**):

1. **Context.** A feature: `GET /` de aviso + `POST /login` (`200`/`401`). **Definir na estreia (REQUISITO DIDÁTICO — do zero):** **brute-force/credential stuffing** (tentar muitas senhas/credenciais contra uma conta), **evento de segurança** (uma ocorrência que a segurança quer saber — a falha de autenticação), **log de segurança/trilha de auditoria** (QUEM/O QUÊ/QUANDO/DE ONDE), **log estruturado** (campos claros pra humano e máquina/SIEM), **detecção vs prevenção** (VER vs BLOQUEAR — A09 é ver), **log de ACESSO vs log de SEGURANÇA** (transporte genérico vs eventos que importam com contexto), **por que não logar o segredo** (a senha não vai no log). Isto é **A09 — Security Logging and Monitoring Failures** — a categoria sobre **saber** que um ataque aconteceu. Portas: `vulnerable` `127.0.0.1:8038`, `fixed` `127.0.0.1:8138`. Trilha: **Burp (Repeater/Intruder)** + `docker compose logs`; sem browser. Cravar: o login está **correto**; o que falta é o **registro** do ataque.
2. **Spot the bug.** Mostrar o `vulnerable/app.py` — o ramo do `401` no `login()`: `return jsonify({"authenticated": False}), 401` **e nada mais**. A pergunta de auditoria **não** é "o login está errado?" (não está) — é **"quando isto retorna `401`, o que o sistema REGISTRA sobre o evento?"** Aqui: nada de segurança. Só o log de acesso do Werkzeug sabe que um request aconteceu — e ele não sabe **qual conta** nem que aquilo foi um **ataque**. Foreshadow do fix: emitir um **evento de segurança estruturado** nesse caminho + um **WARNING** no limiar.
3. **Baseline — a feature funcionando.** `POST /login {victim@lab, victim-lab-pw}` → `200 {"authenticated": true}`. `POST /login {victim@lab, senha-errada}` → `401 {"authenticated": false}`. **Idêntico nos dois lados.** (Deixa claro o "normal" antes do ataque — e que um `401` isolado é rotina, não alarme.)
4. **A demonstração (a rajada no Burp + o contraste dos logs — a prova).**
   - **4a — rodar a rajada de brute-force** contra o `vulnerable` (`:8038`): N (≥ 20) `POST /login {victim@lab, <cada senha de uma lista>}` via **Intruder/Turbo Intruder** (ou uma rajada de requests). **Todas** respondem `401` (a rajada não acerta). **Definir brute-force aqui** se ainda não foi.
   - **4b — ler o log do `vulnerable` (cego):** `docker compose logs vulnerable` → só o **log de acesso genérico** (uma parede de `"POST /login" 401`): sem conta, sem "falha de autenticação", sem limiar. **O ataque é INVISÍVEL.** Cravar: isto **não** é "log-nenhum" — é o log na **altitude errada** (transporte, não segurança); ele não distingue o ataque do ruído.
   - **4c — rodar a MESMA rajada** contra o `fixed` (`:8138`).
   - **4d — ler o log do `fixed` (vê):** `docker compose logs fixed` → as **mesmas** linhas de acesso **MAIS** a **trilha de segurança** (uma linha estruturada por falha: evento, `account=victim@lab`, `ip=...` — **sem a senha**) **MAIS** o **WARNING** de brute-force no limiar. **O ataque é VISÍVEL e investigável.** Mostrar os dois logs **lado a lado** — a prova é a **COMPARAÇÃO**.
   - **§8 (cravar):** lab **isolado** (bind só `127.0.0.1`); a rajada é de senhas de lab erradas, nada destrutivo, nada de rede. **A rajada nem precisa acertar** — o ponto é **VER que ela aconteceu**.
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'" (os cinco).
6. **Impact (honesto — sem overclaim).** Um ataque roda **sem ser detectado**; resposta a incidente e forense ficam cegas — o A09 é "quanto tempo até você saber que foi invadido". **UMA frase:** no mundo real uma dessas tentativas eventualmente acerta, e sem log ninguém investiga — **sem** mover o foco pra o takeover.
7. **Why the fix works (porta 8138).** O **mesmo** ataque, agora **VISÍVEL**: a trilha estruturada + o WARNING deixam **detectar** e **investigar** (qual conta, qual origem, quando, quantas). **Sem travar o login** — os `401` continuam saindo: **detecção, não prevenção**. **Prova de isolamento:** o login (e o log de acesso genérico) é **idêntico** nos dois lados; só o **logging de segurança** separa. **A lição do diff:** o fix é **acrescentar a observabilidade** — **não** bloquear o ataque (rate-limit, nota de honestidade-em-camadas) nem logar a senha (nota "logar o FATO, não o SEGREDO"). (Forward pro DIFF.)

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). As linhas de log são **placeholders** da execução real capturada na Fase 2.

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5) — os CINCO

Isola a causa e desmonta os mal-entendidos vizinhos:

- **(a) NÃO é rate-limiting/lockout.** O `fixed` **DETECTA e REGISTRA** o brute-force; **não o BLOQUEIA** (os `401` continuam saindo — o atacante pode seguir tentando). A09 é **visibilidade**, não prevenção. Travar seria uma defesa **complementar** (defense-in-depth), **legítima mas ortogonal** — adicioná-la mudaria a lição pra "faltou trava". **O furo é a CEGUEIRA, não a falta de trava.**
- **(b) NÃO é logar o segredo.** O fix loga o **EVENTO** (falha, conta, IP, timestamp), **NUNCA** a senha tentada. Logar o segredo é o **anti-padrão OPOSTO** (um vazamento via log — **também** A09). **Logar o FATO, não o SEGREDO.**
- **(c) NÃO é um bug no login.** O login **funciona** e é **idêntico** nos dois lados (query parametrizada, `check_password_hash`, `200`/`401`); ele rejeita a senha errada corretamente. A falha é ele ser **CEGO** ao ataque — não deixar **rastro** do evento de segurança.
- **(d) NÃO é como os outros átomos (a prova NÃO é um marcador/dado aparecendo).** Em todo átomo anterior, você prova a vuln fazendo **algo acontecer**. Aqui a prova é a **AUSÊNCIA** de rastro no `vulnerable` **vs** a trilha no `fixed` — o **contraste** de dois logs sob o mesmo ataque. A "vitória" do atacante no `vulnerable` é que **nada** foi registrado.
- **(e) NÃO é sobre PARAR o brute-force.** A rajada **nem precisa acertar** uma senha (B1 — todas erram). O ponto **não** é impedir o ataque; é **VER** que ele aconteceu. (Se acertasse, o foco deslizaria pra "senha fraca / faltou trava" — B2, descartado.)

**O que É (prova):** um evento de segurança (uma rajada de falhas de autenticação contra uma conta) **acontece e não é registrado**; o `vulnerable` fica **cego** (só o log de acesso genérico), o `fixed` **vê** (a trilha estruturada + o WARNING). A correção é **gerar o log de segurança que falta** — logando o **FATO** (evento, conta, IP), **nunca** o segredo, e **sem** bloquear o ataque (detecção, não prevenção).

---

## Impacto honesto

**Cegueira operacional — um ataque (e, no mundo real, um comprometimento eventual) roda SEM SER DETECTADO.** Sem o log de segurança, a rajada de brute-force não aparece em nenhum lugar que a monitoração pegaria: ninguém é alertado, o time de resposta a incidente não tem o que investigar, e o forense não tem trilha pra reconstruir **o quê**, **quando**, **de onde**. O A09 é literalmente **"quanto tempo até você saber que foi invadido"** — e relatórios reais medem esse **dwell time** (o tempo entre o comprometimento e a detecção) em **meses**. **UMA frase de consequência:** no mundo real, uma dessas tentativas de brute-force eventualmente **acerta**, e sem log **ninguém investiga** — o teto do dano é **você não saber**. **NÃO inflar** pra RCE/takeover como se fosse a lição (a lição é a **cegueira**): o `POST /login` que acerta seria a vuln de **outra** categoria (senha fraca / falta de trava) — aqui o foco é a **VISIBILIDADE**. A classe "logging/monitoring failures" tem **outras faces** (logs sem alerting, logs que vazam segredo, logs sem integridade/retenção) — **descrição de UMA linha da classe, sem** modelar nem nomear átomo/variante futura; na dúvida, mandar o aluno aprofundar no OWASP / na PortSwigger Academy. **Sem foreshadow.**

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY JSON** (o alvo é um endpoint de login REST puro, e a prova é texto de log — decisão de forma óbvia pela categoria, como o `crypto-weak-hash` (31) / `weak-password-reset` (37)). Garantir que a **ÚNICA** vuln é a **ausência de log de segurança**:

- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (molde do 31/37) + no **README**.
- **O login é código correto e da mesma forma nos dois lados** (o baseline funciona igual); **sem** injection (query parametrizada), **sem** IDOR, **sem** falha de hash de senha (werkzeug decente), **sem** rate-limit adicionado, **sem** senha logada.
- **O `fixed` muda SÓ o logging de segurança no caminho da falha** (a linha estruturada + o contador + o WARNING). O resto do `app.py` é **idêntico**.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é **ACRESCENTAR OBSERVABILIDADE** (o log de segurança), **NÃO** bloquear o ataque (rate-limit — nota-enquadramento #2) nem logar o segredo (nota #3); a prova é o **contraste de logs**, não um marcador.

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar.**

- **PortSwigger PRIMEIRO — mas provável ausência de página conceitual limpa.** A PortSwigger Academy organiza o conteúdo por **vuln-classes exploráveis** (SQLi, XSS, SSRF...); **A09 é uma categoria de OBSERVABILIDADE** ("registre e monitore os eventos de segurança"), que a Academy **provavelmente não cobre** com uma página conceitual dedicada — **exatamente a situação do `cve-demo` (36)**, que caiu pro fallback OWASP. **A Fase 2 DEVE buscar por fetch** ("logging" / "monitoring" / "insufficient logging" no `portswigger.net/web-security`); **se houver** uma página conceitual limpa, usá-la; **se não houver**, ir pro fallback.
- **FALLBACK OWASP (provável).** Candidatos a confirmar por fetch: a página do **A09:2021 — Security Logging and Monitoring Failures** no site do OWASP Top 10 (candidato: `https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/`) **como o primer conceitual**, e/ou o **OWASP Logging Cheat Sheet** (candidato: `https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html`) — o guia prático de **o que** logar (e o que **não** logar — a nota "não logar o segredo"). Isto é um **desvio consciente** da fonte-padrão "PortSwigger" do §5 (mesmo padrão do 36, que caiu pro OWASP; e o `CLAUDE.md` §14 já credita OWASP). **AVISAR o mantenedor** explicitamente do desvio, e por quê.
- **Texto do link:** preservar o nome da página em **inglês** também no README PT (`CLAUDE.md` §7).
- **NÃO inventar URL nem grafia** — **confirmar TODAS por fetch na Fase 2**; se não conseguir verificar uma página conceitual limpa, usar o fallback OWASP (A09 / Logging Cheat Sheet) e **avisar o mantenedor**. Se nada verificar, **perguntar ao mantenedor** (`CLAUDE.md` §5).

---

## A trilha e a ferramenta — Burp (rajada) + `docker compose logs` (a prova), sem browser

O "ataque" é uma **rajada HTTP dirigível no Burp** (Repeater/Intruder/Turbo Intruder); a **prova é a leitura dos dois `docker compose logs`** (o passo out-of-band que o Burp não faz — como o `docker compose exec`/marcador do 36 ou o `docker compose logs`/"inbox" do 37). Disciplina (`CLAUDE.md` §3.3):

- **Mostrar o passo a passo no Burp:** a rajada de N `POST /login` errados contra `victim@lab` (Intruder/Turbo Intruder com uma lista de senhas, ou Repeater repetido). Depois, **fora do Burp**, a leitura da prova: `docker compose logs vulnerable` (cego) vs `docker compose logs fixed` (a trilha + o WARNING). **Tudo dirigível por HTTP** (+ `curl`/uma rajada programática como equivalente pra a validação reprodutível).
- **A prova NÃO exige execução client-side** (a prova é **texto de log** no servidor) → **browser NÃO faz parte da trilha** (`CLAUDE.md` §3.3: browser só quando a prova exige — aqui não exige). **SEM trilha browser.**
- **SEM** cracker, **SEM** listener OOB, **SEM** marcador de arquivo. Single-container, tudo local. A única "ferramenta" extra é o `docker compose logs` dos dois serviços — **a leitura do contraste é o coração**.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A09 — Security Logging and Monitoring Failures** (`atoms/A09-logging-failures/`, **NÃO EXISTE — o 38 CRIA**) | ROADMAP lista `logging-failures-demo` em A09; `CLAUDE.md` §4 fixa a pasta abreviada (`logging-failures`, como `A07-auth-failures`/`A06-vulnerable-components`). **Sinalizado** pro mantenedor (o brief propôs também a forma longa). Situar em A09 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow — **atenção redobrada** (tentação de "fechamento"). |
| Topologia | **SINGLE-CONTAINER por lado — SQLite (usuários) + dict (contador, só no `fixed`)** | Molde do `37`/`31`; precisa de estado mas **não** de concorrência (≠ 35). Nota 4. |
| **O CORAÇÃO — o logging** | **`vulnerable`: caminho da falha NÃO loga segurança. `fixed`: linha estruturada por falha + contador + WARNING no limiar.** | A falha é a **ausência de log de segurança** (A09); o fix é **acrescentar a observabilidade**. |
| A forma da PROVA — **TRAVADO (B1)** | **CONTRASTE de dois `docker compose logs`** (`vulnerable` cego vs `fixed` que vê), sob a MESMA rajada | A prova é a **ausência de rastro**, não um marcador. **B2 (a rajada acertar) descartado** — deslizaria pra "senha fraca / rate-limit". |
| Lição-coração | **Um ataque acontece e o app não o registra → invisível. Fix = GERAR o log de segurança (o FATO), NÃO bloquear (rate-limit) nem logar o segredo.** | A09 é a categoria sobre **saber** que os outros nove aconteceram. |
| Contraste central | **vs TODOS os anteriores** (a prova era algo aparecendo; aqui é a ausência) + os três enquadramentos | Não há irmão de "prova por ausência"; o átomo é o atípico. |
| Contraste de apoio | **`36`** (precedente de átomo atípico + voz + fallback OWASP), **`37`/`31`** (molde da app), **`15`** (dict em memória), **`35`** (voz atual), **`01`** (molde) | Publicados; ancoram molde/voz/atipicidade. Sem foreshadow. |
| Tipo de átomo | **API-only JSON** (sem HTML, sem templates, sem browser) | O alvo é um endpoint de login REST puro; a prova é texto de log. |
| Trilha | **BURP (rajada) + `docker compose logs` (prova); sem browser** | A rajada é HTTP; a prova é o contraste dos dois logs (out-of-band, o que o Burp não faz). |
| Flavor — **TRAVADO** | **`POST /login` (o alvo do brute-force) + `GET /` banner JSON** | Cenário canônico de A09. O login é correto; a vuln é a ausência de log. |
| Datastore | **SQLite pros usuários (molde 37/31), dict em memória pro contador (só no `fixed`, molde 15)** | Precisa de estado, não de concorrência. A senha hasheada com werkzeug (não a vuln do 31). |
| Lib / dep | **Flask + stdlib (`logging`/`sqlite3`); `werkzeug` vem com o Flask** | O delta é código (usar o `logging`), **não** dependência. requirements idênticos (≠ 36, que mudou a versão da lib). |
| Limiar do WARNING | **5 falhas consecutivas na mesma conta** (candidato; Item 2) | Baixo pra a rajada cruzar cedo, alto pra não disparar num typo. WARNING uma vez no cruzamento. Confirmar. |
| Formato do log | **`key=value` estruturado via `logging` (timestamp·nível·`security`·evento·`account=`·`ip=`)** (candidato; Item 3) | Legível no `docker compose logs`, parseável por SIEM, paralelo ao `key=value` do 37. Sem a senha. JSON é alternativa. |
| Contador | **dict em memória `FAILURES` por conta; reset no sucesso** (candidato; Item 4) | Molde do 15. Chave por conta (o "N falhas na mesma conta"); a linha registra conta E IP. |
| Não bloquear | **O `fixed` NÃO adiciona rate-limit/lockout** — os `401` continuam | Detecção, não prevenção. Rate-limit é honestidade-em-camadas, não o fix. |
| Não logar o segredo | **A senha tentada NÃO vai no log** — só evento/conta/IP/timestamp | Logar o segredo é o anti-padrão oposto (também A09). Logar o FATO, não o SEGREDO. |
| Fix (eixo) | **Acrescentar o log de segurança (linha por falha + contador + WARNING)** | Tipo de diff ATÍPICO: **observabilidade acrescentada** (mesmo comportamento, agora visível). |
| Impacto | **Cegueira — ataque não detectado; forense sem rastro.** Sem overclaim (não takeover/RCE). | Honesto; o teto é "você não saber". UMA frase de consequência. Sem foreshadow. |
| Theory primer | **PortSwigger primeiro (provável ausência) → fallback OWASP A09 + Logging Cheat Sheet** | A09 é observabilidade; Academy provavelmente não cobre. Confirmar por fetch; avisar o desvio (molde do 36). |
| Título (H1) | **`logging-failures-demo — Missing security logging of authentication failures`** (classe, sem stack) | `CLAUDE.md` §5. Sem "Flask"/"Python"/"`logging`" no H1; o slug já qualifica. Grafia final na Fase 2. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública); **sem** "fecha a fase / completa o Top 10 / último átomo" | `CLAUDE.md` §5 — **atenção redobrada**. Não nomear posição/release/próximos átomos. |
| Portas | **8038 / 8138** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container por lado. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si** (molde do `37`/`31`/`01`, **API-only → SEM `COPY templates`**). Base `python:3.11-slim` (consistência com os irmãos):

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

- `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, threaded=False)` no rodapé do `app.py`; **`init_db()` no `__main__`** cria e semeia o `lab.db` no boot (molde do 37 — sem bind mount, sem seed externo).
- **`-u` (unbuffered) é ESSENCIAL aqui** — as linhas de log (o log de acesso e, no `fixed`, o de segurança) têm que aparecer **na hora** no `docker compose logs` pra a prova ser lida (molde dos irmãos; confirmar no Item 1).

**`docker-compose.yml`** (molde EXATO do `37`/`31`/`01` — dois serviços, **sem** datastore externo, **sem** healthcheck/`depends_on`/rede; apps bind **só** `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8038:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8138:5000"
```

- **§8:** ambos publicam porta **só** em `127.0.0.1`. Sem datastore externo (SQLite embutido), sem rede nomeada.
- **Confirmar na Fase 2** que `./atom up logging-failures-demo` sobe os dois, que o `lab.db` semeia (vítima + segundo usuário), que o baseline (login legítimo/falho isolado) funciona nos dois lados, e que a rajada + os dois `docker compose logs` produzem o contraste (Item 1).

---

## DECISÃO ABERTA pra Fase 2 — o CONTRASTE dos logs ser palpável (o nó técnico; registrar, NÃO travar)

O **contraste dos logs** é **comportamento de plataforma** e deve ser **PROVADO rodando** (**NÃO** é preferência editorial). O eixo está **TRAVADO** (o `vulnerable` não loga segurança; o `fixed` loga o evento estruturado + WARNING, sem bloquear e sem logar a senha); o que confirmar, com o candidato registrado (Item 1):

- **O log de segurança do `fixed` aparece no `docker compose logs`.** Candidato: logger dedicado `security` (`StreamHandler`, `INFO`, `propagate = False`) + `python -u`. **Provar** que as linhas saem.
- **O log de acesso genérico do Werkzeug aparece nos DOIS lados** (o contraste é segurança-ausente vs segurança-presente, **não** log-nenhum vs log). **Provar** que a config de logging do `fixed` **não** o suprime.
- **O formato** (`key=value` vs JSON — Item 3), **o limiar** (candidato 5 — Item 2), **a chave do contador** (por conta — Item 4), **o tamanho/via da rajada** (N ≥ 20; Intruder/Turbo Intruder ou rajada programática — Item 5).
- **A senha NÃO aparece** no log do `fixed`; o `fixed` **NÃO bloqueia** (os `401` continuam).
- **A URL do primer** (PortSwigger provável ausência → fallback OWASP A09 / Logging Cheat Sheet) — **confirmar por fetch**; não inventar; avisar o desvio.

**Protocolo (cravar):** registrar candidato, **rodar**, confirmar; capturar os **dois `docker compose logs` reais** (o `vulnerable` cego, o `fixed` com a trilha + WARNING; a mesma rajada nos dois). **Se o contraste não for palpável**, ajustar a **config de logging** dentro do escopo travado (o que loga o quê) e **PROVAR rodando**. **Se NADA reproduzir de forma legível, PARAR e avisar o mantenedor — NÃO inventar** as linhas de log, o request/response, ou a saída da demonstração.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes de design — exceto onde marcado "DECISÃO ABERTA".

1. **Baseline nos dois lados:** um login legítimo (`200`) e um login falho **isolado** (`401`) funcionam **idêntico** no `vulnerable` **E** no `fixed`. **VALIDAR.**
2. **Usuários semeados:** vítima (`victim@lab`) + segundo (`user@lab`), senhas dummy **hasheadas** com werkzeug (não a vuln do 31). **VALIDAR** que o `lab.db` semeia no boot. A senha real **não** está na lista da rajada.
3. **A DEMONSTRAÇÃO (central — VALIDAR RODANDO / DECISÃO ABERTA):** rodar a rajada de N `POST /login` errados nos dois lados → `docker compose logs vulnerable` **NÃO** mostra evento de segurança (só `401` genéricos), `docker compose logs fixed` mostra a trilha estruturada + o WARNING no limiar. **CAPTURAR os dois logs reais.** **Se o contraste não for palpável, ajustar a config de logging e PROVAR; se NADA reproduzir, PARAR e avisar — NÃO inventar.**
4. **O `fixed` NÃO loga a senha tentada:** confirmar que a senha **não** aparece em nenhuma linha do `docker compose logs fixed`. **VALIDAR.**
5. **O `fixed` NÃO trava o login:** o brute-force continua respondendo `401` (não é bloqueado — detecção, não prevenção). **VALIDAR.**
6. **Uma vuln só / isolamento:** o login é **IDÊNTICO** nos dois lados (mesma query parametrizada, mesmo `check_password_hash`, mesmo `200`/`401`); o **único** diff é o logging de segurança no caminho da falha (+ contador/WARNING no `fixed`). **Sem** SQLi, **sem** rate-limit, **sem** senha logada, **sem** falha de hash. **Confirmar por `diff`** (o resto do `app.py` idêntico; só o ramo do `401` + o setup do logger diferem).
7. **§8:** bind **só** `127.0.0.1` (8038/8138); usuários/senhas **dummy**; nada destrutivo/rede; a rajada é de senhas de lab erradas.
8. **Flask instala limpo; o log vai pro stdout/stderr** (capturado por `docker compose logs`); o `python -u` faz as linhas aparecerem na hora; **o contador se comporta sob a rajada** (candidato `threaded=False` nos dois lados — confirmar).
9. **Primer confirmado por FETCH** (PortSwigger provável ausência → fallback OWASP A09 / Logging Cheat Sheet). **Confirmar por fetch; avisar o mantenedor do desvio da fonte-padrão. Não inventar.**
10. **DECISÃO ABERTA — o contraste dos logs** (seção dedicada): formato/limiar/contador/rajada resolvidos **rodando**; capturar os dois logs. Se não for palpável, **ajustar e PROVAR**; se travar, **PARAR e avisar**.
11. **Diff isola o LOGGING:** o **ÚNICO** delta lógico entre `vulnerable/` e `fixed/` é o logging de segurança (o ramo enriquecido do `401` + o setup do logger + o contador). A **autenticação é idêntica**. **Confirmar por `diff`.**
12. **As notas** (não-rate-limit — honestidade-em-camadas; não-logar-segredo; a-prova-é-a-ausência; impacto) **+ os três enquadramentos** presentes no DIFF/WALKTHROUGH. **VALIDAR** que o átomo demonstra a **VISIBILIDADE** como o eixo (não "faltou trava" nem "senha fraca").

**Bloqueante remanescente:** nenhum de decisão de vuln. **DECISÕES ABERTAS de Fase 2 (probe/forma, não bloqueiam a spec):** o contraste dos logs ser palpável (Item 1); o formato do log (Item 3); o limiar (Item 2); a chave/comportamento do contador (Item 4); o tamanho/via da rajada (Item 5); se o `fixed` loga sucessos (Item 7 — candidato não); a URL do primer por fetch. **Protocolo:** registrar candidato, **rodar**, confirmar; se não reproduzir, ajustar dentro do escopo travado (**o `vulnerable` não loga segurança; o `fixed` loga o evento + WARNING, sem bloquear e sem logar a senha**); se travar de vez, **PARAR e avisar — NÃO inventar** as linhas de log, request/response, saída ou URL.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **ATÍPICO** — a falha **não é explorável** (não há marcador, dado ou takeover); é uma **AUSÊNCIA**. Um brute-force acontece e o `vulnerable` **não o registra**, então fica **invisível**; o `fixed` **loga cada falha** (o FATO — evento, conta, IP, timestamp, nunca a senha) + um **WARNING** no limiar, então fica **visível**. **A prova é o CONTRASTE de dois `docker compose logs`.** **Abrir e fechar** na lição-coração: *o furo é a AUSÊNCIA de log de segurança (A09); o fix é GERAR o log — não bloquear o ataque (rate-limit) nem logar o segredo.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`37` (weak-password-reset) INTEIRO** (o molde quase-exato da app — single-container SQLite, usuários semeados+hasheados, API-only JSON, `GET /`+`POST /login`; aqui o `POST /login` é o alvo do brute-force e o diff é o logging em volta dele; e o `print(..., flush=True)` mostra o padrão de escrever no stdout que o `docker compose logs` lê), **`31` (crypto-weak-hash) INTEIRO** (o mesmo molde single-container SQLite + API-only), **`15` (session-fixation)** (o molde do dict em memória pro estado efêmero — aqui o contador), **`36` (cve-demo) INTEIRO** (o **precedente de átomo atípico** — "mais demonstrativo do que explorável", o fallback OWASP no primer, como estruturar a doc quando não é um exploit clássico), **`35` (voz atual)**, **`01` INTEIRO** (molde canônico single-container Flask + estrutura de doc), esta spec. **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar encenação; **NÃO** copiar arqueologia OWASP; **NÃO** copiar a estrutura antiga do `ATOM-01-SPEC` (a "nota histórica" dele avisa que a trilha browser secundária / "Try it yourself" foram removidas); **headers de seção traduzidos em TODA doc PT** (§7); título = classe sem stack.
- **PONTO PEDAGÓGICO OBRIGATÓRIO (o brief):** o WALKTHROUGH **DEVE** (1) mostrar os **DOIS `docker compose logs`** (o `vulnerable` cego, o `fixed` com a trilha + WARNING) — a prova é o **CONTRASTE**, não um marcador; (2) cravar que a "vitória" do atacante no `vulnerable` é que **NADA** foi registrado; (3) cravar os **três enquadramentos** (não-rate-limit, não-logar-segredo, detecção-vs-prevenção); (4) **definir evento-de-segurança / log-de-acesso-vs-segurança / brute-force / log-estruturado / trilha-de-auditoria DO ZERO** na 1ª ocorrência; (5) mostrar que o **login é IDÊNTICO** nos dois lados (o diff é só o logging). **Sem esses cinco, o átomo não ensina o A09 nem se distingue de "faltou rate-limit / senha fraca".**
- **O ponto técnico frágil é o CONTRASTE ser palpável (riscos #3/#8/#10) — comportamento de plataforma.** Rodar a rajada de verdade e capturar os dois `docker compose logs`, confirmando que o `vulnerable` só tem o acesso genérico e o `fixed` tem a trilha + o WARNING, que a **senha não aparece** no log, e que o `fixed` **não bloqueia**. **Se o contraste não for palpável, ajustar a config de logging dentro do escopo travado e PROVAR; se NADA reproduzir, PARAR e avisar — NÃO inventar** as linhas de log ou a saída.
- **Uma vuln só:** a **única** falha é a **ausência de log de segurança** no caminho da falha de autenticação. O login está **correto** e **idêntico** nos dois lados; **NÃO** modelar SQLi (query parametrizada), **NÃO** modelar senha/hash fraco (seria a vuln do 31), **NÃO** adicionar rate-limit/lockout, **NÃO** logar a senha. O `fixed` muda **SÓ** o logging. **SEM 2ª vuln.**
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é **ACRESCENTAR OBSERVABILIDADE** (o log de segurança), **NÃO** bloquear o ataque (rate-limit — enquadramento #1) nem logar o segredo (enquadramento #2). **Ser honesto** (honestidade-em-camadas): rate-limiting/lockout é uma defesa **verdadeira e necessária** (defense-in-depth), mas é **prevenção**, ortogonal — os dois não se anulam, e um leitor que saia achando "o fix é rate-limiting" **perdeu** a lição do A09 (a VISIBILIDADE).
- **Contraste com TODOS os anteriores (cravar):** não há irmão de "prova por ausência"; a prova aqui é o **contraste de logs**, não algo aparecendo. Ancorar citando publicados (o marcador do 36, o takeover do 37, o dado do 01) **como contraste** — o átomo é o atípico. Citar publicados (01–37) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5 + o brief):** brute-force/credential stuffing, evento de segurança, log de segurança/trilha de auditoria, log estruturado, detecção vs prevenção, log de ACESSO vs log de SEGURANÇA, por que não logar o segredo. **DO ZERO** — o átomo é denso de vocabulário de observabilidade.
- **A09 sem arqueologia:** situar em **A09 — Security Logging and Monitoring Failures**, explicar **por que** (a falha está na **ausência do registro do evento** — o app não vê o ataque —, não num controle de acesso, injeção, ou trava ausente), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 candidato `logging-failures-demo — Missing security logging of authentication failures`. "Flask"/"Python"/"`logging`" no corpo, não no H1 (o slug já qualifica). Grafia final na Fase 2 (alternativas: "Insufficient security logging of authentication failures" / "Missing security logging and monitoring").
- **Política de referência cross-átomo:** OK citar **37/31** (molde), **15** (dict), **36** (precedente atípico/voz/fallback), **35** (voz), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria/variante futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase, "fecha a fase", "completa o Top 10", "último átomo", "abre A09", ou outras faces futuras de A09. **Manter as proibições genéricas.** **Esta spec é pública — nasce limpa de foreshadow (atenção redobrada — este átomo é a tentação máxima de "fechamento").**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`logging-failures-demo — Missing security logging of authentication failures`, grafia exata confirmável na Fase 2). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (log, logging, security event, audit trail, access log, structured log, brute-force, credential stuffing, SIEM, payload, detection, prevention, rate-limiting, lockout, defense-in-depth, dwell time) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): **PortSwigger primeiro** (provável ausência de página conceitual — A09 é observabilidade) → **fallback OWASP A09 + o Logging Cheat Sheet** — **avisar o mantenedor do desvio da fonte-padrão** (molde do 36); nome da página em inglês no PT. **Confirmar TODAS as URLs por fetch na Fase 2** — não inventar.
- **A trilha é Burp (rajada) + `docker compose logs` (prova):** a rajada de N `POST /login` errados no Intruder/Turbo Intruder (ou Repeater repetido) → a leitura dos dois `docker compose logs` (o `vulnerable` cego, o `fixed` com a trilha + WARNING). **SEM** browser (a prova é texto de log, não uma tela).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, no padrão das linhas anteriores (candidato — ajustar na Fase 2): `` Added atom 38: `logging-failures-demo` — Missing security logging of authentication failures: a minimal login API rejects wrong passwords correctly (200/401), but the vulnerable side records NOTHING security-relevant on the failure path — a brute-force burst leaves only Werkzeug's generic HTTP access log, which carries no account, no event classification and no aggregation, so the attack is invisible; the fixed side adds a structured security log line per failure (event, target account, source IP, timestamp — never the attempted password) and a brute-force WARNING past a threshold, without blocking the login (detection, not prevention); the proof is not a marker appearing but the CONTRAST between `docker compose logs vulnerable` (blind) and `docker compose logs fixed` (the trail + the alert) under the same burst (A09 Security Logging and Monitoring Failures, CWE-778 Insufficient Logging, CWE-223 Omission of Security-relevant Information — confirm). `` **Confirmar o CWE por fetch na Fase 2** (candidatos: **CWE-778** "Insufficient Logging" — o mapping A09 mais direto; **CWE-223** "Omission of Security-relevant Information"; e, pra a nota "não logar o segredo", **CWE-532** "Insertion of Sensitive Information into Log File" como o anti-padrão oposto; não inventar). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 38 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir o baseline (login legítimo/falho isolado idêntico nos dois lados) → a rajada de brute-force nos dois lados → capturar os dois `docker compose logs` (o contraste) → o que a vuln NÃO é → o `fixed` (visível, sem travar, sem logar a senha). Portas host podem não ser alcançáveis do sandbox — usar o fallback `docker compose exec` + dirigir a rajada de dentro do container (`python http.client`/`curl` em loop), e ler os dois logs via `docker compose logs`. **Sem** browser (a prova é texto de log).
- **Commits sem trailer `Co-Authored-By`** (a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8038` (vulnerable), `127.0.0.1:8138` (fixed). Bind **só** `127.0.0.1` (§8). Single-container por lado (2 serviços, SQLite embutido pros usuários, dict pro contador no `fixed`, sem datastore externo).
- Se houver dúvida sobre o contraste dos logs ser palpável, o formato/limiar/contador, o tamanho/via da rajada, se o `fixed` loga sucessos, a URL do primer por fetch, o CWE, o nome de pasta A09 (longo vs abreviado), ou se o contraste não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**). **Candidato, se você quiser um pointer de recall reusável** (útil pra este átomo e pra futuros que toquem observabilidade/detecção) — boa parte fica **registrada nesta spec commitada** (a regra desaconselha duplicar o que o repo grava). O que **justificaria** uma memória é a parte **não-repo, de ambiente/ferramenta**, e **só depois de confirmada rodando na Fase 2** (agora seria candidato não-verificado):

- **`a09-logging-proof-by-log-contrast`** (candidato — **gravar só após provar na Fase 2**) — *"O átomo `logging-failures-demo` (38, A09) é ATÍPICO: a falha não é explorável (sem marcador/dado/takeover) — é uma AUSÊNCIA. A prova é o CONTRASTE de dois `docker compose logs` sob a mesma rajada de brute-force: o `vulnerable` só tem o log de acesso genérico do Werkzeug (cego); o `fixed` acrescenta uma linha de segurança estruturada por falha (evento, account, ip — NUNCA a senha) + um WARNING no limiar (candidato 5 falhas/conta). Detecção, não prevenção (o `fixed` NÃO bloqueia; os 401 continuam). Molde single-container SQLite do 37/31 + dict em memória pro contador (molde 15). Logger dedicado (`security`, StreamHandler, propagate=False) pra não suprimir o log de acesso do Werkzeug — o contraste é segurança-ausente vs segurança-presente, não log-nenhum vs log. Primer caiu pro fallback OWASP A09/Logging Cheat Sheet (Academy não cobre observabilidade), como o 36."* — tipo `reference`. **Confirmar os detalhes (formato/limiar/aparição no `docker compose logs`) rodando ANTES de gravar.**

**Ressalva:** só vale gravar se você quiser esse pointer pra futuros átomos de observabilidade/detecção; e **só depois de a Fase 2 provar a mecânica** (agora é candidato). Senão, já está aqui na spec. Sua decisão. *(Ortogonal: na Fase 2, vale o padrão de validar via `docker compose exec` — dirigir a rajada de dentro do container se as portas host não forem alcançáveis do sandbox — e commits sem o trailer `Co-Authored-By`.)*
