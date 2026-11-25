#!/usr/bin/env python3
"""Render the two pages the identity step shows its variants on.

    render_carrier.py carrier <data.json> <output.html>
    render_carrier.py sheet <data.json> <output.html>

The carrier is one fixed, neutral layout for every brand: a header with the
logo, the main promise as the headline, one paragraph and one button. A variant
of a color, type or motto choice is the carrier with that one thing changed;
whatever the data leaves out stays neutral (system type, black and white, the
name as plain text). The sheet shows one logo candidate: large, the mark alone,
at 24, 32 and 48 pixels high, on light and on dark, and in a header. The mark
on dark is the one-color version ("mono"), which takes the color of the text.

The data format is described in reference/carrier.md. Paths in the data are relative
to the data file. Both pages style a light and a dark theme through data-theme
and carry the theme listener of reference/choice-page.md. No dependencies beyond the
Python 3 standard library.

Exit codes: 0 rendered, 1 the data breaks a rule, 2 the data file cannot be read.
"""

import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contract as cc  # noqa: E402

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "templates")

SYSTEM = '-apple-system,BlinkMacSystemFont,"Helvetica Neue",Helvetica,Arial,sans-serif'
NEUTRAL = {"light": {"background": "#FFFFFF", "text": "#111111", "accent": "#111111"},
           "dark": {"background": "#111111", "text": "#FFFFFF", "accent": "#FFFFFF"}}
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")
GOOGLE_FONTS = "https://fonts.googleapis.com/"

CARRIER_KEYS = {"name": True, "promise": True, "paragraph": True, "button": True,
                "lang": False, "logo": False, "logo_dark": False, "colors": False,
                "fonts": False, "motto": False}
SHEET_KEYS = {"name": True, "full": True, "mark": True, "dark": False, "mono": False,
              "lang": False, "header_label": False}


class Problem(Exception):
    """The data breaks a rule of reference/carrier.md."""


def check_keys(data, keys, where="", objects=()):
    """keys: {name: required}. objects: the keys whose value is an object, checked by the
    caller; every other value must be text."""
    if not isinstance(data, dict):
        raise Problem("%smust be an object" % (where or "the data "))
    for key in data:
        if key not in keys:
            raise Problem("unknown key '%s%s'" % (where, key))
    for key, required in keys.items():
        if required and not (isinstance(data.get(key), str) and data[key].strip()):
            raise Problem("missing key '%s%s'" % (where, key))
    for key, value in data.items():
        if key not in objects and not isinstance(value, str):
            raise Problem("'%s%s' must be text" % (where, key))


def read_svg(base, relative, key):
    """The SVG file as markup to place in the page."""
    path = os.path.join(base, relative)
    try:
        with open(path, encoding="utf-8-sig") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as error:
        raise Problem("'%s': %s cannot be read: %s" % (key, relative, error))
    start = text.find("<svg")
    if start == -1:
        raise Problem("'%s': %s is not an SVG document" % (key, relative))
    text = text[start:].strip()
    if re.search(r"<script|\son\w+\s*=|javascript:", text, re.IGNORECASE):
        raise Problem("'%s': %s holds a script; a logo is shapes only" % (key, relative))
    return text


def fill(template, values):
    with open(os.path.join(TEMPLATES, template), encoding="utf-8") as handle:
        text = handle.read()
    return re.sub(r"\{\{(\w+)\}\}", lambda match: values[match.group(1)], text)


def font_stack(name):
    """A family name as the head of a CSS font stack."""
    if re.search(r"[^\w .-]", name):
        raise Problem("'%s' is not a font family name" % name)
    return '"%s",%s' % (name.strip(), SYSTEM)


