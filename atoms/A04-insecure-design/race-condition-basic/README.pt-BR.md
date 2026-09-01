# race-condition-basic — Time-of-check to time-of-use (TOCTOU) race condition

> ⚠️ Intencionalmente vulnerável. Rode apenas localmente. Nunca exponha à internet ou a uma rede compartilhada.

Um laboratório mínimo de Flask + PostgreSQL pra uma falha que se esconde em lógica de negócio comum: uma API de conta cujo `POST /withdraw` **lê** o seu saldo, **checa** em Python se ele cobre o valor, e então **escreve** o débito — em três passos separados. Entre o checar e o escrever há uma fresta de tempo. Dispare um saque de cada vez e nada dá errado. Dispare vinte saques do saldo inteiro *no mesmo instante* e todos os vinte leem o saldo cheio, todos os vinte passam pela checagem antes de qualquer um escrever, e todos os vinte debitam. Você saca vinte vezes um dinheiro que só cobria um saque, e o saldo fica negativo.

Nada na requisição do atacante é malicioso. Ela é **byte a byte idêntica** a um saque legítimo — um valor normal que o saldo cobre. A única diferença entre o uso comum e o ataque é a **concorrência**: várias cópias da mesma requisição chegando juntas. Isto é uma **race condition** do tipo **time-of-check to time-of-use (TOCTOU)** — a verdade que você checou (o saldo cobre) fica velha no instante em que você age sobre ela (debita), porque outra requisição mudou o saldo na fresta entre os dois. O fix *não* é "checar de novo" — uma segunda checagem tem a mesma fresta. É tornar o checar-e-agir **atômico**: deixar o banco decidir *e* escrever num único statement que ele serializa por linha.

> **Teoria primeiro:** Leia [PortSwigger: Race conditions](https://portswigger.net/web-security/race-conditions)
> antes de fazer este átomo — ela cobre as falhas de time-of-check to time-of-use,
> o padrão "limit overrun" (o próprio exemplo dela é sacar dinheiro além do saldo da
> conta, exatamente este lab), e o single-packet attack que você usa pra ganhar a
> corrida. Os átomos deste repo mostram *como* uma vulnerabilidade acontece no
> código; a Academy explica *o que* ela é e por que importa.

Este átomo mora em **A04 — Insecure Design**. O bug não é input virando código (isso é injection — e aqui não há input malicioso nenhum), nem um check de dono ausente, nem um primitivo de crypto fraco. É um defeito no **desenho do fluxo**: "decidir a partir de um valor, depois agir sobre esse valor" foi construído como dois passos separados sem garantir que aconteçam de forma indivisível, então requisições concorrentes escorregam entre eles e quebram um invariante de negócio (nunca sacar além do saldo). Essa ausência de input malicioso é o que separa este átomo de todos os anteriores. No [`sqli-union-basic`](../../A03-injection/sqli-union-basic/) e nos outros átomos de injection a requisição carrega um payload; no [`idor-numeric-id`](../../A01-broken-access-control/idor-numeric-id/) ela carrega um número trocado. Aqui a requisição não carrega **nada diferente** — só o timing dela muda.

## Nota de stack — um PostgreSQL de verdade, e threads

O lab roda **três containers**: um `db` compartilhado (PostgreSQL) mais `vulnerable` e `fixed`, ambos lendo a mesma conta semeada. O serviço `db` **não tem porta no host** — é alcançável só na rede interna do compose (`db:5432`), nunca publicado na sua máquina; só os dois apps bindam em `127.0.0.1`. A tabela `accounts` é semeada no primeiro boot com uma conta fake (`id = 1`, `balance = 100`) — dado de lab. Duas escolhas tornam a corrida fiel e reprodutível: o datastore é **PostgreSQL, não SQLite** (o SQLite serializa as escritas atrás de um lock do banco inteiro, o que *esconderia* a corrida — o Postgres dá concorrência real por linha), e o Flask roda **multi-threaded** (`threaded=True`), porque concorrência de verdade é pré-requisito pra uma corrida existir. Cada requisição abre a própria conexão ao banco, então vinte saques simultâneos viram vinte sessões concorrentes no banco.

## A prova é um número — e você precisa do Turbo Intruder do Burp

Você conduz este átomo pelo **Burp**, mas com uma ferramenta além da usual: o **Turbo Intruder** (uma extensão gratuita do BApp Store). O ataque é concorrência, e nem o Repeater (uma requisição por vez) nem o Intruder padrão ganham uma corrida de forma confiável — a rede *serializa* as requisições, então o primeiro débito acontece antes de o segundo sequer checar. O **single-packet attack** do Turbo Intruder faz N requisições chegarem juntas, neutralizando esse jitter. Este é um desvio deliberado e declarado da trilha "Burp puro" usual do repo, e é necessário: uma corrida só reproduz com requisições genuinamente simultâneas. A prova é um **número** único e inequívoco — o saldo final, negativo no app vulnerable e correto no fixed.

## Como rodar

Da raiz do repo:

```bash
./atom up race-condition-basic
```

- API vulnerable: `http://127.0.0.1:8035`
- API fixed: `http://127.0.0.1:8135`

`GET /` devolve um banner de aviso; o ponto de entrada é `POST /withdraw` com um corpo JSON `{"amount": 100}`, `POST /reset` restaura o saldo pra 100 entre tentativas, e `GET /balance` mostra o número corrente. O container `db` nunca é publicado — só os dois apps são. Pare com `./atom down race-condition-basic`. Se preferir Docker cru: `cd atoms/A04-insecure-design/race-condition-basic && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — passo a passo: confirme que o guard funciona uma requisição por vez, depois dispare uma rajada de saques idênticos com o Turbo Intruder e veja o saldo ir a `-1900`. Depois a mesma rajada contra o app fixed deixa exatamente um passar.
2. [`DIFF.md`](./DIFF.md) — o diff de uma-operação entre `vulnerable/` e `fixed/`, e por que "checar de novo", um lock na aplicação, e o `SERIALIZABLE` são a resposta errada, parcial, ou mais pesada ao lado do `UPDATE` condicional.

## Versão corrigida

O app corrigido na porta 8135 serve o mesmo saque contra o mesmo banco semeado. Ele muda uma coisa: o débito vira um único **`UPDATE` condicional** — `UPDATE accounts SET balance = balance - :amount WHERE id = 1 AND balance >= :amount` — e checa quantas linhas mudaram (`rowcount`): 1 significa que debitou, 0 significa que o saldo não cobria (`409`). A condição e a escrita agora são o *mesmo* statement, que o Postgres serializa por linha: ele trava a linha, re-checa `balance >= amount` contra o valor corrente, e escreve, sem fresta pra outra requisição escorregar. Não há read separado, então não há sleep. Repita o walkthrough contra ele: um saque único ainda funciona idêntico, mas a rajada concorrente agora deixa **exatamente um** saque passar e o saldo para em `0`.
