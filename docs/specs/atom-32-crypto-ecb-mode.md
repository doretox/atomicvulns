# Spec — Átomo 32: `crypto-ecb-mode`

> Documento de especificação para o Claude Code implementar o átomo `crypto-ecb-mode` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A02 (Cryptographic Failures)**: a pasta `atoms/A02-cryptographic-failures/` já contém `jwt-none-alg` (05), `jwt-weak-secret` (13), `jwt-key-confusion` (14) e `crypto-weak-hash` (31). O 32 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo**.
>
> **É SINGLE-CONTAINER** — dois serviços (`vulnerable` + `fixed`), sem datastore externo. Este átomo é **stateless** (sem SQLite): o crachá (token) é **auto-contido** — o servidor cifra a identidade+role dentro dele e não guarda estado de sessão em banco, exatamente como os irmãos JWT (o `jwt-key-confusion` traz uma "Stack note — no database"). Cada lado é **um container Flask** sem persistência. O `docker-compose.yml` tem **dois serviços**, molde do `sqli-union-basic` (01) — **sem** serviço de datastore, **sem** healthcheck/`depends_on`, **sem** rede nomeada.
>
> **A lição em uma linha:** uma cifra de bloco (AES) cifra em blocos de tamanho fixo (16 bytes); o **MODO DE OPERAÇÃO** define como encadear os blocos de uma mensagem maior. O **ECB** é o modo ingênuo: cada bloco é cifrado **INDEPENDENTEMENTE**, com a mesma chave — então blocos de plaintext idênticos viram blocos de ciphertext idênticos (o padrão vaza), e como os blocos são independentes, um atacante **RECORTA e RECOMBINA** blocos de ciphertext pra montar um plaintext forjado, **SEM saber a chave**. O fix **não** é "trocar por CBC" — é um modo **AUTENTICADO** (AES-GCM) que detecta qualquer bloco adulterado e rejeita o token.
>
> **O eixo pedagógico deste átomo (a razão de ele existir ao lado do `crypto-weak-hash` 31):** o 31 é sobre **ARMAZENAMENTO** de senha via hash **mão-única** — o atacante **recupera o input** crackeando (pré-computação). O 32 é sobre **CIFRAGEM REVERSÍVEL** onde o **MODO** vaza estrutura e permite **FORJA por rearranjo de blocos** — o atacante **não recupera nada e não quebra a chave**; ele **forja** por manipulação de estrutura. **Artefato diferente, ação diferente, causa diferente.** Ver "Contraste com o 31".
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha BURP-ONLY**: o ataque é **manipulação de bytes do token cifrado no Repeater**, **sem** browser, **sem** ferramenta offline separada — a prova está na **resposta HTTP**; §4 — pasta/categoria A02 já existe; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A02 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`**, chave/dados dummy, nada destrutivo; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referências vivas** — o **`crypto-weak-hash` (31) INTEIRO** (a **REFERÊNCIA CENTRAL DE CONTRASTE** e a voz mais recente: mesma A02, mas 31 = armazenamento por hash mão-única, 32 = cifragem reversível forjada pelo modo), os **`jwt-none-alg` (05)** e **`jwt-key-confusion` (14)** (tema-irmão A02: lá se **forja** um token quebrando/burlando a **ASSINATURA**; aqui se **forja** um token explorando o **MODO de cifra**), e o **`sqli-union-basic` (01) INTEIRO** (molde canônico single-container Flask + estrutura de doc).
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `app.py`, seed — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A02 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver a política de foreshadow). Justificativa do ROADMAP para este átomo: *"ECB penguin, bit-flipping, padding oracle lite."*
>
> **RESSALVA CRÍTICA DE ESCOPO (do brief, cravar):** o parêntese do ROADMAP menciona **"bit-flipping, padding oracle lite"** — mas **esses são ataques de CBC, NÃO de ECB**. Este átomo escopa **SÓ ataques genuínos de ECB** (bloco determinístico → **cut-and-paste** e **padrão vazando**). **NÃO mencionar bit-flipping nem padding oracle no conteúdo do átomo** — não porque sejam segredo, mas porque são de um **modo diferente** (CBC), e nomeá-los aqui seria (a) fora do escopo "uma vuln = um modo" e (b) foreshadow de um eventual átomo de CBC (proibido, Nota 2). Enquadrar sempre **genericamente** ("outros modos têm suas próprias falhas") sem nomear técnica/modo/átomo futuro.
>
> **A categoria A02 JÁ EXISTE — o 32 reaproveita a pasta.** `atoms/A02-cryptographic-failures/` já existe e já hospeda os três JWT (05/13/14) e o `crypto-weak-hash` (31). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A02-cryptographic-failures/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A02-cryptographic-failures/crypto-ecb-mode/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A02 — Cryptographic Failures"**.
>
> **Rótulo A02 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Cifrar um token de autoridade com um modo de operação inseguro (ECB) é **A02 — Cryptographic Failures** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria dos irmãos. **NÃO** relatar em que número/categoria essa classe caía em edições antigas do OWASP Top 10 — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A02 — Cryptographic Failures.** Explicar **por que** é A02 (o modo de operação escolhido pra proteger o segredo em trânsito é inadequado — determinístico bloco-a-bloco e sem autenticação) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW REDOBRADO

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4, §12). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW REDOBRADO (o ponto mais sensível desta spec).** A spec é **pública/commitada** → **nasce limpa**. **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec**: situar o átomo por **ordinal de fase**, **milestone**, **release/versão** (`v0.x`/`v1.0` etc.), ou como **abertura/encerramento** de qualquer coisa. A **MESMA disciplina** vale — **nada** de "abre a fase" / "primeiro/penúltimo/último átomo da fase" / ordinal. Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não-publicados**, **inclusive um eventual átomo de CBC** (o parêntese "bit-flipping/padding oracle" do ROADMAP aponta pra ele — não citá-lo). **A posição vive SÓ no `ROADMAP.md`.** Confirmo aqui apenas o **número (32)**, o **slug (`crypto-ecb-mode`)** e a **categoria (A02)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo. **Pode citar `01`, `05`, `14`, `31`** (publicados) à vontade (`CLAUDE.md` §5).

## Nota de planning 3 — convenções ATUAIS: API-only JSON (justificado), Burp-ONLY, abertura seca

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **API-only JSON — DECISÃO DE FORMA (justificada; confirmável na Fase 2).** Este é um átomo de **token/autorização**: o vetor é a **manipulação de bytes do token cifrado** e a prova é uma **resposta HTTP** (`GET /me` respondendo como admin), **sem execução client-side**. O `CLAUDE.md` §3.3 lista JWT/token e famílias de API como **naturalmente API-only** — o mesmo enquadramento dos irmãos JWT (05/14) e do `crypto-weak-hash` (31). Justificativa concreta:
>   1. A **prova** é uma **resposta HTTP** (`GET /me` → `role: admin` / recurso privilegiado liberado), **não** uma página renderizada — HTML só "contextualizaria".
>   2. Mantém o átomo **mínimo**: sem template Jinja, sem ruído de render — o que importa é o **token no Repeater**.
>   3. Bônus didático: em corpo/headers **JSON** o token viaja **literal**, sem encoding-gymnastics de formulário.
>   4. Consistente com a convenção recente para átomos de token/auth (05/14/31 são API-only).
>   - **SEM alternativa de HTML.** Diferente do 31 (onde registrei um flip localizado pra form), aqui o ataque É byte-surgery no token — um form de login só atrapalharia. **NÃO** oferecer trilha browser.
> - **Trilha BURP-ONLY (`CLAUDE.md` §3.3 — Burp é a ferramenta principal).** Diferente do 31 (que era **Burp-adjacent**, com o crack de hash rodando no terminal fora do Burp), **aqui o ataque inteiro cabe no Burp**: o atacante lê o token da resposta, **manipula os bytes cifrados** (recorta/recombina blocos) e reenvia — tudo no Repeater (+ Decoder do Burp pra ver/reencodar o token). **A prova é a resposta HTTP** (o `GET /me` devolvendo admin). **SEM ferramenta offline separada** (não há john/hashcat/RainbowCrack aqui — não se quebra chave nenhuma), **SEM browser** (não há execução client-side). É a trilha **primária Burp**, sem exceção de ferramenta externa.
>   - **RESSALVA TÉCNICA A RESOLVER NA FASE 2 (honesta):** o recorte de blocos de 16 bytes precisa ser **factível à mão no Burp**. Em **base64**, as fronteiras de bloco de 16 bytes **NÃO** casam com as fronteiras de caractere base64 (16 não é múltiplo de 3), então o recorte passa pelo **Decoder do Burp** (base64→bytes→editar→base64). Em **hex**, 16 bytes = **32 hex chars** exatos → recorte direto no Repeater, sem Decoder. **A Fase 2 CONFIRMA fazendo o splice de verdade** e escolhe a codificação que mantém o ataque **Burp-only** e didático (ver "Decisão aberta"). Isto **não** redecide o flavor (Rota 1, travada) — é probe de ergonomia sobre o requisito **travado** ("byte-manip no Repeater, sem ferramenta offline").
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (um login que emite um crachá cifrado carregando o role) e a falha (o crachá é cifrado em AES-ECB). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** cifra de bloco (block cipher), **bloco de 16 bytes**, **modo de operação** (mode of operation), **ECB (Electronic Codebook)**, **determinismo bloco-a-bloco**, **cut-and-paste / block-splicing**, **padding (PKCS#7)**, **modo autenticado / AEAD (Authenticated Encryption with Associated Data)**, **GCM (Galois/Counter Mode)**, **nonce**, **tag de autenticação (authentication tag)** — dar a expansão/definição na estreia. O átomo assume que o aluno **pode não ter feito o 31**: define o vocabulário do zero (pode apontar pro 31 pra ver a variante de armazenamento, mas se explica sozinho).
> - **Título = classe sem stack (`CLAUDE.md` §5).** O H1 nomeia a **classe** ("Encryption with an insecure mode of operation"), **NÃO** o motor ("...em AES"/"...em Python"/"...com pycryptodome"). **DECISÃO REGISTRADA (confirmar grafia na Fase 2):** por analogia com o 31 — cujo H1 é "Insecure password storage (weak hashing)", com o **algoritmo (MD5) FORA** do H1 e só a **classe** — o **"ECB" é nível de algoritmo/motor** (como "MD5"), logo **fica FORA do H1**; o **slug** (`crypto-ecb-mode`) já qualifica a variante. O H1 nomeia a classe genérica: **modo de operação inseguro**. Candidatos (ver "Identidade"). "AES"/"ECB"/"Python" no **corpo**, não no H1.
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Ver o padrão vazando`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A02 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — single-container, stateless (sem DB), e requirements.txt IDÊNTICOS entre os lados

