"""The live events page, and the featured row that reaches it.

Two renderers and one data file. `fetch_events.py` writes data/events.json
from other people's calendars; nothing here touches the network, so the build
and every guard over it stay offline and repeatable.

WHY THERE ARE NO PHOTOGRAPHS ON THESE CARDS

The feeds carry image URLs — about a third of the NYC Parks events have one —
and hotlinking them would have been one attribute. privacy.html names exactly
one third party, Google Fonts, and explains that the reader's browser hands it
an IP address. Loading art from nycgovparks.org would have added a second
without saying so, on the page most likely to be opened by somebody who was
promised the site asks nothing of them. The card art is painted here instead,
out of the same palette as the rest of the site.

To put the photographs back, the honest way is to download them at fetch time
into assets/ and serve them from this origin. That is an image pipeline and a
licensing question, not an attribute.
"""

import json
from datetime import date, datetime
from pathlib import Path

DATA = Path("data/events.json")

# How many events the front page's featured row shows. Six is what
# fetch_events.py ranks; this is the render side of the same number.
FEATURED = 6


def load():
    """The events file, or an empty shell if it has never been fetched.

    An empty shell rather than an exception: a fresh clone has no events file,
    and `python3 build_help.py` has to work in a fresh clone. Every renderer
    below degrades to saying there is nothing on yet.
    """
    if not DATA.exists():
        return {"generated": "", "events": [], "featured": [], "sources": []}
    return json.loads(DATA.read_text("utf-8"))


# ------------------------------------------------------------------- pieces

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse(s):
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")


def clock(dt, all_day=False):
    """4pm, not 4:00 PM. 12:30pm, not 12:30 PM."""
    if all_day:
        return ""
    h, m = dt.hour, dt.minute
    ap = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{ap}" if m else f"{h12}{ap}"


def when(e):
    """The one line that says when, in as few characters as it can."""
    s = parse(e["start"])
    if e.get("all_day"):
        return f"{MONTHS[s.month - 1][:3]} {s.day}"
    t = clock(s)
    try:
        en = parse(e["end"])
        if en > s and en.date() == s.date():
            t = f"{t}–{clock(en)}"
    except (ValueError, KeyError):
        pass
    return f"{MONTHS[s.month - 1][:3]} {s.day}, {t}"


def where(e):
    bits = [b for b in (e.get("venue"), e.get("borough")) if b]
    # A venue that already names its borough should not say it twice.
    if len(bits) == 2 and bits[1].lower() in bits[0].lower():
        bits = bits[:1]
    return ", ".join(bits) or "See the listing"


def day_id(d):
    return f"d-{d}"


# Three glyphs the cards need that the directory's icon set does not have.
# Same stroke weight and box as build_help.icon() so they sit in a row with it.
def _svg(path, cls="ico"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" '
            f'fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round">{path}</svg>')


CAL = _svg('<rect x="3" y="5" width="18" height="16" rx="2"/>'
           '<path d="M8 3v4M16 3v4M3 10h18"/>')
PIN = _svg('<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>'
           '<circle cx="12" cy="10" r="3"/>')
PERSON = _svg('<circle cx="12" cy="8" r="3.4"/>'
              '<path d="M5 20a7 7 0 0 1 14 0"/>', "ico ico--sm")
SCREEN = _svg('<rect x="2.5" y="5" width="19" height="13" rx="2"/>'
              '<path d="M9 21h6"/>', "ico ico--sm")


def fmt_icon(e):
    return SCREEN if e.get("format") == "Virtual" else PERSON


# Buckets that are not one of the directory's needs. An event is filed here
# when it is a real, free, public thing that simply is not what this site
# exists to help with — a park concert is not a category of help.
EXTRA = {"other": "Community & recreation"}


def trim(s, n):
    """Cut to a word boundary and say that it was cut.

    The feeds' own text is already trimmed to 260 characters with an ellipsis;
    cutting that again to fit a card dropped the ellipsis and ended events
    mid-word — "Join us to ce".
    """
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0].rstrip(" ,;:.—-") + "…"


def need_label(need_key, build_help):
    if need_key in EXTRA:
        return EXTRA[need_key]
    for n in build_help.NEEDS:
        if n["key"] == need_key:
            return n["short"]
    return "Free event"


def need_icon(need_key, build_help):
    for n in build_help.NEEDS:
        if n["key"] == need_key:
            return build_help.icon(n["icon"])
    return build_help.icon("compass")


