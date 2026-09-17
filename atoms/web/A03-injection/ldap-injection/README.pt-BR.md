# ldap-injection — LDAP injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask + OpenLDAP para LDAP injection. Um endpoint de login corporativo — `POST /login` — recebe um `user` e um `password` e os autentica contra um diretório LDAP: monta um filtro de busca e considera você logado se a busca retorna alguém — `(&(uid=<user>)(userPassword=<password>))`. O detalhe é que um filtro de busca LDAP não é texto inerte — é **estrutura** (RFC 4515), e caracteres como `*`, `(`, `)` e `\` são *sintaxe*, não dado. O endpoint cola o que o cliente mandou direto nesse filtro, então esses metacaracteres são interpretados como lógica do filtro. Mande `*` como senha e o filtro vira `(&(uid=admin)(userPassword=*))` — "um `admin` que simplesmente *tem* uma senha" — e você loga como `admin` sem conhecê-la.

A lição é que a causa raiz é **concatenar input não-confiável no filtro sem escapá-lo**: o valor deixa de ser valor e vira estrutura do filtro. O fix não é validar nem colocar caracteres "estranhos" numa blocklist — é **escapar os metacaracteres da RFC 4515** (`escape_filter_chars`) em cada valor não-confiável antes de montar o filtro, para que `*` `(` `)` `\` virem dado literal (`\2a` `\28` `\29` `\5c`) e o filtro continue sendo o que o código pretendia.

> **Teoria primeiro:** Leia [PortSwigger: LDAP injection](https://portswigger.net/kb/issues/00100500_ldap-injection)
> antes de fazer este átomo, e passe os olhos no [OWASP LDAP Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LDAP_Injection_Prevention_Cheat_Sheet.html)
> para a defesa. Os átomos deste repo mostram *como* uma vulnerabilidade
> acontece no código; essas referências explicam *o que* ela é e por que importa.

## Nota de stack — um diretório OpenLDAP de verdade

Diferente dos átomos de SQL injection (`sqli-union-basic` e os irmãos blind), que embutem o SQLite como um arquivo dentro do processo, este átomo precisa de um *servidor* de diretório de verdade: OpenLDAP. Então o lab roda **três containers** — um `ldap` compartilhado, mais `vulnerable` e `fixed`, os dois consultando o mesmo diretório semeado. O serviço `ldap` **não tem porta no host**: ele é alcançável só na rede interna do compose (`ldap://ldap:389`), nunca publicado na sua máquina — só os dois apps bindam em `127.0.0.1`. Os apps falam com ele usando o **`ldap3`**, um cliente LDAP puro Python (escolhido em vez do `python-ldap` para não precisar do `libldap` nativo nem de toolchain de build). O diretório é semeado com dois usuários fake (`admin`, `jdoe`) cujas senhas são guardadas em plaintext — uma simplificação de lab para o match ingênuo `(userPassword=<valor>)` funcionar; password storage é ortogonal ao fix de LDAP injection (veja o `DIFF.pt-BR.md`). Os apps bindam como uma **service account de baixo privilégio** (`cn=svc`), não o admin do diretório, para que o bypass que você vai ver seja LDAP injection e não uma conexão com privilégio excessivo.

## API only — sem HTML, sem browser

Este átomo não tem UI web: sem templates, sem landing page, toda resposta é JSON. Você opera tudo pelo **Burp Suite (Repeater)** ou por `curl`, e a prova é a própria resposta do login — nada executa num browser. O `WALKTHROUGH.pt-BR.md` trabalha exclusivamente no Burp.

## Como rodar

Da raiz do repo:

```bash
./atom up ldap-injection
```

- API vulnerable: `http://127.0.0.1:8028`
- API fixed: `http://127.0.0.1:8128`

O `GET /` devolve um banner de aviso; o ponto de entrada é `POST /login` (veja o `WALKTHROUGH.pt-BR.md`). O container `ldap` nunca é publicado — só os dois apps são. Pare com `./atom down ldap-injection`. Se preferir Docker cru: `cd atoms/A03-injection/ldap-injection && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

O app corrigido na porta 8128 atende o mesmo login contra o mesmo diretório. Ele adiciona uma coisa — `escape_filter_chars` em volta de `user` e `password` antes de montar o filtro — e não muda mais nada. Replay o walkthrough contra ele: a credencial real em string continua logando com `200`, e o payload `*` que passou no app vulnerable agora retorna `401`, porque o metacaractere é escapado para o literal `\2a` e não pode mais ser estrutura do filtro.
