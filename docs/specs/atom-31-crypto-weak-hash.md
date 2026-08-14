# Spec — Átomo 31: `crypto-weak-hash`

> Documento de especificação para o Claude Code implementar o átomo `crypto-weak-hash` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A02 (Cryptographic Failures)**: a pasta `atoms/A02-cryptographic-failures/` já contém `jwt-none-alg`, `jwt-weak-secret` e `jwt-key-confusion`. O 31 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo**.
>
> **É SINGLE-CONTAINER** — dois serviços (`vulnerable` + `fixed`), sem datastore externo. SQLite é um **arquivo embutido no processo** (não um servidor à parte): cada lado é **um container Flask com seu próprio `lab.db` efêmero**, semeado no boot por `init_db()`. O `docker-compose.yml` tem **dois serviços**, molde do `sqli-union-basic` (01) — **sem** serviço de datastore, **sem** healthcheck/`depends_on`, **sem** rede nomeada.
>
> **A lição em uma linha:** guardar senha com um hash de **PROPÓSITO GERAL e RÁPIDO** (MD5/SHA-1), **sem salt**, é usar o **primitivo errado**. Hash é mão-única — não se "descriptografa" — mas um hash rápido e sem salt é **trivialmente recuperável** quando vaza: por **rainbow table** (tabela pré-computada de hash→senha) ou por dicionário. O fix **não** é "um hash mais forte" nem "só um salt" — é trocar o **PRIMITIVO** por um hash feito pra senha (bcrypt/argon2), deliberadamente **LENTO** e com **salt embutido**.
>
> **O eixo pedagógico NOVO deste átomo (a razão de ele existir ao lado do `jwt-weak-secret` 13):** o 13 já ensinou "quebrar um artefato criptográfico offline", mas por **DICIONÁRIO/brute-force** (o cracker computa o hash de cada chute AO VIVO) e sobre um **segredo de assinatura** (pra **forjar** tokens próprios). O 31 quebra um **HASH DE SENHA** (pra **recuperar a credencial real** da vítima) por **RAINBOW TABLE** — um **time-memory tradeoff**: a tabela é **pré-computada** de uma vez, e a busca troca tempo por memória. **Artefato diferente, consequência diferente, TÉCNICA diferente.** Ver "Contraste com o 13".
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha primária Burp; **AQUI o exploit tem um passo OFFLINE** (a quebra do hash com RainbowCrack), então a trilha é **BURP-ADJACENT** — justificada na Nota de planning 3; §3.4 — SQLite embutido, sem datastore externo; §4 — pasta/categoria A02 já existe; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A02 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`**, dados fake, SQLite efêmero, payload/crack benigno; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referências vivas** — o **`jwt-weak-secret` (13) INTEIRO** (a **REFERÊNCIA CENTRAL DE CONTRASTE**: mesma A02, mesmo crack offline de um artefato, mas o 13 quebra um **segredo de assinatura** por **dicionário** pra **forjar**; o 31 quebra um **hash de senha** por **rainbow table** pra **recuperar** — o contraste É a lição), o **`jwt-none-alg` (05)** (A02, tema "parece crypto mas não é crypto"; citável) e o **`sqli-union-basic` (01) INTEIRO** (molde canônico de código Flask + SQLite single-container + estrutura de doc).
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `app.py`, seed — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A02 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver a política de foreshadow). Justificativa do ROADMAP para este átomo: *"MD5/SHA1 em password storage, brute force com rainbow table/hashcat."*
>
> **A categoria A02 JÁ EXISTE — o 31 reaproveita a pasta.** `atoms/A02-cryptographic-failures/` já existe e já hospeda os três JWT (`jwt-none-alg` 05, `jwt-weak-secret` 13, `jwt-key-confusion` 14). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A02-cryptographic-failures/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A02-cryptographic-failures/crypto-weak-hash/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A02 — Cryptographic Failures"**.
>
> **Rótulo A02 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Armazenar senha com um hash fraco/rápido/sem salt é **A02 — Cryptographic Failures** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria dos irmãos JWT. **NÃO** relatar em que número/categoria essa classe caía em edições antigas do OWASP Top 10 — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A02 — Cryptographic Failures.** Explicar **por que** é A02 (o primitivo criptográfico escolhido pra proteger o segredo armazenado é inadequado — hash rápido de propósito geral onde se precisava de um KDF lento e salgado) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW REDOBRADO

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4, §12). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW REDOBRADO (o ponto mais sensível desta spec).** A spec é **pública/commitada** → **nasce limpa**. **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec**: situar o átomo por **ordinal de fase**, **milestone**, **release/versão** (`v0.x`/`v1.0` etc.), ou como **abertura/encerramento** de qualquer coisa. **ATENÇÃO: este átomo NÃO fecha fase**, mas a **MESMA disciplina** vale — **nada** de "abre a fase" / "primeiro átomo da fase" / "penúltimo/último" / ordinal. Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não-publicados**. **A posição vive SÓ no `ROADMAP.md`.** Confirmo aqui apenas o **número (31)**, o **slug (`crypto-weak-hash`)** e a **categoria (A02)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo. **Pode citar `01`, `05`, `13`** (publicados) à vontade (`CLAUDE.md` §5).

## Nota de planning 3 — convenções ATUAIS: API-only JSON (justificado), Burp-ADJACENT, abertura seca

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **API-only JSON — DECISÃO DE FORMA (justificada; confirmável na Fase 2).** Este é um **átomo de credencial/autenticação**: a prova é uma **resposta HTTP** (o login com a senha recuperada passando), **sem execução client-side**. O `CLAUDE.md` §3.3 lista fluxos de auth como família **naturalmente API-only** — o mesmo enquadramento do `jwt-weak-secret` (13, também A02 e credencial-cêntrico) e do `sqli-second-order` (29, cadeia de auth). Justificativa concreta:
>   1. A **prova** é uma **resposta HTTP** (`POST /login` com a senha crackeada → `200`), **não** uma página renderizada — HTML só "contextualizaria".
>   2. Mantém o átomo **mínimo**: sem template Jinja, sem ruído de render — o que importa é a **request de login no Repeater** + a **quebra offline**.
>   3. Bônus didático: em corpo **JSON** a senha recuperada viaja **literal** (`{"username":"admin","password":"adm1n"}`), sem encoding-gymnastics.
>   4. Consistente com a convenção recente para átomos de credencial/auth (13/29 são API-only JSON).
>   - **Alternativa (flip localizado, se o mantenedor preferir):** um HTML mínimo com form de login — trocar `jsonify` por `render_template` + um `index.html` de ~20 linhas. **Registrar como confirmável, não bloqueante.**
> - **Trilha BURP-ADJACENT — Burp prova, o terminal quebra (`CLAUDE.md` §3.3, a exceção da ferramenta-que-o-Burp-não-faz).** O `CLAUDE.md` §3.3 põe o Burp como primário, com a exceção explícita de quando a *prova* exige algo que o Burp não faz (o exemplo é o browser executando JS em XSS). **Aqui a prova exige QUEBRAR um hash por rainbow table** — coisa que o Burp não faz. Então a trilha **principal** divide as ferramentas, **exatamente como o 13** (onde o john quebrava o secret fora do Burp):
>   - **Terminal do aluno (RainbowCrack):** o passo central e novo — `rtgen` **gera** a rainbow table, `rtsort` ordena, `rcrack` **procura** o hash e recupera a senha. **Fora do Burp, fora do container** (crack offline).
>   - **Burp (Repeater):** **PROVA** que a senha recuperada loga — `POST /login` com a credencial crackeada → `200` (conta tomada). É a parte "profissão" (controle cru da request).
>   - Isso **NÃO** é "trilha secundária" (que, sendo API-only, **não existe** — `CLAUDE.md` §3.3). É a trilha **principal**, que legitimamente usa uma ferramenta externa porque a vuln exige. **SEM trilha browser** (não há execução client-side).
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (um login que verifica a senha contra um hash armazenado) e a falha (o hash é MD5 sem salt). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** hash, **função mão-única** (one-way), **salt**, **rainbow table**, **time-memory tradeoff**, **ataque de dicionário**, **KDF (key derivation function) / hash de senha**, **bcrypt**, **cost/work factor** — dar a expansão/definição na estreia. O átomo assume que o aluno **pode não ter feito o 13**: define o vocabulário do zero (pode apontar pro 13 pra ver a variante de dicionário, mas se explica sozinho).
> - **Título = classe sem stack (`CLAUDE.md` §5).** O H1 nomeia a **classe** ("Insecure password storage (weak hashing)"), **NÃO** o motor ("...em MD5"/"...em Python"/"...com bcrypt"). O **slug** (`crypto-weak-hash`) já qualifica a variante; nenhum "MD5"/"Python"/"bcrypt" no H1. O motor aparece no **corpo**.
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Gerar a rainbow table`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A02 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — single-container, SQLite embutido, e requirements.txt que DIFEREM entre os lados

> **SQLite embutido, molde do `sqli-union-basic` (01).** Cada lado é **um** container Flask com **seu próprio** `lab.db` — **NÃO** há datastore compartilhado. O schema + seed vivem em `init_db()` dentro do `app.py` (via `conn.executescript(...)`, molde do 01), guardado por `if os.path.exists(DB_PATH): return`. O `docker-compose.yml` é **dois serviços** (molde do 01) — **sem** healthcheck, **sem** `depends_on`, **sem** rede nomeada, **sem** imagem de seed.
>
> **NOVIDADE ESTRUTURAL a cravar: os `requirements.txt` dos dois lados DIFEREM.** Confirmado por varredura do repo (na data desta spec): **nenhum** átomo publicado tem `vulnerable/requirements.txt` diferente de `fixed/requirements.txt` — as duas metades sempre compartilharam o manifesto de dependências. **Este átomo é o primeiro a quebrar isso:** o `vulnerable/` usa **só stdlib** pra hashear (`hashlib`), e o `fixed/` **adiciona `bcrypt`**. Consequências pra a Fase 2:
> - `vulnerable/requirements.txt` = `Flask==<pin>` (o `hashlib`/`sqlite3` são stdlib, não vão no requirements).
> - `fixed/requirements.txt` = `Flask==<pin>` **+ `bcrypt==<pin>`**.
> - O **DIFF.md** deve **mencionar** esse delta de dependência (o fix **traz uma lib** que o vulnerable não precisava) — mas o **coração do diff** continua sendo a troca do primitivo no `app.py` (hash/verify), **não** a linha do requirements. Não transformar o átomo num átomo de "gerenciamento de dependência"; a lição é o **primitivo**.
> - **§8:** dados fake, bind **só** `127.0.0.1`, sem PII, senha dummy óbvia; o crack roda **offline, local, numa pasta de trabalho FORA do repo** (ver "Nota operacional RainbowCrack").

