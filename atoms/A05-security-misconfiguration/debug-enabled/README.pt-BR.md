# debug-enabled — Debug mode enabled in a reachable environment

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab Flask mínimo para um dos erros de deploy mais comuns — e mais devastadores: deixar o **debug mode** (modo de desenvolvimento) ligado num lugar que o atacante alcança. A app tem uma rota comum que recebe um valor, transforma em número e busca um item. Mande um valor que não é número e a rota levanta uma **exceção não-tratada**. Num servidor configurado normalmente isso seria um `500` sem graça. Mas esta app roda com `app.run(debug=True)`, o modo de desenvolvimento do Flask — e nesse modo o **Werkzeug** (a biblioteca HTTP que vem junto do Flask, por baixo dele, e fornece o servidor de desenvolvimento embutido e a página de erro) não esconde o erro. Ele renderiza uma **página de debug** interativa: o **traceback** completo (o relatório de erro do Python — a pilha de chamadas, as variáveis locais e as linhas de código-fonte ao redor da falha), devolvido direto pra você.

Essa página é dois problemas de uma vez. Primeiro, ela **vaza** o seu código-fonte, as suas variáveis e os caminhos de arquivo do servidor — **information disclosure** por si só. Segundo, ela embute um **console** interativo: um campo que roda **Python arbitrário dentro do processo do servidor** — **RCE (Remote Code Execution)**. O console é nominalmente protegido por um **PIN** impresso no log do servidor, mas o PIN é *calculado de dados da máquina* (username, machine-id, MAC) e é derivável por um atacante determinado — um obstáculo, não uma parede — e aqui ele está **desligado** de vez (`WERKZEUG_DEBUG_PIN=off`, um ajuste realista de "deixar debugar mais fácil"). Então o ataque inteiro é: mandar um request que quebra a rota, cair na página de debug, ler o segredo do console na página, e emitir mais um request que roda um comando no servidor.

O fix não é "pôr o PIN" nem "capturar a exceção" — os dois deixam o debugger de desenvolvimento exposto. É `debug=False`. Em produção, o **servidor de desenvolvimento** embutido não deveria ser usado de forma alguma: você serve a app atrás de um servidor **WSGI** de verdade (Web Server Gateway Interface — o "padrão de encaixe" entre um app Python e um servidor de produção) como o Gunicorn ou o uWSGI, que não tem debugger. A lógica da rota nunca muda; o mesmo input ruim ainda quebra — só que vira um `500` genérico, sem traceback e sem console.

Este átomo mora em **A05 — Security Misconfiguration**, ao lado dos irmãos [`xxe-basic`](../xxe-basic/) e [`xxe-blind-oob`](../xxe-blind-oob/). O contraste é o ponto: aqueles são um *parser* de XML mal configurado (um default perigoso deixado ligado); este é um *framework/deploy* mal configurado (uma feature de desenvolvimento deixada alcançável). O teto de RCE bate com o [`command-injection-basic`](../../A03-injection/command-injection-basic/) e o [`deserialization-pickle`](../../A08-data-integrity-failures/deserialization-pickle/) — mas por uma porta diferente: lá o **dado do atacante vira código** (costurado num shell, ou carregado como comportamento pra dentro de um deserializer); aqui **nada do atacante vira código** — o console de execução já estava ali, exposto por uma flag de configuração, e o atacante só digita nele. A exceção é só a campainha.

> **Teoria primeiro:** Leia [PortSwigger: Information disclosure](https://portswigger.net/web-security/information-disclosure)
> antes de fazer este átomo — ele nomeia "failing to disable debugging and diagnostic
> features" e "overly verbose error messages" como fontes de disclosure, que é
> exatamente a primeira metade da página de debug. Os átomos deste repo mostram *como*
> uma vulnerabilidade acontece no código; a Academy explica *o que* ela é e por que
> importa. (A Academy cobre o lado information-disclosure; o RCE via console interativo
> que o debugger exposto também habilita é mostrado aqui no átomo.)

## Nota de stack — single-container, sem banco de dados, dependências idênticas

Cada lado é um único container Flask sem datastore: não há nada pra semear — a app só expõe uma rota que quebra com input ruim, então não há usuário, sessão, nem dado. E os dois lados compartilham um `requirements.txt` **idêntico**: o fix é uma flag no código (`debug=True` → `debug=False`, mais remover a linha `WERKZEUG_DEBUG_PIN=off`), não uma dependência. O `Werkzeug` é **pinado explicitamente** (`==3.1.8`) ao lado do `Flask==3.0.0` porque o debugger interativo — o ponto inteiro deste átomo — é do Werkzeug, e o protocolo do console dele é específico da versão; pinar mantém o lab reproduzível.

## Só API — sem HTML, sem browser

Não há UI web nem templates: toda resposta normal é JSON. A interface que ensina a lição é a **página de debug do Werkzeug**, que o framework renderiza sozinho sempre que a app quebra — uma página escrita à mão não acrescentaria nada. Você conduz este átomo inteiramente pelo **Burp Suite (Repeater)**: quebra a rota, lê a página de debug na resposta, extrai o segredo do console do HTML dela, e manda o request que roda um comando — a saída do comando volta na resposta HTTP. O console nasceu pra ser clicado num browser, mas reproduz melhor no Repeater (controle cru dos query params e do segredo), e a prova é server-side, então não há trilha browser.

## Como rodar

A partir da raiz do repo:

```bash
./atom up debug-enabled
```

- API vulnerável: `http://127.0.0.1:8033`
- API corrigida: `http://127.0.0.1:8133`

Não há página inicial além de um banner JSON em `/`; a rota-gatilho é `GET /items/<idx>` (tente `/items/0`, depois `/items/abc`), documentada no `WALKTHROUGH.md`. Pare com `./atom down debug-enabled`. Se preferir Docker puro: `cd atoms/A05-security-misconfiguration/debug-enabled && docker compose up --build`.

## O que ler em seguida

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo no Burp: quebre a rota, veja a página de debug vazar o seu código-fonte e os caminhos, extraia o segredo do console, e rode `id` no servidor (`uid=0(root)`) direto da resposta HTTP. Depois os mesmos requests contra a app corrigida devolvem um `500` seco. Sem browser.
2. [`DIFF.md`](./DIFF.md) — o diff de uma flag entre `vulnerable/` e `fixed/`, e por que "pôr o PIN" e "capturar a exceção" não são o fix.

## Versão corrigida

A API corrigida na porta 8133 roda com `debug=False`. O mesmo input malformado ainda quebra — a rota não muda —, mas a resposta é um `500 Internal Server Error` genérico, sem traceback e sem console, e não há `WERKZEUG_DEBUG_PIN=off`. O request que rodou `id` na 8033 recebe um `500` seco aqui: sem página de debug pra ler um segredo, sem console pra alcançar. Veja o [`DIFF.md`](./DIFF.md) pra entender por que o fix de verdade é desligar o debug mode (e, em produção, servir atrás de um servidor WSGI real) em vez de tentar trancar o debugger.
