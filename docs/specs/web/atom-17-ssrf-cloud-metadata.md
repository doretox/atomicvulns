# Spec — Átomo 17: `ssrf-cloud-metadata`

> Documento de especificação para o Claude Code implementar o décimo-sétimo átomo do projeto `atomicvulns` (Fase 4 — "Server-side Avançado", milestone `v0.4.0`). Este átomo é o **SEGUNDO átomo da Fase 4** (2º dos cinco — `16 ssrf-blind-oob`, **`17 ssrf-cloud-metadata`**, `18 xxe-basic`, `19 ssti-jinja`, `20 deserialization-pickle`; confirmado no `ROADMAP.md`) e **NÃO muda de eixo**: é a **CONTINUAÇÃO e o PAGAMENTO do arco de SSRF (A10)** que começou no átomo 04 (`ssrf-basic`) e seguiu no 16 (`ssrf-blind-oob`). É o **TERCEIRO átomo A10 do repo** e — crucial — **É O ÚLTIMO A10 do roadmap: FECHA o arco de SSRF** (não há próximo A10; o átomo seguinte já é outra categoria). É **infra-pesado como o 04/16**: topologia **MULTI-CONTAINER** (`vulnerable` + `fixed` + `metadata-mock`).
>
> **A lição em uma linha:** um SSRF que alcança o **endpoint de metadata da cloud** (o IMDS, em `169.254.169.254`) devolve as **CREDENCIAIS IAM** da instância — e quem tem essas credenciais **assume o papel da instância na conta cloud**. É o **mesmo primitivo de SSRF** dos átomos anteriores, apontado pro **alvo de maior valor** que existe em toda VM de cloud. O fix é **validar o destino (allowlist deny-by-default)** antes do fetch.
>
> **O que muda do 04 pro 17 NÃO é o mecanismo** (os dois são **in-band**: a app busca e MOSTRA a resposta) — é o **ALVO** (o IMDS, não um serviço interno genérico) e o **IMPACTO** (roubo de credencial IAM → account takeover, não a simples leitura de um dashboard interno). A escalada sobre o 04 é o *alvo específico e ubíquo*, não uma técnica nova.
>
> Leia junto com `CLAUDE.md` (Seção 3.3 — este átomo **TEM HTML e trilha dupla**, NÃO é API-only; §5 — passo "o que a vuln NÃO é" obrigatório e política de referência cross-átomo; §6 — didático > realista; §8 — segurança, **bind `127.0.0.1` e ISOLAMENTO entre átomos**, crítico aqui por causa do multi-container **e do IP link-local**; §10.5 — leitura de referência; e a seção "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), `ROADMAP.md`, e — como **referência viva e primária** — o **átomo-irmão in-band `ssrf-basic` (04) INTEIRO** e o **irmão recém-publicado `ssrf-blind-oob` (16) INTEIRO** (README, WALKTHROUGH, DIFF, os diretórios `vulnerable/`/`fixed/`/`internal/`|`oob-listener/`, e principalmente os `docker-compose.yml`). O `sqli-union-basic` (01) é o molde canônico de HTML/Jinja2 mínimo e de WALKTHROUGH; o `atom-16-ssrf-blind-oob.md` é o **formato de spec mais recente** (este documento o segue).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, `metadata-mock/`, README, WALKTHROUGH, DIFF, templates, `docker-compose.yml` — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`/Makefile/`atom`).

---

## Nota de planning 1 — posição na Fase 4: 17 é o 2º átomo e FECHA o arco A10 (confirmado; sem discrepância)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A Fase 4 ("Server-side Avançado", `v0.4.0`) tem **cinco** átomos — `16 ssrf-blind-oob` (`[x]` em `main`), **`17 ssrf-cloud-metadata`** (`[ ]`, ESTE), `18`, `19`, `20`. O **16 abriu a fase**; o **17 é o segundo** e **NÃO fecha a fase** (o **20** fecha). Os átomos 01–16 já estão `[x]`.
>
> **Terceiro átomo A10 do repo — e o ÚLTIMO.** O `ROADMAP.md` lista `ssrf-cloud-metadata` sob "A10 SSRF", com a justificativa *"mostra o impacto real de SSRF em AWS/GCP/Azure (metadata endpoint). Altíssimo valor em pentest cloud."* A pasta `atoms/A10-ssrf/` **já existe** (criada pelo `ssrf-basic` na Fase 1) e já contém `ssrf-basic/` e `ssrf-blind-oob/`. O 17 mora em `atoms/A10-ssrf/ssrf-cloud-metadata/`, **ao lado** dos dois. **Depois do 17 não há mais A10 no roadmap** — o 17 **fecha o arco de SSRF**. Consequência direta na política de foreshadow: **NÃO há "próximo átomo A10" pra antecipar** (ver "Contraste com o arco / escopo / FORESHADOW").

## Nota de planning 2 — versionamento/release fica FORA desta spec

> O 17 **não fecha** a Fase 4 (o 20 fecha), então **não dispara** release. Versionamento/CHANGELOG/tag/anúncio é **trabalho de release do mantenedor**, não de átomo — não entra nesta spec nem no conteúdo do átomo (`CLAUDE.md` §10.4). A única pegada de changelog é uma **linha em `[Unreleased] / Added`** na Fase 2 (ver "Notas específicas pro Claude Code"). O átomo se descreve como "átomo 17, o que fecha o arco de SSRF", **sem** anunciar release nem foreshadowar a fase/os átomos seguintes.

---

## Identidade

- **ID:** `ssrf-cloud-metadata`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A10 — Server-Side Request Forgery (SSRF)**. Pasta `atoms/A10-ssrf/` (**já existe**). Confirmado contra o `ROADMAP.md` ("A10 SSRF"). **Terceiro átomo desta categoria no repo, e o último do roadmap.** Em prosa (README/DIFF) usar o nome completo — **"Server-Side Request Forgery (SSRF)"** — como o 04/16 já fazem.
- **Pasta:** `atoms/A10-ssrf/ssrf-cloud-metadata/`
- **Número sequencial:** 17
- **Porta vulnerable:** `127.0.0.1:8017`
- **Porta fixed:** `127.0.0.1:8117`
- **Mock de metadata (`metadata-mock`):** **INTERNO-ONLY, SEM porta no host** (só alcançável pela rede do compose). **Só `8017` e `8117` ficam expostas.** (Ver "Wiring do link-local" e "O container".)
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` para `vulnerable` e `fixed` (`CLAUDE.md` §8.1). Containers rodam com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos 01–16 e, na parte multi-container, **idêntico ao 04/16**.
- **Fase / milestone:** Fase 4, `v0.4.0`. **Segundo átomo da Fase 4; NÃO fecha a fase.** Versionamento/release **fora desta spec** (Nota de planning 2).
- **Branch de trabalho:** `atom/ssrf-cloud-metadata`. Convenção `atom/<id>` (`CLAUDE.md` §6). **Branch já criada nesta fase de planning.**
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página **conceitual de SSRF** na PortSwigger Web Security Academy. **NÃO inventar URL.** Candidato primário: a página **geral de SSRF** (a mesma do 04, `https://portswigger.net/web-security/ssrf`, framing "what is SSRF?"), porque o conteúdo de **SSRF contra cloud metadata** vive **dentro** dessa página (seção de ataques comuns / metadata `169.254.169.254`) — **não** há uma página conceitual separada só de "cloud metadata SSRF" na Academy (o 16 pôde usar `/ssrf/blind` porque *blind* tem página própria; *cloud metadata* não tem). **Confirmar por fetch na Fase 2** qual seção/âncora é a mais específica; se surgir uma página dedicada com framing "what is X?", preferi-la; senão, a geral. **Secundário (opcional):** link pra **doc oficial do AWS IMDS** (candidato a confirmar por fetch, ex. a página "Instance metadata and user data" / "Use IMDSv2" no docs.aws.amazon.com — **não inventar a URL exata**). Ver seção "Theory primer".
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7):** candidato `# ssrf-cloud-metadata — Cloud metadata SSRF (IAM credential theft)` — segue o padrão dos irmãos (`id` + nome canônico da vuln em inglês; ex. `ssrf-basic — Server-Side Request Forgery (basic)`, `ssrf-blind-oob — Blind SSRF (out-of-band)`). Texto exato / qualificador confirmável na Fase 2; **preservar o nome em inglês também no README PT**.

---

## Classe de vulnerabilidade

**SSRF contra o endpoint de metadata da cloud (in-band).** Uma app web com uma feature que **busca uma URL fornecida pelo usuário e MOSTRA o corpo da resposta** de volta (in-band — o mesmo *flavor* do `ssrf-basic`). Como o servidor **não valida o destino**, a mesma feature que busca uma URL legítima também pode ser apontada pro **IMDS** (Instance Metadata Service) da cloud, em **`169.254.169.254`** — um endpoint **link-local, não-autenticado, presente em toda instância AWS/GCP/Azure** — cuja resposta contém as **credenciais IAM de sessão da instância**. A app busca essa URL e **ecoa a resposta**, entregando as credenciais direto pro atacante.

### A lição-coração

> **"Um SSRF que alcança o endpoint de metadata da cloud (o IMDS, em `169.254.169.254`) devolve as CREDENCIAIS IAM da instância — e quem tem essas credenciais assume o papel da instância na conta cloud. O mesmo primitivo de SSRF dos átomos anteriores, apontado pro alvo de maior valor que existe em toda VM de cloud. O fix é validar o destino (allowlist deny-by-default) antes do fetch."**

