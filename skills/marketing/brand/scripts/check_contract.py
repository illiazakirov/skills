#!/usr/bin/env python3
"""Check a brand/ directory against the artifact contract.

The contract is reference/contract.md. This script has no dependencies beyond the
Python 3 standard library and never modifies anything.

    check_contract.py check [--step <step>] [<path to brand/>]
    check_contract.py hash <step> [<path to brand/>]
    check_contract.py contrast "<palette line>" ...
    check_contract.py tokens <tokens.json>

Exit codes: 0 no errors, 1 contract errors, 2 brand/ or pipeline.yaml unreadable.
"""

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_tokens as bt  # noqa: E402

STEPS = [
    "00-intake",
    "01-strategy",
    "02-brand-platform",
    "03-identity",
    "04-design-system",
    "05-brand-book",
]

PROFILES = ("b2b-saas", "consumer-app", "local-business", "personal-brand", "physical-product")

TOOLS = {
    "image_generation": ("fal", "svg-only", "none"),
    "screenshots": ("headless-chrome", "manual"),
    "figma_export": ("on", "off"),
}

STEP_STATUSES = ("pending", "in-progress", "approved", "stale", "skipped")
ARTIFACT_STATUSES = ("draft", "approved")
SOURCES = ("generated", "provided")

REVIEW_STEPS = ("02-brand-platform", "03-identity", "04-design-system")

SUMMARY_SECTIONS = ["Decisions", "Constraints on later steps", "Open questions"]
DECISION_FIELDS = ["Page", "Decision", "Comment", "Status"]


def line(name, words=None, pattern=None, shape=None, min_words=None, optional=False,
         headline=False):
    """A plate slot that holds exactly one line."""
    return {"name": name, "kind": "line", "words": words, "min_words": min_words,
            "pattern": pattern, "shape": shape, "optional": optional, "headline": headline,
            "starts": None}


def items(name, low, high, words=None, pattern=None, shape=None, optional=False, starts=None):
    """A plate slot that holds a bulleted list of low to high items.

    starts: one label per item; item i must begin with starts[i] and a colon.
    """
    return {"name": name, "kind": "list", "low": low, "high": high, "words": words,
            "min_words": None, "pattern": pattern, "shape": shape, "optional": optional,
            "headline": False, "starts": starts}


# The twelve brand archetypes (Mark and Pearson, 2001), under the names the trade uses.
ARCHETYPES = ("Innocent", "Everyman", "Hero", "Outlaw", "Explorer", "Creator", "Ruler",
              "Magician", "Lover", "Caregiver", "Jester", "Sage")
_ARCHETYPE = {"pattern": "|".join(ARCHETYPES), "shape": "be one of: " + ", ".join(ARCHETYPES)}

# The four dimensions of tone (Nielsen Norman Group, 2016), in their published order.
# A position is "N of 5": 1 is the first pole, 5 the second.
TONE_DIMENSIONS = ("Formal–casual", "Serious–funny", "Respectful–irreverent",
                   "Matter-of-fact–enthusiastic")

# The kinds of a logo.
LOGO_KINDS = ("Wordmark", "Symbol and wordmark", "Monogram")

# The roles a palette color may carry. A palette line may name several, separated by commas.
THEME_ROLES = ("background on light", "text on light", "background on dark", "text on dark")
PALETTE_ROLES = THEME_ROLES + ("accent", "secondary")

# Body text must reach this contrast with its background in both themes (WCAG 2, level AA).
BODY_CONTRAST = 4.5
LARGE_CONTRAST = 3.0


