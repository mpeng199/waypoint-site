# Product

## Register

brand

## Users

**The website is built for three audiences, in this order.** The others still matter to the programme; they are simply not who the site is written to convert.

**1. Community members — the people the programme exists for — primary since August 2026.** Seniors, low-income and immigrant New Yorkers who need help now. Until then this site did not serve them at all: it held a verified directory of NYC resources and put none of it online, so a resident could not reach a single one of them from here. `help.html` is that directory, and it is now the destination the home page leads with. The single thing they must be able to do: **find a real phone number for the right free help, in under a minute, without giving us anything.** Design constraints follow from who they actually are — an old phone, transit data, possibly a library terminal with JavaScript off, possibly a screen reader, possibly no English. Hence: every row served in the HTML, no scroll-jacking, no WebGL, 44px targets, an 18px floor, seven in-language entry points, and a printable sheet for the ones who have no device at all.

**2. Resource holders — the organisations whose help we distribute.** Consumer assistance programmes, charity-care nonprofits, legal services, prescription assistance programmes, agency helplines. They have a real, chronic problem: eligible people never hear about them. The single thing they must believe by the end of the page: *these students can put my materials in front of people I have never reached, and they will not overstate what I do.* We are offering distribution, not requesting a favour, and the page has to read that way.

**2b. Venue hosts (libraries, senior centers, NYC Aging programmes, faith spaces, FQHC outreach) — the second ask.** Shelf space for reviewed materials, or a small table at programming they already run. Lower stakes than the original co-host ask, and deliberately sequenced behind at least one confirmed resource partner: naming a real partner is what makes this ask land.

**3. Students (14–18).** Seeking meaningful volunteer work that matters. Want clear structure, reliable commitment windows (semester cohorts), peer community, and credibility. One strong chapter and a form, not a co-equal half of the site.

**On the ordering above.** Community members were previously listed last, described as "reached in person at events rather than through this website", and the site was written accordingly — the headline spoke to somebody with a bill they could not pay and every button under it asked that person for their organisation's letterhead. That was the reorganisation of August 2026. Partners and students keep their chapters and their forms, unchanged and still necessary; they simply no longer come first on a page about frightened people.

The honesty statement is still written for community members, and now they can actually read it: it appears on `help.html` and on every printed sheet, because a leave-behind is exactly where somebody mistakes a student for a professional.

**Funders & fiscal sponsors:** deliberately deferred until there is a track record to show. No funding chapter on the site yet.

**Schools & advisors (replication):** deliberately deferred. The Schools chapter, its form, and `schools.html` were removed in August 2026. Do not reintroduce them without a decision to restart that line of work.

## Product Purpose

Waypoint helps New Yorkers buried in medical bills or fighting a denied insurance claim reach the free experts who can actually help — especially elderly, low-income, and immigrant residents.

New York already built the infrastructure: hospitals are required to offer financial assistance to patients under certain incomes, the state runs an independent appeal for denied claims, free counselors take coverage disputes in dozens of languages, and national nonprofits will file a charity care application at no cost. Almost nobody who qualifies ever hears about any of it. The help is real, it is free, and it is invisible, which makes this a distribution problem rather than a funding one — and distribution is something a student corps can genuinely provide before it has ever run an event.

We are not building parallel services or clinical expertise. We are building the **human bridge** and the **reliable volunteer pipeline** that the existing system lacks.

Success is measured by: community members reaching resources they qualify for, partners able to count on consistent volunteer presence, student volunteers gaining meaningful experience and retention across semester cohorts, and a replicable model other schools can adopt.

## Brand Personality

**Three words:** Warm, Grounded, Catalytic

**Voice & tone:** 
- Warm and human-centered — genuinely about connection and presence, not clinical distance
- Trustworthy and expert — credibly run, every boundary thought through, safety-first
- Hopeful without being naive — this is doable; change happens when people show up
- Respectful of communities served — never patronizing, never overclaiming authority

**What we communicate:** Simplicity, honesty, reliability. We tell people exactly who we are, what we can and cannot do, and why it matters. No jargon. No clinical authority claims. No startup energy.

## Scope of the programme, as described publicly

The site leads with **Medical Bills & Coverage Navigation** (Phase A) and this is Waypoint's public identity. Three activities, in order of how much time they take: awareness and distribution (~60%), triage and routing (~30%), warm handoff (~10%).

**August 2026, and this is a scope decision worth re-confirming:** `help.html` lists the whole verified directory — food, housing, legal, benefits, and the rest — not only the billing resources. The distinction that keeps this inside the boundary is that the directory *points at other organisations' help*; it does not offer Waypoint's navigation service for those categories. The page says so in its own words ("We do not run any of the programs on this page. We help people find them"), and no form, no routing and no volunteer commitment attaches to any of it. A partner reading it should understand that we distribute their materials, not that we staff a general-purpose helpline. If that reads as further than intended, the fix is to narrow what `data/resources.csv` publishes, not to hide the page.

