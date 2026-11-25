"""Tests for scripts/render_system.py."""

import importlib.util
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
VALID = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand")

_spec = importlib.util.spec_from_file_location(
    "render_system", os.path.join(SKILL, "scripts", "render_system.py"))
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)

PAGES = ("index.html", "sheet.html", "pages/landing.html", "pages/sign-in.html",
         "pages/sign-up.html")


def run(args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = rs.main(args)
    return code, out.getvalue() + err.getvalue()


class RenderSystem(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.brand = os.path.join(self.tmp, "brand")
        shutil.copytree(VALID, self.brand)
        self.step = os.path.join(self.brand, "04-design-system")
        shutil.rmtree(os.path.join(self.step, "reference"))

    def read(self, *parts):
        with open(os.path.join(self.step, *parts), encoding="utf-8") as handle:
            return handle.read()

    def edit_json(self, name, change):
        path = os.path.join(self.step, name)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        change(data)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)

    def test_build_writes_every_page(self):
        code, out = run(["build", self.brand])
        self.assertEqual(code, 0, out)
        for name in PAGES + ("system.css",):
            self.assertTrue(os.path.isfile(os.path.join(self.step, "reference", name)), name)

    def test_build_matches_the_fixture(self):
        run(["build", self.brand])
        for name in PAGES + ("system.css",):
            with open(os.path.join(VALID, "04-design-system", "reference", name),
                      encoding="utf-8") as handle:
                self.assertEqual(self.read("reference", name), handle.read(), name)

    def test_pages_load_tokens_fonts_and_components_by_relative_path(self):
        run(["build", self.brand])
        index = self.read("reference", "index.html")
        self.assertIn('href="../tokens.css"', index)
        self.assertIn('href="system.css"', index)
        self.assertIn('href="../../03-identity/fonts/fonts.css"', index)
        landing = self.read("reference", "pages", "landing.html")
        self.assertIn('href="../../tokens.css"', landing)
        self.assertIn('href="../system.css"', landing)
        self.assertIn('src="../../../03-identity/logo/full.svg"', landing)
        self.assertIn('src="../../../03-identity/logo/dark.svg"', landing)
        for name in PAGES:
            self.assertNotIn("http", self.read("reference", name).replace(
                "http://www.w3.org/2000/svg", ""), name)

    def test_every_page_has_the_themes_and_the_listener(self):
        run(["build", self.brand])
        for name in PAGES:
            page = self.read("reference", name)
            self.assertIn("brandTheme", page, name)
            self.assertIn("prefers-color-scheme: dark", page, name)
        self.assertIn("theme-switch", self.read("reference", "index.html"))

    def test_the_system_page_numbers_every_block(self):
        run(["build", self.brand])
        index = self.read("reference", "index.html")
        numbers = [int(n) for n in re.findall(r'<span class="num">(\d+)</span>', index)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        for part in ("Foundations", "Atoms", "Molecules", "Organisms", "Pages"):
            self.assertIn(">%s</h2>" % part, index)
        for name in rs.cc.COMPONENTS["Atoms"] + rs.cc.COMPONENTS["Organisms"]:
            self.assertIn(">%s</h3>" % name, index)
        self.assertIn("color.on-accent on color.accent, light</td><td>6 to 1", index)

    def test_copy_is_escaped_and_whole(self):
        self.edit_json("copy.json", lambda d: d["hero"].update(
            {"headline": 'Думай <інакше> & "краще"'}))
        run(["build", self.brand])
        landing = self.read("reference", "pages", "landing.html")
        self.assertIn("Думай &lt;інакше&gt; &amp; &quot;краще&quot;", landing)
        self.assertNotIn("<інакше>", landing)

    def test_missing_role_writes_nothing(self):
        self.edit_json("tokens.json", lambda d: d["color"].pop("info-bg"))
        code, out = run(["build", self.brand])
        self.assertEqual(code, 1)
        self.assertIn("color.info-bg", out)
        self.assertFalse(os.path.exists(os.path.join(self.step, "reference")))

    def test_weak_contrast_writes_nothing(self):
        def change(d):
            d["color"]["text-muted"] = {"$value": {"colorSpace": "srgb",
                                                   "components": [0.8, 0.8, 0.8]}}
        self.edit_json("tokens.json", change)
        code, out = run(["build", self.brand])
        self.assertEqual(code, 1)
        self.assertIn("color.text-muted on color.bg, light", out)

    def test_missing_copy_key_writes_nothing(self):
        self.edit_json("copy.json", lambda d: d["sign_up"].pop("error"))
        code, out = run(["build", self.brand])
        self.assertEqual(code, 1)
        self.assertIn("missing key 'error' in copy.json.sign_up", out)
        self.assertFalse(os.path.exists(os.path.join(self.step, "reference")))

    def test_unknown_copy_key(self):
        self.edit_json("copy.json", lambda d: d.update({"tagline": "x"}))
        code, out = run(["build", self.brand])
        self.assertEqual(code, 1)
        self.assertIn("unknown key 'tagline'", out)

    def test_out_of_date_tokens_css(self):
        with open(os.path.join(self.step, "tokens.css"), "a", encoding="utf-8") as handle:
            handle.write("/* edited */\n")
        code, out = run(["build", self.brand])
        self.assertEqual(code, 1)
        self.assertIn("tokens.css is out of date", out)

    def test_without_logo_and_fonts_the_name_stands_in(self):
        shutil.rmtree(os.path.join(self.brand, "03-identity", "logo"))
        shutil.rmtree(os.path.join(self.brand, "03-identity", "fonts"))
        code, out = run(["build", self.brand])
        self.assertEqual(code, 0, out)
        self.assertIn("NOTE    the identity has no logo/full.svg", out)
        self.assertIn("NOTE    the identity has no fonts/fonts.css", out)
        landing = self.read("reference", "pages", "landing.html")
        self.assertIn('<a class="brand" href="#">Apple</a>', landing)
        self.assertNotIn("fonts.css", landing)

    def test_sheet_of_a_variant_inlines_its_tokens(self):
        variant = os.path.join(self.step, "review", "interface-01", "variant-1.html")
        tokens = os.path.join(self.step, "tokens.json")
        code, out = run(["sheet", tokens, variant, "--brand", self.brand])
        self.assertEqual(code, 0, out)
        with open(variant, encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn("--color-accent: var(--palette-bondi-blue);", page)
        self.assertIn(".button-primary{", page)
        self.assertIn('href="../../../03-identity/fonts/fonts.css"', page)
        self.assertIn("This address already has an account.", page)
        self.assertNotIn('href="../tokens.css"', page)

    def test_icons_carry_no_script_and_take_the_stroke_token(self):
        for name in rs.ICONS:
            svg = rs.icon(name)
            self.assertNotIn("<script", svg, name)
            self.assertNotIn("stroke-width=", svg, name)
            self.assertIn('class="icon"', svg, name)
        self.assertTrue(os.path.isfile(os.path.join(rs.TEMPLATES, "icons", "LICENSE")))


if __name__ == "__main__":
    unittest.main()
