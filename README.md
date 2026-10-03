# Arquitetura do Impossível — site

Site do canal **@ArquiteturadoImpossível**, em `arquiteturadoimpossivel.com` (desde 03/10/2026; o `.com.br` redireciona).
Estático, sem framework e sem build no servidor — o mesmo fluxo do Vestígio
Oculto e do viagemnalupa: gera aqui, commit e push no GitHub, e a Hostinger
publica sozinha.

## Como gerar

```bash
python _src/build.py
```

Nunca edite `index.html`, `obras/*.html` nem `404.html`: são gerados.

## De onde vem o conteúdo

Cada obra é um JSON em `_src/obras/NN-slug.json` (esquema em
`_src/obras/ESQUEMA.md`). **Nenhum texto de obra mora em template.** O JSON
sai da apuração do episódio, que é a fonte:

```
Canais do YouTube\Arquitetura do Impossível\Roteiros\NN Tema\VERIFICACAO.md
```

Se o site e o vídeo divergirem, quem manda é a apuração — corrija o JSON a
partir dela, nunca o contrário.

As fotos saem de `material\foto\` do episódio, com autor e licença do
`MANIFESTO`. Entram domínio público, CC0, CC BY e CC BY-SA. **NC e "No known
copyright restrictions" não entram**, e o build para se aparecerem.

## Nova obra

1. Escreva `_src/obras/NN-slug.json` seguindo o esquema.
2. Ponha as fotos em `assets/img/NN-nome.jpg` (1600 px, JPEG 82) e
   `NN-nome-800.jpg`.
3. No JSON da obra anterior, aponte `proximo` para o novo slug.
4. Se a obra estava em `EM_APURACAO` no `_src/build.py`, tire de lá.
5. `python _src/build.py`.

## O build é porteiro

Ele para, sem gerar nada, quando:

- falta campo obrigatório no JSON, ou `proximo` aponta para obra inexistente;
- uma imagem citada não existe em `assets/img`;
- a licença de uma imagem não é aceita;
- o texto público carrega bastidor de produção (`VERIFICACAO`, "a apurar",
  `[2+]`, nome de arquivo…) — no canal isso já saiu em rodapé de cartela.

## Selo de confiança

Cada número da página leva um selo, o mesmo grau da apuração:
**2+ fontes** · **1 fonte** · **diverge** (mostramos as versões, não
escolhemos) · **sem registro** (ninguém registrou; dizemos isso).

## Data de estreia

Os quadros mostram "Estreia DD mmm AAAA" e viram "No ar" sozinhos no dia,
por um script na página — não é preciso regerar o site para isso.

## Identidade

Da `Identidade Visual\` do canal: cianotipia `#0F2A44` com grade de
prancheta, giz `#E9EEF0`, concreto `#8E9AA3`, viga `#2B5C87` e o **amarelo
de obra `#F2B705` como acento único**. Barlow Condensed nos títulos, IBM Plex
Mono nas cotas e IBM Plex Sans no corpo. Fontes servidas daqui
(`assets/fontes/`, SIL OFL), sem Google Fonts. O único serviço de terceiros
é o AdSense (seção abaixo).

O símbolo (triângulo de Penrose) vai inline a partir de
`_src/marca/simbolo-escuro.svg`; no cabeçalho e no favicon, sem a cota.

## AdSense

Mesma conta e mesmo publisher do Vestígio Oculto: `pub-4401770243539507`.
Tudo sai de três constantes no topo do `_src/build.py`:

- `ADSENSE_LIGADO` — interruptor geral. `False` tira a meta e a faixa de
  todas as páginas e apaga o `ads.txt`.
- `ADSENSE_PUB` — o publisher; o `ads.txt` é gerado a partir dele.
- `CONSENTIMENTO_BLOQUEIA` — `False` (igual ao Vestígio): o anúncio carrega
  na hora e quem clica em "Recusar anúncios" deixa de receber. `True`: nada
  de anúncio até "Entendi".

O `<head>` de cada página leva só a meta `google-adsense-account` (é por ela
que o AdSense verifica o site). O script `adsbygoogle.js` **não** vai escrito
no HTML: a faixa de consentimento o injeta, e só quando pode. Os anúncios
são os automáticos, configurados no painel do AdSense — não há bloco de
anúncio posicionado à mão.