**O mecanismo (o que torna real — cravar no WALKTHROUGH e no DIFF).** `169.254.169.254` é um IP **link-local**, **não-autenticado**, presente em **toda** instância AWS/GCP/Azure. Um `GET` simples em `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` devolve `AccessKeyId`, `SecretAccessKey` e `Token` de sessão — **sem senha, sem auth**. Um SSRF que faz a app buscar essa URL e **ecoar a resposta** entrega as credenciais direto pro atacante. Não é preciso um exploit sofisticado: é um `GET` num IP fixo que **toda** VM de cloud atende.

**Sub-lição (cravar):** o que muda do 04 pro 17 **NÃO é o mecanismo** — os dois são in-band, buscam e mostram. **É o ALVO e o IMPACTO.** O 04 lia um serviço interno **genérico** (dashboard com API keys fake); o 17 lê o **crown-jewel** (IMDS → credencial IAM viva). A lição é o **alvo específico e ubíquo**, não uma técnica nova. Todo pentester de cloud aponta o SSRF pro `169.254.169.254` **primeiro**, porque é o alvo de maior valor e está sempre lá.

### DISTINÇÃO CENTRAL — o arco A10 em três beats (04 → 16 → 17)

Cravar no WALKTHROUGH (abertura) e no DIFF. **Os três compartilham o MESMO primitivo** (o servidor faz uma requisição outbound pra um destino que o atacante escolhe); mudam o **canal de leitura** e o **alvo/impacto**:

| | **04 `ssrf-basic` (IN-BAND, genérico)** | **16 `ssrf-blind-oob` (BLIND, detecção)** | **17 `ssrf-cloud-metadata` (IN-BAND, crown-jewel) — ESTE** |
|---|---|---|---|
| O servidor busca a URL do atacante? | **sim** | **sim** | **sim** (mesmo primitivo) |
| O servidor devolve o conteúdo buscado? | **sim** — body reflete o recurso | **não** — resposta genérica, sem eco | **sim** — body reflete o recurso (volta ao in-band do 04) |
| Canal de detecção | **ler o body** (in-band) | **interação out-of-band** (callback) | **ler o body** (in-band) |
| Alvo demonstrado | serviço interno **genérico** (`internal`) | **tripwire** (`oob-listener`, sem prêmio) | **IMDS** (`169.254.169.254`) — o **crown-jewel** |
| Impacto | leitura de dado interno | **detecção** da primitiva | **roubo de credencial IAM → account takeover** |
| Prova do exploit | "li o dashboard interno" | "fiz o servidor sair pra fora e capturei o hit" | **"li as credenciais IAM da instância no corpo da resposta"** |

**A frase-regra do arco:** *o primitivo é o mesmo nos três; o 04 ensinou a LER a resposta, o 16 ensinou a DETECTAR sem ela, e o 17 aponta o primitivo pro ALVO que paga — o IMDS.* O 17 é o **pagamento** do arco: é o átomo onde a escalada que o 16 deliberadamente **não** cobriu (alcançar metadata de cloud e roubar credencial) finalmente **acontece**.

### Contraste com o arco (eixo A10 — continuidade e fechamento, NÃO mudança)

- **Volta ao modelo IN-BAND do 04** (a app busca e MOSTRA a resposta). A escalada sobre o 04 **NÃO** é a visibilidade (ambos são in-band) — é o **ALVO** (IMDS) e o **IMPACTO** (credencial IAM).
- **Contraste com o 16** (blind): o 16 removia o eco e forçava detecção OOB; o 17 **tem** o eco (é como o aluno **LÊ** as credenciais). O 16 era **byte-idêntico** entre vulnerable e fixed **porque cego**; o 17 dá **recusa VISÍVEL** (`abort(403)`) no fixed **como o 04, porque in-band** (ver "O fix e o tipo de diff").
- **Referenciar 04 E 16 à vontade** (AMBOS PUBLICADOS, `CLAUDE.md` §5) — o 17 é o pagamento do arco que os dois montaram.

### Por que A10 (SSRF)

SSRF contra cloud metadata é **SSRF** — a superfície é idêntica à do 04 (o servidor faz uma requisição outbound pra um destino que o atacante controla e devolve o corpo). O que muda é **só o alvo** (`169.254.169.254`, o IMDS) e o **valor do que se lê** (credencial IAM). Coerente com o eixo server-side da Fase 4 e o **fechamento** do arco A10.

---

## Uma vuln só — o eco é ESCAPADO, o fix é allowlist CORRETA, o mock tem creds FALSAS internal-only

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o servidor **fazer o fetch outbound SEM validar o destino**. Garantias (todas validar na Fase 2):

- **O CORPO BUSCADO É ECOADO COM ESCAPE (moldura travada — não pode virar 2ª vuln).** A app **MOSTRA** o corpo buscado (in-band, é o ponto — é como se lê as credenciais), mas **SEMPRE escapado** (autoescape do Jinja LIGADO, num `<pre>`), **espelhando como o 04 renderiza** (`preview.html`). Mostrar conteúdo buscado **NÃO** pode virar XSS/HTML-injection. O DIFF **deve** notar: *"o eco é escapado de propósito; a vuln é o SSRF, não como o corpo é exibido."*
- **O fix é uma allowlist CORRETA (deny-by-default), NÃO um blocklist de link-local bypassável.** Este é o ponto mais fácil de estragar. A validação decide sobre o **host parseado** (`urlparse(...).hostname`), **não** por match de substring, e é **positiva** (deny-by-default). Bloquear **só** `169.254.0.0/16` é blocklist — contornável (IP decimal/hex, `[::ffff:...]`, redirect `302`→IMDS, DNS rebinding, userinfo) — e o **DIFF do 16 já argumentou que blocklist vaza**. A vuln DESTE átomo é a **AUSÊNCIA de validação de destino**; o fix, quando presente, é **robusto**. Cravar.
- **O mock tem credenciais OBVIAMENTE FALSAS e é interno-only.** Usa os valores **EXAMPLE documentados pela AWS** (`ASIAIOSFODNN7EXAMPLE`, `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`, Token dummy). **Nenhum segredo real** (`CLAUDE.md` §8.3/§8.4). É **interno-only** (sem porta no host); alcançável só pela rede do compose.
- **O fetch TEM timeout** (`timeout=5`, como o 04/16) → **sem** unbounded-consumption/DoS como segunda falha.
- **Sem banco, sem segunda superfície:** nenhum SQLite/sessão/credencial de app; nenhum PII real; a única peça extra é o `metadata-mock`. A **única** superfície é o fetch outbound sem validação de destino.

---

## A decisão estrutural — MOCK NO IP REAL `169.254.169.254` (a "Saída B" do 17): por quê (TRAVADA)

**O ponto que faz o átomo existir** — da **mesma família honesta** das "Saídas B" do 14 (PyJWT mitiga → verify hand-rolled), do 15 (`flask.session` resiste → sessão manual) e do 16 (Collaborator externo indisponível → listener embarcado). Aqui é uma **ruga de INFRA** (endereçamento de rede), não de biblioteca:

**O `metadata-mock` responde no IP REAL `169.254.169.254`.** Motivo — é o **coração da lição**:

1. **O payload que o aluno digita é IDÊNTICO ao de um alvo AWS real** — `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>`. Sem stand-in, sem "imagine que este IP é o metadata": é *o* IP.
2. **Torna o fix HONESTO.** A defesa real de SSRF-contra-metadata é **barrar o link-local** (via allowlist deny-by-default). Com o mock **no IP real**, o fixed barrando `169.254.169.254` é a **defesa de verdade** operando sobre o **alvo de verdade** — não uma encenação sobre um IP inventado.

**SAÍDA B (contingência de infra, deixar EXPLÍCITA aqui):** se o Docker **não** fixar o link-local limpo na geração (subnet `169.254.169.0/24` + `ipv4_address` estático), cai pra um **alias** — o **nome de serviço `metadata-mock`** (via DNS do Docker, **exatamente como o 04/16 endereçam o serviço extra**) ou, se o mantenedor preferir manter a memória-muscular de "digitar um IP", um **IP privado estático** (ex.: `172.31.0.254`, que evoca a default VPC da AWS) — **COM NOTA HONESTA** no README/WALKTHROUGH de que é um **stand-in do IMDS real** (`http://169.254.169.254/...` no mundo real), com o mapeamento explícito. **Mesmo movimento do listener embarcado do 16.** Detalhe operacional da Saída B em "Wiring do link-local".

**O mock nas DUAS "pontas" (alcançável do `vulnerable` E do `fixed`), espelhando a intenção do 04/16:** assim a **ausência de credencial no fixed** é atribuível ao **CÓDIGO** (a allowlist barra a requisição **antes** de sair), **não à rede** (mock inalcançável). Ver "Wiring do link-local" pro detalhe de como isso é feito com um IP fixo (que difere estruturalmente do 04/16 — é o item sinalizado).

---

## Decisões de infra JÁ TRAVADAS — implemente conforme, NÃO reabra

