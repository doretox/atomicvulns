# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` e `fixed/app.ts` diferem só no **bloco de autenticação** — como o token é emitido e como é resolvido. O handler do `POST /login`, a rota `GET /users/:handle` inteira (guarda de posse e tudo), o seed `USERS`, os imports fora um, o bootstrap, o rodapé `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é API-only). Este é o primeiro átomo da série cujo diff toca esse bloco; em todos os anteriores ele era infraestrutura intocada e cripto-forte.

## O fix — um token opaco resolvido por lookup, não um nome lido de dentro do token

```diff
+import { randomBytes } from "node:crypto";
 ...
+const TOKENS = new Map<string, string>();                   // opaque token -> username (in-memory; NOT a JWT)

 function issueToken(user: string): string {
-  return Buffer.from(user).toString("base64url");           // VULNERABLE: the name, encoded -- not entropy
+  const token = randomBytes(24).toString("base64url");      // crypto-strong opaque value
+  TOKENS.set(token, user);                                  // bind token -> identity, server-side
+  return token;
 }

 function authenticate(req: express.Request): string | null {
-  // VULNERABLE: decode the token and trust whoever it spells.
+  // Authentication only: resolve the Bearer token to a username, or null.
   const header = req.header("authorization") ?? "";
   const token = header.startsWith("Bearer ") ? header.slice(7) : "";
-  return Buffer.from(token, "base64url").toString("utf8") || null;
+  return TOKENS.get(token) ?? null;
 }
```

No build vulnerable a identidade viaja **dentro** do token: o `issueToken` codifica o nome, o `authenticate` o decodifica de volta, e quem controla o token controla a identidade. No build fixed o token é um **ponteiro opaco**: `randomBytes(24)` não carrega identidade nenhuma, o `issueToken` guarda o vínculo `token -> user`, e o `authenticate` o resolve por **lookup**. As duas funções fazem o mesmo trabalho — transformar um token num username — mas uma *lê a resposta do token* e a outra *pergunta a um registro que o servidor guardou*.

**Leia o fix pelo que ele muda: a origem da identidade.** O ponto não é um token mais forte. É mudar de onde a identidade vem — pra fora do token, onde o cliente a autora, pra dentro de um registro server-side, onde só o servidor a autora. O token para de **afirmar** quem você é e passa a **referenciar** uma afirmação que o servidor fez no login. É por isso o `randomBytes`: um ponteiro opaco não pode ser derivado de um handle, porque não há nada dentro pra decodificar — só algo pra procurar, e procurar um token que ninguém registrou devolve ninguém (`401`).

> **Identidade que viaja dentro do token é identidade que o cliente pode autorar; o fix não blinda o token, ele para de ler identidade de dentro dele.**

## Por que o diff toca três pontos, e por que são inseparáveis

A mudança não é uma linha, e isso é deliberado — é a natureza da classe, não um afrouxamento de "um átomo = uma vuln". O diff move três coisas: (i) como o `issueToken` emite o token, (ii) como o `authenticate` o resolve, e (iii) a presença do mapa `TOKENS`. São três faces de uma decisão única — *a identidade vem do conteúdo do token (decode) ou de um vínculo guardado (lookup)?* — e não dá pra separá-las coerentemente. Um token opaco (iii + i) **exige** lookup (ii), porque não há identidade dentro pra decodificar; um token auto-descritivo (o build vulnerable) **dispensa** o `TOKENS`, porque a identidade já viaja nele. Mude um sem os outros e a lógica não fecha: um `TOKENS.get` sem `TOKENS.set` autentica ninguém; um token `randomBytes` sem lookup perde a identidade inteira. A lição é **uma** — uma identidade forjável — expressa, por construção, como um trio generate/store/resolve.

Os diffs anteriores da série eram de uma linha porque a lição era uma projeção (um único `res.json`, um único `USERS.set`). Aqui a lição é um **mecanismo** — como a identidade nasce e é resolvida — e mecanismo tem partes. Não é mais largo por desleixo; é mais largo porque a falha é mais fundamental.

## Assinar o token parece o fix — e não é

Um quase-fix tentador para a forja sem tirar a identidade de dentro do token: **assine-o**, pra um cliente não conseguir fabricar um.

```ts
// CONSIDERED AND REJECTED -- sign the token so it can't be forged, but keep the identity inside it.
import { createHmac, timingSafeEqual } from "node:crypto";
const SECRET = "changeme";
function issueToken(user: string): string {
  const body = Buffer.from(user).toString("base64url");
  const sig = createHmac("sha256", SECRET).update(user).digest("base64url");
  return `${body}.${sig}`;                                   // name.signature -- still self-describing
}
function authenticate(req: express.Request): string | null {
  const raw = (req.header("authorization") ?? "").replace(/^Bearer /, "");
  const [body, sig] = raw.split(".");
  if (!body || !sig) return null;
  const user = Buffer.from(body, "base64url").toString("utf8");
  const expected = createHmac("sha256", SECRET).update(user).digest("base64url");
  const a = Buffer.from(sig), b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  return user;                                               // verified -- but identity still came from the token
}
```

