# Spec — Átomo 09: `command-injection-basic`

> Documento de especificação para o Claude Code implementar o nono átomo do projeto `atomicvulns` (Fase 2, quarto átomo da fase). Leia junto com `CLAUDE.md` (Seções 3.3, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — o átomo de referência canônico `atoms/A03-injection/sqli-union-basic/` na íntegra (é o **paralelo conceitual direto**: a variante "basic"/in-band/output-visível de uma classe de injection), além do átomo recém-fechado `atoms/A03-injection/xss-stored/` como referência de **formato atualizado** (estrutura de README/WALKTHROUGH/DIFF, `docker-compose.yml`, `Dockerfile`, blocos de payload decoded/Burp-ready).
>
> Esta spec captura apenas as decisões *específicas* deste átomo — convenções estruturais (Theory primer, port scheme, banner, bilinguismo, etc.) ficam no `CLAUDE.md`. Onde o `sqli-union-basic` já resolveu uma questão (forma do GET com query string, form em `/` + endpoint de resultado, echo do input montado num `<pre>` autoescapado, nota de URL encoding, forma do DIFF), a instrução aqui é **reusar a forma do átomo 01**, não reinventar. Este átomo é, deliberadamente, o "sqli-union-basic do shell".

---

## Identidade

- **ID:** `command-injection-basic`
- **Categoria OWASP:** A03 — Injection
- **Pasta:** `atoms/A03-injection/command-injection-basic/`
- **Número sequencial:** 09
- **Porta vulnerable:** `127.0.0.1:8009`
- **Porta fixed:** `127.0.0.1:8109`
- **Theory primer:** [PortSwigger: OS command injection](https://portswigger.net/web-security/os-command-injection) — página conceitual de introdução confirmada por fetch (H1 literal **"OS command injection"**; abre com "OS command injection is also known as shell injection"). É a página "What is X?", **não** a listagem de labs. O texto do link usa **"OS command injection"** — forma verbatim do H1 e da auto-descrição da página. Nome preservado em inglês também no README PT (convenção v0.1.0). O bloco do README segue o esqueleto verbatim dos átomos 01/08 (só troca o link e o label).

---

## Classe de vulnerabilidade

OS command injection (shell injection), variante **basic / in-band / output-visível**. Input não sanitizado é concatenado numa string que a aplicação passa a um **shell do sistema operacional** para executar; o atacante injeta **metacaracteres de shell** (`;`, `|`, `&&`, `||`, `$(...)`, backticks) e encadeia os próprios comandos ao comando pretendido pela app. Nesta variante a app **roda o comando e devolve o output (stdout+stderr) na própria resposta HTTP** — o atacante injeta `; whoami` e **vê** `root` voltar na tela. É o paralelo direto do `sqli-union-basic` (dado direto na resposta), **não** do blind: não há time-delay nem canal out-of-band aqui.

**Por que esta variante é didaticamente essencial — e o que ela ensina que os outros átomos de injection não ensinam:** um **novo sink, o shell do OS**. Os átomos de injection anteriores mandavam input não sanitizado para interpretadores diferentes — o SQL engine (`sqli-*`) e o parser HTML/JS do browser (`xss-*`). Aqui o interpretador é o **shell** (`/bin/sh`), e a app o invoca via `subprocess.run(..., shell=True)`. A mesma lente de auditoria dos átomos anteriores — rastrear input do **source** até o **sink** perigoso — agora aplicada ao shell. E o **impacto é o mais grave da série**: não é exfiltração de dado (SQLi) nem execução no browser da vítima (XSS), mas **execução de código no OS do servidor (RCE)** — controle direto da máquina.

### Os três sinks de injection (a ser explicitado no DIFF e no WALKTHROUGH)

Assim como a trilogia SQLi (01/06/07) é "uma causa raiz, três canais de exfil" e o par XSS (02/08) é "uma causa raiz, dois modelos de entrega", a família de injection como um todo é **"uma causa raiz, sinks diferentes"**. Este átomo introduz o terceiro sink:

| Átomo(s) | Interpretador (sink) | O atacante injeta | Onde executa | Impacto típico |
|---|---|---|---|---|
| `sqli-union-basic` (01) | SQL engine (SQLite) | sintaxe **SQL** (`' UNION SELECT ...`) | no banco, **server-side** | exfiltração de **dado** |
| `xss-reflected` (02) / `xss-stored` (08) | parser **HTML/JS** do browser | **markup/JavaScript** (`<script>...`) | no **browser da vítima** | sequestro de sessão / ação no contexto da vítima |
| `command-injection-basic` (09) | **shell do OS** (`/bin/sh`) | sintaxe de **shell** (`; \| && $(...)`) | no **OS do servidor** | **RCE — controle da máquina** |

A causa é **idêntica** nos três: input não sanitizado **concatenado numa string que um interpretador vai parsear**. O que muda é **qual interpretador** — e, portanto, a sintaxe do payload e a gravidade do impacto. O fix também rima: separar **código de dado** / tirar o interpretador da equação (query parametrizada no SQLi ↔ lista de argumentos sem shell aqui).

### Contraste explícito com os átomos irmãos — é parte da aula

O DIFF e o WALKTHROUGH devem ancorar no contraste com os átomos de injection **já publicados em `main`** (01, 02, 06, 07, 08):

- **vs `sqli-union-basic`:** mesma silhueta de átomo (form em `/`, endpoint GET que devolve o resultado, input na query string, output direto na resposta). O `sqli-union-basic` injeta **sintaxe SQL** num query; aqui injeta-se **sintaxe de shell** numa linha de comando. Mesma causa (concatenação), sinks diferentes, payloads diferentes. O fix rima: query parametrizada (lá) ↔ lista de argumentos sem shell (aqui) — os dois **separam código de dado**.
- **vs `xss-reflected`/`xss-stored`:** XSS executa **no browser da vítima**; command injection executa **no OS do servidor**. O contraste de impacto fecha a escala de severidade da família injection: XSS ataca o cliente, SQLi vaza dado do servidor, command injection **é o servidor**.

O contraste de sink **é** a lição central deste átomo — não um adendo.

---

## Feature simulada

**Ferramenta de diagnóstico de rede (ping).**

Uma utilidade de rede: o usuário digita um host (nome ou IP), a app roda `ping` nesse host e mostra o output do comando. Do ponto de vista do usuário legítimo, é o tipo de ferramenta que existe em incontáveis painéis de admin, status pages e appliances ("esse servidor está no ar? deixa eu dar um ping"). É o "hello world" de command injection — imediatamente reconhecível, e o sink é cristalino: o host digitado vai **direto** para a linha de comando do `ping`.

**Decisão: ping tool, sem persistência.** É o mínimo absoluto que carrega a lição — um form, um campo, um comando, o output de volta. Nenhum banco, nenhum estado. O contraste com os átomos SQLi/XSS (que tinham SQLite) é ele próprio didático: aqui não há "loot no banco"; o loot é o **próprio OS** (`whoami`, `/etc/passwd`, qualquer comando).

**Tipo de átomo:** `[x] com HTML` / `[ ] API-only` (ver Seção 3.3 do CLAUDE.md).

Dois templates, espelhando o `sqli-union-basic`: `index.html` (o form em `GET /`) + `result.html` (o output em `GET /ping`). Burp continua sendo a **trilha principal** e o browser a **trilha secundária opcional** — **diferente do `xss-stored`**, aqui o browser **não é obrigatório**: o output do comando volta **na própria resposta HTTP**, então o aluno vê `root` / `/etc/passwd` direto no Repeater do Burp, sem precisar de um browser executando nada. Este átomo é Burp-primary clássico, igual ao 01/06/07.

---

## Schema de dados

**N/A — átomo stateless.** Não há banco, não há `init_db()`, não há `DB_PATH`. A "ferramenta de ping" não persiste nada; cada request monta e roda um comando e devolve o output. O `app.py` é, portanto, **ainda mais enxuto** que o do `sqli-union-basic` (sem o bloco de `init_db()`/`executescript()`). Isso é deliberado e alinhado com CLAUDE.md §3.6 (só incluir o que serve à falha/fix).

---

## Rotas

Imports necessários: `import os`, `import subprocess`, `from flask import Flask, request, render_template`.

### `GET /`

Serve o formulário. Espelha o `GET /` do `sqli-union-basic` (renderiza `index.html`, sem lógica).

```python
@app.route("/")
def index():
    return render_template("index.html")
```

### `GET /ping` — **a rota vulnerável**

Recebe `host` na query string, monta `ping -c 1 <host>`, roda via shell, devolve o output.

```python
@app.route("/ping")
def ping():
    host = request.args.get("host", "")
    # VULNERABLE: user input concatenated into a shell command string
    cmd = f"ping -c 1 {host}"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        # timeout: operational hygiene (orthogonal to the vuln/fix), same in both versions
        output = "command timed out after 10s"
    return render_template("result.html", host=host, command=cmd, output=output)
```

- **Source:** `request.args.get("host", "")` — GET, query string (igual ao `username` do 01).
- **Sink:** `subprocess.run(cmd, shell=True, ...)` — o `shell=True` faz o Python rodar `/bin/sh -c "<cmd>"`, e o `/bin/sh` parseia os metacaracteres.
- **Output:** `result.stdout + result.stderr` renderizado **escapado** num `<pre>` (ver seção "Renderização do output"). O `command` montado também é ecoado num `<pre>` (espelhando o "Executed query" do 01).
- **Timeout:** o `subprocess.run` leva `timeout=10` num `try/except subprocess.TimeoutExpired` que devolve `"command timed out after 10s"` — **higiene operacional, ortogonal ao bug e ao fix** (ver "O sink", abaixo). Idêntico nas duas versões.

A versão **fixed** troca só o sink (ver "Fix"): `subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=10)`, e o `result.html` da fixed **não** ecoa o `command` (não há mais uma string de shell única — exatamente como a fixed do 01 dropa o echo da query). O `try/except` e o `timeout=10` são **idênticos** nas duas versões — **só o sink muda**. O `app.py` **difere** entre vulnerable e fixed (o bug mora no `app.py`) — **o inverso do par XSS**, onde o `app.py` era idêntico e o bug morava no template.

---

## O sink — mecanismo exato (`subprocess.run(..., shell=True)`) e por que não os outros candidatos

Para o command injection existir, a app precisa entregar a string montada a um **shell**, que então parseia `;`, `|`, `&&`, `$(...)` como sintaxe.

**Mecanismo escolhido: `subprocess.run(cmd, shell=True, capture_output=True, text=True)`.**

**Por que `subprocess.run(shell=True)` e não os outros candidatos:**

- **`subprocess.run(..., shell=True, capture_output=True, text=True)` (escolhido).** É o idioma moderno e legível de Python para "rodar um comando e capturar o output". `capture_output=True` + `text=True` entregam `result.stdout` e `result.stderr` já como strings, prontos pra concatenar e renderizar. E — crucialmente — o **fix** é o análogo mais limpo possível: **mesma função**, trocando a string + `shell=True` por uma **lista de argumentos** (`shell=False` implícito). Vulnerable e fixed ficam a uma linha de distância, com a diferença de segurança cristalina.
- **`os.system(cmd)` (rejeitado).** Também roda via shell (vulnerável do mesmo jeito), mas **não captura o output** — joga direto no stdout do processo, então não teríamos o que renderizar na resposta. Quebraria a variante "output-visível". E o fix não seria o paralelo limpo do `subprocess` com lista.
- **`os.popen(cmd)` (rejeitado).** Idem shell, captura output mas é uma API legada (wrapper fino sobre `subprocess`); menos idiomático em Python 3 moderno, e de novo não dá o par vulnerable/fixed elegante.

**A flag `-c 1` é obrigatória.** O container é Linux; `ping` no Linux, **sem `-c`, roda pra sempre** (envia probes indefinidamente) e **travaria a request**. `-c 1` (uma única probe) faz o `ping` retornar e a request terminar. Travado: `ping -c 1 <host>`.

**`timeout=10` no `subprocess.run` — higiene operacional (ajuste do mantenedor, incorporado).** O átomo convida o aluno a experimentar comandos (é o ponto). Um aluno curioso vai testar `; sleep 30` ("será que travo?") ou um comando que bloqueia em stdin (`; cat` sem argumento). Sem timeout, a request pendura e o aluno acha que quebrou o lab. Com `timeout=10`, o payload abusivo morre em 10s. Implementação escolhida — **opção (b)**, um `try/except subprocess.TimeoutExpired` de 3 linhas que devolve `output = "command timed out after 10s"`:

```python
try:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    output = result.stdout + result.stderr
except subprocess.TimeoutExpired:
    output = "command timed out after 10s"
```

Escolhi (b) sobre (a) (deixar levantar 500) porque o `"command timed out"` é **didático** — mostra que o comando **realmente rodou e foi morto** por tempo, não que a injeção falhou — e 3 linhas não comprometem a clareza do sink (`subprocess.run(...)` continua sendo a linha central, só envolvida por um `try`). **Ponto crítico (cravar no DIFF e no código):** o timeout é **ortogonal** ao bug e ao fix, exatamente como o escape do output. Está **idêntico nas duas versões** (vulnerable e fixed); **a única variável que muda entre elas é o sink**. O timeout **não** é uma defesa contra command injection — um `; whoami` retorna em milissegundos, muito antes dos 10s — é só para o lab não pendurar num comando abusivo.

---

## O binário `ping` e o container — a única saída do padrão do átomo 01

Diferente de todos os átomos anteriores (que rodavam SQL/templates **dentro** do processo Python), este átomo roda um **binário do OS** (`ping`). Duas consequências que exigem sair do `Dockerfile` byte-idêntico dos átomos 01/08:

1. **`python:3.11-slim` NÃO tem `ping`.** A imagem slim é mínima; o binário `ping` vem do pacote `iputils-ping`, que **não** está instalado. Sem ele, o **baseline legítimo** do walkthrough (`host=127.0.0.1` → output normal do ping) quebraria (`/bin/sh: ping: not found`). Então o `Dockerfile` **precisa instalar** `iputils-ping` via apt. Esta é a **única** divergência do Dockerfile de referência.

   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   # iputils-ping: the "ping tool" feature needs the ping binary,
   # which is not present in the slim base image.
   RUN apt-get update \
       && apt-get install -y --no-install-recommends iputils-ping \
       && rm -rf /var/lib/apt/lists/*
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

   O `Dockerfile` de `vulnerable/` e `fixed/` continua **idêntico entre as duas versões** (como no 01/08); só divergiu do átomo de referência pela linha do apt.

2. **`ping` precisa de `CAP_NET_RAW` (ou root).** O container roda como **root** (o `python:3.11-slim` não tem diretiva `USER` — confirmado nos átomos 01/08, `whoami` → `root`), e o Docker concede `NET_RAW` no set de capabilities **padrão**. Logo `ping -c 1 127.0.0.1` deve funcionar sem nenhuma config extra no compose. **Isto é um ponto de validação manual** (CLAUDE.md §11): se no setup do mantenedor o `ping` reclamar (`socket: Operation not permitted`), o fallback é adicionar ao serviço no `docker-compose.yml`:
   ```yaml
       sysctls:
         - net.ipv4.ping_group_range=0 2147483647
   ```
   Manter o compose **sem** o sysctl por padrão (mais limpo); só adicionar se a validação mostrar que precisa. Ver Open Questions.

**O que `whoami` retorna: `root`.** Como o container roda como root, o `; whoami` injetado retorna `root` — didaticamente o **pior caso**, e o mais honesto: mostra que o comando do atacante roda com privilégio total. O walkthrough deve documentar os outputs esperados (para o validador conferir):

- `127.0.0.1; whoami` → `root`
- `127.0.0.1; id` → `uid=0(root) gid=0(root) groups=0(root)`
- `127.0.0.1; cat /etc/passwd` → o `/etc/passwd` do container (Debian slim: `root:x:0:0:root:/root:/bin/bash`, `daemon`, `bin`, `sys`, ... `nobody`). Capturar o conteúdo exato na validação.

**Enquadramento obrigatório no walkthrough (nota clara):** neste lab o comando roda dentro de um **container descartável e isolado** — o `whoami`/`cat` inofensivo aqui é seguro porque o container é efêmero. Mas num alvo **real** isso é **Remote Code Execution (RCE)** no servidor: o `whoami` representa **controle total da máquina**. O aluno precisa entender que o `root` inócuo do lab é, no mundo real, a classe de maior severidade. **Não** adicionar sandboxing/seccomp/drop de capabilities extra — isso ofuscaria o sink (a lição é o **sink de shell**, não contenção de container); o isolamento padrão do Docker É a rede de segurança.

---

## Renderização do output — `<pre>` escapado (um átomo = uma vuln)

O output do comando (`stdout+stderr`) e a linha de comando ecoada vão em `<pre>`, renderizados com o **autoescape padrão do Jinja LIGADO** — **sem `|safe`**. Exatamente como o `sqli-union-basic` renderiza o `<pre>{{ query }}</pre>` (autoescapado, sem `|safe`).

**Por que isso importa — evitar um segundo bug:** o output de um comando controlado pelo atacante pode conter `<`, `>`, `"`, etc. Se renderizássemos sem escape, um payload como `; echo '<script>alert(1)</script>'` faria o output virar HTML executável — **um reflected XSS acidental empilhado por cima do command injection**. Isso violaria "um átomo = uma vulnerabilidade" (CLAUDE.md §2). O autoescape do Jinja (mantido, `<pre>{{ output }}`) garante que o output aparece como **texto literal**, não markup. É o mesmo princípio de escape que o `xss-stored` ensina — aqui aplicado defensivamente para **não** introduzir a falha que aquele átomo estuda.

> **Cravar no `DIFF`/`WALKTHROUGH` e nos comentários do `app.py`:** o escape do output **não é** o fix de command injection (o fix é o sink; ver abaixo). É higiene para manter o átomo com **exatamente um** bug. Vulnerable e fixed **ambas** escapam o output.

---

## HTML

Dois templates, `templates/index.html` (form) e `templates/result.html` (output), espelhando `index.html`/`profile.html` do `sqli-union-basic`. ≤40 linhas cada, CSS ≤5 linhas inline, sem JS, sem framework. Reusar o esqueleto do 01 (banner, footer de Burp, `<style>` sans-serif/720px).

**`index.html`** (idêntico em vulnerable/fixed): banner de aviso no topo, `<h1>Network Ping Tool</h1>`, `<form method="get" action="/ping">` com um campo `host` + submit, uma dica `<p>Try: 127.0.0.1</p>`, footer de Burp. Espelha o form de `sqli-union-basic`, trocando `username`→`host` e `/profile`→`/ping`.

**`result.html`** (esboço da versão vulnerable; a fixed dropa o bloco "Command:"):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ping result</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}pre{background:#f4f4f4;padding:1em;overflow:auto;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Ping result for: {{ host }}</h1>
<p><strong>Executed command:</strong></p>
<pre>{{ command }}</pre>
<p><strong>Output:</strong></p>
<pre>{{ output }}</pre>
<p><a href="/">&larr; Back</a></p>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- Banner de aviso obrigatório (verbatim dos outros átomos: `&#9888; Intentionally vulnerable. Run locally only.`).
- `{{ host }}`, `{{ command }}`, `{{ output }}` **todos autoescapados** (nunca `|safe`).
- O bloco `Executed command:` + `<pre>{{ command }}</pre>` espelha o "Executed query:" do 01 — o aluno **vê** como o input `127.0.0.1; whoami` virou a linha `ping -c 1 127.0.0.1; whoami`. **Removido na fixed** (como o 01 remove o echo da query), porque na fixed não há uma string de shell única a mostrar.
- Footer padrão com a dica de Burp.

---

## Fix

Diff esperado entre `vulnerable/app.py` e `fixed/app.py`, na view `/ping`:

```diff
     host = request.args.get("host", "")
-    # VULNERABLE: user input concatenated into a shell command string
-    cmd = f"ping -c 1 {host}"
     try:
-        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
+        # FIXED: argument list, no shell — host can never be parsed as shell syntax
+        result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=10)
         output = result.stdout + result.stderr
     except subprocess.TimeoutExpired:
         # timeout: operational hygiene (orthogonal to the vuln/fix), same in both versions
         output = "command timed out after 10s"
-    return render_template("result.html", host=host, command=cmd, output=output)
+    return render_template("result.html", host=host, output=output)
```

(E `fixed/templates/result.html` dropa o bloco `Executed command:` / `<pre>{{ command }}</pre>` — mudança incidental, exatamente como a fixed do `sqli-union-basic` dropa o bloco de debug da query.) O `try/except subprocess.TimeoutExpired` e o `timeout=10` aparecem como **contexto inalterado** no diff (idênticos nas duas versões) — reforçando que **a única mudança de segurança é o sink**: string + `shell=True` → lista de argumentos.

**Uma frase de por que resolve:** com a **lista de argumentos** (`shell=False`, implícito), o Python chama `execvp("ping", ["ping","-c","1", host])` **direto no kernel — nenhum `/bin/sh -c` é spawnado** —, então `host` é **sempre um único argumento** de `ping`, nunca parseado como sintaxe de shell; `127.0.0.1; whoami` vira um "hostname" literal que o `ping` tenta resolver via `getaddrinfo` e **falha** (`ping: 127.0.0.1; whoami: Name or service not known`), sem executar segundo comando.

### Notas obrigatórias no DIFF.md

1. **O análogo direto da query parametrizada.** Assim como no `sqli-union-basic` o `?` faz o driver parsear o SQL **primeiro** e tratar o valor como **dado inerte**, aqui a lista de argumentos faz o OS executar **exatamente um programa** (`ping`) com o input como **argumento inerte** — o shell nunca entra na jogada. Os dois fixes são a **mesma ideia**: separar **código de dado**, tirar o interpretador do caminho. Referenciar `sqli-union-basic` explicitamente (publicado em `main`).

2. **Blocklist/escape de metacaracteres é jogo perdido (paralelo ao SQLi).** O `DIFF` do 01 chama escaping/blacklisting de "a losing game". Mesma lição aqui: tentar filtrar `;` não adianta — o atacante usa `|`, `&&`, `$(...)`, `` ` ``, newline. O walkthrough (Step 2) **prova** isso. A raiz não é "esqueceram de bloquear o `;`"; é "o shell está parseando input do atacante como código". A única correção robusta é **remover o shell**.

3. **Validação de input (allowlist) como defense-in-depth — NÃO o fix (paralelo ao HttpOnly do 08).** Uma allowlist tipo `^[a-zA-Z0-9.-]+$` (só caracteres de hostname/IP) **também** barra o payload, mas é **defense-in-depth**, não a correção de raiz: allowlists incompletas viram bypass, e a lição transferível é "separe código de dado", não "liste os bons caracteres". Explicar por que a versão fixed **não** empilha a allowlist: queremos **exatamente uma variável** mudando entre vulnerable e fixed (o sink), pra lição ficar inequívoca — igual ao 08, que não adiciona HttpOnly na fixed. Dar à allowlist um **papel concreto** (como o 08 deu ao HttpOnly): mesmo com o shell fora, um `host` começando com `-` poderia virar **argument injection** (o `ping` interpretaria como flag); a allowlist, ao proibir o `-` inicial, fecha também essa fresta menor. Mas isso é uma camada extra, não o fix — o fix é a lista de argumentos.

4. **O bug mora no `app.py` (inverso do par XSS).** Aqui `vulnerable/app.py` ≠ `fixed/app.py` (o sink mudou). Vale a nota de contraste: no `xss-stored`/`xss-reflected` o `app.py` era **idêntico** e o bug morava no template; aqui é o oposto — o sink perigoso está no código Python, e o template (fora o echo incidental) é o mesmo.

---

## Walkthrough — payloads

Quatro beats: **baseline legítimo** → **confirmar a injeção** → **provar que a causa não é o `;` (é o shell)** → **impacto máximo (RCE / leitura de arquivo arbitrário)**. Escalada didática espelhando o `sqli-union-basic` (confirmar → explorar → extrair impacto máximo).

> **Nota de timeout (incluir uma frase no walkthrough gerado):** o `subprocess` roda com `timeout=10`; um `; sleep 999` ou um `; cat` sem argumento **não pendura o lab** — morre em 10s e o output vira `command timed out after 10s`. Frisar que isso é **higiene operacional, não o fix nem a vuln** (ortogonal, igual ao escape do output): mostra que o comando **rodou e foi morto** por tempo, não que a injeção falhou. Idêntico nas duas versões.

**Estrutura dos blocos por payload (reusar do 01):** para cada payload, mostrar um bloco **Payload (decoded)** (para leitura) e um bloco **Request line** (com os caracteres significativos encodados, colável direto no Repeater), no formato `GET /ping?host=... HTTP/1.1` / `Host: 127.0.0.1:8009`.

### Baseline — a ferramenta funcionando (estabelece o "normal")

Antes de atacar, o uso legítimo, para o aluno ver a feature em ação (igual o 01 mostra a busca por `alice` funcionando).

- **Payload (decoded):** `host=127.0.0.1`
- **Request line:** `GET /ping?host=127.0.0.1 HTTP/1.1`
- **Observação:** output normal do `ping` (`PING 127.0.0.1 ... 1 packets transmitted, 1 received ...`). A ferramenta faz o que promete. O `<pre>` "Executed command" mostra `ping -c 1 127.0.0.1`.

### `### A note on URL encoding` (subseção, espelhando o 01)

Metacaracteres de shell na query string precisam de atenção — **dois casos mordem** (paralelo ao `%20` do 01 e ao `+`→`%2B` do 08):

- **Espaço → `%20`** (obrigatório): um espaço literal na request line quebra o HTTP (`400 Bad Request`), exatamente como no 01. `; whoami` vira `;%20whoami`.
- **`&` → `%26`** (obrigatório para `&&`): um `&` cru na query string **inicia um novo parâmetro** — `?host=127.0.0.1 && id` seria parseado errado e a injeção quebraria. `&&` tem que virar `%26%26`. (Este é o "trap" análogo ao `+`→`%2B` do 08.)
- Demais metacaracteres (`;`, `|`, `$`, `(`, `)`, `` ` ``) funcionam crus no **valor** da query com o Werkzeug moderno (Flask 3 só quebra query em `&`), mas o caminho seguro e o hábito correto é encodar tudo — ou colar o valor decoded no Repeater e apertar **Ctrl+U** (Burp encoda tudo). **Pelo form do browser (trilha secundária), o encoding é automático.**

### Step 1 — Confirm the injection point

O payload mais simples que encadeia um segundo comando e mostra output visível. (Paralelo ao `alice' --` do Step 1 do 01.)

- **Payload (decoded):** `host=127.0.0.1; whoami`
- **Request line:** `GET /ping?host=127.0.0.1;%20whoami HTTP/1.1`
- **Observação:** o output traz o ping **e**, na sequência, `root`. O `;` separou dois comandos; o shell rodou os dois. O `<pre>` "Executed command" mostra `ping -c 1 127.0.0.1; whoami` — o aluno **vê** o input dele virar linha de comando. Prova: o input não é dado, é **código pro shell**.

### Step 2 — It's not the semicolon: the shell is the sink (o passo de contraste — "o que a vuln NÃO é")

Trocar o `;` por outros metacaracteres e ver que **todos** funcionam. Isola a causa real e desmonta o mal-entendido vizinho ("é só bloquear o `;`"). (Análogo ao "negative probe" do Step 2 do 01, adaptado à classe.)

- **Pipe:** `host=127.0.0.1 | id` → `%7C` — output inclui `uid=0(root)...`
- **AND:** `host=127.0.0.1 && id` → **`%26%26`** (atenção ao encoding!) — idem
- **Command substitution:** `host=127.0.0.1$(id)` → `%24%28id%29` — o `$()` executa `id` e o resultado entra na linha do ping (o ping falha ao resolver, mas o `id` já rodou; observar o output/erro)
- **Observação/lição:** o bug **não é** "esqueceram de bloquear o `;`". É que o **shell inteiro** está parseando input do atacante como código — qualquer metacaractere de shell serve. Por isso blocklist é jogo perdido, e por isso o fix tem que **remover o shell**, não filtrar caracteres. (Cravar o contraste: no `sqli-union-basic` a lição era "escaping de aspas é jogo perdido, parametrize"; aqui é "escaping de metacaractere é jogo perdido, tire o shell".)

### Step 3 — Full command execution: arbitrary file read (impacto máximo)

Provar que é execução de comando arbitrário = RCE. (Paralelo ao Step 3 do 01, que exfiltra a tabela `secrets`.)

- **Payload (decoded):** `host=127.0.0.1; cat /etc/passwd`
- **Request line:** `GET /ping?host=127.0.0.1;%20cat%20/etc/passwd HTTP/1.1`
- **Observação:** o output traz o ping seguido do conteúdo de `/etc/passwd` do container. Ler um arquivo arbitrário do sistema é a prova clássica-inofensiva-mas-ilustrativa de que o atacante controla o comando — e, portanto, a máquina.
- **Enquadramento (obrigatório):** aqui roda em container descartável; num alvo real é **RCE** no servidor — a classe de maior severidade. Manter didático e proporcional (nota do padrão do projeto — demonstrativos, não destrutivos; **nada** de `rm -rf`, fork bombs, etc., mesmo em container).

### `### Why this is command injection (and how it compares to SQLi and XSS)` — explicit contrast (fecha o walkthrough)

Parágrafo final amarrando os três sinks (referenciando `sqli-union-basic` e os átomos XSS, todos publicados em `main`). Sugestão de conteúdo:

> No `sqli-union-basic`, o input não sanitizado ia para o **SQL engine**, e o atacante lia **dado** do banco. Nos átomos de XSS, ia para o **parser HTML/JS do browser**, e o código rodava **no browser da vítima**. Aqui ele vai para o **shell do OS**, e o comando roda **na máquina do servidor**: `whoami` retorna `root`, `cat /etc/passwd` devolve o arquivo. Mesma causa raiz dos três — input concatenado numa string que um interpretador parseia — só que o interpretador agora é o shell, e o resultado é **Remote Code Execution**: o pior caso da família. E o fix rima com o do SQLi: assim como a query parametrizada separou SQL de dado, a **lista de argumentos** separa o comando de seu argumento, tirando o shell da jogada por completo.

### `## 4. Exploitation via browser (secondary track, optional)` + `## 5. Why the fix works`

- **§4 (browser, secundária, opcional):** digitar os payloads direto no form do browser e ver o output na `result.html`. O browser encoda a query automaticamente (a armadilha do `%26` só morde quem monta a request crua no Burp). Serve de primeira experiência de baixa fricção — **mas Burp é a principal** (o output volta na resposta, então Burp basta pra tudo; browser é conveniência, não obrigatório).
- **§5 (why the fix works):** rodar os mesmos payloads contra a porta **8109** (fixed) e ver o `ping` **falhar ao resolver** `127.0.0.1; whoami` como hostname (`Name or service not known`), sem executar `whoami`. O input agora é argumento inerte. Explicar o mecanismo (execvp direto, sem shell) + a nota de allowlist como defense-in-depth.

---

## Dependências extras

```
Flask==3.0.0
```

Idêntico aos átomos 01/02/06/07/08. `subprocess` e `os` são stdlib. **Nada** de pip além do Flask.

**Dependência de OS (não-pip), específica deste átomo:** `iputils-ping`, instalado via `apt-get` no `Dockerfile` (ver seção "O binário `ping` e o container"). É o binário que a feature de ping precisa; o `python:3.11-slim` não o traz. Regra CLAUDE.md §3.6 respeitada: só entra porque **serve à demonstração da falha** (a feature É o ping).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Feature | **Ping tool** (diagnóstico de rede), stateless | "Hello world" de command injection; sink cristalino (host → linha de comando). Sem banco: o loot é o próprio OS, não uma tabela. |
| Método HTTP | **GET** com query string (`?host=...`) | Espelha o `sqli-union-basic` (o gêmeo conceitual, também GET), maximizando o paralelo. URL direto em browser e Burp; dá a lição concreta de URL-encoding (`%20`, `%26`). |
| Sink | `subprocess.run(cmd, shell=True, capture_output=True, text=True)` | Idioma moderno; captura stdout+stderr como string pra renderizar (variante output-visível). `os.system`/`os.popen` não dão o par vulnerable/fixed limpo. |
| Flag do ping | `ping -c 1 <host>` (Linux, container Linux) | Sem `-c`, o ping do Linux roda pra sempre e trava a request. `-c 1` = uma probe, request retorna. |
| Timeout no subprocess | **`timeout=10`** em ambas as versões, com `try/except TimeoutExpired` → `"command timed out after 10s"` | Higiene operacional: o átomo convida a experimentar comandos; sem timeout, `; sleep 999` / `; cat` penduram o lab. Ortogonal ao bug/fix (igual ao escape do output); idêntico nas duas versões — só o sink muda. Opção (b): o "timed out" é didático (comando rodou e foi morto, não que a injeção falhou). |
| Fix (principal) | **Lista de argumentos, sem shell:** `subprocess.run(["ping","-c","1",host], ...)` | Correção canônica e robusta; análogo direto da query parametrizada (separar código de dado). Elimina o shell da equação. |
| Fix (defense-in-depth, no DIFF) | Allowlist `^[a-zA-Z0-9.-]+$` mencionada, **não** implementada na fixed | Não é o fix de raiz (allowlist incompleta = bypass). Paralelo ao HttpOnly do 08: uma variável só muda entre vulnerable/fixed. Papel concreto: também barra argument injection (`-` inicial). |
| Renderização do output | `<pre>{{ output }}</pre>` **autoescapado** (sem `\|safe`), em **ambas** as versões | Evita empilhar um reflected XSS acidental sobre o command injection (um átomo = uma vuln). Espelha o `<pre>{{ query }}</pre>` do 01. |
| Echo do comando montado | `<pre>{{ command }}</pre>` na vulnerable; **removido** na fixed | Espelha o "Executed query" do 01: aluno vê input virar linha de comando. Na fixed não há string de shell única (removido, como o 01 remove o debug da query). |
| Nº de templates | **Dois** (`index.html` form + `result.html` output) | Espelha `index.html`/`profile.html` do 01. |
| `app.py` vulnerable × fixed | **Diferem** (o sink mudou) | Inverso do par XSS (lá o app.py era idêntico, bug no template). Aqui o bug mora no `app.py`. |
| Dockerfile | Igual ao 01/08 **+ apt install `iputils-ping`** | Única divergência: `python:3.11-slim` não tem `ping`, e a feature precisa dele. |
| User do container | **root** (sem diretiva `USER`, como 01/08) | `; whoami` → `root`: pior caso, mais honesto (comando do atacante roda com privilégio total). |
| Trilha Burp vs browser | **Burp principal, browser secundário opcional** (browser NÃO obrigatório) | Diferente do `xss-stored`: o output volta na resposta HTTP, então Burp vê tudo. Igual ao 01/06/07. |
| Nº de steps | **Baseline + 3 steps** (confirmar / não-é-o-`;` / RCE) + contraste final | Escalada espelhando o 01. O Step 2 é o passo "o que a vuln NÃO é" (a causa é o shell, não o `;`). |

---

## Open questions — status após sign-off do mantenedor

Spec **aprovada** pra geração. Status de cada item:

**Confirmadas (sign-off do mantenedor):**

1. **Método HTTP: GET.** Confirmado — espelha o gêmeo `sqli-union-basic` e dá a lição de URL-encoding.
2. **Sink: `subprocess.run(shell=True, capture_output=True)`.** Confirmado.
3. **Fix: lista de argumentos (sem shell); allowlist só como defense-in-depth no DIFF, com papel concreto (fecha argument injection via `-` inicial).** Confirmado.
4. **Output em `<pre>` escapado.** Confirmado.
5. **Baseline legítimo antes de atacar; 3 steps; Step 2 = contraste "não é o `;`, é o shell".** Confirmado.
6. **Echo do comando montado (`Executed command:`) na vulnerable, removido na fixed.** Confirmado — **mantém** (mostra a injeção na estrutura, não é redundante com o output).

**Ajustada pelo mantenedor (incorporada nesta revisão):**

9. **Timeout no subprocess — ADICIONADO.** Reconsiderado: o átomo convida a experimentar comandos, e um aluno vai testar `; sleep 30` ou `; cat` (bloqueia em stdin) e achar que travou o lab. `timeout=10` em **ambas** as versões, via **opção (b)** — `try/except subprocess.TimeoutExpired` de 3 linhas → `output = "command timed out after 10s"` (didático: o comando rodou e foi morto por tempo, não que a injeção falhou). **Ortogonal ao bug e ao fix** (igual ao escape do output): idêntico nas duas versões, só o sink muda entre elas. Documentado no comentário do código e numa frase do walkthrough. Incorporado nas seções Rotas, "O sink", Fix (como contexto do diff), Walkthrough, tabela de decisões e Notas.

**Pendentes — validação na geração (não-bloqueantes, CLAUDE.md §11):**

7. **`ping` funciona no Docker do mantenedor?** Espera-se que sim (root + `NET_RAW` default). Se reclamar `Operation not permitted`, aplicar o fallback `sysctls: net.ipv4.ping_group_range=0 2147483647` no compose. Confirmar rodando na geração.
8. **Conteúdo exato de `/etc/passwd` e output de `whoami`/`id`** — capturar na validação (esperado: `root` / passwd padrão do Debian slim) pra o "output esperado" do walkthrough bater com a realidade.

**Bloqueante remanescente:** nenhuma. Spec aprovada; resta só a validação do `ping`/outputs na geração.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **`sqli-union-basic` do shell**. Cada parágrafo do walkthrough deve poder ser lido com o átomo 01 aberto ao lado; a diferença ("mesma silhueta, mas o sink é o shell e o impacto é RCE") deve estar visível. Reusar a forma do 01: GET + query string, form em `/` + endpoint de resultado, echo do input montado num `<pre>` autoescapado, `### A note on URL encoding`, forma do DIFF, esqueleto do WALKTHROUGH/README.
- **Leitura obrigatória antes de gerar (CLAUDE.md §10.5):** `sqli-union-basic` inteiro (gêmeo conceitual; reusar silhueta, echo `<pre>`, nota de encoding, forma do DIFF) e `xss-stored` (formato atualizado de README/WALKTHROUGH/DIFF, compose, Dockerfile, blocos decoded/Burp-ready).
- **Átomo stateless:** sem banco, sem `init_db()`, sem `DB_PATH`. O `app.py` é mais enxuto que o do 01.
- **`app.py` DIFERE entre vulnerable e fixed** (o sink). O `Dockerfile` é idêntico entre as duas versões (mas diverge do 01/08 pela linha do apt `iputils-ping`).
- **Sink no `app.py`:** `subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)` com `cmd = f"ping -c 1 {host}"`. Fix: `subprocess.run(["ping","-c","1",host], capture_output=True, text=True, timeout=10)`. Não usar `os.system`/`os.popen`.
- **Timeout (`timeout=10`) em AMBAS as versões**, num `try/except subprocess.TimeoutExpired` que põe `output = "command timed out after 10s"`. É **higiene operacional, ortogonal ao bug e ao fix** (igual ao escape do output) — evita que `; sleep 999` / `; cat` pendurem o lab. **Não** é defesa contra command injection (um `; whoami` retorna em ms). Comentar no código e numa frase do walkthrough que é ortogonal. **Só o sink muda entre vulnerable e fixed**; o `try/except` e o `timeout` são idênticos.
- **Output SEMPRE escapado** (`<pre>{{ output }}`, autoescape padrão, **sem `|safe`**), em ambas as versões — pra não criar um reflected XSS acidental. Comentar isso no código/DIFF: **não é** o fix de command injection; é higiene de "um bug só".
- **Container roda como root** → `whoami` = `root`. Documentar os outputs esperados no walkthrough (`root`, `uid=0(root)...`, `/etc/passwd`). Enquadrar o RCE: inofensivo no container efêmero, mas é controle da máquina num alvo real. **Não** adicionar hardening (seccomp, drop-caps, USER não-root) — ofuscaria o sink.
- **Dockerfile:** adicionar `RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping && rm -rf /var/lib/apt/lists/*` (a feature precisa do binário `ping`). Manter o resto igual ao 01/08 (base `python:3.11-slim`, `ENV HOST=0.0.0.0`, `CMD ["python","-u","app.py"]`).
- **`docker-compose.yml`:** `127.0.0.1:8009:5000` (vulnerable), `127.0.0.1:8109:5000` (fixed). Reusar o esqueleto de duas services do 01/08. **Sem** o `sysctls` por padrão; só adicionar se a validação mostrar que o `ping` precisa (ver Open Questions #7).
- **Nota de URL encoding no walkthrough:** espaço→`%20` (senão 400), `&`→`%26` (senão split de parâmetro — o trap deste átomo, análogo ao `+`→`%2B` do 08); demais metacaracteres crus funcionam no Werkzeug moderno mas encodar/Ctrl+U é o hábito. Pelo form do browser, encoding automático.
- **Payloads didáticos e proporcionais** (CLAUDE.md §8.4): `whoami`, `id`, `cat /etc/passwd`. **Nunca** `rm -rf`, fork bomb, ou qualquer payload destrutivo — mesmo em container.
- **Cross-atom reference policy:** OK referenciar `sqli-union-basic`, `xss-reflected`, `xss-stored`, `sqli-blind-boolean`, `sqli-blind-time` (todos em `main`). **Proibido** referenciar `path-traversal-basic` (átomo 10, pendente — mesmo sendo "parente próximo" no ROADMAP), `ssti-jinja`, ou qualquer átomo da Fase 2+ ainda não publicado. Ao falar de leitura de arquivo, manter no frame de command injection (comando `cat` injetado), **não** foreshadowar path traversal.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF), padrão v0.1.0. H1 do `README.md` e `README.pt-BR.md` **idêntico**: `# command-injection-basic — OS Command Injection`.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md`, linkando `https://portswigger.net/web-security/os-command-injection` com o texto `OS command injection` preservado em inglês também no PT.
- **CHANGELOG.md:** ao gerar o átomo (**não agora**), adicionar em `[Unreleased] / Added`: `Added atom 09: \`command-injection-basic\` — OS Command Injection (A03 Injection).` (mesmo padrão das linhas dos átomos 06/07/08).
- **ROADMAP.md:** marcar o átomo 09 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente** (CLAUDE.md §11): baseline (`host=127.0.0.1` → output de ping real); Step 1 (`; whoami` → `root`); Step 2 (`|`, `&&`, `$()` todos executam); Step 3 (`; cat /etc/passwd` → passwd do container); e na **fixed** (8109) os mesmos payloads **falham** (ping não resolve o "hostname", nenhum comando extra roda). Confirmar antes que o `ping` de fato pinga no Docker do mantenedor.
- Se houver dúvida sobre o nome exato de uma aba do Burp na versão atual, **perguntar antes de inventar** (CLAUDE.md). Este átomo usa pouco do Burp (só Repeater no GET) — sem Intruder.
