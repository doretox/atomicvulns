# command-injection-basic — OS Command Injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para OS command injection clássica. Uma "ferramenta de ping de rede" concatena o parâmetro `host` da query string numa string de comando de shell (`ping -c 1 <host>`) e a roda via `subprocess.run(shell=True)`, devolvendo o output na resposta. Como um shell parseia a string montada, um atacante que anexa um metacaractere de shell — `host=127.0.0.1; whoami` — consegue executar um segundo comando no servidor e receber o output de volta na página. O shell é um sink novo: onde o `sqli-union-basic` mandava input pra uma SQL engine, aqui manda pro `/bin/sh`, e o impacto escala de exfiltração de dado para remote code execution no host.

> **Teoria primeiro:** Leia [PortSwigger: OS command injection](https://portswigger.net/web-security/os-command-injection)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up command-injection-basic
```

- App vulnerable: <http://127.0.0.1:8009/>
- App fixed: <http://127.0.0.1:8109/>

Pare com `./atom down command-injection-basic`. Se preferir Docker cru: `cd atoms/A03-injection/command-injection-basic && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8109 atende a mesma ferramenta de ping. Ela troca a string de shell por uma lista de argumentos — `subprocess.run(["ping", "-c", "1", host])` — então `host` é sempre um argumento único e inerte, e nunca chega a um shell pra ser parseado. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela: cada um volta como `ping: <host>: Name or service not known`, sem nenhum comando injetado executado e nada vazado.
