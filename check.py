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


def main():
    for fn in [check_pages_exist, check_links, check_cross_page_anchors, check_stage_layers,
               check_honesty_statement, check_forbidden, check_no_invented_numbers,
               check_billing_boundaries, check_forms, check_labels, check_door,
               check_transition_invariants,
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
