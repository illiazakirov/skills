"""Tests for scripts/export_kit.py, run on a copy of the valid fixture."""

import hashlib
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
FIXTURE = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, "scripts", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ek = load("export_kit")


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = ek.main(list(args))
    return code, out.getvalue(), err.getvalue()


class ExportKit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.brand = os.path.join(self.tmp, "brand")
        shutil.copytree(FIXTURE, self.brand)
        self.out = os.path.join(self.brand, "out")

    def read(self, *parts):
        with open(os.path.join(self.out, *parts), encoding="utf-8") as handle:
            return handle.read()

    def edit(self, relative, old, new):
        path = os.path.join(self.brand, relative)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new, 1))

    def test_builds_the_fixed_layout(self):
        code, out, err = run(self.brand)
        self.assertEqual(code, 0, err)
        for path in ("AGENTS.md", "README.md", "brand.md", "brand.json", "manifest.json",
                     "book/index.html", "logo/full.svg", "logo/mark.svg", "logo/mono.svg",
                     "logo/dark.svg", "fonts/fonts.css", "tokens/tokens.json",
                     "tokens/tokens.css", "system/components.md", "system/system.css",
                     "system/index.html", "system/sheet.html", "system/pages/landing.html",
                     "surfaces/site-hero.html"):
            self.assertTrue(os.path.isfile(os.path.join(self.out, *path.split("/"))), path)
        self.assertIn("no PDF", out)

    def test_carries_nothing_of_the_working_state(self):
        run(self.brand)
        names = [os.path.relpath(os.path.join(folder, name), self.out)
                 for folder, _dirs, files in os.walk(self.out) for name in files]
        for name in names:
            self.assertNotIn("review", name)
            self.assertNotIn("summary.md", name)
            self.assertNotIn("pipeline.yaml", name)
        text = self.read("brand.md")
        self.assertNotIn("Rationale", text)
        self.assertNotIn("File: `", text)
        self.assertNotIn("01-strategy/", text)
        self.assertNotIn("\nstep: ", text)

    def test_every_relative_link_resolves_inside_the_kit(self):
        run(self.brand)
        link = re.compile(r"""(?:href|src)=["']([^"']+)["']|url\(["']?([^"')]+)""")
        for folder, _dirs, files in os.walk(self.out):
            for name in files:
                if not name.endswith((".html", ".css")) or folder == os.path.join(self.out, "book"):
                    continue
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    text = handle.read()
                for match in link.finditer(text):
                    url = (match.group(1) or match.group(2)).split("#")[0].split("?")[0]
                    if not url or re.match(r"^[a-z]+:|^/", url):
                        continue
                    target = os.path.normpath(os.path.join(folder, url))
                    self.assertTrue(target.startswith(self.out + os.sep), (name, url))
                    self.assertTrue(os.path.isfile(target), (name, url))

    def test_brand_json_holds_every_slot(self):
        run(self.brand)
        data = json.loads(self.read("brand.json"))
        self.assertEqual(data["format"], ek.FORMAT)
        self.assertIn("golden-circle", data["plates"]["01-strategy"])
        self.assertIsInstance(data["plates"]["01-strategy"]["golden-circle"]["slots"]["How"], list)
        self.assertIn("brief", data["plates"]["00-intake"])
        self.assertEqual(data["motto"], data["plates"]["03-identity"]["motto"]["slots"]["Motto"])

    def test_manifest_lists_every_file_with_its_hash(self):
        run(self.brand)
        manifest = json.loads(self.read("manifest.json"))
        self.assertEqual(manifest["format"], ek.FORMAT)
        self.assertEqual(set(manifest["built_from"]), set(ek.cc.STEPS))
        on_disk = {os.path.relpath(os.path.join(folder, name), self.out).replace(os.sep, "/")
                   for folder, _dirs, files in os.walk(self.out) for name in files}
        self.assertEqual(set(manifest["files"]) | {"manifest.json"}, on_disk)
        for path, entry in manifest["files"].items():
            with open(os.path.join(self.out, *path.split("/")), "rb") as handle:
                self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), entry["sha256"])

    def test_agents_md_names_the_brand_and_the_language(self):
        run(self.brand)
        text = self.read("AGENTS.md")
        manifest = json.loads(self.read("manifest.json"))
        self.assertIn(manifest["name"], text.splitlines()[0])
        self.assertIn("`brand.md`, from the start.", text)
        self.assertNotIn("{", text)

    def test_the_same_pipeline_gives_the_same_kit(self):
        run(self.brand)
        first = self.read("manifest.json")
        run(self.brand)
        self.assertEqual(first, self.read("manifest.json"))

    def test_refuses_an_unfinished_pipeline(self):
        self.edit("pipeline.yaml", "  05-brand-book:\n    status: approved",
                  "  05-brand-book:\n    status: stale")
        code, _out, err = run(self.brand)
        self.assertEqual(code, 1)
        self.assertIn("05-brand-book is stale", err)
        self.assertFalse(os.path.exists(self.out))

    def test_refuses_a_step_changed_since_approval(self):
        self.edit("03-identity/logo/mark.svg", "<svg", "<svg data-x=\"1\"")
        code, _out, err = run(self.brand)
        self.assertEqual(code, 1)
        self.assertIn("not clean", err)
        self.assertFalse(os.path.exists(self.out))

    def test_refuses_a_link_outside_the_kit(self):
        # A surface that points at the moodboard is not self-contained in the kit.
        self.edit("03-identity/surfaces/site-hero.html", "</body>",
                  '<img src="../../02-brand-platform/moodboard/reference-01.png"></body>')
        for step in ("03-identity", "04-design-system", "05-brand-book"):
            version = ek.cc.step_version(os.path.join(self.brand, step))
            self._set_version(step, version)
        code, _out, err = run(self.brand)
        self.assertEqual(code, 1, err)
        self.assertIn("outside the kit", err)
        self.assertIn("reference-01.png", err)
        self.assertFalse(os.path.exists(self.out))

    def _set_version(self, step, version):
        path = os.path.join(self.brand, "pipeline.yaml")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        old = re.search(r"  %s:\n    status: approved\n    version: ([0-9a-f]{12})" % step,
                        text).group(1)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, version))

    def test_never_removes_a_directory_that_is_not_a_kit(self):
        os.makedirs(self.out)
        with open(os.path.join(self.out, "notes.txt"), "w") as handle:
            handle.write("mine")
        code, _out, err = run(self.brand)
        self.assertEqual(code, 1)
        self.assertIn("is not a kit", err)
        self.assertTrue(os.path.isfile(os.path.join(self.out, "notes.txt")))

    def test_replaces_an_earlier_kit(self):
        run(self.brand)
        with open(os.path.join(self.out, "stray.txt"), "w") as handle:
            handle.write("x")
        code, _out, err = run(self.brand)
        self.assertEqual(code, 0, err)
        self.assertFalse(os.path.exists(os.path.join(self.out, "stray.txt")))
        self.assertEqual([n for n in os.listdir(self.brand) if n.startswith(".out")], [])

    def test_check_says_current_then_stale(self):
        code, out, _err = run(self.brand, "--check")
        self.assertEqual(code, 1)
        self.assertIn("does not exist", out)
        run(self.brand)
        code, out, _err = run(self.brand, "--check")
        self.assertEqual(code, 0, out)
        self.assertIn("current", out)
        with open(os.path.join(self.out, "brand.md"), "a", encoding="utf-8") as handle:
            handle.write("edited\n")
        self.edit("pipeline.yaml", "  05-brand-book:\n    status: approved\n    version: ",
                  "  05-brand-book:\n    status: approved\n    version: 0")
        code, out, _err = run(self.brand, "--check")
        self.assertEqual(code, 1)
        self.assertIn("brand.md was changed by hand", out)
        self.assertIn("05-brand-book is now", out)

    def test_the_kit_does_not_change_any_step_version(self):
        before = {step: ek.cc.step_version(os.path.join(self.brand, step)) for step in ek.cc.STEPS}
        run(self.brand)
        after = {step: ek.cc.step_version(os.path.join(self.brand, step)) for step in ek.cc.STEPS}
        self.assertEqual(before, after)
        report = ek.cc.check(self.brand)
        self.assertEqual(report.errors, [])


