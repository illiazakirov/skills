#!/usr/bin/env python3
"""Render the plates of a brand/ directory as HTML.

A plate is the short, literal answer in the slots of one tool (contract
section 5.1). This script reads the plate files of 00-intake, 01-strategy,
02-brand-platform, 03-identity and 04-design-system and writes, from what exists:

    brand/<step>/review/<name>.html      one page per plate
    brand/01-strategy/review/strategy.html   "Strategy on one page", once all
                                             six headline slots exist
    brand/02-brand-platform/review/platform.html   "Platform on one page":
                                             the headline lines of the step
                                             and the board, once the
                                             Archetype, Voice and Mood plates
                                             exist
    brand/03-identity/review/identity.html   "Identity on one page": the logo,
                                             the palette, the type, the motto
                                             and the surfaces, once the four
                                             plates exist
    brand/map.html                       the brand map: every plate so far

    render_plates.py [<path to brand/>] [--open <page>] [--theme <css file>]

The Interface plate of 04-design-system shows reference/sheet.html and the three
example pages in frames, once render_system.py has built them.

--open opens one page in the browser after rendering: a plate name without
".md" (golden-circle), "strategy", "platform", "identity" or "map".

The Mood plate, the platform page and the map show the board of
02-brand-platform/moodboard/index.md; its images are referenced by relative
path, not copied.
The identity pages show the logo files and load fonts/fonts.css of
03-identity, also by relative path.

Once 03-identity is approved in pipeline.yaml, every page is set in the
brand's own colors and type, with the logo in the masthead. --theme appends a
CSS file after that.

The pages are self-contained and load nothing from the network. A plate with
a missing or malformed slot is skipped and reported; fix it with
check_contract.py first. Exit codes: 0 rendered, 1 nothing to render or a bad
argument, 2 brand/ unreadable.
"""

import argparse
import html
import math
import os
import re
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contract as cc  # noqa: E402
import render_moodboard as rm  # noqa: E402

PLATE_STEPS = ("00-intake", "01-strategy", "02-brand-platform", "03-identity",
               "04-design-system")
PLATFORM = "02-brand-platform"
IDENTITY = "03-identity"
DESIGN = "04-design-system"
EXAMPLE_PAGES = (("Landing", "landing.html"), ("Sign-in", "sign-in.html"),
                 ("Sign-up", "sign-up.html"))
LOGO_FILES = ("full.svg", "mark.svg", "mono.svg", "dark.svg")

KICKERS = {"brief.md": "Kickoff"}
KICKERS.update({name: "Strategy %d of %d" % (i, len(cc.STRATEGY_TOOLS))
                for i, name in enumerate(cc.STRATEGY_TOOLS, 1)})

KICKERS.update({name: "Brand platform" for name in cc.PLATFORM_TOOLS})
KICKERS.update({name: "Identity %d of %d" % (i, len(cc.IDENTITY_TOOLS))
                for i, name in enumerate(cc.IDENTITY_TOOLS, 1)})
KICKERS.update({name: "Design system" for name in cc.DESIGN_TOOLS})

# The lines of "Identity on one page": (file, slot).
IDENTITY_HEADLINES = [("logo.md", "Logo idea"), ("color.md", "Color idea"),
                      ("typography.md", "Type idea"), ("motto.md", "Motto")]

# The lines of "Platform on one page": (file, slot). The name comes from the Name plate
# when the brand was named at this step, and from The Brief otherwise.
PLATFORM_HEADLINES = [("archetype.md", "Character"), ("voice.md", "Voice"),
                      ("name.md", "Name"), ("mood.md", "Territory")]
PLATFORM_REQUIRED = ("archetype.md", "voice.md", "mood.md")

# The six lines of "Strategy on one page": (file, slot, label).
HEADLINES = [(name, slot["name"], title)
             for name, (title, slots) in cc.PLATES["01-strategy"].items()
             for slot in slots if slot["headline"]]

LABELS = {"Why": "WHY", "How": "HOW", "What": "WHAT"}

HOUSE_DISPLAY = '"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif'
HOUSE_TEXT = '-apple-system,BlinkMacSystemFont,"Helvetica Neue",Helvetica,Arial,sans-serif'

