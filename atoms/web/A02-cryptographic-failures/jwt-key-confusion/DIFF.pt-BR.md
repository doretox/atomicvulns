# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em **um lugar — o helper `verify`** (mais os quatro imports da stdlib e o único helper de que ele precisava). Todo o resto é byte-idêntico: os imports compartilhados, o `authenticate`, as quatro rotas (`/login`, `/jwks`, `/api/profile`, `/admin/users`), os dados `USERS`, como as chaves RSA são carregadas, o `Dockerfile` e o `requirements.txt`. As duas versões trazem o **mesmo** par de chaves commitado (`keys/private.pem`, `keys/public.pem`), byte a byte. Não há templates (este átomo é API-only).

```diff
 import os
-import json
-import hmac
-import hashlib
-import base64
 import jwt
 from flask import Flask, request, jsonify, abort
@@
-def _b64url_decode(seg):
-    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))
-
-
 def verify(token):
-    # VULNERABLE: the server reads alg from the token's OWN header and picks the
-    # verification family from it. RS256 -> RSA-verify with the public key (safe, correct).
-    # HS256 -> HMAC-verify using the SAME public-key bytes as the secret (!). ...
-    alg = jwt.get_unverified_header(token).get("alg")
-    if alg == "HS256":
-        header_b64, payload_b64, sig_b64 = token.split(".")
-        signing_input = f"{header_b64}.{payload_b64}".encode()
-        expected = hmac.new(PUBLIC_KEY_PEM, signing_input, hashlib.sha256).digest()
-        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
-            raise ValueError("bad HS256 signature")
-        return json.loads(_b64url_decode(payload_b64))
-    if alg == "RS256":
-        return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
-    raise ValueError("unsupported alg")
+    # FIXED: stop asking the token which algorithm to use. Pin RS256 and let PyJWT enforce
+    # it — a token with alg:HS256 is rejected (HS256 isn't in the allowlist). ...
+    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
```

O `verify` vulnerável lê o `alg` do próprio token e ramifica pra um validador; o `verify` fixed apaga o branch e fixa o algoritmo, deixando o PyJWT impor. Os quatro imports da stdlib e o helper `_b64url_decode` existiam só pra fazer o ramo HS256 na mão — eles vão embora junto.

## O mesmo shape de fix do `jwt-none-alg`

Este é o núcleo do diff, então comece por aqui. O fix do `jwt-none-alg` *removeu* um branch — o escape `if header["alg"] == "none"` que pulava a verificação. Este fix também remove um branch — o caminho `if alg == "HS256"` que verificava com o algoritmo errado — e fixa a allowlist. **Os dois fixes são o mesmo movimento: parar de deixar o `alg` do token decidir como o token é validado.**

A regra do `jwt-none-alg` vale sem mudança aqui:

> Passe `algorithms=` como uma lista positiva de exatamente os algoritmos que este endpoint deve aceitar, e nunca ramifique pelo `header["alg"]` pra escolher como validar. O header é dado, não policy.

O `verify` vulnerável viola essa regra literalmente — sua primeira linha é `jwt.get_unverified_header(token).get("alg")`, e a função inteira é o branch que segue. O fix é uma linha, e é a mesma linha em que o fix do `jwt-none-alg` parou: `jwt.decode(token, KEY, algorithms=[...])`, com o algoritmo decidido pelo servidor, antes de o token ser lido.

O próprio walkthrough do `jwt-none-alg` nomeou este ataque de antemão — *"algorithm-confusion attacks where the server is tricked into using the wrong key"* — como outra forma de perder o mesmo jogo. Este átomo é esse flavor, tornado real. A única diferença é o mecanismo: o `jwt-none-alg` pula a verificação (`none`); este átomo roda a verificação, mas com a família de algoritmo errada.

## Contraste com o `jwt-weak-secret` — código, não um valor; e nada está fraco

O fix do `jwt-weak-secret` mudou um **valor** — um secret fraco por um forte — sem tocar uma linha de lógica. Este fix muda **código**: apaga um branch. Essa é a diferença visível, mas a mais funda é esta: no `jwt-weak-secret` algo estava genuinamente *fraco* (o secret não tinha entropia), e o ataque era *adivinhá-lo*. Aqui **nada está fraco** — a chave RSA é forte, de 2048 bits, a signature forjada verifica de verdade, o HMAC-SHA256 é sólido — e mesmo assim cai. O atacante não adivinha nada; ele usa a chave *pública*, exatamente como publicada, sob um algoritmo que o servidor nunca devia ter aceitado. É isso que faz de key confusion o mais insidioso dos três.

