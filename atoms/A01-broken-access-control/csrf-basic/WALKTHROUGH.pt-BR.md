# Walkthrough — csrf-basic

O alvo é uma página de conta com uma ação: trocar o e-mail de recuperação. Você loga, digita um novo e-mail, e o `POST /email` atualiza a conta. O servidor sabe que é você porque o browser mandou o **cookie de sessão** — o valor que ele guardou no login e reenvia automaticamente em toda request pra este site. Esse reenvio automático é o problema inteiro: o browser anexa o cookie não importa *qual site* causou a request. Uma página em outro site pode conter um `<form>` escondido que dispara um `POST /email` neste alvo a partir do browser da vítima, e o browser vai anexar o cookie de sessão da vítima nele. O servidor vê um cookie válido e troca o e-mail — como se a vítima tivesse pedido. A vítima nunca pediu, e o atacante nunca soube a senha nem leu o cookie.

## 1. Context

O `POST /email` é uma **request de mudança-de-estado** — uma que altera algo no servidor (aqui, o e-mail de recuperação da conta). O servidor a autoriza checando uma coisa: existe um **cookie de sessão** válido? Isto é **CSRF (Cross-Site Request Forgery)**: um atacante faz o browser da vítima disparar uma request de mudança-de-estado num site onde ela está logada, pegando carona na sessão dela. Dois termos nomeiam o cenário. **Cross-site** quer dizer que a request parte de um *site diferente* do alvo (um host registrável diferente — aqui `127.0.0.2` versus o `127.0.0.1` do alvo). A **Same-Origin Policy (SOP)** é a regra do browser que deixa uma origem *enviar* uma request pra outra mas proíbe *ler* a resposta — por isso o CSRF é um ataque cego, fire-and-forget: o atacante dispara a ação mas nunca vê o resultado.

Há uma condição pra isto disparar. O atributo **`SameSite`** de um cookie diz ao browser quando anexá-lo em requests cross-site; o default moderno, `SameSite=Lax`, **não** anexa o cookie num `POST` cross-site, o que bloqueia o CSRF ingênuo sozinho. Este alvo afrouxa o cookie pra `SameSite=None` (a misconfig que reabre o buraco — comum em embeds cross-site e em configs de cookie copiadas sem entender). `SameSite=None` exige o flag `Secure`, que normalmente significa só-HTTPS; funciona aqui sobre HTTP puro porque `127.0.0.1` é um *secure context* (origens loopback são tratadas como confiáveis).

Três serviços, e nenhum fala com o outro — o browser da vítima faz toda request cross-site:

- alvo `vulnerable` — `http://127.0.0.1:8023/`
- alvo `fixed` — `http://127.0.0.1:8123/`
- site `attacker` — `http://127.0.0.2:8080/` (um **site diferente** dos alvos, ainda loopback)

Como o ato que define o CSRF é o browser anexar o cookie sozinho, o browser é onde você explora; o Burp é uma lente de apoio que mostra a request forjada na rede.

## 2. Spot the bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). O bug inteiro é a checagem de autorização no `POST /email`:

```python
@app.route("/email", methods=["POST"])
def change_email():
    if "user" not in session:
        return "Not logged in", 403
    ACCOUNT["email"] = request.form.get("email", "")
    return redirect("/")
```

A única barreira é `if "user" not in session` — *existe um cookie de sessão válido?* Pergunta de auditoria: *este endpoint muda estado, e checa só **quem** está logado — ele checa que o usuário **quis** esta request específica?* Não há token, não há checagem de `Origin`/`Referer`. O cookie prova identidade, e o browser o anexa a qualquer request pra este site — inclusive uma que uma página hostil dispare. (O fix, foreshadowed: exigir um segredo que só uma página servida por este site poderia conter.)

No login o servidor seta o cookie de sessão com os atributos afrouxados:

```
Set-Cookie: session_vuln=...; Secure; HttpOnly; Path=/; SameSite=None
```

`SameSite=None` é o sinal verde pro browser anexar este cookie em requests cross-site.

## 3. Exploitation (no browser)

