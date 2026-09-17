# Spec — Átomo 07: `sqli-blind-time`

> Documento de especificação para o Claude Code implementar o sétimo átomo do projeto `atomicvulns` (Fase 2, segundo átomo da fase). Leia junto com `CLAUDE.md` (Seções 3.3, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — o átomo predecessor `atoms/A03-injection/sqli-blind-boolean/` na íntegra, além do átomo de abertura da trilogia `atoms/A03-injection/sqli-union-basic/`.
>
> Esta spec captura apenas as decisões *específicas* deste átomo — convenções estruturais (Theory primer, port scheme, banner, bilinguismo, etc.) ficam no `CLAUDE.md`. Onde o átomo 06 já resolveu uma questão (formato do Repeater, nota de encoding do body, convenção de placeholder de leitura), a instrução aqui é **reusar a forma do 06**, não reinventar.

---

## Identidade

- **ID:** `sqli-blind-time`
- **Categoria OWASP:** A03 — Injection
- **Pasta:** `atoms/A03-injection/sqli-blind-time/`
- **Número sequencial:** 07
- **Porta vulnerable:** `127.0.0.1:8007`
- **Porta fixed:** `127.0.0.1:8107`
- **Theory primer:** [PortSwigger: Blind SQL injection](https://portswigger.net/web-security/sql-injection/blind) — **a mesma página do átomo 06, por decisão deliberada**. A PortSwigger não tem página separada para time-based; o conteúdo de time delay vive na seção "Exploiting blind SQL injection by triggering time delays" dessa mesma página. Citar com o título exato `Blind SQL injection` em EN e PT (nome em inglês, sem traduzir, conforme convenção v0.1.0). O bloco do README deve sugerir foco na seção de time delays.

---

## Classe de vulnerabilidade

Blind SQL injection time-based (time-delay / timing side-channel). Input não sanitizado concatenado em SQL onde a aplicação **não devolve o resultado da query no body E não tem dois estados de resposta distinguíveis** — a response é byte-a-byte idêntica, mesmo status, para qualquer input. Não há oráculo observável no conteúdo da resposta. O único canal que sobra é a **latência**: o atacante injeta uma condição que dispara uma operação cara *somente quando a condição é verdadeira*, e infere o dado medindo quanto a resposta demorou.

**Por que esta variante é didaticamente essencial — e o que ela ensina que o 06 não ensina:** o átomo 06 (`sqli-blind-boolean`) deixou o aluno confortável com a ideia de "extrair dado por um sinal binário no body". Este átomo remove esse sinal. Ao matar o oráculo de body, ele força o salto conceitual final do blind: **o canal de exfiltração não precisa estar no conteúdo da resposta — pode estar em qualquer propriedade observável dela, inclusive o tempo.** É o caso onde a frase "blind SQLi se explora por inferência, não por leitura" fica literal: não há absolutamente nada para ler.

### O arco da trilogia (a ser explicitado no DIFF e no WALKTHROUGH)

Este é o terceiro de três átomos sobre a **mesma causa raiz** (input concatenado em string SQL), diferenciados pelo **canal que o atacante observa**:

| Átomo | Canal de exfil | Como o dado chega | Nº de requests p/ a senha |
|---|---|---|---|
| 01 `sqli-union-basic` | response **body** (dado direto) | `UNION SELECT` empurra colunas pro template | ~3 |
| 06 `sqli-blind-boolean` | sinal **binário no body** | `Welcome` vs `Invalid` = 1 bit | ~260 |
| 07 `sqli-blind-time` | **latência** | "demorou ~3s (sim) / instantâneo (não)" = 1 bit | ~260, mas cada uma mais lenta |

A causa é idêntica nos três; o fix é idêntico nos três (query parametrizada). O que muda é só **o que o atacante consegue ver** — e portanto a forma do exploit. Este átomo fecha o argumento começado no 01 e continuado no 06.

### O gancho com o átomo 06 — não inventar, está escrito

O `DIFF.md` do átomo 06 **já nomeia exatamente o cenário deste átomo**. Lá, ao discutir por que "achatar as duas respostas" não é um fix de verdade, o texto diz (verbatim):

> "A natural-looking second fix would be to make the response identical on success and failure — render `Login attempt processed.` in both cases, eliminate the asymmetry, and the attacker has no oracle to lean on. That's a workaround, not a mitigation. (...) any other observable difference (**response time**, downstream side effect, log line, second-order behavior) would re-introduce the oracle through a different door."

Este átomo **é** a porta "response time". A app vulnerable do 07 é, literalmente, "e se um dev tivesse aplicado aquele workaround tentador-mas-errado do 06?" — ele achatou as respostas em `Login attempt processed.` (boa intenção: anti-enumeration), mas **não** parametrizou a query. Resultado: o boolean oracle do 06 morreu, mas a injeção continua, e o timing reabre o oráculo por outra porta. O aluno que leu o DIFF do 06 reconhece a string `Login attempt processed.` e fecha o raciocínio sozinho.

---

## Feature simulada

**Login (mensagem unificada / anti-enumeration).**

Mesma feature do átomo 06 — `GET /` (formulário de login) + `POST /login` (verificação) — com **uma diferença deliberada e única**: a resposta é **sempre a mesma página**, independentemente de as credenciais serem válidas ou não. Não há `Welcome, <user>!`; não há `Invalid credentials.`. Há apenas:

- **Sempre:** `Login attempt processed.` (HTTP 200), para qualquer combinação de `username`/`password`, válida ou não.

Do ponto de vista do usuário legítimo: ele tenta logar, e a app responde de forma neutra ("recebemos sua tentativa"). Do ponto de vista de quem projetou: a mensagem foi unificada de propósito, como medida **anti-enumeration** — para um atacante não conseguir distinguir "usuário existe, senha errada" de "usuário não existe". É uma escolha de UX/segurança legítima e comum no mundo real.

O ponto pedagógico: essa unificação é **boa prática contra enumeration**, mas **não é um fix de SQL injection**. Ela apaga o oráculo de body (mata o boolean blind do átomo 06) sem tocar na causa raiz. A injeção segue ali; o atacante só precisa de um canal novo.

**Tipo de átomo:** com HTML (`templates/index.html` para o form + `templates/result.html` com a mensagem única). O HTML existe como destino legítimo das requests do Burp, não como ponto de entrada — o walkthrough é Burp-only desde a primeira request, exatamente como no 06.

---

## Schema de dados

**Idêntico ao átomo 06, byte a byte.** Vetor (a) escolhido (ver "Decisões"): mesma feature de login, mesmo schema, mesmo seed, mesmo alvo. A única coisa que muda do 06 para o 07 é a *resposta* (unificada) e a *forma do exploit* (timing). Reusar o schema sem alteração reforça o fio condutor da trilogia: **mesmo segredo, três formas de roubar.**

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

**Alvo de extração:** `users.password` da `alice` → `wonderland` (10 chars, `[a-z]`). Paralelo exato ao átomo 06 — o aluno extrai *o mesmo segredo*, agora por timing. A nota de "no mundo real seria hash" do 06 vale aqui também (reformulada, não copiada).

`username` é `UNIQUE`, então há índice — isso importa para a confiabilidade do delay (ver seção técnica abaixo).

---

## Rotas

### `GET /`

Formulário de login. Idêntico ao 06:

```python
@app.route("/")
def index():
    return render_template("index.html")
```

### `POST /login` — versão vulnerable

Diferença em relação ao 06: o resultado da query é **deliberadamente ignorado** e a resposta é **sempre a mesma**. A query continua sendo executada (é o que dispara o delay), mas o seu resultado não controla mais o body.

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
    conn.execute(query).fetchone()  # result intentionally ignored — response is uniform
    conn.close()
    return render_template("result.html")
```

**Por que `.fetchone()` permanece mesmo com o resultado ignorado:** a chamada força a engine a avaliar o `WHERE` (e, portanto, a subquery injetada) para produzir a primeira linha. Sem o fetch, o SQLite poderia adiar a avaliação e o delay não dispararia de forma confiável. Manter `.fetchone()` (sem atribuir a `row`) garante a execução e mantém a linha visualmente paralela ao 06. Um comentário curto explica o "ignored".

**Por que não branchar em `row`:** branchar (como o 06 faz) reintroduziria o oráculo de body — exatamente o que este átomo precisa eliminar. A ausência de branch **é** a feature anti-enumeration.

### `POST /login` — versão fixed

```python
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "SELECT username FROM users WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()  # result intentionally ignored — response is uniform
    conn.close()
    return render_template("result.html")
```

A mensagem unificada **permanece** na versão fixed (era anti-enumeration legítimo, nunca foi o bug). O que muda é só a parametrização. Contra a versão fixed, o payload de timing inteiro (cross join e tudo) vira uma string literal inofensiva no valor de `username`: nunca é parseado como SQL, nunca executa, e **toda** request volta instantânea — inclusive o probe incondicional do Step 1. Sem diferencial de tempo, o canal seca. (Validado: o payload completo como valor parametrizado de `username` não casa nenhuma linha e volta em 0,000 s.)

---

## Decisão técnica central — SQLite não tem `SLEEP()`

Esta é a decisão que **define** o átomo e o diferencia de qualquer time-based em MySQL/Postgres/MSSQL. Precisa estar resolvida na spec e explicada no walkthrough.

**O problema:** as primitivas de delay clássicas são DBMS-específicas e **nenhuma existe no SQLite**:

| DBMS | Primitiva de delay |
|---|---|
| MySQL | `SLEEP(n)`, `BENCHMARK(...)` |
| PostgreSQL | `pg_sleep(n)` |
| MSSQL | `WAITFOR DELAY '0:0:n'` |
| Oracle | `dbms_pipe.receive_message(...)` |
| **SQLite** | **— nenhuma —** |

No SQLite o atraso precisa ser **construído**, queimando CPU/tempo de forma condicional.

### Primitiva escolhida: cross join de um CTE pequeno e limitado

```sql
WITH RECURSIVE t(x) AS (
    SELECT 1
    UNION ALL
    SELECT x + 1 FROM t WHERE x < <K>
)
SELECT count(*) FROM t a, t b
```

Como expressão escalar reutilizável (chamarei de `E`): gera uma tabelinha `t` de `K` linhas e conta os `K²` pares do cross join `t a, t b`. O custo de **tempo** é **∝ K²** e CPU-bound; o custo de **memória** é **O(K)** — limitado pelas `K` linhas da tabelinha, **não** pelos `K²` pares (o `count(*)` sobre o join é um nested loop que só incrementa um contador, sem materializar o produto cartesiano). `K` é uma **constante fixa calibrada** do payload (não um placeholder de leitura).

**Por que esta primitiva — e a correção honesta de uma afirmação errada da v1 desta spec.**

A v1 usava um *counting CTE* (`WITH RECURSIVE c(x) AS (... x<N) SELECT count(*) FROM c`) e afirmava que era O(1) de memória ("fila tamanho ~1, `count` em streaming"). Antes de prosseguir, **medi** isso (SQLite 3.50.2, cada caso em processo isolado, pico de RSS via `ru_maxrss`):

| Primitiva | tempo | Δ RSS (pico) |
|---|---|---|
| counting CTE `N=10M` | 0,98 s | **0 MB** |
| counting CTE `N=30M`, `temp_store=MEMORY` | 2,96 s | **0 MB** |
| counting CTE `N=10M` **com `ORDER BY`** (força materializar) | 2,32 s | **455 MB** |
| `hex(randomblob(100M))` (randomblob escalar) | 0,30 s | **285 MB** (linear → ~2,8 GB a ~3 s) |
| **cross join `K=20000`** (400M pares), `temp_store=MEMORY` | 3,5 s | **0 MB** |

Dois achados que contrariam a v1 — e a sua própria intuição, mantenedor:

1. **O counting CTE *de fato* ficou O(1) na versão testada.** Inclusive com `temp_store=MEMORY` (que joga todo material temporário pra RAM) o Δ ficou em 0 MB — prova de que não materializa nem em disco. A previsão "a verificação iria falhar" **não** se confirmou na 3.50.2. Não vou reescrever a história alegando que ele materializa; ele não materializou.
2. **`randomblob` escalar (a inclinação da Opção B) é o *pior* candidato de memória**, não o counting CTE: cresce linear e bateria ~2,8 GB para chegar a ~3 s. O medo de OOM da v1 estava certo de *quem* — só apontava pro alvo errado.

**Então por que trocar a primitiva mesmo com o counting CTE passando?** Porque o O(1) dele depende de uma **otimização interna do SQLite** (streaming/co-rotina de um recursive CTE referenciado uma única vez alimentando um agregado). Só consegui verificar isso na 3.50.2; o container roda `python:3.11-slim` (SQLite ~3.40), que não meço aqui. E o mesmo CTE em **outra forma** (com `ORDER BY`) estoura 455 MB — ou seja, a wariness geral com recursive CTE está **correta**, só não valia para aquela forma específica. **Garantir memória via uma otimização sutil e version-specific é frágil — exatamente a suposição que esta revisão existe pra eliminar.**

O cross join garante o teto por **construção, não por otimização**: a memória é limitada pelas `K` linhas (com `K ~ 20000`, dezenas de KB), independente da versão e independente de o planner materializar `t` ou re-derivá-la — em qualquer estratégia o teto é O(K). Validei end-to-end (ver tabela no fim da seção): o payload completo com cross join deu Δ RSS 0 MB em todos os shapes.

**Ensina técnica real:** continua sendo CPU-burn condicional em SQLite — o que um pentester faz quando descobre que não há `SLEEP()`. A lição bônus (primitiva de delay é DBMS-específica) permanece 100% válida; só o exemplo concreto mudou de "contar até N" para "cruzar uma tabelinha consigo mesma". (Opção A — blob moderado dentro de um loop curto — *também* é limitada em memória, ~5 MB medidos, mas é mais lenta por unidade e depende de `randomblob` ser não-determinístico pra não ser hoisted; fico no cross join pela garantia puramente estrutural e por não usar `randomblob`.)

### Estrutura do payload condicional — `CASE` com short-circuit

O delay tem que disparar **só** quando a condição é verdadeira. O `CASE` do SQLite avalia apenas o ramo correspondente ao `WHEN` que casou — então o CTE caro fica no `THEN` e só roda no caso TRUE:

```sql
... ' AND (
    SELECT CASE
        WHEN (<pergunta>)
        THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < <K>) SELECT count(*) FROM t a, t b)
        ELSE 1
    END
) --
```

`<pergunta>` é uma condição booleana sobre dado real, por exemplo `SUBSTR((SELECT password FROM users WHERE username='alice'),P,1) = 'C'`. Condição TRUE ⇒ o cross join roda ⇒ resposta demora ~3 s. Condição FALSE ⇒ retorna `1` instantaneamente ⇒ resposta rápida.

**O short-circuit do `CASE` foi validado end-to-end** (SQLite 3.50.2, contra uma `users` real com alice/wonderland, Δ RSS sempre 0 MB):

| Shape injetado (`K=16000`) | tempo | observação |
|---|---|---|
| `alice' AND (E) --` (Step 1, incondicional) | 4,1 s | retorna alice; delay dispara |
| `... CASE WHEN (1=1) THEN (E) ELSE 1 END ...` | 3,9 s | TRUE → delay |
| `... CASE WHEN (1=2) THEN (E) ELSE 1 END ...` | **0,000 s** | FALSE → `CASE` nem avalia o `THEN` |
| `... WHEN (SUBSTR(...,1,1)='w') ...` | 3,3 s | char certo → delay |
| `... WHEN (SUBSTR(...,1,1)='a') ...` | **0,000 s** | char errado → instantâneo |
| parametrizado (`fixed/`), payload como valor de `username` | **0,000 s** | sem match, nunca executa |

