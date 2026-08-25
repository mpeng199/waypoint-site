#!/usr/bin/env python3
"""Ask each resource's own website whether the number we print is its number.

Deliberately NOT part of check.py, for the same reason check_links_live.py is
not: it talks to three hundred third-party servers and its answer depends on
the weather. Run it on its own, periodically:

    python3 verify_phones.py            # everything
    python3 verify_phones.py --stale    # only rows verified before this month
    python3 verify_phones.py --stamp    # ... and date the ones it confirms

What it is for: a link check proves the site is up. It does not prove the
number beside it still rings the same desk. A directory whose numbers have
quietly drifted is worse than one with fewer entries, because the person
dialling has no way to tell.

Three outcomes, and only the first is good news:

  CONFIRMED  the number we print appears on the organisation's own page
  OTHER      the page answers, but with different numbers — listed, for a human
  UNSEEN     the page did not answer, or renders its number in JavaScript

Nothing is edited automatically except the date, and only with `--stamp`, and
only on a CONFIRMED row. What `Last Verified` then means for that row is
precise: on that day, the organisation's own website printed the number this
directory prints. It does not mean the hours or the address were re-checked.

OTHER especially needs a person: an organisation legitimately publishes a
switchboard on its homepage and an intake line on a subpage, and swapping one
for the other can send somebody in crisis to a receptionist. That is not
hypothetical — the pass that introduced this tool found six numbers that had
drifted, including a hotline that was one digit wrong.
"""

import datetime
import concurrent.futures
import csv
import html
import re
import subprocess
import sys
from pathlib import Path

CSV = Path(__file__).parent / "data" / "resources.csv"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
PHONE = re.compile(r"(?:1[-. ]?)?\(?\b[2-9]\d{2}\)?[-. ]?\d{3}[-. ]\d{4}\b")


# Disagreements that a person has already looked at and settled. Each entry
# is a reason, not a mute: an organisation legitimately publishes a
# switchboard on the page a link check lands on and the number somebody
# actually needs somewhere else. Keeping them out of the report is what keeps
# the report worth reading — but a NEW disagreement always shows up.
SETTLED = {
    "211 New York":
        "we print the 211 short code and the statewide line; the site's footer "
        "shows the Capital Region office",
    "Adult Protective Services (APS)":
        "we print the central APS line; the page lists the five borough offices",
    "National Domestic Violence Hotline":
        "we print the hotline; the site shows press and administrative lines",
    "Good Days":
        "we print the patient assistance line; the site shows its Texas office",
    "Planned Parenthood of Greater New York":
        "we print PPGNY's main line; the national site lists health centres "
        "across the country",
    "SAMHSA National Helpline":
        "we print 1-800-662-HELP; the site shows the disaster and TTY lines",
    "WIC (Women, Infants & Children)":
        "we print the Growing Up Healthy hotline; the state page shows its "
        "Albany office",
}


def digits(s):
    d = re.sub(r"\D", "", s or "")
    return d[1:] if len(d) == 11 and d.startswith("1") else d


def ours(cell):
    """Every number the CSV prints for this row, as ten digits."""
    out = []
    for m in PHONE.findall(cell or ""):
        d = digits(m)
        if len(d) == 10 and d not in out:
            out.append(d)
    return out


def fetch(url):
    try:
        p = subprocess.run(
            ["curl", "-sL", "--max-time", "25", "-A", UA,
             "-H", "Accept: text/html,application/xhtml+xml",
             "-H", "Accept-Language: en-US,en;q=0.9", url],
            capture_output=True, text=True, timeout=45)
        body = p.stdout
    except Exception:
        return None
    if not body.strip():
        return None
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", body,
                  flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))


