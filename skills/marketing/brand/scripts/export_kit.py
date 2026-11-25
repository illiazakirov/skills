#!/usr/bin/env python3
"""Export the kit: the finished product of a brand pipeline, in brand/out/.

    export_kit.py [<brand>]                            build <brand>/out/
    export_kit.py [<brand>] --check                    say whether <brand>/out/ is current
    export_kit.py [<brand>] --deliver <dir>            copy the current kit to <dir>
    export_kit.py [<brand>] --check --deliver <dir>    say whether <dir> holds the current kit

<brand> is the brand directory (reference/contract.md, section 1): brand/ in a project,
or an order directory in a studio. It defaults to ./brand.

brand/ is the working state of the pipeline: steps, rationale, choice pages,
review pages. brand/out/ holds only what is finished and approved, in a fixed
layout that is the same for every brand, with instructions for the agents and
people who receive it:

    AGENTS.md          how an agent works with the kit: what is where, by task, the rules
    README.md          the same for a person, in short
    brand.md           the brand book as text, with the paths of the kit
    brand.json         every slot of every approved plate, as data
    manifest.json      the brand, the step versions the kit was built from, every file
    book/              index.html and brand-book.pdf, the brand book
    logo/              full.svg, mark.svg, mono.svg, dark.svg
    fonts/             the font files, fonts.css and the licenses
    tokens/            tokens.json (W3C DTCG) and tokens.css
    system/            components.md, system.css, index.html, sheet.html, pages/
    surfaces/          the surfaces of the identity

The kit is built only from a pipeline whose every step is approved (or skipped),
whose check is clean, with no version warnings, and whose brand-book.md says
status: approved. Every relative link of a copied HTML or CSS file is rewritten
to the kit's layout; a link to a file outside the kit stops the export. The kit
is written to a temporary directory and swapped in whole; an existing out/ is
replaced only when its manifest.json says it is a kit.

Delivery copies the current out/ as it is into a directory of the project the
brand is for (reference/contract.md, section 8.1); it never exports. The copy is a
generated directory: its check fails on a changed, missing or added file.

No dependencies beyond the Python 3 standard library. Exit codes: 0 built (or
current, with --check), 1 the pipeline is not ready or the kit is out of date,
2 brand/ unreadable.
"""

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contract as cc  # noqa: E402
import render_book as rb  # noqa: E402
import render_plates as rp  # noqa: E402

OUT = "out"
FORMAT = "brand-kit/2"
FORMAT_PREFIX = "brand-kit/"
INTAKE, IDENTITY, DESIGN, BOOK = "00-intake", "03-identity", "04-design-system", "05-brand-book"

# Where each finished file of brand/ goes in the kit: (source in brand/, path in the kit).
# A directory entry copies every visible file under it.
LAYOUT = [
    (BOOK + "/index.html", "book/index.html"),
    (BOOK + "/brand-book.pdf", "book/brand-book.pdf"),
    (IDENTITY + "/logo/full.svg", "logo/full.svg"),
    (IDENTITY + "/logo/mark.svg", "logo/mark.svg"),
    (IDENTITY + "/logo/mono.svg", "logo/mono.svg"),
    (IDENTITY + "/logo/dark.svg", "logo/dark.svg"),
    (IDENTITY + "/fonts", "fonts"),
    (IDENTITY + "/surfaces", "surfaces"),
    (DESIGN + "/tokens.json", "tokens/tokens.json"),
    (DESIGN + "/tokens.css", "tokens/tokens.css"),
    (DESIGN + "/components.md", "system/components.md"),
    (DESIGN + "/reference", "system"),
]
OPTIONAL = {BOOK + "/brand-book.pdf"}
REWRITTEN = (".html", ".css")

LINK_RE = re.compile(r"""(?P<lead>\b(?:href|src)\s*=\s*)(?P<q>["'])(?P<url>[^"']*)(?P=q)"""
                     r"""|(?P<css>url\(\s*)(?P<cq>["']?)(?P<curl>[^"')]*)(?P=cq)\s*\)""", re.I)
EXTERNAL_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#|/)", re.I)


class Problem(Exception):
    """The kit cannot be built; nothing was written."""


# --- Fixed texts ---------------------------------------------------------------