CSS = """
:root{--paper:#f6f4ef;--ink:#141413;--muted:#77736a;--line:#d9d5cb;--card:#fffefb;--accent:#141413;
--on-accent:var(--paper);--light:#ffffff;--on-light:#141413;--dark:#141413;--on-dark:#ffffff;
--display:%(display)s;
--text:%(text)s;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--text);font-size:16px;line-height:1.45}
main{max-width:1180px;margin:0 auto;padding:56px 32px 96px}
h1,h2,h3,p,ul{margin:0}
ul{padding:0;list-style:none}
.kicker,.slot h3,.progress li,.status{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:500}
.masthead{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--ink);padding-bottom:14px;margin-bottom:56px}
.masthead h1{font-family:var(--display);font-weight:400;font-size:22px}
.masthead h1 img{display:block;height:28px;width:auto}
.plate{margin-bottom:112px}
.plate>header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:28px}
.plate>header h2{font-family:var(--display);font-weight:400;font-size:44px;letter-spacing:-.01em;line-height:1.05}
.status{border:1px solid var(--line);padding:3px 8px;border-radius:99px}
.slots{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);grid-auto-flow:dense}
.slot{background:var(--card);padding:22px 24px;min-width:0}
.slot h3{margin-bottom:12px}
.slot p,.slot li{font-size:17px;line-height:1.4}
.slot li+li{margin-top:9px}
.slot li{padding-left:16px;position:relative}
.slot li:before{content:"";position:absolute;left:0;top:.62em;width:6px;height:1px;background:var(--muted)}
.slot b{font-weight:600}
.slot .q{font-style:italic}
.headline p{font-family:var(--display);font-size:34px;line-height:1.18;letter-spacing:-.01em}

/* The Brief */
.plate-brief .slots{grid-template-columns:repeat(3,1fr)}
.plate-brief .slot-brand,.plate-brief .slot-in-one-line{grid-column:1/-1}
.plate-brief .slot-brand{display:flex;align-items:baseline;gap:20px;padding-top:16px;padding-bottom:16px}
.plate-brief .slot-brand h3{margin:0}
.plate-brief .slot-brand p{font-family:var(--display);font-size:22px}
.plate-brief .slot-in-one-line{padding-top:44px;padding-bottom:52px}
.plate-brief .slot-in-one-line p{font-family:var(--display);font-size:48px;line-height:1.1;letter-spacing:-.015em;max-width:20em}
.plate-brief .slot-for-whom,.plate-brief .slot-why-now,.plate-brief .slot-ambition{padding-bottom:36px}

/* Golden Circle */
.plate-golden-circle .body{display:grid;grid-template-columns:minmax(260px,400px) 1fr;gap:48px;align-items:center}
.rings{width:100%;height:auto;display:block}
.rings circle{fill:none;stroke:var(--ink);stroke-width:1}
.rings .core{fill:var(--accent);stroke:none}
.rings text{font-family:var(--mono);font-size:11px;letter-spacing:.14em;fill:var(--muted);text-anchor:middle}
.rings .core-label{fill:var(--on-accent)}
.plate-golden-circle .slots{grid-template-columns:1fr}

/* Lean Canvas */
.plate-lean-canvas .slots{grid-template-columns:repeat(10,1fr);grid-template-areas:
"pr pr so so uv uv ua ua cs cs" "pr pr so so uv uv ua ua cs cs"
"ea ea km km uv uv ch ch ad ad"
"co co co co co rs rs rs rs rs"}
.slot-problem{grid-area:pr}.slot-existing-alternatives{grid-area:ea}.slot-solution{grid-area:so}
.slot-key-metrics{grid-area:km}.slot-unique-value-proposition{grid-area:uv}
.slot-unfair-advantage{grid-area:ua}.slot-channels{grid-area:ch}.slot-customer-segments{grid-area:cs}
.slot-early-adopter{grid-area:ad}.slot-cost-structure{grid-area:co}.slot-revenue-streams{grid-area:rs}
.plate-lean-canvas .slot p,.plate-lean-canvas .slot li{font-size:15px}
.plate-lean-canvas .headline p{font-size:26px}
.plate-lean-canvas .slot-key-metrics li:first-child{font-weight:600}

/* ICP and Jobs-to-be-Done */
.plate-icp .slots{grid-template-columns:repeat(6,1fr)}
.plate-icp .slot{grid-column:span 6}
.plate-icp .slot-who{grid-column:span 6}
.plate-icp .slot-who p{font-family:var(--display);font-size:26px}
.plate-icp .slot-situation,.plate-icp .slot-trigger{grid-column:span 3}
.plate-icp .slot-tried-before,.plate-icp .slot-where-to-find{grid-column:span 3}
.plate-icp .slot-functional,.plate-icp .slot-emotional,.plate-icp .slot-social{grid-column:span 2}

/* Positioning */
.plate-positioning .slots{grid-template-columns:repeat(6,1fr)}
.plate-positioning .slot{grid-column:span 2}
.plate-positioning .slot-positioning-statement{grid-column:1/-1;order:-1}
.plate-positioning .slot-target-segment,.plate-positioning .slot-market-category{grid-column:span 3}
.plate-positioning .headline p{font-size:30px}

/* Brand Wheel */
.plate-brand-wheel .slots{grid-template-columns:1fr minmax(240px,300px) 1fr;grid-template-areas:
"at es fb" "va es eb" "pe pe pe"}
.slot-attributes{grid-area:at}.slot-functional-benefits{grid-area:fb}.slot-emotional-benefits{grid-area:eb}
.slot-values{grid-area:va}.slot-personality{grid-area:pe}
.plate-brand-wheel .slot-essence{grid-area:es;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;background:var(--accent)}
.plate-brand-wheel .slot-essence h3{color:var(--on-accent);opacity:.6}
.plate-brand-wheel .slot-essence p{color:var(--on-accent);font-size:38px}
.plate-brand-wheel .slot-personality ul{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px 28px}
.plate-brand-wheel .slot-personality li{margin:0;padding:0}
.plate-brand-wheel .slot-personality li:before{display:none}
.plate-brand-wheel .slot-personality b{display:block;font-family:var(--display);font-weight:400;font-size:22px;margin-bottom:4px}

/* Marketing Mix: four Ps in a row; a 7P plate adds a row of three */
.plate-marketing-mix .slots{grid-template-columns:repeat(12,1fr)}
.plate-marketing-mix .slot{grid-column:span 3;padding-bottom:36px}
.plate-marketing-mix .slot-people,.plate-marketing-mix .slot-process,.plate-marketing-mix .slot-physical-evidence{grid-column:span 4}
.plate-marketing-mix .slot h3{font-family:var(--display);font-size:24px;letter-spacing:0;text-transform:none;color:var(--ink);font-weight:400}

/* Messaging */
.plate-messaging .slots{grid-template-columns:1fr}
.plate-messaging .slot-main-promise{text-align:center;padding:44px 24px}
.plate-messaging .slot-main-promise p{font-size:40px}
.plate-messaging .slot ul{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}
.plate-messaging .slot li{margin:0;padding:0}
.plate-messaging .slot li:before{display:none}
.plate-messaging .slot li b,.plate-messaging .slot li .q{display:block;margin-bottom:6px}
.plate-messaging .slot-proofs b{font-family:var(--display);font-weight:400;font-size:22px}

/* Archetype: the wheel of twelve, the two chosen lit, the Character in the hub */
.plate-archetype .body{display:grid;grid-template-columns:minmax(300px,520px) 1fr;gap:48px;align-items:center;margin-bottom:1px}
.wheel{position:relative}
.wheel svg{width:100%;height:auto;display:block}
.segment path{fill:var(--card);stroke:var(--line);stroke-width:1}
.segment text{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;fill:var(--muted);text-anchor:middle}
.segment.primary path{fill:var(--accent);stroke:var(--accent)}
.segment.primary text{fill:var(--on-accent)}
.segment.secondary path{fill:var(--line);stroke:var(--muted)}
.segment.secondary text{fill:var(--ink)}
.hub{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none}
.hub p{width:36%;text-align:center;font-family:var(--display);font-size:18px;line-height:1.22}
.plate-archetype .body .slots{grid-template-columns:1fr 1fr}
.plate-archetype .slot-why-this-pair{grid-column:1/-1}
.plate-archetype .slot-primary-archetype p,.plate-archetype .slot-secondary-archetype p{font-family:var(--display);font-size:30px}
.plate-archetype>.slots{grid-template-columns:1fr;margin-top:24px}
.plate-archetype .slot-personality{grid-area:auto}
.plate-archetype .slot-personality ul{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px 28px}
.plate-archetype .slot-personality li{margin:0;padding:0}
.plate-archetype .slot-personality li:before{display:none}
.plate-archetype .slot-personality b{display:block;font-family:var(--display);font-weight:400;font-size:22px;margin-bottom:4px}

/* Voice: the line, four scales, the rules side by side, the examples in two columns */
.plate-voice .slots{grid-template-columns:1fr 1fr}
.plate-voice .slot-voice,.plate-voice .slot-tone,.plate-voice .slot-examples{grid-column:1/-1}
.plate-voice .slot-voice{padding:40px 24px}
.scale{display:grid;grid-template-columns:120px minmax(120px,280px) 120px 1fr;gap:16px;align-items:center;padding:10px 0}
.scale+.scale{border-top:1px solid var(--line)}
.scale .pole{font-size:15px}
.scale .pole:first-child{text-align:right}
.scale .track{position:relative;height:1px;background:var(--ink)}
.scale .track i{position:absolute;top:-6px;width:13px;height:13px;margin-left:-6.5px;border-radius:50%;background:var(--accent)}
.scale p{font-size:15px;color:var(--muted)}
.examples{display:grid;grid-template-columns:minmax(120px,1fr) 2fr 2fr;gap:0 28px}
.examples>*{padding:12px 0;border-top:1px solid var(--line);font-size:16px;line-height:1.4}
.examples>.head{border-top:0;padding-top:0}
.examples .situation{color:var(--muted);font-size:14px}
.examples .wrong{color:var(--muted);text-decoration:line-through;text-decoration-color:var(--line)}

/* Name */
.plate-name .slots{grid-template-columns:1fr 1fr}
.plate-name .slot-name,.plate-name .slot-rejected{grid-column:1/-1}
.plate-name .slot-name{padding:56px 24px;text-align:center}
.plate-name .slot-name p{font-size:96px;line-height:1;overflow-wrap:anywhere}

/* Mood: the plate above the board */
.plate-mood .slots{grid-template-columns:1fr 1fr 1fr}
.plate-mood .slot-territory{grid-column:1/-1;padding:40px 24px}
.plate-mood .slot-territory p{font-size:56px}
.plate-mood .slot-mood-words p,.plate-mood .slot-mood-words li{font-family:var(--display);font-size:24px}
.plate-mood .slot-mood-words li{padding:0}
.plate-mood .slot-mood-words li:before{display:none}
.board{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:24px;margin-top:32px}
.board img{display:block;width:100%;height:auto;border:1px solid var(--line);background:var(--card)}
.board p{font-size:14px;line-height:1.4;margin-top:8px;color:var(--muted)}

/* Logo: the sheet beside the slots */
.plate-logo .body{display:grid;grid-template-columns:minmax(300px,1fr) 1fr;gap:48px;align-items:start}
.plate-logo .body .slots{grid-template-columns:1fr 1fr}
.plate-logo .slot-logo-idea,.plate-logo .slot-construction,.plate-logo .slot-clear-space,.plate-logo .slot-never{grid-column:1/-1}
.sheet{display:grid;gap:1px;background:var(--line);border:1px solid var(--line)}
.sheet>div{display:flex;align-items:center;justify-content:center;padding:44px 24px;background:var(--light);color:var(--on-light)}
.sheet>.on-dark{background:var(--dark);color:var(--on-dark)}
.sheet .full img{display:block;max-width:70%;max-height:120px;width:auto;height:auto}
.sheet .sizes{gap:36px;align-items:flex-end;padding:28px 24px}
.sheet .sizes figure{margin:0;text-align:center}
.sheet .sizes img{display:block;width:auto;margin:0 auto 8px}
.sheet .sizes figcaption{font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--muted)}

/* Color: one swatch per palette line */
.plate-color .slots{grid-template-columns:1fr 1fr}
.plate-color .slot-color-idea,.plate-color .slot-palette,.plate-color .slot-contrast{grid-column:1/-1}
.plate-color .slot-color-idea{padding:40px 24px}
.swatches{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:20px}
.slot .swatches li{margin:0;padding:0;font-size:14px;line-height:1.35}
.slot .swatches li:before{display:none}
.swatches i{display:block;height:120px;border:1px solid var(--line);margin-bottom:10px}
.swatches b{display:block;font-family:var(--display);font-weight:400;font-size:22px}
.swatches code{display:block;font-family:var(--mono);font-size:12px;letter-spacing:.06em;margin:2px 0 4px}
.swatches span{color:var(--muted)}
.plate-color .slot-contrast ul{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:9px 28px}
.plate-color .slot-contrast li{margin:0}

/* Typography: the specimen above the slots */
.plate-typography .slots{grid-template-columns:1fr 1fr}
.plate-typography .slot-type-idea,.plate-typography .slot-sizes,.plate-typography .slot-license{grid-column:1/-1}
.specimen{border:1px solid var(--line);border-bottom:0;background:var(--card);padding:40px 24px}
.specimen .display{font-size:clamp(40px,7vw,96px);line-height:1.02;letter-spacing:-.015em;overflow-wrap:anywhere}
.specimen .text{font-size:18px;line-height:1.5;max-width:34em;margin-top:20px}
.specimen .kicker{display:block;margin:28px 0 8px}
.specimen .kicker:first-child{margin-top:0}

/* Motto: the line, set large, alone */
.plate-motto .slots{grid-template-columns:1fr 1fr}
.plate-motto .slot-motto,.plate-motto .slot-rejected{grid-column:1/-1}
.plate-motto .slot-motto{padding:56px 24px;text-align:center}
.plate-motto .slot-motto p{font-size:72px;line-height:1.05;overflow-wrap:anywhere}

/* Interface: the sheet beside the slots, the example pages under them */
.plate-interface .body{display:grid;grid-template-columns:minmax(0,1.15fr) 1fr;gap:48px;align-items:start}
.plate-interface .body .slots{grid-template-columns:1fr 1fr}
.plate-interface .slot-interface-idea,.plate-interface .slot-never{grid-column:1/-1}
.system-sheet{width:100%;aspect-ratio:1440/1100;overflow:hidden;border:1px solid var(--line);background:var(--card);container-type:inline-size}
.system-sheet iframe{width:1440px;height:1100px;border:0;transform:scale(calc(100cqw / 1440px));transform-origin:0 0;pointer-events:none}
.examples-frames{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px;margin-top:32px}
.examples-frames .frame{width:300px;height:188px;max-width:100%;overflow:hidden;border:1px solid var(--line);background:var(--card)}
.examples-frames iframe{width:1440px;height:900px;border:0;transform:scale(.2083);transform-origin:0 0;pointer-events:none}
.examples-frames a,.system-link{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);text-decoration:none;margin-top:8px}
.system-link{margin-top:24px;color:var(--ink)}

/* Identity on one page */
.onepage.identity .logo img{display:block;max-height:140px;max-width:min(100%,520px);width:auto;height:auto;margin-bottom:28px}
.onepage.identity .swatches,.onepage.identity .specimen{margin-bottom:28px}
.onepage.identity .specimen{border-bottom:1px solid var(--line)}
.onepage.identity .specimen p{max-width:none}
.onepage.identity .specimen .display{font-size:clamp(40px,7vw,96px)}
.onepage.identity .specimen .text{font-family:var(--text);font-size:18px;letter-spacing:0}
.onepage.identity .swatches b,.onepage.identity .swatches code,.onepage.identity .swatches span{font-size:inherit;letter-spacing:0}
.onepage.identity .swatches li{font-size:14px;padding:0;border:0}
.onepage.identity .swatches b{font-size:22px}
.onepage.identity .swatches code{font-size:12px}
.onepage .motto p{font-size:72px}
.surfaces{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px;margin-top:40px}
.surfaces .frame{width:300px;height:158px;max-width:100%;overflow:hidden;border:1px solid var(--line);background:var(--card)}
.surfaces iframe{width:1200px;height:632px;border:0;transform:scale(.25);transform-origin:0 0;pointer-events:none}
.surfaces a{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);text-decoration:none;margin-top:8px}

/* Strategy on one page, Platform on one page */
.onepage .name p,.onepage .territory p{font-size:72px}
.onepage li{padding:30px 0;border-top:1px solid var(--line)}
.onepage li:first-child{border-top:0;padding-top:0}
.onepage .kicker{display:block;margin-bottom:10px}
.onepage p{font-family:var(--display);font-size:38px;line-height:1.16;letter-spacing:-.01em;max-width:24em}
.onepage .essence p{font-size:72px}

/* Brand map */
.progress{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:88px}
.progress li{border-top:3px solid var(--line);padding-top:8px}
.progress li.done{border-color:var(--ink);color:var(--ink)}
.progress li.draft{border-color:var(--muted)}
.progress a{color:inherit;text-decoration:none}

@media (max-width:820px){
main{padding:32px 16px 64px}
.plate>header h2{font-size:32px}
.headline p,.plate-brief .slot-in-one-line p,.plate-messaging .slot-main-promise p,.onepage p{font-size:26px}
.plate-brief .slot-brand{display:block}.plate-brief .slot-brand h3{margin-bottom:12px}
.onepage .essence p{font-size:44px}
.plate .slots,.plate-golden-circle .body{display:block}
.plate .slot{border-bottom:1px solid var(--line)}
.plate-messaging .slot ul{grid-template-columns:1fr}
.rings{max-width:280px;margin:0 auto 24px}
.plate-archetype .body{display:block}
.wheel{max-width:420px;margin:0 auto 24px}
.hub p{font-size:14px}
.scale{grid-template-columns:1fr 1fr;gap:6px 12px}
.scale .pole:first-child{text-align:left}.scale .track{grid-column:1/-1;margin:8px 6px}
.scale .pole:nth-child(3){grid-row:1;grid-column:2;text-align:right}.scale p{grid-column:1/-1}
.examples{grid-template-columns:1fr}.examples>.head{display:none}
.examples>.situation{padding-bottom:0}.examples>.right,.examples>.wrong{border-top:0;padding-top:4px}
.plate-name .slot-name p,.plate-mood .slot-territory p,.onepage .name p,.onepage .territory p{font-size:44px}
.plate-logo .body{display:block}.sheet{margin-bottom:24px}
.plate-interface .body{display:block}.system-sheet{margin-bottom:24px}
.sheet .sizes{gap:20px}
.plate-motto .slot-motto p,.onepage .motto p{font-size:40px}
.plate-motto .slot-motto{padding:36px 16px}
}
@media print{body{background:#fff}.plate{break-inside:avoid}}
"""
CSS = CSS.replace("%(display)s", HOUSE_DISPLAY).replace("%(text)s", HOUSE_TEXT)

