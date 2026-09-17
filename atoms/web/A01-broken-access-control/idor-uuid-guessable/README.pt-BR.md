# idor-uuid-guessable — Insecure Direct Object Reference (guessable UUID)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para IDOR onde o id do objeto é um UUID. A app serve recibos privados via `GET /receipt/<uuid>`, e o desenvolvedor trata o UUID "impossível de adivinhar" como o controle de acesso — quem tem o link vê o recibo, e nada mais o protege. A view nunca checa se o recibo pertence ao caller, então é exatamente o mesmo bug do `idor-numeric-id`: um ownership check ausente. Trocar o id inteiro por um UUID mudou quão difícil é *adivinhar* o id, não se o servidor *confere* quem está pedindo.

Este átomo é o amadurecimento do `idor-numeric-id`, e ele entrega duas lições de peso igual. **Primeira:** um identificador difícil de adivinhar não é um controle de acesso — até um UUIDv4 perfeitamente aleatório é legível por qualquer um que obtenha o id, porque o check ausente, não o formato do id, sempre foi o bug. **Segunda:** este id nem é imprevisível — é um UUIDv1, que empacota um timestamp e o node do host, então com um clock sequence estável ele é *reconstruível* a partir de dados que a app já expõe (um recibo seu pra recuperar o fingerprint do gerador, mais o `issued_at` da vítima em microssegundos mostrado no dashboard). O fix que importa é o ownership check; trocar para UUIDv4 é defense-in-depth, não a correção.

> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — sem banco

Como o `idor-numeric-id`, este átomo guarda os dados num dict Python simples em vez de SQLite. IDOR não depende da camada de storage: o bug é um check de autorização ausente acima de qualquer store que você use. A superfície é mantida mínima pra a linha que falta ficar óbvia. A escolha de storage em cada átomo segue a superfície do bug — não o contrário.

## Autenticação simulada

Autenticação de verdade (form de login, session, password hashing) está fora do escopo aqui — essa cerimônia cabe num átomo de autenticação dedicado. Este lab simula "quem está logado" com um único header, `X-User-ID`, reusando a convenção do `idor-numeric-id`. Dois usuários no seed, com papéis explícitos:

- `mallory` — a atacante (você). O caller default quando o header está ausente, e quem cria o próprio recibo.
- `alice` — a vítima. O recibo dela é seedado no startup — o alvo que você não deveria conseguir ler.

## Como rodar

Da raiz do repo:

```bash
./atom up idor-uuid-guessable
```

- App vulnerable: <http://127.0.0.1:8011/>
- App fixed: <http://127.0.0.1:8111/>

Pare com `./atom down idor-uuid-guessable`. Se preferir Docker cru: `cd atoms/A01-broken-access-control/idor-uuid-guessable && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8111 atende a mesma feature de recibos. Ela adiciona uma linha — um ownership check que retorna **403 Forbidden** a menos que o recibo pertença ao `X-User-ID` que chamou — e, como defense-in-depth, gera os ids com `uuid4` em vez do `uuid1` reconstruível. Replay o walkthrough contra ela: ler o próprio recibo como dono retorna 200, mas ler como qualquer outro retorna 403, e a reconstrução nem começa contra um id v4. O dashboard continua expondo o `issued_at` exatamente como antes — prova de que o vazamento de metadado nunca foi o bug; o ownership check o torna inerte.
