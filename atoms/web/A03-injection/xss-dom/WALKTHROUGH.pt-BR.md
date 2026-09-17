# Walkthrough — xss-dom

A página faz uma busca inteiramente no browser. Você põe um termo no fragmento da URL — `#q=...`, a parte da URL depois do `#` — e um pequeno script que já está na página o lê e escreve `You searched for: <termo>` na tela. O termo nunca sai do browser: o fragmento é a única parte de uma URL que o browser **não** envia na request HTTP. Então o servidor devolve a mesma página estática toda vez e nunca vê o que você buscou; o termo só entra na página depois, quando o próprio JavaScript da página lê o fragmento e o joga no documento com `innerHTML`. `innerHTML` pede ao browser que *parseie* essa string como HTML — inclusive qualquer event handler que ela carregue. Ponha um `<img src=x onerror=...>` no fragmento e o browser constrói o elemento, a imagem falha ao carregar, o `onerror` dispara, e o seu JavaScript roda.

## 1. Contexto

`GET /` serve uma página de busca de um campo. Não existe endpoint de busca no servidor: você digita um termo (ou edita a URL) e o resultado é renderizado no cliente. Isto é **DOM-based XSS**, uma vuln de injection (OWASP **A03 — Injection**) — cross-site scripting em que todo o caminho do input controlado pelo atacante até a operação perigosa roda no próprio JavaScript do browser, sem nunca tocar o servidor. Dois termos nomeiam as pontas desse caminho: o **source** é de onde vem o input não-confiável (aqui `location.hash`, o fragmento da URL), e o **sink** é a operação perigosa em que ele cai (aqui `innerHTML`, que parseia HTML). O **fragment** (fragmento) — tudo depois do `#` numa URL — é o ponto-chave: o browser o mantém no cliente e nunca o coloca na request HTTP, então o servidor é cego a ele.

Sem banco, sem segundo serviço: a app `vulnerable` está em `127.0.0.1:8021`, a `fixed` em `127.0.0.1:8121`. Como o sink é JavaScript client-side, o browser é onde você explora e observa; o Burp é uma segunda lente que lê o script entregue e prova, na rede, que o seu payload nunca chega ao servidor.

## 2. Ache o bug

Abra [`vulnerable/templates/index.html`](./vulnerable/templates/index.html). O bug inteiro é o script inline:

```javascript
function render() {
  var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
  document.getElementById("result").innerHTML = "You searched for: " + q;
}
window.addEventListener("hashchange", render);
render();
```

`q` é lido direto de `location.hash` — o fragmento da URL, que você controla — e concatenado em `...result").innerHTML`. Pergunta de auditoria: *o meu input cai em `innerHTML`, que parseia a string como HTML e roda qualquer event handler nela?* — sim. Esse é o sink. `render()` roda no load e de novo em todo `hashchange`, então editar o fragmento re-renderiza. Repare no que **não** está aqui: [`vulnerable/app.py`](./vulnerable/app.py) só chama `render_template("index.html")` sem dado nenhum — o servidor nunca recebe, guarda ou renderiza o termo de busca. Source e sink vivem ambos no browser. (O fix, adiantando: mandar o termo pra um sink que escreve texto em vez de parsear HTML.)

O grep barato de primeira passada pra esta classe é um sink de DOM alimentado pela URL:

```bash
grep -rn 'innerHTML\|document.write\|location.hash' .
```

## 3. Exploração (no browser)

O sink é JavaScript client-side, então o exploit roda num browser — o Burp não executa JavaScript. Abra a app vulnerable com o browser passando pelo proxy do Burp (isso captura o tráfego pra Seção 4), mas o payload vai na URL, não numa request do Burp.

### Baseline — a feature

Navegue pra `http://127.0.0.1:8021/#q=laptop`. A página renderiza:

```html
<p id="result">You searched for: laptop</p>
```

`laptop` veio do fragmento e o script da página o renderizou. Comportamento normal de busca.

### Monte o payload — um event handler, não `<script>`

O payload óbvio — `<script>alert(document.domain)</script>` — **não** funciona aqui, e entender por quê é metade da lição. Quando você atribui a `innerHTML` depois do load, o browser parseia a string e constrói o DOM, mas por regra do HTML ele **não** executa um `<script>` inserido desse jeito. (Tente `#q=<script>alert(1)</script>`: nada acontece, e se você inspecionar o elemento result o `<script>` está lá no DOM — parseado e inserido, nunca executado. Os átomos `xss-reflected` e `xss-stored` cada um notou de passagem que esse mesmo payload "silenciosamente não faria nada" em DOM-based XSS — este é esse átomo.) Você precisa de JavaScript que rode **sem** um script tag: um elemento com um event handler inline. O clássico é uma imagem com uma source quebrada:

```
<img src=x onerror=alert(document.domain)>
```

O browser constrói o `<img>`, tenta carregar `src=x`, falha, e dispara o `onerror` — rodando o seu código.

### Dispare

Navegue pra:

```
http://127.0.0.1:8021/#q=<img src=x onerror=alert(document.domain)>
```

