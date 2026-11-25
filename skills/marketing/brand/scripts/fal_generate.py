#!/usr/bin/env python3
"""Generate images with fal.ai for a brand step, within the project's budget.

    fal_generate.py <brand> <step> <output dir> <name> --prompt TEXT
                    [--count N] [--size SIZE] [--model MODEL] [--price USD] [--estimate]
    fal_generate.py <brand> --check-key

Writes <output dir>/<name>-<n>.png, one request per image, and adds the price of every
image that was generated to the step's `spent` in <brand>/pipeline.yaml.

--estimate prints what the batch would cost and what is left of the budget, and calls
nothing. Run it first, tell the owner the price, and generate only after their yes.

The key is read from the studio's .env when <brand> is an order directory
(<studio>/orders/<order>), else from <brand>/.env, else from the environment (FAL_KEY).
Files come first because some agents do not pass environment variables into their sandbox.
It is never printed. --check-key says where the key was found, or where to put it, and
calls nothing: fal checks the key at the first generation.
Sizes: square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9;
all are at most one megapixel. A model that is not in the price table needs --price,
the price of one image in US dollars.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 done, 1 refused or failed, 2 wrong usage, 3 the key is not set.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contract  # noqa: E402

DEFAULT_MODEL = "fal-ai/flux-2-pro"
# US dollars for one image of at most one megapixel. Checked against fal.ai on 2026-11-17.
PRICES = {
    "fal-ai/flux-2-pro": 0.03,
    "fal-ai/flux-pro/v1.1": 0.04,
}
SIZES = ("square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_4_3",
         "landscape_16_9")
DEFAULT_SIZE = "landscape_4_3"
PLACEHOLDER = "put-fal-key-here"
MAX_COUNT = 12
TIMEOUT = 180

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MODEL_RE = re.compile(r"^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)+$")


class Refused(Exception):
    """The batch must not run, or it failed. The message is safe to print."""


def key_files(brand):
    """The .env files that may hold the key, in the order they are read: the studio's
    (when the brand directory is an order, <studio>/orders/<order>), then the brand's."""
    files = []
    parent = os.path.dirname(os.path.abspath(brand))
    if os.path.basename(parent) == "orders":
        files.append(os.path.join(os.path.dirname(parent), ".env"))
    files.append(os.path.join(brand, ".env"))
    return files


def key_from_file(path):
    """Return the FAL_KEY of one .env file, or None."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if line.startswith("FAL_KEY="):
            value = line[len("FAL_KEY="):].strip().strip("'\"")
            return value if value and value != PLACEHOLDER else None
    return None


def read_key(brand, environ=None):
    """Return (key, source): the fal key and the .env path it came from, or "environment";
    (None, None) when it is not set. The studio's .env, then <brand>/.env, then FAL_KEY
    in the environment (reference/contract.md, section 1)."""
    for path in key_files(brand):
        value = key_from_file(path)
        if value:
            return value, path
    environ = os.environ if environ is None else environ
    value = environ.get("FAL_KEY", "").strip()
    if value and value != PLACEHOLDER:
        return value, "environment"
    return None, None


def check_key(brand):
    """Print where the key is, or where to put it; never the key. Return the exit code."""
    _, source = read_key(brand)
    if source is None:
        files = key_files(brand)
        print("fal key: not set. Put it into %s (FAL_KEY=...); also looked in: %s"
              % (files[0], ", ".join(files[1:] + ["the environment (FAL_KEY)"])))
        return 3
    print("fal key: found in %s; it is checked with fal at the first generation" % source)
    return 0


def read_budget(brand, step):
    """Return (limit, total spent, this step's spent) from pipeline.yaml."""
    path = os.path.join(brand, "pipeline.yaml")
    try:
        data = check_contract.parse_yaml(check_contract.read_lines(path))
    except (OSError, check_contract.SubsetError) as error:
        raise Refused("cannot read %s: %s" % (path, error))
    try:
        if data["tools"]["image_generation"] != "fal":
            raise Refused("tools.image_generation is '%s', not 'fal'; paid generation is off"
                          % data["tools"]["image_generation"])
        steps = data["steps"]
        if step not in steps:
            raise Refused("unknown step: %s" % step)
        limit = float(data["budget"]["limit"])
        total = sum(float(entry["spent"]) for entry in steps.values())
        return limit, total, float(steps[step]["spent"])
    except (KeyError, TypeError, ValueError, AttributeError):
        raise Refused("%s is not a valid pipeline file; run the contract check" % path)


def number(value):
    return ("%.4f" % value).rstrip("0").rstrip(".") or "0"


def record_spent(brand, step, amount):
    """Add amount to the step's `spent` line in pipeline.yaml, leaving the rest as it is."""
    path = os.path.join(brand, "pipeline.yaml")
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    inside = False
    for index, line in enumerate(lines):
        if re.match(r"^  \S", line):
            inside = line.split("#")[0].strip() == step + ":"
        elif inside:
            match = re.match(r"^(    spent:\s*)([0-9.]+)(.*)$", line)
            if match:
                lines[index] = match.group(1) + number(float(match.group(2)) + amount) \
                    + match.group(3)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(lines))
                return
    raise Refused("no 'spent' line for %s in %s; the spend of %s was not recorded"
                  % (step, path, number(amount)))