# Where an organisation keeps its phone number when the front page does not.
# Plenty of sites draw the homepage number in JavaScript, or put it only on
# the page whose whole job is to carry it — and reporting those as "we could
# not see it" is a report with eighty entries nobody reads.
CONTACT_PATHS = ("/contact", "/contact-us", "/contact/", "/contact-us/",
                 "/about/contact", "/about-us/contact-us/", "/about/contact-us",
                 "/get-help", "/get-help/", "/gethelp", "/help",
                 "/contact-and-directions/", "/locations", "/locations/",
                 "/services", "/programs", "/about", "/about-us")


def root(url):
    m = re.match(r"(https?://[^/]+)", (url or "").strip())
    return m.group(1) if m else ""


def one(row):
    name, url, cell = row["Resource Name"], row["Website"], row["Phone"]
    mine = ours(cell)
    if not url or not mine:
        return name, "SKIP", ""
    text = fetch(url)
    if text is None:
        return name, "UNSEEN", "site did not answer"

    # 212-639-9675 is 311's direct line and sits in the footer of every
    # nyc.gov page, so it "disagrees" with every City programme number on the
    # site. Noise, not a finding.
    NOISE = {"2126399675"}

    def numbers(t):
        return {d for d in (digits(m) for m in PHONE.findall(t))
                if len(d) == 10} - NOISE

    found = numbers(text)
    # If the page we landed on shows nothing, or shows numbers but not ours,
    # ask the page whose job it is to carry the number before deciding.
    if not (found & set(mine)):
        base = root(url)
        for path in CONTACT_PATHS:
            if base and base + path == url.rstrip("/"):
                continue
            more = fetch(base + path) if base else None
            if not more:
                continue
            here = numbers(more)
            found |= here
            if here & set(mine):
                break
    if any(d in found for d in mine):
        return name, "CONFIRMED", ""
    if not found:
        return name, "UNSEEN", "no phone number in the page's text"
    if name in SETTLED:
        return name, "SETTLED", SETTLED[name]
    show = ", ".join(sorted(found)[:6])
    return name, "OTHER", f"we print {cell[:28]!r}; the page shows {show}"


def main(argv):
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if "--stale" in argv:
        rows = [r for r in rows if r["Last Verified"] < "2026-08"]
    print(f"asking {len(rows)} websites about the number we print\n", flush=True)

    tally = {}
    detail = []
    confirmed = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for name, verdict, note in pool.map(one, rows):
            tally[verdict] = tally.get(verdict, 0) + 1
            if verdict == "CONFIRMED":
                confirmed.add(name)
            if verdict in ("OTHER", "UNSEEN"):
                detail.append((verdict, name, note))
            print(".", end="", flush=True)
    print("\n")

    if "--stale" not in argv:
        gone = sorted(set(SETTLED) - {r["Resource Name"] for r in rows})
        healed = sorted(set(SETTLED) & confirmed)
        if gone or healed:
            print("\n-- entries in SETTLED that no longer earn their place --")
            for name in gone:
                print(f"  {name} — the resource is not in the directory any more")
            for name in healed:
                print(f"  {name} — now confirmed, so the exception can go")

    if "--stamp" in argv and confirmed:
        today = datetime.date.today().isoformat()
        with open(CSV, encoding="utf-8-sig", newline="") as f:
            allrows = list(csv.DictReader(f))
        n = 0
        for r in allrows:
            if r["Resource Name"] in confirmed and r["Last Verified"] != today:
                r["Last Verified"] = today
                n += 1
        cols = list(allrows[0].keys())
        with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(allrows)
        print(f"dated {n} confirmed row(s) {today}\n")
    for k in ("CONFIRMED", "SETTLED", "OTHER", "UNSEEN", "SKIP"):
        if k in tally:
            print(f"{k:10} {tally[k]}")
    for verdict in ("OTHER", "UNSEEN"):
        rows_ = [d for d in detail if d[0] == verdict]
        if not rows_:
            continue
        print(f"\n-- {verdict} --")
        for _, name, note in sorted(rows_):
            print(f"  {name}\n      {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
