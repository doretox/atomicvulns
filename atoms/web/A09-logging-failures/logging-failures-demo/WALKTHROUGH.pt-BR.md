# Walkthrough — logging-failures-demo

A app é uma API de conta pequena com uma rota que importa: `POST /login`. Ela compara um email e uma senha com um hash guardado e responde `200` (autenticado) ou `401` (errado). O login está correto — query parametrizada, senhas hasheadas decentemente, um `401` limpo. A falha é o que acontece *em volta* do `401`: no lado vulnerable, uma falha de autenticação é registrada **em lugar nenhum** que signifique algo para segurança. Então quando um atacante roda um **brute-force** contra uma conta, o ataque não deixa rastro — ele é invisível. A prova deste átomo não é algo aparecendo na tela; é o **contraste entre dois logs** produzidos pelo *mesmo* ataque: o lado vulnerable é cego, o lado fixed vê.

A trilha é o **Burp Suite** — você conduz a rajada de brute-force contra o `POST /login` com o **Intruder** (ou um request repetido no **Repeater**). A prova é lida **fora** do Burp, na saída do próprio servidor: `docker compose logs vulnerable` versus `docker compose logs fixed`. Não há browser — a prova é texto de log, não uma tela.

## 1. Contexto

Uma API de conta pequena em `127.0.0.1:8038` (vulnerable) e `127.0.0.1:8138` (fixed):

- `GET /` — um banner JSON. Não é o alvo.
- `POST /login` — JSON `{"email", "password"}`. Verifica contra o password hash guardado; retorna `200 {"authenticated": true}` ou `401 {"authenticated": false}`. É o alvo do brute-force e o único ponto em que os dois lados diferem.

Este átomo é **A09 — Security Logging and Monitoring Failures**: a categoria sobre conseguir *saber* que um ataque aconteceu — detectá-lo, respondê-lo, e reconstruí-lo depois. Ele é o ponto fora da curva neste repo: não há payload que faça um arquivo marcador aparecer, nada vaza, nenhuma conta é tomada. A lição inteira é o que o lado vulnerable *deixa de anotar*.

Termos, definidos uma vez:

- **Brute-force / credential stuffing.** Um ataque de **brute-force** de login tenta **muitas senhas** contra uma conta até uma funcionar — martelando `victim@lab` com `123456`, `password`, `qwerty`, e por aí vai. **Credential stuffing** é o primo: reapresentar pares email:senha **vazados** contra muitas contas, apostando no reuso de senha. Os dois produzem o mesmo sinal observável — **uma rajada de falhas de autenticação** — e é esse sinal que um security log precisa capturar.
- **Security event.** Uma ocorrência que um time de segurança precisa saber: uma falha de autenticação, um acesso negado, uma mudança de privilégio, uma ação sensível. É distinto de um evento *operacional* comum (algum request chegou). Este átomo trata de um security event: a **falha de autenticação**.
- **Security log / audit trail.** O registro de **quem fez o quê, quando, e de onde** — o histórico dos security events. É o que um responder lê durante um incidente e o que um forense usa depois para reconstruir o que houve. Tratado como evidência, é uma **audit trail** (trilha de auditoria).
- **Structured log (log estruturado).** Uma linha de log com **campos claros**, legível por um humano *e* parseável por uma máquina — um **SIEM** (Security Information and Event Management: a plataforma que agrega logs e dispara alertas). `... WARNING security authentication failure account=victim@lab ip=10.0.0.5` tem campos identificáveis (`account=`, `ip=`) que uma ferramenta consegue filtrar, contar e alertar. Uma frase solta (`"login falhou"`) não ajuda nenhum dos dois.
- **Access log vs security log — a distinção-chave.** O **access log** registra **todo request** de forma genérica: IP de origem, timestamp, método, path, status (`10.0.0.5 - - [...] "POST /login" 401`). Ele captura o **transporte**, e é cego para segurança: não sabe **qual conta** um `POST /login` mirou (o email vai no *corpo*, não na URL), não classifica o `401` como falha de autenticação (para ele, status é status), e não **agrega** ("este é o vigésimo `401` da mesma origem contra a mesma conta"). O **security log** registra os **eventos que importam**, com o contexto que os torna acionáveis: o evento, a conta-alvo, a origem, e — somando — o padrão (`possible brute-force`).
- **Detection vs prevention (detecção vs prevenção).** **Prevention** *bloqueia* um ataque (rate-limiting, lockout de conta, um WAF). **Detection** *vê* o ataque (o security log mais um alerta). São defesas diferentes e complementares — você quer as duas. **A09 é sobre detection**: a capacidade de *saber*. Este átomo conserta a cegueira (detection); ele **não** adiciona um bloqueio (prevention).
- **Por que você nunca loga o segredo.** O security log registra o **fato** de uma falha (que houve uma, para qual conta, de qual IP, quando) — **nunca o segredo** (a senha tentada, tokens, PII). Um log é lido por muita gente, replicado, e retido por muito tempo; escrever uma senha nele transforma o próprio log num vazamento de credencial (o que *também* é uma falha A09). Logue o **fato**, não o **segredo**.

