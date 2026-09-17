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
-    row = conn.execute(query).fetchone()
+    row = conn.execute(
+        "SELECT username FROM users WHERE username = ? AND password = ?",
+        (username, password),
+    ).fetchone()
     conn.close()
```

Os arquivos em `templates/` são idênticos nas duas versões — o bug mora inteiro em `app.py`. As duas strings de response (`Welcome, <user>!` e `Invalid credentials.`) ficam preservadas verbatim na versão fixed, de propósito; veja a nota no fim deste arquivo.

## O que mudou

A concatenação via f-string foi trocada por uma parameterized query: o statement mantém dois placeholders literais `?`, e `username` e `password` são passados separadamente como tupla. O código vulnerable precisava construir uma string de texto SQL a partir do input cru; o código fixed nunca faz isso — entrega o texto SQL e os valores pro driver como dois argumentos separados.

## Por que isso resolve

Quando o driver do SQLite vê um statement com placeholders `?`, ele manda o texto SQL e os valores dos parâmetros como argumentos *separados* pra engine. A engine faz o parse da SQL primeiro — sem nenhum valor de parâmetro — e só depois liga cada input como valor literal dentro do statement já parseado. Não importa quais caracteres cada input contenha (`'`, `--`, `OR`, `SELECT`, parênteses, newlines, etc.), eles ficam dentro dos seus respectivos slots de string literal e nunca são reinterpretados como sintaxe SQL.

A versão vulnerable tem o modelo oposto: o input já é parte do texto SQL quando a engine vê, então a engine *tem* que parsear isso como código. Escapar ou blacklistar caracteres é jogo perdido — o único fix é nunca splicar input do usuário direto no texto SQL.

## Uma nota sobre o oracle

Um segundo "fix" de aparência natural seria fazer a response ser idêntica em sucesso e em falha — renderizar `Login attempt processed.` nos dois casos, eliminar a assimetria, e o atacante fica sem oracle pra apoiar. Isso é workaround, não mitigação. Esconde o sintoma e deixa a injection intacta: qualquer outra diferença observável (response time, side effect downstream, linha de log, comportamento second-order) reintroduziria o oracle por outra porta.

**Blind SQLi não se mitiga achatando as duas responses — isso é workaround frágil. A mitigação é remover a injection. Uma vez que o input está parameterized, o oracle deixa de ser algo que o atacante consegue controlar.**

Por isso o `result.html` fixed deste átomo mantém `Welcome, <user>!` e `Invalid credentials.` verbatim. Responses diferentes pra outcomes diferentes é comportamento normal de login. O que muda entre vulnerable e fixed não é se o oracle existe — é se um atacante consegue injetar uma condição que controla pra qual lado ele aponta.

## Contraste com `sqli-union-basic`

O diff acima parece estruturalmente idêntico ao do [`sqli-union-basic`](../sqli-union-basic/DIFF.pt-BR.md): uma única string SQL concatenada vira um statement parameterized, e o bug fecha. Dois átomos, duas formas de exfil (vazamento via `UNION` vs. inferência por boolean oracle), um fix. Essa é a lição que vale levar deste par: a variedade em SQL injection mora no *canal* por onde o atacante exfiltra, não na causa raiz. Parameterized queries fecham todo canal de uma vez porque removem a pré-condição (input do usuário virando sintaxe SQL) da qual todos eles dependem.
