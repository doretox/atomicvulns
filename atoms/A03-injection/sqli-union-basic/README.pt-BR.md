# sqli-union-basic — SQL Injection UNION-based

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para SQL injection clássica via UNION. Um endpoint de "busca de perfil" concatena o parâmetro `username` direto numa query SQL, permitindo ao atacante anexar um `UNION SELECT` e exfiltrar linhas de uma tabela vizinha `secrets` (password hashes, API keys) que a feature nunca pretendeu expor.

## Run

```bash
cd atoms/A03-injection/sqli-union-basic
docker compose up --build
```

- App vulnerable: <http://127.0.0.1:8001/>
- App fixed: <http://127.0.0.1:8101/>

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8101 atende a mesma feature com os mesmos dados de seed. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela — cada um deve retornar tabela vazia ou apenas a linha legítima da Alice, nunca os secrets exfiltrados.
