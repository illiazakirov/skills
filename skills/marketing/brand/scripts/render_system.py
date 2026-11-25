#!/usr/bin/env python3
"""Render the pages of a design system from its tokens, its copy and the identity.

    render_system.py sheet <tokens.json> <output.html> --brand <brand/>
    render_system.py build <brand/>

The skill ships the components (templates/system/system.css) and the fixed
compositions they are shown in; a brand gives only its tokens, its copy
(04-design-system/copy.json), its logo and its fonts. So a variant of the
Interface choice is a candidate tokens.json rendered as the sheet, and the
finished system is the same pages rendered from the fixed tokens.json.

sheet   one variant of the Interface choice: buttons with their states, a
        field with help and with an error, a card, the choices and a notice.
        The tokens and the components are inlined; nothing else is written.
build   04-design-system/reference/: index.html (the whole system on one
        page, every block numbered for corrections), sheet.html, system.css,
        and pages/landing.html, pages/sign-in.html, pages/sign-up.html. These
        load ../tokens.css and the identity's fonts/fonts.css by relative path.

Every page has a light and a dark theme through data-theme on <html>, follows
the reader's setting until it is switched, carries the theme listener of
reference/choice-page.md, and works at 1440 and at 390. The format of copy.json is
in reference/system.md. No dependencies beyond the Python 3 standard library.

Exit codes: 0 rendered, 1 the tokens or the copy break a rule (nothing is
written), 2 a file cannot be read.
"""

import argparse
import html
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_tokens as bt  # noqa: E402
import check_contract as cc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, os.pardir, "templates", "system")
DESIGN = "04-design-system"
IDENTITY = "03-identity"

ICONS = ("arrow-right", "check", "x", "info", "circle-check", "triangle-alert", "circle-alert",
         "mail", "lock", "user", "menu", "chevron-down", "star", "quote", "eye", "sun", "moon",
         "search", "log-in", "sparkles")
NOTICE_ICONS = {"info": "info", "success": "circle-check", "warning": "triangle-alert",
                "error": "circle-alert"}
BENEFIT_ICONS = ("sparkles", "star", "check")

S = "text"
COPY = {
    "lang": S,
    "nav": [S, S, S],
    "header_button": S,
    "hero": {"headline": S, "lead": S, "button": S, "secondary": S},
    "benefits": {"title": S, "items": [{"title": S, "text": S}] * 3},
    "testimonial": {"quote": S, "name": S, "role": S},
    "call": {"headline": S, "text": S, "button": S},
    "footer": {"text": S, "links": [S, S, S]},
    "sign_in": {"title": S, "email": S, "password": S, "button": S, "switch": S,
                "switch_link": S},
    "sign_up": {"title": S, "name": S, "email": S, "password": S, "terms": S, "button": S,
                "error": S, "switch": S, "switch_link": S},
    "ui": {"placeholder": S, "help": S, "select": S, "options": [S, S, S], "checkbox": S, "radios": [S, S],
           "switch": S, "badge": S,
           "notices": {"info": S, "success": S, "warning": S, "error": S},
           "card": {"title": S, "text": S}},
}

THEME_SCRIPT = ("<script>(function(){var r=document.documentElement;"
                "if(!r.dataset.theme)r.dataset.theme=matchMedia('(prefers-color-scheme: dark)')"
                ".matches?'dark':'light';addEventListener('message',function(e){if(e.data&&"
                "e.data.brandTheme)r.dataset.theme=e.data.brandTheme})})()</script>")
SWITCH_SCRIPT = ("<script>document.querySelector('.theme-switch').addEventListener('click',"
                 "function(){var r=document.documentElement;r.dataset.theme=r.dataset.theme==="
                 "'dark'?'light':'dark'})</script>")


class Problem(Exception):
    """The tokens or the copy break a rule."""


# --- Reading -------------------------------------------------------------------


def check_copy(schema, data, where="copy.json"):
    if schema == S:
        if not isinstance(data, str) or not data.strip():
            raise Problem("%s must be a text that is not empty" % where)
        return
    if isinstance(schema, list):
        if not isinstance(data, list) or len(data) != len(schema):
            raise Problem("%s must be a list of %d" % (where, len(schema)))
        for index, (item_schema, item) in enumerate(zip(schema, data)):
            check_copy(item_schema, item, "%s[%d]" % (where, index))
        return
    if not isinstance(data, dict):
        raise Problem("%s must be an object" % where)
    for key in data:
        if key not in schema:
            raise Problem("unknown key '%s' in %s" % (key, where))
    for key, item_schema in schema.items():
        if key not in data:
            raise Problem("missing key '%s' in %s" % (key, where))
        check_copy(item_schema, data[key], "%s.%s" % (where, key))


