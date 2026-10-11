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

HOSTS WITH NO FEED

A walk, a parade, a race or a night market has a page and no calendar feed.
Those go in data/events_curated.json, one row per event, after a person has
opened the page in a browser and read the date, the place and whether it is
free off the page itself. Each row records the day it was checked and what
the page said, and is carried until the day passes.

EVERY LINK HAS TO LEAD SOMEWHERE

A status code is not enough. The Food Bank's event pages answer 200 with a
complete site around an empty middle; a lapsed domain answers 200 from
whoever bought it. So a feed's link must show its own date in the words of
the page (says_date), and a redirect off the host's domain fails (base). The
featured row only takes links that pass.

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
import concurrent.futures
import hashlib
import html as _html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from pathlib import Path

OUT = Path("data/events.json")

# Events a person found and opened by hand, one organization each — the
# walks, parades, races and fairs that publish no feed. See from_curated().
CURATED = Path("data/events_curated.json")

# Photographs for the featured cards, downloaded here at fetch time and
# served from this origin. Hotlinking them would hand every reader's IP
# address to every host; privacy.html names exactly one third party.
PHOTOS = Path("assets/events")

# How many cards the featured row carries: one per organization, so this is
# also the most organizations it can show.
FEATURED = 24

# Under check.py's 120 KB per card photo, with room to spare.
PHOTO_MAX = 100_000

# The whole page. events.html is held to 110 KB gzipped by check.py, and a
# check that fails stops the daily job from committing anything; forty per
# source across thirty-one sources could reach twice that. The fetcher keeps
# the page inside the budget rather than letting a busy week stale the site.
MAX_EVENTS = 650

# How far ahead to keep. Past today is dropped on every run, so the file is
# self-cleaning: nothing has to remember to delete last week.
HORIZON_DAYS = 120

# Per source, so one prolific publisher cannot crowd out the rest. NYC Parks
# alone returns over a thousand.
# Forty, not sixty: with thirty-odd sources sixty made events.html 1 MB of
# HTML (99 KB gzipped) for a reader on a cheap phone. A prolific feed still
# shows two weeks ahead, and the daily run moves the window.
PER_SOURCE = 40

# And per source per day. Without this the cap above is spent chronologically:
# NYC Parks filled all 220 slots with the next three days and the rest of the
# calendar was empty from the fourth day on. A calendar is judged by its thin
# days, not its thick ones.
PER_SOURCE_DAY = 3

TIMEOUT = 30
# A browser's string with our name and address on the end. The bare
# "WaypointNYC/1.0" was refused (403) by Queens Botanical Garden's and
# CAMBA's firewalls, which turn away anything that does not look like a
# browser; this still says who is asking and where to find us.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36 "
      "WaypointNYC/1.0 (+https://waypointnyc.org)")


