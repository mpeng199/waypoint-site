"""Does check.py actually catch things?

A guard suite that passes tells you nothing on its own — a check can pass
because the site is right, or because the check stopped looking. This breaks
the site twelve ways on purpose, one at a time, rebuilds, runs check.py, and
records whether the suite noticed. Every mutation is a regression somebody
could plausibly commit without meaning to.

    python3 mutate.py

It restores every file it touches and rebuilds afterwards, so a clean tree
before is a clean tree after. If it dies half way, `git checkout -- .` then
`python3 build_help.py`.

Anything reported as MISSED is a hole in check.py, not a hole here.
"""

import re
import shutil, subprocess, sys, os, tempfile
ROOT = os.getcwd()
FILES = ["data/resources.csv","help.css","styles.css","tokens.css","help.js",
         "build_help.py","index.html","i18n.py","script.js","check.py"]
# A fresh directory per run. A reused one can hold a snapshot from a run
# that died half way, and restoring from it puts the damage back.
BAK = tempfile.mkdtemp(prefix="mutate-")

MUTATIONS = [
 ("a phone number loses a digit",
  "data/resources.csv", "800-621-4673", "800-621-467"),
 ("the honesty statement is reworded",
  "build_help.py", "never charge for anything.", "do not charge for most things."),
 ("a language page drops a heading translation",
  "i18n.py", '"food": "Comida",', '"food": "Food",'),
 ("a dark surface loses its focus ring color",
  "help.css", ".hfoot{ --focus:var(--gold-lit);", ".hfoot{ --focus:var(--green);"),
 ("the shared header is restyled on one half",
  "styles.css", ".sitehead{\n  position:fixed;", ".sitehead{\n  padding:40px;\n  position:fixed;"),
 ("a tap target shrinks",
  "tokens.css", "min-height:44px;\n  font-weight:600; font-size:.9rem;",
  "min-height:30px;\n  font-weight:600; font-size:.9rem;"),
 ("the search stops weighting rare words",
  "help.js", "if (v < 0.15) v = 0.15;", "return 1;"),
 ("a resource loses its category",
  "data/resources.csv", '"Food & Nutrition","Pantries and groceries","A free pantry on Staten Island',
  '"Zzz","Pantries and groceries","A free pantry on Staten Island'),
 ("a description starts using agency words",
  "data/resources.csv", "A paid summer job for young people",
  "Provides comprehensive workforce development services and case management to eligible youth"),
 ("the ten language pages lose a tab",
  "build_help.py", "'      <a href=\"index.html#work\">How it works</a>',", ""),
 ("an English month leaks onto a language page",
  "build_help.py", "when=checked_in(rows, L[\"key\"])", "when=checked(rows)"),
 ("index.html can be dragged sideways again",
  "styles.css", "html, body{ overflow-x:clip; }", "body{ overflow-x:hidden; }"),
 # ---- round two: areas the first twelve never touched
 ("the skip link stops being reachable",
  "help.css", ".skip{ position:absolute;", ".skip{ display:none; position:absolute;"),
 ("an Arabic page loses its direction",
  "build_help.py", '{" dir=\\"rtl\\"" if rtl else ""}>', '>'),
 ("a language page claims to be English",
  "build_help.py", '<html lang="{L["tag"]}"{" dir=', '<html lang="en"{" dir='),
 ("an outbound link stops being sandboxed",
  "build_help.py", 'href="{esc(r["Website"])}" rel="noopener"',
  'href="{esc(r["Website"])}" target="_blank"'),
 ("a crisis line stops saying it is always open",
  "data/resources.csv", '"24/7/365"', '"Varies"'),
 ("a resource is listed twice",
  "data/resources.csv", '"Safe Horizon","Domestic',
  '"NYC HOPE — 24-Hour DV Hotline (Safe Horizon)","Domestic'),
 ("a category page loses its jump nav",
  "build_help.py", 'A(\'  <nav class="jump" aria-label="Jump to a kind of help"><ul>\')',
  'A(\'  <nav class="jump" aria-label="Jump to a kind of help" hidden><ul>\')'),
 ("the two halves stop sharing header spacing",
  "help.css", ".sitehead{\n  position:sticky; top:0;",
  ".sitehead{\n  --head-pad:22px;\n  position:sticky; top:0;"),
 ("a website link drops to plain http",
  "data/resources.csv", "https://988lifeline.org", "http://988lifeline.org"),
 ("phone numbers in translated prose stop dialling",
  "build_help.py", "return _DIALABLE.sub(r'<a class=\"dialn\" href=\"tel:\\1\">\\1</a>', text)",
  "return text"),
 ("a description turns into one long sentence",
  "data/resources.csv", "A free pantry on Staten Island",
  "A free pantry located on Staten Island which, subject to availability and "
  "in accordance with applicable eligibility criteria, may be able to provide "
  "groceries to individuals and families who have been determined to be in "
  "need of nutritional assistance at the present time"),
 ("the search stops matching what people actually call things",
  "help.js", "W_ALIAS = 2", "W_ALIAS = 0"),
 ("an unmeasured header follows a language page again",
  "help.css", "body[data-lang] .sitehead{ position:static; }",
  "body[data-lang] .sitehead{ position:sticky; }"),
 ("a dialled number in translated prose shrinks to its glyphs",
  "help.css", '.dialn::after{ content:""; position:absolute; inset:-12px -10px; }', ""),
 ("an inline link is tappable only inside a list again",
  "styles.css", "  .inl{ position:relative; }\n  .inl::after{",
  "  li > .inl{ position:relative; }\n  li > .inl::after{"),
 ("the search box loses its focus ring again",
  "help.css", ".find__box:has(input:focus-visible){\n  outline:3px solid var(--focus);",
  ".find__box:has(input:focus-visible){\n  outline:0;"),
 ("the print hide-list loses its terminator again",
  "help.css", ".cl__all,.clusters__say,.langbar,.sprite,.mast__bg{ display:none !important; }",
  ".cl__all,.clusters__say,.langbar,.sprite,"),
 ("the skip link lands the list under the header again",
  "help.css", ".dir{ display:flex; flex-direction:column;\n  scroll-margin-top:calc(var(--head-h) + 14px); }",
  ".dir{ display:flex; flex-direction:column; }"),
 ("a deep link goes back to racing the browser on a timer",
  "help.js", 'addEventListener("scroll", landOnFragment, { passive: true });',
  'setTimeout(landOnFragment, 300);'),
 ("a card shows one number and dials another",
  "build_help.py", '<a class="pv__call" href="tel:{esc(href)}">',
  '<a class="pv__call" href="tel:311">'),
 ("the language carryover takes the URL raw",
  "help.js", "/[?&]lang=([a-z-]{2,20})/", "/[?&]lang=(.+)/"),
 ("the find card clips its own dropdowns away",
  "help.css", "  border-radius:var(--r); }\n/* This card used to clip",
  "  border-radius:var(--r); overflow:hidden; }\n/* This card used to clip"),
 ("a shut facet stops saying it is filtering",
  "build_help.py", '               f\'        <span class="facet__n" hidden></span>\',\n', ""),
 ("English goes back to the end of the language row",
  "build_help.py",
  '\'  <ul class="langbar__list">\',\n           \'    <li><span class="langbar__here" lang="en" aria-current="page">\'\n           \'English</span></li>\']',
  '\'  <ul class="langbar__list">\']'),
 ("the sub-page hero stops clearing the bar",
  "styles.css", "padding:max(140px, calc(var(--head-h) + 20px)) var(--pad)",
  "padding:140px var(--pad)"),
 ("--head-h goes back to guessing at phone widths",
  "tokens.css", "@media (max-width:359px){ :root{ --head-h:210px; } }", ""),
 ("the hidden attribute stops hiding",
  "tokens.css", "[hidden]{ display:none !important; }", "[hidden]{ display:none; }"),
 # ---- round three: print, contrast, motion, forms, search feedback, SEO
 ("printing loses the numbers under every card",
  "help.css", ".cl__b{ font-size:7pt; color:#000; }",
  ".cl__b{ font-size:7pt; color:#000; display:none; }"),
 ("high contrast mode stops being handled on the light half",
  "help.css", "@media (forced-colors: active){", "@media (forced-colors: never){"),
 ("motion stops being optional on the dark half",
  "styles.css", "@media (prefers-reduced-motion:reduce){",
  "@media (prefers-reduced-motion:no-preference){"),
 ("a form field loses the label that names it",
  "index.html", '<label for="s-email">', '<label>'),
 ("an email field stops being an email field",
  "index.html", '<input id="s-email" type="email" name="email" required',
  '<input id="s-email" type="text" name="email" required'),
 ("the search stops saying it corrected a spelling",
  "help.js", "corrected = fixed.slice();", "corrected = [];"),
 ("the result count stops being announced",
  "build_help.py", '<p class="find__count" role="status" aria-live="polite">',
  '<p class="find__count">'),
 ("a language page stops pointing back at the others",
  "build_help.py", 'f\'<link rel="alternate" hreflang="{L["tag"]}" \'', "''"),
 ("the focus ring stops surviving what is behind it",
  "tokens.css", "--focus:var(--green);", "--focus:transparent;"),
 ("a category page stops naming what it is",
  "build_help.py", '<meta name="description" content="', '<meta name="ignored" content="'),
 ("the directory stops working without JavaScript",
  "build_help.py", 'A(\'  <nav class="jump" aria-label="Jump to a kind of help"><ul>\')',
  'A(\'  <nav class="jump" aria-label="Jump to a kind of help" style="display:none"><ul>\')'),
 ("a resource's description is cut off mid-clause",
  "data/resources.csv", "A free pantry on Staten Island where you pick", "where you pick"),
 # ---- round three: the phases, the doors out of them, and the spelling
 ("a blank screen comes back at every boundary",
  "styles.css", "  --gap:32vh;", "  --gap:50vh;"),
 ("a phase join stops being tighter than a phase boundary",
  "styles.css", "  --gap-in:13vh;", "  --gap-in:30vh;"),
 ("a phase boundary hard-codes its gap instead of tracking the token",
  "styles.css", ".scene{ position:relative; min-height:100svh; display:flex; align-items:center; padding:var(--gap) var(--pad); }",
  ".scene{ position:relative; min-height:100svh; display:flex; align-items:center; padding:32vh var(--pad); }"),
 ("the blocks inside a phase lose their own join",
  "styles.css", "  --gap-in:13vh;", "  --gap-inx:13vh;"),
 ("a jump goes back to landing the heading behind the bar",
  "styles.css", "main > section{ scroll-margin-top:calc(var(--head-h) + 14px); }",
  "main > section{ scroll-margin-top:120px; }"),
 ("Lenis stops being told about the header",
  "script.js", "lenis.scrollTo(target, { offset: -headClearance(), duration: 1.25 });",
  "lenis.scrollTo(target, { offset: 0, duration: 1.25 });"),
 ("a British spelling stops reaching the American page",
  "build_help.py", '    ("program",         "programme programmes"),\n', ""),
 # the guard's own data is the thing most likely to be "tidied" by a spelling
 # pass, and flattening it makes sixteen checks compare a word to itself
 ("the spelling guard starts comparing words to themselves",
  "check.py", '("counselling", "counseling"), ("organisation", "organization"),',
  '("counseling", "counseling"), ("organization", "organization"),'),
 ("the pinned reel comes apart from its own scroll",
  "styles.css", ".scene--pin.scene--tight{ padding-top:0; }", ""),
 ("the page stops reading with scripts off",
  "index.html", "<noscript><style>.focus-in{ filter:none; opacity:1; transform:none; }</style></noscript>", ""),
 ("a chapter summary loses the page behind it",
  "index.html", '<a href="students.html" class="btn btn--solid">What the job actually is',
  '<a href="index.html#top" class="btn btn--solid">What the job actually is'),
]



