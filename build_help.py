#!/usr/bin/env python3
"""Render help.html from data/resources.csv.

Why a build step on a site with no build step: the audience for this page is
somebody on an old phone, on transit data, possibly with a screen reader, and
possibly with JavaScript blocked by a locked-down library terminal. Fetching a
JSON file and templating 114 rows in the browser fails all four of those. So
the rows are baked into the HTML here, once, and the browser's only job is to
hide the ones that do not match. The page works with JS off; it just shows
everything.

Run after editing data/resources.csv:  python3 build_help.py
"""

import csv
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CSV = ROOT / "data" / "resources.csv"
OUT = ROOT / "help.html"


# --------------------------------------------------------------- the needs
# Residents do not arrive looking for "Multi-Service / Navigation". They arrive
# with a sentence. These are those sentences, in the order somebody in trouble
# would scan them: the things that get people hurt first, then the rest.
#
# `cats` is the resource categories that land here. `also` is a second pass by
# subcategory keyword, because some resources genuinely answer two different
# sentences — a health-insurance helpline is both "seeing a doctor" and "this
# bill". A resource may appear under several needs; that is correct, and it is
# what stops somebody bouncing off the one heading we happened to file it under.
NEEDS = [
    {
        "key": "safety",
        "label": "I'm not safe where I live",
        "blurb": "Hurt or threatened by someone at home, or by a partner.",
        "icon": "shield",
        "cats": ["Domestic & Gender-Based Violence"],
    },
    {
        "key": "crisis",
        "label": "I'm in crisis, or I need someone to talk to",
        "blurb": "Feeling unsafe with yourself, overwhelmed, or struggling with drinking or drugs.",
        "icon": "heart",
        "cats": ["Mental Health & Substance Use"],
    },
    {
        "key": "food",
        "label": "I need food",
        "blurb": "Pantries, hot meals, and help signing up for SNAP.",
        "icon": "bowl",
        "cats": ["Food & Nutrition"],
    },
    {
        "key": "housing",
        "label": "I need somewhere to stay, or I might lose my home",
        "blurb": "Shelter tonight, eviction help, and affordable housing.",
        "icon": "roof",
        "cats": ["Housing & Shelter"],
    },
    {
        "key": "bills",
        "label": "I got a medical bill, or my insurance said no",
        "blurb": "The free experts who handle hospital bills, denials, and prescription costs.",
        "icon": "bill",
        "cats": [],
        "also": [
            "health insurance",
            "medicare help",
            "medication",
            "health access program",
            "free financial counseling",
        ],
    },
    {
        "key": "doctor",
        "label": "I need to see a doctor or a dentist",
        "blurb": "Clinics that see you whether or not you have insurance or papers.",
        "icon": "cross",
        "cats": ["Healthcare"],
    },
    {
        "key": "legal",
        "label": "I need a lawyer, or I have an immigration question",
        "blurb": "Free legal help — housing, immigration, benefits, and more.",
        "icon": "scale",
        "cats": ["Legal & Immigration"],
    },
    {
        "key": "money",
        "label": "I need help paying for things",
        "blurb": "Cash assistance, the heating bill, free tax filing, and benefits.",
        "icon": "wallet",
        "cats": ["Benefits & Financial Assistance"],
    },
    {
        "key": "family",
        "label": "I need help with my kids, or I'm a young person alone",
        "blurb": "Childcare, youth drop-in centres, and shelter for young people.",
        "icon": "family",
        "cats": ["Youth & Family"],
    },
    {
        "key": "senior",
        "label": "I'm an older adult, or I care for one",
        "blurb": "Meals, centres, and help for older New Yorkers.",
        "icon": "senior",
        "cats": ["Senior Services"],
    },
    {
        "key": "clothes",
        "label": "I need clothes, a coat, or baby supplies",
        "blurb": "Free clothing, winter coats, diapers, and children's gear.",
        "icon": "coat",
        "cats": ["Clothing & Supplies"],
    },
    {
        "key": "work",
        "label": "I need a job, or classes",
        "blurb": "Job training, paid work for young people, and English classes.",
        "icon": "work",
        "cats": ["Employment & Workforce"],
    },
    {
        "key": "getting-there",
        "label": "I need help getting there",
        "blurb": "Half-price transit, rides to medical appointments, and paratransit.",
        "icon": "bus",
        "cats": ["Transportation"],
    },
    {
        "key": "veterans",
        "label": "I served in the military",
        "blurb": "Health care and services for veterans.",
        "icon": "star",
        "cats": ["Veterans"],
    },
    {
        "key": "start",
        "label": "I'm not sure where to start",
        "blurb": "One call or one screen that points you to everything else.",
        "icon": "compass",
        "cats": ["Multi-Service / Navigation"],
    },
]

