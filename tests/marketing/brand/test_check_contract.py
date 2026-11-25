"""Tests for scripts/check_contract.py.

tests/fixtures/valid/brand is a complete, valid brand/ directory with every
step approved. Each broken case copies it to a temporary directory, breaks one
thing and asserts the error the script reports.

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
SCRIPT = os.path.join(SKILL, "scripts", "check_contract.py")
VALID = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand")

_spec = importlib.util.spec_from_file_location("check_contract", SCRIPT)
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)


class BrandCase(unittest.TestCase):
    """Gives each test its own copy of the valid brand/ to break."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.brand = os.path.join(self.tmp, "brand")
        shutil.copytree(VALID, self.brand)

    def path(self, relative):
        return os.path.join(self.brand, *relative.split("/"))

    def read(self, relative):
        with open(self.path(relative), encoding="utf-8") as handle:
            return handle.read()

    def write(self, relative, text):
        os.makedirs(os.path.dirname(self.path(relative)), exist_ok=True)
        with open(self.path(relative), "w", encoding="utf-8") as handle:
            handle.write(text)

    def replace(self, relative, old, new, count=1):
        text = self.read(relative)
        self.assertIn(old, text, "the fixture no longer contains %r" % old)
        self.write(relative, text.replace(old, new, count))

    def remove(self, relative):
        target = self.path(relative)
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)

    def set_step(self, step, old, new):
        """Replace text inside one step's block of pipeline.yaml."""
        text = self.read("pipeline.yaml")
        start = text.index("  %s:\n" % step)
        end = text.find("\n  0", start + 1)
        end = len(text) if end == -1 else end
        block = text[start:end]
        self.assertIn(old, block)
        self.write("pipeline.yaml", text[:start] + block.replace(old, new, 1) + text[end:])

    def set_statuses_from(self, first_step, status):
        """Give first_step and every later step a status with no version or built_on."""
        text = self.read("pipeline.yaml")
        head = text[: text.index("  %s:\n" % first_step)]
        tail = "".join(
            "  %s:\n    status: %s\n    spent: 0\n" % (step, status)
            for step in cc.STEPS[cc.STEPS.index(first_step):]
        )
        self.write("pipeline.yaml", head + tail)

    def check(self, step=None):
        return cc.check(self.brand, step)

    def assertError(self, path, fragment, step=None):
        errors = self.check(step).errors
        if not any(p == path and fragment in message for p, message in errors):
            self.fail("no error for %s containing %r; errors were:\n%s"
                      % (path, fragment, "\n".join("%s: %s" % e for e in errors) or "(none)"))

    def assertNoError(self, path, step=None):
        errors = [e for e in self.check(step).errors if e[0] == path]
        self.assertEqual(errors, [])

    def assertClean(self, step=None):
        report = self.check(step)
        self.assertEqual(report.errors, [])
        return report


ARCH = "02-brand-platform/archetype.md"
VOICE = "02-brand-platform/voice.md"
MOOD = "02-brand-platform/mood.md"
NAME = "02-brand-platform/name.md"
DECISIONS = "02-brand-platform/review/decisions.md"
NAME_PLATE = """---
step: 02-brand-platform
status: approved
source: generated
---

# Name

## Name

iMac

## Domain

A product name: it lives at apple.com.

## What it says

The Macintosh for the internet, in one letter.

## Rejected

- MacMan: the CEO's own favorite; the agency argued it away.
"""


class PlatformPlates(BrandCase):
    STEP = "02-brand-platform"

    def test_fixture_platform_is_clean(self):
        self.assertClean(self.STEP)

    def test_unknown_archetype(self):
        self.replace(ARCH, "\nOutlaw\n", "\nPirate\n")
        self.assertError(ARCH, "Primary archetype")

    def test_primary_and_secondary_must_differ(self):
        self.replace(ARCH, "\nCreator\n", "\nOutlaw\n")
        self.assertError(ARCH, "must differ")

    def test_character_shape(self):
        self.replace(ARCH, "The rebel who builds", "A rebel that builds")
        self.assertError(ARCH, "Character")

    def test_personality_needs_but_not(self):
        self.replace(ARCH, "Rebellious, but not destructive:", "Rebellious:")
        self.assertError(ARCH, "Personality")

    def test_tone_out_of_order_names_the_expected_dimension(self):
        text = self.read(VOICE)
        first = "- Formal–casual: 4 of 5. One person talking to another across a table.\n"
        second = "- Serious–funny: 3 of 5. Wit in the headline, straight in the facts.\n"
        self.assertIn(first + second, text)
        self.write(VOICE, text.replace(first + second, second + first))
        self.assertError(VOICE, "Formal–casual")

    def test_tone_repeated_dimension(self):
        self.replace(VOICE, "- Serious–funny: 3", "- Formal–casual: 3")
        self.assertError(VOICE, "Serious–funny")

    def test_tone_accepts_a_plain_hyphen(self):
        self.replace(VOICE, "Formal–casual", "Formal-casual")
        self.assertNoError(VOICE)

    def test_tone_position_out_of_range(self):
        self.replace(VOICE, "4 of 5. One person", "6 of 5. One person")
        self.assertError(VOICE, "Tone")

    def test_example_needs_right_and_wrong(self):
        self.replace(VOICE, ' Wrong: "Compare our specifications."', "")
        self.assertError(VOICE, "Examples")

    def test_mood_words_are_single_words(self):
        self.replace(MOOD, "- Playful", "- Very playful")
        self.assertError(MOOD, "Mood words")

    def test_naming_md_is_no_longer_part_of_the_contract(self):
        self.write("02-brand-platform/naming.md", "x")
        self.assertError("02-brand-platform/naming.md", "not part of the contract")

    def test_name_plate_must_match_the_brief(self):
        self.write(NAME, NAME_PLATE)
        self.assertError(NAME, "Brand")
        self.replace("00-intake/brief.md", "\nApple\n", "\niMac\n")
        self.assertNoError(NAME)

    def test_draft_name_plate_is_not_compared_with_the_brief(self):
        self.set_statuses_from("02-brand-platform", "in-progress")
        self.write(NAME, NAME_PLATE.replace("status: approved", "status: draft"))
        self.assertNoError(NAME)

    def test_unnamed_brief_without_a_name_plate(self):
        self.replace("00-intake/brief.md", "\nApple\n", "\nUnnamed\n")
        self.assertError(NAME, "missing")

    def test_unnamed_brief_is_fine_while_the_step_is_in_progress(self):
        self.replace("00-intake/brief.md", "\nApple\n", "\nUnnamed\n")
        self.set_statuses_from("02-brand-platform", "in-progress")
        self.assertNoError(NAME)

    def test_non_latin_name_is_one_word(self):
        self.write(NAME, NAME_PLATE.replace("iMac", "Ґрунт"))
        self.replace("00-intake/brief.md", "\nApple\n", "\nҐрунт\n")
        self.assertNoError(NAME)

    def test_name_longer_than_three_words(self):
        self.write(NAME, NAME_PLATE.replace("iMac", "The Very Long Name"))
        self.assertError(NAME, "limit is 3")

    def test_short_mood_session_needs_no_decisions(self):
        self.replace(MOOD, "source: generated", "source: provided")
        self.remove(DECISIONS)
        self.assertNoError(DECISIONS)

    def test_generated_mood_still_needs_decisions(self):
        self.remove(DECISIONS)
        self.assertError(DECISIONS, "missing")

    def test_given_directory_is_optional_but_not_empty(self):
        os.makedirs(self.path("02-brand-platform/given"))
        self.assertError("02-brand-platform/given/", "is empty")
        self.write("02-brand-platform/given/inventory.md", "# Given\n")
        self.assertNoError("02-brand-platform/given/")
        self.assertNoError("02-brand-platform/given")

    def test_creative_brief_sections(self):
        self.replace("02-brand-platform/creative-brief.md", "## Given\n\nNothing given.\n", "")
        self.assertError("02-brand-platform/creative-brief.md", "missing section '## Given'")

