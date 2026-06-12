# sqli-blind-time — Blind SQL Injection (time-based)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para time-based blind SQL injection. Um endpoint de login concatena os campos `username` e `password` (vindos via POST) numa string SQL — mas a resposta é *sempre a mesma página* (`Login attempt processed.`), com credencial válida ou não. Não há oráculo no body: um dev achatou as duas mensagens para impedir enumeration de usuário, o que matou o canal boolean-based mas deixou a injeção no lugar. A única coisa que ainda varia é o **tempo**. Injetando uma condição que dispara uma computação cara no SQLite *só quando ela é verdadeira*, o atacante lê a senha da alice (`wonderland`) um caractere por vez a partir da latência da resposta — sem ela, ou qualquer diferença na resposta que não seja o relógio, jamais aparecer na página.

> **Teoria primeiro:** Leia [PortSwigger: Blind SQL injection](https://portswigger.net/web-security/sql-injection/blind)
> antes de fazer este átomo — em especial a seção sobre disparar
> time delays. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela
> é e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up sqli-blind-time
```

- App vulnerable: <http://127.0.0.1:8007/>
- App fixed: <http://127.0.0.1:8107/>

Pare com `./atom down sqli-blind-time`. Se preferir Docker cru: `cd atoms/A03-injection/sqli-blind-time && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (Repeater → Intruder), lendo a coluna de latency como oráculo.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8107 atende a mesma feature de login contra os mesmos usuários de seed, e mantém a mesma resposta uniforme `Login attempt processed.` — aquela mensagem achatada era anti-enumeration legítimo, não o bug. Ela usa uma query parametrizada, então todo payload do `WALKTHROUGH.pt-BR.md` volta instantâneo, inclusive o probe incondicional do Step 1: sem delay controlável, o canal de timing some. Mesma root cause e mesmo fix de [`sqli-union-basic`](../sqli-union-basic/) e [`sqli-blind-boolean`](../sqli-blind-boolean/) — só o que o atacante consegue observar mudou.