def card_art(e, build_help):
    """The panel where a photograph would be.

    Tinted per category out of tokens.css so a row of cards reads as a set
    rather than a gallery, with the category's own glyph large in the middle.
    """
    esc = build_help.esc
    return (f'<span class="fev__art" data-need="{esc(e["need"])}" aria-hidden="true">'
            f'{need_icon(e["need"], build_help)}</span>')


def pills(e, build_help):
    esc = build_help.esc
    out = [f'<span class="bdg bdg--need">{esc(need_label(e["need"], build_help))}</span>',
           f'<span class="bdg bdg--fmt">{fmt_icon(e)}{esc(e.get("format") or "In person")}</span>']
    return '<span class="fev__pills">' + "".join(out) + "</span>"


def card(e, build_help, lead=False):
    """One event.

    The heading holds the only link, and help.css stretches it over the card
    with ::after — the same device as the directory masthead. A card wrapped
    in one big anchor reads its whole contents out as the link name, which on
    a screen reader is a sentence nobody asked for.
    """
    esc = build_help.esc
    cls = "fev__c fev__c--lead" if lead else "fev__c"
    a = [f'<li class="{cls}">', '  <article class="fev__card">']
    a.append(f'    <span class="fev__pic">{card_art(e, build_help)}{pills(e, build_help)}</span>')
    a.append('    <span class="fev__body">')
    if lead:
        a.append('      <span class="bdg bdg--feat">Featured</span>')
    a.append(f'      <h3 class="fev__h"><a href="{esc(e["url"])}" target="_blank" '
             f'rel="noopener">{esc(e["title"])}</a></h3>')
    if lead and e.get("description"):
        a.append(f'      <p class="fev__b">{esc(trim(e["description"], 150))}</p>')
    a.append(f'      <p class="fev__meta"><span class="fev__m">{CAL}{esc(when(e))}</span>'
             f'<span class="fev__sep" aria-hidden="true">&mdash;</span>'
             f'<span class="fev__m">{PIN}{esc(where(e))}</span></p>')
    a.append(f'      <span class="fev__go">Explore event <span class="arr">&rarr;</span></span>')
    a.append('    </span>')
    a += ['  </article>', '</li>']
    return a


# --------------------------------------------------- the row on help.html

def featured_frag(doc, build_help):
    """The featured row, as the directory front page carries it.

    Returns [] when there are no events. A carousel with nothing in it is
    worse than no carousel: it is a promise the page cannot keep.
    """
    by_id = {e["id"]: e for e in doc.get("events", [])}
    picks = [by_id[i] for i in doc.get("featured", []) if i in by_id][:FEATURED]
    if not picks:
        return []

    n = len(doc.get("events", []))
    a = ['<section class="fev" aria-labelledby="fev-h">',
         '  <div class="fev__top">',
         '    <div>',
         '      <h2 id="fev-h">Featured events</h2>',
         '      <p class="fev__say">Free things happening around the city &mdash; '
         'food, legal help, and places to take the kids.</p>',
         '    </div>',
         # Arrows are an enhancement: the track scrolls and swipes without
         # them, so they start hidden and help.js shows them.
         '    <div class="fev__nav" hidden>',
         '      <button type="button" class="fev__arw" data-fev="prev" '
         'aria-controls="fevTrack" aria-label="Show the previous events">'
         '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
         'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
         'stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg></button>',
         '      <button type="button" class="fev__arw" data-fev="next" '
         'aria-controls="fevTrack" aria-label="Show the next events">'
         '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
         'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
         'stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg></button>',
         '    </div>',
         '  </div>',
         '  <ul class="fev__track" id="fevTrack">']
    for i, e in enumerate(picks):
        a += ["    " + ln for ln in card(e, build_help, lead=(i == 0))]
    a.append('  </ul>')
    a.append(f'  <a class="fev__all" href="events.html">See all {n} events, '
             f'and the calendar <span class="arr">&rarr;</span></a>')
    a.append('</section>')
    return a


# ------------------------------------------------------------- the calendar