def read_copy(brand):
    path = os.path.join(brand, DESIGN, "copy.json")
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise OSError("cannot read %s: %s" % (path, error))
    check_copy(COPY, data)
    return data


def read_tokens(path):
    """Return (tokens, the text of tokens.css). Raise Problem when they break a rule."""
    try:
        tokens, data, problems = cc.load_tokens(path)
    except (OSError, ValueError) as error:
        raise OSError("cannot read %s: %s" % (path, error))
    problems = problems or cc.missing_tokens(tokens)
    if not problems:
        try:
            problems = cc.weak_tokens(tokens)
        except (KeyError, ValueError) as error:
            problems = [str(error)]
    if not problems:
        try:
            return tokens, bt.build(data)
        except bt.Problem as error:
            problems = error.args[0]
    raise Problem("; ".join(problems))


def icon(name, label=None):
    with open(os.path.join(TEMPLATES, "icons", name + ".svg"), encoding="utf-8") as handle:
        svg = handle.read()
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
    svg = re.sub(r'\s(class|width|height|stroke-width)="[^"]*"', "", svg)
    hidden = ' role="img" aria-label="%s"' % e(label) if label else ' aria-hidden="true"'
    return re.sub(r"\s+", " ", svg.replace("<svg", '<svg class="icon"%s' % hidden, 1))


def e(text):
    return html.escape(text, quote=True)


def rel(path, start):
    return os.path.relpath(path, start).replace(os.sep, "/")


# --- Pieces ---------------------------------------------------------------------


def brand_mark(look):
    if look["logo"]:
        return ('<a class="brand" href="#"><img class="logo-light" src="%s" alt="%s">'
                '<img class="logo-dark" src="%s" alt="%s"></a>'
                % (e(look["logo"]), e(look["name"]), e(look["logo_dark"]), e(look["name"])))
    return '<a class="brand" href="#">%s</a>' % e(look["name"])


def header(c, look):
    links = "".join('<li><a href="#">%s</a></li>' % e(item) for item in c["nav"])
    return ('<header class="site-header"><div class="container">%s'
            '<nav class="site-nav" aria-label="Main"><ul>%s</ul>'
            '<a class="button button-primary" href="#">%s</a></nav>'
            '<details class="menu"><summary class="button button-quiet" aria-label="Menu">%s'
            '</summary><ul>%s<li><a href="#">%s</a></li></ul></details></div></header>'
            % (brand_mark(look), links, e(c["header_button"]), icon("menu"), links,
               e(c["header_button"])))


def hero(c):
    h = c["hero"]
    return ('<section class="hero"><div class="container"><h1 class="t-headline">%s</h1>'
            '<p class="t-lead">%s</p><div class="actions">'
            '<a class="button button-primary" href="#">%s %s</a>'
            '<a class="button" href="#">%s</a></div></div></section>'
            % (e(h["headline"]), e(h["lead"]), e(h["button"]), icon("arrow-right"),
               e(h["secondary"])))


def benefits(c):
    b = c["benefits"]
    items = "".join('<li>%s<h3 class="t-subtitle">%s</h3><p class="muted">%s</p></li>'
                    % (icon(name), e(item["title"]), e(item["text"]))
                    for name, item in zip(BENEFIT_ICONS, b["items"]))
    return ('<section class="benefits"><div class="container"><h2 class="t-title">%s</h2>'
            "<ul>%s</ul></div></section>" % (e(b["title"]), items))


def initials(name):
    return "".join(word[0] for word in name.split()[:2]).upper()


def testimonial(c):
    t = c["testimonial"]
    return ('<section class="testimonial"><div class="container"><figure>'
            '<blockquote class="t-title">%s</blockquote><figcaption>'
            '<span class="avatar">%s</span><span><b>%s</b><br><span class="t-small muted">%s'
            "</span></span></figcaption></figure></div></section>"
            % (e(t["quote"]), e(initials(t["name"])), e(t["name"]), e(t["role"])))


