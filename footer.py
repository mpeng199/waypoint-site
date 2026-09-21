"""The site footer, defined once.

Every page on waypointnyc.org ends with the same footer. This module is the
only place it exists: the markup, the link list, and the English words. The
ten translated pages take their shape from here and their words from i18n.py.

To change the footer, change it here and then run, from the repo root:

    python3 footer.py       # rewrites the five hand-written pages
    python3 build_help.py   # regenerates help.html and the 27 topic/language pages
    python3 build_min.py    # refreshes the .min.css / .min.js

check.py compares every page's footer against what this module renders and
fails on any difference, so a footer changed on one page and not the rest
cannot reach the site.

The CSS lives in tokens.css (not styles.css, not help.css) for the same
reason: tokens.css is the sheet every page already loads.
"""

import html
import re
from pathlib import Path


def esc(t):
    """Escape for a text node. quote=False: these never land in an attribute,
    and &#x27; for every apostrophe in the French and Haitian labels would be
    noise in the diff of a file people read."""
    return html.escape(t, quote=False)

ROOT = Path(__file__).resolve().parent

PIN = ('<svg viewBox="0 0 32 32" aria-hidden="true"><path class="pin" d="M16 2 C9 2 5 7 5 13 '
       'c0 7 8 15 11 17 3-2 11-10 11-17 0-6-4-11-11-11Z"/>'
       '<circle class="pin-dot" cx="16" cy="13" r="4.2"/></svg>')

EMAIL = "waypointoutreach@gmail.com"
# the wbr lets a 320px column break the address instead of overflowing it
EMAIL_SHOWN = 'waypointoutreach@<wbr />gmail.com'

# The English words. A translated page passes its own dict with the same keys;
# words_for() below builds it from i18n.py. Keep the list lengths in step: render()
# zips them against the hrefs below and a short list would silently drop a link.
EN = {
    "vow": "We are trained student volunteers. We help you find the free programs "
           "and professionals in New York that handle medical bills and insurance "
           "denials. We are not doctors, lawyers, benefits counselors, or insurance "
           "experts. We do not read your bills, fill out your forms, or tell you "
           "what you qualify for. We connect you to people who do that, and they do "
           "it for free. We never charge for anything.",
    "heads": ["The journey", "Get involved", "More"],
    "journey": ["Find free help", "Start here", "Bills & denials",
                "How a referral works", "For students", "For partners"],
    "involved": ["Find free help", "Join the corps", "Partner with us"],
    "more": ["Privacy & Legal", "Terms of Use"],
    "copy": "Waypoint. A student-led volunteer initiative in New York City. "
            "Michael, founder.",
    "short": ["Privacy", "Terms"],
    # the wordmark's accessible name. The visible text says "Waypoint Student
    # Health Corps", which is who, not where the link goes.
    "home": "Waypoint, home page",
}

# The anchors the journey column points at, in order. "Find free help" is not
# here: it goes to the directory, which is a different page in every language.
JOURNEY_ANCHORS = ["top", "bills", "work", "students", "partners"]
INVOLVED_ANCHORS = ["students", "partners"]


def _col(head, links, rtl=False):
    """One footer column: a heading and its links, all on one line.

    h2 rather than h4 because the pages run h1 then h2 sections and a column
    heading that skipped to h4 would break the outline for a screen reader.
    """
    out = [f'<div class="footer__col"><h2 class="footer__h">{esc(head)}</h2>']
    for href, label in links:
        d = ' dir="ltr"' if rtl and href.startswith("mailto:") else ""
        shown = EMAIL_SHOWN if href == f"mailto:{EMAIL}" else esc(label)
        out.append(f'<a href="{href}"{d}>{shown}</a>')
    out.append('</div>')
    return "".join(out)


