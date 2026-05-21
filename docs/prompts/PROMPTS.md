# PROMPTS.md — Biblioteca de Prompts para o Claude Code

> Coleção de prompts prontos para usar com o Claude Code durante o projeto `atomicvulns`. Copie, cole, ajuste o que estiver entre `<colchetes>`.
>
> Organização: do setup inicial até operações avançadas e manutenção de longo prazo.

---

## 1. Setup inicial do repositório

### 1.1. Onboarding do Claude Code no projeto (primeira sessão)

```
Leia na ordem:
1. CLAUDE.md
2. ROADMAP.md
3. ATOM-01-SPEC.md (se existir)

Depois, confirme em 3 bullets curtos:
- Qual é o objetivo do projeto.
- Qual é o próximo átomo a implementar segundo o ROADMAP.
- Qual é a regra mais importante sobre UI/frontend no projeto.

Não comece a escrever código ainda.
```

*Use este prompt sempre que abrir uma sessão nova do Claude Code. Serve como "calibração" — se ele errar algum dos 3 pontos, você sabe que algo não foi lido corretamente.*

### 1.2. Criar o arquivo LICENSE

```
Crie o arquivo LICENSE na raiz do repo com o texto padrão da MIT License, copyright "Jose Renato Doreto <ano atual>". Não invente, use o texto canônico da MIT.
```

### 1.3. Criar o README raiz (inglês + PT)

```
Crie README.md (inglês) e README.pt-BR.md na raiz do repo, seguindo a Seção 7 do CLAUDE.md (idioma).

Conteúdo obrigatório:
- Nome do projeto: atomicvulns
- Banner de aviso sobre código intencionalmente vulnerável
- O que é o projeto (2 parágrafos)
- Quem é o público-alvo
- Como rodar um átomo (comando ./atom up <id>)
- Link pro ROADMAP.md
- Link pro CLAUDE.md (marcado como "para contribuidores")
- Seção de licença (MIT)
- Badges placeholder (serão adicionadas depois)

Mantenha as duas versões sincronizadas 1:1.
```

### 1.4. Criar o `.gitignore`

```
Crie um .gitignore apropriado pro projeto. Inclua pelo menos:
- Python (__pycache__, *.pyc, venv, .env)
- SQLite (*.db, *.sqlite, *.sqlite3)
- Docker (volumes locais)
- IDE (.idea, .vscode, .DS_Store)
- Burp (arquivos de projeto .burp)

Comente cada seção para deixar claro o propósito.
```

---

## 2. Implementação de átomos

### 2.1. Implementar o átomo 01 (a partir da spec completa)

```
Leia ATOM-01-SPEC.md. Implemente o átomo `sqli-union-basic` seguindo a spec literalmente.

Não pule nenhum item do checklist de entrega ao final da spec.

Quando terminar:
1. Liste todos os arquivos criados com caminho completo.
2. Mostre o comando exato que eu devo rodar para validar.
3. Diga explicitamente o que eu preciso verificar manualmente no Burp antes de dar merge.
```

### 2.2. Especificar um átomo novo (átomos 02+)

```
Leia docs/templates/ATOM-SPEC-TEMPLATE.md e CLAUDE.md.

Preencha uma spec para o átomo `<id>` (número <NN> no ROADMAP).

Proposta inicial que quero que você considere:
- Feature simulada: <sua ideia>
- Observações: <qualquer constraint específico>

Me entregue a spec preenchida como arquivo em `docs/specs/atom-<NN>-<id>.md`.
Aguarde minha aprovação antes de implementar.
```

### 2.3. Implementar um átomo a partir de spec aprovada

```
Implemente o átomo `<id>` seguindo `docs/specs/atom-<NN>-<id>.md`.

Respeite:
- Seção 5 do CLAUDE.md (estrutura de pastas).
- Seção 3.3 do CLAUDE.md (regras de HTML/rendering).
- Seção 8 do CLAUDE.md (regras de segurança).
- Seção 7 do CLAUDE.md (sincronia PT/EN).

Ao final, liste arquivos criados e me diga exatamente como validar.
```

