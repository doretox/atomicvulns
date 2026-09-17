# DIFF — vulnerable vs. fixed

A mudança é o formato de (de)serialização — a `node-serialize` vira JSON. No `app.js` são três edições (o import, a linha que *escreve* o cookie default, e a linha que o *lê* de volta), e como o desserializador perigoso é uma *dependência*, a mudança também toca o `package.json` e o `Dockerfile`.

`app.js` (comentários abreviados):

```diff
 const http = require("http");
-const serialize = require("node-serialize");
+// FIXED: no node-serialize dependency at all -- JSON is a data-only format (stdlib).
 ...
     if (!cookie) {
-      // First visit: serialize the default prefs (node-serialize + base64) and set the cookie.
-      const raw = Buffer.from(serialize.serialize(DEFAULT_PREFS)).toString("base64");
+      // First visit: serialize the default prefs (JSON + base64) and set the cookie.
+      const raw = Buffer.from(JSON.stringify(DEFAULT_PREFS)).toString("base64");
       return sendJson(res, 200, DEFAULT_PREFS, { "Set-Cookie": `prefs=${raw}; Path=/` });
     }
-    // VULNERABLE: ... passed straight to serialize.unserialize ... "_$$ND_FUNC$$_" -> eval -> RCE ...
+    // FIXED: ... JSON carries DATA ONLY ... JSON.parse never builds a function, never evals ...
     let prefs;
     try {
-      prefs = serialize.unserialize(Buffer.from(cookie, "base64").toString());
+      prefs = JSON.parse(Buffer.from(cookie, "base64").toString());
     } catch (e) {
       prefs = DEFAULT_PREFS;
     }
```

`package.json` — a app vulnerable declara a dependência; a fixed não tem nenhuma:

```diff
   "engines": {
     "node": ">=22 <23"
-  },
-  "dependencies": {
-    "node-serialize": "0.0.4"
   }
 }
```

`Dockerfile` — a imagem vulnerable a instala; a fixed não instala nada:

```diff
 COPY package.json .
-# node-serialize is the object of study (the dangerous deserializer of this ecosystem).
-RUN npm install --omit=dev
+# No `npm install`: zero runtime dependencies (http + JSON are stdlib).
 COPY app.js .
```

Todo o resto é byte a byte idêntico entre as duas versões: no `app.js`, o servidor `http`, o `DEFAULT_PREFS`, o `getCookie` e o `sendJson` escritos à mão, o branch de primeira-visita que seta o cookie, o `try/catch` que cai no tema default, a linha de fallback do `theme`, o handler do `GET /`, o 404, e o `listen`; e a imagem base, o `WORKDIR`, o `ENV HOST`, o `EXPOSE`, e o `CMD` no `Dockerfile`. Não há templates — este átomo é API-only. O bug vive inteiramente no formato com que o cookie é (de)serializado.

## O que mudou

No `app.js`, três linhas, todas o mesmo swap: o import (`node-serialize` → sumiu), a linha que *escreve* o cookie default (`serialize.serialize` → `JSON.stringify`), e a linha que o *lê* de volta (`serialize.unserialize` → `JSON.parse`). A perigosa é a leitura — `serialize.unserialize` no cookie controlado pelo atacante. A escrita só está ali pra cada app ler o formato que escreveu; serializar o dict *próprio* e confiável da app é inofensivo. Isto é um fix *lógica-diferente* isolado no formato de serialização.

O `try/catch Exception` em volta da leitura é **idêntico nas duas versões** e não é o fix. Ele existe pra um cookie malformado degradar pras preferências default em vez de derrubar o request. Na app vulnerable ele tem um efeito colateral arrepiante: depois que o `serialize.unserialize` roda a função do atacante, o valor reconstruído não tem um `theme` string, então o handler cai no fallback e responde um `{"theme":"light"}` normal enquanto o comando já rodou. O RCE é silencioso in-band; o único rastro é o efeito colateral no servidor.

As edições de dependência (`package.json`, `Dockerfile`) não são incidentais — elas *são* parte do fix, e as próximas notas explicam por quê.

## Por que isso resolve — e por que NÃO é "validar o input"

A causa é o **formato**, não o conteúdo do cookie. O payload malicioso é `node-serialize` *bem-formado* — um objeto válido cujo valor `rce` é uma string que começa com `_$$ND_FUNC$$_`. Não há byte malformado pra rejeitar, nenhum metacaractere pra tirar; o exploit anda inteiro dentro de dado válido, conforme a spec do formato. Você não consegue "sanitizar" pra sair disso, porque o perigo não é dado ruim — é que o formato *reconstrói comportamento* (uma função) e dá `eval` nela. Então o fix não é "validar o cookie" nem "bloquear a string `_$$ND_FUNC$$_`"; é parar de usar um formato que pode carregar comportamento.

Prova de isolamento: o cookie default benigno renderiza `{"theme":"light"}` idêntico nas duas apps — na verdade é a *mesma string base64* nas duas, porque `node-serialize` e JSON produzem saída idêntica pra dados puros. Só um cookie cujo valor carregue uma função `_$$ND_FUNC$$_` as separa, e as separa porque o `serialize.unserialize` dá `eval` nela enquanto o `JSON.parse` não consegue.

