#!/usr/bin/env python3
"""Render a brand choice page from its data file.

    render_choice.py <path to data.json>

Writes <same name>.html beside the data file, using the shared template
templates/choice-page.html. The data format is described in reference/choice-page.md.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 rendered, 1 the data breaks a rule, 2 the data file cannot be read.
"""

import html
import json
import os
import re
import sys
from urllib.parse import quote

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                        "templates", "choice-page.html")

LABELS = {
    "variant": "Variant",
    "reference": "Reference",
    "critic": "Critic",
    "no_remarks": "No remarks.",
    "theme": "Theme",
    "light": "Light",
    "dark": "Dark",
    "width": "Width",
    "cycle": "Cycle",
    "open": "Open full size",
    "source": "Source",
    "answer": "Answer in the chat with the number of the variant and your comment, "
              "for example: “2, but with the type from 4”.",
}

DEFAULT_VIEWPORTS = [{"width": 1440, "height": 900}]
LIVE_EXTENSIONS = (".html", ".htm")
IMAGE_EXTENSIONS = (".svg", ".png", ".jpg", ".jpeg", ".webp")
SCREENSHOT_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# A live variant must contain this listener so the page can pass the theme to it.
THEME_MARKER = "brandTheme"
THEME_SNIPPET = (
    "<script>addEventListener('message',function(e){if(e.data&&e.data.brandTheme)"
    "document.documentElement.dataset.theme=e.data.brandTheme})</script>"
)

VARIANT_RE = re.compile(r"<!--gw:variant-->(.*?)<!--gw:/variant-->", re.S)
SLOT_RE = re.compile(r"\{\{([a-z_]+)\}\}")


class DataError(Exception):
    def __init__(self, problems):
        Exception.__init__(self, "\n".join(problems))
        self.problems = problems


def esc(text):
    return html.escape(str(text), quote=True)


def href(path):
    return esc(quote(path.replace(os.sep, "/"), safe="/:@!$&'()*+,;=-._~"))


def fill(template, values):
    """Replace every {{slot}}. Values are already HTML."""
    def replace(match):
        return values[match.group(1)]
    return SLOT_RE.sub(replace, template)


def validate(data, base):
    """Return a list of problems with the data; empty when it can be rendered."""
    problems = []

    def text(mapping, key, where, required=True):
        value = mapping.get(key)
        if value is None:
            if required:
                problems.append("%s'%s' is missing" % (where, key))
            return
        if not isinstance(value, str) or not value.strip():
            problems.append("%s'%s' must be a non-empty string" % (where, key))

    def unknown(mapping, allowed, where):
        for key in mapping:
            if key not in allowed:
                problems.append("%sunknown key '%s'" % (where, key))

    def local_file(path, where, extensions):
        if not isinstance(path, str) or not path.strip():
            problems.append("%s must be a path" % where)
            return None
        if os.path.isabs(path) or "://" in path:
            problems.append("%s must be a path relative to the data file: %s" % (where, path))
            return None
        if not path.lower().endswith(extensions):
            problems.append("%s must be one of %s: %s" % (where, ", ".join(extensions), path))
            return None
        full = os.path.join(base, path)
        if not os.path.isfile(full):
            problems.append("%s does not exist: %s" % (where, path))
            return None
        return full

    if not isinstance(data, dict):
        return ["the data file must hold a JSON object"]
    unknown(data, ("lang", "title", "question", "cycle", "labels", "viewports", "variants"), "")
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

    viewports = data.get("viewports", DEFAULT_VIEWPORTS)
    if not isinstance(viewports, list) or not viewports:
        problems.append("'viewports' must be a non-empty list")
    else:
        for index, viewport in enumerate(viewports, 1):
            valid = isinstance(viewport, dict) and set(viewport) == {"width", "height"} and all(
                isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in viewport.values())
            if not valid:
                problems.append("viewport %d must be {\"width\": <pixels>, \"height\": <pixels>}"
                                % index)

    variants = data.get("variants")
    if not isinstance(variants, list):
        problems.append("'variants' must be a list")
        return problems
    if not 3 <= len(variants) <= 4:
        problems.append("a choice shows three or four variants; found %d" % len(variants))
    for index, variant in enumerate(variants, 1):
        where = "variant %d: " % index
        if not isinstance(variant, dict):
            problems.append(where + "must be an object")
            continue
        unknown(variant, ("title", "note", "file", "reference", "critic"), where)
        text(variant, "title", where)
        text(variant, "note", where, required=False)

        full = local_file(variant.get("file"), where + "'file'",
                          LIVE_EXTENSIONS + IMAGE_EXTENSIONS)
        if full and full.lower().endswith(LIVE_EXTENSIONS):
            with open(full, encoding="utf-8", errors="replace") as handle:
                if THEME_MARKER not in handle.read():
                    problems.append(
                        where + "'file' does not listen for the theme; add this to it and "
                        "style both themes through the data-theme attribute of <html>: "
                        + THEME_SNIPPET)

        reference = variant.get("reference")
        if not isinstance(reference, dict):
            problems.append(where + "'reference' is missing; a variant always stands beside "
                                    "a reference screenshot")
        else:
            unknown(reference, ("image", "caption", "source"), where + "reference: ")
            local_file(reference.get("image"), where + "reference 'image'", SCREENSHOT_EXTENSIONS)
            text(reference, "caption", where + "reference: ")
            source = reference.get("source")
            if source is not None and not (
                    isinstance(source, str) and re.match(r"https?://\S+$", source)):
                problems.append(where + "reference 'source' must be an http(s) URL")

        critic = variant.get("critic")
        if not isinstance(critic, list) or not all(
                isinstance(remark, str) and remark.strip() for remark in critic):
            problems.append(where + "'critic' must be a list of remarks (it may be empty)")
    return problems


