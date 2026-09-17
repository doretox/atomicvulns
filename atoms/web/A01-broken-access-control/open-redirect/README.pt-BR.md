# open-redirect — Open Redirect

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para um Open Redirect clássico. A app tem um form de login com o padrão comum "te levar de volta pra onde você estava": o destino vem num parâmetro `next` (`/login?next=/dashboard`), e depois de um login bem-sucedido o servidor te redireciona pra lá — um `302` com `Location: <next>`. O bug é que ela redireciona pra *qualquer* destino que o `next` disser, sem checar que o destino é uma das próprias páginas dela. Um atacante monta um link que *parece* do alvo — `http://127.0.0.1:8024/login?next=http://evil.example` — a vítima confia no domínio do alvo, loga normalmente, e a app a joga pra fora, pro site do atacante. A prova está na resposta: o header `Location` do `302` aponta pra `evil.example`.

Isto é A01 — Broken Access Control (CWE-601, "URL Redirection to Untrusted Site"). O controle que falha é sobre *pra onde a app pode mandar o usuário*: ela deveria redirecionar só pra dentro de si mesma, mas entrega essa decisão ao input do usuário e manda a vítima pra fora. O fix é server-side e estrutural — o **servidor** decide o destino com uma allowlist. Um `next` legítimo de login é sempre um path interno, então `safe_next()` aceita só um path (sem scheme, sem host, sem protocol-relative `//host`, sem truque de `\`) e cai num destino interno seguro caso contrário. A única diferença entre `vulnerable/` e `fixed/` é essa checagem.

> **Teoria primeiro:** Leia [OWASP: Unvalidated Redirects and Forwards Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; o cheat sheet explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up open-redirect
```

- App vulnerable: <http://127.0.0.1:8024/>
- App fixed: <http://127.0.0.1:8124/>

Logue com `demo` / `demo`. Pare com `./atom down open-redirect`. Se preferir Docker cru: `cd atoms/A01-broken-access-control/open-redirect && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite. A prova é o header `Location` do `302` na resposta (Repeater, ou `curl -i` sem `-L`); não precisa de browser.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8124 atende o mesmo login e a mesma feature de `next`. Ela passa o `next` por `safe_next()` antes de redirecionar: um path interno como `/dashboard` ou `/settings` é honrado, mas qualquer coisa carregando um host — `http://evil.example`, o protocol-relative `//evil.example`, um backslash `/\evil.example`, ou um userinfo `https://demo@evil.example` — é recusada e cai em `/dashboard`. Rode cada payload do `WALKTHROUGH.pt-BR.md`: `next=/dashboard` ainda volta `Location: /dashboard` nas duas apps, mas os destinos externos que a app vulnerable emite verbatim agora voltam como `Location: /dashboard`. A única mudança em relação ao `vulnerable/` é essa checagem estrutural server-side; veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md). Isto é **A01 — Broken Access Control**: o servidor deixou o input do usuário escolher um destino que deveria ter restringido às próprias páginas.
