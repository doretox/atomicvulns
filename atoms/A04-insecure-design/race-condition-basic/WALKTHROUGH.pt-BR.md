# Walkthrough — race-condition-basic

O alvo é uma API de conta pequena. `POST /withdraw` faz o mais comum do mundo: lê o seu saldo, checa se ele cobre o valor que você pediu, e — se cobre — debita. Três passos. Entre o passo que *checa* ("o saldo cobre?") e o passo que *age* ("debita") há uma fresta de tempo: um momento em que a decisão "você pode sacar" já foi tomada mas o débito ainda não aconteceu. Rode um saque e nada dá errado. Dispare vinte saques do saldo inteiro *de uma vez* e todos os vinte leem o saldo cheio, todos os vinte passam pela checagem antes de qualquer um debitar — e todos os vinte debitam. Você saca vinte vezes um dinheiro que só cobria um. Você não injetou nada e não forjou nada: mandou a mesma requisição legítima, só que ao mesmo tempo.

## 1. Contexto

`POST /withdraw` move dinheiro com base num saldo que ele lê primeiro. Pra ver o que dá errado você precisa de alguns termos, definidos do zero.

Uma **race condition** (condição de corrida) é uma situação em que dois ou mais fluxos de execução rodam ao mesmo tempo e o resultado depende da **ordem ou do timing** em que eles chegam nos passos — rode-os um de cada vez e o resultado é sempre certo, mas rode-os juntos e eles se atrapalham. O nome é literal: dois fluxos correndo pelo mesmo recurso, e quem chega primeiro em cada passo muda o resultado. O trecho de código que **lê e então modifica um estado compartilhado** — aqui, ler o saldo e debitá-lo — é a **seção crítica**; uma corrida é dois fluxos dentro dela ao mesmo tempo, se pisando.

Esta corrida em particular é um **TOCTOU** — **time-of-check to time-of-use**. Você *checa* uma condição (o time of check — "o saldo cobre?") e então *age* sobre ela (o time of use — "debita"). Se o estado muda entre o check e o use, você agiu sobre uma verdade que já tinha ficado **velha**. O intervalo entre o check e o act é a **fresta** (ou janela), e quanto mais larga ela é, mais fácil pra outro fluxo escorregar pra dentro dela.

O fix, nomeado de antemão, é **atomicidade**: uma operação é *atômica* quando é **indivisível** — ela acontece inteira ou não acontece, e nenhum outro fluxo consegue observar ou intercalar um estado no meio dela. O read-check-write em três passos *não* é atômico (há dois pontos onde outro fluxo entra); um único statement de banco que decide *e* escreve numa tacada *é*.

Isto é **A04 — Insecure Design**: a falha está no formato do fluxo, não num typo nem numa linha esquecida.

O lab são três serviços numa rede interna: `db` (um PostgreSQL compartilhado, sem porta no host), e os dois apps — `vulnerable` em `http://127.0.0.1:8035/` e `fixed` em `http://127.0.0.1:8135/`. O app é **multi-threaded**, então as requisições realmente rodam concorrentes, e cada requisição abre a própria conexão ao banco. Você conduz o ataque pelo **Burp**, com a extensão **Turbo Intruder** — a Seção 4 explica por que as ferramentas comuns não ganham uma corrida.

## 2. Achar o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). `POST /withdraw` lê, checa, depois escreve — três passos separados:

```python
cur.execute("SELECT balance FROM accounts WHERE id = 1")  # 1. read
balance = cur.fetchone()[0]
if balance < amount:  # 2. check, in Python, on a value that may be stale
    return jsonify({"error": "insufficient funds"}), 409
time.sleep(0.1)       # didactic crutch -- widens a window that already exists
cur.execute(          # 3. write -- no guard in SQL; the check lived back in Python
    "UPDATE accounts SET balance = balance - %s WHERE id = 1", (amount,)
)
conn.commit()
```

Pergunta de auditoria: *entre decidir que o saldo cobre o valor e de fato debitar, outra requisição poderia mudar o saldo?* Sim — nada segura a linha entre o `SELECT` e o `UPDATE`. O guard `if balance < amount` está lá, e está correto; ele só roda sobre um valor lido um instante antes, e a escrita confia nessa decisão agora velha. O `UPDATE` em si **não** carrega condição nenhuma — o check ficou lá atrás no Python, um passo distante da escrita que ele deveria proteger.

O `time.sleep(0.1)` é uma **muleta didática**, e vale ser franco sobre isso: ele alarga uma fresta que **já existe** pra a corrida reproduzir toda vez. A falha é real sem ele — a fresta entre um `SELECT` e um `UPDATE` posterior está lá com ou sem o sleep no meio; o sleep só a deixa larga o bastante pra você acertar na mão. Mais sobre isso depois de você ver a corrida (Seção 4), e sobre por que o fix torna o sleep irrelevante (Seção 7).

## 3. Baseline — o guard funciona uma requisição por vez

Antes da corrida, prove que o guard não está simplesmente ausente. Resete o saldo pra 100 e saque duas vezes, uma depois da outra:

```
$ curl -s -X POST 127.0.0.1:8035/reset
{"balance":100}
$ curl -s -X POST -H 'Content-Type: application/json' -d '{"amount":100}' 127.0.0.1:8035/withdraw
{"balance":0,"withdrew":100}
$ curl -s -X POST -H 'Content-Type: application/json' -d '{"amount":100}' 127.0.0.1:8035/withdraw
{"error":"insufficient funds"}
```

O primeiro saque passa (saldo 100 → 0); o segundo, sobre um saldo de 0, é recusado com `409`. O app vulnerable **rejeita** o saque a mais — sequencialmente. Rode a sequência idêntica contra o app fixed em `:8135` e você tem o resultado idêntico. Então a diferença entre os dois apps *não* é o guard: os dois têm, os dois o aplicam uma requisição por vez. Só a concorrência vai separá-los.

## 4. Exploração (no Burp, com o Turbo Intruder)

**Por que as ferramentas comuns não ganham.** O Repeater manda uma requisição por vez — nunca há um segundo fluxo pra correr. O Intruder padrão consegue mandar em paralelo, mas a rede **serializa** as requisições: mesmo uns poucos microssegundos de jitter fazem uma chegar, ler, checar e *escrever* antes de a próxima ler — e uma vez que o primeiro débito faz commit, o guard da segunda a recusa corretamente. Pra colocar várias requisições dentro da fresta *antes de qualquer uma escrever*, elas têm que chegar **juntas**.

Isso é o **single-packet attack**: uma técnica (da PortSwigger) que faz N requisições baterem no servidor no mesmo instante, neutralizando o jitter da rede. Sobre HTTP/2 ela empacota os bytes finais de 20–30 requisições num único pacote TCP; sobre HTTP/1.1 — que é o que este dev server do Flask fala — o Turbo Intruder usa a **last-byte synchronization** equivalente: manda todos os bytes de cada requisição menos o último, segura num *gate*, e libera os últimos bytes juntos. De qualquer forma, as requisições completam de uma vez. Instale o **Turbo Intruder** pelo **BApp Store** do Burp (Extensions → BApp Store) — é a única extensão que o átomo precisa, e a razão é a própria lição: uma corrida só reproduz com requisições genuinamente simultâneas.

Abra o **Turbo Intruder** pelo menu superior do Burp e escolha **Run script** — a janela dele abre pré-preenchida com um exemplo `example.com`, porta `443`, `https`. Corrija esses campos de conexão pra este átomo: ponha **Host** `127.0.0.1`, **Port** `8035`, e **Protocol** `http`. Cole a requisição no painel de requisição e o script no painel de script. A requisição é só o saque legítimo:

```
POST /withdraw HTTP/1.1
Host: 127.0.0.1:8035
Content-Type: application/json
Content-Length: 15

{"amount": 100}
```

No painel de script, use o script de corrida baseado em gate abaixo. Cole **só o corpo do script** — da linha `def queueRequests` em diante — e **não** a cerca de código em volta: um backtick perdido colado junto faz o Turbo Intruder falhar com `SyntaxError: expecting BACKQUOTE`.

```
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           engine=Engine.THREADED)
    for i in range(20):
        engine.queue(target.req, gate='race1')
    engine.openGate('race1')

def handleResponse(req, interesting):
    table.add(req)
```

Resete o saldo primeiro (`POST /reset` → `{"balance":100}`), depois rode o ataque. Cada uma das 20 linhas na tabela de resultados do Turbo Intruder volta **`200`**, cada corpo um `{"balance":...,"withdrew":100}` bem-sucedido. Leia o número final:

```
$ curl -s 127.0.0.1:8035/balance
{"balance":-1900}
```

Vinte saques de 100 cada passaram de uma conta que tinha **100**: `100 − 20×100 = −1900`. O invariante de negócio — nunca sacar além do saldo — foi estilhaçado, e toda requisição que fez isso era um saque perfeitamente legítimo. Tudo aqui é benigno e local: uma conta fake, um saldo dummy, tudo em loopback, nada destrutivo.

**De volta ao sleep.** Ele alargou a fresta pra uns ~100 ms confiáveis, então todos os vinte `SELECT`s chegam antes de o primeiro `UPDATE` fazer commit — que é por que você tira o `−1900` cheio toda vez, em vez de um overshoot parcial imprevisível. Tire o sleep e a fresta encolhe pra microssegundos; a corrida ainda acontece (ela é real), só deixa de ser garantia numa demo. O ponto é a **fresta**, não o sleep — e o fix fecha a fresta não importa quão larga ela seja.

## 5. O que a vuln NÃO é

A requisição é um saque comum, então isole o que de fato deu errado:

- **NÃO é input malicioso nem injection.** A requisição é **byte a byte idêntica** a um saque legítimo — um valor normal que o saldo cobre. A única diferença é que vinte cópias chegaram de uma vez. Este é o eixo que separa este átomo de todos os anteriores: nos átomos de injection a requisição do atacante carrega um payload, no [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) ela carrega um número trocado — aqui ela não carrega nada diferente, só um *timing* diferente.
- **NÃO é "faltou validação".** O app vulnerable **checa** `balance >= amount`; o guard existe. A Seção 3 prova que ele funciona sequencialmente, idêntico nos dois apps.
- **NÃO é "faltou um guard ou limite".** O guard está bem ali. A falha é **temporal** — a fresta entre o check e a escrita — não a ausência de um check.
- **NÃO é um bug pontual de código.** É uma falha de **desenho** (A04): um check-then-act não-atômico é um *padrão*, não um typo nem uma única linha esquecida.
- **NÃO se conserta "checando de novo".** Reler e re-checar logo antes da escrita deixa a mesma espécie de fresta entre essa segunda checagem e a escrita. Adicionar checagens não fecha a fresta; só a atomicidade fecha.

O que ela **é**: um check-then-act partido em passos separados, com uma fresta entre o check e a escrita na qual requisições concorrentes e legítimas caem juntas — cada uma passando pelo check antes de qualquer uma escrever, então todas escrevem, além do limite que o check deveria impor.

## 6. Impacto

**Um invariante de negócio violado.** As requisições concorrentes levam a conta a um estado que as regras proíbem: um **saldo negativo**, um saque além do saldo, o mesmo limit overrun em qualquer forma — resgatar um voucher várias vezes, gastar um gift card duas vezes, comprar mais estoque do que existe. Sem overclaim: isto não é execução de código nem roubo de credencial. O teto é exatamente o estado inconsistente que a corrida produz — aqui, `−1900` onde o piso era `0`. No mundo real isso é dinheiro movido que não deveria, e é um clássico de relatórios de bug bounty contra fluxos de pagamento, cupom, e saldo.

## 7. Por que o fix funciona

Agora confirme o fix — com uma ressalva sobre o setup. **Os dois apps compartilham a mesma tabela `accounts`** no mesmo container `db`, então o `GET /balance` reflete o que a última rajada deixou, seja qual app a recebeu. Pra testar o app fixed de forma limpa você tem que fazer duas coisas: **resetar o saldo no `:8135`** (`POST /reset` pra `http://127.0.0.1:8135/reset` → `{"balance":100}`) *antes* da rajada, e **trocar o Port na janela do Turbo Intruder de `8035` pra `8135`** — senão a rajada ainda cai no app vulnerable e você vai ver `−1900` no `/balance` mesmo achando que apontou pro fixed.

Com o saldo resetado e o Port em `8135`, rode o **mesmo** script de 20 requisições. Agora a tabela de resultados mostra exatamente **um** `200` e dezenove `409`s, e o saldo para onde deveria:

```
$ curl -s 127.0.0.1:8135/balance
{"balance":0}
```

Essa combinação — um `200`, dezenove `409`s, e um saldo final de `0` no `:8135` — é a prova de que o fix segura: um saque passou de um saldo de 100, e todos os outros foram recusados corretamente. O fix ([`fixed/app.py`](./fixed/app.py)) faz o checar-e-agir um único statement indivisível:

```python
cur.execute(
    "UPDATE accounts SET balance = balance - %s WHERE id = 1 AND balance >= %s",
    (amount, amount),
)
if cur.rowcount == 0:
    return jsonify({"error": "insufficient funds"}), 409
conn.commit()
```

Dois termos pra deixar isso preciso. Uma **transação** é um grupo de operações de banco que o banco trata como uma unidade, com regras sobre o que transações concorrentes enxergam umas das outras. O **`UPDATE` condicional** põe o check *dentro* da escrita — `WHERE id = 1 AND balance >= amount` — então o banco, não o Python, decide e escreve no mesmo instante. Quando o Postgres o roda, ele pega um **row lock** — uma garantia de que só uma transação toca aquela linha por vez, o que é **exclusão mútua** — re-checa `balance >= amount` contra o valor **corrente** da linha, e escreve, tudo como um passo só. O `rowcount` reporta o resultado: `1` debitou, `0` significa que a condição falhou e nada mudou.

Não há fresta de read-check-write, então não há janela pra correr. As vinte requisições ainda chegam juntas e o servidor ainda é multi-threaded; o Postgres simplesmente as serializa na linha. A primeira vê `100`, debita pra `0`, devolve `200`. Cada uma das outras, re-checando `balance >= 100` sob o lock contra o `0` agora corrente, falha, não muda nada, e devolve `409`. E como a atomicidade mora naquele único statement, o timing é irrelevante — é por isso que o `sleep` do app vulnerable não tem contraparte aqui: não há passo separado pra alargar.

Repare no que **não** mudou: `GET /`, `POST /reset`, `GET /balance`, a conexão ao banco, e os imports (fora o `time` agora sem uso) são byte a byte idênticos, e o app é tão multi-threaded quanto antes. A única diferença é a **atomicidade** do débito. Veja o [`DIFF.md`](./DIFF.md) pra a mudança de uma-operação e por que "checar de novo", um lock na aplicação, e o `SERIALIZABLE` são a resposta errada, parcial, ou mais pesada ao lado do `UPDATE` condicional.