RINGS = """<svg class="rings" viewBox="0 0 400 400" role="img" aria-label="Three rings: what, how, why">
<circle cx="200" cy="200" r="196"/><circle cx="200" cy="200" r="130"/>
<circle class="core" cx="200" cy="200" r="64"/>
<text x="200" y="38">WHAT</text><text x="200" y="104">HOW</text>
<text class="core-label" x="200" y="204">WHY</text></svg>"""


def wheel(primary, secondary, character):
    """The twelve archetypes as a ring of equal segments, the Character in the hub."""
    cx = cy = 250
    outer, inner, label = 244, 118, 181
    parts = []
    for index, name in enumerate(cc.ARCHETYPES):
        start, end = math.radians(index * 30 - 105), math.radians(index * 30 - 75)
        middle = (start + end) / 2
        points = [(cx + r * math.cos(a), cy + r * math.sin(a))
                  for r, a in ((outer, start), (outer, end), (inner, end), (inner, start))]
        path = ("M%.1f %.1f A%d %d 0 0 1 %.1f %.1f L%.1f %.1f A%d %d 0 0 0 %.1f %.1f Z"
                % (points[0] + (outer, outer) + points[1] + points[2] + (inner, inner)
                   + points[3]))
        kind = " primary" if name == primary else " secondary" if name == secondary else ""
        parts.append('<g class="segment%s"><path d="%s"/><text x="%.1f" y="%.1f">%s</text></g>'
                     % (kind, path, cx + label * math.cos(middle),
                        cy + label * math.sin(middle) + 3.5, html.escape(name)))
    return ('<div class="wheel"><svg viewBox="0 0 500 500" role="img" aria-label="The twelve '
            'archetypes; primary %s, secondary %s">%s</svg><div class="hub"><p>%s</p></div></div>'
            % (html.escape(primary, quote=True), html.escape(secondary, quote=True),
               "".join(parts), html.escape(character)))


