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

Idiomas (desde 03/10/2026): o português fica na raiz, com os caminhos de
sempre; cada outro idioma ganha uma pasta (`en/`, `es/`) com os mesmos slugs.
Um idioma entra no ar quando existe `_src/i18n/<id>.json` (os textos da
interface); uma obra sai nele quando existe `_src/obras/<id>/NN-slug.json` e a
tradução passa nas travas de `traduzir()` — campo faltando, número que não
bate com o original, texto não traduzido: o build para.
"""
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "_src"
IMG = RAIZ / "assets" / "img"

# Domínio principal desde 03/10/2026. O .com.br continua apontando para os
# mesmos arquivos e redireciona 301, caminho a caminho, pelo .htaccess.
DOMINIO = "https://arquiteturadoimpossivel.com"
SITE_IRMAO_VO = "https://vestigiooculto.com.br"
SITE_IRMAO_XB = "https://xadrezbelico.com"
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
EM_APURACAO = []

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
    """Data por extenso no idioma da página (o nome ficou por história)."""
    d = dt.date.fromisoformat(iso)
    if longa:
        return cfg("data_longa").format(dia=d.day, mes=cfg("meses")[d.month - 1], ano=d.year)
    return cfg("data_curta").format(dia=d.day, mes=cfg("meses_curtos")[d.month - 1], ano=d.year)


def falha(msg):
    raise SystemExit("PARADO: " + msg)


# --- idiomas ------------------------------------------------------------------
# Português na raiz, com os caminhos de sempre; cada outro idioma numa pasta
# (en/, es/), com os MESMOS slugs (o hreflang casa página com página sem
# tabela de correspondência). Ordem = ordem do seletor. Só fica ativo o idioma
# que tem _src/i18n/<id>.json; e só sai nele a página que tem tradução.
IDIOMAS = ["pt", "en", "es"]
BASE_IDIOMA = "pt"
PASTA_ITENS = "obras"            # _src/obras/ e obras/<slug>.html
I18N_DIR = SRC / "i18n"
CONFIG_PT = {
    "nome": "Português", "curto": "PT", "hreflang": "pt-BR", "og_locale": "pt_BR",
    # subtítulo da marca nos outros idiomas ("Arquitetura do Impossível — Impossible
    # Architecture"); em português a marca é só o nome
    "marca_sub": "",
    "meses": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
              "setembro", "outubro", "novembro", "dezembro"],
    "meses_curtos": MESES,
    "data_longa": "{dia} de {mes} de {ano}",
    "data_curta": "{dia:02d} {mes} {ano}",
}
CHAVES_IDIOMA = set(CONFIG_PT)
I18N = {BASE_IDIOMA: {"_idioma": CONFIG_PT, "textos": {}}}
ATIVOS = [BASE_IDIOMA]
L = BASE_IDIOMA                  # idioma da página que está sendo gerada
PAGINA = "index.html"            # chave (caminho em português) da página atual
EXISTE = defaultdict(set)        # idioma -> chaves de página geradas nele
FALTANDO = defaultdict(set)      # idioma -> textos da interface sem tradução
USADOS = defaultdict(set)


def carregar_idiomas():
    """Lê _src/i18n/<id>.json: {"_idioma": {...como CONFIG_PT}, "textos":
    {"texto em português": "tradução"}}. A chave é o próprio texto em
    português: mudou o original, a tradução deixa de casar e o build para."""
    for lg in IDIOMAS:
        if lg == BASE_IDIOMA:
            continue
        arq = I18N_DIR / f"{lg}.json"
        if not arq.exists():
            continue
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            falha(f"i18n/{lg}.json não é JSON válido: {ex}")
        conf = d.get("_idioma") or {}
        falta = CHAVES_IDIOMA - set(conf)
        if falta:
            falha(f"i18n/{lg}.json: _idioma sem {sorted(falta)}")
        if len(conf["meses"]) != 12 or len(conf["meses_curtos"]) != 12:
            falha(f"i18n/{lg}.json: meses e meses_curtos precisam de 12 nomes")
        for k, v in (d.get("textos") or {}).items():
            if set(re.findall(r"\{(\w+)", k)) != set(re.findall(r"\{(\w+)", v)):
                falha(f"i18n/{lg}.json: marcadores {{…}} diferentes entre original e tradução: {k!r}")
            b = BASTIDOR.search(v) or BASTIDOR_TRAD.search(v)
            if b:
                falha(f"i18n/{lg}.json: bastidor no texto ({b.group(0)!r}): {v!r}")
        I18N[lg] = {"_idioma": conf, "textos": d.get("textos") or {}}
        ATIVOS.append(lg)


def tr(s, **kw):
    """Texto da interface no idioma da página. Em português devolve o próprio
    texto; nos outros, a tradução do dicionário — e anota o que faltar, para o
    build parar no fim em vez de publicar meia página em português."""
    if L != BASE_IDIOMA:
        USADOS[L].add(s)
        t = I18N[L]["textos"].get(s)
        if t and t.strip():
            s = t
        else:
            FALTANDO[L].add(s)
    return s.format(**kw) if kw else s


def cfg(k):
    return I18N[L]["_idioma"][k]


def prefixo(lg):
    return "" if lg == BASE_IDIOMA else f"{lg}/"


def url_de(lg, chave):
    """Endereço absoluto da página `chave` (caminho em português) no idioma lg."""
    return f"{DOMINIO}/{prefixo(lg)}{'' if chave == 'index.html' else chave}"


def link(base, chave, ancora=""):
    """href relativo para a página `chave` no idioma da página atual; se ela
    ainda não existe nesse idioma, cai no português (nunca num 404)."""
    lg = L if chave in EXISTE[L] else BASE_IDIOMA
    return f"{base}{prefixo(lg)}{chave}{ancora}"


def hreflang_de(chave):
    """' hreflang="pt-BR"' quando o link cai no português dentro de outro idioma."""
    if L != BASE_IDIOMA and chave not in EXISTE[L]:
        return f' hreflang="{CONFIG_PT["hreflang"]}"'
    return ""


def idiomas_da(chave):
    return [lg for lg in ATIVOS if chave in EXISTE[lg]]


def alternativos(chave):
    """[(hreflang, url)] da página em todos os idiomas em que ela existe, mais
    x-default (inglês quando existe, senão português). Vazio se só há um."""
    lgs = idiomas_da(chave)
    if len(lgs) < 2:
        return []
    alt = [(I18N[lg]["_idioma"]["hreflang"], url_de(lg, chave)) for lg in lgs]
    padrao = "en" if "en" in lgs else BASE_IDIOMA
    return alt + [("x-default", url_de(padrao, chave))]


def seletor_idioma(base):
    """Links para a mesma página nos outros idiomas — só os que existem."""
    lgs = idiomas_da(PAGINA)
    if len(lgs) < 2:
        return ""
    itens = []
    for lg in lgs:
        c = I18N[lg]["_idioma"]
        atual = ' aria-current="true"' if lg == L else ""
        itens.append(f'<a class="idioma" href="{base}{prefixo(lg)}{PAGINA}" hreflang="{c["hreflang"]}" lang="{c["hreflang"]}" '
                     f'aria-label="{e(c["nome"])}" title="{e(c["nome"])}"{atual}>{e(c["curto"])}</a>')
    return f'<div class="idiomas" role="group" aria-label="{e(tr("Idioma"))}">{"".join(itens)}</div>'


def marca_completa():
    sub = cfg("marca_sub")
    return f"{NOME} — {sub}" if sub else NOME


def licenca_rotulo(lic):
    return tr("Domínio público") if re.match(r"dom[ií]nio p[uú]blico$", lic.strip(), re.I) else lic


# --- tradução de conteúdo: travas -----------------------------------------------
# Campos que não se traduzem: se a tradução os trouxer, têm de ser idênticos;
# se omitir, vêm do original.
CAMPOS_FIXOS = {"num", "slug", "regiao", "estreia", "proximo", "relacionados", "conf",
                "arquivo", "licenca", "licenca_url", "origem_url", "recriacao", "foco", "url"}
# Campos que a tradução pode ter mesmo que o original não tenha.
EXTRAS_TRAD = {"titulo_seo", "_excecoes_numeros", "_nota"}
# Texto citado (título de obra, de artigo) pode ficar igual ao original.
PODE_FICAR_IGUAL = re.compile(r"^fontes\[\d+\]\.texto$|\.autor$")
# TODO/TBD/FIXME só em caixa alta: em espanhol "todo" é palavra comum; e
# "pendiente" sozinho também é "declive" (a serra, a rampa): só conta
# "pendiente de verificar/confirmar".
BASTIDOR_TRAD = re.compile(r"(?-i:\bTODO\b|\bTBD\b|\bFIXME\b)|\[\?\]|\bto (?:check|verify|confirm)\b"
                           r"|\b(?:por|pendiente de) (?:verificar|confirmar)\b", re.I)

MESES_NOMES = {
    "pt": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
           "setembro", "outubro", "novembro", "dezembro"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre|setiembre", "octubre", "noviembre", "diciembre"],
}
MULTIPLICADOR = [  # o mais longo antes ("mil millones" = bilhão)
    (r"mil\s+millones", 10 ** 9), (r"bilh(?:ão|ões)|billions?", 10 ** 9),
    (r"milh(?:ão|ões)|millions?|millón|millones", 10 ** 6), (r"mil|thousand", 10 ** 3),
]
_MULT = "|".join(f"(?:{p})" for p, _ in MULTIPLICADOR)
_NUM = r"(?<![\w.,/:])(\d+(?:[.,]\d+)*)"


def _valor(s, lg):
    dec, mil = (".", ",") if lg == "en" else (",", ".")
    if re.fullmatch(rf"\d{{1,3}}(?:\{mil}\d{{3}})+(?:\{dec}\d+)?", s):
        s = s.replace(mil, "")
    s = s.replace(dec, ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def numeros_do_texto(txt, lg):
    """Multiconjunto dos números do texto, normalizados: 1.000 (pt) = 1,000 (en)
    = 1000; "20 mil" = "20,000"; "250–300 mil" = 250000 e 300000; 3/11/1924 =
    3 + novembro + 1924; o mês por extenso conta como número (M11)."""
    t = re.sub(r"(?<![\d/])(\d{1,2})/(\d{1,2})/(\d{4})\b", lambda m: f"{m[1]} §M{int(m[2])}§ {m[3]}", txt)
    c = Counter()
    for m in re.finditer(r"§M(\d+)§", t):
        c[f"M{int(m[1])}"] += 1
    # mês na caixa da ortografia (minúsculo em pt/es, maiúsculo em en):
    # "Rio de Janeiro" não é janeiro, e "may" (verbo) não é May
    for i, nomes in enumerate(MESES_NOMES[lg]):
        n = len(re.findall(rf"\b(?:{nomes})\b", t))
        if n:
            c[f"M{i + 1}"] += n
    # faixa com multiplicador no fim: "250–300 mil" → os dois lados multiplicam
    def faixa(m):
        mult = next(v for p, v in MULTIPLICADOR if re.fullmatch(p, m[3], re.I))
        a, b = _valor(m[1], lg), _valor(m[2], lg)
        if a is None or b is None:
            return m[0]
        # o primeiro lado só herda o multiplicador se veio "abreviado":
        # "250–300 mil" sim; "de 800.000 a 1,5 milhão" não
        return f"§N{a * mult if a < 1000 else a}§ – §N{b * mult}§"
    t = re.sub(_NUM + r"\s*(?:–|-|a|to|y|e|ou|or|o)\s*" + r"(\d+(?:[.,]\d+)*)\s+(" + _MULT + r")\b", faixa, t, flags=re.I)
    for m in re.finditer(r"§N([\d.]+)§", t):
        c[format(Decimal(m[1]).normalize(), "f")] += 1
    t = re.sub(r"§N[\d.]+§", " ", t)
    for m in re.finditer(_NUM + r"(?:\s+(" + _MULT + r")\b)?", t, re.I):
        v = _valor(m[1], lg)
        if v is None:
            continue
        if m[2]:
            v *= next(val for p, val in MULTIPLICADOR if re.fullmatch(p, m[2], re.I))
        c[format(v.normalize(), "f")] += 1
    return c


def conferir_numeros(orig, trad, lg, onde, excecoes):
    a, b = numeros_do_texto(orig, BASE_IDIOMA), numeros_do_texto(trad, lg)
    for x in excecoes:
        a.pop(x, None)
        b.pop(x, None)
    falta = a - b
    sobra = Counter({k: v for k, v in (b - a).items() if not k.startswith("M")})
    erros = []
    if falta:
        erros.append(f"{onde}: número do original ausente na tradução {dict(falta)}")
    if sobra:
        erros.append(f"{onde}: número na tradução que o original não tem {dict(sobra)}")
    return erros


def fundir_traducao(orig, trad, lg, onde="", excecoes=(), erros=None):
    """Confere a tradução contra o original, campo a campo, e devolve o objeto
    completo (campos fixos vêm do original). Acumula os erros em `erros`."""
    if isinstance(orig, dict):
        if not isinstance(trad, dict):
            erros.append(f"{onde or 'raiz'}: esperava objeto")
            return orig
        out = {}
        for k, v in orig.items():
            caminho = f"{onde}.{k}" if onde else k
            if k in CAMPOS_FIXOS:
                if k in trad and trad[k] != v:
                    erros.append(f"{caminho}: campo fixo diferente do original ({trad[k]!r} ≠ {v!r})")
                out[k] = v
            elif k not in trad:
                if v in (None, [], ""):
                    out[k] = v
                else:
                    erros.append(f"{caminho}: falta na tradução")
            else:
                out[k] = fundir_traducao(v, trad[k], lg, caminho, excecoes, erros)
        for k in trad:
            if k not in orig:
                if k in EXTRAS_TRAD:
                    out[k] = trad[k]
                else:
                    erros.append(f"{onde + '.' if onde else ''}{k}: campo que o original não tem")
        return out
    if isinstance(orig, list):
        if not isinstance(trad, list) or len(trad) != len(orig):
            erros.append(f"{onde}: a lista tem de ter {len(orig)} itens, como o original")
            return orig
        return [fundir_traducao(o, t, lg, f"{onde}[{i}]", excecoes, erros) for i, (o, t) in enumerate(zip(orig, trad))]
    if isinstance(orig, str):
        if not isinstance(trad, str) or not trad.strip():
            erros.append(f"{onde}: texto vazio na tradução")
            return orig
        erros += conferir_numeros(orig, trad, lg, onde, excecoes)
        if trad.strip() == orig.strip() and len(orig) >= 25 and " " in orig and not PODE_FICAR_IGUAL.search(onde):
            erros.append(f"{onde}: igual ao português — não traduzido?")
        b = BASTIDOR.search(trad) or BASTIDOR_TRAD.search(trad)
        if b:
            erros.append(f"{onde}: bastidor de produção ({b.group(0)!r})")
        return trad
    if trad != orig:
        erros.append(f"{onde}: valor {trad!r} diferente do original {orig!r}")
    return orig


def carregar_traducoes(itens, campos_obrigatorios, nome_item):
    """{idioma: {slug: item traduzido}} a partir de _src/<pasta>/<id>/NN-slug.json."""
    por_slug = {x["slug"]: x for x in itens}
    trads = {}
    for lg in ATIVOS:
        if lg == BASE_IDIOMA:
            continue
        trads[lg] = {}
        for f in sorted((SRC / PASTA_ITENS / lg).glob("[0-9][0-9]-*.json")):
            try:
                t = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as ex:
                falha(f"{PASTA_ITENS}/{lg}/{f.name} não é JSON válido: {ex}")
            orig = next((x for x in itens if f.name == f"{x['num']}-{x['slug']}.json"), None)
            if orig is None:
                falha(f"{PASTA_ITENS}/{lg}/{f.name}: não há {nome_item} com esse nome em _src/{PASTA_ITENS}/")
            erros = []
            exc = [format(_valor(x, BASE_IDIOMA).normalize(), "f") if re.fullmatch(r"[\d.,]+", x) else x
                   for x in t.get("_excecoes_numeros", [])]
            obj = fundir_traducao(orig, t, lg, "", exc, erros)
            falta = [c for c in campos_obrigatorios if c not in obj]
            if falta:
                erros.append(f"faltam campos obrigatórios {falta}")
            if erros:
                falha(f"tradução {PASTA_ITENS}/{lg}/{f.name} incompleta ou divergente:\n  " + "\n  ".join(erros))
            obj.pop("_excecoes_numeros", None)
            obj.pop("_nota", None)
            obj["_arquivo"] = f
            trads[lg][obj["slug"]] = obj
    return trads


def carregar_temas_traduzidos(temas, membros_por_idioma):
    """_src/temas.<id>.json: [{slug, nome, titulo, resumo, intro}] com os mesmos
    slugs de temas.json; a lista de membros vem do original. O tema só sai no
    idioma se tiver 2 ou mais membros traduzidos."""
    out = {}
    por_slug = {t["slug"]: t for t in temas}
    for lg in ATIVOS:
        if lg == BASE_IDIOMA:
            continue
        out[lg] = []
        arq = SRC / f"temas.{lg}.json"
        if not arq.exists():
            continue
        for tt in json.loads(arq.read_text(encoding="utf-8")):
            orig = por_slug.get(tt.get("slug"))
            if orig is None:
                falha(f"temas.{lg}.json: tema '{tt.get('slug')}' não existe em temas.json")
            erros = []
            base = {k: v for k, v in orig.items() if k != CHAVE_MEMBROS}
            obj = fundir_traducao(base, tt, lg, f"tema {orig['slug']}", (), erros)
            if erros:
                falha(f"temas.{lg}.json:\n  " + "\n  ".join(erros))
            obj[CHAVE_MEMBROS] = [s for s in orig[CHAVE_MEMBROS] if s in membros_por_idioma[lg]]
            if len(obj[CHAVE_MEMBROS]) >= 2:
                out[lg].append(obj)
    return out


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
ROTULO_LEIA = "MAIS"


def ITEM_LEIA(y, base="../"):
    ch = f"obras/{y['slug']}.html"
    return (f'<li><a href="{link(base, ch)}"{hreflang_de(ch)}><span class="rotulo">{e(tr("Obra"))} <b>{e(y["num"])}</b> · {e(y["lugar"].split(",")[-1].strip())}</span>'
            f'<strong>{e(y["obra"])}</strong><span class="onde">{e(y["periodo"])}</span></a></li>')


def conferir_relacionados(x, slugs):
    """`relacionados` (opcional): três slugs do MESMO site, de assunto
    próximo, para o bloco "Leia também". Para se o slug não existir, se
    repetir, se apontar para a própria página ou para o `proximo` (que já
    tem bloco próprio)."""
    rel = x.get("relacionados")
    if rel is None:
        return
    if not isinstance(rel, list) or len(rel) != 3 or len(set(rel)) != 3:
        falha(f"{x['slug']}: relacionados deve ter 3 slugs diferentes: {rel!r}")
    for s in rel:
        if s not in slugs:
            falha(f"{x['slug']}: relacionado '{s}' não existe")
        if s == x["slug"]:
            falha(f"{x['slug']}: relacionado aponta para a própria página")
        if s == x["proximo"]:
            falha(f"{x['slug']}: relacionado '{s}' já é o próximo episódio")


def leia_tambem(x, todos):
    """Bloco "Leia também": três links internos de assunto próximo."""
    rel = x.get("relacionados") or []
    temas = temas_de(x["slug"])
    if not rel and not temas:
        return ""
    base = "../../" if L != BASE_IDIOMA else "../"
    por_slug = {y["slug"]: y for y in todos}
    itens = "".join(ITEM_LEIA(por_slug[s], base) for s in rel)
    lista = f"<ul>{itens}</ul>" if itens else ""
    links = ""
    if temas:
        links = (f'<p class="temas-link"><span class="rotulo">{e(tr("Tema"))}</span> '
                 + " · ".join(f'<a href="{link(base, "temas/" + t["slug"] + ".html")}"{hreflang_de("temas/" + t["slug"] + ".html")}>{e(t["nome"])}</a>' for t in temas) + "</p>")
    return (f'<section class="leia" aria-labelledby="leia"><h2 id="leia"><span class="n">{e(tr(ROTULO_LEIA))}</span>{e(tr("Leia também"))}</h2>'
            f'{lista}{links}</section>')


def conferir_perguntas(nome, x):
    """`perguntas` (opcional): 3 a 5 itens {"p": "…?", "r": "…"}. O texto
    passa pela mesma trava de bastidor do resto da página (a conferência
    abaixo, em carregar(), lê o JSON inteiro menos imagens e fontes)."""
    ps = x.get("perguntas")
    if ps is None:
        return
    if not isinstance(ps, list) or not 3 <= len(ps) <= 5:
        falha(f"{nome}: perguntas deve ter de 3 a 5 itens")
    for it in ps:
        if not isinstance(it, dict) or set(it) != {"p", "r"} or not it["p"].strip() or not it["r"].strip():
            falha(f"{nome}: pergunta malformada {it!r}")
        if not it["p"].strip().endswith("?"):
            falha(f"{nome}: pergunta sem '?': {it['p']!r}")
        m = BASTIDOR.search(it["p"] + " " + it["r"])
        if m:
            falha(f"{nome}: bastidor de produção numa pergunta ({m.group(0)!r}): {it['p']!r}")


def perguntas_html(x):
    """Seção "Perguntas frequentes" (h2 + h3/p). Sem JSON-LD de FAQ, de propósito."""
    ps = x.get("perguntas") or []
    if not ps:
        return ""
    itens = "".join(f"<h3>{e(it['p'])}</h3><p>{para(it['r'])}</p>" for it in ps)
    return f'<h2 id="perguntas"><span class="n">{e(tr(ROTULO_PERGUNTAS))}</span>{e(tr("Perguntas frequentes"))}</h2><div class="perguntas">{itens}</div>'


ROTULO_PERGUNTAS = "PERGUNTAS"

# --- temas ------------------------------------------------------------------
# Páginas-índice por assunto, em temas/<slug>.html, a partir de _src/temas.json.
TEMAS = []
CHAVE_MEMBROS = "obras"


def carregar_temas(itens):
    arq = SRC / "temas.json"
    if not arq.exists():
        return []
    try:
        temas = json.loads(arq.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        falha(f"temas.json não é JSON válido: {ex}")
    slugs = {x["slug"] for x in itens}
    vistos = set()
    for t in temas:
        for k in ("slug", "nome", "titulo", "resumo", "intro", CHAVE_MEMBROS):
            if not t.get(k):
                falha(f"tema sem '{k}': {t.get('slug')}")
        if not re.fullmatch(r"[a-z0-9-]+", t["slug"]) or t["slug"] in vistos:
            falha(f"tema com slug inválido ou repetido: {t['slug']!r}")
        vistos.add(t["slug"])
        if not 2 <= len(t["intro"]) <= 3:
            falha(f"tema {t['slug']}: a introdução tem de ter 2 ou 3 parágrafos")
        m = t[CHAVE_MEMBROS]
        if len(m) < 2 or len(set(m)) != len(m):
            falha(f"tema {t['slug']}: precisa de 2 ou mais itens, sem repetir")
        for s in m:
            if s not in slugs:
                falha(f"tema {t['slug']}: '{s}' não existe")
        texto = json.dumps(t, ensure_ascii=False)
        b = BASTIDOR.search(texto)
        if b:
            falha(f"tema {t['slug']}: bastidor de produção no texto público ({b.group(0)!r})")
    return temas


def titulo_tema(t):
    for x in (f"{t['titulo']} · {NOME}", t["titulo"]):
        if len(x) <= TITULO_MAX:
            return x
    falha(f"tema {t['slug']}: título com mais de {TITULO_MAX} caracteres")


def temas_de(slug):
    return [t for t in TEMAS if slug in t[CHAVE_MEMBROS]]


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
        conferir_perguntas(f.name, o)
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
        conferir_relacionados(o, slugs)
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
    priv = f'<a href="{link(base, "privacidade.html")}"{hreflang_de("privacidade.html")}>{e(tr("política de privacidade"))}</a>'
    return f"""<div class="consentimento" id="consentimento" role="dialog" aria-live="polite" aria-label="{e(tr('Aviso de cookies'))}" hidden>
  <div class="casca">
    <p>{e(tr("Este site usa cookies do Google AdSense para exibir e medir anúncios. Não pedimos cadastro nem e-mail."))} {tr("Detalhes na {politica}.", politica=priv)}</p>
    <div class="botoes">
      <button type="button" data-consent="recusar">{e(tr("Recusar anúncios"))}</button>
      <button type="button" data-consent="aceitar" class="principal">{e(tr("Entendi"))}</button>
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
  // "Rever escolha de cookies", no rodapé: apaga a escolha salva e recarrega,
  // e a faixa volta a aparecer.
  document.querySelectorAll('[data-rever-cookies]').forEach(function(a){{
    a.addEventListener('click',function(ev){{
      ev.preventDefault();
      try{{localStorage.removeItem(CHAVE)}}catch(e){{}}
      location.reload();
    }});
  }});
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

