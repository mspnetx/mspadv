#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador do site MSPADV — Marcelo Paiva Advocacia (PT + EN).

Uso:  python build.py            -> gera o site na pasta _site/
      python build.py --serve    -> gera e abre um servidor local em http://localhost:8000

Não precisa instalar nada além do Python 3.
Conteúdo editável fica em content/ (veja o README.md).
"""
import datetime
import html
import json
import os
import posixpath
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "_site")
LANGS = ["pt", "en"]


def load(*p):
    with open(os.path.join(C, *p), encoding="utf-8") as f:
        return json.load(f)


CFG = load("site.json")
ICONS = load("icones.json")
AREAS = load("areas.json")
T = {l: load(l, "textos.json") for l in LANGS}
SITE_URL = (os.environ.get("SITE_URL") or CFG.get("url") or "").rstrip("/")
BASE_PATH = (re.sub(r"^https?://[^/]+", "", SITE_URL) + "/") if SITE_URL else "/"
WA = CFG["whatsapp"]
TEL = CFG["telefone"]
TEL_FMT = CFG["telefone_fmt"]
EMAIL = CFG["email"]

STATIC = {
    "home": {"pt": "index.html", "en": "en/index.html"},
    "sobre": {"pt": "sobre.html", "en": "en/about.html"},
    "areas": {"pt": "areas-de-atuacao.html", "en": "en/practice-areas.html"},
    "artigos": {"pt": "artigos.html", "en": "en/articles.html"},
    "contato": {"pt": "contato.html", "en": "en/contact.html"},
}
ART_DIR = {"pt": "artigos", "en": "en/articles"}
PAGES = {k: dict(v) for k, v in STATIC.items()}  # chave -> {lang: caminho}
DOCS = {"areas": {}, "artigos": {}, "paginas": {}}  # tipo -> chave -> lang -> doc


# ----------------------------------------------------------------- utilidades
def esc(s):
    return html.escape(s, quote=True)


def icon(name):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % ICONS.get(name, ICONS["scale"]))


WA_ICON = ('<svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true"><path d="M16 3C9 3 3.5 8.5 3.5 15.5c0 2.4.7 4.7 1.9 6.7L3 29l7-1.8c1.9 1 4 1.6 6 1.6 7 0 12.5-5.5 12.5-12.5S23 3 16 3zm0 22.7c-1.8 0-3.6-.5-5.1-1.4l-.4-.2-4.1 1.1 1.1-4-.3-.4a10.3 10.3 0 0 1-1.6-5.6c0-5.7 4.7-10.3 10.4-10.3s10.4 4.6 10.4 10.3-4.7 10.5-10.4 10.5zm5.7-7.7c-.3-.2-1.8-.9-2.1-1-.3-.1-.5-.2-.7.2-.2.3-.8 1-.9 1.2-.2.2-.3.2-.6.1-.3-.2-1.3-.5-2.5-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.5-.5c.2-.2.2-.3.3-.5.1-.2 0-.4 0-.6l-.9-2.1c-.2-.5-.4-.5-.6-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.2.2 2.1 3.3 5.2 4.6.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.3-.7.3-1.3.2-1.4-.1-.2-.3-.2-.6-.4z"/></svg>')


def wa_link(lang):
    from urllib.parse import quote
    return "https://wa.me/%s?text=%s" % (WA, quote(T[lang]["wa_msg"]))


def rel(frm, to):
    """Link relativo do arquivo `frm` para o arquivo `to` (frm=None -> caminho absoluto, usado no 404)."""
    if frm is None:
        return BASE_PATH + to
    return posixpath.relpath(to, posixpath.dirname(frm) or ".")


def url(key, lang, frm):
    p = PAGES.get(key, {})
    if lang in p:
        return rel(frm, p[lang])
    return rel(frm, STATIC["home"][lang])


def absurl(path):
    path = re.sub(r"(^|/)index\.html$", r"\1", path)
    return (SITE_URL + "/" + path) if SITE_URL else "/" + path


def fmt_date(iso, lang):
    d = datetime.date.fromisoformat(iso)
    m = T[lang]["common"]["months"][d.month - 1]
    return "%d de %s de %d" % (d.day, m, d.year) if lang == "pt" else "%s %d, %d" % (m, d.day, d.year)


# ------------------------------------------------- front matter + mini-Markdown
def read_doc(path):
    raw = open(path, encoding="utf-8").read().replace("\r\n", "\n").lstrip("﻿")
    meta, body = {}, raw
    m = re.match(r"---\n(.*?)\n---\n?(.*)", raw, flags=re.S)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        body = m.group(2)
    return meta, body


def inline(s, lang, frm):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)\*(?!\w)", r"<em>\1</em>", s)

    def link(m):
        text, href = m.group(1), m.group(2)
        ext = ""
        if href.startswith("@"):
            href = url(href[1:], lang, frm)
        elif href.startswith("http"):
            ext = ' target="_blank" rel="noopener"'
        return '<a href="%s"%s>%s</a>' % (href, ext, text)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, s)


def md(text, lang, frm):
    """Markdown simples: ## títulos, parágrafos, listas (- / 1.), > destaque, **negrito**, *itálico*, [link](url ou @pagina)."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.rstrip() for l in block.strip().split("\n") if l.strip()]
        if not lines:
            continue
        f = lines[0]
        if f.startswith("### "):
            out.append("<h3>%s</h3>" % inline(f[4:], lang, frm))
        elif f.startswith("## "):
            out.append("<h2>%s</h2>" % inline(f[3:], lang, frm))
        elif f.startswith("# "):
            out.append("<h2>%s</h2>" % inline(f[2:], lang, frm))
        elif all(l.startswith(("- ", "* ")) for l in lines):
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(l[2:], lang, frm) for l in lines))
        elif all(re.match(r"\d+[.)] ", l) for l in lines):
            out.append("<ol>%s</ol>" % "".join("<li>%s</li>" % inline(re.sub(r"^\d+[.)] ", "", l), lang, frm) for l in lines))
        elif all(l.startswith(">") for l in lines):
            out.append('<div class="callout">%s</div>' % "".join("<p>%s</p>" % inline(l.lstrip("> "), lang, frm) for l in lines))
        elif f.startswith("<") and not f.startswith(("<em", "<strong", "<a ")):
            out.append("\n".join(lines))
        else:
            out.append("<p>%s</p>" % inline(" ".join(lines), lang, frm))
    return "\n".join(out)