> **Stateless, sem SQLite — molde dos irmãos JWT.** O crachá é **auto-contido** (o servidor cifra `email=...&role=...` dentro dele) — **não** há usuários semeados em banco nem sessão persistida. Cada lado é **um** container Flask sem persistência, como o `jwt-key-confusion` (que traz "Stack note — no database"). **NÃO** usar SQLite: não há o que semear (qualquer e-mail é aceito e vira um crachá `role=user`; o servidor **nunca** emite `role=admin` — você tem que **forjar**). O `docker-compose.yml` é **dois serviços** (molde do 01) — **sem** healthcheck, **sem** `depends_on`, **sem** rede nomeada, **sem** datastore.
>
> **CONTRASTE ESTRUTURAL COM O 31 a cravar: aqui os `requirements.txt` dos dois lados são IDÊNTICOS.** O 31 foi o **primeiro átomo** cujos lados **diferiram** no manifesto (o `fixed` adicionava `bcrypt`). **Este átomo VOLTA ao padrão comum:** os dois lados usam **a mesma dependência** (`Flask` + `pycryptodome`), **mesmo pin**. O delta entre vulnerable e fixed é **só o MODO no código** (`AES.MODE_ECB` → `AES.MODE_GCM` + o `encrypt_and_digest`/`decrypt_and_verify`), **NÃO** uma dependência a mais. Consequências pra a Fase 2:
> - `vulnerable/requirements.txt` = `fixed/requirements.txt` = `Flask==<pin>` + `pycryptodome==<pin>` (idênticos).
> - O **DIFF.md** deve **contrastar honestamente com o 31**: lá o fix trazia uma lib; **aqui o fix é uma linha de código** (o modo), sem mexer no manifesto. É um bom ponto didático (fix de causa ≠ "instalar coisa").
> - **§8:** chave/dados fake, bind **só** `127.0.0.1`, sem PII, chave dummy óbvia; nada destrutivo, nada sai da máquina.

---

## Identidade

- **ID:** `crypto-ecb-mode`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A02 — Cryptographic Failures**. Pasta `atoms/A02-cryptographic-failures/` (**JÁ EXISTE — o 32 reaproveita**). Confirmado contra o `ROADMAP.md` ("A02 Cryptographic Failures") e o `CLAUDE.md` §4. Em prosa, usar o nome da **classe** — **"Encryption with an insecure mode of operation"** (grafia final na Fase 2) — e a categoria — **"A02 — Cryptographic Failures"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A02-cryptographic-failures/crypto-ecb-mode/`
- **Número sequencial:** 32
- **Porta `vulnerable`:** `127.0.0.1:8032`
- **Porta `fixed`:** `127.0.0.1:8132`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos.
- **Topologia:** **SINGLE-CONTAINER por lado** — dois serviços (`vulnerable` + `fixed`), **stateless, sem datastore**. Molde do `sqli-union-basic` (01), sem a parte de SQLite.
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/encerramento** (§5 foreshadow, redobrado).
- **Branch de trabalho:** `atom/crypto-ecb-mode`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** ver seção "Theory primer". **PortSwigger primeiro; provável fallback OWASP (Cryptographic Storage Cheat Sheet, seção de modos/AEAD) — desvio consciente a AVISAR o mantenedor.** **NÃO inventar URL — confirmar por fetch na Fase 2.**
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# crypto-ecb-mode — Encryption with an insecure mode of operation`** — `id` + nome canônico da **classe** em inglês. **SEM** "AES"/"ECB"/"Python" no H1 (ECB é nível de motor, como MD5 no 31). Grafia canônica exata **confirmável na Fase 2** casando com o título da página do primer; **preservar o nome em inglês também no README PT**. *(Alternativas registradas: "Encryption with a broken mode of operation" (a do brief), "Use of an insecure cipher mode". A forma final casa com o primer confirmado.)*

---

## Classe de vulnerabilidade

**Encryption with an insecure mode of operation (ECB) — um token de autoridade cifrado em AES-ECB, forjável por rearranjo de blocos.** Uma app autentica por login: ela emite um **crachá** (token) que carrega a identidade do usuário e o seu **role**, serializado em texto e **cifrado** com AES no modo **ECB**, entregue ao cliente. Em cada request protegido, o servidor **decifra** o crachá, lê o role e responde conforme. A **lógica de login/autorização está correta** — o que está errado é o **MODO de cifra escolhido**: **ECB (Electronic Codebook)**, o modo em que cada bloco de 16 bytes é cifrado **independentemente** com a mesma chave. Duas consequências diretas: (1) blocos de plaintext idênticos produzem blocos de ciphertext idênticos — **o padrão vaza**; (2) como os blocos são independentes, um atacante pode **recortar e recombinar** blocos de ciphertext de crachás legítimos pra montar um crachá que decifra num plaintext que ele nunca poderia ter pedido — **forjando** o role, **sem conhecer a chave**.

### A lição-coração

> **"Uma cifra de bloco (AES) cifra em blocos de tamanho fixo (16 bytes); o MODO DE OPERAÇÃO define como encadear os blocos de uma mensagem maior. O ECB é o modo ingênuo: cada bloco é cifrado INDEPENDENTEMENTE, com a mesma chave — então blocos de plaintext idênticos viram blocos de ciphertext idênticos (o padrão vaza), e como os blocos são independentes, um atacante RECORTA e RECOMBINA blocos de ciphertext pra montar um plaintext forjado, SEM saber a chave. O fix não é 'trocar por CBC' — é um modo AUTENTICADO (AES-GCM) que detecta qualquer bloco adulterado e rejeita."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH)

Definir cada peça na estreia (o aluno pode não ter feito o 31):

- **Cifra de bloco e o bloco de 16 bytes.** AES é uma **cifra de bloco**: ela cifra pedaços de tamanho fixo — **16 bytes** por bloco. Uma mensagem maior que 16 bytes precisa de uma regra pra encadear os blocos: é o **modo de operação**.
- **ECB — cada bloco por conta própria.** No **ECB (Electronic Codebook)**, cada bloco de 16 bytes é cifrado **isoladamente**, com a mesma chave, **sem** relação com os blocos vizinhos. Consequência 1 (**determinismo bloco-a-bloco**): a **mesma** sequência de 16 bytes de plaintext sempre vira o **mesmo** bloco de ciphertext → **o padrão do plaintext aparece no ciphertext** (o famoso "ECB penguin": cifrar a imagem de um pinguim em ECB ainda deixa o pinguim visível). Consequência 2 (**independência**): como nenhum bloco depende do outro, dá pra **reordenar, remover ou colar** blocos de ciphertext de crachás diferentes — cada bloco decifra pro mesmo plaintext, esteja onde estiver.
- **O ataque de cut-and-paste (block-splicing) — o coração deste átomo.** O crachá carrega `role=user`. O atacante controla o próprio **e-mail** no cadastro/login, e o e-mail entra no plaintext do crachá. Ele escolhe um e-mail cujo comprimento **alinha** a palavra `admin` (mais o **padding** que a fecha num bloco cheio) **sozinha, no início de um bloco de 16 bytes**. O `/login` cifra o que ele mandou e devolve o crachá; ele **lê da própria resposta** o bloco de ciphertext que corresponde a esse `admin` — um `E(admin…)` válido. Depois, com um segundo crachá alinhado pra que o valor do role caia sozinho no último bloco, ele **substitui o bloco do `user` pelo bloco do `admin`** que capturou. O servidor decifra bloco-a-bloco → lê `role=admin` → responde como admin. **A chave nunca foi tocada.**
- **PKCS#7 padding (definir).** Como o plaintext raramente é múltiplo exato de 16, cifras de bloco preenchem o fim com **padding**; o esquema padrão é **PKCS#7** (os N bytes finais valem todos `N`). O truque de splice depende disso: o bloco de `admin` capturado precisa carregar um padding PKCS#7 **válido** pra que, ao virar o último bloco do crachá forjado, o `unpad` o aceite e sobre exatamente `admin`. (Detalhe travado no candidato de layout; ver "Decisão aberta".)

O ponto contraintuitivo a cravar: **você não "quebrou" o AES nem descobriu a chave** — você **rearranjou blocos cifrados válidos** como peças de Lego, e o servidor, decifrando cada bloco isoladamente, montou um plaintext que nunca autorizou.

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas do DIFF)

> **A chave nunca é quebrada, nada é decifrado pelo atacante — só blocos são rearranjados. A causa é a INDEPENDÊNCIA DETERMINÍSTICA dos blocos (ECB) + a AUSÊNCIA DE AUTENTICAÇÃO do token, NÃO "a chave é fraca" nem "AES é inseguro". AES está correto; o MODO é o problema. E o fix de causa não é "trocar ECB por CBC" — é um modo AUTENTICADO (AEAD/GCM) que detecta adulteração e rejeita o token antes de olhar o role.**

### Por que A02 (Cryptographic Failures)

O bug **não é** "input virou código" (injection) nem "faltou um check de dono" (broken access control) — a autorização até checa o role corretamente. É **"o modo de operação escolhido pra proteger o segredo em trânsito é inadequado"**: ECB é determinístico bloco-a-bloco (vaza padrão) e o token não é autenticado (adulterável por rearranjo). No Web Top 10 2021 isso é **A02 — Cryptographic Failures**, exatamente onde os irmãos (05/13/14/31) já moram. Situar em **A02 — Cryptographic Failures**, **sem** contar edições antigas.

---

## Contraste com o `crypto-weak-hash` (31) — CENTRAL (é a razão de o átomo existir)

O **31** é a **referência central de contraste** — e justifica o 32 existir. Os dois são **A02 — Cryptographic Failures** e os dois **"parecem crypto"**. Mas divergem no fundo: **ARTEFATO / AÇÃO / CAUSA / TÉCNICA**. Cravar no WALKTHROUGH e no DIFF (tabela + prosa).