O diferencial TRUE/FALSE é de ~3 s vs. 0,000 s — inequívoco.

### Por que prefixar com `alice' AND ...` (e não `nobody' OR ...` como o 06)

Detalhe de confiabilidade que **precisa** estar certo, senão o átomo não funciona:

- O 06 usou `nobody' OR <cond> --` porque lá o *resultado da linha* era o oráculo (TRUE ⇒ alguma linha casa ⇒ `Welcome`).
- Aqui o resultado da linha é irrelevante (resposta uniforme). O que importa é que a **subquery cara seja avaliada exatamente uma vez** — nem zero (sem delay) nem N vezes (delay multiplicado, sinal sujo).
- Usar `username = 'alice'` (um user que **existe**, com índice `UNIQUE`) ancora a query a exatamente uma linha. A subquery do `CASE` é **não-correlacionada** (não referencia a linha externa), então o SQLite a avalia **uma única vez** — seja porque a fatora como constante antes do seek, seja porque a avalia para a única linha que casou. Em ambas as ordens de plano, é uma vez só. Robusto. (Confirmado empiricamente: o shape TRUE deu ~3,9 s — uma única execução do delay, não múltiplos dele.)
- O prefixo `alice'` apenas fixa a query externa numa linha; a extração da senha acontece na subquery interna independente. Não é circular — é o jeito de garantir timing limpo.

