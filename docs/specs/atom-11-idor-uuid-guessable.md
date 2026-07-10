# Spec — Átomo 11: `idor-uuid-guessable`

> Documento de especificação para o Claude Code implementar o décimo-primeiro átomo do projeto `atomicvulns` (Fase 3, **primeiro átomo da fase** — abre "Access Control & Autenticação", milestone `v0.3.0`). Leia junto com `CLAUDE.md` (Seções 3.3, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — dois átomos de referência já publicados em `main`:
> 1. **`atoms/A01-broken-access-control/idor-numeric-id/` (03) — o átomo IRMÃO DIRETO.** Este átomo é o par natural do 03: mesma classe (IDOR), mesma categoria (A01), mesma causa raiz (ownership check ausente). Reusar o modelo de identidade simulada (`X-User-ID`), o passo de contraste "o que a vuln NÃO é", o vocabulário de broken access control, e o framing "o bug é a checagem AUSENTE, não input que virou código". **Ponto crucial:** o 03 já plantou, no próprio `WALKTHROUGH.md` (§6) e `DIFF.md`, a frase de que trocar o ID por UUID seria *"obfuscation… theater… only changes how hard the bug is to find"*. **Este átomo é a encenação dessa peça:** o ID É um UUID, e não muda nada — porque a checagem ausente, não o formato do ID, sempre foi o bug.
> 2. **`atoms/A01-broken-access-control/path-traversal-basic/` (10) — o outro A01 publicado.** Já contrasta com o 03 (ownership check ausente × confinement check ausente). Referenciar de leve para ancorar a família A01 ("a app te entregou algo que não era pra você; o fix é a checagem que faltava"), sem sobrecarregar.
>
> Esta spec captura apenas as decisões *específicas* deste átomo. Onde o `idor-numeric-id` (03) já resolveu a forma (identidade via header `X-User-ID`, dados em memória sem banco, passo de contraste obrigatório, forma do DIFF/WALKTHROUGH/README, `app.py` diferente entre vulnerable/fixed), a instrução é **reusar a forma do 03**, não reinventar. Este átomo é, deliberadamente, **o amadurecimento do 03**: onde o 03 deixa o dev ingênuo pensando "é só trocar ID sequencial por UUID", o 11 prova que (a) sem ownership check, obscuridade nunca foi controle de acesso, e (b) este UUID nem é imprevisível — é reconstruível a partir de dados que a própria app expõe.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Identidade

- **ID:** `idor-uuid-guessable`
- **Categoria OWASP:** A01 — Broken Access Control
- **Pasta:** `atoms/A01-broken-access-control/idor-uuid-guessable/` (mesma convenção de diretório do `idor-numeric-id` e do `path-traversal-basic`).
- **Número sequencial:** 11
- **Porta vulnerable:** `127.0.0.1:8011`
- **Porta fixed:** `127.0.0.1:8111`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1). Container roda com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask), exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos 01–10.
- **Fase / milestone:** Fase 3, `v0.3.0` (primeiro átomo da fase; **não** fecha a fase — versionamento/release fica pra depois, fora desta spec).
- **Branch de trabalho:** `atom/idor-uuid-guessable`. **Nota de convenção:** o histórico real usa `atom/<id>` (confirmado nos head refs dos PRs #14–#19: `atom/path-traversal-basic`, `atom/command-injection-basic`, etc.), alinhado ao `CLAUDE.md` §6 — **não** a forma `atom-11-...` sugerida no briefing. Adotado o padrão do repo.
- **Theory primer (registrar link, NÃO buscar/inserir agora):** [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor). É a **mesma** página conceitual que o `idor-numeric-id` (03) já usa — correto, porque é a **mesma classe** (IDOR). O texto do link preserva **"Insecure direct object references (IDOR)"** em inglês também no README PT (convenção v0.1.0). A confirmação por fetch e a inserção no bloco de primer dos READMEs ficam para a **Fase 2** (mesma política do atom-10); o bloco segue o esqueleto verbatim dos átomos 03/10 (só troca o link/label — aqui idênticos aos do 03).
- **H1 dos READMEs (idêntico em EN e PT):** `# idor-uuid-guessable — Insecure Direct Object Reference (guessable UUID)` (espelha o H1 do 03, `— Insecure Direct Object Reference (numeric ID)`).

---

## Classe de vulnerabilidade

IDOR (Insecure Direct Object Reference), variante **objeto identificado por UUID "difícil de adivinhar"**. Uma app serve um objeto privado (um recibo) por `GET /receipt/<uuid>`, e **não verifica se o objeto pertence ao chamador**. O identificador é um UUID — que o desenvolvedor trata, implicitamente, como o próprio controle de acesso ("só quem tem o link secreto vê o recibo"). É exatamente o mesmo bug do `idor-numeric-id` (03: ownership check ausente), só que agora o ID **parece** seguro por ser opaco.

### A lição-coração: duas camadas, PESO IGUAL

> **"Um identificador difícil de adivinhar não é um controle de acesso."**

**Camada 1 — obscuridade ≠ autorização.** Mesmo que o UUID fosse *perfeitamente* aleatório (v4, CSPRNG), sem um ownership check qualquer um que **obtenha** o ID (por link compartilhado, referer, histórico do browser, log, ou vazamento) lê o objeto. A raiz é a checagem ausente — idêntica ao 03. Trocar ID sequencial por UUID só muda **quão difícil é adivinhar** o ID, não **se o servidor confere quem está pedindo**.

**Camada 2 — e este ID nem é imprevisível.** O UUID em questão é um **UUIDv1**, que empacota **timestamp** (resolução de 100 ns) e **node** (tipicamente o MAC), mais um **clock sequence** de 14 bits. Com `node` e `clock_seq` **estáveis por processo**, o UUID vira **reconstruível** a partir de dados que a app já expõe: basta um recibo próprio (pra extrair `node`+`clock_seq`) e o `issued_at` da vítima (que a app expõe em precisão de microssegundos) pra colapsar o espaço de busca a **~10 candidatos**.

**As duas camadas têm PESO IGUAL na lição** — ambas são insights essenciais e o walkthrough dá espaço equivalente a cada uma (Camada 2 é o exploit principal; Camada 1 é o passo de contraste obrigatório + a discussão do fix). **Atenção a não confundir "peso igual na lição" com "peso igual no fix":** no fix, o **ownership check é o que corrige**; o `uuid4` é **defense-in-depth**. Ver "Fix".

### Sub-lição (uma frase no walkthrough)

Seguir a RFC 4122 do v1 (que recomenda inicializar o clock sequence com valor aleatório e persisti-lo) **PIORA** a previsibilidade — um `node`+`clock_seq` estáveis são exatamente o que torna o UUID reconstruível. O detalhe do `uuid.uuid1()` do Python **randomizar o `clock_seq` a cada chamada** é uma **mitigação acidental**, não uma decisão de segurança: uma geração fiel à RFC (ou à maioria das libs fora do stdlib) mantém `node`+`clock_seq` estáveis e reabre o buraco. (Confirmado empiricamente: `uuid.uuid1()` puro randomiza o `clock_seq` por chamada — ver "O gerador de ID".)

### Por que A01 (Broken Access Control) — a moldura é a mesma do 03

O bug **não é** "input virou código" (injection). É **"input alcançou um recurso fora do seu escopo autorizado"** — o chamador pediu um recibo que não é dele e a app entregou. Isso é controle de acesso a objeto — A01, idêntico ao 03. O UUID não muda a categoria: continua sendo "a app te deu algo que não era seu". Por ser vuln de **lógica/autorização** (e não de payload), o passo de contraste obrigatório "o que a vuln NÃO é" (CLAUDE.md §5) é **mandatório** — e aqui ele carrega peso extra, porque desmonta DOIS mal-entendidos vizinhos ("IDOR é fingir ser outro user" e "UUID resolve IDOR").

### Contraste com os irmãos A01 (tabela — vai no fechamento do WALKTHROUGH; a prosa no DIFF)

| Átomo (A01) | O recurso é acessado por... | O ID é... | O que falta no código |
|---|---|---|---|
| `idor-numeric-id` (03) | trocar um ID (`/notes/1` → `/notes/2`) | inteiro sequencial | ownership check (a nota é sua?) |
| `idor-uuid-guessable` (11) | **reconstruir e usar o UUID** (`/receipt/<uuid>`) | **UUIDv1 reconstruível** | ownership check (o recibo é seu?) — **o mesmo do 03** |
| `path-traversal-basic` (10) | navegar o filesystem (`notes.txt` → `../../etc/passwd`) | caminho de arquivo | confinement check (o path caiu na pasta?) |

Os três são **"a app te entregou algo que não era pra você"**. O 03 e o 11 dividem **exatamente** a mesma causa e o mesmo fix (ownership check) — diferem só no **formato do ID**, e é justamente esse "só o formato mudou, o bug não" que é a lição do 11. O 10 divide a família A01 mas por outro eixo (confinamento de caminho, não ownership).

**Frame quotável (cravar no fechamento do WALKTHROUGH e no DIFF):** *No `idor-numeric-id` dissemos que trocar o inteiro por um UUID seria "theater" — obfuscation, não autorização. Este átomo encena a peça: o ID É um UUID, e não mudou nada, porque a checagem ausente (não o formato do ID) sempre foi o bug. Pior: este UUID (v1) devolve o próprio timestamp e node pra você, então ele nem é o segredo aleatório que todo mundo assume.*

---

## Feature simulada

**Recibos (receipts).** A app emite recibos: cada um tem um `owner`, um item, um valor e um `issued_at`. Um recibo é visto por `GET /receipt/<uuid>` — o "link privado" do recibo. Do ponto de vista do dev, o UUID no link É a proteção ("só quem recebeu o link vê o recibo"). Do ponto de vista do usuário legítimo, é um "ver meu comprovante" trivial — o tipo de feature de qualquer e-commerce, painel de pedidos ou emissor de nota.

**Tipo de átomo:** `[x] com HTML` / `[ ] API-only` — **decisão confirmada com o mantenedor nesta sessão.** Por categoria (A01) a decisão não era óbvia (03 e 10 têm HTML; o exploit aqui é computacional e poderia justificar API-only). O mantenedor escolheu **HTML mínimo**, como os dois irmãos A01. Consequência: dois templates (`index.html` dashboard + `receipt.html` detalhe), e uma **trilha browser secundária opcional** (baseline). **Ressalva cravada:** a UI é **contexto**, não meio de exploração — o `<form>` NÃO executa o exploit (a reconstrução do UUID é um cálculo, feito por script). **Burp é a trilha principal**: é onde o aluno planta a request de criação, lê o `issued_at` da vítima, e dispara os ~10 candidatos.

**Modelo de trilhas (CLAUDE.md §3.3):** Burp **principal** (as requests — criar, ler o dashboard, testar candidatos — todas rodam no Repeater/Intruder); browser **secundário opcional** (só o baseline: abrir o dashboard, criar o próprio recibo pelo botão, ver o próprio recibo). O browser **não** consegue setar `X-User-ID` nem reconstruir o UUID — então os passos-chave são Burp, igual ao Step 4 do 03.

---

## Modelo de identidade e dados — sem banco

**Sem banco** (como o 03; e como o 03, a escolha segue a superfície do bug: IDOR não depende da camada de storage — é uma checagem de autorização ausente acima de qualquer store). Dados em estruturas Python em memória. Nota "Stack note — no database" no README, espelhando o 03.

**Identidade simulada — reusar o `X-User-ID` do 03.** O header `X-User-ID` nomeia o chamador; é self-asserted (o aluno diz quem é). Dois usuários, com papéis explícitos:

- **`mallory`** — a **atacante** (você). É o **default** quando o header está ausente (o operador do lab É a atacante). Cria o próprio recibo.
- **`alice`** — a **vítima**. Tem um recibo **seedado** no startup — o alvo que a `mallory` não deveria conseguir ler.

(Nomes escolhidos por clareza de papel: `mallory` é a atacante canônica na literatura de segurança; `alice` a parte honesta. Diferente do 03, que usou IDs numéricos `1/2/3` — aqui, com exatamente dois papéis assimétricos, nomes deixam o "atacante × vítima" óbvio. O header e a semântica self-asserted são idênticos ao 03.)

**Estrutura do recibo (dado fake óbvio, CLAUDE.md §8.3 — sem PII real, sem cartão real):**

```python
{"id": "<uuid>", "owner": "alice", "item": "Noise-cancelling headphones",
 "amount": "$1,299.00", "issued_at": <datetime tz-aware UTC, precisão de µs>}
```

**Constantes de identidade, store e seed (topo do `app.py`). As constantes `ATTACKER`/`VICTIM` e o shape do store são idênticos nas duas versões (vulnerable e fixed); só a derivação do `issued_at` em `_add_receipt` muda no fixed (ver "Fix"):**

```python
# --- Simulated identity (same convention as idor-numeric-id) ---
ATTACKER = "mallory"   # you; the default caller when X-User-ID is absent
VICTIM   = "alice"     # the victim; her receipt is seeded at import

# --- In-memory store (no database, like idor-numeric-id) ---
RECEIPTS = {}          # str(uuid) -> {"id","owner","item","amount","issued_at"}

def _add_receipt(owner, item, amount):
    u = _new_receipt_id()                # v1 (vulnerable) / v4 (fixed) — see "O gerador de ID"
    issued_at = _issued_at_from(u)       # fixed/: datetime.now(timezone.utc), since v4 has no time
    RECEIPTS[str(u)] = {"id": str(u), "owner": owner, "item": item,
                        "amount": amount, "issued_at": issued_at}
    return RECEIPTS[str(u)]

# Seed the victim's receipt at import (runs AFTER the generator helpers are defined).
_add_receipt(VICTIM, "Noise-cancelling headphones", "$1,299.00")
```

`ATTACKER` é o default de `X-User-ID` em `GET /`, `POST /receipt` e `GET /receipt/<uuid>`; o seed da vítima usa `VICTIM`. `POST /receipt` acrescenta o recibo do chamador. (Estado mutável de processo único — restart zera; aceitável no lab, notar.)

---

## Rotas

Imports necessários: `import os`, `import uuid`, `import random`, `from datetime import datetime, timezone, timedelta`, `from flask import Flask, request, render_template, abort`. (**Sem** `sqlite3`, **sem** `subprocess`. `abort` usado nas duas versões — igual ao 03.)

### `GET /` — dashboard (o canal de vazamento do `issued_at`)

Renderiza `index.html`: saúda o chamador (`X-User-ID`, default `mallory`), oferece o botão de criar recibo, e mostra a **tabela de overview de TODOS os recibos** com `owner` + `issued_at` (precisão de µs), **sem** o UUID. É aqui que o `issued_at` da vítima vaza — metadado que o dev considera "inofensivo", enquanto o detalhe "sensível" fica atrás do UUID.

```python
@app.route("/")
def index():
    caller = request.headers.get("X-User-ID", ATTACKER)
    overview = sorted(RECEIPTS.values(), key=lambda r: r["issued_at"])
    return render_template("index.html", caller=caller, overview=overview)
```

> **Enquadramento (importante pra "um átomo = uma vuln"):** o overview expor `owner`+`issued_at` **não é uma segunda vulnerabilidade a corrigir** — é o **ambiente/superfície realista** que torna a Camada 2 (reconstrução) possível. Apps reais expõem `created_at`/`issued_at` em listagens o tempo todo (serialização default de datetime em ORMs/JSON já vem com microssegundos). A **única** vuln sob estudo é o ownership check ausente em `GET /receipt/<uuid>`. Por isso o overview é **idêntico nas duas versões** (vulnerable e fixed) — ver "Fix": no fixed ele fica **inerte** (v4 não é reconstruível a partir de timestamp, e o check bloqueia o acesso de qualquer forma), o que **prova** que o vazamento nunca foi o cerne.

### `POST /receipt` — criar o próprio recibo

Cria um recibo para o chamador (`X-User-ID`) e renderiza `receipt.html`. É como a `mallory` obtém um recibo **do mesmo processo/gerador** (pra extrair `node`+`clock_seq`) e como o baseline do browser funciona (botão "Create my receipt").

```python
@app.route("/receipt", methods=["POST"])
def create_receipt():
    caller = request.headers.get("X-User-ID", ATTACKER)
    r = _add_receipt(caller, "Mechanical keyboard", "$499.00")
    return render_template("receipt.html", receipt=r)
```

### `GET /receipt/<uuid:receipt_id>` — **a rota vulnerável**

Busca o recibo pelo ID e o devolve — **sem** ownership check. O converter `<uuid:...>` do Flask aceita qualquer UUID RFC-4122 (v1 e v4), então a mesma rota serve as duas versões.

```python
@app.route("/receipt/<uuid:receipt_id>")
def view_receipt(receipt_id):
    r = RECEIPTS.get(str(receipt_id))
    if r is None:
        abort(404)
    # VULNERABLE: no ownership check — any caller who holds (or reconstructs)
    # the id reads the receipt. The unguessable-looking UUID is treated as the
    # access control; it is not one.
    return render_template("receipt.html", receipt=r)
```

- **Source:** o `<uuid>` do path (o objeto pedido) + o `X-User-ID` (a identidade — que o vulnerable **ignora**, igual ao 03).
- **Sink conceitual:** o retorno do recibo sem comparar `r["owner"]` com o chamador. O bug é **o que não está lá** (a checagem), exatamente como o 03 — não greppa por string perigosa; greppa por endpoint que devolve objeto user-scoped e pergunta "cadê o check de ownership?".
- **`abort(404)`** para recibo inexistente: higiene operacional, idêntica nas duas versões (ortogonal ao bug e ao fix). É o que devolve os 9 "não" quando a `mallory` testa os ~10 candidatos.

### Versão **fixed** — dois eixos mudam (o check + o gerador)

```python
@app.route("/receipt/<uuid:receipt_id>")
def view_receipt(receipt_id):
    caller = request.headers.get("X-User-ID", ATTACKER)
    r = RECEIPTS.get(str(receipt_id))
    if r is None:
        abort(404)
    # FIXED (the fix that matters): serve the receipt only to its owner.
    if r["owner"] != caller:
        abort(403)
    return render_template("receipt.html", receipt=r)
```

E o gerador (defense-in-depth) troca de UUIDv1 estável para UUIDv4:

```python
# vulnerable:
def _new_receipt_id():
    return uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)   # reconstructible

# fixed (defense-in-depth):
def _new_receipt_id():
    return uuid.uuid4()                                    # CSPRNG; no time/node
```

Como o v4 não embute timestamp, no fixed o `issued_at` vem de `datetime.now(timezone.utc)` em vez de derivado do ID (ver "O gerador de ID"). O `app.py` **DIFERE** entre vulnerable e fixed (o bug/checagem e o gerador moram no código) — igual ao 03 e ao 10, inverso do par XSS.

**Status code do fix: `403` (não 404).** Escolhido `403` pra **alinhar com o irmão direto 03** (mesma classe IDOR; o recibo é um recurso legítimo da app que o chamador não está autorizado a ver — "forbidden" é semanticamente certo). Nota de contraste no DIFF: o `path-traversal-basic` (10) usa `404` porque lá o "recurso" está **fora do domínio** da app (não vaza existência); aqui, como no 03, é um objeto **da** app que existe mas não é seu → `403`. Um `404` seria defense-in-depth extra (não vaza que o recibo existe), mencionável no DIFF, mas mantemos `403` pela consistência com o 03.

---

## O gerador de ID — UUIDv1 com `node` + `clock_seq` estáveis (a decisão técnica)

Esta seção é o coração técnico do átomo. **Registrar como decisão técnica** (pedido explícito do mantenedor).

### Por que `uuid.uuid1()` puro NÃO serve

`uuid.uuid1(node=None, clock_seq=None)` do CPython:
- `node` default = `uuid.getnode()` → **estável por processo** (MAC, ou fallback aleatório-multicast cacheado no processo).
- `clock_seq` default = `random.getrandbits(14)` → **randomizado a cada chamada**.

O `clock_seq` randomizado por chamada é o problema pro ataque: dois recibos do mesmo processo teriam `clock_seq` **diferentes**, então a `mallory` **não** poderia aplicar o `clock_seq` do próprio recibo ao da vítima. **Confirmado empiricamente** que `uuid.uuid1()` randomiza o `clock_seq` por chamada. Ou seja: o stdlib do Python, por acaso, tem uma **mitigação acidental**.

### O que a app faz (fiel à RFC / à maioria das libs)

Fixa **ambos** `node` e `clock_seq` por processo:

```python
_NODE = uuid.getnode()            # stable per process
_CLOCK_SEQ = random.getrandbits(14)   # drawn ONCE at import, then stable (RFC 4122:
                                       # initialize the clock sequence randomly, then persist it)

def _new_receipt_id():
    return uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)
```

- **Decisão:** `_CLOCK_SEQ` é sorteado **uma vez** no import e reusado (modelo RFC "inicializa aleatório, persiste"). É o mais **honesto** (modela geradores reais) e reforça a lição: um `clock_seq` *aleatório* não salva, porque é **estável** e portanto **recuperável de UMA amostra** (o recibo da própria `mallory`). Alternativa mais simples/determinística: hardcodar `_CLOCK_SEQ = 0x0a1b` — mencionar como opção, mas preferir o sorteio-único.
- A `mallory` **não precisa saber o valor** de `node`/`clock_seq` — ela os **extrai** do próprio UUIDv1 (`uuid.UUID(x).node`, `.clock_seq`). Como são constantes de processo, valem para o UUID da vítima.

### `issued_at` derivado do timestamp do próprio UUID (reconstrução determinística)

**Decisão:** no vulnerable, o `issued_at` é **derivado do timestamp que o próprio UUIDv1 embute**, garantindo que o campo exposto e o ID descrevem **o mesmo instante** → reconstrução exata, exatamente **10 candidatos**.

```python
_UUID_EPOCH_100NS = 0x01b21dd213814000   # 100ns ticks between 1582-10-15 and 1970-01-01
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

def _issued_at_from(u):
    unix_us = (u.time - _UUID_EPOCH_100NS) // 10   # integer microseconds (drops the 100ns digit)
    return _UNIX_EPOCH + timedelta(microseconds=unix_us)
```

- `u.time` é o campo de 60 bits do v1 (contagem de 100 ns desde 1582-10-15); `.time` já mascara o nibble de versão.
- A divisão inteira `// 10` **descarta exatamente o dígito de 100 ns** (o sub-microssegundo). Esse é o **único dígito desconhecido** pra `mallory` → **10 candidatos** (0..9).
- **Exposição:** `issued_at.isoformat(timespec="microseconds")` → **sempre** 6 casas decimais (ISO 8601), mesmo se os µs terminarem em zero. **Usar `timespec="microseconds"` explícito** — o `isoformat()` cru **omite** a parte fracionária quando `microsecond == 0`, o que degradaria a precisão vista pela atacante (edge de 1-em-1M). Com `timespec` fixo, ela sempre tem precisão de µs → sempre 10 candidatos.
- **Aritmética inteira (não float):** derivar via `timedelta(microseconds=unix_us)` com `unix_us` **inteiro** — evita a perda de precisão de `double` que apareceria em `u.time / 1e7` (segundos de 2026 com precisão de µs beira o limite de 15–16 dígitos significativos do float).

### A cadeia de reconstrução (o exploit — snippet do walkthrough)

```python
import uuid
from datetime import datetime, timezone, timedelta

UUID_EPOCH_100NS = 0x01b21dd213814000
UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# 1) fingerprint recovered from YOUR OWN receipt (a UUIDv1 the app handed you)
mine = uuid.UUID("<your-receipt-id>")
node, clock_seq = mine.node, mine.clock_seq        # process constants → shared with the victim's id

# 2) victim's issued_at, copied from the dashboard (microsecond precision)
issued_at = datetime.fromisoformat("2026-07-09T13:22:41.874219+00:00")

# 3) rebuild the 60-bit time field to the microsecond; only the sub-µs 100ns digit (0..9) is unknown
us = (issued_at - UNIX_EPOCH) // timedelta(microseconds=1)
base = us * 10 + UUID_EPOCH_100NS

def build_v1(t, clock_seq, node):
    fields = (t & 0xffffffff, (t >> 32) & 0xffff, (t >> 48) & 0x0fff,
              (clock_seq >> 8) & 0x3f, clock_seq & 0xff, node)
    return uuid.UUID(fields=fields, version=1)

for d in range(10):
    print(build_v1(base + d, clock_seq, node))     # 10 candidate UUIDs; exactly one is the victim's
```

- O empacotamento de campos espelha **exatamente** o `uuid1()` do CPython (`time_low/time_mid/time_hi_version` + `clock_seq_hi_variant/clock_seq_low` + `node`, `version=1`). Como `node` e `clock_seq` são idênticos aos da vítima e o `time` só varia no dígito de 100 ns, **um** dos 10 candidatos reproduz o UUID da vítima **bit a bit**.
- A `mallory` dispara os 10 candidatos em `GET /receipt/<uuid>` (Burp Repeater — 10 sends; ou Intruder com os 10 na posição do path; ou curl loop). 9 → `404`, 1 → `200` com o recibo da `alice`.
- **Nota sobre o `_last_timestamp` monotônico do CPython:** o `uuid1()` bumpa um `_last_timestamp` global só quando duas chamadas caem no mesmo tick de 100 ns (ou o relógio anda pra trás). Pra recibos emitidos com segundos/minutos de diferença (seed no startup × POST da `mallory` no exploit), não há bump — e, de todo modo, como derivamos `issued_at` **do próprio `u.time`**, a reconstrução é **robusta** mesmo se um bump ocorresse (o `issued_at` refletiria o `u.time` bumpado).

---

## O container

`Dockerfile` **idêntico** entre vulnerable e fixed (como todos os átomos). HTML → **inclui** `COPY templates ./templates`. `uuid`, `random`, `datetime` são stdlib → **nada** de `apt`, e só o Flask no pip. Esqueleto dos átomos 01/08 (o 03 é o mais próximo — sem banco, sem seed em disco):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

`app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py` (idêntico ao 03/10). `docker-compose.yml`: `127.0.0.1:8011:5000` (vulnerable), `127.0.0.1:8111:5000` (fixed) — esqueleto de duas services do 03/10, **sem** `sysctls`.

---

## Renderização — autoescape (um átomo = uma vuln)

Todos os valores nos templates (`{{ caller }}`, `{{ receipt.item }}`, `{{ receipt.owner }}`, `{{ receipt.id }}`, `issued_at`, etc.) vão com o **autoescape padrão do Jinja LIGADO** — **sem `|safe`**, nas duas versões. Papel: os dados são fake e benignos, mas o `caller` vem de um header controlável (`X-User-ID`) e é ecoado no dashboard; sem escape, isso seria um **reflected XSS acidental empilhado** por cima do IDOR — violando "um átomo = uma vuln" (CLAUDE.md §2). Cravar nos comentários/DIFF: o escape **não é** o fix de IDOR (o fix é o ownership check); é higiene pra manter **exatamente um** bug. Igual ao `<pre>` escapado do 09/10.

---

## HTML

Dois templates, ≤40 linhas cada, CSS ≤5 linhas inline, **sem JS** (nada client-side é código causal aqui), sem framework. Reusar o esqueleto dos templates do 03 (banner, footer de Burp, `<style>` sans-serif/720px).

**`index.html`** (dashboard — idêntico em vulnerable/fixed):
- Banner verbatim: `⚠️ Intentionally vulnerable. Run locally only.` (entidade `&#9888;`).
- `<h1>Receipts</h1>`, linha "Logged in as `{{ caller }}`".
- `<form method="post" action="/receipt"><button>Create my receipt</button></form>` (o baseline clicável do browser).
- **Tabela de overview:** `owner` + `issued_at` (µs) de todos os recibos — **sem** o UUID. É o canal de vazamento (visível no browser e legível no Burp via `GET /`).
- Footer: `Open with Burp proxy enabled, interact once, then work from Burp Repeater.`

**`receipt.html`** (detalhe — idêntico em vulnerable/fixed):
- Banner verbatim.
- `<h1>Receipt</h1>` e os campos: `id` (o UUID — é daqui que a `mallory` lê o próprio ID/fingerprint), `owner`, `item`, `amount`, `issued_at`.
- `<a href="/">&larr; Back</a>` + footer de Burp.

Ambos os templates são **idênticos entre vulnerable e fixed** (o bug mora no `app.py`, não no template — inverso do par XSS).

---

## Fix

O fix corrige os **dois eixos** que a lição de duas camadas expõe. O DIFF deve deixar **cristalino** qual é qual:

```diff
+# defense-in-depth (Layer 2): swap the reconstructible generator for a CSPRNG one.
-def _new_receipt_id():
-    return uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)
+def _new_receipt_id():
+    return uuid.uuid4()
 ...
 @app.route("/receipt/<uuid:receipt_id>")
 def view_receipt(receipt_id):
+    caller = request.headers.get("X-User-ID", ATTACKER)
     r = RECEIPTS.get(str(receipt_id))
     if r is None:
         abort(404)
-    # VULNERABLE: no ownership check — any caller who holds (or reconstructs)
-    # the id reads the receipt.
+    # FIXED (the fix that matters, Layer 1): serve the receipt only to its owner.
+    if r["owner"] != caller:
+        abort(403)
     return render_template("receipt.html", receipt=r)
```

(No fixed, `_add_receipt` também passa a usar `issued_at = datetime.now(timezone.utc)` em vez de derivar de `u.time`, porque o v4 não embute timestamp — mudança incidental que acompanha a troca do gerador.)

### A honestidade da lição de duas camadas (obrigatória no DIFF/WALKTHROUGH)

- **O ownership check é O fix.** Ele **sozinho** corrige: você poderia manter o UUIDv1 estável **e** o vazamento de `issued_at` no dashboard, e ainda assim a `mallory` levaria `403` — porque agora o servidor **confere quem pede**. Obscuridade nunca foi o controle; a checagem é.
- **O `uuid4` é defense-in-depth, e sozinho NÃO corrige.** Trocar só o gerador (mantendo o check ausente) deixa o buraco: qualquer um que **obtenha** o ID (link, referer, log, histórico) ainda lê o recibo — e o passo "o que a vuln NÃO é" prova que o endpoint nem olha pra identidade. O `uuid4` só fecha a **rota de reconstrução** (Camada 2); não fecha o **acesso sem autorização** (Camada 1).
- **Por que os dois, então?** Porque a lição tem duas camadas de peso igual, e um fix honesto corrige as duas: a autorização (o cerne) **e** a fonte de previsibilidade (a comodidade falsa). Ordem de prioridade explícita: **check primeiro, gerador depois.**

### Notas obrigatórias no DIFF.md

1. **"Trocar o ID por UUID é jogo perdido (sozinho)"** — paralelo direto ao "escaping é jogo perdido" da série de injection e ao "blocklist é jogo perdido" do 10. O 03 já disse que UUID seria "theater"; aqui está a prova. A correção não é **esconder/embaralhar o ID** — é **conferir o dono**. Amarrar ao 03 (mesmo fix) e ao 10 (mesma família "valide o resultado contra o permitido, não confie na forma do input").
2. **IDOR não greppa por string perigosa.** Como no 03: você acha IDOR **lendo endpoints** que devolvem objeto user-scoped e perguntando "cadê o check de ownership?". Aqui há o agravante de que o UUID **parece** seguro e desarma o revisor desatento ("tem UUID, deve estar ok").
3. **A sub-lição da RFC (uma nota):** persistir o `clock_seq` (fiel à RFC/libs) **piora** a previsibilidade; o `uuid.uuid1()` randomizar por chamada é mitigação **acidental**. Se você **precisa** de v1 por algum motivo, não confie no timestamp/node como segredo — mas o certo é v4 pra IDs opacos, e **sempre** o ownership check.
4. **`403` vs `404` (contraste com o 10):** aqui `403` (como o 03 — objeto da app, não seu); no 10, `404` (recurso fora do domínio). Mencionar que `404` vazaria menos existência (defense-in-depth), mas `403` é o certo semanticamente e mantém consistência com o irmão direto.
5. **O overview do dashboard é ambiente, não segunda vuln** (ver "Rotas") — permanece **idêntico** no fixed pra provar que o vazamento de `issued_at` nunca foi o cerne; o check o torna inerte. (Coarsen o timestamp pra segundos seria defense-in-depth adicional — mencionar, **não** aplicar, pra manter o fix nos dois eixos que o mantenedor travou.)

---

## Walkthrough — estrutura e payloads

Trabalhado **primariamente no Burp** (as requests); browser é a trilha secundária de baseline. Cada request mostra um bloco colável (request-line no Repeater). A reconstrução é o snippet Python da seção "O gerador de ID". Estrutura de beats:

> **Abertura — plantar as duas camadas.** A seção "Context" tease: *você vai ler o recibo da `alice` sem nunca receber o link dela — reconstruindo o UUID a partir de dados que a app te dá. E, no fim, vai ver que nem precisava reconstruir nada: o endpoint nunca checa dono, então qualquer ID que você segure já bastava. Duas camadas, uma causa: não há check de autorização.*

### Context + Spot the bug
- **Context:** app de recibos; `GET /receipt/<uuid>` é o "link privado". O dev trata o UUID como o controle de acesso. Trilha no Burp (browser opcional pro baseline).
- **Spot the bug:** mostrar a view vulnerable. Apontar que **não há** comparação entre `r["owner"]` e o chamador — o bug é **o que não está lá** (idêntico ao 03). Pergunta de auditoria: **"onde este endpoint confere que o recibo é do chamador?"** Resposta: em lugar nenhum.

### How auth works in this lab (subseção curta, reusar do 03)
`X-User-ID` self-asserted nomeia o chamador; default `mallory` (você). O vulnerable **ignora** o header em `GET /receipt/<uuid>` (o Step de contraste torna isso concreto). Dois usuários: `mallory` (atacante/você) e `alice` (vítima, recibo seedado).

### Baseline — a ferramenta funcionando (estabelece o "normal")
- `POST /receipt` (com `X-User-ID: mallory`) → cria o recibo da `mallory`; a resposta traz o **UUID** e o `issued_at`. Ler o próprio recibo (`GET /receipt/<mallory-uuid>`, `X-User-ID: mallory`) → `200`, dados da `mallory`. A feature faz o que promete.
- Observação: repare que o `id` do seu recibo é um **UUIDv1** (dá pra ver pela versão/variant). Guarde-o — ele é o seu "sample do gerador".

### Step 1 — Read the metadata the app leaks (o vazamento do `issued_at`)
- `GET /` (dashboard) → a tabela lista `owner` + `issued_at` de todos, incluindo o `issued_at` da **`alice`** em precisão de µs. **Você não tem o UUID da `alice`** — mas tem o timestamp dela.
- Lição do beat: a app considera esse metadado "inofensivo" e esconde o "sensível" atrás do UUID. As duas premissas vão cair.

### Step 2 — Recover the generator fingerprint (`node` + `clock_seq`)
- Parse do **seu próprio** UUID (do Baseline): `uuid.UUID(mine).node`, `.clock_seq`. São **constantes de processo** → valem pro UUID da `alice`.
- **Sub-lição (uma frase):** que o `clock_seq` seja fixo é a app sendo *fiel à RFC*; o `uuid.uuid1()` do Python randomizar por chamada seria uma mitigação **acidental**. Fidelidade à RFC aqui **piora** a segurança.

### Step 3 — Reconstruct the victim's UUID (~10 candidatos)
- Rodar o snippet (seção "O gerador de ID"): `node`+`clock_seq` (seus) + `issued_at` da `alice` (µs) → **10 candidatos** (só o dígito de 100 ns é desconhecido).
- Explicar o porquê do "10": v1 tem resolução de 100 ns, o `issued_at` exposto tem resolução de 1 µs = 10×100 ns → resta 1 dígito.

### Step 4 — Access the victim's receipt (IDOR confirmado)
- Disparar os 10 candidatos em `GET /receipt/<uuid>` (Repeater — 10 sends; ou Intruder com 10 payloads na posição do path). 9 → `404`, **1 → `200`** com o recibo da **`alice`**. IDOR confirmado: você leu o recibo de outro usuário sem nunca ter recebido o link.
- Request-line de exemplo: `GET /receipt/<candidate-uuid> HTTP/1.1` / `Host: 127.0.0.1:8011`.

### Step 5 — What the vuln is NOT (o passo de contraste OBRIGATÓRIO — CLAUDE.md §5)
Isola a causa real e desmonta os DOIS mal-entendidos vizinhos. Análogo direto ao Step 4 do 03.
- **Payload:** manter o path no **seu próprio** recibo (`GET /receipt/<mallory-uuid>`, um ID que você legitimamente possui) e trocar só o header: `X-User-ID: alice`.
- **Observação:** resposta **inalterada** — ainda o recibo da `mallory`, `200`. O endpoint vulnerable **nunca lê** o `X-User-ID`. Não há identidade pra "spoofar".
- **Lição (cravar, duas camadas):**
  - *Camada 1:* o bug **não é** "a `mallory` fingiu ser a `alice`" nem "o UUID era adivinhável demais". É que **não existe check de autorização** — qualquer ID que você segure, **por mais aleatório que fosse**, seria servido. Por isso trocar pra `uuid4` **sozinho não resolveria**: v4 muda o quão difícil é **adivinhar** o ID, não **se o servidor confere o dono**.
  - *Camada 2:* e, como o Step 3 provou, este UUID (v1) nem é difícil de adivinhar — ele te devolve o próprio timestamp+node.
  - Uma causa, duas camadas: **ausência de autorização.**

### Fechamento — `Why this is IDOR, and why the UUID never helped`
- Tabela de contraste A01 (seção "Classe de vulnerabilidade") + o frame quotável ("no `idor-numeric-id` dissemos que UUID seria theater; aqui está a peça encenada").
- Amarrar ao 03 (mesmo fix: ownership check) e, de leve, ao 10 (família A01, "a app te deu algo que não era seu; o fix é a checagem que faltava"). **Sem** foreshadow de átomos não publicados (12+).

### Impact (honesto — CLAUDE.md sem overclaim)
Escalação **horizontal** de privilégio: leitura de dados de outro usuário do **mesmo nível** (o recibo da `alice` — valor, item). **NÃO é RCE. NÃO é escalação vertical.** Enquadrar sem inflar: num alvo real, dados de recibo/pedido podem conter PII que **encadeia** pra mais ataques, mas o impacto do átomo **é** a leitura cross-user em si.

### Exploitation via browser (secondary track, optional) + Why the fix works
- **Browser (secundária, opcional):** abrir o dashboard (`http://127.0.0.1:8011/`), criar o próprio recibo pelo botão, ver o próprio recibo, e ler o `issued_at` da `alice` na tabela. **Mas** o browser **não** seta `X-User-ID` nem reconstrói o UUID — então os Steps 2–5 são **Burp** (igual ao Step 4 do 03 não ter equivalente no browser). Baixa fricção só pro baseline.
- **Why the fix works (porta 8111):** repetir a cadeia. (a) O ownership check: `GET /receipt/<seu-uuid>` como `X-User-ID: alice` → **`403`** (você segura um ID válido e ainda assim é barrado — prova que o check é o fix). (b) O `uuid4`: seu recibo agora é v4, sem timestamp/node → a reconstrução **nem começa**. (c) O dashboard ainda vaza `issued_at` (idêntico) — mas é **inerte**: v4 não é reconstruível e o check bloqueia de todo jeito. Cravar: **o check corrige sozinho; o v4 é defense-in-depth.**

---

## Dependências extras

```
Flask==3.0.0
```

Idêntico aos átomos 01/02/06/07/08/09/10. `uuid`, `random`, `datetime` são stdlib. **Nada** de pip além do Flask, **nada** de `apt`, **sem** banco. CLAUDE.md §3.6 respeitado.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria | **A01 — Broken Access Control** | "Input alcançou recurso fora do escopo" (acesso), não injection. Mesma moldura e mesmo fix do 03. |
| Classe / variante | **IDOR com UUID "adivinhável"** | Amadurecimento do 03: prova que o formato do ID (UUID) não é o controle; a checagem ausente é. |
| Lição-coração | **Duas camadas, peso igual** | (1) obscuridade ≠ autorização (mesmo v4 sem check = IDOR); (2) e este v1 é reconstruível. |
| Feature | **Recibos** (`GET /receipt/<uuid>`), stateless em memória | O UUID no "link privado" É a falsa proteção. Sem banco (como o 03; storage segue a superfície do bug). |
| Tipo de átomo | **Com HTML** (2 templates) | **Confirmado com o mantenedor.** Por categoria não era óbvio; escolhido HTML como 03/10. UI = contexto, não meio de exploração. |
| Identidade | **`X-User-ID`** (reuso do 03); `mallory` (atacante/default) + `alice` (vítima) | Reusa o modelo do irmão direto. Nomes por clareza de papel (2 papéis assimétricos). |
| Método HTTP | `GET /` (dashboard/leak), `POST /receipt` (mint), `GET /receipt/<uuid>` (vuln) | REST-ish mínimo. `POST` dá à `mallory` um sample do mesmo gerador (extrair node+clock_seq). |
| Canal de vazamento | **Dashboard em `GET /`** expõe `owner`+`issued_at` (µs), sem UUID | Metadado "inofensivo" que alimenta a Camada 2. Ambiente realista, **não** segunda vuln; idêntico no fixed (inerte). |
| Gerador (vulnerable) | **UUIDv1 com `node`+`clock_seq` estáveis** (`clock_seq` sorteado 1× no import) | Fiel à RFC 4122 (inicializar o clock_seq aleatório e persisti-lo). `uuid1()` puro randomiza clock_seq/chamada (mitigação acidental) — não serve. |
| `issued_at` | **Derivado do `u.time` do próprio UUID**, exposto com `isoformat(timespec="microseconds")` | Garante que ID e timestamp descrevem o mesmo instante → reconstrução determinística, exatamente 10 candidatos. Aritmética inteira (sem float). |
| Fix (o que importa) | **Ownership check** `if r["owner"] != caller: abort(403)` | O cerne. Corrige sozinho mesmo mantendo v1 + o vazamento. Mesmo fix do 03. |
| Fix (defense-in-depth) | **Gerador → `uuid4()`** (+ `issued_at = now()`) | Fecha a rota de reconstrução (Camada 2). **Sozinho NÃO corrige** (check ausente = ainda IDOR). |
| Status code do fix | **`403`** | Alinha com o 03 (objeto da app, não seu). `404` (como o 10) seria defense-in-depth extra — nota no DIFF, não aplicado. |
| Renderização | Autoescape padrão, **sem `\|safe`**, em ambas | `X-User-ID` ecoado no dashboard → evita reflected XSS acidental empilhado. Não é o fix; é "um bug só". |
| Nº de templates | **Dois** (`index.html` dashboard + `receipt.html` detalhe), idênticos entre versões | Espelha 03/10. Bug no `app.py`, não no template. |
| `app.py` vulnerable × fixed | **Diferem** (check + gerador) | Igual ao 03 e ao 10, inverso do par XSS. **Dois** eixos mudam — justificado pela lição de duas camadas; DIFF separa "o fix" de "defense-in-depth". |
| Dockerfile | Esqueleto 01/03 **+ `COPY templates`** | Sem `apt`, sem banco, sem seed em disco. Idêntico entre as versões. |
| User do container | **root** (sem `USER`, como todos) | Sem relevância pro bug aqui (não há leitura de FS); manter o padrão do repo. |
| Trilha Burp × browser | **Burp principal, browser secundário (só baseline)** | Reconstrução e Step de contraste são Burp; browser não seta header nem reconstrói. Igual ao 03. |
| Nº de steps | **Baseline + 5 steps + fechamento** | Baseline → leak → fingerprint → reconstruct → access → "o que a vuln NÃO é". Step 5 = contraste obrigatório. |
| Impacto | **Escalação horizontal** (ler recibo de outro user). **Não** RCE, **não** vertical. | Honesto, sem overclaim (pedido do mantenedor). |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Todos são itens de **validação na geração** (CLAUDE.md §11), não decisões pendentes. Os 3 primeiros são os riscos que o mantenedor pediu explicitamente; os demais são de higiene técnica desta spec.

1. **`node` E `clock_seq` estáveis entre recibos do mesmo processo.** Criar 2+ recibos, extrair `.node` e `.clock_seq` de cada, confirmar que são idênticos. (Se `clock_seq` variar, revisar a fixação no `app.py`.)
2. **Reconstrução colapsa a ~10 candidatos e UM reproduz o UUID da vítima bit a bit.** Rodar a cadeia (node+clock_seq do recibo da atacante + `issued_at` µs da vítima) e confirmar que exatamente um dos candidatos == UUID seedado. **Anotar o número real de candidatos observado** (esperado: 10).
3. **Fallback de precisão.** Se a precisão de µs **não** colapsar como esperado (ex.: skew inesperado, ou o candidato certo não bater), ajustar a precisão do `issued_at` exposto (documentar o ajuste). Alternativa registrada: derivar `issued_at` de `u.time` já elimina skew — se ainda assim falhar, investigar o empacotamento de campos.
4. **`isoformat(timespec="microseconds")` sempre emite 6 casas** (mesmo com µs terminando em zero) — evita o edge do `isoformat()` cru omitir a fração quando `microsecond == 0`.
5. **`uuid.getnode()` estável no container** durante o processo; anotar se retorna o MAC do eth0 ou o fallback aleatório-multicast (ambos servem: estável + recuperável).
6. **Aritmética inteira (sem float)** na derivação e na reconstrução (`timedelta(microseconds=int)`), pra não perder precisão de µs em `double`.
7. **`_last_timestamp` monotônico** não interfere pra recibos emitidos com segundos de diferença (seed × POST). Derivar `issued_at` de `u.time` torna a reconstrução robusta a um eventual bump — confirmar.
8. **Fixed (8111):** (a) `GET /receipt/<id-próprio>` como dono → `200`; como não-dono → **`403`**; (b) recibo do fixed é **v4** (`.version == 4`) → reconstrução impossível; (c) o dashboard **ainda** expõe `issued_at` (idêntico ao vulnerable) → confirmar que fica inerte.
9. **Converter `<uuid:...>`** aceita os candidatos reconstruídos (v1 bem-formados) e o v4 do fixed; candidato inexistente → `404`, o correto → `200`.

**Bloqueante remanescente:** nenhum. Spec pronta pra revisão do mantenedor; nada exige decisão adicional antes da geração — resta só a validação acima na Fase 2.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é **o amadurecimento do `idor-numeric-id` (03)**. Cada parágrafo do walkthrough deve poder ser lido com o 03 aberto ao lado; a diferença ("o ID virou UUID e o bug **não** mudou — porque a checagem ausente, não o formato do ID, sempre foi o bug") tem que estar visível. **Abrir e fechar** na lição de duas camadas.
- **Leitura obrigatória antes de gerar (CLAUDE.md §10.5):** `idor-numeric-id` (03) **inteiro** (irmão direto — reusar identidade `X-User-ID`, passo de contraste, framing A01, forma de README/WALKTHROUGH/DIFF; e citar verbatim a frase de "theater/obfuscation" do §6 do WALKTHROUGH e do DIFF do 03) **e** `path-traversal-basic` (10) (o outro A01 — família "checagem ausente", contraste de status code 403×404).
- **Átomo stateless, sem banco** (como o 03): dados em `dict`/estruturas Python em memória, `X-User-ID`, seed do recibo da `alice` no import. **Sem** `sqlite3`, `init_db()`, `DB_PATH`.
- **`app.py` DIFERE entre vulnerable e fixed** (check + gerador). `Dockerfile` idêntico entre as versões. Templates idênticos entre as versões (bug no `app.py`).
- **O gerador é o ponto técnico frágil** — seguir à risca a seção "O gerador de ID": `_NODE = uuid.getnode()`, `_CLOCK_SEQ = random.getrandbits(14)` (uma vez no import), `uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)`; `issued_at` derivado de `u.time` com aritmética inteira; exposto com `timespec="microseconds"`. **Não** usar `uuid.uuid1()` puro (randomiza clock_seq → ataque não funciona).
- **Fix nos dois eixos, com prioridade explícita:** o ownership check é **O** fix; o `uuid4` é defense-in-depth. O DIFF e o WALKTHROUGH devem afirmar que o check **sozinho** corrige e o `uuid4` **sozinho não**. Não deixar o leitor achar que "trocar pra v4" foi a correção.
- **Passo de contraste obrigatório (Step 5)** — manter o path no recibo da própria atacante e trocar só o `X-User-ID`; a resposta não muda → prova que o endpoint ignora identidade (missing check), não é "spoof" nem "UUID fraco". Espelha o Step 4 do 03.
- **Impacto honesto:** escalação **horizontal**; **não** chamar de RCE nem de escalação vertical. Sem overclaim.
- **Renderização sempre escapada** (`X-User-ID` ecoado) — comentar que **não é** o fix; é higiene de "um bug só".
- **Snippet de reconstrução no walkthrough** é didático e proporcional (CLAUDE.md §8.4) — a computação manual explícita (não dá pra fazer aritmética de 100 ns→UUID de cabeça), **não** é tooling de scanner. Burp continua sendo quem dispara as requests.
- **Cross-atom reference policy:** OK e **desejável** referenciar `idor-numeric-id` (03, irmão direto) e `path-traversal-basic` (10, mesma família A01) **explicitamente**; OK citar os demais em `main` (01/02/04/05/06/07/08/09). **PROIBIDO** referenciar ou fazer foreshadow de qualquer átomo da Fase 3+ ainda não publicado (`bola-rest`, `jwt-weak-secret`, `session-fixation`, etc.) — mesmo os "parentes" A01/API. Ao falar de IDs de API/objeto, manter no frame de IDOR/A01; **não** foreshadowar BOLA-como-átomo.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF), padrão v0.1.0. H1 idêntico: `# idor-uuid-guessable — Insecure Direct Object Reference (guessable UUID)`. Termos técnicos (IDOR, ownership check, timestamp, node, clock_seq, payload) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2), linkando `https://portswigger.net/web-security/access-control/idor` com o texto **`Insecure direct object references (IDOR)`** preservado em inglês também no PT. **Buscar/confirmar a URL por fetch na Fase 2** (não inventar); é a mesma que o 03 já usa. Na mesma passada de fetch, **se** o DIFF/WALKTHROUGH for citar a subseção exata da RFC 4122 sobre clock sequence, confirmá-la por fetch antes de cravar; caso contrário, manter a formulação geral (inicializar o clock sequence com valor aleatório e persisti-lo), **sem** §X.Y.Z.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 11: `idor-uuid-guessable` — IDOR via guessable UUID (A01 Broken Access Control). `` (padrão das linhas dos átomos 06–10).
- **ROADMAP.md:** marcar o átomo 11 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): baseline (`POST /receipt` como `mallory` → UUIDv1 + `issued_at`; ler o próprio → 200); Step 1 (`GET /` → `issued_at` da `alice` em µs); Steps 2–3 (extrair node+clock_seq, reconstruir → 10 candidatos); Step 4 (1 candidato → 200 com recibo da `alice`); Step 5 (path próprio + `X-User-ID: alice` → inalterado); fixed (8111): não-dono → 403, v4 sem reconstrução. Confirmar itens 1–9 do checklist.
- **Portas:** `127.0.0.1:8011` (vulnerable), `127.0.0.1:8111` (fixed). Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre o nome exato de uma aba/opção do Burp (Repeater vs Intruder pros 10 candidatos), **perguntar antes de inventar** (CLAUDE.md). Repeater (10 sends) é suficiente; Intruder é a opção "automatizar os 10".