### 2.4. Implementar átomo direto, sem spec formal (para átomos simples)

```
Implemente o átomo `<id>` (OWASP A0X, categoria <nome>) seguindo os padrões estabelecidos no átomo 01.

Antes de codar, me entregue uma proposta curta de design cobrindo:
- Feature simulada
- Endpoint(s)
- Pseudocódigo da view vulnerável
- Diff resumido do fix
- Os 2-3 payloads principais do walkthrough

Aguarde minha aprovação antes de escrever qualquer arquivo.
```

### 2.5. Pedir revisão/ajustes num átomo já implementado

```
O átomo `<id>` tem o seguinte problema: <descreva>.

Diagnostique a causa lendo os arquivos relevantes, proponha o fix mínimo (sem reescrever o átomo inteiro), e aplique.

Se o fix afetar o walkthrough ou o diff, atualize ambas as versões (EN e PT).
```

---

## 3. Validação e testes

### 3.1. Pedir um smoke test manual antes de commitar

```
Vou fazer merge do átomo `<id>` em instantes.

Antes, me entregue um checklist manual de 5-8 verificações que eu preciso fazer, específicas deste átomo. Não me repita o checklist genérico do CLAUDE.md — foque no que é particular deste átomo (payloads, comportamento esperado da feature, detalhes do fix).
```

### 3.2. Reproduzir o exploit passo a passo para conferência

```
Pegue o WALKTHROUGH.md do átomo `<id>` e converta cada payload em um comando `curl` equivalente, sem usar nem Burp nem browser.

Objetivo: eu rodo os curls em sequência e vejo se o exploit reproduz. Isso serve como teste de sanidade alternativo antes de publicar.
```

### 3.3. Gerar testes automatizados de regressão (opcional, pós-MVP)

```
Crie um arquivo `test_exploit.py` na pasta do átomo `<id>` que:
1. Usa `requests` pra fazer os payloads do walkthrough contra o container vulnerable.
2. Verifica que cada payload produz o efeito documentado.
3. Roda os mesmos payloads contra o container fixed e verifica que não produzem o efeito.

O teste serve como regressão para CI. Não vira parte do material didático — fica em `tests/` se preferir.
```

---

## 4. Infraestrutura e tooling

### 4.1. Criar o wrapper `./atom` (após átomo 01 funcionar)

```
Crie um script `atom` na raiz do repo (bash ou python, sua escolha justificada) que suporta:

- `./atom list` → lista todos os átomos disponíveis com status (parado/rodando).
- `./atom up <id>` → sobe docker compose do átomo, mostra URLs de vulnerable e fixed.
- `./atom down <id>` → derruba containers e limpa.
- `./atom doctor` → verifica dependências (docker, docker compose, portas livres).

O script deve localizar átomos automaticamente varrendo `atoms/A0X-*/<id>/`. Não hardcode IDs.

Ao final, crie também um `Makefile` simples com os mesmos comandos, pra quem prefere `make up ATOM=<id>`.
```

### 4.2. Criar GitHub Actions básico

```
Crie `.github/workflows/ci.yml` que roda em todo PR:

1. Lint: busca em todos os `docker-compose.yml` e `app.py` por bind em `0.0.0.0` → falha se encontrar.
2. Build: constrói todos os Dockerfiles dos átomos pra garantir que não quebraram.
3. Lint de sincronia: verifica que todo átomo tem README.md + README.pt-BR.md, WALKTHROUGH.md + WALKTHROUGH.pt-BR.md, DIFF.md + DIFF.pt-BR.md.

Use um job matrix pra descobrir átomos dinamicamente. Não hardcode a lista.
```

### 4.3. Criar template de átomo reutilizável

```
Crie `docs/atom-template/` com a estrutura exata de um átomo vazio (pastas e arquivos placeholder). Os arquivos `.md` devem ter cabeçalhos e seções já estruturados como comentários HTML, prontos pra preencher.

Objetivo: scaffold rápido — copiar a pasta, renomear, preencher.
```

