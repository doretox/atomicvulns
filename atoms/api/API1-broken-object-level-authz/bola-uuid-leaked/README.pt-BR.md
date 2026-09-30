# bola-uuid-leaked — Broken Object Level Authorization (BOLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para BOLA (Broken Object Level Authorization) — o nome que a área de API security dá a um IDOR (insecure direct object reference) que vive num endpoint REST, e o API1:2023, o risco #1 do OWASP API Security Top 10. A API serve registros de pedido via `GET /orders/:id`. Todo request carrega um Bearer token opaco, e o endpoint até autentica ele — token inválido leva `401` — mas nunca checa se o pedido pedido pertence ao caller. O id de cada pedido é um **UUID v4** aleatório, não um número adivinhável, e isso não muda nada: no momento em que a atacante tem um id de pedido válido, o check ausente entrega aquele pedido — o nome do cliente, o endereço de entrega, o item e o valor.

Aqui **"leaked" quer dizer que o UUID do pedido chegou ao atacante por um canal de fora da aplicação** — um chamado de suporte, um print, um link compartilhado — do jeito que ids circulam no mundo real. A aplicação em si não vaza id nenhum; o único bug é o check de posse ausente no `GET /orders/:id`.

A lição é que **estar autenticado não é estar autorizado**. Um token válido prova *quem você é*; não diz nada sobre se *este* objeto é seu. O átomo companheiro `bola-sequential-id` fez o mesmo argumento com um id inteiro sequencial — onde os ids também eram triviais de adivinhar. Este átomo remove essa variável: o id é um UUID aleatório de verdade, obtido de fora, e a falha sobrevive inteira. O formato do id governa *quão difícil* um id é de descobrir; o check ausente é o que faz o request *ter sucesso*. Trocar o contador por um UUID mudou a descoberta, não o bug — e, como o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) mostra, o fix é a mesma linha única de qualquer jeito.

> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — store em memória, sem banco

Os pedidos vivem num `Record` simples de TypeScript, não num banco. BOLA não depende da camada de storage: o bug é um authorization check ausente *acima* de qualquer store que você use, então o store fica mínimo e o check que falta fica óbvio. O mapa `token -> user` também é em memória — reinicie o container e todo token emitido desaparece, então faça login de novo e continue. Os doze ids de pedido são UUIDs fixos, cravados no seed (nunca gerados no boot), pra o walkthrough poder nomear um exatamente.

## Só API — sem HTML, sem browser

Não há templates, não há landing page, não há UI: toda resposta de sucesso é JSON. É proposital — BOLA vive em APIs REST, e este átomo modela uma. Você opera tudo pelo **Burp Suite** (Repeater pra editar e reenviar um request único, Intruder pra repetir um request sobre uma lista de valores) ou pelo `curl`. Não há trilha browser; o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) trabalha exclusivamente no Burp.

## Autenticação simulada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — um valor aleatório que o servidor guarda e resolve de volta pra um usuário, tipo um OAuth2 opaque access token ou uma session id server-side, e explicitamente *não* um JWT (não há nada codificado dentro dele pra ler ou adulterar). Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade**: lidar com senha multiplicaria o código e ensinaria outra lição.

O que o atalho *não* faz é enfraquecer a autenticação. A autenticação aqui **é imposta**: token ausente, malformado ou desconhecido leva `401` em todo endpoint protegido. O token é cripto-forte (`randomBytes`), genuinamente emitido pelo servidor, e o ataque nunca o decodifica, altera ou forja — ele fica válido e seu do primeiro ao último request. Mantenha os dois eixos separados: o que virou UUID é o *id do pedido*, não o token. O que falta não é autenticação; é o object-level authorization check em cima dela.

Quatro usuários no seed:

- `dana` — a atacante (você). Dona de exatamente **um** pedido.
- `alice`, `bob`, `carol` — as vítimas. Dividem os outros **onze** pedidos de forma desigual: seis, três e dois.

## Como rodar

Da raiz do repo:

```bash
./atom up bola-uuid-leaked
```

- API vulnerable: `http://127.0.0.1:8202`
- API fixed: `http://127.0.0.1:8302`

Não há landing page — o ponto de entrada é o `POST /login` (veja o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md)). Pare com `./atom down bola-uuid-leaked`. Se preferir Docker cru: `cd atoms/api/API1-broken-object-level-authz/bola-uuid-leaked && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (só API; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8302 atende a mesma feature de pedidos contra o mesmo seed. Ela acrescenta **um predicado a uma guarda** — o pedido só é devolvido se existir *e* pertencer ao usuário do token que chamou — e não muda mais nada, formato do id incluído. Replay o walkthrough contra ela: o seu próprio pedido continua devolvendo `200`, e todo outro id devolve **`404`**, exatamente o mesmo `404` que um id nunca seedado devolve. Como "não é seu" e "não existe" saem idênticos, o status code não dá ao atacante como distinguir um pedido real de um id inventado.
