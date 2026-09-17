# deserialization-node — Insecure deserialization

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API Node.js mínima para insecure deserialization clássica — remote code execution através da lib **`node-serialize`**. A app é uma API de "user preferences": guarda as suas preferências num cookie `prefs`, serializado com `node-serialize` (um package npm) e codificado em base64. A cada request ela base64-decoda o cookie e chama `serialize.unserialize` na string pra reconstruir as preferências. Mas você controla o seu próprio cookie — e a `node-serialize` não desserializa só *dados*: ela sabe serializar **funções** JavaScript, e no `unserialize` reconstrói uma função rodando **`eval`** no corpo-fonte dela. Um cookie forjado carregando uma função marcada com `_$$ND_FUNC$$_` cujo corpo termina em `()` (uma função que se auto-invoca) faz o `unserialize` rodar aquele código no momento em que desserializa. O mesmo request que lê o seu tema salvo roda o comando do atacante.

Isto é A08 — Software and Data Integrity Failures: a app confia num blob serializado que cruzou uma fronteira de confiança e o reconstrói com um formato que carrega comportamento. É o **rosto Node** da falha que o `deserialization-pickle` mostra em Python — mesma classe, mesmo teto (remote code execution), mesmo tipo de fix (um formato-que-carrega-comportamento → um só-dado), mas ecossistema e mecanismo diferentes: lá o desserializador perigoso é o `pickle` da stdlib do Python (disparado por `__reduce__`); aqui é um package npm, a `node-serialize` (disparada por uma função `_$$ND_FUNC$$_` dada `eval`). O fix não é validar nem assinar o cookie — é trocar o **formato**: JSON carrega só dados, então o `JSON.parse` não tem caminho de código pra rodar. A única diferença entre `vulnerable/` e `fixed/` é `serialize.unserialize` vs `JSON.parse` — e a dependência que essa escolha arrasta.

> **Teoria primeiro:** Leia [PortSwigger: Insecure deserialization](https://portswigger.net/web-security/deserialization)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — Node.js, node-serialize como objeto de estudo

Este é um átomo Node.js em vez de Python/Flask, porque insecure deserialization em Node é idiomática do ecossistema JavaScript: o perigo chega como um package npm que sabe (de)serializar funções. O servidor usa o módulo `http` embutido direto — sem Express, sem framework; o cookie é parseado à mão. A **única** dependência de runtime é a `node-serialize`, e ela vive **só no lado vulnerable** — é o objeto de estudo, pinada numa versão exata e visível no `package.json`. A app `fixed/` tem **zero** dependências de runtime: `JSON.parse` é stdlib. Note que a `node-serialize` não tem release corrigida — o fix não é "atualizar a lib", é **parar de usá-la** e voltar a um formato só-dado. Então o `package.json` e o `Dockerfile` diferem entre os dois lados (o vulnerable instala a `node-serialize`; o fixed não instala nada), e essa diferença faz parte da lição. A imagem base é pinada por tag *e* digest.

## API only — sem HTML, sem browser

Este átomo não tem UI web: sem templates, sem landing page, toda resposta é JSON. É proposital — esta falha de deserialization vive num cookie que uma API JSON lê e reconstrói, e este átomo modela uma. Você o opera inteiramente pelo **Burp Suite (Repeater)** ou por `curl`; não há trilha browser. O JavaScript aqui roda no **servidor** (Node), e a prova de execução é um efeito colateral no servidor — um arquivo marcador — lido com `docker compose exec`, não algo que você vê na resposta HTTP. O `WALKTHROUGH.pt-BR.md` trabalha exclusivamente no Burp.

## Como rodar

Da raiz do repo:

```bash
./atom up deserialization-node
```

- API vulnerable: `http://127.0.0.1:8027`
- API fixed: `http://127.0.0.1:8127`

Não há landing page — o único endpoint é o `GET /`, que seta o cookie `prefs` na primeira visita e o lê de volta a cada request (veja o `WALKTHROUGH.pt-BR.md`). Pare com `./atom down deserialization-node`. Se preferir Docker cru: `cd atoms/A08-data-integrity-failures/deserialization-node && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8127 atende a mesma feature de "user preferences" e lê o mesmo cookie `prefs` — mas (de)serializa com JSON (`JSON.stringify` / `JSON.parse`) em vez de `node-serialize`, e larga a dependência inteira. Rode o exploit do `WALKTHROUGH.pt-BR.md` contra ela: o mesmo cookie malicioso que roda um comando na app vulnerable não faz nada aqui — o `JSON.parse` reconstrói só dados (nunca uma função, nunca um `eval`), a resposta continua `{"theme":"light"}`, e nenhum comando roda (o marcador `/tmp/pwned` nunca é criado). Um cookie benigno faz round-trip idêntico nas duas apps; só o payload `_$$ND_FUNC$$_` as separa. A única mudança em relação ao `vulnerable/` é o formato de serialização; veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md). Isto é **A08 — Software and Data Integrity Failures**: nunca desserialize dado não-confiável com um formato que carrega comportamento.
