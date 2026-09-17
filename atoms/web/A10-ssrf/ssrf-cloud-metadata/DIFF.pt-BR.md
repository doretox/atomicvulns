# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é um gate de destino em volta do fetch no `POST /fetch` (comentários abreviados):

```diff
 import os
+from urllib.parse import urlparse
 import requests
-from flask import Flask, request, render_template
+from flask import Flask, request, render_template, abort

 app = Flask(__name__)

+# Deny-by-default allowlist of vetted destinations, matched on the PARSED host.
+ALLOWED_HOSTS = {"api.github.com"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/fetch", methods=["POST"])
 def fetch():
     url = request.form.get("url", "")
-    # VULNERABLE: fetch an attacker-controlled URL and return the response body verbatim...
+    # FIXED: validate the destination against a deny-by-default allowlist BEFORE fetching...
+    parsed = urlparse(url)
+    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
+        abort(403)
     try:
         r = requests.get(url, timeout=5)
         body, status = r.text, r.status_code
     except requests.RequestException as exc:
         body, status = f"Request error: {exc}", None
     return render_template("result.html", url=url, body=body, status=status)
```

Os templates (`index.html`, `result.html`), o `Dockerfile` e o `requirements.txt` são byte-a-byte idênticos entre as duas versões. O bug vive inteiramente na ausência de validação de destino em volta do `requests.get`.

## O que mudou

Três edições, todas no `app.py`:

- Novos imports: `urllib.parse.urlparse`, mais `abort` do `flask`.
- Uma constante `ALLOWED_HOSTS` com o único host que a feature se dispõe a alcançar.
- Um gate antes do `requests.get`: parsear a URL uma vez, e rejeitar qualquer coisa cujo scheme não seja `http`/`https` **ou** cujo host parseado não esteja na allowlist. Requests rejeitados devolvem `403 Forbidden`.

Este é um fix *lógica-diferente* — código **adicionado**, não um valor alterado — a mesma forma do `ssrf-basic` e do `ssrf-blind-oob` antes dele. O que **não** está no diff: o `try/except/return` que busca e ecoa o corpo fica intocado. O fix age sobre a **requisição** (se o fetch acontece), não sobre a resposta.

## Por que isso corrige o bug

A classe é: o servidor emite uma requisição para um destino que o atacante controla, e aqui ele devolve o corpo — então apontá-lo para `169.254.169.254` devolve as credenciais IAM da instância. A remediação valida esse destino *antes* da requisição, contra uma allowlist deny-by-default. `http://169.254.169.254/…` não está na lista, então nunca chega no `requests.get`, e o metadata endpoint fica inalcançável por esta feature. A checagem roda sobre `urlparse(url).hostname` — o host que o cliente HTTP de fato conectaria — não sobre um substring do raw string.

## Allowlist, não um blocklist da faixa link-local

A alternativa tentadora é bloquear o endereço "ruim": `169.254.169.254`, ou toda a faixa link-local `169.254.0.0/16`. Não faça. Um blocklist perde para os bypasses que blocklists de SSRF sempre perdem:

- encodings alternativos de IP — decimal (`2852039166`), hex (`0xa9fea9fe`), octal, IPv6-mapped (`[::ffff:169.254.169.254]`) — todos alcançam o mesmo host mas escapam de um filtro de string em dotted-decimal;
- redirects: um host de aparência vetada responde `302 → http://169.254.169.254/…` e o cliente segue;
- DNS rebinding: um nome controlado pelo atacante resolve para o endereço link-local na hora do fetch;
- confusão de userinfo/authority: o host real escondido depois de um `@`.

Uma allowlist rejeita tudo que não é explicitamente vetado — o endereço link-local incluso — sem ter que enumerar as evasões. É a mesma forma que todo o arco de SSRF usa: `ssrf-basic` e `ssrf-blind-oob` defendem ambos com uma lista positiva, e o DIFF do `ssrf-blind-oob` detalha por que um blocklist vaza. Allowlists vencem porque são finitas e decidem sobre intenção; blocklists são infinitos e decidem sobre chutes.

## IMDSv2 — mencionado, não aplicado

Há uma segunda defesa, do lado da cloud, que este átomo deliberadamente **não** implementa: o **IMDSv2**. O metadata service real foi endurecido de forma que ler credenciais exige um session token obtido com um request `PUT` primeiro — um SSRF de `GET` simples não consegue obter um — e ele carimba as respostas com `hop-limit=1`, então uma requisição *proxiada pela app* (um hop a mais que a própria instância) é descartada. Qualquer um dos mecanismos cega este SSRF exato.

