# DIFF — vulnerable vs. fixed

O fix é uma coisa só: trocar a **reflexão da origem** por uma **allowlist de correspondência exata**. O app vulnerável ecoa de volta qualquer `Origin` que o request mandou; o app corrigido seta `Access-Control-Allow-Origin` só quando a origem do request é exatamente uma em que ele confia. Todo o resto é inalterado — `GET /account`, `POST /login`, os dados da conta, e a config do cookie de sessão (`SameSite=None; Secure`) são todos idênticos — então a política de CORS é a *única* diferença de segurança entre os dois apps.

## A mudança — `app.py`

```diff
+ALLOWED_ORIGINS = {"http://partner.localhost:9000"}
+
 @app.after_request
 def add_cors(resp):
     origin = request.headers.get("Origin")
-    if origin:
-        resp.headers["Access-Control-Allow-Origin"] = origin        # reflect ANY origin
-        resp.headers["Access-Control-Allow-Credentials"] = "true"
+    if origin in ALLOWED_ORIGINS:                                   # exact match only
+        resp.headers["Access-Control-Allow-Origin"] = origin
+        resp.headers["Access-Control-Allow-Credentials"] = "true"
     return resp
```

`SESSION_COOKIE_NAME` também difere (`session_vuln` vs `session_fixed`) por um motivo não-relacionado à segurança: as duas vítimas moram em `victim.localhost`, e cookie ignora a porta, então um nome de cookie único seria compartilhado entre `:8034` e `:8134`. Nomes distintos mantêm os dois logins separados. Os dois atributos de cookie relevantes pra segurança — `SESSION_COOKIE_SAMESITE="None"` e `SESSION_COOKIE_SECURE=True` — são idênticos nos dois lados, e `GET /account`, `POST /login`, os imports, os dados da conta, o `Dockerfile` e o `requirements.txt` são byte-a-byte idênticos.

## Por que isto corrige o bug

A política vulnerável respondia "sim, você pode ler esta resposta, com os cookies da vítima" pra *qualquer origem que perguntasse*, porque espelhava a `Origin` do request em `Access-Control-Allow-Origin`. A política corrigida responde isso só pra uma origem que ela foi instruída a confiar. Quando a origem do atacante (`http://attacker.localhost:8234`) não está em `ALLOWED_ORIGINS`, a resposta não traz **nenhum cabeçalho `Access-Control-Allow-Origin`**, e o navegador se recusa a entregar a resposta ao script do atacante.

O ponto a guardar: a requisição ainda chega ao servidor. No app corrigido o fetch credenciado ainda chega com o cookie da vítima, e o servidor ainda devolve o dado privado (`200`). O que o navegador se recusa a fazer é *ler* essa resposta em nome de um script de uma origem que o servidor não autorizou. A defesa não é parar a requisição — é declinar de *autorizar a leitura*, nomeando exatamente quem pode fazê-la.

## A reflexão é a causa — não "faltou autenticação", não "dado sensível"

A leitura errada mais comum é que o endpoint "esqueceu de autenticar". Não esqueceu: `GET /account` exige o cookie de sessão e devolve o dado só a um usuário logado — a leitura same-origin da própria vítima prova que a auth funciona. Também não é que o dado seja "sensível demais pra devolver" — o endpoint *deve* devolvê-lo, ao dono. A falha é a *política* de resposta que diz ao navegador pra deixar **qualquer origem** ler essa resposta, cookies e tudo. Prova de isolamento: leia `/account` same-origin nos dois apps e você recebe o dado idêntico; só a leitura *cross-origin* difere — o app vulnerável a entrega ao script do atacante, o corrigido não. A causa é a política de CORS, nada mais.

## Armadilha: "só checar se a `Origin` termina com o nosso domínio"

Um meio-fix tentador é validar a origem de forma frouxa — aceitar qualquer coisa que *contenha* ou *termine com* o seu domínio:

```python
# AINDA VULNERÁVEL -- não faça isto
if origin and origin.endswith("partner.localhost:9000"):
    resp.headers["Access-Control-Allow-Origin"] = origin
```

