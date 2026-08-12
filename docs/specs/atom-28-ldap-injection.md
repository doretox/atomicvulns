# Spec — Átomo 28: `ldap-injection`

> Documento de especificação para o Claude Code implementar o átomo `ldap-injection` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A03 (Injection)**: a pasta `atoms/A03-injection/` já contém `sqli-union-basic`, `sqli-blind-boolean`, `sqli-blind-time`, `xss-reflected`, `xss-stored`, `command-injection-basic`, `ssti-jinja`, `xss-dom` e `nosql-injection-mongo`. O 28 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo**.
>
> **É MULTI-CONTAINER — segue o molde de datastore-servidor do `nosql-injection-mongo` (22).** OpenLDAP é um **servidor de diretório** (não um arquivo embutido no processo, como o SQLite dos irmãos SQLi), então o compose tem **TRÊS serviços**: um `ldap` (OpenLDAP) **compartilhado** + `vulnerable` + `fixed`. O molde de topologia é o **22**: um serviço extra **construído** (imagem fina), **sem porta no host**, alcançável **por nome** na rede interna do compose, com **`healthcheck` + `depends_on: condition: service_healthy`** para a app só subir depois do diretório **pronto E semeado**. Ver a memória de projeto `datastore-atom-compose-pattern` (que nomeia explicitamente "future LDAP" como caso deste molde).
>
> **A lição em uma linha:** no **LDAP injection**, concatenar input não-confiável direto num **filtro de busca LDAP** (RFC 4515) deixa o atacante injetar os **metacaracteres** do filtro — `*`, `(`, `)`, `\` — e **reescrever a LÓGICA da consulta** ao diretório. Numa tela de login que monta o filtro `(&(uid={user})(userPassword={pass}))` e autentica **se a busca retorna alguém**, a injeção **neutraliza a checagem de senha** — bypass de autenticação. A raiz é **CONCATENAÇÃO SEM ESCAPE**: o valor entra como **estrutura** do filtro em vez de **dado**. O fix é **escapar os metacaracteres (RFC 4515)** antes de montar o filtro — aí `*`/`(`/`)`/`\` voltam a ser **texto literal**, e o filtro volta a ser o pretendido.
>
> **NÃO há "Saída B" aqui** (como no `19 ssti-jinja`, `20 deserialization-pickle`, `22 nosql-injection-mongo`). O `ldap3` **não auto-escapa** valores interpolados numa string de filtro: a API idiomática de busca recebe um **filtro como STRING**, e é responsabilidade de quem chama escapar. Então o código ingênuo (f-string com o input cru dentro do filtro) é **diretamente** o bug — não existe uma ferramenta padrão que "resista" e obrigue a modelar um componente especial. O átomo é **uso-direto-do-antipadrão**. **NÃO inventar uma Saída B.** (Confirmar por probe o comportamento do `ldap3` na Fase 2 antes de escrever — risco #7.)
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha primária Burp; **AQUI é API-only e SEM exceção de browser**: o vetor é editar o corpo JSON no Repeater e ver o login passar, **não** há execução no browser; §3.4 — datastore; §4 — pasta/categoria; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A03 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`** nos apps, o **OpenLDAP SEM porta no host**, dados fake, payload benigno; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`nosql-injection-mongo` (22) INTEIRO** (o **IRMÃO conceitual e o MOLDE de topologia**), o **`sqli-union-basic` (01) INTEIRO** (molde canônico de injection + estrutura de doc + o mental model "input reescreve a estrutura da query", que o 28 espelha noutro motor) e o **`command-injection-basic` (09)** (voz/estrutura de um injection de outro sink; citável, não central).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, `ldap/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `.ldif`, `requirements.txt` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A03 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver a política de foreshadow). Justificativa do ROADMAP para este átomo: *"rara em apps modernas mas aparece em corp/AD, vale saber."*
>
> **A categoria A03 JÁ EXISTE — o 28 reaproveita a pasta.** Diferente do `15 session-fixation` (criou `A07-*`), do `18 xxe-basic` (criou `A05-*`) e do `20 deserialization-pickle` (criou `A08-*`), o 28 **não cria categoria**: `atoms/A03-injection/` já existe e já hospeda os SQLi (×3), os XSS (×3), command injection, SSTI e o NoSQLi. **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A03-injection/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A03-injection/ldap-injection/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A03 — Injection"**.
>
> **Rótulo A03 SEM arqueologia (`CLAUDE.md` §5, regra atual).** LDAP injection é **A03 — Injection** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria do SQLi e do NoSQLi. **NÃO** relatar em que número injection caía em edições antigas — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A03 — Injection.** Explicar **por que** LDAP injection é injection (dado não-confiável cai num interpretador — o motor de avaliação de filtro do diretório — que o trata como **estrutura/sintaxe** do filtro, não como dado inerte) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar a versão, **NÃO** taggear, **NÃO** anunciar posição/ordinal de fase. **CRÍTICO (FORESHADOW, §5):** o átomo se descreve **isolado**. **NÃO** anunciar versão/release, **NÃO** situar o átomo numa fase (abrir/fechar/ordinal) nem narrar a sequência de átomos/stacks ao redor, **NÃO** foreshadowar átomos futuros (a posição vive só no `ROADMAP.md`). Esta spec é commitada no repo público, então **a própria spec nasce limpa**: onde precisar situar posição, aponta para o `ROADMAP.md`; nas frases que proíbem foreshadow, mantém a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).

## Nota de planning 3 — convenções ATUAIS: API-only, **Burp-only, SEM exceção de browser**

> Seguir o `CLAUDE.md` **atual**. Divergências concretas a fixar:
>
> - **API-only (`CLAUDE.md` §3.3).** O vetor é o **corpo JSON** de `POST /login` — o payload são strings com **metacaracteres de filtro LDAP**. **Sem `templates/`, sem `render_template`, sem browser.** Respostas em `application/json` via `jsonify`. Molde direto do **`nosql-injection-mongo` (22)** (átomo API-only com datastore: banner num `GET /` JSON, corpo JSON no `POST /login`, trilha 100% Burp Repeater). `CLAUDE.md` §3.3 lista JWT/BOLA/mass-assignment/NoSQL como "naturalmente API-only"; **login-contra-diretório é a mesma família** (cenário corp/AD, sem UI própria) — decisão API-only por categoria.
> - **Burp-only — SEM trilha browser, e SEM a exceção client-side do `xss-dom` (21).** No 21 a prova exigia **JavaScript executando no browser**, então o browser entrava na trilha principal. **Aqui NÃO há execução client-side**: o payload é montado no **corpo JSON** no Repeater, e a prova é a **resposta do login** (`authenticated: true` sem a senha certa). A trilha é **100% Burp (Repeater)**, com `curl` como equivalente. **NÃO usar a exceção de browser; NÃO criar trilha browser.**
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (login que busca no diretório) e a falha (o input vira estrutura do filtro). **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** LDAP injection, diretório LDAP, DN (Distinguished Name), atributos (`uid`/`cn`/`ou`/`dc`/`userPassword`), filtro de busca LDAP (RFC 4515), notação de prefixo, `&`/`|`/`!`, metacaractere, curinga (`*`), bind — dar a expansão/definição na estreia. O átomo é pra quem pode ter **ZERO** background em LDAP.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** ("LDAP injection"), **NÃO** o motor ("...em OpenLDAP"/"...em Active Directory"/"...com ldap3"). O **slug** (`ldap-injection`) já é a classe; nenhum qualificador de stack no H1. O motor (OpenLDAP/`ldap3`/RFC 4515) aparece no **corpo**, não no H1.
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem TODOS os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Baseline — o login funcionando`). A única exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A03 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — topologia multi-container e o SEED do OpenLDAP (molde do 22)

