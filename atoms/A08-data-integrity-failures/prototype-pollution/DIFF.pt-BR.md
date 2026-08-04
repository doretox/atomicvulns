# DIFF — vulnerable vs. fixed

`vulnerable/app.js` e `fixed/app.js` diferem em exatamente um lugar — a função `merge` guarda as chaves que alcançam um prototype antes de descer (o doc-comment dela também muda, e a nota inline agora-errada na linha do recurse é removida; comentários abreviados):

```diff
 function merge(target, source) {
   for (const key of Object.keys(source)) {
+    // FIXED: refuse the three keys that reach a shared prototype before descending.
+    if (key === "__proto__" || key === "constructor" || key === "prototype") {
+      continue;
+    }
     if (isObject(source[key])) {
       if (!(key in target)) {
         target[key] = {};
       }
       merge(target[key], source[key]);
     } else {
       target[key] = source[key];
     }
   }
   return target;
 }
```

Todo o resto é byte a byte idêntico entre as duas versões: o `settings` seedado, `isObject`, `readBody`, `sendJson`, os handlers de `POST /settings` e `GET /me`, o servidor `http` e o `listen`, o `Dockerfile` e o `package.json` (não há templates — este átomo é API-only). O bug — e o fix — vivem inteiramente em por quais chaves o merge desce.

## O que mudou

O `merge` vulnerable desce em `target[key]` pra toda chave cujo valor é um objeto, sem exceções. Quando a chave é `__proto__`, `target[key]` não é um campo — é o prototype do objeto, o `Object.prototype` — então a recursão escreve no pai compartilhado por todo objeto do processo. O `merge` fixed adiciona uma guarda no topo do loop: `if (key === "__proto__" || key === "constructor" || key === "prototype") continue;`. Essas três chaves são puladas, então o loop só desce e escreve em chaves de dados próprias e reais do target. É um fix *cirúrgico* — três linhas que mapeiam direto na causa: a falha é o merge descer por chaves que alcançam o prototype, e a guarda recusa exatamente essas chaves.

## Por que isso corrige o bug — e por que NÃO é "validar o input"

A causa é **por quais chaves o merge percorre**, não o conteúdo do input. `{"__proto__":{"isAdmin":true}}` é JSON perfeitamente bem-formado, com um valor legítimo — não há sintaxe malformada pra rejeitar, nem caractere estranho pra escapar. Nada no *dado* está errado; o que está errado é o merge tratar `__proto__` como uma chave em que pode descer. Então o fix não é "sanitizar o corpo" nem "validar o input" — é o merge **recusar** as chaves que alcançam um prototype compartilhado.

Prova de isolamento: mande o merge benigno `{"theme":"dark"}` pras duas apps e as duas retornam `{"theme":"dark","notifications":{"email":true}}` e mantêm o `GET /me` em `{"admin":false}`. A feature é idêntica. Só o payload `__proto__` diverge — a app vulnerable polui o `Object.prototype` (então o objeto intocado do `GET /me` herda `isAdmin`), a fixed pula a chave e deixa o prototype em paz. Fazer deep-merge de um corpo JSON nunca foi o bug; descer por uma chave que alcança o prototype foi.

## Por que três chaves, não só `__proto__`

O quick fix tentador é guardar a única chave óbvia — "é só pular `__proto__`". Isso perde, porque `__proto__` não é a única porta pro pai compartilhado. `constructor.prototype` alcança o mesmo lugar: pra um objeto comum, `settings.constructor` é a função `Object`, e `Object.prototype` **é** o próprio objeto sendo envenenado. Então o payload

```json
{"constructor":{"prototype":{"isAdmin":true}}}
```

polui o `Object.prototype` com a mesma eficácia que o payload `__proto__` — o merge desce `settings.constructor` → `.prototype` → e escreve `isAdmin` lá — **sem nunca usar a chave `__proto__`**. Uma guarda que bloqueia só `__proto__` deixa essa porta dos fundos escancarada. Por isso a guarda robusta nomeia as **três** chaves: `__proto__` (a porta direta) mais `constructor` e `prototype` (a porta indireta via `constructor.prototype`). Este bypass por `constructor.prototype` é descrito aqui como o motivo da guarda de três chaves; o walkthrough demonstra só o payload `__proto__`.

## Nomear a chave é remendo; a defesa estrutural é outra

A guarda de três chaves é uma *blocklist de chaves* — funciona, e é a mudança mínima que isola o fix neste diff, mas ainda é "caçar o proibido". A defesa que remove a possibilidade na raiz é **estrutural** — ela muda *que tipo de objeto* guarda o dado não-confiável, pra não haver nada pra poluir ou nada que confie no pai poluído:

- **`Object.create(null)`** cria um objeto **sem prototype** — sem pai, sem `Object.prototype` na cadeia dele. Não há nada pra poluir por ele, e ler `obj.__proto__` nele é só uma propriedade comum (ausente), não uma porta pro pai compartilhado.
- **`Map`** é o dicionário real do JavaScript (armazenamento chave→valor de verdade), onde `__proto__` é só uma string de chave inofensiva como qualquer outra, não um acessor mágico. Guardar dado controlado pelo usuário num `Map` em vez de num objeto comum fecha o vetor.
- **`Object.hasOwn(obj, key)`** (ou `Object.prototype.hasOwnProperty.call`) checa só a propriedade *própria* de um objeto ao ler, ignorando o que veio do prototype. Um `if (Object.hasOwn(user, "isAdmin"))` não é enganado por um prototype envenenado.

Esses são o alvo real em produção. Este átomo aplica a guarda de chaves pra o diff continuar cirúrgico — a mesma estrutura nos dois lados, a guarda como único delta — e nomeia as defesas estruturais aqui sem aplicá-las. (Note que "assinar o blob" — o remendo estilo HMAC contra o qual o `deserialization-pickle` adverte — *não* se aplica aqui: não há blob serializado sendo confiado. O paralelo com aquele átomo é no nível da *estrutura*, não da autenticação: os dois corrigem a causa removendo um primitivo inseguro em vez de guardá-lo.)

## Impacto: contaminação global, e como difere do `deserialization-pickle`

O impacto é **contaminação global do `Object.prototype`** → subversão de qualquer código que leia uma propriedade herdada assumindo que ela é ausente. O exemplo deste lab é um bypass de autorização: o `GET /me` cria um objeto fresco, sem privilégio, e ele responde admin. A poluição persiste no processo até um restart e afeta objetos criados depois do ataque.

Tanto este átomo quanto o `deserialization-pickle` são **A08 — Software and Data Integrity Failures**: dado não-confiável corrompe algo em que a app depois confia. Mas o **impacto difere**, e é por isso que são dois átomos e não um:

- **`deserialization-pickle`** — o desserializador *executa* comportamento embutido nos bytes; o teto é **remote code execution**.
- **prototype pollution** — nada executa por padrão; o atacante *corrompe um objeto compartilhado* e *outro* código confia nele, subvertendo lógica/autorização. O teto aqui **não é RCE** — escalar prototype pollution pra execução de código precisa de *gadgets* específicos em libs em volta ou no runtime, o que está fora do escopo deste átomo.

Mesma categoria, mesma raiz "dado não-confiável quebra integridade", mecanismo diferente e teto diferente. "Um átomo = uma vulnerabilidade" é sobre a *causa*: envenenar um prototype compartilhado via um merge não tem nada a ver com reconstruir um formato que carrega comportamento. Este átomo prova o bypass de autorização; a escalada pra RCE é o alcance da classe no mundo real, descrito não armado.
