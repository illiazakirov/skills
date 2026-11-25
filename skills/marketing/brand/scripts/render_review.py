#!/usr/bin/env python3
"""Render a brand review page from its data file.

    render_review.py <path to data.json>

A review page shows finished items (for example the surfaces of an identity) together,
each at its own size with the critic's remarks beside it. It offers no variants: the
owner answers in the chat with corrections. Choices between variants use
render_choice.py instead.

Writes <same name>.html beside the data file, using templates/review-page.html.
The data format is described in reference/review-page.md.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 rendered, 1 the data breaks a rule, 2 the data file cannot be read.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_choice as rc  # noqa: E402
from render_choice import DataError, esc, href  # noqa: E402

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                        "templates", "review-page.html")
LABELS = dict(rc.LABELS, answer="Answer in the chat with the number of the item and what to "
                                "change in it, or say that everything is fixed.")
ITEM_RE = re.compile(r"<!--gw:item-->(.*?)<!--gw:/item-->", re.S)
MAX_SIZE = 4000


def validate(data, base):
    """Return a list of problems with the data; empty when it can be rendered."""
    problems = []

    def text(mapping, key, where, required=True):
        value = mapping.get(key)
        if value is None:
            if required:
                problems.append("%s'%s' is missing" % (where, key))
        elif not isinstance(value, str) or not value.strip():
            problems.append("%s'%s' must be a non-empty string" % (where, key))

    def unknown(mapping, allowed, where):
        for key in mapping:
            if key not in allowed:
                problems.append("%sunknown key '%s'" % (where, key))

    def local_file(path, where, extensions):
        if not isinstance(path, str) or not path.strip():
            problems.append("%s must be a path" % where)
        elif os.path.isabs(path) or "://" in path:
            problems.append("%s must be a path relative to the data file: %s" % (where, path))
        elif not path.lower().endswith(extensions):
            problems.append("%s must be one of %s: %s" % (where, ", ".join(extensions), path))
        elif not os.path.isfile(os.path.join(base, path)):
            problems.append("%s does not exist: %s" % (where, path))

    if not isinstance(data, dict):
        return ["the data file must hold a JSON object"]
    unknown(data, ("lang", "title", "question", "cycle", "labels", "items"), "")
    text(data, "lang", "")
    text(data, "title", "")
    text(data, "question", "", required=False)
    cycle = data.get("cycle")
    if cycle is not None and (isinstance(cycle, bool) or not isinstance(cycle, int) or cycle < 1):
        problems.append("'cycle' must be a whole number, 1 or more")
    labels = data.get("labels", {})
    if not isinstance(labels, dict):
        problems.append("'labels' must be an object")
    else:
        unknown(labels, LABELS, "labels: ")
        for key in labels:
            if key in LABELS:
                text(labels, key, "labels: ")

    items = data.get("items")
    if not isinstance(items, list) or not items:
        problems.append("'items' must be a non-empty list")
        return problems
    for index, item in enumerate(items, 1):
        where = "item %d: " % index
        if not isinstance(item, dict):
            problems.append(where + "must be an object")
            continue
        unknown(item, ("title", "note", "file", "width", "height", "critic", "reference"), where)
        text(item, "title", where)
        text(item, "note", where, required=False)
        local_file(item.get("file"), where + "'file'", rc.LIVE_EXTENSIONS + rc.IMAGE_EXTENSIONS)
        for key in ("width", "height"):
            value = item.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_SIZE:
                problems.append(where + "'%s' must be a whole number of pixels, 1 to %d"
                                % (key, MAX_SIZE))
        critic = item.get("critic")
        if not isinstance(critic, list) or not all(
                isinstance(remark, str) and remark.strip() for remark in critic):
            problems.append(where + "'critic' must be a list of remarks (it may be empty)")
        reference = item.get("reference")
        if reference is not None:
            if not isinstance(reference, dict):
                problems.append(where + "'reference' must be an object")
                continue
            unknown(reference, ("image", "caption", "source"), where + "reference: ")
            local_file(reference.get("image"), where + "reference 'image'",
                       rc.SCREENSHOT_EXTENSIONS)
            text(reference, "caption", where + "reference: ")
            source = reference.get("source")
            if source is not None and not (
                    isinstance(source, str) and re.match(r"https?://\S+$", source)):
                problems.append(where + "reference 'source' must be an http(s) URL")
    return problems


def render(data, base, template):
    """Return the HTML of the review page. Raise DataError when the data breaks a rule."""
    problems = validate(data, base)
    if problems:
        raise DataError(problems)
    labels = dict(LABELS, **data.get("labels", {}))
    common = {"label_" + key: esc(value) for key, value in labels.items()}
    item_template = ITEM_RE.search(template).group(1)
    sections = []
    for number, item in enumerate(data["items"], 1):
        path, title = item["file"], esc(item["title"])
        if path.lower().endswith(rc.LIVE_EXTENSIONS):
            media = '<iframe src="%s" title="%d: %s"></iframe>' % (href(path), number, title)
        else:
            media = '<img class="image" src="%s" alt="%d: %s">' % (href(path), number, title)
        if item["critic"]:
            critic = "<ul>%s</ul>" % "".join("<li>%s</li>" % esc(r) for r in item["critic"])
        else:
            critic = '<p class="quiet">%s</p>' % common["label_no_remarks"]
        reference = ""
        if item.get("reference"):
            ref = item["reference"]
            source = ""
            if ref.get("source"):
                source = ('<p class="quiet">%s: <a href="%s" target="_blank" rel="noopener">%s</a></p>'
                          % (common["label_source"], esc(ref["source"]), esc(ref["source"])))
            reference = (
                '<div class="frame reference" tabindex="0"><img src="%s" alt="%s"></div>'
                '<div class="below"><h3>%s</h3><p>%s</p>%s</div>'
                % (href(ref["image"]), esc(ref["caption"]), common["label_reference"],
                   esc(ref["caption"]), source))
        values = dict(common)
        values.update({
            "number": str(number), "item_title": title,
            "note": '<p class="note">%s</p>' % esc(item["note"]) if item.get("note") else "",
            "item_href": href(path), "item_media": media, "critic": critic,
            "reference": reference, "width": str(item["width"]), "height": str(item["height"]),
        })
        sections.append(rc.fill(item_template, values))
    values = dict(common)
    values.update({
        "lang": esc(data["lang"]), "title": esc(data["title"]),
        "meta": "%s %d" % (common["label_cycle"], data["cycle"]) if data.get("cycle") else "",
        "question": '<p class="question">%s</p>' % esc(data["question"])
                    if data.get("question") else "",
    })
    page = ITEM_RE.sub(lambda match: "\x00", template)
    return rc.fill(page, values).replace("\x00", "\n".join(sections))


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0].startswith("-") or not args[0].endswith(".json"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    data_path = args[0]
    try:
        with open(data_path, encoding="utf-8") as handle:
            data = json.load(handle)
        with open(TEMPLATE, encoding="utf-8") as handle:
            template = handle.read()
    except (OSError, ValueError) as error:
        print("cannot read %s: %s" % (data_path, error), file=sys.stderr)
        return 2
    try:
        page = render(data, os.path.dirname(os.path.abspath(data_path)), template)
    except DataError as error:
        for problem in error.problems:
            print("ERROR   %s" % problem)
        print("%d error(s); nothing was written" % len(error.problems))
        return 1
    output = data_path[:-len(".json")] + ".html"
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(page)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
