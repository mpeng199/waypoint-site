# Reorganising Waypoint around the people it serves

**Goal (user, 2026-08-23):** reorganise the site for *underprivileged NYC
residents who need help*, make every resource we offer extremely easy to
navigate, model the information architecture on Community Health Advocates,
keep it modern.

## The finding that shapes everything

We hold a verified directory of **114 NYC resources** across 14 categories
(`data/resources.csv`, last verified 2026-06-30). **None of it is on the
site.** 96 of the 114 are explicitly undocumented-friendly and 81 are free.
That directory is "the resources we offer", and today a resident cannot reach
a single one of them from this website.

Meanwhile `index.html` is a scroll-choreographed narrative with a WebGL door,
inertial scroll and four pinned scenes, written to convert *partners* and
*students*. It is good at that job. It is the wrong artefact for a frightened
68-year-old with a bill, on an old Android, in Cantonese.

So this is not a re-skin. It is: **give residents their own front door and put
the directory behind it**, and keep the narrative for the audiences it was
written for.

## Decisions

1. **`help.html` is the new centre of the site** — the resource finder. Built
   from the CSV at build time, so all 114 resources are in the HTML and the
   page works with JavaScript off, on a slow phone, in a screen reader. JS
   only filters what is already there.
2. **Need-shaped entry, not category-shaped.** Residents do not search
   "Multi-Service / Navigation". They arrive with "I can't pay this bill" or
   "I need food today". The 14 CSV categories map to plain-language needs.
3. **`index.html` leads with residents.** The narrative survives, demoted
   below a resident entry point. Partners and students keep their chapters.
4. **No scroll-jacking, no WebGL, no inertial scroll on any resident
   surface.** Those are craft for a partner with a MacBook, and a tax on
   everyone else.
5. **Print is a first-class output.** Students hand people paper at tables.
6. **PRODUCT.md's "no card grids" constraint is scoped to the narrative
   journey**, not to a directory of 114 resources. A directory needs scannable
   rows. Flagging this explicitly rather than quietly breaking the rule.

## Sequences

- [x] **S1** Discovery, plan, rebase onto `origin/main` (local main was 28 commits stale)
- [x] **S2** Data pipeline: CSV → need taxonomy → build-time generator *(build_help.py, 15 needs, synonym expansion, contact() + self-check)*
- [x] **S3** `help.html` resource finder: search, filters, resource rows *(121 rows / 15 groups, help.css, help.js)*
- [x] **S4** Triage front: "What do you need help with?" + crisis surfacing *(folded into S3: need index + hand-picked emergency strip)*
- [x] **S5** `index.html` reorganised: residents first *(hero CTA, #help chapter third, nav, skip link, close, footer)*
- [x] **S6** Accessibility hardening *(contrast 20/20 pass AA; min-width:0 grid fix; BCP-47 lang tags; 44px targets; 320px & 200%-text verified)*
- [x] **S7** Language access *(7 in-language panels opening on :target, language bar on both pages, JS follow-through to the filter)* — **translations need a native-speaker review before launch**
- [x] **S8** Print / leave-behind sheets *(prints whatever the filter shows; disclosures opened for paper; emergency numbers and honesty statement on every sheet)*
- [x] **S9** Extend `check.py` *(9 new guards, 522 checks; each verified to fail when the thing it guards is broken)*
- [x] **S10** Browser QA *(1400/900/500/390/320 widths, mobile drawer, keyboard order, every interaction; emergency block regridded 1/2/4)*
- [x] **S11** Handoff *(DESIGN.md now documents the directory, the build step, and the four safety decisions; corrected its now-false "No build step" claim)*
- [x] **S12** Link rot sweep *(check_links_live.py; 9 URLs fixed including both
      shelter intake pages, which were 404 behind a WAF 403; Baby Buggy renamed
      to Good+ Foundation)*
- [x] **S13** Realistic-query sweep *(60 real phrasings; 17 failures -> 4 benign.
      Word-start matching, relevance ordering, crisis/DV vernacular, and four
      missing medical-bill resources added — the directory had none)*
- [x] **S14** Final polish *(no-JS search box, doors guard, start-here ordering; 529 checks)*
- [x] **S16** Directory data quality *(language filter reached 6 of 118 for Arabic; now 85, with explicitly-named rows floated)*
- [x] **S17** Runtime code review *(search was indexing button chrome; mobile
      back-link restored; suite now fails if a check asserts nothing)*
- [x] **S18** Docs realigned *(PRODUCT.md audience order, the "no card grids"
      scope, the directory-breadth scope decision; copy at reading grade 4.2)*
- [x] **S19** Deadline guard *(the cohort training doc says three official NY
      sources gave three different answers for the same appeal window — the
      site now cannot state one, on any page)*
- [ ] **S15** Push + PR — not done: outward-facing, waiting on your go-ahead

## Known data weaknesses (source, not code)

- **`Languages` is "Multiple" on 77 of 118 rows**, which records nothing
  useful. No row names Arabic at all, one names Bengali, one Korean, one
  Haitian Creole. The filter now treats a vague answer as "reachable through
  an interpreter" so it hides nothing, and floats the rows that actually name
  the language — but the real fix is at the source. Worth asking each partner
  which languages they staff, and recording them.
- **`Hours` has 51 distinct formats** for 118 rows ("Mon–Fri", "Vary by site",
  "24/7 online", "By appointment"). Readable, not machine-usable, so there is
  no "open now" filter and should not be one until the data supports it.
- **Staten Island has one borough-specific resource in the whole directory**,
  and that one lists all five boroughs anyway. Manhattan has 16, Brooklyn 10,
  the Bronx 9, Queens 8. A Staten Island resident filtering to their borough
  sees almost nothing but citywide hotlines. The filter now floats local
  results above citywide ones so the shape of that is at least visible, but
  the gap is real and only more outreach fixes it.
- **10 rows have no phone number**, only a website. That is correct for a
  lottery portal or an online screener; it is a gap for anything else.

## Where this stopped, 23 Aug 2026, 10pm

21 commits on `claude/website-accessibility-redesign-2b15ac`, **not pushed** —
that is outward-facing and was never asked for. `git push -u origin
claude/website-accessibility-redesign-2b15ac` when wanted.

`python3 check.py` — 537 passing, 0 failing. `python3 build_help.py` — clean,
and re-running it leaves `help.html` byte-identical, so the committed file is
the generator's output.

**Three things still need a human decision**, all recorded above and in the
summary artifact: the push, a native-speaker review of the seven translations,
and whether publishing every resource category (rather than only billing) is
further than intended.

**Every guard added this day was break-tested** — deliberately tripped to
confirm it fails when the thing it protects fails. That habit caught a bug in
the checker itself: two guards had been silently re-indented out of service
while the suite went on reporting "0 failed". `check.py` now fails if any
check function runs and asserts nothing.

## Invariants that must not break

- The honesty statement, verbatim, on every surface that offers help.
- The eight nevers: no volunteer reads a document, states eligibility, quotes
  a deadline, or predicts an outcome. Directory copy must not imply otherwise.
- No numeric track-record claims. The count on help.html is a count of the
  directory, not a claim about people helped — keep that distinction sharp.
  Counts in prose go stale; prefer naming the source over repeating a number.
- No "Companionship", no schools/replication.
- `python3 check.py` green before every commit. Baseline: 378 passed.
