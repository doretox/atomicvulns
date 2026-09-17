# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em uma coisa: o **gerador do reset token**, e o ciclo de vida do token que decorre dele. O lado vulnerável gera o token com `random` seedado com o relógio; o lado corrigido usa `secrets`, e torna o token single-use e de vida curta. Isso toca o import, o gerador, e as duas linhas que guardam e buscam o token. `GET /`, `POST /login`, as queries parametrizadas, o schema, o seed dos usuários, a entrega "por e-mail" e as portas são byte-idênticos. O `requirements.txt` é idêntico também (veja a última seção).

## O fix — trocar o gerador

```diff
 import os
 import time
-import random
-import string
+import secrets
 import sqlite3
```

```diff
 def make_reset_token():
-    # VULNERABLE: ... random, a PRNG (the Mersenne Twister), SEEDED WITH THE CURRENT TIME ...
-    # the seed here is int(time.time()) ... a value the attacker reads off this response's
-    # Date header. Re-seed with that integer, run the same random.choice() calls, and you
-    # regenerate the SAME token, byte for byte. The secret is not secret ...
-    random.seed(int(time.time()))
-    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))
+    # FIXED: secrets.token_urlsafe(32) draws from a CSPRNG (os.urandom) -- ~256 bits of
+    # UNPREDICTABLE entropy, with no seed the attacker can reproduce ... This is the SAME
+    # generator session-fixation uses for its session ids. The token is unguessable by design.
+    return secrets.token_urlsafe(32)
```

O ciclo de vida do token decorre disso: o lado corrigido guarda uma expiração junto do token e o consome no uso.

```diff
     if row:
         token = make_reset_token()
-        RESET_TOKENS[token] = email  # no single-use, no expiry: the flaw here is the GENERATOR
+        RESET_TOKENS[token] = {"email": email, "expires_at": time.time() + TOKEN_TTL}
         deliver_token(email, token)
```

```diff
 def reset():
     ...
-    email = RESET_TOKENS.get(token)
-    if not email:
+    entry = RESET_TOKENS.pop(token, None)            # single-use: consumed on lookup
+    if not entry or entry["expires_at"] < time.time():   # expiry: reject a token past its TTL
         return jsonify({"reset": False}), 400
```

`random.seed(int(time.time()))` + `random.choice(...)` — um PRNG seedado com um valor que o atacante lê do header `Date` — vira `secrets.token_urlsafe(32)`, um CSPRNG cuja saída nenhuma resposta estreita. Ao redor dele, o token vira single-use (`pop`) e de vida curta (`expires_at`). Esse é o fix inteiro.

## A causa é o gerador, não um check ausente

O bug não é "o fluxo esqueceu de autenticar", e não é "o fluxo esqueceu de checar o dono". O fluxo de reset autentica corretamente — por posse do token, que é exatamente como o forgot-password funciona — e age no *dono do token*, nunca num user id vindo do corpo do request (então **não** é IDOR: o token é o segredo, não o id de um objeto). A única falha é que o segredo é **previsível**: um PRNG (`random`, o Mersenne Twister) seedado com o relógio produz um token que qualquer um reproduz pelo header `Date`. Em termos de CWE isso é um mecanismo fraco de recuperação de senha (CWE-640) cuja raiz é um seed previsível num PRNG (CWE-337) — insufficiently random values (CWE-330). A prova de isolamento: o reset legítimo self-service funciona idêntico nos dois lados; só *prever o token da vítima* separa os dois, e no lado corrigido essa previsão falha porque o `secrets` produziu um token que o atacante não consegue regenerar.

## "Só deixar o token mais longo" não é o fix

A leitura tentadora: *o token foi adivinhado, então deixe-o mais longo e não dá mais.* Errado — o token nunca foi *adivinhado*, foi **reproduzido**. Uma vez que você re-seeda o `random` com o segundo do header `Date`, você roda o gerador adiante e produz o token *inteiro*, seja qual for o tamanho. Um token seedado com o relógio de 32 caracteres e um de 128 caracteres caem para o mesmo script; os caracteres a mais são igualmente determinados pelo seed. Tamanho adiciona entropia só quando o gerador já é imprevisível. A fraqueza é a previsibilidade, não o tamanho.

## "Usar random com um seed melhor" não é o fix

