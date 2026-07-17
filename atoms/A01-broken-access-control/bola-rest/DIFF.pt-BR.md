# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em exatamente uma rota — `get_order`. `POST /login`, `GET /api/orders`, os helpers, os imports, o `Dockerfile` e o `requirements.txt` são idênticos entre as duas versões (e não há templates — este átomo é API-only). A mudança é um object-level authorization check.

## O fix — object-level authorization

```diff
 @app.route("/api/orders/<int:order_id>")
 def get_order(order_id):
-    _authenticate()   # require a valid token (401 otherwise) -- AUTHENTICATION only
+    caller = _authenticate()
     order = ORDERS.get(order_id)
     if order is None:
         abort(404)
-    # VULNERABLE: the request is authenticated, but the order is returned WITHOUT
-    # checking that order["owner"] is the authenticated caller. Being authenticated
-    # is not being authorized for THIS object. (BOLA -- no object-level check.)
+    # FIXED: object-level authorization -- serve the order only to its owner.
+    # 404 (not 403) so "exists but not yours" is indistinguishable from "doesn't
+    # exist": with sequential ids, a 403 would be an enumeration oracle.
+    if order["owner"] != caller:
+        abort(404)
     return jsonify(order)
```

A view fixed compara o `owner` do pedido com o caller autenticado e recusa um mismatch. Esse único condicional fecha o BOLA: a classe é "o servidor devolve um objeto escopado a usuário sem checar que o caller é o dono", e a remediação é exatamente a negação disso.

## Authenticated ≠ authorized — dá pra ver no diff

Olhe a primeira linha que mudou: `_authenticate()` virou `caller = _authenticate()`. É a lição inteira numa edição.

As duas versões autenticam — as duas chamam `_authenticate()`, as duas rejeitam token ausente ou inválido com `401`. A versão vulnerable chama só por esse efeito colateral e **joga a identidade fora**; ela nunca usa *quem* é o caller. A versão fixed **retém** a identidade e confere o objeto contra ela. Autenticação responde "quem é você?"; autorização responde "este objeto é seu?". O bug nunca foi que a primeira pergunta ficou por fazer — foi que a resposta ficou sem uso.

É por isso que "tem auth no endpoint" é um falso conforto numa review, e por que BOLA é tão comum: a autenticação está ali, fazendo o trabalho dela, e te embala pra passar batido pela autorização ausente do lado.

## 404, não 403 — o oráculo de enumeração

A view fixed retorna **`404`** pra um pedido que o caller não possui — não `403` — e um id genuinamente inexistente também retorna `404`. Os dois são deliberadamente indistinguíveis.

Por que não `403`? Porque os ids são **sequenciais**. Um `403` anuncia "este pedido existe, mas não é seu"; varra os inteiros e `403`-vs-`404` vira um **oráculo de enumeração** que mapeia todo pedido do sistema — exatamente o reconhecimento que um atacante quer antes de um BOLA. Retornar `404` pra "não é seu" e pra "não existe" não vaza nada: o atacante não consegue nem saber quais ids são reais.

É aqui que os átomos irmãos diferem, e a diferença é instrutiva:

- **O `idor-uuid-guessable` retorna `403`**, e ali tá certo — os ids dele são UUIDs, um espaço não-enumerável. Um oráculo `403`/`404` sobre 122 bits aleatórios é inútil; você não varre isso. O DIFF dele até avisou de antemão: *"A 403 here does confirm the receipt exists; if that mattered, 404 would be the defense-in-depth choice."* Aqui importa.
- **O `idor-numeric-id` retorna `403` com ids sequenciais** — então carrega o mesmo oráculo latente. Não está errado: foi a primeira e mais simples formulação da lição do check ausente e escolheu o status semanticamente honesto (`403 Forbidden` — "um objeto real, não pra você"), porque vazar existência não era o ponto dele. Este átomo, modelando uma API REST onde enumerar é o movimento-assinatura, faz do oráculo o ponto — então escolhe `404`.
- **O `path-traversal-basic` retorna `404`** também, mas por outro motivo: lá o "recurso" recusado é um path *fora* do domínio da app, e `404` recusa confirmar que exista algo ali. Aqui o objeto é genuinamente da app — `404` esconde que ele existe, de propósito.

Regra de bolso (estendendo a do `idor-uuid-guessable`): retorne **`403`** quando admitir que o objeto existe é aceitável — ou os ids não são enumeráveis; retorne **`404`** quando a própria existência vaza. Ids sequenciais fazem a existência vazar.

## Remodelar o id é jogo perdido

Repare o que o fix *não* muda: o id. O pedido 41 continua um inteiro sequencial simples, na URL, entregue aos clientes pelo endpoint de listagem. O `idor-uuid-guessable` já fez este argumento sobre o próprio fix — que trocar o inteiro por um UUID seria *"obfuscation... teatro"*, que esconder ou randomizar um id "só muda quanto custa *achar* o bug". Numa API o ponto é ainda mais afiado: o id é público *por contrato* — clientes REST devem segurar e passar ids — então "esconde o id" nem é uma opção coerente. A única defesa é autorização. A regra transferível, a mesma que o `idor-numeric-id` e o `idor-uuid-guessable` ensinam: **corrija o check ausente, não remodele o identificador.**

## O endpoint de listagem já escopa — a assimetria é o BOLA

A `GET /api/orders` é *idêntica* nas duas versões, e nas duas ela filtra certo: `[o for o in ORDERS.values() if o["owner"] == caller]`. O desenvolvedor sabia escopar uma resposta pro dono dela — fez na coleção. Só não fez no endpoint de objeto único. Essa assimetria — **lista escopada, item não** — é exatamente como o BOLA aparece em codebases reais, e é por isso que a lista continuar correta na versão fixed não é um segundo fix: ela nunca esteve quebrada. O único bug morava em `get_order`, e o check de uma linha é o reparo inteiro.

## O token é opaco, e o ataque nunca o toca

O Bearer token é uma string opaca aleatória resolvida server-side pelo mapa `TOKENS` — um substituto pra um OAuth2 opaque access token ou uma session id, não um JWT. Nada no ataque inspeciona, decodifica, adultera ou forja ele; a mallory faz login como ela mesma e manda o próprio token, inalterado, o tempo todo. É esse o ponto de um token opaco aqui: ele é sólido e legitimamente dela, então a única coisa que sobra pra explicar a leitura cross-user é a autorização ausente. O token não é a vulnerabilidade; o endpoint é.

## Isto é BOLA — IDOR numa API, e mora no app.py

Nada que o caller manda é parseado ou executado; um id legítimo simplesmente alcança um objeto fora do escopo do caller. Isso é Broken Access Control (A01 na web, **API1:2023** na lista de API), a mesma forma do `idor-numeric-id` e do `idor-uuid-guessable` — lá você troca um número ou reconstrói um UUID, aqui você lê o seu id na API e pede o vizinho, e os três fixes são o ownership check que faltava. Como nos dois irmãos, o bug mora no `app.py`, não em algum template (não há nenhum), e não dá `grep`: não tem `f"`, `|safe`, nem `eval` pra achar. Você o pega lendo cada endpoint que retorna um objeto escopado a usuário e perguntando "onde isto confere que o caller é dono?" — e reparando, aqui, que uma chamada `_authenticate()` funcionando foi silenciosamente confundida com esse check.
