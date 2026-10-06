# bfla-admin-function — Broken Function Level Authorization (BFLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para BFLA (Broken Function Level Authorization), o API5:2023 do OWASP API Security Top 10. Function-level authorization é o check que pergunta *"você pode invocar esta operação, para começo de conversa?"* — uma pergunta diferente de *"este objeto é seu?"*, que é o tipo object-level. A API expõe uma função admin, `POST /admin/users/:handle/promote`, que concede a role de admin à conta nomeada no path. O endpoint autentica o Bearer token — token inválido leva `401` — e então executa a promoção sem nunca checar se o caller é admin, então qualquer membro logado consegue rodá-la.

É aqui que a série muda de eixo. Os três átomos de API1 — `bola-sequential-id`, `bola-uuid-leaked` e `bola-nested-resource` — eram todos BOLA (Broken Object Level Authorization): cada um servia registros de pedido, e em cada um tudo dependia de o pedido solicitado estar ou não ao alcance do caller. BOLA protege **instâncias**; BFLA protege **capacidades**. Aqui não se lê o registro de ninguém. Um membro comum invoca uma função reservada a administradores — **vertical privilege escalation**, alcançar funcionalidade acima do seu próprio nível de privilégio, enquanto os átomos de API1 mostraram o tipo horizontal: alcançar dados que pertencem a um par. A lição é que **um token válido prova quem está chamando, não que o caller pode rodar esta função**.

O path admin aqui é simplesmente conhecido. Rotas admin seguem nomes previsíveis, a spec OpenAPI (a descrição legível por máquina das rotas de uma API) costuma ser pública, e o bundle do front-end — o JavaScript que uma web app manda pra todo browser — carrega paths de telas que um usuário comum nunca vê. Em BFLA real, achar o endpoint quase nunca é a parte difícil, então este átomo o declara em vez de encenar uma descoberta. A vulnerabilidade não é o path ser alcançável; é a invocação da função nunca checar a sua role. O `bola-uuid-leaked` também partiu de uma premissa declarada — um UUID de pedido que chegou ao atacante por fora — mas lá a premissa *era* a lição. Aqui ela é economia: remove um passo que BFLA real raramente tem, pra o átomo gastar o tempo dele na invocação.

> **Teoria primeiro:** Leia [PortSwigger: Access control vulnerabilities and privilege escalation](https://portswigger.net/web-security/access-control)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — store em memória, sem banco

Os usuários vivem num `Map` de TypeScript, cada um carregando um único booleano, `is_admin` — a role que o check ausente deveria ter lido. Não há banco: BFLA não depende da camada de storage, porque o bug é um check ausente *acima* de qualquer store que guarde as roles, então o store fica mínimo e a ausência fica óbvia. O mapa `token -> user` também é em memória.

## Estado — as promoções são reais, e em memória

Este é o primeiro átomo da série cujo endpoint atacado escreve: uma promoção põe de verdade `is_admin` em `true` no alvo, e a mudança dura enquanto o container estiver de pé. Nada no walkthrough depende desse estado acumulado — rode os passos dele duas vezes e os status e os corpos voltam iguais. Cada gêmeo tem o próprio seed, então uma promoção na 8204 não muda nada na 8304. `./atom down bfla-admin-function && ./atom up bfla-admin-function` traz de volta o seed original, com a `carol` como única admin — e todo token emitido some, então faça login de novo.

## Só API — sem HTML, sem browser

Não há templates, não há landing page, não há UI: toda resposta de sucesso é JSON. É proposital — a função sob teste é um endpoint de API, e este átomo não modela nada além disso. Você opera tudo pelo **Burp Suite** (Repeater pra editar e reenviar um request único) ou pelo `curl`. Não há trilha browser; o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) trabalha exclusivamente no Burp.

