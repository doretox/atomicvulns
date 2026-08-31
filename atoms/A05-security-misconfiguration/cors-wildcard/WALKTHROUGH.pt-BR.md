# Walkthrough — cors-wildcard

O alvo é uma API pequena. Você loga pelo portal dela, o servidor seta um **cookie de sessão**, e `GET /account` devolve os dados privados da sua conta enquanto o navegador mandar esse cookie. O endpoint está correto — ele exige o cookie e devolve o dado ao dono. A falha é a política de **CORS** em volta dele: o servidor lê o cabeçalho `Origin` do request e o reflete de volta em `Access-Control-Allow-Origin`, junto com `Access-Control-Allow-Credentials: true`. Isso diz ao navegador "qualquer origem pode ler esta resposta, com os cookies da vítima". Então uma página num **subdomínio irmão hostil** — `evil.lab.localhost`, um subdomínio comprometido ou vítima de takeover do próprio site da vítima — pode fazer o navegador da vítima buscar `/account` com o cookie da vítima anexado e *ler* a resposta privada. A vítima nunca aprovou; o atacante nunca soube a senha nem tocou no cookie.

## 1. Contexto

`GET /account` devolve dado que pertence a um usuário logado. Pra ver o que dá errado, você precisa de uma regra do navegador e do mecanismo que a relaxa.

Uma **origem** (origin) é a tripla **esquema + host + porta** — `http://api.lab.localhost:8034` e `http://evil.lab.localhost:8234` são origens diferentes (host e porta diferentes). Duas origens são **same-site** quando compartilham o mesmo domínio registrável (aqui `lab.localhost`) mesmo com subdomínio diferente, e **cross-origin** sempre que o esquema, host, *ou* porta diferem. Então `api.lab.localhost` e `evil.lab.localhost` são **cross-origin** (host diferente) mas **same-site** (ambos sob `lab.localhost`) — guarde isso; é por que o ataque funciona num navegador moderno (abaixo).

A **Same-Origin Policy (SOP)** é a regra do navegador que deixa um script de uma origem *disparar* uma requisição a outra origem, mas o proíbe de *ler* a resposta. É o que impede um script de `evil.com` de chamar `bank.com`, onde você está logado, e ler a página da sua conta. (A outra metade dela — *enviar* uma requisição cross-origin que você não consegue ler — é o que o [`csrf-basic`](../../A01-broken-access-control/csrf-basic/) abusa. Este átomo é a metade da leitura.)

**CORS (Cross-Origin Resource Sharing)** é como um servidor relaxa a SOP de propósito pra que origens escolhidas *possam* ler suas respostas. Funciona por **cabeçalhos de resposta**, e é uma instrução ao *navegador*, não uma tranca no servidor: o servidor sempre devolve o corpo; o CORS só diz ao navegador se ele pode entregar esse corpo ao script que chamou. Dois cabeçalhos importam aqui:

- **`Access-Control-Allow-Origin`** (ACAO) — nomeia qual origem pode ler a resposta. Pode ser uma origem específica, ou o wildcard `*` ("qualquer origem").
- **`Access-Control-Allow-Credentials: true`** (ACAC) — acrescenta "…inclusive quando a requisição levou credenciais", ou seja, os cookies da vítima. Sem ele, o navegador bloqueia o script de ler a resposta de uma **requisição credenciada** — um `fetch(url, { credentials: 'include' })`, que diz ao navegador pra anexar os cookies do alvo numa chamada cross-origin.

Mais um termo pra depois: um **preflight** é uma requisição `OPTIONS` extra que o navegador manda *antes* de certas requisições cross-origin "não-simples" (métodos ou cabeçalhos custom) pra pedir permissão. Um `GET` puro sem cabeçalhos custom — como o que este ataque usa — é uma "simple request" e **não** dispara preflight; o navegador manda direto e então checa o ACAO/ACAC da resposta antes de expô-la.

