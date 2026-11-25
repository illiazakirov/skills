"""Tests for the profile files and for the strategy skill's agreement with the contract."""

import importlib.util
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
PROFILES = os.path.join(SKILL, "profiles")

_spec = importlib.util.spec_from_file_location(
    "check_contract", os.path.join(SKILL, "scripts", "check_contract.py"))
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

PARTS = ["Strategy questions", "Marketing mix", "Platform questions", "Identity questions",
         "Surfaces", "Components", "Pages"]
SESSIONS = ["Archetype", "Voice", "Name", "Mood"]
TOOLS = ["Golden Circle", "Lean Canvas", "ICP and Jobs-to-be-Done", "Positioning",
         "Brand wheel", "Marketing mix", "Messaging hierarchy"]


def doc(*parts):
    """A local design document. They are not in git, so the check is skipped without them."""
    path = os.path.join(ROOT, "docs", "marketing", "brand", *parts)
    if not os.path.isfile(path):
        raise unittest.SkipTest("local design document missing: docs/marketing/brand/" + "/".join(parts))
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def read(*parts):
    with open(os.path.join(SKILL, *parts), encoding="utf-8") as handle:
        return handle.read()


def profile_files():
    return sorted(name for name in os.listdir(PROFILES)
                  if name.endswith(".md") and name != "README.md")


class Profiles(unittest.TestCase):
    def test_personal_brand_exists(self):
        self.assertIn("personal-brand.md", profile_files())

    def test_every_profile_is_a_known_profile_id(self):
        for name in profile_files():
            self.assertIn(name[:-len(".md")], cc.PROFILES)

    def test_every_profile_has_the_parts_in_order(self):
        for name in profile_files():
            text = read("profiles", name)
            self.assertRegex(text, r"(?m)^Status: (untested|tested)$", name)
            self.assertEqual(re.findall(r"(?m)^## (.+)$", text), PARTS, name)
            parts = re.split(r"(?m)^## .+$", text)
            self.assertEqual(re.findall(r"(?m)^### (.+)$", parts[1]), TOOLS, name)
            mix = parts[2]
            self.assertRegex(mix, r"\b(4P|7P)\b", name)
            self.assertEqual(re.findall(r"(?m)^### (.+)$", parts[3]), SESSIONS, name)
            for session in re.split(r"(?m)^### .+$", parts[3])[1:]:
                self.assertRegex(session, r"(?m)^- .+\?$", name)
            self.assertEqual(re.findall(r"(?m)^### (.+)$", parts[4]), ["Logo", "Surfaces"], name)
            for part in re.split(r"(?m)^### .+$", parts[4])[1:]:
                self.assertRegex(part, r"(?m)^- .+\?$", name)


class StrategySkill(unittest.TestCase):
    def test_names_every_tool_file(self):
        skill = read("steps", "strategy.md")
        for path in cc.STRATEGY_TOOLS:
            self.assertIn("`%s`" % path, skill)

    def test_every_tool_has_its_fixed_text_and_benchmark(self):
        for number, path in enumerate(cc.STRATEGY_TOOLS, 1):
            text = read("steps", "strategy", "tools", path)
            self.assertEqual(re.findall(r"(?m)^## (.+)$", text)[:4],
                             ["Briefing", "Dig", "Sharpness tests", "Link"], path)
            self.assertIn("Session %d of 7" % number, text, path)
            benchmark = read("steps", "strategy", "benchmark", path)
            for slot in cc.PLATES["01-strategy"][path][1]:
                self.assertIn("\n## %s\n" % slot["name"], benchmark, path)
            self.assertIn("\n## Note\n", benchmark, path)

    def test_headline_slots_are_named_in_the_tool_notes(self):
        for path, (_title, slots) in cc.PLATES["01-strategy"].items():
            text = read("steps", "strategy", "tools", path)
            for slot in slots:
                if slot["headline"]:
                    self.assertIn("The headline slot is `%s`." % slot["name"], text, path)

    def test_skill_scripts_exist(self):
        for folder in ("intake", "strategy"):
            skill = read("steps", folder + ".md")
            for name in set(re.findall(r"scripts/([a-z_]+\.py)", skill)):
                self.assertTrue(os.path.isfile(os.path.join(SKILL, "scripts", name)), name)