---

## 5. Documentação e comunicação

### 5.1. Escrever o CONTRIBUTING.md

```
Crie `docs/contributing.md` (e versão PT). Cubra:

- Como propor um átomo novo (checar ROADMAP antes).
- Fluxo de branch (`atom/<id>`) e commits (Conventional Commits).
- Checklist obrigatório antes do PR.
- Política de review (o mantenedor valida no Burp antes de aprovar).
- Código de conduta em 2 parágrafos.

Tom: claro e acolhedor, mas deixando claro que este é um projeto de segurança e revisão é rigorosa.
```

### 5.2. Gerar release notes de uma fase

```
Gere as release notes da Fase <N> (versão v0.<N>) do projeto, cobrindo os átomos <list>.

Formato:
- Highlights (1 parágrafo)
- Átomos adicionados (lista com ID, classe, link pro walkthrough)
- Melhorias estruturais (wrapper, CI, docs)
- Próxima fase (o que vem em v0.<N+1>)

Salve em `docs/releases/v0.<N>.md`. Mantenha tom acessível mas técnico.
```

### 5.3. Escrever um post de anúncio (fim de fase)

```
Escreva um post de blog/LinkedIn anunciando a versão v0.<N> do atomicvulns.

Pontos:
- O que é o projeto em 3 frases.
- O que há de novo nesta release.
- Quem vai se beneficiar e como usar.
- Call-to-action: clonar o repo, rodar o primeiro átomo, dar feedback.

Tom: pentester falando com pentester, sem jargão corporativo. Entregue em PT-BR e EN.
Tamanho: ~300 palavras cada.
```

### 5.4. Gerar índice master dos átomos no README principal

```
Leia todos os átomos em `atoms/A0X-*/` e gere uma tabela markdown no README.md (e README.pt-BR.md) listando:

| # | ID | Categoria OWASP | Status | Porta vuln | Link |

Use emojis discretos pra status (✅ concluído, 🚧 em desenvolvimento, ⏳ planejado).

Essa tabela deve ser regerada sempre que um átomo novo for mergeado — considere criar um script `scripts/update_atoms_index.py` pra isso.
```

---

## 6. Manutenção e iteração

### 6.1. Checkar a saúde geral do projeto

```
Auditoria completa do repo. Verifique e reporte:

1. Átomos que têm PT e EN dessincronizados (datas de modificação ou conteúdo divergente).
2. Átomos que não seguem a Seção 5 do CLAUDE.md (arquivos faltando).
3. Container bindando em 0.0.0.0 em algum lugar.
4. Dependências desatualizadas nos requirements.txt de cada átomo (se afeta o átomo ou é "brinde").
5. Links quebrados entre docs.
6. ROADMAP.md desatualizado (átomos concluídos em main que não estão marcados [x]).

Entregue um relatório em markdown com severidade (crítico/médio/baixo) pra cada item. Não corrija nada ainda — só reporte.
```

### 6.2. Atualizar documentação após mudança estrutural

```
A seguinte mudança foi introduzida: <descreva>.

Encontre todos os lugares no repo que precisam ser atualizados pra refletir essa mudança:
- CLAUDE.md
- ROADMAP.md
- README.md (e PT)
- CONTRIBUTING.md (e PT)
- Templates
- Átomos já existentes (se afetados)

Proponha as edições em forma de diff pra eu aprovar antes de aplicar.
```

### 6.3. Reformular um átomo já publicado

```
O átomo `<id>` foi publicado mas recebeu feedback de que <descreva o feedback>.

Proponha uma reformulação:
- Mantenha o ID e a porta (pra não quebrar referências externas).
- Liste o que muda em: app.py, HTML, walkthrough, diff.
- Diga se é mudança retrocompatível ou se requer aviso na release.

Aguarde aprovação antes de aplicar.
```

### 6.4. Adicionar uma variante (átomo novo muito próximo de um existente)

