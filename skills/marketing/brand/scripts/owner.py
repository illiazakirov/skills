#!/usr/bin/env python3
"""The owner's answers: every point at which a step waits for the owner, as files.

    owner.py ask <brand> <question.json | ->
    owner.py get <brand> <id>
    owner.py answer <brand> <id> (--choice <id> | --text <text>) [--comment <text>] --by <who>
    owner.py pending <brand>

A step writes each question with `ask` and continues only from an answer:

    <brand>/owner/questions/<id>.json   what is asked, the options, the page to look at
    <brand>/owner/answers/<id>.json     the answer, and who gave it

The answer comes from the owner in the chat (the skill records it with `answer
--by owner`), or from another program or agent that writes it with `answer`,
before or after the question is asked. Nothing here ever chooses an answer: a
question without one is waiting. The formats are reference/contract.md, section 9.

`ask` writes the question (the same question asked again is accepted; another
question under the same id is an error), then behaves as `get`. `get` prints
the answer as JSON, or WAITING <id>: <asked>. `answer` never replaces an answer.
`pending` prints one WAITING line per unanswered question.

No dependencies beyond the Python 3 standard library. Exit codes: 0 answered
(pending: nothing waits), 1 an invalid question or answer, 2 the brand
directory cannot be read, 3 waiting for an answer.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contract as cc  # noqa: E402

QUESTION_FORMAT = "brand-question/1"
ANSWER_FORMAT = "brand-answer/1"
KINDS = ("choice", "text", "approve", "spend")
YES_NO = ("yes", "no")
SEGMENT = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ID_RE = re.compile(r"(?P<step>\d\d-%s)\.%s\.%s" % (SEGMENT, SEGMENT, SEGMENT))
QUESTION_KEYS = {"format", "id", "step", "kind", "asked", "context", "options", "recommended",
                 "proposed", "free", "page", "files"}
ANSWER_KEYS = {"format", "id", "choice", "text", "comment", "by"}
OPTION_KEYS = {"id", "label", "means"}
WAITING = 3


class Invalid(Exception):
    """A question or an answer breaks the contract. The message is safe to print."""


class Unreadable(Exception):
    """The brand directory cannot be read."""


# --- Paths -------------------------------------------------------------------------


def question_path(brand, ident):
    return os.path.join(brand, "owner", "questions", ident + ".json")


def answer_path(brand, ident):
    return os.path.join(brand, "owner", "answers", ident + ".json")


def check_brand(brand):
    """The brand directory must exist. It may not hold pipeline.yaml yet: intake asks its
    first questions before it writes one, and answers may be placed before intake runs."""
    if not os.path.isdir(brand):
        raise Unreadable("%s is not a directory; create the brand directory first" % brand)


def check_id(ident):
    match = ID_RE.fullmatch(ident or "")
    if not match or match.group("step") not in cc.STEPS:
        raise Invalid("'%s' is not an id of the form <step>.<part>.<point> with a step of "
                      "the pipeline" % ident)
    return match.group("step")


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except ValueError as error:
        raise Invalid("%s is not valid JSON: %s" % (path, error))


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".new"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


# --- Validation ----------------------------------------------------------------------


def text_value(data, key, where, required=True):
    value = data.get(key)
    if value is None:
        if required:
            raise Invalid("%s: missing '%s'" % (where, key))
        return None
    if not isinstance(value, str) or not value.strip():
        raise Invalid("%s: '%s' must be a non-empty string" % (where, key))
    return value


def validate_question(question, brand=None):
    """Raise Invalid unless question is a question of reference/contract.md, section 9.2."""
    if not isinstance(question, dict):
        raise Invalid("a question is a JSON object")
    where = "question %s" % question.get("id", "?")
    unknown = sorted(set(question) - QUESTION_KEYS)
    if unknown:
        raise Invalid("%s: unknown key '%s'" % (where, unknown[0]))
    if question.get("format") != QUESTION_FORMAT:
        raise Invalid("%s: 'format' must be '%s'" % (where, QUESTION_FORMAT))
    step = check_id(question.get("id"))
    if question.get("step") != step:
        raise Invalid("%s: 'step' must be '%s', the first part of the id" % (where, step))
    kind = question.get("kind")
    if kind not in KINDS:
        raise Invalid("%s: 'kind' must be one of: %s" % (where, ", ".join(KINDS)))
    text_value(question, "asked", where)
    text_value(question, "context", where, required=False)
    options = question.get("options")
    if kind == "choice":
        if not isinstance(options, list) or len(options) < 2:
            raise Invalid("%s: a choice has a list of two or more 'options'" % where)
        seen = set()
        for option in options:
            if not isinstance(option, dict):
                raise Invalid("%s: an option is an object with id, label, means" % where)
            unknown = sorted(set(option) - OPTION_KEYS)
            if unknown:
                raise Invalid("%s: option: unknown key '%s'" % (where, unknown[0]))
            for key in sorted(OPTION_KEYS):
                text_value(option, key, "%s: option" % where)
            if option["id"] in seen:
                raise Invalid("%s: option id '%s' is used twice" % (where, option["id"]))
            seen.add(option["id"])
        recommended = question.get("recommended")
        if recommended is not None and recommended not in seen:
            raise Invalid("%s: 'recommended' is '%s', which is not an option"
                          % (where, recommended))
        if "free" in question and not isinstance(question["free"], bool):
            raise Invalid("%s: 'free' is true or false" % where)
    else:
        for key in ("options", "recommended", "free"):
            if key in question:
                raise Invalid("%s: '%s' belongs only to a choice" % (where, key))
    if "proposed" in question:
        if kind != "text":
            raise Invalid("%s: 'proposed' belongs only to a text question" % where)
        text_value(question, "proposed", where)
    paths = []
    if "page" in question:
        paths.append(text_value(question, "page", where))
    if "files" in question:
        files = question["files"]
        if not isinstance(files, list) or not all(isinstance(f, str) and f for f in files):
            raise Invalid("%s: 'files' is a list of paths" % where)
        paths += files
    for path in paths:
        if os.path.isabs(path) or ".." in path.replace("\\", "/").split("/"):
            raise Invalid("%s: '%s' must be a path inside the brand directory" % (where, path))
        if brand is not None and not os.path.exists(os.path.join(brand, path)):
            raise Invalid("%s: '%s' does not exist in the brand directory" % (where, path))


def validate_answer(answer, question=None):
    """Raise Invalid unless answer is an answer of section 9.3 that fits its question."""
    if not isinstance(answer, dict):
        raise Invalid("an answer is a JSON object")
    where = "answer %s" % answer.get("id", "?")
    unknown = sorted(set(answer) - ANSWER_KEYS)
    if unknown:
        raise Invalid("%s: unknown key '%s'" % (where, unknown[0]))
    if answer.get("format") != ANSWER_FORMAT:
        raise Invalid("%s: 'format' must be '%s'" % (where, ANSWER_FORMAT))
    check_id(answer.get("id"))
    text_value(answer, "by", where)
    choice = text_value(answer, "choice", where, required=False)
    text = text_value(answer, "text", where, required=False)
    if "comment" in answer and not isinstance(answer["comment"], str):
        raise Invalid("%s: 'comment' must be a string" % where)
    if choice is None and text is None:
        raise Invalid("%s: an answer has a 'choice' or a 'text'" % where)
    if question is None:
        return
    if question["id"] != answer["id"]:
        raise Invalid("%s: belongs to question %s" % (where, question["id"]))
    kind = question["kind"]
    if kind in ("approve", "spend"):
        if choice not in YES_NO or text is not None:
            raise Invalid("%s: the answer to '%s' is a choice of yes or no"
                          % (where, question["asked"]))
    elif kind == "text":
        if text is None or choice is not None:
            raise Invalid("%s: the answer to '%s' is a text" % (where, question["asked"]))
    else:
        ids = [option["id"] for option in question["options"]]
        if choice is not None and choice not in ids:
            raise Invalid("%s: '%s' is not an option of '%s' (options: %s)"
                          % (where, choice, question["asked"], ", ".join(ids)))
        if text is not None and not question.get("free"):
            raise Invalid("%s: '%s' takes one of its options, not the owner's own words"
                          % (where, question["asked"]))


# --- Commands -------------------------------------------------------------------------


def load_question(brand, ident):
    path = question_path(brand, ident)
    if not os.path.isfile(path):
        return None
    question = read_json(path)
    validate_question(question)
    if question["id"] != ident:
        raise Invalid("%s holds question %s" % (path, question["id"]))
    return question


def load_answer(brand, ident):
    path = answer_path(brand, ident)
    if not os.path.isfile(path):
        return None
    answer = read_json(path)
    validate_answer(answer)
    if answer["id"] != ident:
        raise Invalid("%s holds the answer to %s" % (path, answer["id"]))
    return answer


def ask(brand, question):
    """Write the question. Return its answer, or None while it waits."""
    check_brand(brand)
    validate_question(question, brand)
    path = question_path(brand, question["id"])
    if os.path.isfile(path):
        if read_json(path) != question:
            raise Invalid("question %s was asked before in other words; a new cycle is a "
                          "new id" % question["id"])
    else:
        write_json(path, question)
    return get(brand, question["id"])


def get(brand, ident):
    """Return the answer to ident, checked against its question, or None while it waits."""
    check_brand(brand)
    check_id(ident)
    answer = load_answer(brand, ident)
    if answer is not None:
        validate_answer(answer, load_question(brand, ident))
    return answer


def give(brand, ident, choice=None, text=None, comment=None, by=None):
    """Write an answer. Never replaces one."""
    check_brand(brand)
    answer = {"format": ANSWER_FORMAT, "id": ident}
    if choice is not None:
        answer["choice"] = choice
    if text is not None:
        answer["text"] = text
    if comment:
        answer["comment"] = comment
    answer["by"] = by
    validate_answer(answer, load_question(brand, ident))
    path = answer_path(brand, ident)
    if os.path.exists(path):
        raise Invalid("question %s is answered already; an answer is never replaced" % ident)
    write_json(path, answer)
    return answer


def pending(brand):
    """Return [question] for every question without an answer, in the order of their ids."""
    check_brand(brand)
    folder = os.path.join(brand, "owner", "questions")
    found = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".json") and not name.startswith("."):
            question = load_question(brand, name[:-5])
            if question is not None and load_answer(brand, question["id"]) is None:
                found.append(question)
    return found


def waiting_line(question):
    line = "WAITING %s: %s" % (question["id"], question["asked"])
    if question.get("page"):
        line += " (page: %s)" % question["page"]
    return line


def main(argv=None):
    parser = argparse.ArgumentParser(description="The owner's answers, as files.")
    commands = parser.add_subparsers(dest="command", required=True)
    p_ask = commands.add_parser("ask", help="write a question; print its answer if any")
    p_ask.add_argument("brand")
    p_ask.add_argument("question", help="the question as a JSON file, or - for standard input")
    p_get = commands.add_parser("get", help="print the answer to a question")
    p_get.add_argument("brand")
    p_get.add_argument("id")
    p_answer = commands.add_parser("answer", help="write the answer to a question")
    p_answer.add_argument("brand")
    p_answer.add_argument("id")
    given = p_answer.add_mutually_exclusive_group(required=True)
    given.add_argument("--choice")
    given.add_argument("--text")
    p_answer.add_argument("--comment")
    p_answer.add_argument("--by", required=True,
                          help="'owner' for an answer given in the chat, else who wrote it")
    p_pending = commands.add_parser("pending", help="list the questions that wait")
    p_pending.add_argument("brand")
    args = parser.parse_args(argv)

    try:
        if args.command == "pending":
            waiting = pending(args.brand)
            for question in waiting:
                print(waiting_line(question))
            if not waiting:
                print("nothing is waiting")
            return WAITING if waiting else 0
        if args.command == "answer":
            answer = give(args.brand, args.id, args.choice, args.text, args.comment, args.by)
            print(json.dumps(answer, ensure_ascii=False, indent=2))
            return 0
        if args.command == "ask":
            if args.question == "-":
                question = json.load(sys.stdin)
            else:
                question = read_json(args.question)
            answer = ask(args.brand, question)
            ident = question["id"]
        else:
            answer = get(args.brand, args.id)
            ident = args.id
        if answer is None:
            question = load_question(args.brand, ident)
            print(waiting_line(question) if question else "WAITING %s: not asked yet" % ident)
            return WAITING
        print(json.dumps(answer, ensure_ascii=False, indent=2))
        return 0
    except Unreadable as error:
        print(error, file=sys.stderr)
        return 2
    except (Invalid, ValueError) as error:
        print("ERROR   %s" % error, file=sys.stderr)
        return 1
    except OSError as error:
        print("ERROR   %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
