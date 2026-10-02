# Arquitetura do Impossível — site

Site do canal **@ArquiteturadoImpossível**, em `arquiteturadoimpossivel.com.br`.
Estático, sem framework e sem build no servidor — o mesmo fluxo do Vestígio
Oculto e do viagemnalupa: gera aqui, commit no GitHub, deploy na Hostinger.

Na Hostinger o site já existe (criado em 02/10/2026, pedido 1009996834, conta
`u888898160`, pasta `domains/arquiteturadoimpossivel.com.br/public_html`).

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
(`assets/fontes/`, SIL OFL), sem Google Fonts: o site não chama nenhum
servidor de terceiros e não usa cookies.

O símbolo (triângulo de Penrose) vai inline a partir de
`_src/marca/simbolo-escuro.svg`; no cabeçalho e no favicon, sem a cota.

## Publicar na Hostinger

**No ar desde 02/10/2026** em https://arquiteturadoimpossivel.com.br, com SSL
(o http já redireciona para https, e o www funciona).

A primeira publicação foi por **pacote**, pelo plugin da Hostinger no Claude
Code, não pelo Git do painel:

1. `python _src/build.py`
2. zip só com o que é servido: `index.html`, `404.html`, `favicon.svg`,
   `robots.txt`, `sitemap.xml`, `.htaccess`, `obras/` e `assets/` (sem `_src/`);
3. envio do zip para `public_html` e "deploy static site archive".

**O deploy apaga a pasta inteira do site antes de extrair** — o pacote tem de
estar completo, nunca só o que mudou.

O `.htaccess` serve o `404.html` e responde 404 para `_src/`, mesmo que ele
um dia vá parar no servidor.

### GitHub (pendente)

O repositório git local existe (branch `main`), mas ainda não tem remoto: o
GitHub CLI não está instalado nesta máquina. Para ligar, crie o repositório
vazio `Arquitetura-do-Impossivel` em github.com e rode:

```bash
git remote add origin https://github.com/allangipa/Arquitetura-do-Impossivel.git
git push -u origin main
```

Se depois quiser deploy automático a cada push, igual ao Vestígio: painel →
**Sites → arquiteturadoimpossivel.com.br → Avançado → Git**, branch `main`,
diretório = raiz.