# Plates: step -> {path: (title, [slots])}. A plate is the literal, short answer
# in the slots of one tool (contract section 5.1). Word limits are per line or
# per list item.
PLATES = {
    "00-intake": {
        "brief.md": ("The Brief", [
            line("Brand"),
            line("In one line", words=12),
            line("For whom"),
            line("Why now"),
            line("Ambition"),
        ]),
    },
    "01-strategy": {
        "golden-circle.md": ("Golden Circle", [
            line("Why", words=15, pattern=r"(We|I) believe .+",
                 shape="start with 'We believe' or 'I believe'", headline=True),
            items("How", 3, 3, words=6),
            line("What", words=12),
        ]),
        "lean-canvas.md": ("Lean Canvas", [
            items("Problem", 3, 3, words=10),
            line("Existing alternatives"),
            items("Customer segments", 1, 2),
            line("Early adopter"),
            line("Unique value proposition", words=15, headline=True),
            items("Solution", 3, 3),
            items("Channels", 1, 3),
            items("Revenue streams", 1, 3),
            items("Cost structure", 1, 3),
            items("Key metrics", 1, 3),
            line("Unfair advantage"),
        ]),
        "icp.md": ("ICP and Jobs-to-be-Done", [
            line("Who"),
            line("Situation"),
            line("Trigger"),
            line("Tried before"),
            line("Where to find"),
            line("Main job", pattern=r"When .+, I want to .+, so I can .+",
                 shape="have the form 'When ..., I want to ..., so I can ...'", headline=True),
            line("Functional"),
            line("Emotional"),
            line("Social"),
            items("Other customers", 1, 2, optional=True),
        ]),
        "positioning.md": ("Positioning", [
            items("Competitive alternatives", 1, 3),
            items("Unique attributes", 3, 3),
            items("Value", 3, 3),
            line("Target segment"),
            line("Market category", words=5),
            line("Positioning statement", words=50, pattern=r"For .+ Unlike .+",
                 shape="have the form 'For ... Unlike ...'", headline=True),
        ]),
        "brand-wheel.md": ("Brand Wheel", [
            items("Attributes", 3, 5),
            items("Functional benefits", 3, 3),
            items("Emotional benefits", 3, 3),
            items("Values", 3, 3, words=2),
            items("Personality", 3, 5, pattern=r"[^:]+: .+",
                  shape="have the form 'Trait: what it means in practice'"),
            line("Essence", words=4, min_words=2, headline=True),
        ]),
        "marketing-mix.md": ("Marketing Mix", [
            line("Product", words=20),
            line("Price", words=20),
            line("Place", words=20),
            line("Promotion", words=20),
            line("People", words=20, optional=True),
            line("Process", words=20, optional=True),
            line("Physical evidence", words=20, optional=True),
        ]),
        "messaging.md": ("Messaging", [
            line("Main promise", words=12, headline=True),
            items("Proofs", 3, 3, pattern=r"[^:]+: .+", shape="have the form 'Claim: fact'"),
            items("Objections", 3, 3, pattern=r"\"[^\"]+\" .+",
                  shape="be the objection in double quotes, then the answer"),
        ]),
    },
    "02-brand-platform": {
        "archetype.md": ("Archetype", [
            line("Primary archetype", **_ARCHETYPE),
            line("Secondary archetype", **_ARCHETYPE),
            line("Character", words=12, pattern=r"The .+ who .+",
                 shape="have the form 'The ... who ...'", headline=True),
            line("Why this pair", words=20),
            items("Personality", 3, 5, pattern=r"[^,:]+, but not [^:]+: .+",
                  shape="have the form 'Trait, but not X: what it means in practice'"),
        ]),
        "voice.md": ("Voice", [
            line("Voice", words=15, pattern=r"We sound like .+, never like .+",
                 shape="have the form 'We sound like ..., never like ...'", headline=True),
            items("Tone", 4, 4, starts=TONE_DIMENSIONS, pattern=r"[^:]+: [1-5] of 5\. .+",
                  shape="have the form 'Dimension: N of 5. Why', with N from 1 to 5"),
            items("We write like this", 3, 5),
            items("We never write", 3, 5),
            items("Examples", 4, 4, pattern=r"[^.]+\. Right: .+ Wrong: .+",
                  shape="have the form 'Situation. Right: ... Wrong: ...'"),
        ]),
        "name.md": ("Name", [
            line("Name", words=3, headline=True),
            line("Domain"),
            line("What it says", words=15),
            items("Rejected", 1, 3, pattern=r"[^:]+: .+", shape="have the form 'Name: reason'",
                  optional=True),
        ]),
        "mood.md": ("Mood", [
            line("Territory", words=4, min_words=2, headline=True),
            items("Mood words", 3, 3, words=1),
            items("Takes", 3, 5),
            items("Excludes", 3, 3),
        ]),
    },
    "03-identity": {
        "logo.md": ("Logo", [
            line("Logo idea", words=12, headline=True),
            line("Kind", pattern="|".join(LOGO_KINDS),
                 shape="be one of: " + ", ".join(LOGO_KINDS)),
            line("Construction", words=20),
            items("Minimum size", 2, 2, starts=("Full logo", "Mark"),
                  pattern=r"[^:]+: \d+ px high", shape="have the form 'Full logo: N px high'"),
            line("Clear space"),
            items("Never", 3, 3),
        ]),
        "color.md": ("Color", [
            line("Color idea", words=12, headline=True),
            items("Palette", 3, 6, pattern=r".+? - #[0-9A-Fa-f]{6} - .+",
                  shape="have the form 'Name - #RRGGBB - role'"),
            line("Accent is for"),
            line("Accent is never for"),
            items("Contrast", 4, 4, pattern=r".+ on .+: \d+(\.\d)? to 1(, .+)?",
                  shape="have the form 'Color on Color: N to 1'"),
        ]),
        "typography.md": ("Typography", [
            line("Type idea", words=12, headline=True),
            line("Display", pattern=r".+ - .+ - .+",
                 shape="have the form 'Family - weights - role'"),
            line("Text", pattern=r".+ - .+ - .+",
                 shape="have the form 'Family - weights - role'"),
            items("Sizes", 3, 3, starts=("Headline", "Lead", "Body"),
                  pattern=r"[^:]+: \d+ px at 1440, \d+ px at 390",
                  shape="have the form 'Headline: N px at 1440, N px at 390'"),
            line("License"),
        ]),
        "motto.md": ("Motto", [
            line("Motto", words=6, headline=True),
            line("What it says", words=15),
            line("Where it stands"),
            items("Rejected", 1, 3, pattern=r".+ - .+", shape="have the form 'Motto - reason'",
                  optional=True),
        ]),
    },
    "04-design-system": {
        "interface.md": ("Interface", [
            line("Interface idea", words=12, headline=True),
            line("Shape", pattern=r".*\d+ px.*",
                 shape="name the radii in pixels, e.g. 'Controls 6 px, cards 12 px'"),
            line("Depth", pattern=r"(Flat|Ruled|Raised)\b.*",
                 shape="start with Flat, Ruled or Raised"),
            line("Density", pattern=r"\d+ px unit, \d+ px controls.*",
                 shape="have the form '8 px unit, 44 px controls'"),
            line("Motion", words=15),
            items("Never", 3, 3),
        ]),
    },
}

# The order of the sessions of the strategy, the brand platform and the identity.
STRATEGY_TOOLS = list(PLATES["01-strategy"])
PLATFORM_TOOLS = list(PLATES["02-brand-platform"])
IDENTITY_TOOLS = list(PLATES["03-identity"])
DESIGN_TOOLS = list(PLATES["04-design-system"])

# The design system: the tokens every brand has (reference/design-tokens.md, section 4).
_TOKEN_GROUPS = (
    ("color", "color", ("bg", "surface", "border", "control-border", "text", "text-muted",
                        "accent", "accent-hover", "on-accent", "link", "focus", "error",
                        "error-bg", "success", "success-bg", "warning", "warning-bg", "info",
                        "info-bg")),
    ("font", "fontFamily", ("display", "text")),
    ("type", "typography", ("headline", "title", "subtitle", "lead", "body", "small", "label")),
    ("space", "dimension", ("xs", "s", "m", "l", "xl", "section")),
    ("radius", "dimension", ("control", "card", "badge")),
    ("border", "dimension", ("width", "control")),
    ("shadow", "shadow", ("card", "raised")),
    ("size", "dimension", ("control",)),
    ("icon", "dimension", ("size",)),
    ("icon", "number", ("stroke",)),
    ("motion", "duration", ("duration",)),
    ("motion", "cubicBezier", ("easing",)),
    ("layout", "dimension", ("content", "gutter")),
)
REQUIRED_TOKENS = {(group, name): kind for group, kind, names in _TOKEN_GROUPS for name in names}

# The pairs whose contrast is measured in both themes: (color, background, minimum).
TOKEN_PAIRS = [("text", "bg", BODY_CONTRAST), ("text", "surface", BODY_CONTRAST),
               ("text-muted", "bg", BODY_CONTRAST), ("text-muted", "surface", BODY_CONTRAST),
               ("link", "bg", BODY_CONTRAST), ("on-accent", "accent", BODY_CONTRAST),
               ("on-accent", "accent-hover", BODY_CONTRAST), ("error", "bg", BODY_CONTRAST),
               ("error", "error-bg", BODY_CONTRAST), ("success", "success-bg", BODY_CONTRAST),
               ("warning", "warning-bg", BODY_CONTRAST), ("info", "info-bg", BODY_CONTRAST),
               ("control-border", "bg", LARGE_CONTRAST),
               ("control-border", "surface", LARGE_CONTRAST), ("focus", "bg", LARGE_CONTRAST)]

# A control must be at least this high at 390, so a thumb can hit it.
TOUCH_TARGET = 44

# The base set of components.md: section -> components, and the pages with their files.
COMPONENTS = {
    "Atoms": ["Button", "Link", "Text input", "Text area", "Select", "Checkbox", "Radio",
              "Switch", "Badge", "Avatar", "Divider"],
    "Molecules": ["Form field", "Notice", "Card"],
    "Organisms": ["Header", "Hero", "Benefits", "Testimonial", "Call to action",
                  "Sign-in form", "Footer"],
}
COMPONENT_FIELDS = ["For", "States", "Tokens", "At 390", "Accessibility"]
PAGES = {"Landing": "pages/landing.html", "Sign-in": "pages/sign-in.html",
         "Sign-up": "pages/sign-up.html"}
