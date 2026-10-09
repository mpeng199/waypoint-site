# Motion

How things move on this site, why, and how that is checked. Written in October
2026 from a full review of every animation on both halves of the site, run
against five craft standards: `apple-design` (Apple's WWDC fluid-interface
talks, translated for the web), `emil-design-eng`, `review-animations`,
`improve-animations` and `find-animation-opportunities` (Emil Kowalski's
design-engineering standards), all in `.agents/skills/`. Locations marked
"was" are as of `89470c0`, the commit the review started from.

The brief was **no crazy changes, just make it stand out.** So almost
nothing here is new motion. It is the site's existing motion made
consistent, made to answer the hand, and made to behave the same on every
screen it reaches. Then there are three small additions, each at a moment
that happens once.

## Findings at a glance

Ordered by leverage. Every one is fixed in this change, and each has a guard
(see "How it is checked").

| # | Severity | Category | Location (was) | Finding | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | HIGH | feedback | everywhere | no `:active` state on any control on any page | the press, §1 |
| 2 | HIGH | contrast | `styles.css:245` | closing headline on phones sits on the poster's full-strength slit; 10% of its italic under 3:1, worst 1.46:1 | the far side of the door, §7 |
| 3 | HIGH | craft | `styles.css:700` | the hero's scrim stops in a straight line and cuts the door's slit into three | §6 |
| 4 | MEDIUM | accessibility | `help.js:167`, `:317` | two scripted smooth scrolls ignore reduced motion | `glide()`, §3 |
| 5 | MEDIUM | accessibility | six rules, §2 | hover motion with no hover gate sticks after a tap | §2 |
| 6 | MEDIUM | timing | `script.js:396–453`, `door.js:479` | five lerps per frame, so twice as fast at 120Hz | `settle()`, `damp()`, §4 |
| 7 | LOW | performance | `tokens.css:260`, `styles.css:337` | the lamp animates `left`; `.tlink` animates `gap` | §5, §8 |
| 8 | LOW | timing | `styles.css:328`, `:1097` | hover at .3s; a disclosure leaves as slowly as it arrives | §8 |
| 9 | LOW | accessibility | — | no `prefers-reduced-transparency` | §8 |
| 10 | LOW | tokens | `styles.css`, `script.js` | four dead motion hooks | deleted, §9 |

**Verdict, under review-animations' bar:** at `89470c0`, *block* (no press
feedback anywhere, ungated hover motion, reduced motion not honoured by two
scripted scrolls). After this change, *approve*: no feel-breaking
regressions, nothing animating that should not, every duration and curve
inside its budget or documented below, interruptible where it needs to be,
and reduced motion respected in CSS and script alike.

**Apple's principles, applied** (apple-design):

| Principle | Here |
| --- | --- |
| Response (§1) | the press, on pointer-down, on every control (§1) |
| Direct manipulation, momentum, rubber-banding (§2, §5, §6, §9) | nothing on the site is dragged; Lenis owns scroll inertia. Not applicable, and no gesture was invented to apply it to |
| Interruptibility (§3) | every UI state change is a CSS transition, which retargets from where it is; the one-shot entrances are keyframes because they happen once |
| Springs (§4) | considered for the four doors and rejected: a click carries no velocity |
| Spatial consistency (§7) | the doors' descriptions enter and leave along the same path; the lamp travels between the tabs it marks |
| Frame-level smoothness (§11) | per-second smoothing (§4); the lamp on transform (§5) |
| Materials (§12) | the translucent header and form panels go solid under reduced transparency (§8) |
| Reduced motion, transparency, contrast (§14) | press dims instead of scaling; scripted scrolls ask; solid ground. `prefers-contrast` was already handled on the directory |
| Typography (§15) | tracking was already size-specific (-.032em display, .22em eyebrows, 0 body) and Fraunces' optical size axis is loaded; balanced display lines and pretty prose added |
| Feedback, wayfinding (§16) | the form's answer arrives rather than appears (§10); the lamp, the current tab and the rail already answer "where am I" |

## The rules

**Every curve lives in `tokens.css`.** Three of them, and neither stylesheet
may type its own `cubic-bezier`:

| Token | Curve | For |
|---|---|---|
| `--ease` | `cubic-bezier(.22,.61,.36,1)` | a change of colour or ground under a pointer; nothing is going anywhere |
| `--ease-out` | `cubic-bezier(.16,1,.3,1)` | anything arriving, and anything answering a press: most of the movement happens in the first frames, while the eye is already there |
| `--ease-in-out` | `cubic-bezier(.77,0,.175,1)` | something already on screen travelling to a new place (the nav lamp) |