def css_inline():
    """O CSS vai dentro do <head>: um arquivo de ~6 KB comprimido custava uma
    ida e volta inteira bloqueando a primeira pintura (PageSpeed, 03/10/2026).
    Fontes com caminho absoluto, porque o <style> resolve a partir da página."""
    css = (SRC / "arquitetura.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r"\n\s*\n+", "\n", css).strip()


CSS_INLINE = None


def cabeca(titulo, descricao, url, imagem, base, jsonld, tipo="website", indexar=True, extra=""):
    global CSS_INLINE
    if CSS_INLINE is None:
        CSS_INLINE = css_inline()
    # 404: noindex e sem canonical (é servido em qualquer endereço)
    # max-image-preview:large: deixa o Google Discover usar a og:image grande
    canon = (f'<link rel="canonical" href="{e(url)}">\n'
             '<meta name="robots" content="max-image-preview:large">') if indexar else '<meta name="robots" content="noindex, follow">'
    lds = jsonld if isinstance(jsonld, list) else [jsonld]
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in lds)
    alt = alternativos(PAGINA) if indexar else []
    if alt:
        canon += "\n" + "\n".join(f'<link rel="alternate" hreflang="{h}" href="{e(u)}">' for h, u in alt)
    locs = "".join(f'\n<meta property="og:locale:alternate" content="{I18N[lg]["_idioma"]["og_locale"]}">'
                   for lg in idiomas_da(PAGINA) if lg != L) if indexar else ""
    return f"""<!doctype html>
<html lang="{cfg('hreflang')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descricao)}">
{canon}
<meta name="theme-color" content="#0F2A44">
<link rel="icon" href="{base}favicon.svg" type="image/svg+xml">
<link rel="preload" href="{base}assets/fontes/barlow-condensed-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{base}assets/fontes/ibm-plex-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
{extra}
{adsense_head()}
<style>{CSS_INLINE}</style>
<meta property="og:type" content="{tipo}">
<meta property="og:site_name" content="{e(marca_completa())}">
<meta property="og:locale" content="{cfg('og_locale')}">{locs}
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descricao)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(imagem)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
{ld}
</head>
<body>
<a class="pular" href="#conteudo">{e(tr("Pular para o conteúdo"))}</a>
"""