class KitTexts(ExportKit):
    """The kit says nothing of where the working directory is (contract, section 8)."""

    def kit_texts(self):
        for folder, _dirs, files in os.walk(self.out):
            for name in files:
                if name.endswith((".md", ".json", ".html", ".css", ".svg")):
                    with open(os.path.join(folder, name), encoding="utf-8") as handle:
                        yield os.path.relpath(os.path.join(folder, name), self.out), handle.read()

    def test_no_path_of_the_brand_directory_and_no_absolute_path(self):
        run(self.brand)
        for name, text in self.kit_texts():
            self.assertNotIn("brand/", text, name)
            self.assertNotIn(self.tmp, text, name)
            self.assertNotIn(os.path.realpath(self.tmp), text, name)
            self.assertNotIn(os.path.expanduser("~"), text, name)
            for step in ek.cc.STEPS:
                self.assertNotIn(step + "/", text, name)

    def test_the_change_sentence_without_an_order(self):
        run(self.brand)
        for name in ("AGENTS.md", "README.md"):
            text = self.read(name)
            self.assertIn("the brand working directory it was built from", text, name)
            self.assertNotIn("project's", text, name)
        self.assertIn("working directory it was built from", self.read("brand.md"))
        self.assertNotIn("order", json.loads(self.read("manifest.json")))

    def test_an_order_is_named_in_the_texts_and_the_manifest(self):
        self.edit("pipeline.yaml", "profile:", "order: acme-shop\nprofile:")
        code, _out, err = run(self.brand)
        self.assertEqual(code, 0, err)
        manifest = json.loads(self.read("manifest.json"))
        self.assertEqual(manifest["order"], "acme-shop")
        self.assertEqual(manifest["format"], "brand-kit/2")
        for name in ("AGENTS.md", "README.md", "brand.md"):
            self.assertIn("order `acme-shop`", self.read(name), name)

    def test_a_kit_of_format_1_is_out_of_date_and_replaced(self):
        run(self.brand)
        path = os.path.join(self.out, "manifest.json")
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["format"] = "brand-kit/1"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        code, out, _err = run(self.brand, "--check")
        self.assertEqual(code, 1)
        self.assertIn("the kit is brand-kit/1", out)
        code, _out, err = run(self.brand)
        self.assertEqual(code, 0, err)
        self.assertEqual(run(self.brand, "--check")[0], 0)