**Two timings are tokens too:** `--t-press` (.16s) for answering a press,
`--t-hover` (.2s) for a hover's invitation. A press is the quicker of the
two because it is a reply, not an offer. Longer durations on this site are
deliberate and each has a written reason next to it; the table at the end
lists them.

**Every control a finger presses gives the moment it is pressed.** It
gives on pointer-down rather than on release, and springs back when let go:
`scale:var(--press)` (.97) for buttons and pills, `var(--press-wide)` (.985)
for cards, whose edges travel further for the same scale. The `:active`
lists live in one place, `tokens.css` device 4. Each control's own
transition list carries `scale var(--t-press) var(--ease-out)`, because a
transition is one list per element and a shared one would erase theirs.
Leaf controls only: `:active` climbs to every ancestor, so a resource card
that holds a Call button would sink under every press inside it.

**Hover may recolour anything. Hover may move something only where a pointer
can hover:** `@media (hover:hover) and (pointer:fine)`. A tap on a touch
screen fires `:hover` and leaves it on until the next tap lands somewhere
else, so ungated hover motion sticks after the tap.

**Smoothing is per second, not per frame.** `settle()` in `script.js` and
`damp()` in `assets/door.js` turn a constant tuned at 60Hz into the same curve
in time at any frame rate, so a 120Hz screen gets the motion that was tuned.

**Reduced motion keeps the answer and drops the movement.** Every transition
goes to near-zero and every animation stops (unchanged), a press dims instead
of scaling, and a smooth scroll requested in script asks first.

**Reduced transparency gets solid ground.** The stuck header and the form
panels drop their blur and become opaque.

## What changed

### 1. The press: the site answers the hand

*apple-design §1 (Response), emil-design-eng "Buttons must feel responsive".*

There was not one `:active` rule on the site. A runtime inventory of eight
pages at two widths found zero. On a slow phone, a tap on a phone number
looked exactly like a tap that missed for however long the dialer took to
open. Now sixteen kinds of control give under the press (`tokens.css`
device 4), including the Call button, the emergency numbers, the language
pills, the filter choices, the event cards and every button on the narrative
pages. Two more answer in their own way: the four doors' `+` and the filter
segments, below.

- **The `+` on the four doors is what gives** (`.ways__row:active
  .ways__sign`, to .8), not the row. A row is the width of the column, and a
  whole row sinking under a click reads as the section moving.
- **A filter segment darkens instead of shrinking** (`.facet__btn:active`).
  A segment of a bar that shrinks comes away from the bar's own edges.
- **iOS needs a touch listener** before WebKit shows `:active` at all, so
  `script.js` and `help.js` each register an empty passive `touchstart`.
  Lenis registered one, but not under reduced motion, which is exactly when
  the press is the only feedback left. (Verified in Chrome; WebKit's rule
  is documented behaviour and was not tested on a device in this pass.)
- `-webkit-tap-highlight-color:transparent` on the same controls, because
  the press replaces the grey flash instead of competing with it.

### 2. Hover motion only where hovering exists

Ungated before, gated now: the shared arrow's lean (`tokens.css`, was :137),
its RTL mirror (`help.css`, was :1269), the back arrow on the breadcrumb (was
`help.css:707`), the emergency numbers' lift (was `help.css:317`), the
event cards' lift (was `help.css:1317`) and the filter underline (was
`help.css:435`). The worst of these was the emergency numbers. On a phone
the number somebody had just called stayed lifted above the other three.

Found on the way: under reduced motion a mirrored arrow kept leaning on
Arabic and Urdu pages. The shared reduced-motion rule loses to the RTL rule
on specificity, and would have un-mirrored the arrow if it hadn't. It now
stays mirrored and still.

### 3. Scripted scrolling asks first

`help.js` asked for `behavior: "smooth"` outright in two places, the event
carousel's arrows (was :167) and the calendar's jump to a day (was :317). An
explicit smooth scroll overrides the stylesheet, so the CSS that turns smooth
scrolling off under reduced motion never reached either. Both go through
`glide()` now, which asks at the moment of scrolling.

### 4. Smoothing per second, not per frame

*apple-design §11 (frame-level smoothness).*