Checagens de substring e sufixo são contornáveis. `http://evil-partner.localhost:9000` **termina com** `partner.localhost:9000`; `http://partner.localhost:9000.evil.example` **contém** o valor. Um atacante que controle uma dessas origens passa na checagem e ganha o cabeçalho refletido. O teste tem que ser uma **correspondência exata** contra um conjunto de origens completas (`origin in ALLOWED_ORIGINS`), não uma comparação frouxa de string.

## Armadilha: "só tirar as credenciais"

Outro fix parcial é continuar refletindo a origem mas parar de mandar `Access-Control-Allow-Credentials: true`. Isso é uma melhora, e vale ser preciso: sem esse cabeçalho o navegador **não** expõe uma resposta *credenciada* a um script cross-origin, então o roubo *autenticado* deste átomo para — o cookie não compra mais a resposta pro atacante. Mas você continua refletindo toda origem, então qualquer dado **público** (não-autenticado) que o endpoint devolva ainda vaza pra qualquer site. Trata o sintoma (leituras credenciadas) e deixa a raiz — refletir qualquer origem — no lugar. O fix de raiz é a allowlist.

## O wildcard `*` não é o vetor

O slug é `cors-wildcard`, e o instinto é que o perigo é `Access-Control-Allow-Origin: *`. Mas o `*` literal **não** funciona pro roubo autenticado: o navegador recusa expor uma resposta credenciada quando o cabeçalho é `*`, então um `fetch(..., {credentials:'include'})` contra uma política `*` falha em ler o corpo. O `*` vaza só dado *público*. Essa recusa é justamente *por que* a reflexão da origem existe — ecoar uma origem **específica** produz um cabeçalho que o navegador *aceita* junto com credenciais. Então "só usar `*`" nem é um ataque que funciona pra dado autenticado, e entender isso é o que aponta pro vetor real: a reflexão.

## Não adicione CORS que você não precisa — o fix de superfície honesto

Existe um fix mais simples que uma allowlist, quando ele se aplica: se um endpoint **não** tem consumidor cross-origin legítimo, ele deveria mandar **nenhum** cabeçalho CORS, e a SOP o protege de graça. Esse é um conselho genuinamente correto — não uma armadilha. Este átomo modela o outro caso, em que a API *tem* um parceiro cross-origin real (`ALLOWED_ORIGINS` é um stand-in dele), então remover o CORS por completo quebraria uma integração legítima. Aí o fix não é "apagar o CORS" e sim "configurar direito" — uma allowlist de correspondência exata nomeando as origens em que você realmente confia. Os dois estão certos; qual se aplica depende de o endpoint ser feito pra ser lido cross-origin ou não.

## O impacto é exfiltração — e é o espelho do CSRF

A política vulnerável deixa um script de outra origem **ler** a resposta autenticada da vítima — exfiltração de dado cross-origin. Sem overclaim: é uma leitura, não uma escrita; o atacante não consegue mudar a conta, e não há execução de código. A classe que ela espelha é o CSRF — os dois quebram a Same-Origin Policy na fronteira de origem — então o contraste vale ser traçado com nitidez:

| | **CSRF** (`csrf-basic`) | **CORS misconfiguration** (este átomo) |
|---|---|---|
| Qual metade da SOP | o lado do **envio** — o navegador dispara uma requisição cross-site | o lado da **leitura** — o navegador expõe uma resposta cross-origin |
| O que o atacante consegue | **disparar** uma ação de mudança-de-estado, cego (não lê a resposta) | **ler** uma resposta autenticada (exfiltração) |
| O cookie da vítima | anexado automaticamente à requisição forjada (`SameSite=None`) | anexado ao `fetch` credenciado (`credentials:'include'`) |
| Causa-raiz | confia no cookie como prova de **intenção** | a política de CORS **reflete qualquer origem** com credenciais |
| Fix | token anti-CSRF por sessão (o atacante não consegue lê-lo) | **allowlist** de correspondência exata de origens confiáveis |
| Categoria OWASP | A01 — Broken Access Control | A05 — Security Misconfiguration |

A regra prática: **o CSRF dispara uma requisição de fora e é cego; uma CORS misconfiguration deixa código de fora ler a resposta.** Enviar versus ler — as duas metades da Same-Origin Policy, quebradas em direções opostas.
