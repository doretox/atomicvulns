# Spec — Átomo 20: `deserialization-pickle`

> Documento de especificação para o Claude Code implementar o vigésimo átomo do projeto `atomicvulns` (Fase 4 — "Server-side Avançado", milestone `v0.4.0`). Este átomo é o **QUINTO e ÚLTIMO átomo da Fase 4** (5º dos cinco — `16 ssrf-blind-oob`, `17 ssrf-cloud-metadata`, `18 xxe-basic`, `19 ssti-jinja`, **`20 deserialization-pickle`**; confirmado no `ROADMAP.md`) e **ABRE UMA CATEGORIA NOVA — A08 (Software and Data Integrity Failures)**. É o **PRIMEIRO átomo A08 do repo**: a pasta `atoms/A08-data-integrity-failures/` **NÃO existe** — este átomo a **cria** (exatamente como o 15 criou a `A07-*` e o 18 criou a `A05-*`). **FECHA a Fase 4** — mas versionamento/release (`v0.4.0`) é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo** (Nota de planning 2).
>
> **É SINGLE-CONTAINER, molde do `01 sqli-union-basic` / `18 xxe-basic`** — só `vulnerable` + `fixed`, sem serviço extra, sem listener, sem rede especial. Depois do multi-container do 16/17 e do single-container do 18/19, o 20 segue single-container.
>
> **A lição em uma linha:** desserializar dados não-confiáveis com um formato que carrega **COMPORTAMENTO** (não só dados) executa código do atacante. O **pickle** do Python reconstrói objetos arbitrários: um objeto com **`__reduce__`** diz ao pickle **qual função chamar** ao desempacotar. `pickle.loads(bytes_do_atacante)` **roda essa função** — **RCE (Remote Code Execution)**. O fix é usar um formato que só carrega **DADOS** (JSON), não comportamento.
>
> **NÃO há "Saída B" aqui (como no 19, e diferente do 14/15/18).** Nos átomos 14 (PyJWT recusa a key confusion ingênua), 15 (`flask.session` resiste à fixation) e 18 (a stdlib `ElementTree` não resolve entidade externa), a ferramenta padrão **já mitigava** o bug ingênuo, então o átomo tinha que modelar o componente onde a vuln vive. **Aqui não existe essa ruga:** `pickle.loads` é a função padrão do próprio Python e é **diretamente** mal-usável — basta o dev passar bytes não-confiáveis pra ela. O átomo é **uso-direto-do-antipadrão**, como o `19 ssti-jinja` (a ferramenta padrão do framework é diretamente mal-usável). **NÃO inventar uma Saída B.**
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha Burp-only**, deserialization é server-side, o browser **não é a prova**; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo técnico na 1ª ocorrência, situar em A08 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind `127.0.0.1`** e **ISOLAMENTO — ATENÇÃO DOBRADA aqui porque o exploit é RCE**; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico de HTML/estrutura single-container), o **`xxe-basic` (18)** e o **`ssti-jinja` (19)** publicados (a **VOZ/estrutura ATUAL** — abertura seca, Burp-only, termo definido, título=classe; e o padrão da nota **"mencionável, não aplicada"** — `defusedxml`/sandbox — que o 20 replica com o **HMAC**), e o **`command-injection-basic` (09)** **SÓ pro CONTRASTE** (o 09 é RCE via **SHELL**, A03; o 20 é RCE via **DESSERIALIZAÇÃO**, A08 — causa/classe/mecanismo/fix DIFERENTES, mesmo impacto). Cravar esse contraste é o que justifica o 20 não ser "o 09 de novo".
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição na Fase 4: 20 é o 5º/ÚLTIMO átomo e ABRE a categoria A08 (confirmado; nome de pasta resolvido contra o `CLAUDE.md` §4)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A Fase 4 ("Server-side Avançado", `v0.4.0`) tem **cinco** átomos — `16 ssrf-blind-oob` (`[x]`), `17 ssrf-cloud-metadata` (`[x]`), `18 xxe-basic` (`[x]`), `19 ssti-jinja` (`[x]`), **`20 deserialization-pickle`** (`[ ]`, ESTE). O 16 abriu a fase; o **20 é o quinto** e **FECHA a fase**. Os átomos 01–19 já estão `[x]` em `main`.
>
> **Primeiro átomo A08 do repo — a categoria abre aqui.** O `ROADMAP.md` (linha 114) lista **`20. deserialization-pickle — A08 Data Integrity Failures`** com a justificativa *"RCE via deserialization em Python. Fecha a fase com um bang."* A pasta `atoms/A08-*` **NÃO existe ainda** — o 20 a **cria** (o mesmo movimento do `15 session-fixation`, que criou `atoms/A07-auth-failures/`, e do `18 xxe-basic`, que criou `atoms/A05-security-misconfiguration/`).
>
> **Nome da pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A08-data-integrity-failures/`.** A árvore do repo no `CLAUDE.md` §4 fixa **`A08-data-integrity-failures/`** com `deserialization-pickle/` dentro. Note que a **categoria OWASP 2021 completa é "Software and Data Integrity Failures"**, mas o **nome de pasta encurta pra `data-integrity-failures`** — **exatamente o padrão já usado no repo**, onde `A07-auth-failures/` encurta "Identification and Authentication Failures" e `A10-ssrf/` encurta "Server-Side Request Forgery". Ou seja: o nome de pasta é a **forma abreviada kebab** que o `CLAUDE.md` §4 já cravou; a **prosa (README/WALKTHROUGH/DIFF) nomeia a categoria por extenso — "A08 — Software and Data Integrity Failures"**. Pasta final: **`atoms/A08-data-integrity-failures/deserialization-pickle/`**. *(Sinalizo a abreviação explicitamente pra o mantenedor conferir; sigo o `CLAUDE.md` §4 como fonte da verdade, como o 18 seguiu pra `A05-security-misconfiguration`.)*
>
> **Rótulo A08 SEM arqueologia (`CLAUDE.md` §5, regra atual — DIVERGE do que o 18 fez).** Insecure deserialization é **A08 — Software and Data Integrity Failures** no OWASP Top 10 2021 (a edição que o projeto segue). **Diferente do 18** (que incluiu uma nota de mapeamento "XXE era A4 em 2017"), o 20 **NÃO** relata história de edições — **mesmo havendo** uma ruga real (deserialization tinha categoria própria numa edição anterior e foi *dobrada* em A08 na de 2021). A regra **atual** do `CLAUDE.md` §5 proíbe arqueologia ("NÃO relate em que número a categoria caía em edições antigas — é ruído histórico"), e o `19 ssti-jinja` já foi escrito sob ela. **Situar apenas: isto é A08 — Software and Data Integrity Failures.** Explicar **por que** a vuln cai em A08 (integridade de dados — ver "Por que A08") é legítimo; contar edições **não**.

## Nota de planning 2 — versionamento/release fica FORA desta spec (mesmo o 20 FECHANDO a fase)

> O 20 **fecha** a Fase 4, então é o átomo que **dispara** a release `v0.4.0`. **MAS** versionamento/CHANGELOG/tag/anúncio é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code") — **NÃO** cortar a versão, **NÃO** taggear, **NÃO** anunciar "fim da fase". **CRÍTICO (FORESHADOW, §5):** o átomo se descreve **isolado** — **NÃO** dizer "último da Fase 4", **NÃO** anunciar `v0.4.0`, **NÃO** foreshadowar a Fase 5. O aluno que abre o átomo não deve ver nenhuma menção de "fecha a fase".

## Nota de planning 3 — convenções ATUAIS valendo (o `CLAUDE.md` foi atualizado; NÃO copiar estilo antigo de irmãos onde divergir)

> O `CLAUDE.md` foi atualizado e o 20 segue as regras **atuais**, iguais às do `18`/`19`. Ao ler irmãos como molde, seguir o **`CLAUDE.md` ATUAL**, não o exemplo dos átomos onde eles divergirem. Divergências concretas a NÃO copiar:
>
> - **Trilha Burp-only (`CLAUDE.md` §3.3).** A trilha é **só Burp Suite** (+ `curl`/script Python como equivalente quando útil). **NÃO existe "trilha browser secundária".** Deserialization é **server-side** — a prova é o **efeito observável no servidor** (o marcador `/tmp/pwned`), lida via `docker compose exec`/logs, **não** o browser. **NÃO criar seção de exploração via browser.** *(Cuidado: READMEs publicados antigos ainda dizem `via Burp Suite (primary) and browser (secondary)` no "What to read next" — resíduo do estilo antigo. No 20 o "What to read next" diz **só Burp** — sem `and browser (secondary)`.)*
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature e a falha. **NADA** de encenação ("você é o pentester" e afins).
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** desserialização/serialização, pickle, `__reduce__`, RCE, base64, JSON — dar a expansão/definição na estreia. O átomo é pra quem **não** conhece a vuln.
> - **Título = classe sem stack (`CLAUDE.md` §5, regra nova).** O H1 nomeia a **classe** ("Insecure deserialization"), **NÃO** o motor ("...em pickle"/"...em Python"). O **slug** (`deserialization-pickle`) qualifica a variante — isso é OK (como `sqli-union-basic`). O motor (pickle) aparece no **corpo**, não no H1.
> - **A08 sem arqueologia** (Nota de planning 1).

---

## Identidade

- **ID:** `deserialization-pickle`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A08 — Software and Data Integrity Failures**. Pasta `atoms/A08-data-integrity-failures/` (**NÃO existe — o 20 a cria**; nome abreviado kebab, ver Nota de planning 1). Confirmado contra o `ROADMAP.md` ("A08 Data Integrity Failures") e o `CLAUDE.md` §4. **Primeiro átomo desta categoria no repo.** Em prosa (README/WALKTHROUGH/DIFF) usar o nome da classe — **"Insecure deserialization"** — e a categoria por extenso — **"A08 — Software and Data Integrity Failures"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A08-data-integrity-failures/deserialization-pickle/`
- **Número sequencial:** 20
- **Porta vulnerable:** `127.0.0.1:8020`
- **Porta fixed:** `127.0.0.1:8120`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos single-container 01/18/19. **§8 atenção dobrada (RCE): o binding local não é opcional aqui — o exploit executa comando no container.**
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM** serviço extra, listener, mock, ou rede especial. Molde do 01/18/19.
- **Fase / milestone:** Fase 4, `v0.4.0`. **Quinto e ÚLTIMO átomo da Fase 4; FECHA a fase.** Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo, ZERO menção de "fecha a fase"/release** (§5 foreshadow).
- **Branch de trabalho:** `atom/deserialization-pickle`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de Insecure deserialization** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/deserialization`** (título esperado da página: **"Insecure deserialization"**). Secundário **opcional**: o aviso de segurança oficial do módulo `pickle` na doc do Python (`https://docs.python.org/3/library/pickle.html`, a caixa de warning "Warning: The pickle module is not secure"). **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# deserialization-pickle — Insecure deserialization`** — `id` + nome canônico da **classe** em inglês (a forma que a PortSwigger usa na página). **SEM** "pickle"/"Python" no H1 (o slug já carrega o motor). Texto exato/grafia canônica **confirmável na Fase 2** (casar com o título exato da página PortSwigger); **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**Insecure deserialization — RCE via `pickle.loads` em dado não-confiável.** Uma app web guarda as **preferências do usuário** num **cookie** serializado com **pickle** e codificado em **base64**. A superfície é o header `Cookie` — e o usuário controla o próprio cookie. A app lê o cookie, base64-decoda, e faz **`pickle.loads`** nos bytes. Como o pickle **reconstrói objetos arbitrários executando as instruções de reconstrução embutidas nos bytes**, um cookie forjado com um objeto que define **`__reduce__`** faz o `pickle.loads` **chamar a função que o atacante escolheu** — `os.system("...")` — durante o desempacotamento. Resultado: **execução de comando no servidor (RCE)** a partir de um cookie.