BOROUGHS = [
    ("bronx", "Bronx"),
    ("brooklyn", "Brooklyn"),
    ("manhattan", "Manhattan"),
    ("queens", "Queens"),
    ("staten-island", "Staten Island"),
]

# Languages worth their own filter row: the ones the directory actually carries
# in volume. Anything rarer is still searchable, it just does not get a chip.
LANG_CHIPS = [
    ("spanish", "Español"),
    ("chinese", "中文"),
    ("russian", "Русский"),
    ("haitian-creole", "Kreyòl"),
    ("bengali", "বাংলা"),
    ("korean", "한국어"),
    ("arabic", "العربية"),
]

LANG_MATCH = {
    "spanish": ["spanish", "español"],
    "chinese": ["chinese", "mandarin", "cantonese"],
    "russian": ["russian"],
    "haitian-creole": ["haitian", "creole", "kreyol"],
    "bengali": ["bengali", "bangla"],
    "korean": ["korean"],
    "arabic": ["arabic"],
}


# ------------------------------------------------------- words people use
# The directory is written in the vocabulary of the agencies that run these
# programmes. Nobody searches for "SNAP", "paratransit" or "ESOL"; they search
# for "food stamps", "access-a-ride" and "english classes". Left alone, a
# search for "food stamps" returned one row out of fourteen food programmes,
# and "dentist" returned one of two dental clinics.
#
# So each row's hidden search text is expanded at build time: if the row
# already contains a trigger on the left, the words on the right are appended
# to what it matches. Expanding documents rather than queries keeps the
# runtime a plain substring test, and keeps the whole table in one reviewable
# place. These are the words, not synonyms in the abstract — "kicked out" is
# in here because that is what somebody facing eviction types.
SYNONYMS = [
    ("snap",            "food stamps ebt"),
    ("pantry",          "free food groceries hungry"),
    ("soup kitchen",    "free meal hot meal hungry"),
    ("dental",          "dentist teeth tooth toothache"),
    ("fqhc",            "clinic doctor checkup primary care"),
    ("medication",      "medicine pills prescription pharmacy drug costs"),
    ("health insurance","obamacare aca marketplace coverage medicaid"),
    ("medicare",        "medicare part b senior insurance"),
    ("eviction",        "evicted landlord kicked out lose my apartment"),
    ("tenant",          "landlord rent apartment lease"),
    ("shelter",         "homeless nowhere to sleep sleep tonight bed"),
    ("housing",         "rent apartment place to live"),
    ("utility",         "con ed electric bill gas bill heat heating pay paying cant pay"),
    ("income support",  "welfare public assistance cash benefits pay paying rent money"),
    ("immigration",     "green card papers undocumented ice deportation asylum visa"),
    ("legal",           "lawyer attorney court sue rights"),
    ("domestic violence","abuse abusive hitting me partner unsafe at home"),
    ("crisis",          "suicide hopeless panic emergency help now"),
    ("substance",       "drugs alcohol addiction overdose drinking recovery"),
    ("mental health",   "depressed depression anxiety therapy counseling"),
    ("senior",          "elderly older adult grandmother grandfather"),
    ("paratransit",     "access-a-ride wheelchair disabled ride"),
    ("transit",         "fair fares metrocard subway bus fare"),
    ("early childhood", "daycare day care pre-k childcare babysitting"),
    ("youth",           "teen teenager kid young person"),
    ("job",             "work employment hiring career resume"),
    ("esol",            "english classes esl learn english"),
    ("veteran",         "army navy marines air force service member"),
    ("hiv",             "aids positive status testing"),
    ("diaper",          "baby supplies formula newborn"),
    ("coat",            "winter clothes jacket warm"),
    ("clothing",        "clothes shoes free clothes"),
    ("tax",             "taxes refund filing irs w2"),
    ("identification",  "id card birth certificate documents"),
]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def esc(s):
    return html.escape(s or "", quote=True)


