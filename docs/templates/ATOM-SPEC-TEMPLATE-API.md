# Template — Spec de Átomo (série API)

> Use este template para especificar qualquer átomo da **série API** (`atoms/api/`) — TypeScript / Express / `tsx`, containerizado, **API-only por natureza**. Para átomos da série web (Python/Flask), use o template irmão [`ATOM-SPEC-TEMPLATE-WEB.md`](./ATOM-SPEC-TEMPLATE-WEB.md).
>
> O átomo 01 da série API (`bola-sequential-id`) é o **átomo-bandeira** e a **referência de estilo TS/Express**: uma vez implementado, ele estabelece os padrões estruturais (forma do `app.ts`, do `package.json`/`tsconfig.json`, do `Dockerfile`, do WALKTHROUGH/DIFF/README) que os demais só *ajustam*. Enquanto ele não existe, o formato segue este template + `CLAUDE.md` §3 (a stack é lei da série).
>
> Preenchimento alvo: ~10 minutos. Se estiver levando mais que isso, provavelmente há complexidade escondida que vale discutir antes de implementar.
>
> **Herança da série (não repetir por átomo — já é lei):** stack TS/Express/`tsx`; imagem base **Node 24 slim, tag pinada — nunca `latest`**; `vulnerable/` e `fixed/` são build-contexts Docker **self-contained** (cada um com seu `package.json` + `tsconfig.json`, **sem módulo compartilhado**); **sem `templates/`, sem HTML, sem browser** (respostas JSON); bind **`127.0.0.1`**; docs **EN + PT sincronizadas**; **Theory primer** obrigatório. Este template captura só as decisões *específicas* deste átomo.

---

## Identidade

- **ID:** `<categoria>-<variante>-<qualificador>` (kebab-case, inglês, único no repo inteiro)
- **Categoria OWASP (API Security Top 10 2023):** APIX — `<nome>`
- **Pasta:** `atoms/api/APIX-<categoria>/<id>/`
- **Número sequencial (série API, conta do 01):** NN (consulte `atoms/api/ROADMAP.md`)
- **Porta vulnerable:** `127.0.0.1:82NN`
- **Porta fixed:** `127.0.0.1:83NN`
- **Porta interna do container:** `<PORT>` (idiomática do Node; ex.: 3000) — o compose mapeia `127.0.0.1:82NN:<PORT>` / `127.0.0.1:83NN:<PORT>`
- **H1 dos READMEs (idêntico em EN e PT):** `# <id> — <Nome canônico da CLASSE>` (o título nomeia a classe; o slug qualifica a variante — CLAUDE.md §5)
- **Branch de trabalho:** `atom/<id>`

> `NN` é a sequência da série API (átomo 01 → 8201/8301). Cada série conta do próprio 01; não se renumera nada (CLAUDE.md §5, "Portas convencionadas").

---

## Classe de vulnerabilidade

Uma frase descrevendo a classe. Uma segunda frase explicando *por que esta variante específica* é interessante didaticamente (o que ela ensina que outras variantes não ensinam).

Situe a vuln na **APIX** da OWASP API Security Top 10 **2023** quando a categoria ancora a lição (ex.: "API1 — Broken Object Level Authorization"). **Sem arqueologia** de edições antigas (CLAUDE.md §5).

---

## Feature simulada

**Nome curto da feature** (ex.: "Listagem de pedidos", "Perfil de conta", "Webhook de callback").

2-3 frases descrevendo o que a API faz do ponto de vista do cliente legítimo. Sem jargão de segurança aqui — é a feature do ponto de vista de quem não sabe que ela é vulnerável.

> **API-only por natureza.** A série API não tem UI: sem `templates/`, sem HTML, sem browser. Toda resposta é JSON (`res.json(...)`). A interação é 100% **Burp (Repeater/Intruder) ou `curl`**. Não se inventa frontend para átomo de API (CLAUDE.md §3.3).

---

## Autenticação

Descreva o modelo de identidade deste átomo. Padrão da série:

- **Token opaco via `POST /login`**, **replicado por átomo** (sem módulo compartilhado). O login recebe o usuário e devolve `{ "token": "<opaco>" }`; o servidor guarda um mapa `token → usuário` em memória e resolve por lookup. **NÃO é JWT** (a menos que o átomo seja especificamente sobre JWT).
- **O token DEVE ser gerado com aleatoriedade criptográfica** (`crypto.randomBytes(...)`), **mesmo quando não é o objeto de estudo**. Um token previsível num átomo que não é sobre isso seria uma **segunda vulnerabilidade** e violaria "um átomo = uma vuln" (CLAUDE.md §2).
- **Autenticação vs. autorização:** deixe explícito o que a autenticação prova (*quem você é*) e o que ela **não** prova (*se este objeto/ação é seu*), quando a distinção for a lição.

