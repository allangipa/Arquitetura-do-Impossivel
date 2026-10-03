#!/usr/bin/env python3
"""Gera o site do Arquitetura do Impossível.

    python _src/build.py        (a partir da raiz do site)

Lê cada obra de `_src/obras/NN-slug.json` (esquema em `_src/obras/ESQUEMA.md`)
e escreve, na raiz:

    index.html  obras/<slug>.html  404.html  favicon.svg
    sitemap.xml  robots.txt  assets/arquitetura.css  assets/img/og-*.jpg

Nunca edite os .html gerados: o próximo build apaga a mudança.

O build é porteiro, não sugestão. Ele PARA quando:
  - um JSON não tem um campo obrigatório, ou o `proximo` aponta para obra
    que não existe;
  - uma imagem citada não está em assets/img;
  - uma licença não é das aceitas (NC e "no known copyright" não entram);
  - o texto público carrega bastidor de produção ("VERIFICACAO", "a apurar",
    "[2+]"…) — o mesmo erro que no canal saiu em rodapé de cartela.
"""
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "_src"
IMG = RAIZ / "assets" / "img"

DOMINIO = "https://arquiteturadoimpossivel.com.br"
CANAL = "https://www.youtube.com/@ArquiteturadoImposs%C3%ADvel"
NOME = "Arquitetura do Impossível"

# AdSense — mesmo publisher do Vestígio Oculto. ADSENSE_LIGADO = False tira
# tudo de todas as páginas e apaga o ads.txt: é o interruptor geral.
ADSENSE_LIGADO = True
ADSENSE_PUB = "pub-4401770243539507"
# False = a faixa avisa e o anúncio carrega de imediato; quem recusar deixa de
# receber. True = nada de anúncio até "Entendi" (mais conservador, menos receita).
# Igual ao Vestígio.
CONSENTIMENTO_BLOQUEIA = False
CHAVE_CONSENTIMENTO = "ai-consentimento"

BORDAO = "Toda semana, uma obra que não deveria ter ficado de pé."

# Episódios anunciados que ainda não têm página: aparecem no quadro como
# "em apuração", sem link. Quando o JSON da obra existir, tire daqui.
EM_APURACAO = [
    {
        "num": "10",
        "obra": "Torre Eiffel",
        "lugar": "Paris, França",
        "regiao": "mundo",
        "impossivel": "A estrutura mais alta do mundo em 1889: ferro e rebite, calculada contra o vento e montada em pouco mais de dois anos.",
        "estreia": "2026-12-10",
    },
]

OBRIGATORIOS = ["num", "slug", "obra", "titulo_video", "lugar", "regiao", "periodo",
                "estreia", "impossivel", "resumo", "abertura", "numeros", "ficha",
                "historia", "mitos", "fontes", "imagens", "proximo"]

LICENCAS_OK = re.compile(r"^(dom[ií]nio p[uú]blico|public domain|cc0|cc by(-sa)? \d\.\d( [a-z]{2,3})?|pd[- ].*)$", re.I)

BASTIDOR = re.compile(
    r"VERIFICACAO|VERIFICAÇÃO\.md|\ba apurar\b|\bconferir\b|\brodada \d|\[2\+\]|\[DIV\]|\[1\]"
    r"|\.md\b|\.tsv\b|MANIFESTO|roteiro diz|n[ãa]o usar\b|n[ãa]o afirmar", re.I)

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

CONF = {
    "2+": ("conf-2", "2+ fontes", "Confirmado em duas ou mais fontes independentes."),
    "1": ("conf-1", "1 fonte", "Uma fonte só; o texto diz qual."),
    "DIV": ("conf-div", "diverge", "As fontes discordam; mostramos as versões e não escolhemos."),
    "sem": ("conf-sem", "sem registro", "Ninguém registrou. Dizemos isso em vez de inventar."),
}

e = lambda s: html.escape(str(s), quote=True)


def para(s):
    """Texto de parágrafo: escapa e aceita *itálico* e **negrito**."""
    t = e(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def data_br(iso, longa=False):
    d = dt.date.fromisoformat(iso)
    if longa:
        return f"{d.day} de {['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'][d.month-1]} de {d.year}"
    return f"{d.day:02d} {MESES[d.month-1]} {d.year}"


def falha(msg):
    raise SystemExit("PARADO: " + msg)


# --- marca ---------------------------------------------------------------
def simbolo(viewbox="0 0 1020 1102.5", classe="", rotulo=NOME, agrupar=False):
    bruto = (SRC / "marca" / "simbolo-escuro.svg").read_text(encoding="utf-8")
    corpo = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", bruto, flags=re.S).strip()
    if agrupar:
        linhas = corpo.splitlines()
        vigas = [l for l in linhas if "F2B705" not in l]
        cotas = [l for l in linhas if "F2B705" in l]
        corpo = f'<g class="vigas">{"".join(vigas)}</g><g class="cotas">{"".join(cotas)}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" class="{classe}" '
            f'role="img" aria-label="{e(rotulo)}">{corpo}</svg>')


SIMBOLO_PEQUENO = lambda: simbolo("0 0 1020 886", rotulo="")  # sem a cota: a 34 px ela vira sujeira


