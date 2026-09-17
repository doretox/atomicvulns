# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é como o `POST /profile` escolhe quais campos escrever na conta (comentários abreviados):

```diff
 account = {"name": "Demo User", "email": "demo@example.com", "role": "user"}

+# The SERVER decides which fields a profile update may set (allowlist of fields).
+ALLOWED_FIELDS = {"name", "email"}
+

 @app.route("/profile", methods=["POST"])
 def update_profile():
     data = request.get_json(silent=True) or {}
-    # VULNERABLE: copy EVERY field from the client's JSON straight into the account ...
-    account.update(data)
+    # FIXED: allowlist of FIELDS -- only name/email are copied; role and anything else ignored ...
+    for field in ALLOWED_FIELDS:
+        if field in data:
+            account[field] = data[field]
     return jsonify(account)
```

Todo o resto é byte-a-byte idêntico entre as duas versões: os imports, a `account` seedada, o `GET /profile`, o `GET /admin`, o `__main__`, o `Dockerfile`, e o `requirements.txt` (não há templates — este átomo é API-only). O bug — e o fix — vivem inteiramente em como o `POST /profile` seleciona os campos.

## O que mudou

A versão vulnerable faz `account.update(data)` — ela mescla o JSON parseado inteiro (`data`, o que quer que o cliente tenha mandado) no dict da conta, então *toda* chave vira um atributo. A versão fixed introduz `ALLOWED_FIELDS = {"name", "email"}` e copia só esses: `for field in ALLOWED_FIELDS: if field in data: account[field] = data[field]`. Isso é um fix *lógica-diferente* — a mescla cega é substituída por uma seleção de campos explícita, definida pelo servidor. A linha `request.get_json(silent=True) or {}` não muda; o que mudou é o que o código faz com o corpo parseado.

## Por que isso corrige o bug

`ALLOWED_FIELDS` é uma allowlist dos atributos que o usuário tem permissão de setar. O loop percorre a *allowlist*, não o input, então uma chave que o cliente manda e que não está na lista nunca é tocada — ela não consegue chegar na conta de jeito nenhum. `name` e `email` atualizam como antes; `role`, `is_admin`, ou qualquer outra coisa no JSON é silenciosamente ignorada. O servidor, não o cliente, agora decide quais atributos uma atualização de perfil pode escrever. Esse é o reparo inteiro: a classe é "a app faz bind dos campos da request num objeto sem escolher quais o usuário pode setar", e a allowlist é exatamente a negação disso.

O guard `if field in data` mantém o comportamento de atualização *parcial* da feature: um campo ausente do JSON fica no valor atual, então um request que manda só `name` atualiza só `name`. Prova de isolamento: mande a atualização legítima `{"name", "email"}` pras duas apps e as duas voltam a mesma conta; só o campo extra `role` diverge — a app vulnerable o escreve, a fixed o descarta. Aceitar uma atualização de perfil em JSON nunca foi o bug; deixar o cliente decidir quais campos ele seta é que era.

## Allowlist de campos, não um blocklist de nomes de campo

O fix rápido tentador é *inspecionar o input* atrás da chave perigosa — "se o JSON tiver `role`, apaga" ou "rejeita a request quando `role` estiver presente". Isso é um blocklist, e ele perde. Um tour rápido do porquê:

- **Você tem que lembrar de todo campo perigoso, pra sempre.** `role` é o óbvio, mas o mesmo objeto de conta pode carregar `is_admin`, `is_staff`, `verified`, `email_verified`, `credits`, `balance`, `owner` — esqueça um e ele continua gravável.
- **Todo campo adicionado ao modelo depois é um buraco novo.** Um blocklist não sabe do `is_superuser` que alguém adiciona no próximo sprint; ele silenciosamente passa a deixá-lo entrar. Uma allowlist o ignora de graça — qualquer coisa não nomeada é descartada por padrão.
- **Variações escapam de uma checagem de chave ingênua:** aninhamento (`{"account": {"role": "admin"}}`), grafias alternativas, capitalização.

O fix durável é estrutural. Em vez de perguntar "o input contém um campo perigoso?", pergunte "esse campo é um que o usuário tem permissão de setar?" — enumere os campos *permitidos* (`name`, `email`) e copie só esses. Tudo fora da lista é descartado, inclusive campos que ainda não existem. O blocklist é nomeado aqui pra mostrar por que ele falha; ele **não** é aplicado.

É a mesma lição allowlist-vs-blocklist do `open-redirect`, o outro átomo A01 onde o servidor tem que decidir em vez de confiar no input. Lá o servidor decide o *destino* do redirect (aceite só um path interno; não blocklist `http://`); aqui ele decide os *campos* graváveis (aceite só `name`/`email`; não blocklist `role`). Mesma forma — enumere o que é permitido, não caça o que é proibido — numa superfície diferente.

## Mass assignment é mais famoso em ORMs

Este átomo modela mass assignment com um `dict.update()` cru pra o bug ser uma linha visível. No mundo real ele é mais notório uma camada abaixo, em frameworks com ORM. Um **ORM** (Object-Relational Mapping — uma lib que mapeia os atributos de um objeto pras colunas do banco) costuma oferecer uma conveniência que constrói ou atualiza um registro direto dos parâmetros da request — `Model(**params)`, `record.update(params)`, um `create(request.POST)`. Quando o saco de parâmetros inteiro é passado, uma chave extra como `role` ou `is_admin` vira uma *coluna* escrita, persistida no banco — o clássico bug de "autobinding" por trás de várias advisories conhecidas. O mecanismo é idêntico ao que você vê aqui (o código confia na *forma* do input e faz bind dele em bloco num objeto), e o fix também: uma allowlist de atributos setáveis, que os frameworks empacotam como "strong parameters", "permitted attributes", ou listas "fillable/guarded". Este átomo usa um dict simples e nenhum ORM de propósito — a mesma lição, sem nada entre você e a única linha ruim. O ORM é descrito aqui, não introduzido.

## Impacto: privilege escalation vertical

O impacto é **privilege escalation vertical**: um `user` normal vira `admin`, e o `GET /admin` só-de-admin abre (`403` → `200`). Esse é o teto honesto — **não é RCE, não é takeover de servidor**; você ganhou um papel na aplicação, não execução de código. Dois contrastes o situam dentro de A01:

- **vs `open-redirect`** (o outro átomo A01 do tipo "o servidor decide"): os dois entregam ao servidor uma decisão que o cliente tinha usurpado, e os dois consertam com uma allowlist server-side. Lá o input controla o *destino* do redirect; aqui ele controla quais *campos* são escritos. Mesma lição, superfície diferente.
- **vs IDOR / BOLA** (`idor-numeric-id`, `idor-uuid-guessable`, `bola-rest`): esses são *horizontais* — você lê o objeto de *outro* usuário porque um check de dono (ownership) está ausente. Este é *vertical* — você escreve no *seu próprio* objeto um campo que concede privilégio, porque a seleção de campos está ausente. Eixo diferente da mesma categoria A01: lá o controle ausente é "esse objeto é seu?"; aqui é "esse campo é seu pra setar?".

Em sistemas reais a mesma falha de uma linha escreve qualquer atributo sensível que o objeto carregue — `is_admin`, `verified`, `credits`, o `owner` de um registro — que é por que mass assignment é uma entrada própria no OWASP API Security Top 10. Este átomo prova a escalada de role; essas escritas mais amplas são o alcance da classe, descrito não construído.