AGENTS = """# {name}: brand kit

This directory is the finished brand of {name}, made with brand and approved by its owner line by line. It is the single input for any work that speaks or looks like the brand: a landing page, a screen, a post, a campaign, an email. Every file was generated from the approved steps of the pipeline; none is edited by hand.

## Read first

1. `brand.md`: the whole brand as text: the strategy, the brand platform, the identity, the design system, the rules. Read it from the start before any task.
2. This file: what is where, and which files a task needs.

The market language is `{language}`: every word of copy you write for the brand is in it. The brand's own lines (the plates in `brand.md`) are in English, except the motto, the voice examples and the name.

## What is here

| Path | What it is | Use it for |
|---|---|---|
| `brand.md` | The brand book as text | Reading the brand; quoting its lines |
| `brand.json` | Every slot of every plate, as data | Reading one line by its step, plate and slot |
| `book/index.html` | The brand book: one self-contained page | Showing the brand to a person |
| `book/brand-book.pdf` | The same, as fixed pages | Sending the brand as a document; absent when it was not printed |
| `logo/full.svg` | The mark and the name | The logo wherever there is room |
| `logo/mark.svg` | The mark alone | Small places: an avatar, a favicon |
| `logo/mono.svg` | One color, `currentColor` | Single-color print, overlays |
| `logo/dark.svg` | For dark backgrounds | The dark theme |
| `fonts/` | The font files, `fonts.css`, the licenses | Loading the type; never from a remote server |
| `tokens/tokens.json` | Every design token, W3C DTCG, with `dark` and `narrow` groups | The source of every value |
| `tokens/tokens.css` | The same as CSS custom properties | Linking into a page |
| `system/components.md` | Every component: what for, states, tokens, at 390, accessibility | Building UI |
| `system/system.css` | The styles of every component | Linking into a page |
| `system/index.html` | Every component and page, drawn | Seeing how a component looks |
| `system/pages/` | A landing page, sign-in and sign-up | The starting point of a new page |
| `surfaces/` | The brand on its surfaces: {surfaces} | The size and composition of each surface |
| `manifest.json` | The brand, the versions it was built from, every file with its hash | Checking what you received |

## By task

**Write copy** (a page, a post, an email, a bio). Read in `brand.md` the Messaging (the main promise, proofs, objections), the Positioning, and the whole Voice plate: the voice, the tone, `We write like this`, `We never write`, the examples. Write in `{language}`. The motto is copy: it stands where `Where it stands` says, never beside or under the logo.

**Build a web page or a screen.** Link `fonts/fonts.css`, `tokens/tokens.css` and `system/system.css`, in this order. Take the markup of a component from `system/index.html` and its rules from `system/components.md`; start a page from one in `system/pages/`. Use the tokens by name, never their values; keep the `Never` lines of the Interface plate. Check both themes and a width of 390.

**Make an image** (a social card, a cover, a slide). Take the logo from `logo/`, the colors from the Color plate, the type from `fonts/`; keep the logo's minimum size and clear space. Use `surfaces/` as the reference for each format. The images must belong to the territory in the Mood plate and avoid what it excludes.

**Read one value in code.** Take it from `brand.json` (a line of a plate) or `tokens/tokens.json` (a design value). Do not parse `brand.md`.

## Rules

{rules}

## When something changes

{change} If you find an error here, report it with the file and the line; do not fix it in the kit.
"""

README = """# {name}: brand kit

The finished brand of {name}, made with brand and approved by its owner. Built from the approved pipeline; never edited by hand.

- Open `book/index.html` in a browser for the brand book, or `book/brand-book.pdf`.
- Give this whole directory to a designer, a developer or an agent. Agents start with `AGENTS.md`.
- `logo/`, `fonts/`, `tokens/`, `system/` and `surfaces/` are the files to build with.

{change}
"""


# --- Reading the pipeline --------------------------------------------------------


def read_pipeline(brand):
    path = os.path.join(brand, "pipeline.yaml")
    try:
        data = cc.parse_yaml(cc.read_lines(path))
    except (OSError, UnicodeDecodeError, cc.SubsetError) as error:
        raise cc.Unreadable("cannot read %s: %s" % (path, error))
    return data


def versions(pipeline):
    steps = pipeline.get("steps") if isinstance(pipeline.get("steps"), dict) else {}
    return {step: (steps.get(step) or {}).get("version", "") for step in cc.STEPS}