1. **IN-BAND, NÃO CEGO (estrutural — NÃO herdar do 16).** O 17 é **in-band**: a app busca a URL e **MOSTRA** o corpo. A resposta do `vulnerable` **ECOA** o conteúdo buscado (as creds do IMDS aparecem no response). O `fixed` dá **RECUSA VISÍVEL** (`abort(403)`), **espelhando o 04**. **NÃO é byte-idêntica** — a decisão de resposta byte-idêntica foi **EXCLUSIVA do 16** (que era cego); aqui **não se aplica**. Cravar no DIFF.
2. **MOCK NO IP REAL `169.254.169.254`** (Saída A), com **Saída B** = alias/IP-privado + nota honesta (acima).
3. **MOCK INTERNO-ONLY:** alcançável **APENAS** pela rede do compose (do `vulnerable` e do `fixed`). **NÃO expõe porta no host** (`CLAUDE.md` §8: só `8017`/`8117` bindados em `127.0.0.1`).
4. **App: Flask + `requests`; Mock: Flask (serve JSON estático do IMDS).** **NENHUMA** dependência de cloud/AWS SDK — o mock é um Flask local servindo JSON. Fix: `urllib.parse.urlparse` + o estilo do 04.

---

## WIRING DO LINK-LOCAL — **DECISÃO SINALIZADA** (o único item não pré-travado)

> Depois de ler os `docker-compose.yml` e os diretórios `internal/` (04) e `oob-listener/` (16), defino o wiring abaixo. **Este é o único item que o prompt me pediu pra DECIDIR e SINALIZAR** — porque o IP link-local fixo é estruturalmente diferente do que o 04/16 fizeram, e a escolha precisa ficar visível pra revisão conjunta.

### A diferença estrutural (por que o 17 NÃO copia o wiring do 04/16 ao pé da letra)

No **04 e no 16, o serviço extra é alcançado por NOME DNS** (`internal`, `oob-listener`). Por isso a topologia deles funciona com **duas redes separadas** (`lab-vulnerable` e `lab-fixed`), cada uma com sua subnet, e o serviço extra ganha um **IP diferente em cada rede** — o **nome** resolve certo em ambas. O serviço nas duas redes dá: (a) isolamento `vulnerable`↔`fixed`; (b) a construção honesta do contraste (o serviço é alcançável das duas pontas → ausência de resultado no fixed é atribuível ao CÓDIGO).

**O 17 precisa alcançar o mock por um IP FIXO** — `169.254.169.254` — porque *o IP idêntico ao real é a lição*. Um único `/32` **só pode viver numa subnet**, e o **IPAM default do Docker recusa subnets sobrepostas entre redes** (erro `Pool overlaps with other one on this address space`). Logo **não dá** pra ter `169.254.169.254` em `lab-vulnerable` **e** em `lab-fixed` (seriam duas redes contendo o mesmo `/32` → sobreposição proibida). **Consequência:** pra `vulnerable` **e** `fixed` alcançarem o **mesmo IP fixo**, os dois têm que compartilhar **uma** rede que seja dona da subnet link-local.

### WIRING — o que vou tentar (Saída A) e a Saída B

> **WIRING (Saída A) — o que escolhi e por quê:**
> - **(a) Uma única rede compartilhada** (`lab`), com `ipam.config.subnet: 169.254.169.0/24` (um `/24` basta e colide menos com o link-local do host que o `/16` inteiro). O **`metadata-mock`** recebe **`ipv4_address: 169.254.169.254`** (estático). `vulnerable` e `fixed` **também** entram nessa rede (IP dinâmico), e é por ela que alcançam `169.254.169.254`.
> - **(b) Nome do serviço/container e diretório:** **`metadata-mock`** (descritivo; deixa claro que é um mock do IMDS). Diretório **`metadata-mock/`** — espelha o `internal/` (04) e o `oob-listener/` (16): nome-do-diretório == nome-do-serviço, com `app.py`, `Dockerfile`, `requirements.txt`, **sem** `templates/`.
> - **(c) Porta interna:** **80** — espelha `internal/` (04) e `oob-listener/` (16) (`app.run(..., port=80)`, `EXPOSE 80`). Assim o payload não carrega porta explícita (`http://169.254.169.254/...`, porta 80 implícita) — exatamente como o IMDS real (que atende em HTTP:80).
> - **(d) Host ports:** só `vulnerable` (`127.0.0.1:8017:5000`) e `fixed` (`127.0.0.1:8117:5000`) publicam. **`metadata-mock` NÃO publica porta** (interno-only).
>
> **POR QUE uma rede só (a divergência do 04/16, e por que ela é OK):** a propriedade **que carrega a lição está PRESERVADA** — o mock em `169.254.169.254` é alcançável **das duas pontas** (`vulnerable` **e** `fixed`) no nível de rede, então a **recusa do fixed (`403`) é atribuível ao CÓDIGO** (a allowlist barra a requisição antes de sair), **não à rede**. É **literalmente a nota do 04**: *"the internal container is still reachable from the fixed container at the network layer — the fix is in the application code, not in the network plumbing."* O **único** byproduct perdido vs 04/16 é a **não-adjacência L3 entre `vulnerable` e `fixed`** (eles passam a se enxergar na rede compartilhada) — e isso **NÃO carrega lição nenhuma**: nenhum dos dois inicia tráfego pro outro; o aluno só os alcança pelas portas do host. **Registrar essa divergência (e por que é inócua) no DIFF/README.**
>
> **SAÍDA B — se o link-local não fixar limpo na Fase 2** (Docker recusa subnet `169.254.x` no driver bridge da máquina; conflito com rota link-local/APIPA do host; roteamento estranho): endereçar o mock pelo **nome DNS de serviço `metadata-mock`** numa subnet privada normal (**exatamente como o 04/16 endereçam o serviço extra** — é o padrão já cravado do arco), voltando à **topologia de DUAS redes** do 04/16 (`vulnerable`→`lab-vulnerable`, `fixed`→`lab-fixed`, `metadata-mock`→ambas). Payload vira `http://metadata-mock/latest/meta-data/...` **COM NOTA HONESTA** mapeando pro real `http://169.254.169.254/...`. *Sub-alternativa* (se o mantenedor quiser manter "digitar um IP"): IP **privado estático** (ex. `172.31.0.254`) com a mesma nota. **Recomendo o nome de serviço** na Saída B (robusto, e reconstitui a topologia de duas redes idêntica ao 04/16). Marcar a Saída B como **plano de contingência explícito** no README/WALKTHROUGH se acionada.

### Esboço do `docker-compose.yml` (Saída A — candidato; a Fase 2 gera o real; **NÃO gerar agora**)

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8017:5000"
    networks:
      - lab
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8117:5000"
    networks:
      - lab
  metadata-mock:
    build: ./metadata-mock
    networks:
      lab:
        ipv4_address: 169.254.169.254

networks:
  lab:
    ipam:
      config:
        - subnet: 169.254.169.0/24
