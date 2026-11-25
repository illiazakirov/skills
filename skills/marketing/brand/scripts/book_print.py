#!/usr/bin/env python3
"""The printed brand book: a document of fixed pages, not the site sent to a printer.

render_book.py feeds a PrintBook the same blocks, in the same order and under the same
numbers, as the page it builds for the screen. The PrintBook lays them out on pages of one
size (PAGE_W x PAGE_H, a 16:9 sheet) from a small set of templates:

    cover, contents, part     the openers, on the brand's dark
    plate                     the spine (number, tool, headline) and the slots in columns;
                              what does not fit goes to a continuation page of the same shape
    canvas                    the Lean Canvas, as a canvas, on one page
    wall, identity, board     the one-page views and the board
    figure                    screenshots, one block a page
    how                       the fixed text and the table of files

Every page has the same frame: the brand and the part above, the block and the folio below.
A block never breaks inside a page: the pages are cut here, by an estimate of each slot's
height, and a script in the page shrinks the type of a page that still runs over (down to
FIT_MIN) and marks one that cannot be saved with data-overflow.
No dependencies beyond the Python 3 standard library.
"""

import html
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_plates as rp  # noqa: E402

PAGE_W, PAGE_H = 1280, 720
BODY_H = 572          # the height of a page's body, between the frame lines
CPL = 47              # characters on a line of a column of slots, at the base size
LINE = 18.5           # the height of that line
FIT_MIN = 0.72        # the least scale the fitting script goes to
FIT_STEPS = [1.15, 1.3, 1.45, 1.6]   # the larger sizes a part with room is tried at
WIDE = {"Tone", "Examples", "Palette"}   # slots drawn across the columns
NARROWEST = 500       # headless Chrome lays out no narrower


def e(text):
    return html.escape(text, quote=True)


def weight(slot, values):
    """The estimated height in px of a slot in a column of the plate template."""
    name = slot["name"]
    if name == "Tone":
        return 2 * (len(values) * 40 + 44)
    if name == "Examples":
        return 2 * (len(values) * 62 + 56)
    if name == "Palette":
        return 2 * 190
    lines = sum(max(1, math.ceil(len(value) / CPL)) for value in values)
    return 46 + lines * LINE + (len(values) - 1) * 6


def cut(cells, first, rest):
    """Cut [(weight, html)] into pages: the first holds `first` px of slots, the others `rest`."""
    pages, room = [[]], first
    for cost, content in cells:
        if pages[-1] and cost > room:
            pages.append([])
            room = rest
        pages[-1].append(content)
        room -= cost
    return pages


def wide_only(css):
    """The styles without their rules for narrow screens. Chrome answers a width query in
    print by the default paper, not by @page, so those rules would reach a 1280 px page."""
    out, at = [], 0
    for match in re.finditer(r"@media \(max-width:[^)]*\)\{", css):
        if match.start() < at:
            continue
        depth, index = 1, match.end()
        while depth and index < len(css):
            depth += {"{": 1, "}": -1}.get(css[index], 0)
            index += 1
        out.append(css[at:match.start()])
        at = index
    return "".join(out) + css[at:]


def scale(text):
    """The class of a headline by its length."""
    n = len(text)
    return "h-1" if n < 30 else "h-2" if n < 70 else "h-3" if n < 130 else "h-4" if n < 210 else "h-5"


STROKE = ('<svg class="stroke" viewBox="0 0 600 60" preserveAspectRatio="none" aria-hidden="true">'
          '<path d="M4 38C120 8 220 56 330 30S520 12 596 34"/></svg>')


