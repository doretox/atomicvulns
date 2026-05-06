# ROADMAP.md — Plano de Implementação

> Checklist vivo. Marque `[x]` conforme for concluindo cada átomo. Este arquivo é a fonte da verdade para "o que fazer a seguir" — o Claude Code consulta aqui quando você não especifica o próximo.

---

## Como usar este arquivo

- **Ordem é proposital.** Cada átomo é pré-requisito conceitual do próximo (salvo quando marcado "independente").
- **Fases são marcos publicáveis.** Ao fechar uma fase, o repo ganha uma release (`v0.1`, `v0.2`, ...) e um anúncio.
- **Seguir a ordem não é obrigatório** — se um cliente seu tá enchendo de JWT, vá pra JWT. Mas o caminho padrão é este.
- **Numeração sequencial** é a base das portas (átomo 01 → 8001/8101, átomo 15 → 8015/8115). Não renumere átomos já publicados.

Legenda:
- `[ ]` — pendente
- `[~]` — em progresso (branch `atom/<id>` aberta)
- `[x]` — concluído e em `main`
- `[s]` — pulado (com justificativa no comentário)

---

## Fase 1 — MVP Pentester (Foundation)

**Objetivo:** cobrir as 5 vulnerabilidades mais frequentes em relatórios de pentest júnior. Ao fim desta fase, o repo já é útil publicado. É o *mínimo viável para marketing e feedback*.

**Milestone:** `v0.1 — MVP`

- [x] **01.** `sqli-union-basic` — A03 Injection
  - *Por que primeiro:* classe mais icônica, exploit visual (dados vazando na tela), template do repo nasce aqui.
  - *Dependências conceituais:* nenhuma.

- [x] **02.** `xss-reflected` — A03 Injection
  - *Por que segundo:* mesma classe (injection) mas sink diferente (HTML em vez de SQL), reforça o conceito de source→sink.
  - *Dependências:* nenhuma.

- [x] **03.** `idor-numeric-id` — A01 Broken Access Control
  - *Por que terceiro:* sai de injection e entra em *logic flaw*. Mostra que nem toda vuln é input malicioso — às vezes é só trocar um `1` por `2`.
  - *Dependências:* nenhuma.

- [~] **04.** `ssrf-basic` — A10 SSRF
  - *Por que quarto:* server-side, moderno, altíssimo impacto em cloud. Requer o conceito de "app que faz request por você" — bom pra introduzir.
  - *Dependências:* nenhuma.

- [ ] **05.** `jwt-none-alg` — A02 Cryptographic Failures
  - *Por que fecha MVP:* introduz o mundo JWT, ensina a decodar token no Burp, mostra que "parece crypto" não é "é crypto".
  - *Dependências:* conceito de autenticação via token (explicado no walkthrough).

---

## Fase 2 — Aprofundamento em Injection

**Objetivo:** dominar as variantes blind e side-channels, que são o que separa pentester júnior de pleno em relatórios de SQLi/command injection.

**Milestone:** `v0.2 — Injection Deep Dive`

- [ ] **06.** `sqli-blind-boolean` — A03 Injection
  - *Por que aqui:* agora que SQLi básico tá internalizado, introduz o conceito de extrair dado sem ver a resposta direto.

- [ ] **07.** `sqli-blind-time` — A03 Injection
  - *Por que aqui:* mesmo conceito do anterior mas via timing side-channel. Par natural.

- [ ] **08.** `xss-stored` — A03 Injection
  - *Por que aqui:* reflected já tá dominado (átomo 02), stored mostra persistência e impacto em vítimas múltiplas.

- [ ] **09.** `command-injection-basic` — A03 Injection
  - *Por que aqui:* outra injection, sink diferente (shell). Reforça padrão source→sink em ambiente OS.

- [ ] **10.** `path-traversal-basic` — A01 Broken Access Control
  - *Por que aqui:* parente próximo de command injection (manipulação de caminho no sistema de arquivos), bom ponte pra fase de access control.

---

## Fase 3 — Access Control & Autenticação

**Objetivo:** sair do input-driven e entrar em falhas de lógica de autorização e identidade — o que mais rende em relatórios de bug bounty.

