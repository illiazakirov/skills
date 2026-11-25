#!/usr/bin/env python3
"""Build tokens.css from a design tokens file in W3C DTCG format.

    build_tokens.py <tokens.json>            write tokens.css beside it
    build_tokens.py <tokens.json> --check    change nothing; fail if tokens.css is out of date

tokens.json is the single source; tokens.css is always generated, never edited.
The format and the conventions are described in reference/design-tokens.md. In short:

- values follow the DTCG format module 2025.10: a color is an object with colorSpace
  "srgb" and components, a dimension is {"value": 16, "unit": "px"};
- a token becomes the CSS custom property named by its path: color.bg -> --color-bg;
- the top-level group "dark" holds the dark theme: dark.color.bg overrides color.bg
  under :root[data-theme="dark"];
- the top-level group "narrow" holds what differs at 600 px wide and below:
  narrow.type.body overrides type.body under @media (max-width: 600px);
- "{color.bg}" refers to another token and becomes var(--color-bg).

No dependencies beyond the Python 3 standard library.

Exit codes: 0 done or up to date, 1 the tokens break a rule or tokens.css is out of
date, 2 the file cannot be read.
"""

import json
import os
import re
import sys

DARK = "dark"
NARROW = "narrow"
OVERRIDES = (DARK, NARROW)
NARROW_MEDIA = "(max-width: 600px)"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALIAS_RE = re.compile(r"^\{([^{}]+)\}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
WEIGHTS = {"thin": 100, "hairline": 100, "extra-light": 200, "ultra-light": 200, "light": 300,
           "normal": 400, "regular": 400, "book": 400, "medium": 500, "semi-bold": 600,
           "demi-bold": 600, "bold": 700, "extra-bold": 800, "ultra-bold": 800, "black": 900,
           "heavy": 900, "extra-black": 950, "ultra-black": 950}
GENERIC_FAMILIES = ("serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
                    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "math")
TYPES = ("color", "dimension", "duration", "fontFamily", "fontWeight", "number",
         "cubicBezier", "shadow", "typography")
HEADER = "/* Generated from tokens.json by build_tokens.py. Do not edit; edit tokens.json. */\n"


class Problem(Exception):
    pass


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def num(value):
    return ("%.4f" % value).rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


def collect(node, path, inherited, tokens, problems):
    """Walk the groups and fill tokens: {path tuple: (type, value)} in document order."""
    if not isinstance(node, dict):
        problems.append("%s: a group must be an object" % ".".join(path))
        return
    if "$ref" in node:
        problems.append("%s: '$ref' is not supported; use \"{group.token}\"" % ".".join(path))
    kind = node.get("$type", inherited)
    if "$value" in node:
        if not path:
            problems.append("the file itself cannot be a token")
        elif kind is None:
            problems.append("%s: no '$type' on the token or on a group above it" % ".".join(path))
        elif kind not in TYPES:
            problems.append("%s: type '%s' is not supported; use one of %s"
                            % (".".join(path), kind, ", ".join(TYPES)))
        else:
            tokens[path] = (kind, node["$value"])
        for key in node:
            if not key.startswith("$"):
                problems.append("%s: a token cannot contain the group or token '%s'"
                                % (".".join(path), key))
        return
    for key, child in node.items():
        if key.startswith("$"):
            continue
        if not NAME_RE.match(key):
            problems.append("%s: names use lowercase letters, digits and hyphens, so that "
                            "they can become CSS property names" % ".".join(path + (key,)))
            continue
        collect(child, path + (key,), kind, tokens, problems)


def css_name(path):
    return "--" + "-".join(path)


class Builder:
    def __init__(self, tokens):
        self.tokens = tokens
        self.problems = []

    def fail(self, path, message):
        self.problems.append("%s: %s" % (".".join(path), message))
        return ""

    def alias(self, path, value, kind, dark):
        """Return var(--target) when value is an alias, None when it is not."""
        if not isinstance(value, str):
            return None
        match = ALIAS_RE.match(value)
        if not match:
            return None
        target = tuple(match.group(1).split("."))
        if target and target[0] in OVERRIDES:
            return self.fail(path, "refers to %s; refer to the token without '%s.', the "
                                   "override replaces it" % (value, target[0]))
        if target not in self.tokens:
            return self.fail(path, "refers to %s, which does not exist" % value)
        if self.tokens[target][0] != kind:
            return self.fail(path, "is a %s but refers to %s, which is a %s"
                             % (kind, value, self.tokens[target][0]))
        seen, current = {path}, target
        while True:
            if current in seen:
                return self.fail(path, "refers to itself through %s" % value)
            seen.add(current)
            following = self.tokens[current][1]
            match = ALIAS_RE.match(following) if isinstance(following, str) else None
            if not match or tuple(match.group(1).split(".")) not in self.tokens:
                break
            current = tuple(match.group(1).split("."))
        return "var(%s)" % css_name(target)

    def value(self, path, kind, value, dark=False):
        aliased = self.alias(path, value, kind, dark)
        if aliased is not None:
            return aliased
        return getattr(self, "css_" + kind)(path, value)

    def css_color(self, path, value):
        if not isinstance(value, dict):
            return self.fail(path, "a color is an object: {\"colorSpace\": \"srgb\", "
                                   "\"components\": [r, g, b], \"hex\": \"#rrggbb\"}")
        if value.get("colorSpace") != "srgb":
            return self.fail(path, "only the 'srgb' color space is supported in this version")
        components = value.get("components")
        if not isinstance(components, list) or len(components) != 3 or not all(
                is_number(c) and 0 <= c <= 1 for c in components):
            return self.fail(path, "'components' must be three numbers from 0 to 1")
        channels = [int(round(c * 255)) for c in components]
        hex_value = "#%02x%02x%02x" % tuple(channels)
        given = value.get("hex")
        if given is not None and (not isinstance(given, str) or not HEX_RE.match(given)
                                  or given.lower() != hex_value):
            return self.fail(path, "'hex' is %s but the components give %s" % (given, hex_value))
        alpha = value.get("alpha", 1)
        if not is_number(alpha) or not 0 <= alpha <= 1:
            return self.fail(path, "'alpha' must be a number from 0 to 1")
        extra = [key for key in value if key not in ("colorSpace", "components", "alpha", "hex")]
        if extra:
            return self.fail(path, "unknown key in a color: %s" % extra[0])
        if alpha == 1:
            return hex_value
        return "rgb(%d %d %d / %s)" % (tuple(channels) + (num(float(alpha)),))

    def unit_value(self, path, value, units, what):
        if not isinstance(value, dict) or set(value) != {"value", "unit"} \
                or not is_number(value["value"]) or value["unit"] not in units:
            return self.fail(path, "a %s is an object: {\"value\": <number>, \"unit\": %s}"
                             % (what, " or ".join('"%s"' % u for u in units)))
        return num(value["value"]) + value["unit"]

    def css_dimension(self, path, value):
        return self.unit_value(path, value, ("px", "rem"), "dimension")

    def css_duration(self, path, value):
        return self.unit_value(path, value, ("ms", "s"), "duration")

    def css_number(self, path, value):
        return num(value) if is_number(value) else self.fail(path, "must be a number")

    def css_fontFamily(self, path, value):
        names = [value] if isinstance(value, str) else value
        if not isinstance(names, list) or not names or not all(
                isinstance(n, str) and n.strip() for n in names):
            return self.fail(path, "a fontFamily is a name or a list of names")
        return ", ".join(n if n in GENERIC_FAMILIES else '"%s"' % n.replace('"', "") for n in names)

    def css_fontWeight(self, path, value):
        if is_number(value) and 1 <= value <= 1000:
            return num(value)
        if isinstance(value, str) and value in WEIGHTS:
            return str(WEIGHTS[value])
        return self.fail(path, "a fontWeight is a number from 1 to 1000 or a name such as 'bold'")

    def css_cubicBezier(self, path, value):
        if not isinstance(value, list) or len(value) != 4 or not all(is_number(v) for v in value) \
                or not (0 <= value[0] <= 1 and 0 <= value[2] <= 1):
            return self.fail(path, "a cubicBezier is four numbers; the first and third from 0 to 1")
        return "cubic-bezier(%s)" % ", ".join(num(v) for v in value)

    def css_shadow(self, path, value):
        if isinstance(value, str):
            return self.fail(path, "a shadow is an object or a list of objects")
        layers = value if isinstance(value, list) else [value]
        if not layers:
            return self.fail(path, "a shadow needs at least one layer")
        parts = []
        for layer in layers:
            aliased = self.alias(path, layer, "shadow", False)
            if aliased is not None:
                parts.append(aliased)
                continue
            fields = ("color", "offsetX", "offsetY", "blur", "spread")
            if not isinstance(layer, dict) or any(f not in layer for f in fields) \
                    or any(k not in fields + ("inset",) for k in layer):
                return self.fail(path, "a shadow layer has color, offsetX, offsetY, blur and "
                                       "spread, and optionally inset")
            if not isinstance(layer.get("inset", False), bool):
                return self.fail(path, "'inset' must be true or false")
            parts.append("%s%s %s %s %s %s" % (
                "inset " if layer.get("inset") else "",
                self.value(path, "dimension", layer["offsetX"]),
                self.value(path, "dimension", layer["offsetY"]),
                self.value(path, "dimension", layer["blur"]),
                self.value(path, "dimension", layer["spread"]),
                self.value(path, "color", layer["color"])))
        return ", ".join(parts)

    def typography(self, path, value):
        """Return [(suffix, css value)] for a typography token."""
        fields = (("fontFamily", "font-family", "fontFamily"), ("fontSize", "font-size", "dimension"),
                  ("fontWeight", "font-weight", "fontWeight"),
                  ("letterSpacing", "letter-spacing", "dimension"),
                  ("lineHeight", "line-height", "number"))
        if not isinstance(value, dict) or set(value) != set(f[0] for f in fields):
            self.fail(path, "a typography token has exactly fontFamily, fontSize, fontWeight, "
                            "letterSpacing and lineHeight")
            return []
        return [(suffix, self.value(path, kind, value[key])) for key, suffix, kind in fields]

    def declarations(self, group=None):
        """The declarations of the base tokens (group None) or of one override group."""
        lines = []
        dark = group is not None
        for path, (kind, value) in self.tokens.items():
            if (path[0] if path[0] in OVERRIDES else None) != group:
                continue
            name_path = path[1:] if dark else path
            if dark:
                if name_path not in self.tokens:
                    self.fail(path, "overrides %s, which does not exist outside '%s'"
                              % (".".join(name_path), group))
                    continue
                if self.tokens[name_path][0] != kind:
                    self.fail(path, "is a %s but %s is a %s"
                              % (kind, ".".join(name_path), self.tokens[name_path][0]))
                    continue
            if kind == "typography":
                aliased = self.alias(path, value, kind, dark)
                if aliased is not None:
                    self.fail(path, "a typography token cannot be an alias; repeat its fields")
                    continue
                for suffix, css in self.typography(path, value):
                    lines.append("  %s-%s: %s;" % (css_name(name_path), suffix, css))
            else:
                lines.append("  %s: %s;" % (css_name(name_path), self.value(path, kind, value, dark)))
        return lines


def build(data):
    """Return the text of tokens.css. Raise Problem with a list of messages."""
    tokens, problems = {}, []
    collect(data, (), None, tokens, problems)
    if not tokens and not problems:
        problems.append("the file holds no tokens")
    builder = Builder(tokens)
    light = builder.declarations()
    dark = builder.declarations(DARK)
    narrow = builder.declarations(NARROW)
    problems.extend(builder.problems)
    if problems:
        raise Problem(problems)
    css = HEADER + "\n:root {\n" + "\n".join(light) + "\n}\n"
    if dark:
        css += '\n:root[data-theme="dark"] {\n' + "\n".join(dark) + "\n}\n"
    if narrow:
        css += "\n@media %s {\n  :root {\n" % NARROW_MEDIA + "\n".join(
            "  " + line for line in narrow) + "\n  }\n}\n"
    return css


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in args
    if check:
        args.remove("--check")
    if len(args) != 1 or args[0].startswith("-") or not args[0].endswith(".json"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    source = args[0]
    target = os.path.join(os.path.dirname(source), "tokens.css")
    try:
        with open(source, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        print("cannot read %s: %s" % (source, error), file=sys.stderr)
        return 2
    try:
        css = build(data)
    except Problem as error:
        for problem in error.args[0]:
            print("ERROR   %s" % problem)
        print("%d error(s); nothing was written" % len(error.args[0]))
        return 1
    if check:
        try:
            with open(target, encoding="utf-8") as handle:
                current = handle.read()
        except OSError:
            current = None
        if current != css:
            print("ERROR   %s is out of date; run build_tokens.py %s" % (target, source))
            return 1
        print("%s is up to date" % target)
        return 0
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(css)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
