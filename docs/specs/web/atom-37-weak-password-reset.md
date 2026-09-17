# Spec — Átomo 37: `weak-password-reset`

> Documento de especificação para o Claude Code implementar o átomo `weak-password-reset` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo **REAPROVEITA uma categoria que JÁ EXISTE — A07 (Identification and Authentication Failures)**: a pasta `atoms/A07-auth-failures/` **já está no disco** (hospeda o `session-fixation`, 15) e **NÃO deve ser recriada** (nome confirmado contra o `CLAUDE.md` §4 e o padrão do irmão `session-fixation` — ver Nota de planning 1). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER** — dois serviços (`vulnerable` + `fixed`), cada lado **um container Flask** com um **SQLite embutido** (`lab.db`) semeado no boot, molde do `crypto-weak-hash` (31) / `sqli-union-basic` (01). Precisa de estado (usuários + tokens de reset), mas **NÃO** de concorrência (diferente do `race-condition-basic`, 35) — então SQLite embutido single-container é o **candidato recomendado**; a alternativa (Postgres multi-container, molde do 22/35) fica registrada como decisão-aberta de Fase 2, provavelmente desnecessária (ver Nota de planning 4).
>
> **A LIÇÃO (o coração — cravar):** o fluxo de "esqueci minha senha" gera um **token** (uma string secreta), o entrega à vítima, e **quem apresenta o token certo pode DEFINIR UMA NOVA SENHA**. Quem tem o token **é** a autorização pra trocar a senha — o token é uma **CREDENCIAL TEMPORÁRIA**. A vuln: o token é **PREVISÍVEL** — gerado pelo `random` do Python (o Mersenne Twister) **seedado com o timestamp** (`random.seed(int(time.time()))`). O atacante pede o reset da vítima, lê o horário da resposta HTTP (header `Date`), **reproduz o seed**, roda o mesmo `random`, **gera o MESMO token**, e reseta a senha da vítima → **account takeover**. Não se quebra cripto nem se injeta nada — o "segredo" simplesmente **não é secreto**. O fix: token de um gerador **CRIPTOGRAFICAMENTE SEGURO** (`secrets`), de **USO ÚNICO**, com **EXPIRAÇÃO curta**.
>
> **REQUISITO DIDÁTICO (crítico — este átomo é DENSO de vocabulário de autenticação e de aleatoriedade que o iniciante não tem):** o WALKTHROUGH e o README **DEVEM definir DO ZERO, na 1ª ocorrência**, assumindo que o aluno não conhece nenhum: **fluxo de password reset** (o mecanismo esqueci-minha-senha → token → nova senha); **token de reset como CREDENCIAL temporária** (quem o tem pode trocar a senha); **entropia / imprevisibilidade** (por que um segredo tem que ser impossível de adivinhar); **PRNG e CSPRNG** (gerador pseudoaleatório comum vs criptograficamente seguro — `random` vs `secrets`); **seed** (o valor inicial que determina toda a sequência de um PRNG; se é previsível, a sequência é previsível); **Mersenne Twister** (o algoritmo do `random` do Python — determinístico, NÃO para segurança); **uso único e expiração** (o ciclo de vida de um token). Definir com clareza de iniciante — **NÃO** assumir familiaridade. Ver "O MECANISMO em detalhe" e a Nota de planning 3.
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha BURP-ONLY**: o ataque é HTTP — pedir o reset da vítima, ler o header `Date`, reproduzir o token com um **script local do atacante**, e postar a nova senha, tudo no Repeater; a **prova é logar como a vítima** com a senha nova; §3.4 — **SQLite** por padrão; §4 — **REAPROVEITAR a categoria A07 existente** (a pasta existe — confirmar o nome contra o §4); §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, **definir termo na 1ª ocorrência**, situar em A07 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`**, dados fake, chaves dummy; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referências vivas** — o **`session-fixation` (15) INTEIRO** (o **IRMÃO A07** — mesma categoria/pasta: reusar o enquadramento "A07 — Identification and Authentication Failures" e a estrutura de doc; e o **CONTRASTE de sub-forma** que define a identidade — 15 é sobre a **SESSÃO** (id forte, o furo é o ciclo de vida); 37 é sobre o **fluxo de RESET** (a credencial temporária **previsível**); o beat "não é adivinhação do id" do 15 é literalmente *"um id fraco, previsível, seria um bug diferente"* — esse bug diferente **é este átomo**), o **`crypto-weak-hash` (31) INTEIRO** (o **MOLDE quase-exato** — single-container SQLite com usuários semeados e senhas hasheadas, API-only JSON, `GET /` banner + `POST /login`; e o **CONTRASTE "não é crypto"** — lá se **quebra** um artefato cripto (hash) offline; aqui não se quebra nada, o segredo é **previsível**), os `idor-numeric-id` (03) / `idor-uuid-guessable` (11) — **SÓ pro CONTRASTE** (o beat "não é IDOR": previsibilidade-de-um-SEGREDO vs id-de-um-OBJETO), os **DOIS átomos publicados MAIS RECENTES — `cve-demo` (36) e `race-condition-basic` (35)** (a **VOZ/estrutura ATUAL** — abertura seca, definir termo do zero, título=classe, headers PT traduzidos, honestidade-em-camadas nas notas-armadilha), e o **`sqli-union-basic` (01)** (molde canônico single-container Flask + estrutura de doc).
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `app.py`, seed — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A07 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). Justificativa do ROADMAP para este átomo: *"token previsível ou reusável em reset de senha."*
>
> **A categoria A07 JÁ EXISTE — o 37 REAPROVEITA a pasta, NÃO cria.** `atoms/A07-auth-failures/` **está no disco** e já hospeda o `session-fixation` (15). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A07-auth-failures/`.** A árvore do repo no §4 fixa `A07-auth-failures/` com `weak-password-reset/` e `session-fixation/` dentro. Note que a **categoria OWASP 2021 completa é "Identification and Authentication Failures"**, mas o **nome de pasta encurta pra `auth-failures`** — exatamente o padrão já usado pelo irmão `session-fixation` (e por `A08-data-integrity-failures/`, `A10-ssrf/`). Ou seja: o nome de pasta é a **forma abreviada kebab** que o §4 já cravou; a **prosa (README/WALKTHROUGH/DIFF) nomeia a categoria por extenso — "A07 — Identification and Authentication Failures"**. Pasta final: **`atoms/A07-auth-failures/weak-password-reset/`** — a Fase 2 cria **só** a pasta do átomo, dentro da pasta de categoria que já existe.
>
> **Rótulo A07 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Gerar a credencial de recuperação de senha com um gerador previsível é **A07 — Identification and Authentication Failures** no OWASP Top 10 2021 (a edição que o projeto segue). **NÃO** relatar em que número/categoria essa classe caía em edições antigas do OWASP Top 10 — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A07 — Identification and Authentication Failures.** Explicar **por que** é A07 (o furo está no **desenho do fluxo de autenticação** — a credencial temporária é gerada de forma adivinhável — não num controle de acesso ausente nem numa primitiva de cripto quebrada — ver "Por que A07") é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4, §12). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW (lei do projeto, `CLAUDE.md` §5; e esta spec é pública/commitada → nasce limpa).** **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec**: situar o átomo por **ordinal de fase**, **milestone**, **release/versão** (`v0.x`/`v1.0` etc.), ou como **abertura/encerramento** de qualquer coisa — **INCLUSIVE** enquadrar como "o último A07", "o que fecha a fase", ou qualquer referência a **outros átomos futuros** (A07 ou não). Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não-publicados**, **sem postular átomo futuro** (nada de "um próximo átomo vai mostrar outra falha de auth"). **A posição vive SÓ no `ROADMAP.md`.** Confirmo aqui apenas o **número (37)**, o **slug (`weak-password-reset`)** e a **categoria (A07)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo. **Pode citar átomos publicados (01–36)** à vontade (`CLAUDE.md` §5) — em especial o `15` (irmão A07, contraste de sub-forma), o `31` (molde + contraste "não é crypto"), o `03`/`11` (contraste "não é IDOR"), o `35`/`36` (voz atual).

