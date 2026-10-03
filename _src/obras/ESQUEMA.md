# Ficha de obra — esquema do JSON

Cada obra do site é um arquivo `_src/obras/NN-slug.json`. O `build.py` lê
todos e gera `obras/<slug>.html` e o quadro da home. **Nenhum texto de obra
mora em template**: mudou um número, muda aqui.

Fonte única do conteúdo: a apuração do episódio
(`Canais do YouTube\Arquitetura do Impossível\Roteiros\NN Tema\VERIFICACAO.md`).
O roteiro e a descrição do YouTube servem para tom e ordem, nunca como fonte
de número.

```json
{
  "num": "01",
  "slug": "cristo-redentor",
  "obra": "Cristo Redentor",
  "titulo_video": "texto exato do título do YouTube, ou null se o vídeo ainda não tem título",
  "lugar": "Corcovado, Rio de Janeiro, Brasil",
  "regiao": "brasil",                // "brasil" ou "mundo"
  "periodo": "1922–1931",            // do primeiro marco de obra à inauguração
  "estreia": "2026-10-08",           // data do episódio no canal
  "impossivel": "uma frase: o que tornava a obra impossível",
  "resumo": "até 155 caracteres; vira meta description",
  "abertura": ["2 parágrafos curtos de abertura da página"],
  "numeros": [                       // 4 a 6, os da faixa de cotas no topo
    {"valor": "38 m", "rotulo": "altura com o pedestal", "conf": "2+"}
  ],
  "ficha": [                         // a tabela "Ficha da obra", para o leitor
    {"item": "Operários", "valor": "…", "conf": "2+|1|DIV|sem", "nota": "opcional, curta"}
  ],
  "historia": [                      // 4 a 7 seções
    {"titulo": "…", "paragrafos": ["…", "…"]}
  ],
  "mitos": [                         // 2 a 5
    {"circula": "o que se repete por aí", "registro": "o que a fonte diz"}
  ],
  "fontes": [
    {"texto": "Autor, título, veículo, ano", "url": "https://… ou null"}
  ],
  "imagens": [                       // a primeira é a capa
    {"arquivo": "01-cristo-redentor-capa.jpg", "alt": "…", "legenda": "…",
     "autor": "…", "licenca": "CC BY-SA 4.0", "licenca_url": "https://…",
     "origem_url": "https://commons.wikimedia.org/wiki/File:…",
     "recriacao": false,
     "foco": "68% 45%"}               // opcional: ponto que não pode sair do quadro no recorte (CSS object-position)
  ],
  "proximo": "empire-state"          // slug da obra seguinte, ou null
}
```

Grau de confiança (`conf`), o mesmo da apuração:
- `2+` confirmado em duas ou mais fontes independentes
- `1` uma fonte só
- `DIV` as fontes divergem — o valor mostra as versões, o site não escolhe
- `sem` ninguém registrou — o valor diz isso com todas as letras

## Campos opcionais de busca e navegação (03/10/2026)

- `"titulo_seo": "Como foi construído o Cristo Redentor (1922–1931)"` — substitui
  o `<title>` padrão (`obra (período) · marca`) quando a obra é buscada de
  outro jeito: "como foi construído o…", o nome em inglês ("Hoover Dam",
  "Forth Bridge"). Até 60 caracteres e único; o build para fora disso. Saiu do
  autocomplete do Google em pt-BR; nunca afirma o que a página não sustenta.
- `"relacionados": ["slug", "slug", "slug"]` — o bloco "Leia também" no fim da
  página: três obras de assunto próximo (pontes pênseis, arranha-céus,
  túneis…). O build para se um slug não existir, repetir, for a própria obra
  ou for o `proximo` (que já tem bloco próprio).

Imagens: o build gera sozinho a cópia `.webp` de cada JPEG (e da versão
`-800`) e serve as duas num `<picture>`; não é preciso fazer nada à mão.

## Perguntas frequentes e páginas de tema (03/10/2026)

