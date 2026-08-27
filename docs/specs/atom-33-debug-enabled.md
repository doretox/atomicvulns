# Spec — Átomo 33: `debug-enabled`

> Documento de especificação para o Claude Code implementar o átomo `debug-enabled` do projeto `atomicvulns`. **Posição na fase e ordem de implementação vivem no `ROADMAP.md`** (a única superfície do repo autorizada a situar isso). Este átomo entra numa **categoria que JÁ EXISTE — A05 (Security Misconfiguration)**: a pasta `atoms/A05-security-misconfiguration/` já contém `xxe-basic` (18) e `xxe-blind-oob` (30). O 33 **REAPROVEITA** essa pasta — **NÃO cria categoria nova** (nome de pasta confirmado contra o `CLAUDE.md` §4 e o padrão dos irmãos XXE). Versionamento/release é trabalho **pós-merge do mantenedor**, **fora desta spec e do conteúdo do átomo**.
>
> **É SINGLE-CONTAINER** — dois serviços (`vulnerable` + `fixed`), sem datastore externo, sem listener, sem serviço extra. Este átomo é **stateless** (sem SQLite): não há usuário/sessão/dado a semear — a app só expõe uma rota que **quebra** com input malformado. Cada lado é **um container Flask** sem persistência. O `docker-compose.yml` tem **dois serviços**, molde do `sqli-union-basic` (01) — **sem** serviço de datastore, **sem** healthcheck/`depends_on`, **sem** rede nomeada.
>
> **A lição em uma linha:** um app Flask rodando em **modo de desenvolvimento** (`app.run(debug=True)`) num ambiente que o atacante alcança transforma **QUALQUER exceção não-tratada** numa **página de debug interativa do Werkzeug** — que vaza código-fonte, variáveis e caminhos (**information disclosure**) **E** embute um **console** que executa **Python arbitrário no processo do servidor** (**RCE — Remote Code Execution**). O atacante dispara uma exceção de propósito, cai na página, e roda comando no servidor. O **PIN** que "protege" o console é **calculado de dados da máquina** — derivável; obstáculo, não proteção. O fix **não** é "pôr o PIN" nem "esconder a exceção" — é **`debug=False`** (e, em produção, servir com um servidor **WSGI** real, não o servidor de desenvolvimento).
>
> **O eixo pedagógico deste átomo:** a causa é uma **FEATURE DE DESENVOLVIMENTO exposta ao atacante**, **NÃO** "faltou tratar o erro" nem "faltou o PIN". A exceção é só o **GATILHO** (o campainha que abre a porta); a **vuln** é o **debugger interativo estar ligado e alcançável**. Isso separa o átomo dos dois RCE já publicados: no `command-injection-basic` (09) o **dado do atacante vira código** costurado num **shell** (A03 — Injection); no `deserialization-pickle` (20) os **bytes do atacante carregam comportamento** que o **desserializador** executa (A08 — Data Integrity); **aqui nada do atacante vira código** — o **console de execução já está exposto** pelo framework, e o atacante só **digita Python nele**. Mesma altura de impacto (RCE), causa distinta. Ver "Contraste com o 09 e o 20".
>
> **REQUISITO DIDÁTICO (crítico — este átomo é DENSO de vocabulário de bastidor):** o WALKTHROUGH e o README **DEVEM definir DO ZERO, na 1ª ocorrência**, assumindo que o aluno não conhece nenhum: **Werkzeug** (a lib HTTP/WSGI por baixo do Flask, que fornece o servidor de desenvolvimento e a página de erro interativa — **vem junto com o Flask, não se instala à parte**); **traceback** (o relatório de erro do Python — pilha de chamadas + valores locais + mensagem — que o Flask, em debug, renderiza como **página web interativa** em vez de esconder); **servidor de desenvolvimento vs produção** (o servidor embutido do Werkzeug é leve, pra testar local, **NÃO** pra produção); **WSGI (Web Server Gateway Interface)** (o "padrão de encaixe" entre um app Python e um servidor real de produção — Gunicorn/uWSGI); **o console interativo do debugger** (o campo, dentro do traceback web, que executa **Python arbitrário no processo do servidor**); **o PIN do debugger** (o cadeado que teoricamente protege o console, **calculado de dados da máquina** — logo derivável). Ver a seção "O MECANISMO em detalhe" e a Nota de planning 3.
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha BURP-ONLY**: o ataque é **dirigível por HTTP** — dispara a exceção, extrai o segredo do HTML da página de debug, emite a requisição que executa Python —, e a **prova é a resposta HTTP**; o console "nasceu" pra browser mas **reproduz melhor no Repeater** — **browser só quando a prova EXIGE**, e aqui **não exige**; §4 — pasta/categoria A05 **já existe**; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, **definir termo na 1ª ocorrência**, situar em A05 **sem arqueologia de edições**, **TÍTULO = classe sem stack**, política de referência/foreshadow; §7 — idioma + **headers de seção traduzidos em TODA doc PT**; §8 — segurança, **bind `127.0.0.1`**, dados fake, e **ATENÇÃO DOBRADA porque o exploit é RCE**: comando benigno, **NUNCA** destrutivo, contido no container; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referências vivas** — os **`xxe-basic` (18)** e **`xxe-blind-oob` (30)** (**IRMÃOS A05**: reusar a estrutura de doc e o enquadramento "A05 — Security Misconfiguration"; **contraste** — os XXE são misconfig de **PARSER XML**, o 33 é misconfig de **FRAMEWORK/DEPLOY**), o **`deserialization-pickle` (20)** (**molde do átomo de RCE**: o enquadramento §8 — lab isolado, payload benigno, marcador via `docker exec`, a prova de RCE **contida**) e o **`command-injection-basic` (09)** (**SÓ pro contraste de causa** — RCE via shell), os **DOIS átomos publicados MAIS RECENTES — `crypto-weak-hash` (31) e `crypto-ecb-mode` (32)** (a **VOZ/estrutura ATUAL**: abertura seca, definir termo, título=classe, headers PT traduzidos), e o **`sqli-union-basic` (01)** (molde canônico single-container Flask + estrutura de doc).
>
> **Escopo desta fase (PLANNING):** **só a spec.** Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `app.py` — isso é a **Fase 2**. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`). Os blocos de código nesta spec são **candidatos** pra guiar a Fase 2 — **não** são os arquivos finais.

---

## Nota de planning 1 — posição (ver `ROADMAP.md`) e REAPROVEITAMENTO da categoria A05 (já existe)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A **posição** deste átomo (ordem de implementação, fase, milestone) está registrada **só no `ROADMAP.md`** — a superfície autorizada. Esta spec **não** repete o ordinal/posição-na-fase nem a versão de release (ver a política de foreshadow). Justificativa do ROADMAP para este átomo: *"Flask `debug=True` com Werkzeug console. Simples e devastador."*
>
> **A categoria A05 JÁ EXISTE — o 33 reaproveita a pasta.** `atoms/A05-security-misconfiguration/` já existe e já hospeda `xxe-basic` (18) e `xxe-blind-oob` (30). **Nome de pasta — RESOLVIDO contra o `CLAUDE.md` §4 (fonte da verdade): `A05-security-misconfiguration/`** (confirmado também pelo `ls` da pasta atual, que lista os dois XXE). Pasta final: **`atoms/A05-security-misconfiguration/debug-enabled/`**. Em prosa (README/WALKTHROUGH/DIFF), a categoria é **"A05 — Security Misconfiguration"**.
>
> **Rótulo A05 SEM arqueologia (`CLAUDE.md` §5, regra atual).** Deixar o modo de desenvolvimento (com debugger interativo) ligado num ambiente alcançável é **A05 — Security Misconfiguration** no OWASP Top 10 2021 (a edição que o projeto segue) — a mesma categoria dos irmãos XXE. **NÃO** relatar em que número/categoria essa classe caía em edições antigas do OWASP Top 10 — é ruído histórico proibido pela regra atual. **Situar apenas: isto é A05 — Security Misconfiguration.** Explicar **por que** é A05 (uma feature de desenvolvimento do framework foi deixada habilitada num ambiente que o atacante alcança — um default/estado de deploy perigoso, não um bug de lógica de negócio) é legítimo; contar edições **não**. *(Nota histórica: o `xxe-basic` (18) incluiu uma nota de mapeamento "XXE era A4 em 2017". O 33 **NÃO** faz isso — segue a regra ATUAL do `CLAUDE.md` §5, igual ao `crypto-ecb-mode` (32) e ao `deserialization-pickle` (20), que já divergiram do 18 nesse ponto.)*
>
> **Enquadramento A05 entre os irmãos (contraste de sub-forma, todos publicados).** Os XXE (18/30) são misconfig de um **componente de parsing** — um **default perigoso do parser XML** deixado ligado. O 33 é misconfig de **FRAMEWORK/DEPLOY** — uma **feature de desenvolvimento do framework** deixada alcançável em execução. **Mesma categoria (A05), sub-forma diferente:** default de parser vs modo de deploy. Ancorar a lição nesse contraste com os irmãos publicados é bem-vindo (`CLAUDE.md` §5); **sem** narrar posição/sequência/arco (foreshadow, Nota 2).

## Nota de planning 2 — versionamento/release fica FORA desta spec + FORESHADOW REDOBRADO

> Versionamento/CHANGELOG-tag/anúncio de release é **trabalho de release do mantenedor, pós-merge**, não de átomo — **não entra nesta spec nem no conteúdo do átomo** (`CLAUDE.md` §10.4, §12). A única pegada de changelog **na Fase 2** é uma **linha em `[Unreleased] / Added`** (ver "Notas específicas pro Claude Code").
>
> **FORESHADOW REDOBRADO (o ponto mais sensível desta spec).** A spec é **pública/commitada** → **nasce limpa**. **PROIBIDO**, tanto no **conteúdo do átomo** quanto **na própria spec**: situar o átomo por **ordinal de fase**, **milestone**, **release/versão** (`v0.x`/`v1.0` etc.), ou como **abertura/encerramento** de qualquer coisa — **inclusive** como "o átomo que abre a A05-misconfig-de-framework", "o primeiro/penúltimo/último de", ou qualquer referência a **outros A05 futuros**. Nas frases que proíbem foreshadow, manter a proibição **GENÉRICA** — **sem nomear átomos não-publicados**. **A posição vive SÓ no `ROADMAP.md`.** Confirmo aqui apenas o **número (33)**, o **slug (`debug-enabled`)** e a **categoria (A05)**, que são metadados operacionais (portas, pasta, commit) — não posicionamento narrativo. **Pode citar `01`, `09`, `18`, `20`, `30`, `31`, `32`** (publicados) à vontade (`CLAUDE.md` §5).

## Nota de planning 3 — convenções ATUAIS: Burp-only (justificado), abertura seca, requisito didático (definir termos do zero)

> Seguir o `CLAUDE.md` **atual**. Decisões de forma e divergências a fixar:
>
> - **Trilha BURP-ONLY — JUSTIFICADA (`CLAUDE.md` §3.3 — Burp é a ferramenta principal; browser só quando a prova EXIGE).** O ataque inteiro é **dirigível por HTTP** e a **prova é a resposta HTTP**:
>   1. **disparar a exceção** = um request com input malformado (Repeater);
>   2. **o "tell"** = a **página de debug do Werkzeug** volta na resposta, vazando código/variáveis/caminhos — **observável no corpo da resposta**;
>   3. **extrair o segredo** = ler o token do console **do HTML da página de debug** (na resposta);
>   4. **executar** = emitir a requisição do debugger com o comando + o segredo (Repeater);
>   5. **a prova** = a **saída do comando volta na resposta HTTP** (o `id` do servidor no corpo).
>   - **O console "nasceu" pra browser** (você clicaria no ícone de console dentro do traceback), **mas o ataque reproduz MELHOR no Repeater** — controle cru dos query params, do encoding, do segredo. **A prova NÃO exige execução client-side** (não há JS do atacante rodando no browser da vítima; o que executa é **Python no servidor**, e a saída volta na resposta). Logo o **browser NÃO faz parte da trilha** (`CLAUDE.md` §3.3: browser só quando a prova exige — aqui não exige). **SEM trilha browser secundária.**
>   - Contraste honesto com os irmãos: o `deserialization-pickle` (20) também é Burp-only e RCE server-side; **diferente do 20**, aqui a **saída do comando volta in-band na resposta** (o console devolve o resultado), então o `id` na resposta é a **prova primária** — o marcador `/tmp/pwned` via `docker exec` é a prova **secundária** (contenção + contraste com o fixed). Ver "A prova".
> - **API-only JSON — DECISÃO DE FORMA (justificada; confirmável na Fase 2).** A app **não precisa de HTML próprio**: a "interface" que ensina a lição é a **página de debug do Werkzeug**, que o **framework renderiza sozinho** em qualquer exceção — um `templates/index.html` bespoke não acrescentaria nada e só somaria ruído. A app é mínima: um `GET /` com **banner JSON de aviso** (molde 31/32) + **uma rota-gatilho** que computa a partir de um parâmetro e **quebra** com valor malformado. **Banner de aviso** (`CLAUDE.md` §8.2) vive no **README** e no **`GET /` JSON** (o padrão dos átomos API-only — não há página HTML própria pra bannerizar).
>   - **Alternativa (flip localizado, se o mantenedor preferir):** um HTML mínimo de ~20 linhas com um form que dispara a rota-gatilho — trocar o `jsonify` do `GET /` por `render_template`. **Registrar como confirmável, não bloqueante.** Recomendo **API-only** (mais mínimo; a página de debug é a UI que importa).
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a 1ª frase situa a feature (um app Flask com uma rota que computa a partir de um parâmetro) e a falha (roda em `debug=True`, com o console do debugger exposto). **NADA** de encenação ("você é o pentester" e afins).
> - **REQUISITO DIDÁTICO — definir CADA termo de bastidor DO ZERO na 1ª ocorrência (`CLAUDE.md` §5 + o brief).** Este átomo é denso de vocabulário que o iniciante não tem: **Werkzeug**, **traceback**, **servidor de desenvolvimento vs produção**, **WSGI**, **console interativo do debugger**, **PIN do debugger**. Definir com a clareza de uma explicação a um iniciante — **NÃO** assumir familiaridade. Ver a lista completa e as definições candidatas em "O MECANISMO em detalhe" e nos beats do WALKTHROUGH.
> - **Título = classe sem stack (`CLAUDE.md` §5).** O H1 nomeia a **classe** — **debug/development mode exposto num ambiente alcançável** —, **NÃO** o motor ("...em Flask"/"...com Werkzeug"/"...em Python"). O **slug** (`debug-enabled`) já qualifica; "Flask"/"Werkzeug"/"Python" ficam no **corpo**, não no H1. Candidato de H1 em "Identidade".
> - **Headers de seção traduzidos em TODA doc PT (`CLAUDE.md` §7).** README/WALKTHROUGH/DIFF em `.pt-BR.md` traduzem **TODOS** os headers (`##`/`###`), com os termos técnicos em inglês dentro do header traduzido (ex.: `## Por que o fix funciona`, `### Passo 1 — Disparar a exceção`). A **única** exceção é o **H1 do README** (idêntico ao EN). Sinal de erro: header PT byte-idêntico ao par EN.
> - **A05 sem arqueologia** (Nota de planning 1).