**Milestone:** `v0.3 — Auth & Access`

- [ ] **11.** `idor-uuid-guessable` — A01 Broken Access Control
  - *Variante do 03:* IDOR em UUID previsível, não só ID numérico. Mostra que UUID ≠ seguro por si só.

- [ ] **12.** `bola-rest` — A01 Broken Access Control
  - *Por que aqui:* BOLA (Broken Object Level Authorization) em API REST, variante moderna do IDOR — é o #1 do OWASP API Top 10.

- [ ] **13.** `jwt-weak-secret` — A02 Cryptographic Failures
  - *Por que aqui:* complementa o `jwt-none-alg`, introduz brute force de secret com hashcat/john.

- [ ] **14.** `jwt-key-confusion` — A02 Cryptographic Failures
  - *Por que aqui:* trilogia JWT fechada com o mais sofisticado dos três (RS256→HS256 confusion).

- [ ] **15.** `session-fixation` — A07 Auth Failures
  - *Por que aqui:* última peça de auth, mostra que a falha pode estar *antes* do login, não só nele.

---

## Fase 4 — Server-side Avançado

**Objetivo:** os ataques que todo pentester quer saber fazer — SSRF explorado de verdade, XXE, SSTI, deserialization.

**Milestone:** `v0.4 — Server-side Power Moves`

- [ ] **16.** `ssrf-blind-oob` — A10 SSRF
  - *Variante do 04:* SSRF sem resposta direta, usando canal out-of-band (Burp Collaborator, interact.sh).

- [ ] **17.** `ssrf-cloud-metadata` — A10 SSRF
  - *Por que aqui:* mostra o impacto real de SSRF em AWS/GCP/Azure (metadata endpoint). Altíssimo valor em pentest cloud.

- [ ] **18.** `xxe-basic` — A05 Security Misconfiguration
  - *Por que aqui:* introduz XML externo, leitura de arquivo via entity.

- [ ] **19.** `ssti-jinja` — A03 Injection
  - *Por que aqui:* Template injection em Jinja2 — perfeito porque o repo inteiro usa Jinja, o contexto é familiar.

- [ ] **20.** `deserialization-pickle` — A08 Data Integrity Failures
  - *Por que aqui:* RCE via deserialization em Python. Fecha a fase com um bang.

---

## Fase 5 — Client-side & NoSQL

**Objetivo:** cobrir o que foi deixado no client-side (DOM XSS, CSRF) e o mundo NoSQL.

**Milestone:** `v0.5 — Client & NoSQL`

- [ ] **21.** `xss-dom` — A03 Injection
  - *Por que aqui:* DOM XSS é conceitualmente mais sutil (sink no JS do cliente, não no HTML do servidor) — fica pra depois dos outros XSS internalizados.

- [ ] **22.** `nosql-injection-mongo` — A03 Injection
  - *Por que aqui:* contraparte moderna do SQLi, com sintaxe própria (`$ne`, `$gt`). Único átomo da fase que introduz MongoDB.

- [ ] **23.** `csrf-basic` — A01 Broken Access Control
  - *Por que aqui:* precisa de contexto de sessão já internalizado (fase 3).

- [ ] **24.** `open-redirect` — A01 Broken Access Control
  - *Por que aqui:* simples, mas frequente em bug bounty como parte de chains (ex: OAuth stealing).

- [ ] **25.** `mass-assignment` — A01 Broken Access Control
  - *Por que aqui:* falha comum em APIs REST que aceitam JSON direto em ORM. Fecha a categoria A01.

---

## Fase 6 — Edge cases e vulns raras

**Objetivo:** cobrir o que aparece raramente mas causa dano enorme quando aparece. Também introduz Node.js pela primeira vez.

**Milestone:** `v0.6 — Rare but Deadly`

- [ ] **26.** `prototype-pollution` — A08 Data Integrity Failures
  - *Primeiro átomo em Node.js.* A única vuln que realmente só faz sentido em JS.

- [ ] **27.** `deserialization-node` — A08 Data Integrity Failures
  - *Por que aqui:* par natural com `deserialization-pickle` (átomo 20), mas no ecossistema Node.