LOGO = "03-identity/logo.md"
COLOR = "03-identity/color.md"
TYPE = "03-identity/typography.md"
MOTTO = "03-identity/motto.md"
APPLE_PALETTE = ["White - #FFFFFF - background on light, text on dark",
                 "Black - #000000 - text on light, background on dark",
                 "Bondi Blue - #0095B6 - accent"]


class IdentityPlates(BrandCase):
    STEP = "03-identity"

    def test_fixture_identity_is_clean(self):
        report = self.assertClean(self.STEP)
        self.assertEqual(report.warnings, [])

    def test_order_of_the_sessions(self):
        self.assertEqual(cc.IDENTITY_TOOLS,
                         ["logo.md", "color.md", "typography.md", "motto.md"])

    def test_headline_slots(self):
        found = [slot["name"] for _title, slots in cc.PLATES[self.STEP].values()
                 for slot in slots if slot["headline"]]
        self.assertEqual(found, ["Logo idea", "Color idea", "Type idea", "Motto"])

    def test_old_rules_file_is_not_part_of_the_contract(self):
        self.write("03-identity/logo/rules.md", "# Rules\n")
        self.assertClean(self.STEP)  # logo/ is a directory of the contract; its files are free
        self.write("03-identity/rules.md", "# Rules\n")
        self.assertError("03-identity/rules.md", "not part of the contract")

    def test_unknown_kind(self):
        self.replace(LOGO, "Symbol and wordmark", "Emblem")
        self.assertError(LOGO, "be one of: Wordmark, Symbol and wordmark, Monogram")

    def test_minimum_size_lines_keep_their_order(self):
        self.replace(LOGO, "- Full logo: 24 px high\n- Mark: 16 px high",
                     "- Mark: 16 px high\n- Full logo: 24 px high")
        self.assertError(LOGO, "must start with 'Full logo:'")

    def test_minimum_size_is_a_number_of_pixels(self):
        self.replace(LOGO, "24 px high", "small")
        self.assertError(LOGO, "Full logo: N px high")

    def test_never_has_exactly_three(self):
        self.replace(LOGO, "- Redrawn, stretched or tilted\n", "")
        self.assertError(LOGO, "has 2 items; must have exactly 3")

    def test_logo_idea_word_limit(self):
        self.replace(LOGO, "the shape alone is enough.",
                     "the shape alone is more than enough for us.")
        self.assertError(LOGO, "the limit is 12")

    def test_palette_line_without_a_hex(self):
        self.replace(COLOR, "#0095B6", "blue")
        self.assertError(COLOR, "Name - #RRGGBB - role")

    def test_two_accents(self):
        self.replace(COLOR, "- Bondi Blue - #0095B6 - accent",
                     "- Bondi Blue - #0095B6 - accent\n- Tangerine - #FF8800 - accent")
        self.assertError(COLOR, "the role 'accent' is given 2 times")

    def test_no_text_color_for_the_dark_theme(self):
        self.replace(COLOR, "background on light, text on dark", "background on light")
        self.assertError(COLOR, "the role 'text on dark' is given 0 times")

    def test_unknown_role(self):
        self.replace(COLOR, "- Bondi Blue - #0095B6 - accent",
                     "- Bondi Blue - #0095B6 - accent, links")
        self.assertError(COLOR, "has the role 'links'")

    def test_two_secondaries(self):
        self.replace(COLOR, "- Bondi Blue - #0095B6 - accent",
                     "- Bondi Blue - #0095B6 - accent\n- Grape - #663399 - secondary"
                     "\n- Lime - #99CC00 - secondary")
        self.assertError(COLOR, "'secondary' is given more than once")

    def test_one_secondary_is_fine(self):
        self.replace(COLOR, "- Bondi Blue - #0095B6 - accent",
                     "- Bondi Blue - #0095B6 - accent\n- Grape - #663399 - secondary")
        self.assertClean(self.STEP)

    def test_contrast_must_follow_from_the_palette(self):
        self.replace(COLOR, "#0095B6", "#00B5D6")
        self.assertError(COLOR, "does not follow from the palette")

    def test_contrast_error_shows_the_expected_line(self):
        self.replace(COLOR, "Bondi Blue on Black: 6 to 1", "Bondi Blue on Black: 9 to 1")
        self.assertError(COLOR, "it must be 'Bondi Blue on Black: 6 to 1'")

    def test_body_text_must_reach_four_and_a_half(self):
        self.replace(COLOR, "- Black - #000000 - text on light, background on dark",
                     "- Gray - #999999 - text on light, background on dark")
        self.assertError(COLOR, "body text must reach 4.5 to 1")

    def test_sizes_keep_their_order_and_shape(self):
        self.replace(TYPE, "- Lead: 24 px at 1440, 20 px at 390", "- Lead: 24 px")
        self.assertError(TYPE, "Headline: N px at 1440, N px at 390")

    def test_display_has_family_weights_and_role(self):
        self.replace(TYPE, "Apple Garamond - one light weight - headlines, and the line under "
                           "the logo", "Apple Garamond")
        self.assertError(TYPE, "Family - weights - role")

    def test_motto_word_limit(self):
        self.replace(MOTTO, "Think different.", "Think a little different every single day.")
        self.assertError(MOTTO, "the limit is 6")

    def test_motto_in_another_script_is_counted_in_words(self):
        self.replace(MOTTO, "Think different.", "Думай інакше, роби просто, живи довго.")
        self.assertClean(self.STEP)

    def test_rejected_is_optional(self):
        text = self.read(MOTTO)
        start, end = text.index("## Rejected"), text.index("## Rationale")
        self.write(MOTTO, text[:start] + text[end:])
        self.assertClean(self.STEP)

    def test_rejected_needs_a_reason(self):
        self.replace(MOTTO, " - correct grammar", ": correct grammar")
        self.assertError(MOTTO, "Motto - reason")

    def test_kept_asset_has_no_choice_in_decisions(self):
        self.replace(COLOR, "source: generated", "source: provided")
        self.write("03-identity/review/decisions.md", "\n".join(
            "## %d. %s\n\n- Page: %s\n- Decision: 1\n- Comment:\n- Status: fixed\n"
            % (number, name, page) for number, (name, page) in enumerate(
                [("Logo", "logo-02.html"), ("Typography", "typography-01.html"),
                 ("Motto", "motto-01.html"), ("Surfaces", "surfaces-01.html")], 1)))
        self.assertClean(self.STEP)

    def test_contrast_lines_of_a_palette(self):
        self.assertEqual(cc.contrast_lines(cc.parse_palette(APPLE_PALETTE)), [
            "Black on White: 21 to 1", "White on Black: 21 to 1",
            "Bondi Blue on White: 3.5 to 1, large text only", "Bondi Blue on Black: 6 to 1"])

    def test_weak_accent_is_marked_not_for_text(self):
        lines = cc.contrast_lines(cc.parse_palette(
            APPLE_PALETTE[:2] + ["Cream - #FFF8E0 - accent"]))
        self.assertTrue(lines[2].endswith(", not for text"), lines[2])

    def test_palette_name_may_hold_a_hyphen(self):
        palette = cc.parse_palette(APPLE_PALETTE[:2] + ["Blue-gray - #5A6B7C - accent"])
        self.assertEqual(palette[2]["name"], "Blue-gray")

    def test_contrast_command(self):
        result = subprocess.run([sys.executable, SCRIPT, "contrast"] + APPLE_PALETTE,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- Bondi Blue on White: 3.5 to 1, large text only", result.stdout)

    def test_contrast_command_refuses_weak_body_text(self):
        result = subprocess.run(
            [sys.executable, SCRIPT, "contrast", APPLE_PALETTE[0],
             "Gray - #999999 - text on light, background on dark", APPLE_PALETTE[2]],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("body text must reach 4.5 to 1", result.stderr)

    def test_contrast_command_names_a_missing_role(self):
        result = subprocess.run([sys.executable, SCRIPT, "contrast"] + APPLE_PALETTE[:2],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("the role 'accent' is given 0 times", result.stderr)


class ValidBrand(BrandCase):
    def test_complete_brand_has_no_errors_or_warnings(self):
        report = self.assertClean()
        self.assertEqual(report.warnings, [])

    def test_each_step_passes_on_its_own(self):
        for step in cc.STEPS:
            self.assertClean(step)

    def test_fal_key_files_are_ignored(self):
        self.write(".env", "FAL_KEY=put-fal-key-here\n")
        self.write(".gitignore", ".env\n")
        report = self.assertClean()
        self.assertEqual(report.warnings, [])

    def test_fresh_project_after_intake(self):
        self.set_statuses_from("01-strategy", "pending")
        for step in cc.STEPS[1:]:
            self.remove(step)
        report = self.assertClean()
        self.assertEqual(report.warnings, [])

    def test_step_in_progress_may_be_incomplete(self):
        self.set_statuses_from("05-brand-book", "in-progress")
        self.remove("05-brand-book/index.html")
        self.remove("05-brand-book/summary.md")
        self.replace("05-brand-book/brand-book.md", "status: approved", "status: draft")
        self.assertClean()

    def test_optional_files_are_accepted(self):
        self.write("02-brand-platform/name.md", NAME_PLATE.replace("iMac", "Apple"))
        self.assertNoError("02-brand-platform/name.md")

    def test_seven_p_sections_are_accepted(self):
        self.assertIn("## Physical evidence", self.read("01-strategy/marketing-mix.md"))
        self.assertClean()

    def test_four_p_sections_are_accepted(self):
        text = self.read("01-strategy/marketing-mix.md")
        start, end = text.index("## People"), text.index("## Note")
        self.write("01-strategy/marketing-mix.md", text[:start] + text[end:])
        self.assertClean()

    def test_provided_source_is_accepted(self):
        self.replace("03-identity/color.md", "source: generated", "source: provided")
        self.assertClean()

    def test_skipped_step_needs_only_its_summary(self):
        self.set_step("03-identity", "status: approved", "status: skipped")
        for name in ("logo", "color.md", "typography.md", "motto.md", "surfaces", "review"):
            self.remove("03-identity/" + name)
        self.assertClean()
        self.remove("03-identity/summary.md")
        self.assertError("03-identity/summary.md", "missing")

    def test_dotfiles_are_ignored(self):
        self.write("01-strategy/.DS_Store", "x")
        self.write("03-identity/surfaces/.DS_Store", "x")
        report = self.assertClean()
        self.assertEqual(report.warnings, [])


class PipelineTemplate(BrandCase):
    """What intake writes from templates/pipeline.yaml must satisfy the contract."""

    VALUES = {
        "<profile id>": "personal-brand",
        "<BCP 47 tag>": "uk",
        "<fal | svg-only | none>": "svg-only",
        "<on | off>": "on",
        "<headless-chrome | manual>": "manual",
        "<US dollars; 0 without paid generation>": "0",
    }

    def fill_template(self):
        with open(os.path.join(SKILL, "templates", "pipeline.yaml"), encoding="utf-8") as handle:
            text = handle.read()
        for placeholder, value in self.VALUES.items():
            self.assertIn(placeholder, text)
            text = text.replace(placeholder, value)
        self.assertNotIn("<", text)
        for step in cc.STEPS[1:]:
            self.remove(step)
        self.write("pipeline.yaml", text)

    def test_filled_template_is_valid_while_intake_is_in_progress(self):
        self.fill_template()
        self.replace("00-intake/idea.md", "status: approved", "status: draft")
        report = self.assertClean()
        self.assertEqual(report.warnings, [])
        self.assertClean(step="00-intake")

    def test_closing_intake_as_the_step_protocol_describes(self):
        self.fill_template()
        version = cc.step_version(self.path("00-intake"))
        self.set_step("00-intake", "status: in-progress",
                      "status: approved\n    version: " + version)
        report = self.assertClean()
        self.assertEqual(report.warnings, [])

    def test_unfilled_template_is_rejected(self):
        with open(os.path.join(SKILL, "templates", "pipeline.yaml"), encoding="utf-8") as handle:
            self.write("pipeline.yaml", handle.read())
        self.assertError("pipeline.yaml", "'profile' is '<profile id>'")


class BrokenFiles(BrandCase):
    def test_missing_required_file(self):
        self.remove("01-strategy/icp.md")
        self.assertError("01-strategy/icp.md", "missing")

    def test_missing_step_directory(self):
        self.remove("04-design-system")
        self.assertError("04-design-system/", "missing")

    def test_missing_summary(self):
        self.remove("02-brand-platform/summary.md")
        self.assertError("02-brand-platform/summary.md", "missing")

    def test_invented_file_name(self):
        self.write("01-strategy/personas.md", "# Personas\n")
        self.assertError("01-strategy/personas.md", "not part of the contract")

    def test_missing_logo_version(self):
        self.remove("03-identity/logo/mono.svg")
        self.assertError("03-identity/logo/mono.svg", "missing")

    def test_logo_that_is_not_svg(self):
        self.write("03-identity/logo/full.svg", "PNG data")
        self.assertError("03-identity/logo/full.svg", "not an SVG")

    def test_empty_surfaces_directory(self):
        self.remove("03-identity/surfaces/site-hero.html")
        self.assertError("03-identity/surfaces/", "is empty")

    def test_missing_fonts(self):
        self.remove("03-identity/fonts")
        self.assertError("03-identity/fonts/", "missing")

    def test_invalid_tokens_json(self):
        self.write("04-design-system/tokens.json", "{ not json")
        self.assertError("04-design-system/tokens.json", "not valid JSON")

    def test_tokens_json_that_is_not_an_object(self):
        self.write("04-design-system/tokens.json", "[]")
        self.assertError("04-design-system/tokens.json", "JSON object")

    def test_empty_html(self):
        self.write("05-brand-book/index.html", "")
        self.assertError("05-brand-book/index.html", "is empty")

    def test_missing_file_reported_under_step_flag_before_approval(self):
        self.set_statuses_from("05-brand-book", "in-progress")
        self.remove("05-brand-book/index.html")
        self.assertClean()
        self.assertError("05-brand-book/index.html", "missing", step="05-brand-book")

    def test_step_flag_allows_draft(self):
        self.set_statuses_from("05-brand-book", "in-progress")
        self.replace("05-brand-book/brand-book.md", "status: approved", "status: draft")
        self.assertClean(step="05-brand-book")


class BrokenFrontmatter(BrandCase):
    FILE = "02-brand-platform/voice.md"

    def test_missing_frontmatter(self):
        self.write(self.FILE, self.read(self.FILE).split("---\n", 2)[2])
        self.assertError(self.FILE, "missing frontmatter")

    def test_unclosed_frontmatter(self):
        self.replace(self.FILE, "source: generated\n---\n", "source: generated\n")
        self.assertError(self.FILE, "not closed")

    def test_missing_field(self):
        self.replace(self.FILE, "source: generated\n", "")
        self.assertError(self.FILE, "missing key 'source'")

    def test_unknown_field(self):
        self.replace(self.FILE, "source: generated\n", "source: generated\nupdated: 2026-11-11\n")
        self.assertError(self.FILE, "unknown key 'updated'")

    def test_step_does_not_match_directory(self):
        self.replace(self.FILE, "step: 02-brand-platform", "step: brand-platform")
        self.assertError(self.FILE, "must be '02-brand-platform'")

    def test_invalid_status(self):
        self.replace(self.FILE, "status: approved", "status: done")
        self.assertError(self.FILE, "'status' is 'done'")

    def test_old_strategy_status_is_rejected(self):
        self.replace("01-strategy/icp.md", "status: approved", "status: hypothesis")
        self.assertError("01-strategy/icp.md", "'status' is 'hypothesis'")

    def test_invalid_source(self):
        self.replace(self.FILE, "source: generated", "source: owner")
        self.assertError(self.FILE, "'source' is 'owner'")

    def test_draft_in_approved_step(self):
        self.replace(self.FILE, "status: approved", "status: draft")
        self.assertError(self.FILE, "'draft' in a step that is approved")

    def test_strategy_in_progress_mixes_approved_and_draft(self):
        self.set_statuses_from("01-strategy", "in-progress")
        for step in cc.STEPS[2:]:
            self.remove(step)
        self.replace("01-strategy/messaging.md", "status: approved", "status: draft")
        self.remove("01-strategy/summary.md")
        self.assertClean()


class BrokenSections(BrandCase):
    def test_missing_section(self):
        self.replace("01-strategy/golden-circle.md", "## Why", "## Purpose")
        self.assertError("01-strategy/golden-circle.md", "missing section '## Why'")

    def test_heading_case_must_match(self):
        self.replace("01-strategy/golden-circle.md", "## Why", "## WHY")
        self.assertError("01-strategy/golden-circle.md", "missing section '## Why'")

    def test_empty_section(self):
        text = self.read("03-identity/color.md")
        start = text.index("## Accent is for")
        end = text.index("## Accent is never for")
        self.write("03-identity/color.md", text[:start] + "## Accent is for\n\n" + text[end:])
        self.assertError("03-identity/color.md", "section '## Accent is for' is empty")

    def test_heading_inside_code_block_does_not_count(self):
        self.replace("01-strategy/golden-circle.md", "## Why\n", "```\n## Why\n```\n")
        self.assertError("01-strategy/golden-circle.md", "missing section '## Why'")

    def test_summary_missing_section(self):
        self.replace("02-brand-platform/summary.md", "## Open questions\n\nNone.\n", "")
        self.assertError("02-brand-platform/summary.md", "sections must be exactly")

    def test_summary_extra_section(self):
        self.write("02-brand-platform/summary.md", self.read("02-brand-platform/summary.md") + "\n## Notes\n\nx\n")
        self.assertError("02-brand-platform/summary.md", "sections must be exactly")

    def test_summary_sections_out_of_order(self):
        self.write("02-brand-platform/summary.md",
                   "## Constraints on later steps\n\nx\n\n## Decisions\n\nx\n\n## Open questions\n\nx\n")
        self.assertError("02-brand-platform/summary.md", "sections must be exactly")

    def test_summary_empty_section(self):
        self.replace("02-brand-platform/summary.md", "None.\n", "")
        self.assertError("02-brand-platform/summary.md", "section '## Open questions' is empty")

    def test_summary_with_frontmatter(self):
        self.write("02-brand-platform/summary.md",
                   "---\nstep: 02-brand-platform\n---\n" + self.read("02-brand-platform/summary.md"))
        self.assertError("02-brand-platform/summary.md", "must not have frontmatter")


class BrokenDecisions(BrandCase):
    FILE = "03-identity/review/decisions.md"

    def test_missing_decisions_file(self):
        self.remove(self.FILE)
        self.assertError(self.FILE, "missing")

    def test_decisions_not_required_outside_choice_steps(self):
        self.assertFalse(os.path.exists(self.path("01-strategy/review")))
        self.assertClean(step="01-strategy")

    def test_open_choice_in_approved_step(self):
        self.replace(self.FILE, "Status: fixed", "Status: open")
        self.assertError(self.FILE, "still open")

    def test_invalid_choice_status(self):
        self.replace(self.FILE, "Status: fixed", "Status: done")
        self.assertError(self.FILE, "'Status' is 'done'")

    def test_missing_line(self):
        self.replace(self.FILE, "- Comment: the mark in 3 is calmer\n", "")
        self.assertError(self.FILE, "must have exactly the lines")

    def test_page_does_not_exist(self):
        self.remove("03-identity/review/logo-02.html")
        self.assertError(self.FILE, "page 'logo-02.html' does not exist")

    def test_empty_decision(self):
        self.replace(self.FILE, "- Decision: 3\n", "- Decision:\n")
        self.assertError(self.FILE, "'Decision' is empty")

    def test_heading_without_number(self):
        self.replace(self.FILE, "## 2. Color", "## Color")
        self.assertError(self.FILE, "must have the form")

    def test_numbering_gap(self):
        self.replace(self.FILE, "## 2. Color", "## 3. Color")
        self.assertError(self.FILE, "out of sequence")

    def test_no_choices_in_approved_step(self):
        self.write(self.FILE, "# Decisions\n")
        self.assertError(self.FILE, "has no choices")

    def test_open_choice_is_fine_while_in_progress(self):
        self.set_statuses_from("03-identity", "in-progress")
        self.replace(self.FILE, "Status: fixed", "Status: open")
        self.assertClean()


class BrokenPlates(BrandCase):
    GC = "01-strategy/golden-circle.md"

    def test_line_slot_over_the_word_limit(self):
        self.replace(self.GC, "We make personal computers",
                     "We make very good and very nice and very fast personal computers")
        self.assertError(self.GC, "plate slot '## What'")

    def test_line_slot_with_two_lines(self):
        self.replace(self.GC, "## What\n", "## What\n\nSomething first.\n")
        self.assertError(self.GC, "plate slot '## What' must be exactly one line")

    def test_why_must_start_with_a_belief(self):
        self.replace(self.GC, "We believe people", "People")
        self.assertError(self.GC, "must start with 'We believe' or 'I believe'")

    def test_personal_why_is_accepted(self):
        self.replace(self.GC, "We believe people", "I believe people")
        self.assertClean()

    def test_list_slot_with_too_few_items(self):
        self.replace(self.GC, "- Challenge the status quo.\n", "")
        self.assertError(self.GC, "plate slot '## How' has 2 items; must have exactly 3")

    def test_list_slot_written_as_prose(self):
        self.replace(self.GC, "- Challenge the status quo.", "Challenge the status quo.")
        self.assertError(self.GC, "plate slot '## How' must be a list")

    def test_list_item_over_the_word_limit(self):
        self.replace(self.GC, "- Challenge the status quo.",
                     "- Challenge the status quo in every single thing.")
        self.assertError(self.GC, "the limit is 6")

    def test_main_job_must_be_a_job_story(self):
        self.replace("01-strategy/icp.md", "When everyone I know", "Everyone I know")
        self.assertError("01-strategy/icp.md", "When ..., I want to ..., so I can ...")

    def test_essence_needs_two_to_four_words(self):
        self.replace("01-strategy/brand-wheel.md", "Think different.", "Different.")
        self.assertError("01-strategy/brand-wheel.md", "the minimum is 2")

    def test_objection_must_be_quoted(self):
        self.replace("01-strategy/messaging.md", '"It costs more than a PC."',
                     "It costs more than a PC.")
        self.assertError("01-strategy/messaging.md", "objection in double quotes")

    def test_brief_one_line_limit(self):
        self.replace("00-intake/brief.md", "Personal computers for people",
                     "Really very personal and friendly computers for all the people")
        self.assertError("00-intake/brief.md", "plate slot '## In one line'")

    def test_rationale_is_free_text(self):
        with open(self.path(self.GC), "a", encoding="utf-8") as handle:
            handle.write("\n## Rationale\n\nA long paragraph.\n\n- and a list\n")
        self.assertClean()

    def test_every_benchmark_in_the_plugin_is_a_valid_plate(self):
        for step, folder in (("00-intake", "intake"), ("01-strategy", "strategy")):
            for name, (_title, slots) in cc.PLATES[step].items():
                source = os.path.join(SKILL, "steps", folder, "benchmark", name)
                with open(source, encoding="utf-8") as handle:
                    lines = handle.read().splitlines()
                report = cc.Report()
                cc.check_plate(name, lines, slots, report)
                cc.check_sections(name, lines, cc.MARKDOWN[step][name][1], report)
                self.assertEqual(report.errors, [], name)


class BrokenPipeline(BrandCase):
    P = "pipeline.yaml"

    def test_missing_tool_key(self):
        self.replace(self.P, "  figma_export: off\n", "")
        self.assertError(self.P, "missing key 'tools.figma_export'")

    def test_removed_tool_key_is_unknown(self):
        self.replace(self.P, "  figma_export: off\n", "  figma_export: off\n  web_research: on\n")
        self.assertError(self.P, "unknown key 'tools.web_research'")

    def test_invalid_tool_value(self):
        self.replace(self.P, "image_generation: svg-only", "image_generation: midjourney")
        self.assertError(self.P, "'tools.image_generation' is 'midjourney'")

    def test_yaml_boolean_is_not_on(self):
        self.replace(self.P, "figma_export: off", "figma_export: false")
        self.assertError(self.P, "'tools.figma_export' is 'false'")

    def test_quoted_values_are_accepted(self):
        self.replace(self.P, "figma_export: off", 'figma_export: "off"  # quoted')
        self.assertClean()

    def test_unknown_profile(self):
        self.replace(self.P, "profile: personal-brand", "profile: nonprofit")
        self.assertError(self.P, "'profile' is 'nonprofit'")

    def test_missing_market_language(self):
        self.replace(self.P, "market_language: uk\n", "")
        self.assertError(self.P, "missing key 'market_language'")

    def test_invalid_market_language(self):
        self.replace(self.P, "market_language: uk", "market_language: Ukrainian language")
        self.assertError(self.P, "'market_language'")

    def test_order_is_accepted(self):
        self.replace(self.P, "profile:", "order: acme-shop\nprofile:")
        self.assertClean()

    def test_invalid_order(self):
        self.replace(self.P, "profile:", "order: Personal Hub\nprofile:")
        self.assertError(self.P, "'order' is 'Personal Hub'")

    def test_unknown_top_level_key(self):
        self.replace(self.P, "profile:", "name: x\nprofile:")
        self.assertError(self.P, "unknown key 'name'")

    def test_invalid_step_status(self):
        self.set_step("05-brand-book", "status: approved", "status: done")
        self.assertError(self.P, "'steps.05-brand-book.status' is 'done'")

    def test_missing_step(self):
        text = self.read(self.P)
        self.write(self.P, text[: text.index("  05-brand-book:\n")])
        self.assertError(self.P, "missing key 'steps.05-brand-book'")

    def test_unknown_step(self):
        self.write(self.P, self.read(self.P) + "  08-landing:\n    status: pending\n    spent: 0\n")
        self.assertError(self.P, "unknown key 'steps.08-landing'")

    def test_approved_step_without_version(self):
        text = self.read(self.P)
        start = text.index("    version:", text.index("  05-brand-book:\n"))
        self.write(self.P, text[:start] + text[text.index("\n", start) + 1:])
        self.assertError(self.P, "missing key 'steps.05-brand-book.version'")

    def test_malformed_version(self):
        self.set_step("00-intake", "version: ", "version: v")
        self.assertError(self.P, "'steps.00-intake.version'")

    def test_pending_step_with_version(self):
        self.set_step("05-brand-book", "status: approved", "status: pending")
        self.assertError(self.P, "'steps.05-brand-book.version' must be absent")

    def test_built_on_missing_an_earlier_step(self):
        text = self.read(self.P)
        start = text.index("      00-intake:", text.index("  05-brand-book:\n"))
        self.write(self.P, text[:start] + text[text.index("\n", start) + 1:])
        self.assertError(self.P, "missing key 'steps.05-brand-book.built_on.00-intake'")

    def test_built_on_a_later_step(self):
        self.set_step("01-strategy", "    built_on:\n",
                      "    built_on:\n      03-identity: aaaaaaaaaaaa\n")
        self.assertError(self.P, "'steps.01-strategy.built_on.03-identity' is not an earlier step")

    def test_approved_after_an_unapproved_step(self):
        self.set_step("01-strategy", "status: approved", "status: in-progress")
        self.assertError(self.P, "'steps.02-brand-platform' is approved but the earlier step "
                                 "'01-strategy' is in-progress")

    def test_missing_spent(self):
        self.set_step("02-brand-platform", "\n    spent: 0", "")
        self.assertError(self.P, "missing key 'steps.02-brand-platform.spent'")

    def test_negative_spent(self):
        self.set_step("02-brand-platform", "spent: 0", "spent: -1")
        self.assertError(self.P, "'steps.02-brand-platform.spent'")

    def test_spend_over_budget(self):
        self.set_step("04-design-system", "spent: 0", "spent: 9.00")
        self.assertError(self.P, "exceeds 'budget.limit'")

    def test_list_is_outside_the_yaml_subset(self):
        self.replace(self.P, "budget:\n  limit: 10.00", "budget:\n  - 10.00")
        self.assertError(self.P, "line 10")

    def test_flow_mapping_is_outside_the_yaml_subset(self):
        self.replace(self.P, "budget:\n  limit: 10.00", "budget: {limit: 10.00}")
        self.assertError(self.P, "flow syntax")

    def test_tab_indentation(self):
        self.replace(self.P, "  limit: 10.00", "\tlimit: 10.00")
        self.assertError(self.P, "tabs")

    def test_duplicate_key(self):
        self.replace(self.P, "profile: personal-brand", "profile: personal-brand\nprofile: b2b-saas")
        self.assertError(self.P, "duplicate key 'profile'")


class Versions(BrandCase):
    def warnings(self):
        report = self.check()
        self.assertEqual(report.errors, [])
        return report.warnings

    def test_change_after_approval_is_a_warning_not_an_error(self):
        self.replace("01-strategy/icp.md", "A household buying", "One household buying")
        warnings = self.warnings()
        self.assertEqual([path for path, _ in warnings], ["01-strategy/"])
        self.assertIn("changed since approval", warnings[0][1])

    def test_built_on_older_version(self):
        self.replace("01-strategy/icp.md", "A household buying", "One household buying")
        new = cc.step_version(self.path("01-strategy"))
        text = self.read("pipeline.yaml")
        old = text.split("  01-strategy:\n    status: approved\n    version: ")[1][:12]
        self.write("pipeline.yaml", text.replace("    version: " + old, "    version: " + new))
        warnings = self.warnings()
        self.assertEqual([path for path, _ in warnings], [s + "/" for s in cc.STEPS[2:]])
        for _, message in warnings:
            self.assertIn("built on an older version of 01-strategy", message)

    def test_review_directory_is_not_part_of_the_version(self):
        before = cc.step_version(self.path("03-identity"))
        self.write("03-identity/review/direction-02.html", "<html></html>")
        self.assertEqual(cc.step_version(self.path("03-identity")), before)
        self.assertEqual(self.warnings(), [])

    def test_summary_is_part_of_the_version(self):
        before = cc.step_version(self.path("03-identity"))
        self.replace("03-identity/summary.md", "Example decision", "Another decision")
        self.assertNotEqual(cc.step_version(self.path("03-identity")), before)

    def test_renaming_a_file_changes_the_version(self):
        before = cc.step_version(self.path("03-identity"))
        os.rename(self.path("03-identity/surfaces/site-hero.html"),
                  self.path("03-identity/surfaces/avatar.html"))
        self.assertNotEqual(cc.step_version(self.path("03-identity")), before)

    def test_no_version_warnings_for_stale_steps(self):
        self.replace("05-brand-book/brand-book.md", "Built by render_book.py", "Edited by hand")
        self.set_step("05-brand-book", "status: approved", "status: stale")
        self.assertEqual(self.warnings(), [])


class CommandLine(BrandCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, SCRIPT] + list(args), cwd=self.tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)

    def test_clean_brand_exits_zero_with_default_path(self):
        result = self.run_script("check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 error(s), 0 warning(s)", result.stdout)

    def test_errors_exit_one(self):
        self.remove("01-strategy/icp.md")
        result = self.run_script("check", self.brand)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR   01-strategy/icp.md: missing", result.stdout)

    def test_warnings_alone_exit_zero(self):
        self.replace("01-strategy/icp.md", "A household buying", "One household buying")
        result = self.run_script("check")
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARNING 01-strategy/: changed since approval", result.stdout)

    def test_step_flag_limits_the_check_to_one_step(self):
        self.remove("01-strategy/icp.md")
        self.assertEqual(self.run_script("check", "--step", "02-brand-platform").returncode, 0)
        self.assertEqual(self.run_script("check", "--step", "01-strategy").returncode, 1)

    def test_missing_brand_exits_two(self):
        self.assertEqual(self.run_script("check", "nowhere").returncode, 2)

    def test_missing_pipeline_exits_two(self):
        self.remove("pipeline.yaml")
        self.assertEqual(self.run_script("check").returncode, 2)

    def test_unknown_step_exits_two(self):
        self.assertEqual(self.run_script("check", "--step", "strategy").returncode, 2)

    def test_hash_prints_the_recorded_version(self):
        result = self.run_script("hash", "00-intake")
        self.assertEqual(result.returncode, 0)
        recorded = self.read("pipeline.yaml").split("  00-intake:\n    status: approved\n    version: ")[1][:12]
        self.assertEqual(result.stdout.strip(), recorded)

    def test_check_does_not_modify_anything(self):
        before = {s: cc.step_version(self.path(s)) for s in cc.STEPS}
        pipeline = self.read("pipeline.yaml")
        self.remove("01-strategy/icp.md")
        before["01-strategy"] = cc.step_version(self.path("01-strategy"))
        self.run_script("check")
        self.assertEqual({s: cc.step_version(self.path(s)) for s in cc.STEPS}, before)
        self.assertEqual(self.read("pipeline.yaml"), pipeline)


TOKENS = "04-design-system/tokens.json"
COMPONENTS = "04-design-system/components.md"
INTERFACE = "04-design-system/interface.md"


def hex_color(value):
    value = value.lstrip("#")
    return {"colorSpace": "srgb",
            "components": [round(int(value[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)]}


class DesignSystemPlates(BrandCase):
    STEP = "04-design-system"

    def edit_tokens(self, change, rebuild=True):
        data = json.loads(self.read(TOKENS))
        change(data)
        self.write(TOKENS, json.dumps(data, indent=2))
        if rebuild:
            self.write("04-design-system/tokens.css", cc.bt.build(data))

    def test_fixture_design_system_is_clean(self):
        report = self.assertClean(self.STEP)
        self.assertEqual(report.warnings, [])

    def test_one_session_and_its_headline(self):
        self.assertEqual(cc.DESIGN_TOOLS, ["interface.md"])
        found = [slot["name"] for _title, slots in cc.PLATES[self.STEP].values()
                 for slot in slots if slot["headline"]]
        self.assertEqual(found, ["Interface idea"])

    def test_depth_starts_with_its_kind(self):
        self.replace(INTERFACE, "Raised: soft", "Soft")
        self.assertError(INTERFACE, "start with Flat, Ruled or Raised")

    def test_density_has_its_form(self):
        self.replace(INTERFACE, "8 px unit, 44 px controls", "dense")
        self.assertError(INTERFACE, "8 px unit, 44 px controls")

    def test_never_has_exactly_three(self):
        self.replace(INTERFACE, "- A square button.\n", "")
        self.assertError(INTERFACE, "has 2 items; must have exactly 3")

    def test_a_missing_role(self):
        self.edit_tokens(lambda d: d["color"].pop("focus"))
        self.assertError(TOKENS, "missing token 'color.focus' (color)")

    def test_a_role_of_the_wrong_type(self):
        self.edit_tokens(lambda d: d["size"].update(
            {"control": {"$type": "number", "$value": 44}}), rebuild=False)
        self.assertError(TOKENS, "'size.control' is a number; it must be a dimension")

    def test_weak_pair_in_the_dark_theme(self):
        self.edit_tokens(lambda d: d["dark"]["color"].update(
            {"text-muted": {"$value": hex_color("#333333")}}))
        self.assertError(TOKENS, "color.text-muted on color.bg, dark: 1.7 to 1; it must reach "
                                 "4.5 to 1")

    def test_weak_border_of_controls(self):
        self.edit_tokens(lambda d: d["color"].update(
            {"control-border": {"$value": hex_color("#DDDDDD")}}))
        self.assertError(TOKENS, "color.control-border on color.bg, light")

    def test_translucent_role(self):
        def change(d):
            d["color"]["text"] = {"$value": dict(hex_color("#000000"), alpha=0.5)}
        self.edit_tokens(change)
        self.assertError(TOKENS, "color.text is translucent")

    def test_accent_must_be_the_identity_accent(self):
        self.edit_tokens(lambda d: d["palette"].update(
            {"bondi-blue": {"$value": hex_color("#0077AA")}}))
        self.assertError(TOKENS, "color.accent is #0077AA in the light theme; the identity "
                                 "fixed #0095B6 (accent)")

    def test_dark_background_must_be_the_identity_one(self):
        self.edit_tokens(lambda d: d["dark"]["color"].update(
            {"bg": {"$value": hex_color("#111111")}}))
        self.assertError(TOKENS, "color.bg is #111111 in the dark theme")

    def test_headline_size_is_the_identity_one(self):
        self.edit_tokens(lambda d: d["narrow"]["type"]["headline"]["$value"].update(
            {"fontSize": {"value": 36, "unit": "px"}}))
        self.assertError(TOKENS, "type.headline is 36 px at 390; the identity fixed 40 px")

    def test_family_is_the_identity_one(self):
        self.edit_tokens(lambda d: d["font"]["text"].update({"$value": ["Inter", "sans-serif"]}))
        self.assertError(TOKENS, "font.text starts with 'Inter'; the identity fixed "
                                 "'Apple Garamond'")

    def test_control_too_small_at_390(self):
        self.edit_tokens(lambda d: d["narrow"]["size"].update(
            {"control": {"$value": {"value": 2, "unit": "rem"}}}))
        self.edit_tokens(lambda d: d["narrow"]["size"].update(
            {"control": {"$value": {"value": 36, "unit": "px"}}}))
        self.assertError(TOKENS, "size.control is 36 px at 390")

    def test_tokens_css_out_of_date(self):
        self.edit_tokens(lambda d: d["space"].update(
            {"m": {"$value": {"value": 18, "unit": "px"}}}), rebuild=False)
        self.assertError("04-design-system/tokens.css", "is out of date")

    def test_a_component_is_missing(self):
        text = self.read(COMPONENTS)
        start = text.index("### Switch")
        end = text.index("### Badge")
        self.write(COMPONENTS, text[:start] + text[end:])
        self.assertError(COMPONENTS, "missing '### Switch' under '## Atoms'")

    def test_component_lines_keep_their_order(self):
        text = self.read(COMPONENTS)
        start = text.index("### Badge")
        block = text[start:text.index("### Avatar")]
        swapped = block.replace("- For:", "- Tmp:").replace("- States:", "- For:").replace(
            "- Tmp:", "- States:")
        self.write(COMPONENTS, text.replace(block, swapped))
        self.assertError(COMPONENTS, "'### Badge' must have exactly the lines For, States, "
                                     "Tokens, At 390, Accessibility")

    def test_a_component_uses_a_primitive(self):
        self.replace(COMPONENTS, "- Tokens: color.border, border.width",
                     "- Tokens: palette.black, border.width")
        self.assertError(COMPONENTS, "'### Divider': 'palette.black' is a primitive")

    def test_a_component_names_an_unknown_token(self):
        self.replace(COMPONENTS, "- Tokens: color.border, border.width",
                     "- Tokens: color.hairline")
        self.assertError(COMPONENTS, "there is no token 'color.hairline'")

    def test_a_page_file_is_missing(self):
        self.remove("04-design-system/reference/pages/sign-up.html")
        self.assertError(COMPONENTS, "'### Sign-up': the page 'reference/pages/sign-up.html' "
                                     "does not exist")
        self.assertError("04-design-system/reference/pages/sign-up.html", "missing")

    def test_old_sections_are_gone(self):
        self.assertEqual(cc.MARKDOWN[self.STEP]["components.md"][1],
                         ["Atoms", "Molecules", "Organisms", "Pages"])

    def test_a_kept_system_needs_no_interface_choice(self):
        self.replace(INTERFACE, "source: generated", "source: provided")
        self.write("04-design-system/review/decisions.md",
                   "# Decisions\n\n## 1. System\n\n- Page: system-01.html\n- Decision: yes\n"
                   "- Comment:\n- Status: fixed\n")
        self.assertClean(self.STEP)

    def test_tokens_command(self):
        out = subprocess.run([sys.executable, SCRIPT, "tokens", self.path(TOKENS)],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("- color.on-accent on color.accent, light: 6 to 1", out.stdout)
        self.assertEqual(len(out.stdout.splitlines()), 2 * len(cc.TOKEN_PAIRS))
        self.edit_tokens(lambda d: (d["color"].pop("link"), d["dark"]["color"].pop("link")))
        out = subprocess.run([sys.executable, SCRIPT, "tokens", self.path(TOKENS)],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("missing token 'color.link'", out.stderr)


class BrandBookContract(BrandCase):
    STEP = "05-brand-book"

    def test_fixture_brand_book_is_clean(self):
        self.assertEqual(self.check(self.STEP).errors, [])

    def test_the_five_sections(self):
        self.assertEqual(cc.MARKDOWN[self.STEP]["brand-book.md"][1],
                         ["Strategy", "Brand platform", "Identity", "Design system",
                          "How to use this"])
        self.replace("05-brand-book/brand-book.md", "## Brand platform", "## Platform")
        self.assertError("05-brand-book/brand-book.md", "missing section '## Brand platform'")

    def test_the_pdf_may_be_absent_but_never_empty(self):
        self.assertFalse(os.path.exists(self.path("05-brand-book/brand-book.pdf")))
        self.assertEqual(self.check(self.STEP).errors, [])
        self.write("05-brand-book/brand-book.pdf", "")
        self.assertError("05-brand-book/brand-book.pdf", "is empty")

class MovedPlugin(unittest.TestCase):
    def test_fixture_brand_still_valid(self):
        """A brand directory made by 1.0.0 passes the check of the skill in its new place."""
        done = subprocess.run([sys.executable, SCRIPT, "check", VALID], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