O ato que define o ataque — o browser anexar o cookie da vítima numa request cross-site — só acontece num browser, então é aqui que você explora. Passe o browser pelo proxy do Burp pra capturar o tráfego pra Seção 4.

### Baseline — a feature

Abra `http://127.0.0.1:8023/`, logue com `demo` / `demo`. A página da conta mostra o estado atual e o form legítimo de troca:

```
Logged in as demo. Recovery email: demo@example.com
```

Troque o e-mail pelo form e ele atualiza — uso normal, intencional. A vítima agora é um usuário logado com um cookie de sessão vivo.

### A página do atacante

O serviço `attacker` serve uma página cujo único conteúdo é um form escondido que se auto-submete no load. `http://127.0.0.2:8080/attack-vuln` é:

```html
<body onload="document.forms[0].submit()">
<form action="http://127.0.0.1:8023/email" method="POST">
  <input type="hidden" name="email" value="attacker@evil.example">
</form>
</body>
```

É um `POST` de form HTML puro (content type `application/x-www-form-urlencoded`) — uma "simple request" que o browser manda cross-site **com cookies** e sem preflight CORS. É por isso que o ataque usa um form e não um `fetch` JSON (que dispararia um preflight que o alvo não permitiu).

### Dispare

Com a vítima ainda logada em `127.0.0.1:8023`, abra a página do atacante em `http://127.0.0.2:8080/attack-vuln`. O form se auto-submete; o browser dispara o `POST /email` no alvo e — porque o cookie é `SameSite=None` — anexa o cookie de sessão da vítima nessa request cross-site. Recarregue a página da conta do alvo:

```
Logged in as demo. Recovery email: attacker@evil.example
```

O e-mail de recuperação agora é o do atacante. **Account takeover:** quem controla o endereço de recuperação pode disparar um reset de senha e recebê-lo. A vítima só abriu uma página em outro site.

Tudo aqui é benigno e local: uma conta fake, um endereço `@evil.example` (um TLD reservado), tudo em loopback, nada destrutivo.

## 4. What Burp shows (e por que o `curl` não)

O CSRF é disparado do browser, mas o Burp prova a mecânica. Em **Proxy → HTTP history**, ache o `POST /email` forjado que a página do atacante disparou:

```
POST /email HTTP/1.1
Host: 127.0.0.1:8023
Cookie: session_vuln=eyJ1c2VyIjoiZGVtbyJ9...
Content-Type: application/x-www-form-urlencoded

email=attacker@evil.example
```

Dois fatos, juntos, são a vulnerabilidade inteira. **O cookie de sessão está presente** — o browser o anexou automaticamente, mesmo a request vindo de `127.0.0.2`. **Não há token** no corpo: só `email=...`. O servidor checou só o cookie, então a request forjada foi autorizada. (Confirmado na camada de rede pela própria contabilidade de cookies do browser: na request forjada, o `session_vuln` é reportado como enviado, sem motivo de bloqueio.)

**Por que o `curl` não é a prova.** É tentador "reproduzir" isto pelo Repeater ou `curl`. Não funciona como CSRF:

```
$ curl -X POST -d "email=x@evil.example" http://127.0.0.1:8023/email
Not logged in                       # HTTP 403 — sem cookie de sessão

$ curl -X POST -H "Cookie: session_vuln=<cole>" -d "email=x@evil.example" \
       http://127.0.0.1:8023/email
                                     # HTTP 302 — e-mail trocado
```

A segunda chamada funciona, mas não é CSRF: *você* colou um cookie que já tinha. Não há vítima, não há outro site, nada foi enganado. O CSRF é justo a parte que o `curl` não consegue fazer — fazer o browser de uma *vítima* anexar o cookie *dela* a uma request que o *atacante* disparou de *outra origem*. Isso só acontece num browser, e é por isso que o exploit é browser-driven e o Burp só observa.

## 5. What the vuln is NOT

O exploit é uma request de aparência legítima, então isole o que de fato deu errado:

- **NÃO é XSS.** Nenhum código do atacante roda no alvo. O form do atacante roda na origem *do atacante*, dispara uma request e — pela Same-Origin Policy — **não consegue ler a resposta**. O ataque é cego: muda estado, não lê dado. "Cross-site" aqui não é "cross-site scripting". (Em [`xss-reflected`](../../A03-injection/xss-reflected/), [`xss-stored`](../../A03-injection/xss-stored/) e [`xss-dom`](../../A03-injection/xss-dom/), o script do atacante roda *dentro* da origem do alvo e lê tudo; o CSRF é o oposto — de fora, e cego.)
- **NÃO é o atacante roubar o cookie.** O atacante nunca tem, lê ou copia o cookie de sessão. O *browser* da vítima o anexa, sozinho, a uma request que o atacante só disparou. A Seção 4 mostrou o cookie presente na request forjada enquanto a página do atacante nunca o tocou.
- **NÃO é sessão quebrada nem login bypass.** A sessão é perfeitamente válida e a vítima logou de verdade. Diferente de [`session-fixation`](../../A07-auth-failures/session-fixation/), onde a falha está no ciclo de vida da sessão, aqui a sessão está correta. O buraco é a **intenção**: o servidor tratou "tem um cookie de sessão válido" como "o usuário quis esta ação".

O que **é**: o servidor autoriza uma ação de mudança-de-estado só pelo cookie — *quem* você é — sem checar *que você quis*. O fix exige uma prova de intenção que o atacante não consegue suprir.

## 6. Impact

**Account takeover via uma mudança-de-estado forçada.** O `POST` forjado troca o e-mail de recuperação da conta por um que o atacante controla; um "esqueci a senha" seguinte manda o reset pro atacante. Mais amplamente, qualquer ação de mudança-de-estado guardada só pelo cookie de sessão — trocar e-mail, trocar senha, transferir dinheiro, adicionar admin — pode ser disparada de uma página que a vítima só visita. Sem overclaim: CSRF é sobre *ações que a vítima não pediu*, não roubo de dado — a Same-Origin Policy cega o atacante pra resposta — e roda no browser da vítima, não no servidor.

## 7. Why the fix works

Aponte a página do atacante pro alvo fixed: abra `http://127.0.0.2:8080/attack-fixed` (o form dela posta pra `127.0.0.1:8123/email`) com a vítima logada em `127.0.0.1:8123`. A request forjada retorna:

```
Forbidden
```

Um HTTP `403`, e o e-mail da conta está **inalterado** (`demo@example.com`). Olhe bem esse `403`: é a página "Forbidden" default do Flask, **não** a mensagem `"Not logged in"` do `curl` sem cookie da Seção 4. Essa distinção é o ponto — a request forjada **passou** na checagem de sessão (o cookie *foi* anexado, `SameSite=None` como sempre), e foi então rejeitada pela checagem do *token*. Na rede a request forjada ainda carrega `Cookie: session_fixed=...` e um corpo de só `email=attacker@evil.example` — o cookie viajou junto exatamente como antes; o que falta é o token.

O alvo fixed adiciona um **token anti-CSRF** por sessão (um "synchronizer token"): um segredo gerado server-side, guardado na sessão e embutido como hidden field no próprio form de e-mail do alvo. O `POST /email` agora o exige no corpo e o compara com a cópia da sessão. O fluxo legítimo continua funcionando — o próprio form da vítima carrega o token, então submetê-lo manda `csrf_token=...&email=...` e a troca passa (verificado: o form real do alvo fixed atualiza o e-mail pra um novo valor sem `403`). A request forjada falha porque o atacante **não consegue ler o token**: ele vive no form HTML do alvo, e a Same-Origin Policy proíbe a página do atacante de ler uma resposta cross-origin. O cookie que o browser manda de graça não basta; o token tem que ser *suprido*, e só uma página da própria origem do alvo o tem.

Note o que **não** mudou: a config do cookie é `SameSite=None; Secure` nos dois lados. O token é a *única* diferença de segurança — o que prova que o fix é o token, não re-apertar o `SameSite`. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) para a mudança e para as três defesas legítimas de CSRF (o token, o `SameSite` e uma checagem de `Origin`/`Referer`) e como elas se somam em camadas.