```

> **Esboço do `docker-compose.yml` (Saída B — só se a A não fixar):** volta ao molde de duas redes do 16 — `vulnerable`→`lab-vulnerable`, `fixed`→`lab-fixed`, `metadata-mock`→ambas, **sem** `ipam`/`ipv4_address`, alcançado pelo nome `metadata-mock`. Idêntico em forma ao `docker-compose.yml` do `ssrf-blind-oob`, trocando `oob-listener` por `metadata-mock`.

**ISOLAMENTO entre átomos (`CLAUDE.md` §8) — nota da Saída A:** o Compose namespaceia a rede por projeto (`ssrf-cloud-metadata_lab`), então não colide com redes de outros átomos. A **subnet `169.254.169.0/24`** é um pool a nível de host: como os átomos rodam **um de cada vez** (`./atom up <id>`) e **nenhum outro átomo usa link-local**, não há conflito. Se o **host** já usar `169.254.0.0/16` (APIPA/link-local numa interface), pode haver conflito de rota — **este é exatamente um gatilho da Saída B**; validar na Fase 2.

---

## Feature e endpoints — app web in-band (TEM HTML, molde do 04)

Uma app web mínima que **busca uma URL fornecida e MOSTRA o resultado** — o *flavor* do 04 (`URL preview` / `fetch a resource` / `import from URL`). Pra **diferenciar** do 04 (que é literalmente "URL Preview") mantendo o mesmo mecanismo in-band, o flavor candidato é **"Fetch from URL" / "Resource fetcher"** (uma ferramentinha server-side que busca uma URL e exibe o corpo). Molde de render **confirmado contra o 04** (tem `templates/`, trilha dupla). HTML **mínimo** (`CLAUDE.md` §3.3: banner de aviso, form com campo de URL, dica de Burp, ≤40 linhas/template, sem frameworks, sem JS).

- **`GET /`** — serve o form (campo de URL). Banner de aviso, dica de Burp. Renderiza `templates/index.html`.
- **`POST /fetch`** — o servidor faz um `GET` na URL fornecida (`request.form["url"]`) e **RETORNA O CORPO** da resposta, renderizado num `<pre>` **escapado** (`templates/result.html`).
  - **VULNERABLE:** busca **SEM validar** o destino e **ecoa o body** (as creds do IMDS voltam aqui).
  - **FIXED:** **valida o destino** (allowlist deny-by-default) **ANTES**; destino não vetado → **`abort(403)`** visível (como o 04).

> **DECISÃO SINALIZADA — método e nome do endpoint.** O prompt travou **`POST /fetch`** (via `request.form["url"]`, conforme o esboço de código). Sinalizo a nuance de arco pra transparência: o **04 usa `GET /fetch?url=`** (preview idempotente), o **16 usa `POST /ping`**. O 17 usa **`POST /fetch`** — o **método POST espelha o 16**, e o **nome `/fetch` + o comportamento in-band (busca-e-mostra) espelham o 04**. O método pelo qual o **aluno fala com a app** (`POST /fetch`) é **independente** do método que a **app usa pra alcançar o IMDS** (sempre um `GET`, via `requests.get`) — então POST `/fetch` **não** compromete o realismo do "GET no IMDS". Uso `POST /fetch` no resto desta spec, fiel ao esboço travado. *(Se o mantenedor preferir o paralelo literal com o `GET /fetch?url=` do 04, a Fase 2 pode trocar — mas o prompt escreveu POST/`request.form` explicitamente; sigo isso.)*

---

## O corpo buscado é ECOADO com ESCAPE (moldura — "um átomo = uma vuln")

A app **MOSTRA** o corpo buscado (in-band, é o ponto — é como o aluno lê as credenciais), mas **SEMPRE escapado** (autoescape do Jinja, num `<pre>`), **espelhando como o 04 renderiza** (`preview.html`). Mostrar conteúdo buscado **NÃO** pode virar uma segunda vuln (XSS/HTML-injection). O `result.html` do 17 é o **gêmeo** do `preview.html` do 04: URL ecoada num `<code>` (escapada) e corpo num `<pre>` (escapado); `status` opcional. **Sem `|safe`, sem `Markup`, sem `render_template_string`.** O DIFF nota: *"o eco é escapado de propósito; a vuln é o SSRF, não como o corpo é exibido."*

---

## O código — o coração no fetch

Imports (vulnerable):

```python
import os
import requests
from flask import Flask, request, render_template
```

### `vulnerable/app.py` — busca sem validar, ecoa o corpo (candidato — Fase 2 gera o real)

```python
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/fetch", methods=["POST"])
def fetch():
    url = request.form.get("url", "")
    # VULNERABLE: fetch an attacker-controlled URL and return the response body verbatim.
    # No destination validation: the server reaches ANY host its network sees -- including the
    # cloud metadata endpoint (169.254.169.254), whose IAM credentials come straight back in
    # the response. SSRF weaponized for credential theft.
    try:
        r = requests.get(url, timeout=5)
        body, status = r.text, r.status_code
    except requests.RequestException as exc:
        body, status = f"Request error: {exc}", None
    return render_template("result.html", url=url, body=body, status=status)  # autoescaped in a <pre>


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `fixed/app.py` — valida o destino antes, recusa VISÍVEL (candidato — Fase 2 gera o real)

```python
import os
from urllib.parse import urlparse
import requests
from flask import Flask, request, render_template, abort

app = Flask(__name__)

# Deny-by-default allowlist of vetted destinations, matched on the PARSED host (not a substring
# of the raw URL). 169.254.169.254 (and anything not explicitly vetted) is never requested, so
# the metadata endpoint is unreachable through this feature.
ALLOWED_HOSTS = {"api.github.com"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/fetch", methods=["POST"])
def fetch():
    url = request.form.get("url", "")
    # FIXED: validate the destination against a deny-by-default allowlist BEFORE fetching.
    # Same SSRF defense family as ssrf-basic (04) and ssrf-blind-oob (16); the host is the
    # load-bearing check. http is allowed as a scheme on purpose -- so the refusal is
    # attributable to the HOST allowlist alone, not to a scheme filter (the metadata endpoint
    # is http, and "we blocked http" would be the wrong lesson).
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        abort(403)  # in-band visible refusal, like ssrf-basic (04) -- this atom is NOT blind
    try:
        r = requests.get(url, timeout=5)
        body, status = r.text, r.status_code
    except requests.RequestException as exc:
        body, status = f"Request error: {exc}", None
    return render_template("result.html", url=url, body=body, status=status)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

### `metadata-mock/app.py` — fake IMDS (IMDSv1-style GET), creds FALSAS (candidato — Fase 2 gera o real)

```python
import os
from flask import Flask, Response, jsonify

app = Flask(__name__)

# Fake IMDS. Serves the minimal surface an SSRF attacker walks: the role name, then the
# credentials JSON. Credentials are the AWS-documented EXAMPLE values -- OBVIOUSLY FAKE, no
# real secret. IMDSv1-style (plain GET, no PUT token) ON PURPOSE: that reachability is what
# the SSRF exploits, and IMDSv2 is the "mentionable, not applied" hardening (see DIFF).
ROLE = "app-instance-role"

CREDS = {
    "Code": "Success",
    "LastUpdated": "2026-07-23T00:00:00Z",
    "Type": "AWS-HMAC",
    "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",              # ASIA... == temporary/STS creds (what IMDS returns)
    "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "Token": "IQoJb3JpZ2luX2VjEXAMPLEtokenEXAMPLEtokenEXAMPLEtokenEXAMPLE=",
    "Expiration": "2026-07-23T06:00:00Z",
}


@app.route("/latest/meta-data/iam/security-credentials/")
def role_list():
    return Response(ROLE + "\n", mimetype="text/plain")  # the attacker learns the role name


@app.route("/latest/meta-data/iam/security-credentials/<role>")
def role_creds(role):
    if role != ROLE:
        return Response("", status=404)
    return jsonify(CREDS)  # AccessKeyId / SecretAccessKey / Token -- the loot


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=80)
```

**Notas de implementação (validar na Fase 2):**

- **Alinhamento com o 04:** o estilo do fixed (parse com `urlparse`, checar `scheme`/`hostname` contra allowlist positiva deny-by-default, `abort(403)`) é **o mesmo do `ssrf-basic/fixed/app.py`** — a defesa **generaliza pelo arco**. O 17 **espelha os dois**: o parse-then-check E a recusa `abort(403)`.
- **`scheme not in ("http", "https")` (permite os dois) — divergência DELIBERADA e sinalizada do 04** (que é `!= "https"`, https-only). Razão pedagógica: o IMDS é **http**. Se o gate fosse https-only, `http://169.254.169.254/...` bateria no check de scheme **antes** do de host, e o aluno poderia concluir errado *"bloquear http foi o fix"*. Permitindo `http` como scheme e recusando **puramente pelo HOST**, a lição fica inequívoca: **o host é o check load-bearing** (ecoa o framing do 16). Registrar no DIFF.
- **`ALLOWED_HOSTS` (candidato `{"api.github.com"}`):** host externo benigno, continuidade com o 04 (que já vetava `api.github.com`). Mostra que a lista é **positiva** (permite o vetado, barra o resto — inclusive o IMDS). **Nota de egress:** a prova **central** (payload do IMDS → `403` no fixed) é **hermética** (o mock é interno, sem egress). Demonstrar um fetch **bem-sucedido** de host vetado no fixed é **opcional** e depende de **egress de internet** (como o 04, que buscava `api.github.com`); o WALKTHROUGH deixa isso opcional. A Fase 2 pode ajustar o host vetado.
- **Eco escapado:** `result.html` renderiza `body` num `<pre>` com autoescape — **sem** `|safe`/`Markup`/`render_template_string`. Sem XSS.
- **`timeout=5`** (espelha o 04/16): obrigatório pra não empilhar unbounded-consumption/DoS como 2ª vuln.
- **Mock IMDSv1-style (GET simples, sem token PUT) DE PROPÓSITO:** é essa alcançabilidade por `GET` que o SSRF explora. **IMDSv2 (token via PUT + hop-limit) é a nota "mencionável, não aplicada"** do DIFF — **não** se implementa o fluxo IMDSv2 no mock.
- **Superfície mínima e realista do mock:** `/latest/meta-data/iam/security-credentials/` (lista o role) → `.../security-credentials/<role>` (JSON de creds). **Opcional (realismo):** `/latest/meta-data/` com um listing curto (`iam/`, `hostname`, ...). Manter mínimo; o essencial é a cadeia role-listing → creds.
- **Creds = valores EXAMPLE da AWS:** `ASIAIOSFODNN7EXAMPLE` (prefixo **ASIA** = credencial **temporária**/STS, que é o que o IMDS devolve — detalhe de precisão didática, cravar em prosa) + `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (secret EXAMPLE clássico da doc AWS) + Token dummy com "EXAMPLE". **Obviamente falsas** (`CLAUDE.md` §8).

---

## O fix e o tipo de diff

**Fix:** **VALIDAR o destino (allowlist deny-by-default)** antes do fetch — **mesma família de defesa** do 04 e do 16, **generalizando o arco**. Tipo de diff: **lógica-diferente** (código **adicionado** no handler do `/fetch`) — o mesmo TIPO dos A01, dos JWT, do 04 e do 16. Diff no ponto do fetch. **A única mudança é o gate + a recusa `abort(403)`** (o resto — `GET /`, imports comuns, o `render_template("result.html", ...)`, rodapé, templates — é byte-idêntico entre vulnerable e fixed).

Diff colável (candidato — Fase 2 gera o real):

```diff
 import os
+from urllib.parse import urlparse
 import requests
-from flask import Flask, request, render_template
+from flask import Flask, request, render_template, abort

 app = Flask(__name__)

