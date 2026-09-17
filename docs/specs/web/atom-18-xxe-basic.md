# Spec — Átomo 18: `xxe-basic`

> Documento de especificação para o Claude Code implementar o décimo-oitavo átomo do projeto `atomicvulns` (Fase 4 — "Server-side Avançado", milestone `v0.4.0`). Este átomo é o **TERCEIRO átomo da Fase 4** (3º dos cinco — `16 ssrf-blind-oob`, `17 ssrf-cloud-metadata`, **`18 xxe-basic`**, `19`, `20`; confirmado no `ROADMAP.md`) e **MUDA DE EIXO**: **sai do arco de SSRF (A10, fechado no 17)** e **abre uma categoria nova — XXE, sob A05**. É o **PRIMEIRO átomo A05 do repo**: a pasta `atoms/A05-security-misconfiguration/` **NÃO existe** — este átomo a **cria** (exatamente como o átomo 15 criou a `A07-*`). **NÃO fecha a Fase 4** (o **20** fecha).
>
> **NÃO tem átomo-irmão pra espelhar.** Diferente do 16/17 (que herdaram a infra e o *flavor* in-band do `04 ssrf-basic`), o 18 abre categoria e **não tem antecessor A05**. O molde a seguir é o dos **átomos HTML single-container clássicos** (`01 sqli-union-basic`, `03 idor-numeric-id`): **VOLTA AO SINGLE-CONTAINER** (só `vulnerable` + `fixed`) depois de dois átomos multi-container (16/17). **NÃO há listener, mock, nem serviço extra. NÃO superengenheirar a infra.**
>
> **A lição em uma linha:** um parser de XML que **resolve entidades externas** deixa o atacante declarar uma entidade que aponta pra um arquivo do servidor (`file://`) — e o **conteúdo desse arquivo é refletido de volta na resposta**. O atacante **lê arquivos arbitrários do servidor** via um documento XML malicioso. O fix é **desabilitar entidades externas (e DTD) na config do parser**.
>
> **A decisão que faz o átomo existir (a "Saída B" do 18):** o vulnerable **USA `lxml`, NÃO o `xml.etree.ElementTree` da stdlib** — porque a nativa **não resolve entidades externas** (não seria vulnerável). Mesmo movimento honesto do 14 (PyJWT recusa a key confusion ingênua) e do 15 (`flask.session` resiste à fixation por design): *a ferramenta padrão já mitiga o bug ingênuo, então o átomo modela o parser onde a vuln realmente vive.* Detalhe em "A decisão estrutural".
>
> Leia junto com `CLAUDE.md` (Seção 3.3 — este átomo **TEM HTML e trilha dupla**, NÃO é API-only; §5 — passo "o que a vuln NÃO é" obrigatório e política de referência/foreshadow cross-átomo; §6 — didático > realista; §8 — segurança, **bind `127.0.0.1`** e §8.3/§8.4 **NENHUM segredo real**; e a seção "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (o molde canônico de HTML/Jinja2 mínimo, single-container, e de WALKTHROUGH de trilha dupla, pra onde o 18 volta) e o **`idor-numeric-id` (03)** (molde de `docker-compose.yml`/`Dockerfile` single-container). O átomo publicado mais recente (`17 ssrf-cloud-metadata`) serve **só pela VOZ/estrutura de docs** — **NÃO** pela infra (o 17 é multi-container; o 18 **não** é). Os specs do `14 jwt-key-confusion` e do `15 session-fixation` servem pelo **padrão da "Saída B"** (a ferramenta padrão às vezes já mitiga; aqui, a **biblioteca de XML importa**).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição na Fase 4: 18 é o 3º átomo e ABRE a categoria A05 (confirmado; sem discrepância)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A Fase 4 ("Server-side Avançado", `v0.4.0`) tem **cinco** átomos — `16 ssrf-blind-oob` (`[x]`), `17 ssrf-cloud-metadata` (`[x]`), **`18 xxe-basic`** (`[ ]`, ESTE), `19` (`[ ]`), `20` (`[ ]`). O **16 abriu a fase**; o 17 foi o 2º; o **18 é o terceiro** e **NÃO fecha a fase** (o **20** fecha). Os átomos 01–17 já estão `[x]` em `main`.
>
> **Primeiro átomo A05 do repo — a categoria abre aqui.** O `ROADMAP.md` (linha 108) lista **`18. xxe-basic — A05 Security Misconfiguration`** com a justificativa *"introduz XML externo, leitura de arquivo via entity."* A pasta `atoms/A05-security-misconfiguration/` **NÃO existe ainda** — o 18 a **cria** (o mesmo movimento do `15 session-fixation`, que criou `atoms/A07-auth-failures/`). O átomo mora em `atoms/A05-security-misconfiguration/xxe-basic/`.
>
> **Sobre o rótulo A05 (nuance de mapeamento OWASP — resolver na prosa do átomo).** No **OWASP Top 10 2021** (a edição que o projeto segue, `CLAUDE.md` §4), **A05 é "Security Misconfiguration"**, e **XXE foi *dobrado* pra dentro dessa categoria** (na edição **2017**, XXE tinha categoria própria, **A4-XXE**). O nome de pasta canônico já está fixado no `CLAUDE.md` §4 (árvore do repo): **`A05-security-misconfiguration/`**, com `xxe-basic/` dentro. **Espelhar exatamente esse padrão de nomenclatura** (`A0N-<categoria-em-kebab>`, como as pastas existentes `A01-broken-access-control`, `A02-cryptographic-failures`, `A03-injection`, `A07-auth-failures`, `A10-ssrf`). Uma **nota de uma linha no README/DIFF** explicando o mapeamento (*"no Top 10 de 2021, XXE está dobrado em A05 Security Misconfiguration; tinha categoria própria — A4 — em 2017"*) é **didática e legítima** (contexto de classe, não foreshadow) e ajuda o aluno que aprendeu "XXE = A4" em material antigo a situar o átomo. Recomendo incluí-la, breve.

## Nota de planning 2 — versionamento/release fica FORA desta spec

> O 18 **não fecha** a Fase 4 (o 20 fecha), então **não dispara** release. Versionamento/CHANGELOG/tag/anúncio é **trabalho de release do mantenedor**, não de átomo — não entra nesta spec nem no conteúdo do átomo (`CLAUDE.md` §10.4). A única pegada de changelog é uma **linha em `[Unreleased] / Added`** na Fase 2 (ver "Notas específicas pro Claude Code"). O átomo se descreve como "átomo 18, o que abre a categoria A05/XXE", **sem** anunciar release nem foreshadowar a fase/os átomos seguintes.

---

## Identidade

- **ID:** `xxe-basic`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A05 — Security Misconfiguration**. Pasta `atoms/A05-security-misconfiguration/` (**NÃO existe — o 18 a cria**). Confirmado contra o `ROADMAP.md` ("A05 Security Misconfiguration") e o `CLAUDE.md` §4. **Primeiro átomo desta categoria no repo.** Em prosa (README/DIFF) usar o nome da classe — **"XML External Entity (XXE) injection"** — e situá-la em A05 (ver Nota de planning 1).
- **Pasta:** `atoms/A05-security-misconfiguration/xxe-basic/`
- **Número sequencial:** 18
- **Porta vulnerable:** `127.0.0.1:8018`
- **Porta fixed:** `127.0.0.1:8118`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos single-container 01/03.
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM serviço extra, SEM rede especial, SEM listener/mock.** Volta ao molde do 01/03 depois do multi-container do 16/17.
- **Fase / milestone:** Fase 4, `v0.4.0`. **Terceiro átomo da Fase 4; NÃO fecha a fase** (o 20 fecha). Versionamento/release **fora desta spec** (Nota de planning 2).
- **Branch de trabalho:** `atom/xxe-basic`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de XXE** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/xxe`** (título da página: **"XML external entity (XXE) injection"**). **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7):** candidato **`# xxe-basic — XML External Entity (XXE) injection`** — `id` + nome canônico da vuln em inglês (a forma que a PortSwigger usa na página). Texto exato / qualificador confirmável na Fase 2; **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**XML External Entity (XXE) injection — leitura de arquivo in-band.** Uma app web com uma feature que **recebe um documento XML, parseia, e reflete um campo dele de volta** na resposta. Como o parser (`lxml`) **resolve entidades externas**, um documento com um `DOCTYPE` que declara uma entidade **SYSTEM** apontando pra `file:///etc/passwd` faz essa entidade **expandir pro conteúdo do arquivo**; quando a app **ecoa o campo** onde a entidade foi usada, o **conteúdo do arquivo do servidor volta na resposta**. É **leitura de arquivo arbitrário** via um XML malicioso.

### A lição-coração

> **"Um parser de XML que resolve ENTIDADES EXTERNAS deixa o atacante definir uma entidade que aponta pra um arquivo do servidor (`file://`) — e o conteúdo desse arquivo é refletido de volta na resposta. O atacante lê arquivos arbitrários do servidor via um documento XML malicioso. O fix é desabilitar entidades externas (e DTD) na config do parser."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** XML permite **DTD** (Document Type Definition), e DTD permite **declarar entidades** — inclusive entidades **EXTERNAS** (`SYSTEM`) que apontam pra uma URI. Se o parser **resolve** essas entidades, um payload como:

```xml
<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]>
```

faz a entidade `&x;` **expandir pro CONTEÚDO do arquivo**. A app então **ecoa `&x;`** (no campo onde ela foi usada) na resposta → **leitura de arquivo**. **Não há bug de lógica na app**; o bug é a **CONFIG do parser** (o default perigoso do `lxml`, que resolve entidade externa local).

### Sub-lição (cravar)

A diferença entre `vulnerable` e `fixed` **NÃO é a lógica da app** — as duas parseiam o XML e ecoam um campo, **byte-idênticas em tudo menos numa coisa**. A diferença é **UMA config do parser**: resolver entidades externas **vs** não resolver. **Bug pontual, na configuração do parser.** Esta é a sub-lição que o "o que a vuln NÃO é" (§5) tem que blindar: o aluno não pode sair achando que "processar XML é o bug" ou que "a app tem um bug de lógica na importação".

### Contraste conceitual com o repo (categoria nova; sem irmão A05 pra espelhar)

Não há átomo A05 publicado pra contrastar; o contraste é **conceitual**, com átomos publicados:

- **XXE é INJEÇÃO, mecanicamente.** Como no `sqli-union-basic` (01) e no `command-injection-basic` (09), há **input não-confiável interpretado por um MOTOR** (aqui, o parser de XML) que **faz mais do que devia** — no SQLi o motor é o SQL engine, no command-injection é o shell, aqui é o parser XML resolvendo entidades. A frase-âncora: *injeção é sempre input caindo num motor que o interpreta com poder demais.* **Mas** o 18 mora em **A05 (Security Misconfiguration)**, não em A03 — porque a **causa-raiz e o fix são uma CONFIGURAÇÃO perigosa do parser** (um default ligado que devia estar desligado), não a construção de uma query. Esse é o motivo honesto de a mesma "cara de injeção" cair em A05.
- **Mesmo IMPACTO que o `path-traversal-basic` (10), porta diferente.** Os dois terminam em **leitura de arquivo arbitrário do servidor** (o clássico `/etc/passwd`), mas por **mecanismos distintos**: o 10 manipula um **caminho de arquivo** (`../../etc/passwd`); o 18 abusa da **resolução de entidade XML**. Contraste didático forte — *"mesmo loot, porta diferente"* — e ambos publicados, então o aluno abre e compara. Citar de leve (uma frase), sem virar tabela.

Referências a 01, 09 e 10 são **bem-vindas** (todos publicados, `CLAUDE.md` §5). **Foreshadow pra frente é PROIBIDO** (ver "Contraste / escopo / FORESHADOW").

### Por que A05 (Security Misconfiguration)

A causa-raiz é um **default inseguro do parser** deixado ligado (resolução de entidade externa) — uma **misconfiguration** do componente de parsing, não um erro de lógica de negócio. É por isso que o OWASP 2021 **dobrou XXE em A05**. Coerente com o eixo server-side da Fase 4.

---

## Uma vuln só — o eco é ESCAPADO, o `secret.txt` é DUMMY, sem billion-laughs, sem 2ª falha

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o parser **resolver entidade externa**. Garantias (todas validar na Fase 2):

- **O CAMPO ECOADO É ESCAPADO (moldura travada — não pode virar 2ª vuln).** A app **MOSTRA** o campo parseado (in-band, é o ponto — é como o aluno **lê** o arquivo), mas **SEMPRE escapado** (autoescape do Jinja LIGADO, num `<pre>`). O conteúdo do `/etc/passwd` aparece como **texto**, **não** como markup — **sem** virar XSS/HTML-injection. **Sem `|safe`, sem `Markup`, sem `render_template_string`.** O DIFF **deve** notar: *"o eco é escapado de propósito; a vuln é o XXE, não como o campo é exibido."*
- **SEM billion-laughs / entity-expansion DoS (subtileza crítica — não empilhar uma 2ª vuln).** Labs de XXE às vezes acidentalmente permitem **DoS por expansão exponencial de entidade** (a "billion laughs"). A vuln DESTE átomo é **LEITURA DE ARQUIVO** (external entity `SYSTEM file://`), **NÃO** expansão. O `lxml` **por default** protege contra isso (`huge_tree=False`, que limita expansão de entidade e profundidade) — **NÃO** setar `huge_tree=True` no vulnerable. **Validar na Fase 2** que um payload de expansão **não derruba o container** (o default do lxml deve capar). Se necessário, uma **nota em prosa** de que expansão de entidade é **outro vetor** — descrição da classe, **sem nomear átomo/variante futura**.
- **`/app/secret.txt` é DUMMY** (valor **obviamente falso**, `CLAUDE.md` §8.3/§8.4). **`/etc/passwd`** é world-readable e **não é segredo** (hashes ficam no `/etc/shadow`, que **NÃO se usa** — root-only, provavelmente `permission denied`, anticlímax; e seria segredo real por §8). Ver "Alvo da leitura".
- **`no_network=True` (default do lxml) mantém em `file://` puro → sem SSRF acidental.** Isso é o que **impede o átomo de pisar no arco A10** (fechado no 17): entidade `file://` lê arquivo local, mas `http://` **não** sai pra rede. Ver "A decisão estrutural" e DIFF nota #4.
- **Sem banco, sem segunda superfície:** nenhum SQLite/sessão/credencial de app; nenhum PII real. A **única** superfície é o parser resolvendo entidade externa.

---

## A decisão estrutural — `lxml`, NÃO `ElementTree` (a "Saída B" do 18): por quê (TRAVADA)

**O ponto que faz o átomo existir** — da **mesma família honesta** das "Saídas B" do 14 (PyJWT **recusa** a key confusion ingênua → o vulnerable verifica na mão) e do 15 (`flask.session` **resiste** à fixation por design → o vulnerable usa sessão server-side manual). Aqui a ruga é de **biblioteca de parsing**:

**O vulnerable USA `lxml`, NÃO o `xml.etree.ElementTree` da stdlib.** Motivo — é o **coração da honestidade do átomo**:

- O **`xml.etree.ElementTree` da stdlib NÃO resolve entidades externas.** Um átomo "vulnerável" construído sobre a nativa **não seria vulnerável** — ela ignora/rejeita entidades `SYSTEM` por design. **Mesma armadilha estrutural do PyJWT no 14 e do `flask.session` no 15:** a ferramenta padrão já mitiga o bug ingênuo.
- **`lxml` resolve entidade externa LOCAL por default** — é o parser onde a vuln realmente vive no mundo real (apps que trocaram a stdlib por lxml por performance/features, herdando o default perigoso). O DIFF/README **DEVE explicar POR QUE lxml e não a nativa** (senão o aluno pensa *"por que esse dev não usou o parser da stdlib?"*). Resposta honesta a cravar: *a stdlib resiste por design; a vuln vive em parsers que resolvem entidade — que é o que o átomo modela.* **Mesmo movimento honesto do 14/15.**

### O DEFAULT do `lxml` — a segunda ruga da "Saída B" (Fase 2 confirma; documentar os DOIS caminhos)

O comportamento **default** do `lxml` decide a forma exata do código vulnerable. **VALIDAR RODANDO na Fase 2** (o item central da Saída B):

- **Comportamento esperado (e por que é elegante pro átomo):** o `lxml` resolve entidade **LOCAL (`file://`)** no default (`resolve_entities=True` é o default histórico), **e por default NÃO acessa rede** (`no_network=True` é o default). Ou seja: o default lê **arquivo local** mas **não** faz request de rede. Isso é **perfeito** pro átomo — mantém em **LEITURA DE ARQUIVO PURA**, sem virar SSRF acidental, **sem pisar no arco A10 (fechado no 17)**.
- **CAMINHO 1 (preferido, se confirmado na Fase 2): "o default já te trai".** Se a versão fixada do `lxml` resolve `file://` **no comportamento default** (sem config explícita de entidade), o vulnerable **NÃO configura nada** de entidade — usa `etree.fromstring(xml_bytes)` (ou um parser com só `no_network=True` explícito por garantia) — e a lição é **"o default inseguro te trai"**. O diff então mostra o fixed **ADICIONANDO** as flags de segurança. **Lição mais forte e honesta** (um código de aparência inocente já é vulnerável).
- **CAMINHO 2 (Saída B, se a versão mudou): "ligar explícito".** Se a versão fixada tornou o default seguro (ou se a resolução da entidade do internal subset exigir opt-in), o vulnerable **liga a resolução EXPLICITAMENTE** (`resolve_entities=True, load_dtd=True`) e o DIFF explica que essa versão exige opt-in. O diff então **inverte as flags** (True → False).

**Nuance técnica a confirmar na Fase 2 (por que os dois caminhos existem):** a entidade fica declarada no **internal subset** do `DOCTYPE` (dentro do próprio documento). Com `resolve_entities=True`, o `lxml` expande `&x;`; a dúvida é se a expansão de uma entidade **`SYSTEM` (externa)** do internal subset acontece com o **bare default** ou exige `load_dtd=True`. **O Caminho 1 é o alvo; o Caminho 2 é o fallback garantido.** A Fase 2 testa o bare default primeiro (item 6 do checklist) e escolhe. **Recomendação:** liderar com o Caminho 1 se ele reproduzir; senão, Caminho 2. Em ambos, o **fixed é o parser endurecido** e a **única mudança é a config do parser**.

### `defusedxml` — NÃO usar (nota "mencionável, não aplicada", NOMEADA)

**NÃO adicionar `defusedxml`.** O suporte a `lxml` no `defusedxml` está **DEPRECADO** (o próprio projeto manda configurar o `lxml` direto). A defesa **limpa e atual** pra uma app `lxml` é **endurecer o próprio parser** (o fix deste átomo). O `defusedxml` **existe e é citável** no DIFF como opção histórica/para stdlib — **descrito, não aplicado** — mesmo movimento da nota do IMDSv2 no 17 (uma defesa real que se **menciona**, mas não é a forma que o átomo aplica). Ver DIFF nota #3.

---

## Decisões de infra JÁ TRAVADAS — implemente conforme, NÃO reabra

1. **SINGLE-CONTAINER.** Só `vulnerable` + `fixed`. **SEM** serviço extra, listener, mock, ou rede especial. Molde do 01/03. **NÃO** herdar a topologia multi-container do 16/17.
2. **IN-BAND, NÃO CEGO.** A app **parseia e MOSTRA** o campo. A resposta do `vulnerable` **ECOA** o conteúdo do arquivo (expandido da entidade); o `fixed` **não expande** → não vaza. A variante cega/OOB de XXE está **FORA de escopo** deste átomo (**NÃO mencionar como "próximo passo"** — ver FORESHADOW).
3. **`lxml`, NÃO `ElementTree`** (a Saída B — acima).
4. **App: Flask + `lxml`.** **NENHUMA** outra dependência: sem banco, sem `requests`, sem `defusedxml`. Ver "Bibliotecas".
5. **Alvo de leitura:** `/etc/passwd` (base image) + `/app/secret.txt` (plantado no Dockerfile, dummy). Ver "Alvo da leitura".

---

## Feature e endpoints — app web in-band (TEM HTML, molde do 01) — **DECISÃO SINALIZADA**

> **Este é o ÚNICO item que o prompt me pediu pra DECIDIR e SINALIZAR** (a feature/flavor que recebe o XML). Tudo o mais está travado. Abaixo, a escolha com justificativa; **NÃO gero código** — a Fase 2 gera.

### O flavor escolhido: **importador de contatos (contact importer)**

Uma app web mínima que **recebe um documento XML de contato e o "importa"**, ecoando de volta o **nome** do contato importado como confirmação. É onde **receber XML é natural** (address books / CRMs / cartões de contato em XML importam exatamente assim), o **form cabe no molde HTML mínimo** (um `<textarea>` com um XML de exemplo benigno pré-preenchido), e o **campo ecoado faz sentido no flavor** (um importador confirma o que importou mostrando o nome).

- **`GET /`** — serve o form: um `<textarea name="xml">` **pré-preenchido com um XML de contato benigno** (sem `DOCTYPE`), banner de aviso, dica de Burp. Renderiza `templates/index.html`.
- **`POST /import`** — recebe o XML (`request.form["xml"]`), **parseia com `lxml`**, extrai o campo **`<name>`**, e **ecoa** "Imported contact: `{name}`" num `<pre>` **escapado** (`templates/result.html`). É **onde a entidade externa expande** (o atacante põe `&x;` no `<name>`).
  - **VULNERABLE:** parser que **resolve entidade externa** → `&x;` expande pro conteúdo do arquivo → o arquivo volta no campo `name`.
  - **FIXED:** parser endurecido → entidade **não** expande → o `name` volta vazio **ou** o parse falha de forma controlada (a Fase 2 decide a forma exata da recusa; ver "O fix").

### Por que este flavor (e não os outros candidatos)

Pesados os três critérios do prompt — (a) o form cabe no molde HTML mínimo; (b) o campo ecoado faz sentido; (c) mínimo, sem segunda feature:

| Candidato | (a) cabe no `<textarea>`? | (b) campo ecoado natural? | (c) mínimo? | Veredito |
|---|---|---|---|---|
| **Contact importer** (escolhido) | ✅ textarea com um `<contact>` de exemplo | ✅ **"Imported contact: `<name>`"** — importador confirma o que importou | ✅ 1 endpoint, 1 campo ecoado | **Escolhido** — concreto, universal, o eco é feedback óbvio |
| API que aceita XML (SOAP-style) | ⚠️ mais natural como API-only (sem form) | ✅ | ✅ | Descartado: o prompt **travou que o 18 TEM HTML** (form + textarea); flavor de API pura contraria isso |
| Upload de config/feed XML | ✅ | ⚠️ "título do feed" é mais abstrato que "nome do contato" | ✅ | Descartado: mesma forma do contato, porém menos concreto pro aluno |

**Nome do endpoint (`POST /import`) e do campo (`<name>`)** são naturais pra "importar um contato". O **método pelo qual o aluno fala com a app** (`POST /import`) é independente do mecanismo da vuln (o parser resolvendo entidade). *(Se o mantenedor preferir outro flavor/endpoint, a Fase 2 ajusta; sigo o contact importer no resto da spec.)*

---

## O campo ecoado é ECOADO com ESCAPE (moldura — "um átomo = uma vuln")

A app **MOSTRA** o campo parseado (in-band, é o ponto — é como o aluno lê o arquivo), mas **SEMPRE escapado** (autoescape do Jinja, num `<pre>`). Mostrar o conteúdo lido **NÃO** pode virar 2ª vuln (XSS/HTML-injection): o conteúdo do arquivo é **dado**, não markup. O `result.html` ecoa o `name` num `<pre>` (escapado) — **espelhando como o `preview.html`/`result.html` dos átomos in-band renderizam corpo buscado**. **Sem `|safe`, sem `Markup`, sem `render_template_string`.** O DIFF nota: *"o eco é escapado de propósito; a vuln é o XXE, não como o campo é exibido."*

---

## O código — o coração no PARSER

Imports (vulnerable e fixed compartilham; a divergência é só a config do parser):

```python
import os
from lxml import etree
from flask import Flask, request, render_template
```

### `vulnerable/app.py` — parser resolve entidade externa, ecoa o campo (candidato — Fase 2 gera o real)

> **Forma-alvo (Caminho 1 — "o default trai", se confirmado na Fase 2):** o vulnerable **não configura entidade** — usa o default do `lxml`, que resolve `file://` local. Comentário crava que o código de aparência inocente já é vulnerável.

```python
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/import", methods=["POST"])
def import_contact():
    xml = request.form.get("xml", "")
    # VULNERABLE: parse untrusted XML with lxml's DEFAULT parser, which RESOLVES EXTERNAL
    # ENTITIES. A DOCTYPE with a SYSTEM entity (file://) is expanded, so an attacker-defined
    # entity reads a server file and its contents come straight back in the echoed <name>.
    # Classic XXE -- there is no bug in the import LOGIC; the bug is the parser's default.
    # (no_network stays at lxml's safe default: file:// is read but http:// is NOT fetched --
    # this is pure arbitrary file disclosure, not SSRF.)
    try:
        doc = etree.fromstring(xml.encode("utf-8"))          # default parser resolves &x;
        name = doc.findtext("name")
    except etree.XMLSyntaxError as exc:
        return render_template("result.html", name=None, error=str(exc))
    return render_template("result.html", name=name, error=None)  # autoescaped in a <pre>


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

> **Forma-garantida (Caminho 2 — Saída B, se o bare default não resolver a entidade SYSTEM do internal subset):** trocar a linha do parse por um parser **explícito**:
>
> ```python
> parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=True)  # dangerous
> doc = etree.fromstring(xml.encode("utf-8"), parser)
> ```
>
> Neste caso o DIFF explica que a versão exige opt-in, e o diff **inverte as flags** (True→False) em vez de mostrá-las sendo adicionadas.

### `fixed/app.py` — entidades externas e DTD DESABILITADAS (candidato — Fase 2 gera o real)

```python
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/import", methods=["POST"])
def import_contact():
    xml = request.form.get("xml", "")
    # FIXED: parse with external-entity resolution and DTD loading DISABLED. A SYSTEM entity
    # is never resolved, so file:// payloads cannot read server files. This is the canonical
    # XXE defense for an lxml app: turn off the dangerous parser features explicitly.
    # (defusedxml's lxml support is deprecated -- hardening the parser is the current advice.)
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    try:
        doc = etree.fromstring(xml.encode("utf-8"), parser)
        name = doc.findtext("name")
    except etree.XMLSyntaxError as exc:
        return render_template("result.html", name=None, error=str(exc))
    return render_template("result.html", name=name, error=None)  # entity neutralized; no leak


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

