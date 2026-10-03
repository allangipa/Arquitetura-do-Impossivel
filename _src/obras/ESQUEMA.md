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
