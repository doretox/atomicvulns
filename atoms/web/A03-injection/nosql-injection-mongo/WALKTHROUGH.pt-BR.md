# Walkthrough — nosql-injection-mongo

## 1. Contexto

A app é uma API de login em JSON. Você faz `POST /login` com `username` e `password`, e o servidor busca o usuário no MongoDB com uma única query — `find_one({"username": username, "password": password})`. Se um documento casa, você está autenticado.

O detalhe que a torna explorável é o que uma query do MongoDB *é*. No SQL, uma query é uma string de texto. No MongoDB, uma query é um **documento** — um objeto de pares campo/valor — e um valor pode ser um **escalar** simples (uma string ou número: "este campo é igual a este valor") ou um **operador** (uma chave especial começando com `$`, como `$ne`, "diferente de", que descreve *como* casar em vez de um valor a casar). Este átomo é **NoSQL injection**: interferir na query que uma app manda para um banco NoSQL. No OWASP Top 10 ele cai em **A03 — Injection**, a mesma categoria do SQL injection — input não-confiável alcançando um interpretador de query que o trata como estrutura, não como dado inerte. O endpoint vulnerable joga o seu input cru direto no documento de query, então você consegue contrabandear um operador para o lugar onde ele esperava uma string.

Este átomo é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater**; os mesmos requests rodam no `curl`. A prova é a própria resposta do login — nada executa num browser. É esse o ferramental inteiro.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view de login é curta:

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    # VULNERABLE: username/password go straight into the query filter...
    user = users.find_one({"username": username, "password": password})
    if user:
        return jsonify({"authenticated": True, "user": user["username"]})
    return jsonify({"authenticated": False}), 401
```

`request.get_json()` parseia o corpo num `dict` Python, e o JSON aninha — então `password` é o que o cliente colocou ali: uma string *ou* um objeto aninhado. Os dois valores vão direto pro documento de filtro entregue ao `find_one`. Faça a pergunta do auditor: *este `password` que EU controlo cai dentro de um filtro de query — e se eu fizer dele um objeto com um operador em vez de uma string?* Aí o objeto vira estrutura da query.

Repare que não há o que dar `grep` como você grepparia uma concatenação de SQL em f-string — o `pymongo` nunca monta uma string de query. Você pega isto lendo cada query cujo filtro recebe input da request e perguntando "o tipo deste valor é forçado a ser um escalar?" Aqui não é.

## 3. Exploração via Burp Suite

Aponte o Burp pra API vulnerable em `127.0.0.1:8022` e trabalhe do Repeater. (As senhas semeadas estão visíveis no `mongo/mongo-init.js`, então o baseline pode usar uma real; o ataque não vai precisar.)

### Baseline — o login funcionando normalmente

Uma credencial real em string autentica:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8022
Content-Type: application/json

{"username": "admin", "password": "s3cr3t-admin-pw"}
```

Response — `200`:

```json
{"authenticated": true, "user": "admin"}
```

A feature funciona, com strings. Segure essa forma: uma string em `password` significa "o campo password é igual a este valor exato."

### Passo 1 — Troque a string por um operador

No lugar da string de senha, mande um **objeto** carregando um operador — `{"$ne": null}`, "diferente de null." O `$ne` não casa um valor literal; ele casa qualquer documento cujo `password` seja qualquer coisa diferente de `null`. Como todo usuário semeado tem uma senha (não-null), ele casa todos — e você prende o username em `admin`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8022
Content-Type: application/json

{"username": "admin", "password": {"$ne": null}}
```

Response — `200`:

```json
{"authenticated": true, "user": "admin"}
```

Você logou como `admin` sem a senha. O filtro que a app de fato rodou foi `{"username": "admin", "password": {"$ne": null}}` — você prendeu o username em `admin` e disse ao Mongo "qualquer senha menos null", e o documento do admin casou. Nada aqui é truque de string; o payload é um objeto JSON perfeitamente válido. (`{"$gt": ""}` — "maior que a string vazia" — te loga da mesma forma, pelo mesmo motivo.)

O lab é isolado — os apps bindam em `127.0.0.1` e o container `mongo` não tem porta no host nenhuma — e o payload é benigno: ele só subverte uma consulta (`find_one`) pra provar o bypass, sem escrever nem dropar nada. Os usuários semeados são fake.

## 4. O que a vuln NÃO é

O exploit é rápido, e pode te empurrar pro fix errado. Mate as conclusões erradas.

**Não é SQL injection.** Não há aspas pra quebrar, `UNION`, `OR 1=1`, nem string de comando alguma — o payload é um objeto JSON válido. Prove: mande o payload clássico de SQL como a *string* de senha —

```
POST /login HTTP/1.1
Host: 127.0.0.1:8022
Content-Type: application/json

{"username": "admin", "password": "' OR 1=1 --"}
```

— e ele falha:

```json
{"authenticated": false}
```

`401`. Não há SQL nem concatenação pra ele quebrar; o `find_one` só procura um usuário cuja senha seja literalmente a string `' OR 1=1 --`, não acha nenhum, e te rejeita. O que te loga é o *objeto*, nunca uma string.

**Não é um bug de escape.** Não há caractere perigoso dentro de uma string pra escapar — o vetor é o *tipo* do valor (um objeto), não um metacaractere dentro de um valor.

**Não é falta de parametrização.** Esta é a armadilha pra quem conhece SQLi. O `pymongo` nunca costura o seu input numa string de texto de query; ele passa o `dict` pro servidor *como um documento* — que é exatamente o que "parametrizado" significa no mundo do SQL: dado mantido separado do comando. E ainda assim é vulnerável, porque a injeção não é sintaxe dentro de uma string — é um valor que mudou de tipo, do escalar que o app esperava para um objeto que o driver encaminha fielmente como operador. A parametrização que fecha o SQL injection não tem análogo que pegue isto.

O que ele *é*: **type confusion** (confusão de tipo). O app esperava um escalar (uma string) e recebeu um objeto, e o objeto virou estrutura da query. O único fix é forçar o tipo — rejeitar qualquer coisa que não seja uma string antes que ela chegue à query (§6).

## 5. Impacto

Bypass de autenticação — account takeover. Você logou como `admin` sem credencial, o que dá acesso a tudo que o `admin` alcança no contexto da vítima. Esse é o mesmo teto de um bypass de auth via SQL injection (o `sqli-union-basic` e os irmãos blind subvertem uma query SQL pro mesmo fim; este subverte uma query do Mongo), alcançado por um mecanismo diferente. Não é RCE aqui — os operadores JavaScript do MongoDB (`$where`) podem escalar o NoSQL injection ainda mais em alguns apps, mas este átomo modela a face de bypass de auth e não reivindica mais que isso.

## 6. Por que o fix funciona

Rode os mesmos requests contra a API fixed na porta **8122** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança).

O payload `{"$ne": null}` é rejeitado:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8122
Content-Type: application/json

{"username": "admin", "password": {"$ne": null}}
```

Response — `400`:

```json
{"error": "username and password must be strings"}
```

A view fixed confere o tipo antes da query: `username` e `password` têm que ser `str`, ou ela retorna `400`. Um objeto nunca alcança o `find_one`, então nunca pode virar um operador.

E a feature fica intacta: a credencial real em string (`{"username": "admin", "password": "s3cr3t-admin-pw"}`) ainda retorna `200` na 8122, exatamente como no app vulnerable. A feature é idêntica; só o payload-objeto separa os dois. O fix força o *tipo* — ele não escapa, não parametriza (o `pymongo` já parametriza), e não faz blocklist de chaves `$`. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) percorre por que cada uma dessas alternativas erra.
