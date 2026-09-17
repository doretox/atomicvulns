# DIFF — vulnerable vs. fixed

O fix é uma coisa só: tornar o checar-e-agir **atômico**. O app vulnerable lê o saldo, checa em Python, e então escreve o débito — três passos separados com uma fresta entre o check e a escrita. O app fixed dobra o check dentro da escrita como um único `UPDATE` condicional que o banco serializa por linha. Todo o resto — `GET /`, `GET /balance`, `POST /reset`, a conexão por request, o `requirements.txt`, o `Dockerfile` — é idêntico, então a atomicidade do débito é a *única* diferença entre os dois apps.

## A mudança — `app.py`

```diff
-import time
 ...
 @app.route("/withdraw", methods=["POST"])
 def withdraw():
     amount = (request.get_json(silent=True) or {}).get("amount")
     conn = db()
     try:
         cur = conn.cursor()
-        cur.execute("SELECT balance FROM accounts WHERE id = 1")   # 1. read
-        balance = cur.fetchone()[0]
-        if balance < amount:                     # 2. check, in Python (maybe stale)
-            return jsonify({"error": "insufficient funds"}), 409
-        time.sleep(0.1)                           # crutch: widen the window
-        cur.execute(                              # 3. write -- no guard in SQL
-            "UPDATE accounts SET balance = balance - %s WHERE id = 1", (amount,)
-        )
+        cur.execute(                              # decide AND write, atomically
+            "UPDATE accounts SET balance = balance - %s WHERE id = 1 AND balance >= %s",
+            (amount, amount),
+        )
+        if cur.rowcount == 0:                     # 0 rows changed => didn't cover it
+            return jsonify({"error": "insufficient funds"}), 409
         conn.commit()
         cur.execute("SELECT balance FROM accounts WHERE id = 1")
         return jsonify({"withdrew": amount, "balance": cur.fetchone()[0]})
     finally:
         conn.close()
```

O guard da versão vulnerable é um `if` de Python sobre um valor lido um statement antes; o `UPDATE` que segue não carrega condição. A versão fixed move o guard **pra dentro** da cláusula `WHERE` do `UPDATE` e lê o `cur.rowcount` pra saber o que aconteceu. O import `time` vai embora junto com o sleep — não sobrou passo separado pra esperar.

## Por que isto corrige o bug

`UPDATE ... WHERE id = 1 AND balance >= amount` faz o banco decidir e escrever num passo indivisível. Pra rodá-lo, o Postgres pega um **row lock** na conta 1 — só uma transação pode segurá-lo por vez — avalia `balance >= amount` contra o valor committed **corrente** da linha, e escreve, depois libera o lock pra a próxima transação. Então quando vinte requisições chegam juntas, o Postgres as enfileira nesse lock: a primeira vê `100`, debita pra `0`, e o `rowcount` dela é `1`; cada uma depois dela, re-checando `balance >= 100` sob o lock contra o `0` agora corrente, não casa com linha nenhuma, não muda nada, e o `rowcount` dela é `0` — um `409`. A condição nunca pode ser avaliada contra um valor que uma escrita concorrente está prestes a invalidar, porque a escrita *é* o mesmo statement travado. Sem fresta, sem janela, sem corrida.

## A causa é a não-atomicidade — não "faltou validação", não "faltou um guard"

A leitura errada tentadora é que o app vulnerable "esqueceu de checar o saldo". Não esqueceu. `if balance < amount: return 409` está bem ali, e funciona: rode um saque por vez e o app corretamente recusa passar do saldo — o baseline no `WALKTHROUGH.md` mostra o segundo saque sequencial levando um `409` no app vulnerable, idêntico ao fixed. O guard existe e impõe a regra sequencialmente. O que ele não faz é permanecer **atômico** com a escrita que ele protege: o check roda sobre um valor que uma requisição concorrente consegue deixar velho antes de a escrita acontecer. Prova de isolamento: um saque único, não-concorrente, se comporta idêntico nos dois apps; só a rajada concorrente os separa. A causa é o check-then-act não-atômico, nada mais — que é por que isto é uma falha de *desenho* (A04), não uma linha esquecida.

## Armadilha: "só checar de novo"

O instinto é reler o saldo e re-checá-lo logo antes da escrita:

```python
# STILL VULNERABLE -- do not do this
cur.execute("SELECT balance FROM accounts WHERE id = 1")
if cur.fetchone()[0] < amount:
    return jsonify({"error": "insufficient funds"}), 409
cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = 1", (amount,))
```

Isso só move a fresta; não a fecha. Entre esse segundo `SELECT` e o `UPDATE` há a mesma espécie de gap, e requisições concorrentes caem nele exatamente como antes. Você pode adicionar uma terceira checagem e uma quarta — cada uma ainda tem um gap entre *ela* e a escrita. O número de checagens não é o problema; o fato de o check e a escrita serem **operações separadas** é. Só torná-las uma operação atômica remove a janela.