def render_tone(values):
    """Four scales. Each value is 'Dimension: N of 5. Why'; 1 is the first pole."""
    rows = []
    for dimension, value in zip(cc.TONE_DIMENSIONS, values):
        match = re.fullmatch(r"[^:]+: ([1-5]) of 5\. (.+)", value)
        first, second = dimension.split("–")
        rows.append('<div class="scale"><span class="pole">%s</span><span class="track">'
                    '<i style="left:%d%%"></i></span><span class="pole">%s</span><p>%s</p></div>'
                    % (html.escape(first), (int(match.group(1)) - 1) * 25,
                       html.escape(second.capitalize()), html.escape(match.group(2))))
    return "".join(rows)


def render_examples(values):
    """Each value is 'Situation. Right: ... Wrong: ...': three columns."""
    cells = ['<span class="head"></span><span class="head kicker">Right</span>'
             '<span class="head kicker">Wrong</span>']
    for value in values:
        situation, right, wrong = re.fullmatch(r"([^.]+)\. Right: (.+) Wrong: (.+)",
                                               value).groups()
        cells.append('<span class="situation">%s</span><span class="right">%s</span>'
                     '<span class="wrong">%s</span>'
                     % (html.escape(situation), html.escape(right), html.escape(wrong)))
    return '<div class="examples">%s</div>' % "".join(cells)