def split_area(body):
    """Separa o texto, os serviços (::: servicos) e as perguntas (::: faq) de uma página de área."""
    svc, faq = [], []

    def grab(name):
        nonlocal body
        m = re.search(r":::\s*%s\s*\n(.*?)\n:::" % name, body, flags=re.S)
        if not m:
            return ""
        body = body.replace(m.group(0), "")
        return m.group(1)
    for line in grab("servicos").split("\n"):
        m = re.match(r"-\s*\*\*(.+?)\*\*\s*\|\s*(.+)", line.strip())
        if m:
            svc.append((m.group(1), m.group(2)))
    for chunk in re.split(r"\n\s*(?=\?)", "\n" + grab("faq")):
        chunk = chunk.strip()
        if chunk.startswith("?"):
            q, _, a = chunk[1:].partition("\n")
            faq.append((q.strip(), " ".join(a.split())))
    return body, svc, faq


# ------------------------------------------------------------ carga do conteúdo
def scan():
    for kind in DOCS:
        for lang in LANGS:
            d = os.path.join(C, lang, kind)
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(".md") or fn.startswith("_"):
                    continue
                key = fn[:-3]
                meta, body = read_doc(os.path.join(d, fn))
                slug = meta.get("slug", key)
                if kind == "artigos":
                    path = "%s/%s.html" % (ART_DIR[lang], slug)
                else:
                    path = ("en/" if lang == "en" else "") + slug + ".html"
                doc = {"key": key, "lang": lang, "meta": meta, "body": body, "path": path, "kind": kind}
                DOCS[kind].setdefault(key, {})[lang] = doc
                PAGES.setdefault(key, {})[lang] = path


def area_items():
    for g in AREAS:
        for it in g["itens"]:
            yield g, it


def articles(lang):
    lst = [v[lang] for v in DOCS["artigos"].values() if lang in v]
    return sorted(lst, key=lambda d: d["meta"].get("data", ""), reverse=True)


# -------------------------------------------------------------------- layout
def head(lang, path, key, title, desc, extra=""):
    t = T[lang]
    css = rel(path, "assets/css/styles.css")
    alts = ""
    for l in LANGS:
        if l in PAGES.get(key, {}):
            alts += '<link rel="alternate" hreflang="%s" href="%s">\n' % (T[l]["lang"], absurl(PAGES[key][l]))
    if "pt" in PAGES.get(key, {}):
        alts += '<link rel="alternate" hreflang="x-default" href="%s">\n' % absurl(PAGES[key]["pt"])
    return """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
{alts}<meta name="robots" content="index, follow">
<meta name="author" content="Marcelo Paiva Advocacia">
<meta property="og:type" content="website">
<meta property="og:locale" content="{ogl}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<meta property="og:site_name" content="MSPADV — Marcelo Paiva Advocacia">
<meta property="og:image" content="{ogimg}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#13262F">
<link rel="icon" type="image/png" href="{fav}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,500&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css}">
{extra}</head>
""".format(lang=t["lang"], title=esc(title), desc=esc(desc), canon=absurl(path or "404.html"), alts=alts, ogl=t["og_locale"],
           ogimg=absurl("assets/img/hero.jpg"), fav=rel(path, "assets/img/favicon.png"), css=css, extra=extra)


def lang_switch(lang, path, key):
    other = "en" if lang == "pt" else "pt"
    target = PAGES.get(key, {}).get(other) or STATIC["artigos" if key in DOCS["artigos"] else "home"][other]
    cur = '<span class="on" aria-current="true">%s</span>' % lang.upper()
    alt = '<a href="%s" hreflang="%s" lang="%s" data-setlang="%s" title="%s">%s</a>' % (
        rel(path, target), T[other]["lang"], T[other]["lang"], other, T[lang]["nav"]["switch"], other.upper())
    inner = (cur + alt) if lang == "pt" else (alt + cur)
    return '<div class="lang-switch" role="group" aria-label="%s">%s</div>' % (T[lang]["nav"]["lang_label"], inner)