Liste os usuários seedados e seus papéis (ex.: atacante/você + vítima(s)). Sem senha real, sem PII real — dado fake óbvio (CLAUDE.md §8.3).

> **Exceção:** se o átomo é sobre a *própria* autenticação (ex.: token previsível, ausência de lockout), o modelo de auth **é** a superfície do bug — descreva a falha aqui, não a mitigue.

---

## Store / dados (se aplicável)

Store **em memória** por padrão (estruturas TS: `Map`, `Record`, array) — a série recorre a um banco só quando a vuln exige (CLAUDE.md §3.4). Descreva as estruturas mínimas e o seed.

```ts
type <Entity> = { /* campos mínimos */ };
const <STORE>: Record<number, <Entity>> = { /* seed */ };
```

Lembrete: dados fake óbvios — endereços/nomes claramente de teste (`Example Ave`, `Faketon`), prefixos `sk_test_`, `fake_`, `dummy_`. **Sem PII real, sem credencial real, sem segredo real** (CLAUDE.md §8.3).

---

## Rotas

Imports necessários no topo (ex.: `import express from "express";`, `import { randomBytes } from "node:crypto";`). Constantes e helpers **idênticos** entre `vulnerable/` e `fixed/`.

### `<MÉTODO> <path>`

Descrição em 1 frase + pseudocódigo do handler (Express). **Handler vulnerável ≤ ~30 linhas** (CLAUDE.md §2.2).

```ts
app.<method>("<path>", (req, res) => {
    // ...
});
```

Repita a seção por rota. Marque claramente qual é a rota **vulnerável** e qual(is) é(são) **correta(s) nas duas versões** (o baseline honesto).

> **Bind do servidor:** `app.listen(PORT, process.env.HOST ?? "127.0.0.1")` — default `127.0.0.1` (CLAUDE.md §8.1); o container sobrescreve com `ENV HOST=0.0.0.0` para o forwarding do Docker alcançar o Express, com exposição host restrita a `127.0.0.1` pelo compose.

---

## Fix

O que muda entre `vulnerable/` e `fixed/`. Idealmente um diff de 1-5 linhas, **em um eixo só**. Uma frase explicando *por que* resolve.

```diff
- linha vulnerável
+ linha segura
```

Se a classe é de **lógica/autorização** (BOLA, BFLA, BOPLA, mass assignment), diga qual é a *leitura correta* do fix — não "acrescentou um if", mas *o que a operação passou a garantir*. Registre a escolha de **status code** e por quê (ex.: 404 indistinguível vs. 403 explícito; ancore no RFC 9110 / mundo real quando a existência do objeto for sensível).

---

## Padrão de prova — Payload vs Trigger

Marque como o átomo prova a falha (premissa da série — `atoms/api/ROADMAP.md`):

- `[ ] **Payload**` — o exploit *é* um input criado que o servidor manuseia mal (injection, SSRF, deserialization). A demonstração carrega o significado.
- `[ ] **Trigger**` — não há sink; o exploit é uma **ação legítima com efeito observável** (BOLA, BFLA, mass assignment, resource abuse). Trocar um id, reordenar uma chamada, mudar um campo, repetir uma request.

> **Classes de lógica → Trigger → passo de contraste OBRIGATÓRIO.** Quando a prova é dado legítimo (não um payload), o aluno corre o risco de internalizar a forma errada do bug (ex.: achar que BOLA é "impersonation" em vez de "check de autorização ausente"). Inclua um passo no walkthrough que **isole a causa real**, frequentemente demonstrando o que a vuln **NÃO é** (CLAUDE.md §5, "Vulns de lógica precisam de um passo 'o que a vuln NÃO é'").

---

## Walkthrough — requests

Lista ordenada dos requests que o aluno vai enviar. **Trilha 100% Burp/curl — SEM browser** (a série é API-only; CLAUDE.md §3.3). Cada request é um bloco colável no Repeater: request-line + headers (`Authorization: Bearer <token>`) + corpo JSON quando houver. Tokens/ids que variam por boot/login são **placeholders** (`<attacker-token>`).

Siga a escalada didática (confirmar → explorar → extrair impacto máximo) quando a classe permitir:

1. **Baseline:** a API funcionando como projetada (login, escopo correto).
2. **Exploit:** o request que dispara a falha.
3. **Passo de contraste (obrigatório em vulns de lógica):** requests que isolam a causa e desmontam o mal-entendido vizinho.
4. **Impacto máximo:** quando a classe comporta (ex.: enumeração no Intruder), a varredura que separa "um objeto vazou" de "a base vazou".
5. **Fix:** repetir a mesma sequência contra o gêmeo `fixed/` (porta 83NN) — o que muda na resposta é a prova do fix.