- **Artefato + primitivo.** O 31 usa um **hash mão-única** (MD5) pra **ARMAZENAR** uma senha — uma função que **não** se inverte. O 32 usa uma **cifra reversível** (AES) num **modo** (ECB) pra **transportar** um token de autoridade — algo feito pra ser decifrado.
- **AÇÃO do atacante.** No 31 o atacante **RECUPERA o input** (a senha original) — ele quebra por **pré-computação** (rainbow table). No 32 o atacante **NÃO recupera nada e NÃO quebra a chave** — ele **FORJA** um plaintext novo **rearranjando blocos cifrados** (cut-and-paste). Recuperar-segredo vs forjar-por-estrutura.
- **CAUSA.** No 31 a causa é o **primitivo** (hash rápido, sem salt). No 32 a causa é o **MODO** (blocos determinísticos e independentes + token não autenticado). Em nenhum dos dois a causa é "a chave/senha é fraca".

### Tabela de contraste (cravar no DIFF e no WALKTHROUGH)

| Eixo | `crypto-weak-hash` (31) | `crypto-ecb-mode` (32) |
|---|---|---|
| **Categoria OWASP** | A02 — Cryptographic Failures | A02 — Cryptographic Failures (**a mesma**) |
| **Primitivo/artefato** | um **hash mão-única** (MD5) de senha **armazenada** | uma **cifra reversível** (AES) num **modo** (ECB), token **em trânsito** |
| **O que o atacante faz** | **RECUPERA** a senha original (o input) | **FORJA** um plaintext novo (rearranjo de blocos) |
| **Técnica** | **rainbow table** — pré-computa hash→senha | **cut-and-paste** — recorta/recombina blocos de ciphertext |
| **A chave/segredo é quebrada?** | a senha é **recuperada** por adivinhação em massa | **não** — a chave **nunca** é tocada |
| **Causa raiz** | **primitivo** errado (hash rápido, sem salt) | **modo** errado (blocos determinísticos independentes + sem autenticação) |
| **Consequência** | roubo/reuso de credencial (takeover) | forja de token → **escalada de privilégio** (user→admin) |
| **O fix** | trocar o **primitivo** (hash rápido → KDF lento e salgado) | trocar o **modo** (ECB → AEAD autenticado, GCM) |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante):** o aluno que só fez o 31 pode achar que "falha de crypto = recuperar o segredo crackeando". O 32 mostra a **outra face**: aqui **nada é recuperado e nada é crackeado** — a falha é **estrutural** (o modo permite **forjar** por rearranjo). **"Um átomo = uma vuln"** é a **CAUSA** (aqui: o modo de operação inseguro/não-autenticado); o **objeto de estudo do 32** é a forja por **manipulação de blocos** e o porquê de um modo **autenticado** (GCM) derrotar isso **categoricamente** (detecta o bloco adulterado e rejeita).

### Relação com os JWT (05/14) — tema-irmão A02, publicados, citáveis

Os JWT (05 `jwt-none-alg`, 14 `jwt-key-confusion`) são o **tema-irmão** perfeito: lá o objetivo também é **FORJAR um token** pra escalar privilégio (`role: user` → `role: admin`) — mas a forja ataca a **ASSINATURA/autenticidade** (burlar `alg=none`, ou confundir o algoritmo pra assinar com uma chave conhecida). Aqui a forja ataca o **MODO de cifra**: o token nem é assinado, é **cifrado** — e o modo (ECB) permite rearranjar blocos. **Mesmo objetivo (forjar autoridade), superfície diferente (assinatura vs modo de cifragem).** Cravar o paralelo com 05/14 (publicados, citáveis à vontade); é um gancho poderoso pro aluno que já fez os JWT. **Sem** narrar sequência/posição/"arco"/completude (foreshadow, Nota 2).

---

## Uma vuln só — a lógica de login/autz está CORRETA; a chave NÃO é exposta; sem endpoint de cifra genérico