class IntakeSkill(unittest.TestCase):
    def test_names_the_brief_and_its_slots(self):
        skill = read("steps", "intake.md")
        self.assertIn("`brief.md`", skill)
        for slot in cc.PLATES["00-intake"]["brief.md"][1]:
            self.assertIn("`%s`" % slot["name"], skill)


class BrandPlatform(unittest.TestCase):
    def test_skill_names_every_file_and_section(self):
        skill = read("steps", "brand-platform.md")
        for path, (required, sections) in cc.MARKDOWN["02-brand-platform"].items():
            self.assertIn("`%s`" % path, skill)
            for section in sections:
                self.assertIn("`%s`" % section, skill, "%s: %s" % (path, section))

    def test_skill_scripts_exist(self):
        skill = read("steps", "brand-platform.md")
        for name in set(re.findall(r"scripts/([a-z_]+\.py)", skill)):
            self.assertTrue(os.path.isfile(os.path.join(SKILL, "scripts", name)), name)


class PlatformSkill(unittest.TestCase):
    def tool(self, path):
        return read("steps", "brand-platform", "tools", path)

    def test_every_session_has_its_fixed_text(self):
        for path in cc.PLATFORM_TOOLS:
            heads = re.findall(r"(?m)^## (.+)$", self.tool(path))
            wanted = ["Briefing", "Dig", "Sharpness tests", "Link", "Notes for the agency"]
            self.assertEqual([h for h in heads if h in wanted], wanted, path)
        self.assertIn("\n## Opening\n", self.tool("mood.md"))
        for number, path in enumerate(cc.PLATFORM_TOOLS, 1):
            self.assertIn("Session %d of 4" % number, self.tool(path), path)

    def test_every_benchmark_is_a_valid_plate(self):
        for path in cc.PLATFORM_TOOLS:
            lines = read("steps", "brand-platform", "benchmark", path).splitlines()
            self.assertEqual(lines[0], "---", path)
            self.assertIn("step: 02-brand-platform", lines[1:5], path)
            body = lines[lines.index("---", 1) + 1:]
            report = cc.Report()
            cc.check_sections(path, body, cc.MARKDOWN["02-brand-platform"][path][1], report)
            cc.check_plate(path, body, cc.PLATES["02-brand-platform"][path][1], report)
            self.assertEqual(report.errors, [], path)
            self.assertIn("## Note", body, path)
            self.assertNotIn("## Rationale", body, path)
            self.assertRegex("\n".join(body), r"Apple, \d{4}\. A teaching reconstruction\.", path)

    def test_headline_slots_are_named_in_the_tool_notes(self):
        for path, (_title, slots) in cc.PLATES["02-brand-platform"].items():
            for slot in slots:
                if slot["headline"]:
                    self.assertIn("The headline slot is `%s`." % slot["name"],
                                  self.tool(path), path)

    def test_archetype_briefing_lists_all_twelve(self):
        text = self.tool("archetype.md")
        for name in cc.ARCHETYPES:
            self.assertRegex(text, r"(?m)^%s\s+- .+ - .+$" % name)
        self.assertNotIn("Apple", text)
        self.assertNotIn("<the twelve lines>", text)
        self.assertIn("The examples are the common reading of the trade; "
                      "not all of them are from the book.", text)

    def test_tone_order_in_the_voice_briefing(self):
        self.assertIn("formal or casual, serious or funny, respectful or irreverent, "
                      "matter-of-fact or enthusiastic", self.tool("voice.md"))

    def test_skill_names_every_session_file_and_no_removed_step(self):
        skill = read("steps", "brand-platform.md")
        for path in cc.PLATFORM_TOOLS + ["creative-brief.md"]:
            self.assertIn("`%s`" % path, skill)
        for gone in ("audience-language", "references.md", "validation", "naming.md",
                     "research", "grill"):
            self.assertNotIn(gone, skill)
        self.assertNotIn("—", skill)
        for role in ("**Strategist**", "**Copywriter**", "**Art Director**"):
            self.assertIn(role, skill)

    def test_skill_carries_the_closing_link_word_for_word(self):
        self.assertIn("Next: the Identity. Everything so far was decided in words and in mood; "
                      "next the Art Director draws it: the logo, the colors and the type, "
                      "inside the territory you fixed.",
                      read("steps", "brand-platform.md"))


    def test_given_assets_need_no_earlier_answer_about_tools(self):
        skill = read("steps", "brand-platform.md")
        given = skill[skill.index("### Given assets"):skill.index("### Tools")]
        self.assertIn("screenshot.py --find", given)
        self.assertIn("Source: given", given)
        self.assertIn("exits with 1 or 2", given)

    def test_identity_may_read_the_voice_it_checks_against(self):
        identity = read("steps", "identity.md")
        self.assertIn("the Motto session also reads `brand/02-brand-platform/voice.md`", identity)

    def test_later_skills_do_not_name_removed_files(self):
        for skill in ("identity", "design-system", "brand-book"):
            text = read("steps", skill + ".md")
            self.assertNotIn("naming.md", text, skill)
            self.assertNotIn("Tone scales", text, skill)
            self.assertNotIn("Visual direction", text, skill)

    def test_fixed_texts_keep_apple_out_of_the_tools(self):
        for path in cc.PLATFORM_TOOLS:
            self.assertNotIn("Apple", self.tool(path), path)
            self.assertNotIn("iMac", self.tool(path), path)

