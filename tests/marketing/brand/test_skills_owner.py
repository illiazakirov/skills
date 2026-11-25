"""The skills ask the owner through owner.py and use valid, fixed ids (contract, section 9)."""

import importlib.util
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
STEP_SKILLS = ("intake", "strategy", "brand-platform", "identity", "design-system", "brand-book")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, "scripts", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ow = load("owner")


def skill(name):
    with open(os.path.join(SKILL, "steps", name + ".md"), encoding="utf-8") as handle:
        return handle.read()


class Skills(unittest.TestCase):
    def test_every_step_runs_owner_py_from_the_skill_root(self):
        for name in STEP_SKILLS:
            self.assertIn('python3 "$GW/scripts/owner.py"', skill(name), name)

    def test_every_step_skill_lists_its_questions(self):
        for name in STEP_SKILLS:
            self.assertIn("## The owner's answers", skill(name), name)

    def test_the_ids_in_the_skills_are_valid(self):
        ident = re.compile(r"`(\d\d-[a-z-]+\.[a-zA-Z0-9.-]+)`")
        checked = 0
        for name in STEP_SKILLS:
            for match in ident.finditer(skill(name)):
                value = match.group(1).replace("-NN", "-01").replace("dig-N", "dig-1")
                if value.count(".") != 2:
                    continue
                ow.check_id(value)
                checked += 1
        self.assertGreater(checked, 15)

    def test_intake_ids_are_fixed(self):
        text = skill("intake")
        for value in ("00-intake.kickoff.story", "00-intake.kickoff.profile",
                      "00-intake.kickoff.market-language", "00-intake.kickoff.name",
                      "00-intake.brief.approve-NN", "00-intake.step.approve-01"):
            self.assertIn("`%s`" % value, text)
            ow.check_id(value.replace("-NN", "-01"))

    def test_no_skill_places_brand_at_the_root_of_the_project(self):
        for name in STEP_SKILLS + ("status",):
            text = skill(name)
            self.assertNotIn("belongs at the root of the owner's project", text, name)
            self.assertNotIn("`brand/` is at the root of the owner's project", text, name)
        with open(os.path.join(SKILL, "reference", "step-protocol.md"), encoding="utf-8") as handle:
            protocol = handle.read()
        self.assertNotIn("is at the root of the target project", protocol)
        self.assertIn("## Asking the owner", protocol)
        self.assertIn("--headless", protocol)


if __name__ == "__main__":
    unittest.main()
