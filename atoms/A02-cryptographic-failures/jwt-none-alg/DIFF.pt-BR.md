# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. Só o helper `decode` muda; rotas, templates e a constante `SECRET` são byte a byte idênticos.

```diff
 def decode(token):
-    header = jwt.get_unverified_header(token)
-    if header.get("alg") == "none":
-        # TODO: remove after local testing — accepts unsigned tokens
-        return jwt.decode(token, options={"verify_signature": False})
     return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Quatro linhas deletadas. Nenhuma adicionada.

## O que mudou

O `decode` vulnerable tinha um branch que inspecionava o header do token e pulava a verificação de signature quando o header anunciava `alg=none`. O fix é deletar o branch — a função agora sempre verifica a signature sob HS256, sem escape hatch driven by header.

O comentário `# TODO: remove after local testing` saiu junto com as linhas que ele descrevia. Esse comentário é a forma realista desse tipo de CVE: um atalho de debug que sobreviveu além do teste pra que serviu e chegou em produção. Reviewers de código deveriam tratar qualquer `verify_signature: False` (no PyJWT) — ou equivalente em outras bibliotecas JWT — como finding inegociável onde quer que apareça num path autenticado.

## Por que isso resolve

Três razões que se reforçam:

- **O fix remove o branch, não o sintoma.** Uma alternativa ingênua seria manter o branch e adicionar um guard tipo `header.get("alg") in BLOCKED_ALGS`. Isso ainda deixaria o header do token escolher qual validador roda — o bug mais fundo da §5 do walkthrough — e perderia pra comparação case-insensitive, escapes Unicode, e a classe maior de ataques de algorithm confusion que nem envolvem `none`.
- **`algorithms=["HS256"]` é uma lista positiva, decidida server-side, antes do token ser lido.** O PyJWT compara a claim `alg` do token com essa lista e rejeita qualquer coisa fora dela. `none` não está lá, então tokens sem signature falham antes de qualquer trabalho de signature começar. A lista é uma propriedade *deste endpoint* (este servidor, este path de código), não *deste token* — essa assimetria é o que fecha o buraco do confused deputy.
- **`SECRET` agora é inegociável.** O `NoneAlgorithm.prepare_key` do PyJWT levanta `InvalidKeyError` se alguma key não-`None` é passada pra ele, e seu `verify()` sempre retorna `False`. Então mesmo que um atacante tentasse coagir o path de algoritmo pra `none` apesar da allowlist, a biblioteca recusaria "verificar" um token alg=none de qualquer forma que retornasse `True`. O hardening da própria biblioteca é backstop pra allowlist da aplicação — defesa em profundidade, não defesa nessa única linha.

## Por que "bloquear alg=none" não é o fix

Uma remediação natural-mas-errada é assim:

```python
header = jwt.get_unverified_header(token)
if header.get("alg") == "none":
    abort(401)
return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Três motivos pra não fazer:

- **Case sensitivity e Unicode.** `"NONE"`, `"None"`, `"nOnE"` e `"none"` decodam pra o mesmo algoritmo em alguns parsers JWT mas escapam do check de string-equality desse guard. Bypasses reais contra exatamente esse pattern foram publicados pra várias bibliotecas JWT.
- **Continua fazendo branch sob `header["alg"]`.** O servidor continua deixando o header do token guiar comportamento, só que com um valor permitido a menos. O pattern sobrevive; só o alfabeto encolhe.
- **Só endereça `none`.** Outras formas do atacante manipular `alg` pra subverter validação — secrets fracos que caem em brute-force, e ataques de algorithm confusion onde o servidor é induzido a usar a chave errada — não envolvem `none`. Uma blocklist que mira `none` especificamente protege contra exatamente um bypass e zero dos relacionados.

A regra geral pra chamadas de decode JWT: passe `algorithms=` como uma lista positiva exatamente dos algoritmos que esse endpoint deve aceitar, e nunca faça branch sob `header["alg"]` pra escolher como validar.

## Contraste com átomos anteriores

Este é o terceiro átomo do projeto onde o fix é *remover* código em vez de adicionar (os dois primeiros foram `sqli-union-basic`, onde o build SQL via `f"…{username}…"` foi deletado; e `xss-reflected`, onde o filtro `|safe` foi deletado). Em `idor-numeric-id` e `ssrf-basic`, o fix adicionou um check ausente. Aqui o bug não é check ausente — *tem* check, é a verificação HS256 na linha 5 do diff. O bug é o *escape hatch* que deixa o atacante contornar ele. Remover o escape hatch deixa só o check.

Uma forma de ler essa família em code review: quando você vir um decode JWT envolvido por qualquer condicional que faz branch baseado no próprio token — `if header.get("alg") == ...`, `if "Bearer " in auth`, `if claims.get("kid") in trusted_kids` — pare e pergunte "que valor a condicional está lendo, e quem controla esse valor?" Se a resposta for "o atacante", a condicional é, no melhor caso, load-bearing, e no pior caso é o bug inteiro.
