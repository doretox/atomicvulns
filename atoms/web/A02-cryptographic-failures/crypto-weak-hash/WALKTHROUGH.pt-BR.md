# Walkthrough — crypto-weak-hash

A app é uma API de login: você manda usuário e senha, ela rehasheia a senha e compara com o hash que guardou no cadastro. A lógica de login está certa. O problema é o primitivo que ela escolheu pra guardar: MD5, sem salt. Um hash é mão-única — você não descriptografa um MD5 —, mas MD5 é um hash rápido e de propósito geral, e sem salt a mesma senha sempre dá o mesmo digest. Então, de posse de um hash tirado de um dump de banco vazado, você recupera a senha original com uma tabela pré-computada de hash→senha (uma rainbow table). Com a senha, você loga como a vítima.

A trilha é **um terminal** — construir a rainbow table e quebrar o hash com o RainbowCrack — mais o **Burp Suite (Repeater)** pra provar que a senha recuperada loga. Quebrar um hash é algo que o Burp não faz, então, do mesmo jeito que um browser executa JavaScript para um bug client-side, a ferramenta que faz essa parte do trabalho entra na trilha principal. Não há browser.

## 1. Contexto

Uma pequena API de login em `127.0.0.1:8031` (vulnerable) e `127.0.0.1:8131` (fixed):

- `GET /` — um banner JSON. Não é o alvo.
- `POST /login` — JSON `{"username", "password"}`. Busca o usuário, rehasheia a senha enviada, compara com o hash armazenado, e devolve `200 {"authenticated": true}` ou `401 {"authenticated": false}`.

Este átomo é **A02 — Cryptographic Failures**: o primitivo escolhido pra proteger o segredo armazenado é o errado.

Termos, definidos uma vez:

- **Hash / função mão-única (one-way).** MD5 mapeia uma senha num digest fixo de 128 bits. Não há inversa — você não "descriptografa" um hash. Então você não inverte; você ataca por *tentativa*: chuta uma senha candidata, hasheia, compara com o alvo. Se bater, achou a senha.
- **Salt.** Um valor aleatório único misturado à senha antes de hashear, de modo que a *mesma* senha produz hashes *diferentes*. Sem salt, `md5("adm1n")` é sempre o mesmo digest — que é exatamente o que torna uma tabela pré-computada reutilizável.
- **Rainbow table.** Uma tabela pré-computada que mapeia hashes de volta a senhas por um keyspace inteiro. É um **time-memory tradeoff**: guardar todo par hash→senha custaria memória demais, e recomputar cada chute a cada crack custaria tempo demais, então uma rainbow table pré-computa *correntes* (chains) de hashes e guarda só as pontas — você paga a pré-computação pesada uma vez, depois busca rápido.
- **Ataque de dicionário.** A outra forma de chutar em massa: hashear uma lista de senhas prováveis. (É assim que o irmão [`jwt-weak-secret`](../jwt-weak-secret/) quebra o secret dele.)
- **Password KDF (key derivation function).** Um hash *feito de propósito* pra senha — deliberadamente **lento**, com um **cost / work factor** ajustável, e salt embutido. `bcrypt` é um; é o fix aqui.

O ponto de partida é uma **premissa**: suponha que você já tem a tabela `users` de um dump de banco — não importa como vazou. A app nunca devolve o hash por HTTP; tirá-lo da app seria uma vulnerabilidade *diferente*. A linha dumpada do `admin` é:

```
admin:d9da8170e8bc9f27b2d32a6c9a6c697d
```

Esse valor de 32 hex é um MD5 sem salt. Dali em diante, tudo é offline.

## 2. Achar o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). Armazenamento e verificação:

```python
def store_hash(password):
    return hashlib.md5(password.encode()).hexdigest()

def verify(password, stored):
    return hashlib.md5(password.encode()).hexdigest() == stored
```

A lógica de login está *correta* — ela rehasheia a senha enviada e compara, e a query de busca é parametrizada (sem SQL injection). O bug não é um check faltando nem uma comparação quebrada. O bug é o **primitivo**: `md5(...)`, sem salt. A pergunta de auditoria não é "ela verifica?" — verifica. É "MD5, sem salt, é a coisa certa pra guardar uma senha?" — e não é: rápido mais sem salt significa que um hash vazado é recuperável de uma tabela pré-computada.

