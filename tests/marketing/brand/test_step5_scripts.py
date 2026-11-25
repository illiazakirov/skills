"""Tests for scripts/render_review.py and scripts/fetch_font.py. No network is used."""

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
EXAMPLE = os.path.join(SKILL, "examples", "review-page")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, "scripts", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rr = load("render_review")
ff = load("fetch_font")


def run(function, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = function(*args, **kwargs)
    return code, out.getvalue(), err.getvalue()


class Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.dir = os.path.join(self.tmp, "review")
        shutil.copytree(EXAMPLE, self.dir)
        os.remove(os.path.join(self.dir, "surfaces-01.html"))
        self.path = os.path.join(self.dir, "surfaces-01.json")
        with open(self.path, encoding="utf-8") as handle:
            self.data = json.load(handle)

    def render(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle)
        return run(rr.main, [self.path])

    def assertProblem(self, fragment):
        code, out, _ = self.render()
        self.assertEqual(code, 1, out)
        self.assertIn(fragment, out)
        self.assertFalse(os.path.exists(self.path[:-5] + ".html"))

    def test_example_is_up_to_date(self):
        with open(rr.TEMPLATE, encoding="utf-8") as handle:
            template = handle.read()
        with open(os.path.join(EXAMPLE, "surfaces-01.html"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), rr.render(self.data, EXAMPLE, template))

    def test_renders_every_item_at_its_size(self):
        code, out, _ = self.render()
        self.assertEqual(code, 0, out)
        with open(self.path[:-5] + ".html", encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn('data-width="400" data-height="400"', page)
        self.assertIn('data-width="1200" data-height="630"', page)
        self.assertEqual(page.count('<section class="variant"'), 4)
        self.assertIn("No remarks.", page)
        self.assertNotIn("{{", page)

    def test_one_item_is_enough_and_reference_is_optional(self):
        self.data["items"] = self.data["items"][1:2]
        self.assertEqual(self.render()[0], 0)

    def test_labels(self):
        self.data["labels"] = {"critic": "Критик"}
        self.render()
        with open(self.path[:-5] + ".html", encoding="utf-8") as handle:
            self.assertIn("Критик", handle.read())

    def test_no_items(self):
        self.data["items"] = []
        self.assertProblem("'items' must be a non-empty list")

    def test_missing_size(self):
        del self.data["items"][0]["width"]
        self.assertProblem("'width' must be a whole number")

    def test_missing_file(self):
        self.data["items"][0]["file"] = "surfaces/absent.html"
        self.assertProblem("does not exist")

    def test_critic_is_required(self):
        del self.data["items"][0]["critic"]
        self.assertProblem("'critic' must be a list")

    def test_reference_needs_caption(self):
        del self.data["items"][0]["reference"]["caption"]
        self.assertProblem("'caption' is missing")

    def test_unknown_key(self):
        self.data["items"][0]["variants"] = []
        self.assertProblem("unknown key 'variants'")


CSS = """/* cyrillic */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/inter/v1/cyr.woff2) format('woff2');
  unicode-range: U+0400-045F;
}
/* latin */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/inter/v1/lat.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}
/* latin */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/inter/v1/lat.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}
"""


class Fonts(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.licensed = True
        self.requests = []

    def fetch(self, url):
        self.requests.append(url)
        if url.startswith(ff.CSS_API):
            return (400, b"") if "Missing" in url else (200, CSS.encode())
        if url.startswith(ff.LICENSES):
            return (200, b"SIL OPEN FONT LICENSE") if self.licensed and "/ofl/" in url else (404, b"")
        return 200, b"woff2:" + url.encode()

    def get(self, *args):
        return run(ff.main, list(args), fetch=self.fetch)

    def files(self):
        return sorted(os.listdir(self.dir))

    def test_downloads_files_license_and_css(self):
        code, out, _ = self.get("Inter", self.dir, "--subsets", "latin,cyrillic")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.files(), ["fonts.css", "inter-LICENSE.txt",
                                        "inter-cyrillic-normal-400.woff2",
                                        "inter-latin-normal-400.woff2"])
        with open(os.path.join(self.dir, "fonts.css")) as handle:
            css = handle.read()
        self.assertEqual(css.count("@font-face"), 3)
        self.assertIn("url(inter-latin-normal-400.woff2)", css)
        self.assertNotIn("https://", css)

    def test_only_the_named_subsets(self):
        self.get("Inter", self.dir, "--subsets", "latin")
        self.assertNotIn("inter-cyrillic-normal-400.woff2", self.files())

    def test_second_family_is_added_and_a_rerun_replaces_its_block(self):
        self.get("Inter", self.dir, "--subsets", "latin")
        self.get("Source Serif", self.dir, "--subsets", "latin")
        self.get("Inter", self.dir, "--subsets", "latin")
        with open(os.path.join(self.dir, "fonts.css")) as handle:
            css = handle.read()
        self.assertEqual(css.count("/* family: Inter */"), 1)
        self.assertEqual(css.count("/* family: Source Serif */"), 1)

    def test_missing_subset_writes_nothing(self):
        code, out, _ = self.get("Inter", self.dir, "--subsets", "latin,greek")
        self.assertEqual(code, 1)
        self.assertIn("has no greek subset", out)
        self.assertEqual(self.files(), [])

    def test_no_open_license_writes_nothing(self):
        self.licensed = False
        code, out, _ = self.get("Inter", self.dir, "--subsets", "latin")
        self.assertEqual(code, 1)
        self.assertIn("no open license", out)
        self.assertEqual(self.files(), [])

    def test_unknown_family(self):
        code, out, _ = self.get("Missing Font", self.dir)
        self.assertEqual(code, 1)
        self.assertIn("has no family", out)

    def test_css_url(self):
        self.assertEqual(ff.css_url("Source Serif", [400, 700], True),
                         ff.CSS_API + "?family=Source+Serif:ital,wght@0,400;0,700;1,400;1,700"
                         "&display=swap")

    def test_usage(self):
        for args in ([], ["Inter"], ["Inter", self.dir, "--weights", "bold"],
                     ["Inter!", self.dir], ["Inter", os.path.join(self.dir, "absent")]):
            self.assertEqual(self.get(*args)[0], 2, args)


if __name__ == "__main__":
    unittest.main()