Uma caixa de alert aparece mostrando `127.0.0.1` — `document.domain`, a origin em que o script está rodando. O seu JavaScript executou dentro da página da app. Veja o que o `innerHTML` fez com o DOM — o parágrafo result agora contém um elemento de imagem real, não texto:

```html
<p id="result">You searched for: <img src="x" onerror="alert(document.domain)"></p>
```

É exatamente por isso que o handler rodou: a string foi *parseada num elemento*, não escrita como caracteres. Qualquer coisa que a página pode fazer no browser — ler cookies desta origin, fazer requests como o usuário logado, reescrever o DOM, exfiltrar a página — esse script agora também pode.

O alert é benigno: uma caixa de diálogo, nada lido ou enviado, nada saindo do browser, num lab local isolado. Num alvo real isto é XSS de verdade; mantenha os payloads demonstrativos (um `alert`), nunca um keylogger ou uma exfiltração real.

## 4. O que o Burp mostra — e o que não mostra

DOM XSS é conduzido pelo browser, mas o Burp não fica ocioso — ele prova o fato que define a classe. No **Proxy → HTTP history**:

**O sink vulnerável vai na resposta.** Ache a request `GET /` e leia o corpo da resposta: o `<script>` inline com `innerHTML = "You searched for: " + q` está bem ali, entregue verbatim ao browser. O servidor entrega o código vulnerável — ele só nunca o executa.

**O seu payload nunca está numa request.** Essa é a chave. Depois de navegar pra `/#q=<img src=x onerror=alert(document.domain)>`, olhe toda request que o Burp capturou. A request line é:

```
GET / HTTP/1.1
```

Não `GET /#q=<img...>`, não `GET /?q=<img...>` — só `GET /`. O fragmento **sumiu**: o browser o retirou antes de enviar. O próprio log do servidor concorda —

```
"GET / HTTP/1.1" 200 -
```

— sem fragmento, sem payload. Essa ausência *é* a prova de que isto é DOM-based, não reflected nem stored: não há request nenhuma carregando o seu payload pro servidor refletir ou guardar, e (na prática) nenhuma pro Burp interceptar e adulterar. O payload viveu e rodou inteiramente no browser. É também por isso que o exploit no mundo real é um **link** forjado, não uma request forjada: o atacante manda pra vítima uma URL com o payload no fragmento.

## 5. O que a vuln NÃO é

Mesmo `alert`, mesma classe dos outros átomos de XSS — então isole o que de fato é diferente:

- **NÃO é reflected XSS.** No `xss-reflected` o servidor pega o `?q=...` da request e o ecoa no HTML que renderiza — o payload está na request, e a resposta *do servidor* o traz de volta. Aqui a resposta é uma página estática fixa que não ecoa nada, porque o seu termo (no fragmento) nunca chegou ao servidor. A Seção 4 mostrou: a request foi um `GET /` pelado.
- **NÃO é stored XSS.** Nada é persistido. Não há banco, e o payload não sobrevive a um reload a menos que esteja de novo no fragmento. Ele vive só na URL em que você está.
- **NÃO é um bug de escape no servidor.** Essa é a armadilha. O reflexo é "é XSS — escapa a saída, liga o autoescape do Jinja, bota uma CSP". Nada disso alcança este bug, porque o dado perigoso nunca passa pelo servidor: a página que o Jinja renderizou é limpa e estática, e o Jinja nunca vê o fragmento. A defesa tem que morar onde o dado é *usado* — no JavaScript client-side.

O que **é**: JavaScript client-side lê um source que você controla (`location.hash`) e o passa pra um sink que parseia HTML (`innerHTML`). O único fix é um sink que escreve texto em vez disso — no cliente.

## 6. Impacto

**Cross-site scripting: JavaScript arbitrário no browser da vítima, sob a origin da página.** O atacante entrega um link — `http://alvo/#q=<payload>` — e quem o abre roda o script do atacante no contexto daquela página: roubar cookies de sessão, fazer requests autenticadas como a vítima, ler ou reescrever o DOM, exfiltrar o conteúdo da página. Mesmo teto do `xss-reflected` e do `xss-stored` (JavaScript no browser da vítima), alcançado por uma causa diferente — um sink de DOM no cliente em vez da saída HTML do servidor. Sem overclaim: isto roda no browser da vítima, não no servidor; o servidor aqui nunca é sequer tocado.

## 7. Por que o fix funciona

Aponte o browser pra app fixed na **8121** e repita o exploit com a *mesma* URL, `http://127.0.0.1:8121/#q=<img src=x onerror=alert(document.domain)>`. Sem alert. A página renderiza:

```html
<p id="result">You searched for: &lt;img src=x onerror=alert(document.domain)&gt;</p>
```

O payload é impresso na tela como texto literal — com os angle brackets e tudo — não construído num elemento. Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança de uma linha: o script fixed lê o mesmo fragmento da mesma forma e só troca o sink, `innerHTML` → `textContent`. `textContent` escreve a string como caracteres e nunca a parseia como HTML, então não há `<img>`, não há `onerror`, nada pra rodar. A busca benigna fica intacta — `#q=laptop` renderiza `You searched for: laptop` nas duas apps — e o fix é exatamente uma coisa: o sink client-side. Nada mudou no servidor, porque nada no servidor jamais foi o problema.
