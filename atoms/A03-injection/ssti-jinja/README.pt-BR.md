# ssti-jinja — Server-side template injection (SSTI)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para Server-Side Template Injection (SSTI) clássico, in-band. A app é uma "personalized greeting" (saudação personalizada): você manda um `name` e ela ecoa `Hello, <name>!`. Pra montar essa saudação, o código costura o seu `name` direto no source do template e o entrega ao Jinja2 — o template engine do Flask — via `render_template_string`. Como o Jinja2 compila qualquer texto que recebe, um `name` que contém uma expressão `{{ ... }}` é *avaliado*, não exibido: `{{7*7}}` volta como `49`, e `{{config}}` despeja a configuração do Flask — incluindo a `SECRET_KEY` que assina os cookies de sessão. A mesma feature que saúda `Ada` lê o segredo da própria app.

Isto é A03 — Injection. Mecanicamente é a mesma forma do `sqli-union-basic` e do `command-injection-basic`: input não-confiável chegando num motor que faz mais do que devia — muda só o motor. Lá o motor é um banco SQL e um shell; aqui é o template engine. O bug não é "usar Jinja2" (todo Flask usa) — é *onde o input entra*: costurado no source do template (como código) em vez de passado como dado. O fix passa o name como dado, e a única diferença entre `vulnerable/` e `fixed/` é essa.

> **Teoria primeiro:** Leia [PortSwigger: Server-side template injection](https://portswigger.net/web-security/server-side-template-injection)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up ssti-jinja
```

- App vulnerable: <http://127.0.0.1:8019/>
- App fixed: <http://127.0.0.1:8119/>

Pare com `./atom down ssti-jinja`. Se preferir Docker cru: `cd atoms/A03-injection/ssti-jinja && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8119 atende a mesma saudação. Ela passa o name como dado — `render_template_string("...Hello, {{ name }}!...", name=name)` — então o Jinja2 preenche o placeholder `{{ name }}` com o valor escapado e nunca o re-avalia. Rode cada payload do `WALKTHROUGH.pt-BR.md` contra ela: `Ada` ainda saúda como `Hello, Ada!`, mas `{{7*7}}` volta literal (`Hello, {{7*7}}!`) e `{{config}}` nunca despeja a `SECRET_KEY`. A única mudança em relação ao `vulnerable/` é passar o name como dado em vez de costurá-lo no source do template; veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).
