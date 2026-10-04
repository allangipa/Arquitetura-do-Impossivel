---
name: arquitetura-do-impossivel
description: Fluxo de trabalho do site estático arquiteturadoimpossivel.com (canal @ArquiteturadoImpossível). Use para qualquer mudança no site — nova obra, correção de texto ou foto, tradução para inglês/espanhol, temas, páginas fixas (sobre, contato, privacidade), AdSense, domínio/.htaccess, SEO ou publicação na Hostinger.
---

# Arquitetura do Impossível — site

Site estático, sem framework. Gera-se localmente com Python, faz-se commit e
push na `main` do GitHub (`allangipa/Arquitetura-do-Impossivel`) e a Hostinger
publica sozinha em ~15 s. O guia completo é o `README.md` na raiz; detalhes
de campos e traduções em `_src/obras/ESQUEMA.md`. Leia a seção pertinente
antes de mexer.

## Regras que não se quebram

1. **Nunca edite HTML gerado**: `index.html`, `404.html`, `obras/*.html`,
   `temas/*.html`, `sobre/contato/privacidade.html`, tudo em `en/` e `es/`,
   `sitemap.xml`, `robots.txt`, `ads.txt`. Mude a fonte em `_src/` e rode
   `python _src/build.py`.
2. **Nenhum texto de obra mora em template.** Cada obra é
   `_src/obras/NN-slug.json`; traduções em `_src/obras/en/` e `_src/obras/es/`
   com o mesmo nome de arquivo. Temas: `_src/temas.json`, `temas.en.json`,
   `temas.es.json`. Interface: `_src/i18n/en.json`, `es.json`. Páginas fixas:
   constantes no `_src/build.py` (`SOBRE_PT`/`ABOUT_EN`/`ACERCA_ES`,
   `CONTATO_PT`/`CONTACT_EN`/`CONTACTO_ES`,
   `PRIVACIDADE`/`PRIVACY_EN`/`PRIVACIDAD_ES`, `FIXAS_SEO`).
3. **A apuração manda.** A fonte de cada obra é
   `Canais do YouTube\Arquitetura do Impossível\Roteiros\NN Tema\VERIFICACAO.md`.
   Se site e vídeo divergirem, corrija o JSON a partir da apuração.
4. **Fotos**: só domínio público, CC0, CC BY e CC BY-SA, com autor e licença
   do `MANIFESTO` do episódio (`material\foto\`). NC e "No known copyright
   restrictions" não entram. Arquivos em `assets/img/NN-nome.jpg` (1600 px,
   JPEG 82) e `NN-nome-800.jpg`.
5. **Selo de confiança** em cada número, o mesmo grau da apuração:
   2+ fontes · 1 fonte · diverge (mostra as versões) · sem registro.
6. **Nada de bastidor no texto público** ("VERIFICACAO", "a apurar", `[2+]`,
   "TODO", nomes de arquivo). O build barra, mas não escreva.
7. **Privacidades em pt, en e es dizem exatamente o mesmo.** Mudou uma, mude
   as outras e a data.
8. Arquivo novo na raiz que não seja página **fica público**: ponha em
   `_src/` ou acrescente ao bloqueio 404 do `.htaccess`.

## O build é porteiro

`python _src/build.py` para sem gerar nada se faltar campo, `proximo` apontar
para obra inexistente, faltar imagem, a licença não for aceita, houver
bastidor ou, nas traduções: número divergente do original, campo fixo
diferente, texto longo igual ao português, título > 60, description fora de
120–155 ou repetida, texto de interface ausente. **Corrija a causa; nunca
afrouxe a trava para passar.**

## Nova obra

1. Escreva `_src/obras/NN-slug.json` seguindo `ESQUEMA.md`, a partir do
   `VERIFICACAO.md` do episódio.
2. Ponha as fotos em `assets/img/` (as duas larguras).
3. Na obra anterior, aponte `proximo` para o novo slug.
4. Se estava em `EM_APURACAO` no `_src/build.py`, tire de lá.
5. `python _src/build.py`.
6. Traduza para en e es (abaixo), para o site continuar completo nos três
   idiomas.

## Traduzir uma obra

1. Copie o JSON para `_src/obras/en/` (ou `es/`) com o mesmo nome e traduza só
   os textos; campos fixos (num, slug, regiao, estreia, proximo, relacionados,
   conf, arquivo, licenca, licenca_url, origem_url, recriacao, foco, url)
   podem ser apagados — vêm do original. Exemplo:
   `_src/obras/en/01-cristo-redentor.json`.
2. Tradução fiel: nenhum fato novo, nenhuma conversão de unidade, divergência
   continua divergência, atribuição continua atribuição. Por extenso fica por
   extenso; algarismo fica algarismo. Citações, pelo idioma original da fonte.
3. Espanhol: números como no português (`1.145`, `3,75`); "bilhão" é
   **"mil millones"**, nunca "billón".
4. `python _src/build.py` e `python _src/seo_audit.py`. Sitemap, hreflang e
   seletor de idioma se ajustam sozinhos.

## Conferir localmente

Servidor de prévia em `.claude/launch.json` (`site-arquitetura`, porta 8765):
use `preview_start` com esse nome e abra a página alterada.
Mudou o `.htaccess`: `python _src/testa_htaccess.py .htaccess arquiteturadoimpossivel`.

## Publicar

```bash
python _src/build.py
python _src/seo_audit.py
git add -A
git commit -m "o que mudou"
git push
```

- **Rode o build antes do commit**: o servidor só publica os `.html` do
  repositório. JSON mudado sem build = site com texto velho, sem erro.
- Mensagens de commit em português, descrevendo o que mudou no site.
- Só faça commit/push quando o usuário pedir.
- **Confira no ar, não no terminal**: o push dar certo não prova o deploy.
  ```bash
  curl -s https://arquiteturadoimpossivel.com/obras/<slug>.html | grep "<trecho novo>"
  python _src/seo_audit.py --no-ar
  ```
- Se o Git da Hostinger falhar, há a publicação por pacote (README, seção
  "Publicação por pacote"): o pacote vai **sempre completo**, porque o deploy
  apaga a pasta antes de extrair.

## Referência rápida

- Domínio: `https://arquiteturadoimpossivel.com` (sem www; constante
  `DOMINIO`). `.com.br`, `www.com.br` e `www.com` redirecionam 301 pelo
  `.htaccess`.
- Idiomas: `IDIOMAS = ["pt", "en", "es"]`; português na raiz, `en/` e `es/`
  com os mesmos slugs. 404 só em português.
- Marca: en "Arquitetura do Impossível — Impossible Architecture"; es
  "Arquitetura do Impossível — Arquitectura de lo Imposible".
- Identidade: cianotipia `#0F2A44`, giz `#E9EEF0`, concreto `#8E9AA3`, viga
  `#2B5C87`, amarelo de obra `#F2B705` como acento único. Barlow Condensed
  (títulos), IBM Plex Mono (cotas), IBM Plex Sans (corpo), servidas de
  `assets/fontes/`. Sem Google Fonts.
- AdSense: `ADSENSE_LIGADO`, `ADSENSE_PUB` (`pub-4401770243539507`),
  `CONSENTIMENTO_BLOQUEIA` no topo do build. Anúncios automáticos; o script
  é injetado pela faixa de consentimento, nunca escrito no HTML.
- Estreia: "Estreia DD mmm AAAA" vira "No ar" sozinho no dia, sem regerar.
- Auditoria de SEO do resultado: `python _src/seo_audit.py` (depois do build,
  antes do push; código 1 se houver erro). `--no-ar` também confere cada URL
  do sitemap no site publicado — use depois do push.
