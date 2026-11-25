#!/usr/bin/env python3
"""List the colors and the font families a site or a stylesheet uses.

    extract_style.py <url or path> [--top N]

The source is a page (its <style> blocks, its style attributes and the
stylesheets it links, each resolved against the page's address) or a
stylesheet. It may be an http(s) URL or a local file. The output is two
markdown lists, most used first:

    ## Colors

    - #1a1a1a (41)

    ## Fonts

    - Inter (12)

Colors are lowercase six-digit hex; rgb(), hsl() and oklch() are converted,
alpha is dropped and a fully transparent color is left out. Named colors
(red, rebeccapurple) and other color functions are not read. Font families
are taken from font-family, from the font shorthand and from custom
properties with "font" in their name; generic families (serif, system-ui and
the like) are left out. The counts are occurrences in the CSS, a hint of
weight and not a measurement. @import is followed. A linked or imported
stylesheet that cannot be fetched is skipped and named on stderr. --top limits
each list (default 12).

Used by the brand platform step to read the colors and fonts of a site the
owner already has. No dependencies beyond the Python 3 standard library.

Exit codes: 0 printed, 1 nothing found, 2 wrong usage or the source cannot be
read.
"""

import argparse
import colorsys
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser

TIMEOUT = 20
GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif",
           "ui-sans-serif", "ui-monospace", "ui-rounded", "math", "emoji", "fangsong",
           "inherit", "initial", "unset", "revert", "revert-layer", "-apple-system",
           "blinkmacsystemfont"}
NOT_FAMILY = ("size", "weight", "height", "spacing", "feature", "variation", "style",
              "stretch", "smoothing", "display")
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
BLOCK_RE = re.compile(r"\{([^{}]*)\}")
HEX_RE = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])")
FUNCTION_RE = re.compile(r"\b(rgba?|hsla?|oklch)\(([^()]*)\)", re.I)
CALL_RE = re.compile(r"[\w-]+\([^()]*\)")
SIZE_RE = re.compile(r"\d[\w.%]*(/[\w.%]+)?$")
IMPORT_RE = re.compile(r"@import\s+(?:url\(\s*)?[\"']?([^\"')\s;]+)", re.I)


