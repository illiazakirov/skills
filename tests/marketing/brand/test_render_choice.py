"""Tests for scripts/render_choice.py.

examples/choice-page holds a valid data file with its variants and reference.
Each test copies it to a temporary directory and changes the data.

Run from the repository root:

    python3 -m unittest discover -s tests
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
SCRIPT = os.path.join(SKILL, "scripts", "render_choice.py")
EXAMPLE = os.path.join(SKILL, "examples", "choice-page")

_spec = importlib.util.spec_from_file_location("render_choice", SCRIPT)
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)


class ChoiceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.dir = os.path.join(self.tmp, "review")
        shutil.copytree(EXAMPLE, self.dir)
        os.remove(os.path.join(self.dir, "layout-01.html"))
        self.data_path = os.path.join(self.dir, "layout-01.json")
        with open(self.data_path, encoding="utf-8") as handle:
            self.data = json.load(handle)
        with open(rc.TEMPLATE, encoding="utf-8") as handle:
            self.template = handle.read()

    def render(self):
        return rc.render(self.data, self.dir, self.template)

    def assertProblem(self, fragment):
        with self.assertRaises(rc.DataError) as caught:
            self.render()
        if not any(fragment in problem for problem in caught.exception.problems):
            self.fail("no problem containing %r in:\n%s"
                      % (fragment, "\n".join(caught.exception.problems)))


class Rendering(ChoiceCase):
    def test_every_slot_is_filled(self):
        page = self.render()
        self.assertNotIn("{{", page)
        self.assertNotIn("<!--gw:", page)

    def test_variants_are_numbered_in_order(self):
        page = self.render()
        for number in (1, 2, 3):
            self.assertIn('id="variant-%d"' % number, page)
            self.assertIn('<div class="number">%d</div>' % number, page)
        self.assertNotIn('id="variant-4"', page)
        self.assertLess(page.index('id="variant-1"'), page.index('id="variant-2"'))

    def test_each_variant_has_reference_and_critic(self):
        page = self.render()
        self.assertEqual(page.count('<div class="frame reference"'), 3)
        self.assertEqual(page.count('src="refs/aihero-home.png"'), 3)
        self.assertEqual(page.count("<h3>Критик</h3>"), 3)
        self.assertIn("<li>Сітка рівна", page)

    def test_empty_critic_list_says_so(self):
        self.assertIn('<p class="quiet">Зауважень немає.</p>', self.render())

    def test_theme_switch_is_present(self):
        page = self.render()
        self.assertIn('data-theme-value="light"', page)
        self.assertIn('data-theme-value="dark"', page)
        self.assertIn("brandTheme", page)

    def test_live_variant_is_an_iframe_and_an_image_variant_is_an_img(self):
        with open(os.path.join(self.dir, "layout-01", "mark.svg"), "w") as handle:
            handle.write('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.data["variants"][2]["file"] = "layout-01/mark.svg"
        page = self.render()
        self.assertEqual(page.count("<iframe "), 2)
        self.assertIn('<img class="image" src="layout-01/mark.svg"', page)

    def test_labels_default_to_english(self):
        del self.data["labels"]
        page = self.render()
        self.assertIn("Variant 2", page)
        self.assertIn(">Reference<", page)
        self.assertIn("<h3>Critic</h3>", page)

    def test_viewport_switch_only_with_several_viewports(self):
        self.assertIn('data-viewport-width="390"', self.render())
        del self.data["viewports"]
        page = self.render()
        self.assertNotIn("data-viewport-width=", page)
        self.assertIn("width: 1440, height: 900", page)

    def test_text_is_escaped(self):
        self.data["title"] = "<script>alert(1)</script>"
        self.data["variants"][0]["critic"] = ["a < b & c"]
        page = self.render()
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("<li>a &lt; b &amp; c</li>", page)

    def test_same_data_renders_the_same_page(self):
        self.assertEqual(self.render(), self.render())


class BrokenData(ChoiceCase):
    def test_two_variants(self):
        del self.data["variants"][2]
        self.assertProblem("three or four variants; found 2")

    def test_five_variants(self):
        self.data["variants"] += self.data["variants"][:2]
        self.assertProblem("three or four variants; found 5")

    def test_variant_without_reference(self):
        del self.data["variants"][1]["reference"]
        self.assertProblem("variant 2: 'reference' is missing")

    def test_reference_screenshot_does_not_exist(self):
        self.data["variants"][0]["reference"]["image"] = "refs/missing.png"
        self.assertProblem("variant 1: reference 'image' does not exist")

    def test_reference_must_be_a_screenshot_file(self):
        self.data["variants"][0]["reference"]["image"] = "https://www.aihero.dev/"
        self.assertProblem("variant 1: reference 'image' must be a path relative")

    def test_reference_without_caption(self):
        del self.data["variants"][0]["reference"]["caption"]
        self.assertProblem("variant 1: reference: 'caption' is missing")

    def test_variant_file_does_not_exist(self):
        self.data["variants"][2]["file"] = "layout-01/variant-9.html"
        self.assertProblem("variant 3: 'file' does not exist")

    def test_variant_without_theme_listener(self):
        with open(os.path.join(self.dir, "layout-01", "variant-1.html"), "w") as handle:
            handle.write("<!doctype html><html><body>plain</body></html>")
        self.assertProblem("variant 1: 'file' does not listen for the theme")

    def test_variant_without_critic(self):
        del self.data["variants"][0]["critic"]
        self.assertProblem("variant 1: 'critic' must be a list")

    def test_variant_without_title(self):
        del self.data["variants"][0]["title"]
        self.assertProblem("variant 1: 'title' is missing")

    def test_missing_title_and_lang(self):
        del self.data["title"]
        del self.data["lang"]
        self.assertProblem("'title' is missing")
        self.assertProblem("'lang' is missing")

    def test_unknown_key(self):
        self.data["winner"] = 2
        self.assertProblem("unknown key 'winner'")

    def test_unknown_label(self):
        self.data["labels"]["verdict"] = "x"
        self.assertProblem("labels: unknown key 'verdict'")

    def test_bad_viewport(self):
        self.data["viewports"] = [{"width": "wide", "height": 900}]
        self.assertProblem("viewport 1 must be")

    def test_bad_source(self):
        self.data["variants"][0]["reference"]["source"] = "javascript:alert(1)"
        self.assertProblem("reference 'source' must be an http(s) URL")


class CommandLine(ChoiceCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, SCRIPT] + list(args), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)

    def test_writes_html_beside_the_data_file(self):
        result = self.run_script(self.data_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "layout-01.html")))

    def test_committed_example_is_up_to_date(self):
        with open(os.path.join(EXAMPLE, "layout-01.html"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), self.render())

    def test_broken_data_exits_one_and_writes_nothing(self):
        del self.data["variants"][2]
        with open(self.data_path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle)
        result = self.run_script(self.data_path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("three or four variants", result.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "layout-01.html")))

    def test_unreadable_data_exits_two(self):
        self.assertEqual(self.run_script(os.path.join(self.dir, "nothing.json")).returncode, 2)
        with open(self.data_path, "w") as handle:
            handle.write("{ not json")
        self.assertEqual(self.run_script(self.data_path).returncode, 2)


if __name__ == "__main__":
    unittest.main()
