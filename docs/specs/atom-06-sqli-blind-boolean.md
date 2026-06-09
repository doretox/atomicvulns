# Spec — Átomo 06: `sqli-blind-boolean`

> Documento de especificação para o Claude Code implementar o sexto átomo do projeto `atomicvulns` (Fase 2, primeiro átomo da fase). Leia junto com `CLAUDE.md` (Seções 3.3, 5, 8, 10.5), `ROADMAP.md`, e o átomo de referência `atoms/A03-injection/sqli-union-basic/`.
>
> Esta spec captura apenas as decisões *específicas* deste átomo — convenções estruturais (Theory primer, port scheme, banner, bilinguismo, etc.) ficam no `CLAUDE.md`.

---

## Identidade

- **ID:** `sqli-blind-boolean`
- **Categoria OWASP:** A03 — Injection
- **Pasta:** `atoms/A03-injection/sqli-blind-boolean/`
- **Número sequencial:** 06
- **Porta vulnerable:** `127.0.0.1:8006`
- **Porta fixed:** `127.0.0.1:8106`
- **Theory primer:** [PortSwigger: Blind SQL injection](https://portswigger.net/web-security/sql-injection/blind) — citar com este título exato em EN e PT (nome em inglês, sem traduzir, conforme convenção estabelecida em v0.1.0).

---

## Classe de vulnerabilidade

Blind SQL injection booleana. Input não sanitizado concatenado em SQL onde o resultado **não** é devolvido no response body, mas a aplicação tem dois estados de resposta distinguíveis (oráculo) — atacante extrai dado uma decisão booleana de cada vez. Esta variante específica ensina o salto conceitual mais importante depois da UNION-based: o canal de exfiltração não precisa ser o response body em si — basta qualquer sinal observável que difira entre `condição = true` e `condição = false`.

Contraste explícito com o átomo 01 (`sqli-union-basic`) é parte da aula: lá o canal é o próprio body (`UNION` empurra linhas pra render); aqui o body só diz "Welcome" ou "Invalid credentials", e o aluno precisa montar o dado bit a bit.

---

## Feature simulada

**Login.**

A app expõe `GET /` (formulário de login) e `POST /login` (verificação). O usuário tipa `username` + `password`, a app procura uma linha em `users` que case com ambos, e devolve uma das duas páginas:

- **Sucesso:** página simples com `Welcome, <username>!` (HTTP 200).
- **Falha:** página com `Invalid credentials.` (HTTP 200, mesmo status — o oráculo vive no body, não no status code).

Sem cookies, sem sessão persistida, sem CSRF token. A app só responde com uma das duas páginas e termina ali. Essa simplicidade é deliberada: o oráculo precisa ser inequívoco, e qualquer feature adicional (flash messages, redirects, headers de sessão) introduz ruído que atrapalha a leitura no Repeater.

**Tipo de átomo:** com HTML (`templates/index.html` para o form + `templates/result.html` mostrando uma das duas mensagens). O HTML existe como destino legítimo das requests enviadas pelo Burp, não como ponto de entrada do aluno — o walkthrough é integralmente Burp-only desde a primeira request.

---

## Schema de dados

SQLite, arquivo `lab.db`, seed idempotente no startup. **Estrutura paralela ao átomo 01**, com uma adição: a tabela `users` ganha uma coluna `password`. A tabela `secrets` é mantida com a mesma forma do átomo 01 para reforçar o paralelismo mnemônico (o aluno já viu esse schema), mas **não é o alvo deste átomo** — o target da exfiltração blind é `users.password`.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    bio TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    password TEXT NOT NULL
);