Trade-off explícito: o **shape** do payload diverge do 06 (`AND (SELECT CASE …)` em vez de `OR …`), porque a primitiva de delay é inerentemente nova. Mas o que importa para a memória muscular **se preserva**: a `<pergunta>` (as condições `LENGTH`/`SUBSTR`) é idêntica à do 06, e a configuração do Intruder é idêntica. A única coisa genuinamente nova é a primitiva de delay + ler latência em vez de body.

### Lição bônus (explicitar no walkthrough)

Time-based é onde **conhecer o backend importa mais**, porque a primitiva de delay é 100% DBMS-específica. Reconhecer que o alvo é SQLite (e não MySQL) é o que determina o payload: você não tem `SLEEP()`, então constrói o atraso com um CTE recursivo. Mencionar `SLEEP`/`pg_sleep`/`WAITFOR` como "o que você usaria nos outros bancos" e o CTE como "a saída no SQLite" — uma frase, sem virar tutorial de todos os DBMS.

### Tuning (calibrar na geração contra o container rodando)

- **Delay alvo:** **~3 s** confirmado pelo mantenedor (rodada 1) para **uma** request TRUE. Longo o bastante para ser inequívoco contra os misses (dezenas de ms), curto o bastante para não arrastar o Intruder (10 hits × 3 s ≈ 30 s + misses ≈ ataque de ~40 s).
- **Knob = `K`, com tempo ∝ K².** Valor inicial sugerido: `K ≈ 12000–16000`. (No host de planning — SQLite 3.50.2 — o payload completo deu ~3,3–4,1 s a `K=16000`, e o cross join puro deu 3,5 s a `K=20000`.) Calibrar contra o container até bater ~3 s; o valor final **deve ser documentado** no DIFF/WALKTHROUGH e fixado no payload. Como o tempo é **quadrático**, a busca converge rápido — dobrar `K` quadruplica o delay — mas por isso mesmo ajustar em passos pequenos perto do alvo.
- **Intruder com 1 request concorrente.** Configurar o Resource Pool com "Maximum concurrent requests = 1". Payloads que queimam CPU competem entre si se rodarem em paralelo, sujando o sinal de latência. Concorrência 1 deixa o tempo limpo. Isto é um detalhe operacional real de time-based blind e merece uma frase no walkthrough.
- **Nota sobre throttle do Burp Community:** o Intruder Community adiciona um atraso artificial constante por request. Isso **não** atrapalha: o offset é o mesmo para TRUE e FALSE, então o diferencial de ~3 s continua nítido. Vale uma frase para o aluno não se assustar achando que "está tudo lento".