> O walkthrough **termina onde a falha foi mostrada e o fix explicado**. Sem seção de exercícios/variações, sem script de exfiltração, sem automação além do necessário (CLAUDE.md §5).

---

## Anatomia dos gêmeos

Cada gêmeo (`vulnerable/` e `fixed/`) é um build-context Docker **self-contained**:

```
<id>/
├── vulnerable/
│   ├── Dockerfile
│   ├── app.ts            # app Express mínima, vulnerável
│   ├── package.json      # próprio (sem módulo compartilhado)
│   └── tsconfig.json     # próprio
├── fixed/                # mesma forma; só o eixo do fix muda em app.ts
├── docker-compose.yml    # sobe vulnerable (82NN) + fixed (83NN), bind 127.0.0.1
├── README.md / README.pt-BR.md
├── WALKTHROUGH.md / WALKTHROUGH.pt-BR.md
├── DIFF.md / DIFF.pt-BR.md
└── burp/                 # opcional: requests exportados do Burp
```

- **`Dockerfile` idêntico entre as versões** (só o build-context difere). Base `node:24-slim` (tag pinada — nunca `latest`), `ENV HOST=0.0.0.0`, `EXPOSE <PORT>`.
- **`docker-compose.yml`** com duas services, bind **só** em `127.0.0.1`.

---

## Dependências extras

Mínimo possível (CLAUDE.md §3.6 — só inclua a lib se serve à falha ou ao fix). Base da série:

```json
{
  "dependencies": { "express": "<5.x pinada>" },
  "devDependencies": {
    "tsx": "<pinada>",
    "@types/express": "<5.x pinada>",
    "@types/node": "<24.x pinada>"
  }
}
```

Sem `requirements.txt` (isso é a série web). Versões **pinadas** e confirmadas na geração (CLAUDE.md §8.7 — updates manuais). Adicione libs além destas só se a vuln/fix exige.

---

## Theory primer

CLAUDE.md §5 exige um bloco de Theory primer no topo do `README.md` e do `README.pt-BR.md` (após título+descrição, antes de "How to run"), linkando pra **página conceitual** da vuln na **PortSwigger Web Security Academy** (a que começa com "What is X?", **não** a listagem de labs).

**BUSQUE a URL real e verifique que existe — NUNCA invente. Se não conseguir verificar, pergunte ao mantenedor.** Use a forma do nome como a própria PortSwigger apresenta (não traduza pro PT).

Formato EN:

```markdown
> **Theory primer:** Read [PortSwigger: <Nome da vuln>](<URL exata>)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato PT:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: <Nome da vuln>](<URL exata>)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

Referência suplementar (opcional, na descrição do README): a página oficial **APIX:2023** da OWASP API Security, quando ancora "onde a vuln cai no Top 10 de API". Também confirmar por fetch.

---

## Segurança e sincronização (checklist herdado — validar sempre)

- **Banner de aviso** no topo de todo README: `⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.`
- **Bind `127.0.0.1`** no `docker-compose.yml` e no `app.listen(...)` (default 127.0.0.1).
- **Dado fake óbvio**, sem PII/credencial/segredo real (CLAUDE.md §8.3).
- **Docs EN + PT sincronizadas no mesmo commit.** Headers de seção **traduzidos** no PT — nenhum header PT byte-idêntico ao par EN, **exceto** o h1 do README. Termos técnicos (BOLA, token, Bearer, payload, sink, enumeration oracle) seguem em **inglês** dentro do texto PT.

---

## Decisões que podem gerar dúvida durante implementação

Capture aqui qualquer ambiguidade (ex.: "o fix retorna 401 ou 404?", "o store é `Map` ou `Record`?", "id parseado com `Number()` — não-numérico vira 404?"). Evita que o Claude Code improvise em momento crítico.

---

## Notas específicas pro Claude Code

Instruções que saem do padrão da série. Exemplos:

- "Primeiro átomo TS do repo — **não há** átomo TS in-repo pra espelhar; estabeleça o padrão seguindo este template + CLAUDE.md §3."
- "O handler vulnerável **chama** `authenticate()` mas descarta a identidade — não transformar isso em 'falha de autenticação'."
- "Cross-ref: só átomos **já publicados**. Se nenhum átomo de API está publicado, **não** cite outro átomo de API; contraste com átomos **web** publicados é bem-vindo (CLAUDE.md §5, 'Referências cross-átomo')."

Se não há nada de especial, escrever "Nenhuma — seguir padrões da série API e do átomo-bandeira `bola-sequential-id`."
