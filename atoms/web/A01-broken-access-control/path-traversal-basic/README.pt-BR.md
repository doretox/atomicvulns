# path-traversal-basic — Path Traversal

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para path traversal clássico. Um "file viewer" junta o parâmetro `file` da query string a um diretório base com `os.path.join(BASE_DIR, file)` e dá `open()` no resultado, devolvendo o conteúdo do arquivo na resposta. Nada confina esse caminho ao diretório base, então um atacante que manda `file=../../../../etc/passwd` sai da pasta e lê um arquivo arbitrário do servidor — o conteúdo volta direto na página. Isto é **A01, não injection**: nada vira código, um nome de arquivo de aparência legítima simplesmente conduz a app a um recurso fora do seu escopo. É o gêmeo por mecânica do `command-injection-basic` — os dois terminam em `/etc/passwd`, mas por caminhos opostos. Lá você fez a app *rodar um comando* (`cat`); aqui você faz a app *abrir um arquivo*, usando a capacidade de ler-arquivo que ela já tinha, só que apontada pra fora do próprio quintal. Um é execução, o outro é navegação — e como este só lê, o impacto é **arbitrary file read** (source, config, credenciais), não o remote code execution do gêmeo.

> **Teoria primeiro:** Leia [PortSwigger: Path traversal](https://portswigger.net/web-security/file-path-traversal)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — arquivos no disco, sem banco

Diferente do `sqli-union-basic`, este átomo não tem banco. O "dado" dele é um punhado de arquivos de texto reais num diretório `files/` (`notes.txt`, `readme.txt`) que a app deveria servir. Esse diretório é o ponto todo: ele dá o baseline legítimo (ler um arquivo que a app oferece) e o sandbox de onde o atacante escapa. O loot aqui não é uma tabela — é o próprio filesystem. A escolha de storage em cada átomo segue a superfície do bug.

## Como rodar

Da raiz do repo:

```bash
./atom up path-traversal-basic
```

- App vulnerable: <http://127.0.0.1:8010/>
- App fixed: <http://127.0.0.1:8110/>

Pare com `./atom down path-traversal-basic`. Se preferir Docker cru: `cd atoms/A01-broken-access-control/path-traversal-basic && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8110 atende o mesmo file viewer. Ela resolve o caminho requisitado com `os.path.realpath` e confirma que o resultado ainda cai dentro do diretório base (`path.startswith(base + os.sep)`) antes de abrir — senão retorna **404**. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela: `../../../../etc/passwd`, o `/etc/passwd` absoluto e `../app.py` todos voltam **404**, enquanto `notes.txt` continua retornando 200. Um único check mata toda rota de traversal — a prova de que eram o mesmo bug.
