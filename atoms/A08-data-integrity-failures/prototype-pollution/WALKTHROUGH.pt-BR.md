# Walkthrough — prototype-pollution

A app guarda as suas preferências: você manda um corpo JSON com campos de config pro `POST /settings`, e ela faz um *deep-merge* deles nos settings atuais — descendo recursivamente em objetos aninhados. O merge é uma função recursiva escrita à mão, e ela desce por *quaisquer* chaves que o seu JSON carregue. Uma dessas chaves é especial: `__proto__`. Mande-a e o merge, em vez de escrever num campo do objeto de settings, escreve no `Object.prototype` — o pai compartilhado por todo objeto do processo Node inteiro. A prova está num segundo endpoint que não tem nada a ver com settings: o `GET /me` cria um objeto de usuário novo e vazio e checa `if (user.isAdmin)`. Depois do ataque, esse objeto fresco — que você nunca tocou — responde admin. Tudo aqui é feito no Burp (ou `curl`); não há passo de browser, porque o JavaScript roda no **servidor** e o efeito é visível na resposta.

## 1. Context

A app `vulnerable` está em `127.0.0.1:8026` e a `fixed` em `127.0.0.1:8126`; não há banco nem segundo serviço — os settings vivem num objeto JavaScript dentro do processo Node. Dois endpoints:

- `POST /settings` — faz deep-merge de um corpo JSON nos settings. **É aqui que o bug mora.**
- `GET /me` — cria um objeto de usuário fresco, default (sem privilégio) e retorna `{"admin": user.isAdmin === true}` — a sua prova.

Isto é **prototype pollution**. Como este é o primeiro átomo JavaScript do repo, aqui estão os conceitos em que ele se apoia, definidos do zero:

- **prototype**: em JavaScript um objeto tem um **objeto-pai** — o seu *prototype* — de onde ele **herda** propriedades. Leia `obj.x` e, se `obj` não tem um `x` próprio, o motor sobe pro prototype e procura lá.
- **prototype chain**: essa busca não para no primeiro pai — ela percorre uma **cadeia** de pais (`obj` → o prototype dele → o prototype daquele prototype → …) até achar a propriedade ou acabar.
- **`Object.prototype`**: no **topo** dessa cadeia, pra quase todo objeto, está um único objeto compartilhado — o `Object.prototype`. Um `{}` comum herda dele. Existe **um** `Object.prototype` pro processo inteiro; todo objeto comum o compartilha como pai final. É isso que torna a falha global.
- **`__proto__`**: cada objeto expõe uma propriedade acessória chamada `__proto__` que **aponta pro seu prototype**. Pra um `{}` comum, `obj.__proto__` **é** o `Object.prototype`. `__proto__` é, literalmente, a porta pro pai compartilhado.
- **deep merge**: mesclar copia os campos de um objeto de origem num de destino. Um deep merge faz isso *recursivamente*: quando um campo é ele próprio um objeto, o merge **desce** e mescla os campos internos em vez de substituir o objeto inteiro. É um padrão comum pra settings e config.
- **prototype pollution**: um deep-merge que, ao descer pela chave `__proto__`, acaba escrevendo no `Object.prototype` compartilhado em vez de num campo do destino — o atacante "polui" o prototype, plantando uma propriedade no pai de todo objeto.

Isto é **A08 — Software and Data Integrity Failures**; o CWE dele (Common Weakness Enumeration — o catálogo padrão de classes de fraqueza) é **CWE-1321**, "Improperly Controlled Modification of Object Prototype Attributes ('Prototype Pollution')". A exploração é feita inteiramente no Burp; `curl` é o equivalente — não há trilha browser (este átomo é API-only, e o JavaScript roda server-side).

## 2. Spot the bug

Abra [`vulnerable/app.js`](./vulnerable/app.js). O merge é a história inteira:

```javascript
function merge(target, source) {
  for (const key of Object.keys(source)) {
    if (isObject(source[key])) {
      if (!(key in target)) {
        target[key] = {};
      }
      merge(target[key], source[key]); // for key "__proto__": recurses into Object.prototype
    } else {
      target[key] = source[key];
    }
  }
  return target;
}
```

O loop percorre `Object.keys(source)` e, pra cada chave cujo valor é um objeto, desce em `target[key]`. Pergunta de auditoria: *o que é `target["__proto__"]`?* Pra um objeto comum não é um campo — é o **prototype** do objeto, ou seja, o `Object.prototype`. Então, quando o `source` carrega uma chave `__proto__`, o merge recorre **no prototype compartilhado** e escreve lá.

