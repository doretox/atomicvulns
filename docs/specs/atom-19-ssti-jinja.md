# Spec — Átomo 19: `ssti-jinja`

> Documento de especificação para o Claude Code implementar o décimo-nono átomo do projeto `atomicvulns` (Fase 4 — "Server-side Avançado", milestone `v0.4.0`). Este átomo é o **QUARTO átomo da Fase 4** (4º dos cinco — `16 ssrf-blind-oob`, `17 ssrf-cloud-metadata`, `18 xxe-basic`, **`19 ssti-jinja`**, `20`; confirmado no `ROADMAP.md`) e é o **SEGUNDO átomo A03 (Injection)** a ganhar uma variante nova nesta fase — mas **NÃO abre categoria**: a pasta `atoms/A03-injection/` **JÁ EXISTE** (mora lá `sqli-union-basic`, `xss-reflected`, `xss-stored`, `sqli-blind-boolean`, `sqli-blind-time`, `command-injection-basic`). O 19 entra **ao lado**, em `atoms/A03-injection/ssti-jinja/`. **NÃO fecha a Fase 4** (o **20** fecha).
>
> **É SINGLE-CONTAINER, molde do `01 sqli-union-basic`** — só `vulnerable` + `fixed`, sem serviço extra, sem listener, sem rede especial. Depois do multi-container do 16/17 e do single-container do 18, o 19 segue single-container.
>
> **A lição em uma linha:** quando input do usuário é **COSTURADO no texto de um template** (em vez de passado como **dado**), o motor de template (**Jinja2**, o engine que o Flask usa pra renderizar HTML) trata esse input como **INSTRUÇÃO**, não como valor — e **avalia** expressões que o atacante injeta. `{{7*7}}` volta `49`; a partir daí o atacante alcança objetos internos da app — a **config do Flask**, com a **`SECRET_KEY`**. O fix é passar o input como **DADO**, nunca costurá-lo no template.
>
> **NÃO há "Saída B" aqui (e isto é uma diferença honesta em relação ao 14/15/18).** Nos átomos 14 (PyJWT recusa a key confusion ingênua), 15 (`flask.session` resiste à fixation) e 18 (a stdlib `ElementTree` não resolve entidade externa), a ferramenta padrão **já mitigava** o bug ingênuo, então o átomo tinha que modelar o componente onde a vuln realmente vive. **Aqui não existe essa ruga:** `render_template_string` é a ferramenta padrão do próprio Flask, e ela é **diretamente** mal-usável — basta o dev **costurar** o input no corpo do template. O átomo é **injeção direta**, como o `01 sqli-union-basic` (concatenação no motor), **sem** ferramenta-que-resiste. **NÃO inventar uma Saída B.**
>
> Leia junto com o `CLAUDE.md` **atual** (§3.3 — **trilha Burp-only**, SSTI é server-side, o browser **não é a prova**; §5 — **abertura seca**, passo "o que a vuln NÃO é" obrigatório, definir termo técnico na 1ª ocorrência, situar em A03 **sem arqueologia de edições**, política de referência/foreshadow; §7 — idioma; §8 — segurança, **bind `127.0.0.1`** e §8.3/§8.4 **NENHUM segredo real**; e "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), o `ROADMAP.md`, e — como **referência viva e primária** — o **`sqli-union-basic` (01) INTEIRO** (molde canônico de HTML/Jinja2 mínimo, single-container, estrutura de WALKTHROUGH/DIFF) e o **`xxe-basic` (18) publicado** (o átomo mais recente e o **primeiro sob as convenções novas** — abertura seca, Burp-only, termo definido; usar como molde de **VOZ/estrutura** atual). Os outros A03 (`command-injection-basic` 09, `xss-reflected` 02) servem **só** pra ancorar o eixo Injection e o contraste conceitual — **NÃO** pra copiar estilo antigo.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição na Fase 4: 19 é o 4º átomo e NÃO abre categoria (confirmado; sem discrepância)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A Fase 4 ("Server-side Avançado", `v0.4.0`) tem **cinco** átomos — `16 ssrf-blind-oob` (`[x]`), `17 ssrf-cloud-metadata` (`[x]`), `18 xxe-basic` (`[x]`), **`19 ssti-jinja`** (`[ ]`, ESTE), `20 deserialization-pickle` (`[ ]`). O 16 abriu a fase; o 18 foi o 3º; o **19 é o quarto** e **NÃO fecha a fase** (o **20** fecha). Os átomos 01–18 já estão `[x]` em `main`.
>
> **Categoria A03 já existe — o átomo entra ao lado, não cria pasta.** O `ROADMAP.md` (linha 111) lista **`19. ssti-jinja — A03 Injection`** com a justificativa *"Template injection em Jinja2 — perfeito porque o repo inteiro usa Jinja, o contexto é familiar."* A pasta `atoms/A03-injection/` **já existe** e tem seis átomos publicados. O 19 mora em `atoms/A03-injection/ssti-jinja/`, **espelhando** o padrão de nomenclatura das pastas existentes (`A0N-<categoria-em-kebab>`).
>
> **Rótulo A03 sem arqueologia (`CLAUDE.md` §5, regra atual).** SSTI é **A03 — Injection** no OWASP Top 10 2021 (a edição que o projeto segue). Diferente do 18 (onde XXE foi *dobrado* em A05 e uma nota de mapeamento era didática), **SSTI não tem ruga de mapeamento entre edições** — sempre foi da família injection. **NÃO** relatar "em que número caía em 2017" nem histórico de edições. Basta situar: *isto é A03 — Injection.*

## Nota de planning 2 — versionamento/release fica FORA desta spec

> O 19 **não fecha** a Fase 4 (o 20 fecha), então **não dispara** release. Versionamento/CHANGELOG/tag/anúncio é **trabalho de release do mantenedor**, não de átomo — não entra nesta spec nem no conteúdo do átomo (`CLAUDE.md` §10.4). A única pegada de changelog é uma **linha em `[Unreleased] / Added`** na Fase 2 (ver "Notas específicas pro Claude Code"). O átomo se descreve como "átomo 19, SSTI em Jinja2, o segundo A03 a ganhar variante nesta fase", **sem** anunciar release nem foreshadowar a fase/os átomos seguintes.

## Nota de planning 3 — este é o PRIMEIRO átomo escrito inteiramente sob as convenções NOVAS (crítico)

> O `CLAUDE.md` foi atualizado recentemente e o 19 é o **primeiro átomo gerado do zero sob as regras atuais**. A **limpeza retroativa dos átomos antigos não aconteceu** — então, ao ler irmãos como molde, o Claude Code deve seguir o **`CLAUDE.md` ATUAL**, não o exemplo dos átomos onde eles divergirem. Divergências concretas a NÃO copiar:
>
> - **Trilha Burp-only (`CLAUDE.md` §3.3).** A trilha é **só Burp Suite** (+ `curl` como equivalente quando útil). **NÃO existe mais "trilha browser secundária".** SSTI é **server-side** — a prova é a **resposta HTTP no Burp**, não o browser. **NÃO criar seção de exploração via browser.** *(Cuidado: vários READMEs publicados — inclusive o do próprio 18 e o do `command-injection-basic` — ainda dizem no "What to read next" `via Burp Suite (primary) and browser (secondary)`. Esse texto é resíduo do estilo antigo; o WALKTHROUGH publicado do 18 já é Burp-only. No 19, o "What to read next" deve dizer só Burp — sem `and browser (secondary)`.)*
> - **Abertura seca (`CLAUDE.md` §5).** O WALKTHROUGH abre **direto na mecânica** — a primeira frase situa a feature e a falha. **NADA** de encenação ("você é o pentester, trabalhando sozinho" e afins). Se um átomo antigo abrir com encenação, **NÃO** copiar.
> - **Definir termo técnico na 1ª ocorrência (`CLAUDE.md` §5).** SSTI (Server-Side Template Injection), Jinja2, `render_template_string`, template engine, `SECRET_KEY`, sink/source — dar a expansão/definição na estreia. O átomo é pra quem **não** conhece a vuln.
> - **A03 sem arqueologia** (Nota de planning 1).

---

## Identidade

- **ID:** `ssti-jinja`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A03 — Injection**. Pasta `atoms/A03-injection/` (**já existe**). Confirmado contra o `ROADMAP.md` ("A03 Injection") e o `CLAUDE.md` §4. **Não é o primeiro A03** — é o sétimo átomo da categoria. Em prosa (README/DIFF) usar o nome da classe — **"Server-Side Template Injection (SSTI)"** — e situá-la em A03 **sem arqueologia de edições**.
- **Pasta:** `atoms/A03-injection/ssti-jinja/`
- **Número sequencial:** 19
- **Porta vulnerable:** `127.0.0.1:8019`
- **Porta fixed:** `127.0.0.1:8119`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos single-container 01/18.
- **Topologia:** **SINGLE-CONTAINER** — só `vulnerable` + `fixed`. **SEM** serviço extra, listener, mock, ou rede especial. Molde do 01/18.
- **Fase / milestone:** Fase 4, `v0.4.0`. **Quarto átomo da Fase 4; NÃO fecha a fase** (o 20 fecha). Versionamento/release **fora desta spec** (Nota de planning 2).
- **Branch de trabalho:** `atom/ssti-jinja`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de SSTI** na PortSwigger Web Security Academy — **framing "what is X?"**, **NÃO** a listagem de labs. Candidato: **`https://portswigger.net/web-security/server-side-template-injection`** (título esperado da página: **"Server-side template injection"**). **NÃO inventar URL — confirmar por fetch na Fase 2**; se não confirmar, perguntar ao mantenedor. Ver "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7):** candidato **`# ssti-jinja — Server-Side Template Injection (Jinja2)`** — `id` + nome canônico da vuln em inglês, com o qualificador do engine (`Jinja2`) que ancora a especificidade deste átomo (o vetor `{{config}}`→`SECRET_KEY` é Flask/Jinja). *(Alternativa, se preferir o padrão-acrônimo do 18 "XML External Entity (XXE) injection": `# ssti-jinja — Server-side template injection (SSTI)`, casando com a grafia exata da PortSwigger.)* Texto exato/qualificador **confirmável na Fase 2**; **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**Server-Side Template Injection (SSTI) em Jinja2 — avaliação de expressão in-band, escalando pra disclosure da `SECRET_KEY`.** Uma app web com uma feature de **saudação personalizada**: recebe um `name` e ecoa "Hello, `<name>`!". O código **costura o `name` no texto do template** que renderiza a saudação. Como o Jinja2 (o motor de template do Flask) **compila e avalia** o texto que recebe, um `name` que contém uma expressão `{{ ... }}` é **avaliado pelo motor**, não exibido como valor: `{{7*7}}` volta `49`, e `{{config}}` faz o motor **imprimir o objeto de config do Flask** — que contém a **`SECRET_KEY`**. É **injeção num motor de template**.

### A lição-coração

> **"Quando input do usuário é COSTURADO no texto de um template (em vez de passado como DADO), o motor de template (Jinja2) trata esse input como INSTRUÇÃO, não como valor — e avalia expressões que o atacante injeta. `{{7*7}}` volta `49`; a partir daí, o atacante alcança objetos internos da app (a config do Flask, com a `SECRET_KEY`). O fix é passar o input como DADO, nunca costurá-lo no template."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** Em Flask, o Jinja2 renderiza templates. O jeito **seguro** passa o dado do usuário como **VARIÁVEL** — `render_template("t.html", name=name)` ou `render_template_string("Hello {{ name }}", name=name)`: o `{{ name }}` é um **placeholder** que o Jinja preenche com o **valor** de `name`, escapando-o e **NÃO** o re-avaliando. A vuln nasce quando o programador **COSTURA** o input no **CORPO** do template — `render_template_string(f"Hello {name}")` ou `"Hello " + name` — aí o input **vira parte do template**, e um `{{ ... }}` injetado é **AVALIADO** pelo motor. A distinção é a app inteira:

```python
render_template_string(f"<h1>Hello, {name}!</h1>")          # name COSTURADO no source -> SSTI
render_template_string("<h1>Hello, {{ name }}!</h1>", name=name)   # name como DADO -> seguro
```

### Sub-lição (cravar)

A diferença entre `vulnerable` e `fixed` **NÃO é "usar Jinja2"** (todo Flask usa) **nem "usar `render_template_string`"** (o `fixed` usa a MESMA função, com segurança). É **input-no-template (costurado) vs input-como-dado (variável)**. **Bug pontual: onde o input entra.** Esta é a sub-lição que o passo "o que a vuln NÃO é" (§5) tem que blindar: o aluno não pode sair achando que "renderizar template é o bug" nem que "`render_template_string` é a função perigosa". O motor é o mesmo, a função é a mesma; muda **só** se o input é costurado no source ou passado como dado.

### Contraste conceitual com o repo (A03; irmãos publicados, citar à vontade)

- **SSTI é INJEÇÃO — mesma forma do `sqli-union-basic` (01) e do `command-injection-basic` (09).** Há **input não-confiável interpretado por um MOTOR** que **faz mais do que devia**. A **frase-âncora do eixo Injection**: *injeção é sempre input caindo num motor que o interpreta com poder demais; muda só o motor.* No 01 o motor é o **SQL engine** (concatenação numa query); no 09 é o **shell** (`/bin/sh` via `subprocess.run(shell=True)`); no 19 é o **motor de template** (Jinja2 avaliando expressões costuradas). **Mesma família mecânica, mesmo A03.**
- **Diferença de impacto pro `command-injection-basic` (09):** o 09 injeta no **shell** e chega a **RCE (Remote Code Execution)** direto; o 19 injeta no **template** e **PARA no vazamento de config/`SECRET_KEY`** (degrau 2 — ver "Escopo / degraus"). Motores diferentes, **tetos de impacto diferentes neste átomo**. Contraste didático forte — ambos publicados, o aluno abre e compara.

Referências a 01 e 09 (e, pra o beat "não é XSS", ao `xss-reflected` 02, publicado) são **bem-vindas** (`CLAUDE.md` §5). **Foreshadow pra frente é PROIBIDO** (ver "Contraste / escopo / FORESHADOW").

### Por que A03 (Injection)

A causa-raiz é **input não-confiável interpretado como código por um motor** (o template engine) — a definição de injection. Diferente do 18 (que foi pra A05 porque a causa era uma **config perigosa** do parser), aqui **não há config**: o dev **construiu** o template com input dentro, exatamente como o `01` construiu a query SQL com input dentro. É injeção pura → **A03**.

---

## Uma vuln só — o foco é a AVALIAÇÃO; HTML reflection (XSS) é efeito colateral da MESMA raiz, notado e NÃO construído; `SECRET_KEY` é DUMMY

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o **input costurado no template** (SSTI). Garantias e sutilezas (todas validar na Fase 2):

- **A sutileza central: costurar input no template TAMBÉM reflete HTML cru — mas o átomo NÃO persegue isso.** Como o `name` vira parte do source do template, um `name` com HTML (`<b>oi</b>`) sai **cru** no output (texto estático de template **não** é autoescapado — só o **output** de `{{ ... }}` é). Ou seja: em SSTI-por-costura, **reflected XSS vem junto** — é inerente à mesma raiz (input no source). Isso é **honesto e real** (em SSTI do mundo real, XSS costuma vir de brinde). **MAS a lição deste átomo é a AVALIAÇÃO** (o motor computar `7*7`→`49`, **ler `config`**) — que HTML cru **não** faz. **Garantir:** o WALKTHROUGH foca em `{{7*7}}` e `{{config}}`; o passo "o que a vuln NÃO é" **nota em uma frase** que refletir HTML é **outra classe (reflected XSS)** — **sem construir payload de XSS**, sem empilhar uma segunda lição. Não viola "um átomo = uma vuln": é **uma raiz** (input costurado no source) com a lição focada em SSTI; o XSS é reconhecido como efeito colateral da mesma raiz, não ensinado.
- **O `fixed` fecha os DOIS (SSTI e o XSS colateral) — bônus honesto, mas o framing continua SSTI.** Passar o `name` como dado (`{{ name }}`, `name=name`) com autoescape ligado (default do `render_template_string`) **não avalia** o input (mata o SSTI) **e** escapa o HTML (mata o reflected XSS). O DIFF **deve** notar: *o fix fecha ambos porque ambos têm a mesma raiz — input costurado; mas o que este átomo ensina é a avaliação (SSTI).*
- **`SECRET_KEY` é DUMMY** (valor **obviamente falso**, `CLAUDE.md` §8.3/§8.4). É a chave que o Flask usa pra **assinar cookies de sessão**; vazá-la deixa o atacante **forjar sessões** (o vetor é real). O valor é de brinquedo (candidato `dev-secret-CHANGEME-not-a-real-secret`), **NÃO** um segredo real. Ver "O segredo: SECRET_KEY".
- **Sem RCE (degrau 3).** O átomo **para no degrau 2** (disclosure da config/`SECRET_KEY`). A cadeia de subclasses do Python que escala SSTI pra execução de comando **NÃO** é construída. **NO MÁXIMO uma menção conceitual de UMA LINHA** no WALKTHROUGH (descrição da classe). Ver "Escopo / degraus".
- **Sem banco, sem segunda superfície:** nenhum SQLite/`requests`/lib extra; nenhum PII real. A **única** superfície é o `name` costurado no template.

---

## Escopo / degraus de impacto (TRAVADO — para no degrau 2)

SSTI em Jinja2 tem três degraus. Este átomo vai **ATÉ o degrau 2 e PARA**:

- **Degrau 1 (confirmação):** `{{7*7}}` → `49`. Prova que a expressão é **avaliada** (não exibida). É o "hello world" do SSTI — o teste canônico que confirma que o input caiu num motor de template.
- **Degrau 2 (CLÍMAX deste átomo):** `{{config}}` → **dump do objeto de config do Flask**, contendo a **`SECRET_KEY`**. Impacto = **disclosure de segredo da app**. Também alcançável: `{{ config.items() }}`, `{{ config['SECRET_KEY'] }}`, `{{ config.SECRET_KEY }}`.
- **Degrau 3 (RCE via cadeia de subclasses do Python) — FORA DE ESCOPO.** RCE é **outra** vulnerabilidade (o `command-injection-basic` 09, publicado, já ensina RCE por outro caminho). Incluí-la quebraria "um átomo = uma vuln". **NÃO construir a cadeia de subclasses.** No máximo **UMA MENÇÃO CONCEITUAL de UMA LINHA** no WALKTHROUGH ("a partir desta mesma injeção, a classe pode escalar até execução de comando via a hierarquia de objetos do Python") — **SEM payload, SEM construir, SEM nomear átomo futuro**. É **descrição da classe**, não foreshadow.

---

## In-band

O 19 é **IN-BAND**: a app **ecoa o resultado da renderização** de volta na resposta — é assim que o aluno **LÊ** o `49` e depois a config/`SECRET_KEY`. **VULNERABLE:** avalia a expressão costurada e devolve o resultado. **FIXED:** trata o input como dado (escapa, não avalia) → `{{7*7}}` volta **literal** `{{7*7}}` (os caracteres `{`, `}`, `*`, `7` não são HTML-especiais, então o autoescape os deixa como texto), sem vazar nada. Diferença observável **na própria resposta** — sem canal lateral, sem OOB.

---

## Feature e endpoints — app web in-band (TEM HTML, molde do 01; SINGLE-CONTAINER) — **DECISÃO SINALIZADA**

> **Este é o ÚNICO item que o prompt me pediu pra DECIDIR e SINALIZAR** (query vs path, e o texto da saudação). Tudo o mais está travado. Abaixo, a escolha com justificativa; **NÃO gero código** — a Fase 2 gera.

### O flavor escolhido: **saudação personalizada (personalized greeting)** via **query string**

Uma app web mínima que **personaliza uma saudação com um nome**, ecoando "Hello, `<name>`!". É o **caso canônico de SSTI** e pedagogicamente forte: a falha se esconde numa **funcionalidade banal** ("personalizar uma saudação"), o que torna o `{{7*7}}`→`49` mais chocante. O `name` chega por **query string** (não path).

**Endpoint — SINALIZADO (query string, endpoint único `GET /`):**

- **`GET /`** — **sem** `?name=`: serve o form (`templates/index.html`), com o banner de aviso, um `<input name="name">` e a dica de Burp. **Com** `?name=<valor>`: **renderiza e ecoa a saudação** — é **onde a expressão costurada é avaliada**.
  - **VULNERABLE:** o `name` é **costurado** no source do template (`render_template_string` com f-string) → SSTI: `{{7*7}}`/`{{config}}` são **avaliados**.
  - **FIXED:** o `name` é passado como **dado** (`render_template_string("...{{ name }}...", name=name)`) → sem avaliação; `{{7*7}}` volta literal.

**Por que query string e endpoint único (e não path / dois endpoints):**

| Decisão | Escolha | Justificativa |
|---|---|---|
| **query vs path** | **query (`?name=`)** | Cabe no molde HTML com `<form method="get">` (como o 01, cujo form GETa `?username=`); no Burp o aluno **edita um único query param** no Repeater — o fluxo mais limpo. Path (`/hello/<name>`) forçaria encodar `{{ }}`/`/` no path e não casa com form. |
| **1 endpoint vs 2** | **1 endpoint `GET /`** (form quando `name` ausente; saudação quando presente) | Recomendação do mantenedor. URL trivial pro Burp (`/?name=…`); uma rota. *(Alternativa de Fase 2, se preferir uma-rota-uma-tarefa como o 01/18: `GET /` só o form + `GET /greet?name=` a saudação. Mesmo princípio; o diff continua na linha da renderização. Eu sigo o endpoint único no resto da spec.)* |
| **texto da saudação** | **"Hello, `<name>`!"** | Curto, universal, o eco é feedback óbvio; baseline `?name=Ada` → "Hello, Ada!". |

*(Se o mantenedor preferir outro flavor/endpoint, a Fase 2 ajusta; sigo o greeting via `GET /?name=` no resto da spec.)*

---

## O código — o coração no `render_template_string`

Imports (vulnerable e fixed **compartilham**; a divergência é **só** como o `name` entra na renderização):

```python
import os
from flask import Flask, request, render_template, render_template_string
```

`render_template("index.html")` serve o form (arquivo em `templates/`, byte-idêntico entre as versões); `render_template_string(...)` renderiza a saudação (o ponto da vuln). Ambas as funções importadas nos dois arquivos.

### `vulnerable/app.py` — `name` COSTURADO no template (SSTI) (candidato — Fase 2 gera o real)

> **Forma-alvo (F1 recomendada):** o `name` entra por **f-string** no source do template. O `<!doctype>`, o banner e o back-link são strings **estáticas** (implicit concat), pra o diff ser cirúrgico — só a linha do `<h1>` é f-string.

```python
app = Flask(__name__)
# Dummy lab secret. Flask uses SECRET_KEY to SIGN session cookies; leaking it lets an attacker
# forge sessions. Obviously fake -- never a real secret (CLAUDE.md security rules).
app.config["SECRET_KEY"] = "dev-secret-CHANGEME-not-a-real-secret"


@app.route("/")
def index():
    name = request.args.get("name")
    if name is None:
        return render_template("index.html")             # no name yet -> show the form
    # VULNERABLE: the name is concatenated INTO the template source, so Jinja2 (Flask's template
    # engine) treats it as template code, not data. An injected {{ ... }} expression is EVALUATED:
    # {{7*7}} -> 49; {{config}} -> Flask's config object, including SECRET_KEY.
    return render_template_string(
        "<!doctype html><title>Greeting</title>"
        "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
        f"<h1>Hello, {name}!</h1>"                        # name is IN the template source -> SSTI
        '<p><a href="/">&larr; Back</a></p>'
    )


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — `name` como DADO (sem avaliação) (candidato — Fase 2 gera o real)

```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-CHANGEME-not-a-real-secret"


@app.route("/")
def index():
    name = request.args.get("name")
    if name is None:
        return render_template("index.html")             # no name yet -> show the form
    # FIXED: the name is passed as DATA via the name= variable, never concatenated into the
    # template source. Jinja2 fills the {{ name }} placeholder with the escaped value and does
    # NOT re-evaluate it, so {{7*7}} comes back literal. Canonical SSTI fix: keep input OUT of
    # the template; pass it as data.
    return render_template_string(
        "<!doctype html><title>Greeting</title>"
        "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
        "<h1>Hello, {{ name }}!</h1>"                     # {{ name }} placeholder filled from data
        '<p><a href="/">&larr; Back</a></p>',
        name=name,                                        # name passed as DATA, never sewn in
    )


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

**Por que F1 (mesma função nos dois lados) e NÃO F2 (`render_template` com arquivo no fixed):**

- **F1** mantém `render_template_string` **nos dois** — a **única** diferença é o argumento: f-string costurada (`f"...{name}..."`) vs placeholder + dado (`"...{{ name }}...", name=name`). Isso **isola cirurgicamente** a lição (input-no-source vs input-como-dado) e **mata a confusão** de que "`render_template_string` é a função perigosa". É a forma mais fiel à sub-lição.
- **F2** (vulnerable com `render_template_string(f-string)`, fixed com `render_template("greet.html", name=name)`) trocaria a **função** e **adicionaria um arquivo** só no fixed (assimetria) — e arriscaria exatamente o mal-entendido que o §5 combate ("o fix é usar arquivo em vez de string"). **Descartada** como forma principal; a Fase 2 pode registrá-la no DIFF como "outra forma correta de passar input como dado", **sem** usá-la no código.
- **Ambas são "input como dado"** — o mesmo princípio. **NÃO** usar blocklist de `{{`/`}}` no input como fix (isso seria filtro furável — outra lição; a correção é **estrutural**, input fora do template).

**Notas de implementação (validar na Fase 2):**

- **`request.args.get("name")` SEM default** (retorna `None` quando ausente) → `/` mostra o form; `/?name=X` mostra a saudação. (Não usar `("name", "world")`, que nunca mostraria o form.)
- **`config` está no contexto do template do Flask por default** — `render_template_string` passa pelo `app.jinja_env` e injeta `config`, `request`, `session`, `g` em **todo** template. Por isso `{{config}}` alcança a `SECRET_KEY` **sem** o dev ter passado `config` explicitamente. **Confirmar rodando na Fase 2.**
- **Autoescape ligado (default do `render_template_string`)** — no `fixed`, `{{ name }}` com `name="{{7*7}}"` sai literal `{{7*7}}` (Jinja **não** re-renderiza o valor); com `name="<b>x</b>"` sai escapado `&lt;b&gt;x&lt;/b&gt;`. **Sem XSS no fixed.**
- **O banner e o back-link são strings estáticas idênticas** nos dois arquivos (só a linha do `<h1>` e o argumento `name=` diferem) → **diff cirúrgico**. Confirmar que o banner (sem `{`/`}`) não interfere no f-string do vulnerable.
- **`SECRET_KEY` setada IDÊNTICA nos dois** (vulnerable e fixed) → a ausência de vazamento no fixed é atribuível à **não-avaliação** (input como dado), **não** à chave estar ausente. Ver "O segredo".

---

## O fix e o tipo de diff

**Fix:** manter o input **FORA do template** (passar como dado: `{{ name }}` + `name=name`). Tipo de diff: **lógica-diferente MÍNIMA** — a mudança é **como o `name` entra na renderização** (costurado no corpo vs variável). Diff no ponto da renderização; o resto (`import`, o `SECRET_KEY`, o branch `if name is None` + `render_template("index.html")`, o `<!doctype>`/banner/back-link estáticos, o `__main__`, os templates) é **byte-idêntico**.

Diff colável (candidato — F1; a Fase 2 gera o real):

```diff
     name = request.args.get("name")
     if name is None:
         return render_template("index.html")
-    # VULNERABLE: the name is concatenated INTO the template source ... {{7*7}} -> 49; {{config}} -> SECRET_KEY.
+    # FIXED: the name is passed as DATA ... Jinja2 fills {{ name }} with the escaped value and does NOT re-evaluate it.
     return render_template_string(
         "<!doctype html><title>Greeting</title>"
         "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
-        f"<h1>Hello, {name}!</h1>"
+        "<h1>Hello, {{ name }}!</h1>"
         '<p><a href="/">&larr; Back</a></p>'
+        , name=name,
     )
```

*(A forma exata do hunk — inclusive a posição do argumento `name=name` — a Fase 2 gera a partir do código real; o essencial é: **f-string costurada → placeholder + dado**, mesma função, resto idêntico.)*

**O CONTRASTE é o diff (obrigatório):** input-no-template (vulnerable) vs input-como-dado (fixed). **A única mudança é como o `name` entra na renderização.**

### Notas obrigatórias no `DIFF.md`

1. **A causa é input-no-template, NÃO "usar Jinja2/templates".** Prova de isolamento: um `name` benigno (`Ada`) renderiza "Hello, Ada!" **IDÊNTICO** no vulnerable e no fixed. Só quando o `name` é `{{7*7}}`/`{{config}}` é que o vulnerable **avalia** e o fixed devolve **literal**. A diferença é 100% **onde o input entra**, não a app.
2. **`render_template_string` com input costurado é o antipadrão; `render_template_string(..., var=var)` (ou `render_template(arquivo, var=var)`) é o certo.** Explicar **"input como código" vs "input como dado"**: costurar coloca o input no **source** (o motor o compila); passar como variável coloca o input como **valor** de um placeholder (o motor o escapa e **não** o re-avalia). **A função é a mesma nos dois lados** — muda só o que ela recebe.
3. **Sandbox NÃO é o fix (nota "mencionável, não aplicada", curta).** O Jinja tem `SandboxedEnvironment`, que tenta **conter** o que uma expressão pode fazer — mas é defesa **mais fraca** e **historicamente furável** (bypasses recorrentes). A correção **real** é **NÃO injetar** (input como dado), não tentar conter a injeção numa sandbox. **Descrito, não aplicado** — mesmo espírito das notas do 17 (IMDSv2) e do 18 (`defusedxml`).
4. **O impacto do degrau 2 é disclosure da `SECRET_KEY`; RCE (degrau 3) é OUTRA vuln, fora deste átomo.** Mencionar em **UMA LINHA conceitual** (a classe SSTI pode escalar pra execução de comando via a hierarquia de objetos do Python) — **sem construir, sem payload, sem nomear átomo futuro**.
5. **Refletir HTML cru é OUTRA classe (reflected XSS), efeito colateral da MESMA raiz.** Costurar input no template também emite HTML cru; o `fixed` fecha isso de brinde (autoescape + input como dado). Mas a lição deste átomo é a **avaliação** (SSTI), não a reflexão de HTML. Notar em uma frase; **não** construir XSS. *(Pode citar o `xss-reflected` (02), publicado, como o átomo que ensina reflected XSS — referência a publicado é permitida.)*

---

## O segredo: `SECRET_KEY` (TRAVADO)

A app define uma **`SECRET_KEY`** no config do Flask (`app.config["SECRET_KEY"] = "..."`), necessária pra sessões — **realista**. É um **DUMMY óbvio de lab** (candidato: `dev-secret-CHANGEME-not-a-real-secret`), **NÃO** um segredo real (`CLAUDE.md` §8.3/§8.4). O `{{config}}` a **vaza**. Pontos didáticos a cravar:

- **A `SECRET_KEY` assina os cookies de sessão do Flask** (via `itsdangerous`). Vazá-la deixa o atacante **forjar/alterar cookies de sessão** — ex.: virar admin, impersonar qualquer usuário. **O valor é dummy, mas o VETOR (vazou a chave → forja sessão) é real.**
- **Setada IDÊNTICA no vulnerable E no fixed.** Assim a **ausência de vazamento no fixed é atribuível à não-avaliação** (input como dado), **não** ao segredo estar ausente. Mesmo raciocínio do "secret plantado nas duas imagens" do 18.

---

## Biblioteca / mecanismo

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask.** O Jinja2 vem junto (dependência do Flask). **Sem banco, sem `requests`, sem segunda dependência.** `os` é stdlib.
- **NÃO é behavior-critical (diferente do 14 PyJWT / 18 lxml).** O comportamento que o átomo usa — Jinja avaliar `{{7*7}}`, e `config` estar no contexto do template — é **estável** há muitas versões do Flask/Jinja. Um **pin normal** basta (candidato `Flask==3.0.0`, casando com 01/18). **Ainda assim, confirmar rodando na Fase 2** que `{{7*7}}`→`49` e `{{config}}`→`SECRET_KEY` na versão fixada. *(Se por acaso a versão mexer no default de autoescape do `render_template_string`, checar; não é esperado.)*

---

## WALKTHROUGH — abertura seca, trilha Burp-only (+ curl equivalente)

**ABERTURA DIRETA na mecânica (`CLAUDE.md` §5).** Sem encenação. A primeira frase situa a feature (saudação personalizada) e a falha (input costurado no template → o motor avalia). Trilha **ÚNICA: Burp** (`curl` como equivalente quando útil — como o `name` vem por GET query string, `curl 'http://127.0.0.1:8019/?name=...'` é um equivalente natural). **NÃO** criar seção de browser.

**Abertura (candidato — plantar a lição, seco):**

> *A app personaliza uma saudação: você manda um `name` e ela responde "Hello, `<name>`!". Por baixo, ela **costura** o seu `name` no texto do template que renderiza a resposta. Como o Jinja2 — o motor de template do Flask — **compila** o texto que recebe, o seu `name` não é tratado como um valor: é tratado como **código de template**. Mande `{{7*7}}` e a resposta volta "Hello, 49!" — o motor avaliou a expressão. A partir daí, você lê a config da própria app, incluindo a `SECRET_KEY` que assina as sessões.*

Beats (molde do 18 publicado — Burp-only, seco):

1. **Context.** App "personalized greeting": `GET /` (form com campo `name`), `GET /?name=…` (o servidor renderiza e **ecoa** a saudação). Isto é **Server-Side Template Injection (SSTI)** — input não-confiável interpretado por um **template engine** (Jinja2) que o avalia — sob **A03 — Injection**. Sem banco, sem segundo serviço: `vulnerable` em `127.0.0.1:8019`, `fixed` em `127.0.0.1:8119`. Trilha: Burp.
2. **Spot the bug.** Mostrar `vulnerable/app.py` — o branch da saudação. `request.args["name"]` flui, **costurado por f-string**, pro `render_template_string(f"...Hello, {name}!...")`. Definir os termos na estreia: **SSTI**, **Jinja2**, **`render_template_string`** ("renderiza uma **string** como template — se a string tem o input dentro, o input vira template"). Pergunta de auditoria: *"o meu `name` é parte do TEXTO que o motor compila — então uma expressão `{{ ... }}` que eu mandar vai ser avaliada?"* → **sim**. Foreshadow do fix: **passar o `name` como dado**, fora do source.
3. **Exploitation via Burp Suite.** Configurar o Proxy, visitar `http://127.0.0.1:8019/`, submeter o form uma vez pra capturar `GET /?name=Ada`, mandar pro **Repeater**. Cada passo mostra o payload **decodificado** (pra ler) — **URL-encodar** o valor de `name` antes de enviar (`{` → `%7B`, `}` → `%7D`; no Repeater, selecionar o valor e **Ctrl+U**). *(Nota de encoding leve: diferente do corpo `x-www-form-urlencoded` do 18, aqui é query string GET; os payloads deste átomo não têm `&`, mas encodar as chaves é a forma robusta.)*
   - **Baseline:** `?name=Ada` → "Hello, Ada!" (feature funciona; in-band). Equivalente: `curl 'http://127.0.0.1:8019/?name=Ada'`.
   - **Degrau 1 — confirmar a injeção:** `?name={{7*7}}` → "Hello, **49**!". O motor **avaliou** a expressão → prova de SSTI. *(Se voltasse "Hello, {{7*7}}!" literal, não haveria SSTI — é exatamente o que o fixed faz.)*
   - **Degrau 2 — vazar o segredo (clímax):** `?name={{config}}` → a resposta ecoa o **dump do objeto de config do Flask**, com a **`SECRET_KEY`** no meio. Ir direto na chave: `?name={{config['SECRET_KEY']}}` (ou `{{config.SECRET_KEY}}`, que evita aspas/colchetes no URL) → **só a chave**. **Capturar req/resposta reais na Fase 2.**
4. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **NÃO é "renderizar template / usar Jinja2 é o bug".** Todo Flask renderiza Jinja. **Prova de isolamento:** `?name=Ada` no vulnerable (8019) **e** no fixed (8119) → os **dois** devolvem "Hello, Ada!" **idêntico**. Só `{{7*7}}`/`{{config}}` separa os dois. A diferença é **onde o input entra**, não "usar template".
   - **NÃO é "`render_template_string` é a função perigosa".** O **fixed usa a MESMA função** — com segurança — passando o `name` como **dado** (`{{ name }}`, `name=name`). O bug é **costurar** o input no source (a f-string), não a chamada.
   - **NÃO é (só) XSS / reflexão de HTML.** Costurar o input também emite HTML cru (um `name` com `<b>` sairia em negrito) — isso é **outra classe (reflected XSS)**. Mas a lição aqui é a **AVALIAÇÃO**: o motor **computa** `7*7` e **lê `config`** — coisa que reflexão de HTML não faz. *(Notar em uma frase; **não** construir XSS. Reflected XSS é o que o `xss-reflected` (02) ensina.)*
   - **NÃO é RCE (neste átomo).** A classe SSTI pode escalar de "avaliar expressão" até **execução de comando** via a hierarquia de objetos do Python; **este átomo para em ler `config`/`SECRET_KEY`** (disclosure). *(Uma linha conceitual, sem payload, sem nomear átomo.)*
   - **O que É (prova):** o motor de template **avalia uma expressão que VOCÊ injeta**, porque o seu input é **parte do source do template**, e te devolve o resultado. A **única** correção é manter o input **FORA do source** — passá-lo como **dado**.
5. **Impact (honesto — sem overclaim).** **Disclosure de segredo da app via SSTI:** o atacante faz o motor avaliar `{{config}}` e **lê a `SECRET_KEY`** (a chave que assina as sessões do Flask). Com ela, **forja cookies de sessão** → impersonação / potencial **account takeover** via sessão forjada. É **disclosure + potencial takeover de sessão**. **NÃO é RCE por si só** neste átomo (a classe escala pra RCE em cenários específicos, mas aqui é leitura de config — **uma linha** reconhecendo a face de RCE, sem construir).
6. **Why the fix works (porta 8119).** Repetir a cadeia contra o `fixed/`:
   - **Degrau 1/2 idênticos:** `?name={{7*7}}` → "Hello, **{{7*7}}**!" **literal**; `?name={{config}}` → **literal** `{{config}}`, **sem** vazar. O motor **não avaliou** — o `name` chegou como **dado**.
   - **Prova-chave:** no vulnerable, `{{7*7}}` vira `49` e `{{config}}` vaza a `SECRET_KEY`; no fixed, os **mesmos** payloads voltam **literais**, sem avaliação. Como é **in-band**, a diferença aparece **na própria resposta**.
   - **A lição do diff:** o fix passa o `name` como **dado** (`{{ name }}` + `name=name`), mantendo-o **fora** do source. **Input-no-template → input-como-dado** (nota #1/#2); **sandbox não é o fix** (nota #3); **RCE é outra vuln** (nota #4); **XSS é a face colateral da mesma raiz** (nota #5).

**Sem** seção de exercícios/variações e **sem** trilha browser (`CLAUDE.md` §5/§3.3 — o walkthrough termina onde a falha foi mostrada e o fix explicado). Payloads/responses são placeholders da execução real capturada na Fase 2.

---

## Impacto honesto

**Disclosure de segredo da app (Sensitive Data / Secret Disclosure) via SSTI, escalando pra sessão forjada.** O atacante faz o motor de template avaliar `{{config}}` e lê a **`SECRET_KEY`** do Flask; de posse dela, **forja/altera cookies de sessão** assinados por essa chave (impersonação, potencial account takeover). Impacto = **disclosure + potencial takeover de sessão**. **NÃO é RCE** por si só neste átomo — a classe SSTI **escala** pra execução de comando via a hierarquia de objetos do Python, mas **este átomo para no degrau 2 (config/`SECRET_KEY`)**. Uma linha reconhecendo que SSTI **tem a face de RCE** é legítima (descrição da classe), **sem** construir nem nomear átomo/variante futura. Sem overclaim.

---

## Contraste com o repo / escopo — e a POLÍTICA DE FORESHADOW

**Sétimo A03 do repo — categoria familiar; contraste com irmãos publicados** (`CLAUDE.md` §5 permite citar publicados à vontade):

- **`sqli-union-basic` (01) e `command-injection-basic` (09)** — cousins mecânicos: SSTI também é **injeção num motor** (input não-confiável interpretado por um engine que faz mais do que devia; aqui o motor é o **template engine** Jinja2). A frase-âncora: *muda só o motor* — SQL (01) / shell (09) / template (19).
- **`command-injection-basic` (09)** — mesmo eixo, **teto de impacto diferente**: o 09 injeta no shell e chega a **RCE** direto; o 19 injeta no template e **para no vazamento de config** (degrau 2). *"Mesma família, motor diferente, teto diferente."*
- **`xss-reflected` (02)** — citável **só** no beat "não é XSS": refletir HTML cru (efeito colateral da costura) é a classe que o 02 ensina; **aqui** a lição é a **avaliação**. Contraste, não empilhamento.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5):**

- **ZERO referência pra frente.** **PROIBIDO** citar/antecipar **qualquer átomo/categoria/variante futura** por número, nome **OU** descrição — inclusive o **átomo 20**, "a próxima fase", ou a release `v0.4.0`.
- **Que SSTI escale pra RCE via a hierarquia de objetos do Python é descrição LEGÍTIMA DA CLASSE** (1 linha, sem construir) — como o 09 descreve o alcance de command injection. **MAS não descrever a escalada como "um próximo passo/átomo".** Na dúvida, mantém conceitual e manda o aluno aprofundar na PortSwigger Academy.

**LIMITE DE ESCOPO:** o 19 vai até o **degrau 2 (disclosure da config/`SECRET_KEY`) in-band** (o finding). Escalada pra RCE (degrau 3) está **fora de escopo** deste átomo.

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a listagem de labs. **Confirmar a URL por fetch na Fase 2 — NÃO inventar** (se não confirmar, perguntar ao mantenedor).

- **Candidato:** **`https://portswigger.net/web-security/server-side-template-injection`** — a página conceitual de SSTI (título esperado **"Server-side template injection"**, framing "What is server-side template injection?"). É a página de introdução da vuln, não a de labs.
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7 — "Server-side template injection", exatamente como a PortSwigger nomear a página).
- Formato do bloco: o padrão do `CLAUDE.md` §5 (o mesmo do `sqli-union-basic`/`xxe-basic`: *"Read [PortSwigger: Server-side template injection](URL) before working through this atom..."*).

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (form com campo `name` + saudação ecoada — não API-only). Garantir que a **ÚNICA** lição é o SSTI (a avaliação):

