# bola-sequential-id — Broken Object Level Authorization (BOLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para BOLA (Broken Object Level Authorization) — o nome que a área de API security dá a um IDOR (insecure direct object reference) que vive num endpoint REST, e o [API1:2023](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization), o risco #1 do OWASP API Security Top 10. A API serve registros de pedido via `GET /orders/:id`. Todo request carrega um Bearer token opaco, e o endpoint até autentica ele — token inválido leva `401` — mas nunca checa se o pedido pedido pertence ao caller. Doze pedidos ficam atrás dos ids contíguos `1001`–`1012` e você é dono de exatamente um deles, então trocar o id no path te entrega o de outra pessoa: o nome dela, o endereço de entrega, o que ela comprou e quanto pagou.

A lição é que **estar autenticado não é estar autorizado**. Um token válido prova *quem você é*; não diz nada sobre se *este* objeto é seu. Duas coisas distintas fazem a leitura acontecer, e mantê-las separadas é o ponto do átomo: o **id sequencial** é o que torna a descoberta barata — sabendo um id, você deduz os vizinhos — enquanto o **ownership check ausente** é o que faz o request ter sucesso. Só o segundo é a vulnerabilidade, e o fix mexe só no segundo: os ids continuam exatamente tão sequenciais e tão públicos quanto antes. O átomo web `bola-rest` já fez o argumento central desta classe em Flask; este aqui a escala — quatro usuários, doze pedidos carregando dado pessoal, e uma enumeração que varre a coleção inteira numa passada.

> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — store em memória, sem banco

Os pedidos vivem num `Record` simples de TypeScript, não num banco. BOLA não depende da camada de storage: o bug é um authorization check ausente *acima* de qualquer store que você use, então o store fica mínimo e o check que falta fica óbvio. O mapa `token -> user` também é em memória — reinicie o container e todo token emitido desaparece, então faça login de novo e continue.

## Só API — sem HTML, sem browser

Não há templates, não há landing page, não há UI: toda resposta de sucesso é JSON. É proposital — BOLA vive em APIs REST, e este átomo modela uma. Você opera tudo pelo **Burp Suite** (Repeater pra editar e reenviar um request único, Intruder pra repetir um request sobre uma lista de valores) ou pelo `curl`. Não há trilha browser; o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) trabalha exclusivamente no Burp.

## Autenticação simulada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — um valor aleatório que o servidor guarda e resolve de volta pra um usuário, tipo um OAuth2 opaque access token ou uma session id server-side, e explicitamente *não* um JWT (não há nada codificado dentro dele pra ler ou adulterar). Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade**: lidar com senha multiplicaria o código e ensinaria outra lição.

O que o atalho *não* faz é enfraquecer a autenticação. A autenticação aqui **é imposta**: token ausente, malformado ou desconhecido leva `401` em todo endpoint protegido. O token é cripto-forte (`randomBytes`), genuinamente emitido pelo servidor, e o ataque nunca o decodifica, altera ou forja — ele fica válido e seu do primeiro ao último request. O que falta não é autenticação; é o object-level authorization check em cima dela.

Quatro usuários no seed:

- `dana` — o atacante (você). Dono de exatamente **um** pedido, o `1007`.
- `alice`, `bob`, `carol` — as vítimas. Dividem os outros **onze** pedidos de forma desigual: seis, três e dois.

## Como rodar

Da raiz do repo:

```bash
./atom up bola-sequential-id
```

- API vulnerable: `http://127.0.0.1:8201`
- API fixed: `http://127.0.0.1:8301`

Não há landing page — o ponto de entrada é o `POST /login` (veja o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md)). Pare com `./atom down bola-sequential-id`. Se preferir Docker cru: `cd atoms/api/API1-broken-object-level-authz/bola-sequential-id && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (só API; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8301 atende a mesma feature de pedidos contra o mesmo seed. Ela acrescenta **um predicado a uma guarda** — o pedido só é devolvido se existir *e* pertencer ao usuário do token que chamou — e não muda mais nada, formato do id incluído. Replay o walkthrough contra ela: o seu próprio pedido continua devolvendo `200`, e todo outro id devolve **`404`**, exatamente o mesmo `404` que um id nunca seedado devolve. Como "não é seu" e "não existe" saem idênticos, o status code não dá ao atacante nada pra enumerar.
