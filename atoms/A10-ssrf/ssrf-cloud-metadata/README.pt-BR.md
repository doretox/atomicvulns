# ssrf-cloud-metadata — Cloud metadata SSRF (IAM credential theft)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab Flask mínimo para o alvo de SSRF de maior impacto na cloud. A app expõe uma feature "Fetch from URL" — você envia uma URL, o servidor a busca e te devolve o corpo da resposta. O servidor nunca valida qual URL foi pedido, então a mesma feature que faz preview de `https://api.github.com/zen` pode ser apontada para `http://169.254.169.254/` — o **cloud metadata endpoint** (o IMDS) que toda instância AWS/GCP/Azure carrega. Um `GET` simples e não-autenticado ali devolve as **credenciais IAM de sessão** da instância, e a app ecoa isso direto de volta para você.

Este é o terceiro átomo de SSRF, e ele fecha o arco que `ssrf-basic` e `ssrf-blind-oob` abriram. No `ssrf-basic` o servidor buscava sua URL e te entregava o corpo de um serviço interno genérico; no `ssrf-blind-oob` a resposta não dizia nada e você confirmava a requisição out-of-band. Aqui o mecanismo é o mesmo do `ssrf-basic` — buscar e mostrar, in-band — mas o *alvo* é o que paga e o *impacto* é roubo de credencial. A escalada sobre o `ssrf-basic` não é a visibilidade (os dois são in-band); é o **alvo** (o metadata endpoint) e o **impacto** (roubo de credencial IAM levando a account takeover na cloud). Mesmo primitivo, apontado para o crown-jewel.

> **Teoria primeiro:** Leia [PortSwigger: Server-side request forgery (SSRF)](https://portswigger.net/web-security/ssrf)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

Do lado do alvo, a AWS documenta o serviço que este átomo mocka: [Use instance metadata to manage your EC2 instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html). O path `iam/security-credentials/<role>` devolve as credenciais de segurança **temporárias** do role da instância, sem autenticação — que é exatamente o que um SSRF para `169.254.169.254` leva embora.

## Estrutura do lab — três containers

Este é um átomo multi-container, como os outros dois átomos de SSRF. Três serviços sobem sob um único `docker-compose.yml`:

- **`vulnerable`** — a app "Fetch from URL" quebrada, publicada em `127.0.0.1:8017`.
- **`fixed`** — a versão corrigida, publicada em `127.0.0.1:8117`.
- **`metadata-mock`** — um fake IMDS respondendo no **IP link-local real `169.254.169.254`** — o endereço exato que o metadata service usa numa instância AWS/GCP/Azure de verdade, então o payload que você digita é idêntico ao real. Ele serve a superfície mínima que um atacante de SSRF percorre: o nome do role IAM, depois as credenciais do role em JSON. **As credenciais são os valores placeholder `…EXAMPLE` documentados pela AWS — obviamente falsas, nenhum segredo real.** Ele **não** é publicado no host (sem `ports:`); `curl http://169.254.169.254/` da sua máquina não o alcança. Ele só é alcançável de dentro da rede Docker que o lab cria. Não há banco de dados; o único estado são as credenciais estáticas e falsas do mock.

**Uma nota sobre a topologia.** Os outros dois átomos de SSRF põem o serviço extra em *duas* redes Docker e o alcançam por nome DNS. Este átomo, em vez disso, fixa o mock no IP `169.254.169.254` — porque esse IP exato *é* a lição. Um único endereço só pode viver numa subnet, então aqui os três containers compartilham **uma** rede. O que importa fica preservado: o mock é alcançável de **ambos** `vulnerable` e `fixed` no nível de rede, então quando a app fixed recusa, essa recusa é o **código da aplicação** (a allowlist) — não a rede — exatamente como no `ssrf-basic`.

## Como rodar

Da raiz do repo:

```bash
./atom up ssrf-cloud-metadata
```

- App vulnerável: <http://127.0.0.1:8017/>
- App corrigida: <http://127.0.0.1:8117/>
- Metadata mock: não publicado — alcançável só através da app vulnerável ou corrigida, em `http://169.254.169.254/`.

Pare com `./atom down ssrf-cloud-metadata`. Se preferir Docker puro: `cd atoms/A10-ssrf/ssrf-cloud-metadata && docker compose up --build`.

## O que ler em seguida

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo via Burp Suite (principal) e browser (secundária).
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão corrigida

A app corrigida na porta 8117 valida o destino **antes** de buscar, contra uma allowlist deny-by-default de hosts vetados, decidida sobre o host parseado (`urllib.parse.urlparse(...).hostname`), não sobre um substring do raw URL. Repita cada payload do `WALKTHROUGH.md` contra ela: um `https://api.github.com/zen` legítimo ainda devolve o mesmo corpo de antes, mas toda URL apontando para `http://169.254.169.254/…` devolve **403 Forbidden** em vez de buscar — sem nome de role, sem credenciais. O container `metadata-mock` continua alcançável do container `fixed` no nível de rede; o fix está no código da aplicação, não na fiação de rede. O fix é uma **lista positiva**, não um blocklist de `169.254.0.0/16`: um blocklist perde para IPs em decimal/hex/IPv6-mapped, truques de userinfo, redirects e DNS rebinding, enquanto uma allowlist rejeita qualquer coisa não vetada. Veja [`DIFF.md`](./DIFF.md) para o porquê, e para a nota sobre IMDSv2 — o hardening do lado da cloud que este átomo descreve mas não aplica.
