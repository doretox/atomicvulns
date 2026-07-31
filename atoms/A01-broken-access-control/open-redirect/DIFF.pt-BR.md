# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é como o destino do login (`next`) é escolhido antes do redirect (comentários abreviados):

```diff
 import os
+from urllib.parse import urlparse
 from flask import Flask, request, redirect, render_template

 app = Flask(__name__)


+def safe_next(target, fallback="/dashboard"):
+    # Allowlist by STRUCTURE: accept only an internal path -- no scheme, no host ...
+    if not target:
+        return fallback
+    t = target.replace("\\", "/")          # browsers treat "\" like "/"; normalize before parsing
+    if not t.startswith("/") or t.startswith("//"):
+        return fallback                     # not an internal path, or protocol-relative "//host"
+    parsed = urlparse(t)
+    if parsed.scheme or parsed.netloc:
+        return fallback                     # any scheme or host present -> external -> refuse
+    return target
+
+
 @app.route("/", methods=["GET"])
 @app.route("/login", methods=["GET", "POST"])
 def login():
     if request.method == "POST":
         ...
         if request.form.get("username") == "demo" and request.form.get("password") == "demo":
-            next_url = request.form.get("next", "/dashboard")
-            # VULNERABLE: redirect to a user-controlled destination with NO check ...
+            # FIXED: the SERVER decides the destination via safe_next() -- internal path only ...
+            next_url = safe_next(request.form.get("next"))
             return redirect(next_url)
```

Todo o resto é byte-a-byte idêntico entre as duas versões: o tratamento do form de login, a checagem de credencial, a própria linha `return redirect(next_url)`, o `GET /dashboard`, o `__main__`, o `Dockerfile`, o `requirements.txt`, e os dois templates (`login.html`, `dashboard.html`). O bug — e o fix — vivem inteiramente em como o `next_url` é computado.

## O que mudou

A versão vulnerable atribui `next_url = request.form.get("next", "/dashboard")` — o valor cru, fornecido pelo cliente — e o entrega direto ao `redirect()`. A versão fixed passa ele por `safe_next()` antes: `next_url = safe_next(request.form.get("next"))`. Isso é um fix *lógica-diferente* — um novo passo de validação server-side, mais o import `urllib.parse` que ele usa. A chamada `redirect(next_url)` não muda; o que mudou é que o `next_url` agora é a decisão do **servidor**, não do cliente.

## Por que isso corrige o bug

`safe_next()` é uma allowlist de *estrutura*. Ela aceita um destino só se ele for um path interno puro:

- normaliza backslashes pra `/` primeiro, porque browsers tratam `\` como `/` (então `/\evil.example` se comportaria como `//evil.example`);
- exige um único `/` inicial e rejeita um `//` inicial (um `//host` protocol-relative é outro site);
- parseia e rejeita qualquer coisa com um `scheme` ou um `netloc` (host) — uma URL absoluta como `http://evil.example` ou `https://demo@evil.example` tem os dois.

Qualquer coisa que não seja um path interno limpo cai em `/dashboard`. Então `next=/dashboard` e `next=/settings` passam inalterados, enquanto `http://evil.example`, `//evil.example`, `/\evil.example` e `https://demo@evil.example` todos colapsam pra `/dashboard`. O redirect agora só pode cair numa das nossas próprias páginas.

## A causa é confiar no destino, não o redirect em si

Redirecionar depois do login é uma feature normal e desejada — isso não é o bug. O bug é confiar num valor *controlado pelo usuário* como o destino. Prova de isolamento: mande `next=/dashboard` pras duas apps e as duas voltam `Location: /dashboard`; a feature legítima é idêntica. Só um `next` *externo* diverge — a app vulnerable o emite verbatim, a app fixed o recusa. Não há nada de errado em "usar `redirect()`"; o fix é decidir o destino no servidor.

## Allowlist de estrutura, não blocklist de strings

O fix rápido tentador é *inspecionar a string* — "rejeitar `next` se começar com `http://`" ou "aceitar só se começar com `https://our-site.com`". Isso é um blocklist, e ele perde. Um tour rápido do que passa por ele:

- **`//evil.example`** — protocol-relative, não tem `http://` pra casar; o browser ainda resolve pra `https://evil.example`.
- **`https://our-site.com.evil.example`** — uma checagem de prefixo allowlist em `https://our-site.com` casa, mas o host real é `evil.example` (o nosso nome é só um rótulo de subdomínio do deles).
- **`https://our-site.com@evil.example`** — tudo antes do `@` é *userinfo*, não o host; a checagem casa `https://our-site.com`, o browser vai pra `evil.example`.
- **`/\evil.example`** e outros truques de backslash — browsers dobram `\` em `/`, então isso se comporta como `//evil.example`, mas uma checagem de string ingênua (e até alguns parsers de URL) tratam `\` literal e deixam passar.
- **percent-encoding** (`%2f%2fevil.example`, …) — mais grafias da mesma coisa pra um filtro de substring deixar passar.

Contra um atacante inventando grafias, string-matching é um jogo interminável de correr atrás. O fix durável é estrutural: em vez de perguntar "essa string parece perigosa?", pergunte "esse destino é um dos *nossos próprios paths* — sem scheme, sem host?". É isso que o `safe_next()` faz (e por que ele normaliza `\` antes de parsear, depois confia no `urlparse` em vez de checagens de substring). O blocklist é nomeado aqui pra mostrar por que ele falha; ele **não** é aplicado.

## Por que um path interno basta aqui

Este átomo restringe o `next` a paths internos porque um "te levar de volta pra onde você estava" de login não tem motivo legítimo de apontar pra outro domínio — então só-path cobre 100% do uso real e fecha o ataque. Isso não é universal. Se uma app genuinamente tivesse que redirecionar pra destinos *externos conhecidos* — SSO cross-domain, um gateway de pagamento, um callback de OAuth — o fix equivalente seria uma allowlist de **hosts**: uma lista fechada de destinos externos permitidos, casada por igualdade exata de host (não prefixo, não substring). Mesmo princípio — o servidor decide de um conjunto fixo — uma allowlist diferente. Essa host-allowlist é mencionada pra esse caso; esta app não precisa dela e não a usa.

## Impacto: baixo sozinho, perigoso como elo de corrente

Por si só um open redirect não revela nada, não roda nada e não muda nada no alvo — ele só relocaliza o browser, então isolado ele avalia como baixo. Seu valor real é como *elo de uma corrente*:

- **Credibilidade de phishing.** O link isca começa no domínio confiável; a vítima confere esse domínio e só depois é jogada pra look-alike do atacante. A origem confiável é o que vende o ataque.
- **Roubo de token em OAuth / SSO.** Onde um `redirect_uri` ou um retorno pós-login é mal-validado, um open redirect pode desviar um authorization code ou token pro destino do atacante.

Contraste isso com o `csrf-basic`, o outro átomo A01 num contexto de login/sessão: o CSRF faz o alvo *agir* em nome da vítima — um request de mudança-de-estado que o alvo executa porque o browser anexa o cookie de sessão da vítima automaticamente. Um open redirect faz o oposto: ele faz o alvo *mandar a vítima embora*, não executa ação nenhuma no alvo, e não precisa de cookie nenhum. Um abusa da confiança do alvo no cookie da vítima; o outro abusa da confiança da vítima no domínio do alvo. Este átomo prova o redirect pra fora; as escaladas encadeadas acima são o alcance da classe — descritas, não construídas.