class PrintBook:
    """Collects the blocks of the book and returns the document."""

    def __init__(self, name, identity, shots, has_logo):
        self.name, self.identity, self.shots, self.has_logo = name, identity, shots, has_logo
        self.pages = []       # {"kind", "part", "label", "number", "html"}
        self.number = 0
        self.part_title = ""
        self.parts = []       # [title, [(number, title, page index)]]

    # --- the frame ---

    def add(self, kind, content, label="", numbered=False, dark=False, fit=True):
        self.pages.append({"kind": kind, "part": self.part_title, "label": label, "dark": dark,
                           "number": self.number if numbered else 0, "html": content,
                           "fit": fit})

    def block(self, title):
        """Open a numbered block; return its number as two digits."""
        self.number += 1
        if self.parts:
            self.parts[-1][1].append((self.number, title, len(self.pages)))
        return "%02d" % self.number

    def spine(self, number, kicker, title, extra="", note=""):
        return ('<div class="spine"><p class="no">%s</p><p class="kicker">%s</p><h2>%s</h2>%s%s'
                "</div>" % (number, e(kicker), e(title),
                            '<p class="note">%s</p>' % e(note) if note else "", extra))

    # --- the openers ---

    def cover(self, motto, line):
        self.number += 1
        logo = ('<img class="logo" src="%slogo/dark.svg" alt="%s">' % (e(self.identity),
                                                                         e(self.name))
                if self.has_logo else '<p class="wordmark">%s</p>' % e(self.name))
        self.add("cover", '%s<div class="lines"><p class="motto">%s</p>%s<p class="line">%s</p>'
                          '</div><p class="what">%s<br>Brand book</p>'
                 % (logo, e(motto), STROKE, e(line), e(self.name)), dark=True, fit=False)
        self.add("contents", "", fit=False)     # filled when every page is known

    def part(self, title, index, total):
        self.part_title = title
        self.parts.append([title, []])
        self.add("part", (index, total, title), dark=True, fit=False)

    # --- the blocks ---

    def plate(self, plate, visual="", lead="", lead_weight=0):
        """visual stands in the spine; lead is drawn across the columns before the slots."""
        key = plate["name"][:-len(".md")]
        number = self.block(plate["title"])
        kicker = rp.KICKERS[plate["name"]]
        if key == "lean-canvas":
            return self.canvas(plate, number, kicker)
        headline, cells = "", []
        if lead:
            cells.append((2 * lead_weight, '<div class="slot wide lead">%s</div>' % lead))
        for slot, values in plate["slots"]:
            if slot["headline"]:
                headline = ('<div class="statement"><h3>%s</h3><p class="%s">%s</p></div>'
                            % (e(rp.LABELS.get(slot["name"], slot["name"])), scale(values[0]),
                               e(values[0])))
                continue
            wide = " wide" if slot["name"] in WIDE else ""
            cells.append((weight(slot, values),
                          rp.render_slot(slot, values).replace('class="slot ',
                                                               'class="slot%s ' % wide, 1)))
        pages = cut(cells, 0.95 * 2 * BODY_H, 0.95 * 3 * BODY_H)
        for index, page in enumerate(pages):
            if index == 0:
                side = self.spine(number, kicker, plate["title"],
                                  ('<div class="visual">%s</div>' % visual if visual else "")
                                  + headline)
                shape = "first"
            else:
                side = self.spine(number, kicker, plate["title"], note="continued")
                shape = "more"
            self.add("plate pg-%s %s" % (key, shape),
                     '%s<div class="cells">%s</div>' % (side, "".join(page)),
                     plate["title"], numbered=True)

    def canvas(self, plate, number, kicker):
        cells = "".join(
            rp.render_slot(slot, values).replace('class="slot ', 'class="slot a-%s ' % area, 1)
            for slot, values in plate["slots"]
            for area in [rp.slug(slot["name"])])
        self.add("canvas", '<div class="strip"><p class="no">%s</p><div><p class="kicker">%s</p>'
                           '<h2>%s</h2></div></div><div class="sheet-canvas">%s</div>'
                 % (number, e(kicker), e(plate["title"]), cells), plate["title"], numbered=True)

    def wall(self, title, kicker, rows):
        """A one-page view: rows is [(label, line)]."""
        number = self.block("%s on one page" % kicker)
        lines = "".join('<li><h3>%s</h3><p class="%s">%s</p></li>' % (e(label), scale(text), e(text))
                        for label, text in rows)
        self.add("wall", '%s<ul class="lines">%s</ul>' % (self.spine(number, kicker, title), lines),
                 "%s on one page" % kicker, numbered=True)

    def board(self, board, prefix, kicker):
        """The board, as pages of the block before it."""
        per = 8
        for start in range(0, len(board), per):
            tiles = "".join(
                '<figure><img src="%s%s" alt="%s"><figcaption>%s</figcaption></figure>'
                % (e(prefix), rp.rm.href(item["file"]), e(item["name"]), e(item["takes"]))
                for item in board[start:start + per])
            side = self.spine("%02d" % self.number, kicker, "The board",
                              note="continued" if start else "")
            self.add("board", '%s<div class="tiles">%s</div>' % (side, tiles),
                     "%s on one page" % kicker, numbered=True)

    def identity_page(self, body):
        number = self.block("Identity on one page")
        self.add("identity", '%s<div class="quad">%s</div>'
                 % (self.spine(number, "Identity", "On one page"), body),
                 "Identity on one page", numbered=True)

    def figure(self, title, kicker, images):
        """images: [(file under shots, caption, phone, size)]. size is the (width, height)
        the shot was made for, or None; a shot narrower than Chrome's least window carries a
        blank strip on its right, which is cut off."""
        number = self.block(title)

        def cut_to(size):
            if not size or size[0] >= NARROWEST:
                return ""
            return (' style="aspect-ratio:%d/%d;object-fit:cover;object-position:left top"'
                    % (size[0], size[1]))

        figures = "".join(
            '<figure class="%s"><img src="%s%s" alt="%s"%s><figcaption>%s</figcaption></figure>'
            % ("phone" if phone else "wide", e(self.shots), e(name), e(caption),
               "" if phone else cut_to(size), e(caption))
            for name, caption, phone, size in images)
        self.add("figure", '%s<div class="frames n-%d">%s</div>'
                 % (self.spine(number, kicker, title), len(images), figures), title,
                 numbered=True, fit=False)

    def how(self, prose_html, table_html):
        number = self.block("How to use this")
        self.add("how", '%s<div class="text">%s</div><div class="files-col">%s</div>'
                 % (self.spine(number, "Handover", "How to use this"), prose_html, table_html),
                 "How to use this", numbered=True)

    # --- the document ---

    def contents(self):
        columns = "".join(
            '<div><h3>%s</h3><ol>%s</ol></div>' % (e(title), "".join(
                '<li><span class="n">%02d</span><span class="t">%s</span><span class="p">%d</span>'
                "</li>" % (number, e(name), page + 1) for number, name, page in entries))
            for title, entries in self.parts)
        return ('<div class="spine"><p class="kicker">%s</p><h2>Contents</h2></div>'
                '<div class="toc">%s</div>' % (e(self.name), columns))

    def part_page(self, index, total, title):
        entries = next(found for name, found in self.parts if name == title)
        listing = "".join('<li><span class="n">%02d</span>%s</li>' % (number, e(name))
                          for number, name, _page in entries)
        return ('<p class="kicker">Part %d of %d</p><h2>%s</h2>%s<ol class="in-part">%s</ol>'
                % (index, total, e(title), STROKE, listing))

    def document(self, css, fonts_link):
        total = len(self.pages)
        out = []
        for index, page in enumerate(self.pages):
            content = page["html"]
            if page["kind"] == "contents":
                content = self.contents()
            elif page["kind"] == "part":
                content = self.part_page(*content)
            framed = page["kind"] not in ("cover", "part")
            logo = ('<img src="%slogo/full.svg" alt="">' % e(self.identity) if self.has_logo
                    else "")
            top = ('<header class="top">%s<span>%s</span><span class="where">%s</span></header>'
                   % (logo, "" if self.has_logo else e(self.name),
                      e(" / ".join(x for x in (page["part"], page["label"]) if x)))
                   if framed else "")
            foot = ('<footer class="foot"><span>%s</span><span>%s</span><span class="folio">'
                    "%d / %d</span></footer>"
                    % ("Brand book", ("Block %02d" % page["number"]) if page["number"] else "",
                       index + 1, total))
            out.append('<section class="pg pg-%s%s" data-page="%d">%s<div class="body%s">%s</div>'
                       "%s</section>" % (page["kind"], " dark" if page["dark"] else "",
                                         index + 1, top, " fit" if page["fit"] else "", content,
                                         foot))
        return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<title>%s: brand book, printed</title>%s<style>%s%s</style></head><body>%s%s"
                "</body></html>\n"
                % (e(self.name), fonts_link, wide_only(css), CSS, "".join(out), FIT_SCRIPT),
                total)


