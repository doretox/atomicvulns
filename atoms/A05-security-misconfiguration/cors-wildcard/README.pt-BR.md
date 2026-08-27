# cors-wildcard — Cross-origin resource sharing (CORS) misconfiguration

> ⚠️ Intencionalmente vulnerável. Rode apenas localmente. Nunca exponha à internet ou a uma rede compartilhada.

Um laboratório mínimo pra um erro que está em todo canto de API: uma política de **CORS** que entrega a resposta pra *qualquer* site, com os cookies da vítima anexados. A origem-vítima é uma API JSON minúscula — você loga, recebe um cookie de sessão, e `GET /account` devolve os dados privados da sua conta enquanto você tiver o cookie. Esse endpoint está **correto**: ele exige o cookie e devolve o dado a quem é dono dele. A falha é uma *política* de resposta em volta dele.

Pra ver por que isso importa, você precisa de uma regra do navegador. Uma **origem** (origin) é a tripla esquema + host + porta (`http://victim.localhost:8034`). A **Same-Origin Policy (SOP)** é a regra que deixa um script de uma origem *disparar* uma requisição a outra origem, mas o **proíbe de LER** a resposta — é o que impede um script de `evil.com` de chamar `bank.com` (onde você está logado) e ler a página da sua conta. **CORS (Cross-Origin Resource Sharing)** é como um servidor pode relaxar isso de propósito, por cabeçalhos de resposta: `Access-Control-Allow-Origin` nomeia qual origem pode ler a resposta, e `Access-Control-Allow-Credentials: true` acrescenta "…inclusive quando a requisição levou os cookies da vítima". Esses cabeçalhos são uma *instrução ao navegador*, não uma tranca no servidor — o servidor sempre devolve o corpo; o CORS só diz ao navegador se ele pode entregar esse corpo ao script que fez a chamada.

Esta vítima erra a política do jeito mais comum: ela lê o cabeçalho `Origin` do request e o **reflete de volta** em `Access-Control-Allow-Origin`, junto com `Access-Control-Allow-Credentials: true`. Ou seja, responde "sim, você pode ler isto, com os cookies da vítima" pra *qualquer origem que perguntar* — inclusive a do atacante. Uma vítima que está logada e então visita a página do atacante tem o navegador fazendo um `fetch` cross-origin **credenciado** (`credentials: 'include'`) a `/account`; o navegador anexa o cookie da vítima, o servidor responde com a política refletida, e o navegador entrega a resposta privada ao script do atacante. Roubo de dados cross-origin — e o atacante nunca soube a senha nem tocou no cookie.

O slug diz "wildcard", mas o `Access-Control-Allow-Origin: *` literal é uma pista falsa aqui: o navegador **RECUSA** expor uma resposta credenciada quando o cabeçalho é `*`, então o `*` vaza só dado público. O vetor que alcança dado *autenticado* é a **reflexão da origem** — ecoar uma origem específica, que o navegador *aceita* junto com credenciais. Então o fix não é "refletir uma origem" (refletir *é* o bug) nem o wildcard — é uma **allowlist de correspondência exata** de origens em que você realmente confia (ou nenhum cabeçalho CORS, se o endpoint não tem consumidor cross-origin).