**Por que um subdomínio irmão, e não `evil.com`.** Os navegadores atuais agora **particionam cookies de 3ª parte por site de topo** — a Total Cookie Protection do Firefox é padrão, e os cookies de 3ª parte estão sendo removidos no resto. Uma leitura *puramente* cross-site (`evil.com` buscando `bank.com`) já não leva o cookie da vítima, então falharia antes mesmo de o CORS importar. Enquadrar o atacante como um **irmão same-site** (`evil.lab.localhost` vs `api.lab.localhost`) mantém o cookie viajando — a requisição ainda é cross-*origin*, então o CORS ainda decide a leitura — o que isola a lição na política de CORS e faz o exploit reproduzir nos navegadores de hoje, Firefox incluído.

Três serviços, nenhum conversando com o outro no backend — o navegador da vítima faz toda requisição cross-origin:

- vítima `vulnerable` — `http://api.lab.localhost:8034/`
- vítima `fixed` — `http://api.lab.localhost:8134/`
- página do `attacker` — `http://evil.lab.localhost:8234/` (um **irmão** hostil da vítima)

Como o CORS é imposto pelo navegador, é lá que você explora; o Burp é uma lente de apoio que mostra a má config na rede.

## 2. Achar o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). `GET /account` é comum e correto:

```python
@app.route("/account")
def account():
    if "user" not in session:
        return jsonify({"error": "not logged in"}), 403
    return jsonify(ACCOUNT)
```

Ele exige o cookie de sessão e devolve o dado. O bug é a política anexada a *toda* resposta:

```python
@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin        # reflection: the bug
        resp.headers["Access-Control-Allow-Credentials"] = "true"   # ...with the victim's cookies
    return resp
```

Pergunta de auditoria: *o servidor nomeia qual origem pode ler a resposta — como ele decide?* Ele não decide. Ele ecoa de volta **qualquer `Origin` que o request mandou**, e acrescenta `Access-Control-Allow-Credentials: true`. Isso é "sim, você pode ler isto, com os cookies da vítima" pra *qualquer* origem que perguntar — inclusive um subdomínio irmão que foi comprometido. (O fix, prenunciado: decidir com uma allowlist de correspondência exata, não com um espelho.)

## 3. O tell — a origem refletida (no Burp)

Antes de tocar no navegador, confirme a má config na rede. Passe o navegador pelo Burp, logue uma vez em `http://api.lab.localhost:8034/`, e mande o request `GET /account` pro **Repeater**. Acrescente um cabeçalho — a origem do irmão atacante — e reenvie:

```
GET /account HTTP/1.1
Host: api.lab.localhost:8034
Origin: http://evil.lab.localhost:8234
Cookie: session_vuln=eyJ1c2VyIjoiZGVtbyJ9...

HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://evil.lab.localhost:8234
Access-Control-Allow-Credentials: true
Content-Type: application/json

{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

A resposta reflete a origem exata que você mandou — `Access-Control-Allow-Origin: http://evil.lab.localhost:8234` — e acrescenta `Access-Control-Allow-Credentials: true`. Troque a `Origin` por qualquer outra e ela espelha essa também: o servidor aprova *toda* origem. Esse é o tell. (O mesmo request pela linha de comando, se preferir: `curl -i -H "Origin: http://evil.lab.localhost:8234" -H "Cookie: session_vuln=..." http://api.lab.localhost:8034/account`.)

**Mas o tell não é a prova, e eis por quê.** Olhe de novo: o Repeater imprimiu o corpo privado. O `curl` também imprimiria. Eles leem `/account` independente de qualquer cabeçalho CORS — porque não são navegadores e simplesmente ignoram o CORS. CORS é uma regra que o *navegador* impõe sobre scripts; não é um controle de acesso no servidor. Reenviar o request no Repeater com um cookie que você tem não é o exploit — não há vítima, não há script cross-origin sendo liberado ou negado. A vulnerabilidade é que um **navegador** vai entregar esta resposta a um **script de outra origem**, e isso só reproduz num navegador.

## 4. Exploração (no navegador)

O exploit precisa de uma vítima logada cujo navegador então visita a página do irmão. Dirija um navegador de verdade (passando pelo Burp se quiser ver o tráfego).

### Logar a vítima

