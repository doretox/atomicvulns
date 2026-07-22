# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é um gate de destino em volta do fetch no `POST /ping`:

```diff
 import os
+from urllib.parse import urlparse
 import requests
 from flask import Flask, request, render_template

 app = Flask(__name__)

+# Deny-by-default allowlist of vetted webhook destinations, matched on the PARSED host (not a
+# substring of the raw URL). In this air-gapped lab the host is not actually reachable (no real
+# egress), so legitimate use is conceptual; what the lab demonstrates is that a non-vetted
+# destination (the oob-listener, or any internal/external host) is never fetched.
+ALLOWED_HOSTS = {"hooks.example.com"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/ping", methods=["POST"])
 def ping():
     url = request.form.get("url", "")
-    # VULNERABLE: fire a server-side request to an attacker-controlled URL and reveal nothing
-    # about the result. The outbound request happens (this is full SSRF); the response below
-    # is generic: no fetched body, no fetched status, no error surfaced. The SSRF is real, it
-    # is merely BLIND, so it must be detected out-of-band (see the oob-listener service).
-    try:
-        requests.get(url, timeout=5)  # server-side request to the attacker-chosen destination
-    except Exception:
-        pass  # swallow everything: surfacing the error would leak an in-band oracle
+    # FIXED: gate the outbound request on the allowlist BEFORE fetching. A destination that is
+    # not explicitly permitted is never requested, so the server cannot be coerced into reaching
+    # arbitrary destinations (internal or external). Same SSRF defense family as ssrf-basic (04);
+    # the host is the load-bearing check. The response below is left byte-identical to the
+    # vulnerable version on purpose: the fix gates the REQUEST, never the response.
+    parsed = urlparse(url)
+    if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:
+        try:
+            requests.get(url, timeout=5)
+        except Exception:
+            pass
     return "Test ping sent."  # generic: says nothing about whether or what was fetched
```

Todo o resto — `GET /`, os imports compartilhados, o rodapé, o `requirements.txt`, o `Dockerfile` e o template — é byte a byte idêntico entre as duas versões. Repare especialmente na linha que **não** mudou: `return "Test ping sent."`. A resposta é a mesma nas duas apps.

## O que mudou

Três edições, todas no `app.py`:

- Um import novo: `urllib.parse.urlparse`.
- Uma constante `ALLOWED_HOSTS` com os únicos hostnames que a feature aceita alcançar.
- Um gate em volta do fetch: parseia a URL uma vez, e só chama `requests.get` se o scheme for `https` **e** o host parseado estiver na allowlist. Qualquer outra coisa simplesmente nunca é buscada.

Este é um fix *lógica-diferente* — código adicionado, não um valor trocado — a mesma forma dos átomos de access control e dos JWT, e do `ssrf-basic` antes dele. O que **não** está no diff é a resposta: `return "Test ping sent."` está intocado, porque o fix opera na requisição, não no que é dito ao usuário.

## Por que isso corrige o bug

A classe é: **o servidor emite uma requisição pra um destino que o atacante controla.** A remediação valida esse destino *antes* de fazer a requisição, contra uma allowlist deny-by-default. Uma URL que não é explicitamente vetada nunca alcança o `requests.get`, então o servidor não pode ser coagido a alcançar hosts arbitrários — internos ou externos. A checagem roda sobre `urlparse(url).hostname`, o host que o cliente HTTP de fato conectaria, não sobre um substring da string crua.

O resto deste arquivo é sobre as armadilhas específicas do SSRF *blind*, onde o fix é fácil de errar de forma sutil.

## Deixar a resposta genérica não é defesa

É tentador achar que a cegueira em si te protege — a app já não diz nada, então o que há pra explorar? Mas a resposta é genérica na app **vulnerable** *e* na **fixed**, e uma delas é explorável. A linha `return "Test ping sent."` idêntica e intocada no diff torna isso concreto: a resposta nunca foi o controle. Esconder o output remove a sua confirmação *in-band*; não faz nada pra impedir o servidor de fazer a requisição. O fix tem que agir no **destino**, que é exatamente o que a resposta não toca.

## Allowlist, não um blocklist de faixas privadas

Uma alternativa de aparência natural é bloquear destinos "ruins" — faixas de IP privado, `localhost`, `169.254.169.254`, e por aí vai. Pro blind SSRF especificamente, isso não basta. Um blocklist de faixas privadas impede você de alcançar um alvo **interno** (bloqueia o impacto), mas **não** impede um callback out-of-band pra um host **externo** — um Collaborator na internet pública não está em faixa privada nenhuma. Então a detecção ainda funciona, e o servidor ainda pode ser levado a alcançar destinos externos escolhidos pelo atacante. Uma **allowlist** rejeita tudo que não é explicitamente vetado — interno *e* externo — então corta tanto a detecção quanto o impacto. É por isso que o fix é uma lista positiva.

