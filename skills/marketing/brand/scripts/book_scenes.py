#!/usr/bin/env python3
"""The scenes of the brand book: every plate set as a world of its own.

render_book.py asks scene() for each plate. A scene takes the slots of the plate, word for
word, and sets them in the shape of its tool: the Golden Circle is travelled from the core
outwards, the Lean Canvas assembles from panes of glass, the Positioning runs sideways, the
Marketing Mix stacks like a deck. A plate without a scene of its own, or one whose slots do
not fit, is wrapped as it is drawn on the brand map (wrap()), on glass over its own light.

Motion is an addition: without JavaScript, with reduced motion and in print every scene is
a plain page with everything on it. All motion rules sit under `.motion` in `@media screen`.
No dependencies beyond the Python 3 standard library.
"""

import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_plates as rp  # noqa: E402


def e(text):
    return html.escape(text, quote=True)


def slots_of(plate):
    return {slot["name"]: values for slot, values in plate["slots"]}


def items(values, show=e):
    return "<ul>%s</ul>" % "".join("<li>%s</li>" % show(value) for value in values)


def size(text):
    """A class for a display line by its length, so a long line does not fill the screen."""
    return "s-xl" if len(text) < 34 else "s-l" if len(text) < 80 else "s-m"


def head(plate):
    return ('<header class="sc-head"><p class="kicker">%s</p><h2>%s</h2></header>'
            % (e(rp.KICKERS[plate["name"]]), e(plate["title"])))


def pane(label, body, extra="", style=""):
    return ('<div class="pane glass %s"%s><h3>%s</h3>%s</div>'
            % (extra, ' style="%s"' % style if style else "", e(label), body))


def labelled(value):
    """'Label: text' -> (label, text); a line without a label has an empty one."""
    label, mark, text = value.partition(": ")
    return (label, text) if mark and len(label) <= 60 else ("", value)


STROKE = ('<svg class="stroke" viewBox="0 0 600 60" preserveAspectRatio="none" aria-hidden="true">'
          '<path pathLength="1" d="M4 38C120 8 220 56 330 30S520 12 596 34"/></svg>')


def light(x, y, w, depth, strength=55):
    """A soft light of the accent color behind the glass; depth is its parallax in px."""
    return ('<i class="light" data-d style="left:%s;top:%s;width:%s;--d:%dpx;--s:%d%%"></i>'
            % (x, y, w, depth, strength))


def section(key, world, body, backdrop="", attrs=""):
    return ('<section class="scene w-%s" id="%s"%s><div class="bg" aria-hidden="true">%s</div>'
            "%s</section>" % (world, key, " " + attrs if attrs else "", backdrop, body))


# --- Strategy ------------------------------------------------------------------


def golden_circle(plate, s):
    orbits = ('<svg class="orbits" viewBox="-500 -500 1000 1000"><circle class="o-what" r="480"/>'
              '<circle class="o-how" r="300"/><circle class="o-why" r="130"/></svg>')
    steps = "".join(
        '<div class="step glass"><h3>%s</h3>%s</div>' % (label, body) for label, body in (
            ("WHY", '<p class="display %s">%s</p>' % (size(s["Why"][0]), e(s["Why"][0]))),
            ("HOW", items(s["How"])),
            ("WHAT", '<p class="display s-m">%s</p>' % e(s["What"][0]))))
    rail = '<ol class="rail" aria-hidden="true"><li>Why</li><li>How</li><li>What</li></ol>'
    return section("golden-circle", "core",
                   '<div class="pin">%s%s<div class="steps">%s</div>%s</div>'
                   % (orbits, head(plate), steps, rail), attrs='data-steps="3"')


def lean_canvas(plate, s):
    order = (("Problem", "problem", -220, -90, -5), ("Solution", "solution", -60, -260, 4),
             ("Unique value proposition", "uvp", 0, 140, 0),
             ("Unfair advantage", "unfair", 90, -240, -3),
             ("Customer segments", "segments", 240, -70, 5),
             ("Existing alternatives", "alternatives", -260, 110, 3),
             ("Key metrics", "metrics", -90, 230, -4), ("Channels", "channels", 110, 250, 3),
             ("Early adopter", "adopter", 260, 130, -5),
             ("Cost structure", "cost", -180, 300, 2), ("Revenue streams", "revenue", 180, 320, -2))
    kinds = {slot["name"]: slot["kind"] for slot, _values in plate["slots"]}
    panes = []
    for name, area, x, y, turn in order:
        values = s[name]
        body = (items(values) if kinds[name] == "list" else
                '<p class="%s">%s</p>' % ("display " + size(values[0]) if area == "uvp" else "",
                                          e(values[0])))
        panes.append(pane(name, body, "a-" + area,
                          "grid-area:%s;--x:%dpx;--y:%dpx;--r:%ddeg" % (area, x, y, turn)))
    backdrop = '<i class="grid" data-d style="--d:60px"></i>' + light("38%", "30%", "46vw", -90)
    return section("lean-canvas", "canvas",
                   '%s<div class="canvas">%s</div>' % (head(plate), "".join(panes)), backdrop)