def header(lang, path, key):
    t = T[lang]
    n = t["nav"]
    u = lambda k: url(k, lang, path)

    def act(k):
        on = key == k or (k == "areas" and key in DOCS["areas"]) or (k == "artigos" and key in DOCS["artigos"])
        return ' class="active" aria-current="page"' if on else ""
    mega, mob = "", ""
    for g in AREAS:
        links = "".join('<a href="%s">%s</a>' % (u(it["key"]), esc(it[lang][0])) for it in g["itens"] if it.get("key"))
        mega += '<div><span class="mega-h">%s</span>%s</div>' % (esc(g[lang]), links)
    for g, it in area_items():
        if it.get("home") and it.get("key"):
            mob += '<a href="%s" class="sub">%s</a>' % (u(it["key"]), esc(it[lang][0]))
    sw = lang_switch(lang, path, key)
    return """<body>
<a class="skip" href="#conteudo">{skip}</a>
<div class="progress" aria-hidden="true"><span></span></div>
<header class="site-header">
  <div class="wrap nav">
    <a href="{home}" class="brand" aria-label="MSPADV — {nhome}">
      <img src="{logo}" alt="MSPADV — Marcelo Paiva Advocacia" width="52" height="52">
      <span class="brand-txt"><b>MSPADV</b><span>Marcelo Paiva Advocacia</span></span>
    </a>
    <nav aria-label="{menu}">
      <ul class="menu">
        <li><a href="{home}"{a_home}>{nhome}</a></li>
        <li><a href="{sobre}"{a_sobre}>{nsobre}</a></li>
        <li class="has-sub"><a href="{areas}"{a_areas}>{nareas}</a>
          <div class="submenu mega">{mega}<a class="mega-all" href="{areas}">{all} &rarr;</a></div>
        </li>
        <li><a href="{artigos}"{a_art}>{nart}</a></li>
        <li><a href="{contato}"{a_cont}>{ncont}</a></li>
      </ul>
    </nav>
    <div class="nav-cta">
      {sw}
      <a href="{wa}" class="btn btn-gold" target="_blank" rel="noopener">{cta}</a>
    </div>
    <button class="burger" aria-label="{menu}" aria-expanded="false"><span></span><span></span><span></span></button>
  </div>
</header>
<div class="overlay"></div>
<aside class="mobile-panel" aria-label="{menu}">
  {sw}
  <a href="{home}">{nhome}</a>
  <a href="{sobre}">{nsobre}</a>
  <a href="{areas}">{nareas}</a>
  {mob}
  <a href="{artigos}">{nart}</a>
  <a href="{contato}">{ncont}</a>
  <a href="{wa}" class="btn btn-wa btn-block" target="_blank" rel="noopener">{nwa}</a>
  <a href="tel:{tel}" class="btn btn-gold btn-block">{ncall}</a>
</aside>
<main id="conteudo">
""".format(skip=n["skip"], home=u("home"), sobre=u("sobre"), areas=u("areas"), artigos=u("artigos"), contato=u("contato"),
           nhome=n["home"], nsobre=n["sobre"], nareas=n["areas"], nart=n["artigos"], ncont=n["contato"],
           a_home=act("home"), a_sobre=act("sobre"), a_areas=act("areas"), a_art=act("artigos"), a_cont=act("contato"),
           logo=rel(path, "assets/img/logo.png"), mega=mega, mob=mob, all=n["all_areas"], sw=sw, wa=wa_link(lang),
           cta=n["cta"], menu=n["menu"], nwa=n["wa"], ncall=n["call"], tel=TEL)


def footer(lang, path):
    t = T[lang]
    f = t["footer"]
    n = t["nav"]
    u = lambda k: url(k, lang, path)
    links = "".join('<li><a href="%s">%s</a></li>' % (u(it["key"]), esc(it[lang][0]))
                    for g, it in area_items() if it.get("home") and it.get("key"))
    return """</main>
<footer class="site-footer">
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <a href="{home}" class="brand">
        <img src="{logo}" alt="MSPADV" style="height:54px" width="54" height="54" loading="lazy">
        <span class="brand-txt"><b>MSPADV</b><span>Marcelo Paiva Advocacia</span></span>
      </a>
      <p>{about}</p>
    </div>
    <div><h4>{h_areas}</h4><ul class="foot-links">{links}</ul></div>
    <div><h4>{h_nav}</h4>
      <ul class="foot-links">
        <li><a href="{sobre}">{nsobre}</a></li>
        <li><a href="{areas}">{nareas}</a></li>
        <li><a href="{artigos}">{nart}</a></li>
        <li><a href="{contato}">{ncont}</a></li>
        <li><a href="{priv}">{npriv}</a></li>
        <li><a href="{terms}">{nterms}</a></li>
      </ul>
    </div>
    <div class="foot-contact"><h4>{h_contact}</h4>
      <p>{i_pin}<span>{place}</span></p>
      <p>{i_tel}<a href="tel:{tel}">{telf}</a></p>
      <p>{i_mail}<a href="mailto:{email}">{email}</a></p>
      <a href="{wa}" class="btn btn-wa" target="_blank" rel="noopener" style="margin-top:8px">{fwa}</a>
    </div>
  </div>
  <div class="wrap foot-bottom">
    <span>&copy; <span id="year">{year}</span> MSPADV — Marcelo Paiva Advocacia. {rights}</span>
    <span><a href="{priv}">{privs}</a> &middot; <a href="{terms}">{termss}</a></span>
  </div>
  <div class="disclaimer"><div class="wrap">{disc}</div></div>
</footer>
<a class="wa-float" href="{wa}" target="_blank" rel="noopener" aria-label="{nwa}">
  <span class="ico">{waicon}</span><span class="lbl">{nwa}</span>
</a>
<div class="lang-hint" hidden><span>{hint}</span><a href="{althref}" data-setlang="{other}">{hint_go} &rarr;</a><button aria-label="OK" data-dismiss>&times;</button></div>
<script src="{js}" defer></script>
</body>
</html>
""".format(home=u("home"), sobre=u("sobre"), areas=u("areas"), artigos=u("artigos"), contato=u("contato"),
           priv=u("politica-de-privacidade"), terms=u("termos-de-uso"), logo=rel(path, "assets/img/logo.png"),
           about=f["about"], h_areas=f["areas"], h_nav=f["nav"], h_contact=f["contact"], links=links,
           nsobre=n["sobre"], nareas=n["areas"], nart=n["artigos"], ncont=n["contato"], npriv=f["privacy_full"],
           nterms=f["terms_full"], i_pin=icon("pin"), i_tel=icon("phone"), i_mail=icon("mail"), place=f["place"],
           tel=TEL, telf=TEL_FMT, email=EMAIL, wa=wa_link(lang), fwa=f["wa"], year=datetime.date.today().year,
           rights=f["rights"], privs=f["privacy"], termss=f["terms"], disc=f["disclaimer"], nwa=n["wa"],
           waicon=WA_ICON.replace('fill="currentColor"', 'fill="#fff"'), js=rel(path, "assets/js/main.js"),
           hint=T["en" if lang == "pt" else "pt"]["nav"]["hint"], hint_go=T["en" if lang == "pt" else "pt"]["nav"]["hint_go"],
           althref="#", other="en" if lang == "pt" else "pt")


