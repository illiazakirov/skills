"""Tests for scripts/render_moodboard.py, scripts/check_domains.py and scripts/fal_generate.py.

Nothing here touches the network: the two scripts that use it take a fetch function.
"""

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
VALID = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, "scripts", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rm = load("render_moodboard")
cd = load("check_domains")
fg = load("fal_generate")
cc = load("check_contract")


def run(function, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = function(*args, **kwargs)
    return code, out.getvalue(), err.getvalue()


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def write(self, relative, content="x"):
        path = os.path.join(self.tmp, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(path, mode) as handle:
            handle.write(content)
        return path

    def read(self, relative):
        with open(os.path.join(self.tmp, relative), encoding="utf-8") as handle:
            return handle.read()


INDEX = """# Moodboard

Calm, dense, typographic.

## 1. aihero home

- File: ../refs/aihero-home.png
- Source: https://www.aihero.dev/
- Takes: the density of the first screen

## 2. Paper texture

- File: paper-1.png
- Source: generated
- Takes: the warm grain <of> the background
"""


class Moodboard(Temp):
    def setUp(self):
        Temp.setUp(self)
        self.write("refs/aihero-home.png")
        self.write("moodboard/paper-1.png")
        self.index = self.write("moodboard/index.md", INDEX)

    def render(self, text=None):
        if text is not None:
            self.write("moodboard/index.md", text)
        return run(rm.main, [self.index])

    def assertProblem(self, text, fragment):
        code, out, _ = self.render(text)
        self.assertEqual(code, 1, out)
        self.assertIn(fragment, out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "moodboard", "board.html")))

    def test_given_material_is_a_source_of_its_own(self):
        self.write("given/logo.png")
        text = INDEX + "\n## 3. The logo\n\n- File: ../given/logo.png\n- Source: given\n" \
                       "- Takes: the heavy round mark\n"
        code, out, _ = self.render(text)
        self.assertEqual(code, 0, out)
        page = self.read("moodboard/board.html")
        self.assertIn('src="../given/logo.png"', page)
        self.assertIn(">given<", page)

    def test_unknown_source_word_is_refused(self):
        self.assertProblem(INDEX.replace("Source: generated", "Source: provided"),
                           "'Source' must be an http(s) URL, the word 'generated' or the word "
                           "'given'")

    def test_index_renders_to_board_html(self):
        code, out, _ = self.render()
        self.assertEqual(code, 0, out)
        page = self.read("moodboard/board.html")
        self.assertIn('src="../refs/aihero-home.png"', page)
        self.assertIn("the warm grain &lt;of&gt; the background", page)
        self.assertIn('href="https://www.aihero.dev/"', page)
        self.assertIn("Calm, dense, typographic.", page)
        self.assertIn("brandTheme", page)
        self.assertNotIn("{{", page)

    def test_other_name_renders_beside_itself_and_may_leave_images_unlisted(self):
        self.write("moodboard/extra.png")
        variant = self.write("moodboard/variant-1.md", INDEX)
        code, out, _ = run(rm.main, [variant, "--lang", "uk"])
        self.assertEqual(code, 0, out)
        self.assertIn('<html lang="uk">', self.read("moodboard/variant-1.html"))

    def test_unlisted_image_in_the_moodboard(self):
        self.write("moodboard/stray.png")
        self.assertProblem(None, "stray.png is in the moodboard directory but not in the index")

    def test_missing_file(self):
        self.assertProblem(INDEX.replace("paper-1.png", "paper-9.png"), "does not exist")

    def test_empty_takes(self):
        self.assertProblem(INDEX.replace("Takes: the density of the first screen", "Takes:"),
                           "'Takes' is empty")

    def test_bad_source(self):
        self.assertProblem(INDEX.replace("Source: generated", "Source: made up"),
                           "'Source' must be")

    def test_numbering_gap(self):
        self.assertProblem(INDEX.replace("## 2.", "## 3."), "numbered from 1 without gaps")

    def test_missing_field(self):
        self.assertProblem(INDEX.replace("- Source: generated\n", ""), "exactly the lines")

    def test_no_images(self):
        self.assertProblem("# Moodboard\n", "lists no images")

    def test_usage(self):
        self.assertEqual(run(rm.main, [])[0], 2)
        self.assertEqual(run(rm.main, ["board.html"])[0], 2)
        self.assertEqual(run(rm.main, [os.path.join(self.tmp, "absent.md")])[0], 2)


BOOTSTRAP = json.dumps({"services": [
    [["com", "net"], ["https://rdap.example/com/v1/"]],
    [["dev"], ["http://insecure.example/", "https://rdap.example/dev"]],
]}).encode()


def registry(answers, bootstrap=(200, BOOTSTRAP)):
    def fetch(url):
        if url == cd.BOOTSTRAP:
            return bootstrap
        return answers.get(url, (0, b"")), b""
    def unwrap(url):
        result = fetch(url)
        return result if url == cd.BOOTSTRAP else (result[0][0] if isinstance(result[0], tuple)
                                                   else result[0], b"")
    return unwrap


