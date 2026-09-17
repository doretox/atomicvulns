# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/templates/index.html` e `fixed/templates/index.html`:

```diff
 // The fragment is never sent to the server -- source = location.hash.
-// VULNERABLE sink: innerHTML parses the string as HTML and fires embedded event
-// handlers (e.g. <img src=x onerror=...>), so a crafted fragment runs attacker JS.
+// FIXED sink: textContent writes the string as literal text; the browser never
+// parses it as HTML, so <img src=x onerror=...> shows up as inert characters.
 function render() {
   var q = new URLSearchParams(location.hash.slice(1)).get("q") || "";
-  document.getElementById("result").innerHTML = "You searched for: " + q;
+  document.getElementById("result").textContent = "You searched for: " + q;
 }
```

Uma atribuição de propriedade muda: `innerHTML` → `textContent`. Todo o resto é byte a byte idêntico entre as duas versões — o `app.py`, o resto do `index.html` (o form, a estrutura do `<script>`, a lógica do `render()`, o listener de `hashchange`), o `Dockerfile` e o `requirements.txt`. O bug vive inteiramente naquele único sink client-side.

## O que mudou

A página vulnerable escreve o termo de busca na página com `element.innerHTML`; a página fixed o escreve com `element.textContent`. As duas leem o mesmo source da mesma forma — `new URLSearchParams(location.hash.slice(1)).get("q")` — e as duas montam a mesma string, `"You searched for: " + q`. A única diferença é qual propriedade do DOM a recebe.

## Por que isso corrige o bug

`innerHTML` e `textContent` diferem de um jeito decisivo: o que fazem com markup na string.

- **`innerHTML`** trata a string como **source HTML**. O browser a parseia, constrói o DOM que ela descreve e liga qualquer event handler que encontrar. Passe `<img src=x onerror=alert(document.domain)>` e você tem um elemento `<img>` real cujo `onerror` roda — JavaScript do atacante, executado.
- **`textContent`** trata a string como **texto literal**. O browser cria um único text node e mostra os caracteres como estão; nunca os parseia como HTML. O mesmo `<img src=x onerror=...>` vira o texto visível `&lt;img src=x onerror=...&gt;` na tela — sem elemento, sem handler, nada pra rodar.

Trocar o sink remove o passo de parsing, e com ele todo payload baseado em markup de uma vez — uma imagem quebrada, um `<svg onload>`, uma tag que quebra o contexto — não importa os caracteres exatos. O caso benigno fica intacto: `#q=laptop` renderiza `You searched for: laptop` de qualquer forma.

## Nada muda no servidor

Repare no que *não* está neste diff: o `app.py`. As duas apps rodam código de servidor byte-idêntico — uma única rota que retorna `render_template("index.html")` sem dado nenhum. **O servidor não participa desta vulnerabilidade de forma alguma: ele nunca recebe o payload e nunca o renderiza.** O termo malicioso vive no fragmento da URL, que o browser nunca envia; o servidor devolve a mesma página estática quer o fragmento seja benigno, malicioso ou ausente. A causa e o fix vivem ambos 100% no JavaScript client-side.

Vale dizer isso com todas as letras, porque é diferente dos outros dois átomos de XSS. No `xss-reflected` e no `xss-stored` os `app.py` também são idênticos e o bug também está "no template" — mas lá o servidor ainda *segura o source*: ele recebe a query `?q=` ou o corpo do `POST`, e o sink é uma expressão Jinja que o servidor avalia ao renderizar. Aqui o servidor nunca vê o input, e o sink é JavaScript que o servidor emite verbatim e nunca executa. A prova é direta — mande `#q=laptop` pras duas apps e as duas renderizam `You searched for: laptop`; só um payload com markup as separa, e só no browser.

## Escapar no servidor não é o fix

O instinto pra qualquer XSS é "escapa a saída" — liga o autoescape do Jinja, HTML-escapa o valor, bota um header Content-Security-Policy (CSP). Pra um bug *reflected* ou *stored* isso é exatamente certo, porque o servidor renderiza o dado contaminado. Aqui não alcança nada:

- O payload chega pelo `location.hash`, que **nunca sai do browser**. O Jinja renderiza uma página que nunca conteve o termo de busca, então não há o que escapar. O autoescape já está ligado nesta app — e é irrelevante, porque nenhum input do usuário passa por uma variável de template server-side.
- Um servidor só consegue defender o dado que ele enxerga, e este dado ele não enxerga. A defesa tem que ficar onde o dado é de fato *usado* — o sink client-side — que é exatamente o que a troca pra `textContent` faz.

Uma CSP ainda vale como **defense-in-depth**: uma policy estrita pode reduzir o que um XSS alcança mesmo que um escape. Mas não é o root fix (e uma policy frouxa não pararia um `onerror` inline). O root fix é parar de entregar dado controlado pelo atacante a um sink que parseia HTML.

## `textContent` escreve dados; `innerHTML` constrói comportamento

A lição mais funda é a mesma que separa dados de código em todo lugar: `textContent` escreve **dados** — os caracteres exatos, inertes — enquanto `innerHTML` pede ao browser pra **construir e rodar comportamento** a partir desses caracteres (elementos, e os event handlers ligados a eles). O fix escolhe a API que não consegue executar.

Se uma feature de verdade realmente precisa renderizar *HTML* do usuário (um comentário rich-text, digamos), a resposta não é `innerHTML` no input cru, mas um sanitizer de HTML dedicado — DOMPurify, por exemplo — que remove o markup perigoso antes de ele chegar ao DOM. Este lab não precisa disso: um resultado de busca é texto puro, então o fix é simplesmente `textContent`, sem dependência adicionada. Sanitizar é a ferramenta pra "precisa renderizar HTML"; `textContent` é a ferramenta pra "só precisa de texto", e escolher texto quando texto é tudo que você precisa é o movimento menor e mais seguro.

## O impacto é XSS — mesmo teto do reflected e do stored, causa diferente

O payload roda JavaScript arbitrário na origin da página, no browser da vítima: roubo de cookie de sessão, requests autenticadas como a vítima, reescrita do DOM, exfiltração da página. Esse é o mesmo teto do [`xss-reflected`](../xss-reflected/) e do [`xss-stored`](../xss-stored/) — os três são cross-site scripting, e os três rodam JavaScript do atacante no browser da vítima. O que difere é a causa e onde o fix mora: reflected e stored são o servidor escrevendo dado contaminado na sua saída HTML (corrigido escapando no servidor); este é JavaScript client-side escrevendo dado contaminado num sink de DOM (corrigido no cliente). Mesma classe, mesmo impacto, bug diferente — que é por que ele é o seu próprio átomo, com o seu próprio fix.
