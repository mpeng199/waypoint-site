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

  * A page can be gone and still answer 200. SOFT_404 below catches the common
    phrasings in a server-rendered body and reports the link as dead.

    It does NOT catch the case that prompted it, and that is worth knowing
    rather than assuming otherwise. nyc.gov answered the dead ActionNYC URL
    with 200, no redirect, and a 6 KB JavaScript shell; the words "you have
    reached an outdated or non-existing page" are written into the page by
    script, after load. Nothing that does not run JavaScript can see them.
    Finding that one took opening the URL in a real browser, and a page that
    matters — a hotline, an intake number — is worth opening by hand once a
    quarter for exactly this reason.
  * A 403/429 usually means the host blocks scripted requests. Those are
    reported separately so nobody "fixes" a working link by deleting it.
  * Some WAFs fingerprint the TLS handshake, not the User-Agent, and answer
    Python with a 503 no matter what it claims to be.
    `https://nystateofhealth.ny.gov` is the standing example: 503 here, 200 in
    curl and in a browser. Cross-check anything in the failure list with
    `curl -IL <url>` before believing it.

With --stamp it also re-dates the rows the phone sweep can never confirm: the
ones with no phone at all, and the ones whose "phone" is a short code like 311
or 988 that no organisation prints on its own site. For those rows, verifying
means confirming the site is live and still on the organisation's own domain,
which is exactly what this does — so the date they carry means that, and
DESIGN.md says so. Nothing with a real phone number is stamped here;
verify_phones.py owns those.