The reading veil (`0.09`), the thread's fade (`0.07`) and shape (`0.055`),
the closing unwind (`0.08`) and the door's pointer parallax (`0.055`) were
all applied once per frame. Tuned at 60Hz, they ran at twice that speed on a
120Hz display, which is most current Macs and iPhones, and at half speed on a
busy one. `settle(k)` is `1 - (1 - k)^frames`, where `frames` is measured
from the frame clock and capped at six. It is identical at 60Hz by
construction, and two 120Hz frames land exactly where one 60Hz frame does.

### 5. The nav lamp travels on transform

It animated `left` and `width` (`tokens.css`, was :260). It now moves on a
`translate` written by `script.js`, which the compositor moves at sub-pixel
precision without laying anything out, and eases in and out because it is
something already on screen moving to a new place. Width still transitions:
the tabs are different widths, and scaling the lamp would stretch its bar
and glow.

### 6. The hero's ground stopped cutting the door

*Found while reviewing the first frame, not by any rule.*

The scrim behind the desktop headline (`styles.css`, was :700) was a radial
gradient 150% of the headline's height, transparent at 78%. So it never
reached transparent inside its own box, and stopped in a straight line about
.45 dark at the headline's top and bottom. That line ran across the door's
slit of light, the brightest thing on the page, and cut it into three pieces
with a hard step at each edge. The ground is now a pseudo-element that
extends past the type with a `closest-side` gradient, so it fades to nothing
on its own edge, outside the headline. The stops are the same; the contrast
under the type is within measurement noise of before (table below).

### 7. The far side of the door stopped shining through the last line

*Found by measuring, not by looking.*

On a desktop the closing beat is `door.js`'s "out" mode, which turns off
the slit's glow, the shaft and the floor pool, because from the lit side
nothing is being thrown into the room you stand in. The CSS poster, which is
the door on every phone, kept all three at full strength, and the closing
headline is set straight across them. Measured glyph by glyph at 390px, 7%
of the line's roman pixels and 10% of its italic measured under the 3:1 that
large type needs, the worst at 1.46:1. In the closing state the slit's glow
is now .2 and the glare and pool .44 (`styles.css`, `:is(html.closing)`).
The slit still reads as a door left ajar, and nothing in the line measures
under 3:1 from 320px up.

### 8. Smaller corrections

| Before | After | Why |
| --- | --- | --- |
| `.btn` `transition: … .3s` (was `styles.css:328`) | colour in `--t-hover`, the press in `--t-press` | hover colour around 200ms; a press is 100–160ms |
| `.btn .arr` and `.btn:hover .arr` restated the shared arrow, ungated | deleted; the shared device does it | one arrow, one rule, one gate |
| `.tlink:hover{ gap:13px }` (was :337) | deleted | it moved the arrow a second time, on top of the shared lean, by re-laying out the link every frame |
| `.ways__blurb` left as slowly as it arrived (.42s + 60ms) | leaves in `--t-press`, arrives as before | exit faster than enter; on a swap the old words are gone before the new ones start, instead of two paragraphs half-visible in one place |
| `.arr` `transition: transform .3s var(--ease)` | `var(--t-hover) var(--ease-out)` | a movement answering a hover; ease-out, at hover speed |
| no `prefers-reduced-transparency` | the stuck header (`--head-solid`) and form panels go opaque | apple-design §14 |
| display headings wrap however they fall | `text-wrap: balance` on display lines, `pretty` on prose | a two-line phrase never leaves one word under a full line; degrades to ordinary wrapping. Not on `.ways__blurb`, whose three-line reserve `pretty` could break |

### 9. Deleted, because nothing rendered it

`.scrollcue` and `@keyframes cue` (a scroll indicator no page has), the
`.doors` / `.door` card grid with its hover lift (the journey's binding rule
is no card grids, and `.ways` replaced it), the `--d` stagger delay on
`.focus-in` (no element ever set `--d`), and the `[data-count]` count-up in
`script.js` (no page has the attribute). check.py keeps them deleted.

### 10. Three additions, each at a moment that happens once

*find-animation-opportunities: the delight budget lives at the rare tier.*

| # | Location | Today | Purpose | Frequency | Motion |
| --- | --- | --- | --- | --- | --- |
| 1 | every pressable control | nothing on press | Feedback | tens a visit | `scale` .97 / .985 on `:active`, `--t-press` `--ease-out`; dims under reduced motion |
| 2 | `.hero__ui` children, **desktop only** | the whole frame appears at once | Orchestration: claim, then answer, then the way out | once a visit | `hero-in`: opacity, 14px rise, 8px blur to focus, .9s `--ease-out`, staggered 0 / 80 / 260 / 440 / 620ms |
| 3 | `.form__ok`, `.form__err` | the panel jumps to a different, shorter panel | Preventing a jarring change, at the one moment somebody has done something | once | `arrive`: opacity and 6px rise, .32s `--ease-out` |