def ready(brand, pipeline):
    """Raise Problem when the pipeline is not finished, not clean or not current."""
    steps = pipeline.get("steps") if isinstance(pipeline.get("steps"), dict) else {}
    open_steps = ["%s is %s" % (step, (steps.get(step) or {}).get("status", "missing"))
                  for step in cc.STEPS
                  if (steps.get(step) or {}).get("status") not in ("approved", "skipped")]
    if open_steps:
        raise Problem("every step must be approved or skipped first: " + "; ".join(open_steps))
    if steps[BOOK].get("status") != "approved":
        raise Problem("%s is skipped; the kit is built from the brand book" % BOOK)
    report = cc.check(brand)
    if report.errors or report.warnings:
        found = ["%s: %s" % item for item in report.errors + report.warnings]
        raise Problem("the check of brand/ is not clean; run brand status: "
                      + "; ".join(found))
    with open(os.path.join(brand, BOOK, "brand-book.md"), encoding="utf-8") as handle:
        head = handle.read(200)
    if "\nstatus: approved\n" not in head:
        raise Problem("%s/brand-book.md is not approved; close the brand book step" % BOOK)


# --- Files -------------------------------------------------------------------------


def visible_files(root):
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        found += [os.path.join(folder, name) for name in sorted(files) if not name.startswith(".")]
    return found


def plan_files(brand):
    """{kit path: absolute source path}. Raise Problem when a required file is missing."""
    plan, missing = {}, []
    for source, target in LAYOUT:
        full = os.path.join(brand, source)
        if os.path.isdir(full):
            for path in visible_files(full):
                relative = os.path.relpath(path, full).replace(os.sep, "/")
                plan[posixpath.join(target, relative)] = path
        elif os.path.isfile(full):
            plan[target] = full
        elif source not in OPTIONAL:
            missing.append(source)
    if missing:
        raise Problem("missing in brand/: " + ", ".join(missing))
    return plan


def rewrite_links(text, source, target, by_source, brand):
    """Point every relative link of a file copied from source to target at the kit's copy.
    Return (text, [links that lead outside the kit])."""
    outside = []

    def replace(match):
        url = match.group("url") if match.group("lead") else match.group("curl")
        if not url or EXTERNAL_RE.match(url):
            return match.group(0)
        cut = re.search(r"[?#]", url)
        path, rest = (url[:cut.start()], url[cut.start():]) if cut else (url, "")
        resolved = os.path.normpath(os.path.join(os.path.dirname(source), path))
        kit_path = by_source.get(resolved)
        if kit_path is None:
            outside.append("%s -> %s" % (os.path.relpath(source, brand), url))
            return match.group(0)
        new = posixpath.relpath(kit_path, posixpath.dirname(target)) + rest
        if match.group("lead"):
            return "%s%s%s%s" % (match.group("lead"), match.group("q"), new, match.group("q"))
        return "%s%s%s%s)" % (match.group("css"), match.group("cq"), new, match.group("cq"))

    return LINK_RE.sub(replace, text), outside


# --- Generated files ----------------------------------------------------------------


def plates_json(brief, plates):
    data = {}
    for plate in [brief] + plates:
        slots = {}
        for slot, values in plate["slots"]:
            slots[slot["name"]] = values[0] if slot["kind"] == "line" else list(values)
        data.setdefault(plate["step"], {})[plate["name"][:-3]] = {"title": plate["title"],
                                                                 "slots": slots}
    return data


def rules_md():
    return rb.HOW_TO_USE.replace("This book, from the start.", "`brand.md`, from the start.")


def change_sentence(order):
    """How the brand is changed, for AGENTS.md and README.md: true wherever the kit is
    delivered, and silent on where the working directory is (reference/contract.md, section 8)."""
    origin = ("the brand working directory of order `%s`, kept by the studio that made "
              "this kit" % order) if order else "the brand working directory it was built from"
    return ("The kit is rebuilt, never edited. The brand is changed in %s, by the step that "
            "owns the line; then the brand book and this kit are built and delivered again."
            % origin)