> **Datastore-servidor, molde do `nosql-injection-mongo` (22).** OpenLDAP é um **serviço à parte** (não um arquivo embutido como o SQLite). Este compose é multi-serviço com um **diretório compartilhado**, exatamente como o 22 fez com o `mongo`. O serviço extra (`ldap`) é **`build:`-ado** (imagem fina), **sem `ports:`** (só rede interna), alcançável **por nome** pelos apps (`ldap://ldap:389`), e **compartilhado** por `vulnerable` e `fixed` (parte da lição: **mesmo diretório, mesmos dados; só o tratamento de input difere** — ambos só **buscam**/`search`, nada escreve/modifica o diretório, então compartilhar é seguro, §8).
>
> **§8 — o OpenLDAP NÃO tem porta no host.** Só `vulnerable` (`127.0.0.1:8028`) e `fixed` (`127.0.0.1:8128`) publicam porta, **só** em `127.0.0.1`. O `ldap` fica **exclusivamente** na rede interna do compose (`ldap://ldap:389`), inacessível do host. Isso **evita** um daemon de diretório aberto na máquina do aluno.
>
> **SEED via LDIF em imagem `build:`-ada — molde do 22 (via A, à prova de SELinux).** O seed do diretório é um arquivo **LDIF** (LDAP Data Interchange Format — o formato-texto para descrever entradas do diretório) **`COPY`-ado** para dentro da imagem `ldap`, exatamente como o 22 fez o `COPY mongo-init.js /docker-entrypoint-initdb.d/`. **NUNCA bind mount** — a validação roda em **Fedora com SELinux**, que **bloqueia bind mounts** para dentro de containers (memória `datastore-atom-compose-pattern` / `jwt-hmac-crack-needs-jumbo-john`: *"Fedora SELinux blocks bind mounts, even `:z`"*). O `ldap/Dockerfile` é `FROM <imagem-openldap-pinada>` + `COPY seed.ldif <dir-de-bootstrap>`. **O diretório de bootstrap e o mecanismo exato dependem da imagem OpenLDAP escolhida — DECISÃO ABERTA / CONFIRME NA FASE 2** (ver "Biblioteca / topologia" e risco #1).
>
> **HEALTHCHECK tem que garantir DADOS SEMEADOS, não só a porta 389 aberta (ponto crítico).** O molde do 22 é `healthcheck` no datastore + `depends_on: condition: service_healthy` nos apps, **não** retry no nível da app (memória `datastore-atom-compose-pattern`). **MAS o healthcheck precisa confirmar que o diretório está no ar E COM O LDIF CARREGADO** — uma **query real que retorna uma entrada conhecida** (ex.: `ldapsearch` por `(uid=admin)` de dentro do container), **não** só um "a porta 389 respondeu". Razão: OpenLDAP aceita conexão TCP antes de terminar de importar o LDIF; se o healthcheck passar cedo demais, a app conecta antes do seed e o **baseline falha intermitente**. Candidato de comando e base DN em "Biblioteca / topologia"; **confirmar na Fase 2** (risco #1). Sem volume persistente: o seed re-roda a cada `up` limpo (dados efêmeros de lab).

---

## Identidade

- **ID:** `ldap-injection`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A03 — Injection**. Pasta `atoms/A03-injection/` (**JÁ EXISTE — o 28 reaproveita**). Confirmado contra o `ROADMAP.md` ("A03 Injection") e o `CLAUDE.md` §4. Em prosa, usar o nome da classe — **"LDAP injection"** — e a categoria — **"A03 — Injection"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A03-injection/ldap-injection/`
- **Número sequencial:** 28
- **Porta vulnerable:** `127.0.0.1:8028`
- **Porta fixed:** `127.0.0.1:8128`
- **Serviço `ldap` (OpenLDAP):** **SEM porta no host** — só rede interna do compose, alcançável por `ldap://ldap:389`.
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers dos apps rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos. O `ldap` **não** publica porta.
- **Topologia:** **MULTI-CONTAINER — TRÊS serviços:** `ldap` (OpenLDAP, compartilhado, sem porta no host) + `vulnerable` + `fixed`. Molde de rede/seed/readiness do `nosql-injection-mongo` (22) — serviço extra `build:`-ado, sem `ports:`, por nome na rede interna, `healthcheck` + `depends_on: condition: service_healthy`. **Ambos os apps leem o MESMO `ldap` semeado.**
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública), ZERO menção de posição/ordinal de fase/release/próximos átomos** (§5 foreshadow).
- **Branch de trabalho:** `atom/ldap-injection`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de LDAP injection** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/ldap-injection`** (título/grafia esperados: **"LDAP injection"**). **NÃO inventar URL — confirmar por fetch na Fase 2**; **se não houver página conceitual "what is X" limpa na Academy**, cair no **OWASP "LDAP Injection Prevention Cheat Sheet"** como primer e **avisar o mantenedor** (desvio consciente do padrão PortSwigger — registrar a razão). Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# ldap-injection — LDAP injection`** — `id` + nome canônico da **classe** em inglês. **SEM** "OpenLDAP"/"Active Directory"/"ldap3" no H1. Grafia canônica exata (maiúscula/minúscula de "injection") **confirmável na Fase 2** casando com o título da página PortSwigger; **preservar o nome em inglês também no README PT**. *(Nota: o `22` fechou em "NoSQL Injection" com I maiúsculo; o candidato aqui segue o brief — "LDAP injection" — e a grafia final casa com o primer.)*

---

## Classe de vulnerabilidade

**LDAP injection — concatenar input não-confiável num filtro de busca LDAP deixa o input virar SINTAXE do filtro.** Um endpoint de login recebe `username`/`password` e monta um **filtro de busca LDAP** — a string que descreve *quais* entradas do diretório casar. LDAP (Lightweight Directory Access Protocol) organiza identidade numa **base hierárquica** (o "diretório", tipo OpenLDAP ou Active Directory, comum em ambiente corporativo). Um filtro LDAP segue a **RFC 4515** e usa **notação de prefixo**: `(&(A)(B))` é "A **E** B", `(|(A)(B))` é "A **OU** B", `(!(A))` é "**NÃO** A", e `*` é um **curinga**. A app monta, por concatenação de string, `(&(uid={user})(userPassword={pass}))` — "casa a entrada cujo `uid` é _user_ **E** cujo `userPassword` é _pass_" — e autentica **se a busca retorna ≥1 entrada**. Como o `user` entra **cru** na string do filtro, o atacante manda **metacaracteres** de filtro (`*`, `(`, `)`, `\`) que **fecham, reabrem e reordenam** os parênteses do filtro — reescrevendo a lógica de modo que ela case **qualquer** `uid` e **descarte** a condição de senha. O input não foi tratado como **valor** (um `uid` a procurar): virou **estrutura** (parênteses e operadores do filtro).

### A lição-coração

> **"Concatenar input não-confiável direto num filtro de busca LDAP deixa o atacante injetar os metacaracteres do filtro (`*`, `(`, `)`, `\`) e reescrever a LÓGICA da consulta ao diretório. Numa tela de login que monta `(&(uid={user})(userPassword={pass}))` e autentica se a busca retorna alguém, a injeção neutraliza a checagem de senha — bypass de autenticação. A raiz é CONCATENAR sem escapar: o valor entra como estrutura do filtro, não como dado. O fix é escapar os metacaracteres (RFC 4515) antes de montar o filtro — aí `*`/`(`/`)`/`\` voltam a ser texto literal, e o filtro volta a ser o pretendido."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH)

- **Notação de prefixo.** O operador vem **antes** dos operandos, cada um entre parênteses: `(&(uid=jdoe)(userPassword=x))` = `AND(uid=jdoe, userPassword=x)`. `&` = AND, `|` = OR, `!` = NOT. Um filtro válido tem **exatamente um** filtro no topo (top-level), com os parênteses balanceados.
- **`*` é curinga.** `(uid=*)` casa **qualquer** entrada que **tenha** um `uid` (presença); `(uid=adm*)` casa `uid` começando com "adm". Um `*` sozinho no lugar de um valor transforma uma igualdade numa correspondência ampla.
- **Como o payload reposiciona os parênteses.** O `user` cru entra no meio de `(&(uid=`_user_`)(userPassword=`_pass_`))`. Mandando metacaracteres no `user`, o atacante **fecha** o `(uid=` cedo, injeta **componentes irmãos** (ex.: `(uid=*)` — casa qualquer uid) e um operador **OR** que torna a condição de senha **irrelevante** (basta um dos ramos do OR ser verdadeiro), e ajusta os parênteses pra o filtro continuar sendo **um** filtro top-level bem-formado. Resultado: o filtro casa a entrada-alvo (ou qualquer entrada) **sem** depender do `userPassword` correto.
- **A lógica frágil "busca retornou ⇒ logado" é o que quebra.** A app decide o login pela **contagem de resultados** da busca. Se a injeção faz a busca **retornar** algo, a app loga — **sem** nunca ter validado a senha de verdade. (Essa lógica é parte do desenho vulnerável — ver a nota de DIFF sobre BIND.)

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e da nota #2 do DIFF)

**A diferença NÃO é "validar/limitar o username" — é ESCAPAR os metacaracteres do filtro.** Este é o mal-entendido que o átomo desarma. O instinto do aluno experiente vai ser *"é só proibir `*` e parênteses no campo `user`"* — uma **allowlist/blocklist de charset**. Isso é **remendo frágil**: bloquear caractere é jogo de gato-e-rato (encodings, caracteres não-listados, campos que legitimamente precisam de símbolos). O **fix de causa** é **escapar** os metacaracteres **no ponto de uso** (RFC 4515, via `escape_filter_chars`): aí `*`/`(`/`)`/`\` viram **dado literal** dentro do filtro — o input volta a ser **valor**, não **estrutura**, e **não importa** que caractere ele contém, porque nenhum metacaractere é mais interpretado como sintaxe. Escapar fecha na raiz; validar charset persegue o sintoma.

### Por que A03 (Injection)

LDAP injection é **A03 — Injection**, a mesma categoria do SQLi e do NoSQLi. O eixo de injection é: **dado não-confiável cai num interpretador que o trata como código/estrutura, não como dado inerte.** No SQLi o "interpretador" é o **parser de SQL**, e o dado vira **sintaxe** de comando. No LDAP injection o "interpretador" é o **motor de avaliação de filtro** do diretório, e o dado vira **sintaxe de filtro** — parênteses, operadores (`&`/`|`), curingas (`*`). Mesma família (input não-confiável → interpretador que o executa como estrutura), **mesmo teto de impacto** neste átomo (subverter a consulta → bypass de autenticação). Situar em **A03 — Injection**, **sem** contar edições antigas.

---

## Contraste com o `nosql-injection-mongo` (22) — CENTRAL (é o eixo que justifica o átomo) — e com o SQLi (01)

O **22** é o **irmão conceitual** e o contraste que importa: os dois são **A03 — Injection** onde **input não-confiável muda a ESTRUTURA de uma query-language que NÃO é SQL**, por passagem/concatenação **sem tratamento**, e os dois têm o **mesmo teto** (bypass de autenticação). O que **DIFERE** — e o que faz o 28 não ser "o 22 de novo" — é o **motor e a linguagem** e, por consequência, **onde mora o fix**. Cravar no WALKTHROUGH e no DIFF (tabela + prosa). A tabela inclui o **SQLi (01)** como o terceiro ponto de referência da mesma família (o mental model "input reescreve a query" nasce lá):

| Eixo | SQL injection (`01`) | NoSQL injection / Mongo (`22`) | LDAP injection (`28`) |
|---|---|---|---|
| **Categoria OWASP** | A03 — Injection | A03 — Injection | A03 — Injection |
| **Query-language** | SQL (string de comando) | query do MongoDB (documento JSON) | filtro de busca LDAP, RFC 4515 (string, notação de prefixo) |
| **Como o input vira estrutura** | **SINTAXE** injetada numa **STRING** (quebra de aspas, `UNION`, `OR 1=1`) | **TIPO** muda: escalar (string) → **objeto** com um operador (`$ne`) | **METACARACTERES** numa **STRING de filtro** concatenada: `*` `(` `)` `\` |
| **Teto de impacto (neste átomo)** | subversão da query (exfil / bypass de auth) | **bypass de auth** | **bypass de auth** |
| **O fix** | query **PARAMETRIZADA** (bind vars separam comando de dado) | **FORÇAR O TIPO** (rejeitar não-string) | **ESCAPAR os metacaracteres** do filtro (RFC 4515) → viram dado literal |
| **A defesa-armadilha (mencionável, não aplicada)** | — | *"é só parametrizar/escapar"* — **não mapeia** (o `pymongo` já é "parametrizado") | *"é só validar/allowlist o charset do `user`"* — **remendo frágil**; escapar no ponto de uso é o fix de causa |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante — e a inversão que o aluno ganha lendo 22 e 28 lado a lado):** no **22**, escapar/parametrizar **NÃO era o fix** — a injeção era por **mudança de tipo** (escalar → objeto), sem string pra escapar, e o fix era **forçar o tipo**. Aqui, no **28**, escapar **É exatamente o fix** — porque a injeção **é** por **metacaracteres dentro de uma string de filtro concatenada** (channel de string-syntax, como o SQLi). Ou seja: *"injection numa query-language que não é SQL"* é **uma classe**, mas **COMO o input vira estrutura** decide o fix — por **tipo** (22 → forçar o tipo; escapar falha) ou por **metacaractere numa string** (28 → escapar; validar charset é a armadilha). A defesa que **errava** o alvo no 22 é a que **acerta** no 28. Citar `22` e `01` (publicados) à vontade — o aluno abre os dois e compara.

**Relação com o SQLi (01):** o 28 fica **mais perto do SQLi** que o 22 no *channel* (os dois injetam **sintaxe numa string** — o filtro LDAP é montado por concatenação, como o SQL vulnerable do 01). A diferença fina 01→28: o fix do SQLi é **parametrizar** (bind vars — a API do `sqlite3` tem placeholders `?`); o fix idiomático do LDAP injection, com a API de busca por **string de filtro** do `ldap3`, é **escapar** os metacaracteres (RFC 4515) — não há um "bind var" universal pro filtro. Mesmo mental model (input reescreve a estrutura da query), motor e correção pontual distintos.

**"Um átomo = uma vuln" se refere à CAUSA, não ao teto de impacto** (`CLAUDE.md` §2). O `28` é a **mesma família de injection por teto (bypass de auth), mas de motor/linguagem/fix distintos** do `22` e do `01`. O objeto de estudo é **o filtro LDAP e o escape RFC 4515**.

---

## Flavor — login corporativo contra um diretório LDAP (`POST /login`) — TRAVADO

Um endpoint de **login corporativo** que autentica **contra um diretório LDAP** (cenário corp/AD). `POST /login` recebe o corpo em **JSON** — `{"user": "...", "password": "..."}` —, a app **conecta ao OpenLDAP**, monta o filtro `(&(uid={user})(userPassword={pass}))`, faz um **search** na subárvore de usuários, e **autentica SE a busca retorna ≥1 entrada** (a lógica frágil "voltou algo ⇒ logado", **TRAVADA como parte da vuln no `vulnerable`**). **Superfície = o corpo JSON de `POST /login`** (campos `user`/`password`). Uma única rota injetável; **sem** segundo endpoint, **sem** segunda superfície.

- **API-only, sem HTML, sem templates.** Respostas JSON: `{"authenticated": true, "uid": "..."}` / `{"authenticated": false}`. Login-contra-diretório é cenário corp sem UI própria — a decisão API-only é por categoria (§3.3), no molde do `22`.
- **Por que JSON e não form:** consistência com o molde API-only do `22` e simplicidade (um corpo JSON no Repeater). Diferente do `22`, aqui o payload são **strings** (com metacaracteres) — um `<form>` *poderia* carregar as mesmas strings; a escolha por JSON é de **forma/consistência**, não uma exigência técnica como era no `22` (lá o objeto aninhado só existia em JSON). **Registrar essa diferença honestamente** — não copiar do `22` o argumento "form não reproduz": aqui reproduz; a escolha é estilística/consistência.
- **Diretório semeado com poucos usuários fake** (candidato: `admin`, `jdoe`) — **dados fake, SEM PII real**, senhas dummy óbvias.

---

## Payload-prova — BYPASS DE AUTENTICAÇÃO (conceito TRAVADO; string EXATA é probe de Fase 2; §8)

**A prova (TRAVADA):** um login com `user` carregando metacaracteres de filtro + **senha ERRADA** → `authenticated: true` no `vulnerable` (8028); a **MESMA** request → `authenticated: false` no `fixed` (8128). O atacante loga **sem** a senha correta.

**A STRING EXATA do payload — DECISÃO ABERTA / CONFIRME NA FASE 2 (probe; NÃO travar; registrar candidatos + "proponha o que funcionar").** A string depende de **(a)** como o OpenLDAP trata filtros malformados / múltiplos filtros top-level, **(b)** como o `ldap3` (pure-Python) faz o parse da string de filtro antes de enviar, e **(c)** o ACL/matching do `userPassword` (ver risco #8). **A Fase 2 monta, DISPARA e confirma capturando o filtro REAL que chega no servidor** (logar o filtro montado). Candidatos, em ordem de preferência:

1. **Candidato primário (injeção no `user`, forma canônica de ensino) — `user = "*)(uid=*))(|(uid=*"`, `password` = qualquer.** Com o template `(&(uid={user})(userPassword={pass}))` e `password="x"`, a concatenação crua vira:
   ```
   (&(uid=*)(uid=*))(|(uid=*)(userPassword=x))
   ```
   Mecânica: fecha o `(uid=` cedo, casa `uid=*` (qualquer uid), fecha o `&`, e reabre um `(|(uid=*)...)` que torna a senha irrelevante. **RISCO (registrado):** isso produz **DOIS filtros top-level** (`(&...)` seguido de `(|...)`). Servidores/bibliotecas variam: alguns tomam só o **primeiro** filtro e ignoram o resto (⇒ bypass); o `ldap3`, por ser um parser estrito de Python, **pode rejeitar** múltiplos filtros top-level (`LDAPInvalidFilterError`). **É o candidato do brief e a forma que a literatura ensina — testar primeiro.**
2. **Fallback bem-formado (UM filtro top-level, mais provável de agradar o parser do `ldap3`) — `password = "*"`, `user = "admin"`.** Vira:
   ```
   (&(uid=admin)(userPassword=*))
   ```
   `(userPassword=*)` é um filtro de **presença** ("a entrada TEM o atributo `userPassword`"). Como o `admin` tem senha, casa `admin` **sem** a senha correta — bypass, com **um único filtro válido**. **Depende** de o `userPassword` ser **pesquisável por presença** (ACL/matching — risco #8); é a forma mais limpa e ldap3-friendly se o ACL permitir.
3. **Fallback bem-formado, injeção no `user` (UM filtro válido) — `user = "*"`, `password = "*"`.** Vira `(&(uid=*)(userPassword=*))` — casa **qualquer** entrada com `uid` e `userPassword`; a busca retorna a **primeira** e o login passa como ela. Prova o bypass, mas loga como "o primeiro usuário", não necessariamente `admin`.

**Protocolo de probe (Fase 2):** montar, **disparar** o candidato 1; **logar o filtro real** que a app monta; se o `ldap3`/OpenLDAP reproduzir o bypass, **travar o candidato 1**. Se **rejeitar** (múltiplos filtros top-level), tentar os fallbacks bem-formados (2/3), ajustando pra **UM filtro top-level válido**. **Se NENHUM reproduzir, PARAR e avisar o mantenedor — NÃO inventar** payload nem "quase-funciona". Capturar request/response reais dos dois lados (`vulnerable` → `true`; `fixed` → `false`).

**Regras §8, a cravar no WALKTHROUGH:**

- O payload é **benigno**: subverte o **filtro de busca** (`search`) pra **provar o bypass pela resposta de login** — **NADA** destrutivo (sem modificar/deletar entradas, sem escrita no diretório). Só um `search` que casa demais.
- Dados semeados são **fake** (`admin` + um usuário comum, senhas dummy plaintext). Sem PII, sem segredo real.
- O lab é **isolado** (apps bind **só** `127.0.0.1`; o `ldap` **sem porta no host**; containers descartáveis). O WALKTHROUGH deixa **explícito** que é um lab local e o bypass é uma **prova de conceito benigna**.

---

## O código — o coração no filtro de busca do `app.py`

O fix é **server-side** (no `app.py`) — como no SQLi (01) e no NoSQLi (22). O `app.py` **DIFERE** entre os lados (o escape vive no servidor, no ponto de montar o filtro).

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma a assinatura do `ldap3` na versão pinada, e captura o comportamento por probe.** Assinatura exata do `search` (base DN, `search_scope`, `attributes`), a forma do bind de serviço, e o import de escape são itens de confirmação (riscos #7/#8/#9).

### `vulnerable/app.py` — o filtro montado por concatenação crua (candidato)

```python
import os

from flask import Flask, request, jsonify
from ldap3 import Server, Connection, ALL, SUBTREE

app = Flask(__name__)

LDAP_URL = os.environ.get("LDAP_URL", "ldap://ldap:389")
# Service bind identity: the app binds as a directory account that is allowed to
# SEARCH the userPassword attribute, then decides auth by whether the search
# matched. (See DIFF note on why a real design would BIND as the user instead.)
BIND_DN = os.environ.get("LDAP_BIND_DN", "cn=admin,dc=example,dc=com")
BIND_PW = os.environ.get("LDAP_BIND_PW", "changeme")
PEOPLE_DN = os.environ.get("LDAP_PEOPLE_DN", "ou=people,dc=example,dc=com")


@app.route("/")
def index():
    # Banner only -- the vuln lives in POST /login (see WALKTHROUGH).
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": 'POST /login with a JSON body {"user": "...", "password": "..."}. '
                "Work from Burp Repeater.",
    })


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "")
    password = body.get("password", "")
    # VULNERABLE: user/password are concatenated straight into the LDAP search
    # filter. An LDAP filter is structure (RFC 4515): the metacharacters * ( ) \
    # are syntax, not data. If `user` carries them, it rewrites the filter's logic
    # -- matching any uid and dropping the password check -- so the search returns
    # an entry and the login succeeds without the right password.
    filt = f"(&(uid={user})(userPassword={password}))"
    conn = Connection(Server(LDAP_URL, get_info=ALL), BIND_DN, BIND_PW, auto_bind=True)
    conn.search(PEOPLE_DN, filt, search_scope=SUBTREE, attributes=["uid"])
    if conn.entries:
        return jsonify({"authenticated": True, "uid": str(conn.entries[0].uid)})
    return jsonify({"authenticated": False}), 401
```

### `fixed/app.py` — MESMO código, com ESCAPE dos metacaracteres antes de montar o filtro (candidato)

```python
from ldap3.utils.conv import escape_filter_chars  # confirm exact import in Phase 2
...
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "")
    password = body.get("password", "")
    # FIXED: escape the RFC 4515 filter metacharacters in every untrusted value
    # BEFORE building the filter. * ( ) \ become literal data (\2a \28 \29 \5c),
    # so `user`/`password` are matched as VALUES, never interpreted as filter
    # structure. The filter is always the intended (&(uid=<value>)(userPassword=<value>)).
    filt = f"(&(uid={escape_filter_chars(user)})(userPassword={escape_filter_chars(password)}))"
    conn = Connection(Server(LDAP_URL, get_info=ALL), BIND_DN, BIND_PW, auto_bind=True)
    conn.search(PEOPLE_DN, filt, search_scope=SUBTREE, attributes=["uid"])
    if conn.entries:
        return jsonify({"authenticated": True, "uid": str(conn.entries[0].uid)})
    return jsonify({"authenticated": False}), 401