Uma sutileza explica por que o corpo JSON é a superfície de ataque. Se você escrevesse o object-literal `{ __proto__: ... }` no código, `__proto__` seria um *setter* especial (ele seta o prototype do literal) e **não** viraria uma chave normal — um loop de merge nunca a veria. Mas o dado do atacante não é um literal; é texto que passa por `JSON.parse`, e o parser faz `__proto__` virar uma **chave própria comum**. Então `Object.keys(source)` a entrega, e o loop desce. O fix (foreshadow): fazer o merge **recusar** as chaves que alcançam um prototype, em vez de descer por elas.

## 3. Exploitation via Burp Suite

Aponte o Burp pra API vulnerable em `127.0.0.1:8026` e trabalhe no Repeater. Cada request abaixo é um bloco que você cola no Repeater; as mesmas requests rodam no `curl`. (Os blocos de `POST /settings` carregam `Content-Type: application/json`; este servidor escrito à mão chama `JSON.parse` no corpo independente do header, mas mandá-lo é correto e casa com um cliente real.)

### Baseline — limpo, capturado primeiro

Como poluir o `Object.prototype` é global e **persiste** até o processo reiniciar, leia o estado limpo **antes** de atacar. Pergunte ao endpoint do usuário fresco se ele é admin:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8026
```

Resposta — `200`:

```json
{"admin":false}
```

Um objeto de usuário novinho não tem `isAdmin`, então `user.isAdmin === true` é `false`. Agora exercite a feature com um merge **benigno** — mude o tema:

```
POST /settings HTTP/1.1
Host: 127.0.0.1:8026
Content-Type: application/json

{"theme":"dark"}
```

Resposta — `200`, os settings atualizados:

```json
{"theme":"dark","notifications":{"email":true}}
```

O equivalente no curl:

```bash
curl -i http://127.0.0.1:8026/settings -H 'Content-Type: application/json' \
  -d '{"theme":"dark"}'
```

A feature funciona: o merge escreve `theme` e deixa `notifications` em paz. O `GET /me` continua `{"admin":false}` — um merge benigno não muda nada de privilégio. Daqui pra frente, só uma coisa muda — a chave de topo do JSON vira `__proto__`.

### Step 1 — Poluir o prototype (o ataque)

Mande um corpo cuja chave de topo é `__proto__`, carregando `isAdmin: true`:

```
POST /settings HTTP/1.1
Host: 127.0.0.1:8026
Content-Type: application/json

{"__proto__":{"isAdmin":true}}
```

Resposta — `200`, e note o que ela mostra:

```json
{"theme":"dark","notifications":{"email":true}}
```

A resposta parece **completamente normal** — nenhum `isAdmin` em lugar nenhum. Isso é esperado: o merge escreveu no `Object.prototype`, não no objeto `settings`, e `JSON.stringify(settings)` só serializa as propriedades *próprias* de `settings`. O estrago é invisível aqui. curl:

```bash
curl -i http://127.0.0.1:8026/settings -H 'Content-Type: application/json' \
  -d '{"__proto__":{"isAdmin":true}}'
```

### Step 2 — Confirmar a contaminação global

Volte pro endpoint do usuário fresco — o que nunca mencionou settings:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8026
```

Resposta:

```json
{"admin":true}
```

Essa é a prototype pollution. O `GET /me` cria um objeto **novo e vazio** e lê `user.isAdmin`; o objeto não tem um `isAdmin` próprio, então o motor sobe pro `Object.prototype` — que você acabou de envenenar — e acha `true`. Você nunca tocou nesse objeto; você envenenou o **pai compartilhado**, e todo objeto do processo agora herda `isAdmin: true`. (`isAdmin: true` é uma flag benigna de lab; nada aqui é destrutivo, e é tudo loopback.)

> A poluição é global ao processo e agora fica até o container reiniciar, então rode o baseline **antes** do ataque — como acima — pra ver a virada `false` → `true` limpa. Pra resetar, `./atom down prototype-pollution` e depois `./atom up prototype-pollution` (ou `docker compose restart vulnerable`).

## 4. What the vuln is NOT

O exploit é uma chave num corpo JSON, então é fácil tirar a lição errada. Isole a causa real:

