# xss-dom — DOM-based Cross-Site Scripting

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para DOM-based XSS. A página faz uma busca client-side: um JavaScript que já está na página lê o termo de busca do fragmento da URL (`location.hash`, a parte depois do `#`) e o escreve na página com `innerHTML`. O fragmento nunca é enviado na request HTTP, então o servidor devolve uma página limpa e estática e nunca vê o termo — todo o fluxo source→sink vive no browser. Um fragmento forjado como `#q=<img src=x onerror=alert(document.domain)>` faz o `innerHTML` parsear a string como HTML e disparar o handler `onerror`, executando JavaScript do atacante no browser da vítima. O fix é uma linha client-side: escrever o termo com `textContent`, que nunca parseia HTML.

> **Teoria primeiro:** Leia [PortSwigger: DOM-based cross-site scripting (XSS)](https://portswigger.net/web-security/cross-site-scripting/dom-based)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Como rodar

Da raiz do repo:

```bash
./atom up xss-dom
```

- App vulnerable: <http://127.0.0.1:8021/>
- App fixed: <http://127.0.0.1:8121/>

Pare com `./atom down xss-dom`. Se preferir Docker cru: `cd atoms/A03-injection/xss-dom && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo. O browser planta o payload no fragmento da URL e o executa; o Burp Suite lê o script vulnerável na resposta servida e prova que o fragmento nunca chega ao servidor (ambos obrigatórios — o sink é JavaScript client-side, que o Burp não executa).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8121 serve a página byte-idêntica e lê o mesmo fragmento da mesma forma — só troca o sink de `innerHTML` para `textContent`. Aponte o browser pra ela, navegue pra qualquer payload do `WALKTHROUGH.pt-BR.md`, e o termo aparece como texto literal (`<img src=x onerror=...>` impresso na tela, com os angle brackets e tudo), nada executa. Nada muda no servidor — a vulnerabilidade e o fix vivem inteiramente no JavaScript client-side. Mesma classe que [`xss-reflected`](../xss-reflected/) e [`xss-stored`](../xss-stored/), e o mesmo impacto (JavaScript no browser da vítima); mas lá o sink é a saída HTML do servidor e o fix escapa no servidor, enquanto aqui o sink é uma escrita no DOM do cliente e o fix é client-side.
