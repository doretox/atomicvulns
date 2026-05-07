# Spec — Átomo 01: `sqli-union-basic`

> Documento de especificação para o Claude Code implementar o primeiro átomo do projeto `atomicvulns`. Leia junto com `CLAUDE.md` (Seções 3.3, 5, 8) e `ROADMAP.md`.

*Nota histórica: esta spec foi escrita quando o template do walkthrough incluía a seção "Try it yourself". Essa seção foi posteriormente removida do projeto. O conteúdo abaixo é preservado como referência histórica e não reflete o template atual.*

---

## Identidade

- **ID:** `sqli-union-basic`
- **Categoria OWASP:** A03 — Injection
- **Pasta:** `atoms/A03-injection/sqli-union-basic/`
- **Número sequencial:** 01
- **Porta vulnerable:** `127.0.0.1:8001`
- **Porta fixed:** `127.0.0.1:8101`

---

## Classe de vulnerabilidade

UNION-based SQL injection clássica. Input não sanitizado concatenado em query SQL permite ao atacante sobrepor uma segunda `SELECT` via `UNION`, exfiltrando dados de outras tabelas acessíveis ao mesmo DB connection.

---

## Feature simulada

**Perfil público de usuário.**

Endpoint `GET /profile?username=<nome>` retorna dados públicos do usuário informado: nome de exibição, bio, e data de cadastro. A página exibe os resultados em uma tabela simples.

**Observação didática (só na versão vulnerable):** a página renderizada mostra também a query SQL executada, como um "bloco de debug", pra o aluno visualizar o que seu input virou no back-end. Esse bloco não existe na versão fixed.

---

## Schema do banco (SQLite)

Duas tabelas. Banco em arquivo `lab.db`, recriado no startup via script `seed.py` (idempotente).

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    bio TEXT NOT NULL,
    joined_at TEXT NOT NULL
);

