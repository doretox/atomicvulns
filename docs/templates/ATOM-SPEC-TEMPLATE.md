# Template — Spec de Átomo

> Use este template para especificar qualquer átomo além do 01. O átomo 01 (`sqli-union-basic`) já estabeleceu os padrões estruturais — aqui só capturamos as decisões *específicas* deste átomo.
>
> Preenchimento alvo: ~10 minutos. Se estiver levando mais que isso, provavelmente há complexidade escondida que vale discutir antes de implementar.

---

## Identidade

- **ID:** `<categoria>-<variante>-<qualificador>`
- **Categoria OWASP:** A0X — <nome>
- **Pasta:** `atoms/A0X-<categoria>/<id>/`
- **Número sequencial:** NN (consulte ROADMAP.md)
- **Porta vulnerable:** `127.0.0.1:80NN`
- **Porta fixed:** `127.0.0.1:81NN`

---

## Classe de vulnerabilidade

Uma frase descrevendo a classe. Uma segunda frase explicando *por que esta variante específica* é interessante didaticamente (o que ela ensina que outras variantes não ensinam).

---

## Feature simulada

**Nome curto da feature** (ex: "Busca de produtos", "Upload de avatar", "Link de reset de senha").

2-3 frases descrevendo o que a app faz do ponto de vista do usuário legítimo. Sem jargão de segurança aqui — é a feature do ponto de vista de quem não sabe que ela é vulnerável.

**Tipo de átomo:** `[ ] com HTML` / `[ ] API-only` (ver Seção 3.3 do CLAUDE.md)

---

## Schema de dados (se aplicável)

Se o átomo usa banco, descreva as tabelas mínimas e o seed. Se não usa (ex: SSRF, path traversal), pular esta seção.

```sql
-- Tabelas
CREATE TABLE ...;

-- Seed (users/dados de exemplo)
INSERT INTO ... VALUES ...;
```

Lembrete: dados fake óbvios, prefixos tipo `sk_test_`, `fake_`, `dummy_`.

---

## Rotas

### `<MÉTODO> <path>`

Descrição em 1 frase + pseudocódigo da view vulnerável (≤15 linhas).

```python
@app.route('...')
def view():
    ...
```

Repita a seção se houver mais de uma rota.

---

## Fix

O que muda entre `vulnerable/` e `fixed/`. Idealmente um diff de 1-5 linhas. Uma frase explicando *por que* resolve.

```diff
- linha vulnerável
+ linha segura
```

---

## Walkthrough — payloads

Lista ordenada dos payloads que o aluno vai usar. Siga a estrutura de escalada didática (confirmar → explorar → extrair impacto máximo) sempre que a classe permitir.

1. **Step 1 — <nome curto>:** `<payload>` → o que o aluno observa
2. **Step 2 — <nome curto>:** `<payload>` → o que o aluno observa
3. **Step 3 — <nome curto>:** `<payload>` → o que o aluno observa

Se a vuln não comporta escalada (ex: open redirect), 1 passo só, sem forçar.

---

## Dependências extras

Se o átomo precisa de lib além do Flask, liste aqui com versão fixa. Pense duas vezes antes de adicionar — a regra da Seção 3.6 do CLAUDE.md é "só inclua se serve à falha ou ao fix".

```
Flask==3.0.0
<outra-lib>==X.Y.Z
```

---

## Decisões que podem gerar dúvida durante implementação

Se houver algo ambíguo (ex: "tokens JWT devem ter `exp` ou não?", "o endpoint deve retornar 401 ou 403 quando o fix bloqueia?"), capture aqui. Evita que o Claude Code improvise em momento crítico.

---

## Notas específicas pro Claude Code

Instruções adicionais que saem do padrão do átomo 01. Exemplos:

- "Este átomo é API-only, não há `templates/`."
- "Usar `requests` em vez de `urllib` pra ilustrar o pattern comum em apps reais."
- "O walkthrough precisa incluir uso do Burp Collaborator — documentar como configurar."

Se não há nada de especial, escrever "Nenhuma — seguir padrões do átomo 01."
