#!/usr/bin/env python3
"""Build the brand book from the approved plates of a brand/ directory.

    render_book.py [<path to brand/>] [--approve] [--no-pdf]

Writes, in brand/05-brand-book/:

    review/source.html   the book before bundling
    review/shots/        the screenshots of the surfaces and the example pages
    index.html           the book: one self-contained page in the brand's style
    brand-book.pdf       the same, printed by headless Chrome, always light
    brand-book.md        the same content as text, for agents

The composition is fixed and the same for every brand: the cover; Strategy on
one page and the seven plates; Platform on one page and the plates of the
platform; Identity on one page, its four plates and its surfaces; the
Interface plate, the sheet and the three example pages of the design system;
How to use this. Only the slots of a plate go in, never its Rationale. Every
block is numbered, so the owner can correct by number. The page has a light
and a dark theme and a switch; it follows the reader's setting until switched.

The screenshots are taken with headless Chrome when tools.screenshots is
headless-chrome. When it is manual, or no Chrome is found, the script names the
images to place in review/shots/ and stops until they are there; the PDF is
then skipped. brand-book.md says status: draft unless --approve is given.

No dependencies beyond the Python 3 standard library. Exit codes: 0 built,
1 something is missing or not approved (nothing is written), 2 brand/ unreadable.
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import book_print as bp  # noqa: E402
import book_scenes as bs  # noqa: E402
import bundle_html as bh  # noqa: E402
import check_contract as cc  # noqa: E402
import render_plates as rp  # noqa: E402
import render_system as rs  # noqa: E402
import screenshot as ss  # noqa: E402

BOOK = "05-brand-book"
STRATEGY, PLATFORM, IDENTITY, DESIGN = "01-strategy", "02-brand-platform", "03-identity", \
    "04-design-system"
PARTS = [(STRATEGY, "Strategy"), (PLATFORM, "Brand platform"), (IDENTITY, "Identity"),
         (DESIGN, "Design system")]

# The sizes of the surfaces of the profiles, used when no surfaces review page names them.
SURFACE_SIZES = {"site-hero": (1440, 900), "avatar": (400, 400), "social-cover": (1500, 500),
                 "og-image": (1200, 630), "email-signature": (600, 220)}
DEFAULT_SURFACE = (1200, 630)
SHEET_SIZE = (1440, 1100)
WIDE, NARROW = (1440, 900), (390, 844)
CHROME_MIN_WIDTH = 500  # headless Chrome lays out no narrower than this
# The screenshots and the PDF are light, whatever the setting of the machine.
LIGHT = ("--blink-settings=preferredColorScheme=1",)

HOW_TO_USE = """**Read first.** This book, from the start. The strategy says what the brand promises and to whom; the platform says how it sounds; the identity and the design system say how it looks.

**Fixed.** The logo files, the palette, the two families and their sizes, the motto, and every value in `tokens.json`. Use them as they are. Never redraw the logo, add a color or set a size by hand.

**Free.** The composition of a page, the images, the length of a text, the order of sections, within the rules of this book.

**Check before you ship.**

- Text reaches 4.5 to 1 on its background, and the borders of controls 3 to 1, in both themes.
- No line breaks a rule of We never write.
- The accent appears only where Accent is for allows it.
- The logo is never smaller than its Minimum size and keeps its Clear space.

