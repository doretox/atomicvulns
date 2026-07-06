# Walkthrough — path-traversal-basic

## 1. Contexto

A app é um "file viewer". Você digita um nome de arquivo em `/`, o form dispara um request `GET /view?file=<nome>`, e o servidor lê esse arquivo do diretório `files/` dele e te mostra o conteúdo — o tipo de feature de "abrir um documento" que existe em help centers e painéis de admin por todo lado.

Como o `command-injection-basic`, este átomo é trabalhado inteiramente no Burp. O arquivo é lido no servidor e o conteúdo volta direto na resposta HTTP, então não há nada pra executar num browser — você vê o `/etc/passwd` ali no painel de response do Repeater. A trilha do browser na seção 5 é conveniência, não requisito.

E tenha aquele átomo em mente, porque você está prestes a chegar no **mesmo destino** — `/etc/passwd` — pela rota **oposta**. No `command-injection-basic` você fez a app *rodar um comando* seu. Aqui você vai fazer a app *abrir um arquivo* seu. Um é execução; o outro é navegação. Segure esse contraste; a seção 4 fecha nele.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/view` monta o caminho assim:

```python
filename = request.args.get("file", "")
# VULNERABLE: user input joined onto the base dir and opened directly —
# nothing confines the resolved path to BASE_DIR
path = os.path.join(BASE_DIR, filename)
with open(path) as f:
    content = f.read()
```

O `filename` vem direto da query string e é juntado ao `BASE_DIR` (`/app/files`), depois entregue ao `open()`. Não há um "sink" perigoso no sentido de injection — sem shell, sem SQL engine, sem template. A app só abre o arquivo que o caminho aponta. O bug é a coisa que **não está lá**: nenhum check de que o caminho resolvido fica *dentro* do `BASE_DIR`. O `os.path.join` não colapsa `..`, e o `open()` segue o `../` árvore acima de boa vontade, então quem chama decide de onde a app lê.

É uma lente de auditoria diferente da dos átomos de injection. Lá você grepa por uma chamada perigosa (`shell=True`, `f"...SELECT`, `|safe`). Aqui você acha endpoints de manipulação de arquivo — `open(`, `os.path.join(`, `send_file(` — e faz uma pergunta: **o que confina esse caminho ao diretório permitido?** Quando a resposta é "nada", você tem um achado.

```bash
grep -rn 'open(\|os.path.join(\|send_file(' .
```

Duas coisas que a app faz *certo*, pra você não confundir com o bug:

- **O conteúdo é HTML-escaped.** O `result.html` renderiza `<pre>{{ content }}</pre>` pelo autoescape default do Jinja (sem `|safe`). Se não fizesse, ler um arquivo que contém `<script>...` transformaria o conteúdo do arquivo em HTML vivo — um reflected XSS empilhado por cima do path traversal. Escapar mantém este átomo com exatamente um bug. **Não** é o fix de path traversal.
- **O 404 num caminho ruim é higiene, não defesa.** `try/except OSError: abort(404)` faz uma contagem errada de `../` ou um typo retornar um 404 limpo em vez de um stack trace 500. É ortogonal à vulnerabilidade e ao fix, e idêntico nas duas versões — um traversal *bem-sucedido* retorna 200 com o arquivo, longe desse caminho.

A view `/view` também ecoa o caminho montado num `<pre>` de debug ("Resolved path"), o que facilita seguir este lab — você vê seu nome de arquivo virar um caminho de filesystem. Num app real você inferiria o formato do caminho pelo comportamento.

## 3. Como o app serve arquivos

A app deveria servir só os arquivos do próprio diretório `files/` — `notes.txt` e `readme.txt`, listados na home page. Esse é o conjunto "permitido": a feature legítima nunca precisa de mais nada. O exploit faz a app servir arquivos de *fora* desse diretório. Use o bloco "Resolved path" em cada página de resultado pra ver exatamente qual caminho a app abriu — é a janela mais clara pro traversal.