Então por que não está no diff? Porque o IMDSv2 é uma propriedade do **metadata service** — configuração de cloud/infra —, não do `vulnerable/app.py`. A forma deste projeto é um diff *no código da aplicação*, e o fix no nível de aplicação para "a app busca qualquer URL" é validar o destino, que é o que o `fixed/app.py` faz. O IMDSv2 é real, é onde este ataque fica muito mais difícil no campo, e numa instância real você deve forçá-lo (e ajustar o `hop-limit` do metadata da instância apropriadamente) — mas é defesa do lado do **alvo**: nomeada aqui, não aplicada no diff. É o mesmo movimento que o `jwt-weak-secret` faz com a nota "secret management … mencionável, não aplicada" dele — nomear o controle do mundo real que vive fora do código da app, e manter o diff do átomo na única mudança que ele ensina.

## Recusa visível aqui vs a resposta idêntica no `ssrf-blind-oob`

O `ssrf-blind-oob` devolve uma resposta **byte-idêntica** tenha ele buscado ou não — de propósito, porque é *blind*: se a app fixed respondesse diferente, você conseguiria confirmar o bloqueio pela resposta, contradizendo toda a lição de "confirmar out-of-band". Este átomo faz o oposto: o `fixed` responde com um `403` visível. Isso é correto aqui porque este átomo é **in-band** — a resposta já carrega informação (ela ecoa o corpo buscado), então um `403` distinto não muda nada na lição e lê naturalmente, exatamente como o `abort(403)` do `ssrf-basic`. Mesma família de defesa (validar o destino); a *forma da recusa* segue o canal: blind → idêntica, in-band → visível.

## O eco é escapado de propósito

O `result.html` renderiza o corpo buscado dentro de um `<pre>{{ body }}</pre>` com o autoescape do Jinja ligado (sem `|safe`, sem `Markup`, sem `render_template_string`). Aponte a app para um corpo cheio de `<`/`>` e ele volta como `&lt;`/`&gt;` no source da página. Isso é deliberado: mostrar conteúdo buscado não pode virar uma segunda vulnerabilidade (XSS refletido / HTML injection). A única vulnerabilidade aqui é o SSRF — o servidor buscar um destino que não deveria. Como o corpo é exibido não faz parte do bug, e o fix não toca nisso.

## A allowlist está correta, não é um blocklist bypassável

Um filtro *bypassável* transformaria silenciosamente este átomo numa lição de "SSRF filter bypass" (um tópico diferente e mais avançado), então o fix decide sobre o host parseado e resiste às evasões usuais. Verificado contra a app fixed:

| Payload (corpo `url=`) | Host parseado | Resultado |
|---|---|---|
| `https://api.github.com/zen` | `api.github.com` | allowed (o host vetado) |
| `http://169.254.169.254/latest/meta-data/…` | `169.254.169.254` | 403 (não vetado — a defesa real) |
| `http://2852039166/…` (decimal) | `2852039166` | 403 |
| `http://0xa9fea9fe/…` (hex) | `0xa9fea9fe` | 403 |
| `http://[::ffff:169.254.169.254]/…` | `::ffff:169.254.169.254` | 403 |
| `http://api.github.com@169.254.169.254/…` (userinfo) | `169.254.169.254` | 403 |

A última linha é a que vale reter: a string `api.github.com` está presente, então `if "api.github.com" in url` passaria e deixaria a requisição alcançar o metadata endpoint. `urlparse(...).hostname` devolve o host real — a parte depois do `@` — que não está na lista.

Um limite honesto, no mesmo espírito "mencionado, não aplicado" do IMDSv2: `requests.get` segue redirects por default, então um fix gate-only ainda seguiria um `302` para `169.254.169.254` *se um host vetado o emitisse*. Neste lab isso não é alcançável — o host vetado é benigno e não redireciona para o metadata endpoint, e qualquer redirector não-vetado é rejeitado no gate porque o host dele não está na lista. Código de produção que precise ser à prova de balas também fixaria `allow_redirects=False` (ou revalidaria cada hop); este átomo mantém o diff no gate de destino e nota o hardening de redirect aqui em vez de empilhá-lo no código.

## Uma nota sobre a topologia (por que uma rede só)

O `ssrf-basic` e o `ssrf-blind-oob` põem o serviço extra em duas redes Docker e o alcançam por nome DNS, o que mantém `vulnerable` e `fixed` em redes separadas. Este átomo fixa o mock no IP `169.254.169.254` — o ponto inteiro é que o payload seja idêntico ao de um alvo real — e um único endereço só pode viver numa subnet, então aqui os três containers compartilham uma rede. É uma divergência deliberada, e ela é inócua para a lição: a propriedade que importa fica preservada — o mock é alcançável de **ambos** `vulnerable` e `fixed` no nível de rede, então o `403` da app fixed é atribuível ao **código** dela (a allowlist recusando), não a uma rede inalcançável. A única coisa perdida é a separação L3 entre `vulnerable` e `fixed`, que não carrega lição: nenhuma das apps jamais inicia tráfego para a outra, e você só as alcança pelas portas do host.