+# Deny-by-default allowlist of vetted destinations, matched on the PARSED host.
+ALLOWED_HOSTS = {"api.github.com"}
+

 @app.route("/")
 def index():
     return render_template("index.html")


 @app.route("/fetch", methods=["POST"])
 def fetch():
     url = request.form.get("url", "")
-    # VULNERABLE: fetch an attacker-controlled URL and return the response body verbatim...
+    # FIXED: validate the destination against a deny-by-default allowlist BEFORE fetching...
+    parsed = urlparse(url)
+    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
+        abort(403)
     try:
         r = requests.get(url, timeout=5)
         body, status = r.text, r.status_code
     except requests.RequestException as exc:
         body, status = f"Request error: {exc}", None
     return render_template("result.html", url=url, body=body, status=status)
```

**O CONTRASTE é o diff (obrigatório):** busca-sem-validar-e-ecoa (vulnerable) vs valida-o-destino-antes-e-recusa-visível (fixed).

### Notas obrigatórias no `DIFF.md`

1. **ALLOWLIST, NÃO BLOCKLIST DE LINK-LOCAL (coerente com o DIFF do 16).** Bloquear só `169.254.0.0/16` é **blocklist** — contornável: IP **decimal** (`http://2852039166/`), **hex** (`http://0xa9fea9fe/`), **IPv6-mapped** (`http://[::ffff:169.254.169.254]/`), **redirect** `302`→IMDS, **DNS rebinding**, **userinfo** (`http://allowed@169.254.169.254/`). O **DIFF do 16 já argumentou que blocklist vaza**; o 17 tem que ser **coerente**. Uma **allowlist deny-by-default** barra **QUALQUER** destino não vetado (link-local incluso) **sem depender de enumerar as evasões**. Explicar **por que a allowlist é a escolha coerente do arco** (o 04 e o 16 já a usam; a defesa generaliza).
2. **IMDSv2 — A NOTA "MENCIONÁVEL, NÃO APLICADA" (forte, obrigatória, NOMEADA).** A indústria endureceu o **próprio IMDS**: o **IMDSv2** exige um **token de sessão obtido via `PUT`** (um SSRF de `GET` simples **não** alcança) e põe **hop-limit=1** na resposta (uma request proxiada pela app — um pulo a mais — é **descartada**). **POR QUE não é o diff deste átomo:** IMDSv2 é **postura do SERVIÇO de metadata (infra)**, **não** um fix no `vulnerable/app.py`; a forma do projeto é **diff no código do app**. Então é **DESCRITO** (é onde o 17 fica real — a defesa em profundidade do lado da cloud), **não aplicado** — mesmo espírito da nota de secret-management do átomo 13, levado a sério. **Nomear "IMDSv2" explicitamente.**
3. **RECUSA VISÍVEL (17) vs BYTE-IDÊNTICA (16).** O **16 era byte-idêntico** entre vulnerable e fixed **porque cego** (revelar o bloqueio pela resposta contradiria "olhe out-of-band"); o **17 dá recusa visível (`abort(403)`) como o 04 porque é in-band** (a resposta dele já carrega informação, então um `403` distinto não estraga lição nenhuma). Mesma família de fix (validar destino), **forma da recusa adaptada ao canal** (in-band → visível).
4. **O ECO É ESCAPADO DE PROPÓSITO.** A app mostra o corpo buscado (in-band, é o ponto), mas via autoescape do Jinja num `<pre>`. *"A vuln é o SSRF, não como o corpo é exibido."* Sem `|safe`/`Markup` → sem XSS empilhado.
5. **O fix é allowlist CORRETA, não blocklist bypassável.** Decide sobre `urlparse(...).hostname` (o host real que o cliente HTTP vai conectar), **não** por match de substring. Tabela de robustez (validar na Fase 2, molde da tabela do DIFF do 16), todas as formas do endereço do IMDS → **host parseado não está na allowlist → `403`**:

   | Payload (contra o fixed) | Host parseado (`urlparse().hostname`) | Resultado |
   |---|---|---|
   | `https://api.github.com/...` | `api.github.com` | **allowed** (o destino vetado) |
   | `http://169.254.169.254/latest/meta-data/...` | `169.254.169.254` | **403** (não vetado — a defesa real) |
   | `http://2852039166/...` (decimal) | `2852039166` | **403** (não vetado) |
   | `http://0xa9fea9fe/...` (hex) | `0xa9fea9fe` | **403** (não vetado) |
   | `http://[::ffff:169.254.169.254]/...` | `::ffff:169.254.169.254` | **403** (não vetado) |
   | `http://api.github.com@169.254.169.254/...` (userinfo) | `169.254.169.254` | **403** (host real é depois do `@`) |

   A linha do **userinfo** é a importante: `api.github.com` aparece na string, então um `if "api.github.com" in url` ingênuo passaria — e deixaria a request chegar no IMDS. Parsear primeiro e comparar `hostname` derruba. **Nota de honestidade sobre REDIRECT (mencionável, não aplicada — como o IMDSv2):** um `GET` do `requests` **segue redirects por default**; um fix gate-only ainda seguiria um `302`→IMDS **se o próprio host vetado emitisse esse redirect**. No lab isso **não é reproduzível** (o host vetado é benigno e não redireciona pro IMDS; um redirector não-vetado é barrado **no gate**, porque o host inicial dele não está na allowlist). O hardening de produção (`allow_redirects=False` / re-validar cada hop) é **descrito, não aplicado** — mantém a **única mudança do diff = o gate + a recusa** (checklist item 13). Registrar em prosa.

---

## Encenação — ATOR ÚNICO (o pentester), a cadeia clássica recon→loot do IMDS

Um ator — o aluno é o atacante/pentester. A cadeia clássica de **recon → loot** do IMDS. O WALKTHROUGH deixa explícito. No Burp (trilha principal):

1. **Provar o SSRF in-band (baseline).** `POST /fetch` numa URL e ver o **corpo voltar** — a feature busca-e-mostra funcionando.
2. **Apontar pro IMDS (recon do role).** `POST /fetch` com `url=http://169.254.169.254/latest/meta-data/iam/security-credentials/` → volta o **nome do role** (`app-instance-role`).
3. **Loot.** `POST /fetch` com `url=http://169.254.169.254/latest/meta-data/iam/security-credentials/app-instance-role` → volta o **JSON com `AccessKeyId`/`SecretAccessKey`/`Token`**. **Credencial IAM exfiltrada via SSRF.**
4. **Contra o FIXED (`8117`).** Mesma cadeia → **`abort(403)` visível**, **sem creds**.

**PROVA-CHAVE (cravar, mostrar explicitamente):** no **vulnerable**, as **credenciais IAM aparecem no corpo da resposta**; no **fixed**, a **mesma request é recusada (`403`)** e **nada volta**. A diferença observável é o corpo (creds vs `403`) — porque é **in-band** (contraste com o 16, onde a prova era o hit no log).

---

## A trilha — Burp principal + browser secundária (trilha dupla, `CLAUDE.md` §3.3)

O 17 **está no molde HTML de trilha dupla** (04/16 já eram; espelhar). O Burp é a trilha **principal** — é onde o pentester **planta e manipula** o payload cru (controle da URL, do encoding, do método no Repeater), a parte que ensina a profissão; a **prova** é o corpo da resposta (as creds), que o par Burp entrega direto (in-band, sem precisar de JS no browser → **não** é a exceção-XSS do §3.3).

- **Trilha principal — Burp (Repeater).** Cada request é um bloco colável. O aluno controla o `POST /fetch` no Repeater e **lê as credenciais no corpo** da resposta.
- **Trilha secundária — browser (opcional, baixa fricção).** Abrir `/`, submeter o form uma vez com a URL do IMDS, ver as creds renderizadas no `<pre>`. Mesmo papel: primeira experiência sem atrito. **Sem JS.**

---

## Walkthrough — estrutura e beats

Trilha principal **Burp**, secundária **browser**. Ids/hosts/creds são placeholders da execução real capturada na Fase 2. Estrutura de beats (molde do 04, com o alvo IMDS e o impacto de credencial explícitos):

> **Abertura — plantar a lição.** Tease: *no `ssrf-basic` você apontava o servidor pra um serviço interno e lia um dashboard. Mesmo primitivo aqui — só que você vai apontar pro alvo que existe em TODA VM de cloud e que paga mais que qualquer dashboard: o endpoint de metadata, `169.254.169.254`. Um `GET` sem auth lá devolve as credenciais IAM da instância. Você vai fazer a app buscar essa URL, ler as credenciais no corpo da resposta, e com elas assumir o papel da instância na conta cloud.*