## 2. Achar o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py) e leia o caminho da falha do `login()`:

```python
    if row and check_password_hash(row["password_hash"], password):
        return jsonify({"authenticated": True})
    # (nada aqui)
    return jsonify({"authenticated": False}), 401
```

A pergunta de auditoria **não** é "o login está errado?" — não está; ele rejeita a senha errada com um `401` limpo, exatamente como deveria. A pergunta é **"quando isto retorna `401`, o que o sistema registra sobre o evento?"** A resposta: nada de segurança. Uma senha errada *é* um security event — alguém falhou em se autenticar como `email` de algum IP de origem — mas nenhuma linha de segurança é escrita. A única coisa que sobra é o access log genérico do servidor, que não consegue nomear a conta-alvo e não consegue distinguir um ataque de um typo. O fix (seção 7) não toca no login; ele *acrescenta* o registro que falta.

## 3. Baseline — o login funciona, idêntico

Primeiro, para você saber o que é "normal". Aponte o Burp para `127.0.0.1:8038` (vulnerable). Um login correto:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8038
Content-Type: application/json

{"email": "victim@lab", "password": "victim-lab-pw"}
```

```
HTTP/1.1 200 OK
{"authenticated":true}
```

Uma senha errada isolada:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8038
Content-Type: application/json

{"email": "victim@lab", "password": "hunter2"}
```

```
HTTP/1.1 401 UNAUTHORIZED
{"authenticated":false}
```

As duas respostas são **idênticas no lado fixed (8138)**. Um `401` isolado é rotina — um usuário errando a digitação — não um alarme. A história só muda quando as falhas vêm numa **rajada**.

## 4. O ataque — a mesma rajada, e os dois logs

### Passo 1 — Rodar a rajada de brute-force (Burp Intruder), lado vulnerable

Mande o request `POST /login` para o **Intruder**. Marque o valor da senha como a única posição de payload (Sniper):

```
POST /login HTTP/1.1
Host: 127.0.0.1:8038
Content-Type: application/json

{"email": "victim@lab", "password": "§123456§"}
```

Carregue uma lista de senhas comuns como o payload set — o tipo de lista que um brute-force real usa:

```
123456
password
12345678
qwerty
123456789
letmein
football
iloveyou
admin
welcome
... (20 no total)
```

Comece o ataque. As vinte respostas voltam `401` — a lista não contém a senha real de `victim@lab`, então a rajada nunca acerta. E tudo bem: este átomo não é sobre *parar* o ataque, é sobre *ver* o ataque. (Um Repeater repetido, ou o Turbo Intruder, faz o mesmo trabalho.)

### Passo 2 — Ler o log do vulnerable: cego

```
$ docker compose logs vulnerable
```

