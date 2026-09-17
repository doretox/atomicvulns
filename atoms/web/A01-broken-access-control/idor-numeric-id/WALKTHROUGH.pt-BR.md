# Walkthrough — idor-numeric-id

## 1. Contexto

A app expõe uma feature pequena de "notas privadas". A home page te diz como qual usuário você está logado e te dá um link pra sua própria nota; clicar dispara `GET /notes/1` e o servidor renderiza o corpo da nota num bloco HTML simples. Três usuários no seed: alice (id 1), bob (id 2), carol (id 3). Cada um possui exatamente uma nota, e os IDs das notas calham de bater com os IDs dos donos (1, 2, 3) — isso é conveniência do seed, não uma propriedade da qual a app dependa.

Este é o primeiro átomo do projeto que **não é input-driven**. Em `sqli-union-basic` e `xss-reflected` você construiu um payload — um fragmento de SQL, uma tag HTML — e o servidor o tratou mal. Aqui não tem payload. O "exploit" é mudar um número numa URL de `1` pra `2`. A vulnerabilidade não está em como a app *processa* input; está em código que a app *nunca escreveu* — o check ausente de que a nota requisitada de fato pertence a você.

Acostume-se com essa forma. Uma fração grande dos achados de IDOR/BOLA em bug bounty é exatamente isto: o request é bem-formado, o input é legítimo, a app obedientemente devolve dados que o caller não tinha por que estar lendo.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/notes/<id>` é curta:

```python
@app.route("/notes/<int:note_id>")
def view_note(note_id):
    note = next((n for n in NOTES if n["id"] == note_id), None)
    if note is None:
        abort(404)
    # VULNERABLE: no ownership check — any caller can view any note by id.
    return render_template("note.html", note=note)
```

Leia duas vezes. Nada concatena input de usuário num sink perigoso. Não tem filter de template fazendo coisa arriscada. A função procura uma nota por primary key e devolve. O bug é **o que não está lá**: nenhuma comparação entre `note["owner_id"]` e o id do usuário que chamou. A função confia que "se você pediu a nota N, você tem direito de ver a nota N" — e essa suposição é exatamente o que o atacante quebra.

Duas coisas pra internalizar dessa forma:

- **`grep` pelas keywords que aparecem em bugs de injection (`f"`, `%s`, `|safe`, `Markup`, `eval`) não acha IDOR.** Esta classe aparece como a *ausência* de código, e ausência não dá grep. Auditoria aqui é por traço de request: escolha um endpoint que retorna dado escopado a usuário, pergunte "onde está o ownership check", e se a resposta é "em lugar nenhum", você tem um achado.
- **O fix é um único check explícito no servidor.** Não é "trocar inteiro por UUID", não é "rate-limit", não é "tirar o ID da URL". Isso é obfuscation. Segura a regra: **o servidor tem que verificar, em todo request, que o caller tem direito ao objeto requisitado.**

## 3. Como funciona a "auth" deste lab

Auth de verdade (form de login, session cookie, password hashing) está fora do escopo de um lab de IDOR — triplicaria o tamanho do código e ensinaria outra lição.

Aqui simulamos com um único header: **`X-User-ID`**. Qualquer inteiro que o cliente mandar, a app trata como "o usuário logado". Se o header está ausente, a app default-a pra `1` pra a UI ser clicável sem você configurar nada.

Duas consequências pra ter em mente antes de começar a explorar:

- **O header é auto-declarado.** Nada impede você de dizer que é o user `2` ou `99`. Numa app de verdade isso seria outro bug (broken authentication) — mas aqui a gente nem fingiu verificar identidade. A "session" é o que você disser que é.
- **Se a app *usa* essa identidade declarada pra autorização é uma pergunta diferente.** A versão vulnerable lê `X-User-ID` na home page (pra te cumprimentar pelo nome) mas ignora dentro de `/notes/<id>`. É aí que está o bug. O Passo 4 abaixo torna a distinção concreta.

## 4. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8003/>, clique em **View my note**, depois em **Proxy → HTTP history** ache o request `GET /notes/1` e **Send to Repeater**.

O browser não envia `X-User-ID` sozinho (não é um header padrão). O default em `app.py` faz a app se comportar como se você tivesse mandado `X-User-ID: 1`. Pra deixar todo request explícito e fácil de variar nos passos abaixo, **adicione o header manualmente no Repeater** na primeira vez:

```
X-User-ID: 1
```