---

## HTML

Dois templates, ambos ≤40 linhas, CSS ≤5 linhas inline, sem JS, sem framework. Reaproveitar o esqueleto do 06.

### `templates/index.html`

- Banner de aviso no topo.
- Título: `Sign in`.
- `<form method="post" action="/login">` com dois campos (`username`, `password`) e botão `Sign in`.
- Linha curta `Try: alice / wonderland` — mantida do 06, mas com um propósito diferente: aqui ela serve para o aluno comprovar, no browser, que **mesmo a credencial correta devolve a mensagem genérica** (`Login attempt processed.`). Isso torna a premissa "resposta uniforme" tangível antes de ir pro Burp.
- Rodapé padrão com a dica do Burp.

### `templates/result.html`

- Banner de aviso no topo.
- **Sem condicional Jinja.** Conteúdo fixo:
  - `<h1>Login attempt processed.</h1>`
  - um parágrafo neutro, ex.: `<p>If those credentials are valid, you are now signed in.</p>`
- Link `← Back` para `/`.
- Rodapé padrão com a dica do Burp.

**Importante:** `result.html` é **idêntico** nas versões vulnerable e fixed e **idêntico** para qualquer input. Essa uniformidade É o ponto do átomo — não há string discriminante para o aluno procurar (ao contrário do `Welcome, alice!` do 06). Se uma refatoração futura reintroduzir qualquer variação no body por outcome, o átomo deixa de ensinar time-based e vira boolean blind de novo. A string `Login attempt processed.` é escolhida de propósito para ecoar o DIFF do átomo 06.