def overflowing(dom):
    """The numbers of the pages the fitting script could not save, from the DOM Chrome dumps."""
    return sorted(int(n) for n in re.findall(
        r'<section class="pg [^"]*" data-page="(\d+)" data-overflow="1"', dom))


# Each part of a page is fitted on its own: the headline of the spine does not hold back the
# slots beside it. A part with room is set larger, in steps, so the book keeps few type sizes.
FIT_SCRIPT = """<script>(function(){
var STEPS=%(steps)s;
function over(el){return el.scrollHeight>el.clientHeight+2||el.scrollWidth>el.clientWidth+2}
function fitPart(el){
var inner=[el].concat([].slice.call(el.querySelectorAll(':scope>.slot')));
function any(){return inner.some(over)}
function set(k){el.style.setProperty('--k',k.toFixed(2))}
var k=1;set(k);
if(any()){while(any()&&k>%(min)s){k-=.02;set(k)}return !any()}
for(var i=0;i<STEPS.length;i++){set(STEPS[i]);if(any())break;k=STEPS[i]}
set(k);return true}
function fit(){
[].forEach.call(document.querySelectorAll('.pg'),function(pg){
var body=pg.querySelector('.body.fit');if(!body)return;
var ok=true;
[].forEach.call(body.querySelectorAll(':scope>.spine,:scope>.cells,:scope>.sheet-canvas,:scope>.lines,:scope>.text,:scope>.files-col,:scope>.tiles'),function(el){ok=fitPart(el)&&ok});
if(ok&&!over(body))pg.removeAttribute('data-overflow');else pg.setAttribute('data-overflow','1');
})}
if(document.fonts&&document.fonts.ready){document.fonts.ready.then(fit)}else{fit()}
addEventListener('load',fit);
})()</script>""" % {"min": FIT_MIN, "steps": FIT_STEPS}