- **Só UM template de arquivo:** `templates/index.html` (o form). A **saudação NÃO é um arquivo** — é `render_template_string` (é o ponto da vuln). **Não há `result.html`/`greet.html`** (diferente do 01 `profile.html` e do 18 `result.html`, cuja renderização de resultado era um arquivo; aqui o resultado **precisa** ser string-template pra a vuln existir).
- **Autoescape ligado** (default do `render_template_string`) → no **fixed**, `{{ name }}` escapa o valor e não o re-avalia (sem SSTI, sem XSS).
- **A costura no vulnerable também reflete HTML cru (XSS colateral)** — reconhecido como face da **mesma raiz**, **notado e não construído**; a lição é a **avaliação**.
- **`SECRET_KEY` DUMMY** (valor obviamente falso), setada **igual** nos dois.
- **Sem banco, sem segunda superfície.** A **única** superfície é o `name` costurado no template.

---

## HTML — `templates/` (mínimo, molde do 01; só `index.html`)

Molde do `sqli-union-basic`: `<!doctype>`, banner de aviso **obrigatório**, ≤40 linhas, ≤5 linhas de CSS inline, **sem** frameworks, **sem** JS, dica de Burp no rodapé. **`index.html` é byte-idêntico** entre vulnerable e fixed (o diff vive só no `app.py`). A saudação **não** tem template de arquivo (é `render_template_string`). Candidato (a Fase 2 finaliza o texto exato):