def call(c):
    k = c["call"]
    return ('<section class="cta"><div class="container"><h2 class="t-title">%s</h2>'
            '<p class="t-lead">%s</p><div class="actions">'
            '<a class="button button-primary" href="#">%s</a></div></div></section>'
            % (e(k["headline"]), e(k["text"]), e(k["button"])))


def footer(c, look):
    links = "".join('<li><a href="#">%s</a></li>' % e(item) for item in c["footer"]["links"])
    return ('<footer class="site-footer"><div class="container"><p>%s · %s</p><ul>%s</ul>'
            "</div></footer>" % (e(look["name"]), e(c["footer"]["text"]), links))


def field(label, kind, name, c, help_text=None, error=None, value=""):
    ident = "f-" + name
    described = ""
    extra = ""
    if help_text:
        extra += '<span class="help" id="%s-help">%s</span>' % (ident, e(help_text))
        described = ' aria-describedby="%s-help"' % ident
    if error:
        extra += ('<span class="error-text" id="%s-error">%s%s</span>'
                  % (ident, icon("circle-alert"), e(error)))
        described = ' aria-describedby="%s-error" aria-invalid="true"' % ident
    placeholder = ' placeholder="%s"' % e(c["ui"]["placeholder"]) if kind == "email" else ""
    return ('<div class="field"><label class="label" for="%s">%s</label>'
            '<input class="input" id="%s" type="%s"%s%s value="%s">%s</div>'
            % (ident, e(label), ident, kind, placeholder, described, e(value), extra))


def sign_in_form(c):
    s = c["sign_in"]
    return ('<div class="card"><h1 class="t-title">%s</h1><form action="#">%s%s'
            '<button class="button button-primary" type="submit">%s</button></form>'
            '<p class="switch-line t-small muted">%s <a href="#">%s</a></p></div>'
            % (e(s["title"]), field(s["email"], "email", "in-email", c),
               field(s["password"], "password", "in-password", c),
               e(s["button"]), e(s["switch"]), e(s["switch_link"])))


def sign_up_form(c):
    s = c["sign_up"]
    return ('<div class="card"><h1 class="t-title">%s</h1><form action="#">%s%s%s'
            '<label class="check"><input type="checkbox"> %s</label>'
            '<button class="button button-primary" type="submit">%s</button></form>'
            '<p class="switch-line t-small muted">%s <a href="#">%s</a></p></div>'
            % (e(s["title"]), field(s["name"], "text", "up-name", c),
               field(s["email"], "email", "up-email", c, error=s["error"],
                     value=c["ui"]["placeholder"]),
               field(s["password"], "password", "up-password", c),
               e(s["terms"]), e(s["button"]), e(s["switch"]), e(s["switch_link"])))


def buttons(c):
    label = c["hero"]["button"]
    rows = []
    for kind, name in (("button-primary", "Primary"), ("", "Secondary"),
                       ("button-quiet", "Quiet")):
        cells = "".join('<button class="button %s%s" type="button"%s>%s</button>'
                        % (kind, state, " disabled" if state == " is-disabled" else "", e(label))
                        for state in ("", " is-hover", " is-focus", " is-active", " is-disabled"))
        rows.append('<div class="row"><span class="t-label muted">%s</span>%s</div>' % (name, cells))
    return ('<p class="t-small muted">default, hover, focus, active, disabled</p>%s'
            % "".join(rows))


def notices(c):
    return "".join('<div class="notice notice-%s" role="%s">%s<span>%s</span></div>'
                   % (kind, "alert" if kind == "error" else "status", icon(NOTICE_ICONS[kind]),
                      e(c["ui"]["notices"][kind]))
                   for kind in ("info", "success", "warning", "error"))


def card(c):
    u = c["ui"]
    return ('<div class="card"><span class="badge badge-accent">%s</span>'
            '<h3 class="t-subtitle">%s</h3><p class="muted">%s</p>'
            '<a class="button" href="#">%s %s</a></div>'
            % (e(u["badge"]), e(u["card"]["title"]), e(u["card"]["text"]),
               e(c["hero"]["button"]), icon("arrow-right")))


