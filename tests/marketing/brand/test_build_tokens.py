"""Tests for scripts/build_tokens.py."""

import copy
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
EXAMPLE = os.path.join(SKILL, "examples", "design-tokens")

_spec = importlib.util.spec_from_file_location(
    "build_tokens", os.path.join(SKILL, "scripts", "build_tokens.py"))
bt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bt)

PX = lambda n: {"value": n, "unit": "px"}  # noqa: E731
WHITE = {"colorSpace": "srgb", "components": [1, 1, 1]}


def run(args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = bt.main(args)
    return code, out.getvalue() + err.getvalue()


class Build(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(EXAMPLE, "tokens.json"), encoding="utf-8") as handle:
            self.data = json.load(handle)

    def problems(self, data):
        with self.assertRaises(bt.Problem) as caught:
            bt.build(data)
        return "\n".join(caught.exception.args[0])

    def test_example_css_is_up_to_date(self):
        with open(os.path.join(EXAMPLE, "tokens.css"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), bt.build(self.data))

    def test_values(self):
        css = bt.build(self.data)
        for line in ("--color-accent: #b4451f;", "--color-bg: var(--color-neutral-0);",
                     "--color-scrim: rgb(0 0 0 / 0.5);", "--space-4: 1rem;",
                     '--font-display: "Source Serif 4", "Georgia", serif;',
                     "--font-weight-bold: 700;", "--type-headline-font-size: 3.5rem;",
                     "--type-headline-font-family: var(--font-display);",
                     "--shadow-card: 0px 1px 2px 0px var(--color-scrim);",
                     "--motion-ease: cubic-bezier(0.2, 0, 0, 1);"):
            self.assertIn("  " + line, css)

    def test_dark_theme_overrides_under_the_same_name(self):
        css = bt.build(self.data)
        dark = css.split(':root[data-theme="dark"] {')[1]
        self.assertIn("--color-bg: var(--color-neutral-900);", dark)
        self.assertIn("--color-accent: #e2733f;", dark)
        self.assertNotIn("--dark-", css)

    def test_narrow_overrides_under_a_media_query(self):
        data = copy.deepcopy(self.data)
        data["narrow"] = {"space": {"m": {"$type": "dimension", "$value": PX(12)}}}
        data.setdefault("space", {})["m"] = {"$type": "dimension", "$value": PX(16)}
        css = bt.build(data)
        narrow = css.split("@media (max-width: 600px) {")[1]
        self.assertIn("--space-m: 12px;", narrow)
        self.assertIn("--space-m: 16px;", css.split("@media")[0])
        self.assertNotIn("--narrow-", css)

    def test_narrow_override_needs_a_base_token(self):
        data = copy.deepcopy(self.data)
        data["narrow"] = {"space": {"nowhere": {"$type": "dimension", "$value": PX(12)}}}
        self.assertIn("does not exist outside 'narrow'", self.problems(data))

    def test_no_dark_group_no_dark_block(self):
        del self.data["dark"]
        self.assertNotIn("data-theme", bt.build(self.data))

    def test_color_must_be_an_object(self):
        self.assertIn("a color is an object",
                      self.problems({"c": {"$type": "color", "$value": "#ffffff"}}))

    def test_hex_must_agree_with_components(self):
        value = dict(WHITE, hex="#000000")
        self.assertIn("'hex' is #000000 but the components give #ffffff",
                      self.problems({"c": {"$type": "color", "$value": value}}))

    def test_dimension_must_be_an_object_with_a_known_unit(self):
        self.assertIn("a dimension is an object",
                      self.problems({"s": {"$type": "dimension", "$value": "16px"}}))
        self.assertIn("a dimension is an object",
                      self.problems({"s": {"$type": "dimension", "$value": {"value": 1, "unit": "em"}}}))

    def test_missing_type(self):
        self.assertIn("no '$type'", self.problems({"s": {"$value": 1}}))

    def test_type_is_inherited_from_a_group(self):
        css = bt.build({"z": {"$type": "number", "modal": {"$value": 10}}})
        self.assertIn("--z-modal: 10;", css)

    def test_alias_must_exist_and_match_type(self):
        self.assertIn("does not exist",
                      self.problems({"c": {"$type": "color", "$value": "{c2}"}}))
        data = {"s": {"$type": "dimension", "$value": PX(1)},
                "c": {"$type": "color", "$value": "{s}"}}
        self.assertIn("is a color but refers to {s}, which is a dimension", self.problems(data))

    def test_alias_cycle(self):
        data = {"a": {"$type": "number", "$value": "{b}"}, "b": {"$type": "number", "$value": "{a}"}}
        self.assertIn("refers to itself", self.problems(data))

    def test_alias_into_dark_is_refused(self):
        data = copy.deepcopy(self.data)
        data["color"]["fg"]["$value"] = "{dark.color.bg}"
        self.assertIn("refer to the token without 'dark.'", self.problems(data))

    def test_dark_override_needs_a_light_token_of_the_same_type(self):
        data = {"c": {"$type": "color", "$value": WHITE},
                "dark": {"d": {"$type": "color", "$value": WHITE}}}
        self.assertIn("overrides d, which does not exist outside 'dark'", self.problems(data))
        data = {"c": {"$type": "color", "$value": WHITE},
                "dark": {"c": {"$type": "number", "$value": 1}}}
        self.assertIn("is a number but c is a color", self.problems(data))

    def test_names_must_be_css_safe(self):
        self.assertIn("lowercase letters", self.problems({"Brand Color": {"$type": "number", "$value": 1}}))

    def test_unsupported_type_and_ref(self):
        self.assertIn("is not supported",
                      self.problems({"b": {"$type": "border", "$value": {}}}))
        self.assertIn("'$ref' is not supported",
                      self.problems({"c": {"$type": "number", "$ref": "#/x", "$value": 1}}))

    def test_typography_needs_all_fields(self):
        self.assertIn("exactly fontFamily",
                      self.problems({"t": {"$type": "typography", "$value": {"fontSize": PX(16)}}}))

    def test_empty_file(self):
        self.assertIn("holds no tokens", self.problems({}))


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copy(os.path.join(EXAMPLE, "tokens.json"), self.tmp)
        self.json = os.path.join(self.tmp, "tokens.json")
        self.css = os.path.join(self.tmp, "tokens.css")

    def test_writes_and_checks(self):
        self.assertEqual(run([self.json, "--check"])[0], 1)
        self.assertEqual(run([self.json])[0], 0)
        self.assertEqual(run([self.json, "--check"])[0], 0)
        with open(self.css, "a") as handle:
            handle.write("/* edited */\n")
        code, out = run([self.json, "--check"])
        self.assertEqual(code, 1)
        self.assertIn("out of date", out)

    def test_broken_tokens_write_nothing(self):
        with open(self.json, "w") as handle:
            json.dump({"c": {"$type": "color", "$value": "#fff"}}, handle)
        self.assertEqual(run([self.json])[0], 1)
        self.assertFalse(os.path.exists(self.css))

    def test_unreadable(self):
        with open(self.json, "w") as handle:
            handle.write("{not json")
        self.assertEqual(run([self.json])[0], 2)
        self.assertEqual(run([])[0], 2)
        self.assertEqual(run([os.path.join(self.tmp, "absent.json")])[0], 2)

    def test_fixture_tokens_are_built(self):
        fixture = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand", "04-design-system",
                               "tokens.json")
        self.assertEqual(run([fixture, "--check"])[0], 0)


if __name__ == "__main__":
    unittest.main()