---

## Fix

Diff esperado entre `vulnerable/app.py` e `fixed/app.py` (mesma forma dos átomos 01 e 06):

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
-    conn.execute(query).fetchone()  # result intentionally ignored — response is uniform
+    conn.execute(
+        "SELECT username FROM users WHERE username = ? AND password = ?",
+        (username, password),
+    ).fetchone()  # result intentionally ignored — response is uniform
     conn.close()
     return render_template("result.html")
```

Mesma mecânica dos átomos 01 e 06 (placeholder `?` faz o driver parsear a SQL antes de ligar os valores como dado literal), **reformulada** no DIFF.md, não copiada.

### Duas notas obrigatórias no DIFF.md

1. **Nota de fechamento da trilogia.** Este é o **terceiro** átomo com fix idêntico. A técnica de exploração variou com o que o atacante observa (dado direto → sinal binário → latência), mas a vulnerabilidade e sua correção **não** mudaram. *Uma root cause, um fix, três exploits.* Referenciar `sqli-union-basic` e `sqli-blind-boolean` explicitamente (ambos publicados em `main`). A query parametrizada fecha **todos** os canais de uma vez — body, boolean e timing — porque remove a pré-condição (input virando sintaxe SQL) da qual os três dependem.

2. **Nota da mensagem unificada (paralela à "nota sobre o oracle" do 06).** A mensagem `Login attempt processed.` **permanece** na versão fixed. Ela é anti-enumeration legítimo e **nunca foi a vulnerabilidade** — a injeção era. Achatar a resposta matou o boolean oracle do 06, mas o timing reabriu o oráculo por outra porta; só a parametrização fecha de verdade. Conectar diretamente à "nota sobre o oracle" do DIFF do 06 (que previu a porta "response time"): este átomo é a demonstração concreta daquela previsão. Paralelo ao "o oráculo continua existindo, mas o atacante perde o controle" do 06 — aqui, "a mensagem uniforme continua, mas o atacante perde o canal de timing".

---

## Walkthrough — payloads

Cinco passos. A escalada: **provar injeção via delay (o canal nasce aqui)** → tornar o delay condicional (oráculo temporal TRUE/FALSE) → extrair length por timing → extrair char por timing → automatizar no Intruder lendo latência.

Todas as requests são `POST /login HTTP/1.1`, `Content-Type: application/x-www-form-urlencoded`, body `username=<...>&password=<...>`. **Reusar integralmente do átomo 06:** a nota de encoding do body (`=`, `&`, `%` precisam de encode; `Ctrl+U`/`%20` para espaços), a convenção de placeholder de leitura (`N`, `P`, `C`), e os dois blocos por passo (**Body (decoded)** + **Body (Burp-ready)**). Não reinventar essas notas — referenciar a forma estabelecida no 06.

**Moldura da trilha browser (instrução do mantenedor, rodada 1).** O walkthrough é Burp-only, como o 06. Mas a **primeira frase** da seção de exploração deve mandar o aluno abrir `/` no browser **uma única vez**, logar com `alice/wonderland`, e notar que a resposta é a mensagem genérica `Login attempt processed.` — *essa é a premissa do átomo*: a resposta é uniforme, não há "sucesso" visível. Dali em diante, tudo no Burp. O browser aqui é **prova-de-premissa de uma linha**, não uma trilha de exploração paralela (diferente da trilha browser que foi removida do 06 na validação — lá ela competia com o Burp; aqui só estabelece a premissa e sai).

Definir cedo, uma vez, a expressão de delay reutilizável (`E`), com o `K` calibrado no lugar de `<K>` (`K` é constante fixa, não placeholder de leitura):

```
E = (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < <K>) SELECT count(*) FROM t a, t b)
```

### Step 1 — Prove the injection *and* discover the only channel (unconditional delay)

- **Body (decoded):** `username=alice' AND (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < <K>) SELECT count(*) FROM t a, t b) --&password=x`
- **Resposta esperada:** a mesma página `Login attempt processed.` de sempre — **mas a response trava por ~3 s** antes de voltar.
- **Por quê:** a query vira `SELECT username FROM users WHERE username = 'alice' AND <E> --' AND password = 'x'`. `alice` casa (índice), o `AND` força a avaliação de `E`, o cross join faz `K²` comparações queimando ~3 s. O `count` (`K²`) é não-zero ⇒ truthy ⇒ a linha até retorna, mas isso é irrelevante: o body é uniforme.
- **A lição central, aqui:** em time-based, "confirmar a injeção" e "estabelecer o oráculo" **colapsam no mesmo passo**. No 06, confirmar injeção (Step 1, login bypass) e estabelecer o oráculo (Steps 2–3) eram coisas separadas, porque havia um sinal no body desde o começo. Aqui não há sinal nenhum no body — a *primeira* evidência de que existe injeção **já é** um delay. O tempo é o canal desde o primeiro probe. Não há outra coisa para observar.
- **Contraste obrigatório (o "o que a vuln NÃO é" desta classe):** um único request lento não prova nada — poderia ser jitter de rede ou carga do servidor. A prova vem da **repetibilidade e do controle**: reenvie 2–3 vezes (sempre ~3 s) e compare com um request benigno (`username=alice&password=wonderland`, instantâneo). O sinal de time-based não é "lentidão absoluta", é "diferença de latência que **eu controlo** via payload". O Step 2 transforma esse controle em oráculo.