def choices(c):
    u = c["ui"]
    radios = "".join('<label class="check"><input type="radio" name="period"%s> %s</label>'
                     % (" checked" if i == 0 else "", e(text)) for i, text in enumerate(u["radios"]))
    return ('<label class="check"><input type="checkbox" checked> %s</label>'
            '<label class="check"><input type="checkbox"> %s</label>%s'
            '<label class="check"><input type="checkbox" role="switch" class="switch" checked> %s'
            "</label>" % (e(u["checkbox"]), e(u["checkbox"]), radios, e(u["switch"])))


def select(c, ident="f-select"):
    options = "".join("<option>%s</option>" % e(o) for o in c["ui"]["options"])
    return ('<div class="select-wrap"><select class="select" id="%s">%s</select>%s</div>'
            % (ident, options, icon("chevron-down")))


# --- Pages ------------------------------------------------------------------------


CHROME = """
.sheet,.doc{padding:var(--space-xl) var(--layout-gutter)}
.sheet{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:var(--space-xl);max-width:calc(var(--layout-content) + 2 * var(--layout-gutter));margin:0 auto}
.sheet>section,.block .demo{display:grid;gap:var(--space-m);align-content:start}
.row{display:flex;flex-wrap:wrap;align-items:center;gap:var(--space-s)}
.row>.t-label{flex-basis:100%}
.doc{max-width:calc(var(--layout-content) + 2 * var(--layout-gutter));margin:0 auto}
.doc-bar{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:var(--space-m);padding:var(--space-s) var(--layout-gutter);background:var(--color-bg);border-bottom:var(--border-width) solid var(--color-border)}
.doc-bar .brand img{height:calc(var(--size-control) * .5)}
.doc h2.part{margin:var(--space-section) 0 var(--space-l)}
.doc h2.part:first-child{margin-top:var(--space-l)}
.block{scroll-margin-top:calc(var(--size-control) + 2 * var(--space-s));display:grid;grid-template-columns:minmax(160px,220px) 1fr;gap:var(--space-l);padding:var(--space-xl) 0;border-top:var(--border-width) solid var(--color-border)}
.block>header{display:grid;gap:var(--space-xs);align-content:start}
.num{display:inline-flex;align-items:center;justify-content:center;width:var(--size-control);height:var(--size-control);border-radius:var(--radius-badge);background:var(--color-surface);border:var(--border-width) solid var(--color-border);font-family:var(--type-label-font-family);font-size:var(--type-label-font-size);font-weight:var(--type-label-font-weight)}
.wide{grid-column:1/-1}
.swatches{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:var(--space-m)}
.swatches i{display:block;height:calc(var(--size-control) * 1.5);border-radius:var(--radius-card);border:var(--border-width) solid var(--color-border);margin-bottom:var(--space-xs)}
.swatches code,.specs code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:var(--type-small-font-size)}
.specs{display:grid;gap:var(--space-xs)}
.specs td,.specs th{text-align:left;padding:var(--space-xs) var(--space-m) var(--space-xs) 0;border-bottom:var(--border-width) solid var(--color-border);vertical-align:top}
table.specs{border-collapse:collapse;width:100%}
.fail{color:var(--color-error)}
.bar{height:var(--space-m);background:var(--color-accent);border-radius:var(--space-xs)}
.shape{width:calc(var(--size-control) * 2.5);height:calc(var(--size-control) * 1.5);background:var(--color-surface);border:var(--border-control) solid var(--color-control-border)}
.icons{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:var(--space-m)}
.icons li{display:grid;justify-items:center;gap:var(--space-xs);padding:var(--space-m) 0}
.frames{display:flex;flex-wrap:wrap;gap:var(--space-l);align-items:flex-start}
.frame{overflow:hidden;border:var(--border-width) solid var(--color-border);border-radius:var(--radius-card);background:var(--color-bg)}
.frame iframe{border:0;transform-origin:0 0;pointer-events:none}
.frame.wide-frame{width:432px;height:270px}.frame.wide-frame iframe{width:1440px;height:900px;transform:scale(.3)}
.frame.narrow-frame{width:195px;height:422px}.frame.narrow-frame iframe{width:390px;height:844px;transform:scale(.5)}
.specimen{display:grid;gap:var(--space-l)}
.specimen>div{display:grid;gap:var(--space-xs)}
@media (max-width:600px){
.block{grid-template-columns:1fr}
.frame.wide-frame{width:100%;max-width:432px}
}
"""