Invariante inegociável do átomo (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o **modo ECB** (determinístico + não-autenticado). Para garantir isso:

- **A lógica de autorização está CERTA.** O servidor decifra o crachá, lê o role, e libera admin **só** se o role for `admin`. **Não** há bypass de lógica, **não** há check ausente (contraste explícito com IDOR/BOLA: aqui o check de role **existe e funciona** — o problema é que o token que ele consulta é **forjável** pelo modo de cifra).
- **A chave NÃO é exposta — CRÍTICO.** **NENHUM** endpoint devolve a chave, nem um "oráculo" que a vaze. A chave é uma **constante dummy fixa no código** (`CLAUDE.md` §8.3) — **e isso NÃO é a vuln** (o ataque funciona **sem** a chave; o WALKTHROUGH c+rava isso). Um endpoint que vazasse a chave seria outra falha — **PROIBIDO**.
- **SEM endpoint de cifra genérico (a "Rota 2", rejeitada).** O app cifra **apenas** o input do fluxo normal (o crachá no `/login`). **NÃO** existe um endpoint "cifre este texto arbitrário pra mim" — isso seria um oráculo de cifragem artificial, uma superfície diferente (e a Rota 2 do brief, **rejeitada**). O atacante obtém os blocos de que precisa **do fluxo legítimo** (controlando o próprio e-mail), não de um oráculo.
- **Sem injection, sem 2ª superfície.** O `GET /` é só o banner JSON. O `/login` emite o crachá; o `/me` decifra e responde. O `fixed` muda **SÓ** o modo de cifra (ECB → GCM: `encrypt`/`decrypt` + o `verify`). Nada mais.

---

## Feature simulada — crachá cifrado em ECB, e-mail controlado (TRAVADO — Rota 1)

Uma app de **sessão API-only**, stateless:

- **`GET /`** — banner JSON de aviso (molde do 31): `{"warning": "⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.", "hint": "POST /login to get a badge, then GET /me with it. Work from Burp Repeater."}`. **Não injetável.**
- **`POST /login`** — corpo JSON `{"email": "...", "password": "..."}` (a autenticação é **simulada**, molde dos JWT: o `password` é ortogonal/nominal — ver abaixo; o que importa é que o **e-mail é atacante-controlado**). O servidor monta o plaintext do crachá (`email=<email>&role=user`), cifra com **AES-ECB**, e devolve o crachá **serializado em texto** (base64 **ou** hex — ver "Decisão aberta") no corpo da resposta: candidato `{"badge": "<token>"}`. **O role emitido é SEMPRE `user` — o servidor NUNCA emite `admin`.** (Igual aos JWT: você não loga como admin, você **forja**.)
- **`GET /me`** — lê o crachá (candidato: header `Authorization: Bearer <token>`; confirmar na Fase 2), **decifra**, faz o parse de `email=...&role=...`, e responde conforme o role: `role=user` → o próprio perfil (candidato `{"email": "...", "role": "user"}`); `role=admin` → **recurso privilegiado** (candidato `{"email": "...", "role": "admin", "admin_area": "<conteúdo só-admin dummy>"}`). **A prova da forja é esta resposta** (o `role: admin` / o `admin_area` liberado a partir de um crachá que o servidor nunca emitiu como admin).

**Autenticação simulada (molde dos JWT — ortogonal à vuln).** O `password` no `/login` **não** é a superfície: seguir o padrão do `jwt-none-alg`/`jwt-key-confusion` (auth simulada, sem verificação real de senha) — o `/login` aceita o e-mail atacante-controlado e emite um crachá `role=user`. **CONFIRME NA FASE 2** a forma exata (ignorar o password vs aceitar qualquer valor vs checar contra um usuário dummy) — o invariante **travado** é: **(a) o e-mail que entra no crachá é atacante-controlado; (b) o servidor nunca emite `role=admin`.** Registrar o resto como confirmável, mantendo o átomo mínimo.

- **HTML: NENHUM** (API-only). Sem `templates/`, sem `render_template`.
- **A chave é uma constante dummy fixa** (16/24/32 bytes; candidato 16 bytes) — óbvia e não-secreta (`CLAUDE.md` §8.3). **A chave NÃO é a vuln** — o ataque funciona sem ela.

---

## O "tell" do ECB, na rede (mostrar, não só afirmar)

**ANTES** do splice, o WALKTHROUGH DEVE mostrar a propriedade central de forma **observável no Burp**: submeter um `/login` com um e-mail contendo um **PADRÃO REPETIDO** (ex.: um e-mail com 32+ bytes idênticos, alinhado pra encher dois blocos inteiros com o mesmo conteúdo) e mostrar, no crachá decodificado em **hex**, **DOIS blocos de 16 bytes IDÊNTICOS** — o "ECB penguin" em miniatura, direto na resposta HTTP. É a **prova visível** de que bloco-de-plaintext-igual → bloco-de-ciphertext-igual, que **fundamenta** o splice.

- Isto é **observável na resposta HTTP** (o crachá vem no corpo) + o **Decoder do Burp** (pra ver os bytes em hex). Sem ferramenta externa.
- O **penguin VISUAL** (a imagem clássica do pinguim cifrado em ECB) fica no **theory primer** como ilustração canônica do conceito — **NÃO** no passo de ataque (o ataque mostra os bytes, não a imagem).
- **VALIDAR RODANDO na Fase 2** e capturar o hex real com os dois blocos idênticos (o comprimento exato do e-mail de padrão repetido = probe; ver checklist).

---

## O ataque (cut-and-paste no Burp) + a prova (TRAVADO; espinha = block-splicing)

**Cenário travado; o layout exato do crachá é candidato confirmado por probe (Fase 2 — ver "Decisão aberta").** Cadeia, **tudo no Burp** (Repeater + Decoder):

1. **Baseline:** `POST /login` com um e-mail normal → recebe o crachá; `GET /me` com ele → responde como **`user`**. Idêntico nos dois lados.
2. **O tell (padrão vazando):** `POST /login` com e-mail de padrão repetido → decodificar o crachá em hex → **dois blocos de 16 bytes idênticos**. Prova de que ECB é determinístico bloco-a-bloco.
3. **Capturar o bloco `admin`:** `POST /login` com o **e-mail de alinhamento** (comprimento calculado pra `admin`+padding cair sozinho num bloco) → da resposta, isolar o bloco de ciphertext que corresponde a `E(admin…)`.
4. **Montar o crachá forjado:** `POST /login` com o **e-mail do "crachá vítima"** (comprimento calculado pra o valor do role cair sozinho no último bloco) → **substituir** o bloco do `user` pelo bloco do `admin` capturado no passo 3.
5. **A prova:** `GET /me` com o crachá forjado no **vulnerable (8032)** → responde como **admin** (`role: admin` / `admin_area` liberado). Conta escalada, **sem** a chave.

**FIXED (8132):** o **mesmo** crachá recombinado, sob **AES-GCM**, **falha o selo de autenticação** — `decrypt_and_verify` levanta exceção porque a **tag** (o selo que liga o ciphertext ao seu conteúdo) não bate com os blocos adulterados → o servidor **REJEITA** o token (candidato: `401`/`400`) **ANTES** de olhar o role. A prova do fix é essa **rejeição observável** — e o baseline (crachá íntegro) funciona **idêntico** nos dois lados. §8: chave/dados dummy, `127.0.0.1`, nada destrutivo.

### Prova de isolamento (o que traça a diferença PURO ao modo)

- **Baseline legítimo, IDÊNTICO nos dois lados:** um crachá **íntegro** (não adulterado) → `GET /me` responde como `user` nos **dois** lados. O fluxo funciona igual; só o crachá **adulterado** separa vulnerable de fixed.
- **Ataque:** no **vulnerable**, o crachá recombinado decifra em `role=admin` (ECB decifra cada bloco isoladamente, aceita o Frankenstein) → admin. No **fixed**, o crachá recombinado **falha a tag GCM** → rejeitado. A diferença é **100% o modo de cifra**, não a chave (a mesma) nem a lógica de autz (idêntica).

---

## Prova — BENIGNA E OBSERVÁVEL (`CLAUDE.md` §8)

A prova é a **forja do crachá + o acesso privilegiado liberado** — **sem RCE**, sem dump destrutivo. Cadeia:

- **Baseline:** crachá íntegro → `GET /me` como `user`, **idêntico** nos dois lados.
- **Ataque (vulnerable):** cut-and-paste de blocos → crachá que decifra em `role=admin` → `GET /me` libera o recurso privilegiado (escalada).
- **Fixed:** o mesmo crachá recombinado → a tag GCM falha → token **rejeitado** antes de ler o role → sem escalada.

Tudo **no Burp**, `127.0.0.1`, containers descartáveis; **dados/chave dummy** (chave óbvia, e-mails fake); **nada sai da máquina, nada destrutivo**. O WALKTHROUGH deixa **explícito** que é um lab local e a escalada é uma **prova de conceito benigna**. **Não overclamar** (impacto = forja de token → escalada de privilégio; **não** RCE, **não** recuperação de chave).

---

## O código — o coração no modo de cifra (candidatos; a Fase 2 gera o real)

O fio condutor: **como o crachá é cifrado e decifrado**. O `app.py` **DIFERE** entre os lados **no modo de cifra** (`issue_badge`/`read_badge`); todo o resto — `GET /` banner, o parse do corpo, a montagem do plaintext `email=...&role=...`, o parse do role, os endpoints — é **IDÊNTICO na forma** (só o modo muda).

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma o `pycryptodome` instalando/rodando (ECB e GCM), captura o splice real reproduzindo `role=admin`, e trava o layout do crachá por probe.**

### `vulnerable/app.py` — AES-ECB (candidato)

```python
import os
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Flask, request, jsonify

app = Flask(__name__)
# Dummy fixed key -- this is a lab; the KEY is NOT the vuln (CLAUDE.md §8.3). The attack
# below never touches the key. Must be 16/24/32 bytes; candidate 16 bytes (confirm in Phase 2).
KEY = b"0123456789abcdef"


def issue_badge(email, role):
    plaintext = f"email={email}&role={role}".encode()
    # VULNERABLE: AES-ECB. Each 16-byte block is encrypted INDEPENDENTLY with the same key, so
    # identical plaintext blocks -> identical ciphertext blocks (the pattern leaks), and blocks
    # can be CUT and REARRANGED to forge a plaintext without knowing the key. The mode is the flaw.
    cipher = AES.new(KEY, AES.MODE_ECB)
    token = cipher.encrypt(pad(plaintext, AES.block_size))
    return base64.b64encode(token).decode()  # or hex -- see "Decisão aberta"


def read_badge(token):
    cipher = AES.new(KEY, AES.MODE_ECB)
    plaintext = unpad(cipher.decrypt(base64.b64decode(token)), AES.block_size)
    # parse "email=...&role=..." -> dict {email, role}
    fields = dict(kv.split("=", 1) for kv in plaintext.decode().split("&"))
    return fields


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "POST /login to get a badge, then GET /me with it. Work from Burp Repeater.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    # Simulated auth (JWT-sibling pattern): the password is orthogonal to the vuln; role is
    # ALWAYS "user" -- the server never mints an admin badge. You have to FORGE it.
    badge = issue_badge(email, "user")
    return jsonify({"badge": badge})


@app.route("/me")
def me():
    token = (request.headers.get("Authorization", "") or "").removeprefix("Bearer ").strip()
    try:
        fields = read_badge(token)
    except Exception:
        return jsonify({"error": "invalid badge"}), 400
    if fields.get("role") == "admin":
        return jsonify({"email": fields.get("email"), "role": "admin",
                        "admin_area": "dummy admin-only content"})
    return jsonify({"email": fields.get("email"), "role": fields.get("role")})


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — AES-GCM (autenticado) (candidato)

Só `issue_badge`/`read_badge` mudam; o resto é idêntico:

```python
import os
import base64
from Crypto.Cipher import AES
from flask import Flask, request, jsonify

# ... GET /, /login, /me identical to vulnerable, calling issue_badge/read_badge ...

def issue_badge(email, role):
    plaintext = f"email={email}&role={role}".encode()
    # FIXED: AES-GCM is an AUTHENTICATED mode (AEAD). encrypt_and_digest returns a tag that binds
    # the whole ciphertext; a unique nonce per message removes ECB's determinism. Any tampered or
    # rearranged block fails verification on read. We pack nonce + tag + ciphertext together.
    cipher = AES.new(KEY, AES.MODE_GCM)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    return base64.b64encode(cipher.nonce + tag + ct).decode()


def read_badge(token):
    raw = base64.b64decode(token)
    nonce, tag, ct = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(KEY, AES.MODE_GCM, nonce=nonce)
    # decrypt_and_verify RAISES if the tag doesn't match -- a tampered badge is rejected here,
    # before the role is ever read.
    plaintext = cipher.decrypt_and_verify(ct, tag)
    fields = dict(kv.split("=", 1) for kv in plaintext.decode().split("&"))
    return fields
```

- **O CONTRASTE (MODE_ECB vs MODE_GCM + o `decrypt_and_verify`) é o diff.** `GET /`, o `/login`, o `/me`, o parse — **idênticos na forma**.
- **Confirmar na Fase 2:** os tamanhos do `nonce` (default do pycryptodome no GCM é 16 bytes) e da `tag` (16 bytes) e a ordem de empacotamento (`nonce+tag+ct`); o `unpad`/`pad` no ECB (PKCS#7, `AES.block_size`); a chave dummy de 16 bytes limpa. **Validar rodando** que o splice reproduz `role=admin` no ECB e é **rejeitado** no GCM.

---

## O fix e o tipo de diff

**Fix:** **trocar o MODO** — de ECB (`AES.MODE_ECB`, determinístico e não-autenticado) por um modo **AUTENTICADO** (`AES.MODE_GCM`, com nonce único por mensagem e uma tag que sela o ciphertext). Tipo de diff: **lógica-diferente no ponto do cipher** (`issue_badge`/`read_badge`). O resto (`GET /`, `/login`, `/me`, o parse) é **idêntico na forma**.

**O CONTRASTE é o diff:** cifra determinística sem autenticação (vulnerable) vs cifra autenticada com nonce (fixed). **A mudança é o modo** — no `encrypt`/`decrypt` e no `verify`. **Os `requirements.txt` NÃO mudam** (mesma lib, mesmo pin nos dois lados) — o fix é uma linha de código, não uma dependência (contraste honesto com o 31).

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é o MODO, não a chave nem "AES".** O bug **não** é "a chave é fraca" nem "AES é inseguro" — **AES está correto**, e a **chave nunca é tocada** no ataque. A causa é o **modo**: blocos determinísticos e independentes (ECB) num token **não autenticado**. Trocar a chave ou "usar mais bits de AES" **não** resolve nada.
2. **"É só trocar ECB por CBC" — nota-ARMADILHA COM HONESTIDADE EM CAMADAS.** Nomear a intuição: *"o problema era o padrão vazando e o cut-and-paste, então troca por CBC."* Ser **honesto**: CBC **mata o padrão-vazando** (o penguin) e **quebra o cut-and-paste limpo** (os blocos deixam de ser independentes) — isso é uma **melhora REAL**, não pura armadilha. **MAS** CBC deixa o token **NÃO-AUTENTICADO** — ainda adulterável por outros meios. Sair do ECB é **necessário mas não suficiente**. A lição funda: um **token de autoridade cifrado à mão SEM autenticação** é frágil **em qualquer modo** → a resposta é **AEAD** (GCM), que **autentica**. **CBC = melhora-parcial-legítima, não armadilha pura** (mesmo espírito da nota do salt no 31). **NÃO** nomear as técnicas específicas que ainda quebram um CBC não-autenticado (são de outro modo/átomo — foreshadow; ver Nota 1).
3. **Determinístico vs semântica (nonce).** ECB **não** tem IV/nonce → é **determinístico** (a mesma mensagem sempre dá o mesmo ciphertext — é o que vaza o padrão e viabiliza reconhecer/reusar blocos). GCM usa um **nonce único por mensagem** → a mesma mensagem cifra diferente a cada vez (segurança semântica), e a **tag** liga o ciphertext ao seu conteúdo.
4. **Impacto.** Forja de token de sessão → **escalada de privilégio** (user→admin) / bypass de autorização. **Não** inflar pra RCE nem pra "recuperação de chave" (a chave nunca é obtida).

---

## Biblioteca / stack

- **`vulnerable/` e `fixed/`: Flask + `pycryptodome`** (AES ECB/GCM, `pad`/`unpad`). `base64` é stdlib (não vai no requirements).
- **Os `requirements.txt` são IDÊNTICOS entre os lados** (Nota de planning 4) — **mesmo pin**. O delta vulnerable×fixed é **só o modo no código**, **não** uma dependência. **Contraste explícito com o 31** (onde os lados diferiam por causa do `bcrypt`): aqui o fix é uma **linha de código**.
- **Confirmar o pin do `pycryptodome` rodando na Fase 2.** `pycryptodome` distribui **wheel** (com binário nativo) — provavelmente instala no `python:3.11-slim` **sem toolchain de build** (paralelo à memória `rsa-atoms-crypto-wheel`, que confirmou `cryptography`/`PyJWT` instalando como wheel). **Confirmar RODANDO**; se exigir toolchain, documentar (ou pinar uma versão com wheel manylinux). `Flask==3.0.0` casa com os irmãos. **Import é `from Crypto.Cipher import AES`** (pacote `pycryptodome`, namespace `Crypto`) — **NÃO** confundir com o `pycrypto` morto.
- **SEM** ORM, `requests`, SQLite, ou 2ª dependência. `CLAUDE.md` §3.6. Stateless.
- **SEM SAÍDA B:** o `AES.MODE_ECB` é o **próprio antipadrão** que um iniciante escreve ao pegar a receita mais curta de "cifrar com AES" (é o modo default histórico em muitos exemplos ruins) — exatamente como o `hashlib.md5` no 31. **Declarar isso explicitamente:** o vulnerable **não** é uma configuração rebuscada, é o caminho ingênuo mais comum. Não há "saída B" (variante alternativa da vuln) a modelar — a única falha é o modo.

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY JSON** (o vetor é o **token cifrado** manipulado no Repeater; decisão de forma justificada na Nota de planning 3). Garantir que a **ÚNICA** vuln é o **modo ECB**:

- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (molde do 31). **O `GET /` não é injetável.**
- **A lógica de autz está CORRETA** (o check de role existe e funciona); **sem injection**; **a chave NÃO é exposta** (nem oráculo de cifra genérico — Rota 2 rejeitada). **NÃO** empilhar 2ª superfície.
- **O `fixed` muda SÓ o modo de cifra** (`issue_badge`/`read_badge`: ECB → GCM + o `verify`). `GET /`, `/login`, `/me`, o parse são idênticos na forma.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é ir pra um modo **AUTENTICADO (GCM)**, **NÃO** só sair do ECB pra CBC (a armadilha da nota #2 do DIFF). A chave é a **mesma** nos dois lados — o que muda é **o modo**.

---

## WALKTHROUGH — abertura seca; Burp-only; headers PT traduzidos

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (um login que emite um crachá cifrado carregando o role) e a falha (o crachá é cifrado em AES-ECB). Trilha **Burp-only**: o ataque inteiro (ler o token, recortar/recombinar blocos, reenviar) roda **no Burp** (Repeater + Decoder); **a prova é a resposta HTTP** (`GET /me` como admin). **SEM ferramenta offline, SEM browser.**

**Abertura (candidato — plantar a lição, seco):**

> *A app é um login: você manda e-mail e senha, ela te devolve um crachá cifrado que carrega quem você é e o seu role, e todo request protegido decifra esse crachá pra decidir o que liberar. A autorização está certa — ela checa o role. O problema é o modo de cifra do crachá: AES-ECB. Uma cifra de bloco cifra em pedaços de 16 bytes; o ECB cifra cada pedaço isoladamente, com a mesma chave. Então blocos de plaintext idênticos viram blocos de ciphertext idênticos, e — porque os blocos são independentes — você pode recortar e recombinar blocos de crachás legítimos pra montar um crachá que decifra em role=admin, sem nunca saber a chave.*

Beats (molde do 31 — abertura seca, seções numeradas `## 1..N`; token no Repeater; **sem browser, sem ferramenta offline**):

1. **Context.** A feature: `POST /login` emite o crachá cifrado; `GET /me` decifra e responde conforme o role. **Definir na estreia:** **cifra de bloco (block cipher)**, **bloco de 16 bytes**, **modo de operação**, **ECB (Electronic Codebook)**, **determinismo bloco-a-bloco**, **cut-and-paste / block-splicing**, **PKCS#7 padding**, **modo autenticado / AEAD**, **GCM (Galois/Counter Mode)**, **nonce**, **tag de autenticação**. Isto é **A02 — Cryptographic Failures**. Portas: `vulnerable` `127.0.0.1:8032`, `fixed` `127.0.0.1:8132`. Trilha: **Burp (Repeater + Decoder)**; sem browser, sem ferramenta offline. Cravar: **você não vai quebrar a chave** — o crachá é forjado por **estrutura**.
2. **The tell — o padrão vazando (OBRIGATÓRIO, ANTES do splice).** `POST /login` com um e-mail de **padrão repetido** → decodificar o crachá em hex → **dois blocos de 16 bytes idênticos**. É a prova visível de que ECB é determinístico bloco-a-bloco — a base do splice. (Mencionar o "ECB penguin" como a ilustração canônica; a imagem mora no primer.)
3. **Spot the bug.** Mostrar o `vulnerable/app.py`: `issue_badge`/`read_badge` usando `AES.MODE_ECB`. Apontar que a **autz está correta** (o check de role funciona) — o bug é o **modo**. Pergunta de auditoria: *"cifrar um token de autoridade em ECB — esse modo é adequado?"* → não: determinístico (vaza padrão) + blocos independentes (recombináveis) + não-autenticado (adulterável). Foreshadow do fix: **um modo autenticado**.
4. **Exploitation (Burp — o cut-and-paste; a prova é o `GET /me`).**
   - **4a — baseline:** login normal → crachá → `GET /me` responde `user`.
   - **4b — montar o e-mail de alinhamento** (comprimento calculado pra `admin`+padding cair sozinho num bloco — o cálculo travado no candidato de layout; ver "Decisão aberta").
   - **4c — capturar o bloco `admin` cifrado** da resposta do `/login` (isolar o bloco de ciphertext do `admin`).
   - **4d — montar o crachá vítima** (e-mail de comprimento que põe o valor do role sozinho no último bloco) e **substituir o bloco do `user` pelo do `admin`** capturado.
   - **4e — a prova:** `GET /me` com o crachá forjado no vulnerable → **responde como admin** (`role: admin` / `admin_area`). Bloco colável no Repeater.
   - **§8 (cravar):** lab **isolado** (bind só `127.0.0.1`; container descartável); tudo **no Burp**; chave/dados **dummy**; **sem** RCE, **nada** destrutivo, nada sai da máquina.
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'".
6. **Impact (honesto — sem overclaim).** Ver "Impacto honesto".
7. **Why the fix works (porta 8132).** Repetir contra o `fixed/`:
   - No fixed, o crachá é cifrado em **AES-GCM** (autenticado). O **mesmo** crachá recombinado do passo 4 → `decrypt_and_verify` **falha a tag** → o servidor **rejeita** (candidato `401`/`400`) **antes** de ler o role. A prova é a **rejeição observável** na resposta HTTP.
   - **Determinismo vs nonce:** repetir o "tell" (passo 2) contra o fixed → **os blocos NÃO se repetem** (o nonce único por mensagem quebra o determinismo). Bom contraste observável.
   - **Prova de isolamento:** crachá **íntegro** → `GET /me` como `user` **idêntico** nos dois lados; **só** o crachá **adulterado** separa vulnerable (vira admin) de fixed (rejeitado). A diferença é **100% o modo**.
   - **A lição do diff:** o fix **troca o modo** por um **autenticado (GCM)**. **NÃO** é "trocar a chave", **NÃO** é "só sair do ECB pra CBC" (nota #2 — CBC ajuda, mas deixa o token não-autenticado). (Forward pro DIFF.)

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Requests/responses/tokens são **placeholders** da execução real capturada na Fase 2 (o hex real com os blocos repetidos, o crachá forjado real, o layout travado por probe).

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5)

Isola a causa e desmonta os mal-entendidos vizinhos (os quatro):

- **(a) NÃO é que "a chave é fraca / foi vazada".** A chave **nunca** é quebrada nem usada pelo atacante — o rearranjo de blocos funciona **sem** a chave. **Prova de isolamento categórica:** a **mesma** chave, no lado **fixed**, cifra em GCM, e o crachá recombinado é **rejeitado** — a diferença é **100% o modo**, não a chave.
- **(b) NÃO é que "AES é inseguro".** O **AES está correto**; o **MODO (ECB)** é a falha. Um modo autenticado (GCM) com o **mesmo AES** e a **mesma chave** neutraliza o ataque.
- **(c) NÃO é injection nem input malicioso clássico.** Você **não** injetou código nem quebrou um parser — você **rearranjou bytes CIFRADOS válidos** (blocos que a própria app emitiu). Nenhum input virou código.
- **(d) NÃO é o problema do 31.** Lá (`crypto-weak-hash`) é um **hash mão-única** de senha, **recuperado** por pré-computação (rainbow table). Aqui é uma **cifra reversível** **forjada** por estrutura de blocos — nada é recuperado, nada é crackeado. (Contraste central; citar o 31, publicado.)

---

## Impacto honesto

**Forja de token de sessão → escalada de privilégio (user→admin) / bypass de autorização.** O atacante monta um crachá que decifra em `role=admin` — sem credencial de admin, sem a chave — e o servidor o trata como admin. **Sem overclaim:** o finding é **forja de token + escalada de privilégio** — **NÃO** inflar pra RCE (não há execução de código), **NÃO** afirmar "recuperação de chave" (a chave nunca é obtida). O teto é **o que o role forjado libera**. A classe "modo de operação inseguro" tem **outras faces** (outros modos têm suas próprias falhas de determinismo/maleabilidade) — **descrição de UMA linha da classe**, **sem** modelar nem nomear átomo/variante/técnica futura (foreshadow, Nota 2 — inclusive **sem** citar bit-flipping/padding oracle, que são de outro modo). A **prova do lab é benigna** (o crachá forjado, o `admin_area` dummy). Sem foreshadow.

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A02 — átomo dentro de família publicada; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`crypto-weak-hash` (31)** — o contraste **central** (seção dedicada + tabela). Mesma A02, os dois "parecem crypto"; o que **difere** é ARTEFATO (hash mão-única vs cifra reversível), AÇÃO (recuperar o segredo vs forjar por estrutura), CAUSA (primitivo vs modo) e TÉCNICA (rainbow table vs cut-and-paste). Referência pra **trás**, permitida.
- **`jwt-none-alg` (05) e `jwt-key-confusion` (14)** — irmãos A02, tema-irmão "**forjar um token** de autoridade". Lá a forja ataca a **assinatura/autenticidade**; aqui ataca o **modo de cifra**. Gancho forte pro aluno que já fez JWT. Referência pra **trás**, permitida.
- **`sqli-union-basic` (01)** — molde canônico de código/doc (single-container Flask). Citável.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5; e esta spec é pública):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer** átomo/categoria/variante/técnica futura por número, nome, slug **OU** descrição — inclusive outros A02 futuros, "próxima fase", "outras faces do modo inseguro" modeladas como átomo futuro, ou a posição/ordinal/release de fase. **ESPECIFICAMENTE PROIBIDO:** **bit-flipping** e **padding oracle** (o parêntese do ROADMAP) — são ataques de **outro modo (CBC)**, apontariam pra um eventual átomo de CBC; **não entram** no conteúdo. Quando a tentação surgir, generalizar ("outros modos têm suas próprias falhas") **sem** nomear técnica/modo/átomo.
- **PROIBIDO anunciar posição de fase (abrir/fechar/ordinal/"primeiro de"/"penúltimo"), versão/release, ou a sequência de átomos ao redor.** O átomo — **e esta spec** — se descreve **isolado**. Nas frases que proíbem foreshadow, manter a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).
- Que "modo inseguro tenha outras faces" é, no máximo, **descrição conceitual de UMA LINHA** — **sem** nomear átomo/variante/técnica futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy / OWASP.

