# idor-numeric-id — Insecure Direct Object Reference (ID numérico)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para IDOR clássico. A app serve notas privadas via `GET /notes/<id>`. Um header simulado `X-User-ID` diz pra app qual usuário está "logado", mas a view nunca checa se a nota requisitada pertence a esse usuário — qualquer um consegue ler a nota de qualquer outro mudando um único dígito na URL.

Este é o primeiro átomo do projeto que **não é input-driven**. Não tem payload malicioso pra construir — o exploit é literalmente contar `1, 2, 3`. A vulnerabilidade vive em código que *não está lá* (o ownership check ausente), não em código que maltrata uma string.

> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — sem banco

Diferente do `sqli-union-basic`, este átomo guarda os dados numa lista Python simples em vez de SQLite. IDOR não depende da camada de storage: o bug é um check de autorização ausente acima de qualquer store que você use. A superfície é mantida mínima pra a linha que falta ficar óbvia. A escolha de storage em cada átomo segue a superfície do bug — não o contrário.

## Autenticação simulada

Autenticação de verdade (form de login, session, password hashing) está fora do escopo aqui — essa cerimônia cabe num átomo de autenticação dedicado. Este lab simula "quem está logado" com um único header: `X-User-ID`. Se ausente, a app default-a pra `1` (alice) pra a UI rodar sem você configurar nada. Três usuários no seed:

- `1` — alice — nota "Banking"
- `2` — bob — nota "Meeting"
- `3` — carol — nota "Card"

## Como rodar

Da raiz do repo:

```bash
./atom up idor-numeric-id
```

- App vulnerable: <http://127.0.0.1:8003/>
- App fixed: <http://127.0.0.1:8103/>

Pare com `./atom down idor-numeric-id`. Se preferir Docker cru: `cd atoms/A01-broken-access-control/idor-numeric-id && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8103 atende a mesma feature com as mesmas notas seed. Repita cada request do `WALKTHROUGH.pt-BR.md` contra ela — sua própria nota (`/notes/1` com `X-User-ID: 1`) retorna 200, mas qualquer combinação cross-user (ex: `/notes/2` autenticado como `1`) retorna **403 Forbidden** em vez de vazar conteúdo.