CREATE TABLE secrets (
    user_id INTEGER NOT NULL,
    password_hash TEXT NOT NULL,
    api_key TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Dados de seed

```sql
INSERT INTO users (username, bio, joined_at) VALUES
    ('alice', 'Coffee lover and trail runner.', '2023-01-15'),
    ('bob',   'Full-time dad, part-time sysadmin.', '2023-04-02'),
    ('carol', 'Building things on the internet.', '2023-09-20');

INSERT INTO secrets (user_id, password_hash, api_key) VALUES
    (1, '$2b$12$fakehashfakehashfakehashfakeha', 'sk_test_alice_fakekey_aaaa1111'),
    (2, '$2b$12$otherhashotherhashotherhashoth', 'sk_test_bob_fakekey_bbbb2222'),
    (3, '$2b$12$carolhashcarolhashcarolhashcar', 'sk_test_carol_fakekey_cccc3333');
```

**Importante:** os hashes e API keys são **fake óbvios**. Sem risco de confundir com credencial real. Mantenha esse padrão — prefixo `sk_test_`, palavras repetidas no hash.

---

## Rotas da aplicação

### `GET /`

Página inicial. Contém:
- Banner de aviso (`⚠️ Intentionally vulnerable...`)
- Formulário curto com `<input name="username">` e botão "View profile"
- Lista de usuários disponíveis ("Try: alice, bob, carol")
- Rodapé com a dica do Burp

### `GET /profile?username=<nome>`

Endpoint vulnerável. Pseudocódigo da view:

```python
@app.route('/profile')
def profile():
    username = request.args.get('username', '')
    query = f"SELECT username, bio, joined_at FROM users WHERE username = '{username}'"
    rows = get_db().execute(query).fetchall()
    return render_template('profile.html', rows=rows, query=query, username=username)
```

**Na versão `fixed/`:**

```python
@app.route('/profile')
def profile():
    username = request.args.get('username', '')
    rows = get_db().execute(
        "SELECT username, bio, joined_at FROM users WHERE username = ?",
        (username,)
    ).fetchall()
    return render_template('profile.html', rows=rows, username=username)
```

Note: na versão fixed, a query **não** é passada pro template (não há bloco de debug).

---

## HTML (respeitando Seção 3.3 do CLAUDE.md)

Três arquivos no máximo, ≤40 linhas cada:

### `templates/index.html`

- Banner de aviso no topo
- Título curto: "User Profile Lookup"
- Form GET com input `username`
- Uma linha: `Try: alice, bob, carol`
- Rodapé com a dica do Burp

### `templates/profile.html`

- Banner de aviso no topo
- Tabela com colunas `username | bio | joined_at` e uma linha por `row` em `rows`
- **Só na versão vulnerable:** abaixo da tabela, um `<pre>` com label `Executed query:` e o valor de `{{ query }}`. Esse bloco é o insight didático — o aluno vê sua própria injection renderizada.
- Link "← Back" pra `/`
- Rodapé com a dica do Burp

### CSS

Até 5 linhas no `<style>` inline, em cada template. Apenas `body { font-family: sans-serif; max-width: 720px; margin: 2em auto; padding: 0 1em; }` e um retoque no `<pre>` (background cinza claro, padding, border-radius pequeno). Nada mais.

---

## Walkthrough — estrutura obrigatória

O `WALKTHROUGH.md` tem esta estrutura (replicada em `WALKTHROUGH.pt-BR.md`):

### Seção 1 — Context (2-3 frases)

O que a app faz, qual feature o aluno explora.

### Seção 2 — Spot the bug (1 parágrafo + snippet)

Mostra a linha vulnerável (`query = f"... WHERE username = '{username}'"`) e explica por que é falha. Não revela ainda como explorar — o aluno deve conseguir adivinhar.

### Seção 3 — Exploitation via Burp Suite (trilha principal)

Três passos didáticos, cada um com request bruto e response relevante:

#### Step 1 — Confirm the injection point

- Request: `GET /profile?username=alice' -- HTTP/1.1`
- Observação: a app ainda retorna Alice normalmente; o bloco "Executed query" revela que o `'` virou parte da SQL e o `--` comentou o resto. Confirma que input vira código.

#### Step 2 — Determine column count and displayed columns

- Request: `GET /profile?username=x' UNION SELECT '1','2','3' -- HTTP/1.1`
- Observação: a tabela agora mostra uma linha com `1 | 2 | 3`. O aluno confirma: 3 colunas, todas renderizadas. Se tentasse `UNION SELECT '1','2'`, a query falharia (mostrar isso como experiência opcional).

#### Step 3 — Exfiltrate data from another table

- Request: `GET /profile?username=x' UNION SELECT users.username, secrets.password_hash, secrets.api_key FROM users JOIN secrets ON users.id = secrets.user_id -- HTTP/1.1`
- Observação: a tabela mostra três linhas — username de cada user, password hash, API key. Impacto total.
- Nota didática: aqui é onde o aluno vê o pulo de "ver meu próprio perfil" pra "vazar credenciais de todo mundo".

Cada step mostra o request completo (método, path com querystring url-encoded, Host header) e a parte relevante da response (a linha da tabela renderizada). Screenshots do Burp Repeater são bem-vindos mas opcionais.

### Seção 4 — Exploitation via browser (trilha secundária, opcional)

Mesmos três payloads, mas colados na barra de endereços ou no campo do form. Útil pra quem não tem Burp ainda.

### Seção 5 — Why the fix works (1 parágrafo + diff de 2 linhas)

Aponta pro `DIFF.md` e resume: parâmetro vinculado trata input como dado, nunca como código. O driver SQLite sabe disso; concat de string não.

### Seção 6 — Try it yourself (3-4 variações)

Pequenos desafios pra fixar:
- E se a app usasse `"` em vez de `'` ao redor do input? (resposta: trocar aspas no payload)
- E se só 2 colunas fossem renderizadas? (resposta: ajustar o UNION)
- Como descobrir o nome da tabela `secrets` sem saber de antemão? (resposta: `UNION SELECT name, null, null FROM sqlite_master WHERE type='table' --` — introduz metadata do SQLite)

---

## DIFF.md — estrutura

Título: `DIFF — vulnerable vs. fixed`

Bloco de diff unificado real entre os dois `app.py`:

```diff
 @app.route('/profile')
 def profile():
     username = request.args.get('username', '')
-    query = f"SELECT username, bio, joined_at FROM users WHERE username = '{username}'"
-    rows = get_db().execute(query).fetchall()
-    return render_template('profile.html', rows=rows, query=query, username=username)
+    rows = get_db().execute(
+        "SELECT username, bio, joined_at FROM users WHERE username = ?",
+        (username,)
+    ).fetchall()
+    return render_template('profile.html', rows=rows, username=username)
```

Depois, dois parágrafos curtos:

1. **O que mudou no código.** Troca de f-string concat por placeholder `?` com tuple de parâmetros.
2. **Por que isso resolve.** O driver SQLite, ao ver `?`, trata o valor como dado literal independente de conter `'`, `--`, `UNION` ou qualquer coisa. A SQL é parseada *antes* do valor ser substituído; não há como o input escapar da string literal pra virar código.

Remover também `query=query` do context do template e o bloco "Executed query" do `profile.html` na versão fixed.

---

## README.md do átomo — estrutura

Curto, ~20 linhas:

- Banner de aviso
- Título: "sqli-union-basic — UNION-based SQL Injection"
- Parágrafo único descrevendo o átomo
- Seção "Run": `./atom up sqli-union-basic` → navegar pra `http://127.0.0.1:8001`
- Seção "What to read next": lista pra `WALKTHROUGH.md` e `DIFF.md`
- Seção "Fixed version": roda em `http://127.0.0.1:8101` com o mesmo walkthrough não funcionando

Mesma estrutura em `README.pt-BR.md`.

---

## Dockerfile e docker-compose.yml

### `docker-compose.yml`

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8001:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8101:5000"
```

### Dockerfile (idêntico pros dois, exceto o diretório fonte)

Base `python:3.11-slim`, copia `requirements.txt`, instala, copia app, roda `python app.py`. Roda seed no startup (o `app.py` chama `init_db()` se `lab.db` não existir).

### `requirements.txt`

```
Flask==3.0.0
```

Só isso. Sem Flask-SQLAlchemy, sem nada extra. `sqlite3` é stdlib.

---

## Checklist de entrega (o Claude Code deve validar antes de dar por pronto)

- [ ] Estrutura de pastas exatamente como Seção 5 do CLAUDE.md.
- [ ] `app.py` vulnerável ≤30 linhas (excluindo o `init_db`).
- [ ] `app.py` fixed ≤30 linhas.
- [ ] HTML ≤40 linhas por template.
- [ ] CSS ≤5 linhas inline.
- [ ] Banner de aviso em todo HTML e todo README.
- [ ] Portas bindam em `127.0.0.1`.
- [ ] `WALKTHROUGH.md` tem as 6 seções acima, trilha Burp como principal.
- [ ] `WALKTHROUGH.pt-BR.md` sincronizado 1:1 com o inglês.
- [ ] `DIFF.md` e `DIFF.pt-BR.md` sincronizados.
- [ ] `README.md` e `README.pt-BR.md` do átomo sincronizados.
- [ ] `requirements.txt` tem apenas Flask.
- [ ] Seed do banco é idempotente (não quebra se `lab.db` já existe).
- [ ] Os três payloads do walkthrough funcionam na versão vulnerable.
- [ ] Os três payloads do walkthrough **falham** na versão fixed.

---

## Notas pro Claude Code

1. **Não inventar.** Siga esta spec literalmente. Se algo estiver ambíguo, perguntar em vez de improvisar.
2. **Não adicionar "extras" bem-intencionados.** Nada de login, flash messages, logging, ORM, blueprints. O átomo é intencionalmente minimalista.
3. **Comentários no código em inglês, curtos e apenas onde agregam.** Evite comentários redundantes. Um comentário bem colocado na linha da vulnerabilidade em `vulnerable/app.py` é bem-vindo (ex: `# VULNERABLE: user input concatenated into SQL string`).
4. **Ao final, propor marcação no `ROADMAP.md`:** mover átomo 01 de `[ ]` para `[x]` após validação manual do mantenedor.
