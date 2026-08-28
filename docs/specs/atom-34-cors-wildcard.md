# Spec — Átomo 34: `cors-wildcard`

> Documento de especificação para o Claude Code implementar o átomo `cors-wildcard` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A05 (Security Misconfiguration)**: a pasta `atoms/A05-security-misconfiguration/` já contém `xxe-basic` (18), `xxe-blind-oob` (30) e `debug-enabled` (33). O 34 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É MULTI-CONTAINER — DUAS origens: `victim` + `attacker`** (cada origem-vítima em dois lados, `vulnerable` + `fixed`). A origem-atacante é uma **página HTML+JS** de onde o script cross-origin parte. **MOLDE do `csrf-basic` (23):** os serviços **NÃO se falam server-to-server** — quem faz TODAS as requests cross-origin é o **browser da vítima**. Logo **NÃO há rede interna (`networks:`), NÃO há `depends_on`, NÃO há healthcheck** (diverge do molde de datastore do `nosql-injection-mongo` (22), onde havia rede interna/readiness): cada serviço só publica o **próprio binding no host** e é alcançado pelo browser. O navegador é o **único "cabo"** entre as origens.
>
> **A lição em uma linha:** o navegador impõe a **Same-Origin Policy (SOP)** — um script de `evil.com` pode **DISPARAR** uma requisição a `banco.com`, mas **NÃO pode LER** a resposta (é o que impede `evil.com` de ler sua página de conta no `banco.com`). **CORS** (Cross-Origin Resource Sharing) é como o **SERVIDOR relaxa** a SOP de propósito, por **cabeçalhos de resposta**: `Access-Control-Allow-Origin` diz **qual origem** pode ler, e `Access-Control-Allow-Credentials: true` diz **"inclusive com os cookies da vítima"**. A má config: o servidor **REFLETE de volta qualquer origem que pergunta** E manda `Allow-Credentials: true` — responde "sim" pra **QUALQUER** site. Uma vítima logada no alvo que visita o site do atacante tem o navegador anexando os cookies dela na requisição, e o **script do atacante LÊ a resposta autenticada** — roubo de dados cross-origin. O fix **NÃO** é "refletir uma origem específica" (refletir **É** o bug) — é uma **ALLOWLIST de correspondência EXATA** de origens realmente confiáveis (ou **nenhum** cabeçalho CORS, se o endpoint não precisa de acesso cross-origin).
>
> **O CORAÇÃO TÉCNICO — a sutileza que o slug NÃO conta (CRÍTICO).** O slug é `cors-wildcard`, mas o **curinga literal** `Access-Control-Allow-Origin: *` **NÃO pode ser combinado** com `Access-Control-Allow-Credentials: true` — o **navegador BLOQUEIA** essa combinação (o `fetch` credenciado falha). Logo a má config perigosa pra roubar dado **AUTENTICADO** **não é** o `*` literal (que só vaza dado **PÚBLICO**, baixo impacto) — é a **REFLEXÃO DA ORIGEM**: o servidor lê o cabeçalho `Origin` do request e o devolve em `Access-Control-Allow-Origin`, junto com `Allow-Credentials: true`. O navegador **ACEITA** uma origem específica refletida com credenciais → o atacante lê dado autenticado. **O átomo CENTRA NA REFLEXÃO + CREDENCIAIS** (o caso do ROADMAP, "permitindo credenciais"); o `*` literal vira um **BEAT DE ENSINO** ("por que o `*` ingênuo nem funciona com credenciais — o navegador recusa"). Definir isso claramente no MECANISMO e no WALKTHROUGH.
>
> **§3.3 — trilha primária Burp, MAS este átomo usa a EXCEÇÃO client-side (como o `21 xss-dom` e o `23 csrf-basic`): o BROWSER está na trilha PRINCIPAL — exceção JUSTIFICADA.** A prova EXIGE o navegador: **CORS é um controle imposto pelo BROWSER**. `curl`/Burp **leem qualquer resposta ignorando os cabeçalhos CORS** — não são controle de acesso do servidor. O Burp mostra o **"tell"** (a origem refletida + `Allow-Credentials` na resposta), mas o **EXPLOIT** (o script do atacante LENDO a resposta autenticada da vítima) só reproduz num **browser real**. *(A razão da exceção difere do 33 — irmão A05, Burp-only: lá o ataque inteiro é HTTP e a prova é a resposta HTTP. Aqui a prova é o navegador OBEDECER o cabeçalho e liberar/bloquear a leitura pro script do atacante — algo que `curl`/Burp não reproduzem.)*
>
> **REQUISITO DIDÁTICO (crítico — átomo denso de vocabulário).** O WALKTHROUGH e o README **DEVEM definir DO ZERO, na 1ª ocorrência**, assumindo que o aluno **não conhece nenhum**: **Same-Origin Policy (SOP)**, **origem** (esquema + host + porta), **CORS**, **`Access-Control-Allow-Origin`**, **`Access-Control-Allow-Credentials: true`**, **requisição credenciada** (`fetch` com `credentials:'include'`), **preflight** (a requisição `OPTIONS` que o navegador faz antes de certas requisições cross-origin). Definir com clareza de iniciante — **NÃO** assumir familiaridade. Ver "O MECANISMO em detalhe" e a Nota de planning 3. *(A SOP já foi introduzida no `csrf-basic` (23) pelo lado do ENVIO; aqui o foco é o lado da LEITURA — mas define-se do zero mesmo assim.)*
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha Burp **com a EXCEÇÃO client-side** deste átomo; §4 — pasta/categoria A05 **já existe**; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo na 1ª ocorrência, situar em A05 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind loopback** e **ISOLAMENTO** dos serviços, dados fake; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referências vivas** — o **`csrf-basic` (23) INTEIRO** (o **MOLDE CENTRAL**: multi-container onde os serviços NÃO se falam, browser na trilha principal, validação headless com sessão/cookie persistente; e o **CONTRASTE** — 23 = SOP no lado do ENVIO, 34 = SOP no lado da LEITURA), o **`debug-enabled` (33)** e os **`xxe-basic` (18)/`xxe-blind-oob` (30)** (**IRMÃOS A05**: reusar o enquadramento "A05 — Security Misconfiguration"; contraste de sub-forma — parser (XXE) / framework-deploy (debug) / **política de resposta HTTP mal configurada** (CORS)), o **`xss-dom` (21)** (molde da **exceção de browser** e da **técnica de validação headless**), o **`crypto-ecb-mode` (32)** (a **VOZ/estrutura ATUAL** — abertura seca, definir termo, título=classe, headers PT traduzidos, honestidade-em-camadas nas notas-armadilha), e o **`sqli-union-basic` (01)** (molde canônico single-container Flask — a origem-vítima é um Flask nesse molde + estrutura de doc).
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, `victim/`, `attacker/`, README, WALKTHROUGH, DIFF, templates, HTML/JS, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `app.py` — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A05 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver Nota de planning 2 e a política de foreshadow). Justificativa do ROADMAP para este átomo: *"CORS mal configurado permitindo credenciais. Frequente em APIs."*
>
> **A categoria A05 JÁ EXISTE — o 34 reaproveita a pasta.** `atoms/A05-security-misconfiguration/` já existe e já hospeda `xxe-basic` (18), `xxe-blind-oob` (30) e `debug-enabled` (33). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A05-security-misconfiguration/`** (confirmado também pelo `ls` da pasta atual, que lista os dois XXE e o debug-enabled). Pasta final: **`atoms/A05-security-misconfiguration/cors-wildcard/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A05 — Security Misconfiguration"**.
>
> **Rótulo A05 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Um endpoint que responde a política de CORS relaxada (refletindo qualquer origem + credenciais) num ambiente que o atacante alcança é **A05 — Security Misconfiguration** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria dos irmãos XXE (18/30) e do `debug-enabled` (33). **NÃO** relatar em que número/categoria essa classe caía em edições antigas do OWASP Top 10 — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A05 — Security Misconfiguration.** Explicar **por que** é A05 (uma **política de resposta HTTP mal configurada** — o servidor instrui o navegador a liberar a leitura cross-origin pra qualquer origem —, não um bug de lógica de negócio; a lógica do `/account` está correta) é legítimo; contar edições **não**. *(Nota histórica: o `xxe-basic` (18) incluiu uma nota de mapeamento "XXE era A4 em 2017". O 34 **NÃO** faz isso — segue a regra ATUAL do `CLAUDE.md` §5, igual ao `debug-enabled` (33) e ao `crypto-ecb-mode` (32).)*
>
> **Enquadramento A05 entre os irmãos (contraste de sub-forma, todos publicados).** Os XXE (18/30) são misconfig de um **componente de parsing** (default perigoso do parser XML). O `debug-enabled` (33) é misconfig de **framework/deploy** (modo de desenvolvimento alcançável). O 34 é misconfig de **política de resposta HTTP** (os cabeçalhos CORS instruindo o navegador a liberar a leitura cross-origin credenciada pra qualquer origem). **Mesma categoria (A05), sub-forma diferente:** default de parser vs modo de deploy vs política de resposta. Ancorar a lição nesse contraste com os irmãos publicados é bem-vindo (`CLAUDE.md` §5); **sem** narrar posição/sequência/arco (foreshadow, Nota 2).

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4, §12). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW (lei do projeto, `CLAUDE.md` §5; e esta spec é pública/commitada → nasce limpa).** **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec**: situar o átomo por **ordinal de fase**, **milestone**, **release/versão** (`v0.x`/`v1.0` etc.), ou como **abertura/encerramento** de qualquer coisa — **inclusive** como "o átomo que fecha a A05-misconfig", "o primeiro/penúltimo/último de", ou qualquer referência a **outros A05 futuros**. Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não-publicados**, **sem postular átomo futuro**. **A posição vive SÓ no `ROADMAP.md`.** Confirmo aqui apenas o **número (34)**, o **slug (`cors-wildcard`)** e a **categoria (A05)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo. **Pode citar `01`, `18`, `21`, `23`, `30`, `31`, `32`, `33`** (publicados) à vontade (`CLAUDE.md` §5).

