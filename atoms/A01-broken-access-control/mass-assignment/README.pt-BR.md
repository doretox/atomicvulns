# mass-assignment — Mass Assignment

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em Flask para um **Mass Assignment** clássico. A app tem um endpoint de atualização de perfil: você manda um corpo JSON com os campos da sua conta e ela salva — `POST /profile` com `{"name": "...", "email": "..."}` muda seu nome e e-mail. O bug é que o handler copia *todos* os campos do JSON direto pra sua conta (`account.update(data)`), não só os que o formulário oferecia. Então, se você acrescentar `"role": "admin"` — um campo que o formulário de perfil nunca teve —, ele é copiado também, e sua conta vira admin. A prova está na resposta: o `GET /profile` passa a reportar `role: admin`, e o `GET /admin`, que retornava `403` antes, agora responde `200`.

A lição é que o **servidor**, não o cliente, tem que decidir quais campos uma request pode setar. Confiar na *forma* do input — ligar quaisquer chaves que chegarem direto no objeto — é o bug inteiro. Isto é **A01 — Broken Access Control** (CWE-915, "Improperly Controlled Modification of Dynamically-Determined Object Attributes"; seu pai CWE-913 é um dos CWEs que a OWASP mapeia pra A01:2021): o controle que falta é sobre *quais atributos o usuário pode modificar* — você deveria poder setar `name`/`email`, mas a app deixa você escrever `role`, um campo que só o servidor deveria controlar. O OWASP API Security Top 10 rastreia a mesma falha como [API3:2023 — Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/) (que absorveu o antigo risco standalone "Mass Assignment"). O fix é server-side e estrutural — uma **allowlist de campos**: o servidor nomeia os campos que o usuário pode setar (`name`, `email`) e copia só esses; `role` e todo o resto são ignorados. A única diferença entre `vulnerable/` e `fixed/` é essa seleção de campos.

> **Teoria primeiro:** Leia [PortSwigger: Mass assignment](https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — sem banco

Como o `bola-rest`, este átomo guarda o estado num dict Python simples em vez de um banco. Mass assignment não depende da camada de storage — o bug é a cópia cega de campos acima de qualquer store que você use. Não há **ORM** aqui, de propósito: um ORM é onde essa falha é mais famosa (um campo extra vira uma coluna escrita no banco), mas este átomo modela a mesma falha com um `dict.update()` cru pra a única linha ruim ficar visível a olho nu. Veja o `DIFF.pt-BR.md`.

## API only — sem HTML, sem browser

Este átomo não tem UI web: sem templates, sem landing page, toda resposta é JSON. É proposital — mass assignment vive em APIs que fazem bind de corpos de request em objetos, e este átomo modela uma. Você o opera inteiramente pelo **Burp Suite (Repeater)** ou por `curl`; não há trilha browser. O `WALKTHROUGH.pt-BR.md` trabalha exclusivamente no Burp — a prova é a resposta (o `role` no `GET /profile`, o status do `GET /admin`).

## Como rodar

Da raiz do repo:

```bash
./atom up mass-assignment
```

- API vulnerable: `http://127.0.0.1:8025`
- API fixed: `http://127.0.0.1:8125`

Não há landing page — os endpoints são `POST /profile`, `GET /profile` e `GET /admin` (veja o `WALKTHROUGH.pt-BR.md`). A conta vive em memória, então um restart (`./atom down mass-assignment` e depois `up`) a reseta pra um `role: user` novo se você quiser refazer o baseline. Pare com `./atom down mass-assignment`. Se preferir Docker cru: `cd atoms/A01-broken-access-control/mass-assignment && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8125 atende a mesma feature de perfil. Ela adiciona uma **allowlist de campos** — `ALLOWED_FIELDS = {"name", "email"}` — e copia só esses do JSON, sem mudar mais nada. Rode o walkthrough contra ela: `POST /profile` com `{"name": ..., "email": ..., "role": "admin"}` ainda atualiza seu nome e e-mail mas **ignora o `role`**, então o `GET /profile` mantém `role: user` e o `GET /admin` continua retornando `403`. Uma atualização legítima de `name`/`email` se comporta idêntica nas duas apps; só o campo extra `role` as separa. A única mudança em relação ao `vulnerable/` é essa allowlist de campos server-side; veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md). Isto é **A01 — Broken Access Control**: o servidor, não o cliente, decide quais campos podem ser setados.
