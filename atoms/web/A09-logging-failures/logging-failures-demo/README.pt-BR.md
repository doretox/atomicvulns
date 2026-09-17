# logging-failures-demo — Missing security logging of authentication failures

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab Flask mínimo para a única classe de vulnerabilidade em que **a falha é algo que *não* acontece**. A app é uma API de login minúscula: `POST /login` recebe um email e uma senha, compara com um password hash guardado, e responde `200 {"authenticated": true}` ou `401 {"authenticated": false}`. O login está correto — uma query parametrizada, senhas hasheadas decentemente, um `401` limpo para senha errada. Agora aponte um **brute-force** contra ele — um atacante martelando uma conta com senha atrás de senha. Cada tentativa falha *é* um **security event** (algo que um time de segurança precisa saber), mas no lado vulnerable o caminho da falha não registra **nada** de segurança. O que sobra é o **access log** HTTP genérico do servidor — uma linha por request (método, path, status, IP de origem), que captura o *transporte*, não o significado de segurança: ele não carrega a conta-alvo (o email vai no corpo, não na URL), nunca rotula o `401` como falha de autenticação, e nunca agrega. Vinte tentativas de invasão parecem exatamente vinte usuários errando a senha. O ataque acontece e ninguém vê.

Isto é **A09 — Security Logging and Monitoring Failures**: a categoria sobre conseguir *saber* que um ataque aconteceu — detectá-lo, respondê-lo, e reconstruí-lo depois. Diferente de todos os outros átomos deste repo, a prova **não é algo aparecendo** — sem arquivo marcador, sem dado vazado, sem account takeover. É o **contraste entre dois logs**: rode a *mesma* rajada de brute-force contra os dois lados e compare os `docker compose logs`. O lado vulnerable é **cego** (só o access log genérico); o lado fixed acrescenta uma linha de **security log estruturada** para cada falha — legível por um humano e parseável por uma máquina — e um **WARNING de brute-force** claro assim que as falhas cruzam um limiar. O fix é *gerar o security log que falta*: ele loga o **fato** de cada falha (o evento, a conta-alvo, o IP de origem, o timestamp) e **nunca o segredo** (a senha tentada fica fora do log). Ele **não** é rate-limiting — o lado fixed **detecta e registra** o ataque, ele não o **bloqueia** (toda tentativa ainda responde `401`). A09 é sobre **visibilidade, não prevenção**.

> **Teoria primeiro:** Leia [OWASP: A09:2021 – Security Logging and Monitoring Failures](https://owasp.org/Top10/2021/A09_2021-Security_Logging_and_Monitoring_Failures/)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; o OWASP explica *o que* esta categoria é e
> por que importa. (Diferente da maioria dos átomos, o primer aqui é o OWASP, não a
> PortSwigger Web Security Academy: a Academy organiza os tópicos por *classe* de
> vulnerabilidade explorável, e logging-e-monitoring é uma categoria de
> detecção/observabilidade pra qual ela não tem uma página conceitual dedicada.)

Para o lado prático — que eventos registrar e, tão importante quanto, o que manter *fora* de um log — o [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) é a referência companheira: ele lista falhas de autenticação entre os eventos a logar, e senhas, session tokens e segredos entre os dados a excluir.

## Nota de stack — SQLite single-container, e os dois lados compartilham dependências

Cada lado é um único container Flask com seu próprio `lab.db` efêmero, semeado no boot com dois usuários — não há datastore separado. No lado fixed o contador de falhas por conta vive num dict em memória (um contador de vida curta não precisa de banco), o mesmo formato que o [`session-fixation`](../../A07-auth-failures/session-fixation/) usa pro seu store de sessão. O fix não muda nada no `requirements.txt`: `logging` é standard library, então as dependências dos dois lados são byte-idênticas e a diferença inteira é o security logging no `app.py`. (Contraste com o [`cve-demo`](../../A06-vulnerable-components/cve-demo/), onde o diff inteiro era uma linha do `requirements.txt`; aqui o diff é código.)

## Só API — sem HTML, sem browser

Não há UI web: sem templates, toda resposta é JSON. Você conduz este átomo pelo **Burp Suite** — mande a rajada de brute-force contra o `POST /login` com o **Intruder** (ou um request repetido no **Repeater**): uma lista de senhas erradas contra uma conta. A prova é lida **fora** do Burp, na saída do servidor: compare `docker compose logs vulnerable` (cego) com `docker compose logs fixed` (a trilha de segurança mais o WARNING). Não há trilha browser — a prova é texto de log, não uma tela.

## O login está correto — de propósito

O login é **idêntico nos dois lados** e correto: uma query parametrizada (sem SQL injection), um password hash salgado decente (`werkzeug.security.generate_password_hash`, não MD5/SHA-1 — password *storage* é outro átomo, [`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/)), e um `200`/`401` limpo. Este lab carrega exatamente uma falha: o lado vulnerable não **loga** a falha de autenticação. O lado fixed acrescenta só esse logging — ele **não** adiciona rate-limiting nem lockout, e **não** loga a senha tentada. Detecção, não prevenção; o fato, não o segredo.

## Como rodar

A partir da raiz do repo:

```bash
./atom up logging-failures-demo
```

- API vulnerável: `http://127.0.0.1:8038`
- API corrigida: `http://127.0.0.1:8138`

`GET /` devolve um banner JSON; a rota-alvo é `POST /login`. Para ver a vulnerabilidade, rode uma rajada de logins falhos contra uma conta e compare os logs dos dois lados:

```bash
docker compose logs vulnerable   # cego: só linhas de acesso "POST /login 401" genéricas
docker compose logs fixed        # vê: uma linha de segurança por falha + um WARNING de brute-force
```

Pare com `./atom down logging-failures-demo`. Se preferir Docker puro: `cd atoms/A09-logging-failures/logging-failures-demo && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — passo a passo pelo Burp Suite: rode a mesma rajada de brute-force contra os dois lados e leia os dois logs lado a lado — o vulnerable cego, o fixed com a trilha de segurança e o WARNING. Trilha principal, sem browser.
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão corrigida

A API corrigida na porta 8138 serve o **mesmo** login — mesma query, mesmo hash check, mesmo `200`/`401` — mas no caminho da falha emite um security event estruturado (`authentication failure account=… ip=…`, nunca a senha) e, após cinco falhas consecutivas contra uma conta, um `WARNING … possible brute-force …`. Repita a rajada contra ela: toda tentativa ainda responde `401` — o ataque **não é bloqueado** — mas agora cada falha está registrada e o WARNING nomeia a conta e a origem. O mesmo ataque que era invisível na 8038 é visível e investigável na 8138. A mudança é pura **observabilidade**: detecção, não prevenção. Veja o [`DIFF.md`](./DIFF.md).