Redirects are reported but are usually not worth chasing — most are a trailing
slash, a dropped www, or a locale prefix, and the reader never sees them. Chase
the ones where the path itself changed.
"""

import csv
import datetime as dt
import datetime
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
            # A GET is the only way to see a page that answers 200 and says it
            # is gone. Only the first 40 KB: the message is always near the top
            # and some of these hosts serve megabytes.
            if method == "GET" and r.status == 200:
                body = r.read(40000).decode("utf-8", "replace")
                if SOFT_404.search(re.sub(r"<[^>]+>", " ", body)):
                    return 404, "answers 200 and says the page is gone"
            return r.status, r.url if r.url.rstrip("/") != url.rstrip("/") else ""
    except urllib.error.HTTPError as e:
        return e.code, ""
    except urllib.error.URLError as e:
        return None, f"{type(e.reason).__name__}: {e.reason}"
    except Exception as e:         # noqa: BLE001 — one bad host must not stop the sweep
        return None, f"{type(e).__name__}: {e}"


def selfcheck_hosts():
    """Which hosts can be believed, and which need a person with a browser."""
    for u in ("https://www.nyc.gov/site/hra/help/snap-benefits-food-program.page",
              "https://finder.nyc.gov/foodhelp/locations"):
        assert needs_a_browser(u), f"{u} is a shell and must be flagged"
    for u in ("https://access.nyc.gov/programs/snap/",
              "https://www.schools.nyc.gov/school-life/health-and-wellness/x",
              "https://www.masbia.org", "https://oasas.ny.gov/harm-reduction"):
        assert not needs_a_browser(u), f"{u} serves its content and must not be flagged"
    return True


def selfcheck():
    """SOFT_404 has to match what hosts actually say, and nothing else.

    Every string below is real. The "not gone" list matters more than the
    other one: a false positive here deletes a working resource from a
    directory somebody is relying on.
    """
    gone = [
        "You have reached an outdated or non-existing page",
        "The page you are looking for could not be found",
        "Sorry, this page cannot be found",
        "404 Error",
        "This page no longer exists",
        "The page you requested was not found.",
        "this page has moved",
    ]
    fine = [
        "Find help with the cost of medicine.",
        "We could not find a pantry near that address — try another ZIP",
        "Page 404 of our annual report",
        "404 Broadway, Suite 200",
        "Sorry, this page is only available in English",
        "If you cannot be reached by phone we will write to you",
    ]
    for t in gone:
        assert SOFT_404.search(t), f"missed a real 'page is gone': {t!r}"
    for t in fine:
        assert not SOFT_404.search(t), f"would delete a working page over: {t!r}"
    return len(gone), len(fine)


def _says_it_is_gone(url):
    """A 200 whose body says the page is not there. Returns a note or ""."""
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": BROWSER_UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                return ""
            body = r.read(40000).decode("utf-8", "replace")
    except Exception:              # noqa: BLE001 — a body we cannot read proves nothing
        return ""
    if SOFT_404.search(re.sub(r"<[^>]+>", " ", body)):
        return "answers 200 and says the page is gone"
    return ""


def probe(url):
    """(status, note). HEAD, then GET, then GET as a browser.

    A HEAD that answers 200 is not the end of it: a page can be gone and still
    answer 200 with "you have reached an outdated or non-existing page" in the
    body, which is exactly how a dead immigration-hotline link sat in this
    directory being reported as reachable. So a 200 from HEAD is followed by
    one GET to read what the page actually says.
    """
    for ua in (UA, BROWSER_UA):
        for method in ("HEAD", "GET"):
            status, note = _attempt(url, method, ua)
            if status and 200 <= status < 400:
                if status == 200:
                    # nyc.gov answers HEAD with 200 and this UA's GET with 403,
                    # so the body has to be asked for as a browser or the
                    # "outdated page" notice is never seen.
                    gone = _says_it_is_gone(url)
                    if gone:
                        return 404, gone
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


# Bot walls. A Radware/Cloudflare/Akamai challenge redirects to the vendor's
# own domain and then back, which looks exactly like a takeover and is not one.
# Reporting those in the loudest section on the page is how the loudest section
# stops being read, so they are named and demoted.
BOT_WALLS = ("perfdrive.com", "validate.perfdrive.com", "challenges.cloudflare.com",
             "geo.captcha-delivery.com", "datadome.co", "hcaptcha.com",
             "akamaized.net", "incapsula.com", "imperva.com", "sucuri.net")


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
    if any(w in final for w in BOT_WALLS):
        return False
    return frozenset({a, b}) not in SAME_ORG


TEN_DIGITS = re.compile(r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}")


def unverifiable_by_phone(row):
    """Rows verify_phones.py can never confirm, however long it runs.

    Its definition, not a second one: it looks for ten-digit numbers and skips
    a row that has none. So this asks the same question — is there a ten-digit
    number here — rather than keeping a list of short codes beside it. The
    first draft did keep such a list and two rows fell between the two tools:
    "988 then press 1 / text 838255" and "Text FOOD to 726879" have digits in
    them, none of which is a phone number either tool could check.

    For these rows "we checked this" can only mean the site is live and is
    still on the organisation's own domain, which is what this file does.
    """
    for m in TEN_DIGITS.findall(row.get("Phone") or ""):
        if len(re.sub(r"\D", "", m).lstrip("1")) == 10:
            return False
    return True


# A 200 that says the page is gone. Every one of these is a real string from a
# real host: nyc.gov's is the one that hid a dead immigration-hotline link.
# Hosts that build their pages in the browser. A 200 from one of these proves
# the server answered, not that the page exists: nyc.gov serves a full
# navigation shell with no article in it and writes "you have reached an
# outdated or non-existing page" from script afterwards. The dead SNAP page and
# the live Homebase page are byte-for-byte indistinguishable to anything that
# does not run JavaScript — same length, same chrome, same everything.
#
# So these are not reported as reachable. They are listed separately, to be
# opened by hand. `--browser-list` prints just the URLs.
# Two hosts, not all of nyc.gov: access.nyc.gov and schools.nyc.gov serve
# their content in the HTML and can be read here. www.nyc.gov's CMS does not,
# and finder.nyc.gov serves a 1.7 KB shell.
# nystateofhealth.ny.gov joins them for a different reason: it answers a
# scripted request with 503 and a browser with the page. Two sweeps in a row
# reported it NOT REACHABLE while it was serving 855-355-5777 to anyone who
# opened it. A failure list is only worth reading if everything on it is a real
# failure, so this one moves to the list a person checks.
NEEDS_A_BROWSER = ("www.nyc.gov", "nyc.gov", "finder.nyc.gov",
                   "nystateofhealth.ny.gov")
# What a person saw when they last opened them, and when.
BROWSER_LOG = "data/browser-checked.txt"
SERVES_ITS_CONTENT = ("access.nyc.gov", "schools.nyc.gov", "on.nyc.gov",
                      "a069-access.nyc.gov", "home.nyc.gov")


SOFT_404 = re.compile(
    r"you have reached an outdated or non-existing page"
    r"|page (?:you (?:are looking for|requested) )?(?:could not be|cannot be|was not) found"
    r"|this page (?:no longer exists|has moved|is no longer available)"
    r"|404 (?:error|not found)"
    # "sorry, this page" needs what follows it: "sorry, this page is only
    # available in English" is a working page saying something useful.
    r"|sorry,? (?:this|that) page (?:cannot be|could not be|is not|does not|no longer)",
    re.I)


def needs_a_browser(url):
    host = re.sub(r"^https?://", "", (url or "")).split("/")[0].lower()
    if host in SERVES_ITS_CONTENT:
        return False
    return host in NEEDS_A_BROWSER


def main():
    stamp = "--stamp" in sys.argv
    if "--browser-list" in sys.argv:
        with open(CSV, encoding="utf-8-sig", newline="") as f:
            urls = sorted({r["Website"].strip() for r in csv.DictReader(f)
                           if needs_a_browser(r.get("Website"))})
        # What the last pass found, so this prints a to-do rather than a list.
        seen, oldest = {}, None
        try:
            with open(BROWSER_LOG, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#") or not line.strip():
                        continue
                    when, title, url = line.rstrip("\n").split("\t")
                    seen[url] = (when, title)
                    oldest = when if oldest is None else min(oldest, when)
        except FileNotFoundError:
            pass

        for u in urls:
            if u in seen:
                when, title = seen[u]
                print(f"  {when}  {title[:44]:46}  {u}")
            else:
                print(f"  {'NEVER':10}  {'—':46}  {u}")
        missing = [u for u in urls if u not in seen]
        stale = [u for u in seen if u not in urls]
        print(f"\n{len(urls)} page(s) that only a browser can verify.")
        if missing:
            print(f"{len(missing)} of them have never been opened. Open each and "
                  f"read the title: nyc.gov's soft 404 is titled \"Page Not "
                  f"Found\", so a title naming the subject is a live page.")
        if stale:
            print(f"{len(stale)} line(s) in {BROWSER_LOG} are for URLs no longer "
                  f"in the directory; they can go.")
        if oldest and not missing:
            age = (dt.date.today() - dt.date.fromisoformat(oldest)).days
            print(f"Oldest check: {oldest} ({age} days ago)."
                  + ("  Due — redo the pass." if age > 92 else "  Redo quarterly."))
        print(f"Record a pass in {BROWSER_LOG}: date, title, URL, tab-separated.")
        return 0
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.DictReader(f))
    rows = [r for r in all_rows if (r.get("Website") or "").strip()]

    targets = [(r["Resource Name"].strip(), r["Website"].strip()) for r in rows]
    print(f"checking {len(targets)} websites\n", flush=True)

    ok, redirects, blocked, dead, hijacked, tls = [], [], [], [], [], []
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
            elif status in (401, 403, 429) or (status in (307, 302) and not note):
                # A 3xx with nothing to follow is a JavaScript challenge
                # (Sucuri, Cloudflare) sitting in front of a live site, not a
                # dead link. Believing it kills good resources.
                blocked.append((name, url, status))
            elif isinstance(note, str) and "CERTIFICATE_VERIFY_FAILED" in note:
                tls.append((name, url))
            else:
                dead.append((name, url, status or note))
            print(".", end="", flush=True)

    print("\n")
    # A host on this list is one a script cannot judge, whatever it answered.
    # Pull it out of every bucket, not just the happy ones: nystateofhealth
    # answers 503 to a script and serves the page to a browser, and reporting
    # that as NOT REACHABLE puts a live site on the list somebody is meant to
    # panic about.
    browser = [(n, u) for n, u, _x in ok + redirects + dead + blocked
               if needs_a_browser(u)]
    ok = [t for t in ok if not needs_a_browser(t[1])]
    redirects = [t for t in redirects if not needs_a_browser(t[1])]
    dead = [t for t in dead if not needs_a_browser(t[1])]
    blocked = [t for t in blocked if not needs_a_browser(t[1])]
    print(f"reachable          {len(ok)}")
    print(f"reachable via redirect {len(redirects)}")
    print(f"blocked our request    {len(blocked)}  (probably fine in a browser)")
    print(f"FAILED             {len(dead)}")
    print(f"only a browser can say  {len(browser)}  (see below)")

    if browser:
        print("\n-- a 200 here proves the server answered, not that the page "
              "exists --")
        print("   These hosts build the page in the browser, so a dead page and")
        print("   a live one look identical to this checker. Open them:")
        print("     python3 check_links_live.py --browser-list")
        for n, u in sorted(browser)[:6]:
            print(f"     {n[:38]:<38} {u}")
        if len(browser) > 6:
            print(f"     ... and {len(browser) - 6} more")

    if stamp:
        today = datetime.date.today().isoformat()
        live = {name for name, _u, _n in ok} | {name for name, _u, _n in redirects}
        n = 0
        for r in all_rows:
            if (r["Resource Name"].strip() in live
                    and unverifiable_by_phone(r)
                    and r.get("Last Verified", "") < today):
                r["Last Verified"] = today
                n += 1
        if n:
            cols = list(all_rows[0].keys())
            with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
                w.writeheader()
                w.writerows(all_rows)
        print(f"\nstamped {n} row(s) that have no phone to verify: their site "
              f"answered, on their own domain, today")

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
    if tls:
        print("\n-- BROKEN HTTPS. Drop these unless the host fixes it. --")
        print("   The server is not sending its full certificate chain. A")
        print("   current desktop browser papers over that; a six-year-old")
        print("   Android shows a full-screen security warning instead of the")
        print("   page. That is the device this directory is written for, and")
        print("   a scare like that is worse than the resource being missing.")
        for name, url in sorted(tls):
            print(f"  {name}  {url}")
    if blocked:
        print("\n-- refused a scripted request; verify by hand before touching --")
        for name, url, code in sorted(blocked):
            print(f"  [{code}] {name}  {url}")
    if dead:
        print("\n-- NOT REACHABLE --")
        for name, url, why in sorted(dead):
            print(f"  [{why}] {name}  {url}")

    return 1 if (dead or hijacked or tls) else 0


if __name__ == "__main__":
    sys.exit(main())
