# DIFF — vulnerable vs. fixed

O fix é uma coisa só: um **token anti-CSRF** por sessão (um "synchronizer token"), feito à mão — sem framework, sem `Flask-WTF`. O servidor gera um segredo por sessão, embute como hidden field no próprio form de e-mail e o exige de volta no corpo do `POST /email`. Todo o resto não muda; em particular a config de segurança do cookie de sessão é **idêntica** nos dois lados (`SameSite=None; Secure`), então o token é a *única* diferença de segurança entre os dois apps.

## A mudança — `app.py`

```diff
 import os
+import secrets
-from flask import Flask, render_template, request, redirect, session
+from flask import Flask, render_template, request, redirect, session, abort

 app.config.update(
-    SESSION_COOKIE_NAME="session_vuln",
+    SESSION_COOKIE_NAME="session_fixed",
     SESSION_COOKIE_SAMESITE="None",
     SESSION_COOKIE_SECURE=True,
 )

+def csrf_token():
+    # One unguessable secret per session, stored server-side in the session.
+    if "csrf_token" not in session:
+        session["csrf_token"] = secrets.token_urlsafe(32)
+    return session["csrf_token"]

 @app.route("/")
 def index():
     if "user" not in session:
         return render_template("login.html")
-    return render_template("account.html", email=ACCOUNT["email"])
+    return render_template("account.html", email=ACCOUNT["email"], csrf_token=csrf_token())

 @app.route("/email", methods=["POST"])
 def change_email():
     if "user" not in session:
         return "Not logged in", 403
+    token = session.get("csrf_token")
+    if not token or request.form.get("csrf_token") != token:
+        abort(403)
     ACCOUNT["email"] = request.form.get("email", "")
     return redirect("/")
```

O `SESSION_COOKIE_NAME` difere (`session_vuln` vs `session_fixed`) por uma razão não-de-segurança: os dois alvos moram em `127.0.0.1`, e cookies ignoram a porta, então um único nome de cookie seria compartilhado entre as portas 8023 e 8123. Nomes distintos mantêm os dois logins separados. Os dois atributos de segurança — `SESSION_COOKIE_SAMESITE="None"` e `SESSION_COOKIE_SECURE=True` — são byte-idênticos nos dois lados.

## A mudança — `templates/account.html`

```diff
 <form method="post" action="/email">
+  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
   <label>New email: <input type="email" name="email" autofocus></label>
   <button type="submit">Update email</button>
 </form>
```

O próprio form do servidor agora carrega o token. `login.html`, o resto de `account.html`, o `Dockerfile` e o `requirements.txt` são byte-a-byte idênticos entre os dois apps.

## Por que isso conserta o bug

O `POST /email` vulnerable perguntava só *"existe um cookie de sessão válido?"* — e o browser anexa esse cookie a qualquer request pro site, inclusive uma que uma página hostil dispare. O `POST /email` fixed também pergunta *"a request carrega o token secreto da sessão?"*. O form legítimo tem (o servidor o pôs lá); a request forjada de outro site não tem, porque **o atacante não consegue ler o token pra incluí-lo**. A Same-Origin Policy deixa a página do atacante *enviar* uma request pro alvo mas proíbe *ler* a resposta do alvo — então ela nunca vê o hidden field, e nunca o preenche. O `secrets.token_urlsafe(32)` torna o token não-adivinhável, então também não dá pra brute-forçar.

## O token vai na request, não (só) no cookie

Este é o cerne, e vale dizer com precisão. A request forjada **já carrega o cookie de sessão** — o browser o anexa automaticamente porque `SameSite=None`. Então "tem o cookie de sessão?" não pode ser o teste que barra o CSRF: a resposta é *sim* também pra request forjada. O que separa uma request real de uma forjada é um valor que tem que ser **suprido ativamente no corpo da request** — algo que o atacante teria que *ler* pra incluir, e a Same-Origin Policy o impede de ler.

Há uma sutileza em *onde* o token de referência vive. Nesta implementação ele fica na sessão, o que no Flask significa que ele viaja dentro do cookie de sessão assinado — então o token, também, viaja na request forjada. Tudo bem, porque a checagem não compara o cookie com ele mesmo: ela compara o token no **corpo da request** (`request.form.get("csrf_token")`) com a cópia da sessão. A request forjada supre o cookie (de graça, via browser) mas *não* o token do corpo — e o token do corpo é a metade que o atacante não consegue produzir. A defesa funciona exigindo algo que o atacante teria que **ler**, não algo que o browser manda sozinho.