### A lição-coração

> **"Desserializar dados não-confiáveis com um formato que carrega COMPORTAMENTO (não só dados) executa código do atacante. O pickle do Python reconstrói objetos arbitrários: um objeto com `__reduce__` diz ao pickle qual função chamar ao desempacotar. `pickle.loads(bytes_do_atacante)` roda essa função — RCE. O fix é usar um formato que só carrega DADOS (JSON), não comportamento."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** O pickle **não guarda só o ESTADO** de um objeto (os valores dos seus atributos); ele guarda **INSTRUÇÕES de reconstrução**. O hook **`__reduce__`** é como um objeto diz ao pickle: *"pra me recriar, chame a função F com os argumentos A"* — ele retorna uma tupla `(callable, args)`. No **unpickle** (`pickle.loads`), o pickle **CHAMA** esse `callable(*args)`. Um atacante define uma classe cujo `__reduce__` retorna `(os.system, ("touch /tmp/pwned",))` — e o `pickle.loads` **EXECUTA** `os.system("touch /tmp/pwned")` ao desempacotar. **Não há bug de lógica na app**; é o pickle fazendo **exatamente o que foi projetado** (reconstruir comportamento). O único erro da app foi **dar bytes não-confiáveis pro `loads`**.

Um detalhe que reforça o quão perigoso é: o pickle **importa** o módulo nomeado no payload durante o `loads` (ele guarda `os` / `system` como referência global e resolve na hora). Ou seja, o atacante alcança **qualquer callable importável** — a app **nem precisa** ter importado `os.system`. É o formato, não a app, que dá esse poder.

### Sub-lição (cravar)

A diferença entre `vulnerable` e `fixed` **NÃO é "validar o input"** nem **"assinar o cookie"** — é o **FORMATO**. `pickle` carrega **comportamento** (executa código na reconstrução); `json` carrega **só dados** (no pior caso, um dict estranho; `json.loads` não tem caminho de execução). **Bug pontual: o formato de (de)serialização.** Esta é a sub-lição que o passo "o que a vuln NÃO é" (§5) tem que blindar: o aluno não pode sair achando que "o cookie foi adulterado, então é só assinar" nem que "é um bug de validação". O que separa vulnerable de fixed é **pickle vs JSON**.

### Contraste conceitual com o repo (categoria A08 nova — ver seção dedicada "Contraste com o 09")

O contraste central é com o **`command-injection-basic` (09)** — mesmo **impacto** (RCE), **causa/classe/mecanismo/fix DIFERENTES**. Detalhe na seção "Contraste com o 09 (crítico)". Contrastes secundários, todos publicados e citáveis à vontade (`CLAUDE.md` §5):

- **Família "dado não-confiável vira código".** No `sqli-union-basic` (01) o motor é o SQL engine, no `command-injection-basic` (09) é o shell, no `ssti-jinja` (19) é o template engine — em todos, **input** não-confiável cai num **interpretador** que o executa (injection, A03). O 20 é **primo dessa família por impacto**, mas a causa é distinta: aqui não há um interpretador que a app invoca com input concatenado — é o **próprio desserializador** (`pickle`) que reconstrói e **executa comportamento** embutido nos **bytes serializados**. Por isso A08 (integridade de dados), não A03 (injection). *(Cravar: a semelhança é o teto de impacto; a raiz é outra.)*

### Por que A08 (Software and Data Integrity Failures)

A categoria A08 é sobre **confiar em dados/código cuja integridade não foi verificada** — assumir que um blob de dados que cruzou uma fronteira de confiança é seguro pra ser processado/reconstruído. Desserializar dados não-confiáveis é **o exemplo canônico**: a app trata o cookie (dado que o usuário controla) como se fosse um objeto confiável e o **reconstrói** com um formato que carrega comportamento. É uma **falha de integridade de dados** → **A08**. Coerente com o eixo server-side da Fase 4.

---

## Contraste com o 09 (CRÍTICO — é o que justifica o átomo existir)

O 20 chega a **RCE**, como o `command-injection-basic` (09, publicado). Mas é uma vuln **DIFERENTE** — cravar isso no WALKTHROUGH e no DIFF, ou o átomo parece "o 09 de novo":