1. **Context.** App web "fetch from URL": `GET /` (form de URL), `POST /fetch` (o servidor busca a URL e **mostra** o corpo). Isto é **A10 — SSRF** apontado pro **cloud metadata endpoint**. **Um ator: você, o pentester.** Trilha: Burp (principal) + browser (secundária).
2. **About this lab's environment.** O terceiro container, **`metadata-mock`**: um **fake IMDS** respondendo em **`169.254.169.254`** (Saída A) — **o IP real do metadata em AWS/GCP/Azure** —, interno-only (sem porta no host), com credenciais **obviamente falsas** (valores EXAMPLE da AWS). Explicar que num pentest real esse IP é o IMDS da instância; aqui é um mock local. **Se a Saída B estiver ativa:** a **NOTA HONESTA** de que o mock está num alias/IP-privado como stand-in do `169.254.169.254` real.
3. **Spot the bug.** Mostrar `vulnerable/app.py` — o `POST /fetch`. `request.form["url"]` flui direto pra `requests.get(url, ...)` e o body é ecoado, sem parsing, sem allowlist, sem checagem de destino. **Igual ao 04 nesse ponto.** Pergunta de auditoria: *"o servidor busca um destino que EU escolho e me devolve o corpo?"* → **sim**. Foreshadow do fix: **validar o destino (allowlist)**.
4. **The attack — recon → loot (o núcleo — VALIDAR RODANDO).** Três passos:
   - **4a — baseline in-band:** `POST /fetch` numa URL → o corpo volta (a feature funciona, in-band).
   - **4b — recon do role:** `url=http://169.254.169.254/latest/meta-data/iam/security-credentials/` → o **nome do role** volta no corpo.
   - **4c — loot:** `url=http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` → o **JSON de credenciais** (`AccessKeyId`/`SecretAccessKey`/`Token`) volta no corpo. **Credencial IAM roubada via SSRF.** Explicar em prosa que o prefixo `ASIA...` denota credencial **temporária** (STS) e que, num alvo real, essas credenciais seriam usadas com o AWS CLI/SDK (`aws sts get-caller-identity`, etc.) pra assumir o papel da instância — **sem** transformar isso em passo executável do átomo (o finding é o **roubo via SSRF**; usar a credencial é pós-exploração, fora de escopo `CLAUDE.md` §12).
5. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos:
   - **NÃO é "o IMDS/AWS está mal configurado".** O `169.254.169.254` é **link-local, não-autenticado e presente por design** em toda VM de cloud — é **assim que a identidade da instância funciona**, não uma misconfiguration. O **bug é 100% da app** que busca qualquer URL. (Este é o contraste-chave — o aluno não pode sair achando que "a AWS expõe o metadata" é a falha.)
   - **NÃO é RCE no servidor da app.** O finding é **roubo de credencial via SSRF** — não execução de código no servidor da app. (As creds podem levar a mais **na conta cloud**, mas isso é escalada com a credencial, não RCE na app.)
   - **NÃO é "você autenticou como o atacante".** As credenciais são **da instância** (o role IAM); você as obtém porque **o servidor** carregou a request pro IMDS por você (ecoa o ponto "Identity" do 04). Você herda a identidade da instância, não cria uma.
   - **O que É (prova):** o servidor busca um destino **que você escolhe** (`http://169.254.169.254/...`) e **te devolve o corpo** com a credencial. A **única** correção é **validar o destino** (a fixed: allowlist deny-by-default → `403`) — **não** confiar que "ninguém vai apontar pro metadata", nem blocklistar só o link-local.