def shell(title, body, look, css_links, inline_css="", lang="en", bar=""):
    links = "".join('<link rel="stylesheet" href="%s">' % e(href) for href in css_links)
    return ("<!doctype html>\n<html lang=\"%s\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title>%s%s<style>%s%s</style></head><body>%s%s</body></html>\n"
            % (e(lang), e(title), THEME_SCRIPT, links, inline_css, CHROME, bar, body))


def sheet_body(c):
    u = c["ui"]
    return ('<div class="sheet"><section><h2 class="t-label muted">Buttons</h2>%s</section>'
            '<section><h2 class="t-label muted">Fields</h2>%s%s<div class="field">'
            '<label class="label" for="f-select">%s</label>%s</div></section>'
            '<section><h2 class="t-label muted">Card</h2>%s</section>'
            '<section><h2 class="t-label muted">Choices</h2>%s</section>'
            '<section><h2 class="t-label muted">Notices</h2>%s</section></div>'
            % (buttons(c), field(c["sign_up"]["email"], "email", "sheet-email", c,
                                 help_text=u["help"]),
               field(c["sign_up"]["email"], "email", "sheet-email-error", c,
                     error=c["sign_up"]["error"], value=u["placeholder"]),
               e(c["ui"]["select"]), select(c), card(c), choices(c), notices(c)))


def number_blocks(blocks):
    """blocks: [(part, [(title, note, html, wide)])] -> the body with numbered blocks."""
    out, number = [], 0
    for part, items in blocks:
        out.append('<h2 class="part t-title" id="%s">%s</h2>' % (e(part.lower()), e(part)))
        for title, note, content, wide in items:
            number += 1
            out.append('<section class="block" id="b%d"><header><span class="num">%d</span>'
                       '<h3 class="t-subtitle">%s</h3><p class="t-small muted">%s</p></header>'
                       '<div class="demo%s">%s</div></section>'
                       % (number, number, e(title), e(note), " wide" if wide else "", content))
    return "".join(out)


def hex_of(tokens, path, dark):
    try:
        return cc.token_hex(tokens, path[1], dark)
    except (KeyError, ValueError):
        return "-"


def describe(tokens, path, narrow=False):
    """A short text for a token's value at a width."""
    try:
        kind, value = cc.resolve(tokens, path, narrow=narrow)
    except KeyError:
        return "-"
    if kind == "dimension" or kind == "duration":
        return bt.num(value["value"]) + value["unit"]
    if kind == "typography":
        size = value["fontSize"]
        if isinstance(size, str):
            size = cc.resolve(tokens, tuple(size.strip("{}").split(".")), narrow=narrow)[1]
        return "%s%s / %s" % (bt.num(size["value"]), size["unit"], bt.num(value["lineHeight"]))
    if kind == "fontFamily":
        return ", ".join(value) if isinstance(value, list) else value
    if kind == "cubicBezier":
        return "cubic-bezier(%s)" % ", ".join(bt.num(v) for v in value)
    return str(value)