---

## Identidade

- **ID:** `crypto-weak-hash`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A02 — Cryptographic Failures**. Pasta `atoms/A02-cryptographic-failures/` (**JÁ EXISTE — o 31 reaproveita**). Confirmado contra o `ROADMAP.md` ("A02 Cryptographic Failures") e o `CLAUDE.md` §4. Em prosa, usar o nome da classe — **"Insecure password storage (weak hashing)"** — e a categoria — **"A02 — Cryptographic Failures"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A02-cryptographic-failures/crypto-weak-hash/`
- **Número sequencial:** 31
- **Porta `vulnerable`:** `127.0.0.1:8031`
- **Porta `fixed`:** `127.0.0.1:8131`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos.
- **Topologia:** **SINGLE-CONTAINER por lado** — dois serviços (`vulnerable` + `fixed`), cada um com seu `lab.db` efêmero embutido. **Sem** datastore externo. Molde do `sqli-union-basic` (01).
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/encerramento** (§5 foreshadow, redobrado).
- **Branch de trabalho:** `atom/crypto-weak-hash`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** ver seção "Theory primer". **PortSwigger primeiro; provável fallback OWASP (Password Storage Cheat Sheet) — desvio consciente a AVISAR o mantenedor.** **NÃO inventar URL — confirmar por fetch na Fase 2.**
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# crypto-weak-hash — Insecure password storage (weak hashing)`** — `id` + nome canônico da **classe** em inglês. **SEM** "MD5"/"Python"/"bcrypt" no H1. Grafia canônica exata **confirmável na Fase 2** casando com o título da página do primer; **preservar o nome em inglês também no README PT**. *(Alternativas registradas: "Insecure password hashing", "Password storage using a weak hash". A forma final casa com o primer confirmado.)*

---

## Classe de vulnerabilidade

**Insecure password storage (weak hashing) — senha guardada com um hash de propósito geral, rápido e sem salt.** Uma app autentica por login: no cadastro/seed, ela grava a senha do usuário como o **hash** dela; no login, ela **rehasheia** a senha enviada e compara com o armazenado. A **lógica de login está correta** — o que está errado é o **primitivo escolhido pra hashear**: **MD5** (um hash criptográfico de **propósito geral**, projetado pra ser **rápido**), aplicado **sem salt**. Um hash é uma **função mão-única** (one-way): dado o hash, não há como "descriptografar" de volta a senha. Mas *rápido* e *sem salt* significa que, quando o hash vaza (por um dump de banco, por exemplo), o atacante o **recupera** — não invertendo a função (impossível), mas **adivinhando por tentativa**: chuta uma senha, hasheia, compara. Duas formas de fazer isso em escala: **ataque de dicionário** (hashear uma lista de senhas prováveis) ou **rainbow table** (uma tabela **pré-computada** de hash→senha, que cobre um espaço inteiro de senhas). Como MD5 é rápido (bilhões de hashes por segundo) e **sem salt** (a mesma senha sempre dá o mesmo hash → uma tabela pré-computada serve pra qualquer alvo), a recuperação é **trivial**.

### A lição-coração

> **"Guardar senha com um hash de PROPÓSITO GERAL e RÁPIDO (MD5/SHA-1), sem salt, é usar o primitivo ERRADO. Hash é mão-única — não se 'descriptografa' — mas um hash rápido e sem salt é TRIVIALMENTE recuperável quando vaza: por rainbow table (tabela pré-computada de hash→senha) ou por dicionário. O fix não é 'um hash mais forte' nem 'só um salt' — é trocar o PRIMITIVO por um hash feito pra senha (bcrypt/argon2), deliberadamente LENTO e com salt embutido."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH)

Definir cada peça na estreia (o aluno pode não ter feito o 13):

- **Hash é mão-única.** MD5 mapeia uma senha num digest de 128 bits. **Não existe função inversa** — você não "descriptografa" um hash. Então o atacante **não** inverte: ele **ataca por tentativa** — chuta uma senha candidata, hasheia, e compara com o hash-alvo. Se bater, achou a senha.
- **Por que MD5 é o primitivo errado pra senha:** foi projetado pra ser **rápido** (é um hash de propósito geral, pra checksums/integridade). Rápido = o atacante computa **bilhões de candidatos por segundo**. Pra senha, você quer o **oposto**: um hash **deliberadamente lento**.
- **Sem salt = pré-computação serve.** **Salt** é um valor aleatório único, misturado à senha antes de hashear, de modo que a **mesma** senha vira **hashes diferentes** pra salts diferentes. **Sem salt**, `md5("adm1n")` é **sempre** o mesmo digest — então o atacante pode **pré-computar** uma tabela gigante de `senha → hash` **uma vez** e reusá-la contra **qualquer** hash sem salt. Com salt, cada senha teria que ter sua **própria** tabela — inviável.
- **Rainbow table (o coração técnico deste átomo):** um **time-memory tradeoff** (troca tempo por memória). Guardar toda a tabela `senha → hash` custaria memória demais; recomputar tudo a cada crack custaria tempo demais. A rainbow table faz o meio-termo: **pré-computa CORRENTES** (aplica hash → uma função de redução → hash → redução… repetidamente) e guarda **só as pontas** (início e fim) de cada corrente. Pra crackear, regenera correntes a partir do hash-alvo e procura uma ponta que bata; achando, **caminha** a corrente até reencontrar a senha. **O custo pesado (a pré-computação) é pago UMA vez** e amortizado sobre muitos cracks; a busca depois é rápida.

O ponto contraintuitivo a cravar: **você não "quebrou" o MD5 nem inverteu nada** — você **recuperou a senha original** por adivinhação em massa, viabilizada por o hash ser rápido e sem salt.

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas do DIFF)

> **A diferença NÃO é o ALGORITMO específico (MD5 vs outro) nem "adicionar validação" — é CUSTO COMPUTACIONAL + salt.** Trocar MD5 por outro hash **rápido** (SHA-1, SHA-256) **não** resolve: continua rápido → continua adivinhável. Pôr **só** um salt no MD5 mata a **rainbow table** (a pré-computação), mas o MD5 **continua rápido** → um **dicionário/brute** ainda quebra uma senha fraca. O **fix de causa** é trocar o **PRIMITIVO** por um **KDF de senha** (bcrypt/argon2), que é **lento por projeto** (custo configurável) **e** já traz **salt embutido** — os dois juntos.

### Por que A02 (Cryptographic Failures)

O bug **não é** "input virou código" (injection) nem "faltou um check de dono" (broken access control). É **"o primitivo criptográfico escolhido pra proteger o segredo armazenado é inadequado"** — um hash rápido de propósito geral, sem salt, onde se precisava de um KDF lento e salgado. No Web Top 10 2021 isso é **A02 — Cryptographic Failures**, exatamente onde os irmãos JWT (05/13/14) já moram. Situar em **A02 — Cryptographic Failures**, **sem** contar edições antigas.

---

## Contraste com o `jwt-weak-secret` (13) — CENTRAL (é a razão de o átomo existir)

O **13** é a **referência central de contraste** — e justifica o 31 existir. Os dois são **A02 — Cryptographic Failures** e **ambos quebram um artefato criptográfico OFFLINE**. Mas divergem em **três eixos**: **CAUSA / CONSEQUÊNCIA / TÉCNICA**. Cravar no WALKTHROUGH e no DIFF (tabela + prosa).

- **Artefato + consequência.** O 13 quebra um **SEGREDO DE ASSINATURA** (a chave HMAC) pra **FORJAR** tokens próprios — é uma falha de **integridade/autenticidade** (você passa a emitir tokens que o servidor confia; bypass por forja). O 31 quebra um **HASH DE SENHA** pra **RECUPERAR a credencial real** da vítima — é uma falha de **confidencialidade do segredo armazenado** (você recupera a senha e loga como a vítima; roubo/reuso de credencial).
- **TÉCNICA (o eixo pedagógico NOVO).** O 13 usa **DICIONÁRIO/brute-force**: o cracker (john/hashcat) computa o HMAC de **cada chute AO VIVO**, no momento do crack. O 31 usa **RAINBOW TABLE**: a tabela é **PRÉ-COMPUTADA de uma vez** (a parte cara), e a busca depois é um **time-memory tradeoff** (troca tempo por memória). **O aluno VÊ a pré-computação acontecendo** (`rtgen` fazendo trabalho real) — é o que separa o 31 do 13.

### Tabela de contraste (cravar no DIFF e no WALKTHROUGH)

| Eixo | `jwt-weak-secret` (13) | `crypto-weak-hash` (31) |
|---|---|---|
| **Categoria OWASP** | A02 — Cryptographic Failures | A02 — Cryptographic Failures (**a mesma**) |
| **Artefato quebrado offline** | um **segredo de assinatura** (chave HMAC) | um **hash de senha** armazenado |
| **O que o crack te dá** | a **chave** → você **FORJA** tokens próprios | a **senha real** da vítima → você **loga como ela** |
| **Propriedade violada** | integridade/autenticidade (você emite o que o servidor confia) | confidencialidade do segredo armazenado (você o recupera) |
| **Consequência** | bypass de auth por **forja** (ser qualquer um, qualquer role) | **roubo/reuso de credencial** (takeover; outros sistemas se reusada) |
| **TÉCNICA** | **dicionário/brute** — hasheia cada chute **AO VIVO** (john/hashcat) | **rainbow table** — **PRÉ-COMPUTA** correntes, guarda pontas; busca = time-memory tradeoff |
| **Onde o trabalho pesado acontece** | por chute, na hora do crack | **na pré-computação** (uma vez, amortizada), depois busca rápida |
| **O fix** | trocar um **VALOR fraco** (secret) por um de alta entropia | trocar o **PRIMITIVO** (hash rápido sem salt → KDF lento e salgado) |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante):** o 13 e o 31 são **dois ataques a artefatos criptográficos armazenados/emitidos**, mas o aluno que só fez o 13 pode achar que "quebrar hash é sempre john contra wordlist". O 31 mostra a **outra técnica canônica** — a **rainbow table** — e o **outro alvo** — o **hash de senha**, cuja recuperação é **roubo de credencial**, não forja. **"Um átomo = uma vuln"** é a **CAUSA** (aqui: o primitivo de hash inadequado no armazenamento); o **objeto de estudo do 31** é a recuperação de senha por **tabela pré-computada** e o porquê de o **salt** (num KDF lento) derrotar isso **categoricamente**.

