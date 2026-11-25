"""Tests for scripts/owner.py: the owner's answers as files (contract, section 9)."""

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
FIXTURE = os.path.join(ROOT, "tests", "marketing", "brand", "fixtures", "valid", "brand")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, "scripts", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ow = load("owner")
cc = load("check_contract")


def run(*args, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    old = None
    if stdin is not None:
        import sys
        old, sys.stdin = sys.stdin, io.StringIO(stdin)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = ow.main(list(args))
    finally:
        if old is not None:
            import sys
            sys.stdin = old
    return code, out.getvalue(), err.getvalue()


def choice(ident="02-brand-platform.mood.choice-01", **extra):
    question = {
        "format": "brand-question/1",
        "id": ident,
        "step": ident.split(".")[0],
        "kind": "choice",
        "asked": "Which territory?",
        "options": [
            {"id": "1", "label": "Quiet workshop", "means": "paper, daylight"},
            {"id": "2", "label": "Night studio", "means": "dark ground, warm light"},
            {"id": "3", "label": "Open field", "means": "air, pale colors"},
        ],
        "recommended": "2",
    }
    question.update(extra)
    return question


def text(ident="00-intake.kickoff.story", **extra):
    question = {"format": "brand-question/1", "id": ident, "step": ident.split(".")[0],
                "kind": "text", "asked": "Tell us about the business."}
    question.update(extra)
    return question


class Owner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.brand = os.path.join(self.tmp, "studio", "orders", "acme")
        shutil.copytree(FIXTURE, self.brand)

    def write(self, name, data):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        return path

    def ask(self, question):
        return run("ask", self.brand, self.write("q.json", question))

    def files(self, kind):
        folder = os.path.join(self.brand, "owner", kind)
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


class AskAndAnswer(Owner):
    def test_an_unanswered_question_waits(self):
        code, out, _err = self.ask(choice(page="02-brand-platform/review/moodboard-01.html"))
        self.assertEqual(code, 3)
        self.assertIn("WAITING 02-brand-platform.mood.choice-01: Which territory?", out)
        self.assertIn("page: 02-brand-platform/review/moodboard-01.html", out)
        self.assertEqual(self.files("questions"), ["02-brand-platform.mood.choice-01.json"])
        self.assertEqual(self.files("answers"), [])

    def test_answer_then_get(self):
        self.ask(choice())
        code, out, err = run("answer", self.brand, "02-brand-platform.mood.choice-01",
                             "--choice", "2", "--comment", "with the colors from 3",
                             "--by", "orchestrator")
        self.assertEqual(code, 0, err)
        code, out, _err = run("get", self.brand, "02-brand-platform.mood.choice-01")
        self.assertEqual(code, 0)
        answer = json.loads(out)
        self.assertEqual(answer, {"format": "brand-answer/1",
                                  "id": "02-brand-platform.mood.choice-01", "choice": "2",
                                  "comment": "with the colors from 3", "by": "orchestrator"})

    def test_an_answer_placed_before_the_question(self):
        code, _out, err = run("answer", self.brand, "00-intake.kickoff.story",
                              "--text", "A studio for slow software.", "--by", "order-file")
        self.assertEqual(code, 0, err)
        code, out, _err = self.ask(text())
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["text"], "A studio for slow software.")

    def test_an_answer_placed_before_that_does_not_fit_stops_the_step(self):
        run("answer", self.brand, "02-brand-platform.mood.choice-01", "--choice", "7",
            "--by", "order-file")
        code, _out, err = self.ask(choice())
        self.assertEqual(code, 1)
        self.assertIn("'7' is not an option", err)

    def test_an_answer_is_never_replaced(self):
        self.ask(choice())
        run("answer", self.brand, "02-brand-platform.mood.choice-01", "--choice", "1",
            "--by", "owner")
        code, _out, err = run("answer", self.brand, "02-brand-platform.mood.choice-01",
                              "--choice", "3", "--by", "owner")
        self.assertEqual(code, 1)
        self.assertIn("never replaced", err)
        self.assertEqual(ow.get(self.brand, "02-brand-platform.mood.choice-01")["choice"], "1")

    def test_the_same_question_again_is_accepted_another_is_not(self):
        self.ask(choice())
        self.assertEqual(self.ask(choice())[0], 3)
        code, _out, err = self.ask(choice(asked="Which one, really?"))
        self.assertEqual(code, 1)
        self.assertIn("new cycle is a new id", err)

    def test_question_from_standard_input(self):
        code, out, _err = run("ask", self.brand, "-", stdin=json.dumps(text()))
        self.assertEqual(code, 3)
        self.assertIn("WAITING 00-intake.kickoff.story", out)

    def test_pending_lists_only_what_waits(self):
        self.ask(choice())
        self.ask(text())
        run("answer", self.brand, "00-intake.kickoff.story", "--text", "x", "--by", "owner")
        code, out, _err = run("pending", self.brand)
        self.assertEqual(code, 3)
        self.assertEqual(out.strip().splitlines(),
                         ["WAITING 02-brand-platform.mood.choice-01: Which territory?"])
        run("answer", self.brand, "02-brand-platform.mood.choice-01", "--choice", "1",
            "--by", "owner")
        code, out, _err = run("pending", self.brand)
        self.assertEqual(code, 0)
        self.assertIn("nothing is waiting", out)

    def test_get_before_the_question_is_asked(self):
        code, out, _err = run("get", self.brand, "00-intake.kickoff.profile")
        self.assertEqual(code, 3)
        self.assertIn("not asked yet", out)

    def test_the_brand_directory_must_exist(self):
        code, _out, err = run("pending", os.path.join(self.tmp, "nowhere"))
        self.assertEqual(code, 2)
        self.assertIn("create the brand directory first", err)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "nowhere")))

    def test_a_new_order_without_a_pipeline(self):
        order = os.path.join(self.tmp, "studio", "orders", "new")
        os.makedirs(order)
        code, _out, err = run("answer", order, "00-intake.kickoff.story", "--text", "x",
                              "--by", "order-file")
        self.assertEqual(code, 0, err)
        code, out, _err = run("ask", order, "-", stdin=json.dumps(text()))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["text"], "x")

    def test_the_answers_do_not_change_any_step_version(self):
        before = {s: cc.step_version(os.path.join(self.brand, s)) for s in cc.STEPS}
        self.ask(choice())
        run("answer", self.brand, "02-brand-platform.mood.choice-01", "--choice", "1",
            "--by", "owner")
        after = {s: cc.step_version(os.path.join(self.brand, s)) for s in cc.STEPS}
        self.assertEqual(before, after)
        report = cc.check(self.brand)
        self.assertEqual((report.errors, report.warnings), ([], []))