def render(*, home="index.html", help_href="help.html", anchor="index.html#",
           words=None, rtl=False, extra=None, year_span=True):
    """The footer, as HTML.

    home        where the wordmark goes (a language page points at itself)
    help_href   the directory, in this page's language
    anchor      "#" on index.html, "index.html#" everywhere else
    words       a dict shaped like EN; defaults to English
    rtl         Arabic and Urdu: the wordmark and the address stay LTR
    extra       one line rendered under the bottom bar (the help pages' count)
    year_span   a <span data-year> the page's script refreshes on load
    """
    w = words or EN
    # zip() below truncates in silence, so a link added to EN and not to a
    # language would just be absent from that page's footer and from nowhere
    # else — the exact drift this module exists to prevent. Fail instead.
    for key in ("heads", "journey", "involved", "more", "short"):
        if len(w[key]) != len(EN[key]):
            raise ValueError(
                f'footer: "{key}" has {len(w[key])} items, English has '
                f'{len(EN[key])}. Add it to every language in i18n.py, or the '
                f'footer is not the same object on every page.')
    ltr = ' dir="ltr"' if rtl else ""

    journey = [(help_href, w["journey"][0])] + [
        (f"{anchor}{a}", label) for a, label in zip(JOURNEY_ANCHORS, w["journey"][1:])
    ]
    involved = [(help_href, w["involved"][0])] + [
        (f"{anchor}{a}", label) for a, label in zip(INVOLVED_ANCHORS, w["involved"][1:])
    ] + [(f"mailto:{EMAIL}", EMAIL)]
    more = list(zip(["privacy.html", "terms.html"], w["more"]))

    year = '<span data-year>2026</span>' if year_span else "2026"

    out = [
        '<footer class="footer">',
        '  <div class="footer__wrap">',
        '    <div class="footer__grid">',
        '      <div>',
        f'        <a class="brand" href="{home}" aria-label="{html.escape(w["home"])}">{PIN}'
        f'<span class="brand__txt"{ltr}>Waypoint<small>Student Health Corps</small>'
        '</span></a>',
        f'        <p class="footer__note">{esc(w["vow"])}</p>',
        '      </div>',
        '      ' + _col(w["heads"][0], journey, rtl),
        '      ' + _col(w["heads"][1], involved, rtl),
        '      ' + _col(w["heads"][2], more, rtl),
        '    </div>',
        '    <div class="footer__base">',
        f'      <p>© {year} {esc(w["copy"])}</p>',
        f'      <p><a href="privacy.html" class="footer__ul">{esc(w["short"][0])}</a>'
        f' · <a href="terms.html" class="footer__ul">{esc(w["short"][1])}</a></p>',
        '    </div>',
    ]
    if extra:
        out.append(f'    <p class="footer__ver">{extra}</p>')
    out += ['  </div>', '</footer>']
    return "\n".join(out)


def words_for(U):
    """The footer's words for a translated page, out of i18n.py's UI dict.

    Most of them were already there. The vow is the same paragraph the footer
    has always carried, and the journey column is the nav, in the nav's order —
    reusing them is what keeps a link from being worded one way in the header
    and another in the footer. Only the three column headings, "Start here",
    the terms link, the copyright line and the two short labels in the bottom
    bar had to be written for this footer.
    """
    return {
        "vow": U["vow"],
        "heads": U["foot_h"],
        "journey": [U["nav"][0], U["foot_start"]] + list(U["nav"][1:]),
        "involved": [U["nav"][0], U["foot_links"][2], U["foot_links"][3]],
        "more": [U["foot_links"][4], U["foot_terms"]],
        "copy": U["foot_copy"],
        "short": U["foot_short"],
        "home": U["home"],
    }


# ---- rewriting the hand-written pages -------------------------------------
#
# index.html anchors within itself; the other four have to name the page. That
# is the only thing that differs between them, and it is why this is a table
# and not five copies of a call.
PAGES = {
    "index.html":    {"anchor": "#"},
    "privacy.html":  {"anchor": "index.html#"},
    "terms.html":    {"anchor": "index.html#"},
    "partners.html": {"anchor": "index.html#"},
    "students.html": {"anchor": "index.html#"},
}

# The three standalone documents. They carry their own inline stylesheet, load
# none of the site's CSS, and are linked from nowhere: admin.html is a gated,
# noindex panel, the other two are handouts. A public footer on them would be
# furniture in a room nobody visits, so they are out of scope by name rather
# than by accident.
STANDALONE = {"admin.html", "cohort-onboarding.html", "partner-pitch.html"}