class Domains(unittest.TestCase):
    def check(self, domains, answers, **kwargs):
        code, out, _ = run(cd.main, domains, fetch=registry(answers, **kwargs))
        self.assertEqual(code, 0)
        return out.splitlines()

    def test_states(self):
        lines = self.check(["Taken.com", "free.dev", "down.net", "odd.com", "name.ua"], {
            "https://rdap.example/com/v1/domain/taken.com": (200, b""),
            "https://rdap.example/dev/domain/free.dev": (404, b""),
            "https://rdap.example/com/v1/domain/odd.com": (429, b""),
        })
        self.assertTrue(lines[0].startswith("registered ") and lines[0].endswith("taken.com"))
        self.assertTrue(lines[1].startswith("not registered ") and lines[1].endswith("free.dev"))
        self.assertIn("unknown", lines[2])
        self.assertIn("did not answer", lines[2])
        self.assertIn("answered 429", lines[3])
        self.assertIn("the .ua zone has no RDAP service", lines[4])

    def test_bootstrap_unavailable_is_unknown_not_free(self):
        lines = self.check(["free.dev"], {}, bootstrap=(0, b""))
        self.assertTrue(lines[0].startswith("unknown"))

    def test_usage(self):
        for args in ([], ["not a domain"], ["https://example.com"], ["nodot"]):
            self.assertEqual(run(cd.main, args, fetch=registry({}))[0], 2, args)


