# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py` para a view `/login`:

```diff
 @app.route("/login", methods=["POST"])
 def login():
     username = request.form.get("username", "")
     password = request.form.get("password", "")
-    # VULNERABLE: user input concatenated into SQL string
-    query = (
-        f"SELECT username FROM users "
-        f"WHERE username = '{username}' AND password = '{password}'"
-    )
     conn = sqlite3.connect(DB_PATH)
-    conn.execute(query).fetchone()  # result intentionally ignored — response is uniform
+    conn.execute(
+        "SELECT username FROM users WHERE username = ? AND password = ?",
+        (username, password),
+    ).fetchone()  # result intentionally ignored — response is uniform
     conn.close()
     return render_template("result.html")
```

Os arquivos em `templates/` são idênticos nas duas versões — o bug mora inteiro em `app.py`. A resposta uniforme `Login attempt processed.` é preservada verbatim na versão fixed, de propósito; veja a nota no fim.

## O que mudou

A concatenação via f-string foi trocada por uma parameterized query: o statement mantém dois placeholders literais `?`, e `username` e `password` são passados separadamente como tupla. O código vulnerable precisava construir uma string de texto SQL a partir do input cru; o código fixed nunca faz isso. Note que o `.fetchone()` e o `render_template("result.html")` uniforme não mudam — a resposta já era idêntica em todo outcome, e continua assim.

## Por que isso resolve

Quando o driver do SQLite vê um statement com placeholders `?`, ele faz o parse do texto SQL primeiro — sem nenhum valor de parâmetro — e só depois liga cada input como valor literal dentro do statement já parseado. O payload de timing inteiro — a aspa de fechamento, o `CASE`, o recursive CTE, o cross join, o comentário `--` — chega como o *value* de `username`. Ele é armazenado, comparado com a coluna `username`, não casa nada, e nunca é parseado como SQL. Nada do que o atacante manda vira trabalho que a engine executa, então não sobra nenhum delay controlável pra medir.

Rode qualquer payload do walkthrough contra a app fixed na porta 8107: todos retornam `Login attempt processed.` instantaneamente, inclusive o probe incondicional do Step 1 que travava por segundos contra a versão vulnerable. Escapar ou blacklistar caracteres é jogo perdido — o único fix é nunca splicar input do usuário direto no texto SQL.

## Uma nota sobre a resposta uniforme

É tentador ler a mensagem achatada `Login attempt processed.` como parte do fix. Ela não é — e essa distinção é todo o ponto deste átomo.

Achatar a resposta foi uma medida **anti-enumeration** legítima: com uma mensagem neutra só, um atacante não consegue distinguir "usuário válido, senha errada" de "usuário não existe". É boa prática, e de fato removeu o boolean oracle do qual o [`sqli-blind-boolean`](../sqli-blind-boolean/) dependia. Mas nunca tocou na injeção. O `DIFF.pt-BR.md` daquele átomo disse isso com todas as letras — que achatar as duas respostas é "workaround, não mitigação", porque "qualquer outra diferença observável (**response time**, side effect downstream, linha de log, comportamento second-order) reintroduziria o oracle por outra porta". Este átomo *é* essa porta. A app vulnerable aqui é exatamente "e se um dev tivesse aplicado aquele workaround tentador mas nunca parametrizado a query?" — e a resposta é que o timing reabre o oráculo.

Então a mensagem uniforme permanece na versão fixed, exatamente como na vulnerable. Ela nunca foi o bug; a injeção era. O paralelo com o `sqli-blind-boolean` é exato: lá, o fix manteve as duas mensagens diferentes e o atacante simplesmente perdeu o controle de qual aparecia; aqui, o fix mantém a mensagem uniforme única e o atacante perde o canal de timing. O que muda entre vulnerable e fixed nunca é se um oráculo pode existir — é se um atacante consegue injetar algo que o controle.

## A trilogia — uma root cause, um fix, três exploits

Este é o terceiro átomo cujo fix é essa mesma mudança de duas linhas. O diff é estruturalmente idêntico aos do [`sqli-union-basic`](../sqli-union-basic/DIFF.pt-BR.md) e do [`sqli-blind-boolean`](../sqli-blind-boolean/DIFF.pt-BR.md): uma string SQL concatenada vira um statement parameterized, e o bug fecha.

Nos três, a técnica de exploração mudou completamente conforme o que o atacante conseguia observar — dado direto no body (`UNION`), um sinal de um bit no body (boolean oracle), depois latency pura (tempo). A vulnerabilidade e sua correção não mudaram nada. Parameterized queries fecham cada um desses canais de uma vez, porque removem a única pré-condição da qual os três dependem: input do usuário virando sintaxe SQL. Uma root cause, um fix, três exploits.