Ela **funciona contra este exploit**: um atacante que só sabe o nome `alice` não consegue produzir o HMAC sem o `SECRET`, então um `base64url("alice")` cru é rejeitado (type-checado e verificado num protótipo: um token legitimamente emitido resolve, uma forja sem assinatura não). Mas resolve o **problema errado**. A identidade continua viajando no token, agora com integridade parafusada em cima. O fix de verdade é mais básico: a identidade não devia ser derivável do token de jeito nenhum — o vínculo opaco server-side é a correção, não remendar um token auto-descritivo com uma assinatura. Assinar troca "qualquer um forja" por "quem tem o segredo forja, e o token virou um JWT caseiro", herdando toda a superfície de gestão de chave e algoritmo que o token opaco simplesmente não tem. E arrasta o átomo pra uma classe diferente — assinaturas, confusão de algoritmo, expiração — que é outra conversa. O foil está aqui pra fechar essa porta de propósito.

Em escala, "token opaco + lookup" é o que frameworks de sessão fazem (um session id aleatório mapeado a um registro server-side); JWTs resolvem o mesmo problema pelo outro caminho, com claims assinados e o próprio conjunto de armadilhas. Este átomo nomeia o princípio — a identidade não pode ser derivável — não uma biblioteca; nenhuma dependência de JWT ou HMAC entra no fix (o bloco acima é só ilustrativo, e o `fixed/` não importa nada além de `randomBytes`).

## O `401` que o build vulnerable não consegue dar

Um comportamento vale registrar porque é o sintoma da classe inteira. O que conta como "token ruim" difere entre os builds, e a diferença *é* a vulnerabilidade.

No build fixed, todo token não-registrado leva `401` — um lookup miss. A categoria "credencial presente mas **não reconhecida**" existe. No build vulnerable, essa categoria quase não existe: o servidor decodifica qualquer coisa e confia, então um token que decodifica pra uma string **não-vazia** é aceito como *aquela identidade*. Um token "ruim" então cai em:

- um decode **vazio** (`""`, `Bearer !!!`, sem header) → `null` → **`401`** — o único `401` honesto que o build vulnerable dá, e ele existe por acidente do `|| null`, não por reconhecer invalidez;
- um decode pra handle **não-dono** (`base64url("alice")` contra `/users/clancy`, ou bytes não-UTF-8 como `Bearer ////`) → **`403`** (posse);
- um decode pra handle **não-seedado** igual ao path (`Bearer Zm9v` = `"foo"` contra `/users/foo`) → **`404`**.

Então a ausência de um `401` honesto pra "token não reconhecido" é o sintoma: no build vulnerable *não há* token não reconhecido — todo decode não-vazio é reconhecido como alguém. **Um servidor que nunca diz "não te conheço" é um servidor que reconhece qualquer um.** (Verificado contra os containers rodando: fixed `Bearer YWxpY2U` → `401`; vulnerable `Bearer YWxpY2U` → `200` contra `/users/alice`, `403` contra `/users/clancy`. Nenhum token lixo produz `500` — o decode é total, virando bytes inválidos no caractere de substituição U+FFFD em vez de lançar.)

## Status codes — herdados, com um sintoma novo

Os status codes do `GET /users/:handle` são os da série, não re-argumentados aqui:

- **Uma leitura alheia → `403`.** `GET /users/alice` com o token real do `clancy` é recusado pela guarda de posse, que compara o handle do path com o caller **antes de qualquer lookup** — então não revela existência e não é um enumeration oracle. Mesma guarda, mesmo raciocínio do `bfla-method-based`; o [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md) dele carrega a conta completa, o RFC 9110 §15.5.4 e o critério único da série pra `403` vs `404`.
- **Token ausente ou inválido → `401`** com um challenge `WWW-Authenticate: Bearer` (RFC 9110 §15.5.2); o `403` não carrega nenhum, porque aquele caller já está autenticado. Também herdado; ver o mesmo [`DIFF.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.md).

O argumento novo é o de cima: no build vulnerable o `401` pra uma credencial *presente mas não reconhecida* falta, porque o build reconhece toda credencial. Isso não é uma escolha de estilo de status code — é a impressão digital do bug.

## Isto é Broken Authentication — uma identidade forjável

Nada que o chamador manda é parseado ou executado. Um Bearer token bem-formado, atrás de um check de posse correto, lê um perfil — e o token não prova nada, porque qualquer um o constrói a partir de um handle público. Isto é **Broken Authentication** — **API2:2023** no OWASP API Security Top 10. Ler como BOLA aponta pro lugar errado (o check de posse está presente e correto — `GET /users/alice` com o seu próprio token é `403`); ler como roubo de token descreve mal o método (nada foi interceptado — o token foi fabricado a partir de um nome); ler como cripto fraca ignora que não há cripto nenhuma — base64url é codificação, não cifra. A falha é anterior a todas elas: o mecanismo que prova identidade pode ser produzido por qualquer um, então todo check de autorização correto do sistema acaba servindo o atacante, que *é* a vítima até onde o servidor consegue saber. O impacto é **impersonation total** de qualquer handle conhecido mais acesso ao dado privado daquele usuário, e **não é revogável** — um token que o servidor nunca guardou é um que ele não consegue invalidar. Como o resto da série, o bug vive no `app.ts` e não dá `grep`: você o pega perguntando, do token, *isto é imprevisível pra quem não o recebeu?* — e notando que um check de posse correto foi silenciosamente confiado a se apoiar numa identidade que qualquer um pode forjar.
