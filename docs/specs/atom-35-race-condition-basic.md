# Spec — Átomo 35: `race-condition-basic`

> Documento de especificação para o Claude Code implementar o átomo `race-condition-basic` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo **ABRE uma categoria que NÃO EXISTE ainda — A04 (Insecure Design)**: a pasta `atoms/A04-insecure-design/` **não está no disco** e **deve ser criada** (nome confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos `A0X-<categoria-kebab>` — `A01-broken-access-control`, `A02-cryptographic-failures`, `A03-injection`, `A05-security-misconfiguration`, etc.). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É MULTI-CONTAINER — app + datastore Postgres.** **MOLDE do `nosql-injection-mongo` (22):** um **datastore compartilhado** (aqui **PostgreSQL**) que `vulnerable`/`fixed` alcançam **por nome numa rede interna**, com `depends_on: condition: service_healthy` e **healthcheck de readiness**; o datastore é **BUILDADO** (`build:`) com o seed **COPYado** pra dentro de uma imagem fina (**sem bind mount** — o SELinux do host bloqueia bind mount em container, ver o `mongo/Dockerfile` do 22), e **NÃO publica portas** (`ports:`) — só a rede interna. **Só o app** binda `127.0.0.1`. **NÃO** é o molde do `csrf-basic` (23), onde os serviços não se falam e não há rede/healthcheck. **O Flask roda MULTI-THREADED** — a concorrência real de requisições é **pré-requisito** pra a corrida existir.
>
> **A lição em uma linha:** código que muda estado normalmente **CHECA** uma condição e **então AGE** — "o saldo cobre o saque? sim → debita". Entre o **checar** e o **agir** há uma **fresta de tempo**. Se duas requisições chegam ao mesmo tempo, as duas passam pela checagem **ANTES** de qualquer uma escrever o resultado — as duas leem o saldo cheio, as duas debitam — e o estado final fica **errado** (saque além do saldo). É **TOCTOU** (time-of-check to time-of-use): a verdade que você checou fica **velha** no instante em que você **age** sobre ela. O atacante **não injeta nada** nem quebra credencial — dispara **N cópias da MESMA requisição legítima** simultaneamente e explora a fresta. O fix **NÃO** é "checar de novo" (a segunda checagem tem a mesma fresta) — é tornar o checar-e-agir **ATÔMICO**: deixar o banco **decidir-e-escrever numa tacada** que ele serializa (`UPDATE contas SET saldo = saldo - :amount WHERE id = :id AND saldo >= :amount`, checando se **1 linha** foi afetada).
>
> **O CORAÇÃO — o que separa este átomo de TODOS os anteriores (CRÍTICO).** Em cada átomo publicado até aqui a requisição do atacante carrega **algo diferente** da requisição normal: um payload de injection (`sqli-union-basic`, os XSS, `command-injection-basic`, `ssti-jinja`), um número trocado (`idor-numeric-id`), um campo a mais (`mass-assignment`), um cabeçalho forjado (`cors-wildcard`). **Aqui NÃO.** A requisição do atacante é **100% legítima, byte-idêntica à normal** — um saque comum de um valor que o saldo cobre. A **única** diferença é a **CONCORRÊNCIA**: N cópias da mesma request chegando **no mesmo instante**. A falha é **TEMPORAL** (a fresta entre checar e agir), **não** de conteúdo. Esse é o beat "o que a vuln NÃO é" central.
>
> **§3.3 — trilha primária Burp, MAS este átomo exige uma EXTENSÃO ativa: o TURBO INTRUDER (desvio de ferramenta JUSTIFICADO).** O ataque é **concorrência de requisições** — disparar N cópias da mesma request pra chegarem **juntas** ao servidor. O **Repeater/Intruder normal frequentemente NÃO ganha a corrida** (a rede **serializa** as requisições — o jitter faz uma chegar antes da outra, e a primeira já escreveu antes de a segunda checar). Pra vencer a corrida **de forma confiável** é preciso o **Turbo Intruder** (extensão gratuita do **BApp Store**, o repositório oficial de extensões do Burp) e o **single-packet attack** — a técnica que faz N requisições chegarem no mesmo instante. Isso **desvia** da disciplina usual do repo (Burp com, no máximo, as extensões passivas comuns — HaE, Logger++), que nenhum átomo publicado precisou romper; **mas é NECESSÁRIO** — é a ferramenta que reproduz uma corrida de forma confiável num lab. **Declarar o desvio** no WALKTHROUGH e no README (é a exceção de ferramenta deste átomo, como o `debug-enabled` (33) declarou a sua disciplina Burp-only). Ver Nota de planning 3 e "A trilha e a ferramenta".
>
> **REQUISITO DIDÁTICO (crítico — átomo denso de CONCEITO, não de vocabulário de protocolo).** O WALKTHROUGH e o README **DEVEM definir DO ZERO, na 1ª ocorrência**, assumindo que o aluno **não conhece nenhum**: **race condition** (dois fluxos concorrentes cujo resultado depende da ordem/timing), **TOCTOU** (time-of-check to time-of-use — a verdade checada fica velha no instante em que você age sobre ela), a **fresta/janela** entre checar e agir, **atomicidade** (uma operação indivisível — ou acontece inteira, ou não acontece), **exclusão mútua / lock** (garantir que só um fluxo entra na seção crítica por vez), **transação de banco** e o **UPDATE condicional** (decidir e escrever numa tacada só que o banco serializa), e o **single-packet attack** (mandar N requisições que chegam no servidor no mesmo instante). Definir com clareza de iniciante — **NÃO** assumir familiaridade. Ver "O MECANISMO em detalhe" e a Nota de planning 3.
>
> **NOTA DE TRANSPARÊNCIA DO SLEEP (obrigatória — muleta didática nomeada).** O `vulnerable/` inclui um `time.sleep` **mínimo** entre o check e o write pra **alargar a fresta** e a corrida reproduzir **de forma confiável** (regra de ouro do repo: o walkthrough reproduz **sempre**; sem o sleep a corrida depende de sorte de timing). Isso **NÃO** pode ser escondido: o WALKTHROUGH e o DIFF **declaram explicitamente** que (1) a fresta **EXISTE sem o sleep** (a vuln é **real**; o sleep não a cria, só a torna demonstrável — como uma senha fraca que faz o `hashcat` achar rápido num lab não "cria" a fraqueza) e (2) o fix (UPDATE condicional) fecha a janela **independente do tempo** — com o fix, o sleep vira **irrelevante** (a corrida não acontece nem com a fresta alargada). Ver "O sleep — muleta honesta".
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha Burp **com a exceção de ferramenta** deste átomo: o Turbo Intruder; §4 — **criação da categoria nova A04** (a pasta não existe — confirmar o nome contra o §4); §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A04 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind loopback** (o Postgres **sem** portas, só o app em `127.0.0.1`), dados fake; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referências vivas** — o **`nosql-injection-mongo` (22) INTEIRO** (o **MOLDE do datastore**: multi-container com datastore buildado sem portas, seed COPYado numa imagem fina, healthcheck + `depends_on: service_healthy`, rede interna), o **`sqli-union-basic` (01)** (molde canônico de estrutura de doc + Flask), e os **DOIS átomos publicados mais recentes — `cors-wildcard` (34) e `debug-enabled` (33)** (a **VOZ/estrutura ATUAL** — abertura seca, definir termo do zero, título=classe, headers PT traduzidos, honestidade-em-camadas nas notas-armadilha, o requisito didático, a declaração de disciplina de ferramenta).
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, `db/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `init.sql`, `requirements.txt`, `app.py`, script do Turbo Intruder — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e CRIAÇÃO da categoria A04 (nova)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). Justificativa do ROADMAP para este átomo: *"TOCTOU em lógica de negócio (ex: resgatar cupom 2x simultâneo)."*
>
> **A categoria A04 NÃO EXISTE ainda — o 35 CRIA a pasta.** `atoms/A04-insecure-design/` **não está no disco** (o `ls atoms/` lista A01, A02, A03, A05, A07, A08, A10 — **falta a A04**). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A04-insecure-design/`** (o §4 lista `A04-insecure-design/` contendo `race-condition-basic/`), casando com o padrão dos irmãos (`A0X-<categoria-kebab>`). Pasta final: **`atoms/A04-insecure-design/race-condition-basic/`** — **a Fase 2 cria a pasta de categoria e a do átomo**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A04 — Insecure Design"**.
>
> **Rótulo A04 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Uma falha de negócio cuja sequência check-then-act **não é atômica** — de forma que requisições concorrentes violam um invariante (saque além do saldo) — é **A04 — Insecure Design** no OWASP Top 10 2021 (a edição que o projeto segue). **NÃO** relatar em que número/categoria essa classe caía em edições antigas do OWASP Top 10 — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A04 — Insecure Design.** Explicar **por que** é A04 (o furo está no **desenho** do fluxo — decidir e agir em passos separados sem garantir atomicidade —, não num bug pontual de código nem numa validação ausente) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4, §12). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW (lei do projeto, `CLAUDE.md` §5; e esta spec é pública/commitada → nasce limpa).** **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec**: situar o átomo por **ordinal de fase**, **milestone**, **release/versão** (`v0.x`/`v1.0` etc.), ou como **abertura/encerramento** de qualquer coisa — **INCLUSIVE** "o único átomo de A04", "o primeiro de concorrência", "o que abre A04", ou qualquer referência a **outros átomos futuros** (A04 ou não). Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não-publicados**, **sem postular átomo futuro** (nada de "um próximo átomo vai mostrar outra corrida"). **A posição vive SÓ no `ROADMAP.md`.** Confirmo aqui apenas o **número (35)**, o **slug (`race-condition-basic`)** e a **categoria (A04)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo. **Pode citar átomos publicados (01–34)** à vontade (`CLAUDE.md` §5) — todos servem de contraste conceitual ("diferente de X, aqui o input é benigno").

