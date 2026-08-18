#!/usr/bin/env python3
"""
Waypoint site checks.

Guards the things that rot silently: dead links and anchors, missing assets,
the honesty statement drifting out of any surface that must carry it verbatim,
overclaims about what a volunteer may do with a bill or a denial,
stale references to programmes we do not run, and the asset-size budget that
keeps the site fast on a library's wifi.

    python3 check.py            # run everything
    python3 check.py -v         # list every passing check too

No dependencies. Exits non-zero on the first failing category.
"""

import html
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv

PAGES = ["index.html", "privacy.html", "terms.html", "partner-pitch.html",
         "cohort-onboarding.html", "students.html", "partners.html", "admin.html"]

# Printed on every flyer, every table sign, and the site. It exists to stop a
# vulnerable person mistaking a student for a professional; it does not get
# reworded. Source of truth: Mission & Operating Model v2.0, section 8.
#
# Fragment rules, learned from how strip_tags() works: each fragment must be a
# contiguous, tag-free run (a tag mid-fragment becomes a space and breaks the
# match), and matching is case-sensitive, so fragments start mid-sentence where
# the surrounding wording may differ.
HONESTY = ("We are trained student volunteers.",
           "not doctors, lawyers, benefits counselors, or insurance experts",
           "do not read your bills, fill out your forms, or tell you what you qualify for")

# The statement is duplicated by hand with no shared source, so the linter is
# the shared source. index.html carries it twice: the vow scene and the footer.
HONESTY_SURFACES = {"index.html": 2, "partner-pitch.html": 1, "cohort-onboarding.html": 1}

# Cut from the public site: schools/replication and the Companionship track.
FORBIDDEN = [
    (r"#schools\b", "link to the removed Schools chapter"),
    (r"\bCompanionship\b", "the Companionship track, which we do not run yet"),
    (r"waypoint\.example", "placeholder contact domain"),
    (r"\[website URL\]", "unfilled placeholder"),
    (r"assets/land\d\.png", "unoptimised PNG landscape (use .webp)"),
    (r"\bTrack [AB]\b", "internal track naming"),
    (r"a working name", "the org name is settled; drop the placeholder hedge"),
    # The billing vertical's own failure modes. Volunteers never state
    # eligibility, quote a deadline, promise an outcome, or read like a lawyer.
    (r"\b\d+\s*%\s*of the federal poverty (?:level|line)\b",
     "a numeric eligibility threshold; who qualifies is never ours to state"),
    (r"501\(r\)|26 U\.S\.C\.|Public Health Law\s*(?:§|Section)|N\.Y\. Pub(?:lic)?\.? Health",
     "a statute citation; describe the role, do not cite the law"),
    (r"\bfree bill (?:review|audit)\b", "a bill-review service we do not provide"),
    (r"\b(?:success fee|contingency fee|% of (?:your )?savings)\b",
     "a fee model; we never charge for anything"),
    (r"\bmedical debt (?:relief|forgiveness|settlement)\b",
     "debt work that is neither ours to do nor ours to promise"),
    # Roadmap vocabulary. Everyone reading these pages is deciding whether to
    # volunteer or to work with us, and neither decision is helped by knowing
    # what is sequenced behind what. The phasing is an operating decision and it
    # lives in PRODUCT.md, which is not a page. Name the work, not the plan.
    (r"\bsecond track\b", "roadmap vocabulary; name the work, not its position in a plan"),
    (r"\bsequenced behind\b", "roadmap vocabulary; the reader is not managing our backlog"),
    (r"\bhalf-built\b", "roadmap vocabulary; an internal justification, not visitor copy"),
]

failures, passes = [], []


def ok(msg):
    passes.append(msg)


def bad(msg):
    failures.append(msg)


class Missing(Exception):
    """A file a check needs is not there."""


def read(p):
    """Never raise past main(): a crashed harness reports nothing at all,
    which is strictly worse than a harness that reports one missing file."""
    f = ROOT / p
    if not f.is_file():
        raise Missing(str(p))
    return f.read_text(encoding="utf-8")


