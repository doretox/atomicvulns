# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é como o `name` entra no render do `GET /greet` (comentários abreviados):

```diff
 @app.route("/greet")
 def greet():
     name = request.args.get("name", "world")
-    # VULNERABLE: the name is concatenated INTO the template source with an f-string ...
+    # FIXED: the name is passed as DATA via the name= variable, never concatenated in ...
     return render_template_string(
         "<!doctype html><title>Greeting</title>"
         "<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>"
-        f"<h1>Hello, {name}!</h1>"                        # name is IN the template source -> SSTI
-        '<p><a href="/">&larr; Back</a></p>'
+        "<h1>Hello, {{ name }}!</h1>"                     # {{ name }} placeholder filled from data
+        '<p><a href="/">&larr; Back</a></p>',
+        name=name,                                        # name passed as DATA, never sewn in
     )
```

Todo o resto é byte-a-byte idêntico entre as duas versões: os imports, a linha de config da `SECRET_KEY`, a view `GET /`, o esqueleto estático da saudação (doctype, banner, back link), o `__main__`, o `Dockerfile`, o `requirements.txt`, e o `templates/index.html`. O bug vive inteiramente naquela única chamada de render.

## O que mudou

O `render_template_string` é chamado nas duas versões — a função é a mesma. A diferença é o argumento. A versão vulnerable monta o `<h1>` com uma **f-string** (`f"<h1>Hello, {name}!</h1>"`), então o Python cola o `name` no *source* do template antes de o Jinja2 compilar. A versão fixed usa um **placeholder** (`"<h1>Hello, {{ name }}!</h1>"`) e passa o valor separadamente (`name=name`), então o `name` chega ao Jinja2 como *dado*, não como parte do texto do template. É um fix *logic-different* isolado numa linha — a menor expressão possível de "onde o input entra é o bug inteiro".

## Por que isso resolve

A classe é: o input do atacante vira parte do source do template, então o motor compila e avalia qualquer expressão `{{ ... }}` que o atacante escreva. `{{7*7}}` avalia pra `49`; `{{config}}` renderiza o objeto de config do Flask, que inclui a `SECRET_KEY`. Quando o name é passado como dado, o Jinja2 o substitui no slot `{{ name }}` como valor literal — HTML-escapando e nunca re-parseando como código de template. Então `{{7*7}}` volta como o texto literal `{{7*7}}`, e `{{config}}` nunca lê a config. O `Ada` benigno renderiza idêntico dos dois jeitos; só a avaliação sumiu.

## A causa é *onde o input entra*, não "usar Jinja2"

Todo Flask renderiza templates Jinja2 — isso não é o bug. O bug é que a versão vulnerable coloca input não-confiável no *source* do template (como código) em vez de passá-lo como dado. A prova de isolamento é direta: mande `name=Ada` pras duas apps e as duas retornam exatamente `Hello, Ada!` — a lógica da saudação é idêntica. Só quando o name carrega uma expressão `{{ ... }}` é que elas divergem: a vulnerable avalia, a fixed devolve literal. Nada na lógica da rota difere; a diferença inteira é aquela única chamada de render.

## Input como código vs. input como dado

As duas versões chamam a **mesma função**, então este átomo não é "`render_template_string` é perigosa, use outra coisa". O `render_template_string` é seguro quando o template é uma string fixa e o valor do usuário é passado como keyword argument — que é exatamente a versão fixed. O movimento perigoso é *compor o template a partir do input*: uma f-string (ou `"..." + name`, ou `.format(name)`) faz o input virar parte do source, e o motor então o trata como código. Manter o input do usuário fora do texto do template — passá-lo como dado por um `{{ placeholder }}` — é a regra durável. Escapar ou blocklistar `{{`/`}}` no input é o jogo perdido que a SQL injection já ensinou: filtros são burlados. O único fix é estrutural: nunca splicar input do usuário no source do template.

## Uma sandbox não é o fix

O Jinja2 traz um `SandboxedEnvironment` que tenta *conter* o que uma expressão renderizada pode alcançar (bloqueando acesso a alguns atributos e builtins). Ele aparece como um jeito de "tornar SSTI seguro", mas é uma defesa mais fraca e historicamente furada — escapes de sandbox são recorrentes, e endurecer uma é um alvo móvel. Este átomo deliberadamente não o usa: o fix real é não injetar de início (input como dado), não deixar a injeção acontecer e tentar cercá-la. O `SandboxedEnvironment` é citado aqui, não aplicado.

## O impacto é disclosure; RCE é outro bug

Este átomo para no segundo degrau da escada de SSTI: `{{7*7}}` confirma a avaliação, `{{config}}` revela a `SECRET_KEY`. Essa chave assina os cookies de sessão do Flask, então vazá-la deixa o atacante forjar sessões — disclosure com um caminho pra account takeover, não remote code execution. SSTI como *classe* pode escalar de avaliar uma expressão pra executar comando pela hierarquia de objetos do Python, mas isso é um finding separado e este átomo não o constrói. A `SECRET_KEY` aqui (`dev-secret-CHANGEME-not-a-real-secret`) é um placeholder de lab obviamente falso, setado idêntico nas duas apps — então a app fixed não vazá-la é atribuível ao input ser dado (nunca avaliado), não à chave estar ausente.

## Costurar o input no source também reflete HTML cru

Como a versão vulnerable faz o name virar parte do *texto* do template, um name como `<b>x</b>` é emitido como markup cru (renderiza em negrito) — isso é reflected cross-site scripting (XSS), uma classe diferente da avaliação de template que este átomo ensina (o `xss-reflected` cobre reflected XSS diretamente). As duas compartilham uma causa-raiz — input costurado no source — então o fix fecha as duas de uma vez: passar o name como dado faz o Jinja2 autoescapá-lo (`<b>` vira `&lt;b&gt;`) *e* nunca avaliá-lo. A lição deste átomo é a avaliação (SSTI); a reflexão de HTML cru é notada aqui, não perseguida.
