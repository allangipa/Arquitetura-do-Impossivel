# Arquitetura do Impossível — site

Site do canal **@ArquiteturadoImpossível**, em `arquiteturadoimpossivel.com.br`.
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
(`assets/fontes/`, SIL OFL), sem Google Fonts: o site não chama nenhum
servidor de terceiros e não usa cookies.

O símbolo (triângulo de Penrose) vai inline a partir de
`_src/marca/simbolo-escuro.svg`; no cabeçalho e no favicon, sem a cota.

## Publicar

**No ar desde 02/10/2026** em https://arquiteturadoimpossivel.com.br, com SSL
(o http redireciona para https, e o www funciona).

Repositório: https://github.com/allangipa/Arquitetura-do-Impossivel, branch
`main`. **Cada push na `main` publica o site** — o Git do painel da Hostinger
(Sites → arquiteturadoimpossivel.com.br → Avançado → Git, diretório = raiz)
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
`curl -s https://arquiteturadoimpossivel.com.br/obras/<slug>.html | grep "<trecho novo>"`).
O push dar certo não prova que o deploy deu.

### O que o `.htaccess` segura

Com o deploy por Git o repositório **inteiro** vai para o servidor, não só o
site. O `.htaccess` é o que impede o resto de ser servido:

- `404.html` como página de erro;
- 404 para `_src/`, `.claude/`, `.git/`, `README.md` e `.gitignore`.

Arquivo novo na raiz que não seja página (nota, script, planilha) **fica
público** até entrar nessa lista. Na dúvida, ponha dentro de `_src/`.

### Publicação por pacote (só se o Git falhar)

A primeira publicação, antes de o Git ser ligado, foi por pacote, pelo plugin
da Hostinger no Claude Code: zip só com o que é servido (`index.html`,
`404.html`, `favicon.svg`, `robots.txt`, `sitemap.xml`, `.htaccess`, `obras/`
e `assets/`), envio para `public_html` e "deploy static site archive".
**Esse deploy apaga a pasta inteira do site antes de extrair**: o pacote vai
sempre completo, nunca só o que mudou.