### Step 2 — Make the delay conditional (the temporal oracle)

Introduz o `CASE`. Mesma `E`, agora dentro de um `THEN`, disparada só quando a condição casa.

- **Ramo TRUE — Body (decoded):** `username=alice' AND (SELECT CASE WHEN (1=1) THEN <E> ELSE 1 END) --&password=x` → resposta **demora ~3 s**.
- **Ramo FALSE — Body (decoded):** `username=alice' AND (SELECT CASE WHEN (1=2) THEN <E> ELSE 1 END) --&password=x` → resposta **instantânea**.
- **Por quê:** o `CASE` do SQLite só avalia o ramo que casou. `WHEN 1=1` ⇒ roda `E` (delay). `WHEN 1=2` ⇒ retorna `1` (sem CTE, sem delay). Agora o aluno tem os dois estados do oráculo, medidos no relógio: **lento = TRUE, rápido = FALSE**. Qualquer condição booleana que ele consiga expressar em SQL agora é respondível por um cronômetro.
- Esse passo é o gêmeo temporal do "estabelecer o oráculo TRUE/FALSE" do 06 — a `<pergunta>` ocupa o mesmo lugar; só o que **responde** mudou (latência, não texto).

### Step 3 — Extract the length by timing

Troca a `<pergunta>` por uma sobre dado real: o comprimento da senha.

- **Body (decoded, N variável):** `username=alice' AND (SELECT CASE WHEN ((SELECT LENGTH(password) FROM users WHERE username='alice') = N) THEN <E> ELSE 1 END) --&password=x`
- À mão no Repeater, 2–3 iterações para sentir o ritmo: `N=5` → rápido; `N=10` → **~3 s**; `N=15` → rápido. Conclusão: a senha tem **10** caracteres.
- Idêntico em espírito ao Step 4 do 06 — só que o "sim" agora é o relógio batendo ~3 s em vez do texto `Welcome`.

### Step 4 — Extract one character by timing

A `<pergunta>` mais fina: o caractere na posição `P` é o candidato `C`?

- **Body (decoded, P e C variáveis):** `username=alice' AND (SELECT CASE WHEN (SUBSTR((SELECT password FROM users WHERE username='alice'),P,1) = 'C') THEN <E> ELSE 1 END) --&password=x`
- À mão (primeiro char): `P=1, C='a'` → rápido (não é `a`); `P=1, C='w'` → **~3 s** (é `w`).
- Reforçar a distinção dos dois argumentos do `SUBSTR` (igual ao 06): o primeiro (`P`) é a **posição** (o que varia para varrer a senha); o segundo (`1`) é o **tamanho** (sempre 1, um char por vez). Essa distinção prepara a marcação de positions no Intruder.

### Step 5 — Automate with Burp Intruder, reading latency

**Este é o passo que mais reusa o átomo 06 — destacar isso explicitamente.** A mecânica do Intruder é **quase idêntica**; a *única* diferença é qual coluna lê o oráculo.

Request base (P=1, C=w marcados depois):

```
username=alice' OR ...   ← NÃO; usar a forma com AND/CASE do Step 4
username=alice' AND (SELECT CASE WHEN (SUBSTR((SELECT password FROM users WHERE username='alice'),§1§,1) = '§w§') THEN <E> ELSE 1 END) --&password=x
```

Configuração (idêntica ao 06, item a item, exceto o passo 6):

