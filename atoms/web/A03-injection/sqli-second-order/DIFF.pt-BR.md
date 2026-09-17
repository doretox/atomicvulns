# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` são byte-idênticos exceto o `UPDATE` na view do `POST /change-password` — a única mudança do átomo:

```diff
     conn = db()
     # The logged-in user's username is READ BACK from the DB (parameterized read).
     uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
-    # VULNERABLE: the username re-read from the DB is concatenated straight into the
-    # UPDATE. It was STORED safely (parameterized) at registration, so it was never
-    # treated as untrusted here -- but a value read back from the DB is untrusted
-    # input again. Note `new_password` (fresh input) IS parameterized; only the
-    # re-read value is spliced in -- so a payload username rewrites WHICH row this hits.
-    query = f"UPDATE users SET password = ? WHERE username = '{uname}'"
-    conn.execute(query, (new_password,))
+    # FIXED: the username re-read from the DB is bound as a parameter, exactly like
+    # every other query in this app. A value read back from the DB is untrusted input
+    # again -- so it goes through a placeholder, never into SQL text. The payload is
+    # matched as a literal value; the UPDATE hits only the caller's own row.
+    conn.execute(
+        "UPDATE users SET password = ? WHERE username = ?", (new_password, uname)
+    )
```

## O que mudou

O username relido deixa de ser concatenado no texto SQL e vira um parâmetro passado ao driver. Olhe os dois valores naquele único `UPDATE`: o `new_password` — input fresco desta request — **já** era um placeholder `?` nos dois lados. Só o `uname` — o valor relido do banco — se move, de uma f-string colada (`WHERE username = '{uname}'`) para um placeholder (`WHERE username = ?`). Todo o resto do app é idêntico entre as duas versões: cadastro, login, o `SELECT` que relê, o schema e o seed, a sessão — tudo era, e continua, parametrizado.

## Por que isso corrige o bug

Com um placeholder, o driver do SQLite parseia o `UPDATE` **primeiro**, sem o valor, e só então passa o `uname` como um valor de dado literal no statement já parseado. Os metacaracteres em `admin'--` — a `'` e o `--` — ficam dentro do slot de string literal; eles não podem mais fechar a aspa e comentar o resto. O `WHERE` casa a linha cujo username é *exatamente* a string `admin'--` (a própria linha do atacante), então o change-password faz o que devia: troca a senha do próprio chamador e de mais ninguém. Na versão vulnerable o valor já estava dentro do texto SQL quando o motor o viu, então o motor teve que parsear `'--` como sintaxe e o `WHERE` colapsou para `username = 'admin'`.

## A causa é a segunda query, não o cadastro

O bug **não** é que o cadastro fosse inseguro — ele não é. O `INSERT` é parametrizado, e um username-payload é gravado como texto inerte; atacar o `/register` diretamente não faz nada. A causa é que a **segunda** query concatena um valor relido do banco. Parametrizar essa query neutraliza porque o valor relido vira dado literal, nunca sintaxe — então o `WHERE` casa exatamente a linha pretendida e não há o que reestruturar. O mental model a guardar: **toda leitura do banco é input não-confiável de novo**. Um valor não fica seguro por ter passado pelas suas próprias tabelas; ele entrou como input do atacante e recruza o trust boundary toda vez que você o lê.

## "Eu já parametrizei o cadastro" / "é só sanitizar o username" não é o fix

Dois reflexos levam pro caminho errado, e vale nomear os dois:

- *"Parametrizei o cadastro, então tô seguro."* Parametrizar a **entrada** protege a query da entrada. Não faz nada por uma query **posterior** que concatena o valor no ponto de uso — a proteção não viaja com o dado.
- *"É só sanitizar/validar o username no cadastro — proibir aspas e `--`."* Isso é uma blocklist no lugar errado. Ela persegue a *forma* do payload (encodings alternativos, caracteres que você não listou, outros caminhos que escrevem na tabela), e deixa a query que concatena intocada. É também frágil contra usernames que legitimamente contêm símbolos.

O fix é tratar o valor relido como não-confiável **no ponto de uso** e passá-lo como parâmetro. Aí não importa quais caracteres ele contém, porque nenhum deles é jamais parseado como SQL.

## Mesma classe do first-order SQL injection — o que muda é o timing

Esta é a mesma classe de vulnerabilidade, o mesmo motor e o mesmo fix do first-order SQL injection ([`sqli-union-basic`](../sqli-union-basic/)): input não-confiável concatenado numa query, rodado pelo mesmo parser do SQLite, corrigido por uma query parametrizada. O que difere é **quando** o input chega ao parser — e essa é a razão inteira de isto ser um átomo separado.

| | First-order SQL injection (`sqli-union-basic`) | Second-order SQL injection (este átomo) |
|---|---|---|
| Ordem | Primeira (in-band) | Segunda (stored) |
| Onde o payload entra | Concatenado na query da própria request | Guardado por um caminho **parametrizado** (o cadastro), como valor literal |
| Quando dispara | Na mesma request | Numa request **posterior e diferente** — o segundo fluxo relê o valor e o concatena |
| Por que passa despercebido | Não passa — o payload age no fluxo que você está testando | O ponto de entrada testa como seguro (o cadastro é parametrizado; um probe ingênuo ali não faz nada) — a bomba dorme no banco |
| Motor | Parser SQL do SQLite | O **mesmo** parser SQL do SQLite |
| O fix | Parametrizar a query | Parametrizar a query **do segundo uso também** |

A lição do `sqli-union-basic` — *nunca concatene input não-confiável numa query* — estava certa mas incompleta. Ela tem que incluir *e todo valor relido do banco é input não-confiável de novo*. Aqui, uma query num segundo fluxo esqueceu disso, mesmo que toda outra query no mesmo app parametrize corretamente.