```

- **O diff é o `escape_filter_chars` em `user` e `password`.** Só o ponto de montar `filt` muda; o `GET /` (banner), os imports base, a conexão/bind ao `ldap`, `Dockerfile` e `requirements.txt` são **idênticos** entre os lados (a única linha nova no `fixed` é o `import` do `escape_filter_chars`). **O `app.py` DIFERE** (o fix vive no servidor, no ponto de uso).
- **Escapar `user` E `password`.** Os dois são atacante-controlados e os dois entram no filtro; escapar **ambos** é o fix honesto (defesa no ponto de uso, não só no campo "óbvio").
- **Bind de serviço + search (higiene idêntica nos dois lados).** A app conecta ao `ldap` como uma identidade de serviço (candidato: o rootdn `cn=admin,dc=example,dc=com`) que tem acesso de **search** ao `userPassword`, monta o filtro e decide o login pela contagem. Conexão/parse do JSON/helper de resposta: **idênticos** vulnerable×fixed. **A assinatura exata do `search` e a identidade de bind são probe de Fase 2** (risco #8).
- **`get_json(silent=True) or {}` + `.get(..., "")`**: parse tolerante; corpo ausente/inválido → strings vazias. Higiene, ortogonal ao bug. (Confirmar na Fase 2 que o filtro com strings vazias não casa nada / retorna `false` limpo.)

---

## O fix e o tipo de diff

**Fix:** **escapar os metacaracteres do filtro (RFC 4515)** em `user` **e** `password`, via `escape_filter_chars`, **antes** de montar o filtro. Tipo de diff: **lógica-diferente** — a chamada de escape adicionada no ponto de montar `filt` (input cru → input escapado), mais o `import`. Os metacaracteres viram texto literal; o filtro volta a ser o pretendido; o bypass falha.

Diff colável (candidato — a Fase 2 gera o real):

```diff
+from ldap3.utils.conv import escape_filter_chars
 ...
     user = body.get("user", "")
     password = body.get("password", "")