def icp(plate, s):
    path = "".join('<li class="rise"><h3>%s</h3><p>%s</p></li>' % (e(name), e(s[name][0]))
                   for name in ("Situation", "Trigger", "Tried before", "Where to find"))
    jobs = "".join(pane(name, "<p>%s</p>" % e(s[name][0]), "rise")
                   for name in ("Functional", "Emotional", "Social"))
    others = ""
    if s.get("Other customers"):
        others = ('<div class="others"><h3>Other customers</h3>%s</div>'
                  % items(s["Other customers"], rp.rich))
    body = ('%s<div class="who"><div class="who-line"><h3>Who</h3><p class="display %s">%s</p>'
            '</div><ol class="path">%s</ol></div>'
            '<blockquote class="job"><h3>Main job</h3><p class="display %s">%s</p>%s</blockquote>'
            '<div class="jobs">%s</div>%s'
            % (head(plate), size(s["Who"][0]), e(s["Who"][0]), path,
               size(s["Main job"][0]), e(s["Main job"][0]), STROKE, jobs, others))
    return section("icp", "person", body, light("-12%", "6%", "60vw", -120, 40))


def positioning(plate, s):
    panels = "".join(
        '<div class="panel p-%s"><h3>%s</h3>%s</div>' % (kind, e(name), items(s[name]))
        for name, kind in (("Competitive alternatives", "them"), ("Unique attributes", "only"),
                           ("Value", "value")))
    statement = s["Positioning statement"][0]
    body = ('<div class="run"><div class="pin">%s<div class="track">%s</div>'
            '<i class="axis" aria-hidden="true"></i></div></div>'
            '<div class="landing"><p class="display %s">%s</p><dl><div><dt>Target segment</dt>'
            "<dd>%s</dd></div><div><dt>Market category</dt><dd>%s</dd></div></dl></div>"
            % (head(plate), panels, size(statement), e(statement), e(s["Target segment"][0]),
               e(s["Market category"][0])))
    return section("positioning", "field", body, light("60%", "50%", "50vw", -140, 45))


def brand_wheel(plate, s):
    rings = ('<svg class="spin" viewBox="-500 -500 1000 1000" aria-hidden="true">'
             '<circle r="470"/><circle class="dash" r="380"/><circle r="250"/>%s</svg>'
             % "".join('<line x1="0" y1="-470" x2="0" y2="-440" transform="rotate(%d)"/>' % a
                       for a in range(0, 360, 15)))
    quarter = lambda name, area: pane(name, items(s[name]), "rise", "grid-area:" + area)  # noqa: E731
    traits = "".join("<li><b>%s</b><span>%s</span></li>" % (e(label or text), e(text if label else ""))
                     for label, text in map(labelled, s["Personality"]))
    essence = s["Essence"][0]
    body = ('%s<div class="wheel-grid">%s%s<div class="essence" style="grid-area:core">%s'
            '<div class="disc"><h3>Essence</h3><p class="display">%s</p></div></div>%s%s</div>'
            '<div class="traits"><h3>Personality</h3><ul data-focus>%s</ul></div>'
            % (head(plate), quarter("Attributes", "a"), quarter("Values", "c"), rings,
               e(essence), quarter("Functional benefits", "b"),
               quarter("Emotional benefits", "d"), traits))
    return section("brand-wheel", "orbit", body)


def marketing_mix(plate, s):
    bands = "".join(
        '<li class="band glass" style="--i:%d"><b>%s</b><p>%s</p></li>'
        % (index, e(slot["name"]), e(values[0]))
        for index, (slot, values) in enumerate(plate["slots"]))
    backdrop = light("55%", "20%", "44vw", -160) + light("5%", "62%", "36vw", 120, 35)
    return section("marketing-mix", "stack",
                   '%s<ol class="bands">%s</ol>' % (head(plate), bands), backdrop)


def messaging(plate, s):
    promise = s["Main promise"][0]
    proofs = "".join('<li class="rise"><b>%s</b><span>%s</span></li>'
                     % (e(label or text), e(text if label else ""))
                     for label, text in map(labelled, s["Proofs"]))
    talk = []
    for value in s["Objections"]:
        quoted = re.fullmatch(r'("[^"]+")\s+(.+)', value)
        if quoted:
            talk.append('<li><p class="ask glass rise from-l">%s</p><p class="answer rise from-r">'
                        "%s</p></li>" % (e(quoted.group(1)), e(quoted.group(2))))
        else:
            talk.append('<li><p class="answer rise">%s</p></li>' % e(value))
    body = ('%s<div class="promise"><h3>Main promise</h3><p class="display %s">%s</p>%s</div>'
            '<div class="proofs"><h3>Proofs</h3><ul>%s</ul></div>'
            '<div class="talk"><h3>Objections</h3><ol>%s</ol></div>'
            % (head(plate), size(promise), e(promise), STROKE, proofs, "".join(talk)))
    return section("messaging", "promise", body, light("20%", "8%", "60vw", -110, 50))