Agora todo request que sair desta aba do Repeater carrega o header explicitamente, e você consegue editá-lo como qualquer outra linha.

Diferente de SQL injection ou XSS, **nenhum dos passos abaixo usa URL encoding ou caracteres especiais** — você está mudando inteiros numa URL e um inteiro num header. Só isso. Se estiver pensando em `%20` ou backslashes aqui, está pensando demais.

### Passo 1 — Ler sua própria nota

Request line no Repeater:

```
GET /notes/1 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 1
```

Response: status 200, página renderiza a nota da alice ("Bank PIN: 4231"). A response também mostra `Note id: 1 · Owner id: 1`, então você consegue ver de quem o registro é. Este é o seu baseline — o request legítimo, exatamente como a feature foi desenhada.

### Passo 2 — Ler a nota de outra pessoa

Mude um caractere na request line: `1` → `2`. Não mexa no header.

```
GET /notes/2 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 1
```

Response: status 200, a página renderiza a nota do bob ("Confidential meeting Friday 2pm"). O painel da response confirma `Owner id: 2` — você, dizendo ser o user 1, acabou de ler conteúdo do user 2. Isso é o IDOR. O servidor devolveu o dado porque nada no caminho do código proíbe.

Pausa um segundo. O request é *válido* por toda regra de protocolo: linha bem-formada, path válido, inteiro válido, todos os headers em ordem. Uma WAF que olha "input malicioso" não vê nada. Authentication "passou" (na medida em que existe). Authorization nunca foi consultada. É por isso que IDOR é tão comum em bug bounty — o request parece bom.

### Passo 3 — Confirmar o padrão

```
GET /notes/3 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 1
```

Response: nota da carol ("Credit card ending in 8821"). Mais um ponto de dado mostrando que o bug não é específico do bob — é universal. Qualquer note id no seed é alcançável a partir de qualquer caller.

Num engagement real, este é o passo onde você escreve o finding: enumera o range, captura três ou quatro reads cross-user pra estabelecer o padrão, e para. Você não precisa ler todas as notas do banco pra provar o bug — três bastam.

### Passo 4 — Provar que o bug é "check ausente", não "identity errada"

Agora mantenha o path em `/notes/1` (a nota da alice) e mude *só o header* pra dizer que é outro user:

```
GET /notes/1 HTTP/1.1
Host: 127.0.0.1:8003
X-User-ID: 2
```

Response: status 200, nota da alice de novo. Owner id: 1. **Nada na response mudou quando você "virou bob".**

Sente nessa um pouco. Se o bug fosse "a app confia na identidade declarada do caller pra autorização", então mudar `X-User-ID` de `1` pra `2` deveria mudar *alguma coisa* — outra nota, outro erro, qualquer coisa diferente. Não muda, porque a view `/notes/<id>` nunca lê o header. Não tem o que spoofar. O "fix" não é "validar o header melhor"; o header nunca fez parte da decisão.

O bug é precisamente: **a decisão de autorização está ausente**, não "a decisão de autorização usa inputs ruins". Um check correto no server-side (ver seção 5) lê o id do caller, compara com `note["owner_id"]` e rejeita as divergências. Se o caller é honesto sobre a identidade dele é uma preocupação separada (e um átomo separado).

## 5. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança. Em resumo, a view `/notes/<id>` corrigida lê `X-User-ID` e compara com `note["owner_id"]` antes de devolver a nota — se não baterem, o request é rejeitado com `403 Forbidden`:

```python
user_id = request.headers.get("X-User-ID", "1")
note = next((n for n in NOTES if n["id"] == note_id), None)
if note is None:
    abort(404)
if str(note["owner_id"]) != user_id:
    abort(403)
return render_template("note.html", note=note)
```

Replay todo request da seção 4 contra <http://127.0.0.1:8103/>:

- Passo 1 (`/notes/1` com `X-User-ID: 1`): 200, sua nota.
- Passo 2 (`/notes/2` com `X-User-ID: 1`): **403 Forbidden**.
- Passo 3 (`/notes/3` com `X-User-ID: 1`): **403 Forbidden**.
- Passo 4 (`/notes/1` com `X-User-ID: 2`): **403 Forbidden**.

Olha o que o fix *não* faz: não muda os IDs de inteiros pra UUIDs, não esconde eles da URL, não adiciona token, não faz rate-limit. Nada disso é autorização — é obfuscation. A única linha que importa é a comparação explícita; todo o resto é teatro.
