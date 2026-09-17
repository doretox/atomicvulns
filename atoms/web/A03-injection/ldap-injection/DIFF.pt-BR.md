# DIFF — vulnerable vs. fixed

`vulnerable/app.py` e `fixed/app.py` diferem em exatamente dois pontos — um import adicionado e a linha que monta o filtro de busca. O `GET /` (o banner de aviso), a conexão LDAP e o bind da service account, o tratamento da resposta, o `Dockerfile` e o `requirements.txt` são idênticos entre as duas versões, assim como a imagem compartilhada `ldap/` e seu seed. (Este átomo é API-only — não há templates.)

## O fix — escapar os metacaracteres do filtro

```diff
+from ldap3.utils.conv import escape_filter_chars
 ...
     user = body.get("user", "")
     password = body.get("password", "")
-    # VULNERABLE: user/password are concatenated straight into the LDAP search
-    # filter. ... the metacharacters * ( ) \ are syntax, not data ...
-    filt = f"(&(uid={user})(userPassword={password}))"
+    # FIXED: escape the RFC 4515 filter metacharacters in every untrusted value
+    # before building the filter. * ( ) \ become literal data (\2a \28 \29 \5c) ...
+    filt = f"(&(uid={escape_filter_chars(user)})(userPassword={escape_filter_chars(password)}))"
     print("LDAP search filter:", filt, flush=True)
     conn = Connection(server, BIND_DN, BIND_PW, auto_bind=True)
     conn.search(PEOPLE_DN, filt, search_scope=SUBTREE, attributes=["uid"])
```

A view vulnerable concatena `user` e `password` direto na string do filtro. A view fixed passa cada valor antes pelo `escape_filter_chars`, que substitui os metacaracteres da RFC 4515 `*`, `(`, `)`, `\` (e NUL) pelas suas sequências de escape `\2a`, `\28`, `\29`, `\5c` antes de chegarem ao filtro. Um `*` mandado como senha deixa então de ser o curinga que transforma `(userPassword=<valor>)` num teste de presença — ele vira a busca literal `(userPassword=\2a)`, casando só uma conta cuja senha seja literalmente a string de um caractere `*` (não há nenhuma), então o login é recusado. O valor volta a ser casado como valor. O fix escapa **os dois**, `user` e `password`: ambos são controlados pelo atacante e ambos caem no filtro, então ambos são escapados no ponto de uso.

## Por que isso corrige o bug

Um filtro de busca LDAP é estrutura, e o `ldap3` manda a string de filtro que você entrega ao diretório verbatim — ele não escapa os valores interpolados por você. O app vulnerable monta o filtro a partir do input cru, então um metacaractere no input vira sintaxe do filtro. O app fixed garante que todo valor não-confiável é escapado antes de o filtro ser montado, então o filtro só pode ser o pretendido `(&(uid=<literal>)(userPassword=<literal>))` — duas igualdades literais, sem espaço para um curinga ou uma cláusula enxertada. O caso benigno fica inalterado: uma credencial real não tem metacaracteres, então escapar é um no-op e ela passa exatamente como antes. A causa raiz nunca foi o caractere que o atacante digitou; foi concatenar input não-confiável no filtro *como estrutura*, e escapar no ponto de uso é exatamente a negação disso.

## Validar ou colocar caracteres numa blocklist não é o fix

Um leitor experiente tem um fix na ponta da língua: "é input de usuário numa query — é só restringir os caracteres, proibir `*` e parênteses no campo `user`." Seja como uma blocklist de caracteres ruins ou uma allowlist dos bons, é a forma errada. Policiar o charset do input persegue a forma do ataque: encodings alternativos, um metacaractere que você esqueceu (`\`, NUL), um campo que legitimamente contém símbolos, o próximo input que você não pensou em filtrar. Você fica um bypass atrás, e quebra dado real que por acaso contém um símbolo.

Escapar é diferente em natureza: ele diz "seja lá o que este valor contém, trate tudo como dado", e vive no **ponto de uso** — o momento em que o valor é colocado no filtro — então não há nada a manter atualizado e nenhum input legítimo que ele rejeite. Escape no sink; não tente sanitizar a source. (Mesma forma das notas "mencionável, não aplicada" do `ssti-jinja` e do `nosql-injection-mongo`: nomeie o controle que o leitor busca e mostre por que não é o fix.)

## O desenho honesto é um bind, não "a busca casou"

Uma nota de desenho, porque é o fix mais profundo e tentador e este átomo de propósito o deixa de lado. Decidir a auth *buscando* `(&(uid=...)(userPassword=...))` e confiar que um match significa um login válido é frágil por si só — é o que deixa um truque no filtro virar um bypass de auth. A autenticação LDAP de verdade é um **bind**: o app conecta ao diretório *como o próprio DN do usuário* com a senha fornecida, e o sucesso desse bind *é* a checagem de senha. A injeção deste átomo — um metacaractere no filtro de busca — não consegue produzir um bypass contra um bind, porque o diretório verifica a senha ele mesmo em vez de contar hits de busca.

Então por que manter o desenho frágil e só escapar? Porque trocar para um bind muda o *desenho*, não a *vulnerabilidade*. Este átomo isola uma falha — input não-confiável concatenado num filtro — e sua negação mínima é escapar esse input. Reescrever o login para bind corrigiria a injeção só como efeito colateral de substituir o mecanismo inteiro, que é exatamente o tipo de mudança que borra qual é a lição. Nomeie o desenho melhor; mantenha o diff na causa. (Mesmo espírito da nota "hashing é ortogonal" do `nosql-injection-mongo`.)

## Mesma classe do NoSQL injection do Mongo — fix oposto

O finding é um bypass de autenticação: um login forjado como `admin` sem a senha, o que é account takeover. É o mesmo teto de um bypass de auth via SQL injection ou NoSQL injection — e vale pôr este átomo ao lado do `nosql-injection-mongo` (22), porque eles são parecidos em impacto e categoria e *nada mais*.

| Eixo | SQL injection (`sqli-union-basic`) | NoSQL injection (`nosql-injection-mongo`) | LDAP injection (este átomo) |
|---|---|---|---|
| Categoria | A03 — Injection | A03 — Injection | A03 — Injection |
| Query-language | SQL — uma string de comandos | uma query MongoDB — um documento JSON | um filtro de busca LDAP — uma string (RFC 4515) |
| Como o input vira estrutura | sintaxe emendada numa string (`' OR 1=1 --`) | mudança de tipo: uma string vira um objeto carregando um operador (`{"$ne": null}`) | metacaracteres numa string de filtro concatenada (`*` `(` `)` `\`) |
| O fix | parametrizar (bind variables) | forçar o tipo (rejeitar não-string) | escapar os metacaracteres da RFC 4515 |
| Escapar o input é o fix? | — | **não** — não há o que escapar; a injeção era um *tipo* | **sim** — o valor carregava *sintaxe* de filtro |

Leia essa última linha de ponta a ponta. No átomo do Mongo, escapar é justamente *não* ser o fix: a injeção era um valor que mudava de tipo para um operador, não havia string para escapar, e o fix era forçar o tipo. Aqui a injeção é um metacaractere dentro de uma string que o app concatenou, então escapar é *exatamente* o fix. Mesma classe — input não-confiável virando estrutura de query numa query-language que não é SQL — mas *como* o input vira estrutura decide o remédio, e o remédio que errou no 22 é o que acerta aqui. "Um átomo = uma vuln" é sobre a causa, não sobre o impacto: `sqli-union-basic`, `nosql-injection-mongo` e este átomo podem todos terminar numa query subvertida e num login bypassado, por três causas diferentes.
