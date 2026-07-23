# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é o parser que a view `POST /import` constrói (comentários abreviados):

```diff
 @app.route("/import", methods=["POST"])
 def import_contact():
     xml = request.form.get("xml", "")
-    # VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES ...
-    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=True)  # dangerous
+    # FIXED: parse with external-entity resolution and DTD loading DISABLED ...
+    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)  # hardened
     try:
         doc = etree.fromstring(xml.encode("utf-8"), parser)
         name = doc.findtext("name") or ""
     except etree.XMLSyntaxError as exc:
         return render_template("result.html", name=None, error=str(exc))
     return render_template("result.html", name=name, error=None)
```

Os templates (`index.html`, `result.html`), o `Dockerfile` (incluindo a linha que planta o dummy `/app/secret.txt`) e o `requirements.txt` são byte-a-byte idênticos entre as duas versões. O bug vive inteiramente em duas flags do parser.

## O que mudou

Uma edição, no `app.py`: as flags passadas pro `etree.XMLParser`. A versão vulnerable seta `resolve_entities=True, load_dtd=True`; a fixed seta as duas como `False`. O `no_network=True` não muda — as duas versões mantêm. Nada mais se move: o `try/except`, o `findtext("name")`, o render do template, e todos os outros arquivos são os mesmos. É um fix *config-different* — o mesmo code path, com as features perigosas do parser desligadas — a menor expressão possível de "uma config é o bug inteiro".

## Por que isso resolve

A classe é: o parser resolve entities que o atacante declara no documento, então uma entidade `SYSTEM` apontando pra `file:///…` expande pro conteúdo daquele arquivo, que a app ecoa de volta no `<name>`. Desabilitar resolução de external entity (`resolve_entities=False`) e processamento de DTD (`load_dtd=False`) faz com que a declaração `<!ENTITY x SYSTEM …>` nunca seja acionada e o `&x;` nunca expanda numa leitura de arquivo. Neste lab, o resultado observável é o `<name>` voltar **vazio** — a referência resolve pra nada —, então nenhum conteúdo de arquivo é revelado. O contato benigno (sem `DOCTYPE`, sem entities) parseia e importa exatamente como antes; só a capacidade perigosa sumiu.

## lxml, e não a standard library

A standard library do Python traz o `xml.etree.ElementTree`, e ele **não** resolve external entities — dê a ele o payload deste átomo e a entity simplesmente nunca é expandida. Um átomo construído sobre ele não seria vulnerável de jeito nenhum. É por isso que este lab usa **`lxml`**, o parser third-party popular (escolhido em projetos reais por performance e XPath), que *resolve* external entities. A vulnerabilidade é uma propriedade de *qual parser você usa e como você o configura*, não de "parsear XML".

Este é o mesmo movimento honesto de dois átomos anteriores: `jwt-key-confusion` (o PyJWT moderno recusa a algorithm confusion ingênua, então aquele átomo faz o check quebrado na mão) e `session-fixation` (a sessão de cookie assinado do Flask resiste a fixation por design, então aquele átomo modela uma sessão server-side manual). Em cada caso a ferramenta padrão já mitiga o bug ingênuo, então o átomo modela o componente do mundo real onde a vuln de fato vive — aqui, um parser `lxml` instruído a resolver entities.

## O default do lxml — esta versão é segura, então a app liga explícito

Você poderia esperar que a app vulnerable só usasse o parser default do lxml e pronto. Ela não pode, e vale dizer o porquê honestamente. Na versão fixada (**lxml 5.3.0, libxml2 2.12.9**) o default puro é *seguro*: `etree.fromstring(xml)` levanta `Entity 'x' not defined` no nosso payload, porque não aciona a declaração de entity do DTD. Então a app vulnerable **liga explicitamente** (opt-in), construindo `etree.XMLParser(resolve_entities=True, load_dtd=True)`.

Esse opt-in é o anti-padrão realista. Um dev habilita processamento de entity/DTD — pra expandir entities legítimas no documento, ou copiando um snippet antigo — e herda a resolução de external entity junto. (Um detalhe sutil confirmado rodando esta versão: `resolve_entities=True` é o valor *default documentado* do lxml, mas passá-lo **explicitamente** é o que faz o libxml2 substituir a external entity aqui, enquanto o default puro não substitui. De qualquer forma, é a configuração explícita da app que abre o buraco.)

A regra durável não depende da versão: **nunca resolva external entities em XML não-confiável.** Qual configuração de parser é perigosa é específico da versão, então o comportamento deste átomo foi confirmado rodando a versão exata fixada — nunca assumido. Se você subir o `lxml`, re-cheque.

## defusedxml — citado, não aplicado

O nome que aparece pra hardening de XML em Python é o **`defusedxml`**. Este átomo deliberadamente não o usa. O `defusedxml` é a ferramenta certa pra *standard library*, mas o **suporte a `lxml` nele está deprecado** — a própria orientação do projeto é configurar o `lxml` direto (desligar resolução de entity, carregamento de DTD, e acesso à rede no parser), que é exatamente o que o `fixed/app.py` faz. Então o `defusedxml` é citado aqui, não aplicado: o mesmo movimento "cite o controle do mundo real, mantenha o diff na única mudança que ele ensina" que o `ssrf-cloud-metadata` faz com o IMDSv2.

## Este átomo é file disclosure, não SSRF

Os dois parsers mantêm `no_network=True` (o default do lxml). Isso confina a resolução de entity a arquivos locais: uma entity `file://` lê um arquivo, mas uma entity `http://` **não** é buscada — aponte uma pra uma URL e o `<name>` volta vazio (verificado). Então este átomo fica firmemente em **arbitrary file disclosure** e nunca faz uma requisição de rede. Manter o `no_network=True` na app vulnerable é de propósito: garante que a lição seja uma leitura de arquivo limpa e não escorregue acidentalmente pra uma requisição server-side.

## O eco é escapado de propósito

O `result.html` renderiza o nome importado dentro de `<pre>{{ name }}</pre>` com o autoescape do Jinja ligado (sem `|safe`, sem `Markup`, sem `render_template_string`). Quando o "nome" é um arquivo cheio de `<`/`>` — ou um atacante manda um nome `<script>alert(1)</script>` — ele volta como `&lt;script&gt;alert(1)&lt;/script&gt;` no source da página: texto, não markup. Isso é de propósito. Exibir o arquivo revelado não pode virar uma segunda vulnerabilidade (reflected XSS / HTML injection). O único bug aqui é o XXE — o parser resolvendo uma external entity — e como o resultado é exibido não faz parte disso. O fix não toca o template; os templates das duas versões são byte-idênticos.

## Sem DoS de billion-laughs

Um perigo separado, vizinho ao XXE, é o ataque "billion laughs": entities aninhadas que expandem exponencialmente e esgotam a memória. Esse é um vetor *diferente* da leitura de arquivo que este átomo ensina, e fica fora de cena: o default do lxml (`huge_tree=False`) capa a amplificação de entity, então um payload de billion-laughs é rejeitado com `Maximum entity amplification factor exceeded` e o container permanece de pé — o `except XMLSyntaxError` renderiza uma página de erro controlada. A única e exclusiva vulnerabilidade aqui é a resolução de external entity.
