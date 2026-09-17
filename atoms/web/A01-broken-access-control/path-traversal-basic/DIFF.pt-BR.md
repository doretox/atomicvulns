# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py` para a view `/view`:

```diff
     filename = request.args.get("file", "")
-    # VULNERABLE: user input joined onto the base dir and opened directly —
-    # nothing confines the resolved path to BASE_DIR
-    path = os.path.join(BASE_DIR, filename)
+    # FIXED: resolve the real path, then confirm it stays inside BASE_DIR
+    base = os.path.realpath(BASE_DIR)
+    path = os.path.realpath(os.path.join(base, filename))
+    if not path.startswith(base + os.sep):
+        abort(404)
     try:
         with open(path) as f:
             content = f.read()
     except OSError:
         # missing/unreadable file: operational hygiene, orthogonal to the
         # vuln and the fix, identical in both versions
         abort(404)
-    return render_template("result.html", filename=filename, path=path, content=content)
+    return render_template("result.html", filename=filename, content=content)
```

O `fixed/templates/result.html` também larga o echo "Resolved path" (`<pre>{{ path }}</pre>`) — mudança incidental, do mesmo jeito que a versão fixed do `command-injection-basic` larga o echo "Executed command". Repare no que *não* muda: o `try/except OSError: abort(404)` e a linha `with open(path)` são idênticos nas duas versões (aparecem como contexto inalterado no diff), então a única mudança relevante pra segurança é o confinamento do caminho resolvido.

## O que mudou

O `os.path.join(BASE_DIR, filename)` + `open()` cru — que abria qualquer caminho que o input resolvia — foi trocado por um passo resolve-então-confirma:

- `base = os.path.realpath(BASE_DIR)` — a forma canônica e absoluta do diretório permitido.
- `path = os.path.realpath(os.path.join(base, filename))` — a forma canônica do caminho *requisitado*, com todo `../` colapsado e qualquer componente absoluto resolvido.
- `if not path.startswith(base + os.sep): abort(404)` — o containment check: a menos que o caminho resolvido caia dentro de `base`, recuse.

A versão vulnerable também ecoava o caminho montado na página; isso some na versão fixed, que não tem um caminho não-confinado que valha mostrar.

## Por que isso resolve

O `os.path.realpath` faz o trabalho que a versão vulnerable pulou: ele *resolve* o caminho. `../../../../etc/passwd` colapsa pra `/etc/passwd`; o `/etc/passwd` absoluto resolve pra `/etc/passwd`; `../app.py` colapsa pra `/app/app.py`. Não importa que truque o input usou pra apontar pra fora da pasta, depois do `realpath` você está olhando pro único arquivo real que ele nomeia. O prefix check então faz a única pergunta que importa — *esse arquivo está dentro do diretório que eu tenho permissão de servir?* — e recusa quando não está. Tanto o vetor relativo quanto o absoluto do walkthrough resolvem pra `/etc/passwd`, que não está sob `/app/files/`, então os dois levam o mesmo `abort(404)`. Um check, toda rota fechada.

Dois detalhes que se pagam:

- **`realpath`, não `abspath`.** O `os.path.abspath` colapsa `..` lexicalmente mas não segue symlinks; o `os.path.realpath` resolve symlinks também, fechando um escape via symlink dentro da base. Pra este lab qualquer um dos dois barraria os payloads, mas `realpath` é o default robusto.
- **`base + os.sep`, não só `base`.** Checar `path.startswith(base)` sozinho aceitaria errado um diretório irmão: com `base = /app/files`, a string `/app/files-secret/x` *começa* com `/app/files`. Anexar o separador (`/app/files/`) faz o check significar "dentro deste diretório" em vez de "compartilha este prefixo". (`os.path.commonpath([base, path]) == base` é um jeito ainda mais robusto de expressar a mesma intenção.)

Ele retorna **404**, não 403 — e diferente do `idor-numeric-id`, que retorna **403** pra um objeto real que o caller não pode acessar, essa diferença é proposital. Aqui um traversal rejeitado e um arquivo in-base genuinamente inexistente (um typo tipo `nope.txt`) retornam ambos 404, então os dois modos de falha ficam indistinguíveis: o atacante não consegue usar o status code pra mapear quais caminhos escapam do sandbox versus quais simplesmente não existem. 403 confirmaria existência; 404 não confirma nada.