## Três defesas legítimas de CSRF, em três camadas

Átomos anteriores deste repo emparelham o fix real com uma nota nomeando uma defesa *errada* ou parcial — um filtro, uma assinatura, escape no servidor — que parece certa mas erra o alvo. **CSRF é diferente: tem três defesas genuinamente legítimas, em três camadas diferentes, e esta nota nomeia as três com honestidade.**

- **Token anti-CSRF (synchronizer token) — camada de APLICAÇÃO.** *É o que o fix aplica.* Verifica **intenção**: só uma página servida pelo próprio site carrega o token, e o atacante não consegue lê-lo (SOP), então não forja uma request completa. Funciona em qualquer browser e não depende do transporte nem de atributos do cookie.
- **`SameSite=Lax` / `Strict` — camada de COOKIE.** É o default do browser que este app *desligou*. Manda o browser não anexar o cookie em requests cross-site de jeito nenhum — defense-in-depth de verdade, não um remendo. Mas depende de o browser honrá-lo, e alguns fluxos legítimos (embeds cross-site, alguns SSO) precisam de `SameSite=None`, e aí esta camada some. É exatamente a situação que este átomo modela.
- **Checagem de `Origin` / `Referer` — camada de SERVIDOR.** O servidor confere que a request veio da própria origem. Alternativa válida e barata — mas depende de esses headers estarem presentes e confiáveis (ferramentas de privacidade e alguns proxies removem ou alteram), então costuma ser complemento, não o único controle.

As três são legítimas, e em produção você as empilha (um token *e* `SameSite=Lax` *e*, muitas vezes, uma checagem de `Origin`). Este átomo aplica o **token** por ser o portável e o que verifica intenção diretamente, e mantém `SameSite=None` nos dois lados justamente pra que o token — não o atributo do cookie — seja visivelmente o que fecha o buraco.

## A config do cookie é idêntica — o token é o único delta de segurança

Olhe o que *não* está neste diff: nenhuma mudança em `SESSION_COOKIE_SAMESITE` ou `SESSION_COOKIE_SECURE`. Os dois apps rodam `SameSite=None; Secure`. O app fixed **não** fecha o buraco re-apertando o `SameSite` pra `Lax`; ele fecha com o token, deixando o cookie afrouxado no lugar. Isso isola a lição: com a config do cookie mantida constante, o `POST` forjado ainda chega *com o cookie de sessão* nos dois apps — passa no vulnerable e retorna `403` no fixed — então o token, e só o token, é o que fez a diferença. O fluxo benigno e legítimo fica intacto: submeter o próprio form do alvo (que carrega o token) atualiza o e-mail nos dois apps.

## O impacto é account takeover — e não é XSS

A request forjada troca o e-mail de recuperação da conta por um que o atacante controla, o que transforma um "esqueci a senha" num account takeover. A classe com que mais se confunde é XSS — as duas envolvem "outro site" — então vale traçar o contraste com nitidez:

| | **XSS** (`xss-reflected` / `xss-stored` / `xss-dom`) | **CSRF** (este átomo) |
|---|---|---|
| Onde o código do atacante roda | **dentro** da origem do alvo | na origem **do atacante** (nenhum código no alvo) |
| Consegue ler a resposta do alvo? | **sim** — mesma origem, lê cookies, DOM, corpo | **não** — a SOP proíbe ler cross-origin; o ataque é **cego** |
| O que consegue | ler **e** escrever no contexto do alvo | **disparar** uma ação de mudança-de-estado, fire-and-forget |
| Categoria OWASP | A03 — Injection | A01 — Broken Access Control |

A regra de bolso: **XSS roda dentro do alvo e lê tudo; CSRF dispara de fora e é cego.** O CSRF não consegue ler dado (a SOP o cega) e não roda código no servidor — ele força uma mudança-de-estado que a vítima não pediu. É por isso que é **A01 — Broken Access Control**: o servidor autorizou uma ação privilegiada só pela identidade (uma sessão válida), sem verificar que o usuário quis aquilo.
