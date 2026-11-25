#!/usr/bin/env python3
"""Bundle an HTML page and the local files it uses into one self-contained HTML file.

    bundle_html.py <source.html> <output.html>

Inlines, relative to the source file:

- <link rel="stylesheet" href="..."> as a <style> block, with the files its url(...)
  point to (fonts, images) embedded as data URIs;
- url(...) in the page's own <style> blocks and style attributes;
- <img src="..."> and <script src="..."> .

The result opens anywhere, without the directory it was built in and without a network.
Nothing is written when a file is missing, or when the page loads anything from a remote
server or in a frame. Links (<a href>) are left as they are.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 bundled, 1 the page breaks a rule, 2 wrong usage or the source cannot be read.
"""

import base64
import os
import re
import sys
from urllib.parse import unquote

MIME = {
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".avif": "image/avif", ".ico": "image/x-icon",
}
URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
SCRIPT_RE = re.compile(r"<script\b([^>]*)>\s*</script>", re.I)
FRAME_RE = re.compile(r"<(iframe|frame|object|embed)\b", re.I)
IMPORT_RE = re.compile(r"@import\b", re.I)


def attribute(tag, name):
    match = re.search(r"\b%s\s*=\s*(\"([^\"]*)\"|'([^']*)')" % name, tag, re.I)
    if not match:
        return None
    return match.group(2) if match.group(2) is not None else match.group(3)


def is_remote(reference):
    return re.match(r"^([a-z][a-z0-9+.-]*:)?//", reference, re.I) is not None


class Bundler:
    def __init__(self):
        self.problems = []

    def read(self, base, reference, what):
        """Return the bytes of a local file, or None after recording the problem."""
        if is_remote(reference):
            self.problems.append("%s loads from a remote server: %s" % (what, reference))
            return None
        path = os.path.join(base, unquote(reference.split("#")[0].split("?")[0]))
        try:
            with open(path, "rb") as handle:
                return handle.read()
        except OSError:
            self.problems.append("%s does not exist: %s" % (what, reference))
            return None

    def data_uri(self, base, reference, what):
        if reference.startswith("data:") or reference.startswith("#"):
            return reference
        extension = os.path.splitext(reference.split("#")[0].split("?")[0])[1].lower()
        if extension not in MIME:
            self.problems.append("%s has a file type that cannot be embedded: %s"
                                 % (what, reference))
            return reference
        content = self.read(base, reference, what)
        if content is None:
            return reference
        return "data:%s;base64,%s" % (MIME[extension], base64.b64encode(content).decode("ascii"))

    def css(self, text, base, what):
        if IMPORT_RE.search(text):
            self.problems.append("%s uses @import, which is not bundled; use <link> instead"
                                 % what)
        return URL_RE.sub(
            lambda match: "url(%s)" % self.data_uri(base, match.group(2).strip(),
                                                    "a url() in %s" % what), text)

    def page(self, text, base):
        if FRAME_RE.search(text):
            self.problems.append("the page shows another document in a frame; a bundled page "
                                 "cannot contain one. Show it as an image instead")
        text = self.css(text, base, "the page")

        def link(match):
            tag = match.group(0)
            if (attribute(tag, "rel") or "").lower() != "stylesheet":
                if (attribute(tag, "rel") or "").lower() in ("icon", "shortcut icon") \
                        and attribute(tag, "href"):
                    uri = self.data_uri(base, attribute(tag, "href"), "the page icon")
                    return tag.replace(attribute(tag, "href"), uri)
                if is_remote(attribute(tag, "href") or ""):
                    self.problems.append("a <link> loads from a remote server: %s"
                                         % attribute(tag, "href"))
                return tag
            href = attribute(tag, "href") or ""
            content = self.read(base, href, "a stylesheet")
            if content is None:
                return tag
            sheet = self.css(content.decode("utf-8", "replace"),
                             os.path.dirname(os.path.join(base, unquote(href))),
                             "the stylesheet %s" % href)
            return "<style>\n%s\n</style>" % sheet.replace("</style", "<\\/style")

        def image(match):
            tag = match.group(0)
            src = attribute(tag, "src")
            if not src:
                return tag
            return tag.replace(src, self.data_uri(base, src, "an image"), 1)

        def script(match):
            src = attribute(match.group(1), "src")
            if not src:
                return match.group(0)
            content = self.read(base, src, "a script")
            if content is None:
                return match.group(0)
            return "<script>\n%s\n</script>" % content.decode("utf-8", "replace").replace(
                "</script", "<\\/script")

        text = LINK_RE.sub(link, text)
        text = IMG_RE.sub(image, text)
        text = SCRIPT_RE.sub(script, text)
        return text


def bundle(text, base):
    """Return (bundled text, problems)."""
    bundler = Bundler()
    return bundler.page(text, base), bundler.problems


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or any(arg.startswith("-") for arg in args) \
            or not all(arg.lower().endswith((".html", ".htm")) for arg in args) \
            or os.path.abspath(args[0]) == os.path.abspath(args[1]):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    source, output = args
    try:
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        print("cannot read %s: %s" % (source, error), file=sys.stderr)
        return 2
    result, problems = bundle(text, os.path.dirname(os.path.abspath(source)))
    if problems:
        for problem in problems:
            print("ERROR   %s" % problem)
        print("%d error(s); nothing was written" % len(problems))
        return 1
    try:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(result)
    except OSError as error:
        print("cannot write %s: %s" % (output, error), file=sys.stderr)
        return 2
    print("%s %d KB" % (output, (len(result.encode("utf-8")) + 1023) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