# --- carga e conferência --------------------------------------------------
def carregar():
    obras = []
    for f in sorted((SRC / "obras").glob("[0-9][0-9]-*.json")):
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            falha(f"{f.name} não é JSON válido: {ex}")
        falta = [c for c in OBRIGATORIOS if c not in o]
        if falta:
            falha(f"{f.name} sem os campos {falta}")
        if f.name != f"{o['num']}-{o['slug']}.json":
            falha(f"{f.name}: nome do arquivo não bate com num/slug")
        if o["regiao"] not in ("brasil", "mundo"):
            falha(f"{f.name}: regiao deve ser brasil ou mundo")
        dt.date.fromisoformat(o["estreia"])
        if not o["imagens"]:
            falha(f"{f.name}: precisa de pelo menos uma imagem (a capa)")
        for im in o["imagens"]:
            for k in ("arquivo", "alt", "legenda", "autor", "licenca"):
                if not im.get(k):
                    falha(f"{f.name}: imagem sem '{k}': {im}")
            if not (IMG / im["arquivo"]).exists():
                falha(f"{f.name}: imagem inexistente assets/img/{im['arquivo']}")
            if re.search(r"\bNC\b|no known copyright", im["licenca"], re.I) or not LICENCAS_OK.match(im["licenca"].strip()):
                falha(f"{f.name}: licença não aceita em {im['arquivo']}: {im['licenca']!r}")
        for n in o["numeros"] + o["ficha"]:
            if n.get("conf") not in CONF:
                falha(f"{f.name}: conf inválido {n.get('conf')!r} em {n}")
        texto = json.dumps({k: v for k, v in o.items() if k not in ("imagens", "fontes")}, ensure_ascii=False)
        texto += " ".join(i["legenda"] + " " + i["alt"] for i in o["imagens"])
        m = BASTIDOR.search(texto)
        if m:
            ctx = texto[max(0, m.start() - 60):m.end() + 60]
            falha(f"{f.name}: bastidor de produção no texto público ({m.group(0)!r}): …{ctx}…")
        obras.append(o)
    slugs = {o["slug"] for o in obras}
    for o in obras:
        if o["proximo"] and o["proximo"] not in slugs:
            falha(f"{o['slug']}: proximo '{o['proximo']}' não existe")
    if not obras:
        falha("nenhuma obra em _src/obras")
    return obras


# --- peças comuns ----------------------------------------------------------

def adsense_head():
    if not ADSENSE_LIGADO:
        return "<!-- AdSense desligado em _src/build.py -->"
    return (f'<meta name="google-adsense-account" content="ca-{ADSENSE_PUB}">\n'
            '<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>')


def consentimento(base):
    """A faixa de cookies. O script do AdSense não fica no HTML: entra por
    aqui, e só quando pode — mesmo desenho do site do Vestígio Oculto."""
    if not ADSENSE_LIGADO:
        return ""
    return f"""<div class="consentimento" id="consentimento" role="dialog" aria-live="polite" aria-label="Aviso de cookies" hidden>
  <div class="casca">
    <p>Este site usa cookies do Google AdSense para exibir anúncios e medir audiência. Não pedimos cadastro nem e-mail. Detalhes na <a href="{base}privacidade.html">política de privacidade</a>.</p>
    <div class="botoes">
      <button type="button" data-consent="recusar">Recusar anúncios</button>
      <button type="button" data-consent="aceitar" class="principal">Entendi</button>
    </div>
  </div>
</div>
<script>
(function(){{
  var CHAVE='{CHAVE_CONSENTIMENTO}', PUB='{ADSENSE_PUB}', BLOQUEIA={'true' if CONSENTIMENTO_BLOQUEIA else 'false'};
  function ler(){{try{{return localStorage.getItem(CHAVE)}}catch(e){{return null}}}}
  function gravar(v){{try{{localStorage.setItem(CHAVE,v)}}catch(e){{}}}}
  function carrega(){{
    if(!PUB||document.getElementById('ads-google'))return;
    var s=document.createElement('script');s.id='ads-google';s.async=true;s.crossOrigin='anonymous';
    s.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-'+PUB;
    document.head.appendChild(s);
  }}
  var escolha=ler();
  if(escolha==='aceitar'||(escolha===null&&!BLOQUEIA))carrega();
  var caixa=document.getElementById('consentimento');
  if(escolha===null&&caixa){{
    caixa.hidden=false;
    caixa.addEventListener('click',function(ev){{
      var b=ev.target.closest('[data-consent]');if(!b)return;
      var v=b.dataset.consent;gravar(v);caixa.hidden=true;
      if(v==='aceitar')carrega();else{{var x=document.getElementById('ads-google');if(x)x.remove();}}
    }});
  }}
  // Europa, Reino Unido, Suíça: quem pergunta é a mensagem do Google (a
  // plataforma certificada que o AdSense exige lá). Se ela diz que o GDPR se
  // aplica, esta faixa sai da frente. Sem a mensagem publicada, não dispara.
  if(escolha===null&&caixa){{
    var n=0,t=setInterval(function(){{
      if(typeof window.__tcfapi==='function'){{
        clearInterval(t);
        window.__tcfapi('addEventListener',2,function(tc,ok){{if(ok&&tc&&tc.gdprApplies)caixa.hidden=true;}});
      }}else if(++n>40)clearInterval(t);
    }},250);
  }}
}})();
</script>
"""

def cabeca(titulo, descricao, url, imagem, base, jsonld, tipo="website"):
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descricao)}">
<link rel="canonical" href="{e(url)}">
<meta name="theme-color" content="#0F2A44">
<link rel="icon" href="{base}favicon.svg" type="image/svg+xml">
<link rel="preload" href="{base}assets/fontes/barlow-condensed-700.woff2" as="font" type="font/woff2" crossorigin>
{adsense_head()}
<link rel="stylesheet" href="{base}assets/arquitetura.css">
<meta property="og:type" content="{tipo}">
<meta property="og:site_name" content="{e(NOME)}">
<meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descricao)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(imagem)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
"""


def topo(base, atual=""):
    cur = lambda k: ' aria-current="page"' if k == atual else ""
    return f"""<header class="topo">
  <div class="casca">
    <a class="marca" href="{base}index.html">{SIMBOLO_PEQUENO()}<span>Arquitetura <em>do Impossível</em></span></a>
    <nav class="nav" aria-label="Principal">
      <a href="{base}index.html#obras"{cur('obras')}>Obras</a>
      <a href="{base}index.html#metodo"{cur('metodo')}>Método</a>
      <a href="{base}sobre.html"{cur('sobre')}>Sobre</a>
      <a class="yt" href="{CANAL}" target="_blank" rel="noopener">YouTube</a>
    </nav>
  </div>
