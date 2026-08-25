# Reorganising Waypoint around the people it serves

**Goal (user, 2026-08-23):** reorganise the site for *underprivileged NYC
residents who need help*, make every resource we offer extremely easy to
navigate, model the information architecture on Community Health Advocates,
keep it modern.

**Extended (user, 2026-08-24):** make the two halves of the site read as one
theme; review the translations properly and make them consistent throughout;
expand the directory by deep research, verifying that every programme is real;
cluster "find help" into manageable chunks with an expand-to-a-page option;
and make the resident side consistent with the narrative side.

## The finding that shaped the first half

We held a verified directory of NYC resources and **published none of it**.
The headline spoke to somebody with a bill they could not pay and every button
under it asked that person for their organisation's letterhead. So: give
residents their own front door and put the directory behind it, and keep the
narrative for the audiences it was written for.

## Where it stands, 311 resources and 38 commits on

- **`help.html` is a way in, not the directory.** One cluster per kind of
  help, three real places with real numbers under each, and a link to that
  kind of help's own page.
- **Seventeen category pages**, each built to be skimmed: a rail of what is on
  it, resources in named buckets, a Start here block, and every neighbouring
  kind of help one tap away.
- **311 verified resources** across 17 categories, every one of them
  checked against a first-party source on 24-25 August 2026.
- **Ten languages** — Local Law 30's ten — each panel naming every kind of
  help in that language.
- **One palette.** `tokens.css` is the only place a brand hue exists.
- **`python3 check.py`: 1826 passed, 0 failed.**

## Sequences

- [x] **S1** Discovery, plan, rebase onto `origin/main`
- [x] **S2** Data pipeline: CSV → need taxonomy → build-time generator
- [x] **S3** `help.html` resource finder: search, filters, resource rows
- [x] **S4** Triage front: need index + hand-picked emergency strip
- [x] **S5** `index.html` reorganised: residents first
- [x] **S6** Accessibility hardening
- [x] **S7** Language access (7 panels)
- [x] **S8** Print / leave-behind sheets
- [x] **S9** Extend `check.py`
- [x] **S10** Browser QA at five widths
- [x] **S11** Handoff docs
- [x] **S12** Link rot sweep (`check_links_live.py`)
- [x] **S13** Realistic-query sweep
- [x] **S14** Final polish
- [x] **S16** Directory data quality
- [x] **S17** Runtime code review
- [x] **S18** Docs realigned
- [x] **S19** Deadline guard
- [x] **S20** **One theme.** `tokens.css`; the directory's masthead is the
      painted valley the door opens onto; same lockup, same nav pill, same
      gold-italic headings, same deep-green footer. Neither stylesheet may
      restate a brand hue.
- [x] **S21** **Clustering.** The directory split into a front page of
      clusters plus one page per need. Front-page search runs off a compact
      index in the document; category pages still hide rows that are already
      there.
- [x] **S22** **Deep research.** 118 → 311 resources. Sources: nyc.gov's own
      programme API, then organisation-by-organisation verification.
- [x] **S23** **Translations.** Seven languages → the ten Local Law 30 names.
      Panels now navigate the whole directory rather than describing it.
- [x] **S24** **Second query sweep.** Loose fallback restored, relevance
      ranking, phrase bonus, stemmer; five data gaps closed.
- [x] **S25** **A11y and print.** 320px at 200% text no longer scrolls
      sideways; contrast audited across every new component; the printed sheet
      had a blank where its count should be.
- [x] **S26** **Third research push.** Community organisations by borough and
      by language.
- [ ] **S15** Push + PR — still not done. Outward-facing; waiting on a
      go-ahead.

## What still needs a human

1. **The push.** 38 commits sit on
   `claude/website-accessibility-redesign-2b15ac`, unpushed.
   `git push -u origin claude/website-accessibility-redesign-2b15ac`.
2. **A native-speaker review of the ten in-language panels.** They are short,
   plain, and carry nothing a reader must act on precisely — the only
   instructions are 911, 988 and 311 — but nobody who speaks these languages
   has read them. The multilingual students are the obvious reviewers.
3. **Whether publishing every category is further than intended.** The
   directory now spans 17 categories including reentry and
   disability. `PRODUCT.md` records the reasoning; the fix, if it reads as too
   far, is to narrow what `data/resources.csv` publishes, not to hide pages.
4. **Hudson Guild.** Researched, written up, then dropped: hudsonguild.org
   refuses connections on 443 from three separate network paths and its number
   came from a third-party listing. Worth a phone call.

## Known data weaknesses (source, not code)

- **Languages is still vague on most rows.** Named-language coverage improved
  a lot with the community organisations — Chinese, Bengali, Korean, Urdu and
  Polish now have real numbers behind them — but most rows still say
  "Multiple", which records nothing useful. The filter treats a vague answer
  as "reachable through an interpreter" so it hides nothing, and floats the
  rows that name the language. The real fix is to ask each partner which
  languages they staff.
- **Hours are not machine-usable.** Dozens of distinct formats. Readable, not
  filterable, and there should be no "open now" filter until the data supports
  one.
- **Staten Island is thin but no longer empty.** Project Hospitality and the
  Community Health Center of Richmond are now in, and the filter floats local
  results above citywide ones so the shape of the gap stays visible.
- **Some rows have no phone**, only a website. Correct for a lottery portal or
  an online screener; a gap for anything else. `merge_rows.py` refuses a row
  with neither.

## Invariants that must not break

- The honesty statement, verbatim, on every surface that offers help.
- The eight nevers: no volunteer reads a document, states eligibility, quotes
  a deadline, or predicts an outcome.
- No numeric track-record claims. The counts on the resident pages count the
  directory, not people helped — and they are generated, never typed.
- No "Companionship", no schools/replication.
- Every guard added is break-tested: deliberately tripped to confirm it fails
  when the thing it protects fails.
- `python3 check.py` green before every commit.