The entrance uses the page's own blur-to-focus, shorter, so the page has one
way of arriving rather than two. It is **desktop only on purpose.** PERF.md's
mobile score of 84 is measured at phone width, where Speed Index would pay
for every frame of it, and the person on the phone is the likelier of the two
to have a bill in their hand. Every control is live from the first frame,
and reduced motion removes it.

**Considered and rejected:**

- **Animating directory results as filters narrow them.** Rejected on
  frequency and function: tens of times a visit, on the data somebody is
  trying to read and act on.
- **Opening the resource card's "More about this" with a height
  transition.** Rejected on function and risk: `::details-content` has
  broken this directory's layout once already, and a frightened reader
  gains nothing from the drawer gliding.
- **Staggering the eyebrow, phrase and lede inside each scene's reveal.**
  Rejected on cost: the reveal blurs one block, and a stagger means three
  blurred layers per block on the device least able to afford them.
- **A spring on the four doors.** Rejected: there is no gesture to carry
  velocity, and a click is not a throw. The rows are interruptible CSS
  transitions already.
- **A shake on a failed send.** Rejected on register: this is serious work
  with vulnerable adults, and the brand is warm and grounded, not playful.

## Worst-case data: the event cards

*break-ui.* The event cards are the one place on the site where text nobody
here wrote reaches the page unedited: titles, venues and descriptions come
straight from NYC Parks, NYLAG and the Food Bank. So they got a worst-case
pass. A fixture of eight plausible events went through the real renderer
(`events.py`, then `build_help.py`) in a scratch copy of the site: the data
changed, the component did not. It was rendered against the live data at
1440, 390 and 320px. The fixture had a 140-character title, a URL as a
title, a one-word title, an all-caps title, emoji and Chinese, markup and
quotes, a 30-letter German compound, a three-clause venue, an all-day event
and a 2,000-character description.

| # | Severity | Field | Worst case | What happened | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | Ugly | `.ev__meta` location | real data, at 320px: "Chinatown YMCA Beacon, Manhattan" | the pin sat on a line by itself and the place wrapped below it, because pin and place were separate items in a wrapping row | `events.py` groups them in `.ev__at`, the way the featured card already did; the pin aligns to the first line (`1lh`) |
| 2 | Ugly | `.fev__h` title | "Bronx River Alliance Presents: Free Family-Friendly Guided Canoe Tour and Ecology Walk Along the Bronx River Greenway (Registration Required)" | every card in the row stretched to the tallest: 551px against 415, with "Yoga" beside it mostly blank | the title link clamps at three lines, four on the lead card. Row back to 460px; the real data's 415 is untouched |
| 3 | Fragile | title | — | no limit anywhere upstream; the feed decides | the clamp is the limit; the full title is the link's text (whole accessible name) and is printed in full on events.html |
| 4 | Ugly, introduced and fixed | focus ring | a clamped title, tabbed to | clamping the heading cropped the link's ring, and padding it clear showed the top of the hidden line under the ellipsis | the clamp sits on the link: an element's overflow never clips its own outline |
| 5 | Ugly | `.fev__m` place, two lines | the three-clause venue | the pin centred between the two lines | top-aligned, like #1 |

**Held up:** markup in a title renders as text (`esc()`), a URL as a title
breaks inside the card rather than out of it, an empty venue says "See the
listing" instead of leaving a bare pin, an all-day event shows its date
alone, a long description is cut at a word and says so with an ellipsis,
emoji and CJK render whole, and no page scrolls sideways at any width.

**Decided, not fixed:** the lead card on a phone grows to fit a long
venue (404px at 390 for the worst case, 234 for the live data). A place
somebody has to find is not something to truncate.

`check_a_feed_cannot_break_the_cards` pushes a hostile event through the
renderer on every run, and two mutations prove it notices (clamp removed,
pin ungrouped).

## What it cost

About 460 bytes gzipped across every stylesheet and script, most of it the
press lists in `tokens.css`. The narrative page's own stylesheet and script
came out slightly smaller after the dead code went.

## Settled, and left alone

These looked like findings under the standards and are deliberate,
documented decisions. They were not changed.

- `.ways__row` animates `padding` (a layout property) on hover. That is the
  whole affordance: the rows below give way (`styles.css`, "THE DOORS").