</header>
"""


def rodape(base):
    ano = dt.date.today().year
    return f"""<footer class="rodape">
  <div class="casca">
    <div>
      <h4>Arquitetura do Impossível</h4>
      <p>Como uma obra que parecia impossível ficou de pé: o projeto, o cálculo, o canteiro, quem trabalhou e quem morreu. Aqui, número tem fonte.</p>
      <p><a href="{CANAL}" target="_blank" rel="noopener">Assista no YouTube</a></p>
    </div>
    <div>
      <h4>Do mesmo criador</h4>
      <ul>
        <li><a href="https://vestigiooculto.com.br" rel="noopener">Vestígio Oculto</a> — arqueologia e mistério</li>
        <li>Xadrez Bélico — batalhas explicadas como partida</li>
      </ul>
    </div>
    <div>
      <h4>Este site</h4>
      <ul>
        <li><a href="{base}sobre.html">Sobre</a> · <a href="{base}contato.html">Contato</a></li>
        <li>Exibe anúncios do Google AdSense. <a href="{base}privacidade.html">Política de privacidade</a>.</li>
        <li>Fotos de terceiros sob domínio público ou Creative Commons, com crédito em cada página.</li>
      </ul>
    </div>
    <div class="linha"><span>© {ano} {NOME} · textos autorais</span><span>o impossível, medido.</span></div>
  </div>
</footer>
"""


SCRIPT = """<script>
(function(){
  var hoje=new Date();hoje.setHours(0,0,0,0);
  document.querySelectorAll('[data-estreia]').forEach(function(el){
    var p=el.getAttribute('data-estreia').split('-'),d=new Date(+p[0],p[1]-1,+p[2]);
    if(d<=hoje){el.textContent=el.getAttribute('data-no-ar')||'No ar';el.classList.add('no-ar');}
  });
  var fs=document.querySelectorAll('.filtros button'),cs=document.querySelectorAll('.obra-card');
  fs.forEach(function(b){b.addEventListener('click',function(){
    fs.forEach(function(x){x.setAttribute('aria-pressed',x===b)});
    var f=b.dataset.f;cs.forEach(function(c){c.hidden=!(f==='todas'||c.dataset.regiao===f)});
  })});
  var rv=document.querySelectorAll('.revela');
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){x.target.classList.add('visto');io.unobserve(x.target)}})},{rootMargin:'0px 0px -8% 0px'});
    rv.forEach(function(x){io.observe(x)});
  } else rv.forEach(function(x){x.classList.add('visto')});
  var bar=document.querySelector('.progresso'),art=document.querySelector('.texto');
  if(bar&&art){var up=function(){var r=art.getBoundingClientRect(),t=r.height-innerHeight;bar.style.transform='scaleX('+Math.min(1,Math.max(0,-r.top/(t>0?t:1)))+')'};addEventListener('scroll',up,{passive:true});up();}
  var links=document.querySelectorAll('.indice a');
  if(links.length&&'IntersectionObserver' in window){
    var io2=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){links.forEach(function(a){a.classList.toggle('ativo',a.getAttribute('href')==='#'+x.target.id)})}})},{rootMargin:'-20% 0px -70% 0px'});
    document.querySelectorAll('.texto h2[id]').forEach(function(h){io2.observe(h)});
  }
  var lupa=document.querySelector('.lupa');
  if(lupa){
    var li=lupa.querySelector('img'),lp=lupa.querySelector('p'),lb=lupa.querySelector('button'),ant=null;
    var fecha=function(){lupa.classList.remove('aberta');document.body.style.overflow='';if(ant)ant.focus()};
    document.querySelectorAll('.fig button').forEach(function(b){b.addEventListener('click',function(){
      ant=b;var im=b.querySelector('img');li.src=b.dataset.grande;li.alt=im.alt;lp.textContent=b.dataset.legenda;
      lupa.classList.add('aberta');document.body.style.overflow='hidden';lb.focus();
    })});
    lb.addEventListener('click',fecha);
    lupa.addEventListener('click',function(ev){if(ev.target===lupa)fecha()});
    addEventListener('keydown',function(ev){if(ev.key==='Escape'&&lupa.classList.contains('aberta'))fecha()});
  }
})();
</script>
</body>
</html>
"""


def conf_selo(c):
    cls, txt, tit = CONF[c]
    return f'<span class="conf {cls}" title="{e(tit)}">{e(txt)}</span>'


def img_tag(arquivo, alt, base, tamanhos="100vw", carregar="lazy", classe="", foco=None):
    nome = Path(arquivo).stem
    menor = IMG / f"{nome}-800.jpg"
    w, h = Image.open(IMG / arquivo).size
    srcset = ""
    if menor.exists():
        srcset = f' srcset="{base}assets/img/{nome}-800.jpg 800w, {base}assets/img/{arquivo} {w}w" sizes="{tamanhos}"'
    cl = f' class="{classe}"' if classe else ""
    # `foco` (opcional na imagem do JSON): o ponto que não pode sair do quadro
    # quando a foto é recortada (capa no celular, cartão da home). CSS object-position.
    st = f' style="object-position:{e(foco)}"' if foco else ""
    return (f'<img src="{base}assets/img/{e(arquivo)}"{srcset} width="{w}" height="{h}" '
            f'alt="{e(alt)}" loading="{carregar}" decoding="async"{cl}{st}>')


def credito(im):
    lic = e(im["licenca"])
    if im.get("licenca_url"):
        lic = f'<a href="{e(im["licenca_url"])}" rel="license noopener">{lic}</a>'
    autor = e(im["autor"])
    if im.get("origem_url"):
        autor = f'<a href="{e(im["origem_url"])}" rel="noopener">{autor}</a>'
    return f"{autor} · {lic}"


# --- imagem de compartilhamento --------------------------------------------
def fonte(nome, tam):
    return ImageFont.truetype(str(SRC / "marca" / nome), tam)


def og_obra(o):
    destino = IMG / f"og-{o['slug']}.jpg"
    capa = Image.open(IMG / o["imagens"][0]["arquivo"]).convert("RGB")
    im = ImageOps.fit(capa, (1200, 630), Image.LANCZOS, centering=(0.5, 0.45))
    # escurece de baixo para cima, para o título ler sobre qualquer foto
    sombra = Image.new("L", (1, 630))
    for y in range(630):
        sombra.putpixel((0, y), int(245 * min(1, max(0, (y - 150) / 330)) ** 1.1))
    sombra = sombra.resize((1200, 630))
    im = Image.composite(Image.new("RGB", im.size, (9, 27, 45)), im, sombra)
    d = ImageDraw.Draw(im)
    d.text((56, 372), f"OBRA {o['num']}  ·  {o['lugar'].split(',')[-1].strip().upper()}", font=fonte("IBMPlexMono-Medium.ttf", 22), fill=(242, 183, 5))
    tam = 96
    while tam > 50 and d.textlength(o["obra"].upper(), font=fonte("BarlowCondensed-Bold.ttf", tam)) > 1088:
        tam -= 4
    d.text((52, 410), o["obra"].upper(), font=fonte("BarlowCondensed-Bold.ttf", tam), fill=(233, 238, 240))
    d.text((56, 528), "ARQUITETURA DO IMPOSSÍVEL", font=fonte("BarlowCondensed-SemiBold.ttf", 34), fill=(242, 183, 5))
    for x in range(-40, 1240, 40):  # faixa de obra
        d.polygon([(x, 630), (x + 20, 630), (x + 32, 612), (x + 12, 612)], fill=(242, 183, 5))
    d.rectangle([0, 606, 1200, 611], fill=(242, 183, 5))
    im.save(destino, "JPEG", quality=84, optimize=True, progressive=True)
    return destino.name


def og_home():
    destino = IMG / "og-home.jpg"
    b = Image.open(SRC / "marca" / "banner-2560x1440.png").convert("RGB")
    ImageOps.fit(b, (1200, 630), Image.LANCZOS).save(destino, "JPEG", quality=86, optimize=True, progressive=True)
    return destino.name


# --- home ------------------------------------------------------------------
def card(o, base):
    capa = o["imagens"][0]
    return f"""<li class="obra-card revela" data-regiao="{o['regiao']}">
  <div class="foto">{img_tag(capa['arquivo'], capa['alt'], base, '(max-width:720px) 100vw, 400px', foco=capa.get('foco'))}
    <span class="num">{e(o['num'])}</span>
    <span class="selo selo-estreia" data-estreia="{o['estreia']}" data-no-ar="No ar">Estreia {e(data_br(o['estreia']))}</span>
  </div>
  <div class="corpo">
    <h3><a href="{base}obras/{o['slug']}.html">{e(o['obra'])}</a></h3>
    <div class="onde">{e(o['lugar'])} · {e(o['periodo'])}</div>
    <p class="imp">{para(o['impossivel'])}</p>
    <div class="pe"><span>{'Brasil' if o['regiao']=='brasil' else 'Mundo'}</span><span>Ler a obra →</span></div>
  </div>