## Nota de planning 3 — convenções ATUAIS: EXCEÇÃO client-side (browser na trilha PRINCIPAL), abertura seca, requisito didático

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **§3.3 — EXCEÇÃO client-side: o browser é trilha PRINCIPAL (como o 21/23), o Burp APOIA.** A prova **EXIGE** o navegador porque **CORS é um controle do BROWSER**, não do servidor. O `fetch` credenciado LENDO a resposta autenticada — e o navegador ou **liberando** (vulnerable) ou **bloqueando** (fixed) essa leitura — **só acontece num browser real**. O Burp **inspeciona e prova a rede** (o "tell": a origem refletida + `Allow-Credentials: true` na resposta) e mostra que o endpoint está mal configurado — mas o ato **definidor** (o navegador obedecer o cabeçalho e expor/negar a leitura pro script cross-origin) é do **browser**. **Trilha principal única** (browser + Burp); **SEM** "trilha browser secundária" redundante (proibida pela §3.3 atual). *(Detalhe na Nota de planning 3-A.)*
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (uma API que devolve os dados privados da conta a quem tem o cookie de sessão) e a falha (a política de CORS reflete qualquer origem e permite credenciais). **NADA** de encenação ("você é o pentester" e afins).
> - **REQUISITO DIDÁTICO — definir CADA termo DO ZERO na 1ª ocorrência (`CLAUDE.md` §5 + o brief).** Este átomo é denso de vocabulário que o iniciante não tem: **Same-Origin Policy (SOP)**, **origem** (esquema + host + porta), **CORS (Cross-Origin Resource Sharing)**, **`Access-Control-Allow-Origin`**, **`Access-Control-Allow-Credentials: true`**, **requisição credenciada** (`fetch` com `credentials:'include'`), **preflight** (a requisição `OPTIONS`). Definir com a clareza de uma explicação a um iniciante — **NÃO** assumir familiaridade. Ver a lista completa e as definições candidatas em "O MECANISMO em detalhe" e nos beats do WALKTHROUGH.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** — **CORS misconfiguration** —, **NÃO** o motor ("...em Flask"/"...com flask-cors"/"...em Python"). "CORS" no H1 é o **nome da classe** (a sigla que o pentester procura) — aceitável. O **slug** (`cors-wildcard`) qualifica a variante. O mecanismo (reflexão da origem / `Allow-Credentials` / after_request) aparece no **corpo**, não no H1. Candidato de H1 em "Identidade".
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Ver a origem refletida`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A05 sem arqueologia** (Nota de planning 1).

## Nota de planning 3-A — o papel do Burp aqui: o Burp mostra o TELL, mas curl/Burp NÃO provam o impacto (CORS é controle do browser)

> **Sinalizado — sutileza importante pra Fase 2, e é a própria lição.** Nos átomos server-side (SQLi, NoSQLi, SSTI, e o irmão `debug-enabled` (33)) a trilha é Burp porque o vetor **e a prova** vivem na request/resposta que **você** monta. **No CORS isso NÃO se aplica pra prova, e a razão É a lição:** os cabeçalhos CORS **não são um controle do servidor** — o servidor **entrega a resposta pra quem pedir, sempre**; os cabeçalhos são uma **instrução ao NAVEGADOR** sobre se ele pode **entregar a resposta ao script** que fez a chamada. Um `curl`/Repeater a `GET /account` (com o cookie colado à mão, ou até sem cookie) **lê o corpo inteiro** — porque `curl` não é um navegador e **ignora** os cabeçalhos CORS. Isso **NÃO é o exploit**: não houve vítima, não houve script cross-origin sendo liberado/bloqueado.
>
> Logo o papel do Burp aqui é de **APOIO dentro da trilha principal**:
>
> 1. **MOSTRAR O TELL:** mandar `GET /account` (no `vulnerable`) com um cabeçalho `Origin: http://<origem-atacante>` e mostrar, na **RESPOSTA**, que o servidor devolve `Access-Control-Allow-Origin: http://<origem-atacante>` (a **mesma** origem refletida) + `Access-Control-Allow-Credentials: true`. Esse é o **sinal da má config** — o servidor topa qualquer origem. Contraste no fixed: a resposta **NÃO reflete** a origem do atacante.
> 2. **EXPLICAR por que o tell sozinho não é a prova:** `curl`/Burp leem o corpo de qualquer jeito (CORS não é controle do servidor). A **prova do impacto** — o script do atacante conseguindo LER a resposta autenticada da vítima — exige o **navegador**, que é quem **obedece** o cabeçalho.
>
> Quem **planta e manipula** as requests (o tell, o encoding, o Repeater) é o **Burp**; quem **executa o exploit e observa a leitura** (o `fetch` credenciado lendo o dado da vítima) é o **browser**. Cravar no WALKTHROUGH que **curl não é a prova aqui** (risco #6) — é o **oposto** do irmão `debug-enabled` (33, Burp-only, onde a prova é a resposta HTTP). *(Registrar essa divergência explicitamente — Burp mostra o tell, browser prova o impacto.)*

## Nota de planning 4 — topologia multi-container SEM comunicação server-to-server (molde do 23)

> **DUAS origens (vítima + atacante), mas elas NÃO se comunicam server-to-server.** O molde é o do `csrf-basic` (23), **não** o do `nosql-injection-mongo` (22). No 22 o `mongo` era um **datastore compartilhado** que `vulnerable`/`fixed` alcançavam **por nome numa rede interna**, com `depends_on` e healthcheck de readiness. **Aqui não há nada disso:** a origem-atacante **não** conversa com a origem-vítima no backend — é o **browser da vítima** que faz **todas** as requests cross-origin (carrega a página do atacante, cujo JS faz o `fetch` credenciado pro alvo). As origens são **ilhas**; o único "cabo" entre elas é o **browser**.
>
> **Consequências (LOCKED):**
> - **SEM `networks:`** — nenhuma rede interna compartilhada. Cada serviço só precisa do próprio `ports:` no host.
> - **SEM `depends_on`, SEM healthcheck** — os serviços não dependem uns dos outros pra subir; não há readiness a esperar. **NÃO** copiar o healthcheck do molde de datastore (22).
> - **Cada serviço publica o próprio binding no host** e é alcançado pelo browser via `http://<origem>:<porta>`.
> - **§8 — tudo em loopback, local-only.** Ver "Decisões abertas" (topologia de origens) e "§8 / isolamento".

---

## Decisões abertas — VOCÊ DECIDE / CONFIRME NA FASE 2 (PROPOR O QUE FUNCIONAR)

> Estas **NÃO** são preferências editoriais nem decisões de design a redecidir — são **comportamento de plataforma (navegador + DNS) que só se conhece testando**. Nesta fase de spec, o **candidato está registrado**; a **validação empírica e a escolha final são da Fase 2** (probe num browser headless real). O objetivo de cada item está **TRAVADO**; o que fica aberto é **qual valor concreto** o realiza.

### Item 1 (O NÓ TÉCNICO) — a TOPOLOGIA DE ORIGENS / HOSTNAMES (objetivo TRAVADO; valor a CONFIRMAR/PROVAR)

**O problema (o coração da plumbing).** O ataque exige **origens genuinamente distintas** (pra o `fetch` ser cross-origin e a política de CORS importar), **E** que o **cookie de sessão da vítima** viaje pra origem-vítima no `fetch` credenciado **mas NÃO vaze** pra origem-atacante. **Cookie IGNORA porta:** um cookie de `127.0.0.1:8134` também é enviado pra `127.0.0.1:8034` — então **distinguir origens só por porta COMPARTILHA o pote de cookies e falseia a demo** (o `vulnerable` e o `fixed`, ambos em `127.0.0.1`, colidiriam de cookie; e a distinção vítima↔atacante ficaria só na porta, o que não isola o pote).

**RUMO TRAVADO:** usar **HOSTNAMES DISTINTOS que resolvem pra loopback** — **NÃO** só portas. Candidatos: **`victim.localtest.me` / `attacker.localtest.me`**, **OU** subdomínios **`.localhost`** (ex.: `victim.localhost` / `attacker.localhost`), **OU** um **alias interno** (ex.: entradas em `/etc/hosts` do container do navegador headless). Hostnames distintos dão (a) origens de fato diferentes (host distinto → origem distinta, mesmo apontando pro mesmo loopback) e (b) **potes de cookie separados** (o cookie de `victim.*` **não** vai pra `attacker.*`).

**PROPRIEDADE A APROVEITAR (registrar):** com hostnames, **o binding do Docker pode permanecer no literal `127.0.0.1:<porta>`** (o hostname resolve pra `127.0.0.1`), **honrando o §8 literal e o parser do wrapper `./atom`** (que casa só `127.0.0.1`), enquanto os **hostnames distintos** fornecem a distinção de origem. Isso é **mais limpo** que o desvio pra `127.0.0.2` que o `csrf-basic` (23) usou (o atacante do 23 não aparecia no `./atom` porque bindava em `127.0.0.2`). **Confirmar na Fase 2.**

**A COLISÃO vulnerable↔fixed (registrar; precedente do 23).** Mesmo com hostnames, se `vulnerable` e `fixed` compartilharem o **mesmo** host (ex.: ambos `victim.localtest.me`, só a porta muda), o pote de cookie **colide** (cookie ignora porta) — logar/semear num contamina o outro. Duas saídas, **a Fase 2 escolhe a mais limpa**: (a) **nomes de cookie distintos por lado** (`session_vuln`/`session_fixed`, `SESSION_COOKIE_NAME` — o exato precedente do `csrf-basic` (23), item 2), **ou** (b) **hostnames distintos por lado** (ex.: `victim.localtest.me` pro vulnerable e `victim-fixed.localtest.me` pro fixed). **Invariante:** a **política de CORS** tem que ser o **único delta de segurança** entre os lados — a plumbing de anticolisão (nome ou hostname) **não** conta como delta de segurança.

**A resolução DNS OFFLINE no headless (o risco frágil).** O `localtest.me` depende de **resolver via internet** (é um domínio público que aponta pra `127.0.0.1`); num **container de navegador headless OFFLINE**, isso pode **não resolver**. Um `.localhost` (RFC 6761 — resolvido localmente por muitos resolvers) **ou** uma entrada em `/etc/hosts`/`--host-resolver-rules` do Chromium headless pode ser **mais robusto offline**. **QUAL** hostname e **COMO** garantir a resolução DNS de dentro do container do navegador headless offline é **DECISÃO ABERTA**.

**O que a Fase 2 tem que PROVAR (rodando num browser headless real):** (a) o par de origens escolhido é **cross-origin**; (b) o **cookie da vítima** viaja no `fetch` credenciado pra origem-vítima **e NÃO vaza** pra origem-atacante (potes separados); (c) o vulnerable **reflete** a origem do atacante + `Allow-Credentials: true` e o navegador **libera** a leitura; (d) o esquema de hostnames **resolve offline** dentro do container headless. **PROPOR o esquema que funcionar. Se NADA reproduzir offline, PARAR e avisar o mantenedor** — o átomo inteiro depende disso.

### Itens de forma (candidato registrado; a Fase 2 confirma pela via mais didática)

- **Item 2 — a forma dos cabeçalhos CORS (flask-cors explícito vs `after_request` à mão).** Decidir pela mais **DIDÁTICA** — **o cabeçalho tem que estar VISÍVEL no código** pra o aluno ver a causa. **Recomendo `after_request` à mão** (setar `Access-Control-Allow-Origin`/`Allow-Credentials` explicitamente — ethos do repo, como o HMAC à mão do `20` e o synchronizer token à mão do `23`). Se usar `flask-cors`, que seja de forma **explícita e legível** — **NÃO** como "mágica" escondida que esconde a causa.
- **Item 3 — a allowlist do fixed inclui uma 3ª origem "parceira" ou basta a própria origem da vítima.** Modelar a vítima como tendo um **parceiro cross-origin legítimo** (então precisa de **ALGUM** CORS — o fix **não** é "apagar CORS", é "configurar certo"). Confirmar na Fase 2 se a allowlist contém uma origem "parceira" (candidato: `http://partner.localtest.me:<porta>`, que pode ou não ter container próprio) ou se basta enquadrar a allowlist com a própria origem da vítima.
- **Item 4 — a forma exata da exfiltração no lab.** O JS do atacante LÊ o dado e o **exibe na página de A** (candidato mais simples/observável) e/ou **manda pra um endpoint de A**. Confirmar a forma mais observável no headless.
- **Item 5 — o tratamento do preflight `OPTIONS`.** Confirmar se o `fetch` credenciado a `GET /account` (requisição "simples", sem cabeçalhos custom) **dispara** preflight (candidato: **não dispara** — GET simples com `credentials:'include'` é "simple request") e, se disparar, **como a origem-vítima responde** nos dois lados. Definir o termo "preflight" no WALKTHROUGH de qualquer forma (requisito didático).

---

## Identidade

- **ID:** `cors-wildcard`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A05 — Security Misconfiguration**. Pasta `atoms/A05-security-misconfiguration/` (**JÁ EXISTE — o 34 reaproveita**). Confirmado contra o `ROADMAP.md` ("A05 Security Misconfiguration") e o `CLAUDE.md` §4. Em prosa, usar o nome da **classe** — **CORS misconfiguration** — e a categoria — **"A05 — Security Misconfiguration"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A05-security-misconfiguration/cors-wildcard/`
- **Número sequencial:** 34
- **Porta `vulnerable` (origem-vítima):** `127.0.0.1:8034` (TRAVADO)
- **Porta `fixed` (origem-vítima):** `127.0.0.1:8134` (TRAVADO)
- **Origem do `attacker`:** a CONFIRMAR — **Item 1** (a porta própria e o esquema de hostnames dependem da topologia de origens; candidato a registrar: uma porta própria — ex.: `:8080` no molde do 23 — servida sob um hostname distinto que resolve pra loopback).
- **Bind:** **loopback** em todo `docker-compose.yml` (`CLAUDE.md` §8.1). Os alvos **só** em `127.0.0.1`. Se os hostnames distintos resolverem pra `127.0.0.1` (Item 1), o binding permanece no literal `127.0.0.1` (honrando §8 e o wrapper). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a loopback pelo compose — mesmo padrão dos irmãos.
- **Topologia:** **MULTI-CONTAINER — DUAS origens:** `victim` (em dois lados, `vulnerable` + `fixed`) + `attacker`. **Elas NÃO se comunicam server-to-server** (o browser media todas as requests cross-origin) → **SEM rede interna, SEM `depends_on`, SEM healthcheck** (Nota de planning 4, molde do 23). Cada serviço só publica o próprio binding no host.
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/abertura/encerramento** (§5 foreshadow).
- **Branch de trabalho:** `atom/cors-wildcard`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de CORS** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/cors`** (título/grafia esperados: **"Cross-origin resource sharing (CORS)"**), que cobre exatamente **reflexão de origem + `Allow-Credentials` + o problema do `*`** — fit limpo. **Provavelmente NÃO precisa de fallback OWASP** (diferente do 33). **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# cors-wildcard — Cross-origin resource sharing (CORS) misconfiguration`** — `id` + nome canônico da **classe** em inglês (a classe é **CORS misconfiguration**; a sigla expandida na 1ª ocorrência). **SEM** "Flask"/"flask-cors"/"Python" no H1 (o slug já qualifica a variante). *(Alternativas registradas: `CORS misconfiguration`, `Cross-origin resource sharing misconfiguration`.)* Grafia canônica exata **confirmável na Fase 2** (casando, quando possível, com o título da página do primer); **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**CORS misconfiguration — o servidor relaxa a Same-Origin Policy pra QUALQUER origem, com credenciais.** Uma API com login e um endpoint autenticado que devolve **dado privado** da conta (aqui, o perfil/saldo da vítima). O navegador impõe a **Same-Origin Policy (SOP)**: um script rodando na origem `A` pode **disparar** uma requisição pra origem `B`, mas **não pode LER** a resposta de `B` (é o que impede um site qualquer de ler a sua página de conta noutro site onde você está logado). O **CORS** (Cross-Origin Resource Sharing) é o mecanismo pelo qual o **servidor de `B`** pode **relaxar** essa regra de propósito — por **cabeçalhos de resposta** —, dizendo ao navegador "esta origem `A` pode ler a minha resposta". O endpoint aqui faz isso **errado**: ele lê o cabeçalho `Origin` do request e o **reflete de volta** em `Access-Control-Allow-Origin`, junto com `Access-Control-Allow-Credentials: true` — ou seja, responde "sim, você pode ler, inclusive com os cookies da vítima" pra **QUALQUER** origem que perguntar.

O atacante, hospedado em **outra origem**, serve uma página cujo JS faz um `fetch` **credenciado** (`credentials:'include'`) pro endpoint da vítima. A vítima — **logada no alvo** — abre a página do atacante; o navegador dela, obedecendo a regra de "reenviar o cookie do alvo em toda request pro alvo", **anexa o cookie de sessão da vítima** no `fetch`. O servidor devolve o dado privado **com a política de CORS refletindo a origem do atacante**; o navegador vê `Access-Control-Allow-Origin: <origem-do-atacante>` + `Allow-Credentials: true` e **libera a leitura pro script do atacante** — que **exfiltra** o dado autenticado da vítima. A **lógica do endpoint está correta** (ele autentica, vê o cookie, devolve o dado a quem deveria); o buraco é a **política de CORS** instruir o navegador a liberar a leitura pra quem não devia.

### A lição-coração

> **"O navegador impõe a Same-Origin Policy: um script de `evil.com` pode DISPARAR uma requisição a `banco.com`, mas NÃO pode LER a resposta — é o que impede `evil.com` de ler sua conta no `banco.com`. CORS é como o servidor relaxa isso de propósito, por cabeçalhos: `Access-Control-Allow-Origin` diz qual origem pode ler, e `Allow-Credentials: true` diz 'inclusive com os cookies da vítima'. A má config: o servidor REFLETE de volta qualquer origem que pergunta E manda `Allow-Credentials: true` — responde 'sim' pra QUALQUER site. Uma vítima logada no `banco.com` que visita `evil.com` tem o navegador anexando os cookies dela na requisição, e o script do atacante LÊ a resposta autenticada — roubo de dados cross-origin. O fix NÃO é 'refletir uma origem específica' (refletir É o bug) — é uma ALLOWLIST de origens realmente confiáveis (ou nenhum cabeçalho CORS, se o endpoint não precisa de acesso cross-origin)."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH — DEFINIR CADA PEÇA NA ESTREIA)