## Nota de planning 3 — convenções ATUAIS: Burp + TURBO INTRUDER (desvio justificado), abertura seca, requisito didático, transparência do sleep

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **Trilha BURP com o TURBO INTRUDER — desvio de ferramenta JUSTIFICADO (`CLAUDE.md` §3.3 — Burp é a ferramenta principal).** O ataque é **concorrência**: disparar N cópias da **mesma** request legítima pra chegarem **juntas**. Uma corrida **não** se dispara de forma confiável no Repeater (você manda uma request por vez) nem no Intruder padrão (a rede **serializa** — o jitter entrega uma request antes da outra, e a 1ª já escreveu antes de a 2ª checar). A ferramenta que vence a corrida com confiabilidade é o **Turbo Intruder** (extensão gratuita do BApp Store) via **single-packet attack**. **Declarar o desvio** explicitamente — é a **exceção de ferramenta** deste átomo. Nenhum átomo publicado precisou de uma extensão ativa de exploração; este precisa, e a razão **é a própria lição** (uma corrida só se explora com requisições genuinamente simultâneas). **SEM** trilha browser (o ataque é HTTP puro; a prova é o **número** — o saldo final errado na resposta/no estado).
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (uma API de conta com saldo; `POST /withdraw` lê o saldo, checa se cobre o valor, e debita) e a falha (o checar e o agir são **passos separados**, com uma fresta no meio). **NADA** de encenação ("você é o pentester" e afins).
> - **REQUISITO DIDÁTICO — definir CADA conceito DO ZERO na 1ª ocorrência (`CLAUDE.md` §5 + o brief).** Este átomo é denso de **conceito** (não de vocabulário de protocolo, como o `cors-wildcard` (34) era). Definir do zero: **race condition**, **TOCTOU**, a **fresta/janela**, **atomicidade**, **exclusão mútua / lock**, **transação** + **UPDATE condicional**, **single-packet attack**. Ver a lista completa e as definições candidatas em "O MECANISMO em detalhe".
> - **NOTA DE TRANSPARÊNCIA DO SLEEP.** Declarar no WALKTHROUGH **e** no DIFF que o `time.sleep` do `vulnerable/` é uma **muleta didática** que alarga uma fresta **que já existe** (a vuln é real sem ele) e que o fix a torna **irrelevante**. **NÃO esconder o sleep.** Ver "O sleep — muleta honesta".
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** — **race condition (TOCTOU)** —, **NÃO** o motor ("...em Flask"/"...com Postgres"/"...em Python"). O **slug** (`race-condition-basic`) já qualifica a variante. O mecanismo (read-check-write vs UPDATE condicional, o backend Postgres, o Turbo Intruder) aparece no **corpo**, não no H1. Candidato de H1 em "Identidade".
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Disparar a rajada concorrente`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A04 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — topologia multi-container COM datastore Postgres (molde do 22), Flask MULTI-THREADED

> **App + datastore compartilhado (molde do `nosql-injection-mongo` (22), NÃO o do `csrf-basic` (23)).** No 22 o `mongo` era um **datastore compartilhado** que `vulnerable`/`fixed` alcançavam **por nome numa rede interna**, buildado sem portas, com seed COPYado e healthcheck de readiness. **Aqui é igual, com PostgreSQL no lugar do Mongo.** O contraste com o 23 (onde os serviços não se falam e não há rede/healthcheck) **não** se aplica — este átomo **precisa** do datastore compartilhado.
>
> **Consequências (LOCKED):**
> - **Serviço `db` (Postgres) BUILDADO** (`build: ./db`), com o `init.sql` **COPYado** pra `/docker-entrypoint-initdb.d/` numa imagem fina (`FROM postgres:<pin>` + `COPY`) — **sem bind mount** (SELinux; a exata razão do `mongo/Dockerfile` do 22).
> - **`db` NÃO publica portas** — só a **rede interna** (`networks: [lab]`), alcançável por **nome** (`db:5432`). Só `vulnerable`/`fixed` publicam no host (`127.0.0.1:8035`/`127.0.0.1:8135`).
> - **`healthcheck` (`pg_isready`) + `depends_on: db: condition: service_healthy`** nos dois apps — esperam o Postgres ficar pronto (o `init.sql` roda durante o init, antes de o Postgres aceitar conexões TCP externas, então um `pg_isready` que passa significa **seed concluído** — igual à garantia do 22).
> - **Flask MULTI-THREADED** (`app.run(..., threaded=True)`) — a concorrência real de requisições é **pré-requisito** pra a corrida. O estado compartilhado disputado vive **no Postgres** (não na memória do Flask), então threads bastam: cada thread pega a **própria conexão** ao banco, e o GIL do Python **libera** nas I/O do banco e no `sleep`, deixando as N requisições rodarem de fato concorrentes. Ver "Biblioteca / topologia" e "Decisões abertas / Item 1".
> - **§8 — app em loopback, Postgres sem exposição.** Ver "Decisões abertas" (a combinação reprodutível) e "§8 / isolamento".

---

## Decisões abertas — VOCÊ DECIDE / CONFIRME NA FASE 2 (PROPOR O QUE FUNCIONAR)

> O **objetivo** de cada item está **TRAVADO**; o que fica aberto é **qual valor/forma concreta** o realiza. O Item 1 é **comportamento de plataforma (Postgres + Flask + Turbo Intruder) que só se conhece TESTANDO** — um **probe de comportamento sério**, não preferência editorial.

### Item 1 (O NÓ TÉCNICO) — a COMBINAÇÃO que torna a corrida REPRODUTÍVEL (objetivo TRAVADO; a combinação a PROVAR RODANDO)

**O problema.** A corrida só ensina a lição se **reproduz de forma confiável** — no `vulnerable`, uma rajada concorrente faz **vários** saques passarem (saldo final **errado/negativo**); no `fixed`, a **mesma** rajada deixa **só um** passar (saldo final **correto**). A reprodutibilidade depende de uma **combinação** de fatores, e nenhum atalho editorial substitui **provar rodando**:

- **Backend PostgreSQL** (TRAVADO — não SQLite). O SQLite serializaria as escritas demais (lock de arquivo no banco inteiro) e **mascararia** a corrida; o Postgres dá concorrência de linha fiel. **Isto é a razão do datastore, não artifício.**
- **Nível de isolamento da transação** — candidato **`READ COMMITTED`** (o **default** do Postgres). É o que deixa a **fresta clássica** aberta no `vulnerable` (o `SELECT` lê o valor committed, a Python checa, o `UPDATE` escreve depois) **E** faz o `UPDATE` condicional do `fixed` ser **atômico e correto** (sob `READ COMMITTED`, o `UPDATE ... WHERE saldo >= :amount` re-avalia a condição contra a versão **corrente** da linha, sob o lock de linha, na hora de escrever — o recheck do Postgres). **Confirmar rodando** que `READ COMMITTED` reproduz os dois lados; **não** subir pra `SERIALIZABLE` sem necessidade (seria uma segunda solução legítima — ver as notas do DIFF —, mas o UPDATE condicional é o fix mínimo).
- **Nº de threads/workers do Flask** — candidato **`threaded=True`** no dev server (single-process, N threads), que **basta** porque o estado disputado está no Postgres (cada thread tem a própria conexão; o GIL libera nas I/O do banco e no `sleep`). Se threads **não** bastarem (não deve acontecer), a alternativa é um WSGI server multi-worker (`gunicorn --workers N`) — mas isso **adiciona dependência**; **preferir o dev server threaded**. **Provar** que a concorrência é real.
- **Tamanho do `sleep` mínimo** entre o check e o write no `vulnerable` — grande o suficiente pra **todas** as N leituras ocorrerem **antes** da 1ª escrita (é o que garante o overshoot dramático), pequeno o suficiente pra não parecer artificial. Candidato a calibrar rodando (ordem de dezenas a poucas centenas de ms). Ver "O sleep — muleta honesta".
- **Nº de requisições do Turbo Intruder** — candidato **~20** cópias da mesma request. Grande o suficiente pra o overshoot ser inequívoco (saldo bem negativo), pequeno o suficiente pra a rajada ser limpa.
- **A técnica do Turbo Intruder — o SUB-NÓ mais delicado.** O **single-packet attack** "próprio" (o que a PortSwigger inventou) usa **HTTP/2** pra empacotar o último byte de N requisições num **único pacote TCP**, neutralizando o jitter da rede. **O Flask dev server é HTTP/1.1** — não fala HTTP/2. Sobre HTTP/1.1, o mecanismo equivalente do Turbo Intruder é a **last-byte synchronization** (o *gate*: manda todos os bytes de cada request **menos o último**, segura, e libera todos os últimos bytes **juntos**) — a realização prática de "fazê-las chegar juntas". **Fase 2 tem que PROVAR qual técnica reproduz** contra o dev server HTTP/1.1 (candidato: o *gate*/last-byte-sync); se a corrida **exigir** HTTP/2, avaliar um proxy (ex.: nginx) na frente — mas isso **adiciona escopo**; o candidato é **HTTP/1.1 + gate**. Manter o **conceito** "N requisições chegando juntas" no WALKTHROUGH (definir "single-packet attack" do zero), e registrar honestamente a técnica concreta que provou reproduzir.

**O que a Fase 2 tem que PROVAR (rodando de verdade):** a combinação (backend + isolamento + threads + sleep + N + técnica do Turbo Intruder) que faz a corrida reproduzir **de forma confiável** — vários saques passam no `vulnerable` (saldo final errado/negativo), **só um** passa no `fixed` (saldo final correto). **PROPOR o que funcionar.** **Se a corrida NÃO reproduzir de forma confiável, ajustar dentro do escopo travado (read-check-write separado no vulnerable; UPDATE condicional no fixed) e PROVAR; se NADA reproduzir, PARAR e avisar o mantenedor — NÃO inventar o resultado da corrida.**

### Itens de forma (candidato registrado; a Fase 2 confirma pela via mais didática)

- **Item 2 — a forma exata do endpoint.** Candidato **recomendado: `POST /withdraw` com corpo JSON `{"amount": N}`** (o valor é explícito e fácil de fixar em `{"amount": 100}` na rajada do Turbo Intruder). Alternativa registrada: **resgatar um voucher de valor fixo** (`POST /redeem` sem corpo, valor fixo) — mesmo **mecanismo** (débito condicional). **Recomendo `withdraw`** (mais direto). Confirmar na Fase 2.
- **Item 3 — o mecanismo de reset/re-seed do saldo entre tentativas.** Candidato **recomendado: `POST /reset`** que seta o saldo de volta a 100 num único `UPDATE` (rápido pra iterar no Burp; comentar claramente que é **conveniência de lab**, não parte da feature modelada — como o `POST /login` é palco no 34). Alternativa: `docker compose restart db` (re-roda o `init.sql`). **Recomendo `POST /reset`**. Confirmar na Fase 2.
- **Item 4 — os status codes do `fixed` pro saque negado.** Candidato **`409 Conflict`** ("insufficient funds" — um conflito de estado) com **`400`** como alternativa. Sucesso = **`200`** (`{"withdrew": 100, "balance": 0}`). Confirmar na Fase 2.
- **Item 5 — o código exato do script do Turbo Intruder** (single-packet attack / gate). Candidato em "A prova"; **a provar rodando** (Item 1, sub-nó da técnica).

---

## Identidade

- **ID:** `race-condition-basic`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A04 — Insecure Design**. Pasta `atoms/A04-insecure-design/` (**NÃO EXISTE — o 35 CRIA**). Confirmado contra o `ROADMAP.md` ("A04 Insecure Design") e o `CLAUDE.md` §4. Em prosa, usar o nome da **classe** — **race condition (TOCTOU)** — e a categoria — **"A04 — Insecure Design"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A04-insecure-design/race-condition-basic/` (Fase 2 cria a pasta de categoria e a do átomo)
- **Número sequencial:** 35
- **Porta `vulnerable` (app):** `127.0.0.1:8035` (TRAVADO)
- **Porta `fixed` (app):** `127.0.0.1:8135` (TRAVADO)
- **Datastore (`db`, Postgres):** **NÃO publica portas** — só a rede interna (`db:5432`). Alcançado pelos apps por nome.
- **Bind:** **loopback** em todo `docker-compose.yml` (`CLAUDE.md` §8.1). Só os apps em `127.0.0.1` (8035/8135); o Postgres **sem** `ports:`. Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a loopback pelo compose — mesmo padrão dos irmãos.
- **Topologia:** **MULTI-CONTAINER — app + datastore:** `vulnerable` + `fixed` (Flask) + `db` (Postgres compartilhado). **Molde do `nosql-injection-mongo` (22):** rede interna, `db` buildado sem portas com seed COPYado, `healthcheck` + `depends_on: service_healthy`. **Flask MULTI-THREADED.**
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/abertura/encerramento** (§5 foreshadow).
- **Branch de trabalho:** `atom/race-condition-basic`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de Race conditions** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/race-conditions`** (título/grafia esperados: **"Race conditions"**), que cobre exatamente **TOCTOU, limit-overrun, e o single-packet attack** (que a própria PortSwigger inventou) — fit **limpo**. **Provavelmente NÃO precisa de fallback OWASP.** **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# race-condition-basic — Time-of-check to time-of-use (TOCTOU) race condition`** — `id` + nome canônico da **classe** em inglês (a classe é **race condition**; **TOCTOU** qualifica o mecanismo específico, expandido na 1ª ocorrência). **SEM** "Flask"/"Postgres"/"Python" no H1 (o slug já qualifica a variante). *(Alternativas registradas: `Race condition (TOCTOU)`, ou casar com o título da página do primer — `Race conditions`.)* Grafia canônica exata **confirmável na Fase 2** (casando, quando possível, com o título da página do primer); **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**Race condition (TOCTOU) — um check-then-act não-atômico que requisições concorrentes furam.** Uma API de conta com um **saldo** guardado no Postgres. `POST /withdraw {amount}` faz o padrão mais natural do mundo: **lê** o saldo atual (`SELECT`), **checa em Python** se ele cobre o valor (`if saldo >= amount`), e — se cobre — **escreve** o débito (`UPDATE saldo = saldo - amount`). Três passos separados. Entre o **checar** (passo 2) e o **agir** (passo 3) existe uma **fresta de tempo**: o instante em que a decisão "pode debitar" já foi tomada, mas a escrita ainda não aconteceu.