# Slots drawn in the shape of the tool instead of as a line or a list.
def family(value):
    """The family of a Display or Text line ('Family - weights - role'), safe inside a CSS
    string in a style attribute."""
    return re.sub(r"[^\w .-]", "", value.split(" - ")[0]).strip()


def render_palette(values):
    """One swatch per palette line: the color, its name, its hex value and its role."""
    cells = []
    for value in values:
        match = re.fullmatch(r"(.+?) - (#[0-9A-Fa-f]{6}) - (.+)", value)
        if not match:
            continue
        cells.append('<li><i style="background:%s"></i><b>%s</b><code>%s</code><span>%s</span></li>'
                     % (match.group(2), html.escape(match.group(1)), match.group(2).upper(),
                        html.escape(match.group(3))))
    return '<ul class="swatches">%s</ul>' % "".join(cells)


def render_specimen(display, text, sample):
    """The type pair at work: the display family's name set in itself, a line in the text
    family."""
    return ('<div class="specimen"><span class="kicker">Display</span>'
            '<p class="display" style="font-family:\'%s\',var(--display)">%s</p>'
            '<span class="kicker">Text</span>'
            '<p class="text" style="font-family:\'%s\',var(--text)">%s</p></div>'
            % (family(display), html.escape(display.split(" - ")[0]),
               family(text), html.escape(sample)))


# What a page takes from the identity while none exists; see brand_look().
NO_LOOK = {"css": "", "fonts": False, "logo": False, "styled": False, "system": False}


def logo_picture(identity, alt, look):
    """The full logo. On a page in the brand's style, which follows the reader's light or
    dark setting, the dark version is offered too. identity leads from the page to the
    03-identity directory."""
    base = html.escape(identity, quote=True) + "logo/"
    image = '<img src="%sfull.svg" alt="%s">' % (base, html.escape(alt, quote=True))
    if not look["styled"]:
        return image
    return ('<picture><source srcset="%sdark.svg" media="(prefers-color-scheme: dark)">%s'
            "</picture>" % (base, image))


def render_sheet(identity):
    """The logo sheet: the full logo on light and on dark, the mark at three sizes.
    identity leads from the page to the 03-identity directory."""
    base = html.escape(identity, quote=True) + "logo/"
    sizes = "".join('<figure><img src="%smark.svg" alt="" style="height:%dpx">'
                    "<figcaption>%d px</figcaption></figure>" % (base, size, size)
                    for size in (24, 32, 48))
    return ('<div class="sheet"><div class="full on-light"><img src="%sfull.svg" alt="The logo">'
            '</div><div class="full on-dark"><img src="%sdark.svg" alt="The logo on dark"></div>'
            '<div class="sizes on-light">%s</div></div>' % (base, base, sizes))


SHAPED_SLOTS = {"Tone": render_tone, "Examples": render_examples, "Palette": render_palette}


def load_board(brand):
    """Return the images of the moodboard index as [{name, file, takes}]. Raise ValueError
    when the index is missing or breaks a rule of reference/moodboard.md."""
    base = os.path.join(brand, PLATFORM, "moodboard")
    try:
        with open(os.path.join(base, "index.md"), encoding="utf-8") as handle:
            text = handle.read()
        return rm.parse(text, base, False)[2]
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError("cannot be read: %s" % error)
    except rm.IndexProblems as error:
        raise ValueError("; ".join(error.problems))


def render_board(board, prefix):
    """The board: each image with what is taken from it. prefix leads from the page to
    the moodboard directory."""
    if not board:
        return ""
    return '<ul class="board">%s</ul>' % "".join(
        '<li><img src="%s%s" alt="%s" loading="lazy"><p>%s</p></li>'
        % (html.escape(prefix, quote=True), rm.href(item["file"]),
           html.escape(item["name"], quote=True), html.escape(item["takes"]))
        for item in board)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def split_frontmatter(lines):
    """Return (fields, body lines). Fields are empty when there is no valid frontmatter."""
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            try:
                return cc.parse_yaml(lines[1:end]), lines[end + 1:]
            except cc.SubsetError:
                return {}, lines[end + 1:]
    return {}, lines