O átomo assume que o aluno **não conhece nenhum** destes termos. Definir do zero, na 1ª ocorrência:

- **Origem (origin).** A tripla **esquema + host + porta** (ex.: `http://banco.com:80`). Dois URLs são da **mesma origem** só se as três partes batem. `http://banco.com` e `https://banco.com` são origens **diferentes** (esquema); `http://banco.com` e `http://evil.com` são diferentes (host); `http://banco.com:8034` e `http://banco.com:8134` são diferentes (porta). *(Ressalva a cravar: **cookie NÃO usa a porta** pra decidir onde ir — por isso a plumbing de origens do lab precisa de cuidado, Item 1 — mas a **origem** do CORS usa. Duas coisas distintas.)*
- **Same-Origin Policy (SOP).** A regra fundamental do navegador: um script rodando numa origem pode **DISPARAR** requisições a outra origem, mas o navegador **NÃO deixa esse script LER a resposta** de outra origem. É o que impede o JS de `evil.com` de fazer uma chamada ao `banco.com` (onde você está logado) e **ler** a página da sua conta. **A SOP tem duas metades** — poder enviar, não poder ler; o foco deste átomo é o lado da **LEITURA**.
- **CORS (Cross-Origin Resource Sharing).** O mecanismo pelo qual o **servidor** pode **relaxar** a SOP **de propósito**, permitindo que origens específicas **leiam** suas respostas. Ele funciona por **cabeçalhos de resposta HTTP** — o servidor "dá permissão" e o **navegador obedece**. CORS **não** é um controle no servidor (o servidor sempre entrega o corpo a quem faz a requisição); é uma **instrução ao navegador** sobre se ele pode **repassar** a resposta ao script que a pediu.
- **`Access-Control-Allow-Origin` (ACAO).** O cabeçalho de resposta que diz **QUAL origem** pode ler a resposta. Pode ser uma origem específica (`http://parceiro.com`) ou o **curinga `*`** ("qualquer origem"). Se a origem do request **bate** com o ACAO, o navegador libera a leitura pro script; senão, **bloqueia** (o script recebe um erro de CORS, sem o corpo).
- **`Access-Control-Allow-Credentials: true` (ACAC).** O cabeçalho que diz ao navegador "**inclusive com credenciais**" — ou seja, o navegador pode **anexar os cookies da vítima** na requisição cross-origin **E** expor a resposta ao script mesmo tendo mandado esses cookies. **Sem** esse cabeçalho, uma requisição credenciada tem a resposta **bloqueada** pelo navegador, mesmo que o ACAO bata.
- **Requisição credenciada (`credentials:'include'`).** Por padrão, o `fetch` cross-origin **NÃO** manda os cookies do alvo. Pra mandar (e é isso que caracteriza o ataque), o atacante usa `fetch(url, { credentials: 'include' })` — que instrui o navegador a **anexar os cookies do alvo** na requisição cross-origin. É o análogo de leitura do que o `csrf-basic` (23) explora no envio.
- **Preflight (a requisição `OPTIONS`).** Antes de certas requisições cross-origin (as "não-simples" — ex.: método `PUT`/`DELETE`, ou cabeçalhos custom), o navegador manda **primeiro** uma requisição `OPTIONS` "de sondagem" (o **preflight**), perguntando ao servidor se aquela requisição é permitida; só se o servidor responder OK é que a requisição real é enviada. Uma requisição **simples** (um `GET` sem cabeçalhos custom, como o `fetch` a `GET /account` deste átomo) **não** dispara preflight — mas o navegador **ainda** checa o ACAO/ACAC da resposta antes de liberar a leitura. *(Definir o termo mesmo que o ataque não dispare preflight — requisito didático; ver Item 5.)*

**A REFLEXÃO vs o `*` literal (o coração técnico — DEFINIR CLARAMENTE):**

- **O `*` literal quase não serve pra roubo autenticado.** A especificação do CORS **proíbe** combinar `Access-Control-Allow-Origin: *` com `Access-Control-Allow-Credentials: true`: quando a resposta traz `ACAO: *`, o navegador **RECUSA** expor uma resposta **credenciada** (o `fetch` com `credentials:'include'` falha). Ou seja, `*` só libera dado **público** (sem cookies) — **baixo impacto**.
- **Por isso a REFLEXÃO existe.** Pra driblar essa recusa, o servidor mal configurado **lê o `Origin` do request e o devolve** em `ACAO` — assim o ACAO é uma **origem específica** (não `*`), e o navegador **aceita** combiná-lo com `Allow-Credentials: true`. O efeito prático é o mesmo de "`*` com credenciais" (qualquer origem lê), mas **funciona** — o navegador não recusa uma origem específica refletida. **Este é o vetor autenticado**, e é o que o átomo modela.

O ponto contraintuitivo a cravar: **o `*` do slug é a intuição ingênua, mas o `*` literal nem funciona com credenciais** — o vetor real de roubo autenticado é a **reflexão da origem** + `Allow-Credentials: true`.

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas do DIFF)

> **A causa é a POLÍTICA (refletir qualquer origem + credenciais), NÃO "faltou autenticação" nem "o dado é sensível demais". O endpoint EXIGE o cookie e o VÊ — a autenticação funciona. O dado ser privado é o que dá valor ao roubo, mas não é o furo. O furo é o navegador ser INSTRUÍDO (pelos cabeçalhos CORS do servidor) a liberar a LEITURA da resposta pro atacante. O fix não é 'refletir uma origem específica' (refletir É o bug — reflete o atacante junto) — é uma ALLOWLIST de correspondência EXATA de origens confiáveis (ou nenhum cabeçalho CORS, se o endpoint não precisa de acesso cross-origin).**

### Por que A05 (Security Misconfiguration)

O bug **não é** "input virou código" (injection) nem "faltou um check de dono" (broken access control — o endpoint **tem** o check de sessão e ele **passa** pra vítima) nem "o primitivo de crypto é fraco" (A02). É **"uma política de resposta HTTP foi configurada de forma perigosa"** — o servidor instrui o navegador a liberar a leitura cross-origin credenciada pra **qualquer** origem. É um **estado de configuração perigoso**, não um erro de lógica de negócio (a rota `/account` está logicamente correta: autentica, vê o cookie, devolve o dado certo à vítima). No Web Top 10 2021 isso é **A05 — Security Misconfiguration**, a mesma categoria dos irmãos XXE (18/30) e do `debug-enabled` (33). Situar em **A05 — Security Misconfiguration**, **sem** contar edições antigas. Contraste de sub-forma com os irmãos: XXE é misconfig de **parser** (default perigoso); `debug-enabled` é misconfig de **framework/deploy** (modo de dev alcançável); aqui é misconfig de **política de resposta HTTP** (os cabeçalhos CORS).

---

## Contraste com o 23 (central — é o que justifica o átomo e ancora a SOP) + irmãos A05

O 34 e o `csrf-basic` (23, publicado) são **as duas metades da Same-Origin Policy**. Cravar no WALKTHROUGH e no DIFF, ou o átomo parece "o 23 de novo". Ambos são "browser cross-origin", ambos exploram a fronteira de origem — mas a **operação é OPOSTA**.

| Eixo | `csrf-basic` (23) | `cors-wildcard` (34) |
|---|---|---|
| **Categoria OWASP** | **A01 — Broken Access Control** | **A05 — Security Misconfiguration** |
| **Metade da SOP** | o lado do **ENVIO** — o browser **DISPARA** uma request cross-site sozinho | o lado da **LEITURA** — o navegador **LIBERA a LEITURA** da resposta cross-origin |
| **O que o atacante consegue** | **disparar** uma ação de mudança-de-estado (escrita **CEGA** — não lê a resposta) | **LER** uma resposta autenticada (exfiltração — **lê** o dado privado) |
| **O atacante LÊ a resposta?** | **NÃO** — a SOP cega o atacante (fire-and-forget) | **SIM** — a má config de CORS **instrui o navegador a liberar** a leitura |
| **O cookie da vítima** | viaja sozinho na request forjada (`SameSite=None`) | viaja no `fetch` credenciado (`credentials:'include'`) |
| **Causa-raiz** | o servidor confia no cookie como prova de **INTENÇÃO** (não verifica que o user quis) | a **política de CORS** reflete qualquer origem + `Allow-Credentials: true` |
| **Fix** | **token anti-CSRF** (verifica intenção; o atacante não LÊ o token — SOP) | **allowlist de correspondência EXATA** de origens (ou não pôr CORS) |
| **Impacto** | account takeover via escrita forçada | exfiltração de dado autenticado cross-origin |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante):** os dois exploram a fronteira de origem no navegador, mas em **direções opostas**. No 23 a SOP **impede o atacante de LER** a resposta — então o ataque é uma **escrita cega** (o atacante dispara e não vê o resultado). No 34 a má config **desfaz** justamente essa proteção de leitura — o atacante **lê** o dado autenticado que a SOP deveria ter bloqueado. **Enviar (23) vs ler (34): as duas metades da SOP.** Citar 23 (publicado) à vontade — o aluno abre os dois e vê *"a mesma fronteira de origem, quebrada nos dois sentidos"*.

**Irmãos A05 (contraste de sub-forma, todos publicados):** `xxe-basic` (18) e `xxe-blind-oob` (30) são misconfig de **parser XML**; `debug-enabled` (33) é misconfig de **framework/deploy**; o 34 é misconfig de **política de resposta HTTP**. Reusar o enquadramento "A05 — Security Misconfiguration" e ancorar a lição nesse contraste de sub-forma. **Molde de browser/headless:** o `xss-dom` (21) — exceção de browser + técnica de validação headless (mas o contraste com 21 é o mesmo do 23: no XSS o script roda **dentro** do alvo e lê tudo; aqui o script roda **na origem do atacante** e só lê porque a má config o liberou).

---

## Uma vuln só — o `/account` está CORRETO; a única falha é a política de CORS