Navegue pro portal da vítima em `http://api.lab.localhost:8034/`. É uma página HTML pequena — um banner de aviso e dois botões. Clique em **Log in (demo)**: a página dispara um `fetch('/login', …)` in-page e mostra

```
Logged in. Now click “View my account”.
```

O servidor setou `Set-Cookie: session_vuln=...; Secure; HttpOnly; Path=/; SameSite=None`, então o seu navegador agora guarda o cookie de sessão da vítima pra `api.lab.localhost`. `SameSite=None` é o que deixa o navegador anexá-lo numa requisição cross-origin depois; `Secure` é aceito sobre HTTP puro porque `*.lab.localhost` é um *secure context*. Clique em **View my account** — a página busca `/account` same-origin e mostra o seu dado privado:

```
{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

Este é o uso comum e pretendido: você, na própria origem da vítima, lendo a sua própria conta.

### Visitar a página do irmão

Agora, ainda logado, navegue pro irmão atacante em `http://evil.lab.localhost:8234/attack-vuln`. O único conteúdo dele é um script que faz o fetch credenciado cross-origin:

```js
fetch("http://api.lab.localhost:8034/account", { credentials: "include" })
  .then(r => r.text())
  .then(body => { document.getElementById("loot").textContent = body; })
  .catch(e => { document.getElementById("loot").textContent = "CORS error: " + e; });
```

A página renderiza o dado privado da vítima — lido de outra origem:

```
Data read cross-origin from http://api.lab.localhost:8034/account:
{"balance":"USD 42,000.00","email":"demo@example.com","user":"demo"}
```

Esse é o ataque. O navegador da vítima anexou o cookie de `api.lab.localhost` na requisição cross-origin (`credentials: 'include'`, e o cookie *não* foi removido porque os dois são same-site), o servidor devolveu o dado privado com a política de CORS refletida, e o navegador — obedecendo essa política — entregou a resposta ao script do **irmão**. Um subdomínio comprometido leu o saldo da conta e o e-mail de recuperação da vítima sem nunca saber a senha nem ler o cookie.

Tudo aqui é benigno e local: uma conta fake com saldo dummy, tudo em loopback, nada destrutivo.

## 5. O que a vuln NÃO é

A requisição a `/account` parece legítima, então isole o que de fato deu errado:

- **NÃO é falta de autenticação.** O endpoint exige o cookie e o checa — a leitura same-origin da própria vítima na Seção 4 prova que a auth funciona. O que a falha expõe é a *leitura da resposta* por outra origem. Prova de isolamento: logue no app corrigido (`:8134`) e leia `/account` same-origin e você recebe o dado idêntico — só a leitura *cross-origin* difere entre os dois apps.
- **NÃO é CSRF.** O [`csrf-basic`](../../A01-broken-access-control/csrf-basic/) faz o navegador *enviar* uma requisição de mudança-de-estado que o atacante não consegue ler — uma escrita cega. Aqui o atacante *lê* dado autenticado. Direções opostas na mesma Same-Origin Policy: enviar versus ler.
- **NÃO é "o `*` é o perigo".** O `Access-Control-Allow-Origin: *` literal **não** funciona pro roubo autenticado — o navegador recusa expor uma resposta credenciada quando o cabeçalho é `*`, então o `*` vaza só dado público. O vetor é a **reflexão da origem**: ecoar uma origem *específica*, que o navegador aceita junto com credenciais. A reflexão existe justamente pra contornar a recusa de `*`-com-credenciais.
- **NÃO é injection nem um bug no código do endpoint.** `/account` está logicamente correto — autentica e devolve o dado certo. A falha é a **política** de CORS (uma configuração), que é por que isto é **A05 — Security Misconfiguration**, não um bug de lógica de aplicação.
- **NÃO é um vazamento server-side.** `curl` e Burp leem a resposta de qualquer jeito (Seção 3) — o CORS nunca os para. O que a má config quebra é a proteção que o *navegador* teria dado à vítima: recusar entregar uma resposta cross-origin a um script hostil.

