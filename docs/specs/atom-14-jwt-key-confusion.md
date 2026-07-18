# Spec — Átomo 14: `jwt-key-confusion`

> Documento de especificação para o Claude Code implementar o décimo-quarto átomo do projeto `atomicvulns` (Fase 3 — "Access Control & Autenticação", milestone `v0.3.0`). Este é o **terceiro e último ataque a JWT do repo** e **fecha a trilogia JWT** iniciada no `jwt-none-alg` (05) e continuada no `jwt-weak-secret` (13). A trilogia é uma escada de três degraus, e este átomo é o **clímax**:
> - **05 (`jwt-none-alg`) — o servidor NÃO verifica.** `alg:none`, a assinatura é pulada. *"A fechadura não trancava."*
> - **13 (`jwt-weak-secret`) — o servidor verifica CERTO, mas a chave é FRACA.** HS256 imposto corretamente, secret de dicionário, quebrado por brute force. *"A fechadura tranca; a chave estava num post-it."*
> - **14 (`jwt-key-confusion`, ESTE) — o servidor verifica, a chave é FORTE (RSA robusto), a assinatura MATEMATICAMENTE BATE — e mesmo assim cai.** Porque o servidor deixa o **token** escolher qual algoritmo usar. *Nada* está fraco: o RSA está intacto, o HMAC está intacto, a chave tem 2048 bits. O bug é **puramente confiar no campo `alg` do token**.
>
> O eixo é **A02 — Cryptographic Failures** (mesma pasta dos irmãos). Leia junto com `CLAUDE.md` (Seções 3.3, 3.6, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — os **dois irmãos JWT** já publicados em `main`:
> 1. **`atoms/A02-cryptographic-failures/jwt-none-alg/` (05) — o irmão no SHAPE DO FIX, e o parentesco é a lição.** O 05 e o 14 são **o mesmo bug de fundo**: o servidor confiando no `alg` que o token declara. No 05 o token diz *"não verifique"* (`none`); no 14 o token diz *"verifique com ESTA família"* (`HS256` em vez de `RS256`). E os **dois fixes são o mesmo movimento**: parar de ramificar pelo `alg` do token e travar a lista de algoritmos (05 remove o branch `alg:none`; 14 remove o branch alg-controlado e trava em `algorithms=["RS256"]`). O `verify` VULNERÁVEL do 14 **abre igual ao do 05** — `jwt.get_unverified_header(token)` e um `if` no `alg`. Reusar TODO o vocabulário de JWT (header/payload/signature, `sub`/`role`, `Bearer`, `jwt.encode`/`jwt.decode`, allowlist de algoritmos), a forma de README/WALKTHROUGH/DIFF, e a frase-regra do 05: *"the header is data, not policy."*
> 2. **`atoms/A02-cryptographic-failures/jwt-weak-secret/` (13) — o irmão no MOLDE API-only e no IMPACTO.** Reusar o molde API-only exato do 13: `POST /login` sem senha (`{"user"}`, default `alice`, `role` sempre `user`), respostas JSON via `jsonify`, `GET /api/profile` (baseline + captura do token), `GET /admin/users` (exige `role: admin`), dado admin fake benigno (`USERS`), **sem templates, sem browser**, WALKTHROUGH em trilha Burp + terminal. O **impacto é o mesmo do 13** — escalação **VERTICAL** (`role: user` → `role: admin` forjado), controle da autenticação. O que muda é o **mecanismo**: no 13 algo estava FRACO (o secret); no 14 **nada** está fraco.
>
> Esta spec captura apenas as decisões *específicas* deste átomo. Onde 05 e 13 já resolveram a forma (vocabulário JWT, claims `sub`/`role`, estrutura API-only, `POST /login` sem senha, forma de DIFF/WALKTHROUGH/README, o par "trilha Burp + terminal"), a instrução é **reusar a forma**, não reinventar. **Diferença estrutural central deste átomo:** o servidor vulnerável **verifica a assinatura NA MÃO** — lê o `alg` do header ele mesmo e ramifica para HMAC ou RSA — porque o PyJWT moderno **bloqueia** a confusão ingênua. Isso é a **SAÍDA B** (ver a seção homônima), e é o que torna o átomo didaticamente honesto **sem** CVE de brinde: o anti-padrão que causa key confusion no mundo real É a verificação hand-rolled.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, nem chaves — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Nota de planning 1 — posição na Fase 3: 14 fecha a TRILOGIA, NÃO a FASE (discrepância a reconciliar)

> **Levantado ao confirmar contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** O briefing desta sessão descreveu o 14 como *"o que FECHA a Fase 3 (5º e último átomo da fase)"*. **O `ROADMAP.md` diz outra coisa:** a Fase 3 tem **cinco** átomos — `11 idor-uuid-guessable`, `12 bola-rest`, `13 jwt-weak-secret`, **`14 jwt-key-confusion`**, `15 session-fixation` — e o **15 (`session-fixation`, A07)** é o quinto, listado DEPOIS do 14, e é ele quem **fecha a Fase 3**. Logo o **14 é o QUARTO átomo da Fase 3**, não o quinto.
>
> O que É verdade e é o coração deste átomo: o 14 **fecha a trilogia JWT** (05 → 13 → 14 são os três — e únicos — ataques a JWT do projeto; o 15 é auth de sessão, não JWT). A confusão provável do briefing foi **conflar "fecha a trilogia JWT" (verdadeiro) com "fecha a Fase 3" (é o 15 quem fecha)**.
>
> **Decisão desta spec:** seguir o `ROADMAP.md`. A framing de fase abaixo (Identidade) diz "quarto átomo da Fase 3; o `session-fixation` (15) é o phase-closer" — **isso vive SÓ aqui, no briefing interno**; jamais no conteúdo publicado do átomo (o 15 é **não-publicado** → proibido referenciá-lo em README/WALKTHROUGH/DIFF, `CLAUDE.md` §5). A framing de **trilogia JWT** (14 = clímax/fechamento dos três ataques a JWT) é a que vai pro conteúdo, e é honrada por inteiro. **Ação do mantenedor:** confirmar. Se a intenção real for reordenar a Fase 3 (mover/remover o 15), ajustar o `ROADMAP.md` numa tarefa própria — **não** nesta spec.

## Nota de planning 2 — débito do 05 (`alg:none` §5) JÁ resolvido; nada a fazer

> A spec do 13 registrou um débito preexistente: o WALKTHROUGH do 05 (§5) foreshadowava "atoms 13 and 14" **por número**, ferindo a política de não citar átomos não-publicados (`CLAUDE.md` §5), a ser tratado *"provavelmente ao gerar o 14"*. **Verificado agora contra `main`:** o commit **#23** (`docs(jwt-none-alg): generalize the bug-shape note, drop unpublished-atom foreshadow`) **já retirou** o foreshadow. O §5 do 05 hoje diz, genericamente, *"algorithm-confusion attacks where the server is tricked into using the wrong key"* — **sem** números de átomo. O DIFF do 05 idem. **Portanto o débito está quitado; a Fase 2 NÃO precisa (e não deve) tocar no 05 pra "consertar" isso.** Registrado aqui só pra o Claude Code da Fase 2 não sair caçando um débito que não existe mais. *(A memória de projeto `atom-05-foreshadow-debt` ficou desatualizada por causa do #23 — proposta de atualização/remoção no fim desta spec; memória é decisão do mantenedor.)*

---

## Identidade

- **ID:** `jwt-key-confusion`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A02 — Cryptographic Failures** (mesma pasta dos irmãos JWT: `atoms/A02-cryptographic-failures/`). Confirmado contra o repo: 05 e 13 estão em `A02-cryptographic-failures/` e o `ROADMAP.md` lista o 14 como "A02 Cryptographic Failures". *(Nuance honesta na seção "Por que A02": a raiz do bug é um **erro de LÓGICA de verificação**, não cripto quebrada — mas A02 é a moldura de categoria coerente com os irmãos e com a superfície JWT/assinatura. O 05 já enquadrou seu bug A02 assim: "None of the cryptography is broken".)*
- **Também é (contexto):** o **terceiro e último ataque a JWT do projeto** — 05, 13 e 14 são os **três** ataques a JWT do repo. A trilogia **fecha aqui**. Não há um quarto átomo JWT: **não prometer nem foreshadowar** um (ver "Contraste com irmãos" e "Política de referência cross-átomo").
- **Pasta:** `atoms/A02-cryptographic-failures/jwt-key-confusion/`
- **Número sequencial:** 14
- **Porta vulnerable:** `127.0.0.1:8014`
- **Porta fixed:** `127.0.0.1:8114`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Container roda com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos 01–13.
- **Fase / milestone:** Fase 3, `v0.3.0`. **Quarto átomo da Fase 3** (ver Nota de planning 1 — o `session-fixation` (15) é o phase-closer, não o 14). Versionamento/release fica pra depois, **fora desta spec**.
- **Branch de trabalho:** `atom/jwt-key-confusion`. Convenção `atom/<id>` (`CLAUDE.md` §6). Branch já criada nesta fase de planning.
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** a **mesma** página de JWT attacks do PortSwigger que 05 e 13 usam, preferindo a **seção de algorithm confusion** se houver âncora específica. Ver seção "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7):** `# jwt-key-confusion — JWT algorithm confusion (RS256 → HS256)` — segue o padrão dos irmãos (`jwt-none-alg — JWT alg=none signature bypass`; `jwt-weak-secret — JWT weak signing secret (brute-forced)`): `id` + descrição em inglês da vuln, com o qualificador `(RS256 → HS256)` fixando o vetor. Texto exato do H1 confirmável na Fase 2, mas manter a forma "`id` — descrição em inglês".

---

## Classe de vulnerabilidade

**JWT algorithm confusion (key confusion), variante RS256 → HS256.** A app assina seus JWTs com **RS256** (RSA, assimétrico): a chave **privada** assina, a chave **pública** verifica, e a pública é **publicada** (`GET /jwks`) pra clientes verificarem tokens — o que é **correto e por design**. A falha é que o servidor **verifica os tokens confiando no campo `alg` que o próprio token declara**: se o token diz `alg: RS256`, verifica com RSA; se diz `alg: HS256`, verifica com **HMAC-SHA256 usando a MESMA chave pública como secret**. Um atacante pega a chave pública (é pública!), monta um token `alg: HS256` com `role: admin`, e assina um HMAC-SHA256 usando **os bytes exatos da chave pública** como secret. O servidor lê `alg: HS256`, faz HMAC com a chave pública que ele tem, e a assinatura **bate** — porque é a mesma chave que o atacante usou. Token forjado aceito, escalação vertical.

### A lição-coração

> **"Quando o servidor deixa o token escolher qual algoritmo usar, a assimetria colapsa: a chave pública — segura justamente por ser pública sob RS256 — vira o secret de forja sob HS256."**

**O mecanismo (cravar no WALKTHROUGH e no DIFF).** RS256 é **assimétrico**: a chave privada assina, a chave pública verifica, e **saber verificar NÃO ensina a assinar**. É *exatamente* isso que torna seguro publicar a chave pública — quem a tem só consegue *conferir* tokens, não *criar*. HMAC (HS256) é **simétrico**: a **MESMA** chave assina e verifica (assinar = verificar). Quando o servidor é enganado a tratar a chave **pública** RSA como um **secret HMAC**, a assimetria colapsa: a chave que era só pra verificar vira também a chave de **assinar** — porque em HMAC não há diferença entre as duas. E o atacante **tem** a chave pública. Logo tem tudo pra forjar. A vuln é o servidor **confiar no `alg` do token pra escolher a FAMÍLIA de algoritmo**.

**Sub-lição (cravar):** **"a mesma chave, dois algoritmos, dois significados de segurança".** A chave pública é **inofensiva** sob RS256 (só verifica) e **catastrófica** sob HS256 (assina). O **VALOR** dos bytes é idêntico nos dois casos; o **ALGORITMO** muda tudo. *(Paralelo com o 13: lá "assinado ≠ seguro" — a assinatura é tão forte quanto o secret. Aqui "verificado ≠ seguro se o token escolhe COMO verificar" — a verificação roda, e ainda assim cai porque o token dita o método.)*

### Enquadramento central — key confusion NÃO é falha de CRIPTOGRAFIA, é ERRO DE LÓGICA (a observação do mantenedor — cravar)

O RSA está **intacto**. O HMAC está **intacto**. A chave tem 2048 bits, forte. Nada foi "quebrado" matematicamente. **Key confusion é um ERRO DE LÓGICA de quem escreveu a verificação** — o programador confiou no token pra escolher o algoritmo. O átomo **materializa esse erro no código** (a ramificação `if alg == "HS256": ... elif alg == "RS256": ...` com a MESMA chave nos dois ramos) pra o aluno **ver a linha causal**. Erros de programação — alguém checando a chave/assinatura de forma incorreta — são a raiz de muita vuln, e este átomo é um exemplar cristalino: código presente e **logicamente errado**, cercado de cripto perfeitamente sólida. *(Isto afia a tese do 05 — "looks-like-crypto is not is-crypto": um `jwt.decode` cercado de chave e `algorithms=` **parece** um boundary; se a POLÍTICA de verificação é decidida pelo token, não é. O 05 aplicou isso ao "pular a verificação"; o 14 aplica ao "trocar de família de algoritmo".)*

### A trilogia em três camadas (o arco fechando — cravar na abertura, no contraste e no fechamento)

| | 05 `jwt-none-alg` | 13 `jwt-weak-secret` | 14 `jwt-key-confusion` (ESTE) |
|---|---|---|---|
| **Metáfora** | A fechadura **não trancava** | A fechadura **tranca; a chave num post-it** | A fechadura tranca, a chave é **forte**, a assinatura **bate** — e mesmo assim abre |
| **O servidor** | **não** verifica (`alg:none`) | verifica **certo**, mas a chave é **fraca** | verifica, chave **forte** — mas o **token escolhe o algoritmo** |
| **O que está fraco** | a verificação (pulada) | o **valor** do secret (dicionário) | **NADA** — RSA forte, HMAC sólido, assinatura válida |
| **O bug** | branch `alg:none` (confia no `alg`) | um **VALOR** (o `SECRET` fraco) | branch alg-controlado (confia no `alg`) |
| **O ataque na assinatura** | **arranca** (`alg:none`, 3º segmento vazio) | **refaz** com o secret quebrado | **refaz** com a chave pública como secret HMAC |
| **O fix** | remover o branch `alg:none` | trocar o valor do secret (fraco→forte) | remover o branch alg-controlado, travar `algorithms=["RS256"]` |

**A linha que fecha o arco:** *"as três formas de um JWT falhar mesmo com um `jwt.decode` no código"* — (05) não verificar, (13) verificar com chave fraca, (14) verificar com chave forte deixando o token escolher COMO. O 14 é o **mais sofisticado e mais insidioso**: nos dois primeiros havia algo visivelmente errado (verificação pulada; secret de dicionário); no 14 **tudo parece impecável** — e cai.

### Distinção do 05 (MESMO shape de fix — o parentesco é a lição — CRAVAR)

O 14 é irmão do 05 no **shape do fix**, e o WALKTHROUGH/DIFF devem cravar isso:

- **O mesmo bug de fundo:** o servidor **confia no `alg` que o token declara**. 05: o token diz `none` → pula a verificação. 14: o token diz `HS256` → troca a família de algoritmo. Em ambos, o `verify` VULNERÁVEL **abre igual** — `jwt.get_unverified_header(token)` e um `if` no `header["alg"]`.
- **O mesmo movimento de fix:** parar de perguntar ao token e **travar a allowlist**. 05 remove o branch `alg:none` e deixa `jwt.decode(token, SECRET, algorithms=["HS256"])`. 14 remove o branch alg-controlado e deixa `jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])`. **Os dois tiram a decisão do token.** A regra do 05 vale idêntica: *"never branch off `header['alg']` to choose how to validate; the header is data, not policy."*
- **A diferença de mecanismo:** 05 = **não verificar** (`none`); 14 = **verificar com a família errada** (confusion). O 05 já **nomeou** este flavor genericamente na sua §5/DIFF (*"algorithm-confusion attacks where the server is tricked into using the wrong key"*) — o 14 é **esse flavor concretizado**. Callback permitido (05 é publicado); **não** transformar em foreshadow (o 05 já não foreshadowa nada — ver Nota de planning 2).

### Distinção do 13 (nada está fraco — o clímax)

- No **13**, algo estava **FRACO**: o secret, uma palavra de dicionário. O ataque foi **adivinhar a chave** (brute force com john).
- No **14**, **NADA está fraco**: a chave RSA é robusta (2048 bits), a assinatura HMAC que o atacante produz **bate matematicamente**, o HMAC-SHA256 é sólido. Não há brute force, não há chave adivinhada. O atacante **já tem** a chave (é pública) e a usa **legitimamente** num algoritmo que o servidor **não devia** ter aceitado.
- Por isso o 14 é o **clímax**: o que o distingue **não é impacto maior** (é o mesmo do 13 — vertical), é o **mecanismo mais sofisticado**. *(Ver "Impacto".)*

### O que este átomo acrescenta ao arco — escalação VERTICAL (coerência com o 13)

Como o 13, o 14 ensina escalação **VERTICAL**: `role: user` legítimo → `role: admin` forjado. Mesmo **impacto** do 13 (poder administrativo, não só outra identidade), **mecanismo diferente**. Mantém o arco JWT consistente no impacto (vertical) enquanto varia o mecanismo (05 não-verifica → 13 chave-fraca → 14 confusion). Distingue do eixo **HORIZONTAL** dos A01 desta fase (11/12: ler dado de outro user do mesmo nível).

### Por que A02 (Cryptographic Failures)

Coerência de pasta/categoria com os irmãos JWT (05 e 13, ambos A02; confirmado no repo e no `ROADMAP.md`), e a superfície é o **mecanismo de assinatura do JWT**. Nuance honesta a cravar (não contradiz A02, afia): a **raiz** não é cripto quebrada — é um **erro de lógica de verificação** (confiar no `alg` do token). Como o 05, o bug **não `grep`a**: `jwt.decode(token, key, algorithms=["RS256"])` é exatamente o que uma implementação **correta** parece; o bug é a **verificação hand-rolled que ramifica pelo `alg`**, escrita ao lado. Pega-se lendo a **lógica de verificação** e perguntando *"quem escolhe o algoritmo — o servidor ou o token?"*.

---

## Uma vuln só — RS256 verificado, `alg:none` e alg desconhecido REJEITADOS, só a confusão HS256-com-chave-pública abre

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o servidor confiar no `alg` do token pra escolher a família (a confusão RS256→HS256). Garantias:

- **A chave RSA é forte (2048+ bits).** Nenhuma fraqueza de chave (isso é o 13). O `/login` assina RS256 **corretamente** com a privada.
- **`alg:none` → rejeitado (`401`).** O `verify` só trata `HS256` e `RS256`; qualquer outro `alg` (`none`, `ES256`, lixo) cai no ramo final → erro → `401`. Se o 14 aceitasse `alg:none`, **empilharia a vuln do 05**. **PROIBIDO.**
- **Assinatura RS256 inválida → `401`.** O ramo RS256 verifica de verdade (via PyJWT travado em RS256); um token RS256 com assinatura adulterada é rejeitado. A verificação **funciona** — o que ela não devia é *trocar de família* a mando do token.
- **HMAC com chave errada → `401`.** No ramo HS256, um HMAC assinado com bytes que **não** são a chave pública não bate → `401`. Só a chave pública (que o servidor usa como secret) forja. A **única** porta é HS256-com-a-chave-pública.
- **Sem segunda falha empilhada:** a chave **privada NUNCA** sai (só a **pública** em `/jwks`); nenhum secret/chave serializado em resposta; `/admin/users` devolve só dado fake benigno (`user`/`role`). Sem `render_template` → sem XSS acidental.

**Cravar:** o ataque **não** contorna a verificação nem quebra a cripto — ele faz o servidor **verificar com a chave errada**, satisfazendo um HMAC que o próprio servidor calcula com a chave pública. A assinatura forjada é **matematicamente idêntica** à que o servidor produziria *se* aceitasse HS256 com aquela chave — e ele aceita.

---

## A decisão estrutural — SAÍDA B (verificação manual): por quê (TRAVADA)

**O ponto que faz o átomo existir.** O **PyJWT moderno (≥ 1.5.0, e o 2.x que usamos) BLOQUEIA key confusion por padrão.** Sua `HMACAlgorithm.prepare_key` **recusa** uma chave assimétrica como secret HMAC: passar um PEM que contenha `-----BEGIN PUBLIC KEY-----` (ou `CERTIFICATE`, `RSA PUBLIC KEY`, `ssh-rsa`) a um algoritmo HMAC levanta `InvalidKeyError`. Ou seja: um servidor "vulnerável" **ingênuo** que fizesse `jwt.decode(token, public_key_pem, algorithms=["HS256", "RS256"])` **NÃO seria vulnerável** — o PyJWT abortaria no ramo HS256. *(A mesma proteção vale na forja: `jwt.encode(payload, public_key_pem, algorithm="HS256")` também levanta `InvalidKeyError`. Nem o atacante consegue forjar via PyJWT direto — ver "A forja".)*

**A saída travada é a SAÍDA B: o servidor vulnerável verifica NA MÃO.** Ele lê o `alg` do header ele mesmo e ramifica: no ramo HS256, calcula o HMAC-SHA256 com `hmac`/`hashlib` da stdlib usando os **bytes da chave pública** como secret (contornando o guard do PyJWT); no ramo RS256, delega ao PyJWT travado em RS256. Isso:

- **Usa PyJWT MODERNO (`PyJWT==2.12.1`, a mesma dos irmãos) — SEM CVE de brinde (`CLAUDE.md` §8.5).** A vuln **não** é uma versão velha de lib com bug conhecido; é **lógica de aplicação**. As libs estão atuais e patchadas.
- **É didaticamente HONESTO:** mostra **exatamente** o anti-padrão que causa key confusion no mundo real — o servidor ramificando pelo `alg` do token, com a **mesma chave** nos dois ramos. O `if alg == "HS256"` **É** o bug, visível no código.
- **Conecta com o 05:** o `verify` vulnerável **abre igual** ao do 05 (`jwt.get_unverified_header` + `if` no `alg`).

**Obrigação no DIFF e no WALKTHROUGH — explicar POR QUE o servidor verifica na mão** (senão o aluno pensa *"que servidor idiota, por que não usa a lib?"*). Resposta honesta a cravar:
- **Muitos servidores reais fazem exatamente isso:** frameworks de auth caseiros; libs de JWT de **outras linguagens** que **não** têm esse guard; código legado que ramifica pelo `alg`; wrappers que "só queriam suportar RS256 e HS256". **É aí que key confusion mora no mundo real.**
- A própria **recusa do PyJWT é a lição de que libs modernas mitigam isso** — e de que o bug sobrevive em **quem reimplementa a verificação na mão**. O fix (travar `algorithms=["RS256"]` e deixar a lib impor) é, literalmente, *"pare de fazer na mão; deixe a lib moderna fazer o que ela já sabe recusar"*.

---

## Feature simulada — API com autenticação JWT RS256 (API-only, sem HTML)

**Uma API com login por token JWT assinado em RS256.** O cliente faz login e recebe um JWT `role: user` assinado com a chave **privada**. A API **publica a chave pública** (`GET /jwks`) pra clientes verificarem tokens — passo **honesto e por design**. Um endpoint comum aceita qualquer token válido; um endpoint administrativo exige `role: admin`. Do ponto de vista do dev, *"a assinatura RSA garante que ninguém forja um token sem a privada, e eu suporto RS256 e HS256 pra ser flexível"* — mas essa flexibilidade (deixar o token escolher o algoritmo) é a porta.

**Tipo de átomo:** `[ ] com HTML` / `[x] API-only` — **decisão travada** (idêntica ao 13). Justificativa: `CLAUDE.md` §3.3 lista "JWT (todas as variantes)" como naturalmente API-only; o exploit é 100% token-cêntrico (obter a chave pública → forjar → replay); molde do 13; elimina XSS acidental. Consequências (idênticas ao 13): sem HTML, sem `templates/`, sem `render_template`; respostas `application/json` via `jsonify`; corpo JSON no `POST /login`; auth via `Authorization: Bearer <jwt>`; **sem trilha browser** no WALKTHROUGH.

---

## Modelo de identidade e dados — sem banco

**Sem banco** (como 05/11/12/13; `CLAUDE.md` §3.4 — o storage segue a superfície do bug). Dados em estruturas Python em memória. Nota "Stack note — no database" no README, espelhando os irmãos.

**Autenticação simulada — JWT sem senha (molde do 13).** `POST /login` recebe `{"user": "<nome>"}` (default `alice`) e devolve um **JWT RS256** com claims `{"sub": "<nome>", "role": "user"}`, assinado com a chave **privada**. **Sem senha** (auth real fora de escopo, como no 13). `role` **SEMPRE** `user` — o servidor **nunca** emite `admin`. Esse é o ponto: você não "loga como admin", tem que **forjar**.

**Dado admin fake (benigno, sem PII/segredo/chave — `CLAUDE.md` §8.3).** `GET /admin/users` devolve a **mesma** lista curta do 13 — só `user` + `role`, **nada** de senha, PII, ou qualquer chave:

```python
USERS = [
    {"user": "alice", "role": "user"},
    {"user": "bob",   "role": "user"},
    {"user": "carol", "role": "admin"},
]
```

**Estado de processo único** aceitável (nada persiste; restart zera). JWT é stateless — sem store de token. **A chave privada NUNCA aparece em resposta** (nem a título de debug); a **pública** aparece **só** em `/jwks`.

---

## As chaves RSA (decisão do Claude Code — sinalizada)

O átomo precisa de um **par RSA** (privada pra assinar no `/login`; pública pra servir em `/jwks` e verificar no ramo RS256). Duas formas possíveis: (a) gerar em runtime no import; (b) commitar um par fixo (`.pem` dummy no repo). **Decisão travada: par FIXO COMMITADO.** Justificativa:

- **Estabilidade e inspeção:** o aluno vê **exatamente** a chave que forja; o walkthrough é determinístico (tokens/forja reproduzíveis). Gerar em runtime faria a privada **regenerar entre restarts**, quebrando tokens e invalidando o walkthrough capturado; gerar no build faria `vulnerable/` e `fixed/` terem chaves **diferentes**, quebrando a coerência do par (o fixed tem que usar a **mesma** chave RSA que o vulnerable — o que muda é só a verificação).
- **Aviso DUMMY obrigatório** (README + comentário no `app.py`): *"DUMMY lab RSA keypair — never a real key. The private key is committed only because this is an intentionally-vulnerable lab (`CLAUDE.md` §8.3, chaves dummy óbvias)."* A privada no repo é aceitável **só** por ser dummy de laboratório intencionalmente vulnerável.

**Layout (decisão do Claude Code, sinalizada):** commitar `private.pem` + `public.pem` (2048-bit) e lê-los como **bytes crus** no `app.py` (sem `import cryptography` direto — o PyJWT carrega o PEM internamente pra RS256). Como o build context do Docker é **por serviço**, os dois arquivos são **duplicados idênticos** em `vulnerable/keys/` e `fixed/keys/` (mesmo par nos dois; o Dockerfile faz `COPY keys ./keys`). A Fase 2 gera o par **uma vez** (ex.: `openssl genpkey -algorithm RSA -pkcs8 ... -out private.pem` + `openssl rsa -in private.pem -pubout -out public.pem`, público em SubjectPublicKeyInfo `-----BEGIN PUBLIC KEY-----`) e commita os literais.

**CRÍTICO — o invariante frágil (o ponto que faz a forja bater):** a forma que `/jwks` **SERVE** a chave pública DEVE ser **exatamente** a mesma (mesmos bytes, mesmo encoding — PEM com/sem newline final, mesmos headers) que o servidor usa **INTERNAMENTE** como secret HMAC no ramo HS256. **Garantia estrutural:** definir **uma** constante `PUBLIC_KEY_PEM = <bytes de public.pem>` e usar **a mesma variável** nos dois lugares (no corpo de `/jwks` e no `hmac.new(PUBLIC_KEY_PEM, ...)`). Assim são, por construção, os mesmos bytes. Se `/jwks` re-serializasse a chave (normalizando newlines, trocando encoding), o HMAC do atacante **não bateria** e nem o "gabarito" da forja funcionaria. A Fase 2 **valida rodando** (ver Riscos #1 e #5).

---

## Rotas

Imports do **vulnerable**: `import os`, `import json`, `import hmac`, `import hashlib`, `import base64`, `import jwt`, `from flask import Flask, request, jsonify, abort`. (O ramo RS256 delega ao PyJWT; o ramo HS256 usa `hmac`/`hashlib`/`base64`/`json` da stdlib. **Sem** `render_template`, `sqlite3`, `secrets`, `subprocess`, e **sem** `import cryptography` direto — o `cryptography` é dependência **transitiva-mas-necessária** do PyJWT pra RS256; ver "Bibliotecas".)

Imports do **fixed**: `import os`, `import jwt`, `from flask import Flask, request, jsonify, abort`. (O fixed **não** faz HMAC manual → **sem** `json`/`hmac`/`hashlib`/`base64`; o `verify` é um `jwt.decode` travado.)

Constantes e helpers no topo. **A diferença vulnerable × fixed é o `verify` (e os imports que ele exige)** — todo o resto (`/login`, `/jwks`, `/api/profile`, `/admin/users`, `authenticate`, `USERS`, carga das chaves, rodapé) é **idêntico**.

```python
app = Flask(__name__)

# Fixed DUMMY lab RSA keypair (2048-bit). NEVER a real key — committed only because this
# is an intentionally-vulnerable lab (CLAUDE.md §8.3). Same keypair in vulnerable/ and
# fixed/. The private key signs; the public key is published at /jwks and is exactly the
# secret an attacker forges with under HS256 (see DIFF.md).
_KEYS = os.path.join(os.path.dirname(__file__), "keys")
PRIVATE_KEY_PEM = open(os.path.join(_KEYS, "private.pem"), "rb").read()
PUBLIC_KEY_PEM = open(os.path.join(_KEYS, "public.pem"), "rb").read()

USERS = [
    {"user": "alice", "role": "user"},
    {"user": "bob",   "role": "user"},
    {"user": "carol", "role": "admin"},
]
```

### `def verify(token)` — VULNERABLE (o coração materializado)

```python
def _b64url_decode(seg):
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def verify(token):
    # VULNERABLE: the server reads alg from the token's OWN header and picks the
    # verification family from it. RS256 -> RSA-verify with the public key (safe, correct).
    # HS256 -> HMAC-verify using the SAME public-key bytes as the secret (!). The public
    # key is public (served at /jwks), so under HS256 anyone can forge. This alg-controlled
    # branch is the whole bug. (PyJWT refuses an asymmetric key as an HMAC secret, so the
    # HS256 branch is hand-rolled — which is exactly where key confusion lives in the wild.)
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(PUBLIC_KEY_PEM, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            raise ValueError("bad HS256 signature")
        return json.loads(_b64url_decode(payload_b64))
    if alg == "RS256":
        return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
    raise ValueError("unsupported alg")
```

- **A ramificação alg-controlada é OBRIGATÓRIA e visível** (o mantenedor travou isso). Abre como o 05 (`jwt.get_unverified_header` + `if` no `alg`).
- **A MESMA `PUBLIC_KEY_PEM`** nos dois ramos: RS256 a usa como chave de verificação (inofensiva); HS256 a usa como **secret HMAC** (catastrófica). Esse é o colapso da assimetria, no código.
- `alg:none` / desconhecido → `raise` no ramo final → `401` (via `authenticate`). **Uma vuln só.**
- (Forma exata é **candidata**; a Fase 2 confirma/refina pra mínimo e correto, mantendo a ramificação alg-controlada com a mesma chave.)

### `def verify(token)` — FIXED (mesmo SHAPE do 05: travar o algoritmo)

```python
def verify(token):
    # FIXED: stop asking the token which algorithm to use. Pin RS256 and let PyJWT enforce
    # it — a token with alg:HS256 is rejected (HS256 isn't in the allowlist). Same shape as
    # jwt-none-alg's fix: don't branch on the token's alg; declare the allowlist, let the
    # library impose it. The public key is now only ever a *verification* key, never an
    # HMAC secret.
    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
```

### `authenticate()` — idêntico nas duas versões

```python
def authenticate():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        abort(401)
    try:
        return verify(auth.split(" ", 1)[1].strip())
    except Exception:
        abort(401)
```

- `except Exception` (não `jwt.PyJWTError` como nos irmãos): no vulnerable o `verify` manual levanta `ValueError`/`binascii.Error` além de erros do PyJWT; a captura larga mantém `authenticate` **byte-idêntico** entre as versões, localizando **todo** o diff em `verify` + imports. (Candidato; Fase 2 confirma.)

### `POST /login` — obter um JWT RS256 legítimo (idêntico nas duas versões)

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "alice")  # no password — auth ceremony out of scope
    token = jwt.encode({"sub": user, "role": "user"}, PRIVATE_KEY_PEM, algorithm="RS256")
    return jsonify({"token": token})  # role is always "user"; /login never mints admin
```

- `jwt.encode(..., algorithm="RS256")` com um PEM privado retorna `str` em PyJWT 2.x → `jsonify` direto. (Fase 2 confirma.)

### `GET /jwks` — servir a chave PÚBLICA (idêntico nas duas versões; NÃO é o bug)

```python
@app.route("/jwks")
def jwks():
    # Publishing the RSA PUBLIC key is correct and by design: clients verify tokens with
    # it. This is NOT the bug. The bug is the vulnerable server later accepting this same
    # key as an HMAC secret. The bytes served here are the exact bytes the HS256 branch
    # HMACs with — that is what makes the forgery match.
    return PUBLIC_KEY_PEM, 200, {"Content-Type": "application/x-pem-file"}
```

- **Decisão do Claude Code:** servir o **PEM cru** (não um JWK Set JSON). Motivo: a lição do **"mesmos bytes"** fica máxima — o atacante salva o corpo da resposta e usa **esses bytes** como secret HMAC, sem etapa de conversão/decode que reintroduza dúvida de encoding. Nome `/jwks` por ser o termo que o aluno pesquisa; `/public-key` é alias igualmente aceitável. *(Mencionável, não aplicado: um servidor real costuma servir um **JWK Set** JSON, de onde o atacante — ou o jwt_tool — reconstrói o mesmo PEM. Servir PEM aqui é conveniência de clareza de lab; a Fase 2 pode finalizar nome/Content-Type.)*

### `GET /api/profile` e `GET /admin/users` — idênticos ao 13 (e entre as versões)

```python
@app.route("/api/profile")
def profile():
    claims = authenticate()
    return jsonify({"sub": claims.get("sub"), "role": claims.get("role")})


@app.route("/admin/users")
def admin_users():
    claims = authenticate()
    if claims.get("role") != "admin":
        abort(403)
    return jsonify(USERS)
```

- **`403` (não `404`)** pra `role: user` — semanticamente correto, sem oráculo de enumeração (endpoint fixo, não indexa objeto por id sequencial). Mesma justificativa do 13; **não** copiar o `404` do 12 por reflexo.
- A verificação de assinatura acontece dentro de `authenticate()`/`verify()` **antes** do check de `role`: token inválido morre em `401` no `verify`, nunca chega no `if role != admin`.

### Rodapé (idêntico nas duas versões)

```python
if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

---

## O bug e o fix — diff de LÓGICA-DIFERENTE (irmão do 05)

**Tipo de diff: lógica-diferente** — a ramificação manual alg-controlada do `vulnerable` vira a allowlist travada do `fixed`. É o tipo dos A01 e do **05** (código presente e errado → corrigido), **NÃO** o valor-diferente do 13. **Não inventar um "quarto tipo".** O `app.py` difere em: (a) os imports (`json`/`hmac`/`hashlib`/`base64` saem no fixed), (b) o helper `_b64url_decode` (sai no fixed), e (c) o `verify` (ramificação manual → `jwt.decode` travado). Todo o resto (`/login`, `/jwks`, `/api/profile`, `/admin/users`, `authenticate`, `USERS`, carga das chaves, rodapé) é **byte-idêntico**, incluindo as **mesmas chaves RSA**.

### Notas obrigatórias no `DIFF.md`

1. **O mesmo SHAPE de fix do 05 (obrigatório, o núcleo).** 05 removeu o branch `alg:none`; 14 remove o branch alg-controlado e trava `algorithms=["RS256"]`. **Os dois param de confiar no `alg` do token.** Mecanismo diferente (05: `none` = pular a verificação; 14: confusion = trocar de família). Cravar a regra do 05, idêntica: *"declare `algorithms=` as a positive list and never branch off `header['alg']`; the header is data, not policy."* Incluir o callback à §5/DIFF do 05, que já nomeou "algorithm-confusion ... using the wrong key" como flavor da mesma doença.
2. **Contraste com o 13 (valor vs. lógica).** O fix do 13 trocou um **VALOR** (secret fraco→forte), zero linha de lógica; o fix do 14 muda **CÓDIGO** (remove o branch). E o mais importante: no 13 algo estava **fraco** (o secret); no 14 **NADA** está fraco — chave RSA forte, assinatura que **bate** — e mesmo assim cai. O 14 é o mais insidioso.
3. **POR QUE o servidor verifica na mão (obrigatório — SAÍDA B).** O PyJWT moderno **bloqueia** a confusão ingênua (`InvalidKeyError` ao receber chave assimétrica como secret HMAC), então um servidor que usasse a lib "do jeito ingênuo" **não** seria vulnerável. Key confusion mora em **verificação hand-rolled** (frameworks caseiros, libs de outras linguagens sem esse guard, código que ramifica pelo `alg`). O átomo reproduz esse anti-padrão honestamente. A recusa do PyJWT **é** a lição: libs modernas mitigam; o bug sobrevive em quem reimplementa. *(E a forja também é manual pelo mesmo motivo — ver "A forja".)*
4. **O colapso da assimetria (a lição-coração no diff).** A **mesma** `PUBLIC_KEY_PEM` está nos dois ramos do `verify` vulnerável: inofensiva sob RS256 (verifica), catastrófica sob HS256 (vira secret de forja). Mesmos bytes, dois algoritmos, dois significados de segurança.
5. **A02 que não `grep`a.** `jwt.decode(..., algorithms=["RS256"])` é o que o código **correto** parece; o bug é a ramificação escrita ao lado. Pega-se lendo a lógica e perguntando *"quem escolhe o algoritmo?"*. O RSA e o HMAC estão intactos — a raiz é **erro de lógica**, não cripto quebrada.
6. **`403` (não `404`)** no `/admin/users` — nota curta pra evitar cópia reflexa do 12 (mesma do 13).
7. **`/jwks` publica a pública de propósito (não é o bug), e o fix não o toca.** A chave RSA continua a mesma e forte; só o `verify` muda. Publicar a chave pública é correto sob RS256 — o erro era **aceitá-la como secret HMAC**.

---

## A forja — script Python explícito (stdlib) + jwt_tool linkado

A forja é **CONSTRUÇÃO**, não brute-force (diferente do 13, que quebrava com john — **a memória `jwt-hmac-crack-needs-jumbo-john` NÃO se aplica aqui**, não há crack). Um **script Python explícito** no walkthrough, **stdlib pura** (espelha o ramo HS256 do servidor — reforça o "mesmos bytes"):

```python
import base64, hmac, hashlib

# The EXACT bytes served by GET /jwks (save the response body to jwks.pem).
pub = open("jwks.pem", "rb").read()

def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")

header = b64url(b'{"alg":"HS256","typ":"JWT"}')
payload = b64url(b'{"sub":"alice","role":"admin"}')
signing_input = header + b"." + payload
sig = b64url(hmac.new(pub, signing_input, hashlib.sha256).digest())
print((signing_input + b"." + sig).decode())
```

- O aluno **VÊ** exatamente: qual chave (os bytes do `/jwks`), qual encoding (base64url), qual algoritmo (HMAC-SHA256) — a lição do "mesmos bytes" fica visível. É o **espelho** do ramo HS256 do servidor.
- **POR QUE não é um one-liner PyJWT (contraste com o 13):** no 13 a forja foi `jwt.encode({...}, secret, algorithm="HS256")` — o PyJWT aceita uma **string** como secret. Aqui o secret é a **chave pública RSA**, e o PyJWT **recusa** (`InvalidKeyError`) — então a forja **tem** que ser manual (stdlib) ou via uma ferramenta que faça o HMAC na mão. Isso é a mesma proteção que o servidor vulnerável contornou, agora batendo no atacante: **cravar** que nem atacante nem servidor honesto conseguem fazer isso via PyJWT direto — só hand-rolled.
- **Mencionar o jwt_tool como a ferramenta de campo** (tem modo de key confusion pronto, ex. `-X k` com `-pk public.pem`) — **LINKAR** (`https://github.com/ticarpi/jwt_tool`, **confirmar a URL exata por fetch na Fase 2**), **NÃO ensinar** (mesma disciplina do john no 13: usada/linkada, não tutorial de instalação/flags). O script Python é a trilha primária por ser transparente e sem dependência extra; o jwt_tool é o "no campo se usa isto".
- **O snippet mostrado DEVE ser real e ter rodado** (validação Fase 2 — capturar o token de saída real e confirmar o replay → `200`).

---

## A trilha — Burp planta/replaya, o terminal forja

`CLAUDE.md` §3.3 põe o Burp como primário, com a exceção de quando a *prova* exige algo que o Burp não faz. **Este átomo é análogo ao 13:** o Burp não computa um HMAC-com-chave-pública. A **trilha principal** divide as ferramentas:

- **Burp (Repeater):** login, captura do token legítimo, `GET /jwks` (ou `curl`) pra pegar a chave pública, e o **replay** do token forjado no `/admin/users`. A parte "profissão" — controle cru do request/header/token.
- **Terminal do aluno (script Python):** monta o token `alg:HS256 role:admin` e assina o HMAC com os bytes da chave pública. **Fora do Burp, fora do container.** É o passo central.

**Sem trilha browser** (API-only — `CLAUDE.md` §3.3). Registrar pro Claude Code da Fase 2: WALKTHROUGH em Burp + terminal, **sem** browser. *(Diferente do 13, aqui o passo de terminal é **construção determinística**, não brute-force — valida rodando o script e replayando, sem cracker.)*

---

## Bibliotecas — PyJWT (coerência com os irmãos) + cryptography (pra RSA)

- **`PyJWT==2.12.1`** — a **mesma** dos irmãos 05 e 13. Usada pra: assinar RS256 no `/login`, o ramo RS256 do `verify` vulnerável, e o `jwt.decode` travado do `verify` FIXED. O ramo HS256 do vulnerable **contorna** o PyJWT (usa `hmac`/`hashlib`), porque o PyJWT **bloquearia** a confusão (essa é a lição da SAÍDA B).
- **`cryptography`** — **segunda dependência** além do PyJWT (o 05 e o 13 eram Flask+PyJWT só). O PyJWT **exige** `cryptography` instalado pra suportar RS256 (a família RSA é implementada sobre ela); sem ela, `jwt.encode/decode` RS256 **falham**. É load-bearing **mesmo o `app.py` não a importando diretamente** (o PyJWT a usa por baixo). **Confirmar a versão exata na Fase 2** (a mais atual que instala limpo com `PyJWT==2.12.1` no `python:3.11-slim` — sem CVE de brinde, `CLAUDE.md` §8.5). Registrar no `requirements.txt` explicitamente (Dependabot off, updates manuais — `CLAUDE.md` §8.7).
- **Nota sobre o pin (`CLAUDE.md` §8.7):** aqui o pin é **coerência/reprodutibilidade** — a vuln (confiar no `alg` do token) é **agnóstica de versão** de lib; ela vive na lógica hand-rolled, não num comportamento específico do PyJWT. Ao contrário: o comportamento do PyJWT moderno é o que **mitiga** a versão ingênua, e é por isso que a SAÍDA B (verificação manual) existe. Registrar: o pin do 14 **não é behavior-critical** como o do 05 (que estuda como uma versão trata `alg:none`).
- **`requirements.txt` (idêntico vulnerable × fixed):** `Flask==3.0.0`, `PyJWT==2.12.1`, `cryptography==<a confirmar na Fase 2>`.

---

## Renderização / "um átomo = uma vuln"

**API-only, respostas JSON via `jsonify`** — **sem templates**, logo **sem risco de XSS acidental**. A única vuln é a confusão de algoritmo. Garantir (ver também "Uma vuln só"):
- **Só `HS256` e `RS256` tratados; `alg:none`/desconhecido → `401`** (senão empilharia a vuln do 05).
- **Sem vazamento de chave:** a **privada NUNCA** é serializada; a **pública** só em `/jwks`; `/admin/users` devolve só dado fake benigno.
- **Erros via `abort()` cru** (padrão Flask): o **status code é o sinal do exploit** (`200`/`401`/`403`); corpo do erro é imaterial e **não reflete input** (sem XSS). Consistente com 03/05/10/11/12/13. Error handler JSON seria polimento cosmético — **mencionável, não aplicado** (`CLAUDE.md` §3.6).

---

## Walkthrough — estrutura e beats

Trilha principal **Burp + terminal**, **sem browser** (API-only). Cada request é um bloco colável no Repeater; o script de forja em bloco `python`/`bash`. Tokens/chaves são placeholders da sessão real capturada na Fase 2. Estrutura de beats (molde do 13):

> **Abertura — plantar a lição.** Tease: *você vai pegar a chave PÚBLICA da API — que é pública de propósito, qualquer um pode baixá-la — e com ela forjar um token `role: admin` que o servidor aceita como genuíno. Não porque a assinatura está quebrada (ela bate matematicamente), não porque a chave é fraca (é um RSA de 2048 bits) — mas porque o servidor deixou o TOKEN escolher qual algoritmo usar. Você diz "verifique isto como HMAC", e a chave pública — inofensiva pra verificar sob RSA — vira a chave de assinar sob HMAC. Nada está fraco. E mesmo assim abre.*

### 1. Context
- API com auth por JWT **RS256**: `POST /login` (dá seu token `role: user`), `GET /jwks` (publica a chave **pública** — honesto, por design), `GET /api/profile` (qualquer token válido), `GET /admin/users` (exige `role: admin`). Isto é **A02 — algorithm confusion (RS256→HS256)**. Trilha: Burp (login, captura, `/jwks`, replay) + terminal (forja). API-only, sem browser. **Situar na trilogia já aqui:** 05 = não trancava (`alg:none`); 13 = trancava, chave fraca; 14 = tranca, chave **forte**, o token escolhe o algoritmo.

### 2. Spot the bug
- Mostrar o `vulnerable/app.py`. Apontar que o `verify` **abre igual ao do 05** — `jwt.get_unverified_header(token)` e um `if` no `alg`. O ramo RS256 é **correto** (verifica com a pública). O ramo **HS256** faz HMAC com a **mesma chave pública** como secret — e a chave pública é **pública**. Pergunta de auditoria: *"quem escolhe qual ramo roda?"* → o **token**. Esse branch é o bug. Foreshadow do fix: "a correção vai **parar de perguntar ao token** e travar `algorithms=["RS256"]` — o mesmo movimento do 05".

### 3. RS256 vs HS256 — a crux (recap curto)
- RS256 é **assimétrico**: privada assina, pública verifica; **saber verificar não ensina a assinar** — é o que torna seguro publicar a pública. HS256 é **simétrico**: a mesma chave assina e verifica. Quando o servidor trata a chave pública como secret HMAC, a assimetria **colapsa**: a pública vira chave de **assinar**. E o atacante a **tem**. Cravar a sub-lição: **mesma chave, dois algoritmos, dois significados de segurança**. (Pra anatomia byte-a-byte de um JWT, apontar pro 05 §2 — auto-contido, não repete o primer inteiro.)

### 4. Baseline — a API funcionando (Repeater)
- `POST /login {"user":"alice"}` → `{"token":"<jwt RS256>"}` (role `user`). `GET /api/profile` com o token → `200`, claims. `GET /admin/users` com o mesmo → **`403`** (autenticado, não admin). `GET /jwks` → a chave pública PEM (seu material de forja — e é pública por design). Baseline legítimo.

### 5. Step 1 — Grab the public key (`GET /jwks`)
- Baixar a chave pública (Burp ou `curl`), salvar os **bytes exatos** num arquivo (`jwks.pem`). Recon **honesto** — a chave é pra ser pública. Cravar: *"o que vem a seguir não quebra nenhum segredo; usa um dado público de um jeito que o servidor não devia permitir."*

### 6. Step 2 — Forge the token (terminal, script Python explícito)
- Montar header `alg:HS256` + payload `role:admin`, HMAC-SHA256 sobre o signing input usando **os bytes exatos da chave pública** como secret. Mostrar o **script real** e o **token de saída real** (Fase 2). Cravar o "mesmos bytes". Nota: **o PyJWT recusa** fazer isso (chave assimétrica como secret HMAC) — atacante e servidor honesto **têm** que cair no HMAC manual; essa recusa **é** a proteção que o servidor vulnerável contornou. Mencionar + linkar o **jwt_tool** (modo de key confusion), sem tutorializar.

### 7. Step 3 — Replay the forged token (Burp)
- `GET /admin/users` com `Authorization: Bearer <forged HS256 jwt>` → **`200`**, o dado admin. **Escalação vertical confirmada.** Você não quebrou o RSA nem o HMAC — você fez o servidor **verificar com a chave errada**, deixando o token escolher o algoritmo.

### 8. What the vuln is NOT (passo de contraste — isola a causa e crava a trilogia)
Serve à §5 do `CLAUDE.md` (isolar a causa real, desmontar mal-entendidos vizinhos — aqui a confusão com 05, com 13, e com "a cripto foi quebrada"). Provar, no Repeater:
- **NÃO é cripto quebrada.** O RSA está intacto, o HMAC está intacto, a chave tem 2048 bits. Um token RS256 legítimo ainda verifica; a assinatura RSA é sólida. Nada foi quebrado matematicamente.
- **NÃO é chave fraca (não é o 13).** A chave RSA é robusta; a confusão **não** precisa de chave fraca. Você não adivinhou nada — você **usou** a chave pública, que é pública.
- **NÃO é `alg:none` (não é o 05).** Mande um token `alg:none` → **`401`** (só `HS256`/`RS256` tratados). MAS cravar o **parentesco** com o 05: os dois são o servidor confiando no `alg` do token — 05 diz "não verifique", 14 diz "verifique com esta família". Mesma doença, sintoma diferente.
- **É SÓ o servidor deixar o token escolher o algoritmo.** Prova cirúrgica: pegue o token forjado e troque o `alg` do header pra `RS256` (mantendo a assinatura HMAC) → **`401`** (o ramo RS256 faz RSA-verify, falha). Só a porta **HS256-com-a-chave-pública** abre. A falha inteira é a ramificação alg-controlada.
- **A trilogia explícita** (tabela 05/13/14): não verifica → verifica com chave fraca → verifica com chave forte deixando o token escolher COMO.

### 9. Impact (honesto — sem overclaim)
- Escalação **VERTICAL** de privilégio, **igual ao 13**: com a chave pública (que é pública!), o atacante forja **qualquer** token — vira admin, ou qualquer user, com qualquer claim. Impacto: **controle da autenticação** daquela app. **NÃO é RCE.** Sem overclaim. Cravar: o que faz o 14 ser o **clímax** **não** é impacto maior que o 13 (é o mesmo, vertical) — é o **mecanismo mais insidioso**: nada está fraco (chave forte, assinatura que bate), e mesmo assim cai.

### 10. Why the fix works (porta 8114)
Repetir a cadeia contra o `fixed/`:
- O **mesmo** token forjado (`alg:HS256`) → **`401`** (o `jwt.decode(..., algorithms=["RS256"])` ignora o `alg` do token e exige RS256; HS256 não está na allowlist).
- Um token RS256 **legítimo** → ainda `200` no `/api/profile`, `403` no `/admin/users` (o role gate segue de pé).
- Tudo mais **idêntico**: mesmos endpoints, mesmas chaves RSA, mesmo `/jwks`. **A única mudança é o `verify`** (ramificação manual → decode travado).
- **A lição do diff:** o fix é o **mesmo movimento do 05** — parar de confiar no `alg` do token, travar a allowlist, deixar a lib impor. (Forward pro `DIFF.md`.)

**Sem trilha browser** (API-only) e **sem** seção de exercícios/variações (`CLAUDE.md` §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## O container

`Dockerfile` **idêntico** entre vulnerable e fixed, e **API-only** (sem `COPY templates`, como o 13) **mas com `COPY keys`** (o 13 não tinha chaves; o 14 tem). PyJWT + cryptography instalam via pip (sem `apt`). Esqueleto:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY keys ./keys
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

- **As chaves SÃO copiadas pro container** (`COPY keys ./keys`) — diferente da `wordlist` do 13, que ficava fora. Aqui o app precisa da privada (assinar) e da pública (servir/verificar) em runtime. Os `keys/` (par idêntico) vivem em `vulnerable/keys/` e `fixed/keys/`.
- `docker-compose.yml`: `127.0.0.1:8014:5000` (vulnerable), `127.0.0.1:8114:5000` (fixed) — esqueleto de duas services do 05/13, sem `sysctls`. Bind **só** em `127.0.0.1`.
- **`cryptography` no `python:3.11-slim`:** a Fase 2 confirma que instala limpo (wheel; sem precisar de toolchain de build). Se exigir `build-essential`/headers, **sinalizar** — preferir uma versão com wheel pra `slim` a inflar o Dockerfile.

---

## Dependências extras

```
Flask==3.0.0
PyJWT==2.12.1
cryptography==<a confirmar na Fase 2>
```

Idêntico entre vulnerable e fixed. `os`/`json`/`hmac`/`hashlib`/`base64` são stdlib (não vão no `requirements`). **Nada** de banco, templates, `apt`, ou outra lib. `CLAUDE.md` §3.6 respeitado (o `cryptography` serve à demonstração: sem ele não há RS256).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página conceitual da vuln. Os irmãos 05 e 13 usam **[PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt)**. Algorithm confusion é uma sub-classe coberta nessa página (a Academy tem uma seção **"Algorithm confusion attacks"** / **"JWT algorithm confusion"**).

- **Candidato do bloco (confirmar por fetch na Fase 2):** [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt) — **a mesma página dos irmãos**, por coerência entre os três átomos JWT.
- **Fase 2:** verificar por fetch se há uma **âncora/seção específica de algorithm confusion** dentro de `/web-security/jwt` (ex.: `#algorithm-confusion-attacks`) e, se houver, **preferi-la**; senão, a página geral. Espelhar a nota parentética que o 13 usa: *"(Its 'Algorithm confusion attacks' section is this atom.)"*. **Não inventar a URL** — confirmar por fetch.
- **Texto do link:** preservar **"JWT attacks"** em inglês também no README PT (convenção `CLAUDE.md` §7 / 05 / 13).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A02 — Cryptographic Failures** | Coerência com 05 e 13 (mesma pasta, confirmado no repo e no ROADMAP); superfície = mecanismo de assinatura JWT. Raiz é erro de lógica de verificação (nuance honesta, não contradiz A02). |
| Nome / classe | **JWT algorithm confusion (RS256 → HS256)** | Terceiro e último ataque a JWT; nada fraco — o token escolhe o algoritmo. |
| Posição na trilogia | **Terceiro/clímax** (fecha a trilogia JWT) | 05 (não verifica) → 13 (chave fraca) → 14 (token escolhe o algoritmo). O contraste é a lição. **Não** prometer um quarto. |
| Posição na Fase 3 | **Quarto átomo** (NÃO fecha a fase) | ROADMAP: o `session-fixation` (15) é o phase-closer. Ver Nota de planning 1. |
| Lição-coração | **"o token escolhe o algoritmo → a assimetria colapsa → a chave pública vira secret de forja"** + sub-lição "mesma chave, dois algoritmos, dois significados" | RSA/HMAC intactos; a falha é 100% confiar no `alg` do token. |
| Enquadramento | **Erro de LÓGICA, não cripto quebrada** | O átomo materializa o erro no código (branch alg-controlado). Afia a tese "looks-like-crypto is not is-crypto" do 05. |
| Contraste com o 05 | **MESMO shape de fix** (não confie no `alg` do token; trave a allowlist) | Irmão direto no fix. Mecanismo diferente (05 none = pular; 14 = trocar de família). Callback à §5 do 05 (permitido). |
| Contraste com o 13 | **Nada está fraco** (vs. o secret fraco do 13); fix de código (vs. fix de valor) | O 14 é o mais insidioso: chave forte, assinatura que bate, e cai. |
| Escalação | **VERTICAL** (`role: user` → `role: admin` forjado) | Mesmo impacto do 13; mecanismo diferente. Distingue do horizontal dos A01 (11/12). |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | `CLAUDE.md` §3.3 (JWT naturalmente API-only); exploit token-cêntrico; molde do 13. |
| Feature | **API JWT RS256** (`/login`, `/jwks`, `/api/profile`, `/admin/users`), em memória | Habitat canônico. `/jwks` publica a pública (honesto). Sem banco. |
| `POST /login` | JSON `{"user"}` (default `alice`), **sem senha**, `role` sempre `user`, JWT **RS256** | Molde do 13. Login nunca emite `admin` → força a forja. |
| `GET /jwks` | Serve a chave **pública** como **PEM cru** (idêntico nas versões) | Não é o bug (publicar a pública é correto). PEM cru maximiza a lição "mesmos bytes". Decisão do Claude Code. |
| O bug | **Verificação hand-rolled que ramifica pelo `alg` do token** (SAÍDA B) | O PyJWT moderno bloqueia a confusão ingênua; o anti-padrão real é a verificação na mão. Sem CVE de brinde. |
| Verificação vulnerável | **`jwt.get_unverified_header` + `if alg`; HS256 = HMAC(`PUBLIC_KEY_PEM`); RS256 = `jwt.decode(...RS256)`** | Abre igual ao 05. A mesma chave nos dois ramos = colapso da assimetria, visível. |
| Fix (único eixo) | **Remover o branch, travar `jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])`** | Mesmo movimento do 05. A pública volta a ser só chave de verificação. |
| Diff | **Lógica-diferente** (branch manual → allowlist travada) | Tipo dos A01/05 (código presente e errado → corrigido). **Não** o valor-diferente do 13; **não** inventar quarto tipo. |
| Chaves RSA | **Par fixo commitado, dummy 2048-bit; `private.pem`+`public.pem` duplicados em `vulnerable/keys/` e `fixed/keys/`** | Estabilidade/inspeção; a mesma chave nas duas versões. Aviso DUMMY. Decisão do Claude Code. |
| Invariante das chaves | **`/jwks` serve os MESMOS bytes que o HS256 branch HMACa** (uma constante `PUBLIC_KEY_PEM`) | Sem isso a forja não bate. Ponto frágil #1/#5 — validar rodando na Fase 2. |
| Forja | **Script Python stdlib** (`hmac`/`hashlib`); **não** PyJWT (recusa chave assimétrica); **jwt_tool** mencionado+linkado | Transparente, "mesmos bytes"; contraste com o one-liner PyJWT do 13. |
| Bibliotecas | **PyJWT==2.12.1** (irmãos) + **cryptography** (RS256) | Coerência; `cryptography` é load-bearing pro RS256 do PyJWT. Pin não é behavior-critical (≠ 05). |
| Trilha | **Burp (login/captura/`/jwks`/replay) + terminal (forja); SEM browser** | API-only; a exceção da §3.3 cobre o terminal na trilha principal. Sem crack (≠ 13). |
| Nº de beats | **Baseline + 3 steps + contraste + impacto + fix** | Baseline → pegar a pública → forjar → replay → "o que a vuln NÃO é" (crava a trilogia). |
| Impacto | **Escalação vertical / controle da auth.** Não RCE. | Honesto, igual ao 13. O clímax é pelo mecanismo, não pelo impacto. |
| Theory primer | **PortSwigger JWT attacks** (mesma dos irmãos); checar âncora de algorithm confusion na Fase 2 | `CLAUDE.md` manda PortSwigger; coerência. URL confirmada por fetch. |
| Erros | **`abort()` cru**; status code é o sinal | Consistente com 03/05/10/11/12/13. Corpo não reflete input (sem XSS). |
| `app.py` vulnerable × fixed | **Diferem no `verify` + imports que ele exige** | Resto byte-idêntico (mesmas chaves inclusive). Diff lógica-diferente. |
| Dockerfile / compose | Esqueleto do 13 + **`COPY keys`**; portas 8014/8114 | Idêntico entre versões; bind só `127.0.0.1`. Chaves copiadas pro container (≠ wordlist do 13). |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–9 são os centrais pedidos; 10–12 são higiene técnica. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /jwks`** serve a chave pública RSA, e a forma (encoding/bytes) é **EXATAMENTE** a que o servidor usa internamente como secret HMAC no ramo HS256 (mesma constante `PUBLIC_KEY_PEM`). **A privada NUNCA é servida** por endpoint algum.
2. **`POST /login`** devolve um **JWT RS256 válido** `{"sub": "...", "role": "user"}`, assinado com a **privada**. Decodificar confirma as claims e `alg: RS256`. `jwt.encode` RS256 retorna `str`.
3. **Baseline:** token legítimo (RS256, `role: user`) → `GET /api/profile` `200`; `GET /admin/users` com `role: user` → **`403`**.
4. **Verificação vulnerável correta pra tokens legítimos:** um token RS256 legítimo passa (ramo RS256 verifica com a pública). Um token RS256 com **assinatura inválida** → **`401`**. Um `alg` **desconhecido** (ex. `ES256`, lixo) **ou** **`alg:none`** → **rejeitado** (`401`, não cai em ramo válido — prova que a única porta é a confusão HS256, **não** empilha o 05).
5. **O ATAQUE (item central — VALIDAR RODANDO, o ponto frágil):** forjar de VERDADE um token `alg:HS256 role:admin` assinando HMAC-SHA256 com os **bytes exatos da chave pública** (a forma do `/jwks`) como secret. Confirmar `GET /admin/users` com o token forjado → **`200`** + dado admin (escalação vertical). **CAPTURAR** o script real e o request/response real. Se o HMAC **não bater** (encoding errado), **AJUSTAR** até bater com a forma que o servidor usa e **DOCUMENTAR** a forma exata. **NÃO inventar** — se a forja não bater rodando, **PARAR e avisar o mantenedor**.
6. **Fixed (8114):** o **MESMO** token forjado (`alg:HS256`) → **`401`** (`algorithms=["RS256"]` ignora o `alg` do token e exige RS256). Um token RS256 **legítimo** → ainda `200` no `/api/profile`, `403` no `/admin/users`. Endpoints e chaves idênticos; só o `verify` muda (manual ramificado → decode travado).
7. **`app.py` vulnerable × fixed:** confirmar por `diff` que a mudança é o `verify` (+ os imports `json`/`hmac`/`hashlib`/`base64` e o helper `_b64url_decode` que saem no fixed), e que o resto (`/login`, `/jwks`, `/api/profile`, `/admin/users`, `authenticate`, `USERS`, carga das chaves, rodapé) é **coerente/idêntico**, **incluindo as mesmas chaves RSA**. Diff **lógica-diferente** (como o 05).
8. **Uma vuln só:** chave RSA **forte** (2048+); **sem** privada serializada; **sem** `alg:none` por caminho separado; `/admin` devolve só dado fake benigno; API-only → sem XSS. O PyJWT **bloqueia** a confusão ingênua — confirmar que é **por isso** que o vulnerable faz HMAC manual (documentar no DIFF).
9. **Links por fetch:** **jwt_tool** (`github.com/ticarpi/jwt_tool`, confirmar URL + que tem modo de key confusion). **Primer PortSwigger JWT** (mesma URL dos irmãos; checar âncora específica de algorithm confusion).
10. **API-only confirmado:** **sem** `templates/`, Dockerfile **sem** `COPY templates` (mas **com** `COPY keys`), `app.py` **sem** `render_template`; respostas de sucesso em `application/json` (exceto `/jwks`, que serve `application/x-pem-file`). Chaves **copiadas** pro container.
11. **Libs:** `PyJWT==2.12.1` + `cryptography==<versão>` instalam limpo no `python:3.11-slim` (wheel, sem toolchain de build — se exigir, **sinalizar**); RS256 sign/verify e o decode travado funcionam; a forja HMAC-com-pública bate; `jwt.encode` retorna `str`. **Sem CVE de brinde** (`CLAUDE.md` §8.5). Portas `8014`/`8114` **só** `127.0.0.1`.
12. **Chaves DUMMY:** par fixo commitado, marcado como DUMMY de lab (aviso claro no README e no `app.py`); gerado uma vez na Fase 2; `private.pem`+`public.pem` idênticos em `vulnerable/keys/` e `fixed/keys/`.

**Bloqueante remanescente:** nenhum de decisão. **Pendência a reconciliar (não técnica):** a posição na Fase 3 (Nota de planning 1 — 14 fecha a trilogia, o 15 fecha a fase). Pendências de Fase 2 (não bloqueantes agora): validar a forja rodando (o ponto frágil #5); confirmar a versão do `cryptography`; confirmar as URLs do primer e do jwt_tool por fetch; gerar o par RSA dummy.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo **fecha a trilogia JWT** e é irmão do **05 no shape do fix** e do **13 no molde/impacto**. Cada beat deve poder ser lido com 05 e 13 abertos ao lado; a tabela 05/13/14 e o par "mesmo bug de fundo do 05 (confiar no `alg`), mecanismo diferente" têm que estar visíveis na abertura, no contraste e no fechamento. **Abrir e fechar** na lição-coração: o token escolhe o algoritmo → a assimetria colapsa → a chave pública vira secret de forja; **nada está fraco**.
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** `jwt-none-alg` (05) **inteiro** (irmão do fix — reusar `jwt.get_unverified_header`+`if alg`, a regra "header is data, not policy", o callback à §5) **e** `jwt-weak-secret` (13) **inteiro** (molde API-only — `/login` sem senha, JSON, `/api/profile`+`/admin/users`, `USERS`, WALKTHROUGH sem browser, notas "API only"/"Authentication, simulated"/"Stack note — no database"; impacto vertical). Ler também esta spec e o `sqli-union-basic` (referência canônica).
- **Átomo stateless, sem banco, sem templates, API-only** (como o 13): dados em memória, JWT stateless. **Sem** `sqlite3`, `render_template`, `templates/`. **Com** `keys/` (par RSA dummy) copiado pro container.
- **SAÍDA B é o coração estrutural:** o vulnerable verifica **na mão** e ramifica pelo `alg`; explicar **por quê** (o PyJWT moderno bloqueia a confusão ingênua; key confusion mora na verificação hand-rolled do mundo real). Sem isso o aluno acha o servidor idiota. Cravar no DIFF e no WALKTHROUGH.
- **O ponto técnico frágil é a forja bater (risco #5).** `/jwks` serve os **mesmos bytes** que o HS256 branch HMACa (uma constante `PUBLIC_KEY_PEM`). Forjar de verdade e confirmar `200` no `/admin/users`. **Se não bater, PARAR e avisar — NÃO inventar** o token/output.
- **Uma vuln só:** só `HS256`/`RS256` tratados; `alg:none` → `401` (senão empilha o 05); chave RSA forte; privada nunca serializada; sem XSS.
- **A forja é CONSTRUÇÃO, não crack** (≠ 13; a memória do john **não se aplica**). Script Python stdlib transparente; **não** PyJWT (recusa chave assimétrica — cravar esse contraste com o one-liner do 13). jwt_tool **mencionado+linkado**, não ensinado.
- **Impacto honesto:** escalação **VERTICAL** / controle da autenticação; **não** RCE. Igual ao 13 no impacto; o clímax é pelo **mecanismo** (nada fraco), não pelo impacto.
- **Política de referência cross-átomo:** OK e **obrigatório** referenciar `jwt-none-alg` (05) e `jwt-weak-secret` (13) explicitamente (o contraste/trilogia é a lição). OK citar de leve os A01 desta fase (11/12) pelo eixo horizontal-vs-vertical. **PROIBIDO** referenciar/foreshadowar **qualquer** átomo não publicado — inclui o **`session-fixation` (15)** e **não há um quarto átomo JWT** (a trilogia FECHA aqui). Enquadrar como **"os três ataques a JWT do projeto"**, **sem** prometer um quarto e **sem** antecipar a Fase 4 ou o phase-closer. *(O débito do 05 já foi quitado pelo #23 — Nota de planning 2 — não reintroduzir referência por número.)*
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico em EN e PT (`jwt-key-confusion — JWT algorithm confusion (RS256 → HS256)`, texto exato confirmável na Fase 2). Termos técnicos (JWT, RS256, HS256, HMAC, RSA, algorithm confusion / key confusion, alg, claim, `sub`/`role`, `Bearer`, sign/verify, forge, public key/private key, PEM/JWK, allowlist, payload) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger JWT attacks (mesma URL dos irmãos, texto `JWT attacks` preservado em inglês no PT). **Confirmar a URL por fetch na Fase 2** (checar âncora de algorithm confusion).
- **Chaves:** par RSA dummy fixo commitado (`private.pem`+`public.pem`, 2048-bit), duplicado idêntico em `vulnerable/keys/` e `fixed/keys/`; aviso DUMMY no README e no `app.py`. Privada no repo aceitável **só** por ser dummy de lab (`CLAUDE.md` §8.3).
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 14: `jwt-key-confusion` — JWT algorithm confusion, RS256→HS256 (A02 Cryptographic Failures). `` (padrão das linhas dos átomos 06–13).
- **ROADMAP.md:** marcar o átomo 14 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec. *(E — separadamente — reconciliar a Nota de planning 1 se a intenção for reordenar a Fase 3.)*
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–12; reproduzir baseline → `/jwks` → **forja real (HMAC-com-pública)** → replay (`200` admin) → contraste (`alg:none`/RS256-com-sig-HMAC → `401`) → fixed (token forjado → `401`, RS256 legítimo → `200`/`403`). Validar via `docker exec` + `python http.client` de dentro do container se as portas host não forem alcançáveis do sandbox (a forja roda no host/terminal, fora do container).
- **Portas:** `127.0.0.1:8014` (vulnerable), `127.0.0.1:8114` (fixed). Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre a versão do `cryptography`, a URL do primer/jwt_tool, a âncora de algorithm confusion, ou se a forja não bater rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).
