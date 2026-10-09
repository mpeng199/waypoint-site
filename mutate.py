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
         "build_help.py","index.html","i18n.py","script.js","check.py",
         "assets/door.js","events.py"]
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
 # .hfoot became the shared .footer in tokens.css (Sep 2026) and this went on
 # targeting a rule that no longer existed: "DID NOT APPLY", every run.
 ("a dark surface loses its focus ring color",
  "tokens.css", ".footer{ position:relative; z-index:3; --focus:var(--gold-lit);",
  ".footer{ position:relative; z-index:3; --focus:var(--green);"),
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
 # the resource's name became its outbound link; the old Website button this
 # targeted is gone, so the mutation had stopped applying
 ("an outbound link stops being sandboxed",
  "build_help.py",
  'target="_blank" rel="noopener">{esc(r["Resource Name"])}',
  'target="_blank">{esc(r["Resource Name"])}'),
 ("a wrapping row becomes a column without nowrap",
  "help.css", ".find__top{ flex-direction:column; flex-wrap:nowrap; }",
  ".find__top{ flex-direction:column; }"),
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
 ("the page stops reading with scripts off",
  "index.html", "<noscript><style>.focus-in{ filter:none; opacity:1; transform:none; }</style></noscript>", ""),
 ("a chapter summary loses the page behind it",
  "index.html", '<a href="students.html" class="btn btn--solid">What the job actually is',
  '<a href="index.html#top" class="btn btn--solid">What the job actually is'),
 # ---- round four: the ten translations. Every one of these is a thing that
 #      was actually true of the file in September 2026, and that only a
 #      native speaker would have caught by reading.
 ("an Arabic sentence takes a Latin comma back",
  "i18n.py", "المزايا، والتنقل، والسكن الميسَّر", "المزايا, والتنقل, والسكن الميسَّر"),
 ("French loses the unbreakable space before a question mark",
  "i18n.py", '"needs_h": "De quoi avez-vous besoin\u202f?",',
  '"needs_h": "De quoi avez-vous besoin ?",'),
 ("the crisis line goes back to translating the English euphemism",
  "i18n.py", "Tiene pensamientos de hacerse daño, o necesita hablar con alguien ahora",
  "No se siente seguro consigo mismo, o necesita hablar con alguien ahora"),
 ("a translation stops using the noun the city prints",
  "i18n.py", '"housing": "Vivienda y refugio",', '"housing": "Vivienda y alojamiento",'),
 ("a language page stops saying an interpreter can be asked for",
  "i18n.py",
  '"প্রশিক্ষিত। নাম না বলেও ফোন করতে পারেন। এই নম্বরগুলোর যেকোনোটিতে দোভাষী "\n'
  '                "চাওয়া যায়: ফোন ধরার পর ইংরেজিতে আপনার ভাষার নাম বলুন।",',
  '"প্রশিক্ষিত। নাম না বলেও ফোন করতে পারেন।",'),
 ("a program stops being named and is only described",
  "i18n.py", "MetroCard za pół ceny (Fair Fares NYC)", "MetroCard za pół ceny"),
 ("one page starts using two words for one thing",
  "i18n.py", '"disability": "残疾", "record": "出狱之后",',
  '"disability": "残障", "record": "出狱之后",'),
 ("a translated string picks up a double space",
  "i18n.py", "Денежное пособие, счёт за отопление",
  "Денежное пособие,  счёт за отопление"),
 ("the student word goes back to meaning undergraduate",
  "i18n.py", '            "Uczniowie", "Organizacje"],',
  '            "Studenci", "Organizacje"],'),
 # ---- round five: motion (October 2026). Every one of these looks fine on
 #      the laptop it was made on: a hover lift only sticks under a thumb,
 #      per-frame smoothing only runs fast at 120Hz, a missing press only
 #      shows on a slow phone, and a hard-edged scrim only on a desktop door.
 ("a control stops answering a press",
  "tokens.css", "  .rail__nav a,.chip,.fev__arw,.cal__arw):active{ scale:var(--press); }",
  "  .rail__nav a,.fev__arw,.cal__arw):active{ scale:var(--press); }"),
 ("the Call button's press snaps instead of giving",
  "help.css", "  transition:background .16s var(--ease),\n    scale var(--t-press) var(--ease-out); }\n.call:hover",
  "  transition:background .16s var(--ease); }\n.call:hover"),
 ("the iPhone loses every press on the directory",
  "help.js", '  document.addEventListener("touchstart", function () {}, { passive: true });\n', ""),
 ("an emergency number lifts under a thumb again",
  "help.css", "@media (hover:hover) and (pointer:fine){ .sos__list a:hover{ transform:translateY(-2px); } }",
  ".sos__list a:hover{ transform:translateY(-2px); }"),
 ("the shared arrow leans on touch again",
  "tokens.css", "@media (hover:hover) and (pointer:fine){\n  :where(a,button):hover > .arr,",
  "@media all{\n  :where(a,button):hover > .arr,"),
 ("the carousel glides whatever the reader asked for",
  "help.js", "track.scrollBy({ left: dir * step(), behavior: glide() });",
  'track.scrollBy({ left: dir * step(), behavior: "smooth" });'),
 ("the reading veil settles per frame again",
  "script.js", "veilNow += (want - veilNow) * settle(0.09);",
  "veilNow += (want - veilNow) * (reduced ? 1 : 0.09);"),
 ("the door's parallax settles per frame again",
  "assets/door.js", "px = lerp(px, pxTarget, k); py = lerp(py, pyTarget, k);",
  "px = lerp(px, pxTarget, 0.055); py = lerp(py, pyTarget, 0.055);"),
 ("a stylesheet types its own curve",
  "help.css", ".call:hover{ background:var(--green-2); }",
  ".call:hover{ background:var(--green-2); transition-timing-function:cubic-bezier(.4,0,.2,1); }"),
 ("transition: all comes back",
  "styles.css", ".tlink:hover{ border-color:var(--gold); }",
  ".tlink:hover{ border-color:var(--gold); transition:all .3s; }"),
 ("the hero's ground gets its hard edge back",
  "styles.css", "radial-gradient(closest-side, rgba(8,15,11,.55) 0%, rgba(8,15,11,.4) 52%, rgba(8,15,11,0) 100%)",
  "radial-gradient(75% 150% at 50% 50%, rgba(8,15,11,.55) 0%, rgba(8,15,11,.4) 52%, rgba(8,15,11,0) 78%)"),
 ("the closing slit shines through the last line again",
  "styles.css", ":is(html.closing) .poster__glow{ transform:translate(-50%,-50%); opacity:.2; }",
  ":is(html.closing) .poster__glow{ transform:translate(-50%,-50%); opacity:1; }"),
 ("the hero entrance reaches the phone",
  "styles.css", "@media (min-width:901px){\n  .hero__eye,.hero__l", "@media all{\n  .hero__eye,.hero__l"),
 ("a dead scroll cue comes back",
  "styles.css", "@keyframes cue-x{ to{ transform:translateX(100%); } }\n",
  "@keyframes cue-x{ to{ transform:translateX(100%); } }\n@keyframes cue{ to{ top:100%; } }\n"),
 ("the scroll cue goes back to animating left",
  "styles.css", "@keyframes cue-x{ to{ transform:translateX(100%); } }",
  "@keyframes cue-x{ to{ left:100%; } }"),
 ("the scroll cue loops for the life of the page again",
  "styles.css", "html.hasjs:not(.at-door) .hero__cue i::after{ animation:none; }\n", ""),
 ("a long feed title stretches the featured row again",
  "help.css", ".fev__h a{ display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:3;\n  overflow:hidden; }", ""),
 ("the events list leaves its pin behind again",
  "events.py", "<span class=\"ev__at\">{PIN}<span>{esc(where(e))}</span></span>'", "{PIN}<span>{esc(where(e))}</span>'"),
 ("the rail goes back to numbering its parts",
  "script.js", 'var h = sc.querySelector("h2, h3");', 'var h = null;'),
 ("the lamp goes back to animating left",
  "tokens.css", "transition:transform .4s var(--ease-in-out), width .4s var(--ease-in-out), opacity .35s var(--ease); }",
  "transition:left .4s var(--ease-in-out), width .4s var(--ease-in-out), opacity .35s var(--ease); }"),
 ("a disclosure leaves as slowly as it arrives",
  "styles.css", "  transition:opacity var(--t-press) var(--ease), transform var(--t-press) var(--ease); }\n.ways--js .ways__blurb",
  "  transition:opacity .42s var(--ease-out) .06s, transform .42s var(--ease-out) .06s; }\n.ways--js .ways__blurb"),
 ("a button's hover slows back to .3s",
  "styles.css", "  transition:background var(--t-hover) var(--ease), border-color var(--t-hover) var(--ease),",
  "  transition:background .3s var(--ease), border-color .3s var(--ease),"),
 ("the header stays translucent for a reader who asked for solid ground",
  "tokens.css", "  .sitehead.stuck{ --head-bg:var(--head-solid); backdrop-filter:none;",
  "  .sitehead.stuck{ backdrop-filter:none;"),
 # ---- the Find help menu (October 2026)
 ("a page's Find help menu drifts from the others",
  "index.html", '<li><a href="help.html#featured">Featured events</a></li>',
  '<li><a href="help.html#featured">Events</a></li>'),
 ("search is offered with no script to run it",
  "tokens.css", "html:not(.hasjs) .findmenu__search{ display:none; }", ""),
 ("arriving at search leaves the cursor on the page",
  "help.js", "      setTimeout(land, 0);\n", ""),
 ("the featured events lose the anchor the menu points at",
  "events.py", 'class="fev" id="featured"', 'class="fev"'),
 ("Escape stops closing the menu",
  "script.js", 'if (e.key !== "Escape" || !findmenu.open) return;',
  'if (e.key !== "Esc" || !findmenu.open) return;'),
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
# Everything below runs only when this file is the program.
#
# It used to run on import, which is a trap with the blast radius of the
# whole repo: `import mutate` to read MUTATIONS — to count them, to run a
# subset, to list them in a report — rewrote all ten files seventy-one times
# instead. The finally block put them back, so nothing was lost and nothing
# said anything; it just took eleven minutes and looked like a hang. A module
# that damages the working tree because somebody imported it is not one
# anybody can build tooling on, and being built on is the point of this file.
def main():
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


if __name__ == "__main__":
    main()