def topo(base, atual=""):
    cur = lambda k: ' aria-current="page"' if k == atual else ""
    sub = f'<small class="marca-sub" lang="{cfg("hreflang")}">{e(cfg("marca_sub"))}</small>' if cfg("marca_sub") else ""
    return f"""<header class="topo">
  <div class="casca">
    <a class="marca" href="{link(base, 'index.html')}"{'' if L == BASE_IDIOMA else ' lang="pt-BR"'}>{SIMBOLO_PEQUENO()}<span>Arquitetura <em>do Impossível</em>{sub}</span></a>
    <nav class="nav" aria-label="{e(tr('Principal'))}">
      <a href="{link(base, 'index.html', '#obras')}"{cur('obras')}>{e(tr('Obras'))}</a>
      <a href="{link(base, 'index.html', '#metodo')}"{cur('metodo')}>{e(tr('Método'))}</a>
      <a href="{link(base, 'sobre.html')}"{hreflang_de('sobre.html')}{cur('sobre')}>{e(tr('Sobre'))}</a>
      <a class="yt" href="{CANAL}" target="_blank" rel="noopener">YouTube</a>{seletor_idioma(base)}
    </nav>
  </div>
</header>
"""


def rodape(base):
    ano = dt.date.today().year
    rever = f' <a href="#" role="button" data-rever-cookies>{e(tr("Rever escolha de cookies"))}</a>.' if ADSENSE_LIGADO else ""
    priv = f'<a href="{link(base, "privacidade.html")}"{hreflang_de("privacidade.html")}>{e(tr("Política de privacidade"))}</a>'
    return f"""<footer class="rodape">
  <div class="casca">
    <div>
      <h2>{e(marca_completa())}</h2>
      <p>{e(tr("Como uma obra que parecia impossível ficou de pé: o projeto, o cálculo, o canteiro, quem trabalhou e quem morreu. Aqui, número tem fonte."))}</p>
      <p><a href="{CANAL}" target="_blank" rel="noopener">{e(tr("Assista no YouTube"))}</a></p>
    </div>
    <div>
      <h2>{e(tr("Do mesmo criador"))}</h2>
      <ul>
        <li><a href="{SITE_IRMAO_VO}" target="_blank" rel="noopener">Vestígio Oculto</a> — {e(tr("arqueologia e mistério"))}</li>
        <li><a href="{SITE_IRMAO_XB}/" target="_blank" rel="noopener">Xadrez Bélico</a> — {e(tr("batalhas explicadas como partida"))}</li>
      </ul>
    </div>
    <div>
      <h2>{e(tr("Este site"))}</h2>
      <ul>
        <li><a href="{link(base, 'sobre.html')}"{hreflang_de('sobre.html')}>{e(tr("Sobre"))}</a> · <a href="{link(base, 'contato.html')}"{hreflang_de('contato.html')}>{e(tr("Contato"))}</a></li>
        <li>{e(tr("Exibe anúncios do Google AdSense."))} {priv}.{rever}</li>
        <li>{e(tr("Fotos de terceiros sob domínio público ou Creative Commons, com crédito em cada página."))}</li>
      </ul>
    </div>
    <div class="linha"><span>© {ano} {NOME} · {e(tr("textos autorais"))}</span><span>{e(tr("o impossível, medido."))}</span></div>
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
    return f'<span class="conf {cls}" title="{e(tr(tit))}">{e(tr(txt))}</span>'


def webp(jpg):
    """Cópia WebP ao lado do JPEG (o JPEG fica como reserva no <picture>).
    Só regera se faltar ou se o JPEG for mais novo."""
    destino = jpg.with_suffix(".webp")
    if not destino.exists() or destino.stat().st_mtime < jpg.stat().st_mtime:
        Image.open(jpg).convert("RGB").save(destino, "WEBP", quality=78, method=5)
    return destino.name


def webp_srcset(arquivo, base):
    """(srcset WebP, tem versão de 800?) da imagem `arquivo`."""
    nome = Path(arquivo).stem
    menor = IMG / f"{nome}-800.jpg"
    w = Image.open(IMG / arquivo).size[0]
    grande = f"{base}assets/img/{webp(IMG / arquivo)}"
    if menor.exists():
        return f"{base}assets/img/{webp(menor)} 800w, {grande} {w}w", True
    return grande, False


def img_tag(arquivo, alt, base, tamanhos="100vw", carregar="lazy", classe="", foco=None):
    """<picture> com WebP e reserva JPEG. `carregar="eager"` é a imagem do LCP
    (a capa): sai com fetchpriority alto; o resto é lazy."""
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
    prio = ' fetchpriority="high"' if carregar == "eager" else ""
    ws, tem800 = webp_srcset(arquivo, base)
    sz = f' sizes="{tamanhos}"' if tem800 else ""
    return (f'<picture><source type="image/webp" srcset="{ws}"{sz}>'
            f'<img src="{base}assets/img/{e(arquivo)}"{srcset} width="{w}" height="{h}" '
            f'alt="{e(alt)}" loading="{carregar}"{prio} decoding="async"{cl}{st}></picture>')


def preload_capa(arquivo, base, tamanhos="100vw"):
    """Avisa o navegador da capa (LCP) já no <head>, antes do HTML do corpo."""
    ws, tem800 = webp_srcset(arquivo, base)
    sz = f' imagesizes="{tamanhos}"' if tem800 else ""
    return f'<link rel="preload" as="image" type="image/webp" imagesrcset="{ws}"{sz} fetchpriority="high">'


def credito(im):
    lic = e(licenca_rotulo(im["licenca"]))
    if im.get("licenca_url"):
        lic = f'<a href="{e(im["licenca_url"])}" rel="license noopener">{lic}</a>'
    autor = e(im["autor"])
    if im.get("origem_url"):
        autor = f'<a href="{e(im["origem_url"])}" rel="noopener">{autor}</a>'
    return f"{autor} · {lic}"


# --- imagem de compartilhamento --------------------------------------------
def fonte(nome, tam):
    return ImageFont.truetype(str(SRC / "marca" / nome), tam)


def og_obra(o, nome_arq=None, rotulo=None, titulo=None):
    """Imagem de compartilhamento 1200x630. Também serve às páginas de tema
    (nome_arq, rotulo e titulo próprios, sobre a capa da primeira obra)."""
    destino = IMG / (nome_arq or f"og-{prefixo(L).replace('/', '-')}{o['slug']}.jpg")
    rotulo = rotulo or tr("OBRA {num}  ·  {pais}", num=o['num'], pais=o['lugar'].split(',')[-1].strip().upper())
    titulo = (titulo or o["obra"]).upper()
    capa = Image.open(IMG / o["imagens"][0]["arquivo"]).convert("RGB")
    im = ImageOps.fit(capa, (1200, 630), Image.LANCZOS, centering=(0.5, 0.45))
    # escurece de baixo para cima, para o título ler sobre qualquer foto
    sombra = Image.new("L", (1, 630))
    for y in range(630):
        sombra.putpixel((0, y), int(245 * min(1, max(0, (y - 150) / 330)) ** 1.1))
    sombra = sombra.resize((1200, 630))
    im = Image.composite(Image.new("RGB", im.size, (9, 27, 45)), im, sombra)
    d = ImageDraw.Draw(im)
    d.text((56, 372), rotulo, font=fonte("IBMPlexMono-Medium.ttf", 22), fill=(242, 183, 5))
    tam = 96
    while tam > 50 and d.textlength(titulo, font=fonte("BarlowCondensed-Bold.ttf", tam)) > 1088:
        tam -= 4
    d.text((52, 410), titulo, font=fonte("BarlowCondensed-Bold.ttf", tam), fill=(233, 238, 240))
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


# --- SEO -------------------------------------------------------------------
TITULO_MAX = 60
DESCRICAO_MIN, DESCRICAO_MAX = 120, 155
LOGO = f"{DOMINIO}/assets/marca/logo-512.png"
ORG = {"@type": "Organization", "name": NOME, "url": DOMINIO + "/",
       "logo": {"@type": "ImageObject", "url": LOGO, "width": 512, "height": 512}}

def seo_fixas():
    """(título, descrição) das páginas fixas no idioma da página atual."""
    return {
        "index.html": (tr("{nome}: como isto foi erguido", nome=NOME),
                       tr("Grandes construções que pareciam impossíveis: o projeto, o cálculo, o canteiro, quantos "
                          "trabalharam, quanto custou e quem morreu. Número com fonte.")),
        "sobre.html": (f"Sobre o {NOME}: como cada obra é apurada",
                       f"O que é o {NOME}, projeto independente sobre grandes obras: como cada página é apurada, "
                       "o selo de confiança, as imagens e quem faz."),
        "contato.html": (f"Contato · {NOME}",
                         f"Como falar com o {NOME} por e-mail: correções com fonte, créditos e retirada de imagens, "
                         "pedidos sobre seus dados (LGPD) e pautas."),
        "privacidade.html": (f"Política de privacidade · {NOME}",
                             f"Como o {NOME} trata dados, cookies e anúncios do Google AdSense, como rever a escolha de "
                             "cookies e seus direitos sob a LGPD."),
        **FIXAS_SEO.get(L, {}),
    }


# Sobre, contato e privacidade em outros idiomas (desde 03/10/2026): o texto
# mora aqui no build, como o português. Idioma que não está em FIXAS_IDIOMAS
# continua caindo nas páginas em português.
FIXAS_IDIOMAS = {"en", "es"}
FIXAS_SEO = {
    "es": {
        "sobre.html": (f"Acerca de {NOME}: cómo se investiga",
                       f"Qué es {NOME}, proyecto independiente sobre grandes obras: cómo se investiga, "
                       "el sello de confianza, las imágenes y quién lo hace."),
        "contato.html": (f"Contacto · {NOME}",
                         f"Cómo escribir a {NOME} por correo: correcciones con fuente, créditos y retiro de imágenes, "
                         "solicitudes sobre tus datos (LGPD) y temas."),
        "privacidade.html": (f"Política de privacidad · {NOME}",
                             f"Cómo {NOME} trata datos, cookies y anuncios de Google AdSense, cómo revisar tu elección "
                             "de cookies y tus derechos según la LGPD."),
    },
    "en": {
        "sobre.html": (f"About {NOME}: how each page is researched",
                       f"What {NOME} is, an independent project on great structures: how pages are researched, "
                       "the confidence seal, the images and who makes it."),
        "contato.html": (f"Contact · {NOME}",
                         f"How to reach {NOME} by e-mail: corrections with a source, image credits and removals, "
                         "requests about your data (LGPD) and story ideas."),
        "privacidade.html": (f"Privacy policy · {NOME}",
                             f"How {NOME} handles data, cookies and Google AdSense ads, how to review your cookie "
                             "choice, and your rights under Brazil's LGPD."),
    },
}


# Sobre, contato e privacidade: português e os idiomas de FIXAS_IDIOMAS; nos
# outros, os links para elas caem no português.


def titulo_seo(o):
    """Assunto primeiro, marca no fim, até 60 caracteres. O período sai se não
    couber, antes da marca. `titulo_seo` no JSON (opcional) substitui o padrão
    quando a obra é buscada de outro jeito ("como foi construído o…", o nome
    em inglês); passa pelas mesmas travas."""
    if o.get("titulo_seo"):
        t = o["titulo_seo"].strip()
        if len(t) > TITULO_MAX:
            falha(f"{o['slug']}: titulo_seo com {len(t)} caracteres (máx. {TITULO_MAX})")
        return t
    for t in (f"{o['obra']} ({o['periodo']}) · {NOME}", f"{o['obra']} · {NOME}"):
        if len(t) <= TITULO_MAX:
            return t
    falha(f"{o['slug']}: não há título de até {TITULO_MAX} caracteres")


def data_git(caminho, primeira=False):
    """Data (AAAA-MM-DD) do primeiro ou do último commit do arquivo; hoje se
    ele ainda tem mudança não publicada (ou não está no git)."""
    rel = str(Path(caminho).relative_to(RAIZ)).replace("\\", "/")
    try:
        if not primeira:
            sujo = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=RAIZ,
                                  capture_output=True, text=True).stdout.strip()
            if sujo:
                return dt.date.today().isoformat()
        args = ["git", "log", "--format=%cs", "--", rel]
        if primeira:
            args[2:2] = ["--diff-filter=A"]
        datas = subprocess.run(args, cwd=RAIZ, capture_output=True, text=True).stdout.split()
        if datas:
            return datas[-1] if primeira else datas[0]
    except OSError:
        pass
    return dt.date.today().isoformat()


def migalhas(*itens):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u}
                                for i, (n, u) in enumerate(itens, start=1)]}


def conferir_seo(paginas, lg="pt"):
    """Porteiro: título até 60 e único; descrição de 120 a 155 e única —
    dentro de cada idioma."""
    erros, vt, vd = [], {}, {}
    for nome, (t, d) in paginas.items():
        if len(t) > TITULO_MAX:
            erros.append(f"{nome}: título com {len(t)} caracteres ({t!r})")
        if not DESCRICAO_MIN <= len(d) <= DESCRICAO_MAX:
            erros.append(f"{nome}: descrição com {len(d)} caracteres ({DESCRICAO_MIN}–{DESCRICAO_MAX})")
        if t in vt:
            erros.append(f"{nome}: título igual ao de {vt[t]}")
        if d in vd:
            erros.append(f"{nome}: descrição igual à de {vd[d]}")
        vt[t], vd[d] = nome, nome
    if erros:
        falha(f"SEO [{lg}]\n  " + "\n  ".join(erros))


def logo_png():
    """Logo quadrado (PNG) que o JSON-LD do publisher pede: o avatar do canal."""
    destino = RAIZ / "assets" / "marca" / "logo-512.png"
    destino.parent.mkdir(exist_ok=True)
    (Image.open(SRC / "marca" / "avatar-800x800.png").convert("RGB")
     .resize((512, 512), Image.LANCZOS).save(destino, "PNG", optimize=True))


# --- home ------------------------------------------------------------------
def regiao_rotulo(o):
    return tr("Brasil") if o["regiao"] == "brasil" else tr("Mundo")


def card(o, base, texto=None):
    capa = o["imagens"][0]
    ch = f"obras/{o['slug']}.html"
    return f"""<li class="obra-card revela" data-regiao="{o['regiao']}">
  <div class="foto">{img_tag(capa['arquivo'], capa['alt'], base, '(max-width:720px) 100vw, 400px', foco=capa.get('foco'))}
    <span class="num">{e(o['num'])}</span>
    <span class="selo selo-estreia" data-estreia="{o['estreia']}" data-no-ar="{e(tr('No ar'))}">{e(tr('Estreia'))} {e(data_br(o['estreia']))}</span>
  </div>
  <div class="corpo">
    <h3><a href="{link(base, ch)}"{hreflang_de(ch)}>{e(o['obra'])}</a></h3>
    <div class="onde">{e(o['lugar'])} · {e(o['periodo'])}</div>
    <p class="imp">{para(texto or o['impossivel'])}</p>
    <div class="pe"><span>{e(regiao_rotulo(o))}</span><span>{e(tr('Ler a obra →'))}</span></div>
  </div>
