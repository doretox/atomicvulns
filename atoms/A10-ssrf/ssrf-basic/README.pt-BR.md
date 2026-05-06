# ssrf-basic — Server-Side Request Forgery (basic)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para SSRF clássico. A app expõe uma feature de "URL preview" — você cola uma URL, o servidor faz o fetch dela, e você recebe o corpo da resposta de volta, igual um app de chat que mostra um preview quando você compartilha um link. O servidor nunca valida qual URL ele está sendo mandado buscar, então a mesma feature que o atacante usa pra preview de `https://api.github.com/zen` também funciona pra alcançar `http://internal/` — um host numa rede Docker privada que o atacante não consegue tocar direto.

Este é o primeiro átomo do projeto em que o **servidor em si** é quem faz o request de saída. Em `sqli-union-basic`, `xss-reflected` e `idor-numeric-id`, o atacante mandava um payload que a app processava localmente. Em SSRF o atacante manda uma *URL*, e a app por conta própria faz um request HTTP *pra essa URL*. A forma da ameaça muda: agora o alcance do atacante é igual ao alcance do servidor — serviços internos, endpoints de cloud metadata, qualquer coisa que a rede do servidor enxerga.

## Estrutura do lab — três containers

Este é também o primeiro átomo multi-container. Três serviços sobem num único `docker-compose.yml`:

- **`vulnerable`** — a app de URL preview quebrada, publicada em `127.0.0.1:8004`.
- **`fixed`** — a versão corrigida, publicada em `127.0.0.1:8104`.
- **`internal`** — um "dashboard admin corporativo" fake, devolvendo API keys inventadas, URLs de banco e uma tabelinha de usuários. **É parte deste lab, não é um sistema real.** Intencionalmente não é publicado no host (sem `ports:`); só é alcançável de dentro das redes Docker que o lab cria. Tentar abrir direto no browser (e.g. `curl http://localhost`) não funciona — esse é o ponto. O serviço `internal` é o *alvo* do SSRF; alcançá-lo *através* da app vulnerável é o que o walkthrough demonstra.

As apps `vulnerable` e `fixed` ficam em redes Docker **separadas**; as duas compartilham a rede com `internal`. Então `internal` é alcançável a partir de cada app, mas as apps não se enxergam entre si — mantém a lição limpa.

## Como rodar

Da raiz do repo:

```bash
./atom up ssrf-basic
```

- App vulnerable: <http://127.0.0.1:8004/>
- App fixed: <http://127.0.0.1:8104/>
- Serviço internal: não publicado — só alcançável através da app vulnerable ou fixed.

Pare com `./atom down ssrf-basic`. Se preferir Docker cru: `cd atoms/A10-ssrf/ssrf-basic && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8104 aplica uma allowlist explícita de hosts (`api.github.com`, `wikipedia.org`) e exige `https`. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela: o preview legítimo de `https://api.github.com/zen` retorna o mesmo conteúdo de antes, mas toda URL apontando pra `http://internal/` (ou qualquer outro host) devolve **403 Forbidden** em vez de fazer o fetch. O container `internal` continua alcançável a partir do container `fixed` na camada de rede — o fix está no código da app, não na plumbing da rede.
