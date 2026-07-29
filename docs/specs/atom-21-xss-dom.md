# Spec — Átomo 21: `xss-dom`

> Documento de especificação para o Claude Code implementar o vigésimo-primeiro átomo do projeto `atomicvulns` (Fase 5 — ver `ROADMAP.md`). Este átomo é **um átomo da Fase 5** (posição e demais átomos da fase no `ROADMAP.md` — a única superfície do repo autorizada a listá-los) e entra numa **categoria que JÁ EXISTE — A03 (Injection)**: a pasta `atoms/A03-injection/` já contém `sqli-union-basic`, `sqli-blind-boolean`, `sqli-blind-time`, `xss-reflected`, `xss-stored`, `command-injection-basic` e `ssti-jinja`. O 21 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos, ex.: a pasta do `xss-reflected`). Versionamento/release da fase é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER, molde do `01 sqli-union-basic` / `02 xss-reflected` / `08 xss-stored`** — só `vulnerable` + `fixed`, sem serviço extra, sem listener, sem rede especial.
>
> **A lição em uma linha:** no **DOM-based XSS** a falha vive **inteira no JavaScript do cliente** — um trecho de JS lê um **source** controlável pelo atacante e o escreve num **sink** perigoso sem tratar. Aqui o source é `location.hash` (o **fragmento** `#…` da URL) e o sink é `element.innerHTML`. Como o fragmento **NÃO é enviado na request HTTP**, o payload **nunca chega ao servidor** — o servidor entrega uma página limpa e completa, e o payload só entra **depois**, quando o próprio JS da página lê o hash e joga em `innerHTML`. `innerHTML` pede ao browser que **PARSEIE** a string como HTML: ele constrói o DOM e dispara event handlers embutidos (ex.: `<img src=x onerror=…>`), executando JS do atacante. O fix é usar uma API que **NÃO parseia HTML** (`textContent`), **no CLIENTE**.
>
> **NÃO há "Saída B" aqui** (como no `19 ssti-jinja` e no `20 deserialization-pickle`). O antipadrão — JS do cliente lendo `location.hash` e escrevendo em `innerHTML` — é **diretamente** o bug; não existe uma ferramenta padrão que "resista" e obrigue a modelar um componente especial. O átomo é **uso-direto-do-antipadrão**. **NÃO inventar uma Saída B.**
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — trilha primária Burp, **MAS com a EXCEÇÃO client-side que este átomo usa**: quando a prova exige **execução de JavaScript no browser**, o **browser faz parte da trilha PRINCIPAL** — Burp inspeciona/manipula requests, o browser observa a execução; **sem** trilha browser "secundária" redundante; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo técnico na 1ª ocorrência, situar em A03 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind `127.0.0.1`** e **ISOLAMENTO**, **payload benigno** (`alert`); e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico de HTML/estrutura single-container), o **`xss-reflected` (02)** e o **`xss-stored` (08)** publicados (os **dois irmãos XSS server-side** — o alvo do **CONTRASTE** central; ambos citáveis à vontade), e os **dois átomos publicados mais recentes — `ssti-jinja` (19)** e **`deserialization-pickle` (20)** (a **VOZ/estrutura ATUAL**: abertura seca, termo definido, título=classe, e o padrão da nota **"mencionável, não aplicada"** — sandbox/HMAC — que o 21 replica com **"escapar no servidor / CSP não é o fix"**).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição na fase (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A03 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** O `xss-dom` é **um átomo da Fase 5** — a posição na fase e os demais átomos da fase estão no `ROADMAP.md` (a única superfície do repo autorizada a listá-los). Os átomos 01–20 já estão `[x]` em `main`. Justificativa do ROADMAP para este átomo: *"DOM XSS é conceitualmente mais sutil (sink no JS do cliente, não no HTML do servidor) — fica pra depois dos outros XSS internalizados."*
>
> **A categoria A03 JÁ EXISTE — o 21 reaproveita a pasta.** Diferente do `15 session-fixation` (criou `A07-*`), do `18 xxe-basic` (criou `A05-*`) e do `20 deserialization-pickle` (criou `A08-*`), o 21 **não cria categoria**: `atoms/A03-injection/` já existe e já hospeda os dois irmãos XSS (`xss-reflected`, `xss-stored`) além dos quatro outros de injection. **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A03-injection/`** (confirmado também pelo `ls` da pasta atual). Pasta final: **`atoms/A03-injection/xss-dom/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A03 — Injection"**.
>
> **Rótulo A03 SEM arqueologia (`CLAUDE.md` §5, regra atual).** DOM-based XSS é **A03 — Injection** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria dos irmãos `xss-reflected`/`xss-stored`. **NÃO** relatar em que número XSS caía em edições antigas (em 2017 XSS era categoria própria, A7; **não contar isso** — é ruído histórico proibido pela regra atual). **Situar apenas: isto é A03 — Injection.** Explicar **por que** DOM XSS é injection (dado não-confiável vira código executável num sink — aqui, um sink de DOM no cliente) é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release da fase fica FORA desta spec

> Versionamento/CHANGELOG-tag/anúncio de release da fase é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar a versão, **NÃO** taggear, **NÃO** anunciar posição de fase. **CRÍTICO (FORESHADOW, §5):** o átomo se descreve **isolado** — **NÃO** anunciar a versão/release da fase, **NÃO** foreshadowar os próximos átomos da fase (listados só no `ROADMAP.md`) nem qualquer átomo futuro. O aluno que abre o átomo não deve ver nenhum gesto pra frente.

## Nota de planning 3 — convenções ATUAIS valendo (seguir o `CLAUDE.md` atual; NÃO copiar estilo antigo dos irmãos onde divergir)

> O `CLAUDE.md` foi atualizado ao longo do projeto e o 21 segue as regras **atuais**, iguais às do `19`/`20`. Ao ler irmãos como molde, seguir o **`CLAUDE.md` ATUAL**, não o exemplo dos átomos onde eles divergirem. Divergências concretas a **NÃO** copiar (crítico — os irmãos XSS `02`/`08` foram escritos sob o estilo antigo em pontos):
>
> - **§3.3 — trilha primária Burp COM a EXCEÇÃO client-side (o browser na trilha PRINCIPAL), mas SEM "trilha browser secundária".** O `08 xss-stored` (estilo antigo) descrevia uma **"trilha secundária opcional (browser-only)"** que reencena o ataque sem Burp. A regra **atual** do `CLAUDE.md` §3.3 **proíbe** essa trilha secundária redundante ("NÃO incluir uma 'trilha browser secundária' que apenas reencena o ataque com menos controle — é redundante"). No 21: **UMA trilha só, a principal**, que legitimamente usa **Burp + browser juntos** (Burp inspeciona/prova a rede; o browser planta-via-URL e observa a execução). **NÃO** criar uma seção "browser-only secundária". *(Detalhe DOM-específico na Nota de planning 3-A abaixo e na seção WALKTHROUGH.)*
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature e a falha. **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** DOM-based XSS, source, sink, fragment/`location.hash`, `innerHTML`/`textContent`, DOM — dar a expansão/definição na estreia. O átomo é pra quem **não** conhece a vuln.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra atual).** O H1 nomeia a **classe** ("DOM-based Cross-Site Scripting"), **NÃO** o mecanismo ("...via innerHTML"/"...em JavaScript"/"...via location.hash"). O **slug** (`xss-dom`) qualifica a variante — isso é OK (como `sqli-union-basic`). O motor (JS/`innerHTML`/`location.hash`) aparece no **corpo**, não no H1.
> - **A03 sem arqueologia** (Nota de planning 1).
> - **"What to read next" Burp+browser (não "Burp secondary").** READMEs antigos (02/08) ainda dizem `via Burp Suite (primary) and browser (secondary)` — resíduo do estilo antigo. No 21, o browser **não é secundário**: é parte **obrigatória** da trilha principal. Redigir sem o rótulo "secondary".

## Nota de planning 3-A — o papel do Burp neste átomo DIVERGE do stored XSS (08): aqui o Burp NÃO "planta" — INSPECIONA e PROVA

> **Sinalizado — sutileza DOM-específica, importante pra Fase 2.** O `CLAUDE.md` §3.3 descreve a divisão client-side como *"o Burp planta e manipula as requests … e o browser observa a execução"* — modelo do **stored XSS (08)**, onde o payload viaja num `POST /comment` que o Burp intercepta e repete. **No DOM XSS isso NÃO se aplica**, e a razão **É a própria lição**: o payload vive no **fragmento da URL** (`#…`), que o **browser nunca envia na request**. Logo o Burp **não tem uma request pra plantar o payload** — ele não vê o fragmento passar. O papel do Burp aqui é:
>
> 1. **INSPECIONAR** o `<script>` **na resposta servida** — ler o sink no JS que o servidor entrega (o `innerHTML` lendo `location.hash`).
> 2. **PROVAR** que o fragmento **NÃO aparece em NENHUMA request** — evidência direta, na rede, de que o servidor **não recebe** o payload (o que **distingue** DOM de reflected/stored).
>
> Quem **planta** o payload é o **browser** (navegando pra `/#q=<payload>` ou digitando no form, que escreve `location.hash`); quem **observa** a execução é o **browser** (o `alert` disparando). **Essa incapacidade do Burp de interceptar o payload numa request É, ela mesma, a prova de que o bug é DOM-based** — cravar isso no WALKTHROUGH. Continua sendo **trilha principal com Burp** (Burp é a lente de rede que prova a ausência do payload no tráfego); só que o verbo do Burp aqui é **inspecionar/provar**, não **plantar**. *(Registrar essa divergência do 08 explicitamente — é o que o prompt chamou de "Burp planta/inspeciona"; para o DOM, é inspeciona.)*