1. **Send to Intruder** a request do Repeater que funcionou.
2. **Marcar duas payload positions** com `§...§`: o `1` da **posição** do `SUBSTR` (varia 1→10) e o `w` candidato (varia a→z). **Não** marcar o `1` do *tamanho* do `SUBSTR` nem nenhum dígito do `<K>` do cross join — mesma armadilha do 06 (há vários dígitos literais no payload; marcar o errado quebra o ataque). Vale uma frase apontando os dígitos que **não** se marca.
3. **Attack type:** `Cluster bomb` (produto cartesiano posição × candidato).
4. **Payload set 1 (posição):** `Numbers`, de 1 a 10, step 1. (10 payloads.)
5. **Payload set 2 (candidato):** `Simple list`, as 26 letras minúsculas, uma por linha. (Mesma justificativa do 06: **não** usar `Brute forcer`, que explode em 26ⁿ.) Request count: **260** (10 × 26).
6. **AQUI ESTÁ A ÚNICA DIFERENÇA EM RELAÇÃO AO 06.** No 06, o oráculo era a coluna do **Grep — Match** (`Welcome, alice!`). Aqui **não há string para casar** — todas as 260 responses são byte-a-byte idênticas (`Login attempt processed.`). O oráculo é a **coluna de latência**: `Response received` (tempo até o primeiro byte, ms) ou `Response completed`. Pode ser preciso habilitá-la no menu de colunas da tabela de resultados (nomes iguais em Community e Pro). **Configurar o Resource Pool com Maximum concurrent requests = 1** (senão os payloads que queimam CPU competem e sujam o tempo).
7. **Start attack.** Ordenar pela coluna de latência, decrescente. Os **10 hits lentos** (~3 s cada) revelam, em ordem de posição, `w, o, n, d, e, r, l, a, n, d` → `wonderland`. Os outros 250 voltam em dezenas de ms.

Fechamento do passo: o ataque é, por natureza, **mais lento** que o do 06 (cada bit custa ~3 s no pior caso, e a concorrência é 1) — mas o resultado é o mesmo. O oráculo nunca esteve no body; estava no relógio.

### Why this is time-based — explicit contrast (fecha o walkthrough)

Parágrafo final amarrando a trilogia (referenciando 01 e 06, ambos publicados). Sugestão de conteúdo:

> No `sqli-union-basic` o dado vinha no body. No `sqli-blind-boolean` o body só dizia "sim/não", mas ainda dizia *algo*. Aqui o body não diz **nada** — é idêntico em toda resposta. Um dev achatou as mensagens para impedir enumeration (boa intenção) mas não corrigiu a injeção. O boolean oracle morreu; o atacante mediu o tempo. A mesma `<pergunta>` ("o char na posição P é C?") que o 06 respondia lendo texto, o 07 responde com um cronômetro. Mesma causa, mesmo fix, mesmo segredo (`wonderland`) — só o canal observável encolheu de novo, do conteúdo para o tempo.

---

## Dependências extras

```
Flask==3.0.0
```

Mesmas do átomo 06. `sqlite3` é stdlib. **Nada** mais — sem bcrypt (password é texto puro de propósito), sem `requests`, sem JWT, e em especial **nada para "medir tempo" no servidor**: o delay é construído no SQL, não em `time.sleep()` no Python (usar `time.sleep` seria trapaça — não demonstraria a injeção).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Vetor | Login com mensagem unificada (`POST /login`), **vetor (a)** | Contraste mais apertado possível com o 06 (mesma feature, oráculo de body removido). Realiza literalmente o cenário "response time" que o DIFF do 06 previu. Reusa o schema do 06 sem mudança. |
| Primitiva de delay | **Cross join de CTE pequeno** (`K` linhas → `K²` trabalho) | Memória limitada por **construção** (O(K), ~dezenas de KB), não por otimização version-specific. Medição: `randomblob` estouraria ~2,8 GB a ~3 s; o counting CTE só é O(1) graças a uma otimização que não dá pra garantir no SQLite ~3.40 do container. CPU-burn real contra SQLite sem `SLEEP()`. |
| Estrutura do payload | `alice' AND (SELECT CASE WHEN (<cond>) THEN <E> ELSE 1 END) --` | `CASE` dá o short-circuit (delay só no TRUE). `alice'` + índice `UNIQUE` garante avaliação **exatamente uma vez** (timing limpo), independente da ordem do plano. |
| Resposta da app | Uniforme (`Login attempt processed.`), HTTP 200 sempre | Mata o oráculo de body do 06 e força o canal de tempo. Eco deliberado da string nomeada no DIFF do 06. |
| Schema | Idêntico ao 06 (reuso byte a byte) | "Mesmo segredo, três formas de roubar." O aluno reconhece o cenário e foca no canal novo. |
| Alvo de extração | `users.password` da alice = `wonderland` (10 chars, `[a-z]`) | Paralelo ao 01/06. Curto p/ o walkthrough, longo p/ o Intruder valer a pena. Texto puro pela legibilidade; nota de "real seria hash". |
| `K` do cross join | ~3 s/request TRUE (confirmado); inicial `K≈12000–16000`, **calibrar**; tempo ∝ K² | Inequívoco contra misses (dezenas de ms), sem arrastar o Intruder. CPU-dependente — valor final fixado na geração. |
| Intruder | Hands-on, Cluster bomb idêntico ao 06, **oráculo = coluna de latência**, concorrência 1 | Coerência com o 06; a única coisa nova a aprender é "ler latência em vez de body". |
| Debug block (query renderizada) | **Ausente** (como no 06) | Mostrar a query destruiria a aula de blind. |

---

## Open questions — status após rodada 1 de review

