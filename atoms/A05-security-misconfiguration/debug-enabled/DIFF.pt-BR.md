# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em exatamente um lugar: o bloco `__main__` que sobe o servidor. O lado vulnerável roda com `debug=True` e desliga o PIN do debugger; o lado corrigido roda com `debug=False`. Nada mais muda — os imports, o `app.json.compact = True`, o banner `GET /`, a rota `GET /items/<idx>` e o `Dockerfile` são byte-idênticos, e os dois `requirements.txt` também. A vulnerabilidade inteira, e o fix inteiro, é uma flag.

## O fix — desligar o debug mode

```diff
 if __name__ == "__main__":
-    # VULNERABLE: debug=True exposes Werkzeug's interactive debugger (console -> RCE);
-    # WERKZEUG_DEBUG_PIN=off unlocks that console. The dev mode is the flaw, not the route.
-    os.environ["WERKZEUG_DEBUG_PIN"] = "off"
-    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)
+    # FIXED: debug=False -- no interactive debugger, no console. Same exception -> generic 500.
+    # In production, serve behind a real WSGI server (Gunicorn/uWSGI), not this dev server.
+    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=False)
```

(Comentários abreviados.) `debug=True` liga o debugger interativo do Werkzeug — a página de erro *e* o console que roda Python arbitrário no processo do servidor. `WERKZEUG_DEBUG_PIN=off` remove a única tranca na frente desse console. `debug=False` remove os dois: uma exceção não-tratada agora vira um `500` genérico, sem traceback e sem console, e não há linha de PIN porque não há debugger pra destrancar. A rota que quebra fica intacta.

Uma linha idêntica nos dois lados merece nota porque é fácil de ler errado: `app.json.compact = True`. O debug mode também faz o Flask *pretty-print* do JSON, então sem essa linha a resposta benigna do `GET /items/0` ficaria diferente nos dois lados (indentada vs. compacta). Fixar a saída compacta nos dois mantém a resposta benigna byte-idêntica, pra que a **única** diferença observável entre as apps seja o que uma exceção não-tratada vira. É ortogonal à vuln e idêntica nos dois arquivos.

## A causa é o dev mode exposto, não "a rota esqueceu de tratar o erro"

É tentador ler a quebra como o bug: `int("abc")` levanta, então a rota devia ter capturado. Mas a exceção é só o **gatilho**, não a vulnerabilidade. Prova de isolamento: mande o mesmo `GET /items/abc` pra app corrigida — ela levanta o `ValueError` *idêntico* e devolve um `500` seco. Mesma exceção, sem página de debug, sem console. O que difere não é *se* a rota quebra; é o que o servidor *faz* com uma quebra, e isso é dado inteiramente pela flag debug.

Isso importa porque o "fix" óbvio — envolver a rota num `try/except` — é uma armadilha (abaixo).

## "Só capturar a exceção" não é o fix

Um `errorhandler` ou um `try/except` em volta do `int(idx)` impediria *este* traceback de renderizar. Mas trata o sintoma, não a causa: o debugger interativo continua ligado. A **próxima** exceção não-tratada — de outra rota, outro input, um bug que você ainda nem escreveu — renderiza a página de debug e reabre o console. Você ficaria jogando whack-a-mole com pontos de erro enquanto deixa o console de execução armado. O debugger tem que estar *off*, não meramente não-alcançado por um caminho de código.

## "Só pôr o PIN" não é o fix

O outro reflexo: o console é protegido por um PIN, então liga o PIN. Seja preciso sobre o que isso compra. O PIN até eleva um pouco a barra — mas é **calculado de dados da máquina**: o username, um machine id (`/etc/machine-id` ou o boot id), e o MAC address, hasheados juntos. A própria página de debug vaza vários desses inputs (o seu username aparece nos caminhos de arquivo de todo traceback), e o resto é estável e às vezes obtenível, então um atacante determinado consegue *derivar* o PIN. É um obstáculo, não uma parede. E, mais fundamental: um console de **desenvolvimento** não tem por que estar alcançável num ambiente deployado, ponto. Ligar o PIN tranca — mal — uma porta que não devia existir aqui. Deixar `debug=True` é o erro; `debug=False` remove a porta.