```
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "GET / HTTP/1.1" 200 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:27] "POST /login HTTP/1.1" 401 -
vulnerable-1  | 172.22.0.1 - - [11/Sep/2026 15:03:27] "POST /login HTTP/1.1" 401 -
   ... (vinte linhas "POST /login 401" idênticas no total)
```

Esse é o registro inteiro do ataque. Vinte `401`s, todos idênticos. Nada aqui diz qual conta foi mirada (o email estava no corpo, que o access log nunca vê), nada rotula isso como falhas de autenticação, e nada agrega em "um ataque". Vinte tentativas de invasão contra `victim@lab` são indistinguíveis de vinte pessoas errando a própria senha. Um pipeline de monitoração chaveado em security events recebe **nada**, porque nada de segurança foi emitido.

Note o que isto **não** é: **não** é "log nenhum". O access log HTTP genérico está bem ali. É o log na **altitude errada** — transporte, não segurança. Essa distinção é o átomo inteiro. (O IP de origem aparece como `172.22.0.1` porque, atrás do Docker, esse é o gateway que a app vê; o ponto é o *campo*, não o valor — um deploy real atrás de um proxy registraria o endereço do cliente via `X-Forwarded-For`.)

### Passo 3 — Rodar a mesma rajada contra o lado fixed (8138)

Repita o Passo 1 contra `127.0.0.1:8138` — o mesmo request, a mesma lista de senhas:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8138
Content-Type: application/json

{"email": "victim@lab", "password": "§123456§"}
```

Toda resposta é de novo `401`. O lado fixed **não** trava a conta nem faz throttle da origem — o ataque roda até o fim exatamente como antes. O que muda é só o que é anotado.

### Passo 4 — Ler o log do fixed: ele vê

```
$ docker compose logs fixed
```

```
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:26] "GET / HTTP/1.1" 200 -
fixed-1  | 2026-09-11 15:03:30,071 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,249 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,438 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,610 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
fixed-1  | 2026-09-11 15:03:30,786 INFO security authentication failure account=victim@lab ip=172.22.0.1
fixed-1  | 2026-09-11 15:03:30,786 WARNING security possible brute-force against victim@lab from 172.22.0.1 (5 failures)
fixed-1  | 172.22.0.1 - - [11/Sep/2026 15:03:30] "POST /login HTTP/1.1" 401 -
   ... (a linha INFO security se repete para cada uma das vinte tentativas; o WARNING dispara uma vez, na quinta)