</li>"""


def card_apuracao(a):
    return f"""<li class="obra-card apuracao revela" data-regiao="{a['regiao']}">
  <div class="foto"><span class="num">{e(a['num'])}</span>
    <span class="selo">Em apuração</span>
  </div>
  <div class="corpo">
    <h3>{e(a['obra'])}</h3>
    <div class="onde">{e(a['lugar'])}</div>
    <p class="imp">{para(a['impossivel'])}</p>
    <div class="pe"><span>{'Brasil' if a['regiao']=='brasil' else 'Mundo'}</span><span>Estreia {e(data_br(a['estreia']))}</span></div>
  </div>
</li>"""


def home(obras, og):
    base = ""
    graus = "".join(f"<li>{conf_selo(k)}<p><strong>{ {'2+':'Confirmado','1':'Fonte única','DIV':'Divergência','sem':'Sem registro'}[k] }</strong>{e(v[2])}</p></li>" for k, v in CONF.items())
    jsonld = {"@context": "https://schema.org", "@type": "WebSite", "name": NOME, "url": DOMINIO + "/",
              "inLanguage": "pt-BR", "description": "Como grandes obras que pareciam impossíveis ficaram de pé.",
              "publisher": {"@type": "Organization", "name": NOME, "sameAs": [CANAL]}}
    cards = "\n".join(card(o, base) for o in obras) + "\n" + "\n".join(card_apuracao(a) for a in EM_APURACAO)
    return (cabeca(f"{NOME} — como isto foi erguido",
                   "Grandes construções que pareciam impossíveis: o projeto, o cálculo, o canteiro, quantos trabalharam, quanto custou e quem morreu. Número com fonte.",
                   DOMINIO + "/", f"{DOMINIO}/assets/img/{og}", base, jsonld)
            + topo(base) + f"""<main id="conteudo">
<section class="abre">
  <div class="casca">
    <div>
      <div class="cota"><span>o impossível, medido</span></div>
      <h1>Como isto foi <em>erguido?</em></h1>
      <p class="lead">Toda semana, a história de uma grande construção que parecia impossível, e de quem resolveu o problema. O projeto, o cálculo, o canteiro. Quantos operários, quanto tempo, quanto custou, quem se feriu e quem morreu.</p>
      <div class="botoes">
        <a class="botao cheio" href="#obras">Ver as obras</a>
        <a class="botao" href="{CANAL}" target="_blank" rel="noopener">Canal no YouTube</a>
      </div>
    </div>
    <div class="simbolo" aria-hidden="true">{simbolo(agrupar=True, rotulo="")}</div>
  </div>
</section>
<div class="faixa" role="presentation"></div>

<section class="secao" id="obras">
  <div class="casca">
    <header>
      <div>
        <span class="rotulo">Prancheta <b>{len(obras) + len(EM_APURACAO):02d}</b> obras</span>
        <h2>As obras</h2>
        <p>Um episódio do Brasil, um do resto do mundo, alternados. Cada página tem a ficha técnica completa e a história de como a obra ficou de pé.</p>
      </div>
      <div class="filtros" role="group" aria-label="Filtrar obras">
        <button type="button" data-f="todas" aria-pressed="true">Todas</button>
        <button type="button" data-f="brasil" aria-pressed="false">Brasil</button>
        <button type="button" data-f="mundo" aria-pressed="false">Mundo</button>
      </div>
    </header>
    <ul class="obras">
{cards}
    </ul>
  </div>
</section>

<section class="secao metodo" id="metodo">
  <div class="casca">
    <div>
      <span class="rotulo">Método</span>
      <h2>Aqui, número <span class="destaque">tem fonte</span></h2>
      <p>Toda obra grande vem com lenda: o operário enterrado no concreto, a estrutura “construída em X dias”, o número de mortos que ninguém conferiu. Cada dado deste site carrega um selo dizendo quanto se pode confiar nele.</p>
      <p>Quando as fontes discordam, mostramos as versões e não escolhemos. Quando ninguém registrou, dizemos isso em vez de inventar.</p>
    </div>
    <ul class="graus">{graus}</ul>
  </div>