# --- Brand platform and identity -------------------------------------------------


def mood(plate, s):
    words = "".join('<li data-d style="--d:%dpx">%s</li>' % (depth, e(word))
                    for word, depth in zip(s["Mood words"], (-70, 40, -30, 60, -50, 30)))
    body = ('%s<div class="territory"><h3>Territory</h3><p class="display s-xl">%s</p>%s</div>'
            '<ul class="words" aria-label="Mood words">%s</ul><div class="pair">%s%s</div>'
            % (head(plate), e(s["Territory"][0]), STROKE, words,
               pane("Takes", items(s["Takes"]), "rise"),
               pane("Excludes", items(s["Excludes"]), "rise")))
    return section("mood", "mood", body, light("50%", "0%", "70vw", -140, 60))


def readable(hexa):
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return "#000000" if 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b) > 0.3 else "#FFFFFF"


def color(plate, s):
    bands = []
    for value in s["Palette"]:
        match = re.fullmatch(r"(.+?) - (#[0-9A-Fa-f]{6}) - (.+)", value)
        if not match:
            raise ValueError(value)
        name, hexa, role = match.groups()
        bands.append('<li style="--c:%s;color:%s"><b>%s</b><code>%s</code><span>%s</span>'
                     "</li>" % (hexa, readable(hexa), e(name), hexa.upper(), e(role)))
    idea = s["Color idea"][0]
    body = ('%s<div class="idea"><h3>Color idea</h3><p class="display %s">%s</p></div>'
            '<ul class="chroma" aria-label="Palette">%s</ul><div class="pair">%s%s</div>%s'
            % (head(plate), size(idea), e(idea), "".join(bands),
               pane("Accent is for", "<p>%s</p>" % e(s["Accent is for"][0]), "rise"),
               pane("Accent is never for", "<p>%s</p>" % e(s["Accent is never for"][0]), "rise"),
               pane("Contrast", items(s["Contrast"], rp.rich), "wide rise")))
    return section("color", "chroma", body)


def motto(plate, s):
    line = s["Motto"][0]
    rejected = ""
    if s.get("Rejected"):
        rejected = '<div class="rejected"><h3>Rejected</h3>%s</div>' % items(s["Rejected"])
    body = ('%s<div class="line"><h3>Motto</h3><p class="display s-xl">%s</p>%s</div>'
            '<div class="pair">%s%s</div>%s'
            % (head(plate), e(line), STROKE,
               pane("What it says", "<p>%s</p>" % e(s["What it says"][0]), "rise"),
               pane("Where it stands", "<p>%s</p>" % e(s["Where it stands"][0]), "rise"),
               rejected))
    return section("motto", "motto", body, light("30%", "0%", "60vw", -120, 55))


SCENES = {"golden-circle": golden_circle, "lean-canvas": lean_canvas, "icp": icp,
          "positioning": positioning, "brand-wheel": brand_wheel,
          "marketing-mix": marketing_mix, "messaging": messaging, "mood": mood,
          "color": color, "motto": motto}


def scene(plate):
    """The scene of a plate, or None when it has none or its slots do not fit one."""
    key = plate["name"][:-len(".md")]
    if key not in SCENES:
        return None
    try:
        return SCENES[key](plate, slots_of(plate))
    except (KeyError, IndexError, ValueError):
        return None


def wrap(key, content, lights=1):
    """A block drawn elsewhere (a plate of the map, a one-page view), on glass over a light."""
    backdrop = light("58%", "4%", "52vw", -130) if lights else ""
    return ('<div class="scene w-plain w-%s"><div class="bg" aria-hidden="true">%s</div>%s</div>'
            % (key, backdrop, content))


def wall(key, kicker, title, rows_html, after=""):
    """A one-page view: the headline lines of a step, the one in the middle of the screen
    lit. rows_html is the <ul class="onepage"> of render_plates."""
    rows_html = rows_html.replace('<ul class="onepage', '<ul data-focus class="onepage', 1)
    return ('<section class="scene w-wall" id="%s"><div class="bg" aria-hidden="true">%s</div>'
            '<header class="sc-head"><p class="kicker">%s</p><h2>%s</h2></header>%s%s</section>'
            % (key, light("-10%", "20%", "50vw", -150, 40), e(kicker), e(title), rows_html,
               after))