| Eixo | `command-injection-basic` (09) | `deserialization-pickle` (20) |
|---|---|---|
| **Categoria OWASP** | **A03 — Injection** | **A08 — Software and Data Integrity Failures** |
| **Superfície** | query param (`?host=`) concatenado num comando | cookie `prefs` (pickle+base64) |
| **Quem executa** | o **SHELL** (`/bin/sh -c`, via `subprocess.run(..., shell=True)`) | o **DESSERIALIZADOR** (`pickle.loads` reconstruindo o objeto) |
| **Causa-raiz** | app **costura** input não-confiável num **comando de shell** | app faz `pickle.loads` em **bytes não-confiáveis** (formato que carrega comportamento) |
| **Fix** | **parametrizar / tirar o shell** (lista de args, sem `shell=True`) | **trocar o FORMATO** (JSON — dados, não comportamento) |
| **Impacto** | **RCE** | **RCE** (mesmo teto) |

**"Um átomo = uma vuln" se refere à CAUSA, não ao impacto** (`CLAUDE.md` §2). Assim como `sqli-union-basic` (01) e `xxe-basic` (18) ambos terminam em **leitura/vazamento de dados** sem serem o mesmo átomo (SQL engine vs parser XML), o 09 e o 20 ambos terminam em **RCE** sem serem o mesmo átomo (shell vs desserializador). **Só o impacto final coincide.** Citar o 09 (publicado) à vontade no contraste — o aluno abre os dois e compara: *"mesmo loot (RCE), porta completamente diferente"*.

---

## Uma vuln só — o foco é o `pickle.loads`; autoescape LIGADO; a prova é BENIGNA; SEM assinar o cookie

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é **`pickle.loads` em dado não-confiável** (o cookie). Garantias e sutilezas (todas validar na Fase 2):

- **Autoescape do Jinja LIGADO.** A página só **mostra** as prefs (`Theme: {{ theme }}`). Se o `theme` for refletido, é **escapado** (autoescape default do `render_template`) — **sem XSS**. A superfície é o **cookie desserializado**, não a exibição. Sem `|safe`, sem `Markup`, sem `render_template_string`.
- **A prova de RCE é BENIGNA e contida (§8, atenção dobrada).** O payload roda um comando que **PROVA execução sem dano** (`touch /tmp/pwned`) — a prova é **"executou"**, não "causou dano". **NÃO** usar payload destrutivo (nada de `rm`, nada de rede/reverse shell, nada que saia do container). Ver "Prova de RCE".
- **`fixed` = trocar o FORMATO (JSON), NÃO validar/assinar.** O fix é **estrutural** (formato que não executa). O fixed **não** valida o pickle, **não** assina o cookie com HMAC, **não** faz blocklist — isso seria a **defesa-armadilha** da nota #3 do DIFF, não a correção. Ver "O fix" e DIFF nota #3.
- **Nenhum dos dois apps ASSINA o cookie.** O cookie `prefs` do vulnerable é pickle+base64 **cru** (sem assinatura); o do fixed é json+base64 **cru**. Isso é **de propósito**: a ausência de assinatura é o que faz o aluno experiente pensar "é só assinar" — e a nota #3 do DIFF **desarma** essa intuição (assinar fecha o sintoma, não a causa). Se o vulnerable assinasse, a nota #3 perderia o gancho. **NÃO** usar `flask.session` (que assina) nem `SECRET_KEY` — não há segredo neste átomo.
- **Sem banco, sem segunda superfície, sem 2ª dependência.** Nenhum SQLite/`requests`/lib extra; nenhum PII real. A **única** superfície é o cookie `prefs` chegando ao `pickle.loads`.
- **`pickle.dumps` na app NÃO é a vuln.** A app **serializa** as prefs default dela própria (`pickle.dumps(DEFAULT_PREFS)`) pra setar o cookie inicial — isso é **dado confiável saindo**, inofensivo. A vuln é **exclusivamente** `pickle.loads` em bytes **não-confiáveis** (o cookie que volta do cliente). Cravar essa assimetria (dumps de dado próprio = ok; loads de dado do atacante = RCE).

---

## Flavor — cookie de preferências picklado (TRAVADO)

Uma app web mínima de **preferências do usuário** (**user preferences**) que guarda as prefs num **cookie** serializado com pickle+base64. **Didático:** mostra que input não-confiável **não é só formulário** — é **qualquer coisa que o usuário controla**, e o usuário controla o próprio cookie. O ponto **NÃO é a UI**; é o cookie.

### Fluxo (endpoint único `GET /`)

- **`GET /` sem cookie `prefs`:** a app cria um objeto de preferências default (`{"theme": "light"}`), **serializa** (vulnerable: pickle+base64; fixed: json+base64), **seta** no cookie `prefs`, e renderiza a página mostrando `Theme: light`.
- **`GET /` com cookie `prefs`:** a app base64-decoda o cookie e **desserializa** (vulnerable: `pickle.loads`; fixed: `json.loads`), e usa o objeto pra renderizar `Theme: <theme>`.
  - **VULNERABLE:** `pickle.loads` direto nos bytes do cookie → um cookie malicioso (`__reduce__`) **executa código** no desempacotamento.
  - **FIXED:** `json.loads` nos bytes → **só dados**; um cookie malicioso no máximo dá erro de decode/dict, **nunca executa**.
- **O ataque:** o atacante **substitui** o cookie `prefs` por um pickle malicioso (objeto com `__reduce__` → `os.system(comando-prova)`) base64-encodado. No próximo `GET /`, o `pickle.loads` **executa** o comando.

**Cada versão LÊ o formato que ESCREVE** (vulnerable: pickle+base64 nos dois lados; fixed: json+base64 nos dois lados). O **contraste `pickle.loads` vs `json.loads` é o diff.**

**Sem form de troca de tema.** A app **só exibe** as prefs — o cookie é setado automaticamente no 1º request. **NÃO** adicionar um form/endpoint pra mudar o tema (seria 2ª superfície). O aluno interage tampereando o cookie no Burp — é o que espelha o mundo real (um cookie serializado que "você não deveria editar", editado assim mesmo).

---

## Prova de RCE — CONTIDA e INOFENSIVA (TRAVADO; §8 atenção dobrada) — **DECISÃO SINALIZADA**

> **Este é o item que o prompt me pediu pra DECIDIR e SINALIZAR:** a forma mais limpa de evidenciar execução, benigna e observável. Abaixo, a escolha com justificativa.

### Comando-prova escolhido: **`touch /tmp/pwned`** (marcador de arquivo)

O `__reduce__` do payload retorna `(os.system, ("touch /tmp/pwned",))`. A prova de que o RCE ocorreu é o **efeito observável**: o arquivo **`/tmp/pwned` existe no container do vulnerable** e **NÃO existe no do fixed**.

**Por que `touch /tmp/pwned` (e não as alternativas):**

| Opção | Prova | Veredito |
|---|---|---|
| **`touch /tmp/pwned`** (escolhido) | `docker compose exec vulnerable ls -la /tmp/pwned` → existe; no fixed → `No such file or directory` | **Escolhido** — check **binário e limpo** (existe/não-existe), arquivo **vazio** (máximo benigno: nada lido, nada destruído, nada de rede), marcador "pwned" universalmente reconhecível em treino de segurança |
| `id` (saída nos logs) | `os.system("id")` imprime `uid=0(root)...` no stdout do container → `docker compose logs vulnerable` | **Alternativa/cor** — prova execução **E** que rodou como **root**; ótima cor adicional. A Fase 2 pode capturar as DUAS (o marcador `touch` como prova primária + um `id` mostrando `uid=0(root)` nos logs). |
| `id > /tmp/pwned` | marcador + identidade dentro do arquivo | Descartado como primário: mistura redirect de shell (`>`) no comando, um detalhe a mais sem ganho sobre `touch` + `id`-nos-logs separados |

**Regras §8 (RCE — atenção dobrada), a cravar no WALKTHROUGH:**

- O comando é **benigno**: `touch` cria um arquivo **vazio** — não lê, não apaga, não escreve conteúdo, **não faz rede**, **não sai do container**.
- **PROIBIDO** payload destrutivo (`rm`, fork bomb), rede (reverse shell, `curl` pra fora), ou qualquer coisa que escape o container. O objetivo é **DEMONSTRAR execução**, com o **mínimo efeito**.
- O container é **isolado e descartável**; o RCE fica **contido** no container do átomo; portas bind **só** `127.0.0.1`. O WALKTHROUGH deixa **explícito** que é um lab isolado e o payload é uma **prova de conceito benigna** — **exatamente o enquadramento do `command-injection-basic` (09)** na seção "What this really is" ("harmless here because isolated container; on a real target this is RCE — keep payloads demonstrative, never `rm -rf`/reverse shell").