class IdentitySkill(unittest.TestCase):
    STEP = "03-identity"

    def tool(self, path):
        return read("steps", "identity", "tools", path)

    def skill(self):
        return read("steps", "identity.md")

    def test_every_session_has_its_fixed_text(self):
        for number, path in enumerate(cc.IDENTITY_TOOLS, 1):
            heads = re.findall(r"(?m)^## (.+)$", self.tool(path))
            self.assertEqual(heads, ["Briefing", "Dig", "Sharpness tests", "Link",
                                     "Notes for the agency"], path)
            self.assertIn("**Strategist:** Session %d of 4" % number, self.tool(path), path)
            self.assertEqual(len(re.findall(r"(?m)^\d\. ", self.tool(path))), 3, path)
            self.assertEqual(len(re.findall(
                r"(?m)^- ", self.tool(path).split("## Sharpness tests")[1].split("## Link")[0])),
                5, path)

    def test_who_leads_each_session(self):
        for path in ("logo.md", "color.md", "typography.md"):
            self.assertIn("\nFrom here the Art Director leads.\n", self.tool(path), path)
        self.assertIn("\nFrom here the Copywriter leads.\n", self.tool("motto.md"))

    def test_every_benchmark_is_a_valid_plate(self):
        for path in cc.IDENTITY_TOOLS:
            lines = read("steps", "identity", "benchmark", path).splitlines()
            self.assertEqual(lines[0], "---", path)
            self.assertIn("step: 03-identity", lines[1:5], path)
            body = lines[lines.index("---", 1) + 1:]
            report = cc.Report()
            cc.check_sections(path, body, cc.MARKDOWN[self.STEP][path][1], report)
            cc.check_plate(path, body, cc.PLATES[self.STEP][path][1], report)
            self.assertEqual(report.errors, [], path)
            self.assertIn("## Note", body, path)
            self.assertNotIn("## Rationale", body, path)
            self.assertRegex("\n".join(body), r"Apple, \d{4}\. A teaching reconstruction\.", path)

    def test_color_benchmark_carries_the_calculated_contrast(self):
        body = read("steps", "identity", "benchmark", "color.md").splitlines()
        values = cc.plate_values(body, cc.PLATES[self.STEP]["color.md"][1])
        self.assertEqual(values["Contrast"],
                         cc.contrast_lines(cc.parse_palette(values["Palette"])))

    def test_headline_slots_are_named_in_the_tool_notes(self):
        for path, (_title, slots) in cc.PLATES[self.STEP].items():
            for slot in slots:
                if slot["headline"]:
                    self.assertIn("The headline slot is `%s`." % slot["name"],
                                  self.tool(path), path)

    def test_fixed_texts_keep_apple_out_of_the_tools_and_the_skill(self):
        for text in [self.tool(path) for path in cc.IDENTITY_TOOLS]:
            for word in ("Apple", "iMac", "Bondi"):
                self.assertNotIn(word, text)
        self.assertNotIn("Bondi", self.skill())
        self.assertNotIn("Think different", self.skill())

    def test_skill_carries_the_opening_and_the_closing_word_for_word(self):
        skill = self.skill()
        self.assertIn(
            "> **Strategist:** The platform is approved, and from here the agency works from "
            "one page: the Creative Brief. The identity is four sessions: Logo, Color, "
            "Typography, Motto. In the first three the Art Director draws three proposals and "
            "you choose in the browser. In the fourth the Copywriter writes. Nothing is fixed "
            "until you say it is.", skill)
        self.assertIn("> What you asked to keep stays as it is; its session is short.", skill)
        self.assertIn(
            "> **Strategist:** The identity is approved. Every plate you made before is now "
            "set in your brand's colors and type: open the brand map. Next is the design "
            "system, in a new session: the Art Director turns the identity into the rules of "
            "an interface.", skill)

    def test_profile_questions_word_for_word(self):
        profile = read("profiles", "personal-brand.md")
        self.assertIn("- Is the logo your own name, your initials, or a mark apart from you?",
                      profile)
        self.assertIn("- On the avatar: your photograph, or the mark?", profile)

    def test_skill_names_the_sessions_and_nothing_of_the_old_flow(self):
        skill = self.skill()
        for path in cc.IDENTITY_TOOLS:
            self.assertIn("`%s`" % path, skill)
            self.assertIn("`tools/%s`" % path, skill)
            self.assertIn("`benchmark/%s`" % path, skill)
        for gone in ("level.md", "rules.md", "direction-", "Brand colors", "Type pair",
                     "research", "validation", "Google Fonts by"):
            self.assertNotIn(gone, skill)
        self.assertNotIn("—", skill)
        for role in ("**Strategist**", "**Copywriter**", "**Art Director**"):
            self.assertIn(role, skill)
        for word in ("keep", "adapt", "replace"):
            self.assertIn("**%s**" % word, skill)