- `"perguntas": [{"p": "Pergunta como se busca?", "r": "Resposta de 1 a 3 frases."}]`
  (opcional, 3 a 5 itens, logo antes de `fontes`) — vira a seção "Perguntas
  frequentes" (âncora `#perguntas`), depois dos mitos e antes das fontes, e
  entra no índice "Nesta página". As perguntas saem das buscas reais (autocomplete
  do Google em pt-BR: "como foi construído…", "quantas pessoas morreram…",
  "quem venceu…", "por que … perdeu…"). **A resposta só repete o que a página já
  diz**: nenhum fato novo; divergência continua divergência ("as fontes
  divergem: X ou Y"); onde a página diz que não há registro, a resposta diz
  isso. O build para se faltar "?", se houver menos de 3 ou mais de 5 itens, ou
  se aparecer termo de bastidor (a mesma trava do resto da página). Sem
  JSON-LD de FAQ, de propósito.
- `_src/temas.json` — as páginas-índice `temas/<slug>.html`: `slug`, `nome`
  (o h1), `titulo` (o `<title>`; a marca entra no fim se couber em 60),
  `resumo` (a description, 120–155), `intro` (2 ou 3 parágrafos, só com o
  que as páginas do grupo dizem) e `obras` (a lista de slugs, 2 ou mais). O
  build gera a página com cartões, CollectionPage + BreadcrumbList, imagem de
  compartilhamento própria (`og-tema-<slug>.jpg`), põe no sitemap, lista na
  home (seção `#temas`) e linka o tema no bloco "Leia também" de cada obra do
  grupo. Para se um slug não existir, repetir, ou se o texto tiver bastidor.

## Traduções (03/10/2026)

Arquivos paralelos, **mesmo nome** do original:

```
_src/obras/NN-slug.json        português (a fonte; manda sempre)
_src/obras/en/NN-slug.json     inglês
_src/obras/es/NN-slug.json     espanhol
_src/temas.en.json                    temas em inglês (opcional)
_src/i18n/en.json                     textos da interface em inglês
```

**A tradução tem os mesmos campos e as mesmas listas, na mesma ordem e com o
mesmo número de itens** (mesmas seções, mesmos parágrafos, mesmas linhas de
ficha, mesmas imagens). O build confere campo a campo (`fundir_traducao`).

- **Campos fixos** — num, slug, regiao, estreia, proximo, relacionados, conf, arquivo, licenca, licenca_url, origem_url, recriacao, foco, url: não se traduzem. Podem ser omitidos
  (vêm do original); se estiverem, têm de ser idênticos.
- **Opcionais só da tradução**: `titulo_seo` (o nome como se busca naquele
  idioma), `_nota` (comentário, não publicado) e `_excecoes_numeros`.
- `autor` das imagens e `texto` das fontes podem ficar iguais ao original
  (nome próprio, título de obra citada); o resto, com 25 caracteres ou mais,
  igual ao português é tratado como "não traduzido" e para o build.

### Conferência de números

Todo número do original tem de aparecer no mesmo campo da tradução, e a
tradução não pode ter número que o original não tem. A comparação normaliza:

| português | inglês | conta como |
|---|---|---|
| `1.145` / `3,75` | `1,145` / `3.75` | 1145 / 3.75 |
| `20 mil`, `1,5 milhão` | `20,000`, `1.5 million` | 20000, 1500000 |
| `250–300 mil` | `250,000–300,000` | 250000 e 300000 |
| `3/11/1924` | `3 November 1924` | 3, mês 11, 1924 |
| `12 de outubro` | `12 October` / `October 12` | 12, mês 10 |

O mês por extenso conta como número (só na caixa da ortografia: minúsculo em
pt/es, maiúsculo em en — "Rio de Janeiro" não é janeiro). Número escrito por
extenso ("cinco anos") não é conferido: mantenha por extenso. Exceção legítima
(raro): liste o número em `"_excecoes_numeros": ["1.000"]` na tradução — ele
deixa de ser conferido nos dois lados.

### Textos da interface: `_src/i18n/<id>.json`

```json
{
  "_idioma": {"nome": "English", "curto": "EN", "hreflang": "en", "og_locale": "en_US",
              "marca_sub": "Impossible Architecture",
              "meses": ["January", "…"], "meses_curtos": ["Jan", "…"],
              "data_longa": "{mes} {dia}, {ano}", "data_curta": "{mes} {dia:02d}, {ano}"},
  "textos": {"Leia também": "Read next", "Detalhes na {politica}.": "Details in our {politica} (in Portuguese)."}
}
```

A **chave é o próprio texto em português** que está no build. Mudou o texto
em português, a tradução deixa de casar e o build para listando o que falta
(e avisa das chaves que ficaram sobrando). Os marcadores `{…}` têm de ser os
mesmos dos dois lados. Datas por extenso saem de `data_longa`/`data_curta`.