---

## O código — o coração no `pickle.loads`

Imports **divergem** só no módulo de (de)serialização (vulnerable: `pickle`; fixed: `json`); o resto compartilha:

```python
# vulnerable                              # fixed
import os                                 import os
import base64                             import base64
import pickle                             import json
from flask import (Flask, request,        from flask import (Flask, request,
    render_template, make_response)           render_template, make_response)
```

`render_template("index.html", theme=...)` renderiza a página (arquivo em `templates/`, byte-idêntico entre as versões); `make_response(...)` + `set_cookie` seta o cookie inicial. O ponto da vuln é a linha do `pickle.loads` (fixed: `json.loads`).

### `vulnerable/app.py` — `pickle.loads` direto no cookie (RCE) (candidato — Fase 2 gera o real)

```python
app = Flask(__name__)
DEFAULT_PREFS = {"theme": "light"}


@app.route("/")
def index():
    cookie = request.cookies.get("prefs")
    if cookie is None:
        # First visit: serialize the default prefs (pickle + base64) and set the cookie.
        raw = base64.b64encode(pickle.dumps(DEFAULT_PREFS)).decode()
        resp = make_response(render_template("index.html", theme=DEFAULT_PREFS["theme"]))
        resp.set_cookie("prefs", raw)
        return resp
    # VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to pickle.loads.
    # pickle reconstructs arbitrary objects, executing any __reduce__ the bytes carry -- a crafted
    # cookie -> code execution on the server. Untrusted data must never reach pickle.loads.
    prefs = pickle.loads(base64.b64decode(cookie))   # RCE: attacker bytes -> arbitrary code on load
    return render_template("index.html", theme=prefs["theme"])


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — JSON (só dados) (candidato — Fase 2 gera o real)

```python
app = Flask(__name__)
DEFAULT_PREFS = {"theme": "light"}


@app.route("/")
def index():
    cookie = request.cookies.get("prefs")
    if cookie is None:
        # First visit: serialize the default prefs (JSON + base64) and set the cookie.
        raw = base64.b64encode(json.dumps(DEFAULT_PREFS).encode()).decode()
        resp = make_response(render_template("index.html", theme=DEFAULT_PREFS["theme"]))
        resp.set_cookie("prefs", raw)
        return resp
    # FIXED: prefs are (de)serialized as JSON, which carries DATA ONLY, never behavior. A malicious
    # cookie can at worst produce a weird dict; json.loads cannot execute code. Root fix: change the
    # FORMAT (data, not behavior) -- not "sign the cookie" (see DIFF for why signing is a patch).
    prefs = json.loads(base64.b64decode(cookie))     # JSON: data only; no code path on load
    return render_template("index.html", theme=prefs["theme"])


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

**Reconciliação com o snippet travado do prompt.** O prompt cravou o coração (`raw = base64.b64decode(cookie); prefs = pickle.loads(raw)`); o snippet usava `request.cookies.get("prefs", "")` como abreviação. **Aqui o default é `None`** (`request.cookies.get("prefs")`) pra **ramificar**: sem cookie → seta o default (senão `base64.b64decode("")`→`b""`→`pickle.loads(b"")` daria `EOFError` no 1º request). O **branch "sem cookie → seta default" é byte-idêntico** entre as versões (só o `dumps`/`loads` e o import divergem).

**Notas de implementação (validar/decidir na Fase 2):**

- **Rendering pós-`loads` malicioso.** Depois que `pickle.loads` executa o payload, o valor **retornado** é o retorno de `os.system` (**`0`**, um int) — o RCE (`touch`) **já disparou** durante o `loads`. Aí `prefs["theme"]` num int **levanta `TypeError`** → resposta **500**. **Isso é aceitável**: a prova do RCE **não é o corpo/status da resposta**, é o **marcador `/tmp/pwned`** — o comando rodou **dentro** do `pickle.loads`, antes de qualquer rendering. O WALKTHROUGH crava isso.
- **REFINAMENTO RECOMENDADO pra Fase 2 (opcional, mais limpo — decisão do mantenedor):** envolver a leitura do cookie num `try/except Exception: prefs = DEFAULT_PREFS` **IDÊNTICO nos dois apps** (byte-a-byte). Efeito: (a) o **vulnerable** dispara o `touch` no `loads`, cai no `except` no `prefs["theme"]`, e **responde `Theme: light` normal** — o ataque fica **SILENCIOSO** (página idêntica à benigna) enquanto `/tmp/pwned` foi criado → demonstração **mais forte e realista** (deserialization RCE é **invisível in-band**; a única pista é o efeito colateral); (b) o **fixed** cai no `except` (o `json.loads` de bytes de pickle levanta) e também responde `Theme: light` — nenhum app dá 500. Como o `try/except` é **idêntico**, o **diff continua sendo só `pickle`↔`json`** (import + `dumps` + `loads`). **Trade-off:** +2 linhas iguais nos dois, em troca de UX limpa + a lição "RCE silencioso". **Recomendo esse refinamento**; a Fase 2/mantenedor decide. Em ambos os desenhos, a **prova é o marcador**, não a resposta.
- **`request.cookies.get("prefs")` SEM default** (retorna `None` quando ausente) → `/` seta o cookie; com cookie → desserializa. (Não usar `("prefs", "")`.)
- **Cookie value é base64** (alfabeto `A-Za-z0-9+/=`): **todos** são `cookie-octet` válidos (RFC 6265) — `+`, `/`, `=` viajam limpos num cookie (diferente de `;`, que separa cookies). O aluno **cola o base64 direto** como valor do cookie `prefs`. **Confirmar na Fase 2** que o round-trip do cookie é limpo; se algum char incomodar, `base64.urlsafe_b64encode` (que troca `+/` por `-_`) é o fallback — a app teria que usar `urlsafe_b64decode` também, nos dois lados.
- **`make_response` + `set_cookie`** importados do Flask; o branch de set-cookie é idêntico nos dois (só o formato do `raw` diverge).

---

## O fix e o tipo de diff

**Fix:** trocar o **FORMATO** de (de)serialização — **pickle → JSON**. Tipo de diff: **lógica-diferente** — muda o formato usado pra dump/loads das prefs (`pickle.dumps`/`loads` → `json.dumps`/`loads`, com o base64 igual). O diff toca **três pontos**, todos o mesmo swap de formato: o **import** (`pickle`→`json`), o **serialize** (set do cookie default: `pickle.dumps`→`json.dumps(...).encode()`), e o **deserialize** (leitura do cookie: `pickle.loads`→`json.loads`). A linha **perigosa** é o `pickle.loads`; o `dumps` só mantém cada app auto-consistente. O resto (`os`/`base64`, `DEFAULT_PREFS`, o branch sem-cookie, o `render_template`, `__main__`, os templates, o `Dockerfile`, `requirements.txt`) é **byte-idêntico** (à parte o formato).

Diff colável (candidato — a Fase 2 gera o real):

```diff
-import pickle
+import json
 ...
     if cookie is None:
-        raw = base64.b64encode(pickle.dumps(DEFAULT_PREFS)).decode()
+        raw = base64.b64encode(json.dumps(DEFAULT_PREFS).encode()).decode()
         resp = make_response(render_template("index.html", theme=DEFAULT_PREFS["theme"]))
         resp.set_cookie("prefs", raw)
         return resp
-    # VULNERABLE: ... pickle.loads ... -> code execution on load ...
+    # FIXED: ... JSON carries DATA ONLY ... json.loads cannot execute code ...
-    prefs = pickle.loads(base64.b64decode(cookie))
+    prefs = json.loads(base64.b64decode(cookie))
     return render_template("index.html", theme=prefs["theme"])
```

**O CONTRASTE é o diff (obrigatório):** `pickle.loads` (executa comportamento) vs `json.loads` (só dados). **A única mudança é o formato de (de)serialização.**

### Notas obrigatórias no `DIFF.md`