# --------------------------------------------------------------- the sources
#
# `need` is the Waypoint category an event files under when its own source
# says nothing more specific. `trust_free` marks a source whose events are all
# free — the two mobile programs are, by their own description; a park event
# may carry a materials fee, so it is not claimed to be free unless it says so.
# What a community board itself holds, as against what it lists (see the
# boards below).
# A board's own sessions. Not "town hall" (a senator's, listed by a board),
# not "public hearing" (Brooklyn 6 lists the Borough President's), and not a
# bare "meeting" (it lists the Park Slope Food Coop's members' meeting).
MEETINGS = r"(?i)\b(committee|full board|board meeting|monthly meeting)\b"

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
        "trust_free": r"(?i)pantry",
        # Its event pages are empty shells: a pantry's own page shows no date,
        # no place and no text, only the site's menus (opened 10 Oct 2026).
        # The address is in the feed, so the row keeps it, and the link goes
        # to the Food Bank's own map of where to get food.
        "fallback": "https://www.foodbanknyc.org/find-food/",
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
    # Eleven more that run The Events Calendar, found by probing ninety NYC
    # organizations' sites for the endpoint on 10 Oct 2026. Every one had an
    # event page opened in a browser first, and each showed its event — which
    # is not a given: the Food Bank's pages are empty shells (see blank_pages).
    #
    # file_by_words is off for all eleven: their categories are audience tags,
    # not topics. NAMI-NYC's "Family or Friend" means a group for relatives,
    # and word-filing labelled it "Kids & young people"; Prospect Park's
    # "Food Kids Lakeside" put a farmers market under "Older adults". Each
    # files under its own need instead, which is never wrong about it.
    {
        "key": "nami", "name": "NAMI-NYC", "kind": "tribe",
        "url": "https://naminycmetro.org/wp-json/tribe/events/v1/events",
        "site": "https://naminycmetro.org/", "need": "crisis", "trust_free": True,
        "file_by_words": False,
        "note": "Free mental health support groups and talks, many on Zoom.",
    },
    {
        "key": "prospect", "name": "Prospect Park Alliance", "kind": "tribe",
        "lists_others": True,
        "url": "https://www.prospectpark.org/wp-json/tribe/events/v1/events",
        "site": "https://www.prospectpark.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Nature walks, markets and family days in Prospect Park.",
    },
    {
        "key": "riverside", "name": "Riverside Park Conservancy", "kind": "tribe",
        "lists_others": True,
        "url": "https://riversideparknyc.org/wp-json/tribe/events/v1/events",
        "site": "https://riversideparknyc.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Concerts, walks and volunteer days in Riverside Park.",
    },
    {
        "key": "qbg", "name": "Queens Botanical Garden", "kind": "tribe",
        "url": "https://queensbotanical.org/wp-json/tribe/events/v1/events",
        "site": "https://queensbotanical.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Garden workshops, festivals and volunteer days in Flushing.",
    },
    {
        "key": "randalls", "name": "Randall's Island Park Alliance", "kind": "tribe",
        "url": "https://randallsisland.org/wp-json/tribe/events/v1/events",
        "site": "https://randallsisland.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Youth sports, farm days and volunteering on Randall's Island.",
    },
    {
        "key": "simuseum", "name": "Staten Island Museum", "kind": "tribe",
        "url": "https://www.statenislandmuseum.org/wp-json/tribe/events/v1/events",
        "site": "https://www.statenislandmuseum.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Workshops, talks and nature walks on Staten Island.",
    },
    {
        "key": "cmom", "name": "Children's Museum of Manhattan", "kind": "tribe",
        "url": "https://cmom.org/wp-json/tribe/events/v1/events",
        "site": "https://cmom.org/", "need": "family", "trust_free": False,
        "file_by_words": False,
        # Its feed leaves every venue empty; everything is at the museum.
        "place": ("Children's Museum of Manhattan", "Manhattan"),
        "note": "Story times, art and play for young children.",
    },
    {
        "key": "weeksville", "name": "Weeksville Heritage Center", "kind": "tribe",
        "url": "https://www.weeksvillesociety.org/wp-json/tribe/events/v1/events",
        "site": "https://www.weeksvillesociety.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Music, history and community days in Crown Heights.",
    },
    {
        "key": "littleisland", "name": "Little Island", "kind": "tribe",
        "url": "https://littleisland.org/wp-json/tribe/events/v1/events",
        "site": "https://littleisland.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Performances and evenings in the park on the Hudson.",
    },
    {
        "key": "fortune", "name": "The Fortune Society", "kind": "tribe",
        "url": "https://fortunesociety.org/wp-json/tribe/events/v1/events",
        "site": "https://fortunesociety.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Help for people coming home from jail or prison.",
    },
    {
        "key": "camba", "name": "CAMBA", "kind": "tribe",
        "url": "https://camba.org/wp-json/tribe/events/v1/events",
        "site": "https://camba.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Brooklyn help with housing, health, jobs and legal problems.",
    },
    {
        "key": "lesec", "name": "Lower East Side Ecology Center", "kind": "tribe",
        "url": "https://www.lesecologycenter.org/wp-json/tribe/events/v1/events",
        "site": "https://www.lesecologycenter.org/", "need": "other", "trust_free": True,
        "file_by_words": False,
        # Its titles are only the place ("Cambria Heights"); the kind is what
        # happens there, so the kind goes in front.
        "retitle": [(r"(?i)recycling", "Electronics recycling: {title}"),
                    (r"(?i)compost drop", "Food scrap drop-off: {title}")],
        "note": "Free electronics recycling and food scrap drop-offs around the city.",
    },
    {
        "key": "moca", "name": "Museum of Chinese in America", "kind": "tribe",
        "url": "https://www.mocanyc.org/wp-json/tribe/events/v1/events",
        "site": "https://www.mocanyc.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Walking tours, films and workshops about Chinese American history.",
    },
    # Community boards are the city's most local public meeting, and three of
    # the fifty-nine run this calendar (probed 10 Oct 2026; the rest answer
    # nothing at the same path). Anyone may attend and speak. Their calendars
    # list the neighborhood's events too — Brooklyn 6 carries a Nitehawk film
    # screening — and a card saying "Hosted by Brooklyn Community Board 6"
    # over a cinema's show would be false, so only their own meetings are kept.
    {
        "key": "brooklyncb6", "name": "Brooklyn Community Board 6", "kind": "tribe",
        "url": "https://brooklyncb6.cityofnewyork.us/wp-json/tribe/events/v1/events",
        "site": "https://brooklyncb6.cityofnewyork.us/", "need": "civic", "trust_free": True,
        "file_by_words": False, "keep_if": MEETINGS,
        "note": "Public meetings about Park Slope, Carroll Gardens, Red Hook and nearby, and local events.",
    },
    {
        "key": "manhattancb1", "name": "Manhattan Community Board 1", "kind": "tribe",
        "url": "https://manhattancb1.cityofnewyork.us/wp-json/tribe/events/v1/events",
        "site": "https://manhattancb1.cityofnewyork.us/", "need": "civic", "trust_free": True,
        "file_by_words": False, "keep_if": MEETINGS,
        "note": "Public meetings about Lower Manhattan.",
    },
    {
        "key": "queenscb3", "name": "Queens Community Board 3", "kind": "tribe",
        "url": "https://queenscb3.cityofnewyork.us/wp-json/tribe/events/v1/events",
        "site": "https://queenscb3.cityofnewyork.us/", "need": "civic", "trust_free": True,
        "file_by_words": False, "keep_if": MEETINGS,
        "note": "Public meetings about Jackson Heights, East Elmhurst and North Corona.",
    },
    # A second probe the same night, of borough presidents, the Council and
    # business improvement districts, found five more.
    {
        "key": "brooklynbp", "name": "Brooklyn Borough President", "kind": "tribe",
        "url": "https://www.brooklynbp.nyc.gov/wp-json/tribe/events/v1/events",
        "site": "https://www.brooklynbp.nyc.gov/", "need": "civic", "trust_free": True,
        "note": "Public hearings, resource fairs and know-your-rights sessions in Brooklyn.",
    },
    {
        "key": "cb14brooklyn", "name": "Brooklyn Community Board 14", "kind": "tribe",
        "url": "https://cb14brooklyn.com/wp-json/tribe/events/v1/events",
        "site": "https://cb14brooklyn.com/", "need": "civic", "trust_free": True,
        "file_by_words": False, "keep_if": MEETINGS,
        "note": "Public meetings about Flatbush, Midwood and Kensington.",
    },
    {
        "key": "cityparks", "name": "City Parks Foundation", "kind": "tribe",
        "lists_others": True,
        "url": "https://cityparksfoundation.org/wp-json/tribe/events/v1/events",
        "site": "https://cityparksfoundation.org/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Volunteer days in neighborhood parks, and free programs in them.",
    },
    {
        "key": "flatironnomad", "name": "Flatiron NoMad Partnership", "kind": "tribe",
        "lists_others": True,
        "url": "https://www.flatironnomad.nyc/wp-json/tribe/events/v1/events",
        "site": "https://www.flatironnomad.nyc/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Run clubs, shows and public events around the Flatiron plazas.",
    },
    {
        "key": "parkslope5th", "name": "Park Slope Fifth Avenue BID", "kind": "tribe",
        "lists_others": True,
        "url": "https://www.parkslopefifthavenuebid.com/wp-json/tribe/events/v1/events",
        "site": "https://www.parkslopefifthavenuebid.com/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Free advice for small businesses, and Fifth Avenue's street events.",
    },
    {
        "key": "cobblehill", "name": "Cobble Hill Association", "kind": "tribe",
        "lists_others": True,
        "url": "https://cobblehill.nyc/wp-json/tribe/events/v1/events",
        "site": "https://cobblehill.nyc/", "need": "other", "trust_free": False,
        "file_by_words": False,
        "note": "Park volunteer days and neighborhood events in Cobble Hill.",
    },
    {
        "key": "sichildrens", "name": "Staten Island Children's Museum", "kind": "tribe",
        "url": "https://sichildrensmuseum.org/wp-json/tribe/events/v1/events",
        "site": "https://sichildrensmuseum.org/", "need": "family", "trust_free": False,
        "file_by_words": False, "place": ("Staten Island Children's Museum", "Staten Island"),
        "note": "Workshops and play for young children at Snug Harbor.",
    },
    {
        "key": "wyckoff", "name": "Wyckoff Farmhouse Museum", "kind": "tribe",
        "url": "https://wyckoffmuseum.org/wp-json/tribe/events/v1/events",
        "site": "https://wyckoffmuseum.org/", "need": "other", "trust_free": False,
        "file_by_words": False, "place": ("Wyckoff Farmhouse Museum", "Brooklyn"),
        "note": "A weekly farmstand and family days at Brooklyn's oldest house.",
    },
    {
        "key": "dyckman", "name": "Dyckman Farmhouse Museum", "kind": "tribe",
        "url": "https://www.dyckmanfarmhouse.org/wp-json/tribe/events/v1/events",
        "site": "https://www.dyckmanfarmhouse.org/", "need": "other", "trust_free": False,
        "file_by_words": False, "place": ("Dyckman Farmhouse Museum", "Manhattan"),
        "note": "Festivals and history days in Inwood, in English and Spanish.",
    },
    # Squarespace sites answer ?format=json on an events page with the same
    # list the page shows. Three of the hosts checked by hand run on it.
    {
        "key": "essexmarket", "name": "Essex Market", "kind": "squarespace",
        "lists_others": True,
        "url": "https://www.essexmarket.nyc/events",
        "site": "https://www.essexmarket.nyc/", "need": "other", "trust_free": False,
        "file_by_words": False, "place": ("Essex Market", "Manhattan"),
        "note": "Free classes, music and tours in the Lower East Side market hall.",
    },
    {
        "key": "historic-richmond-town", "name": "Historic Richmond Town", "kind": "squarespace",
        "url": "https://www.historicrichmondtown.org/events",
        "site": "https://www.historicrichmondtown.org/", "need": "other", "trust_free": False,
        "file_by_words": False, "place": ("Historic Richmond Town", "Staten Island"),
        "note": "Tours, crafts and seasonal days at the living history village.",
    },
    {
        "key": "fortgreenepark", "name": "Fort Greene Park Conservancy", "kind": "squarespace",
        "lists_others": True,
        "url": "https://www.fortgreenepark.org/calendar",
        "site": "https://www.fortgreenepark.org/", "need": "other", "trust_free": False,
        "file_by_words": False, "place": ("Fort Greene Park", "Brooklyn"),
        "note": "Yoga, run clubs, history walks and volunteer days in Fort Greene Park.",
    },
    {
        "key": "curated", "name": "Checked by hand", "kind": "curated",
        "url": "", "site": "", "need": "other", "trust_free": False, "note": "",
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

def fetch_bytes(url, final=None):
    """GET url. With `final` (a list), the address it ended up at is appended."""
    url = urllib.parse.quote(url, safe=":/?&=%#+,;@~!$'()*")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, application/rss+xml, text/calendar, */*",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        if final is not None:
            final.append(r.geturl())
        return r.read(8_000_000)


def fetch(url, final=None):
    raw = fetch_bytes(url, final)
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


def is_free(src, kind, *blobs):
    """Free to go to. A price anywhere beats the source's word for it.

    `trust_free` is True for a source whose events are all free, or a pattern
    over the event's kind for one that mixes: the Food Bank's mobile pantries
    are free and its Eat For Good dinners, in the same feed, are not.
    """
    joined = " ".join(b for b in (kind, *blobs) if b)
    if re.search(r"(?i)\$\s?\d", joined):
        return False
    t = src.get("trust_free")
    if t is True or (isinstance(t, str) and re.search(t, kind or "")):
        return True
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
    # Before "doctor": the directory's own name for this need is "Crisis &
    # mental health", and a support group is not a visit to a doctor.
    (r"(?i)\b(mental health|suicide prevention|support group)\b", "crisis"),
    (r"(?i)\b(health (screening|clinic|fair|insurance)|medical clinic|free clinic|"
     r"vaccin|immuniz|dental|dentist|blood pressure|flu shot|"
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
            # A 400 past the last page is the normal end. On the first page it
            # is a refusal, and has to reach the report rather than read as a
            # quiet day: two feeds sat at zero that way.
            if page == 1:
                raise
            break
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
                "free": is_free(src, cats, blurb, e.get("cost")),
                "alt_url": e.get("website") or None,
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
            "free": is_free(src, cats, blurb, title),
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
            "free": is_free(src, "", blurb, title),
        })
    return out


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def from_curated(src, today, horizon):
    """Events found and opened by hand, from data/events_curated.json.

    For hosts with no feed — a walk, a parade, a race, a night market — so
    the featured row is not limited to the few nonprofits that happen to run
    one calendar plugin. Each row says the day a person opened its page in a
    browser (`checked`) and what that page showed. It stays until the event is
    over, unless its page goes away first: verify() drops a row whose link
    answers 404 or 410, so a cancelled event does not outlive its listing.
    """
    if not CURATED.exists():
        return []
    out = []
    for c in json.loads(CURATED.read_text("utf-8"))["events"]:
        out.append({
            "title": c["title"], "start": c["start"], "end": c.get("end") or c["start"],
            "all_day": bool(c.get("all_day")),
            "venue": c.get("venue", ""), "borough": c.get("borough", ""),
            "address": c.get("address", ""), "description": c.get("description", ""),
            "url": c["url"], "image": c.get("image"), "fit": c.get("fit"),
            "kind": c.get("kind") or c["org"], "format": c.get("format") or "In person",
            "free": bool(c.get("free")), "need": c.get("need") or "other",
            "source": c["org"], "source_key": slug(c["org"]), "source_url": c["site"],
            "checked": c["checked"],
        })
    return out


NYC = ZoneInfo("America/New_York")


def _ms(v):
    """Squarespace's epoch milliseconds, as a New York wall-clock time.

    Converted explicitly: GitHub's runners are on UTC, where a plain
    fromtimestamp() puts every 3pm tango class at 7pm.
    """
    if not v:
        return None
    return datetime.fromtimestamp(v / 1000, NYC).replace(tzinfo=None)


def from_squarespace(src, today, horizon):
    """A Squarespace events page; it answers ?format=json with its upcoming list."""
    d = json.loads(fetch(src["url"] + "?format=json"))
    origin = "/".join(src["url"].split("/")[:3])
    out = []
    for it in d.get("upcoming") or []:
        start = _ms(it.get("startDate"))
        if not start or not it.get("fullUrl"):
            continue
        loc = it.get("location") or {}
        place = text(loc.get("addressTitle"), 90)
        blurb = text(it.get("excerpt") or it.get("body"))
        title = text(it.get("title"), 120)
        img = it.get("assetUrl")
        out.append({
            "title": title,
            "start": iso(start),
            "end": iso(_ms(it.get("endDate")) or start),
            "all_day": False,
            "venue": place,
            "borough": borough(loc.get("addressLine2"), loc.get("addressLine1"), place),
            "address": text(loc.get("addressLine1"), 90),
            "description": blurb,
            "url": origin + it["fullUrl"],
            # The original upload can be a 6000px camera file; ask for less.
            "image": (img + "?format=1500w") if img and "?" not in img else img,
            "kind": src["name"],
            "format": fmt_of(place, blurb, title),
            "free": is_free(src, "", blurb, title),
        })
    return out


ADAPTERS = {"tribe": from_tribe, "parks-rss": from_parks_rss, "ics": from_ics,
            "curated": from_curated, "squarespace": from_squarespace}


# ------------------------------------------------- is the link a real page?

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Not events at all: Manhattan Community Board 1 puts its holiday closures on
# the same calendar as its meetings.
CANCELLED = re.compile(r"(?i)\b(cancell?ed|postponed)\b|^office closed\b")

# Real events that a reader of this page cannot go to. Historic Richmond
# Town's "Restoration Alumni Reunion" was its featured card for a night.
NOT_PUBLIC = re.compile(r"(?i)\b(alumni reunion|members?[- ]only|for members only|"
                        r"member mornings?|private event|invitation[- ]only|sold[- ]out)\b")


def page_words(url):
    """What a reader of url would read: no head, no script, no style.

    Raises on a redirect that leaves the host's own domain. A lapsed domain
    gets bought and pointed somewhere else: americasparade.org, which a search
    still gives for the Veterans Day Parade, lands on a gambling site today.
    """
    final = []
    s = fetch(url, final)
    if final and base(final[0]) != base(url):
        raise ValueError(f"{url} now lands on {final[0]}")
    s = re.sub(r"(?is)<(head|script|style|noscript|svg|template)\b.*?</\1>", " ", s)
    return SPACE.sub(" ", _html.unescape(TAGS.sub(" ", s))).lower()


def base(url):
    """nyrr.org for www.nyrr.org; give.foodbanknyc.org is still the Food Bank."""
    host = urllib.parse.urlsplit(url).hostname or ""
    return ".".join(host.split(".")[-2:])


def says_date(words, start):
    """Does the page name the day? Any page that is about an event does.

    The Food Bank's pantry pages answer 200 with a full site around them and
    nothing in the middle — no date, no place. A status code cannot tell that
    page from a real one; the date can.
    """
    d = parse_dt(start)
    m = MONTHS[d.month - 1].lower()
    forms = [f"{m} {d.day}", f"{m[:3]} {d.day}", f"{m[:3]}. {d.day}",
             f"{d.day} {m}", f"{d.month}/{d.day}", f"{d.month:02d}/{d.day:02d}",
             f"{d:%Y-%m-%d}"]
    return any(re.search(rf"(?<!\w){re.escape(f)}(st|nd|rd|th)?(?!\w)", words)
               for f in forms)


def verify(e):
    """Is the link a real page for this event?

    A feed's row has to show its own date. A hand-checked row was already
    opened in a browser — some hosts build the page in script, some turn a
    robot away — so it only has to still be there.
    """
    try:
        words = page_words(e["url"])
    except urllib.error.HTTPError as x:
        return bool(e.get("checked")) and x.code not in (404, 410)
    except ValueError:
        return False
    except Exception:                                # noqa: BLE001
        return bool(e.get("checked"))
    return bool(e.get("checked")) or says_date(words, e["start"])


def blank_pages(rows, n=3):
    """True when a feed's event pages do not show their events.

    Sampled: a feed's pages come out of one template, so three empty ones
    mean the template is empty. Opening every page every morning would be
    hundreds of requests to small nonprofits' servers.
    """
    seen = []
    for r in list({r["url"]: r for r in rows}.values())[:n]:
        try:
            seen.append(says_date(page_words(r["url"]), r["start"]))
        except Exception:                            # noqa: BLE001
            continue
    return bool(seen) and not any(seen)


def carried(key):
    """Yesterday's rows for a source that failed today.

    NYC Parks has answered GitHub's servers with 405 every morning since at
    least 27 Sep 2026, while answering a browser normally, and each failure
    deleted every park event from the site. A row still in the future is
    still true; it stays until the source answers again or the day passes.
    """
    try:
        old = json.loads(OUT.read_text("utf-8"))["events"]
    except (OSError, ValueError, KeyError):
        return []
    return [e for e in old if e.get("source_key") == key]


# ------------------------------------------------------------------ photos

def webp_size(path):
    b = Path(path).read_bytes()[:30]
    if b[12:16] == b"VP8X":
        return (1 + int.from_bytes(b[24:27], "little"),
                1 + int.from_bytes(b[27:30], "little"))
    if b[12:16] == b"VP8L":
        n = int.from_bytes(b[21:25], "little")
        return (n & 0x3FFF) + 1, ((n >> 14) & 0x3FFF) + 1
    return (int.from_bytes(b[26:28], "little") & 0x3FFF,
            int.from_bytes(b[28:30], "little") & 0x3FFF)


def photo(e, offline=False):
    """The host's own picture for this event, copied here.

    Shrunk to 640px wide (two pixels per pixel on the widest card) and
    re-encoded by cwebp. Named after the picture's address, so it is fetched
    once and every later run finds it on disk. When cwebp is missing or the
    host refuses, the card keeps its painted panel; nothing else changes.
    """
    src = e.get("image")
    if not src:
        return
    out = PHOTOS / (hashlib.sha1(src.encode()).hexdigest()[:16] + ".webp")
    if not out.exists():
        if offline or not shutil.which("cwebp"):
            return
        try:
            raw = fetch_bytes(src)
        except Exception:                            # noqa: BLE001
            return
        PHOTOS.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / "in"
            tmp.write_bytes(raw)
            # A busy photograph at q62 came within 30 KB of the 120 KB that
            # check.py allows a card, and one over it would stop the daily
            # job from committing anything. So: q62, then q40, then no photo.
            for q in ("62", "40"):
                # ponytail: -resize also enlarges a picture narrower than
                # 640px. Hosts' share images are 1200px and up; measure
                # before adding a width probe.
                r = subprocess.run(["cwebp", "-quiet", "-metadata", "none", "-q", q,
                                    "-resize", "640", "0", str(tmp), "-o", str(out)],
                                   capture_output=True)
                if r.returncode or not out.exists() or out.stat().st_size <= PHOTO_MAX:
                    break
        if (r.returncode or not out.exists() or out.stat().st_size < 2000
                or out.stat().st_size > PHOTO_MAX):
            out.unlink(missing_ok=True)
            return
    e["photo"] = out.as_posix()
    e["photo_w"], e["photo_h"] = webp_size(out)


def prune(events):
    """Delete pictures nothing uses any more, so assets/ does not only grow."""
    used = {Path(e["photo"]).name for e in events if e.get("photo")}
    for f in PHOTOS.glob("*.webp"):
        if f.name not in used:
            f.unlink()


# --------------------------------------------------------------------- driver

def collect(today, horizon):
    # New York's clock, not the machine's: the daily job runs on UTC, where
    # 5:20am in the city reads 9:20 and an 8am market would count as over.
    now = datetime.now(NYC).replace(tzinfo=None)
    got, report = [], []
    for src in SOURCES:
        try:
            rows = ADAPTERS[src["kind"]](src, today, horizon)
            err = ""
        except Exception as e:                       # noqa: BLE001
            # The hand-checked file is ours, not a server's: a typo in it is a
            # bug to stop on, not a bad day to ride out. Riding it out would
            # commit a site with every hand-checked event quietly gone.
            if src["kind"] == "curated":
                raise
            # One source having a bad day must not empty the page. The old
            # file stays on disk and yesterday's events are still better than
            # none — but the run says so, loudly, and --dry-run shows it.
            rows, err = carried(src["key"]), f"{type(e).__name__}: {e}"
        kept = []
        for r in rows:
            d = parse_dt(r["start"])
            if not d or d.date() < today or d.date() > horizon:
                continue
            # Over already. The morning run never sees this; a run in the
            # evening listed that day's 8am farmers market as coming up.
            if not r.get("all_day") and (parse_dt(r.get("end")) or d) < now:
                continue
            # NAMI-NYC keeps a cancelled group on its calendar and says so
            # only in the title.
            if not r["title"] or CANCELLED.search(r["title"]):
                continue
            # Listed, but not open to whoever reads this page.
            if NOT_PUBLIC.search(r["title"]) or NOT_PUBLIC.search(r.get("description") or ""):
                continue
            # A hand-checked row names its own host; a feed's rows are the feed's.
            if not r.get("venue") and src.get("place"):
                r["venue"], r["borough"] = src["place"]
            for rx, tpl in src.get("retitle", ()):
                if re.search(rx, r["kind"]) and ":" not in r["title"]:
                    r["title"] = tpl.format(title=r["title"])
                    break
            # A park's or a neighborhood's calendar lists other groups'
            # events (an NYRR run on NYC Parks', a health van on Prospect
            # Park's). The card says "Listed by" for those, not "Hosted by".
            if src.get("lists_others"):
                r["listed"] = True
            r.setdefault("source", src["name"])
            r.setdefault("source_key", src["key"])
            r.setdefault("source_url", src["site"])
            if src.get("keep_if") and not re.search(src["keep_if"], r["title"]):
                continue
            r["need"] = r.get("need") or (
                need_for(src, r["title"], r["kind"], r["description"])
                if src.get("file_by_words", True) else src["need"])
            kept.append(r)
        kept.sort(key=lambda r: r["start"])
        per_day, per_org, spread = {}, {}, []
        for r in kept:
            k = (r["source_key"], r["start"][:10])
            if per_day.get(k, 0) >= PER_SOURCE_DAY:
                continue
            if per_org.get(r["source_key"], 0) >= PER_SOURCE:
                continue
            per_day[k] = per_day.get(k, 0) + 1
            per_org[r["source_key"]] = per_org.get(r["source_key"], 0) + 1
            spread.append(r)
        kept = spread
        note = ""
        if src["kind"] == "tribe" and not err and blank_pages(kept):
            # The pages are empty, but the feed is not. A row with its own
            # event website goes there; a row with a place goes to the host's
            # page about that kind of event; a row with neither has nothing
            # to tell anyone and is dropped.
            keep = []
            for r in kept:
                if r.get("alt_url"):
                    r["url"] = r["alt_url"]
                elif src.get("fallback") and (r["venue"] or r["address"]):
                    r["url"] = src["fallback"]
                else:
                    continue
                keep.append(r)
            note = f"  (pages are empty: {len(keep)} relinked, {len(kept) - len(keep)} dropped)"
            kept = keep
        got += kept
        newest = max((r["start"][:10] for r in kept), default="—")
        report.append({"key": src["key"], "name": src["name"], "n": len(kept),
                       "newest": newest, "error": err, "note": note})
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


def cap(events, n=MAX_EVENTS):
    """The soonest n, keeping every hand-checked row: there are few, and each
    is a host with no feed that would otherwise vanish from the page."""
    keep = [e for e in events if e.get("checked")]
    rest = [e for e in events if not e.get("checked")][:max(0, n - len(keep))]
    return sorted(keep + rest, key=lambda e: (e["start"], e["title"]))


def pick(events, offline=False):
    """The featured row: one event per organization, each link checked.

    One per organization because the row is how a reader finds out who is out
    there, and six cards of the same legal van said one thing six times. Each
    host's best three are checked at once, and the best that passes gets the
    card, so a host with an empty page loses its card to its own next event,
    or to the next host, never to a dead link.
    """
    per, cands = {}, []
    org = lambda e: e["source"].lower()          # noqa: E731
    for e in sorted(events, key=rank):
        k = org(e)
        if per.get(k, 0) < 3:
            per[k] = per.get(k, 0) + 1
            cands.append(e)
    if offline:
        # No network, so no new checks: only what a run with the network
        # already passed, or a person opened. --offline once featured every
        # host unchecked, the Food Bank's empty pages included.
        good = [bool(e.get("verified") or e.get("checked")) for e in cands]
    else:
        with concurrent.futures.ThreadPoolExecutor(12) as ex:
            good = list(ex.map(verify, cands))
        for e, g in zip(cands, good):
            if g:
                e["verified"] = True
    out, orgs, gists = [], set(), []
    for e, g in zip(cands, good):
        if not g or org(e) in orgs:
            continue
        # Two hosts, one event: the Fortune Society lists its marathon team
        # as "The 2026 TCS New York City Marathon". The row names it once.
        day, gist = e["start"][:10], re.sub(r"\d+|\bthe\b|\W+", "", e["title"].lower())
        if any(d == day and (gist in o or o in gist) for d, o in gists):
            continue
        orgs.add(org(e))
        gists.append((day, gist))
        out.append(e)
    return out[:FEATURED]


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
        "lists_others": True,
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
    assert need_for(parks, "Mental Health First Aid", "Wellness", "") == "crisis"
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

    # --- a link has to show its event. The Food Bank's pantry pages answer
    # 200 and are empty; only the date tells them from a real page.
    assert says_date("october 15 @ 10:00 am - 3:00 pm", "2026-10-15T10:00:00")
    assert says_date("tuesday, october 13th 2026 vip", "2026-10-13T17:30:00")
    assert says_date("mobile pantry 10/13/2026", "2026-10-13T11:00:00")
    assert not says_date("october 15", "2026-10-01T10:00:00"), "Oct 1 is not Oct 15"
    assert not says_date("10/13", "2026-10-01T10:00:00")
    assert not says_date("donate now sign up for updates", "2026-10-13T11:00:00")
    assert base("https://give.foodbanknyc.org/e/1") == base("https://www.foodbanknyc.org/")
    assert base("https://njtanksweeps.com/") != base("https://americasparade.org/")

    # --- free: a price beats the source's word; a mixed feed trusts by kind
    fb = {"trust_free": r"(?i)pantry"}
    assert is_free(fb, "Mobile Pantry") and not is_free(fb, "Eat For Good")
    assert not is_free({"trust_free": True}, "Race", "Registration $35")
    assert CANCELLED.search("Living with Thoughts of Suicide CANCELLED")
    assert not CANCELLED.search("Cancellation policy")
    assert CANCELLED.search("Office Closed – Columbus Day")
    assert NOT_PUBLIC.search("Restoration Alumni Reunion")
    assert NOT_PUBLIC.search("Member Mornings: Iris van Herpen")
    assert not NOT_PUBLIC.search("Open to members of the public")
    assert re.search(MEETINGS, "CB6 Full Board Meeting")
    assert re.search(MEETINGS, "Human Services Committee Meeting")
    assert not re.search(MEETINGS, "Park Slope Food Coop: General Meeting")
    assert not re.search(MEETINGS, "BKBP ULURP Public Hearing")

    # --- the featured row: one card per organization
    def fe(i, k, d):
        return {"id": i, "source_key": k, "source": k.upper(), "start": d + "T10:00:00",
                "need": "other", "title": i}
    got = pick([fe("1", "a", "2026-10-12"), fe("2", "a", "2026-10-13"),
                fe("3", "b", "2026-10-14")], offline=True)
    assert got == [], "offline, nothing unchecked is featured"
    got = pick([dict(fe("1", "a", "2026-10-12"), verified=True), fe("2", "a", "2026-10-13"),
                dict(fe("3", "b", "2026-10-14"), checked="2026-10-10")], offline=True)
    assert [e["id"] for e in got] == ["1", "3"], got
    got = pick([dict(fe("TCS New York City Marathon", "a", "2026-11-01"), verified=True),
                dict(fe("The 2026 TCS New York City Marathon", "b", "2026-11-01"), verified=True)],
               offline=True)
    assert len(got) == 1, "one event listed by two hosts gets one card"

    # --- prune: a picture nothing uses is deleted, a used one is kept
    global PHOTOS
    real_photos = PHOTOS
    with tempfile.TemporaryDirectory() as d:
        PHOTOS = Path(d)
        (PHOTOS / "used.webp").write_bytes(b"x")
        (PHOTOS / "orphan.webp").write_bytes(b"x")
        prune([{"photo": f"{d}/used.webp"}, {"title": "no photo"}])
        assert sorted(f.name for f in PHOTOS.iterdir()) == ["used.webp"]
    PHOTOS = real_photos

    # --- Squarespace: epoch milliseconds to New York time, whatever the
    # machine's own zone is (GitHub's runners are on UTC)
    sq = json.dumps({"upcoming": [{"title": "Intro to Tango", "fullUrl": "/events/tango",
                                   "startDate": 1791745200000, "endDate": 1791752400000,
                                   "location": {"addressTitle": "Essex Market Mezzanine"},
                                   "assetUrl": "https://img.example/a.jpg"}]})
    real, fetch = fetch, lambda _u: sq
    try:
        rows = from_squarespace({"key": "s", "name": "S", "url": "https://x.example/events",
                                 "trust_free": False}, date(2026, 1, 1), date(2027, 1, 1))
    finally:
        fetch = real
    assert rows[0]["start"] == "2026-10-11T15:00:00", rows[0]["start"]
    assert rows[0]["url"] == "https://x.example/events/tango"
    assert rows[0]["image"].endswith("?format=1500w")
    # one card per organization even when a host has two keys
    got = pick([dict(fe("1", "a", "2026-10-12"), verified=True, source="Same Org"),
                dict(fe("2", "b", "2026-10-13"), verified=True, source="Same Org")], offline=True)
    assert len(got) == 1, "the same host under two keys still gets one card"

    # --- the page cap keeps the soonest, and every hand-checked row
    many = [{"start": f"2026-10-{d:02d}T10:00:00", "title": str(d)} for d in range(11, 31)]
    many.append({"start": "2026-12-31T10:00:00", "title": "late, by hand", "checked": "2026-10-10"})
    kept = cap(many, 5)
    assert [e["title"] for e in kept] == ["11", "12", "13", "14", "late, by hand"], kept

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

    today = datetime.now(NYC).date()
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
    events = cap(events)
    for e in events:                 # recomputed below, never carried over
        for k in ("photo", "photo_w", "photo_h") + (() if a.offline else ("verified",)):
            e.pop(k, None)
    for i, e in enumerate(events):
        e["id"] = f'{e["source_key"]}-{e["start"][:10]}-{i:04d}'

    picks = pick(events, a.offline)
    chosen = {id(e) for e in picks}
    for e in events:
        if id(e) in chosen or e.get("checked"):
            photo(e, offline=a.offline or a.dry_run)
    # By date, so the row reads as what is coming up. The wide first card is
    # the soonest with a picture that a person checked: it is the one with a
    # description written here, and its blurb is printed. A feed's own blurb
    # put "For tickets and more information, click here ." on the lead.
    picks.sort(key=lambda e: e["start"])
    lead = (next((e for e in picks if e.get("photo") and e.get("checked")), None)
            or next((e for e in picks if e.get("photo")), None))
    if lead:
        picks.remove(lead)
        picks.insert(0, lead)
    # Pictures before painted panels, each group by date: a phone shows only
    # the first four, and those are the cards that show the event is real.
    picks[1:] = sorted(picks[1:], key=lambda e: (not e.get("photo"), e["start"]))
    featured = [e["id"] for e in picks]

    sources = [{"key": s["key"], "name": s["name"], "site": s["site"],
                "note": s["note"]} for s in SOURCES if s["kind"] != "curated"]
    for e in events:
        if e.get("checked") and all(x["key"] != e["source_key"] for x in sources):
            sources.append({"key": e["source_key"], "name": e["source"],
                            "site": e["source_url"],
                            "note": "", "by_hand": True})

    doc = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "horizon": horizon.isoformat(),
        "sources": sources,
        "featured": featured,
        "events": events,
    }

    for r in report:
        flag = "  !! " + r["error"] if r["error"] else ""
        print(f'  {r["n"]:5d}  {r["name"]:38s} through {r["newest"]}{flag}{r["note"]}',
              file=sys.stderr)
    print(f"  {len(events):5d}  kept after dedupe; {len(featured)} featured, "
          f"{sum(1 for e in picks if e.get('photo'))} with a photo",
          file=sys.stderr)
    # The row is promised to draw on at least twenty organizations. Nothing
    # here can fail the job over it — a thin row is better than a stale site —
    # so it says so where somebody will see it: GitHub prints ::warning:: on
    # the run's summary page. Hand-checked rows expire, and when they run out
    # this is the line that asks for more.
    left = sorted({e["start"][:10] for e in events if e.get("checked")})
    print(f"  {len({e['source'] for e in picks}):5d}  organizations on the featured row; "
          f"hand-checked events run through {left[-1] if left else 'nothing'}",
          file=sys.stderr)
    if len({e["source"] for e in picks}) < 20:
        print(f"::warning::The featured row has only {len({e['source'] for e in picks})} "
              f"organizations. Add hand-checked events to data/events_curated.json.",
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
    if PHOTOS.exists():
        prune(events)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(f"  wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