## Nota de planning 3 — convenções ATUAIS: Burp-only (justificado), abertura seca, requisito didático

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **Trilha BURP-ONLY — JUSTIFICADA (`CLAUDE.md` §3.3 — Burp é a ferramenta principal).** O ataque inteiro é **dirigível por HTTP**: `POST /forgot` (pede o reset da vítima), ler o header `Date` da resposta (o horário do servidor), reproduzir o token com um **script local do atacante** (roda o mesmo `random.seed(<Date>)`), `POST /reset` (posta a nova senha), e `POST /login` (a **prova**: logar como a vítima com a senha que o **atacante** definiu) — **tudo no Repeater**, com o script de previsão como a única ferramenta offline (equivalente ao cracker do 31 / ao Turbo Intruder do 35: um passo que o Burp não faz). **SEM browser** — não há execução client-side; a prova é a resposta HTTP do `POST /login`. **A previsão é um script Python cru** que o WALKTHROUGH **mostra** (é a ferramenta central do átomo — ver "A mecânica da previsão").
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (um fluxo de reset de senha que emite um token e deixa quem o apresenta definir a nova senha) e a falha (o token é gerado por um `random` seedado com o relógio, previsível pelo header `Date`). **NADA** de encenação ("você é o pentester" e afins).
> - **REQUISITO DIDÁTICO — definir CADA termo DO ZERO na 1ª ocorrência (`CLAUDE.md` §5 + o brief).** Este átomo é denso de **vocabulário de autenticação e de aleatoriedade**: **password reset flow**, **token-como-credencial temporária**, **entropia/imprevisibilidade**, **PRNG vs CSPRNG** (`random` vs `secrets`), **seed**, **Mersenne Twister**, **uso único/expiração**. Ver a lista completa e as definições candidatas em "O MECANISMO em detalhe".
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** — **predictable password-reset token** —, **NÃO** o motor ("...em Flask"/"...em Python"/"...com `random`"/"...Mersenne Twister"). O **slug** (`weak-password-reset`) já qualifica a variante. "Python"/"`random`"/"`secrets`"/"Mersenne Twister" aparecem no **corpo**, não no H1. Candidato de H1 em "Identidade".
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Pedir o reset da vítima`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A07 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — topologia single-container com SQLite embutido (candidato; molde do 31/01), usuários semeados

> **Precisa de estado, mas NÃO de concorrência.** A app tem **usuários** (a vítima + um segundo) e **tokens de reset** vivos — precisa de um datastore leve. **NÃO** precisa de concorrência/corrida (diferente do `race-condition-basic`, 35, que exigiu Postgres multi-thread pra a corrida ser real). Então:
>
> - **CANDIDATO RECOMENDADO — SINGLE-CONTAINER com SQLite embutido**, molde **exato** do `crypto-weak-hash` (31): cada lado é **um** container Flask com seu próprio `lab.db` efêmero, criado e semeado no boot por um `init_db()` (sem datastore externo, sem bind mount de seed, sem `depends_on`/healthcheck/rede nomeada). O `docker-compose.yml` tem **dois serviços** (`vulnerable` + `fixed`), bind **só** `127.0.0.1`. **É o mais simples e basta** — a lição não exige concorrência.
> - **ALTERNATIVA registrada (provavelmente desnecessária): multi-container com Postgres** (molde do datastore do 22/35). **Só** se, na Fase 2, algo do estado exigir realismo que o SQLite embutido não dê — o que **não se antecipa aqui**. **Default desta spec: SQLite single-container.** Confirmar na Fase 2.
> - **Onde vivem os tokens de reset.** Os **usuários** (email + `password_hash`) moram no SQLite (persistem o takeover: a senha trocada tem que "colar" pro `POST /login` provar). Os **tokens de reset** podem morar num **dict em memória** (`RESET_TOKENS = {token: email}`) — são estado efêmero de curta vida, e um dict basta (molde do `SESSIONS` em dict do `session-fixation` (15), que deliberadamente não usou banco pro estado de sessão). Decisão de forma da Fase 2 (dict em memória vs tabela SQLite) — **candidato: dict em memória pros tokens, SQLite pros usuários**. O que **não** muda: a senha trocada tem que persistir no store dos usuários pra o `POST /login` provar o takeover.
> - **Semear ao menos DOIS usuários:** a **vítima** (`victim@lab`) e um **segundo** (o atacante, `attacker@lab`, ou só um segundo usuário) — senhas dummy de lab, **hasheadas decentemente** (`werkzeug.security.generate_password_hash`) pra **NÃO** introduzir a vuln de storage do 31 "de brinde" (§8.5; a senha **não** é o foco — ver "Uma vuln só").
> - **§8:** bind **só** `127.0.0.1` (8037/8137); usuários/senhas **dummy**; nada real. O SQLite é local ao container, efêmero.

---

## Decisões abertas — VOCÊ DECIDE / CONFIRME NA FASE 2 (PROPOR O QUE FUNCIONAR)

> O **objetivo** de cada item está **TRAVADO**; o que fica aberto é **qual valor/forma concreta** o realiza. O Item 1 é **comportamento de plataforma (a reprodução do token seedado, com a granularidade do relógio e o skew) que só se conhece TESTANDO** — um **probe de comportamento sério**, não preferência editorial.

### Item 1 (O NÓ TÉCNICO) — a granularidade do seed e a JANELA de previsão (objetivo TRAVADO; a previsão a PROVAR RODANDO)

**O problema.** A lição só existe se o **token previsto BATE o token do servidor de forma reprodutível** — o `POST /reset` com o token previsto **funciona** no `vulnerable`. O eixo travado é: **o seed é uma função do tempo** (`int(time.time())`, segundos, é o candidato), e o atacante lê esse tempo do header `Date` da resposta HTTP (granularidade de **segundos**, em GMT). Duas rugas a resolver **rodando**:

- **A granularidade do seed.** Candidato: `random.seed(int(time.time()))` → epoch em **segundos** (UTC). O header `Date` do HTTP também é em segundos (GMT). Se o token é gerado no **mesmo segundo** em que a resposta é datada, o atacante reproduz o seed **exato**. **Confirmar rodando** que o seed = `int(time.time())` no `/forgot` casa com o segundo do header `Date` da mesma resposta.
- **O skew e a JANELA.** Se houver sub-segundo/clock skew (o token seedado a `:22.9`, a resposta datada a `:23.1`), o seed exato pode escapar por 1s. O atacante então **varre uma pequena janela** de seeds (`t-W .. t+W`, candidato **W = 2** ou **3** segundos), gera o token pra cada seed, e tenta cada um no `POST /reset` até um funcionar. **Candidato: janela de ±2–3s.** **Documentar o W que a Fase 2 provar.**

**O que a Fase 2 tem que PROVAR (rodando de verdade):** que o **script do atacante** — `random.seed(<epoch do Date>)` + a **mesma** geração do token (mesmo alfabeto, mesmo N, mesma sequência de chamadas `random`) — **reproduz o token do servidor**, e que o `POST /reset` com ele **troca a senha da vítima**, e que o `POST /login` com a nova senha **entra** (o takeover). **PROPOR o que funcionar.** Gate: **se o token previsto não bater de forma reprodutível, ajustar a granularidade/janela DENTRO do escopo travado (seed = função do tempo) e PROVAR; se NADA reproduzir, PARAR e avisar o mantenedor — NÃO inventar o token, o request/response, ou a saída do ataque.**

> **Restrição de determinismo a cravar na Fase 2:** pra o atacante reproduzir a sequência, o `vulnerable` tem que **seedar e gerar o token sem NADA mais consumir o RNG entre o `seed()` e o loop** (qualquer `random.*` intermediário desincroniza), e **re-seedar a cada `/forgot`** (cada pedido é independentemente previsível). O `random.seed(int)` do CPython é **reprodutível e estável** entre processos/máquinas com o mesmo esquema de geração — o atacante roda o mesmo Python e a mesma função. Provar rodando.

### Itens de forma (candidato registrado; a Fase 2 confirma pela via mais didática)

- **Item 2 — os nomes dos endpoints.** Candidatos **recomendados: `POST /login`** (autentica; a prova do takeover), **`POST /forgot`** (`{"email": ...}` → gera e associa um token ao usuário), **`POST /reset`** (`{"token": ..., "new_password": ...}` → se o token é válido, troca a senha do dono). `GET /` = banner JSON de aviso + dica (molde API-only do 31). Confirmar na Fase 2.
- **Item 3 — o formato do token vulnerável** (comprimento/alfabeto do gerador). Candidato: `"".join(random.choice(ALPHABET) for _ in range(N))` com `ALPHABET = string.ascii_letters + string.digits` e `N = 32` — **paralelo visual** ao `secrets.token_urlsafe(32)` do fix (o diff isola no **gerador**, não na "forma" do token). Alternativa registrada: `random.getrandbits(...)` / `hex`. **Recomendo o `random.choice` sobre um alfabeto** (mais legível, mais paralelo ao fix). O atacante tem que espelhar **exatamente** o alfabeto e o N. Confirmar na Fase 2.
- **Item 4 — a entrega do token ("o e-mail").** Candidato **recomendado: ambos os lados LOGAM o token no stdout** (`app.logger.info(...)`) como **stand-in do e-mail** — o canal out-of-band por onde o usuário receberia o link. Isto **NÃO** é uma 2ª vuln (info disclosure): é a simulação da entrega, análoga ao `session-fixation` (15) imprimir o `session_id` na tela ("real apps don't — surfaced here so you can watch"). **A resposta HTTP do `/forgot` NÃO devolve o token** (é genérica: *"if that account exists, a reset link has been sent"*), pra o **ataque ser por PREVISÃO, não por leitura**. O **baseline legítimo** usa o token do log (o "inbox"); o **ataque prevê** o token da vítima (nunca o lê). Confirmar na Fase 2.
- **Item 5 — expiração/uso-único no `vulnerable`.** Candidato **recomendado: AUSENTES no `vulnerable`** (o token vive no dict até ser usado; sem `pop`, sem check de tempo) — mantém o código vulnerável mínimo e o foco **100% no gerador**. Se a Fase 2 preferir incluí-los no `vulnerable`, que sejam **IRRELEVANTES pro ataque** (o token previsto é usado **na hora**; a ausência deles **NÃO** pode ser o que condena o `vulnerable` — a falha é a **previsibilidade**). Ver "Uma vuln só" e a nota de honestidade-em-camadas #4.

---

## Identidade

- **ID:** `weak-password-reset`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A07 — Identification and Authentication Failures**. Pasta `atoms/A07-auth-failures/` (**JÁ EXISTE — o 37 REAPROVEITA**, não cria; nome abreviado kebab, ver Nota de planning 1). Confirmado contra o `ROADMAP.md` ("A07 Auth Failures") e o `CLAUDE.md` §4. Em prosa, usar o nome da **classe** — **predictable password-reset token** — e a categoria por extenso — **"A07 — Identification and Authentication Failures"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A07-auth-failures/weak-password-reset/` (Fase 2 cria **só** a pasta do átomo; a de categoria já existe, com o `session-fixation` dentro)
- **Número sequencial:** 37
- **Porta `vulnerable`:** `127.0.0.1:8037` (TRAVADO)
- **Porta `fixed`:** `127.0.0.1:8137` (TRAVADO)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos.
- **Topologia:** **SINGLE-CONTAINER por lado** — dois serviços (`vulnerable` + `fixed`), **SQLite embutido** por lado (`lab.db` semeado no boot). Molde do `crypto-weak-hash` (31) / `sqli-union-basic` (01). Candidato; alternativa Postgres registrada como improvável (Nota de planning 4).
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/abertura/encerramento** (§5 foreshadow).
- **Branch de trabalho:** `atom/weak-password-reset`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** ver seção "Theory primer". **PortSwigger PRIMEIRO** — a Academy tem trilha forte de **Authentication** e cobertura de **password reset** (fit LIMPO **provável**). **Confirmar a URL/grafia por fetch na Fase 2; provavelmente NÃO precisa de fallback OWASP. NÃO inventar URL/grafia.**
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# weak-password-reset — Predictable password-reset token`** — `id` + nome canônico da **classe** em inglês. **SEM** "Flask"/"Python"/"`random`"/"Mersenne Twister" no H1 (o slug já qualifica; o motor fica no corpo). *(Alternativas registradas: `Weak password-reset token`, ou `Predictable password-recovery token`.)* Recomendo **"Predictable password-reset token"** por nomear o **defeito exato** (a previsibilidade) e ser a forma mais reconhecível/transferível pra um pentester procurando a classe. Grafia canônica exata **confirmável na Fase 2**; **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**Predictable password-reset token — account takeover por um segredo de autenticação adivinhável.** Um fluxo de **password reset** ("esqueci minha senha") emite um **token** — uma string secreta que a app entrega ao usuário (por e-mail, no mundo real) e que serve de **credencial temporária**: quem apresenta o token certo pode **definir uma nova senha** pra aquela conta. O fluxo está **correto** — autentica por **posse do token** (é assim que o esqueci-minha-senha funciona). Mas a app gera o token com o módulo **`random`** do Python, **seedado com o relógio**: `random.seed(int(time.time()))` e daí um punhado de `random.choice(...)`. O `random` é um **PRNG** (Pseudo-Random Number Generator — gerador **pseudo**aleatório): dado o **seed**, toda a sequência é **determinística e reproduzível**. E o seed — o horário em segundos — é um valor que o atacante **lê da própria resposta HTTP** (o header `Date`). O atacante pede o reset **da vítima**, lê o `Date`, **reproduz o seed**, roda o **mesmo** `random`, **gera o mesmo token**, e reseta a senha da vítima. **Não se quebra cripto** (nenhum hash, nenhuma cifra) e **não se injeta nada**: o segredo simplesmente **não é secreto o suficiente**. O fix **não** é reescrever o fluxo — é trocar o **gerador** por um **CSPRNG** (`secrets.token_urlsafe`), somado a **uso único** e **expiração curta**.

### A lição-coração

