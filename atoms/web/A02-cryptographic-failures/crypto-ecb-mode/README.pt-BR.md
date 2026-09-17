# crypto-ecb-mode — Encryption with an insecure mode of operation

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab Flask mínimo para a falha clássica de **modo** de uma cifra de bloco. A app te entrega um **crachá** (badge) de sessão — um token que carrega a sua identidade e o seu role — que ela cifra com **AES no modo ECB**. AES é uma *block cipher* (cifra de bloco): ela cifra blocos de tamanho fixo, de 16 bytes, e um **mode of operation** (modo de operação) é a regra pra encadear esses blocos ao longo de uma mensagem maior. O ECB (Electronic Codebook) é o ingênuo — ele cifra cada bloco de 16 bytes de forma *independente*, com a mesma chave. Duas consequências decorrem daí, e as duas são exploráveis: blocos de plaintext idênticos viram blocos de ciphertext idênticos (o padrão vaza) e — porque os blocos são independentes — você pode **recortar e colar** (cut-and-paste) blocos de ciphertext entre crachás pra forjar um plaintext que o servidor nunca emitiu. Você escala `role=user` pra `role=admin` sem nunca conhecer a chave.

Este é o irmão do [`crypto-weak-hash`](../crypto-weak-hash/), e o contraste é a lição. Os dois são **A02 — Cryptographic Failures** e os dois "parecem crypto", mas lá você ataca um *hash* mão-única de uma senha armazenada e **recupera** o input por pré-computação (uma rainbow table); aqui você ataca uma *cifra* reversível num *modo* quebrado e **forja** um plaintext novo rearranjando blocos — nada é recuperado e a chave nunca é quebrada. Ele também compartilha o objetivo — forjar um token de autoridade pra escalar privilégio — com os átomos JWT [`jwt-none-alg`](../jwt-none-alg/) e [`jwt-key-confusion`](../jwt-key-confusion/): lá a forja ataca a *assinatura* do token; aqui ela ataca o *modo de cifra* do token. O fix não é "trocar ECB por CBC" — é um modo **autenticado** (AES-GCM) que detecta qualquer bloco adulterado e rejeita o crachá.

> **Teoria primeiro:** Leia [OWASP: Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
> antes de fazer este átomo — a seção "Cipher Modes" dele é a lição: evite ECB,
> prefira modos autenticados (GCM). Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; o cheat sheet explica *o que* é cifragem
> segura e por que importa. (A PortSwigger Web Security Academy, fonte usual de
> primer deste repo, não tem página conceitual sobre modos de cifra, então este
> átomo aponta pra guia canônica da OWASP.)

## Nota de stack — single-container, sem banco de dados, dependências idênticas

Cada lado é um único container Flask sem datastore: o crachá é auto-contido (o servidor cifra a sua identidade e o seu role dentro dele), então não há nada pra semear nem sessão pra persistir — o mesmo formato stateless dos átomos JWT. E, diferente do `crypto-weak-hash`, cujo fix trouxe uma lib nova, aqui `vulnerable/` e `fixed/` compartilham um `requirements.txt` **idêntico** (Flask + pycryptodome). O fix é uma linha de código — o modo de cifra —, não uma dependência.

## Só API — sem HTML, sem browser

Não há UI web: sem templates, toda resposta é JSON. Você conduz este átomo inteiramente pelo **Burp Suite (Repeater + Decoder)** — lê o crachá de uma resposta de login, recorta e rearranja os blocos de ciphertext, e reenvia. A prova é a resposta HTTP (`GET /me` respondendo como admin). Não há ferramenta offline — nada é quebrado, a chave nunca é tocada — e não há trilha browser.

O crachá é **hex-encoded**, então cada bloco de 16 bytes tem exatamente 32 hex chars. As fronteiras de bloco caem no caractere, o que mantém o cut-and-paste factível à mão no Repeater — sem ida-e-volta de Base64.

## Como rodar

A partir da raiz do repo:

```bash
./atom up crypto-ecb-mode
```

- API vulnerável: `http://127.0.0.1:8032`
- API corrigida: `http://127.0.0.1:8132`

Não há página inicial além de um banner JSON em `/` — os pontos de entrada são `POST /login` (pega um crachá) e `GET /me` (gasta ele), documentados no `WALKTHROUGH.md`. Pare com `./atom down crypto-ecb-mode`. Se preferir Docker puro: `cd atoms/A02-cryptographic-failures/crypto-ecb-mode && docker compose up --build`.

## O que ler em seguida

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo no Burp: veja o padrão vazando (dois blocos de ciphertext idênticos), extraia um bloco `admin` de uma resposta de login, cole ele por cima do bloco `user`, e veja o `GET /me` tratar o crachá forjado como admin. Depois o mesmo crachá é rejeitado sob GCM. Sem browser.
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão corrigida

A API corrigida na porta 8132 cifra o crachá com **AES-GCM**, um modo autenticado — mesma chave, mesmos endpoints, só o modo muda. O GCM adiciona um **nonce** novo por mensagem (então dois crachás idênticos deixam de parecer idênticos — o padrão para de vazar) e uma **tag** de autenticação que liga o ciphertext. O crachá recombinado que te logou como admin na 8032 falha a checagem da tag e é rejeitado com `400` **antes de o role ser lido**. Veja o [`DIFF.md`](./DIFF.md) pra entender por que "só trocar por CBC" é uma melhora real, mas parcial — não o fix — e por que o problema nunca foi a chave nem o AES em si.