</li>"""


def card_apuracao(a):
    return f"""<li class="obra-card apuracao revela" data-regiao="{a['regiao']}">
  <div class="foto"><span class="num">{e(a['num'])}</span>
    <span class="selo">{e(tr('Em apuração'))}</span>
  </div>
  <div class="corpo">
    <h3>{e(a['obra'])}</h3>
    <div class="onde">{e(a['lugar'])}</div>
    <p class="imp">{para(a['impossivel'])}</p>
    <div class="pe"><span>{e(regiao_rotulo(a))}</span><span>{e(tr('Estreia'))} {e(data_br(a['estreia']))}</span></div>
  </div>
</li>"""


def site_jsonld(descricao):
    """WebSite + Organization: a mesma entidade em todos os idiomas."""
    subs = [I18N[lg]["_idioma"]["marca_sub"] for lg in ATIVOS if I18N[lg]["_idioma"]["marca_sub"]]
    site = {"@type": "WebSite", "@id": DOMINIO + "/#site", "name": NOME, "url": DOMINIO + "/",
            "inLanguage": cfg("hreflang"), "description": descricao, "publisher": {"@id": DOMINIO + "/#org"}}
    if subs:
        site["alternateName"] = subs
    return {"@context": "https://schema.org", "@graph": [
        site, dict(ORG, **{"@id": DOMINIO + "/#org", "sameAs": [CANAL] if CANAL else []})]}


def home(obras, og, total=None):
    """`obras`: as que existem no idioma da página; `total`: quantas há em
    português (nos outros idiomas, a home avisa que o resto está em português)."""
    base = "../" if L != BASE_IDIOMA else ""
    titulo, desc = seo_fixas()["index.html"]
    nomes = {'2+': tr('Confirmado'), '1': tr('Fonte única'), 'DIV': tr('Divergência'), 'sem': tr('Sem registro')}
    graus = "".join(f"<li>{conf_selo(k)}<p><strong>{e(nomes[k])}</strong>{e(tr(v[2]))}</p></li>" for k, v in CONF.items())
    apur = EM_APURACAO if L == BASE_IDIOMA else []
    cards = "\n".join(card(o, base) for o in obras) + "\n" + "\n".join(card_apuracao(a) for a in apur)
    resto = ""
    if total and total > len(obras):
        resto = (f'<p class="em-portugues"><a href="{base}index.html#obras" hreflang="{CONFIG_PT["hreflang"]}">'
                 f'{e(tr("As outras {n} obras ainda estão só em português →", n=total - len(obras)))}</a></p>')
    return (cabeca(titulo, desc, url_de(L, "index.html"), f"{DOMINIO}/assets/img/{og}", base, site_jsonld(desc))
            + topo(base) + f"""<main id="conteudo">
<section class="abre">
  <div class="casca">
    <div>
      <div class="cota"><span>{e(tr('o impossível, medido'))}</span></div>
      <h1>{tr('Como isto foi <em>erguido?</em>')}</h1>
      <p class="lead">{e(tr('Toda semana, a história de uma grande construção que parecia impossível, e de quem resolveu o problema. O projeto, o cálculo, o canteiro. Quantos operários, quanto tempo, quanto custou, quem se feriu e quem morreu.'))}</p>
      <div class="botoes">
        <a class="botao cheio" href="#obras">{e(tr('Ver as obras'))}</a>
        <a class="botao" href="{CANAL}" target="_blank" rel="noopener">{e(tr('Canal no YouTube'))}</a>
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
        <span class="rotulo">{e(tr('Prancheta'))} <b>{len(obras) + len(apur):02d}</b> {e(tr('obras'))}</span>
        <h2>{e(tr('As obras'))}</h2>
        <p>{e(tr('Obras do Brasil e do resto do mundo, uma por semana. Cada página tem a ficha técnica completa e a história de como a obra ficou de pé.'))}</p>
      </div>
      <div class="filtros" role="group" aria-label="{e(tr('Filtrar obras'))}">
        <button type="button" data-f="todas" aria-pressed="true">{e(tr('Todas'))}</button>
        <button type="button" data-f="brasil" aria-pressed="false">{e(tr('Brasil'))}</button>
        <button type="button" data-f="mundo" aria-pressed="false">{e(tr('Mundo'))}</button>
      </div>
    </header>
    <ul class="obras">
{cards}
    </ul>{resto}
  </div>
</section>

{secao_temas(base)}
<section class="secao metodo" id="metodo">
  <div class="casca">
    <div>
      <span class="rotulo">{e(tr('Método'))}</span>
      <h2>{tr('Aqui, número <span class="destaque">tem fonte</span>')}</h2>
      <p>{e(tr('Toda obra grande vem com lenda: o operário enterrado no concreto, a estrutura “construída em X dias”, o número de mortos que ninguém conferiu. Cada dado deste site carrega um selo dizendo quanto se pode confiar nele.'))}</p>
      <p>{e(tr('Quando as fontes discordam, mostramos as versões e não escolhemos. Quando ninguém registrou, dizemos isso em vez de inventar.'))}</p>
    </div>
    <ul class="graus">{graus}</ul>
  </div>
</section>
</main>
""" + rodape(base) + consentimento(base) + SCRIPT)


def secao_temas(base, atual=None, titulo="Temas", rotulo="Por assunto"):
    """Lista de temas: na home (seção #temas) e no pé de cada página de tema."""
    ts = [t for t in TEMAS if t["slug"] != atual]
    if not ts:
        return ""
    itens = "".join(f'<li><a href="{link(base, "temas/" + t["slug"] + ".html")}"><span class="rotulo">{len(t[CHAVE_MEMBROS]):02d} {e(tr("obras"))}</span>'
                    f'<strong>{e(t["nome"])}</strong></a></li>' for t in ts)
    sid = ' id="temas"' if atual is None else ""
    return f"""<section class="secao temas"{sid}>
  <div class="casca">
    <header><div><span class="rotulo">{e(tr(rotulo))}</span><h2>{e(tr(titulo))}</h2>
      <p>{e(tr('As obras agrupadas pelo problema que resolveram: pontes, arranha-céus, túneis, estádios, água.'))}</p></div></header>
    <ul class="temas-lista">{itens}</ul>
  </div>
</section>
"""


def pagina_tema(t, obras, og):
    base = "../../" if L != BASE_IDIOMA else "../"
    ch = f"temas/{t['slug']}.html"
    url = url_de(L, ch)
    por_slug = {o["slug"]: o for o in obras}
    membros = sorted((por_slug[s] for s in t[CHAVE_MEMBROS]), key=lambda o: o["num"])
    cards = "\n".join(card(o, base, o["resumo"]) for o in membros)
    inicio = url_de(L, "index.html")
    jsonld = [{
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": t["nome"], "headline": t["titulo"], "description": t["resumo"], "url": url, "inLanguage": cfg("hreflang"),
        "isPartOf": {"@type": "WebSite", "name": NOME, "url": DOMINIO + "/"},
        "image": {"@type": "ImageObject", "url": f"{DOMINIO}/assets/img/{og}", "width": 1200, "height": 630},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(membros), "itemListElement": [
            {"@type": "ListItem", "position": i, "url": url_de(L if f"obras/{o['slug']}.html" in EXISTE[L] else BASE_IDIOMA, f"obras/{o['slug']}.html"), "name": o["obra"]}
            for i, o in enumerate(membros, start=1)]},
    }, migalhas((NOME, inicio), (tr("Temas"), inicio + "#temas"), (t["nome"], url))]
    intro = "".join(f"<p>{para(p)}</p>" for p in t["intro"])
    return (cabeca(titulo_tema(t), t["resumo"], url, f"{DOMINIO}/assets/img/{og}", base, jsonld)
            + topo(base, "temas") + f"""<main id="conteudo">
<section class="tema-abre">
  <div class="casca">
    <nav class="migalhas" aria-label="{e(tr('Você está em'))}"><a href="{link(base, 'index.html')}">{e(tr('Início'))}</a> / <a href="{link(base, 'index.html', '#temas')}">{e(tr('Temas'))}</a> / <span>{e(t['nome'])}</span></nav>
    <span class="rotulo">{e(tr('Tema'))} · <b>{len(membros):02d}</b> {e(tr('obras'))}</span>
    <h1>{e(t['nome'])}</h1>
    <div class="intro">{intro}</div>
  </div>
</section>
<div class="faixa" role="presentation"></div>
<section class="secao" id="obras">
  <div class="casca">
    <header><div><span class="rotulo">{e(tr('Prancheta'))}</span><h2>{e(tr('As obras deste tema'))}</h2></div></header>
    <ul class="obras">
{cards}
    </ul>
  </div>
</section>
{secao_temas(base, t['slug'], 'Outros temas', 'Mais')}
</main>
""" + rodape(base) + consentimento(base) + SCRIPT)