> **"O fluxo de 'esqueci minha senha' gera um token secreto, o entrega à vítima, e quem apresenta o token certo pode definir uma nova senha — o token é uma CREDENCIAL TEMPORÁRIA (quem o tem é a autorização pra trocar a senha). A vuln: o token é PREVISÍVEL — gerado pelo `random` do Python seedado com o timestamp (`random.seed(int(time.time()))`). O atacante pede o reset da vítima, lê o horário da resposta (header `Date`), reproduz o seed, roda o mesmo `random`, gera o MESMO token, e reseta a senha da vítima → toma a conta. Não se quebra cripto nem se injeta nada — o segredo simplesmente não é secreto o suficiente. O fix: token de um gerador CRIPTOGRAFICAMENTE SEGURO (`secrets.token_urlsafe`), de USO ÚNICO, com EXPIRAÇÃO curta."**

**+ MECANISMO:** o `random` do Python é o **Mersenne Twister**, determinístico a partir do seed; seedar com `time.time()` (um valor que o atacante calcula pelo header `Date`) torna **toda a sequência reproduzível** — o atacante refaz o seed e gera o mesmo token. **+ SUB-LIÇÃO:** a causa é o **GERADOR PREVISÍVEL** (PRNG comum + seed calculável), **NÃO** 'o token é curto' (aumentar o tamanho de um gerador previsível não ajuda — a fraqueza é a previsibilidade) nem 'faltou autenticação' (o fluxo autentica corretamente por posse do token; o furo é o token ser adivinhável).

### O MECANISMO em detalhe (o coração do WALKTHROUGH — DEFINIR CADA PEÇA NA ESTREIA)

O átomo assume que o aluno **não conhece nenhum** destes conceitos. Definir do zero, na 1ª ocorrência:

- **Password reset flow (o fluxo de "esqueci minha senha").** O mecanismo padrão pra um usuário que esqueceu a senha recuperar a conta **sem** provar a senha antiga (que ele não tem): ele pede o reset (informando o e-mail), o servidor gera um **token** e o entrega **fora da app** (por e-mail), e o usuário apresenta esse token pra **definir uma nova senha**. São três passos: **pedir** → **receber o token** → **trocar a senha**.
- **Token de reset como CREDENCIAL temporária.** O token é o que **prova** que você é o dono da conta **naquele momento** — não a senha, não a sessão, **o token**. Quem tem o token pode trocar a senha; portanto **o token É a autorização**. Ele é uma **credencial** (uma prova de identidade) **temporária** (válida por pouco tempo, de uso único). Se um atacante **descobre** o token, ele **é**, pra o servidor, o dono da conta.
- **Entropia / imprevisibilidade.** **Entropia** é a medida de quão **imprevisível** um valor é — quantos "chutes" um atacante precisaria, em média, pra adivinhá-lo. Um segredo (senha, chave, token) só é seguro se tem entropia **alta**: tantas possibilidades que adivinhar é inviável. Um token de reset **precisa** ser impossível de adivinhar — porque adivinhá-lo **é** virar o dono da conta. Entropia **baixa** (ou **previsível**) mata o segredo, por mais longo que ele pareça.
- **PRNG e CSPRNG.** Um **PRNG** (Pseudo-Random Number Generator) é um gerador de números "aleatórios" que, na verdade, são **calculados** por uma fórmula a partir de um valor inicial (o **seed**). Ele **parece** aleatório, mas é **determinístico**: mesmo seed → mesma sequência, sempre. É ótimo pra simulações e jogos, **péssimo pra segredos**. Um **CSPRNG** (Cryptographically Secure PRNG) é um gerador feito **para segurança**: sua saída é **imprevisível** mesmo pra quem já viu saídas anteriores, e ele semeia a si mesmo com entropia real do sistema operacional (`os.urandom`). No Python: **`random` é um PRNG** (Mersenne Twister); **`secrets` é o CSPRNG** — a diferença **é** a lição.
- **Seed.** O **valor inicial** que determina **toda** a sequência de um PRNG. Chame `random.seed(X)` e as próximas chamadas `random.*` produzem sempre a **mesma** sequência pra o mesmo `X`. Consequência afiada: **se o seed é previsível, a sequência inteira é previsível**. Seedar com `int(time.time())` (o horário em segundos) é seedar com um valor que **qualquer um calcula** — inclusive pelo header `Date` da resposta.
- **Mersenne Twister.** O algoritmo por trás do módulo **`random`** do Python. É um PRNG **determinístico** de altíssima qualidade estatística (excelente pra simulação) mas **explicitamente NÃO criptográfico** — a própria doc do Python avisa: *"não use `random` para segurança; use `secrets`"*. Dado o seed (ou observando saídas suficientes), seu estado interno é **recuperável**, e a sequência inteira, **reproduzível**. Determinístico por design — o oposto do que um segredo precisa.
- **Uso único e expiração (o ciclo de vida do token).** Um token de reset bem-feito **morre depois de usado** (**uso único**: uma vez que trocou a senha, aquele token não vale mais) e **morre com o tempo** (**expiração**: vale só por alguns minutos). Isso limita a janela em que um token — mesmo vazado — é útil. São propriedades de **higiene** de um token; **não** são o que este átomo conserta (o furo central é a **previsibilidade**), mas fazem parte do **fix completo** (ver a honestidade-em-camadas).

**O ponto contraintuitivo a cravar:** o fluxo **faz exatamente o que deveria** — quem tem o token troca a senha. O atacante **não** burla nenhum check; ele **satisfaz** o check, apresentando o token **certo**. O furo é que o token **certo é calculável**. Por isso "reforçar o fluxo" (mais checks, token mais longo) não resolve: enquanto o **gerador** for previsível, o atacante gera o token que o fluxo pede. A correção é tornar o token **imprevisível** — trocar o **gerador**.

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas do DIFF)

> **A causa é o GERADOR PREVISÍVEL (um PRNG comum seedado com um valor calculável — o relógio, lido do header `Date`), NÃO 'o token é curto' (aumentar o tamanho de um gerador previsível não ajuda — reproduzido o seed, o atacante gera o token inteiro, de qualquer tamanho; a fraqueza é a PREVISIBILIDADE, não o comprimento) e NÃO 'faltou autenticação/um check de dono' (o fluxo autentica corretamente por posse do token; não é IDOR — o token É o segredo, não o id de um objeto). O fix é a IMPREVISIBILIDADE: um CSPRNG (`secrets`), somado a uso único + expiração como o token bem-gerido. Um token imprevisível que nunca expirasse ainda seria muito melhor que um previsível — a previsibilidade é o eixo.**

### Por que A07 (Identification and Authentication Failures)

O bug **não é** "input virou código" (injection — A03: o app não costura input não-confiável num sink), **não é** "faltou um check de dono / troquei o id de um objeto" (A01/IDOR — o token **não** é o id de um recurso; é o **segredo de autenticação**, e o fluxo **autentica** por posse dele), **não é** "quebrei uma primitiva de cripto" (A02 — nenhum hash é crackeado, nenhuma cifra é quebrada; o segredo é **previsível**, não **cifrado-fraco**). É **"o mecanismo de recuperação de credencial gera a credencial temporária de forma adivinhável"** — uma falha de **desenho do fluxo de autenticação/identificação**. No Web Top 10 2021 isso é **A07 — Identification and Authentication Failures**, que inclui explicitamente **weak credential recovery and forgot-password processes**. Situar em **A07 — Identification and Authentication Failures**, **sem** contar edições antigas. Explicar **por que** é A07 (a falha está em **como a credencial de autenticação é gerada**, não num controle de acesso nem numa primitiva de cripto) é a lição. Ancora no irmão A07 `session-fixation` (15), a **outra** sub-forma de falha de autenticação (ver o contraste).

---

## Contraste — o eixo que DEFINE a identidade (o que separa este átomo dos vizinhos)

O átomo toca conceitos que orbitam outros já publicados — id/segredo (IDOR), aleatoriedade/segredo (crypto), credencial de autenticação (session-fixation). O que o distingue é **onde** mora a falha: **a PREVISIBILIDADE de um SEGREDO DE AUTENTICAÇÃO**. Cravar no WALKTHROUGH e no DIFF, ou o átomo colide com os vizinhos. **"Um átomo = uma vuln" se refere à CAUSA** (`CLAUDE.md` §2):

| Eixo | Vizinho | `weak-password-reset` (37) |
|---|---|---|
| **`session-fixation` (15) — irmão A07** | a **SESSÃO**: o `session_id` é **forte** (`secrets.token_urlsafe`, imprevisível); o furo é o **ciclo de vida** (ele **sobrevive** à mudança de privilégio no login) | a **credencial de RESET**: o token é **PREVISÍVEL** (`random` seedado); o furo **É** a previsibilidade do segredo. **Mesma categoria (A07), sub-formas opostas** — e o fix do 37 (`secrets.token_urlsafe`) é **exatamente** o gerador que o 15 **já usa** pro id |
| **`idor-numeric-id` (03) / `idor-uuid-guessable` (11)** | trocar o **id de um OBJETO** e acessar o recurso de outro por baixo de um **controle de acesso ausente** | o token previsível **NÃO** é o id de um recurso — é o **PRÓPRIO SEGREDO DE AUTENTICAÇÃO**; prever o token **É** provar que você é a vítima (o fluxo faz o que deveria). A falha é o **SEGREDO SER PREVISÍVEL**, não um controle de acesso faltando |
| **`crypto-weak-hash` (31) / `crypto-ecb-mode` (32)** | **quebrar** um artefato cripto **offline** (rainbow table no hash; cut-and-paste de blocos no ECB) — a primitiva é errada | **não se quebra nada** — nenhum hash é crackeado, nenhuma cifra é forçada. O token é **reproduzido** porque o **gerador** é previsível. Falha de **desenho de autenticação** (A07), não de **primitiva de cripto** (A02) |

**PONTO AFIADO A CRAVAR:** o `session-fixation` (15), no seu próprio beat "o que a vuln NÃO é", diz textualmente que **um id fraco e previsível seria um bug diferente** — e este átomo **é** esse bug diferente, aplicado ao token de reset. O aluno que fez o 15 chega aqui com a âncora perfeita: lá o segredo era forte e o furo era o ciclo de vida; aqui o segredo é **fraco** e o furo **é** isso. Citar o `15` (publicado) à vontade — é a âncora que dá sentido ao par A07.

---

## Uma vuln só — o fluxo está correto; a única falha é o GERADOR PREVISÍVEL