def contact(phone):
    """(kind, label, href) for the one action button on a row.

    Three shapes appear in the data and they are not interchangeable:

      "917-720-9700"                    -> call it
      "800-621-4673 (800-621-HOPE)"     -> call the first, drop the mnemonic
      "988 then press 1 / text 838255"  -> call 988. Naively stripping
          non-digits across the whole cell yields +19881838255, which is a
          number that does not exist; this is the bug that makes a crisis line
          unreachable, so the cell is cut at the first separator FIRST and
          only then reduced to digits.
      "Text HOME to 741741"             -> a text shortcode. It cannot be
          dialled at all, so it must not render as a Call button.

    Anything with no reachable number returns ("none", "", ""), and the row
    falls back to its website.
    """
    if not phone:
        return ("none", "", "")

    # A text-only line: no dialable number, an sms: target instead.
    m = re.match(r"\s*text\s+(\S+)\s+to\s+([0-9\-]+)", phone, flags=re.I)
    if m:
        return ("text", phone.split(";")[0].strip(), "sms:" + re.sub(r"[^0-9]", "", m.group(2)))

    # Cut to the first alternative before touching the digits.
    first = re.split(r"[;/(]|\bthen\b|\bor\b", phone, flags=re.I)[0]
    digits = re.sub(r"[^0-9]", "", first)
    if not digits:
        return ("none", "", "")

    label = re.sub(r"\s*\(.*?\)", "", first).strip().rstrip(",")
    if len(digits) <= 4:            # 311, 911, 988
        href = digits
    elif len(digits) == 10:
        href = "+1" + digits
    elif len(digits) == 11 and digits.startswith("1"):
        href = "+" + digits
    else:
        return ("none", "", "")     # malformed rather than guess at a number
    return ("call", label, href)


def needs_for(row):
    """Every sentence this resource answers."""
    found = []
    cat = row["Category"]
    sub = (row["Subcategory"] or "").lower()
    name = (row["Resource Name"] or "").lower()
    for need in NEEDS:
        if cat in need.get("cats", []):
            found.append(need["key"])
            continue
        for kw in need.get("also", []):
            if kw in sub or kw in name:
                found.append(need["key"])
                break
    return found or ["start"]


def boroughs_for(row):
    """Borough tokens. Citywide and national resources match every borough.

    Getting this wrong in the generous direction shows somebody a resource
    that turns out to be in another borough. Getting it wrong in the strict
    direction hides a citywide hotline from them entirely, so when the cell is
    ambiguous, match everything.
    """
    cell = (row["Boroughs Served"] or "").lower()
    if "citywide" in cell or "national" in cell or "statewide" in cell:
        return [k for k, _ in BOROUGHS] + ["citywide"]
    hits = [k for k, label in BOROUGHS if label.lower() in cell]
    if "bronx" in cell and "bronx" not in hits:
        hits.append("bronx")
    return hits or [k for k, _ in BOROUGHS] + ["citywide"]


def langs_for(row):
    cell = (row["Languages"] or "").lower()
    hits = [key for key, words in LANG_MATCH.items() if any(w in cell for w in words)]
    # "175+ languages via interpreter" and friends: an interpreter line covers
    # every chip we offer, and it is the single most useful fact for somebody
    # who does not read English.
    if re.search(r"\d\d\+? languages|interpreter|all languages|language line", cell):
        hits = [k for k, _ in LANG_CHIPS]
    return hits


def flags_for(row):
    """The four facts that decide whether somebody dares to call."""
    f = []
    cost = (row["Cost"] or "").lower()
    hours = (row["Hours"] or "").lower()
    tags = (row["Tags"] or "").lower()
    access = (row["Access Type"] or "").lower()
    if cost.startswith("free"):
        f.append("free")
    if "24/7" in hours or "24-7" in tags or "24 hours" in hours:
        f.append("open-247")
    if row["Undocumented-Friendly"].strip().lower() == "yes":
        f.append("no-status")
    if "walk-in" in hours or "walk in" in (row["Notes"] or "").lower():
        f.append("walk-in")
    for token, key in [("phone", "phone"), ("online", "online"),
                       ("in-person", "in-person"), ("text", "text"), ("chat", "chat")]:
        if token in access:
            f.append(key)
    return f