## 4. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8010/>, submeta `notes.txt` pelo form uma vez pra capturar o tráfego, depois clique com o botão direito no request `GET /view?file=notes.txt` em **Proxy → HTTP history** e escolha **Send to Repeater**.

### Baseline — a ferramenta fazendo seu trabalho

Envie o request capturado como está e leia a resposta. O bloco "Resolved path" mostra `/app/files/notes.txt`, e o conteúdo é o arquivo de seed:

```
Resolved path:
/app/files/notes.txt

Contents:
Project notes
-------------
- Ship the file viewer demo.
- Ask design for the new icon.
- Nothing secret here — this is just seed content.
```

É a feature funcionando como deveria — serviu um arquivo que ela oferece. Agora conduza ela pra fora da pasta.

### Uma nota sobre URL encoding

Os traps dos átomos de injection não existem aqui. Não há espaços nem `&` nesses payloads, e `.` e `/` passam crus no *valor* da query string — então `?file=../../../../etc/passwd` vai no fio exatamente como escrito, sem encoding nenhum. (No `command-injection-basic` um espaço tinha que ser `%20` e o `&&` tinha que ser `%26%26`; nada disso se aplica.)

Um fato de encoding vale saber, e importa pro fix. `..%2f` é a forma percent-encoded de `../`, e o Werkzeug decoda `%2f` de volta pra `/` num valor de query — então `file=..%2f..%2fetc%2fpasswd` chega como `../../etc/passwd` e se comporta idêntico. É exatamente o truque que passa por um filtro ingênuo que só bloqueia a string literal `../` (ver `DIFF.pt-BR.md`). O form do browser encoda `/` pra `%2f` no envio e o servidor decoda de volta — mesmo resultado. Se você quiser que o Burp encode um valor pra você, selecione ele e aperte **Ctrl+U**.

Cada passo abaixo mostra um **Payload** (decoded, pra leitura) e uma **Request line** (pronta pra colar no Repeater).

### Passo 1 — Confirmar o traversal

Suba pra fora da pasta com `../` e leia um arquivo que a app nunca quis servir.

```
Payload:       ../../../../etc/passwd
Request line:  GET /view?file=../../../../etc/passwd HTTP/1.1
               Host: 127.0.0.1:8010
```

Response — o bloco "Resolved path" mostra seu nome de arquivo virando um caminho que sobe a árvore, e o conteúdo é o `/etc/passwd` inteiro do container:

```
Resolved path:
/app/files/../../../../etc/passwd

Contents:
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

Seu input não era um nome de arquivo confinado; era uma **rota pelo filesystem**. `os.path.join("/app/files", "../../../../etc/passwd")` vira `/app/files/../../../../etc/passwd`, e o `open()` deixa o OS resolver os `..` até a raiz.

**Quantos `../`?** A base é `/app/files`, dois níveis abaixo de `/`, então o *mínimo* pra chegar em `/etc/passwd` é `../../etc/passwd` (dois). Este passo manda quatro. Os de sobra são inofensivos — `..` em `/` só fica em `/` (o pai da raiz é a raiz) — e num alvo real você raramente sabe a profundidade exata, então overshoot é o hábito. Tanto `../../etc/passwd` quanto `../../../../etc/passwd` leem o mesmo arquivo.

### Passo 2 — Não é o `../`: o caminho simplesmente não é confinado

A conclusão errada natural é "a app devia ter bloqueado o `../`". Não devia importar se você usa `../` ou não — o caminho simplesmente não é confinado à pasta. Prove com um payload que não contém **nenhum `../`**: um caminho absoluto.

```
Payload:       /etc/passwd
Request line:  GET /view?file=/etc/passwd HTTP/1.1
               Host: 127.0.0.1:8010