Invariante inegociável do átomo (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o **gerador previsível do token** (`random` seedado com o tempo). Para garantir isso:

- **O fluxo de reset está CORRETO.** Associar token→usuário, exigir o token pra trocar a senha, trocar a senha do **dono** do token — tudo certo. **NÃO** modelar um IDOR no `/reset` (ex.: aceitar um `user_id` no corpo e trocar a senha de quem o corpo mandar) — isso seria **outra** vuln (A01). O `/reset` troca a senha do **dono do token**, ponto.
- **O login está CORRETO.** `POST /login` compara a senha submetida com o `password_hash` guardado (`werkzeug.check_password_hash`). Sem SQLi (query parametrizada), sem bypass. É só a **prova** do takeover.
- **A senha dos usuários é guardada com um hash DECENTE.** `werkzeug.security.generate_password_hash` (PBKDF2/scrypt salted, o default do werkzeug) — **NÃO** MD5/SHA1 cru. Isso é deliberado: **não** introduzir a vuln de storage do `crypto-weak-hash` (31) "de brinde" (§8.5). A senha **não** é o objeto de estudo; o **token** é.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é a **IMPREVISIBILIDADE** do gerador (`random` seedado → `secrets`), **NÃO** aumentar o token (nota-armadilha #2) nem "usar `random` com um seed melhor" (nota-armadilha #3). **Uso único + expiração** entram como parte do **fix completo** (o token bem-gerido), **NÃO** como a falha central — a nota de honestidade-em-camadas #4 impede o aluno de sair achando que "o fix é só pôr expiração". **Prova de isolamento (o eixo):** contra o `fixed`, o token **previsto** falha **na hora** porque **nunca foi gerado** (o `secrets` fez outro) — o `/reset` recusa como token desconhecido, **antes** de uso-único/expiração sequer entrarem em jogo. A **previsibilidade** é o que separa os lados.
- **Sem 2ª vuln.** Sem injection (queries parametrizadas), sem IDOR (o `/reset` age no dono do token), sem falha de hash de senha (werkzeug decente), sem falha de controle de acesso. **Único diff `vulnerable`↔`fixed`: o gerador do token (+ o ciclo de vida no fix).**

---

## Flavor — fluxo de reset com token previsível (TRAVADO)

Cenário canônico de A07: uma app com **login** e um **fluxo de recuperação de senha**.

- **APP (Flask, API-only JSON, `vulnerable` :8037 / `fixed` :8137):**
  - **`POST /login`** (Item 2) — `{"email": ..., "password": ...}`; compara com o `password_hash` do usuário (`werkzeug.check_password_hash`, query parametrizada). Responde `{"authenticated": true/false}`. **É a PROVA do takeover** (logar como a vítima com a senha nova).
  - **`POST /forgot`** (Item 2) — `{"email": ...}`; se o usuário existe, gera um token de reset (`make_reset_token()`), associa `token → email` (`RESET_TOKENS`), e "envia por e-mail" (Item 4: loga no stdout como stand-in). **Responde genérico** (`{"message": "If that account exists, a reset link has been sent."}`) — **não** devolve o token nem revela se o e-mail existe. **É o coração:** o `make_reset_token()` do `vulnerable` é `random.seed(int(time.time()))` + `random.choice`.
  - **`POST /reset`** (Item 2) — `{"token": ..., "new_password": ...}`; se o token é válido, troca o `password_hash` do **dono do token**. Responde `{"reset": true/false}`.
  - **`GET /`** — banner JSON de aviso (molde do 31/API-only) + dica de uso (`POST /forgot` → `POST /reset` → `POST /login`; trabalhar do Burp Repeater). **Banner de aviso** (`CLAUDE.md` §8.2) vive no README e no `GET /` JSON.
- **SEM HTML** (categoria naturalmente API-only — o fluxo é REST puro: login, forgot, reset), como o `crypto-weak-hash` (31). **Sem** `templates/index.html`. **COM datastore** (SQLite pros usuários; dict pros tokens — Nota 4).
- **Usuários semeados (dummy):** `victim@lab` e `attacker@lab` (ou um segundo usuário), senhas de lab hasheadas com werkzeug.

**O ATAQUE (resumo; detalhe em "A prova"):** o atacante chama `POST /forgot {victim@lab}`, lê o header `Date` da resposta (o horário do servidor), **reproduz** `random.seed(<epoch do Date>)` num script local, gera o **mesmo** token, e chama `POST /reset {token, nova_senha}` → a senha da vítima muda → o atacante loga como a vítima (`POST /login {victim@lab, nova_senha}`). **A vítima nunca vazou o token** — ele foi **PREVISTO**.

---

## A prova — account takeover (TRAVADO; a previsão é probe de comportamento na Fase 2)

**Cadeia (TRAVADA):**

- **(baseline)** o fluxo de reset funciona pra um usuário legítimo: `POST /forgot` pro **próprio** e-mail → pega o token do canal de entrega (o log/"inbox", Item 4) → `POST /reset {token, nova_senha}` → `POST /login {nova_senha}` entra. **Idêntico nos dois lados** — é a feature funcionando.
- **(ataque, só faz sentido no `vulnerable`)** o atacante **prevê** o token da **VÍTIMA** pelo header `Date`, reseta a senha dela, e **LOGA** como a vítima com a senha nova. **PROVA:** `POST /login {victim@lab, <senha que o ATACANTE definiu>}` → `{"authenticated": true}`. O atacante **entrou na conta da vítima** — nunca viu a senha antiga, nunca viu o token real.
- **(FIXED)** o **mesmo** ataque → o token previsto (do `random` seedado) **NÃO bate** o token real (gerado por `secrets`, imprevisível) → o `POST /reset` **falha** (`{"reset": false}`, token desconhecido) → o atacante **não entra**.

### A mecânica da previsão (o SCRIPT do atacante — a ferramenta central; probe de comportamento na Fase 2)

O seed é `int(time.time())` (segundos). O atacante sabe o horário do servidor pelo header `Date` da resposta (granularidade de **segundos**, GMT) — então reproduz o seed exato se o token é gerado no mesmo segundo, ou varre uma **janela** de ±W segundos se houver skew (Item 1). O script (candidato — a Fase 2 prova rodando, referenciando a mecânica real do `random`):

```python
#!/usr/bin/env python3
# CANDIDATE attacker-side token predictor. Reproduces the server's PREDICTABLE reset token.
# It runs the SAME generator the vulnerable app runs, re-seeded from the server's clock,
# which the attacker reads straight off the /forgot response's Date header.
# Phase 2 MUST prove this reproduces the server token and that POST /reset accepts it.
import sys, random, string, calendar, email.utils

ALPHABET = string.ascii_letters + string.digits   # MUST match the server's generator (Item 3)
TOKEN_LEN = 32                                     # MUST match the server's N (Item 3)

def predict(seed):
    random.seed(seed)                              # same seed -> same Mersenne Twister sequence
    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))

# The Date header from the /forgot response, e.g. "Wed, 10 Sep 2026 14:03:22 GMT"
date_header = sys.argv[1]
t = calendar.timegm(email.utils.parsedate(date_header))   # HTTP date (GMT) -> epoch seconds (UTC)

# Candidate: the token was seeded with int(time.time()) at the same second the response was dated.
# Sweep a small window (Item 1: W=2..3) to absorb sub-second / clock skew; try each predicted
# token against POST /reset until one is accepted.
for seed in range(t - 2, t + 3):
    print(seed, predict(seed))
```

**Mecânica (a explicar no WALKTHROUGH, do zero):** `random.seed(<t>)` põe o Mersenne Twister num estado **determinado por `<t>`**; o **mesmo** `t` + a **mesma** sequência de `random.choice` → o **mesmo** token, byte por byte. O atacante conhece o esquema de geração (neste lab, lendo o `vulnerable/app.py` — átomo white-box) e o `t` (o header `Date`) → **reproduz** o token. A lição **transferível**: qualquer token de PRNG seedado por um valor observável é reproduzível uma vez conhecidos o **esquema** e o **seed**. **A forma exata (granularidade/janela) a CONFIRMAR rodando** (Item 1) — se o candidato não reproduzir, ajustar dentro do escopo travado (seed = função do tempo) e **provar**; **se NADA reproduzir, PARAR e avisar** — **NÃO inventar** o token.

### Prova de isolamento (o que traça a diferença PURO à previsibilidade)

- **Fluxo de reset legítimo, IDÊNTICO nos dois lados:** o próprio usuário pede o reset, recebe o token pelo canal de entrega (o log/"inbox"), reseta, e loga com a nova senha → **funciona igual** no `vulnerable` **e** no `fixed`. **A feature é idêntica** — só a **previsão do token da vítima** separa.
- **A PREVISÃO do token da vítima:** no `vulnerable`, o token previsto (pelo `Date`) **bate** o real → o `/reset` troca a senha da vítima → takeover. No `fixed`, o token previsto **não bate** o real (`secrets`) → o `/reset` recusa (token desconhecido) → sem takeover. A diferença é **100% a PREVISIBILIDADE do gerador** — o resto do fluxo é idêntico. **Cravar:** não há o que "sanitizar" no fluxo; o mesmo fluxo, com um gerador imprevisível, resiste. **O gerador É a diferença.**

---

## O código — o coração no GERADOR do token (candidatos)

O fio condutor: **o fluxo NÃO muda entre os lados; o gerador do token muda** (+ o ciclo de vida no fix). Os `POST /login`, `POST /forgot`, `POST /reset` têm a **mesma** forma nos dois lados — só o `make_reset_token()` (e, no fix, o `pop`/expiração no `/reset`) difere.

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma a reprodução (Item 1), captura o request/response reais, e PROVA o ataque rodando.**

### `vulnerable/app.py` — `random.seed(int(time.time()))` + token do `random` (candidato)

```python
import os
import time
import random
import string
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")
ALPHABET = string.ascii_letters + string.digits
TOKEN_LEN = 32

# Ephemeral reset-token store: token -> email. Dummy lab state (CLAUDE.md §8).
RESET_TOKENS = {}


def make_reset_token():
    # VULNERABLE: the reset token is a TEMPORARY CREDENTIAL -- whoever holds it may set a new
    # password for the account. It is generated with Python's `random`, a PRNG (the Mersenne
    # Twister), SEEDED WITH THE CURRENT TIME. random is deterministic from its seed, and the
    # seed here is int(time.time()) -- the server's clock in whole seconds, a value the attacker
    # reads straight off this response's Date header. Reproduce the seed, run the same random
    # calls, and you regenerate the SAME token. The secret is not secret. Fix: a CSPRNG
    # (secrets), single-use, short expiry. See fixed/ and DIFF.md.
    random.seed(int(time.time()))
    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))


@app.route("/forgot", methods=["POST"])
def forgot():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row:
        token = make_reset_token()
        RESET_TOKENS[token] = email
        # In a real app the token is EMAILED, never returned over HTTP. This lab logs it to
        # stdout ONLY as a stand-in for that out-of-band delivery (the user's "inbox"), so the
        # baseline flow has a token to use -- the ATTACK never reads it, it PREDICTS it.
        app.logger.info("reset token for %s: %s", email, token)
    # Generic response either way: leaks neither the token nor whether the account exists.
    return jsonify({"message": "If that account exists, a reset link has been sent."})


@app.route("/reset", methods=["POST"])
def reset():
    body = request.get_json(silent=True) or {}
    token = body.get("token", "")
    new_password = body.get("new_password", "")
    email = RESET_TOKENS.get(token)          # no single-use / no expiry: the flaw is the GENERATOR
    if not email:
        return jsonify({"reset": False}), 400
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                 (generate_password_hash(new_password), email))
    conn.commit()
    conn.close()
    return jsonify({"reset": True})


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /forgot {email}, then POST /reset {token, new_password}, then "
                "POST /login {email, password}. Work from Burp Repeater.",
    })


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
    # Seed two users with dummy lab passwords, stored with a DECENT hash (werkzeug's default,
    # a salted KDF) -- NOT to study password storage (that is crypto-weak-hash), just so the
    # only flaw is the reset-token GENERATOR. Dummy data (CLAUDE.md §8).
    seed = [("victim@lab", "victim-lab-pw"), ("attacker@lab", "attacker-lab-pw")]
    for email, pw in seed:
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                     (email, generate_password_hash(pw)))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — `secrets.token_urlsafe` + uso único + expiração (candidato)

Muda **só** o `make_reset_token()` (o gerador) e o **ciclo de vida** no `/reset` (uso único + expiração). Todo o resto (`/forgot`, `/login`, `/`, `init_db`, o seed) é **idêntico** ao `vulnerable`.

```python
import os
import time
import secrets                                       # CSPRNG, replaces random
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")
TOKEN_TTL = 15 * 60                                  # seconds -- short expiry

# token -> {"email": ..., "expires_at": ...}
RESET_TOKENS = {}


def make_reset_token():
    # FIXED: secrets.token_urlsafe(32) draws from a CSPRNG (os.urandom) -- ~256 bits of
    # UNPREDICTABLE entropy, with no seed the attacker can reproduce. Nothing in the response
    # (the Date header or anything else) narrows the search. This is the SAME generator
    # session-fixation already uses for its session ids. The token is unguessable by design.
    return secrets.token_urlsafe(32)


# ... /forgot IDENTICAL to vulnerable, except it stores an expiry alongside the email:
#     RESET_TOKENS[token] = {"email": email, "expires_at": time.time() + TOKEN_TTL}


@app.route("/reset", methods=["POST"])
def reset():
    body = request.get_json(silent=True) or {}
    token = body.get("token", "")
    new_password = body.get("new_password", "")
    entry = RESET_TOKENS.pop(token, None)            # SINGLE-USE: consumed on lookup
    if not entry or entry["expires_at"] < time.time():   # EXPIRY
        return jsonify({"reset": False}), 400
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                 (generate_password_hash(new_password), entry["email"]))
    conn.commit()
    conn.close()
    return jsonify({"reset": True})

# ... /login, /, init_db IDENTICAL to vulnerable ...
```

- **O CONTRASTE PRINCIPAL é o `make_reset_token()`:** `random.seed(int(time.time()))` + `random.choice` **→** `secrets.token_urlsafe(32)`. Esse é o eixo do átomo.
- **Uso único + expiração** são o **fix completo** (o token bem-gerido), **não** a falha central — ver a honestidade-em-camadas #4. Contra o **ataque de previsão**, o que salva o `fixed` é a **imprevisibilidade** (o token previsto nem existe no store); uso-único/expiração protegem contra **outros** cenários (reuso, vazamento + uso tardio).
- **Item 5:** o `vulnerable` **não** enforça uso-único/expiração (candidato) — mantém o foco no gerador. Se a Fase 2 incluí-los no `vulnerable`, que sejam **irrelevantes** pro ataque (o token previsto é usado na hora).

### `requirements.txt` — IDÊNTICOS nos dois lados (candidato)

```
# vulnerable/requirements.txt   E   fixed/requirements.txt  (mesmo conteúdo)
Flask==3.0.0
```

**Os requirements são IDÊNTICOS** — o delta é o **gerador do token no `app.py`** (`random` → `secrets`), **NÃO** uma dependência. `random`, `time`, `secrets`, `sqlite3` são **stdlib**; `werkzeug` (o hash de senha) **vem com o Flask**. **Contraste com o `crypto-weak-hash` (31):** lá o fix trouxe uma lib (`bcrypt`); **aqui o fix é uma troca de módulo da stdlib** — nada a instalar. (Se a Fase 2 confirmar que nada além do Flask é preciso, os dois `requirements.txt` ficam byte-idênticos.)

---

## O fix e o tipo de diff

**Fix:** trocar o **gerador previsível** (`random` seedado com o tempo) por um **CSPRNG** (`secrets.token_urlsafe`), **+ uso único** (`pop` no `/reset`) **+ expiração curta** (TTL). O diff mora no **`make_reset_token()`** (o eixo) e no **ciclo de vida** do token no `/reset`. Tipo de diff: **lógica-diferente no gerador do segredo** (não uma flag, não uma versão de dependência).

Diff colável (candidato — a Fase 2 gera o real):

```diff
-import random
+import secrets
 ...
 def make_reset_token():
-    # VULNERABLE: PRNG (Mersenne Twister) seeded with the clock -> predictable from Date header
-    random.seed(int(time.time()))
-    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))
+    # FIXED: CSPRNG, ~256 bits of unpredictable entropy, no reproducible seed
+    return secrets.token_urlsafe(32)
 ...
 def reset():