# --- página de obra ---------------------------------------------------------
def figura(im, n, base):
    leg = f"{im['legenda']} — {im['autor']}, {licenca_rotulo(im['licenca'])}"
    return f"""<figure class="fig revela">
  <button type="button" class="cantos" data-grande="{base}assets/img/{e(im['arquivo'])}" data-legenda="{e(leg)}" aria-label="{e(tr('Ampliar imagem: {alt}', alt=im['alt']))}">{img_tag(im['arquivo'], im['alt'], base, '(max-width:980px) 100vw, 720px')}</button>
  <figcaption><span class="fn">FIG. {n:02d}</span><span>{para(im['legenda'])}</span><small>{credito(im)}</small></figcaption>
</figure>"""


def pagina_obra(o, obras, og):
    base = "../../" if L != BASE_IDIOMA else "../"
    url = url_de(L, f"obras/{o['slug']}.html")
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
    legenda_conf = "".join(f"<span>{conf_selo(k)} {e(tr(v[2]))}</span>" for k, v in CONF.items())
    mitos = "".join(f'<li><div><span class="rotulo">{e(tr("O que circula"))}</span><p>{para(m["circula"])}</p></div><div><span class="rotulo"><b>{e(tr("O que o registro diz"))}</b></span><p>{para(m["registro"])}</p></div></li>' for m in o["mitos"])
    fontes = "".join(
        f'<li>{para(f["texto"])}' + (f' — <a href="{e(f["url"])}" rel="noopener">{e(re.sub(r"^https?://(www\.)?", "", f["url"]).split("/")[0])}</a>' if f.get("url") else "") + "</li>"
        for f in o["fontes"])
    creditos = "".join(f'<li>Fig. {i+1:02d} — {e(im["legenda"].rstrip("."))}: {credito(im)}</li>' for i, im in enumerate(o["imagens"]))

    indice = ([("ficha", tr("Ficha da obra"))] + [(sid, t) for sid, t, _ in secoes] + [("mitos", tr("Mitos e registro"))]
              + ([("perguntas", tr("Perguntas frequentes"))] if o.get("perguntas") else []) + [("fontes", tr("Fontes"))])
    indice_html = "".join(f'<li><a href="#{a}">{e(t)}</a></li>' for a, t in indice)

    i_atual = [x["slug"] for x in obras].index(o["slug"])
    ant = obras[i_atual - 1] if i_atual > 0 else None
    prox = next((x for x in obras if x["slug"] == o["proximo"]), None) if o["proximo"] else None
    nav = ""
    ob = lambda x: f"obras/{x['slug']}.html"
    if ant or prox:
        nav = f'<nav class="seguinte" aria-label="{e(tr("Outras obras"))}">'
        nav += (f'<a href="{link(base, ob(ant))}"{hreflang_de(ob(ant))}><span class="rotulo">← {e(tr("Obra"))} {ant["num"]}</span><strong>{e(ant["obra"])}</strong></a>' if ant else "<span></span>")
        nav += (f'<a href="{link(base, ob(prox))}"{hreflang_de(ob(prox))}><span class="rotulo">{e(tr("Obra"))} {prox["num"]} →</span><strong>{e(prox["obra"])}</strong></a>' if prox
                else f'<a href="{link(base, "index.html", "#obras")}"><span class="rotulo">{e(tr("Todas as obras →"))}</span><strong>{e(tr("Prancheta"))}</strong></a>')
        nav += "</nav>"

    # "Próximo episódio": o papel da chamada no fim do vídeo. Se o próximo
    # já tem página, leva a ela; se só está anunciado (EM_APURACAO), mostra
    # sem link, com a data de estreia.
    seguinte = ""
    anunciado = next((a for a in EM_APURACAO if int(a["num"]) == int(o["num"]) + 1), None) if L == BASE_IDIOMA else None
    if prox:
        pc = prox["imagens"][0]
        seguinte = f"""<a class="proximo-ep" href="{link(base, ob(prox))}"{hreflang_de(ob(prox))}>
      <div class="foto">{img_tag(pc['arquivo'], pc['alt'], base, '(max-width:640px) 100vw, 260px', foco=pc.get('foco'))}</div>
      <div class="txt">
        <span class="rotulo">{e(tr('Próximo episódio'))} · {e(tr('Obra'))} <b>{e(prox['num'])}</b> · <span class="selo-estreia" data-estreia="{prox['estreia']}" data-no-ar="{e(tr('no ar'))}">{e(tr('estreia'))} {e(data_br(prox['estreia']))}</span></span>
        <h3>{e(prox['obra'])}</h3>
        <span class="onde">{e(prox['lugar'])} · {e(prox['periodo'])}</span>
        <p>{para(prox['impossivel'])}</p>
        <span class="ir">{e(tr('Ler a obra →'))}</span>
      </div>
    </a>"""
    elif anunciado:
        seguinte = f"""<div class="proximo-ep sem-pagina">
      <div class="txt">
        <span class="rotulo">{e(tr('Próximo episódio'))} · {e(tr('Obra'))} <b>{e(anunciado['num'])}</b> · {e(tr('estreia'))} {e(data_br(anunciado['estreia']))}</span>
        <h3>{e(anunciado['obra'])}</h3>
        <span class="onde">{e(anunciado['lugar'])}</span>
        <p>{para(anunciado['impossivel'])}</p>
        <span class="ir">{e(tr('Em apuração'))}</span>
      </div>
    </div>"""

    arq = o.get("_arquivo") or SRC / "obras" / f"{o['num']}-{o['slug']}.json"
    inicio = url_de(L, "index.html")
    jsonld = [{
        "@context": "https://schema.org", "@type": "Article",
        "headline": tr("{obra} ({periodo}): como a obra ficou de pé", obra=o['obra'], periodo=o['periodo']),
        "description": o["resumo"], "inLanguage": cfg("hreflang"), "url": url,
        "image": {"@type": "ImageObject", "url": f"{DOMINIO}/assets/img/{og}", "width": 1200, "height": 630},
        "datePublished": data_git(arq, primeira=True), "dateModified": data_git(arq),
        "author": {"@type": "Organization", "name": NOME, "url": DOMINIO + "/"}, "publisher": ORG,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "about": {"@type": "LandmarksOrHistoricalBuildings", "name": o["obra"], "address": o["lugar"]},
    }, migalhas((NOME, inicio), (tr("Obras"), inicio + "#obras"), (o["obra"], url))]
    return (cabeca(titulo_seo(o), o["resumo"], url, f"{DOMINIO}/assets/img/{og}", base, jsonld, "article",
                   extra=preload_capa(capa["arquivo"], base))
            + '<div class="progresso" aria-hidden="true"></div>' + topo(base, "obras") + f"""<main id="conteudo">
<header class="capa">
  {img_tag(capa['arquivo'], capa['alt'], base, '100vw', 'eager', foco=capa.get('foco'))}
  <span class="credito-capa">{e(capa['legenda'])} — {credito(capa)}</span>
  <div class="casca">
    <span class="rotulo">{e(tr('Obra'))} <b>{e(o['num'])}</b> · {e(regiao_rotulo(o))}</span>
    <h1>{e(o['obra'])}</h1>
    <div class="sub">{e(o['lugar'])} · {e(o['periodo'])}</div>
    <p class="imp">{para(o['impossivel'])}</p>
  </div>
</header>
<section class="cotas" aria-label="{e(tr('A obra em números'))}"><ul>{numeros}</ul></section>
<div class="casca obra-layout">
  <article class="texto">
    <div class="abertura">{''.join(f'<p>{para(p)}</p>' for p in o['abertura'])}</div>

    <h2 id="ficha"><span class="n">{e(tr('FICHA'))}</span>{e(tr('Ficha da obra'))}</h2>
    <table class="ficha">
      <tbody>{ficha}</tbody>
    </table>
    <div class="legenda-conf">{legenda_conf}</div>

    {''.join(h for _, _, h in secoes)}
    {sobra}

    <h2 id="mitos"><span class="n">{e(tr('MITOS'))}</span>{e(tr('O que circula e o que o registro diz'))}</h2>
    <ul class="mitos">{mitos}</ul>

    {perguntas_html(o)}

    <section class="video">
      <div>
        <span class="rotulo">{e(tr('Episódio'))} {e(o['num'])} · <span class="selo-estreia" data-estreia="{o['estreia']}" data-no-ar="{e(tr('no ar'))}">{e(tr('estreia'))} {e(data_br(o['estreia'], True))}</span></span>
        <h3>{e(o['titulo_video']) if o['titulo_video'] else e(tr('Episódio em produção'))}</h3>
        <p>{e(tr(BORDAO))}</p>
      </div>
      <a class="botao cheio" href="{CANAL}" target="_blank" rel="noopener">{e(tr('Ver no YouTube'))}</a>
    </section>

    {seguinte}

    {leia_tambem(o, obras)}

    <h2 id="fontes"><span class="n">{e(tr('FONTES'))}</span>{e(tr('Fontes'))}</h2>
    <ol class="fontes">{fontes}</ol>
    <h3 style="margin-top:2rem">{e(tr('Imagens'))}</h3>
    <ul class="creditos">{creditos}</ul>
  </article>
  <aside class="indice" aria-label="{e(tr('Nesta página'))}">
    <div class="lado-card">
      <span class="rotulo">{e(tr('Ficha rápida'))}</span>
      <dl>
        <div><dt>{e(tr('Onde'))}</dt><dd>{e(o['lugar'])}</dd></div>
        <div><dt>{e(tr('Obra'))}</dt><dd>{e(o['periodo'])}</dd></div>
        <div><dt>{e(tr('Episódio'))}</dt><dd>{e(o['num'])} · {e(data_br(o['estreia']))}</dd></div>
      </dl>
    </div>
    <span class="rotulo">{e(tr('Nesta página'))}</span>
    <ol>{indice_html}</ol>
  </aside>
</div>
{nav}
</main>
<div class="lupa" role="dialog" aria-modal="true" aria-label="{e(tr('Imagem ampliada'))}"><button type="button">{e(tr('Fechar'))}</button><img alt=""><p></p></div>
""" + rodape(base) + consentimento(base) + SCRIPT)


def pagina_404():
    base = "/"  # o 404 é servido em qualquer caminho: endereços absolutos
    return (cabeca(f"Página não encontrada · {NOME}", "Esta página não existe.", DOMINIO + "/404.html",
                   f"{DOMINIO}/assets/img/og-home.jpg", base, {"@context": "https://schema.org", "@type": "WebPage", "name": "404"},
                   indexar=False)
            + topo(base) + f"""<main id="conteudo" class="simples"><div class="casca">
  <div class="cota"><span>erro 404</span></div>
  <h1>Esta viga <span class="destaque">não fecha</span></h1>
  <p>A página que você procurou não existe, ou mudou de endereço. Como o triângulo da nossa marca: parece que leva a algum lugar, mas não leva.</p>
  <div class="botoes"><a class="botao cheio" href="/index.html#obras">Ver as obras</a></div>
</div></main>
""" + rodape(base) + consentimento(base) + SCRIPT)


# --- main ---------------------------------------------------------------------