class Identity(unittest.TestCase):
    def test_skill_names_every_file_and_section(self):
        skill = read("steps", "identity.md")
        for path, (required, sections) in cc.MARKDOWN["03-identity"].items():
            self.assertIn("`%s`" % path, skill)
            for section in sections:
                self.assertIn("`%s`" % section, skill, "%s: %s" % (path, section))
        for path in cc.OTHER["03-identity"]:
            self.assertIn(path, skill)

    def test_skill_scripts_exist_and_critic_is_defined(self):
        skill = read("steps", "identity.md")
        for name in set(re.findall(r"scripts/([a-z_]+\.py)", skill)):
            self.assertTrue(os.path.isfile(os.path.join(SKILL, "scripts", name)), name)
        self.assertIn("`critic.md`", skill)
        critic = read("critic.md")
        self.assertTrue(critic.startswith("# Critic"))
        for line in ("grid:", "typography:", "density:", "contrast:", "cheap-expensive:",
                     "verdict: pass | rework"):
            self.assertIn(line, critic)

    def test_surfaces_of_the_profile_are_in_the_skill(self):
        skill = read("steps", "identity.md")
        profile = read("profiles", "personal-brand.md")
        surfaces = re.split(r"(?m)^## .+$", profile)[5]
        for name in re.findall(r"(?m)^- (.+)$", surfaces):
            self.assertIn("| %s |" % name, skill)