## Nota de planning 4 — single-container, stateless, requirements.txt IDÊNTICOS, e o Werkzeug behavior-critical

> **Stateless, sem SQLite — não há o que semear.** A app **não** tem usuários/sessão/dado — só a rota-gatilho que quebra com input malformado. Cada lado é **um** container Flask sem persistência. O `docker-compose.yml` é **dois serviços** (molde do 01) — **sem** healthcheck, **sem** `depends_on`, **sem** rede nomeada, **sem** datastore.
>
> **`requirements.txt` IDÊNTICOS entre os lados (molde do 32, contraste com o 31).** Os dois lados usam **a mesma dependência, mesmo pin**. O delta vulnerable×fixed é **UMA flag no código** (`debug=True` → `debug=False`) + a **ausência do `WERKZEUG_DEBUG_PIN=off` no fixed** — **NÃO** uma dependência a mais. Consequências pra Fase 2:
> - `vulnerable/requirements.txt` = `fixed/requirements.txt` (idênticos, mesmo pin).
> - O **DIFF.md** contrasta honestamente: o fix é **uma linha** (a flag), sem mexer no manifesto — diff pequeno, impacto enorme.
>
> **O WERKZEUG É BEHAVIOR-CRITICAL (paralelo ao PyJWT no `jwt-none-alg`).** O comportamento em estudo — a página de debug interativa e o **protocolo do console por HTTP** (nomes dos query params, onde o segredo aparece no HTML, se `PIN=off` remove o unlock) — é **VERSION-DEPENDENT do Werkzeug**. O Werkzeug **vem como dependência do Flask** (não se instala à parte), mas a versão importa. **Fase 2:** pinar de forma que a versão do Werkzeug seja **determinística e reproduza o eval por HTTP com PIN off** — candidato: pinar `Flask==<pin>` **e** `Werkzeug==<pin>` explicitamente (mesmo pin nos dois lados), pra travar o invariante educacional (igual ao pin proposital do PyJWT no `jwt-none-alg`). **Confirmar rodando.** Ver "Biblioteca / stack" e "DECISÃO ABERTA".
>
> **§8 (RCE — atenção DOBRADA):** bind **só** `127.0.0.1` (não é opcional — o exploit executa comando no container); comando-prova **benigno** e **contido**; nada destrutivo, nada de rede/fora-do-container; dados fake. Ver "Prova — RCE benigna e contida".

---

## Identidade

- **ID:** `debug-enabled`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A05 — Security Misconfiguration**. Pasta `atoms/A05-security-misconfiguration/` (**JÁ EXISTE — o 33 reaproveita**). Confirmado contra o `ROADMAP.md` ("A05 Security Misconfiguration") e o `CLAUDE.md` §4. Em prosa, usar o nome da **classe** — **debug/development mode exposto** (grafia final na Fase 2) — e a categoria — **"A05 — Security Misconfiguration"** — **sem arqueologia de edições**.
- **Pasta:** `atoms/A05-security-misconfiguration/debug-enabled/`
- **Número sequencial:** 33
- **Porta `vulnerable`:** `127.0.0.1:8033`
- **Porta `fixed`:** `127.0.0.1:8133`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos irmãos. **§8 atenção DOBRADA (RCE): o binding local não é opcional — o exploit executa comando no container.**
- **Topologia:** **SINGLE-CONTAINER por lado** — dois serviços (`vulnerable` + `fixed`), **stateless, sem datastore**. Molde do `sqli-union-basic` (01), sem a parte de SQLite.
- **Fase / milestone:** ver `ROADMAP.md`. Versionamento/release **fora desta spec** (Nota de planning 2). **No conteúdo do átomo (e nesta spec pública): ZERO menção de posição/ordinal de fase/release/próximos átomos/abertura/encerramento** (§5 foreshadow, redobrado).
- **Branch de trabalho:** `atom/debug-enabled`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** ver seção "Theory primer". **PortSwigger PRIMEIRO** — candidato **"Information disclosure"** (`https://portswigger.net/web-security/information-disclosure`), que cobre debug pages / verbose errors (a metade *disclosure* do átomo). **Fallback OWASP** (Security Misconfiguration) se a página conceitual não encaixar — desvio consciente a AVISAR o mantenedor. **NÃO inventar URL — confirmar por fetch na Fase 2.**
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7 e §5 título=classe):** candidato **`# debug-enabled — Debug mode enabled in a reachable environment`** — `id` + nome canônico da **classe** em inglês. **SEM** "Flask"/"Werkzeug"/"Python" no H1 (o slug já qualifica; o motor fica no corpo). Grafia canônica exata **confirmável na Fase 2** (casando, quando possível, com o título da página do primer). *(Alternativas registradas: "Debug/development mode exposed in production", "Interactive debugger exposed via debug mode". A forma final é a mais fiel à classe "modo de desenvolvimento exposto"; preservar o nome em inglês também no README PT.)*

---

## Classe de vulnerabilidade

**Debug mode enabled in a reachable environment — o debugger interativo do Werkzeug exposto, com RCE via console.** Um app Flask sobe com `app.run(debug=True)`. Nesse modo, **qualquer exceção não-tratada** que a app levantar **não** vira um `500` genérico — vira uma **página de debug interativa** renderizada pelo **Werkzeug** (a biblioteca HTTP por baixo do Flask). Essa página **mostra o traceback** (o relatório de erro: pilha de chamadas, valores locais, trechos de código-fonte, caminhos de arquivo) — **information disclosure** direto na resposta HTTP — **e** embute um **console interativo**: um campo que executa **Python arbitrário no processo do servidor**. O atacante manda um request com **input malformado** de propósito → cai na página de debug → **lê o segredo do console no HTML** → emite a requisição que **roda um comando no servidor** → **RCE**. A **lógica da rota pode estar correta**: o erro que dispara a página é só o **gatilho**. A vuln é o **modo de desenvolvimento (com o debugger) estar ligado e alcançável**.

### A lição-coração

> **"Um app Flask rodando em modo de desenvolvimento (`app.run(debug=True)`) num ambiente que o atacante alcança transforma QUALQUER exceção não-tratada numa página de debug interativa do Werkzeug — que vaza código-fonte, variáveis e caminhos (information disclosure) E embute um console que executa Python arbitrário no processo do servidor (RCE). O atacante dispara uma exceção de propósito, cai na página, e roda comando no servidor. O PIN que 'protege' o console é calculado de dados da máquina — derivável, obstáculo e não proteção. O fix não é 'pôr o PIN' nem 'esconder a exceção' — é `debug=False` (e servir com um WSGI real em produção, não o servidor de desenvolvimento)."**

### O MECANISMO em detalhe (o coração do WALKTHROUGH — DEFINIR CADA PEÇA NA ESTREIA)

O átomo assume que o aluno **não conhece nenhum** destes termos. Definir do zero, na 1ª ocorrência:

- **Werkzeug.** A biblioteca HTTP/WSGI **por baixo do Flask** — o Flask é construído em cima dela. Ela **vem junto com o Flask** (é instalada como dependência quando você `pip install flask`; **não se instala à parte**). Entre outras coisas, ela fornece **o servidor de desenvolvimento** (o servidor embutido que o `app.run()` levanta) e **a página de erro interativa** (o "debugger"). Quando o átomo fala do "debugger", é uma feature do **Werkzeug**, ativada pelo `debug=True` do Flask.
- **Traceback.** O **relatório de erro do Python**: quando uma exceção não é tratada, o Python monta a **pilha de chamadas** (qual função chamou qual, linha a linha), com os **valores das variáveis locais** em cada nível e a **mensagem** da exceção. Normalmente isso vai pro terminal/log do servidor. O Flask, **em modo debug**, **renderiza o traceback como uma página web interativa** em vez de escondê-lo atrás de um `500` genérico.
- **Servidor de desenvolvimento vs produção.** O `app.run()` inicia o **servidor embutido do Werkzeug** — leve, feito pra **testar localmente** enquanto você programa. Ele **não é pra produção** (o próprio Werkzeug avisa: *"This is a development server. Do not use it in a production deployment."*). Em produção, a app roda atrás de um **servidor de produção real**.
- **WSGI (Web Server Gateway Interface).** O **"padrão de encaixe"** entre um app Python (Flask) e um servidor real. Em produção, você serve o app com um **servidor WSGI** — **Gunicorn** ou **uWSGI** — que **não tem** debugger nem servidor de desenvolvimento embutido. Rodar `app.run(debug=True)` num ambiente alcançável é justamente **não** ter feito isso.
- **O console interativo do debugger.** Dentro da página de traceback, **cada frame da pilha** tem um **console** — um campo que **executa Python arbitrário no processo do servidor**, no contexto daquele frame (pra o dev inspecionar variáveis ao vivo). Por definição, **isso é execução de código arbitrário**: quem alcança o console **roda o que quiser no servidor**.
- **O PIN do debugger.** A partir de certa versão, o Werkzeug "protege" o console com um **PIN** (um número de 9 dígitos) **impresso no log de startup do servidor** (`* Debugger PIN: 123-456-789`). O PIN é **calculado de dados da máquina** — combinando **username**, o **caminho/módulo do app**, o **machine-id** (`/etc/machine-id`/boot-id) e o **MAC** da placa de rede (`uuid.getnode()`), tudo hasheado. Como o próprio traceback **vaza** vários desses dados (o username aparece nos caminhos, o caminho do módulo aparece na pilha), e os demais são **estáveis**, o PIN é **derivável** por um atacante determinado — é um **obstáculo, não uma proteção**. E há a variável de ambiente **`WERKZEUG_DEBUG_PIN=off`**, que **desliga o PIN inteiro** (uma misconfig comum de "deixar debugar mais fácil").

