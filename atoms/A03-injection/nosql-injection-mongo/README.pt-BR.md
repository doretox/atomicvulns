# nosql-injection-mongo — NoSQL Injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask + MongoDB para NoSQL injection. Um endpoint de login em JSON — `POST /login` — recebe `username` e `password` e monta uma query no MongoDB para achar o usuário: `find_one({"username": username, "password": password})`. O detalhe é que uma query do MongoDB não é uma string de SQL — é um **documento**, um objeto cujos valores podem ser escalares simples *ou* operadores. O endpoint joga o que o cliente mandou direto nesse documento, então se `password` chega como o objeto `{"$ne": null}` ("diferente de null") em vez de uma string, ele vira um **operador** do Mongo: o filtro passa a casar qualquer usuário com senha, e você loga como `admin` sem jamais conhecê-la.

A lição é que a causa raiz é **type confusion** (confusão de tipo), não sintaxe de string. O app esperava um escalar (uma string) e recebeu um objeto, e o driver passou esse objeto adiante fielmente, como estrutura da query. É por isso que o reflexo do SQL injection — "é injection, é só parametrizar" — erra aqui: o `pymongo` nunca concatena string, então ele já é o equivalente moral de uma query parametrizada, e ainda assim é vulnerável. O fix não é escapar nem parametrizar; é **forçar o tipo** — rejeitar qualquer coisa que não seja uma string antes que ela chegue à query.

> **Teoria primeiro:** Leia [PortSwigger: NoSQL injection](https://portswigger.net/web-security/nosql-injection)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — um MongoDB de verdade

Diferente dos átomos de SQL injection (`sqli-union-basic` e os irmãos blind), que embutem o SQLite como um arquivo dentro do processo, este átomo precisa de um *servidor* de banco de verdade: MongoDB. Então o lab roda **três containers** — um `mongo` compartilhado, mais `vulnerable` e `fixed`, os dois lendo os mesmos dados semeados. O serviço `mongo` **não tem porta no host**: ele é alcançável só na rede interna do compose (`mongodb://mongo:27017/`), nunca publicado na sua máquina — só os dois apps bindam em `127.0.0.1`. A coleção `users` é semeada no primeiro boot com dois usuários fake (`admin`, `alice`) cujas senhas são guardadas em plaintext — uma simplificação de lab; hashing de senha é ortogonal ao fix de NoSQL injection (veja o `DIFF.pt-BR.md`).

## API only — sem HTML, sem browser

Este átomo não tem UI web: sem templates, sem landing page, toda resposta é JSON. É proposital — o vetor de ataque *é* o corpo JSON da request. Um operador do MongoDB como `{"$ne": null}` é um objeto aninhado, e só o JSON carrega um objeto aninhado até o app; um form HTML ou uma query string chegariam como string simples (o `request.form`/`request.args` do Flask nunca montam um objeto aninhado — o truque `password[$ne]=` é comportamento de Express/PHP, não de Flask). Então você opera este átomo inteiramente pelo **Burp Suite (Repeater)** ou por `curl`; não há trilha browser, e a prova é a própria resposta do login. O `WALKTHROUGH.pt-BR.md` trabalha exclusivamente no Burp.

## Como rodar

Da raiz do repo:

```bash
./atom up nosql-injection-mongo
```

- API vulnerable: `http://127.0.0.1:8022`
- API fixed: `http://127.0.0.1:8122`

O `GET /` devolve um banner de aviso; o ponto de entrada é `POST /login` (veja o `WALKTHROUGH.pt-BR.md`). O container `mongo` nunca é publicado — só os dois apps são. Pare com `./atom down nosql-injection-mongo`. Se preferir Docker cru: `cd atoms/A03-injection/nosql-injection-mongo && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

O app corrigido na porta 8122 atende o mesmo login contra o mesmo MongoDB semeado. Ele adiciona um guard — `username` e `password` têm que ser strings, ou a request é rejeitada com **400** — e não muda mais nada. Replay o walkthrough contra ele: credenciais reais em string continuam logando com `200`, e o payload `{"$ne": null}` que passou no app vulnerable agora retorna `400`, porque um objeto nunca alcança o filtro da query.