def month_grid(year, month, counts, build_help):
    """One month, Monday-first, with a count on every day that has something.

    Every day with events is a link to that day's heading further down the
    page, so the calendar works with JavaScript off. help.js upgrades the same
    links into a filter.
    """
    esc = build_help.esc
    first = date(year, month, 1)
    lead = first.weekday()
    days = (date(year + (month == 12), month % 12 + 1, 1) - first).days
    today = date.today()

    a = [f'<div class="cal__m" data-month="{year}-{month:02d}">',
         f'  <h3 class="cal__mh">{MONTHS[month - 1]} {year}</h3>',
         '  <div class="cal__dow" aria-hidden="true">'
         + "".join(f"<span>{d[0]}</span>" for d in DAYS) + '</div>',
         '  <ul class="cal__grid">']
    for _ in range(lead):
        a.append('    <li class="cal__d cal__d--pad" aria-hidden="true"></li>')
    for dnum in range(1, days + 1):
        d = date(year, month, dnum)
        key = d.isoformat()
        c = counts.get(key, 0)
        cls = "cal__d"
        if c:
            cls += " cal__d--on"
        if d == today:
            cls += " cal__d--today"
        if c:
            label = (f'{c} event{"s" if c != 1 else ""} on '
                     f'{DAYS[d.weekday()]} {MONTHS[month - 1]} {dnum}')
            # The class goes on the anchor, not the <li>: the anchor is the
            # thing you can focus, and check_focus_ring decides whether a dark
            # rule is a room or a control by asking whether its class ever
            # lands on a focusable tag.
            a.append(f'    <li class="{cls}"><a class="cal__a" '
                     f'href="#{day_id(key)}" '
                     f'data-day="{key}" aria-label="{esc(label)}">'
                     f'<span class="cal__n">{dnum}</span>'
                     f'<span class="cal__c" aria-hidden="true">{c}</span></a></li>')
        else:
            a.append(f'    <li class="{cls}"><span class="cal__n">{dnum}</span></li>')
    a += ['  </ul>', '</div>']
    return a


def calendar_frag(events, build_help):
    counts = {}
    for e in events:
        k = e["start"][:10]
        counts[k] = counts.get(k, 0) + 1
    if not counts:
        return []
    months = sorted({k[:7] for k in counts})
    a = ['<section class="cal" aria-labelledby="cal-h">',
         '  <div class="cal__top">',
         '    <h2 id="cal-h">Pick a day</h2>',
         '    <p class="cal__say">A number means something is happening. '
         'Tap a day to see only that day.</p>',
         '  </div>',
         '  <div class="cal__ms">']
    for m in months:
        y, mo = int(m[:4]), int(m[5:7])
        a += ["    " + ln for ln in month_grid(y, mo, counts, build_help)]
    a += ['  </div>',
          '  <p class="cal__reset" hidden><button type="button" class="linkish" '
          'data-cal="all">Show every day again</button></p>',
          '</section>']
    return a


# ------------------------------------------------------------ the day list

def day_block(key, evs, build_help):
    esc = build_help.esc
    d = date.fromisoformat(key)
    today = date.today()
    rel = ""
    if d == today:
        rel = "Today"
    elif (d - today).days == 1:
        rel = "Tomorrow"
    head = f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}"
    a = [f'<section class="day" id="{day_id(key)}" data-day="{key}" '
         f'aria-labelledby="h-{day_id(key)}">',
         f'  <h3 class="day__h" id="h-{day_id(key)}">{esc(head)}'
         + (f' <span class="day__rel">{rel}</span>' if rel else "")
         + f' <span class="day__n">{len(evs)}</span></h3>',
         '  <ul class="day__list">']
    for e in evs:
        s = parse(e["start"])
        t = clock(s, e.get("all_day")) or "All day"
        a += [
            f'    <li class="ev" data-need="{esc(e["need"])}" '
            f'data-boro="{esc(e.get("borough") or "")}" '
            f'data-fmt="{esc(e.get("format") or "")}">',
            f'      <span class="ev__t">{esc(t)}</span>',
            '      <span class="ev__main">',
            f'        <h4 class="ev__h"><a href="{esc(e["url"])}" target="_blank" '
            f'rel="noopener">{esc(e["title"])}</a></h4>',
        ]
        if e.get("description"):
            a.append(f'        <p class="ev__b">{esc(trim(e["description"], 180))}</p>')
        a.append(f'        <p class="ev__meta">{PIN}<span>{esc(where(e))}</span>'
                 f'<span class="ev__dot" aria-hidden="true">&middot;</span>'
                 f'<span class="ev__by">{esc(e["source"])}</span></p>')
        a.append('      </span>')
        a.append('      <span class="ev__tags">'
                 f'<span class="bdg bdg--need">{esc(need_label(e["need"], build_help))}</span>'
                 f'<span class="bdg bdg--fmt">{fmt_icon(e)}'
                 f'{esc(e.get("format") or "In person")}</span>'
                 + (f'<span class="bdg bdg--free">Free</span>' if e.get("free") else "")
                 + '</span>')
        a.append('    </li>')
    a += ['  </ul>', '</section>']
    return a