def page(lang, path, key, title, desc, body, extra_head=""):
    doc = head(lang, path, key, title, desc, extra_head) + header(lang, path, key) + body + footer(lang, path)
    # o aviso de idioma aponta para a mesma página no outro idioma
    other = "en" if lang == "pt" else "pt"
    target = PAGES.get(key, {}).get(other) or STATIC["home"][other]
    doc = doc.replace('<a href="#" data-setlang', '<a href="%s" data-setlang' % rel(path, target))
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(doc)
    BUILT.append((path, key, lang))


BUILT = []


# ---------------------------------------------------------------- componentes
def crumbs(lang, path, trail):
    parts = ['<a href="%s">%s</a>' % (url("home", lang, path), T[lang]["nav"]["home"])]
    for label, key in trail:
        parts.append('<a href="%s">%s</a>' % (url(key, lang, path), esc(label)) if key else esc(label))
    return '<div class="crumbs">%s</div>' % "<span>/</span>".join(parts)


def page_hero(lang, path, trail, title, lead, kicker=""):
    k = '<span class="kicker">%s</span>' % kicker if kicker else ""
    return """<section class="page-hero">
  <div class="wrap">
    %s%s
    <h1>%s</h1>
    <p class="lead">%s</p>
  </div>
</section>
""" % (crumbs(lang, path, trail), k, title, lead)


def cta_band(lang, path, title, text):
    c = T[lang]["common"]
    return """<section class="cta-band">
  <div class="wrap" data-reveal>
    <h2>%s</h2>
    <p>%s</p>
    <div class="hero-cta">
      <a href="%s" class="btn btn-wa" target="_blank" rel="noopener">%s %s</a>
      <a href="%s" class="btn btn-gold">%s</a>
    </div>
  </div>
</section>
""" % (title, text, wa_link(lang), WA_ICON, T[lang]["nav"]["wa"], url("contato", lang, path), c["schedule"])


def area_card(it, lang, path, tag=True):
    c = T[lang]["common"]
    title, desc = it[lang]
    if it.get("key"):
        return ('<a class="area-card premium" href="%s" data-reveal>%s<div class="ic">%s</div><h3>%s</h3><p>%s</p>'
                '<span class="more">%s <i>&rarr;</i></span></a>') % (
            url(it["key"], lang, path), '<span class="tag-premium">%s</span>' % c["premium"] if tag else "",
            icon(it["icon"]), esc(title), esc(desc), c["more"])
    return ('<a class="area-card" href="%s" data-reveal><div class="ic">%s</div><h3>%s</h3><p>%s</p>'
            '<span class="more muted">%s <i>&rarr;</i></span></a>') % (
        url("contato", lang, path), icon(it["icon"]), esc(title), esc(desc), c["consult"])


def post_card(doc, lang, path):
    m = doc["meta"]
    return """<a class="post" href="%s" data-reveal>
  <div class="thumb"><span class="cat">%s</span></div>
  <div class="body">
    <span class="date">%s</span>
    <h3>%s</h3>
    <p>%s</p>
    <span class="more">%s <i>&rarr;</i></span>
  </div>
</a>""" % (rel(path, doc["path"]), esc(m.get("categoria", "")), fmt_date(m["data"], lang), esc(m["title"]),
           esc(m.get("resumo", "")), T[lang]["common"]["read"])


def checklist(items, ic="check"):
    return '<ul class="checklist">%s</ul>' % "".join(
        '<li><span class="ck">%s</span><div><b>%s</b><span>%s</span></div></li>' % (icon(ic), a, b) for a, b in items)