def load_plate(brand, step, name):
    """Return {title, status, slots: [(slot, [values])]} or None when absent, or raise ValueError."""
    path = os.path.join(brand, step, name)
    if not os.path.isfile(path):
        return None
    title, slots = cc.PLATES[step][name]
    fields, body = split_frontmatter(cc.read_lines(path))
    report = cc.Report()
    cc.check_sections(name, body, cc.MARKDOWN[step][name][1], report)
    cc.check_plate(name, body, slots, report)
    if report.errors:
        raise ValueError("; ".join(message for _, message in report.errors))
    values = cc.plate_values(body, slots)
    return {"name": name, "step": step, "title": title,
            "status": fields.get("status", "draft") if isinstance(fields, dict) else "draft",
            "slots": [(slot, values[slot["name"]]) for slot in slots if slot["name"] in values]}


def rich(text):
    """Escape one entry; set a leading 'Label:' in bold and a leading quotation in italics."""
    quoted = re.fullmatch(r'("[^"]+")\s+(.+)', text)
    if quoted:
        return '<span class="q">%s</span> %s' % (html.escape(quoted.group(1)),
                                                 html.escape(quoted.group(2)))
    labelled = re.fullmatch(r"([^:]{1,60}):\s+(.+)", text)
    if labelled:
        return "<b>%s</b> %s" % (html.escape(labelled.group(1)), html.escape(labelled.group(2)))
    return html.escape(text)


def render_slot(slot, values):
    classes = "slot slot-%s%s" % (slug(slot["name"]), " headline" if slot["headline"] else "")
    label = LABELS.get(slot["name"], slot["name"])
    # Only slots whose lines have a set shape ("Trait: meaning") are split into label and text.
    shaped = bool(slot["pattern"]) or slot["name"] == "Other customers"
    show = rich if shaped and not slot["headline"] else html.escape
    if slot["name"] in SHAPED_SLOTS:
        content = SHAPED_SLOTS[slot["name"]](values)
    elif slot["kind"] == "line":
        content = "<p>%s</p>" % show(values[0])
    else:
        content = "<ul>%s</ul>" % "".join("<li>%s</li>" % show(value) for value in values)
    return '<div class="%s"><h3>%s</h3>%s</div>' % (classes, html.escape(label), content)


def one(plate, slot_name):
    """The single line of a slot of a loaded plate."""
    return next(values[0] for slot, values in plate["slots"] if slot["name"] == slot_name)


def render_system(design):
    """The sheet beside the slots and the example pages of the design system. design leads
    from the page to the 04-design-system directory."""
    base = html.escape(design, quote=True) + "reference/"
    sheet = ('<div class="system-sheet"><iframe src="%ssheet.html" title="The interface" '
             'loading="lazy"></iframe></div>' % base)
    frames = "".join('<li><div class="frame"><iframe src="%spages/%s" title="%s" loading="lazy">'
                     '</iframe></div><a href="%spages/%s">%s</a></li>'
                     % (base, name, title, base, name, title) for title, name in EXAMPLE_PAGES)
    after = ('<ul class="examples-frames">%s</ul><a class="system-link" href="%sindex.html">'
             "The whole system on one page</a>" % (frames, base))
    return sheet, after


def render_plate(plate, board=None, prefix="../moodboard/", identity="../", look=NO_LOOK,
                 design="../"):
    """identity and design lead from the page to the 03-identity and 04-design-system
    directories; look is the result of brand_look()."""
    key = plate["name"][:-len(".md")]
    slots = '<div class="slots">%s</div>' % "".join(
        render_slot(slot, values) for slot, values in plate["slots"])
    if key == "golden-circle":
        slots = '<div class="body">%s%s</div>' % (RINGS, slots)
    elif key == "archetype":
        by_slot = {slot["name"]: (slot, values) for slot, values in plate["slots"]}
        beside = "".join(render_slot(*by_slot[name]) for name in
                         ("Primary archetype", "Secondary archetype", "Why this pair"))
        slots = ('<div class="body">%s<div class="slots">%s</div></div><div class="slots">%s</div>'
                 % (wheel(by_slot["Primary archetype"][1][0],
                          by_slot["Secondary archetype"][1][0], by_slot["Character"][1][0]),
                    beside, render_slot(*by_slot["Personality"])))
    elif key == "mood":
        slots += render_board(board, prefix)
    elif key == "logo" and look["logo"]:
        slots = '<div class="body">%s%s</div>' % (render_sheet(identity), slots)
    elif key == "interface" and look["system"]:
        sheet, after = render_system(design)
        slots = '<div class="body">%s%s</div>%s' % (sheet, slots, after)
    elif key == "typography":
        slots = render_specimen(one(plate, "Display"), one(plate, "Text"),
                                one(plate, "Type idea")) + slots
    status = "" if plate["status"] == "approved" else '<span class="status">draft</span>'
    return ('<section class="plate plate-%s" id="%s"><header><div><p class="kicker">%s</p>'
            "<h2>%s</h2></div>%s</header>%s</section>"
            % (key, key, html.escape(KICKERS[plate["name"]]), html.escape(plate["title"]),
               status, slots))


def page(title, brand_name, body, theme, look=None, identity="../../03-identity/"):
    """look is the result of brand_look(); identity leads from the page to 03-identity."""
    look = look or NO_LOOK
    base = html.escape(identity, quote=True)
    link = '<link rel="stylesheet" href="%sfonts/fonts.css">' % base if look["fonts"] else ""
    name = html.escape(brand_name)
    if look["styled"] and look["logo"]:
        name = logo_picture(identity, brand_name, look)
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title>%s<style>%s%s%s</style></head><body><main>"
            "<div class=\"masthead\"><h1>%s</h1><p class=\"kicker\">%s</p></div>%s"
            "</main></body></html>\n"
            % (html.escape(title), link, CSS, look["css"], theme, name, html.escape(title), body))


def readable_on(color, first, second):
    """Whichever of two colors reads better on color."""
    return first if cc.contrast(first, color) >= cc.contrast(second, color) else second