## A ruga do lab: nosso sink é interno

Seja honesto sobre um detalhe que este lab não tem como evitar. No mundo real, o sink out-of-band (Collaborator, `interactsh`) é **externo**, então um filtro "bloqueia faixas privadas" **não** o bloquearia e a detecção ainda funcionaria — que é exatamente por que um blocklist é insuficiente. Neste lab air-gapped o sink (`oob-listener`) é **necessariamente interno**, então a mesma allowlist que barra alvos internos por acaso barra também o nosso sink. Não aprenda demais dessa coincidência: o fix não "mata a detecção de blind SSRF" em geral. Aqui ele barra o callback só porque nosso sink é interno; contra um Collaborator externo real, só uma allowlist — não um blocklist de faixas privadas — barraria o callback.

## `abort(403)` no `ssrf-basic` vs uma resposta idêntica aqui

O `ssrf-basic` rejeita uma URL não-permitida com `abort(403)` — uma recusa visível. Lá tudo bem: a app é in-band, a resposta dela já carrega informação, então um erro distinto não muda nada da lição. Este átomo deliberadamente **não** faz isso. Ele gateia o fetch e retorna o **mesmo** `Test ping sent.` quer o destino tenha sido permitido ou não. Se a app fixed respondesse diferente pra um destino bloqueado, você poderia confirmar o bloqueio pela resposta — contradizendo o ponto inteiro de que blind SSRF é confirmado out-of-band. Mesma família de defesa (validar o destino), forma adaptada à cegueira: a resposta fica constante, e a única coisa que muda é se o callback acontece.

Pela mesma razão, a app vulnerable engole a exceção do fetch (`except Exception: pass`) em vez de surfaceá-la como o `ssrf-basic` faz. Surfacear "connection refused" vs "timeout" vs "ok" seria um *oráculo in-band* que de-blinda parcialmente o átomo. (Um side-channel grosseiro de **timing** — um host alcançável responde rápido, um que não responde trava até o timeout de 5 segundos — é inerente a qualquer blind SSRF e não dá pra remover por completo; não é o canal que este átomo ensina. O callback out-of-band é.)

## A allowlist é correta, não um blocklist bypassável

A checagem decide sobre `urlparse(url).hostname`, então resiste às evasões usuais — e isso importa, porque um filtro *bypassável* transformaria silenciosamente este átomo numa lição de "SSRF filter bypass" (um tópico diferente e mais avançado). Verificado contra a app fixed:

| Payload | Host parseado | Resultado |
|---|---|---|
| `https://hooks.example.com/proof-ssrf-16` | `hooks.example.com` | permitido (o destino vetado) |
| `http://oob-listener/proof-ssrf-16` | `oob-listener` | bloqueado (não vetado; e não é `https`) |
| `http://2130706433/` | `2130706433` | bloqueado (forma de IP decimal não é host vetado) |
| `http://hooks.example.com.evil.test/` | `hooks.example.com.evil.test` | bloqueado (truque de sufixo: host completo não é vetado) |
| `http://oob-listener:80/proof-ssrf-16` | `oob-listener` | bloqueado (a porta é removida do host) |
| `https://hooks.example.com@oob-listener/` | `oob-listener` | bloqueado (truque de userinfo: o host real é depois do `@`) |

A última linha é a importante: a string `hooks.example.com` aparece na URL, então um teste ingênuo `if "hooks.example.com" in url` a deixaria passar — e deixaria a requisição alcançar o `oob-listener`. Parsear primeiro e comparar `hostname` derrota isso, porque `urlparse` retorna o host que o cliente de fato conectará. O bug neste átomo é a **ausência** de validação de destino; o fix, quando presente, tem que ser robusto — senão não é um fix de verdade.

## Por que o listener é embarcado

O átomo entrega o próprio sink out-of-band (`oob-listener`) em vez de te mandar apontar payloads pra um serviço de interação real. É o movimento estrutural honesto deste átomo. Detectar blind SSRF no campo depende de um serviço **externo** que você controla — Burp Collaborator, `interactsh`, um catcher de DNS/HTTP na internet. Este lab é isolado por design (bindado em `127.0.0.1`, sem dependência do mundo externo), então o exploit dele não pode exigir alcançar um terceiro. Embarcar um análogo self-hosted e air-gapped desse sink é o que deixa o ataque ser reproduzido offline, por qualquer um, com nada além de `docker compose logs`. É a mesma disciplina que você vê quando uma biblioteca ou um ambiente já provê algo em que o mundo real se apoia: em vez de fingir que não existe, o átomo modela o equivalente local honesto.