def board_wall(board, prefix):
    """The board as three columns that move at three speeds."""
    if not board:
        return ""
    columns = [[], [], []]
    for index, item in enumerate(board):
        columns[index % 3].append(
            '<figure class="glass"><img src="%s%s" alt="%s" loading="lazy"><figcaption>%s'
            "</figcaption></figure>" % (e(prefix), rp.rm.href(item["file"]), e(item["name"]),
                                        e(item["takes"])))
    return '<div class="board-wall">%s</div>' % "".join(
        '<div data-d style="--d:%dpx">%s</div>' % (depth, "".join(column))
        for column, depth in zip(columns, (-50, 50, -110)))


def chapter(step, title, index, total):
    """The opening of a part: its name across the screen."""
    return ('<div class="scene w-part"><div class="bg" aria-hidden="true">%s</div>'
            '<p class="kicker">Part %d of %d</p><h2 class="part" id="%s">%s</h2>%s</div>'
            % (light("50%", "30%", "60vw", -180, 50), index, total, step, e(title), STROKE))


CSS = """
/* --- The scenes of the book --- */
html{overflow-x:clip}
:root{--glass:color-mix(in srgb,var(--paper) 58%,transparent);--glass-line:color-mix(in srgb,var(--ink) 13%,transparent);--dim:color-mix(in srgb,var(--paper) 55%,var(--ink))}
.kicker,.slot h3,.scene h3,.scene dt{font-family:var(--text);font-weight:600;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.scene{position:relative;margin:0 calc(50% - 50vw);padding:120px calc(50vw - 50%);overflow:clip;background:var(--paper)}
.scene>*{position:relative}
.scene>.bg{position:absolute;inset:0;overflow:hidden;pointer-events:none}
.scene h3{margin-bottom:14px}
.scene ul,.scene ol{list-style:none;margin:0;padding:0}
.block:has(>.scene)>.num,.block:has(>.scene)>.num{z-index:3;top:120px;background:var(--glass);backdrop-filter:blur(12px)}
.glass{background:var(--glass);-webkit-backdrop-filter:blur(22px) saturate(1.35);backdrop-filter:blur(22px) saturate(1.35);border:1px solid var(--glass-line);border-radius:8px}
.light{position:absolute;aspect-ratio:1;border-radius:50%;background:radial-gradient(closest-side,color-mix(in srgb,var(--accent) var(--s,55%),transparent),transparent);filter:blur(24px)}
.stroke{display:block;width:min(100%,560px);height:34px;margin-top:10px;overflow:visible}
.stroke path{fill:none;stroke:var(--accent);stroke-width:5;stroke-linecap:round;vector-effect:non-scaling-stroke;stroke-dasharray:1;stroke-dashoffset:0}
.sc-head{margin-bottom:56px}
.sc-head h2{font-family:var(--display);font-weight:400;font-size:44px;line-height:1.05;letter-spacing:-.01em}
.display{font-family:var(--display);letter-spacing:-.02em;line-height:1.04;text-wrap:balance}
.s-xl{font-size:clamp(52px,9.4vw,148px)}
.s-l{font-size:clamp(36px,5.2vw,84px)}
.s-m{font-size:clamp(28px,3.3vw,50px);line-height:1.12}
.pane{padding:24px 26px;min-width:0}
.pane p,.pane li{font-size:17px;line-height:1.4}
.pane li+li{margin-top:9px}
.pane li{padding-left:16px;position:relative}
.pane li:before{content:"";position:absolute;left:0;top:.62em;width:6px;height:1px;background:var(--muted)}
.pane b{font-weight:600}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:56px}
.pair .wide,.pair+.pane{grid-column:1/-1}
.pair+.pane{margin-top:20px}

/* The part openers */
.w-part{min-height:92vh;display:flex;flex-direction:column;justify-content:center;background:color-mix(in srgb,var(--paper) 94%,var(--ink))}
.w-part .part{border:0;margin:14px 0 0;padding:0;font-size:clamp(64px,13vw,210px);line-height:.92;letter-spacing:-.035em}
.w-part .stroke{width:min(70%,820px);height:48px;margin-top:22px}

/* The cover */
.w-cover{min-height:100vh;display:flex;flex-direction:column;justify-content:center}
.w-cover .cover{min-height:0;margin:0;position:relative}
.w-cover .contents{margin:72px 0 0}

/* One page: the wall of headlines */
.w-wall .onepage{border:0}
.w-wall .onepage>li{padding:44px 0;border-top:1px solid var(--glass-line)}
.w-wall .onepage>li>p{font-family:var(--display);font-size:clamp(30px,4.4vw,68px);line-height:1.06;letter-spacing:-.02em;max-width:22em;text-wrap:balance}
.w-wall .onepage>li>.kicker{display:block;margin-bottom:14px}
.board-wall{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:96px;align-items:start}
.board-wall>div{display:grid;gap:24px}
.board-wall>div:nth-child(2){margin-top:120px}
.board-wall figure{margin:0;padding:10px}
.board-wall img{display:block;width:100%;height:auto;border-radius:4px}
.board-wall img[src$=".svg"],.board-wall img[src^="data:image/svg"]{background:var(--light);padding:18px}
.board-wall figcaption{font-size:14px;line-height:1.4;color:var(--muted);padding:12px 6px 6px}

/* Golden Circle: from the core outwards */
.w-core{padding-top:0;padding-bottom:0}
.w-core .pin{position:relative;padding:120px 0;display:grid;gap:28px;align-content:center}
.w-core .sc-head{margin:0}
.orbits{position:absolute;right:-8vmin;top:50%;width:112vmin;height:112vmin;margin-top:-56vmin;overflow:visible;opacity:.9}
.orbits circle{fill:none;stroke:var(--glass-line);stroke-width:1.5;vector-effect:non-scaling-stroke;transition:stroke .5s,fill .5s}
.orbits .o-why{fill:var(--accent);stroke:none}
.w-core .steps{display:grid;gap:20px;max-width:760px}
.w-core .step{padding:40px 44px}
.w-core .step .display{font-size:clamp(34px,4.4vw,68px)}
.w-core .step li{font-family:var(--display);font-size:clamp(26px,3vw,44px);line-height:1.1;letter-spacing:-.015em}
.w-core .step li+li{margin-top:16px}
.rail{display:none}

/* Lean Canvas: panes of glass that come together */
.w-canvas{background:color-mix(in srgb,var(--paper) 95%,var(--ink))}
.w-canvas .grid{position:absolute;inset:-120px 0;background-image:linear-gradient(var(--glass-line) 1px,transparent 1px),linear-gradient(90deg,var(--glass-line) 1px,transparent 1px);background-size:64px 64px;opacity:.55}
.canvas{display:grid;gap:14px;grid-template-columns:repeat(12,1fr);grid-template-areas:"problem problem solution solution uvp uvp uvp uvp unfair unfair segments segments" "alternatives alternatives metrics metrics uvp uvp uvp uvp channels channels adopter adopter" "cost cost cost cost cost cost revenue revenue revenue revenue revenue revenue"}
.canvas .pane{padding:20px}
.canvas .pane p,.canvas .pane li{font-size:15px}
.canvas .a-uvp{border-color:var(--accent);display:flex;flex-direction:column;justify-content:center}
.canvas .a-uvp{padding:32px}
.canvas .pane.a-uvp .display{font-size:clamp(28px,3vw,46px);line-height:1.06}

/* ICP: one person, then his job in his own words */
.w-person .who{display:grid;grid-template-columns:1.15fr 1fr;gap:64px;align-items:start}
.w-person .who-line{position:sticky;top:120px}
.w-person .who-line .display{font-size:clamp(32px,3.9vw,60px);line-height:1.06}
.w-person .path{border-left:1px solid var(--glass-line);padding-left:32px;display:grid;gap:56px}
.w-person .path li{position:relative}
.w-person .path li:before{content:"";position:absolute;left:-37px;top:3px;width:9px;height:9px;border-radius:50%;background:var(--accent)}
.w-person .path p{font-size:22px;line-height:1.35}
.w-person .job{margin:140px 0 0;padding:0}
.w-person .job .display{font-size:clamp(34px,5vw,80px)}
.w-person .job .stroke{width:min(60%,620px)}
.w-person .jobs{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:72px}
.w-person .others{margin-top:56px;max-width:52em}
.w-person .others li{font-size:17px;line-height:1.45;padding:14px 0;border-top:1px solid var(--glass-line)}

/* Positioning: the field, crossed sideways */
.w-field{background:color-mix(in srgb,var(--paper) 96%,var(--accent))}
.w-field .track{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.w-field .panel{padding:32px;border:1px solid var(--glass-line);border-radius:8px;background:var(--glass);backdrop-filter:blur(22px)}
.w-field .panel li{font-family:var(--display);font-size:clamp(22px,2.3vw,34px);line-height:1.14;letter-spacing:-.01em;padding:18px 0;border-top:1px solid var(--glass-line)}
.w-field .p-them li{color:var(--dim);text-decoration:line-through;text-decoration-thickness:1px;text-decoration-color:var(--accent)}
.w-field .p-only{border-color:var(--accent)}
.w-field .axis{display:none}
.w-field .landing{margin-top:120px}
.w-field .landing .display{font-size:clamp(30px,4.3vw,66px);max-width:20em}
.w-field dl{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin:64px 0 0;border-top:1px solid var(--glass-line);padding-top:28px}
.w-field dd{margin:10px 0 0;font-size:22px;line-height:1.3}

/* Brand Wheel: the essence in the middle, everything else in orbit */
.w-orbit .wheel-grid{display:grid;grid-template-columns:1fr minmax(300px,1.1fr) 1fr;grid-template-areas:"a core b" "c core d";gap:20px;align-items:center}
.w-orbit .essence{position:relative;display:grid;place-items:center;aspect-ratio:1}
.w-orbit .spin{position:absolute;inset:-34%;width:168%;height:168%;pointer-events:none}
.w-orbit .spin circle,.w-orbit .spin line{fill:none;stroke:var(--glass-line);stroke-width:1.5;vector-effect:non-scaling-stroke}
.w-orbit .spin .dash{stroke-dasharray:2 14;stroke:var(--accent)}
.w-orbit .disc{position:relative;width:86%;aspect-ratio:1;border-radius:50%;background:var(--accent);color:var(--on-accent);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:12%}
.w-orbit .disc h3{color:inherit;opacity:.7}
.w-orbit .disc .display{font-size:clamp(28px,3.4vw,52px)}
.w-orbit .traits{margin-top:120px}
.w-orbit .traits li{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:32px;align-items:baseline;padding:22px 0;border-top:1px solid var(--glass-line)}
.w-orbit .traits b{font-family:var(--display);font-weight:400;font-size:clamp(34px,5vw,76px);line-height:1;letter-spacing:-.02em}
.w-orbit .traits span{font-size:20px;line-height:1.4}

/* Marketing Mix: a deck that stacks */
.w-stack{background:color-mix(in srgb,var(--paper) 92%,var(--ink))}
.w-stack .bands{display:grid;gap:14px}
.w-stack .band{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);gap:40px;align-items:start;padding:14px 32px 44px;background:color-mix(in srgb,var(--paper) 86%,transparent)}
.w-stack .band b{font-family:var(--display);font-weight:400;font-size:clamp(30px,3.6vw,52px);line-height:1;letter-spacing:-.02em}
.w-stack .band p{font-size:21px;line-height:1.4;padding-top:8px}

/* Messaging: the promise, its proofs, and the answers */
.w-promise .promise{min-height:62vh;display:flex;flex-direction:column;justify-content:center}
.w-promise .promise .display{font-size:clamp(44px,7.4vw,124px)}
.w-promise .promise .stroke{width:min(52%,640px);height:44px}
.w-promise .proofs{margin-top:96px}
.w-promise .proofs ul{display:grid;grid-template-columns:repeat(3,1fr);gap:0}
.w-promise .proofs li{padding:28px 28px 28px 0;border-top:2px solid var(--ink)}
.w-promise .proofs li+li{padding-left:28px;border-left:1px solid var(--glass-line)}
.w-promise .proofs b{display:block;font-family:var(--display);font-weight:400;font-size:clamp(26px,2.8vw,42px);line-height:1.05;letter-spacing:-.015em;margin-bottom:14px}
.w-promise .proofs span{font-size:19px;line-height:1.4;color:var(--dim)}
.w-promise .talk{margin-top:120px}
.w-promise .talk li{display:grid;gap:16px;margin-top:44px}
.w-promise .ask{justify-self:start;max-width:min(100%,30em);padding:20px 26px;border-radius:8px 8px 8px 0;font-size:22px;line-height:1.3;font-style:italic;color:var(--dim)}
.w-promise .answer{justify-self:end;max-width:min(100%,24em);font-family:var(--display);font-size:clamp(24px,2.7vw,40px);line-height:1.12;letter-spacing:-.015em;text-align:right}

/* Mood: the territory and its words */
.w-mood{background:color-mix(in srgb,var(--paper) 90%,#000)}
.w-mood .words{margin:96px 0 40px}
.w-mood .words li{font-family:var(--display);font-size:clamp(56px,12vw,190px);line-height:.9;letter-spacing:-.03em;color:transparent;-webkit-text-stroke:1.5px var(--ink)}
.w-mood .words li:nth-child(2n){text-align:right;color:var(--ink);-webkit-text-stroke:0}

/* Color: the page turns into each color */
.w-chroma .chroma{margin:72px 0 0}
.w-chroma .chroma li{background:var(--c);box-shadow:0 0 0 100vmax var(--c);clip-path:inset(0 -100vmax);min-height:34vh;padding:32px 0;display:grid;grid-template-columns:1fr auto;align-content:end;align-items:end;gap:6px 24px}
.w-chroma .chroma b{font-family:var(--display);font-weight:400;font-size:clamp(48px,9vw,140px);line-height:.9;letter-spacing:-.03em;grid-row:span 2}
.w-chroma .chroma code{font-family:var(--text);font-weight:600;font-size:18px;letter-spacing:.06em;text-align:right}
.w-chroma .chroma span{font-size:16px;text-align:right;opacity:.8}

/* Motto */
.w-motto .line{min-height:56vh;display:flex;flex-direction:column;justify-content:center}
.w-motto .line .stroke{width:min(64%,780px);height:46px}
.w-motto .rejected{margin-top:56px}
.w-motto .rejected li{font-size:19px;line-height:1.4;padding:14px 0;border-top:1px solid var(--glass-line);color:var(--dim)}

/* A plate as the map draws it, on glass */
.w-plain .plate,.w-plain .shot{margin-bottom:0}
.w-shot{padding-top:72px;padding-bottom:72px}
.scene .prose ul{list-style:disc;padding-left:22px}
.w-plain .slots{background:none;border:0;gap:12px}
.w-plain .slot{background:var(--glass);-webkit-backdrop-filter:blur(22px) saturate(1.35);backdrop-filter:blur(22px) saturate(1.35);border:1px solid var(--glass-line);border-radius:8px}
.w-plain .headline p{font-size:clamp(34px,4.6vw,72px);line-height:1.04;letter-spacing:-.02em}
.w-archetype{background:color-mix(in srgb,var(--paper) 94%,var(--ink))}
.w-voice{background:color-mix(in srgb,var(--paper) 97%,var(--accent))}
.w-typography .specimen{background:var(--glass);backdrop-filter:blur(22px);border:1px solid var(--glass-line);border-radius:8px;margin-bottom:12px}
.w-typography .specimen .display{font-size:clamp(56px,11vw,170px);letter-spacing:-.03em}

@media (max-width:820px){
.scene{padding-top:80px;padding-bottom:80px}
.block:has(>.scene)>.num{position:absolute;left:0;top:28px;margin:0}
.sc-head{margin-bottom:36px}.sc-head h2{font-size:32px}
.pair,.w-person .who,.w-person .jobs,.w-field .track,.w-field dl,.w-promise .proofs ul,.board-wall{grid-template-columns:1fr}
.board-wall>div:nth-child(2){margin-top:0}
.canvas{grid-template-columns:1fr;grid-template-areas:"uvp" "problem" "alternatives" "segments" "adopter" "solution" "channels" "revenue" "cost" "metrics" "unfair"}
.w-person .who-line{position:static}
.w-person .job{margin-top:80px}
.w-orbit .wheel-grid{grid-template-columns:1fr;grid-template-areas:"core" "a" "b" "c" "d"}
.w-orbit .essence{max-width:340px;margin:0 auto 24px;width:100%}
.w-orbit .traits li,.w-stack .band{grid-template-columns:1fr;gap:10px}
.w-promise .proofs li,.w-promise .proofs li+li{padding:22px 0;border-left:0}
.w-promise .answer{text-align:left;justify-self:start}
.orbits{opacity:.45}
.w-part{min-height:70vh}
}

@media screen{
.motion [data-d]{transform:translate3d(0,calc(var(--v,0)*var(--d)),0);will-change:transform}
.motion .rise{opacity:0;transform:translate3d(0,36px,0);transition:opacity .8s cubic-bezier(.2,.7,.2,1),transform .8s cubic-bezier(.2,.7,.2,1)}
.motion .rise.from-l{transform:translate3d(-60px,0,0)}
.motion .rise.from-r{transform:translate3d(60px,0,0);transition-delay:.18s}
.motion .rise.in{opacity:1;transform:none}
.motion [data-focus]>*{opacity:.22;transition:opacity .45s}
.motion [data-focus]>.on{opacity:1}
.motion .stroke path{stroke-dashoffset:calc(1 - min(1,var(--e,1)*1.5))}
.motion .w-part .part{transform:translate3d(calc(var(--v,0)*-9vw),0,0)}
.motion .w-part .kicker{transform:translate3d(calc(var(--v,0)*5vw),0,0)}

.motion .w-core{height:340vh}
.motion .w-core .pin{position:sticky;top:0;height:100vh;padding:96px 0 40px}
.motion .w-core .orbits{transform:scale(calc(3.3 - var(--p,0)*2.4));transform-origin:50% 50%}
.motion .w-core .steps>.step{grid-area:1/1;opacity:0;transform:translate3d(0,44px,0) scale(.97);transition:opacity .5s,transform .6s cubic-bezier(.2,.7,.2,1);pointer-events:none}
.motion .w-core .steps>.step.on{opacity:1;transform:none;pointer-events:auto}
.motion .w-core[data-step="0"] .o-why{fill:var(--accent)}
.motion .w-core .o-why{fill:color-mix(in srgb,var(--accent) 30%,transparent)}
.motion .w-core[data-step="1"] .o-how,.motion .w-core[data-step="2"] .o-what{stroke:var(--accent);stroke-width:3}
.motion .rail{display:flex;gap:28px;font-family:var(--text);font-weight:600;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.motion .rail li{padding-top:12px;border-top:2px solid var(--glass-line);min-width:72px;transition:color .4s,border-color .4s}
.motion .w-core[data-step="0"] .rail li:nth-child(1),.motion .w-core[data-step="1"] .rail li:nth-child(2),.motion .w-core[data-step="2"] .rail li:nth-child(3){color:var(--ink);border-color:var(--accent)}

.motion .canvas{--a:min(1,calc(var(--e,1)*1.35))}
.motion .canvas .pane{opacity:calc(.15 + var(--a)*.85);transform:translate3d(calc((1 - var(--a))*var(--x)),calc((1 - var(--a))*var(--y)),0) rotate(calc((1 - var(--a))*var(--r)))}

.motion .w-orbit .spin{transform:rotate(calc(var(--v,0)*70deg))}
.motion .w-chroma .chroma b{transform:translate3d(calc(var(--v,0)*-6vw),0,0)}
.motion .w-archetype .wheel svg{transform:rotate(calc(var(--v,0)*-24deg))}
}
@media screen and (min-width:821px){
.motion .w-field .run{height:320vh}
.motion .w-field .pin{position:sticky;top:0;height:100vh;display:flex;flex-direction:column;justify-content:center;container-type:inline-size}
.motion .w-field .track{display:flex;width:max-content;gap:6vw;--q:clamp(0,calc((var(--p,0) - .1)/.78),1);transform:translate3d(calc(var(--q)*(100cqw - 100%)),0,0);will-change:transform}
.motion .w-field .panel{flex:0 0 min(66vw,860px);padding:44px}
.motion .w-field .panel li{font-size:clamp(28px,3.2vw,48px)}
.motion .w-field .axis{display:block;height:2px;margin-top:44px;background:linear-gradient(90deg,var(--accent) calc(var(--p,0)*100%),var(--glass-line) 0)}
}
@media screen and (min-width:821px) and (min-height:780px){
.motion .w-stack .band{position:sticky;top:calc(84px + var(--i)*62px);min-height:230px}
.motion .w-stack .bands{padding-bottom:20vh}
}
@media print{
.scene{margin:0;padding:24px 0;overflow:visible;background:none}
.scene>.bg{display:none}
.glass,.w-plain .slot,.w-field .panel{background:none;backdrop-filter:none;-webkit-backdrop-filter:none}
.w-part,.w-cover{min-height:0}
.w-part .part{font-size:72px}
.w-person .who-line{position:static}
.w-chroma .chroma{margin:32px 0 0}
.w-chroma .chroma li{box-shadow:none;clip-path:none;min-height:90px;padding:16px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.s-xl{font-size:64px}.s-l{font-size:44px}.s-m{font-size:28px}
.orbits{display:none}
}
"""

