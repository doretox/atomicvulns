# jwt-none-alg — JWT alg=none signature bypass

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask pra o bug canônico de bypass de assinatura JWT. A app autentica com tokens assinados em HS256, mas o helper de decode tem um branch esquecido que aceita tokens cujo header `alg` é `"none"` — um formato de token sem assinatura definido pela própria spec do JWT pra cenários "sem necessidade de integridade". O atacante reescreve o header pra `alg=none`, flipa `role` pra `admin`, larga a signature, e o servidor lê as claims forjadas como autênticas.

Este é o primeiro átomo do projeto onde o bug é uma **falha de configuração criptográfica**, não de input nem de lógica. Nada da cryptography está quebrado — o servidor só escolheu, num branch, *não fazer* cryptography. A vulnerabilidade é o gap entre "parece um security boundary" e "é um security boundary".

> **Teoria primeiro:** Leia [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## API-only com uma página de contexto

A maioria dos bugs de JWT só faz sentido em contexto de API — não tem form pra preencher, não tem link pra clicar, só bytes que você monta e manda em `Authorization: Bearer ...`. Este átomo mantém essa forma. A home (`/`) existe só pra te entregar um token inicial (assinado pra o usuário seed `alice`, role `user`) pra você ter algo concreto pra inspecionar antes de forjar. A exploração real acontece contra `/admin` e `/me` no Burp Repeater. Não tem form de login — a cerimônia de autenticação está fora de escopo aqui, do mesmo jeito que estava em `idor-numeric-id`.

## Como rodar

Da raiz do repo:

```bash
./atom up jwt-none-alg
```

- App vulnerable: <http://127.0.0.1:8005/>
- App fixed: <http://127.0.0.1:8105/>

Pare com `./atom down jwt-none-alg`. Se preferir Docker cru: `cd atoms/A02-cryptographic-failures/jwt-none-alg && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal). Inclui um primer "Anatomy of a JWT" pra primeira vez que você decodar um na mão.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8105 mantém exatamente as mesmas rotas e exatamente o mesmo SECRET, então um token emitido pela vulnerable é aceito pela fixed e vice-versa — o que muda é quais tokens são rejeitados. Replique o token forjado com `alg=none` do `WALKTHROUGH.pt-BR.md` contra `GET /admin` na porta 8105: mesmos bytes, mesmo path, response é **401 Unauthorized** em vez do painel admin. O fix é uma linha de código.