</section>
</main>
""" + rodape(base) + consentimento(base) + SCRIPT)


# --- página de obra ---------------------------------------------------------
def figura(im, n, base):
    leg = f"{im['legenda']} — {im['autor']}, {im['licenca']}"
    return f"""<figure class="fig revela">
  <button type="button" class="cantos" data-grande="{base}assets/img/{e(im['arquivo'])}" data-legenda="{e(leg)}" aria-label="Ampliar imagem: {e(im['alt'])}">{img_tag(im['arquivo'], im['alt'], base, '(max-width:980px) 100vw, 720px')}</button>
  <figcaption><span class="fn">FIG. {n:02d}</span><span>{para(im['legenda'])}</span><small>{credito(im)}</small></figcaption>
</figure>"""


def pagina_obra(o, obras, og):
    base = "../"
    url = f"{DOMINIO}/obras/{o['slug']}.html"
    capa = o["imagens"][0]
    resto = o["imagens"][1:]
    secoes = []
    for i, s in enumerate(o["historia"]):
        sid = f"s{i+1}"
        corpo = "".join(f"<p>{para(p)}</p>" for p in s["paragrafos"])
        fig = ""
        if i < len(resto):
            fig = figura(resto[i], i + 2, base)
        secoes.append((sid, s["titulo"], f'<h2 id="{sid}"><span class="n">{i+1:02d}</span>{e(s["titulo"])}</h2>{corpo}{fig}'))
    # figuras que sobraram (mais imagens que seções) vão antes dos mitos
    sobra = "".join(figura(im, len(o["historia"]) + 2 + k, base) for k, im in enumerate(resto[len(o["historia"]):]))

    numeros = "".join(f'<li><span class="valor">{e(n["valor"])}</span><span class="rot">{e(n["rotulo"])}</span>{conf_selo(n["conf"])}</li>' for n in o["numeros"])
    ficha = "".join(
        f'<tr><th scope="row">{e(f["item"])}</th><td class="v">{para(f["valor"])}'
        + (f'<span class="nota">{para(f["nota"])}</span>' if f.get("nota") else "")
        + f'</td><td class="c">{conf_selo(f["conf"])}</td></tr>' for f in o["ficha"])
    legenda_conf = "".join(f"<span>{conf_selo(k)} {e(v[2])}</span>" for k, v in CONF.items())
    mitos = "".join(f'<li><div><span class="rotulo">O que circula</span><p>{para(m["circula"])}</p></div><div><span class="rotulo"><b>O que o registro diz</b></span><p>{para(m["registro"])}</p></div></li>' for m in o["mitos"])
    fontes = "".join(
        f'<li>{para(f["texto"])}' + (f' — <a href="{e(f["url"])}" rel="noopener">{e(re.sub(r"^https?://(www\.)?", "", f["url"]).split("/")[0])}</a>' if f.get("url") else "") + "</li>"
        for f in o["fontes"])
    creditos = "".join(f'<li>Fig. {i+1:02d} — {e(im["legenda"])}: {credito(im)}</li>' for i, im in enumerate(o["imagens"]))

    indice = [("ficha", "Ficha da obra")] + [(sid, t) for sid, t, _ in secoes] + [("mitos", "Mitos e registro"), ("fontes", "Fontes")]
    indice_html = "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in indice)

    i_atual = [x["slug"] for x in obras].index(o["slug"])
    ant = obras[i_atual - 1] if i_atual > 0 else None
    prox = next((x for x in obras if x["slug"] == o["proximo"]), None) if o["proximo"] else None
    nav = ""
    if ant or prox:
        nav = '<nav class="seguinte" aria-label="Outras obras">'
        nav += (f'<a href="{ant["slug"]}.html"><span class="rotulo">← Obra {ant["num"]}</span><strong>{e(ant["obra"])}</strong></a>' if ant else "<span></span>")
        nav += (f'<a href="{prox["slug"]}.html"><span class="rotulo">Obra {prox["num"]} →</span><strong>{e(prox["obra"])}</strong></a>' if prox else '<a href="../index.html#obras"><span class="rotulo">Todas as obras →</span><strong>Prancheta</strong></a>')
        nav += "</nav>"

    # "Próximo episódio": o papel da chamada no fim do vídeo. Se o próximo
    # já tem página, leva a ela; se só está anunciado (EM_APURACAO), mostra
    # sem link, com a data de estreia.
    seguinte = ""
    anunciado = next((a for a in EM_APURACAO if int(a["num"]) == int(o["num"]) + 1), None)
    if prox:
        pc = prox["imagens"][0]
        seguinte = f"""<a class="proximo-ep" href="{prox['slug']}.html">
      <div class="foto">{img_tag(pc['arquivo'], pc['alt'], base, '(max-width:640px) 100vw, 260px', foco=pc.get('foco'))}</div>
      <div class="txt">
        <span class="rotulo">Próximo episódio · Obra <b>{e(prox['num'])}</b> · <span class="selo-estreia" data-estreia="{prox['estreia']}" data-no-ar="no ar">estreia {e(data_br(prox['estreia']))}</span></span>
        <h3>{e(prox['obra'])}</h3>
        <span class="onde">{e(prox['lugar'])} · {e(prox['periodo'])}</span>
        <p>{para(prox['impossivel'])}</p>
        <span class="ir">Ler a obra →</span>
      </div>
    </a>"""
    elif anunciado:
        seguinte = f"""<div class="proximo-ep sem-pagina">
      <div class="txt">
        <span class="rotulo">Próximo episódio · Obra <b>{e(anunciado['num'])}</b> · estreia {e(data_br(anunciado['estreia']))}</span>
        <h3>{e(anunciado['obra'])}</h3>
        <span class="onde">{e(anunciado['lugar'])}</span>
        <p>{para(anunciado['impossivel'])}</p>
        <span class="ir">Em apuração</span>
      </div>
    </div>"""

    jsonld = {
        "@context": "https://schema.org", "@type": "Article", "headline": f"{o['obra']}: como foi erguido",
        "description": o["resumo"], "inLanguage": "pt-BR", "url": url,
        "image": f"{DOMINIO}/assets/img/{og}",
        "author": {"@type": "Organization", "name": NOME}, "publisher": {"@type": "Organization", "name": NOME},
        "about": {"@type": "LandmarksOrHistoricalBuildings", "name": o["obra"], "address": o["lugar"]},
    }
    return (cabeca(f"{o['obra']}: como foi erguido — {NOME}", o["resumo"], url, f"{DOMINIO}/assets/img/{og}", base, jsonld, "article")
            + '<div class="progresso" aria-hidden="true"></div>' + topo(base, "obras") + f"""<main id="conteudo">
