#!/usr/bin/env python3
"""Collect free public events in New York City into data/events.json.

Deliberately outside check.py, for the same reason check_links_live.py and
verify_phones.py are: it talks to other people's servers. A guard suite has to
give the same answer on a plane.

Run it:  python3 fetch_events.py            # fetch, write data/events.json
         python3 fetch_events.py --dry-run  # fetch, print a summary, write nothing
         python3 fetch_events.py --offline  # re-normalise what is already on disk

WHAT IS IN HERE AND WHY

Every source below was opened and checked before it was written down. Three
that look obvious are not here, and the reason each is missing is worth more
than the line it would have taken:

  * NYC Open Data "Parks Events Listing" (fudw-fgrp) answers 200 with clean
    JSON and its newest event is 28 Dec 2019. A feed can be alive and dead at
    the same time; `--dry-run` prints the newest date of every source so this
    kind of death is visible rather than silent.
  * NYPL sits behind Incapsula and answers a bot-check page to anything
    without a browser.
  * Brooklyn and Queens libraries publish no feed at any of the usual paths.

The city's libraries are the biggest free-programming provider in New York and
the omission is a real hole. It needs a browser to fill, which belongs in
check_links_live.py's --browser-list pass, not here.

ADDING A SOURCE

Append to SOURCES. A WordPress site running The Events Calendar plugin —
which a surprising number of nonprofits do — exposes every event at
`/wp-json/tribe/events/v1/events` with no key, so `kind="tribe"` is usually
all it takes. `kind="ics"` reads the iCalendar format that Luma, Partiful and
Google Calendar all export, so a calendar URL from any of them drops in with
no new code. Probe a candidate first:

    curl -s '<site>/wp-json/tribe/events/v1/events?per_page=2' | head -c 400
"""

import argparse
import html as _html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, date
from pathlib import Path

OUT = Path("data/events.json")

# How far ahead to keep. Past today is dropped on every run, so the file is
# self-cleaning: nothing has to remember to delete last week.
HORIZON_DAYS = 120

# Per source, so one prolific publisher cannot crowd out the rest. NYC Parks
# alone returns over a thousand.
PER_SOURCE = 260

# And per source per day. Without this the cap above is spent chronologically:
# NYC Parks filled all 220 slots with the next three days and the rest of the
# calendar was empty from the fourth day on. A calendar is judged by its thin
# days, not its thick ones.
PER_SOURCE_DAY = 8

TIMEOUT = 30
UA = "WaypointNYC/1.0 (+https://waypointnyc.org) free-event-directory"


# --------------------------------------------------------------- the sources
#
# `need` is the Waypoint category an event files under when its own source
# says nothing more specific. `trust_free` marks a source whose events are all
# free — the two mobile programs are, by their own description; a park event
# may carry a materials fee, so it is not claimed to be free unless it says so.
SOURCES = [
    {
        "key": "nylag",
        "name": "New York Legal Assistance Group",
        "kind": "tribe",
        "url": "https://nylag.org/wp-json/tribe/events/v1/events",
        "site": "https://nylag.org/",
        "need": "legal",
        "trust_free": True,
        "note": "Free legal help, including the Mobile Legal Help Center van.",
    },
    {
        "key": "foodbank",
        "name": "Food Bank For New York City",
        "kind": "tribe",
        "url": "https://www.foodbanknyc.org/wp-json/tribe/events/v1/events",
        "site": "https://www.foodbanknyc.org/",
        "need": "food",
        "trust_free": True,
        "note": "Mobile pantry distributions.",
    },
    {
        "key": "parks",
        "name": "NYC Parks",
        "kind": "parks-rss",
        "url": "https://www.nycgovparks.org/xml/events_300_rss.xml",
        "site": "https://www.nycgovparks.org/events",
        # Not "family". Most park events match no Waypoint need at all, and
        # defaulting them to one labelled a tai chi class and an adult 5K
        # "Kids & young people". Events that really are for children still
        # reach "family" through the word list above; the rest say what they
        # are. A fallback that names the wrong thing is worse than a vague one.
        "need": "other",
        "trust_free": False,
        "note": "Free and low-cost programming in the city's parks.",
    },
    # An iCalendar source looks like this. Luma exposes one per public
    # calendar, Partiful one per event, Google Calendar one per calendar.
    # {
    #     "key": "somecal", "name": "Some Organisation", "kind": "ics",
    #     "url": "https://api.lu.ma/ics/get?entity=calendar&id=cal-XXXX",
    #     "site": "https://lu.ma/someorg", "need": "start",
    #     "trust_free": True, "note": "",
    # },
]


