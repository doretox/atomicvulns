# bfla-method-based — Broken Function Level Authorization (BFLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para BFLA (Broken Function Level Authorization), o API5:2023 do OWASP API Security Top 10. A autorização se aplica a um par **(método, path)**, não a um path. A API protege o `GET /users/:handle` com um ownership check — você lê só o seu próprio perfil — mas deixa o `PATCH /users/:handle`, o mesmíssimo path, sem check nenhum, então qualquer usuário logado consegue editar o registro de qualquer um. Os dois métodos autenticam o Bearer token — um inválido leva `401` — e então a escrita prossegue sem nunca perguntar se o registro é seu.

O check que o `GET` tem e o `PATCH` não é um check de **posse** — object-level, o mesmo *"este registro é meu?"* que os átomos de API1 giravam. Mas isso é só o *conteúdo* do check ausente; o eixo da vulnerabilidade é o **método**. Então a pergunta de auditoria aqui é **"a autorização cobre todos os métodos deste path?"**, não "de quem é o objeto?". Leia como BOLA (Broken Object Level Authorization) e você procura no lugar errado: o ownership check está presente e *correto* no `GET` — ele devolve `403` quando você pede o registro de outra pessoa, `200` quando pede o seu — e a falha é só ele não cobrir o `PATCH`.

Este é o segundo BFLA da série. Seu irmão `bfla-admin-function` (também API5) mostrou uma função **sem** autorização nenhuma — um membro comum invocando uma operação restrita a admin, o que é **vertical** privilege escalation. Aqui um check existe e funciona num método de um path e simplesmente falta em outro: um dev protegeu a leitura, supôs que o recurso estava protegido, e deixou a escrita aberta. Os três átomos de API1 faziam uma pergunta sobre o objeto — *"este pedido é seu?"* no `bola-sequential-id` e no `bola-uuid-leaked`, *"ele pertence a esta loja?"* no `bola-nested-resource` — e a respondiam em toda rota que servia o objeto. Este átomo responde a pergunta de posse no `GET` e esquece de fazê-la no `PATCH`. O alcance é **horizontal** — editar o registro de um par, não ganhar uma role mais alta — e a lição é que **um check num método de um path nunca protege os outros**.

> **Teoria primeiro:** Leia [PortSwigger: Access control vulnerabilities and privilege escalation](https://portswigger.net/web-security/access-control)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — store em memória, sem banco

Os usuários vivem num `Map` de TypeScript, cada um guardando um único campo editável, `displayName`. Não há banco: BFLA não depende da camada de storage, porque o bug é um check ausente *acima* de qualquer store que guarde os registros, então o store fica mínimo e a brecha fica óbvia. O mapa `token -> user` também é em memória.

## Estado — a edição é real, e em memória

O `PATCH` escreve de verdade: ele muda o `displayName` do alvo, e a mudança dura enquanto o container estiver de pé. Mas essa mudança **não é observável pelo atacante através da API** — a resposta do `PATCH` só ecoa o valor que você mandou, e o `GET /users/:handle` recusa com `403` um registro que não é seu. O que torna a mudança visível é a **vítima** lendo o próprio registro: faça login como `alice` e o `GET /users/alice` devolve o `displayName` que o `clancy` escreveu. Cada gêmeo tem o próprio seed, então uma edição na 8205 não muda nada na 8305. O `./atom down bfla-method-based && ./atom up bfla-method-based` traz de volta o seed original — e com ele todo token emitido, então faça login de novo.

## Só API — sem HTML, sem browser

Não há templates, não há landing page, não há UI: toda resposta de sucesso é JSON. É proposital — a coisa sob teste é uma API, e este átomo não modela nada além disso. Você opera tudo pelo **Burp Suite** (Repeater pra editar e reenviar um request único) ou pelo `curl`. Não há trilha browser; o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) trabalha exclusivamente no Burp.

