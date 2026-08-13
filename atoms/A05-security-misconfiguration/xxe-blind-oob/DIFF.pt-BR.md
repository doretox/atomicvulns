# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é o parser que a view do `POST /import` monta (comentários abreviados):

```diff
 @app.route("/import", methods=["POST"])
 def import_batch():
     xml = request.data
-    # VULNERABLE: parser RESOLVES EXTERNAL ENTITIES, loads DTDs, reaches the NETWORK ...
-    parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)  # dangerous
+    # FIXED: external-entity resolution and DTD loading OFF -- the two flags that are the cause ...
+    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=False)  # hardened
     try:
         etree.fromstring(xml, parser)
     except etree.XMLSyntaxError:
         pass
     return jsonify(status="received")
```

O `requirements.txt`, o `Dockerfile` (incluindo a linha que planta o `/app/secret.txt` dummy) e o serviço `oob-listener` são byte a byte idênticos entre as duas versões. O bug vive inteiramente nas flags do parser.

## O que mudou

Uma edição, no `app.py`: as flags passadas pro `etree.XMLParser`. A versão vulnerable seta `resolve_entities=True, load_dtd=True`; a fixed seta as duas pra `False`. O `no_network=False` fica **inalterado** — as duas versões o mantêm. Nada mais se move: o `request.data`, o `try/except`, o `etree.fromstring` e o intocado `return jsonify(status="received")` são idênticos. É um fix *lógica-diferente* — o mesmo caminho de código, com as features perigosas do parser desligadas — e, crucialmente, a linha da resposta não muda: **o fix endurece o parser, nunca a resposta.**

## Por que isso corrige o bug

A classe é: o parser resolve entidades que o atacante declara, então uma parameter entity externa apontando pra `http://…` faz o parser **buscar** a DTD do atacante, que por sua vez dirige uma requisição adicional que carrega um arquivo do servidor pra fora. Desligar a resolução de entidade externa (`resolve_entities=False`) e o processamento de DTD (`load_dtd=False`) faz com que a declaração `<!ENTITY % ext SYSTEM …>` nunca seja executada e `%ext;` nunca seja expandida num fetch. Neste lab o resultado observável é que o `oob-listener` não registra **nenhum** callback pra a app fixed — o parser não vai atrás de nada. O documento benigno (sem `DOCTYPE`, sem entidades) parseia e confirma exatamente como antes; só a capacidade perigosa some.

## As duas flags são load-bearing — o fix mínimo

O fix inverte **duas** flags, e as duas são necessárias. Isso foi confirmado rodando o parser pinado (`lxml==5.3.0`, `libxml2` 2.12.9) contra o payload de ataque sob cada configuração:

| Config do parser | DTD externa buscada? |
|---|---|
| `resolve_entities=True,  load_dtd=True` (vulnerable) | **sim** — o callback OOB dispara |
| `resolve_entities=False, load_dtd=True` | **sim** — só a carga de DTD já busca |
| `resolve_entities=True,  load_dtd=False` | **sim** — só a resolução de entidade já busca |
| `resolve_entities=False, load_dtd=False` (fixed) | **não** — o callback nunca dispara |

Desligar só uma flag deixa um caminho que ainda recupera a DTD, então o fix precisa desligar **as duas** — resolução de entidade externa e carga de DTD. É a mudança mínima que fecha a causa.

**Por que `no_network` *não* é o fix.** Setar `no_network=True` sozinho também para o callback — mas essa é a lição errada. Bloquear a rede é um controle de egress em cima de um XXE inalterado: o parser continuaria resolvendo entidades externas, continuaria lendo recursos `file://`, continuaria vulnerável em qualquer deploy onde a rede seja alcançável (que é a maioria). O fix tem que ser na **resolução de entidade**, e é por isso que o diff muda as duas flags de entidade e deliberadamente deixa `no_network=False` — o mesmo valor que a app vulnerable tinha. Com resolução de entidade e DTD desligadas, o parser não resolve referência externa nenhuma, então o acesso à rede é irrelevante; deixá-lo inalterado mantém o diff apontando direto pra causa em vez de escondê-la atrás de uma flag de firewall.

## Esconder o eco não é um fix

O instinto depois de ver o `xxe-basic` (que *ecoava* o arquivo de volta) é: "o problema era o valor voltar na resposta, então é só parar de devolver". Esse instinto está errado, e este átomo foi construído pra prová-lo. A app `/import` **já** não devolve nada além de `{"status":"received"}` — nunca ecoa — e é totalmente vulnerável: o parser resolve a entidade e alcança a rede independentemente do que a resposta diz. Esconder o output remove sua confirmação *in-band*; não faz nada ao parser. A linha da resposta (`return jsonify(status="received")`) é byte-idêntica nas duas versões exatamente pra deixar isso concreto — ela nunca foi o controle. O fix tem que agir no **parser**, que é justamente o que a resposta não toca.

