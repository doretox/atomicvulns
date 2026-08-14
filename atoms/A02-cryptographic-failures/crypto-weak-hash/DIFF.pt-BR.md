# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em exatamente uma coisa: o **primitivo de hash**. O lado vulnerável armazena e verifica com MD5 sem salt; o lado corrigido usa bcrypt. Essa mudança toca `store_hash`, `verify`, o import e o comentário do seed — nada mais. `GET /`, o fluxo do `POST /login`, a query parametrizada, o schema e as portas são byte-idênticos. A única outra diferença está no `requirements.txt` (veja abaixo).

## O fix — trocar o primitivo

```diff
 import os
-import hashlib
 import sqlite3
+import bcrypt
 from flask import Flask, request, jsonify
```

```diff
 def store_hash(password):
-    # VULNERABLE: MD5 is a fast, general-purpose hash, used here with NO salt. It is the
-    # WRONG PRIMITIVE for passwords. [...] a fast, unsalted hash is trivially RECOVERABLE.
-    return hashlib.md5(password.encode()).hexdigest()
+    # FIXED: bcrypt is a purpose-built password KDF -- deliberately SLOW (a tunable cost/work
+    # factor) and SALTED (bcrypt.gensalt() embeds a unique random salt in every hash). [...]
+    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


 def verify(password, stored):
-    return hashlib.md5(password.encode()).hexdigest() == stored
+    return bcrypt.checkpw(password.encode(), stored.encode())
```

`hashlib.md5(...).hexdigest()` — um hash rápido e de propósito geral, sem salt — vira `bcrypt.hashpw(..., bcrypt.gensalt())`, um password KDF lento e salgado, verificado com `bcrypt.checkpw`. O seed grava o que `store_hash` retornar, então no lado corrigido a linha do admin é um hash bcrypt em vez de um MD5; a lógica de login em volta nunca mudou. Esse é o fix inteiro.

## A causa é o primitivo, não o algoritmo

O bug não é "MD5 é quebrado". É usar um hash *rápido e de propósito geral* pra guardar uma senha. Pegar um hash rápido diferente não resolve — veja as duas seções seguintes. O bcrypt neutraliza o ataque por causa do *tipo de função que ele é*: lento por design, e salgado por design.

## "Só põe um salt no MD5" não é o fix

A leitura tentadora: *o problema era a tabela pré-computada, então salga o hash e a tabela fica inútil.* Meio certo. Um salt de fato derrota a rainbow table — um salt-por-hash torna cada hash armazenado único, então nenhuma tabela pré-computada única serve. Mas isso mata um **sintoma**, não a **causa**. MD5 salgado continua *rápido*: o atacante troca para um ataque de dicionário ou brute-force, hasheando chutes ao vivo — bilhões por segundo — contra o seu hash salgado, e uma senha fraca ainda cai. A causa é a *velocidade*.

Pra deixar claro, o salt não é uma armadilha nem um erro — é um ingrediente legítimo e necessário, e um password KDF de verdade já inclui um (o bcrypt salga cada hash automaticamente; o Argon2 também). O ponto é que um salt *sozinho*, colado num hash rápido, não basta. Um KDF feito de propósito te dá salt **e** lentidão juntos — que é por que o fix é um primitivo novo, não um remendo no antigo.

## "Usa SHA-256, ele não é quebrado como o MD5" não é o fix

Errado pelo mesmo motivo. SHA-256 não tem fraqueza de colisão conhecida — mas é um hash rápido e de propósito geral, igual ao MD5. Guardado sem salt, um hash de senha SHA-256 cai pelo mesmíssimo ataque de rainbow table; salgado, ele ainda cai por um ataque de dicionário ao vivo, porque é rápido. "Mais forte" no sentido de resistência a colisão não é a propriedade que você precisa. A propriedade que você precisa é *lento e salgado* — um password KDF (bcrypt, Argon2, scrypt, PBKDF2).

## O lado fixed não tem o que atacar — por inspeção

Você não re-roda o crack contra o hash corrigido pra provar o fix; dá pra ver por inspeção. O valor armazenado é um hash bcrypt salgado (`$2b$12$...`), não um MD5 de 32 hex — uma rainbow table de MD5 nem aceitaria isso. E o RainbowCrack não consegue mirar bcrypt de jeito nenhum: o `rtgen` só constrói tabelas pra hashes sem salt (`lm`, `ntlm`, `md5`, `sha1`, `sha256` — sem bcrypt), porque pré-computação é sem sentido sob um salt-por-hash. Não há tabela pra gerar, e não há onde procurar o hash. A rainbow table não é *mais lenta* contra bcrypt — ela é *inaplicável*.

## Os dois lados diferem nas dependências

Incomum para este repo, `vulnerable/requirements.txt` e `fixed/requirements.txt` não são idênticos:

```diff
 Flask==3.0.0
+bcrypt==4.2.1
```

O lado vulnerável hasheia com a biblioteca padrão (`hashlib`, sem dependência). O lado corrigido traz uma biblioteca — `bcrypt` — porque o fix *é* o primitivo, e o primitivo certo é um KDF feito de propósito que você importa, não algo que você inventa na mão. O coração do diff continua sendo a mudança no `app.py`; a linha de dependência só acompanha.

## Impacto, e o contraste com o `jwt-weak-secret`

O impacto é recuperação de credencial levando a account takeover: a senha recuperada é a real da vítima, e senhas reusadas carregam o comprometimento para outros sistemas. Não é RCE.

O irmão deste átomo, [`jwt-weak-secret`](../jwt-weak-secret/), também é **A02 — Cryptographic Failures**, e também quebra um artefato criptográfico offline. Mas difere em todos os outros eixos, e o contraste é a lição:

| | `jwt-weak-secret` | `crypto-weak-hash` |
|---|---|---|
| Artefato quebrado offline | um **segredo de assinatura** (chave HMAC) | um **hash de senha** armazenado |
| O que o crack te dá | a chave → **forjar** tokens seus | a **senha real** da vítima → logar como ela |
| Propriedade violada | integridade / autenticidade | confidencialidade do segredo armazenado |
| Técnica | **dicionário** — hasheia cada chute ao vivo | **rainbow table** — pré-computa o trabalho de uma vez |
| O fix | trocar um **valor** fraco (o secret) | trocar o **primitivo** (hash rápido sem salt → KDF lento e salgado) |

Um quebra um segredo pra *forjar*; o outro recupera uma senha pra *se passar por*. Um hasheia chutes ao vivo; o outro pré-computa o trabalho adiantado. Mesma categoria, oposto em causa, consequência e técnica.