-    email = RESET_TOKENS.get(token)                 # no single-use, no expiry
-    if not email:
+    entry = RESET_TOKENS.pop(token, None)           # single-use
+    if not entry or entry["expires_at"] < time.time():   # expiry
         return jsonify({"reset": False}), 400
```

**O CONTRASTE é o gerador:** `random` seedado **→** `secrets`. **Nenhuma** linha do fluxo de reset (associar token→usuário, trocar a senha do dono) muda de intenção.

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é o GERADOR PREVISÍVEL, NÃO 'faltou autenticação' e NÃO 'faltou um check de dono'.** O fluxo **autentica** por posse do token (é assim que reset funciona) e **age no dono do token** (não é IDOR — o token **é** o segredo, não o id de um objeto). O furo é o token ser **adivinhável**: o `random` seedado com o `Date` é reproduzível. **Prova de isolamento:** o fluxo legítimo funciona **igual** nos dois lados; só a **previsão** do token da vítima separa — e ela morre no `fixed` porque o `secrets` fez um token que o atacante não consegue reproduzir.
2. **"Só aumentar o token" — nota-ARMADILHA.** Mais caracteres num gerador **previsível** não ajudam: reproduzido o seed, o atacante gera o token **inteiro**, de qualquer tamanho. A fraqueza é a **PREVISIBILIDADE**, não o comprimento; o remédio é **entropia imprevisível** (`secrets`), não mais bytes de um PRNG.
3. **"Usar `random` com um seed melhor" — nota-ARMADILHA.** O `random` (Mersenne Twister) **NÃO** é pra segurança em **nenhum** seed — mesmo bem seedado, seu estado interno é **recuperável** observando saídas suficientes, e a sequência, reproduzível. A resposta é um **CSPRNG** (`secrets`/`os.urandom`), **não** um PRNG "melhor seedado". (Nomear a intuição — "e se eu seedar com `os.urandom`?" — e responder: aí você já está usando entropia de CSPRNG; o certo é usar o `secrets`, feito pra isso, e não remendar o `random`.)
4. **HONESTIDADE EM CAMADAS sobre uso-único + expiração (CRÍTICA — sem virar o fix).** Enquadrar assim, explicitamente:
   - **(a)** Uso único e expiração são propriedades **legítimas e necessárias** de um token de reset bem-feito — **defense-in-depth**: mesmo um token forte deve expirar e valer uma vez só (limita a janela de um token vazado). O fix **as inclui**.
   - **(b)** MAS a falha **CENTRAL** deste átomo é a **PREVISIBILIDADE**. Um token **imprevisível** que nunca expirasse ainda seria **muito melhor** que um previsível — porque o atacante nunca o adivinharia. Contra **este** ataque (previsão), o que salva o `fixed` é o **`secrets`**: o token previsto **nem existe** no store, então o `/reset` o recusa **antes** de uso-único/expiração entrarem em jogo.
   - **(c)** Nomear as duas sem deixar o aluno achar que "o fix é só pôr expiração". Um leitor que saia daqui achando isso **perdeu** a lição: teria adicionado expiração e **continuado com um token previsível** — o atacante ainda o adivinha **dentro** da janela de validade. **Cravar:** o eixo é a imprevisibilidade; uso-único/expiração são o acabamento honesto, não a causa. *(Mesma honestidade-em-camadas das notas-armadilha do 31 (o salt)/32 (o CBC)/33 (o PIN): a defesa nomeada tem valor, mas não é o fix de causa **deste** átomo.)*
5. **Impacto: account takeover.** O atacante **define** a senha da vítima e **entra** na conta dela. Contraste com o `session-fixation` (15): ambos A07, mas 15 = a **sessão** (id forte, ciclo de vida); 37 = a **credencial de reset previsível** (o segredo é fraco). **Sem foreshadow.**

---

## Biblioteca / stack

- **`vulnerable/` e `fixed/`: Flask + stdlib.** `random`, `time`, `secrets`, `sqlite3`, `string` são **stdlib** (não vão no requirements); `werkzeug.security` (o hash de senha) **vem com o Flask**. A vuln vive numa escolha de **módulo da stdlib** (`random` vs `secrets`), não numa dependência.
- **Os `requirements.txt` são IDÊNTICOS** nos dois lados (candidato: só `Flask==3.0.0`). O delta é o **gerador no `app.py`**. **Contraste com o 31** (onde o fix trouxe `bcrypt`): aqui o fix é uma **troca de módulo stdlib**, nada a instalar.
- **SQLite embutido** (candidato, Nota 4) pros **usuários**; **dict em memória** pros **tokens de reset**. **SEM** ORM, `requests`, Postgres (candidato), MongoDB, ou 2ª dependência. `CLAUDE.md` §3.6.
- **O Flask (e qualquer dep) em versão ATUAL** — **sem** CVE "de brinde" (`CLAUDE.md` §8.5). `Flask==3.0.0` casa com os irmãos; confirmar que instala.
- **SEM SAÍDA B clássica.** `random.seed(time)` + `random` **é** o antipadrão ingênuo **direto** — não há "a ferramenta padrão resiste ao ataque ingênuo" (como uma query parametrizada resistiria à SQLi). O `secrets` é a ferramenta **certa** (o fix), não um default que por acaso resiste. **A reprodução da previsão (a janela de segundos) é o probe** (Item 1). **NÃO inventar uma Saída B** — declarar que não há.

---

## §8 / isolamento — o app em loopback, dados dummy

- **Bind só `127.0.0.1`** (8037/8137) no `docker-compose.yml` (`CLAUDE.md` §8.1). SQLite local ao container, efêmero.
- **Usuários/senhas dummy** (`victim@lab`/`attacker@lab`, senhas de lab óbvias), hasheadas decentemente. **Nada real** (§8.3). Sem credenciais reais, sem dados de cliente.
- **Sem código malicioso** (§8.4): o "exploit" é um script Python que roda o **mesmo `random`** — nada destrutivo, nada de rede/C2. A nova senha é dummy de lab.
- **Banner de aviso** (§8.2) no README (PT+EN) e no `GET /` JSON.

---

## WALKTHROUGH — abertura seca; Burp-only; DENSO EM DEFINIÇÕES; headers PT traduzidos

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (um fluxo de reset que emite um token e deixa quem o apresenta definir a nova senha) e a falha (o token é gerado por um `random` seedado com o relógio — previsível pelo header `Date`). Trilha **Burp-only**: `POST /forgot` → ler o `Date` → o **script de previsão** → `POST /reset` → `POST /login` (a prova). **SEM browser.**

**Abertura (candidato — plantar a lição, seco):**

> *A app tem um fluxo de recuperação de senha. Você manda `POST /forgot` com um e-mail, o servidor gera um token de reset e o "envia" pro dono da conta, e quem apresentar esse token em `POST /reset` pode definir uma nova senha. O token é uma credencial temporária: quem o tem é, pra o servidor, o dono da conta. O fluxo está correto — o problema é COMO o token é gerado. A app usa o módulo `random` do Python, seedado com o relógio: `random.seed(int(time.time()))`. O `random` é determinístico a partir do seed, e o seed é o horário em segundos — um valor que vem de graça no header `Date` de qualquer resposta HTTP. Reproduza o seed, rode o mesmo `random`, e você gera o mesmo token que o servidor gerou pra vítima.*

Beats (molde do 31/35/36 — abertura seca, seções numeradas `## 1..N`; tudo no Repeater + o script de previsão; **sem browser**):