- [ ] **28.** `ldap-injection` — A03 Injection
  - *Por que aqui:* rara em apps modernas mas aparece em corp/AD, vale saber.

- [ ] **29.** `sqli-second-order` — A03 Injection
  - *Por que aqui:* SQLi sofisticado onde o payload é guardado em um ponto e triggado em outro. Exige os SQLis anteriores internalizados.

- [ ] **30.** `xxe-blind-oob` — A05 Security Misconfiguration
  - *Variante do 18:* XXE sem resposta direta, via out-of-band.

---

## Fase 7 — Completar cobertura do Top 10

**Objetivo:** fechar os itens do Top 10 ainda descobertos (A02 crypto puro, A04, A05 misconfig, A06, A07 restante, A09).

**Milestone:** `v1.0 — Full OWASP Top 10 Coverage`

- [ ] **31.** `crypto-weak-hash` — A02 Cryptographic Failures
  - *Por que aqui:* MD5/SHA1 em password storage, brute force com rainbow table/hashcat.

- [ ] **32.** `crypto-ecb-mode` — A02 Cryptographic Failures
  - *Por que aqui:* ECB penguin, bit-flipping, padding oracle lite.

- [ ] **33.** `debug-enabled` — A05 Security Misconfiguration
  - *Por que aqui:* Flask `debug=True` com Werkzeug console. Simples e devastador.

- [ ] **34.** `cors-wildcard` — A05 Security Misconfiguration
  - *Por que aqui:* CORS mal configurado permitindo credenciais. Frequente em APIs.

- [ ] **35.** `race-condition-basic` — A04 Insecure Design
  - *Por que aqui:* TOCTOU em lógica de negócio (ex: resgatar cupom 2x simultâneo). Único átomo de A04.

- [ ] **36.** `cve-demo` — A06 Vulnerable Components
  - *Por que aqui:* átomo diferente — aponta pra CVE concreta em lib específica, mostra o exploit público rodando.

- [ ] **37.** `weak-password-reset` — A07 Auth Failures
  - *Por que aqui:* token previsível ou reusável em reset de senha.

- [ ] **38.** `logging-failures-demo` — A09 Logging Failures
  - *Por que por último:* átomo atípico, mais demonstrativo do que explorável. Mostra como a ausência de log deixa ataque invisível.

---

## Após Fase 7 — Pós-MVP completo

Quando todos os 38 átomos estiverem publicados, possíveis direções:

- **OWASP API Security Top 10** (átomos específicos de API não cobertos acima).
- **OWASP Mobile Top 10** (muda stack pra mobile — decisão separada).
- **Cloud-specific** (IAM misconfig, S3 buckets, etc.).
- **Aprofundar átomos existentes** com variantes (ex: `sqli-union-postgres`, `sqli-union-mysql` para mostrar diferenças de syntax).
- **Traduzir walkthroughs pra outros idiomas** (ES, FR) se houver demanda da comunidade.
- **Criar "chains"** — sequências de 2-3 átomos encadeados pra mostrar como vulns se compõem no mundo real.

Nenhuma dessas direções é compromisso. Decisão fica pra quando chegar lá.

---

## Dúvidas frequentes que você vai ter durante execução

**"Estou preso no átomo X, posso pular?"**
Pode. Marque como `[s]` com justificativa, e volte depois. Só evite pular os da Fase 1 — o MVP depende dos 5.

**"Quero fazer um átomo fora da ordem porque tô estudando pra um pentest específico."**
Vai fundo. A ordem é recomendação, não prisão. Só lembre de dar um número sequencial novo (o próximo disponível) pra não bagunçar as portas.

**"E se a OWASP lançar uma nova edição do Top 10 durante o projeto?"**
Renomeamos as pastas `A0X-*` conforme o novo mapeamento, mas mantemos os IDs dos átomos. Os arquivos de código não mudam.

**"Quando abrir o repo pro público?"**
Recomendação: quando a Fase 1 fechar (v0.1). 5 átomos é o mínimo pra alguém clonar e achar útil. Antes disso é esqueleto.

---

**Última atualização do plano:** criação do documento.