**Notas de implementação (validar na Fase 2):**

- **`.encode("utf-8")` de propósito:** `etree.fromstring` sobre uma `str` com declaração de encoding (`<?xml ... encoding=...?>`) levanta *"Unicode strings with encoding declaration are not supported"*. Passar **bytes** evita a armadilha e é o realista (o corpo chega como bytes). Os payloads do átomo não têm declaração, mas encodar é a forma robusta.
- **A forma exata da RECUSA do fixed (Fase 2 decide, DIFF documenta):** com `resolve_entities=False`/`load_dtd=False`, o `lxml` ou (a) **não expande** a entidade e `findtext("name")` volta **vazio/None** (campo vazio), ou (b) **levanta `XMLSyntaxError`** (entidade não definida) → cai no `except` → **mensagem de parse controlada**. **Nos dois casos: nenhum conteúdo de arquivo vaza.** Confirmar qual, e garantir que a mensagem de erro (se houver) **não carrega conteúdo de arquivo** (não carrega — o arquivo nunca é lido no fixed).
- **`findtext("name")`** volta o texto do primeiro `<name>`; com a entidade expandida no vulnerable, esse texto **é** o conteúdo do arquivo.
- **Sem `huge_tree=True`** em nenhum dos dois (mantém a proteção default contra billion-laughs — ver "Uma vuln só").
- **O eco é escapado** (`result.html`, `<pre>`, autoescape) — sem `|safe`/`Markup`/`render_template_string`.