### Relação leve com o `jwt-none-alg` (05) — publicado, citável

O 05 martelou *"parece crypto, não é crypto"* (o servidor não fazia crypto nenhuma num branch). O 31 é um **primo conceitual**, com a diferença afiada: aqui a app **faz** crypto (ela hasheia), mas **do jeito errado** — o **primitivo inadequado** pra tarefa. Não é "faltou crypto" (05) nem "a chave era fraca" (13) — é **"o primitivo criptográfico escolhido não serve pra proteger senha"**. Citar o 05/13 como **irmãos publicados** que o aluno pode abrir e comparar — **sem** narrar sequência/posição/"arco" que implique ordem ou completude (foreshadow, Nota 2).

---

## Uma vuln só — a lógica de login está CORRETA; o hash NÃO é exposto por HTTP

Invariante inegociável do átomo (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o **primitivo de hash fraco no armazenamento**. Para garantir isso:

- **A lógica de login está CERTA.** O `POST /login` verifica a senha corretamente: rehasheia o input com o mesmo primitivo e compara com o armazenado. **Não** há SQLi (as queries são parametrizadas), **não** há bypass de lógica. O verify **só** está "errado" no sentido de comparar contra o **primitivo errado** — mas a comparação em si é correta.
- **O hash NÃO é exposto por HTTP — CRÍTICO.** **NENHUM** endpoint devolve o hash armazenado. Um endpoint que vazasse o hash seria uma **2ª vuln** (information disclosure), violando "um átomo = uma vuln". **PROIBIDO.** O artefato de partida do ataque (a linha `admin:<md5>`) vem de um **DUMP DE BANCO** — uma **PREMISSA**, enquadrada **genericamente** ("obtida de um dump, seja lá como"). O WALKTHROUGH **APRESENTA** a linha dumpada como ponto de partida; ele **não** obtém o hash explorando a app.
- **O dump é PREMISSA, não vuln.** Não modelar *como* o dump aconteceu (isso seria outra vuln, ou foreshadow de uma). Enquadrar: *"suponha que você obteve a tabela `users` de um dump de banco — como se dá em vazamentos reais."*
- **Sem injection, sem 2ª superfície.** `GET /` é só o banner JSON. `POST /login` é a única rota com lógica, e é parametrizada. O `fixed` muda **SÓ** o primitivo de hash/verify (e o seed que grava no formato correspondente).

---

## Feature simulada — login com premissa de dump (TRAVADO)

Uma app de **login API-only**:

- **`GET /`** — banner JSON de aviso (molde do 29): `{"warning": "⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.", "hint": "POST /login with {username, password}. Work from Burp Repeater."}`. **Não injetável.**
- **`POST /login`** — corpo JSON `{"username": "...", "password": "..."}`. O servidor busca o usuário (query parametrizada), **rehasheia** a senha enviada com o primitivo do lado, compara com o hash armazenado, e responde **`200` + sessão** (candidato: `{"authenticated": true}` + `Set-Cookie` de sessão do Flask) ou **`401`** (`{"authenticated": false}`).

Usuários semeados num **SQLite efêmero** (`init_db()` no boot). O **admin** tem senha **FRACA** semeada = **`adm1n`**, **IGUAL nos dois lados** — **só o ARMAZENAMENTO difere** (o `vulnerable/` grava o **MD5** de `adm1n`; o `fixed/` grava o **bcrypt** de `adm1n`). Alguns usuários fake a mais pra a tabela dumpada parecer real (dados fake, sem PII).

- **O artefato de partida do ataque** é a **tabela `users` obtida de um DUMP** (premissa). O WALKTHROUGH apresenta a linha do admin (`admin:<md5-de-adm1n>`) como dado inicial. **CRÍTICO (uma-vuln-só):** o hash **NÃO** é exposto por HTTP — **nada** de endpoint que devolve o hash.
- **HTML: NENHUM** (API-only). Sem `templates/`, sem `render_template`.
- **Senha do admin = `adm1n` (TRAVADA pelo brief).** É uma senha fraca de **5 caracteres**, no charset **loweralpha-numeric** (a–z + 0–9). Escolha proposital: o espaço de senhas é **pequeno o suficiente** pra uma rainbow table cobrir por **keyspace** (não por wordlist) — o que demonstra que a rainbow table brute-força o **espaço inteiro**, pegando até senhas que não são palavra de dicionário limpa. (Contraste com o 13, que usou **wordlist**.)

### Estado/sessão — mínimo, higiene idêntica nos dois lados

O `POST /login` bem-sucedido pode devolver um estado de sessão mínimo (candidato: `session["uid"]` do Flask, molde do 29) **só** pra a resposta `200` ser realista. É **higiene, ortogonal à vuln, idêntica nos dois lados**. **Requisito duro (pra não virar 2ª vuln):** a sessão **não** é a superfície — a prova é o **status `200` do próprio login**, não algo que a sessão destranca. `SECRET_KEY` dummy óbvio (`changeme`, `CLAUDE.md` §8.3), ortogonal, idêntico nos dois lados. **CONFIRME NA FASE 2** se a sessão sequer é necessária — se o `200`/`401` do login já é prova suficiente (provável), a sessão pode ser dispensada, mantendo o átomo ainda mais mínimo. Registrar como confirmável.

---

## O ataque (RainbowCrack) + a prova (TRAVADO; espinha = RainbowCrack)

**Cenário travado; os parâmetros exatos da rainbow table são candidatos confirmados por probe (Fase 2 — ver "Decisão aberta").** Cadeia:

1. **Ponto de partida (premissa):** o atacante tem a tabela `users` de um dump — a linha `admin:<md5-de-adm1n>`. Pega o **hash MD5 do admin**.
2. **Gerar a rainbow table (`rtgen`) — o aluno VÊ a pré-computação:** gerar a tabela pro espaço da senha (candidato: MD5, charset `loweralpha-numeric`, comprimento 5). `rtgen` faz **trabalho real e visível** (contador/barra andando) — **é a pré-computação, o conceito central**.
3. **Ordenar (`rtsort`):** ordena a(s) tabela(s) gerada(s) pra busca eficiente.
4. **Crackear (`rcrack`):** procura o hash MD5 do admin na tabela → **recupera `adm1n`**.
5. **A prova (Burp):** `POST /login {"username":"admin","password":"adm1n"}` no **vulnerable** (8031) → **`200`** — conta do admin tomada.

**FIXED (8131):** no `fixed`, o valor armazenado do admin é um **bcrypt salgado** (`$2b$...`, ~60 chars) — **não** um digest MD5 de 32 hex. Contra isso, uma rainbow table de MD5 é o artefato **categoricamente errado**: nem é o mesmo primitivo (o `rcrack` de uma tabela MD5 nem aceita a string `$2b$...`). E, mais fundo, o **próprio RainbowCrack não consegue mirar bcrypt**: o `rtgen` só oferece hashes **sem salt** (lm/ntlm/md5/sha1/sha256) — **não há bcrypt** —, porque **pré-computação é SEM SENTIDO sob salt-por-hash** (não há tabela hash→senha pra construir). **A prova do fix é, então, por INSPEÇÃO** (o valor armazenado é `$2b$...`, salgado) **+ o fato da ferramenta** (o `rtgen` sequer implementa bcrypt), **NÃO** um `rcrack` que "roda e volta vazio". A técnica de rainbow table não é "mais devagar" contra bcrypt — é **INAPLICÁVEL**: não há tabela pra gerar.

> **Precisão honesta (cravar, não overclamar):** o que a rainbow table derrota **categoricamente** no lado fixed é a **pré-computação** — o **salt** significa que **nenhuma tabela genérica** serve (você precisaria de uma tabela por salt). Além disso, o bcrypt é **lento por projeto**, o que encareceria também um ataque de dicionário/brute direto contra ele. O átomo **não** afirma "bcrypt torna `adm1n` eternamente inquebrável" — afirma que **a técnica de rainbow table não tem o que atacar** (o salt) e que o custo de qualquer adivinhação sobe (a lentidão). Os dois juntos — salt + lentidão — são o que o KDF de propósito entrega.

### Prova de isolamento (o que traça a diferença PURO ao primitivo)

- **Baseline legítimo, IDÊNTICO nos dois lados:** `POST /login` com a senha **correta** (`adm1n` pro admin, ou a senha de outro user semeado) → **`200`** nos **dois** lados. O login funciona igual; a senha certa loga em ambos. **Só o resultado do crack offline difere.**
- **Ataque:** no **vulnerable**, a rainbow table recupera `adm1n` do hash MD5 dumpado → login como admin. No **fixed**, o valor dumpado é um **bcrypt salgado** (`$2b$...`) — a técnica de rainbow table é **INAPLICÁVEL** (o `rtgen` nem oferece bcrypt; sob salt-por-hash não há tabela pra pré-computar) → nenhuma senha a recuperar → sem login. A diferença é **100% o primitivo de armazenamento**, não a senha (que é a mesma) nem a lógica de login (idêntica).

---

## Prova — BENIGNA E OBSERVÁVEL (`CLAUDE.md` §8)

A prova é a **recuperação da senha + o login passando** — não um dump destrutivo, **sem RCE**. Cadeia:

- **Baseline:** login com a senha correta → `200`, **idêntico** nos dois lados.
- **Ataque (vulnerable):** rainbow table recupera `adm1n` do hash MD5 dumpado → `POST /login` com `adm1n` → `200` (takeover).
- **Fixed:** o valor armazenado é um bcrypt salgado (`$2b$...`); a rainbow table é **inaplicável** (o `rtgen` sequer oferece bcrypt — sem tabela pra gerar), então não há recuperação → sem login.

Tudo **offline**, `127.0.0.1`, containers descartáveis; **dados dummy** (senha `adm1n` óbvia, users fake); o **crack roda LOCAL, numa pasta de trabalho FORA do repo** (ver "Nota operacional RainbowCrack"). **NADA destrutivo, NADA sai da máquina.** O WALKTHROUGH deixa **explícito** que é um lab local e o takeover é uma **prova de conceito benigna**. **Não overclamar** (impacto = recuperação de credencial + takeover; **não** RCE).

---

## O código — o coração no hash/verify (candidatos; a Fase 2 gera o real)

O fio condutor: **como a senha é armazenada e verificada**. O `app.py` **DIFERE** entre os lados **no primitivo de hash/verify** (e o seed grava no formato correspondente); todo o resto — `GET /` banner, o parse do corpo, a query parametrizada que busca o user, a sessão, o schema — é **IDÊNTICO na forma** (só o primitivo muda).

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma o `bcrypt` instalando/rodando (`gensalt`/`checkpw`), e captura o crack real do RainbowCrack.**

### `vulnerable/app.py` — MD5 sem salt (candidato)

```python
import os
import hashlib
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "lab.db")


def store_hash(password):
    # VULNERABLE: MD5 is a fast, general-purpose hash, used here with NO salt. It is the
    # WRONG PRIMITIVE for passwords. A hash is one-way (you cannot decrypt it), but a fast,
    # unsalted hash is trivially RECOVERABLE once it leaks: the same password always yields
    # the same digest, so an attacker can pre-compute a hash->password table once (a rainbow
    # table) and reuse it against any unsalted hash. The login logic below is correct -- the
    # flaw is entirely this choice of primitive. Fix: a slow, salted password KDF (see fixed/).
    return hashlib.md5(password.encode()).hexdigest()


def verify(password, stored):
    # Re-hash the submitted password with the same primitive and compare. Correct verification
    # against the WRONG primitive.
    return hashlib.md5(password.encode()).hexdigest() == stored


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login with {\"username\": \"...\", \"password\": \"...\"}. "
                "Work from Burp Repeater.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row and verify(password, row["password_hash"]):
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        """
    )
    # Seed: admin's weak password is stored as an UNSALTED MD5 digest. Dummy data (CLAUDE.md §8).
    seed = [("admin", "adm1n"), ("alice", "alice-lab-pw"), ("bob", "bob-lab-pw")]
    for username, pw in seed:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, store_hash(pw)),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — bcrypt (lento + salt embutido) (candidato)

Só o `store_hash`/`verify` (e o import) mudam; o resto é idêntico:

```python
import os
import sqlite3
import bcrypt
from flask import Flask, request, jsonify

# ... GET / and /login identical to vulnerable, calling store_hash/verify ...

def store_hash(password):
    # FIXED: bcrypt is a purpose-built password KDF -- deliberately SLOW (a tunable cost/work
    # factor) and SALTED (bcrypt.gensalt() embeds a unique random salt in every hash). Because
    # each hash is salted, NO pre-computed rainbow table applies to it -- the attacker would
    # need a separate table per salt, which is infeasible. And the slowness raises the cost of
    # any live guessing (dictionary/brute) too. Salt AND slowness together, from one primitive.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify(password, stored):
    # bcrypt.checkpw re-derives using the salt embedded in `stored` and compares in constant time.
    return bcrypt.checkpw(password.encode(), stored.encode())
```

- **Cada lado grava/lê o formato que usa:** o seed do `vulnerable/` grava o **MD5** de cada senha; o seed do `fixed/` grava o **bcrypt**. A senha semeada é a **mesma** (`adm1n` pro admin) nos dois — **só o formato armazenado difere**.
- **O CONTRASTE (md5 vs bcrypt no `store_hash` E no `verify`) é o diff.** `GET /`, o parse do corpo, a query parametrizada, a sessão (se houver), o schema `users` são **idênticos na forma**.
- **Confirmar na Fase 2:** `bcrypt.hashpw`/`checkpw` com `gensalt()` automático; o `.decode()`/`.encode()` pra guardar o hash bcrypt como `TEXT` no SQLite (bcrypt trabalha em bytes) — validar a forma exata rodando.

---

## O fix e o tipo de diff

**Fix:** **trocar o PRIMITIVO** — MD5 sem salt (`hashlib.md5(...).hexdigest()`) por um KDF de senha lento e salgado (`bcrypt.hashpw(..., bcrypt.gensalt())` / `bcrypt.checkpw(...)`). Tipo de diff: **lógica-diferente no ponto do hash/verify** (e o seed grava no formato correspondente). Diff no `store_hash`/`verify` (+ o import do `bcrypt` + a linha do `requirements.txt`). O resto (`GET /`, `/login` fluxo, a query parametrizada, a sessão, o schema) é **idêntico na forma**.

Diff colável (candidato — a Fase 2 gera o real):

```diff
-import hashlib
+import bcrypt
 ...
 def store_hash(password):
-    # VULNERABLE: MD5 -- fast, general-purpose, NO salt. Wrong primitive for passwords.
-    return hashlib.md5(password.encode()).hexdigest()
+    # FIXED: bcrypt -- slow, purpose-built password KDF with a unique salt embedded per hash.
+    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


 def verify(password, stored):
-    return hashlib.md5(password.encode()).hexdigest() == stored
+    return bcrypt.checkpw(password.encode(), stored.encode())
```

**O CONTRASTE é o diff:** hash rápido de propósito geral sem salt (vulnerable) vs KDF de senha lento e salgado (fixed). **A mudança é o primitivo** — no `store_hash`, no `verify`, no import, e no `requirements.txt` (o fixed **adiciona** `bcrypt`).

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é o PRIMITIVO, não o algoritmo específico.** O bug é usar um hash **rápido de propósito geral** pra senha (MD5) — **não** "MD5 tem colisões". Trocar MD5 por **outro hash rápido não resolve** (ver notas #2/#3). O fix neutraliza porque bcrypt é **lento** e **salgado por projeto**.
2. **"Só põe um salt no MD5" NÃO é o fix — nota-ARMADILHA (SINTOMA vs CAUSA), com HONESTIDADE.** Nomear a intuição: *"o problema era a tabela pré-computada, então é só salgar."* Mostrar que salt **mata a rainbow table/pré-computação** (o **SINTOMA**), **mas** o MD5 **continua RÁPIDO** → um **dicionário/brute** ainda quebra uma senha fraca (a **CAUSA** é a velocidade). **Cravar SINTOMA vs CAUSA.** **HONESTIDADE (a exceção "mais de uma defesa legítima em camadas", `CLAUDE.md`):** o salt **NÃO** é só armadilha — é componente **LEGÍTIMO e necessário** (bcrypt/argon2 já incluem salt por padrão). O ponto é que salt **SOZINHO, colado num hash rápido, é INSUFICIENTE** — o KDF de propósito te dá **salt E lentidão juntos**. Ser honesto sobre isso na nota.
3. **"Usa SHA-256, que não é quebrado igual o MD5" NÃO é o fix — nota-ARMADILHA.** SHA-256 **não** é quebrado por colisão, mas é **IGUALMENTE RÁPIDO** e de propósito geral → **igualmente quebrável** pra senha. A resposta é um hash **LENTO DE PROPÓSITO** (KDF), **não** um hash "mais forte". Cravar: "mais forte" (resistência a colisão) ≠ "adequado pra senha" (lento + salgado).
4. **Impacto.** Recuperação de credencial → **account takeover**, amplificado por **reuso de senha** entre sistemas. **Não** inflar pra RCE.
5. **Delta de dependência (curto).** O `fixed/requirements.txt` **adiciona `bcrypt`** — o único átomo do repo cujos dois lados **não** compartilham o manifesto de dependências. Mencionar que o fix **traz uma lib** (o KDF de propósito), mas que o **coração do diff é o primitivo no `app.py`**, não a linha do requirements.

---

## Biblioteca / stack

- **`vulnerable/`: Flask + stdlib** (`hashlib`, `sqlite3` — stdlib, não vão no requirements). `requirements.txt` = **`Flask==<pin>`** só.
- **`fixed/`: Flask + `bcrypt`** (+ stdlib). `requirements.txt` = **`Flask==<pin>` + `bcrypt==<pin>`**.
- **Os `requirements.txt` DIFEREM entre os lados** (Nota de planning 4) — o `fixed` adiciona `bcrypt`. Novidade estrutural do repo.
- **Confirmar o pin do `bcrypt` rodando na Fase 2.** `bcrypt` distribui **wheel** (com binário nativo) — provavelmente instala no `python:3.11-slim` **sem toolchain de build** (paralelo à memória `rsa-atoms-crypto-wheel`, que confirmou `cryptography` instalando como wheel puro). **Confirmar RODANDO**; se exigir toolchain, documentar (ou pinar uma versão com wheel manylinux). `Flask==3.0.0` casa com os irmãos.
- **SEM** ORM, `requests`, ou 2ª dependência além do `bcrypt` (no fixed). `CLAUDE.md` §3.6.
- **A rainbow table NÃO é copiada pro container** (nem asset commitado) — ela é **gerada pelo aluno/mantenedor no terminal**, offline, numa pasta de trabalho em `/tmp` (ver "Nota operacional RainbowCrack"). Diferente do 13 (que commitou uma `wordlist-sample.txt`): aqui **não** há asset de wordlist — a rainbow table é gerada, não distribuída, e uma tabela de tamanho real é grande demais pra commitar (`CLAUDE.md` §8).

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY JSON** (o vetor é o **corpo JSON** no Repeater; decisão de forma justificada na Nota de planning 3). Garantir que a **ÚNICA** vuln é o **primitivo de hash fraco no armazenamento**:

- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`. Sem HTML ⇒ sem autoescape/XSS acidental.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (molde do 29/13). **O `GET /` não é injetável.**
- **A lógica de login está CORRETA** (verify certo, comparação certa — só contra o primitivo errado); **as queries são parametrizadas** (sem SQLi). **NÃO** empilhar SQLi/injection.
- **O hash NÃO é exposto por HTTP** — nenhum endpoint devolve o hash (senão seria information disclosure, 2ª vuln). O dump é **premissa**.
- **O `fixed` muda SÓ o primitivo de hash/verify** (`store_hash`/`verify` + import + requirements + o formato que o seed grava). `GET /`, o fluxo do `/login`, a query parametrizada, a sessão, o schema são idênticos na forma.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é **trocar o primitivo** (bcrypt), **NÃO** "adicionar validação" nem **só** um salt (as armadilhas das notas #2/#3 do DIFF). A senha (`adm1n`) é a **mesma** nos dois lados — o que muda é **como ela é armazenada**.
- **A sessão (se houver) NÃO pode virar 2ª vuln:** é higiene mínima, idêntica nos dois lados, ortogonal; a prova é o **`200` do login**, não algo que a sessão destranca. `SECRET_KEY` dummy ortogonal.

---

## WALKTHROUGH — abertura seca; Burp-adjacent; headers PT traduzidos

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (um login que verifica a senha contra um hash armazenado) e a falha (o hash é MD5 sem salt). Trilha **Burp-adjacent**: o crack (`rtgen`→`rtsort`→`rcrack`) roda **no terminal, offline**; o **Burp (Repeater) prova** que a senha recuperada loga. **SEM trilha browser.**

**Abertura (candidato — plantar a lição, seco):**

> *A app é um login: você manda usuário e senha, ela rehasheia a senha e compara com o hash que guardou. A lógica está certa. O problema é o primitivo que ela escolheu pra guardar: MD5, sem salt. Hash é mão-única — você não descriptografa um MD5. Mas MD5 é um hash rápido e de propósito geral, e sem salt a mesma senha sempre dá o mesmo digest — então, de posse de um hash vazado num dump, você recupera a senha original por uma tabela pré-computada de hash→senha (uma rainbow table). Com a senha na mão, você loga como a vítima.*

Beats (molde do 13/29 — abertura seca, seções numeradas `## 1..N`; corpo JSON no Repeater + crack no terminal; **sem browser**):

1. **Context.** A feature: `POST /login` verifica a senha contra o hash armazenado. **Definir na estreia:** **hash / função mão-única (one-way)** (não se descriptografa; ataca-se por tentativa), **salt** (valor aleatório único misturado à senha → mesma senha, hashes diferentes), **rainbow table** (tabela **pré-computada** hash→senha, cobrindo um espaço inteiro), **time-memory tradeoff** (guarda pontas de correntes, troca tempo por memória), **ataque de dicionário** (hashear uma lista de senhas prováveis), **KDF / hash de senha** (função **lenta de propósito** pra derivar/verificar senha), **bcrypt**, **cost/work factor** (o parâmetro de lentidão). Isto é **A02 — Cryptographic Failures**. Portas: `vulnerable` `127.0.0.1:8031`, `fixed` `127.0.0.1:8131`. Trilha: **terminal (RainbowCrack quebra) + Burp (prova o login)**; sem browser. **A premissa do dump:** *"suponha que você obteve a tabela `users` de um dump — a linha `admin:<md5>` é seu ponto de partida."* Cravar que o hash **não** veio da app (não há endpoint que o vaze) — é premissa.
2. **Spot the bug.** Mostrar o `vulnerable/app.py`: `store_hash`/`verify` usando `hashlib.md5(...)` **sem salt**. Apontar que o **login está correto** (rehasheia e compara certo) — o bug é o **primitivo**. Pergunta de auditoria: *"MD5, sem salt, pra guardar senha — esse primitivo é adequado?"* → não: rápido + sem salt = recuperável por tabela pré-computada. Foreshadow do fix: **trocar o primitivo por um KDF lento e salgado**.
3. **Exploitation (terminal — o crack por rainbow table; a prova é o login no Burp).**
   - **3a — o hash de partida (premissa):** da tabela dumpada, pegar `admin:<md5-de-adm1n>`.
   - **3b — GERAR a rainbow table (`rtgen`) — o aluno VÊ a pré-computação (OBRIGATÓRIO):** rodar `rtgen` pro espaço da senha (MD5, `loweralpha-numeric`, comprimento 5; parâmetros exatos = probe da Fase 2). **Mostrar o `rtgen` trabalhando** (contador/progresso) — **é a pré-computação, o conceito central e o que separa este átomo do 13**. *(Este passo é central, não detalhe.)*
   - **3c — ordenar (`rtsort`):** ordena a(s) tabela(s).
   - **3d — crackear (`rcrack`):** procurar o hash MD5 do admin → **recupera `adm1n`**. Mostrar o output real (Fase 2).
   - **3e — a prova (Burp):** `POST /login {"username":"admin","password":"adm1n"}` no vulnerable → **`200`** (conta do admin tomada). Bloco colável no Repeater.
   - **§8 (cravar):** lab **isolado** (bind só `127.0.0.1`; container descartável); crack **offline, local, numa pasta de trabalho FORA do repo**; dados **dummy**; **sem** RCE, **nada** destrutivo.
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'".
5. **Impact (honesto — sem overclaim).** Ver "Impacto honesto".
6. **Why the fix works (porta 8131).** Repetir contra o `fixed/`:
   - No fixed, o valor dumpado do admin é um **bcrypt salgado** (`$2b$...`), não um MD5. A prova é **por INSPEÇÃO + fato da ferramenta**, não um comando que volta vazio: (1) uma rainbow table de MD5 é o artefato **categoricamente errado** — o `rcrack` de uma tabela MD5 nem aceita a string `$2b$...`; (2) o **próprio RainbowCrack não mira bcrypt** — o `rtgen` só oferece hashes sem salt (lm/ntlm/md5/sha1/sha256), porque **pré-computação é sem sentido sob salt-por-hash** (não há tabela hash→senha pra construir). **A prova é CATEGÓRICA:** a técnica não é "mais devagar" contra bcrypt — é **INAPLICÁVEL** (não há tabela pra gerar).
   - **Precisão honesta (nota #2):** o salt derrota a **pré-computação** categoricamente; a **lentidão** do bcrypt encareceria também um dicionário/brute direto. Salt **E** lentidão juntos — não "só um salt".
   - **Prova de isolamento:** login legítimo (senha correta) → `200` **idêntico** nos dois lados; **só** o resultado do crack offline separa vulnerable (recupera `adm1n`) de fixed (não recupera). A diferença é **100% o primitivo de armazenamento**.
   - **A lição do diff:** o fix **troca o primitivo** (bcrypt). **NÃO** é "hash mais forte" (nota #3) nem "só um salt" (nota #2) nem "adicionar validação". (Forward pro DIFF.)

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Requests/responses/outputs são **placeholders** da execução real capturada na Fase 2 (o MD5 real de `adm1n`, o output real do `rcrack`, os parâmetros da tabela travados por probe).

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5)

Isola a causa e desmonta os mal-entendidos vizinhos (os quatro):

- **(a) NÃO é que a senha `adm1n` era fraca.** A senha fraca **ajuda** (keyspace pequeno), mas a falha que o átomo isola é o **ARMAZENAMENTO**. **Prova de isolamento categórica:** a **mesma** senha `adm1n`, no lado **fixed**, é armazenada como um **bcrypt salgado** (`$2b$...`), contra o qual a rainbow table é **INAPLICÁVEL** (o `rtgen` nem oferece bcrypt; sob salt-por-hash não há tabela pra pré-computar). Logo a diferença é **100% o primitivo**, não a senha.
- **(b) NÃO é que você "descriptografou" / "inverteu" o hash.** MD5 é mão-única, sem inversa. Você **recuperou a senha original** por **pré-computação + busca** (um keyspace search), **não** por decriptação. (Armadilha do iniciante.)
- **(c) NÃO é que "MD5 tem colisões".** A fraqueza de colisão do MD5 é **irrelevante** aqui — você **não** achou uma colisão, achou a **senha original**. **SHA-256** (sem colisão conhecida), armazenado sem salt, cairia **igual**, porque é **igualmente rápido**. A causa é o primitivo ser **rápido + sem salt**, não a brokenness específica do MD5.
- **(d) NÃO é information disclosure nem injection.** O hash **não** foi vazado por um bug da app (nenhum endpoint o devolve) e **nenhum** input virou código. O dump é o **ponto de partida assumido** (premissa); a **única** falha é o **primitivo de armazenamento**.

---

## Impacto honesto

**Recuperação de credencial → account takeover, amplificado por reuso de senha.** O atacante, de posse do hash dumpado, **recupera a senha real** da vítima (aqui, o admin) por rainbow table e **loga como ela** — acesso à conta comprometida. Se a vítima **reusa** a senha em outros sistemas (comum), o impacto **transborda** pra esses sistemas. **Sem overclaim:** o finding é **recuperação de credencial + takeover** — **NÃO** inflar pra RCE (não há execução de código), **NÃO** afirmar comprometimento de sistema além do que a credencial dá. O teto é **o que a credencial recuperada permite**. A classe "weak hashing" tem **outras faces** (SHA-1 sem salt, hashes rápidos com salt mas ainda rápidos, iteração insuficiente) — **descrição de UMA linha da classe**, **sem** modelar nem nomear átomo/variante futura (foreshadow, Nota 2). A **prova do lab é benigna** (a senha dummy `adm1n`, o login passando). Sem foreshadow.

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A02 — átomo dentro de família publicada; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`jwt-weak-secret` (13)** — o contraste **central** (seção dedicada + tabela). Mesma A02, mesmo crack offline de um artefato; o que **difere** é CAUSA (segredo de assinatura vs hash de senha), CONSEQUÊNCIA (forja vs recuperação de credencial) e **TÉCNICA** (dicionário ao vivo vs rainbow table pré-computada). Referência pra **trás**, permitida.
- **`jwt-none-alg` (05)** — irmão A02, tema "parece crypto, não é crypto". Citável de leve pelo eixo "o mecanismo parece proteger, mas o primitivo/uso está errado". Referência pra **trás**, permitida.
- **`sqli-union-basic` (01)** — molde canônico de código/doc (single-container Flask + SQLite). Citável.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5; e esta spec é pública):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer** átomo/categoria/variante futura por número, nome, slug **OU** descrição — inclusive outros A02 futuros, "próxima fase", "outras faces do weak hashing" modeladas como átomo futuro, ou a posição/ordinal/release de fase.
- **PROIBIDO anunciar posição de fase (abrir/fechar/ordinal/"primeiro de"/"penúltimo"), versão/release, ou a sequência de átomos ao redor.** O átomo — **e esta spec** — se descreve **isolado**. **ATENÇÃO: este átomo NÃO fecha fase, mas a MESMA disciplina vale.** Nas frases que proíbem foreshadow, manter a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).
- Que "weak hashing tenha outras faces" é, no máximo, **descrição conceitual de UMA LINHA** — **sem** nomear átomo/variante futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy / OWASP.

**LIMITE DE ESCOPO:** o 31 vai até **recuperar a senha do admin por rainbow table (a partir de um hash dumpado) → login como admin** (o finding), provado pela resposta `200` do login. **Uma vuln, uma causa (o primitivo de hash fraco/rápido/sem salt no armazenamento), um fix (trocar o primitivo por um KDF lento e salgado — bcrypt).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar.**

- **PortSwigger PRIMEIRO — mas PROVÁVEL fallback OWASP (AVISAR o mantenedor).** A PortSwigger Academy foca em vulns **web** (SQLi, XSS, SSRF, JWT attacks, auth) e **provavelmente NÃO tem uma página conceitual dedicada a "weak password hashing" / "password storage"**. **A Fase 2 DEVE buscar por fetch** — candidatos a testar: uma seção sobre armazenamento/hashing de senha dentro do tópico de **authentication** (ex.: algo em `https://portswigger.net/web-security/authentication`), ou de **access control**/**information disclosure**. **Se houver** uma página conceitual limpa da vuln, usá-la.
- **FALLBACK justificado (provável): OWASP Password Storage Cheat Sheet.** Se a PortSwigger não tiver página conceitual limpa pra armazenamento/hashing de senha, usar a **OWASP Password Storage Cheat Sheet** (candidato de URL a confirmar por fetch: `https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html`). **É um desvio consciente da convenção "PortSwigger" do §5** — a fonte OWASP é a autoridade canônica de password storage, cobre exatamente a lição (KDFs lentos, salt, bcrypt/argon2) e o `CLAUDE.md` §14 já credita OWASP. **AVISAR o mantenedor explicitamente** de que este átomo diverge da fonte-padrão do primer, e por quê.
- **Texto do link:** preservar o nome da página em **inglês** também no README PT (`CLAUDE.md` §7).
- **NÃO inventar URL nem grafia** — confirmar por fetch na Fase 2; se não conseguir verificar, **perguntar ao mantenedor** (`CLAUDE.md` §5).

---

## A ferramenta (RainbowCrack) — usar e linkar, NÃO ensinar; e a trilha

O átomo ensina a **VULNERABILIDADE** (primitivo de hash fraco), **NÃO** a ferramenta. Disciplina (molde da seção "john" do 13):

- **Mostrar o passo a passo do ataque:** os comandos `rtgen`/`rtsort`/`rcrack`, o **output real** (Fase 2), a senha recuperada, o login provado. Mas **NÃO** virar tutorial de RainbowCrack: nada de "como instalar", nada de explicar cada flag exaustivamente, nada de teoria de correntes além do necessário pra a lição.
- **Linkar a fonte do RainbowCrack** (`https://project-rainbowcrack.com/`) pra quem quiser aprofundar. **Confirmar a URL exata por fetch na Fase 2.**
- **A trilha é Burp-adjacent** (Nota de planning 3): **terminal (RainbowCrack quebra) + Burp (prova o login)**, **sem** browser. Espelha a exceção do `CLAUDE.md` §3.3 (a ferramenta que o Burp não faz, como o browser no XSS ou o john no 13).

### Nota operacional RainbowCrack (para a Fase 2 — validação; NÃO é o que o aluno vê)

**Contexto do ambiente do mantenedor (confirmado por `ls`/`command -v` na data desta spec):** o **RainbowCrack 1.8 está INSTALADO** — `rtgen`/`rtsort`/`rcrack` no PATH via `/usr/local/bin`; `alglib0.so` e `charset.txt` em `~/tools/rainbowcrack-1.8-linux64/`; `charset.txt` contém `loweralpha-numeric = [abcdefghijklmnopqrstuvwxyz0123456789]` (cobre `adm1n`, comprimento 5).

**ARMADILHA cravada em teste anterior do mantenedor:** o `rtgen`/`rcrack` **carregam o algoritmo do plugin `alglib0.so` e o procuram no DIRETÓRIO ATUAL (cwd)** — o `ld.so.conf` faz o **binário iniciar**, mas a **descoberta do algoritmo é um scan do cwd**. Então **TODO o trabalho de rainbow table (geração + crack) roda numa pasta TEMPORÁRIA em `/tmp`** — ex.: `mkdir -p /tmp/rc-atom31` (ou `mktemp -d`) — com **CÓPIAS de `charset.txt` E `alglib0.so`** copiadas pra dentro **ANTES** de rodar `rtgen`; as tabelas nascem lá. **NUNCA no repo, NUNCA na home, NUNCA em `~/Downloads` — SEMPRE `/tmp`** (limpa sozinho no reboot, sem faxina manual). **Fonte dos arquivos:** `~/tools/rainbowcrack-1.8-linux64/{charset.txt,alglib0.so}`. *(Foi o cwd-scan que fez o smoke test `md5`→`"abc"` só reproduzir depois de copiar o `alglib0.so` pra pasta de trabalho.)*

**Fluxo de validação candidato (Fase 2 — confirmar/ajustar rodando):**

```bash
work=$(mktemp -d /tmp/rc-atom31.XXXX)
cp ~/tools/rainbowcrack-1.8-linux64/{charset.txt,alglib0.so} "$work"/
cd "$work"
# rtgen md5 <charset> <len_min> <len_max> <table_index> <chain_len> <chain_num> <part_index>
# parâmetros (chain_len/chain_num/nº de tabelas) = DECISÃO ABERTA (cobertura alta + geração VISÍVEL)
rtgen md5 loweralpha-numeric 5 5 0 <chain_len> <chain_num> 0
rtsort .
rcrack . -h <md5-de-adm1n>     # deve recuperar: adm1n
```

Isto é **nota de Fase 2** (o mantenedor validando); o **WALKTHROUGH do aluno** mostra os comandos limpos + o output real capturado, **não** a ginástica de `cwd`/`alglib0.so` (que é específica deste install manual e não do Kali empacotado).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A02 — Cryptographic Failures** (`atoms/A02-cryptographic-failures/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `crypto-weak-hash` em A02; `CLAUDE.md` §4 fixa a pasta. Situar em A02 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Topologia | **SINGLE-CONTAINER por lado** — 2 serviços (vulnerable + fixed), SQLite embutido, sem datastore | Molde do `01`. SQLite é arquivo embutido; cada lado tem seu `lab.db` efêmero. |
| Banco | **SQLite efêmero, read-only no request** (só `SELECT` no login; `INSERT` só no seed) | Seed no boot via `init_db()`; sem volume; recria/reseta a cada `up` limpo. |
| Lição-coração | **Primitivo errado: hash rápido de propósito geral, sem salt. Fix = KDF lento e salgado (bcrypt), não "hash mais forte" nem "só um salt".** | Hash é mão-única, mas rápido+sem-salt = recuperável por rainbow table/dicionário. |
| Sub-lição crítica | **A diferença é CUSTO COMPUTACIONAL + salt, não o algoritmo específico nem "adicionar validação"** | Trocar MD5 por outro hash rápido não resolve; salt sozinho num hash rápido é insuficiente. |
| Contraste central | **`13` (jwt-weak-secret)** — mesma A02, crack offline; difere CAUSA/CONSEQUÊNCIA/TÉCNICA | Justifica o átomo. 13 = segredo de assinatura, dicionário, forja; 31 = hash de senha, rainbow table, recuperação. |
| Contraste de apoio | **`05` (jwt-none-alg)** — "parece crypto, não é crypto"; **`01`** molde de código/doc | Publicados; ancoram a lição. Sem foreshadow. |
| Eixo pedagógico NOVO | **Rainbow table (pré-computação / time-memory tradeoff)** | O aluno VÊ o `rtgen` gerar a tabela — o que separa do dicionário-ao-vivo do 13. |
| Tipo de átomo | **API-only JSON** (sem HTML, sem templates, sem browser) | Átomo de credencial/auth; prova = resposta HTTP; molde 13/29. **Confirmável (flip pra form é localizado).** |
| Trilha | **BURP-ADJACENT: terminal (RainbowCrack quebra) + Burp (prova o login); SEM browser** | A prova exige quebrar um hash (Burp não faz) — a exceção do §3.3, como o john no 13. |
| Flavor — **TRAVADO** | **Login API-only; admin com senha fraca `adm1n` semeada IGUAL nos dois lados; só o armazenamento difere; hash de partida vem de um dump (premissa)** | A ÚNICA superfície é o primitivo de armazenamento. Hash **não** exposto por HTTP. |
| Senha do admin — **TRAVADA** | **`adm1n`** (5 chars, loweralpha-numeric) | Keyspace pequeno → rainbow table cobre por keyspace (não wordlist). Contraste com o 13 (wordlist). |
| Sessão — **candidato, confirmar** | **Sessão Flask mínima OU nenhuma** (o `200`/`401` do login já prova) | Higiene ortogonal, idêntica nos dois lados; `SECRET_KEY=changeme` dummy. Confirmar se é sequer necessária. |
| Prova — **conceito TRAVADO, params = probe** | **rtgen → rtsort → rcrack recupera `adm1n` → `POST /login` com `adm1n` → `200`** | Params da tabela = DECISÃO ABERTA (Fase 2, rodando). Fixed: bcrypt salgado (`$2b$...`) → prova por inspeção + o `rtgen` nem oferece bcrypt (rainbow table INAPLICÁVEL), não um rcrack vazio. |
| Código vulnerable | **`hashlib.md5(password.encode()).hexdigest()`** (store e verify), sem salt | O primitivo errado. Login logicamente correto. |
| Código fixed | **`bcrypt.hashpw(pw, bcrypt.gensalt())` / `bcrypt.checkpw(...)`** | KDF lento + salt embutido. Cada lado grava/lê seu formato. |
| `app.py` vulnerable × fixed | **DIFERE** no primitivo (store_hash/verify + import) e no formato que o seed grava | O fix vive no servidor, no ponto do hash/verify. |
| Fix (único eixo) | **Trocar o PRIMITIVO** (MD5 sem salt → bcrypt lento e salgado) | Correção na raiz. NÃO "hash mais forte", NÃO "só salt", NÃO "validação". |
| Diff | **Lógica-diferente** (store_hash/verify) **+ delta de dependência** (fixed adiciona bcrypt) | O coração é o primitivo no `app.py`; o requirements diferente é nota curta (#5). |
| `requirements.txt` | **DIFEREM** — vulnerable = Flask; fixed = Flask + bcrypt | **Novidade estrutural** (1º átomo cujos lados não compartilham o manifesto — verificado por varredura). |
| "Só um salt no MD5" | **Mencionar, NÃO aplicar** (nota #2, com honestidade) | Mata a rainbow table (sintoma), mas MD5 continua rápido (causa). Salt é legítimo, mas insuficiente sozinho. |
| "Usa SHA-256" | **Mencionar, NÃO aplicar** (nota #3) | SHA-256 não é quebrado por colisão, mas é igualmente rápido → igualmente quebrável pra senha. |
| Bibliotecas | **Flask** (vulnerable); **Flask + bcrypt** (fixed) | hashlib/sqlite3 stdlib. bcrypt instala como wheel (confirmar). Sem ORM/dep extra. |
| Rainbow table como asset | **NÃO commitar** — gerada pelo aluno no terminal, offline, em `/tmp` | Tabela real é grande demais pra commitar (`CLAUDE.md` §8). Diferente da wordlist do 13. |
| Banner | **Obrigatório, num `GET /` JSON de aviso** (API-only) | `CLAUDE.md` §8.2. `GET /` não injetável. |
| Impacto | **Recuperação de credencial / account takeover (+ reuso).** Sem RCE. | Honesto; teto = o que a credencial permite. Sem foreshadow. |
| Theory primer | **PortSwigger primeiro; PROVÁVEL fallback OWASP Password Storage Cheat Sheet** | Academy pode não ter página conceitual de password hashing. Desvio consciente — avisar o mantenedor. Confirmar por fetch. |
| Título (H1) | **`crypto-weak-hash — Insecure password storage (weak hashing)`** (classe, sem stack) | `CLAUDE.md` §5. Sem "MD5"/"Python"/"bcrypt" no H1. Grafia final casa com o primer. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública); **NÃO fecha fase, mesma disciplina** | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release/outras faces como átomo futuro. |
| Portas | **8031 / 8131** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container por lado. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si** (molde do `01`/`13`, **mas API-only → SEM `COPY templates`**):

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

- `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py` (idêntico aos irmãos). `init_db()` chamado no boot (seed embutido; `executescript` + `INSERT`s dentro do `app.py`, molde do `01`).
- **O `Dockerfile` é idêntico entre os lados**, mas **cada lado copia seu próprio `requirements.txt`** (que diferem — fixed adiciona bcrypt) e seu próprio `app.py` (que diferem no primitivo). A rainbow table **não** é copiada pro container (crack offline no terminal).

**`docker-compose.yml`** (molde EXATO do `01` — dois serviços, **sem** datastore, **sem** healthcheck/`depends_on`/rede; apps bind **só** `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8031:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8131:5000"
```

- **§8:** ambos publicam porta **só** em `127.0.0.1`. Sem datastore externo, sem rede nomeada. Banco efêmero por container (recria/reseta a cada `up` limpo).
- **Confirmar na Fase 2** que `./atom up crypto-weak-hash` sobe os dois e o login funciona de primeira.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes de design — exceto onde marcado "DECISÃO ABERTA".

1. **Baseline login OK nos dois lados:** `POST /login` com a senha **correta** (`adm1n` pro admin) → **`200`/sessão** no vulnerable **E** no fixed. Senha errada → `401`. **VALIDAR.**
2. **O seed do vulnerable grava o MD5 SEM salt do admin;** a tabela `users` é o artefato de dump. **CONFIRMAR** (via `docker exec` no SQLite) que `password_hash` do admin é `md5("adm1n")` literal (sem salt). Capturar o MD5 real pro walkthrough.
3. **O ATAQUE (central — VALIDAR RODANDO):** `rtgen` gera a rainbow table pro espaço de `adm1n` (MD5, `loweralpha-numeric`, comprimento 5; params = **DECISÃO ABERTA**), `rtsort` ordena, `rcrack` **recupera `adm1n`** de forma **REPRODUTÍVEL**. **Capturar o output real** (com a geração visível). **Se não recuperar reprodutivelmente, PARAR e avisar o mantenedor — NÃO inventar.**
4. **A prova (Burp):** `POST /login {"username":"admin","password":"adm1n"}` → **`200`**/takeover no **vulnerable** (8031). Capturar request/response reais.
5. **FIXED:** o seed grava **bcrypt** (salgado, `$2b$...`) do admin. A rainbow table é **INAPLICÁVEL** aqui — **não** "rode o rcrack e ele volta vazio": (a) o valor armazenado é `$2b$...`, não um MD5 de 32 hex (o rcrack de uma tabela MD5 nem aceita); (b) o `rtgen` sequer implementa bcrypt (só hashes sem salt), porque salt-por-hash torna a pré-computação sem sentido. **CONFIRMAR a prova por INSPEÇÃO** (o valor armazenado é `$2b$...` salgado) **+ o fato da ferramenta** (a lista de algoritmos que o `rtgen` imprime no uso não inclui bcrypt), **não** um comando de crack. A prova é **categórica** (não há tabela pra gerar), não "mais devagar". Capturar (o hash bcrypt real do seed + a lista de algoritmos do `rtgen`).
6. **Prova de isolamento:** login legítimo (senha correta) **IDÊNTICO** nos dois lados (`200`); **só** o resultado do crack offline difere — e isso traça **PURO** ao primitivo de hash. **VALIDAR** que a mesma senha `adm1n` no fixed (bcrypt) não é recuperável pela rainbow table.
7. **Uma vuln só:** **SEM** information disclosure (o hash **não** é exposto por HTTP — nenhum endpoint o devolve), **SEM** injection (queries parametrizadas). O **único** diff funcional é o primitivo de hash/verify (+ o import + o requirements + o formato que o seed grava). **Confirmar por `diff`.**
8. **§8:** bind **só** `127.0.0.1` (8031/8131); **dados dummy** (senha `adm1n` óbvia, users fake, sem PII); **crack offline LOCAL numa pasta de trabalho FORA do repo** (`/tmp` — ver Nota operacional); **nada destrutivo**, nada sai da máquina.
9. **`bcrypt` instala/pina limpo:** confirmar que `bcrypt==<pin>` instala no `python:3.11-slim` (provável wheel sem toolchain — paralelo `rsa-atoms-crypto-wheel`); `gensalt()` automático; `checkpw` verifica; o hash bcrypt guarda/lê como `TEXT` no SQLite (`.decode()`/`.encode()`). **Se exigir toolchain, documentar/ajustar o pin.**
10. **Theory primer confirmado por FETCH:** PortSwigger primeiro (provável ausência de página conceitual de password hashing); **fallback OWASP Password Storage Cheat Sheet** (candidato `https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html`). **Confirmar por fetch; avisar o mantenedor do desvio da fonte-padrão.** Confirmar a URL do RainbowCrack (`https://project-rainbowcrack.com/`) por fetch. **Não inventar.**
11. **DECISÃO ABERTA — parâmetros da rainbow table** (ver seção dedicada abaixo): `chain_len`/`chain_num`/nº de tabelas que dão **cobertura ALTA** E **geração VISÍVEL**. **VOCÊ CONFIRME/PROPONHA NA FASE 2** rodando; se não recuperar reprodutivelmente, **PARAR e avisar**.
12. **Diff isola só o primitivo:** o **ÚNICO** delta funcional entre `vulnerable/app.py` e `fixed/app.py` é o primitivo de hash/verify; `GET /`, o fluxo do `/login`, a query parametrizada, a sessão, o schema são idênticos na forma. **Confirmar por `diff`.**

**Bloqueante remanescente:** nenhum de decisão de vuln. **DECISÕES ABERTAS de Fase 2 (probe, não bloqueiam a spec):** os parâmetros da rainbow table (seção abaixo); a forma exata da prova do lado fixed (mostrar que não há tabela pra atacar); se a sessão é necessária; a URL/grafia do primer por fetch (e o desvio OWASP); o pin do bcrypt. **Protocolo:** registrar candidato, **rodar**, confirmar; se não reproduzir, ajustar dentro do escopo travado; se travar de vez, **PARAR e avisar — NÃO inventar** crack, params, output ou URL.

---

## DECISÃO ABERTA pra Fase 2 — parâmetros da rainbow table (registrar, NÃO travar)

Os parâmetros da rainbow table pro `adm1n` dependem do **TESTE** (não de preferência editorial): `charset`/comprimento/`chain_len`/`chain_num`/nº de tabelas que dão **cobertura ALTA** E **geração VISÍVEL** (barra/contador andando, tabela de tamanho real — o aluno precisa **VER a pré-computação acontecendo**).

- **Candidato travado no piso:** `charset` **`loweralpha-numeric`** (a–z + 0–9, confirmado no `charset.txt`), comprimento **5** (cobre `adm1n`). Keyspace = 36⁵ ≈ **60,5 milhões** — pequeno o suficiente pra `rtgen` gerar uma tabela de cobertura alta em tempo **visível mas razoável**.
- **VOCÊ CONFIRME/PROPONHA NA FASE 2:** `chain_len`, `chain_num` e o **número de tabelas** (`table_index` 0..N) que, juntos, recuperam `adm1n` de forma **reprodutível** com **cobertura alta**. (RainbowCrack docs e defaults ajudam; a cobertura sobe com mais tabelas e chains mais longas, ao custo de tempo de geração/busca.) **Rodar, medir, escolher o que reproduz.**
- **O `rtgen` é DETERMINÍSTICO — isso rebaixa a barra de reprodutibilidade.** Mesmos parâmetros (`charset`, comprimento, `table_index`, `chain_len`, `chain_num`, `part_index`) produzem a tabela **IDÊNTICA byte-a-byte**, logo a **mesma cobertura**. Consequência pro protocolo: a Fase 2 **não** precisa "atingir cobertura estatística alta e torcer pra `adm1n` estar coberto" — precisa achar **UM** conjunto de parâmetros que recupere `adm1n` **UMA vez** (rodando) e **TRAVAR** esse conjunto. Qualquer pessoa regenerando com os parâmetros travados gera a tabela idêntica e o crack **sempre reproduz**. A barra é **"achar params que recuperam `adm1n` e cravar"**, não **"cobertura alta e esperança"**. (Reforça o gate: se nenhum conjunto razoável recuperar `adm1n`, **PARAR e avisar**.)
- **Idem a forma exata da prova do lado fixed:** a prova é **por INSPEÇÃO** (o valor armazenado é um bcrypt salgado `$2b$...`) **+ o fato da ferramenta** (o `rtgen` só oferece hashes sem salt — não há bcrypt —, porque pré-computação é sem sentido sob salt-por-hash). **NÃO** é "rode o rcrack contra o bcrypt e ele volta vazio". A rainbow table é **INAPLICÁVEL** (não há tabela pra gerar), não "mais devagar".
- **Protocolo:** se os params candidatos não recuperarem `adm1n` reprodutivelmente, **ajustar dentro do escopo travado** (charset/len fixos; mexer em chains/tabelas) e **documentar o que reproduziu**; **se NADA reproduzir, PARAR e avisar o mantenedor — NÃO inventar** params nem output.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **par de contraste do `13` no eixo da TÉCNICA e do ARTEFATO** — mesma A02, mesmo "quebrar um artefato criptográfico offline", mas o 31 quebra um **hash de senha** por **rainbow table** (pré-computada) pra **recuperar a credencial real**, onde o 13 quebrava um **segredo de assinatura** por **dicionário** (ao vivo) pra **forjar**. Cada beat deve poder ser lido com o **`13` aberto ao lado**, e a diferença (CAUSA/CONSEQUÊNCIA/TÉCNICA) visível. **Abrir e fechar** na lição-coração: *primitivo errado (hash rápido sem salt); o fix é um KDF lento e salgado, não "hash mais forte" nem "só um salt".*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`13` INTEIRO** (contraste central — reusar a disciplina "usa/linka a ferramenta, não ensina", a trilha Burp+terminal, a estrutura de README/WALKTHROUGH/DIFF; o par 13↔31 é o eixo), **`05`** (irmão A02 "parece crypto, não é crypto"), **`01` INTEIRO** (molde canônico single-container Flask+SQLite + estrutura de doc), esta spec. **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar encenação; **headers de seção traduzidos em TODA doc PT** (§7); título = classe sem stack.
- **PONTO PEDAGÓGICO OBRIGATÓRIO (a razão de o átomo existir separado do 13):** o WALKTHROUGH **DEVE** fazer o aluno **VER a rainbow table sendo GERADA** (`rtgen` fazendo trabalho real — a pré-computação **É** o conceito). **E DEVE** mostrar que contra o bcrypt a técnica **NÃO TEM O QUE ATACAR** (o salt) — a prova categórica de por que o fix funciona. **Sem esses dois, o átomo perde a razão de existir separado do 13.**
- **O ponto técnico frágil é o crack real (risco #3/#11).** Rodar `rtgen`/`rtsort`/`rcrack` de verdade, capturar output real (com geração visível), confirmar que recupera `adm1n` reprodutivelmente. **Nota operacional (Fase 2):** rodar numa pasta `/tmp` com cópias de `charset.txt` **e** `alglib0.so` (o cwd-scan do plugin — ver "Nota operacional RainbowCrack"). **Se não recuperar, PARAR e avisar — NÃO inventar output.**
- **Uma vuln só:** a **única** falha é o primitivo de hash fraco no armazenamento. **A lógica de login está CORRETA** (verify certo, contra o primitivo errado); **queries parametrizadas** (sem SQLi); **o hash NÃO é exposto por HTTP** (sem information disclosure — o dump é premissa); o `fixed` muda **SÓ** o primitivo (+ import + requirements + formato do seed). **SEM 2ª superfície.**
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é **trocar o primitivo** (bcrypt), **NÃO** "adicionar validação" nem **só** um salt (armadilhas #2/#3 do DIFF). A senha (`adm1n`) é a **mesma** nos dois lados — muda **como ela é armazenada**. **Ser honesto** (nota #2): o salt é legítimo e necessário, mas insuficiente **sozinho** num hash rápido; o KDF dá salt **E** lentidão.
- **Impacto honesto:** **recuperação de credencial → account takeover**, amplificado por **reuso de senha**; **não** inflar pra RCE. "Weak hashing tem outras faces" só como **descrição da CLASSE** (uma linha), **sem** nomear átomo/variante futura.
- **`requirements.txt` DIFEREM entre os lados** (novidade estrutural — verificada por varredura): vulnerable = `Flask`; fixed = `Flask` + `bcrypt`. O DIFF menciona o delta (nota #5), mas o coração é o primitivo no `app.py`. **Confirmar o pin do bcrypt rodando.**
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** os quatro — **(a)** não é a senha fraca (prova categórica: `adm1n` + bcrypt no fixed não é recuperável → a diferença é o primitivo); **(b)** não é "descriptografou/inverteu" (hash é mão-única; foi recuperação por pré-computação); **(c)** não é "MD5 tem colisões" (irrelevante; SHA-256 sem salt cairia igual, por ser rápido); **(d)** não é information disclosure nem injection (o dump é premissa; o hash não é exposto).
- **Contraste com o `13` (cravar):** tabela (2 colunas: 13/31) + prosa; mesma A02, crack offline; difere CAUSA/CONSEQUÊNCIA/**TÉCNICA** (dicionário-ao-vivo vs rainbow-table-pré-computada). Citar `13`/`05`/`01` (publicados) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** hash, função mão-única (one-way), salt, rainbow table, time-memory tradeoff, ataque de dicionário, KDF/hash de senha, bcrypt, cost/work factor.
- **A02 sem arqueologia:** situar em **A02 — Cryptographic Failures**, explicar **por que** (primitivo criptográfico inadequado pro segredo armazenado), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `crypto-weak-hash — Insecure password storage (weak hashing)`. "MD5"/"Python"/"bcrypt" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **13** (contraste central), **05** (irmão A02), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase e outras faces do weak hashing como átomo futuro. **Manter as proibições genéricas.** **ATENÇÃO: este átomo NÃO fecha fase — mesma disciplina.** **Esta spec é pública — nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`crypto-weak-hash — Insecure password storage (weak hashing)`, grafia exata confirmável na Fase 2 contra o primer). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (hash, salt, rainbow table, time-memory tradeoff, dictionary attack, KDF, bcrypt, work factor, one-way, payload, takeover) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): PortSwigger primeiro; **provável fallback OWASP Password Storage Cheat Sheet** — **avisar o mantenedor do desvio da fonte-padrão**; nome da página em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **A ferramenta RainbowCrack é USADA, não ensinada:** passo a passo do ataque sim; tutorial de instalação/flags não. Linkar `https://project-rainbowcrack.com/` (confirmar por fetch). O WALKTHROUGH do aluno mostra os comandos limpos + output real; a ginástica de `cwd`/`alglib0.so` é **nota de Fase 2** (validação neste install), não conteúdo do aluno.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 31: `crypto-weak-hash` — Insecure password storage: a login app stores the admin's password as an unsalted MD5 digest, so a hash leaked in a database dump is recovered with a pre-computed rainbow table (rtgen/rtsort/rcrack) and replayed to log in as the victim; the fix swaps the primitive for bcrypt (slow, salted), against which no rainbow table applies (A02 Cryptographic Failures). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 31 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline (login OK nos dois lados) → o crack real (rtgen gera a tabela → rtsort → rcrack recupera `adm1n`) → a prova (`POST /login` com `adm1n` → `200` no vulnerable) → o que a vuln NÃO é → fixed (bcrypt salgado → sem tabela → sem recuperação). Portas host podem não ser alcançáveis do sandbox — ver a memória `validating-atoms-via-docker-exec` (fallback: `docker exec` + dirigir o app/DB de dentro do container; o crack roda no host/terminal, fora do container). **Sem** browser (a prova é a resposta do login).
- **Commits sem trailer `Co-Authored-By`** (memória `commit-no-coauthor-trailer` — a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8031` (vulnerable), `127.0.0.1:8131` (fixed). Bind **só** `127.0.0.1`. Single-container por lado (2 serviços, sem datastore).
- Se houver dúvida sobre os parâmetros da rainbow table, o comportamento do `bcrypt`, se a sessão é necessária, a URL/grafia do primer (e o desvio OWASP), ou se o crack não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**). **Candidato, se você quiser um pointer de recall reusável** — a **nota operacional do RainbowCrack** é a mais provável de servir a futuros átomos que mexam com rainbow tables, e é conhecimento de **ambiente/ferramenta** que **não** vive no repo:

- **`rainbowcrack-cwd-scans-for-alglib`** — *"RainbowCrack 1.8 na fedorex: `rtgen`/`rtsort`/`rcrack` no PATH (`/usr/local/bin`), mas `rtgen`/`rcrack` carregam o algoritmo do plugin `alglib0.so` procurando-o no DIRETÓRIO ATUAL (cwd) — o `ld.so.conf` faz o binário INICIAR, mas a descoberta de algoritmo é um scan do cwd. Rodar TODO o trabalho de rainbow table (geração + crack) numa pasta TEMPORÁRIA em `/tmp` (`mktemp -d /tmp/rc-...`), com CÓPIAS de `charset.txt` E `alglib0.so` (de `~/tools/rainbowcrack-1.8-linux64/`) copiadas pra dentro ANTES de rodar `rtgen`; as tabelas nascem lá. NUNCA no repo/home/Downloads — SEMPRE `/tmp` (auto-limpa no reboot). `charset.txt` tem `loweralpha-numeric = [a-z0-9]`. Fluxo: `rtgen md5 loweralpha-numeric <lmin> <lmax> 0 <chain_len> <chain_num> 0` → `rtsort .` → `rcrack . -h <hash>`. Usado no átomo `crypto-weak-hash` (31)."* — tipo `project`/`reference`.

**Ressalva:** parte desse fato (a existência do átomo, o fluxo geral) vai ficar **registrada nesta spec commitada** (a regra de memória desaconselha duplicar o que o repo grava). O que **justifica** a memória é a parte **não-repo, específica do ambiente**: o **cwd-scan do `alglib0.so`** e o **`/tmp` como pasta de trabalho** — conhecimento de ferramenta reusável. Proponho gravar **só** se você quiser esse pointer de recall pra futuros átomos de rainbow table; senão, ele já está aqui na spec. Sua decisão. *(Ortogonal: a memória relevante na Fase 2 é `validating-atoms-via-docker-exec` — dirigir o app/DB de dentro do container se as portas host não forem alcançáveis; e `rsa-atoms-crypto-wheel` — paralelo pro bcrypt instalar como wheel sem toolchain.)*
