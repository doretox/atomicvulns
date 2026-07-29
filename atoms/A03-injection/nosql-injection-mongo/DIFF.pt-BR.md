# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em exatamente um lugar — a rota `login` — e a mudança é um único guard de tipo. O `GET /` (o banner de aviso), os imports, a conexão com o MongoDB, o `Dockerfile` e o `requirements.txt` são idênticos entre as duas versões, assim como a imagem `mongo/` compartilhada e o seed dela. (Este átomo é API-only — não há templates.)

## O fix — forçar o tipo

```diff
 @app.route("/login", methods=["POST"])
 def login():
     body = request.get_json(silent=True) or {}
     username = body.get("username")
     password = body.get("password")
-    # VULNERABLE: username/password go straight into the query filter. A MongoDB
-    # query is a DOCUMENT, not a string. If password arrives as an object like
-    # {"$ne": null} instead of a string, it becomes a Mongo OPERATOR ("not equal"),
-    # so the filter matches any user with a password and the login succeeds without
-    # it. The input didn't inject syntax into a string -- it changed the value's type.
+    # FIXED: force the type -- username and password must be strings. An object
+    # carrying an operator (e.g. {"$ne": null}) is rejected before it can reach the
+    # query filter, so it can never become query structure.
+    if not isinstance(username, str) or not isinstance(password, str):
+        return jsonify({"error": "username and password must be strings"}), 400
     user = users.find_one({"username": username, "password": password})
     if user:
         return jsonify({"authenticated": True, "user": user["username"]})
     return jsonify({"authenticated": False}), 401
```

A view fixed recusa qualquer `username` ou `password` que não seja uma string. Um objeto — a única coisa que pode carregar um operador do Mongo — é rejeitado com `400` antes da query rodar, então ele nunca pode virar estrutura da query. Esse único guard fecha a injeção: a classe é "input não-confiável alcança um filtro de query como operador", e forçar o valor a ser um escalar é exatamente a negação disso.

O fix **rejeita** em vez de coagir. `str(password)` também pararia o operador — o objeto viraria a string inofensiva `"{'$ne': None}"` — mas aceitaria silenciosamente uma request malformada e mascararia a intenção do atacante. Rejeitar diz "este campo tem que ser uma string" e para ali; é o fix honesto.

## Por que isto corrige o bug

Uma query do MongoDB é um documento, e o `pymongo` manda pro servidor, como esse documento, qualquer `dict` que você entregar. O app vulnerable monta o filtro a partir do input cru, então um atacante que manda um objeto em vez de uma string faz esse objeto ser colocado na query *como operador*. O app fixed garante que os dois valores são escalares antes de o filtro ser montado, então o filtro só pode ser `{"username": "<uma string>", "password": "<uma string>"}` — dois matches de igualdade literal, sem espaço pra um operador. O caso benigno fica inalterado: uma credencial real em string faz o round-trip exatamente como antes.

## Parametrizar ou escapar não é o fix

Um leitor experiente já tem um fix na ponta da língua: "é injection — parametriza a query, ou escapa o input, como você faria pro SQL." Vale ser preciso sobre por que isso erra aqui.

Parametrizar é o que fecha o SQL injection: o app SQLi vulnerable costura o input numa *string* de texto SQL (`f"... WHERE username = '{username}'"`), e um parâmetro bindado (`"... = ?", (username,)`) mantém o comando e o dado separados, então nenhum caractere do input pode virar sintaxe SQL. Mas aqui não há string de texto de query pra costurar. O `pymongo` nunca concatena — ele passa o seu `dict` pro servidor *como documento*, que já é o equivalente moral de uma query parametrizada: o dado é estruturalmente separado de qualquer comando. E ainda assim é vulnerável, porque a injeção nunca foi sobre sintaxe dentro de uma string. É sobre **tipo**: o atacante trocou um escalar por um objeto, e o driver encaminhou esse objeto fielmente — operador e tudo. Escapar não tem em que morder (não há metacaractere numa string; o valor *é* um objeto), e a parametrização que te salva do SQLi não tem análogo que pegue um valor mudando de tipo. O fix tem que ser um passo antes: garantir que o valor é um escalar. (O mesmo movimento das notas "named, not applied" do `ssti-jinja` e do `deserialization-pickle`: nomeie o controle que o leitor buscaria, e mostre por que ele não é o fix aqui.)

## Blocklist de chaves `$` também não é o fix

O próximo instinto é manter o objeto mas limpá-lo: "é só tirar qualquer chave que comece com `$`." Isso é uma blocklist, e blocklists perseguem a *forma* do ataque em vez da causa — operadores se escondem em objetos aninhados, arrays e chaves com ponto; existem operadores que a sua lista não nomeia; encodings variam. Você fica sempre um bypass atrás. A raiz é uma **whitelist de tipo**, não uma blocklist de chave: exija que o valor seja uma string, e não importa mais que chaves um objeto *teria* carregado, porque nenhum objeto passa. Dar whitelist no tipo fecha a causa; dar blocklist na chave remenda o sintoma.

## Type confusion — escalar vs. objeto

Diga a causa às claras. O app esperava um **escalar** — um valor único, uma string: "a senha é igual a isto." O que ele aceitou foi um **objeto** — `{"$ne": null}` — que o MongoDB lê como *estrutura*: um operador descrevendo como casar, não um valor a casar. O bug inteiro é que o input teve permissão de mudar de tipo, do escalar que o código presumia para um objeto que o motor de query interpreta. Forçar o tipo fecha na raiz: com uma string garantida, não há objeto, logo não há operador.

Uma nota ortogonal, porque é uma tangente tentadora: **hashing de senha não é o fix de NoSQL injection.** Até um app que guarda um hash bcrypt e busca o usuário por username primeiro ainda é injetável *no filtro do username* — mande `{"username": {"$ne": null}}` e o `find_one` retorna o primeiro usuário da coleção e te loga como ele. O hashing protege a senha em repouso; não faz nada quanto a um operador alcançando um filtro de query. (Este átomo mantém senhas plaintext justamente pra que a forma canônica `password: {"$ne": null}` seja a história inteira — o fix é o guard de tipo, não o formato de armazenamento.)

## O impacto é um bypass de auth — como o SQL injection, por uma causa diferente

O achado é um bypass de autenticação: um login forjado te loga como `admin` sem a senha, o que é account takeover. Esse é o mesmo teto de um bypass de auth via SQL injection — e vale segurar os dois lado a lado, porque eles são iguais em impacto e categoria e em nada mais. Os dois são **A03 — Injection**; os dois subvertem a query que o login roda. Mas o SQLi injeta *sintaxe* numa *string* que o app concatena, e o fix dele é uma query parametrizada; este injeta um *operador* mudando o *tipo* de um valor num documento que o driver já passa fielmente, e o fix dele é forçar o tipo. Mesmo teto, mesma categoria, mecanismo diferente, fix diferente. "Um átomo, uma vulnerabilidade" é sobre a *causa*, não o impacto — o `sqli-union-basic` e este átomo podem os dois terminar numa query subvertida e num login burlado, por duas raízes diferentes.