1. **A causa é o FORMATO (pickle carrega comportamento), NÃO "validar/sanitizar o cookie".** Prova de isolamento: um cookie **benigno** (as prefs default) renderiza `Theme: light` **igual** nos dois apps (a **feature é idêntica**); só um cookie com **`__reduce__` malicioso** separa os dois — o vulnerable **executa** (`/tmp/pwned` aparece), o fixed **não** (`json.loads` no máximo dá erro/dict, nenhum `touch`). **Cravar a assimetria fina:** o pickle malicioso é **pickle perfeitamente válido** — não é input malformado; não há o que "sanitizar". O formato **em si** executa comportamento embutido em dados bem-formados.
2. **`pickle.loads` em dado não-confiável é o antipadrão; JSON (dado, não comportamento) é o certo.** Explicar **"dados vs comportamento"**: o pickle reconstrói **objetos arbitrários** (inclui **execução** via `__reduce__` — ele guarda *instruções de reconstrução*, não só estado); o JSON só produz **tipos primitivos** (dict/list/str/número/bool/null) — **não há caminho de código** no `json.loads`. A correção é **estrutural** (trocar pra um formato que não executa), não filtrar/validar bytes de pickle.
3. **HMAC / ASSINAR O COOKIE NÃO É O FIX (nota-ADVERTÊNCIA curta, mas DIDÁTICA — explicar POR QUE está aqui).** Enquadrar assim, explicitamente:
   - **(a) Nomear a intuição.** O aluno experiente vai pensar: *"o cookie foi adulterado — é só assiná-lo com HMAC (`hash` autenticado) pra impedir a adulteração"*.
   - **(b) Reconhecer o que isso resolve — e o que NÃO.** Assinar torna o cookie **tamper-evidente**: um cookie forjado é **rejeitado**, então **eleva a barra** pra ESTE vetor. **Mas fecha o SINTOMA (a adulteração DAQUELE cookie), não a CAUSA.** A operação perigosa — `pickle.loads` em dado que cruzou a fronteira de confiança — **continua lá**. Se a chave de assinatura **vazar** (*como o `ssti-jinja` (19) mostrou: uma `SECRET_KEY` de assinatura pode ser vazada*) ou se bytes não-confiáveis alcançarem o `loads` por **qualquer outro caminho** (outro endpoint, uma fila, um cache, um arquivo), é **RCE de novo, na hora**.
   - **(c) Cravar SINTOMA vs CAUSA.** Assinar é **mitigação/defense-in-depth** que **guarda** um primitivo inseguro; a **correção de causa** é **remover** o primitivo inseguro — trocar o **FORMATO** (JSON, que não executa). *(Mesmo espírito das notas "mencionável, não aplicada" do 17 (IMDSv2), 18 (`defusedxml`) e 19 (sandbox): nomear a defesa-armadilha que o aluno escolheria, pra ele não cair nela.)* **CURTA** (a intuição + o porquê), **NÃO** uma seção gigante; enquadrada como *"isto NÃO é o fix, e aqui está o motivo"*. *(A referência ao 19 é a publicado — permitida e ilustrativa; usar como cor, opcional.)*
4. **O impacto é RCE; contraste com o 09 (RCE por causa diferente).** Referir a tabela/seção "Contraste com o 09": mesmo teto (RCE), causa/classe/mecanismo/fix diferentes. **Sem foreshadow** (não nomear átomos/variantes futuras — nem os outros A08 do roadmap).

---

## Biblioteca / mecanismo

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask.** `pickle`, `base64`, `json`, `os` são **stdlib**. **Sem banco, sem `requests`, sem 2ª dependência.** (O `subprocess` **não** é necessário — o payload do atacante usa `os.system`, resolvido pelo próprio pickle no `loads`; a app não importa nada pro payload.)
- **NÃO é behavior-critical (diferente do 14 PyJWT / 18 lxml).** O comportamento que o átomo usa — `pickle.loads` chamar o callable do `__reduce__` — é **estável** há muitas versões do Python. Um **pin normal** basta (`Flask==3.0.0`, casando com 01/18/19). **Ainda assim, confirmar rodando na Fase 2** que o `__reduce__` executa na versão fixada (item 6 do checklist).

---

## WALKTHROUGH — abertura seca, trilha Burp-only (+ script Python / curl equivalente)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (preferências num cookie) e a falha (o cookie é desserializado com pickle → o unpickle executa comportamento). Trilha **ÚNICA: Burp** (a montagem do payload usa um **script Python curto** — é como se faz no mundo real; `curl` pra mandar o cookie é equivalente). **NÃO** criar seção de browser.

**Abertura (candidato — plantar a lição, seco):**

> *A app guarda as suas preferências num cookie chamado `prefs`. Por baixo, ela **serializa** o objeto de preferências com **pickle** — o módulo do Python que transforma um objeto em bytes e reconstrói o objeto a partir deles — e base64-encoda o resultado no cookie. A cada request, ela lê o `prefs`, base64-decoda, e faz `pickle.loads` nos bytes pra reconstruir as prefs. O problema: **você controla o seu cookie**. E o pickle não guarda só os dados do objeto — guarda **instruções de como reconstruí-lo**, incluindo **qual função chamar**. Um cookie forjado faz o `pickle.loads` **rodar a função que você escolher** — comando no servidor.*

Beats (molde do 18/19 publicado — Burp-only, seco; seções numeradas `## 1..6`):