def http(url, key=None, body=None):
    """Return the bytes of the response. Raise Refused with a message that holds no key."""
    headers = {"User-Agent": "brand"}
    data = None
    if body is not None:
        headers.update({"Authorization": "Key " + key, "Content-Type": "application/json"})
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = json.loads(error.read().decode("utf-8", "replace")).get("detail", "")
        except (ValueError, AttributeError):
            pass
        hint = {401: " (the key in .env was rejected)",
                403: " (the key may not use this model, or a spending limit was reached)",
                404: " (no such model)"}.get(error.code, "")
        raise Refused("fal answered %d%s%s" % (error.code, hint,
                                               ": %s" % (detail,) if detail else ""))
    except (urllib.error.URLError, OSError) as error:
        raise Refused("no answer from %s: %s" % (url.split("/")[2],
                                                 getattr(error, "reason", error)))


def generate_one(model, prompt, size, key, fetch):
    """Return the bytes of one generated PNG."""
    answer = fetch("https://fal.run/" + model, key,
                   {"prompt": prompt, "image_size": size, "output_format": "png"})
    try:
        url = json.loads(answer.decode("utf-8"))["images"][0]["url"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise Refused("fal returned no image")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise Refused("fal returned no image")
    return fetch(url)


def next_number(directory, name):
    taken = [int(match.group(1)) for match in
             (re.match(r"^%s-(\d+)\.png$" % re.escape(name), entry)
              for entry in os.listdir(directory)) if match]
    return max(taken) + 1 if taken else 1


def parse(args):
    options = {"prompt": None, "count": "1", "size": DEFAULT_SIZE, "model": DEFAULT_MODEL,
               "price": None, "estimate": False}
    positional = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--estimate":
            options["estimate"] = True
            index += 1
        elif arg.startswith("--") and arg[2:] in options:
            if index + 1 >= len(args):
                return None
            options[arg[2:]] = args[index + 1]
            index += 2
        elif arg.startswith("--"):
            return None
        else:
            positional.append(arg)
            index += 1
    if len(positional) != 4 or not options["prompt"] or not options["prompt"].strip():
        return None
    if not options["count"].isdigit() or not 1 <= int(options["count"]) <= MAX_COUNT:
        return None
    if options["size"] not in SIZES or not MODEL_RE.match(options["model"]):
        return None
    if not NAME_RE.match(positional[3]) or positional[1] not in check_contract.STEPS:
        return None
    if options["price"] is not None:
        try:
            options["price"] = float(options["price"])
        except ValueError:
            return None
        if not 0 < options["price"] < 100:
            return None
    options["count"] = int(options["count"])
    return positional, options


def main(argv=None, fetch=http):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[1] == "--check-key":
        return check_key(argv[0])
    parsed = parse(argv)
    if parsed is None:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    (brand, step, directory, name), options = parsed
    model, count = options["model"], options["count"]
    price = options["price"] if options["price"] is not None else PRICES.get(model)
    try:
        if price is None:
            raise Refused("no price is known for %s; pass --price with the price of one "
                          "image in US dollars, from the model's page on fal.ai" % model)
        limit, total, _ = read_budget(brand, step)
        cost = price * count
        left = limit - total
        print("%d image(s) with %s at $%s each: $%s. Budget: $%s of $%s spent, $%s left."
              % (count, model, number(price), number(cost), number(total), number(limit),
                 number(left)))
        if cost > left + 1e-9:
            raise Refused("the batch costs more than what is left of the budget; "
                          "nothing was generated")
        if options["estimate"]:
            return 0
        if not os.path.isdir(directory):
            raise Refused("the output directory does not exist: %s" % directory)
        key, _ = read_key(brand)
        if key is None:
            print("The fal key is not set. Put it into %s as FAL_KEY=<key>."
                  % " or ".join(key_files(brand)), file=sys.stderr)
            return 3
        first = next_number(directory, name)
        for offset in range(count):
            image = generate_one(model, options["prompt"], options["size"], key, fetch)
            record_spent(brand, step, price)
            path = os.path.join(directory, "%s-%d.png" % (name, first + offset))
            with open(path, "wb") as handle:
                handle.write(image)
            print(path)
    except Refused as error:
        print("ERROR   %s" % error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
