# DIFF — vulnerable vs. fixed

Diff unificado entre `vulnerable/app.py` e `fixed/app.py`. A única mudança é o formato de (de)serialização — `pickle` vira `json` (comentários abreviados):

```diff
-import pickle
+import json
 ...
     if cookie is None:
-        # First visit: serialize the default prefs (pickle + base64) and set the cookie.
-        raw = base64.b64encode(pickle.dumps(DEFAULT_PREFS)).decode()
+        # First visit: serialize the default prefs (JSON + base64) and set the cookie.
+        raw = base64.b64encode(json.dumps(DEFAULT_PREFS).encode()).decode()
         resp = make_response(render_template("index.html", theme=DEFAULT_PREFS["theme"]))
         resp.set_cookie("prefs", raw)
         return resp
-    # VULNERABLE: ... passed straight to pickle.loads ... -> code execution on load ...
+    # FIXED: ... JSON carries DATA ONLY ... json.loads cannot execute code ...
     try:
-        prefs = pickle.loads(base64.b64decode(cookie))  # RCE: attacker bytes -> code on load
+        prefs = json.loads(base64.b64decode(cookie))  # JSON: data only; no code path on load
         theme = prefs["theme"]
     except Exception:
         theme = DEFAULT_PREFS["theme"]
```

Todo o resto é byte-a-byte idêntico entre as duas versões: os imports `os`/`base64`, o `DEFAULT_PREFS`, o branch de primeira visita que seta o cookie, o `try/except` que cai no tema default, o `render_template`, o `__main__`, o `Dockerfile`, o `requirements.txt`, e o `templates/index.html`. O bug vive inteiramente no formato com que o cookie é (de)serializado.

## O que mudou

Três linhas, todas o mesmo swap: o import (`pickle` → `json`), a linha que *escreve* o cookie default (`pickle.dumps` → `json.dumps(...).encode()`), e a linha que o *lê* de volta (`pickle.loads` → `json.loads`). A perigosa é a leitura — `pickle.loads` no cookie controlado pelo atacante. A escrita só existe pra cada app ler o formato que escreveu; dar dump do dict *próprio* e confiável da app é inofensivo. É um fix *logic-different* isolado no formato de serialização — a menor expressão possível de "o formato é o bug inteiro".

O `try/except Exception` em volta da leitura é **idêntico nas duas versões** e não é o fix. Ele existe pra um cookie malformado degradar pras preferências default em vez de dar 500. Na app vulnerable ele tem um efeito colateral arrepiante: depois que o `pickle.loads` executa o comando do atacante, o valor reconstruído não é um dict, então `prefs["theme"]` levanta e o except cai silenciosamente no default — a página renderiza um `Theme: light` normal enquanto o comando já rodou. O RCE é silencioso.

## Por que isso resolve

A classe é: o `pickle.loads` reconstrói qualquer objeto que os bytes descreverem, e bytes de pickle podem descrever "chame esta função" — então bytes não-confiáveis viram código. O `json.loads` não tem esse poder: a gramática do JSON produz só primitivos — objetos/dicts, arrays/listas, strings, números, booleans, null. Nenhuma construção JSON nomeia um callable Python, então não há caminho de código a alcançar. Dê à app fixed o mesmo cookie malicioso de pickle e o `json.loads` simplesmente levanta uma exceção nos bytes não-JSON; o comando nunca roda. O caso benigno fica inalterado — o default `{"theme": "light"}` faz round-trip pelo JSON exatamente como fazia pelo pickle.

## A causa é o formato, não "validar o cookie"