class Kinds(Owner):
    def answer(self, question, *args):
        self.ask(question)
        return run("answer", self.brand, question["id"], *args, "--by", "owner")

    def test_approve_takes_yes_or_no(self):
        question = {"format": "brand-question/1", "id": "00-intake.step.approve",
                    "step": "00-intake", "kind": "approve", "asked": "Close the kickoff?"}
        self.assertEqual(self.answer(question, "--choice", "maybe")[0], 1)
        code, _out, err = run("answer", self.brand, question["id"], "--choice", "no",
                              "--comment", "the ambition is too small", "--by", "owner")
        self.assertEqual(code, 0, err)

    def test_spend_takes_yes_or_no(self):
        question = {"format": "brand-question/1", "id": "02-brand-platform.mood.spend-01",
                    "step": "02-brand-platform", "kind": "spend",
                    "asked": "Generate 4 images for $0.12?"}
        self.assertEqual(self.answer(question, "--text", "sure")[0], 1)
        self.assertEqual(run("answer", self.brand, question["id"], "--choice", "yes",
                             "--by", "owner")[0], 0)

    def test_text_takes_text(self):
        self.assertEqual(self.answer(text(), "--choice", "1")[0], 1)
        self.assertEqual(run("answer", self.brand, "00-intake.kickoff.story", "--text", "x",
                             "--by", "owner")[0], 0)

    def test_own_words_only_when_free(self):
        code, _out, err = self.answer(choice(), "--text", "something else")
        self.assertEqual(code, 1)
        self.assertIn("not the owner's own words", err)
        free = choice("01-strategy.golden-circle.why", free=True)
        self.assertEqual(self.answer(free, "--text", "We believe ...")[0], 0)


class InvalidFiles(Owner):
    def assertInvalid(self, question, message):
        code, _out, err = self.ask(question)
        self.assertEqual(code, 1, err)
        self.assertIn(message, err)
        self.assertEqual(self.files("questions"), [])

    def test_bad_id(self):
        self.assertInvalid(choice("mood-choice"), "is not an id")
        self.assertInvalid(choice("09-launch.mood.choice"), "is not an id")
        self.assertInvalid(choice("02-brand-platform.Mood.choice"), "is not an id")

    def test_step_must_match_the_id(self):
        self.assertInvalid(choice(step="03-identity"), "'step' must be '02-brand-platform'")

    def test_unknown_key(self):
        self.assertInvalid(choice(answer="2"), "unknown key 'answer'")

    def test_a_choice_needs_options(self):
        self.assertInvalid(choice(options=[{"id": "1", "label": "a", "means": "b"}]),
                           "two or more 'options'")

    def test_an_option_needs_what_it_means(self):
        self.assertInvalid(choice(options=[{"id": "1", "label": "a"},
                                           {"id": "2", "label": "b", "means": "c"}]),
                           "missing 'means'")

    def test_duplicate_option(self):
        self.assertInvalid(choice(options=[{"id": "1", "label": "a", "means": "b"},
                                           {"id": "1", "label": "c", "means": "d"}]),
                           "used twice")

    def test_recommended_must_be_an_option(self):
        self.assertInvalid(choice(recommended="9"), "not an option")

    def test_options_belong_only_to_a_choice(self):
        self.assertInvalid(text(options=choice()["options"]), "belongs only to a choice")

    def test_the_page_must_exist_inside_the_brand_directory(self):
        self.assertInvalid(choice(page="02-brand-platform/review/nothing.html"), "does not exist")
        self.assertInvalid(choice(page="../outside.html"), "inside the brand directory")
        self.assertInvalid(choice(page="/etc/hosts"), "inside the brand directory")

    def test_an_answer_needs_who_gave_it(self):
        self.ask(text())
        code, _out, err = run("answer", self.brand, "00-intake.kickoff.story", "--text", "x",
                              "--by", " ")
        self.assertEqual(code, 1)
        self.assertIn("'by'", err)

    def test_a_hand_written_answer_file_is_checked(self):
        self.ask(choice())
        path = os.path.join(self.brand, "owner", "answers",
                            "02-brand-platform.mood.choice-01.json")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"format": "brand-answer/1", "id": "02-brand-platform.mood.choice-01",
                       "choice": "2"}, handle)
        code, _out, err = run("get", self.brand, "02-brand-platform.mood.choice-01")
        self.assertEqual(code, 1)
        self.assertIn("missing 'by'", err)


if __name__ == "__main__":
    unittest.main()