- **NÃO é "editei os settings".** Você não escreveu `isAdmin` *nos settings* — a resposta do `POST /settings` nunca o mostrou. A prova é o `GET /me`, um endpoint que não fala nada de settings e cria um objeto **novo e vazio**; ele virou admin porque o **pai compartilhado** (`Object.prototype`) foi envenenado, não porque os settings mudaram. (Contraste com o `mass-assignment`, onde o atacante escreve um campo extra *no próprio objeto* que está sendo atualizado. Aqui o atacante envenena o **prototype global**, e um *terceiro* objeto, intocado, o herda.)
- **NÃO é o `deserialization-pickle`, e NÃO é RCE.** Ambos são A08, mas aqui **nada executa por padrão** — o atacante *corrompe uma estrutura compartilhada*, e o dano aparece quando *outro* código confia nela. Lá o desserializador *executa* comportamento embutido (remote code execution); aqui é subversão da lógica de autorização. Mesma categoria, impacto diferente.
- **NÃO é bug de validação.** `{"__proto__":{"isAdmin":true}}` é **JSON perfeitamente válido** — não há input malformado pra rejeitar, nada pra "sanitizar". A falha é o merge **descer por uma chave que alcança o prototype**.

**Prova de isolamento:** mande o merge *benigno* — `{"theme":"dark"}` — pras **duas** apps, e as duas retornam `{"theme":"dark","notifications":{"email":true}}` e mantêm o `GET /me` em `{"admin":false}`. A feature é idêntica. Só o payload `__proto__` separa as duas: a app vulnerable polui, a fixed recusa a chave.

A única coisa que **é**: o merge desce por `__proto__` e muta o `Object.prototype` compartilhado, então todo objeto — inclusive o `{}` fresco do `GET /me` — herda o campo plantado. O fix é fazer o merge **recusar** as chaves que alcançam um prototype (`__proto__`, `constructor`, `prototype`).

## 5. Impact

**Contaminação global do `Object.prototype`:** qualquer código que leia uma propriedade herdada assumindo que ela é ausente — `if (user.isAdmin)` — é subvertido. O exemplo deste lab é um bypass de autorização: um objeto de usuário default, sem privilégio, responde admin. A poluição **persiste** no processo até um restart, e afeta objetos criados *depois* do ataque, longe do ponto de injeção.

Esse é o teto honesto deste átomo. **Não é RCE por padrão.** Prototype pollution *pode* escalar pra remote code execution no mundo real, mas só com *gadgets* específicos — uma cadeia onde uma propriedade herdada envenenada flui pra um sink perigoso de alguma lib ou do runtime (um template engine, `child_process`, `require`). Isso depende do ecossistema em volta e não é uma propriedade da falha isolada; seria um segundo mecanismo, então fica fora de escopo aqui. O teto difere do `deserialization-pickle`, o outro átomo A08 do repo, que chega a RCE por causa própria. O valor desta classe está em quão *silenciosa e global* ela é: uma chave num corpo JSON contamina todo objeto do processo, e o dano aparece onde algum código lê uma propriedade herdada que assumia ausente.

## 6. Why the fix works

Rode a cadeia contra a API fixed na porta **8126** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança). Ela começa limpa — `GET /me` → `{"admin":false}`. Agora mande o **mesmo payload de ataque**:

```
POST /settings HTTP/1.1
Host: 127.0.0.1:8126
Content-Type: application/json

{"__proto__":{"isAdmin":true}}
```

Resposta — `200`:

```json
{"theme":"light","notifications":{"email":true}}
```

Depois leia o endpoint do usuário fresco:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8126
```

Resposta — ainda:

```json
{"admin":false}
```

O merge fixed pula as três chaves que alcançam um prototype no topo do loop (`if (key === "__proto__" || key === "constructor" || key === "prototype") continue;`), então ele nunca desce no `Object.prototype`. O prototype fica intacto, e o objeto fresco do `GET /me` não herda nada. Enquanto isso, um merge benigno `{"theme":"dark"}` se comporta exatamente como na app vulnerable — a feature está intacta; só as chaves que alcançam um prototype são descartadas.

O fix inteiro é o merge recusar as chaves que alcançam um prototype compartilhado — uma guarda no merge, não validação de input (o payload é JSON válido). Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra saber por que a guarda nomeia **três** chaves e não só `__proto__`, por que a defesa robusta de produção é estrutural (`Object.create(null)`, `Map`, `Object.hasOwn`), e como o impacto desta falha A08 difere do `deserialization-pickle`.