1. **Context.** A feature: `GET /` de aviso + `POST /login` + `POST /forgot` + `POST /reset`. **Definir na estreia (REQUISITO DIDÁTICO — do zero):** **password reset flow** (esqueci-minha-senha → token → nova senha), **token-como-credencial temporária** (quem o tem troca a senha), **entropia/imprevisibilidade** (por que um segredo tem que ser impossível de adivinhar), **PRNG vs CSPRNG** (`random` vs `secrets`), **seed** (o valor que determina toda a sequência; previsível → sequência previsível), **Mersenne Twister** (o `random` do Python — determinístico, não pra segurança), **uso único/expiração** (o ciclo de vida). Isto é **A07 — Identification and Authentication Failures**. Portas: `vulnerable` `127.0.0.1:8037`, `fixed` `127.0.0.1:8137`. Trilha: **Burp (Repeater)** + o **script de previsão**; sem browser. Cravar: o token é uma **credencial**, e ela é **previsível**.
2. **Spot the bug.** Mostrar o `vulnerable/app.py` — o `make_reset_token()`: `random.seed(int(time.time()))` + `random.choice`. A pergunta de auditoria: **"de onde vem a aleatoriedade deste segredo?"** Aqui, de um **PRNG seedado com o relógio** — e o relógio está no header `Date`. Foreshadow do fix: um **CSPRNG** (`secrets`), sem seed reproduzível.
3. **Baseline — o fluxo funcionando.** `POST /forgot` pro **próprio** e-mail do atacante (`attacker@lab`) → pegar o token do canal de entrega (o log/"inbox", Item 4) → `POST /reset {token, nova_senha}` → `POST /login {attacker@lab, nova_senha}` → entra. O fluxo legítimo funciona. (Deixa claro o que é "normal" antes do ataque.)
4. **Exploitation (Burp + o script de previsão — a prova é o login).**
   - **4a — pedir o reset da VÍTIMA:** `POST /forgot {"email": "victim@lab"}` no Repeater. Ler o header **`Date`** da resposta (o horário do servidor, em segundos). A resposta é **genérica** — **não** traz o token (o ponto é que você não precisa dele: você o **prevê**).
   - **4b — prever o token (o SCRIPT):** rodar o script do atacante (mostrar o código) — `random.seed(<epoch do Date>)` + a **mesma** geração (mesmo alfabeto, mesmo N) → o **mesmo** token. Explicar a mecânica **do zero** (Mersenne Twister determinístico; o `Date` entrega o seed). Se houver skew, varrer a **janela** de ±W segundos (Item 1) e ter uma lista curta de tokens candidatos.
   - **4c — resetar a senha da vítima:** `POST /reset {"token": "<previsto>", "new_password": "pwned-by-attacker"}` → `{"reset": true}`. (Se varreu a janela, o token candidato que funcionar é o certo.)
   - **4d — PROVAR o takeover (o login é a prova):** `POST /login {"email": "victim@lab", "password": "pwned-by-attacker"}` → `{"authenticated": true}`. **Você entrou na conta da vítima com a senha que VOCÊ definiu.** Nunca viu a senha antiga, nunca viu o token real — **previu** o token.
   - **§8 (cravar):** lab **isolado** (bind só `127.0.0.1`); tudo **no Burp** + um script Python que roda o **mesmo `random`**; nada destrutivo, nada de rede. Num alvo real isso é **account takeover** — os dados são dummy de lab.
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'" (os cinco).
6. **Impact (honesto — sem overclaim).** **Account takeover:** o atacante define a senha da vítima e entra na conta. O teto é o controle da conta da vítima.
7. **Why the fix works (porta 8137).** Repetir o ataque contra o `fixed/`:
   - `POST /forgot {victim@lab}` → ler o `Date` → rodar o **mesmo** script de previsão → o token previsto. `POST /reset {"token": "<previsto>", ...}` → `{"reset": false}` (400): o token previsto **não existe** — o `secrets` gerou um token **imprevisível** que o `Date` não entrega. **`POST /login`** com a senha do atacante → `401`. **Sem takeover.**
   - **Prova de isolamento:** o fluxo legítimo (o próprio usuário, com o token do "inbox") → funciona **idêntico** nos dois lados; só a **previsão** do token da vítima separa. A diferença é **100% a previsibilidade do gerador**.
   - **A lição do diff:** o fix é a **IMPREVISIBILIDADE** (`secrets`), **+ uso único + expiração** como o token bem-gerido (nota de honestidade-em-camadas — o eixo é a imprevisibilidade, não a expiração). (Forward pro DIFF.)

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). O token previsto/os headers/o request-response são **placeholders** da execução real capturada na Fase 2.

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5) — os CINCO

Isola a causa e desmonta os mal-entendidos vizinhos:

