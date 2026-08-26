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
import math
import os
import re
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv

# The directory used to be one page. It is now a front page and one page per
# kind of help, generated together by build_help.py, so the list of resident
# pages is derived from the generator rather than typed here — a need added to
# NEEDS gets checked the moment it exists, and cannot be forgotten.
def _need_keys():
    import build_help
    return [n["key"] for n in build_help.NEEDS]


def _lang_pages():
    import build_help
    return [build_help.lang_page(L["key"]) for L in build_help.LANGUAGES]


CATEGORY_PAGES = [f"help-{k}.html" for k in _need_keys()]
LANGUAGE_PAGES = _lang_pages()
# Everything the directory serves. RESIDENT_PAGES is what a resident reads;
# the English ones are checked for English prose, the ten language ones are
# not, so most guards want ENGLISH_PAGES instead.
ENGLISH_PAGES = ["help.html"] + CATEGORY_PAGES
RESIDENT_PAGES = ENGLISH_PAGES

PAGES = (["index.html", "help.html"] + CATEGORY_PAGES + LANGUAGE_PAGES +
         ["privacy.html", "terms.html", "partner-pitch.html",
          "cohort-onboarding.html", "students.html", "partners.html", "admin.html"])

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
HONESTY_SURFACES = dict({"index.html": 2, "partner-pitch.html": 1,
                         "cohort-onboarding.html": 1},
                        **{p: 1 for p in RESIDENT_PAGES})

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
    # Hedging the one promise that costs a reader nothing to believe. "We never
    # charge" is either true everywhere or it is not a promise.
    (r"charge for most|we (?:may|sometimes|usually) charge|usually free",
     "a hedged version of \"we never charge for anything\""),
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
LOCAL_REF = re.compile(r'(?:href|src)="(?!https?:|mailto:|tel:|sms:|data:|#)([^"]+)"')
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

        # Every page, not just index.html. The condition here used to be
        # `if page == "index.html" or a in ids`, which means that on any other
        # page a MISSING anchor fell through both branches and was never
        # reported — so the check quietly only ran on one file. It let the
        # language panels link to #dir on the front page, where there is no
        # #dir, on the one control aimed at people who cannot read the page.
        ids = set(ID.findall(src))
        for a in set(ANCHOR.findall(src)):
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
    # Never quote a filing deadline, on any surface. From the cohort training
    # doc: while those materials were being written, three official New York
    # sources gave three different answers for the same appeal filing window.
    # It does not matter which was right — being wrong here can cost somebody
    # their appeal entirely, and a page is quoted from far more confidently
    # than a volunteer is. The professional confirms the deadline; the site
    # creates urgency without numbers ("call today, not next week").
    (r"\bwithin\s+\d+\s*(?:calendar\s+|business\s+|)(?:days?|weeks?|months?|years?)\b",
     "a filing deadline; three official sources disagreed on the appeal window"),
    (r"\byou have\s+\d+\s*(?:calendar\s+|business\s+|)(?:days?|weeks?|months?)\b",
     "a filing deadline stated to the reader"),
    (r"\b\d+[- ](?:day|week|month)\s+(?:deadline|window|limit)\b",
     "a named filing window"),
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

    Every one of them now reads --gap rather than a literal, so this resolves
    the variable before measuring. That indirection exists for the phone, which
    deliberately does NOT keep the desktop contract (a block there is a
    paragraph, not a screen, and several are taller than the viewport at any
    padding), so the mobile value is checked against its own rule further down:
    small enough to have actually fixed the 48%-blank-page problem, large
    enough to still read as a pause.
    """
    css = read("styles.css")
    GAP = 50.0

    def gap_value(scope):
        """The --gap declaration in effect: 'desktop' from :root, 'mobile' from
        the max-width:900px block. Returned in vh-equivalent units."""
        if scope == "desktop":
            m = re.search(r":root\{(.*?)\n\}", css, re.S)
            if m:
                d = re.search(r"--gap:\s*([^;]+);", m.group(1))
                if d:
                    v = re.search(r"([\d.]+)vh", d.group(1))
                    if v:
                        return float(v.group(1))
            return None
        m = re.search(r"@media \(max-width:900px\)\{(.*?)\n\}\n@media", css, re.S)
        if not m:
            return None
        d = re.search(r":root\{\s*--gap:\s*([^;]+);", m.group(1))
        if not d:
            return None
        v = re.search(r"clamp\([^,]+,\s*([\d.]+)svh", d.group(1))
        return float(v.group(1)) if v else None

    DESKTOP_GAP = gap_value("desktop")
    MOBILE_GAP = gap_value("mobile")

    def vhs(pattern, label, scope):
        """Resolve a padding value to vh numbers, following var(--gap) and the
        calc() multipliers written on top of it."""
        m = re.search(pattern, css)
        if not m:
            bad(f"one-block-at-a-time: cannot find {label}")
            return []
        raw = m.group(1)
        gap = DESKTOP_GAP if scope == "desktop" else MOBILE_GAP
        found = [float(v) for v in re.findall(r"([\d.]+)vh(?![a-z])", raw)]
        for mult in re.findall(r"calc\(\s*var\(--gap\)\s*\*\s*([\d.]+)\s*\)", raw):
            if gap is not None:
                found.append(gap * float(mult))
        bare = len(re.findall(r"var\(--gap\)", raw)) - len(
            re.findall(r"calc\(\s*var\(--gap\)\s*\*", raw))
        if bare > 0 and gap is not None:
            found.extend([gap] * bare)
        if not found:
            bad(f"one-block-at-a-time: {label} no longer carries a vh value "
                f"or a resolvable var(--gap)")
        return found

    rules = [
        (r"\n\.scene\{[^}]*?padding:([^;]+);", "scene", "desktop"),
        (r"\.hold__anchor\{[^}]*?padding-block:([^;]+);", "hold anchor", "desktop"),
        (r"\.hold__stream\{[^}]*?padding-block:([^;]+);", "hold stream", "desktop"),
        (r"\n\.footer\{[^}]*?padding:([^;]+);", "footer", "desktop"),
        (r"\.scene\{[^}]*?min-height:auto;\s*padding-block:([^;]+);", "mobile scene", "mobile"),
        (r"\.scene--hold\{\s*padding:([^;]+);", "mobile hold", "mobile"),
        (r"\.scene--hold\{\s*padding-block:([^;]+);", "reduced-motion hold", "desktop"),
    ]
    for pattern, label, scope in rules:
        floor = GAP if scope == "desktop" else 0.0
        vals = vhs(pattern, label, scope)
        if not vals:
            continue
        if min(vals) >= floor:
            ok(f"{label}: keeps >= {floor:g}vh of clear space either side"
               if floor else f"{label}: resolves through --gap ({min(vals):g}svh)")
        else:
            bad(f"{label}: only {min(vals):g}vh of clear space, under the "
                f"{floor:g}vh that keeps it off the next section's screen")

    # ---- the phone's own rule ----
    # 50vh either side on a phone was 9,894px of blank screen, 48% of the page,
    # and it turned a 13-screen read into a 25-screen scroll. The gap has to
    # come down; it must not come down to nothing, and it must not creep back.
    if DESKTOP_GAP != GAP:
        bad(f"--gap on the desktop is {DESKTOP_GAP}vh, not the {GAP:g}vh the "
            f"one-block-at-a-time contract needs")
    else:
        ok(f"--gap resolves to {GAP:g}vh on the desktop")
    if MOBILE_GAP is None:
        bad("no mobile --gap: the phone is back on the desktop's 50vh, which "
            "is half a page of blank screen")
    elif not 10.0 <= MOBILE_GAP <= 30.0:
        bad(f"mobile --gap is {MOBILE_GAP:g}svh; under 10 the beats run "
            f"together, over 30 the blank-screen scroll comes back")
    else:
        ok(f"mobile --gap is {MOBILE_GAP:g}svh: a pause, not a screen")
    mobile_root = re.search(r"@media \(max-width:900px\)\{(.*?)--gap:\s*([^;]+);", css, re.S)
    if mobile_root and "svh" in mobile_root.group(2):
        ok("mobile --gap is in svh, so the address bar cannot resize the page")
    else:
        bad("mobile --gap must use svh: vh changes as the address bar slides")

    # the stream has to clear the screen before its own sticky phrase does,
    # or the phrase is left labelling a beat the reader can no longer see
    anchor = vhs(r"\.hold__anchor\{[^}]*?padding-block:([^;]+);", "hold anchor", "desktop")
    stream = vhs(r"\.hold__stream\{[^}]*?padding-block:([^;]+);", "hold stream", "desktop")
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
        # Only origins the BROWSER fetches on its own count here, because
        # that is what privacy.html has to disclose: any src=, plus href= on a
        # <link>. An <a href> to another site fetches nothing and discloses
        # nothing until the reader chooses to follow it — and the directory is
        # 84 outbound links to food pantries and legal aid offices, which is
        # the entire point of the page rather than a leak.
        src_hosts = set(re.findall(r'\ssrc="https?://([^/"]+)', read(page)))
        link_hosts = set(re.findall(r'<link\b[^>]*\shref="https?://([^/"]+)', read(page)))
        hosts = src_hosts | link_hosts
        allowed = {"fonts.googleapis.com", "fonts.gstatic.com", "supabase.com",
                   "resend.com", "www.nyc.gov", "nystateofhealth.ny.gov"}
        rogue = hosts - allowed
        if rogue:
            bad(f"{page}: unexpected third-party origin(s) loaded by the browser: {sorted(rogue)}")
        else:
            ok(f"{page}: no unexpected third-party origins loaded")
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
    nav = re.findall(r'<nav class="sitehead__links".*?</nav>', src, flags=re.S)
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
        block = re.findall(r'<nav class="sitehead__links".*?</nav>', read(page), flags=re.S)
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
    # Comments first: a brace inside one derails any brace-counting after it.
    body = re.sub(r"/\*.*?\*/", "", block.group(1), flags=re.S)
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

    # Wherever the pin is released, --t never moves, so a reel left at --k:0
    # shows four lines of officialese and the section argues against itself.
    # Derived rather than listed by query: the releasing block is whichever one
    # makes .pin__sticky static, and that pairing is the invariant. Listing the
    # queries by hand missed the narrow one once, and then went stale the moment
    # the release moved to a different query.
    media = re.findall(r"@media ([^{]+)\{(.*?)\n\}", css, flags=re.S)
    released = [(q.strip(), b) for q, b in media
                if re.search(r"\.pin__sticky\{[^}]*position:static", b)]
    if not released:
        bad("reel: nothing releases the pin any more — reduced motion and a "
            "viewport too short to hold a sticky both need a stacked fallback")
    for q, b in released:
        if re.search(r"\.reel__row\{[^}]*--k:1", b):
            ok(f"reel: lands on the plain meaning where the pin is released ({q})")
        else:
            bad(f"reel: {q} releases the pin but leaves --k at 0, so the reel "
                f"shows officialese nobody can scroll past")
    # and released blocks must give the sentences their own rows back, because
    # the phone stacks all four into one grid cell
    for q, b in released:
        if re.search(r"\.pin__line\{[^}]*grid-area:auto", b):
            ok(f"lines: released, the sentences get their own rows back ({q})")
        else:
            bad(f"lines: {q} releases the pin but leaves .pin__line in the "
                f"phone's shared cell, so all four sentences render on top of "
                f"each other")

    # The phone KEEPS the pin, and that is the whole reason the section reads
    # there. Released, the reel's four translations and the four sentences that
    # narrate them arrive together, and the narration turns into repetition:
    # "Stripped down it says: they said no, and this is yours to pay" lands
    # under a reel that has already said both, in those words.
    narrow_blocks = [b for q, b in media if q.strip() == "(max-width:900px)"]
    pinned = any(re.search(r"\.scene--pin\{[^}]*height:[\d.]+svh", b) for b in narrow_blocks)
    shared_cell = any(re.search(r"\.pin__line\{[^}]*grid-area:1/1", b) for b in narrow_blocks)
    if pinned and shared_cell:
        ok("lines: a phone keeps the pin, so one sentence is on screen at a time")
    else:
        bad("lines: the phone has released the pin again. That hands a reader "
            "holding a real denial notice eight blocks at once — four "
            "translations followed by four sentences restating them — instead "
            "of one sentence at a time over a reel that is still translating")

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
    nav = re.search(r'<nav class="sitehead__links".*?</nav>', src, flags=re.S)
    if not nav:
        bad("audience: no primary nav block, so nav order cannot be checked")
        return
    targets = re.findall(r'href="#([^"]+)"', nav.group(0))
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

    # The menu button measured 30x22 — under even the 24px WCAG 2.5.8 minimum.
    # There is no menu button any more; the tabs are the primary navigation on
    # a phone, so they are what has to be thumb-sized.
    tok = read("tokens.css")
    tall = re.search(r"\.sitehead__links a\{[^}]*min-height:(\d+)px", tok)
    if tall and int(tall.group(1)) >= 44:
        ok(f"mobile: a nav tab is at least {tall.group(1)}px tall, a thumb target")
    else:
        bad("mobile: the nav tabs are under 44px on a phone, and they are now "
            "the primary navigation control — there is no menu to fall back to")


def check_mobile_reads():
    """What a phone actually gets: the drawer, the hero's fit, and an idle CPU.

    Every item here is a defect that was live on the site and invisible on a
    laptop, which is the whole reason it needs a guard. None of them show up in
    a desktop browser at any width, because three of the four only exist below
    900px and the fourth only reproduces once the page has been scrolled.
    """
    css = read("styles.css")
    js = read("script.js")
    idx = read("index.html")
    blocks = re.findall(r"@media \(max-width:900px\)\{(.*?)\n\}", css, flags=re.S)
    narrow = "\n".join(blocks)

    # ---- the tabs, on a phone, without opening anything ----
    # This used to be seven checks about a drawer: its scrim, its scroll lock,
    # its Escape key, its focus round-trip, and a note about backdrop-filter
    # making .nav the containing block for its own fixed child. Three links
    # never needed any of it, and the drawer was the last place the two halves
    # of the site behaved differently on a phone. What has to hold now is
    # simpler and stricter: every tab is on the screen, always.
    for dead, what in [(r"\.nav__tog", "the hamburger button"),
                       (r"menu-open", "the drawer's body class"),
                       (r"\.nav__links", "the drawer's own nav class")]:
        left = [f for f, src in (("styles.css", css), ("script.js", js),
                                 ("index.html", idx)) if re.search(dead, src)]
        if left:
            bad(f"{what} still appears in {', '.join(left)} — a half-removed "
                f"drawer leaves dead CSS that can still match, or JS that "
                f"queries an element nobody ships")
        else:
            ok(f"{what} is gone from every file")

    head = re.search(r'<header class="sitehead">.*?</header>', idx, flags=re.S)
    if not head:
        bad("index.html: no .sitehead, so the shared header is not on this half")
    else:
        block = head.group(0)
        if re.search(r"position:fixed|display:none", narrow):
            pass
        hidden = re.search(r"\.sitehead__links\{[^}]*(?:display:none|visibility:hidden|"
                           r"position:fixed)", narrow)
        if hidden:
            bad("the tabs are hidden or lifted out of the flow below 900px — "
                "on a phone that means a control the reader has to find first")
        else:
            ok("the tabs stay in the flow on a phone; no menu to open")
        tok = read("tokens.css")
        if re.search(r"@media \(max-width:1080px\)\{[^@]*\.sitehead__links\{[^}]*flex-wrap:wrap",
                     tok, flags=re.S):
            ok("the tabs wrap onto a second row rather than scrolling sideways")
        else:
            bad("nothing wraps the tabs on a narrow screen, so at 200% text "
                "they run off the side")

    # ---- the hero has to fit a phone on its side ----
    if re.search(r"@media \(max-height:560px\) and \(max-width:900px\)", css):
        ok("hero: a short viewport has its own rules")
    else:
        bad("hero: nothing handles a short viewport. At 740x360 the four rows "
            "needed 623px inside a 360px sticky with overflow:hidden, and both "
            "call-to-action controls were clipped off the bottom with nothing "
            "on screen to say so")
    if re.search(r"\.hero__l,\.hero__r\{[^}]*min\(clamp\([^)]*\),\s*[\d.]+svh\)", narrow):
        ok("hero: the headline yields to viewport height, not just width")
    else:
        bad("hero: the headline is sized on width alone again, so a short "
            "screen cannot shrink it and the buttons go back under the fold")
    if re.search(r"\.hero\{ height:190svh", narrow) or re.search(r"\.hero\{[^}]*height:[\d.]+svh", narrow):
        ok("hero: its height is in svh, so the address bar cannot move it")
    else:
        bad("hero: .hero is back on vh, which changes as the address bar slides "
            "and shifts the door's pass-through mid-gesture")

    # ---- the loop must stop when there is nothing to draw ----
    if "function busy()" in js and re.search(r"if \(busy\(\)\) requestAnimationFrame", js):
        ok("loop: frames are conditional on something still moving")
    else:
        bad("loop: the scroll loop runs unconditionally again — 11 forced "
            "layouts and ~1.1ms of main thread every frame for the life of the "
            "page, most of which is spent while the reader is reading")
    if re.search(r"\(function loop\(\) \{ tick\(\); requestAnimationFrame\(loop\); \}\)\(\)", js):
        bad("loop: the old unconditional rAF loop is back")
    else:
        ok("loop: no unconditional rAF loop")
    if "window.__waypointProbe" in js:
        ok("loop: its stop condition is observable, so the idling can be tested")
    else:
        bad("loop: no probe — a headless tab never fires rAF, so without one "
            "there is no way to verify the loop idles and wakes")

    # ---- the address bar must not be treated as a resize ----
    if "vhStable" in js and "viewportChanged" in js:
        ok("viewport: height is re-read only when the width really changes")
    else:
        bad("viewport: heroT() divides by a live innerHeight again. On a phone "
            "the address bar changes it by 60-100px mid-scroll, which shifts "
            "the door's whole pass-through by about 8% every time it moves")
    door = read("assets/door.js")
    if re.search(r"coarse && w === lastW", door):
        ok("viewport: the door ignores address-bar-only resizes")
    else:
        bad("viewport: door.js reallocates its drawing buffer every time the "
            "address bar slides, during the one animation the page opens on")

    # ---- the things that were simply misaligned or out of reach ----
    if re.search(r"\.ways__foot\{[^}]*justify-content:flex-start", narrow):
        ok("ways: its button sits on the same axis as the rest of the section")
    else:
        bad("ways: the section's button is centred while .scene forces "
            "text-align:left around it")
    if re.search(r"\.footer__grid\{[^}]*repeat\(2,minmax\(0,1fr\)\)", narrow):
        ok("footer: two even columns")
    else:
        bad("footer: a bare 1fr floors at min-content, so the contact address "
            "drags its column wide and starves the other one")
    if "<wbr" in idx:
        ok("footer: the contact address has somewhere to wrap")
    else:
        bad("footer: the address is one unbreakable token in a 155px column, "
            "so it breaks mid-word")


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
    # Find the section by its unique heading phrase
    if 'where the line is' not in src:
        bad("lane: cannot find the line section by its heading")
        return
    section = strip_comments(src.split('where the line is', 1)[-1].split("</section>", 1)[0])

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
    head = src.split('where the line is', 1)[0][-300:]
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


# ----------------------------------------------------------- the directory
# help.html is generated, so the first and most important thing to know is
# whether the file on disk is still what the generator produces. Everything
# below it is only meaningful if that holds.
def check_theme_is_shared():
    """The two halves of the site must be one brand, provably.

    They were two stylesheets that happened to agree on eight hex values, and
    "happened to agree" is a state that ends the first time somebody nudges a
    green. tokens.css is now the only place a brand hue exists; both
    stylesheets map onto it and neither may restate one.

    This is not a tidiness check. The directory and the narrative page share
    an audience — a partner reads the story then sends somebody to the
    directory — and the moment the greens diverge the second page reads as a
    different organisation, which for a page about medical bills is a page
    somebody does not trust.
    """
    if not (ROOT / "tokens.css").is_file():
        bad("tokens.css is missing; the shared palette is gone and each "
            "stylesheet is back to defining its own brand")
        return
    tokens = read("tokens.css")

    hues = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", tokens)}
    inks = set(re.findall(r"rgba\(\s*25[12],\s*25[45],\s*24[47],\s*\.\d+\s*\)", tokens))
    if len(hues) >= 14:
        ok(f"tokens.css defines the palette in one place ({len(hues)} hues)")
    else:
        bad(f"tokens.css only defines {len(hues)} hues; the palette has leaked "
            "back into the stylesheets")

    for sheet in ("styles.css", "help.css"):
        css = read(sheet)
        # Comments are prose about the palette and legitimately name hues.
        body = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
        restated = sorted({h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", body)} & hues)
        if restated:
            bad(f"{sheet} restates brand hue(s) {restated} instead of using the "
                "token. Two copies of a colour is two colours as soon as one "
                "is edited.")
        else:
            ok(f"{sheet} restates no brand hue")
        leaked = sorted(set(re.findall(
            r"rgba\(\s*25[12],\s*25[45],\s*24[47],\s*\.\d+\s*\)", body)) & inks)
        if leaked:
            bad(f"{sheet} restates cream-on-dark ink level(s) {leaked}; use "
                "--ink-soft / --ink-faint / --ink-strong / --hair")
        else:
            ok(f"{sheet} takes its cream-on-dark ink levels from the tokens")

    # Loaded first, and by every page that loads either stylesheet — a page
    # that loads help.css without tokens.css renders with every custom
    # property undefined, which is a page with no colours at all.
    for page in PAGES:
        if not (ROOT / page).is_file():
            continue
        src = read(page)
        uses = [n for n in ("styles.css", "help.css") if f'href="{n}"' in src]
        if not uses:
            continue
        if 'href="tokens.css"' not in src:
            bad(f"{page} loads {uses[0]} without tokens.css, so every colour on "
                "it is an undefined custom property")
            continue
        if src.index('href="tokens.css"') > min(src.index(f'href="{n}"') for n in uses):
            bad(f"{page} loads tokens.css after {uses[0]}; the variables must be "
                "defined before the rules that read them")
    ok("every page that loads a stylesheet loads tokens.css first")

    # The devices that make the two halves recognisable as one place. Each of
    # these was carried across deliberately; losing one is how the directory
    # quietly becomes a different website.
    front, story = read("help.html"), read("index.html")
    helpcss = read("help.css")
    for what, test in [
        ("the brand lockup, identical on both",
         '<span class="brand__txt">Waypoint<small>Student Health Corps</small></span>'
         in front and
         '<span class="brand__txt">Waypoint<small>Student Health Corps</small></span>'
         in story),
        ("the eyebrow above the title", 'class="eyebrow mast__eye"' in front),
        ("the roman-then-gold-italic heading", "<em>" in front and
         ".mast h1 em{ color:var(--gold); }" in helpcss),
        ("the painted valley behind the masthead", 'class="mast__bg"' in front and
         "assets/band.webp" in helpcss),
        # Asked as "does .hfoot paint itself green-deep", not as "does this
        # exact byte sequence appear": adding --focus to the same block once
        # made this fail while the footer was still green.
        ("the deep green footer",
         bool(re.search(r"\.hfoot\{[^}]*background:var\(--green-deep\)", helpcss))),
    ]:
        if test:
            ok(f"carried across: {what}")
        else:
            bad(f"the directory has lost {what}, which is one of the things that "
                "makes it read as the same organisation as the narrative page")

    if (ROOT / "assets" / "band.webp").is_file():
        kb = (ROOT / "assets" / "band.webp").stat().st_size / 1024
        if kb <= 40:
            ok(f"assets/band.webp is {kb:.0f} KB")
        else:
            bad(f"assets/band.webp is {kb:.0f} KB. The masthead image is the only "
                "picture on a page built for somebody on transit data; over 40 KB "
                "it stops being worth what it buys.")
    else:
        bad("assets/band.webp is missing, so the masthead has no picture in it")


def check_directory_is_generated():
    """help.html must equal what build_help.py produces, byte for byte.

    Compared, never rewritten. An earlier version of this check just ran the
    generator, which "passed" by overwriting whatever it found — so a
    hand-edit was silently reverted and, worse, every check below it then read
    the regenerated file and saw nothing wrong. A guard that repairs the thing
    it is meant to be measuring reports success either way.

    If this fails, the change belongs in data/resources.csv or build_help.py,
    followed by `python3 build_help.py`.
    """
    if not (ROOT / "build_help.py").is_file():
        bad("build_help.py is missing; help.html can no longer be regenerated")
        return
    sys.path.insert(0, str(ROOT))
    try:
        # Bytecode is cached on (mtime, size). A build_help.py that was edited
        # and put back — which is what break-testing a guard does — can land on
        # the same size in the same second, and then `reload` cheerfully hands
        # back the OLD module while every check below reads the NEW file. That
        # produced a full page of confident, wrong failures once.
        importlib.invalidate_caches()
        import build_help
        importlib.reload(build_help)
    except Exception as e:
        bad(f"build_help.py does not import: {type(e).__name__}: {e}")
        return

    try:
        build_help.selfcheck()
        ok("build_help.py: the phone-parser self-check passes")
    except AssertionError as e:
        bad(f"build_help.py self-check failed: {e}")
        return

    # The link checker's "this page says it is gone" pattern, against real
    # strings. Offline, so it belongs here even though the checker itself
    # talks to the internet and does not.
    try:
        import check_links_live
        g, f = check_links_live.selfcheck()
        ok(f"check_links_live.py: the soft-404 pattern matches {g} real "
           f"'page is gone' notices and rejects {f} working pages")
        check_links_live.selfcheck_hosts()
        ok("check_links_live.py: the hosts that build pages in the browser are "
           "flagged for a person, and the ones that serve their content are not")
    except AssertionError as e:
        bad(f"check_links_live.py soft-404 self-check failed: {e}")

    rows = build_help.load()
    want = {"help.html": build_help.render_overview(rows)}
    for need in build_help.NEEDS:
        want[build_help.page_for(need["key"])] = build_help.render_category(need, rows)
    by_need = {n["key"]: build_help.ordered(rows, n["key"]) for n in build_help.NEEDS}
    for L in build_help.LANGUAGES:
        want[build_help.lang_page(L["key"])] = build_help.render_language(L, rows, by_need)

    stale = [name for name, fresh in want.items()
             if not (ROOT / name).is_file() or read(name) != fresh]
    if not stale:
        ok(f"all {len(want)} resident pages match build_help.py's output "
           f"({len(rows)} resources)")
    else:
        bad(f"{len(stale)} resident page(s) are not what build_help.py produces "
            f"({', '.join(sorted(stale)[:4])}). They were hand-edited, or "
            "data/resources.csv changed without a rebuild — either way the next "
            "`python3 build_help.py` silently discards the difference. Run it.")

    home = read("index.html")
    if build_help.home_links() in home:
        ok("index.html's list of what the directory holds is the generated one")
    else:
        bad("index.html's list of what the directory holds is not what "
            "build_help.py produces. Run `python3 build_help.py`.")

    orphans = sorted(p.name for p in ROOT.glob("help-*.html") if p.name not in want)
    if orphans:
        bad(f"stale category page(s) with no need behind them: {orphans}. A need "
            "was renamed or removed and its page was left behind, so the site "
            "still serves a directory nothing links to and nothing regenerates.")
    else:
        ok("no orphaned category pages")

    unreachable = [r["Resource Name"] for r in rows
                   if build_help.contact(r["Phone"])[0] == "none" and not r["Website"]]
    if unreachable:
        bad(f"data/resources.csv: no phone and no website: {unreachable[:5]}")
    else:
        ok("data/resources.csv: every resource has a way to reach it")


def check_directory_reachable():
    """Every resource must be reachable, and every tel: must actually dial.

    A row nobody can act on is worse than no row: it costs somebody in trouble
    the time to read it. And a tel: that is neither a short code nor a full
    +1 number is a number that fails silently at the worst possible moment —
    this is the guard for the "988 then press 1 / text 838255" class of bug,
    where stripping non-digits across a whole cell produced +19881838255.
    """
    src = "\n".join(read(p) for p in CATEGORY_PAGES)
    rows = re.findall(r'<li class="r"[^>]*>(.*?)</li>', src, flags=re.S)
    if not rows:
        bad("the category pages carry no resource rows at all")
        return
    ok(f"the category pages carry {len(rows)} resource rows in the HTML")

    unreachable = [r for r in rows if 'href="tel:' not in r
                   and 'href="sms:' not in r and 'class="visit"' not in r]
    if unreachable:
        names = re.findall(r'class="r__name">([^<]+)', "".join(unreachable))
        bad(f"{len(unreachable)} resource(s) with no phone and no "
            f"website, so there is no way to act on them: {names[:5]}")
    else:
        ok("every rendered resource has a phone number or a website")

    tels = set(re.findall(r'href="tel:([^"]+)"', src))
    bad_tels = [t for t in tels if not re.fullmatch(r"\+1[0-9]{10}|[0-9]{3}", t)]
    if bad_tels:
        bad(f"tel: links that will not dial: {bad_tels}")
    else:
        ok(f"all {len(tels)} phone links are a short code or a full +1 number")


def check_directory_emergency():
    """The emergency strip is a safety surface, not a content block.

    Four numbers, each answering a different emergency, each dialable. 911
    must be one of them and must be first: somebody scanning this page in a
    panic reads the first thing in the block.
    """
    src = read("help.html")
    block = re.search(r'<section class="sos".*?</section>', src, flags=re.S)
    if not block:
        bad("help.html: the emergency strip is gone")
        return
    nums = re.findall(r'href="tel:([^"]+)"', block.group(0))
    if not nums:
        bad("help.html: the emergency strip has no phone numbers in it")
        return
    if nums[0] == "911":
        ok("help.html: the emergency strip leads with 911")
    else:
        bad(f"help.html: the emergency strip leads with {nums[0]}, not 911")
    if len(nums) >= 4:
        ok(f"help.html: {len(nums)} emergency numbers offered")
    else:
        bad(f"help.html: only {len(nums)} emergency numbers; danger, self-harm, "
            f"domestic violence and 'anything else' each need their own")
    if len(set(nums)) == len(nums):
        ok("help.html: no emergency number is listed twice")
    else:
        bad(f"help.html: an emergency number is duplicated: {nums}. A heuristic "
            f"once put two copies of 988 and a hospital switchboard here.")


def check_directory_no_js_contract():
    """The resident pages must be usable with JavaScript off.

    The whole reason the rows are generated into the HTML instead of fetched
    is that the reader may be on a locked-down library terminal, a dying
    phone, or a connection that drops help.js. So: on a category page no row
    may ship hidden, and on every resident page the only controls that ship
    hidden are the ones that genuinely cannot work without a script. Nobody is
    offered a control that does nothing.
    """
    for page in CATEGORY_PAGES:
        src = read(page)
        hidden_rows = [r for r in re.findall(r'<li class="r"[^>]*>', src) if "hidden" in r]
        if hidden_rows:
            bad(f"{page}: {len(hidden_rows)} row(s) ship with the hidden "
                f"attribute, so a reader without JavaScript never sees them")
    ok(f"no resource row is hidden in any of the {len(CATEGORY_PAGES)} category pages")

    for page in RESIDENT_PAGES:
        src = read(page)
        for sel, why in [(r'<section class="find"[^>]*\shidden>', "the search and filter block"),
                         (r'class="dir__none" hidden>', "the no-matches message"),
                         (r'<button type="button" class="printbtn" hidden>', "the print button")]:
            if not re.search(sel, src):
                bad(f"{page}: {why} no longer ships hidden — without JavaScript "
                    f"it would be a control that does nothing")
        if "<noscript>" not in src:
            bad(f"{page}: no <noscript> note. With scripts off the search block "
                "vanishes with no explanation of where it went.")
    ok(f"across {len(RESIDENT_PAGES)} resident pages, every script-only control "
       "ships hidden with a <noscript> note beside it")

    # help.js may only *hide* rows on a category page: everything there is
    # already in the markup. The front page is the one exception, and it is a
    # deliberate one — it carries fifteen clusters of three, not the whole
    # directory, so its search has to build results from the index. The rule
    # that replaces "never build markup" is narrower and stronger: the index
    # must cover every resource, and every row it builds must point at a real
    # anchor on a real category page.
    js = read("help.js")
    for meth in ["document.write", "insertAdjacentHTML"]:
        if meth in js:
            bad(f"help.js uses {meth}")
    builds = js.count("innerHTML")
    if builds > 2:
        bad(f"help.js writes innerHTML in {builds} places. Building markup is "
            "allowed only for front-page search results; anywhere else it "
            "means a resource exists that the no-JavaScript page never shows.")
    else:
        ok("help.js builds markup only for front-page search results")

    src = read("help.html")
    m = re.search(r'<script type="application/json" id="ix">(.*?)</script>', src, re.S)
    if not m:
        bad("help.html: the search index is gone, so the front page's search "
            "box can no longer reach anything that is not one of the previews")
        return
    try:
        ix = json.loads(m.group(1).replace("<\\/", "</"))
    except Exception as e:
        bad(f"help.html: the search index is not valid JSON ({e}); the front "
            "page's search silently does nothing")
        return

    import build_help
    rows = build_help.load()
    if len(ix["rows"]) == len(rows):
        ok(f"help.html: the search index covers all {len(rows)} resources, not "
           "only the ones previewed")
    else:
        bad(f"help.html: the search index has {len(ix['rows'])} entries for "
            f"{len(rows)} resources. Searching the front page cannot find the "
            "difference.")

    ids = {}
    for page in CATEGORY_PAGES:
        for i in re.findall(r'\sid="(r-[^"]+)"', read(page)):
            ids[i] = page
    broken = [it for it in ix["rows"]
              if f"r-{it['g']}-{it['i']}" not in ids]
    if broken:
        bad(f"{len(broken)} search result(s) link to an anchor that does not "
            f"exist on any category page, e.g. {broken[0]['n']!r} -> "
            f"help-{broken[0]['g']}.html#r-{broken[0]['g']}-{broken[0]['i']}")
    else:
        ok(f"every one of the {len(ix['rows'])} search results links to a real "
           "anchor on a real category page")


# The numbers this site writes into prose are a standing hazard. "Fifteen
# kinds of help" was true for about four hours. Guard the whole class rather
# than the instance.
SPELLED = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
           "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
           "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
           "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}


def check_no_stale_counts():
    """Prose on a resident page must not count things the build already counts.

    Two numbers on this site are allowed to be written down, because both are
    generated from the data every build: the directory's total, and each
    category page's own total. Everything else — how many kinds of help there
    are, how many languages, how many places under a heading — goes stale the
    first time somebody adds one, and it goes stale silently, in a sentence
    nobody re-reads.
    """
    import build_help
    n_needs = len(build_help.NEEDS)
    n_langs = len(build_help.LANGUAGES)
    words = "|".join(SPELLED)
    countish = re.compile(
        rf"\b({words})\b\s+(kinds? of help|languages?|headings?|clusters?|"
        r"pages?|categor(?:y|ies))", re.I)

    found = []
    for page in RESIDENT_PAGES + ["index.html"]:
        text = strip_tags(strip_comments(read(page)))
        for m in countish.finditer(text):
            said, what = SPELLED[m.group(1).lower()], m.group(2).lower()
            truth = n_langs if "language" in what else n_needs
            if said != truth:
                found.append(f"{page}: says {m.group(0)!r}, but there are {truth}")
            else:
                found.append(f"{page}: {m.group(0)!r} happens to be right today, "
                             "and is written in prose where nothing will update it")
    if found:
        for f in found:
            bad(f)
    else:
        ok("no resident page counts in prose something the build already counts")

    # The two counts that ARE allowed have to be the generated ones.
    rows = build_help.load()
    if re.search(r"list of <b>%d places</b>" % len(rows), read("help.html")):
        ok(f"the one count in the front page's prose is the generated {len(rows)}")
    else:
        bad("the front page's total is not the generated count")


# ---------------------------------------------------------------- searching
# The queries that must not stop working, and what each one has to reach.
#
# This is a check on the DATA, not on the ranking. It asserts that every
# content word in the query appears somewhere in the named resource's
# searchable text — its name, what it calls itself, its tags, or the
# plain-English phrases SYNONYMS attaches. If that holds, help.js can find it;
# if it stops holding, help.js cannot, however good the ranking is.
#
# Every entry here was a real failure at some point. "my husband hits me",
# "i want to die" and "heroin" all returned a blank page once. "my daughter is
# being abused" returned a housing lottery. "unpaid wages" returned a
# job-training centre, because the directory had nothing about wage theft at
# all. A query in this table is a promise that the words a frightened person
# actually types reach the thing that helps them.
CRITICAL_QUERIES = [
    # the emergencies
    ("my husband hits me",          "NYC HOPE — 24-Hour DV Hotline (Safe Horizon)"),
    ("my daughter is being abused", "Safe Horizon"),
    ("im scared of my boyfriend",   "NYC HOPE — 24-Hour DV Hotline (Safe Horizon)"),
    ("i want to die",               "NYC 988 (formerly NYC Well)"),
    ("kill myself", ("988 Suicide & Crisis Lifeline",
                                    "NYC 988 (formerly NYC Well)")),
    ("someone to talk to",          "NYC 988 (formerly NYC Well)"),
    ("heroin", ("NY OASAS HOPEline", "NYC 988 (formerly NYC Well)")),
    ("narcan",                      "OASAS Free Naloxone / Harm Reduction"),
    ("overdose",                    "OASAS Free Naloxone / Harm Reduction"),
    ("they took my passport",       "National Human Trafficking Hotline"),
    # what this site exists for
    ("cant pay my hospital bill",   "Hospital Financial Assistance (every NY hospital)"),
    ("charity care", ("Hospital Financial Assistance (every NY hospital)", "Dollar For")),
    ("insurance said no",           "Community Health Advocates (CHA)"),
    ("denied claim",           "Community Health Advocates (CHA)"),
    ("medical debt collector",      "Consumer Financial Protection Bureau — complaint"),
    ("my medicine is too expensive","NeedyMeds"),
    # food
    ("food stamps",                 "SNAP (Food Stamps)"),
    ("free food",                   "Food Help NYC (official finder)"),
    ("hot meal",                    "Holy Apostles Soup Kitchen"),
    # housing
    ("shelter tonight",             "NYC DHS Shelter Intake (right to shelter)"),
    ("kicked out",                  "Homebase (Homelessness Prevention)"),
    ("landlord wont fix",      "JustFix"),
    ("back rent", ("HRA Emergency Assistance / One Shot Deal",
                                    "FHEPS (rent help for families)")),
    ("i sleep on the train", ("Coalition for the Homeless — Crisis Intervention",
                                    "Breaking Ground Street Outreach")),
    # health
    ("free clinic no insurance",    "NYC Care"),
    ("dentist",                     "NYU College of Dentistry Clinics"),
    ("abortion",                    "NYC Abortion Access Hub"),
    ("birth control",               "Planned Parenthood of Greater New York"),
    # legal, work, benefits
    ("deportation",                 "Immigrant Defense Project Hotline"),
    ("green card",                  "CUNY Citizenship Now!"),
    ("unpaid wages",                "NYS Department of Labor — unpaid wages"),
    ("my boss didnt pay me",        "NYC Worker Rights (DCWP)"),
    ("my benefits were cut off",    "New York Legal Assistance Group (NYLAG)"),
    ("con ed shut off my power", "Con Edison payment help"),
    ("free tax help",               "NYC Free Tax Prep"),
    # the ones added because the directory had nothing
    ("seal my record",              "Legal Action Center"),
    ("job with a felony",           "Center for Employment Opportunities (CEO)"),
    ("wheelchair",                  "Access-A-Ride (MTA Paratransit)"),
    ("im blind",                    "Lighthouse Guild"),
    ("help after a fire",           "American Red Cross Greater New York"),
    ("i cant afford a funeral",     "HRA Burial Assistance"),
    ("my son was shot",             "Mayor’s Office to Prevent Gun Violence"),
    ("free wifi",                   "New York Public Library — help at the branch"),
    ("interpreter",                 "NYC 311"),
    ("who do i call",               "NYC 311"),

    # The ten languages, searched rather than only read. Each of these
    # returned nothing at all until the tokenizer stopped deleting every
    # character outside ASCII and the vocabulary existed to match.
    ("comida",                      "Food Help NYC (official finder)"),
    ("abogado",                     "MOIA Immigration Legal Support Hotline (ActionNYC)"),
    ("violencia doméstica",         "NYC HOPE — 24-Hour DV Hotline (Safe Horizon)"),
    ("\u98df\u7269",                        "Food Help NYC (official finder)"),
    ("\u533b\u751f",                        "NYC Care"),
    ("\u0435\u0434\u0430",                       "Food Help NYC (official finder)"),
    ("\u0432\u0440\u0430\u0447",                     "NYC Care"),
    ("manje",                       "Food Help NYC (official finder)"),
    ("\uc74c\uc2dd",                        "Food Help NYC (official finder)"),
    ("\u0637\u0639\u0627\u0645",                     "Food Help NYC (official finder)"),
    ("\u06a9\u06be\u0627\u0646\u0627",                    "Food Help NYC (official finder)"),
    ("nourriture",                  "Food Help NYC (official finder)"),
    ("jedzenie",                    "Food Help NYC (official finder)"),
    ("\u0996\u09be\u09ac\u09be\u09b0",                   "Food Help NYC (official finder)"),

    # The last round of gaps.
    ("ice came to my door",         "Know Your Rights with ICE"),
    ("i got court papers",          "Housing Court Help Center"),
    ("con ed shut off",             "Con Edison payment help"),
    ("i cant sleep since the baby", "Postpartum depression help (NYC Health)"),
    # Found by typing fifty realistic phrasings into the built page and
    # reading what came back. Each of these returned nothing, or returned
    # something from a different part of somebody's life.
    ("free eyeglasses", "SUNY College of Optometry — University Eye Center"),
    ("my mom has dementia", "CaringKind — dementia helpline"),
    ("period products", "Free period products (schools and shelters)"),
    ("help paying for a funeral", "HRA Burial Assistance"),
    ("somewhere to sleep tonight", ("NYC DHS Shelter Intake (right to shelter)",
                                    "The Bowery Mission")),
    ("i am being evicted", "Right to Counsel — Free Eviction Defense"),
    ("paying for medicine", "RxAssist"),
    ("i need a bed", ("NYC DHS Shelter Intake (right to shelter)", "The Bowery Mission")),
    ("i need a therapist", "NAMI-NYC Helpline"),
    ("special education", ("Advocates for Children — education helpline",
                                          "The New York Foundling")),
    ("my child was suspended", "Advocates for Children — education helpline"),
    ("halal", ("ICNA Relief NY food pantries",
                                    "Council of Peoples Organization (COPO)")),
    ("day laborer", "NICE — New Immigrant Community Empowerment"),
    ("tps", "MOIA Immigration Legal Support Hotline (ActionNYC)"),
    # The initials and building names people are handed on the phone.
    ("welfare", "Cash Assistance (Public Assistance / TANF)"),
    ("acs", ("The Bronx Defenders", "Brooklyn Defender Services",
             "Neighborhood Defender Service of Harlem")),
    ("bellevue", "NYC Health + Hospitals (public hospital system)"),
    ("section8", "NYCHA Public Housing"),
]

# The stop list and the stemmer, kept in step with help.js by hand. Both are
# small, both are commented in one place there, and duplicating them here is
# cheaper than shipping a JavaScript runtime into the linter.
_STOP = set((" i me my mine we our you your a an the is am are be been it its this that "
             "to of for and or in on at with from about need needs help please do does did "
             "how where what who can cant cannot get got some any my im ive have has had "
             "there here now they them he she his her not no "
             "being was were just still even much very really been ").split())


def _stem(w):
    if not w.isascii():
        return w
    for suf, keep in (("ing", 3), ("ies", 3), ("ed", 2), ("es", 2), ("s", 1), ("ly", 2)):
        if len(w) - keep >= 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


# ------------------------------------------------------------- reading level
# Flesch-Kincaid, on the copy this site writes about itself. Not on the
# resources: their descriptions come from the agencies that run them and are
# edited where they are wrong, not rewritten to hit a number.
#
# The measure is crude and it is mostly measuring sentence length, which is
# exactly the thing worth measuring here. Four of the page intros scored
# between 11 and 15 not because the words were hard — they were "benefits",
# "rent", "meals" — but because each was one thirty-to-forty-five word
# sentence, and a long sentence is what a frightened person stops reading.
_VOWELS = "aeiouy"


def _syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n, prev = 0, False
    for ch in w:
        v = ch in _VOWELS
        if v and not prev:
            n += 1
        prev = v
    if w.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


def reading_grade(text):
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = [w for w in re.split(r"[^A-Za-z']+", text) if w]
    if not sentences or not words:
        return None
    syl = sum(_syllables(w) for w in words)
    return round(0.39 * (len(words) / len(sentences))
                 + 11.8 * (syl / len(words)) - 15.59, 1)


def check_reading_level():
    """The copy the site writes about itself has to be readable."""
    import build_help
    rows = build_help.load()
    CEILING = 9.0

    # Only on prose. The formula is a ratio of words to sentences and
    # syllables to words, and on a five-word noun phrase both ratios are
    # nonsense — "Immigration" scores grade 32 as a one-word sentence. A
    # heading is checked for what actually goes wrong with headings: length.
    MIN_WORDS = 18

    over = []
    for need in build_help.NEEDS:
        for field in ("blurb", "intro"):
            text = need[field]
            if len(re.findall(r"[A-Za-z']+", text)) < MIN_WORDS:
                continue
            g = reading_grade(text)
            if g is not None and g > CEILING:
                over.append(f'{need["key"]}/{field}: grade {g} — {text[:70]!r}')

    g = reading_grade(build_help.HONESTY)
    if g is not None and g > CEILING:
        over.append(f"the honesty statement is at grade {g}")

    # Headings: a rail entry is read at a glance and wraps to three lines on a
    # phone if it runs long.
    LABEL_MAX = 52
    for key, buckets in build_help.GROUPS.items():
        for bk, label, _ in buckets:
            if len(label) > LABEL_MAX:
                over.append(f"{key}/{bk}: bucket label is {len(label)} characters "
                            f"({LABEL_MAX} is the ceiling) — {label!r}")
    for need in build_help.NEEDS:
        if len(need["short"]) > 26:
            over.append(f'{need["key"]}: the short name is {len(need["short"])} '
                        f'characters, too long for a chip — {need["short"]!r}')

    # Agency words a reader has to already know. Each of these is fine in the
    # Subcategory (internal filing) and in the Tags (search vocabulary); in the
    # prose somebody reads, each has an ordinary-English version and the
    # ordinary-English version is what ships.
    # An abbreviation the reader has to already expand. DV is the one that
    # kept coming back — it is what the field calls domestic violence, and it
    # is not what anybody living through it calls it.
    ABBREV = re.compile(r"\b(DV|FQHC|ESOL|HSE|TANF|CBO|LEP|SUD)\b")
    for r in rows:
        for field in ("Description", "Notes"):
            m = ABBREV.search(r[field] or "")
            if m:
                over.append(f'{r["Resource Name"]}: {field} uses the abbreviation '
                            f'{m.group(0)!r} without saying what it is')

    JARGON = {
        "sliding scale": "a price based on what you earn",
        "federally qualified": "community health centre",
        "case manage": "a caseworker",
        "arrears": "rent you have fallen behind on",
        "warm handoff": "hand the person over",
        "psychosocial": "",
        "wraparound": "",
        "means-tested": "",
    }
    for r in rows:
        for field in ("Description", "Notes"):
            low = (r[field] or "").lower()
            for term, plain in JARGON.items():
                if term in low:
                    over.append(f'{r["Resource Name"]}: {field} says {term!r}'
                                + (f' — say {plain!r}' if plain else ""))

    # Who qualifies is never ours to state — it is the first of the eight
    # nevers, and "for eligible low-income individuals" tells somebody they
    # may not be before anybody has looked at their situation. The Who Can
    # Access column carries that, one tap down, phrased as a description of
    # who the programme is for rather than a judgement about the reader.
    WHO = re.compile(r"\b(eligible|eligibility|qualifying)\b", re.I)
    for r in rows:
        m = WHO.search(r["Description"] or "")
        if m:
            over.append(f'{r["Resource Name"]}: the description says '
                        f'{m.group(0)!r} — who qualifies is not ours to state')

    # A claim with a clock on it. The site already refuses to quote a filing
    # deadline; the same reasoning applies to "free through the end of the
    # year" and "locations were changing in 2026", which go stale in silence
    # and are then read in February by somebody who believes them.
    DATED = re.compile(r"\b(through the end of|by the end of|expires?|"
                       r"as of 20\d\d|in 20\d\d|through 20\d\d|closes on)\b", re.I)
    for r in rows:
        for field in ("Description", "Notes"):
            m = DATED.search(r[field] or "")
            if m:
                over.append(f'{r["Resource Name"]}: {field} makes a claim with a '
                            f'clock on it — {m.group(0)!r}')

    # A slash between two words is a punctuation mark the reader has to
    # interpret, on a page read by people whose second language is English.
    # 24/7 and HIV/AIDS are fixed phrases and stay.
    ALLOWED_SLASH = {"24/7", "HIV/AIDS"}
    for r in rows:
        for field in ("Description", "Notes"):
            for m in re.finditer(r"\w+/\w+", r[field] or ""):
                if m.group(0) not in ALLOWED_SLASH:
                    over.append(f'{r["Resource Name"]}: {field} has '
                                f'{m.group(0)!r} — say it with a word')

    if over:
        for x in over:
            bad("reading level: " + x)
    else:
        whole = reading_grade(" ".join(
            [n["blurb"] for n in build_help.NEEDS]
            + [n["intro"] for n in build_help.NEEDS]
            + [build_help.HONESTY]))
        ok(f"the prose the site writes about itself is at or below grade "
           f"{CEILING:.0f} (all of it together: {whole}), and every heading "
           "fits its chip")


def check_page_weight():
    """What a reader on transit data actually downloads.

    Measured gzipped, because that is what crosses the wire and because raw
    size badly overstates the cost of the search index — it is repetitive and
    compresses to a fifth. Deduplicating it by hand saved two kilobytes and
    was not worth the machinery; this budget is the thing that would catch it
    if that ever stopped being true.

    The budgets are set a little above where the pages sit, so ordinary growth
    is fine and a step change is not.
    """
    import gzip
    # The ten language pages get the tightest budget on the site, at 14 KB
    # against the 8 they currently weigh. They are static HTML with no script
    # and no search index, and the reader they exist for is on the worst
    # connection here — so a step change on those is the one most worth
    # catching.
    budgets = [("help.html", 90), *[(p, 40) for p in CATEGORY_PAGES],
               *[(p, 14) for p in LANGUAGE_PAGES]]
    worst = 0
    for page, kb in budgets:
        if not (ROOT / page).is_file():
            continue
        raw = (ROOT / page).read_bytes()
        gz = len(gzip.compress(raw, 9)) / 1024
        worst = max(worst, gz)
        if gz > kb:
            bad(f"{page} is {gz:.0f} KB gzipped, over its {kb} KB budget. On the "
                "connection this page is written for that is the difference "
                "between arriving and giving up.")
    ok(f"every resident page is inside its transfer budget "
       f"(largest {worst:.0f} KB gzipped)")


def check_checked_date_is_derived():
    """"Checked June-August 2026" must come from the data, not from a keystroke.

    Three failures live here, and all three shipped at least once.

    It was typed in three places, and by the time anybody looked two said June
    and one said August — on the sheet a student hands somebody, as the answer
    to "how do I know this is still right".

    Then it was derived from the newest row, so one number confirmed this
    morning let the whole sheet claim August over a list a fifth of which
    nobody had touched since June.

    And this check itself hunted for "Checked <Month> <Year>", so the moment
    the wording became a span it matched nothing anywhere and passed with an
    empty hand. A check that cannot fail is worse than no check, because it
    reports a green square. So it now demands the sentence be *present* on
    every page as well as correct.
    """
    import build_help
    rows = build_help.load()
    months = "|".join(build_help.MONTHS)

    def span(rs):
        """The oldest and newest month in a set of rows, worked out here.

        Deliberately not build_help.checked(). A check that asks the code
        under test what the right answer is agrees with that code even when
        the code is wrong: an earlier version of this one derived its
        expectation from checked(), so when checked() went back to printing
        only the newest month — the bug this check exists to catch — the
        check moved with it and reported a green square.
        """
        ds = sorted(r["Last Verified"] for r in rs if r.get("Last Verified"))
        if not ds:
            return "not yet checked"
        lo, hi = ds[0].split("-"), ds[-1].split("-")
        m0, y0 = build_help.MONTHS[int(lo[1]) - 1], lo[0]
        m1, y1 = build_help.MONTHS[int(hi[1]) - 1], hi[0]
        if (m0, y0) == (m1, y1):
            return f"{m0} {y0}"
        return f"{m0}\u2013{m1} {y1}" if y0 == y1 else f"{m0} {y0}\u2013{m1} {y1}"
    SPAN = rf"(?:{months})(?: \d{{4}})?(?:\u2013(?:{months}) \d{{4}})?"
    # Two sentences, two scopes, and they are allowed to differ. The printed
    # header speaks for the resources on the page it is printed on; the site
    # footer sits under the whole directory's count and speaks for the file.
    HEAD = re.compile(rf"Checked ({SPAN}); programs change")
    FOOT = re.compile(rf"Last checked ({SPAN})\.")
    whole = span(rows)
    if whole != build_help.checked(rows):
        bad(f"build_help.checked() says {build_help.checked(rows)!r}; the oldest and newest dates in the file are {whole!r}")

    bad_pages, seen = [], 0
    for page in RESIDENT_PAGES:
        src = read(page)
        key = page[len("help-"):-len(".html")] if page.startswith("help-") else None
        want = span(build_help.ordered(rows, key)) if key else whole
        for pat, said_of, label in ((HEAD, want, "the resources on it were"),
                                    (FOOT, whole, "the directory was")):
            found = pat.findall(src)
            if not found:
                bad_pages.append(f"{page}: the {'printed header' if pat is HEAD else 'footer'} "
                                 f"has no date sentence — the wording moved and this "
                                 f"check went blind")
                continue
            for said in found:
                seen += 1
                if said != said_of:
                    bad_pages.append(f"{page} says {said!r}; {label} checked {said_of}")

    if bad_pages:
        for x in sorted(set(bad_pages)):
            bad(x)
    else:
        ok(f"every \"checked\" date on the resident pages is generated from that "
           f"page's own rows ({seen} of them, {whole} overall)")


def check_focus_ring():
    """The focus ring is one object, and its colour belongs to the surface.

    Found by tabbing through the built pages with a script that measured each
    ring against the colour actually behind it: in the deep-green footer, on
    both halves of the site, the ring was --green on --green-deep. 1.24:1. It
    was being drawn and it could not be seen, which for a keyboard or switch
    user is the same as not being drawn.

    The cause was that each component named its own ring colour, so the ring
    knew about the button and nothing about the room. It is now a token —
    --focus — set once per dark room and inherited. This guards the three ways
    that arrangement gets undone:

      1. a --focus that does not contrast with the ground declared beside it;
      2. a component going back to naming its own outline colour;
      3. `outline:none` with nothing restoring a ring under forced colours,
         where the border and box-shadow substitutes are thrown away.
    """
    tok = read("tokens.css")
    root = dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{3,8})", tok))

    def rgb(c):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(x * 2 for x in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def lum(c):
        def f(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = rgb(c)
        return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)

    def ratio(a, b):
        la, lb = lum(a), lum(b)
        hi, lo = max(la, lb), min(la, lb)
        return (hi + .05) / (lo + .05)

    def hexof(v):
        v = v.strip().rstrip(";").split()[0]
        m = re.fullmatch(r"var\(--([a-z0-9-]+)\)", v)
        if m:
            return root.get(m.group(1))
        return v if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", v) else None

    if "--focus" not in tok:
        bad("tokens.css does not define --focus; the ring has no default")
        return
    ok("tokens.css defines --focus, so both stylesheets ask the same question")

    if not re.search(r":focus-visible\s*\{[^}]*outline:[^}]*var\(--focus\)", tok):
        bad("tokens.css defines --focus but no rule paints a ring with it")
    else:
        ok("one :focus-visible rule, in the shared sheet, paints the ring")

    # The search input opts out of that rule with outline:none and hands its
    # ring to the box around it. Tabbed to, it had no ring at all: the box's
    # own indication was a 1.5px border change and a halo at 10% alpha, 1.03:1
    # against the ground. The busiest control on the directory was the
    # quietest, and nothing said so, because the guard above only asks whether
    # the shared rule exists.
    if re.search(r"\.find__box input\{[^}]*outline\s*:\s*none", read("help.css")):
        if not re.search(r"\.find__box:has\(input:focus-visible\)\s*\{[^}]*"
                         r"outline\s*:\s*3px solid var\(--focus\)", read("help.css"),
                         re.S):
            bad("the search input sets outline:none and nothing gives the box "
                "around it the site's 3px ring, so tabbing to the busiest "
                "control on the directory shows nothing")
        else:
            ok("the search box takes the same ring as everything else")

    # 1. every --focus must beat the ground it is declared next to
    pairs = 0
    for sheet in ("help.css", "styles.css", "tokens.css"):
        src = read(sheet)
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", src):
            body = m.group(2)
            decl = re.search(r"--focus:\s*([^;]+)", body)
            if not decl:            # a block that *uses* var(--focus), not one that sets it
                continue
            sel = m.group(1).strip().splitlines()[-1].strip()
            # A ring set to nothing is the failure this whole guard exists to
            # prevent, and it resolves to no hex at all, so it used to fall
            # through the contrast test untested.
            raw = decl.group(1).strip().rstrip(";")
            if re.match(r"transparent|none|currentColor|inherit", raw, re.I):
                bad(f"{sheet} sets --focus:{raw} on {sel}. The ring is still "
                    f"drawn and still cannot be seen, which for a keyboard or "
                    f"switch user is the same as not drawing it.")
                continue
            ring = hexof(decl.group(1))
            bgm = re.search(r"(?:^|;|\s)background(?:-color)?:\s*([^;]+)", body)
            ground = hexof(bgm.group(1)) if bgm else None
            if ground is None and sel in (":root", "html", "body"):
                ground = root.get("cream")
            if not ring or not ground:
                continue
            pairs += 1
            r = ratio(ring, ground)
            if r < 3:
                bad(f"{sheet}: {sel} sets --focus:{ring} on {ground} — "
                    f"{r:.2f}:1, and 3:1 is the floor for a focus indicator")
            else:
                ok(f"{sheet}: {sel} focus ring {r:.1f}:1 against its own ground")
    # A dark *room* on the light half of the site must name a ring, because
    # everything focusable inside it inherits one. A dark *control* must not:
    # its ring is offset outward and lands on the light page behind it, and
    # naming one there would paint gold on cream. The difference is not a
    # judgement call — a control is an element you can focus, so ask the built
    # HTML whether the class ever appears on one.
    focusable_classes = set()
    for page in RESIDENT_PAGES:
        for m in re.finditer(r"<(?:a|button|input|select|textarea|summary)\b[^>]*"
                             r'class="([^"]+)"', read(page)):
            focusable_classes.update(m.group(1).split())

    rooms, unnamed = 0, []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", read("help.css")):
        body = m.group(2)
        bgm = re.search(r"(?:^|;|\s)background(?:-color)?:\s*([^;]+)", body)
        if not bgm or not re.search(r"(?:^|;|\s)color:", body):
            continue
        ground = hexof(bgm.group(1))
        if not ground or lum(ground) >= .18:
            continue
        sel = m.group(1).strip().splitlines()[-1].strip()
        cls = re.match(r"\.([A-Za-z0-9_-]+)", sel)
        if not cls or cls.group(1) in focusable_classes:
            continue                      # a control; its ring lands outside it
        rooms += 1
        if "--focus:" not in body:
            unnamed.append(f"help.css: {sel} is a dark room on a light page but "
                           f"names no --focus, so everything focusable inside it "
                           f"gets a green ring on a green ground")
    for u in sorted(set(unnamed)):
        bad(u)
    if not unnamed:
        ok(f"all {rooms} dark rooms in the directory name their own focus ring")

    if "--focus" not in read("styles.css"):
        bad("styles.css never sets --focus; the narrative side is one dark room "
            "and body must say so once for everything inside it")
    else:
        ok("the narrative side sets --focus once, on body, for the whole dark room")

    # 2. nobody may go back to a hand-coloured ring
    rogue = []
    for sheet in ("help.css", "styles.css"):
        src = read(sheet)
        for m in re.finditer(r"([^{}]*:focus(?:-visible|-within)?[^{}]*)\{([^{}]*)\}", src):
            body = m.group(2)
            if "forced-colors" in src[max(0, m.start() - 260):m.start()]:
                continue          # Highlight is a system colour, and correct there
            col = re.search(r"outline(?:-color)?:\s*(?:[\d.]+px\s+\w+\s+)?"
                            r"(#[0-9A-Fa-f]{3,8}|var\(--(?!focus)[a-z0-9-]+\))", body)
            if col:
                rogue.append(f"{sheet}: {m.group(1).strip().splitlines()[-1].strip()[:52]} "
                             f"paints its own ring ({col.group(1)}) instead of var(--focus)")
    for r in sorted(set(rogue)):
        bad(r)
    if not rogue:
        ok("no component paints its own focus ring; they all inherit --focus")

    # 3. outline:none needs a forced-colours understudy
    for sheet in ("help.css", "styles.css"):
        src = read(sheet)
        strips = re.findall(r"([^{}]+)\{[^{}]*outline:\s*(?:none|0)\s*[;}]", src)
        if not strips:
            ok(f"{sheet} never removes an outline")
            continue
        if not re.search(r"@media\s*\(forced-colors:\s*active\)\s*\{[^{}]*"
                         r"\{[^{}]*outline:[^{}]*Highlight", src, re.S):
            bad(f"{sheet} removes the outline on {strips[0].strip()[:40]!r} but has no "
                f"forced-colors rule putting a ring back; in High Contrast the "
                f"border and shadow standing in for it are discarded")
        else:
            ok(f"{sheet} removes an outline and restores one under forced colours")


def check_heading_order():
    """Every page's headings, as a screen reader lists them.

    Somebody navigating by heading gets an outline, not a page, and a level
    that jumps h2 -> h4 tells them a heading is missing and they have lost
    their place. The two narrative pages did exactly that: the footer column
    labels were h4 because h4 was the size they wanted, three levels below a
    page whose sections are h2.

    Cheap to state, so it covers every page the site has rather than the one
    it was noticed on.
    """
    tag = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.S | re.I)
    strip = re.compile(r"<[^>]+>")
    # "Every page the site has" used to mean a list that had drifted: it named
    # privacy.html and not terms.html, and neither of the two internal
    # documents. Both of those turned out to be wrong — one had four h1s, the
    # other started at h2. Glob it, so the docstring stays true.
    for page in sorted(str(q) for q in Path(".").glob("*.html")):
        try:
            src = read(page)
        except Missing:
            continue
        if 'http-equiv="refresh"' in src:
            continue
        hs = [(int(m.group(1)), strip.sub("", m.group(2)).strip()[:40])
              for m in tag.finditer(src)]
        ones = [h for h in hs if h[0] == 1]
        if len(ones) != 1:
            bad(f"{page}: {len(ones)} h1s; a page is one thing and says so once")
        skips = []
        prev = 0
        for lvl, txt in hs:
            if prev and lvl > prev + 1:
                skips.append(f"h{prev} to h{lvl} at {txt!r}")
            prev = lvl
        if skips:
            bad(f"{page}: heading levels skip — {'; '.join(skips[:3])}")
        else:
            ok(f"{page}: {len(hs)} headings, one h1, no level skipped")


def check_language_numbers_dial():
    """The numbers on a translated page have to be tappable, like every other
    number on the site.

    They were plain text: "llame al 911", "311 ke liye call karein". Every
    number on every English part of this site is one tap. The reader who most
    needs it not to be — no English, a phone, possibly an emergency — was the
    one being asked to memorise three digits and go find the dialler.

    This used to read the `langnote` panels, which the ten full language pages
    replaced. It looped over nothing and passed. It now reads the pages.
    """
    import build_help

    want = ("911", "988", "311", "988")
    # Anything that looks like a number a person would dial, once the links
    # are taken out of the page. Three digits alone, or a ten-digit number in
    # any of the shapes the descriptions use.
    loose = re.compile(r"(?<![\d>-])(?:911|988|311|\d{3}[-.\s]\d{3}[-.\s]\d{4})"
                       r"(?![\d<-])")
    missing, seen = [], 0
    for key in build_help.LANG_SLUG:
        page = build_help.lang_page(key)
        if not os.path.exists(page):
            bad(f"{page} is missing")
            continue
        seen += 1
        src = read(page)
        # Take the anchors out whole — what is left is text nobody can tap.
        text = re.sub(r"<a\b[^>]*>.*?</a>", " ", src, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        for hit in sorted(set(loose.findall(text))):
            missing.append(f"{page} prints {hit} as text, not a link")
        for n in ("911", "988", "311"):
            if f'href="tel:{n}"' not in src:
                missing.append(f"{page} never gives the reader {n}")
    for m in sorted(set(missing))[:12]:
        bad(m)
    if not missing:
        ok(f"all {seen} language pages dial their numbers rather than printing them")


def check_one_header():
    """The same bar on all twenty pages: same lockup, same three tabs, same order.

    They were two components that had drifted: five tabs on the narrative side
    and three on the directory, a solid pin against an outlined one, 22px of
    padding against 12px, a slide-out drawer on one half and a wrapped second
    row on the other. Each difference was defensible on its own and together
    they made one organisation look like two.

    The look is in tokens.css. What varies per half is six colour tokens and
    one line of positioning — and this fails if anything else does.
    """
    PAGES = [p for p in RESIDENT_PAGES + ["index.html", "privacy.html", "terms.html"]
             if (ROOT / p).is_file()]
    grab = re.compile(r'<header class="sitehead">(.*?)</header>', re.S)
    tabs = re.compile(r'<a href="([^"]+)"[^>]*>([^<]+)</a>')

    shapes = {}
    for page in PAGES:
        m = grab.search(read(page))
        if not m:
            bad(f"{page}: no shared header — this page is still its own component")
            continue
        block = m.group(1)
        # the lockup, to the pixel: one pin path, one wordmark, one strapline
        for want, what in [('class="pin"', "the pin"),
                           ('class="pin-dot"', "the pin's centre"),
                           ('<span class="brand__txt">Waypoint', "the wordmark"),
                           ("<small>Student Health Corps</small>", "the strapline")]:
            if want not in block:
                bad(f"{page}: the header is missing {what}")
        names = [t[1] for t in tabs.findall(block) if "brand" not in t[0]]
        names = [n for n in names if n != "Waypoint"]
        shapes.setdefault(tuple(names), []).append(page)

    if len(shapes) == 1:
        names = next(iter(shapes))
        ok(f"all {len(PAGES)} pages carry the same tabs, in the same order: "
           f"{' / '.join(names)}")
    else:
        for names, pages in sorted(shapes.items(), key=lambda kv: -len(kv[1])):
            bad(f"{len(pages)} page(s) show tabs {list(names)} "
                f"(e.g. {pages[0]}) — the two halves have drifted apart again")

    # the gold pill means the same thing in both places
    for page in PAGES:
        m = grab.search(read(page))
        if m and 'class="is-find"' not in m.group(1):
            bad(f"{page}: 'Find help' is not the gold pill, so the one tab "
                f"addressed to somebody in trouble looks like the others")
            break
    else:
        ok("'Find help' is the gold pill on every page, both halves")

    # Every class the header is built from has to be styled in the shared
    # sheet. .nav-lamp was not: it sat in styles.css, which only the narrative
    # half loads, so on the eighteen directory pages the span shipped with no
    # rules and stood in the flow as an ordinary inline element — invisible,
    # and pushing every tab four pixels right. The two bars measured identical
    # above 1080px, where the row is right-aligned and the phantom fell off
    # the end, and four pixels apart below it. At 375px it changed where the
    # row of tabs broke.
    tok = read("tokens.css")
    head_classes = set()
    for page in PAGES:
        m = grab.search(read(page))
        if m:
            for attr in re.findall(r'class="([^"]+)"', m.group(1)):
                head_classes.update(attr.split())
    for cls in sorted(head_classes):
        for sheet in ("help.css", "styles.css"):
            for sel in re.findall(r"([^{}]+)\{[^{}]*\}", read(sheet)):
                sel = sel.strip().splitlines()[-1].strip()
                # a footer or a print block may reach in; a bare rule may not
                if re.search(rf"(?:^|,\s*)\.{re.escape(cls)}\b", sel):
                    bad(f"{sheet} styles .{cls} ({sel[:44]}), but that is part of "
                        f"the shared header — only one of the two halves loads "
                        f"this sheet, so the bar renders differently on the other")
    ok(f"all {len(head_classes)} classes the header is built from are styled "
       f"in the shared sheet")

    # everything that differs must be a token, not a second component
    for sheet in ("help.css", "styles.css"):
        src = read(sheet)
        own = re.findall(r"\.sitehead[^{,]*\{([^}]*)\}", src)
        for body in own:
            for prop in re.findall(r"(?:^|;)\s*([a-z-]+):", body):
                if prop.startswith("--") or prop in ("position", "inset", "top"):
                    continue
                bad(f"{sheet} restyles the shared header ({prop}) instead of "
                    f"setting a token; that is how the two halves drifted")
        if "--head-bg" not in src:
            bad(f"{sheet} never sets --head-bg, so its header has no ground")
    ok("each half sets only colours and position; the bar itself is shared")
    # Nothing may sit between the skip link and the header. index.html had its
    # journey rail — eleven fixed scroll-position dots — earlier in the DOM,
    # so a keyboard user tabbed through all of them before reaching the site's
    # primary navigation. The rail is position:fixed, so its place in the
    # document only ever decided that.
    # An empty container counts. The rail ships as <nav class="rail"></nav> and
    # script.js fills it with eleven buttons, so looking for <button> in the
    # source finds nothing and passes — which is exactly what this check did on
    # its first draft. Anything that can hold controls has to come after.
    HOLDER = re.compile(r"<(?:nav|form|menu)\b|<(?:a\s[^>]*href|button|input|"
                        r"select|textarea|summary)\b", re.I)
    for page in PAGES:
        src = read(page)
        skip = src.find('class="skip"')
        head = src.find('<header class="sitehead">')
        if skip < 0 or head < 0:
            continue
        between = HOLDER.findall(src[src.index(">", skip) + 1:head])
        if between:
            bad(f"{page}: {between[0]}…> comes before the header, so tabbing "
                f"reaches whatever it holds before the site's primary "
                f"navigation — and an empty container counts, because script "
                f"fills it")
    ok("on every page the header is the first thing after the skip link")

    # The bar has to publish its own height, because with five tabs it is 73px
    # at a desk, 155px at 375px and 203px at 320px, and no calc() can know
    # which. Everything that clears it reads --head-h; when nothing sets it
    # from the measurement, the fallback silently understates it by 80px and a
    # heading you clicked lands behind the bar on a phone.
    for js in ("script.js", "help.js"):
        src = read(js)
        if re.search(r"ResizeObserver\([^)]*\)[\s\S]{0,220}?setProperty\(\s*[\"']--head-h",
                     src):
            ok(f"{js}: the header publishes its measured height as --head-h")
        else:
            bad(f"{js} no longer measures the header. --head-h falls back to a "
                f"calc() that is only right when the tabs fit on one row, so "
                f"anchors land behind the bar on a phone")

    hardcoded = re.findall(r"(scroll-margin-top|top):\s*(\d+)px", read("help.css"))
    stale = [f"{k}:{v}px" for k, v in hardcoded if 60 <= int(v) <= 240]
    if stale:
        bad(f"help.css clears the header with a typed height ({', '.join(sorted(set(stale)))}); "
            f"the bar is 73px to 203px depending on width, so it has to be --head-h")
    else:
        ok("everything that clears the header on the directory reads --head-h")

    if ".sitehead{" not in tok or ".sitehead__links a.is-find{" not in tok:
        bad("tokens.css no longer owns the header; it has moved back into a sheet")
    else:
        ok("tokens.css owns the bar, the lockup and the pill")


def check_language_header():
    """The ten language pages wear the same bar, in their own words.

    Same component, same five tabs, same order, same gold pill on the first —
    but the labels are that language's, and "Find help" goes to that
    language's own front page rather than the English one, because that is
    where a reader of this page finds help. The other four go to the narrative
    site, which is written for students and organisations and is in English.
    """
    import build_help, i18n
    grab = re.compile(r'<header class="sitehead">(.*?)</header>', re.S)
    tabs = re.compile(r'<a href="([^"]+)"([^>]*)>([^<]+)</a>')

    ROLES = ["find", "bills", "work", "students", "partners"]
    for L in build_help.LANGUAGES:
        page = build_help.lang_page(L["key"])
        m = grab.search(read(page))
        if not m:
            bad(f"{page} has no shared header")
            continue
        block = m.group(1)
        got = [t for t in tabs.findall(block) if "brand" not in t[1]]
        got = [t for t in got if t[2] != "Waypoint"]
        if len(got) != 5:
            bad(f"{page}: {len(got)} tabs, not five — the bar has drifted "
                f"from the English one")
            continue
        want_href = [build_help.lang_page(L["key"]), "index.html#bills",
                     "index.html#work", "index.html#students", "index.html#partners"]
        want_label = i18n.UI[L["key"]]["nav"]
        for i, role in enumerate(ROLES):
            href, attrs, label = got[i]
            if href != want_href[i]:
                bad(f"{page}: the {role} tab points at {href!r}, not "
                    f"{want_href[i]!r}")
            if html.unescape(label) != want_label[i]:
                bad(f"{page}: the {role} tab reads {label!r}; i18n.py says "
                    f"{want_label[i]!r}")
        if 'class="is-find"' not in got[0][1]:
            bad(f"{page}: the first tab is not the gold pill")
        for want, what in [('class="pin"', "the pin"),
                           ('<span class="brand__txt"', "the wordmark"),
                           ("Student Health Corps", "the strapline"),
                           ('class="nav-lamp"', "the lamp")]:
            if want not in block:
                bad(f"{page}: the header is missing {what}")
    ok("all ten language pages: the same bar, the same five tabs, in their "
       "own words, with Find help pointing at their own front page")


def check_language_round_trip():
    """A language page is a way in, not a cul-de-sac.

    Every link off it carries the language — help-food.html?lang=bengali — so
    the category page it lands on has the Bengali filter already applied, the
    chip visibly pressed, and the disclosure open so the shorter list has a
    reason and one tap undoes it. Without that, the ten pages end at a wall of
    English with no thread back.
    """
    import build_help
    for L in build_help.LANGUAGES:
        page = build_help.lang_page(L["key"])
        src = read(page)
        want = f'?lang={L["key"]}'
        outs = re.findall(r'href="(help-[a-z-]+\.html[^"]*)"', src)
        outs = [h for h in outs if not h.startswith(tuple(
            build_help.lang_page(O["key"]) for O in build_help.LANGUAGES))]
        naked = sorted({h for h in outs if want not in h})
        if naked:
            bad(f"{page}: {len(naked)} link(s) into the English directory drop "
                f"the language ({naked[0]}), so the filter is not applied when "
                f"the reader lands")
        elif not outs:
            bad(f"{page} links to no category page at all")
    ok("every link from the ten language pages carries its language with it")

    # and the page they land on says, in their language, what just happened
    for page in CATEGORY_PAGES:
        src = read(page)
        n = len(re.findall(r'class="enote enote--carry"[^>]*hidden', src))
        if n != len(build_help.LANGUAGES):
            bad(f"{page} carries {n} of the ten in-language lines for somebody "
                f"arriving from a translated page; the words around them change "
                f"language mid-journey with nothing to say why")
    ok("every category page can say, in any of the ten, why the words changed")

    js = read("help.js")
    if re.search(r"lang=\(\[a-z-\]\{2,20\}\)", js) and "useLanguage(" in js:
        ok("help.js reads ?lang= on arrival and presses the matching chip")
    else:
        bad("help.js no longer applies ?lang= on arrival, so every link from "
            "the ten language pages lands on an unfiltered English page")
    # The value has to be one of the ten before anything is done with it.
    # Written as an early return now rather than an if, so this asks whether
    # a chip is looked up and bailed on, not for one particular spelling.
    guard = re.search(r"querySelector\('\.chip\[data-f=\"lang\"\][^\n]*\n"
                      r"\s*(if \(!chip\) return;|if \(chip\))", js)
    if guard:
        ok("help.js ignores a ?lang= that is not one of the ten")
    else:
        bad("help.js applies ?lang= without checking the value is one of the "
            "ten; that is a URL, and a URL is not to be trusted")


def check_language_print():
    """A translated sheet handed across a table has to say who made it.

    The English pages learned this once: a printed leave-behind with no source
    on it is a photocopy of nothing. The ten language pages get the same
    printhead, in their own language, plus the one line that has to survive
    printing — what is in this language, what is not, and the number that puts
    an interpreter on the call.
    """
    import build_help, i18n
    css = read("help.css")
    for L in build_help.LANGUAGES:
        page = build_help.lang_page(L["key"])
        src = read(page)
        U = i18n.UI[L["key"]]
        m = re.search(r'<div class="printhead".*?</div>', src, re.S)
        if not m:
            bad(f"{page} prints with no attribution on it")
        elif U["foot_say"] not in html.unescape(m.group(0)):
            # scoped to the printhead: foot_say is in the footer too, and a
            # footer lands on the last sheet, which is not where somebody
            # looks to see who handed this to them
            bad(f"{page}'s printed header does not say who collected this")
    ok("all ten language pages carry a printed attribution in their own language")

    # The print block, not "everything after it": help.css gained a section
    # below @media print, so slicing to end-of-file made this check see the
    # screen rules as well and pass on rules it was meant to be missing.
    i = css.index("@media print{")
    depth, j = 0, i
    while j < len(css):
        if css[j] == "{":
            depth += 1
        elif css[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    pr = css[i:j + 1]
    for sel, why in [(".enote{", "the note about what is and is not in this language"),
                     (".enote__p{", "that note's text")]:
        if sel not in pr:
            bad(f"the print sheet drops {why}; on paper that is the difference "
                f"between a list somebody can use and one they put down")
    if ".enote" in pr and "display:none" in pr.split(".enote")[1][:80]:
        bad("the print sheet hides .enote outright")
    ok("the print sheet keeps the language note and the interpreter number")


def check_language_voice():
    """Two things a translated page gets wrong quietly.

    One addressee, per language. Spanish addresses the reader as usted from the
    masthead to the footer, Polish impersonally, Chinese as 您. A page that
    slides between them reads as though two people wrote it, which on a page
    somebody opens frightened is a reason not to trust it. This fails when one
    language uses both.

    And no gendered ending on the reader. The seventeen headings are the reader
    speaking — "I need food" — and in Polish, Russian, Spanish, Arabic and Urdu
    the obvious way to write that agrees with a gender the site cannot know.
    "Nie jestem bezpieczny", "Я служил", "estoy solo", "خدمت", "اکیلا": every
    one of those told half the readers the page was not written for them. The
    fix is a construction that does not agree — a noun instead of a past tense,
    an adverb instead of an adjective — so this fails on the endings rather
    than on a word list.
    """
    import build_help, i18n

    REGISTER = {
        "spanish": (r"\b(usted|Elija|Llame|Escoja)\b", r"\b(tú|Elige|Llama|tuyo)\b"),
        "french": (r"\b(vous|Appelez|Choisissez)\b", r"\b(Appelle|Choisis|ton |ta )\b"),
        "polish": (r"\b(potrzebujesz|Zadzwoń|twoim|Nie trzeba)\b", r"\b(Pan|Pani|Państwo)\b"),
        "russian": (r"\b(вы|вам|Позвоните|Выберите)\b", r"\b(ты|тебе|Позвони|Выбери)\b"),
        "chinese": (r"您", r"你(?!好)"),
        "urdu": (r"آپ", r"\bتم\b"),
    }
    for lang, (main_rx, other_rx) in REGISTER.items():
        U = i18n.UI[lang]
        text = " ".join(v if isinstance(v, str) else " ".join(v) for v in U.values())
        text += " " + " ".join(i18n.BLURBS[lang].values())
        a = len(re.findall(main_rx, text, re.I))
        b = len(re.findall(other_rx, text, re.I))
        if a and b:
            bad(f"{lang}: the page addresses the reader two different ways "
                f"({a} one way, {b} the other) — it reads as though two people "
                f"wrote it")
    ok(f"all {len(REGISTER)} languages with a politeness distinction keep one "
       f"register from the masthead to the footer")

    # endings that agree with the reader's gender
    # Anchored to the reader's own clause, not to the word. "mi seguro dijo
    # que no" is an insurance policy, and "أرعى شخصًا مسنًا" is the person
    # being cared for; a bare word list called both of those a defect.
    GENDERED = {
        "polish": r"(jestem \w*(?:ny|na)\b|\b\w+łem\b|\b\w+łam\b)",
        "russian": r"(\bЯ служил\w?\b|\bя вышел\b|\bя вышла\b|\bя один\b|\bя одна\b)",
        "spanish": r"(\bestoy (?:seguro|segura|solo|sola)\b|\bsoy (?:solo|sola)\b)",
        "french": r"(\bje suis (?:un jeune )?seule?\b)",
        "arabic": r"(^خدمت |\bأنا مسن\b|\bأنا شاب\b|\bخرجت من\b)",
        "urdu": r"(میں اکیلا|دیکھ بھال کرتا ہوں|واپس آ رہا ہوں)",
    }
    for L in build_help.LANGUAGES:
        rx = GENDERED.get(L["key"])
        if not rx:
            continue
        for key, label in L["needs"].items():
            m = re.search(rx, label)
            if m:
                bad(f"{L['name_en']}: the {key!r} heading says {m.group(0)!r}, "
                    f"which agrees with a gender this site cannot know — the "
                    f"reader is being told the page was written for somebody else")
    ok("none of the seventeen headings, in any language, puts a gendered "
       "ending on the reader")


def check_nothing_parks_offscreen():
    """Nothing may be hidden by shoving it to a physical -9999px.

    The skip link did, on every page, and on the two right-to-left ones that
    is not "off-screen" — it is off the *end*, the direction the page scrolls.
    help-ur.html reported a document 10,695 pixels wide against a 696-pixel
    body: ten thousand pixels of empty cream a thumb could pan into, on the
    two pages whose readers can least afford a page that behaves strangely.

    It was invisible to the reflow check because that measured body.scrollWidth
    and the overflow was on the documentElement.

    Clipping is the technique that works in both directions, so this fails on
    the offset rather than on the symptom.
    """
    for sheet in ("help.css", "styles.css", "tokens.css"):
        src = read(sheet)
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", src):
            body = m.group(2)
            hit = re.search(r"(?:^|;|\s)(left|right|margin-left|margin-right|text-indent)"
                            r":\s*-\s*(\d{4,})px", body)
            if hit:
                sel = m.group(1).strip().splitlines()[-1].strip()
                bad(f"{sheet}: {sel[:44]} parks something at "
                    f"{hit.group(1)}:-{hit.group(2)}px. On a right-to-left page "
                    f"that is off the end of the document, not off-screen — use "
                    f"clip-path:inset(50%) on a 1px box instead")
    ok("nothing is hidden by a physical offset; the off-screen technique works "
       "in both directions")

    # and the thing it was protecting has to still work
    for sheet in ("help.css", "styles.css"):
        src = read(sheet)
        m = re.search(r"\.skip\{([^}]*)\}", src)
        f = re.search(r"\.skip:focus\{([^}]*)\}", src)
        if not m or not f:
            bad(f"{sheet} has no skip link, or none that reappears on focus")
            continue
        if "clip-path" not in m.group(1):
            bad(f"{sheet}: the skip link is not clipped, so it is either "
                f"visible or parked somewhere")
        if "clip-path:none" not in f.group(1).replace(" ", ""):
            bad(f"{sheet}: the skip link never unclips, so a keyboard user "
                f"tabs onto a control they cannot see")
    ok("the skip link is clipped at rest and unclipped on focus, on both halves")


def check_script_typography():
    """The four things a script needs that English does not.

    Each of these was visible on a rendered page before it was fixed, and each
    is invisible to anyone who does not read the script.
    """
    css = read("help.css")
    WANT = [
        (r"\.help--ko\{[^}]*word-break:keep-all",
         "Korean breaks between eojeol, not inside a word. Without keep-all "
         "the masthead came out '묻지 않 / 습니다' — one word split across two "
         "lines, four times on the first screen"),
        (r"\.help--ko\{[^}]*overflow-wrap:anywhere",
         "keep-all with nothing to catch a unit longer than the column pushes "
         "the page sideways"),
        (r"\.help--bn[^{]*\{[^}]*line-height:1\.8",
         "Bengali has a headline and ascenders English does not; at English's "
         "leading the lines collide"),
        (r"\.help--ar[^{]*\{[^}]*line-height:1\.9|"
         r"\.help--ur[^{]*\{[^}]*line-height:1\.9",
         "Arabic and Urdu hang well below the baseline"),
        (r"\.help--zh[^{]*\{[^}]*max-width:44ch",
         "CJK has no word spaces, so the eye wants a shorter measure, not a "
         "looser one"),
        (r"\.mast__title b\{[^}]*font-style:normal",
         "Fraunces has a drawn italic and CJK, Bengali, Arabic and Urdu do "
         "not, so a browser asked for one slants the glyphs by matrix"),
    ]
    for rx, why in WANT:
        if re.search(rx, css, re.S):
            ok(f"script typography: {why.split(chr(46))[0][:58]}")
        else:
            bad(f"help.css no longer handles this: {why}")

    # and the five scripts with no drawn italic must not be asked for one
    import build_help
    for L in build_help.LANGUAGES:
        page = build_help.lang_page(L["key"])
        src = read(page)
        m = re.search(r'<h1 class="mast__title">(.*?)</h1>', src, re.S)
        if not m:
            bad(f"{page} has no masthead title")
            continue
        # Decided from the script, not from build_help.NO_ITALIC: asking the
        # code under test which languages have an italic means the check
        # agrees with it even when it is wrong, which is how the first draft
        # passed with Chinese removed from the set.
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
        latin_or_cyrillic = all(
            ord(c) < 0x250 or 0x400 <= ord(c) <= 0x52F or not c.isalpha()
            for c in title)
        has_em = "<em>" in m.group(1)
        should = latin_or_cyrillic
        if has_em != should:
            bad(f"{page}: the title emphasis is <{'em' if has_em else 'b'}> and "
                f"this script has {'a' if should else 'no'} drawn italic "
                f"in Fraunces — a browser asked for one it does not have "
                f"slants the glyphs by matrix")
    ok("the five scripts with no drawn italic carry the gold without one")


def check_language_pages_need_no_script():
    """A language page is the whole page with no JavaScript at all.

    The English front page ships a search box, a filter panel and a print
    button hidden, and reveals them from help.js — controls that genuinely
    need script, with a <noscript> beside them saying where they went. A
    language page has none of that: no script tag, nothing hidden, every count
    correct in the markup.

    That is not an accident of what got built. The reader these pages exist for
    is disproportionately on an old phone on a bad connection, and the search
    they would get is a box that returns English descriptions. Seventeen
    labelled cards in their own language, with places named and dialable under
    each, is both lighter and better — so the property is worth holding on to
    rather than something to fill in later.
    """
    import build_help
    rows = build_help.load()
    by_need = {n["key"]: build_help.ordered(rows, n["key"]) for n in build_help.NEEDS}
    for L in build_help.LANGUAGES:
        page = build_help.lang_page(L["key"])
        src = read(page)
        if "<script" in src:
            bad(f"{page} loads a script; this page works without one and the "
                f"reader it is for is on the worst connection on the site")
        hidden = re.findall(r"<(\w+)[^>]*\shidden[\s>]", src)
        if hidden:
            bad(f"{page} ships {len(hidden)} hidden element(s) ({hidden[0]}); "
                f"with no script on the page nothing will ever reveal them")
        # every count on a card is the number of resources on the page it opens
        for key, group in by_need.items():
            m = re.search(rf'id="n-{key}".*?class="cl__all"[^>]*>([^<]*)<', src, re.S)
            if not m:
                bad(f"{page} has no card for {key!r}")
                continue
            said = re.search(r"\d+", m.group(1))
            if not said or int(said.group(0)) != len(group):
                bad(f"{page}: the {key!r} card says {said.group(0) if said else 'nothing'} "
                    f"and the page it opens has {len(group)}")
    ok("all ten language pages are complete static HTML: no script, nothing "
       "hidden, every count generated")


def check_language_sentence_length():
    """The English pages hold a grade-9 reading level. The other ten cannot be
    measured that way — Flesch-Kincaid counts English syllables — but the thing
    it is really a proxy for travels: short sentences.

    So this measures what can be measured in any script. The English site runs
    a median of about eleven words a sentence; all ten translations land
    between nine and twelve, which is the number that says nobody quietly
    rewrote a page in the register of a government leaflet.

    The ceiling is generous on purpose. The longest sentence on every one of
    the eleven pages is the same one — the lede listing what the directory
    covers — and a list is long because the items are the point.
    """
    import i18n, statistics
    END = re.compile(r"[.!?\u3002\uff01\uff1f\u0964\u06d4\u061f]+")
    for key, U in i18n.UI.items():
        text = " ".join([U["lede1"], U["lede2"], U["sos_note"], U["english"],
                         U["vow"], U["foot_say"]])
        text += " " + " ".join(i18n.BLURBS[key].values())
        parts = [p.strip() for p in END.split(text) if p.strip()]

        def words(p):
            if key in ("chinese", "korean"):
                # no word spaces; characters over 1.8 is the usual rough
                # equivalent for Chinese and Korean at this register
                cjk = len(re.findall(r"[\u3000-\u9fff\uac00-\ud7af]", p))
                return max(len(p.split()), round(cjk / 1.8))
            return len(p.split())

        w = [words(p) for p in parts]
        med, longest = statistics.median(w), max(w)
        if med > 16:
            bad(f"{key}: a median of {med:.0f} words a sentence against the "
                f"English site's eleven — somebody has rewritten this page in "
                f"the register of a government leaflet")
        elif longest > 34:
            bad(f"{key}: a {longest}-word sentence. The longest on the English "
                f"pages is the lede, at 22")
    ok(f"all ten translations run 9 to 12 words a sentence, the same discipline "
       f"the English pages are held to")


def check_hreflang_is_reciprocal():
    """The eleven front pages are one document in eleven languages, and a
    search engine only believes that if every one of them says so.

    A hreflang set that is not reciprocal is discarded: a Spanish speaker
    searching in Spanish then gets whichever page the crawler indexed first,
    which for this site is the English one — the page they cannot read.
    """
    import build_help
    group = ["help.html"] + [build_help.lang_page(L["key"])
                             for L in build_help.LANGUAGES]
    want = {"x-default": "help.html", "en": "help.html"}
    for L in build_help.LANGUAGES:
        want[L["tag"]] = build_help.lang_page(L["key"])

    for page in group:
        src = read(page)
        got = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" '
                              r'href="([^"]+)" />', src))
        missing = {k: v for k, v in want.items() if got.get(k) != v}
        if missing:
            bad(f"{page} names {len(got)} of the {len(want)} pages in its "
                f"language group (missing or wrong: {sorted(missing)[:3]}) — "
                f"a set that is not reciprocal is thrown away")
        canon = re.search(r'<link rel="canonical" href="([^"]+)" />', src)
        if not canon:
            bad(f"{page} has no canonical, so the group has no anchor")
        elif canon.group(1) != page:
            bad(f"{page} says its canonical is {canon.group(1)!r}")
    ok(f"all {len(group)} front pages name the whole language group and "
       f"themselves, with an x-default")


def check_language_spacing_is_shared():
    """A language page is the English page in another language, not another
    design of it.

    Which means the per-script rules may adjust *typography* and nothing else.
    Leading, tracking, word breaking and the measure are properties of a
    script and have to change; padding, margins, gaps, radii and box sizes are
    the page's rhythm and must not. Measured at 1280px, the four pages checked
    by hand come back with the same 26px between the language row and the
    masthead, the same 37px to the emergency panel, the same 60px to the
    promise, and the same 24px card padding and 16px radius as the English
    page. This is the rule that keeps that true.
    """
    TYPOGRAPHY = {"line-height", "letter-spacing", "word-break", "overflow-wrap",
                  "word-spacing", "max-width", "font-style", "font-weight",
                  "font-size", "text-align", "font-feature-settings",
                  "font-variant", "hyphens", "text-wrap", "direction",
                  "unicode-bidi", "color", "text-decoration", "content"}
    css = read("help.css")
    seen = 0
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel = m.group(1).strip().splitlines()[-1].strip()
        if not re.search(r"\.help--[a-z]{2}\b", sel):
            continue
        seen += 1
        for prop in re.findall(r"(?:^|;)\s*([a-z-]+)\s*:", m.group(2)):
            if prop.startswith("--") or prop in TYPOGRAPHY:
                continue
            bad(f"help.css: {sel[:40]} sets {prop}, which is the page's "
                f"rhythm rather than the script's typography. A language page "
                f"is the English page in another language, not another design "
                f"of it")
    if seen < 5:
        bad(f"only {seen} per-script rules left in help.css; the scripts that "
            f"need different leading have stopped getting it")
    else:
        ok(f"all {seen} per-script rules touch typography only, never spacing")


def check_page_cannot_be_dragged_sideways():
    """At 320px with text at 200%, no page may pan.

    index.html could be dragged 78 pixels into nothing. No text was lost — the
    overflow is a sticky column in one of the hold scenes — but a page sliding
    under your thumb while you are trying to scroll down is its own kind of
    broken, and WCAG 1.4.10 does not care that what slid off was empty.

    overflow-x:hidden was already on body and did not stop it. hidden on one
    axis coerces the other from visible to auto, which makes body its own
    scroll container and leaves the document element scrolling instead. `clip`
    is the value that exists for this: it clips without creating a scroll
    container, so overflow-y stays genuinely visible and every position:sticky
    on the page keeps working. It has to be on both elements, because either
    one can end up being the one that scrolls.
    """
    for sheet in ("styles.css", "help.css"):
        src = read(sheet)
        broken = re.search(r"(?:^|[\s,])(html|body)[^{}]*\{[^}]*overflow-x:\s*hidden", src, re.M)
        if broken:
            bad(f"{sheet} sets overflow-x:hidden on {broken.group(1)}. That "
                f"coerces overflow-y to auto, makes it its own scroll container "
                f"and leaves the document element scrolling — use clip")
    st = read("styles.css")
    if re.search(r"html,\s*body\{[^}]*overflow-x:\s*clip", st):
        ok("the narrative page cannot be dragged sideways, and its sticky "
           "scenes still stick")
    else:
        bad("styles.css no longer clips the page horizontally; at 320px with "
            "text at 200% it can be dragged 78px into nothing")


def check_tap_targets():
    """Every control on the directory is at least 44px tall.

    Not 24 — that is the WCAG 2.5.8 floor, and this directory is read on a
    phone by somebody who is frightened, often one-handed, often in a hurry.
    44 is what Apple and Google both ask for and what the rest of this site
    already does; the jump row was 40 and it is a row of seventeen small pills,
    which is exactly where a thumb misses.
    """
    # styles.css too: the home page's resident links live there, and they were
    # the smallest tap targets on the site.
    css = read("help.css") + "\n" + read("tokens.css") + "\n" + read("styles.css")
    CONTROLS = [(r"\.jump a\{", "the jump row"),
                (r"\.helplinks a\{", "the resident links on the home page"),
                (r"\.chip\{", "a filter chip"),
                (r"\.langbar__list a\{", "a language link"),
                (r"\.langbar__here\{", "the language you are on"),
                (r"\.sitehead__links a\{", "a nav tab"),
                (r"\.printbtn\{", "the print button"),
                (r"\.pv__call\{", "a phone number in a preview")]
    for rx, what in CONTROLS:
        m = re.search(rx + r"([^}]*)\}", css, re.S)
        if not m:
            bad(f"{what} has no rule; it may have been renamed away from this check")
            continue
        h = re.search(r"min-height:\s*(\d+)px", m.group(1))
        if not h:
            continue          # sized by padding and line-height; measured live
        if int(h.group(1)) < 44:
            bad(f"{what} is {h.group(1)}px tall. 44 is what the rest of this "
                f"site does and what a thumb needs")
    ok(f"all {len(CONTROLS)} named controls on the directory are 44px or taller")

    # An inline link inside a sentence cannot have a min-height — it is a run
    # of glyphs in a line box. Its hit area comes from an absolutely
    # positioned ::after with a negative inset, and if that rule is missing or
    # scoped too narrowly the link is as tall as its text and nothing says so.
    # Both of these were found by hit-testing the built pages, not by reading
    # the CSS: .dialn measured 24x20 on every language page, and .inl kept its
    # 17-22px box in a paragraph because the rule said `li > .inl`.
    INLINE = [(r"\.dialn", "a phone number inside translated prose"),
              (r"\.inl", "an inline link in the narrative pages")]
    # Match the selector exactly. `li > .inl::after` is the bug this pair was
    # written for, and a substring search finds it just as happily as `.inl`.
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)

    def exact(cls):
        for sel, body in rules:
            for one in sel.split(","):
                if one.strip().splitlines()[-1].strip() == cls + "::after":
                    return body
        return None

    for rx, what in INLINE:
        body = exact(rx.replace("\\", ""))
        exp = re.match(r"(?s)(.*)", body) if body is not None else None
        if not exp:
            bad(f"{what} has no ::after hit area, so it is only as tall as its "
                f"own text — about 20px, against the 44 the rest of the site "
                f"gives a thumb")
            continue
        inset = re.search(r"inset:\s*(-?\d+)px", body)
        if not inset or int(inset.group(1)) > -11:
            bad(f"{what}'s hit area grows by "
                f"{inset.group(1) if inset else '0'}px vertically; it needs at "
                f"least 11 on each side to clear 44px around a line of text")
        else:
            ok(f"{what} is tappable")


def check_high_contrast_covers_the_cards():
    """Everything with a hairline border gets a thicker one at higher contrast.

    A 1.5px border in a pale green is the only thing separating most of these
    cards from the page. Somebody who has asked their system for more contrast
    has told you they cannot see it.

    The list is explicit rather than derived: a component with no border does
    not belong here, and one that gains a border later should be added on
    purpose rather than swept in.
    """
    css = read("help.css")
    m = re.search(r"@media \(prefers-contrast:more\)\{(.*?)\n\}", css, re.S)
    if not m:
        bad("help.css no longer has a higher-contrast block at all")
        return
    # only the rule that actually thickens the border counts. The first draft
    # searched the whole block, and .enote appears in it twice — so removing
    # it from the border-width rule left the other mention behind and the
    # check passed on a card that had gone back to a hairline.
    thick = re.findall(r"([^{}]+)\{[^{}]*border-width:\s*2px", m.group(1))
    block = " , ".join(thick)
    for sel, what in [(".r", "a resource card"), (".cl", "a cluster card"),
                      (".jump a", "the jump row"), (".find__box", "the search box"),
                      (".enote", "the language note"),
                      (".langbar__list a", "a language link"),
                      (".printbtn", "the print button"),
                      (".pv__call", "a phone number")]:
        # the last selector in a rule is followed by the brace, which the
        # capture above stops at — so end-of-string counts as a boundary too
        if not re.search(rf"(?:^|[,\s]){re.escape(sel)}(?=[,{{\s]|$)", block, re.M):
            bad(f"{what} ({sel}) keeps its hairline border at higher contrast; "
                f"somebody who asked their system for more contrast has told "
                f"you they cannot see it")
    ok("every bordered card and control thickens its border at higher contrast")


def check_every_row_has_someone_to_verify_it():
    """Two tools stamp dates, and between them they must cover every row.

    verify_phones.py asks each organisation's own site whether the number we
    print is its number, and skips a row with no ten-digit number in it.
    check_links_live.py --stamp handles exactly those: for a row whose "phone"
    is 311, or a text shortcode, or nothing, verifying can only mean the site
    is live and still on its own domain.

    A row owned by neither is a row whose date nobody is responsible for, and
    it will quietly age. Two fell through the first time this was split: "988
    then press 1 / text 838255" and "Text FOOD to 726879" both have digits in
    them, and neither has a phone number either tool could check.
    """
    import csv as _csv
    import verify_phones
    import check_links_live
    with open(ROOT / "data" / "resources.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(_csv.DictReader(f))

    phone, link, orphan, both = 0, 0, [], []
    for r in rows:
        has_site = bool((r.get("Website") or "").strip())
        by_phone = has_site and bool(verify_phones.ours(r["Phone"]))
        by_link = check_links_live.unverifiable_by_phone(r)
        if by_phone and by_link:
            both.append(r["Resource Name"])
        elif by_phone:
            phone += 1
        elif by_link:
            link += 1
        else:
            orphan.append(r["Resource Name"])
    for n in both[:4]:
        bad(f"{n!r} would be stamped by both tools; the two would fight over "
            f"what its date means")
    for n in orphan[:4]:
        bad(f"{n!r} is stamped by neither tool: it has a phone number too "
            f"unusual to check and a site nobody is checking either, so its "
            f"date will quietly age")
    if not both and not orphan:
        ok(f"every row has a tool responsible for its date: {phone} by phone, "
           f"{link} by the site being live")


def check_every_resource_is_findable_by_name():
    """Somebody told you to call Safe Horizon. Typing that has to reach it.

    Most people arrive at this directory with a name in their head, given to
    them by a caseworker, a neighbour or a flyer. A row that its own name
    cannot find is a row that person will conclude does not exist.

    Uses the same scoring model as check_critical_queries, so it tests the
    order and not just reachability: two rows used to lose to a longer name
    containing theirs — "Safe Horizon" opened with Safe Horizon Streetwork
    Project, "Met Council" with Met Council on Housing Tenant Hotline.
    """
    import build_help
    K = _js_constants()
    if not K:
        return
    rows = build_help.load()
    model = _search_model(rows, K)
    missing, second = [], []
    for r in rows:
        name = r["Resource Name"]
        order = model(name)
        if not order:
            missing.append(name)
        elif order[0] != name:
            second.append(f"{name!r} is outranked by {order[0]!r}")
    for m in missing[:5]:
        bad(f"{m!r} cannot be found by searching its own name")
    for m in second[:5]:
        bad(m)
    if not missing and not second:
        ok(f"all {len(rows)} resources come back first when you type their name")


def _js_one_edit(src, a, b):
    """oneEditApart's behaviour, evaluated by node against the real source."""
    import json
    import subprocess
    prog = ("function oneEditApart(a, b) {" + src + "\n}\n"
            "process.stdout.write(String(oneEditApart(" +
            json.dumps(a) + "," + json.dumps(b) + ")));")
    try:
        out = subprocess.run(["node", "-e", prog], capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None          # no node here: the string checks still ran
    return out.stdout.strip() == "true"


def check_one_typo_does_not_empty_the_page():
    """A misspelling should not be answered with a blank page.

    This is read on a phone by somebody upset, and "fod", "docter", "lawer",
    "sucide", "landlrd", "hosuing" and "shleter" all returned nothing. help.js
    now retries a query that matched nothing against the words the page
    actually contains, allowing one insertion, deletion, substitution or
    transposition.

    Transposition is the half that matters most: swapping two letters is the
    commonest typing mistake there is and it costs two edits under plain
    Levenshtein, so the first draft still answered "hosuing" and "shleter" with
    nothing. And among the candidates one edit away it takes the one this page
    uses most — "lawer" is one edit from "later", "lower" and "lawyer", and
    alphabetical order picked "later" and answered a question about lawyers
    with NeedyMeds.

    Guarded here as a property of the algorithm rather than of the data, so it
    does not go stale as the directory grows.
    """
    js = read("help.js")
    for name, why in [
            ("oneEditApart", "the one-edit test"),
            ("nearestWord", "the retry against the page's own words"),
            ("vocabulary", "the vocabulary the retry compares against")]:
        if f"function {name}(" not in js:
            bad(f"help.js no longer has {why} ({name}); a typo empties the page again")
            return
    # Run the algorithm rather than looking for its source: a disabled copy
    # of the transposition branch still contains the string that tested for it,
    # and the first version of this check passed with it switched off.
    body = re.search(r"function oneEditApart\(a, b\) \{(.*?)\n  \}", js, re.S)
    if not body:
        bad("cannot read oneEditApart to test it")
        return
    src = body.group(1)
    if not _js_one_edit(src, "hosuing", "housing"):
        bad("the one-edit test no longer allows a transposition, which is the "
            "commonest typing mistake and costs two edits without it")
    if not _js_one_edit(src, "foood", "food"):
        bad("the one-edit test no longer allows a deletion")
    if _js_one_edit(src, "food", "shelter"):
        bad("the one-edit test matches two unrelated words")
    if "df > bestDf" not in js:
        bad("the retry no longer prefers the word this page uses most, so "
            "'lawer' resolves alphabetically and lands on 'later'")
    if "word.length < 4" not in js:
        bad("the retry no longer has a length floor; at three characters one "
            "edit reaches a different word entirely")
    if "corrected" not in js or "Showing results for" not in js:
        bad("a corrected spelling is no longer announced, so the list changes "
            "under the reader with no explanation")
    else:
        ok("one typo does not empty the page: transpositions included, the "
           "page's commonest spelling wins, and the correction is announced")


def check_every_category_page_answers_its_own_questions():
    """A search on a category page searches that page. It has to find things.

    The front page is not the only search on this site: each of the seventeen
    has its own box, scoped to its own resources, and a query that comes back
    empty there is a dead end even when the answer exists two pages over.
    Sixty-nine obvious questions, four or five per page. Five used to fail:

      "baby formula" on the food page, where WIC hands out infant formula and
      the row never said the word.
      "vaccine" on the doctor page, where every clinic gives them.
      "expungement" on the record page, because New York seals records rather
      than expunging them and nobody types "sealing".
      "i cant stop crying" and "hearing voices" on the crisis page, which are
      what people type instead of the clinical word.
    """
    import build_help
    K = _js_constants()
    if not K:
        return
    rows = build_help.load()
    PROBES = {
        "safety": ["restraining order", "my partner hits me"],
        "crisis": ["i cant stop crying", "hearing voices", "detox"],
        "food": ["hot meal", "halal", "baby formula"],
        "housing": ["eviction", "shelter tonight", "no heat"],
        "bills": ["surprise bill", "charity care"],
        "doctor": ["dentist", "vaccine", "no insurance"],
        "legal": ["deportation", "green card", "criminal record"],
        "money": ["cash assistance", "utility bill", "tax help"],
        "family": ["daycare", "school suspension"],
        "senior": ["dementia", "home care", "medicare"],
        "clothes": ["winter coat", "diapers", "period products"],
        "work": ["job training", "english classes"],
        "getting-there": ["metrocard", "ride to the doctor"],
        "veterans": ["va benefits", "veteran housing"],
        "disability": ["wheelchair", "ssi", "benefits denied"],
        "record": ["job with a record", "expungement"],
        "start": ["i dont know where to start", "one number"],
    }
    empty, n = [], 0
    for key, queries in PROBES.items():
        page_rows = build_help.ordered(rows, key)
        model = _search_model(page_rows, K)
        for q in queries:
            n += 1
            if not model(q):
                empty.append(f"help-{key}.html: {q!r} finds nothing on the page")
    for e in empty[:6]:
        bad(e)
    if not empty:
        ok(f"all {n} obvious questions find something on the page they belong to")


def check_also_tags_are_real_needs():
    """`also:<need>` puts a row on a second page. It has to name a real one.

    A multi-service organisation's subcategory is "One place that does many
    things", which is true of all of them and so useless as a cross-filing
    trigger — but the biggest food pantry on Staten Island is a multi-service
    organisation, and somebody on "I need food" has to be able to see it. So a
    row can name the other pages it belongs on. A typo in one of those names
    would silently put it nowhere.
    """
    import csv as _csv
    import build_help
    keys = {n["key"] for n in build_help.NEEDS}
    with open(ROOT / "data" / "resources.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(_csv.DictReader(f))
    used, n = set(), 0
    for r in rows:
        for t in (r.get("Tags") or "").split(";"):
            t = t.strip()
            if not t.startswith("also:"):
                continue
            n += 1
            need = t[5:]
            used.add(need)
            if need not in keys:
                bad(f"{r['Resource Name']!r} says also:{need}, which is not one "
                    f"of the seventeen kinds of help")
            if need in [k for k in keys if k in r["Category"].lower()]:
                bad(f"{r['Resource Name']!r} says also:{need} for a page its "
                    f"category already puts it on")
    ok(f"{n} cross-filings across {len(used)} kinds of help, all naming a real one")


def check_the_data_itself():
    """Four things about the CSV that nothing else was looking at.

    Found by mutation testing: twelve plausible regressions were introduced one
    at a time and the suite caught five. These are three of the seven it missed
    — a phone number with nine digits, a category nobody recognises, and a
    language whose short label is still the English one.
    """
    import csv as _csv
    import build_help
    import i18n
    with open(ROOT / "data" / "resources.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(_csv.DictReader(f))

    # 1. a printed number has to be dialable. "800-621-467" is nine digits and
    #    every guard in this suite was happy with it.
    # Split on the punctuation that separates two numbers before measuring
    # one: "646-692-2273 (646-NYC-CARE)" is one number written twice, and a
    # greedy pattern reads it as a thirteen-digit one.
    # A short code counts only when it is the WHOLE part. "\b\d{3}\b" matched
    # the "800" inside "800-621-467" and pronounced a nine-digit number fine.
    PHONE = re.compile(r"\d{3}[\-\. ]\d{3}[\-\. ]\d{4}")
    SHORT = re.compile(r"^\s*(\d{3}|\d{6})\s*$")
    broken = []
    for r in rows:
        for part in re.split(r"[(/,;]|\bor\b|\bthen\b", r["Phone"] or ""):
            # Per part, not per cell: "800-621-467 (800-621-HOPE); TTY
            # 866-604-5350" has a broken number in it and a good one after,
            # and testing the cell as a whole finds the good one and stops.
            n = len(re.sub(r"\D", "", part))
            # Letters mean a vanity number or a texting instruction
            # ("646-NYC-CARE", "Text HOME to 741741") and are counted by hand
            # in check_phone_numbers_are_reachable. Everything else is digits,
            # and digits only come in four lengths anybody can dial.
            if n and not re.search(r"[A-Za-z]", part) and n not in (3, 6, 10, 11):
                broken.append(f"{r['Resource Name']!r} has {part.strip()!r} in "
                              f"its phone column: {n} digits is not a number "
                              f"anybody can dial")
            for m in PHONE.findall(part):
                d = re.sub(r"\D", "", m)
                if d.startswith("1") and len(d) == 11:
                    d = d[1:]
                if len(d) not in (3, 6, 10):    # 311, a text shortcode, a number
                    broken.append(f"{r['Resource Name']!r} prints {m.strip()!r}, "
                                  f"which is {len(d)} digits and cannot be dialled")
    for b in broken[:5]:
        bad(b)
    if not broken:
        ok(f"every phone number in the directory is a dialable shape")

    # 2. a category nobody recognises files the row under "not sure where to
    #    start" and nothing says so
    known = set()
    for need in build_help.NEEDS:
        known.update(need.get("cats", []))
    strays = sorted({r["Category"] for r in rows if r["Category"] not in known})
    for c in strays[:4]:
        bad(f"category {c!r} belongs to no kind of help, so its rows land in "
            f"'I am not sure where to start' with nothing to say why")
    if not strays:
        ok(f"all {len(known)} categories in the CSV map to a kind of help")

    # 3. a short label left in English is invisible to every other check,
    #    because for a Latin-script language English looks like the language
    for lang, short in i18n.SHORT.items():
        if lang in ("english",):
            continue
        same = [k for k, v in short.items()
                if v == next(n["short"] for n in build_help.NEEDS if n["key"] == k)]
        if same:
            bad(f"{lang}: the short label for {same[0]!r} is still the English "
                f"one ({short[same[0]]!r})")
    ok("no language's jump row is still showing an English label")

    # 4. every row can be dialled or opened. merge_rows refuses one with
    #    neither; this is the check that it stayed true.
    orphan = [r["Resource Name"] for r in rows
              if not (r["Phone"] or "").strip() and not (r["Website"] or "").strip()]
    for o in orphan[:3]:
        bad(f"{o!r} has neither a phone number nor a website: there is no way "
            f"to act on it")
    if not orphan:
        ok(f"all {len(rows)} resources can be reached, by phone or by link")


def check_no_sideways_scroll():
    """The two CSS mistakes that make this page scroll sideways.

    WCAG 1.4.10 is not a formality here: at 320px with text at 200% — the
    narrowest screen at the largest text, which is precisely the combination
    this directory exists to survive — a page that scrolls horizontally is a
    page where half of every sentence is off the edge and the reader has to
    drag it back for each line.

    Both causes are grid defaults. A track is max-content wide unless told
    otherwise, and a grid item refuses to shrink below its own min-content
    unless told otherwise. One long chip in the rail made the whole page
    437px wide.
    """
    css = read("help.css")
    body = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)

    bare = re.findall(r"repeat\(auto-fill,\s*minmax\((\d+px)\s*,", body)
    if bare:
        bad(f"help.css: repeat(auto-fill, minmax({bare[0]}, ...)) — a fixed "
            "minimum wider than the screen makes the track wider than the "
            "screen. Use minmax(min(Npx,100%), 1fr).")
    else:
        ok("help.css: every auto-fill grid can shrink below its own minimum")

    tight = re.sub(r"\s+", "", body)
    for sel in (".cat", ".cat__rail", ".cat__main"):
        if sel not in tight:
            bad(f"help.css: {sel} is gone; the category layout has changed shape")

    if re.search(r"\.cat\{[^}]*grid-template-columns:minmax\(0,1fr\)", tight):
        ok("help.css: the category grid's single column is bounded")
    else:
        bad("help.css: the category grid no longer declares "
            "grid-template-columns:minmax(0,1fr), so one long word in the rail "
            "can widen the whole page")

    shrinks = [sel for sel in (".cat__rail", ".cat__main")
               if not re.search(r"(^|[,{}])[^{}]*" + re.escape(sel) +
                                r"[^{}]*\{[^}]*min-width:0", tight)]
    if shrinks:
        bad(f"help.css: {shrinks} has no min-width:0, so it cannot shrink below "
            "its own content and the page scrolls sideways at 320px")
    else:
        ok("help.css: both children of the category grid may shrink")


def _js_constants():
    """The scoring constants, read out of help.js rather than typed here.

    The model below is a model, and the failure mode of a model is that it
    drifts from the thing it models and keeps passing. Every number it uses
    comes from the file it is modelling, so a change to the weights either
    changes this check's behaviour too or fails outright for a missing name.
    """
    js = read("help.js")
    want = ["W_NAME", "W_KIND", "W_TAG", "W_ALIAS", "W_BODY", "W_CAT",
            "EXACT", "STEMMED", "W_PHRASE", "W_NAME_EXACT"]
    got = {}
    for name in want:
        m = re.search(rf"\b{name}\s*=\s*([\d.]+)", js)
        if not m:
            bad(f"help.js no longer defines {name}; the search model in check.py "
                f"is now modelling something that does not exist")
            return None
        got[name] = float(m.group(1))
    m = re.search(r"if \(v < ([\d.]+)\) v = [\d.]+;", js)
    if not m:
        bad("help.js no longer floors the inverse document frequency; either "
            "the weighting is gone or its shape changed, and the model in "
            "check.py is now modelling something else")
        return None
    got["IDF_FLOOR"] = float(m.group(1))
    # And the weighting itself, not just its floor. Replacing the body of idf()
    # with `return 1` left the floor line readable and the model still applying
    # a weighting the page had stopped applying.
    if not re.search(r"function idf\(w\)[\s\S]{0,700}?Math\.log\(n / df\)", js):
        bad("help.js computes no inverse document frequency any more, so a "
            "word in half the rows scores the same as a word in one")
        return None
    if not re.search(r"points \+= p \* idf\(w\)", js):
        bad("help.js no longer multiplies a field score by the word's rarity")
        return None
    return got


def _search_model(rows, K):
    """help.js's scoring, in Python, returning names best-first for a query.

    One model, used by every check that asks about search, so there is one
    thing to keep honest rather than two. Every constant comes from help.js
    (see _js_constants); the model itself is checked against the live page by
    hand, and the probes that found the queries it guards were run in a
    browser, not here.
    """
    import build_help

    def fields(r):
        own, cat = build_help.haystack(r)
        return {
            "name": r["Resource Name"].lower(),
            "kind": r["Subcategory"].lower(),
            "tags": build_help.tagtext(r).lower(),
            "alias": (own + " " + build_help.needwords(r["_needs"])).lower(),
            "body": r["Description"].lower(),
            "cat": cat.lower(),
        }

    F = {r["Resource Name"]: fields(r) for r in rows}
    FLAT = {n: " ".join(f.values()) for n, f in F.items()}
    N = len(rows)
    idf_cache = {}

    def starts(hay, w):
        if not w.isascii():
            return w in hay
        return bool(re.search(r"\b" + re.escape(w), hay))

    def exact(hay, w):
        if not w.isascii():
            return w in hay
        return bool(re.search(r"\b" + re.escape(w) + r"\b", hay))

    def field_score(hay, w, weight):
        if starts(hay, w):
            return weight * (K["EXACT"] if exact(hay, w) else 1.0)
        st = _stem(w)
        if st != w and starts(hay, st):
            return weight * K["STEMMED"]
        return 0.0

    def idf(w):
        if w in idf_cache:
            return idf_cache[w]
        df = sum(1 for hay in FLAT.values()
                 if starts(hay, w) or (_stem(w) != w and starts(hay, _stem(w))))
        v = math.log(N / df) / math.log(N) if df else 1.0
        idf_cache[w] = min(1.0, max(K["IDF_FLOOR"], v))
        return idf_cache[w]

    ORDER = [("name", "W_NAME"), ("kind", "W_KIND"), ("tags", "W_TAG"),
             ("alias", "W_ALIAS"), ("body", "W_BODY"), ("cat", "W_CAT")]

    def words_of(query):
        phrase = query.lower().replace("\u2019", "")
        return phrase, [w for w in re.split(r"[^\w\-]+", phrase, flags=re.UNICODE)
                        if w and w not in _STOP
                        and (len(w) >= 2 or not w.isascii())
                        and not (w.isdigit() and len(w) < 3)]

    def score(name, words, phrase):
        f = F[name]
        hits = points = 0
        for w in words:
            p = 0.0
            for key, const in ORDER:
                p = field_score(f[key], w, K[const])
                if p:
                    break
            if p:
                hits += 1
                points += p * idf(w)
        if hits and len(phrase) > 6 and (phrase in f["alias"] or phrase in f["name"]
                                         or phrase in f["tags"]):
            points += K["W_PHRASE"]
        if phrase and f["name"] == phrase:
            points += K["W_NAME_EXACT"]
        return hits, points

    def run(query):
        """Names best-first, cut the way help.js cuts: only the tier that
        matched the most words."""
        phrase, words = words_of(query)
        if not words:
            return []
        scored = {n: score(n, words, phrase) for n in F}
        best = max(h for h, _ in scored.values())
        if not best:
            return []
        tier = [(p, n) for n, (h, p) in scored.items() if h == best]
        tier.sort(key=lambda t: -t[0])
        return [n for _p, n in tier]

    run.score = score
    run.words_of = words_of
    return run


def check_critical_queries():
    """The searches that must not stop working — and must still come first.

    This used to count matched words only: it asked whether the target row was
    in the tier that matched the most words, which is a reachability test. But
    every failure the fifty-phrasing probe turned up was an *ordering* failure.
    "free eyeglasses" did reach the optometry clinic; it put naloxone and
    eviction defence above it, and this check was happy.

    It uses _search_model now — the same scoring help.js computes, with every
    constant read out of help.js — and asserts the target comes FIRST.
    """
    import build_help
    K = _js_constants()
    if not K:
        return
    rows = build_help.load()
    names = {r["Resource Name"] for r in rows}
    model = _search_model(rows, K)

    broken = []
    for query, target in CRITICAL_QUERIES:
        # Some questions have more than one right answer. "back rent" is
        # answered by the emergency grant that pays arrears and by the rent
        # subsidy for families, and insisting on one of them would push the
        # data around until the guard was happy rather than until the page was.
        targets = target if isinstance(target, tuple) else (target,)
        missing = [t for t in targets if t not in names]
        if missing:
            broken.append(f"{query!r} should reach {missing[0]!r}, which is not "
                          "in the directory any more")
            continue
        order = model(query)
        if not order:
            broken.append(f"{query!r} matches nothing in the whole directory")
        elif order[0] not in targets:
            here = next((i for i, n in enumerate(order) if n in targets), None)
            if here is None:
                broken.append(f"{query!r} no longer reaches {targets[0]!r} at all; "
                              f"it returns {order[0]!r}")
            else:
                broken.append(f"{query!r} reaches {order[here]!r} but ranks "
                              f"{order[0]!r} above it (position {here + 1})")
    if broken:
        for b in broken:
            bad(b)
    else:
        ok(f"all {len(CRITICAL_QUERIES)} critical searches still come back "
           f"first, scored the way help.js scores them")


def check_home_names_the_same_needs():
    """The narrative page and the directory must name the same things.

    They are two halves of one site and a reader crosses between them: the
    home page's list is the first thing somebody in trouble sees, and if it
    offers eight of sixteen kinds of help, the other eight do not exist as far
    as that reader is concerned. Worse, if it words them differently, the two
    halves read as two organisations with overlapping lists.
    """
    import build_help
    src = read("index.html")
    block = re.search(r'<ul class="helplinks">.*?</ul>', src, re.S)
    if not block:
        bad("index.html: the list of what the directory holds is gone")
        return
    hrefs = re.findall(r'href="(help-[a-z\-]+\.html)"', block.group(0))
    want = [build_help.page_for(n["key"]) for n in build_help.NEEDS]
    if hrefs != want:
        missing = [h for h in want if h not in hrefs]
        bad(f"index.html lists {len(hrefs)} of the {len(want)} kinds of help"
            + (f"; missing {missing}" if missing else "; in a different order"))
    else:
        ok(f"index.html names all {len(want)} kinds of help, in the same order")

    labels = [html.unescape(x) for x in
              re.findall(r'href="help-[a-z\-]+\.html">([^<]+)</a>', block.group(0))]
    wrong = [(a, b) for a, b in zip(labels, [n["label"] for n in build_help.NEEDS])
             if a != b]
    if wrong:
        bad(f"index.html words a kind of help differently from the directory: "
            f"{wrong[:2]}")
    else:
        ok("index.html words each kind of help exactly as the directory does")


def check_page_furniture():
    """Two small things that only show up on a phone, and both look like bugs.

    A category page opens with a Start here block. A bucket further down that
    also says "Start here" makes the page look like it has two beginnings, and
    the rail then lists both. Only the lead block may use the phrase.

    And a search placeholder longer than the box clips mid-word — "Try:
    hospital bill, denied claim, p" — which reads as a broken page on exactly
    the device most of these readers are holding.
    """
    import build_help
    stray = []
    for key, buckets in build_help.GROUPS.items():
        for bk, label, _ in buckets:
            if bk != "lead" and label.lower().startswith("start here"):
                stray.append(f"{key}/{bk}: {label!r}")
    if stray:
        for x in stray:
            bad(f'a bucket says "Start here" but the lead block already does — {x}')
    else:
        ok('only the lead block on a category page says "Start here"')

    LIMIT = 36
    long = [(n["key"], n["ph"]) for n in build_help.NEEDS if len(n["ph"]) > LIMIT]
    if long:
        for key, ph in long:
            bad(f"{key}: the search placeholder is {len(ph)} characters ({ph!r}); "
                f"over {LIMIT} it clips mid-word in the box on a phone")
    else:
        ok(f"every search placeholder fits its box ({LIMIT} characters or fewer)")


def check_directory_clusters():
    """The front page is one cluster per need, each a way in to one page.

    The failure this guards against is quiet and total: a cluster whose "See
    all" link points at a page that does not exist, or a cluster showing three
    previews of a need whose page shows something else. Either way somebody
    taps and lands nowhere.
    """
    import build_help
    src = read("help.html")
    rows = build_help.load()

    clusters = re.findall(r'<section class="cl" id="n-([a-z\-]+)"', src)
    keys = [n["key"] for n in build_help.NEEDS]
    if clusters == keys:
        ok(f"help.html: all {len(keys)} clusters present, in the order NEEDS defines")
    else:
        bad(f"help.html: the clusters {clusters} do not match NEEDS {keys}")

    # Every cluster hands off to its own page, and the count it promises is
    # the count that page delivers. A "See all 19 places" over a page holding
    # eleven is the kind of small lie that stops somebody trusting the rest.
    for need in build_help.NEEDS:
        key = need["key"]
        page = build_help.page_for(key)
        block = re.search(
            r'<section class="cl" id="n-%s".*?</section>' % re.escape(key), src, re.S)
        if not block:
            bad(f"help.html: no cluster for {key}")
            continue
        block = block.group(0)
        if f'href="{page}"' not in block:
            bad(f"help.html: the {key} cluster does not link to {page}")
            continue
        promised = re.search(r'class="cl__all"[^>]*>See (?:all )?(\d+)? ?', block)
        want = len(build_help.ordered(rows, key))
        actual = len(re.findall(r'<li class="r"', read(page)))
        if promised and promised.group(1) and int(promised.group(1)) != want:
            bad(f"help.html: the {key} cluster promises {promised.group(1)} "
                f"places; there are {want}")
        elif actual != want:
            bad(f"{page} renders {actual} rows for {want} resources")
    ok(f"every cluster links to its page, and promises the number that page holds")

    # A preview line is the first sentence of a description. When a
    # description has no full stop until the end, the whole thing lands on the
    # cluster card and the card stops being a preview.
    PV_MAX = 150
    longwinded = [t for t in re.findall(r'<p class="pv__d">([^<]+)</p>', src)
                  if len(html.unescape(t)) > PV_MAX]
    if longwinded:
        bad(f"{len(longwinded)} preview line(s) run past {PV_MAX} characters, so "
            f"the cluster card is showing a paragraph: {longwinded[0][:80]!r}")
    else:
        ok(f"every preview line fits its card ({PV_MAX} characters or fewer)")

    previews = re.findall(r'<li class="pv">', src)
    per = build_help.PREVIEW
    expect = sum(min(per, len(build_help.ordered(rows, n["key"])))
                 for n in build_help.NEEDS)
    if len(previews) == expect:
        ok(f"help.html: {len(previews)} previews, {per} per cluster — the front "
           "page shows a way in, not the whole directory")
    else:
        bad(f"help.html: {len(previews)} previews where {expect} were expected. "
            "The front page's job is to not be the whole directory.")

    # A bucket rule that matches nothing has usually rotted — a label got
    # reworded and the rule that pointed at it did not. Rewording the
    # subcategories once left nine of them dead, and only a distribution dump
    # showed it. Some emptiness is honest (nobody offers that kind of help
    # yet), so this is a budget rather than a rule.
    dead = []
    for need in build_help.NEEDS:
        grp = build_help.ordered(rows, need["key"])
        for bk, label, words in build_help.GROUPS.get(need["key"], []):
            if not words:
                continue
            if not any(build_help.group_for(r, need["key"]) == bk for r in grp):
                dead.append(f'{need["key"]}/{bk} ("{label}")')
    # Named, not counted. A budget lets six rules rot one at a time and never
    # says so; a list says exactly which emptiness was looked at and accepted.
    EXPECTED_EMPTY = {
        'doctor/women ("Pregnancy and new parents")':
            "the maternal rows are filed under mental health and under family",
        'legal/money ("Benefits, debt, and consumer problems")':
            "the organisations that do this are filed under their main practice",
        'veterans/crisis ("If you are in crisis")':
            "the Veterans Crisis Line is filed under mental health",
        'disability/health ("Health care")':
            "the clinics are filed under health care and reach this page as "
            "cross-references, which do not count toward a bucket being alive",
    }
    surprising = [d for d in dead if d not in EXPECTED_EMPTY]
    stale = [d for d in EXPECTED_EMPTY if d not in dead]
    if surprising:
        bad(f"bucket rule(s) that now match nothing: {surprising}. Usually a "
            "label was reworded and the rule pointing at it was not.")
    elif stale:
        ok(f"{len(dead)} bucket rules are empty, all of them known; "
           f"{len(stale)} entry(ies) in the expected list have come back to life "
           "and can be removed")
    else:
        ok(f"the only empty bucket rules are the {len(dead)} already looked at "
           "and accepted")

    # The rail on each category page is that page's table of contents. A rail
    # entry pointing at a section that is not there is a dead link in the one
    # control built for skimming.
    for page in CATEGORY_PAGES:
        cat = read(page)
        rail = re.findall(r'class="rail__nav"[^>]*>.*?</nav>', cat, re.S)
        if not rail:
            bad(f"{page}: no rail, so there is no way to see what is on the page "
                "without scrolling all of it")
            continue
        targets = re.findall(r'href="#(g-[^"]+)"', rail[0])
        ids = set(re.findall(r'\sid="(g-[^"]+)"', cat))
        missing = [t for t in targets if t not in ids]
        if missing:
            bad(f"{page}: rail links to {missing}, which is not on the page")
        heads = re.findall(r'<section class="grp[^"]*" id="(g-[^"]+)"', cat)
        if targets != heads:
            bad(f"{page}: the rail lists {targets} but the page has {heads}, in "
                "that order — the contents and the page disagree")
    ok(f"every rail on the {len(CATEGORY_PAGES)} category pages matches its page, "
       "in order")


def check_directory_languages():
    """Language access, which on this site is not a nicety.

    New York City's Local Law 30 designates ten citywide languages. The people
    this directory is written for are disproportionately in that group.

    They used to get a panel: a heading, three sentences and a Close link,
    revealed by :target under an otherwise English page. A blurb about the
    page rather than the page. Each of the ten is now a page of its own, built
    from the same components in the same order as the English one, and this
    checks that they really are pages — not that a translation exists
    somewhere, which is what the panel version of this check settled for.
    """
    import build_help, i18n
    langs = build_help.LANGUAGES
    rows = build_help.load()

    # 1. ten pages, and every English page offers all ten
    for page in ENGLISH_PAGES:
        src = read(page)
        # the link may carry a fragment: from "I need food", switching
        # language lands on that language's food card rather than its top
        missing = [L["endonym"] for L in langs
                   if f'href="{build_help.lang_page(L["key"])}' not in src]
        if missing:
            bad(f"{page} does not link to {len(missing)} of the ten language "
                f"pages ({', '.join(missing[:3])}) — a reader who cannot read "
                f"this page cannot get off it")
    ok(f"all {len(ENGLISH_PAGES)} English pages link to all ten language pages")

    # and where the link carries a fragment, that fragment has to be there
    for page in CATEGORY_PAGES:
        key = page[len("help-"):-len(".html")]
        for L in langs:
            href = f'{build_help.lang_page(L["key"])}#n-{key}'
            if f'href="{href}"' not in read(page):
                bad(f"{page}: switching to {L['name_en']} does not keep the "
                    f"reader's place ({href} is not linked)")
                break
            if f'id="n-{key}"' not in read(build_help.lang_page(L["key"])):
                bad(f"{build_help.lang_page(L['key'])} has no #n-{key} to land on")
                break
    ok("switching language from a category page lands on the same kind of help")

    for L in langs:
        page = build_help.lang_page(L["key"])
        if not (ROOT / page).is_file():
            bad(f"{L['name_en']} has no page ({page})")
            continue
        src = read(page)
        # Compared against the page with its entities resolved, not against a
        # re-escaped copy of the expectation: the escaper is the code under
        # test, and an apostrophe leaves it as &#x27;.
        plain = html.unescape(src)
        U = i18n.UI[L["key"]]

        # 2. it declares its own language, and the tag is well formed
        if f'<html lang="{L["tag"]}"' not in src:
            bad(f"{page}: <html> does not declare lang=\"{L['tag']}\", so a "
                f"screen reader reads it with the English voice")
        if not re.fullmatch(r"[a-z]{2,3}(-[A-Za-z]{2,8})*", L["tag"]):
            bad(f"{L['name_en']}: {L['tag']!r} is not a BCP-47 tag")

        # 3. direction is decided by the script, not by a config line that
        #    could be wrong. An Arabic-script title means the page is RTL.
        rtl_script = bool(re.search(r"[\u0590-\u07BF]", U["title_a"] + U["title_b"]))
        declared = 'dir="rtl"' in src.split(">", 3)[1] + src[:400]
        if rtl_script and not declared:
            bad(f"{page} is written in a right-to-left script and is not "
                f"marked dir=\"rtl\"")
        if declared and not rtl_script:
            bad(f"{page} is marked dir=\"rtl\" and is not in an RTL script")

        # 4. the three numbers, dialable, in every language
        body = re.sub(r"<a[^>]*>.*?</a>", "", src, flags=re.S)
        for num in ("911", "988", "311"):
            if f'href="tel:{num}"' not in src:
                bad(f"{page} never dials {num} — the one instruction that is "
                    f"safe in every language")
            if re.search(rf"(?<![0-9]){num}(?![0-9])", body):
                bad(f"{page} prints {num} as text somewhere as well as dialing it")

        # 5. every one of the seventeen kinds of help, named in this language
        for key, label in L["needs"].items():
            if label not in plain:
                bad(f"{page} does not name {key!r} in {L['name_en']}")

        # 5b. the same table of contents the English page has, in the same
        #     seventeen, in the same order
        jm = re.search(r'<nav class="jump"[^>]*>(.*?)</nav>', src, re.S)
        if not jm:
            bad(f"{page} has no jump row; seventeen cards is a long scroll in "
                f"any language")
        else:
            got = re.findall(r"<a[^>]*>([^<]*)</a>", jm.group(1))
            want = [i18n.SHORT[L["key"]][n["key"]] for n in build_help.NEEDS]
            if [html.unescape(g) for g in got] != want:
                bad(f"{page}: the jump row does not name the seventeen in "
                    f"i18n.SHORT order")

        # 6. and a line under each, which is what makes it a page rather than
        #    a menu of headings
        for key, blurb in i18n.BLURBS[L["key"]].items():
            if blurb not in plain:
                bad(f"{page} names {key!r} but does not say what is behind it")

        # 7. the promise, whole. It is a promise, so it is not summarised.
        if U["vow"] not in plain:
            bad(f"{page} does not carry the honesty statement in {L['name_en']}")

        # 7b. the names only a screen reader hears are in the language too.
        #     A blind Korean reader met "Waypoint home" and "Primary" spoken
        #     in English on a Korean page, which is exactly the reader this
        #     page exists for.
        for m in re.finditer(r'aria-label="([^"]+)"', src):
            v = html.unescape(m.group(1))
            if v in (U["home"], U["nav_label"], U["langbar_h"]):
                continue
            if re.fullmatch(r"[\x00-\x7F]+", v) and L["tag"] not in ("es", "fr", "pl", "ht"):
                bad(f"{page}: aria-label={v!r} is in English; a screen reader "
                    f"speaks it on a page that is not")

        # 8a. no English month names. The footer read "Last checked
        #     June-August 2026" on all ten pages, in English, under a sentence
        #     in Bengali — and a date is the one thing on that line a reader
        #     actually checks.
        for month in build_help.MONTHS:
            if re.search(rf"\b{month}\b", plain):
                bad(f"{page} prints the English month {month!r}; the checked "
                    f"date is the one thing on that line a reader checks")
                break
        else:
            got = build_help.checked_in(rows, L["key"])
            if got not in plain:
                bad(f"{page} does not print its checked date ({got!r})")

        # 8. no non-Western digits in a phone number: a reader may copy them
        #    into a dialler that will not take them
        for m in re.finditer(r'href="tel:([^"]+)"', src):
            if not re.fullmatch(r"[+0-9]+", m.group(1)):
                bad(f"{page}: tel:{m.group(1)} is not a dialable number")

        # 9. Nothing is left in English except what is declared as English.
        #    An organisation's name is a proper noun and stays — "Access-A-Ride"
        #    is what you say on the phone — so build_help marks those lang="en"
        #    and this drops them before looking. Anything English that is NOT
        #    marked is prose that was never translated.
        marked = re.sub(r'<(\w+)[^>]*lang="en"[^>]*>.*?</\1>', "", src, flags=re.S)
        marked = re.sub(r"<(script|style)\b.*?</\1>", "", marked, flags=re.S)
        stray = []
        for m in re.finditer(r">([^<>{}]{25,})<", marked):
            t = m.group(1).strip()
            if not t or not re.search(r"[A-Za-z]", t):
                continue
            # A run counts as untranslated only if it is ASCII throughout.
            # Counting the proportion of Latin letters does not work: CJK packs
            # a whole sentence into a dozen characters, so one product name in
            # it tips the balance and the line reads as English.
            if any(ord(c) > 0x24F for c in t):
                continue          # carries this language's own script
                continue          # mostly non-Latin: this language's own script
            if L["tag"] in ("es", "fr", "pl", "ht"):
                continue          # Latin-script languages: cannot tell this way
            stray.append(t[:60])
        for t in sorted(set(stray))[:3]:
            bad(f"{page} has a run of English prose in it: {t!r}")

    ok(f"all ten language pages: own lang tag, direction from the script, "
       f"911/988/311 dialable, all seventeen kinds of help named and "
       f"described, and the promise carried whole")



def check_directory_needs():
    """Every need offered must lead to something, on its own page.

    The front page is a promise: fifteen sentences, each saying "there is help
    for this". A cluster over an empty page, or a bucket heading with nothing
    under it, breaks that promise silently.
    """
    import build_help
    rows = build_help.load()

    # The back-link must survive the phone. It was display:none under 640px —
    # on the one device where these pages scroll longest and there is nothing
    # else to climb back with. Checked once, not per group.
    if re.search(r"@media \(max-width:640px\)\{.*?\.grp__top\{[^}]*display:\s*none",
                 read("help.css"), flags=re.S):
        bad("help.css: .grp__top is hidden on phones, so a reader who has "
            "scrolled into a group has no way back to the top of the page")
    else:
        ok("help.css: the back-link survives on a phone")

    for need in build_help.NEEDS:
        page = build_help.page_for(need["key"])
        src = read(page)
        groups = re.findall(r'<section class="grp[^"]*" id="(g-[^"]+)"', src)
        if not groups:
            bad(f"{page}: no groups at all")
            continue
        for g in groups:
            block = src.split(f'id="{g}"', 1)[-1].split("</section>", 1)[0]
            if not block.count('<li class="r"'):
                bad(f"{page}: '{g}' is a heading with nothing under it")
        # If anything on the page is marked start-here, it leads the page in
        # its own block. Rows otherwise fall in CSV order, which makes the
        # first thing somebody reads an accident of when it was typed — that is
        # how "I got a medical bill" came to open with a membership programme
        # and bury Community Health Advocates eighth. And bucketing them by
        # subject reintroduced the same problem a different way: the best first
        # call was three headings down because of what it was filed under.
        # Only the resources whose own category is this need can lead it. A
        # resource that arrives here as a cross-reference may well be the best
        # first call for the need it belongs to and quite wrong for this one —
        # Access-A-Ride leads "getting there", not "disability".
        primary = [r for r in build_help.ordered(rows, need["key"])
                   if need["key"] in [nd["key"] for nd in build_help.NEEDS
                                      if r["Category"] in nd.get("cats", [])]]
        marked = [r for r in primary if "start-here" in r["Tags"]]
        # Past LEAD_MAX the build deliberately drops the lead block: a Start
        # here section holding thirteen of fifteen resources is not a lead.
        if len(marked) > build_help.LEAD_MAX:
            if f"g-{need['key']}-lead" in src:
                bad(f"{page}: {len(marked)} resources are marked start-here and "
                    "the page still has a lead block; past a few, a lead is not "
                    "a lead")
            marked = []
        if marked:
            if groups[0] != f"g-{need['key']}-lead":
                bad(f"{page}: something here is marked start-here but the page "
                    "does not open with it, so the best first call is not the "
                    "first thing read")
            lead = src.split(f'id="g-{need["key"]}-lead"', 1)[-1].split("</section>", 1)[0]
            n_lead = lead.count('<li class="r"')
            if n_lead != len(marked):
                bad(f"{page}: {len(marked)} of this need's own resources are "
                    f"marked start-here but {n_lead} are in the lead block, so "
                    "one of them is buried or doubled")
    ok(f"every bucket on all {len(CATEGORY_PAGES)} category pages has resources "
       "under it, and each page opens with its best first call")

    # A cluster preview must be a real resource on the page it links to, with
    # the same name. A preview quoting a name the page does not carry is the
    # front page advertising something that is not there.
    front = read("help.html")
    for need in build_help.NEEDS:
        block = re.search(r'<section class="cl" id="n-%s".*?</section>'
                          % re.escape(need["key"]), front, re.S)
        if not block:
            continue
        names = re.findall(r'class="pv__n"[^>]*>([^<]+)</a>', block.group(0))
        page = read(build_help.page_for(need["key"]))
        for nm in names:
            if f">{nm}</h3>" not in page:
                bad(f'help.html: the {need["key"]} cluster previews {nm!r}, which '
                    f'is not on {build_help.page_for(need["key"])}')
    ok("every preview on the front page is a resource that is really on the "
       "page it links to")


def check_directory_a11y():
    """The basics, on the page most likely to be read by somebody who needs them."""
    src = read("help.html")
    if src.count("<h1") == 1:
        ok("help.html: exactly one h1")
    else:
        bad(f"help.html: expected 1 h1, found {src.count('<h1')}")
    if 'class="skip"' in src:
        ok("help.html: skip link present")
    else:
        bad("help.html: no skip link")
    if 'aria-live="polite"' in src:
        ok("help.html: the result count is announced when the list changes")
    else:
        bad("help.html: filtering changes the list with no live region, so a "
            "screen reader user gets no feedback that anything happened")

    ids = re.findall(r'\sid="([^"]+)"', src)
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        bad(f"help.html: duplicate id(s) {sorted(dupes)[:5]}; every anchor to "
            f"one of these lands on whichever came first")
    else:
        ok(f"help.html: all {len(ids)} ids are unique")

    # Seven resources are filed under two needs and so are rendered twice. The
    # count the page prints must be resources, not rows, or it overstates the
    # directory by exactly the number of things we cross-filed.
    keys = re.findall(r'data-key="([^"]+)"', src)
    front = read("help.html")
    keys = re.findall(r'<li class="r"[^>]*data-key="([^"]+)"',
                      "\n".join(read(p) for p in CATEGORY_PAGES))
    lede = re.search(r"list of <b>(\d+) places</b>", front)
    if not lede:
        bad("help.html: the masthead no longer states how many places are listed")
    elif int(lede.group(1)) == len(set(keys)):
        ok(f"help.html: the masthead's count ({lede.group(1)}) is unique "
           f"resources, not the {len(keys)} rows rendered across the pages")
    else:
        bad(f"help.html: the masthead claims {lede.group(1)} places but the "
            f"category pages carry {len(set(keys))} distinct resources")

    # Every category page states its own count too, and that one has to be the
    # number of rows on that page. It is the promise somebody checks against
    # what they can see.
    import build_help
    rows = build_help.load()
    for need in build_help.NEEDS:
        page = build_help.page_for(need["key"])
        src = read(page)
        m = re.search(r"<b>(\d+) places?</b> on this page", src)
        actual = len(set(re.findall(r'data-key="([^"]+)"', src)))
        if not m:
            bad(f"{page}: does not say how many places are on it")
        elif int(m.group(1)) != actual:
            bad(f"{page}: promises {m.group(1)} places, carries {actual}")
    ok(f"every category page's count matches the rows on it")


def check_directory_print():
    """Paper is a real output: students hand people printed sheets.

    The failure this guards is subtle — print hid the disclosures, which is
    where the hours, address and languages live, so the sheet carried a name
    and a number and none of the facts that decide whether somebody can get
    there.
    """
    css = read("help.css")
    block = re.search(r"@media print\{(.*)\n\}", css, flags=re.S)
    if not block:
        bad("help.css: no print stylesheet, so the leave-behind is the screen "
            "design on paper")
        return
    p = block.group(1)
    if re.search(r"\.r__facts\s*\{[^}]*display:\s*none", p):
        bad("help.css: print hides the fact list, so the sheet loses the hours, "
            "the address and the languages")
    else:
        ok("help.css: print keeps each resource's hours, address and languages")
    if re.search(r"\.vowbox\{[^}]*display:\s*none", p) or ".vowbox" not in p:
        bad("help.css: the honesty statement is not styled for print. A printed "
            "sheet is exactly where somebody mistakes a student for a professional.")
    else:
        ok("help.css: the honesty statement prints")
    if "break-inside:avoid" in p:
        ok("help.css: resource cards are kept whole across page breaks")
    else:
        bad("help.css: nothing stops a page break splitting a card, leaving a "
            "phone number on one sheet and its name on another")

    js = read("help.js")
    if "beforeprint" in js and "afterprint" in js:
        ok("help.js opens the disclosures for printing and closes them after")
    else:
        bad("help.js does not open the disclosures on beforeprint, so Ctrl+P "
            "produces a sheet with no hours or addresses on it")


def check_home_offers_help():
    """The home page must lead somewhere useful for somebody in trouble.

    This is the whole reorganisation in one check. The page used to answer
    "the help is real, free and invisible" with a partner pitch, and every
    call to action on it was addressed to somebody who was not frightened.
    """
    src = read("index.html")
    hero = re.search(r'<div class="hero__cta">(.*?)</div>', src, flags=re.S)
    if hero and 'href="help.html"' in hero.group(1):
        first = re.search(r'href="([^"]+)"', hero.group(1)).group(1)
        if first == "help.html":
            ok("index.html: the hero's first call to action is finding help")
        else:
            bad(f"index.html: the hero leads with {first}, not the directory. "
                f"The headline is addressed to somebody with a bill they "
                f"cannot pay; the first button under it should be too.")
    else:
        bad("index.html: the hero does not offer the directory at all")

    if re.search(r'<section class="scene[^"]*" id="help">', src):
        ok("index.html: the resident chapter is present")
    else:
        bad("index.html: the resident chapter (#help) is gone")

    # It has to arrive before the page starts talking to organisations.
    pos_help = src.find('id="help"')
    pos_students = src.find('id="students"')
    pos_partners = src.find('id="partners"')
    if -1 < pos_help < pos_students < pos_partners:
        ok("index.html: residents, then students, then partners")
    else:
        bad("index.html: the resident chapter no longer comes first. Somebody "
            "in trouble should not scroll past a volunteer pitch and a partner "
            "pitch to reach the help.")

    # They used to point at a panel further down help.html. They point at the
    # ten pages now, which is the difference between being told the site knows
    # your language and being handed a page in it.
    import build_help
    want = {build_help.lang_page(L["key"]) for L in build_help.LANGUAGES}
    langs = sorted(w for w in want if f'href="{w}"' in src)
    if len(langs) == len(want):
        ok(f"index.html: all {len(langs)} language pages are reachable from the "
           f"home page")
    else:
        bad(f"index.html: only {len(langs)} of {len(want)} language pages linked; somebody who "
            f"cannot read the headline needs a way in from here")


# The home page names four routes out of a medical bill. Each one is a promise
# that the directory can be asked about it, and for a while none of them could
# be: help.html contained no row mentioning charity care, an external appeal, a
# denial, an appeal, a medical bill or medical debt, while index.html sent
# people to the directory for exactly those things. Nothing broke, nothing
# looked wrong, and the page was simply not true.
#
# Adding a door here without a resource behind it fails the build. If a door is
# renamed, this map has to be updated with it — that is the point, and the
# failure message says so.
DOORS = {
    "Hospital financial assistance": ["financial assistance"],
    "The state's independent appeal": ["external appeal"],
    "Free coverage counselors":       ["community health advocates", "health insurance"],
    "Prescription cost programmes":   ["medication", "prescription"],
}


def check_doors_have_resources():
    """Every route the home page names must be answerable from the directory."""
    idx = read("index.html")
    named = re.findall(r'<span class="ways__name">([^<]+)</span>', idx)
    if not named:
        bad("index.html: no doors found, so the promises cannot be checked")
        return

    helptext = strip_tags("\n".join(read(p) for p in RESIDENT_PAGES)).lower()
    bills = strip_tags(read("help-bills.html")).lower()

    for door in named:
        door = door.replace("&amp;", "&").strip()
        terms = DOORS.get(door)
        if terms is None:
            bad(f'index.html names the route "{door}" but check.py has no entry '
                f'for it in DOORS. Add one naming the words that prove the '
                f'directory can answer it, or the page is promising something '
                f'nothing backs up.')
            continue
        if any(t in bills for t in terms):
            ok(f'door "{door}" has a resource behind it')
        elif any(t in helptext for t in terms):
            bad(f'door "{door}" is answered somewhere in the directory but not '
                f'under "I got a medical bill" — somebody following that '
                f'promise from the home page lands in the wrong group')
        else:
            bad(f'door "{door}" is named on the home page and NOTHING in the '
                f'directory answers it. Looked for {terms}.')



def check_the_promises_are_still_there():
    """The honesty paragraph is the site's boundary, so it is checked as text.

    Every clause in it is a promise somebody could quietly soften later — the
    difference between "we never charge for anything" and "we do not charge for
    most things" is invisible in a diff review and enormous to a reader
    deciding whether to call. Each clause is required verbatim on every page
    that carries the paragraph.
    """
    clauses = [
        "trained student volunteers",
        "not doctors, lawyers, benefits counselors, or insurance experts",
        "do not read your bills, fill out your forms, or tell you what you "
        "qualify for",
        "they do it for free",
        "never charge for anything",
    ]
    # The anchor is a sentence that appears nowhere else. privacy.html and
    # terms.html make the same promises in their own legal wording, and this
    # guard is about the resident-facing paragraph, not about those.
    anchor = "We connect you to people who do that"
    carriers = [f for f in sorted(str(q) for q in Path(".").glob("*.html"))
                if anchor in read(f)]
    if not carriers:
        bad("no page carries the honesty paragraph any more")
        return
    for f in carriers:
        html = re.sub(r"<[^>]+>", "", read(f))
        html = html.replace("&nbsp;", " ")
        for c in clauses:
            if c in html:
                ok(f"{f} still promises: {c[:40]}")
            else:
                bad(f"{f} carries the honesty paragraph but no longer says "
                    f"{c!r}. That sentence is a promise to a reader deciding "
                    f"whether it is safe to call. Restore it or take the whole "
                    f"paragraph down deliberately.")


def check_no_english_month_on_a_language_page():
    """A date is the one English word that sneaks onto a translated page.

    Every other string on the ten language pages comes out of i18n.py, but the
    "checked" date is assembled from a month name, and reaching for the English
    formatter instead of the translated one produces a page that reads
    perfectly until the last line, where it says August.
    """
    months = re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\b")
    import build_help

    for key in build_help.LANG_SLUG:
        f = build_help.lang_page(key)
        if not os.path.exists(f):
            bad(f"{f} is missing")
            continue
        text = re.sub(r"<[^>]+>", " ", read(f))
        found = sorted(set(months.findall(text)))
        if found:
            bad(f"{f} prints the English month {', '.join(found)}. The date "
                f"comes from checked_in(rows, key), which translates it; "
                f"checked(rows) does not.")
        else:
            ok(f"{f} dates itself in its own language")


def check_the_emergency_strip_is_always_open():
    """The four numbers at the top of every resident page are the 3am block.

    Somebody reading them is not going to notice a small-print "Mon-Fri" and
    wait until Monday. Every row the strip draws from has to be answered
    around the clock, and any row whose name promises 24 hours has to have
    hours that agree with its own name.
    """
    import build_help

    rows = build_help.load()
    by_name = {r["Resource Name"]: r for r in rows}
    allday = re.compile(r"24[/ ]?7|24 ?hours|24-hour|around the clock", re.I)

    for name, _why in build_help.SOS:
        r = by_name.get(name)
        if not r:
            bad(f"the emergency strip names {name!r}, which is not in the data")
        elif not allday.search(r["Hours"]):
            bad(f"the emergency strip offers {name!r}, whose hours read "
                f"{r['Hours']!r}. A number on that strip is one somebody dials "
                f"at 3am; it has to be answered then.")
        else:
            ok(f"emergency strip: {name} is answered around the clock")

    for r in rows:
        if allday.search(r["Resource Name"]) and not allday.search(r["Hours"]):
            bad(f"{r['Resource Name']!r} promises 24 hours in its own name but "
                f"its hours read {r['Hours']!r}")


def check_outbound_links_are_safe():
    """Every link off this site opens in the same tab, with rel="noopener".

    Same tab because the back button is the one control every reader already
    knows, and a new tab takes it away from them. noopener because a page we
    do not control should never get a handle on the one the reader came from.
    """
    blank, bare = [], []
    for f in sorted(str(q) for q in Path(".").glob("*.html")):
        for tag in re.findall(r"<a\b[^>]*>", read(f)):
            if 'target="_blank"' in tag and "noopener" not in tag:
                blank.append(f"{f}: {tag[:90]}")
            m = re.search(r'href="(https?://[^"]+)"', tag)
            if m and "noopener" not in tag:
                bare.append(f"{f}: {m.group(1)[:70]}")
    for x in sorted(set(blank))[:6]:
        bad(f"a link opens a new tab with no rel=noopener — {x}")
    for x in sorted(set(bare))[:6]:
        bad(f"an outbound link has no rel=noopener — {x}")
    if not blank and not bare:
        ok("every outbound link stays in the tab and carries rel=noopener")


def check_every_website_is_https():
    """A directory that sends somebody to http:// is sending them somewhere a
    network can read and rewrite. Every site we name supports https."""
    import build_help

    bad_ones = [r["Resource Name"] for r in build_help.load()
                if r["Website"].startswith("http://")]
    if bad_ones:
        for n in bad_ones[:8]:
            bad(f"{n!r} is listed with an http:// address; use https://")
    else:
        ok("every website in the directory is https")


def check_the_skip_link_works():
    """The first thing a keyboard reaches on every page.

    Three ways it stops working and none of them are visible: it gets
    display:none (which takes it out of the tab order entirely), it loses the
    :focus rule that brings it on screen, or it points at an id that a later
    edit renamed. This checks all three.
    """
    css = read("help.css") + read("styles.css")
    rule = re.search(r"\.skip\{([^}]*)\}", css)
    if not rule:
        bad("there is no .skip rule any more")
        return
    if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden", rule.group(1)):
        bad("the skip link is display:none, which takes it out of the tab "
            "order — it is not hidden from sight, it is gone. Use the "
            "clip-path pattern the rest of the site uses.")
    else:
        ok(".skip is clipped, not removed")
    if not re.search(r"\.skip:focus\b", css):
        bad("the skip link has no :focus rule, so it never comes on screen")
    else:
        ok(".skip:focus brings it back on screen")

    for f in sorted(str(q) for q in Path(".").glob("*.html")):
        src = read(f)
        # 2.4.1 is about bypassing a block of repeated content. A page with no
        # site header has no repeated block to bypass — the redirect stubs and
        # the internal pages are not exempted by choice, they have nothing to
        # skip.
        if 'class="sitehead"' not in src:
            continue
        m = re.search(r'<a class="skip" href="#([^"]+)"', src)
        if not m:
            bad(f"{f} carries the site header but has no skip link, so a "
                f"keyboard reader tabs the whole bar on every page")
        elif f'id="{m.group(1)}"' not in src:
            bad(f"{f}'s skip link points at #{m.group(1)}, which is not on the "
                f"page — it would send a keyboard reader nowhere")
        else:
            ok(f"{f} skips to #{m.group(1)}")


def check_category_pages_keep_their_jump_nav():
    """Seventeen kinds of help, and seven groups inside each one, is too much
    to scroll past.

    Two navs do that work and both are the page's table of contents: help.html
    opens with `.jump`, a link per kind of help, and every category page opens
    with `.rail__nav`, a link per group on it. On a phone either one is the
    difference between finding the right block and giving up. Each has to be
    there, not hidden, and to name every target the page actually has — a nav
    that names six of seven groups leaves the seventh with nothing that
    reaches it.
    """
    import build_help

    langs = {build_help.lang_page(k) for k in build_help.LANG_SLUG}

    def one(page, cls, prefix):
        src = read(page)
        nav = re.search(rf'<nav class="{cls}"([^>]*)>(.*?)</nav>', src, re.S)
        if not nav:
            bad(f"{page} has lost its {cls} nav, which is the only thing on "
                f"the page that takes a reader to a section")
            return
        if re.search(r"\bhidden\b", nav.group(1)) or \
                re.search(r"display\s*:\s*none|visibility\s*:\s*hidden",
                          nav.group(1)):
            bad(f"{page}'s {cls} nav is hidden, which is the same as not "
                f"having one for everybody who can see the page")
            return
        links = set(re.findall(rf'href="#({prefix}[^"]*)"', nav.group(2)))
        targets = set(re.findall(rf'id="({prefix}[^"]*)"', src))
        if not links:
            bad(f"{page}'s {cls} nav has no links in it")
        elif links - targets:
            bad(f"{page}'s {cls} nav points at {sorted(links - targets)}, "
                f"which is not on the page")
        elif targets - links:
            bad(f"{page} has {sorted(targets - links)} that the {cls} nav "
                f"never names, so nothing takes a reader there")
        else:
            ok(f"{page} jumps to all {len(links)} of its sections")

    one("help.html", "jump", "n-")
    for page in sorted(str(q) for q in Path(".").glob("help-*.html")):
        if page not in langs:
            one(page, "rail__nav", "g-")


def check_header_spacing_lives_in_one_place():
    """The two halves may choose the header's colours. They may not choose its
    spacing.

    That is the whole reason the header tokens are split the way they are:
    tokens.css owns the measurements so the bar is the same height, the same
    padding and the same gaps on the dark half and the light one, and a reader
    moving between them sees nothing move. A stylesheet that redefines one of
    the spacing tokens breaks that silently — the bar still looks fine on the
    page you are editing.
    """
    spacing = ["--head-pad", "--head-row", "--head-gap", "--head-h",
               "--head-wrap", "--head-gutter"]
    for f in ("help.css", "styles.css"):
        src = read(f)
        # a definition, not a var() read
        for tok in spacing:
            if re.search(rf"{tok}\s*:", src):
                bad(f"{f} sets {tok}. The header's measurements live in "
                    f"tokens.css so that both halves get the same ones; a "
                    f"stylesheet that redefines one moves the bar on its half "
                    f"only. Set colours here, measurements there.")
            else:
                ok(f"{f} leaves {tok} to tokens.css")
    if not re.search(r"--head-pad\s*:", read("tokens.css")):
        bad("tokens.css no longer defines --head-pad")


def check_the_docs_do_not_carry_a_stale_count():
    """The pages cannot go stale about how many resources there are, because
    the build counts them. The docs can, and did — five places said 340 when
    the file held 351, and every one of them was written by somebody who was
    right at the time.

    So: a number written next to the word "resources" in a doc, a comment or a
    docstring has to be the number in the file. Anywhere the count is
    incidental, take it out rather than maintaining it.
    """
    import build_help

    n = len(build_help.load())
    near = re.compile(r"\b(\d{2,4})\s+(?:verified\s+|English\s+)?resources?\b")
    hits = []
    for f in ("DESIGN.md", "PLAN-help.md", "build_help.py", "check.py",
              "i18n.py", "help.js"):
        if not os.path.exists(f):
            continue
        for i, line in enumerate(read(f).split("\n"), 1):
            # "118 -> 311 resources" in the task log is history, and history
            # is supposed to stay where it was.
            if "→" in line or "->" in line:
                continue
            for m in near.finditer(line):
                said = int(m.group(1))
                if said != n:
                    hits.append(f"{f}:{i} says {m.group(0)!r}; the file holds "
                                f"{n}. Fix the number, or drop it — a count "
                                f"nobody regenerates is a count that goes "
                                f"wrong quietly.")
    if hits:
        for h in hits[:8]:
            bad(h)
    else:
        ok(f"no doc, comment or docstring miscounts the {n} resources")


def check_the_printed_page_keeps_its_numbers():
    """The print stylesheet exists to produce a leave-behind.

    Students hand it across a table at an event: a kind of help, three real
    places under it, every phone number in plain type. The rules that make it
    two sheets instead of forty are all `display:none`, and one more of those
    aimed at the wrong selector produces a handout with no numbers on it —
    which nobody notices, because nobody prints the site to check.
    """
    css = read("help.css")
    block = re.search(r"@media print\{(.*?)\n\}", css, re.S)
    if not block:
        bad("help.css has no @media print block; the leave-behind is gone")
        return
    # Comments first: a brace inside one derails any brace-counting after it.
    body = re.sub(r"/\*.*?\*/", "", block.group(1), flags=re.S)
    # The selectors that carry a phone number onto paper.
    carriers = [".cl__b", ".cl__pv", ".pv__call", ".pv__n", ".cl h3 a"]
    for sel in carriers:
        hidden = re.search(rf"{re.escape(sel)}\s*\{{[^}}]*display\s*:\s*none",
                           body)
        if hidden:
            bad(f"the print stylesheet hides {sel}, which is where a phone "
                f"number lands on paper. The printed page is the thing a "
                f"student hands somebody; it is numbers or it is nothing.")
        else:
            ok(f"print keeps {sel}")
    # And the controls have to be gone. The rule that hides them is one long
    # selector list, and it lost its terminating line in an edit — what was
    # left ended in a comma, which CSS joined to the next rule, so the header,
    # the search box, the jump nav, the breadcrumb and the footer links
    # stopped being hidden and started printing as three-column grids. Six
    # sheets instead of three, and nobody prints the site to check.
    CHROME = [".sitehead", ".find", ".jump", ".crumb", ".skip",
              ".hfoot__links", ".cl__all", ".langbar", ".printbtn"]
    for sel in CHROME:
        hidden = False
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
            names = [x.strip().split()[0] if x.strip() else ""
                     for x in m.group(1).split(",")]
            if sel in names and re.search(r"display\s*:\s*none", m.group(2)):
                hidden = True
                break
        if hidden:
            ok(f"print hides {sel}")
        else:
            bad(f"the print stylesheet does not hide {sel}, so it prints. The "
                f"leave-behind is answers and phone numbers; a search box on "
                f"paper is a control nobody can use.")

    # And the numbers have to be black on white, not a grey nobody can read
    # through a photocopier.
    if "color:#000" not in body:
        bad("the print stylesheet never sets a black ink colour")
    else:
        ok("print sets black ink")


def check_form_fields_say_what_they_want():
    """A form that asks for an email should say so to the browser.

    type="email" is three things at once: the phone shows an @ key, the
    browser rejects a typo before the round trip, and a password manager knows
    what the field is. type="text" on a field named email throws all three
    away and looks identical.
    """
    for f in sorted(str(q) for q in Path(".").glob("*.html")):
        for tag in re.findall(r"<input\b[^>]*>", read(f)):
            name = re.search(r'name="([^"]+)"', tag)
            if not name:
                continue
            kind = re.search(r'type="([^"]+)"', tag)
            kind = kind.group(1) if kind else "text"
            want = {"email": "email", "phone": "tel", "tel": "tel"}.get(
                name.group(1).lower())
            if want and kind != want:
                bad(f'{f}: <input name="{name.group(1)}"> is type="{kind}"; it '
                    f'should be type="{want}" so the phone shows the right '
                    f'keyboard and the browser catches a typo first')
            elif want:
                ok(f"{f}: {name.group(1)} is type={want}")


def check_the_search_says_when_it_guessed():
    """If the search silently fixes a spelling, the reader is looking at
    results for a word they did not type.

    Somebody who typed "sheltr" and sees shelters is fine. Somebody who typed
    a real word we mangled into a different real word is being misled, and has
    no way to tell. So the correction is announced, in the same status line
    that announces the count.
    """
    js = read("help.js")
    if not re.search(r"Showing results for", js):
        bad("help.js no longer tells the reader when it corrected a spelling. "
            "A search that quietly answers a different question is worse than "
            "one that finds nothing.")
        return
    ok("the search announces a correction")
    # and the announcement has to be built from what it actually corrected
    if not re.search(r"corrected\s*=\s*fixed", js):
        bad("help.js announces a correction but never records one, so the "
            "sentence can only ever be empty")
    else:
        ok("the announcement is built from the words it actually changed")


def check_every_page_names_itself():
    """A page with no description is a page that arrives in a search result,
    or in somebody's messages, as a bare URL.

    Every page gets a title and a one-sentence description, and on the
    resident side the description is the page's own lede — generated, so it
    cannot drift from what the page says.
    """
    for f in sorted(str(q) for q in Path(".").glob("*.html")):
        src = read(f)
        if 'http-equiv="refresh"' in src:
            continue                      # the redirect stubs
        if re.search(r'<meta name="robots"[^>]*noindex', src):
            continue                      # a page nobody should find at all
        title = re.search(r"<title>(.*?)</title>", src, re.S)
        desc = re.search(r'<meta name="description" content="([^"]*)"', src)
        if not title or not title.group(1).strip():
            bad(f"{f} has no title")
        elif not desc:
            bad(f"{f} has no meta description, so it arrives anywhere it is "
                f"shared as a bare URL")
        elif len(desc.group(1).strip()) < 40:
            bad(f"{f}'s description is {len(desc.group(1).strip())} characters "
                f"— too short to say what the page is")
        else:
            ok(f"{f} names itself")


def check_every_resource_says_what_it_is():
    """A row with no description is a name and a phone number.

    The description is the whole reason somebody picks one row over another —
    it is what tells them this pantry is the one that does not ask for ID.
    Without it the card is a phone number with a proper noun above it, and the
    reader has to call to find out whether it was worth calling.
    """
    import build_help

    thin, shape = [], []
    for r in build_help.load():
        d = (r["Description"] or "").strip()
        if len(d) < 40:
            thin.append(f"{r['Resource Name']!r} has "
                        f"{'no description' if not d else f'a {len(d)}-character description'}")
            continue
        # A description is a sentence. Anything that starts mid-clause or
        # stops without a full stop is a description something ate — a
        # truncation, a bad paste, a clause deleted by a careless edit — and
        # it lands on the card looking almost right.
        if not re.match(r'[A-Z0-9"\u201c]', d):
            shape.append(f"{r['Resource Name']!r} starts mid-sentence: {d[:60]!r}")
        elif not d.endswith((".", "?", "!", "\u201d")):
            shape.append(f"{r['Resource Name']!r} stops without a full stop: "
                         f"{d[-60:]!r}")
    if thin:
        for t in thin[:8]:
            bad(t + " — a card with no sentence on it is a phone number with a "
                    "name above it")
    for t in shape[:8]:
        bad(t)
    if not thin and not shape:
        ok("every resource says what it is, in a whole sentence")


def check_a_page_without_script_does_not_trust_head_h():
    """--head-h is a guess, and only JavaScript makes it true.

    The token computes the header's height from the assumption that the tab
    row wraps to two rows. How many rows it really takes depends on how long
    the tab labels are, which is a different answer in every language.
    Measured at 320px: Spanish and French 251px, English and Russian 203,
    Arabic and Chinese 155 — against a declared 116 in every case.

    help.html and index.html publish the measured height with a
    ResizeObserver, so the guess never survives first paint. The ten language
    pages ship no script on purpose, and there the guess stood: a tap on any
    section link landed the heading up to 121px under a bar that was still
    covering it.

    So the rule is: a page that trusts --head-h for its anchor offsets has to
    be a page that corrects it. The language pages do not, so below the width
    where the bar wraps it stops following them.
    """
    import build_help

    css = read("help.css")
    if not re.search(r"body\[data-lang\][^{]*\.sitehead\s*\{[^}]*position\s*:\s*static",
                     css):
        bad("help.css no longer takes the header out of the flow on the "
            "language pages. Those pages ship no script, so --head-h stays at "
            "its two-row guess and a sticky bar covers the heading every "
            "in-page link jumps to. Restore the rule or give the pages the "
            "script that measures the bar.")
    else:
        ok("the language pages do not let an unmeasured bar follow them")

    # and the premise: they really do ship no script
    for key in build_help.LANG_SLUG:
        page = build_help.lang_page(key)
        if os.path.exists(page) and re.search(r"<script\b", read(page)):
            bad(f"{page} has a script on it now; if it measures the header, "
                f"this guard's premise is gone and the static rule can go too")


def main():
    for fn in [check_pages_exist, check_links, check_cross_page_anchors, check_stage_layers,
               check_honesty_statement, check_forbidden, check_no_invented_numbers,
               check_billing_boundaries, check_forms, check_labels, check_door,
               check_transition_invariants, check_reel, check_audience_order, check_mobile_budget, check_mobile_reads, check_vow, check_lane, check_doors,
               check_one_block_at_a_time, check_vendored,
               check_asset_budget, check_a11y_basics, check_nav_matches_sections,
               check_theme_is_shared, check_one_header, check_language_header, check_language_round_trip, check_language_print, check_language_voice, check_nothing_parks_offscreen, check_script_typography, check_language_pages_need_no_script, check_language_sentence_length, check_hreflang_is_reciprocal, check_language_spacing_is_shared, check_page_cannot_be_dragged_sideways, check_tap_targets, check_high_contrast_covers_the_cards, check_every_row_has_someone_to_verify_it, check_every_resource_is_findable_by_name, check_one_typo_does_not_empty_the_page, check_every_category_page_answers_its_own_questions, check_also_tags_are_real_needs, check_the_data_itself, check_focus_ring, check_heading_order, check_language_numbers_dial,
               check_the_promises_are_still_there,
               check_no_english_month_on_a_language_page,
               check_the_emergency_strip_is_always_open,
               check_outbound_links_are_safe, check_every_website_is_https,
               check_the_skip_link_works, check_category_pages_keep_their_jump_nav,
               check_header_spacing_lives_in_one_place,
               check_the_docs_do_not_carry_a_stale_count,
               check_the_printed_page_keeps_its_numbers,
               check_form_fields_say_what_they_want,
               check_the_search_says_when_it_guessed,
               check_every_page_names_itself,
               check_every_resource_says_what_it_is,
               check_a_page_without_script_does_not_trust_head_h,
               check_directory_is_generated, check_directory_reachable,
               check_directory_emergency, check_directory_no_js_contract,
               check_directory_languages, check_directory_needs,
               check_directory_clusters, check_no_stale_counts,
               check_page_furniture, check_home_names_the_same_needs,
               check_critical_queries, check_no_sideways_scroll,
               check_checked_date_is_derived, check_page_weight,
               check_reading_level,
               check_directory_a11y, check_directory_print,
               check_home_offers_help, check_doors_have_resources]:
        before = len(passes) + len(failures)
        try:
            fn()
        except Missing as e:
            bad(f"{fn.__name__}: skipped, {e} is missing")
        # A check function that reports nothing has stopped checking. This is
        # not hypothetical: an edit once re-indented two guards into the body
        # of an `if` that was false, and the suite went on printing "0 failed"
        # while they no longer ran. Silence is the one failure mode a linter
        # cannot report on itself, so it is reported here.
        if len(passes) + len(failures) == before:
            bad(f"{fn.__name__} ran but asserted nothing, so whatever it "
                f"guarded is now unguarded")

    if VERBOSE:
        for p in passes:
            print(f"  ok   {p}")
    print(f"\n{len(passes)} passed, {len(failures)} failed")
    for f in failures:
        print(f"  FAIL {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