def form(lang, title, sub):
    f = T[lang]["form"]
    opts = "".join("<option>%s</option>" % esc(it[lang][0]) for g, it in area_items())
    opts += "<option>%s</option>" % f["other"]
    return """<form class="form-card" data-contact data-wa="{wa}" data-email="{email}" data-endpoint="{endpoint}" data-intro="{intro}" data-labels="{labels}" novalidate>
  <h3>{title}</h3>
  <p class="sub">{sub}</p>
  <div class="field"><label for="nome">{name}</label><input id="nome" name="nome" type="text" autocomplete="name" placeholder="{name_ph}" required></div>
  <div class="form-row">
    <div class="field"><label for="tel">{phone}</label><input id="tel" name="telefone" type="tel" autocomplete="tel" placeholder="{phone_ph}" required></div>
    <div class="field"><label for="email">{mail}</label><input id="email" name="email" type="email" autocomplete="email" placeholder="{mail_ph}"></div>
  </div>
  <div class="field"><label for="area">{subject}</label><select id="area" name="area">{opts}</select></div>
  <div class="field"><label for="mensagem">{msg}</label><textarea id="mensagem" name="mensagem" placeholder="{msg_ph}"></textarea></div>
  <div class="form-actions">
    <button type="submit" value="wa" class="btn btn-wa">{waicon} {send_wa}</button>
    <button type="submit" value="email" class="btn btn-ghost">{send_mail}</button>
  </div>
  <div class="form-err" role="alert">{err}</div>
  <div class="form-ok" role="status">{ok}</div>
  <p class="form-note">{note}</p>
</form>""".format(wa=WA, email=EMAIL, endpoint=CFG.get("formulario_endpoint", ""), intro=esc(T[lang]["wa_msg"]),
                  labels=esc("|".join(f["labels"])), title=title, sub=sub, name=f["name"], name_ph=f["name_ph"],
                  phone=f["phone"], phone_ph=f["phone_ph"], mail=f["mail"], mail_ph=f["mail_ph"], subject=f["subject"],
                  opts=opts, msg=f["msg"], msg_ph=f["msg_ph"], waicon=WA_ICON, send_wa=f["send_wa"],
                  send_mail=f["send_mail"], err=f["err"], ok=f["ok"], note=f["note"])


def sidebar(lang, path, heading, links):
    c = T[lang]["common"]
    return """<aside class="sidebar">
  <div class="side-card">
    <h3>%s</h3>
    <p>%s</p>
    <a href="%s" class="btn btn-wa btn-block" target="_blank" rel="noopener">%s</a>
    <a href="tel:%s" class="btn btn-gold btn-block">%s %s</a>
  </div>
  <div class="side-list"><h4>%s</h4>%s</div>
</aside>""" % (c["help_title"], c["help_text"], wa_link(lang), T[lang]["nav"]["wa"], TEL, c["call"], TEL_FMT, heading,
               "".join('<a href="%s">%s</a>' % (h, esc(t)) for t, h in links))


def ld(obj):
    return '<script type="application/ld+json">%s</script>\n' % json.dumps(obj, ensure_ascii=False)