-    # VULNERABLE: user/password are concatenated straight into the LDAP search
-    # filter. The metacharacters * ( ) \ are filter SYNTAX (RFC 4515), not data,
-    # so `user` can rewrite the filter's logic and drop the password check.
-    filt = f"(&(uid={user})(userPassword={password}))"
+    # FIXED: escape the RFC 4515 metacharacters in every untrusted value BEFORE
+    # building the filter. * ( ) \ become literal data, so the values are matched
+    # as VALUES, never interpreted as filter structure.
+    filt = f"(&(uid={escape_filter_chars(user)})(userPassword={escape_filter_chars(password)}))"
```

**O CONTRASTE é o diff:** o vulnerable concatena o input cru no filtro (os metacaracteres viram sintaxe); o fixed **escapa** antes de montar (os metacaracteres viram dado). A única mudança é o escape no ponto de uso.

### Notas obrigatórias no `DIFF.md`

1. **A CAUSA é CONCATENAR NO FILTRO SEM ESCAPAR, não "o usuário mandou um caractere estranho".** Enquadrar honesto: o bug não é o atacante ter mandado `*`/`(`/`)` — é a app ter **concatenado** um valor não-confiável **como estrutura** do filtro. Escapar **neutraliza** porque `*`/`(`/`)`/`\` passam a ser **dado literal** (`\2a`/`\28`/`\29`/`\5c` na forma RFC 4515), não sintaxe — o filtro volta a ser exatamente `(&(uid=<valor>)(userPassword=<valor>))`, duas igualdades literais, sem espaço pra reestruturação. **CURTA e direta.**
2. **"VALIDAR/ALLOWLIST O CHARSET DO USERNAME" NÃO É O FIX — nota-ADVERTÊNCIA "mencionável, não aplicada"** (molde do `19 ssti-jinja` "a sandbox não é o fix" / `20 deserialization-pickle` HMAC / `22 nosql-injection-mongo` "parametrizar não é o fix"):
   - **(a) Nomear a intuição.** O aluno experiente vai pensar: *"é só proibir `*` e parênteses no campo `user`."*
   - **(b) Mostrar que é remendo frágil.** Bloquear caractere é **jogo de gato-e-rato**: encodings alternativos, metacaracteres fora da lista, campos que legitimamente contêm símbolos. Blocklist persegue a **forma** do ataque, sempre um passo atrás. O **fix de causa** é **escapar no ponto de uso** (RFC 4515): aí não importa que caractere o input contém, porque **nenhum** é interpretado como sintaxe de filtro.
   - **(c) Cravar o fix real:** escapar os metacaracteres, um passo antes de montar o filtro. **CURTA** (intuição + porquê), **NÃO** seção gigante.
   - **(d) REFORÇO HONESTO SOBRE O DESENHO (bind) — mencionável, não aplicado.** Autenticar de verdade contra LDAP **não** é "a busca retornou algo": é um **BIND** — uma tentativa de **conexão** ao diretório **com o DN daquela entrada e a senha fornecida**; se o bind tem sucesso, a senha está certa. O desenho `search`-conta-resultados (que este átomo usa) é frágil **por si só** e é o que transforma a injeção num bypass de auth. **MENCIONAR** o bind como o desenho correto; **MAS o átomo mantém o fix mínimo/isolado (escape)** pra o diff ser **só a causa da injeção** — **NÃO** reescrever a app pra bind (isso mudaria o **desenho**, não isolaria a **vuln**). Análogo à nota "hashing é ortogonal" do `22`: nomear o desenho correto, explicar por que fica fora do escopo do diff.
3. **CONTRASTE com o `22` (mesma classe/causa, motor diferente) — e a inversão do fix.** Referir a tabela da seção "Contraste". Mesma classe (A03, injection numa query-language que não é SQL; input vira estrutura), **motor/linguagem diferentes** (diretório LDAP/metacaracteres de filtro vs Mongo/operadores `$` em JSON). **Ponto afiado:** o que **não** era o fix no `22` (escapar — lá a injeção era por **tipo**) é **exatamente** o fix aqui (escapar — aqui a injeção é por **metacaractere numa string**). "Um átomo = uma vuln" = a **causa** (injeção estrutural), não o teto. **Sem foreshadow** (não nomear átomo/variante futura; outras faces do LDAP injection ficam em UMA linha de descrição da classe).

---

## Biblioteca / topologia

- **Apps (`vulnerable`/`fixed`): Flask + `ldap3`.** `requirements.txt` **idêntico** entre os dois:

```
Flask==3.0.0
ldap3==<pin a CONFIRMAR na Fase 2>
```

  - `Flask==3.0.0` casa com os irmãos. **`ldap3`**: registrar um pin de release estável (candidato a confirmar: `ldap3==2.9.1`). **NÃO é behavior-critical no sentido do `jwt-none-alg`**: a semântica de metacaractere de filtro é **RFC 4515 / comportamento do servidor**, estável — o pin é higiene. **Confirmar por probe** (Fase 2) que o pin escolhido **(a)** monta/envia o filtro como string sem auto-escapar (⇒ o antipadrão é diretamente o bug, sem Saída B — risco #7) e **(b)** expõe `escape_filter_chars` no import registrado (`from ldap3.utils.conv import escape_filter_chars` — confirmar o caminho exato na versão pinada, risco #9).
  - **Sem `requests`, sem ORM, sem 2ª dependência.** `ldap3` puro. **Dockerfile dos dois apps idêntico entre si** (`FROM python:3.11-slim`, `pip install`, `COPY app.py`, `ENV HOST=0.0.0.0`, `CMD python -u app.py`; **sem** `COPY templates` — API-only). **Confirmar por probe** que `Flask`/`ldap3` instalam em `python:3.11-slim` (`ldap3` é **puro Python** — provável wheel sem toolchain; confirmar na Fase 2, risco #10). *(Nota: `ldap3` é pure-Python e NÃO depende do OpenLDAP nativo `python-ldap`/`libldap` — por isso não precisa de toolchain de build. Registrar como razão do `ldap3` em vez de `python-ldap`.)*
- **Serviço `ldap` (OpenLDAP, compartilhado):** imagem **pinada por tag + digest** (`CLAUDE.md` §8; molde do `22` que pinou `mongo:7.0`). **SEM porta no host** (só rede interna). Alcançável pelos apps por **nome** — `LDAP_URL=ldap://ldap:389`. **A imagem e o mecanismo de seed são DECISÃO ABERTA / CONFIRME NA FASE 2 (risco #1):**
  - **Candidato primário: `osixia/openldap:<tag>@<digest>`** — imagem madura com bootstrap de LDIF: `COPY seed.ldif /container/service/slapd/assets/config/bootstrap/ldif/custom/` cria a imagem fina e semeia no primeiro init (analogia direta ao `COPY mongo-init.js` do `22`). Cria a base (`dc=example,dc=com`) e o rootdn via env (`LDAP_ORGANISATION`/`LDAP_DOMAIN`/`LDAP_ADMIN_PASSWORD`). **RISCO:** o osixia tem quirks de bootstrap (ordem do LDIF, estrutura esperada) e é menos mantido; **confirmar na Fase 2** que o LDIF carrega determinístico.
  - **Fallbacks (se o osixia não cooperar):** `bitnami/openldap` (via `LDAP_CUSTOM_LDIF_DIR`) **ou** uma imagem `build:`-ada a partir de `debian:stable-slim` + `slapd`/`ldap-utils` com o LDIF importado no entrypoint. Escolher o que der seed **determinístico** e healthcheck confiável. **Registrar o escolhido com tag+digest.**
