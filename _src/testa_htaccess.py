# Uso: python _src/testa_htaccess.py .htaccess <dominio-sem-.com>  (ex.: xadrezbelico)
"""Emula as regras de mod_rewrite do .htaccess (só o que usamos: RewriteCond
com %{HTTP_HOST}/%{HTTPS}, [NC], [OR], RewriteRule ^ alvo [R=301,L])."""
import re, sys
def regras(arq):
    out, conds = [], []
    for l in open(arq, encoding="utf-8"):
        l = l.strip()
        if l.startswith("RewriteCond"):
            _, var, pad, *fl = l.split(None, 3)
            fl = fl[0].strip("[]").split(",") if fl else []
            conds.append((var, pad, fl))
        elif l.startswith("RewriteRule"):
            _, pad, alvo, fl = l.split(None, 3)
            out.append((conds, pad, alvo, fl)); conds = []
    return out
def roda(arq, host, https, uri):
    env = {"%{HTTP_HOST}": host, "%{HTTPS}": "on" if https else "off", "%{REQUEST_URI}": uri}
    for conds, pad, alvo, fl in regras(arq):
        ok, acum = True, None
        for var, p, f in conds:
            neg = p.startswith("!"); p = p.lstrip("!")
            r = bool(re.search(p, env[var], re.I if "NC" in f else 0)) != neg
            acum = r if acum is None else (acum or r) if prev_or else (acum and r)
            prev_or = "OR" in f
            if acum is False and not prev_or: break
        if (acum is None or acum) and re.search(pad, uri.lstrip("/")):
            dest = alvo.replace("%{REQUEST_URI}", uri)
            return dest
    return None
dom = sys.argv[2]
casos = [
    (f"{dom}.com.br", True, "/"), (f"www.{dom}.com.br", False, "/obras/cristo-redentor.html?x=1"),
    (f"WWW.{dom.upper()}.COM.BR", True, "/en/obras/cristo-redentor.html"),
    (f"www.{dom}.com", True, "/temas/pontes.html"), (f"{dom}.com", False, "/sobre.html"),
    (f"{dom}.com", True, "/obras/cristo-redentor.html"), (f"{dom}.com.br", True, "/_src/build.py"),
    (f"{dom}.com.br", True, "/n%C3%A3o-existe.html"), ("algo.hostingersite.com", True, "/"),
    (f"{dom}.com.br.", True, "/x"),
]
for h, s, u in casos:
    # o redirecionamento inclui a query string do pedido original (Apache faz isso
    # sozinho quando o alvo não tem "?"); aqui só acrescentamos para mostrar
    d = roda(sys.argv[1], h, s, u.split("?")[0])
    q = ("?" + u.split("?")[1]) if "?" in u and d else ""
    print(f"{'https' if s else 'http '}://{h}{u:45} -> {('301 ' + d + q) if d else '200 (serve)'}")
