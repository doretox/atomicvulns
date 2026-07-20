# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é o bloco que roda *depois* do check de credenciais no `POST /login`:

```diff
     if CREDENTIALS.get(user) != password:
         abort(401)  # trivial credential check — the password is not the object of study
-    # VULNERABLE: authenticate the CURRENT session, keeping the SAME session_id. The id that
-    # existed before login (possibly attacker-planted) now identifies an AUTHENTICATED session.
-    # No new id when the privilege level changes (anonymous -> authenticated) = session fixation.
+    # FIXED: authenticate, then REGENERATE the session id. Rebind the now-authenticated session
+    # onto a NEW id and discard the old one, so any id that existed before login (possibly
+    # attacker-planted) can never become authenticated. This regeneration is the whole fix.
     sess["authenticated"] = True
     sess["user"] = user
-    return redirect("/account")  # cookie unchanged — the pre-login sid is now authenticated
+    new_sid = secrets.token_urlsafe(32)
+    SESSIONS[new_sid] = sess          # rebind the (now-authenticated) session onto a NEW id
+    del SESSIONS[sid]                 # discard the old (possibly planted) id
+    resp = redirect("/account")
+    resp.set_cookie("session_id", new_sid, httponly=True, samesite="Lax")
+    return resp
```

Todo o resto — os imports, `SESSIONS`, `CREDENTIALS`, `current_session`, `GET /`, `GET /account`, o rodapé, e **os dois templates** — é byte a byte idêntico entre as duas versões.

## O que mudou

Repare nas duas linhas que *não* mudaram: `sess["authenticated"] = True` e `sess["user"] = user`. Autenticar a sessão é igual nas duas versões. O que o fix **acrescenta** é tudo em volta do id:

- `new_sid = secrets.token_urlsafe(32)` — cunha um session id novinho.
- `SESSIONS[new_sid] = sess` — rebinda o objeto de sessão (agora autenticado) nesse id novo.
- `del SESSIONS[sid]` — descarta o id antigo por inteiro, pra ele não identificar nada.
- `resp.set_cookie("session_id", new_sid, ...)` — entrega o id novo pro cliente.

A versão vulnerable não faz nada disso; ela só retorna, e o cookie que o cliente já segura — o id pré-login — agora é uma sessão autenticada. É um fix *lógica-diferente*: não um valor trocado, mas código adicionado — a mesma forma dos átomos de access control, onde o fix é o código que faltava.

## Por que isso resolve

A classe é: **uma sessão autenticada é identificada por algo que existia antes da autenticação.** A remediação é exatamente a negação: **emitir um session id novo no momento em que o nível de privilégio muda** (anônimo → autenticado), e largar o antigo. Qualquer id que um atacante pudesse ter plantado antes do login é descartado no instante em que a vítima autentica, então ele nunca nomeia uma sessão autenticada. É o fix inteiro — uma regeneração, num momento.

Repare no que *não* está no diff. Os ids já eram fortes. O cookie já tinha `HttpOnly` e `SameSite`. O check de login, os templates, o storage — tudo inalterado. Nada disso era o bug, e nada disso precisava mexer.

## Fixation não é hijacking

O bug vizinho com que este é mais confundido é o session *hijacking*, e a diferença é o ponto inteiro do átomo:

- **Hijacking** *rouba* um session id que já está **autenticado** — depois do login, via sniffing, XSS lendo o cookie, malware. O atacante pega algo que existe.
- **Fixation** *fornece* um session id **antes** da autenticação e deixa a vítima autenticá-lo. O atacante dá algo e espera.

Direção (subtrair vs dar) e timing (depois vs antes). O atacante num ataque de fixation nunca lê o cookie autenticado da vítima — ele teve o id desde antes de a vítima logar. É por isso que o fix é **regeneração**, que mata fixation especificamente: mesmo um atacante que segura o id pré-login o perde no instante em que o id rotaciona no login.

## Por que uma sessão server-side manual, e não `flask.session`

A app vulnerable faz o próprio store de sessão (`SESSIONS` dict + cookie `session_id` opaco) em vez de usar o `session` nativo do Flask. Isso é deliberado, e é a parte honesta do átomo.

O `session` do Flask é um **cookie assinado client-side**: os dados da sessão são serializados, assinados com a `SECRET_KEY`, e guardados no próprio cookie. Não há id server-side pra fixar, e o valor do cookie *muda* no instante em que você loga (agora codifica `authenticated: True, user: alice`, re-assinado) — então ele regenera por natureza. Um atacante não consegue plantar um valor que vire autenticado, porque forjar esse valor exigiria a `SECRET_KEY` (um bug completamente diferente). **Um átomo de session fixation construído sobre `flask.session` não seria vulnerável.**

Session fixation vive na outra forma, mais comum: uma **sessão server-side com um id opaco no cookie** (`PHPSESSID`, `JSESSIONID`, e todo framework que guarda sessão server-side). Essas precisam **rotacionar o id no login**, e esquecer disso é o bug. Este átomo modela essa forma pra a rotação ausente ficar visível. É o mesmo movimento honesto que você vê quando uma lib já mitiga uma classe: a ferramenta padrão resiste ao bug, então o bug sobrevive em código que gerencia sessão na mão — que é exatamente onde ele vive no mundo real.

## Flags de cookie não consertam isso

Um "fix" tentador é blindar o cookie: `HttpOnly`, `Secure`, `SameSite`. Resista. Essas flags defendem contra **roubo** de cookie (hijacking) — e a app vulnerable **já seta `HttpOnly` e `SameSite`**, e mesmo assim é totalmente explorável. Fixation nunca lê o cookie da vítima, então proteger a confidencialidade do cookie não toca em nada. (`Secure` fica de fora só porque o lab roda em HTTP puro; em produção você a setaria, mas ela é igualmente ortogonal a fixation.) O fix durável é regenerar o id, ponto — e é por isso que as flags são idênticas nas duas versões e ficam fora do diff.

## O session id é forte nas duas versões

`secrets.token_urlsafe(32)` cunha o id na app vulnerable *e* na fixed — 256 bits de entropia, impossível de adivinhar em qualquer uma. Isso importa: se o id fosse fraco, o átomo carregaria **dois** bugs (um id previsível *e* a não-regeneração), e um leitor poderia "consertar" o errado. O id aqui é forte; o único bug é que a app vulnerable deixa um id legitimamente emitido sobreviver à transição anônimo → autenticado. Regeneração — não mais entropia — é o fix.

## Uma nota sobre migração

O fix rebinda o *mesmo objeto de sessão* num id novo (`SESSIONS[new_sid] = sess; del SESSIONS[sid]`) em vez de construir um do zero. Aqui não há estado pré-login digno de preservar além das duas flags que acabamos de setar, então faz pouca diferença. Numa app real você carregaria o estado benigno pré-login (um carrinho, um locale, um CSRF token) pro id novo — mas **nunca o id em si**. Regenerar o identificador preservando a sessão é exatamente o que "session id regeneration" significa.
