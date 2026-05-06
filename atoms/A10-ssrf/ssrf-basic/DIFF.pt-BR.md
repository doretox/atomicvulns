# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`:

```diff
 import os
+from urllib.parse import urlparse
 import requests
-from flask import Flask, request, render_template
+from flask import Flask, request, render_template, abort

 app = Flask(__name__)

+ALLOWED_HOSTS = {"api.github.com", "wikipedia.org"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/fetch")
 def fetch():
     url = request.args.get("url", "")
     if not url:
         return render_template("index.html")
-    # VULNERABLE: server-side request to attacker-controlled URL, no allowlist.
+    parsed = urlparse(url)
+    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
+        abort(403)
     try:
         response = requests.get(url, timeout=5)
         content, status = response.text, response.status_code
     except requests.RequestException as exc:
         content, status = f"Request error: {exc}", None
     return render_template("preview.html", url=url, content=content, status=status)
```

Os templates são idênticos nas duas versões — o bug vive inteiramente na ausência de validação ao redor do `requests.get`.

## O que mudou

Três edits, todos em `app.py`:

- Import novo: `urllib.parse.urlparse`, mais `abort` do `flask`.
- Uma constante `ALLOWED_HOSTS` com os únicos dois hostnames que a feature aceita buscar.
- Um gate de duas linhas inserido antes do `requests.get`: faz o parse da URL uma vez e rejeita qualquer coisa cujo scheme não seja `https` ou cujo hostname não esteja na allowlist. Requests rejeitados devolvem `403 Forbidden`.

## Por que isso resolve

O fix é uma **lista positiva**: só `https://api.github.com/...` e `https://wikipedia.org/...` passam. Qualquer outra coisa — `http://internal/`, `http://169.254.169.254/`, `file:///etc/passwd`, `gopher://...`, ou um domínio qualquer — falha no check e nunca chega no `requests.get`. A decisão é "essa URL está na lista pequena do que a gente aceita?", e a resposta é sim só quando a URL já estava na lista pra começar.

O check acontece **depois** do parse via `urlparse`, não fazendo string-matching no argumento `url` cru. Isso importa: `https://api.github.com.evil.tld/`, `https://api.github.com@evil.tld/` e `https://EVIL.com/?x=api.github.com` passariam todos por um teste ingênuo do tipo `if "api.github.com" in url` mas falham nesse aqui — `urlparse(...).hostname` devolve o hostname real ao qual o client HTTP vai se conectar (`api.github.com.evil.tld`, `evil.tld`, `evil.com`), que é o que comparamos.

O check também é **agnóstico ao content-type** — ele roda na URL do request, não na response. O serviço `internal` deste lab serve `text/plain` por legibilidade, mas o fix se comportaria igual se `internal` começasse a devolver HTML, JSON, binário, ou qualquer outra coisa: URLs são rejeitadas antes do fetch acontecer, e nada da response é jamais inspecionado. Vale deixar isso explícito pra que uma futura mudança de formato no serviço internal nunca seja confundida com regressão no fix.

## Por que blocklist não é o fix

Uma alternativa de aparência natural é **bloquear** inputs conhecidos como ruins em vez de permitir os conhecidos como bons — strings tipo `internal`, `localhost`, `127.0.0.1`, `169.254.169.254`, ou faixas de IP RFC 1918. Não faça. Blocklists pra SSRF perdem pra bypass repetidamente:

- Resolução DNS no momento do fetch pode devolver IP privado pra um hostname de cara pública (DNS rebinding, ou simplesmente um domínio controlado pelo atacante cujo A record aponta pra `127.0.0.1`).
- IPv6 (`::1`, `[::ffff:127.0.0.1]`) e representações alternativas de IPv4 (`2130706433`, `017700000001`, `0x7f000001`) escapam de filtros de string que só conhecem a forma decimal pontuada.
- Redirects: a URL que você checa resolve pra um host público, devolve `302` pra `http://169.254.169.254/`, e seu client HTTP segue. O check rodou na URL errada.
- Parsers de URL e clients HTTP às vezes discordam sobre qual substring é "o host" — userinfo, colchetes de IPv6, ponto final, caracteres percent-encoded na authority, todos criam frestas.

O átomo `ssrf-blind-oob` (átomo 16) caminha por vários desses bypasses contra uma defesa por blocklist mais realista. Por enquanto o takeaway é forma, não técnica: **allowlists são finitas e decidem por intenção; blocklists são infinitas e decidem por palpite.**

## Contraste com os átomos anteriores

Este é o segundo átomo cujo fix *adiciona* código em vez de remover (o primeiro foi `idor-numeric-id`). Em `sqli-union-basic` e `xss-reflected`, o fix era apagar um único construct ruim — a montagem da SQL via f-string, o filter `|safe`. Em `idor-numeric-id`, o fix era um check explícito de ownership que deveria estar lá. Aqui é outro tipo de "check ausente": o check do IDOR responde "esse caller é dono desse objeto?", uma propriedade de *quem está pedindo*; o check do SSRF responde "essa URL está no conjunto pequeno de coisas que a gente vai buscar?", uma propriedade do *que está sendo pedido*. Mesma família — bug como ausência — mas a pergunta que falta é diferente. Saber que tipo de pergunta está faltando é a maior parte do trabalho de achar bugs dessa família numa revisão de código.
