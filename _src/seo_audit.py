"""Auditoria de SEO do site GERADO — rode depois do build, antes do push.

O build confere o que sai dos JSON (título, description). Esta auditoria lê os
.html prontos, como um buscador leria, e confere o que só existe no resultado:
canonical, hreflang recíproco, og:*, JSON-LD, h1, alt, links e imagens locais,
sitemap e robots.

    python _src/seo_audit.py            # só os arquivos daqui
    python _src/seo_audit.py --no-ar    # também pede cada URL do sitemap ao site no ar

Sai com código 1 se houver erro; avisos não barram.
"""
import json
import re
import sys
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from xml.etree import ElementTree

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "_src"))
from build import DOMINIO, IDIOMAS, TITULO_MAX, DESCRICAO_MIN, DESCRICAO_MAX  # noqa: E402

LANG_HTML = {"pt": "pt-BR", "en": "en", "es": "es"}
FORA = {"_src", ".claude", ".git", "assets"}
SEM_INDICE = {"404.html"}   # noindex, sem canonical, fora do sitemap

erros, avisos = [], []


class Pagina(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.titulo, self._no_titulo = "", False
        self.meta, self.links = {}, []          # meta: nome/propriedade -> [conteúdos]
        self.canonical, self.hreflang = None, {}
        self.jsonld, self._no_ld, self._ld = [], False, ""
        self.h1, self.imgs, self.hrefs, self.srcs = 0, [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._no_titulo = True
        elif tag == "meta":
            chave = a.get("name") or a.get("property")
            if chave:
                self.meta.setdefault(chave, []).append(a.get("content", ""))
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if rel == "canonical":
                self.canonical = a.get("href")
            elif rel == "alternate" and a.get("hreflang"):
                if a["hreflang"] in self.hreflang:
                    erros.append(f"{self.nome}: hreflang {a['hreflang']} repetido")
                self.hreflang[a["hreflang"]] = a.get("href")
            elif rel in ("icon", "stylesheet") and a.get("href"):
                self.srcs.append(a["href"])
            elif rel == "preload":
                if a.get("href"):
                    self.srcs.append(a["href"])
                if a.get("imagesrcset"):
                    self.srcs += [p.split()[0] for p in a["imagesrcset"].split(",")]
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._no_ld, self._ld = True, ""
        elif tag == "h1":
            self.h1 += 1
        elif tag == "img":
            self.imgs.append(a)
            if a.get("src"):
                self.srcs.append(a["src"])
            if a.get("srcset"):
                self.srcs += [p.split()[0] for p in a["srcset"].split(",")]
        elif tag == "source" and a.get("srcset"):
            self.srcs += [p.split()[0] for p in a["srcset"].split(",")]
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._no_titulo = False
        elif tag == "script" and self._no_ld:
            self._no_ld = False
            self.jsonld.append(self._ld)

    def handle_data(self, data):
        if self._no_titulo:
            self.titulo += data
        elif self._no_ld:
            self._ld += data


def url_publica(rel):
    """Caminho do arquivo -> endereço público (index.html vira a pasta)."""
    p = rel.as_posix()
    if p == "index.html":
        p = ""
    elif p.endswith("/index.html"):
        p = p[: -len("index.html")]
    return f"{DOMINIO}/{p}"


def arquivo_de(url):
    """Endereço público (do domínio) -> arquivo local, ou None se for externo."""
    u = urlparse(url)
    if u.netloc and u.netloc != urlparse(DOMINIO).netloc:
        return None
    caminho = unquote(u.path).lstrip("/")
    if caminho == "" or caminho.endswith("/"):
        caminho += "index.html"
    return RAIZ / caminho


def idioma_do(rel):
    return rel.parts[0] if rel.parts[0] in IDIOMAS and len(rel.parts) > 1 else "pt"


def paginas():
    for f in sorted(RAIZ.rglob("*.html")):
        rel = f.relative_to(RAIZ)
        if rel.parts[0] not in FORA:
            yield rel


def auditar_pagina(rel):
    nome = rel.as_posix()
    p = Pagina()
    p.nome = nome
    p.feed((RAIZ / rel).read_text(encoding="utf-8"))
    lg = idioma_do(rel)
    url = url_publica(rel)
    indexavel = rel.name not in SEM_INDICE

    if p.lang != LANG_HTML.get(lg):
        erros.append(f"{nome}: <html lang={p.lang!r}>, esperado {LANG_HTML.get(lg)!r}")

    titulo = p.titulo.strip()
    desc = (p.meta.get("description") or [""])[0]
    if not titulo:
        erros.append(f"{nome}: sem <title>")
    elif len(titulo) > TITULO_MAX:
        erros.append(f"{nome}: título com {len(titulo)} caracteres ({titulo!r})")
    if indexavel and not DESCRICAO_MIN <= len(desc) <= DESCRICAO_MAX:
        erros.append(f"{nome}: description com {len(desc)} caracteres ({DESCRICAO_MIN}–{DESCRICAO_MAX})")
    for chave in ("description", "robots", "og:title", "og:url", "og:description", "og:image"):
        if len(p.meta.get(chave, [])) > 1:
            erros.append(f"{nome}: meta {chave} repetida")

    robots = (p.meta.get("robots") or [""])[0]
    if indexavel:
        if "noindex" in robots:
            erros.append(f"{nome}: noindex numa página que deveria ser indexada")
        if p.canonical != url:
            erros.append(f"{nome}: canonical {p.canonical!r}, esperado {url!r}")
        og = {k: (p.meta.get(k) or [""])[0] for k in ("og:title", "og:description", "og:url", "og:image")}
        if og["og:url"] != url:
            erros.append(f"{nome}: og:url {og['og:url']!r} difere do canonical")
        for k in ("og:title", "og:description", "og:image"):
            if not og[k]:
                erros.append(f"{nome}: sem {k}")
        if og["og:image"]:
            alvo = arquivo_de(og["og:image"])
            if alvo is None:
                avisos.append(f"{nome}: og:image fora do domínio ({og['og:image']})")
            elif not alvo.exists():
                erros.append(f"{nome}: og:image não existe ({og['og:image']})")
        if not p.meta.get("twitter:card"):
            avisos.append(f"{nome}: sem twitter:card")
    else:
        if "noindex" not in robots:
            erros.append(f"{nome}: deveria levar noindex")
        if p.canonical:
            erros.append(f"{nome}: não deveria ter canonical (é servida em qualquer endereço)")

    if p.h1 != 1:
        erros.append(f"{nome}: {p.h1} <h1> (esperado 1)")

    for i, bloco in enumerate(p.jsonld, 1):
        try:
            d = json.loads(bloco)
        except json.JSONDecodeError as e:
            erros.append(f"{nome}: JSON-LD #{i} inválido ({e})")
            continue
        nos = d.get("@graph", [d])
        if "@context" not in d or any("@type" not in n for n in nos):
            erros.append(f"{nome}: JSON-LD #{i} sem @context ou @type")
        for d in (n for n in nos if n.get("@type") == "Article"):
            for k in ("headline", "image", "datePublished", "author", "publisher"):
                if k not in d:
                    erros.append(f"{nome}: Article sem {k}")
            if len(d.get("headline", "")) > 110:
                avisos.append(f"{nome}: headline do Article com mais de 110 caracteres")
            if d.get("inLanguage") != LANG_HTML.get(lg):
                erros.append(f"{nome}: Article inLanguage {d.get('inLanguage')!r}")
    if indexavel and not p.jsonld:
        avisos.append(f"{nome}: sem JSON-LD")

    for im in p.imgs:
        if not im.get("src"):
            continue   # a <img> vazia da lupa, que o script da página preenche ao ampliar
        if "alt" not in im:
            erros.append(f"{nome}: <img> sem alt ({im.get('src')})")
        elif not im["alt"].strip() and im.get("role") != "presentation" and im.get("aria-hidden") != "true":
            avisos.append(f"{nome}: <img> com alt vazio ({im.get('src')})")
        if not (im.get("width") and im.get("height")):
            avisos.append(f"{nome}: <img> sem width/height ({im.get('src')})")

    # links e recursos locais
    for ref in set(p.hrefs) | set(p.srcs):
        if ref.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
            continue
        alvo = arquivo_de(urljoin(url, ref))
        if alvo is not None and not alvo.exists():
            erros.append(f"{nome}: link ou recurso quebrado → {ref}")

    return {"nome": nome, "lg": lg, "url": url, "indexavel": indexavel,
            "titulo": titulo, "desc": desc, "hreflang": p.hreflang}


def auditar_hreflang(info):
    por_url = {i["url"]: i for i in info}
    for i in info:
        h = i["hreflang"]
        if not i["indexavel"]:
            if h:
                erros.append(f"{i['nome']}: página noindex com hreflang")
            continue
        if not h:
            continue   # existe só num idioma: hreflang dispensável
        proprio = LANG_HTML[i["lg"]]
        if h.get(proprio) != i["url"]:
            erros.append(f"{i['nome']}: hreflang {proprio} não aponta para a própria página")
        if "x-default" not in h:
            erros.append(f"{i['nome']}: hreflang sem x-default")
        for cod, href in h.items():
            if cod == "x-default":
                continue
            outra = por_url.get(href)
            if outra is None:
                erros.append(f"{i['nome']}: hreflang {cod} → página inexistente ({href})")
                continue
            if LANG_HTML[outra["lg"]] != cod:
                erros.append(f"{i['nome']}: hreflang {cod} aponta para página em {outra['lg']}")
            if outra["hreflang"] != h:
                erros.append(f"{i['nome']}: hreflang não recíproco com {outra['nome']}")
        if h.get("x-default") not in h.values() or list(h.values()).count(h.get("x-default")) < 2:
            erros.append(f"{i['nome']}: x-default não é uma das versões listadas")


def auditar_unicos(info):
    for campo, rotulo in (("titulo", "título"), ("desc", "description")):
        vistos = defaultdict(list)
        for i in info:
            if i["indexavel"] and i[campo]:
                vistos[(i["lg"], i[campo])].append(i["nome"])
        for (lg, _), nomes in vistos.items():
            if len(nomes) > 1:
                erros.append(f"{rotulo} repetido em [{lg}]: {', '.join(nomes)}")


def auditar_sitemap(info):
    arq = RAIZ / "sitemap.xml"
    if not arq.exists():
        erros.append("sitemap.xml não existe")
        return []
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    try:
        arvore = ElementTree.parse(arq)
    except ElementTree.ParseError as e:
        erros.append(f"sitemap.xml inválido ({e})")
        return []
    por_url = {i["url"]: i for i in info}
    locs = []
    for u in arvore.getroot().findall("s:url", ns):
        loc = u.findtext("s:loc", namespaces=ns)
        locs.append(loc)
        i = por_url.get(loc)
        if i is None:
            erros.append(f"sitemap: {loc} não corresponde a nenhuma página")
            continue
        if not i["indexavel"]:
            erros.append(f"sitemap: {loc} é noindex e não deveria estar lá")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", u.findtext("s:lastmod", "", ns)):
            avisos.append(f"sitemap: {loc} sem lastmod AAAA-MM-DD")
        alt = {l.get("hreflang"): l.get("href") for l in u.findall("x:link", ns)}
        if alt != i["hreflang"]:
            erros.append(f"sitemap: alternates de {loc} diferem do hreflang da página")
    if len(locs) != len(set(locs)):
        erros.append("sitemap: URL repetida")
    for i in info:
        if i["indexavel"] and i["url"] not in locs:
            erros.append(f"sitemap: falta {i['url']}")
    return locs


def auditar_robots():
    arq = RAIZ / "robots.txt"
    if not arq.exists():
        erros.append("robots.txt não existe")
        return
    txt = arq.read_text(encoding="utf-8")
    if f"Sitemap: {DOMINIO}/sitemap.xml" not in txt:
        erros.append("robots.txt sem a linha Sitemap do domínio")
    if re.search(r"^Disallow:\s*/\s*$", txt, re.M):
        erros.append("robots.txt bloqueia o site inteiro")


def auditar_no_ar(locs):
    print(f"Conferindo {len(locs)} URLs no ar…")
    for loc in locs:
        req = urllib.request.Request(loc, method="HEAD", headers={"User-Agent": "seo_audit"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status != 200 or r.url != loc:
                    erros.append(f"no ar: {loc} → {r.status} {r.url}")
        except Exception as e:  # noqa: BLE001 — qualquer falha de rede é erro de publicação
            erros.append(f"no ar: {loc} → {e}")


def main():
    info = [auditar_pagina(rel) for rel in paginas()]
    auditar_unicos(info)
    auditar_hreflang(info)
    locs = auditar_sitemap(info)
    auditar_robots()
    if "--no-ar" in sys.argv:
        auditar_no_ar(locs)

    por_lg = defaultdict(int)
    for i in info:
        por_lg[i["lg"]] += 1
    print(f"{len(info)} páginas (" + ", ".join(f"{lg}: {n}" for lg, n in sorted(por_lg.items())) + f"), {len(locs)} no sitemap")
    for a in sorted(set(avisos)):
        print(f"  aviso: {a}")
    for e in sorted(set(erros)):
        print(f"  ERRO: {e}")
    print(f"{len(set(erros))} erro(s), {len(set(avisos))} aviso(s)")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