PRIVACIDADE = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Documento · atualizado em 03 de outubro de 2026</span>
  <h1>Política de privacidade</h1>
  <p class="lead">Um site que cobra fonte dos outros deve ser claro sobre si mesmo. Aqui está o que o {{NOME}} coleta, o que não coleta, quem mais está envolvido e o que você pode exigir.</p>

  <div class="resumo"><strong>O resumo.</strong> Não pedimos cadastro, não temos formulário e não mantemos lista de e-mails: se você nos escrever, o seu e-mail fica só na nossa caixa de entrada, para a resposta. O que existe são cookies de publicidade do Google, usados para exibir anúncios, que carregam desde a primeira página. Se você recusar na faixa, o script de anúncios é retirado e deixa de carregar a partir da página seguinte; o que ele já tiver lido ou gravado na página em que você estava não é desfeito. A escolha pode ser revista a qualquer momento pelo link “Rever escolha de cookies”, no rodapé, e a publicidade personalizada pode ser desligada nas configurações do Google.</div>

  <h2>1. Quem é o responsável</h2>
  <p>O <strong>{{NOME}}</strong> é um projeto editorial independente, publicado em {{DOMINIO_NU}}, {{CANAL_FRASE}}. Para qualquer assunto desta política — inclusive pedidos de exclusão ou de informação —, o contato é o e-mail informado na página de <a href="contato.html">contato</a>.</p>

  <h2>2. O que coletamos, e o que não</h2>
  <p>Não há cadastro, login, comentários, newsletter nem formulário de contato. Nenhuma página pede seu nome, e-mail, telefone ou documento. Não montamos perfil de leitor e não vendemos nem compartilhamos lista de ninguém, porque lista não existe.</p>
  <p>O que existe é o que qualquer site recebe por ser acessado: o servidor que hospeda estas páginas registra o endereço IP, a data e a hora, a página pedida e o navegador usado. Esses registros servem para segurança e diagnóstico de falha, e não são usados para identificar pessoas.</p>

  <h2>3. Cookies e publicidade</h2>
  <p>Este site exibe anúncios por meio do <strong>Google AdSense</strong>. Para isso, o Google e seus parceiros usam cookies — pequenos arquivos gravados no seu navegador — para selecionar e medir os anúncios.</p>
  <ul>
    <li>O Google, como fornecedor terceirizado, utiliza cookies para exibir anúncios neste site.</li>
    <li>Os cookies de publicidade do Google permitem que ele e seus parceiros veiculem anúncios com base nas visitas do usuário a este e a outros sites da internet.</li>
    <li>Parceiros e redes de terceiros também podem usar cookies, identificadores de dispositivo ou tecnologia semelhante para medir e personalizar os anúncios.</li>
    <li>Nenhum desses dados passa por nós: o site não recebe, não armazena e não tem acesso ao que essas redes coletam.</li>
  </ul>
  <p>Você pode desativar a publicidade personalizada — em todos os sites da rede do Google, não só neste — em <a href="https://adssettings.google.com" rel="noopener">adssettings.google.com</a>. As regras completas do Google estão em <a href="https://policies.google.com/technologies/ads?hl=pt-BR" rel="noopener">policies.google.com/technologies/ads</a>, e para sair da publicidade comportamental de várias redes de uma vez existe o <a href="https://www.aboutads.info/choices/" rel="noopener">aboutads.info/choices</a>.</p>
  <p>Todo navegador também permite bloquear ou apagar cookies. Fazer isso não impede a leitura de nada: o conteúdo deste site não depende de cookie para funcionar.</p>

  <h2>4. O que guardamos no seu navegador</h2>
  <p>Uma única coisa, e ela não sai do seu aparelho: quando você responde à faixa de cookies, a escolha fica registrada no armazenamento local do navegador, sob a chave <code>{{CHAVE}}</code>. Serve só para não perguntar de novo a cada página. Não é cookie, não é enviada a servidor nenhum e some quando você limpa os dados do site ou clica em “Rever escolha de cookies”, no rodapé de qualquer página: a escolha salva é apagada e a faixa volta a aparecer.</p>

  <h2>5. Conteúdo de terceiros</h2>
  <p>Um único serviço externo participa da exibição destas páginas: o <strong>Google AdSense</strong>, que entrega os anúncios. O script de anúncios carrega desde a primeira página, antes de qualquer resposta. Se você recusar na faixa, ele é retirado e deixa de ser carregado a partir da página seguinte; o que ele já tiver exibido, lido ou gravado na página em que você estava não é desfeito, e cookies que o Google já tenha gravado ficam no navegador até você apagá-los.</p>
  <p>O <strong>YouTube</strong> só entra em cena se você clicar num link para o canal: nenhum vídeo é incorporado nestas páginas. Todo o resto — as imagens das fichas de obra e as fontes tipográficas — vem deste mesmo domínio.</p>

  <h2>6. Seus direitos sob a LGPD</h2>
  <p>A Lei nº 13.709/2018 garante a você o direito de confirmar se há tratamento de dados seus, de acessá-los, de corrigi-los, de pedir anonimização ou eliminação, de solicitar portabilidade, de saber com quem foram compartilhados e de revogar consentimento a qualquer momento.</p>
  <p>Aqui o exercício desses direitos é curto, porque a base de dados que poderíamos entregar é praticamente vazia. Ainda assim, qualquer pedido feito pela página de <a href="contato.html">contato</a> será respondido. Para revogar a escolha feita na faixa de cookies, use o link “Rever escolha de cookies”, no rodapé de qualquer página. Para os dados que o Google coleta através dos anúncios, o pedido precisa ser feito ao próprio Google — nós exibimos o espaço, mas é ele quem trata esses dados.</p>

  <h2>7. Crianças e adolescentes</h2>
  <p>O conteúdo deste site não se dirige a menores de 13 anos, e não coletamos conscientemente dados de crianças. Se você é responsável por uma criança e acredita que algum dado dela chegou até aqui, entre em contato para que seja eliminado.</p>

  <h2>8. Mudanças nesta política</h2>
  <p>Se algo mudar — uma nova rede de anúncios, uma ferramenta de medição, uma área de comentários —, esta página muda junto, e a data no topo é atualizada.</p>

  <div class="botoes" style="margin-top:2.5rem"><a class="botao cheio" href="index.html#obras">Ver as obras</a></div>
</div></main>
"""


PRIVACY_EN = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Document · updated October 3, 2026</span>
  <h1>Privacy policy</h1>
  <p class="lead">A site that demands sources from others should be clear about itself. Here is what {{NOME}} collects, what it does not collect, who else is involved and what you can demand.</p>

  <div class="resumo"><strong>In short.</strong> We do not ask you to sign up, we have no forms and we keep no e-mail list: if you write to us, your e-mail stays only in our inbox, for the reply. What does exist are Google advertising cookies, used to show ads, which load from the first page on. If you decline in the banner, the ad script is removed and stops loading from the next page on; whatever it has already read or stored on the page you were on is not undone. You can review your choice at any time through the “Review cookie choice” link in the footer, and personalized advertising can be turned off in Google’s settings.</div>

  <h2>1. Who is responsible</h2>
  <p><strong>{{NOME}}</strong> is an independent editorial project, published at {{DOMINIO_NU}}, {{CANAL_FRASE}}. For any matter concerning this policy — including requests for deletion or for information — the contact is the e-mail address given on the <a href="contato.html">contact</a> page.</p>

  <h2>2. What we collect, and what we do not</h2>
  <p>There is no sign-up, login, comments, newsletter or contact form. No page asks for your name, e-mail, phone number or ID. We do not build reader profiles and we do not sell or share anyone’s list, because no list exists.</p>
  <p>What exists is what any site receives simply by being visited: the server that hosts these pages logs the IP address, the date and time, the page requested and the browser used. These logs serve security and fault diagnosis, and are not used to identify people.</p>

  <h2>3. Cookies and advertising</h2>
  <p>This site shows ads through <strong>Google AdSense</strong>. To do so, Google and its partners use cookies — small files stored in your browser — to select and measure the ads.</p>
  <ul>
    <li>Google, as a third-party vendor, uses cookies to serve ads on this site.</li>
    <li>Google’s advertising cookies enable it and its partners to serve ads based on the user’s visits to this and other sites on the internet.</li>
    <li>Third-party partners and networks may also use cookies, device identifiers or similar technology to measure and personalize ads.</li>
    <li>None of this data passes through us: the site does not receive, store or have access to what these networks collect.</li>
  </ul>
  <p>You can turn off personalized advertising — across all sites in Google’s network, not just this one — at <a href="https://adssettings.google.com" rel="noopener">adssettings.google.com</a>. Google’s full rules are at <a href="https://policies.google.com/technologies/ads?hl=en" rel="noopener">policies.google.com/technologies/ads</a>, and to opt out of behavioral advertising from several networks at once there is <a href="https://www.aboutads.info/choices/" rel="noopener">aboutads.info/choices</a>.</p>
  <p>Every browser also lets you block or delete cookies. Doing so does not prevent you from reading anything: the content of this site does not depend on cookies to work.</p>

  <h2>4. What we store in your browser</h2>
  <p>A single thing, and it never leaves your device: when you answer the cookie banner, your choice is recorded in the browser’s local storage, under the key <code>{{CHAVE}}</code>. It serves only so that you are not asked again on every page. It is not a cookie, it is not sent to any server, and it disappears when you clear the site’s data or click “Review cookie choice” in the footer of any page: the saved choice is erased and the banner appears again.</p>

  <h2>5. Third-party content</h2>
  <p>A single external service takes part in displaying these pages: <strong>Google AdSense</strong>, which delivers the ads. The ad script loads from the first page on, before any answer. If you decline in the banner, it is removed and stops being loaded from the next page on; whatever it has already displayed, read or stored on the page you were on is not undone, and cookies Google has already stored remain in the browser until you delete them.</p>
  <p><strong>YouTube</strong> only comes in if you click a link to the channel: no video is embedded in these pages. Everything else — the images on the structure pages and the typefaces — comes from this same domain.</p>

  <h2>6. Your rights under the LGPD</h2>
  <p>Brazil’s General Data Protection Law (LGPD, Law No. 13,709/2018) guarantees you the right to confirm whether any data of yours is being processed, to access it, to correct it, to request its anonymization or deletion, to request portability, to know with whom it was shared and to withdraw consent at any time.</p>
  <p>Here, exercising these rights is quick, because the database we could hand over is practically empty. Even so, any request made through the <a href="contato.html">contact</a> page will be answered. To withdraw the choice made in the cookie banner, use the “Review cookie choice” link in the footer of any page. For the data Google collects through the ads, the request must be made to Google itself — we display the space, but Google is the one that processes that data.</p>

  <h2>7. Children and teenagers</h2>
  <p>The content of this site is not directed at children under 13, and we do not knowingly collect data from children. If you are responsible for a child and believe any of their data has reached us, get in touch so that it can be deleted.</p>

  <h2>8. Changes to this policy</h2>
  <p>If anything changes — a new ad network, a measurement tool, a comments section — this page changes with it, and the date at the top is updated.</p>

  <div class="botoes" style="margin-top:2.5rem"><a class="botao cheio" href="index.html#obras">See the structures</a></div>
</div></main>
"""

ABOUT_EN = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">About</span>
  <h1>About {{NOME}}</h1>

  <h2>1. What it is</h2>
  <p><strong>Arquitetura do Impossível</strong> (Impossible Architecture) is an independent editorial project, made in Brazil, about great structures: how a work that seemed impossible came to stand. Each page of this site accompanies an episode of the YouTube channel, {{CANAL}}, in Portuguese, and is published before the premiere, while the episode is still to come. It goes beyond the video: it has the full fact sheet, the sources, the credited images and the disagreements that do not fit in a video.</p>
  <p>The question is always the same: <em>what made this structure impossible, and who solved it</em> — with what math, what material, what improvisation. The protagonist is the engineering problem; people come in as those who faced it. Structures from Brazil and the rest of the world, one a week.</p>

  <h2>2. How a page is made</h2>
  <ul>
    <li><strong>Every fact sheet covers what is usually missing:</strong> how many workers, how long, how much it cost, who was injured and who died — every line with a source.</li>
    <li><strong>Every number carries a confidence seal:</strong> confirmed in two or more sources, single source (the text says which), disagreement (we show the versions and do not pick one) or no record (we say nobody recorded it, instead of making it up).</li>
    <li><strong>The debunked myth is part of the story:</strong> the worker buried in the concrete, the structure "built in X days", the death toll nobody checked.</li>
    <li><strong>Today’s value only with a stated method.</strong> Converting old money without saying how is making numbers up.</li>
    <li><strong>Entirely original writing.</strong> The sources are listed at the end of each page.</li>
  </ul>

  <h2>3. Images</h2>
  <p>Only real photographs, plans and documents are used, from collections in the public domain or under a Creative Commons license that allows commercial use, with author and license credited on every page. AI-generated images are not used on this site.</p>

  <h2>4. Corrections</h2>
  <p>Got a date, a name or a number wrong? Write through the <a href="contato.html">contact</a> page, preferably with the source. A confirmed error is corrected here, and the correction also applies to whatever comes next on the channel.</p>

  <h2>5. Who makes it</h2>
  <p>{{NOME}} is written, researched and maintained independently, with no ties to any university, company or government body. It comes from the same creator as two other projects with the same care for sources: <a href="{{VO}}" rel="noopener">Vestígio Oculto</a>, on archaeology and mystery, and <a href="{{XB}}" rel="noopener">Xadrez Bélico</a>, on battles explained as a chess game (both in Portuguese).</p>
  <p>The site is supported by Google AdSense ads, described in the <a href="privacidade.html">privacy policy</a>. No ad interferes with what is written.</p>
</div></main>
"""

CONTACT_EN = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Contact</span>
  <h1>Contact {{NOME}}</h1>
  <p class="lead">A correction, an image credit, a request about your data or anything else: there is just one way in.</p>
  <div class="resumo"><strong>E-mail:</strong> <a href="mailto:allangipa@gmail.com">allangipa@gmail.com</a></div>

  <h2>What to write about</h2>
  <ul>
    <li><strong>Corrections.</strong> A wrong date, name or number. Send the source along: that is what makes a quick fix possible.</li>
    <li><strong>Images and credits.</strong> If you are the author of an image used here and the credit is incomplete, or you want it removed, write to us.</li>
    <li><strong>Your data.</strong> Requests under the LGPD, as set out in the <a href="privacidade.html">privacy policy</a>.</li>
    <li><strong>Story ideas, press and partnerships.</strong> Topic suggestions are welcome too.</li>
  </ul>

  <h2>How we reply</h2>
  <p>There is no form and no sign-up: the conversation happens by e-mail, and your address is not used for anything other than replying. A confirmed correction goes into the page.</p>
</div></main>
"""