A leitura tentadora seguinte: *o seed era o problema — seede com algo imprevisível e o `random` serve.* Ainda errado. `random` (o Mersenne Twister) **não é um gerador de segurança sob nenhum seed**. Mesmo bem seedado, seu estado interno é recuperável a partir de saídas suficientes, e toda a sua sequência futura fica então reproduzível — ele foi feito para qualidade estatística, não para imprevisibilidade, e a doc do Python diz isso na cara. E se você recorrer ao `os.urandom` para seedá-lo, você já está segurando entropia criptográfica: o movimento certo é usar `secrets` (feito exatamente para isso), não remendar o `random`. A resposta é um *tipo* diferente de gerador — um CSPRNG — não um PRNG melhor seedado.

## Single-use e expiração são o acabamento, não o fix

O lado corrigido também torna o token single-use (`pop`) e de vida curta (`expires_at`). Cuidado com como você lê isso.

Single-use e expiração são propriedades **legítimas e necessárias** de um reset token bem-feito — defense in depth. Um token deve ser usável uma vez (para que um token usado não seja replayado) e por pouco tempo (para que um token vazado apodreça rápido). Um fix completo as inclui, e o lado corrigido as inclui.

**Mas não são o que derrota este ataque, e não são a falha central.** A falha central é a previsibilidade. Um token *imprevisível* que nunca expirasse ainda seria muito mais seguro que um *previsível*, porque o atacante nunca conseguiria regenerá-lo pra começar. Repare onde o token previsto morre no lado corrigido: no `POST /reset`, rejeitado como um **token desconhecido** — ele nunca esteve no store, porque o `secrets` gerou outra coisa. Expiração e single-use nem chegam a ser consultados; não há o que expirar. Adicione uma expiração ao lado *vulnerável* e o ataque ainda funciona: o atacante prevê o token e o usa na hora, bem dentro de qualquer janela.

Então nomeie as duas, mas mantenha-as no lugar. Um leitor que sai achando "o fix foi adicionar uma expiração" perdeu a lição: teria parafusado uma expiração num token ainda **previsível**, e o atacante ainda o reproduziria e o gastaria dentro da janela. O eixo é a imprevisibilidade; single-use e expiração são o acabamento honesto sobre um token que já é impossível de adivinhar. (Mesma honestidade-em-camadas da nota do `salt` no `crypto-weak-hash` ou da nota do `PIN` no `debug-enabled`: a defesa nomeada é real, mas não é o fix de raiz *aqui*.)

## Impacto, e o contraste com os vizinhos

O impacto é account takeover: o atacante define a senha da vítima e loga como ela. Não é RCE; o teto é o controle da conta cujo reset foi previsto — que, num alvo real, é qualquer conta cujo reset o atacante consiga pedir.

Este átomo fica a um eixo de distância de três vizinhos, e os contrastes são a lição:

| Vizinho | O eixo dele | `weak-password-reset` (este átomo) |
|---|---|---|
| [`session-fixation`](../session-fixation/) — também **A07** | a **sessão**: o id é *forte* (`secrets`), a falha é o **ciclo de vida** dele — ele sobrevive ao login | a **credencial de reset**: o token é *previsível* (`random`-seedado), e a previsibilidade **é** a falha — o fix inclusive cai no mesmo gerador `secrets` que o 15 já usa |
| [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) / [`idor-uuid-guessable`](../../A01-broken-access-control/idor-uuid-guessable/) | trocar o **id de um objeto** e alcançar o recurso de outro usuário por baixo de um **check de controle de acesso ausente** | o token previsível **não** é o id de um objeto — é o **segredo** de autenticação; prevê-lo *é* virar a vítima, não escapar de um guard |
| [`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/) / [`crypto-ecb-mode`](../../A02-cryptographic-failures/crypto-ecb-mode/) | **quebrar** um artefato cripto offline (rainbow table; cut-and-paste de blocos) | nada é quebrado — o token é **reproduzido** porque o gerador é previsível; uma falha de *desenho* de autenticação (A07), não de *primitiva* cripto (A02) |

## Os dois lados compartilham as dependências

Diferente do `crypto-weak-hash`, cujo fix traz uma biblioteca (`bcrypt`), o fix aqui não adiciona nada ao `requirements.txt`:

```
Flask==3.1.3
```

— byte-idêntico nos dois lados. `random` e `secrets` são ambos da biblioteca padrão do Python, então trocar um pelo outro muda só o `app.py`. A ferramenta certa para um segredo impossível de adivinhar já estava na caixa; o lado vulnerável só pegou o módulo errado.