(É o mesmo formato das notas de honestidade-em-camadas do resto do repo — o salt no `crypto-weak-hash`, o CBC no `crypto-ecb-mode`: o controle nomeado tem *algum* valor, mas não é o fix de causa.)

## Servir em produção — um servidor WSGI real

Mais uma coisa, e esta **não** é armadilha — é contexto de deploy legítimo. O `app.run()` inicia o **servidor de desenvolvimento** embutido do Werkzeug, que imprime, a cada boot, `WARNING: This is a development server. Do not use it in a production deployment.` O fix mínimo deste átomo é `debug=False`. A prática de deploy completa é não usar o servidor de desenvolvimento de forma alguma: rodar a app atrás de um servidor **WSGI** real (Gunicorn, uWSGI), que não tem debugger nem servidor de desenvolvimento pra expor. `debug=False` fecha a vulnerabilidade; servir atrás de um servidor WSGI é como você evita estar a uma flag de distância dela, pra começar.

## Os dois lados compartilham as dependências

Diferente do `crypto-weak-hash`, cujo fix trouxe uma lib nova (`bcrypt`), aqui `vulnerable/requirements.txt` e `fixed/requirements.txt` são **idênticos**:

```
Flask==3.0.0
Werkzeug==3.1.8
```

O `Werkzeug` é a própria dependência do Flask — você não instala à parte —, mas aqui ele está pinado **explicitamente** de propósito. O debugger interativo e o protocolo do console dele (o request `__debugger__`/`cmd`/`frm`/`s`, onde o `SECRET` fica na página) são do Werkzeug, e são específicos da versão; pinar a versão exata mantém o exploit do `WALKTHROUGH.md` reproduzível. O fix é uma mudança de uma flag no código, não uma mudança de dependência — um lembrete de que uma misconfiguration devastadora pode ser, e frequentemente é, uma única linha de config.

## O impacto é information disclosure + RCE — como 09/20, por uma causa diferente

Dois findings: a página de debug vaza código-fonte, variáveis e caminhos (information disclosure), e o console dela roda Python arbitrário (RCE). RCE é o teto — o mesmo teto do [`command-injection-basic`](../../A03-injection/command-injection-basic/) e do [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/), o que vale pausar, porque os três se parecem no impacto e em nada mais. "Um átomo, uma vulnerabilidade" é sobre a **causa**, não o impacto:

| | `command-injection-basic` (09) | `deserialization-pickle` (20) | `debug-enabled` (33) |
|---|---|---|---|
| Categoria | **A03 — Injection** | **A08 — Data Integrity Failures** | **A05 — Security Misconfiguration** |
| Superfície | input do usuário num comando de shell | um cookie `pickle` | uma exceção não-tratada + o debugger exposto |
| Quem executa | o **shell** (`/bin/sh -c`) | o **deserializer** (`pickle.loads`) | o **console de dev** do framework (Werkzeug) |
| Input do atacante vira código? | sim — costurado no comando | ~sim — os bytes carregam comportamento | **não** — o console já estava aberto |
| Causa-raiz | app monta um comando de shell a partir do input | `pickle.loads` em bytes não-confiáveis | dev mode (debugger) deixado alcançável |
| O fix | tirar o shell (lista de args) | trocar o formato (JSON) | `debug=False` (+ WSGI real em prod) |

O ponto afiado é a quarta linha: no 09 o dado do atacante é costurado num comando, no 20 são bytes que *carregam* comportamento — nos dois, algo do atacante vira código. No 33 nada do atacante vira código. O console de execução já estava lá, exposto por uma flag de configuração; a exceção é só a campainha que abre a página. Mesmo loot (RCE), três portas completamente diferentes — e aqui a porta é um ajuste de deploy, não uma linha de lógica da aplicação.
