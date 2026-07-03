# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py` para a view `/ping`:

```diff
 @app.route("/ping")
 def ping():
     host = request.args.get("host", "")
-    # VULNERABLE: user input concatenated into a shell command string
-    cmd = f"ping -c 1 {host}"
     try:
-        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
+        # FIXED: argument list, no shell — host can never be parsed as shell syntax
+        result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=10)
         output = result.stdout + result.stderr
     except subprocess.TimeoutExpired:
         # timeout: operational hygiene (orthogonal to the vuln/fix), same in both versions
         output = "command timed out after 10s"
-    return render_template("result.html", host=host, command=cmd, output=output)
+    return render_template("result.html", host=host, output=output)
```

O `fixed/templates/result.html` também larga o echo "Executed command" (`<pre>{{ command }}</pre>`) — mudança incidental, do mesmo jeito que a versão fixed do `sqli-union-basic` larga o bloco de debug da query. Repare no que *não* muda: o `try/except subprocess.TimeoutExpired` e o `timeout=10` são idênticos nas duas versões (aparecem como contexto inalterado no diff), então a única mudança relevante pra segurança é o próprio sink — uma string de shell virou uma lista de argumentos.

## O que mudou

A string única entregue a um shell foi trocada por uma lista de argumentos: `subprocess.run(f"ping -c 1 {host}", shell=True)` virou `subprocess.run(["ping", "-c", "1", host])` (com o `shell=True` fora, voltando ao default `False`). `host` não é mais splicado numa string que um shell parseia — é um elemento do vetor de argumentos. A versão vulnerable também montava uma string `cmd` e a ecoava na página; as duas somem na versão fixed, que não tem uma linha de shell única pra mostrar.

## Por que isso resolve

Com uma lista de argumentos e sem shell, o Python chama `execvp("ping", ["ping", "-c", "1", host])` e o kernel executa o `ping` direto. **Nenhum `/bin/sh -c` é spawnado**, então nada nunca parseia `;`, `|`, `&&` ou `$(...)` como sintaxe. `host` chega no `ping` como um argumento opaco — o operando de destino. `127.0.0.1; whoami` vira um "hostname" literal que o `ping` passa pro `getaddrinfo`, que falha:

```
ping: 127.0.0.1; whoami: Name or service not known
```

Os metacaracteres são texto inerte. É o análogo exato da query parametrizada do `sqli-union-basic`: lá, o placeholder `?` faz a SQL engine parsear o statement *primeiro* e ligar o valor como dado inerte; aqui, a lista de argumentos faz o OS rodar exatamente um programa com o input como argumento inerte. Os dois fixes são a mesma ideia — separar código de dado, manter o interpretador fora da jogada. A versão vulnerable tem o modelo oposto: o input já é parte de um programa quando o shell o vê, então o shell *tem* que parsear isso como código.

## Blocklistar metacaracteres é jogo perdido

Um "fix" tentador é remover o caractere perigoso — rejeitar ou apagar o `;`. O Passo 2 do walkthrough já mostra por que isso falha: `|`, `&&` e `$(...)` chegam num segundo comando igualzinho, e ainda há mais (`||`, backticks, newlines, redirects...). A causa raiz não é um caractere; é que um shell está parseando input do atacante como código. Enquanto o input for splicado num comando de shell, escapar e blocklistar são jogo perdido — a mesma lição que o `sqli-union-basic` ensina sobre escapar aspas. O único fix robusto é remover o shell.

## Validação de input — defense-in-depth, não o fix

Uma allowlist — aceitar só caracteres de hostname/IP, ex.: `^[a-zA-Z0-9.-]+$`, e rejeitar o resto — também barraria esses payloads. Vale ter, mas como *segunda camada*, não como o fix, pelos mesmos motivos que o `xss-stored` coloca o `HttpOnly` em defense-in-depth:

- **Não é o fix de raiz.** Uma allowlist é uma blocklist virada do avesso, e allowlists incompletas viram bypass; a lição transferível é "separe código de dado", não "enumere os caracteres bons". O fix da lista de argumentos fecha o buraco não importa o que o input contenha.
- **Uma variável por vez.** A app fixed muda exatamente uma coisa — o sink — então fica inequívoco qual mudança fecha a injection. Empilhar uma allowlist por cima borraria isso, do mesmo jeito que adicionar `HttpOnly` na app XSS fixed borraria.

A allowlist ganha, porém, um papel concreto e não-redundante: mesmo com o shell fora, um `host` começando com `-` (digamos `-f`, uma flag de flood do `ping`) seria lido pelo `ping` como uma *opção* em vez de um destino — **argument injection**, um problema mais estreito que command injection mas ainda indesejado. Uma allowlist que proíbe o `-` inicial fecha essa fresta também. Então: a lista de argumentos é o fix; a allowlist é uma camada extra que vale a pena e que, de quebra, fecha a porta do argument injection.

## O bug mora no app.py (o inverso do par XSS)

Aqui `vulnerable/app.py` e `fixed/app.py` diferem — o sink perigoso está no código Python, e os templates (fora o echo incidental do comando) são iguais. É a imagem espelhada do `xss-stored` e do `xss-reflected`, onde o `app.py` era byte a byte idêntico entre as versões e o bug morava inteiramente no template. Mesma lente de auditoria, localização oposta: pra command injection você lê o código atrás de chamadas de `subprocess` / `os.system` com `shell=True`; pra XSS você lê os templates atrás de `|safe`. Saber qual arquivo abrir é metade da auditoria.
