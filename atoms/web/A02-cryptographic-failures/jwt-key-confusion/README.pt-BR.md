# jwt-key-confusion — JWT algorithm confusion (RS256 → HS256)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask para o terceiro tipo de falha de JWT: **algorithm confusion**. A API assina seus tokens com **RS256** — cryptography assimétrica, onde uma chave **privada** assina e uma chave **pública** verifica — e publica essa chave pública em `GET /jwks`, exatamente como um serviço real faria pra clientes verificarem tokens. **Nada aqui é fraco.** A chave RSA é robusta, de 2048 bits; a signature é matematicamente sólida. A única falha é que o servidor decide *como* verificar cada token confiando no campo `alg` que o **próprio token** declara: `alg:RS256` → verifica com RSA, `alg:HS256` → verifica por HMAC **usando essa mesma chave pública como secret**. Como a chave pública é pública, um atacante forja um token `alg:HS256` com `role: admin`, assina o HMAC com os bytes exatos da chave pública, e o servidor aceita — a signature bate, porque é feita com a mesma chave com que o servidor verifica.

Este átomo **fecha a trilogia JWT**, e é irmão dos dois átomos JWT anteriores — de duas formas diferentes:

- [`jwt-none-alg`](../jwt-none-alg/) — **a fechadura não trancava** (`alg:none`, verificação pulada).
- [`jwt-weak-secret`](../jwt-weak-secret/) — **a fechadura trancava, mas a chave estava num post-it** (HS256, secret de dicionário, quebrado por brute force).
- **Este átomo — a fechadura tranca, a chave é forte, a signature bate — e mesmo assim abre**, porque o servidor deixa o *token* escolher o algoritmo.

Ele compartilha seu **shape de fix** com o `jwt-none-alg`: os dois bugs são o servidor confiando no `alg` do token, e os dois fixes são o mesmo movimento — parar de ramificar pelo header, fixar a allowlist de algoritmos, e deixar a lib impor. O header é dado, não policy. E compartilha seu **impacto** com o `jwt-weak-secret`: escalação vertical de privilégio (`role: user` → `role: admin` forjado). O que muda é o mecanismo — no `jwt-weak-secret` algo estava *fraco*; aqui nada está. Key confusion não é cryptography quebrada (o RSA e o HMAC estão ambos intactos); é um **erro de lógica** em como a verificação foi escrita.

> **Teoria primeiro:** Leia [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt#jwt-algorithm-confusion)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa. (A seção "JWT algorithm confusion" dela é este átomo.)

## Nota de stack — sem banco

Como os dois irmãos JWT, este átomo guarda os dados em estruturas Python simples, não num banco. Algorithm confusion não depende da camada de storage — o JWT é stateless, e o servidor só guarda o par RSA com que assina e verifica. A superfície é mínima pra o único branch controlado pelo `alg` ficar óbvio.

## API only — sem HTML, sem browser

Não há UI web: sem templates, sem landing page, toda resposta é JSON (exceto `GET /jwks`, que serve a chave pública como PEM). Bugs de JWT vivem em contexto de API — bytes que você monta e manda em `Authorization: Bearer ...`. Você opera este átomo pelo **Burp Suite (Repeater)** e por um **terminal** — a forja acontece no terminal, do jeito que aconteceria num engajamento real. Não há trilha browser; o `WALKTHROUGH.pt-BR.md` trabalha no Burp mais o terminal.

## Autenticação simulada

Autenticação de verdade (senha, hashing, session de login) está fora do escopo. Este lab simula com `POST /login`, que devolve um **JWT assinado em RS256** carregando `{"sub": "...", "role": "user"}`. Não há senha, e **`role` é sempre `user`** — o servidor nunca emite um token de admin. É esse o ponto: você não consegue logar como admin, tem que *forjar*. Quatro endpoints:

- `POST /login` — obter um token legítimo `role: user` (assinado com a chave privada RSA).
- `GET /jwks` — a chave **pública** RSA, em PEM. Pública por design (clientes verificam com ela) — e o material de forja do atacante.
- `GET /api/profile` — qualquer token válido; devolve suas claims (seu baseline, e onde você captura o JWT).
- `GET /admin/users` — exige `role: admin`; seu token `user` leva `403`, um token `admin` forjado leva `200`.

## Chaves — um par RSA DUMMY de lab

O átomo traz um **par RSA fixo e commitado, de 2048 bits** (em `vulnerable/keys/` e `fixed/keys/`, byte-idênticos). É uma **chave DUMMY de lab — nunca uma real.** A chave privada está commitada *só* porque este é um lab intencionalmente vulnerável; um par fixo mantém o walkthrough determinístico (você recebe os tokens exatos mostrados). Nunca reutilize pra nada de verdade. Só a chave **pública** é servida (`/jwks`); a privada nunca sai do processo.

## Como rodar

Da raiz do repo:

```bash
./atom up jwt-key-confusion
```

- API vulnerable: `http://127.0.0.1:8014`
- API fixed: `http://127.0.0.1:8114`

Não há landing page — o ponto de entrada é `POST /login` (veja o `WALKTHROUGH.pt-BR.md`). Pare com `./atom down jwt-key-confusion`. Se preferir Docker cru: `cd atoms/A02-cryptographic-failures/jwt-key-confusion && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo: o Burp loga, captura o token e pega a chave pública; o terminal forja o token admin; o Burp faz o replay. Sem trilha browser.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8114 é **byte-idêntica exceto pelo helper `verify`** (e os imports de que ele precisa). Em vez de ler o `alg` do token e ramificar, ela fixa `jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])` e deixa o PyJWT impor — o mesmo shape de fix do `jwt-none-alg`. Replique o token forjado `alg:HS256` contra `GET /admin/users` na porta 8114 e ele retorna **401** (HS256 não está na allowlist); um token RS256 legítimo ainda leva `200` no `/api/profile` e `403` no `/admin/users`. Mesmo par de chaves, mesmos endpoints — o token só não escolhe mais como é verificado.