> **Teoria primeiro:** Leia [PortSwigger: Cross-origin resource sharing (CORS)](https://portswigger.net/web-security/cors)
> antes de fazer este átomo — ela cobre a reflexão do cabeçalho `Origin` em
> `Access-Control-Allow-Origin` e o papel do `Access-Control-Allow-Credentials`,
> que é exatamente esta falha. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

Este átomo fica em **A05 — Security Misconfiguration**, ao lado dos irmãos [`xxe-basic`](../xxe-basic/), [`xxe-blind-oob`](../xxe-blind-oob/) e [`debug-enabled`](../debug-enabled/). O contraste é o ponto: os átomos de XXE são um *parser XML* mal configurado e o `debug-enabled` é um *framework/deploy* mal configurado; este é uma *política de resposta HTTP* mal configurada. E ele é a imagem espelhada do [`csrf-basic`](../../A01-broken-access-control/csrf-basic/): os dois quebram a Same-Origin Policy na fronteira de origem, mas em direções opostas. O CSRF quebra o lado do **envio** — faz o navegador da vítima *disparar* uma requisição de mudança-de-estado que o atacante não consegue ler (uma escrita cega). Este quebra o lado da **leitura** — deixa o atacante *ler* uma resposta autenticada que a SOP deveria ter escondido (exfiltração). Enviar versus ler: as duas metades da SOP.

## Nota de stack — duas origens, dirigido pelo browser, sem link server-to-server

Duas origens, três serviços: a **vítima** (uma cópia `vulnerable` e uma `fixed`) e a página do **atacante**. Elas nunca conversam entre si no backend — o navegador da vítima faz toda requisição cross-origin — então não há rede interna, nem `depends_on`, nem healthcheck. Hostnames distintos dão origens genuinamente distintas: a vítima é `victim.localhost` (`:8034` vulnerable, `:8134` fixed) e o atacante é `attacker.localhost` (`:8234`). Todos resolvem pra `127.0.0.1` (os navegadores mapeiam `*.localhost` pra loopback), então os bindings do Docker ficam em `127.0.0.1` — local-only — enquanto o navegador ainda vê três sites separados. O cookie de sessão da vítima é `SameSite=None; Secure` pra o navegador anexá-lo no fetch credenciado cross-origin do atacante; `Secure` funciona sobre HTTP puro porque `*.localhost` é um *secure context* (loopback). `vulnerable` e `fixed` dividem o host `victim.localhost`, então usam nomes de cookie distintos (`session_vuln` / `session_fixed`) pra manter os logins separados, já que cookie ignora a porta — plumbing, não uma diferença de segurança.

## O browser é a prova — e o `curl` não é

Você dirige este átomo por um **navegador** (com o Burp como lente de apoio), porque CORS é imposto pelo *navegador*, não pelo servidor. Aponte `curl` ou o Burp Repeater pra `/account` e você lê o corpo privado toda vez — até no app corrigido — porque eles não são navegadores e simplesmente ignoram os cabeçalhos CORS. Isso não é o exploit; é só o **tell**. O Burp ainda é útil: mande `/account` com um cabeçalho `Origin:` e você vê o app vulnerável *refletir* a origem de volta com `Access-Control-Allow-Credentials: true` — a assinatura da má config. Mas o impacto — um script de outra origem de fato *lendo* o dado da vítima — só reproduz num navegador de verdade, que é onde o walkthrough roda.

## Como rodar

Da raiz do repo:

```bash
./atom up cors-wildcard
```

- API vítima vulnerável: `http://victim.localhost:8034` (bindada em `127.0.0.1:8034`)
- API vítima corrigida: `http://victim.localhost:8134` (bindada em `127.0.0.1:8134`)
- Página do atacante: `http://attacker.localhost:8234` (bindada em `127.0.0.1:8234`)

Use os hostnames `*.localhost` no navegador (não as portas cruas em `127.0.0.1`) — os hostnames distintos são o que torna as origens cross-origin. Pare com `./atom down cors-wildcard`. Se preferir Docker cru: `cd atoms/A05-security-misconfiguration/cors-wildcard && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — passo a passo: logar como a vítima, ver o app vulnerável refletir a origem do atacante no Burp, e então abrir a página do atacante no navegador e ver o script dela ler os dados privados da conta da vítima cross-origin. Depois, a mesma página contra o app corrigido é bloqueada pelo navegador com um erro de CORS.
2. [`DIFF.md`](./DIFF.md) — o diff de uma-política entre `vulnerable/` e `fixed/`, e por que "checar se a `Origin` termina com o nosso domínio", "só tirar as credenciais" e "usar `*`" não são o fix.

## Versão corrigida

A API corrigida na porta 8134 troca a reflexão da origem por uma **allowlist de correspondência exata**: ela ecoa `Access-Control-Allow-Origin` só quando a `Origin` do request é exatamente uma das origens em que confia (um parceiro legítimo, aqui um stand-in). Uma origem não-confiável — a do atacante — não recebe cabeçalho CORS nenhum, então o navegador bloqueia a leitura cross-origin e o script do atacante vê um erro de CORS, não o dado. `GET /account` continua devolvendo o mesmo dado à vítima logada, e a requisição ainda chega ao servidor com o cookie anexado — o navegador só se recusa a entregar a resposta a um script de uma origem que o servidor não autorizou. Veja o [`DIFF.md`](./DIFF.md) pra entender por que o fix é uma allowlist, e não refletir uma origem "específica", tirar as credenciais, ou o wildcard.
