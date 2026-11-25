"""Tests for scripts/render_plates.py."""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
VALID = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand")

sys.path.insert(0, os.path.join(SKILL, "scripts"))
_spec = importlib.util.spec_from_file_location(
    "render_plates", os.path.join(SKILL, "scripts", "render_plates.py"))
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)
cc = rp.cc


class RenderPlates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.brand = os.path.join(self.tmp, "brand")
        shutil.copytree(VALID, self.brand)

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_renders_every_plate_the_one_page_and_the_map(self):
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        expected = (["brief"] + [name[:-3] for name in cc.STRATEGY_TOOLS] + ["strategy"]
                    + ["archetype", "voice", "mood", "platform"]
                    + ["logo", "color", "typography", "motto", "identity", "interface", "map"])
        self.assertEqual(list(pages), expected)
        for path in pages.values():
            self.assertTrue(os.path.isfile(path), path)

    def test_plate_pages_live_in_review_and_keep_the_step_version(self):
        before = cc.step_version(os.path.join(self.brand, "01-strategy"))
        pages, _ = rp.render(self.brand)
        self.assertEqual(os.path.dirname(pages["golden-circle"]),
                         os.path.join(self.brand, "01-strategy", "review"))
        self.assertEqual(cc.step_version(os.path.join(self.brand, "01-strategy")), before)
        self.assertEqual(cc.check(self.brand).errors, [])
        self.assertEqual(cc.check(self.brand).warnings, [])

    def test_page_holds_the_slots_and_not_the_rationale(self):
        path = os.path.join(self.brand, "01-strategy", "golden-circle.md")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n## Rationale\n\nSecret working notes.\n")
        pages, _ = rp.render(self.brand)
        text = self.read(pages["golden-circle"])
        self.assertIn("We believe people with passion", text)
        self.assertIn("Challenge the status quo.", text)
        self.assertNotIn("Secret working notes", text)
        self.assertNotIn("Steve Jobs", text)

    def test_pages_are_self_contained_and_escaped(self):
        path = os.path.join(self.brand, "00-intake", "brief.md")
        text = self.read(path).replace("\nApple\n", "\nA <b>& Co\n", 1)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        pages, _ = rp.render(self.brand)
        for page in pages.values():
            content = self.read(page)
            self.assertNotIn("http://", content)
            self.assertNotIn("https://", content)
            self.assertNotIn("<script", content)
        self.assertIn("A &lt;b&gt;&amp; Co", self.read(pages["map"]))

    def test_one_page_waits_for_all_six_headlines(self):
        os.remove(os.path.join(self.brand, "01-strategy", "messaging.md"))
        pages, _ = rp.render(self.brand)
        self.assertNotIn("strategy", pages)
        self.assertNotIn("messaging", pages)
        self.assertIn("map", pages)

    def test_draft_is_marked_and_shown_as_unfinished_on_the_map(self):
        path = os.path.join(self.brand, "01-strategy", "icp.md")
        text = self.read(path).replace("status: approved", "status: draft")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        pages, _ = rp.render(self.brand)
        self.assertIn('<span class="status">draft</span>', self.read(pages["icp"]))
        self.assertIn('<li class="draft"><a href="#icp">', self.read(pages["map"]))

    def test_malformed_plate_is_skipped_and_reported(self):
        path = os.path.join(self.brand, "01-strategy", "golden-circle.md")
        text = self.read(path).replace("We believe people", "People")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        pages, skipped = rp.render(self.brand)
        self.assertNotIn("golden-circle", pages)
        self.assertEqual(len(skipped), 1)
        self.assertIn("01-strategy/golden-circle.md", skipped[0])

    def test_theme_is_appended(self):
        pages, _ = rp.render(self.brand, theme=":root{--accent:#c00}")
        self.assertIn(":root{--accent:#c00}</style>", self.read(pages["map"]))

    def test_nothing_to_render(self):
        for step in rp.PLATE_STEPS:
            shutil.rmtree(os.path.join(self.brand, step))
        self.assertEqual(rp.main([self.brand]), 1)

    # The brand platform.

    PLATFORM = "02-brand-platform"

    def edit(self, relative, old, new):
        path = os.path.join(self.brand, *relative.split("/"))
        text = self.read(path)
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new, 1))

    def write_name(self, name):
        path = os.path.join(self.brand, self.PLATFORM, "name.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("---\nstep: 02-brand-platform\nstatus: approved\nsource: generated\n"
                         "---\n\n# Name\n\n## Name\n\n%s\n\n## Domain\n\nexample.com: "
                         "likely free; confirm with a registrar\n\n## What it says\n\n"
                         "The ground everything else is built on.\n" % name)
        self.edit("00-intake/brief.md", "\nApple\n", "\n%s\n" % name)

    def test_platform_pages_are_rendered_in_review(self):
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        for key in ("archetype", "voice", "mood", "platform"):
            self.assertEqual(os.path.dirname(pages[key]),
                             os.path.join(self.brand, self.PLATFORM, "review"))
        self.assertNotIn("name", pages)
        self.assertEqual(list(pages)[-1], "map")

    def test_rendering_keeps_the_platform_version(self):
        before = cc.step_version(os.path.join(self.brand, self.PLATFORM))
        rp.render(self.brand)
        self.assertEqual(cc.step_version(os.path.join(self.brand, self.PLATFORM)), before)

    def test_wheel_marks_the_two_archetypes(self):
        text = self.read(rp.render(self.brand)[0]["archetype"])
        self.assertEqual(text.count('class="segment'), 12)
        self.assertRegex(text, r'<g class="segment primary">(?:(?!</g>).)*Outlaw')
        self.assertRegex(text, r'<g class="segment secondary">(?:(?!</g>).)*Creator')
        for name in cc.ARCHETYPES:
            self.assertIn(">%s<" % name, text)

    def test_voice_shows_four_scales_and_both_columns(self):
        text = self.read(rp.render(self.brand)[0]["voice"])
        self.assertEqual(text.count('class="scale"'), 4)
        self.assertIn("left:75%", text)   # 4 of 5
        self.assertIn("left:50%", text)   # 3 of 5
        self.assertIn("Chic. Not geek.", text)
        self.assertIn("Compare our specifications.", text)
        self.assertIn("Matter-of-fact", text)

    def test_platform_page_takes_the_name_from_the_brief(self):
        text = self.read(rp.render(self.brand)[0]["platform"])
        for line in ("The rebel who builds tools for people who make things.",
                     "We sound like a friend who knows computers, never like a manual.",
                     ">Apple<", "Candy and glass"):
            self.assertIn(line, text)
        self.assertIn("../moodboard/reference-01.png", text)
        self.assertIn("the translucent color you can see into", text)

    def test_mood_page_shows_the_board(self):
        text = self.read(rp.render(self.brand)[0]["mood"])
        self.assertIn("../moodboard/reference-01.png", text)
        self.assertIn("Beige boxes", text)

    def test_map_reaches_the_board_from_the_brand_root(self):
        text = self.read(rp.render(self.brand)[0]["map"])
        self.assertIn("02-brand-platform/moodboard/reference-01.png", text)
        self.assertNotIn("../moodboard", text)
        self.assertIn('<a href="#archetype">', text)
        self.assertIn('id="platform"', text)

    def test_name_plate_is_rendered_and_leads_the_platform_page(self):
        self.write_name("Ґрунт")
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        self.assertIn("Ґрунт", self.read(pages["name"]))
        self.assertIn(">Ґрунт<", self.read(pages["platform"]))
        self.assertLess(list(pages).index("voice"), list(pages).index("name"))
        self.assertLess(list(pages).index("name"), list(pages).index("mood"))

    def test_name_is_escaped(self):
        self.write_name("A <b>& Co")
        pages, _ = rp.render(self.brand)
        self.assertIn("A &lt;b&gt;&amp; Co", self.read(pages["name"]))
        self.assertNotIn("A <b>& Co", self.read(pages["platform"]))

    def test_platform_page_waits_for_the_three_required_plates(self):
        os.remove(os.path.join(self.brand, self.PLATFORM, "mood.md"))
        pages, _ = rp.render(self.brand)
        self.assertNotIn("platform", pages)
        self.assertIn("archetype", pages)

    def test_broken_board_is_reported_and_the_lines_still_render(self):
        os.remove(os.path.join(self.brand, self.PLATFORM, "moodboard", "index.md"))
        pages, skipped = rp.render(self.brand)
        self.assertIn("platform", pages)
        self.assertIn("Candy and glass", self.read(pages["platform"]))
        self.assertEqual(len(skipped), 1)
        self.assertIn("moodboard", skipped[0])

    def test_board_with_a_missing_image_is_reported(self):
        os.remove(os.path.join(self.brand, self.PLATFORM, "moodboard", "reference-01.png"))
        pages, skipped = rp.render(self.brand)
        self.assertIn("mood", pages)
        self.assertTrue(any("reference-01.png" in message for message in skipped))

    def test_short_mood_session_renders(self):
        self.edit("02-brand-platform/mood.md", "source: generated", "source: provided")
        os.remove(os.path.join(self.brand, self.PLATFORM, "review", "decisions.md"))
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        self.assertIn("platform", pages)

    def test_rationale_never_reaches_a_platform_page(self):
        path = os.path.join(self.brand, self.PLATFORM, "mood.md")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\nFirst three seconds: curiosity.\n")
        pages, _ = rp.render(self.brand)
        for key in ("mood", "platform", "map"):
            self.assertNotIn("First three seconds", self.read(pages[key]))

    def test_five_lines_render_in_every_list(self):
        self.edit("02-brand-platform/archetype.md", "- Confident, but not loud: says a thing once.\n",
                  "- Confident, but not loud: says a thing once.\n"
                  "- Warm, but not soft: stays on the user's side.\n")
        self.edit("02-brand-platform/mood.md", "- One object alone on white\n",
                  "- One object alone on white\n- Daylight\n")
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        self.assertIn("Warm, but not soft", self.read(pages["archetype"]))
        self.assertIn("Daylight", self.read(pages["mood"]))

    def test_open_platform(self):
        opened = []
        original, rp.webbrowser.open = rp.webbrowser.open, opened.append
        self.addCleanup(setattr, rp.webbrowser, "open", original)
        self.assertEqual(rp.main([self.brand, "--open", "platform"]), 0)
        self.assertTrue(opened[0].endswith("02-brand-platform/review/platform.html"))

    # The identity.

    IDENTITY = "03-identity"

    def set_identity_status(self, status):
        path = os.path.join(self.brand, "pipeline.yaml")
        text = self.read(path)
        start = text.index("  03-identity:\n")
        end = text.index("  04-design-system:\n")
        block = text[start:end].replace("status: approved", "status: %s" % status)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text[:start] + block + text[end:])

    def test_identity_pages_are_rendered_in_review(self):
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        review = os.path.join(self.brand, self.IDENTITY, "review")
        for key in ("logo", "color", "typography", "motto", "identity"):
            self.assertEqual(pages[key], os.path.join(review, key + ".html"))

    def test_rendering_keeps_the_identity_version(self):
        before = cc.step_version(os.path.join(self.brand, self.IDENTITY))
        rp.render(self.brand)
        self.assertEqual(cc.step_version(os.path.join(self.brand, self.IDENTITY)), before)
        report = cc.check(self.brand)
        self.assertEqual((report.errors, report.warnings), ([], []))

    def test_logo_page_shows_the_sheet(self):
        pages, _ = rp.render(self.brand)
        text = self.read(pages["logo"])
        for name in ("full.svg", "dark.svg", "mark.svg"):
            self.assertIn('src="../logo/%s"' % name, text)
        for size in (24, 32, 48):
            self.assertIn("height:%dpx" % size, text)
        self.assertIn("The same apple, without the stripes", text)

    def test_color_page_has_one_swatch_per_palette_line(self):
        pages, _ = rp.render(self.brand)
        text = self.read(pages["color"])
        self.assertEqual(text.count('<i style="background:#'), 3)
        self.assertIn('<i style="background:#0095B6"></i><b>Bondi Blue</b>', text)
        self.assertIn("<b>Bondi Blue on White</b> 3.5 to 1, large text only", text)

    def test_six_palette_lines_render(self):
        self.edit("03-identity/color.md", "- Bondi Blue - #0095B6 - accent",
                  "- Bondi Blue - #0095B6 - accent\n- Grape - #663399 - secondary")
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        self.assertEqual(self.read(pages["color"]).count('<i style="background:#'), 4)

    def test_typography_page_sets_the_specimen_in_the_family(self):
        pages, _ = rp.render(self.brand)
        text = self.read(pages["typography"])
        self.assertIn("font-family:'Apple Garamond',var(--display)", text)
        self.assertIn('href="../../03-identity/fonts/fonts.css"', text)

    def test_family_name_cannot_break_out_of_the_style(self):
        self.edit("03-identity/typography.md", "Apple Garamond - one light weight",
                  "Evil';}</style><b>x - one light weight")
        pages, _ = rp.render(self.brand)
        text = self.read(pages["typography"])
        self.assertNotIn("<b>x", text)
        self.assertNotIn("Evil';", text)
        self.assertIn("Evil&#x27;;}&lt;/style&gt;&lt;b&gt;x", text)

    def test_motto_in_another_script_is_whole_and_escaped(self):
        self.edit("03-identity/motto.md", "Think different.", "Думай <інакше> & роби.")
        pages, _ = rp.render(self.brand)
        for key in ("motto", "identity", "map"):
            text = self.read(pages[key])
            self.assertIn("Думай &lt;інакше&gt; &amp; роби.", text, key)
            self.assertNotIn("<інакше>", text, key)

    def test_motto_page_without_rejected(self):
        path = os.path.join(self.brand, self.IDENTITY, "motto.md")
        text = self.read(path)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text[:text.index("## Rejected")] + text[text.index("## Rationale"):])
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        self.assertNotIn("Rejected", self.read(pages["motto"]))

    def test_identity_page_waits_for_the_four_plates(self):
        os.remove(os.path.join(self.brand, self.IDENTITY, "motto.md"))
        pages, _ = rp.render(self.brand)
        self.assertNotIn("identity", pages)
        self.assertIn("logo", pages)

    def test_identity_page_holds_the_four_lines_and_the_surfaces(self):
        pages, _ = rp.render(self.brand)
        text = self.read(pages["identity"])
        for line in ("The same apple, without the stripes", "White, and one color you can see",
                     "A bookish serif", "Think different."):
            self.assertIn(line, text)
        self.assertIn('src="../logo/full.svg"', text)
        self.assertIn('<iframe src="../surfaces/site-hero.html"', text)

    def test_map_reaches_the_identity_from_the_brand_root(self):
        pages, _ = rp.render(self.brand)
        text = self.read(pages["map"])
        self.assertIn('id="identity"', text)
        self.assertIn('src="03-identity/logo/full.svg"', text)
        self.assertIn('<iframe src="03-identity/surfaces/site-hero.html"', text)
        self.assertIn('href="03-identity/fonts/fonts.css"', text)
        self.assertNotIn('"../logo/', text)

    def test_approved_identity_styles_the_earlier_pages(self):
        pages, _ = rp.render(self.brand)
        text = self.read(pages["golden-circle"])
        self.assertIn("--paper:#FFFFFF;--ink:#000000;--accent:#0095B6", text)
        self.assertIn("--display:'Apple Garamond',", text)
        self.assertIn('href="../../03-identity/fonts/fonts.css"', text)
        self.assertIn('<img src="../../03-identity/logo/full.svg" alt="Apple">', text)
        self.assertIn('srcset="../../03-identity/logo/dark.svg"', text)
        self.assertIn("prefers-color-scheme:dark){:root{--paper:#000000;--ink:#FFFFFF}}", text)

    def test_identity_in_progress_leaves_the_house_style(self):
        self.set_identity_status("in-progress")
        pages, skipped = rp.render(self.brand)
        self.assertEqual(skipped, [])
        text = self.read(pages["golden-circle"])
        self.assertNotIn("#0095B6", text)
        self.assertNotIn("logo/full.svg", text)
        self.assertIn("<h1>Apple</h1>", text)
        self.assertNotIn("#0095B6;--on-accent", self.read(pages["color"]))
        for key in ("motto", "identity"):  # the house style has no dark side
            self.assertNotIn("prefers-color-scheme", self.read(pages[key]))
        self.assertIn("logo/full.svg", self.read(pages["identity"]))
        self.assertNotIn("logo/full.svg", self.read(pages["motto"]))  # the motto stands alone

    def test_text_on_the_accent_is_the_readable_one(self):
        self.assertEqual(rp.readable_on("#FFEE00", "#FFFFFF", "#000000"), "#000000")
        self.assertEqual(rp.readable_on("#002244", "#FFFFFF", "#000000"), "#FFFFFF")

    def test_missing_fonts_and_logo_are_reported_and_the_pages_still_render(self):
        os.remove(os.path.join(self.brand, self.IDENTITY, "fonts", "fonts.css"))
        os.remove(os.path.join(self.brand, self.IDENTITY, "logo", "dark.svg"))
        pages, skipped = rp.render(self.brand)
        self.assertTrue(any("fonts/fonts.css" in message for message in skipped), skipped)
        self.assertTrue(any("logo" in message for message in skipped), skipped)
        text = self.read(pages["golden-circle"])
        self.assertIn("--accent:#0095B6", text)
        self.assertNotIn("fonts.css", text)
        self.assertIn("<h1>Apple</h1>", text)
        self.assertNotIn("<img", self.read(pages["logo"]))
        self.assertNotIn("<img", self.read(pages["motto"]))

    def test_broken_palette_is_reported_and_the_house_colors_stay(self):
        self.edit("03-identity/color.md", "- Bondi Blue - #0095B6 - accent",
                  "- Bondi Blue - #0095B6 - links")
        pages, skipped = rp.render(self.brand)
        self.assertTrue(any("colors are not applied" in message for message in skipped), skipped)
        self.assertNotIn("--accent:#0095B6", self.read(pages["golden-circle"]))

    def test_rationale_never_reaches_an_identity_page(self):
        pages, _ = rp.render(self.brand)
        for key in ("logo", "color", "typography", "motto", "identity", "map"):
            self.assertNotIn("Example working notes", self.read(pages[key]), key)

    def test_identity_pages_load_nothing_from_the_network(self):
        pages, _ = rp.render(self.brand)
        for key in ("logo", "color", "typography", "motto", "identity", "map"):
            text = self.read(pages[key])
            for banned in ("http://", "https://", "<script"):
                self.assertNotIn(banned, text, key)

    def test_open_identity(self):
        opened = []
        original, rp.webbrowser.open = rp.webbrowser.open, opened.append
        self.addCleanup(setattr, rp.webbrowser, "open", original)
        self.assertEqual(rp.main([self.brand, "--open", "identity"]), 0)
        self.assertTrue(opened[0].endswith("03-identity/review/identity.html"))

    def test_missing_brand_exits_two(self):
        self.assertEqual(rp.main([os.path.join(self.tmp, "nowhere")]), 2)


    def test_interface_plate_shows_the_sheet_and_the_example_pages(self):
        pages, _ = rp.render(self.brand)
        page = self.read(pages["interface"])
        self.assertEqual(os.path.dirname(pages["interface"]),
                         os.path.join(self.brand, "04-design-system", "review"))
        self.assertIn('<iframe src="../reference/sheet.html"', page)
        for name in ("landing", "sign-in", "sign-up"):
            self.assertIn('src="../reference/pages/%s.html"' % name, page)
        self.assertIn('href="../reference/index.html"', page)
        self.assertIn("Controls you want to touch", page)
        self.assertNotIn("Fixture: the Aqua interface", page)
        self.assertNotIn("<script", page)

    def test_map_reaches_the_design_system_from_the_brand_root(self):
        pages, _ = rp.render(self.brand)
        page = self.read(pages["map"])
        self.assertIn('id="interface"', page)
        self.assertIn('src="04-design-system/reference/sheet.html"', page)
        self.assertIn('href="04-design-system/reference/index.html"', page)

    def test_interface_plate_waits_for_the_built_system(self):
        shutil.rmtree(os.path.join(self.brand, "04-design-system", "reference"))
        pages, _ = rp.render(self.brand)
        page = self.read(pages["interface"])
        self.assertNotIn("<iframe", page)
        self.assertIn("Controls you want to touch", page)

    def test_rendering_keeps_the_design_system_version(self):
        before = cc.step_version(os.path.join(self.brand, "04-design-system"))
        rp.render(self.brand)
        self.assertEqual(cc.step_version(os.path.join(self.brand, "04-design-system")), before)

if __name__ == "__main__":
    unittest.main()