---

## Alvo da leitura — dois arquivos, dois papéis (TRAVADO)

- **`/etc/passwd`** — **PRIMEIRO payload** do walkthrough. Clássico universal, world-readable, **sempre presente** no container (vem na base image `python:3.11-slim`), **NÃO é segredo** (os hashes ficam no `/etc/shadow`, que **NÃO se usa**). O "hello world" do XXE — prova a leitura de arquivo com um alvo que todo mundo reconhece.
- **`/app/secret.txt` (dummy)** — **SEGUNDO payload, o CLÍMAX.** Um arquivo **plantado na imagem** (uma linha no `Dockerfile`) com um segredo **OBVIAMENTE FALSO** (candidato: `FLAG-xxe-<hex>-EXAMPLE-not-a-real-secret`, ou uma fake API key/senha de brinquedo). Mostra o **impacto real**: *"li o segredo da PRÓPRIA app — um arquivo que jamais deveria sair dali."* É **DUMMY de lab** (`CLAUDE.md` §8.3/§8.4), **NÃO segredo real** — mesmo movimento das creds EXAMPLE do mock do 17.
- **`/app/secret.txt` é plantado nas DUAS imagens (`vulnerable` E `fixed`)** — assim a **ausência de vazamento no fixed é atribuível ao PARSER** (a entidade não expande), **não ao arquivo estar ausente**. Mesmo raciocínio do "mock alcançável das duas pontas" do 17. `/etc/passwd` também está nas duas (vem da base).
- **NÃO usar `/etc/shadow`** (segredo real por §8; e é root-only → provavelmente `permission denied`, anticlímax).

