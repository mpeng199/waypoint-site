#!/usr/bin/env python3
"""Ask every website in the directory whether it is still there.

Deliberately NOT part of check.py. That suite is offline, deterministic and
runs on every edit; this one talks to eighty-odd third-party servers and its
answer depends on the weather. A flaky CDN must never be able to fail the
build. Run it on its own, periodically:

    python3 check_links_live.py

What it is for: a dead link in a resource directory is not a broken link. It
is somebody in trouble spending their afternoon on a page that no longer
exists, and deciding the rest of the list is probably wrong too.

Findings are advisory, and the failure list needs a human before anyone edits
the CSV. Two known false alarms:

  * A 403/429 usually means the host blocks scripted requests. Those are
    reported separately so nobody "fixes" a working link by deleting it.
  * Some WAFs fingerprint the TLS handshake, not the User-Agent, and answer
    Python with a 503 no matter what it claims to be.
    `https://nystateofhealth.ny.gov` is the standing example: 503 here, 200 in
    curl and in a browser. Cross-check anything in the failure list with
    `curl -IL <url>` before believing it.

Redirects are reported but are usually not worth chasing — most are a trailing
slash, a dropped www, or a locale prefix, and the reader never sees them. Chase
the ones where the path itself changed.
"""

import csv
import concurrent.futures
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CSV = Path(__file__).parent / "data" / "resources.csv"
TIMEOUT = 20

# Identify honestly by default: this is a link check run by the site that
# lists these organisations, and saying so is the polite thing to do.
UA = ("Mozilla/5.0 (compatible; WaypointLinkCheck/1.0; "
      "+https://github.com/mpeng199/waypoint-site) link-verification")

# Every nyc.gov page, and about a third of the nonprofits, sit behind a WAF
# that 403s anything not shaped like a browser. Thirty-one false alarms in a
# report of eighty-four is a report nobody reads, so a 403 gets one retry with
# an ordinary browser string before being believed. Still not silent: whatever
# fails BOTH attempts is reported as blocked-and-unverified rather than dead,
# because a WAF rejection is not evidence the page is gone.
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _attempt(url, method, ua):
    req = urllib.request.Request(url, method=method,
                                 headers={"User-Agent": ua, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.url if r.url.rstrip("/") != url.rstrip("/") else ""
    except urllib.error.HTTPError as e:
        return e.code, ""
    except urllib.error.URLError as e:
        return None, f"{type(e.reason).__name__}: {e.reason}"
    except Exception as e:         # noqa: BLE001 — one bad host must not stop the sweep
        return None, f"{type(e).__name__}: {e}"


def probe(url):
    """(status, note). HEAD, then GET, then GET as a browser."""
    for ua in (UA, BROWSER_UA):
        for method in ("HEAD", "GET"):
            status, note = _attempt(url, method, ua)
            if status and 200 <= status < 400:
                return status, note
            if status not in (403, 405, 429, 501, None):
                return status, note      # a real 404/500: believe it
        if status is None:
            return status, note          # DNS or connection failure: believe it
    return status, note


# Second-level domain, i.e. what somebody had to buy. www./m./secure. prefixes
# and country suffixes are noise; whether the *registrable* name changed is the
# whole question.
def _base(url):
    host = re.sub(r"^https?://", "", (url or "").strip()).split("/")[0].lower()
    host = re.sub(r":\d+$", "", host)
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "gov", "ac", "edu"):
        return ".".join(parts[-3:])        # example.co.uk
    return ".".join(parts[-2:])


# Known and legitimate. Each one is a real organisation that publishes under a
# second name, checked by hand — not a pattern, a list, so a NEW off-domain
# redirect is always reported.
SAME_ORG = {
    frozenset({"nyc.gov", "cityofnewyork.us"}),
    frozenset({"nyc.gov", "nyc988.cityofnewyork.us"}),
    frozenset({"ny.gov", "nystateofhealth.ny.gov"}),
    frozenset({"cuny.edu", "cuny.edu"}),
}


def offsite(url, final):
    """Did following this link land on somebody else's domain?

    This is the check that caught ppgny.org, which Planned Parenthood of
    Greater New York had let lapse: it 301'd to a marketing domain and then to
    an unrelated commercial site, and the directory had been quietly sending
    people looking for reproductive health care there. A redirect that changes
    the registrable domain is the signature of exactly that, and it is not the
    same class of finding as a trailing slash.
    """
    a, b = _base(url), _base(final)
    if a == b or not b:
        return False
    return frozenset({a, b}) not in SAME_ORG


def main():
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("Website") or "").strip()]

    targets = [(r["Resource Name"].strip(), r["Website"].strip()) for r in rows]
    print(f"checking {len(targets)} websites\n", flush=True)

    ok, redirects, blocked, dead, hijacked = [], [], [], [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(probe, url): (name, url) for name, url in targets}
        for fut in concurrent.futures.as_completed(futures):
            name, url = futures[fut]
            status, note = fut.result()
            if status and 200 <= status < 300:
                if note and offsite(url, note):
                    hijacked.append((name, url, note))
                elif note:
                    redirects.append((name, url, note))
                else:
                    ok.append((name, url, note))
            elif status in (401, 403, 429):
                blocked.append((name, url, status))
            else:
                dead.append((name, url, status or note))
            print(".", end="", flush=True)

    print("\n")
    print(f"reachable          {len(ok)}")
    print(f"reachable via redirect {len(redirects)}")
    print(f"blocked our request    {len(blocked)}  (probably fine in a browser)")
    print(f"FAILED             {len(dead)}")

    if hijacked:
        print("\n" + "=" * 70)
        print("-- LEFT ITS OWN DOMAIN. TREAT AS UNSAFE UNTIL A HUMAN LOOKS. --")
        print("   A charity's site does not normally redirect to a different")
        print("   organisation. The usual cause is that the domain lapsed and")
        print("   somebody else bought it, which turns this directory into a")
        print("   list of somewhere else's traffic. Do not 'fix' these by")
        print("   following the redirect.")
        print("=" * 70)
        for name, url, to in sorted(hijacked):
            print(f"  {name}\n      {url}\n   -> {to}")
    if redirects:
        print("\n-- moved (update the CSV to the new address) --")
        for name, url, to in sorted(redirects):
            print(f"  {name}\n      {url}\n   -> {to}")
    if blocked:
        print("\n-- refused a scripted request; verify by hand before touching --")
        for name, url, code in sorted(blocked):
            print(f"  [{code}] {name}  {url}")
    if dead:
        print("\n-- NOT REACHABLE --")
        for name, url, why in sorted(dead):
            print(f"  [{why}] {name}  {url}")

    return 1 if (dead or hijacked) else 0


if __name__ == "__main__":
    sys.exit(main())