---

## Identidade

- **ID:** `xss-dom`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A03 — Injection**. Pasta `atoms/A03-injection/` (**JÁ EXISTE — o 21 reaproveita**). Confirmado contra o `ROADMAP.md` ("A03 Injection") e o `CLAUDE.md` §4. **Oitavo átomo de A03; terceiro XSS (par natural do `02`/`08`).** Em prosa, usar o nome da classe — **"DOM-based Cross-Site Scripting"** — e a categoria — **"A03 — Injection"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A03-injection/xss-dom/`
- **Número sequencial:** 21
- **Porta vulnerable:** `127.0.0.1:8021`
- **Porta fixed:** `127.0.0.1:8121`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos single-container 01/02/08/19/20.
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM** serviço extra, listener, mock, ou rede especial. Molde do 01/02/08.
- **Fase / milestone:** Fase 5 (ver `ROADMAP.md`). Versionamento/release da fase **fora desta spec** (Nota de planning 2). **No conteúdo do átomo, ZERO menção de posição de fase/release/próximos átomos** (§5 foreshadow).
- **Branch de trabalho:** `atom/xss-dom`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de DOM-based XSS** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/cross-site-scripting/dom-based`** (título esperado da página: **"DOM-based cross-site scripting"**; abertura conceitual sobre sources/sinks — `location.hash`/`innerHTML` são os exemplos canônicos da própria página). **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# xss-dom — DOM-based Cross-Site Scripting`** — `id` + nome canônico da **classe** em inglês (a forma paralela à dos irmãos: `02` usa "Reflected Cross-Site Scripting", `08` usa "Stored Cross-Site Scripting"). **SEM** "JavaScript"/"innerHTML"/"location.hash" no H1 (o slug já carrega a variante). Grafia canônica exata (hifenização de "DOM-based", capitalização) **confirmável na Fase 2** (casar com o título da página PortSwigger); **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**DOM-based Cross-Site Scripting — o source→sink vive INTEIRO no cliente.** Uma página tem uma "busca" cujo resultado é renderizado **pelo próprio JavaScript do browser**, lendo o **fragmento** da URL. O formato é `#q=<termo>`. Um trecho de JS na página lê `location.hash` (o **source**), extrai o `q`, e escreve `"You searched for: <termo>"` num elemento via `element.innerHTML` (o **sink**). Como o fragmento (`#…`) **não é enviado ao servidor**, o servidor entrega **sempre a mesma página limpa e estática**; o dado do atacante só entra **no browser, depois do load**, quando o JS lê o hash. Um termo forjado — `<img src=x onerror=alert(document.domain)>` — faz o `innerHTML` **parsear a string como HTML**, construir um `<img>`, falhar ao carregar `src=x`, disparar o `onerror` e **executar o JS do atacante**. Resultado: **XSS** — execução de JavaScript arbitrário no contexto de origem da página, no browser da vítima.

### A lição-coração

> **"No DOM-based XSS a falha vive INTEIRA no JavaScript do cliente: um trecho de JS lê um SOURCE controlável pelo atacante e o escreve num SINK perigoso sem tratar. Aqui o source é `location.hash` (o fragmento `#…` da URL) e o sink é `element.innerHTML`. Como o fragmento NÃO é enviado na request HTTP, o payload NUNCA chega ao servidor — o servidor entrega uma página limpa e completa, e o payload só entra depois, quando o próprio JS da página lê o hash e joga em innerHTML. innerHTML pede ao browser que PARSEIE a string como HTML: ele constrói o DOM e dispara event handlers embutidos (ex.: `<img src=x onerror=…>`), executando JS do atacante. O fix é usar uma API que NÃO parseia HTML (`textContent`), no CLIENTE."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** Três peças, todas do lado do cliente:

1. **O source é o fragmento — e o fragmento não vai pra rede.** A URL `http://127.0.0.1:8021/#q=<payload>` tem um **fragmento** (tudo depois do `#`). Por especificação, o browser **não envia** o fragmento na request HTTP — ele fica **só no browser**, acessível ao JS via `location.hash`. É por isso que o servidor **nunca vê** o payload: a request que chega ao Flask é um `GET /` limpo, sem o `#q=…`. *(Definir "fragmento" e `location.hash` na estreia.)*
2. **O sink é `innerHTML` — que parseia HTML.** `element.innerHTML = "..."` não escreve texto: pede ao browser pra **interpretar a string como HTML** e **construir o DOM** correspondente. Se a string tem `<img src=x onerror=alert(1)>`, o browser cria um elemento `<img>` real com um handler `onerror`; a imagem `src=x` falha, o `onerror` **roda**. É assim que markup vira execução — **sem** um `<script>` explícito.
3. **A PEGADINHA (cravar): `<script>` inserido via `innerHTML` NÃO executa.** Por decisão do HTML5, script tags inseridos no DOM **depois** do load via `innerHTML` **não rodam**. Então o payload **não pode** ser `<script>alert(1)</script>` — tem que ser um **event handler** (`<img src=x onerror=…>`, `<svg onload=…>`). *(Isto é exatamente o que os irmãos `02`/`08` já anteciparam nos seus asides sobre DOM XSS — ver "Contraste"; o 21 é onde essa lição aterrissa.)*