---

## O fix e o tipo de diff

**Fix:** **desabilitar entidades externas e DTD no parser** (`resolve_entities=False, load_dtd=False`, mantendo `no_network=True`). Tipo de diff: **lógica-diferente MÍNIMA** — a mudança é a **CONFIG DO PARSER** (a linha do `XMLParser` / do `fromstring`). Diff no ponto do parse. O resto (`GET /`, imports, o `render_template("result.html", ...)`, o `except`, rodapé, templates) é **byte-idêntico** entre vulnerable e fixed.

- **Se Caminho 1 (default trai):** o diff mostra o parser endurecido sendo **ADICIONADO** (default inseguro → parser seguro explícito).
- **Se Caminho 2 (opt-in):** o diff **inverte** as flags (`resolve_entities=True, load_dtd=True` → `False, False`).

Diff colável (candidato — **Caminho 1**; a Fase 2 gera o real conforme o comportamento confirmado):

```diff
 @app.route("/import", methods=["POST"])
 def import_contact():
     xml = request.form.get("xml", "")
-    # VULNERABLE: parse untrusted XML with lxml's DEFAULT parser, which RESOLVES EXTERNAL ENTITIES...
+    # FIXED: parse with external-entity resolution and DTD loading DISABLED...
+    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
     try:
-        doc = etree.fromstring(xml.encode("utf-8"))
+        doc = etree.fromstring(xml.encode("utf-8"), parser)
         name = doc.findtext("name")
     except etree.XMLSyntaxError as exc:
         return render_template("result.html", name=None, error=str(exc))
     return render_template("result.html", name=name, error=None)
```