**Resolvidas pelo mantenedor (rodada 1):**

1. **Delay-alvo ~3 s** — confirmado. Não encurtar p/ 2 s (margem de jitter apertada em máquina sob carga); não alongar p/ 5 s (10 hits lentos + overhead incomodam).
2. **Mensagem unificada `Login attempt processed.`** — manter. O callback verbatim à string nomeada no DIFF do 06 é o fecho do arco.
3. **`Try: alice / wonderland` no index** — manter, com a função de prova-de-premissa (ver "Moldura da trilha browser" no walkthrough).
4. **Charset Intruder `[a-z]`** — manter, alinhado ao 06.
5. **Step 1 com CTE puro (sem `CASE`)** — manter. Escalada mais suave ("primeiro só faço travar; depois faço o travamento depender de uma pergunta").

**Corrigida por medição (era a antiga OQ "OOM-safety do CTE"):**

6. **Primitiva de delay + perfil de memória.** Resolvida empiricamente (ver Seção técnica). A afirmação de O(1) do counting CTE da v1 era sutilmente frágil (dependia de uma otimização version-specific do SQLite), e a Opção B (`randomblob`) sugerida estouraria ~2,8 GB para chegar a ~3 s. Primitiva trocada para **cross join de CTE pequeno**, com teto de memória O(K) por construção. A tarefa de calibração deixou de ser "confirmar que é O(1)" e virou **"calibrar `K` para ~3 s medindo a RAM real do container, com teto < 200 MB"** — o cross join deve ficar muito abaixo (dezenas de KB); o teto é guarda-corpo, não expectativa.

**Bloqueante remanescente:** nenhuma. Todas as decisões estão fixadas; resta apenas calibrar `K` na fase de geração contra o container.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o "fim da linha" do blind — o 06 tirou o dado do body e deixou um bit; o 07 tira o próprio bit do body e o joga no relógio. Cada parágrafo do walkthrough deve poder ser lido com o `sqli-blind-boolean` aberto ao lado, e a diferença ("aqui o sinal é tempo, não texto") deve estar visível na linha em discussão.
- **Leitura obrigatória antes de gerar (Seção 10.5 do CLAUDE.md):** `sqli-blind-boolean` inteiro (predecessor imediato) e `sqli-union-basic` (abertura da trilogia). Reusar a forma do 06 para: nota de encoding do body, convenção de placeholder de leitura, blocos decoded/Burp-ready, estrutura do README/DIFF/WALKTHROUGH, esqueleto de `docker-compose.yml` e `Dockerfile`.
- **Não introduzir** bcrypt, sessões, CSRF, flash messages, JWT, nem `time.sleep()` no Python. O delay é **SQL**, não servidor. Se sentir vontade de "consertar" o login, pare — não é este átomo.
- **`result.html` é uniforme e idêntico em vulnerable e fixed.** Sem condicional Jinja, sem variável de contexto. A ausência de string discriminante é a feature — não reintroduzir variação por outcome em refatoração.
- **Manter `.fetchone()` em ambas as versões** (resultado ignorado, com comentário). É o que força a avaliação do `WHERE`/CTE e dispara o delay; sem ele o timing fica não-confiável.
- **Calibrar `K` contra o container** e **documentar o valor final** no DIFF e no WALKTHROUGH. Validar que: (a) uma request TRUE leva ~3 s, (b) uma FALSE volta em dezenas de ms, (c) a RAM do container fica **abaixo de 200 MB** durante um probe TRUE (o cross join deve ficar em dezenas de KB — medir, não assumir), (d) contra a versão **fixed**, **todas** as requests (inclusive o probe incondicional do Step 1) voltam instantâneas.
- **Walkthrough Intruder:** descrever menus do Burp Community Edition (Cluster bomb, Numbers, Simple list existem nas duas edições). A coluna de latência (`Response received` / `Response completed`) pode precisar ser habilitada no menu de colunas; o Resource Pool com concorrência 1 é obrigatório para timing limpo. Se houver dúvida sobre o nome exato de uma aba/coluna na versão atual do Burp, **perguntar antes de inventar**.
- **Cross-atom reference policy:** OK referenciar `sqli-union-basic` e `sqli-blind-boolean` (publicados em `main`); **proibido** referenciar `xss-stored`, `command-injection-basic` ou qualquer átomo da Fase 2+ ainda não publicado. Foreshadowing vira generalização da lição ou link à PortSwigger Academy (Seção 5 do CLAUDE.md).
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF), padrão v0.1.0.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md`, linkando `https://portswigger.net/web-security/sql-injection/blind` com o título `Blind SQL injection` preservado em inglês também no PT; sugerir foco na seção de time delays.
- **`docker-compose.yml`:** `127.0.0.1:8007:5000` (vulnerable), `127.0.0.1:8107:5000` (fixed). Reaproveitar o esqueleto do 06.
- **CHANGELOG.md:** ao gerar o átomo, adicionar entrada em `[Unreleased] / Added` no mesmo padrão da linha do átomo 06.
- **Validar manualmente os cinco passos** na versão vulnerable (delays nos lugares certos) e a sua falha na versão fixed (tudo instantâneo).
