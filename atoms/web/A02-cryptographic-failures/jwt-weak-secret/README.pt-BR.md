# jwt-weak-secret — JWT weak signing secret (brute-forced)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask para o segundo tipo de falha de JWT: um secret de assinatura fraco o bastante pra cair em brute force. A API assina seus tokens com HS256 e **os verifica corretamente** — não há branch `alg:none`, a allowlist `algorithms=["HS256"]` é imposta, uma signature adulterada é rejeitada com `401`. Nada da cryptography está quebrado. A única falha é o **valor** do secret: ele é uma palavra de dicionário. Um atacante captura um token legítimo, quebra o secret HS256 por brute force contra uma wordlist e — de posse da chave — forja um token com `role: admin` que o servidor aceita como genuíno, porque ele *é* genuíno: assinado com a chave de verdade.

Este é o irmão do [`jwt-none-alg`](../jwt-none-alg/), e o contraste é a lição. Lá, **a fechadura não trancava** — o servidor pulava a verificação de assinatura quando o token pedia (`alg:none`). Aqui, **a fechadura tranca, corretamente — mas a chave estava anotada num post-it.** No `jwt-none-alg` você *arranca* a signature; aqui você a *refaz*, perfeitamente válida, com o secret roubado. "Assinado" não é "seguro": uma signature é tão forte quanto sua chave, e uma chave tirada de uma wordlist não é chave nenhuma. O `jwt-none-alg` até aponta pra cá — o walkthrough dele cita *"weak shared secrets that survive a brute-force"* como outra forma de perder o mesmo jogo. Este átomo é esse jogo.

> **Teoria primeiro:** Leia [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa. (A seção "Brute-forcing secret keys" dela é este átomo.)

## Nota de stack — sem banco

Como o `jwt-none-alg`, este átomo guarda os dados em estruturas Python simples, não num banco. Um secret fraco não depende da camada de storage — o JWT é stateless, e o servidor só guarda o `SECRET` com que verifica. A superfície é mínima pra o único valor fraco ficar óbvio.

## API only — sem HTML, sem browser

Não há UI web: sem templates, sem landing page, toda resposta é JSON. Bugs de JWT vivem em contexto de API — bytes que você monta e manda em `Authorization: Bearer ...`. Você opera este átomo pelo **Burp Suite (Repeater)** e por um **terminal** — o crack e a forja acontecem no terminal, do jeito que aconteceriam num engajamento real. Não há trilha browser; o `WALKTHROUGH.pt-BR.md` trabalha no Burp mais o terminal.

## Autenticação simulada

Autenticação de verdade (senha, hashing, session de login) está fora do escopo — isso cabe num átomo de autenticação dedicado. Este lab simula com `POST /login`, que devolve um **JWT assinado em HS256** carregando `{"sub": "...", "role": "user"}`. Não há senha, e **`role` é sempre `user`** — o servidor nunca emite um token de admin. É esse o ponto: você não consegue logar como admin, tem que *forjar*. Três endpoints:

- `POST /login` — obter um token legítimo `role: user`.
- `GET /api/profile` — qualquer token válido; devolve suas claims (seu baseline, e onde você captura o JWT).
- `GET /admin/users` — exige `role: admin`; seu token `user` leva `403`, um token `admin` forjado leva `200`.

## Como rodar

Da raiz do repo:

```bash
./atom up jwt-weak-secret
```

- API vulnerable: `http://127.0.0.1:8013`
- API fixed: `http://127.0.0.1:8113`

Não há landing page — o ponto de entrada é `POST /login` (veja o `WALKTHROUGH.pt-BR.md`). Pare com `./atom down jwt-weak-secret`. Se preferir Docker cru: `cd atoms/A02-cryptographic-failures/jwt-weak-secret && docker compose up --build`.

O átomo traz uma `wordlist-sample.txt` curada e pequena (~1000 senhas comuns) na raiz, pra o passo do crack — veja o walkthrough.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo: o Burp captura e replay o token, o terminal quebra o secret (John the Ripper) e forja o token admin. Sem trilha browser.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8113 é **byte-idêntica exceto por uma linha** — a constante `SECRET`. Ela troca o fraco `changeme123` por um valor de 43 caracteres e alta entropia vindo de `secrets.token_urlsafe(32)`. Mesmo algoritmo, mesma verificação, mesmos endpoints. Rode o mesmo crack do John the Ripper contra um token da app fixed e ele não acha nada (o secret forte não está em wordlist nenhuma); replique o token admin que você forjou contra a vulnerable e ele retorna **401** (a signature não bate mais). A segurança morava inteiramente no valor do secret — não em uma linha de lógica.