```

Response — o **mesmo** conteúdo de `/etc/passwd` do Passo 1, mas olha o caminho resolvido:

```
Resolved path:
/etc/passwd
```

O diretório base *sumiu*. `os.path.join("/app/files", "/etc/passwd")` retorna `/etc/passwd` — quando um componente é absoluto, o `os.path.join` descarta tudo antes dele. Você chegou no mesmíssimo arquivo sem um único `../`.

Sente nessa. Um dev que "conserta" isso removendo `../` do input não fez nada: `/etc/passwd` passa direto. O bug nunca foi o token `../` — é que a app abre qualquer caminho que o input resolve, sem check de que ele caiu dentro da pasta. É por isso que blocklist é jogo perdido, e por isso o fix de verdade (seção 6) *resolve o caminho e confirma o destino* em vez de limpar caracteres. No `command-injection-basic` a lição paralela era "escapar metacaracteres é jogo perdido — tire o shell"; aqui é "filtrar `../` é jogo perdido — confine o caminho".

### Passo 3 — Ler além do /etc/passwd: o próprio source da app

O `/etc/passwd` prova que você escapou da pasta. Pra provar que o alcance é *arbitrário*, leia algo que importa — o próprio código-fonte da aplicação:

```
Payload:       ../app.py
Request line:  GET /view?file=../app.py HTTP/1.1
               Host: 127.0.0.1:8010
```

Response — o source do servidor rodando, direto do disco:

```
Resolved path:
/app/files/../app.py

Contents:
import os
from flask import Flask, request, render_template, abort

app = Flask(__name__)
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
...
    path = os.path.join(BASE_DIR, filename)
    with open(path) as f:
        content = f.read()
...
```

Repare que isso levou só **um** `../` — o `app.py` mora em `/app`, um nível acima de `/app/files`, enquanto o `/etc/passwd` precisou de dois (e o Passo 1 fez overshoot pra quatro). A quantidade de `../` depende de onde o alvo está em relação à base: você está *andando pela árvore* e contando passos até o destino. Esse é o modelo mental inteiro — navegação, não encantamento.

(Um à parte que amarra com a seção 2: no response cru do Burp os caracteres `"` do source aparecem como `&#34;` — isso é a app fazendo HTML-escape do conteúdo do arquivo, exatamente a higiene que a gente sinalizou. É inofensivo aqui, e o browser renderiza eles de volta pra `"`.)

**O que isso é de verdade.** Aqui o arquivo é lido dentro de um container descartável e isolado, então dumpar `/etc/passwd` ou o source da app como `root` é inofensivo — esse isolamento é a rede de segurança deste lab. Num alvo real isso é **arbitrary file read**: código-fonte, arquivos `.env`, config, chaves SSH, credenciais de cloud — qualquer coisa que o processo do servidor consiga ler. É só leitura (diferente do gêmeo), mas uma credencial vazada ou uma árvore de source vazada rotineiramente *encadeia* em compromisso mais profundo. Mantenha seus payloads demonstrativos — ler um arquivo, imprimir um passwd; não há motivo pra apelar pra nada destrutivo, e nem pra dumpar arquivos sensíveis como `/etc/shadow` gratuitamente só porque o `root` consegue.

### Por que isso é path traversal, não command injection

Você acabou de ler `/etc/passwd` — o mesmo arquivo que o `command-injection-basic` te entregou. Mas nada aqui executou. A distinção é o ponto todo deste átomo:

> No command injection, você fez a app **rodar um comando** seu. No path traversal, você fez a app **abrir um arquivo** seu — usando exatamente a função que ela já tinha (abrir arquivos), só que apontada pra fora do quintal. Um é **execução**; o outro é **navegação**. Os dois te deram `/etc/passwd`, mas por caminhos opostos: um executando `cat`, o outro **sendo** o próprio `cat`. No command injection você tem que **invocar** o `cat`; aqui o file viewer vulnerável já **é** uma máquina de ler-e-mostrar arquivo — você só redireciona ela pra fora da pasta. A app **é** o `cat`.

|  | command injection | path traversal (este átomo) |
|---|---|---|
| A app... | **executa** um programa | **abre e lê** um arquivo |
| Seu input vira | um **comando** | um **caminho / nome de arquivo** |
| Você ganha o poder de | rodar **qualquer coisa** (RCE) | ler **qualquer arquivo** (só leitura) |
| `/etc/passwd` sai porque | você mandou **executar** `cat /etc/passwd` | você **navegou** até ele com `../` |
| A feature original era | rodar um `ping` | servir um arquivo |
| Categoria OWASP | A03 — Injection | A01 — Broken Access Control |

Aquela última linha é por que este átomo vive em **Broken Access Control**, não Injection: nada virou código, um nome de arquivo simplesmente conduziu a app a um recurso fora do escopo. É o mesmo formato do `idor-numeric-id` — lá você trocou um ID numérico (`/notes/1` → `/notes/2`) pra ler a nota de outro usuário; aqui você navega o filesystem (`notes.txt` → `../../etc/passwd`) pra ler um arquivo que não é seu pra ver. Nos dois, a app te entregou algo que não era pra você, e nos dois o fix é o check que faltava — um ownership check lá, um confinement check aqui.

## 5. Exploração via browser (trilha secundária, opcional)

Os mesmos payloads funcionam direto da barra de endereços — sem Burp:

1. <http://127.0.0.1:8010/view?file=../../../../etc/passwd>
2. `http://127.0.0.1:8010/view?file=/etc/passwd`
3. <http://127.0.0.1:8010/view?file=../app.py>

