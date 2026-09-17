# xss-reflected — Reflected Cross-Site Scripting

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para reflected XSS clássico. Um endpoint de "busca de posts" ecoa o parâmetro `q` da query string de volta para a página de resposta através de um template Jinja que marca o valor como `|safe`, desligando o autoescape que normalmente encodaria `<`, `>`, `&`, `'` e `"`. Qualquer HTML ou `<script>` que o atacante mande em `q` roda no browser sob a origin da app.

> **Teoria primeiro:** Leia [PortSwigger: Reflected cross-site scripting (XSS)](https://portswigger.net/web-security/cross-site-scripting/reflected)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up xss-reflected
```

- App vulnerable: <http://127.0.0.1:8002/>
- App fixed: <http://127.0.0.1:8102/>

Pare com `./atom down xss-reflected`. Se preferir Docker cru: `cd atoms/A03-injection/xss-reflected && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8102 atende a mesma feature com os mesmos posts seed. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela — a página deve renderizar o payload como texto literal (angle brackets visíveis na tela, nada executando), nunca como HTML ou JavaScript vivo.
