"""Tests for scripts/render_book.py. They run without Chrome: the fixture's pipeline says
screenshots: manual, and its review/shots/ holds placeholder images."""

import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
VALID = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand")

_spec = importlib.util.spec_from_file_location(
    "render_book", os.path.join(SKILL, "scripts", "render_book.py"))
rb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rb)


def run(args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = rb.main(args)
    return code, out.getvalue() + err.getvalue()


class RenderBook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.brand = os.path.join(self.tmp, "brand")
        shutil.copytree(VALID, self.brand)
        self.step = os.path.join(self.brand, "05-brand-book")
        for name in ("index.html", "brand-book.md"):
            os.remove(os.path.join(self.step, name))
        os.remove(os.path.join(self.step, "review", "source.html"))

    def read(self, *parts):
        with open(os.path.join(self.step, *parts), encoding="utf-8") as handle:
            return handle.read()

    def replace(self, relative, old, new):
        path = os.path.join(self.brand, *relative.split("/"))
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new, 1))

    def assertNothingWritten(self):
        for name in ("index.html", "brand-book.md"):
            self.assertFalse(os.path.exists(os.path.join(self.step, name)), name)

    def test_the_book_names_the_paths_of_the_kit(self):
        code, out = run([self.brand, "--approve"])
        self.assertEqual(code, 0, out)
        page = self.read("index.html")
        self.assertIn("Path in the kit", page)
        self.assertNotIn("Path in brand/", page)
        self.assertIn("tokens/tokens.json", page)

    def test_builds_the_fixture_book(self):
        code, out = run([self.brand, "--approve"])
        self.assertEqual(code, 0, out)
        for name in ("index.html", "brand-book.md"):
            with open(os.path.join(VALID, "05-brand-book", name), encoding="utf-8") as handle:
                self.assertEqual(self.read(name), handle.read(), name)
        self.assertIn("NOTE    no Chrome, so no PDF", out)

    def test_the_page_is_self_contained(self):
        run([self.brand])
        page = self.read("index.html")
        self.assertNotIn("<iframe", page)
        self.assertNotIn('src="../', page)
        self.assertNotIn('src="shots/', page)
        self.assertIn('src="data:image/png;base64,', page)
        self.assertIn('src="data:image/svg+xml;base64,', page)
        self.assertNotRegex(page, r'(src|href)="https?://')

    def test_the_order_of_the_book_and_its_numbers(self):
        run([self.brand])
        page = self.read("index.html")
        parts = re.findall(r'<h2 class="part" id="([^"]+)">', page)
        self.assertEqual(parts, ["01-strategy", "02-brand-platform", "03-identity",
                                 "04-design-system", "how"])
        numbers = [int(n) for n in re.findall(r'<span class="num">(\d+)</span>', page)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        for anchor in ('id="cover"', 'id="strategy"', 'id="golden-circle"', 'id="platform"',
                       'id="identity"', 'id="surface-site-hero"', 'id="interface"',
                       'id="page-sign-up"', 'id="how-to-use"'):
            self.assertIn(anchor, page)
        self.assertLess(page.index('id="strategy"'), page.index('id="golden-circle"'))

    def review_surfaces(self, items):
        import json
        path = os.path.join(self.brand, "03-identity", "review", "surfaces-01.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"items": [{"file": "../surfaces/site-hero.html", "width": w, "height": h}
                                 for w, h in items]}, handle)

    def test_a_surface_reviewed_at_two_sizes_is_shown_at_both(self):
        self.review_surfaces([(1440, 900), (390, 844)])
        code, out = run([self.brand])
        self.assertEqual(code, 1, out)
        self.assertIn("surface-site-hero-390.png (03-identity/surfaces/site-hero.html, "
                      "390 x 844)", out)
        shots = os.path.join(self.step, "review", "shots")
        shutil.copy(os.path.join(shots, "page-landing-390.png"),
                    os.path.join(shots, "surface-site-hero-390.png"))
        code, out = run([self.brand])
        self.assertEqual(code, 0, out)
        source = self.read("review", "source.html")
        block = source[source.index('id="surface-site-hero"'):source.index('id="interface"')]
        self.assertIn('src="shots/surface-site-hero.png" alt="site hero at 1440"', block)
        self.assertIn('<div class="phone"><img src="shots/surface-site-hero-390.png"', block)
        self.assertEqual(source.count('id="surface-site-hero"'), 1)

    def test_a_narrow_surface_is_cut_back_to_its_own_width(self):
        self.review_surfaces([(400, 400)])
        code, out = run([self.brand])
        self.assertEqual(code, 0, out)
        self.assertIn('alt="site hero" loading="lazy" style="aspect-ratio:400/400;'
                      'width:min(100%,400px);object-fit:cover;object-position:left top"',
                      self.read("review", "source.html"))

    def test_the_logo_of_identity_on_one_page_follows_the_theme(self):
        run([self.brand])
        source = self.read("review", "source.html")
        block = source[source.index('id="identity"'):source.index('id="logo"')]
        self.assertIn('<img class="logo-light" src="../../03-identity/logo/full.svg"', block)
        self.assertIn('<img class="logo-dark" src="../../03-identity/logo/dark.svg"', block)

    def test_every_strategy_plate_is_a_scene_of_its_own(self):
        run([self.brand])
        source = self.read("review", "source.html")
        for key, world in (("golden-circle", "core"), ("lean-canvas", "canvas"),
                           ("icp", "person"), ("positioning", "field"),
                           ("brand-wheel", "orbit"), ("marketing-mix", "stack"),
                           ("messaging", "promise")):
            self.assertIn('<section class="scene w-%s" id="%s"' % (world, key), source)
        self.assertEqual(source.count('class="scene w-part"'), 5)

    def test_motion_is_an_addition(self):
        """Without JavaScript, with reduced motion and in print the book is a plain page:
        every rule that hides or pins sits under .motion, inside a screen media query."""
        css = rb.bs.CSS
        screen = css.index("@media screen{")
        plain = css[:screen] + css[css.index("@media print{"):]
        self.assertNotIn(".motion", plain)
        self.assertNotIn("opacity:0", plain)
        self.assertIn("prefers-reduced-motion", rb.bs.JS)

    def test_a_plate_that_does_not_fit_its_scene_is_drawn_as_on_the_map(self):
        plate = {"name": "golden-circle.md", "title": "Golden Circle", "step": "01-strategy",
                 "status": "approved", "slots": []}
        self.assertIsNone(rb.bs.scene(plate))
        self.assertIsNone(rb.bs.scene(dict(plate, name="logo.md")))

    def test_the_printed_book_is_fixed_pages_with_the_numbers_of_the_screen(self):
        run([self.brand])
        paper, screen = self.read("review", "print.html"), self.read("review", "source.html")
        self.assertIn("@page{size:1280px 720px;margin:0}", paper)
        pages = re.findall(r'<section class="pg pg-([a-z]+)[^"]*" data-page="(\d+)"', paper)
        self.assertEqual([int(n) for _kind, n in pages], list(range(1, len(pages) + 1)))
        kinds = [kind for kind, _n in pages]
        self.assertEqual(kinds[:3], ["cover", "contents", "part"])
        self.assertEqual(kinds.count("part"), 5)
        blocks = sorted(set(int(n) for n in re.findall(r"<span>Block (\d+)</span>", paper)))
        on_screen = [int(n) for n in re.findall(r'<span class="num">(\d+)</span>', screen)]
        self.assertEqual(blocks, on_screen[1:])     # the cover, block 1, carries no number
        self.assertIn("%d / %d" % (len(pages), len(pages)), paper)
        self.assertNotIn("Fixture: the Aqua interface", paper)

    def test_the_printed_book_drops_the_rules_for_narrow_screens(self):
        css = "a{b:c}@media (max-width:820px){.x{y:z}.q{r:s}}d{e:f}@media print{g{h:i}}"
        self.assertEqual(rb.bp.wide_only(css), "a{b:c}d{e:f}@media print{g{h:i}}")
        run([self.brand])
        self.assertNotIn("@media (max-width", self.read("review", "print.html"))

    def test_a_long_plate_goes_on_to_a_page_of_the_same_shape(self):
        cells = [(400, "a"), (400, "b"), (400, "c"), (900, "d")]
        self.assertEqual(rb.bp.cut(cells, 1000, 1500), [["a", "b"], ["c", "d"]])
        self.assertEqual(rb.bp.cut([(5000, "a")], 1000, 1500), [["a"]])

    def test_pages_the_fitting_could_not_save_are_read_from_the_dom(self):
        dom = ('<section class="pg pg-plate first" data-page="7" data-overflow="1" style="">'
               '<section class="pg pg-wall" data-page="8">')
        self.assertEqual(rb.bp.overflowing(dom), [7])

    def test_slots_only_never_the_rationale(self):
        run([self.brand])
        page, text = self.read("index.html"), self.read("brand-book.md")
        for rationale in ("Fixture: the Aqua interface",):
            self.assertNotIn(rationale, page)
            self.assertNotIn(rationale, text)
        self.assertIn("Controls you want to touch", page)
        self.assertNotIn('<span class="status">draft</span>', page)

    def test_the_fixed_text_of_how_to_use_this(self):
        run([self.brand])
        text = self.read("brand-book.md")
        path = os.path.join(ROOT, "docs", "marketing", "brand", "design", "brand-book.md")
        if not os.path.isfile(path):
            self.skipTest("local design document missing: docs/marketing/brand/design/brand-book.md")
        design = open(path, encoding="utf-8").read()
        approved = design[design.index("**Read first.**"):design.index("Under the text")].strip()
        self.assertIn(approved, text)
        self.assertIn("| Tokens | `04-design-system/tokens.json (the source), tokens.css "
                      "(generated)` |", text)

    def test_markdown_has_the_sections_the_contract_wants(self):
        run([self.brand])
        text = self.read("brand-book.md")
        found = re.findall(r"(?m)^## (.+)$", text)
        self.assertEqual(found, rb.cc.MARKDOWN["05-brand-book"]["brand-book.md"][1])
        self.assertIn("status: draft", text)
        self.assertIn("| `color.accent` | color | #0095B6 |  |  |", text)
        self.assertIn("| `color.bg` | color | #FFFFFF | #000000 |  |", text)
        self.assertIn("| `type.headline` | typography | 72px / 1.05 |  | 40px / 1.08 |", text)

    def test_the_theme_follows_the_switch_and_prints_light(self):
        run([self.brand])
        page = self.read("index.html")
        self.assertIn(':root[data-theme="dark"]{--paper:#000000;--ink:#FFFFFF}', page)
        self.assertIn('@media print{:root,:root[data-theme="dark"]{--paper:#FFFFFF', page)
        self.assertNotIn("prefers-color-scheme:dark){:root", page)
        self.assertIn("theme-switch", page)

    def test_a_draft_plate_stops_the_book(self):
        self.replace("01-strategy/messaging.md", "status: approved", "status: draft")
        code, out = run([self.brand])
        self.assertEqual(code, 1)
        self.assertIn("01-strategy/messaging.md is a draft", out)
        self.assertNothingWritten()

    def test_an_identity_that_is_not_approved_stops_the_book(self):
        text = open(os.path.join(self.brand, "pipeline.yaml"), encoding="utf-8").read()
        start = text.index("  03-identity:")
        text = text[:start] + text[start:].replace("status: approved", "status: in-progress", 1)
        with open(os.path.join(self.brand, "pipeline.yaml"), "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out = run([self.brand])
        self.assertEqual(code, 1)
        self.assertIn("the identity is not approved", out)

    def test_missing_screenshots_are_named(self):
        os.remove(os.path.join(self.step, "review", "shots", "page-sign-in-390.png"))
        code, out = run([self.brand])
        self.assertEqual(code, 1)
        self.assertIn("page-sign-in-390.png (04-design-system/reference/pages/sign-in.html, "
                      "390 x 844)", out)
        self.assertNothingWritten()

    def test_missing_system_pages_stop_the_book(self):
        shutil.rmtree(os.path.join(self.brand, "04-design-system", "reference", "pages"))
        code, out = run([self.brand])
        self.assertEqual(code, 1)
        self.assertIn("run render_system.py build", out)

    def test_copy_in_the_market_language_is_escaped(self):
        self.replace("03-identity/motto.md", "Think different.", "Думай <інакше> & так.")
        code, out = run([self.brand])
        self.assertEqual(code, 0, out)
        page = self.read("index.html")
        self.assertIn("Думай &lt;інакше&gt; &amp; так.", page)
        self.assertNotIn("<інакше>", page)

    def test_rendering_keeps_the_versions_of_earlier_steps(self):
        before = {step: rb.cc.step_version(os.path.join(self.brand, step))
                  for step in rb.cc.STEPS[:5]}
        run([self.brand])
        for step, version in before.items():
            self.assertEqual(rb.cc.step_version(os.path.join(self.brand, step)), version, step)


SANDBOXED_CHROME = """#!%s
import sys
args = sys.argv[1:]
if "--single-process" not in args or any(a.startswith("--virtual-time-budget") for a in args):
    import os
    os.abort()
pdf = [a.split("=", 1)[1] for a in args if a.startswith("--print-to-pdf=")]
if pdf:
    open(pdf[0], "wb").write(b"%%PDF-1.4 book")
else:
    sys.stdout.write('<section class="pg spread" data-page="7" data-overflow="1"></section>')
"""


class SandboxedChrome(unittest.TestCase):
    """A sandbox that kills Chrome at start (Codex's): the book is printed in one process."""

    def setUp(self):
        import stat
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.chrome = os.path.join(self.tmp, "chrome")
        with open(self.chrome, "w") as handle:
            handle.write(SANDBOXED_CHROME % sys.executable)
        os.chmod(self.chrome, os.stat(self.chrome).st_mode | stat.S_IEXEC)
        self.page = os.path.join(self.tmp, "print.html")
        open(self.page, "w").close()

    def test_the_pdf_is_printed_in_one_process(self):
        output = os.path.join(self.tmp, "book.pdf")
        self.assertIsNone(rb.print_pdf(self.chrome, self.page, output))
        self.assertTrue(os.path.getsize(output) > 0)

    def test_the_dom_is_read_in_one_process(self):
        self.assertEqual(rb.overflowing_pages(self.chrome, self.page), [7])


if __name__ == "__main__":
    unittest.main()