PAGE_FIELDS = ["File", "Uses"]

# Plate files a step may go without: the Name session runs only for an unnamed brand.
OPTIONAL_PLATES = {"02-brand-platform": ("name.md",)}


def _plate_sections(step):
    return {path: (path not in OPTIONAL_PLATES.get(step, ()),
                   [slot["name"] for slot in slots if not slot["optional"]])
            for path, (_title, slots) in PLATES[step].items()}


# Markdown artifacts: step -> {path: (required, [required sections])}
MARKDOWN = {
    "00-intake": dict({"idea.md": (True, ["Idea"])}, **_plate_sections("00-intake")),
    "01-strategy": _plate_sections("01-strategy"),
    "02-brand-platform": dict({"creative-brief.md": (True, [
        "Brand", "Strategy", "Audience", "Character", "Voice", "Mood", "Given", "Constraints",
    ])}, **_plate_sections("02-brand-platform")),
    "03-identity": _plate_sections("03-identity"),
    "04-design-system": dict({"components.md": (True, list(COMPONENTS) + ["Pages"])},
                             **_plate_sections("04-design-system")),
    "05-brand-book": {
        "brand-book.md": (True, [
            "Strategy", "Brand platform", "Identity", "Design system", "How to use this",
        ]),
    },
}

# Other artifacts: step -> {path: kind}. All are required.
# Kinds: file (not empty), svg, json (a JSON object), dir (not empty), png-dir,
# optional-dir (may be absent; when present, a directory that is not empty),
# optional-file (may be absent; when present, a file that is not empty).
OTHER = {
    "02-brand-platform": {"moodboard": "dir", "given": "optional-dir"},
    "03-identity": {
        "logo/full.svg": "svg",
        "logo/mark.svg": "svg",
        "logo/mono.svg": "svg",
        "logo/dark.svg": "svg",
        "fonts": "dir",
        "surfaces": "dir",
    },
    "04-design-system": dict({
        "tokens.json": "json",
        "tokens.css": "file",
        "copy.json": "json",
        "reference/index.html": "file",
        "reference/sheet.html": "file",
        "reference/system.css": "file",
    }, **{"reference/" + path: "file" for path in PAGES.values()}),
    "05-brand-book": {"index.html": "file", "brand-book.pdf": "optional-file"},
}

VERSION_RE = re.compile(r"[0-9a-f]{12}")
NUMBER_RE = re.compile(r"\d+(\.\d+)?")
LANGUAGE_RE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*")
ORDER_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
KEY_LINE_RE = re.compile(r"^( *)([A-Za-z0-9_][A-Za-z0-9_.-]*):(?:[ \t]+(.*))?$")
HEADING_RE = re.compile(r"^(#{1,2})\s+(.*\S)\s*$")
CHOICE_RE = re.compile(r"^(\d+)\. \S")
FIELD_RE = re.compile(r"^- ([A-Za-z][A-Za-z ]*):\s*(.*)$")


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append((path, message))

    def warning(self, path, message):
        self.warnings.append((path, message))


# --- YAML subset -----------------------------------------------------------


class SubsetError(Exception):
    """The text is outside the YAML subset the contract allows."""


def _strip_comment(line):
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"" and (i == 0 or line[i - 1] in " \t"):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def parse_yaml(lines):
    """Parse the contract's YAML subset into nested dicts of strings."""
    root = {}
    stack = [root]
    for number, raw in enumerate(lines, 1):
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        if "\t" in line[: len(line) - len(line.lstrip())]:
            raise SubsetError("line %d: tabs are not allowed in indentation" % number)
        match = KEY_LINE_RE.match(line)
        if not match:
            raise SubsetError("line %d: expected 'key: value'" % number)
        indent, key, value = len(match.group(1)), match.group(2), (match.group(3) or "").strip()
        if indent % 2:
            raise SubsetError("line %d: indentation must be a multiple of two spaces" % number)
        depth = indent // 2
        if depth > len(stack) - 1:
            raise SubsetError("line %d: unexpected indentation" % number)
        del stack[depth + 1:]
        parent = stack[depth]
        if key in parent:
            raise SubsetError("line %d: duplicate key '%s'" % (number, key))
        if not value:
            parent[key] = {}
            stack.append(parent[key])
            continue
        if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
            value = value[1:-1]
        elif value[0] in "[{|>&*!'\"":
            raise SubsetError(
                "line %d: lists, flow syntax, multi-line strings, anchors and tags "
                "are not allowed" % number
            )
        parent[key] = value
    return root


# --- Reading files -----------------------------------------------------------


def read_lines(path):
    with open(path, encoding="utf-8-sig") as handle:
        return handle.read().splitlines()


def visible(names):
    return sorted(name for name in names if not name.startswith("."))


def h2_sections(lines):
    """Return [(heading, [non-blank content lines])] for each second-level heading."""
    sections = []
    current = None
    fenced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
        elif not fenced:
            match = HEADING_RE.match(line)
            if match:
                current = None
                if len(match.group(1)) == 2:
                    current = (match.group(2), [])
                    sections.append(current)
                continue
        if current is not None and stripped:
            current[1].append(stripped)
    return sections


# --- Versions ----------------------------------------------------------------