def render_carrier(data, base):
    check_keys(data, CARRIER_KEYS, objects=("colors", "fonts"))
    colors = data.get("colors", {})
    check_keys(colors, {"light": False, "dark": False}, "colors.", ("light", "dark"))
    values = {}
    for theme in ("light", "dark"):
        given = colors.get(theme, {})
        check_keys(given, {"background": False, "text": False, "accent": False},
                   "colors.%s." % theme)
        chosen = dict(NEUTRAL[theme], **given)
        for role, color in chosen.items():
            if not isinstance(color, str) or not HEX_RE.fullmatch(color):
                raise Problem("'colors.%s.%s' is '%s'; must be a color of the form #RRGGBB"
                              % (theme, role, color))
            values["%s_%s" % (theme, role)] = color
        on_accent = max((chosen["background"], chosen["text"]),
                        key=lambda color: cc.contrast(color, chosen["accent"]))
        values["%s_on_accent" % theme] = on_accent

    fonts = data.get("fonts", {})
    check_keys(fonts, {"display": False, "text": False, "css": False}, "fonts.")
    values["display"] = font_stack(fonts["display"]) if fonts.get("display") else SYSTEM
    values["text"] = font_stack(fonts["text"]) if fonts.get("text") else SYSTEM
    values["fonts_link"] = ""
    if fonts.get("css"):
        address = fonts["css"]
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:|//", address) and not address.startswith(
                GOOGLE_FONTS):
            raise Problem("'fonts.css' is '%s'; must be a relative path, or an address at %s "
                          "while the type pair is not fixed" % (address, GOOGLE_FONTS))
        values["fonts_link"] = '<link rel="stylesheet" href="%s">' % html.escape(
            address, quote=True)

    name = html.escape(data["name"])
    if data.get("logo_dark") and not data.get("logo"):
        raise Problem("'logo_dark' needs 'logo'")
    if data.get("logo"):
        logo = '<div class="logo logo-light" role="img" aria-label="%s">%s</div>' % (
            html.escape(data["name"], quote=True), read_svg(base, data["logo"], "logo"))
        if data.get("logo_dark"):
            logo += '<div class="logo logo-dark" role="img" aria-label="%s">%s</div>' % (
                html.escape(data["name"], quote=True),
                read_svg(base, data["logo_dark"], "logo_dark"))
    else:
        logo = '<div class="logo"><span class="name">%s</span></div>' % name
    values.update({
        "lang": html.escape(data.get("lang", "en"), quote=True), "name": name, "logo": logo,
        "header_class": "has-dark" if data.get("logo_dark") else "",
        "motto": '<p class="motto">%s</p>' % html.escape(data["motto"])
                 if data.get("motto") else "",
        "promise": html.escape(data["promise"]), "paragraph": html.escape(data["paragraph"]),
        "button": html.escape(data["button"]),
    })
    return fill("carrier.html", values)


def render_sheet(data, base):
    check_keys(data, SHEET_KEYS)
    full = read_svg(base, data["full"], "full")
    mark = read_svg(base, data["mark"], "mark")
    dark = read_svg(base, data["dark"], "dark") if data.get("dark") else full
    # The mark on dark is the one-color version, which takes the color of the text around it.
    mono = read_svg(base, data["mono"], "mono") if data.get("mono") else ""

    def sizes(svg):
        return "".join("<figure>%s<figcaption>%d px</figcaption></figure>"
                       % (svg.replace("<svg", '<svg style="height:%dpx"' % size, 1), size)
                       for size in (24, 32, 48))

    return fill("logo-sheet.html", {
        "lang": html.escape(data.get("lang", "en"), quote=True),
        "name": html.escape(data["name"]), "full": full, "mark": mark, "dark": dark,
        "sizes": '<div class="panel sizes light%s">%s</div>' % ("" if mono else " wide",
                                                                 sizes(mark)),
        "sizes_dark": '<div class="panel sizes dark">%s</div>' % sizes(mono) if mono else "",
        "header_label": html.escape(data.get("header_label", "In a header")),
    })


MODES = {"carrier": render_carrier, "sheet": render_sheet}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] not in MODES:
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        return 1
    mode, source, output = args
    try:
        with open(source, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print("%s cannot be read: %s" % (source, error), file=sys.stderr)
        return 2
    try:
        text = MODES[mode](data, os.path.dirname(os.path.abspath(source)))
    except Problem as error:
        print(error, file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
