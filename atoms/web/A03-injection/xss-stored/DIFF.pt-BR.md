# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/templates/index.html` e `fixed/templates/index.html`:

```diff
-<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
+<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body }}</li>
```

Os arquivos `app.py` são idênticos nas duas versões — o bug vive inteiramente no template, a mesma forma do `xss-reflected`.

## O que mudou

O filter `|safe` foi removido da expressão `{{ comment.body }}`. No Jinja, `|safe` marca um valor como HTML já confiável e diz pro renderer pular o autoescape. Sem ele, o autoescape default do Jinja entra em ação e encoda `<`, `>`, `&`, `'` e `"` nas respectivas entidades HTML (`&lt;`, `&gt;`, `&amp;`, `&#39;`, `&#34;`) antes do valor ser escrito na response. O `author` e o `created_at` ao lado já eram escapados (sem `|safe`) e estão inalterados — o body era o único sink, então o fix é o único `|safe` do arquivo.

## Por que isso resolve

Um comentário é armazenado na íntegra — o `INSERT` parametrizado nunca foi o problema — e o perigo está puramente em como ele é renderizado de volta. Com autoescape ligado, o `<script>alert(document.domain)</script>` armazenado chega no browser de todo visitante como a string literal `&lt;script&gt;alert(document.domain)&lt;/script&gt;`: visível pro leitor como texto, inerte pro parser do HTML como markup. O payload de exfil do cookie do Passo 3 também cai como texto — nenhum `fetch` roda, o listener fica silencioso. Payloads que tentam abrir uma tag, fechar uma, sair de um atributo ou conectar um event handler perdem a força ainda no template, independentemente dos caracteres exatos que usem.

## Mesmo fix do `xss-reflected`, reformulado

Esta é a mesma mudança de uma linha do [`xss-reflected`](../xss-reflected/DIFF.pt-BR.md): uma expressão marcada com `|safe` perde o filter e cai no autoescape do Jinja. Mesmo sink, mesma defesa, mesma classe. O reflexo de auditoria é idêntico: `grep -rn '|safe' templates/` (mais `Markup(` e `{% autoescape false %}`) revela todo ponto onde o escape foi desligado, e cada hit é um candidato a sink de XSS. Se você internalizou o fix do reflected, já conhece este.

## Mesmo fix, blast radius maior

É tentador catalogar stored XSS como "reflected, só que pior". Mecanicamente é o *mesmo* bug — output sem escape — com uma *entrega diferente*, e é exatamente por isso que o fix é o mesmo: a root cause é idêntica. Mas a entrega é o que torna o stored mais perigoso, e o fix de uma linha remove essa mesma root cause num cenário muito maior:

- **Reflected** precisa que a vítima clique num link preparado pelo atacante carregando o payload na URL — isso é engenharia social, e atinge uma vítima por clique.
- **Stored** precisa que a vítima só faça uma coisa: visitar uma página em que ela já confia. O payload é persistido server-side e re-servido pra *todo* visitante, *toda* vez, até alguém apagar — sem link, sem isca, sem o atacante presente.

A mesma linha de código fecha os dois. A lição rima com o "uma root cause, um fix, N exploits" da trilogia SQLi: aqui é uma root cause (output sem escape), um fix (autoescape), dois modelos de entrega (reflected e stored).

## Uma nota sobre HttpOnly — defense-in-depth, não o fix

A app seta o cookie de session sem o flag `HttpOnly`, nas *duas* versões. Você poderia esperar que a app fixed o adicionasse — e ela deliberadamente não adiciona. Dois motivos:

- **Não é o fix.** Marcar o cookie como `HttpOnly` impediria o `document.cookie` de lê-lo, o que derrotaria o payload *específico* de roubo de cookie do Passo 3 mesmo que o XSS continuasse presente. Mas o XSS ainda estaria lá: o atacante poderia desfigurar a página, fazer requests autenticadas como a vítima, capturar teclas, ou ler o DOM. `HttpOnly` encolhe o blast radius de um payload; não fecha o buraco. O buraco é fechado escapando o output.
- **Uma variável por vez.** Manter exatamente uma diferença entre `vulnerable/` e `fixed/` (o `|safe`) deixa inequívoco qual mudança fecha o XSS. Adicionar `HttpOnly` na versão fixed também borraria isso.

`HttpOnly` ainda vale a pena em aplicações reais — uma segunda camada valiosa que limita o estrago se um XSS escapar. Ele só pertence à coluna "defense-in-depth", ao lado de uma Content-Security-Policy, não à coluna "este é o fix". O fix é, e continua sendo, escapar dado não-confiável na saída.
