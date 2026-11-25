#!/usr/bin/env python3
"""Take a screenshot of the first screen of a page with headless Chrome.

    screenshot.py <url or local .html file> <output.png> [--width 1440] [--height 900]
    screenshot.py --find

The screenshot is the viewport only (the first screen), never the whole page.
--find prints the path of the Chrome that would be used.
Chrome is looked for in $BRAND_CHROME, the usual application paths and the PATH.
When Chrome is killed at start, as in a sandbox that forbids its helper processes, it is
tried once more with --single-process; chrome-headless-shell works there, Google Chrome does not.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 done, 1 the screenshot failed, 2 wrong usage, 3 Chrome was not found.
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile

DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 900
TIMEOUT = 90  # seconds for one page

APPLICATION_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
PATH_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def find_chrome(environ=None):
    """Return the path of a Chrome or Chromium executable, or None."""
    environ = os.environ if environ is None else environ
    override = environ.get("BRAND_CHROME")
    if override:
        return override if os.path.isfile(override) else None
    for path in APPLICATION_PATHS:
        if os.path.isfile(path):
            return path
    for name in PATH_NAMES:
        found = shutil.which(name, path=environ.get("PATH"))
        if found:
            return found
    return None


def target_url(target):
    """Turn a URL or a local file path into a URL Chrome can open; None if neither."""
    if target.startswith(("http://", "https://", "file://")):
        return target
    if os.path.isfile(target):
        path = os.path.abspath(target).replace(os.sep, "/")
        return "file://" + (path if path.startswith("/") else "/" + path)
    return None


def command(chrome, url, output, width, height, profile, extra=(), single=False):
    """extra: further Chrome switches, placed before the URL. single: run Chrome in one
    process, without the virtual time budget, which never ends in that mode."""
    switches = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--force-device-scale-factor=1",
        "--user-data-dir=%s" % profile,
        "--window-size=%d,%d" % (width, height),
        "--virtual-time-budget=8000",
        "--screenshot=%s" % output,
    ]
    if single:
        switches = one_process(switches)
    return switches + list(extra) + [url]


def png_size(path):
    """Return (width, height) of a PNG file, or None when it is not a PNG."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def one_process(switches):
    """The switches for a second try in one process: a sandbox that forbids Chrome's helper
    processes (Codex's on macOS) kills it at start otherwise. The virtual time budget is
    dropped, because it never ends in that mode."""
    return [s for s in switches if not s.startswith("--virtual-time-budget")] + ["--single-process"]


def run_chrome(chrome, switches, url, done=lambda result: True):
    """Run Chrome with switches and the url. When Chrome is killed by a signal and done(result)
    is false, try once more in one process. Return the last CompletedProcess.
    Raise OSError or subprocess.TimeoutExpired as subprocess.run does."""
    def once(extra):
        profile = tempfile.mkdtemp(prefix="brand-chrome-")
        try:
            return subprocess.run([chrome, "--user-data-dir=%s" % profile] + extra + [url],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=TIMEOUT)
        finally:
            shutil.rmtree(profile, ignore_errors=True)
    result = once(list(switches))
    if crashed(result.returncode) and not done(result):
        result = once(one_process(switches))
    return result


def crashed(returncode):
    """True when Chrome was killed by a signal rather than exiting on its own."""
    return returncode < 0 or returncode >= 128


def attempt(chrome, url, output, width, height, extra, single=False):
    """Run Chrome once. Return (None, None) on success, else (message, returncode)."""
    if os.path.exists(output):
        os.remove(output)
    profile = tempfile.mkdtemp(prefix="brand-chrome-")
    try:
        result = subprocess.run(command(chrome, url, output, width, height, profile, extra,
                                        single),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "Chrome did not finish within %d seconds" % TIMEOUT, None
    except OSError as error:
        return "Chrome could not be started: %s" % error, None
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if png_size(output) is None:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        return "Chrome wrote no screenshot (exit %d)%s" % (
            result.returncode, ": " + detail[-1] if detail else ""), result.returncode
    return None, None


def capture(chrome, url, output, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, extra=()):
    """Write the screenshot. Return None on success or a message on failure.

    A sandbox that forbids Chrome's helper processes (Codex's on macOS, for one) kills
    Chrome at start; then it is tried once more in a single process. Google Chrome
    still fails there, chrome-headless-shell does not."""
    output = os.path.abspath(output)
    message, code = attempt(chrome, url, output, width, height, extra)
    if message is None or code is None or not crashed(code):
        return message
    message, code = attempt(chrome, url, output, width, height, extra, single=True)
    if message is None:
        return None
    return (message + ". Chrome is killed at start, as inside a sandbox that forbids its "
            "helper processes. Install chrome-headless-shell "
            "(npx @puppeteer/browsers install chrome-headless-shell@stable) and set "
            "BRAND_CHROME to its path.")


def parse(args):
    """Return (target, output, width, height) or None when the usage is wrong."""
    positional, width, height = [], DEFAULT_WIDTH, DEFAULT_HEIGHT
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("--width", "--height"):
            if index + 1 >= len(args) or not args[index + 1].isdigit() or int(args[index + 1]) < 1:
                return None
            if arg == "--width":
                width = int(args[index + 1])
            else:
                height = int(args[index + 1])
            index += 2
        elif arg.startswith("--"):
            return None
        else:
            positional.append(arg)
            index += 1
    if len(positional) != 2 or not positional[1].lower().endswith(".png"):
        return None
    return positional[0], positional[1], width, height


def main(argv=None, environ=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ["--find"]:
        chrome = find_chrome(environ)
        if not chrome:
            print("Chrome was not found", file=sys.stderr)
            return 3
        print(chrome)
        return 0
    parsed = parse(args)
    if parsed is None:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    target, output, width, height = parsed
    url = target_url(target)
    if url is None:
        print("not a URL and not an existing file: %s" % target, file=sys.stderr)
        return 2
    if not os.path.isdir(os.path.dirname(os.path.abspath(output))):
        print("the directory of the output file does not exist: %s" % output, file=sys.stderr)
        return 2
    chrome = find_chrome(environ)
    if not chrome:
        print("Chrome was not found; set BRAND_CHROME to its path, or place the "
              "screenshot by hand", file=sys.stderr)
        return 3
    problem = capture(chrome, url, output, width, height)
    if problem:
        print("ERROR   %s: %s" % (target, problem))
        return 1
    print("%s %dx%d" % ((output,) + png_size(output)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