Numa execução única, isso funciona. O problema aparece com **concorrência**: se **duas** requisições de saque chegam **ao mesmo tempo**, as duas rodam o passo 1 e leem o **mesmo** saldo cheio (ex.: 100), as duas rodam o passo 2 e a checagem **passa** nas duas (100 ≥ 100), e só então as duas rodam o passo 3 e **debitam** — cada uma subtraindo 100 de um saldo que só cobria um saque. O estado final fica **errado** (saldo negativo, ou dois débitos de 100 de um saldo de 100). É **TOCTOU** — *time-of-check to time-of-use*: a verdade que você **checou** (o saldo cobre o valor) fica **velha** no instante em que você **age** (debita), porque **outra** requisição mexeu no mesmo estado no meio do caminho.

O atacante **não injeta nada, não quebra credencial, não forja cabeçalho**. Ele dispara **N cópias da MESMA requisição de saque legítima** — cada uma byte-idêntica a um saque normal — **simultaneamente**, e explora a fresta. A **lógica do endpoint está "certa" na aparência** (ele **tem** o check `saldo >= amount`); o furo é que o **check e a escrita são passos separados**, não uma operação indivisível.

### A lição-coração

> **"Código que muda estado normalmente CHECA uma condição e então AGE: 'o saldo cobre o saque? sim → debita'. Entre o checar e o agir há uma fresta de tempo. Se duas requisições chegam ao mesmo tempo, as duas passam pela checagem ANTES de qualquer uma escrever o resultado — as duas leem o saldo cheio, as duas debitam — e o estado final fica errado (saque além do saldo). É TOCTOU: a verdade que você checou fica velha no instante em que você age. O atacante não injeta nada nem quebra credencial — dispara N cópias da MESMA requisição legítima simultaneamente e explora a fresta. O fix NÃO é 'checar de novo' (a segunda checagem tem a mesma fresta) — é tornar o checar-e-agir ATÔMICO: deixar o banco decidir-e-escrever numa tacada (`UPDATE contas SET saldo = saldo - :amount WHERE id = :id AND saldo >= :amount`, checando se 1 linha foi afetada)."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH — DEFINIR CADA PEÇA NA ESTREIA)

O átomo assume que o aluno **não conhece nenhum** destes conceitos. Definir do zero, na 1ª ocorrência:

- **Race condition (condição de corrida).** Uma situação em que **dois (ou mais) fluxos de execução rodam concorrentes** e o **resultado depende da ORDEM/TIMING** em que eles chegam nos passos — se rodassem um de cada vez o resultado seria sempre certo, mas rodando ao mesmo tempo eles se **atrapalham**. O nome "corrida": dois fluxos correndo pelo mesmo recurso, e quem chega primeiro em cada passo muda o resultado.
- **Seção crítica.** O trecho de código que **lê e modifica um estado compartilhado** (aqui: ler o saldo e debitar). É onde a corrida acontece — dois fluxos dentro da seção crítica ao mesmo tempo se pisam.
- **TOCTOU (time-of-check to time-of-use).** O padrão específico de race deste átomo: você **checa** uma condição (*time of check* — "o saldo cobre?") e depois **age** com base nela (*time of use* — "debita"). Se o estado **muda** entre o check e o use, você agiu sobre uma verdade **velha**. A "corrida" é entre o seu fluxo e outro que altera o estado **na fresta** entre esses dois momentos.
- **A fresta / janela.** O intervalo de tempo **entre o check e o act** em que a decisão já foi tomada mas a escrita ainda não aconteceu. Quanto **maior** a fresta, mais fácil outro fluxo entrar nela. (É exatamente essa fresta que o `sleep` do `vulnerable` **alarga** — a muleta didática; ela **existe** sem o sleep, só é mais estreita.)
- **Atomicidade.** Uma operação é **atômica** quando é **indivisível**: ou ela acontece **inteira**, ou não acontece — **nenhum** outro fluxo consegue observar ou intercalar um estado no meio dela. O read-check-write em três passos **não** é atômico (há dois pontos onde outro fluxo entra). Um único `UPDATE ... WHERE` que decide **e** escreve numa tacada **é** atômico (o banco não deixa ninguém intercalar).
- **Exclusão mútua / lock.** O mecanismo de garantir que **só um fluxo por vez** entra na seção crítica — os outros **esperam** a vez. Um **lock** (trava) é a forma concreta: você "adquire" o lock antes da seção crítica e "libera" depois; enquanto um fluxo tem o lock, os outros bloqueiam. (Um lock **na aplicação** — `threading.Lock` — resolve **dentro de um processo**; ver a nota de honestidade-em-camadas no DIFF sobre por que ele não é a solução **geral**.)
- **Transação de banco.** Um agrupamento de operações no banco tratado como **uma unidade** — com garantias de isolamento entre transações concorrentes. O **nível de isolamento** (`READ COMMITTED` é o default do Postgres) define **o que** uma transação enxerga das outras enquanto elas rodam.
- **UPDATE condicional (o fix).** Um `UPDATE ... SET saldo = saldo - :amount WHERE id = :id AND saldo >= :amount` que **coloca a condição DENTRO da própria escrita**. O banco, ao executar, **trava a linha**, **re-avalia** a condição contra o valor **corrente** e **escreve** — tudo numa operação **serializada por linha**. O `rowcount` (quantas linhas o UPDATE afetou) diz o resultado: **1** = passou e debitou; **0** = a condição falhou (saldo insuficiente), nada mudou. Não há fresta: a decisão e a escrita são **a mesma** operação atômica.
- **Single-packet attack.** A técnica de mandar **N requisições que chegam no servidor no MESMO instante** — pra elas caírem todas na fresta antes de qualquer uma escrever. Sem isso, a rede **serializa** as requisições (o *jitter* — a variação de latência — entrega uma antes da outra), e a primeira já debitou antes de a segunda checar, matando a corrida. A técnica (que a PortSwigger inventou) neutraliza esse jitter. Definir o **conceito** ("fazê-las chegar juntas") no WALKTHROUGH; a **realização concreta** contra o dev server HTTP/1.1 (o *gate*/last-byte-synchronization do Turbo Intruder) é o sub-nó do Item 1, a provar rodando.

**O ponto contraintuitivo a cravar:** o `vulnerable` **NÃO** está "sem validação" — ele **tem** o check `saldo >= amount`, e num acesso único ele funciona. O furo é que o check e a escrita são **passos separados** (não-atômicos); a concorrência fura a fresta entre eles. Por isso "checar de novo" **não** conserta (a segunda checagem tem a **mesma** fresta) — o fix é a **atomicidade**.

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas do DIFF)

> **A causa é a NÃO-ATOMICIDADE do check-then-act (uma falha de DESENHO — A04), NÃO "faltou validação" nem "faltou um guard". A validação EXISTE (o vulnerable checa `saldo >= amount`); o guard EXISTE. O furo é que a validação/guard e a escrita são passos SEPARADOS, com uma fresta que a concorrência atravessa. O fix não é adicionar um check (já tem um) nem "checar de novo" (mesma fresta) — é tornar o decidir-e-escrever ATÔMICO: um UPDATE condicional que o banco serializa por linha.**

### Por que A04 (Insecure Design)

O bug **não é** "input virou código" (injection — A03: **não há** input malicioso; a request é legítima), **não é** "faltou um check de dono" (broken access control — A01: o fluxo não é sobre autorização), **não é** "o primitivo de crypto é fraco" (A02), **não é** "uma política/config perigosa" (A05). É um **defeito no DESENHO do fluxo de negócio**: a sequência "decidir com base num estado, depois agir sobre esse estado" foi desenhada em **passos separados**, sem garantir que a decisão e a ação fossem **indivisíveis** sob concorrência. O invariante de negócio ("nunca sacar além do saldo") depende de uma atomicidade que o desenho **não** garante. No Web Top 10 2021 isso é **A04 — Insecure Design**. Situar em **A04 — Insecure Design**, **sem** contar edições antigas. Explicar **por que** é design (o furo é estrutural — o padrão check-then-act não-atômico —, não um typo nem uma validação esquecida) é a lição.

---

## Contraste — não há input malicioso (o eixo que separa este átomo de TODOS os anteriores)

O eixo que torna este átomo diferente de **tudo** que veio antes: **não há input malicioso**. Em cada átomo publicado, a request do atacante carrega **algo** que a distingue da normal:

| Átomo publicado (contraste) | O que muda na request do atacante |
|---|---|
| `sqli-union-basic` (01), os XSS, `command-injection-basic`, `ssti-jinja` | um **payload** — o input carrega sintaxe/código |
| `idor-numeric-id` (03) | um **número trocado** (`/notes/1` → `/notes/2`) — dado legítimo, mas **diferente** |
| `mass-assignment` (25) | um **campo a mais** no corpo (`"is_admin": true`) |
| `cors-wildcard` (34) | um **cabeçalho forjado** (`Origin:` do atacante) |
| **`race-condition-basic` (35)** | **NADA.** A request é **byte-idêntica** a um saque legítimo. |

**PONTO AFIADO A CRAVAR:** aqui a request do atacante é **100% legítima** — um saque comum de um valor que o saldo cobre. A **única** diferença entre o uso normal e o ataque é a **CONCORRÊNCIA**: N cópias da **mesma** request chegando no **mesmo instante**. A falha é **TEMPORAL** (a fresta entre checar e agir), **não** de **conteúdo**. Um contraste especialmente útil é com o `idor-numeric-id` (03, publicado): lá o exploit já era "dado legítimo" (trocar um número), mas **ainda mudava a request**; aqui **nem isso** — a request não muda em nada, só a **simultaneidade**. Citar átomos publicados como contraste ("diferente de X, aqui o input é benigno") é bem-vindo (`CLAUDE.md` §5). **Sem** foreshadow (nada de "um átomo futuro mostra outra corrida").

---

## Uma vuln só — o guard EXISTE; a única falha é a NÃO-ATOMICIDADE