<header class="capa">
  {img_tag(capa['arquivo'], capa['alt'], base, '100vw', 'eager', foco=capa.get('foco'))}
  <span class="credito-capa">{e(capa['legenda'])} — {credito(capa)}</span>
  <div class="casca">
    <span class="rotulo">Obra <b>{e(o['num'])}</b> · {'Brasil' if o['regiao']=='brasil' else 'Mundo'}</span>
    <h1>{e(o['obra'])}</h1>
    <div class="sub">{e(o['lugar'])} · {e(o['periodo'])}</div>
    <p class="imp">{para(o['impossivel'])}</p>
  </div>
</header>
<section class="cotas" aria-label="A obra em números"><ul>{numeros}</ul></section>
<div class="casca obra-layout">
  <article class="texto">
    <div class="abertura">{''.join(f'<p>{para(p)}</p>' for p in o['abertura'])}</div>

    <h2 id="ficha"><span class="n">FICHA</span>Ficha da obra</h2>
    <table class="ficha">
      <tbody>{ficha}</tbody>
    </table>
    <div class="legenda-conf">{legenda_conf}</div>

    {''.join(h for _, _, h in secoes)}
    {sobra}

    <h2 id="mitos"><span class="n">MITOS</span>O que circula e o que o registro diz</h2>
    <ul class="mitos">{mitos}</ul>

    <section class="video">
      <div>
        <span class="rotulo">Episódio {e(o['num'])} · <span class="selo-estreia" data-estreia="{o['estreia']}" data-no-ar="no ar">estreia {e(data_br(o['estreia'], True))}</span></span>
        <h3>{e(o['titulo_video']) if o['titulo_video'] else 'Episódio em produção'}</h3>
        <p>{e(BORDAO)}</p>
      </div>
      <a class="botao cheio" href="{CANAL}" target="_blank" rel="noopener">Ver no YouTube</a>
    </section>

    {seguinte}

    <h2 id="fontes"><span class="n">FONTES</span>Fontes</h2>
    <ol class="fontes">{fontes}</ol>
    <h3 style="margin-top:2rem">Imagens</h3>
    <ul class="creditos">{creditos}</ul>
  </article>
  <aside class="indice" aria-label="Nesta página">
    <div class="lado-card">
      <span class="rotulo">Ficha rápida</span>
      <dl>
        <div><dt>Onde</dt><dd>{e(o['lugar'])}</dd></div>
        <div><dt>Obra</dt><dd>{e(o['periodo'])}</dd></div>
        <div><dt>Episódio</dt><dd>{e(o['num'])} · {e(data_br(o['estreia']))}</dd></div>
      </dl>
    </div>
    <span class="rotulo">Nesta página</span>
    <ol>{indice_html}</ol>
  </aside>
</div>
{nav}
</main>
<div class="lupa" role="dialog" aria-modal="true" aria-label="Imagem ampliada"><button type="button">Fechar</button><img alt=""><p></p></div>
""" + rodape(base) + consentimento(base) + SCRIPT)


def pagina_404():
    base = "/"  # o 404 é servido em qualquer caminho: endereços absolutos
    return (cabeca(f"Página não encontrada — {NOME}", "Esta página não existe.", DOMINIO + "/404.html",
                   f"{DOMINIO}/assets/img/og-home.jpg", base, {"@context": "https://schema.org", "@type": "WebPage", "name": "404"})
            + topo(base) + f"""<main id="conteudo" class="simples"><div class="casca">
  <div class="cota"><span>erro 404</span></div>
  <h1>Esta viga <span class="destaque">não fecha</span></h1>
  <p>A página que você procurou não existe, ou mudou de endereço. Como o triângulo da nossa marca: parece que leva a algum lugar, mas não leva.</p>
  <div class="botoes"><a class="botao cheio" href="/index.html#obras">Ver as obras</a></div>
