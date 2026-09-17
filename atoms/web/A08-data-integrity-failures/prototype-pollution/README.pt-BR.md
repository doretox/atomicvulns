# prototype-pollution — Prototype pollution

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em Node.js para um **Prototype pollution** clássico. A app guarda as suas preferências: você manda um corpo JSON com campos de config pro `POST /settings` e ela faz um *deep-merge* deles nos settings atuais — descendo recursivamente em objetos aninhados. Em JavaScript quase todo objeto herda de um pai compartilhado, o `Object.prototype`; ler uma propriedade que o objeto não tem faz o motor subir até esse pai, e a chave `__proto__` de um objeto é a porta pra ele. O bug é que o merge desce por *qualquer* chave do seu JSON — inclusive `__proto__`. Mande `{"__proto__":{"isAdmin":true}}` e o merge, em vez de escrever num campo dos settings, escreve no `Object.prototype` **compartilhado por todo objeto do processo**. A prova está num endpoint que nem fala de settings: o `GET /me` cria um objeto de usuário novo e vazio e checa `if (user.isAdmin)` — e agora, embora você nunca tenha tocado nesse objeto, ele responde admin.

A lição é que um deep-merge de JSON não-confiável tem que **recusar as chaves que alcançam um prototype compartilhado**, não descer por elas. Isto é **A08 — Software and Data Integrity Failures** (CWE-1321, "Improperly Controlled Modification of Object Prototype Attributes ('Prototype Pollution')"): um blob de dado não-confiável corrompe a integridade de uma estrutura de dados compartilhada por todo o processo — o pai de todo objeto. Ele divide a categoria com o `deserialization-pickle`, o outro átomo A08 do repo, mas o **impacto difere**: lá o desserializador *executa* comportamento embutido (remote code execution); aqui nada executa por padrão — o atacante envenena um objeto compartilhado e *outro* código confia nele, subvertendo a lógica de autorização. O fix é server-side — o merge **guarda as três chaves** que alcançam um prototype (`__proto__`, `constructor`, `prototype`) e as pula. A única diferença entre `vulnerable/` e `fixed/` é essa guarda.

> **Teoria primeiro:** Leia [PortSwigger: Prototype pollution](https://portswigger.net/web-security/prototype-pollution)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — Node.js, sem framework, sem dependências

Este é o primeiro átomo do repo em **Node.js** em vez de Python/Flask — prototype pollution é uma falha idiomática de JavaScript (o `Object.prototype` compartilhado e a prototype chain só existem em JS). O servidor usa o módulo `http` embutido direto: sem Express, sem framework, sem lib de merge, **zero dependências de runtime**. O corpo da request é lido à mão e passado por um `JSON.parse` explícito, e o deep-merge é **escrito à mão** — pra a única linha ruim ficar visível na fonte, não enterrada no `node_modules`. O `package.json` existe só pra pinar o `engines` do Node; a imagem base é pinada por tag *e* digest.

## API only — sem HTML, sem browser

Este átomo não tem UI web: sem templates, sem landing page, toda resposta é JSON. É proposital — este prototype pollution vive numa API JSON que mescla um corpo de request num objeto, e este átomo modela uma. Você o opera inteiramente pelo **Burp Suite (Repeater)** ou por `curl`; não há trilha browser. Note que "prototype pollution" *também* existe como falha client-side (browser) — este átomo **não** é isso: o JavaScript aqui roda no **servidor** (Node), o `Object.prototype` envenenado pertence ao processo Node, e a prova é a resposta HTTP. O `WALKTHROUGH.pt-BR.md` trabalha exclusivamente no Burp.

## Como rodar

Da raiz do repo:

```bash
./atom up prototype-pollution
```

- API vulnerable: `http://127.0.0.1:8026`
- API fixed: `http://127.0.0.1:8126`

Não há landing page — os endpoints são `POST /settings` e `GET /me` (veja o `WALKTHROUGH.pt-BR.md`). Poluir o `Object.prototype` é global ao processo e **persiste** até o processo reiniciar, então capture o baseline limpo (`GET /me` → `{"admin":false}`) **antes** de atacar. Um restart (`./atom down prototype-pollution` e depois `up`, ou `docker compose restart vulnerable`) reseta a poluição. Pare com `./atom down prototype-pollution`. Se preferir Docker cru: `cd atoms/A08-data-integrity-failures/prototype-pollution && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8126 atende a mesma feature de settings. O merge dela **guarda as três chaves que alcançam um prototype** — `if (key === "__proto__" || key === "constructor" || key === "prototype") continue;` — e não muda mais nada. Rode o walkthrough contra ela: `POST /settings` com `{"__proto__":{"isAdmin":true}}` é aceito (`200`), mas a chave `__proto__` é pulada, então o `Object.prototype` fica intacto e o `GET /me` continua retornando `{"admin":false}`. Um merge benigno (`{"theme":"dark"}`) se comporta idêntico nas duas apps; só o payload `__proto__` as separa. A única mudança em relação ao `vulnerable/` é essa guarda de chaves; veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md). Isto é **A08 — Software and Data Integrity Failures**: o merge tem que recusar as chaves que alcançam um prototype compartilhado.