def brand_look(brand, plates, skipped):
    """What the pages take from the identity: {css, fonts, logo, styled}.

    fonts and logo say whether fonts/fonts.css and the four logo files exist; the identity
    pages use them as soon as they do. css restyles every page in the brand's colors and
    type, and styled is True, only once 03-identity is approved in pipeline.yaml."""
    base = os.path.join(brand, IDENTITY)
    look = {"css": "", "styled": False,
            "system": os.path.isfile(os.path.join(brand, DESIGN, "reference", "sheet.html")),
            "fonts": os.path.isfile(os.path.join(base, "fonts", "fonts.css")),
            "logo": all(os.path.isfile(os.path.join(base, "logo", name))
                        for name in LOGO_FILES)}
    try:
        state = cc.parse_yaml(cc.read_lines(os.path.join(brand, "pipeline.yaml")))
        status = state["steps"][IDENTITY]["status"]
    except (OSError, UnicodeDecodeError, cc.SubsetError, KeyError, TypeError):
        return look
    if status not in ("approved", "stale"):
        return look
    by_name = {plate["name"]: plate for plate in plates}
    rules = []
    if "color.md" in by_name:
        try:
            palette = cc.parse_palette(
                next(values for slot, values in by_name["color.md"]["slots"]
                     if slot["name"] == "Palette"))
        except ValueError as error:
            skipped.append("%s/color.md: the brand's colors are not applied: %s"
                           % (IDENTITY, error))
        else:
            role = {name: color["hex"] for color in palette for name in color["roles"]}
            mixes = ("--muted:color-mix(in srgb,var(--paper) 38%,var(--ink));"
                     "--line:color-mix(in srgb,var(--paper) 84%,var(--ink));"
                     "--card:color-mix(in srgb,var(--paper) 96%,var(--ink));")
            light = (role["background on light"], role["text on light"])
            dark = (role["background on dark"], role["text on dark"])
            rules.append(
                ":root{--paper:%s;--ink:%s;--accent:%s;--on-accent:%s;%s"
                "--light:%s;--on-light:%s;--dark:%s;--on-dark:%s}"
                % (light[0], light[1], role["accent"],
                   readable_on(role["accent"], light[0], light[1]), mixes,
                   light[0], light[1], dark[0], dark[1]))
            rules.append("@media (prefers-color-scheme:dark){:root{--paper:%s;--ink:%s}}" % dark)
            rules.append("@media print{:root{--paper:%s;--ink:%s}}" % light)
    else:
        skipped.append("%s/color.md: missing; the brand's colors are not applied" % IDENTITY)
    if "typography.md" in by_name:
        rules.append(":root{--display:'%s',%s;--text:'%s',%s}"
                     % (family(one(by_name["typography.md"], "Display")), HOUSE_DISPLAY,
                        family(one(by_name["typography.md"], "Text")), HOUSE_TEXT))
        if not look["fonts"]:
            skipped.append("%s/fonts/fonts.css: missing; the brand's type falls back to the "
                           "house faces" % IDENTITY)
    else:
        skipped.append("%s/typography.md: missing; the brand's type is not applied" % IDENTITY)
    if not look["logo"]:
        skipped.append("%s/logo/: a logo file is missing; the masthead shows the name"
                       % IDENTITY)
    look["css"] = "\n/* The brand's own style */\n" + "\n".join(rules) + "\n"
    look["styled"] = True
    return look


def render_onepage(plates):
    """Return the body of "Strategy on one page", or None while a headline slot is missing."""
    by_name = {plate["name"]: plate for plate in plates}
    rows = []
    for name, slot_name, title in HEADLINES:
        plate = by_name.get(name)
        if plate is None:
            return None
        value = next(values[0] for slot, values in plate["slots"] if slot["name"] == slot_name)
        rows.append('<li class="%s"><span class="kicker">%s · %s</span><p>%s</p></li>'
                    % (slug(slot_name), html.escape(title),
                       html.escape(LABELS.get(slot_name, slot_name)), html.escape(value)))
    return '<ul class="onepage">%s</ul>' % "".join(rows)


def list_surfaces(brand):
    """The HTML files of 03-identity/surfaces, in name order."""
    base = os.path.join(brand, IDENTITY, "surfaces")
    try:
        return sorted(name for name in os.listdir(base)
                      if name.endswith(".html") and not name.startswith("."))
    except OSError:
        return []


def render_identity(plates, surfaces, look, identity="../"):
    """Return the body of "Identity on one page", or None while a plate is missing."""
    by_name = {plate["name"]: plate for plate in plates}
    if any(name not in by_name for name, _slot in IDENTITY_HEADLINES):
        return None
    base = html.escape(identity, quote=True)
    shown = {
        "logo.md": logo_picture(identity, "The logo", look) if look["logo"] else "",
        "color.md": render_palette(next(values for slot, values in by_name["color.md"]["slots"]
                                        if slot["name"] == "Palette")),
        "typography.md": render_specimen(one(by_name["typography.md"], "Display"),
                                         one(by_name["typography.md"], "Text"),
                                         one(by_name["typography.md"], "Type idea")),
        "motto.md": "",
    }
    rows = "".join('<li class="%s">%s<span class="kicker">%s</span><p>%s</p></li>'
                   % (name[:-len(".md")], shown[name], html.escape(slot_name),
                      html.escape(one(by_name[name], slot_name)))
                   for name, slot_name in IDENTITY_HEADLINES)
    frames = "".join(
        '<li><div class="frame"><iframe src="%ssurfaces/%s" title="%s" loading="lazy"></iframe>'
        '</div><a href="%ssurfaces/%s">%s</a></li>'
        % (base, rm.href(name), html.escape(name, quote=True), base, rm.href(name),
           html.escape(name[:-len(".html")].replace("-", " ")))
        for name in surfaces)
    return '<ul class="onepage identity">%s</ul>%s' % (
        rows, '<ul class="surfaces">%s</ul>' % frames if frames else "")


