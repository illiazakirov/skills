"""Tests for scripts/bundle_html.py."""

import base64
import importlib.util
import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
_spec = importlib.util.spec_from_file_location(
    "bundle_html", os.path.join(SKILL, "scripts", "bundle_html.py"))
bh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bh)

PAGE = """<!doctype html><html><head>
<link rel="stylesheet" href="../fonts/fonts.css">
<link href='tokens.css' rel='stylesheet'>
<style>.hero { background: url("shots/hero.png"); }</style>
</head><body>
<img alt="Logo" src="../logo/full.svg">
<img src="data:image/png;base64,AAAA">
<a href="../04-design-system/reference/index.html">Design system</a>
<a href="https://example.com/">Site</a>
<script src="page.js"></script>
<script>var inline = 1;</script>
</body></html>
"""


class Bundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.write("fonts/fonts.css", "@font-face { src: url(inter.woff2) format('woff2'); }")
        self.write("fonts/inter.woff2", b"FONT")
        self.write("logo/full.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>")
        self.write("book/tokens.css", ":root { --bg: #fff; }")
        self.write("book/shots/hero.png", b"PNG")
        self.write("book/page.js", "var a = '</script>';")
        self.source = self.write("book/source.html", PAGE)
        self.output = os.path.join(self.tmp, "book", "index.html")

    def write(self, relative, content):
        path = os.path.join(self.tmp, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if isinstance(content, bytes) else "w") as handle:
            handle.write(content)
        return path

    def run_main(self, page=None):
        if page is not None:
            self.write("book/source.html", page)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = bh.main([self.source, self.output])
        return code, out.getvalue() + err.getvalue()

    def result(self):
        with open(self.output, encoding="utf-8") as handle:
            return handle.read()

    def assertProblem(self, page, fragment):
        code, out = self.run_main(page)
        self.assertEqual(code, 1, out)
        self.assertIn(fragment, out)
        self.assertFalse(os.path.exists(self.output))

    def test_everything_local_is_embedded(self):
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        page = self.result()
        font = base64.b64encode(b"FONT").decode()
        self.assertIn("url(data:font/woff2;base64,%s)" % font, page)
        self.assertIn(":root { --bg: #fff; }", page)
        self.assertIn("url(data:image/png;base64,%s)" % base64.b64encode(b"PNG").decode(), page)
        self.assertIn('src="data:image/svg+xml;base64,', page)
        self.assertIn("var a = '<\\/script>';", page)
        self.assertIn("var inline = 1;", page)
        self.assertNotIn("<link", page)
        self.assertNotIn("page.js", page)
        self.assertNotIn("fonts.css", page)

    def test_links_and_existing_data_uris_are_kept(self):
        self.run_main()
        page = self.result()
        self.assertIn('href="../04-design-system/reference/index.html"', page)
        self.assertIn('href="https://example.com/"', page)
        self.assertIn('src="data:image/png;base64,AAAA"', page)

    def test_missing_file(self):
        self.assertProblem(PAGE.replace("tokens.css", "absent.css"), "does not exist: absent.css")

    def test_missing_font_inside_a_stylesheet(self):
        os.remove(os.path.join(self.tmp, "fonts", "inter.woff2"))
        self.assertProblem(None, "does not exist: inter.woff2")

    def test_remote_resources_are_refused(self):
        self.assertProblem(PAGE.replace("../fonts/fonts.css",
                                        "https://fonts.googleapis.com/css2?family=Inter"),
                           "loads from a remote server")
        self.assertProblem(PAGE.replace("../logo/full.svg", "//cdn.example/logo.svg"),
                           "loads from a remote server")

    def test_frames_are_refused(self):
        self.assertProblem(PAGE.replace("<body>", '<body><iframe src="x.html"></iframe>'),
                           "in a frame")

    def test_import_is_refused(self):
        self.assertProblem(PAGE.replace(".hero {", "@import 'x.css'; .hero {"), "@import")

    def test_usage(self):
        for args in ([], [self.source], [self.source, self.source],
                     [self.source, os.path.join(self.tmp, "out.txt")],
                     [os.path.join(self.tmp, "absent.html"), self.output]):
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(bh.main(args), 2, args)


if __name__ == "__main__":
    unittest.main()