# The emergency strip, curated by hand and not by rule.
#
# A heuristic over tags and hours got this wrong in exactly the way that
# matters: it put a hospital switchboard and two copies of 988 in front of
# somebody in danger. Four lines, each answering a different emergency, each
# free, each answered by a person at any hour. The wording beside each number
# is written for the person reading it, not lifted from the directory's
# internal subcategory. Changing this list is a safety decision.
SOS = [
    ("NYC 988 (formerly NYC Well)",
     "You feel unsafe with yourself, or you need to talk to somebody now"),
    ("NYC HOPE — 24-Hour DV Hotline (Safe Horizon)",
     "Someone at home or a partner is hurting you or frightening you"),
    ("NYC 311",
     "Anything else at all. Free, any hour, in your language"),
]


def urgent(row):
    """True for the hand-picked emergency lines above."""
    return row["Resource Name"] in [name for name, _ in SOS]


def load():
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        row = {k: (v or "").strip() for k, v in row.items()}
        if not row.get("Resource Name"):
            continue
        row["_needs"] = needs_for(row)
        row["_boroughs"] = boroughs_for(row)
        row["_langs"] = langs_for(row)
        row["_flags"] = flags_for(row)
        row["_urgent"] = urgent(row)
        row["_id"] = slug(row["Resource Name"])
        out.append(row)
    return out


def haystack(r):
    """What the search box matches against.

    Only the vocabulary that is NOT already visible in the row: the internal
    tags and category, plus every plain-English phrase SYNONYMS attaches to
    this row. help.js unions this with the row's own textContent, so repeating
    the description here would just ship it twice.
    """
    # What a synonym is allowed to fire on: the fields that say what this
    # resource IS. Description and Notes are deliberately excluded — most rows
    # carry a note like "does not ask about immigration status", and letting
    # that fire the immigration trigger attached "green card" to 29 unrelated
    # rows, so a search for "green card" returned a food pantry and a DV
    # hotline before it reached a single immigration lawyer.
    base = " ".join([
        r["Resource Name"], r["Subcategory"], r["Tags"], r["Category"],
    ]).lower()
    extra = [r["Tags"].replace(";", " "), r["Category"]]
    for trigger, words in SYNONYMS:
        if trigger in base:
            extra.append(words)
    return " ".join(extra).lower()


# --------------------------------------------------------------- rendering
# Every icon is one path on a 24-box, drawn in currentColor. Inline because a
# sprite sheet is one more request on the page most likely to be opened on a
# bad connection, and because these need to survive the page being printed.
ICONS = {
    "shield": "M12 3 4 6v6c0 5 3.4 8.4 8 9 4.6-.6 8-4 8-9V6l-8-3Z",
    "heart": "M12 20s-7-4.5-7-9.5A4 4 0 0 1 12 8a4 4 0 0 1 7 2.5C19 15.5 12 20 12 20Z",
    "bowl": "M4 11h16a8 8 0 0 1-16 0ZM9 7c0-1 1-1.5 1-2.5M13 7c0-1 1-1.5 1-2.5M3 20h18",
    "roof": "M3 11 12 4l9 7M6 10v9h12v-9M10 19v-5h4v5",
    "bill": "M6 3h12v18l-3-2-3 2-3-2-3 2V3ZM9 8h6M9 12h6M9 16h3",
    "cross": "M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7V3Z",
    "scale": "M12 4v16M6 20h12M12 6 5 10h8L6 10M12 6l7 4h-8l7 0M3 10a3 3 0 0 0 6 0M15 10a3 3 0 0 0 6 0",
    "wallet": "M3 7h15a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Zm0 0 12-3v3M16 13h2",
    "family": "M8 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm8 1a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM4 20v-4a4 4 0 0 1 8 0v4M14 20v-3a3 3 0 0 1 6 0v3",
    "senior": "M12 7a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm-2 3h4l1 5-2 1v6M10 10 8 15l2 1v6M17 12v10",
    "coat": "M12 3 7 5v16h10V5l-5-2Zm0 0v18M7 9l-3 2v7M17 9l3 2v7",
    "work": "M3 8h18v12H3V8Zm6 0V5h6v3M3 13h18",
    "bus": "M5 4h14v11H5V4Zm0 11 1 4h2l1-4m6 0 1 4h2l1-4M5 9h14M8 12h.01M16 12h.01",
    "star": "m12 3 2.6 5.6 6 .8-4.4 4.2 1.1 6.1L12 16.8 6.7 19.7l1.1-6.1L3.4 9.4l6-.8L12 3Z",
    "compass": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3.5-12.5-2 5-5 2 2-5 5-2Z",
}