**LIMITE DE ESCOPO:** o 32 vai até **forjar um crachá que decifra em `role=admin` por cut-and-paste de blocos ECB → `GET /me` liberando o recurso privilegiado** (o finding), provado pela resposta HTTP. **Uma vuln, uma causa (o modo ECB — determinístico, independente, não-autenticado), um fix (trocar o modo por um AEAD autenticado — GCM).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar.**

- **PortSwigger PRIMEIRO — mas PROVÁVEL fallback OWASP (AVISAR o mantenedor).** A PortSwigger Academy foca em vulns **web** (SQLi, XSS, SSRF, JWT attacks, auth) e **provavelmente NÃO tem uma página conceitual dedicada a "ECB mode" / "cipher modes of operation"** (mesma situação do 31, que caiu no fallback OWASP). **A Fase 2 DEVE buscar por fetch** — se houver uma página conceitual limpa (ex.: algo em criptografia/cryptographic failures na Academy), usá-la.
- **FALLBACK justificado (provável): OWASP Cryptographic Storage Cheat Sheet** (seção de modos de operação / AEAD). Candidato de URL a confirmar por fetch: `https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html`. **É um desvio consciente da convenção "PortSwigger" do §5** — a fonte OWASP é autoridade canônica de armazenamento/modos e cobre exatamente a lição (evitar ECB, usar AEAD/GCM), e o `CLAUDE.md` §14 já credita OWASP. **AVISAR o mantenedor explicitamente** de que este átomo diverge da fonte-padrão do primer, e por quê (mesmo padrão do 31).
- **A ilustração do "ECB penguin"** (a imagem clássica do pinguim cifrado em ECB, canônica do conceito) pode ser **referenciada** como o exemplo canônico — confirmar por fetch uma fonte estável (ex.: a página da Wikipedia sobre modos de operação de cifra de bloco, que hospeda a imagem canônica). **NÃO** incorporar a imagem no ataque (o ataque mostra bytes); é ilustração conceitual do primer.
- **Texto do link:** preservar o nome da página em **inglês** também no README PT (`CLAUDE.md` §7).
- **NÃO inventar URL nem grafia** — confirmar por fetch na Fase 2; se não conseguir verificar, **perguntar ao mantenedor** (`CLAUDE.md` §5).