**O CONTRASTE é o diff (obrigatório):** parser-que-resolve-entidade (vulnerable) vs parser-com-entidade-desabilitada (fixed). **A única mudança é a config do parser.**

### Notas obrigatórias no `DIFF.md`

1. **`lxml` vs `ElementTree` (a Saída B — obrigatória).** A stdlib (`xml.etree.ElementTree`) **não resolve entidade externa** → um átomo sobre ela **não seria vulnerável**. A vuln vive em `lxml`, que **resolve** entidade externa local. Explicar **por que o átomo usa `lxml`** (a nativa resiste por design; o átomo modela o parser onde o bug realmente mora) — **mesmo movimento honesto do 14 (PyJWT) e do 15 (`flask.session`)**.
2. **O DEFAULT do `lxml` é perigoso (resolve entidade local): "o default te trai".** A lição é que a **config default** te trai; o fix é **desligar as flags perigosas explicitamente**. (Ajustar conforme a Fase 2: se o vulnerable usar o bare default → o fixed **adiciona** as flags; se a versão exigir opt-in → o diff **inverte** as flags. Documentar o caminho efetivamente usado.)
3. **`defusedxml` — NOTA "mencionável, não aplicada" (NOMEADA).** Existe e é a defesa histórica pra stdlib, **mas** o suporte a `lxml` nele está **deprecado** (mandam configurar o `lxml` direto). Pra uma app `lxml`, a defesa atual é **endurecer o parser** (o fix deste átomo). **Descrito, não aplicado** — como o IMDSv2 do 17.
4. **XXE aqui é LEITURA DE ARQUIVO, NÃO SSRF.** O `no_network=True` (default) mantém a resolução em `file://` (arquivo local); `http://` **não** sai pra rede. Por isso o átomo é **arbitrary file disclosure** e **não** toca o arco A10 (SSRF). Que XXE possa alcançar rede/OOB é **descrição da classe** — **NÃO nomear/antecipar** a variante cega como "um próximo passo" (foreshadow proibido).

---

## Encenação — ATOR ÚNICO (o pentester)

Um ator — o aluno é o atacante/pentester. O WALKTHROUGH deixa explícito. No Burp (trilha principal):

1. **Baseline (a feature funcionando).** `POST /import` com o **XML de contato benigno** (sem `DOCTYPE`) → a app ecoa o `name` normalmente (ex.: "Imported contact: Ada Lovelace").
2. **Provar o XXE (`/etc/passwd`).** Injetar o `DOCTYPE` com `<!ENTITY x SYSTEM "file:///etc/passwd">` e usar `&x;` no `<name>` → a resposta volta com o **conteúdo do `/etc/passwd`** no campo `name`.
3. **Clímax (`/app/secret.txt`).** Trocar o `file://` pro `file:///app/secret.txt` → a resposta volta com o **segredo (dummy) da própria app**.
4. **Contra o FIXED (`8118`).** Os mesmos payloads → **NÃO vazam** (a entidade não expande; `name` vazio ou parse controlado).

**PROVA-CHAVE (cravar):** no **vulnerable**, o **conteúdo do arquivo aparece na resposta** (o `&x;` expandiu); no **fixed**, a mesma injeção **não expande** → **nada vaza**. A diferença observável é o campo ecoado (conteúdo do arquivo **vs** vazio/erro) — porque é **in-band**.

---

## A trilha — Burp principal + browser secundária (trilha dupla, `CLAUDE.md` §3.3)

O 18 está no **molde HTML de trilha dupla** (como o 01). O Burp é a trilha **principal** — é onde o pentester **planta e manipula** o payload cru (o `DOCTYPE`, a entidade, o encoding, o Repeater), a parte que ensina a profissão; a **prova** é o campo ecoado (o conteúdo do arquivo), que o par Burp entrega direto (in-band, sem precisar de JS no browser → **NÃO** é a exceção-XSS/client-side do §3.3).

- **Trilha principal — Burp (Repeater).** Cada request é um bloco colável. O aluno controla o `POST /import` no Repeater e **lê o arquivo no campo ecoado** da resposta.
- **Trilha secundária — browser (opcional, baixa fricção).** Abrir `/`, colar o XML malicioso no textarea, submeter, ver o conteúdo do arquivo renderizado no `<pre>`. Mesmo papel: primeira experiência sem atrito. **Sem JS.**

---

## Walkthrough — estrutura e beats

Trilha principal **Burp**, secundária **browser**. Payloads/responses são placeholders da execução real capturada na Fase 2. Estrutura de beats (molde do 01, com o alvo de arquivo e o impacto de disclosure explícitos):

> **Abertura — plantar a lição.** *Você tem uma feature que importa um contato de um XML e te mostra o nome importado. XML parece inofensivo — até você lembrar que XML tem DTD, e DTD deixa você declarar uma entidade que aponta pra um arquivo do servidor. Se o parser resolver essa entidade, o conteúdo do arquivo vira o "nome" do contato — e volta na sua tela. Você vai ler o `/etc/passwd`, depois o segredo da própria app.*

1. **Context.** App web "contact importer": `GET /` (form com textarea de XML), `POST /import` (o servidor parseia e **mostra** o nome). Isto é **A05 — XXE** (XML External Entity injection). **Um ator: você, o pentester.** Trilha: Burp (principal) + browser (secundária). Nota de mapeamento OWASP (XXE dobrado em A05 no Top 10 2021; era A4 em 2017).
2. **Spot the bug.** Mostrar `vulnerable/app.py` — o `POST /import`. `request.form["xml"]` flui pro `etree.fromstring(...)` com o parser do `lxml` que **resolve entidade externa** (default perigoso). Pergunta de auditoria: *"o parser resolve entidades que EU declaro no XML — inclusive uma que aponta pra um arquivo?"* → **sim**. Foreshadow do fix: **desabilitar entidade externa/DTD no parser**.
3. **The attack (o núcleo — VALIDAR RODANDO).** Três passos:
   - **3a — baseline:** `POST /import` com o `<contact>` benigno → o `name` volta (feature funciona, in-band).
   - **3b — `/etc/passwd`:** payload com `<!DOCTYPE contact [<!ENTITY x SYSTEM "file:///etc/passwd">]>` e `<name>&x;</name>` → o **conteúdo do `/etc/passwd`** volta no campo `name`.
   - **3c — clímax (`/app/secret.txt`):** trocar pro `file:///app/secret.txt` → o **segredo dummy da app** volta. **Arquivo arbitrário lido via XXE.**
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **NÃO é "processar/aceitar XML é o bug".** Parsear XML é normal; **resolver entidade externa** é o bug. **Prova de isolamento:** submeter o **mesmo `<contact>` benigno** (sem `DOCTYPE`) ao vulnerable **e** ao fixed → os **dois importam "Ada Lovelace" idêntico** (a lógica de importação é a mesma). Só quando se adiciona o `DOCTYPE`+entidade é que o vulnerable vaza e o fixed não. **A diferença é 100% o parser, não a app.**
   - **NÃO é um bug de lógica na app.** Não há erro na rota `/import`; as duas versões parseiam e ecoam. A **única** diferença é **uma config do parser** (resolve entidade **vs** não).
   - **NÃO é SSRF / "alcançar a rede".** Com `no_network=True` (default), a entidade lê um **arquivo local** (`file://`) — **não** faz request de rede. É **leitura de arquivo**, não SSRF.
   - **NÃO é XSS.** O conteúdo do arquivo volta **escapado** (autoescape, `<pre>`) — é texto, não markup. A vuln é o parser ler o arquivo, não como ele é exibido.
   - **NÃO é a stdlib.** Se o mesmo payload fosse parseado com o `xml.etree.ElementTree` da stdlib, a entidade externa **não** expandiria (a nativa não resolve) — o que prova que a vuln é a **resolução de entidade do `lxml`**, não "XML" nem "a app". (Prosa; **não** virar passo executável.)
   - **O que É (prova):** o parser resolve uma entidade **que você declara** apontando pra um arquivo, e **te devolve o conteúdo** no campo ecoado. A **única** correção é **desabilitar entidade externa/DTD no parser** (a fixed).