def generated(brand, pipeline, plates, brief):
    name = rb.brand_name(plates, brief)
    order = pipeline.get("order") or None
    change = change_sentence(order)
    by_name = {plate["name"]: plate for plate in plates}
    language = pipeline.get("market_language", "")
    surfaces = ", ".join(s[:-5] for s in rp.list_surfaces(brand)) or "none"
    brand_data = {
        "format": FORMAT,
        "name": name,
        "motto": rp.one(by_name["motto.md"], "Motto"),
        "in_one_line": rp.one(brief, "In one line"),
        "profile": pipeline.get("profile", ""),
        "market_language": language,
        "plates": plates_json(brief, plates),
    }
    return name, brand_data, {
        "AGENTS.md": AGENTS.format(name=name, language=language, surfaces=surfaces,
                                   rules=rules_md(), change=change),
        "README.md": README.format(name=name, change=change),
        "brand.md": rb.book_md(brand, plates, brief, "approved", kit=True, order=order),
        "brand.json": json.dumps(brand_data, ensure_ascii=False, indent=2) + "\n",
    }


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# --- Build -----------------------------------------------------------------------


def is_kit(out):
    try:
        with open(os.path.join(out, "manifest.json"), encoding="utf-8") as handle:
            value = json.load(handle).get("format")
        return isinstance(value, str) and value.startswith(FORMAT_PREFIX)
    except (OSError, ValueError, AttributeError):
        return False


def refuse_non_kit(directory):
    if os.path.exists(directory) and not is_kit(directory) and (
            os.path.isfile(directory) or os.listdir(directory)):
        raise Problem("%s exists and is not a kit (no manifest.json of %s); move it away"
                      % (directory, FORMAT_PREFIX + "*"))