## Mesmo bug do xxe-basic, canal diferente

O `xxe-basic` (in-band) e este átomo (blind, out-of-band) são a mesma classe de vulnerabilidade com o mesmo fix. O que difere é o canal:

| | `xxe-basic` (in-band) | `xxe-blind-oob` (blind / out-of-band) |
|---|---|---|
| Categoria | A05 — Security Misconfiguration | A05 — Security Misconfiguration (a mesma) |
| Causa | parser resolve entidades externas / DTD | a **mesma** |
| Canal | in-band — o valor volta na resposta | out-of-band — a requisição do parser pro listener |
| O que você observa | o arquivo na resposta HTTP | o hit chegando no log do listener |
| Fix | `resolve_entities=False, load_dtd=False` | o **mesmo** |

A dobradiça é uma flag só do parser: **`no_network`**. O parser vulnerable do `xxe-basic` mantém `no_network=True`, então a entidade resolve só `file://` — uma leitura de arquivo local, ecoada de volta in-band. O parser vulnerable deste átomo seta `no_network=False`, então o parser alcança a **rede**; com a resposta muda, a prova vira o callback out-of-band. Mesma causa, mesmo fix — a única flag diferente da app vulnerable é o que transforma uma leitura de arquivo in-band num canal out-of-band. É por isso que são dois átomos: a causa é um bug só, mas o canal de confirmação é o que vale estudar duas vezes.

## lxml, não a biblioteca padrão

A biblioteca padrão do Python traz o `xml.etree.ElementTree`, e ele **não** resolve entidades externas — dê a ele este payload e a entidade simplesmente nunca é expandida. Um átomo construído sobre ele não seria vulnerável de jeito nenhum. É por isso que este lab usa **`lxml`** (sobre `libxml2`), o parser terceiro popular (escolhido em projetos reais por velocidade e XPath), que *consegue* resolver entidades externas. A vulnerabilidade é uma propriedade de *qual parser você usa e como o configura*, não de "parsear XML" — o mesmo movimento honesto do `xxe-basic`. Como esse comportamento é específico da versão, o parser é pinado e o fetch out-of-band foi confirmado rodando a versão exata; se você subir o `lxml`, re-verifique.

## defusedxml — citado, não aplicado

O nome que aparece pra endurecimento de XML em Python é **`defusedxml`**. Este átomo deliberadamente não o usa. O `defusedxml` é a ferramenta certa pra a *biblioteca padrão*, mas o **suporte a `lxml` nele está deprecado** — a própria orientação do projeto é configurar o `lxml` direto (desligar resolução de entidade e carga de DTD no parser), que é exatamente o que o `fixed/app.py` faz. Então o `defusedxml` é citado aqui, não aplicado.

## Por que o listener é embarcado

O átomo embarca seu próprio sink out-of-band (`oob-listener`) em vez de mandar você apontar payloads pra um servidor de interação real. Detectar blind XXE no campo depende de um serviço **externo** que você controla — Burp Collaborator, `interactsh`, um catcher de DNS/HTTP na internet. Este lab é isolado por design (bindado em `127.0.0.1`, sem dependência do mundo externo), então seu exploit não pode exigir alcançar um terceiro. Embarcar um análogo self-hosted e air-gapped desse sink é o que deixa o ataque ser reproduzido offline, por qualquer um, com nada além de `docker compose logs`. O listener é **infraestrutura, ortogonal à vulnerabilidade** — não guarda segredo e não é o objeto de estudo; o arquivo que exfiltra é o da própria app vulnerable. É a mesma disciplina que o `ssrf-blind-oob` usa, e o arquivo que ele planta (`/app/secret.txt`) vive nas imagens vulnerable e fixed pra que um não-vazamento do lado fixed seja atribuível ao parser, não a um arquivo faltando.

## Sem DoS de billion-laughs

Um risco separado, adjacente a XXE, é o ataque "billion laughs": entidades aninhadas que expandem exponencialmente e esgotam a memória. É um vetor *diferente* do canal out-of-band que este átomo ensina, e fica fora da mesa: o default do `lxml` (`huge_tree=False`, que nenhuma das versões muda) capa a amplificação de entidade, então um payload de billion-laughs é rejeitado com `Maximum entity amplification factor exceeded` e o container fica de pé. A única e única vulnerabilidade aqui é a resolução de entidade externa alcançando a rede.