## Autenticação simulada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — um valor aleatório que o servidor guarda e resolve de volta pra um usuário, tipo um OAuth2 opaque access token ou uma session id server-side, e explicitamente *não* um JWT (não há nada codificado dentro dele pra ler ou adulterar). Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade**: lidar com senha multiplicaria o código e ensinaria outra lição.

O que o atalho *não* faz é enfraquecer a autenticação. A autenticação aqui **é imposta**: token ausente, malformado ou desconhecido leva `401` nas duas rotas, no build vulnerable exatamente como no fixed. O token é cripto-forte (`randomBytes`), genuinamente emitido pelo servidor, e o ataque nunca o decodifica, altera ou forja — ele fica válido e seu do primeiro ao último request. O que falta não é autenticação; é o ownership check no método `PATCH` — um check que o método `GET` no mesmo path já tem.

## Usuários e registros

Dois usuários no seed, cada um dono de exatamente um registro — o que tem a chave do próprio handle:

- `clancy` — o atacante (você). Dono do registro `clancy`.
- `alice` — a vítima. Dona do registro `alice`, o que o `clancy` edita no exploit.

Cada registro guarda um único campo editável, `displayName` (`"Clancy Park"`, `"Alice Nguyen"` no seed) — um campo de perfil comum, **não** um flag de privilégio. Não há role de admin neste átomo: posse é simplesmente *o handle no path igual ao caller*, e o build fixed mostra que a feature continua funcionando deixando você editar o seu **próprio** registro.

## Três rotas, nada mais

- `POST /login` — corpo `{"user":"<name>"}`, devolve `{"token":"<opaque>"}`; usuário desconhecido leva `400`.
- `GET /users/:handle` — lê um perfil. **Correto nos dois builds:** um ownership check devolve o registro só pro dono (`200` com `{"handle":"<handle>","displayName":"<value>"}`), e `403` pro de qualquer outro.
- `PATCH /users/:handle` — edita o nome de exibição. O build **vulnerable** omite o ownership check que o `GET` tem, então ele escreve qualquer registro. Sucesso é `200` com `{"handle":"<handle>","displayName":"<value>"}`; alvo desconhecido leva `404`.

Não há rota de listagem, nem `GET /me`, nem delete. Um ponto que vale dizer com todas as letras: o `200` do `PATCH` confirma o **bypass** — a escrita foi aceita pra um não-dono — mas o corpo dele só ecoa o `displayName` que você mandou, então não é, por si só, prova de que o registro mudou. A prova é a vítima lendo o próprio registro pelo `GET` autorizado, onde o valor plantado volta.

## Como rodar

Da raiz do repo:

```bash
./atom up bfla-method-based
```

- API vulnerable: `http://127.0.0.1:8205`
- API fixed: `http://127.0.0.1:8305`

Não há landing page — o ponto de entrada é o `POST /login` (veja o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md)). Pare com `./atom down bfla-method-based`. Se preferir Docker cru: `cd atoms/api/API5-broken-function-level-authz/bfla-method-based && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (só API; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8305 atende as mesmas duas rotas de usuário contra o mesmo seed, e acrescenta **uma guarda** ao `PATCH`, entre o check de autenticação e a busca do registro: o mesmo ownership check que o `GET` já tem — recusa com **`403`** a menos que o handle no path seja o do próprio caller. Nada mais muda. Replay o walkthrough contra ela: o `clancy` editando a `alice` agora leva `403`, devolvido antes de qualquer escrita, então o registro da `alice` fica intocado; o `clancy` editando o **próprio** registro continua levando `200`, então a feature funciona pra quem é dono do registro; e token ausente ou ruim continua levando `401`. O ownership check roda antes da busca, então um não-dono leva o mesmo `403` pra um handle que não existe. Repare no status: `403`, não o `404` que os átomos de API1 devolvem pra um pedido fora do seu escopo — lá o `404` escondia a existência de um pedido num espaço de ids enumerável; aqui o check compara o handle do path com o caller antes de qualquer busca, então não revela existência nenhuma a esconder. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) trabalha o porquê.