```

Mesmo ataque, os mesmos vinte `401`s — mas agora cada falha está no registro como um **security event**: o evento (`authentication failure`), a **conta-alvo** (`account=victim@lab`), a **origem** (`ip=172.22.0.1`), e um **timestamp**. E assim que cinco falhas contra uma conta se acumulam, um `WARNING` nomeia o padrão sem rodeios: `possible brute-force against victim@lab from 172.22.0.1`. É isto que um responder ou um SIEM precisa — transforma uma parede de `401`s idênticos num ataque nomeado, atribuível e alertável.

Duas coisas para notar. Primeiro, o access log genérico **continua ali** — as mesmas linhas do lado vulnerable. O security log foi *acrescentado ao lado* dele; o contraste é segurança-ausente versus segurança-presente, não log-nenhum versus log. Segundo, as senhas tentadas (`123456`, `qwerty`, …) aparecem **em lugar nenhum** do log. O registro é o fato — falha, conta, origem, hora — nunca o segredo.

> Este é um lab local: os dois apps bindam em `127.0.0.1`, os usuários e senhas são dummy (`victim@lab`, senhas de lab obviamente falsas), e o "ataque" é uma rajada de logins com senha errada de uma lista — nada aqui é destrutivo e nada sai da máquina. A rajada nem chega a adivinhar a senha; esse não é o ponto.

## 5. O que a vuln NÃO é

Cinco conclusões erradas para matar. Cada uma mantém este átomo distinto de um vizinho.

**NÃO é rate-limiting (nem lockout).** O lado fixed **detecta e registra** o brute-force; ele **não bloqueia** — cada uma das vinte tentativas ainda responde `401`, e o atacante poderia seguir. Travar a conta ou fazer throttle do IP seria uma defesa *adicional* boa, mas é **prevention** — outra coisa. Adicioná-la aqui mudaria a lição para "faltou um lockout no login", que não é esta falha. O furo é a **cegueira**, não a trava que falta.

**NÃO é logar o segredo.** O fix registra o **evento** — falha, conta, IP, timestamp — e nunca a senha tentada. Escrever a senha no log é o anti-padrão *oposto*: transforma o log num vazamento de credencial, e é **também** uma falha A09. Logue o fato, não o segredo.

**NÃO é um bug no login.** O login funciona e é **byte-a-byte idêntico** nos dois lados (mesma query parametrizada, mesmo `check_password_hash`, mesmo `200`/`401`). Ele rejeita senhas erradas corretamente. A falha é ele ser **cego** ao ataque — não deixar registro de segurança dele.

**NÃO é como os outros átomos.** Em todo o resto deste repo você prova a vulnerabilidade fazendo *algo acontecer* — um arquivo marcador, linhas vazadas, um takeover. Aqui a prova é a **ausência** de rastro no lado vulnerable versus o rastro no lado fixed: o *mesmo* ataque, um log cego e um que vê. A "vitória" do atacante no lado vulnerable é justamente que **nada foi registrado**.

**NÃO é sobre parar o brute-force.** A rajada nem precisa adivinhar a senha — as vinte tentativas falham, e a lição está completa. O ponto não é impedir o ataque; é *ver* que ele aconteceu. (Fazer a rajada acertar deslizaria o foco para "senha fraca" ou "faltou lockout" — categorias diferentes.)

O que **é**, cirurgicamente: um security event — uma rajada de falhas de autenticação contra uma conta — acontece e **não é registrado**. O lado vulnerable é cego (só o access log genérico); o lado fixed vê (uma linha de segurança estruturada por falha, mais um WARNING no limiar). O fix gera o security log que falta — logando o fato, nunca o segredo, e sem bloquear o ataque.

## 6. Impacto

Cegueira. No lado vulnerable o brute-force roda e aparece **em lugar nenhum** que um sistema de monitoração pegaria: ninguém é alertado, o time de resposta a incidente não tem o que investigar, e um forense depois não tem rastro para reconstruir **o que** houve, **quando**, ou **de onde**. A09 é, sem rodeios, "quanto tempo até você descobrir que foi invadido" — e relatórios reais medem esse dwell time em **meses**. O teto do dano é *não saber*: no mundo real uma dessas tentativas de brute-force eventualmente acerta, e sem registro, ninguém investiga. (Que o chute eventualmente funcione é outra categoria — senha fraca, ou um lockout que falta; aqui o foco fica na visibilidade.)

## 7. Por que o fix funciona (porta 8138)

Você já viu no Passo 4: o **mesmo** ataque, agora visível. O lado fixed não muda nada no login — mesma query, mesmo hash check, mesmo `200`/`401`, e a rajada ainda roda até o fim sem ser bloqueada — ele só **acrescenta o security log** no caminho da falha: uma linha estruturada por falha (`authentication failure account=… ip=…`), e um `WARNING … possible brute-force …` assim que cinco falhas contra uma conta se acumulam. Isso basta para detectar o ataque e investigá-lo: qual conta, qual origem, quando, quantas.

A prova de isolamento: o login (e o access log genérico) é idêntico nas duas portas; só o security logging os separa. A mudança é pura **observabilidade** — detecção, não prevenção, e o fato, não o segredo. Veja o [`DIFF.md`](./DIFF.md) para o diff linha a linha e por que "só adicionar um lockout" e "só logar a tentativa" são ambas a leitura errada do fix.