def render_platform(plates, brand_name, board, prefix="../moodboard/"):
    """Return the body of "Platform on one page", or None while a required plate is missing."""
    by_name = {plate["name"]: plate for plate in plates}
    if any(name not in by_name for name in PLATFORM_REQUIRED):
        return None
    rows = []
    for name, slot_name in PLATFORM_HEADLINES:
        plate = by_name.get(name)
        if plate is not None:
            value = next(values[0] for slot, values in plate["slots"]
                         if slot["name"] == slot_name)
        elif brand_name not in ("Brand", "Unnamed"):
            value = brand_name
        else:
            continue
        rows.append('<li class="%s"><span class="kicker">%s</span><p>%s</p></li>'
                    % (slug(slot_name), html.escape(slot_name), html.escape(value)))
    return '<ul class="onepage">%s</ul>%s' % ("".join(rows), render_board(board, prefix))


def render_map(plates, onepage, platform=None, board=None, identity=None, look=NO_LOOK):
    by_name = {plate["name"]: plate for plate in plates}
    cells = []
    for step in PLATE_STEPS:
        for name, (title, _slots) in cc.PLATES[step].items():
            plate = by_name.get(name)
            if plate is None:
                if name in cc.OPTIONAL_PLATES.get(step, ()):
                    continue
                cells.append("<li>%s</li>" % html.escape(title))
            else:
                state = "done" if plate["status"] == "approved" else "draft"
                cells.append('<li class="%s"><a href="#%s">%s</a></li>'
                             % (state, name[:-len(".md")], html.escape(title)))
    body = '<ul class="progress">%s</ul>' % "".join(cells)
    if onepage:
        body += ('<section class="plate" id="strategy"><header><div><p class="kicker">Strategy</p>'
                 "<h2>On one page</h2></div></header>%s</section>" % onepage)
    prefix = PLATFORM + "/moodboard/"
    sections = ""
    for plate in plates:
        if platform and plate["step"] == PLATFORM and 'id="platform"' not in sections:
            sections += ('<section class="plate" id="platform"><header><div>'
                         '<p class="kicker">Brand platform</p><h2>On one page</h2></div></header>'
                         "%s</section>" % platform(prefix))
        if identity and plate["step"] == IDENTITY and 'id="identity"' not in sections:
            sections += ('<section class="plate" id="identity"><header><div>'
                         '<p class="kicker">Identity</p><h2>On one page</h2></div></header>'
                         "%s</section>" % identity(IDENTITY + "/"))
        sections += render_plate(plate, board, prefix, IDENTITY + "/", look, DESIGN + "/")
    return body + sections


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def render(brand, theme=""):
    """Render everything that exists. Return ({page name: path}, [skipped messages])."""
    plates, skipped, pages = [], [], {}
    for step in PLATE_STEPS:
        for name in cc.PLATES[step]:
            try:
                plate = load_plate(brand, step, name)
            except (OSError, UnicodeDecodeError, ValueError) as error:
                skipped.append("%s/%s: %s" % (step, name, error))
                continue
            if plate:
                plates.append(plate)
    if not plates:
        return pages, skipped

    brand_name = "Brand"
    for plate in plates:
        if plate["name"] == "brief.md":
            brand_name = next(values[0] for slot, values in plate["slots"]
                              if slot["name"] == "Brand")
    board = None
    if any(plate["name"] == "mood.md" for plate in plates):
        try:
            board = load_board(brand)
        except ValueError as error:
            skipped.append("%s/moodboard/index.md: %s" % (PLATFORM, error))

    look = brand_look(brand, plates, skipped)

    def write_plates(steps):
        for plate in plates:
            if plate["step"] in steps:
                key = plate["name"][:-len(".md")]
                path = os.path.join(brand, plate["step"], "review", key + ".html")
                write(path, page(plate["title"], brand_name,
                                 render_plate(plate, board, look=look), theme, look))
                pages[key] = path

    write_plates(PLATE_STEPS[:2])
    onepage = render_onepage(plates)
    if onepage:
        path = os.path.join(brand, "01-strategy", "review", "strategy.html")
        write(path, page("Strategy on one page", brand_name, onepage, theme, look))
        pages["strategy"] = path
    write_plates((PLATFORM,))
    platform = None
    if render_platform(plates, brand_name, board) is not None:
        def platform(prefix="../moodboard/"):
            return render_platform(plates, brand_name, board, prefix)
        path = os.path.join(brand, PLATFORM, "review", "platform.html")
        write(path, page("Platform on one page", brand_name, platform(), theme, look))
        pages["platform"] = path
    write_plates((IDENTITY,))
    identity = None
    surfaces = list_surfaces(brand)
    if render_identity(plates, surfaces, look) is not None:
        def identity(base="../"):
            return render_identity(plates, surfaces, look, base)
        path = os.path.join(brand, IDENTITY, "review", "identity.html")
        write(path, page("Identity on one page", brand_name, identity(), theme, look))
        pages["identity"] = path
    write_plates((DESIGN,))
    path = os.path.join(brand, "map.html")
    write(path, page("Brand map", brand_name,
                     render_map(plates, onepage, platform, board, identity, look),
                     theme, look, IDENTITY + "/"))
    pages["map"] = path
    return pages, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render the plates of brand/ as HTML.")
    parser.add_argument("brand", nargs="?", default="brand", help="path to brand/")
    parser.add_argument("--open", metavar="PAGE", dest="open_page",
                        help="open this page afterwards: a plate name, 'strategy', "
                             "'platform', 'identity' or 'map'")
    parser.add_argument("--theme", metavar="CSS", help="a CSS file appended to the house style")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.brand):
        print("%s is not a directory" % args.brand, file=sys.stderr)
        return 2
    theme = ""
    if args.theme:
        try:
            with open(args.theme, encoding="utf-8") as handle:
                theme = handle.read().replace("</style", "<\\/style")
        except (OSError, UnicodeDecodeError) as error:
            print("theme cannot be read: %s" % error, file=sys.stderr)
            return 1

    pages, skipped = render(args.brand, theme)
    for message in skipped:
        print("SKIPPED %s" % message)
    for key in pages:
        print("%s: %s" % (key, pages[key]))
    if not pages:
        print("no plates to render", file=sys.stderr)
        return 1
    if args.open_page:
        target = pages.get(args.open_page)
        if target is None:
            print("no page '%s'; rendered: %s" % (args.open_page, ", ".join(pages)),
                  file=sys.stderr)
            return 1
        webbrowser.open("file://" + os.path.abspath(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
