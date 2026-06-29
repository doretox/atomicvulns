# xss-stored — Stored Cross-Site Scripting

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para stored (persistent) XSS. Um guestbook salva o comentário de cada visitante no SQLite e renderiza todos os comentários salvos de volta para os visitantes seguintes através de um template Jinja que marca o body do comentário como `|safe`, desligando o autoescape que normalmente encodaria `<`, `>`, `&`, `'` e `"`. Um `<script>` plantado uma vez — por um visitante, num único `POST` — roda no browser de todo visitante que abrir a página depois, sem nenhum link para clicar e sem o atacante presente. Para tornar o impacto concreto, o `GET /` também seta um cookie `session` não-HttpOnly que o payload final do walkthrough exfiltra para um listener de uma linha.

> **Teoria primeiro:** Leia [PortSwigger: Stored cross-site scripting (XSS)](https://portswigger.net/web-security/cross-site-scripting/stored)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up xss-stored
```

- App vulnerable: <http://127.0.0.1:8008/>
- App fixed: <http://127.0.0.1:8108/>

Pare com `./atom down xss-stored`. Se preferir Docker cru: `cd atoms/A03-injection/xss-stored && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo: plantar o payload via Burp Suite (trilha principal), depois ver disparar no browser (obrigatório — o Burp não executa JavaScript).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8108 atende o mesmo guestbook contra os mesmos comentários de seed, e continua setando o mesmo cookie `session` — esse cookie nunca foi o bug. Ela larga o filter `|safe`, então o body do comentário passa pelo autoescape default do Jinja. Plante qualquer payload do `WALKTHROUGH.pt-BR.md` e recarregue: a página renderiza ele como texto literal (angle brackets visíveis na tela, nada executando), e o listener de exfiltração do cookie fica silencioso. Mesma root cause e mesmo fix de uma linha do [`xss-reflected`](../xss-reflected/) — só a entrega (persistida, vítima de terceiros) mudou.