def render(data, base, template):
    """Return the HTML of the choice page. Raise DataError when the data breaks a rule."""
    problems = validate(data, base)
    if problems:
        raise DataError(problems)

    labels = dict(LABELS, **data.get("labels", {}))
    common = {"label_" + key: esc(value) for key, value in labels.items()}
    viewports = data.get("viewports", DEFAULT_VIEWPORTS)

    variant_template = VARIANT_RE.search(template).group(1)
    sections = []
    for number, variant in enumerate(data["variants"], 1):
        path = variant["file"]
        title = esc(variant["title"])
        if path.lower().endswith(LIVE_EXTENSIONS):
            media = '<iframe src="%s" title="%s %d: %s"></iframe>' % (
                href(path), common["label_variant"], number, title)
        else:
            media = '<img class="image" src="%s" alt="%s %d: %s">' % (
                href(path), common["label_variant"], number, title)
        if variant["critic"]:
            critic = "<ul>%s</ul>" % "".join("<li>%s</li>" % esc(r) for r in variant["critic"])
        else:
            critic = '<p class="quiet">%s</p>' % common["label_no_remarks"]
        reference = variant["reference"]
        source = ""
        if reference.get("source"):
            source = '<p class="quiet">%s: <a href="%s" target="_blank" rel="noopener">%s</a></p>' % (
                common["label_source"], esc(reference["source"]), esc(reference["source"]))
        values = dict(common)
        values.update({
            "number": str(number),
            "variant_title": title,
            "note": '<p class="note">%s</p>' % esc(variant["note"]) if variant.get("note") else "",
            "variant_href": href(path),
            "variant_media": media,
            "critic": critic,
            "reference_src": href(reference["image"]),
            "reference_caption": esc(reference["caption"]),
            "reference_source": source,
        })
        sections.append(fill(variant_template, values))

    viewport_control = ""
    if len(viewports) > 1:
        buttons = "".join(
            '<button type="button" data-viewport-width="%d" data-viewport-height="%d" '
            'aria-pressed="%s">%d</button>' % (
                v["width"], v["height"], "true" if i == 0 else "false", v["width"])
            for i, v in enumerate(viewports))
        viewport_control = (
            '<div class="control"><span id="width-label">%s</span>'
            '<div class="segments" role="group" aria-labelledby="width-label">%s</div></div>'
            % (common["label_width"], buttons))

    values = dict(common)
    values.update({
        "lang": esc(data["lang"]),
        "title": esc(data["title"]),
        "meta": "%s %d" % (common["label_cycle"], data["cycle"]) if data.get("cycle") else "",
        "question": '<p class="question">%s</p>' % esc(data["question"])
                    if data.get("question") else "",
        "viewport_control": viewport_control,
        "default_width": str(viewports[0]["width"]),
        "default_height": str(viewports[0]["height"]),
    })
    page = VARIANT_RE.sub(lambda match: "\x00", template)
    return fill(page, values).replace("\x00", "\n".join(sections))


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