# --------------------------------------------------------------- whole page

def render_page(doc, build_help, rows):
    esc = build_help.esc
    events = doc.get("events", [])
    n = len(events)

    by_day = {}
    for e in events:
        by_day.setdefault(e["start"][:10], []).append(e)
    for k in by_day:
        by_day[k].sort(key=lambda e: (e["start"], e["title"]))

    boros = sorted({e["borough"] for e in events if e.get("borough")})
    present = {e["need"] for e in events}
    needs = [nd for nd in build_help.NEEDS if nd["key"] in present]
    needs += [{"key": k, "short": v} for k, v in EXTRA.items() if k in present]

    p = []
    A = p.append
    p += build_help.head(
        "Free events happening in New York City — Waypoint",
        "A day-by-day calendar of free events in New York City: mobile food "
        "pantries, free legal help, and things to do in every borough. Updated "
        "every morning from the organizations that run them.",
        "#cal-h", "Skip to the calendar",
        build_help.alternates("events.html"))
    p += build_help.header_frag()
    A('<main class="wrap">')

    # ---- masthead, the same shape as the directory's
    A('<section class="mast mast--ev">')
    A('  <div class="mast__bg" aria-hidden="true"></div>')
    A('  <span class="eyebrow mast__eye">Waypoint &middot; New York City</span>')
    A('  <h1>Free events, <em>day by day.</em></h1>')
    if n:
        A(f'  <p class="mast__say">There are <b>{n} free events</b> on this page, '
          'from mobile food pantries and free legal help to story hours and '
          'fitness classes in the parks. Pick a day below.</p>')
    else:
        A('  <p class="mast__say">The events list has not been collected yet. '
          'The directory is still here, and every phone number on it works.</p>')
    A('  <p class="mast__say mast__say--2">Nothing here needs an account. '
      'Each one links to the organization running it, so you can check the '
      'details and go.</p>')
    A('</section>')

    # For paper. The events page is the one somebody prints to take to a
    # table, and a printed sheet with no source on it is a photocopy of
    # nothing. Same sentence as the directory's, because it makes the same
    # claim about the same collection.
    A('<div class="printhead" aria-hidden="true">')
    A('  <p class="printhead__s">Collected by Waypoint, a student volunteer '
      'corps. We do not run any of these programs &mdash; we help people find '
      f'them. Checked {build_help.checked(rows)}; programs change. Every event '
      'here links to the organization running it.</p>')
    A('</div>')

    if n:
        A(f'<p class="ev__fresh">Collected from '
          f'{len(doc.get("sources", []))} public calendars, last updated '
          f'{build_help.esc(freshness(doc))}. Times and places come from the '
          f'organizations themselves &mdash; call ahead if you are going far.</p>')

    A('<noscript><p class="noscript-note">The day picker and the filters need '
      'JavaScript, which is turned off. Nothing is lost: every event is on '
      'this page already, listed under the day it happens, and every link '
      'works.</p></noscript>')

    p += calendar_frag(events, build_help)

    # ---- filters. Plain checkboxes wrapped in labels: the whole control is
    # the hit area, and with JavaScript off they are simply inert.
    if n:
        A('<section class="evf" aria-labelledby="evf-h" hidden>')
        A('  <h2 id="evf-h" class="evf__h">Narrow it down</h2>')
        A('  <div class="evf__row">')
        # id + <label for>, not a label wrapped around the input. Both are
        # valid HTML and only the first is what check_labels looks for — and
        # the rest of the site's forms are written this way, so matching them
        # is cheaper than arguing with the guard.
        def opt(kind, value, label):
            i = f'f-{kind}-{build_help.slug(value)}'
            A(f'      <label class="evf__o" for="{i}">'
              f'<input id="{i}" type="checkbox" data-f="{kind}" '
              f'value="{esc(value)}" /> <span>{esc(label)}</span></label>')

        A('    <fieldset class="evf__set"><legend>What kind</legend>')
        for nd in needs:
            opt("need", nd["key"], nd["short"])
        A('    </fieldset>')
        if boros:
            A('    <fieldset class="evf__set"><legend>Where</legend>')
            for b in boros:
                opt("boro", b, b)
            A('    </fieldset>')
        A('    <fieldset class="evf__set"><legend>How</legend>')
        for f in ("In person", "Virtual"):
            if any(e.get("format") == f for e in events):
                opt("fmt", f, f)
        A('    </fieldset>')
        A('  </div>')
        A('  <p class="evf__state" role="status"></p>')
        A('</section>')

    # ---- the days
    A('<div class="days" id="days">')
    if not by_day:
        A('  <p class="dir__none">No events are listed right now. The '
          '<a href="help.html">directory</a> is still here, and every phone '
          'number on it works.</p>')
    for k in sorted(by_day):
        p += ["  " + ln for ln in day_block(k, by_day[k], build_help)]
    A('  <p class="days__none" hidden>Nothing matched that. '
      '<button type="button" class="linkish" data-cal="all">Show everything '
      'again</button></p>')
    A('</div>')

    # ---- tell us about one. Posts to the same edge function as every other
    # form on the site; form_type is what sorts them in the admin list.
    A('<section class="tellus" id="add" aria-labelledby="tellus-h">')
    A('  <h2 id="tellus-h">Know an event that is not here?</h2>')
    A('  <p class="tellus__say">If your organization runs something free and '
      'open to the public, tell us and we will add it. We read every one.</p>')
    A('  <form class="tellus__f" data-form="event">')
    A('    <div class="tellus__g">')
    A('      <label for="ev-name">Your name</label>')
    A('      <input id="ev-name" name="name" type="text" autocomplete="name" required />')
    A('    </div>')
    A('    <div class="tellus__g">')
    A('      <label for="ev-email">Your email, so we can ask if something is unclear</label>')
    A('      <input id="ev-email" name="email" type="email" autocomplete="email" required />')
    A('    </div>')
    A('    <div class="tellus__g">')
    A('      <label for="ev-what">What is the event, and who runs it?</label>')
    A('      <input id="ev-what" name="event" type="text" required />')
    A('    </div>')
    A('    <div class="tellus__g">')
    A('      <label for="ev-when">When is it?</label>')
    A('      <input id="ev-when" name="when" type="text" '
      'placeholder="Saturdays, 10am to noon" required />')
    A('    </div>')
    A('    <div class="tellus__g">')
    A('      <label for="ev-where">Where is it, or is it online?</label>')
    A('      <input id="ev-where" name="where" type="text" required />')
    A('    </div>')
    A('    <div class="tellus__g">')
    A('      <label for="ev-link">A link with the details, if there is one</label>')
    A('      <input id="ev-link" name="link" type="url" inputmode="url" />')
    A('    </div>')
    # Honeypot, the same one script.js already knows how to read.
    A('    <div class="trap" aria-hidden="true"><label for="ev-trap">Leave this '
      'empty</label><input id="ev-trap" name="trap" type="text" tabindex="-1" '
      'autocomplete="off" /></div>')
    A('    <button type="submit" class="btn">Send it to us</button>')
    A('    <p class="form__ok" role="status">Thank you &mdash; we have it.</p>')
    A('    <p class="form__err" role="alert">That did not send. Please email '
      '<a href="mailto:waypointoutreach@gmail.com">waypointoutreach@gmail.com</a>.</p>')
    A('  </form>')
    A('</section>')

    # ---- where this came from
    if doc.get("sources"):
        A('<section class="src" aria-labelledby="src-h">')
        A('  <h2 id="src-h" class="src__h">Where these come from</h2>')
        A('  <ul class="src__l">')
        for s in doc["sources"]:
            A(f'    <li><a href="{esc(s["site"])}" target="_blank" rel="noopener">'
              f'{esc(s["name"])}</a> &mdash; {esc(s["note"])}</li>')
        A('  </ul>')
        A('</section>')

    # The same honesty paragraph the directory carries. This is a page a
    # resident reads, so it makes the same promise in the same words.
    p += build_help.vow_frag()
    A('</main>')
    # The site footer's sentence is about the directory — its resource count
    # and the span those resources were checked over. Passing the event count
    # here made it say "175 resources", which is a different number about a
    # different thing. How fresh the events are is said in the page instead.
    p += build_help.footer_frag(len(rows), build_help.checked(rows))
    return "\n".join(p) + "\n"


def freshness(doc):
    g = doc.get("generated") or ""
    if not g:
        return "recently"
    try:
        d = datetime.strptime(g[:10], "%Y-%m-%d").date()
    except ValueError:
        return "recently"
    if d == date.today():
        return "this morning"
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"