def swap_in(directory, contents):
    """Write {kit path: bytes} to a staging directory beside <directory>, then swap it in
    whole. An existing <directory> is replaced only when it is a kit."""
    refuse_non_kit(directory)
    parent, base = os.path.split(os.path.abspath(directory))
    os.makedirs(parent, exist_ok=True)
    staging = os.path.join(parent, ".%s-new" % base)
    shutil.rmtree(staging, ignore_errors=True)
    for target, data in contents.items():
        path = os.path.join(staging, *target.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
    old = os.path.join(parent, ".%s-old" % base)
    shutil.rmtree(old, ignore_errors=True)
    if os.path.exists(directory):
        os.rename(directory, old)
    os.rename(staging, directory)
    shutil.rmtree(old, ignore_errors=True)


def build(brand):
    """Build brand/out/. Return (path of out/, [notes]). Raise Problem."""
    pipeline = read_pipeline(brand)
    ready(brand, pipeline)
    try:
        plates, brief, _board, _look, _skipped = rb.load(brand)
    except rb.Problem as error:
        raise Problem(str(error))
    plan = plan_files(brand)
    by_source = {os.path.normpath(source): target for target, source in plan.items()}
    contents, outside = {}, []
    for target, source in sorted(plan.items()):
        with open(source, "rb") as handle:
            data = handle.read()
        if target.endswith(REWRITTEN):
            text, lost = rewrite_links(data.decode("utf-8"), source, target, by_source, brand)
            outside += lost
            data = text.encode("utf-8")
        contents[target] = data
    if outside:
        raise Problem("these links lead outside the kit: " + "; ".join(outside))
    name, _brand_data, texts = generated(brand, pipeline, plates, brief)
    for target, text in texts.items():
        contents[target] = text.encode("utf-8")
    manifest = {"format": FORMAT, "name": name}
    if pipeline.get("order"):
        manifest["order"] = pipeline["order"]
    manifest.update({
        "built_from": versions(pipeline),
        "files": {path: {"sha256": sha256(data), "bytes": len(data)}
                  for path, data in sorted(contents.items())},
    })
    contents["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()

    out = os.path.join(brand, OUT)
    swap_in(out, contents)
    notes = ["%d files, %.1f MB" % (len(contents), sum(map(len, contents.values())) / 1e6)]
    if "book/brand-book.pdf" not in contents:
        notes.append("the brand book has no PDF, so neither has the kit")
    return out, notes


def current(brand):
    """Return [reasons the kit is out of date]; empty when it is current."""
    out = os.path.join(brand, OUT)
    if not is_kit(out):
        return ["%s/ does not exist or is not a kit" % OUT]
    with open(os.path.join(out, "manifest.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    reasons = []
    if manifest.get("format") != FORMAT:
        reasons.append("the kit is %s; the current format is %s"
                       % (manifest.get("format"), FORMAT))
    now = versions(read_pipeline(brand))
    for step, version in now.items():
        if manifest.get("built_from", {}).get(step) != version:
            reasons.append("%s is now %s, the kit was built from %s"
                           % (step, version or "unversioned",
                              manifest.get("built_from", {}).get(step) or "nothing"))
    for path, entry in manifest.get("files", {}).items():
        try:
            with open(os.path.join(out, *path.split("/")), "rb") as handle:
                if sha256(handle.read()) != entry.get("sha256"):
                    reasons.append("%s was changed by hand" % path)
        except OSError:
            reasons.append("%s is missing" % path)
    return reasons


def read_manifest(directory):
    with open(os.path.join(directory, "manifest.json"), encoding="utf-8") as handle:
        return json.load(handle)


def inside(path, directory):
    path, directory = os.path.realpath(path), os.path.realpath(directory)
    return path == directory or path.startswith(directory + os.sep)


def deliver(brand, target):
    """Copy the current <brand>/out/ to <target>. Return (target, [notes]). Raise Problem."""
    reasons = current(brand)
    if reasons:
        raise Problem("the kit in %s/ is not current; export it first: %s"
                      % (OUT, "; ".join(reasons)))
    if inside(target, brand):
        raise Problem("%s is inside the brand directory; deliver the kit to the project "
                      "it is for" % target)
    out = os.path.join(brand, OUT)
    manifest = read_manifest(out)
    contents = {}
    for path in list(manifest["files"]) + ["manifest.json"]:
        with open(os.path.join(out, *path.split("/")), "rb") as handle:
            contents[path] = handle.read()
    swap_in(target, contents)
    return target, ["%d files" % len(contents)]


def delivered_current(brand, target):
    """Return [reasons the kit in <target> is not the current kit]; empty when it is."""
    reasons = ["%s/: %s" % (OUT, reason) for reason in current(brand)]
    if not is_kit(target):
        return reasons + ["%s does not exist or is not a kit" % target]
    try:
        theirs = read_manifest(target)
    except (OSError, ValueError) as error:
        return reasons + ["%s/manifest.json cannot be read: %s" % (target, error)]
    if not reasons and theirs != read_manifest(os.path.join(brand, OUT)):
        reasons.append("%s holds another kit: built from %s, the current one from %s"
                       % (target, theirs.get("built_from"),
                          read_manifest(os.path.join(brand, OUT)).get("built_from")))
    listed = set(theirs.get("files", {})) | {"manifest.json"}
    for path, entry in theirs.get("files", {}).items():
        try:
            with open(os.path.join(target, *path.split("/")), "rb") as handle:
                if sha256(handle.read()) != entry.get("sha256"):
                    reasons.append("%s was changed by hand" % path)
        except OSError:
            reasons.append("%s is missing" % path)
    for path in visible_files(target):
        relative = os.path.relpath(path, target).replace(os.sep, "/")
        if relative not in listed:
            reasons.append("%s is not part of the kit" % relative)
    return reasons


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export the kit to <brand>/out/, or deliver it.")
    parser.add_argument("brand", nargs="?", default="brand",
                        help="the brand directory (default: ./brand)")
    parser.add_argument("--check", action="store_true",
                        help="only say whether the kit is current")
    parser.add_argument("--deliver", metavar="DIR",
                        help="copy the current kit to DIR (with --check: check DIR)")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.brand):
        print("%s is not a directory" % args.brand, file=sys.stderr)
        return 2
    try:
        if args.check:
            reasons = (delivered_current(args.brand, args.deliver) if args.deliver
                       else current(args.brand))
            for reason in reasons:
                print("STALE   %s" % reason)
            what = "the delivered kit" if args.deliver else "the kit"
            print("%s is current" % what if not reasons else "%s is out of date" % what)
            return 1 if reasons else 0
        if args.deliver:
            target, notes = deliver(args.brand, args.deliver)
            print("delivered: %s" % target)
            for note in notes:
                print("NOTE    %s" % note)
            return 0
        out, notes = build(args.brand)
    except cc.Unreadable as error:
        print(error, file=sys.stderr)
        return 2
    except Problem as error:
        print("ERROR   %s" % error, file=sys.stderr)
        print("nothing was written", file=sys.stderr)
        return 1
    print("kit: %s" % out)
    for note in notes:
        print("NOTE    %s" % note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