CSS = """
/* --- The printed book: fixed pages --- */
@page{size:%(w)dpx %(h)dpx;margin:0}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:#8a8a90;font-size:13px}
main{all:unset}
.pg{position:relative;width:%(w)dpx;height:%(h)dpx;overflow:hidden;background:var(--paper);color:var(--ink);break-after:page;break-inside:avoid;margin:0 auto}
.pg.dark{background:var(--dark);color:var(--on-dark);--ink:var(--on-dark);--paper:var(--dark);--muted:color-mix(in srgb,var(--dark) 38%%,var(--on-dark));--line:color-mix(in srgb,var(--dark) 80%%,var(--on-dark))}
@media screen{.pg{margin:24px auto;box-shadow:0 6px 30px rgba(0,0,0,.35)}}
.pg h2,.pg h3,.pg p,.pg ul,.pg ol,.pg figure{margin:0;padding:0}
.pg ul,.pg ol{list-style:none}
.pg .kicker,.pg h3,.top,.foot,.pg figcaption,.pg .note{font-family:var(--text);font-weight:600;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.top,.foot{position:absolute;left:44px;right:44px;display:flex;align-items:center;gap:16px}
.top{top:26px;padding-bottom:12px;border-bottom:1px solid var(--line)}
.top img{height:13px;width:auto;display:block}
.top .where{margin-left:auto}
.foot{bottom:24px;padding-top:12px;border-top:1px solid var(--line)}
.foot .folio{margin-left:auto;color:var(--ink)}
.pg.dark .foot{border-top-color:var(--line)}
.body{position:absolute;left:44px;right:44px;top:74px;height:%(body)dpx;display:grid;grid-template-columns:repeat(12,1fr);column-gap:24px;align-content:start}
.body>*{--k:1;min-width:0;max-height:%(body)dpx}

/* The spine: what block this is, and its headline */
.spine{grid-column:span 4;display:flex;flex-direction:column;height:%(body)dpx;overflow:hidden}
.spine .no{font-family:var(--display);font-size:56px;line-height:.9;letter-spacing:-.03em;color:var(--accent)}
.spine .kicker{margin-top:18px}
.spine h2{font-family:var(--display);font-weight:400;font-size:28px;line-height:1.08;letter-spacing:-.015em;margin-top:4px}
.spine .note{margin-top:8px}
.spine .visual{margin-top:20px;max-width:230px}
.spine .visual .rings{max-width:150px;margin:0}
.spine .visual .wheel{max-width:230px;margin:0}
.spine .visual .hub p{font-size:10px}
.spine .visual .segment text{font-size:11px}
.spine .visual .sheet>div{padding:16px 12px}
.spine .visual .sheet .sizes{gap:18px;padding:12px}
.spine .visual .sheet .sizes img{max-height:28px}
.spine .visual .sheet .full img{max-height:44px}
.statement{margin-top:auto;padding:20px 0 8px;border-top:2px solid var(--ink)}
.statement p,.lines p{font-family:var(--display);letter-spacing:-.02em;line-height:1.06;text-wrap:balance}
.statement h3{margin-bottom:10px}
.h-1{font-size:calc(58px*var(--k))}
.h-2{font-size:calc(40px*var(--k))}
.h-3{font-size:calc(30px*var(--k))}
.h-4{font-size:calc(24px*var(--k))}
.h-5{font-size:calc(20px*var(--k));line-height:1.12}

/* The slots of a plate, in columns */
.cells{grid-column:span 8;height:%(body)dpx;columns:2;column-gap:28px;column-fill:balance;overflow:hidden}
.pg-plate.more .spine{grid-column:span 3}
.pg-plate.more .cells{grid-column:span 9;columns:3}
.pg .slot{background:none;border:0;border-top:1px solid var(--line);padding:calc(13px*var(--k)) 0 calc(15px*var(--k));break-inside:avoid;min-width:0}
.pg .slot h3{margin-bottom:calc(8px*var(--k))}
.pg .slot p,.pg .slot li{font-size:calc(13px*var(--k));line-height:1.42}
.pg .slot li+li{margin-top:calc(6px*var(--k))}
.pg .slot li{padding-left:13px;position:relative}
.pg .slot li:before{content:"";position:absolute;left:0;top:.66em;width:6px;height:1px;background:var(--muted)}
.pg .slot b{font-weight:600}
.pg .slot .q{font-style:italic;color:var(--muted);display:block;margin-bottom:2px}
.pg .slot.wide{column-span:all}
.pg .scale{grid-template-columns:86px minmax(90px,170px) 86px 1fr;gap:12px;padding:calc(7px*var(--k)) 0}
.pg .scale .pole,.pg .scale p{font-size:calc(12px*var(--k))}
.pg .scale .track i{top:-5px;width:11px;height:11px;margin-left:-5.5px}
.pg .examples{grid-template-columns:minmax(90px,.8fr) 2fr 2fr;gap:0 20px}
.pg .examples>*{padding:calc(7px*var(--k)) 0;font-size:calc(12px*var(--k));line-height:1.36}
.pg .examples .situation{font-size:calc(11px*var(--k))}
.pg .swatches{grid-template-columns:repeat(6,1fr);gap:12px}
.pg .swatches li{padding:0;font-size:calc(11px*var(--k))}
.pg .swatches li:before{display:none}
.pg .swatches li+li{margin-top:0}
.pg .swatches i{height:64px;margin-bottom:8px}
.pg .swatches b{font-size:calc(16px*var(--k))}
.pg .swatches code{font-family:var(--text);font-weight:600;font-size:calc(10.5px*var(--k))}
.pg .slot.lead{border-top:0;padding-top:0}
.pg .specimen{border:0;background:none;padding:0}
.pg .specimen .display{font-size:calc(72px*var(--k));line-height:.95;letter-spacing:-.03em}
.pg .specimen .text{font-size:calc(15px*var(--k));margin-top:10px}
.pg .specimen .kicker{margin:14px 0 6px}
.pg-archetype .slot-primary-archetype p,.pg-archetype .slot-secondary-archetype p,.pg-mood .slot-mood-words li{font-family:var(--display);font-size:calc(24px*var(--k));line-height:1.1}
.pg-mood .slot-mood-words li{padding:0}
.pg-mood .slot-mood-words li:before{display:none}

/* The Lean Canvas, as a canvas */
.pg-canvas .body{display:block}
.strip{display:flex;align-items:center;gap:18px;height:60px}
.strip .no{font-family:var(--display);font-size:56px;line-height:.9;letter-spacing:-.03em;color:var(--accent)}
.strip h2{font-family:var(--display);font-weight:400;font-size:26px;line-height:1.08;letter-spacing:-.015em;margin-top:2px}
.sheet-canvas{--k:1;height:%(canvas)dpx;margin-top:12px;display:grid;gap:0;grid-template-columns:repeat(10,1fr);grid-template-rows:1fr 1fr auto;border:1px solid var(--ink);overflow:hidden;grid-template-areas:"problem problem solution solution unique-value-proposition unique-value-proposition unfair-advantage unfair-advantage customer-segments customer-segments" "existing-alternatives existing-alternatives key-metrics key-metrics unique-value-proposition unique-value-proposition channels channels early-adopter early-adopter" "cost-structure cost-structure cost-structure cost-structure cost-structure revenue-streams revenue-streams revenue-streams revenue-streams revenue-streams"}
.sheet-canvas .slot{border:0;box-shadow:0 0 0 .5px var(--ink);padding:calc(12px*var(--k)) calc(14px*var(--k));overflow:hidden}
.sheet-canvas .slot p,.sheet-canvas .slot li{font-size:calc(11.5px*var(--k));line-height:1.36}
.sheet-canvas .a-problem{grid-area:problem}.sheet-canvas .a-solution{grid-area:solution}
.sheet-canvas .a-unique-value-proposition{grid-area:unique-value-proposition;display:flex;flex-direction:column;justify-content:center;background:color-mix(in srgb,var(--paper) 90%%,var(--accent))}
.sheet-canvas .a-unique-value-proposition p{font-family:var(--display);font-size:calc(19px*var(--k));line-height:1.08;letter-spacing:-.015em;hyphens:auto}
.sheet-canvas .a-unfair-advantage{grid-area:unfair-advantage}.sheet-canvas .a-customer-segments{grid-area:customer-segments}
.sheet-canvas .a-existing-alternatives{grid-area:existing-alternatives}.sheet-canvas .a-key-metrics{grid-area:key-metrics}
.sheet-canvas .a-channels{grid-area:channels}.sheet-canvas .a-early-adopter{grid-area:early-adopter}
.sheet-canvas .a-cost-structure{grid-area:cost-structure}.sheet-canvas .a-revenue-streams{grid-area:revenue-streams}

/* The one-page views */
.pg-wall .spine,.pg-identity .spine,.pg-board .spine,.pg-figure .spine,.pg-how .spine,.pg-contents .spine{grid-column:span 3}
.pg-wall .lines{grid-column:span 9;height:%(body)dpx;columns:2;column-gap:28px;column-fill:balance;overflow:hidden}
.pg-wall .lines li{break-inside:avoid;padding:calc(14px*var(--k)) 0 calc(18px*var(--k));border-top:1px solid var(--line)}
.pg-wall .lines h3{margin-bottom:8px}
.pg-wall .lines .h-1{font-size:calc(40px*var(--k))}
.pg-wall .lines .h-2{font-size:calc(28px*var(--k))}
.pg-wall .lines .h-3{font-size:calc(21px*var(--k))}
.pg-wall .lines .h-4{font-size:calc(17px*var(--k));line-height:1.14}
.pg-wall .lines .h-5{font-size:calc(15px*var(--k));line-height:1.18}
.quad{grid-column:span 9;height:%(body)dpx;overflow:hidden}
.quad .onepage{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:0 28px;height:100%%;border:0}
.quad .onepage>li{padding:16px 0;border-top:1px solid var(--line);min-height:0;overflow:hidden;display:flex;flex-direction:column;justify-content:flex-end}
.quad .onepage>li>p{font-family:var(--display);font-size:22px;line-height:1.1;letter-spacing:-.015em;max-width:none}
.quad .onepage>li>.kicker{display:block;margin:10px 0 6px}
.quad .onepage img,.quad .onepage picture img{max-height:72px;max-width:80%%;width:auto;height:auto;margin:0 0 auto}
.quad .swatches{margin:0 0 auto}
.quad .swatches{gap:8px;width:100%%}
.quad .swatches i{height:56px}
.quad .swatches b{font-family:var(--text);font-weight:600;font-size:10.5px;line-height:1.2}
.quad .swatches code{font-weight:400;font-size:9.5px}
.quad .swatches span{display:none}
.quad .specimen{border:0;background:none;padding:0;margin:0 0 auto}
.pg .quad .onepage.identity .specimen .display{font-size:34px;line-height:1;letter-spacing:-.02em}
.quad .specimen .text,.quad .specimen .kicker{display:none}
.quad .onepage>li.motto>p{font-size:48px;line-height:1}
.tiles{grid-column:span 9;height:%(body)dpx;display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:1fr 1fr;gap:18px 20px;overflow:hidden}
.tiles figure{min-height:0;display:flex;flex-direction:column}
.tiles img{display:block;width:100%%;height:150px;object-fit:cover;border:1px solid var(--line)}
.tiles img[src$=".svg"],.tiles img[src^="data:image/svg"]{object-fit:contain;background:var(--light);padding:14px;box-sizing:border-box}
.tiles figcaption{font-weight:400;font-size:calc(10.5px*var(--k));letter-spacing:0;text-transform:none;line-height:1.36;margin-top:8px;color:var(--ink)}

/* Screenshots */
.frames{grid-column:span 9;height:%(body)dpx;box-sizing:border-box;display:flex;gap:28px;align-items:center;justify-content:center;padding:26px;background:var(--card);border:1px solid var(--line)}
.frames figure{display:flex;flex-direction:column;min-width:0;max-height:100%%}
.frames img{display:block;max-width:100%%;max-height:%(shot)dpx;box-shadow:0 1px 0 var(--line);width:auto;height:auto;object-fit:contain;border:1px solid var(--line);background:var(--light)}
.frames figcaption{margin-top:10px}
.frames .phone{flex:none}
.frames .phone img{height:%(shot)dpx;max-width:none;aspect-ratio:390/844;object-fit:cover;object-position:left top}
.frames.n-2 .wide{flex:1 1 0}
.frames.n-2 .phone img{height:440px}
.frames.n-2 .wide img{max-height:440px}

/* How to use this */
.pg-how .text{grid-column:span 5;height:%(body)dpx;overflow:hidden}
.pg-how .text p,.pg-how .text li{font-size:calc(13.5px*var(--k));line-height:1.45}
.pg-how .text p+p,.pg-how .text p+ul,.pg-how .text ul+p{margin-top:calc(12px*var(--k))}
.pg-how .text ul{list-style:disc;padding-left:18px}
.pg-how .text code,.pg-how .files code{font-family:var(--text);font-weight:600;font-size:.92em}
.pg-how .files-col{grid-column:span 4;height:%(body)dpx;overflow:hidden}
.pg-how .files{width:100%%;border-collapse:collapse;margin:0}
.pg-how .files td,.pg-how .files th{text-align:left;padding:calc(8px*var(--k)) 10px calc(8px*var(--k)) 0;border-top:1px solid var(--line);vertical-align:top;font-size:calc(11.5px*var(--k));line-height:1.36;overflow-wrap:anywhere}
.pg-how .files th{font-weight:600;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}

/* The openers */
.stroke{display:block;overflow:visible}
.stroke path{fill:none;stroke:var(--accent);stroke-width:5;stroke-linecap:round;vector-effect:non-scaling-stroke}
.pg-cover .body,.pg-part .body{top:56px;height:%(open)dpx;display:flex;flex-direction:column}
.pg-cover .logo{height:44px;width:auto;align-self:flex-start}
.pg-cover .wordmark{font-family:var(--display);font-size:44px}
.pg-cover .lines{margin-top:auto}
.pg-cover .motto{font-family:var(--display);font-size:104px;line-height:.94;letter-spacing:-.035em;max-width:11em;text-wrap:balance}
.pg-cover .stroke{width:420px;height:34px;margin:14px 0 26px}
.pg-cover .line{font-size:20px;line-height:1.35;max-width:30em;color:var(--muted)}
.pg-cover .what{position:absolute;right:0;top:0;text-align:right;font-family:var(--text);font-weight:600;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;line-height:1.7;color:var(--muted)}
.pg-part .body{justify-content:flex-end}
.pg-part h2{font-family:var(--display);font-weight:400;font-size:150px;line-height:.9;letter-spacing:-.04em;margin-top:10px}
.pg-part .stroke{width:520px;height:40px;margin-top:18px}
.pg-part .in-part{position:absolute;right:0;top:0;width:300px}
.pg-part .in-part li{display:flex;gap:14px;padding:7px 0;border-top:1px solid var(--line);font-size:13px}
.pg-part .n,.toc .n{font-family:var(--text);font-weight:600;color:var(--accent);min-width:22px}
.toc{grid-column:span 9;height:%(body)dpx;display:grid;grid-template-columns:repeat(5,1fr);gap:0 20px;overflow:hidden;align-content:start}
.toc h3{color:var(--ink);padding-bottom:10px;border-bottom:2px solid var(--ink)}
.toc li{display:flex;gap:8px;padding:7px 0;border-bottom:1px solid var(--line);font-size:11.5px;line-height:1.3}
.toc .t{flex:1;min-width:0}
.toc .p{color:var(--muted)}
.pg[data-overflow]{outline:3px solid #e00;outline-offset:-3px}
@media print{body{background:none}.pg{margin:0;box-shadow:none}.pg[data-overflow]{outline:0}}
""" % {"w": PAGE_W, "h": PAGE_H, "body": BODY_H, "canvas": BODY_H - 72, "shot": BODY_H - 84,
       "open": PAGE_H - 56 - 64}