**Como o console executa por HTTP (candidato — VERSION-DEPENDENT do Werkzeug, PROVAR na Fase 2).** A página de debug embute um **segredo por-processo** no próprio HTML (candidato: um bloco `<script>` com algo como `SECRET = "<20 chars>"`). O console então executa via **query params** num request ao servidor (candidato ao mesmo path que quebrou):

```
GET /<path>?__debugger__=yes&cmd=<python>&frm=<frame_id>&s=<secret>
```

onde `__debugger__=yes` marca o request como do debugger, `cmd` é o Python a avaliar, `frm` é o **id do frame** (um número que aparece no HTML) cujo contexto usar, e `s` é o **segredo** lido do HTML. **Com o PIN desligado**, **não há passo de unlock** — o eval roda direto e a **saída volta no corpo da resposta HTTP**. **Tudo isso é VERSION-DEPENDENT** (nomes exatos dos params, formato do segredo no HTML, se `PIN=off` de fato remove o unlock) e é a **DECISÃO ABERTA** a provar rodando na Fase 2.

O ponto contraintuitivo a cravar: **o atacante não "injetou" nada e não "quebrou" nada** — o **console de execução já estava aberto**, exposto pelo framework em modo debug. A exceção só **abriu a porta**; a porta estava **destrancada** por configuração.

### Sub-lição CRÍTICA (o coração do passo "o que a vuln NÃO é" e das notas do DIFF)

> **A causa é uma FEATURE DE DESENVOLVIMENTO exposta ao atacante, NÃO "faltou tratar o erro" nem "faltou o PIN". A exceção é só o GATILHO — o problema é o debugger de dev estar ligado e alcançável. Um error handler esconde AQUELE erro, não fecha o debugger (a próxima exceção não-tratada reabre o console). O PIN é derivável (calculado de dados da máquina) — obstáculo, não proteção — e o console não deveria estar exposto de qualquer forma. O fix de causa é `debug=False` (e, em produção, servir com um WSGI real — não o servidor de desenvolvimento).**

### Por que A05 (Security Misconfiguration)

O bug **não é** "input virou código" (injection) nem "faltou um check de dono" (broken access control) nem "o primitivo de crypto é fraco" (A02). É **"uma feature de desenvolvimento do framework foi deixada habilitada num ambiente que o atacante alcança"** — um **estado de configuração/deploy perigoso**, não um erro de lógica de negócio (a rota-gatilho pode estar logicamente correta). No Web Top 10 2021 isso é **A05 — Security Misconfiguration**, a mesma categoria dos irmãos XXE (18/30). Situar em **A05 — Security Misconfiguration**, **sem** contar edições antigas. Contraste de sub-forma com os irmãos: XXE é misconfig de **parser** (default perigoso); aqui é misconfig de **framework/deploy** (modo de dev alcançável).

---

## Contraste com o 09 e o 20 (RCE por causa diferente) — CENTRAL (é o que justifica o átomo existir)

O 33 chega a **RCE**, como o `command-injection-basic` (09) e o `deserialization-pickle` (20), **ambos publicados**. É uma vuln **DIFERENTE** — cravar no WALKTHROUGH e no DIFF, ou o átomo parece "o 09/20 de novo". **"Um átomo = uma vuln" se refere à CAUSA, não ao impacto** (`CLAUDE.md` §2): os três terminam em RCE por **portas completamente diferentes**.

| Eixo | `command-injection-basic` (09) | `deserialization-pickle` (20) | `debug-enabled` (33) |
|---|---|---|---|
| **Categoria OWASP** | **A03 — Injection** | **A08 — Software and Data Integrity Failures** | **A05 — Security Misconfiguration** |
| **Superfície** | query param (`?host=`) costurado num comando | cookie `prefs` (pickle+base64) | uma rota que **quebra** com input malformado + o **console do debugger exposto** |
| **Quem executa** | o **SHELL** (`/bin/sh -c`, via `shell=True`) | o **DESSERIALIZADOR** (`pickle.loads` reconstruindo o objeto) | o **CONSOLE DE DEV do framework** (o debugger do Werkzeug avaliando Python) |
| **O input do atacante vira código?** | **sim** — input concatenado no comando | **quase** — os bytes **carregam** comportamento que o `loads` roda | **NÃO** — o atacante **não injeta nada**; ele **cai num console que o framework já expõe** e digita Python |
| **Causa-raiz** | app **costura** input não-confiável num **comando de shell** | app faz `pickle.loads` em **bytes não-confiáveis** (formato que carrega comportamento) | **modo de desenvolvimento (debugger) deixado ligado e alcançável** (`debug=True` + PIN off) |
| **O erro/gatilho** | o próprio payload injetado | o próprio cookie forjado | uma **exceção não-tratada** — o **gatilho**, **não** a vuln |
| **Fix** | **parametrizar / tirar o shell** (lista de args) | **trocar o FORMATO** (JSON — dados, não comportamento) | **`debug=False`** (+ servir com WSGI real em produção) |
| **Impacto** | **RCE** | **RCE** | **information disclosure + RCE** |

**PONTO AFIADO A CRAVAR (o que torna o átomo não-redundante):** nos três o teto é RCE, mas **só no 33 nada do atacante vira código**. No 09 o dado dele é **concatenado** e executado; no 20 os bytes dele **carregam** comportamento; no 33 o **console de execução já está aberto** pelo framework — o atacante só **encontra a porta** (disparando uma exceção qualquer) e **digita**. A exceção é o **campainha**, não a chave. Por isso a causa é **CONFIGURAÇÃO** (modo de dev exposto), não injection nem desserialização. Citar 09 e 20 (publicados) à vontade — o aluno abre os três e vê *"mesmo loot (RCE), três portas completamente diferentes"*.

---

## Uma vuln só — a rota-gatilho pode estar CORRETA; sem 2ª superfície; PIN é OFF (não modelado)

