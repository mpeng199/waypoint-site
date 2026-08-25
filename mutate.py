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
         "build_help.py","index.html","i18n.py"]
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
 ("a dark surface loses its focus ring colour",
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
]

def snapshot():
    for f in FILES:
        shutil.copy(f, os.path.join(BAK, f.replace("/","_")))

def restore():
    for f in FILES:
        shutil.copy(os.path.join(BAK, f.replace("/","_")), f)

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)

snapshot()
caught, missed = [], []
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

print(f"\ncaught {len(caught)} of {len(MUTATIONS)}")
for n,_ in caught: print("   caught  ", n)
for n,why in missed: print("   MISSED  ", n, why)