**General Resource Navigation is the second track, and the site names it without describing the sequencing.** It gets a full scene of its own — *"It was never only about the bill"* — naming it as where Waypoint started and as half of why we exist, and stopping there. The phasing and the reasons behind it are operating decisions, not visitor copy: everyone reading that page is deciding whether to volunteer or to work with us, and neither decision is helped by a roadmap. `check.py` now fails the build on "second track", "sequenced behind" and "half-built" appearing on any page.

Internally none of that changed. It remains sequenced behind Phase A and gated on six unlock criteria (confirmed partners, a legal review cleared, an active trained cohort, completed distribution runs, a named second lead, a written impact report). The site still never offers it as a service available today — that would invite a partner to ask for it now, which is the scope creep the narrowing was meant to prevent — but it says plainly that it is half of what Waypoint is.

The Companionship track is undecided and appears on no public surface. `check.py` fails the build if the word appears at all.

**The eight nevers are the operating spine and constrain every word of copy.** A volunteer never: reads or interprets a bill, denial letter, or insurance document (not even to help someone understand it); drafts or fills in an appeal or application; says whether someone qualifies; states a deadline; takes custody of documents; records a name beside medical or financial detail; determines someone's plan type; or predicts an outcome. Any copy that implies otherwise is a defect, and `check_billing_boundaries` in `check.py` fails the build on the affirmative forms.

Status is stated plainly: **Waypoint has not held its first event.** The site turns that into the ask — the first host is the founding branch, shapes how the programme runs, and is named in the first semester report. No numbers are claimed anywhere, because there are none yet. `check.py` fails the build if a numeric track-record claim appears.

## Anti-references

**Avoid:**
- Clinical or medical-tech aesthetic — nothing that makes us look like a health-tech startup or a provider
- Slick, minimalist, future-forward energy — too detached for what this is about
- Patronizing or oversimplified tone — the communities we serve are intelligent; respect that
- Exclamation-point enthusiasm or cutesy phrasing — this is serious work with vulnerable adults
- Dense, legalese-heavy copy — accessibility means clarity, not compliance jargon
- Overclaiming or vague partnership asks — be specific about what we need and why

## Design Principles

1. **Credibility through clarity.** Every boundary, every role, every process is stated plainly. No fine print. Busy adults (partners, faculty) must trust us in under a minute.

2. **Honesty is the brand.** The "what we are / what we are not" statement is the most important thing on every surface. It prevents harm and builds trust with the communities we serve.

3. **Safety first, always.** Visual hierarchy and information design serve guardrails and clarity over aesthetics. The hard boundaries are the most visible thing, not buried.

4. **Design for the room.** Materials work equally well as PDFs, printed leave-behinds, and on-screen. Language works for multilingual communities, older adults, and people with limited digital literacy.

5. **Warm without precious.** The palette is intentional (green, gold, cream) and the typography sophisticated (Fraunces + Inter), but nothing decorative that distracts from the message.

## Accessibility & Inclusion

- **WCAG AA minimum** (color contrast, keyboard navigation, screen-reader compatible)
- **Emphasis on clarity for multilingual users:** simple vocabulary, visual hierarchy over jargon, consideration for translated materials
- **Design for older adults:** generous spacing, readable type sizes, high contrast where it matters
- **Immigrant-sensitive:** avoid assumptions about documentation status; route immigration questions to professionals
- **Print-first thinking:** materials must work as PDFs and printed documents, not just screens

## Amendment: craft vs. the "slick" anti-reference (August 2026)

The August 2026 redesign takes its **mechanics** from technically ambitious sites (a real-time 3D hero, inertial scrolling, scroll-choreographed chapters) while explicitly rejecting their **register**. The anti-reference above still stands: no neutral grotesque, no luxury pacing, no startup gloss. Fraunces + Inter, the green/gold/cream palette, the painterly landscapes and the plain warm voice are unchanged, and they are what keep the site from reading as a health-tech product.

Concretely, "not slick" is enforced by: no card grids, no numbered step lists, no section labels, no stock photography, no numeric bragging, and a page whose loudest single moment is a statement about what we refuse to do.

**These constraints are scoped to the narrative journey (`index.html`), not to `help.html`.** The directory is a different kind of object and needs the opposite affordances: 118 resources have to be scannable, so they are rows in a grid, each group carries a heading, and the whole page is labelled. The resident chapter on the home page still obeys the rule — it is a flowing list of sentences, not a mosaic of tiles.

---

**Core constraint:** Every surface must answer the question a busy adult or vulnerable community member asks in the first 10 seconds: *Who are these students? Can I trust them?* The answer is yes — because every boundary is thought through and written down.