O que **é**: o servidor instrui o navegador (pelos cabeçalhos CORS refletidos) a deixar *qualquer* origem ler a resposta autenticada, então um script num subdomínio irmão hostil lê o dado privado da vítima. O fix é uma allowlist de correspondência exata de origens em que o servidor realmente confia.

## 6. Impacto

**Exfiltração cross-origin de dado autenticado.** Qualquer origem que a vítima visita enquanto logada pode ler o que `/account` devolver — aqui o saldo da conta e o e-mail de recuperação; no mundo real, qualquer endpoint privado com essa política (perfil, mensagens, tokens, chaves). O cenário realista é o modelado aqui: um **subdomínio irmão hostil** — um subdomínio da mesma organização que foi comprometido, deixado rodando como staging esquecido, ou tomado por um subdomain takeover — transformando uma política de CORS "confie nos nossos próprios domínios" ampla demais num vazamento de dados. Isso é clássico em relatórios de bug bounty. Sem overclaim: isto é uma **leitura**, não uma escrita — o atacante não consegue *mudar* a conta (essa é a outra metade da SOP, o lado da escrita que o `csrf-basic` cobre), e não é execução de código no servidor. O teto é exatamente o que o endpoint autenticado devolve.

## 7. Por que o fix funciona

Aponte a página do atacante pra vítima corrigida: com uma sessão estabelecida em `http://api.lab.localhost:8134/` do mesmo jeito da Seção 4 (o cookie dela é `session_fixed`), navegue pra `http://evil.lab.localhost:8234/attack-fixed`. A página mostra:

```
Data read cross-origin from http://api.lab.localhost:8134/account:
CORS error: TypeError: Failed to fetch
```

e o console do navegador explica por quê:

```
Access to fetch at 'http://api.lab.localhost:8134/account' from origin
'http://evil.lab.localhost:8234' has been blocked by CORS policy: No
'Access-Control-Allow-Origin' header is present on the requested resource.
```

O script do atacante recebeu **nada**. Olhe de perto o que aconteceu, porque é o cerne: a requisição **ainda chegou ao servidor**. A vítima corrigida logou `GET /account HTTP/1.1" 200` e devolveu o dado privado — o navegador tinha anexado o cookie `session_fixed` (same-site, como antes) e o servidor respondeu exatamente como antes. O que mudou é que a resposta não trouxe **nenhum `Access-Control-Allow-Origin` pra origem do atacante**, então o navegador se recusou a entregar o corpo ao script. O cookie viajou junto e o servidor respondeu; o navegador bloqueou a *leitura*.

O app corrigido troca a reflexão por uma **allowlist de correspondência exata** ([`fixed/app.py`](./fixed/app.py)):

```python
ALLOWED_ORIGINS = {"http://partner.lab.localhost:9000"}

@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp
```

O fix **não** é "apagar o CORS": um *irmão* legítimo — `partner.lab.localhost` — ainda precisa ler esta API, e ainda pode. Essa é a lição afiada: **nem todo subdomínio irmão é confiável; você nomeia os exatos, não reflete a família inteira.** Confirme com o tell — o parceiro da allowlist é refletido, o irmão hostil não:

```
$ curl -s -D - -o /dev/null -H "Origin: http://partner.lab.localhost:9000" http://api.lab.localhost:8134/account
Access-Control-Allow-Origin: http://partner.lab.localhost:9000
Access-Control-Allow-Credentials: true

$ curl -s -D - -o /dev/null -H "Origin: http://evil.lab.localhost:8234" http://api.lab.localhost:8134/account
HTTP/1.1 403 FORBIDDEN
        # nenhum Access-Control-Allow-Origin — o navegador bloqueia a leitura do irmão
```

Note o que **não** mudou: o cookie de sessão é `SameSite=None; Secure` nos dois apps, e `/account` é byte-a-byte idêntico. A política de CORS é a *única* diferença de segurança — o que isola que o fix é a allowlist, não algo sobre o endpoint ou o cookie. Veja o [`DIFF.md`](./DIFF.md) pra mudança de uma-política e por que "confiar na nossa própria família de subdomínios", "só tirar as credenciais" e "usar `*`" não são o fix.
