# sqli-blind-boolean — Blind SQL Injection (boolean-based)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para blind SQL injection booleana. Um endpoint de login concatena os campos `username` e `password` (vindos via POST) direto numa query SQL. O response body nunca devolve dado — só renderiza uma de duas páginas, `Welcome, <user>!` ou `Invalid credentials.` — mas essas duas mensagens formam um oráculo binário. Injetando condições que controlam esse oráculo, o atacante extrai dado um bit por vez, caractere por caractere, até recuperar a senha da alice (`wonderland`) sem ela jamais aparecer em nenhuma response.

> **Teoria primeiro:** Leia [PortSwigger: Blind SQL injection](https://portswigger.net/web-security/sql-injection/blind)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up sqli-blind-boolean
```

- App vulnerable: <http://127.0.0.1:8006/>
- App fixed: <http://127.0.0.1:8106/>

Pare com `./atom down sqli-blind-boolean`. Se preferir Docker cru: `cd atoms/A03-injection/sqli-blind-boolean && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8106 atende a mesma feature de login contra os mesmos usuários de seed. Ela continua retornando `Welcome, <user>!` para credencial correta e `Invalid credentials.` para qualquer outra coisa — essa assimetria é comportamento legítimo de login, não é o bug. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela: todos retornam `Invalid credentials.`, inclusive o login bypass do Step 1. O atacante perdeu o controle sobre o oráculo mesmo com o oráculo ainda existindo.