A página `privacidade.html` é gerada pelo build e descreve só o que este site
faz. Mudou algo (outra rede, medição, comentários): muda o texto e a data.

## Publicar

**No ar desde 02/10/2026.** Domínio principal desde 03/10/2026:
**https://arquiteturadoimpossivel.com** (sem www). O `arquiteturadoimpossivel.com.br` e o `www.arquiteturadoimpossivel.com`
estão estacionados na Hostinger no MESMO site — servem os mesmos arquivos — e
o `.htaccess` os redireciona 301 para o .com (seção "Domínio" abaixo).

Repositório: https://github.com/allangipa/Arquitetura-do-Impossivel, branch
`main`. **Cada push na `main` publica o site** — o Git do painel da Hostinger
(Sites → arquiteturadoimpossivel.com.br → Avançado → Git, diretório = raiz; o site no painel continua com o nome do domínio original)
puxa o commit e põe no ar em cerca de 15 segundos.

```bash
python _src/build.py
git add -A
git commit -m "o que mudou"
git push
```

**Rode o build antes do commit.** O servidor não gera nada: ele publica os
`.html` que estão no repositório. Mudou um JSON e não rodou o build, o site
continua com o texto velho — sem erro nenhum.

E confira no ar, não no terminal: abra a página que mudou (ou
`curl -s https://arquiteturadoimpossivel.com/obras/<slug>.html | grep "<trecho novo>"`).
O push dar certo não prova que o deploy deu.

### O que o `.htaccess` segura

Com o deploy por Git o repositório **inteiro** vai para o servidor, não só o
site. O `.htaccess` é o que impede o resto de ser servido:

- `404.html` como página de erro;
- 404 para `_src/`, `.claude/`, `.git/`, `README.md` e `.gitignore`;
- o 301 de domínio (seção "Domínio").

Arquivo novo na raiz que não seja página (nota, script, planilha) **fica
público** até entrar nessa lista. Na dúvida, ponha dentro de `_src/`.

### Publicação por pacote (só se o Git falhar)

A primeira publicação, antes de o Git ser ligado, foi por pacote, pelo plugin
da Hostinger no Claude Code: zip só com o que é servido (`index.html`,
`404.html`, `favicon.svg`, `robots.txt`, `sitemap.xml`, `.htaccess`, `obras/`
e `assets/`), envio para `public_html` e "deploy static site archive".
**Esse deploy apaga a pasta inteira do site antes de extrair**: o pacote vai
sempre completo, nunca só o que mudou.

## Domínio: .com principal, .com.br redireciona (03/10/2026)

`DOMINIO` no `_src/build.py` é `https://arquiteturadoimpossivel.com`: canonical, og:url,
JSON-LD, sitemap e robots saem dele. O `ads.txt` não muda (não tem domínio).

O `.htaccess`, antes das regras de 404, redireciona **301, caminho a caminho
e com a query string**:

| pedido | vai para |
|---|---|
| `http(s)://arquiteturadoimpossivel.com.br/<caminho>` | `https://arquiteturadoimpossivel.com/<caminho>` |
| `http(s)://www.arquiteturadoimpossivel.com.br/<caminho>` | `https://arquiteturadoimpossivel.com/<caminho>` |
| `http(s)://www.arquiteturadoimpossivel.com/<caminho>` | `https://arquiteturadoimpossivel.com/<caminho>` |
| `http://arquiteturadoimpossivel.com/<caminho>` | `https://arquiteturadoimpossivel.com/<caminho>` |

Só esses hosts: o domínio temporário da Hostinger e qualquer outro ficam como
estão. A regra de 404 para `_src/`, `.git/` etc. continua valendo (no .com.br
o pedido primeiro vira 301 para o .com, e lá dá 404).

Para conferir as regras sem servidor: `python _src/testa_htaccess.py .htaccess arquiteturadoimpossivel`
(emula o mod_rewrite com os casos acima). Depois de publicar, no ar:

```bash
curl -sI https://arquiteturadoimpossivel.com.br/obras/cristo-redentor.html | grep -i "^location"
curl -sI http://www.arquiteturadoimpossivel.com/ | grep -i "^location"
```

**Antes do push com esta regra, o SSL do .com e do www.com tem de estar ativo**
no painel (SSL → instalar para o domínio estacionado): o 301 manda para https.