## Blocklistar `../` é jogo perdido

Um "fix" tentador é rejeitar ou remover a sequência perigosa — apagar `../` do input. O Passo 2 do walkthrough já mostra por que isso falha: o caminho absoluto `/etc/passwd` chega no mesmo arquivo com **zero `../`**. E mesmo contra traversal relativo um filtro de string perde — `..%2f` (percent-encoded, que o Werkzeug decoda de volta pra `../`), `....//` (remove o `../` do meio e sobra `../`), `..\` no Windows, double-encoding. A causa raiz não é o token `../`; é que o caminho resolvido nunca é confinado. Enquanto você filtrar a *string do input* em vez de confinar o *caminho resolvido*, escapar e blocklistar são jogo perdido — a mesma lição que o `sqli-union-basic` ensina sobre escapar aspas e o `command-injection-basic` sobre escapar metacaracteres de shell. A regra transferível nos três: **valide o resultado contra o que é permitido (aqui, uma localização sob o diretório base), não o input contra o que é proibido.**

## `os.path.basename` e `send_from_directory` — ferramentas mais simples com um papel

Duas outras abordagens valem conhecer, nenhuma delas o fix geral mas ambas com um lugar:

- **`os.path.basename(filename)`** joga fora todo componente de diretório, deixando só o nome final (`../../etc/passwd` → `passwd`, `/etc/passwd` → `passwd`), então um traversal nunca sobe. É mais simples que resolve-e-confirma — e é um *fix alternativo* legítimo **quando a app nunca precisa de subdiretórios**. No momento em que a feature tiver que servir `docs/readme.txt`, o `basename` quebra ela, e o `realpath` + prefix check é o caminho. Este átomo usa o fix geral pra ele valer independente do layout dos arquivos.
- **`send_from_directory(directory, filename)`** é o file server embutido do Flask, e ele faz exatamente esse containment check por você (resolvendo o caminho e recusando qualquer coisa fora de `directory`). Em código Flask real, prefira ele a um `open()` na mão. A gente faz na mão aqui só porque a feature renderiza o conteúdo *inline* num `<pre>` em vez de mandar o arquivo como download — então fazemos na mão o mesmo check que o `send_from_directory` faria por baixo.

## A01, não A03 — isto é access control

Os átomos de injection todos têm o formato "input virou código": SQL (`sqli-union-basic`), HTML/JS (os átomos de XSS), shell (`command-injection-basic`). Este não. Nada que o atacante manda é parseado ou executado — um nome de arquivo de aparência legítima simplesmente conduz a app a um *recurso fora do escopo pretendido*. Isso é Broken Access Control, e é por isso que o átomo vive em A01.

É o mesmo formato do `idor-numeric-id`, o outro átomo A01: lá, trocar um ID numérico (`/notes/1` → `/notes/2`) alcança um objeto que não é seu; aqui, navegar o filesystem (`notes.txt` → `../../etc/passwd`) alcança um arquivo que não é seu. Os dois são "a app te entregou um recurso que não era pra você", e os dois fixes são o check que faltava — um ownership check lá, um confinement check aqui. Contraste com o `command-injection-basic`, seu gêmeo por mecânica: lá seu input virou um *comando* (código); aqui vira uma *localização* (um caminho). Mesmo destino (`/etc/passwd`), mecanismo oposto — execução versus navegação — e categoria oposta (A03 versus A01).

## O bug mora no app.py (o inverso do par XSS)

Aqui `vulnerable/app.py` e `fixed/app.py` diferem — o confinamento ausente está no código Python, e os templates (fora o echo incidental "Resolved path") são iguais. É a imagem espelhada do `xss-stored` e do `xss-reflected`, onde o `app.py` era byte a byte idêntico entre as versões e o bug morava inteiramente no template. Mesma lente de auditoria, localização diferente: pra path traversal você lê o código atrás de chamadas de manipulação de arquivo (`open`, `os.path.join`, `send_file`) e pergunta o que confina o caminho; pra XSS você lê os templates atrás de `|safe`. Saber qual arquivo abrir é metade da auditoria.