**`templates/index.html`** (~18 linhas — molde do `index.html` do 01, `<form method="get">` com um `<input name="name">`):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Greeting</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}input{font-family:monospace;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Personalized Greeting</h1>
<p>Enter a name and the server greets you: <code>Hello, &lt;name&gt;!</code></p>
<form method="get" action="/">
  <input name="name" value="Ada" autofocus>
  <button type="submit">Greet</button>
</form>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- `method="get"` → o `name` vai pra query string (`/?name=…`), que é o que o aluno manipula no Burp.
- **Sem JS, sem framework** (`CLAUDE.md` §3.3). CSS mínimo inline.
- A saudação (`render_template_string`) já inclui o banner + back-link no próprio skeleton (ver "O código") — satisfaz "banner em toda página HTML" (`CLAUDE.md` §8.2) sem um segundo arquivo.

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` — molde do `sqli-union-basic` (**com** `COPY templates`). **Nenhuma** linha extra (diferente do 18, que plantava `secret.txt`): aqui o segredo é a **`SECRET_KEY` no config do Flask** (no `app.py`), não um arquivo. Só Flask via pip — sem `apt`, sem banco.

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

**`docker-compose.yml`** (candidato — molde do 01/18, **single-container**, bind **só** `127.0.0.1`; a Fase 2 gera o real):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8019:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8119:5000"
```

**Sem `networks:`, sem serviço extra.** Molde simples do 01/18.

---

## Bibliotecas

**`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos):**

```
Flask==3.0.0
```

- **Só Flask** (Jinja2 vem junto). **Sem** banco, `requests`, ou 2ª dependência. `os` é stdlib.
- **Pin normal, NÃO behavior-critical** (diferente de PyJWT no 14 / lxml no 18): o comportamento de avaliação do Jinja e `config` no contexto são **estáveis**. Fixar a versão (candidato `Flask==3.0.0`) e **confirmar rodando** na Fase 2 que `{{7*7}}`→`49` e `{{config}}`→`SECRET_KEY`.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A03 — Injection** (`atoms/A03-injection/`, **já existe**) | ROADMAP linha 111 lista `ssti-jinja` em A03; `CLAUDE.md` §4. **Sétimo A03**, entra ao lado. SSTI sempre foi injection — **sem arqueologia de edições**. |
| Posição na Fase 4 | **Quarto (o 16 abriu; o 20 fecha)** | ROADMAP: 16/17/18/**19**/20; 01–18 já `[x]`. |
| Eixo | **A03 familiar — injeção num MOTOR (template engine)** | Contraste com 01 (SQL engine) e 09 (shell); *muda só o motor*. |
| Topologia | **SINGLE-CONTAINER** (só vulnerable + fixed) | Molde do 01/18. Sem serviço extra/listener/mock. |
| Visibilidade | **IN-BAND** (renderiza e ECOA o resultado) | É como o aluno lê o `49` e a `SECRET_KEY`. Sem OOB/canal lateral. |
| "Saída B" (ferramenta-que-resiste) | **NÃO existe aqui** | `render_template_string` é diretamente mal-usável (costurar input). Injeção direta, como o 01. **NÃO inventar Saída B.** |
| Lição-coração | **Input costurado no template → motor avalia `{{...}}` → `{{config}}` vaza `SECRET_KEY`. Fix: input como dado.** | O bug é **onde o input entra**, não "usar Jinja2/`render_template_string`". |
| Degraus (escopo) | **Até o degrau 2 (config/`SECRET_KEY`); degrau 3 (RCE) FORA** | RCE é outra vuln (09 já ensina). Degrau 3 = 1 linha conceitual, sem construir. |
| Feature — **SINALIZADO** | **Personalized greeting**, `GET /?name=…` (query string, endpoint único) | Cabe no molde HTML com form GET; Burp edita um query param. Alternativa (2 endpoints) notada. |
| Código vulnerable | **`render_template_string(f"...{name}...")`** (name costurado) | O `name` vira source do template → avaliação. |
| Código fixed — **F1 recomendada** | **`render_template_string("...{{ name }}...", name=name)`** (name como dado) | Mesma função nos dois lados → isola a lição, mata a confusão "a função é perigosa". F2 (`render_template` arquivo) descartada como forma principal. |
| Fix (único eixo) | **Manter input FORA do template (passar como dado)** | Correção **estrutural**, não filtro de `{{`/`}}` (que seria furável, outra lição). |
| Diff | **Lógica-diferente MÍNIMA** — a única mudança é como o `name` entra na renderização | Diff no ponto do render; resto byte-idêntico. |
| Sandbox (`SandboxedEnvironment`) | **NÃO aplicar** (nota "mencionável, não aplicada") | Defesa mais fraca e furável; a correção real é não injetar. Como IMDSv2 (17) / defusedxml (18). |
| Segredo | **`SECRET_KEY` no config do Flask, DUMMY, setada igual nos dois** | Vetor real (assina sessões); ausência de leak no fixed = não-avaliação, não chave ausente. Valor obviamente falso (`CLAUDE.md` §8). |
| XSS colateral | **Reconhecido (mesma raiz), notado e NÃO construído** | Costurar reflete HTML cru; o átomo ensina a **avaliação**. `xss-reflected` (02) é o átomo de XSS. |
| HTML | **Só `index.html` (form GET)**; saudação via `render_template_string` (sem arquivo) | O resultado **precisa** ser string-template pra a vuln existir. Sem `result.html`. |
| Bibliotecas | **`Flask==3.0.0`** (pin normal, não behavior-critical) | Jinja avalia; `config` no contexto — estável. Sem banco. |
| Impacto | **Secret disclosure (`SECRET_KEY`) → sessão forjada.** NÃO RCE. | Honesto; sem overclaim; RCE só como descrição de classe. |
| Theory primer | **PortSwigger SSTI** (`/web-security/server-side-template-injection`, confirmar por fetch) | Página conceitual "what is X?". Não inventar. Nome em inglês no PT. |
| Trilha | **Burp-only (+ curl)** | `CLAUDE.md` §3.3 atual. SSTI é server-side; o browser não é a prova. Sem trilha browser. |
| Abertura do WALKTHROUGH | **Seca, direto na mecânica** | `CLAUDE.md` §5. Sem encenação. |
| Foreshadow | **ZERO pra frente** | `CLAUDE.md` §5. Não nomear o 20/próxima fase; RCE só como classe. |
| Portas | **8019 / 8119** (bind só `127.0.0.1`) | `CLAUDE.md` §8. Single-container. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–7 são os centrais; 8–12 são higiene técnica. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /`** (sem `?name=`) serve o form (input `name`, banner, dica de Burp). Template renderiza.
2. **`GET /?name=Ada` (vuln)** → a app **ecoa "Hello, Ada!"** (baseline; feature funciona, in-band).
3. **Degrau 1 (VALIDAR RODANDO):** `?name={{7*7}}` → "Hello, **49**!". **Capturar req/resposta reais.** **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** responses.
4. **Degrau 2 (clímax, VALIDAR RODANDO):** `?name={{config}}` → a resposta **ecoa o dump da config com a `SECRET_KEY`**; `?name={{config['SECRET_KEY']}}` (e/ou `{{config.SECRET_KEY}}`) → **a chave direto**. **Capturar.** Confirmar que `config` está no contexto do template por default do Flask.
5. **FIXED (`8119`):** os mesmos payloads → **literais**, sem avaliação (`{{7*7}}` volta "Hello, {{7*7}}!"; `{{config}}` volta literal, sem vazar). **Capturar a diferença.**
6. **Prova de isolamento:** `?name=Ada` → "Hello, Ada!" **IDÊNTICO** no 8019 e no 8119.
7. **Confirmar que o vulnerable COSTURA o `name`** (f-string/concatenação no source do `render_template_string`), **NÃO** como variável — senão não seria vulnerável (a sutileza central). E que o **fixed passa o `name` como dado** (`{{ name }}` + `name=name`), **não** como blocklist de caracteres.
8. **Uma vuln só:** autoescape ligado; `SECRET_KEY` **dummy** setada igual nos dois; **sem banco**; **sem 2ª superfície**. O XSS colateral (costura reflete HTML cru) é **notado, não construído** — confirmar que o WALKTHROUGH **não** empilha um payload de XSS.
9. **Primer PortSwigger (SSTI)** confirmado **por fetch** (`/web-security/server-side-template-injection`). Se em dúvida, perguntar ao mantenedor. **Não inventar.**
10. **Higiene de rede:** portas **8019/8119** bind **só** `127.0.0.1`. **Single-container** (sem serviço extra, sem `networks:`). `./atom up ssti-jinja` sobe sem erro. **Validar via `docker exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`).
11. **`app.py` vulnerable × fixed:** confirmar por `diff` que a **única** mudança é **como o `name` entra na renderização** (f-string costurada vs `{{ name }}` + `name=name`), e que o resto (`import`, `SECRET_KEY`, branch do form, `<!doctype>`/banner/back-link estáticos, `__main__`) e o **`index.html`** são **byte-idênticos**. Diff **lógica-diferente mínima**.
12. **`Flask==3.0.0`** instala limpo no `python:3.11-slim` (wheel). Confirmar `{{7*7}}`→`49` e `{{config}}`→`SECRET_KEY` na versão fixada (não é behavior-critical, mas confirmar).

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** reproduzir o ataque rodando (itens 2–6); confirmar `config` no contexto (item 4); confirmar a URL do primer por fetch (item 9); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **injeção direta** — sem Saída B, sem ferramenta-que-resiste. Cada beat deve poder ser lido com o **`sqli-union-basic` (01)** aberto ao lado (o molde single-container/HTML/estrutura) e o **`xxe-basic` (18) publicado** ao lado (a **voz** atual — abertura seca, Burp-only, termo definido). **Abrir e fechar** na lição-coração: *o bug é o input costurado no template; o motor avalia o que o atacante injeta; o fix é passar o input como dado.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`sqli-union-basic` (01) INTEIRO** (molde canônico) e **`xxe-basic` (18) publicado** (VOZ/estrutura atual — abertura seca, Burp-only). Os outros A03 (`command-injection-basic` 09, `xss-reflected` 02) **só** pra ancorar o eixo Injection e o contraste. **Seguir o `CLAUDE.md` ATUAL** onde os átomos antigos divergirem (Burp-only, abertura seca) — **NÃO** copiar trilha browser nem encenação, mesmo que apareçam em irmãos antigos.
- **NÃO há Saída B (crítico):** `render_template_string` é a ferramenta padrão do Flask e é **diretamente** mal-usável (costurar input no source). **NÃO** inventar uma ruga de "a ferramenta padrão resiste" — ela não resiste; o dev é que costura. Injeção direta, como o 01.
- **A prova é o `{{7*7}}`/`{{config}}` (não) serem avaliados (riscos #3/#4/#5).** Capturar a cadeia real: vulnerable → `49` → dump de `config` com `SECRET_KEY`; fixed → literais, sem vazar. **Se não bater rodando, PARAR e avisar — NÃO inventar** responses.
- **A sutileza que NÃO pode enfraquecer a lição:** o **vulnerable DEVE costurar** o input (f-string/concat no source); o **fixed DEVE ser input-como-dado CORRETO** (`{{ name }}` + `name=name`), **não** uma blocklist de `{{`/`}}` (filtro furável = outra lição; a correção é **estrutural**). **F1 recomendada** (mesma função nos dois lados) — isola a lição.
- **Uma vuln só:** foco na **AVALIAÇÃO** (SSTI). O **XSS colateral** (costura reflete HTML cru) é **notado em uma frase, não construído**. `SECRET_KEY` **dummy**, setada igual nos dois. Sem banco, sem 2ª superfície.
- **Abertura seca + trilha Burp-only:** WALKTHROUGH entra direto na mecânica; **sem** encenação; **sem** seção browser. `curl` como equivalente onde útil (GET query string). Rotular os beats: **baseline** → **degrau 1 (`{{7*7}}`)** → **degrau 2 (`{{config}}`, clímax)** → **o que a vuln NÃO é** → **impacto** → **fixed**.
- **Impacto honesto:** **secret disclosure (`SECRET_KEY`) → sessão forjada.** **NÃO** RCE. RCE só como **descrição da classe** (1 linha), **sem** nomear átomo/variante futura.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** isola que **o bug é o input costurado no template**, não "usar Jinja2/`render_template_string`", não (só) XSS, não RCE. **Prova de isolamento:** `?name=Ada` importa idêntico no vulnerable e no fixed; só `{{7*7}}`/`{{config}}` separa os dois.
- **Definir termo na 1ª ocorrência (`CLAUDE.md` §5):** SSTI (Server-Side Template Injection), Jinja2 (o template engine do Flask), `render_template_string` (renderiza uma string como template), `SECRET_KEY` (a chave que assina cookies de sessão do Flask), sink/source.
- **A03 sem arqueologia:** situar em **A03 — Injection**, **sem** relatar edições antigas (SSTI sempre foi injection; não há ruga de mapeamento como o XXE do 18).
- **Política de referência cross-átomo:** OK citar **01, 09** (injeção-num-motor) e **02** (só no beat "não é XSS"), todos publicados. **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome **ou** descrição — inclusive o **20**; **NÃO** anunciar "próxima fase" nem a release `v0.4.0`.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico em EN e PT (`ssti-jinja — Server-Side Template Injection (Jinja2)`, texto exato confirmável na Fase 2). Termos técnicos (SSTI, Jinja2, template, `render_template_string`, `SECRET_KEY`, payload, sink, source, in-band, autoescape) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (SSTI), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — não inventar.
- **"What to read next" Burp-only:** o README do 19 deve referenciar o WALKTHROUGH **só como Burp Suite** — **sem** `and browser (secondary)` (resíduo do estilo antigo que aparece em READMEs publicados; não copiar).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 19: `ssti-jinja` — Server-Side Template Injection (SSTI) in Jinja2: attacker-controlled input sewn into a template is evaluated by the engine, disclosing the Flask config and SECRET_KEY (A03 Injection). `` (padrão das linhas dos átomos anteriores).
- **ROADMAP.md:** marcar o átomo 19 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline → `{{7*7}}` → `{{config}}` → fixed (literais). Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8019` (vulnerable), `127.0.0.1:8119` (fixed). Bind **só** em `127.0.0.1`. Single-container.
- Se houver dúvida sobre a URL do primer, a forma exata do H1, `config` no contexto, o flavor/endpoint (1 vs 2), ou se o ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato, se você quiser um pointer de recall rápido independente do spec/DIFF** (e útil pra futuros átomos de template/injection):

- **`ssti-jinja-sew-vs-data`** — *"O átomo `ssti-jinja` (19) mostra SSTI em Jinja2/Flask: a raiz é input COSTURADO no source do template (`render_template_string(f\"...{name}...\")`), que o motor avalia — `{{7*7}}`→`49`, `{{config}}`→`SECRET_KEY` (config está no contexto do template do Flask por default). Fix = input como DADO (`render_template_string(\"...{{ name }}...\", name=name)`) — MESMA função nos dois lados (não é 'render_template_string é perigosa'). Sem Saída B (diferente de 14/18): a ferramenta padrão é diretamente mal-usável. Para no degrau 2 (disclosure), NÃO RCE. Costurar input também reflete HTML cru (XSS colateral, mesma raiz, não construído). `SECRET_KEY` dummy. Só Flask==3.0.0, pin normal (não behavior-critical)."* — tipo `project`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, a menos que você queira o pointer de recall. Sua decisão.