# ------------------------------------------------------------------ plumbing

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, application/rss+xml, text/calendar, */*",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
    # NYC Parks serves iso-8859-1 and says so; everything else is utf-8.
    for enc in ("utf-8", "iso-8859-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


TAGS = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def text(s, limit=260):
    """Third-party HTML down to one clean line.

    Event descriptions arrive as marketing HTML with entities, newlines and
    the occasional <script>. Nothing here is trusted into the page as markup —
    build_help.esc() escapes it again at render time. This is only about
    making it readable.
    """
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>", " ", s)
    s = TAGS.sub(" ", s)
    s = _html.unescape(s)
    s = s.replace(" ", " ").replace("​", "")
    s = SPACE.sub(" ", s).strip()
    if len(s) > limit:
        cut = s[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-")
        s = cut + "…"
    return s


BOROUGHS = {
    "manhattan": "Manhattan", "new york": "Manhattan", "ny": "Manhattan",
    "brooklyn": "Brooklyn", "bklyn": "Brooklyn",
    "queens": "Queens", "bronx": "Bronx", "the bronx": "Bronx",
    "staten island": "Staten Island",
}

# Neighbourhoods that arrive in the city field instead of a borough. Only the
# ones the live feeds actually produced are here; guessing at the rest would
# put a made-up borough under a real address.
NEIGHBOURHOOD = {
    "st. albans": "Queens", "saint albans": "Queens", "jamaica": "Queens",
    "east elmhurst": "Queens", "elmhurst": "Queens", "flushing": "Queens",
    "corona": "Queens", "astoria": "Queens", "far rockaway": "Queens",
    "long island city": "Queens", "ridgewood": "Queens", "woodside": "Queens",
    "jackson heights": "Queens", "rego park": "Queens", "forest hills": "Queens",
    "harlem": "Manhattan", "washington heights": "Manhattan", "inwood": "Manhattan",
    "bed-stuy": "Brooklyn", "bedford-stuyvesant": "Brooklyn",
    "bushwick": "Brooklyn", "flatbush": "Brooklyn", "sunset park": "Brooklyn",
    "coney island": "Brooklyn", "brownsville": "Brooklyn", "canarsie": "Brooklyn",
    "east new york": "Brooklyn", "williamsburg": "Brooklyn", "crown heights": "Brooklyn",
}


# Longest first, so "staten island" is tested before "island" could ever be
# added below it.
BORO_WORDS = [("staten island", "Staten Island"), ("manhattan", "Manhattan"),
              ("brooklyn", "Brooklyn"), ("queens", "Queens"),
              ("bronx", "Bronx")]


def borough(*candidates):
    for c in candidates:
        if not c:
            continue
        k = c.strip().lower().rstrip(",.")
        if k in BOROUGHS:
            return BOROUGHS[k]
        if k in NEIGHBOURHOOD:
            return NEIGHBOURHOOD[k]
    # Only unambiguous names are scanned for inside a longer string. "NY" and
    # "New York" are in BOROUGHS because a city field containing exactly that
    # means Manhattan — but scanned for as words they are inside every address
    # in the state, and "Brooklyn, NY" came back Manhattan because \bny\b
    # matched before \bbrooklyn\b ever got a turn.
    for c in candidates:
        if not c:
            continue
        low = c.lower()
        for k, v in BORO_WORDS:
            if re.search(rf"\b{re.escape(k)}\b", low):
                return v
    return ""


VIRTUAL = re.compile(
    r"(?i)\b(virtual|online|zoom|webinar|teams meeting|google meet|livestream|"
    r"remote|telephonic|by phone|web-based)\b")


def fmt_of(*blobs):
    joined = " ".join(b for b in blobs if b)
    return "Virtual" if VIRTUAL.search(joined) else "In person"


FREE = re.compile(r"(?i)\b(free|no cost|no charge|at no cost|complimentary)\b")


def is_free(src, *blobs):
    if src.get("trust_free"):
        return True
    joined = " ".join(b for b in blobs if b)
    if re.search(r"(?i)\$\s?\d", joined):
        return False
    return bool(FREE.search(joined))


# Source vocabulary onto Waypoint's categories. Left as the source's own words
# where nothing fits: calling a tai chi class "Not safe at home" to make the
# taxonomy tidy would be a lie told by a lookup table.
#
# Every pattern here is anchored on words that carry the category ALONE.
# "clinic" does not, and filed a girls' softball clinic under "A doctor or
# dentist"; "health" does not, and did the same to a tai chi class whose
# description mentions health benefits. Both now need a medical word next to
# them. The rule the hard way: a word that is ordinary English outside the
# category cannot be trusted to name the category.
NEED_BY_WORD = [
    (r"(?i)\b(legal|lawyer|attorney|know your rights|eviction|tenant rights|"
     r"immigration help|asylum|deportation)\b", "legal"),
    (r"(?i)\b(pantry|food bank|free food|meal|grocer|nutrition|snap benefits|produce)\b", "food"),
    (r"(?i)\b(health (screening|clinic|fair|insurance)|medical clinic|free clinic|"
     r"vaccin|immuniz|dental|dentist|blood pressure|mental health|flu shot|"
     r"covid test)\b", "doctor"),
    (r"(?i)\b(housing|shelter|homeless|rent(al)? assistance)\b", "housing"),
    (r"(?i)\b(job fair|career|employment|resume|hiring|workforce|"
     r"english class|esol|ged|high school equivalency)\b", "work"),
    (r"(?i)\b(senior|older adult|aging)\b", "senior"),
    (r"(?i)\b(veteran)\b", "veterans"),
    (r"(?i)\b(accessible|disabilit|adaptive|sensory friendly)\b", "disability"),
    (r"(?i)\b(benefits enrollment|tax prep|vita site|financial counsel|debt)\b", "money"),
    (r"(?i)\b(kids|children|family|youth|teen|toddler|storytime|stroller)\b", "family"),
]


def need_for(src, title, kind, description):
    """What an event is about.

    Title and category first, description only if those two say nothing. A
    description is marketing copy and mentions everything: the tai chi listing
    sells "health benefits", which is not the same as being health care.
    """
    for blob in (f"{title} {kind}", description):
        if not blob or not blob.strip():
            continue
        for pat, key in NEED_BY_WORD:
            if re.search(pat, blob):
                return key
    return src["need"]


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def parse_dt(s):
    if not s:
        return None
    s = s.strip().replace("Z", "")
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
              "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(s[:len(datetime.now().strftime(f))], f)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s[:19])
    except ValueError:
        return None


# ------------------------------------------------------------------ adapters

def from_tribe(src, today, horizon):
    """The Events Calendar's REST API. Paged, 50 at a time."""
    out, page, seen_pages = [], 1, 0
    while len(out) < PER_SOURCE and seen_pages < 8:
        url = (f"{src['url']}?per_page=50&page={page}"
               f"&start_date={today:%Y-%m-%d}&end_date={horizon:%Y-%m-%d}")
        try:
            d = json.loads(fetch(url))
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
            break                      # a 400 past the last page is the normal end
        events = d.get("events") or []
        if not events:
            break
        for e in events:
            start = parse_dt(e.get("start_date"))
            if not start:
                continue
            v = e.get("venue") or {}
            place = text(v.get("venue"), 90)
            city = text(v.get("city"), 40)
            blurb = text(e.get("description") or e.get("excerpt"))
            cats = " ".join(c.get("name", "") for c in (e.get("categories") or []))
            img = e.get("image") or {}
            out.append({
                "title": text(e.get("title"), 120),
                "start": iso(start),
                "end": iso(parse_dt(e.get("end_date")) or start),
                "all_day": bool(e.get("all_day")),
                "venue": place,
                "borough": borough(city, v.get("address"), place, blurb),
                "address": text(v.get("address"), 90),
                "description": blurb,
                "url": e.get("url") or src["site"],
                "image": (img.get("url") if isinstance(img, dict) else None) or None,
                "kind": text(cats, 60) or src["name"],
                "format": fmt_of(place, blurb, cats, e.get("title")),
                "free": is_free(src, blurb, cats, e.get("cost")),
            })
        page += 1
        seen_pages += 1
    return out


ITEM = re.compile(r"<item>(.*?)</item>", re.S)


def _tag(block, name):
    m = re.search(rf"<{name}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>", block, re.S)
    return m.group(1).strip() if m else ""


# NYC Parks numbers every park with a borough letter in front: M072 is in
# Manhattan, X001 in the Bronx. It is the only borough the feed states outright
# — the location line is a landmark ("Soldiers' and Sailors' Monument") that
# names no borough at all, which is why 93 events had none.
PARK_BOROUGH = {"M": "Manhattan", "B": "Brooklyn", "Q": "Queens",
                "X": "Bronx", "R": "Staten Island"}


def from_parks_rss(src, today, horizon):
    """NYC Parks' RSS, which carries a full event schema in its own namespace."""
    body = fetch(src["url"])
    out = []
    for m in ITEM.finditer(body):
        b = m.group(1)
        d = parse_dt(_tag(b, "event:startdate"))
        if not d:
            continue
        st = _tag(b, "event:starttime")
        start = d
        tm = re.match(r"(?i)(\d{1,2}):(\d{2})\s*(am|pm)", st or "")
        if tm:
            h, mi, ap = int(tm.group(1)), int(tm.group(2)), tm.group(3).lower()
            h = (h % 12) + (12 if ap == "pm" else 0)
            start = d.replace(hour=h, minute=mi)
        end = parse_dt(_tag(b, "event:enddate")) or start
        et = re.match(r"(?i)(\d{1,2}):(\d{2})\s*(am|pm)", _tag(b, "event:endtime") or "")
        if et:
            h, mi, ap = int(et.group(1)), int(et.group(2)), et.group(3).lower()
            end = end.replace(hour=(h % 12) + (12 if ap == "pm" else 0), minute=mi)
        loc = _tag(b, "event:location") or _tag(b, "event:parknames")
        pid = _tag(b, "event:parkids").strip().upper()[:1]
        cats = _tag(b, "event:categories").replace("|", ", ")
        blurb = text(_tag(b, "description"))
        title = text(_tag(b, "title"), 120)
        img = _tag(b, "event:image") or None
        out.append({
            "title": title,
            "start": iso(start),
            "end": iso(max(end, start)),
            "all_day": not bool(tm),
            "venue": text(loc, 90),
            "borough": (PARK_BOROUGH.get(pid)
                        or borough(loc, _tag(b, "event:parknames"), blurb)),
            "address": text(_tag(b, "event:parknames"), 90),
            "description": blurb,
            # The feed's links are http; the site is https and every outbound
            # link on it has to be too.
            "url": (_tag(b, "link") or src["site"]).replace("http://", "https://"),
            "image": img.replace("http://", "https://") if img else None,
            "kind": text(cats, 60),
            "format": fmt_of(loc, blurb, cats, title),
            "free": is_free(src, blurb, title, cats),
        })
    return out


UNFOLD = re.compile(r"\r?\n[ \t]")


def from_ics(src, today, horizon):
    """iCalendar — what Luma, Partiful and Google Calendar all export."""
    body = UNFOLD.sub("", fetch(src["url"]))
    out = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", body, re.S):
        def prop(name):
            m = re.search(rf"^{name}[^:\r\n]*:(.*)$", block, re.M)
            return m.group(1).strip() if m else ""

        start = parse_dt(prop("DTSTART"))
        if not start:
            continue
        # RFC 5545 escapes, which arrive literally in SUMMARY and DESCRIPTION.
        def unesc(s):
            return (s.replace("\\n", " ").replace("\\,", ",")
                     .replace("\\;", ";").replace("\\\\", "\\"))

        loc = text(unesc(prop("LOCATION")), 90)
        blurb = text(unesc(prop("DESCRIPTION")))
        title = text(unesc(prop("SUMMARY")), 120)
        out.append({
            "title": title,
            "start": iso(start),
            "end": iso(parse_dt(prop("DTEND")) or start),
            "all_day": "VALUE=DATE" in (re.search(r"^DTSTART[^:\r\n]*", block, re.M)
                                        or type("x", (), {"group": lambda s: ""})()).group(0),
            "venue": loc,
            "borough": borough(loc, blurb),
            "address": loc,
            "description": blurb,
            "url": prop("URL") or src["site"],
            "image": None,
            "kind": src["name"],
            "format": fmt_of(loc, blurb, title),
            "free": is_free(src, blurb, title),
        })
    return out


ADAPTERS = {"tribe": from_tribe, "parks-rss": from_parks_rss, "ics": from_ics}


# --------------------------------------------------------------------- driver

def collect(today, horizon):
    got, report = [], []
    for src in SOURCES:
        try:
            rows = ADAPTERS[src["kind"]](src, today, horizon)
            err = ""
        except Exception as e:                       # noqa: BLE001
            # One source having a bad day must not empty the page. The old
            # file stays on disk and yesterday's events are still better than
            # none — but the run says so, loudly, and --dry-run shows it.
            rows, err = [], f"{type(e).__name__}: {e}"
        kept = []
        for r in rows:
            d = parse_dt(r["start"])
            if not d or d.date() < today or d.date() > horizon:
                continue
            if not r["title"]:
                continue
            r["source"] = src["name"]
            r["source_key"] = src["key"]
            r["source_url"] = src["site"]
            r["need"] = need_for(src, r["title"], r["kind"], r["description"])
            kept.append(r)
        kept.sort(key=lambda r: r["start"])
        per_day, spread = {}, []
        for r in kept:
            day = r["start"][:10]
            if per_day.get(day, 0) >= PER_SOURCE_DAY:
                continue
            per_day[day] = per_day.get(day, 0) + 1
            spread.append(r)
        kept = spread[:PER_SOURCE]
        got += kept
        newest = max((r["start"][:10] for r in kept), default="—")
        report.append({"key": src["key"], "name": src["name"], "n": len(kept),
                       "newest": newest, "error": err})
    return got, report


def dedupe(events):
    """Same title, same day, same place is one event however many feeds say it."""
    seen, out = {}, []
    for e in sorted(events, key=lambda r: (r["start"], r["title"])):
        k = (re.sub(r"\W+", "", e["title"].lower())[:50],
             e["start"][:10],
             re.sub(r"\W+", "", (e["venue"] or "").lower())[:30])
        if k in seen:
            continue
        seen[k] = True
        out.append(e)
    return out


def rank(e):
    """What earns a place in the six featured cards on the directory page.

    Sooner is better, a photo is better than none, and the two categories the
    rest of this site exists for outrank a yoga class.
    """
    d = parse_dt(e["start"])
    days = (d.date() - date.today()).days if d else 99
    s = 100 - min(days, 60)
    if e.get("image"):
        s += 22
    if e["need"] in ("food", "legal", "doctor", "housing", "money"):
        s += 30
    if e.get("free"):
        s += 8
    if e.get("borough"):
        s += 5
    if len(e.get("description") or "") > 60:
        s += 6
    return -s



# ------------------------------------------------------------- self-check
#
# check.py cannot reach any of this: it is offline by design and everything
# above talks to other people's servers. But the parsing and the filing are
# where the real bugs were, and all three below shipped once:
#
#   * a girls' softball CLINIC filed under "A doctor or dentist";
#   * a tai chi class filed the same way, because its description sells
#     "health benefits";
#   * every park event filed under "Kids & young people", because that was
#     the fallback.
#
# Run: python3 fetch_events.py --selfcheck

def selfcheck():
    parks = {"key": "parks", "name": "NYC Parks", "need": "other",
             "trust_free": False}
    legal = {"key": "nylag", "name": "NYLAG", "need": "legal",
             "trust_free": True}

    # --- filing: the words that carry a category, and the ones that do not
    assert need_for(parks, "Girl's Softball Clinic", "Sports", "") == "other", \
        "'clinic' alone must not mean health care"
    assert need_for(parks, "Summer on the Hudson: Tai Chi", "Fitness",
                    "a martial art with health benefits") == "other", \
        "a description mentioning health must not outvote the title"
    assert need_for(parks, "Free Dental Screening", "Health", "") == "doctor"
    assert need_for(parks, "Toddler Storytime", "Best for Kids", "") == "family"
    assert need_for(legal, "Van at Senator Comrie's office", "Mobile Legal "
                    "Help Center", "") == "legal"
    assert need_for(parks, "Mobile Pantry", "Food", "") == "food"
    # the fallback is the source's own, and for parks that is deliberately
    # not one of the directory's needs
    assert need_for(parks, "Kayaking", "Waterfront", "") == "other"

    # --- borough, including the park-id prefix that fixed 67 of them
    assert PARK_BOROUGH["X"] == "Bronx" and PARK_BOROUGH["R"] == "Staten Island"
    assert borough("East Elmhurst") == "Queens"
    assert borough("", "Brooklyn, NY") == "Brooklyn"
    assert borough("nowhere in particular") == ""

    # --- format
    assert fmt_of("Zoom", "", "") == "Virtual"
    assert fmt_of("Riverside Park", "wear sunscreen", "") == "In person"

    # --- third-party HTML down to one line, cut on a word boundary
    assert text("<p>Hello&nbsp;<b>there</b></p>") == "Hello there"
    assert text("<script>alert(1)</script>ok") == "ok"
    assert text("x" * 400).endswith("\u2026")
    assert "<" not in text("<img src=x onerror=y>hi")

    # --- times
    assert iso(parse_dt("2026-09-22 11:00:00")) == "2026-09-22T11:00:00"
    assert parse_dt("") is None and parse_dt("not a date") is None

    # --- dedupe: same title, same day, same place is one event
    def ev(t, d, v):
        return {"title": t, "start": d + "T10:00:00", "venue": v}
    assert len(dedupe([ev("Pantry", "2026-09-22", "Agatha House"),
                       ev("Pantry", "2026-09-22", "Agatha House"),
                       ev("Pantry", "2026-09-23", "Agatha House")])) == 2

    # --- ics, the format Luma and Partiful both export
    ics = ("BEGIN:VCALENDAR\n" "BEGIN:VEVENT\n"
           "SUMMARY:Free legal clinic\n"
           "DTSTART:20260922T140000\n" "DTEND:20260922T160000\n"
           r"LOCATION:123 Main St\, Brooklyn" "\n"
           "URL:https://lu.ma/x\n"
           "DESCRIPTION:Bring your papers\n"
           "END:VEVENT\nEND:VCALENDAR")
    src = {"key": "t", "name": "T", "site": "https://lu.ma/x",
           "need": "legal", "trust_free": True, "url": ""}
    global fetch
    real, fetch = fetch, lambda _u: ics
    try:
        rows = from_ics(src, date(2026, 1, 1), date(2027, 1, 1))
    finally:
        fetch = real
    assert len(rows) == 1, rows
    assert rows[0]["title"] == "Free legal clinic"
    assert rows[0]["start"] == "2026-09-22T14:00:00"
    assert rows[0]["borough"] == "Brooklyn"          # the escaped comma parsed
    assert rows[0]["url"] == "https://lu.ma/x"

    print("selfcheck ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, write nothing")
    ap.add_argument("--offline", action="store_true",
                    help="re-sort and re-filter data/events.json without fetching")
    ap.add_argument("--selfcheck", action="store_true",
                    help="run the offline assertions and exit")
    a = ap.parse_args()

    if a.selfcheck:
        selfcheck()
        return

    today = date.today()
    horizon = today + timedelta(days=HORIZON_DAYS)

    if a.offline:
        if not OUT.exists():
            sys.exit(f"{OUT} does not exist — run without --offline first.")
        events = json.loads(OUT.read_text("utf-8"))["events"]
        events = [e for e in events
                  if today <= (parse_dt(e["start"]) or datetime.min).date() <= horizon]
        report = []
    else:
        events, report = collect(today, horizon)

    events = dedupe(events)
    events.sort(key=lambda e: (e["start"], e["title"]))
    for i, e in enumerate(events):
        e["id"] = f'{e["source_key"]}-{e["start"][:10]}-{i:04d}'

    # One card per title. These feeds are full of weekly series, and the six
    # featured slots filled up with the same tai chi class on six Sundays.
    # One card per title, and at most two per category. Ranking alone filled
    # all six slots with the same legal van parked outside six different
    # offices — correctly scored, and a dull row that hides the other 135
    # events behind it.
    featured, titles, per_need = [], set(), {}
    for e in sorted(events, key=rank):
        t = re.sub(r"\W+", "", e["title"].lower())[:40]
        if t in titles or per_need.get(e["need"], 0) >= 2:
            continue
        titles.add(t)
        per_need[e["need"]] = per_need.get(e["need"], 0) + 1
        featured.append(e["id"])
        if len(featured) == 6:
            break

    doc = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "horizon": horizon.isoformat(),
        "sources": [{"key": s["key"], "name": s["name"], "site": s["site"],
                     "note": s["note"]} for s in SOURCES],
        "featured": featured,
        "events": events,
    }

    for r in report:
        flag = "  !! " + r["error"] if r["error"] else ""
        print(f'  {r["n"]:5d}  {r["name"]:38s} through {r["newest"]}{flag}',
              file=sys.stderr)
    print(f"  {len(events):5d}  kept after dedupe, {len(featured)} featured",
          file=sys.stderr)

    if a.dry_run:
        by = {}
        for e in events:
            by[e["need"]] = by.get(e["need"], 0) + 1
        print("\n  by category: " + ", ".join(f"{k} {v}" for k, v in
                                              sorted(by.items(), key=lambda x: -x[1])),
              file=sys.stderr)
        print("  wrote nothing (--dry-run)", file=sys.stderr)
        return

    if not events:
        # Refusing to write is the whole point: a total network failure would
        # otherwise replace a good file with an empty one and the site would
        # quietly lose its events page.
        sys.exit("no events from any source — leaving data/events.json alone")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(f"  wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