def http(url):
    """Return the text of a URL. Raise OSError when it cannot be fetched."""
    request = urllib.request.Request(url, headers={"User-Agent": "brand"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, ValueError) as error:
        raise OSError(str(error))


def read(source):
    """Return the text of a URL or of a local file. Raise OSError."""
    if re.match(r"https?://", source, re.I):
        return http(source)
    if source.startswith("file://"):
        source = urllib.request.url2pathname(urllib.parse.urlparse(source).path)
    with open(source, encoding="utf-8", errors="replace") as handle:
        return handle.read()


class _Styles(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.css, self.links, self._in_style = [], [], False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "style":
            self._in_style = True
        elif tag == "link" and "stylesheet" in (attrs.get("rel") or "").lower().split() \
                and attrs.get("href"):
            self.links.append(attrs["href"])
        if attrs.get("style"):
            self.css.append("x{%s}" % attrs["style"])

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.css.append(data)


def _resolve(base, href):
    if re.match(r"https?://", base, re.I):
        return urllib.parse.urljoin(base, href)
    if re.match(r"https?://", href, re.I):
        return href
    return os.path.join(os.path.dirname(base), href)


def _with_imports(css, base, fetch, seen):
    """Return css followed by every stylesheet it imports, each fetched once."""
    parts = [css]
    for href in IMPORT_RE.findall(COMMENT_RE.sub("", css)):
        parts.append(_sheet(_resolve(base, href), fetch, seen))
    return "\n".join(parts)


def _sheet(target, fetch, seen):
    if target in seen:
        return ""
    seen.add(target)
    try:
        return _with_imports(fetch(target), target, fetch, seen)
    except OSError as error:
        print("skipped %s: %s" % (target, error), file=sys.stderr)
        return ""


def collect(source, fetch=read):
    """Return all the CSS of a page, or the stylesheet itself with what it imports. Raise
    OSError when the source cannot be read; a linked or imported stylesheet that cannot be
    read is skipped and named on stderr."""
    text = fetch(source)
    seen = {source}
    path = urllib.parse.urlparse(source).path if "://" in source else source
    if path.lower().endswith(".css") or not text.lstrip().startswith("<"):
        return _with_imports(text, source, fetch, seen)
    parser = _Styles()
    parser.feed(text)
    css = [_with_imports(block, source, fetch, seen) for block in parser.css]
    for href in parser.links:
        css.append(_sheet(_resolve(source, href), fetch, seen))
    return "\n".join(css)


def _ranked(counter):
    return sorted(counter.items(), key=lambda pair: (-pair[1], pair[0].lower()))


def _number(text, scale=1.0):
    """'50%' is 0.5 * scale; '128' is 128. None when it is not a number."""
    match = re.fullmatch(r"(-?\d*\.?\d+)(%|deg)?", text.strip())
    if not match:
        return None
    value = float(match.group(1))
    return value / 100.0 * scale if match.group(2) == "%" else value


def _hex(red, green, blue):
    """Three channels from 0 to 1, as '#rrggbb'."""
    return "#%02x%02x%02x" % tuple(int(round(min(max(c, 0.0), 1.0) * 255))
                                   for c in (red, green, blue))


def _color(name, arguments):
    """One rgb(), hsl() or oklch() call as '#rrggbb'. None when it cannot be read or is
    fully transparent."""
    parts = [part for part in re.split(r"[\s,/]+", arguments.strip()) if part]
    if len(parts) not in (3, 4):
        return None
    if len(parts) == 4 and _number(parts[3], 1.0) == 0:
        return None
    name = name.lower()
    if name.startswith("rgb"):
        channels = [_number(part, 255.0) for part in parts[:3]]
        if None in channels:
            return None
        return _hex(*(channel / 255.0 for channel in channels))
    if name.startswith("hsl"):
        hue, saturation, lightness = (_number(parts[0]), _number(parts[1], 1.0),
                                      _number(parts[2], 1.0))
        if None in (hue, saturation, lightness):
            return None
        return _hex(*colorsys.hls_to_rgb((hue % 360) / 360.0, lightness, saturation))
    lightness, chroma, hue = _number(parts[0], 1.0), _number(parts[1], 0.4), _number(parts[2])
    if None in (lightness, chroma, hue):
        return None
    a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
    long_, medium, short = ((lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3,
                            (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3,
                            (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3)
    linear = (4.0767416621 * long_ - 3.3077115913 * medium + 0.2309699292 * short,
              -1.2684380046 * long_ + 2.6097574011 * medium - 0.3413193965 * short,
              -0.0041960863 * long_ - 0.7034186147 * medium + 1.7076147010 * short)
    return _hex(*(12.92 * c if c <= 0.0031308 else 1.055 * max(c, 0.0) ** (1 / 2.4) - 0.055
                  for c in linear))


def _family_of(shorthand):
    """The family list of a 'font:' shorthand: what follows the size, the last token that
    starts with a digit ('italic 700 16px/1.2 Georgia, serif' gives 'Georgia, serif')."""
    head, comma, rest = CALL_RE.sub("1px", shorthand.strip()).partition(",")
    tokens = re.sub(r"\s*/\s*", "/", head).split()
    sizes = [index for index, token in enumerate(tokens) if SIZE_RE.match(token)]
    if not sizes:
        return ""
    return " ".join(tokens[sizes[-1] + 1:]) + comma + rest


def extract(css):
    """Return (colors, fonts): two lists of (value, count), most used first. Only the
    declarations inside rule blocks are read, so selectors and comments never count."""
    colors, fonts = Counter(), Counter()
    for block in BLOCK_RE.findall(COMMENT_RE.sub("", css)):
        for declaration in block.split(";"):
            name, colon, value = declaration.partition(":")
            name, value = name.strip().lower(), re.sub(r"!important", "", value, flags=re.I)
            if not colon or not value.strip():
                continue
            for digits in HEX_RE.findall(value):
                if len(digits) == 8 and digits[6:].lower() == "00" or \
                        len(digits) == 4 and digits[3] == "0":
                    continue
                if len(digits) in (3, 4):
                    digits = "".join(char * 2 for char in digits[:3])
                colors["#" + digits[:6].lower()] += 1
            for function, arguments in FUNCTION_RE.findall(value):
                color = _color(function, arguments)
                if color:
                    colors[color] += 1
            if name == "font-family":
                families = value
            elif name == "font":
                families = _family_of(value)
            elif name.startswith("--") and "font" in name \
                    and not any(word in name for word in NOT_FAMILY):
                families = value
            else:
                continue
            for family in families.split(","):
                family = family.strip().strip("\"'").strip()
                if family and family.lower() not in GENERIC and "(" not in family \
                        and not family[0].isdigit():
                    fonts[family] += 1
    return _ranked(colors), _ranked(fonts)


def main(argv=None):
    parser = argparse.ArgumentParser(description="List the colors and fonts of a site or "
                                                 "a stylesheet.")
    parser.add_argument("source", help="an http(s) URL or a local .html or .css file")
    parser.add_argument("--top", type=int, default=12, help="lines per list (default 12)")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    try:
        css = collect(args.source)
    except OSError as error:
        print("%s cannot be read: %s" % (args.source, error), file=sys.stderr)
        return 2
    colors, fonts = extract(css)
    if not colors and not fonts:
        print("no colors and no fonts found in %s" % args.source, file=sys.stderr)
        return 1
    for title, rows in (("Colors", colors), ("Fonts", fonts)):
        print("## %s\n" % title)
        for value, count in rows[:max(args.top, 1)]:
            print("- %s (%d)" % (value, count))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