def icon(name):
    d = ICONS.get(name, ICONS["compass"])
    return (f'<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" '
            f'fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="{d}"/></svg>')


# The four badges worth putting on the row itself. Everything else lives one
# tap down in the details, because a row that says eight things says nothing.
BADGES = [
    ("free", "Free"),
    ("open-247", "Open 24/7"),
    ("no-status", "No immigration status asked"),
]


def render_row(r, need_key):
    """One resource. The two things somebody needs are the name and the number,
    so those are the two things that are big; the rest is one tap down.

    A resource filed under two needs is rendered twice, so the id has to carry
    the group: duplicate ids would break every anchor on the page and make a
    screen reader announce two different rows by the same name. `data-key` is
    the shared identity, which is how the counter below says "43 places" and
    not "45" when both copies of two resources are showing.
    """
    a = []
    a.append(f'<li class="r" id="r-{esc(need_key)}-{esc(r["_id"])}"'
             f' data-key="{esc(r["_id"])}"'
             f' data-needs="{esc(" ".join(r["_needs"]))}"'
             f' data-boro="{esc(" ".join(r["_boroughs"]))}"'
             f' data-lang="{esc(" ".join(r["_langs"]))}"'
             f' data-flags="{esc(" ".join(r["_flags"]))}"'
             f' data-find="{esc(haystack(r))}">')
    a.append('<div class="r__head">')
    a.append(f'<h3 class="r__name">{esc(r["Resource Name"])}</h3>')
    if r["Subcategory"]:
        a.append(f'<p class="r__kind">{esc(r["Subcategory"])}</p>')
    a.append("</div>")
    a.append(f'<p class="r__what">{esc(r["Description"])}</p>')

    badges = [f'<span class="bdg bdg--{k}">{v}</span>'
              for k, v in BADGES if k in r["_flags"]]
    if badges:
        a.append('<p class="r__badges">' + "".join(badges) + "</p>")

    # actions
    a.append('<div class="r__do">')
    kind, label, href = contact(r["Phone"])
    if kind == "call":
        a.append(f'<a class="call" href="tel:{esc(href)}">'
                 f'<svg class="ico" aria-hidden="true"><use href="#i-phone"/></svg>'
                 f'<span><small>Call</small>{esc(label)}</span></a>')
    elif kind == "text":
        a.append(f'<a class="call call--text" href="{esc(href)}">'
                 f'<svg class="ico" aria-hidden="true"><use href="#i-text"/></svg>'
                 f'<span><small>Text</small>{esc(label)}</span></a>')
    if r["Website"]:
        a.append(f'<a class="visit" href="{esc(r["Website"])}" rel="noopener">'
                 f'Open website<span class="arr" aria-hidden="true">&#8599;</span></a>')
    a.append("</div>")

    # details
    facts = [
        ("Phone", r["Phone"]),
        ("Who it is for", r["Who Can Access"]),
        ("Cost", r["Cost"]),
        ("Hours", r["Hours"]),
        ("Languages", r["Languages"]),
        ("Where", r["Address / Location"]),
        ("Boroughs", r["Boroughs Served"]),
        ("How to reach them", r["Access Type"]),
    ]
    facts = [(k, v) for k, v in facts if v and v.lower() not in ("n/a", "-")]
    a.append('<details class="r__more"><summary><span>More about this</span></summary>'
             '<div class="r__facts"><dl>')
    for k, v in facts:
        a.append(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>")
    a.append("</dl>")
    if r["Notes"]:
        a.append(f'<p class="r__note">{esc(r["Notes"])}</p>')
    if r["Last Verified"]:
        a.append(f'<p class="r__ver">We checked this on {esc(r["Last Verified"])}.</p>')
    a.append("</div></details>")
    a.append("</li>")
    return "\n".join(a)


HONESTY = (
    "We are trained student volunteers. We help you find the free programs and "
    "professionals in New York that handle medical bills and insurance denials. "
    "We are not doctors, lawyers, benefits counselors, or insurance experts. We "
    "do not read your bills, fill out your forms, or tell you what you qualify "
    "for. We connect you to people who do that, and they do it for free. We "
    "never charge for anything."
)


def render(rows):
    n = len(rows)
    by_need = {need["key"]: [r for r in rows if need["key"] in r["_needs"]]
               for need in NEEDS}
    p = []
    A = p.append
    A('<!DOCTYPE html>')
    A('<html lang="en">')
    A('<head>')
    A('<meta charset="UTF-8" />')
    A('<meta name="viewport" content="width=device-width, initial-scale=1.0" />')
    A('<title>Find free help in New York City — Waypoint</title>')
    A('<meta name="description" content="A plain-language directory of free and '
      'low-cost help in New York City: food, medical bills, housing, health care, '
      'legal help, and more. Most of these do not ask about immigration status." />')
    A('<meta name="theme-color" content="#13231A" />')
    A('<meta property="og:title" content="Find free help in New York City — Waypoint" />')
    A('<meta property="og:description" content="Food, medical bills, housing, a '
      'doctor, a lawyer. Free help that already exists in New York, in one place." />')
    A('<meta property="og:type" content="website" />')
    A('<link rel="preconnect" href="https://fonts.googleapis.com" />')
    A('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />')
    A('<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />')
    A('<link rel="stylesheet" href="help.css" />')
    A('</head>')
    A('<body class="help">')
    A('<a class="skip" href="#needs">Skip to the list of help</a>')
    # one copy of the phone glyph, referenced by every Call button below
    A('<svg class="sprite" aria-hidden="true"><symbol id="i-phone" viewBox="0 0 24 24" '
      'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
      'stroke-linejoin="round"><path d="M6 3h3l2 5-2.5 1.5a12 12 0 0 0 6 6L16 13l5 2v3a2 '
      '2 0 0 1-2.2 2A17 17 0 0 1 4 5.2 2 2 0 0 1 6 3Z"/></symbol>'
      '<symbol id="i-text" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      '<path d="M21 12a8 8 0 0 1-8 8H4l2.2-2.6A8 8 0 1 1 21 12Z"/></symbol></svg>')

    # ---- header
    A('<header class="hhead">')
    A('  <div class="hhead__in">')
    A('    <a class="brand" href="index.html" aria-label="Waypoint home">')
    A('      <svg viewBox="0 0 32 32" aria-hidden="true"><path class="pin" d="M16 2 C9 2 5 7 5 13 c0 7 8 15 11 17 3-2 11-10 11-17 0-6-4-11-11-11Z"/><circle class="pin-dot" cx="16" cy="13" r="4.2"/></svg>')
    A('      <span class="brand__txt">Waypoint<small>Free help, New York City</small></span>')
    A('    </a>')
    A('    <nav class="hhead__links" aria-label="Primary">')
    A('      <a href="help.html" aria-current="page">Find help</a>')
    A('      <a href="index.html#students">Students</a>')
    A('      <a href="index.html#partners">Partners</a>')
    A('    </nav>')
    A('  </div>')
    A('</header>')

    A('<main class="wrap">')

    # ---- title
    A('<div class="lede">')
    A('  <h1>Find free help in New York City</h1>')
    A(f'  <p class="lede__say">This is a list of <b>{n} places</b> that help New '
      'Yorkers with food, medical bills, housing, health care, legal problems and '
      'more. Nearly all of them are free. Most do not ask about immigration status.</p>')
    A('  <p class="lede__say lede__say--2">You do not need an account. You do not '
      'need to tell us anything. Pick what you need below, and call them yourself.</p>')
    A('</div>')

    # ---- emergency
    A('<section class="sos" aria-labelledby="sos-h">')
    A('  <h2 id="sos-h" class="sos__h">If you need help right now</h2>')
    A('  <ul class="sos__list">')
    A('    <li><a href="tel:911"><span class="sos__num">911</span>'
      '<span class="sos__for">You are in danger, or someone is badly hurt</span></a></li>')
    by_name = {r["Resource Name"]: r for r in rows}
    for name, why in SOS:
        r = by_name.get(name)
        if not r:
            raise SystemExit(f"emergency strip: {name!r} is not in the directory")
        kind, label, href = contact(r["Phone"])
        if kind != "call":
            raise SystemExit(f"emergency strip: {name!r} has no dialable number")
        A(f'    <li><a href="tel:{esc(href)}"><span class="sos__num">'
          f'{esc(label)}</span><span class="sos__for">{esc(why)}</span></a></li>')
    A('  </ul>')
    A('  <p class="sos__note">These lines are free, and they are answered by people '
      'trained for exactly this. You can call them without giving your name.</p>')
    A('</section>')

    # ---- search + filters
    A('<section class="find" aria-labelledby="find-h">')
    A('  <h2 id="find-h" class="sr-only">Search and narrow the list</h2>')
    A('  <div class="find__search">')
    A('    <label for="q">Search for what you need</label>')
    A('    <div class="find__box">')
    A('      <svg class="ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>')
    A('      <input id="q" type="search" autocomplete="off" '
      'placeholder="Try: food, rent, dentist, lawyer" />')
    A('      <button type="button" class="find__clear" hidden>Clear</button>')
    A('    </div>')
    A('  </div>')

    A('  <div class="find__filters" hidden>')
    A('    <fieldset class="fset"><legend>Where you are</legend><div class="chips">')
    for key, label in BOROUGHS:
        A(f'      <button type="button" class="chip" data-f="boro" data-v="{key}" aria-pressed="false">{label}</button>')
    A('    </div></fieldset>')
    A('    <fieldset class="fset"><legend>Language you speak</legend><div class="chips">')
    for key, label in LANG_CHIPS:
        A(f'      <button type="button" class="chip" data-f="lang" data-v="{key}" aria-pressed="false" lang="{key.split("-")[0]}">{label}</button>')
    A('    </div></fieldset>')
    A('    <fieldset class="fset"><legend>Only show</legend><div class="chips">')
    for key, label in [("free", "Free"), ("open-247", "Open 24/7"),
                       ("no-status", "Does not ask immigration status"),
                       ("phone", "You can call")]:
        A(f'      <button type="button" class="chip" data-f="flags" data-v="{key}" aria-pressed="false">{label}</button>')
    A('    </div></fieldset>')
    A('    <button type="button" class="reset" hidden>Start over</button>')
    A('  </div>')
    A('  <p class="find__count" role="status" aria-live="polite"></p>')
    A('</section>')

    # ---- the needs index
    A('<nav class="needs" id="needs" aria-labelledby="needs-h">')
    A('  <h2 id="needs-h">What do you need help with?</h2>')
    A('  <ul class="needs__grid">')
    for need in NEEDS:
        c = len(by_need[need["key"]])
        A(f'    <li><a class="need" href="#n-{need["key"]}" data-need="{need["key"]}">')
        A(f'      {icon(need["icon"])}')
        A(f'      <span class="need__t">{esc(need["label"])}</span>')
        A(f'      <span class="need__b">{esc(need["blurb"])}</span>')
        A(f'      <span class="need__n">{c} place{"s" if c != 1 else ""}</span>')
        A('    </a></li>')
    A('  </ul>')
    A('</nav>')

    # ---- the directory
    A('<div class="dir" id="dir">')
    A('<p class="dir__none" hidden>Nothing here matched that. Try a different word, '
      'or <button type="button" class="linkish reset">show everything again</button>. '
      'If you cannot find it, call <a href="tel:311">311</a> &mdash; they will point '
      'you somewhere, in your language, at any hour.</p>')
    for need in NEEDS:
        group = by_need[need["key"]]
        A(f'<section class="grp" id="n-{need["key"]}" data-need="{need["key"]}" '
          f'aria-labelledby="h-{need["key"]}">')
        A('  <div class="grp__head">')
        A(f'    {icon(need["icon"])}')
        A('    <div>')
        A(f'      <h2 id="h-{need["key"]}">{esc(need["label"])}</h2>')
        A(f'      <p>{esc(need["blurb"])}</p>')
        A('    </div>')
        A(f'    <a class="grp__top" href="#needs">Back to the list</a>')
        A('  </div>')
        A('  <ul class="rows">')
        for r in group:
            A(render_row(r, need["key"]))
        A('  </ul>')
        A("</section>")
    A("</div>")

    # ---- honesty
    A('<section class="vowbox" aria-labelledby="vow-h">')
    A('  <h2 id="vow-h">Who we are, and what we will never do</h2>')
    A(f'  <p class="vowbox__full">{HONESTY}</p>')
    A('  <p class="vowbox__src">This is printed on everything we hand out, and said '
      'out loud at every table.</p>')
    A('</section>')

    A('</main>')

    # ---- footer
    A('<footer class="hfoot">')
    A('  <div class="hfoot__in">')
    A('    <p class="hfoot__say">Waypoint is a student volunteer corps in New York '
      'City. We do not run any of the programs on this page. We help people find '
      'them.</p>')
    A('    <ul class="hfoot__links">')
    A('      <li><a href="index.html">About Waypoint</a></li>')
    A('      <li><a href="index.html#students">Volunteer with us</a></li>')
    A('      <li><a href="index.html#partners">For organisations</a></li>')
    A('      <li><a href="privacy.html">Privacy &amp; legal</a></li>')
    A('      <li><a href="mailto:waypointoutreach@gmail.com">waypointoutreach@gmail.com</a></li>')
    A('    </ul>')
    A(f'    <p class="hfoot__ver">{n} resources. Last checked June 2026. '
      'Programs change &mdash; if something here is wrong, please tell us.</p>')
    A('  </div>')
    A('</footer>')
    A('<script src="help.js" defer></script>')
    A('</body>')
    A('</html>')
    return "\n".join(p) + "\n"

def selfcheck():
    """The phone parser, which is the one place here where being wrong hurts
    somebody: a number that does not dial on a crisis line is worse than no
    button at all. Run by every build."""
    cases = [
        # cell                                    kind     label            href
        ("917-720-9700",                          "call", "917-720-9700",  "+19177209700"),
        ("800-621-4673 (800-621-HOPE); TTY 866-604-5350",
                                                  "call", "800-621-4673",  "+18006214673"),
        ("311 (or 212-639-9675)",                 "call", "311",           "311"),
        # the one that mattered: naive digit-stripping gave +19881838255
        ("988 then press 1 / text 838255",        "call", "988",           "988"),
        ("Text HOME to 741741",                   "text", "Text HOME to 741741", "sms:741741"),
        ("800-786-2929 (1-800-RUNAWAY)",          "call", "800-786-2929",  "+18007862929"),
        ("1-800-273-8255",                        "call", "1-800-273-8255","+18002738255"),
        ("",                                      "none", "",              ""),
        ("see website",                           "none", "",              ""),
    ]
    for cell, kind, label, href in cases:
        got = contact(cell)
        assert got == (kind, label, href), f"contact({cell!r}) -> {got}, wanted {(kind, label, href)}"

    # every dialable href is either a short code or a full +1 number: anything
    # in between is a number that will not connect.
    for r in load():
        kind, label, href = contact(r["Phone"])
        if kind == "call":
            assert re.fullmatch(r"\+1[0-9]{10}|[0-9]{3}", href), \
                f"{r['Resource Name']}: unusable tel: {href!r} from {r['Phone']!r}"
    print("selfcheck ok")


if __name__ == "__main__":
    selfcheck()
    rows = load()
    print(f"{len(rows)} resources")
    from collections import Counter
    c = Counter(n for r in rows for n in r["_needs"])
    for need in NEEDS:
        print(f'  {c[need["key"]]:3}  {need["label"]}')
    print(f'  urgent: {sum(1 for r in rows if r["_urgent"])}')
    missing = [r["Resource Name"] for r in rows
               if contact(r["Phone"])[0] == "none" and not r["Website"]]
    unparsed = [(r["Resource Name"], r["Phone"]) for r in rows
                if r["Phone"] and contact(r["Phone"])[0] == "none"]
    if unparsed:
        print("PHONE NOT PARSED:", unparsed, file=sys.stderr)
    if missing:
        print("NO WAY TO REACH:", missing, file=sys.stderr)
    OUT.write_text(render(rows), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.name}  {kb:.0f} KB")
