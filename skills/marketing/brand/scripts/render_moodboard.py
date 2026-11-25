#!/usr/bin/env python3
"""Render a brand moodboard from its markdown index.

    render_moodboard.py <index.md> [<output.html>] [--lang TAG]

Without an output path: index.md is rendered to board.html beside it, and any other
<name>.md to <name>.html. The index format is described in reference/moodboard.md:

    # Moodboard

    An optional introduction.

    ## 1. Name of the image

    - File: aihero-home.png
    - Source: https://www.aihero.dev/
    - Takes: the density of the first screen

The page uses the shared template templates/moodboard.html and listens for the choice
page's theme, so a rendered board can be shown as a live variant.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 rendered, 1 the index breaks a rule, 2 the index cannot be read.
"""

import html
import os
import re
import sys
from urllib.parse import quote

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                        "templates", "moodboard.html")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg")
FIELDS = ["File", "Source", "Takes"]
GENERATED = "generated"
GIVEN = "given"  # material the owner handed over, in the step's given/ directory

HEADING_RE = re.compile(r"^## (\d+)\. (\S.*)$")
FIELD_RE = re.compile(r"^- ([A-Za-z]+):(.*)$")
ITEM_RE = re.compile(r"<!--gw:item-->(.*?)<!--gw:/item-->", re.S)
SLOT_RE = re.compile(r"\{\{([a-z_]+)\}\}")


class IndexProblems(Exception):
    def __init__(self, problems):
        Exception.__init__(self, "\n".join(problems))
        self.problems = problems


def esc(text):
    return html.escape(str(text), quote=True)


def href(path):
    return esc(quote(path.replace(os.sep, "/"), safe="/:@!$&'()*+,;=-._~"))


def parse(text, base, complete):
    """Return (title, intro paragraphs, items). Raise IndexProblems when a rule is broken.

    complete: every image file in the index's own directory must be listed.
    """
    problems = []
    title, intro, items, current, paragraph = None, [], [], None, []

    def flush():
        if paragraph:
            intro.append(" ".join(paragraph))
            del paragraph[:]

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = HEADING_RE.match(line)
        if line.startswith("# ") and title is None and current is None:
            title = line[2:].strip()
        elif heading:
            flush()
            current = {"number": int(heading.group(1)), "name": heading.group(2).strip(),
                       "fields": []}
            items.append(current)
        elif line.startswith("#"):
            problems.append("unexpected heading: %s" % line)
        elif current is None:
            if line.strip():
                paragraph.append(line.strip())
            else:
                flush()
        elif line.strip():
            field = FIELD_RE.match(line)
            if field:
                current["fields"].append((field.group(1), field.group(2).strip()))
            else:
                problems.append("%d. %s: unexpected line: %s"
                                % (current["number"], current["name"], line.strip()))
    flush()

    if not title:
        problems.append("the index must start with a '# ' title")
    if not items:
        problems.append("the index lists no images; each is a '## <number>. <name>' heading")
    listed = set()
    for position, item in enumerate(items, 1):
        where = "%d. %s: " % (item["number"], item["name"])
        if item["number"] != position:
            problems.append(where + "images are numbered from 1 without gaps; expected %d"
                            % position)
        if [name for name, _ in item["fields"]] != FIELDS:
            problems.append(where + "must have exactly the lines File, Source and Takes, "
                                    "in this order")
            continue
        path, source, takes = (value for _, value in item["fields"])
        item.update(file=path, source=source, takes=takes)
        if not path or os.path.isabs(path) or "://" in path:
            problems.append(where + "'File' must be a path relative to the index")
        elif not path.lower().endswith(IMAGE_EXTENSIONS):
            problems.append(where + "'File' must be one of %s: %s"
                            % (", ".join(IMAGE_EXTENSIONS), path))
        elif not os.path.isfile(os.path.join(base, path)):
            problems.append(where + "'File' does not exist: %s" % path)
        else:
            listed.add(os.path.normpath(path))
        if source not in (GENERATED, GIVEN) and not re.match(r"https?://\S+$", source):
            problems.append(where + "'Source' must be an http(s) URL, the word '%s' or the "
                                    "word '%s'" % (GENERATED, GIVEN))
        if not takes:
            problems.append(where + "'Takes' is empty; say what exactly is taken from "
                                    "this image")
    if complete:
        for name in sorted(os.listdir(base)):
            if name.lower().endswith(IMAGE_EXTENSIONS) and not name.startswith(".") \
                    and name not in listed:
                problems.append("%s is in the moodboard directory but not in the index" % name)
    if problems:
        raise IndexProblems(problems)
    return title, intro, items


def render(text, base, template, lang="en", complete=False):
    title, intro, items = parse(text, base, complete)
    item_template = ITEM_RE.search(template).group(1)

    def fill(source, values):
        return SLOT_RE.sub(lambda match: values[match.group(1)], source)

    figures = []
    for item in items:
        if item["source"] in (GENERATED, GIVEN):
            source = esc(item["source"])
        else:
            source = '<a href="%s" target="_blank" rel="noopener">%s</a>' % (
                esc(item["source"]), esc(item["source"]))
        figures.append(fill(item_template, {
            "src": href(item["file"]), "name": esc(item["name"]),
            "number": str(item["number"]), "takes": esc(item["takes"]), "source": source}))
    page = ITEM_RE.sub(lambda match: "\x00", template)
    page = fill(page, {
        "lang": esc(lang), "title": esc(title),
        "intro": '<div class="intro">%s</div>' % "".join("<p>%s</p>" % esc(p) for p in intro)
                 if intro else ""})
    return page.replace("\x00", "\n".join(figures))


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    lang = "en"
    if "--lang" in args:
        index = args.index("--lang")
        if index + 1 >= len(args):
            print(__doc__.strip(), file=sys.stderr)
            return 2
        lang = args[index + 1]
        del args[index:index + 2]
    if not 1 <= len(args) <= 2 or any(arg.startswith("-") for arg in args) \
            or not args[0].endswith(".md") or (len(args) == 2 and not args[1].endswith(".html")):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    index_path = args[0]
    is_index = os.path.basename(index_path) == "index.md"
    if len(args) == 2:
        output = args[1]
    elif is_index:
        output = os.path.join(os.path.dirname(index_path), "board.html")
    else:
        output = index_path[:-len(".md")] + ".html"
    try:
        with open(index_path, encoding="utf-8") as handle:
            text = handle.read()
        with open(TEMPLATE, encoding="utf-8") as handle:
            template = handle.read()
    except OSError as error:
        print("cannot read %s: %s" % (index_path, error), file=sys.stderr)
        return 2
    try:
        page = render(text, os.path.dirname(os.path.abspath(index_path)), template, lang,
                      complete=is_index)
    except IndexProblems as error:
        for problem in error.problems:
            print("ERROR   %s" % problem)
        print("%d error(s); nothing was written" % len(error.problems))
        return 1
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(page)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