```
Adicione o átomo `<id-novo>` que é uma variante de `<id-existente>`.

Diferenças esperadas: <lista>.

Reaproveite tudo que for possível do átomo existente (estrutura, HTML base, tom do walkthrough), ajustando apenas o que é específico da variante. A spec tem que caber em 1 página.
```

---

## 7. Quando algo dá errado

### 7.1. Claude Code propôs algo que viola o CLAUDE.md

```
Sua última proposta viola a seguinte regra do CLAUDE.md: <cite a seção>.

Reavalie, proponha uma alternativa que respeite a regra, e explique por que a primeira proposta não cabia.
```

### 7.2. Exploit do walkthrough não funciona ao testar

```
Rodei `./atom up <id>` e tentei o Step <N> do walkthrough. Não funciona: <descreva o que aconteceu vs. o esperado>.

Diagnóstico possível: <sua hipótese, se tiver alguma>.

Investigue (leia o código, teste você mesmo se tiver como), identifique a causa, e corrija. Se o payload no walkthrough estava errado, corrija o walkthrough. Se o código do app estava errado, corrija o app. Atualize PT e EN.
```

### 7.3. Limpar contexto e recomeçar

```
Ignore todo o progresso desta sessão. Releia CLAUDE.md e ROADMAP.md do zero.

Meu pedido atual é: <refaça o pedido>.

Não tente recuperar estado de mensagens anteriores — comece como se fosse o primeiro turno.
```

---

## 8. Prompts de "pensamento" (não geram código)

Esses são úteis pra discutir o projeto antes de implementar.

### 8.1. Brainstorm de variantes pra um item do Top 10

```
Olhando a categoria OWASP A0<X> — <nome>, liste 5-8 variantes de vulnerabilidade que fariam bons átomos pro projeto (incluindo as que já estão no ROADMAP).

Pra cada uma:
- ID proposto
- Uma linha descrevendo o exploit principal
- Quão didático é de 1 a 5 (1 = muito abstrato, 5 = visual/impactante)
- Se vale ou não adicionar ao ROADMAP como átomo futuro

Objetivo: decidir se o ROADMAP atual cobre bem essa categoria ou se está faltando algo importante.
```

### 8.2. Avaliar dificuldade do próximo átomo

```
O próximo átomo do ROADMAP é `<id>`.

Me dê uma avaliação honesta:
- Quão complexa é essa vuln pra alguém que já fez os átomos anteriores?
- Há armadilhas de implementação (libs que mudam comportamento, features específicas de SGBD/runtime)?
- Quanto tempo realista de trabalho pra mim (validação + revisão)?
- Recomenda mudar a ordem, colocar antes outro átomo que prepare melhor?
```

### 8.3. Sanity check no tom/didática do walkthrough

```
Leia WALKTHROUGH.md do átomo `<id>` e critique com olhos de estudante de pentest que já passou da fase inicial (já fez uns 3-5 átomos).

Aponte:
- Passos que pularam explicação.
- Jargão sem definição.
- Partes onde o salto lógico é grande demais.
- Partes chatas ou redundantes.
- Partes que funcionam muito bem (pra eu replicar o padrão em outros átomos).

Não edite nada — só critique.
```

---

## Dicas gerais de uso

**Sempre que abrir uma sessão nova,** comece com o prompt 1.1 (onboarding). Custa 30 segundos e previne ~90% dos problemas de contexto.

**Quando pedir implementação de átomo,** sempre peça pra ele *propor antes de codar*. O custo de revisar uma proposta em texto é mínimo; o custo de refazer código gerado é alto.

**Quando ele errar,** aponte a regra específica do CLAUDE.md violada em vez de reclamar genericamente. Isso ensina o comportamento certo pra sessão inteira.

**Quando a conversa ficar muito longa,** salve progresso num arquivo `.md` no repo e comece sessão nova com o prompt 1.1. Contexto longo degrada qualidade.

**Quando pedir algo complexo,** peça em etapas: (1) entenda o problema, (2) proponha o plano, (3) implemente um pedaço, (4) valide comigo, (5) continue. Não "faça tudo de uma vez".