Invariante inegociável do átomo (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o **modo de desenvolvimento (debugger) exposto** (`debug=True` + PIN off num ambiente alcançável). Para garantir isso:

- **A rota-gatilho é código COMUM.** Ela computa a partir de um parâmetro e **quebra** com valor malformado (candidato: um `int()`/lookup — ver "Flavor"). O input **benigno funciona igual nos dois lados**; só o **malformado + o debug** expõe o console. A lógica pode estar "correta" — a falha **não** é a rota. Contraste explícito no passo "o que a vuln NÃO é": o problema **não** é "faltou um `try/except`" (isso esconderia **este** erro, não fecharia o debugger).
- **O PIN está DESLIGADO — e o cálculo do PIN NÃO é modelado como parte do ataque.** Duas razões (travadas): (a) modelar o cálculo do PIN exigiria um **2º bug** (leitura de machine-id/MAC) e seria **não-determinístico** (o PIN muda por container/boot); (b) o PIN vira o **beat "o que a vuln NÃO é"** / nota-armadilha ("o PIN PARECE proteção, mas é derivável — obstáculo, não fix"), **NÃO** a espinha. A vuln única é: **o debugger interativo está exposto ao atacante** (`debug=True` liga; `PIN=off` tira o cadeado). **NÃO** modelar leitura de machine-id/MAC, **NÃO** derivar o PIN no walkthrough.
- **Sem 2ª superfície, sem leitura de arquivo, sem injection.** O `GET /` é só o banner JSON. A rota-gatilho só computa/quebra. O `fixed` muda **SÓ** o `debug` (True→False) e a **ausência do `PIN=off`**. **Nada mais.** Sem SQLite, sem `requests`, sem lib extra.
- **A prova de RCE é BENIGNA e contida (§8, atenção DOBRADA).** O comando roda um `id` (saída na resposta) e/ou um `touch /tmp/pwned` (marcador via `docker exec`, ausente no fixed) — **nada destrutivo, nada de rede, nada sai do container**. Ver "Prova".

---

## Flavor — debug ligado, PIN desligado (TRAVADO)

Um app Flask **API-only mínimo, single-container**, com **`app.run(debug=True)`** E o **PIN do debugger DESLIGADO** (`WERKZEUG_DEBUG_PIN=off` no ambiente — uma misconfig realista de "deixar debugar mais fácil"). Endpoints:

- **`GET /`** — banner JSON de aviso (molde do 31/32): `{"warning": "⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.", "hint": "GET /<trigger-route> with a value; a malformed value crashes the app. Work from Burp Repeater."}`. **Não injetável.**
- **A rota-gatilho** (candidato: `GET /items/<idx>`) — computa/olha algo a partir do parâmetro e **levanta uma exceção não-tratada** com valor malformado. **Candidato travado no espírito, exato confirmável na Fase 2:** um parâmetro que vai pra `int()` + um lookup/divisão. Ex.: `ITEMS[int(idx)]` — `idx` não-numérico → `ValueError`; `idx` fora do range → `IndexError`. **Input benigno** (ex.: `/items/0`) → resposta normal (candidato JSON `{"item": "<valor>"}`), **idêntica nos dois lados**. **Input malformado** (ex.: `/items/abc`) → exceção não-tratada → no vulnerable, a **página de debug do Werkzeug**; no fixed, um `500` genérico.
  - **A rota-gatilho é IDÊNTICA nos dois lados** (o input benigno funciona igual; só o malformado + o `debug` expõe o console). **NÃO** há `try/except` na rota (o gatilho precisa **escapar** pra o handler de debug do Werkzeug) — e isso é **de propósito**: o passo "o que a vuln NÃO é" mostra que **adicionar** o `try/except` esconderia **este** erro sem fechar o debugger.

**O ATAQUE (resumo; detalhe em "O ataque"):** o atacante dispara a exceção → recebe a **página de debug do Werkzeug** → dela extrai o **segredo do console** (do HTML) → emite a **requisição que executa Python no servidor** → **RCE**.

- **HTML: NENHUM** (API-only — Nota de planning 3). Sem `templates/`, sem `render_template`. A "UI" que importa é a **página de debug do Werkzeug** (renderizada pelo framework).
- **PIN OFF via ambiente (candidato; confirmar a forma na Fase 2).** Candidato: `ENV WERKZEUG_DEBUG_PIN=off` no `vulnerable/Dockerfile` (ou `environment:` no compose do serviço vulnerable) — **presente só no vulnerable**. **Alternativa (diff single-file, mais limpo):** setar `os.environ["WERKZEUG_DEBUG_PIN"] = "off"` no `app.py` do vulnerable, **antes** do `app.run(debug=True)`. **Fase 2 CONFIRMA** qual forma **de fato** desliga o PIN na versão fixada do Werkzeug (o eval por HTTP tem que rodar **sem** passo de unlock) e escolhe a que mantém o diff mínimo. O invariante **travado**: **PIN off no vulnerable; ausente no fixed**.

---

## O "tell" — a página de debug vazando (mostrar ANTES do RCE) — OBRIGATÓRIO

**ANTES** de qualquer execução de comando, o WALKTHROUGH DEVE mostrar a **metade *information disclosure*** do impacto — o "tell" observável na resposta HTTP:

- Disparar a exceção (input malformado) no **vulnerable** → a resposta é a **página de debug do Werkzeug**, que **vaza**: o **traceback** (pilha de chamadas), **trechos do código-fonte** da app, os **valores das variáveis locais** no momento do erro, e os **caminhos de arquivo** no servidor (que revelam o layout do filesystem, o username no path, etc.). **Isso já é um finding por si só** (information disclosure) — mostrar e nomear **antes** do RCE, porque **o vazamento é metade do impacto**.
- É **observável na resposta HTTP** (o corpo é a página de debug) — direto no Repeater. Sem browser.
- Contraste imediato com o **fixed**: o **mesmo** input malformado → um **`500` genérico** (sem traceback, sem código, sem variáveis, sem console). A diferença é **observável na própria resposta**.
- **VALIDAR RODANDO na Fase 2** e capturar o HTML real da página de debug (o traceback, o trecho de código, a presença do ícone/campo de console e do segredo embutido).

---

## O ataque (Burp-only) + a prova (TRAVADO; espinha = console exposto)

**Cenário travado; a mecânica exata do eval por HTTP é candidato confirmado por probe (Fase 2 — ver "DECISÃO ABERTA", é VERSION-DEPENDENT do Werkzeug).** Cadeia, **tudo no Burp** (Repeater):

1. **Baseline:** `GET /items/0` (input benigno) → resposta normal (`{"item": "..."}`), **idêntica** nos dois lados. A feature funciona.
2. **Disparar a exceção:** `GET /items/abc` (input malformado) → no **vulnerable**, a **página de debug do Werkzeug** volta na resposta.
3. **O tell (mostrar o vazamento — ANTES do RCE):** na resposta, apontar o **traceback**, o **código-fonte**, as **variáveis**, os **caminhos** vazados. Nomear: isto é **information disclosure**, já um finding.
4. **Extrair o segredo do console:** ler do HTML da página de debug o **segredo do console** (candidato: `SECRET = "<...>"`) e um **id de frame** (candidato: `frm=<id>` que aparece no HTML). *(VERSION-DEPENDENT — Fase 2 confirma onde/como aparecem.)*
5. **Emitir a requisição de execução (RCE):** um request ao debugger com o comando + o segredo (candidato: `GET /items/abc?__debugger__=yes&cmd=<python>&frm=<frame_id>&s=<secret>`). Com o **PIN off**, **sem** unlock → o comando **roda no servidor** e a **saída volta no corpo da resposta**.
6. **A prova:** o comando devolve, na resposta HTTP, a saída de `id` (candidato) — o servidor **executou código** que o atacante escolheu. Conta RCE, **sem** ter injetado nada num interpretador.

**FIXED (8133):** o **mesmo** input malformado (`GET /items/abc`) → um **`500` genérico** (sem traceback interativo, sem console). O request de eval do passo 5 → **não** existe debugger pra atender (candidato: `500`/`404`/resposta genérica; confirmar na Fase 2). **Sem página de debug, sem segredo pra extrair, sem console, sem RCE.** A prova do fix é essa **ausência observável** — e o baseline (input benigno) funciona **idêntico** nos dois lados.

### Prova de isolamento (o que traça a diferença PURO ao modo debug)

- **Baseline benigno, IDÊNTICO nos dois lados:** `GET /items/0` → mesma resposta (`{"item": "..."}`) no vulnerable **e** no fixed. A feature é a mesma; **só** o input malformado + o `debug` separa.
- **Ataque:** no **vulnerable**, o input malformado abre a página de debug (info disclosure) e o console (RCE); no **fixed**, o **mesmo** input malformado dá um `500` genérico — **nada vaza, nada executa**. A diferença é **100% a flag `debug`** (+ o `PIN=off`), **não** a rota (idêntica) nem uma dependência (mesma).

---

## Prova — RCE BENIGNA E CONTIDA (`CLAUDE.md` §8 — atenção DOBRADA; molde do 20) — **DECISÃO SINALIZADA**

> **Item que exige DECIDIR e SINALIZAR** (a forma mais limpa de evidenciar execução, benigna e observável). Abaixo, a escolha com justificativa; a Fase 2 captura o comando-prova exato rodando.

### Comando-prova PRIMÁRIO: **`id` com a saída na resposta HTTP**

O console do Werkzeug **devolve a saída do comando no corpo da resposta** — então a prova mais limpa e **Burp-only** é rodar **`id`** e ver `uid=...(...) gid=...(...)` **na própria resposta** (candidato de `cmd`: `__import__("os").popen("id").read()` — expressão que retorna a string; forma exata confirmável na Fase 2). Prova execução **E** (bônus, como no 20) mostra **como quem** rodou (provavelmente `root` no container). **Diferente do 20** (deserialization RCE é "silenciosa in-band", provada pelo marcador), aqui a **saída volta in-band** — a prova primária é a resposta HTTP.

### Comando-prova SECUNDÁRIO (contenção + contraste com o fixed): **`touch /tmp/pwned` (marcador)**

Como no `deserialization-pickle` (20): o comando cria o marcador `/tmp/pwned`; a prova de contenção é `docker compose exec vulnerable ls -la /tmp/pwned` → **existe** no vulnerable, **`No such file or directory`** no fixed. Reforça o contraste "executou vs nada" no lado corrigido.

| Opção | Prova | Veredito |
|---|---|---|
| **`id` na resposta** (primário) | a resposta HTTP do eval contém `uid=...` | **Escolhido primário** — Burp-only puro (a prova É a resposta), + mostra a identidade (root) |
| **`touch /tmp/pwned`** (secundário) | `docker compose exec vulnerable ls -la /tmp/pwned` → existe; fixed → ausente | **Escolhido secundário** — marcador binário limpo, contido, e o contraste com o fixed |
| `rm`/reverse shell/rede | — | **PROIBIDO** (`CLAUDE.md` §8) — destrutivo/sai do container |

**Regras §8 (RCE — atenção DOBRADA), a cravar no WALKTHROUGH (molde do 20):**

- Os comandos são **benignos**: `id` só lê a identidade do processo; `touch` cria um arquivo **vazio** — nenhum lê/apaga conteúdo, **nenhum faz rede**, **nenhum sai do container**.
- **PROIBIDO** payload destrutivo (`rm`, fork bomb), rede (reverse shell, `curl` pra fora), ou qualquer coisa que escape o container. O objetivo é **DEMONSTRAR execução**, com o **mínimo efeito**.
- O container é **isolado e descartável**; o RCE fica **contido** no container do átomo; portas bind **só** `127.0.0.1`. O WALKTHROUGH deixa **explícito** que é um lab isolado e o comando é uma **prova de conceito benigna** — **exatamente o enquadramento do `command-injection-basic` (09) e do `deserialization-pickle` (20)** ("harmless here because isolated container; on a real target this is RCE — keep payloads demonstrative, never `rm -rf`/reverse shell").

---

## O código — o coração na flag `debug` (candidatos; a Fase 2 gera o real)

O fio condutor: **o app roda em modo debug**. O `app.py` **DIFERE** entre os lados **numa flag** (`debug=True` → `debug=False`) + a **ausência do `PIN=off` no fixed**; todo o resto — `GET /` banner, a rota-gatilho, os imports — é **IDÊNTICO**.

> **Todos os blocos abaixo são CANDIDATOS — a Fase 2 gera o código real, confirma a versão do Werkzeug reproduzindo a página de debug + o eval por HTTP com PIN off, captura o request/response reais, e trava o gatilho + o comando-prova.**

### `vulnerable/app.py` — `debug=True`, PIN off (RCE) (candidato)

```python
import os
from flask import Flask, jsonify

app = Flask(__name__)
ITEMS = ["alpha", "bravo", "charlie"]  # dummy data (CLAUDE.md §8) -- content is irrelevant


@app.route("/")
def index():
    return jsonify({
        "warning": "⚠️ Intentionally vulnerable. Run locally only. "
                   "Never expose to the internet or a shared network.",
        "hint": "GET /items/<idx> with a number; a malformed idx crashes the app. "
                "Work from Burp Repeater.",
    })


@app.route("/items/<idx>")
def get_item(idx):
    # Ordinary route logic. It converts the path segment to an int and looks up an item.
    # A malformed idx ("abc") raises ValueError; an out-of-range int raises IndexError.
    # There is intentionally NO try/except here -- the point is NOT "the route forgot to
    # handle the error". The unhandled exception is only the TRIGGER; the vuln is that the
    # app runs with the interactive debugger EXPOSED (see app.run below).
    return jsonify({"item": ITEMS[int(idx)]})


if __name__ == "__main__":
    # VULNERABLE: debug=True turns on Werkzeug's INTERACTIVE DEBUGGER. Any unhandled exception
    # is rendered as an interactive web page that leaks source/variables/paths (information
    # disclosure) AND embeds a console that runs ARBITRARY PYTHON in this server process (RCE).
    # WERKZEUG_DEBUG_PIN=off removes the PIN "lock" on that console -- a realistic "make
    # debugging easier" misconfiguration. The route logic above is fine; the flaw is entirely
    # this development mode being reachable. Fix: debug=False (and serve behind a real WSGI
    # server in production -- not this development server). (candidate: PIN via env; confirm Phase 2)
    os.environ["WERKZEUG_DEBUG_PIN"] = "off"
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)
```

### `fixed/app.py` — `debug=False` (candidato)

Só o rodapé muda (o `debug` e a ausência do `PIN=off`); o resto é idêntico:

```python
# ... imports, GET /, GET /items/<idx> IDENTICAL to vulnerable ...

if __name__ == "__main__":
    # FIXED: debug=False -- no interactive debugger, no console. The SAME malformed idx still
    # raises an exception, but it becomes a GENERIC 500 with no traceback and no console.
    # In production, this development server should not be used at all: serve the app behind a
    # real WSGI server (Gunicorn/uWSGI), which has no debugger. The route logic is unchanged.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=False)
```

- **O CONTRASTE (`debug=True` + `PIN=off` vs `debug=False`) é o diff.** `GET /`, a rota-gatilho, os imports — **idênticos**. A rota **quebra igual** nos dois; só o `debug` expõe o console.
- **Confirmar na Fase 2:** que a versão fixada do Werkzeug (i) renderiza a página de debug interativa com `debug=True`; (ii) o `PIN=off` (seja no env do Dockerfile/compose, seja no `app.py`) **de fato** remove o unlock; (iii) o eval por HTTP roda com o formato de params candidato; (iv) o fixed dá um `500` genérico (sem console). **Se a forma in-app do `PIN=off` não pegar, mover pro Dockerfile/compose (env) e PROVAR.**
- **Nota (orthogonal — Fase 2 decide):** `debug=True` liga também o **reloader** (que observa arquivos e reinicia). É **ortogonal à vuln** e inofensivo no container; se causar ruído/log duplo, `app.run(debug=True, use_reloader=False)` mantém o **debugger** ligado sem o reloader — mas o `debug=True` cru é o antipadrão mais fiel. Manter mínimo.

---

## O fix e o tipo de diff

**Fix:** **`debug=True` → `debug=False`** (+ a **ausência do `WERKZEUG_DEBUG_PIN=off`** no fixed). Tipo de diff: **uma flag** (a mais localizada do repo até aqui) — o resto (`GET /`, a rota-gatilho, imports) é **byte-idêntico**. **Diff pequeno, impacto enorme.**

Diff colável (candidato — a Fase 2 gera o real conforme onde o `PIN=off` acabar vivendo):

```diff
 if __name__ == "__main__":
-    # VULNERABLE: debug=True exposes Werkzeug's interactive debugger (console -> RCE);
-    # WERKZEUG_DEBUG_PIN=off removes the PIN lock. The dev mode is the flaw, not the route.
-    os.environ["WERKZEUG_DEBUG_PIN"] = "off"
-    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)
+    # FIXED: debug=False -- no interactive debugger, no console. Same exception -> generic 500.
+    # In production, serve behind a real WSGI server (Gunicorn/uWSGI), not this dev server.
+    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=False)
```

**O CONTRASTE é o diff:** modo de desenvolvimento com debugger exposto (vulnerable) vs modo normal, sem debugger (fixed). **A única mudança funcional é a flag `debug`** (+ o `PIN=off`). A rota que quebra é **idêntica**.

### Notas obrigatórias no `DIFF.md` (CURTAS, didáticas)

1. **A causa é o MODO DE DESENVOLVIMENTO EXPOSTO, não "faltou tratar a exceção".** A exceção é só o **GATILHO**. **Prova de isolamento:** o **mesmo** input malformado, no lado **fixed** (`debug=False`), dá um `500` genérico — **sem** console, **sem** vazamento. A diferença é **100% a flag `debug`**, não a rota. Um error handler / `try/except` esconderia **AQUELE** erro específico, mas o debugger de dev continuaria ligado e a **próxima** exceção não-tratada reabriria o console — trata o **sintoma**, não a causa.
2. **"Só põe o PIN" NÃO é o fix — nota-ARMADILHA (com honestidade).** Nomear a intuição: *"o console é protegido por um PIN, então é só ligar o PIN."* Ser honesto: o PIN **eleva um pouco a barra**, mas é **calculado de dados da máquina** (username + machine-id + MAC, hasheados) — e o **próprio traceback vaza** vários desses dados (username nos caminhos, caminho do módulo na pilha), os demais são **estáveis** → o PIN é **derivável** por um atacante determinado. É **obstáculo, não proteção**. E, mais fundo: **o console de dev não deveria estar exposto de forma alguma**. Sair do `debug=True` é a correção; "pôr o PIN" apenas tranca (mal) uma porta que não devia existir naquele ambiente. *(Mesma honestidade-em-camadas das notas do salt no 31 e do CBC no 32: a defesa nomeada tem valor parcial, mas não é o fix de causa.)*
3. **"Só captura a exceção com um error handler / `try/except`" NÃO é o fix — nota-ARMADILHA (SINTOMA vs CAUSA).** Nomear a intuição: *"a página apareceu porque um erro escapou — então captura o erro."* Mostrar que isso **esconde o GATILHO** (aquele erro específico), **mas** o **debugger de desenvolvimento continua ligado** — a **próxima** exceção não-tratada (de outra rota, outro input, um bug futuro) **reabre o console**. Trata o **sintoma**, não a **causa** (o modo de dev exposto). **Cravar SINTOMA vs CAUSA.**
4. **Impacto: information disclosure + RCE; contraste com 09/20 (mesmo teto, causa diferente).** A metade *disclosure* (o traceback vazando código/variáveis/caminhos) já é finding; a metade *RCE* (o console) é o teto. **Mesmo teto de RCE do `command-injection-basic` (09) e do `deserialization-pickle` (20)**, por **causa distinta** — no 09 o **shell** executa input costurado; no 20 o **desserializador** roda comportamento embutido nos bytes; aqui o **debugger de dev exposto** já oferece o console (o atacante nada injeta). Referir a tabela "Contraste com o 09 e o 20". **Sem foreshadow.**
5. **HONESTIDADE — o WSGI real é contexto de deploy legítimo, NÃO armadilha.** Mencionar que, em produção, a app deve rodar atrás de um **servidor WSGI real** (Gunicorn/uWSGI) — que **não tem** o servidor de desenvolvimento nem o debugger — é **contexto correto de deploy**, não uma defesa-armadilha. **O fix mínimo do átomo é `debug=False`**; o **contexto completo** é "servidor de desenvolvimento + debug fora de produção". Enquadrar as duas coisas: a correção pontual (a flag) e a prática de deploy (o WSGI). Não confundir com as armadilhas #2/#3.

---

## Biblioteca / stack

- **`vulnerable/` e `fixed/`: Flask** (o **Werkzeug vem junto** — é dependência do Flask, **não** se instala à parte; **DEFINIR isso** no README/WALKTHROUGH). `os` é stdlib (não vai no requirements).
- **Os `requirements.txt` são IDÊNTICOS entre os lados** (Nota de planning 4) — **mesmo pin**. O delta vulnerable×fixed é **a flag `debug` no código** (+ o `PIN=off`), **NÃO** uma dependência. **Contraste com o 31** (onde os lados diferiam por causa do `bcrypt`): aqui o fix é **uma linha de código**.
- **O WERKZEUG É BEHAVIOR-CRITICAL — pinar pra travar o invariante (paralelo ao PyJWT no `jwt-none-alg`).** O protocolo do console por HTTP (params, segredo no HTML, `PIN=off`) é **version-dependent**. Candidato: pinar **`Flask==<pin>`** **e** **`Werkzeug==<pin>`** explicitamente (mesmo pin nos dois lados) pra a versão do Werkzeug ser **determinística e reproduzir o eval com PIN off**. **Confirmar RODANDO na Fase 2** (a versão exata que reproduz o ataque candidato). `Flask==3.0.0` casa com os irmãos, mas **confirmar o par Flask/Werkzeug** que reproduz — se a versão que o `Flask==3.0.0` puxa mudar o protocolo do console, **pinar o Werkzeug na versão que reproduz** e documentar (mesmo espírito do pin proposital do PyJWT).
- **SEM** ORM, `requests`, SQLite, ou 2ª dependência. `CLAUDE.md` §3.6. Stateless.
- **SEM SAÍDA B (declarar explicitamente).** `app.run(debug=True)` é o **próprio antipadrão ingênuo** — literalmente o que quase todo tutorial de "primeiros passos com Flask" mostra (`app.run(debug=True)` pra ter reload + erros bonitos ao desenvolver). **Diferente do 14/15/18** (onde a ferramenta padrão **já mitigava** o bug ingênuo, exigindo modelar o componente onde a vuln vive), **aqui não há essa ruga**: o modo debug é **diretamente** o antipadrão — como o `pickle.loads` no 20 e o `AES.MODE_ECB` no 32. **NÃO inventar uma Saída B.** A única falha é a flag.

---

## Renderização / "um átomo = uma vuln" / API-only

**API-ONLY JSON** (a "UI" que ensina é a página de debug do Werkzeug, renderizada pelo framework; decisão de forma justificada na Nota de planning 3). Garantir que a **ÚNICA** vuln é o **modo debug exposto**:

- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas `application/json` via `jsonify`.
- **Banner de aviso OBRIGATÓRIO** (`CLAUDE.md` §8.2) — num **`GET /`** que devolve um **JSON de aviso** (molde do 31/32) + no **README**. **O `GET /` não é injetável.**
- **A rota-gatilho é código comum** (o input benigno funciona igual nos dois lados); **sem injection**, **sem** 2ª superfície, **sem** leitura de arquivo, **sem** modelar o cálculo do PIN.
- **O `fixed` muda SÓ a flag `debug`** (True→False) + a ausência do `PIN=off`. `GET /`, a rota-gatilho, os imports são **idênticos**.
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é **`debug=False`**, **NÃO** "pôr o PIN" (armadilha #2) nem "capturar a exceção" (armadilha #3). A rota que quebra é a **mesma** nos dois lados — o que muda é **o modo**.

---

## WALKTHROUGH — abertura seca; Burp-only; DENSO EM DEFINIÇÕES; headers PT traduzidos

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A 1ª frase situa a feature (um app Flask com uma rota que computa a partir de um parâmetro) e a falha (roda em `debug=True`, com o console do debugger exposto). Trilha **Burp-only**: disparar a exceção, extrair o segredo, emitir o eval — **tudo no Repeater**; **a prova é a resposta HTTP** (o `id` do servidor no corpo). **SEM browser** (a prova não exige execução client-side).

**Abertura (candidato — plantar a lição, seco):**

> *A app é um app Flask com uma rota que recebe um valor, converte pra número e devolve um item. Mande um valor que não é número e a rota quebra — uma exceção não-tratada. Numa app normal isso seria um erro 500 sem graça. Mas esta app roda em `debug=True`, o modo de desenvolvimento do Flask. Nesse modo, o Werkzeug — a biblioteca HTTP por baixo do Flask — não esconde o erro: ele te devolve uma página de debug interativa, que mostra o código-fonte, as variáveis e os caminhos do servidor (isso já vaza informação), e embute um console que executa Python arbitrário no processo do servidor. Você dispara a exceção de propósito, cai na página, e roda um comando no servidor. O PIN que deveria trancar o console está desligado — e mesmo ligado, ele é derivável.*

Beats (molde do 20/31/32 — abertura seca, seções numeradas `## 1..N`; tudo no Repeater; **sem browser**):

1. **Context.** A feature: um `GET /` de aviso + uma rota-gatilho que converte um parâmetro pra `int()` e olha um item. **Definir na estreia (REQUISITO DIDÁTICO — do zero):** **Werkzeug** (a lib HTTP por baixo do Flask, que vem junto e fornece o servidor de dev e a página de erro interativa), **traceback** (o relatório de erro do Python — pilha + variáveis + mensagem — que o debug renderiza como página web), **servidor de desenvolvimento vs produção** (o embutido do Werkzeug é pra testar local, não pra produção), **WSGI** (o padrão de encaixe entre o app e um servidor real — Gunicorn/uWSGI), **console interativo do debugger** (o campo, dentro do traceback, que executa Python no servidor), **PIN do debugger** (o cadeado calculado de dados da máquina — derivável), **RCE (Remote Code Execution)** (comando arbitrário no servidor). Isto é **A05 — Security Misconfiguration**. Portas: `vulnerable` `127.0.0.1:8033`, `fixed` `127.0.0.1:8133`. Trilha: **Burp (Repeater)**; sem browser. Cravar: **você não vai injetar código em lugar nenhum** — o console **já está exposto**; você só o encontra e o usa.
2. **Spot the bug.** Mostrar o `vulnerable/app.py`: `app.run(..., debug=True)` + `WERKZEUG_DEBUG_PIN=off`. Apontar que a **rota-gatilho está logicamente OK** (converte e olha um item) — o bug é o **modo**. Pergunta de auditoria: *"o app roda em `debug=True` num lugar que eu alcanço — o que acontece quando eu faço uma rota qualquer quebrar?"* → cai na página de debug com um console de Python. Foreshadow do fix: **`debug=False`**.
3. **The tell — a página de debug vazando (OBRIGATÓRIO, ANTES do RCE).** `GET /items/abc` → a **página de debug do Werkzeug** volta. Apontar o **traceback**, o **código-fonte**, as **variáveis**, os **caminhos** vazados. Nomear: **information disclosure** — já um finding. Contraste imediato: no fixed, o mesmo request dá um **`500` genérico** (nada disso).
4. **Exploitation (Burp — o console; a prova é a resposta HTTP).**
   - **4a — baseline:** `GET /items/0` → resposta normal, idêntica nos dois lados.
   - **4b — disparar a exceção:** `GET /items/abc` → a página de debug (do passo 3).
   - **4c — extrair o segredo do console:** ler do HTML o **segredo** (candidato `SECRET = "..."`) e um **id de frame** (candidato `frm=<id>`). *(VERSION-DEPENDENT — a forma exata é confirmada rodando; ver "DECISÃO ABERTA".)*
   - **4d — emitir a requisição de execução:** candidato `GET /items/abc?__debugger__=yes&cmd=<python que roda `id`>&frm=<frame_id>&s=<secret>`. Com o **PIN off**, sem unlock → o comando **roda no servidor**.
   - **4e — a prova:** a **saída de `id` volta no corpo da resposta** (`uid=...`). RCE — comando do atacante executado no servidor. *(Secundário/contenção: `cmd` = `touch /tmp/pwned`, confirmado por `docker compose exec vulnerable ls -la /tmp/pwned`.)* Bloco colável no Repeater.
   - **§8 (cravar):** lab **isolado** (bind só `127.0.0.1`; container descartável); tudo **no Burp**; comando **benigno** (`id`/`touch`); **nada** destrutivo, nada de rede, nada sai do container. Num alvo real isso é **RCE** — manter os payloads demonstrativos.
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Ver "Beat 'o que a vuln NÃO é'".
6. **Impact (honesto — sem overclaim).** Ver "Impacto honesto".
7. **Why the fix works (porta 8133).** Repetir contra o `fixed/`:
   - No fixed, `debug=False`: o **mesmo** `GET /items/abc` → um **`500` genérico** (sem traceback interativo, sem código, sem variáveis, sem console). O request de eval do passo 4d → **não** há debugger pra atender (candidato: `500`/`404`; confirmar Fase 2). **Sem página de debug, sem segredo, sem console, sem RCE.**
   - **Prova de isolamento:** input benigno (`/items/0`) → resposta **idêntica** nos dois lados; **só** o input malformado + o `debug` separa (vulnerable → página de debug + RCE; fixed → `500` genérico). A diferença é **100% a flag `debug`**.
   - **A lição do diff:** o fix é **`debug=False`** (e, em produção, servir com um **WSGI real** — Gunicorn/uWSGI —, não o servidor de desenvolvimento). **NÃO** é "pôr o PIN" (nota #2 — derivável) nem "capturar a exceção" (nota #3 — esconde o gatilho, não fecha o debugger). (Forward pro DIFF.)

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Requests/responses/segredo/frame-id são **placeholders** da execução real capturada na Fase 2 (a página de debug real, o segredo real, o request de eval real, a saída de `id` real).

---

## Beat "o que a vuln NÃO é" (obrigatório — `CLAUDE.md` §5) — os QUATRO

Isola a causa e desmonta os mal-entendidos vizinhos (os quatro do brief):

- **(a) NÃO é "faltou tratar a exceção".** A exceção é só o **GATILHO**. **Prova de isolamento categórica:** o **mesmo** input malformado, no lado **fixed** (`debug=False`), dá um `500` genérico — a diferença é **100% o modo debug**, não a rota. Um error handler / `try/except` esconderia **este** erro, mas **não** fecharia o debugger: a **próxima** exceção não-tratada reabriria o console. O problema é o **debugger de dev exposto**, não o erro específico.
- **(b) NÃO é "faltou pôr o PIN".** O PIN é **derivável** (calculado de username + machine-id + MAC, e o traceback vaza vários desses dados) — **obstáculo, não proteção**. E o **console de dev não deveria estar exposto de qualquer forma**. Ligar o PIN tranca (mal) uma porta que não devia existir naquele ambiente. *(Neste átomo o PIN está `off` — a misconfig realista de "debugar mais fácil" — mas mesmo ligado não seria o fix.)*
- **(c) NÃO é injection.** Você **não** injetou código num parser/interpretador/shell — você **caiu num console que o próprio framework expõe** em modo dev e **digitou** Python. Nenhum input seu "virou código": o console de execução **já estava aberto**. *(Contraste com 09/20 — ver a tabela: lá o dado do atacante vira/carrega código; aqui não.)*
- **(d) NÃO é bug da aplicação.** O código da rota pode estar **correto** — converte e olha um item. A falha é de **CONFIGURAÇÃO** (modo de dev ligado num ambiente alcançável), não de lógica. É por isso que é **A05 — Security Misconfiguration**, não um bug de código.

**O que É (prova):** o app roda em modo de desenvolvimento com o debugger do Werkzeug **exposto**; qualquer exceção não-tratada abre uma página que **vaza** (código/variáveis/caminhos) e oferece um **console** que **executa Python no servidor**. A **única** correção é **`debug=False`** (e servir com WSGI real em produção).

---

## Impacto honesto

**Information disclosure + RCE (Remote Code Execution).** Duas metades, ambas a cravar: (1) a página de debug **vaza** o traceback, o código-fonte, os valores das variáveis e os caminhos do servidor — **information disclosure** por si só; (2) o **console** executa **Python arbitrário no processo do servidor** — **RCE**, o teto. **Mesmo teto de RCE do `command-injection-basic` (09) e do `deserialization-pickle` (20)**, por **causa distinta** (debugger de dev exposto vs shell vs desserializador). **Sem overclaim:** o finding é **info disclosure + RCE no container do app** — **NÃO** inflar pra "comprometimento total da infra" (RCE no container já é o topo do átomo), **NÃO** modelar escalada além disso. A **prova do lab é benigna** (o `id` na resposta, o marcador `/tmp/pwned`). A classe "misconfiguration" tem **outras faces** (outros defaults/estados de deploy perigosos) — **descrição de UMA linha da classe**, **sem** modelar nem nomear átomo/variante/técnica futura (foreshadow, Nota 2). Sem foreshadow.

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Categoria A05 — átomo dentro de família publicada; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`command-injection-basic` (09) e `deserialization-pickle` (20)** — o contraste **central** (seção dedicada + tabela). Mesmo teto (RCE), causa/classe/superfície/fix diferentes. *"Mesmo loot, três portas completamente diferentes."* Referência pra **trás**, permitida.
- **`xxe-basic` (18) e `xxe-blind-oob` (30)** — **irmãos A05**. Reusar a estrutura de doc e o enquadramento "A05 — Security Misconfiguration". Contraste de sub-forma: os XXE são misconfig de **parser XML** (default perigoso); o 33 é misconfig de **framework/deploy** (modo de dev alcançável). Referência pra **trás**, permitida.
- **`crypto-weak-hash` (31) e `crypto-ecb-mode` (32)** — a **voz/estrutura ATUAL** (abertura seca, definir termo, título=classe, headers PT traduzidos, honestidade-em-camadas nas notas-armadilha). Molde de voz. **`sqli-union-basic` (01)** — molde canônico de código/doc (single-container Flask). Citáveis.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5; e esta spec é pública):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer** átomo/categoria/variante/técnica futura por número, nome, slug **OU** descrição — inclusive **outros A05 futuros**, "próxima fase", "outras misconfigurações" modeladas como átomo futuro, ou a posição/ordinal/release de fase.
- **PROIBIDO anunciar posição de fase (abrir/fechar/ordinal/"primeiro de"/"penúltimo"), versão/release, ou a sequência de átomos ao redor** — **inclusive** enquadrar o átomo como "o que abre a A05-misconfig-de-framework". O átomo — **e esta spec** — se descreve **isolado**. Nas frases que proíbem foreshadow, manter a proibição **genérica** (sem listar nomes/slugs de átomos não-publicados).
- Que "misconfiguration tenha outras faces" é, no máximo, **descrição conceitual de UMA LINHA** — **sem** nomear átomo/variante/técnica futura. Na dúvida, mandar o aluno aprofundar na PortSwigger Academy / OWASP.

**LIMITE DE ESCOPO:** o 33 vai até **disparar uma exceção → cair na página de debug do Werkzeug (info disclosure) → usar o console pra executar um comando benigno no servidor (RCE)**, provado pela resposta HTTP (+ o marcador contido). **Uma vuln, uma causa (o modo de desenvolvimento com o debugger exposto — `debug=True` + PIN off num ambiente alcançável), um fix (`debug=False`, servindo com WSGI real em produção).**

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar.**

- **PortSwigger PRIMEIRO — candidato "Information disclosure".** A PortSwigger Academy tem um tópico conceitual de **Information disclosure** (candidato de URL a confirmar por fetch: `https://portswigger.net/web-security/information-disclosure`), que cobre explicitamente **debug pages / verbose error messages / debug modes** como fonte de disclosure — encaixa na **metade *information disclosure*** deste átomo (o traceback vazando). **A Fase 2 DEVE buscar por fetch** e confirmar se a página conceitual serve (título "Information disclosure" / framing "What is information disclosure?"). **Ressalva honesta:** a PortSwigger provavelmente **não** cobre a metade *RCE via console de debugger* — se a página de Information disclosure encaixar limpo pra o enquadramento conceitual, usá-la e cobrir a metade RCE no corpo do átomo; se **não** houver página conceitual limpa, ir pro fallback.
- **FALLBACK justificado (se preciso): OWASP Security Misconfiguration.** Candidato de URL a confirmar por fetch: a página do **A05:2021 – Security Misconfiguration** no site do OWASP Top 10 (`https://owasp.org/Top10/A05_2021-Security_Misconfiguration/`), ou o cheat sheet aplicável. **É um desvio consciente da convenção "PortSwigger" do §5** — a fonte OWASP é autoridade canônica de misconfiguration e cobre exatamente a classe (incluindo debug features habilitadas), e o `CLAUDE.md` §14 já credita OWASP. **AVISAR o mantenedor explicitamente** de que este átomo pode divergir da fonte-padrão do primer, e por quê (mesmo padrão do 31/32).
- **Secundário (opcional):** a doc oficial do Flask/Werkzeug sobre o servidor de desenvolvimento e o modo debug (o aviso "do not use the development server in production" e a caixa sobre o debugger). Complemento canônico — **opcional**; confirmar a URL por fetch.
- **Texto do link:** preservar o nome da página em **inglês** também no README PT (`CLAUDE.md` §7).
- **NÃO inventar URL nem grafia** — confirmar por fetch na Fase 2; se não conseguir verificar, **perguntar ao mantenedor** (`CLAUDE.md` §5).

---

## A trilha e a ferramenta — Burp-only, sem browser

O ataque inteiro é **HTTP dirigível no Burp** (Repeater); **a prova é a resposta HTTP**. Disciplina (`CLAUDE.md` §3.3):

- **Mostrar o passo a passo no Burp:** disparar a exceção (input malformado), ler a página de debug na resposta, extrair o segredo do HTML, montar o request de eval (query params), reenviar, capturar a saída do comando na resposta. **Tudo no Burp.**
- **O console "nasceu" pra browser** (você clicaria no ícone de console dentro do traceback), **mas reproduz melhor no Repeater** — controle cru dos params, do encoding e do segredo. **A prova NÃO exige execução client-side** (o que executa é Python **no servidor**, e a saída volta na resposta) → **browser não faz parte da trilha** (`CLAUDE.md` §3.3: browser só quando a prova exige — aqui não exige). **SEM trilha browser.**
- **SEM** ferramenta offline (não se quebra nada), **SEM** cracker, **SEM** listener OOB. Single-container, tudo local.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A05 — Security Misconfiguration** (`atoms/A05-security-misconfiguration/`, **JÁ EXISTE — reaproveitar**) | ROADMAP lista `debug-enabled` em A05; `CLAUDE.md` §4 fixa a pasta (irmãos XXE 18/30). Situar em A05 **sem arqueologia**. |
| Posição / fase | Ver `ROADMAP.md` (única superfície autorizada) | Release **fora da spec/conteúdo** (Nota 2). Spec pública nasce **limpa** de foreshadow. |
| Topologia | **SINGLE-CONTAINER por lado** — 2 serviços, **stateless (sem DB)** | Molde do `01` sem SQLite; nada a semear (só uma rota que quebra). |
| Estado | **Stateless** — sem usuário/sessão/dado | A vuln é o modo de deploy, não um dado. |
| Lição-coração | **Modo de desenvolvimento (debugger) exposto: `debug=True` + PIN off num ambiente alcançável. Fix = `debug=False` (+ WSGI real em prod), NÃO "pôr o PIN" nem "capturar a exceção".** | Qualquer exceção não-tratada abre uma página que vaza (disclosure) e um console (RCE). |
| Sub-lição crítica | **A causa é uma FEATURE DE DEV exposta; a exceção é só o GATILHO** | Error handler esconde o erro, não fecha o debugger; o PIN é derivável. |
| Contraste central | **`09` (command-injection) + `20` (deserialization-pickle)** — mesmo teto RCE, causa diferente | Justifica o átomo. 09 = shell executa input costurado; 20 = desserializador roda bytes; 33 = console de dev já exposto (nada injetado). |
| Contraste de apoio | **`18`/`30` (XXE)** — irmãos A05 (misconfig de parser vs de framework/deploy); **`31`/`32`** voz atual; **`01`** molde | Publicados; ancoram a lição/voz. Sem foreshadow. |
| Eixo pedagógico | **Nada do atacante vira código — o console de execução já está exposto pelo framework** | O que separa do 09/20 (lá o dado vira/carrega código). |
| Tipo de átomo | **API-only JSON** (sem HTML, sem templates, sem browser) | A "UI" que ensina é a página de debug do Werkzeug (framework renderiza). **Alternativa de form registrada, não bloqueante.** |
| Trilha | **BURP-ONLY: Repeater; sem browser, sem ferramenta offline** | Ataque é HTTP; prova é a resposta HTTP; console reproduz melhor no Repeater; prova não exige client-side. |
| Flavor — **TRAVADO** | **App Flask API-only com `app.run(debug=True)` + `WERKZEUG_DEBUG_PIN=off`; uma rota-gatilho quebra com input malformado; atacante cai na página de debug e usa o console; a prova é a resposta HTTP** | A ÚNICA superfície é o modo debug. PIN off (não modelar o cálculo). Sem 2ª superfície. |
| PIN | **DESLIGADO (`WERKZEUG_DEBUG_PIN=off`); o cálculo NÃO é modelado** | Modelá-lo exigiria 2º bug + seria não-determinístico. O PIN vira o beat "o que a vuln NÃO é" (derivável). |
| Rota-gatilho — **candidato, confirmar** | **`GET /items/<idx>` → `ITEMS[int(idx)]`** (ValueError/IndexError) | Gatilho exato = probe da Fase 2 (int()/lookup/divisão). Logicamente correto; sem `try/except` de propósito. |
| O "tell" (disclosure na rede) | **input malformado → página de debug do Werkzeug vazando código/variáveis/caminhos** | Metade do impacto; mostrar ANTES do RCE. Fixed: `500` genérico. |
| Prova — **conceito TRAVADO, mecânica = probe** | **baseline → disparar exceção → tell (página de debug) → extrair segredo → eval por HTTP → `id` na resposta (RCE)** | Mecânica do eval (params/segredo/PIN) = DECISÃO ABERTA (Fase 2, rodando, VERSION-DEPENDENT). Fixed: `500` genérico, sem console. |
| Prova de RCE | **`id` na resposta (primário) + `touch /tmp/pwned` via `docker exec` (secundário/contenção)** | Console devolve a saída in-band → `id` na resposta é Burp-only puro; marcador prova contenção + contraste com fixed. §8 dobrada: benigno, contido. |
| Código vulnerable | **`app.run(..., debug=True)`** + `WERKZEUG_DEBUG_PIN=off` | O modo errado. Rota logicamente correta. |
| Código fixed | **`app.run(..., debug=False)`** (sem `PIN=off`) | Sem debugger; mesma exceção vira `500` genérico. |
| `app.py` vulnerable × fixed | **DIFERE** só na flag `debug` (+ ausência do `PIN=off`) | O fix vive no rodapé (`app.run`). |
| Fix (único eixo) | **`debug=True` → `debug=False`** (+ WSGI real em prod, contexto de deploy) | Correção na raiz. NÃO "pôr o PIN", NÃO "capturar a exceção". |
| Diff | **Uma flag** (a mais localizada do repo); **requirements IDÊNTICOS** | Diff pequeno, impacto enorme. Contraste com o 31 (lá o requirements diferia). |
| `requirements.txt` | **IDÊNTICOS** — Flask (+ Werkzeug pinado), mesmo pin nos dois lados | O fix é uma linha de código, não uma dependência. Werkzeug behavior-critical (pinar). |
| Werkzeug | **Vem junto do Flask (não à parte); BEHAVIOR-CRITICAL → pinar** | O protocolo do console é version-dependent (paralelo ao pin do PyJWT no `jwt-none-alg`). Confirmar a versão que reproduz. |
| "Só põe o PIN" | **Nota-ARMADILHA (honestidade): eleva a barra, mas é derivável — obstáculo, não fix** (nota #2) | Calculado de dados da máquina que o traceback vaza; o console não devia estar exposto. |
| "Só captura a exceção" | **Nota-ARMADILHA: esconde o gatilho, não fecha o debugger** (nota #3) | A próxima exceção não-tratada reabre o console. Sintoma vs causa. |
| WSGI real em prod | **Contexto de deploy legítimo, NÃO armadilha** (nota #5, honestidade) | Fix mínimo = `debug=False`; contexto completo = dev server + debug fora de produção. |
| Bibliotecas | **Flask (Werkzeug junto, pinado)** — os dois lados, mesmo pin | Sem ORM/DB/dep extra. Werkzeug behavior-critical (confirmar a versão). |
| Banner | **Obrigatório, num `GET /` JSON de aviso** (API-only) + README | `CLAUDE.md` §8.2. `GET /` não injetável. |
| Impacto | **Information disclosure + RCE.** Sem overclaim além de RCE no container. | Honesto; mesmo teto RCE do 09/20, causa diferente. Sem foreshadow. |
| Theory primer | **PortSwigger "Information disclosure" primeiro; possível fallback OWASP Security Misconfiguration** | Cobre a metade disclosure; RCE-via-console provável fora da Academy. Desvio consciente — avisar (molde 31/32). Confirmar por fetch. |
| Título (H1) | **`debug-enabled — Debug mode enabled in a reachable environment`** (classe, sem stack) | `CLAUDE.md` §5. Sem "Flask"/"Werkzeug"/"Python" no H1; o slug já qualifica. Grafia final na Fase 2. |
| Foreshadow | **ZERO pra frente** (inclusive na spec pública); **sem** "abre a A05-misconfig" | `CLAUDE.md` §5. Não nomear próximos átomos/posição/release. |
| Portas | **8033 / 8133** (bind só `127.0.0.1`) | `CLAUDE.md` §8 (dobrada — RCE). Single-container por lado. |
| §8 (RCE) | **Comando benigno (`id`/`touch`), contido no container, bind só `127.0.0.1`, nada destrutivo/rede** | Atenção DOBRADA — o exploit executa comando. Molde do 20. |

---

## O container

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** — **idênticos entre si SE o `PIN=off` for no `app.py`** (molde do `31`/`32`/`01`, **API-only → SEM `COPY templates`**):

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

- `app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=<True|False>)` no rodapé do `app.py`. **Sem `init_db()`** (stateless, sem SQLite).
- **Onde vive o `PIN=off` (Fase 2 decide, ver "Flavor"):** se no `app.py` do vulnerable → os `Dockerfile` ficam **idênticos** entre os lados (mais limpo). Se no ambiente → `ENV WERKZEUG_DEBUG_PIN=off` **só no `vulnerable/Dockerfile`** (ou `environment:` no compose do serviço vulnerable), e aí os `Dockerfile` diferem por essa linha. **Confirmar rodando qual forma desliga o PIN de fato na versão do Werkzeug.**
- **Reloader:** `debug=True` liga o reloader (spawna child + observa arquivos). No `python:3.11-slim` com `python -u` isso funciona; se causar ruído, `use_reloader=False` (mantém o debugger). Ortogonal — confirmar na Fase 2 que o `-u` + reloader não atrapalham a captura.

**`docker-compose.yml`** (molde EXATO do `31`/`32`/`01` — dois serviços, **sem** datastore, **sem** healthcheck/`depends_on`/rede; apps bind **só** `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8033:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8133:5000"
```

- **§8 (dobrada — RCE):** ambos publicam porta **só** em `127.0.0.1` — não é opcional aqui (o exploit executa comando no container). Sem datastore externo, sem rede nomeada. Stateless.
- **Confirmar na Fase 2** que `./atom up debug-enabled` sobe os dois e a rota-gatilho (`/items/0` OK, `/items/abc` quebra) funciona de primeira, e que o vulnerable renderiza a página de debug.

---

## DECISÃO ABERTA pra Fase 2 — a mecânica do console por HTTP (VERSION-DEPENDENT; registrar, NÃO travar)

A **mecânica exata do eval por HTTP** é **VERSION-DEPENDENT do Werkzeug** e deve ser **PROVADA rodando** (**NÃO** é preferência editorial). O que confirmar, com o candidato registrado:

- **O formato dos query params do debugger.** Candidato: `?__debugger__=yes&cmd=<python>&frm=<frame_id>&s=<secret>` (onde `__debugger__=yes` marca o request, `cmd` é o Python, `frm` é o id do frame, `s` é o segredo). **Confirmar os nomes e o formato exatos rodando.**
- **Como/onde o segredo do console aparece no HTML da página de debug.** Candidato: um bloco `<script>` com `SECRET = "<20 chars>"`. **Confirmar** onde/como o segredo e o **id de frame** (`frm`) aparecem no HTML.
- **Se o `PIN=off` de fato remove o passo de unlock na versão fixada.** Candidato: `WERKZEUG_DEBUG_PIN=off` desliga o PIN → o eval roda **sem** um passo prévio de `pinauth`. **Confirmar** que na versão fixada não há unlock (e onde o `PIN=off` precisa estar setado — env do Dockerfile/compose vs `app.py` — pra pegar).
- **O gatilho exato da exceção.** Candidato: `GET /items/<idx>` → `ITEMS[int(idx)]` (ValueError com `idx` não-numérico; IndexError com out-of-range). **Confirmar** que a exceção **escapa** pro handler de debug do Werkzeug (sem `try/except` na rota, sem errorhandler global) e abre a página. Ajustar o gatilho (int()/divisão/lookup) se necessário.
- **O comando-prova benigno exato.** Candidato: `cmd` que roda `id` (saída na resposta) + o marcador `touch /tmp/pwned`. **Confirmar** a forma de `cmd` que o console aceita (expressão vs statement) e captura a saída de `id` real.
- **A rejeição exata do fixed.** Candidato: `500` genérico pro input malformado; `500`/`404`/resposta genérica pro request de eval. **Confirmar** o comportamento observável do fixed.

**Protocolo (cravar):** registrar candidato, **rodar**, confirmar; capturar o **request/response real** (a página de debug, o segredo, o request de eval, a saída de `id`). **Se não reproduzir**, ajustar dentro do escopo travado (**debug on, PIN off**) — trocar a versão do Werkzeug pinada por uma que reproduza, ou o gatilho, ou a forma do `cmd` — e **PROVAR rodando**. **Se NADA reproduzir, PARAR e avisar o mantenedor — NÃO inventar** o request/response, o segredo, o formato dos params, ou a saída.

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes de design — exceto onde marcado "DECISÃO ABERTA".

1. **Baseline nos dois lados:** `GET /items/0` (input benigno) → resposta normal **idêntica** no vulnerable **E** no fixed. **VALIDAR.**
2. **O gatilho:** `GET /items/abc` (input malformado) → **exceção não-tratada** (que escapa pro handler de debug no vulnerable; vira `500` no fixed). **VALIDAR** que a exceção escapa (sem `try/except`/errorhandler que a capture).
3. **O TELL (VALIDAR RODANDO):** no **vulnerable**, o input malformado → **página de debug do Werkzeug** vazando **código-fonte, variáveis e caminhos**. **Capturar o HTML real** (o traceball, o trecho de código, o campo de console, o segredo embutido).
4. **O RCE (central — VALIDAR RODANDO; item frágil/version-dependent):** extrair o **segredo** do HTML + emitir a **requisição de execução** (params do debugger) → o comando **roda no servidor** e a **saída de `id` volta na resposta** (+ o marcador `touch /tmp/pwned` confirmado por `docker compose exec vulnerable ls -la /tmp/pwned`). **Capturar request/response reais e o comando-prova.** **Se não reproduzir, PARAR e avisar — NÃO inventar.**
5. **FIXED (8133):** o **mesmo** input malformado → um **`500` genérico** (sem traceback interativo, sem console); o request de eval → sem debugger pra atender. **SEM** página de debug, **SEM** segredo, **SEM** console, **SEM** RCE (e `docker compose exec fixed ls -la /tmp/pwned` → ausente). **Confirmar a ausência observável.**
6. **Prova de isolamento:** input benigno (`/items/0`) → resposta **IDÊNTICA** nos dois lados; **só** o input malformado + o `debug` separa (vulnerable → debug page + RCE; fixed → `500`). A diferença traça **PURO** à flag `debug`. **VALIDAR.**
7. **Uma vuln só:** **SEM** modelar o cálculo do PIN (PIN off), **SEM** leitura de machine-id/MAC, **SEM** leitura de arquivo, **SEM** injection, **SEM** 2ª superfície; o **único** diff funcional é a flag `debug` (+ o `PIN=off` ausente no fixed). **Confirmar por `diff`.**
8. **§8 (RCE, atenção DOBRADA):** comando-prova **benigno** (`id`/`touch`), **contido** no container, bind **só** `127.0.0.1` (8033/8133), **nada** destrutivo, **nada** de rede/fora-do-container; dados fake.
9. **Flask/Werkzeug instala/pina limpo (mesmo pin nos dois lados):** confirmar que a versão fixada **renderiza a página de debug** com `debug=True` **e reproduz o eval por HTTP com PIN off**. **Werkzeug behavior-critical** — pinar `Flask==<pin>` + `Werkzeug==<pin>` na versão que reproduz (paralelo ao pin do PyJWT no `jwt-none-alg`). **Se a versão que o Flask puxa mudar o protocolo do console, pinar o Werkzeug na versão que reproduz e documentar.**
10. **Theory primer confirmado por FETCH:** PortSwigger "Information disclosure" (candidato `https://portswigger.net/web-security/information-disclosure`) primeiro; **fallback OWASP Security Misconfiguration** (candidato `https://owasp.org/Top10/A05_2021-Security_Misconfiguration/`) se não encaixar. **Confirmar por fetch; avisar o mantenedor do desvio da fonte-padrão se cair no fallback.** **Não inventar.**
11. **DECISÃO ABERTA — mecânica do eval por HTTP** (seção dedicada): params, segredo no HTML, `PIN=off` sem unlock, gatilho, comando-prova, rejeição do fixed. **VOCÊ CONFIRME/PROVE NA FASE 2** rodando; se não reproduzir, **PARAR e avisar**.
12. **Diff isola só a flag:** o **ÚNICO** delta funcional entre `vulnerable/app.py` e `fixed/app.py` é a flag `debug` (+ o `PIN=off`); `GET /`, a rota-gatilho, os imports, o requirements são idênticos. **Confirmar por `diff`.**

**Bloqueante remanescente:** nenhum de decisão de vuln. **DECISÕES ABERTAS de Fase 2 (probe, não bloqueiam a spec):** a mecânica do eval por HTTP (seção dedicada); o gatilho exato (int()/divisão/lookup); a forma do `cmd` benigno; onde o `PIN=off` vive (env vs app.py); a versão do Werkzeug que reproduz; API-only vs form (recomendado API-only); a rejeição exata do fixed; a URL/grafia do primer por fetch (e o possível desvio OWASP). **Protocolo:** registrar candidato, **rodar**, confirmar; se não reproduzir, ajustar dentro do escopo travado (**debug on, PIN off**); se travar de vez, **PARAR e avisar — NÃO inventar** request/response, segredo, params ou URL.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **terceiro RCE do repo por uma porta nova** — mesmo teto que o `command-injection-basic` (09, shell) e o `deserialization-pickle` (20, desserializador), mas **aqui nada do atacante vira código**: o **console de execução já está exposto** pelo framework em modo debug, e o atacante só o **encontra** (disparando uma exceção) e o **usa**. **Abrir e fechar** na lição-coração: *modo de desenvolvimento (debugger) exposto (`debug=True` + PIN off); o fix é `debug=False` (+ WSGI real em prod), NÃO "pôr o PIN" nem "capturar a exceção".*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`20` (deserialization-pickle) INTEIRO** (molde do RCE — §8 atenção dobrada, payload benigno/contido, marcador via `docker exec`, o enquadramento "harmless here / on a real target this is RCE"), **`09` (command-injection)** (contraste de causa — RCE via shell), **`18`/`30` (XXE)** (irmãos A05 — estrutura de doc + enquadramento "A05 — Security Misconfiguration"; contraste de sub-forma), **`31`/`32` (crypto)** (voz/estrutura ATUAL — abertura seca, definir termo, título=classe, headers PT, honestidade-em-camadas nas notas-armadilha), **`01` INTEIRO** (molde canônico single-container Flask + estrutura de doc), esta spec. **Seguir o `CLAUDE.md` ATUAL** onde os irmãos divergirem — **NÃO** copiar encenação; **NÃO** copiar a arqueologia OWASP do 18; **headers de seção traduzidos em TODA doc PT** (§7); título = classe sem stack.
- **PONTO PEDAGÓGICO OBRIGATÓRIO (o brief):** o WALKTHROUGH **DEVE** (1) mostrar a **página de debug VAZANDO** (código/variáveis/caminhos) como o "tell" **ANTES** do RCE — o vazamento é **metade** do impacto; (2) provar o **RCE** com um comando **benigno e contido** (`id` na resposta + o marcador); (3) **definir Werkzeug / traceback / servidor-de-dev-vs-produção / WSGI / console / PIN DO ZERO** na 1ª ocorrência. **Sem esses três, o átomo não ensina a lição nem fica claro pro iniciante.**
- **O ponto técnico frágil é a mecânica do eval por HTTP (risco #4/#11) — VERSION-DEPENDENT.** Fazer o ataque de verdade e confirmar que reproduz o RCE com a saída na resposta. **Se não reproduzir com o candidato, ajustar dentro do escopo travado (debug on, PIN off) — versão do Werkzeug, gatilho, forma do `cmd` — e PROVAR rodando; se NADA reproduzir, PARAR e avisar — NÃO inventar** request/response, segredo, params ou saída.
- **Uma vuln só:** a **única** falha é o **modo debug exposto**. **A rota-gatilho pode estar correta** (o input benigno funciona igual nos dois lados); **NÃO** modelar o cálculo do PIN (PIN off), **NÃO** ler machine-id/MAC, **NÃO** ler arquivo, **sem** injection; o `fixed` muda **SÓ** a flag `debug` (+ ausência do `PIN=off`). **SEM 2ª superfície.**
- **A SUTILEZA que NÃO pode enfraquecer a lição:** o fix é **`debug=False`** (e, em prod, WSGI real), **NÃO** "pôr o PIN" (armadilha #2 — derivável) nem "capturar a exceção" (armadilha #3 — esconde o gatilho, não fecha o debugger). **Ser honesto** (notas #2/#3/#5): o PIN eleva um pouco a barra mas é derivável; o error handler trata o sintoma; o WSGI real é contexto de deploy legítimo (não armadilha), com o fix mínimo sendo a flag.
- **Impacto honesto:** **information disclosure + RCE**; **não** inflar além de RCE no container. A metade disclosure é **metade do impacto** — mostrar antes do RCE. "Misconfiguration tem outras faces" só como **descrição da CLASSE** (uma linha), **sem** nomear átomo/variante/técnica futura.
- **`requirements.txt` IDÊNTICOS entre os lados** (contraste com o 31): vulnerable = fixed = `Flask` (+ `Werkzeug` pinado), mesmo pin. O DIFF contrasta honestamente com o 31 (lá o fix trazia uma lib; aqui é uma linha de código). **Werkzeug behavior-critical — confirmar/pinar a versão que reproduz** (paralelo ao PyJWT no `jwt-none-alg`).
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** os quatro — **(a)** não é "faltou tratar a exceção" (a exceção é o gatilho; prova categórica: mesmo input + `debug=False` no fixed dá `500` genérico); **(b)** não é "faltou o PIN" (derivável — dados da máquina que o traceback vaza; o console não devia estar exposto); **(c)** não é injection (o console já está aberto; nada do atacante vira código); **(d)** não é bug da aplicação (a rota pode estar correta; a falha é de CONFIGURAÇÃO — A05).
- **Contraste com 09/20 (cravar):** tabela (3 colunas: 09/20/33) + prosa; mesmo teto RCE, causa/superfície/fix diferentes; o ponto afiado é "só no 33 nada do atacante vira código". **Contraste com 18/30** (irmãos A05: misconfig de parser vs de framework/deploy). Citar `09`/`20`/`18`/`30`/`31`/`32`/`01` (publicados) à vontade.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5 + o brief):** Werkzeug, traceback, servidor de desenvolvimento vs produção, WSGI, console interativo do debugger, PIN do debugger, RCE, information disclosure. **DO ZERO** — o átomo é denso de bastidor.
- **A05 sem arqueologia:** situar em **A05 — Security Misconfiguration**, explicar **por que** (feature de dev exposta em ambiente alcançável — estado de deploy perigoso), **sem** contar edições OWASP antigas. **NÃO copiar** a nota de mapeamento "era A4 em 2017" do 18 (o 33 segue a regra atual, como 20/32).
- **Título = classe sem stack (`CLAUDE.md` §5):** H1 candidato `debug-enabled — Debug mode enabled in a reachable environment`. "Flask"/"Werkzeug"/"Python" no corpo, não no H1 (o slug já qualifica). Grafia final na Fase 2.
- **Política de referência cross-átomo:** OK citar **09/20** (contraste central), **18/30** (irmãos A05), **31/32** (voz), **01** (molde), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria/técnica futura por número, nome, slug **ou** descrição — inclusive a posição/ordinal/release de fase, "abre a A05-misconfig-de-framework", ou outros A05 futuros. **Manter as proibições genéricas.** **Esta spec é pública — nasce limpa de foreshadow.**
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). **H1 idêntico em EN e PT** (`debug-enabled — Debug mode enabled in a reachable environment`, grafia exata confirmável na Fase 2). **Headers de seção traduzidos em TODA doc PT** (§7 — nenhum header `##`/`###` PT byte-idêntico ao par EN, salvo o H1 do README). Termos técnicos (Werkzeug, traceback, WSGI, debugger, console, PIN, debug mode, development/production server, RCE, information disclosure, payload) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): PortSwigger "Information disclosure" primeiro; **possível fallback OWASP Security Misconfiguration** — **avisar o mantenedor do desvio da fonte-padrão se cair no fallback** (molde do 31/32); nome da página em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **A trilha é Burp-only:** disparar a exceção, ler a página de debug, extrair o segredo, montar o eval, capturar a saída — **tudo no Burp** (Repeater). **SEM** browser (a prova não exige client-side; o console reproduz melhor no Repeater), **SEM** ferramenta offline.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, no padrão das linhas anteriores (candidato — ajustar na Fase 2): `` Added atom 33: `debug-enabled` — Debug mode enabled in a reachable environment: a Flask app runs with app.run(debug=True) and the debugger PIN disabled, so any unhandled exception (a malformed value crashing an ordinary route) renders Werkzeug's interactive debug page — which leaks source, variables and paths (information disclosure) and embeds a console that runs arbitrary Python in the server process; the attacker triggers the exception, lifts the console secret from the debug page HTML, and issues an HTTP request that executes a command on the server (RCE), all from Burp Repeater; the fix is debug=False (and serving behind a real WSGI server in production), which turns the same exception into a generic 500 with no traceback and no console (A05 Security Misconfiguration, CWE-489 candidate — confirm). `` **Confirmar o CWE por fetch na Fase 2** (candidatos: CWE-489 "Active Debug Code"; CWE-215 "Insertion of Sensitive Information Into Debugging Code" pra a metade disclosure; não inventar). **NÃO** cortar a versão/taggear/anunciar release.
- **ROADMAP.md:** marcar o átomo 33 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline (`/items/0` idêntico nos dois lados) → o gatilho (`/items/abc` quebra) → o tell (página de debug vazando) → o ataque real (extrair o segredo → eval por HTTP → `id` na resposta + marcador) → o que a vuln NÃO é → fixed (`500` genérico, sem console). Portas host podem não ser alcançáveis do sandbox — ver a memória `validating-atoms-via-docker-exec` (fallback: `docker exec` + dirigir o app de dentro do container com `python http.client`/`curl`). **Sem** browser (a prova é a resposta HTTP). O eval por HTTP é dirigível de dentro do container/sandbox pra validação, mesmo que o WALKTHROUGH do aluno mostre no Burp.
- **Commits sem trailer `Co-Authored-By`** (memória `commit-no-coauthor-trailer` — a história deste repo é limpa do trailer; usar a mensagem do mantenedor verbatim). **Nesta fase de spec, NÃO commitar de qualquer forma.**
- **Portas:** `127.0.0.1:8033` (vulnerable), `127.0.0.1:8133` (fixed). Bind **só** `127.0.0.1` (§8 dobrada — RCE). Single-container por lado (2 serviços, sem datastore, stateless).
- Se houver dúvida sobre a mecânica do eval por HTTP, a versão do Werkzeug, onde o `PIN=off` precisa estar, o gatilho exato, a forma do `cmd` benigno, a URL/grafia do primer (e o desvio OWASP), o CWE, ou se o RCE não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code **propõe**, o mantenedor **decide**). **Candidato, se você quiser um pointer de recall reusável** — o mais provável de servir a este átomo (e a qualquer futuro que mexa com o servidor de dev do Flask) é a **mecânica do console do Werkzeug por HTTP** e o **pin behavior-critical do Werkzeug**, mas boa parte disso fica **registrada nesta spec commitada** (a regra desaconselha duplicar o que o repo grava). O que **justificaria** uma memória é a parte **não-repo, de ambiente/ferramenta**, e **só depois de confirmada rodando na Fase 2** (agora seria candidato não-verificado):

- **`werkzeug-debugger-http-eval`** (candidato — **gravar só após provar na Fase 2**) — *"O console interativo do debugger do Werkzeug (ligado por Flask `debug=True`) executa Python por HTTP via query params `?__debugger__=yes&cmd=<python>&frm=<frame_id>&s=<secret>`, onde o segredo por-processo vem embutido no HTML da página de debug (candidato `SECRET = \"...\"`). `WERKZEUG_DEBUG_PIN=off` desliga o PIN e remove o unlock. VERSION-DEPENDENT — pinar `Werkzeug==<versão que reproduz>` (behavior-critical, paralelo ao pin do PyJWT). Confirmar params/segredo/PIN por versão. Usado no átomo `debug-enabled` (33)."* — tipo `reference`. **Confirmar os detalhes rodando ANTES de gravar** (senão vira memória de fato não-verificado).

**Ressalva:** só vale gravar se você quiser esse pointer pra futuros átomos que toquem o dev server do Flask/Werkzeug; e **só depois de a Fase 2 provar a mecânica** (agora é candidato). Senão, já está aqui na spec. Sua decisão. *(Ortogonal: as memórias relevantes na Fase 2 são `validating-atoms-via-docker-exec` — dirigir o app de dentro do container se as portas host não forem alcançáveis; e `commit-no-coauthor-trailer` — commits sem o trailer, na Fase 2.)*