def params_for(name):
    """How render() has to be called for a given page.

    This is the table check.py reads. If a page is not in it, the page is not
    one this footer belongs on, and saying so here is the only place that
    decision is recorded.
    """
    if name in PAGES:
        return dict(anchor=PAGES[name]["anchor"])

    import build_help, i18n           # lazy: build_help imports this module
    for L in build_help.LANGUAGES:
        if build_help.lang_page(L["key"]) == name:
            return dict(home=name, help_href=name, anchor="index.html#",
                        words=words_for(i18n.UI[L["key"]]),
                        rtl=L["dir"] == "rtl")
    if name in ("help.html", "events.html", "suggest.html") \
            or name.startswith("help-"):
        return dict(anchor="index.html#")   # an English directory page
    return None


# The directory pages add one line under the bottom bar. Everything above it
# has to be identical to every other page, so the guard compares the footer
# with this line taken out.
VER_RE = re.compile(r'\n[ \t]*<p class="footer__ver">.*?</p>', re.S)


def shared_part(html_text):
    return VER_RE.sub("", html_text)


FOOTER_RE = re.compile(r'[ \t]*<footer class="footer">.*?</footer>', re.S)


def apply_to(path, anchor):
    """Swap the page's footer for the rendered one. Returns True if it changed."""
    src = path.read_text(encoding="utf-8")
    if not FOOTER_RE.search(src):
        raise SystemExit(f"{path.name}: no <footer class=\"footer\"> to replace")
    # a lambda, so backslashes and \g in the rendered footer stay literal
    new = FOOTER_RE.sub(lambda _: render(anchor=anchor), src, count=1)
    if new == src:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def main():
    changed = []
    for name, cfg in PAGES.items():
        if apply_to(ROOT / name, cfg["anchor"]):
            changed.append(name)
    print(f"footer: {len(changed)} of {len(PAGES)} hand-written pages rewritten"
          + (f" ({', '.join(changed)})" if changed else ""))


def demo():
    """python3 footer.py --demo"""
    en = render(anchor="#")
    assert en.count('<footer class="footer">') == 1
    assert en.count("</footer>") == 1
    # index anchors within itself, everyone else names the page
    assert 'href="#bills"' in en and 'href="index.html#bills"' not in en
    assert 'href="index.html#bills"' in render(anchor="index.html#")
    # every label in the table reaches the markup
    for label in EN["journey"] + EN["involved"] + EN["more"]:
        assert esc(label) in en, label
    # the ampersand is escaped exactly once, not doubled
    assert "Bills &amp; denials" in en and "&amp;amp;" not in en
    # three columns, three headings
    assert en.count('class="footer__col"') == 3
    assert en.count('class="footer__h"') == 3
    # the directory link follows the page's language
    assert 'href="help-es.html"' in render(anchor="index.html#", help_href="help-es.html")
    # the wordmark says where it goes, in the reader's language
    assert 'aria-label="Waypoint, home page"' in en
    import i18n
    assert f'aria-label="{i18n.UI["spanish"]["home"]}"' in render(
        anchor="index.html#", words=words_for(i18n.UI["spanish"]))
    # rtl keeps the wordmark and the address readable
    r = render(anchor="index.html#", rtl=True)
    assert 'class="brand__txt" dir="ltr"' in r
    assert f'href="mailto:{EMAIL}" dir="ltr"' in r
    assert ' dir="ltr"' not in en
    # a language missing a label fails loudly rather than dropping the link
    short = dict(EN); short["more"] = EN["more"][:1]
    try:
        render(anchor="#", words=short)
    except ValueError as e:
        assert "more" in str(e)
    else:
        raise AssertionError("a short word list was accepted")
    # the help pages' extra line lands inside the footer, after the bottom bar
    x = render(anchor="index.html#", extra="351 resources.")
    assert x.index("footer__base") < x.index("footer__ver") < x.index("</footer>")
    # a short word list must not silently drop links
    en_links = en.count("<a href=")
    assert en_links == 6 + 4 + 2 + 2, en_links   # journey + involved + more + base
    assert en.count('<a class="brand"') == 1
    print("footer.py: ok")


if __name__ == "__main__":
    import sys
    demo() if "--demo" in sys.argv else main()
