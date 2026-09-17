# Spec — Átomo 10: `path-traversal-basic`

> Documento de especificação para o Claude Code implementar o décimo átomo do projeto `atomicvulns` (Fase 2, **quinto e último átomo da fase** — fecha o "Injection Deep Dive" e faz a ponte de volta pra Access Control). Leia junto com `CLAUDE.md` (Seções 3.3, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — dois átomos de referência:
> 1. **`atoms/A03-injection/command-injection-basic/` (09) — o átomo IRMÃO por MECÂNICA.** Este átomo é deliberadamente amarrado ao 09: ambos terminam lendo `/etc/passwd`, mas por mecanismos OPOSTOS (execução de comando × navegação de filesystem). Reusar a silhueta (GET, output na resposta num `<pre>` escapado, echo do "alvo montado", form em `/` + endpoint de resultado, estrutura do WALKTHROUGH/DIFF, nota de encoding).
> 2. **`atoms/A01-broken-access-control/idor-numeric-id/` (03) — o átomo IRMÃO por CATEGORIA.** É o último A01 publicado antes deste. Reusar o vocabulário de "broken access control" (acesso a recurso que não devia), o passo de contraste "o que a vuln NÃO é", o framing de "o bug é a checagem AUSENTE, não input que virou código".
>
> Esta spec captura apenas as decisões *específicas* deste átomo. Onde o `command-injection-basic` (09) já resolveu a forma (GET + query string, echo do alvo montado num `<pre>` autoescapado, `<pre>` de output escapado, nota de URL encoding, forma do DIFF, esqueleto do WALKTHROUGH/README), a instrução é **reusar a forma do 09**, não reinventar. E onde o `idor-numeric-id` (03) já resolveu o framing de A01, reusar o framing. Este átomo é, deliberadamente, **o gêmeo do 09 que anda pela outra perna da forquilha**: mesmo destino (`/etc/passwd`), caminho oposto (navegação, não execução) — e por isso vive em A01, não A03.

---

## Identidade

- **ID:** `path-traversal-basic`
- **Categoria OWASP:** A01 — Broken Access Control
- **Pasta:** `atoms/A01-broken-access-control/path-traversal-basic/` (mesma convenção de diretório de categoria do `idor-numeric-id`, confirmada por leitura: o 03 vive em `atoms/A01-broken-access-control/idor-numeric-id/`).
- **Número sequencial:** 10
- **Porta vulnerable:** `127.0.0.1:8010`
- **Porta fixed:** `127.0.0.1:8110`
- **Theory primer:** [PortSwigger: Path traversal](https://portswigger.net/web-security/file-path-traversal) — página conceitual de introdução **confirmada por fetch** (H1 literal **"Path traversal"**; abre com "Path traversal is also known as directory traversal. These vulnerabilities enable an attacker to read arbitrary files on the server that is running an application."). É a página "What is X?", **não** a listagem de labs. O texto do link usa **"Path traversal"** — forma verbatim do H1 (a própria página diz que "directory traversal" é sinônimo; o H1 é "Path traversal", então é essa a forma canônica). Nome preservado em inglês também no README PT (convenção v0.1.0). O bloco do README segue o esqueleto verbatim dos átomos 03/09 (só troca o link e o label).

---

## Classe de vulnerabilidade

Path traversal (directory traversal), variante **basic / in-band / conteúdo-visível**. Uma app lê e serve arquivos com base num nome vindo do usuário: ela **concatena esse input a um diretório base** e **abre o arquivo** que o caminho resultante aponta. O atacante injeta sequências `../` (ou um caminho absoluto) para **escapar do diretório pretendido** e ler arquivos arbitrários do sistema. **Nenhum comando é executado** — a app apenas `open()`-a o arquivo que o caminho aponta e devolve o conteúdo na própria resposta HTTP (num `<pre>` escapado), mesma silhueta in-band do `command-injection-basic`.

**Por que esta variante é didaticamente essencial — e a distinção que É o coração deste átomo.** O `command-injection-basic` (09) e este átomo (10) **ambos terminam lendo `/etc/passwd`** — e por isso soam idênticos se mal explicados. NÃO são, e desfazer essa confusão é o objetivo pedagógico central:

> **No command injection, você fez a app RODAR UM COMANDO seu. No path traversal, você fez a app ABRIR UM ARQUIVO seu** — usando exatamente a função que ela já tinha (abrir arquivos), só que apontada pra fora do quintal. Um é **EXECUÇÃO**; o outro é **NAVEGAÇÃO**. Os dois te deram `/etc/passwd`, mas por caminhos opostos: um **executando** `cat`, o outro **SENDO** o próprio `cat`.

A imagem que gruda: no command injection você tem que **invocar** o `cat` (`; cat /etc/passwd`); no path traversal a app **já é** uma máquina de ler-e-mostrar arquivo — você só **redireciona** ela pra fora da pasta. **A app vulnerável ao path traversal *é* o `cat`.**

### Por que A01 (Broken Access Control) e não A03 (Injection) — a moldura muda

Esta é a decisão de categoria, e ela carrega a lição. Nos átomos de injection (01/02/06/07/08/09), a moldura é **"input virou código"** — SQL, HTML/JS, ou shell. Aqui a moldura é outra: **"input te levou a um recurso que não devia"**. Não há sintaxe perigosa óbvia (nada de `;`, `|`, `'`, `<script>`): só **pontos e barras que parecem um nome de arquivo legítimo**. É falha de **ONDE a app deixa você ir**, não de **O QUE ela deixa você executar**. Isso é controle de acesso a recurso — A01.

E é exatamente o que amarra o átomo 10 de volta ao `idor-numeric-id` (03), o outro A01:

| Átomo (A01) | O recurso é acessado por... | O que falta no código |
|---|---|---|
| `idor-numeric-id` (03) | **trocar um ID** (`/notes/1` → `/notes/2`) | check de ownership (a nota é sua?) |
| `path-traversal-basic` (10) | **navegar o filesystem** (`notes.txt` → `../../etc/passwd`) | check de confinamento (o path caiu dentro da pasta?) |

Os dois são **"a app te entregou algo que não era pra você"** — não "você injetou código". No 03 o exploit é dado legítimo (um número). No 10 o exploit *parece* dado legítimo (um nome de arquivo). Ambos são vulns de **lógica/autorização**, e por isso ambos precisam do passo de contraste obrigatório "o que a vuln NÃO é" (CLAUDE.md §5, "Vulns de lógica precisam de um passo 'o que a vuln NÃO é'").

### O ponto que fecha a distinção (cravar no WALKTHROUGH e no DIFF)

- **Command injection é ESTRITAMENTE MAIS PODEROSO.** Executar comando inclui poder ler arquivo (dá pra fazer `cat` via injeção). Path traversal é **só leitura** — você lê qualquer arquivo, mas não executa nada. **Não chamar path traversal de "RCE"** — seria overclaim. O impacto honesto é *arbitrary file read*: source, config, credenciais, chaves — que **frequentemente encadeia** pra mais compromisso (cred vazada → auth; source vazado → mais bugs), mas o path traversal *em si* é read-only.
- **Path traversal é MAIS SUTIL.** Sem caractere "perigoso" pra um WAF grepar; o payload parece um nome de arquivo. Por isso é fácil de deixar passar em code review e em scanner.

### Tabela de contraste (vai no fechamento do WALKTHROUGH; a moldura em prosa vai no DIFF)

| | command injection (09) | path traversal (10) |
|---|---|---|
| A app faz | **EXECUTA** um programa | **ABRE e lê** um arquivo |
| Seu input vira | um **COMANDO** | um **NOME DE CAMINHO** |
| Você ganha o poder de | rodar **QUALQUER COISA** (RCE) | ler **QUALQUER ARQUIVO** (só leitura) |
| `/etc/passwd` sai porque | você mandou **EXECUTAR** `cat /etc/passwd` | você **NAVEGOU** até ele com `../` |
| A feature original era | rodar um `ping` | servir um arquivo |
| Categoria OWASP | A03 — Injection | A01 — Broken Access Control |

---

## Feature simulada

**Visualizador de arquivo (file viewer) — SEM download.**

A app oferece um punhado de arquivos de texto e mostra o **conteúdo** de qualquer um deles na tela. O usuário digita/escolhe um nome de arquivo, a app lê esse arquivo de um diretório de conteúdo (`files/`) e devolve o conteúdo num `<pre>`. Do ponto de vista do usuário legítimo, é um "ver documento"/"ler o readme" trivial — o tipo de feature que existe em qualquer painel de docs, help center ou file browser embutido.

**Decisão: viewer que MOSTRA o conteúdo na resposta, não um download.** Baixar um arquivo a cada teste é chato e tira o foco; o conteúdo volta **in-band** na própria resposta HTTP, na mesma silhueta do `command-injection-basic` (input entra na query, conteúdo/output volta num `<pre>` escapado). Assim o aluno vê `/etc/passwd` direto no Repeater do Burp, sem precisar salvar arquivo nenhum. Sem banco: o "loot" é o **próprio filesystem** (`/etc/passwd`, o source da própria app), não uma tabela — mesmo espírito stateless do 09.

**Tipo de átomo:** `[x] com HTML` / `[ ] API-only` (ver Seção 3.3 do CLAUDE.md).

Dois templates, espelhando o `command-injection-basic`: `index.html` (o form em `GET /`) + `result.html` (o conteúdo em `GET /view`). Burp é a **trilha principal** e o browser a **trilha secundária opcional** — **igual ao 09, e diferente do `xss-stored`**: o conteúdo do arquivo volta **na própria resposta HTTP**, então o aluno vê tudo no Repeater; o browser **não** é obrigatório (não há nada de client-side pra executar — a prova é o conteúdo do arquivo aparecendo na resposta).

---

## "Schema de dados" — arquivos no disco, sem banco

**N/A pra banco** — átomo stateless, sem SQLite, sem `init_db()`, sem `DB_PATH` (como o 09; e como o 03, que também não tinha banco). O "dado" deste átomo são **arquivos reais no disco**, dentro de um diretório de conteúdo servido pela app.

**Diretório base:** `files/` (ao lado do `app.py`; no container vira `/app/files/`).

**Arquivos de seed (2, benignos, obviamente de demo):**

- `files/readme.txt` — texto curto explicando a "feature" (ex.: *"File viewer demo. The files below are served from this app's `files/` directory. Pick one to see its contents."*).
- `files/notes.txt` — algumas notas inócuas de exemplo (ex.: uma lista/rascunho benigno; **nada** de credencial real, seguindo CLAUDE.md §8.3 — dado fake óbvio).

Papel didático dos seeds: (1) dar o **baseline legítimo** (o aluno lê `notes.txt` e vê a ferramenta funcionar como prometido); (2) dar ao atacante **de onde escapar** com `../`. O `readme.txt` reforça que a pasta tem um conteúdo "oficial" pequeno e conhecido — o contraste com "e no entanto eu li o `/etc/passwd`" fica mais forte.

**`BASE_DIR`** (idêntico nas duas versões, no topo do `app.py`, análogo ao `DB_PATH` do 01):

```python
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
```

Resolve pra `/app/files` no container (WORKDIR `/app`, `app.py` em `/app/app.py`). Absoluto e auto-documentado ("a pasta `files` ao lado do `app.py`"). Ser absoluto importa pro fix (o prefix check compara caminhos absolutos).

---

## Rotas

Imports necessários: `import os`, `from flask import Flask, request, render_template, abort`. (`abort` é usado nas DUAS versões — hygiene de 404; o 03 também importa `abort`. **Sem** `subprocess`, **sem** `sqlite3`.)

### `GET /`

Serve o formulário. Espelha o `GET /` do 09 (renderiza `index.html`, sem lógica).

```python
@app.route("/")
def index():
    return render_template("index.html")
```

### `GET /view` — **a rota vulnerável**

Recebe `file` na query string, monta o caminho concatenando ao `BASE_DIR`, abre e devolve o conteúdo.

```python
@app.route("/view")
def view():
    filename = request.args.get("file", "")
    # VULNERABLE: user input joined onto the base dir and opened directly —
    # nothing confines the resolved path to BASE_DIR
    path = os.path.join(BASE_DIR, filename)
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
        # missing/unreadable file: operational hygiene, orthogonal to the
        # vuln and the fix, identical in both versions
        abort(404)
    return render_template("result.html", filename=filename, path=path, content=content)
```

- **Source:** `request.args.get("file", "")` — GET, query string (análogo ao `host` do 09 e ao `username` do 01).
- **Sink:** `open(os.path.join(BASE_DIR, filename))` — o input entra num caminho de filesystem e a app **abre** o que ele apontar. Não há interpretador/execução; o "sink" é o próprio `open()` sobre um caminho não-confinado.
- **Conteúdo:** `f.read()` renderizado **escapado** num `<pre>` (ver "Renderização do conteúdo").
- **Echo do caminho montado:** `path` também é ecoado num `<pre>` na vulnerable — espelhando o "Executed command" do 09. O aluno **vê** `file=../../../../etc/passwd` virar `path = /app/files/../../../../etc/passwd`. **Removido na fixed** (como o 09 remove o echo do comando).
- **Hygiene de 404:** `try/except OSError: abort(404)` evita um 500 feio quando o aluno erra a contagem de `../` ou digita um arquivo inexistente. É **higiene operacional, ortogonal ao bug e ao fix**, e **idêntica nas duas versões** — exatamente como o `timeout=10` do 09. Não é defesa contra path traversal (um traversal *bem-sucedido* retorna 200 com conteúdo, muito antes de qualquer erro).

### Versão **fixed** — só o sink/checagem muda

```python
@app.route("/view")
def view():
    filename = request.args.get("file", "")
    # FIXED: resolve the real path, then confirm it stays inside BASE_DIR
    base = os.path.realpath(BASE_DIR)
    path = os.path.realpath(os.path.join(base, filename))
    if not path.startswith(base + os.sep):
        abort(404)
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
        abort(404)
    return render_template("result.html", filename=filename, content=content)
```

O `try/except OSError: abort(404)` e a linha `with open(path)` são **contexto inalterado** entre as versões — a **única** mudança de segurança é: resolver com `os.path.realpath` + **confirmar o prefixo** antes de abrir. O `app.py` **DIFERE** entre vulnerable e fixed (o bug/checagem mora no `app.py`) — **igual ao 09 e ao 03, inverso do par XSS**.

---

## O sink — mecanismo de montagem do caminho (`os.path.join` + `open`) e por que NÃO string concat

Para o path traversal existir, a app precisa **montar um caminho a partir do input e abrir o arquivo sem confinar** onde esse caminho pode cair.

**Mecanismo escolhido: `os.path.join(BASE_DIR, filename)` + `open()`.** (Resposta à Open Question #1 do briefing.)

**Por que `os.path.join` e não concatenação de string (`BASE_DIR + "/" + filename`):**

1. **É o idioma real.** `os.path.join(base, user_input)` é como apps Python de verdade montam caminhos. Um pentester auditando código real vê exatamente esse padrão — usar o idioma treina o olho pro mundo real.
2. **`../` funciona nos dois** (a lição canônica está garantida). `os.path.join` **não colapsa** `..` — ele só trata componentes absolutos de forma especial. `os.path.join("/app/files", "../../etc/passwd")` = `"/app/files/../../etc/passwd"`, e o `open()` deixa o kernel resolver os `..` → `/etc/passwd`. O traversal relativo clássico funciona.
3. **A pegadinha do caminho absoluto vira o motor do passo de contraste** (Step 2). `os.path.join("/app/files", "/etc/passwd")` = `"/etc/passwd"` — **um componente absoluto DESCARTA tudo antes dele**. Ou seja: `file=/etc/passwd` (com barra inicial, **zero `../`**) já escapa. Isso é uma footgun documentada do `os.path.join`, e — crucialmente — é a **prova perfeita** de que "o bug não é o `../`": um payload sem nenhum `../` ainda escapa. Espelha exatamente o Step 2 do 09 ("não é o `;`, é o shell"). Com **string concat isso NÃO aconteceria**: `"/app/files" + "/" + "/etc/passwd"` = `"/app/files//etc/passwd"` → `/app/files/etc/passwd`, que fica **dentro** da base e não escapa. Escolher string concat **perderia** esse passo de contraste.
4. **Um único fix mata os dois vetores** (`../` relativo E `/etc/passwd` absoluto) → prova de que são **o mesmo bug** (mesma causa raiz: caminho não-confinado). Ver "Fix".

Ou seja: `os.path.join` não é só mais realista — a footgun do componente absoluto é o que **habilita** o passo "o que a vuln NÃO é". Decisão cravada: **`os.path.join`**.

> **Enquadramento obrigatório (cravar no WALKTHROUGH):** o `../` (relativo) é a **identidade** desta vuln — Step 1 lidera com ele. O caminho absoluto (Step 2) é a **ilustração** de que o `../` não é a essência, não um vetor co-igual. O átomo se chama *path traversal*; o `../` é a estrela, o absoluto é o holofote que mostra a causa raiz. Não sobrecarregar o absoluto a ponto de ofuscar o `../`.

---

## O container e os arquivos de seed — mais perto do 01 do que o 09

Diferente do `command-injection-basic` (09), que precisou de `apt install iputils-ping` (a feature era um binário do OS), este átomo é **stdlib puro** (`os` + `open`). Não há binário externo, não há `subprocess`. Então o `Dockerfile` é o **esqueleto do átomo 01/08 + uma linha** — `COPY files ./files` (pra os arquivos de seed entrarem na imagem):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
COPY files ./files
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

`Dockerfile` **idêntico entre vulnerable e fixed** (como todos os átomos). **Sem** `apt`, **sem** `sysctls` no compose (nada de ping aqui).

**Container roda como root** (sem diretiva `USER`, como todos os átomos). Consequência didática: como root, a app lê **qualquer** arquivo do container — `/etc/passwd`, o source em `/app/app.py`, e (em tese) `/etc/shadow`. O walkthrough mantém os alvos **proporcionais e demonstrativos** (`/etc/passwd`, `../app.py`) — CLAUDE.md §8.4. Mencionar que "roda como root, então qualquer arquivo legível está ao alcance" como enquadramento de impacto, **sem** dumpar arquivos gratuitamente.

**`/etc/passwd` do container:** Debian slim, **idêntico ao capturado no `command-injection-basic` (09)** — mesma base `python:3.11-slim`. Revalidar na geração pra o "output esperado" bater, mas espera-se byte-a-byte igual ao do 09 (`root:x:0:0:root:/root:/bin/bash`, `daemon`, `bin`, ... `nobody`).

---

## Renderização do conteúdo — `<pre>` escapado (um átomo = uma vuln)

O conteúdo lido (`content`) e o caminho ecoado (`path`) vão em `<pre>` com o **autoescape padrão do Jinja LIGADO** — **sem `|safe`**. Exatamente como o 09 renderiza `<pre>{{ output }}</pre>` e o 01 renderiza `<pre>{{ query }}</pre>`.

**Por que importa — evitar um segundo bug:** um arquivo lido pode conter `<`, `>`, `"` (ler um `.html`, ou o próprio `result.html` via traversal, ou o `app.py` com suas strings). E o `path` ecoado contém o input do atacante (`file=<script>...`). Sem escape, isso viraria um **reflected XSS acidental empilhado por cima do path traversal** — violando "um átomo = uma vulnerabilidade" (CLAUDE.md §2). O autoescape garante que conteúdo e caminho aparecem como **texto literal**.

> **Cravar no `DIFF`/`WALKTHROUGH` e nos comentários do código:** o escape **não é** o fix de path traversal (o fix é o confinamento do caminho; ver abaixo). É higiene pra manter o átomo com **exatamente um** bug. Vulnerable e fixed **ambas** escapam. Mesmo texto do 09.

---

## HTML

Dois templates, ≤40 linhas cada, CSS ≤5 linhas inline, sem JS, sem framework. Reusar o esqueleto do 09 (banner, footer de Burp, `<style>` sans-serif/720px, `<pre>` cinza).

**`index.html`** (idêntico em vulnerable/fixed): banner de aviso no topo, `<h1>File Viewer</h1>`, `<form method="get" action="/view">` com um campo `file` + submit, uma dica listando os arquivos oferecidos (`<p>Available files: notes.txt, readme.txt</p>`), footer de Burp. Espelha o form do 09, trocando `host`→`file` e `/ping`→`/view`.

**`result.html`** (esboço da versão vulnerable; a fixed dropa o bloco "Resolved path:"):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>File &mdash; {{ filename }}</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}pre{background:#eee;padding:0.5em;border-radius:4px;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>File contents</h1>
<p><strong>Resolved path:</strong></p>
<pre>{{ path }}</pre>
<p><strong>Contents:</strong></p>
<pre>{{ content }}</pre>
<p><a href="/">&larr; Back</a></p>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- Banner de aviso verbatim (`&#9888; Intentionally vulnerable. Run locally only.`).
- `{{ filename }}`, `{{ path }}`, `{{ content }}` **todos autoescapados** (nunca `|safe`).
- O bloco `Resolved path:` + `<pre>{{ path }}</pre>` espelha o "Executed command" do 09 — o aluno **vê** `file=../../../../etc/passwd` virar `path = /app/files/../../../../etc/passwd`. **Removido na fixed** (a fixed não passa `path` ao template).
- Footer padrão com a dica de Burp.

---

## Fix

Diff esperado entre `vulnerable/app.py` e `fixed/app.py`, na view `/view`:

```diff
     filename = request.args.get("file", "")
-    # VULNERABLE: user input joined onto the base dir and opened directly —
-    # nothing confines the resolved path to BASE_DIR
-    path = os.path.join(BASE_DIR, filename)
+    # FIXED: resolve the real path, then confirm it stays inside BASE_DIR
+    base = os.path.realpath(BASE_DIR)
+    path = os.path.realpath(os.path.join(base, filename))
+    if not path.startswith(base + os.sep):
+        abort(404)
     try:
         with open(path) as f:
             content = f.read()
     except OSError:
         abort(404)
-    return render_template("result.html", filename=filename, path=path, content=content)
+    return render_template("result.html", filename=filename, content=content)
```

(E `fixed/templates/result.html` dropa o bloco `Resolved path:` / `<pre>{{ path }}</pre>` — mudança incidental, exatamente como a fixed do 09 dropa o echo do comando e a do 01 dropa o debug da query.) O `try/except OSError` e o `with open(path)` aparecem como **contexto inalterado** — reforçando que **a única mudança de segurança é o confinamento do caminho**.

**Uma frase de por que resolve:** `os.path.realpath` **colapsa os `../`** (e resolve componentes absolutos) pra o caminho canônico absoluto; o **prefix check** (`path.startswith(base + os.sep)`) confirma que esse caminho canônico caiu **dentro** do diretório permitido. `../../../../etc/passwd` e `/etc/passwd` **ambos** resolvem pra `/etc/passwd`, que **não** começa com `/app/files/` → `abort(404)`. Um arquivo legítimo (`notes.txt`) resolve pra `/app/files/notes.txt`, que começa com `/app/files/` → servido.

### Resposta do fix ao escapar: **404** (não 403). (Resposta à Open Question #5.)

Escolhido **404** (não o 403 do `idor-numeric-id`), por dois motivos:

1. **Não vaza existência.** 403 ("existe, mas você não pode") confirmaria ao atacante que `/etc/shadow` existe vs. não existe. 404 não confirma nada sobre o que há fora da base.
2. **Colapsa os dois modos de falha.** Na fixed, "path escapou da base" (prefix check → 404) e "arquivo in-base não existe" (`open` falha → 404) retornam **o mesmo** 404 → o atacante **não distingue** "saí do sandbox" de "arquivo não existe". Isso é uma **propriedade de segurança** real (não dá pra mapear o que escapa vs. o que só falta).

**Contraste explícito com o 03 (vai no DIFF):** o `idor-numeric-id` usa **403** porque lá o objeto (nota 2) é um recurso legítimo da app que o caller não está autorizado a ver — "forbidden" é semanticamente certo. Aqui o "recurso" é um caminho **fora do domínio da app** — "not found (entre os arquivos que sirvo)" leaka menos. A escolha do status code depende de você querer, ou não, **admitir a existência** do recurso. Ótimo ponto de contraste entre os dois A01.

### Notas obrigatórias no DIFF.md

1. **Blocklist de `../` é jogo perdido** (paralelo direto ao "escaping é jogo perdido" do SQLi/01 e command injection/09). Filtrar a string `../` não adianta: `..%2f` (encoded, e o Werkzeug decoda de volta pra `../` no valor da query), `....//` (o filtro remove o `../` do meio e sobra `../`), `..\` (Windows), double-encoding — e, o mais direto, **o caminho absoluto `/etc/passwd`, que não tem nenhum `../`**. O **Step 2 do walkthrough já prova isso** (absoluto, zero `../`). A raiz não é "esqueceram de bloquear o `../`"; é "o caminho não é confinado". A correção não é **limpar a string** — é **RESOLVER o caminho e CONFIRMAR o destino**. Mesma lição transferível da série: **valide o resultado contra o permitido (allowlist de localização), não o input contra o proibido (blocklist)**.

2. **`basename()` como alternativa/camada — com papel concreto** (paralelo ao HttpOnly do 08 e à allowlist do 09, mas com um sabor a mais). `os.path.basename(filename)` descarta **qualquer** componente de diretório (fica só o nome do arquivo), o que **também** barra o traversal e é **mais simples** que realpath+prefixo. Papel concreto (dar como o 09 deu à allowlist): **se a app NÃO precisa de subdiretórios**, `basename` é um **fix legítimo e mais simples**; **se precisa** servir `docs/readme.txt`, ele mata o subdiretório legítimo, e aí `realpath`+prefixo é o caminho. Ou seja, aqui `basename` é uma **alternativa condicional** (não só "camada extra") — enquadrar com precisão: não é o fix universal, é o fix quando a superfície não tem subpastas. Manter **uma variável só** mudando entre vulnerable/fixed (o confinamento) → por isso a fixed usa realpath+prefixo (o fix geral), e o `basename` fica **discutido no DIFF**, não empilhado no código (igual o 08 não empilha HttpOnly).

3. **`send_from_directory` — o idioma do Flask (nota de mundo real).** O Flask já traz `send_from_directory(dir, filename)`, que faz **exatamente** esse containment check por baixo (resolve e confirma que caiu dentro de `dir`, senão 404). Em código real, **prefira-o** a um `open()` na mão. A razão de este átomo fazer na mão é a feature: `send_from_directory` **envia o arquivo** como resposta (download/inline), e aqui a gente **renderiza o conteúdo inline num `<pre>`** — então fazemos à mão o mesmo check que o helper faria. Nota honesta e prática (preempta o leitor esperto que pergunta "por que não `send_from_directory`?").

4. **A01, não A03 — a moldura de access control** (o coração; ver "Classe de vulnerabilidade"). O bug **não é** "input virou código" (injection); é **"input alcançou um recurso fora do seu escopo autorizado"** (broken access control). Amarrar ao `idor-numeric-id` (03): IDOR = acessa recurso trocando um ID; path traversal = acessa recurso navegando o filesystem. Ambos são "a app te deu algo que não era seu". Contrastar com `command-injection-basic` (09): lá o input virou **código executável** (um comando); aqui virou **uma localização** (um caminho). Esta seção carrega os cross-refs (03 e 09).

5. **O bug mora no `app.py` (inverso do par XSS).** `vulnerable/app.py` ≠ `fixed/app.py` (o confinamento mudou). Nota de contraste breve: no `xss-stored`/`xss-reflected` o `app.py` era idêntico e o bug morava no template; aqui é o oposto. Auditoria: pra path traversal você lê o código atrás de `open(`/`os.path.join(` com input do usuário e pergunta "**o que confina esse caminho?**" — se a resposta é "nada", achou o bug. (Diferente do IDOR, que "não greppa" por ser check ausente sem sink — aqui há sink greppável.)

---

## Walkthrough — payloads

Estrutura de 4 beats espelhando o 09: **baseline legítimo** → **confirmar o traversal (`../`)** → **provar que não é o `../` (caminho absoluto — o passo "o que a vuln NÃO é")** → **impacto: leitura arbitrária além do `/etc/passwd`**. Fecha com a distinção command injection × path traversal (anchor + tabela) e a amarra A01 com o `idor-numeric-id`.

**Estrutura dos blocos por payload (reusar do 09):** cada payload mostra um bloco **Payload (decoded)** (leitura) e um **Request line** (`GET /view?file=... HTTP/1.1` / `Host: 127.0.0.1:8010`, colável no Repeater).

> **Abertura do walkthrough — plantar a distinção.** A seção "Context" tem que já teasar a âncora: *"você vai acabar lendo `/etc/passwd`, igualzinho ao `command-injection-basic` — mas pelo mecanismo OPOSTO. Lá você fez a app RODAR um comando; aqui você faz a app ABRIR um arquivo."* Abrir E fechar na distinção (a abertura tease, o fechamento desenvolve com a tabela).

### Context + Spot the bug

- **Context:** file viewer, lê um arquivo por nome e mostra o conteúdo. Trabalhado **inteiro no Burp** (o conteúdo volta na resposta; browser não é obrigatório — igual ao 09). Tease da âncora (acima).
- **Spot the bug:** mostrar a view `/view` da vulnerable. Apontar `os.path.join(BASE_DIR, filename)` + `open()`. O bug é **o que não confina** o caminho. As **duas coisas feitas certo** (pra não confundir com o bug), igual ao 09: (a) o conteúdo é **escapado** no `<pre>` (senão um arquivo com HTML viraria XSS — *não* é o fix); (b) o `try/except OSError → 404` é higiene (evita 500 em typo/depth errado), **idêntico nas duas versões**. Grep de primeira passada: `open(`, `os.path.join(`, `send_file(` com input do usuário. A pergunta de auditoria: **"o que confina esse caminho ao diretório permitido?"**

### How the app serves files (subseção curta, análoga ao "How auth works" do 03)

Explicar: a app serve **apenas** os arquivos de `files/` (`notes.txt`, `readme.txt`); é o "diretório oficial" da feature. O exploit faz a app servir arquivos **de fora** dessa pasta. O echo "Resolved path" na `result.html` mostra o caminho que a app **realmente** abriu — use-o pra enxergar o traversal acontecendo.

### `### A note on URL encoding` (subseção, espelhando o 09/01 — mas com um contraste)

Diferente do 09 (onde espaço→`%20` e `&`→`%26` mordiam), **aqui os payloads não têm espaço nem `&`** — `.`, `/` e letras são todos seguros no **valor** da query. Então:

- **`/` e `.` viajam crus** no valor da query (`?file=../../../../etc/passwd` vai inteiro; o `/` é legal em query string, o Werkzeug não quebra nele). Nada a encodar pra o `../` clássico.
- **`..%2f` é a forma encodada de `../`** — o Werkzeug **decoda** `%2f`→`/` no valor da query, então `file=..%2f..%2fetc/passwd` chega como `../../etc/passwd` e funciona **idêntico**. Ponto didático: `..%2f` é **exatamente** o que derrota um blocklist ingênuo que só grepa a string literal `../` (amarra com "blocklist é jogo perdido" no DIFF).
- **Nota do form (trilha browser):** o form (`application/x-www-form-urlencoded`) encoda `/`→`%2f` no envio; o servidor decoda de volta — de novo, prova que `..%2f` **é** `../`. Pelo browser o encoding é automático; pelo Burp, cole o valor decoded e use **Ctrl+U** se quiser encodar tudo.

*(Validar na geração: `%2f` decoda no valor da query com Werkzeug/Flask 3. Alta confiança — decodificação de valor de query é padrão; o caso de `%2f`-não-decoda é só no PATH da URL, não na query.)*

### Baseline — a ferramenta funcionando (estabelece o "normal")

- **Payload (decoded):** `file=notes.txt`
- **Request line:** `GET /view?file=notes.txt HTTP/1.1`
- **Observação:** o conteúdo de `notes.txt` aparece no `<pre>`. O "Resolved path" mostra `/app/files/notes.txt`. A ferramenta faz o que promete — serve um arquivo que ela oferece. (Igual o 09 mostra o `ping 127.0.0.1` funcionando antes de subverter.)

### Step 1 — Confirm the traversal (o `../` canônico)

O traversal relativo clássico: subir a árvore e ler fora da pasta.

- **Payload (decoded):** `file=../../../../etc/passwd`
- **Request line:** `GET /view?file=../../../../etc/passwd HTTP/1.1`
- **Observação:** o `<pre>` traz o `/etc/passwd` do container. O "Resolved path" mostra `/app/files/../../../../etc/passwd` — o aluno **vê** o input dele virar um caminho que sobe a árvore. Prova: o input não é um nome de arquivo confinado, é uma **rota pelo filesystem**.
- **Nota de profundidade (didática):** a base é `/app/files` (2 níveis abaixo de `/`), então o **mínimo** pra chegar em `/etc/passwd` é `../../etc/passwd` (2 `../`). O walkthrough usa `../../../../` (4) porque **`..` de sobra em `/` são no-op** (o pai de `/` é `/`) e, num alvo real, você **não sabe** a profundidade exata — então **overshoot** é o hábito correto. (Validar: 4 funciona, 2 é o mínimo.)

### Step 2 — It's not the `../`: the path just isn't confined (o passo de contraste — "o que a vuln NÃO é")

O passo obrigatório de contraste (CLAUDE.md §5) — isola a causa real e desmonta o mal-entendido vizinho ("é só bloquear o `../`"). Análogo direto ao Step 2 do 09 ("não é o `;`, é o shell") e ao Step 4 do 03 ("é check ausente, não identidade errada").

- **Payload (decoded):** `file=/etc/passwd` (caminho **absoluto**, com barra inicial — **zero `../`**)
- **Request line:** `GET /view?file=/etc/passwd HTTP/1.1`
- **Observação:** o **mesmo** `/etc/passwd` de novo — mas **sem nenhum `../`**. O `os.path.join(BASE_DIR, "/etc/passwd")` descartou o `BASE_DIR` (componente absoluto ganha) e abriu `/etc/passwd` direto. O "Resolved path" mostra `/etc/passwd` (a base sumiu).
- **Lição (cravar):** o bug **não é** "esqueceram de bloquear o `../`". É que **o caminho não é confinado** à pasta permitida — e um caminho absoluto chega no mesmo lugar **sem usar `../` nenhum**. Um dev que só filtra a string `../` é **completamente bypassado** por `/etc/passwd`. Por isso blocklist é jogo perdido, e por isso o fix tem que **resolver o caminho e confirmar o destino**, não filtrar caracteres. (Cravar o contraste com o 09: lá "escaping de metacaractere é jogo perdido, tire o shell"; aqui "filtrar `../` é jogo perdido, confine o caminho".)

### Step 3 — Read beyond /etc/passwd: the app's own source (impacto de leitura arbitrária)

Provar que não é só `/etc/passwd` — é **qualquer** arquivo legível. Ler o source da própria app é impacto realista (vaza secret, config, e dá mapa pra mais bugs). Paralelo ao Step 3 do 09 (que lê `/etc/passwd` como clímax; aqui o clímax é "leia o próprio código do servidor").

- **Payload (decoded):** `file=../app.py`
- **Request line:** `GET /view?file=../app.py HTTP/1.1`
- **Observação:** o `<pre>` traz o **próprio `app.py` vulnerável** (`/app/files/../app.py` = `/app/app.py`). O aluno lê o código do servidor — incluindo o comentário `# VULNERABLE` e o sink.
- **Nota de navegação (didática, amarra o modelo mental):** repare que aqui é **1 `../` só** (`app.py` está em `/app`, um nível acima de `/app/files`), enquanto o `/etc/passwd` precisou de 2+ (overshoot 4). **A quantidade de `../` depende de ONDE o alvo está em relação à base** — você está **andando pela árvore** e contando passos até o destino. Isso reforça a imagem de **navegação** (a essência de A01 aqui).
- **Enquadramento de impacto (obrigatório, e honesto):** aqui roda em container descartável; num alvo real, *arbitrary file read* vaza source, config, `.env`, chaves SSH, credenciais de cloud — **e frequentemente encadeia** pra compromisso maior (cred vazada → login; source → mais bugs). Mas **é leitura**, não execução: **NÃO chamar de RCE**. Manter demonstrativo (CLAUDE.md §8.4) — `/etc/passwd` e o próprio source, **nada** destrutivo, sem dumpar `/etc/shadow` gratuitamente.

### `### Why this is path traversal, not command injection (and it lives in A01)` — fechamento

Fecha na distinção. Incluir o **bloco-âncora** e a **tabela de contraste** (seção "Classe de vulnerabilidade" acima). Bloco-âncora EN (a ser usado no `WALKTHROUGH.md`; a versão PT no `WALKTHROUGH.pt-BR.md` é a formulação do mantenedor, quase verbatim):

> **command injection vs path traversal — the distinction that matters.** In `command-injection-basic` you made the app **run a command** of yours. Here you made the app **open a file** of yours — using the very capability it already had (opening files), just pointed outside its own yard. One is **execution**; the other is **navigation**. Both handed you `/etc/passwd`, but by opposite routes: command injection *ran `cat` for you*; path traversal made the app *itself be* the `cat`. In command injection you had to **invoke** `cat`; here the vulnerable file viewer already **is** a read-a-file-and-print-it machine — you only redirected it out of its folder. **The app *is* `cat`.**

Depois da tabela, amarrar A01: *este é o motivo de o átomo viver em Broken Access Control, não Injection — nada virou código; um input te levou a um recurso fora do escopo. É o mesmo formato do `idor-numeric-id`: lá você trocou um ID pra ler a nota de outro; aqui você navegou o filesystem pra ler um arquivo de fora. Nos dois, a app te entregou algo que não era pra você — e o fix é a checagem que faltava (ownership lá; confinamento aqui).*

### `## Exploitation via browser (secondary track, optional)` + `## Why the fix works`

- **Browser (secundária, opcional):** os mesmos payloads na barra de endereço (`http://127.0.0.1:8010/view?file=../../../../etc/passwd`, `.../view?file=/etc/passwd`, `.../view?file=../app.py`) ou pelo form. O browser **não normaliza `../` na query string** (só no path), então os payloads vão crus; pelo form, `/`→`%2f` e o servidor decoda. Primeira experiência de baixa fricção — **mas Burp é a principal** (o conteúdo volta na resposta, Burp basta pra tudo). *(Validar: browser não colapsa `../` na query — alta confiança, dot-segment removal é só no path.)*
- **Why the fix works:** rodar os mesmos payloads contra a porta **8110** (fixed): **todos** → **404** (tanto `../../../../etc/passwd` quanto `/etc/passwd` quanto `../app.py`), enquanto `file=notes.txt` → 200 com conteúdo. **Um fix, os dois vetores mortos** = prova de que eram o mesmo bug. Explicar o mecanismo (realpath colapsa `../` e resolve o absoluto → prefix check confirma o confinamento → 404 pra qualquer coisa fora de `/app/files/`). Mencionar `basename` (alternativa quando não há subpasta), `send_from_directory` (o idioma do Flask que faz isso por baixo) e a nota "blocklist é jogo perdido" — detalhes no `DIFF.md`.

---

## Dependências extras

```
Flask==3.0.0
```

Idêntico aos átomos 01/02/06/07/08/09. `os` é stdlib; `open` é builtin. **Nada** de pip além do Flask, e — diferente do 09 — **nada** de `apt` (sem binário de OS; a feature é `open()` puro). CLAUDE.md §3.6 respeitado no limite: o átomo mais enxuto de dependências da série.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria | **A01 — Broken Access Control** | O bug é "input alcançou recurso fora do escopo" (acesso), não "input virou código" (injection). Amarra ao `idor-numeric-id` (03). |
| Feature | **File viewer** (mostra conteúdo inline), stateless | Silhueta in-band do 09 (input entra, conteúdo volta num `<pre>`); sem download (chato, tira foco). Sem banco: o loot é o filesystem. |
| Método HTTP | **GET** com query string (`?file=...`) | Espelha 09/01. URL direto em browser e Burp. |
| Mecanismo de montagem | **`os.path.join(BASE_DIR, filename)` + `open()`** | Idioma real; `../` funciona; a footgun do componente **absoluto** (`join(base,"/etc/passwd")` descarta a base) **habilita o Step 2 de contraste**. String concat perderia o vetor absoluto. |
| Vetores no walkthrough | **`../` relativo (Step 1) + `/etc/passwd` absoluto (Step 2)** + `../app.py` (Step 3) | `../` é a identidade; o absoluto é o holofote ("não é o `../`"); app.py é o impacto (leitura arbitrária). |
| Diretório base + seed | `files/` com `notes.txt` + `readme.txt`; `BASE_DIR = os.path.join(dirname(abspath(__file__)), "files")` → `/app/files` | Baseline legítimo + de onde escapar. Base absoluta pro prefix check. Dado fake óbvio (§8.3). |
| Alvo de impacto | **`/etc/passwd`** (Steps 1–2) + **`../app.py`** (Step 3) | `/etc/passwd` é o clássico e o destino compartilhado com o 09 (âncora). app.py = leitura arbitrária realista (source disclosure). |
| Fix (principal) | **`os.path.realpath` + prefix check** (`startswith(base + os.sep)`), senão `abort(404)` | Resolve os `../`/absolutos pro caminho canônico e confirma confinamento. Allowlist de **localização**, não blocklist de string. Fecha os dois vetores. |
| Resposta do fix | **404** (não 403) | Não vaza existência; colapsa "escapou" e "não existe" no mesmo status (o atacante não distingue). Contraste didático com o 403 do 03. |
| Fix alternativo/camada (no DIFF) | `os.path.basename` (alternativa **se não há subpasta**); `send_from_directory` (idioma Flask, faz o check por baixo) | `basename` é fix legítimo e mais simples quando não há subdiretório; realpath+prefixo é o geral. Uma variável só muda no código (o confinamento); resto no DIFF. Paralelo ao HttpOnly/08 e allowlist/09. |
| Hygiene de erro | `try/except OSError: abort(404)` em **ambas** as versões | Evita 500 em typo/depth errado. Ortogonal ao bug/fix, idêntica nas duas versões — igual ao `timeout=10` do 09. |
| Renderização do conteúdo | `<pre>{{ content }}</pre>` e `<pre>{{ path }}</pre>` **autoescapados** (sem `\|safe`), em **ambas** | Evita reflected XSS acidental empilhado (arquivo/input com `<`). Espelha `<pre>{{ output }}` do 09. Não é o fix. |
| Echo do caminho montado | `<pre>{{ path }}</pre>` na vulnerable; **removido** na fixed | Espelha o "Executed command" do 09: aluno vê input virar caminho. |
| Nº de templates | **Dois** (`index.html` form + `result.html` conteúdo) | Espelha 09 (`index.html`/`result.html`). |
| `app.py` vulnerable × fixed | **Diferem** (o confinamento mudou) | Igual ao 09 e ao 03, inverso do par XSS. O bug mora no `app.py`. |
| Dockerfile | Esqueleto 01/08 **+ `COPY files ./files`** | Precisa dos seeds na imagem. **Sem** `apt` (diferente do 09 — sem binário de OS). |
| User do container | **root** (sem `USER`, como todos) | Lê qualquer arquivo; enquadrar impacto sem dumpar `/etc/shadow`. |
| Trilha Burp vs browser | **Burp principal, browser secundário opcional** | Conteúdo volta na resposta → Burp basta. Igual ao 09/01, diferente do `xss-stored`. |
| Nº de steps | **Baseline + 3 steps** (traversal `../` / não-é-o-`../` / source) + fechamento (âncora + tabela) | Escalada espelhando o 09. Step 2 é o passo obrigatório "o que a vuln NÃO é". |

---

## Open questions — status

Todas as 7 open questions do briefing **resolvidas nesta spec com justificativa**. Restam só itens de **validação na geração** (não-bloqueantes, CLAUDE.md §11).

**Resolvidas (decisão cravada nesta spec):**

1. **Mecanismo de montagem → `os.path.join`.** Idiomático; `../` funciona; a footgun do componente absoluto habilita o Step 2. (Ver "O sink".)
2. **Vetores → ambos:** `../` relativo (Step 1, canônico) + `/etc/passwd` absoluto (Step 2, contraste) + `../app.py` (Step 3, impacto).
3. **Diretório base + seed → `files/` com `notes.txt` + `readme.txt`.** `BASE_DIR = /app/files`.
4. **Alvo de impacto → `/etc/passwd`** (Steps 1–2, destino compartilhado com o 09) **+ `../app.py`** (Step 3).
5. **Resposta do fix → 404** (não vaza existência; colapsa escapou/não-existe; contraste com o 403 do 03).
6. **Progressão → Baseline + 3 steps + fechamento** (traversal / não-é-o-`../` / source). Step 2 = contraste.
7. **Nota de encoding →** `/` e `.` crus no valor da query; `..%2f` decoda pra `../` (o bypass de blocklist, amarra com o DIFF). Sem trap de `%20`/`%26` (não há espaço/`&` nos payloads) — contraste explícito com o 09.

**Pendentes — validação na geração (não-bloqueantes):**

- **A.** Conteúdo exato de `/etc/passwd` do container — espera-se **idêntico** ao do `command-injection-basic` (mesma base `python:3.11-slim`); revalidar pra o "output esperado" bater.
- **B.** Profundidade dos `../`: confirmar que `../../etc/passwd` (2, mínimo) e `../../../../etc/passwd` (4, overshoot) **ambos** leem `/etc/passwd` a partir de `/app/files`.
- **C.** `../app.py` lê `/app/app.py` (layout WORKDIR `/app` + `COPY app.py .` — esperado, confirmado pelo Dockerfile do 09).
- **D.** `%2f` decoda pra `/` no **valor da query** (Werkzeug/Flask 3) — alta confiança; confirmar `file=..%2f..%2fetc/passwd` funciona.
- **E.** O browser **não** normaliza `../` na query string (só no path) — alta confiança; confirmar na trilha secundária.
- **F.** Na **fixed** (8110): `notes.txt` → 200; `../../../../etc/passwd`, `/etc/passwd`, `../app.py` → **404**. Confirmar prefix check (`startswith(base + os.sep)`) rejeita os três e aceita o legítimo.

**Bloqueante remanescente:** nenhum. Spec pronta pra revisão do mantenedor; nada exige decisão adicional antes da geração — resta só a validação acima na próxima sessão.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **o gêmeo do 09 pela outra perna** — mesma silhueta (GET, `<pre>` escapado, echo do alvo montado, form em `/` + endpoint), mesmo destino (`/etc/passwd`), mecanismo **oposto** (navegação de filesystem, não execução). Cada parágrafo do walkthrough deve poder ser lido com o `command-injection-basic` aberto ao lado; a diferença ("a app não RODA um comando, ela ABRE um arquivo — e por isso é A01, não A03") deve estar visível. **Abrir e fechar** o walkthrough na distinção (tease no Context, desenvolvimento + tabela no fechamento).
- **Leitura obrigatória antes de gerar (CLAUDE.md §10.5):** `command-injection-basic` (09) inteiro (gêmeo por mecânica — reusar silhueta, echo `<pre>`, nota de encoding, forma do DIFF/WALKTHROUGH, compose, Dockerfile) **e** `idor-numeric-id` (03) inteiro (gêmeo por categoria — framing A01, passo de contraste "o que a vuln NÃO é", vocabulário de access control).
- **Átomo stateless:** sem banco, sem `init_db()`, sem `DB_PATH`. Em vez disso, `BASE_DIR` + arquivos de seed em `files/`.
- **`app.py` DIFERE entre vulnerable e fixed** (o confinamento do caminho). `Dockerfile` idêntico entre as duas versões (e diverge do 09 por **não** ter `apt`; diverge do 01/08 só por `COPY files ./files`).
- **Sink no `app.py`:** `os.path.join(BASE_DIR, filename)` + `open()`, **sem** confinamento. Fix: `base = os.path.realpath(BASE_DIR)`; `path = os.path.realpath(os.path.join(base, filename))`; `if not path.startswith(base + os.sep): abort(404)`. Usar `realpath` (não `abspath` — realpath também resolve symlink, mais robusto). **Não** tentar sanitizar/filtrar a string `../`.
- **Detalhe sutil do prefix check (cravar no DIFF, análogo ao `-` inicial do 09):** é `base + os.sep`, **não** só `base` — senão um irmão tipo `/app/files-secret` passaria (`"/app/files-secret/x".startswith("/app/files")` é `True`; com `+ os.sep` vira `False`). (Pode citar `os.path.commonpath` como alternativa ainda mais robusta, em uma linha.)
- **Hygiene de erro (`try/except OSError: abort(404)`) em AMBAS as versões** — evita 500 em typo/depth errado. É **ortogonal ao bug e ao fix**, idêntica nas duas versões (igual ao `timeout=10` do 09). **Só o confinamento muda** entre vulnerable e fixed. Comentar no código.
- **Conteúdo e caminho SEMPRE escapados** (`<pre>{{ content }}`, `<pre>{{ path }}`, autoescape padrão, **sem `|safe`**), em ambas — pra não criar reflected XSS acidental (arquivo/input com `<`). Comentar: **não é** o fix de path traversal; é higiene de "um bug só".
- **Container roda como root** → lê qualquer arquivo. Documentar os alvos esperados (`/etc/passwd` = idêntico ao do 09; `../app.py` = o próprio source). Enquadrar impacto: leitura arbitrária (source/config/creds), **não RCE**; inofensivo no container efêmero, sério num alvo real. **Não** adicionar hardening (USER não-root, seccomp) — ofuscaria o sink.
- **`docker-compose.yml`:** `127.0.0.1:8010:5000` (vulnerable), `127.0.0.1:8110:5000` (fixed). Reusar o esqueleto de duas services do 09. **Sem** `sysctls`.
- **Payloads didáticos e proporcionais** (CLAUDE.md §8.4): `notes.txt`, `../../../../etc/passwd`, `/etc/passwd`, `../app.py`. **Nunca** dumpar `/etc/shadow` gratuitamente, nada destrutivo.
- **Cross-atom reference policy:** OK e **desejável** referenciar `command-injection-basic` (09, mecânica contrastante) e `idor-numeric-id` (03, categoria A01 compartilhada) **explicitamente**; OK referenciar `sqli-union-basic` (01) e os demais em `main` (02/04/05/06/07/08). **Proibido** referenciar qualquer átomo da Fase 3+ ainda não publicado (`idor-uuid-guessable`, `bola-rest`, etc.) — mesmo sendo A01 "parentes". Ao falar de leitura de arquivo, manter no frame de path traversal (navegação), **não** foreshadowar XXE ou LFI-como-átomo.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF), padrão v0.1.0. H1 do `README.md` e `README.pt-BR.md` **idêntico**: `# path-traversal-basic — Path Traversal`.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md`, linkando `https://portswigger.net/web-security/file-path-traversal` com o texto **`Path traversal`** preservado em inglês também no PT.
- **CHANGELOG.md:** ao gerar o átomo (**não agora**), adicionar em `[Unreleased] / Added`: `` Added atom 10: `path-traversal-basic` — Path traversal (A01 Broken Access Control). `` (mesmo padrão das linhas dos átomos 06–09).
- **ROADMAP.md:** marcar o átomo 10 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar ROADMAP nesta fase de spec. Nota: este átomo **fecha a Fase 2** — o versionamento/release (v0.2.0) é tratado **depois**, fora desta spec.
- **Validar manualmente** (CLAUDE.md §11): baseline (`file=notes.txt` → conteúdo); Step 1 (`../../../../etc/passwd` → passwd); Step 2 (`/etc/passwd` absoluto → mesmo passwd, prova "não é o `../`"); Step 3 (`../app.py` → source); e na **fixed** (8110) os três payloads de ataque → **404**, `notes.txt` → 200. Confirmar itens A–F das Open Questions.
- Se houver dúvida sobre o nome exato de uma aba do Burp, **perguntar antes de inventar** (CLAUDE.md). Este átomo usa pouco do Burp (só Repeater no GET) — sem Intruder.