class Fal(Temp):
    def setUp(self):
        Temp.setUp(self)
        self.brand = os.path.join(self.tmp, "brand")
        shutil.copytree(VALID, self.brand)
        self.pipeline = os.path.join(self.brand, "pipeline.yaml")
        self.edit(lambda text: text.replace("image_generation: svg-only", "image_generation: fal")
                  .replace("image_generation: none", "image_generation: fal"))
        self.set_limit("3.5")
        self.write("brand/.env", "FAL_KEY=secret-key-123\n")
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("FAL_KEY", None)
        self.out = os.path.join(self.tmp, "out")
        os.mkdir(self.out)
        self.calls = []

    def edit(self, change):
        with open(self.pipeline, encoding="utf-8") as handle:
            text = handle.read()
        with open(self.pipeline, "w", encoding="utf-8") as handle:
            handle.write(change(text))

    def set_limit(self, value):
        import re
        self.edit(lambda text: re.sub(r"(?m)^  limit: .*$", "  limit: " + value, text))

    def state(self):
        return cc.parse_yaml(cc.read_lines(self.pipeline))

    def fetch(self, url, key=None, body=None):
        self.calls.append((url, key, body))
        if body is not None:
            return json.dumps({"images": [{"url": "https://fal.media/files/a.png"}]}).encode()
        return b"PNGDATA"

    def generate(self, *extra, **kwargs):
        args = [self.brand, "02-brand-platform", self.out, "paper", "--prompt", "warm paper"]
        return run(fg.main, args + list(extra), fetch=kwargs.get("fetch", self.fetch))

    def test_setup_uses_fal(self):
        self.assertEqual(self.state()["tools"]["image_generation"], "fal")

    def test_generates_records_spend_and_keeps_the_pipeline_valid(self):
        before = float(self.state()["steps"]["02-brand-platform"]["spent"])
        code, out, _ = self.generate("--count", "2")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(os.listdir(self.out)), ["paper-1.png", "paper-2.png"])
        after = float(self.state()["steps"]["02-brand-platform"]["spent"])
        self.assertAlmostEqual(after - before, 0.06)
        url, key, body = self.calls[0]
        self.assertEqual(url, "https://fal.run/fal-ai/flux-2-pro")
        self.assertEqual(key, "secret-key-123")
        self.assertEqual(body["prompt"], "warm paper")
        self.assertNotIn("secret-key-123", out)
        report = cc.check(self.brand)
        self.assertEqual([e for e in report.errors if "pipeline" in e[0]], [])

    def test_numbering_continues(self):
        self.generate()
        self.generate()
        self.assertEqual(sorted(os.listdir(self.out)), ["paper-1.png", "paper-2.png"])

    def test_estimate_calls_nothing_and_needs_no_key(self):
        os.remove(os.path.join(self.brand, ".env"))
        code, out, _ = self.generate("--count", "4", "--estimate")
        self.assertEqual(code, 0, out)
        self.assertIn("$0.12", out)
        self.assertEqual(self.calls, [])

    def test_over_budget_is_refused(self):
        self.set_limit("2.55")
        code, out, _ = self.generate("--count", "2")
        self.assertEqual(code, 1)
        self.assertIn("more than what is left of the budget", out)
        self.assertEqual(self.calls, [])

    def test_placeholder_key(self):
        self.write("brand/.env", "FAL_KEY=put-fal-key-here\n")
        code, _, err = self.generate()
        self.assertEqual(code, 3)
        self.assertIn(".env", err)
        self.assertEqual(self.calls, [])

    def test_file_beats_environment(self):
        os.environ["FAL_KEY"] = "stale-env-key"
        self.assertEqual(fg.read_key(self.brand),
                         ("secret-key-123", os.path.join(self.brand, ".env")))
        code, out, err = self.generate()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.calls[0][1], "secret-key-123")

    def test_environment_used_when_no_file(self):
        os.remove(os.path.join(self.brand, ".env"))
        os.environ["FAL_KEY"] = "env-key-456"
        self.assertEqual(fg.read_key(self.brand), ("env-key-456", "environment"))
        code, out, err = self.generate()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.calls[0][1], "env-key-456")
        self.assertNotIn("env-key-456", out + err)

    def test_studio_file_beats_brand_file(self):
        studio = os.path.join(self.tmp, "studio")
        order = os.path.join(studio, "orders", "acme")
        shutil.copytree(self.brand, order)
        self.write("studio/.env", "FAL_KEY=studio-key\n")
        self.assertEqual(fg.read_key(order, environ={}),
                         ("studio-key", os.path.join(studio, ".env")))

    def test_comment_lines_are_ignored(self):
        with open(os.path.join(SKILL, "templates", "fal.env"), encoding="utf-8") as handle:
            header = handle.read().replace("FAL_KEY=put-fal-key-here", "FAL_KEY=abc")
        self.write("brand/.env", header)
        self.assertEqual(fg.read_key(self.brand, environ={})[0], "abc")

    def test_old_one_line_env_still_read(self):
        self.write("brand/.env", "FAL_KEY=old-style")
        self.assertEqual(fg.read_key(self.brand, environ={})[0], "old-style")

    def test_placeholder_counts_as_missing(self):
        with open(os.path.join(SKILL, "templates", "fal.env"), encoding="utf-8") as handle:
            self.write("brand/.env", handle.read())
        self.assertEqual(fg.read_key(self.brand, environ={}), (None, None))

    def test_check_key_found(self):
        code, out, err = run(fg.main, [self.brand, "--check-key"], fetch=self.fetch)
        self.assertEqual(code, 0, out + err)
        self.assertIn("fal key: found in %s" % os.path.join(self.brand, ".env"), out)
        self.assertNotIn("secret-key-123", out + err)
        self.assertEqual(self.calls, [])

    def test_check_key_missing(self):
        os.remove(os.path.join(self.brand, ".env"))
        code, out, err = run(fg.main, [self.brand, "--check-key"], fetch=self.fetch)
        self.assertEqual(code, 3)
        self.assertIn("fal key: not set. Put it into %s" % os.path.join(self.brand, ".env"),
                      out + err)

    def test_key_of_the_studio_for_an_order(self):
        studio = os.path.join(self.tmp, "studio")
        order = os.path.join(studio, "orders", "acme")
        shutil.copytree(self.brand, order)
        os.remove(os.path.join(order, ".env"))
        self.write("studio/.env", "FAL_KEY=studio-key-789\n")
        self.brand, self.pipeline = order, os.path.join(order, "pipeline.yaml")
        code, out, err = self.generate()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.calls[0][1], "studio-key-789")
        self.assertNotIn("studio-key-789", out + err)

    def test_the_studio_key_is_read_only_for_an_order(self):
        os.remove(os.path.join(self.brand, ".env"))
        self.write(".env", "FAL_KEY=project-key\n")
        self.assertEqual(fg.read_key(self.brand, environ={}), (None, None))
        code, _, err = self.generate()
        self.assertEqual(code, 3)
        self.assertEqual(self.calls, [])

    def test_generation_must_be_fal(self):
        self.edit(lambda text: text.replace("image_generation: fal", "image_generation: svg-only"))
        code, out, _ = self.generate()
        self.assertEqual(code, 1)
        self.assertIn("paid generation is off", out)

    def test_unknown_model_needs_a_price(self):
        code, out, _ = self.generate("--model", "fal-ai/other")
        self.assertEqual(code, 1)
        self.assertIn("--price", out)
        code, out, _ = self.generate("--model", "fal-ai/other", "--price", "0.1")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.calls[0][0], "https://fal.run/fal-ai/other")

    def test_failure_records_only_what_was_generated(self):
        before = float(self.state()["steps"]["02-brand-platform"]["spent"])

        def failing(url, key=None, body=None):
            if body is not None and len([c for c in self.calls if c[2] is not None]) >= 1:
                raise fg.Refused("fal answered 403")
            return self.fetch(url, key, body)

        code, out, _ = self.generate("--count", "3", fetch=failing)
        self.assertEqual(code, 1)
        self.assertEqual(os.listdir(self.out), ["paper-1.png"])
        after = float(self.state()["steps"]["02-brand-platform"]["spent"])
        self.assertAlmostEqual(after - before, 0.03)

    def test_usage(self):
        for args in ([], [self.brand, "02-brand-platform", self.out, "paper"],
                     [self.brand, "04-nope", self.out, "paper", "--prompt", "x"],
                     [self.brand, "02-brand-platform", self.out, "Bad Name", "--prompt", "x"],
                     [self.brand, "02-brand-platform", self.out, "paper", "--prompt", "x",
                      "--count", "99"],
                     [self.brand, "02-brand-platform", self.out, "paper", "--prompt", "x",
                      "--size", "huge"]):
            self.assertEqual(run(fg.main, args, fetch=self.fetch)[0], 2, args)


if __name__ == "__main__":
    unittest.main()