- `.ways__body` opens over .55s, 0fr to 1fr. The opening and closing rows
  share one curve so their heights always sum to the same total, and the
  section never wobbles on a swap.
- The stuck header fades in over .12s and out over .4s. Appearing is the safe
  direction to hurry, over the clay emergency panel.
- `.focus-in` reveals once over 1.1s and never un-reveals: marketing
  register, and erasing text at rest was a measured defect.
- The doorstage handover timings (`.25s linear`, the poster held .55s then
  dropped) exist to avoid double exposure between canvas and poster.
- Lenis jumps take 1.25s: a long page, and the journey is the point.

## How it is checked

**`check.py`, nine guards**, each with its reasoning in its docstring:
`check_motion_speaks_one_language`, `check_every_press_is_answered`,
`check_hover_motion_needs_a_hover`, `check_scripted_scrolling_asks_first`,
`check_smoothing_is_per_second`, `check_the_hero_ground_has_no_edge`,
`check_the_far_side_of_the_door_is_dim`,
`check_the_entrance_stays_off_the_phone`, and
`check_a_feed_cannot_break_the_cards` (below). They read CSS through a small
rule walker (`_css_rules`) that knows which `@media` block a rule sits in,
which the flat regex the older guards use cannot tell.

**`mutate.py`, sixteen new mutations**, one per way the above could be
undone without anything looking wrong on the machine it was done on. All
sixteen are caught. Run them alone:

```python
import mutate
mutate.MUTATIONS = mutate.MUTATIONS[-16:]
mutate.main()
```

**`check_runtime.js`, a real Chrome**, because a stylesheet can say
`scale:var(--press)` under `:active` and never once be pressed:

- pointer-down on the hero's buttons, the Call button, the emergency numbers,
  an event card, a pill and a language link really scales them, and release
  brings them back
- the resource card around a pressed Call button does not sink with it
- a touch profile reports no fine hovering pointer, and an emergency number
  does not lift under a hover it cannot have
- the hero's five entrances run on a desk and none run on a phone
- the nav lamp is positioned by transform, not `left`
- the closing slit is dimmed when the closing beat owns the stage
- under reduced motion the carousel arrow jumps; without it, it glides
- **contrast against the ground that is actually there**: the hero and the
  closing line rendered three times (whole, italic transparent, all
  transparent), diffed to find each glyph's pixels, and every one compared
  against the composited pixel behind it. A contrast check that reads a
  background colour finds nothing to read on a WebGL door

```
node check_runtime.js http://localhost:8753 -v
```

### Measured

Glyph-masked contrast, percentage of glyph pixels under 3:1 (the large-type
threshold; both headlines are large type), with the worst single pixel:

| | before | after |
|---|---|---|
| hero, 1440×900, italic | 0.8%, 2.07 | 0.8%, 1.88 (the gold "N" on the slit's white-hot core) |
| hero, 390×844, italic | 0%, 4.24 | 0%, 4.00 |
| hero, 320×640, italic | — | 0%, 3.91 |
| closing line, 768×1024 | roman 2.8%, italic 3.1%, worst 2.23 | 0%, worst 4.83 |
| closing line, 390×844 | roman 7.4%, italic 10.2%, worst 1.46 | 0%, worst 3.49 |
| closing line, 375×667 | — | 0%, worst 3.04 |
| closing line, 320×640 | italic 2.3%, worst 1.08 | 0%, worst 3.10 |

The desktop hero's 0.8% is part of one letter crossing the slit's core. A
scrim dark enough to clear it (tried at .66) moved the worst pixel only to
2.47 while darkening the door, so it stays, and `check_runtime.js` allows
exactly that much.

## Durations that are long on purpose

| What | Duration | Why it is allowed |
|---|---|---|
| `.focus-in` reveal | 1.1s | marketing reveal, once per block, `--ease-out` front-loads it |
| `hero-in` | .9s, staggered to 1.52s | once a visit, desktop only, never blocks a control |
| `.ways__body` | .55s | the swap invariant above |
| `.ways__row` padding | .4s | the affordance itself |
| `.nav-lamp` | .4s | on-screen travel between tabs, a few times a visit |
| `.sitehead` fade out | .4s | slow out, quick in, over the emergency panel |
| `#doorCanvas` fade | .5s | the canvas arriving over a finished poster |
| `.hero__cue` | 2.4s, looping | a 1px line; stops under reduced motion |

Everything a reader triggers directly stays at or under .25s.