def snapshot():
    for f in FILES:
        shutil.copy(f, os.path.join(BAK, f.replace("/","_")))

def restore():
    for f in FILES:
        shutil.copy(os.path.join(BAK, f.replace("/","_")), f)

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)

# A mutation only means something against a green baseline. It also catches
# leftover damage from a run that was interrupted before it could restore —
# without this, the next run snapshots the damage and "restores" to it.
base = run("python3 check.py")
if not re.search(r"(?<!\d)0 failed", base.stdout):
    sys.exit("check.py is already failing. Fix that first — or, if a previous "
             "run was interrupted: git checkout -- . && python3 build_help.py")

snapshot()
caught, missed = [], []
try:
  for name, path, old, new in MUTATIONS:
    # Bytes, not text. Text mode converted the CSV's CRLF line endings to LF
    # on write, so a restore from a snapshot taken after that point put a
    # silently different file back.
     src = open(path, "rb").read()
     o, n2 = old.encode(), new.encode()
     if o not in src:
         missed.append((name, "MUTATION DID NOT APPLY"))
         continue
     open(path, "wb").write(src.replace(o, n2))
     run("python3 build_help.py")
     r = run("python3 check.py")
     # "10 failed" contains "0 failed" — the substring test scored ten
     # real catches as misses.
     failed = not re.search(r"(?<!\d)0 failed", r.stdout)
     (caught if failed else missed).append((name, ""))
     restore()
     run("python3 build_help.py")

finally:
  restore()
  run("python3 build_help.py")

print(f"\ncaught {len(caught)} of {len(MUTATIONS)}")
for n,_ in caught: print("   caught  ", n)
for n,why in missed: print("   MISSED  ", n, why)
