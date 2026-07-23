# xxe-basic — XML External Entity (XXE) injection

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para XXE clássico, in-band. A app é um "contact importer": você cola um cartão de contato em XML, o servidor parseia e ecoa de volta o nome do contato importado. O parser resolve **external entities**, então um documento cujo `DOCTYPE` declara uma entidade `SYSTEM` apontando pra `file:///etc/passwd` faz essa entidade expandir pro conteúdo do arquivo — e a app te devolve isso no campo `name`. A mesma feature que importa `Ada Lovelace` lê arquivos arbitrários do servidor.

Este é o primeiro átomo do repo em **A05 — Security Misconfiguration**. XXE está dobrado em A05 na OWASP Top 10 2021; tinha categoria própria (A4) na edição de 2017. A causa-raiz encaixa em A05 com precisão: uma feature do parser — resolução de external entity — que deveria estar desligada está ligada. Mecanicamente, XXE é uma *injection*: input não-confiável chegando num motor (o parser de XML) que faz mais do que devia — a mesma forma do `sqli-union-basic` e do `command-injection-basic`, onde o motor é um banco SQL e um shell. Aqui o motor é o parser de XML, e o bug e o fix são uma única config do parser. O impacto é o mesmo do `path-traversal-basic` — arbitrary file disclosure, o `/etc/passwd` e os próprios arquivos da app — alcançado por outra porta.

> **Teoria primeiro:** Leia [PortSwigger: XML external entity (XXE) injection](https://portswigger.net/web-security/xxe)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota sobre a biblioteca — por que lxml, e não a standard library

O parser de XML da standard library do Python (`xml.etree.ElementTree`) **não** resolve external entities, então um átomo construído sobre ele não seria vulnerável. Este lab usa **`lxml`**, o parser third-party popular, que *resolve*. No `lxml` 5.3.0 o default puro é seguro — recusa uma external entity não-definida —, então a app vulnerable **liga explicitamente** (opt-in) construindo o parser com `resolve_entities=True, load_dtd=True`. Esse é o anti-padrão realista: um dev habilita processamento de entity/DTD por motivos legítimos e herda a resolução de external entity junto. O fix desliga essas flags de volta. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pro raciocínio completo, incluindo por que o `defusedxml` é citado mas não usado.

## Como rodar

Da raiz do repo:

```bash
./atom up xxe-basic
```

- App vulnerable: <http://127.0.0.1:8018/>
- App fixed: <http://127.0.0.1:8118/>

Pare com `./atom down xxe-basic`. Se preferir Docker cru: `cd atoms/A05-security-misconfiguration/xxe-basic && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8118 atende a mesma feature com o mesmo input. O parser dela desabilita resolução de external entity e carregamento de DTD (`resolve_entities=False, load_dtd=False`), então uma entidade `SYSTEM` nunca é resolvida. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela: o contato benigno ainda importa como `Ada Lovelace`, mas todo payload `file://` volta com o campo `name` **vazio** — nenhum conteúdo de arquivo. A única mudança em relação ao `vulnerable/` é essa configuração do parser; veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).