# -------------------------------------------------------------------- páginas
def build_home(lang):
    path = STATIC["home"][lang]
    h = T[lang]["home"]
    c = T[lang]["common"]
    u = lambda k: url(k, lang, path)
    img = lambda n: rel(path, "assets/img/" + n)
    stats = "".join('<div><b data-count="%s" data-prefix="%s" data-suffix="%s">%s%s%s</b><span>%s</span></div>' % (
        s[0], s[1], s[2], s[1], s[0], s[2], s[3]) for s in h["stats"])
    diffs = "".join('<div class="diff" data-reveal><div class="ic">%s</div><h3>%s</h3><p>%s</p></div>' % (icon(d[0]), d[1], d[2])
                    for d in h["diffs"])
    groups = ""
    for g in AREAS:
        cards = "".join(area_card(it, lang, path, tag=False) for it in g["itens"] if it.get("home"))
        n = sum(1 for it in g["itens"] if it.get("home"))
        groups += """<div class="area-group">
      <div class="group-head" data-reveal><h3>%s</h3><p>%s</p></div>
      <div class="areas-grid%s">%s</div>
    </div>""" % (esc(g[lang]), esc(g[lang + "_d"]), " cols3" if n % 3 == 0 else "", cards)
    steps = "".join('<li data-reveal><span class="num">%02d</span><h3>%s</h3><p>%s</p></li>' % (i + 1, s[0], s[1])
                    for i, s in enumerate(h["steps"]))
    posts = "".join(post_card(d, lang, path) for d in articles(lang)[:3])
    body = """<section class="hero">
  <div class="wrap">
    <div class="hero-text">
      <span class="kicker">{kicker}</span>
      <h1>{h1}</h1>
      <p class="lead">{lead}</p>
      <div class="hero-langs"><span>Português</span><span>English</span></div>
      <div class="hero-cta">
        <a href="{contato}" class="btn btn-gold">{cta1}</a>
        <a href="{wa}" class="btn btn-wa" target="_blank" rel="noopener">{waicon} {cta2}</a>
      </div>
      <div class="hero-trust">{stats}</div>
    </div>
    <div class="hero-photo">
      <div class="frame"><img src="{photo}" alt="{photo_alt}" width="800" height="966" fetchpriority="high"></div>
      <div class="hero-badge"><b>{badge_b}</b><span>{badge_s}</span><small>Rio de Janeiro · São Paulo</small></div>
    </div>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head" data-reveal><span class="kicker">{d_k}</span><h2>{d_t}</h2></div>
    <div class="diff-grid">{diffs}</div>
  </div>
</section>

<section class="sec bg-cream" id="areas">
  <div class="wrap">
    <div class="sec-head" data-reveal><span class="kicker">{a_k}</span><h2>{a_t}</h2><p class="lead" style="margin:14px auto 0">{a_l}</p></div>
    {groups}
    <div class="center" style="margin-top:40px"><a href="{areas}" class="btn btn-dark">{a_all}</a></div>
  </div>
</section>

<section class="sec bg-navy">
  <div class="wrap split">
    <div class="img-reveal" data-reveal><img src="{office}" alt="{office_alt}" width="1200" height="800" loading="lazy"></div>
    <div data-reveal>
      <span class="kicker light">{w_k}</span>
      <h2>{w_t}</h2>
      {why}
      <a href="{sobre}" class="btn btn-gold" style="margin-top:10px">{w_btn}</a>
    </div>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="sec-head" data-reveal><span class="kicker">{s_k}</span><h2>{s_t}</h2></div>
    <ol class="steps">{steps}</ol>
  </div>
</section>

<section class="sec bg-cream">
  <div class="wrap">
    <div class="sec-head" data-reveal><span class="kicker">{p_k}</span><h2>{p_t}</h2></div>
    <div class="post-grid">{posts}</div>
    <div class="center" style="margin-top:40px"><a href="{artigos}" class="btn btn-ghost">{p_all}</a></div>
  </div>
</section>

<section class="sec" id="consulta">
  <div class="wrap urgent">
    <div data-reveal>
      <span class="kicker">{f_k}</span>
      <h2>{f_t}</h2>
      <p class="lead">{f_l}</p>
      {f_list}
    </div>
    <div data-reveal>{form}</div>
  </div>
</section>
""".format(kicker=h["kicker"], h1=h["h1"], lead=h["lead"], contato=u("contato"), cta1=h["cta1"], wa=wa_link(lang),
           waicon=WA_ICON, cta2=T[lang]["nav"]["wa"], stats=stats, photo=img("marcelo.jpg"), photo_alt=h["photo_alt"],
           badge_b=h["badge"][0], badge_s=h["badge"][1], d_k=h["diff_kicker"], d_t=h["diff_title"], diffs=diffs,
           a_k=h["areas_kicker"], a_t=h["areas_title"], a_l=h["areas_lead"], groups=groups, areas=u("areas"),
           a_all=h["areas_all"], office=img("office.jpg"), office_alt=h["office_alt"], w_k=h["why_kicker"],
           w_t=h["why_title"], why=checklist(h["why"]), sobre=u("sobre"), w_btn=h["why_btn"], s_k=h["steps_kicker"],
           s_t=h["steps_title"], steps=steps, p_k=h["posts_kicker"], p_t=h["posts_title"], posts=posts,
           artigos=u("artigos"), p_all=h["posts_all"], f_k=h["form_kicker"], f_t=h["form_title"], f_l=h["form_lead"],
           f_list=checklist(h["form_list"], "lock"), form=form(lang, h["form_card"][0], h["form_card"][1]))
    body += cta_band(lang, path, h["cta_title"], h["cta_text"])
    schema = ld({"@context": "https://schema.org", "@type": "LegalService", "name": "MSPADV — Marcelo Paiva Advocacia",
                 "description": h["desc"], "areaServed": ["Rio de Janeiro", "São Paulo"], "telephone": TEL,
                 "email": EMAIL, "url": absurl(path), "knowsLanguage": ["pt", "en"],
                 "image": absurl("assets/img/hero.jpg")})
    page(lang, path, "home", h["title"], h["desc"], body, schema)


def build_sobre(lang):
    path = STATIC["sobre"][lang]
    s = T[lang]["sobre"]
    img = lambda n: rel(path, "assets/img/" + n)
    stats = "".join('<div class="stat"><b data-count="%s" data-prefix="%s" data-suffix="%s">%s%s%s</b><span>%s</span></div>' % (
        x[0], x[1], x[2], x[1], x[0], x[2], x[3]) for x in s["stats"])
    cards = "".join('<div class="area-card" data-reveal><div class="ic">%s</div><h3>%s</h3><p>%s</p></div>' % (icon(x[0]), x[1], x[2])
                    for x in s["cards"])
    body = page_hero(lang, path, [(T[lang]["nav"]["sobre"], None)], s["h1"], s["lead"]) + """
<section class="sec">
  <div class="wrap bio">
    <div class="bio-photo" data-reveal>
      <div class="frame"><img src="{photo}" alt="{alt}" width="800" height="966"></div>
      <div class="badge"><b>{badge_b}</b><span>{badge_s}</span></div>
    </div>
    <div data-reveal>
      <span class="kicker">Marcelo Paiva Advocacia</span>
      <h2>{h2}</h2>
      {paras}
      <div class="stat-row">{stats}</div>
    </div>
  </div>
</section>

<section class="sec bg-cream">
  <div class="wrap">
    <div class="sec-head" data-reveal><span class="kicker">{c_k}</span><h2>{c_t}</h2></div>
    <div class="areas-grid cols3">{cards}</div>
  </div>
</section>

<section class="sec bg-navy">
  <div class="wrap split">
    <div data-reveal>
      <span class="kicker light">{v_k}</span>
      <h2>{v_t}</h2>
      {values}
    </div>
    <div class="img-reveal" data-reveal><img src="{office}" alt="{office_alt}" width="1200" height="800" loading="lazy"></div>
  </div>
</section>
""".format(photo=img("marcelo.jpg"), alt=s["photo_alt"], badge_b=s["badge"][0], badge_s=s["badge"][1], h2=s["h2"],
           paras="".join("<p>%s</p>" % p for p in s["paras"]), stats=stats, c_k=s["cards_kicker"], c_t=s["cards_title"],
           cards=cards, v_k=s["values_kicker"], v_t=s["values_title"], values=checklist(s["values"]),
           office=img("office.jpg"), office_alt=s["office_alt"])
    body += cta_band(lang, path, s["cta_title"], s["cta_text"])
    page(lang, path, "sobre", s["title"], s["desc"], body)