## Por que o servidor vulnerável verifica na mão (e por que ele tem que)

Uma pergunta justa: por que o `verify` vulnerável faz um HMAC na mão com `hmac`/`hashlib` em vez de só chamar o PyJWT? Porque **o PyJWT moderno bloqueia este ataque por padrão, e uma chamada ingênua não seria vulnerável.** Passar uma chave pública RSA (um PEM contendo `-----BEGIN PUBLIC KEY-----`) pra um algoritmo HMAC levanta:

```
jwt.exceptions.InvalidKeyError: The specified key is an asymmetric key or x509
certificate and should not be used as an HMAC secret.
```

Então `jwt.decode(token, public_key_pem, algorithms=["HS256", "RS256"])` — a versão vulnerável "óbvia" — abortaria no caminho HS256, não confirmaria a forja. Pra reproduzir o bug de verdade numa lib já patchada, o servidor tem que contornar esse guard, que é exatamente o que fazer o HMAC na mão faz.

Isto não é um espantalho. Key confusion vive, no mundo real, exatamente nesse tipo de código: middleware de auth caseiro, libs de JWT de outras linguagens que não têm esse guard, e wrappers que ramificam pelo `alg` pra "suportar RS256 e HS256". **A recusa da lib é, ela mesma, a lição** — libs modernas mitigam isso, e o bug sobrevive em quem reimplementa a verificação na mão. (A mesma recusa é por que a forja no `WALKTHROUGH.pt-BR.md` também não pode ser um one-liner PyJWT: o atacante faz o HMAC na mão também.)

## O colapso da assimetria, visível no código

Olhe onde `PUBLIC_KEY_PEM` aparece no `verify` vulnerável. Está nos **dois** ramos:

- sob `RS256`, como a **chave de verificação** RSA — inofensiva, correta, exatamente pra isso que serve;
- sob `HS256`, como o **secret HMAC** — catastrófica, porque verificar um HMAC é conseguir assinar um.

Mesma constante, mesmos bytes, dois ramos, dois significados de segurança completamente diferentes. É a vulnerabilidade inteira em duas linhas: no instante em que o servidor concordou em tratar uma chave pública de verificação como um secret compartilhado, a assimetria que tornava a chave segura pra publicar colapsou.

## Isto é A02 — e não dá `grep`

Como nos irmãos JWT, o bug não é uma chamada perigosa que dá pra procurar. `jwt.decode(token, key, algorithms=["RS256"])` — a linha fixed — é exatamente como um código *correto* se parece. Não há `eval`, nem SQL montado com string, nem `|safe`. O bug é o branch escrito à mão ao lado, e a confiança mal colocada dentro dele. Você o pega lendo a lógica de verificação e fazendo uma pergunta: **"quem escolhe o algoritmo — o servidor, ou o token?"** Se a resposta é o token, você achou. O RSA e o HMAC estão ambos intactos; a causa raiz é um **erro de lógica**, não cryptography quebrada — que é por que isto mora em A02 (Cryptographic Failures) como uma falha de *configuração criptográfica*, a mesma prateleira do `jwt-none-alg`.

## `403`, não `404`

O `GET /admin/users` retorna **`403`** pra um token válido não-admin — "autenticado, mas não permitido". Não há oráculo de enumeração pra esconder: o endpoint é um recurso fixo, não um objeto indexado por um id sequencial. (Esse foi o motivo do `bola-rest` escolher `404`; nenhum id desses existe aqui, então `403` é o status honesto. Não copie o `404` por reflexo.)

## O `/jwks` publica a chave pública de propósito — e o fix não o toca

Servir a chave pública RSA em `/jwks` é **correto e por design**: clientes precisam dela pra verificar tokens, e uma chave pública é segura pra publicar. Ela *não* é o bug, e o fix não a toca — a chave continua a mesma, ainda de 2048 bits, ainda servida. O bug nunca foi publicar a chave; foi o servidor vulnerável depois aceitar essa mesma chave como um secret HMAC. Os bytes que o `/jwks` serve são os bytes exatos que o ramo HS256 vulnerável passa pro `hmac.new`, que é por que a forja bate — a premissa inteira do "mesmos bytes" do ataque. O fix fecha o branch que usou mal a chave, não o endpoint que a publica.
