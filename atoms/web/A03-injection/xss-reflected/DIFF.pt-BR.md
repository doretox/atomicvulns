# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/templates/search.html` e `fixed/templates/search.html`:

```diff
-<h1>Results for: {{ q|safe }}</h1>
+<h1>Results for: {{ q }}</h1>
```

Os arquivos `app.py` são idênticos nas duas versões — o bug vive inteiramente no template.

## O que mudou

O filter `|safe` foi removido da expressão `{{ q }}`. No Jinja, `|safe` marca um valor como HTML já confiável e diz pro renderer pular o autoescape. Sem ele, o autoescape default do Jinja entra em ação e encoda `<`, `>`, `&`, `'` e `"` nas respectivas entidades HTML (`&lt;`, `&gt;`, `&amp;`, `&#39;`, `&#34;`) antes do valor ser escrito na response.

## Por que isso resolve

Com autoescape ligado e o valor passando por uma expressão `{{ q }}` normal, todo caractere que poderia *mexer no parse do HTML* vira entidade. O `<script>alert(1)</script>` do atacante chega no browser como a string literal `&lt;script&gt;alert(1)&lt;/script&gt;` — visível pro usuário como texto, invisível pro parser do HTML como markup. Payloads que tentam abrir uma tag nova, fechar uma existente, sair de um atributo ou invocar um event handler perdem a força ainda na camada do template, independentemente dos caracteres exatos usados.

## Contraste com `sqli-union-basic`

No `sqli-union-basic` o sink fica em `app.py`: a linha vulnerable é a f-string que monta a SQL, e ler só a view é suficiente pra pegar o bug. No `xss-reflected` a source continua em `app.py` (na chamada `request.args.get("q", ...)`), mas o sink está em `templates/search.html` (a expressão marcada com `|safe`). O caminho source→sink cruza arquivos, que é a forma normal em app web: qualquer source-review séria num projeto Flask tem que ler templates, não só view functions. Uma primeira passada barata e de alto sinal é `grep -rn '|safe' templates/` (mais `Markup(`, mais `autoescape=false`) — todo hit é um candidato a sink de XSS.