def foundations(tokens, c):
    roles = [name for (group, name), kind in cc.REQUIRED_TOKENS.items() if group == "color"]
    swatches = "".join('<li><i style="background:var(--color-%s)"></i><b>%s</b><br>'
                       '<code>%s · %s</code></li>'
                       % (name, e("color." + name), hex_of(tokens, ("color", name), False),
                          hex_of(tokens, ("color", name), True)) for name in roles)
    rows = "".join('<tr%s><td>%s</td><td>%s to 1</td></tr>'
                   % ("" if ratio >= minimum else ' class="fail"', e(text.split(": ")[0]),
                      ("%.1f" % ratio).rstrip("0").rstrip("."))
                   for text, ratio, minimum in cc.token_contrast(tokens))
    samples = {"headline": c["hero"]["headline"], "title": c["benefits"]["title"],
               "subtitle": c["benefits"]["items"][0]["title"], "lead": c["hero"]["lead"],
               "body": c["benefits"]["items"][0]["text"], "small": c["footer"]["text"],
               "label": c["sign_in"]["email"]}
    type_rows = "".join('<div><span class="t-small muted">type.%s · %s at 1440 · %s at 390</span>'
                        '<p class="t-%s">%s</p></div>'
                        % (name, describe(tokens, ("type", name)),
                           describe(tokens, ("type", name), True), name, e(samples[name]))
                        for name in samples)
    fonts = "".join('<p class="t-small muted">font.%s: %s</p>'
                    % (name, e(describe(tokens, ("font", name)))) for name in ("display", "text"))
    spaces = "".join('<div class="row"><span class="t-label muted">space.%s · %s</span>'
                     '<span class="bar" style="width:var(--space-%s)"></span></div>'
                     % (name, describe(tokens, ("space", name)), name)
                     for name in ("xs", "s", "m", "l", "xl", "section"))
    shapes = "".join('<div><div class="shape" style="border-radius:var(--radius-%s)"></div>'
                     '<p class="t-small muted">radius.%s · %s</p></div>'
                     % (name, name, describe(tokens, ("radius", name)))
                     for name in ("control", "card", "badge"))
    borders = "".join('<p class="t-small muted">border.%s · %s</p>'
                      % (name, describe(tokens, ("border", name))) for name in ("width", "control"))
    shadows = "".join('<div><div class="shape" style="border:0;box-shadow:var(--shadow-%s);'
                      'border-radius:var(--radius-card)"></div><p class="t-small muted">'
                      'shadow.%s</p></div>' % (name, name) for name in ("card", "raised"))
    layout = "".join('<p class="t-small muted">%s.%s · %s at 1440 · %s at 390</p>'
                     % (group, name, describe(tokens, (group, name)),
                        describe(tokens, (group, name), True))
                     for group, name in (("layout", "content"), ("layout", "gutter"),
                                         ("size", "control")))
    icons = "".join('<li>%s<span class="t-small muted">%s</span></li>' % (icon(name), name)
                    for name in ICONS)
    return [
        ("Colors", "Every role, light · dark.", '<ul class="swatches">%s</ul>' % swatches, True),
        ("Contrast", "Text 4.5 to 1, borders of controls and focus 3 to 1.",
         '<table class="specs"><tbody>%s</tbody></table>' % rows, False),
        ("Type", "The scale; headline, lead and body are the identity's.",
         '<div class="specimen">%s%s</div>' % (fonts, type_rows), True),
        ("Spacing and layout", "The base unit and its steps.",
         '<div class="specs">%s%s</div>' % (spaces, layout), False),
        ("Radii and borders", "", '<div class="row">%s</div>%s' % (shapes, borders), False),
        ("Shadows", "", '<div class="row">%s</div>' % shadows, False),
        ("Motion", "Every change of state.",
         '<p class="t-small muted">motion.duration · %s · motion.easing · %s</p>'
         '<div class="row"><button class="button button-primary" type="button">%s</button>'
         '<label class="check"><input type="checkbox" role="switch" class="switch"> %s</label>'
         "</div>" % (describe(tokens, ("motion", "duration")),
                     describe(tokens, ("motion", "easing")), e(c["hero"]["button"]),
                     e(c["ui"]["switch"])), False),
        ("Icons", "Lucide, ISC License; icons derived from Feather, MIT License.",
         '<ul class="icons">%s</ul>' % icons, True),
    ]


def frames(name):
    return ('<div class="frames"><div class="frame wide-frame"><iframe src="pages/%s" '
            'title="%s at 1440" loading="lazy"></iframe></div><div class="frame narrow-frame">'
            '<iframe src="pages/%s" title="%s at 390" loading="lazy"></iframe></div></div>'
            '<p><a href="pages/%s">Open at full size</a></p>' % (name, name, name, name, name))


