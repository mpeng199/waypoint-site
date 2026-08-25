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


CATEGORY_PAGES = [f"help-{k}.html" for k in _need_keys()]
RESIDENT_PAGES = ["help.html"] + CATEGORY_PAGES

PAGES = (["index.html", "help.html"] + CATEGORY_PAGES +
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
    nav = re.search(r'<nav class="nav__links".*?</nav>', src, flags=re.S)
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

    # the menu button measured 30x22 — under even the 24px WCAG 2.5.8 minimum
    if re.search(r"\.nav__tog::after[^{]*\{[^}]*inset:-13px", narrow):
        ok("mobile: the menu button's hit area is widened past its glyph")
    else:
        bad("mobile: .nav__tog is back to a 30x22 hit area — the primary "
            "navigation control on a phone, under the WCAG 2.5.8 minimum")


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

    # ---- the drawer ----
    # 1. backdrop-filter on .nav makes it the containing block for its own
    #    fixed child, so past 40px of scroll the drawer opened as a 375x77 strip
    if re.search(r"\.menu-open \.nav[^{]*\{[^}]*backdrop-filter:none", css):
        ok("drawer: the bar drops its blur while the menu is open")
    else:
        bad("drawer: .nav keeps backdrop-filter with the menu open, which makes "
            "it the containing block for the fixed drawer — the menu collapses "
            "to the height of the bar everywhere except the top of the page")
    # 2. transform alone hides it from the eye and from nothing else
    if re.search(r"\.nav__links\{[^}]*visibility:hidden", narrow) and \
       re.search(r"\.nav__links\.open\{[^}]*visibility:visible", narrow):
        ok("drawer: closed means closed to the keyboard too")
    else:
        bad("drawer: the closed drawer is only translated off-screen, so its "
            "links keep tabindex 0 and a keyboard user tabs into a menu that "
            "is not open")
    # a panel, not a takeover — and the scrim is what earns the panel. Without
    # it the strip of page beside the drawer shows a severed wordmark and two
    # letters of the headline at full contrast, which is what drove it to
    # full-screen the first time.
    if re.search(r"\.nav__links\{[^}]*width:min\(", narrow):
        ok("drawer: a bounded panel rather than the whole screen")
    else:
        bad("drawer: .nav__links has no bounded width — it covers the entire "
            "viewport instead of sitting over the page as a panel")
    if re.search(r"\.menu-open body::after\{[^}]*pointer-events:auto", css) and \
       re.search(r"body::after\{[^}]*position:fixed", css):
        ok("drawer: a scrim dims the page beside the panel and takes the tap")
    else:
        bad("drawer: no scrim. The page beside the panel reads at full "
            "contrast, showing a wordmark cut in half by the panel edge")
    if re.search(r'e\.target\.closest\("\.nav__links, \.nav__tog"\)', js):
        ok("drawer: tapping the dimmed page closes it")
    else:
        bad("drawer: the scrim swallows taps without closing the menu, which "
            "is the first gesture anyone tries on a panel")

    # 3. a fixed layer over a document that is still scrolling underneath it
    if "lenis.stop()" in js and 'style.overflow = open ? "hidden"' in js:
        ok("drawer: opening it stops the page, Lenis included")
    else:
        bad("drawer: nothing locks the scroll while the menu is open — a swipe "
            "on the menu scrolls the journey behind it. Lenis drives the scroll "
            "itself, so an overflow:hidden body alone does not stop it")
    # 4. escape, and focus that makes the round trip
    if re.search(r'e\.key === "Escape"', js) and "tog.focus()" in js:
        ok("drawer: Escape closes it and focus returns to the button")
    else:
        bad("drawer: no Escape, or focus is left in the closed drawer")

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
        ("the deep green footer", ".hfoot{ background:var(--green-deep)" in helpcss),
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

    rows = build_help.load()
    want = {"help.html": build_help.render_overview(rows)}
    for need in build_help.NEEDS:
        want[build_help.page_for(need["key"])] = build_help.render_category(need, rows)

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


def check_directory_clusters():
    """The front page is fifteen clusters, each a way in to one page.

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
    """The seven in-language panels, and the tags that make them speakable."""
    src = read("help.html")
    panels = re.findall(r'<section class="langnote" id="lang-([a-z-]+)" lang="([a-z]+)"', src)
    if len(panels) >= 7:
        ok(f"help.html: {len(panels)} in-language panels present")
    else:
        bad(f"help.html: only {len(panels)} in-language panels; expected 7")

    # Every lang= on the page must be a real subtag. lang="spanish" is not one,
    # so a screen reader keeps its English voice and reads the label as English
    # — silently, on the one row of the page aimed at people who do not read it.
    valid = {"en", "es", "zh", "ru", "ht", "bn", "ko", "ar"}
    tags = set(re.findall(r'(?<!-)\blang="([^"]+)"', src))
    rogue = tags - valid
    if rogue:
        bad(f"help.html: lang attribute(s) that are not valid subtags: {sorted(rogue)}")
    else:
        ok(f"help.html: every lang attribute is a real subtag {sorted(tags)}")

    # Every language offered must actually reach a usable share of the
    # directory. This is the guard for the bug that made the feature nearly
    # useless: 77 rows record their languages as "Multiple", which matched no
    # chip, so filtering by Arabic — which no row names explicitly — returned
    # six places out of a hundred and eighteen and implied the rest could not
    # help. A chip that reaches almost nothing is worse than no chip.
    total = src.count('<li class="r"')
    for key, _tag in [(k, t) for k, t in re.findall(r'data-f="lang" data-v="([a-z-]+)"[^>]*lang="([a-z]+)"', src)]:
        reach = len(re.findall(r'data-lang="[^"]*(?:\b' + key + r'\b|\bmany\b)[^"]*"', src))
        if reach >= total * 0.25:
            ok(f"help.html: the {key} filter reaches {reach} of {total} rows")
        else:
            bad(f"help.html: the {key} filter reaches only {reach} of {total} "
                f"rows. Filtering by it hides most of the directory from "
                f"exactly the person least able to search it another way.")

    if 'dir="rtl"' in src:
        ok("help.html: the Arabic panel is marked right-to-left")
    else:
        bad("help.html: no dir=\"rtl\" anywhere, so the Arabic panel renders "
            "left-to-right")

    # Each panel has to route somewhere a person can actually be helped, and
    # 311 is the one number that answers in any language at any hour.
    for key, _ in panels:
        block = src.split(f'id="lang-{key}"', 1)[-1].split("</section>", 1)[0]
        if "311" in block:
            ok(f"help.html: the {key} panel names 311 as the interpreter route")
        else:
            bad(f"help.html: the {key} panel does not mention 311. It is the "
                f"fallback that works even if the translation above it reads badly.")


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
        marked = re.findall(r'<li class="r"[^>]*data-find="([^"]*start-here[^"]*)"', src)
        if marked:
            if groups[0] != f"g-{need['key']}-lead":
                bad(f"{page}: something here is marked start-here but the page "
                    "does not open with it, so the best first call is not the "
                    "first thing read")
            lead = src.split(f'id="g-{need["key"]}-lead"', 1)[-1].split("</section>", 1)[0]
            if lead.count('<li class="r"') != len(marked):
                bad(f"{page}: {len(marked)} resource(s) are marked start-here but "
                    f"{lead.count(chr(60) + 'li class=' + chr(34) + 'r' + chr(34))} "
                    "are in the lead block, so one of them is buried or doubled")
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

    langs = re.findall(r'href="help\.html#lang-([a-z-]+)"', src)
    if len(langs) >= 7:
        ok(f"index.html: {len(langs)} in-language entry points on the home page")
    else:
        bad(f"index.html: only {len(langs)} in-language links; somebody who "
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



def main():
    for fn in [check_pages_exist, check_links, check_cross_page_anchors, check_stage_layers,
               check_honesty_statement, check_forbidden, check_no_invented_numbers,
               check_billing_boundaries, check_forms, check_labels, check_door,
               check_transition_invariants, check_reel, check_audience_order, check_mobile_budget, check_mobile_reads, check_vow, check_lane, check_doors,
               check_one_block_at_a_time, check_vendored,
               check_asset_budget, check_a11y_basics, check_nav_matches_sections,
               check_theme_is_shared,
               check_directory_is_generated, check_directory_reachable,
               check_directory_emergency, check_directory_no_js_contract,
               check_directory_languages, check_directory_needs,
               check_directory_clusters,
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
