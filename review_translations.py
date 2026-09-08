#!/usr/bin/env python3
"""One language, printed the way a reviewer needs to read it.

    python3 review_translations.py                 # list the ten
    python3 review_translations.py spanish         # to the terminal
    python3 review_translations.py spanish -o es.txt

The translations live in three dicts in i18n.py and one in build_help.py, in
the order the *code* wants them, which is not the order a reader meets them.
Handing a native speaker `i18n.py` asks them to hold that mapping in their
head while also reading for calques. This prints their language in page order
— masthead, emergency panel, the seventeen kinds of help, the promise, the
footer — with the English source beside every string, and the register and
gender rules at the top so they are being reviewed against on purpose.

No dependencies. It reads the same data the build reads, so it cannot drift
from what ships.
"""

import sys
import textwrap

sys.path.insert(0, ".")
import build_help as B          # noqa: E402
import i18n                     # noqa: E402

LANGS = {L["key"]: L for L in B.LANGUAGES}
NEEDS = {n["key"]: n for n in B.NEEDS}
ORDER = [n["key"] for n in B.NEEDS]

# What each language's reviewer has to hold in mind while reading. Kept here
# rather than in TRANSLATIONS.md as well, because the person reading this
# printout may never open the repo.
RULES = {
    "spanish": "Addressed as usted throughout. Leísmo de cortesía (le atienden) "
               "is deliberate and consistent — do not change it in one place.",
    "french":  "Addressed as vous. A narrow no-break space (U+202F) before ? ! ; "
               "and a no-break space (U+00A0) before : — plain spaces are a bug.",
    "polish":  "Impersonal (potrzebujesz), never Pan/Pani. No ending may agree "
               "with the reader's gender.",
    "haitian-creole": "Standard (IPN) orthography, not French spellings.",
    "russian": "Addressed as вы. No ending may agree with the reader's gender.",
    "chinese": "Simplified, 您 not 你. Full-width ，。？！ only.",
    "korean":  "Formal -습니다/-십시오. 어르신 is an honorific for other people, "
               "never for oneself.",
    "bengali": "Sentences end on ।, never a full stop. তরুণ/তরুণী is a gendered "
               "pair — the reader's own line must not pick one.",
    "arabic":  "Comma ، semicolon ؛ question mark ؟ — never the Latin ones. No "
               "ending may agree with the reader's gender.",
    "urdu":    "آپ, never تم. Comma ، and full stop ۔ — never the Latin ones.",
}

# The nouns checked against ACCESS NYC, which publishes the same programs in
# the same ten languages. check_the_words_the_city_prints enforces these.
CITY_WORDS = {
    "spanish": "refugio (not alojamiento) · asistencia en efectivo · cuidado infantil",
    "russian": "Денежное пособие (not Денежная помощь) · ночлег, deliberately not приют",
    "korean":  "현금 지원 · 쉼터, deliberately not the city's 대피소",
    "haitian-creole": "avantaj (not benefis) · Èd an lajan kach",
    "urdu":    "مراعات (not فوائد) · نقد امداد · پناہ گاہ",
    "arabic":  "المزايا (not المساعدات) · مساعدة نقدية · مأوى",
    "bengali": "নগদ সহায়তা · আশ্রয়",
    "polish":  "świadczenia · pomoc pieniężna",
    "french":  "prestations · aide en espèces",
    "chinese": "现金补助 · 福利 · 残疾 (one word, not also 残障)",
}

KEPT_IN_ENGLISH = ("SNAP", "Medicaid", "MetroCard", "Access-A-Ride",
                   "Fair Fares NYC", "Homebase", "Waypoint")

