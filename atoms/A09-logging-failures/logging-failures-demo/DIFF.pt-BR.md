# DIFF — vulnerable vs. fixed

O login é **idêntico** nos dois lados — mesma query parametrizada, mesmo `check_password_hash`, mesmo `200`/`401`. O `diff vulnerable/app.py fixed/app.py` mostra só quatro coisas, todas de logging: o `import logging`, o setup do security logger, uma linha que zera o contador de falhas no sucesso, e o caminho da falha enriquecido. O `requirements.txt` e o `Dockerfile` são byte-idênticos. Este é um *tipo* de diff diferente de todos os outros átomos: nada no comportamento da app muda — o fix só torna o comportamento existente **visível**.

## O fix — adicionar o security log que faltava

```diff
 import os
+import logging
 import sqlite3
 from flask import Flask, request, jsonify
 from werkzeug.security import generate_password_hash, check_password_hash

 app = Flask(__name__)
 DB_PATH = os.environ.get("DB_PATH", "lab.db")
+
+# How many consecutive failures against one account raise a brute-force WARNING.
+BRUTE_FORCE_THRESHOLD = 5
+
+# In-memory per-account failure counter: email -> consecutive failures. Reset on success.
+FAILURES = {}
+
+# A dedicated SECURITY logger, separate from Werkzeug's generic HTTP access log, writing
+# structured lines to the container's output. A dedicated logger + propagate=False leaves
+# Werkzeug's logger untouched, so the access log still appears on BOTH sides.
+_handler = logging.StreamHandler()
+_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
+security_log = logging.getLogger("security")
+security_log.setLevel(logging.INFO)
+security_log.addHandler(_handler)
+security_log.propagate = False
 ...
     if row and check_password_hash(row["password_hash"], password):
+        FAILURES.pop(email, None)  # a success clears the account's failure streak
         return jsonify({"authenticated": True})
-    # (nothing here — the authentication failure is recorded nowhere security-relevant)
+    # Record the FACT of the failure -- event, account, source IP, timestamp -- NEVER the secret.
+    ip = request.remote_addr
+    security_log.info("authentication failure account=%s ip=%s", email, ip)
+    FAILURES[email] = FAILURES.get(email, 0) + 1
+    if FAILURES[email] == BRUTE_FORCE_THRESHOLD:
+        security_log.warning("possible brute-force against %s from %s (%d failures)",
+                             email, ip, FAILURES[email])
     return jsonify({"authenticated": False}), 401
```

Essa é a mudança inteira. O caminho da falha — que no lado vulnerable só retorna `401` — agora emite um **security event** estruturado para cada falha, e assim que cinco falhas contra uma conta se acumulam, um `WARNING` que nomeia o padrão. Nada mais muda: a query, o hash check, os status codes, o `init_db`, o seed, e o server model `threaded=False` são iguais nos dois lados.

Este é um *tipo* de diff diferente do resto do repo. No `deserialization-pickle` o diff é uma mudança de lógica (`pickle` → `json`); no `debug-enabled` é uma flag (`debug=True` → `False`); no `cve-demo` é uma versão de dependência no `requirements.txt`. Aqui o comportamento do código está intacto — o login faz exatamente o que fazia — e o fix só **acrescenta observabilidade**. A vulnerabilidade não é uma linha errada; é uma linha que **falta**.

## A causa é o security log que falta, não um bug no login

É tentador ler "o ataque é invisível" e caçar o erro no `login()`. Não há: o login está correto e é **byte-a-byte idêntico** nos dois lados. Prova de isolamento: um login legítimo retorna `200` e uma senha errada isolada retorna `401` nos **dois** lados — a feature é a mesma. Rode a *mesma* rajada de brute-force contra os dois e a única coisa que difere é o registro que ela deixa:

- `docker compose logs vulnerable` → vinte linhas de acesso `"POST /login" 401` idênticas. Sem conta, sem "authentication failure", sem limiar. **Cego.**
- `docker compose logs fixed` → as mesmas linhas de acesso, **mais** uma linha `INFO security authentication failure account=victim@lab ip=…` por tentativa, **mais** um `WARNING … possible brute-force against victim@lab … (5 failures)` na quinta. **Ele vê.**

A diferença é 100% o security logging. Não há o que "sanitizar" no login — o mesmo login, com o security log acrescentado, torna o mesmo ataque visível.

## "Só adicionar um lockout / rate-limit" é uma defesa real — mas não é o fix deste átomo

Mostre este átomo para um revisor e o reflexo é imediato: *"trava a conta, ou faz throttle do IP de origem, depois de N falhas."*

