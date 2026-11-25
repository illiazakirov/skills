"""Tests for scripts/extract_style.py. Nothing here touches the network."""

import contextlib
import importlib.util
import io
import os
import shutil
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
_spec = importlib.util.spec_from_file_location(
    "extract_style", os.path.join(SKILL, "scripts", "extract_style.py"))
es = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(es)

CSS = """
body { color: #FFF; background: #ffffff; font-family: "Inter Tight", Helvetica, sans-serif }
h1 { color: rgb(255, 0, 0); font-family: 'Inter Tight', system-ui }
a { border-color: rgba(0,128,0,.5); font: italic 700 16px/1.2 Georgia, serif }
"""

PAGE = """<html><head>
<style>h2{color:#0000ff}</style>
<link rel="stylesheet" href="a.css">
<link href="/deep/b.css" rel="stylesheet preload">
<link rel="icon" href="favicon.ico">
</head><body style="color:#111111"><p>#abcdef is not a color here</p></body></html>"""


class Extract(unittest.TestCase):
    def test_colors_are_normalized_and_counted(self):
        colors, _ = es.extract(CSS)
        self.assertEqual(colors, [("#ffffff", 2), ("#008000", 1), ("#ff0000", 1)])

    def test_fonts_drop_generics_and_quotes(self):
        _, fonts = es.extract(CSS)
        self.assertEqual(fonts, [("Inter Tight", 2), ("Georgia", 1), ("Helvetica", 1)])

    def test_eight_digit_hex_drops_the_alpha(self):
        self.assertEqual(es.extract("a{color:#11223380}")[0], [("#112233", 1)])

    def test_selectors_are_not_colors(self):
        self.assertEqual(es.extract("#add{color:#123456}\n#face,#bad123 a{margin:0}")[0],
                         [("#123456", 1)])

    def test_comments_are_ignored(self):
        colors, fonts = es.extract("/* font-family: Ghost; color:#111111 */ a{color:#222222}")
        self.assertEqual((colors, fonts), ([("#222222", 1)], []))

    def test_fully_transparent_is_not_black(self):
        self.assertEqual(es.extract("a{color:rgba(0,0,0,0);b:rgb(0 0 0 / 0%)}")[0], [])

    def test_hsl_and_percent_rgb(self):
        colors = dict(es.extract("a{color:hsl(0, 100%, 50%);b:hsl(120deg 100% 25%);"
                                 "c:rgb(100%, 0%, 0%)}")[0])
        self.assertEqual(colors, {"#ff0000": 2, "#008000": 1})

    def test_oklch(self):
        colors = [value for value, _ in es.extract("a{color:oklch(1 0 0);b:oklch(0 0 0);"
                                                   "c:oklch(62.8% 0.2577 29.23)}")[0]]
        self.assertIn("#ffffff", colors)
        self.assertIn("#000000", colors)
        red = [c for c in colors if c not in ("#ffffff", "#000000")][0]
        self.assertGreater(int(red[1:3], 16), 245)
        self.assertLess(int(red[3:5], 16), 25)
        self.assertLess(int(red[5:7], 16), 25)

    def test_fonts_in_custom_properties(self):
        fonts = es.extract(":root{--font-sans:'Sohne', sans-serif;--radius:4px}"
                           "a{font-family:var(--font-sans)}")[1]
        self.assertEqual(fonts, [("Sohne", 1)])

    def test_font_shorthand_with_a_function_size(self):
        fonts = es.extract("a{font:500 clamp(1rem, 2vw, 2rem)/1.1 Inter Display, serif}")[1]
        self.assertEqual(fonts, [("Inter Display", 1)])

    def test_nothing_found(self):
        self.assertEqual(es.extract("a{display:none}"), ([], []))


class Collect(unittest.TestCase):
    def fetch(self, pages, asked):
        def fetch(url):
            asked.append(url)
            if url not in pages:
                raise OSError("no such page")
            return pages[url]
        return fetch

    def test_page_gives_its_styles_and_linked_sheets(self):
        asked = []
        css = es.collect("https://example.test/shop/", self.fetch({
            "https://example.test/shop/": PAGE,
            "https://example.test/shop/a.css": "a{color:#00ff00}",
            "https://example.test/deep/b.css": "b{color:#ff00ff}"}, asked))
        colors = dict(es.extract(css)[0])
        self.assertEqual(set(colors), {"#0000ff", "#111111", "#00ff00", "#ff00ff"})
        self.assertNotIn("https://example.test/shop/favicon.ico", asked)

    def test_a_sheet_that_cannot_be_fetched_is_skipped(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            css = es.collect("https://example.test/shop/", self.fetch({
                "https://example.test/shop/": PAGE,
                "https://example.test/shop/a.css": "a{color:#00ff00}"}, []))
        self.assertIn("#00ff00", css)
        self.assertIn("https://example.test/deep/b.css", err.getvalue())

    def test_stylesheet_that_mentions_tags_is_still_a_stylesheet(self):
        sheet = "/* <p> note */ a:after{content:'<div>';color:#00ff00}"
        css = es.collect("https://example.test/a.css",
                         self.fetch({"https://example.test/a.css": sheet}, []))
        self.assertEqual(es.extract(css)[0], [("#00ff00", 1)])

    def test_imports_are_followed_once(self):
        asked = []
        css = es.collect("https://example.test/a.css", self.fetch({
            "https://example.test/a.css": "@import url('b.css');@import \"a.css\";"
                                          "a{color:#00ff00}",
            "https://example.test/b.css": "b{color:#ff00ff}"}, asked))
        self.assertEqual(set(dict(es.extract(css)[0])), {"#00ff00", "#ff00ff"})
        self.assertEqual(asked.count("https://example.test/a.css"), 1)

    def test_stylesheet_is_taken_as_it_is(self):
        css = es.collect("https://example.test/a.css",
                         self.fetch({"https://example.test/a.css": "a{color:#00ff00}"}, []))
        self.assertEqual(css.strip(), "a{color:#00ff00}")


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = es.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_local_stylesheet(self):
        code, out, _ = self.run_main(self.write("site.css", CSS))
        self.assertEqual(code, 0)
        self.assertIn("## Colors\n\n- #ffffff (2)\n", out)
        self.assertIn("## Fonts\n\n- Inter Tight (2)\n", out)

    def test_local_page_with_a_linked_local_sheet(self):
        self.write("a.css", "a{color:#00ff00}")
        code, out, _ = self.run_main(self.write("index.html",
                                                '<link rel="stylesheet" href="a.css">'))
        self.assertEqual(code, 0)
        self.assertIn("- #00ff00 (1)", out)

    def test_top_limits_each_list(self):
        code, out, _ = self.run_main(self.write("site.css", CSS), "--top", "1")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("\n- "), 2)

    def test_missing_source_exits_two(self):
        code, _, err = self.run_main(os.path.join(self.tmp, "nowhere.css"))
        self.assertEqual(code, 2)
        self.assertIn("cannot be read", err)

    def test_nothing_found_exits_one(self):
        code, _, _ = self.run_main(self.write("empty.css", "a{display:none}"))
        self.assertEqual(code, 1)

    def test_no_argument_exits_two(self):
        self.assertEqual(self.run_main()[0], 2)


if __name__ == "__main__":
    unittest.main()