1. **Context.** App "user preferences": `GET /` seta o cookie `prefs` (pickle+base64) e mostra `Theme: light`. Definir na estreia: **serialização/desserialização** (transformar objeto↔bytes), **pickle** (o módulo do Python que faz isso), **`__reduce__`** (o hook que diz ao pickle *qual função chamar* pra reconstruir um objeto), **RCE** (Remote Code Execution — comandos arbitrários no servidor), **base64** (codificação de binário em texto). Isto é **Insecure deserialization**, sob **A08 — Software and Data Integrity Failures**. Sem banco, sem segundo serviço: `vulnerable` em `127.0.0.1:8020`, `fixed` em `127.0.0.1:8120`. Trilha: Burp.
2. **Spot the bug.** Mostrar `vulnerable/app.py` — a linha `prefs = pickle.loads(base64.b64decode(cookie))`. O cookie **vem do cliente** (o aluno controla). Pergunta de auditoria: *"esses bytes vêm do meu cookie, que EU controlo — e o pickle reconstrói objetos arbitrários, executando o que o `__reduce__` mandar?"* → **sim**. Foreshadow do fix: **trocar o formato** — usar um que só carregue dados.
3. **Exploitation via Burp Suite.**
   - **Baseline:** configurar o Proxy, visitar `http://127.0.0.1:8020/`. A app **seta o cookie `prefs`** e mostra `Theme: light` (feature funciona). No Burp, **base64-decodar o valor do cookie `prefs`** pra **MOSTRAR** que é um stream de pickle (bytes como `\x80\x04}...` — reconhecivelmente **não** JSON). O aluno **vê o formato** na rede.
   - **Montar o payload (script Python curto — é como se faz no mundo real):**
     ```python
     import base64, os, pickle

     class Exploit:
         def __reduce__(self):
             # tells pickle: to "rebuild" me, call os.system("touch /tmp/pwned")
             return (os.system, ("touch /tmp/pwned",))

     print(base64.b64encode(pickle.dumps(Exploit())).decode())
     ```
     Explicar o que o script faz: define uma classe cujo `__reduce__` diz ao pickle "pra me reconstruir, chame `os.system('touch /tmp/pwned')`". `pickle.dumps` empacota isso; base64 encoda pro cookie.
   - **Disparar (Repeater):** pegar o `GET /` no Repeater, **substituir o valor do cookie `prefs`** pelo base64 do script, enviar. O `pickle.loads` do servidor **executa** `os.system("touch /tmp/pwned")` durante o desempacotamento.
   - **PROVAR a execução (efeito observável — a resposta NÃO é a prova):** `docker compose exec vulnerable ls -la /tmp/pwned` → o arquivo **existe** (foi criado pelo `touch` disparado no `loads`). *(Cor opcional: trocar o comando por `id` e ver `uid=0(root)...` em `docker compose logs vulnerable` — prova execução E que rodou como root.)* **Deixar claro:** o RCE dispara **dentro** do `pickle.loads`, **antes** de a app fazer qualquer coisa com o resultado — por isso a prova é o **marcador**, não o corpo da resposta.
   - **§8 (cravar):** isto roda num **container isolado e descartável**; o `touch` é **benigno** (arquivo vazio, sem dano, sem rede, sem sair do container). Num alvo real isso é **RCE** — controle do host. **Manter os payloads demonstrativos** (um marcador, um `id`); **nunca** `rm -rf`, reverse shell, ou algo destrutivo — nem num container. *(Espelhar o "What this really is" do `command-injection-basic` (09).)*
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **NÃO é "cookie adulterável genérico" (assinar NÃO resolve).** A tentação é "assina o cookie com HMAC". Isso **eleva a barra** pra este vetor (o cookie forjado é rejeitado), mas **não** toca a causa: `pickle.loads` em dado não-confiável continua sendo RCE — se a chave vazar (*como no `ssti-jinja` (19)*) ou os bytes chegarem por outro caminho, RCE de novo. A causa é o **FORMATO**, não a autenticação do cookie. *(Sintoma vs causa — ver DIFF nota #3.)*
   - **NÃO é o MESMO que command injection (09), apesar do mesmo impacto (RCE).** No 09 a app **costura** input num **comando de shell** e o **shell** executa (A03). Aqui o **desserializador** (`pickle`) reconstrói um objeto e **executa o comportamento embutido nos bytes** (A08). **Causa, classe, mecanismo e fix diferentes; só o RCE coincide.** *(Ver "Contraste com o 09".)*
   - **NÃO é bug de validação.** O pickle malicioso é **pickle válido** — não há input malformado pra rejeitar. Não dá pra "sanitizar" a saída; é o formato que executa. *(Ver DIFF nota #1.)*
   - **O que É (prova):** `pickle.loads` reconstrói um objeto que **VOCÊ** forjou e **chama a função que o `__reduce__` nomeia** — RCE — porque o **formato carrega comportamento**. A **única** correção é usar um formato que só carrega **dados** (JSON).
5. **Impact (honesto — sem overclaim).** **RCE (Remote Code Execution):** o atacante executa comandos arbitrários no servidor via um cookie malicioso desserializado. É o **impacto máximo** — **mesmo teto do `command-injection-basic` (09)**, por **causa distinta** (desserialização vs shell). Sem overclaim, sem foreshadow.
6. **Why the fix works (porta 8120).** Repetir contra o `fixed/`:
   - O **MESMO cookie malicioso** → `json.loads` nos bytes de pickle → **não executa** (dá erro de decode / no máximo um dict); a página não roda comando.
   - **Prova-chave:** `docker compose exec fixed ls -la /tmp/pwned` → **`No such file or directory`**. O `touch` **nunca** rodou no fixed. No vulnerable rodou; no fixed não — **mesmo cookie, execução vs nada**.
   - **A lição do diff:** o fix troca o **formato** (`pickle`→`json`), que só carrega **dados**. **Trocar-o-formato** (notas #1/#2); **assinar NÃO é o fix** (nota #3 — sintoma vs causa); **RCE por causa diferente do 09** (nota #4). A feature (`Theme: light` no uso benigno) fica **intacta**.

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Payloads/responses/marcador são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**RCE (Remote Code Execution) via insecure deserialization.** O atacante substitui o cookie `prefs` por um pickle malicioso; no `pickle.loads`, o servidor **executa** a função que o `__reduce__` nomeia — comando arbitrário no host. É o **impacto máximo**. **Mesmo teto do `command-injection-basic` (09)**, mas **causa distinta** (desserialização de formato-com-comportamento vs concatenação em shell). **Sem overclaim** (não inflar pra "comprometimento total da infra" — é RCE no container do app, o que já é o topo). **Sem foreshadow** (não citar átomos/variantes/categorias futuras).

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A08 NOVA — abre aqui; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`command-injection-basic` (09)** — o contraste **central** (seção dedicada). Mesmo impacto (RCE), causa/classe/mecanismo/fix diferentes. *"Mesmo loot, porta completamente diferente."*
- **`sqli-union-basic` (01), `ssti-jinja` (19)** — família "dado não-confiável vira efeito perigoso via um motor". Citáveis pra ancorar que o 20 é **primo por impacto**, mas de **raiz diferente** (o desserializador executa comportamento embutido nos bytes; não é input concatenado num interpretador).
- **`ssti-jinja` (19)** — citável na nota #3 do DIFF (chave de assinatura pode **vazar** — o 19 vazou a `SECRET_KEY`), reforçando por que "assinar o cookie" é mitigação, não fix. Referência a publicado, opcional, ilustrativa.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante futura** por número, nome **OU** descrição — inclusive **os outros átomos A08 do roadmap** (o átomo de deserialization em Node e o de prototype pollution), a **Fase 5**, ou a release **`v0.4.0`**.
- **PROIBIDO anunciar "fecha a fase"/"último átomo".** O átomo se descreve **isolado** (Nota de planning 2). O aluno não vê nenhuma menção de fase/release/próximos átomos.
- **Que a superfície de deserialization exista em outros ecossistemas/formatos é, no máximo, descrição conceitual de UMA LINHA** ("outros formatos que carregam comportamento têm o mesmo problema") — **sem** nomear átomo/linguagem/variante futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 20 vai até **RCE via `pickle.loads`** do cookie (o finding), provado pelo marcador benigno. **Uma vuln, uma causa (o formato), um fix (JSON).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato (primário):** **`https://portswigger.net/web-security/deserialization`** — a página conceitual de Insecure deserialization (título esperado **"Insecure deserialization"**, framing "What is insecure deserialization?"). É a página de introdução da vuln, não a de labs.
- **Secundário (opcional):** o **aviso de segurança oficial do módulo `pickle`** na doc do Python — `https://docs.python.org/3/library/pickle.html` (a caixa "Warning: The pickle module is **not secure**. Only unpickle data you trust."). Complemento honesto e canônico. **Opcional** — o primário PortSwigger é o obrigatório (`CLAUDE.md` §5).
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7 — "Insecure deserialization", exatamente como a PortSwigger nomear a página).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `sqli-union-basic`/`xxe-basic`/`ssti-jinja`).

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (página que exibe as prefs — não API-only). Garantir que a **ÚNICA** lição é o `pickle.loads` em dado não-confiável:

- **Só UM template de arquivo:** `templates/index.html` (exibe `Theme: {{ theme }}` + banner + dica de Burp). **Byte-idêntico** entre vulnerable e fixed (o diff vive só no `app.py`).
- **Autoescape LIGADO** (default do `render_template`) → `{{ theme }}` é escapado (sem XSS, mesmo se um cookie benigno setar um `theme` com `<...>`).
- **`fixed` = trocar formato (JSON), NÃO validar/assinar** (sutileza que **não pode** virar 2ª vuln nem enfraquecer a lição): a correção é **estrutural** (formato que não executa), **não** "validar o pickle" nem "assinar o cookie" (isso seria a defesa-armadilha da nota #3, não a correção).
- **Sem banco, sem 2ª superfície, sem assinatura/segredo.** A **única** superfície é o cookie `prefs` chegando ao `pickle.loads`.
- **Comando-prova benigno e contido** (§8). O RCE fica no container do átomo.

---

## HTML — `templates/` (mínimo, molde do 01; só `index.html`)

Molde do `sqli-union-basic`: `<!doctype>`, banner de aviso **obrigatório**, ≤40 linhas, ≤5 linhas de CSS inline, **sem** frameworks, **sem** JS, dica de Burp no rodapé. **`index.html` é byte-idêntico** entre vulnerable e fixed. **Sem form** (o cookie é setado pela app; o aluno tampereia no Burp). Candidato (a Fase 2 finaliza o texto exato):

**`templates/index.html`** (~15 linhas):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>User Preferences</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>User Preferences</h1>
<p>Theme: <strong>{{ theme }}</strong></p>
<p>Your preferences are stored in the <code>prefs</code> cookie.</p>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- **Sem JS, sem framework** (`CLAUDE.md` §3.3). CSS mínimo inline. `{{ theme }}` autoescapado.
- O `<p>` sobre o cookie `prefs` **aponta o aluno pra superfície** (o cookie), sem explicar o exploit — contexto de feature, não walkthrough.

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` — molde do `sqli-union-basic` (**com** `COPY templates`). **Nenhuma** linha extra (sem `apt`, sem banco, sem plantar arquivo — diferente do 18, que plantava `secret.txt`; aqui não há segredo). Só Flask via pip.

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

**`docker-compose.yml`** (candidato — molde do 01/18/19, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8020:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8120:5000"
```

**Sem `networks:`, sem serviço extra.** Molde simples do 01/18/19. **§8:** bind **só** `127.0.0.1` — não-negociável aqui (o exploit é RCE).

---

## Bibliotecas

**`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask.** `pickle`/`base64`/`json`/`os` são **stdlib**. **Sem** banco, `requests`, ou 2ª dependência.
- **Pin normal, NÃO behavior-critical** (diferente de PyJWT no 14 / lxml no 18): o `pickle.loads` chamar o callable do `__reduce__` é **estável**. Fixar (`Flask==3.0.0`) e **confirmar rodando** na Fase 2 que o `__reduce__` executa na versão fixada.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A08 — Software and Data Integrity Failures** (`atoms/A08-data-integrity-failures/`, **NÃO existe — o 20 cria**) | ROADMAP linha 114 lista `deserialization-pickle` em A08; `CLAUDE.md` §4 fixa o nome de pasta abreviado (`data-integrity-failures`, como `A07-auth-failures`). **Primeiro A08.** Situar em A08 **sem arqueologia**. |
| Posição na Fase 4 | **Quinto e ÚLTIMO (fecha a fase)** | ROADMAP: 16/17/18/19/**20**; 01–19 já `[x]`. Release `v0.4.0` **fora da spec/conteúdo** (Nota 2). |
| Nome de pasta A08 | **`A08-data-integrity-failures`** (abreviado) | `CLAUDE.md` §4 (fonte da verdade); padrão do repo (A07/A10 encurtam). Prosa usa o nome por extenso. **Sinalizado** pro mantenedor. |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Molde do 01/18/19. Sem serviço extra/listener/mock/rede. |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe aqui** (como no 19) | `pickle.loads` é a função padrão do Python e é **diretamente** mal-usável. Uso-direto-do-antipadrão. **NÃO inventar Saída B.** |
| Lição-coração | **Formato que carrega comportamento (pickle) executa código no `loads`; fix = formato só-dados (JSON).** | O bug é o **FORMATO**, não "validar/assinar o cookie". |
| Contraste central | **`command-injection-basic` (09)** — RCE por causa DIFERENTE (shell vs desserializador) | Justifica o 20 não ser "o 09 de novo". "Um átomo = uma vuln" = causa, não impacto. |
| Flavor — **TRAVADO** | **Cookie de preferências picklado** (`GET /`, cookie `prefs` pickle+base64) | Input não-confiável não é só form — é o cookie que o usuário controla. UI mínima; o ponto é o cookie. |
| Comando-prova — **SINALIZADO** | **`touch /tmp/pwned`** (marcador; `id`→logs como cor) | Prova binária e limpa (existe/não), arquivo vazio (máximo benigno, §8). |
| Código vulnerable | **`pickle.loads(base64.b64decode(cookie))`** | Bytes não-confiáveis → RCE no unpickle. |
| Código fixed | **`json.loads(base64.b64decode(cookie))`** | JSON só carrega dados; sem caminho de execução. |
| Rendering pós-loads malicioso | **500 aceitável** (RCE já disparou no `loads`); **refinamento recomendado:** `try/except`→default **idêntico nos dois** (RCE silencioso, sem 500, diff continua pickle↔json) | A prova é o **marcador**, não a resposta. Refinamento = UX limpa + lição "RCE invisível in-band". |
| Fix (único eixo) | **Trocar o FORMATO (pickle→JSON)** | Correção **estrutural**, não validar/assinar (defesa-armadilha da nota #3). |
| Diff | **Lógica-diferente** — import + dumps + loads, todos o swap pickle↔json | A linha perigosa é `pickle.loads`; resto byte-idêntico. |
| HMAC / assinar cookie | **NÃO aplicar** (nota-advertência #3, sintoma vs causa) | Eleva a barra, mas não remove o primitivo inseguro; chave pode vazar (cf. 19). Como IMDSv2 (17)/defusedxml (18)/sandbox (19). |
| Assinatura/segredo | **Nenhum** (`flask.session`/`SECRET_KEY` NÃO usados) | Cookie cru (sem assinatura) é o que dá o gancho da nota #3. |
| Autoescape | **Ligado** (default) | `{{ theme }}` escapado; sem XSS. |
| HTML | **Só `index.html`** (exibe theme + banner + dica); **sem form** | Cookie setado pela app; o aluno tampereia no Burp. |
| Bibliotecas | **`Flask==3.0.0`** (pin normal, não behavior-critical) | `pickle`/`base64`/`json`/`os` stdlib. Sem banco. Confirmar `__reduce__` executa. |
| Impacto | **RCE.** Mesmo teto do 09, causa distinta. | Honesto; sem overclaim; sem foreshadow. |
| Theory primer | **PortSwigger Insecure deserialization** (`/web-security/deserialization`, confirmar por fetch); pickle-docs secundário opcional | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Trilha | **Burp-only** (+ script Python/curl) | `CLAUDE.md` §3.3 atual. Server-side; a prova é o marcador, não o browser. Sem trilha browser. |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. |
| Título (H1) | **`deserialization-pickle — Insecure deserialization`** (classe, sem stack) | `CLAUDE.md` §5. Slug carrega "pickle"; H1 não. |
| Foreshadow | **ZERO pra frente** | `CLAUDE.md` §5. Não nomear A08 futuros/Fase 5/`v0.4.0`/"fecha a fase". |
| Portas | **8020 / 8120** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. §8 atenção dobrada (RCE). |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–8 são os centrais; 9–12 são higiene técnica. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /`** (sem cookie `prefs`) → a app **seta** o cookie `prefs` (pickle+base64) e mostra `Theme: light`. Template renderiza.
2. **`GET /`** (com o cookie default) → lê as prefs, mostra o tema (feature funciona nos dois apps).
3. **O ATAQUE (central — VALIDAR RODANDO):** gerar o pickle malicioso (script Python com `__reduce__` → `os.system("touch /tmp/pwned")`), base64, pôr no cookie `prefs`, `GET /` no vulnerable → o comando **EXECUTA** (`/tmp/pwned` criado dentro do container). **Capturar** o payload, o request e a prova de execução reais. **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** responses/prova.
4. **FIXED (`8120`):** o **MESMO** cookie malicioso → `json.loads` **NÃO executa** (erro de decode ou dict inócuo); **`/tmp/pwned` NÃO é criado**. **Capturar a diferença** (`ls` no vulnerable vs no fixed).
5. **Prova de isolamento:** o cookie **benigno** (prefs default) → `Theme: light` (feature idêntica nos dois). Confirmar que o pickle malicioso é **pickle válido** (não input malformado) — a lição da nota #1.
6. **Confirmar que o vulnerable faz `pickle.loads` no cookie** (não noutro lugar) e que o **`__reduce__` executa na versão fixada** (Flask 3.0.0 / Python da base image). Confirmar que o **`pickle.dumps` do default é inofensivo** (dado próprio) e que a vuln é **só** o `loads` do cookie.
7. **Uma vuln só:** autoescape ligado; **sem banco**; **sem 2ª superfície**; **sem assinatura/segredo**; fixed usa **JSON** (não valida/assina). Confirmar que o WALKTHROUGH **não** empilha outra vuln.
8. **§8 (RCE — atenção dobrada):** o comando **NÃO** é destrutivo, **NÃO** faz rede, **NÃO** sai do container. O container é **isolado**. Bind **só** `127.0.0.1` (8020/8120). Confirmar o enquadramento "lab isolado + prova benigna" no WALKTHROUGH.
9. **Rendering pós-loads:** decidir o desenho (500 aceitável **ou** o `try/except`→default idêntico recomendado). Se `try/except`, confirmar que é **byte-idêntico** nos dois e que o **diff continua** só `pickle`↔`json`.
10. **Cookie round-trip:** o base64 (com `+`/`/`/`=`) viaja limpo no cookie `prefs`; se não, cair pra `urlsafe_b64encode`/`decode` (nos dois lados). Confirmar que o aluno cola o base64 direto no Repeater.
11. **Primer PortSwigger (deserialization)** confirmado **por fetch** (`/web-security/deserialization`). Se em dúvida, perguntar ao mantenedor. **Não inventar.** (Secundário pickle-docs opcional.)
12. **`app.py` vulnerable × fixed:** confirmar por `diff` que a **única** mudança é o **formato** (import `pickle`↔`json`, `dumps`, `loads`), e que o resto (`os`/`base64`, `DEFAULT_PREFS`, branch sem-cookie, `render_template`, `__main__`) e o **`index.html`**/`Dockerfile`/`requirements.txt` são **byte-idênticos**. Diff **lógica-diferente** isolado ao (de)serialize. **Portas 8020/8120 bind só `127.0.0.1`. Single-container.** `./atom up deserialization-pickle` sobe sem erro. **Validar via `docker compose exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`); o `ls /tmp/pwned` também roda via `docker compose exec`.

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** reproduzir o ataque rodando (itens 3–4); confirmar `__reduce__` executa (item 6); decidir rendering pós-loads (item 9); confirmar a URL do primer por fetch (item 11); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **uso-direto-do-antipadrão** — sem Saída B, sem ferramenta-que-resiste (como o 19). Cada beat deve poder ser lido com o **`sqli-union-basic` (01)** aberto ao lado (molde single-container/HTML/estrutura) e o **`xxe-basic` (18)/`ssti-jinja` (19) publicados** ao lado (a **voz** atual — abertura seca, Burp-only, termo definido, título=classe, nota "mencionável não aplicada"). **Abrir e fechar** na lição-coração: *o formato carrega comportamento; `pickle.loads` de dado não-confiável executa código; o fix é trocar pra um formato que só carrega dados (JSON).*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`01` INTEIRO** (molde), **`18`/`19` publicados** (VOZ/estrutura atual), **`09`** (SÓ pro contraste RCE). **Seguir o `CLAUDE.md` ATUAL** onde os átomos antigos divergirem (Burp-only, abertura seca) — **NÃO** copiar trilha browser nem encenação, nem a nota de arqueologia OWASP que o 18 usou (o 20 **não** conta edições).
- **NÃO há Saída B (crítico):** `pickle.loads` é diretamente mal-usável. **NÃO** inventar uma ruga de "a ferramenta padrão resiste".
- **A prova é o marcador `/tmp/pwned` (riscos #3/#4).** Capturar a cadeia real: vulnerable → `touch` executa → arquivo existe; fixed → `json.loads` não executa → arquivo não existe. **Se não bater rodando, PARAR e avisar — NÃO inventar** prova/responses. A prova **não** é o corpo da resposta (pode ser 500 ou `Theme: light`); é o **efeito colateral** (marcador via `docker compose exec`; opcional `id` nos logs).
- **§8 ATENÇÃO DOBRADA (RCE):** comando **benigno e contido** (`touch`); bind **só** `127.0.0.1`; container **isolado**; **nada** destrutivo/rede/fora-do-container. Enquadrar explicitamente no WALKTHROUGH (espelhar o 09).
- **A sutileza que NÃO pode enfraquecer a lição:** o **fixed troca o FORMATO (JSON)**, **NÃO** "valida o pickle" nem "assina o cookie" (filtro/assinatura = defesa-armadilha da nota #3; a correção é **estrutural**). **Nenhum dos apps assina o cookie** (senão a nota #3 perde o gancho).
- **Uma vuln só:** foco no `pickle.loads` de dado não-confiável. Autoescape ligado (sem XSS). Sem banco, sem 2ª superfície, sem segredo. `pickle.dumps` do próprio default é inofensivo — a vuln é só o `loads` do cookie.
- **Abertura seca + trilha Burp-only:** WALKTHROUGH entra direto na mecânica; **sem** encenação; **sem** seção browser. Script Python curto pra montar o payload (mundo real); `curl` equivalente pra mandar o cookie. Rotular os beats: **baseline (ver o pickle na rede)** → **montar payload** → **disparar + provar (marcador)** → **o que a vuln NÃO é** → **impacto (RCE)** → **fixed (mesmo cookie, sem execução)**.
- **Impacto honesto:** **RCE.** Mesmo teto do 09, causa distinta. Sem overclaim, sem foreshadow.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que o bug é o **FORMATO** (pickle carrega comportamento), não "cookie adulterável" (assinar não resolve — sintoma vs causa), não o **mesmo** que command-injection (09) apesar do RCE (causa diferente), não bug de validação (pickle malicioso é pickle válido).
- **Contraste com o 09 (cravar):** tabela/prosa com causa/classe/mecanismo/fix diferentes, mesmo impacto. Citar o 09 (publicado) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** serialização/desserialização, pickle, `__reduce__`, RCE, base64, JSON.
- **A08 sem arqueologia:** situar em **A08 — Software and Data Integrity Failures**, explicar **por que** (integridade de dados), **sem** contar edições OWASP antigas (diverge do 18).
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 `deserialization-pickle — Insecure deserialization`. "pickle"/"Python" no corpo, não no H1.
- **Política de referência cross-átomo:** OK citar **09** (contraste RCE), **01/19** (família por impacto), **19** (chave vaza, na nota #3), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome **ou** descrição — inclusive os **outros A08 do roadmap** (deserialization em Node, prototype pollution); **NÃO** anunciar "próxima fase", "fecha a fase", nem a release `v0.4.0`.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`deserialization-pickle — Insecure deserialization`, grafia exata confirmável na Fase 2). Termos técnicos (pickle, `__reduce__`, deserialization, RCE, base64, JSON, payload, cookie) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (Insecure deserialization), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar. (Secundário pickle-docs opcional.)
- **"What to read next" Burp-only:** o README do 20 referencia o WALKTHROUGH **só como Burp Suite** — **sem** `and browser (secondary)` (resíduo do estilo antigo).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 20: `deserialization-pickle` — Insecure deserialization: an attacker-controlled cookie deserialized with Python's pickle executes embedded behavior via __reduce__, giving remote code execution (A08 Software and Data Integrity Failures). `` (padrão das linhas dos átomos anteriores). **NÃO** cortar a versão/taggear/anunciar release — isso é pós-merge do mantenedor.
- **ROADMAP.md:** marcar o átomo 20 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline → payload → marcador no vulnerable → marcador ausente no fixed. Validar via `docker compose exec` de dentro do container (portas host + `ls /tmp/pwned`).
- **Portas:** `127.0.0.1:8020` (vulnerable), `127.0.0.1:8120` (fixed). Bind **só** `127.0.0.1`. Single-container. §8 atenção dobrada (RCE).
- Se houver dúvida sobre a URL do primer, a grafia exata do H1, o desenho do rendering pós-loads, o round-trip do cookie, ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos A08/deserialization):

- **`deserialization-pickle-format-not-validation`** — *"O átomo `deserialization-pickle` (20) abre A08: RCE via `pickle.loads(base64.b64decode(cookie))` num cookie `prefs`. Raiz = o FORMATO (pickle carrega COMPORTAMENTO: `__reduce__` retorna `(os.system, ('touch /tmp/pwned',))` e o `loads` CHAMA a função). Fix = trocar o formato pra JSON (só dados). NÃO é validar/assinar: assinar eleva a barra mas guarda um primitivo inseguro (nota-armadilha #3, como IMDSv2/defusedxml/sandbox). Prova benigna = marcador `/tmp/pwned` via `docker compose exec` (a resposta não é a prova; RCE dispara DENTRO do loads). Contraste com 09: mesmo RCE, causa diferente (shell vs desserializador) — 'um átomo=uma vuln' é causa, não impacto. Sem Saída B (pickle.loads diretamente mal-usável). Só Flask==3.0.0 (pin normal). Nome de pasta A08 abreviado: `A08-data-integrity-failures` (CLAUDE.md §4)."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão.