</div></main>
""" + rodape(base) + consentimento(base) + SCRIPT)


# --- main ---------------------------------------------------------------------

PRIVACIDADE = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Documento · atualizado em 02 de outubro de 2026</span>
  <h1>Política de privacidade</h1>
  <p class="lead">Um site que cobra fonte dos outros deve ser claro sobre si mesmo. Aqui está o que o {{NOME}} coleta, o que não coleta, quem mais está envolvido e o que você pode exigir.</p>

  <div class="resumo"><strong>O resumo, em três linhas.</strong> Não pedimos cadastro, não temos formulário e não guardamos seu e-mail. O que existe são cookies de publicidade do Google, usados para exibir anúncios. Você pode recusá-los na faixa que aparece na primeira visita, ou desligá-los a qualquer momento nas configurações do Google.</div>

  <h2>1. Quem é o responsável</h2>
  <p>O <strong>{{NOME}}</strong> é um projeto editorial independente, publicado em arquiteturadoimpossivel.com.br, {{CANAL_FRASE}}. Para qualquer assunto desta política — inclusive pedidos de exclusão ou de informação —, o contato é o e-mail divulgado no canal.</p>

  <h2>2. O que coletamos, e o que não</h2>
  <p>Não há cadastro, login, comentários, newsletter nem formulário de contato. Nenhuma página pede seu nome, e-mail, telefone ou documento. Não montamos perfil de leitor e não vendemos nem compartilhamos lista de ninguém, porque lista não existe.</p>
  <p>O que existe é o que qualquer site recebe por ser acessado: o servidor que hospeda estas páginas registra o endereço IP, a data e a hora, a página pedida e o navegador usado. Esses registros servem para segurança e diagnóstico de falha, e não são usados para identificar pessoas.</p>

  <h2>3. Cookies e publicidade</h2>
  <p>Este site exibe anúncios por meio do <strong>Google AdSense</strong>. Para isso, o Google e seus parceiros usam cookies — pequenos arquivos gravados no seu navegador — para selecionar e medir os anúncios.</p>
  <ul>
    <li>O Google, como fornecedor terceirizado, utiliza cookies para exibir anúncios neste site.</li>
    <li>O <strong>cookie DART</strong> permite que o Google veicule anúncios com base nas visitas do usuário a este e a outros sites da internet.</li>
    <li>Parceiros e redes de terceiros também podem usar cookies, identificadores de dispositivo ou tecnologia semelhante para medir e personalizar os anúncios.</li>
    <li>Nenhum desses dados passa por nós: o site não recebe, não armazena e não tem acesso ao que essas redes coletam.</li>
  </ul>
  <p>Você pode desativar a publicidade personalizada — em todos os sites da rede do Google, não só neste — em <a href="https://adssettings.google.com" rel="noopener">adssettings.google.com</a>. As regras completas do Google estão em <a href="https://policies.google.com/technologies/ads?hl=pt-BR" rel="noopener">policies.google.com/technologies/ads</a>, e para sair da publicidade comportamental de várias redes de uma vez existe o <a href="https://www.aboutads.info/choices/" rel="noopener">aboutads.info/choices</a>.</p>
  <p>Todo navegador também permite bloquear ou apagar cookies. Fazer isso não impede a leitura de nada: o conteúdo deste site não depende de cookie para funcionar.</p>

  <h2>4. O que guardamos no seu navegador</h2>
  <p>Uma única coisa, e ela não sai do seu aparelho: quando você responde à faixa de cookies, a escolha fica registrada no armazenamento local do navegador, sob a chave <code>{{CHAVE}}</code>. Serve só para não perguntar de novo a cada página. Não é cookie, não é enviada a servidor nenhum e some quando você limpa os dados do site.</p>

  <h2>5. Conteúdo de terceiros</h2>
  <p>Um único serviço externo participa da exibição destas páginas: o <strong>Google AdSense</strong>, que entrega os anúncios. Se você recusar os cookies na faixa, o anúncio não é sequer carregado, e nem esse pedido acontece.</p>
  <p>O <strong>YouTube</strong> só entra em cena se você clicar num link para o canal: nenhum vídeo é incorporado nestas páginas. Todo o resto — as imagens das fichas de obra e as fontes tipográficas — vem deste mesmo domínio.</p>

  <h2>6. Seus direitos sob a LGPD</h2>
  <p>A Lei nº 13.709/2018 garante a você o direito de confirmar se há tratamento de dados seus, de acessá-los, de corrigi-los, de pedir anonimização ou eliminação, de solicitar portabilidade, de saber com quem foram compartilhados e de revogar consentimento a qualquer momento.</p>
  <p>Aqui o exercício desses direitos é curto, porque a base de dados que poderíamos entregar é praticamente vazia. Ainda assim, qualquer pedido feito pelo contato do canal será respondido. Para os dados que o Google coleta através dos anúncios, o pedido precisa ser feito ao próprio Google — nós exibimos o espaço, mas é ele quem trata esses dados.</p>

  <h2>7. Crianças e adolescentes</h2>
  <p>O conteúdo deste site não se dirige a menores de 13 anos, e não coletamos conscientemente dados de crianças. Se você é responsável por uma criança e acredita que algum dado dela chegou até aqui, entre em contato para que seja eliminado.</p>

  <h2>8. Mudanças nesta política</h2>
  <p>Se algo mudar — uma nova rede de anúncios, uma ferramenta de medição, uma área de comentários —, esta página muda junto, e a data no topo é atualizada.</p>

  <div class="botoes" style="margin-top:2.5rem"><a class="botao cheio" href="index.html#obras">Ver as obras</a></div>
</div></main>
"""


def pagina_privacidade():
    """Escrita para ESTE site, não copiada de modelo: diz só o que ele faz.
    Adaptada da política do Vestígio Oculto, que tem o mesmo desenho."""
    base = ""
    if CANAL:
        canal = f'com canal correspondente no YouTube, <a href="{CANAL}" target="_blank" rel="noopener">@ArquiteturadoImpossível</a>'
    else:
        canal = "com canal correspondente no YouTube"
    corpo = (PRIVACIDADE.replace("{{NOME}}", NOME).replace("{{CANAL_FRASE}}", canal)
             .replace("{{CHAVE}}", CHAVE_CONSENTIMENTO))
    return (cabeca(f"Política de privacidade — {NOME}",
                   f"Como o {NOME} trata dados, cookies e publicidade, e quais são os seus direitos sob a LGPD.",
                   DOMINIO + "/privacidade.html", f"{DOMINIO}/assets/img/og-home.jpg", base,
                   {"@context": "https://schema.org", "@type": "WebPage", "name": "Política de privacidade"})
            + topo(base) + corpo + rodape(base) + consentimento(base) + SCRIPT)