class DesignSystem(unittest.TestCase):
    def skill(self):
        return read("steps", "design-system.md")

    def design(self):
        return doc("design", "design-system.md")

    def test_skill_names_every_file_and_section(self):
        skill = self.skill()
        for path, (required, sections) in cc.MARKDOWN["04-design-system"].items():
            self.assertIn("`%s`" % path, skill)
            for section in sections:
                self.assertIn("`%s`" % section, skill, "%s: %s" % (path, section))
        for path in cc.OTHER["04-design-system"]:
            self.assertIn(path.split("/")[-1], skill, path)
        for names in cc.COMPONENTS.values():
            for name in names:
                self.assertIn(name, skill)

    def test_skill_scripts_exist(self):
        skill = self.skill()
        self.assertIn("`critic.md`", skill)
        for name in set(re.findall(r"scripts/([a-z_]+\.py)", skill)):
            self.assertTrue(os.path.isfile(os.path.join(SKILL, "scripts", name)), name)

    def test_the_session_has_its_fixed_text_and_no_benchmark(self):
        text = read("steps", "design-system", "tools", "interface.md")
        self.assertEqual(re.findall(r"(?m)^## (.+)$", text),
                         ["Briefing", "Dig", "Sharpness tests", "Link", "Notes for the agency"])
        self.assertIn("Session 1 of 1", text)
        self.assertIn("The headline slot is `Interface idea`.", text)
        self.assertFalse(os.path.exists(os.path.join(SKILL, "steps", "design-system",
                                                     "benchmark")))
        self.assertNotIn("Apple", text + self.skill())

    def test_fixed_texts_word_for_word(self):
        approved = self.design()
        approved = approved[approved.index("### Opening"):approved.index("## Fact check")]
        text = self.skill() + read("steps", "design-system", "tools", "interface.md")
        for line in approved.splitlines():
            line = line[2:] if line.startswith("> ") else line
            line = line.strip()
            if line and not line.startswith(("#", "Approved", "Only when", "Asked only", "`")) \
                    and line != ">":
                self.assertIn(line, text)

    def test_no_layout_choice_is_left(self):
        skill = self.skill()
        for old in ("layout-", "Layout and hero", "type-scale-", "components-NN"):
            self.assertNotIn(old, skill)


class BrandBook(unittest.TestCase):
    def skill(self):
        return read("steps", "brand-book.md")

    def test_skill_names_every_file_and_section(self):
        skill = self.skill()
        for path, (required, sections) in cc.MARKDOWN["05-brand-book"].items():
            self.assertIn("`%s`" % path, skill)
            for section in sections:
                self.assertIn(section, skill, "%s: %s" % (path, section))
        for path in cc.OTHER["05-brand-book"]:
            self.assertIn("`%s`" % path, skill)

    def test_skill_scripts_exist(self):
        skill = self.skill()
        for name in set(re.findall(r"scripts/([a-z_]+\.py)", skill)):
            self.assertTrue(os.path.isfile(os.path.join(SKILL, "scripts", name)), name)

    def test_fixed_texts_word_for_word(self):
        design = doc("design", "brand-book.md")
        for heading in ("### Opening", "### Showing the review page", "### Closing"):
            block = design[design.index(heading):].split("\n\n")[1]
            self.assertTrue(block.startswith("> "), heading)
            self.assertIn(block, self.skill(), heading)

    def test_the_book_is_built_by_the_script_and_asks_nothing(self):
        skill = self.skill()
        self.assertIn("render_book.py", skill)
        for old in ("bundle_html.py", "the language of the page", "brand:critic"):
            self.assertNotIn(old, skill)


class Plugin(unittest.TestCase):
    def test_every_step_has_a_file_and_the_steps_chain(self):
        order = ["intake", "strategy", "brand-platform", "identity",
                 "design-system", "brand-book"]
        self.assertEqual(sorted(n[:-3] for n in os.listdir(os.path.join(SKILL, "steps")) if n.endswith(".md")),
                         sorted(order + ["status"]))
        for name, following in zip(order, order[1:]):
            skill = read("steps", name + ".md")
            self.assertIn("brand %s" % following, skill, name)

    def test_no_placeholder_files_are_left(self):
        for directory, _, files in os.walk(os.path.join(SKILL, "steps")):
            self.assertNotIn(".gitkeep", files, directory)


if __name__ == "__main__":
    unittest.main()
