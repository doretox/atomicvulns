# bola-rest — Broken Object Level Authorization (BOLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask, uma API REST, para BOLA (Broken Object Level Authorization) — o nome que o mundo de API security dá ao IDOR quando ele vive num endpoint REST, e o [API1:2023](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/), o risco #1 do OWASP API Security Top 10. A API serve registros de pedido via `GET /api/orders/<id>`. Todo request carrega um Bearer token opaco, e o endpoint até autentica ele — token inválido leva `401` — mas nunca checa se aquele pedido pertence ao caller. Então qualquer usuário logado lê o pedido de qualquer um só trocando o id no path. É exatamente o mesmo bug do `idor-numeric-id` e do `idor-uuid-guessable`: um object-level authorization check ausente.

A lição é que **estar autenticado não é estar autorizado**. Um token válido prova *quem você é*; não diz nada sobre se *este* objeto é seu. E onde os dois átomos irmãos de IDOR ensinaram que remodelar o id — um UUID, um valor aleatório — não é controle de acesso, este aqui fecha o arco: numa API REST o id é *público por design*. Ele está no path, é um inteiro sequencial, e o cliente recebe os próprios ids da `GET /api/orders`. Não há o que adivinhar nem o que reconstruir, então a object-level authorization é a única linha de defesa que poderia existir — e ela está ausente. O fix deixa o id sequencial intacto e adiciona uma linha: comparar o owner do pedido com o caller.

> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — sem banco

Como o `idor-numeric-id` e o `idor-uuid-guessable`, este átomo guarda os dados num dict Python simples em vez de um banco. BOLA não depende da camada de storage: o bug é um check de autorização ausente acima de qualquer store que você use. A superfície é mantida mínima pra a linha que falta ficar óbvia.

## API only — sem HTML, sem browser

Diferente dos átomos irmãos, este não tem UI web: sem templates, sem landing page, toda resposta é JSON. É proposital — BOLA vive em APIs REST, e este átomo modela uma. Você o opera inteiramente pelo **Burp Suite (Repeater)** ou por `curl`; não há trilha browser. O `WALKTHROUGH.pt-BR.md` trabalha exclusivamente no Burp.

## Autenticação simulada

Autenticação de verdade (senha, hashing, session de login) está fora do escopo aqui — isso cabe num átomo de autenticação dedicado. Este lab simula com `POST /login`, que recebe um nome de usuário e devolve um **Bearer token opaco**: um valor aleatório que o servidor guarda e resolve de volta pra um usuário (tipo um OAuth2 opaque access token ou uma session server-side — *não* um JWT). Dois usuários no seed:

- `mallory` — a atacante (você). Faz login como ela mesma e recebe o próprio token.
- `alice` — a vítima, cujo pedido é seedado no startup — o que você não deveria conseguir ler.

O token é genuíno e emitido pelo servidor, e o ataque nunca o inspeciona, decodifica ou forja — ele permanece válido o tempo todo. O que falta não é autenticação; é o object-level authorization check em cima dela.

## Como rodar

Da raiz do repo:

```bash
./atom up bola-rest
```

- API vulnerable: `http://127.0.0.1:8012`
- API fixed: `http://127.0.0.1:8112`

Não há landing page — o ponto de entrada é `POST /login` (veja o `WALKTHROUGH.pt-BR.md`). Pare com `./atom down bola-rest`. Se preferir Docker cru: `cd atoms/A01-broken-access-control/bola-rest && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8112 atende a mesma feature de pedidos. Ela adiciona uma linha — um object-level authorization check que retorna **404** a menos que o pedido pertença ao usuário do token que chamou — e não muda mais nada, mantendo o id inteiro sequencial tão público quanto antes (remodelar o id nunca foi o fix). Replay o walkthrough contra ela: ler o próprio pedido retorna 200, ler o de qualquer outro retorna **404**, e como um request de não-dono recusado e um id genuinamente inexistente retornam ambos 404, o status code não dá ao atacante nada pra enumerar.