# Espanhol (desde 03/10/2026): a privacidade diz exatamente o que a portuguesa
# diz, parágrafo a parágrafo. Mudou uma, muda as outras.
PRIVACIDAD_ES = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Documento · actualizado el 3 de octubre de 2026</span>
  <h1>Política de privacidad</h1>
  <p class="lead">Un sitio que les exige fuentes a los demás debe ser claro sobre sí mismo. Aquí está lo que {{NOME}} recopila, lo que no recopila, quién más participa y lo que puedes exigir.</p>

  <div class="resumo"><strong>En resumen.</strong> No pedimos registro, no tenemos formularios y no mantenemos lista de correos: si nos escribes, tu correo queda solo en nuestra bandeja de entrada, para la respuesta. Lo que sí existe son cookies publicitarias de Google, usadas para mostrar anuncios, que se cargan desde la primera página. Si rechazas en el aviso, el script de anuncios se retira y deja de cargarse a partir de la página siguiente; lo que ya haya leído o guardado en la página en la que estabas no se deshace. Puedes revisar tu elección en cualquier momento con el enlace “Revisar elección de cookies”, en el pie de página, y la publicidad personalizada puede desactivarse en la configuración de Google.</div>

  <h2>1. Quién es el responsable</h2>
  <p><strong>{{NOME}}</strong> es un proyecto editorial independiente, publicado en {{DOMINIO_NU}}, {{CANAL_FRASE}}. Para cualquier asunto de esta política —incluidas solicitudes de eliminación o de información—, el contacto es el correo indicado en la página de <a href="contato.html">contacto</a>.</p>

  <h2>2. Qué recopilamos, y qué no</h2>
  <p>No hay registro, inicio de sesión, comentarios, boletín ni formulario de contacto. Ninguna página pide tu nombre, correo, teléfono ni documento. No armamos perfiles de lectores y no vendemos ni compartimos listas de nadie, porque no existe ninguna lista.</p>
  <p>Lo que existe es lo que cualquier sitio recibe por ser visitado: el servidor que aloja estas páginas registra la dirección IP, la fecha y la hora, la página solicitada y el navegador usado. Esos registros sirven para seguridad y diagnóstico de fallas, y no se usan para identificar personas.</p>

  <h2>3. Cookies y publicidad</h2>
  <p>Este sitio muestra anuncios a través de <strong>Google AdSense</strong>. Para ello, Google y sus socios usan cookies —pequeños archivos guardados en tu navegador— para seleccionar y medir los anuncios.</p>
  <ul>
    <li>Google, como proveedor externo, utiliza cookies para mostrar anuncios en este sitio.</li>
    <li>Las cookies publicitarias de Google le permiten a Google y a sus socios mostrar anuncios basados en las visitas del usuario a este y a otros sitios de internet.</li>
    <li>Socios y redes de terceros también pueden usar cookies, identificadores de dispositivo o tecnología similar para medir y personalizar los anuncios.</li>
    <li>Ninguno de esos datos pasa por nosotros: el sitio no recibe, no almacena y no tiene acceso a lo que esas redes recopilan.</li>
  </ul>
  <p>Puedes desactivar la publicidad personalizada —en todos los sitios de la red de Google, no solo en este— en <a href="https://adssettings.google.com" rel="noopener">adssettings.google.com</a>. Las reglas completas de Google están en <a href="https://policies.google.com/technologies/ads?hl=es-419" rel="noopener">policies.google.com/technologies/ads</a>, y para excluirte de la publicidad basada en el comportamiento de varias redes a la vez existe <a href="https://www.aboutads.info/choices/" rel="noopener">aboutads.info/choices</a>.</p>
  <p>Todo navegador también permite bloquear o borrar cookies. Hacerlo no impide leer nada: el contenido de este sitio no depende de cookies para funcionar.</p>

  <h2>4. Qué guardamos en tu navegador</h2>
  <p>Una sola cosa, y no sale de tu dispositivo: cuando respondes al aviso de cookies, tu elección queda registrada en el almacenamiento local del navegador, bajo la clave <code>{{CHAVE}}</code>. Sirve solo para no volver a preguntarte en cada página. No es una cookie, no se envía a ningún servidor y desaparece cuando borras los datos del sitio o haces clic en “Revisar elección de cookies”, en el pie de cualquier página: la elección guardada se borra y el aviso vuelve a aparecer.</p>

  <h2>5. Contenido de terceros</h2>
  <p>Un único servicio externo participa en la visualización de estas páginas: <strong>Google AdSense</strong>, que entrega los anuncios. El script de anuncios se carga desde la primera página, antes de cualquier respuesta. Si rechazas en el aviso, se retira y deja de cargarse a partir de la página siguiente; lo que ya haya mostrado, leído o guardado en la página en la que estabas no se deshace, y las cookies que Google ya haya guardado quedan en el navegador hasta que las borres.</p>
  <p><strong>YouTube</strong> solo entra en escena si haces clic en un enlace al canal: ningún video está incrustado en estas páginas. Todo lo demás —las imágenes de las fichas de obra y las fuentes tipográficas— viene de este mismo dominio.</p>

  <h2>6. Tus derechos según la LGPD</h2>
  <p>La Ley General de Protección de Datos de Brasil (LGPD, Ley n.º 13.709/2018) te garantiza el derecho a confirmar si hay tratamiento de datos tuyos, a acceder a ellos, a corregirlos, a pedir su anonimización o eliminación, a solicitar su portabilidad, a saber con quién se compartieron y a revocar el consentimiento en cualquier momento.</p>
  <p>Aquí el ejercicio de esos derechos es breve, porque la base de datos que podríamos entregar está prácticamente vacía. Aun así, toda solicitud hecha a través de la página de <a href="contato.html">contacto</a> será respondida. Para revocar la elección hecha en el aviso de cookies, usa el enlace “Revisar elección de cookies”, en el pie de cualquier página. Para los datos que Google recopila a través de los anuncios, la solicitud debe hacerse al propio Google: nosotros mostramos el espacio, pero es Google quien trata esos datos.</p>

  <h2>7. Niños y adolescentes</h2>
  <p>El contenido de este sitio no está dirigido a menores de 13 años, y no recopilamos a sabiendas datos de niños. Si eres responsable de un niño y crees que algún dato suyo llegó hasta aquí, ponte en contacto para que sea eliminado.</p>

  <h2>8. Cambios en esta política</h2>
  <p>Si algo cambia —una nueva red de anuncios, una herramienta de medición, una sección de comentarios—, esta página cambia también, y la fecha de arriba se actualiza.</p>

  <div class="botoes" style="margin-top:2.5rem"><a class="botao cheio" href="index.html#obras">Ver las obras</a></div>
</div></main>
"""

ACERCA_ES = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Acerca de</span>
  <h1>Acerca de {{NOME}}</h1>

  <h2>1. Qué es</h2>
  <p><strong>Arquitetura do Impossível</strong> (Arquitectura de lo Imposible) es un proyecto editorial independiente, hecho en Brasil, sobre grandes construcciones: cómo una obra que parecía imposible quedó en pie. Cada página de este sitio acompaña un episodio del canal de YouTube, {{CANAL}}, en portugués, y se publica antes del estreno, cuando el episodio todavía está por salir. Va más allá del video: trae la ficha técnica completa, las fuentes, las imágenes con crédito y las divergencias que no caben en un video.</p>
  <p>La pregunta es siempre la misma: <em>qué hacía imposible esta obra, y quién lo resolvió</em> —con qué cálculo, con qué material, con qué improvisación—. El protagonista es el problema de ingeniería; las personas entran como quienes lo enfrentaron. Obras de Brasil y del resto del mundo, una por semana.</p>

  <h2>2. Cómo se hace una página</h2>
  <ul>
    <li><strong>La ficha de cada obra cubre lo que suele faltar:</strong> cuántos obreros, cuánto tiempo, cuánto costó, quién se lesionó y quién murió, cada línea con su fuente.</li>
    <li><strong>Cada cifra lleva un sello de confianza:</strong> confirmada en dos o más fuentes, fuente única (el texto dice cuál), divergencia (mostramos las versiones y no elegimos) o sin registro (decimos que nadie lo registró, en lugar de inventar).</li>
    <li><strong>El mito desmontado es parte de la historia:</strong> el obrero enterrado en el concreto, la obra "hecha en X días", la cuenta de muertos que nadie verificó.</li>
    <li><strong>Valor actual solo con método declarado.</strong> Convertir dinero antiguo sin decir cómo es inventar cifras.</li>
    <li><strong>Textos íntegramente propios.</strong> Las fuentes quedan listadas al final de cada página.</li>
  </ul>

  <h2>3. Imágenes</h2>
  <p>Solo se usan fotografías, planos y documentos reales, de acervos en dominio público o bajo una licencia Creative Commons que permite el uso comercial, con autor y licencia acreditados en cada página. En este sitio no se usan imágenes generadas por IA.</p>

  <h2>4. Correcciones</h2>
  <p>¿Hay una fecha, un nombre o una cifra equivocados? Escribe a través de la página de <a href="contato.html">contacto</a>, de preferencia con la fuente. El error confirmado se corrige aquí, y la corrección vale también para lo que venga después en el canal.</p>

  <h2>5. Quién lo hace</h2>
  <p>{{NOME}} se escribe, se investiga y se mantiene de forma independiente, sin vínculo con ninguna universidad, empresa u organismo público. Es del mismo creador de otros dos proyectos con el mismo cuidado por las fuentes: <a href="{{VO}}" rel="noopener">Vestígio Oculto</a>, sobre arqueología y misterio, y <a href="{{XB}}" rel="noopener">Xadrez Bélico</a>, sobre batallas explicadas como una partida de ajedrez (ambos en portugués).</p>
  <p>El sitio se sostiene con anuncios de Google AdSense, descritos en la <a href="privacidade.html">política de privacidad</a>. Ningún anuncio interfiere en lo que se escribe.</p>
</div></main>
"""

CONTACTO_ES = """<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Contacto</span>
  <h1>Escribe a {{NOME}}</h1>
  <p class="lead">Una corrección, el crédito de una imagen, una solicitud sobre tus datos o cualquier otro asunto: el camino es uno solo.</p>
  <div class="resumo"><strong>Correo:</strong> <a href="mailto:allangipa@gmail.com">allangipa@gmail.com</a></div>

  <h2>Para qué escribir</h2>
  <ul>
    <li><strong>Correcciones.</strong> Una fecha, un nombre o una cifra equivocados. Envía la fuente: es lo que permite corregir rápido.</li>
    <li><strong>Imágenes y créditos.</strong> Si eres autor de una imagen usada aquí y el crédito está incompleto, o quieres que se retire, escríbenos.</li>
    <li><strong>Tus datos.</strong> Solicitudes según la LGPD, conforme a la <a href="privacidade.html">política de privacidad</a>.</li>
    <li><strong>Temas, prensa y alianzas.</strong> Las sugerencias de temas también son bienvenidas.</li>
  </ul>

  <h2>Cómo respondemos</h2>
  <p>No hay formulario ni registro: la conversación es por correo, y tu dirección no se usa para nada más que responder. La corrección confirmada entra en la página.</p>
</div></main>
"""


def pagina_privacidade():
    """Escrita para ESTE site, não copiada de modelo: diz só o que ele faz.
    Adaptada da política do Vestígio Oculto, que tem o mesmo desenho. A versão
    em inglês e a em espanhol dizem exatamente o mesmo: mudou uma, mudam as outras."""
    base = "" if L == BASE_IDIOMA else "../"
    yt = f'<a href="{CANAL}" target="_blank" rel="noopener">@ArquiteturadoImpossível</a>'
    if L == "en":
        canal = f"with a matching YouTube channel, {yt}" if CANAL else "with a matching YouTube channel"
        modelo = PRIVACY_EN
    elif L == "es":
        canal = f"con un canal correspondiente en YouTube, {yt}" if CANAL else "con un canal correspondiente en YouTube"
        modelo = PRIVACIDAD_ES
    else:
        canal = f"com canal correspondente no YouTube, {yt}" if CANAL else "com canal correspondente no YouTube"
        modelo = PRIVACIDADE
    corpo = (modelo.replace("{{NOME}}", NOME).replace("{{CANAL_FRASE}}", canal)
             .replace("{{CHAVE}}", CHAVE_CONSENTIMENTO).replace("{{DOMINIO_NU}}", DOMINIO.split("//")[1]))
    u = url_de(L, "privacidade.html")
    TITULO_PRIV, DESC_PRIV = seo_fixas()["privacidade.html"]
    return (cabeca(TITULO_PRIV, DESC_PRIV, u, f"{DOMINIO}/assets/img/og-home.jpg", base,
                   [{"@context": "https://schema.org", "@type": "WebPage", "name": TITULO_PRIV, "description": DESC_PRIV,
                     "url": u, "inLanguage": cfg("hreflang")},
                    migalhas((NOME, url_de(L, "index.html")), (tr("Política de privacidade"), u))])
            + topo(base) + corpo + rodape(base) + consentimento(base) + SCRIPT)