def system_body(tokens, c, look):
    u = c["ui"]
    atoms = [
        ("Button", "Primary, secondary, quiet.", buttons(c), True),
        ("Link", "", '<p>%s <a href="#">%s</a> · <a class="is-hover" href="#">%s</a> · '
                     '<a class="is-focus" href="#">%s</a></p>'
         % (e(c["sign_in"]["switch"]), e(c["sign_in"]["switch_link"]),
            e(c["sign_in"]["switch_link"]), e(c["sign_in"]["switch_link"])), False),
        ("Text input", "default, focus, disabled, error",
         '<input class="input" placeholder="%s"><input class="input is-focus" value="%s">'
         '<input class="input" disabled value="%s"><input class="input" aria-invalid="true" '
         'value="%s">' % (e(u["placeholder"]), e(u["placeholder"]), e(u["placeholder"]),
                          e(u["placeholder"])), False),
        ("Text area", "", '<textarea class="textarea">%s</textarea>' % e(c["hero"]["lead"]), False),
        ("Select", "", select(c, "f-select-atom"), False),
        ("Checkbox", "", '<div class="row"><label class="check"><input type="checkbox"> %s</label>'
                         '<label class="check"><input type="checkbox" checked> %s</label>'
                         '<label class="check"><input type="checkbox" disabled> %s</label></div>'
         % (e(u["checkbox"]), e(u["checkbox"]), e(u["checkbox"])), False),
        ("Radio", "", '<div class="row">%s</div>'
         % "".join('<label class="check"><input type="radio" name="r-atom"%s> %s</label>'
                   % (" checked" if i == 0 else "", e(t)) for i, t in enumerate(u["radios"])),
         False),
        ("Switch", "", '<div class="row"><label class="check"><input type="checkbox" '
                       'role="switch" class="switch"> %s</label><label class="check"><input '
                       'type="checkbox" role="switch" class="switch" checked> %s</label></div>'
         % (e(u["switch"]), e(u["switch"])), False),
        ("Badge", "", '<div class="row"><span class="badge">%s</span>'
                      '<span class="badge badge-accent">%s</span></div>'
         % (e(u["badge"]), e(u["badge"])), False),
        ("Avatar", "", '<div class="row"><span class="avatar">%s</span>'
                       '<span class="avatar avatar-l">%s</span></div>'
         % (e(initials(c["testimonial"]["name"])), e(initials(c["testimonial"]["name"]))), False),
        ("Divider", "", '<hr class="divider">', False),
    ]
    molecules = [
        ("Form field", "Label, input, help; and with an error.",
         '<div class="row" style="align-items:flex-start">%s%s</div>'
         % (field(c["sign_up"]["email"], "email", "m-email", c, help_text=u["help"]),
            field(c["sign_up"]["email"], "email", "m-email-error", c, error=c["sign_up"]["error"],
                  value=u["placeholder"])), False),
        ("Notice", "info, success, warning, error", notices(c), False),
        ("Card", "", card(c), False),
    ]
    organisms = [
        ("Header", "At 390 the navigation folds into a menu.", header(c, look), True),
        ("Hero", "", hero(c), True),
        ("Benefits", "", benefits(c), True),
        ("Testimonial", "", testimonial(c), True),
        ("Call to action", "", call(c), True),
        ("Sign-in form", "", '<div class="auth">%s</div>' % sign_in_form(c), True),
        ("Footer", "", footer(c, look), True),
    ]
    pages = [(title, "An example of assembly, not the design of a site.", frames(name), True)
             for title, name in (("Landing", "landing.html"), ("Sign-in", "sign-in.html"),
                                 ("Sign-up", "sign-up.html"))]
    return number_blocks([("Foundations", foundations(tokens, c)), ("Atoms", atoms),
                          ("Molecules", molecules), ("Organisms", organisms), ("Pages", pages)])


def page_bodies(c, look):
    return {
        "landing.html": (c["hero"]["headline"], header(c, look) + "<main>" + hero(c)
                         + benefits(c) + testimonial(c) + call(c) + "</main>" + footer(c, look)),
        "sign-in.html": (c["sign_in"]["title"], header(c, look) + '<main class="auth">'
                         + sign_in_form(c) + "</main>" + footer(c, look)),
        "sign-up.html": (c["sign_up"]["title"], header(c, look) + '<main class="auth">'
                         + sign_up_form(c) + "</main>" + footer(c, look)),
    }


# --- Commands -------------------------------------------------------------------


def brand_name(brand):
    for step, name, slot in (("02-brand-platform", "name.md", "Name"),
                             ("00-intake", "brief.md", "Brand")):
        plate = cc.read_plate(brand, step, name) if os.path.isfile(
            os.path.join(brand, step, name)) else None
        if plate and plate[1].get(slot):
            return plate[1][slot][0].strip()
    return "Brand"


def identity_look(brand, page_dir):
    """The brand's name, logo and fonts as seen from page_dir."""
    base = os.path.join(brand, IDENTITY)
    logo = os.path.join(base, "logo", "full.svg")
    dark = os.path.join(base, "logo", "dark.svg")
    fonts = os.path.join(base, "fonts", "fonts.css")
    has_logo = os.path.isfile(logo)
    return {"name": brand_name(brand),
            "logo": rel(logo, page_dir) if has_logo else None,
            "logo_dark": rel(dark if os.path.isfile(dark) else logo, page_dir) if has_logo else None,
            "fonts": rel(fonts, page_dir) if os.path.isfile(fonts) else None}