## 3. Exploração — recuperar a senha com uma rainbow table

Isto roda no seu terminal, com o [RainbowCrack](https://en.wikipedia.org/wiki/RainbowCrack): o `rtgen` constrói tabelas, o `rtsort` ordena, o `rcrack` procura um hash. O espaço de senhas que estamos atacando é pequeno: `adm1n` tem cinco caracteres, todos letras minúsculas e dígitos — o charset `loweralpha-numeric`. São 36⁵ = 60.466.176 candidatos, pequeno o suficiente pra uma rainbow table cobrir o *keyspace inteiro*. Sem precisar de wordlist — isso pega senhas que não são palavra de dicionário limpa.

### Passo 1 — Construir a rainbow table (veja a pré-computação)

O `rtgen` pré-computa a tabela pra MD5 sobre esse keyspace. Esta é a parte cara — e todo o ponto do tradeoff: você paga adiantado, uma vez, pra transformar todo crack futuro numa busca rápida.

```
rtgen md5 loweralpha-numeric 5 5 0 3800 40000 0
```

Isto é: hash `md5`, charset `loweralpha-numeric`, comprimento `5` a `5`, table index `0`, chains de `3800` de comprimento, `40000` delas.

```
rainbow table md5_loweralpha-numeric#5-5_0_3800x40000_0.rt parameters
hash algorithm:         md5
charset name:           loweralpha-numeric
charset data:           abcdefghijklmnopqrstuvwxyz0123456789
charset length:         36
plaintext length range: 5 - 5
reduce offset:          0x00000000
plaintext total:        60466176

sequential starting point begin from 0 (0x0000000000000000)
generating...
40000 of 40000 rainbow chains generated (0 m 5.4 s)
```

Uma tabela sozinha cobre só ~86% do keyspace — as chains colidem e se fundem (merge), e nenhuma tabela sozinha passa desse teto. Pra fechar a lacuna, você gera algumas tabelas que usam cada uma uma *reduction function diferente*, selecionada pelo **table index** (o `0` acima). Repita com index 1 a 4:

```
rtgen md5 loweralpha-numeric 5 5 1 3800 40000 0
rtgen md5 loweralpha-numeric 5 5 2 3800 40000 0
rtgen md5 loweralpha-numeric 5 5 3 3800 40000 0
rtgen md5 loweralpha-numeric 5 5 4 3800 40000 0
```

Cada uma imprime um `reduce offset` escalonado — `0x00010000`, `0x00020000`, … — o botão que torna as chains dela independentes das outras, de modo que as cinco juntas cobrem bem mais de 99,9%:

```
reduce offset:          0x00010000
40000 of 40000 rainbow chains generated (0 m 5.8 s)
```

Cinco tabelas pequenas, pré-computadas.

### Passo 2 — Ordenar as tabelas

O `rcrack` precisa das tabelas ordenadas pra busca rápida:

```
rtsort .
```

### Passo 3 — Quebrar o hash

Agora o retorno do tradeoff — procure o hash dumpado:

```
rcrack . -h d9da8170e8bc9f27b2d32a6c9a6c697d
```

```
5 rainbow tables found
...
plaintext of d9da8170e8bc9f27b2d32a6c9a6c697d is adm1n

statistics
----------------------------------------------------------------
plaintext found:                             1 of 1
total time:                                  0.38 s
...
result
----------------------------------------------------------------
d9da8170e8bc9f27b2d32a6c9a6c697d  adm1n  hex:61646d316e
```

A pré-computação levou segundos; a busca levou **0,38 s**. A senha do admin é `adm1n`. Você não descriptografou o hash — MD5 não tem inversa — você recuperou a senha original pré-computando o keyspace e procurando nele.

### Passo 4 — Logar como a vítima (Burp)

Aponte o Burp pra `127.0.0.1:8031` e mande a credencial recuperada pelo Repeater:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8031
Content-Type: application/json

{"username": "admin", "password": "adm1n"}
```

Resposta — `200`:

```json
{"authenticated":true}
```

Conta tomada. O hash vazado virou a senha viva, e a senha te logou.

> Isto é um lab local: as duas apps bindam em `127.0.0.1`, os dados são dummy (`adm1n` é uma senha obviamente falsa, os usuários são fake), e o crack rodou inteiramente offline na sua própria máquina. Nada aqui sai da máquina, e nada é destrutivo.

## 4. O que a vuln NÃO é

Quatro conclusões erradas pra matar.

**Não é que `adm1n` era uma senha fraca.** Uma senha curta *ajuda* (o keyspace é pequeno), mas a falha que este átomo isola é o *armazenamento*. A prova é categórica: o lado fixed guarda a **mesma** senha `adm1n` — e a rainbow table não recupera nada lá (próxima seção). Mesma senha, resultado diferente: a diferença é 100% o primitivo.

**Não é que você "descriptografou" o hash.** MD5 é mão-única; não tem inversa. Você recuperou a senha pré-computando pares candidato→hash e procurando o alvo — um keyspace search, não decriptação.

**Não é que "MD5 tem colisões".** A fraqueza de colisão do MD5 é irrelevante aqui — você não achou uma colisão, você achou a senha *original*. SHA-256, que não tem colisão conhecida, guardado sem salt cairia exatamente igual, porque é igualmente *rápido*. A causa é um primitivo rápido e sem salt — não a brokenness específica do MD5.

**Não é information disclosure nem injection.** Nenhum bug da app vazou o hash (nada o devolve), e nenhum input virou código (a query é parametrizada). O dump é o ponto de partida assumido; a única falha é o primitivo de armazenamento.

## 5. Impacto

Recuperação de credencial levando a account takeover. De um hash vazado você recupera a senha *real* da vítima e loga como ela — aqui, o administrador. E porque as pessoas reusam senha, uma senha recuperada do dump de um sistema muitas vezes abre contas em *outros* sistemas. **Não é RCE** — não há execução de código — e o teto é o que a credencial recuperada destrancar. Mas pra uma credencial armazenada, "recuperada" é o jogo inteiro: o segredo que o hash deveria proteger está agora nas mãos do atacante.

## 6. Por que o fix funciona

Rode o mesmo ataque contra a API corrigida na porta **8131** (veja [`DIFF.md`](./DIFF.md)). A tabela `users` dela, dumpada, guarda o admin como bcrypt:

```
admin:$2b$12$P5nBP/bbDFwHcd1aR6UEneKKcUXJNOvBN4wZ24d0G3FkYG9BT4yWu
```

A rainbow table não é *mais lenta* aqui — ela é **inaplicável**, e você vê isso por inspeção, sem rodar um crack:

- O valor armazenado é um hash bcrypt **salgado** (`$2b$...`, 60 caracteres), não um MD5 de 32 hex. O `rcrack` contra uma tabela MD5 nem aceitaria isso.
- Mais fundamental, o **RainbowCrack não consegue mirar bcrypt de jeito nenhum**. O `rtgen` dele só constrói tabelas pra hashes sem salt — rode-o sem argumentos e o menu é:

```
hash algorithms implemented:
    lm HashLen=8 PlaintextLen=0-7
    ntlm HashLen=16 PlaintextLen=0-15
    md5 HashLen=16 PlaintextLen=0-15
    sha1 HashLen=20 PlaintextLen=0-20
    sha256 HashLen=32 PlaintextLen=0-20
```

  Sem bcrypt. E isso não é uma omissão: pré-computação é *sem sentido* sob um salt-por-hash. O salt torna cada hash único, então não há uma única tabela hash→senha pra construir — você precisaria de uma tabela separada pra cada salt possível. Não há o que gerar, então não há onde procurar o hash.

Dois ressalvas honestas, pra você não ler demais nisso. O salt derrota a *pré-computação* — rainbow tables — categoricamente. O bcrypt *também* ajuda contra a outra técnica: a lentidão deliberada dele (um cost factor ajustável, `$12$` no hash acima) torna um ataque de dicionário ou brute-force ao vivo muito mais caro por chute. Salt e lentidão juntos, de um só primitivo — esse é o ponto.

A prova de isolamento: logue com a senha correta nas **duas** portas e você recebe um `200` idêntico — o login funciona igual em cada lado. Só o crack offline difere, e essa diferença traça puramente ao primitivo de armazenamento.

O fix é uma coisa só: trocar o primitivo. Não "um hash mais forte" (SHA-256 é igualmente rápido), não "só um salt" (um salt sozinho num hash rápido ainda perde pra um dicionário), não "mais validação". Um password KDF lento e salgado. Veja o [`DIFF.md`](./DIFF.md) para o diff e por que esses dois fixes-armadilha não se sustentam.