class Delivery(ExportKit):
    def setUp(self):
        ExportKit.setUp(self)
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.project)
        self.target = os.path.join(self.project, "docs", "brand")

    def check(self):
        return run(self.brand, "--check", "--deliver", self.target)

    def test_delivers_an_exact_copy_and_the_check_says_current(self):
        run(self.brand)
        code, out, err = run(self.brand, "--deliver", self.target)
        self.assertEqual(code, 0, err)
        self.assertIn("delivered", out)
        mine = sorted(ek.visible_files(self.out))
        theirs = sorted(ek.visible_files(self.target))
        self.assertEqual([os.path.relpath(p, self.out) for p in mine],
                         [os.path.relpath(p, self.target) for p in theirs])
        for a, b in zip(mine, theirs):
            with open(a, "rb") as one, open(b, "rb") as two:
                self.assertEqual(one.read(), two.read(), a)
        code, out, _err = self.check()
        self.assertEqual(code, 0, out)
        self.assertIn("the delivered kit is current", out)
        self.assertEqual(sorted(os.listdir(os.path.join(self.project, "docs"))), ["brand"])

    def test_the_delivery_carries_nothing_of_the_working_state(self):
        with open(os.path.join(self.brand, ".env"), "w") as handle:
            handle.write("FAL_KEY=secret-key-123\n")
        os.makedirs(os.path.join(self.brand, "owner", "answers"))
        run(self.brand)
        run(self.brand, "--deliver", self.target)
        names = os.listdir(self.target)
        for name in (".env", "pipeline.yaml", "owner", "map.html") + tuple(ek.cc.STEPS):
            self.assertNotIn(name, names)
        for folder, _dirs, files in os.walk(self.target):
            for name in files:
                with open(os.path.join(folder, name), "rb") as handle:
                    self.assertNotIn(b"secret-key-123", handle.read(), name)

    def test_refuses_a_kit_that_is_not_current(self):
        code, _out, err = run(self.brand, "--deliver", self.target)
        self.assertEqual(code, 1)
        self.assertIn("export it first", err)
        self.assertFalse(os.path.exists(self.target))

    def test_never_exports(self):
        run(self.brand)
        self.edit("pipeline.yaml", "  05-brand-book:\n    status: approved\n    version: ",
                  "  05-brand-book:\n    status: approved\n    version: 0")
        code, _out, err = run(self.brand, "--deliver", self.target)
        self.assertEqual(code, 1)
        self.assertIn("05-brand-book is now", err)

    def test_never_replaces_a_directory_that_is_not_a_kit(self):
        run(self.brand)
        os.makedirs(self.target)
        with open(os.path.join(self.target, "notes.md"), "w") as handle:
            handle.write("mine")
        code, _out, err = run(self.brand, "--deliver", self.target)
        self.assertEqual(code, 1)
        self.assertIn("is not a kit", err)
        self.assertTrue(os.path.isfile(os.path.join(self.target, "notes.md")))

    def test_refuses_a_target_inside_the_brand_directory(self):
        run(self.brand)
        code, _out, err = run(self.brand, "--deliver", os.path.join(self.brand, "kit"))
        self.assertEqual(code, 1)
        self.assertIn("inside the brand directory", err)

    def test_replaces_an_earlier_delivery(self):
        run(self.brand)
        run(self.brand, "--deliver", self.target)
        with open(os.path.join(self.target, "stray.txt"), "w") as handle:
            handle.write("x")
        code, _out, err = run(self.brand, "--deliver", self.target)
        self.assertEqual(code, 0, err)
        self.assertFalse(os.path.exists(os.path.join(self.target, "stray.txt")))
        self.assertEqual([n for n in os.listdir(os.path.join(self.project, "docs"))
                          if n.startswith(".")], [])

    def test_check_finds_a_changed_a_missing_and_an_added_file(self):
        run(self.brand)
        run(self.brand, "--deliver", self.target)
        with open(os.path.join(self.target, "brand.md"), "a", encoding="utf-8") as handle:
            handle.write("edited\n")
        os.remove(os.path.join(self.target, "logo", "mark.svg"))
        with open(os.path.join(self.target, "extra.css"), "w") as handle:
            handle.write("x")
        with open(os.path.join(self.target, ".DS_Store"), "w") as handle:
            handle.write("x")
        code, out, _err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("brand.md was changed by hand", out)
        self.assertIn("logo/mark.svg is missing", out)
        self.assertIn("extra.css is not part of the kit", out)
        self.assertNotIn(".DS_Store", out)

    def test_check_finds_a_kit_that_is_no_longer_current(self):
        run(self.brand)
        run(self.brand, "--deliver", self.target)
        self.edit("pipeline.yaml", "profile:", "order: acme-shop\nprofile:")
        run(self.brand)
        code, out, _err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("holds another kit", out)
        run(self.brand, "--deliver", self.target)
        self.assertEqual(self.check()[0], 0)

    def test_check_without_a_delivery(self):
        run(self.brand)
        code, out, _err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("does not exist or is not a kit", out)

    def test_works_from_a_studio_order(self):
        order = os.path.join(self.tmp, "studio", "orders", "acme")
        shutil.move(self.brand, order)
        self.brand, self.out = order, os.path.join(order, "out")
        self.assertEqual(run(order)[0], 0)
        self.assertEqual(run(order, "--deliver", self.target)[0], 0)
        self.assertEqual(self.check()[0], 0)


if __name__ == "__main__":
    unittest.main()