def build_areas_index(lang):
    path = STATIC["areas"][lang]
    a = T[lang]["areas"]
    body = page_hero(lang, path, [(T[lang]["nav"]["areas"], None)], a["h1"], a["lead"])
    for i, g in enumerate(AREAS):
        n = len(g["itens"])
        body += """<section class="sec%s" id="%s">
  <div class="wrap">
    <div class="sec-head left" data-reveal><span class="kicker">%s</span><h2>%s</h2><p class="lead" style="margin-top:14px">%s</p></div>
    <div class="areas-grid%s">%s</div>
  </div>
</section>
""" % (" bg-cream" if i % 2 else "", g["id"], "%02d" % (i + 1), esc(g[lang]), esc(g[lang + "_d"]),
       " cols3" if n % 3 == 0 else "", "".join(area_card(it, lang, path) for it in g["itens"]))
    body += cta_band(lang, path, a["cta_title"], a["cta_text"])
    page(lang, path, "areas", a["title"], a["desc"], body)


def build_area(doc):
    lang, path, key, m = doc["lang"], doc["path"], doc["key"], doc["meta"]
    c = T[lang]["common"]
    text, svc, faq = split_area(doc["body"])
    group = next(g for g, it in area_items() if it.get("key") == key)
    short = next(it for g, it in area_items() if it.get("key") == key)[lang][0]
    related = [(it[lang][0], url(it["key"], lang, path)) for it in group["itens"] if it.get("key") and it["key"] != key][:6]
    svc_html = ""
    if svc:
        svc_html = '<h2>%s</h2><div class="svc-grid">%s</div>' % (
            c["services"], "".join('<div class="svc"><b>%s</b><span>%s</span></div>' % (inline(a, lang, path), inline(b, lang, path)) for a, b in svc))
    body = page_hero(lang, path, [(T[lang]["nav"]["areas"], "areas"), (short, None)], esc(m["title"]), esc(m.get("lead", "")), esc(group[lang]))
    body += """<section class="sec">
  <div class="wrap layout">
    <div class="prose" data-reveal>
%s
%s
    </div>
    %s
  </div>
</section>
""" % (md(text, lang, path), svc_html, sidebar(lang, path, c["related_areas"], related))
    if faq:
        items = "".join("""<div class="faq-item">
      <button class="faq-q" aria-expanded="false">%s<span class="pm"></span></button>
      <div class="faq-a"><p>%s</p></div>
    </div>""" % (esc(q), inline(a, lang, path)) for q, a in faq)
        body += """<section class="sec bg-cream">
  <div class="wrap">
    <div class="sec-head" data-reveal><span class="kicker">%s</span><h2>%s %s</h2></div>
    <div class="faq" data-reveal>%s</div>
  </div>
</section>
""" % (c["faq_kicker"], c["faq_title"], esc(short), items)
    body += cta_band(lang, path, esc(m.get("cta", c["cta_default"])), c["cta_text"])
    schema = ""
    if faq:
        schema = ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>|\*\*", "", a)}} for q, a in faq]})
    page(lang, path, key, m.get("titulo_seo", m["title"] + " | MSPADV"), m.get("descricao", m.get("lead", "")), body, schema)


def build_articles_index(lang):
    path = STATIC["artigos"][lang]
    a = T[lang]["artigos"]
    posts = "".join(post_card(d, lang, path) for d in articles(lang))
    body = page_hero(lang, path, [(T[lang]["nav"]["artigos"], None)], a["h1"], a["lead"]) + """<section class="sec">
  <div class="wrap"><div class="post-grid">%s</div></div>
</section>
""" % posts
    body += cta_band(lang, path, a["cta_title"], a["cta_text"])
    page(lang, path, "artigos", a["title"], a["desc"], body)


def build_article(doc):
    lang, path, key, m = doc["lang"], doc["path"], doc["key"], doc["meta"]
    c = T[lang]["common"]
    others = [(d["meta"]["title"], rel(path, d["path"])) for d in articles(lang) if d["key"] != key][:5]
    cat = m.get("categoria", "")
    body = page_hero(lang, path, [(T[lang]["nav"]["artigos"], "artigos"), (cat, None)], esc(m["title"]), esc(m.get("resumo", "")))
    body += """<section class="sec">
  <div class="wrap layout">
    <article class="prose" data-reveal>
      <p class="post-meta">%s &middot; <time datetime="%s">%s</time></p>
%s
      <div class="callout notice"><p>%s</p></div>
    </article>
    %s
  </div>
</section>
""" % (esc(cat), m["data"], fmt_date(m["data"], lang), md(doc["body"], lang, path), c["notice"],
       sidebar(lang, path, c["other_articles"], others))
    body += cta_band(lang, path, T[lang]["artigos"]["post_cta"], T[lang]["artigos"]["cta_text"])
    schema = ld({"@context": "https://schema.org", "@type": "Article", "headline": m["title"],
                 "description": m.get("resumo", ""), "datePublished": m["data"], "inLanguage": T[lang]["lang"],
                 "author": {"@type": "Organization", "name": "MSPADV — Marcelo Paiva Advocacia"},
                 "mainEntityOfPage": absurl(path)})
    page(lang, path, key, m["title"] + " | MSPADV", m.get("resumo", ""), body, schema)


