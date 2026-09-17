# Walkthrough — open-redirect

A app tem um form de login com o padrão comum "te levar de volta pra onde você estava": o destino pra onde ela deve te mandar de volta vem num parâmetro `next` (`/login?next=/dashboard`). Logue com credenciais válidas e, no sucesso, o servidor responde `302 Found` com `Location: <next>`, e o browser segue pra lá. O problema: o servidor põe *qualquer* coisa que o `next` disser nesse `Location`, sem checar que o destino é uma das próprias páginas dele. Mande `next=http://evil.example` e a resposta do login redireciona a vítima pra bem longe do site — pro atacante. A prova é server-side e está bem na resposta: o header `Location` do `302`. Tudo aqui é feito no Burp (ou `curl -i`); não há passo de browser, porque o redirect é decidido e visível no fio.

## 1. Contexto

A app `vulnerable` está em `127.0.0.1:8024` e a `fixed` em `127.0.0.1:8124`; não há banco nem segundo serviço. `GET /login` mostra um form de login que carrega o valor de `next` num hidden field, prefilado a partir da query string. `POST /login` com as credenciais demo (`demo` / `demo`) tem sucesso e redireciona pra `next`. `GET /dashboard` é a landing page interna pra onde você deveria voltar.

Isto é um **open redirect**: a app redireciona o usuário pra um destino tirado do input do usuário sem checar que o destino é dela mesma. Termos usados abaixo:

- **parâmetro `next`** (também visto como `returnUrl`, `redirect_to`, `continue`): o valor que carrega "pra onde mandar o usuário de volta" depois de uma ação como o login.
- **path relativo** (`/dashboard`): um destino *dentro* deste site — sem host, resolvido contra a origem atual.
- **URL absoluta** (`https://host/path`): um destino com scheme e host próprios — outro site.
- **URL protocol-relative** (`//host`): uma URL sem scheme; o browser a resolve contra o scheme atual, então `//evil.example` vira `https://evil.example` — outro site. É a forma que um filtro ingênuo de `http://` deixa passar.
- **header `Location`**: o header de resposta num redirect `3xx` que diz ao browser pra onde ir.

Isto é **A01 — Broken Access Control** (CWE-601, "URL Redirection to Untrusted Site"): o controle que falta é sobre *pra onde a app pode mandar o usuário*. A exploração é feita inteiramente no Burp; `curl -i` é o equivalente.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). Num login bem-sucedido a view redireciona assim:

```python
if request.form.get("username") == "demo" and request.form.get("password") == "demo":
    next_url = request.form.get("next", "/dashboard")
    # VULNERABLE: redirect to a user-controlled destination with NO check that it
    # points inside our own site ...
    return redirect(next_url)
```

`redirect(next_url)` seta `Location: <next_url>` e devolve um `302`. `next_url` é o valor cru que o cliente mandou — nada checa que ele aponta pra dentro deste site. Pergunta de auditoria: *o destino vem direto do meu input, e o servidor nunca pergunta "isto é uma das minhas próprias páginas?"* — então qualquer URL que eu puser em `next` vira o `Location`. O fix (foreshadow): deixar o **servidor** decidir o destino — aceitar só um path interno.

## 3. Exploração via Burp Suite

Configure o Burp Proxy e aponte seu browser pra ele. Visite <http://127.0.0.1:8024/>, submeta o form de login uma vez (`demo` / `demo`) pra capturar o tráfego, depois clique com o botão direito no request `POST /login` em **Proxy → HTTP history** e escolha **Send to Repeater**.

O redirect dispara no `POST /login`, então é isso que trabalhamos no Repeater. O atacante entrega o `next` malicioso com um link GET — `/login?next=<destino>` — e o form de login carrega esse valor pro POST como hidden field, então uma vítima logando normalmente o manda de volta. Testar o `POST /login` direto exercita exatamente o request que o browser da vítima faz. A prova é a status line e o header `Location` da resposta, então **não siga o redirect** (no curl, sem `-L`).

### Passo 1 — Baseline: a feature funciona

Request no Repeater:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8024
Content-Type: application/x-www-form-urlencoded
Content-Length: 43

username=demo&password=demo&next=/dashboard
```

Resposta (só os headers — o `302` é o ponto inteiro):

```
HTTP/1.1 302 FOUND
Content-Type: text/html; charset=utf-8
Content-Length: 207
Location: /dashboard
```

O equivalente com curl:

```bash
curl -i http://127.0.0.1:8024/login -d 'username=demo&password=demo&next=/dashboard'
```

`Location: /dashboard` é um **path relativo** — o browser fica no alvo e cai na dashboard interna. Esse é o "te levar de volta pra onde você estava" legítimo. Daqui em diante, só o valor de `next` muda.

### Passo 2 — Redirecionar a vítima pra fora (o ataque)

Troque `next` por uma URL absoluta apontando pro site do atacante:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8024
Content-Type: application/x-www-form-urlencoded
Content-Length: 52

username=demo&password=demo&next=http://evil.example
```