Invariante inegociável do átomo (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é a **política de CORS** (reflexão da origem + `Allow-Credentials: true` num ambiente que o atacante alcança). Para garantir isso:

- **O `/account` é código CORRETO.** Ele autentica (exige o cookie de sessão), vê o cookie, e devolve o dado privado da conta **a quem deveria** (a vítima logada). A lógica de autenticação/autorização está **certa** — o input benigno (a vítima acessando a própria conta) funciona igual nos dois lados. **A falha NÃO é o endpoint** — é a **política de CORS** que o navegador recebe junto.
- **O login/sessão é comum.** `POST /login` (auth simulada, seta o cookie de sessão) é só o **palco** — estabelece a sessão da vítima. **Não é a vuln.** Sem datastore: o estado da conta é um `dict`/variável do módulo (`ACCOUNT = {...}`).
- **O `fixed` muda SÓ a política de CORS** (reflexão → allowlist de correspondência exata). O `/account`, o `POST /login`, os imports, o estado da conta — **idênticos**. A anticolisão de cookie (Item 1) é **plumbing**, **não** delta de segurança.
- **A origem-atacante NÃO tem vuln própria.** É só o **palco cross-origin** de onde o `fetch` credenciado parte. Sem segunda superfície injetável.
- **Sem 2ª vuln:** **sem** injection, **sem** falha de auth (o endpoint autentica), **sem** leitura de arquivo, **sem** mass assignment. O único diff é a **política de CORS**.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é a **ALLOWLIST EXATA**, **NÃO** "checar substring/sufixo" (armadilha #2), **NÃO** "só tirar as credenciais" (armadilha #3), **NÃO** "usar `*`" (nem funciona com credenciais — #4).

---

## Flavor — duas origens, vítima logada por cookie (TRAVADO)

Cenário canônico de CORS misconfiguration: **uma API que devolve dado privado da conta, com a política de CORS refletindo qualquer origem + credenciais.** As duas origens:

- **ORIGEM-VÍTIMA (`vulnerable` :8034 / `fixed` :8134) — Flask, API-only JSON:**
  - **`POST /login`** — auth simulada (usuário fake semeado; qualquer credencial demo correta loga). Seta o **cookie de sessão** da vítima. **Não é a vuln.**
  - **`GET /account`** (ou `/me`) — **EXIGE o cookie** e devolve **dado privado** (candidato: **saldo/perfil dummy** — ex.: `{"user": "demo", "balance": "...", "email": "demo@example.com"}`, dados fake §8). É código **correto**. **COM A MÁ CONFIG DE CORS** no vulnerable: a resposta reflete a `Origin` do request + `Allow-Credentials: true`.
  - **A política de CORS** é setada (candidato) num **`after_request` à mão** (Item 2 — cabeçalho visível no código). No `vulnerable`, **reflete** a `Origin`; no `fixed`, só seta o cabeçalho se a `Origin` estiver **exatamente** numa **allowlist**.
- **ORIGEM-ATACANTE (`attacker`) — página HTML mínima + JS:**
  - Uma página cujo JS faz **`fetch('http://<vítima>/account', { credentials: 'include' })`**, **LÊ** o dado privado e o **EXFILTRA** (Item 4: exibe na página de A e/ou manda pra um endpoint de A).
  - Deve permitir demonstrar **tanto o sucesso** contra o `vulnerable` (:8034) **quanto o bloqueio** contra o `fixed` (:8134) — candidato: **duas páginas/rotas** (`/attack-vuln`, `/attack-fixed`), cada uma apontando o `fetch` pro alvo respectivo. **O atacante NÃO tem vuln própria.**

**O ATAQUE (resumo; detalhe em "A prova no browser"):** a vítima está logada na origem-vítima (cookie semeado); visita a página do atacante; o JS de A faz o `fetch` credenciado pra origem-vítima; o navegador **anexa o cookie da vítima**; a origem-vítima responde com a má config de CORS; o navegador **LIBERA a leitura** pro script de A → **A lê o dado privado da vítima**. **PROVA:** a página de A **mostra o dado privado da vítima** (que a SOP deveria ter bloqueado). **FIXED:** o **mesmo** `fetch` → o navegador **BLOQUEIA a leitura** (a allowlist da vítima não inclui a origem de A) → o JS de A recebe um **erro de CORS** e **nada de dado** (mostrar o erro no console/na página).

Este átomo **PRECISA de HTML/JS** (o exploit é client-side, como 21/23) — a origem-atacante é uma **página real** cujo JS faz o `fetch`. A origem-vítima é **API-only JSON** (sem HTML próprio — a "UI" que ensina é o `fetch` do atacante lendo a resposta).

---

## O "tell" — a origem refletida na resposta (mostrar ANTES do exploit no browser) — OBRIGATÓRIO

**ANTES** do exploit no navegador, o WALKTHROUGH DEVE mostrar o **"tell"** observável no Burp/na resposta HTTP:

- Mandar um request a `GET /account` (no **vulnerable**) com um cabeçalho **`Origin: http://<origem-atacante>`** e mostrar, na **RESPOSTA**, que o servidor **DEVOLVE** `Access-Control-Allow-Origin: http://<origem-atacante>` (a **MESMA** origem refletida) + `Access-Control-Allow-Credentials: true`. **Isso é o sinal da má config** — o servidor topa qualquer origem. Repetir com uma `Origin` diferente pra mostrar que ele reflete **qualquer** uma.
- **É observável na resposta HTTP** — direto no Repeater. Mas **explicar** (Nota de planning 3-A): `curl`/Burp **leem o corpo de qualquer forma** (CORS não é controle do servidor), então **o tell sozinho não é a prova do impacto** — ele mostra a **má config**; a **prova** (o script do atacante conseguindo ler) exige o navegador.
- Contraste imediato com o **fixed**: o **mesmo** request com `Origin: http://<origem-atacante>` → a resposta **NÃO reflete** a origem do atacante (não há cabeçalho `Access-Control-Allow-Origin`, ou ele traz só uma origem da allowlist que **não** é a do atacante). A diferença é **observável na própria resposta**.
- **VALIDAR RODANDO na Fase 2** e capturar a resposta real (os cabeçalhos ACAO/ACAC refletidos no vulnerable; a ausência no fixed).

---

## A prova no browser (TRAVADO; a prova EXIGE o navegador) + validação headless

O impacto (o atacante **LENDO** o dado autenticado) só se prova no **navegador**, porque **CORS é um controle do browser**. Cadeia (browser na trilha principal):

1. **Semear a sessão da vítima na origem-vítima** (cookie) — via `POST /login` no browser.
2. **Carregar a página do atacante** (origem de A).
3. **O JS de A faz `fetch('http://<vítima>/account', { credentials: 'include' })`** — o navegador anexa o cookie da vítima.
4. **No `vulnerable`:** a resposta reflete a origem de A + `Allow-Credentials: true` → o navegador **LIBERA a leitura** → **A LÊ e exibe o dado privado** da vítima. **A prova é A exibindo o dado.**
5. **No `fixed`:** a resposta **não reflete** a origem de A → o navegador **BLOQUEIA a leitura** → o JS de A recebe um **erro de CORS** e **nada de dado**. **A prova do fix é o erro de CORS + a ausência do dado.**

**VALIDAÇÃO HEADLESS (Fase 2):** headless-CDP com **sessão/cookie persistente** — semear o cookie na origem da vítima, navegar pra origem do atacante, executar o `fetch`, capturar o que A conseguiu ler. **Consultar a memória `validating-csrf-cross-site-headless`** (o molde de **CDP com sessão/cookie persistente** entre navegações — o mesmo desafio do `csrf-basic` (23): login → cookie → página do atacante → observar o resultado; aqui o resultado é o **dado exfiltrado** exibido por A, lido via `--dump-dom` ou avaliação de JS, **não** um `alert` que trava headless). §8: dados dummy, `127.0.0.1`, nada real. **É um probe de comportamento de navegador** (version/headless-dependent, como a dança do 23) — **PROVAR rodando**; gate: **"não reproduziu → PARA e avisa, NÃO inventa"** a prova/o dado exfiltrado.

### Prova de isolamento (o que traça a diferença PURO à política de CORS)

- **Same-origin, IDÊNTICO nos dois lados:** a vítima acessando o **próprio** `/account` (mesma origem — o browser da vítima na origem-vítima) lê o dado **IDÊNTICO** no vulnerable **e** no fixed. A feature é a mesma; a política de CORS **não afeta** o acesso same-origin (a SOP nem entra). **Só** o `fetch` **CROSS-ORIGIN** do atacante separa os lados.
- **Cross-origin:** no **vulnerable**, o `fetch` do atacante **lê** o dado (a má config liberou); no **fixed**, o **mesmo** `fetch` é **bloqueado** pelo navegador (erro de CORS). A diferença é **100% a política de CORS**, **não** o `/account` (idêntico) nem uma dependência.

---

## O código — o coração na política de CORS do `app.py` da origem-vítima (candidatos)

O fio condutor: **a política de CORS reflete qualquer origem + credenciais**. O `app.py` da origem-vítima **DIFERE** entre `vulnerable` e `fixed` **na política de CORS** (reflexão → allowlist exata); todo o resto — `POST /login`, `GET /account`, os imports, o estado da conta — é **IDÊNTICO**. O `attacker/app.py` é o mesmo palco nos dois cenários.

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma a topologia de origens (Item 1), captura o request/response reais, e prova o exploit no browser headless.**

### `victim` `vulnerable/app.py` — CORS reflete a origem + credenciais (candidato)

```python
import os
from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = "changeme-vuln"  # dummy dev-only key (CLAUDE.md §8.3)

# Session cookie so the victim's login persists. SameSite=None; Secure so the
# credentialed cross-origin fetch carries the cookie (Secure works over HTTP on
# loopback -- secure context). Anti-collision (name/hostname) is Item 1 plumbing,
# NOT a security delta.
app.config.update(
    SESSION_COOKIE_NAME="session_vuln",
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# Single demo user's private account state, in memory -- no datastore needed. Dummy (§8).
ACCOUNT = {"user": "demo", "balance": "R$ 42.000,00", "email": "demo@example.com"}


@app.route("/login", methods=["POST"])
def login():
    if request.form.get("username") == "demo" and request.form.get("password") == "demo":
        session["user"] = "demo"
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401


@app.route("/account")
def account():
    # ORDINARY, CORRECT endpoint: it REQUIRES the session cookie and returns the
    # logged-in user's private data. Authentication works. The flaw is NOT here.
    if "user" not in session:
        return jsonify({"error": "not logged in"}), 403
    return jsonify(ACCOUNT)


@app.after_request
def add_cors(resp):
    # VULNERABLE: reflect back WHATEVER Origin asked, plus allow credentials. This tells
    # the browser "yes, THIS origin may read the response WITH the victim's cookies" -- for
    # ANY origin, because we echo whatever we get. Reflection (not the literal *) is the
    # authenticated-theft vector: the browser refuses `*` together with credentials, so a
    # reflected specific origin is how the misconfig actually works. The header is set by
    # hand (after_request) so the cause is VISIBLE in the code.
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin       # <-- reflection: the bug
        resp.headers["Access-Control-Allow-Credentials"] = "true"  # <-- "with the victim's cookies"
    return resp


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `victim` `fixed/app.py` — allowlist de correspondência EXATA (candidato)

Só a política de CORS muda; o resto é idêntico:

```python
# ... imports, session config (name session_fixed -- Item 1 plumbing), ACCOUNT,
#     POST /login, GET /account IDENTICAL to vulnerable ...

# Exact-match allowlist of ORIGINS we actually trust (a legitimate cross-origin
# partner). NOT "reflect a specific origin" -- reflecting IS the bug. Item 3 confirms
# whether this holds a partner origin or the victim's own origin.
ALLOWED_ORIGINS = {"http://partner.localtest.me:8080"}  # candidate -- Phase 2 confirms


@app.after_request
def add_cors(resp):
    # FIXED: only echo the Origin if it is EXACTLY in the allowlist. An untrusted origin
    # (the attacker) gets NO CORS header at all, so the browser blocks the cross-origin
    # read. Exact match -- NOT endswith/substring (bypassable: evil-partner..., ...evil.com),
    # NOT dropping credentials while still reflecting (public data still leaks).
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp
```

### `attacker/app.py` + página — o palco cross-origin, SEM vuln própria (candidato)

Um Flask mínimo servindo a(s) página(s) com o JS do `fetch` credenciado (Item 4 — a forma da exfiltração):

```html
<!-- attack.html (candidate) -- served by the attacker origin -->
<script>
  // Credentialed fetch: credentials:'include' tells the browser to attach the victim's
  // cookies for the victim origin. On the vulnerable target the misconfig lets us READ
  // the response; on the fixed target the browser blocks the read (CORS error).
  fetch("http://victim.localtest.me:8034/account", { credentials: "include" })
    .then(r => r.json())
    .then(d => { document.getElementById("loot").textContent = JSON.stringify(d); })   // exfil: display
    .catch(e => { document.getElementById("loot").textContent = "CORS error: " + e; }); // fixed: blocked
</script>
```

### Notas de implementação (validar/decidir na Fase 2)

- **A política de CORS via `after_request` à mão (Item 2 — recomendado).** O cabeçalho **visível no código** ensina a causa. Se usar `flask-cors`, de forma **explícita/legível** — nunca como mágica escondida.
- **O `GET /account` lê a sessão (cookie), devolve JSON.** É código **correto** — o input benigno (vítima na própria conta) funciona igual nos dois lados. A única diferença é o `after_request`.
- **Cookie config `SameSite=None; Secure` (candidato) pra o cookie viajar no `fetch` credenciado cross-origin.** Como no `csrf-basic` (23) — `Secure` sobre HTTP funciona porque loopback é secure context. **Confirmar na Fase 2** que o cookie viaja no `fetch` credenciado (Item 1 / risco #3). A **anticolisão** (nome/hostname) é plumbing (Item 1), **não** delta de segurança.
- **Preflight (Item 5):** um `GET` simples com `credentials:'include'` (sem cabeçalhos custom) **não** dispara preflight (candidato). Se disparar (ou se a Fase 2 usar uma variante que dispare), tratar o `OPTIONS` **nos dois lados** consistentemente. **Definir "preflight" no WALKTHROUGH de qualquer forma** (requisito didático).
- **Banner de aviso (§8) em TODA página HTML** — inclusive a do atacante. E no `GET /` JSON da origem-vítima (padrão dos átomos API-only). Confirmar na Fase 2.

---

## O fix e o tipo de diff

**Fix:** trocar a **REFLEXÃO** da origem por uma **ALLOWLIST de correspondência EXATA** de origens confiáveis (ou **remover** os cabeçalhos CORS, se o endpoint não precisa de acesso cross-origin). A política de CORS é o **único delta de segurança** entre `vulnerable` e `fixed`; o `/account`, o `POST /login` e o estado da conta são **idênticos** (a anticolisão de cookie do Item 1 é plumbing, não segurança). Tipo de diff: **lógica-diferente** — a condição do `after_request` (refletir qualquer origem → só setar se a origem estiver **exatamente** na allowlist).

Diff colável (candidato — a Fase 2 gera o real; recortes do `after_request`):

```diff
+ALLOWED_ORIGINS = {"http://partner.localtest.me:8080"}  # exact-match allowlist
+
 @app.after_request
 def add_cors(resp):
     origin = request.headers.get("Origin")
-    if origin:
-        resp.headers["Access-Control-Allow-Origin"] = origin       # reflect ANY origin
-        resp.headers["Access-Control-Allow-Credentials"] = "true"
+    if origin in ALLOWED_ORIGINS:                                   # exact match only
+        resp.headers["Access-Control-Allow-Origin"] = origin
+        resp.headers["Access-Control-Allow-Credentials"] = "true"
     return resp
```

**O CONTRASTE é o diff:** refletir qualquer origem (vulnerable) vs setar o cabeçalho **só** pra uma allowlist de correspondência exata (fixed). O `/account` que autentica e devolve o dado é **idêntico**.

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é REFLETIR QUALQUER ORIGEM + credenciais, NÃO "faltou autenticação" nem "o dado é sensível demais".** O endpoint **autentica e VÊ o cookie** — a auth funciona. O dado ser privado dá **valor** ao roubo, mas o **furo** é a política de CORS **liberar a LEITURA** da resposta pro atacante. **Prova de isolamento:** o acesso **same-origin** (a vítima na própria conta) lê o dado **idêntico** nos dois lados; **só** o `fetch` **cross-origin** do atacante separa vulnerable (lê) de fixed (bloqueado). A diferença é **100% a política de CORS**, não o endpoint.
2. **"Só checar se a `Origin` CONTÉM/termina com nosso domínio" NÃO é o fix — nota-ARMADILHA (a clássica).** Nomear a intuição: *"é só aceitar origens que terminam com `banco.com`."* Mostrar que `origin.endswith("banco.com")` é **contornável** — `http://evil-banco.com` **termina** com `banco.com`, e `http://banco.com.evil.com` **contém** `banco.com`. **Substring/sufixo NÃO é correspondência exata.** O check tem que ser **match EXATO** contra uma allowlist (`origin in ALLOWED_ORIGINS`). *(Mesma honestidade-em-camadas das notas dos átomos recentes: a defesa nomeada parece razoável, mas tem furo.)*
3. **"Tirar as credenciais mas continuar refletindo" NÃO é o fix — nota-ARMADILHA (parcial, honestidade em camadas).** Nomear a intuição: *"é só não mandar `Allow-Credentials: true`."* Ser honesto: **sem** `Allow-Credentials`, o navegador **não expõe** a resposta credenciada — então o **roubo AUTENTICADO** para (o cookie não vaza). **MAS** dado **público** (sem cookie) **ainda vaza** pra qualquer origem, porque você continua refletindo o ACAO. É **melhora parcial**, **não** o fix de causa (a causa é **refletir qualquer origem**). O fix de causa é a **allowlist exata**.
4. **O `*` literal NÃO é o vetor com credenciais — o navegador RECUSA `*` + `Allow-Credentials`.** Nomear a intuição do slug: *"o perigo é o `Access-Control-Allow-Origin: *`."* Mostrar que o `*` literal **nem funciona** pro roubo autenticado — o navegador **recusa** combinar `*` com `Allow-Credentials: true` (o `fetch` credenciado falha), então `*` só vaza dado **público** (baixo impacto). **É por isso que a REFLEXÃO existe:** driblar essa recusa devolvendo uma origem **específica** (a refletida), que o navegador **aceita** com credenciais.
5. **Impacto: exfiltração de dado autenticado cross-origin; CONTRASTE com o 23 (LER vs ENVIAR).** O impacto é o atacante **LER** a resposta privada da vítima — as duas metades da SOP: o `csrf-basic` (23) quebra a SOP no **envio** (escrita cega), o 34 quebra na **leitura** (exfiltração). **Sem overclaim** (não há escrita aqui — é leitura; não é account takeover, não é RCE). O teto é o que o endpoint autenticado devolve. **Sem foreshadow.**
6. **HONESTIDADE — "não adicionar CORS que você não precisa" é conselho de superfície legítimo, NÃO armadilha.** Se o endpoint **não** é cross-origin, o fix mais simples é **não pôr cabeçalho CORS nenhum**. Mas o átomo modela o caso em que **ALGUM** CORS é necessário (um **parceiro cross-origin legítimo**), e aí o fix é a **allowlist exata** — não "apagar CORS". Enquadrar as duas coisas: a correção de superfície (não pôr CORS desnecessário) e a correção do caso modelado (allowlist quando o cross-origin é legítimo). Não confundir com as armadilhas #2/#3.

---

## Biblioteca / topologia

- **Origem-vítima (`vulnerable`/`fixed`):** **Flask + stdlib**. `requirements.txt`: **Flask** (pin candidato **`Flask==3.0.0`** — casando com os irmãos; **confirmar** que instala em `python:3.11-slim` por probe na Fase 2). **SEM datastore** — estado da conta em memória. Se a Fase 2 optar por `flask-cors` (Item 2), pinar e usar de forma explícita/legível; **preferir** `after_request` à mão (cabeçalho visível). `requirements` **idênticos** entre os lados onde aplicável (o delta é a lógica do `after_request`, não uma dependência).
- **Origem-atacante (`attacker`):** **Flask mínimo** (ou `http.server`) servindo a(s) página(s) HTML+JS. **Sem vuln própria**, sem dependência extra. **Item 2/Fase 2** decide a forma mais simples.
- **Dois/três Dockerfiles** (`victim vulnerable`, `victim fixed`, `attacker`), molde dos irmãos (**com** `COPY templates` só onde há HTML — o atacante; a origem-vítima é API-only). `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé; `ENV HOST=0.0.0.0` no Dockerfile (forwarding do Docker), exposição host restrita a loopback pelo compose.
- **SAÍDA B — parcial (emenda pós-validação; a redação anterior "SEM SAÍDA B" estava incompleta).** Refletir-a-origem + `Allow-Credentials: true` é o **antipadrão ingênuo** de "fazer o CORS funcionar logo, sem pensar" (a receita de copiar-colar de StackOverflow pra "resolver o erro de CORS"). **MAS** existe, sim, uma defesa-de-plataforma que resiste ao roubo **puramente cross-site**: a **Total Cookie Protection / dynamic First-Party Isolation** do navegador (default no Firefox desde 2022; e o fim iminente dos cookies de 3ª parte) **particiona o cookie `SameSite=None` por site de topo**, então um `fetch` credenciado de um site **estranho** (evil.com → banco.com) **não leva o cookie da vítima** e o exploit **não dispara** (comprovado na validação: no Firefox padrão só disparava com a partição desligada; no Chrome atual ainda dispara porque ele ainda manda cookie de 3ª parte). Por isso o átomo enquadra o cenário no eixo de **subdomínio irmão**: a vítima `api.lab.localhost` e o atacante `evil.lab.localhost` são **cross-origin** (o CORS ainda decide a leitura) mas **same-site** (compartilham o site `lab.localhost`), então a partição de cookie de 3ª parte **não entra** e o cookie viaja — deixando a **política de CORS** como o **único** controle em jogo, e o exploit reproduz **de forma determinística nos navegadores atuais** (Firefox padrão **E** Chrome). **NÃO é "nenhuma ferramenta resiste"** (como a redação anterior sugeria, e diferente do jeito que o `csrf-basic` (23) É Saída B via `SameSite=Lax`): é que o átomo é enquadrado no eixo onde a **falha de CORS** é o que decide, isolada da proteção de cookie de 3ª parte. *(Isto também **resolve o Item 1** — topologia de origens — para subdomínios de `lab.localhost`, todos resolvendo pra `127.0.0.1`; o binding do Docker permanece `127.0.0.1`.)*

---

## §8 / isolamento — as origens em loopback; o binding permanece literal `127.0.0.1`

- **Origem-vítima:** `127.0.0.1:8034` (vulnerable) e `127.0.0.1:8134` (fixed) — literal `127.0.0.1`.
- **Origem-atacante:** binding a CONFIRMAR (Item 1). **Se os hostnames distintos resolverem pra `127.0.0.1`** (Item 1), o binding do atacante **permanece no literal `127.0.0.1:<porta>`** e os hostnames dão a distinção de origem — **honrando o §8 literal e o parser do wrapper `./atom`** (que casa só `127.0.0.1`). Isso é **mais limpo** que o desvio pra `127.0.0.2` do `csrf-basic` (23). **Confirmar na Fase 2** que a origem do atacante **não é alcançável de fora** (loopback) e que resolve **offline** no headless.
- **Todos os serviços em loopback, local-only.** `CLAUDE.md` §8.1. Sem exposição à rede/internet. Dados dummy (perfil/saldo fake, `.example`/valores fictícios); `secret_key` dummy.
- **CI linter de port-binding (ROADMAP, ainda não existe) — flag pro mantenedor.** O linter planejado valida `ports:` em `127.0.0.1`. **Se** o esquema de hostnames mantiver o binding no literal `127.0.0.1` (Item 1), **não há desvio** a documentar — vantagem sobre o `127.0.0.2` do 23. **Se** a Fase 2 precisar de um IP não-literal, tratar como desvio documentado. **Registrar** pro mantenedor decidir junto com o Item 1.

---

## WALKTHROUGH — abertura seca; browser na trilha PRINCIPAL (§3.3 EXCEÇÃO client-side); DENSO EM DEFINIÇÕES

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (uma API que devolve os dados privados da conta a quem tem o cookie de sessão) e a falha (a política de CORS reflete qualquer origem + credenciais). Trilha **principal única**: **browser + Burp juntos** — o **Burp** mostra o "tell" (a origem refletida + `Allow-Credentials` na resposta); o **browser** reproduz o exploit (a vítima logada → a página do atacante faz o `fetch` credenciado → A lê o dado). **NÃO** criar uma "trilha browser secundária" (proibida pela §3.3 atual).

**Abertura (candidato — plantar a lição, seco):**

> *A app é uma API: você faz login, recebe um cookie de sessão, e `GET /account` te devolve os dados privados da sua conta enquanto você tiver o cookie. Normalmente, um script rodando noutro site — o site do atacante — poderia até DISPARAR essa requisição a partir do seu navegador (que anexaria o seu cookie), mas o navegador NÃO deixaria esse script LER a resposta: é a Same-Origin Policy, a regra que impede um site qualquer de ler a sua página de conta noutro site. O problema desta app: ela diz ao navegador, por cabeçalhos de resposta (CORS), que QUALQUER origem pode ler a resposta — inclusive com os seus cookies. Ela faz isso refletindo de volta a origem de quem pergunta. Então o site do atacante faz o seu navegador buscar a sua conta, com o seu cookie, e — porque a app mandou o navegador liberar — LÊ os seus dados. Você nunca autorizou; o atacante nunca soube a sua senha nem leu o seu cookie.*

Beats (molde do 23 publicado — abertura seca, seções numeradas `## 1..7`):

1. **Context.** Feature: uma API autenticada que devolve dado privado da conta. **Definir na estreia (REQUISITO DIDÁTICO — do zero):** **origem** (esquema + host + porta), **Same-Origin Policy (SOP)** (o navegador deixa um script DISPARAR request cross-origin mas NÃO LER a resposta — as duas metades; foco na LEITURA), **CORS (Cross-Origin Resource Sharing)** (como o servidor relaxa a SOP por cabeçalhos de resposta), **`Access-Control-Allow-Origin`** (qual origem pode ler), **`Access-Control-Allow-Credentials: true`** (inclusive com os cookies da vítima), **requisição credenciada** (`fetch` com `credentials:'include'`), **preflight** (a `OPTIONS` de sondagem antes de requisições não-simples). Isto é **A05 — Security Misconfiguration**. Topologia: origem-vítima (`vulnerable` :8034, `fixed` :8134) e origem-atacante (Item 1); as duas origens distintas e o `fetch` credenciado. Trilha: Burp (mostra o tell) + browser (prova o exploit).
2. **Spot the bug.** Mostrar o `after_request` do `vulnerable/app.py` — ele **reflete** a `Origin` do request em `Access-Control-Allow-Origin` + `Allow-Credentials: true`. Apontar que o `/account` está **logicamente correto** (autentica, vê o cookie, devolve o dado) — o bug é a **política de CORS**. Pergunta de auditoria: *"este servidor diz ao navegador QUAL origem pode ler a resposta — e ele responde 'sim' pra qualquer origem que pergunta, com credenciais?"* → sim (reflete). Foreshadow do fix: uma **allowlist de correspondência exata**.
3. **The tell (Burp — a origem refletida; OBRIGATÓRIO, ANTES do exploit no browser).** `GET /account` com `Origin: http://<atacante>` → a resposta reflete `Access-Control-Allow-Origin: http://<atacante>` + `Allow-Credentials: true`. Nomear: a **má config**. **Explicar** que `curl`/Burp leem o corpo de qualquer jeito (CORS não é controle do servidor) — o tell mostra a config errada, **não** é a prova do impacto. Contraste imediato: no fixed, a mesma request **não reflete** a origem do atacante.
4. **Exploitation (browser — o `fetch` credenciado; a prova é A lendo o dado).**
   - **4a — baseline (same-origin):** a vítima loga (`POST /login`) e acessa o próprio `/account` — vê o dado. Same-origin: a SOP nem entra; funciona idêntico nos dois lados.
   - **4b — a página do atacante:** um `fetch('http://<vítima>:8034/account', { credentials: 'include' })`. Explicar `credentials:'include'` (manda o cookie da vítima) e por que um `GET` simples **não** dispara preflight.
   - **4c — disparar:** com a vítima **logada** na origem-vítima, abrir a página do atacante (origem de A) → o JS faz o `fetch` credenciado → o navegador anexa o cookie da vítima → a origem-vítima responde com a má config → o navegador **libera a leitura** → **A exibe o dado privado da vítima** (saldo/perfil). **Exfiltração cross-origin autenticada.**
   - **§8 (cravar):** lab **isolado** (tudo loopback); dados dummy; nada destrutivo.
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'".
6. **Impact (honesto — sem overclaim).** Ver "Impacto honesto".
7. **Why the fix works (porta 8134).** Repetir contra o `fixed/`:
   - A **MESMA** página do atacante (agora apontando pro :8134) → o navegador dispara o `fetch` e **ainda anexa o cookie** → mas a resposta **não reflete** a origem de A (a allowlist não a inclui) → o navegador **BLOQUEIA a leitura** → o JS de A recebe um **erro de CORS** e **nada de dado**. **Cravar:** o cookie **ainda viajou** — mas o navegador não expôs a resposta ao script, porque a política de CORS não liberou aquela origem.
   - **Prova de isolamento:** o acesso **same-origin** (a vítima na própria conta) e o acesso de um **parceiro legítimo** (se modelado, Item 3) funcionam nos **dois** lados; **só** o `fetch` **cross-origin do atacante** separa vulnerable (lê) de fixed (bloqueado).
   - **A lição do diff:** o fix é a **allowlist de correspondência exata** (nota #1), **NÃO** checar substring/sufixo (nota #2), **NÃO** só tirar credenciais (nota #3), **NÃO** usar `*` (nem funciona com credenciais — nota #4); impacto = exfiltração (LER), contraste com 23 (ENVIAR) (nota #5). (Forward pro DIFF.)

**Sem** seção de exercícios/variações e **sem** "trilha browser secundária" (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Requests/responses/dado exfiltrado são **placeholders** da execução real capturada na Fase 2 (o tell real no Burp, o dado real exibido por A, o erro de CORS real no fixed). Explicar por que o Burp mostra o tell mas a prova exige o browser (CORS é controle do navegador).

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5) — os QUATRO/CINCO

Isola a causa e desmonta os mal-entendidos vizinhos (os do brief):

- **(a) NÃO é "faltou autenticação".** O endpoint **EXIGE o cookie e o VÊ** — a autenticação funciona (a vítima logada lê a própria conta). O furo é **liberar a LEITURA** da resposta pro atacante, via a política de CORS. *(Prova de isolamento: o acesso same-origin lê o dado idêntico nos dois lados; só o `fetch` cross-origin do atacante separa.)*
- **(b) NÃO é CSRF (o 23).** CSRF faz o navegador **ENVIAR** uma escrita cega (o atacante **não lê** a resposta — a SOP o cega); aqui o atacante **LÊ** dado autenticado. **Operação oposta na SOP** (enviar vs ler). *(Contraste com o `23`, publicado — a tabela: as duas metades da SOP.)*
- **(c) NÃO é "o `*` é o perigo".** O `*` literal **nem funciona** com credenciais — o navegador **recusa** combinar `Access-Control-Allow-Origin: *` com `Allow-Credentials: true`. O vetor autenticado é a **REFLEXÃO** da origem (uma origem específica devolvida, que o navegador aceita com credenciais). *(É por isso que a reflexão existe: driblar a recusa do `*`.)*
- **(d) NÃO é injection nem bug de código do endpoint.** A lógica do `/account` está **correta** (autentica, vê o cookie, devolve o dado). A falha é a **POLÍTICA de CORS** (configuração) — por isso é **A05 — Security Misconfiguration**, não um bug de lógica.
- **(e) NÃO é vazamento server-side.** `curl`/Burp **sempre** leem a resposta (CORS não é controle do servidor). O que a má config quebra é a proteção que o **NAVEGADOR** daria à vítima — a SOP no lado da leitura. Por isso o tell é visível no Burp, mas a **prova** exige o browser.

**O que É (prova):** o servidor instrui o navegador (pelos cabeçalhos CORS) a **liberar a leitura** da resposta autenticada pra **qualquer** origem (refletindo a `Origin` + `Allow-Credentials: true`); uma vítima logada que visita o site do atacante tem o dado privado **lido** pelo script do atacante. A correção é uma **allowlist de correspondência exata** de origens confiáveis.

---

## Impacto honesto

**Exfiltração de dado autenticado cross-origin** — o atacante **LÊ** a resposta privada da vítima (perfil/saldo) que a SOP deveria ter bloqueado. **Sem overclaim:** é **leitura**, não escrita — **NÃO** inflar pra "account takeover"/"controle da conta" (não há escrita aqui; isso é o eixo do `csrf-basic` (23), a outra metade da SOP), **NÃO** inflar pra RCE. O **teto** é o que o endpoint autenticado devolve (o dado privado exposto). **Contraste com o 23** (as duas metades da SOP: 23 = envio/escrita cega; 34 = leitura/exfiltração). A **prova do lab** é o dado da vítima aparecendo na página do atacante (vulnerable) e o erro de CORS (fixed). A classe "misconfiguration" tem **outras faces** (outros defaults/estados de configuração perigosos) — **descrição de UMA linha da classe**, **sem** modelar nem nomear átomo/variante/técnica futura (foreshadow, Nota 2). Sem foreshadow.

---

## Renderização / "um átomo = uma vuln"

**TEM HTML/JS na origem-atacante** (a página com o `fetch` credenciado — o exploit é client-side, como 21/23; o browser é **obrigatório** pra provar o mecanismo, §3.3 exceção client-side). A origem-vítima é **API-only JSON** (sem HTML próprio — a "UI" que ensina é o `fetch` do atacante lendo a resposta). Garantir que a **ÚNICA** lição é a **política de CORS** refletir qualquer origem + credenciais:

- **`POST /login` e `GET /account` NÃO são a vuln.** São o palco (estabelecer a sessão, devolver o dado a quem deveria). A **única** superfície é a **política de CORS** no `after_request`.
- **O `fixed` muda SÓ a política de CORS** (reflexão → allowlist exata). O `/account`, o `POST /login`, os imports, o estado da conta são **idênticos**. A anticolisão de cookie (Item 1) é **plumbing**, **não** delta de segurança.
- **A página do atacante NÃO tem vuln.** É o palco cross-origin; sem segunda superfície injetável.
- **Sem datastore, sem segunda superfície, sem segredo real** (`secret_key` dummy; dados de conta fake). Estado da conta em memória.
- **JS mínimo no atacante** — só o `fetch` credenciado + exibir o resultado (Item 4). É a **entrega do exploit** (client-side), não uma segunda superfície causal; §3.3 permite JS quando o exploit **é** client-side (como 21/23).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/cors`** — a página conceitual de CORS (título/grafia esperados: **"Cross-origin resource sharing (CORS)"**, abertura "What is CORS?"). Ela cobre **exatamente** o que o átomo modela: **reflexão de origem**, **`Access-Control-Allow-Credentials`**, e **o problema do `*`** — fit **limpo**. É a página de introdução da vuln, não a de labs.
- **Provavelmente NÃO precisa de fallback OWASP** (diferente do `debug-enabled` (33), onde a metade RCE ficava fora da Academy). O tópico de CORS da PortSwigger cobre a classe inteira deste átomo.
- **Texto do link:** **"Cross-origin resource sharing (CORS)"** — a forma que a própria PortSwigger usa. Preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7).
- **NÃO inventar URL nem grafia** — confirmar por fetch na Fase 2.

---

## A trilha e a ferramenta — browser na trilha principal, Burp apoia (mostra o tell)

O exploit é **client-side** (o navegador é quem obedece CORS); **a prova exige o browser**. Disciplina (`CLAUDE.md` §3.3, exceção client-side):

- **Burp APOIA (mostra o tell):** mandar `GET /account` com `Origin: http://<atacante>` e ver a resposta **refletir** a origem + `Allow-Credentials: true` (vulnerable) / **não refletir** (fixed). O Burp **planta e manipula** as requests (encoding, Repeater, o cabeçalho `Origin`).
- **Browser PROVA (executa o exploit):** a vítima logada → a página do atacante faz o `fetch` credenciado → A **lê e exibe** o dado (vulnerable) / recebe **erro de CORS** (fixed). O browser **observa a execução** (a leitura liberada/bloqueada).
- **Cravar que `curl`/Burp NÃO são a prova (risco #6):** eles leem o corpo **ignorando** os cabeçalhos CORS (não são navegadores) — o que mostram é o **tell** (a config errada), **não** o impacto (o script cross-origin conseguindo ler). **O que caracteriza a vuln é o NAVEGADOR obedecer o cabeçalho e liberar a leitura pro script do atacante.**
- **SEM** ferramenta offline, **SEM** cracker, **SEM** listener OOB. Multi-container, tudo loopback.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A05 — Security Misconfiguration** (`atoms/A05-security-misconfiguration/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `cors-wildcard` em A05; `CLAUDE.md` §4 fixa a pasta (irmãos XXE 18/30, debug-enabled 33). Situar em A05 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Topologia | **MULTI-CONTAINER — 2 origens** (`victim` vulnerable+fixed + `attacker`) | Molde do `23`: as origens **NÃO** se falam server-to-server (browser media) → **sem rede interna/`depends_on`/healthcheck**. |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe** (uso-direto-do-antipadrão, como 20/32) | Refletir-a-origem + `Allow-Credentials:true` É o antipadrão ingênuo. *(A plumbing de origens exige cuidado — Item 1 —, mas não é "ferramenta que resiste".)* |
| Coração técnico | **REFLEXÃO da origem + credenciais** (o `*` literal é só beat de ensino) | O `*` literal + `Allow-Credentials` o navegador **recusa** → só vaza dado público. A reflexão dribla a recusa → roubo autenticado. |
| Lição-coração | **SOP bloqueia a LEITURA cross-origin; CORS relaxa por cabeçalho; refletir qualquer origem + credenciais libera a leitura pro atacante. Fix = allowlist EXATA (ou não pôr CORS).** | O bug é a política instruir o navegador a liberar a leitura pra quem não devia. |
| Sub-lição crítica | **A causa é a POLÍTICA (refletir qualquer origem + credenciais), NÃO "faltou auth" nem "o dado é sensível"** | O endpoint autentica e vê o cookie; o furo é o navegador ser instruído a liberar a leitura. |
| Contraste central | **`csrf-basic` (23)** — as duas metades da SOP: 23 = ENVIO (escrita cega), 34 = LEITURA (exfiltração) | Justifica o átomo. Mesma fronteira de origem, sentidos opostos. |
| Contraste de apoio | **`18`/`30` (XXE) + `33` (debug-enabled)** irmãos A05 (parser vs framework/deploy vs política HTTP); **`21`** molde de browser/headless; **`32`** voz atual; **`01`** molde Flask | Publicados; ancoram a lição/voz/sub-forma. Sem foreshadow. |
| Eixo pedagógico | **CORS é controle do BROWSER — curl/Burp leem qualquer resposta; a prova exige o navegador** | O que separa o tell (Burp) da prova (browser). |
| Tipo de átomo | **Origem-vítima API-only JSON; origem-atacante HTML+JS (exploit client-side)** | O browser é obrigatório (CORS é controle do navegador). Como 21/23. |
| Trilha | **browser (PRINCIPAL, prova o exploit) + Burp (APOIA, mostra o tell)** | §3.3 exceção client-side: o navegador obedece CORS; curl não reproduz a prova (Nota 3-A). **Sem** trilha secundária. |
| Flavor — **TRAVADO** | **`POST /login` (cookie) + `GET /account` (dado privado) com CORS refletindo a origem; atacante faz `fetch` credenciado e LÊ** | A ÚNICA superfície é a política de CORS. `/account` correto. Sem 2ª superfície. |
| Payload-prova — **TRAVADO** | **`fetch(vítima, {credentials:'include'})` → A LÊ e exibe o dado privado** (vulnerable); **erro de CORS, nada de dado** (fixed) | Prova = A exibindo o dado (exfiltração). Benigno, dados fake, loopback (§8). |
| O "tell" (Burp) | **`GET /account` com `Origin: http://<atacante>` → resposta reflete `Access-Control-Allow-Origin` + `Allow-Credentials:true`** | Sinal da má config; mostrar ANTES do exploit. Fixed: não reflete. Não é a prova (curl lê de qualquer jeito). |
| Código vulnerable | **`after_request` reflete `request.headers.get("Origin")` + `Allow-Credentials:true`** | Reflete qualquer origem → o navegador libera a leitura pro atacante. |
| Código fixed | **allowlist de correspondência EXATA** (`origin in ALLOWED_ORIGINS`) | Só libera origens confiáveis; o atacante não está na lista → navegador bloqueia. |
| Forma dos cabeçalhos — **Item 2** | **`after_request` à mão (recomendado); flask-cors só se explícito/legível** | Cabeçalho **visível no código** ensina a causa. Ethos do repo (HMAC/token à mão do 20/23). |
| `app.py` vuln × fixed | **DIFERE só na política de CORS** (reflexão → allowlist) | O delta é a política; `/account`, login, imports idênticos. |
| Config de cookie vuln × fixed | **IDÊNTICA de SEGURANÇA** (`SameSite=None; Secure`); só nome/hostname difere (Item 1) | A política de CORS é o **único** delta de segurança. |
| Fix (único eixo) | **REFLEXÃO → allowlist de correspondência EXATA** (ou não pôr CORS) | Correção na raiz. NÃO substring/sufixo (#2), NÃO só tirar creds (#3), NÃO `*` (#4). |
| Impacto | **Exfiltração de dado autenticado cross-origin (LER).** Sem overclaim (não é escrita/takeover/RCE). | Honesto; teto = o que o endpoint devolve. Contraste com 23 (ENVIAR). Sem foreshadow. |
| Theory primer | **PortSwigger "Cross-origin resource sharing (CORS)"** (`/web-security/cors`, confirmar por fetch) | Cobre reflexão + credenciais + `*`. Fit limpo; provável sem fallback OWASP. Não inventar. |
| Título (H1) | **`cors-wildcard — Cross-origin resource sharing (CORS) misconfiguration`** (classe, sem stack) | `CLAUDE.md` §5. "CORS" é o nome da classe (aceitável); slug qualifica. Sem "Flask"/"Python". Grafia final na Fase 2. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública); **sem** "fecha a A05" | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release. Publicados 01/18/21/23/30/31/32/33 OK. |
| Portas | **8034 / 8134** (origem-vítima, bind `127.0.0.1`); atacante = Item 1 | `CLAUDE.md` §8. Multi-container, molde do 23. |
| **Item 1 — topologia de origens** | **ABERTO — VOCÊ DECIDE/PROVE NA FASE 2** (rumo: hostnames distintos resolvendo pra loopback; NÃO só portas) | Cookie ignora porta → só-porta compartilha o pote e falseia a demo. Resolução DNS offline no headless = risco. Se nada reproduzir offline, PARAR. |

---

## O container

**`victim/vulnerable/Dockerfile`, `victim/fixed/Dockerfile`** (API-only → **SEM `COPY templates`**) e **`attacker/Dockerfile`** (**COM** `COPY templates` — tem HTML), molde dos irmãos:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# (attacker also: COPY templates ./templates)
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

**`docker-compose.yml`** (candidato — molde do `23`: **SEM rede interna, SEM `depends_on`, SEM healthcheck**; as origens **não** se falam; a Fase 2 gera o real e confirma o Item 1):

```yaml
services:
  vulnerable:
    build: ./vulnerable      # victim origin, vulnerable
    ports:
      - "127.0.0.1:8034:5000"
  fixed:
    build: ./fixed           # victim origin, fixed
    ports:
      - "127.0.0.1:8134:5000"
  attacker:
    build: ./attacker        # attacker origin (HTML+JS). Port/hostname scheme = Item 1.
    ports:
      - "127.0.0.1:8080:5000"   # candidate -- binding stays literal 127.0.0.1 if a distinct
                                # hostname (Item 1) resolves to loopback; Phase 2 confirms.
```

- **Sem `networks:`, sem `depends_on`, sem healthcheck** — as origens **não se falam** (Nota de planning 4, molde do 23). O browser media todas as requests cross-origin.
- **§8:** todos os bindings em **loopback**. Origem-vítima **só** em `127.0.0.1` (8034/8134). Origem-atacante = Item 1 (se hostname distinto resolvendo pra loopback, binding permanece literal `127.0.0.1`).
- **Confirmar na Fase 2** que `./atom up cors-wildcard` sobe os serviços e que o esquema de origens (Item 1) resolve offline no headless com **potes de cookie separados**.

---

## DECISÃO ABERTA pra Fase 2 — a topologia de origens (o nó técnico; registrar, NÃO travar)

A **topologia de origens / hostnames** (Item 1 da seção "Decisões abertas") é o **nó técnico** deste átomo — comportamento de **navegador + DNS** que deve ser **PROVADO rodando** (**NÃO** é preferência editorial). Resumo do que confirmar (candidato registrado no Item 1):

- **O esquema de hostnames distintos que resolve pra loopback** (candidatos: `localtest.me` subdomínios / `.localhost` / alias em `/etc/hosts` ou `--host-resolver-rules` do Chromium), com **resolução OFFLINE** garantida dentro do container do navegador headless.
- **Potes de cookie SEPARADOS:** o cookie da vítima viaja no `fetch` credenciado pra origem-vítima **e NÃO vaza** pra origem-atacante; e `vulnerable`↔`fixed` **não se contaminam** (nomes de cookie distintos — precedente do 23 — ou hostnames distintos por lado).
- **O binding permanecendo literal `127.0.0.1`** (se os hostnames resolverem pra loopback) — vantagem sobre o `127.0.0.2` do 23.
- **A forma dos cabeçalhos CORS** (Item 2 — `after_request` à mão recomendado), a **allowlist do fixed** (Item 3 — parceira ou própria origem), a **forma da exfiltração** (Item 4), o **preflight** (Item 5).

**Protocolo (cravar):** registrar candidato, **rodar** num browser headless real, confirmar; capturar o **request/response real** (o tell no Burp; o dado exfiltrado por A no vulnerable; o erro de CORS no fixed). **Se não reproduzir**, ajustar dentro do escopo travado (**reflexão + credenciais no vulnerable; allowlist exata no fixed**) — trocar o esquema de hostnames, a via de resolução DNS offline, a anticolisão de cookie — e **PROVAR rodando**. **Se NADA reproduzir offline, PARAR e avisar o mantenedor — NÃO inventar** o tell, o dado exfiltrado, o comportamento do navegador, ou a resolução DNS.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–5 são os centrais; 6–12 são higiene/isolamento. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes — **exceto o Item 1 (topologia de origens, marcado VOCÊ DECIDE), que fecha na Fase 2 por probe.**

1. **Baseline (os dois lados).** A vítima loga (`POST /login`), o cookie de sessão é setado, e o acesso **same-origin** a `GET /account` devolve o dado dela — **idêntico** no vulnerable **e** no fixed. **VALIDAR.**
2. **O TELL (Burp — VALIDAR, capturar).** `GET /account` com `Origin: http://<atacante>` → a resposta reflete `Access-Control-Allow-Origin: http://<atacante>` + `Access-Control-Allow-Credentials: true` (vulnerable); no **fixed**, **NÃO** reflete a origem do atacante. **CAPTURAR** as duas respostas.
3. **O EXPLOIT (browser — VALIDAR RODANDO headless; item frágil).** Vítima logada (cookie semeado na origem-vítima) + página do atacante faz `fetch(vítima, {credentials:'include'})` → A **LÊ e exibe** o dado privado da vítima no **vulnerable** (:8034). **CAPTURAR** a cadeia real (login → cookie → página do atacante → dado exfiltrado). **Se não reproduzir, PARAR e avisar — NÃO inventar** prova.
4. **FIXED (browser — VALIDAR RODANDO).** O **MESMO** `fetch` → o navegador **BLOQUEIA** a leitura (erro de CORS) → A **não recebe dado**. **CAPTURAR** o erro de CORS + a ausência do dado. Confirmar que o **cookie da vítima ainda viaja** na requisição (mas o navegador não expõe a resposta ao script).
5. **Prova de isolamento.** O acesso **same-origin** (vítima na própria conta) — e, se modelado (Item 3), o de um **parceiro legítimo** — lê o dado **IDÊNTICO** nos dois lados; **só** o `fetch` **cross-origin do atacante** separa vulnerable (lê) de fixed (bloqueado). A diferença traça **PURO** à política de CORS. **VALIDAR.**
6. **`curl`/Burp NÃO são a prova.** Um `curl`/Repeater a `/account` **lê o corpo ignorando CORS** (não é navegador) — isso mostra o **tell**, **não** o exploit. Confirmar que a demo do impacto é **browser-mediada** e **registrar por que curl não é a prova** aqui (Nota 3-A).
7. **Uma vuln só.** Só a **política de CORS**; `POST /login` e `GET /account` **não** são a vuln (o endpoint autentica e está correto); o `fixed` muda **só** a política de CORS; a página do atacante **não** tem vuln. **Confirmar por `diff`.**
8. **Topologia de origens / cookie (Item 1 — VOCÊ DECIDE; VALIDAR RODANDO).** Confirmar o esquema de **hostnames distintos** que (a) o browser trata como **cross-origin**, (b) resolve **OFFLINE** no headless, (c) mantém **potes de cookie separados** (o cookie da vítima **não vaza** pra origem-atacante; `vulnerable`↔`fixed` não se contaminam). **PROPOR o esquema que funcionar. Se NADA reproduzir offline, PARAR e avisar.**
9. **Config de cookie byte-idêntica de SEGURANÇA** entre `vulnerable` e `fixed` (`SameSite=None; Secure` nos dois; a anticolisão do Item 1 — nome/hostname — é **plumbing**); o **ÚNICO delta de segurança** no `app.py` é a **política de CORS** (o `after_request`).
10. **§8.** Dados de conta **dummy** (perfil/saldo fake), `secret_key` dummy, tudo **loopback**; nada destrutivo; nada exposto à rede. **Se** o esquema de hostnames mantiver o binding literal `127.0.0.1`, **sem** desvio a documentar (vantagem sobre o `127.0.0.2` do 23); senão, registrar o desvio (§8/isolamento).
11. **Preflight (Item 5).** Confirmar se o `fetch` credenciado a `GET /account` dispara preflight (candidato: **não** — GET simples); se disparar, tratar o `OPTIONS` consistentemente nos dois lados. **Definir "preflight" no WALKTHROUGH de qualquer forma.**
12. **Theory primer** confirmado **por fetch** (`/web-security/cors`, título "Cross-origin resource sharing (CORS)"). Provável **sem** fallback OWASP. Se em dúvida, perguntar ao mantenedor. **Não inventar.** Confirmar a **grafia exata do H1**.

**Bloqueante remanescente:** nenhum de decisão de vuln. **O Item 1 (topologia de origens) fecha na Fase 2 por probe** — não é pendência de design, é "propor o que funcionar rodando". **Pendências de Fase 2 (não bloqueantes agora):** provar a dança origens-distintas/cookie-credenciado/leitura-liberada num browser headless offline (itens 2–5, 8); a forma dos cabeçalhos (Item 2); a allowlist do fixed (Item 3); a forma da exfiltração (Item 4); o preflight (Item 5/11); confirmar a URL/H1 do primer por fetch (item 12); confirmar o pin do Flask por probe; gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo e o `csrf-basic` (23) são **as duas metades da Same-Origin Policy** — o 23 quebra a SOP no **envio** (escrita cega), o 34 quebra na **leitura** (exfiltração). Cada beat deve poder ser lido com o **`23`** aberto ao lado (o **CONTRASTE central** + o **molde estrutural** do multi-container/browser-principal/headless). **Abrir e fechar** na lição-coração: *a SOP bloqueia a leitura cross-origin; CORS relaxa por cabeçalho; refletir qualquer origem + credenciais libera a leitura pro atacante; o fix é a allowlist de correspondência exata (ou não pôr CORS).*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`23` (csrf-basic) INTEIRO** (molde central — multi-container sem comunicação server-to-server, browser na trilha principal, validação headless com cookie persistente; contraste ENVIAR↔LER), **`33` (debug-enabled)** e **`18`/`30` (XXE)** (irmãos A05 — enquadramento "A05 — Security Misconfiguration" + contraste de sub-forma), **`21` (xss-dom)** (exceção de browser + técnica headless), **`32` (crypto-ecb-mode)** (voz/estrutura ATUAL — abertura seca, definir termo, título=classe, headers PT, honestidade-em-camadas), **`01` INTEIRO** (molde canônico Flask + estrutura de doc), esta spec. **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar "trilha browser secundária", encenação, nem arqueologia OWASP; **headers de seção traduzidos em TODA doc PT** (§7); título = classe sem stack.
- **PONTO PEDAGÓGICO OBRIGATÓRIO (o brief):** o WALKTHROUGH **DEVE** (1) mostrar o **"tell" no Burp** (a origem refletida + `Allow-Credentials` na resposta) **E** explicar por que isso sozinho **não** é a prova (curl lê de qualquer jeito); (2) provar o impacto **NO NAVEGADOR** (o script do atacante LENDO o dado autenticado — o que a SOP deveria bloquear); (3) mostrar o **fixed BLOQUEANDO** a leitura no navegador (o erro de CORS); (4) **definir SOP/origem/CORS/os cabeçalhos/requisição-credenciada/preflight DO ZERO**; (5) cravar o **contraste com o 23** (ler vs enviar) e **por que o `*` não é o vetor com credenciais** (o navegador recusa `*` + creds; a reflexão dribla). **Sem esses cinco, o átomo não ensina a lição nem fica claro pro iniciante.**
- **O coração técnico (cravar): REFLEXÃO, não `*` literal.** O slug é `cors-wildcard`, mas o `*` literal **nem funciona** com credenciais (o navegador recusa) — o vetor autenticado é a **reflexão da origem** + `Allow-Credentials: true`. O `*` vira **beat de ensino** (nota #4 do DIFF). **NÃO** modelar o ataque em cima do `*` literal.
- **O ponto técnico frágil é a topologia de origens (Item 1 / riscos #3/#4/#8) — comportamento de navegador+DNS.** Fazer o exploit de verdade num browser headless e confirmar que reproduz **offline** com potes de cookie separados. **Se não reproduzir com o candidato, ajustar dentro do escopo travado (reflexão+creds no vulnerable; allowlist exata no fixed) — o esquema de hostnames, a resolução DNS offline, a anticolisão de cookie — e PROVAR rodando; se NADA reproduzir, PARAR e avisar — NÃO inventar** o tell, o dado exfiltrado, ou a resolução DNS.
- **Uma vuln só:** a **única** falha é a **política de CORS** (reflexão + credenciais). **O `/account` está correto** (autentica, vê o cookie, devolve o dado); **NÃO** modelar falha de auth, injection, leitura de arquivo, ou 2ª superfície; o `fixed` muda **SÓ** a política de CORS (reflexão → allowlist exata). A anticolisão de cookie (Item 1) é **plumbing**, não delta de segurança. **SEM 2ª superfície.**
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é a **allowlist de correspondência EXATA**, **NÃO** "checar substring/sufixo" (armadilha #2 — `endswith` é contornável), **NÃO** "só tirar credenciais" (armadilha #3 — para o roubo autenticado mas dado público ainda vaza), **NÃO** "usar `*`" (nem funciona com credenciais — #4). **Ser honesto** (notas #2/#3/#4/#6): cada intuição tem valor/limite nomeado. "Não pôr CORS desnecessário" é conselho de superfície legítimo (nota #6), mas o átomo modela o caso em que ALGUM CORS é necessário (parceiro legítimo) e o fix é a allowlist.
- **Impacto honesto:** **exfiltração de dado autenticado cross-origin (LER)**; **NÃO** inflar pra account takeover (não há escrita — isso é o 23) nem RCE. O teto é o que o endpoint devolve. **Contraste com o 23** (ENVIAR vs LER). "Misconfiguration tem outras faces" só como **descrição da CLASSE** (uma linha), **sem** nomear átomo/variante/técnica futura.
- **`requirements.txt`** — Flask (pin candidato `Flask==3.0.0`, confirmar por probe); origem-vítima e atacante sem dependência pesada; **preferir `after_request` à mão** a `flask-cors` (cabeçalho visível — Item 2). Sem datastore, sem ORM.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** os quatro/cinco — **(a)** não é "faltou auth" (o endpoint autentica e vê o cookie; prova: same-origin idêntico nos dois lados); **(b)** não é CSRF (o 23 ENVIA cego; aqui LÊ — operação oposta na SOP); **(c)** não é "o `*` é o perigo" (o `*` nem funciona com creds; o vetor é a reflexão); **(d)** não é injection/bug do endpoint (a política é a falha — A05); **(e)** não é vazamento server-side (curl sempre lê; a má config quebra a proteção do NAVEGADOR).
- **Contraste com o 23 (cravar):** tabela (2 colunas: 23/34) + prosa; as duas metades da SOP (envio vs leitura). **Contraste com 18/30/33** (irmãos A05: parser vs framework/deploy vs política HTTP). **Molde de browser/headless: 21.** Citar `01`/`18`/`21`/`23`/`30`/`31`/`32`/`33` (publicados) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5 + o brief):** Same-Origin Policy (SOP), origem (esquema+host+porta), CORS, `Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials: true`, requisição credenciada (`credentials:'include'`), preflight (`OPTIONS`). **DO ZERO** — o átomo é denso de vocabulário; a SOP se define do zero mesmo tendo aparecido no 23 (lá pelo lado do envio; aqui pelo da leitura).
- **A05 sem arqueologia:** situar em **A05 — Security Misconfiguration**, explicar **por que** (política de resposta HTTP mal configurada — o servidor instrui o navegador a liberar a leitura cross-origin credenciada), **sem** contar edições OWASP antigas. **NÃO copiar** a nota de mapeamento "era A4 em 2017" do 18 (o 34 segue a regra atual, como 33/32).
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 candidato `cors-wildcard — Cross-origin resource sharing (CORS) misconfiguration`. "CORS" é o nome da classe (aceitável); "Flask"/"flask-cors"/"Python" no corpo, não no H1 (o slug já qualifica). Grafia final na Fase 2.
- **Política de referência cross-átomo:** OK citar **23** (contraste central + molde), **18/30/33** (irmãos A05), **21** (molde browser/headless), **32** (voz), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria/técnica futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase, "fecha a A05", ou outros A05 futuros. **Manter as proibições genéricas.** **Esta spec é pública — nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`cors-wildcard — Cross-origin resource sharing (CORS) misconfiguration`, grafia exata confirmável na Fase 2). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (CORS, SOP, origin, `Access-Control-Allow-Origin`, `Allow-Credentials`, preflight, credentialed, payload, cross-origin) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger CORS (`/web-security/cors`, "Cross-origin resource sharing (CORS)"), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar. Provável **sem** fallback OWASP.
- **A trilha é browser-principal + Burp-apoio:** Burp mostra o tell (origem refletida + `Allow-Credentials`), o browser prova o exploit (o `fetch` credenciado lendo o dado / bloqueado no fixed). **SEM** trilha browser secundária. Cravar que curl não é a prova (CORS é controle do navegador — Nota 3-A).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, no padrão das linhas anteriores (candidato — ajustar na Fase 2): `` Added atom 34: `cors-wildcard` — Cross-origin resource sharing (CORS) misconfiguration: an authenticated API endpoint returns private account data with a CORS policy that reflects the request's Origin back in Access-Control-Allow-Origin plus Access-Control-Allow-Credentials: true, so a logged-in victim who visits the attacker's page has the browser attach their cookie to a credentialed fetch and hand the private response to the attacker's script (cross-origin data exfiltration -- the read side of the Same-Origin Policy, opposite the send side in csrf-basic); the literal * wildcard does not work with credentials (the browser refuses it), so the vector is origin reflection, not *; the fix is an exact-match allowlist of trusted origins (or no CORS headers at all) (A05 Security Misconfiguration, CWE-942 candidate -- confirm). `` **Confirmar o CWE por fetch na Fase 2** (candidato: CWE-942 "Permissive Cross-domain Policy with Untrusted Domains"; não inventar). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 34 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline (same-origin idêntico nos dois lados) → o tell (Burp: origem refletida) → o exploit real (browser: o `fetch` credenciado lendo o dado da vítima no vulnerable) → o que a vuln NÃO é → fixed (erro de CORS, nada de dado). A prova exige um **browser real** com **cookies + fetch cross-origin** — **consultar a memória `validating-csrf-cross-site-headless`** (CDP com sessão/cookie persistente — o mesmo molde do 23: login → cookie → página do atacante → observar o resultado; aqui o resultado é o dado exfiltrado por A, lido via `--dump-dom`/avaliação de JS, **não** um `alert`). **Sem** browser não se prova (curl ignora CORS). Portas host podem não ser alcançáveis do sandbox — se preciso, ver a memória `validating-atoms-via-docker-exec` pro tell (Burp/HTTP), **mas o exploit exige o browser headless**.
- **Commits sem trailer `Co-Authored-By`** (a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8034` (vulnerable), `127.0.0.1:8134` (fixed); atacante = Item 1. Bind loopback. Multi-container (molde do 23), **sem rede interna/`depends_on`/healthcheck**.
- Se houver dúvida sobre a topologia de origens (Item 1), a resolução DNS offline no headless, a anticolisão de cookie, a forma dos cabeçalhos (Item 2), a allowlist (Item 3), a exfiltração (Item 4), o preflight (Item 5), a URL/H1 do primer, o CWE, o pin do Flask, ou se o exploit não reproduzir no browser, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos multi-origem/client-side):

- **`cors-reflection-not-wildcard-is-the-vector`** — *"O átomo `cors-wildcard` (34) entra em A05 (reaproveita `atoms/A05-security-misconfiguration/`): CORS misconfiguration via `after_request` que REFLETE `request.headers.get('Origin')` em `Access-Control-Allow-Origin` + `Allow-Credentials: true`. O coração: o `*` LITERAL não funciona com credenciais (o navegador RECUSA `*` + `Allow-Credentials`), então o vetor de roubo autenticado é a REFLEXÃO da origem (uma origem específica devolvida, que o navegador aceita com creds) — o `*` vira beat de ensino. MULTI-CONTAINER (victim vulnerable :8034 + fixed :8134 + attacker), molde do `csrf-basic` (23): as origens NÃO se falam (browser media) → SEM rede interna/depends_on/healthcheck. Browser na trilha principal (CORS é controle do NAVEGADOR — curl/Burp leem qualquer resposta ignorando CORS; o Burp mostra o TELL — origem refletida + `Allow-Credentials` —, mas a prova exige o browser). Fix = allowlist de correspondência EXATA (`origin in ALLOWED_ORIGINS`), NÃO endswith/substring (contornável: evil-banco.com, banco.com.evil.com), NÃO só tirar creds (dado público ainda vaza), NÃO `*`. Contraste com 23: as DUAS metades da SOP — 23 quebra no ENVIO (escrita cega), 34 quebra na LEITURA (exfiltração). Prova = o dado da vítima aparecendo na página do atacante num BROWSER real com cookie persistente (validação headless-CDP, molde do 23). NÓ técnico ABERTO na Fase 2: topologia de origens por HOSTNAMES distintos resolvendo pra loopback (não por porta — cookie ignora porta e compartilha o pote), com resolução DNS OFFLINE no headless (localtest.me vs .localhost vs /etc/hosts). Só Flask; sem datastore."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall pra futuros átomos multi-origem/client-side. Sua decisão. *(Ortogonal: as memórias relevantes na Fase 2 são `validating-csrf-cross-site-headless` — CDP com cookie persistente pro exploit —, `validating-atoms-via-docker-exec` — pro tell via HTTP se as portas host não forem alcançáveis — e a convenção de commit sem o trailer `Co-Authored-By`.)*
