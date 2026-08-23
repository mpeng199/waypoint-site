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
- [ ] **S8** Print / leave-behind sheets
- [ ] **S9** Extend `check.py` to cover the resident surfaces
- [ ] **S10** Browser QA, desktop + phone, iterate
- [ ] **S11** Polish, commit, PR

## Invariants that must not break

- The honesty statement, verbatim, on every surface that offers help.
- The eight nevers: no volunteer reads a document, states eligibility, quotes
  a deadline, or predicts an outcome. Directory copy must not imply otherwise.
- No numeric track-record claims. "114 resources" is a count of the directory,
  not a claim about people helped — keep that distinction sharp.
- No "Companionship", no schools/replication.
- `python3 check.py` green before every commit. Baseline: 378 passed.