**Sub-lição CRÍTICA (cravar — é o coração do passo "o que a vuln NÃO é" e da nota #2 do DIFF).** **Escapar no servidor não conserta NADA**, porque o servidor **não vê o dado**. Ligar autoescape do Jinja, escapar a saída, filtrar no backend — tudo isso opera sobre dados que **passam pelo servidor**, e o fragmento **não passa**. A defesa tem que estar **onde o dado é USADO** — no cliente, trocando o sink perigoso (`innerHTML`) por um seguro (`textContent`). Esta é a intuição-armadilha que o átomo desarma: o aluno experiente pensa "é só escapar/autoescape/CSP" e **erra o alvo** porque o dado nunca cruza o servidor.

### Por que A03 (Injection)

DOM-based XSS é **A03 — Injection**, a mesma categoria dos irmãos `xss-reflected`/`xss-stored`. O eixo de injection é: **dado não-confiável cai num interpretador/sink que o trata como código**. No XSS o "interpretador" é o **HTML/JS parser do browser**, e o sink é onde o dado vira markup executável. No reflected/stored esse sink é a **saída HTML renderizada pelo servidor**; no DOM XSS o sink é uma **API de DOM no JavaScript do cliente** (`innerHTML`) que parseia HTML pós-load. Mesma família (input → sink que executa), mesmo teto de impacto (execução de JS no browser) — só muda **onde** o source→sink acontece (100% no cliente) e, por consequência, **onde mora o fix** (no cliente). Coerente com o caráter client-side desta vulnerabilidade.

---

## Contraste com o `02` (reflected) e o `08` (stored) — CRÍTICO (é o que justifica o átomo existir)

Os três são **XSS (A03)** e têm o **MESMO impacto** (execução de JS no browser da vítima). O que **difere** — e o que faz o 21 não ser "o 02/08 de novo" — é o **caminho source→sink** e **onde mora o fix**. Cravar no WALKTHROUGH e no DIFF:

| Eixo | `xss-reflected` (02) | `xss-stored` (08) | `xss-dom` (21) |
|---|---|---|---|
| **Categoria OWASP** | A03 — Injection | A03 — Injection | A03 — Injection |
| **Onde vive o source→sink** | o **servidor** reflete o input na resposta HTML | o input é **persistido** server-side e servido depois | **100% no cliente** — o JS lê `location.hash` e escreve no DOM |
| **O servidor vê o payload?** | **sim** — na query string (`?q=`) | **sim** — persistido no banco | **NÃO** — o fragmento (`#…`) não vai na request |
| **Sink** | Jinja `{{ q\|safe }}` (render do **servidor**) | Jinja `{{ body\|safe }}` (render do **servidor**) | `element.innerHTML` (JS do **cliente**) |
| **Onde mora o fix** | escape na **saída do servidor** (autoescape) | escape na **saída do servidor** (autoescape) | **no cliente** (`textContent`) |
| **Impacto** | XSS (JS no browser da vítima) | XSS (JS no browser da vítima) | XSS (JS no browser da vítima) |

**"Um átomo = uma vuln" se refere à CAUSA, não ao impacto** (`CLAUDE.md` §2). Assim como a trilogia SQLi (01/06/07) é "uma causa, três canais de exfil" e o par XSS server-side (02/08) é "uma causa, dois modelos de entrega", o **trio XSS** fecha com o 21 sendo **a mesma família por impacto, mas de causa/mecanismo/fix distintos**: no 02/08 o sink é o **render do servidor** (fix: escapar na saída server-side); no 21 o sink é o **DOM do cliente** (fix: trocar o sink no client JS). **Só o impacto coincide.** Citar `02` e `08` (publicados) à vontade — o aluno abre os três e compara: *"mesmo teto (JS no browser), mas o dado nem passa pelo servidor aqui, e o fix vive no cliente."*

**Gancho pedagógico dos asides já publicados (usar — é continuidade, não foreshadow).** Os WALKTHROUGHs do `02` e `08` **já contêm** um aside dizendo que, em DOM-based XSS, um `<script>` inserido via `innerHTML` pós-load **não** executa e o payload "falharia lá". O `xss-reflected` (Step 3) escreve: *"In a DOM-based XSS … browsers deliberately do not execute script tags inserted via `innerHTML` post-load. The exact same literal payload that wins here would silently do nothing there."* O 21 é **exatamente esse "there"** — a lição que os irmãos generalizaram agora aterrissa num átomo abrível. Como `02`/`08` estão **publicados**, o 21 pode **referenciá-los explicitamente** (referência pra **trás**, permitida por §5), fechando o trio: *"o reflected/stored te avisaram que `<script>` via innerHTML não dispara — aqui é onde isso importa, e por isso o payload é um event handler."*

---

## Uma vuln só — o foco é `innerHTML` lendo `location.hash`; página server-render ESTÁTICA; a prova é BENIGNA; o fix é CLIENT-SIDE

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é **`element.innerHTML` recebendo dado de `location.hash`** no JS do cliente. Garantias e sutilezas (todas validar na Fase 2):

- **A página que o servidor renderiza é ESTÁTICA — sem variável Jinja de input.** O `app.py` só faz `render_template("index.html")` **sem passar dado do usuário**; o template **não interpola nada controlável** (o `<script>` e o HTML são fixos). Logo **não existe sink server-side** — nem um segundo XSS possível pelo lado do servidor. O autoescape do Jinja está **ligado** (convenção), mas é **irrelevante** aqui: não há variável de input pra escapar. **A ÚNICA superfície é `location.hash` chegando ao `innerHTML` no cliente.** *(CUIDADO na Fase 2: se algum dia se adicionar uma variável Jinja ao template, ela tem que estar autoescapada — NUNCA `| safe` com input. O desenho recomendado é template 100% estático, sem variável de input, o que torna "uma vuln só" à prova de bala.)*
- **A prova de XSS é BENIGNA e contida (§8).** O payload dispara um `alert(document.domain)` — marcador universal e inofensivo que **prova execução** sem dano, sem rede real, sem sair do container/browser. Ver "Prova de execução".
- **`fixed` = trocar o SINK no CLIENTE (`innerHTML`→`textContent`), NÃO escapar no servidor.** O fix é **client-side**. O fixed **não** liga um filtro no backend, **não** escapa no Jinja, **não** adiciona CSP como "o fix" — isso seria a **defesa-armadilha** da nota #2 do DIFF (escapar no servidor não alcança um dado que nunca chega ao servidor). Ver "O fix" e DIFF nota #2.
- **Sem banco, sem segunda superfície, sem 2ª dependência.** Nenhum SQLite/`requests`/lib extra; nenhum PII real; **sem lib JS** (o `textContent` é dependency-free). A **única** superfície é o fragmento da URL.
- **Sem `<script>` cru como payload (a pegadinha).** O payload é **event handler** (`<img … onerror=…>`), porque `<script>` via `innerHTML` não executa. Confirmar na Fase 2 rodando no browser (item 4 do checklist).

---

## Flavor — busca client-side via fragmento da URL (TRAVADO)

Uma página com uma **"busca"** cujo resultado é renderizado **pelo próprio JS no browser**, lendo o fragmento. **Didático:** mostra que input não-confiável **não é só formulário nem query string** — é **qualquer coisa que o usuário controla**, incluindo o **fragmento da URL**, que **nem chega ao servidor**. O ponto **NÃO é a UI**; é o fragmento → `innerHTML`.

### Fluxo (endpoint único `GET /`, servidor estático)

- **`GET /`:** o servidor entrega **sempre a mesma página estática** (formulário de busca + um `<script>` que renderiza no cliente). **NÃO existe endpoint de busca no servidor** — isso **REFORÇA** que o servidor não vê o termo (a busca é 100% client-side).
- **No browser:** o `<script>` da página lê `location.hash` no **load** (e no evento **`hashchange`**), extrai `q` (candidato: `new URLSearchParams(location.hash.slice(1)).get("q")`), e renderiza `"You searched for: <termo>"` dentro de um elemento.
  - **VULNERABLE:** via `element.innerHTML` → um termo com markup (`<img … onerror=…>`) **executa** no browser.
  - **FIXED:** via `element.textContent` → o mesmo termo aparece como **texto literal inerte**; nada executa.
- **Como o dado entra no hash (duas vias, ambas client-side):**
  - **(a) Navegação direta** pra `http://127.0.0.1:8021/#q=<payload>` — é assim que um atacante entrega DOM XSS (um **link forjado**). **Esta é a via primária do walkthrough.**
  - **(b) O formulário** — um `<input>` cujo submit escreve `location.hash = "q=" + valor` (mantendo o dado no **cliente**, `return false` pra não submeter ao servidor). Torna a "feature" legível (uma caixa de busca visível) e demonstra, ao vivo, que o termo vira `#q=…` na URL (não uma query string) — o que **reforça** que o servidor não recebe. *(Opcional/`CONFIRMAR NA FASE 2`: o form é conveniência de contexto; o core é a navegação direta. Manter HTML MÍNIMO.)*

**Cada versão LÊ o hash da MESMA forma; o ÚNICO delta é `innerHTML`↔`textContent`.** O contraste `innerHTML` (parseia HTML) vs `textContent` (texto literal) **é o diff.**

**Sem endpoint de busca no servidor.** Não adicionar um `GET /search?q=` no Flask (seria uma 2ª superfície e viraria reflected). A busca é **só client-side** — e a **ausência** de um endpoint de servidor é parte da lição (o servidor não participa).

---

## Prova de execução — CONTIDA e INOFENSIVA (TRAVADO; §8)

A prova é o **JS do atacante EXECUTAR no browser**, de forma inofensiva e observável: um `alert`.

### Payload-prova escolhido: **`<img src=x onerror=alert(document.domain)>`**

O `<img>` tenta carregar `src=x` (um recurso inexistente), **falha**, e dispara o handler **`onerror`**, que roda `alert(document.domain)`. `document.domain` mostra a **origin** da página (`127.0.0.1`) — provando que o JS roda **no contexto de origem da página** (o que dá o impacto de XSS). A prova é:

- **No `vulnerable` (8021):** navegar pra `http://127.0.0.1:8021/#q=<img src=x onerror=alert(document.domain)>` → o **`alert` dispara** no browser.
- **No `fixed` (8121):** o **mesmo** hash → o payload aparece como **texto literal inerte** ("You searched for: `<img src=x onerror=alert(document.domain)>`") → o **`alert` NÃO dispara**.

**Por que event handler e NÃO `<script>` (a pegadinha a travar):** browser moderno **não executa** um `<script>` inserido via `innerHTML` pós-load (HTML5). Então `<script>alert(1)</script>` no hash **não** dispararia — daria a falsa impressão de "não é vulnerável". O payload correto é **event-handler-based** (`<img onerror>` / `<svg onload>`). **CONFIRMAR NA FASE 2, rodando no browser:** (a) o `<img src=x onerror=…>` **dispara** no vulnerable; (b) `<script>…</script>` via `innerHTML` **NÃO** dispara; (c) o payload EXATO (incluindo encoding do fragmento — ver "Notas de implementação") e a extração do `q`. **TRAVAR o payload exato** que dispara depois de rodar.

**Alternativa de cor (registrar, opcional):** `<svg onload=alert(document.domain)>` — dispara no parse do `<svg>` (não precisa de erro de carregamento). Bom fallback se algum detalhe do `<img onerror>` incomodar na Fase 2. **Primário: `<img src=x onerror=alert(document.domain)>`.**

**Regras §8, a cravar no WALKTHROUGH:**

- O payload é **benigno**: `alert(document.domain)` só **abre uma caixa de diálogo** — não lê dado real, não faz rede, não sai do browser/container. É um **marcador** de "executou", como o `alert` do `02`/`08`.
- **PROIBIDO** payload destrutivo, exfil real, keylogger, ou qualquer coisa fora do container/lab. O objetivo é **DEMONSTRAR execução**, com o **mínimo efeito**.
- O lab é **isolado** (bind **só** `127.0.0.1`, container descartável). O WALKTHROUGH deixa **explícito** que é um lab local e o payload é uma **prova de conceito benigna** — mesmo enquadramento do `02`/`08` (o `alert` é o marcador; num alvo real, XSS é roubo de sessão/DOM — mas os payloads ficam demonstrativos). A **escalada honesta** (roubo de cookie/sessão) é **descrita**, não armada (ver "Impacto honesto").

---

## O código — o coração no `<script>` do template (NÃO no `app.py`)

O `app.py` **não participa da vuln**: ele só serve a página estática. Toda a lógica da falha (e do fix) vive no `<script>` do `templates/index.html`.

### `app.py` — BYTE-IDÊNTICO entre `vulnerable` e `fixed` (candidato — Fase 2 gera o real)

```python
import os
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

- **Sem endpoint de busca, sem banco, sem estado.** O servidor só entrega a página. `render_template("index.html")` **sem contexto** — nenhuma variável de input interpolada (página estática, "uma vuln só").
- **`app.py` é idêntico nas duas versões** — o diff vive **só** no `<script>` do template.

### `vulnerable/templates/index.html` — o `<script>` com o sink `innerHTML` (candidato — Fase 2 gera o real)

```html
<script>
// Renders the search term from the URL fragment (#q=...). The fragment is a
// CLIENT-SIDE source: browsers never send it in the HTTP request, so the server
// never sees it.  source = location.hash  ->  sink = innerHTML.
// VULNERABLE: innerHTML parses the string as HTML -- it builds DOM and fires any
// event handler it carries (e.g. <img src=x onerror=...>), so a crafted fragment
// runs the attacker's JavaScript. The server delivered a clean page; the payload
// entered here, in the browser, after load.
function render() {
  var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
  document.getElementById("result").innerHTML = "You searched for: " + q;
}
window.addEventListener("hashchange", render);
render();
</script>
```

### `fixed/templates/index.html` — MESMO `<script>`, só troca o sink pra `textContent` (candidato)

```html
<script>
// Renders the search term from the URL fragment (#q=...). Same client-side source.
//   source = location.hash  ->  sink = textContent.
// FIXED: textContent writes the string as LITERAL TEXT -- the browser never parses
// it as HTML, so <img src=x onerror=...> shows up as inert characters, not an
// element, and nothing executes. The fix lives on the CLIENT, where the data is
// used -- escaping on the server would never reach it (the fragment never arrives).
function render() {
  var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
  document.getElementById("result").textContent = "You searched for: " + q;
}
window.addEventListener("hashchange", render);
render();
</script>
```

**Cada lado LÊ o mesmo `location.hash` da mesma forma; o ÚNICO delta de código é `innerHTML`↔`textContent`** (+ o comentário). O `app.py`, o resto do `index.html`, o `Dockerfile` e o `requirements.txt` são **byte-idênticos**.

### Heads-up estrutural — SINALIZADO (precisão de uma decisão travada)

> **O prompt cravou:** *"PRIMEIRA vez no repo que a causa/fix NÃO estão no app.py."* **Sinalizo uma precisão** (para o mantenedor confirmar), porque escrever isso literalmente seria **impreciso** e o átomo preza exatidão:
>
> - O `xss-reflected` (02) e o `xss-stored` (08) — os dois irmãos publicados — **também** têm `app.py` byte-idêntico com o bug vivendo **no template** (o `\|safe`). Então o 21 **NÃO é o primeiro** átomo cujo fix mora fora do `app.py`.
> - **O que É genuinamente inédito no 21 (e mais afiado):** é o **primeiro átomo em que o `app.py` (o código do servidor) não participa DE FORMA ALGUMA da vuln** — não recebe o input malicioso **nem** o renderiza. No 02/08 o `app.py` ainda segura o **source** (recebe a query / o corpo do POST), mesmo com o sink no template; **aqui o `app.py` nunca vê o payload**, porque o fragmento da URL não chega ao servidor. O fluxo source→sink inteiro (`location.hash` → `innerHTML`) vive no **browser**.
> - **Segunda distinção fina:** no 02/08 o sink é uma **expressão Jinja processada no servidor** (`{{ q\|safe }}` — uma decisão de autoescape server-side, com o dado passando pelo servidor); no 21 o sink é **JavaScript que o servidor emite verbatim e nunca interpreta**, executado no **cliente** pós-load.
>
> **Formulação recomendada para o DIFF/WALKTHROUGH** (em vez de "primeira vez fora do app.py"): *"o servidor não participa — nem vê o payload nem o renderiza; a causa e o fix vivem 100% no JavaScript do cliente."* O mantenedor confirma essa formulação na Fase 2. *(Mesmo espírito do 20 sinalizar a abreviação do nome de pasta A08: sigo a decisão, mas afio a redação pra não gravar imprecisão.)*

### Notas de implementação (validar/decidir na Fase 2)

- **Extração do `q` e encoding do fragmento.** Candidato: `new URLSearchParams(location.hash.slice(1)).get("q")` — casa com o formato `#q=<termo>` e é o jeito idiomático. **Confirmar na Fase 2** que a extração entrega o payload íntegro ao `innerHTML` (o browser pode percent-encodar partes do fragmento ao navegar; `URLSearchParams` decoda `%XX`/`+`). Se o payload exato não sobreviver limpo ao round-trip, **fallback**: extração por substring simples (ex.: `decodeURIComponent(location.hash.replace(/^#q=/, ""))`), aplicada **idêntica** nos dois lados (o diff continua sendo só `innerHTML`↔`textContent`). **Travar a forma exata rodando no browser.**
- **`render()` roda no load e no `hashchange`.** `render()` no fim do `<script>` cobre o caso "navegou direto pra `/#q=<payload>`" (dispara no load); o listener de `hashchange` cobre "mudou o hash com a página aberta" (form/barra de endereço). Confirmar que **ambas** as vias renderizam.
- **O form (opcional) escreve `location.hash` no cliente.** Se incluído: `onsubmit="location.hash = 'q=' + <valor>; return false;"` — o `return false` impede o submit ao servidor (o dado fica no cliente). **NÃO** transformar num `GET` de servidor (viraria reflected). Confirmar que digitar o payload no form também dispara (via `hashchange`).
- **`document.getElementById("result")`** — o alvo do render é um `<p id="result">` (ou `<div>`) vazio no HTML. Presente e idêntico nos dois templates.

---

## O fix e o tipo de diff

**Fix:** trocar o **SINK no CLIENTE** — **`element.innerHTML` → `element.textContent`**. Tipo de diff: **lógica-diferente** — **UMA linha** no `<script>` do template (o comentário acompanha). `textContent` escreve a string como **texto literal**: o browser **não parseia** como HTML, então `<img … onerror=…>` vira caracteres inertes visíveis, não um elemento. O `app.py` é **byte-idêntico**; o resto do `index.html`, o `Dockerfile` e o `requirements.txt` também. **O servidor não muda em nada** — a vuln e o fix vivem 100% no cliente.

Diff colável (candidato — a Fase 2 gera o real):

```diff
   function render() {
     var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
-    // VULNERABLE: innerHTML parses the string as HTML and fires embedded handlers.
-    document.getElementById("result").innerHTML = "You searched for: " + q;
+    // FIXED: textContent writes literal text; the browser never parses it as HTML.
+    document.getElementById("result").textContent = "You searched for: " + q;
   }
```

**O CONTRASTE é o diff (obrigatório):** `innerHTML` (parseia HTML → executa event handlers) vs `textContent` (texto literal → nada executa). **A única mudança é o sink, no cliente.**

### Notas obrigatórias no `DIFF.md`

1. **NADA MUDA NO SERVIDOR — a vuln e o fix vivem 100% no cliente (pedido explícito do mantenedor; deixar CRISTALINO).** O `app.py` é **byte-idêntico** nos dois lados; o diff é **só** a linha do `<script>` (`innerHTML`→`textContent`). Prova de isolamento: um termo **benigno** (`#q=laptop`) renderiza "You searched for: laptop" **igual** nos dois apps (a **feature é idêntica**); só um termo com **markup/event handler** separa os dois — o vulnerable **executa** (o `alert` dispara), o fixed **não** (o payload vira texto inerte). **Cravar a formulação afiada** (heads-up estrutural, seção "O código"): o servidor **não participa** — não vê o payload (o fragmento não chega) nem o renderiza; source (`location.hash`) e sink (`innerHTML`) vivem no **JS do cliente**. *(Isto contrasta com o `02`/`08`, onde o `app.py` ao menos segura o source e o sink é render do servidor.)*
2. **ESCAPAR NO SERVIDOR / AUTOESCAPE DO JINJA NÃO É O FIX (nota-ADVERTÊNCIA curta mas DIDÁTICA — "mencionável, não aplicada").** Enquadrar explicitamente, no molde do 19 ("A sandbox is not the fix") / 20 (HMAC):
   - **(a) Nomear a intuição.** O aluno experiente vai pensar: *"é XSS — é só escapar no servidor / ligar autoescape do Jinja / botar uma CSP e resolve"*.
   - **(b) Mostrar que NÃO alcança.** O payload chega pelo **`location.hash`**, que **nunca é enviado ao servidor** — o Jinja **não vê o dado** (a página que ele serviu é limpa e estática). Escapar/filtrar no backend opera sobre dados que **passam pelo servidor**; este **não passa**. A defesa server-side **erra o alvo**.
   - **(c) Cravar: a defesa tem que estar onde o dado é USADO — no cliente** (trocar o sink pra `textContent`). *(CSP — Content Security Policy, um header que restringe o que a página pode executar — pode ser citada **en passant** como **defense-in-depth** valiosa: uma CSP bem feita limita o estrago de um XSS que escape, mas **não é a causa nem o root fix**, e uma CSP frouxa não pega `onerror` inline. Mencionar, **não** aplicar como "o fix".)* **CURTA** (a intuição + o porquê), **NÃO** uma seção gigante.
3. **DADOS vs COMPORTAMENTO: `textContent` escreve caracteres LITERAIS; `innerHTML` manda o browser CONSTRUIR DOM.** `textContent` **nunca parseia** — a string vira texto visível, ponto. `innerHTML` pede ao browser pra **interpretar** a string como HTML, construir o DOM e **disparar event handlers** embutidos. Por isso a troca fecha o bug: sem parsing, não há elemento nem handler. *(Se um app real **precisar** renderizar HTML do usuário — ex.: um editor rich-text — o caminho é **sanitizar** com uma lib dedicada, ex.: **DOMPurify**, que remove markup perigoso antes do `innerHTML`. **Mencionar como alternativa, NÃO aplicar** — o fix do lab é `textContent`, dependency-free, porque a "busca" só precisa de texto.)*
4. **IMPACTO XSS; contraste com reflected (02) e stored (08): mesmo impacto, causa e fix no cliente.** O impacto é **execução de JS arbitrário no contexto de origem da página** → roubo de cookie/sessão, requests autenticadas no contexto da vítima, manipulação do DOM, exfil do conteúdo da página. **Mesmo teto** dos irmãos XSS (`02`/`08`), mas **causa** (sink no DOM do cliente, não render do servidor) e **fix** (client-side `textContent`, não escape server-side) **diferentes**. Referir a tabela da seção "Contraste com o 02 e o 08". **Sem foreshadow** (não nomear átomos/variantes futuras).

---

## Biblioteca / mecanismo

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask** (casando com 01/02/08/19/20). O JS do template é **vanilla, sem lib** (`innerHTML`/`textContent`/`URLSearchParams`/`addEventListener` são APIs nativas do browser). **Sem banco, sem `requests`, sem 2ª dependência, sem lib JS.**
- **NÃO é behavior-critical.** O comportamento do átomo — `innerHTML` parsear HTML e disparar `onerror`; `<script>` via `innerHTML` **não** rodar; `textContent` não parsear — é **estável** em todos os browsers modernos (spec HTML5). Pin normal (`Flask==3.0.0`) basta. **Confirmar rodando no browser na Fase 2** (itens 3–5 do checklist).
- **JS permitido AQUI por exceção do `CLAUDE.md` §3.3.** JS é proibido por padrão nos átomos, **exceto** onde o JS **é o código causal da falha** — DOM XSS é o caso exemplar. O `<script>` de render é a **causa**; o `onsubmit` do form (se incluído) é plumbing mínimo. **JS cru, sem framework, no mínimo absoluto.**

---

## WALKTHROUGH — abertura seca; browser na trilha PRINCIPAL (§3.3 EXCEÇÃO client-side)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (busca client-side via fragmento) e a falha (o JS lê `location.hash` e joga em `innerHTML`). Trilha **principal única**: **Burp + browser juntos** — o Burp **inspeciona a resposta servida e prova que o fragmento não vai pra rede** (Nota de planning 3-A); o **browser planta-via-URL e observa a execução** (o `alert`). **NÃO** criar uma "trilha browser secundária" (proibida pela §3.3 atual).

**Abertura (candidato — plantar a lição, seco):**

> *A página faz uma busca no cliente: você põe um termo no fragmento da URL (`#q=…`) e um JavaScript que já está na página o lê e escreve "You searched for: <termo>" na tela. O termo **nunca sai do browser** — o fragmento é a parte da URL depois do `#`, e o browser **não o envia** na request HTTP. Então o servidor devolve **sempre a mesma página estática**; o termo de busca só entra **depois**, quando o próprio JavaScript da página lê o fragmento e o joga no documento com `innerHTML`. `innerHTML` pede ao browser pra **parsear** essa string como HTML — inclusive qualquer event handler que ela carregue. Ponha um `<img src=x onerror=…>` no fragmento e o browser constrói o elemento, a imagem falha ao carregar, e o `onerror` roda o seu JavaScript.*

Beats (molde do 19/20 publicado — abertura seca, seções numeradas `## 1..7`):

1. **Context.** Página de "busca" client-side: `GET /` entrega uma página estática (form + `<script>` de render). Definir na estreia: **DOM-based XSS** (Cross-Site Scripting em que o source→sink vive **inteiro** no JavaScript do cliente, sem passar pelo servidor), **source** (a entrada controlável — aqui `location.hash`), **sink** (o ponto perigoso onde o dado é usado — aqui `innerHTML`), **fragment / `location.hash`** (a parte da URL depois do `#`, que o browser **não envia** ao servidor), **`innerHTML`** (API que **parseia** a string como HTML e constrói DOM), **`textContent`** (API que escreve **texto literal**, sem parsear), **DOM** (Document Object Model — a árvore de objetos da página que o JS manipula). Isto é **DOM-based XSS**, sob **A03 — Injection**. Sem banco, sem segundo serviço: `vulnerable` em `127.0.0.1:8021`, `fixed` em `127.0.0.1:8121`. Trilha: Burp (inspeciona/prova a rede) + browser (planta-via-URL e observa).
2. **Spot the bug.** Mostrar o `<script>` de `vulnerable/templates/index.html` — a linha `document.getElementById("result").innerHTML = "You searched for: " + q`, com `q` vindo de `location.hash`. Pergunta de auditoria: *"esse `q` vem do fragmento da URL, que EU controlo — e `innerHTML` parseia HTML e dispara event handlers?"* → **sim**. Notar que **o `app.py` é limpo**: o servidor só serve a página estática; o bug está **inteiro** no JS do cliente. Grep barato pra esta classe: procurar sinks de DOM recebendo `location`/`document.URL` (ex.: `grep -rn 'innerHTML\|location.hash\|document.write' .`). Foreshadow do fix: trocar o sink por um que **não parseie HTML**.
3. **Exploitation (browser planta-via-URL; a prova é o `alert`).**
   - **Baseline (feature benigna):** navegar pra `http://127.0.0.1:8021/#q=laptop` (ou digitar `laptop` no form) → a página mostra "You searched for: laptop". A busca funciona; o termo veio do **fragmento**, renderizado **no cliente**.
   - **Montar o payload (event handler, não `<script>`):** explicar a pegadinha — `<script>…</script>` inserido via `innerHTML` pós-load **não** executa (HTML5), então o payload é um **event handler**: `<img src=x onerror=alert(document.domain)>`. O `<img>` falha ao carregar `src=x` e dispara o `onerror`.
   - **Disparar:** navegar pra `http://127.0.0.1:8021/#q=<img src=x onerror=alert(document.domain)>` → o **`alert` dispara** no browser, mostrando `127.0.0.1` — **JS do atacante rodando no contexto de origem da página**. *(O mesmo dispara se o payload for digitado no form, via `hashchange` — mas a navegação direta é o modelo de entrega real: um link forjado.)*
   - **§8 (cravar):** lab **isolado** (bind só `127.0.0.1`); o `alert` é **benigno** (só uma caixa de diálogo — sem rede, sem dano). Num alvo real, esse mesmo primitivo rouba sessão/manipula a página — **manter os payloads demonstrativos** (`alert`), nunca armar exfil real. *(Espelhar o enquadramento do `02`/`08`.)*
4. **O papel do BURP (SUPORTE dentro da trilha principal — inspecionar e PROVAR a rede; Nota de planning 3-A).**
   - **Inspecionar o sink na resposta servida:** com o Proxy do Burp ligado, visitar `http://127.0.0.1:8021/` e ler, na resposta, o `<script>` que o servidor entrega — **o sink no JS entregue** (`innerHTML` lendo `location.hash`). O Burp mostra o **código causal** chegando ao browser.
   - **PROVAR que o fragmento NÃO vai pra rede:** navegar pra `/#q=<payload>` e olhar o **HTTP history** do Burp — a request que sai é um **`GET /` limpo**, **sem** o `#q=…`. O servidor **nunca recebe** o payload. **Essa ausência é a assinatura do DOM XSS** (e o motivo de o Burp não ter uma request pra "plantar" o payload, diferente do reflected/stored). Cravar: *"o Burp confirma, na rede, o que a teoria diz — o payload vive só no browser."*
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **NÃO é reflected (02).** O servidor **não reflete nada** — a página servida é estática e idêntica, com ou sem payload; a URL do `GET /` na rede está **limpa** (sem query string). Não há eco de um parâmetro na resposta do servidor. *(Prova: o Burp history do Step 4 — o payload não está em request nenhuma.)*
   - **NÃO é stored (08).** **Nada é persistido** — não há banco, o payload não sobrevive a um reload sem estar de novo no hash. Ele vive só na URL do momento.
   - **NÃO é um bug de escape no servidor (a sub-lição CRÍTICA).** A página que o servidor entrega é **limpa** e o dado **nunca passa pelo servidor** — então **escapar no servidor / autoescape do Jinja / CSP não alcançam**: não há o que escapar do lado que nunca vê o dado. A defesa tem que estar **onde o dado é usado**, no cliente. *(Sintoma vs causa — ver DIFF nota #2.)*
   - **O que É (prova):** o JS do cliente lê um source que **VOCÊ** controla (`location.hash`) e o joga num sink que **parseia HTML** (`innerHTML`) — DOM XSS, source→sink inteiro no browser. A **única** correção é usar um sink que **não parseia** (`textContent`), no cliente.
6. **Impact (honesto — sem overclaim).** **XSS — execução de JavaScript arbitrário no contexto de origem da página, no browser da vítima.** Um atacante entrega um **link forjado** (`…/#q=<payload>`); quem clica executa o JS no contexto da página — roubo de cookie/sessão, requests autenticadas como a vítima, manipulação do DOM, exfil da página. É o **mesmo teto** dos irmãos XSS (`02`/`08`), por **causa distinta** (sink no DOM do cliente, não render do servidor). Sem overclaim, sem foreshadow.
7. **Why the fix works (porta 8121).** Repetir contra o `fixed/`:
   - O **MESMO hash** (`#q=<img src=x onerror=alert(document.domain)>`) → o `<script>` do fixed usa **`textContent`** → o payload é escrito como **texto literal**: a página mostra visivelmente "You searched for: `<img src=x onerror=alert(document.domain)>`" e **nada executa** (o `alert` **não** dispara).
   - **A lição do diff:** o fix troca o **sink no cliente** (`innerHTML`→`textContent`), que **não parseia HTML**. **Escapar no servidor NÃO é o fix** (nota #2 — o dado nunca chega lá); **dados vs comportamento** (nota #3 — `textContent` escreve literal, `innerHTML` constrói DOM); **mesmo impacto do 02/08, causa/fix no cliente** (nota #4). A feature (busca benigna) fica **intacta** nos dois: `#q=laptop` → "You searched for: laptop" idêntico.

**Sem** seção de exercícios/variações e **sem** "trilha browser secundária" (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado; a trilha principal já usa o browser). Payloads/screens/prova do `alert` são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**XSS (Cross-Site Scripting) via DOM-based sink.** O atacante entrega um link forjado com o payload no fragmento (`http://…/#q=<img src=x onerror=…>`); ao abrir, o JS da própria página lê o fragmento e o joga em `innerHTML`, e o JS do atacante **executa no contexto de origem da página** — no browser da vítima. Poder disso: ler/roubar cookies não-HttpOnly (sequestro de sessão), fazer requests autenticadas no contexto da vítima, manipular o DOM (defacement, phishing in-page), exfiltrar o conteúdo da página. É o **impacto máximo de XSS**, o **mesmo teto** do `xss-reflected` (02) e do `xss-stored` (08), por **causa distinta** (sink no DOM do cliente vs render do servidor). **Sem overclaim** (não inflar pra "comprometimento do servidor" — DOM XSS roda no browser da vítima, não no servidor; é aí que está o poder e o limite). **Sem foreshadow** (não citar átomos/variantes/categorias futuras). A **prova do lab é benigna** (`alert`); a escalada (roubo de sessão) é **descrita**, não armada (§8).

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A03 — átomo dentro de família publicada; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`xss-reflected` (02) e `xss-stored` (08)** — o contraste **central** (seção dedicada + tabela). Mesmo impacto (XSS), causa/mecanismo/fix diferentes (render do servidor vs sink no DOM do cliente; fix server-side vs client-side). **Fechar o trio XSS.** Usar o **gancho dos asides já publicados** (02/08 avisaram que `<script>` via innerHTML não dispara em DOM XSS — o 21 é onde isso aterrissa). Referência pra **trás**, permitida.
- **`sqli-union-basic` (01), `command-injection-basic` (09), `ssti-jinja` (19)** — família "dado não-confiável cai num sink que o executa" (injection, A03). Citáveis **opcionalmente** pra ancorar que XSS é injection e o eixo é source→sink; **não** central. O contraste que importa é com o 02/08.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante futura** por número, nome **OU** descrição — inclusive os **próximos átomos da fase** (listados só no `ROADMAP.md`, nunca no conteúdo), **outros sinks/sources de DOM XSS** modelados como átomo futuro, ou a posição/release de fase.
- **PROIBIDO anunciar "abre a fase"/"primeiro átomo".** O átomo se descreve **isolado** (Nota de planning 2). O aluno não vê nenhuma menção de fase/release/próximos átomos.
- **Que existam outros sources (ex.: `document.referrer`, `postMessage`) e outros sinks (ex.: `document.write`, `eval`) é, no máximo, descrição conceitual de UMA LINHA** ("DOM XSS existe com outros sources e sinks — o padrão é o mesmo: um source controlável caindo num sink que executa") — **sem** nomear átomo/variante futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 21 vai até **XSS via `innerHTML` lendo `location.hash`** (o finding), provado pelo `alert` benigno. **Uma vuln, uma causa (sink de DOM no cliente), um fix (`textContent`, no cliente).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/cross-site-scripting/dom-based`** — a página conceitual de DOM-based XSS (título esperado **"DOM-based cross-site scripting"**, abertura "What is DOM-based XSS?" com os conceitos de **sources** e **sinks**; `location.hash`/`innerHTML` são os exemplos que a própria página usa). É a página de introdução da vuln, não a de labs. Paralela às dos irmãos (`.../reflected`, `.../stored`).
- **Texto do link:** **"DOM-based cross-site scripting (XSS)"** — forma paralela à do `02` ("Reflected cross-site scripting (XSS)") e do `08` ("Stored cross-site scripting (XSS)"). Preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `sqli-union-basic`/`xss-reflected`/`xss-stored`).

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (a página de busca, com o `<script>` causal — não API-only; e o browser é **obrigatório** pra provar a execução, §3.3 exceção client-side). Garantir que a **ÚNICA** lição é `innerHTML` lendo `location.hash`:

- **Página server-render ESTÁTICA — sem variável Jinja de input.** `render_template("index.html")` **sem contexto**; o template não interpola nada controlável. **Não há sink server-side** → **impossível um 2º XSS pelo servidor**. Autoescape do Jinja **ligado** (default), mas **irrelevante** (não há variável de input pra escapar). *(Se a Fase 2 adicionar qualquer variável Jinja, ela DEVE estar autoescapada — SEM `| safe` com input. Recomendado: template 100% estático, sem variável de input.)*
- **A ÚNICA superfície é `location.hash` → `innerHTML`** no JS do cliente. Sem banco, sem 2ª superfície, sem endpoint de busca no servidor.
- **`fixed` = trocar o sink no CLIENTE (`textContent`), NÃO escapar no servidor** (a defesa-armadilha da nota #2). A correção é **client-side**.
- **Payload benigno e contido** (§8): `alert(document.domain)`. A execução fica no browser/lab isolado.
- **`<script>` cru NÃO é o payload** (a pegadinha): payload é event handler (`<img … onerror=…>`). Confirmar na Fase 2.

---

## HTML — `templates/index.html` (mínimo, molde do 01/02; com `<script>` causal)

Molde do `sqli-union-basic`/`xss-reflected`: `<!doctype>`, banner de aviso **obrigatório**, ≤40 linhas, ≤5 linhas de CSS inline, **sem** frameworks. **Exceção `CLAUDE.md` §3.3: TEM `<script>` — o JS é o código causal da falha** (DOM XSS); JS cru, sem lib, no mínimo. Dica de Burp no rodapé. **O `index.html` difere entre vulnerable e fixed em UMA linha** (`innerHTML`↔`textContent`). Candidato (a Fase 2 finaliza o texto exato; versão vulnerable — a fixed só troca `innerHTML` por `textContent`):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Search</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Search</h1>
<form onsubmit="location.hash = 'q=' + document.getElementById('q').value; return false;">
  <label>Query: <input type="text" id="q" autofocus></label>
  <button type="submit">Search</button>
</form>
<p id="result"></p>
<script>
// source = location.hash  ->  sink = innerHTML (see WALKTHROUGH/DIFF)
function render() {
  var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
  document.getElementById("result").innerHTML = "You searched for: " + q;
}
window.addEventListener("hashchange", render);
render();
</script>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- **Banner de aviso obrigatório** no topo. **≤40 linhas** (o esboço tem ~27). **CSS ≤5 linhas** inline.
- **`<form>`** com `onsubmit` que escreve `location.hash` no cliente (`return false` — não submete ao servidor). Torna a feature legível e mostra o termo virando `#q=…` na URL. *(Opcional — o core é a navegação direta; confirmar na Fase 2.)*
- **`<p id="result">`** vazio — alvo do render.
- **`<script>`** com o sink (`innerHTML` na versão vulnerable). **JS cru, sem framework.**
- **Rodapé padrão** com a dica do Burp *(ajustar na Fase 2 se a redação "work from Burp Repeater" soar estranha pra um átomo onde o Repeater não é o palco — o Burp aqui inspeciona/prova; a redação exata do rodapé é confirmável, mas manter o banner e a dica de "abrir com o Burp ligado")*.

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` — molde do `sqli-union-basic`/`xss-reflected` (**com** `COPY templates`). **Nenhuma** linha extra (sem `apt`, sem banco, sem plantar arquivo). Só Flask via pip.

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

**`docker-compose.yml`** (candidato — molde do 01/02/08, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8021:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8121:5000"
```

**Sem `networks:`, sem serviço extra.** Molde simples do 01/02/08. **§8:** bind **só** `127.0.0.1`.

---

## Bibliotecas

**`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask.** APIs de browser (`innerHTML`/`textContent`/`URLSearchParams`/`addEventListener`) são nativas — **sem lib JS**. **Sem** banco, `requests`, ou 2ª dependência.
- **Pin normal, NÃO behavior-critical:** o comportamento do átomo é do **browser** (spec HTML5 estável), não de uma versão de lib Python. Fixar (`Flask==3.0.0`) e **confirmar rodando no browser** na Fase 2 que o payload dispara.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A03 — Injection** (`atoms/A03-injection/`, **JÁ EXISTE — reaproveitar**) | ROADMAP linha 125 lista `xss-dom` em A03; `CLAUDE.md` §4 fixa a pasta. Oitavo A03, terceiro XSS. Situar em A03 **sem arqueologia**. |
| Posição na fase | Ver `ROADMAP.md` | Fase 5; 01–20 já `[x]`. Release da fase **fora da spec/conteúdo** (Nota 2). |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Molde do 01/02/08. Sem serviço extra/listener/mock/rede. |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe** (como no 19/20) | JS lendo `location.hash`→`innerHTML` é diretamente o bug. Uso-direto-do-antipadrão. **NÃO inventar Saída B.** |
| Lição-coração | **DOM XSS: source (`location.hash`) → sink (`innerHTML`) 100% no cliente; o servidor não vê o dado; fix = trocar o sink pra `textContent`, no cliente.** | O bug é o **sink de DOM no cliente**, não algo no servidor. Escapar no servidor não alcança. |
| Contraste central | **`xss-reflected` (02) + `xss-stored` (08)** — XSS por caminho/fix DIFERENTES (render do servidor vs sink no DOM) | Fecha o trio XSS. Justifica o 21 não ser "o 02/08 de novo". "Um átomo = uma vuln" = causa, não impacto. |
| Flavor — **TRAVADO** | **Busca client-side via fragmento** (`#q=<termo>`, renderizado no cliente; sem endpoint de busca no servidor) | Superfície = o fragmento, que **nem chega ao servidor** — reforça a lição. Input não é só form/query string. UI mínima. |
| Payload-prova — **TRAVADO (confirmar exato na Fase 2)** | **`<img src=x onerror=alert(document.domain)>`** (`<svg onload=…>` como cor) | Event handler (não `<script>`, que via innerHTML não dispara — a pegadinha). `alert` benigno (§8). |
| Código vulnerable | **`el.innerHTML = "You searched for: " + q`** (`q` de `location.hash`) | `innerHTML` parseia HTML → dispara event handlers → XSS. |
| Código fixed | **`el.textContent = "You searched for: " + q`** | `textContent` escreve texto literal; não parseia HTML; nada executa. |
| `app.py` vulnerable × fixed | **Byte-idêntico** (só faz `render_template` da página estática) | O bug/fix vivem **só** no `<script>` do template. Servidor não participa. |
| Onde vive a causa/fix — **SINALIZADO** | **100% no cliente**; o **servidor não vê nem renderiza o payload** (formulação afiada, não "primeira vez fora do app.py" — 02/08 também têm app.py idêntico) | Precisão: 02/08 seguram o *source* no app.py; aqui o app.py **nunca vê** o payload. Mantenedor confirma a redação. |
| Fix (único eixo) | **Trocar o SINK no cliente (`innerHTML`→`textContent`)** | Correção **client-side**, onde o dado é usado — não escapar/CSP no servidor (defesa-armadilha da nota #2). |
| Diff | **Lógica-diferente** — UMA linha no `<script>` (`innerHTML`↔`textContent`); `app.py` byte-idêntico | A linha perigosa é `innerHTML`. Servidor não muda em nada. |
| Escapar no servidor / CSP | **NÃO aplicar** (nota-advertência #2, "mencionável, não aplicada") | O dado (fragmento) nunca chega ao servidor; Jinja/CSP não alcançam. Como sandbox (19)/HMAC (20). CSP en passant como defense-in-depth. |
| Sanitizar HTML (DOMPurify) | **Mencionar, NÃO aplicar** (nota #3) | Se um app *precisa* de HTML do usuário, sanitiza; aqui a busca só precisa de texto → `textContent`, dependency-free. |
| Página server-render | **Estática, sem variável Jinja de input** | Sem sink server-side → impossível 2º XSS pelo servidor. Autoescape ligado mas irrelevante. |
| Bibliotecas | **`Flask==3.0.0`** (pin normal) + vanilla JS (sem lib) | APIs de browser nativas. Sem banco. JS permitido (código causal, §3.3). Confirmar payload dispara no browser. |
| Impacto | **XSS.** Mesmo teto do 02/08, causa/fix no cliente. | Honesto; roda no browser da vítima; sem overclaim; sem foreshadow. |
| Theory primer | **PortSwigger DOM-based XSS** (`/cross-site-scripting/dom-based`, confirmar por fetch) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Trilha | **Burp + browser (trilha PRINCIPAL única)**; Burp **inspeciona/prova a rede** (não planta — Nota 3-A), browser **planta-via-URL e observa** | `CLAUDE.md` §3.3 exceção client-side. **Sem** trilha browser "secundária" (proibida pela regra atual). |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. |
| Título (H1) | **`xss-dom — DOM-based Cross-Site Scripting`** (classe, sem stack) | `CLAUDE.md` §5. Slug carrega a variante; H1 não leva "JavaScript"/"innerHTML"/"location.hash". |
| Foreshadow | **ZERO pra frente** | `CLAUDE.md` §5. Não nomear próximos átomos (só no `ROADMAP.md`)/posição de fase/release/outros sources-sinks como átomo futuro. |
| Portas | **8021 / 8121** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–8 são os centrais; 9–12 são higiene técnica. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /`** entrega a página estática; a busca benigna (`#q=laptop`) renderiza "You searched for: laptop" via JS (no load e via form).
2. **A feature funciona** nos dois lados: hash → render no cliente; **`hashchange` re-renderiza** (mudar o hash com a página aberta dispara `render()`).
3. **O ATAQUE (central — VALIDAR RODANDO NO BROWSER):** navegar pra `http://127.0.0.1:8021/#q=<img src=x onerror=alert(document.domain)>` → o JS **EXECUTA** (o `alert` dispara) no vulnerable. **Capturar** o payload, a URL e a prova (o `alert`) reais. **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** prova.
4. **A PEGADINHA (VALIDAR RODANDO):** confirmar que **`<script>…</script>` via `innerHTML` NÃO dispara** (pra justificar o payload event-handler) e que **`<img src=x onerror=…>` dispara**. **TRAVAR o payload exato** (e `<svg onload=…>` como fallback se preciso).
5. **FIXED (8121):** o **MESMO** hash → **`textContent`** renderiza o payload como **texto literal inerte**; o **`alert` NÃO dispara**. **Capturar a diferença** (mesma URL, execução vs texto).
6. **Prova de isolamento:** o termo **benigno** (`#q=laptop`) → "You searched for: laptop" **idêntico** nos dois; só o malicioso separa. Confirmar que a **feature é a mesma** e só o sink diverge.
7. **O caminho source→sink:** confirmar que o sink é **`innerHTML` lendo `location.hash`** (não outro lugar), e travar a forma de **extração do `q`** (`URLSearchParams` ou fallback substring) que entrega o payload íntegro ao `innerHTML` (round-trip do fragmento/encoding).
8. **Burp/rede (Nota 3-A):** confirmar que o fragmento (`#…`) **NÃO aparece em NENHUMA request** (o `GET /` na HTTP history está limpo) — o servidor **não recebe** o payload. E que o `<script>` vulnerável **é visível na resposta servida** (Burp lê o sink entregue).
9. **Uma vuln só:** página server-render **estática** (sem variável Jinja de input; autoescape ligado mas irrelevante); **sem banco**; **sem 2ª superfície**; **sem endpoint de busca no servidor**; fixed troca o **sink no cliente** (não escapa no servidor). Confirmar que o WALKTHROUGH **não** empilha outra vuln.
10. **§8:** payload **benigno** (`alert`), **sem** rede/exfil real/destruição; lab **contido**; bind **só** `127.0.0.1` (8021/8121). Enquadrar "lab isolado + prova benigna" no WALKTHROUGH.
11. **`app.py` vulnerable × fixed BYTE-IDÊNTICO;** o diff é **só** a linha do `<script>` (`innerHTML`↔`textContent`). Confirmar por `diff` que `app.py`, o resto do `index.html`, `Dockerfile` e `requirements.txt` são idênticos. **Portas 8021/8121 bind só `127.0.0.1`. Single-container.** `./atom up xss-dom` sobe sem erro. *(Validação de browser: a prova exige um browser real renderizando a página — o `alert` não é observável via `curl`/`docker exec`. Usar um browser no host apontando pra `127.0.0.1:8021`/`8121`; se a porta host não for alcançável do sandbox, ver memória `validating-atoms-via-docker-exec` para servir a página, mas a **execução do JS precisa de browser**.)*
12. **Theory primer** confirmado **por fetch** (`/cross-site-scripting/dom-based`, título "DOM-based cross-site scripting"). Se em dúvida, perguntar ao mantenedor. **Não inventar.** Confirmar a **grafia exata do H1** (hifenização/capitalização de "DOM-based Cross-Site Scripting") contra a página.

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** reproduzir o ataque no browser (itens 3–5); travar o payload exato e a extração do `q` (itens 4, 7); confirmar a URL/H1 do primer por fetch (item 12); confirmar a formulação afiada do heads-up estrutural (seção "O código"); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo **fecha o trio XSS** e é **uso-direto-do-antipadrão** (sem Saída B). Cada beat deve poder ser lido com o **`xss-reflected` (02)** e o **`xss-stored` (08)** abertos ao lado, e a diferença ("aqui o dado nem passa pelo servidor, e o fix vive no cliente") deve estar visível na linha em discussão. Ler também o **`sqli-union-basic` (01)** (molde single-container/HTML/estrutura) e o **`ssti-jinja` (19)/`deserialization-pickle` (20)** publicados (a **voz** atual — abertura seca, termo definido, título=classe, nota "mencionável não aplicada"). **Abrir e fechar** na lição-coração: *o source (`location.hash`) e o sink (`innerHTML`) vivem no cliente; o servidor não vê o payload; o fix é trocar o sink pra `textContent`, no cliente.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`01` INTEIRO** (molde), **`02`/`08` INTEIROS** (irmãos XSS — o contraste central; reusar a forma do banner, do HTML mínimo; **usar o gancho dos asides de DOM XSS que eles já têm**), **`19`/`20` publicados** (VOZ/estrutura atual). **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar a "trilha browser secundária" do 08 (proibida pela §3.3 atual), nem encenação, nem o rótulo "browser (secondary)".
- **NÃO há Saída B (crítico):** o JS lendo `location.hash`→`innerHTML` é diretamente o bug. **NÃO** inventar uma ruga de "a ferramenta padrão resiste".
- **A prova é o `alert` no BROWSER (riscos #3/#5).** A execução do JS **não** é observável via `curl`/`docker exec` — **precisa de um browser real** renderizando a página. Capturar a cadeia real: vulnerable → `#q=<img … onerror=…>` → `alert` dispara; fixed → mesmo hash → texto inerte, sem `alert`. **Se não bater rodando, PARAR e avisar — NÃO inventar** prova/screens.
- **A PEGADINHA a travar (crítico):** `<script>` via `innerHTML` **NÃO** executa pós-load; o payload é **event handler** (`<img … onerror=…>`/`<svg onload=…>`). Confirmar rodando e **travar o payload exato**. *(Isto é exatamente o aside que o 02/08 já publicaram — o 21 é onde aterrissa; citar o 02/08, publicados.)*
- **§8:** payload **benigno** (`alert`); bind **só** `127.0.0.1`; container/browser **isolado**; **nada** destrutivo/exfil-real/fora-do-lab. Enquadrar explicitamente no WALKTHROUGH (espelhar o 02/08).
- **A sutileza que NÃO pode enfraquecer a lição:** o **fixed troca o SINK no cliente (`textContent`)**, **NÃO** escapa no servidor / liga autoescape / bota CSP (defesa-armadilha da nota #2 — o dado nunca chega ao servidor). A defesa vive **onde o dado é usado**.
- **Uma vuln só:** foco em `innerHTML` lendo `location.hash`. Página server-render **estática, sem variável Jinja de input** (sem 2º XSS pelo servidor; autoescape ligado mas irrelevante). Sem banco, sem 2ª superfície, sem endpoint de busca no servidor.
- **Burp inspeciona/prova, NÃO planta (Nota 3-A — divergência do 08):** no DOM XSS o payload vive no fragmento e **não vai pra rede**; o Burp **lê o sink na resposta servida** e **prova que o fragmento não está em request nenhuma** (a assinatura do DOM XSS). O **browser** planta-via-URL e observa. **Trilha principal única** (Burp + browser); **sem** trilha secundária.
- **Abertura seca:** WALKTHROUGH entra direto na mecânica; **sem** encenação. Rotular os beats: **context (definir DOM XSS/source/sink/fragment)** → **spot the bug (o `<script>` lê `location.hash`→`innerHTML`)** → **exploitation (baseline `#q=laptop`; payload event-handler; `alert` no browser)** → **papel do Burp (inspeciona o sink; prova que o fragmento não vai pra rede)** → **o que a vuln NÃO é** → **impacto (XSS)** → **fixed (mesmo hash, `textContent`, sem execução)**.
- **Impacto honesto:** **XSS** no browser da vítima. Mesmo teto do 02/08, causa/fix no cliente. **Sem overclaim** (não é comprometimento do servidor), **sem foreshadow**.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é o **sink de DOM no cliente** (`innerHTML`←`location.hash`); **não é reflected** (o servidor não reflete — URL limpa na rede), **não é stored** (nada persistido), **não é bug de escape no servidor** (o dado nunca chega ao servidor; escapar/CSP lá não alcançam).
- **Contraste com 02/08 (cravar):** tabela + prosa; mesmo impacto, causa/mecanismo/fix diferentes; **fechar o trio XSS**; usar o gancho dos asides já publicados. Citar 02/08 (publicados) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** DOM-based XSS, source, sink, fragment/`location.hash`, `innerHTML`/`textContent`, DOM.
- **A03 sem arqueologia:** situar em **A03 — Injection**, explicar **por que** DOM XSS é injection (input → sink que executa, aqui no DOM do cliente), **sem** contar edições OWASP antigas.
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `xss-dom — DOM-based Cross-Site Scripting`. "JavaScript"/"innerHTML"/"location.hash" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **02/08** (contraste XSS central) e **opcionalmente 01/09/19** (família injection), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome **ou** descrição — inclusive os **próximos átomos da fase** (listados só no `ROADMAP.md`) e outros sources/sinks de DOM XSS como átomo futuro; **NÃO** anunciar posição de fase/release.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`xss-dom — DOM-based Cross-Site Scripting`, grafia exata confirmável na Fase 2). Termos técnicos (DOM, source, sink, fragment, `location.hash`, `innerHTML`, `textContent`, payload, XSS, CSP) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (DOM-based XSS), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **"What to read next" Burp + browser (NÃO "Burp secondary"):** o browser é parte **obrigatória** da trilha principal; redigir sem o rótulo "browser (secondary)" (resíduo do estilo antigo do 02/08).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 21: `xss-dom` — DOM-based Cross-Site Scripting: client-side JavaScript reads an attacker-controlled URL fragment (location.hash) and writes it to innerHTML, so a crafted fragment executes in the victim's browser without ever reaching the server (A03 Injection). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 21 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline → payload event-handler → `alert` no vulnerable → texto inerte (sem `alert`) no fixed, **num browser real**. Provar via Burp que o fragmento não está em request nenhuma.
- **Portas:** `127.0.0.1:8021` (vulnerable), `127.0.0.1:8121` (fixed). Bind **só** `127.0.0.1`. Single-container.
- Se houver dúvida sobre a URL/H1 do primer, o payload exato que dispara, a forma de extração do `q`, a formulação do heads-up estrutural, ou se o ataque não reproduzir no browser, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos client-side):

- **`xss-dom-client-side-sink-not-server`** — *"O átomo `xss-dom` (21) fecha o trio XSS (A03, reaproveita `atoms/A03-injection/`): DOM-based XSS via `el.innerHTML = ... + new URLSearchParams(location.hash.slice(1)).get('q')` no `<script>` do template. Fluxo source→sink 100% no cliente: o fragmento (`location.hash`, `#...`) NÃO vai pra rede, então o servidor nunca vê o payload (app.py byte-idêntico entre vuln/fixed, só serve a página estática). Fix = trocar o sink no CLIENTE (`innerHTML`→`textContent`); escapar no servidor/Jinja/CSP NÃO alcança (dado nunca chega ao servidor) — nota-armadilha #2, como sandbox(19)/HMAC(20). Payload = event handler `<img src=x onerror=alert(document.domain)>` (NÃO `<script>`, que via innerHTML pós-load não dispara — a pegadinha). Prova = `alert` num BROWSER real (não observável por curl/docker exec). Burp aqui INSPECIONA a resposta e PROVA que o fragmento não está em request nenhuma (não 'planta', diferente do stored 08). Contraste 02/08: mesmo impacto XSS, causa (sink no DOM vs render do servidor) e fix (cliente vs servidor) diferentes. Só Flask==3.0.0; JS vanilla permitido (código causal, §3.3)."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão.