def build_contact(lang):
    path = STATIC["contato"][lang]
    ct = T[lang]["contato"]
    rows = [("whatsapp", ct["l_wa"], '<a href="%s" target="_blank" rel="noopener">%s</a>' % (wa_link(lang), TEL_FMT)),
            ("phone", ct["l_tel"], '<a href="tel:%s">%s</a>' % (TEL, TEL_FMT)),
            ("mail", ct["l_mail"], '<a href="mailto:%s">%s</a>' % (EMAIL, EMAIL)),
            ("pin", ct["l_place"], "<span>%s</span>" % ct["place"]),
            ("clock", ct["l_hours"], "<span>%s</span>" % ct["hours"])]
    info = "".join('<div class="ci" data-reveal><div class="ic">%s</div><div><b>%s</b>%s</div></div>' % (icon(i), l, v) for i, l, v in rows)
    body = page_hero(lang, path, [(T[lang]["nav"]["contato"], None)], ct["h1"], ct["lead"]) + """<section class="sec">
  <div class="wrap contact-grid">
    <div class="contact-info">
      <span class="kicker">%s</span>
      <h2 style="margin-bottom:32px">%s</h2>
      %s
      <a href="%s" class="btn btn-wa" target="_blank" rel="noopener">%s %s</a>
    </div>
    <div data-reveal>%s</div>
  </div>
</section>
""" % (ct["kicker"], ct["h2"], info, wa_link(lang), WA_ICON, ct["wa_now"], form(lang, ct["form_card"][0], ct["form_card"][1]))
    page(lang, path, "contato", ct["title"], ct["desc"], body)


def build_simple(doc):
    lang, path, key, m = doc["lang"], doc["path"], doc["key"], doc["meta"]
    body = page_hero(lang, path, [(m["title"], None)], esc(m["title"]), esc(m.get("lead", ""))) + """<section class="sec">
  <div class="wrap"><div class="prose" style="max-width:820px" data-reveal>
%s
  </div></div>
</section>
""" % md(doc["body"], lang, path)
    page(lang, path, key, m["title"] + " | MSPADV", m.get("lead", ""), body)


def build_404():
    e = T["pt"]["e404"]
    path = "404.html"
    body = """<section class="page-hero" style="min-height:60vh;display:flex;align-items:center">
  <div class="wrap">
    <span class="kicker">404</span>
    <h1>%s</h1>
    <p class="lead">%s</p>
    <div class="hero-cta" style="margin-top:28px">
      <a class="btn btn-gold" href="%s">%s</a>
      <a class="btn btn-ghost" href="%s">Go to the English site</a>
    </div>
  </div>
</section>
""" % (e["h1"], e["lead"], BASE_PATH, e["btn"], BASE_PATH + "en/")
    doc = head("pt", None, "404", e["h1"] + " | MSPADV", e["lead"]) + header("pt", None, "404") + body + footer("pt", None)
    doc = doc.replace('<meta name="robots" content="index, follow">', '<meta name="robots" content="noindex">')
    with open(os.path.join(OUT, path), "w", encoding="utf-8") as f:
        f.write(doc)


def build_meta():
    today = datetime.date.today().isoformat()
    urls = ""
    for path, key, lang in sorted(BUILT):
        pr = "1.0" if key == "home" else ("0.9" if key in DOCS["areas"] else "0.7")
        urls += "  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>\n" % (absurl(path), today, pr)
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % urls)
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n" + ("\nSitemap: %s/sitemap.xml\n" % SITE_URL if SITE_URL else ""))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    if CFG.get("dominio"):
        with open(os.path.join(OUT, "CNAME"), "w") as f:
            f.write(CFG["dominio"].strip() + "\n")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
    scan()
    for key in [it["key"] for g, it in area_items() if it.get("key")]:
        for lang in LANGS:
            if lang not in DOCS["areas"].get(key, {}):
                sys.exit("ERRO: falta o arquivo content/%s/areas/%s.md (citado em content/areas.json)" % (lang, key))
    for lang in LANGS:
        build_home(lang)
        build_sobre(lang)
        build_areas_index(lang)
        build_articles_index(lang)
        build_contact(lang)
    for kind, fn in (("areas", build_area), ("artigos", build_article), ("paginas", build_simple)):
        for versions in DOCS[kind].values():
            for doc in versions.values():
                fn(doc)
    build_404()
    build_meta()
    print("Site gerado em _site/ — %d páginas (%s)" % (len(BUILT) + 1, SITE_URL or "sem URL definida"))
    if "--serve" in sys.argv:
        import functools
        import http.server
        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=OUT)
        print("Abra http://localhost:8000  (Ctrl+C para encerrar)")
        http.server.ThreadingHTTPServer(("", 8000), h).serve_forever()


if __name__ == "__main__":
    main()