**When something is missing.** Do not improvise. Name what is missing and go back to the step that owns it: the strategy, the platform, the identity or the design system."""

BOOK_CSS = """
.book-bar{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 32px;background:var(--paper);border-bottom:1px solid var(--line)}
.book-bar img{height:28px;width:auto}
.book-bar button{font:inherit;font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);background:none;border:1px solid var(--line);border-radius:99px;padding:6px 12px;cursor:pointer}
.logo-dark{display:none}
:root[data-theme="dark"] .logo-light{display:none}
:root[data-theme="dark"] .logo-dark{display:block}
.onepage .logo img.logo-dark{display:none}
:root[data-theme="dark"] .onepage .logo img.logo-light{display:none}
:root[data-theme="dark"] .onepage .logo img.logo-dark{display:block}
.board img[src$=".svg"],.board img[src^="data:image/svg"]{background:var(--light)}
.cover{min-height:560px;display:flex;flex-direction:column;justify-content:center;gap:28px;margin-bottom:112px}
.cover img{max-width:min(100%,520px);max-height:160px;width:auto;height:auto}
.cover .name{font-family:var(--display);font-size:96px;line-height:1;letter-spacing:-.02em;overflow-wrap:anywhere}
.cover .motto{font-family:var(--display);font-size:40px;line-height:1.1}
.cover .line{font-size:22px;max-width:30em;color:var(--muted)}
.contents{margin-bottom:112px}
.contents ol{list-style:none;padding:0;columns:2;column-gap:48px}
.contents li{padding:6px 0;border-top:1px solid var(--line);break-inside:avoid}
.contents a{color:var(--ink);text-decoration:none}
.part{font-family:var(--display);font-weight:400;font-size:64px;letter-spacing:-.015em;margin:0 0 56px;padding-top:24px;border-top:3px solid var(--ink)}
.block{position:relative}
.num{position:absolute;left:-56px;top:2px;width:36px;height:36px;display:flex;align-items:center;justify-content:center;border:1px solid var(--line);border-radius:50%;font-family:var(--mono);font-size:12px;color:var(--muted)}
.shot{margin-bottom:112px}
.shot header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:20px}
.shot h2{font-family:var(--display);font-weight:400;font-size:44px;line-height:1.05}
.shot figure{margin:0}
.shot img{display:block;max-width:100%;height:auto;border:1px solid var(--line);background:var(--card)}
.shot figcaption{font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--muted);margin-top:8px}
.pair{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}
.pair .wide{flex:1 1 520px;min-width:0}
.phone{width:195px;height:422px;overflow:hidden;border:1px solid var(--line);flex:none}
.phone img{height:422px;width:auto;max-width:none;border:0}
.prose p,.prose li{font-size:18px;line-height:1.5;max-width:42em}
.prose p+p,.prose p+ul,.prose ul+p{margin-top:16px}
.prose ul{list-style:disc;padding-left:22px}
.prose code,.files code{font-family:var(--mono);font-size:14px}
.files{width:100%;border-collapse:collapse;margin-top:40px}
.files td,.files th{text-align:left;padding:10px 16px 10px 0;border-top:1px solid var(--line);vertical-align:top}
.files th{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:500}
@media (max-width:820px){
.num{position:static;margin-bottom:12px}
.cover .name{font-size:52px}.cover .motto{font-size:28px}
.part{font-size:40px}
.contents ol{columns:1}
.shot h2{font-size:32px}
.book-bar{padding:10px 16px}
}
@media print{
.book-bar{display:none}
.part{break-before:page}
.block,.shot{break-inside:avoid}
.logo-dark{display:none!important}.logo-light{display:block!important}
}
"""

THEME_SCRIPT = rs.THEME_SCRIPT
SWITCH_SCRIPT = ("<script>document.querySelector('.theme-switch').addEventListener('click',"
                 "function(){var r=document.documentElement;r.dataset.theme=r.dataset.theme==="
                 "'dark'?'light':'dark'})</script>")


class Problem(Exception):
    """Something the book needs is missing or not approved."""


def e(text):
    return html.escape(text, quote=True)


def md_inline(text):
    """`code` and **bold** of the fixed text, as HTML."""
    text = e(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def prose(text):
    out, items = [], []
    for line in text.splitlines():
        if line.startswith("- "):
            items.append("<li>%s</li>" % md_inline(line[2:]))
            continue
        if items:
            out.append("<ul>%s</ul>" % "".join(items))
            items = []
        if line.strip():
            out.append("<p>%s</p>" % md_inline(line))
    if items:
        out.append("<ul>%s</ul>" % "".join(items))
    return '<div class="prose">%s</div>' % "".join(out)


# --- Reading -------------------------------------------------------------------


def load(brand):
    """The approved plates, the board and the look. Raise Problem when a plate is missing,
    malformed or a draft, or when the identity is not approved."""
    plates, skipped = [], []
    for step in (STRATEGY, PLATFORM, IDENTITY, DESIGN):
        for name in cc.PLATES[step]:
            try:
                plate = rp.load_plate(brand, step, name)
            except (OSError, UnicodeDecodeError, ValueError) as error:
                raise Problem("%s/%s: %s" % (step, name, error))
            if plate is None:
                if name in cc.OPTIONAL_PLATES.get(step, ()):
                    continue
                raise Problem("%s/%s is missing" % (step, name))
            if plate["status"] != "approved":
                raise Problem("%s/%s is a draft; the book holds only what is approved"
                              % (step, name))
            plates.append(plate)
    brief = rp.load_plate(brand, "00-intake", "brief.md")
    if brief is None:
        raise Problem("00-intake/brief.md is missing")
    try:
        board = rp.load_board(brand)
    except ValueError as error:
        raise Problem("%s/moodboard/index.md: %s" % (PLATFORM, error))
    look = rp.brand_look(brand, plates, skipped)
    if not look["styled"]:
        raise Problem("the identity is not approved in pipeline.yaml; the book is set in the "
                      "brand's style")
    for name in ("sheet.html", "pages/landing.html", "pages/sign-in.html", "pages/sign-up.html"):
        if not os.path.isfile(os.path.join(brand, DESIGN, "reference", name)):
            raise Problem("%s/reference/%s is missing; run render_system.py build" % (DESIGN, name))
    return plates, brief, board, look, skipped


def brand_name(plates, brief):
    for plate in plates:
        if plate["name"] == "name.md":
            return rp.one(plate, "Name")
    return rp.one(brief, "Brand")


def surface_sizes(brand):
    """{surface file: [(width, height), ...]}, widest first, from the latest surfaces review
    data, if any. A surface reviewed at two sizes is shown in the book at both."""
    import json
    review = os.path.join(brand, IDENTITY, "review")
    try:
        names = sorted(n for n in os.listdir(review) if re.fullmatch(r"surfaces-\d+\.json", n))
    except OSError:
        return {}
    if not names:
        return {}
    try:
        with open(os.path.join(review, names[-1]), encoding="utf-8") as handle:
            data = json.load(handle)
        sizes = {}
        for item in data.get("items", []):
            size = (int(item["width"]), int(item["height"]))
            listed = sizes.setdefault(os.path.basename(item["file"]), [])
            if size not in listed:
                listed.append(size)
        return {name: sorted(listed, reverse=True) for name, listed in sizes.items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def shot_list(brand):
    """[(shot file name, page path, width, height, caption)] the book needs."""
    sizes = surface_sizes(brand)
    shots = []
    for name in rp.list_surfaces(brand):
        stem = name[:-len(".html")]
        listed = sizes.get(name) or [SURFACE_SIZES.get(stem, DEFAULT_SURFACE)]
        page, title = os.path.join(brand, IDENTITY, "surfaces", name), stem.replace("-", " ")
        for index, (width, height) in enumerate(listed):
            # The widest keeps the plain name; a further size carries its width.
            shot = "surface-%s.png" % stem if index == 0 else "surface-%s-%d.png" % (stem, width)
            caption = title if len(listed) == 1 else "%s at %d" % (title, width)
            shots.append((shot, page, width, height, caption))
    reference = os.path.join(brand, DESIGN, "reference")
    shots.append(("system-sheet.png", os.path.join(reference, "sheet.html")) + SHEET_SIZE
                 + ("the interface",))
    for title, name in rp.EXAMPLE_PAGES:
        stem = name[:-len(".html")]
        page = os.path.join(reference, "pages", name)
        shots.append(("page-%s-1440.png" % stem, page) + WIDE + (title + " at 1440",))
        shots.append(("page-%s-390.png" % stem, page) + NARROW + (title + " at 390",))
    return shots


def take_shots(brand, chrome, shots_dir):
    """Take every screenshot with Chrome. Raise Problem on the first failure."""
    os.makedirs(shots_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="brand-book-")
    try:
        for name, page, width, height, _caption in shot_list(brand):
            url = ss.target_url(page)
            if width < CHROME_MIN_WIDTH:
                wrapper = os.path.join(work, name + ".html")
                with open(wrapper, "w", encoding="utf-8") as handle:
                    handle.write('<!doctype html><body style="margin:0"><iframe src="%s" '
                                 'style="width:%dpx;height:%dpx;border:0;display:block">'
                                 "</iframe></body>" % (e(url), width, height))
                url, width = ss.target_url(wrapper), CHROME_MIN_WIDTH
            failure = ss.capture(chrome, url, os.path.join(shots_dir, name), width, height,
                                 LIGHT)
            if failure:
                raise Problem("screenshot %s: %s" % (name, failure))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --- The page -------------------------------------------------------------------


def themed(css):
    """The brand's look follows the reader's setting; in the book it follows data-theme,
    and print is always light."""
    dark = re.search(r"@media \(prefers-color-scheme:dark\)\{:root\{([^}]*)\}\}", css)
    if dark:
        css = css.replace(dark.group(0), ':root[data-theme="dark"]{%s}' % dark.group(1))
    return re.sub(r"@media print\{:root\{([^}]*)\}\}",
                  r'@media print{:root,:root[data-theme="dark"]{\1}}', css)


def blocks_html(blocks):
    """blocks: [(kind, html)] with kind 'part' or 'block' -> numbered HTML."""
    out, number = [], 0
    for kind, content in blocks:
        if kind == "part":
            out.append(content)
            continue
        number += 1
        out.append('<div class="block" id="b%d"><span class="num">%d</span>%s</div>'
                   % (number, number, content))
    return "".join(out), number


def themed_logo(body, identity, look):
    """The full logo of a one-page view, in the version of the book's theme. The page's own
    <picture> follows the reader's setting, not the book's switch, so the pair is set here."""
    if not look["logo"]:
        return body
    single = rp.logo_picture(identity, "The logo", dict(look, styled=False))
    base = e(identity) + "logo/"
    pair = ('<img class="logo-light" src="%sfull.svg" alt="The logo">'
            '<img class="logo-dark" src="%sdark.svg" alt="The logo">' % (base, base))
    return body.replace(single, pair)


def shot_block(key, title, kicker, figures):
    """A block of screenshots, as a scene: it keeps the space of the scenes around it."""
    return bs.wrap("shot", '<section class="shot" id="%s"><header><div><p class="kicker">%s</p>'
                           "<h2>%s</h2></div></header>%s</section>"
                   % (key, e(kicker), e(title), figures), lights=0)


def figure(src, caption, phone=False, size=None):
    """size is the (width, height) the shot was made for. Chrome lays out no narrower than
    CHROME_MIN_WIDTH, so a narrower shot has a blank strip on its right; it is cut off here."""
    cut = ""
    if size and not phone and size[0] < CHROME_MIN_WIDTH:
        cut = (' style="aspect-ratio:%d/%d;width:min(100%%,%dpx);object-fit:cover;'
               'object-position:left top"' % (size[0], size[1], size[0]))
    image = '<img src="%s" alt="%s" loading="lazy"%s>' % (e(src), e(caption), cut)
    if phone:
        return '<figure><div class="phone">%s</div><figcaption>%s</figcaption></figure>' % (
            image, e(caption))
    return '<figure class="wide">%s<figcaption>%s</figcaption></figure>' % (image, e(caption))


FILES = [
    ("Logo", "03-identity/logo/full.svg, mark.svg, mono.svg, dark.svg"),
    ("Fonts", "03-identity/fonts/fonts.css and the font files beside it"),
    ("Surfaces", "03-identity/surfaces/"),
    ("Tokens", "04-design-system/tokens.json (the source), tokens.css (generated)"),
    ("Components", "04-design-system/components.md, reference/system.css"),
    ("The whole system", "04-design-system/reference/index.html"),
    ("This book as text", "05-brand-book/brand-book.md"),
]

# The same table for the kit that export_kit.py writes to brand/out/.
KIT_FILES = [
    ("Logo", "logo/full.svg, mark.svg, mono.svg, dark.svg"),
    ("Fonts", "fonts/fonts.css and the font files beside it"),
    ("Surfaces", "surfaces/"),
    ("Tokens", "tokens/tokens.json (the source), tokens.css (generated)"),
    ("Components", "system/components.md, system/system.css"),
    ("The whole system", "system/index.html"),
    ("This book", "book/index.html, book/brand-book.pdf"),
    ("This book as text", "brand.md"),
    ("Every slot as data", "brand.json"),
]


def files_table():
    """The files of the kit: the book travels in the kit, so it names the kit's paths and
    nothing of the working directory (reference/contract.md, section 8)."""
    rows = "".join("<tr><td>%s</td><td><code>%s</code></td></tr>" % (e(what), e(path))
                   for what, path in KIT_FILES)
    return ('<table class="files"><thead><tr><th>What</th><th>Path in the kit</th></tr></thead>'
            "<tbody>%s</tbody></table>" % rows)


def book_body(brand, plates, brief, board, look):
    identity, prefix, shots = "../../03-identity/", "../../02-brand-platform/moodboard/", "shots/"
    name = brand_name(plates, brief)
    by_name = {plate["name"]: plate for plate in plates}
    motto = rp.one(by_name["motto.md"], "Motto")
    plain = dict(look, system=False)
    logo = ('<img class="logo-light" src="%slogo/full.svg" alt="%s"><img class="logo-dark" '
            'src="%slogo/dark.svg" alt="%s">' % (identity, e(name), identity, e(name))
            if look["logo"] else "")
    blocks = [("block", '<section class="cover" id="cover">%s<p class="name">%s</p>'
                        '<p class="motto">%s</p><p class="line">%s</p>%s</section>'
               % (logo, e(name), e(motto), e(rp.one(brief, "In one line")), bs.STROKE))]
    contents = []
    # The printed book takes the same blocks in the same order, so the numbers agree.
    printed = bp.PrintBook(name, identity, shots, look["logo"])
    printed.cover(motto, rp.one(brief, "In one line"))

    def part(step, title):
        contents.append((step, title))
        blocks.append(("part", bs.chapter(step, title, len(contents), len(PARTS) + 1)))
        printed.part(title, len(contents), len(PARTS) + 1)

    def visual(plate):
        key, slots = plate["name"][:-len(".md")], bs.slots_of(plate)
        try:
            if key == "golden-circle":
                return {"visual": rp.RINGS}
            if key == "archetype":
                return {"visual": rp.wheel(slots["Primary archetype"][0],
                                           slots["Secondary archetype"][0],
                                           slots["Character"][0])}
            if key == "logo" and look["logo"]:
                return {"visual": rp.render_sheet(identity)}
            if key == "typography":
                return {"lead": rp.render_specimen(slots["Display"][0], slots["Text"][0],
                                                   slots["Type idea"][0]), "lead_weight": 170}
        except (KeyError, IndexError):
            pass
        return {}

    def onepage(key, title, kicker, body):
        blocks.append(("block", bs.wrap(
            key, '<section class="plate" id="%s"><header><div><p class="kicker">'
                 '%s</p><h2>%s</h2></div></header>%s</section>' % (key, e(kicker), e(title), body))))

    def plates_of(step):
        """Each plate as its scene; one without a scene as the map draws it, on glass."""
        for plate in plates:
            if plate["step"] == step:
                blocks.append(("block", bs.scene(plate) or bs.wrap(
                    plate["name"][:-len(".md")],
                    rp.render_plate(plate, None, prefix, identity, plain))))
                printed.plate(plate, **visual(plate))

    part(STRATEGY, "Strategy")
    blocks.append(("block", bs.wall("strategy", "Strategy", "On one page",
                                    rp.render_onepage(plates))))
    printed.wall("On one page", "Strategy",
                 [("%s · %s" % (title, rp.LABELS.get(slot, slot)), rp.one(by_name[plate], slot))
                  for plate, slot, title in rp.HEADLINES if plate in by_name])
    plates_of(STRATEGY)
    part(PLATFORM, "Brand platform")
    blocks.append(("block", bs.wall("platform", "Brand platform", "On one page",
                                    rp.render_platform(plates, name, None, prefix),
                                    bs.board_wall(board, prefix))))
    printed.wall("On one page", "Brand platform",
                 [(slot, rp.one(by_name[plate], slot) if plate in by_name else name)
                  for plate, slot in rp.PLATFORM_HEADLINES
                  if plate in by_name or name not in ("Brand", "Unnamed")])
    printed.board(board, prefix, "Brand platform")
    plates_of(PLATFORM)
    part(IDENTITY, "Identity")
    onepage("identity", "On one page", "Identity",
            themed_logo(rp.render_identity(plates, [], dict(look, styled=False), identity),
                        identity, look))
    printed.identity_page(rp.render_identity(plates, [], dict(look, styled=False), identity))
    plates_of(IDENTITY)
    surfaces = {}
    for shot, page, width, height, caption in shot_list(brand):
        if shot.startswith("surface-"):
            surfaces.setdefault(page, []).append((shot, (width, height), caption))
    for page, listed in surfaces.items():
        stem = os.path.basename(page)[:-len(".html")]
        figures = "".join(figure(shots + shot, caption, phone=size == NARROW, size=size)
                          for shot, size, caption in listed)
        if len(listed) > 1:
            figures = '<div class="pair">%s</div>' % figures
        blocks.append(("block", shot_block("surface-" + stem,
                                           stem.replace("-", " ").capitalize(), "Surface",
                                           figures)))
        printed.figure(stem.replace("-", " ").capitalize(), "Surface",
                       [(shot, caption, size == NARROW, size) for shot, size, caption in listed])
    part(DESIGN, "Design system")
    plates_of(DESIGN)
    blocks.append(("block", shot_block("sheet", "The interface", "Design system",
                                       figure(shots + "system-sheet.png", "the interface"))))
    printed.figure("The interface", "Design system", [("system-sheet.png", "the interface", False, None)])
    for title, page_name in rp.EXAMPLE_PAGES:
        stem = page_name[:-len(".html")]
        printed.figure(title, "Example page, not the design of a site",
                       [("page-%s-1440.png" % stem, title + " at 1440", False, None),
                        ("page-%s-390.png" % stem, title + " at 390", True, None)])
        blocks.append(("block", shot_block(
            "page-" + stem, title, "Example page, not the design of a site",
            '<div class="pair">%s%s</div>' % (
                figure("%spage-%s-1440.png" % (shots, stem), title + " at 1440"),
                figure("%spage-%s-390.png" % (shots, stem), title + " at 390", phone=True)))))
    contents.append(("how", "How to use this"))
    blocks.append(("part", bs.chapter("how", "How to use this", len(contents), len(PARTS) + 1)))
    printed.part("How to use this", len(contents), len(PARTS) + 1)
    printed.how(prose(HOW_TO_USE), files_table())
    blocks.append(("block", bs.wrap("how-to-use", '<section class="shot" id="how-to-use">%s%s'
                                    "</section>" % (prose(HOW_TO_USE), files_table()))))
    body, count = blocks_html(blocks)
    toc = '<nav class="contents"><p class="kicker">Contents</p><ol>%s</ol></nav>' % "".join(
        '<li><a href="#%s">%s</a></li>' % (key, e(title)) for key, title in contents)
    # The cover is the first block; it and the contents open the book as one scene.
    start, end = body.index("<section"), body.index("</section>") + len("</section>")
    cover = bs.section("cover-scene", "cover", body[start:end] + toc,
                       bs.light("48%", "-10%", "70vw", -160, 60))
    return body[:start] + cover + body[end:], count, name, printed


def book_page(brand, plates, brief, board, look):
    body, count, name, printed = book_body(brand, plates, brief, board, look)
    identity = "../../03-identity/"
    link = '<link rel="stylesheet" href="%sfonts/fonts.css">' % identity if look["fonts"] else ""
    paper, sheets = printed.document(rp.CSS + themed(look["css"]), link)
    logo = ('<img class="logo-light" src="%slogo/full.svg" alt="%s"><img class="logo-dark" '
            'src="%slogo/dark.svg" alt="%s">' % (identity, e(name), identity, e(name))
            if look["logo"] else '<span>%s</span>' % e(name))
    bar = ('<div class="book-bar">%s<span class="kicker">Brand book</span>'
           '<button class="theme-switch" type="button">Light · Dark</button></div>' % logo)
    page = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s: brand book</title>%s%s<style>%s%s%s</style></head><body>%s<main>%s</main>"
            "%s</body></html>\n"
            % (e(name), THEME_SCRIPT, link, rp.CSS, themed(look["css"]), BOOK_CSS + bs.CSS, bar,
               body, SWITCH_SCRIPT + bs.JS))
    return page, count, paper, sheets


# --- brand-book.md ---------------------------------------------------------------


def plate_md(plate, kit=False):
    lines = ["### %s" % plate["title"], ""]
    if not kit:
        lines += ["File: `%s/%s`" % (plate["step"], plate["name"]), ""]
    for slot, values in plate["slots"]:
        if slot["kind"] == "line":
            lines.append("**%s**: %s" % (slot["name"], values[0]))
        else:
            lines.append("**%s**:" % slot["name"])
            lines.append("")
            lines.extend("- " + value for value in values)
        lines.append("")
    return lines


def token_value(tokens, path, dark=False, narrow=False):
    try:
        kind, _value = cc.resolve(tokens, path, dark, narrow)
    except KeyError:
        return "-"
    if kind == "color":
        value = cc.resolve(tokens, path, dark, narrow)[1]
        try:
            channels = tuple(int(round(c * 255)) for c in value["components"])
        except (KeyError, TypeError):
            return "-"
        alpha = value.get("alpha", 1)
        return "#%02X%02X%02X" % channels + ("" if alpha == 1 else " at %s" % alpha)
    if kind == "shadow":
        return "a shadow, see tokens.json"
    return rs.describe(tokens, path, narrow)


def tokens_md(brand):
    tokens, _data, _problems = cc.load_tokens(os.path.join(brand, DESIGN, "tokens.json"))
    rows = ["| Token | Type | Value | Dark | At 390 |", "|---|---|---|---|---|"]
    for path, (kind, _value) in tokens.items():
        if path[0] in ("dark", "narrow"):
            continue
        dark = token_value(tokens, path, dark=True) if ("dark",) + path in tokens else ""
        narrow = token_value(tokens, path, narrow=True) if ("narrow",) + path in tokens else ""
        rows.append("| `%s` | %s | %s | %s | %s |"
                    % (".".join(path), kind, token_value(tokens, path), dark, narrow))
    return rows


def book_md(brand, plates, brief, status, kit=False, order=None):
    """brand-book.md; with kit, the same text for the kit in brand/out/ (export_kit.py): no
    frontmatter, no paths of plate files, the paths of the kit instead of those of brand/,
    and no word on where the working directory is (reference/contract.md, section 8)."""
    name = brand_name(plates, brief)
    by_name = {plate["name"]: plate for plate in plates}
    if kit:
        out = ["# Brand book: %s" % name, "",
               "Built by export_kit.py from the approved brand book. Never edit it; the brand is "
               "changed in the brand working directory %s, by the step that owns a line, "
               "and the book and the kit are built again."
               % ("of order `%s`" % order if order else "it was built from"), ""]
    else:
        out = ["---", "step: %s" % BOOK, "status: %s" % status, "source: generated", "---", "",
               "# Brand book: %s" % name, "",
               "Built by render_book.py from the approved plates. Never edit it; change the step "
               "that owns a line and build the book again.", ""]
    out += ["**Motto**: %s" % rp.one(by_name["motto.md"], "Motto"), "",
           "**In one line**: %s" % rp.one(brief, "In one line"), ""]
    for step, title in PARTS:
        out += ["## %s" % title, ""]
        headlines = [(plate, slot["name"]) for plate in plates if plate["step"] == step
                     for slot, _values in plate["slots"] if slot["headline"]]
        if headlines:
            out += ["### On one page", ""]
            out += ["- **%s**: %s" % (slot, rp.one(plate, slot)) for plate, slot in headlines]
            out.append("")
        for plate in plates:
            if plate["step"] == step:
                out += plate_md(plate, kit)
        if step == IDENTITY:
            surfaces = "surfaces/" if kit else "%s/surfaces/" % IDENTITY
            out += ["### Surfaces", ""]
            out += ["- `%s%s`" % (surfaces, s) for s in rp.list_surfaces(brand)]
            out.append("")
        if step == DESIGN:
            if kit:
                source = ("The source is `tokens/tokens.json`; `tokens/tokens.css` is generated "
                          "from it. Every component and page is in `system/index.html`.")
            else:
                source = ("The source is `%s/tokens.json`; `tokens.css` is generated from it. "
                          "Every component and page is in `%s/reference/index.html`."
                          % (DESIGN, DESIGN))
            out += ["### Tokens", "", source, ""]
            out += tokens_md(brand)
            out.append("")
    where = "this kit" if kit else "brand/"
    out += ["## How to use this", "", HOW_TO_USE, "", "| What | Path in %s |" % where, "|---|---|"]
    out += ["| %s | `%s` |" % (what, path) for what, path in (KIT_FILES if kit else FILES)]
    return "\n".join(out) + "\n"


# --- Build ---------------------------------------------------------------------


def print_pdf(chrome, page, output):
    output = os.path.abspath(output)

    def printed(_result=None):
        return os.path.isfile(output) and os.path.getsize(output) > 0
    if os.path.exists(output):
        os.remove(output)
    try:
        ss.run_chrome(chrome, ["--headless=new", "--disable-gpu", "--no-first-run",
                               "--no-default-browser-check", "--no-pdf-header-footer",
                               "--virtual-time-budget=8000", LIGHT[0],
                               "--print-to-pdf=%s" % output],
                      ss.target_url(page), printed)
    except (OSError, subprocess.TimeoutExpired) as error:
        return "Chrome did not print the PDF: %s" % error
    if not printed():
        return "Chrome wrote no PDF"
    return None


def overflowing_pages(chrome, page):
    """The pages of the printed book whose text does not fit, read from the DOM Chrome
    leaves after the fitting script ran. An empty list when Chrome cannot say."""
    try:
        result = ss.run_chrome(chrome, ["--headless=new", "--disable-gpu", "--no-first-run",
                                        "--no-default-browser-check",
                                        "--virtual-time-budget=8000", LIGHT[0], "--dump-dom"],
                               ss.target_url(page), lambda result: bool(result.stdout))
        return bp.overflowing(result.stdout.decode("utf-8", "replace"))
    except (OSError, subprocess.TimeoutExpired):
        return []


def screenshots_mode(brand):
    try:
        data = cc.parse_yaml(cc.read_lines(os.path.join(brand, "pipeline.yaml")))
        return data["tools"]["screenshots"]
    except (OSError, UnicodeDecodeError, cc.SubsetError, KeyError, TypeError):
        return "manual"


def build(brand, approve=False, pdf=True):
    """Build the book. Return ({name: path}, [notes]). Raise Problem."""
    plates, brief, board, look, skipped = load(brand)
    step_dir = os.path.join(brand, BOOK)
    review = os.path.join(step_dir, "review")
    shots_dir = os.path.join(review, "shots")
    notes = list(skipped)
    chrome = ss.find_chrome() if screenshots_mode(brand) == "headless-chrome" else None
    if chrome:
        take_shots(brand, chrome, shots_dir)
    else:
        missing = ["%s (%s, %d x %d)" % (name, os.path.relpath(page, brand), width, height)
                   for name, page, width, height, _caption in shot_list(brand)
                   if not os.path.isfile(os.path.join(shots_dir, name))]
        if missing:
            raise Problem("place these screenshots in %s/review/shots/, then run again: %s"
                          % (BOOK, "; ".join(missing)))
    page, count, paper, sheets = book_page(brand, plates, brief, board, look)
    bundled, problems = bh.bundle(page, review)
    if problems:
        raise Problem("; ".join(problems))
    written = {}
    rp.write(os.path.join(review, "source.html"), page)
    written["source"] = os.path.join(review, "source.html")
    # The printed book is a document of its own, with fixed pages; the PDF is made from it.
    rp.write(os.path.join(review, "print.html"), paper)
    written["print"] = os.path.join(review, "print.html")
    rp.write(os.path.join(step_dir, "index.html"), bundled)
    written["index"] = os.path.join(step_dir, "index.html")
    rp.write(os.path.join(step_dir, "brand-book.md"),
             book_md(brand, plates, brief, "approved" if approve else "draft"))
    written["markdown"] = os.path.join(step_dir, "brand-book.md")
    notes.append("%d numbered blocks" % count)
    if pdf and chrome:
        failure = print_pdf(chrome, written["print"], os.path.join(step_dir, "brand-book.pdf"))
        if failure:
            notes.append(failure + "; the book has no PDF")
        else:
            written["pdf"] = os.path.join(step_dir, "brand-book.pdf")
            notes.append("the PDF has %d pages" % sheets)
            over = overflowing_pages(chrome, written["print"])
            if over:
                notes.append("the text runs over on page %s of the PDF; shorten the slot in "
                             "its step, or report it" % ", ".join(map(str, over)))
    elif pdf:
        notes.append("no Chrome, so no PDF; record it in summary.md")
    return written, notes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the brand book.")
    parser.add_argument("brand", nargs="?", default="brand", help="path to brand/")
    parser.add_argument("--approve", action="store_true",
                        help="write brand-book.md with status: approved")
    parser.add_argument("--no-pdf", action="store_true", help="do not print the PDF")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.brand):
        print("%s is not a directory" % args.brand, file=sys.stderr)
        return 2
    try:
        written, notes = build(args.brand, args.approve, not args.no_pdf)
    except Problem as error:
        print("ERROR   %s" % error, file=sys.stderr)
        print("nothing was written", file=sys.stderr)
        return 1
    for key in written:
        print("%s: %s" % (key, written[key]))
    for note in notes:
        print("NOTE    %s" % note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