def strip_tags(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def strip_comments(s):
    """Markup only. Every check that greps for the absence of something has to
    run on this: the comment explaining why a thing is absent contains the
    thing, and matching your own explanation is a false positive that reads
    exactly like a real one."""
    return re.sub(r"<!--.*?-->", " ", s, flags=re.S)


# ---------------------------------------------------------------- structure
def check_pages_exist():
    for p in PAGES:
        if (ROOT / p).is_file():
            ok(f"page present: {p}")
        else:
            bad(f"missing page: {p}")
    if (ROOT / "schools.html").exists():
        bad("schools.html still exists; the Schools chapter was removed")
    else:
        ok("schools.html removed")


# ------------------------------------------------------------ links/assets
LOCAL_REF = re.compile(r'(?:href|src)="(?!https?:|mailto:|tel:|data:|#)([^"]+)"')
STYLE_URL = re.compile(r"url\(['\"]?(?!data:|https?:)([^'\")]+)['\"]?\)")
ANCHOR = re.compile(r'href="#([^"]+)"')
ID = re.compile(r'\sid="([^"]+)"')


def check_links():
    for page in PAGES:
        if not (ROOT / page).is_file():
            continue
        src = read(page)
        for ref in set(LOCAL_REF.findall(src)) | set(STYLE_URL.findall(src)):
            target = (ROOT / ref.split("?")[0].split("#")[0]).resolve()
            if target.exists():
                ok(f"{page} -> {ref}")
            else:
                bad(f"{page}: dead reference {ref!r}")

        ids = set(ID.findall(src))
        for a in set(ANCHOR.findall(src)):
            if page == "index.html" or a in ids:
                if a in ids:
                    ok(f"{page} anchor #{a}")
                else:
                    bad(f"{page}: anchor #{a} has no matching id")


CROSS_REF = re.compile(r'href="([A-Za-z0-9._-]+\.html)#([^"]+)"')


def check_cross_page_anchors():
    """Any local page.html#fragment link must land on a real id, whichever page
    it points at. Checking only index.html let broken secondary anchors pass."""
    ids_by_page = {}

    def ids_for(target):
        if target not in ids_by_page:
            if not (ROOT / target).is_file():
                ids_by_page[target] = None
            else:
                ids_by_page[target] = set(ID.findall(read(target)))
        return ids_by_page[target]

    for page in PAGES:
        if not (ROOT / page).is_file():
            continue
        for target, frag in set(CROSS_REF.findall(read(page))):
            known = ids_for(target)
            if known is None:
                bad(f"{page}: links to {target}#{frag} but {target} does not exist")
            elif frag in known:
                ok(f"{page} -> {target}#{frag}")
            else:
                bad(f"{page}: {target}#{frag} has no matching id in {target}")


def check_stage_layers():
    """Lazily-loaded landscape layers carry data-src instead of an inline url."""
    src = read("index.html")
    lazy = re.findall(r'class="stage__layer"[^>]*data-src="([^"]+)"', src)
    eager = re.findall(r'class="stage__layer"[^>]*background-image:url\(\'([^\']+)\'\)', src)
    for ref in lazy + eager:
        if (ROOT / ref).is_file():
            ok(f"stage layer asset {ref}")
        else:
            bad(f"stage layer asset missing: {ref}")
    if len(lazy) == 3 and len(eager) == 1:
        ok("stage: first landscape eager, the other three deferred")
    else:
        bad(f"stage layers: expected 1 eager + 3 deferred, got {len(eager)} + {len(lazy)}")


# ------------------------------------------------------------------ content
def check_honesty_statement():
    """Every surface that must carry the statement, carries all of it.

    Checking only index.html let the pitch and onboarding copies drift, which is
    exactly the failure this statement exists to prevent: the printed leave-behind
    saying something the site does not."""
    for page, times in HONESTY_SURFACES.items():
        if not (ROOT / page).is_file():
            bad(f"{page}: missing, so the honesty statement cannot be verified")
            continue
        text = re.sub(r"\s+", " ", strip_tags(read(page)))
        for fragment in HONESTY:
            n = text.count(fragment)
            if n >= times:
                ok(f"{page}: honesty fragment present {n}x")
            else:
                bad(f"{page}: honesty statement altered or missing "
                    f"({n}x, expected {times}x): {fragment!r}")


def check_forbidden():
    for page in PAGES:
        if not (ROOT / page).is_file():
            continue
        src = read(page)
        for pattern, why in FORBIDDEN:
            hits = re.findall(pattern, src)
            if hits:
                bad(f"{page}: contains {why} ({len(hits)}x, e.g. {hits[0]!r})")
            else:
                ok(f"{page}: no {why}")


def check_no_invented_numbers():
    """We have run no events. Nothing on the site may imply a track record."""
    text = re.sub(r"\s+", " ", strip_tags(read("index.html")))
    claims = re.findall(r"\b\d[\d,]*\+?\s+(?:people|events|partners|volunteers|residents|New Yorkers|students)\b", text, re.I)
    if claims:
        bad(f"index.html: numeric track-record claim found: {claims}")
    else:
        ok("index.html: no numeric track-record claims")
    if "have not held" in text or "not held its first event" in text:
        ok("index.html: pre-launch status stated plainly")
    else:
        bad("index.html: the page should say the first event has not happened yet")


# ------------------------------------------------------- billing boundaries
# Students inform and refer. They never read a document, state eligibility,
# quote a deadline, or promise an outcome. These guards cannot live in
# FORBIDDEN, because our own boundary sentences contain the same verbs under a
# negation ("they do not read your bills"). So: split into sentences, drop the
# ones carrying a negation cue, and only then look for an affirmative claim.
BILLING_OVERCLAIM = [
    (r"\b(?:we|our students|students|volunteers)\s+(?:can\s+|will\s+|also\s+|)"
     r"(?:negotiate|settle|dispute|appeal|reduce|lower|erase|forgive|waive|wipe)\b",
     "a first-person claim to do the regulated billing work"),
    (r"\b(?:we|our students|students|volunteers)\s+(?:can\s+|will\s+|)"
     r"(?:file|submit|complete|fill out|draft)\s+(?:the|your|an?|any)\s+"
     r"(?:application|appeal|form|paperwork|letter)\b",
     "a claim to file or draft on somebody's behalf"),
    (r"\b(?:reduc\w*|lower\w*|eras\w*|forgiv\w*|settl\w*|wip\w*)\s+"
     r"(?:your|their|the|a|any)\s+(?:hospital\s+|medical\s+)?(?:bill|bills|debt)\b",
     "an outcome claim about somebody's bill"),
    (r"\byou (?:will |)(?:qualify|are eligible)\b",
     "an eligibility determination, which is never ours to make"),
    (r"\b(?:we|our students|students|volunteers)\s+(?:can\s+|will\s+|)"
     r"(?:read|review|interpret|look over)\s+(?:your|their|the)\s+"
     r"(?:bill|bills|denial|letter|paperwork|documents?)\b",
     "a claim to read documents, which is the first of the eight nevers"),
]
NEGATION = re.compile(r"\b(?:never|not|cannot|can't|don't|doesn't|no|without|instead of)\b", re.I)


def check_billing_boundaries():
    for page in PAGES:
        if not (ROOT / page).is_file():
            continue
        text = re.sub(r"\s+", " ", strip_tags(read(page)))
        hits = []
        for sentence in re.split(r"(?<=[.!?;])\s+", text):
            if NEGATION.search(sentence):
                continue           # a boundary statement, not a claim
            for pattern, why in BILLING_OVERCLAIM:
                m = re.search(pattern, sentence, re.I)
                if m:
                    hits.append((why, m.group(0)))
        if hits:
            bad(f"{page}: overclaims on billing: {hits[:3]}")
        else:
            ok(f"{page}: no billing overclaim")

    # the positive half: the primary chapter has to actually be on the page
    idx = read("index.html")
    text = re.sub(r"\s+", " ", strip_tags(idx))
    if 'id="bills"' in idx:
        ok("index.html: the billing chapter has an anchor")
    else:
        bad('index.html: no id="bills"; bills and denials are the primary identity')
    for phrase in ["financial assistance", "denial"]:
        if phrase in text:
            ok(f"index.html: names {phrase!r}")
        else:
            bad(f"index.html: must name {phrase!r}")
    money = re.findall(r"\$\s?\d[\d,]*", text)
    if money:
        bad(f"index.html: dollar figures imply an outcome we cannot promise: {money[:3]}")
    else:
        ok("index.html: no dollar figures")


def check_forms():
    src = read("index.html")
    kinds = re.findall(r'data-form="([^"]+)"', src)
    if sorted(kinds) == ["partners", "students"]:
        ok("forms: partners + students only")
    else:
        bad(f"forms: expected partners+students, found {kinds}")
    for kind in kinds:
        block = src.split(f'data-form="{kind}"', 1)[1]
        for needed in ["trap", "form__ok", "form__err", "form__legal"]:
            if needed in block.split("</form>")[0]:
                ok(f"form {kind}: has {needed}")
            else:
                bad(f"form {kind}: missing {needed}")


def check_labels():
    """Every input/select/textarea needs a label bound to it."""
    src = read("index.html")
    fors = set(re.findall(r'<label for="([^"]+)"', src))
    fields = re.findall(r'<(?:input|select|textarea)[^>]*\sid="([^"]+)"', src)
    for fid in fields:
        if fid in fors:
            ok(f"labelled field #{fid}")
        else:
            bad(f"field #{fid} has no <label for>")
    traps = re.findall(r'class="trap"[^>]*', src)
    for t in traps:
        if 'aria-hidden="true"' in t and 'tabindex="-1"' in t:
            ok("honeypot hidden from assistive tech and tab order")
        else:
            bad("honeypot must be aria-hidden and out of the tab order")


# ------------------------------------------------------------------ the door
def check_door():
    door = read("assets/door.js")
    for token in ["prefers-reduced-motion", "webglOK", "no-gl", "still", "AdditiveBlending"]:
        if token in door:
            ok(f"door.js: {token}")
        else:
            bad(f"door.js: missing {token}")
    css = read("styles.css")
    if ".doorstage__poster" in css and ".no-gl" in css:
        ok("CSS poster fallback present for no-WebGL")
    else:
        bad("CSS poster fallback missing")
    if re.search(r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)", css):
        ok("reduced-motion block present")
    else:
        bad("reduced-motion block missing from styles.css")
    idx = read("index.html")
    if 'type="module" src="assets/door.js"' in idx:
        ok("door.js loaded as a module")
    else:
        bad("door.js not loaded as a module")


def check_transition_invariants():
    """The three things that made the transition look broken, guarded."""
    door = read("assets/door.js")
    css = read("styles.css")
    idx = read("index.html")
    js = read("script.js")

    # 1. the camera must stop in front of the wall. Crossing it puts the eye
    #    through the light-shaft quads and the wall, which is the diagonal-band bug.
    m = re.search(r"const END_Z\s*=\s*([\d.]+)", door)
    if m and float(m.group(1)) > 0.2:
        ok(f"door: camera stops at z={m.group(1)}, in front of the wall")
    else:
        bad("door: END_Z must stay in front of the wall (> 0.2)")
    if re.search(r"lerp\(START_Z,\s*-", door):
        bad("door: camera dollies past the wall again")
    else:
        ok("door: camera never dollies past the wall")

    # 2. the shaft's near end has to stay clear of the lens, or the layers
    #    stack additively across the whole viewport into a flat wash
    if "camZ * 0.55" in door or re.search(r"reach\s*=.*camZ\s*\*", door):
        ok("door: shaft length is proportional to camera distance")
    else:
        bad("door: shaft near end is not tied to the camera distance")

    # 3. one fixed reading veil, never per-section scrims: two adjacent section
    #    gradients both fade out at their shared edge and leave a bright seam
    if '<div class="readveil"' in idx and ".readveil{" in css:
        ok("single fixed reading veil present")
    else:
        bad("the fixed .readveil layer is missing")
    for sel in [".scene--hold::before", ".scene--vow::before"]:
        if sel in css:
            bad(f"{sel} is back: per-section scrims band at every section seam")
        else:
            ok(f"no per-section scrim on {sel.split('::')[0]}")
    if "--readVeil" in js and "--readVeil" in css:
        ok("reading veil is driven from the scroll loop")
    else:
        bad("--readVeil is not wired between script.js and styles.css")

    # 4. the thread fades when idle and reshapes per scene
    if "--spiralShow" in css and "spiralFade" in js and "spiralTarget" in js:
        ok("thread: idle fade + per-scene shape wired")
    else:
        bad("thread: idle fade or per-scene shape missing")
    # the closing frame is the door and one line: the thread unwinds and leaves
    if "closingRoom" in js and "openNow" in js and re.search(r"\* leaving|leaving\s*=", js):
        ok("thread: opens out and clears the closing scene")
    else:
        bad("thread: nothing makes it leave the closing scene")

    # 5. a throwing frame must fall back to the poster, not freeze the canvas
    if "falling back to the poster" in door and "broken" in door:
        ok("door: render failures fall back to the CSS poster")
    else:
        bad("door: no guard around the render loop")


def check_one_block_at_a_time():
    """Never two dense, unrelated blocks of text on the screen at once.

    A block leaves the screen once the next section's top edge is `space below`
    from the viewport top, and the next block arrives once that edge is one
    screen minus `space above` from it. So the two never share the screen only
    while space-below + space-above >= 100vh at every boundary, which is what
    the matching 50vh paddings below buy. They are the whole mechanism: drop
    any one of them and that pair starts double-booking the screen again.
    """
    css = read("styles.css")
    GAP = 50.0

    def vhs(pattern, label):
        m = re.search(pattern, css)
        if not m:
            bad(f"one-block-at-a-time: cannot find {label}")
            return []
        found = [float(v) for v in re.findall(r"([\d.]+)vh", m.group(1))]
        if not found:
            bad(f"one-block-at-a-time: {label} no longer carries a vh value")
        return found

    rules = [
        (r"\n\.scene\{[^}]*?padding:([^;]+);", "scene"),
        (r"\.hold__anchor\{[^}]*?padding-block:([^;]+);", "hold anchor"),
        (r"\.hold__stream\{[^}]*?padding-block:([^;]+);", "hold stream"),
        (r"\n\.footer\{[^}]*?padding:([^;]+);", "footer"),
        (r"\.scene\{[^}]*?min-height:auto;\s*padding-block:([^;]+);", "mobile scene"),
        (r"\.scene--hold\{\s*padding:([^;]+);", "mobile hold"),
        (r"\.scene--hold\{\s*padding-block:([^;]+);", "reduced-motion hold"),
    ]
    for pattern, label in rules:
        vals = vhs(pattern, label)
        if not vals:
            continue
        if min(vals) >= GAP:
            ok(f"{label}: keeps >= {GAP:g}vh of clear space either side")
        else:
            bad(f"{label}: only {min(vals):g}vh of clear space, under the "
                f"{GAP:g}vh that keeps it off the next section's screen")

    # the stream has to clear the screen before its own sticky phrase does,
    # or the phrase is left labelling a beat the reader can no longer see
    anchor = vhs(r"\.hold__anchor\{[^}]*?padding-block:([^;]+);", "hold anchor")
    stream = vhs(r"\.hold__stream\{[^}]*?padding-block:([^;]+);", "hold stream")
    if anchor and stream:
        if stream[-1] > anchor[-1]:
            ok(f"hold phrase outlives its beats ({stream[-1]:g}vh > {anchor[-1]:g}vh)")
        else:
            bad(f"hold stream's {stream[-1]:g}vh must exceed the anchor's "
                f"{anchor[-1]:g}vh, or the beats outlast their own phrase")


def check_vendored():
    """No CDN dependencies: privacy.html discloses only Google Fonts."""
    for f in ["assets/vendor/three.module.min.js", "assets/vendor/three.core.min.js",
              "assets/vendor/lenis.min.js", "assets/vendor/VERSIONS.txt"]:
        if (ROOT / f).is_file():
            ok(f"vendored: {f}")
        else:
            bad(f"vendored dependency missing: {f}")
    for page in PAGES:
        if not (ROOT / page).is_file():
            continue
        hosts = set(re.findall(r'(?:src|href)="https?://([^/"]+)', read(page)))
        allowed = {"fonts.googleapis.com", "fonts.gstatic.com", "supabase.com",
                   "resend.com", "www.nyc.gov", "nystateofhealth.ny.gov"}
        rogue = hosts - allowed
        if rogue:
            bad(f"{page}: unexpected third-party origin(s): {sorted(rogue)}")
        else:
            ok(f"{page}: no unexpected third-party origins")
    # three.module re-exports the core chunk; both must be vendored together
    mod = read("assets/vendor/three.module.min.js")
    for chunk in set(re.findall(r'from"\./([a-z0-9.]+\.js)"', mod)):
        if (ROOT / "assets/vendor" / chunk).is_file():
            ok(f"three.js chunk vendored: {chunk}")
        else:
            bad(f"three.js expects ./{chunk} which is not vendored")


# ------------------------------------------------------------------- budget
BUDGET = {"assets/land1.webp": 260, "assets/land2.webp": 260,
          "assets/land3.webp": 320, "assets/land4.webp": 260}


def check_asset_budget():
    for ref, limit_kb in BUDGET.items():
        f = ROOT / ref
        if not f.is_file():
            bad(f"budget: {ref} missing")
            continue
        kb = f.stat().st_size / 1024
        if kb <= limit_kb:
            ok(f"budget: {ref} {kb:.0f}KB <= {limit_kb}KB")
        else:
            bad(f"budget: {ref} is {kb:.0f}KB, over the {limit_kb}KB budget")
    shipped = sum((ROOT / r).stat().st_size for r in BUDGET if (ROOT / r).is_file())
    total_kb = shipped / 1024
    if total_kb <= 900:
        ok(f"budget: landscapes total {total_kb:.0f}KB")
    else:
        bad(f"budget: landscapes total {total_kb:.0f}KB, over 900KB")


# --------------------------------------------------------------------- a11y
def check_a11y_basics():
    src = read("index.html")
    if 'class="skip"' in src:
        ok("skip link present")
    else:
        bad("no skip link")
    if src.count("<h1") == 1:
        ok("exactly one h1")
    else:
        bad(f"expected 1 h1, found {src.count('<h1')}")
    if '<canvas class="spiral" id="spiral" aria-hidden="true">' in src and 'class="doorstage" aria-hidden="true"' in src:
        ok("decorative canvases are aria-hidden")
    else:
        bad("decorative canvases must be aria-hidden")
    if 'lang="en"' in src:
        ok("document language set")
    else:
        bad("missing lang attribute")
    for m in re.findall(r"<img\b[^>]*>", src):
        if "alt=" in m:
            ok("img has alt")
        else:
            bad(f"img without alt: {m[:60]}")


def check_nav_matches_sections():
    src = read("index.html")
    nav = re.findall(r'<nav class="nav__links".*?</nav>', src, flags=re.S)
    if not nav:
        bad("index.html: no primary nav block, so nav wiring cannot be checked")
        return
    targets = re.findall(r'href="#([^"]+)"', nav[0])
    ids = set(ID.findall(src))
    for t in targets:
        if t in ids:
            ok(f"nav link #{t} resolves")
        else:
            bad(f"nav link #{t} has no section")
    js = read("script.js")
    declared = re.search(r'var navSections = \[([^\]]+)\]', js)
    if declared:
        listed = re.findall(r'"([^"]+)"', declared.group(1))
        if listed == targets:
            ok(f"script.js nav sections match the markup: {listed}")
        else:
            bad(f"script.js tracks {listed} but the nav links to {targets}")
    else:
        bad("could not find navSections in script.js")

    # every page's nav must offer the same journey, in the same order
    for page in ["privacy.html", "terms.html"]:
        if not (ROOT / page).is_file():
            continue
        block = re.findall(r'<nav class="nav__links".*?</nav>', read(page), flags=re.S)
        if not block:
            bad(f"{page}: no primary nav")
            continue
        order = [a.split("#")[-1] for a in re.findall(r'href="index\.html#([^"]+)"', block[0])]
        if order == targets:
            ok(f"{page}: nav order matches the homepage")
        else:
            bad(f"{page}: nav order {order} does not match the homepage {targets}")


# --------------------------------------------------------------- the doors
# Three lines of prose at the 44ch measure the blurbs are capped to. Anything
# longer takes a fourth line, and a fourth line is the whole bug: the row that
# closes and the row that opens only cancel out while every blurb is the same
# height, and the moment one differs the column beside it starts moving under
# the pointer. 156 is the budget with a character of slack; the longest blurb
# written to it lands at 148.
BLURB_MAX = 156


def check_doors():
    """#work: four doors that open on click without moving what is above them."""
    src = read("index.html")
    css = read("styles.css")
    js = read("script.js")

    items = re.findall(r'<div class="ways__item">(.*?)\n        </div>', src, flags=re.S)
    if len(items) == 4:
        ok("doors: four of them")
    else:
        bad(f"doors: expected 4, found {len(items)}")

    # every row is a real button wired to the panel it discloses
    rows = re.findall(r'<button class="ways__row"[^>]*aria-controls="([^"]+)"', src)
    bodies = set(re.findall(r'<div class="ways__body" id="([^"]+)"', src))
    if len(rows) == len(bodies) == 4:
        ok("doors: four rows, four panels")
    else:
        bad(f"doors: {len(rows)} rows against {len(bodies)} panels")
    for target in rows:
        if target in bodies:
            ok(f"doors: {target} is disclosed by its own row")
        else:
            bad(f"doors: aria-controls={target!r} points at no panel")

    # no-JS has to leave the descriptions readable, so the markup must not claim
    # a collapsed state and the CSS default must be open. script.js owns both.
    section = strip_comments(src.split('id="work"', 1)[-1].split("</section>", 1)[0])
    if "aria-expanded" not in section:
        ok("doors: markup claims no collapsed state it cannot open")
    else:
        bad("doors: aria-expanded is hardcoded in the markup; with the script "
            "blocked that is a lie and the descriptions become unreachable")
    if re.search(r"\.ways__body\{[^}]*grid-template-rows:1fr", css) and \
       re.search(r"\.ways--js \.ways__body\{[^}]*grid-template-rows:0fr", css):
        ok("doors: panels default open, and only .ways--js closes them")
    else:
        bad("doors: the no-JS fallback is gone; a click-only disclosure that "
            "starts closed hides its content from anyone without the script")
    if re.search(r'classList\.add\([^)]*"ways--js"', js) and \
       'setAttribute("aria-expanded", "false")' in js:
        ok("doors: script.js closes the panels and says so in the same breath")
    else:
        bad("doors: script.js must add .ways--js and write aria-expanded together")

    # hover must not open anything: revealing prose on hover means it arrives
    # while the pointer is passing through and leaves as you move toward it
    for sel in [r"\.ways__item:hover \.ways__body", r"\.ways__item:hover \.ways__blurb"]:
        if re.search(sel, css):
            bad("doors: hover opens the description again; hover is the header "
                "breathing, the description is a click")
        else:
            ok(f"doors: hover does not trigger {sel.split(' ')[-1]}")

    # the equal-height contract, in the two places it actually lives
    blurbs = re.findall(r'<p class="ways__blurb">([^<]+)</p>', src)
    if len(blurbs) == 4:
        ok("doors: every row carries a blurb")
    else:
        bad(f"doors: {len(blurbs)} blurbs for 4 rows")
    for b in blurbs:
        if len(b) <= BLURB_MAX:
            ok(f"doors: blurb fits its three reserved lines ({len(b)} chars)")
        else:
            bad(f"doors: blurb is {len(b)} chars, over the {BLURB_MAX} that fit "
                f"three lines: {b[:48]!r}... a fourth line puts the wobble back")

    # anchored to the start of a line: ".ways__blurb{" also occurs inside
    # ".ways--boot .ways__blurb{", and matching that one reads the wrong body
    block = re.search(r"^\.ways__blurb\{(.*?)\}", css, flags=re.S | re.M)
    if not block:
        bad("doors: no .ways__blurb rule; the height reserve is gone")
        return
    body = block.group(1)
    if re.search(r"max-width:\s*\d+ch", body):
        ok("doors: the blurb measure is still capped in ch")
    else:
        bad("doors: .ways__blurb lost its ch cap, so line count depends on the "
            "viewport again and the blurbs stop matching around 1150px")
    if re.search(r"min-height:calc\(1\.62em \* 3", body):
        ok("doors: three lines still reserved whether the sentence fills them or not")
    else:
        bad("doors: .ways__blurb lost its three-line reserve; opening a row now "
            "changes the section's height")


def check_reel():
    """#bills: four lines of officialese that roll into what they mean."""
    src = read("index.html")
    css = read("styles.css")

    section = strip_comments(src.split('id="bills"', 1)[-1].split("</section>", 1)[0])
    # split into row blocks and read each one, rather than one regex spanning
    # the whole nested shape: a brittle mega-pattern reports "0 rows" for a
    # markup reflow that broke nothing
    parts = re.split(r'<div class="reel__row', section)[1:]
    rows = []
    for part in parts:
        at = re.search(r'style="--at:([.\d]+)"', part)
        n = re.search(r'<span class="reel__strip" style="--n:(\d+)">', part)
        strip = part.split('class="reel__strip"', 1)[-1].split("</span>\n            </span>", 1)[0]
        phrases = re.findall(r"<span[^>]*>([^<]+)</span>", strip)
        rows.append({"at": float(at.group(1)) if at else None,
                     "n": int(n.group(1)) if n else None,
                     "phrases": phrases,
                     "turn": part.startswith(" reel__row--turn")})
    if len(rows) == 4:
        ok("reel: four rows")
    else:
        bad(f"reel: expected 4 rows, found {len(rows)}")

    # thresholds have to climb, or two reels roll on top of each other
    ats = [r["at"] for r in rows if r["at"] is not None]
    if len(ats) == len(rows) and ats == sorted(ats) and len(set(ats)) == len(ats):
        ok(f"reel: rows land in order {ats}")
    else:
        bad(f"reel: --at values {ats} are not strictly increasing; rows will "
            f"roll over each other instead of in sequence")

    for r in rows:
        # a strip must declare the number of lines it actually has, or the roll
        # lands between two of them and the window shows half of each
        if r["n"] == len(r["phrases"]):
            ok(f"reel: --n:{r['n']} matches its {len(r['phrases'])} lines")
        else:
            bad(f"reel: a strip declares --n:{r['n']} but holds "
                f"{len(r['phrases'])} lines; the roll will stop between two of "
                f"them and show half of each")

    # The row must not resize as it rolls. The reference buys that with a hidden
    # sizer because its reel is inline; this one buys it structurally, and these
    # two declarations ARE the guarantee — make the window inline-block or the
    # strip static and the width starts following whichever phrase is showing.
    win = re.search(r"\.reel__win\{(.*?)\}", css, flags=re.S)
    strip = re.search(r"\.reel__strip\{(.*?)\}", css, flags=re.S)
    if win and "display:block" in win.group(1):
        ok("reel: the window is a block, so its width is the column's")
    else:
        bad("reel: .reel__win is no longer display:block; its width will follow "
            "whichever phrase is showing and the row will resize mid-roll")
    # --line is shared by the window and by spans set at .62em. A custom
    # property is re-resolved per element, so an em value means one thing on
    # the window and a smaller thing on the officialese lines: the steps and
    # the window height stop agreeing and the roll walks off the strip. This
    # one shipped broken until the render showed two phrases in the window.
    if win:
        m = re.search(r"--line:([^;]+);", win.group(1))
        if not m:
            bad("reel: .reel__win no longer declares --line, which is the step "
                "size for the roll and the height of the window at once")
        elif "em" in m.group(1).replace("rem", ""):   # rem is fine, em is not
            bad(f"reel: --line is {m.group(1).strip()!r} — an em basis is "
                f"re-resolved on every span, so the strip's steps and the "
                f"window's height stop agreeing and the roll overshoots")
        else:
            ok("reel: --line has one basis, so steps and window height agree")
    if strip and "position:absolute" in strip.group(1):
        ok("reel: the strip is out of flow, so it cannot size the window")
    else:
        bad("reel: .reel__strip left the flow; the longest phrase in it now sets "
            "the row width")

    # Both released states must render the reel landed. The pin only exists
    # above 900px and outside reduced motion; everywhere else --t never moves,
    # so a reel left at --k:0 shows four lines of officialese and the section
    # argues against itself. Missed the narrow one once already.
    for query, label in [(r"@media \(max-width:900px\)", "narrow"),
                         (r"@media \(prefers-reduced-motion:reduce\)", "reduced motion")]:
        # styles.css carries several blocks per query, so check them all
        blocks = re.findall(query + r"\{(.*?)\n\}", css, flags=re.S)
        if any(re.search(r"\.reel__row\{[^}]*--k:1", b) for b in blocks):
            ok(f"reel: lands on the plain meaning when the pin is released ({label})")
        else:
            bad(f"reel: {label} releases the pin but leaves --k at 0, so the reel "
                f"shows officialese nobody can scroll past")

    # the payoff: the last row has to turn, and it is the only gold on the artwork
    if "You are allowed to argue" in section:
        ok("reel: the last row lands on the door, not on more officialese")
    else:
        bad("reel: the turn is gone; the section exists to end somewhere useful")
    if re.search(r"\.reel__row--turn \.reel__plain\{[^}]*var\(--gold\)", css):
        ok("reel: gold is spent on the turn")
    else:
        bad("reel: the turn is no longer gold, which is the one signal that the "
            "last line is different from the three above it")

    # illustration, not content
    if re.search(r'<div class="reel" aria-hidden="true">', src):
        ok("reel: the artwork is hidden from assistive tech")
    else:
        bad('reel: .reel must carry aria-hidden="true"; a screen reader reading '
            'every officialese phrase the reel passes learns nothing')

    # state is a pure function of --t, so no parked frame is undressed
    if re.search(r"--k:clamp\(0, calc\(\(var\(--t,0\) - var\(--at\)\)", css):
        ok("reel: every row's position is a pure function of --t")
    else:
        bad("reel: rows no longer derive --k from --t; a parked scroll can land "
            "on a frame nothing has composed")
    # feather while moving, crisp when still
    if re.search(r"--feather:min\(", css) and re.search(r"mask-image:linear-gradient\(180deg, transparent 0,", css):
        ok("reel: the window feathers while rolling and goes crisp when landed")
    else:
        bad("reel: the feather mask is gone; the reel now clips its phrases with "
            "a hard edge top and bottom while it rolls")

    # the line masks: the three details that make or break the reveal
    mask = re.search(r"\.pin__line > span\{(.*?)\}", css, flags=re.S)
    inner = re.search(r"\.pin__line > span > span\{(.*?)\}", css, flags=re.S)
    if mask and "overflow:clip" in mask.group(1):
        ok("line masks: overflow:clip, so the mask cannot become a scroll container")
    else:
        bad("line masks: .pin__line > span must use overflow:clip, not hidden")
    if mask and "padding-bottom:var(--desc)" in mask.group(1) \
            and "margin-bottom:calc(var(--desc) * -1)" in mask.group(1):
        ok("line masks: descenders have room, and the line box still measures the same")
    else:
        bad("line masks: the descender allowance is gone; g, y and p will shear")
    if inner and "translateY(calc(100% + var(--desc)))" in inner.group(1):
        ok("line masks: the parked line clears the descender allowance too")
    else:
        bad("line masks: parking at plain 100% leaves the glyph tops showing "
            "through the descender padding")


def check_audience_order():
    """Two audiences, two labelled chapters, and the nav walks them in order.

    Students come first because a student has to be convinced and a partner
    arrives already knowing what they want. The nav, the footer's journey
    column, script.js's tracker and the page itself all have to agree on that
    order — four places, edited by hand, and nothing visibly breaks when one of
    them drifts.
    """
    src = read("index.html")

    # nav targets must appear in the page in the same order they appear in the nav
    nav = re.search(r'<nav class="nav__links".*?</nav>', src, flags=re.S)
    targets = re.findall(r'href="#([^"]+)"', nav.group(0)) if nav else []
    where = [src.index(f'id="{t}"') for t in targets if f'id="{t}"' in src]
    if len(where) == len(targets) and where == sorted(where):
        ok(f"audience: the nav walks the page in order {targets}")
    else:
        bad(f"audience: the nav order {targets} does not match the page order. "
            f"A visitor clicking down the nav would jump backwards.")

    # students before partners, as chapters
    st, pa = src.find('id="students"'), src.find('id="partners"')
    if -1 < st < pa:
        ok("audience: the student chapter precedes the partner chapter")
    else:
        bad("audience: the partner chapter is no longer last. Everything "
            "addressed to organisations sits after everything addressed to "
            "volunteers, so a student never has to scroll past a partner pitch.")

    # each chapter announces itself
    for anchor_id, label in [("students", "For students"), ("partners", "For partners")]:
        block = src.split(f'id="{anchor_id}"', 1)[-1].split("</section>", 1)[0]
        if f'<span class="eyebrow">{label}</span>' in block:
            ok(f"audience: the {anchor_id} chapter is labelled {label!r}")
        else:
            bad(f"audience: the {anchor_id} chapter lost its {label!r} label. The "
                f"two audiences are only distinguishable if each one says who it "
                f"is talking to.")

    # the partner anchor has to sit on the chapter's first scene, or the nav
    # lands one scene past the label it was supposed to introduce
    if re.search(r'<section class="scene scene--hold scene--reach" id="partners">', src):
        ok("audience: #partners anchors the top of its chapter")
    else:
        bad("audience: #partners moved off the chapter's opening scene, so the "
            "nav skips the label that introduces it")


def check_mobile_budget():
    """Below 900px a phone must not be asked to re-raster the desktop page.

    None of this is layout. It is measured compositing cost: the script tick
    runs at 0.03ms, so the jank was never script — it was six stacked
    full-screen layers, four scaling background images, a blend mode and an
    animated blur, all of which a desktop GPU absorbs and a phone does not.
    Every rule below removes one full-screen layer from the per-frame budget,
    and every one of them is the kind of thing a later edit deletes without
    noticing, because nothing looks wrong on a laptop when it comes back.
    """
    css = read("styles.css")
    js = read("script.js")
    blocks = re.findall(r"@media \(max-width:900px\)\{(.*?)\n\}", css, flags=re.S)
    narrow = "\n".join(blocks)

    for pattern, label, why in [
        (r"\.stage__grain\{[^}]*display:none", "the grain layer is dropped",
         "a mix-blend-mode on a fixed full-screen layer makes the compositor read "
         "back the whole backdrop every frame, for 5% noise nobody can see at 375px"),
        (r"\.stage__layer\{[^}]*will-change:opacity", "the backdrop promises opacity only",
         "will-change:transform pins a compositing layer for a property that no "
         "longer animates here"),
        (r"\.hero__ui\{[^}]*filter:none", "the hero blur is off",
         "a scrubbed blur re-rasters the whole hero every frame, across the 190vh "
         "the hero is tall on a phone"),
    ]:
        if re.search(pattern, narrow):
            ok(f"mobile: {label}")
        else:
            bad(f"mobile: {label} — gone. {why}.")

    # the two script-side halves of the same budget
    if re.search(r"var zoom = !narrow\.matches", js):
        ok("mobile: journey() stops writing transform to the backdrop")
    else:
        bad("mobile: journey() writes a scale to four full-screen background "
            "layers every frame again; that re-raster is the single biggest "
            "cost on a phone")
    if re.search(r"if \(narrow\.matches\) \{\s*if \(spiral\.width\)", js):
        ok("mobile: the hidden spiral canvas allocates nothing")
    else:
        bad("mobile: sresize() allocates a device-pixel-ratio backing store for a "
            "display:none canvas again — megabytes of GPU memory and a "
            "full-surface clear every frame for something nobody can see")
    if 'classList.toggle("door-gone"' in js and re.search(r"\.door-gone \.doorstage\{[^}]*visibility:hidden", css):
        ok("mobile: the door stops compositing once it has handed over")
    else:
        bad("mobile: the doorstage is back to opacity:0 alone, which keeps a "
            "full-screen WebGL layer alive in the compositor for the whole page")

    # the menu button measured 30x22 — under even the 24px WCAG 2.5.8 minimum
    if re.search(r"\.nav__tog::after[^{]*\{[^}]*inset:-13px", narrow):
        ok("mobile: the menu button's hit area is widened past its glyph")
    else:
        bad("mobile: .nav__tog is back to a 30x22 hit area — the primary "
            "navigation control on a phone, under the WCAG 2.5.8 minimum")


def check_vow():
    """The statement: short version visible, full version one tap away."""
    src = read("index.html")
    section = strip_comments(src.split("scene--vow", 1)[-1].split("</section>", 1)[0])

    # The full wording now sits inside a disclosure. That is only acceptable
    # while the visible line still does the job on its own — it is the sentence
    # that stops somebody mistaking a student for a professional, and it cannot
    # be behind a tap. Trim it further and this fires.
    short = re.search(r'<p class="vow">(.*?)</p>', section, flags=re.S)
    if not short:
        bad("vow: no visible short statement; the whole point of collapsing the "
            "full text is that a shorter one stays on screen")
    else:
        text = strip_tags(short.group(1))
        for must, why in [("trained student volunteers", "who we are"),
                          ("not doctors", "what we are not"),
                          ("never charge", "that nobody pays us")]:
            if must in text:
                ok(f"vow: the visible line still says {why}")
            else:
                bad(f"vow: the visible line no longer says {why} ({must!r}). "
                    f"With the full statement collapsed, this line is the only "
                    f"thing a frightened person reads before deciding to trust us.")

    # It has to open with no script. This is the one disclosure on the site
    # where a JS failure would hide a safety statement rather than a nicety.
    if re.search(r'<details class="vow__more">', section):
        ok("vow: the full statement is native <details>, so it opens with no JS")
    else:
        bad("vow: the full statement is no longer in a <details>. A scripted "
            "disclosure hides it entirely when the script fails, and this is the "
            "one piece of copy that must never be unreachable.")
    body = section.split("<details", 1)[-1]
    if "We are trained student volunteers." in body:
        ok("vow: the verbatim statement is inside the disclosure")
    else:
        bad("vow: the verbatim statement is not inside the <details>")


def check_lane():
    """The line: a hold scene of beats, each stating its own boundary."""
    src = read("index.html")
    css = read("styles.css")
    section = strip_comments(src.split('scene--lane', 1)[-1].split("</section>", 1)[0])

    beats = re.findall(r'<p class="beat focus-in"><b>([^<]+)</b>\s*([^<]+)</p>', section)
    if len(beats) == 5:
        ok("lane: five beats")
    else:
        bad(f"lane: expected 5 beats, found {len(beats)}. This section has been a "
            f"checklist, a ten-row register and a set of indented pairs; each "
            f"failed by giving the reader a shape to decode instead of prose.")

    for lead, body in beats:
        if lead.endswith("."):
            ok(f"lane: run-in lead {lead[:32]!r}")
        else:
            bad(f"lane: beat lead {lead!r} is not a sentence; .beat is a run-in "
                f"lead and prose, never a heading over a list")
        # the section's entire job: every beat has to carry its own boundary,
        # because nothing is drawn to mark one any more
        if re.search(r"\b(?:never|no|cannot|until)\b", body, re.I):
            ok(f"lane: {lead[:26]!r} states its own boundary")
        else:
            bad(f"lane: the beat under {lead!r} states no boundary. With no rule "
                f"and no columns, the prose is the only place the line exists.")

    # every shape this section was cut down from, kept out
    for pat, why in [(r"\u2713|\u2714", "a tick"), (r"\u2715|\u2717|\u2718", "a cross"),
                     (r"counter-increment:\s*lane", "a numbered register"),
                     (r"\.lane__", "bespoke lane styling")]:
        if re.search(pat, css) or re.search(pat, section):
            bad(f"lane: {why} is back. The section is .beat and nothing else — "
                f"the same component the reach and partners scenes use.")
            break
    else:
        ok("lane: no ticks, no numbering, no bespoke styling")

    # organisation: the phrase holds while the beats move past it. This is also
    # what keeps the page's own thread out of the type, since spiralTarget puts
    # a hold scene's thread down the gutter between its two columns.
    head = src.split('scene--lane', 1)[0][-300:]
    if "scene--hold" in head and "scene--hold-r" in head:
        ok("lane: organised as a hold scene, phrase right and beats left")
    else:
        bad("lane: the section is no longer a scene--hold; the phrase scrolls "
            "away from the statements it introduces, and its thread falls back "
            "to the pin rule that runs down the middle of the type")
    if "data-pin" not in head:
        ok("lane: no longer a pin, so nothing scrubs a heading off its own beats")
    else:
        bad("lane: data-pin is back on the line section")


def main():
    for fn in [check_pages_exist, check_links, check_cross_page_anchors, check_stage_layers,
               check_honesty_statement, check_forbidden, check_no_invented_numbers,
               check_billing_boundaries, check_forms, check_labels, check_door,
               check_transition_invariants, check_reel, check_audience_order, check_mobile_budget, check_vow, check_lane, check_doors,
               check_one_block_at_a_time, check_vendored,
               check_asset_budget, check_a11y_basics, check_nav_matches_sections]:
        try:
            fn()
        except Missing as e:
            bad(f"{fn.__name__}: skipped, {e} is missing")

    if VERBOSE:
        for p in passes:
            print(f"  ok   {p}")
    print(f"\n{len(passes)} passed, {len(failures)} failed")
    for f in failures:
        print(f"  FAIL {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