def read_system_css():
    with open(os.path.join(TEMPLATES, "system.css"), encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def render_sheet(tokens_path, output, brand):
    """Render one variant. Return the notes on what fell back."""
    _tokens, css = read_tokens(tokens_path)
    c = read_copy(brand)
    page_dir = os.path.dirname(os.path.abspath(output))
    look = identity_look(brand, page_dir)
    links = [look["fonts"]] if look["fonts"] else []
    inline = (css + read_system_css()).replace("</style", "<\\/style")
    write(output, shell("Interface", sheet_body(c), look, links, inline, c["lang"]))
    return [] if look["fonts"] else ["the identity has no fonts/fonts.css; the faces fall back"]


def render_build(brand):
    """Render reference/. Return ({name: path}, notes on what fell back)."""
    step_dir = os.path.join(brand, DESIGN)
    tokens, css = read_tokens(os.path.join(step_dir, "tokens.json"))
    c = read_copy(brand)
    reference = os.path.join(step_dir, "reference")
    pages_dir = os.path.join(reference, "pages")
    notes = []
    look = identity_look(brand, reference)
    if not look["logo"]:
        notes.append("the identity has no logo/full.svg; the pages show the name")
    if not look["fonts"]:
        notes.append("the identity has no fonts/fonts.css; the faces fall back")
    try:
        with open(os.path.join(step_dir, "tokens.css"), encoding="utf-8") as handle:
            if handle.read() != css:
                raise Problem("tokens.css is out of date; run build_tokens.py on tokens.json")
    except OSError:
        raise Problem("tokens.css is missing; run build_tokens.py on tokens.json")
    written = {}
    os.makedirs(pages_dir, exist_ok=True)
    shutil.copyfile(os.path.join(TEMPLATES, "system.css"), os.path.join(reference, "system.css"))
    written["system.css"] = os.path.join(reference, "system.css")

    def links(look_here, depth):
        up = "../" * depth
        found = [up + "tokens.css", up[3:] + "system.css"]
        return found + ([look_here["fonts"]] if look_here["fonts"] else [])

    bar = ('<div class="doc-bar">%s<span class="t-label muted">Design system</span>'
           '<button class="button button-quiet theme-switch" type="button" '
           'aria-label="Switch the theme">%s</button></div>'
           % (brand_mark(look), icon("moon")))
    path = os.path.join(reference, "index.html")
    write(path, shell("Design system", '<main class="doc">%s</main>%s'
                      % (system_body(tokens, c, look), SWITCH_SCRIPT),
                      look, links(look, 1), lang=c["lang"], bar=bar))
    written["index.html"] = path
    path = os.path.join(reference, "sheet.html")
    write(path, shell("Interface", sheet_body(c), look, links(look, 1), lang=c["lang"]))
    written["sheet.html"] = path
    page_look = identity_look(brand, pages_dir)
    for name, (title, body) in page_bodies(c, page_look).items():
        path = os.path.join(pages_dir, name)
        write(path, shell(title, body, page_look, links(page_look, 2), lang=c["lang"]))
        written["pages/" + name] = path
    return written, notes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render the pages of a design system.")
    commands = parser.add_subparsers(dest="command", required=True)
    sheet = commands.add_parser("sheet", help="render one variant of the Interface choice")
    sheet.add_argument("tokens", help="the candidate tokens.json")
    sheet.add_argument("output", help="the .html file to write")
    sheet.add_argument("--brand", default="brand", help="path to brand/")
    build = commands.add_parser("build", help="render 04-design-system/reference/")
    build.add_argument("brand", nargs="?", default="brand", help="path to brand/")
    args = parser.parse_args(argv)
    try:
        if args.command == "sheet":
            notes = render_sheet(args.tokens, args.output, args.brand)
            print(args.output)
        else:
            written, notes = render_build(args.brand)
            for name in written:
                print(written[name])
    except Problem as error:
        print("ERROR   %s" % error, file=sys.stderr)
        print("nothing was written", file=sys.stderr)
        return 1
    except OSError as error:
        print(error, file=sys.stderr)
        return 2
    for note in notes:
        print("NOTE    %s" % note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