O browser **não** normaliza `../` na query string (ele só colapsa dot-segments no *path* da URL), então esses passam intactos; o form encoda `/` pra `%2f` no envio e o servidor decoda de volta. Use isto pra a primeira leitura; passe pro Burp quando quiser controle byte a byte do payload, que é como você trabalharia um alvo real — e é o único lugar onde o truque de encoding `..%2f` da seção 4 é visível.

## 6. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança. Em resumo, a view `/view` corrigida resolve o caminho requisitado pra forma canônica e confirma que ele fica dentro do diretório base antes de abrir:

```python
base = os.path.realpath(BASE_DIR)
path = os.path.realpath(os.path.join(base, filename))
if not path.startswith(base + os.sep):
    abort(404)
```

O `os.path.realpath` colapsa todo `../` (e resolve um componente absoluto) pra um caminho real e canônico; o prefix check então confirma que esse caminho ainda fica sob `/app/files/`. Replay cada payload da seção 4 contra <http://127.0.0.1:8110/view>:

- `file=notes.txt` → **200**, o arquivo (está dentro da base).
- `file=../../../../etc/passwd` → **404** (resolve pra `/etc/passwd`, fora da base).
- `file=/etc/passwd` → **404** (resolve pra `/etc/passwd`, fora da base).
- `file=../app.py` → **404** (resolve pra `/app/app.py`, fora da base).

Um check, e *toda* rota — relativa, absoluta, encodada — volta 404, enquanto o arquivo legítimo continua servindo. Essa é a prova de que os dois vetores dos Passos 1 e 2 eram o mesmo bug: o confinamento estava ausente, e adicioná-lo fecha todos de uma vez. Repare que retorna **404**, não 403 — diferente do `idor-numeric-id`, que retorna 403 pra um objeto real que você não pode acessar. Aqui um caminho rejeitado e um arquivo genuinamente inexistente retornam ambos 404, então o atacante nem consegue dizer quais caminhos escapam do sandbox. Tentar *blocklistar* `../` seria jogo perdido (`..%2f`, `....//`, e o `/etc/passwd` absoluto simples derrotam tudo); o `DIFF.pt-BR.md` também cobre o `os.path.basename` como alternativa mais simples quando a app não precisa de subdiretórios, e o `send_from_directory` do Flask, que faz esse containment check por você.