## Autenticação simulada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — um valor aleatório que o servidor guarda e resolve de volta pra um usuário, tipo um OAuth2 opaque access token ou uma session id server-side, e explicitamente *não* um JWT (não há nada codificado dentro dele pra ler ou adulterar). Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade**: lidar com senha multiplicaria o código e ensinaria outra lição.

O que o atalho *não* faz é enfraquecer a autenticação. A autenticação aqui **é imposta**: token ausente, malformado ou desconhecido leva `401` no endpoint admin, no build vulnerable exatamente como no fixed. O token é cripto-forte (`randomBytes`), genuinamente emitido pelo servidor, e o ataque nunca o decodifica, altera ou forja — ele fica válido e seu do primeiro ao último request. O que falta não é autenticação; é o function-level check em cima dela — se o caller autenticado tem a role que a função exige.

## Usuários e roles

Quatro usuários no seed, cada um com um flag de role:

- `clancy` — o atacante (você). Um membro comum: `is_admin: false`.
- `alice` — a vítima principal, também membro comum: a conta que o `clancy` promove no exploit.
- `bob` — um membro comum, o alvo da promoção legítima da `carol` no build fixed.
- `carol` — a única administradora do seed (`is_admin: true`), presente pra o build fixed poder mostrar a função ainda funcionando pra alguém que tem permissão de rodá-la.

Os usuários não têm nome, e-mail nem endereço — nada que uma resposta pudesse vazar. É de propósito: não há aqui dado de terceiros pra confundir com uma leitura de objeto.

## Duas rotas, nada mais

- `POST /login` — corpo `{"user":"<name>"}`, devolve `{"token":"<opaque>"}`; usuário desconhecido leva `400`.
- `POST /admin/users/:handle/promote` — a função admin. O alvo vai no path; não precisa de corpo. Sucesso é `200` com `{"handle":"<target>","is_admin":true}`; alvo desconhecido leva `404`.

Não há rota de leitura — nada de `GET /me`, nada de listagem de usuários — nem de demote; isso é escolha, não omissão. A função admin muda estado e devolve só o que escreveu: o handle que você mandou e um `true` literal, nunca o registro de outro usuário. Sem dado de terceiros voltando, não há nada pra ler como *"vi uma coisa que não era minha"* — o reflexo de BOLA que os átomos de API1 treinaram — e o ataque fica no eixo da operação. O preço vai dito com todas as letras: o efeito de uma promoção é real, mas **não é observável pela API**. O corpo de sucesso volta byte a byte idêntico quer o alvo fosse membro, quer já fosse admin, e nenhuma rota lê uma role de volta, então de fora um `200` só te diz que a função rodou.

## Como rodar

Da raiz do repo:

```bash
./atom up bfla-admin-function
```

- API vulnerable: `http://127.0.0.1:8204`
- API fixed: `http://127.0.0.1:8304`

Não há landing page — o ponto de entrada é o `POST /login` (veja o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md)). Pare com `./atom down bfla-admin-function`. Se preferir Docker cru: `cd atoms/api/API5-broken-function-level-authz/bfla-admin-function && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (só API; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8304 atende a mesma função admin contra o mesmo seed, e acrescenta **uma guarda**, entre o check de autenticação e a busca do alvo: o handler checa se o caller é admin e recusa com **`403`** se não for. Nada mais muda. Replay o walkthrough contra ela: o `clancy` promovendo a `alice` agora leva `403`, devolvido antes de qualquer escrita; a `carol`, a admin do seed, promovendo o `bob` continua levando `200`, então a feature funciona pra quem pode rodá-la; e token ausente ou ruim continua levando `401`. O check de role roda antes mesmo de o alvo ser buscado, então um não-admin leva o mesmo `403` pra um handle que não existe. Repare no status: `403`, não o `404` que os átomos de API1 devolvem pra um pedido fora do seu escopo. Lá, o `404` deixava *"não é seu"* indistinguível de *"não existe"*; aqui a coisa protegida é uma função única e conhecida, sem existência a esconder — o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) trabalha o porquê.
