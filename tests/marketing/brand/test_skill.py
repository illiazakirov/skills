"""brand is one skill: a router in SKILL.md, the steps in steps/, every path relative to
the skill's own folder, and nothing that only one harness provides (.agents/agnostic.md)."""

import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
STEPS = ("intake", "strategy", "brand-platform", "identity", "design-system", "brand-book", "status")


def read(*parts):
    with open(os.path.join(SKILL, *parts), encoding="utf-8") as handle:
        return handle.read()


def texts():
    """(path, text) of every Markdown file of the skill."""
    for path in sorted(glob.glob(os.path.join(SKILL, "**", "*.md"), recursive=True)):
        with open(path, encoding="utf-8") as handle:
            yield os.path.relpath(path, SKILL), handle.read()


class Router(unittest.TestCase):
    def test_frontmatter_is_name_and_description_only(self):
        text = read("SKILL.md")
        self.assertTrue(text.startswith("---\n"))
        head = text.split("\n---", 1)[0]
        keys = re.findall(r"(?m)^([a-z-]+):", head)
        self.assertEqual(sorted(keys), ["description", "name"])
        self.assertRegex(head, r"(?m)^name: brand$")

    def test_router_names_every_step(self):
        text = read("SKILL.md")
        for step in STEPS:
            self.assertIn("`steps/%s.md`" % step, text, step)
        self.assertIn("name the valid steps", text)

    def test_no_step_named_runs_status_even_without_a_pipeline(self):
        text = read("SKILL.md")
        rule = [l for l in text.splitlines() if l.startswith("- No step named")][0]
        self.assertIn("run `status`", rule)
        self.assertNotIn("intake", rule)

    def test_an_unknown_argument_is_ruled_before_the_default(self):
        """A typo such as `brand identiy` names no valid step; it must not fall to status."""
        text = read("SKILL.md")
        self.assertLess(text.index("name the valid steps"), text.index("- No step named"))

    def test_step_files_have_no_frontmatter(self):
        for step in STEPS:
            self.assertFalse(read("steps", step + ".md").startswith("---"), step)


class Paths(unittest.TestCase):
    def test_every_script_a_step_names_exists(self):
        for where, text in texts():
            for name in set(re.findall(r"scripts/([a-z_]+\.py)", text)):
                self.assertTrue(os.path.isfile(os.path.join(SKILL, "scripts", name)),
                                "%s names scripts/%s" % (where, name))

    def test_command_examples_quote_the_skill_root(self):
        for where, text in texts():
            for line in text.splitlines():
                for match in re.finditer(r"\$GW/", line):
                    before = line[:match.start()]
                    self.assertTrue(before.endswith('"'), "%s: %s" % (where, line.strip()))


class Status(unittest.TestCase):
    OFFER = "Continue with %s (`brand %s`)? Answer \"yes\" to start it now."

    def test_status_ends_with_one_offer_to_continue(self):
        text = read("steps", "status.md")
        self.assertIn(self.OFFER % ("<the next step>", "<step>"), text)
        self.assertIn(self.OFFER % ("the kickoff", "intake"), text)

    def test_yes_starts_the_next_step_in_this_session(self):
        text = read("steps", "status.md")
        self.assertIn("read `steps/<step>.md` and follow it now, in this session, with the same brand directory", text)
        self.assertNotIn("never run a step.", text)

    def test_headless_status_asks_nothing(self):
        text = read("steps", "status.md")
        self.assertIn("With `--headless`, ask nothing", text)


class FalKey(unittest.TestCase):
    SENTENCE = "Put your fal key into `<brand>/.env` (the file explains how) and tell me when it is saved."

    def test_the_owner_is_never_given_a_command_with_the_skill_root(self):
        """The owner's terminal has no GW and no idea where the skill is installed."""
        env = read("templates", "fal.env")
        self.assertNotIn("<skill root>", env)
        self.assertNotIn("$GW", env)
        self.assertIn("ask your agent to check the key", env.lower())
        for where in (("steps", "brand-platform.md"), ("reference", "step-protocol.md")):
            text = read(*where)
            self.assertIn(self.SENTENCE, text, where)
            self.assertIn("--check-key", text, where)


class Fixtures(unittest.TestCase):
    def test_fixtures_are_never_converted_by_git(self):
        """Their recorded hashes break if a checkout turns LF into CRLF."""
        import subprocess
        path = "tests/marketing/brand/fixtures/valid/brand/pipeline.yaml"
        done = subprocess.run(["git", "check-attr", "text", "--", path], cwd=ROOT,
                              capture_output=True, text=True)
        self.assertEqual(done.stdout.strip(), "%s: text: unset" % path)


class Critic(unittest.TestCase):
    def test_critic_is_launched_as_a_fresh_subagent(self):
        for step in ("identity", "design-system"):
            text = read("steps", step + ".md")
            self.assertIn("start a subagent with a fresh context window", text.lower()
                          .replace("start one subagent per variant, each with a fresh context window",
                                   "start a subagent with a fresh context window"), step)
            self.assertIn("critic.md", text, step)
            self.assertNotIn("brand:critic", text, step)


if __name__ == "__main__":
    unittest.main()
