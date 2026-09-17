# session-fixation — Session fixation

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para session fixation. A app tem um form de login e uma página protegida `/account`, e rastreia quem você é com uma sessão server-side: um `session_id` opaco viaja num cookie enquanto os dados da sessão ficam no servidor (o padrão clássico `PHPSESSID` / `JSESSIONID`). No login, a app vulnerable autentica *a sessão que você já tinha* sem emitir um `session_id` novo — então um id que existia **antes** do login (um que um atacante poderia ter plantado) passa a identificar uma sessão **autenticada**.

Este não é um bug input-driven — não tem payload pra construir. O atacante **dá** um session id pra vítima em vez de roubar um: ele pega um `session_id` anônimo do servidor, planta no navegador da vítima **antes** do login, deixa a vítima logar com **a própria** senha correta, e então cavalga aquela sessão agora autenticada com o id que ele já conhecia. Ele nunca descobre a senha. O bug inteiro é um único passo ausente: o servidor nunca **regenera** o session id quando o nível de privilégio muda de anônimo pra autenticado.

> **Teoria primeiro:** Leia [OWASP: Session fixation](https://owasp.org/www-community/attacks/Session_fixation)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a OWASP explica *o que* ela é
> e por que importa.

*Session fixation não tem uma página dedicada na PortSwigger Academy (o primer padrão usado nesta série de átomos), então este aponta pra OWASP, que a cobre conceitualmente.*

## Fixation não é hijacking

Mantenha a distinção clara, porque ela *é* a lição. **Hijacking rouba um session id já autenticado** — depois do login, via sniffing, XSS, malware. **Fixation planta um id antes do login** e deixa a vítima autenticá-lo. Direção diferente (o atacante *dá*, não subtrai) e timing diferente (antes, não depois). O atacante nunca lê o cookie autenticado da vítima — ele teve o id desde antes de ela logar. Defesas contra roubo de cookie (`HttpOnly`, `Secure`) portanto **não** consertam fixation; o fix é regenerar o id no login. Ver [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).

## Nota de stack — sem banco

As sessões vivem num dict Python simples (`SESSIONS = {session_id: {...}}`), não num banco — session fixation é sobre o *ciclo de vida* da sessão, não sobre a camada de storage. E, crucialmente, a app **não** usa o `session` nativo do Flask: aquele é um cookie assinado client-side, sem id server-side pra fixar, e regenera por design — então fixation não vive lá. Este lab modela o padrão de sessão server-side (um id opaco no cookie) onde session fixation de fato acontece. Ver [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra por que a escolha de mecanismo importa.

## Autenticação simulada

Autenticação de verdade (password hashing, rate limiting, MFA) está fora do escopo — ensinaria outra lição. Uma credencial no seed, checada com comparação direta de string:

- `alice` / `password123`

A senha é deliberadamente trivial: não é o objeto de estudo. A *única* coisa que difere entre a app vulnerable e a fixed é o que acontece com o `session_id` no login — nada sobre a senha ou o check de login.

As páginas imprimem o `session_id` atual na tela. Apps reais não fazem isso; ele aparece aqui só pra você observar, num relance, se o id muda no login (não muda, na app vulnerable — esse é o bug). Num engagement real você o leria do cookie, no Burp ou no DevTools.

## Como rodar

Da raiz do repo:

```bash
./atom up session-fixation
```

- App vulnerable: <http://127.0.0.1:8015/>
- App fixed: <http://127.0.0.1:8115/>

Pare com `./atom down session-fixation`. Se preferir Docker cru: `cd atoms/A07-auth-failures/session-fixation && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8115 atende a mesma feature. Repita a cadeia de ataque do `WALKTHROUGH.pt-BR.md` contra ela: você ainda consegue pegar um `session_id` anônimo e logar com ele, mas no instante em que a vítima autentica, o servidor emite um id **novo** e descarta o antigo — então o id que você plantou nunca é autenticado, e replayá-lo contra `/account` retorna um redirect pra tela de login em vez da conta. A única mudança é essa regeneração no login.
