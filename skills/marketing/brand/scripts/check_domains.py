#!/usr/bin/env python3
"""Check whether domain names are registered, through the registries' RDAP services.

    check_domains.py <domain> [<domain> ...]

Prints one line per domain:

    registered      example.com
    not registered  example.dev
    unknown         example.ua     (the reason)

"not registered" means the registry has no record of the name. It is likely free, but
only a registrar can confirm that it can be bought, and at what price. "unknown" means
the zone has no RDAP service or the registry did not answer.
No dependencies beyond the Python 3 standard library.

Exit codes: 0 every domain was looked up (whatever the answers), 2 wrong usage.
"""

import json
import re
import sys
import urllib.error
import urllib.request

BOOTSTRAP = "https://data.iana.org/rdap/dns.json"
TIMEOUT = 20
DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]*$")


def http(url):
    """Return (status, body bytes). Status 0 means no answer."""
    request = urllib.request.Request(url, headers={"User-Agent": "brand",
                                                   "Accept": "application/rdap+json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (urllib.error.URLError, OSError):
        return 0, b""


def servers(fetch):
    """Return {tld: RDAP base URL} from the IANA bootstrap file, or None."""
    status, body = fetch(BOOTSTRAP)
    if status != 200:
        return None
    try:
        result = {}
        for tlds, urls in json.loads(body.decode("utf-8"))["services"]:
            base = [url for url in urls if url.startswith("https://")]
            for tld in tlds:
                if base:
                    result[tld.lower()] = base[0].rstrip("/") + "/"
        return result
    except (ValueError, KeyError, TypeError):
        return None


def lookup(domain, table, fetch):
    """Return (state, reason) for one domain."""
    if table is None:
        return "unknown", "the list of RDAP services could not be loaded"
    tld = domain.rsplit(".", 1)[1]
    base = table.get(tld)
    if base is None:
        return "unknown", "the .%s zone has no RDAP service" % tld
    status, _ = fetch(base + "domain/" + domain)
    if status == 200:
        return "registered", ""
    if status == 404:
        return "not registered", ""
    if status == 0:
        return "unknown", "the registry did not answer"
    return "unknown", "the registry answered %d" % status


def main(argv=None, fetch=http):
    args = [arg.lower().rstrip(".") for arg in (sys.argv[1:] if argv is None else argv)]
    if not args or not all(DOMAIN_RE.match(arg) for arg in args):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    table = servers(fetch)
    for domain in args:
        state, reason = lookup(domain, table, fetch)
        print("%-15s %s%s" % (state, domain, "     (%s)" % reason if reason else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
