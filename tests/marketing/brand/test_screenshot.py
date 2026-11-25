"""Tests for scripts/screenshot.py.

Most tests use a fake Chrome: a small script that writes a PNG where it is told to.
One test uses the real Chrome and is skipped when none is installed.
"""

import importlib.util
import os
import shutil
import stat
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, "skills", "marketing", "brand")
SCRIPT = os.path.join(SKILL, "scripts", "screenshot.py")

_spec = importlib.util.spec_from_file_location("screenshot", SCRIPT)
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)


def png(width, height):
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    rows = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))
    return (ss.PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


FAKE = """#!%s
import sys
args = sys.argv[1:]
out = [a.split("=", 1)[1] for a in args if a.startswith("--screenshot=")][0]
size = [a.split("=", 1)[1] for a in args if a.startswith("--window-size=")][0]
if args[-1].endswith("crash.html") or (args[-1].endswith("sandboxed.html")
                                         and ("--single-process" not in args
                                              or any(a.startswith("--virtual-time-budget")
                                                     for a in args))):
    import os
    os.abort()
if args[-1].endswith("fail.html"):
    sys.stderr.write("net::ERR_NAME_NOT_RESOLVED\\n")
    sys.exit(0)
with open(sys.argv[0] + ".png", "rb") as source, open(out, "wb") as target:
    target.write(source.read())
with open(sys.argv[0] + ".log", "w") as log:
    log.write(size + " " + args[-1])
"""


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.fake = os.path.join(self.tmp, "chrome")
        with open(self.fake, "w") as handle:
            handle.write(FAKE % sys.executable)
        os.chmod(self.fake, os.stat(self.fake).st_mode | stat.S_IEXEC)
        with open(self.fake + ".png", "wb") as handle:
            handle.write(png(8, 5))
        self.env = {"BRAND_CHROME": self.fake, "PATH": ""}
        self.out = os.path.join(self.tmp, "shot.png")

    def log(self):
        with open(self.fake + ".log") as handle:
            return handle.read()


class FindChrome(Case):
    def test_override_is_used(self):
        self.assertEqual(ss.find_chrome(self.env), self.fake)

    def test_override_that_does_not_exist_is_not_replaced(self):
        self.assertIsNone(ss.find_chrome({"BRAND_CHROME": "/no/such/chrome", "PATH": ""}))

    def test_found_on_path(self):
        if any(os.path.isfile(path) for path in ss.APPLICATION_PATHS):
            self.skipTest("an installed Chrome takes precedence over the PATH")
        os.rename(self.fake, os.path.join(self.tmp, "chromium"))
        self.assertEqual(ss.find_chrome({"PATH": self.tmp}), os.path.join(self.tmp, "chromium"))

    def test_find_command(self):
        self.assertEqual(ss.main(["--find"], self.env), 0)
        self.assertEqual(ss.main(["--find"], {"BRAND_CHROME": "/no/such", "PATH": ""}), 3)


class Capture(Case):
    def test_url_is_captured_at_the_default_size(self):
        self.assertEqual(ss.main(["https://example.com/", self.out], self.env), 0)
        self.assertEqual(ss.png_size(self.out), (8, 5))
        self.assertEqual(self.log(), "1440,900 https://example.com/")

    def test_size_can_be_set(self):
        code = ss.main(["https://example.com/", self.out, "--width", "390", "--height", "844"],
                       self.env)
        self.assertEqual(code, 0)
        self.assertTrue(self.log().startswith("390,844 "))

    def test_local_file_becomes_a_file_url(self):
        page = os.path.join(self.tmp, "page.html")
        open(page, "w").close()
        self.assertEqual(ss.main([page, self.out], self.env), 0)
        self.assertTrue(self.log().endswith("file://" + os.path.abspath(page).replace(os.sep, "/")))

    def test_failed_capture_is_an_error_and_leaves_no_old_file(self):
        with open(self.out, "wb") as handle:
            handle.write(png(1, 1))
        page = os.path.join(self.tmp, "fail.html")
        open(page, "w").close()
        self.assertEqual(ss.main([page, self.out], self.env), 1)
        self.assertFalse(os.path.exists(self.out))

    def test_a_crash_is_retried_in_one_process(self):
        """A sandbox that forbids Chrome's helper processes (Codex's) kills the first try."""
        page = os.path.join(self.tmp, "sandboxed.html")
        open(page, "w").close()
        self.assertEqual(ss.main([page, self.out], self.env), 0)
        self.assertEqual(ss.png_size(self.out), (8, 5))

    def test_a_crash_in_one_process_too_names_the_headless_shell(self):
        page = os.path.join(self.tmp, "crash.html")
        open(page, "w").close()
        message = ss.capture(self.fake, ss.target_url(page), self.out)
        self.assertIn("chrome-headless-shell", message)
        self.assertIn("BRAND_CHROME", message)

    def test_a_page_error_is_not_retried(self):
        page = os.path.join(self.tmp, "fail.html")
        open(page, "w").close()
        message = ss.capture(self.fake, ss.target_url(page), self.out)
        self.assertNotIn("chrome-headless-shell", message)

    def test_no_chrome(self):
        env = {"BRAND_CHROME": "/no/such", "PATH": ""}
        self.assertEqual(ss.main(["https://example.com/", self.out], env), 3)


class Usage(Case):
    def test_wrong_usage(self):
        for args in ([], ["https://example.com/"], ["https://example.com/", "shot.jpg"],
                     ["https://example.com/", self.out, "--width"],
                     ["https://example.com/", self.out, "--width", "wide"],
                     ["https://example.com/", self.out, "--full"],
                     ["no-such-file.html", self.out],
                     ["https://example.com/", os.path.join(self.tmp, "missing", "shot.png")]):
            self.assertEqual(ss.main(args, self.env), 2, args)

    def test_png_size_rejects_other_files(self):
        with open(self.out, "wb") as handle:
            handle.write(b"not a png at all, just some bytes")
        self.assertIsNone(ss.png_size(self.out))
        self.assertIsNone(ss.png_size(os.path.join(self.tmp, "absent.png")))


class RealChrome(unittest.TestCase):
    def test_first_screen_of_a_local_page(self):
        chrome = ss.find_chrome()
        if not chrome:
            self.skipTest("Chrome is not installed")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        page = os.path.join(tmp, "page.html")
        with open(page, "w") as handle:
            handle.write("<!doctype html><body style='margin:0;height:5000px;background:#06c'>")
        out = os.path.join(tmp, "page.png")
        self.assertEqual(ss.main([page, out, "--width", "800", "--height", "600"]), 0)
        self.assertEqual(ss.png_size(out), (800, 600))


if __name__ == "__main__":
    unittest.main()
