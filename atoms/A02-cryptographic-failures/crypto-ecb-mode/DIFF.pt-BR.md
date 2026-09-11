# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em exatamente uma coisa: o **modo de cifra**. O lado vulnerable cifra o crachá com AES-ECB; o lado fixed usa AES-GCM. Essa mudança toca o import de padding, o `issue_badge` e o `read_badge` — nada mais. `GET /`, `POST /login`, `GET /me`, o parse de `email=...&role=...` e as portas são byte-idênticos. E, diferente do `crypto-weak-hash`, os dois lados compartilham um `requirements.txt` **idêntico** (veja abaixo).

## O fix — trocar o modo

```diff
 import os
 from Crypto.Cipher import AES
-from Crypto.Util.Padding import pad, unpad
 from flask import Flask, request, jsonify
```

```diff
 def issue_badge(email, role):
     plaintext = f"email={email}&role={role}".encode()
-    cipher = AES.new(KEY, AES.MODE_ECB)
-    return cipher.encrypt(pad(plaintext, AES.block_size)).hex()
+    cipher = AES.new(KEY, AES.MODE_GCM)
+    ct, tag = cipher.encrypt_and_digest(plaintext)
+    return (cipher.nonce + tag + ct).hex()


 def read_badge(token):
-    cipher = AES.new(KEY, AES.MODE_ECB)
-    plaintext = unpad(cipher.decrypt(bytes.fromhex(token)), AES.block_size)
+    raw = bytes.fromhex(token)
+    nonce, tag, ct = raw[:16], raw[16:32], raw[32:]
+    cipher = AES.new(KEY, AES.MODE_GCM, nonce=nonce)
+    plaintext = cipher.decrypt_and_verify(ct, tag)
     return dict(kv.split("=", 1) for kv in plaintext.decode().split("&"))
```

`AES.MODE_ECB` — determinístico, blocos independentes e não-autenticado — vira `AES.MODE_GCM`, um modo autenticado. Na escrita, `encrypt_and_digest` devolve uma **tag** de autenticação e a cifra gera um **nonce** novo, os dois empacotados junto do ciphertext. Na leitura, `decrypt_and_verify` recomputa a tag e **levanta exceção** se um único byte foi alterado — então o crachá recombinado é rejeitado no handler do `except` (`400`) antes de o role ser parseado. O ECB precisava de PKCS#7 padding (`pad`/`unpad`); o GCM é um modo de stream e não precisa de nenhum, então esse import some. Os endpoints ao redor da cifra nunca mudaram. É esse o fix inteiro.

## A causa é o modo, não a chave nem o AES

O bug não é "a chave é fraca" nem "o AES é quebrado". A chave é uma constante dummy, **idêntica nos dois lados**, e o ataque nunca a toca — a forja é puro rearranjo de blocos. O AES em si está sólido: o lado fixed é o *mesmo* AES com a *mesma* chave, e o ataque morre. O que mudou foi só *como os blocos são encadeados e autenticados* — o modo. Buscar uma chave mais longa ou uma cifra diferente não corrigiria nada.

## "Só trocar por CBC" não é o fix

A leitura tentadora: *o problema era o padrão vazando e o cut-and-paste limpo, então troca ECB por CBC e os dois somem.* Meio certo, e vale ser honesto sobre isso. O CBC (Cipher Block Chaining) faz XOR de cada bloco de plaintext com o bloco de ciphertext anterior antes de cifrar, então blocos de plaintext idênticos deixam de produzir ciphertext idêntico — o padrão **para de vazar** (sem penguin) — e os blocos deixam de ser independentes, então o splice limpo de copiar-um-bloco-igual **para de funcionar**. Isso é uma melhora real, não uma armadilha.

Mas não é o fix, porque o CBC deixa o crachá **não-autenticado**. Nada no CBC deixa o servidor *detectar* que um token foi alterado — o ciphertext continua sem carregar prova de integridade, então um crachá adulterado segue adulterável por outros meios. Sair do ECB é **necessário mas não suficiente**. A lição mais funda: um token de autoridade cifrado à mão sem autenticação é frágil em *qualquer* modo. A resposta não é um modo não-autenticado diferente — é um modo **autenticado** (AEAD: GCM, ou CCM), onde uma tag prova que o ciphertext é exatamente o que o servidor emitiu. Confidencialidade nunca foi a propriedade faltando; integridade foi.

## Determinístico vs. randomizado — o nonce

O ECB não tem IV nem nonce, então é **determinístico**: o mesmo plaintext sempre cifra pro mesmo ciphertext. É exatamente isso que vaza o padrão (blocos idênticos transparecem) e o que deixa um atacante reconhecer e reusar um bloco. O GCM pega um **nonce** único por mensagem, então o mesmo plaintext cifra diferente toda vez — emita o mesmo crachá duas vezes e os dois tokens não compartilham byte nenhum. Determinismo é uma propriedade do modo, e é metade do porquê de o ECB ser inseguro pra qualquer coisa estruturada.

## Os dois lados compartilham as dependências

Diferente do `crypto-weak-hash`, cujo fix trouxe uma lib nova (`bcrypt`), aqui `vulnerable/requirements.txt` e `fixed/requirements.txt` são **idênticos**:

```
Flask==3.1.3
pycryptodome==3.21.0
```

Tanto o ECB quanto o GCM vêm do mesmo `pycryptodome` já em uso. O fix é uma mudança de modo de uma linha no código, não uma dependência — um bom lembrete de que corrigir uma falha de crypto costuma ser *usar o primitivo corretamente*, não instalar algo novo.

## Impacto, e o contraste com o `crypto-weak-hash`

O impacto é forja de token levando a escalada de privilégio: um crachá que decifra em `role=admin`, cunhado sem credencial de admin e sem a chave. Não é RCE, e não é recuperação de chave — o teto é o que o role forjado destrava.

O irmão deste átomo, [`crypto-weak-hash`](../crypto-weak-hash/), também é **A02 — Cryptographic Failures**, e os dois "parecem crypto". Mas são opostos no mecanismo, e o contraste é a lição:

| | `crypto-weak-hash` | `crypto-ecb-mode` |
|---|---|---|
| Primitivo / artefato | um **hash** mão-única (MD5) de uma senha armazenada | uma **cifra** reversível (AES) num **modo** quebrado (ECB) |
| O que o atacante faz | **recupera** a senha original (o input) | **forja** um plaintext novo (rearranja blocos) |
| Técnica | **rainbow table** — pré-computa hash→senha | **cut-and-paste** — recombina blocos de ciphertext |
| A chave/segredo é quebrada? | a senha é recuperada por adivinhação em massa | **não** — a chave nunca é tocada |
| Causa raiz | **primitivo** errado (hash rápido, sem salt) | **modo** errado (blocos determinísticos independentes + sem autenticação) |
| O fix | trocar o primitivo (hash rápido → KDF lento e salgado) | trocar o modo (ECB → AEAD autenticado/GCM) |

Um recupera um segredo pré-computando; o outro forja rearranjando estrutura. Ele também compartilha o *objetivo* — forjar um token de autoridade pra escalar — com os átomos JWT [`jwt-none-alg`](../jwt-none-alg/) e [`jwt-key-confusion`](../jwt-key-confusion/): lá a forja ataca a assinatura do token, aqui ela ataca o modo de cifra do token. Mesma categoria, superfície diferente.