6. **Impact (honesto — sem overclaim).** **Roubo de credencial IAM → account takeover na cloud:** o atacante lê credenciais de sessão vivas do IMDS via SSRF e **assume o papel da instância** (faz o que o role permitir na conta). É **um dos SSRF de maior impacto do mundo real**. Âncora factual **opcional** no README: o **breach da Capital One em 2019** (SSRF → IMDS → credenciais → dados em S3). **NÃO é RCE no servidor da app** em si. Sem overclaim.
7. **Why the fix works (porta 8117).** Repetir a cadeia contra o `fixed/`:
   - **4b/4c idênticos:** `POST /fetch` com a URL do IMDS → **`403 Forbidden`** visível, **sem corpo de creds**.
   - **Prova-chave:** o **vulnerable devolve as credenciais no corpo**; o **fixed recusa (`403`)** e nada volta. Como é **in-band**, a diferença aparece **na própria resposta** (contraste explícito com o 16, onde a prova era o hit no log).
   - **A lição do diff:** o fix **acrescenta** o gate de destino (allowlist, parse-then-check host, deny-by-default) **antes** do fetch, e recusa com `abort(403)`. **Allowlist, não blocklist de link-local** (forward pro `DIFF.md`, notas #1/#5); **IMDSv2** é a defesa do lado da cloud (nota #2, mencionável não aplicada).

**Trilha browser (secundária, opcional)** logo após a principal: submeter o form com a URL do IMDS, ver as creds no `<pre>`, depois repetir no `8117` e ver o `403`. **Sem** seção de exercícios/variações (`CLAUDE.md` §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## Impacto honesto

**Roubo de credencial IAM → account takeover na cloud.** O atacante lê credenciais de sessão **vivas** do IMDS via SSRF e **assume o papel da instância** — pode fazer o que o role permitir na conta cloud. É **um dos SSRF de maior impacto no mundo real** (âncora factual opcional: **Capital One, 2019** — SSRF → IMDS → credenciais). **NÃO é RCE** no servidor da app em si (as creds podem levar a mais **na conta**, mas o finding do átomo é o **roubo de credencial via SSRF**). **Sem overclaim.**

---

## Contraste com o arco / escopo — e a POLÍTICA DE FORESHADOW

**Arco de SSRF (A10), agora COMPLETO:** `04 (ssrf-basic, in-band — lê a resposta de um serviço interno genérico)` → `16 (ssrf-blind-oob, blind — detecta OOB, sem prêmio)` → **`17 (ssrf-cloud-metadata, in-band — o crown-jewel: IMDS → credencial IAM)`**. O 17 é o **pagamento do arco**: é o átomo onde a escalada que o 16 deliberadamente deixou de fora (alcançar metadata de cloud e roubar credencial) **acontece**. **Referenciar 04 E 16 (AMBOS PUBLICADOS) à vontade** (`CLAUDE.md` §5) — contraste explícito ancora a lição em algo que o aluno abre e valida.

**POLÍTICA DE FORESHADOW (crítico — lei do projeto, `CLAUDE.md` §5):**
- **O 17 FECHA o arco de SSRF. NÃO há próximo A10 pra antecipar.** **ZERO referência pra frente.**
- **PROIBIDO** citar/antecipar o **próximo átomo** ou **qualquer átomo/categoria futura** por número, nome **OU** descrição; **PROIBIDO** anunciar "próxima fase" ou a release `v0.4.0` no conteúdo do átomo.
- O que o SSRF **alcança** (serviços internos, metadata de cloud) é **descrição legítima da CLASSE** (como o 04 faz), **não** foreshadow. Falar do impacto de credencial IAM e de account takeover é a **lição deste átomo**, não antecipação de outro.
- Na dúvida, **mantém conceitual** e, se a variante tem página na PortSwigger Academy, é lá que se manda o aluno aprofundar.

**LIMITE DE ESCOPO:** o 17 vai até o **roubo da credencial via SSRF** (o finding). **Usar** a credencial (AWS CLI/SDK, enumerar a conta, pivotar) é **pós-exploração** — **fora de escopo** (`CLAUDE.md` §12: "técnicas de pós-exploração fora do escopo"). Descrever em uma linha que a credencial *seria* usada pra assumir o role; **não** transformar em passo executável.

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln ("what is X?"), **não** a página de listagem de labs. **Confirmar a URL por fetch na Fase 2 — não inventar** (se não confirmar, perguntar ao mantenedor).

- **Primário (candidato):** a **página geral de SSRF** — `https://portswigger.net/web-security/ssrf` (a mesma do 04, framing "what is SSRF?"). Razão: o conteúdo de **SSRF contra cloud metadata** (`169.254.169.254`) vive **dentro** dessa página (seção de ataques comuns), **não** numa página conceitual separada (diferente do *blind*, que tem `/ssrf/blind` própria e por isso o 16 pôde usá-la). **Confirmar por fetch na Fase 2** a seção/âncora mais específica; se surgir uma página dedicada "what is X?" de cloud-metadata SSRF, preferi-la.
- **Secundário (opcional):** doc **oficial do AWS IMDS** (candidato a confirmar por fetch — a página "Instance metadata and user data" / "Use IMDSv2" no `docs.aws.amazon.com`). **Não inventar a URL exata** — confirmar por fetch na Fase 2.
- **Texto do link:** preservar o nome em **inglês** também no README PT (`CLAUDE.md` §7 — ex. "Server-side request forgery (SSRF)", exatamente como a PortSwigger nomear a página).

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (form de URL + exibição do corpo — não API-only), **autoescape do Jinja LIGADO** (default). Garantir que a **ÚNICA** superfície é o SSRF:

- **Sem XSS:** o corpo buscado é ecoado num `<pre>` **escapado** (`{{ body }}`) — **sem** `|safe`/`Markup`/`render_template_string`. A URL ecoada também escapada.
- **Fetch com timeout** (`timeout=5`) → **sem** unbounded-consumption/DoS como 2ª falha.
- **Allowlist CORRETA** (parse-then-check host, deny-by-default) → **não** blocklist bypassável (senão o átomo vira "SSRF filter bypass", outro tópico).
- **Mock com creds FALSAS** (valores EXAMPLE da AWS) e **interno-only** (sem porta no host) → sem segredo real, sem 2º alvo exposto.
- A **única** superfície é o fetch outbound sem validação de destino.

---

## HTML — `templates/` (mínimo, molde do 04; `index.html` + `result.html`)

Molde do `ssrf-basic`/`sqli-union-basic`: `<!doctype>`, banner de aviso obrigatório, ≤40 linhas, ≤5 linhas de CSS inline, **sem** frameworks, **sem** JS, dica de Burp no rodapé. Diferente do 16 (que **não** tinha template de resultado, pra materializar a cegueira), o 17 **TEM** `result.html` (é in-band — o corpo é mostrado), **espelhando o `preview.html` do 04**. Templates **idênticos** entre vulnerable e fixed (o diff vive só no `app.py`). Candidatos (Fase 2 finaliza o texto exato):

**`templates/index.html`** (~18 linhas — molde do `index.html` do 04, form `POST /fetch`):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Fetch from URL</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Fetch from URL</h1>
<p>Enter a URL and the server fetches it and shows you the response body.</p>
<form method="post" action="/fetch">
  <label>URL: <input type="url" name="url" size="48" value="https://api.github.com/zen" autofocus></label>
  <button type="submit">Fetch</button>
</form>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

**`templates/result.html`** (~17 linhas — gêmeo do `preview.html` do 04; corpo num `<pre>` **escapado**):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Result &mdash; {{ url }}</title>
<style>body{font-family:sans-serif;max-width:960px;margin:2em auto;padding:0 1em;}pre{background:#eee;padding:0.8em;border-radius:4px;overflow:auto;max-height:480px;white-space:pre-wrap;word-break:break-all;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Result</h1>
<p>Fetched URL: <code>{{ url }}</code></p>
<p>HTTP status: <strong>{{ status if status is not none else "n/a" }}</strong></p>
<pre>{{ body }}</pre>
<p><a href="/">&larr; Back</a></p>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- Form pré-preenchido com uma URL benigna (candidato `https://api.github.com/zen`, casa com a `ALLOWED_HOSTS` do fixed) — o **ataque** é trocar por `http://169.254.169.254/latest/meta-data/iam/security-credentials/`.
- `result.html` é o gêmeo do `preview.html` do 04 (mesmos campos `url`/`status`/`body`, corpo escapado num `<pre>`). **`metadata-mock` NÃO tem `templates/`** (serve JSON/texto direto, como o `internal/` do 04).

---

## O container

`Dockerfile` **idêntico** entre `vulnerable` e `fixed` (**com** `COPY templates`, como o 04); `metadata-mock` usa o Dockerfile do `internal/` do 04 (**sem** `COPY templates`, `EXPOSE 80`). Só Flask (+ `requests` no vulnerable/fixed) via pip — sem `apt`, sem banco.

**`vulnerable/Dockerfile` e `fixed/Dockerfile`** (idêntico ao `ssrf-basic/vulnerable/Dockerfile`):

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

**`metadata-mock/Dockerfile`** (idêntico ao `ssrf-basic/internal/Dockerfile`):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Override default host (127.0.0.1) so other containers on the Docker network can reach Flask.
# This service is never published to the host (no ports: in docker-compose.yml).
ENV HOST=0.0.0.0
EXPOSE 80
CMD ["python", "-u", "app.py"]
```

`docker-compose.yml`: ver "Wiring do link-local" (três services; só `vulnerable`/`fixed` publicam porta, bind **só** `127.0.0.1`; `metadata-mock` **sem** porta no host, no IP `169.254.169.254` na Saída A / nome de serviço na Saída B).

---

## Bibliotecas

- **`vulnerable/requirements.txt` e `fixed/requirements.txt` (idênticos, espelham o 04):**

```
Flask==3.0.0
requests==2.32.3
```

- **`metadata-mock/requirements.txt` (espelha o `internal/` do 04 — só Flask, o mock não faz request outbound):**

```
Flask==3.0.0
```

- `os`, `urllib.parse` são **stdlib** (não vão no `requirements`).
- **Sem pin behavior-critical:** a vuln (fetch sem validar destino) é **agnóstica de versão** — é lógica de aplicação pura (diferente dos JWT, onde a versão do PyJWT **era** o objeto de estudo, `CLAUDE.md` §8.7). Os pins são só reprodutibilidade, coerentes com o 04/16.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A10 — SSRF** (`atoms/A10-ssrf/`, já existe) | ROADMAP lista `ssrf-cloud-metadata` em A10. **Terceiro átomo A10 — e o último do roadmap.** |
| Posição na Fase 4 | **Segundo (o 16 abriu; o 20 fecha)** | ROADMAP: 16/**17**/18/19/20; 01–16 já `[x]`. |
| Eixo | **CONTINUIDADE — arco A10/SSRF; FECHA o arco** | Pagamento do arco 04→16→17; não há próximo A10. |
| Visibilidade | **IN-BAND (busca e MOSTRA)** — volta ao modelo do 04 | A escalada sobre o 04 é ALVO+IMPACTO, não visibilidade. |
| Lição-coração | **SSRF→IMDS (`169.254.169.254`)→credencial IAM→account takeover; mesmo primitivo, alvo de maior valor** | O que muda do 04 é o alvo e o impacto, não o mecanismo. |
| Distinção central | **Arco em 3 beats: 04 (lê) → 16 (detecta) → 17 (loot do IMDS)** | O primitivo é o mesmo; muda canal e alvo/impacto. |
| Decisão estrutural | **Mock no IP REAL `169.254.169.254`** (Saída A); Saída B = alias/IP-privado + nota honesta | O payload idêntico ao real é a lição; torna o fix honesto. Mesma família honesta do 16. |
| Wiring — **SINALIZADO** | **Uma rede compartilhada** (`lab`, subnet `169.254.169.0/24`, mock em `.169.254`); vuln+fixed nela | IP fixo `/32` só vive numa subnet; IPAM do Docker recusa subnets sobrepostas → não dá pra ter o mesmo IP em duas redes (04/16 usam NOME, por isso têm duas). Propriedade load-bearing (mock alcançável das duas pontas) preservada. |
| Feature | **App web "fetch from URL"** (`/`, `/fetch`), in-band | Flavor do 04 (busca-e-mostra), diferenciado no nome. |
| Endpoint / método — **SINALIZADO** | **`POST /fetch`** (`request.form["url"]`) | Método travado pelo prompt (esboço `request.form`). POST espelha o 16; `/fetch`+in-band espelham o 04. Fallback: `GET /fetch?url=` do 04. |
| Resposta do vulnerable | **ECOA o corpo buscado** (creds do IMDS voltam), escapado num `<pre>` | In-band — é como o aluno lê as creds. Escapado → sem XSS. |
| Resposta do fixed | **`abort(403)` VISÍVEL** (como o 04) | In-band → recusa visível OK. **NÃO byte-idêntica** (isso foi exclusivo do 16, cego). |
| Fix (único eixo) | **Validar o destino (allowlist deny-by-default)** antes do fetch | Mesma família do 04/16; a defesa generaliza pelo arco. |
| Scheme gate — **SINALIZADO** | **`("http", "https")`** (permite os dois) | IMDS é http; permitir http e recusar pelo HOST torna o host o check load-bearing (evita a lição falsa "bloqueei http"). Diverge do https-only do 04, de propósito. |
| Diff | **Lógica-diferente** (código adicionado no `/fetch`): gate + `abort(403)` | Tipo dos A01/JWT/04/16. A única mudança é o gate + a recusa. |
| Mock | **fake IMDS IMDSv1-style; role-listing → JSON de creds EXAMPLE da AWS; porta 80; interno-only** | Superfície mínima realista; creds obviamente falsas; sem token PUT (IMDSv2 é nota, não código). |
| HTML | **`index.html` (form) + `result.html` (corpo escapado)** — gêmeo do `preview.html` do 04 | In-band → tem template de resultado (diferente do 16). |
| Bibliotecas | **`Flask==3.0.0` + `requests==2.32.3`** (vuln/fixed); **`Flask==3.0.0`** (mock) | Espelha o 04/16. Pin não behavior-critical (SSRF é agnóstico de versão). Sem AWS SDK. |
| Impacto | **roubo de credencial IAM → account takeover.** Não RCE. Usar a credencial = pós-exploração (fora de escopo). | Honesto; sem overclaim; âncora Capital One 2019 opcional. |
| Theory primer | **PortSwigger SSRF geral** (`/web-security/ssrf`, confirmar por fetch); secundário AWS IMDS docs | Cloud-metadata SSRF vive dentro da página geral; não há página "what is X?" só de metadata. Não inventar. |
| Foreshadow | **ZERO pra frente** (17 fecha o arco; não há próximo A10) | `CLAUDE.md` §5. Impacto de credencial é a lição, não antecipação. |
| Portas | **8017 / 8117** (bind só `127.0.0.1`); mock **sem porta no host** | `CLAUDE.md` §8. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–8 são os centrais; 9–13 são higiene técnica / topologia. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /`** → serve o form (campo de URL, banner, dica de Burp). Template mínimo renderiza.
2. **`POST /fetch` (vuln) com URL benigna vetada** → **corpo volta** (in-band funciona; baseline).
3. **O ATAQUE (central — VALIDAR RODANDO):** no vulnerable, `POST /fetch` pro IMDS → `.../security-credentials/` devolve o **role**; `.../security-credentials/<role>` devolve o **JSON de creds falsas NO CORPO**. **Capturar a cadeia real.** **Se não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** ids/responses/creds.
4. **FIXED (`8117`):** mesma cadeia → **`abort(403)` visível, SEM creds**. **Capturar a recusa** (o `403`).
5. **Robustez do fix (allowlist CORRETA, não blocklist bypassável):** parse-then-check host. Testar **decimal** (`http://2852039166/`), **hex** (`http://0xa9fea9fe/`), **`[::ffff:169.254.169.254]`**, **userinfo** (`http://api.github.com@169.254.169.254/`) → **TODOS barrados** (deny-by-default; host parseado não está na allowlist → `403`). **Redirect `302`→IMDS:** o redirector não-vetado é barrado **no gate**; o hardening `allow_redirects=False` é **descrito, não aplicado** (nota do DIFF — mantém a única mudança = gate + recusa). Confirmar que **só** `api.github.com` (o vetado) passa.
6. **In-band real:** a resposta do vuln realmente **MOSTRA** o conteúdo buscado (contraste com o 16, que era cego). Confirmar que as creds aparecem **no corpo**.
7. **Mock = superfície IMDS realista, creds obviamente falsas, interno-only:** role-listing → JSON de creds (valores EXAMPLE da AWS), sem segredo real, **NÃO** exposto em porta do host. Confirmar que o `metadata-mock` **não tem** mapeamento de porta pro host no compose.
8. **Link-local (Saída A):** `169.254.169.254` fixado (subnet `169.254.169.0/24` + `ipv4_address`). Confirmar **alcançável do `vulnerable` E do `fixed`** no nível de rede (a recusa do fixed é do **código**, não da rede). **Se não fixar limpo → Saída B** (nome de serviço `metadata-mock` / IP privado + **nota honesta**); documentar a Saída B se acionada.
9. **Uma vuln só:** autoescape do Jinja ligado (corpo escapado no `<pre>`); fetch com `timeout=5` (sem DoS); allowlist correta (não blocklist); sem falha empilhada. A **única** superfície é o fetch sem validação de destino.
10. **IMDSv2 descrito no DIFF** (nota obrigatória #2, nomeada: token via PUT + hop-limit; postura do serviço de metadata, não fix no código do app → descrito, não aplicado).
11. **Primer PortSwigger** (página geral de **SSRF**, `/web-security/ssrf`, ou seção mais específica) **confirmado por fetch**. Secundário AWS IMDS docs (confirmar por fetch, não inventar). Se em dúvida, perguntar ao mantenedor.
12. **Higiene:** portas **8017/8117** bind **só** `127.0.0.1`; `metadata-mock` **interno-only** (sem `ports:`). `Flask==3.0.0`+`requests==2.32.3` instalam limpo no `python:3.11-slim`. `./atom up ssrf-cloud-metadata` sobe sem erro. **Validar via `docker exec` + `python http.client`/`curl` de dentro do container** se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`).
13. **`app.py` vulnerable × fixed:** confirmar por `diff` que a mudança é **só** o gate + a recusa no `/fetch` (ausente vs presente: import `urlparse`+`abort` + `ALLOWED_HOSTS` + `parsed = urlparse(url)` + `if ...: abort(403)`), e que o resto (`GET /`, imports comuns, o `render_template("result.html", ...)`, rodapé) e os **templates** são **byte-idênticos**. Diff **lógica-diferente**.

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** validar a cadeia de ataque rodando (itens 2–4); confirmar o wiring do link-local (item 8) e acionar a Saída B se preciso; confirmar as URLs de primer por fetch (item 11); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo **FECHA o arco A10** aberto pelo 04 e continuado pelo 16 — é o **pagamento** do arco. Cada beat deve poder ser lido com o **`ssrf-basic` (04)** e o **`ssrf-blind-oob` (16)** abertos ao lado. **Abrir e fechar** na lição-coração: *o primitivo de SSRF é o mesmo dos átomos anteriores; apontado pro IMDS (`169.254.169.254`), devolve a credencial IAM da instância → account takeover.*
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** **`ssrf-basic` (04) INTEIRO** (o irmão in-band — estilo do allowlist, `abort(403)`, o `preview.html`, o `internal/`, o `docker-compose.yml`) e **`ssrf-blind-oob` (16) INTEIRO** (o irmão recém-publicado — o contraste blind vs in-band, o padrão do serviço extra nas redes, e o **DIFF que argumenta allowlist > blocklist**, com que o 17 tem que ser **coerente**); `sqli-union-basic` (01, referência canônica); esta spec. Ler **não é pra copiar** — é pra **conformar** à convenção do arco.
- **A SAÍDA A/B do link-local é o coração estrutural sinalizado:** implementar a **Saída A** (mock no IP real `169.254.169.254`, uma rede compartilhada); se o Docker não fixar o link-local limpo, cair pra **Saída B** (nome de serviço/IP privado) **COM NOTA HONESTA**. Explicar **por que** o 17 usa uma rede só (diferente das duas redes do 04/16) — o IP fixo `/32` força isso, e a propriedade load-bearing (mock alcançável das duas pontas) fica preservada. Cravar no DIFF/README.
- **A prova é a credencial (não) voltar no corpo (risco #3/#4).** Capturar a cadeia real: vulnerable → role-listing → JSON de creds **no corpo**; fixed → **`403`**, sem creds. **Se não bater rodando, PARAR e avisar — NÃO inventar** creds/responses.
- **Uma vuln só:** eco **escapado** (autoescape, `<pre>`, sem `|safe`); fix é allowlist **correta** (parse-then-check host, deny-by-default, **não** blocklist de link-local); fetch com timeout; mock com creds **falsas** (valores EXAMPLE da AWS) e **interno-only**. A **única** superfície é o fetch sem validação de destino.
- **Ator único, cadeia recon→loot:** rotular no WALKTHROUGH **baseline** → **recon** (role) → **loot** (creds) → **fixed** (`403`). O aluno é o pentester sozinho.
- **Impacto honesto:** **roubo de credencial IAM → account takeover.** **NÃO** RCE na app. **Usar** a credencial é pós-exploração (**fora de escopo**, `CLAUDE.md` §12 — descrever em uma linha, não executar). Âncora Capital One 2019 **opcional**.
- **`what the vuln is NOT` (obrigatório, `CLAUDE.md` §5):** cravar que **o IMDS/`169.254.169.254` NÃO é a misconfiguration** (é link-local, não-autenticado, por design em toda VM de cloud) — **o bug é a app** que busca qualquer URL. Esse é o contraste-chave (o vizinho conceitual errado: "a AWS expõe o metadata").
- **Política de referência cross-átomo:** OK citar **04 e 16 à vontade** (ambos publicados; o arco 04→16→17 é a espinha). **PROIBIDO** referenciar/foreshadowar qualquer átomo não-publicado/categoria futura por número, nome **ou** descrição; **NÃO** anunciar "próxima fase" nem a release `v0.4.0` no conteúdo do átomo. O 17 **fecha** o arco A10 — **não há próximo A10 pra antecipar**.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico em EN e PT (`ssrf-cloud-metadata — Cloud metadata SSRF (IAM credential theft)`, texto exato confirmável na Fase 2). Termos técnicos (SSRF, in-band, out-of-band, payload, allowlist, deny-by-default, blocklist, IMDS, IMDSv2, metadata endpoint, link-local, IAM, role, credential, session token, account takeover, egress, DNS rebinding, sink, source) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (SSRF), nome da página preservado em inglês no PT; secundário opcional AWS IMDS docs. **Confirmar as URLs por fetch na Fase 2** — não inventar.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 17: `ssrf-cloud-metadata` — SSRF against the cloud metadata endpoint (169.254.169.254), stealing IAM credentials (A10 SSRF). `` (padrão das linhas dos átomos anteriores; a linha do 16 já está em `[Unreleased]`).
- **ROADMAP.md:** marcar o átomo 17 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–13; reproduzir baseline → recon → loot (creds no corpo) → fixed (`403`). Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8017` (vulnerable), `127.0.0.1:8117` (fixed). `metadata-mock` **interno-only**. Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre as URLs de primer, a forma exata do H1, o wiring do link-local (Saída A vs B), o método/nome do endpoint, ou se a cadeia de ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato único, se você quiser um pointer de recall rápido independente do spec/DIFF:**

- **`ssrf-cloud-metadata-link-local-wiring`** — *"No `ssrf-cloud-metadata` (17, fecha o arco A10), o `metadata-mock` (fake IMDS, creds EXAMPLE da AWS, interno-only) responde no IP REAL `169.254.169.254`. Diferente do 04/16 (que endereçam o serviço extra por NOME DNS e por isso usam DUAS redes), o 17 precisa do IP fixo `/32`, que só vive numa subnet — e o IPAM do Docker recusa subnets sobrepostas entre redes. Logo `vulnerable`+`fixed`+`metadata-mock` compartilham UMA rede (`ipam` subnet `169.254.169.0/24`, mock com `ipv4_address` estático). Saída B se o link-local não fixar: alias `metadata-mock`/IP privado + nota honesta. Fix = allowlist deny-by-default (`abort(403)` visível, in-band, como o 04 — NÃO byte-idêntico como o 16). IMDSv2 = nota mencionável-não-aplicada no DIFF."* — tipo `project`/`reference`.

**Ressalva:** esse fato vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, salvo se você quiser o recall rápido do wiring link-local fora do spec (é o único ponto genuinamente não-óbvio e reutilizável entre sessões). Sua decisão.