5. **Impact (honesto — sem overclaim).** **Leitura de arquivo arbitrário do servidor (Arbitrary File Disclosure)** via XXE: o atacante lê arquivos que o processo da app consegue ler (`/etc/passwd`, o `secret.txt` da app, configs, código-fonte, chaves, etc.). Impacto = **disclosure**. **NÃO é RCE por si só.** Mencionar em **uma linha** que XXE tem **outras faces** (a classe pode escalar em cenários específicos) — **descrição da classe, sem nomear átomo/variante futura**.
6. **Why the fix works (porta 8118).** Repetir a cadeia contra o `fixed/`:
   - **3b/3c idênticos:** o mesmo payload → **`name` vazio / parse controlado**, **sem conteúdo de arquivo**.
   - **Prova-chave:** o **vulnerable devolve o arquivo no campo**; o **fixed não expande** e nada vaza. Como é **in-band**, a diferença aparece **na própria resposta**.
   - **A lição do diff:** o fix **desabilita** entidade externa e DTD no parser (`resolve_entities=False, load_dtd=False`), mantendo `no_network=True`. **`lxml` vs stdlib** (nota #1); **o default trai** (nota #2); **`defusedxml` mencionável não aplicada** (nota #3); **XXE aqui é file read, não SSRF** (nota #4).

**Trilha browser (secundária, opcional)** logo após a principal: colar o XML malicioso no textarea, submeter, ver o arquivo no `<pre>`; depois repetir no `8118` e ver que nada vaza. **Sem** seção de exercícios/variações (`CLAUDE.md` §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## Impacto honesto

**Leitura de arquivo arbitrário do servidor (Arbitrary File Disclosure) via XXE.** O atacante lê qualquer arquivo que o processo da app consiga ler — `/etc/passwd`, o `secret.txt` da app, arquivos de config, código-fonte, chaves. Impacto = **disclosure**. **NÃO é RCE** por si só (a classe XXE pode escalar em cenários específicos, mas **este átomo é leitura de arquivo in-band** — sem overclaim). Uma linha reconhecendo que XXE **tem outras faces** é legítima (descrição da classe), **sem** nomear átomo/variante futura.

---

## Contraste com o repo / escopo — e a POLÍTICA DE FORESHADOW

**Categoria NOVA (A05) — abre o eixo XXE; sem irmão A05 publicado.** O contraste é **conceitual**, com átomos publicados (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`sqli-union-basic` (01) e `command-injection-basic` (09)** — cousins mecânicos: XXE também é **injeção num motor** (input não-confiável interpretado por um engine que faz mais do que devia; aqui o motor é o parser XML). **Mas** o 18 é **A05** porque a causa/fix é uma **config perigosa do parser**, não a construção de uma query/comando.
- **`path-traversal-basic` (10)** — **mesmo impacto** (leitura de arquivo arbitrário, `/etc/passwd`), **mecanismo diferente** (path vs entidade XML). *"Mesmo loot, porta diferente."* Ambos publicados — o aluno abre e compara.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante futura** por número, nome **OU** descrição — inclusive **a variante blind/OOB de XXE**, os átomos 19/20, ou "a próxima fase". **PROIBIDO** anunciar a release `v0.4.0` no conteúdo do átomo.
- **Que XXE tenha "outras faces" (cega, OOB, SSRF via XXE, escalada) é descrição LEGÍTIMA DA CLASSE** — como o 04 descreve o que SSRF alcança. **MAS não descrever a variante cega como "um próximo passo/átomo".** Na dúvida, mantém conceitual e manda o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 18 vai até a **leitura de arquivo in-band** (o finding). Variante cega/OOB e escalada de XXE para RCE/SSRF estão **fora de escopo** deste átomo.

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/xxe`** — a página conceitual de XXE (título **"XML external entity (XXE) injection"**, framing "What is XXE injection?"). É a página de introdução da vuln, não a de labs.
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7 — ex. "XML external entity (XXE) injection", exatamente como a PortSwigger nomear a página).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `sqli-union-basic`: *"Read [PortSwigger: XML external entity (XXE) injection](URL) before working through this atom..."*).

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (form com textarea de XML + exibição do campo ecoado — não API-only), **autoescape do Jinja LIGADO** (default). Garantir que a **ÚNICA** superfície é o XXE:

- **Sem XSS:** o campo ecoado (que pode conter o conteúdo do arquivo) é renderizado num `<pre>` **escapado** (`{{ name }}`) — **sem** `|safe`/`Markup`/`render_template_string`.
- **Sem billion-laughs/entity-expansion DoS:** `huge_tree` fica no default (`False`); validar que um payload de expansão **não** derruba o container.
- **`secret.txt` DUMMY** (valor obviamente falso) e **`/etc/shadow` NÃO usado**.
- **`no_network=True`** (default) → `file://` puro, sem SSRF acidental.
- A **única** superfície é o parser resolvendo entidade externa.

---

## HTML — `templates/` (mínimo, molde do 01; `index.html` + `result.html`)

Molde do `sqli-union-basic`: `<!doctype>`, banner de aviso obrigatório, ≤40 linhas, ≤5 linhas de CSS inline, **sem** frameworks, **sem** JS, dica de Burp no rodapé. Templates **idênticos** entre vulnerable e fixed (o diff vive só no `app.py`). Candidatos (a Fase 2 finaliza o texto exato):

**`templates/index.html`** (~20 linhas — molde do `index.html` do 01, com um `<textarea>` pré-preenchido com um contato benigno):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Contact Importer</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}textarea{width:100%;height:9em;font-family:monospace;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Contact Importer</h1>
<p>Paste a contact card (XML) and the server imports it and shows the name.</p>
<form method="post" action="/import">
  <textarea name="xml" autofocus>&lt;contact&gt;
  &lt;name&gt;Ada Lovelace&lt;/name&gt;
  &lt;email&gt;ada@example.com&lt;/email&gt;
&lt;/contact&gt;</textarea>
  <button type="submit">Import</button>
</form>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

**`templates/result.html`** (~16 linhas — nome ecoado num `<pre>` **escapado**):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Imported contact</title>
<style>body{font-family:sans-serif;max-width:960px;margin:2em auto;padding:0 1em;}pre{background:#eee;padding:0.8em;border-radius:4px;overflow:auto;max-height:480px;white-space:pre-wrap;word-break:break-all;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Imported contact</h1>
{% if error %}<p>Could not parse the document.</p><pre>{{ error }}</pre>
{% else %}<p>Imported contact:</p><pre>{{ name }}</pre>{% endif %}
<p><a href="/">&larr; Back</a></p>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- O textarea vem pré-preenchido com o `<contact>` **benigno** (o ataque é **adicionar** o `DOCTYPE`+entidade e trocar o `<name>` por `&x;`).
- `result.html` ecoa `name` (ou a mensagem de erro) num `<pre>` **escapado**. **Não há terceiro template**; o `metadata-mock`/serviço extra **não existe** (single-container).
- Confirmar na Fase 2 que o `error` ecoado **nunca** carrega conteúdo de arquivo (não carrega — o fixed não lê o arquivo).

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` — molde do `sqli-union-basic` (**com** `COPY templates`), **mais UMA linha** que **planta o `/app/secret.txt` dummy** (mantém single-container; sem serviço extra). Só Flask + `lxml` via pip — sem `apt`, sem banco.

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** (candidato — idênticos entre si):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
# Plant a DUMMY app secret so the XXE has an app-owned file to disclose (obviously fake, lab-only).
RUN printf 'lab secret -- FLAG-xxe-9f1c2a-EXAMPLE-not-a-real-secret\n' > /app/secret.txt
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

- O `secret.txt` é plantado **nos dois** (`vulnerable` **e** `fixed`) — a ausência de vazamento no fixed é do **parser**, não do arquivo faltar. Valor **obviamente falso** (`CLAUDE.md` §8). *(Alternativa de Fase 2: um `secret.txt` committado no diretório e `COPY`ado, se preferir o valor visível no repo em vez de no `RUN`. Qualquer um serve; o `RUN printf` mantém tudo num arquivo só.)*
- `/etc/passwd` **já** está na base image (`python:3.11-slim`) — nada a fazer.

**`docker-compose.yml`** (candidato — molde do 01/03, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8018:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8118:5000"
```

**Sem `networks:`, sem serviço extra.** Volta ao molde simples do 01/03.

---

## Bibliotecas

**`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
lxml==5.3.0
```

- **`lxml`:** **fixar a versão exata na Fase 2** (candidato `5.3.0`) **e confirmar o comportamento default de entidade** (o item central da Saída B / checklist #6). O `lxml` distribui **wheels manylinux** — instala no `python:3.11-slim` **sem toolchain de build** (`pip install lxml` pega o wheel prebuilt; mesmo espírito da memória `rsa-atoms-crypto-wheel`). Confirmar o install limpo na Fase 2.
- **`os`** é stdlib (não vai no `requirements`).
- **SEM `defusedxml`** (deprecado pra lxml — ver DIFF nota #3). **SEM** banco, `requests`, ou 2ª dependência.
- **Pin behavior-critical (sim, como os JWT).** Diferente do 04/16/17 (SSRF, agnóstico de versão), aqui o **comportamento default de resolução de entidade do `lxml` É o objeto de estudo** — então a versão do `lxml` é **behavior-critical** (`CLAUDE.md` §8.7, mesma razão do PyJWT no 14). Fixar a versão e não atualizar automaticamente.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A05 — Security Misconfiguration** (`atoms/A05-security-misconfiguration/`, **criar**) | ROADMAP linha 108 lista `xxe-basic` em A05; `CLAUDE.md` §4 fixa o nome de pasta. **Primeiro átomo A05** — a categoria abre aqui (como o 15 abriu A07). XXE dobrado em A05 no Top 10 2021 (era A4 em 2017). |
| Posição na Fase 4 | **Terceiro (o 16 abriu; o 20 fecha)** | ROADMAP: 16/17/**18**/19/20; 01–17 já `[x]`. |
| Eixo | **CATEGORIA NOVA — sai do arco A10 (fechado no 17), abre XXE/A05** | Sem irmão A05; contraste conceitual com 01/09/10 (publicados). |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Volta ao molde do 01/03 depois do multi-container do 16/17. Sem serviço extra/listener/mock. |
| Visibilidade | **IN-BAND** (parseia e MOSTRA o campo) | É como o aluno lê o arquivo. Variante cega/OOB fora de escopo (sem foreshadow). |
| Lição-coração | **Parser resolve entidade externa → `file://` lê arquivo → conteúdo volta no campo ecoado. Fix: desabilitar entidade/DTD.** | O bug é a CONFIG do parser, não a lógica da app. |
| Decisão estrutural (Saída B) | **`lxml`, NÃO `ElementTree`** | A stdlib não resolve entidade externa → não seria vulnerável. Mesmo movimento honesto do 14 (PyJWT) e do 15 (`flask.session`). |
| Default do `lxml` (Saída B, Fase 2 confirma) | **Caminho 1 "o default trai" (preferido) / Caminho 2 "opt-in explícito" (fallback)** | Se o bare default resolve `file://` → vulnerable usa o default, fixed adiciona flags. Senão → vulnerable liga explícito, diff inverte flags. `no_network=True` (default) mantém file-read puro (sem SSRF). |
| Feature — **SINALIZADO** | **Contact importer** (`GET /`, `POST /import`, campo `<name>` ecoado) | Único item não pré-travado. Cabe no textarea; o eco ("Imported contact: name") é feedback natural; mínimo. |
| Resposta do vulnerable | **ECOA o campo** (conteúdo do arquivo volta), escapado num `<pre>` | In-band — é como o aluno lê o arquivo. Escapado → sem XSS. |
| Resposta do fixed | **Campo vazio / parse controlado** (Fase 2 decide a forma exata) | Entidade não expande → nada de arquivo vaza. |
| Fix (único eixo) | **Desabilitar entidade externa e DTD no parser** (`resolve_entities=False, load_dtd=False`, `no_network=True`) | Defesa canônica de XXE em app lxml: desligar a feature perigosa do parser. |
| Diff | **Lógica-diferente MÍNIMA** — a única mudança é a config do parser | Diff no ponto do parse; resto byte-idêntico. |
| `defusedxml` | **NÃO aplicar** (nota "mencionável, não aplicada", nomeada) | Suporte a lxml deprecado; a defesa atual pra app lxml é endurecer o parser. Como o IMDSv2 do 17. |
| Alvo da leitura | **`/etc/passwd` (1º) + `/app/secret.txt` dummy (clímax)** | Clássico world-readable + segredo obviamente falso plantado no Dockerfile (nas duas imagens). `/etc/shadow` NÃO. |
| HTML | **`index.html` (form textarea) + `result.html` (campo escapado)** | Molde do 01, trilha dupla. |
| Bibliotecas | **`Flask==3.0.0` + `lxml==5.3.0`** (fixar exato na Fase 2) | `lxml` é behavior-critical (o default de entidade É o estudo) — como PyJWT no 14. Sem defusedxml, sem banco. |
| Impacto | **Arbitrary File Disclosure.** NÃO RCE. | Honesto; sem overclaim; XXE "tem outras faces" só como descrição de classe. |
| Theory primer | **PortSwigger XXE** (`/web-security/xxe`, confirmar por fetch) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Foreshadow | **ZERO pra frente** | `CLAUDE.md` §5. Não nomear a variante cega/OOB nem 19/20/próxima fase. |
| Portas | **8018 / 8118** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–6 são os centrais; 7–12 são higiene técnica. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /`** serve o form (textarea com o XML de exemplo benigno, banner, dica de Burp). Template renderiza.
2. **`POST /import` (vuln) com o XML benigno** → a app **ecoa o `name` normalmente** ("Imported contact: Ada Lovelace"). Feature funciona (baseline).
3. **O ATAQUE (central — VALIDAR RODANDO):** no vulnerable, `POST /import` com `<!DOCTYPE contact [<!ENTITY x SYSTEM "file:///etc/passwd">]>` + `<name>&x;</name>` → a resposta **contém o conteúdo do `/etc/passwd`** no campo `name`. **Capturar o payload e a resposta reais.** **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** responses.
4. **CLÍMAX:** mesmo payload com `file:///app/secret.txt` → a resposta **contém o segredo dummy**. Capturar.
5. **FIXED (`8118`):** os mesmos payloads → **NÃO vazam** (entidade não expande; `name` vazio **ou** parse controlado). **Capturar a diferença** (campo vazio/erro vs conteúdo).
6. **Confirmar o DEFAULT do `lxml` da versão fixada (o coração da Saída B):** o bare default resolve `file://` sem config explícita? → decide **Caminho 1** (default trai; vulnerable usa default, fixed adiciona flags) vs **Caminho 2** (opt-in; vulnerable liga explícito, diff inverte). Confirmar `no_network=True` (sem SSRF acidental). Documentar o caminho efetivamente usado no DIFF (nota #2).
7. **`lxml`, não `ElementTree`** (a nativa não seria vulnerável — cravar no DIFF nota #1).
8. **Uma vuln só:** autoescape ligado (conteúdo do arquivo **escapado** no `<pre>`); **SEM billion-laughs/entity-expansion DoS** (`huge_tree` no default `False`; validar que um payload de expansão **não** derruba o container; se o lxml expandir demais, limitar); `secret.txt` dummy; sem XSS; sem 2ª falha.
9. **Primer PortSwigger (XXE)** confirmado **por fetch** (`/web-security/xxe`). Se em dúvida, perguntar ao mantenedor. **Não inventar.**
10. **Higiene de rede:** portas **8018/8118** bind **só** `127.0.0.1`. **Single-container** (sem serviço extra, sem `networks:`). `./atom up xxe-basic` sobe sem erro. **Validar via `docker exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`).
11. **`app.py` vulnerable × fixed:** confirmar por `diff` que a **única** mudança é a **config do parser** (o `XMLParser(...)`/`fromstring(...)`), e que o resto (`GET /`, imports, `render_template("result.html", ...)`, `except`, rodapé) e os **templates** são **byte-idênticos**. Diff **lógica-diferente mínima**.
12. **Arquivos-alvo:** `/app/secret.txt` plantado no `Dockerfile` (nas **duas** imagens) com valor **obviamente falso**; `/etc/passwd` presente (base image). `Flask==3.0.0`+`lxml==<pin>` instalam limpo (wheel) no `python:3.11-slim`.

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** reproduzir o ataque rodando (itens 2–5); confirmar o default do `lxml` (item 6) e escolher Caminho 1/2; confirmar a URL do primer por fetch (item 9); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo **ABRE a categoria A05/XXE** — não tem irmão pra espelhar. Cada beat deve poder ser lido com o **`sqli-union-basic` (01)** aberto ao lado (o molde single-container / HTML / trilha dupla pra onde o 18 volta). **Abrir e fechar** na lição-coração: *não há bug de lógica na app; o bug é o parser resolver entidade externa — uma config perigosa (por isso A05).*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`sqli-union-basic` (01) INTEIRO** (molde canônico), **`idor-numeric-id` (03)** (compose/Dockerfile single-container), o **`17 ssrf-cloud-metadata`** só pela **voz** de docs (NÃO pela infra — o 18 é single-container), e os specs do **14/15** pelo **padrão da Saída B**. Ler **não é pra copiar** — é pra **conformar** à convenção.
- **A SAÍDA B é o coração honesto do átomo (duas rugas):** (1) **`lxml`, não `ElementTree`** — a stdlib não resolve entidade externa (não seria vulnerável); explicar **por quê** no DIFF (mesmo movimento do 14/15). (2) **O default do `lxml`** — testar o bare default primeiro (item 6); liderar com "o default trai" (Caminho 1) se reproduzir; senão, opt-in explícito (Caminho 2). Cravar no DIFF (nota #2).
- **A prova é o arquivo (não) voltar no campo ecoado (risco #3/#4/#5).** Capturar a cadeia real: vulnerable → `/etc/passwd` no campo → `secret.txt` no campo; fixed → vazio/erro, sem arquivo. **Se não bater rodando, PARAR e avisar — NÃO inventar** responses.
- **Uma vuln só:** eco **escapado** (autoescape, `<pre>`, sem `|safe`); **sem billion-laughs** (`huge_tree` no default; validar); `no_network=True` (sem SSRF); `secret.txt` **dummy**; `/etc/shadow` **não** usado; sem XSS. A **única** superfície é o parser resolvendo entidade externa.
- **Ator único:** rotular no WALKTHROUGH **baseline** → **`/etc/passwd`** → **clímax (`secret.txt`)** → **fixed**. O aluno é o pentester sozinho.
- **Impacto honesto:** **Arbitrary File Disclosure.** **NÃO** RCE. XXE "tem outras faces" só como **descrição da classe**, **sem** nomear átomo/variante futura.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** o passo de contraste isola que **o bug é a resolução de entidade do parser**, não "processar XML", não um bug de lógica, não SSRF, não XSS, não a stdlib. **A prova de isolamento:** o **mesmo `<contact>` benigno** importa idêntico no vulnerable e no fixed; só o `DOCTYPE`+entidade separa os dois.
- **Política de referência cross-átomo:** OK citar **01, 09, 10** (publicados; injeção-num-motor e mesmo-loot-porta-diferente). **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome **ou** descrição — **inclusive a variante blind/OOB de XXE**; **NÃO** anunciar "próxima fase" nem a release `v0.4.0`.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico em EN e PT (`xxe-basic — XML External Entity (XXE) injection`, texto exato confirmável na Fase 2). Termos técnicos (XXE, XML, DTD, entity, external entity, SYSTEM, `file://`, in-band, payload, parser, arbitrary file disclosure, sink, source, autoescape) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (XXE), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 18: `xxe-basic` — XML External Entity (XXE) injection: arbitrary file disclosure via an lxml parser that resolves external entities (A05 Security Misconfiguration). `` (padrão das linhas dos átomos anteriores; as linhas do 16/17 já estão em `[Unreleased]`).
- **ROADMAP.md:** marcar o átomo 18 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline → `/etc/passwd` → `secret.txt` → fixed (sem vazamento). Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8018` (vulnerable), `127.0.0.1:8118` (fixed). Bind **só** em `127.0.0.1`. Single-container.
- Se houver dúvida sobre a URL do primer, a forma exata do H1, o comportamento default do `lxml` (Caminho 1 vs 2), o flavor/endpoint, ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato único, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos que mexam com XML):

- **`xxe-atoms-use-lxml-not-elementtree`** — *"Átomos de XXE usam `lxml`, NÃO o `xml.etree.ElementTree` da stdlib — a nativa não resolve entidades externas (não seria vulnerável). Mesma armadilha estrutural do PyJWT no 14 e do `flask.session` no 15 ('a ferramenta padrão mitiga; o bug vive em quem usa a que não mitiga'). O default do `lxml` resolve entidade LOCAL `file://` mas por default NÃO acessa rede (`no_network=True`) — então é leitura de arquivo pura, não SSRF; e `huge_tree=False` (default) capa billion-laughs. Fix = `XMLParser(resolve_entities=False, load_dtd=False, no_network=True)`. NÃO usar `defusedxml` (suporte a lxml deprecado). Confirmar o comportamento default da versão pinada rodando (behavior-critical, como PyJWT)."* — tipo `project`/`reference`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava), **e** o comportamento default exato é **version-dependent** (só confirmado na Fase 2). Proponho **não** gravar por ora — ou, se quiser gravar, fazê-lo **após a Fase 2 confirmar** o default, pra a memória nascer verdadeira. Sua decisão.
