# sqli-second-order — Second-order SQL injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab mínimo em Flask + SQLite para second-order SQL injection. O app tem dois fluxos. O cadastro — `POST /register` — grava um username por um `INSERT` **seguro, parametrizado**, então um payload SQL no username é escrito como valor literal e nada acontece. Depois, um fluxo autenticado de troca de senha — `POST /change-password` — relê esse username do banco e o **concatena cru** numa segunda query, um `UPDATE`. Então um username-payload plantado no cadastro fica dormente na tabela e detona no *segundo* fluxo: ele reescreve qual linha o `UPDATE` atinge, deixando um atacante trocar a senha de outra conta.

A lição é que parametrizar o input no ponto de **entrada** não te protege se você o desparametriza no ponto de **uso**. A query do cadastro nunca foi o problema — ela é segura. O bug é que um valor relido do banco é tratado como confiável só porque veio do banco, e **toda leitura do banco é input não-confiável de novo**. O fix não é sanitizar nem validar o username no cadastro — é **parametrizar a segunda query também**, para que o valor relido entre como dado e nunca vire sintaxe SQL.

> **Teoria primeiro:** Leia [PortSwigger: Second-order SQL injection](https://portswigger.net/web-security/sql-injection#second-order-sql-injection)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — SQLite embutido, gravável e efêmero

Como os outros átomos de SQL injection (`sqli-union-basic` e os irmãos blind), este átomo embute o SQLite como um arquivo dentro do processo — não há datastore externo, e cada lado (`vulnerable` e `fixed`) roda como um único container com seu próprio `lab.db`, semeado no boot. Uma diferença importa: aqueles átomos são read-only (`SELECT`), mas este **escreve** — `POST /register` faz um `INSERT` e `POST /change-password` faz um `UPDATE`. O banco é **efêmero**: ele vive dentro do container, sem volume persistente. Como o exploit muta o banco (ele troca a senha de outra conta), **para rodar o ataque de novo do zero, derrube e suba o átomo** — `./atom down sqli-second-order && ./atom up sqli-second-order` recria o container e re-semeia um banco limpo; senão o baseline semeado não vale mais. Os apps dependem só de `Flask`; o `sqlite3` está na standard library, e o cookie de sessão usa a assinatura nativa do Flask.

## API only — sem HTML, sem browser

Este átomo não tem UI web: sem templates, sem landing page, toda resposta é JSON. Você opera tudo pelo **Burp Suite (Repeater)** ou por `curl`, e a prova é uma resposta de login — nada executa num browser. O `WALKTHROUGH.pt-BR.md` trabalha exclusivamente no Burp.

## Como rodar

Da raiz do repo:

```bash
./atom up sqli-second-order
```

- API vulnerable: `http://127.0.0.1:8029`
- API fixed: `http://127.0.0.1:8129`

O `GET /` devolve um banner de aviso; os fluxos são `POST /register`, `POST /login` e `POST /change-password` (veja o `WALKTHROUGH.pt-BR.md`). Pare com `./atom down sqli-second-order`. Se preferir Docker cru: `cd atoms/A03-injection/sqli-second-order && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

O app corrigido na porta 8129 atende os mesmos três fluxos contra os mesmos dados de seed. Ele muda uma coisa — o `UPDATE` no `POST /change-password` passa o username relido como parâmetro (`WHERE username = ?`) em vez de concatená-lo — e nada mais. Replay o walkthrough contra ele: registrar o username `admin'--` e rodar o change-password agora atualiza só a *própria* linha do atacante, então logar como `admin` com a senha nova do atacante retorna `401`, e a senha original do `admin` continua funcionando.