## Armadilha: um lock na aplicação funciona num processo — mas não escala

Uma resposta parcial, real e honesta, é envolver a seção crítica num lock na aplicação:

```python
LOCK = threading.Lock()
...
with LOCK:                       # only one thread in the critical section at a time
    # read, check, write
```

Isto **funciona** — num único processo. É exclusão mútua genuína: só uma thread entra no read-check-write por vez, então a corrida thread-contra-thread some, e contra o servidor Flask single-process deste átomo ela seguraria. Seja preciso sobre por que não é o fix geral: ele não escala além de **um processo**. Rode o app sob múltiplos workers, ou em dois servidores atrás de um load balancer, e cada processo tem o **próprio** `threading.Lock` na própria memória — eles não o compartilham — então duas requisições atendidas por dois processos ficam sem sincronia e a corrida volta. O `UPDATE` condicional empurra a exclusão mútua pra baixo, pro **banco**, o único ponto que todo processo já compartilha, que é por que ele é o fix idiomático e escalável. O lock é um fix legítimo pra um único processo, não uma ideia errada — só uma que para de funcionar no instante em que você escala pra fora.

## O sleep é uma muleta didática — o fix o torna irrelevante

O `time.sleep(0.1)` no app vulnerable é uma **muleta nomeada**, não a vulnerabilidade. Ele alarga uma fresta que já existe — o gap entre um `SELECT` e um `UPDATE` posterior é inerente a ler, checar e escrever em passos separados — pra que a demo reproduza o `−1900` cheio toda vez, em vez de um overshoot parcial dependente de timing. Tire-o e a falha ainda é real; só fica mais difícil de acertar na mão de forma confiável. O app fixed não tem sleep porque não tem passo separado pra esperar: o `UPDATE` condicional fecha a janela não importa o timing. Se você desconfiava que o fix só "ganha" por ser mais rápido, adicione o mesmo `time.sleep(0.1)` antes do `UPDATE` condicional no app fixed e rode a rajada de novo — ele ainda deixa exatamente um saque passar. A correção é a atomicidade, não a velocidade.

## O `SERIALIZABLE` também resolve — o `UPDATE` condicional é só o fix mínimo

Pra ser completo e honesto: o `UPDATE` condicional não é o *único* fix correto. Rodar o read-check-write original dentro de uma transação no nível de isolamento **`SERIALIZABLE`** também fecha a corrida — o Postgres detecta que as transações concorrentes não podem ser ordenadas de forma consistente e aborta uma com um erro de serialização, então a perdedora tem que tentar de novo. É uma abordagem legítima e correta, e a certa quando a seção crítica abrange vários statements que não podem ser colapsados em um. Aqui ela seria mais pesada do que o problema precisa: significa capturar a falha de serialização e fazer um loop de retry. O `UPDATE` condicional é o fix mínimo e mais direto — um statement, sem loop de retry — que é por que o átomo o usa. Os dois são corretos; o fix de statement único é simplesmente o menor que faz o serviço.

## O impacto é um invariante de negócio violado — e não há input malicioso

A corrida leva a conta a um estado que as regras de negócio proíbem: um saldo negativo, um saque além do saldo, um limit overrun em qualquer forma (resgatar um voucher várias vezes, gastar um gift card duas vezes, vender mais estoque do que existe). Sem overclaim — isto não é execução de código nem roubo de credencial; o teto é o estado inconsistente que a corrida produz. O que mais nitidamente distingue esta classe das outras deste repo é que **não há input malicioso nenhum**. O exploit de todo átomo anterior muda *algo* na requisição; este só muda o timing dela:

| Átomo | O que a requisição do atacante carrega |
|---|---|
| [`sqli-union-basic`](../../A03-injection/sqli-union-basic/) e os átomos de injection | um **payload** — o input carrega sintaxe ou código |
| [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) | um **número trocado** (`/notes/1` → `/notes/2`) — dado legítimo, mas diferente |
| [`mass-assignment`](../../A01-broken-access-control/mass-assignment/) | um **campo a mais** no corpo (`"is_admin": true`) |
| [`cors-wildcard`](../../A05-security-misconfiguration/cors-wildcard/) | um **cabeçalho forjado** (o `Origin:` do atacante) |
| **`race-condition-basic`** (este átomo) | **nada** — byte a byte um saque legítimo; só a concorrência difere |

A regra de bolso: uma race condition não é uma requisição ruim, é um *schedule* ruim. A defesa não é inspecionar a requisição com mais rigor — ela é legítima — mas tornar a mudança de estado que age sobre ela **atômica**.
