# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py` para a view `/notes/<id>`:

```diff
 @app.route("/notes/<int:note_id>")
 def view_note(note_id):
+    user_id = request.headers.get("X-User-ID", "1")
     note = next((n for n in NOTES if n["id"] == note_id), None)
     if note is None:
         abort(404)
-    # VULNERABLE: no ownership check — any caller can view any note by id.
+    if str(note["owner_id"]) != user_id:
+        abort(403)
     return render_template("note.html", note=note)
```

Os templates e a view da home page são idênticos nas duas versões — o bug vive inteiramente no check ausente dentro de `view_note`.

## O que mudou

Duas linhas de lógica foram adicionadas na versão fixed:

- `user_id = request.headers.get("X-User-ID", "1")` — puxa a identidade declarada do caller a partir do request, com o mesmo default que a home page usa.
- `if str(note["owner_id"]) != user_id: abort(403)` — o ownership check explícito. `note["owner_id"]` é inteiro no seed e `user_id` veio do header como string, então a comparação faz cast pra um tipo comum. Um codebase real normalizaria os tipos mais acima; o cast aparece inline aqui pra a comparação ficar visível num único lugar.

O comentário `# VULNERABLE` foi apagado porque a linha que ele descrevia não existe mais.

## Por que isso resolve

Olha o que *não* está no diff. Os IDs continuam numéricos e continuam incrementando. A URL continua sendo `/notes/1`, `/notes/2`, `/notes/3`. A tabela de notas é a mesma. O header continua sendo auto-declarado. Nada disso é o fix — e nada disso precisava mudar.

O fix é um único conditional. A classe da vulnerabilidade é "o servidor devolve um objeto escopado a usuário sem checar se o caller é o dono". A remediação é exatamente a negação: "o servidor devolve um objeto escopado a usuário só depois de checar que o caller é o dono". Qualquer outra coisa — UUIDs, signed tokens, URLs escondidas, rate limits — deixa esse conditional ausente e só muda quanto custa *achar* o bug.

## Contraste com `sqli-union-basic` e `xss-reflected`

Nos dois átomos anteriores, o bug era uma única linha de código *ruim*: a SQL via f-string, o filter `|safe`. Remover ou trocar essa linha era o fix. Aqui não tem linha ruim pra remover — o fix é *adicionar* código que deveria estar lá. É por isso que auditoria por grep acha bugs de injection mas perde os de access control: não tem string-pista pra procurar. IDOR você acha lendo endpoints e perguntando, pra cada um que retorna dado escopado a usuário, "onde este código verifica ownership?" Quando a resposta é "em lugar nenhum", o achado está bem na sua frente.
