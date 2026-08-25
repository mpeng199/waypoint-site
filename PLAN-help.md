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

## Where it stands, 340 resources and 62 commits on

- **`help.html` is a way in, not the directory.** One cluster per kind of
  help, three real places with real numbers under each, and a link to that
  kind of help's own page.
- **Seventeen category pages**, each built to be skimmed: a rail of what is on
  it, resources in named buckets, a Start here block, and every neighbouring
  kind of help one tap away.
- **340 verified resources** across 17 categories, 276 of them checked
  against a first-party source on 24-25 August 2026.
- **Ten languages** — Local Law 30's ten — each panel naming every kind of
  help in that language, and the search box understanding all ten.
- **One palette.** `tokens.css` is the only place a brand hue exists.
- **`python3 check.py`: 1,833 passing, none failing.**

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
- [x] **S27** **Search in ten languages.** The tokenizer was deleting every
      non-ASCII character, so the page could be read in ten and searched in
      one. `NEED_WORDS` carries the query vocabulary; it ships once per page.
- [x] **S27b** **Plain English.** Every agency word a reader meets said in
      ordinary English: no FQHC, no DV, no sliding scale, no arrears, no slash
      between two words, no claim with a clock on it, no statement of who
      qualifies. Guarded, all of it.
- [x] **S28** **Phone verification.** `verify_phones.py` asks each
      organisation's own site whether the number we print is its number.
      Eleven had drifted, one by a single digit.
- [ ] **S15** Push + PR — still not done. Outward-facing; waiting on a
      go-ahead.

## What still needs a human

1. **The push.** 62 commits sit on
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
- **63 rows still carry a June verification date** — not because anything is
  known to be wrong with them, but because their sites draw the phone number
  in JavaScript or refuse a scripted request. `verify_phones.py` reports them
  as UNSEEN, never as confirmed.
- **Some rows have no phone**, only a website. Correct for a lottery portal or
  an online screener; a gap for anything else. `merge_rows.py` refuses a row
  with neither.

## The last pass (25 August)

Five things the audits turned up, each fixed at the cause rather than the
symptom, each left with a break-tested guard:

1. **A focus ring nobody could see.** In the deep green footer of all twenty
   pages the ring was `--green` on `--green-deep`: 1.24:1. Every component had
   been naming its own ring colour, so the ring knew about the button and
   nothing about the room. It is one token now, set per surface. Worst ring on
   any page is 7.6:1. Also restored a ring under forced colours, where the two
   controls that hand theirs to a wrapper had nothing left.
2. **"Checked August 2026" over a list a fifth of which said June.** The date
   was derived — from `max()`, the most flattering true number in the file. It
   prints the span now, and a category page's printed header spans that
   category's own rows.
3. **911 dialled in English and was printed as text in ten other languages.**
   The reader least able to use the English page was the one asked to memorise
   three digits. `dial()` links them at build time; thirty links per page.
4. **Footer column labels read h2 → h4** to anything navigating by heading,
   because h4 was the size wanted.
5. **Ten more descriptions that described the organisation rather than the
   help** — "the nation's largest youth employment program" says nothing to
   somebody who needs a summer job.

And two guards that were passing without checking anything: the date guard
matched a wording that no longer existed, and derived its expectation from the
function it was testing.

## The language pages (25 August)

Ten pages, one per Local Law 30 language, replacing the ten `:target` panels.
Same components, same order, same spacing as the English front page.

Six things the audits turned up while building them, each fixed at the cause:

1. **Eighteen headings addressed only men.** "Nie jestem bezpieczny", "Я служил
   в армии", "estoy solo", "خدمت في الجيش", "میں اکیلا نوجوان ہوں" — the
   obvious first-person phrasing in Polish, Russian, Spanish, Arabic and Urdu
   agrees with a gender the site cannot know. All eighteen now use a
   construction that does not agree.
2. **Ten thousand pixels of empty cream on Arabic and Urdu.** The skip link was
   parked at `left:-9999px`, which on a right-to-left page is off the *end* —
   the direction the page scrolls. The reflow check had been measuring
   `body.scrollWidth` and the overflow was on the documentElement.
3. **"Last checked June–August 2026"** in English on all ten, under a sentence
   in Bengali. The date is the one thing on that line a reader checks.
4. **Korean broke words in half**, four times on the first screen.
5. **The names only a screen reader hears** — "Waypoint home", the primary nav —
   were English on pages that were not.
6. **The Chinese masthead had a space in the middle** of its title, because the
   two halves were joined the way English joins them.

And two guards that agreed with the code instead of checking it: the
italic-script check asked `build_help.NO_ITALIC` which languages have an
italic, and the `?lang=` check looked for one particular spelling of a guard
clause.

Still needs a human: **a native speaker of each language should read their own
page end to end.** Nothing in `i18n.py` is machine output, and nothing in it
has been read by somebody who speaks the language.

## The quarterly pass a person has to do

Two things in this project cannot be automated from here, and pretending
otherwise is how the ActionNYC and SNAP links stayed dead:

1. **Open the 34 pages `check_links_live.py --browser-list` prints.** They are
   on hosts that build the page in the browser, so a dead page and a live one
   are byte-for-byte identical to anything that does not run JavaScript. Look
   for "you have reached an outdated or non-existing page". Two of the
   thirty-four were dead when this was first done by hand, and one of them was
   food stamps.
2. **Have a native speaker read each of the ten language pages end to end.**
   Nothing in `i18n.py` is machine output and nothing in it has been read by
   somebody who speaks the language.

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