def pagina_sobre():
    base = ""
    canal = f'<a href="{CANAL}" target="_blank" rel="noopener">@ArquiteturadoImpossível</a>' if CANAL else "no YouTube"
    corpo = f"""<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Sobre</span>
  <h1>Sobre o {NOME}</h1>

  <h2>1. O que é</h2>
  <p>O <strong>Arquitetura do Impossível</strong> é um projeto editorial independente, feito no Brasil, sobre grandes construções: como uma obra que parecia impossível ficou de pé. Cada página deste site acompanha um episódio do canal no YouTube, {canal}, e vai além dele: traz a ficha técnica completa, as fontes, as imagens com crédito e as divergências que não cabem num vídeo.</p>
  <p>A pergunta é sempre a mesma: <em>o que tornava esta obra impossível, e quem resolveu</em> — com que conta, com que material, com que improviso. O protagonista é o problema de engenharia; as pessoas entram como quem o enfrentou. Um episódio do Brasil, um do resto do mundo, alternados.</p>

  <h2>2. Como uma página é feita</h2>
  <ul>
    <li><strong>A ficha de toda obra cobre o que costuma faltar:</strong> quantos operários, quanto tempo, quanto custou, quem se feriu e quem morreu — cada linha com fonte.</li>
    <li><strong>Cada número leva um selo de confiança:</strong> confirmado em duas ou mais fontes, fonte única (o texto diz qual), divergência (mostramos as versões e não escolhemos) ou sem registro (dizemos que ninguém registrou, em vez de inventar).</li>
    <li><strong>O mito desmontado é parte da história:</strong> o operário enterrado no concreto, a obra "feita em X dias", a conta de mortos que ninguém conferiu.</li>
    <li><strong>Valor de hoje só com método declarado.</strong> Converter dinheiro antigo sem dizer como é inventar número.</li>
    <li><strong>Texto integralmente autoral.</strong> As fontes ficam listadas no fim de cada página.</li>
  </ul>

  <h2>3. Imagens</h2>
  <p>Só entram fotografias, plantas e documentos reais, de acervos em domínio público ou sob licença Creative Commons que permite uso comercial, com autor e licença creditados em cada página. Imagem gerada por IA não entra neste site.</p>

  <h2>4. Correções</h2>
  <p>Errou-se uma data, um nome, um número? Escreva pela página de <a href="contato.html">contato</a>, de preferência com a fonte. O erro confirmado é corrigido aqui, e a correção vale também para o que vier depois no canal.</p>

  <h2>5. Quem faz</h2>
  <p>O {NOME} é escrito, apurado e mantido de forma independente, sem vínculo com universidade, empresa ou órgão público. É do mesmo criador de outros dois projetos com o mesmo cuidado com a fonte: <a href="https://vestigiooculto.com.br" rel="noopener">Vestígio Oculto</a>, sobre arqueologia e mistério, e <a href="https://xadrezbelico.com.br" rel="noopener">Xadrez Bélico</a>, sobre batalhas explicadas como partida.</p>
  <p>O site se mantém com anúncios do Google AdSense, descritos na <a href="privacidade.html">política de privacidade</a>. Nenhum anúncio interfere no que é escrito.</p>
</div></main>
"""
    return (cabeca(f"Sobre — {NOME}", f"O que é o {NOME}, como cada página é apurada, de onde vêm as imagens e quem faz o projeto.",
                   DOMINIO + "/sobre.html", f"{DOMINIO}/assets/img/og-home.jpg", base,
                   {"@context": "https://schema.org", "@type": "AboutPage", "name": f"Sobre — {NOME}"})
            + topo(base, "sobre") + corpo + rodape(base) + consentimento(base) + SCRIPT)


def pagina_contato():
    base = ""
    corpo = f"""<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Contato</span>
  <h1>Fale com o {NOME}</h1>
  <p class="lead">Correção, crédito de imagem, pedido sobre seus dados ou qualquer outro assunto: o caminho é um só.</p>
  <div class="resumo"><strong>E-mail:</strong> <a href="mailto:allangipa@gmail.com">allangipa@gmail.com</a></div>

  <h2>Para que escrever</h2>
  <ul>
    <li><strong>Correções.</strong> Uma data, um nome ou um número errado. Mande a fonte junto: é o que permite corrigir rápido.</li>
    <li><strong>Imagens e créditos.</strong> Se você é autor de uma imagem usada aqui e o crédito está incompleto, ou quer que ela saia, escreva.</li>
    <li><strong>Seus dados.</strong> Pedidos sob a LGPD, conforme a <a href="privacidade.html">política de privacidade</a>.</li>
    <li><strong>Pautas, imprensa e parcerias.</strong> Sugestões de tema também são bem-vindas.</li>
  </ul>

  <h2>Como respondemos</h2>
  <p>Não há formulário nem cadastro: a conversa é por e-mail, e o seu endereço não é usado para mais nada além de responder. Correção confirmada entra na página.</p>
</div></main>
"""
    return (cabeca(f"Contato — {NOME}", f"Como falar com o {NOME}: correções, créditos de imagem, pedidos sobre dados e pautas.",
                   DOMINIO + "/contato.html", f"{DOMINIO}/assets/img/og-home.jpg", base,
                   {"@context": "https://schema.org", "@type": "ContactPage", "name": f"Contato — {NOME}"})
            + topo(base, "contato") + corpo + rodape(base) + consentimento(base) + SCRIPT)

def main():
    obras = carregar()
    (RAIZ / "obras").mkdir(exist_ok=True)
    (RAIZ / "assets").mkdir(exist_ok=True)

    css = (SRC / "arquitetura.css").read_text(encoding="utf-8").replace("url(/assets/fontes/", "url(fontes/")
    (RAIZ / "assets" / "arquitetura.css").write_text(css, encoding="utf-8")
    (RAIZ / "favicon.svg").write_text(simbolo("0 0 1020 886", rotulo=NOME), encoding="utf-8")

    og = {o["slug"]: og_obra(o) for o in obras}
    (RAIZ / "index.html").write_text(home(obras, og_home()), encoding="utf-8")
    gerados = {"index.html"}
    for o in obras:
        (RAIZ / "obras" / f"{o['slug']}.html").write_text(pagina_obra(o, obras, og[o["slug"]]), encoding="utf-8")
        gerados.add(f"obras/{o['slug']}.html")
    for velho in (RAIZ / "obras").glob("*.html"):
        if f"obras/{velho.name}" not in gerados:
            velho.unlink()
            print("removido (obra sem JSON):", velho.name)
    (RAIZ / "404.html").write_text(pagina_404(), encoding="utf-8")
    (RAIZ / "privacidade.html").write_text(pagina_privacidade(), encoding="utf-8")
    (RAIZ / "sobre.html").write_text(pagina_sobre(), encoding="utf-8")
    (RAIZ / "contato.html").write_text(pagina_contato(), encoding="utf-8")
    ads = RAIZ / "ads.txt"
    if ADSENSE_LIGADO:
        ads.write_text("# Declaração de vendedor autorizado (IAB ads.txt)\n"
                       "# Gerado por _src/build.py a partir de ADSENSE_PUB. Não editar à mão.\n"
                       f"google.com, {ADSENSE_PUB}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    elif ads.exists():
        ads.unlink()

    hoje = dt.date.today().isoformat()
    urls = [DOMINIO + "/", DOMINIO + "/sobre.html", DOMINIO + "/contato.html", DOMINIO + "/privacidade.html"] + [f"{DOMINIO}/obras/{o['slug']}.html" for o in obras]
    (RAIZ / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{hoje}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /_src/\n\nSitemap: {DOMINIO}/sitemap.xml\n", encoding="utf-8")

    print(f"ok: {len(obras)} obras, {len(EM_APURACAO)} em apuração")
    for o in obras:
        print(f"  {o['num']} {o['obra']}: {len(o['ficha'])} linhas de ficha, {len(o['historia'])} seções, {len(o['imagens'])} imagens")


if __name__ == "__main__":
    main()
