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

## 3. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8006/>, faça login com `alice / wonderland` uma vez pra capturar o tráfego, depois clique com o botão direito no request `POST /login` em **Proxy → HTTP history** e escolha **Send to Repeater**.

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

Sai de "demonstrar o oracle" e entra em *usar* ele. Embute uma subquery que pergunta algo concreto sobre dado real:

Body (decoded, N variável):

```
username=nobody' OR (SELECT LENGTH(password) FROM users WHERE username='alice') = N --&password=x
```

Pra cada valor de N que você testa, a subquery retorna o comprimento real da senha da alice, a comparação é verdadeira só quando N casa, e o oracle pisca de acordo. Rode manualmente algumas vezes no Repeater:

- `N = 5` → `Invalid credentials.`
- `N = 10` → `Welcome, alice!`
- `N = 15` → `Invalid credentials.`

Conclusão: a senha da alice tem 10 caracteres. Você descobriu um fato sobre um dado que não consegue ler diretamente, lendo um bit por request.

Um atacante real automatizaria isso com Intruder (uma posição, payload set `Numbers` de 1 a 20), mas fazer duas ou três iterações na mão aqui é o suficiente pra sentir o ritmo antes do próximo passo aumentar a escala.

### Passo 5 — Extrair caracteres e automatizar com Burp Intruder

Mesmo truque, pergunta mais fina. Em vez de perguntar "o comprimento é N?", pergunta "o caractere na posição P é igual a C?".

Body (decoded, P = posição, C = caractere candidato):

```
username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),P,1) = 'C' --&password=x
```

Demonstre o primeiro caractere na mão no Repeater. Substitua P=1 e teste um candidato:

- P=1, C=`a` → `Invalid credentials.`
- P=1, C=`w` → `Welcome, alice!` → o primeiro caractere é `w`.

Fazer isso na mão pra todas as 10 posições × 26 letras seria 260 requests. É pra isso que existe o Intruder.

**Configure o Intruder** (os passos abaixo usam nomes de menu do Burp Community; no Pro são idênticos):

1. **Send to Intruder.** Clique com botão direito no request que funcionou no Repeater e escolha **Send to Intruder**. Vá pra aba Intruder.
2. **Marque duas payload positions** no body do request com `§...§`:
   - O `1` dentro de `,1,` (a posição P).
   - O `'w'` que você acabou de usar (o candidato C). Marque só a letra, não as aspas em volta.

   O body deve ficar assim:

   ```
   username=nobody' OR SUBSTR((SELECT password FROM users WHERE username='alice'),§1§,1) = '§w§' --&password=x
   ```

3. **Attack type:** `Cluster bomb`. Itera o produto cartesiano dos dois payload sets — toda posição combinada com todo candidato.
4. **Payload set 1 (a posição `§1§`):** type `Numbers`, de `1` a `10`, step `1`.
5. **Payload set 2 (o candidato `§w§`):** type `Brute forcer`, character set `abcdefghijklmnopqrstuvwxyz`, length `1`. (O seed usa só letras minúsculas — um atacante real tipicamente ampliaria pra `[a-zA-Z0-9]` ou printable ASCII e aceitaria mais requests.)
6. **Grep — Match.** Em **Settings** dentro da aba do Intruder (ou **Options** em versões mais antigas do Burp), encontre a seção **Grep — Match** e adicione a string literal `Welcome, alice!`. Quando o ataque rodar, o Intruder vai mostrar uma coluna de checkbox em cada request — exatamente o oracle binário, exposto como uma coluna ordenável.
7. **Start attack.** Com 10 posições × 26 letras = 260 requests, o ataque termina em segundos contra uma app local.

Ordene os resultados pela coluna `Welcome, alice!`. Você fica com 10 matches, um por posição. Lê eles em ordem de posição:

```
1: w
2: o
3: n
4: d
5: e
6: r
7: l
8: a
9: n
10: d
```

Concatenado: `wonderland`. Essa é a senha armazenada da alice, recuperada sem ela jamais aparecer em uma única response body.

### Por que isso é "blind" — contraste explícito com sqli-union-basic

A causa do bug é idêntica nos dois átomos: input do usuário concatenado em string SQL sem parameter binding. O que difere é o que o atacante consegue ver e portanto a *forma* do exploit.

Em `sqli-union-basic` o canal de exfil é o próprio response body: `UNION` anexa linhas extras, o template renderiza toda coluna retornada, o atacante lê o dado direto da página. O trabalho cabe em três payloads porque cada um retorna o dado em si.

Aqui não há canal de dado. O body tem exatamente duas formas: `Welcome` ou `Invalid`. O atacante inverte o problema — em vez de pedir "me devolva o dado", ele pergunta ao banco "o dado *é igual a* esse candidato?", e usa os dois estados observáveis da response como um único bit. 260 bits de perguntas cuidadosamente escolhidas depois, a senha está reconstruída. Mesmo bug, canal mais estreito, mais requests, mesmo desfecho.

Uma nota de mundo real enquanto estamos no assunto: apps de verdade armazenam senhas como hash, não em texto puro. A técnica blind acima funciona do mesmo jeito contra uma coluna de hash — você estaria extraindo `$2b$12$...` em vez de `wonderland`, o que leva bem mais requests (charset mais largo e string mais longa). A técnica é o que generaliza; a coluna que você está lendo é detalhe deste lab específico.

## 4. Exploração via browser (trilha secundária, opcional)

Os passos 1, 2 e 3 são práticos de rodar pelo browser se você ainda não tem o Burp configurado — abra <http://127.0.0.1:8006/>, cole a forma *decoded* de cada payload no campo username, digite qualquer coisa no password, submeta, leia a página resultante:

1. `alice' --` → `Welcome, alice!`
2. `nobody' OR '1'='1` (quebrado) → `Invalid credentials.`; depois `nobody' OR '1'='1' --` (consertado) → `Welcome, alice!`
3. `nobody' OR 1=2 --` → `Invalid credentials.`

Use essa trilha pra primeira leitura, pra *sentir* o oracle piscando entre os dois estados com seus próprios cliques.

A partir do Passo 4, o browser para de ser prático. O Passo 4 te faz iterar um número contra o mesmo payload, e o Passo 5 precisa de centenas de requests espalhados em duas payload positions — isso é trabalho de Repeater e Intruder. Passe pro Burp depois que o oracle clicar.

## 5. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança. Em resumo: a versão fixed chama `conn.execute("... WHERE username = ? AND password = ?", (username, password))`. Com placeholders, o driver do SQLite faz o parse do statement primeiro — sem os valores dos parâmetros — e só depois liga cada input como valor literal dentro do statement já parseado. Nenhum caractere de nenhum dos dois inputs consegue deslocar o parse: `'`, `--`, `OR`, `SELECT`, parênteses, newlines, tudo permanece nos seus respectivos slots de string literal e nunca é reinterpretado como sintaxe SQL.

Rode qualquer payload da seção 3 contra <http://127.0.0.1:8106/login>. Todos retornam `Invalid credentials.` — inclusive o login bypass do Passo 1, que contra a versão vulnerable era passe livre. As duas strings de response não mudaram; essa assimetria é comportamento legítimo de login, não é o bug. O que o atacante perdeu foi qualquer capacidade de injetar uma condição que empurraria a response pra `Welcome`. O oracle continua existindo; o atacante não controla mais ele.
