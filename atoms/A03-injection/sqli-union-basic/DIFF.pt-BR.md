# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py` para a view `/profile`:

```diff
 @app.route("/profile")
 def profile():
     username = request.args.get("username", "")
-    # VULNERABLE: user input concatenated into SQL string
-    query = f"SELECT username, bio, joined_at FROM users WHERE username = '{username}'"
     conn = sqlite3.connect(DB_PATH)
-    rows = conn.execute(query).fetchall()
+    rows = conn.execute(
+        "SELECT username, bio, joined_at FROM users WHERE username = ?", (username,)
+    ).fetchall()
     conn.close()
-    return render_template("profile.html", rows=rows, query=query, username=username)
+    return render_template("profile.html", rows=rows, username=username)
```

O template `profile.html` também perde o bloco de debug "Executed query" na versão fixed (a variável `query` deixa de ser passada pro template).

## O que mudou

A concatenação via f-string foi trocada por uma parameterized query: o statement mantém o placeholder literal `?` e o valor de `username` é passado separadamente como uma tupla de um elemento. O bloco de debug vulnerable — que ecoava a SQL executada de volta na página — também foi removido, porque não tem motivo pra existir na versão fixed (e nada de interessante vazaria por ele, já que a SQL não contém mais o input).

## Por que isso resolve

Quando o driver do SQLite vê um statement com placeholder `?`, ele manda o texto SQL e os valores dos parâmetros como argumentos *separados* pra engine. A engine faz o parse da SQL primeiro — sem o valor do parâmetro — e só depois liga `username` como valor literal no statement já parseado. Não importa quais caracteres o input contenha (`'`, `--`, `UNION`, `;`, newlines, etc.), eles ficam dentro do slot de string literal e nunca são reinterpretados como sintaxe SQL.

A versão vulnerable tem o modelo oposto: o input já é parte do texto SQL quando a engine vê, então a engine *tem* que parsear isso como código. Escapar ou blacklistar caracteres é jogo perdido — o único fix é nunca splicar input do usuário direto no texto SQL.
