# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em **exatamente uma linha** — a constante `SECRET`. Todo o resto é byte-idêntico: os imports, os helpers `decode`/`authenticate`, as três rotas, a verificação `algorithms=["HS256"]`, o `Dockerfile` e o `requirements.txt`. Não há templates (este átomo é API-only). A `wordlist-sample.txt` na raiz do átomo é um asset de ataque, não parte de nenhuma das apps.

## O fix — um valor mais forte

```diff
 # HS256 signing secret. The verification logic below is correct and byte-identical in
 # both vulnerable/ and fixed/ — the whole security of this atom rests on the strength
 # of this one value. See DIFF.md.
-SECRET = "changeme123"  # VULNERABLE: weak, guessable, sits in any password wordlist
+SECRET = "jlui6jbnFeh9_BXEPw4wUaF1UwEfZ2R9uaSkVqDoWuk"  # FIXED: strong, high-entropy (secrets.token_urlsafe(32)); not in any wordlist
```

O fraco `changeme123` vira um valor de 43 caracteres vindo de `secrets.token_urlsafe(32)` — 32 bytes de saída de CSPRNG, codificados em base64url. É um literal fixo, não `SECRET = secrets.token_urlsafe(32)`: gerar ele a cada boot do processo rotacionaria a chave a cada restart e invalidaria tokens vivos. Um valor forte, fixado.

Essa é a mudança inteira. Rode o mesmo `john --wordlist=wordlist-sample.txt jwt.txt` contra um token da app fixed e ele retorna `0 password hashes cracked, 1 left` — o secret forte não está em wordlist nenhuma, e 32 bytes aleatórios não são brute-forçáveis de jeito nenhum. O token admin forjado com `changeme123` leva `401` na app fixed, porque o HMAC não bate mais.

## O fix muda um valor, não código — um diff que este repo não tinha visto

Todo fix de átomo até aqui teve uma de duas formas. Nos átomos A01 (`idor-numeric-id`, `bola-rest`, …) e no `jwt-none-alg`, o `app.py` difere numa **rota ou helper** — um check adicionado, um branch removido; o bug e o fix moram no *código*. No par de reflected-XSS, o `app.py` é **idêntico** e a diferença vive num template (um filtro `|safe`). Este átomo é um terceiro tipo: o `app.py` difere, mas **só numa constante** — nenhuma linha de lógica muda.

Essa é a lição, dentro do próprio diff. O `decode` está correto e intocado. Nenhum endpoint se move. A remediação não foi *fazer* algo diferente — foi *escolher um valor melhor*. **A segurança morava inteiramente no secret, não no código em volta.** Um diff de uma linha, e a linha é dado.

## Contraste com o `jwt-none-alg` — e por que a lição dele não bastava

O fix do `jwt-none-alg` *removeu* código: quatro linhas, o branch `alg:none` que pulava a verificação. Este fix não remove nem adiciona lógica nenhuma — troca um literal.

Olhe o `decode` deste átomo:

```python
def decode(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

Isso é **byte a byte o `decode` _fixed_ do `jwt-none-alg`.** Este átomo começa onde aquele terminou — a lição do algoritmo já aprendida: uma allowlist positiva `algorithms=`, sem branch no header. E ainda assim cai, porque a *chave* é adivinhável. O `jwt-none-alg` ensinou *"looks-like-crypto is not is-crypto"* — um `jwt.decode` cercado de `SECRET` e `algorithms=` só *parece* um boundary se algum caminho pula a verificação. Este átomo afia pra o caso em que nada é pulado: verificação correta ainda não é um boundary se o secret é fraco. **05 = a fechadura era contornável (o algoritmo); 13 = a fechadura roda, mas a chave que a defende é fraca.** Ambos são "parece um boundary, não é" — um mirando no algoritmo, o outro na chave.

O walkthrough do `jwt-none-alg` até nomeou isto de antemão: *"weak shared secrets that survive a brute-force"* foram listados como outra forma de perder o mesmo jogo. Este átomo é esse flavor, tornado real. A conclusão: acertar o algoritmo (o fix do 05) é **necessário mas não suficiente** — um JWT é tão confiável quanto o secret por trás da signature. "Assinado" não é "seguro".

O runtime também diz isso. O PyJWT 2.12 emite `InsecureKeyLengthWarning` pro `changeme123` de 11 bytes a cada sign e verify; com o secret fixed de 43 bytes o warning some. A lib sinaliza uma chave curta — ela só não recusa.

## O secret forte está visível no `fixed/app.py` — por que isso não quebra a lição

O secret forte está hardcoded no repo, à vista. Isso não enfraquece a demonstração, por um motivo: **o modelo de ataque é "o atacante tem um token e uma wordlist", não "o atacante lê seu código-fonte".** Num deploy real o fonte não é público; o atacante parte de um JWT capturado e tenta recuperar a chave a partir dele. A lição é que recuperar uma chave de *alta entropia* a partir do token é inviável — e isso continua verdade quer o valor esteja impresso aqui ou não. O lab hardcoda os dois secrets, fraco e forte, pra o átomo ter valores estáveis e inspecionáveis pra reproduzir.

Um fix de produção também faria uma coisa que este átomo deliberadamente não faz: tirar o secret do fonte por completo, pra uma environment variable ou um secrets manager. Isso é outra preocupação (secret management), e misturar ela borraria o único eixo que este átomo isola — *entropia*. Então as duas versões hardcodam, e só o valor muda. Mencionável, não aplicado.

## `403`, não `404`

O `GET /admin/users` retorna **`403`** pra um token válido não-admin — o status honesto: "autenticado, mas não permitido". Não há oráculo de enumeração pra esconder aqui: o endpoint é um recurso fixo, não um objeto indexado por um id sequencial. (Esse foi o motivo do `bola-rest` escolher `404` — ids sequenciais, onde um `403` confirmaria que um objeto existe. Nenhum id desses existe neste átomo, então `403` está certo; não copie o `404` por reflexo.)

## Isto é A02 — a falha é um valor, e não dá `grep`

O bug não é input parseado nem um check ausente — é uma chave de baixa entropia protegendo uma signature HMAC, recuperada por brute force. Isso é uma **Cryptographic Failure (A02)**, a mesma categoria do `jwt-none-alg`. E como o irmão, não dá `grep`: não há chamada perigosa pra procurar — `jwt.decode(..., algorithms=["HS256"])` é exatamente como uma implementação *correta* se parece. Você o pega lendo a única coisa que o grep pula: o valor da chave. Pergunte de todo secret de assinatura: "isto poderia estar numa wordlist?" — e aqui a resposta é sim.
