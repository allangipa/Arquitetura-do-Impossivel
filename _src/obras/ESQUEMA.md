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
