# csrf-basic — Cross-Site Request Forgery (CSRF)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para Cross-Site Request Forgery (CSRF). O alvo é uma página de conta autenticada com uma ação de "trocar o e-mail de recuperação": o `POST /email` atualiza a conta, e o servidor autoriza checando uma única coisa — existe um cookie de sessão válido? O browser anexa esse cookie automaticamente a *toda* request pro alvo, não importa qual site disparou. Então uma página em **outro site** (o serviço `attacker`) pode hospedar um `<form>` escondido que auto-submete um `POST /email` pro alvo; o browser da vítima anexa o cookie de sessão dela nessa request forjada, e o servidor troca o e-mail como se a vítima tivesse pedido — um account takeover (o atacante agora controla o endereço de reset de senha). O cookie prova *quem* você é, não *que você quis* aquilo. O fix é um token anti-CSRF por sessão que o servidor põe no próprio form e exige de volta no corpo da request: um atacante em outra origem não consegue lê-lo (a Same-Origin Policy proíbe ler uma resposta cross-origin), então não forja a request completa — mesmo com o cookie viajando junto.

A versão ingênua desse bug não dispara mais: o default moderno do browser, `SameSite=Lax`, recusa anexar o cookie de sessão a um `POST` cross-site e o bloqueia sozinho. Então o lab modela as condições do mundo real onde o CSRF ainda acontece: dois sites genuinamente diferentes, e um cookie de sessão afrouxado pra `SameSite=None` (a misconfig que você encontra em embeds cross-site e em configs de cookie cargo-cult).

> **Teoria primeiro:** Leia [PortSwigger: Cross-site request forgery (CSRF)](https://portswigger.net/web-security/csrf)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up csrf-basic
```

- Alvo vulnerable: <http://127.0.0.1:8023/>
- Alvo fixed: <http://127.0.0.1:8123/>
- Site do atacante: <http://127.0.0.2:8080/> — um **site diferente** dos alvos

O `./atom up` imprime só os dois alvos em `127.0.0.1`; o atacante está em `127.0.0.2` (ainda loopback — `127.0.0.0/8` é local-only, nunca alcançável fora da máquina), então abra pela URL acima. Faça login num alvo com `demo` / `demo`.

Pare com `./atom down csrf-basic`. Se preferir Docker cru: `cd atoms/A01-broken-access-control/csrf-basic && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo. O browser é onde o CSRF acontece: ele anexa o cookie da vítima na request forjada cross-site sozinho, o que o `curl` não reproduz (um cookie que você cola à mão é só uma request autenticada normal). O Burp é uma lente de apoio que mostra, na rede, que o `POST` forjado carrega o cookie de sessão e nenhum token.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

O alvo corrigido na porta 8123 é byte-idêntico exceto por uma coisa: um token anti-CSRF por sessão, gerado server-side, embutido como hidden field no próprio form de e-mail, e exigido no corpo do `POST /email`. A config do cookie de sessão não muda (`SameSite=None; Secure` nos dois lados) — o token é a *única* diferença de segurança, o que isola que o fix é o token, não re-apertar o `SameSite`. Aponte a página do atacante pro alvo fixed e o mesmo `POST` forjado retorna `403`: o browser ainda anexa o cookie de sessão, mas a request não tem token, e o atacante não conseguiu ler um porque a Same-Origin Policy bloqueia ler o form do alvo. O fluxo legítimo — o próprio form do alvo, que carrega o token — continua funcionando nos dois lados. Isto é **A01 — Broken Access Control**: o servidor autorizou uma ação de mudança-de-estado de *quem quer que tivesse uma sessão válida*, sem verificar que o usuário *quis* aquilo.