- **(a) NÃO é IDOR (03/11).** O token previsível **NÃO** é o id de um objeto que você acessa sem permissão; é o **SEGREDO de autenticação**. Prever o token **É** virar a vítima (o fluxo faz o que deveria: quem tem o token troca a senha), **não** acessar o recurso dela por baixo de um controle ausente. Prova: o `/reset` age no **dono do token** — não há id de objeto trocável.
- **(b) NÃO é um átomo de crypto (31/32).** Não se **quebra** hash nem cifra; nenhuma primitiva é forçada. O token é **reproduzido** porque o **gerador** é previsível — falha de **desenho de autenticação** (A07), não de **primitiva de cripto** (A02).
- **(c) NÃO é 'faltou autenticação'.** O fluxo **autentica** por posse do token — corretamente. O furo é o token ser **adivinhável**. O atacante não burla o check; ele **satisfaz** o check com o token **certo** (que calculou).
- **(d) NÃO é 'o token é curto'.** Aumentar o tamanho de um gerador **previsível** não ajuda: reproduzido o seed, o atacante gera o token **inteiro**, de qualquer comprimento. A fraqueza é a **PREVISIBILIDADE**, não o tamanho.
- **(e) NÃO é 'só faltou expiração/uso-único'.** O furo **central** é a **previsibilidade** (honestidade-em-camadas #4). Um token imprevisível que nunca expirasse ainda seria muito melhor que um previsível; adicionar expiração a um token **previsível** só dá ao atacante uma janela — ele ainda o adivinha **dentro** dela. Uso-único/expiração são o **fix completo**, não a causa.

**E, ancorando no irmão A07:** diferente do **`session-fixation` (15)** — onde o `session_id` é **forte** (`secrets`) e o furo é o **ciclo de vida** (ele sobrevive ao login) —, aqui o segredo (o token de reset) é **fraco/previsível**, e isso **É** o furo. O `15` até diz, no seu próprio "o que a vuln NÃO é", que *um id previsível seria um bug diferente*: este átomo **é** esse bug.

**O que É (prova):** o token de reset — uma credencial temporária — é gerado por um **PRNG seedado com um valor observável** (o relógio, via `Date`), logo **reproduzível**; o atacante **regenera** o token da vítima e reseta a senha dela. A correção é um **gerador imprevisível** (`secrets`); o acabamento honesto é uso-único + expiração.

---

## Impacto honesto

**Account takeover.** O atacante prevê o token de reset da vítima, **define** a senha dela, e **entra** na conta (o `POST /login` com a senha nova é a prova). O teto é o **controle da conta da vítima** — ler/agir como ela. **NÃO** inflar pra RCE nem pra "comprometimento total": o alcance é a conta cujo token foi previsto (embora, num alvo real, isso valha pra **qualquer** conta cujo reset o atacante consiga pedir — a mesma previsibilidade). O atacante **nunca** vê a senha antiga nem o token real; o poder vem **inteiramente** de o segredo ser calculável. **Sem foreshadow.** A classe "weak credential recovery" tem **outras faces** (token reusável, reset poisoning, host-header injection no link) — **descrição de UMA linha da classe, sem** modelar nem nomear átomo/variante futura; na dúvida, mandar o aluno aprofundar na PortSwigger Academy.

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY JSON** (o fluxo é REST puro — login/forgot/reset; decisão de forma óbvia pela categoria, como o `crypto-weak-hash` (31)). Garantir que a **ÚNICA** vuln é o **gerador previsível do token**:

- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (molde do 31) + no **README**.
- **O fluxo de reset e o login são código correto e da mesma forma nos dois lados** (o fluxo legítimo funciona igual); **sem** injection (queries parametrizadas), **sem** IDOR (o `/reset` age no dono do token), **sem** falha de hash de senha (werkzeug decente).
- **O `fixed` muda SÓ o gerador do token** (`make_reset_token`) **+ o ciclo de vida** (uso único + expiração no `/reset`). O resto do `app.py` é **idêntico**.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é a **IMPREVISIBILIDADE** (`secrets`), **NÃO** aumentar o token (armadilha #2) nem 'random melhor seedado' (armadilha #3); uso-único/expiração são parte do fix completo mas **NÃO** a falha central (honestidade #4).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar.**

- **PortSwigger PRIMEIRO — fit LIMPO provável.** A Academy tem uma trilha de **Authentication** robusta e cobre **vulnerabilidades em mecanismos de reset de senha**. Candidatos a **confirmar por fetch** (grafia/URL exatas): a página conceitual de **Authentication vulnerabilities** (candidato: `https://portswigger.net/web-security/authentication`) e, mais específica, a de **"Vulnerabilities in other authentication mechanisms"** / a seção de **password reset** dentro da trilha de authentication (candidato a localizar por fetch — a Academy tem material sobre reset tokens/reset flows). **Preferir a página mais específica de reset se houver uma conceitual limpa**; senão, a de Authentication vulnerabilities como conceitual raiz. **Provavelmente NÃO precisa de fallback OWASP** (diferente do 31/33/15, que caíram pro OWASP por ausência de página conceitual na Academy).
- **Texto do link:** preservar o nome da página em **inglês** também no README PT (`CLAUDE.md` §7).
- **NÃO inventar URL nem grafia** — **confirmar por fetch na Fase 2**; se não conseguir verificar uma página conceitual limpa, considerar o fallback OWASP (ex.: **OWASP: Forgot Password Cheat Sheet**, a confirmar) e **avisar o mantenedor** do desvio, como fizeram o 15 (OWASP) e o 31 (OWASP cheat sheet). Se nada verificar, **perguntar ao mantenedor** (`CLAUDE.md` §5).

---

## A trilha e a ferramenta — Burp-only + o script de previsão do atacante

O ataque inteiro é **HTTP dirigível no Burp** (Repeater); a **única ferramenta offline** é o **script de previsão** (roda o mesmo `random` — o Burp não faz isso, como não crackeia um hash no 31 nem ganha a corrida no 35). Disciplina (`CLAUDE.md` §3.3):

- **Mostrar o passo a passo no Burp:** `POST /forgot {victim}` (ler o `Date`), depois o **script de previsão** (mostrar o código — é a ferramenta central), depois `POST /reset {token previsto, nova senha}`, e a **prova** `POST /login {victim, nova senha}`. **Tudo no Burp** (+ `curl` como equivalente, se útil); o script de previsão é um `.py` local (candidato em `burp/` ou inline no WALKTHROUGH — decidir na Fase 2).
- **A prova NÃO exige execução client-side** (a prova é a resposta HTTP do `POST /login`) → **browser NÃO faz parte da trilha** (`CLAUDE.md` §3.3: browser só quando a prova exige — aqui não exige). **SEM trilha browser.**
- **SEM** cracker, **SEM** listener OOB, **SEM** Turbo Intruder. Single-container, tudo local. A única "ferramenta" extra é o **script de previsão** (e, opcional, `docker compose logs` pra ver o token no "inbox" na **validação/baseline** — **não** no ataque, que prevê).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A07 — Identification and Authentication Failures** (`atoms/A07-auth-failures/`, **JÁ EXISTE — REAPROVEITA**) | ROADMAP lista `weak-password-reset` em A07; `CLAUDE.md` §4 fixa a pasta abreviada (`auth-failures`, como o irmão `session-fixation`). Situar em A07 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Topologia | **SINGLE-CONTAINER por lado — SQLite embutido** (candidato; Postgres improvável) | Molde do `31`/`01`; precisa de estado (usuários+tokens) mas **não** de concorrência (≠ 35). Nota 4. |
| **O CORAÇÃO — o gerador** | **`random.seed(int(time.time()))` + `random.choice` → `secrets.token_urlsafe(32)`** | A falha é a **previsibilidade** do gerador; o fix é a imprevisibilidade. |
| Lição-coração | **O token de reset é uma CREDENCIAL TEMPORÁRIA gerada de forma PREVISÍVEL (PRNG seedado com o relógio, lido do `Date`); o atacante reproduz e toma a conta. Fix = CSPRNG (`secrets`) + uso único + expiração.** | Não se quebra cripto nem se injeta; o segredo não é secreto o suficiente. |
| Contraste central | **`session-fixation` (15)** — irmão A07; sub-formas opostas (sessão/ciclo-de-vida vs reset/previsibilidade) | Ancora o par A07. O 15 diz que "um id previsível seria um bug diferente" — este átomo é esse bug. |
| Contraste de apoio | **`31`** (molde + "não é crypto"), **`03`/`11`** ("não é IDOR"), **`35`/`36`** (voz atual), **`01`** (molde) | Publicados; ancoram molde/voz/contraste. Sem foreshadow. |
| Tipo de átomo | **API-only JSON** (sem HTML, sem templates, sem browser) | O fluxo é REST puro (login/forgot/reset), como o brief da categoria pede. |
| Trilha | **BURP-ONLY: Repeater + o script de previsão; sem browser** | O ataque é HTTP; a prova é o `POST /login`. O script roda o mesmo `random` (o Burp não faz). |
| Flavor — **TRAVADO** | **`POST /login` + `POST /forgot {email}` + `POST /reset {token,new_password}`; `GET /` banner JSON** | Fluxo canônico de A07. O fluxo é correto; a vuln é o gerador. |
| Datastore | **SQLite pros usuários (persiste o takeover), dict em memória pros tokens** (candidato) | Molde do 31 (SQLite) + do 15 (dict pros tokens efêmeros). A senha trocada tem que persistir pro login provar. |
| Lib / dep | **Flask + stdlib (`random`/`secrets`/`time`/`sqlite3`); `werkzeug` vem com o Flask** | O delta é módulo stdlib (`random`→`secrets`), **não** dependência. requirements idênticos (≠ 31, que trouxe bcrypt). |
| Entrega do token | **Ambos os lados LOGAM o token (stdout) como stand-in do e-mail; a resposta HTTP é genérica** | O baseline usa o "inbox"; o ataque **prevê** (não lê). Não é 2ª vuln — é a simulação da entrega (molde do id-na-tela do 15). |
| Senha dos usuários | **Hasheada com `werkzeug.generate_password_hash` (KDF salted)** | **NÃO** introduzir a vuln de storage do 31. A senha não é o foco; o token é. |
| Fix (eixo) | **`secrets.token_urlsafe(32)` + uso único (`pop`) + expiração (TTL 15 min)** | Imprevisibilidade é o eixo; uso-único/expiração são o token bem-gerido (defense-in-depth). |
| `random` "melhor seedado" | **NÃO é o fix — nota-armadilha #3** | O Mersenne Twister não é pra segurança em nenhum seed; a resposta é um CSPRNG. |
| "Token mais longo" | **NÃO é o fix — nota-armadilha #2** | Reproduzido o seed, o atacante gera o token inteiro, de qualquer tamanho. A fraqueza é a previsibilidade. |
| Uso-único/expiração | **Parte do fix completo, NÃO a falha central — honestidade #4** | Um token imprevisível eterno já seria muito melhor que um previsível. O eixo é a imprevisibilidade. |
| Diff | **No `make_reset_token()` (gerador) + no ciclo de vida do `/reset`** | Lógica-diferente no gerador do segredo (não flag, não versão de dep). |
| Impacto | **Account takeover.** Sem overclaim (não RCE). | Honesto; controle da conta da vítima. Sem foreshadow. |
| Theory primer | **PortSwigger primeiro (fit provável — Authentication/password reset); fallback OWASP só se não houver página conceitual** | A Academy cobre authentication/reset. Confirmar por fetch; avisar desvio se cair pro OWASP. |
| Título (H1) | **`weak-password-reset — Predictable password-reset token`** (classe, sem stack) | `CLAUDE.md` §5. Sem "Flask"/"Python"/"random"/"Mersenne" no H1; o slug já qualifica. Grafia final na Fase 2. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública); **sem** "fecha A07" | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release. |
| Portas | **8037 / 8137** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container por lado. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si** (molde do `31`/`01`, **API-only → SEM `COPY templates`**). Base `python:3.11-slim` (consistência com os irmãos):

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

- `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py`; **`init_db()` no `__main__`** cria e semeia o `lab.db` no boot (molde do 31 — sem bind mount, sem seed externo).
- `-u` (unbuffered) pra o token logado ("inbox", Item 4) aparecer na hora em `docker compose logs` (útil no baseline/validação).

**`docker-compose.yml`** (molde EXATO do `31`/`01` — dois serviços, **sem** datastore externo, **sem** healthcheck/`depends_on`/rede; apps bind **só** `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8037:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8137:5000"
```

- **§8:** ambos publicam porta **só** em `127.0.0.1`. Sem datastore externo (SQLite embutido), sem rede nomeada.
- **Confirmar na Fase 2** que `./atom up weak-password-reset` sobe os dois, que o `lab.db` semeia (vítima + atacante), e que o baseline (fluxo de reset legítimo) funciona de primeira nos dois lados.

---

## DECISÃO ABERTA pra Fase 2 — a granularidade/janela do seed (o nó técnico; registrar, NÃO travar)

A **reprodução do token previsto** é **comportamento de plataforma** e deve ser **PROVADA rodando** (**NÃO** é preferência editorial). O eixo está **TRAVADO** (seed = função do tempo; o `Date` entrega o tempo); o que confirmar, com o candidato registrado (Item 1):

- **A granularidade do seed.** Candidato: `int(time.time())` (segundos, UTC), casando com o segundo do header `Date` (GMT). **Provar** que o seed reproduzido bate o do servidor.
- **A janela `W`.** Se houver sub-segundo/clock skew, o atacante varre `t-W .. t+W`. Candidato **W = 2–3s**. **Documentar** o W que a Fase 2 provar.
- **A reprodução determinística.** O `vulnerable` **seeda e gera sem nada consumir o RNG no meio**, e **re-seeda a cada `/forgot`**; o atacante roda o **mesmo** esquema (alfabeto/N). **Provar** que o `random.seed(int)` reproduz idêntico entre o servidor e o script.
- **O formato do token** (alfabeto/N — Item 3) e **os nomes dos endpoints** (Item 2).
- **A URL do primer** (PortSwigger authentication/reset) — **confirmar por fetch**; não inventar.

**Protocolo (cravar):** registrar candidato, **rodar**, confirmar; capturar o **request/response real** (o `/forgot` com o `Date`, o token previsto pelo script, o `/reset`, e a **prova** — o `POST /login` como a vítima com a senha nova; e o `fixed` recusando). **Se não reproduzir**, ajustar dentro do escopo travado (**seed = função do tempo; gerador = `random` seedado**) — a granularidade/janela — e **PROVAR rodando**. **Se NADA reproduzir de forma reprodutível, PARAR e avisar o mantenedor — NÃO inventar** o token, o request/response, ou a saída do ataque.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes de design — exceto onde marcado "DECISÃO ABERTA".

1. **Baseline nos dois lados:** o fluxo de reset legítimo (`/forgot` pro próprio e-mail → token do "inbox" → `/reset` → `/login` com a senha nova) funciona **idêntico** no `vulnerable` **E** no `fixed`. **VALIDAR.**
2. **Usuários semeados:** vítima (`victim@lab`) + segundo (`attacker@lab`), senhas dummy **hasheadas** com werkzeug. **VALIDAR** que o `lab.db` semeia no boot.
3. **O ATAQUE (central — VALIDAR RODANDO / DECISÃO ABERTA):** prever o token da vítima pelo header `Date` (reproduzir `random.seed`) → `/reset` troca a senha dela → `/login` **entra** como a vítima com a senha que o atacante definiu. **Capturar** o `Date`, o token previsto (o script), o request e a prova. **Se não reproduzir, ajustar granularidade/janela e PROVAR; se NADA reproduzir, PARAR e avisar — NÃO inventar.**
4. **FIXED (`8137`):** o **mesmo** ataque → o token previsto **NÃO** bate o real (`secrets`) → o `/reset` recusa (`{"reset": false}`, 400) → o `/login` dá `401`. **Sem takeover.** **Capturar a diferença.**
5. **Prova de isolamento:** o fluxo de reset legítimo (o próprio usuário, token do "inbox") → **idêntico** nos dois lados; só a **previsão** do token da vítima separa, e a diferença é **100% a previsibilidade do gerador**. **VALIDAR.**
6. **Uma vuln só:** **sem** injection (queries parametrizadas), **sem** IDOR (o `/reset` age no dono do token), **sem** vuln de hash de senha (werkzeug decente); **único diff** `vulnerable`↔`fixed` = o `make_reset_token()` (+ o ciclo de vida no fix). **Confirmar por `diff`** (o resto do `app.py` idêntico).
7. **§8:** bind **só** `127.0.0.1` (8037/8137); usuários/senhas **dummy**; nada destrutivo/rede; o script de previsão roda só o `random`.
8. **O gerador vulnerável é o `random` seedado com `time`; o fix é `secrets`; a previsão reproduz.** **VALIDAR** que o `secrets.token_urlsafe(32)` fecha o ataque (token imprevisível).
9. **Primer confirmado por FETCH** (PortSwigger authentication/password reset; fallback OWASP só se preciso — avisar o desvio). **Não inventar.**
10. **DECISÃO ABERTA — granularidade/janela do seed** (seção dedicada): resolvida **rodando**; documentar o W. Se não reproduzir, **PARAR e avisar**.
11. **Diff isola o gerador do token:** o **ÚNICO** delta lógico entre `vulnerable/` e `fixed/` é o `make_reset_token()` (+ uso único/expiração no `/reset`); requirements idênticos. **Confirmar por `diff`.**
12. **As notas-armadilha** (tamanho não resolve — #2; `random` melhor-seedado não resolve — #3) **+ a honestidade** (uso-único/expiração são fix completo, não a falha central — #4) presentes no DIFF/WALKTHROUGH. **VALIDAR** que o átomo demonstra a **previsibilidade** como o eixo.

**Bloqueante remanescente:** nenhum de decisão de vuln. **DECISÕES ABERTAS de Fase 2 (probe/forma, não bloqueiam a spec):** a granularidade/janela do seed (Item 1); a topologia (SQLite single-container vs Postgres — candidato SQLite); os nomes dos endpoints e o formato do token; se o `vulnerable` inclui expiração/uso-único (candidato: ausentes); a URL do primer por fetch. **Protocolo:** registrar candidato, **rodar**, confirmar; se não reproduzir, ajustar dentro do escopo travado (**seed = função do tempo; gerador = `random` seedado → `secrets`**); se travar de vez, **PARAR e avisar — NÃO inventar** payload, request/response, saída ou URL.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **account takeover por um SEGREDO PREVISÍVEL** — o token de reset é uma **credencial temporária** gerada por um **PRNG seedado com o relógio** (lido do header `Date`), logo **reproduzível**. **Abrir e fechar** na lição-coração: *o furo é a PREVISIBILIDADE do gerador (`random` seedado → `secrets`); não se quebra cripto nem se injeta; uso-único/expiração são o acabamento honesto, não a causa.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`15` (session-fixation) INTEIRO** (irmão A07 — enquadramento da categoria + contraste de sub-forma + o beat "um id previsível seria um bug diferente"), **`31` (crypto-weak-hash) INTEIRO** (molde quase-exato: single-container SQLite, usuários semeados+hasheados, API-only JSON, `GET /`+`POST /login`; + o contraste "não é crypto"), **`03`/`11` (contraste "não é IDOR")**, **`35`/`36` (voz atual — abertura seca, definir termo, título=classe, headers PT, honestidade-em-camadas)**, **`01` INTEIRO** (molde canônico single-container Flask + estrutura de doc), esta spec. **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar encenação; **NÃO** copiar arqueologia OWASP; **headers de seção traduzidos em TODA doc PT** (§7); título = classe sem stack.
- **PONTO PEDAGÓGICO OBRIGATÓRIO (o brief):** o WALKTHROUGH **DEVE** (1) mostrar o **account takeover de ponta a ponta** — o atacante loga como a vítima com a senha que **ELE** definiu (a prova é o `POST /login`); (2) mostrar o **SCRIPT** do atacante que reproduz `random.seed(<Date>)` e gera o token (a ferramenta central da previsão); (3) cravar que o **header `Date` entrega o seed**; (4) **definir PRNG-vs-CSPRNG / seed / Mersenne-Twister / token-como-credencial / entropia / password-reset-flow / uso-único-e-expiração DO ZERO** na 1ª ocorrência; (5) os beats **"não é IDOR / não é crypto / não é 'faltou auth' / não é 'token curto' / não é 'só faltou expiração'"** + a âncora no `15`. **Sem esses cinco, o átomo não ensina a lição nem se distingue do IDOR.**
- **O ponto técnico frágil é a reprodução da previsão (riscos #3/#10) — comportamento de plataforma.** Fazer o ataque de verdade e confirmar que o token previsto **bate** o do servidor e que o `/reset`+`/login` provam o takeover, com a granularidade/janela documentada. **Se não reproduzir com o candidato, ajustar dentro do escopo travado (seed = função do tempo; `random` seedado → `secrets`) — a granularidade/janela — e PROVAR rodando; se NADA reproduzir, PARAR e avisar — NÃO inventar** o token, o request/response ou a saída.
- **Uma vuln só:** a **única** falha é o **gerador previsível** (`random` seedado com `time`). O fluxo de reset, o login e o storage de senha (werkzeug) estão **corretos**; **NÃO** modelar IDOR no `/reset` (agir no dono do token), **NÃO** modelar SQLi (queries parametrizadas), **NÃO** modelar hash fraco de senha (seria a vuln do 31). O `fixed` muda **SÓ** o gerador (+ uso único/expiração). **SEM 2ª vuln.**
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é a **IMPREVISIBILIDADE** (`secrets`), **NÃO** aumentar o token (armadilha #2) nem 'random melhor seedado' (armadilha #3). **Ser honesto** (honestidade-em-camadas #4): uso-único/expiração são propriedades **verdadeiras e necessárias** de um token bem-feito, mas a falha **central** é a **previsibilidade** — os dois não se anulam, e um leitor que saia achando "o fix é só pôr expiração" **perdeu** a lição.
- **Contraste com o 15 (cravar):** tabela + prosa; ambos A07, sub-formas **opostas** (sessão/ciclo-de-vida vs reset/previsibilidade). E o fix do 37 (`secrets.token_urlsafe`) é **exatamente** o gerador que o 15 já usa pro id — thread bonito. Citar o `15` (publicado) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5 + o brief):** password reset flow, token-como-credencial temporária, entropia/imprevisibilidade, PRNG vs CSPRNG, seed, Mersenne Twister, uso-único/expiração. **DO ZERO** — o átomo é denso de vocabulário de auth e de aleatoriedade.
- **A07 sem arqueologia:** situar em **A07 — Identification and Authentication Failures**, explicar **por que** (a falha está em **como a credencial é gerada** — desenho de autenticação —, não num controle de acesso nem numa primitiva de cripto), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 candidato `weak-password-reset — Predictable password-reset token`. "Python"/"`random`"/"`secrets`"/"Mersenne Twister" no corpo, não no H1 (o slug já qualifica). Grafia final na Fase 2 (alternativas: "Weak..." / "Predictable password-recovery token").
- **Política de referência cross-átomo:** OK citar **15** (irmão/contraste), **31** (molde/contraste), **03/11** (contraste), **35/36** (voz), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria/variante futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase, "fecha A07", ou outros A07/A09 futuros. **Manter as proibições genéricas.** **Esta spec é pública — nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`weak-password-reset — Predictable password-reset token`, grafia exata confirmável na Fase 2). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (token, reset, PRNG, CSPRNG, seed, Mersenne Twister, entropy, payload, `random`, `secrets`, single-use, expiry, account takeover) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): **PortSwigger primeiro** (fit provável — trilha de Authentication / reset de senha); **confirmar a URL/grafia por fetch**; fallback OWASP **só** se não houver página conceitual limpa (avisar o mantenedor do desvio, molde do 15/31); nome da página em inglês no PT. **Não inventar URL.**
- **A trilha é Burp-only + o script de previsão:** `POST /forgot {victim}` (ler o `Date`) → o **script** que reproduz `random.seed(<Date>)` e gera o token → `POST /reset {token, nova senha}` → **a prova**: `POST /login {victim, nova senha}`. **SEM** browser (a prova é a resposta HTTP do login). O `docker compose logs` (o token no "inbox") entra **só** no baseline/validação, **não** no ataque (que prevê).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, no padrão das linhas anteriores (candidato — ajustar na Fase 2): `` Added atom 37: `weak-password-reset` — Predictable password-reset token: a forgot-password flow issues a reset token — a temporary credential whose holder may set a new password — generated with Python's random module seeded from the clock (random.seed(int(time.time()))), so an attacker requests the victim's reset, reads the server time from the response's Date header, reproduces the seed, runs the same Mersenne Twister sequence to regenerate the exact token, resets the victim's password and logs in as her (account takeover); no crypto is broken and nothing is injected — the secret is simply predictable — and the fix swaps the generator for a CSPRNG (secrets.token_urlsafe), single-use and short-lived, so the predicted token no longer matches and the reset is refused (A07 Identification and Authentication Failures, CWE-640, CWE-330/CWE-337/CWE-338 candidate — confirm). `` **Confirmar o CWE por fetch na Fase 2** (candidatos: **CWE-640** "Weak Password Recovery Mechanism for Forgotten Password" — o mapping A07 mais direto; **CWE-330** "Use of Insufficiently Random Values"; **CWE-337** "Predictable Seed in PRNG"; **CWE-338** "Use of Cryptographically Weak PRNG"; não inventar). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 37 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir o baseline (fluxo legítimo idêntico nos dois lados) → o ataque real (prever o token da vítima → resetar → logar como ela) → o que a vuln NÃO é → `fixed` (mesmo ataque, token previsto não bate, sem takeover). Portas host podem não ser alcançáveis do sandbox — usar o fallback `docker compose exec` + dirigir o app de dentro do container (`python http.client`/`curl`), e o token do "inbox" via `docker compose logs`. **Sem** browser (a prova é o `POST /login`).
- **Commits sem trailer `Co-Authored-By`** (a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8037` (vulnerable), `127.0.0.1:8137` (fixed). Bind **só** `127.0.0.1` (§8). Single-container por lado (2 serviços, SQLite embutido, sem datastore externo).
- Se houver dúvida sobre a granularidade/janela do seed que reproduz, a topologia (SQLite vs Postgres), os nomes dos endpoints, o formato do token, se o `vulnerable` inclui expiração/uso-único, a URL do primer por fetch, o CWE, ou se a previsão não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**). **Candidato, se você quiser um pointer de recall reusável** (útil pra este átomo e pra futuros que toquem geração de segredos/aleatoriedade) — boa parte fica **registrada nesta spec commitada** (a regra desaconselha duplicar o que o repo grava). O que **justificaria** uma memória é a parte **não-repo, de ambiente/ferramenta**, e **só depois de confirmada rodando na Fase 2** (agora seria candidato não-verificado):

- **`predictable-prng-token-reproduction-via-date-header`** (candidato — **gravar só após provar na Fase 2**) — *"O átomo `weak-password-reset` (37, A07) demonstra account takeover por SEGREDO PREVISÍVEL: um token de reset gerado com `random.seed(int(time.time()))` + `random.choice` é reproduzível — o atacante lê o segundo do servidor no header `Date` da resposta, refaz o seed e gera o mesmo token. Reprodução determinística exige seedar-e-gerar sem outro consumo do RNG no meio, e re-seedar a cada request; janela de ±W segundos absorve o skew (W provado na Fase 2). Fix = `secrets.token_urlsafe(32)` (CSPRNG) + uso único + expiração — a IMPREVISIBILIDADE é o eixo, não o tamanho nem 'random melhor seedado'. Molde single-container SQLite do 31; requirements idênticos (o delta é módulo stdlib `random`→`secrets`). Contraste A07 com o 15 (sessão/ciclo-de-vida vs reset/previsibilidade)."* — tipo `reference`. **Confirmar os detalhes (granularidade/janela) rodando ANTES de gravar.**

**Ressalva:** só vale gravar se você quiser esse pointer pra futuros átomos que toquem geração de segredos/PRNG; e **só depois de a Fase 2 provar a mecânica** (agora é candidato). Senão, já está aqui na spec. Sua decisão. *(Ortogonal: na Fase 2, vale o padrão de validar via `docker compose exec` — dirigir o app de dentro do container se as portas host não forem alcançáveis do sandbox — e commits sem o trailer `Co-Authored-By`.)*