É tentador arquivar isto como "input não-confiável — valide". Mas olhe o payload: no disassembly, é pickle *bem-formado* (`PROTO`, `STACK_GLOBAL` resolvendo `posix.system`, o reduce que o chama). Não há byte malformado pra rejeitar, nem metacaractere pra tirar — o exploit anda inteiramente dentro de pickle válido, conforme a spec. Você não "sanitiza" pra sair dessa, porque o perigo não é dado ruim; é que o formato *executa* o dado que recebe. Prova de isolamento: o cookie default benigno renderiza `Theme: light` idêntico nas duas apps; só um cookie cujo pickle carrega um `__reduce__` separa as duas, e as separa porque o `pickle.loads` o roda enquanto o `json.loads` não consegue.

## Dados vs. comportamento

Esta é a lição inteira, então diga direto. Um formato de **dados** (JSON) descreve *valores*: depois do `json.loads` você tem um dict, uma lista, uma string — inertes. Um formato de **comportamento** (pickle) descreve *como reconstruir um objeto*, e a reconstrução pode incluir chamar funções arbitrárias (é exatamente pra isso que serve o `__reduce__`). Desserializar input não-confiável com um formato de comportamento entrega ao atacante uma chamada de função. A regra durável: **nunca desserialize dado não-confiável com um formato que possa carregar comportamento** — o pickle, o `yaml.load` do `PyYAML` sem `SafeLoader`, e os serializadores nativos de outras linguagens compartilham essa forma. Quando o dado cruza uma fronteira de confiança, use um formato só-dados.

## Assinar o cookie não é o fix

Um leitor experiente já tem um fix pronto: "o cookie foi adulterado — assina com um HMAC (um hash com chave que detecta adulteração) pra um forjado ser rejeitado". Vale ser preciso sobre por que este átomo *não* faz isso.

Assinar ajuda em *algo*: torna o cookie tamper-evidente, então um pickle forjado é rejeitado antes de chegar ao `loads` — eleva a barra pra *este* caminho de entrega. Mas fecha o **sintoma** (adulterar *este* cookie), não a **causa**. A operação perigosa — `pickle.loads` em dado que cruzou uma fronteira de confiança — continua lá, guardada em vez de removida. Se a chave de assinatura vazar, é RCE na hora de novo (chaves vazam — o `ssti-jinja` revela uma `SECRET_KEY` do Flask direto da config da app). E se esses bytes chegarem ao `pickle.loads` por qualquer outra rota — um cache, uma fila de mensagens, um arquivo enviado, um segundo endpoint — a assinatura no cookie não protege nada disso. Você está confiando no sigilo da chave pra tornar seguro um primitivo inseguro, quando poderia simplesmente remover o primitivo inseguro.

Então assinar é defense-in-depth, não o fix de causa. Trocar o formato é o fix de causa: JSON não executa, com chave ou sem chave, com caminho ou sem caminho. A própria doc do `pickle` do Python traça exatamente essa linha — "consider signing data with hmac if you need to ensure that it has not been tampered with", mas "safer serialization formats such as json may be more appropriate if you are processing untrusted data". Este átomo está processando dado não-confiável, então troca o formato. (Mesmo movimento das notas "citada, não aplicada" do `ssrf-cloud-metadata`, `xxe-basic` e `ssti-jinja`: nomear o controle que o leitor buscaria, e mostrar por que ele não é o fix aqui.)

## O impacto é RCE — como command injection, por uma causa diferente

O finding é Remote Code Execution: um cookie adulterado roda comandos arbitrários no servidor. É o mesmo teto do `command-injection-basic`, o que vale pausar, porque os dois se parecem no impacto e em nada mais. Lá, a app monta uma string de comando de shell com o input do usuário e um shell a parseia — o fix é parar de invocar um shell (lista de argumentos, sem `shell=True`). Aqui nada monta um comando; o desserializador reconstrói um objeto e roda o comportamento embutido nos bytes — o fix é parar de usar um formato que carrega comportamento. Mesmo impacto, categoria diferente (A03 vs. A08), mecanismo diferente, fix diferente. "Um átomo, uma vulnerabilidade" é sobre a *causa*, não o impacto — assim como dois átomos podem terminar em file disclosure por raízes diferentes, estes dois terminam em RCE por raízes diferentes.
