# deserialization-pickle — Insecure deserialization

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Lab mínimo em Flask para insecure deserialization clássica — remote code execution através do `pickle` do Python. A app é uma página de "user preferences": ela guarda as suas preferências num cookie `prefs`, serializado com **pickle** (o serializador de objetos embutido no Python) e codificado em base64. A cada request, ela base64-decoda o cookie e chama `pickle.loads` nos bytes pra reconstruir as preferências. Mas você controla o seu próprio cookie — e o pickle não guarda só os *dados* de um objeto, guarda *instruções de como reconstruí-lo*, incluindo qual função chamar. Um cookie forjado cujo `__reduce__` nomeia `os.system` faz o `pickle.loads` rodar essa função durante o unpickle. A mesma página que mostra o seu tema salvo roda o comando do atacante.

Isto é A08 — Software and Data Integrity Failures: a app confia num blob serializado que cruzou uma fronteira de confiança e o reconstrói com um formato que carrega comportamento. Ela alcança o mesmo teto do `command-injection-basic` — remote code execution — mas por uma causa diferente: lá um shell executa o input do atacante; aqui o *próprio desserializador* executa o comportamento embutido nos bytes. O fix não é validar nem assinar o cookie — é trocar o **formato**: JSON carrega só dados, nunca comportamento, então o `json.loads` não tem caminho de código pra rodar. A única diferença entre `vulnerable/` e `fixed/` é `pickle` vs `json`.

> **Teoria primeiro:** Leia [PortSwigger: Insecure deserialization](https://portswigger.net/web-security/deserialization)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

A própria doc do Python é direta: o [módulo `pickle` "não é seguro"](https://docs.python.org/3/library/pickle.html) — "only unpickle data you trust".

## Como rodar

Da raiz do repo:

```bash
./atom up deserialization-pickle
```

- App vulnerable: <http://127.0.0.1:8020/>
- App fixed: <http://127.0.0.1:8120/>

Pare com `./atom down deserialization-pickle`. Se preferir Docker cru: `cd atoms/A08-data-integrity-failures/deserialization-pickle && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite.
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A app corrigida na porta 8120 atende a mesma página de "user preferences" e lê o mesmo cookie `prefs` — mas (de)serializa em JSON em vez de pickle. Rode o exploit do `WALKTHROUGH.pt-BR.md` contra ela: o mesmo cookie malicioso que roda um comando na app vulnerable não faz nada aqui — o `json.loads` rejeita os bytes de pickle, a página ainda renderiza `Theme: light`, e nenhum comando roda (o marcador `/tmp/pwned` nunca é criado). A única mudança em relação ao `vulnerable/` é o formato de serialização; veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md).