-- secrets mirrors atom-01 schema for recognition;
-- not the target of this atom's exploit.
CREATE TABLE secrets (
    user_id INTEGER NOT NULL,
    password_hash TEXT NOT NULL,
    api_key TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO users (username, bio, joined_at, password) VALUES
    ('alice', 'Coffee lover and trail runner.',    '2023-01-15', 'wonderland'),
    ('bob',   'Full-time dad, part-time sysadmin.','2023-04-02', 'hunter2pwd'),
    ('carol', 'Building things on the internet.',  '2023-09-20', 'carolcat42');

INSERT INTO secrets (user_id, password_hash, api_key) VALUES
    (1, '$2b$12$fakehashfakehashfakehashfakeha', 'sk_test_alice_fakekey_aaaa1111'),
    (2, '$2b$12$otherhashotherhashotherhashoth', 'sk_test_bob_fakekey_bbbb2222'),
    (3, '$2b$12$carolhashcarolhashcarolhashcar', 'sk_test_carol_fakekey_cccc3333');
```

**Por que `password` em texto puro:** a vulnerabilidade é SQLi blind, não password storage. Texto puro mantém o walkthrough legível (10 caracteres alfanuméricos minúsculos para alice) e o aluno consegue verificar visualmente o resultado da extração. O walkthrough inclui uma frase reconhecendo que aplicações reais armazenam hash, e que a técnica blind extrairia o hash com exatamente o mesmo procedimento, só que muito mais lento. Não fingir realismo onde isso atrapalha a aula.

**Alvo de extração:** `users.password` da `alice` → `wonderland` (10 chars, `[a-z]`).

---

## Rotas

### `GET /`

Formulário de login. Pseudocódigo trivial:

```python
@app.route("/")
def index():
    return render_template("index.html")
```

### `POST /login`

Endpoint vulnerável. Pseudocódigo da view vulnerável:

```python
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    # VULNERABLE: user input concatenated into SQL string
    query = (
        f"SELECT username FROM users "
        f"WHERE username = '{username}' AND password = '{password}'"
    )
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(query).fetchone()
    conn.close()
    if row:
        return render_template("result.html", outcome="welcome", username=row[0])
    return render_template("result.html", outcome="invalid")
```

**Decisão deliberada — sem debug block.** O átomo 01 renderiza a query executada no template (`Executed query: ...`) pra o aluno ver o efeito da injection diretamente. Aqui isso **destrói a lição**: blind SQLi presume que o atacante não tem visibilidade da query nem do resultado da query — só do oráculo binário. Vazar a query no body transforma o átomo em UNION-based-bis. Por isso o template `result.html` **não** recebe nem mostra a query, em nenhuma das versões. Esta divergência é documentada no walkthrough em uma frase curta ("ao contrário do átomo 01, aqui não há bloco de debug — blind precisa ser blind").

### Versão `fixed/`

```python
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT username FROM users WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()
    conn.close()
    if row:
        return render_template("result.html", outcome="welcome", username=row[0])
    return render_template("result.html", outcome="invalid")
```

---

## HTML

Dois templates, ambos respeitando ≤40 linhas, CSS ≤5 linhas, sem JS, sem framework.

### `templates/index.html`

- Banner de aviso no topo.
- Título: `Sign in`.
- `<form method="post" action="/login">` com dois campos (`username`, `password`) e um botão `Sign in`.
- Linha curta: `Try: alice / wonderland` (dica do happy path — sem isso o aluno não tem como ver "Welcome" sem já estar atacando, e perde a referência do estado "sucesso").
- Rodapé padrão com a dica do Burp.

### `templates/result.html`

- Banner de aviso no topo.
- Um bloco condicional Jinja:
  - Se `outcome == "welcome"`: `<h1>Welcome, {{ username }}!</h1>` + um parágrafo curto neutro (ex: `You are signed in.`).
  - Senão: `<h1>Invalid credentials.</h1>` + `<p>Please check your username and password.</p>`.
- Link `← Back` para `/`.
- Rodapé padrão com a dica do Burp.

**Importante:** os dois textos discriminantes ("Welcome, ..." vs "Invalid credentials.") são o **oráculo**. Não os mexa em refatorações futuras sem atualizar o walkthrough — o aluno procura essas strings exatas em busca de match.

---

## Fix

Diff esperado entre `vulnerable/app.py` e `fixed/app.py`:

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

Mesma justificativa do átomo 01 (placeholder `?` força o driver a separar SQL de dado), reformulada no DIFF.md sem copiar e colar — mas com uma diferença explícita: **a mensagem de erro do fix não muda**. O fix **não** existe pra "esconder o oráculo"; existe pra impedir que input vire SQL. O oráculo (mensagens diferentes para sucesso/falha) é comportamento legítimo de qualquer login real e continua presente na versão fixed — só que não pode mais ser questionado pelo atacante porque o atacante perdeu a capacidade de injetar condições.

Esta nuance vale uma frase no DIFF.md: "blind SQLi não se mitiga 'achatando as duas respostas' — isso é workaround frágil. A mitigação é remover a injeção; com o input parametrizado, o oráculo deixa de ser controlável pelo atacante."

---

## Walkthrough — payloads

Cinco passos. A escalada didática aqui é: prova de injeção → estabelecer o oráculo (TRUE) → estabelecer o oráculo (FALSE) → extrair length → extrair primeiro char → automatizar com Intruder.

Todas as requests são `POST /login HTTP/1.1` com `Content-Type: application/x-www-form-urlencoded` e body `username=<...>&password=<...>`. O walkthrough deve incluir uma nota curta sobre encoding no body URL-encoded (paralela à nota de URL encoding do átomo 01 e 02): `'`, `=`, `&` no body precisam de cuidado; `Ctrl+U` na seleção dentro do Repeater faz o serviço.

### Step 1 — Confirm the injection point (login bypass)

- **Body (decoded):** `username=alice' --&password=anything`
- **Body (Burp-ready):** `username=alice%27%20--&password=anything`
- **Resposta esperada:** `Welcome, alice!` (página de sucesso).
- **Por quê:** o `'` fecha o literal de username e `--` comenta o `AND password = '...'`. A query vira `SELECT username FROM users WHERE username = 'alice' --' AND password = 'anything'`, retorna a linha da alice, login efetuado **sem saber a senha**. Confirma que o input vira SQL.

Este passo é familiar para quem fez o átomo 01 — é a mesma técnica de fechamento de string + comentário. Serve aqui como "âncora": antes de entrar no terreno blind, o aluno precisa ter certeza de que está mesmo injetando.

### Step 2 — Establish the boolean oracle (TRUE branch)

- **Body (decoded):** `username=nobody' OR '1'='1&password=x`
- **Body (Burp-ready):** `username=nobody%27%20OR%20%271%27%3D%271&password=x`
- **Resposta esperada:** `Welcome, alice!` (ou seja, *alguém* — a primeira linha que casar; ver nota abaixo).
- **Por quê:** a query final é `SELECT username FROM users WHERE username = 'nobody' OR '1'='1' AND password = 'x'`. Pelas regras de precedência SQL (`AND` antes de `OR`), isso vira `username='nobody' OR ('1'='1' AND password='x')`. O segundo lado nunca casa (nenhum user tem password `x`), e `username='nobody'` também não casa — então o aluno **esperaria** "Invalid credentials". Esse comportamento contra-intuitivo é a primeira armadilha de blind: precisão sintática importa. O walkthrough deve mostrar o payload acima falhando primeiro, depois corrigir para um que de fato force TRUE:

- **Body (decoded, corrigido):** `username=nobody' OR '1'='1' --&password=x`
- **Body (Burp-ready):** `username=nobody%27%20OR%20%271%27%3D%271%27%20--&password=x`
- **Resposta esperada:** `Welcome, alice!` (primeira linha da tabela retorna; SQLite ordena por rowid por padrão, então é alice).
- **Por quê:** a única coisa que mudou foi o `--` no final. A query final agora é `SELECT username FROM users WHERE username = 'nobody' OR '1'='1' --' AND password = 'x'`. O `--` comenta tudo a partir dele, sobrando `username='nobody' OR '1'='1'`, que é TRUE pra toda linha. `fetchone()` traz a primeira → alice. O `--` resolveu a precedência ao **encerrar o contexto da query antes do `AND password`** — sem ele, o `AND` continuava amarrando o `'1'='1'` ao predicado de senha, e o `OR` perdia.

Esse pequeno "tropeço pedagógico" (mostrar o `OR '1'='1'` quebrando antes de o `--` resolver) ensina algo que blind exige: **você não vê a query, então precisa raciocinar sobre precedência de operadores como se tivesse acesso ao parser**. A lição é sobre o `--`, não sobre as aspas — uma variável muda entre os dois payloads, uma coisa é ensinada.

### Step 3 — Establish the FALSE branch

- **Body (decoded):** `username=nobody' OR 1=2 --&password=x`
- **Body (Burp-ready):** `username=nobody%27%20OR%201%3D2%20--&password=x`
- **Resposta esperada:** `Invalid credentials.`.
- **Por quê:** `username='nobody' OR 1=2` é FALSE pra toda linha, `fetchone()` retorna `None`. Este é o "lado escuro" do oráculo. Ao final deste passo, o aluno tem em mãos os dois estados — qualquer condição que ele consiga embutir no `OR ... --` vai retornar um ou outro. **Aqui o conceito 'blind' faz clique.**

### Step 4 — Extract password length

Agora se sai do "demonstrar o oráculo" e entra em "usar o oráculo como meio de exfil". A condição embutida é uma subquery que pergunta sobre dado real.

- **Body (decoded, N variável):** `username=nobody' OR (SELECT LENGTH(password) FROM users WHERE username='alice') = N --&password=x`

O aluno itera N de 1 até ~20. Para todo N ≠ comprimento real, resposta = `Invalid credentials.`. Quando N = 10, resposta = `Welcome, alice!`. Conclusão: a senha tem 10 caracteres.

Este passo deve ser demonstrado primeiro **à mão no Repeater** com 2-3 iterações (ex: N=5 → invalid, N=10 → welcome, N=15 → invalid), pra o aluno sentir o ritmo da inferência. O Intruder entra no Step 5.

### Step 5 — Extract characters and automate with Burp Intruder

Payload base:

- **Body (decoded, P = posição, C = caractere candidato):** `username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),P,1) = 'C' --&password=x`

Demonstração manual no Repeater (primeiro caractere):

- P=1, C='a' → `Invalid credentials.`
- P=1, C='w' → `Welcome, alice!` → primeiro char é `w`.

Aí o walkthrough explicitamente faz a transição pro Intruder, com configuração detalhada paralela ao nível de hands-on que o atom 01 usa pro Repeater:

1. **Send to Intruder** o request com payload base configurado para P=1.
2. **Marcar duas posições de payload** com `§...§`: o `1` em `,1,` e o `'a'` (o caractere candidato).
3. **Attack type:** `Cluster bomb` (cartesiano entre posições × caracteres).
4. **Payload set 1 (posição P):** Numbers, 1 a 10, step 1.
5. **Payload set 2 (caractere C):** Brute forcer com charset `abcdefghijklmnopqrstuvwxyz`, length 1. (Justificar a escolha do alfabeto: o aluno já sabe que o password é 10 chars; pode também escolher `[a-z0-9]` por segurança, mas para este seed lowercase basta.)
6. **Grep — Match** com a string `Welcome, alice!` na aba *Options* (ou *Settings* em versões mais novas). A coluna `Welcome, alice!` no resultado vira o boolean do oráculo.
7. **Start attack.** Resultado: 10 hits, um por posição, cada hit revelando uma letra. Ordenando por posição: `w`, `o`, `n`, `d`, `e`, `r`, `l`, `a`, `n`, `d` → `wonderland`.

O walkthrough mostra o resultado consolidado e fecha o ciclo com uma observação: **o oráculo era binário, mas com 10 × 26 = 260 requests o atacante extraiu a senha inteira**. Esse é o ponto.

### Why this is "blind" — a explicit contrast with atom 01

O walkthrough fecha com um parágrafo curto contrastando com `sqli-union-basic`:

> Em UNION-based, o canal de exfil é o próprio response body: a query traz colunas extras, o template as renderiza, e o atacante lê dados diretamente. Aqui não há canal direto — o body só tem duas formas possíveis ("Welcome" ou "Invalid"). O atacante inverte o problema: em vez de pedir "me devolva o dado", pergunta "o dado *é* X?", e usa as duas respostas observáveis como bit. 260 bits depois, tem a senha. A causa do bug é idêntica nos dois átomos (concatenação de input em string SQL); o que muda é o que o atacante consegue ver, e portanto a forma do exploit.

---

## Dependências extras

```
Flask==3.0.0
```

Mesmas do átomo 01. `sqlite3` é stdlib. Nada mais — sem bcrypt (password é texto puro deliberadamente), sem requests (não há HTTP outbound), sem JWT.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Vetor | Login form (`POST /login`) | Oráculo binário mais limpo possível (sucesso/falha de auth). Realista — todo pentester encontra blind SQLi em logins. |
| Método HTTP | `POST` form-encoded | Login real é POST. Introduz o workflow de editar request body no Repeater (atoms 01 e 02 só tinham querystring), agregando técnica útil sem desviar do tema. |
| Schema | Estende o do átomo 01 (`users + secrets`, adiciona `users.password`) | Reforça memória; o aluno reconhece o cenário e foca na diferença do exploit, não no setup. |
| Oráculo | Texto do response body (`Welcome, ...` vs `Invalid credentials.`), status 200 nas duas | Mais realista (status code idêntico força o aluno a ler o body). Mais detectável no Burp (visível direto no painel Response). |
| Alvo de extração | `users.password` da alice = `wonderland` (10 chars, `[a-z]`) | Curto o suficiente pra walkthrough caber, longo o suficiente pra Intruder valer a pena. Texto puro mantém legibilidade; nota no walkthrough cobre o "real-world seria hash". |
| Sink | Direto em `app.py`, paralelo ao átomo 01 | Princípio do projeto: vuln visível em ≤30 linhas, sem indireção. |
| Debug block (query renderizada) | **Removido** deliberadamente | Mostrar a query destrói a aula de blind. Divergência documentada no walkthrough em uma frase. |
| Burp Intruder | Hands-on com configuração explícita | Coerência com átomo 01 (que é hands-on com Repeater). Intruder é a técnica que muda a escala do ataque — descrever sem demonstrar deixaria o aluno de fora do salto pedagógico mais importante do átomo. |

---

## Open questions para o mantenedor revisar

Lista curta, em ordem de impacto descendente. Se nenhuma destas for problema, o Claude Code segue com as decisões da tabela acima.

1. **Alvo de extração — `users.password` em texto puro vs. alternativa.** A spec assume `users.password = 'wonderland'` em texto puro porque é o mais legível. Alternativas consideradas e rejeitadas:
   - `secrets.api_key` (paralelo perfeito ao átomo 01) — rejeitado porque 30 chars × 36 alfabeto = ~1000 requests; o walkthrough fica longo demais para o pedagogicamente necessário.
   - Adicionar `users.recovery_code` (6-8 dígitos numéricos) — rejeitado por adicionar uma coluna nova sem motivo de feature; o oráculo natural do login já direciona o aluno pra password.
   - Hashear o password — rejeitado porque extrair 60 chars de bcrypt char-by-char é absurdo numa aula introdutória.
   - O texto da senha de alice (`wonderland`) é uma escolha estética e pode ser trocado livremente desde que mantenha 8-12 chars `[a-z]`. Se houver objeção forte ao texto puro mesmo com a nota didática, sugerir alternativa.

2. **Vetor — login vs. cookie-based session lookup vs. search/profile.** A spec assume login. PortSwigger ensina blind boolean primeiro via cookie (`TrackingId` lookup). O caminho cookie tem a vantagem de "exploração sem autenticar nada" mas o setup é mais artificial e o aluno tem de aceitar a premissa de que existe esse cookie por motivos. Login é mais autoexplicativo. Confirmar?

3. **Mensagens de erro idênticas no fix?** A spec deixa as duas mensagens (`Welcome, ...` / `Invalid credentials.`) presentes na versão fixed também — o argumento é que isso é comportamento legítimo de login e a mitigação real é a parametrização. Caso o mantenedor prefira que o fix *também* unifique as mensagens (defense in depth), o `result.html` da pasta fixed pode renderizar `Login attempt processed.` nos dois casos. Acho que **não** deve fazer isso (perde a clareza pedagógica do "o oráculo continua, mas o atacante perdeu o controle"), mas registro a alternativa.

4. **Pequeno "tropeço pedagógico" no Step 2 (`OR '1'='1'` → quebra → corrige para `OR 1=1 --`).** Adiciona valor (ensina precedência de operadores em contexto blind), mas alonga o passo. Manter ou cortar direto para o payload que funciona?

5. **Charset do Intruder no Step 5.** A spec usa `[a-z]` porque a senha do seed é minúscula. Realisticamente um atacante testaria `[a-zA-Z0-9]` ou imprimíveis ASCII. Manter restrito por brevidade do walkthrough, ou ampliar o charset e aceitar mais requests no exemplo?

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o "irmão escuro" do átomo 01. Onde o 01 mostra dado escapando pelo body, este mostra dado escapando por inferência. Cada parágrafo do walkthrough deve poder ser lido com o `sqli-union-basic` aberto ao lado, e a diferença entre os dois deve estar visível na linha em discussão.
- **Não introduzir bcrypt, sessões, CSRF tokens, flash messages, JWT, ou qualquer feature de login "real".** O login é instrumento didático mínimo, não exemplo de autenticação. Se você sentir vontade de "consertar" o login (hash, lockout, rate-limit), pare — não é este átomo.
- **`templates/result.html` deve manter as duas strings discriminantes (`Welcome, ...` e `Invalid credentials.`) verbatim em ambas as versões (vulnerable e fixed).** O walkthrough referencia essas strings; mudar quebra silenciosamente a aula.
- **Walkthrough Intruder:** descrever configuração de menus reais do Burp Community Edition (não Pro). O `Cluster bomb`, o `Grep — Match`, o `Numbers` payload set existem nas duas. Se houver dúvida sobre nome exato de tab/aba na versão atual do Burp, perguntar antes de inventar.
- **Cross-atom reference policy:** está OK referenciar `sqli-union-basic` (já publicado em `main`); está proibido referenciar `sqli-blind-time`, `xss-stored` ou qualquer outro átomo da Fase 2+ ainda não publicado. Onde a tentação for foreshadowing ("o próximo átomo vai mostrar time-based"), generalizar a lição ou linkar PortSwigger Academy, conforme Seção 5 do `CLAUDE.md`.
- **Bilingue PT+EN no mesmo commit**, padrão estabelecido em v0.1.0.
- **Theory primer obrigatório** no topo do `README.md` e do `README.pt-BR.md` linkando para `https://portswigger.net/web-security/sql-injection/blind`, com o título "Blind SQL injection" preservado em inglês também na versão PT.
- **`docker-compose.yml`:** `127.0.0.1:8006:5000` (vulnerable), `127.0.0.1:8106:5000` (fixed). Reaproveitar o esqueleto do átomo 01.
- **Validar manualmente que os cinco passos funcionam na versão vulnerable e falham na versão fixed.** O Step 1 (`alice' --`) deve, no fixed, retornar `Invalid credentials.` — não bypass.
