"""Tests for scripts/render_carrier.py."""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
_spec = importlib.util.spec_from_file_location(
    "render_carrier", os.path.join(SKILL, "scripts", "render_carrier.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><circle cx="4" cy="4" r="%d"/></svg>'
LISTENER = "addEventListener('message'"


class Carrier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        for number, name in enumerate(("full", "dark", "mark", "mono"), 1):
            self.put(name + ".svg", '<?xml version="1.0"?>\n' + SVG % number)
        self.data = {"name": "Ґрунт", "promise": "Tools that <get> out of your way",
                     "paragraph": "One paragraph & no more.", "button": "See it"}
        self.out = os.path.join(self.tmp, "out", "variant-1.html")

    def put(self, name, text):
        with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_mode(self, mode, data):
        self.put("data.json", json.dumps(data))
        return rc.main([mode, os.path.join(self.tmp, "data.json"), self.out])

    def render(self, mode="carrier", **extra):
        self.assertEqual(self.run_mode(mode, dict(self.data, **extra)), 0)
        with open(self.out, encoding="utf-8") as handle:
            return handle.read()

    def refused(self, mode="carrier", **extra):
        data = {key: value for key, value in dict(self.data, **extra).items()
                if value is not None}
        self.assertEqual(self.run_mode(mode, data), 1)
        self.assertFalse(os.path.exists(self.out))

    def test_neutral_carrier(self):
        text = self.render()
        self.assertIn("--bg:#FFFFFF;--fg:#111111;--accent:#111111;--on-accent:#FFFFFF", text)
        self.assertIn('html[data-theme="dark"]{--bg:#111111;--fg:#FFFFFF', text)
        self.assertIn('<span class="name">Ґрунт</span>', text)
        self.assertIn("Tools that &lt;get&gt; out of your way", text)
        self.assertIn("One paragraph &amp; no more.", text)
        self.assertIn(LISTENER, text)
        self.assertNotIn("http", text.replace("http://www.w3.org", ""))
        self.assertNotIn("{{", text)

    def test_colors_fonts_logo_and_motto(self):
        text = self.render(
            logo="full.svg", logo_dark="dark.svg", motto="Думай <інакше>.", lang="uk",
            colors={"light": {"accent": "#FFEE00"}, "dark": {"background": "#000000"}},
            fonts={"display": "Fraunces", "text": "Inter", "css": "../fonts/fonts.css"})
        self.assertIn('<html lang="uk"', text)
        self.assertIn("--accent:#FFEE00;--on-accent:#111111", text)  # dark label on yellow
        self.assertIn('--bg:#000000', text)
        self.assertIn('--display:"Fraunces",', text)
        self.assertIn('<link rel="stylesheet" href="../fonts/fonts.css">', text)
        self.assertIn('<circle cx="4" cy="4" r="1"/>', text)
        self.assertIn('<circle cx="4" cy="4" r="2"/>', text)
        self.assertIn('class="has-dark"', text)
        self.assertNotIn("<?xml", text)
        self.assertIn("Думай &lt;інакше&gt;.", text)

    def test_google_fonts_while_the_pair_is_open(self):
        address = "https://fonts.googleapis.com/css2?family=Inter&display=swap"
        text = self.render(fonts={"text": "Inter", "css": address})
        self.assertIn('href="https://fonts.googleapis.com/css2?family=Inter&amp;display=swap"',
                      text)

    def test_other_remote_stylesheet_is_refused(self):
        self.refused(fonts={"css": "https://example.com/fonts.css"})
        self.refused(fonts={"css": "//example.com/fonts.css"})

    def test_family_name_cannot_break_out(self):
        self.refused(fonts={"display": 'X";}</style>'})

    def test_unknown_key(self):
        self.refused(headline="x")
        self.refused(colors={"light": {"link": "#000000"}})
        self.refused(colors={"sepia": {}})

    def test_missing_name(self):
        self.refused(name=None)
        self.refused(name="  ")

    def test_bad_color(self):
        self.refused(colors={"light": {"accent": "blue"}})
        self.refused(colors={"light": {"accent": 5}})
        self.refused(colors={"light": "#000000"})

    def test_missing_logo_file(self):
        self.refused(logo="nowhere.svg")

    def test_logo_dark_needs_logo(self):
        self.refused(logo_dark="dark.svg")

    def test_logo_with_a_script_is_refused(self):
        self.put("full.svg", '<svg><script>alert(1)</script></svg>')
        self.refused(logo="full.svg")
        self.put("full.svg", '<svg onload="alert(1)"></svg>')
        self.refused(logo="full.svg")

    def test_file_that_is_not_svg(self):
        self.put("full.svg", "PNG")
        self.refused(logo="full.svg")

    def test_sheet(self):
        self.data = {"name": "Ґрунт", "full": "full.svg", "mark": "mark.svg",
                     "dark": "dark.svg", "mono": "mono.svg"}
        text = self.render("sheet")
        self.assertEqual(text.count('r="1"/>'), 2)   # large, and in the light header
        self.assertEqual(text.count('r="2"/>'), 2)   # on dark, and in the dark header
        self.assertEqual(text.count('r="3"/>'), 4)   # alone, and at three sizes
        self.assertEqual(text.count('r="4"/>'), 3)   # the one-color mark at three sizes on dark
        for size in (24, 32, 48):
            self.assertIn('<svg style="height:%dpx"' % size, text)
        self.assertIn("In a header", text)
        self.assertIn(LISTENER, text)
        self.assertNotIn("{{", text)

    def test_sheet_without_dark_and_mono(self):
        self.data = {"name": "A", "full": "full.svg", "mark": "mark.svg",
                     "header_label": "У шапці"}
        text = self.render("sheet")
        self.assertEqual(text.count('r="1"/>'), 4)
        self.assertIn("sizes light wide", text)
        self.assertNotIn("sizes dark", text.split("</style>")[1])
        self.assertIn("У шапці", text)

    def test_sheet_needs_the_mark(self):
        self.data = {"name": "A", "full": "full.svg"}
        self.refused("sheet")

    def test_usage_and_unreadable_data(self):
        self.assertEqual(rc.main([]), 1)
        self.assertEqual(rc.main(["poster", "a", "b"]), 1)
        self.assertEqual(rc.main(["carrier", os.path.join(self.tmp, "none.json"), self.out]), 2)
        self.put("data.json", "{not json")
        self.assertEqual(rc.main(["carrier", os.path.join(self.tmp, "data.json"), self.out]), 2)


if __name__ == "__main__":
    unittest.main()