def pagina_sobre():
    base = "" if L == BASE_IDIOMA else "../"
    canal = f'<a href="{CANAL}" target="_blank" rel="noopener">@ArquiteturadoImpossível</a>' if CANAL else {"en": "on YouTube", "es": "en YouTube"}.get(L, "no YouTube")
    if L in ("en", "es"):
        corpo = {"en": ABOUT_EN, "es": ACERCA_ES}[L].replace("{{CANAL}}", canal).replace("{{NOME}}", NOME) \
            .replace("{{VO}}", SITE_IRMAO_VO).replace("{{XB}}", SITE_IRMAO_XB)
    else:
        corpo = SOBRE_PT(canal)
    u = url_de(L, "sobre.html")
    TITULO_SOBRE, DESC_SOBRE = seo_fixas()["sobre.html"]
    return (cabeca(TITULO_SOBRE, DESC_SOBRE, u, f"{DOMINIO}/assets/img/og-home.jpg", base,
                   [{"@context": "https://schema.org", "@type": "AboutPage", "name": TITULO_SOBRE, "description": DESC_SOBRE,
                     "url": u, "inLanguage": cfg("hreflang")},
                    migalhas((NOME, url_de(L, "index.html")), (tr("Sobre"), u))])
            + topo(base, "sobre") + corpo + rodape(base) + consentimento(base) + SCRIPT)


def SOBRE_PT(canal):
    return f"""<main id="conteudo"><div class="casca privacidade">
  <span class="rotulo">Sobre</span>
  <h1>Sobre o {NOME}</h1>

  <h2>1. O que é</h2>
  <p>O <strong>Arquitetura do Impossível</strong> é um projeto editorial independente, feito no Brasil, sobre grandes construções: como uma obra que parecia impossível ficou de pé. Cada página deste site acompanha um episódio do canal no YouTube, {canal}, e é publicada antes da estreia, quando o episódio ainda está para sair. Vai além do vídeo: traz a ficha técnica completa, as fontes, as imagens com crédito e as divergências que não cabem num vídeo.</p>
  <p>A pergunta é sempre a mesma: <em>o que tornava esta obra impossível, e quem resolveu</em> — com que conta, com que material, com que improviso. O protagonista é o problema de engenharia; as pessoas entram como quem o enfrentou. Obras do Brasil e do resto do mundo, uma por semana.</p>

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
  <p>O {NOME} é escrito, apurado e mantido de forma independente, sem vínculo com universidade, empresa ou órgão público. É do mesmo criador de outros dois projetos com o mesmo cuidado com a fonte: <a href="{SITE_IRMAO_VO}" rel="noopener">Vestígio Oculto</a>, sobre arqueologia e mistério, e <a href="{SITE_IRMAO_XB}" rel="noopener">Xadrez Bélico</a>, sobre batalhas explicadas como partida.</p>
  <p>O site se mantém com anúncios do Google AdSense, descritos na <a href="privacidade.html">política de privacidade</a>. Nenhum anúncio interfere no que é escrito.</p>
</div></main>
"""


def pagina_contato():
    base = "" if L == BASE_IDIOMA else "../"
    corpo = ({"en": CONTACT_EN, "es": CONTACTO_ES}[L].replace("{{NOME}}", NOME)
             if L in ("en", "es") else CONTATO_PT())
    u = url_de(L, "contato.html")
    TITULO_CONTATO, DESC_CONTATO = seo_fixas()["contato.html"]
    return (cabeca(TITULO_CONTATO, DESC_CONTATO, u, f"{DOMINIO}/assets/img/og-home.jpg", base,
                   [{"@context": "https://schema.org", "@type": "ContactPage", "name": TITULO_CONTATO, "description": DESC_CONTATO,
                     "url": u, "inLanguage": cfg("hreflang")},
                    migalhas((NOME, url_de(L, "index.html")), (tr("Contato"), u))])
            + topo(base, "contato") + corpo + rodape(base) + consentimento(base) + SCRIPT)


def CONTATO_PT():
    return f"""<main id="conteudo"><div class="casca privacidade">
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

def sitemap_xml(entradas):
    """Um sitemap só, com as versões de cada página em xhtml:link (hreflang)."""
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for lg, chave, data in entradas:
        alt = alternativos(chave)
        extra = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>' for h, u in alt)
        linhas.append(f"  <url><loc>{url_de(lg, chave)}</loc><lastmod>{data}</lastmod>{extra}{chr(10) + '  ' if extra else ''}</url>")
    return "\n".join(linhas) + "\n</urlset>\n"


def main():
    global TEMAS, L, PAGINA
    obras = carregar()
    temas_pt = carregar_temas(obras)
    carregar_idiomas()
    trads = carregar_traducoes(obras, OBRIGATORIOS, "obra")
    for lg, d in trads.items():
        for o in d.values():
            conferir_perguntas(f"{PASTA_ITENS}/{lg}/{o['_arquivo'].name}", o)
    temas_por = {BASE_IDIOMA: temas_pt, **carregar_temas_traduzidos(temas_pt, {lg: set(d) for lg, d in trads.items()})}
    # idioma sem nenhuma obra traduzida ainda não entra no ar
    for lg in list(ATIVOS):
        if lg != BASE_IDIOMA and not trads.get(lg):
            ATIVOS.remove(lg)
            print(f"idioma '{lg}': dicionário pronto, nenhuma {PASTA_ITENS[:-1]} traduzida — fica fora do ar")

    # o que existe em cada idioma (decide links, hreflang e seletor)
    EXISTE[BASE_IDIOMA] = ({"index.html", "sobre.html", "contato.html", "privacidade.html"}
                           | {f"obras/{o['slug']}.html" for o in obras} | {f"temas/{t['slug']}.html" for t in temas_pt})
    for lg in ATIVOS[1:]:
        EXISTE[lg] = ({"index.html"} | {f"obras/{s}.html" for s in trads[lg]}
                      | {f"temas/{t['slug']}.html" for t in temas_por[lg]}
                      | ({"sobre.html", "contato.html", "privacidade.html"} if lg in FIXAS_IDIOMAS else set()))

    def lista_de(lg):
        """Todas as obras, na versão do idioma quando existe (para links e "Leia também")."""
        return obras if lg == BASE_IDIOMA else [trads[lg].get(o["slug"], o) for o in obras]

    def traduzidas(lg):
        return obras if lg == BASE_IDIOMA else [trads[lg][o["slug"]] for o in obras if o["slug"] in trads[lg]]

    for lg in ATIVOS:
        L = lg
        TEMAS = temas_por[lg]
        fixas = seo_fixas()
        seo = {k: v for k, v in fixas.items() if k in EXISTE[lg]}
        seo.update({f"obras/{o['slug']}": (titulo_seo(o), o["resumo"]) for o in traduzidas(lg)})
        seo.update({f"temas/{t['slug']}": (titulo_tema(t), t["resumo"]) for t in TEMAS})
        conferir_seo(seo, lg)

    css = (SRC / "arquitetura.css").read_text(encoding="utf-8").replace("url(/assets/fontes/", "url(fontes/")
    (RAIZ / "assets").mkdir(exist_ok=True)
    (RAIZ / "assets" / "arquitetura.css").write_text(css, encoding="utf-8")
    (RAIZ / "favicon.svg").write_text(simbolo("0 0 1020 886", rotulo=NOME), encoding="utf-8")
    logo_png()
    og_casa = og_home()

    saida = {}           # caminho relativo -> html (grava só no fim, se tudo passou)
    datas = {}           # (idioma, chave) -> lastmod
    fixas_data = data_git(Path(__file__).resolve())
    for lg in ATIVOS:
        L = lg
        TEMAS = temas_por[lg]
        pre = prefixo(lg)
        todas = lista_de(lg)
        delas = traduzidas(lg)
        for o in delas:
            PAGINA = f"obras/{o['slug']}.html"
            saida[pre + PAGINA] = pagina_obra(o, todas, og_obra(o))
            datas[(lg, PAGINA)] = data_git(o.get("_arquivo") or SRC / "obras" / f"{o['num']}-{o['slug']}.json")
        por_slug = {o["slug"]: o for o in todas}
        d_temas = data_git(SRC / ("temas.json" if lg == BASE_IDIOMA else f"temas.{lg}.json")) if TEMAS else fixas_data
        for t in TEMAS:
            PAGINA = f"temas/{t['slug']}.html"
            primeira = min((por_slug[s] for s in t[CHAVE_MEMBROS]), key=lambda o: o["num"])
            og_t = og_obra(primeira, f"og-{pre.replace('/', '-')}tema-{t['slug']}.jpg",
                           tr("TEMA  ·  {n} OBRAS", n=len(t[CHAVE_MEMBROS])), t["nome"])
            saida[pre + PAGINA] = pagina_tema(t, todas, og_t)
            datas[(lg, PAGINA)] = max([d_temas, fixas_data] + [datas[(lg, f"obras/{s}.html")] for s in t[CHAVE_MEMBROS]])
        PAGINA = "index.html"
        saida[pre + PAGINA] = home(delas, og_casa, total=len(obras))
        if lg == BASE_IDIOMA or lg in FIXAS_IDIOMAS:
            for chave, fn in (("privacidade.html", pagina_privacidade), ("sobre.html", pagina_sobre),
                              ("contato.html", pagina_contato)):
                PAGINA = chave
                saida[pre + chave] = fn()
                datas[(lg, chave)] = fixas_data
        if lg == BASE_IDIOMA:
            PAGINA = "404.html"
            saida["404.html"] = pagina_404()
        datas[(lg, "index.html")] = max([fixas_data] + [d for (l2, _), d in datas.items() if l2 == lg])

    faltam = {lg: sorted(v) for lg, v in FALTANDO.items() if v}
    if faltam:
        falha("textos da interface sem tradução (acrescente em _src/i18n/<id>.json, em \"textos\"):\n"
              + "\n".join(f"  [{lg}] {s!r}" for lg, v in faltam.items() for s in v))
    fonte_build = Path(__file__).read_text(encoding="utf-8")
    for lg in ATIVOS[1:]:
        # o que nenhuma página usou E não aparece mais no build: o original mudou
        sobra = {s for s in set(I18N[lg]["textos"]) - USADOS[lg] if s not in fonte_build}
        if sobra:
            print(f"aviso [{lg}]: {len(sobra)} texto(s) no dicionário que o build não usa mais (original mudou?):")
            for s in sorted(sobra):
                print("   ", repr(s[:90]))

    # grava, e apaga as páginas que deixaram de ser geradas
    for rel, txt in saida.items():
        destino = RAIZ / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(txt, encoding="utf-8")
    pastas = [RAIZ / "obras", RAIZ / "temas"] + [RAIZ / lg / sub for lg in IDIOMAS if lg != BASE_IDIOMA
                                                for sub in ("obras", "temas", "")]
    for pasta in pastas:
        if pasta.is_dir():
            for velho in pasta.glob("*.html"):
                rel = str(velho.relative_to(RAIZ)).replace("\\", "/")
                if rel not in saida:
                    velho.unlink()
                    print("removido (fora do build):", rel)
    for lg in IDIOMAS:
        if lg != BASE_IDIOMA:
            for sub in ("obras", "temas", ""):
                d = RAIZ / lg / sub
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()

    ads = RAIZ / "ads.txt"
    if ADSENSE_LIGADO:
        ads.write_text("# Declaração de vendedor autorizado (IAB ads.txt)\n"
                       "# Gerado por _src/build.py a partir de ADSENSE_PUB. Não editar à mão.\n"
                       f"google.com, {ADSENSE_PUB}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    elif ads.exists():
        ads.unlink()

    # sitemap: português primeiro, na ordem de sempre; depois cada idioma
    ordem = []
    for lg in ATIVOS:
        chaves = (["index.html"] + [f"obras/{o['slug']}.html" for o in obras]
                  + (["sobre.html", "contato.html", "privacidade.html"] if lg == BASE_IDIOMA or lg in FIXAS_IDIOMAS else [])
                  + [f"temas/{t['slug']}.html" for t in temas_por[lg]])
        ordem += [(lg, c, datas[(lg, c)]) for c in chaves if (lg, c) in datas]
    (RAIZ / "sitemap.xml").write_text(sitemap_xml(ordem), encoding="utf-8")
    (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /_src/\n\nSitemap: {DOMINIO}/sitemap.xml\n", encoding="utf-8")

    L = BASE_IDIOMA
    print(f"ok: {len(obras)} obras, {len(EM_APURACAO)} em apuração, {len(temas_pt)} temas · idiomas no ar: {', '.join(ATIVOS)}")
    for lg in ATIVOS[1:]:
        print(f"  [{lg}] {len(trads[lg])} obra(s) traduzida(s): {', '.join(sorted(trads[lg]))}; {len(temas_por[lg])} tema(s)")
    for o in obras:
        print(f"  {o['num']} {o['obra']}: {len(o['ficha'])} linhas de ficha, {len(o['historia'])} seções, {len(o['imagens'])} imagens")


if __name__ == "__main__":
    main()
