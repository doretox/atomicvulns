# weak-password-reset — Predictable password-reset token

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask para um fluxo de password reset cujo token é **previsível**. Quando um usuário esquece a senha, a app emite um **reset token** — uma string secreta que ela "envia por e-mail" ao dono da conta —, e quem apresentar esse token pode definir uma nova senha. O token é uma **credencial temporária**: tê-lo *é* a autorização para trocar a senha. O fluxo em si está correto. A falha é *como* o token é gerado: com o módulo `random` do Python, **seedado com o relógio** (`random.seed(int(time.time()))`). `random` é um PRNG (pseudo-random number generator) — determinístico a partir do seed —, e o seed é o horário do servidor em segundos inteiros, um valor que o atacante lê direto do header HTTP `Date` da resposta. Re-seede com ele, rode o mesmo gerador, e você reproduz o token da vítima byte a byte, reseta a senha dela e loga como ela. Não se quebra cripto nem se injeta nada — o segredo simplesmente não é secreto.

Este é o irmão do [`session-fixation`](../session-fixation/), e o contraste é a lição. Os dois são **A07 — Identification and Authentication Failures**, e os dois giram em torno de uma credencial que identifica um usuário sem nunca ser roubada. Mas lá o session id é *forte* (`secrets.token_urlsafe`) e o bug é o **ciclo de vida** dele — ele sobrevive ao login; aqui o reset token é *fraco* — **previsível** — e essa previsibilidade **é** o bug. (A própria nota "o que a vuln NÃO é" do session fixation diz que um id fraco e previsível "seria um bug diferente"; este átomo é esse bug.) O fix não é um fluxo mais forte nem um token mais longo — é um **gerador** diferente: `secrets.token_urlsafe`, um CSPRNG (cryptographically secure PRNG), somado a single-use e a uma expiração curta.

> **Teoria primeiro:** Leia [PortSwigger: Vulnerabilities in other authentication mechanisms](https://portswigger.net/web-security/authentication/other-mechanisms)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — single-container SQLite, e os dois lados compartilham as dependências

Cada lado é um único container Flask com seu próprio `lab.db` efêmero, semeado no boot com dois usuários — não há datastore separado. Os reset tokens vivem num dict em memória (um token de curta vida não precisa de banco), a mesma forma que o `session-fixation` usa para o store de sessão. Diferente do `crypto-weak-hash`, cujo fix traz uma biblioteca, o fix aqui não muda nada no `requirements.txt`: `random` e `secrets` são ambos biblioteca padrão, então as dependências dos dois lados são byte-idênticas e a diferença inteira é um gerador no `app.py`.

## Só API — sem HTML, sem browser

Não há UI web: sem templates, toda resposta é JSON. Você opera este átomo pelo **Burp Suite (Repeater)** — pede o reset da vítima, lê o header `Date`, roda um pequeno **script preditor local** que reproduz o token (a única coisa que o Burp não faz — do mesmo jeito que um browser roda JavaScript para um bug client-side, a ferramenta que reproduz o token entra na trilha principal), reseta a senha e loga como a vítima. Não há trilha de browser; a prova é a resposta do login.

## As senhas são hasheadas direito — de propósito

As senhas dos usuários semeados são guardadas com um hash decente e salgado (`werkzeug.security.generate_password_hash`), não MD5/SHA-1. Isso é deliberado: *armazenamento* de senha é outro átomo ([`crypto-weak-hash`](../../A02-cryptographic-failures/crypto-weak-hash/)), e este lab tem que carregar exatamente uma falha — o gerador do reset token. O login e o fluxo de reset estão corretos; só o token é previsível.

## Como rodar

Da raiz do repo:

```bash
./atom up weak-password-reset
```

- API vulnerável: `http://127.0.0.1:8037`
- API corrigida: `http://127.0.0.1:8137`

Não há landing page além de um banner JSON em `/` — os pontos de entrada são `POST /forgot`, `POST /reset` e `POST /login` (veja `WALKTHROUGH.md`). Pare com `./atom down weak-password-reset`. Se preferir Docker puro: `cd atoms/A07-auth-failures/weak-password-reset && docker compose up --build`.

## O que ler em seguida

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo via Burp Suite: pedir o reset da vítima, prever o token pelo header `Date`, resetar a senha e logar como a vítima. Trilha principal, sem browser.
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão corrigida

A API corrigida na porta 8137 serve o **mesmo** fluxo — mesmos endpoints, mesma "entrega por e-mail", mesmo login — mas gera o reset token com `secrets.token_urlsafe(32)`, um CSPRNG, e o torna single-use com uma expiração curta. Repita o ataque contra ela: o header `Date` ainda te diz o segundo, mas re-seedar o `random` não reproduz mais nada — o token veio de `os.urandom`, não de um PRNG seedado com o relógio —, então o `POST /reset` rejeita todo token previsto e o takeover falha. O token previsto é recusado como desconhecido *antes* de single-use ou expiração sequer entrarem em jogo: a mudança decisiva é o gerador imprevisível. Veja [`DIFF.md`](./DIFF.md).