---

## A trilha e a ferramenta — Burp-only, sem ferramenta offline

Diferente do 31 (que precisava do RainbowCrack, uma ferramenta offline separada, pra quebrar o hash), **este átomo não quebra nada** — a forja é **manipulação de bytes no Burp**. Disciplina:

- **Mostrar o passo a passo do ataque:** ler o crachá da resposta, decodificar (Decoder do Burp), identificar/recortar os blocos de 16 bytes, recombinar, reenviar no Repeater. **Tudo no Burp.**
- **SEM** john/hashcat/RainbowCrack ou qualquer cracker — **não há chave/segredo a quebrar**. **SEM** browser — a prova é a resposta HTTP.
- **A ergonomia do recorte de blocos** (base64 via Decoder vs hex direto no Repeater) é **Decisão Aberta** (ver abaixo) — a Fase 2 escolhe a que mantém o ataque **Burp-only e didático**, provando por execução.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A02 — Cryptographic Failures** (`atoms/A02-cryptographic-failures/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `crypto-ecb-mode` em A02; `CLAUDE.md` §4 fixa a pasta. Situar em A02 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Escopo (vs parêntese do ROADMAP) | **SÓ ataques genuínos de ECB** (determinismo → penguin + cut-and-paste) | "bit-flipping/padding oracle" são de **CBC** — fora do escopo, **não** mencionar (foreshadow de outro modo/átomo). |
| Topologia | **SINGLE-CONTAINER por lado** — 2 serviços, **stateless (sem DB)** | Molde do `01` sem SQLite; crachá auto-contido, molde dos JWT (14 tem "no database"). |
| Estado | **Stateless** — token auto-contido, sem sessão persistida | A autoridade viaja no crachá cifrado; nada a semear. |
| Lição-coração | **Modo errado: ECB (determinístico, independente, não-autenticado). Fix = modo AUTENTICADO (GCM), não "trocar por CBC" nem "trocar a chave".** | Blocos idênticos vazam padrão; blocos independentes recombinam; token não-autenticado é forjável. |
| Sub-lição crítica | **A chave nunca é quebrada; a causa é o MODO (não "chave fraca" nem "AES inseguro")** | O rearranjo funciona sem a chave; AES está correto. |
| Contraste central | **`31` (crypto-weak-hash)** — mesma A02, "parece crypto"; difere ARTEFATO/AÇÃO/CAUSA/TÉCNICA | Justifica o átomo. 31 = hash mão-única, recuperar por rainbow table; 32 = cifra reversível, forjar por blocos. |
| Contraste de apoio | **`05`/`14` (JWT)** — forjar token via assinatura; **`01`** molde de código/doc | Publicados; ancoram a lição (forja de token; superfície diferente). Sem foreshadow. |
| Eixo pedagógico | **Forja por rearranjo de blocos (cut-and-paste), sem quebrar a chave** | O que separa do 31 (recuperação) e dos JWT (ataque à assinatura). |
| Tipo de átomo | **API-only JSON** (sem HTML, sem templates, sem browser) | Átomo de token; prova = resposta HTTP; molde 05/14/31. **Sem alternativa de HTML.** |
| Trilha | **BURP-ONLY: Repeater + Decoder; sem ferramenta offline, sem browser** | O ataque é byte-manip do token; a prova é a resposta HTTP. |
| Flavor — **TRAVADO (Rota 1)** | **Login API-only emite crachá cifrado (`email=...&role=user`) em AES-ECB; e-mail atacante-controlado; forja por splice de blocos; `GET /me` prova** | A ÚNICA superfície é o modo. Chave **não** exposta; **sem** endpoint de cifra genérico (Rota 2 rejeitada). |
| Rota 2 (cifra genérica) | **REJEITADA** — sem endpoint "cifre-me isto" | Seria oráculo artificial / 2ª superfície; o atacante usa o fluxo legítimo (controla o e-mail). |
| Endpoints | **`GET /` banner · `POST /login` emite crachá `role=user` · `GET /me` decifra e responde por role** | Mínimo; o servidor **nunca** emite `role=admin` (você forja), molde dos JWT. |
| Auth — **candidato, confirmar** | **Simulada (password ortogonal/nominal)**; e-mail atacante-controlado; nunca emite admin | Molde dos JWT (05/14). Invariante travado: e-mail controlado + nunca-admin. Confirmar forma exata. |
| O "tell" (penguin na rede) | **e-mail de padrão repetido → 2 blocos de 16B idênticos no crachá (hex)** | Prova visível do determinismo bloco-a-bloco; fundamenta o splice. Params (comprimento) = probe. |
| Prova — **conceito TRAVADO, layout = probe** | **baseline user → tell → capturar bloco `admin` → splice sobre o bloco `user` → `GET /me` admin** | Layout exato do crachá = DECISÃO ABERTA (Fase 2, rodando). Fixed: GCM rejeita o crachá adulterado (tag falha). |
| Código vulnerable | **`AES.new(KEY, AES.MODE_ECB)`**; `encrypt(pad(...))` / `unpad(decrypt(...))` | O modo errado. Autz logicamente correta. |
| Código fixed | **`AES.new(KEY, AES.MODE_GCM)`**; `encrypt_and_digest` / `decrypt_and_verify` (levanta se a tag falha) | Modo autenticado; detecta adulteração e rejeita. Nonce único por mensagem. |
| `app.py` vulnerable × fixed | **DIFERE** só no modo (`issue_badge`/`read_badge`) | O fix vive no ponto do cipher. |
| Fix (único eixo) | **Trocar o MODO** (ECB → GCM autenticado) | Correção na raiz. NÃO "trocar a chave", NÃO só "ECB→CBC". |
| Diff | **Lógica-diferente** (issue_badge/read_badge); **requirements IDÊNTICOS** | O coração é o modo no `app.py`; **contraste com o 31** (lá o requirements diferia). |
| `requirements.txt` | **IDÊNTICOS** — Flask + pycryptodome, mesmo pin nos dois lados | O fix é uma linha de código, não uma dependência. |
| "Só trocar ECB por CBC" | **Mencionar como melhora-parcial-legítima, NÃO aplicar** (nota #2, honestidade em camadas) | CBC mata penguin+cut-and-paste limpo (melhora real), mas deixa o token não-autenticado. AEAD (GCM) é o fix. |
| Chave | **Constante dummy fixa (16B candidato), idêntica nos dois lados** | `CLAUDE.md` §8.3. **A chave NÃO é a vuln** — o ataque funciona sem ela. |
| Bibliotecas | **Flask + pycryptodome** (os dois lados, mesmo pin) | AES ECB/GCM + pad/unpad. Instala como wheel (confirmar). Sem ORM/DB/dep extra. |
| Banner | **Obrigatório, num `GET /` JSON de aviso** (API-only) | `CLAUDE.md` §8.2. `GET /` não injetável. |
| Impacto | **Forja de token → escalada de privilégio (user→admin).** Sem RCE, sem recuperação de chave. | Honesto; teto = o que o role forjado libera. Sem foreshadow. |
| Theory primer | **PortSwigger primeiro; PROVÁVEL fallback OWASP Cryptographic Storage Cheat Sheet** | Academy provavelmente sem página conceitual de modos ECB. Desvio consciente — avisar (molde do 31). Confirmar por fetch. |
| Título (H1) | **`crypto-ecb-mode — Encryption with an insecure mode of operation`** (classe, sem stack) | `CLAUDE.md` §5. "ECB" é nível de motor (como MD5 no 31) → fora do H1; o slug já qualifica. Grafia final casa com o primer. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública); **sem** bit-flipping/padding oracle/CBC-como-átomo | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release/técnicas de outro modo. |
| Portas | **8032 / 8132** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container por lado. |
| Codificação do token | **base64 candidato (brief); hex como alternativa** — **DECISÃO ABERTA** | Recorte de bloco à mão precisa ser Burp-only; base64 via Decoder, hex direto. Fase 2 escolhe rodando. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si** (molde do `31`/`01`, **API-only → SEM `COPY templates`**):

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

- `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py` (idêntico aos irmãos). **Sem `init_db()`** (stateless, sem SQLite).
- **O `Dockerfile` é idêntico entre os lados**, e **cada lado copia seu próprio `requirements.txt` (idênticos) e `app.py` (que difere só no modo).**

**`docker-compose.yml`** (molde EXATO do `31`/`01` — dois serviços, **sem** datastore, **sem** healthcheck/`depends_on`/rede; apps bind **só** `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8032:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8132:5000"
```

- **§8:** ambos publicam porta **só** em `127.0.0.1`. Sem datastore externo, sem rede nomeada. Stateless (nada persistido).
- **Confirmar na Fase 2** que `./atom up crypto-ecb-mode` sobe os dois e o fluxo (`/login` → `/me`) funciona de primeira.

---

## DECISÃO ABERTA pra Fase 2 — o layout do crachá (registrar, NÃO travar)

O **layout exato do plaintext do crachá** (ordem dos campos, padding, e-mails de alinhamento) depende do **TESTE**, não de preferência editorial: os campos têm que fazer `role=<valor>` e o valor `admin`/`user` caírem em **blocos de 16 bytes limpos e recortáveis**, e o splice tem que produzir `role=admin` **de fato**. É **probe de comportamento (alinhamento de bloco)**, não decisão de produto.

**Layout CANDIDATO (com o cálculo de alinhamento no papel — bloco = 16 bytes; o ataque canônico de cut-and-paste, estilo cryptopals #13):**

Plaintext do crachá: **`email=<email>&role=<role>`** (role é o **último** campo, pra o valor cair no último bloco e o `unpad` fechar após o splice).

- **Prefixos fixos:** `email=` = 6 bytes; `&role=` = 6 bytes.
- **(A) Capturar o bloco `admin`.** Escolher um e-mail que empurra `admin` + padding pro **início de um bloco**. Com `email=` (6 bytes) + **10 bytes de filler** = 16 (bloco 0 cheio), o e-mail continua com `admin` (5 bytes) + **11 bytes `0x0b`** (padding PKCS#7 válido: 11 bytes de valor `0x0b`) = bloco 1 = `admin\x0b\x0b…\x0b` (16 bytes). E-mail = `"AAAAAAAAAA" + "admin" + "\x0b"*11` (26 bytes). O crachá resultante tem, no **bloco de índice 1**, `E(admin\x0b*11)` — guardar esse bloco (`C_admin`).
- **(B) Montar o crachá vítima.** Escolher um e-mail que põe o **valor do role sozinho no último bloco**. O prefixo até o valor do role é `email=<email>&role=` = 6 + E + 6 = 12 + E; querer ≡ 0 mod 16 → **E = 4** (12+4 = 16 = bloco 0). Então: bloco 0 = `email=AAAA&role=` (16 bytes); bloco 1 = `user` + padding `0x0c`*12 (16 bytes). E-mail = `"AAAA"` (4 bytes).
- **(C) O splice.** Substituir o **bloco 1** do crachá vítima (`E(user\x0c*12)`) por `C_admin` (`E(admin\x0b*11)`). O servidor decifra → `email=AAAA&role=admin\x0b*11` → `unpad` remove os 11 bytes `0x0b` (PKCS#7 válido) → `email=AAAA&role=admin`. Parse → `role=admin`. **`GET /me` → admin.**

**Por que o padding `0x0b` importa (didática a cravar):** o bloco `admin` capturado precisa carregar **padding PKCS#7 válido** (11 bytes de `0x0b` após os 5 de `admin`), pra que, ao virar o **último** bloco do crachá forjado, o `unpad` o aceite e sobre exatamente `admin`. O atacante **pré-carrega esses bytes de padding no próprio e-mail** — é o pulo do gato do cut-and-paste.

**RESSALVAS a resolver rodando na Fase 2 (probe, não editorial):**

- **Bytes não-imprimíveis no e-mail.** O e-mail de captura carrega 11 bytes `0x0b` — em corpo JSON, expressos como `` (o parser JSON os vira em bytes reais). **Confirmar que o Burp/Repeater consegue enviá-los** e que o servidor os cifra literalmente (sem validar/normalizar o e-mail). **Se a validação de e-mail atrapalhar,** o app **não** deve validar formato de e-mail (é orthogonal à vuln; validação só complicaria o alinhamento) — cravar isso.
- **Codificação do token (liga com a Nota 3).** Se o token for **hex**, o recorte é direto (bloco = 32 hex chars) no Repeater; se **base64**, o recorte passa pelo Decoder do Burp (as fronteiras de 16 bytes não casam com as de base64). **A Fase 2 escolhe a codificação que mantém o splice Burp-only e didático, PROVANDO por execução.**
- **Ordem dos campos / comprimentos.** Se o alinhamento não fechar com este layout (ex.: o parse exige outra ordem, ou o padding do último bloco colide), **ajustar ordem de campos / comprimento do e-mail / posição do role** e **PROVAR rodando**. **VOCÊ CONFIRME/PROPONHA NA FASE 2 o layout que faz o splice produzir `role=admin` de fato; se não reproduzir, PARA e avisa — NÃO inventar** layout, bloco, ou output.
- **Determinismo a favor da reprodutibilidade.** ECB é determinístico: fixados a chave, o layout e os e-mails, o crachá e os blocos são **idênticos** a cada execução. A barra é **achar um layout+e-mails que produzam `role=admin` UMA vez (rodando) e TRAVAR**; qualquer um reexecutando reproduz. Não é "cobertura estatística", é "achar e cravar".

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes de design — exceto onde marcado "DECISÃO ABERTA".

1. **Baseline nos dois lados:** `POST /login` → crachá; `GET /me` com ele → responde **`user`** no vulnerable **E** no fixed. **VALIDAR.**
2. **O TELL (VALIDAR RODANDO):** `/login` com e-mail de **padrão repetido** → o crachá decodificado (hex) mostra **dois blocos de 16 bytes idênticos** no vulnerable. **Capturar o hex real.** (No fixed, sob GCM, os blocos **não** se repetem — capturar pra o contraste.)
3. **O ATAQUE (central — VALIDAR RODANDO):** e-mail de alinhamento → capturar o bloco `admin` cifrado → splice sobre o bloco `user` → `GET /me` responde **`role=admin`** no **vulnerable (8032)** de forma **reprodutível**. **É o item frágil (o alinhamento).** **Capturar request/response reais.** **Se não reproduzir, PARAR e avisar — NÃO inventar.**
4. **FIXED (8132):** o **mesmo** crachá recombinado → `decrypt_and_verify` **falha a tag** → token **REJEITADO** (candidato `401`/`400`) **antes** de olhar o role. **Confirmar a rejeição observável.** Capturar a resposta.
5. **Prova de isolamento:** crachá **íntegro** → `GET /me` como `user` **IDÊNTICO** nos dois lados; só o crachá **adulterado** separa (vulnerable → admin; fixed → rejeitado). A diferença traça **PURO** ao modo. **VALIDAR.**
6. **Uma vuln só:** **SEM** exposição de chave (nenhum endpoint a devolve), **SEM** endpoint de cifra genérico (Rota 2), **SEM** injection; o **único** diff funcional é o modo de cifra (`issue_badge`/`read_badge`). **Confirmar por `diff`.**
7. **§8:** bind **só** `127.0.0.1` (8032/8132); **chave/dados dummy** (chave óbvia, e-mails fake, sem PII); tudo **no Burp/local**; **nada destrutivo**, nada sai da máquina.
8. **`pycryptodome` instala/pina limpo** (mesmo pin nos dois lados): confirmar que `pycryptodome==<pin>` instala no `python:3.11-slim` (provável wheel sem toolchain — paralelo `rsa-atoms-crypto-wheel`); ECB (`encrypt`/`decrypt` + `pad`/`unpad`) e GCM (`encrypt_and_digest`/`decrypt_and_verify`, nonce/tag) **OK rodando**. Import `from Crypto.Cipher import AES`.
9. **Theory primer confirmado por FETCH:** PortSwigger primeiro (provável ausência de página conceitual de modos ECB); **fallback OWASP Cryptographic Storage Cheat Sheet** (candidato `https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html`). **Confirmar por fetch; avisar o mantenedor do desvio da fonte-padrão.** Confirmar uma fonte estável pra a ilustração do "ECB penguin". **Não inventar.**
10. **DECISÃO ABERTA — layout do crachá** (seção dedicada): o layout + e-mails que fazem o splice produzir `role=admin`. **VOCÊ CONFIRME/PROPONHA NA FASE 2** rodando; se não reproduzir, **PARAR e avisar**.
11. **Diff isola só o modo:** o **ÚNICO** delta funcional entre `vulnerable/app.py` e `fixed/app.py` é o modo de cifra; `GET /`, `/login`, `/me`, o parse, o requirements são idênticos. **Confirmar por `diff`.**
12. **Determinismo (ECB, sem nonce) e nonce (GCM) confirmados no comportamento:** ECB repete blocos (tell) e é forjável; GCM não repete e rejeita adulteração. **Capturar os dois comportamentos.**

**Bloqueante remanescente:** nenhum de decisão de vuln. **DECISÕES ABERTAS de Fase 2 (probe, não bloqueiam a spec):** o layout do crachá + e-mails de alinhamento (seção dedicada); a codificação do token (base64 vs hex, pela ergonomia Burp-only); a forma exata da auth simulada (password ortogonal); a rejeição exata do fixed (`401` vs `400`); a URL/grafia do primer por fetch (e o desvio OWASP); o pin do pycryptodome. **Protocolo:** registrar candidato, **rodar**, confirmar; se não reproduzir, ajustar dentro do escopo travado; se travar de vez, **PARAR e avisar — NÃO inventar** layout, bloco, output ou URL.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **par de contraste do `31` no eixo ARTEFATO/AÇÃO/CAUSA** — mesma A02, os dois "parecem crypto", mas o 31 usa um **hash mão-única** de senha e o atacante **RECUPERA o input** por pré-computação, enquanto o 32 usa uma **cifra reversível** num **modo** (ECB) e o atacante **FORJA** um plaintext novo **rearranjando blocos**, **sem tocar a chave**. Cada beat deve poder ser lido com o **`31` aberto ao lado**, e a diferença visível. **Abrir e fechar** na lição-coração: *modo errado (ECB — determinístico, independente, não-autenticado); o fix é um modo autenticado (GCM), não "trocar por CBC" nem "trocar a chave".*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`31` INTEIRO** (contraste central + voz mais recente — reusar a estrutura de README/WALKTHROUGH/DIFF, a honestidade "mais de uma defesa em camadas" da nota do salt como molde da nota "CBC não basta", o passo "o que a vuln NÃO é"), **`05` e `14`** (irmãos A02, forja de token via assinatura — o tema-irmão), **`01` INTEIRO** (molde canônico single-container Flask + estrutura de doc), esta spec. **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar encenação; **headers de seção traduzidos em TODA doc PT** (§7); título = classe sem stack.
- **PONTO PEDAGÓGICO OBRIGATÓRIO (a razão de o átomo existir separado do 31 e dos JWT):** o WALKTHROUGH **DEVE** (1) fazer o aluno **VER os dois blocos de ciphertext idênticos na rede** (o tell determinístico) **ANTES** do splice, e (2) mostrar que o **mesmo** crachá recombinado sob **GCM** é **REJEITADO** pelo selo (a tag). **Sem esses dois, o átomo perde a intuição central e a prova do fix.**
- **O ponto técnico frágil é o alinhamento do splice (risco #3/#10).** Fazer o cut-and-paste de verdade e confirmar que reproduz `role=admin`. **Se não reproduzir com o layout candidato, ajustar ordem de campos/padding/e-mail dentro do escopo travado e PROVAR rodando; se NADA reproduzir, PARAR e avisar — NÃO inventar** layout, bloco ou output.
- **Uma vuln só:** a **única** falha é o modo ECB. **A autz está CORRETA** (o check de role existe e funciona — contraste com IDOR/BOLA); **a chave NÃO é exposta** (nem oráculo de cifra genérico — Rota 2 rejeitada); **sem injection**; o `fixed` muda **SÓ** o modo. **SEM 2ª superfície.**
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é ir pra um modo **AUTENTICADO (GCM)**, **NÃO** só sair do ECB pra CBC (armadilha #2) nem "trocar a chave". **Ser honesto** (nota #2): CBC é uma melhora **legítima e parcial** (mata o penguin e o cut-and-paste limpo), mas deixa o token **não-autenticado**; AEAD dá **autenticação**.
- **Impacto honesto:** **forja de token → escalada de privilégio (user→admin)**; **não** inflar pra RCE nem "recuperação de chave". "Modo inseguro tem outras faces" só como **descrição da CLASSE** (uma linha), **sem** nomear átomo/variante/técnica futura — **em especial NÃO citar bit-flipping/padding oracle** (são de CBC, foreshadow de outro modo/átomo).
- **`requirements.txt` IDÊNTICOS entre os lados** (contraste com o 31): vulnerable = fixed = `Flask` + `pycryptodome`, mesmo pin. O DIFF **contrasta honestamente com o 31** (lá o fix trazia uma lib; aqui é uma linha de código). **Confirmar o pin do pycryptodome rodando.**
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** os quatro — **(a)** não é "chave fraca/vazada" (a chave nunca é tocada; prova categórica: mesma chave + GCM no fixed rejeita); **(b)** não é "AES inseguro" (AES ok; o MODO é a falha); **(c)** não é injection (é rearranjo de bytes cifrados válidos); **(d)** não é o problema do 31 (lá hash mão-única recuperado por pré-computação; aqui cifra reversível forjada por blocos).
- **Contraste com o `31` (cravar):** tabela (2 colunas: 31/32) + prosa; mesma A02, os dois "parecem crypto"; difere ARTEFATO/AÇÃO/CAUSA/TÉCNICA. **Paralelo com 05/14** (forja de token via assinatura vs via modo de cifra). Citar `31`/`05`/`14`/`01` (publicados) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** cifra de bloco, bloco de 16 bytes, modo de operação, ECB, determinismo bloco-a-bloco, cut-and-paste/block-splicing, PKCS#7 padding, modo autenticado/AEAD, GCM, nonce, tag de autenticação.
- **A02 sem arqueologia:** situar em **A02 — Cryptographic Failures**, explicar **por que** (modo de operação inadequado pro segredo em trânsito), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 candidato `crypto-ecb-mode — Encryption with an insecure mode of operation`. "AES"/"ECB"/"Python" no corpo, não no H1 (ECB é nível de motor, como MD5 no 31; o slug já qualifica). Grafia final casa com o primer.
- **Política de referência cross-átomo:** OK citar **31** (contraste central), **05/14** (irmãos A02, forja de token), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria/técnica futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase, "outras faces do modo inseguro" como átomo futuro, e **especialmente bit-flipping/padding oracle** (técnicas de CBC → apontam pra um eventual átomo de CBC). **Manter as proibições genéricas.** **Esta spec é pública — nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`crypto-ecb-mode — Encryption with an insecure mode of operation`, grafia exata confirmável na Fase 2 contra o primer). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (block cipher, mode of operation, ECB, block, cut-and-paste, block-splicing, padding, PKCS#7, AEAD, GCM, nonce, authentication tag, token, forge, payload) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): PortSwigger primeiro; **provável fallback OWASP Cryptographic Storage Cheat Sheet** — **avisar o mantenedor do desvio da fonte-padrão** (molde do 31); nome da página em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar. Referenciar uma fonte estável pra a ilustração do "ECB penguin".
- **A trilha é Burp-only:** ler o crachá, decodificar/recortar/recombinar blocos e reenviar — **tudo no Burp** (Repeater + Decoder). **SEM** cracker offline (não se quebra chave), **SEM** browser (a prova é a resposta HTTP). A ergonomia base64-vs-hex do recorte é Decisão Aberta (Fase 2 escolhe rodando).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, no padrão das linhas anteriores (candidato — ajustar na Fase 2): `` Added atom 32: `crypto-ecb-mode` — Encryption with an insecure mode of operation: a login app hands out a session badge that carries `role=user` encrypted with AES-ECB, a deterministic mode that encrypts each 16-byte block independently, so identical plaintext blocks leak as identical ciphertext blocks and blocks can be cut and pasted between badges — the attacker aligns `admin` into its own block via a chosen email, lifts that ciphertext block from the login response, splices it over the `user` block, and GET /me treats the forged badge as admin without ever breaking the key; the fix swaps the mode for authenticated AES-GCM, whose per-message tag makes the tampered badge fail verification and be rejected before the role is read (A02 Cryptographic Failures, CWE-327 candidate — confirm). `` **Confirmar o CWE por fetch na Fase 2** (candidato CWE-327 "Use of a Broken or Risky Cryptographic Algorithm"; não inventar). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 32 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline (`/login`→`/me` user nos dois lados) → o tell (blocos repetidos) → o ataque real (capturar bloco `admin` → splice → `GET /me` admin no vulnerable) → o que a vuln NÃO é → fixed (GCM rejeita o crachá adulterado). Portas host podem não ser alcançáveis do sandbox — ver a memória `validating-atoms-via-docker-exec` (fallback: `docker exec` + dirigir o app de dentro do container com `python http.client`). **Sem** browser (a prova é a resposta HTTP). O splice em si é aritmética de blocos + reenvio — factível de dentro do container/sandbox pra validação, mesmo que o WALKTHROUGH do aluno mostre no Burp.
- **Commits sem trailer `Co-Authored-By`** (memória `commit-no-coauthor-trailer` — a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8032` (vulnerable), `127.0.0.1:8132` (fixed). Bind **só** `127.0.0.1`. Single-container por lado (2 serviços, sem datastore, stateless).
- Se houver dúvida sobre o layout do crachá, o comportamento do `pycryptodome` (ECB/GCM/pad), a codificação do token, a forma da auth simulada, a URL/grafia do primer (e o desvio OWASP), o CWE, ou se o splice não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**). **Candidato, se você quiser um pointer de recall reusável** — o mais provável de servir a futuros átomos de cifra simétrica é a **receita do pycryptodome pra ECB/GCM** e a **feição do ataque de cut-and-paste**, mas boa parte disso fica **registrada nesta spec commitada** (a regra desaconselha duplicar o que o repo grava). O que **justificaria** uma memória é a parte **não-repo, de ambiente/ferramenta**:

- **`pycryptodome-aes-modes-wheel`** (candidato) — *"pycryptodome (`from Crypto.Cipher import AES`; `pip install pycryptodome`) instala como wheel no `python:3.11-slim` sem toolchain (paralelo a [[rsa-atoms-crypto-wheel]]). ECB: `AES.new(key, AES.MODE_ECB)` + `pad`/`unpad` de `Crypto.Util.Padding` (PKCS#7, `AES.block_size`=16). GCM: `AES.new(key, AES.MODE_GCM)` → `encrypt_and_digest` (nonce em `.nonce`, default 16B; tag 16B) / `decrypt_and_verify(ct, tag)` levanta `ValueError` se a tag não bate. Usado no átomo `crypto-ecb-mode` (32)."* — tipo `reference`.

**Ressalva:** só vale gravar se você quiser esse pointer pra futuros átomos de cripto simétrica; senão, já está aqui na spec. Sua decisão. *(Ortogonal: a memória relevante na Fase 2 é `validating-atoms-via-docker-exec` — dirigir o app de dentro do container se as portas host não forem alcançáveis; e `rsa-atoms-crypto-wheel` — paralelo pro pycryptodome instalar como wheel.)*