Isso é **verdade** e vale fazer — rate-limiting e lockout são defense-in-depth genuína contra brute-force. Mas são **prevention** — eles *bloqueiam* o ataque — e este átomo é sobre **detection**: conseguir *ver* o ataque. O lado fixed deliberadamente **não** bloqueia: cada uma das vinte tentativas ainda responde `401`, e o atacante poderia seguir. Adicionar um lockout mudaria a lição para "o login precisava de um bloqueio", que é outra categoria (uma falha de desenho/prevenção) e enterraria o ponto do A09.

Os dois não estão em conflito — você quer detection *e* prevention — mas não se substituem, e este átomo conserta o que faltava: **visibilidade**. A armadilha a evitar: um leitor que saia daqui achando "então o fix é rate-limiting" perdeu o A09 inteiro — teria bloqueado *este* ataque enquanto continua cego ao próximo, e a tudo que um lockout não pega. (É a mesma forma de honestidade-em-camadas da nota do salt no `crypto-weak-hash`, da nota do `safe_load` no `cve-demo`, ou da nota de uso-único/expiração no `weak-password-reset`: o controle nomeado tem valor real, mas não é o fix de causa deste átomo.)

## Logue o fato, nunca o segredo

Note quais campos a linha de segurança carrega: o **evento** (`authentication failure`), a **conta** (`account=victim@lab`), a **origem** (`ip=…`), e um **timestamp**. Ela **não** carrega um campo `password=`. Essa omissão é deliberada e importa: um log é lido por muita gente, enviado a um SIEM, e retido por muito tempo, então escrever a senha tentada nele transformaria o próprio log num dump de credenciais — o anti-padrão *oposto*, e **também** uma falha A09 (dado sensível em logs). Logue o **fato**, não o **segredo**. (Uma audit trail mais completa também registraria os *sucessos* de login — quem autenticou, quando, de onde — não só as falhas; este lab loga o caminho da falha porque é onde a lição mora, mas a mesma regra "o fato, não o segredo" vale para todo evento que você registra.)

## A prova é a ausência — e como isso separa este átomo

Todo outro átomo deste repo prova sua vulnerabilidade fazendo **algo acontecer**: um arquivo marcador aparece, linhas vazam, uma conta é tomada. Este é o oposto — o "resultado" do lado vulnerable é que **nada é registrado**, e você só vê isso por contraste com o lado fixed. "Um átomo, uma vulnerabilidade" é sobre a **causa**, e a causa aqui é um security log *ausente*. Os eixos que mantêm este átomo distinto dos vizinhos:

| Eixo | O vizinho | `logging-failures-demo` (38) |
|---|---|---|
| Forma da prova (vs **todo** átomo anterior) | algo **aparece** — um marcador `/tmp/pwned` (`cve-demo`, `deserialization-pickle`), linhas vazadas (`sqli-union-basic`), um takeover (`weak-password-reset`) | a **ausência** de rastro no lado vulnerable vs o rastro no lado fixed — o **contraste de dois `docker compose logs`** sob o mesmo ataque |
| Prevention (rate-limiting / lockout) | **bloquear** o brute-force — o ataque para | **ver** o brute-force — registrar cada falha + WARN no limiar; o ataque **não** é bloqueado (os `401` continuam). Detecção, não prevenção |
| Logar o segredo (o anti-padrão A09 oposto) | um log que guarda a senha tentada / tokens / PII — um vazamento pelo log | o log guarda o **fato** (evento, conta, IP, hora), **nunca** o segredo |
| A credencial (vs `weak-password-reset`, 37) | o segredo de auth é **previsível** — uma falha em como ele é gerado (A07) | a autenticação está **correta**; a falha simplesmente não é **registrada** como security event (A09) |

## O impacto é cegueira

O teto aqui é **não saber**. No lado vulnerable o brute-force roda e não aparece em lugar nenhum que um sistema de monitoração pegaria: sem alerta, sem nada para a resposta a incidente abrir, sem rastro para um forense reconstruir **o que** houve, **quando**, ou **de onde**. A09 é, sem rodeios, "quanto tempo até você descobrir que foi invadido" — e relatórios reais medem esse dwell time em **meses**. Uma consequência segue direto: no mundo real uma dessas tentativas de brute-force eventualmente acerta, e sem registro, ninguém investiga. Que o chute eventualmente funcione é *outra* categoria — uma senha fraca, ou um lockout que falta — então o foco fica onde a falha está: na **visibilidade**.