Invariante inegociável do átomo (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é a **não-atomicidade do check-then-act**. Para garantir isso:

- **O endpoint TEM o guard.** O `vulnerable` **checa** `saldo >= amount` antes de debitar. A falha **NÃO** é ausência de check — é o check **não ser atômico** com a escrita. **NÃO** modelar o `vulnerable` como um `UPDATE saldo = saldo - amount` **sem** guard nenhum (isso seria "faltou validação", uma vuln **diferente**). O `vulnerable` **precisa** ter o read → check → write em passos separados.
- **A autenticação/validação de forma é comum e correta.** Se houver identificação de conta, ela funciona igual nos dois lados. **Não é a vuln.** (Modelar como conta única semeada mantém o átomo mínimo — ver "Flavor".)
- **O `fixed` muda SÓ a atomicidade** (read-check-write separado → UPDATE condicional + `rowcount`). O endpoint, o corpo, a rota — **idênticos** no que não seja a atomicidade da operação de débito. O `sleep` do `vulnerable` **some** no `fixed` (não há passo separado a alargar).
- **Sem 2ª vuln:** **sem** injection (o `amount` é parametrizado — nada de SQL string), **sem** falha de auth, **sem** leitura de arquivo, **sem** mass assignment. O único diff é a **atomicidade da operação de débito**.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é a **ATOMICIDADE** (UPDATE condicional / o banco serializa), **NÃO** "checar de novo" (armadilha #2 — mesma fresta), **NÃO** **só** um lock de aplicação (parcial — resolve num processo, não escala; nota de honestidade-em-camadas #3).

---

## Flavor — saque/débito de saldo (TRAVADO)

Cenário canônico de TOCTOU em lógica de negócio: **uma conta com saldo, e um débito condicional que não é atômico.**

- **APP (Flask, API-only JSON, `vulnerable` :8035 / `fixed` :8135):**
  - **`POST /withdraw`** — corpo JSON `{"amount": N}` (Item 2). **Lê** o saldo (`SELECT`), **checa em Python** `if saldo >= amount`, e — se cobre — **debita** (`UPDATE saldo = saldo - amount`). É o coração da vuln no `vulnerable`; no `fixed`, é um **UPDATE condicional atômico**.
  - **`POST /reset`** (Item 3) — seta o saldo de volta a 100 num único `UPDATE`. **Conveniência de lab** (iterar tentativas no Burp), **não** a vuln — comentar claramente. Atômico e trivial.
  - **`GET /`** — banner JSON de aviso (molde dos átomos API-only 22/33/34) + dica de uso (`POST /withdraw {"amount": ...}`, trabalhar do Turbo Intruder). **Banner de aviso** (`CLAUDE.md` §8.2) vive no README e no `GET /` JSON.
  - **(Opcional) `GET /balance`** — devolve o saldo corrente (pra o aluno **ver** o número final errado sem inspecionar o banco). Registrar como candidato pró-observabilidade; confirmar na Fase 2 se `POST /withdraw` já devolve o saldo na resposta (então `/balance` é redundante).
- **DATASTORE (`db`, Postgres):** tabela **`accounts`** semeada com **uma** conta (`id = 1`, `balance = 100`) via `init.sql`. Dados fake (§8).

**O ATAQUE (resumo; detalhe em "A prova"):** resetar o saldo pra 100; disparar **~20** `POST /withdraw {"amount": 100}` **simultâneas** (Turbo Intruder, single-packet/gate); no `vulnerable`, **vários** passam (várias respostas 200 "withdraw ok" quando **só uma** deveria) e o saldo final fica **errado/negativo** (ex.: −1900 com 20 saques de 100 de um saldo de 100). **PROVA:** um **número inequívoco** — o saldo final **negativo**, ou a **soma dos saques bem-sucedidos > saldo inicial**. **FIXED:** a **mesma** rajada → **só UMA** passa (200), as outras **falham** (409/400 "insufficient funds"); saldo final **correto** (0).

Este átomo é **API-only** — **sem** `templates/index.html`. A interação é direta via **Burp/Turbo Intruder** (a "UI" que ensina é a **rajada concorrente** e o **número final**). Categoria naturalmente API-only, como o `nosql-injection-mongo` (22) e o `debug-enabled` (33).

---

## A prova — a corrida, reprodutível (TRAVADO; probe de comportamento SÉRIO na Fase 2)

A prova é o **número**: o saldo final que **viola o invariante**. Cadeia:

1. **Reset:** `POST /reset` → saldo = 100 (ou re-seed).
2. **Rajada (vulnerable :8035):** ~20 `POST /withdraw {"amount": 100}` **simultâneas** via **Turbo Intruder** (single-packet/gate). Todas caem na fresta antes de qualquer escrita → **várias** passam pelo check → **várias** respostas **200** ("withdraw ok"); o saldo final fica **negativo** (ex.: −1900) ou a soma dos saques bem-sucedidos excede 100.
3. **Fixed (:8135):** reset; a **mesma** rajada → **só UMA** resposta **200**; as outras **409/400** ("insufficient funds"); saldo final **0** (correto). O banco **serializou** a decisão-e-escrita por linha.

**Candidato de script do Turbo Intruder (Item 5 — a PROVAR rodando; a técnica concreta é o sub-nó do Item 1):**

```python
# Turbo Intruder -- fire N identical withdrawals as simultaneously as possible.
# gate/last-byte synchronization is the HTTP/1.1 realization of "arrive together"
# (the Flask dev server is HTTP/1.1, not HTTP/2). Phase 2 proves the technique.
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           engine=Engine.THREADED)
    for i in range(20):
        engine.queue(target.req, gate='race')   # hold at the gate
    engine.openGate('race')                      # release all at once

def handleResponse(req, interesting):
    table.add(req)                               # inspect: how many 200s?
```

**PROBE DE COMPORTAMENTO (Fase 2, version/ambiente-dependent — NÃO determinístico):** o Claude Code tem que **PROVAR a corrida rodando de verdade** e achar a **combinação** (Postgres + isolamento + threads + sleep + N + técnica do Turbo Intruder) que a torna **reprodutível de forma confiável**. **Gate:** "não reproduziu de forma confiável → **PARA e avisa**, **NÃO** inventa o resultado da corrida". Registrado como decisão-aberta (Item 1). §8: dados dummy, `127.0.0.1`, nada destrutivo (é um débito de saldo fake).

### Prova de isolamento (o que traça a diferença PURO à atomicidade)

- **Saque único, NÃO-concorrente:** um **único** `POST /withdraw {"amount": 100}` (sem rajada) → resultado **IDÊNTICO** nos dois lados: saldo 100 → 0, resposta 200. E um segundo saque único de 100 sobre saldo 0 → **negado** nos dois lados (o `vulnerable` **também** nega, porque sequencialmente o check funciona). **Prova que o `vulnerable` NÃO está "sem check"** — o check existe e funciona **sem concorrência**. **Só** a rajada **concorrente** separa os lados.
- **Rajada concorrente:** no `vulnerable`, vários passam (saldo errado); no `fixed`, só um passa (saldo correto). A diferença é **100% a atomicidade** da operação de débito, **não** a presença/ausência do check nem uma dependência.

---

## O sleep — muleta honesta (TRAVADO, com transparência obrigatória)

O `vulnerable/` inclui um `time.sleep` **mínimo** entre o check e o write pra **alargar a fresta** e a corrida reproduzir **de forma confiável**. Isto é uma **muleta didática nomeada** — e a transparência é **obrigatória** no WALKTHROUGH **e** no DIFF:

1. **A fresta EXISTE sem o sleep.** A vuln é **real**: o read-check-write em passos separados tem a janela **inerentemente**, com ou sem o sleep. O sleep **não cria** a vuln — só a **alarga** o suficiente pra a demo reproduzir **sempre** (a regra de ouro do repo). Analogia a cravar: uma senha fraca não fica fraca porque o `hashcat` a acha rápido num lab; o lab só torna a fraqueza **demonstrável**. O sleep é isso pra a corrida.
2. **O fix torna o sleep IRRELEVANTE.** O `fixed` (UPDATE condicional) fecha a janela **independente do tempo** — não há read-check-write separado pra ter fresta. Com o fix, a corrida **não acontece** nem com a fresta alargada. **Demonstração de honestidade opcional a registrar:** mesmo que se **adicione** um `sleep` idêntico **antes** do UPDATE condicional no `fixed`, ele **ainda** vence a corrida — provando que a correção é a **atomicidade**, **não** "o fixed é mais rápido". Registrar como beat candidato pró-honestidade (confirmar na Fase 2 se entra no WALKTHROUGH ou fica só como nota do DIFF).
3. **NÃO esconder o sleep.** Ele aparece no código do `vulnerable` **com um comentário** que o nomeia como muleta didática, e o WALKTHROUGH/DIFF o declaram. Um leitor que veja o sleep e pense "então a vuln é o sleep" tem que sair da leitura corrigido: a vuln é a **não-atomicidade**; o sleep só a torna visível.

---

## O código — o coração no read-check-write vs UPDATE condicional (candidatos)

O fio condutor: **o débito é um check-then-act não-atômico**. O `app.py` **DIFERE** entre `vulnerable` e `fixed` **na operação de débito** (read-check-write separado → UPDATE condicional + `rowcount`); todo o resto — `GET /`, `POST /reset`, os imports, a conexão ao banco — é **IDÊNTICO**.

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma a combinação reprodutível (Item 1), captura as requests/responses reais, e PROVA a corrida rodando.**

### `victim` `vulnerable/app.py` — read → check em Python → sleep → write (candidato)

```python
import os
import time
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

def db():
    # A fresh connection per request -- so N concurrent requests get N concurrent
    # DB sessions (sharing one connection across threads would serialize them and
    # hide the race). Postgres default max_connections (100) covers the burst.
    return psycopg2.connect(os.environ["DATABASE_URL"])

@app.route("/withdraw", methods=["POST"])
def withdraw():
    amount = (request.get_json(silent=True) or {}).get("amount")
    conn = db()
    cur = conn.cursor()
    # VULNERABLE: check-then-act in THREE separate steps. Between the check
    # (step 2) and the write (step 3) there is a gap. Under concurrency, N
    # requests all read the full balance and all pass the check BEFORE any of
    # them writes -- so all of them debit. The guard EXISTS; it just isn't
    # atomic with the write. That non-atomicity is the whole bug (see DIFF.md).
    cur.execute("SELECT balance FROM accounts WHERE id = 1")     # 1. read
    balance = cur.fetchone()[0]
    if balance >= amount:                                        # 2. check (in Python)
        time.sleep(0.1)  # DIDACTIC CRUTCH: widens a window that already exists,
                         # so the race reproduces every time (see WALKTHROUGH/DIFF).
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = 1",
                    (amount,))                                   # 3. write (no SQL guard)
        conn.commit()
        cur.execute("SELECT balance FROM accounts WHERE id = 1")
        new_balance = cur.fetchone()[0]
        conn.close()
        return jsonify({"withdrew": amount, "balance": new_balance})
    conn.close()
    return jsonify({"error": "insufficient funds"}), 409

if __name__ == "__main__":
    # threaded=True: real concurrency is a prerequisite for the race to exist.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, threaded=True)
```

### `victim` `fixed/app.py` — UPDATE condicional atômico + rowcount (candidato)

```python
# ... imports, db(), GET /, POST /reset IDENTICAL to vulnerable ...

@app.route("/withdraw", methods=["POST"])
def withdraw():
    amount = (request.get_json(silent=True) or {}).get("amount")
    conn = db()
    cur = conn.cursor()
    # FIXED: decide-and-write in ONE atomic statement. The condition lives in the
    # WHERE clause, so Postgres locks the row, re-checks `balance >= amount` against
    # the CURRENT value, and writes -- all serialized per row. No read-check-write
    # gap, so no window to race. rowcount tells the result: 1 = debited, 0 = the
    # condition failed (insufficient funds) and nothing changed.
    cur.execute(
        "UPDATE accounts SET balance = balance - %s "
        "WHERE id = 1 AND balance >= %s",
        (amount, amount),
    )
    if cur.rowcount == 1:
        conn.commit()
        cur.execute("SELECT balance FROM accounts WHERE id = 1")
        new_balance = cur.fetchone()[0]
        conn.close()
        return jsonify({"withdrew": amount, "balance": new_balance})
    conn.close()
    return jsonify({"error": "insufficient funds"}), 409
```

**O CONTRASTE é o diff:** read → check-em-Python → sleep → write **separados** (vulnerable) vs **UPDATE condicional atômico + `rowcount`** (fixed). O `GET /`, o `POST /reset`, os imports, a conexão — **idênticos**. O `sleep` **some** no fixed (não há passo separado a alargar).

### Notas de implementação (validar/decidir na Fase 2)

- **Conexão por request** (não compartilhar uma conexão entre threads — psycopg2 não é thread-safe pra isso; e um pool menor que N **serializaria** e mataria a corrida). Postgres `max_connections` default (100) cobre N=20. Confirmar rodando.
- **`READ COMMITTED`** (default do Postgres) — deixa a fresta no vulnerable e faz o UPDATE condicional do fixed atômico (o recheck sob lock de linha). **Não** subir pra `SERIALIZABLE` sem necessidade (Item 1).
- **`amount` parametrizado** (`%s`) — **nada** de string SQL montada (sem SQLi de brinde; §8 e "uma vuln só").
- **`threaded=True`** no `app.run` — a concorrência real é pré-requisito (Item 1).
- **`init.sql`** semeia `accounts(id, balance)` com `(1, 100)`. Ver "O container".

---

## O fix e o tipo de diff

**Fix:** tornar o check-then-act **ATÔMICO** — trocar o read → check-em-Python → write (três passos) por um **UPDATE condicional** que o banco serializa por linha (`UPDATE ... SET balance = balance - :amount WHERE id = :id AND balance >= :amount`), checando o **`rowcount`** (1 = debitou, 0 = saldo insuficiente). A atomicidade da operação de débito é o **único delta** entre `vulnerable` e `fixed`. Tipo de diff: **lógica-diferente** (a estrutura da operação muda de "ler, checar, esperar, escrever" pra "decidir-e-escrever numa tacada"); o `sleep` **desaparece** (não há passo separado).

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é a NÃO-ATOMICIDADE (falha de DESENHO — A04), NÃO "faltou validação"/"faltou guard".** O `vulnerable` **JÁ checa** `balance >= amount`; a validação **existe**. A falha é o check e a escrita serem **passos separados**, com uma fresta que a concorrência atravessa. **Prova de isolamento:** um saque **único** (não-concorrente) funciona **idêntico** nos dois lados (o check do vulnerable funciona sem concorrência); **só** a rajada concorrente separa. A diferença é **100% a atomicidade**, não a presença do check.
2. **"Checar de novo depois" NÃO é o fix — nota-ARMADILHA.** Nomear a intuição: *"é só reler o saldo e checar mais uma vez antes de escrever."* Mostrar que uma **segunda** checagem tem a **MESMA** fresta — entre a segunda checagem e a escrita há outra janela, e a concorrência a atravessa igual. **Adicionar checagens não fecha a janela**; só a **atomicidade** (a decisão e a escrita como **uma** operação) fecha. *(Honestidade-em-camadas: a intuição parece razoável, mas não resolve.)*
3. **Lock na aplicação (`threading.Lock`) — nota de HONESTIDADE EM CAMADAS (solução PARCIAL legítima, não armadilha pura).** Um lock em torno do check-then-act **FUNCIONA** num **único processo** (é exclusão mútua **real** — só um fluxo entra na seção crítica por vez, então a corrida entre threads some). **MAS não é a solução geral:** não escala pra **múltiplos workers/processos/servidores** — cada processo tem o **próprio** lock em memória, e dois processos rodando o mesmo código não compartilham a trava, então a corrida volta **entre processos**. O **UPDATE condicional** deixa o **BANCO** (o ponto único **compartilhado** por todos os processos) garantir a atomicidade — a solução **idiomática e escalável**. Nomear o lock como **solução-parcial-legítima-num-processo**, no espírito das notas do salt/CBC/PIN dos átomos recentes — **não** como armadilha pura.
4. **O `sleep` é muleta didática (ver a nota de transparência) — o fix o torna irrelevante.** O `time.sleep` do `vulnerable` **alarga** uma fresta que **já existe** (a vuln é real sem ele) pra a demo reproduzir sempre; o `fixed` (UPDATE condicional) fecha a janela **independente do tempo**, então o sleep vira **irrelevante**. **NÃO esconder** — declarar aqui e no WALKTHROUGH. *(Beat opcional: o fix vence mesmo com um sleep adicionado antes do UPDATE — prova que é atomicidade, não velocidade.)*
5. **Impacto: violação de INVARIANTE DE NEGÓCIO.** Saldo negativo / débito além do saldo / limite (cupom, estoque) excedido. **Sem overclaim** — não é RCE, não é roubo de credencial. O **teto** é o estado inconsistente que a corrida produz.

**HONESTIDADE — a transação `SERIALIZABLE` também resolve.** Uma transação com nível de isolamento **`SERIALIZABLE`** (que faz o Postgres abortar uma das transações concorrentes com um erro de serialização, forçando retry) **também** conserta a corrida — é um contexto **legítimo**. **MAS** o **UPDATE condicional** é o fix **mínimo e mais direto** (uma query, sem gerenciar retries de transação abortada). **Enquadrar as duas coisas:** o UPDATE condicional é o fix idiomático do átomo; `SERIALIZABLE` é a alternativa correta de maior escopo. **Não** apresentar `SERIALIZABLE` como "o único jeito" nem escondê-la.

---

## Biblioteca / topologia

- **App (`vulnerable`/`fixed`):** **Flask + psycopg2 (Postgres driver)**. `requirements.txt`: **Flask** (pin candidato **`Flask==3.0.0`**, casando com os irmãos) + **`psycopg2-binary`** (pin candidato **`psycopg2-binary==2.9.9`** — o `-binary` evita precisar de toolchain de compilação no `python:3.11-slim`; alternativa registrada: `psycopg[binary]` (psycopg 3)). **Confirmar** que instalam em `python:3.11-slim` por probe na Fase 2. **`requirements.txt` IDÊNTICOS** entre `vulnerable` e `fixed` — o delta é a **query** (a operação de débito), **NÃO** uma dependência (molde do 32/33: fix é código, não manifesto).
- **Datastore (`db`):** **PostgreSQL** (imagem oficial, pin candidato **`postgres:16`** — confirmar na Fase 2). **Buildado** (`build: ./db`) com o `init.sql` **COPYado** pra `/docker-entrypoint-initdb.d/` (sem bind mount — SELinux; a razão do `mongo/Dockerfile` do 22). **NÃO publica portas.** Env: `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` dummy (§8). Healthcheck `pg_isready`.
- **Flask MULTI-THREADED** (`threaded=True`) — a concorrência é pré-requisito (Nota 4). O estado disputado está no Postgres; threads bastam (conexão por request; GIL libera na I/O e no sleep).
- **SEM "SAÍDA B" clássica — MAS o ambiente pode MASCARAR a corrida (registrar honestamente).** O read-check-write ingênuo é o que um iniciante escreve — não há uma "ferramenta que resiste" como em alguns átomos. **PORÉM** a escolha de **backend/config** importa pra a corrida ser **FIEL e explorável**: o **SQLite serializaria demais** (lock de arquivo do banco inteiro) e **esconderia** a corrida — **por isso Postgres**; e o **nível de isolamento** e a **concorrência real** (threads) importam. **Declarar** que a escolha de backend/config é pra a fresta ser **fiel**, **não** artifício. A Fase 2 confirma o isolamento (candidato `READ COMMITTED`, o default) e o nº de threads/workers (Item 1).

---

## §8 / isolamento — o app em loopback, o Postgres sem exposição

- **App:** `127.0.0.1:8035` (vulnerable) e `127.0.0.1:8135` (fixed) — literal `127.0.0.1`.
- **Postgres (`db`):** **sem `ports:`** — só a rede interna (`db:5432`), **nunca** publicado no host. Alcançado pelos apps por nome. (Mesma postura do `mongo` do 22.)
- **Todos os serviços local-only.** `CLAUDE.md` §8.1. Sem exposição à rede/internet. Dados **dummy** (uma conta fake, saldo fictício 100); credenciais do Postgres **dummy** (`POSTGRES_PASSWORD` óbvio, ex.: `changeme`).
- **Nada destrutivo.** O "exploit" é um débito de um **saldo fake** num banco de lab — o dano é o **número errado** (invariante violado), nada além do container. Reset trivial (`POST /reset`).
- **CI linter de port-binding (ROADMAP, ainda não existe) — sem desvio a documentar.** O binding dos apps é o literal `127.0.0.1` (8035/8135), casando com o parser do wrapper `./atom`; o Postgres não binda porta nenhuma. **Sem** o desvio de IP que outros multi-container precisaram.

---

## WALKTHROUGH — abertura seca; Burp + TURBO INTRUDER; DENSO EM DEFINIÇÕES; headers PT traduzidos

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (uma API de conta: `POST /withdraw` lê o saldo, checa se cobre o valor, e debita) e a falha (o checar e o agir são **passos separados**, com uma fresta no meio que a concorrência atravessa). Trilha **Burp com o Turbo Intruder** (desvio de ferramenta declarado); **SEM** browser (o ataque é HTTP puro; a prova é o **número**).

**Abertura (candidato — plantar a lição, seco):**

> *A app é uma API de conta. `POST /withdraw` faz o mais natural do mundo: lê o seu saldo, checa se ele cobre o valor que você quer sacar, e — se cobre — debita. Três passos. Entre o passo de checar ("o saldo cobre?") e o passo de agir ("debita") existe uma fresta de tempo: um instante em que a decisão "pode sacar" já foi tomada, mas o débito ainda não aconteceu. Rode um saque de cada vez e nada dá errado. Mas mande vinte saques do valor inteiro do saldo ao MESMO tempo, e todos os vinte leem o saldo cheio, todos passam pela checagem antes de qualquer um debitar — e todos debitam. Você saca vinte vezes um dinheiro que só dava pra sacar uma. Você não injetou nada, não forjou nada: mandou a MESMA requisição legítima, só que ao mesmo tempo.*

Beats (molde do 01/22/33/34 — abertura seca, seções numeradas `## 1..7`):

1. **Context.** Feature: `POST /withdraw` lê o saldo, checa `saldo >= amount`, debita. **Definir na estreia (REQUISITO DIDÁTICO — do zero):** **race condition** (dois fluxos concorrentes cujo resultado depende do timing), **seção crítica**, **TOCTOU** (a verdade checada fica velha no instante em que você age), a **fresta/janela**, **atomicidade** (operação indivisível), **exclusão mútua/lock**, **transação** + **UPDATE condicional**, **single-packet attack** (N requisições chegando juntas). Isto é **A04 — Insecure Design**. Topologia: app (`vulnerable` :8035, `fixed` :8135) + Postgres interno. Trilha: Burp + **Turbo Intruder** (declarar o desvio de ferramenta).
2. **Spot the bug.** Mostrar o `withdraw` do `vulnerable/app.py` — o read → check-em-Python → sleep → write em **três passos**. Apontar que o endpoint **TEM** o guard (`if balance >= amount`) — o bug **NÃO** é falta de check; é o check **não ser atômico** com a escrita. Nomear a fresta. Foreshadow do fix: um **UPDATE condicional atômico**. Declarar o `sleep` como **muleta didática** (a fresta existe sem ele; ver a nota de transparência).
3. **Baseline (não-concorrente — prova que o check FUNCIONA).** Um `POST /withdraw {"amount": 100}` **único** → saldo 100 → 0, resposta 200. Um segundo saque único de 100 sobre saldo 0 → **negado** (409). **Idêntico** nos dois lados. Isto prova que o `vulnerable` **não** está "sem check" — sequencialmente ele funciona. **Só** a concorrência fura.
4. **Exploitation (Turbo Intruder — a rajada concorrente; a prova é o número).**
   - **4a — por que o Repeater/Intruder normal NÃO ganha a corrida.** Explicar: mandar uma request por vez (Repeater) nunca dispara a corrida; o Intruder padrão **serializa** (a rede tem jitter — uma request chega antes da outra, e a 1ª já debitou antes de a 2ª checar). **Definir single-packet attack:** a técnica de fazer N requisições chegarem **juntas** (a PortSwigger a inventou). Declarar o desvio: precisa do **Turbo Intruder** (extensão do BApp Store).
   - **4b — montar a rajada.** Mostrar o **script/config do Turbo Intruder** (Item 5) — o *gate*/last-byte-sync que segura N requisições e as libera juntas. ~20 cópias de `POST /withdraw {"amount": 100}`.
   - **4c — disparar (vulnerable :8035).** Reset (`POST /reset`) → saldo 100. Disparar a rajada → **várias** respostas **200** ("withdraw ok"); ver o **saldo final negativo** (ex.: −1900). **A prova é o número.** Contar as respostas 200 (Turbo Intruder mostra a tabela) e mostrar o saldo final.
   - **§8 (cravar):** débito de saldo **fake** num banco de lab; tudo loopback; nada destrutivo.
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'".
6. **Impact (honesto — sem overclaim).** Ver "Impacto honesto".
7. **Why the fix works (porta 8135).** Reset; a **MESMA** rajada contra o `fixed` → **só UMA** resposta **200**; as outras **409/400** ("insufficient funds"); saldo final **0**. **Cravar:** o banco **serializou** a decisão-e-escrita por linha (o UPDATE condicional trava a linha, re-avalia `balance >= amount` contra o valor corrente, e escreve — atômico). **Prova de isolamento:** o saque **único** funciona nos dois lados; **só** a rajada concorrente separa. **A lição do diff:** o fix é a **atomicidade** (nota #1), **NÃO** "checar de novo" (armadilha #2), **NÃO** só um lock de aplicação (parcial #3); o `sleep` é muleta e o fix o torna irrelevante (#4); impacto = invariante de negócio violado (#5). (Forward pro DIFF.)

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Requests/responses/números são **placeholders** da execução real capturada na Fase 2 (a rajada real no Turbo Intruder, a contagem de 200s, o saldo final negativo no vulnerable / correto no fixed). Explicar por que o Repeater/Intruder normal não ganha a corrida (a rede serializa) e o single-packet attack resolve.

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5) — os QUATRO/CINCO

Isola a causa e desmonta os mal-entendidos vizinhos (os do brief):

- **(a) NÃO é input malicioso/injection.** A requisição é **100% LEGÍTIMA, byte-idêntica** à normal (um saque comum de um valor que o saldo cobre). A **única** diferença é a **CONCORRÊNCIA** (N cópias ao mesmo tempo). **Este é o contraste central com TODOS os átomos anteriores** — neles a request do atacante carrega um payload/número/campo/cabeçalho diferente; aqui **nada** muda na request, só a **simultaneidade**. A falha é **temporal**, não de conteúdo.
- **(b) NÃO é "faltou validação".** O `vulnerable` **JÁ checa** `balance >= amount`; a validação **existe**. Ela só não é **atômica** com a escrita. *(Prova de isolamento: o saque único funciona idêntico nos dois lados.)*
- **(c) NÃO é "faltou um guard/limite".** O guard **está lá**; a falha é **temporal** (a fresta), **não** a ausência do check. Adicionar mais guards não fecha a janela — só a atomicidade fecha.
- **(d) NÃO é bug pontual de código.** É falha de **DESENHO** (A04): a sequência check-then-act **não-atômica** é o **padrão-problema**, não um typo nem uma linha esquecida. Por isso é **A04 — Insecure Design**, não A03 nem A01.
- **(e) NÃO se conserta "checando de novo".** A segunda checagem tem a **MESMA** fresta (a armadilha #2 do DIFF) — entre ela e a escrita há outra janela. Só a **atomicidade** (a decisão e a escrita como uma operação só) fecha.

**O que É (prova):** o read-check-write em passos separados tem uma **fresta** entre o check e a escrita; N requisições legítimas simultâneas caem todas na fresta antes de qualquer escrita, todas passam pelo check, e todas escrevem — violando o invariante (saldo negativo). A correção é tornar o check-then-act **atômico** (UPDATE condicional que o banco serializa por linha).

---

## Impacto honesto

**Violação de invariante de negócio** — o estado inconsistente que a corrida produz: **saldo negativo**, **débito além do saldo**, **limite/cupom/estoque excedido** (sacar duas vezes o mesmo dinheiro, resgatar o mesmo voucher N vezes, comprar mais do que há em estoque). **Sem overclaim:** **NÃO** inflar pra RCE, **NÃO** pra roubo de credencial, **NÃO** pra account takeover. O **teto** é o **estado inconsistente** que a corrida produz — o invariante que o desenho deveria garantir e não garantiu. A **prova do lab** é o **número**: o saldo final negativo (vulnerable) vs correto (fixed). A classe "race condition / TOCTOU" tem **outras faces** (outras seções críticas não-atômicas) — **descrição de UMA linha da classe**, **sem** modelar nem nomear átomo/variante/técnica futura (foreshadow, Nota 2). Sem foreshadow.

---

## Renderização / "um átomo = uma vuln"

**API-only — SEM `templates/index.html`** (categoria naturalmente API-only, como 22/33). A "UI" que ensina é a **rajada concorrente** no Turbo Intruder e o **número final**. Garantir que a **ÚNICA** lição é a **não-atomicidade do check-then-act**:

- **O endpoint TEM o guard.** O `vulnerable` checa `balance >= amount`. A falha **NÃO** é ausência de check — é o check não ser **atômico** com a escrita. **NÃO** modelar o `vulnerable` sem guard (seria "faltou validação", vuln diferente).
- **`POST /reset` e `GET /` NÃO são a vuln.** São palco/conveniência (resetar o saldo entre tentativas; banner). A **única** superfície é a **operação de débito** não-atômica.
- **O `fixed` muda SÓ a atomicidade** (read-check-write → UPDATE condicional + `rowcount`). O resto — idêntico. O `sleep` some no fixed.
- **`amount` parametrizado** — sem SQLi de brinde. **Sem** datastore-injection, **sem** falha de auth, **sem** 2ª superfície.
- **Sem segredo real** (credenciais do Postgres dummy; conta/saldo fake). Estado no Postgres, semeado por `init.sql`.

**SUTILEZA:** o fix é a **ATOMICIDADE** (UPDATE condicional / o banco serializa), **NÃO** "checar de novo" (armadilha #2) nem **só** um lock de aplicação (parcial, #3).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/race-conditions`** — a página conceitual de Race conditions (título/grafia esperados: **"Race conditions"**, abertura "What are race conditions?"). Ela cobre **exatamente** o que o átomo modela: **TOCTOU**, **limit-overrun**, e o **single-packet attack** (que a própria PortSwigger inventou e documenta ali) — fit **limpo**. É a página de introdução da vuln, não a de labs.
- **Provavelmente NÃO precisa de fallback OWASP** — o tópico de Race conditions da PortSwigger cobre a classe inteira deste átomo, **incluindo** a ferramenta (o single-packet attack no Turbo Intruder).
- **Texto do link:** **"Race conditions"** — a forma que a própria PortSwigger usa. Preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7).
- **NÃO inventar URL nem grafia** — confirmar por fetch na Fase 2.

---

## A trilha e a ferramenta — Burp + TURBO INTRUDER (desvio justificado); por que o Repeater/Intruder normal não ganha a corrida

O ataque é **concorrência** — a prova exige requisições genuinamente **simultâneas**. Disciplina (`CLAUDE.md` §3.3, com a **exceção de ferramenta** deste átomo):

- **O Repeater NÃO serve** — ele manda **uma** request por vez; nunca há concorrência.
- **O Intruder padrão frequentemente NÃO ganha a corrida** — mesmo com threads, a **rede serializa** (o *jitter* — variação de latência — faz uma request chegar antes da outra, e a 1ª já debitou antes de a 2ª checar). A corrida **depende de sorte de timing** — inaceitável pra a regra de ouro do repo (o walkthrough reproduz **sempre**).
- **O TURBO INTRUDER ganha (desvio de ferramenta JUSTIFICADO)** — extensão gratuita do **BApp Store** (o repositório oficial de extensões do Burp). Via **single-packet attack** (ou, contra o dev server HTTP/1.1, o *gate*/last-byte-synchronization equivalente), ele faz as N requisições chegarem **juntas**, neutralizando o jitter — a corrida reproduz de forma **confiável**. **Declarar o desvio:** nenhum átomo publicado precisou de uma extensão ativa de exploração; este precisa, e a razão **é a própria lição** (uma corrida só se explora com requisições genuinamente simultâneas). É o análogo, do lado da ferramenta, do que o `debug-enabled` (33) fez ao declarar a sua disciplina Burp-only.
- **SEM** browser (o ataque é HTTP puro; a prova é o **número** — o saldo final na resposta/estado). **SEM** listener OOB, **SEM** cracker. Multi-container, app em loopback, Postgres interno.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A04 — Insecure Design** (`atoms/A04-insecure-design/`, **NÃO EXISTE — CRIAR**) | ROADMAP lista `race-condition-basic` em A04; `CLAUDE.md` §4 fixa a pasta. Situar em A04 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow (sem "único A04"/"primeiro de concorrência"). |
| Topologia | **MULTI-CONTAINER — app + datastore** (`vulnerable` + `fixed` + `db` Postgres) | Molde do `22`: datastore compartilhado, rede interna, buildado sem portas, seed COPYado, healthcheck + `depends_on: service_healthy`. |
| Backend do datastore | **PostgreSQL** (não SQLite) | O SQLite serializaria as escritas e **mascararia** a corrida; o Postgres dá concorrência de linha **fiel**. É a razão do datastore, não artifício. |
| Concorrência do app | **Flask `threaded=True`** (estado no Postgres; conexão por request) | A concorrência real é pré-requisito. Threads bastam (GIL libera na I/O e no sleep). Workers só se threads não bastarem (Item 1). |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe** (uso-direto-do-antipadrão) | O read-check-write ingênuo é o que um iniciante escreve. *(Mas o backend/config importa pra a corrida ser FIEL — Postgres, isolamento, threads.)* |
| Coração técnico | **read → check-em-Python → sleep → write** (separados) vs **UPDATE condicional atômico + `rowcount`** | O check e a escrita serem passos separados é a fresta; o UPDATE condicional os funde numa operação serializada por linha. |
| Lição-coração | **Check-then-act não-atômico → concorrência fura a fresta → invariante violado. Fix = atomicidade (UPDATE condicional), NÃO "checar de novo".** | A verdade checada fica velha no instante em que você age (TOCTOU). |
| Sub-lição crítica | **A causa é a NÃO-ATOMICIDADE (design — A04), NÃO "faltou validação"/"faltou guard"** | O vulnerable JÁ checa `balance >= amount`; a falha é o check e a escrita serem passos separados. |
| Contraste central | **NÃO há input malicioso** — a request é 100% legítima, byte-idêntica à normal; só a **concorrência** separa | O eixo que separa este átomo de TODOS os anteriores (payload/número/campo/cabeçalho). |
| Ferramenta | **Burp + TURBO INTRUDER (single-packet/gate)** — desvio de ferramenta declarado | O Repeater/Intruder normal não ganha a corrida (a rede serializa). Extensão do BApp Store; necessária pra a corrida confiável. |
| Sleep | **Muleta didática nomeada** (alarga uma fresta que já existe; o fix o torna irrelevante) | Transparência obrigatória no WALKTHROUGH e no DIFF. A vuln é real sem o sleep. |
| Flavor — **TRAVADO** | **Conta com saldo no Postgres; `POST /withdraw {amount}` read-check-write; ataque = rajada concorrente de `{amount:100}`** | A ÚNICA superfície é a operação de débito não-atômica. Guard presente. |
| Prova — **TRAVADO** | **Saldo final NEGATIVO / soma dos saques > saldo inicial** (vulnerable); **só um 200, saldo correto** (fixed) | A prova é o **número** inequívoco. Benigno, saldo fake, loopback (§8). |
| Fix (único eixo) | **read-check-write separado → UPDATE condicional atômico + `rowcount`** | Correção na raiz (atomicidade). NÃO "checar de novo" (#2), NÃO só lock de app (parcial #3). |
| Impacto | **Violação de invariante de negócio** (saldo negativo / débito além do saldo). Sem overclaim (não é RCE/cred/takeover). | Honesto; teto = o estado inconsistente da corrida. Sem foreshadow. |
| Theory primer | **PortSwigger "Race conditions"** (`/web-security/race-conditions`, confirmar por fetch) | Cobre TOCTOU + limit-overrun + single-packet attack. Fit limpo; provável sem fallback OWASP. Não inventar. |
| Título (H1) | **`race-condition-basic — Time-of-check to time-of-use (TOCTOU) race condition`** (classe, sem stack) | `CLAUDE.md` §5. Slug qualifica a variante. Sem "Flask"/"Postgres"/"Python". Grafia final na Fase 2. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública); **sem** "único A04"/"primeiro de concorrência" | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release. Publicados 01–34 OK como contraste. |
| Portas | **8035 / 8135** (app, bind `127.0.0.1`); Postgres **sem** portas (rede interna) | `CLAUDE.md` §8. Multi-container, molde do 22. |
| Renderização | **API-only** (sem `templates/index.html`) | A "UI" é a rajada no Turbo Intruder + o número final. Como 22/33. |
| **Item 1 — combinação reprodutível** | **ABERTO — VOCÊ DECIDE/PROVE NA FASE 2** (Postgres + `READ COMMITTED` + `threaded=True` + sleep + N + técnica do Turbo Intruder) | Comportamento de plataforma; probe sério. Se NADA reproduzir de forma confiável, PARAR e avisar — NÃO inventar a corrida. |

---

## O container

**`vulnerable/Dockerfile`, `fixed/Dockerfile`** (API-only → **SEM `COPY templates`**), molde dos irmãos:

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

**`db/Dockerfile`** (Postgres buildado, seed COPYado — molde do `mongo/Dockerfile` do 22):

```dockerfile
FROM postgres:16
# Bake the seed into the image so it runs on first init, with no bind mount.
# (Bind-mounting the seed is the usual approach, but SELinux on the host blocks
# bind mounts into containers, so the seed is COPYed into a thin image instead.)
COPY init.sql /docker-entrypoint-initdb.d/
```

**`db/init.sql`** (candidato — semeia uma conta; dados fake §8):

```sql
-- Seeded into a fresh Postgres on first init: the official image runs any .sql in
-- /docker-entrypoint-initdb.d/ before it starts accepting TCP connections, so a
-- passing pg_isready means the seed is done. One fake account. Fake balance.
CREATE TABLE accounts (id INT PRIMARY KEY, balance INT NOT NULL);
INSERT INTO accounts (id, balance) VALUES (1, 100);
```

**`docker-compose.yml`** (candidato — molde do `22`: **rede interna + `db` sem portas + healthcheck + `depends_on: service_healthy`**; a Fase 2 gera o real e prova a corrida):

```yaml
services:
  db:
    build: ./db
    # No ports: -- the datastore is reachable only on the internal network,
    # never published to the host.
    environment:
      - POSTGRES_USER=lab
      - POSTGRES_PASSWORD=changeme        # dummy, lab-only (CLAUDE.md §8)
      - POSTGRES_DB=labdb
    healthcheck:
      # Apps wait for this (condition: service_healthy). Postgres runs the seed
      # during init, before it accepts TCP connections, so a passing check means
      # the seed is done.
      test: ["CMD-SHELL", "pg_isready -U lab -d labdb"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 5s
    networks:
      - lab
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8035:5000"
    environment:
      - DATABASE_URL=postgresql://lab:changeme@db:5432/labdb
    depends_on:
      db:
        condition: service_healthy
    networks:
      - lab
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8135:5000"
    environment:
      - DATABASE_URL=postgresql://lab:changeme@db:5432/labdb
    depends_on:
      db:
        condition: service_healthy
    networks:
      - lab

networks:
  lab:
```

- **`db` sem `ports:`** — só a rede interna `lab`, alcançável por nome (`db:5432`). Só os apps publicam no host (loopback).
- **Healthcheck + `depends_on: service_healthy`** — os apps esperam o Postgres ficar pronto (seed concluído). Molde do 22.
- **§8:** apps em **loopback** (8035/8135); Postgres **sem** exposição. Credenciais/dados **dummy**.
- **Confirmar na Fase 2** que `./atom up race-condition-basic` sobe os três serviços, o seed roda, e a corrida reproduz (Item 1).

---

## DECISÃO ABERTA pra Fase 2 — a combinação reprodutível (o nó técnico; registrar, NÃO travar)

A **combinação que torna a corrida reprodutível** (Item 1 da seção "Decisões abertas") é o **nó técnico** deste átomo — comportamento de **Postgres + Flask + Turbo Intruder** que deve ser **PROVADO rodando** (**NÃO** é preferência editorial). Resumo do que confirmar (candidato registrado no Item 1):

- **Backend Postgres** (travado — não SQLite) + **nível de isolamento** (candidato `READ COMMITTED`, o default — deixa a fresta no vulnerable e faz o UPDATE condicional atômico no fixed).
- **Concorrência real:** Flask `threaded=True` (candidato) + **conexão por request** (não compartilhar conexão entre threads; pool ≥ N). Confirmar que N requisições rodam de fato concorrentes.
- **Tamanho do `sleep`** (calibrar: grande o bastante pra todas as leituras precederem a 1ª escrita, pequeno o bastante pra não parecer artificial) e **N** do Turbo Intruder (candidato ~20).
- **A técnica do Turbo Intruder** (sub-nó delicado): o *gate*/last-byte-synchronization (HTTP/1.1) vs o single-packet attack próprio (HTTP/2, que o dev server não fala). Provar qual reproduz contra o dev server; se exigir HTTP/2, avaliar proxy (adiciona escopo — evitar).
- **A forma do endpoint** (Item 2 — `withdraw {amount}` recomendado), o **reset** (Item 3 — `POST /reset` recomendado), os **status codes** do fixed (Item 4 — 409/400), o **script exato do Turbo Intruder** (Item 5).

**Protocolo (cravar):** registrar candidato, **rodar** de verdade, confirmar; capturar as **requests/responses reais** (a rajada no Turbo Intruder, a contagem de 200s, o saldo final negativo no vulnerable / correto no fixed). **Se não reproduzir de forma confiável**, ajustar dentro do escopo travado (**read-check-write separado no vulnerable; UPDATE condicional no fixed**) — o isolamento, as threads/workers, o sleep, o N, a técnica do Turbo Intruder — e **PROVAR rodando**. **Se NADA reproduzir de forma confiável, PARAR e avisar o mantenedor — NÃO inventar** o resultado da corrida, a contagem de saques, ou o saldo final.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–4 são os centrais; 5–12 são higiene/isolamento. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes — **exceto o Item 1 (a combinação reprodutível, marcado VOCÊ DECIDE), que fecha na Fase 2 por probe.**

1. **Baseline (os dois lados).** Um saque **único** legítimo funciona nos dois lados (o saldo debita corretamente: 100 → 0, resposta 200; um segundo saque de 100 sobre 0 é negado). **VALIDAR.**
2. **Reset/re-seed.** O `POST /reset` (ou re-seed) volta o saldo a 100. **VALIDAR.**
3. **O ATAQUE (VALIDAR RODANDO — o probe de comportamento; provar reprodutibilidade).** A rajada concorrente (Turbo Intruder single-packet/gate) no `vulnerable` → **várias** respostas **200** + saldo final **ERRADO/negativo**. **CAPTURAR** a rajada real, a contagem de 200s, o saldo final. **Se não reproduzir de forma confiável, PARAR e avisar — NÃO inventar** a corrida.
4. **FIXED (VALIDAR RODANDO).** A **MESMA** rajada → **só UMA** resposta **200**, o resto **negado** (409/400), saldo final **correto** (0). **CAPTURAR.**
5. **Prova de isolamento.** Um saque **único** (não-concorrente) → resultado **IDÊNTICO** nos dois lados (o check do vulnerable funciona sem concorrência); **só** a concorrência separa. **VALIDAR.**
6. **Uma vuln só.** **Sem** injection (`amount` parametrizado), **sem** falha de auth; o `vulnerable` **TEM** o guard (`balance >= amount`); o único diff = a **atomicidade** (read-check-write → UPDATE condicional). **Confirmar por `diff`.**
7. **§8.** Bind `127.0.0.1` (apps 8035/8135); **Postgres sem `ports:`**; dados/credenciais **dummy**; nada destrutivo (débito de saldo fake). **Sem** desvio de IP a documentar.
8. **Postgres + Flask multi-threaded sobem limpo.** `healthcheck` + `depends_on: service_healthy`; o `init.sql` semeia a conta; a corrida é **FIEL** (o ambiente não a mascara — Postgres, não SQLite; `READ COMMITTED`; threads reais). **VALIDAR** `./atom up`.
9. **Theory primer confirmado por FETCH** (`/web-security/race-conditions`, título "Race conditions"). Provável **sem** fallback OWASP. Se em dúvida, perguntar ao mantenedor. **Não inventar.** Confirmar a **grafia exata do H1**.
10. **A combinação reprodutível (Item 1 — VOCÊ DECIDE; resolvida RODANDO).** Postgres + isolamento + threads/workers + sleep + N + técnica do Turbo Intruder. **PROPOR o que funcionar. Se NADA reproduzir, PARAR e avisar.**
11. **O diff isola SÓ a atomicidade** (read-check-write separado → UPDATE condicional + `rowcount`); `requirements.txt` idênticos (o delta é a query, não uma dependência); o `sleep` some no fixed.
12. **O `sleep` é declarado transparentemente** (WALKTHROUGH + DIFF) como muleta didática, e o **fix o torna irrelevante** (a corrida não acontece nem com a fresta alargada; opcional: o fix vence mesmo com um sleep adicionado — prova que é atomicidade, não velocidade).

**Bloqueante remanescente:** nenhum de decisão de vuln. **O Item 1 (a combinação reprodutível) fecha na Fase 2 por probe** — não é pendência de design, é "propor o que funcionar rodando". **Pendências de Fase 2 (não bloqueantes agora):** provar a corrida rodando (itens 3, 4, 10); a forma do endpoint (Item 2); o reset (Item 3); os status codes (Item 4); o script do Turbo Intruder (Item 5); confirmar a URL/H1 do primer por fetch (item 9); confirmar os pins do Flask/psycopg2/Postgres por probe; gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **primeiro em que a request do atacante é benigna** — 100% legítima, byte-idêntica à normal; **só a concorrência** separa. Cada beat deve poder ser lido com essa verdade no centro: a falha é **temporal** (a fresta entre checar e agir), **não** de conteúdo. **Abrir e fechar** na lição-coração: *check-then-act não-atômico → concorrência fura a fresta → invariante violado; o fix é a atomicidade (UPDATE condicional), não "checar de novo".*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`22` (nosql-injection-mongo) INTEIRO** (o **MOLDE do datastore** — multi-container com datastore buildado sem portas, seed COPYado numa imagem fina, healthcheck + `depends_on: service_healthy`, rede interna), **`01` (sqli-union-basic) INTEIRO** (molde canônico Flask + estrutura de doc), **`34` (cors-wildcard)** e **`33` (debug-enabled)** (voz/estrutura ATUAL — abertura seca, definir termo do zero, título=classe, headers PT, honestidade-em-camadas, a **declaração de disciplina de ferramenta**), esta spec. **Seguir o `CLAUDE.md` ATUAL** — abertura seca, **headers de seção traduzidos em TODA doc PT** (§7), título = classe sem stack, **A04 sem arqueologia**.
- **PONTO PEDAGÓGICO OBRIGATÓRIO (o brief):** o WALKTHROUGH **DEVE** (1) fazer o aluno **VER o saldo final ERRADO/negativo** depois da rajada concorrente (a prova é o **número**); (2) mostrar o **CONFIG/SCRIPT do Turbo Intruder** (single-packet/gate) — é a ferramenta central e o aluno precisa saber usá-la; (3) **declarar transparentemente o papel do sleep** (alarga uma fresta que já existe; o fix o torna irrelevante); (4) **definir TOCTOU/race/fresta/atomicidade/lock/transação/UPDATE-condicional/single-packet DO ZERO**; (5) **cravar o beat "input 100% legítimo, só a concorrência separa"**. **Sem esses cinco, o átomo não ensina a lição nem fica claro pro iniciante.**
- **O coração técnico (cravar): NÃO-ATOMICIDADE, não "faltou check".** O `vulnerable` **TEM** o guard (`balance >= amount`); a falha é ele **não ser atômico** com a escrita. **NÃO** modelar o vulnerable sem guard (seria "faltou validação", vuln diferente). O fix é a **atomicidade** (UPDATE condicional + `rowcount`), **NÃO** "checar de novo" (mesma fresta) nem **só** um lock de app (parcial).
- **O ponto técnico frágil é a COMBINAÇÃO reprodutível (Item 1 / riscos #3/#4/#10) — comportamento de Postgres+Flask+Turbo Intruder.** Fazer a corrida de verdade e confirmar que reproduz **de forma confiável** (vários saques passam no vulnerable; só um no fixed). **Se não reproduzir com o candidato, ajustar dentro do escopo travado (read-check-write no vulnerable; UPDATE condicional no fixed) — o isolamento, as threads/workers, o sleep, o N, a técnica do Turbo Intruder — e PROVAR rodando; se NADA reproduzir, PARAR e avisar — NÃO inventar** o resultado da corrida.
- **Uma vuln só:** a **única** falha é a **não-atomicidade do check-then-act**. **O guard existe** (não modelar falha de auth, injection, leitura de arquivo, ou 2ª superfície); o `fixed` muda **SÓ** a atomicidade (read-check-write → UPDATE condicional). O `reset`/`GET /` são palco/conveniência, não a vuln. **SEM 2ª superfície.**
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é a **atomicidade**, **NÃO** "checar de novo" (armadilha #2 — mesma fresta), **NÃO** só um lock de aplicação (nota #3 — parcial: funciona num processo, não escala pra múltiplos workers/servidores). **Ser honesto** (notas #2/#3/#4 e a nota SERIALIZABLE): nomear o valor/limite de cada intuição. O lock de app **não** é armadilha pura (é exclusão mútua real num processo); `SERIALIZABLE` **também** resolve (contexto legítimo), mas o UPDATE condicional é o fix mínimo. Espírito das notas do salt/CBC/PIN dos átomos recentes.
- **Impacto honesto:** **violação de invariante de negócio** (saldo negativo / débito além do saldo / limite excedido); **NÃO** inflar pra RCE/roubo de credencial/takeover. O teto é o estado inconsistente que a corrida produz. "Race condition tem outras faces" só como **descrição da CLASSE** (uma linha), **sem** nomear átomo/variante/técnica futura.
- **`requirements.txt`** — Flask (pin candidato `Flask==3.0.0`) + psycopg2-binary (pin candidato `psycopg2-binary==2.9.9`), **idênticos** entre os lados (o delta é a query, não uma dependência); confirmar por probe que instalam em `python:3.11-slim`. Postgres pin candidato `postgres:16`. Sem ORM, sem dependência pesada.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** os quatro/cinco — **(a)** não é input malicioso/injection (a request é 100% legítima, byte-idêntica; só a concorrência separa — **o contraste central com TODOS os anteriores**); **(b)** não é "faltou validação" (o guard existe, só não é atômico); **(c)** não é "faltou um guard/limite" (o guard está lá; a falha é temporal); **(d)** não é bug pontual (é design — A04); **(e)** não se conserta "checando de novo" (mesma fresta).
- **Contraste com átomos publicados (cravar o "input benigno"):** citar publicados (01–34) como contraste — o eixo é "diferente de X, aqui o input é benigno" (payload/número/campo/cabeçalho → **nada**, só a concorrência). Contraste especialmente útil: `idor-numeric-id` (03 — lá o exploit já era dado legítimo, mas **mudava** a request; aqui **nem isso**). **PROIBIDO** foreshadowar átomo não-publicado/futuro (inclusive "único A04"/"primeiro de concorrência"/outros A04). **Manter as proibições genéricas.** **Esta spec é pública — nasce limpa de foreshadow.**
- **Definir conceito na 1ª ocorrência (`CLAUDE.md` §5 + o brief):** race condition, seção crítica, TOCTOU, a fresta, atomicidade, exclusão mútua/lock, transação, UPDATE condicional, single-packet attack. **DO ZERO** — o átomo é denso de **conceito**; não assumir familiaridade.
- **A04 sem arqueologia:** situar em **A04 — Insecure Design**, explicar **por que** (o furo é de **desenho** — a sequência check-then-act não-atômica é o padrão-problema, não um typo nem uma validação esquecida), **sem** contar edições OWASP antigas. Como 33/34.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 candidato `race-condition-basic — Time-of-check to time-of-use (TOCTOU) race condition`. Slug qualifica; "Flask"/"Postgres"/"Python" no corpo, não no H1. Grafia final na Fase 2 (casar, se possível, com o título do primer).
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT.** **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (race condition, TOCTOU, atomicity, lock, transaction, single-packet attack, payload, sink, source) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger Race conditions (`/web-security/race-conditions`, "Race conditions"), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar. Provável **sem** fallback OWASP.
- **A trilha é Burp + Turbo Intruder (desvio de ferramenta declarado):** o Repeater/Intruder normal não ganha a corrida (a rede serializa); o Turbo Intruder (BApp Store) via single-packet/gate faz as requisições chegarem juntas. **SEM** browser. Cravar por que curl/Repeater não bastam (não há concorrência simultânea confiável).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, no padrão das linhas anteriores (candidato — ajustar na Fase 2): `` Added atom 35: `race-condition-basic` — Time-of-check to time-of-use (TOCTOU) race condition: an account API whose POST /withdraw reads the balance, checks `balance >= amount` in Python, then writes the debit as three separate steps, so N identical legitimate withdrawals fired simultaneously all pass the check before any of them writes and all debit (the balance goes negative -- a business-invariant violation); no malicious input, the request is byte-identical to a normal withdrawal and only the concurrency differs; the fix makes the check-then-act atomic with a single conditional UPDATE the database serializes per row (UPDATE ... SET balance = balance - :amount WHERE id = :id AND balance >= :amount, checking rowcount) -- not "check again" (same window) and not just an application lock (works in one process, doesn't scale); multi-container (Flask app + shared Postgres), exploited with Burp's Turbo Intruder single-packet attack (A04 Insecure Design, CWE-362 candidate -- confirm). `` **Confirmar o CWE por fetch na Fase 2** (candidato: CWE-362 "Concurrent Execution using Shared Resource with Improper Synchronization ('Race Condition')"; não inventar). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 35 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec. (A pasta de categoria A04 é **criada** na Fase 2, não agora.)
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline (saque único idêntico nos dois lados) → o ataque real (a rajada concorrente no Turbo Intruder → vários saques + saldo negativo no vulnerable) → o que a vuln NÃO é → fixed (só um 200, saldo correto). A prova exige **rodar a corrida de verdade** (Turbo Intruder). Portas host podem não ser alcançáveis do sandbox — se preciso, validar o comportamento via `docker exec`/rede interna, mas a corrida tem que ser **provada rodando**.
- **Commits sem trailer `Co-Authored-By`** (a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8035` (vulnerable), `127.0.0.1:8135` (fixed); Postgres **sem** portas (rede interna). Bind loopback. Multi-container (molde do 22), **com** rede interna/`depends_on`/healthcheck.
- Se houver dúvida sobre a combinação reprodutível (Item 1), o isolamento, as threads/workers, o sleep, o N, a técnica do Turbo Intruder (HTTP/1.1 gate vs HTTP/2 single-packet), a forma do endpoint (Item 2), o reset (Item 3), os status codes (Item 4), o script do Turbo Intruder (Item 5), a URL/H1 do primer, o CWE, os pins, ou se a corrida não reproduzir, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**; e o `CLAUDE.md` deste repo reforça que gravar memória de projeto é decisão do mantenedor). **Candidato, se a Fase 2 provar que a corrida reprodutível foi NÃO-TRIVIAL** (é o cenário do brief pra valer a memória) — útil pra futuros átomos de concorrência/datastore:

- **`reproducing-a-race-with-turbo-intruder-and-postgres`** — *"Pra um átomo de race condition (TOCTOU) reproduzir de forma CONFIÁVEL num lab: (1) datastore PostgreSQL (NÃO SQLite — o SQLite serializa as escritas com lock de arquivo do banco inteiro e MASCARA a corrida); (2) nível de isolamento READ COMMITTED (o default do Postgres) — deixa a fresta clássica no read-check-write separado E faz o UPDATE condicional (`... WHERE saldo >= :v`) ser atômico (o Postgres trava a linha, re-avalia a condição contra o valor corrente, e escreve); (3) Flask `threaded=True` + CONEXÃO POR REQUEST (não compartilhar conexão entre threads; pool ≥ N) — o estado disputado está no banco, então threads bastam (o GIL libera na I/O e no sleep); (4) um `time.sleep` mínimo entre o check e o write no vulnerable pra alargar a fresta (muleta didática — a vuln é real sem ele); (5) o TURBO INTRUDER (extensão do BApp Store) via single-packet attack pro disparo simultâneo — o Repeater/Intruder normal NÃO ganha a corrida (a rede serializa). SUB-NÓ: o single-packet attack próprio é HTTP/2; o Flask dev server é HTTP/1.1, então a realização é o gate/last-byte-synchronization do Turbo Intruder. A prova é o NÚMERO (saldo final negativo no vulnerable; só um saque passa no fixed). O fix é a ATOMICIDADE (UPDATE condicional + rowcount), NÃO 'checar de novo' (mesma fresta) nem só um lock de app (parcial — não escala pra múltiplos processos)."* — tipo `reference`.

**Ressalva:** boa parte desse fato vai ficar **registrada no spec commitado e no DIFF/WALKTHROUGH** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall pra futuros átomos de concorrência/datastore **E** a Fase 2 confirme que a combinação reprodutível foi não-trivial (precisou de ajuste real). Sua decisão.
