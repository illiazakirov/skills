#!/usr/bin/env python3
"""Download an open-license font family from Google Fonts into a brand's fonts directory.

    fetch_font.py "<Family name>" <fonts dir> [--weights 400,700] [--italic]
                  [--subsets latin,latin-ext]

Writes into <fonts dir>:

    <family>-<subset>-<style>-<weight>.woff2    the font files
    <family>-LICENSE.txt                        the license text of the family
    fonts.css                                   @font-face rules with relative URLs

fonts.css keeps one block per family, so the script is run once for each family of the
type pair. Nothing is written when the family, a weight or a subset does not exist, or
when no open license is found for the family. A subset the market language needs must
be named: for Ukrainian, add cyrillic and cyrillic-ext.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 done, 1 refused, 2 wrong usage.
"""

import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

CSS_API = "https://fonts.googleapis.com/css2"
LICENSES = "https://raw.githubusercontent.com/google/fonts/main/"
LICENSE_PATHS = (("ofl", "OFL.txt"), ("apache", "LICENSE.txt"), ("ufl", "UFL.txt"))
# Google Fonts serves woff2 with unicode-range subsets only to a current browser.
BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 60

FAMILY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ]*$")
FACE_RE = re.compile(r"/\*\s*([a-z0-9-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", re.S)
BLOCK = "/* family: %s */"
BLOCK_END = "/* end: %s */"


class Refused(Exception):
    pass


def http(url):
    """Return (status, body bytes). Status 0 means no answer."""
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (urllib.error.URLError, OSError):
        return 0, b""


def slug(family):
    return family.lower().replace(" ", "-")


def css_url(family, weights, italic):
    if italic:
        axes = "ital,wght@" + ";".join(["0,%d" % w for w in weights] + ["1,%d" % w for w in weights])
    else:
        axes = "wght@" + ";".join(str(w) for w in weights)
    return "%s?family=%s:%s&display=swap" % (CSS_API, urllib.parse.quote(family).replace("%20", "+"),
                                             axes)


def parse_faces(css):
    """Return the @font-face rules of a Google Fonts stylesheet as dicts."""
    faces = []
    for subset, body in FACE_RE.findall(css):
        def value(name):
            match = re.search(r"%s:\s*([^;]+);" % name, body)
            return match.group(1).strip() if match else None
        url = re.search(r"url\((https://[^)]+\.woff2)\)", body)
        if not url or not value("font-weight") or not value("font-style"):
            continue
        faces.append({"subset": subset, "style": value("font-style"),
                      "weight": value("font-weight"), "range": value("unicode-range"),
                      "url": url.group(1)})
    return faces


def fetch_license(family, fetch):
    name = slug(family).replace("-", "")
    for directory, filename in LICENSE_PATHS:
        status, body = fetch("%s%s/%s/%s" % (LICENSES, directory, name, filename))
        if status == 200 and body.strip():
            return body
    raise Refused("no open license was found for '%s' in the Google Fonts repository; "
                  "the font may not be used until its license is known" % family)


def update_css(path, family, rules):
    start, end = BLOCK % family, BLOCK_END % family
    block = "%s\n%s\n%s\n" % (start, "\n".join(rules), end)
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.S)
    text = pattern.sub(lambda match: block, text) if pattern.search(text) else \
        (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def fetch_family(family, directory, weights, italic, subsets, fetch=http):
    """Download the family. Return the list of files written. Raise Refused on any problem."""
    status, body = fetch(css_url(family, weights, italic))
    if status == 400:
        raise Refused("Google Fonts has no family '%s' with weights %s%s"
                      % (family, ", ".join(str(w) for w in weights),
                         " and italics" if italic else ""))
    if status != 200:
        raise Refused("Google Fonts did not answer (%s)" % (status or "no connection"))
    faces = parse_faces(body.decode("utf-8", "replace"))
    available = sorted(set(face["subset"] for face in faces))
    missing = [subset for subset in subsets if subset not in available]
    if not faces:
        raise Refused("Google Fonts returned no font files for '%s'" % family)
    if missing:
        raise Refused("'%s' has no %s subset; it has: %s"
                      % (family, ", ".join(missing), ", ".join(available)))
    license_text = fetch_license(family, fetch)

    files, rules, written = {}, [], []
    for face in faces:
        if face["subset"] not in subsets:
            continue
        if face["url"] not in files:
            status, data = fetch(face["url"])
            if status != 200 or not data:
                raise Refused("a font file could not be downloaded (%s)" % (status or "no connection"))
            name = "%s-%s-%s-%s.woff2" % (slug(family), face["subset"], face["style"],
                                          face["weight"].replace(" ", "-"))
            files[face["url"]] = (name, data)
        rules.append(
            "@font-face { font-family: '%s'; font-style: %s; font-weight: %s; font-display: swap; "
            "src: url(%s) format('woff2');%s }"
            % (family, face["style"], face["weight"], files[face["url"]][0],
               " unicode-range: %s;" % face["range"] if face["range"] else ""))

    for name, data in files.values():
        with open(os.path.join(directory, name), "wb") as handle:
            handle.write(data)
        written.append(name)
    license_name = "%s-LICENSE.txt" % slug(family)
    with open(os.path.join(directory, license_name), "wb") as handle:
        handle.write(license_text)
    update_css(os.path.join(directory, "fonts.css"), family, rules)
    return sorted(written) + [license_name, "fonts.css"]


def parse(args):
    options = {"weights": "400,700", "subsets": "latin,latin-ext", "italic": False}
    positional = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--italic":
            options["italic"] = True
            index += 1
        elif arg in ("--weights", "--subsets"):
            if index + 1 >= len(args):
                return None
            options[arg[2:]] = args[index + 1]
            index += 2
        elif arg.startswith("--"):
            return None
        else:
            positional.append(arg)
            index += 1
    if len(positional) != 2 or not FAMILY_RE.match(positional[0]):
        return None
    weights = options["weights"].split(",")
    if not all(w.isdigit() and 100 <= int(w) <= 900 for w in weights):
        return None
    subsets = [s for s in options["subsets"].split(",") if s]
    if not subsets or not all(re.match(r"^[a-z0-9-]+$", s) for s in subsets):
        return None
    return positional[0], positional[1], sorted(set(int(w) for w in weights)), \
        options["italic"], subsets


def main(argv=None, fetch=http):
    parsed = parse(sys.argv[1:] if argv is None else argv)
    if parsed is None:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    family, directory, weights, italic, subsets = parsed
    if not os.path.isdir(directory):
        print("the fonts directory does not exist: %s" % directory, file=sys.stderr)
        return 2
    try:
        written = fetch_family(family, directory, weights, italic, subsets, fetch)
    except Refused as error:
        print("ERROR   %s" % error)
        return 1
    for name in written:
        print(os.path.join(directory, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