# UI keys, in the order the reader meets them on the page.
UI_ORDER = [
    ("skip",      "the skip link, first thing a screen reader reaches"),
    ("home",      "the wordmark's link label"),
    ("nav_label", "the nav landmark's name"),
    ("nav",       "the five header tabs, in the header's order"),
    ("eyebrow",   "the small line above the masthead title"),
    ("title_a",   "the masthead title, roman half"),
    ("title_b",   "…and the emphasised half (gold)"),
    ("lede1",     "first masthead paragraph — {n} is the resource count"),
    ("lede2",     "second masthead paragraph"),
    ("sos_h",     "heading of the emergency panel"),
    ("sos",       "the four numbers' 'this is for' lines, in panel order: "
                  "911, the domestic-violence line, 988, 311"),
    ("sos_note",  "the line under the four numbers"),
    ("langbar_h", "heading over the language chips"),
    ("here",      "marks the language you are already reading"),
    ("english_h", "heading of the English-pages note"),
    ("english",   "what is and is not in this language"),
    ("jump_h",    "the jump row above the seventeen cards"),
    ("needs_h",   "heading over the seventeen cards"),
    ("needs_sub", "the line under it"),
    ("open_all",  "the link at the foot of a card — {n} is that need's count"),
    ("vow_h",     "heading of the honesty statement"),
    ("vow",       "THE HONESTY STATEMENT. A promise, translated whole and "
                  "never summarised. It is what stops a frightened person "
                  "mistaking a student for a professional."),
    ("vow_src",   "the line under it"),
    ("foot_say",  "what Waypoint is"),
    ("foot_links", "five footer links, in the footer's order"),
    ("foot_ver",  "{n} resources, {when} the checked span"),
]


def wrap(s, indent):
    return textwrap.fill(str(s), 96, initial_indent=indent,
                         subsequent_indent=indent + "  ")


def report(key, out):
    L, U = LANGS[key], i18n.UI[key]
    w = lambda *a: print(*a, file=out)

    w("=" * 96)
    w(f"  {L['endonym']}  ({L['name_en']}, {L['tag']}, {L['dir']})")
    w("=" * 96)
    w("")
    w(wrap("REGISTER — " + RULES[key], "  "))
    w("")
    w(wrap("THE CITY'S WORDS — " + CITY_WORDS[key], "  "))
    w("")
    w(wrap("NOT TRANSLATED, on purpose — these are what somebody has to say on "
           "the phone and type into a search box: " + ", ".join(KEPT_IN_ENGLISH),
           "  "))
    w("")
    w(wrap("Resource names, addresses and phone numbers are not translated "
           "either. Their English descriptions stay in English rather than be "
           "guessed at, which is what the 'english' string below exists to say.",
           "  "))
    w("")

    w("-" * 96)
    w("  THE PAGE'S OWN WORDS")
    w("-" * 96)
    for k, why in UI_ORDER:
        v = U[k]
        w("")
        w(f"  [{k}]  {why}")
        if isinstance(v, list):
            for i, x in enumerate(v):
                w(wrap(f"{i}. {x}", "      "))
        else:
            w(wrap(v, "      "))

    w("")
    w("-" * 96)
    w("  THE SEVENTEEN KINDS OF HELP")
    w("  Each is the reader speaking, in the first person, and must not agree")
    w("  with a gender. Under it: the line that says what is behind it, and")
    w("  the short label used in the jump row.")
    w("-" * 96)
    for k in ORDER:
        w("")
        w(f"  {k}")
        w(wrap(f"EN heading   {NEEDS[k]['label']}", "      "))
        w(wrap(f"   heading   {L['needs'][k]}", "      "))
        w(wrap(f"EN blurb     {NEEDS[k]['blurb']}", "      "))
        w(wrap(f"   blurb     {i18n.BLURBS[key][k]}", "      "))
        w(wrap(f"EN chip      {NEEDS[k]['short']}", "      "))
        w(wrap(f"   chip      {i18n.SHORT[key][k]}", "      "))

    w("")
    w("-" * 96)
    w("  DATES")
    w("-" * 96)
    one, span = i18n.DATE_SPAN[key]
    months = i18n.MONTHS[key]
    w(wrap("months  " + ", ".join(months), "      "))
    w(wrap(f"one     {one.format(a=months[5], b=months[7], y=2026)}", "      "))
    w(wrap(f"span    {span.format(a=months[5], b=months[7], y=2026)}", "      "))
    w("")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dest = None
    if "-o" in sys.argv:
        dest = sys.argv[sys.argv.index("-o") + 1]
        args = [a for a in args if a != dest]

    if not args:
        print(__doc__.strip().split("\n\n")[0])
        print("\nThe ten:\n")
        for L in B.LANGUAGES:
            print(f"  {L['key']:16} {L['endonym']}")
        print("\n  all              every one of them, in one file")
        return 0

    keys = list(LANGS) if args[0] == "all" else args
    unknown = [k for k in keys if k not in LANGS]
    if unknown:
        print(f"not a language on this site: {', '.join(unknown)}", file=sys.stderr)
        return 2

    out = open(dest, "w", encoding="utf-8") if dest else sys.stdout
    try:
        for k in keys:
            report(k, out)
    finally:
        if dest:
            out.close()
            print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
