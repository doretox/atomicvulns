# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem; os templates, o `Dockerfile` e o `requirements.txt` são idênticos entre as duas versões. A mudança tem duas partes, e elas não são iguais — uma é *o* fix, a outra é defense-in-depth.

## O fix que importa — um ownership check

A mudança relevante pra segurança é um único conditional na view `/receipt/<uuid>`:

```diff
 @app.route("/receipt/<uuid:receipt_id>")
 def view_receipt(receipt_id):
+    caller = request.headers.get("X-User-ID", ATTACKER)
     r = RECEIPTS.get(str(receipt_id))
     if r is None:
         abort(404)
-    # VULNERABLE: no ownership check -- any caller who holds (or reconstructs)
-    # the id reads the receipt. The unguessable-looking UUID is treated as the
-    # access control; it is not one.
+    # FIXED (the fix that matters): serve the receipt only to its owner.
+    if r["owner"] != caller:
+        abort(403)
     return render_template("receipt.html", receipt=r)
```

A view fixed lê a identidade declarada do caller (`X-User-ID`, o mesmo header auto-declarado que o resto da app usa) e compara com `r["owner"]` antes de devolver o recibo. Divergência → `403 Forbidden`. Esse único conditional fecha o IDOR: a classe é "o servidor devolve um objeto escopado a usuário sem checar se o caller é o dono", e a remediação é exatamente a negação disso.

## Defense-in-depth — um id não-reconstruível

A segunda mudança troca o gerador de id, e remove a maquinaria que o antigo precisava:

```diff
-def _new_receipt_id():
-    return uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)
+def _new_receipt_id():
+    return uuid.uuid4()
```

O `uuid1` embutia um timestamp e o `node` do host e, com um `clock_seq` estável, era reconstruível a partir do `issued_at` que o dashboard vaza (ver [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md), Passos 2–4). O `uuid4` é sorteado de um CSPRNG e não embute nenhum dos dois, então a reconstrução não tem de onde partir. Com o gerador antigo fora, as constantes `_NODE`/`_CLOCK_SEQ` e o helper `_issued_at_from` vão junto (o `_add_receipt` fixed carimba `issued_at = datetime.now(timezone.utc)` em vez de derivar do id).

## Por que o check sozinho basta — e a troca do gerador sozinha não

Este é o coração da lição de duas camadas, e o DIFF tem que ser honesto sobre isso:

- **O ownership check corrige o bug sozinho.** Você poderia manter o `uuid1` *e* manter o dashboard vazando o `issued_at`, e o ataque ainda falharia — o id reconstruído agora retorna `403`, porque o servidor finalmente confere quem está pedindo. Obscuridade nunca foi o controle; o check é.
- **A troca do gerador não corrige o bug sozinha.** Mantenha o check ausente e só troque pra `uuid4`, e qualquer um que *obtenha* um id válido — link compartilhado, header `Referer`, linha de log, histórico do browser — ainda lê o recibo. O Passo 5 do walkthrough prova que o endpoint nem olha pra identidade. O `uuid4` fecha a rota de *reconstrução* (Camada 2); não faz nada quanto ao *acesso* (Camada 1).

Então o fix entrega os dois, em ordem de prioridade: o check é a correção; o `uuid4` é defense-in-depth que remove uma fonte desnecessária de previsibilidade. Vá no check primeiro.

## Remodelar o id é jogo perdido sozinho

O `idor-numeric-id`, o irmão direto, já disse isso sobre o próprio fix: trocar o inteiro por um UUID seria *"obfuscation... teatro"*, e "UUIDs, signed tokens, URLs escondidas, rate limits ... só mudam quanto custa *achar* o bug". Este átomo é essa afirmação tornada concreta — o id *é* um UUID e o bug continua intacto — com um plus: o UUIDv1 nem era difícil de achar, porque carregava o próprio timestamp e node. A regra transferível, a mesma que o `sqli-union-basic` ensina sobre escaping e o `path-traversal-basic` sobre blocklist de `../`: **corrija o check ausente, não remodele o identificador.** Esconder ou randomizar o id só muda quanto custa achá-lo; nunca adiciona a autorização que não está lá.

## 403, não 404 — e por que isso difere do path-traversal-basic

A view fixed retorna **403 Forbidden**: o recibo é um objeto real da app que este caller não está autorizado a ver, então "forbidden" é o status honesto — a mesma escolha que o `idor-numeric-id` faz. Contraste com o `path-traversal-basic`, que retorna **404** pra um traversal rejeitado: lá o "recurso" é um caminho *fora* do domínio da app, e o 404 se recusa a confirmar se existe algo ali. A regra de bolso: retorne 403 quando o objeto é seu-de-saber-que-existe-mas-não-de-ler; retorne 404 quando admitir a existência já vaza. Um 403 aqui de fato confirma que o recibo existe; se isso importasse, 404 seria a escolha de defense-in-depth — mas mantemos 403 por consistência com o IDOR irmão, porque aqui a existência não é a parte sensível, o conteúdo é.

## O vazamento do dashboard é o ambiente, não um segundo bug

O dashboard em `GET /` expõe o `owner` e o `issued_at` em microssegundos de todos os recibos, e ele é **idêntico na versão fixed** — de propósito. Timestamps precisos demais numa listagem são o solo realista onde a reconstrução cresce (serialização default de datetime vaza microssegundos o tempo todo), mas não são a vulnerabilidade sob estudo, e o átomo mantém exatamente um bug. Deixar o vazamento no lugar na app fixed prova o ponto: com o ownership check presente (e o `uuid4` por cima), o mesmo `issued_at` fica inerte. Reduzir a precisão pra segundos seria um hardening extra razoável, mas não é o fix e não foi aplicado aqui.

(Mais uma linha de higiene, nas duas versões: os templates autoescapam tudo, incluindo o `X-User-ID` controlado pelo atacante e ecoado no dashboard. Esse escape também **não é** o fix de IDOR — ele só impede que um header sem escape empilhe um reflected XSS por cima, pra o átomo continuar em exatamente um bug.)

## Isto é IDOR — o mesmo bug do idor-numeric-id, e ele vive no app.py

Nada que o atacante manda é parseado ou executado; um id legítimo simplesmente alcança um objeto fora do escopo do caller. Isso é Broken Access Control (A01), a mesma forma do `idor-numeric-id` — lá você troca um número, aqui você reconstrói um UUID, e os dois fixes são o ownership check que faltava. Como nos dois irmãos A01, o bug vive no `app.py`, não nos templates, e não dá `grep`: não tem `f"`, `|safe` ou `eval` pra procurar. Você o acha lendo cada endpoint que retorna um objeto escopado a usuário e perguntando "onde isto confere que o caller é dono?" — e reparando, aqui, que um UUID na URL foi silenciosamente confundido com esse check.