JS = """<script>(function(){
if(!window.matchMedia||matchMedia('(prefers-reduced-motion: reduce)').matches||matchMedia('print').matches)return;
var root=document.documentElement;root.classList.add('motion');
var scenes=[].slice.call(document.querySelectorAll('.scene,.run'));
var lists=[].slice.call(document.querySelectorAll('[data-focus]'));
var rises=[].slice.call(document.querySelectorAll('.rise'));
var queued=false;
function clamp(x){return x<0?0:x>1?1:x}
function frame(){
queued=false;var vh=window.innerHeight;
scenes.forEach(function(s){
var r=s.getBoundingClientRect();
if(r.bottom<-vh||r.top>2*vh)return;
s.style.setProperty('--e',clamp((vh-r.top)/vh).toFixed(4));
var p=clamp(-r.top/Math.max(1,r.height-vh));
s.style.setProperty('--p',p.toFixed(4));
s.style.setProperty('--v',((r.top+r.height/2-vh/2)/vh).toFixed(4));
var n=+s.getAttribute('data-steps');
if(n){var a=Math.min(n-1,Math.floor(p*n));
if(s.getAttribute('data-step')!==String(a)){s.setAttribute('data-step',a);
[].forEach.call(s.querySelectorAll('.step'),function(el,i){el.classList.toggle('on',i===a)})}}
});
rises=rises.filter(function(el){
if(el.getBoundingClientRect().top<vh*.9){el.classList.add('in');return false}return true});
lists.forEach(function(list){
var r=list.getBoundingClientRect();if(r.bottom<0||r.top>vh)return;
var best=null,gap=1e9;
[].forEach.call(list.children,function(el){var b=el.getBoundingClientRect();
var d=Math.abs(b.top+b.height/2-vh*.5);if(d<gap){gap=d;best=el}});
[].forEach.call(list.children,function(el){el.classList.toggle('on',el===best)});
});
}
function queue(){if(!queued){queued=true;requestAnimationFrame(frame)}}
addEventListener('scroll',queue,{passive:true});addEventListener('resize',queue);
addEventListener('beforeprint',function(){root.classList.remove('motion')});
addEventListener('afterprint',function(){root.classList.add('motion');queue()});
frame();
})()</script>"""