def step_version(step_dir):
    """Hash a step directory as defined in section 2.3 of the contract."""
    paths = []
    for base, dirs, files in os.walk(step_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if base == step_dir and "review" in dirs:
            dirs.remove("review")
        for name in files:
            if not name.startswith("."):
                full = os.path.join(base, name)
                paths.append((os.path.relpath(full, step_dir).replace(os.sep, "/"), full))
    digest = hashlib.sha256()
    for relative, full in sorted(paths, key=lambda item: item[0].encode("utf-8")):
        with open(full, "rb") as handle:
            file_digest = hashlib.sha256(handle.read()).hexdigest()
        digest.update(relative.encode("utf-8") + b"\0" + file_digest.encode("ascii") + b"\n")
    return digest.hexdigest()[:12]


# --- pipeline.yaml -----------------------------------------------------------


def check_pipeline(data, report):
    """Validate pipeline.yaml. Return {step: {status, version, built_on}} with valid values only."""
    path = "pipeline.yaml"

    def unknown_keys(mapping, allowed, where):
        for key in mapping:
            if key not in allowed:
                report.error(path, "unknown key '%s%s'" % (where, key))

    def scalar(mapping, key, where, allowed=None, pattern=None, expected=None):
        value = mapping.get(key)
        if value is None:
            report.error(path, "missing key '%s%s'" % (where, key))
            return None
        if isinstance(value, dict):
            report.error(path, "'%s%s' must have a value" % (where, key))
            return None
        if allowed is not None and value not in allowed:
            report.error(path, "'%s%s' is '%s'; must be one of: %s"
                         % (where, key, value, ", ".join(allowed)))
            return None
        if pattern is not None and not pattern.fullmatch(value):
            report.error(path, "'%s%s' is '%s'; must be %s" % (where, key, value, expected))
            return None
        return value

    def mapping_at(parent, key, where):
        value = parent.get(key)
        if value is None:
            report.error(path, "missing key '%s%s'" % (where, key))
            return {}
        if not isinstance(value, dict):
            report.error(path, "'%s%s' must be a mapping" % (where, key))
            return {}
        return value

    unknown_keys(data, ("order", "profile", "market_language", "tools", "budget", "steps"), "")
    if "order" in data:
        scalar(data, "order", "", pattern=ORDER_RE,
               expected="the name of the order: a-z, 0-9 and inner '-'")
    scalar(data, "profile", "", allowed=PROFILES)
    scalar(data, "market_language", "", pattern=LANGUAGE_RE,
           expected="a BCP 47 language tag such as 'uk' or 'en-US'")

    tools = mapping_at(data, "tools", "")
    unknown_keys(tools, TOOLS, "tools.")
    for key, allowed in TOOLS.items():
        scalar(tools, key, "tools.", allowed=allowed)

    budget = mapping_at(data, "budget", "")
    unknown_keys(budget, ("limit",), "budget.")
    limit = scalar(budget, "limit", "budget.", pattern=NUMBER_RE,
                   expected="a non-negative number")

    steps = mapping_at(data, "steps", "")
    unknown_keys(steps, STEPS, "steps.")
    state = {}
    total_spent = 0.0
    spent_known = True
    for index, step in enumerate(STEPS):
        where = "steps.%s." % step
        entry = mapping_at(steps, step, "steps.")
        earlier = STEPS[:index]
        unknown_keys(entry, ("status", "version", "built_on", "spent"), where)
        status = scalar(entry, "status", where, allowed=STEP_STATUSES)

        version = None
        if "version" in entry:
            version = scalar(entry, "version", where, pattern=VERSION_RE,
                             expected="12 lowercase hex characters")
            if status == "pending":
                report.error(path, "'%sversion' must be absent while the step is pending" % where)
        elif status in ("approved", "stale", "skipped"):
            report.error(path, "missing key '%sversion' (required when the step is %s)"
                         % (where, status))

        built_on = {}
        if "built_on" in entry:
            raw = entry["built_on"]
            if not isinstance(raw, dict):
                report.error(path, "'%sbuilt_on' must be a mapping" % where)
                raw = {}
            if status == "pending":
                report.error(path, "'%sbuilt_on' must be absent while the step is pending" % where)
            for key in raw:
                if key not in earlier:
                    report.error(path, "'%sbuilt_on.%s' is not an earlier step" % (where, key))
                else:
                    value = scalar(raw, key, where + "built_on.", pattern=VERSION_RE,
                                   expected="12 lowercase hex characters")
                    if value:
                        built_on[key] = value
        if status in ("approved", "stale"):
            for key in earlier:
                if key not in entry.get("built_on", {}):
                    report.error(path, "missing key '%sbuilt_on.%s' (required when the step is %s)"
                                 % (where, key, status))

        spent = scalar(entry, "spent", where, pattern=NUMBER_RE, expected="a non-negative number")
        if spent is None:
            spent_known = False
        else:
            total_spent += float(spent)

        state[step] = {"status": status, "version": version, "built_on": built_on}

    if limit is not None and spent_known and total_spent > float(limit) + 1e-9:
        report.error(path, "total spent (%.2f) exceeds 'budget.limit' (%.2f)"
                     % (total_spent, float(limit)))

    for index, step in enumerate(STEPS):
        if state[step]["status"] != "approved":
            continue
        for earlier in STEPS[:index]:
            earlier_status = state[earlier]["status"]
            if earlier_status is not None and earlier_status not in ("approved", "skipped"):
                report.error(path, "'steps.%s' is approved but the earlier step '%s' is %s"
                             % (step, earlier, earlier_status))
    return state


# --- Files in a step ---------------------------------------------------------


def check_sections(path, lines, required, report):
    sections = h2_sections(lines)
    names = [name for name, _ in sections]
    for name in required:
        if name not in names:
            report.error(path, "missing section '## %s'" % name)
        elif not any(content for found, content in sections if found == name):
            report.error(path, "section '## %s' is empty" % name)


def plate_values(lines, slots):
    """Read a plate from the body of a tool file: {slot name: [lines or list items]}."""
    found = {}
    for name, content in h2_sections(lines):
        found.setdefault(name, content)
    values = {}
    for slot in slots:
        content = found.get(slot["name"])
        if content is None:
            continue
        if slot["kind"] == "list":
            content = [item[2:].strip() if item.startswith("- ") else item for item in content]
        values[slot["name"]] = content
    return values


def check_plate(path, lines, slots, report):
    """Check the slots of a plate: one line or a list, the counts, the word limits, the shape."""
    found = {}
    for name, content in h2_sections(lines):
        found.setdefault(name, content)
    for slot in slots:
        content = found.get(slot["name"])
        if not content:
            continue  # a missing or empty section is reported by check_sections
        where = "plate slot '## %s'" % slot["name"]
        if slot["kind"] == "line":
            if len(content) != 1 or content[0].startswith("- "):
                report.error(path, "%s must be exactly one line, not a list" % where)
                continue
            entries = content
        else:
            if any(not item.startswith("- ") for item in content):
                report.error(path, "%s must be a list; every line starts with '- '" % where)
                continue
            if not slot["low"] <= len(content) <= slot["high"]:
                expected = ("exactly %d" % slot["low"] if slot["low"] == slot["high"]
                            else "%d to %d" % (slot["low"], slot["high"]))
                report.error(path, "%s has %d items; must have %s"
                             % (where, len(content), expected))
            entries = [item[2:].strip() for item in content]
            for entry, label in zip(entries, slot["starts"] or ()):
                if not entry.replace("–", "-").startswith(label.replace("–", "-") + ":"):
                    report.error(path, "%s: '%s' must start with '%s:'; the lines are %s, "
                                 "in this order" % (where, entry, label,
                                                    ", ".join(slot["starts"])))
        for entry in entries:
            count = len(entry.split())
            if slot["words"] is not None and count > slot["words"]:
                report.error(path, "%s: '%s' has %d words; the limit is %d"
                             % (where, entry, count, slot["words"]))
            if slot["min_words"] is not None and count < slot["min_words"]:
                report.error(path, "%s: '%s' has %d words; the minimum is %d"
                             % (where, entry, count, slot["min_words"]))
            if slot["pattern"] and not re.fullmatch(slot["pattern"], entry):
                report.error(path, "%s: '%s' must %s" % (where, entry, slot["shape"]))


def check_markdown_artifact(brand, step, relative, required, forbid_draft, report):
    path = "%s/%s" % (step, relative)
    try:
        lines = read_lines(os.path.join(brand, step, relative))
    except (OSError, UnicodeDecodeError) as error:
        report.error(path, "cannot be read: %s" % error)
        return

    body = lines
    if not lines or lines[0].strip() != "---":
        report.error(path, "missing frontmatter")
    else:
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            report.error(path, "frontmatter is not closed with '---'")
            body = []
        else:
            body = lines[end + 1:]
            check_frontmatter(path, step, lines[1:end], forbid_draft, report)
    check_sections(path, body, required, report)
    plate = PLATES.get(step, {}).get(relative)
    if plate:
        check_plate(path, body, plate[1], report)


def check_frontmatter(path, step, lines, forbid_draft, report):
    try:
        fields = parse_yaml(lines)
    except SubsetError as error:
        report.error(path, "frontmatter: %s" % error)
        return
    for key in fields:
        if key not in ("step", "status", "source"):
            report.error(path, "frontmatter: unknown key '%s'" % key)

    def field(key):
        value = fields.get(key)
        if value is None:
            report.error(path, "frontmatter: missing key '%s'" % key)
        elif isinstance(value, dict):
            report.error(path, "frontmatter: '%s' must have a value" % key)
            return None
        return value

    value = field("step")
    if value is not None and value != step:
        report.error(path, "frontmatter: 'step' is '%s'; must be '%s'" % (value, step))

    status = field("status")
    allowed = ARTIFACT_STATUSES
    if status is not None:
        if status not in allowed:
            report.error(path, "frontmatter: 'status' is '%s'; must be one of: %s"
                         % (status, ", ".join(allowed)))
        elif status == "draft" and forbid_draft:
            report.error(path, "frontmatter: 'status' is 'draft' in a step that is approved")

    source = field("source")
    if source is not None and source not in SOURCES:
        report.error(path, "frontmatter: 'source' is '%s'; must be one of: %s"
                     % (source, ", ".join(SOURCES)))


def check_summary(brand, step, report):
    path = "%s/summary.md" % step
    try:
        lines = read_lines(os.path.join(brand, step, "summary.md"))
    except (OSError, UnicodeDecodeError) as error:
        report.error(path, "cannot be read: %s" % error)
        return
    if lines and lines[0].strip() == "---":
        report.error(path, "must not have frontmatter")
    sections = h2_sections(lines)
    names = [name for name, _ in sections]
    if names != SUMMARY_SECTIONS:
        report.error(path, "sections must be exactly, in this order: %s (found: %s)"
                     % (", ".join(SUMMARY_SECTIONS), ", ".join(names) or "none"))
    for name, content in sections:
        if name in SUMMARY_SECTIONS and not content:
            report.error(path, "section '## %s' is empty; write 'None.' if there is nothing"
                         % name)


def check_decisions(brand, step, strict, report):
    path = "%s/review/decisions.md" % step
    review_dir = os.path.join(brand, step, "review")
    try:
        lines = read_lines(os.path.join(review_dir, "decisions.md"))
    except (OSError, UnicodeDecodeError) as error:
        report.error(path, "cannot be read: %s" % error)
        return
    if lines and lines[0].strip() == "---":
        report.error(path, "must not have frontmatter")
    sections = h2_sections(lines)
    has_open = False
    for index, (heading, content) in enumerate(sections, 1):
        match = CHOICE_RE.match(heading)
        if not match:
            report.error(path, "heading '## %s' must have the form '## <number>. <name>'"
                         % heading)
        elif int(match.group(1)) != index:
            report.error(path, "choice '## %s' is out of sequence; expected number %d"
                         % (heading, index))
        fields = [m.groups() for m in (FIELD_RE.match(line) for line in content) if m]
        if [key for key, _ in fields] != DECISION_FIELDS:
            report.error(path, "choice '## %s' must have exactly the lines %s, in this order"
                         % (heading, ", ".join(DECISION_FIELDS)))
            continue
        values = dict(fields)
        page = values["Page"].strip()
        if not page:
            report.error(path, "choice '## %s': 'Page' is empty" % heading)
        elif not os.path.isfile(os.path.join(review_dir, page)):
            report.error(path, "choice '## %s': page '%s' does not exist in review/"
                         % (heading, page))
        if not values["Decision"].strip():
            report.error(path, "choice '## %s': 'Decision' is empty" % heading)
        status = values["Status"].strip()
        if status not in ("open", "fixed"):
            report.error(path, "choice '## %s': 'Status' is '%s'; must be one of: open, fixed"
                         % (heading, status))
        has_open = has_open or status == "open"
    if strict:
        if not sections:
            report.error(path, "has no choices")
        if has_open:
            report.error(path, "has a choice that is still open")


def check_other(brand, step, relative, kind, strict, report):
    path = "%s/%s" % (step, relative)
    full = os.path.join(brand, step, relative)
    is_dir_kind = kind in ("dir", "png-dir", "optional-dir")
    if not os.path.lexists(full):
        if strict and kind not in ("optional-dir", "optional-file"):
            report.error(path + ("/" if is_dir_kind else ""), "missing")
        return
    if is_dir_kind:
        if not os.path.isdir(full):
            report.error(path, "must be a directory")
            return
        entries = visible(os.listdir(full))
        if not entries and (strict or kind == "optional-dir"):
            report.error(path + "/", "is empty")
        if kind == "png-dir":
            for name in entries:
                if not name.endswith(".png") or not os.path.isfile(os.path.join(full, name)):
                    report.error("%s/%s" % (path, name), "only .png files are allowed here")
        return
    if not os.path.isfile(full):
        report.error(path, "must be a file")
        return
    try:
        with open(full, "rb") as handle:
            content = handle.read()
    except OSError as error:
        report.error(path, "cannot be read: %s" % error)
        return
    if not content.strip():
        report.error(path, "is empty")
    elif kind == "svg" and b"<svg" not in content:
        report.error(path, "is not an SVG document")
    elif kind == "json":
        try:
            parsed = json.loads(content.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as error:
            report.error(path, "is not valid JSON: %s" % error)
        else:
            if not isinstance(parsed, dict):
                report.error(path, "must be a JSON object")


def check_step(brand, step, state, forced, report):
    status = state[step]["status"]
    strict = forced or status in ("approved", "stale")
    forbid_draft = status in ("approved", "stale")
    step_dir = os.path.join(brand, step)

    if not os.path.isdir(step_dir):
        if strict or status == "skipped":
            report.error(step + "/", "missing")
        return

    markdown = MARKDOWN.get(step, {})
    other = OTHER.get(step, {})
    allowed = {"summary.md", "review"}
    allowed.update(relative.split("/")[0] for relative in list(markdown) + list(other))
    for name in visible(os.listdir(step_dir)):
        if name not in allowed:
            report.error("%s/%s" % (step, name), "is not part of the contract")

    for relative, (required, sections) in markdown.items():
        if os.path.isfile(os.path.join(step_dir, relative)):
            check_markdown_artifact(brand, step, relative, sections, forbid_draft, report)
        elif required and strict:
            report.error("%s/%s" % (step, relative), "missing")

    for relative, kind in other.items():
        check_other(brand, step, relative, kind, strict, report)

    if os.path.isfile(os.path.join(step_dir, "summary.md")):
        check_summary(brand, step, report)
    elif strict or status == "skipped":
        report.error("%s/summary.md" % step, "missing")

    choice_made = True
    if step == "02-brand-platform":
        choice_made = check_platform(brand, strict, report)
    if step == "03-identity":
        check_identity(brand, report)
    if step == "04-design-system":
        check_design(brand, report)

    if os.path.isfile(os.path.join(step_dir, "review", "decisions.md")):
        check_decisions(brand, step, strict, report)
    elif strict and step in REVIEW_STEPS and choice_made:
        report.error("%s/review/decisions.md" % step, "missing")


def read_plate(brand, step, name):
    """Return (frontmatter fields, {slot: [values]}) of a plate file, or None when it cannot
    be read. Malformed content is reported by check_markdown_artifact, not here."""
    try:
        lines = read_lines(os.path.join(brand, step, name))
    except (OSError, UnicodeDecodeError):
        return None
    fields, body = {}, lines
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            body = lines[end + 1:]
            try:
                fields = parse_yaml(lines[1:end])
            except SubsetError:
                fields = {}
    if not isinstance(fields, dict):
        fields = {}
    return fields, plate_values(body, PLATES[step][name][1])


def _one(values, slot):
    content = values.get(slot) or [""]
    return content[0].strip()


def check_platform(brand, strict, report):
    """The rules of 02-brand-platform that span slots or files. Return False when the Mood
    session was the short one (everything given), which makes no choice on a choice page."""
    step = "02-brand-platform"
    archetype = read_plate(brand, step, "archetype.md")
    if archetype:
        primary = _one(archetype[1], "Primary archetype")
        if primary and primary == _one(archetype[1], "Secondary archetype"):
            report.error("%s/archetype.md" % step,
                         "the primary and the secondary archetype must differ")

    if strict:
        brief = read_plate(brand, "00-intake", "brief.md")
        brand_name = _one(brief[1], "Brand") if brief else ""
        name = read_plate(brand, step, "name.md")
        if name is None:
            if brand_name == "Unnamed":
                report.error("%s/name.md" % step,
                             "missing: The Brief says 'Unnamed', so the brand is named here")
        elif name[0].get("status") == "approved" and brand_name != _one(name[1], "Name"):
            report.error("%s/name.md" % step,
                         "'## Brand' in 00-intake/brief.md is '%s'; it must be the name '%s'"
                         % (brand_name, _one(name[1], "Name")))

    mood = read_plate(brand, step, "mood.md")
    return not (mood and mood[0].get("source") == "provided")


def parse_palette(values):
    """Read the lines of a Palette slot: [{name, hex, roles}]. Raise ValueError when a line
    has no shape or the roles do not add up."""
    palette = []
    for value in values:
        match = re.fullmatch(r"(.+?) - (#[0-9A-Fa-f]{6}) - (.+)", value.strip())
        if not match:
            raise ValueError("'%s' must have the form 'Name - #RRGGBB - role'" % value)
        roles = [role.strip() for role in match.group(3).split(",")]
        for role in roles:
            if role not in PALETTE_ROLES:
                raise ValueError("'%s' has the role '%s'; a role is one of: %s"
                                 % (match.group(1), role, ", ".join(PALETTE_ROLES)))
        palette.append({"name": match.group(1).strip(), "hex": match.group(2).upper(),
                        "roles": roles})
    for role in THEME_ROLES + ("accent",):
        count = sum(color["roles"].count(role) for color in palette)
        if count != 1:
            raise ValueError("the role '%s' is given %d times; exactly one color must carry it"
                             % (role, count))
    if sum(color["roles"].count("secondary") for color in palette) > 1:
        raise ValueError("the role 'secondary' is given more than once")
    return palette


def luminance(hex_color):
    """The relative luminance of '#RRGGBB' (WCAG 2)."""
    total = 0.0
    for offset, weight in ((1, 0.2126), (3, 0.7152), (5, 0.0722)):
        channel = int(hex_color[offset:offset + 2], 16) / 255
        total += weight * (channel / 12.92 if channel <= 0.04045
                           else ((channel + 0.055) / 1.055) ** 2.4)
    return total


def contrast(first, second):
    """The contrast ratio of two '#RRGGBB' colors, from 1 to 21."""
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def palette_pairs(palette):
    """The four pairs the Contrast slot reports: [(color, background, is body text)]."""
    by_role = {role: color for color in palette for role in color["roles"]}
    return [(by_role["text on light"], by_role["background on light"], True),
            (by_role["text on dark"], by_role["background on dark"], True),
            (by_role["accent"], by_role["background on light"], False),
            (by_role["accent"], by_role["background on dark"], False)]


def contrast_lines(palette):
    """The lines of the Contrast slot for a parsed palette."""
    lines = []
    for color, background, body in palette_pairs(palette):
        ratio = contrast(color["hex"], background["hex"])
        number = ("%.1f" % ratio).rstrip("0").rstrip(".")
        note = ""
        if not body and ratio < LARGE_CONTRAST:
            note = ", not for text"
        elif not body and ratio < BODY_CONTRAST:
            note = ", large text only"
        lines.append("%s on %s: %s to 1%s" % (color["name"], background["name"], number, note))
    return lines


def weak_body_text(palette):
    """Messages for the themes in which body text does not reach BODY_CONTRAST."""
    problems = []
    for color, background, body in palette_pairs(palette):
        ratio = contrast(color["hex"], background["hex"])
        if body and ratio < BODY_CONTRAST:
            problems.append("%s on %s is %.2f to 1; body text must reach %s to 1"
                            % (color["name"], background["name"], ratio, BODY_CONTRAST))
    return problems


def check_identity(brand, report):
    """The rules of 03-identity that span slots: the palette and its contrast."""
    step = "03-identity"
    path = "%s/color.md" % step
    color = read_plate(brand, step, "color.md")
    if not color or not color[1].get("Palette"):
        return
    try:
        palette = parse_palette(color[1]["Palette"])
    except ValueError as error:
        report.error(path, "plate slot '## Palette': %s" % error)
        return
    for problem in weak_body_text(palette):
        report.error(path, "plate slot '## Palette': %s" % problem)
    found = color[1].get("Contrast")
    expected = contrast_lines(palette)
    if found and found != expected:
        for have, want in zip(found, expected):
            if have != want:
                report.error(path, "plate slot '## Contrast': '%s' does not follow from the "
                                   "palette; it must be '%s'" % (have, want))


# --- The design system -------------------------------------------------------


def load_tokens(path):
    """Read a tokens file: ({path tuple: (type, value)}, the parsed JSON, [problems])."""
    with open(path, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    tokens, problems = {}, []
    if not isinstance(data, dict):
        return tokens, data, ["the file must be a JSON object"]
    bt.collect(data, (), None, tokens, problems)
    return tokens, data, problems


def resolve(tokens, path, dark=False, narrow=False):
    """The (type, value) of a token in a theme and at a width, through overrides and aliases.
    Raise KeyError when it does not exist."""
    seen = set()
    while True:
        entry = None
        for group, on in ((bt.NARROW, narrow), (bt.DARK, dark)):
            if on and (group,) + path in tokens:
                entry = tokens[(group,) + path]
                break
        if entry is None:
            entry = tokens[path]
        kind, value = entry
        match = bt.ALIAS_RE.match(value) if isinstance(value, str) else None
        if not match:
            return kind, value
        if path in seen:
            raise KeyError(path)
        seen.add(path)
        path = tuple(match.group(1).split("."))


def token_hex(tokens, name, dark=False):
    """'#RRGGBB' of the color role color.<name>. Raise ValueError when it is not a plain,
    opaque sRGB color."""
    kind, value = resolve(tokens, ("color", name), dark)
    components = value.get("components") if isinstance(value, dict) else None
    if kind != "color" or not isinstance(components, list) or len(components) != 3 \
            or not all(bt.is_number(c) for c in components):
        raise ValueError("color.%s is not a color" % name)
    if value.get("alpha", 1) != 1:
        raise ValueError("color.%s is translucent; a role color must be opaque" % name)
    return "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in components)


def token_px(tokens, path, narrow=False):
    """The size of a dimension token in pixels (1 rem = 16 px), or None."""
    try:
        kind, value = resolve(tokens, path, narrow=narrow)
    except KeyError:
        return None
    if kind != "dimension" or not isinstance(value, dict) or not bt.is_number(value.get("value")):
        return None
    return value["value"] * (16 if value.get("unit") == "rem" else 1)


def missing_tokens(tokens):
    """Messages for the required tokens that are absent or of another type."""
    problems = []
    for path, kind in REQUIRED_TOKENS.items():
        if path not in tokens:
            problems.append("missing token '%s' (%s)" % (".".join(path), kind))
        elif tokens[path][0] != kind:
            problems.append("'%s' is a %s; it must be a %s"
                            % (".".join(path), tokens[path][0], kind))
    return problems


def token_contrast(tokens):
    """[(text, ratio, minimum)] for every pair of TOKEN_PAIRS in both themes. Raise
    ValueError when a role is not an opaque color."""
    rows = []
    for theme, dark in (("light", False), ("dark", True)):
        for color, background, minimum in TOKEN_PAIRS:
            ratio = contrast(token_hex(tokens, color, dark), token_hex(tokens, background, dark))
            rows.append(("color.%s on color.%s, %s: %s to 1"
                         % (color, background, theme, ("%.1f" % ratio).rstrip("0").rstrip(".")),
                         ratio, minimum))
    return rows


def weak_tokens(tokens):
    return ["%s; it must reach %s to 1" % (text, ("%.1f" % minimum).rstrip("0").rstrip("."))
            for text, ratio, minimum in token_contrast(tokens) if ratio < minimum]


def identity_agreement(brand, tokens):
    """Messages for the tokens that change what the identity fixed."""
    problems = []
    color = read_plate(brand, "03-identity", "color.md")
    try:
        palette = parse_palette(color[1].get("Palette", [])) if color else None
    except ValueError:
        palette = None
    if palette:
        role = {name: c["hex"] for c in palette for name in c["roles"]}
        for token, fixed, dark in (("bg", "background on light", False),
                                   ("text", "text on light", False),
                                   ("accent", "accent", False),
                                   ("bg", "background on dark", True),
                                   ("text", "text on dark", True),
                                   ("accent", "accent", True)):
            try:
                have = token_hex(tokens, token, dark)
            except (KeyError, ValueError):
                continue
            if have != role[fixed]:
                problems.append("color.%s is %s in the %s theme; the identity fixed %s (%s)"
                                % (token, have, "dark" if dark else "light", role[fixed], fixed))
    typography = read_plate(brand, "03-identity", "typography.md")
    if typography:
        values = typography[1]
        for token, slot in (("display", "Display"), ("text", "Text")):
            fixed = _one(values, slot).split(" - ")[0].strip()
            try:
                kind, value = resolve(tokens, ("font", token))
            except KeyError:
                continue
            first = value[0] if isinstance(value, list) and value else value
            if fixed and isinstance(first, str) and first.strip() != fixed:
                problems.append("font.%s starts with '%s'; the identity fixed '%s'"
                                % (token, first, fixed))
        for size in values.get("Sizes", []):
            match = re.fullmatch(r"(\w+): (\d+) px at 1440, (\d+) px at 390", size.strip())
            if not match:
                continue
            name = match.group(1).lower()
            for narrow, fixed in ((False, match.group(2)), (True, match.group(3))):
                try:
                    kind, value = resolve(tokens, ("type", name), narrow=narrow)
                    have = value["fontSize"]
                    if isinstance(have, str):
                        have = resolve(tokens, tuple(have.strip("{}").split(".")), narrow=narrow)[1]
                    pixels = have["value"] * (16 if have.get("unit") == "rem" else 1)
                except (KeyError, TypeError, AttributeError):
                    continue
                if pixels != int(fixed):
                    problems.append("type.%s is %s px at %s; the identity fixed %s px"
                                    % (name, bt.num(pixels), "390" if narrow else "1440", fixed))
    return problems


def check_design(brand, report):
    """The rules of 04-design-system that span files: the tokens, their contrast, their
    agreement with the identity, tokens.css, and the shape of components.md."""
    step = "04-design-system"
    path = "%s/tokens.json" % step
    try:
        tokens, data, problems = load_tokens(os.path.join(brand, step, "tokens.json"))
    except (OSError, ValueError):
        return  # reported by check_other
    if problems:
        for problem in problems:
            report.error(path, problem)
        return
    missing = missing_tokens(tokens)
    for problem in missing:
        report.error(path, problem)
    try:
        css = bt.build(data)
    except bt.Problem as error:
        for problem in error.args[0]:
            report.error(path, problem)
        css = None
    if css is not None:
        try:
            with open(os.path.join(brand, step, "tokens.css"), encoding="utf-8") as handle:
                if handle.read() != css:
                    report.error("%s/tokens.css" % step, "is out of date; run build_tokens.py "
                                 "on tokens.json")
        except (OSError, UnicodeDecodeError):
            pass
    if missing:
        check_components(brand, tokens, report)
        return
    try:
        for problem in weak_tokens(tokens):
            report.error(path, problem)
    except (KeyError, ValueError) as error:
        report.error(path, str(error))
    control = token_px(tokens, ("size", "control"), narrow=True)
    if control is not None and control < TOUCH_TARGET:
        report.error(path, "size.control is %s px at 390; a control must be at least %d px high"
                     % (bt.num(control), TOUCH_TARGET))
    for problem in identity_agreement(brand, tokens):
        report.error(path, problem)
    check_components(brand, tokens, report)


COMPONENT_FIELD_RE = re.compile(r"^- ([A-Za-z][A-Za-z0-9 ]*):\s*(.*)$")


def h3_blocks(content):
    """[(heading, [lines])] for the '### ' headings in the content of a section."""
    blocks = []
    for entry in content:
        if entry.startswith("### "):
            blocks.append((entry[4:].strip(), []))
        elif blocks:
            blocks[-1][1].append(entry)
    return blocks


def check_components(brand, tokens, report):
    step = "04-design-system"
    path = "%s/components.md" % step
    try:
        lines = read_lines(os.path.join(brand, step, "components.md"))
    except (OSError, UnicodeDecodeError):
        return
    sections = dict((name, content) for name, content in h2_sections(lines))
    for section, names in list(COMPONENTS.items()) + [("Pages", list(PAGES))]:
        fields_wanted = PAGE_FIELDS if section == "Pages" else COMPONENT_FIELDS
        blocks = h3_blocks(sections.get(section, []))
        found = [name for name, _ in blocks]
        for name in names:
            if name not in found:
                report.error(path, "missing '### %s' under '## %s'" % (name, section))
        for name, block in blocks:
            fields = [m.groups() for m in (COMPONENT_FIELD_RE.match(e) for e in block) if m]
            if [key for key, _ in fields] != fields_wanted:
                report.error(path, "'### %s' must have exactly the lines %s, in this order"
                             % (name, ", ".join(fields_wanted)))
                continue
            values = dict(fields)
            for key, value in fields:
                if not value.strip():
                    report.error(path, "'### %s': '%s' is empty" % (name, key))
            if section == "Pages":
                target = values["File"].strip().strip("`")
                if target and not os.path.isfile(os.path.join(brand, step, "reference", target)):
                    report.error(path, "'### %s': the page 'reference/%s' does not exist"
                                 % (name, target))
                continue
            for token in values["Tokens"].split(","):
                token = token.strip().strip("`").strip()
                if not token:
                    continue
                parts = tuple(token.split("."))
                if parts[0] == "palette":
                    report.error(path, "'### %s': '%s' is a primitive; a component uses role "
                                       "tokens" % (name, token))
                elif parts[0] in bt.OVERRIDES:
                    report.error(path, "'### %s': name '%s' without '%s.'; the override "
                                       "applies by itself" % (name, token, parts[0]))
                elif parts not in tokens:
                    report.error(path, "'### %s': there is no token '%s' in tokens.json"
                                 % (name, token))


def check_versions(brand, step, state, report):
    """Warn when an approved step no longer matches the recorded versions."""
    entry = state[step]
    if entry["status"] != "approved":
        return
    step_dir = os.path.join(brand, step)
    if entry["version"] and os.path.isdir(step_dir):
        actual = step_version(step_dir)
        if actual != entry["version"]:
            report.warning(step + "/", "changed since approval (recorded version %s, current %s)"
                           % (entry["version"], actual))
    for earlier, recorded in entry["built_on"].items():
        current = state[earlier]["version"]
        if current and current != recorded:
            report.warning(step + "/", "built on an older version of %s (built on %s, current %s)"
                           % (earlier, recorded, current))


# --- Entry points ------------------------------------------------------------


class Unreadable(Exception):
    """brand/ or pipeline.yaml cannot be read at all."""


def check(brand, only_step=None):
    """Check brand/ and return a Report. Raise Unreadable when there is nothing to check."""
    if not os.path.isdir(brand):
        raise Unreadable("%s is not a directory" % brand)
    try:
        lines = read_lines(os.path.join(brand, "pipeline.yaml"))
    except (OSError, UnicodeDecodeError) as error:
        raise Unreadable("pipeline.yaml cannot be read: %s" % error)

    report = Report()
    try:
        data = parse_yaml(lines)
    except SubsetError as error:
        report.error("pipeline.yaml", str(error))
        return report

    state = check_pipeline(data, report)
    for step in ([only_step] if only_step else STEPS):
        check_step(brand, step, state, step == only_step, report)
        check_versions(brand, step, state, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check a brand/ directory against the artifact contract.")
    commands = parser.add_subparsers(dest="command", required=True)
    check_parser = commands.add_parser("check", help="check brand/ against the contract")
    check_parser.add_argument("--step", choices=STEPS, metavar="STEP",
                              help="check only this step, as strictly as an approved step")
    check_parser.add_argument("brand", nargs="?", default="brand", help="path to brand/")
    hash_parser = commands.add_parser("hash", help="print the version of a step")
    hash_parser.add_argument("step", choices=STEPS, metavar="STEP")
    hash_parser.add_argument("brand", nargs="?", default="brand", help="path to brand/")
    contrast_parser = commands.add_parser(
        "contrast", help="print the Contrast lines of a palette; exit 1 if it cannot be used")
    contrast_parser.add_argument("lines", nargs="+", metavar="LINE",
                                 help="a palette line: 'Name - #RRGGBB - role[, role]'")
    tokens_parser = commands.add_parser(
        "tokens", help="print the contrast of the color roles of a tokens file; exit 1 if a "
                       "role is missing or a pair is too weak")
    tokens_parser.add_argument("tokens", help="path to tokens.json")
    args = parser.parse_args(argv)

    if args.command == "tokens":
        try:
            tokens, _data, problems = load_tokens(args.tokens)
        except (OSError, ValueError) as error:
            print("cannot read %s: %s" % (args.tokens, error), file=sys.stderr)
            return 2
        problems = problems or missing_tokens(tokens)
        if not problems:
            try:
                for text, ratio, minimum in token_contrast(tokens):
                    print("- " + text)
                problems = weak_tokens(tokens)
            except (KeyError, ValueError) as error:
                problems = [str(error)]
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0

    if args.command == "contrast":
        try:
            palette = parse_palette(args.lines)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 1
        for text in contrast_lines(palette):
            print("- " + text)
        problems = weak_body_text(palette)
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0

    if args.command == "hash":
        step_dir = os.path.join(args.brand, args.step)
        if not os.path.isdir(step_dir):
            print("%s is not a directory" % step_dir, file=sys.stderr)
            return 2
        print(step_version(step_dir))
        return 0

    try:
        report = check(args.brand, args.step)
    except Unreadable as error:
        print(error, file=sys.stderr)
        return 2
    for path, message in report.errors:
        print("ERROR   %s: %s" % (path, message))
    for path, message in report.warnings:
        print("WARNING %s: %s" % (path, message))
    print("%d error(s), %d warning(s)" % (len(report.errors), len(report.warnings)))
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
