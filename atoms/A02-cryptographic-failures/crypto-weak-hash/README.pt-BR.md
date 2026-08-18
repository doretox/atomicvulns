# crypto-weak-hash — Insecure password storage (weak hashing)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask para a falha de armazenamento de senha mais comum: a app guarda a senha de cada usuário como um **MD5 sem salt**. Um hash é mão-única (one-way) — você não descriptografa —, mas MD5 é um hash *rápido e de propósito geral*, e usado sem salt a mesma senha sempre produz o mesmo digest. Esse é o primitivo errado para senha: quando o hash vaza (num dump de banco, por exemplo), ele é trivialmente **recuperável**. Você não inverte o hash — você chuta senhas, hasheia e compara, em escala. Este átomo faz isso com uma **rainbow table**: uma tabela pré-computada de hash→senha que cobre um keyspace inteiro. A senha recuperada te loga direto como a vítima.

Este é o irmão do [`jwt-weak-secret`](../jwt-weak-secret/), e o contraste é a lição. Os dois quebram um artefato criptográfico offline — mas lá você quebra um *segredo de assinatura* (por dicionário) para **forjar** tokens seus; aqui você recupera uma *senha armazenada* (por rainbow table) para **logar como o usuário real**. Artefato diferente, consequência diferente, técnica diferente: um segredo de assinatura é integridade, um hash de senha armazenado é confidencialidade; um ataque de dicionário hasheia cada chute ao vivo, uma rainbow table pré-computa o trabalho de uma vez. O fix não é "um hash mais forte" nem "só adicionar um salt" — é um **primitivo** diferente: bcrypt, um KDF (key derivation function) de senha, lento e salgado.

> **Teoria primeiro:** Leia [OWASP: Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; o cheat sheet explica *o que* é
> armazenamento seguro de senha — KDFs lentos e salgados — e por que importa.
> (A Web Security Academy da PortSwigger, a fonte usual de primer deste repo,
> é focada em ataque e não tem página conceitual sobre password storage, então
> este átomo aponta para a orientação canônica da OWASP.)

## Nota de stack — single-container SQLite, e os dois lados diferem nas dependências

Cada lado é um único container Flask com seu próprio `lab.db` efêmero, semeado no boot — não há datastore separado. Uma coisa é incomum para este repo: `vulnerable/` e `fixed/` **não** compartilham o `requirements.txt`. O lado vulnerável hasheia com a biblioteca padrão (`hashlib`); o lado corrigido adiciona uma dependência — `bcrypt`. O fix *é* o primitivo, e o primitivo traz uma biblioteca.

## Só API — sem HTML, sem browser

Não há UI web: sem templates, toda resposta é JSON. Você opera este átomo pelo **Burp Suite (Repeater)** para provar o login, e por um **terminal** para rodar o crack offline com o RainbowCrack (`rtgen` / `rtsort` / `rcrack`) — a mesma divisão que você usaria num engagement real, porque quebrar um hash é algo que o Burp não faz. Não há trilha de browser.

## O ponto de partida — um hash vazado

O ataque assume que você já tem a tabela `users` de um **dump de banco** — não importa como vazou. A app nunca expõe o hash por HTTP (isso seria uma segunda vulnerabilidade, separada); o `WALKTHROUGH.md` te entrega a linha dumpada `admin:<md5>` como ponto de partida. Dali em diante, tudo é offline.

## Como rodar

Da raiz do repo:

```bash
./atom up crypto-weak-hash
```

- API vulnerável: `http://127.0.0.1:8031`
- API corrigida: `http://127.0.0.1:8131`

Não há landing page além de um banner JSON em `/` — o ponto de entrada é `POST /login` (veja `WALKTHROUGH.md`). Pare com `./atom down crypto-weak-hash`. Se preferir Docker puro: `cd atoms/A02-cryptographic-failures/crypto-weak-hash && docker compose up --build`.

## O que ler em seguida

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo: o Burp confirma o login, o terminal constrói uma rainbow table (você vê o `rtgen` fazendo a pré-computação) e recupera a senha, e então a senha recuperada te loga. Sem trilha de browser.
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão corrigida

A API corrigida na porta 8131 guarda a **mesma** senha (`adm1n`) como um **bcrypt salgado** (`$2b$...`) em vez de um MD5 sem salt. Mesma lógica de login, mesmos endpoints — só o primitivo de armazenamento muda. Contra um hash bcrypt a rainbow table não é "mais lenta", é **inaplicável**: um hash salgado não tem tabela pré-computada para construir (o RainbowCrack sequer oferece bcrypt), então não há onde procurar o hash. O bcrypt também é lento de propósito, encarecendo *qualquer* ataque de adivinhação. Veja [`DIFF.md`](./DIFF.md) para entender por que "só adicionar um salt" e "usar SHA-256" são, os dois, o fix errado.