## Dados vs. comportamento — e por que o fix larga a dependência

Esta é a lição inteira, então diga sem rodeio. Um formato de **dados** (JSON) descreve *valores*: depois do `JSON.parse` você tem um objeto, um array, uma string — inertes. O payload `_$$ND_FUNC$$_`, parseado como JSON, é só um objeto com um campo string inofensivo. Um formato de **comportamento** (`node-serialize`) descreve *como reconstruir um objeto*, e a reconstrução pode incluir reconstruir uma **função** — o que ele faz dando `eval` no corpo-fonte dela. Desserializar input não-confiável com um formato de comportamento entrega execução de código ao atacante. A regra durável: **nunca desserialize dado não-confiável com um formato que pode carregar comportamento**.

Aqui esse formato perigoso não é a biblioteca padrão — é um package npm, a `node-serialize`. Então o fix não é "atualizar a lib": a `node-serialize` não tem release corrigida, e mesmo que tivesse, uma lib cujo *trabalho* é (de)serializar funções é a ferramenta errada pra input não-confiável. O fix **remove a dependência** e volta pro `JSON` (stdlib). É por isso que o `package.json` da app fixed não tem `dependencies` e o seu `Dockerfile` não tem `npm install` — a capacidade insegura inteira sumiu, não foi remendada. (No `deserialization-pickle`, o desserializador perigoso é o `pickle` da stdlib do Python, que você não consegue "desinstalar" — então lá o fix troca a *função* de serialização. Mesma ideia — um formato só-dado — expressa conforme cada ecossistema permite: trocar a função em Python, largar o package em Node.)

## Assinar o cookie não é o fix

Um leitor experiente tem um fix pronto: "o cookie foi adulterado — assina ele com um HMAC (um hash com chave que detecta adulteração) pra um forjado ser rejeitado". Vale ser preciso sobre por que este átomo *não* faz isso.

Assinar ajuda em *algo*: torna o cookie tamper-evidente, então um payload forjado é rejeitado antes de chegar ao `unserialize` — eleva a barra pra *este* caminho de entrega. Mas fecha o **sintoma** (adulterar *este* cookie), não a **causa**. A operação perigosa — `serialize.unserialize` em dado que cruzou uma fronteira de confiança — continua lá, guardada em vez de removida. Se a chave de assinatura vazar, é RCE na hora de novo. E se esses bytes chegarem ao `serialize.unserialize` por qualquer outra rota — um cache, uma fila de mensagens, um arquivo enviado, um segundo endpoint — a assinatura no cookie não protege nada disso. Você está apostando no sigilo da chave pra tornar um primitivo inseguro seguro, quando podia só remover o primitivo inseguro.

Então assinar é defense-in-depth, não a correção de raiz. Trocar o formato é a correção de raiz: o `JSON.parse` não executa, com chave ou sem chave, com caminho ou sem caminho. (Mesmo movimento das notas "citada, não aplicada" do `ssrf-cloud-metadata`, do `xxe-basic` e do `ssti-jinja`: nomear o controle que o leitor apelaria, e mostrar por que não é o fix aqui — e a mesma linha sintoma-vs-causa que o `deserialization-pickle` traça sobre o HMAC.)

## O impacto é RCE — mesma classe do `deserialization-pickle`, por um mecanismo diferente

O finding é Remote Code Execution: um cookie adulterado roda comandos arbitrários no servidor. É o mesmo teto do `deserialization-pickle`, e vale pôr os dois lado a lado — porque são a **mesma classe de vulnerabilidade** (insecure deserialization, A08 — Software and Data Integrity Failures) alcançada por uma **causa concreta diferente**:

| Eixo | `deserialization-pickle` | `deserialization-node` (este átomo) |
|---|---|---|
| **Runtime / formato** | Python, `pickle` (stdlib) | Node.js, `node-serialize` (package npm) |
| **Onde mora o executor** | `pickle.loads` (biblioteca padrão) | `serialize.unserialize` (dependência npm) |
| **Gatilho de código no dado** | objeto com `__reduce__` → chama a função no unpickle | função com `_$$ND_FUNC$$_` → `eval` no unserialize |
| **Fix** | trocar formato: `pickle` → JSON | trocar formato: `unserialize` → `JSON.parse` |
| **Impacto** | RCE | RCE |

Mesmo impacto, mesma categoria, mesmo *tipo* de fix (um formato-que-carrega-comportamento → um só-dado) — e ainda assim dois átomos, não um. "Um átomo = uma vulnerabilidade" é sobre a *causa*, e a causa aqui é concreta: *qual* desserializador roda, e *o que* no dado o dispara. Em Python o desserializador perigoso vem na biblioteca padrão e dispara pelo `__reduce__`; em Node ele chega como package npm e dispara por uma função `_$$ND_FUNC$$_` dada `eval`. A mesma classe se materializa por um mecanismo nativo de cada ecossistema — este átomo é o rosto Node da falha que o `deserialization-pickle` mostra em Python.