Resposta:

```
HTTP/1.1 302 FOUND
Content-Type: text/html; charset=utf-8
Content-Length: 225
Location: http://evil.example
```

`Location: http://evil.example` — a resposta do login agora manda a vítima pra **outro host**. O link que começou isso foi `http://127.0.0.1:8024/login?next=http://evil.example`: ele começa no próprio domínio do alvo (no qual a vítima confia e onde ela realmente loga), e o próprio alvo a joga pro atacante. Isso é o open redirect. (`evil.example` é um TLD reservado pra documentação — não resolve pra nada, e a app nunca conecta nele; ela só *emite* o `Location`.)

### Passo 3 — O payload `//` que um blocklist deixa passar

Um dev que "conserta" isso bloqueando `http://` ainda perde. Mande uma URL **protocol-relative** — sem scheme:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8024
Content-Type: application/x-www-form-urlencoded
Content-Length: 47

username=demo&password=demo&next=//evil.example
```

Resposta:

```
HTTP/1.1 302 FOUND
Content-Type: text/html; charset=utf-8
Content-Length: 215
Location: //evil.example
```

`Location: //evil.example` não tem `http://` nem `https://` pra um filtro de string casar — mas um browser resolve `//evil.example` contra o scheme atual, virando `https://evil.example`. Mesmo redirect pra fora, passando pelo filtro ingênuo. (O Werkzeug passa o `Location` verbatim aqui; versões antigas reescreviam locations relativos pra absolutos, que é exatamente por que os bytes valem ser capturados em vez de assumidos.)

## 4. O que a vuln NÃO é

O exploit é só um valor num parâmetro, então é fácil tirar a lição errada. Isole a causa real:

- **NÃO é XSS.** Nada é injetado numa página e nenhum script roda; o servidor só emite um header `Location` num `302`. Não há sink de HTML/JS aqui — só um redirect.
- **NÃO é CSRF.** Nenhuma ação de mudança-de-estado acontece no alvo, e nenhum cookie está envolvido (este login não guarda sessão nenhuma — o redirect dispara igual com ou sem uma). Onde o `csrf-basic` faz o alvo *agir* em nome da vítima usando o cookie que o browser anexa sozinho, um open redirect faz o alvo *mandar a vítima embora* e não toca em nada no alvo. "Cross-site" aqui quer dizer que o destino é outro site, não que algo rodou no alvo.
- **NÃO é um redirect legítimo.** Um `next` real de login é sempre um path interno — a app não tem motivo de te mandar pra outro host. **Prova de isolamento:** `next=/dashboard` volta `Location: /dashboard` nas **duas** apps, vulnerable e fixed (Passo 1). Só o destino *externo* as separa.

A única coisa que a vuln **é**: o servidor confia num destino controlado pelo usuário e o emite como o `Location`, mandando a vítima pra fora. O único fix é deixar o **servidor** decidir o destino — aceitar só um path interno.

## 5. Impacto

**Sozinho, baixo; como elo de uma corrente, real.** Um open redirect não vaza dado, não roda código e não muda nada no alvo — por si só ele só relocaliza o browser. Seu valor pro atacante é credibilidade e encadeamento:

- **Phishing.** O link malicioso *começa* no domínio confiável (`http://127.0.0.1:8024/login?next=...`); a vítima confere esse domínio, loga de verdade, e só então é jogada pra uma página look-alike do atacante pronta pra colher o que vier a seguir. A origem confiável empresta credibilidade à isca inteira.
- **Roubo de token em OAuth / SSO.** Quando um destino de redirect (um `redirect_uri` ou um retorno pós-login) é mal-validado, um open redirect pode desviar um authorization code ou token pro destino do atacante.

Este átomo prova o redirect pra fora; a escalada acima é o alcance real da classe — descrita aqui, não construída. Sem overclaim.

## 6. Por que o fix funciona

Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança. A app fixed passa o `next` por `safe_next()`, que aceita só um path interno (sem scheme, sem host, sem protocol-relative `//`, sem truque de `\`) e cai em `/dashboard` caso contrário. Repita o ataque contra <http://127.0.0.1:8124/login>:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8124
Content-Type: application/x-www-form-urlencoded
Content-Length: 52

username=demo&password=demo&next=http://evil.example
```

Resposta:

```
HTTP/1.1 302 FOUND
Content-Length: 207
Location: /dashboard
```

O destino externo é recusado e substituído pelo default interno seguro — `Location: /dashboard`, não `http://evil.example`. O payload `//evil.example` é barrado do mesmo jeito (também volta `Location: /dashboard`), porque a checagem estrutural rejeita qualquer destino carregando um host, não só os escritos `http://`. Enquanto isso o `next=/dashboard` legítimo ainda volta `Location: /dashboard` nas duas apps, então a feature está intacta; só os destinos pra fora mudam. O fix inteiro é o servidor decidir o destino — uma allowlist de estrutura (isto é um path interno?), não um blocklist de strings. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra por que um blocklist perde e por que um path interno basta aqui.