- **Seed (`seed.ldif`):** semeia a subárvore de pessoas com um **`admin`** + um **usuário comum** (candidato: `jdoe`), **senhas PLAINTEXT** (simplificação de lab — ver "uma vuln só" e nota #2 do DIFF: password storage é ortogonal ao fix de LDAP injection). Estrutura candidata (base DN `dc=example,dc=com`; confirmar objectClasses/atributos obrigatórios na Fase 2):

```ldif
dn: ou=people,dc=example,dc=com
objectClass: organizationalUnit
ou: people

dn: uid=admin,ou=people,dc=example,dc=com
objectClass: inetOrgPerson
uid: admin
cn: Directory Admin
sn: Admin
userPassword: s3cr3t-admin-pw

dn: uid=jdoe,ou=people,dc=example,dc=com
objectClass: inetOrgPerson
uid: jdoe
cn: Jane Doe
sn: Doe
userPassword: jdoe-pw
```

  - **`userPassword` em TEXTO PURO — TRAVADO como candidato, CONFIRMAR na Fase 2 (risco #8).** O filtro ingênuo `(userPassword={pass})` só casa se o `userPassword` for **pesquisável por igualdade** pela identidade de bind da app. Duas armadilhas a confirmar: **(a)** se o OpenLDAP guardar/hashear o `userPassword`, a igualdade literal não casa → guardar **plaintext** no LDIF (aceitável em lab intencionalmente vulnerável — dado fake); **(b)** o **ACL default** do OpenLDAP frequentemente restringe `search`/`compare` no `userPassword` (`by self ... by anonymous auth by * none`) — se a identidade de bind da app **não** tiver acesso de search ao `userPassword`, **nem o baseline honesto casa**. Mitigação candidata: a app binda como o **rootdn** (`cn=admin,dc=example,dc=com`), que tem acesso pleno; **ou** relaxar o ACL no config da imagem. **Confirmar rodando** que o **login honesto casa** (`admin` + `s3cr3t-admin-pw` → `true`) **e** que o **bypass funciona**; propor o que funcionar. Higiene idêntica nos dois lados.
  - **Ambos os apps leem o MESMO `ldap` semeado** — parte da lição (mesmo diretório, mesmos dados; só o tratamento de input difere). Ambos só **buscam** (`search`); nada escreve/modifica (§8). **Confirmar na Fase 2** que os dois apps enxergam o mesmo `admin`.
  - **Dado fake óbvio** (`CLAUDE.md` §8.3): usuário/senha dummy, sem PII, sem segredo real. A senha plaintext do `admin` é **visível no seed** (o aluno pode lê-la) — o **baseline** do walkthrough a usa pra mostrar a feature funcionando; o **ataque** loga **sem** ela.
- **`healthcheck` do `ldap` (candidato — DEVE verificar DADOS, não só a porta; risco #1):** um `ldapsearch` de dentro do container por uma entrada conhecida, só passando quando o seed terminou:

```yaml
healthcheck:
  test: ["CMD-SHELL", "ldapsearch -x -H ldap://127.0.0.1:389 -b 'ou=people,dc=example,dc=com' '(uid=admin)' uid | grep -q '^uid: admin'"]
  interval: 5s
  timeout: 5s
  retries: 10
  start_period: 10s
```

  - O `ldapsearch` **anônimo** por `(uid=admin)` só precisa ler o `uid` (não o `userPassword`), então tende a funcionar mesmo com ACL restritivo no `userPassword`. **Confirmar na Fase 2** os flags exatos, se a busca anônima é permitida, e o base DN. Os apps usam `depends_on: { ldap: { condition: service_healthy } }` (molde do `22`).

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY** (o vetor é o **corpo JSON** no Repeater; `CLAUDE.md` §3.3 — login-contra-diretório é família API-only). Garantir que a **ÚNICA** vuln é o `/login` **concatenar** valores não-confiáveis no **filtro de busca LDAP**:

- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`. Sem HTML ⇒ sem autoescape/XSS acidental.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (molde do `22`): *"⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network."* + dica de trabalhar pelo Burp Repeater. **O `GET /` não é injetável** — é só o banner; a única superfície é o `POST /login`.
- **A ÚNICA vuln é o `/login`.** **SEM** segundo endpoint injetável, **SEM** segunda superfície. **SEM Saída B** (o `ldap3` não auto-escapa → o filtro por f-string com input cru é diretamente o bug; **MAS confirmar por probe** — risco #7).
- **O `fixed` muda SÓ o escape** no `/login` (o `escape_filter_chars` em `user`/`password` + o `import`). `GET /`, conexão/bind, `Dockerfile`, `requirements.txt`, o serviço `ldap` e o seed são **idênticos** entre os lados.
- **A sutileza que NÃO pode enfraquecer a lição:** o fixed **escapa** os metacaracteres do filtro (`escape_filter_chars`), **NÃO** valida/allowlista o charset (a defesa-armadilha da nota #2), **NÃO** troca o desenho pra bind (nota #2d). A conexão/bind ao LDAP, o parse, o healthcheck/seed são **higiene idêntica** nos dois lados — ortogonais à vuln.
- **`userPassword` no filtro (plaintext) é simplificação NECESSÁRIA** pro shape canônico do bypass (`userPassword` casado direto na igualdade). Registrar como **ortogonal**: password storage **não** é o fix de LDAP injection (nota #2/#2d).

---

## WALKTHROUGH — abertura seca; Burp-only (`CLAUDE.md` §3.3, SEM exceção browser)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (login que autentica contra um diretório LDAP) e a falha (o input vira estrutura do filtro). Trilha **100% Burp (Repeater)**, `curl` como equivalente; **SEM trilha browser** (a prova é a resposta do login, não execução no cliente).

**Abertura (candidato — plantar a lição, seco):**

> *A app é um login corporativo que autentica contra um diretório LDAP. Pra achar o usuário, ela monta um filtro de busca — `(&(uid={user})(userPassword={pass}))` — e considera você autenticado **se a busca retorna alguém**. O detalhe que a torna explorável: esse filtro é montado **colando o que você digitou direto na string**, e um filtro LDAP tem **metacaracteres** — `*`, `(`, `)` — que são **sintaxe**, não texto. Mandando esses caracteres no campo `user`, você **reescreve o filtro**: faz ele casar qualquer `uid` e joga fora a checagem de senha. A busca volta com uma entrada, e você loga sem nunca ter mandado a senha certa.*

Beats (molde do `22` publicado — abertura seca, seções numeradas `## 1..6`, adaptar a forma request-baseline no Repeater, sem browser):

1. **Context.** Login que autentica contra LDAP; `POST /login` monta `(&(uid=...)(userPassword=...))` e conta resultados. **Definir na estreia** (o aluno pode ter zero background): **diretório LDAP** (base hierárquica de identidade — tipo OpenLDAP/Active Directory, comum em corp), **DN** (Distinguished Name — o caminho único de uma entrada, ex.: `uid=jdoe,ou=people,dc=example,dc=com`), os **atributos** que aparecem (`uid`, `cn`, `ou`, `dc`, `userPassword`), **filtro de busca LDAP** (RFC 4515 — a string que descreve *quais* entradas casar), **notação de prefixo** (`(&(A)(B))` = "A E B"; `&`=AND, `|`=OR, `!`=NOT), **metacaractere** (`*`/`(`/`)`/`\` — sintaxe do filtro), **curinga** (`*` — casa qualquer valor). Isto é **LDAP injection**, sob **A03 — Injection**. Topologia: `ldap` compartilhado (sem porta no host) + `vulnerable` em `127.0.0.1:8028` + `fixed` em `127.0.0.1:8128`. Trilha 100% Burp/curl (API-only, sem browser).
2. **Spot the bug.** Mostrar a view vulnerable — `filt = f"(&(uid={user})(userPassword={password}))"`, com `user`/`password` vindos direto de `request.get_json()`, e o `conn.search(...)` seguido de `if conn.entries`. Pergunta de auditoria: *"esse `user` que EU controlo é **colado** na string do filtro — e se, no lugar de um uid, eu mandar parênteses e um `*`?"* → o input vira **estrutura** do filtro. Grep barato pra esta classe: input de request concatenado numa string de filtro (ex.: procurar `f"(&` / `search(` e ver se o valor veio do corpo sem escape). Foreshadow do fix: **escapar os metacaracteres** antes de montar o filtro.
3. **Exploitation (Repeater — o payload são metacaracteres no corpo JSON; a prova é a resposta do login).**
   - **Baseline (feature benigna):** `POST /login` com `{"user":"admin","password":"s3cr3t-admin-pw"}` (a senha real, semeada — visível no `seed.ldif`) → `authenticated: true`, `uid: admin`. O login funciona **com um uid e uma senha honestos**. (Mostrar também que a senha ERRADA → `false`, ancorando o baseline dos dois lados.)
   - **Montar o payload:** no campo `user`, metacaracteres que **reescrevem** o filtro (candidato de Fase 2 — a string exata é confirmada rodando; ver "Payload-prova"). Explicar o filtro **resultante** e por que ele casa sem a senha (`*` casa qualquer uid; o `|`/presença torna a condição de senha irrelevante).
   - **Disparar:** `POST /login` com o payload no `user` + **senha errada** → `authenticated: true`, logado **sem** a senha correta. Mostrar o **filtro real** que a app montou (capturado na Fase 2).
   - **§8 (cravar):** lab **isolado** (apps bind só `127.0.0.1`; `ldap` sem porta no host); o payload é **benigno** — só subverte o `search` pra provar o bypass pela resposta, **sem** escrita/modificação no diretório. Num alvo real, LDAP injection vai de bypass de auth a extração de atributos — **manter os payloads demonstrativos**.
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **(a) NÃO é bug de validação de charset.** Bloquear `*` e parênteses no `user` é **remendo** (gato-e-rato: encoding, caracteres fora da lista). O fix é **escapar** no ponto de uso — aí o metacaractere vira dado e **nenhuma** blocklist é necessária. *(Prova opcional: mostrar que uma allowlist ingênua ainda vaza por outra via; ou simplesmente cravar o argumento.)*
   - **(b) NÃO é o `22` (NoSQLi/Mongo).** Mesma **classe** (injection numa query-language que não é SQL; input vira estrutura), **motor/linguagem diferentes** (filtro LDAP/metacaracteres `* ( )` vs documento Mongo/operadores `$ne`/`$gt`). E a **inversão do fix**: no `22`, escapar **não** resolvia (a injeção era por **tipo**, e o fix era **forçar o tipo**); aqui, escapar **é** o fix (a injeção é por **metacaractere numa string** concatenada). *(Prova: o payload do `22` — um objeto JSON `{"$ne":null}` no `password` — **não** faz nada aqui; o `ldap3` recebe strings, não interpreta operadores `$`. O que explora aqui são **metacaracteres de filtro** numa string.)*
   - **(c) NÃO é RCE.** É injeção de **lógica no filtro** (bypass de auth / consulta ao diretório), **não** execução de código. **Sem overclaim.**
   - **Prova de isolamento (cravar):** um login **honesto** (`user`+senha corretos, **sem** metacaracteres) se comporta **IDÊNTICO** nos dois lados (`authenticated: true`); um login com credencial **errada** dá `false` nos dois; **só o PAYLOAD de injeção** separa o `vulnerable` (`true`) do `fixed` (`false`).
5. **Impact (honesto — sem overclaim).** **Bypass de autenticação → acesso sem credencial válida:** logar como `admin` sem a senha dá acesso ao que o `admin` acessa (no contexto da vítima). É o **mesmo teto** do bypass via SQLi/NoSQLi, por **motor distinto**. A classe LDAP injection tem **outras faces** (extração de atributos manipulando o filtro) — **descrição de UMA linha da classe**, **sem modelar nem foreshadowar**. Sem overclaim (não é RCE aqui), sem foreshadow.
6. **Why the fix works (porta 8128).** Repetir contra o `fixed/`:
   - A **MESMA** request (payload no `user` + senha errada) → **`authenticated: false`** (`401`): o `escape_filter_chars` transformou os metacaracteres em **dado literal**, o filtro voltou a ser `(&(uid=<literal>)(userPassword=<literal>))`, não casou nenhuma entrada. Sem bypass.
   - **Prova de isolamento:** o baseline honesto (`{"user":"admin","password":"s3cr3t-admin-pw"}`) → `authenticated: true` **igual** nos dois lados. A **feature é idêntica**; só o **payload de injeção** separa o vulnerable do fixed.
   - **A lição do diff:** o fix **escapa os metacaracteres** (RFC 4515). **Validar/allowlist o charset NÃO é o fix** (nota #2 — remendo frágil); o desenho correto de auth seria um **bind**, não "a busca retornou" (nota #2d — mencionado, não aplicado, pra o diff isolar só a causa da injeção); mesma classe do `22`, motor diferente, e a **inversão do fix** (nota #3).

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado; a trilha é Burp/curl). Requests/responses são placeholders da execução real capturada na Fase 2. (A senha honesta é a semeada, fixa no seed; o payload exato de injeção é travado por probe.)

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5)

Reforço do beat 4 acima, porque num vuln onde o exploit é "mandar uns caracteres" o aluno pode internalizar a forma errada:

- **(a) NÃO é bug de validação de charset** — bloquear `*` e parênteses é remendo; o fix é **escapar** os metacaracteres no ponto de uso.
- **(b) NÃO é o `22`** — mesma classe (injection numa query-language não-SQL), **motor/linguagem diferentes**; e a **inversão do fix** (escapar não resolvia o `22`, resolve aqui).
- **(c) NÃO é RCE** — é injeção de **lógica no filtro** (bypass de auth), não execução de código.
- **Prova de isolamento:** login honesto idêntico nos dois lados (`true`); credencial errada → `false` nos dois; só o **payload de injeção** separa vulnerable (`true`) de fixed (`false`).

---

## Impacto honesto

**Bypass de autenticação (login sem credencial válida).** O atacante loga sem a senha, mandando metacaracteres no `user` que reescrevem o filtro pra casar a entrada-alvo e descartar a checagem de senha; a busca retorna, e a lógica frágil "voltou algo ⇒ logado" autentica. Poder disso: **acesso não autorizado** — ao que a conta comprometida (ex.: `admin`) acessa, no contexto da vítima. É o **mesmo teto** do bypass via SQL injection / NoSQL injection, por **motor distinto** (metacaractere de filtro LDAP, não sintaxe de SQL nem operador de Mongo). **Sem overclaim:** o finding aqui é o **bypass de auth** — **NÃO** inflar pra RCE (não há execução de código), **NÃO** afirmar dump irrestrito do diretório (o átomo mantém o finding no bypass de login). A classe LDAP injection tem **outras faces** (manipular o filtro pra extrair atributos) — **UMA linha** de descrição da classe, **sem** modelar nem foreshadowar. A **prova do lab é benigna** (a resposta do login); a escalada é **descrita**, não armada (§8).

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A03 — átomo dentro de família publicada; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`nosql-injection-mongo` (22)** — o contraste **central** (seção dedicada + tabela). Mesma categoria (A03), mesmo teto (bypass de auth), **motor/linguagem e fix diferentes** (metacaractere de filtro + escapar vs operador que troca o tipo + forçar o tipo). **A inversão do fix** (escapar erra no `22`, acerta aqui) é o ponto que justifica o átomo. É também o **molde de topologia** (datastore-servidor, seed por imagem build-ada, healthcheck+service_healthy). Referência pra **trás**, permitida.
- **`sqli-union-basic` (01)** — o **mental model** "input reescreve a estrutura da query" nasce aqui; molde canônico de injection + estrutura de doc/código. O `28` fica **mais perto do `01`** no *channel* (sintaxe numa string), com fix pontual distinto (escape vs parametrização). Citável à vontade.
- **`command-injection-basic` (09)** — família "dado não-confiável cai num interpretador que o executa" (injection, A03). Citável **opcionalmente** pra ancorar que LDAP injection é injection e o eixo é input → interpretador; **não** central.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5; e esta spec é pública):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante futura** por número, nome, slug **OU** descrição — inclusive os próximos átomos (a posição vive **só** no `ROADMAP.md`), **outras faces do LDAP injection** modeladas como átomo futuro, ou a posição/ordinal/release de fase.
- **PROIBIDO anunciar posição de fase (abrir/fechar/ordinal), versão/release, ou a sequência de átomos/stacks ao redor.** O átomo — **e esta spec** — se descreve **isolado**. Nas frases que proíbem foreshadow, manter a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).
- **Que o LDAP injection tenha outras faces** (extração de atributos manipulando o filtro) é, no máximo, **descrição conceitual de UMA LINHA** ("o LDAP injection tem outras faces além do bypass de auth — o padrão é o mesmo: input não-confiável virando estrutura de filtro") — **sem** nomear átomo/variante futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 28 vai até **bypass de autenticação via metacaracteres no filtro de `uid`/`userPassword`** (o finding), provado pela resposta do login. **Uma vuln, uma causa (concatenar input não-confiável num filtro LDAP sem escapar ⇒ o input vira estrutura), um fix (escapar os metacaracteres RFC 4515, no servidor).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, cair no fallback e avisar).