## Idiomas (03/10/2026)

Português na **raiz**, com os caminhos de sempre (`/obras/<slug>.html`,
`/temas/<slug>.html`) — nenhuma página em português mudou de endereço. Cada
outro idioma ganha uma pasta com **os mesmos slugs**: `/en/obras/<slug>.html`,
depois `/es/`. A lista mora em `IDIOMAS = ["pt", "en", "es"]` no build; só
fica no ar o idioma que tem dicionário **e** pelo menos uma obra traduzida.

O que existe em cada idioma decide tudo sozinho:

- `<html lang>` (`pt-BR`, `en`, `es`) e `og:locale` (+ `og:locale:alternate`);
- `hreflang` em toda página que existe em mais de um idioma: `pt-BR`, `en`,
  `es` e `x-default` (inglês quando existe, senão português), recíproco;
- o **sitemap** (um só) lista cada versão com os `xhtml:link` alternates;
- o **seletor de idioma** no cabeçalho (PT · EN · ES) mostra só os idiomas
  em que **aquela** página existe, e fica visível no celular;
- links internos: na página em inglês, link para uma obra que ainda não
  tem inglês cai na versão em português (com `hreflang="pt-BR"`), nunca num 404;
- a home de cada idioma lista só as obras traduzidas e avisa quantas
  ainda estão só em português.

Marca no inglês: **"Arquitetura do Impossível — Impossible Architecture"**
(`marca_sub` em `_src/i18n/en.json`; aparece no cabeçalho, no rodapé, no
`og:site_name` e como `alternateName` no JSON-LD). No espanhol (no ar desde
03/10/2026, `_src/i18n/es.json`): **"Arquitetura do Impossível — Arquitectura
de lo Imposible"**. O `<title>` continua com o nome em português no fim, para caber
em 60.

Sobre, contato e privacidade existem em português, inglês e espanhol (o texto
mora no build: `PRIVACIDADE`/`PRIVACY_EN`/`PRIVACIDAD_ES`, `SOBRE_PT`/`ABOUT_EN`/`ACERCA_ES`,
`CONTATO_PT`/`CONTACT_EN`/`CONTACTO_ES`, e o título/description em `FIXAS_SEO`).
Idioma fora de `FIXAS_IDIOMAS` cai nas páginas em português. **As privacidades
em inglês e em espanhol dizem exatamente o que a portuguesa diz**: mudou uma,
mude as outras. O 404 é um só, em português.

Espanhol: as 33 obras em `_src/obras/es/` e os temas em `_src/temas.es.json`.
A conferência de números trata o espanhol como o português (`1.145`, `3,75`);
"bilhão" é **"mil millones"** (nunca "billón", que é 10¹²). A trava de bastidor
só pega `TODO` em caixa alta (em espanhol "todo" é palavra comum) e
"pendiente de verificar/confirmar" (sozinho, "pendiente" também é declive).

### Traduzir uma obra (o fluxo)

1. Copie `_src/obras/NN-slug.json` para `_src/obras/en/NN-slug.json`
   (mesmo nome de arquivo) e traduza **os textos**. Os campos fixos
   (num, slug, regiao, estreia, proximo, relacionados, conf, arquivo, licenca, licenca_url, origem_url, recriacao, foco, url) podem ser apagados: vêm do original. Exemplo pronto:
   `_src/obras/en/01-cristo-redentor.json`.
2. Tradução fiel: nenhum fato novo, nenhuma conversão de unidade, divergência
   continua divergência, atribuição continua atribuição ("segundo X").
   Número por extenso fica por extenso; algarismo fica algarismo.
3. `python _src/build.py`. O build **para** se: faltar campo ou item de lista;
   um número do original não aparecer na tradução (ou aparecer um que o
   original não tem); um campo fixo divergir; um texto longo estiver igual ao
   português; o título passar de 60 ou a description sair de 120–155 ou
   repetir dentro do idioma; aparecer bastidor ("TODO", "to check"…); faltar
   texto da interface no dicionário.
4. A página entra sozinha no sitemap, no hreflang das duas versões e no
   seletor. Rode o `seo_audit.py` antes do push.

Detalhes das travas, da conferência de números e do dicionário da interface
em `_src/obras/ESQUEMA.md`, seção "Traduções".