- **Candidato:** **`https://portswigger.net/web-security/ldap-injection`** — a página conceitual de LDAP injection (título/grafia esperados **"LDAP injection"**). É a página de introdução da vuln, não a de labs.
- **Fallback (se a Academy não tiver página conceitual "what is X" limpa):** **OWASP "LDAP Injection Prevention Cheat Sheet"** — registrar como **desvio consciente** do padrão PortSwigger e **avisar o mantenedor** na entrega. **Não inventar** URL.
- **Texto do link:** **"LDAP injection"** — a forma apresentada pela própria PortSwigger (ou "LDAP Injection" do OWASP, se cair no fallback). Preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `sqli-union-basic`/`nosql-injection-mongo`).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A03 — Injection** (`atoms/A03-injection/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `ldap-injection` em A03; `CLAUDE.md` §4 fixa a pasta. Situar em A03 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Topologia | **MULTI-CONTAINER — 3 serviços:** `ldap` (compartilhado, sem porta no host) + vulnerable + fixed | Datastore-servidor. Molde do `nosql-injection-mongo` (22); memória `datastore-atom-compose-pattern` (nomeia "future LDAP"). |
| Datastore | **OpenLDAP** (imagem pinada tag+digest — candidato `osixia/openldap`, confirmar) | Diretório LDAP real. Sem porta no host (§8). Imagem/seed = risco #1. |
| Entrega do seed | **LDIF `COPY`-ado numa imagem `ldap` `build:`-ada** (via A do `22`) | À prova de SELinux (bind mount bloqueado no host Fedora — memória `datastore-atom-compose-pattern`). **Confirmar dir de bootstrap por imagem na Fase 2.** |
| Readiness | **`healthcheck` (query real, não só porta) + `depends_on: condition: service_healthy`** | Molde do `22`/memória. O healthcheck DEVE confirmar dados semeados (`ldapsearch` por `(uid=admin)`), senão baseline intermitente (risco #1). |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe** (como no 19/20/22) | `ldap3` não auto-escapa a string de filtro → o f-string com input cru é diretamente o bug. **NÃO inventar Saída B.** Confirmar por probe (risco #7). |
| Lição-coração | **LDAP injection: concatenar input no filtro sem escapar ⇒ metacaracteres viram estrutura; fix = escapar (RFC 4515), no servidor.** | O bug é **concatenação sem escape**; o input vira sintaxe de filtro. |
| Sub-lição crítica | **A diferença NÃO é validar/limitar o username — é ESCAPAR os metacaracteres** | Desarma o instinto "é só proibir `*` e parênteses". Blocklist de charset é remendo; escapar fecha na causa. |
| Contraste central | **`22` (NoSQLi/Mongo)** — mesma A03, mesmo teto, motor/fix DIFERENTES; **inversão do fix** (escapar erra no 22, acerta aqui) | Justifica o átomo. "Um átomo = uma vuln" = causa (injeção estrutural), não teto. |
| Contraste de apoio | **`01` (SQLi)** — mental model "input reescreve a query"; channel mais próximo (sintaxe numa string) | O fix pontual difere: parametrizar (SQL) vs escapar (LDAP). |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | Login-contra-diretório é família API-only (§3.3); molde do `22`. Corpo JSON no Repeater. |
| Trilha | **100% Burp (Repeater) / curl; SEM browser** | Prova = resposta do login (não execução client-side). **NÃO** usar a exceção de browser do 21. |
| Flavor — **TRAVADO** | **Login corporativo contra LDAP** (`POST /login`, corpo `{"user":...,"password":...}`) | Cenário corp/AD. Filtro `(&(uid={user})(userPassword={pass}))`; autentica se a busca retorna. |
| Payload-prova — **conceito TRAVADO, string = probe** | **metacaracteres no `user` + senha errada → `true`** (candidato `*)(uid=*))(|(uid=*`; fallbacks bem-formados) | Loga sem a senha. **String exata confirmada por probe (risco #7), capturando o filtro real; se nada reproduzir, PARAR e avisar.** |
| Código vulnerable | **`filt = f"(&(uid={user})(userPassword={password}))"`** (input cru) + `search` + `if conn.entries` | Metacaracteres no `user` viram estrutura → casa demais → bypass. |
| Código fixed | **`escape_filter_chars(user)` e `escape_filter_chars(password)`** antes de montar o filtro | Metacaracteres viram dado literal; o filtro volta ao pretendido. |
| `app.py` vulnerable × fixed | **DIFERE** (só o escape na montagem do filtro + o import) | O fix vive no servidor, no ponto de uso (como 01/22). |
| Fix (único eixo) | **Escapar os metacaracteres do filtro (RFC 4515) antes de montar** | Correção na raiz (concatenação sem escape). Não validar charset, não trocar pra bind. |
| Diff | **Lógica-diferente** — o `escape_filter_chars` no ponto de montar `filt` | A linha perigosa é o f-string com input cru; o fix é escapar antes dela. |
| Validar/allowlist charset | **Mencionar, NÃO aplicar** (nota #2) | Remendo frágil (encoding/caracteres fora da lista); a raiz é escapar no ponto de uso. |
| Desenho de auth por bind | **Mencionar, NÃO aplicar** (nota #2d) | Auth real = BIND (conexão com o DN+senha), não "busca retornou". Trocar mudaria o desenho, não isolaria a vuln. |
| Password storage (plaintext no LDIF) | **Simplificação de lab; ortogonal** (nota #2/#2d) | Necessária pro shape `(userPassword=<valor>)` casar. Hashing protege senha em repouso, não o filtro. **ACL/matching = risco #8.** |
| Diretório compartilhado | **Um `ldap`, lido pelos DOIS apps (só `search`, nada escreve)** | Parte da lição: mesmo diretório/dados; só o tratamento de input difere. Seguro (só leitura, §8). |
| Bibliotecas | **`Flask==3.0.0` + `ldap3==<pin a confirmar>`** | `ldap3` é **pure-Python** (sem toolchain, diferente do `python-ldap`). Não behavior-critical. Confirmar pin/instalação/escape import. |
| Banner | **Obrigatório, num `GET /` JSON de aviso** (API-only) | `CLAUDE.md` §8.2. `GET /` não injetável; única superfície é `POST /login`. |
| Impacto | **Bypass de auth.** Mesmo teto do SQLi/NoSQLi, motor distinto. | Honesto; **não** inflar pra RCE nem dump irrestrito. Sem foreshadow. |
| Theory primer | **PortSwigger "LDAP injection"** (`/web-security/ldap-injection`, confirmar por fetch; fallback OWASP Cheat Sheet + avisar) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Título (H1) | **`ldap-injection — LDAP injection`** (classe, sem stack) | `CLAUDE.md` §5. Sem "OpenLDAP"/"Active Directory"/"ldap3" no H1. Grafia final casa com o primer. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública) | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release/outras faces do LDAP injection como átomo futuro. |
| Portas | **8028 / 8128** (apps, bind só `127.0.0.1`); `ldap` **sem porta no host** | `CLAUDE.md` §8. Multi-container. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si** (molde dos irmãos, **API-only → SEM `COPY templates`**; **com `ldap3`** via `requirements.txt`):

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

`app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py` (idêntico aos irmãos).

**`ldap/Dockerfile`** (via A recomendada — Nota de planning 4; candidato, imagem/dir de bootstrap a confirmar na Fase 2 conforme a imagem escolhida):

```dockerfile
FROM osixia/openldap:<tag>@sha256:<digest>
# Bake the LDIF seed into the image so it loads on first init, with no bind mount.
# (Bind-mounting the seed is the usual approach, but SELinux on the host blocks
# bind mounts into containers, so the seed is COPYed into a thin image instead.)
COPY seed.ldif /container/service/slapd/assets/config/bootstrap/ldif/custom/
```

**`docker-compose.yml`** (candidato — 3 serviços; `ldap` **sem porta no host**; apps bind **só** `127.0.0.1`; rede interna compartilhada; healthcheck que verifica DADOS + `service_healthy` — molde do `22`; a Fase 2 gera o real):

```yaml
services:
  ldap:
    build: ./ldap
    # No ports: -- the directory is reachable only on the internal network,
    # never published to the host.
    environment:
      - LDAP_ORGANISATION=Example
      - LDAP_DOMAIN=example.com
      - LDAP_ADMIN_PASSWORD=changeme   # dummy; also the app's service-bind pw
    healthcheck:
      # Must confirm the SEED loaded, not just that port 389 is open: a real search
      # for a known entry. OpenLDAP finishes importing the LDIF before it serves
      # this, so a passing search means the directory is ready AND seeded.
      test: ["CMD-SHELL", "ldapsearch -x -H ldap://127.0.0.1:389 -b 'ou=people,dc=example,dc=com' '(uid=admin)' uid | grep -q '^uid: admin'"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
    networks:
      - lab
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8028:5000"
    environment:
      - LDAP_URL=ldap://ldap:389
      - LDAP_BIND_DN=cn=admin,dc=example,dc=com
      - LDAP_BIND_PW=changeme
      - LDAP_PEOPLE_DN=ou=people,dc=example,dc=com
    depends_on:
      ldap:
        condition: service_healthy
    networks:
      - lab
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8128:5000"
    environment:
      - LDAP_URL=ldap://ldap:389
      - LDAP_BIND_DN=cn=admin,dc=example,dc=com
      - LDAP_BIND_PW=changeme
      - LDAP_PEOPLE_DN=ou=people,dc=example,dc=com
    depends_on:
      ldap:
        condition: service_healthy
    networks:
      - lab

networks:
  lab:
```

- **§8:** só `vulnerable`/`fixed` publicam porta, **só** em `127.0.0.1`. O `ldap` **não** tem `ports:` — inacessível do host.
- **`condition: service_healthy`** garante que os apps só sobem depois do healthcheck do `ldap` passar — e o healthcheck **só passa com o seed carregado** (query real). **Confirmar na Fase 2** (risco #1) que `./atom up ldap-injection` sobe os 3 e o login honesto funciona de primeira, sem retry no app.
- **`changeme` é dummy óbvio** (`CLAUDE.md` §8.3) — a senha do rootdn/admin do diretório, usada também como bind de serviço da app. **A env var e os DNs são IDÊNTICOS nos dois apps** (higiene). Confirmar na Fase 2 os nomes exatos das env vars conforme a imagem OpenLDAP escolhida.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes de design — exceto onde marcado "DECISÃO ABERTA".

1. **Compose sobe determinístico (LDAP pronto COM dados antes da app):** `./atom up ldap-injection` sobe os **3** serviços; o **healthcheck do `ldap` confirma o SEED carregado** (não só a porta 389) via `ldapsearch` por `(uid=admin)`; os apps sobem com `condition: service_healthy` e **não** precisam de retry. **DECISÃO ABERTA:** imagem OpenLDAP (tag+digest) e o **dir de bootstrap** do seed conforme a imagem (`osixia` candidato; fallback `bitnami`/`debian+slapd`). Confirmar o LDIF carregar determinístico.
2. **Login honesto casa (baseline):** `POST /login` com `{"user":"admin","password":"s3cr3t-admin-pw"}` → `authenticated: true` / `uid: admin` nos **dois** lados.
3. **Credencial errada → `false`:** `{"user":"admin","password":"wrong"}` → `authenticated: false` (`401`) nos **dois** lados.
4. **O ATAQUE (central — VALIDAR RODANDO):** payload de metacaracteres no `user` + senha errada → `authenticated: true` no **vulnerable** (8028). **CAPTURAR o filtro REAL que a app monta** (logar) e a request/response. **Se não reproduzir, PARAR e avisar — NÃO inventar.**
5. **FIXED:** a **MESMA** request de ataque → `authenticated: false` (`401`) no **fixed** (8128); o `escape_filter_chars` transformou os metacaracteres em dado literal. **CAPTURAR.**
6. **Prova de isolamento:** login honesto (string) funciona **idêntico** nos dois lados; credencial errada → `false` nos dois; só o **payload de injeção** separa vulnerable de fixed.
7. **String exata do payload + comportamento do `ldap3` (probe):** confirmar que o `ldap3` **não auto-escapa** o filtro (⇒ sem Saída B) e travar a string que reproduz. Candidato primário `*)(uid=*))(|(uid=*` (pode falhar por múltiplos filtros top-level no parser do `ldap3`); fallbacks bem-formados (`user=admin`+`password=*` → `(userPassword=*)` presença; `user=*`+`password=*`). **Remontar como UM filtro top-level válido se o primário falhar; se nada reproduzir, PARAR e avisar.**
8. **`userPassword` casa (probe — armadilha dupla):** **(a)** guardar `userPassword` em **texto puro** no LDIF pra a igualdade `(userPassword=<valor>)` casar (dado fake, lab); **(b)** garantir que a **identidade de bind da app** (candidato: rootdn `cn=admin,dc=example,dc=com`) tem acesso de **search** ao `userPassword` — o ACL default do OpenLDAP costuma restringir (`by * none`), o que faria **até o baseline honesto** falhar. Mitigar bindando como rootdn **ou** relaxando o ACL. **Confirmar que o baseline honesto casa E o bypass funciona.**
9. **`escape_filter_chars` import/uso correto na versão pinada:** confirmar `from ldap3.utils.conv import escape_filter_chars` (ou o caminho exato do pin) e que escapar `user`/`password` **bloqueia** o payload no fixed sem quebrar o baseline honesto.
10. **Instalação em `python:3.11-slim`:** `Flask` + `ldap3` instalam como **wheel puro** (sem toolchain — `ldap3` é pure-Python, não `python-ldap`/`libldap`). Confirmar.
11. **Uma vuln só:** **só** `POST /login` é injetável; `GET /` é só o banner (não injetável); **sem** 2º endpoint; o `fixed` muda **só** o escape (+ import). Confirmar por `diff` e que o WALKTHROUGH **não** empilha outra vuln.
12. **§8 — payload benigno + isolamento:** o bypass é provado **pela resposta do login**; **NADA** destrutivo (sem modificar/deletar entradas, sem escrita no diretório); dados semeados **fake**; **`ldap` SEM porta no host**; apps bind **só** `127.0.0.1` (8028/8128); lab contido.
13. **Theory primer** confirmado **por fetch** (PortSwigger "LDAP injection", `/web-security/ldap-injection`); confirmar a **grafia exata do H1** contra a página; **fallback OWASP Cheat Sheet + avisar** se não houver página conceitual limpa. **Não inventar.**
14. **Diff é só o escape:** o **ÚNICO** delta funcional entre `vulnerable/app.py` e `fixed/app.py` é o `escape_filter_chars` na montagem do filtro (+ o `import`). `GET /`, conexão/bind, `Dockerfile`, `requirements.txt`, `ldap/` e o seed **idênticos** entre os lados. Confirmar por `diff`.

**Bloqueante remanescente:** nenhum de decisão de vuln. **DECISÕES ABERTAS de Fase 2 (probe, não bloqueiam a spec):** a imagem OpenLDAP + dir de bootstrap do seed (item 1); a string exata do payload + comportamento do `ldap3` (item 7); o storage/ACL do `userPassword` (item 8); a URL/H1 do primer por fetch (item 13). **Protocolo:** registrar candidato, **disparar**, confirmar rodando; se não reproduzir, ajustar dentro do escopo travado; se travar de vez, **PARAR e avisar — NÃO inventar**.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **irmão LDAP do `nosql-injection-mongo` (22)** e é **uso-direto-do-antipadrão** (sem Saída B). Cada beat deve poder ser lido com o **`22` aberto ao lado**, e a diferença ("mesma classe — injection numa query-language que não é SQL, input vira estrutura —, mas aqui o motor é o **filtro LDAP** e o que entra são **metacaracteres numa string**, então o fix é **escapar** (RFC 4515), **NÃO** forçar o tipo; e — a inversão — escapar **não** resolvia o `22`, mas resolve aqui") deve estar visível na linha em discussão. **Abrir e fechar** na lição-coração: *concatenar input no filtro sem escapar deixa o input virar estrutura; o fix é escapar os metacaracteres, no servidor.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`22` INTEIRO** (irmão conceitual + molde de topologia datastore/seed/healthcheck + molde API-only/Burp-only + estrutura de WALKTHROUGH/DIFF/README + a nota "mencionável não aplicada"), **`01` INTEIRO** (mental model "input reescreve a query" + molde canônico de código/estrutura/doc de injection), **`09`** (voz de um injection de outro sink; opcional). **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar do `21` a **exceção de browser / trilha browser** (aqui é Burp-only), nem encenação; **headers de seção traduzidos em TODA doc PT** (§7).
- **NÃO há Saída B (crítico):** o `ldap3` **não auto-escapa** a string de filtro — então o `filt = f"(&(uid={user})...)"` com o input cru é **diretamente** o bug. **NÃO** inventar uma ruga de "a ferramenta padrão resiste". **MAS confirmar por probe** (comportamento do `ldap3`) **antes** de escrever (risco #7).
- **A prova é a RESPOSTA do login (riscos #4/#5), no Burp/curl — NÃO no browser.** Não há execução client-side. Capturar a cadeia real: vulnerable → payload → `authenticated: true` **sem** a senha; fixed → mesma request → `authenticated: false`. **Capturar também o filtro real montado** (logar). **Se não bater rodando, PARAR e avisar — NÃO inventar** prova nem payload.
- **§8:** payload **benigno** (bypass provado pela resposta, **sem** escrita/modificação no diretório); apps bind **só** `127.0.0.1`; **`ldap` SEM porta no host**; dados semeados **fake**; lab contido. Enquadrar explicitamente no WALKTHROUGH.
- **A sutileza que NÃO pode enfraquecer a lição:** o **fixed escapa** os metacaracteres (`escape_filter_chars`), **NÃO** valida/allowlista o charset (nota #2), **NÃO** troca o desenho pra bind (nota #2d). A defesa vive **no ponto de montar o filtro**, transformando metacaractere em dado literal.
- **Uma vuln só:** foco no filtro montado por concatenação crua no `POST /login`. `GET /` é **só** o banner (não injetável). **Sem** 2ª superfície, **sem** 2º endpoint injetável. O `fixed` muda **só** o escape (+ import).
- **API-only, Burp-only:** sem `templates/`, sem `render_template`, sem browser. Respostas `jsonify`. Banner obrigatório num `GET /` JSON. Trilha 100% Burp Repeater (`curl` equivalente). **NÃO** criar trilha browser (a prova é a resposta do login).
- **Abertura seca:** WALKTHROUGH entra direto na mecânica; **sem** encenação. Rotular os beats: **context (definir LDAP/DN/atributos/filtro-RFC4515/notação-de-prefixo/metacaractere/curinga)** → **spot the bug (filtro por f-string com input cru)** → **exploitation (baseline honesto; payload de metacaracteres; resposta do login + filtro real)** → **o que a vuln NÃO é (não é validação de charset; não é o `22`; não é RCE)** → **impacto (bypass de auth)** → **fixed (mesma request → `false`; escape)**.
- **Impacto honesto:** **bypass de auth**; **não** inflar pra RCE nem dump irrestrito. Mesmo teto do SQLi/NoSQLi, motor distinto. Sem overclaim, sem foreshadow.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que a causa é **concatenar sem escapar** (input vira estrutura de filtro); **não é** bug de validação de charset (escapar é o fix, não blocklist), **não é** o `22` (mesma classe, motor diferente, **inversão do fix**), **não é** RCE (injeção de lógica no filtro, não execução).
- **Contraste com o `22` (cravar):** tabela (3 colunas: 01/22/28) + prosa; mesma A03, mesmo teto, motor/fix diferentes; **a inversão do fix** (escapar erra no `22`, acerta aqui). Citar `22`/`01`/`09` (publicados) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** LDAP injection, diretório LDAP, DN, atributos (`uid`/`cn`/`ou`/`dc`/`userPassword`), filtro de busca LDAP (RFC 4515), notação de prefixo (`&`/`|`/`!`), metacaractere, curinga (`*`), bind.
- **A03 sem arqueologia:** situar em **A03 — Injection**, explicar **por que** LDAP injection é injection (input → motor de avaliação de filtro que o trata como estrutura), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `ldap-injection — LDAP injection`. "OpenLDAP"/"Active Directory"/"ldap3"/"RFC 4515" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **22** (contraste central + molde de topologia), **01** (mental model + molde de doc/código) e **opcionalmente 09** (família injection), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase, a sequência de átomos/stacks ao redor, e outras faces do LDAP injection como átomo futuro. **Manter as proibições genéricas** (sem listar nomes de átomos não-publicados). **Esta spec é pública — a própria spec nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`ldap-injection — LDAP injection`, grafia exata confirmável na Fase 2). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (LDAP injection, DN, filter, metacharacter, wildcard, bind, escape, payload, bypass) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (LDAP injection), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar; fallback OWASP Cheat Sheet + avisar.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 28: `ldap-injection` — LDAP injection: a corporate login concatenates untrusted input straight into an LDAP search filter, so filter metacharacters (* ( )) in the `user` field rewrite the query, match any uid, and drop the password check — logging in without a valid password (A03 Injection). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 28 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–14; reproduzir baseline honesto → payload de metacaracteres → `true` no vulnerable → `false` no fixed, capturando o filtro real. Portas host podem não ser alcançáveis do sandbox — ver a memória `validating-atoms-via-docker-exec` (fallback: `docker exec` + query de dentro do container). **Sem** browser (a prova é a resposta do login).
- **Commits sem trailer `Co-Authored-By`** (memória `commit-no-coauthor-trailer` — a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8028` (vulnerable), `127.0.0.1:8128` (fixed). Bind **só** `127.0.0.1`. **`ldap` sem porta no host.** Multi-container (3 serviços).
- Se houver dúvida sobre a URL/H1 do primer, a string exata do payload, o comportamento do `ldap3`, a imagem/seed do OpenLDAP, o ACL/storage do `userPassword`, ou se o ataque não reproduzir, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF:**

- **`ldap-injection-escape-filter`** — *"O átomo `ldap-injection` (28, A03, reaproveita `atoms/A03-injection/`): LDAP injection via `filt = f\"(&(uid={user})(userPassword={password}))\"` com o input cru de `request.get_json()` num login corp contra OpenLDAP. Payload = metacaracteres de filtro no `user` (candidato `*)(uid=*))(|(uid=*`; fallback bem-formado `user=admin`+`password=*` → `(userPassword=*)` presença) + senha errada → loga sem a senha (o `*`/`(`/`)` viram estrutura do filtro). Raiz = CONCATENAR sem escapar; o input vira sintaxe de filtro (RFC 4515), NÃO 'char estranho'. Fix = `escape_filter_chars` (de `ldap3.utils.conv`) em user E password antes de montar o filtro, no servidor — NÃO validar/allowlist charset (nota-armadilha #2, remendo frágil), NÃO trocar pra bind (nota #2d: auth real seria um BIND, mas trocar mudaria o desenho, não isola a vuln). Sem Saída B (o `ldap3` não auto-escapa a string de filtro). API-only, Burp-only (prova = resposta do login, sem browser). Multi-container molde do 22: 3 serviços (ldap OpenLDAP compartilhado SEM porta no host + vulnerable 8028 + fixed 8128); seed LDIF via imagem build-ada com COPY (à prova de SELinux) — NÃO bind mount; healthcheck DEVE confirmar dados semeados (ldapsearch por uid=admin), não só a porta 389. Armadilhas de probe (Fase 2): string exata do payload (ldap3 pode rejeitar múltiplos filtros top-level); userPassword plaintext no LDIF + ACL/bind precisa de search access (bindar como rootdn). Contraste central = 22 (mesmo teto, motor/fix diferentes; a INVERSÃO: escapar erra no 22 — lá é tipo —, acerta aqui — aqui é metacaractere numa string)."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão. *(Ortogonal: as memórias relevantes na Fase 2 são `datastore-atom-compose-pattern` — que já nomeia "future LDAP" — e `validating-atoms-via-docker-exec`; a de validação client-side/DOM headless **não se aplica** — este átomo é Burp-only sem browser.)*
