# Design System

A scroll-driven journey through a painterly landscape, with warm green + gold palette. Every surface is designed for clarity first: busy adults and vulnerable community members must understand the "what we are / what we are not" statement in under 10 seconds.

## The shape of the page

The homepage is one continuous journey. It opens on **the door** (real-time WebGL), carries you through it into the painted world, and closes on the same door seen from the far side. In between, fourteen beats cycle between four registers so the page never settles into one rhythm: the phrase-per-screen scenes, a denser **hold scene** (three times, where the phrase needs to keep its place while substance moves past it), a **pinned scene** (once) where the journey parks and hands the screen to something that is not prose, and one **section you operate** rather than scroll.

    door → real, free, invisible → [pin] the reel → what we are
      → [doors] where the thread leads → the honesty statement → [hold] the line
      → the other half
      → FOR STUDENTS: the corps → students form
      → FOR PARTNERS: [hold] who we reach → [hold] what we ask for → partner form
      → the door, from the other side

The page addresses two audiences and it now says so. Everything written to
volunteers is one labelled block, everything written to organisations is
another, and the partner block sits **last**. A student has to be convinced and
a partner arrives already knowing what they want, so a student never has to
scroll past a pitch aimed at somebody else to reach the thing they came for.
Each block opens with an eyebrow naming its reader — `For students`,
`For partners`.

This is the second deliberate exception to "no section labels" below. It is
here because the alternative is worse: two audiences interleaved with nothing
telling either of them which paragraphs are theirs.

**Four places encode that order and they are edited by hand** — the primary nav,
the footer's journey column, `script.js`'s `navSections` tracker, and the page
itself. Nothing looks broken when one of them drifts, so `check.py` asserts the
nav walks the page in ascending document order, that `#students` precedes
`#partners`, that both blocks keep their labels, and that `#partners` anchors
the *first* scene of its block rather than the second — otherwise the nav lands
one scene past the label meant to introduce it.

### Pinned scenes

Each is a section taller than the viewport holding a sticky child that fills it;
scrolling the surplus height scrubs `--t` from 0 to 1. That one variable drives
everything, and `script.js` sets nothing else:

| Pin | What `--t` does | The point it makes |
|---|---|---|
| **The reel** (`#bills`) | Rolls four lines of officialese, one at a time, into what they actually mean | The letter is written in a language built for somebody else, and its last line is a door |

#### The reel (`#bills`)

**Reference: the odometer on [leocussen.edu.au](https://www.leocussen.edu.au),
an Awwwards nominee** — the Leo Cussen Centre for Law, an institution whose job
is making dense professional material navigable for people who need it, with
accessibility built in from the start. Its statistics module rolls each digit on
a vertical strip that settles on a value. Two details there are what make it read
as engineering rather than as decoration, and both are carried over — one
literally, one not.

The section's claim is that a denial letter is written in a language built for
somebody else. So the artwork is four lines lifted off a real notice, each on a
reel that rolls through the officialese and lands on what it actually means:

    Determination           ADVERSE DETERMINATION      → They said no.
    Patient responsibility  PATIENT RESPONSIBILITY     → This is yours to pay.
    Reason code             REASON CODE N130           → No reason you can read.
    Appeal rights           APPEAL RIGHTS · SEE REVERSE → You are allowed to argue.

The two voices are set to look nothing alike — officialese small, tracked and
uppercase in Inter; what it means in Fraunces, the face the rest of the page
speaks in. The last row is the turn and the only gold on the artwork: on a real
denial it is the one line that points anywhere useful, and it is the smallest
type on the page. It hands straight to `#work` ("There is a solution for this"), and
to the counselors there who "argue with insurers for a living".

This replaced a static plate of a denial notice — an accurate picture of a bill,
which is one order of thought short of the point. A picture of that language
states the problem; a reel that rolls the language into what it means *performs*
it, and lands the section somewhere useful.

**What was taken from the reference, and what was not.**

- **The window cannot be resized by its contents.** Theirs buys this with a
  `visibility:hidden` sizer copy behind the window, because their reel is inline
  and its width follows its content. This one buys it structurally — block
  window in a fixed grid column, strip absolutely positioned — which is the same
  guarantee with no hidden markup. Measured both ways before dropping the sizer:
  520px either way. Copying it regardless would have been dead weight that
  looked like craft.
- **Feathered while moving, crisp when still.** Theirs fades a gradient overlay
  in and out at the window edges. That cannot be copied literally here: an
  overlay painted in a flat colour smears against the landscape. This one
  feathers the **mask** instead, which fades content to transparent whatever is
  behind it — same intent, correct mechanism for this background.

**One basis for `--line`, and never `em`.** `--line` is both the height of the
window and the step size of the roll. A custom property is substituted as tokens
and re-resolved per element, so `1.42em` means one thing on the window and a
smaller thing on the `.62em` officialese spans; the steps and the window stop
agreeing and the roll walks off the end of the strip. It shipped that way until
a render showed two phrases in one window. It is now a `clamp()` in `rem`/`vw`,
and every strip line is a flex box of exactly `--line`, so type size and step
size are independent. `check.py` rejects any `em` in it.

**Released states carry the finished frame.** The pin only exists above 900px
and outside reduced motion. Everywhere else `--t` never moves, so both released
states pin `--k:1` and every reel renders landed on its plain meaning — a phone
showing four lines of untranslated officialese would be the section arguing
against itself. Missed on the narrow breakpoint once; guarded now.

#### Line-mask reveals

The four narration lines used to arrive blurred, which reads as soft focus
rather than composition. They now arrive the way editorial sites do it: each
line clipped to its own box and travelling up into place on a stagger, so the
sentence assembles. Lines are **set by hand** rather than split at runtime — the
copy is fixed, so the ragging is a typographic decision instead of whatever the
box happens to do, and it costs no script and no library.

Three details do the work, and they are the three normally got wrong:

1. **`overflow:clip`, not `hidden`.** `hidden` creates a scroll container, so a
   focused element inside can be scrolled by the browser and the mask silently
   gains an offset. `clip` cannot scroll at all.
2. **Descenders.** Clipping at the content edge shears the tails off g, y and p.
   Bottom padding gives them room, pulled straight back out with an equal
   negative margin so the line box still measures the same.
3. **The parked position clears the padding too.** Travelling `100%` leaves the
   glyph tops showing through that descender allowance; the hidden state is
   `100%` **plus** the allowance, which is exactly the bottom clip edge.

### The honesty statement — short on screen, full one tap away

The statement is the one piece of copy on the site that exists to stop somebody
mistaking a student for a professional. It ran seventy-five words set large in
display italic, which took most of a screen and, being that long, was the part
people scrolled past.

It is now two pieces. **What stays on screen is the short version** — *"We are
trained student volunteers — not doctors, not lawyers, not benefits counselors.
We walk you to the free professionals who are, and we never charge for
anything."* Twenty-eight words carrying the three things that actually protect
somebody: who we are, what we are not, and that nobody pays us. This is a
straight improvement against the brief at the top of this document, which asks
that a vulnerable reader take the statement in under ten seconds.

**The full wording sits behind a disclosure**, verbatim and never reworded, with
the "printed on everything we hand out" attribution under it. `check.py` still
counts the verbatim fragments twice across `index.html` — the disclosure and the
page footer — so nothing about that contract changed.

Two rules this is built to, and `check.py` enforces both:

- **The visible line has to keep carrying the essentials.** Collapsing the full
  text is only safe while a shorter one stays on screen, so the check asserts
  the visible sentence still contains *trained student volunteers*, *not
  doctors*, and *never charge*. Trim it further and the build fails.
- **It is a native `<details>`, not the disclosure JS the doors use.** Everywhere
  else on the site a script failure costs a nicety. Here it would hide a safety
  statement, so the mechanism has to be one that opens with no script at all.
  This is the reason to prefer native markup over the fancier pattern that is
  already in the codebase.

### The line — a hold scene of beats

Four shapes, each failing differently, and the last change removed the section's
CSS altogether.

A **tick-and-cross checklist** was the most generic possible form. A **numbered
register** in two halves was handsomer but still a taxonomy — ten items the
reader must sort into buckets before any of it means anything, in a section that
follows a scene which has already stated the boundary in prose. **Four indented
pairs** with a gold dash fixed the content but still handed the reader a shape
to decode. What it is now is what the reach and partners scenes already were:
`scene--hold-r` holding a stream of **`.beat`** — a bolded run-in lead and a
short description, no marks of any kind.

    Listens, in your language.  You describe what you are holding, in your own
    words. A volunteer never reads it back to you or tells you what it means.

    Names the office that handles it.  They can tell you who takes this kind of
    problem. They can never tell you whether you qualify for it.

    Dials the number and stays while it rings.  You do the talking. A volunteer
    sits with you through the wait and never speaks in your place.

    Leaves with nothing.  No photo of your paperwork, no copy of your bill, and
    no name written down beside any of it.

    And none of it starts until it is checked.  No volunteer speaks to anyone
    about a bill until someone with real health-insurance-law knowledge has
    been over our materials.

**The boundary lives in the prose.** Nothing is drawn and nothing is indented:
each beat states its own limit — *never reads it back to you*, *can never tell
you whether you qualify* — so the line is made five times over rather than drawn
once between two columns. `check.py` enforces that every beat carries one,
because with no rule and no columns the prose is the only place the line exists.

**Why it is a hold and not a pin.** It was a pinned scene scrubbing `--t`, which
meant the phrase scrolled away from the very statements it was introducing.
Measured against the partners ask it now behaves identically — phrase parks at
477px and holds through a 609px window, versus that section's 566px. This is
also what keeps the page's own thread out of the type: `spiralTarget()` matched
`scene--pin` first and ran the thread down the centre, whereas a hold scene's
thread goes in the gutter between the two columns. The explicit `scene--lane`
override this once needed is gone.

**There is no lane CSS.** The indent, the gold dash, the staged crossing, the
`--t` thresholds and their reduced-motion resets all went with this change. The
section is `.beat` and nothing else, which is why it needs no responsive case,
no released state and no guard against its own motion. `check.py` rejects any
`.lane__` selector reappearing.

### The doors (`#work`) — the one section you operate

Everywhere else the scroll is the only input. Here it is not: four hairline rows
name the four places a problem actually goes, centred and alone on the screen,
each opening onto a sentence about what is behind that door.

This replaced a scroll-drawn fan diagram — four labels on stalks, wires tweened
from `--t`. It went for two reasons. A label on a stalk cannot say what is behind
it, so the section named four things and explained none of them; and re-tweening
four `stroke-dashoffset`s every frame meant any scroll stutter was visible as the
drawing itself stuttering. Operating a row costs one attribute change.

**Two states, two triggers, and they do not overlap.** Hover only makes the
header breathe about 8px taller and turn gold — an invitation, nothing more.
The description opens on a **click** and nothing else, and **nothing is open
until asked**. Prose revealed on hover arrives while the pointer is only passing
through and vanishes the moment you move toward it, so it can never actually be
read; that is a hover state pretending to be a disclosure.

**What stays still.** Because the section's height is its content plus 100vh of
padding, the block sits at its `padding-top` with no free space to centre in — so
opening a row pushes only what is below it and never lifts the row you clicked.
Switching between rows does not move anything at all, and that takes two things
together:

- **Every blurb reserves the same three lines** (`min-height:calc(1.62em * 3 + …)`
  on `.ways__blurb`) whether its sentence fills them or not.
- **The measure is capped at `44ch`**, narrower than the column ever gets before
  the layout stacks, so the cap always binds and the line count stops depending
  on the viewport. Without it one blurb takes a fourth line around 1150px while
  the others keep three — a band nobody thinks to test.

Given equal heights the closing row shrinks on exactly the curve the opening one
grows on, so `h·f + h·(1−f) = h` at every frame of the swap. Measured: 577px
closed, 681px with any of the four open.

**Degradation.** The markup ships with **no `aria-expanded` and the panels open**,
because a disclosure whose only trigger is a click is content nobody can reach if
the click handler never lands. `script.js` takes the list over in one breath —
add `.ways--js`, which closes the panels, and write the attribute that says so —
behind a `.ways--boot` cut so the reader never watches four descriptions animate
shut on load. Clicking the open row closes it again. Below 900px the heading
un-constrains its measure and the three-line reserve is released, since tap is
the only pointer and nothing sits beside the list to be pushed around. There is
no reduced-motion case: nothing here needs motion to be read, so the global
`transition-duration` override just makes the row open instantly.

`check.py` guards all of it — the disclosure wiring, that hover opens nothing,
that the no-JS fallback is intact, and the 156-character blurb budget that keeps
three lines true.

**Below 900px and under `prefers-reduced-motion` the pin releases**: height goes
`auto`, the sticky child goes static, and each mechanism renders its finished
state — every reel already landed on its plain meaning, every mask already open.
Nothing depends on scroll to become readable.

Rules the page is built to: no card grids, no numbered step lists, no section labels, no visible boundary between beats. Each beat hands off to the next. The doors are the one deliberate exception — a hairline list is a boundary, and it is there because four named things need four rules between them to be four things rather than a paragraph. It stays a list of names, never a grid of cards, and the sequence beside it stays unnumbered.

## The door (`assets/door.js`)

A wall in darkness with a door ajar, warm light knifing through the gap on the latch side, and the sunlit valley (`land1.webp`, the same asset the journey uses) beyond it. Scroll drives `t` from 0 to 1: the door swings wider and the camera dollies from `z 9.6` to `z 0.72`.

**Every parked position has to look intentional**, because scroll can stop anywhere. Three rules make that true, and `check.py` guards all three:

- **The camera stops in front of the wall.** It used to fly through to `z -1.4`, which took the eye through the 54 light-shaft quads and the wall itself; edge-on quads read as hard diagonal bands across the viewport. At `z 0.72` the opening is wider than the frame, so you get the same sensation of passing through with nothing to collide with.
- **The shaft's near end is proportional to the camera distance** (`camZ * 0.55`), never a fixed offset. An additive quad a few centimetres from the lens covers the whole viewport, and 54 of them stacked is a flat grey wash.
- **The beam and the slit bloom retire.** Both peak while the door is opening and are gone by `t ≈ 0.82`. Letting them keep growing turns the opening into an additive white slab, because past halfway the opening *is* the light and no longer needs blooming. The valley's brightness is held back to match, then brought to full once the beam is gone.

The handover happens only between `t 0.95` and `1`, the window where the doorway is already wider than the viewport, so the canvas and the painted backdrop are showing the same thing. The `beyond` plane converges on the crop the CSS background will use, and a modest warm swell (`.threshold`, peak 0.45) softens the seam. If the render ever throws, the loop stops and the CSS poster takes over rather than leaving a frozen canvas.

| Piece | How it is made |
|---|---|
| Wall + jamb | `ExtrudeGeometry` from a `Shape` with a door-shaped hole, so the opening has real depth |
| Casing | Three boxes proud of the wall on the approach side only; without it the door reads as a slot in a void |
| Panel | Hinged group, swings toward whichever side the camera is on |
| Light shaft | ~54 layered additive quads with an analytic soft-box mask that widens with distance, plus value-noise dust |
| Floor pool | Additive plane using the same gap maths |
| Motes | ~900 additive points, alpha gated by the same mask |
| Lighting | One warm `PointLight` **behind** the wall (rakes the jamb, leaves the near face dark) plus a short-range spill light so the wall reads as a surface. **No shadow maps** — the geometry does the occlusion |

The gap is computed the way a hinged door actually leaves one: half-width `0.95·(1−cos θ)`, centred at `0.95·cos θ`, so it opens from the latch side.

**Degradation, in order.** `prefers-reduced-motion` renders one static frame with the door already open and turns the pass-through into a cut. Phones cap pixel ratio at 1.6, drop to 26 shaft layers and 260 motes, and widen the FOV to 52° in portrait. No WebGL at all leaves the **CSS poster** (`.doorstage__poster`) in place — a wall, casing, panel in perspective, slit and soft glare built entirely from gradients. It is a finished picture, not a grey box, and it costs no extra bytes.

`window.__waypointDoor` exposes `set(t, mode)`, `live(on)`, `still()` and a read-only `probe()`; `window.__waypointTick` recomputes everything scroll-linked, including the thread. These exist because headless tabs report `hidden`, so `requestAnimationFrame` never runs and the only way to verify a scroll-driven state is to drive it: freeze `set`, call `still()`, then read `probe()`. Diagnosing by eye alone led to three wrong hypotheses before `probe()` gave the actual uniform values.

## Color

### Semantic Roles

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Background (primary) | `--green-deep` | `#13231A` | Body background, page foundation |
| Surface (secondary) | `--green` | `#1E3528` | Panels, containers, UI surfaces |
| Surface (tertiary) | `--green-2` | `#2C4A38` | Hover states, elevated surfaces |
| Accent (primary) | `--gold` | `#E7C57E` | Links, highlights, interactive affordances, brand voice |
| Accent (secondary) | `--sage` | `#A6C39A` | Subtle supporting accent |
| Background (light) | `--mint` | `#FBFFF4` | Near-white, used rarely |
| Surface (light) | `--mint-2` | `#E7EFE3` | Light backgrounds |
| Text (primary) | `--cream` | `#FCFEF7` | Body text, primary ink |
| Text (soft) | `--ink-soft` | `rgba(252,254,247,.78)` | Secondary text, ~78% opacity |
| Text (faint) | `--ink-faint` | `rgba(252,254,247,.55)` | Labels, eyebrows, tertiary text ~55% opacity |

### Palette Strategy

**Committed**: One saturated color (green) as the dominant surface, gold as the accent that carries voice. This strategy works for Waypoint because the deep green is both trustworthy (institutional, grounded) and warm (not clinical). Gold softens it and signals connection + hope. No beige safety blanket; the green is the brand.

### Contrast & Accessibility

- Body text (`--cream` on `--green-deep`): 13.5:1 ✓
- Large text (`--ink-soft` on `--green`): 9.2:1 ✓
- Placeholder text: Uses `--ink-faint` (~55% cream on dark green). Cross-check at focus; should hit 7:1 minimum. Currently ~6.8:1; may need bump on very small text.
- All interactive states (links, buttons) hit ≥7:1 with gold on green.

## Typography

### Typeface Selection

| Role | Family | Stack | Rationale |
|------|--------|-------|-----------|
| Display (h1–h3) | Fraunces | `"Fraunces", Georgia, serif` | Museum caption energy: institutional but warm, not modern. Supports italic for emphasis (gold italics mark the voice). Loaded at opsz 9..144, wght 400/500. |
| Body (p, labels, UI) | Inter | `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | Neutral, legible, accessible. No personality; lets Fraunces carry the brand. |

### Scale

Modular scale with fluid `clamp()` for responsive sizing. Minimum ratio: 1.25× between steps.

| Element | Size (clamp) | Weight | Line-height |
|---------|--------------|--------|-------------|
| h1 (hero) | `clamp(2.8rem, 7vw, 6.4rem)` | 400 | 1.02 |
| h2 (scene phrase) | `clamp(2.6rem, 6vw, 5.4rem)` | 400 | 1.02 |
| h3 (panel heading) | `clamp(1.7rem, 3.4vw, 2.5rem)` | 400 | 1.0 |
| Lede (scene description) | `clamp(1.08rem, 1.6vw, 1.4rem)` | 400 | 1.55 |
| Body (default) | `17px` | 400 | 1.6 |
| Small / label | `12–14px` | 500–600 | 1.0 |

All display text gets `text-shadow: 0 2px 40px rgba(12,22,16,.55)` to ensure legibility over the landscape.

### Emphasis

- **Italics** (`em`): Fraunces italic, color `--gold`. Marks the brand voice and key insights.
- **Strong** (`b`, `strong`): weight 600 (sans-serif only). Subheadings, inline emphasis.
- **Tracking**: Display headlines get `letter-spacing: -0.025em` (tight); labels get `letter-spacing: 0.2em` (loose, all-caps).

## Layout

### Spacing System

Fluid padding based on viewport width. All major spacing uses `clamp()` to scale smoothly.

| Token | Value | Usage |
|-------|-------|-------|
| `--pad` | `clamp(22px, 5vw, 80px)` | Section padding, container inset |
| `--container` | `1280px` | Max-width for prose and grids |

### Grid & Composition

- **Hero** (`.hero`): 240vh tall (190vh on phones, 100svh under reduced motion) with a `position:sticky` inner frame. Type is arranged around the doorway in a 2×3 grid: eyebrow top-left, headline split top-left / bottom-right, lede and CTAs bottom-left, scroll cue bottom-right. The whole `.hero__ui` fades, scales and blurs as a function of `--doorT`, so the type falls away as the camera moves through the opening. On phones the split headline stacks into one left-aligned column.
- **Hold scenes** (`.scene--hold`): two columns. `.hold__anchor` is `position:sticky` and keeps the phrase in place while `.hold__stream` moves past it at its own rate. `.scene--hold-r` mirrors the columns. A full-bleed `::before` gradient, faded to nothing at both ends of the section, keeps dense text legible over the landscape without drawing a visible box. Below 900px the anchor stops holding and everything flows in one column.
- **Beats** (`.beat`): continuous prose with a bolded run-in lead sentence. Deliberately not headings, not numbered, not cards.
- **Scene sections** (`.scene`): Full-height (100svh min), centered or aligned left/right. Flexible layout for asymmetric composition.
- **Panel sections** (`.panel`): Translucent backdrop (green with blur), border, rounded corners. Live over the landscape for visual layering.
- **Forms**: 12-column grid, fields span 6 (two-up) or 12 (full-width). Responsive: `@media (max-width: 900px)` collapses to single column.
- **Flow grid** (`.flow`): Auto grid with bordered separators, key-value pairs for processes or lists.
- **Facts grid** (`.facts`): `repeat(4, 1fr)` on desktop, `repeat(2, 1fr)` at tablet, `1fr` on mobile.

### Responsive Breakpoints

| Breakpoint | Target | Changes |
|------------|--------|---------|
| `@media (max-width: 900px)` | Tablet | Nav menu collapses to side drawer; spiral rail hides; scene sections align left; grid columns collapse |
| `@media (max-width: 560px)` | Mobile | Footer grid to single column; facts grid to single column |

### Line Length

Body prose max-width: 42–54ch. Prevents lines from getting too long and hard to read.

## Components

### Navigation

- **Fixed nav** with minimal styling (no pill backgrounds). Sticky on scroll with blur backdrop.
- **Active indicator** ("nav-lamp"): Tubelight effect with glow, slides between sections.
- **Mobile toggle**: Hamburger → × animation, slides in full-height drawer menu.

### Buttons

| Variant | Style | Hover |
|---------|-------|-------|
| `.btn` (default) | Outlined, semi-transparent bg, cream text | Bg lightens, border brightens |
| `.btn--solid` | Solid cream bg, green text | Transitions to gold bg on hover |

Both support icon placement with `.arr` (arrow) that translates on hover.

### Forms

All form inputs:
- Font-size: 16px (avoids mobile zoom on iOS)
- Border-radius: 8px (consistent with cards)
- Focus state: Gold border + subtle gold glow (`box-shadow: 0 0 0 3px rgba(231,197,126,.14)`)
- Placeholder text uses `--ink-faint`, hits ~55% opacity (verify contrast on focus)

**Select dropdowns** use custom SVG arrow (sage green color) to override browser default.

### Cards / Doors

`.door` cards: Semi-transparent green bg with blur, bordered. Hover lifts (+5px translateY) and brightens border to gold.

## Motion

### Keyframe Animations

| Name | Effect | Duration | Easing | Use |
|------|--------|----------|--------|-----|
| `cue` | Golden scrollbar animation (0% → 100% top) | 2s | `var(--ease)` | Scroll indicator at bottom of opening scene |
| `reveal` (blur-to-focus) | Blur 16px → 0, opacity 0 → 1, scale .99 → 1 | 1.1s | `var(--ease-out)` | Section entrance animations (staggered via `--d` var) |

### Easing Functions

| Token | Curve | Usage |
|-------|-------|-------|
| `--ease` | `cubic-bezier(.22, .61, .36, 1)` | General transitions, UI movements |
| `--ease-out` | `cubic-bezier(.16, 1, .3, 1)` | Reveal animations, focus-in effects |

### Parallax & Scroll Interactions

- **Inertial scrolling**: Lenis (vendored) with `lerp: 0.085`. Anchor clicks and the progress rail route through `lenis.scrollTo`. Disabled entirely under reduced motion.
- **The thread** (`#spiral`) reshapes itself for the scene at the viewport centre and only exists while you are moving. It swings wide *opposite* the text on the alternating scenes (centre 26% against a right-aligned scene, 74% against a left-aligned one), and narrows to a quiet line down the gutter on hold scenes (centre 50%, about 4% of the viewport wide). Parameters lerp toward their target so the reshape is continuous, never a cut. It fades in on scroll and fades out about 700ms after movement stops, so a still page is never cluttered by it. As the closing scene arrives the coil **opens out and unwinds** (amplitude roughly doubles, from about 17% of the viewport to 31%) while its opacity falls to zero, so it reads as making way rather than switching off. It is fully gone before the door appears: the last frame of the page is the door, one line and one button, nothing else. Under reduced motion it is static and follows the same closing fade.
- **Reading veil** (`.readveil`): one fixed full-viewport layer whose opacity follows how much dense text is on screen. It replaced per-section scrims, which were the cause of the horizontal banding: two adjacent sections each faded their gradient to transparent at the shared edge, leaving a bright stripe at every seam. A single fixed element cannot produce a seam.
- **Journey progress** is measured from the *end of the hero* to the end of the document, so adding the 240vh door section does not compress the landscape crossfade.
- **Landscape layers** (`.stage__layer`): Scale (1.05 + parallax) and opacity crossfade based on scroll position. Four-layer progression.
- **Focus-in reveals**: Applied to `.focus-in` elements; staggered via `--d` custom property (multiply by 90ms).
- **Reduced motion**: All animations disabled via `@media (prefers-reduced-motion: reduce)`. Blur → instant; opacity → instant; scale → none.

### Navigation Transitions

- **Nav lamp slide**: 0.45s `--ease` for left/width positioning.
- **Mobile menu slide**: 0.45s `--ease` for translateX.
- **Scroll cue animation**: 2s infinite, smooth flow-down effect.

## Accessibility

### Color Contrast

- Primary text on dark green: 13.5:1 ✓ (AAA)
- Interactive elements (buttons, links): 7:1+ ✓ (AA large)
- Labels / faint text: 6.8:1 (verify; borderline AA on small text)

### Motion

- All animations disabled under `@media (prefers-reduced-motion: reduce)`
- Entrance reveals use crossfade as fallback (no blur or scale)

### The header

One component, `.sitehead` in `tokens.css`, on all twenty pages. Same lockup,
same five tabs in the same order — **Find help · Bills & denials · How it
works · Students · Partners** — same gold "Find help" pill, same tubelight
lamp, same wrap rule, same stuck-on-scroll rule. It was two headers that had
drifted: five tabs on one half against three on the other, a solid pin against
an outlined one, 22px of padding against 12px, a drawer against a wrap.

On the directory the four section links point back into the narrative page,
because that is where those sections are, and the lamp ships with them and
never lights: there is nothing on a directory page for it to slide between.
Shipping it anyway is what lets the two headers be one string of markup.

Each half sets **six colour tokens and one line of positioning**, nothing else:

| token | narrative | directory |
|---|---|---|
| `--head-bg` | `rgba(19,35,26,.55)` | `rgba(252,254,247,.90)` |
| `--head-line` | `--hair` | `--line` |
| `--head-ink` | `--cream` | `--ink` |
| `--head-ink-2` | `--ink-soft` | `--ink-2` |
| `--head-ink-3` | `--ink-faint` | `--ink-3` |
| `--head-hover` | `rgba(252,254,247,.10)` | `--line-2` |
| `--head-dot` (the pin's centre) | `transparent` | `--gold` |
| `--head-shadow` | `0 1px 12px rgba(12,22,16,.6)` | `none` |
| position | `fixed` (floats over the door) | `sticky` (sits under the top edge) |

Both are **transparent until you have scrolled past 40px**, then take their own
page's ground with a blur. Over cream that is nearly invisible, which is the
point: the bar appears when there is something behind it to separate from. It
fades in over 120ms and out over 400ms — appearing is the safe direction to
hurry, because during the fade the bar's own type sits half-transparent over
whatever is passing under it.

The pin is **solid, filled with the header's ink** — cream on the dark half,
deep green on the light one, the same mark either way. Its centre is the one
piece that adapts: nothing on the dark ground, where the filled pin reads on
its own, and gold on cream, where the mark wants a counter.

**The bar has its own column.** It used to inherit each page's — 1280px with
an 80px gutter on the narrative side, 1160px with 44px on the directory — so
the wordmark sat 32 to 40px apart depending on the width and you could watch it
move when you switched pages. `--head-wrap` and `--head-gutter` are set once in
`tokens.css`; the directory's page column is derived from them, so the wordmark
still sits directly over the first thing under it.

Every class the bar is built from is styled in `tokens.css` — `.sitehead`,
`.brand`, `.brand__txt`, `.nav-lamp`, all of it. `check_one_header` fails if a
page sheet targets any of them, because only one half loads each sheet: the
lamp lived in `styles.css` and shipped ruleless on eighteen directory pages,
standing in the flow as an inline element and pushing every tab 4px right, and
the wordmark's widened phone hit-area was narrative-only.

Measured at nine widths from 320px to 1920px, on six pages: the bar, the
lockup, the pin, the wordmark, the strapline, the lamp and every tab box are
**pixel-identical**.

Below about 1050px the tabs take a row of their own, which reads as a
deliberate second line rather than the ragged two-then-three a plain wrap gives
between 700 and 1000px.

**`--head-h` is published by the bar itself.** With five tabs it comes to 73px
at a desk, 155px at 375px and 203px at 320px — no `calc()` in a stylesheet can
know that, so a `ResizeObserver` in `script.js` and `help.js` sets the custom
property from the measured height; the `calc()` in `tokens.css` is the no-JS
fallback and is exact wherever the tabs fit on one row. Everything that has to
clear a fixed header reads it: the hero's top padding is `max(what it wanted,
--head-h + a gap)` in all three places that set it, and every `scroll-margin`
on the directory is `calc(var(--head-h) + 14px)` — those were a flat 84px,
which on a phone landed the heading you asked for 70px behind the bar.

`check_one_header` fails if the tabs differ between pages, if the gold pill
comes off, if the lockup is edited on one half, or if either stylesheet so
much as restyles a padding on the shared bar.

### The focus ring

One ring, in `tokens.css`, for both halves of the site:

```css
:where(a,button,input,select,textarea,summary,[tabindex]):focus-visible{
  outline:3px solid var(--focus); outline-offset:3px; border-radius:6px;
}
```

The colour is a **property of the surface, not of the control**. Because the
ring is offset outward it is painted on the ground the control sits on, so a
button cannot know what colour its own ring should be. `--focus` defaults to
`--green` for the light directory; each dark room re-points it once and
everything inside inherits:

| Surface | `--focus` | Ratio against its ground |
|---|---|---|
| the directory page | `--green` | 13.2:1 on white |
| `.mast`, `.hfoot`, `.langnote`, `.vowbox` | `--gold-lit` | 11.5:1 on `--green-deep` |
| `.sos` (the clay emergency panel) | `#FFF` | 7.6:1 |
| `body` on the narrative side | `--gold-lit` | 11.5:1 |

Dark *controls* — `.skip`, `.call`, a pressed `.chip` — deliberately set
nothing: their ring lands on the light page outside them.

Two controls hand their ring to a wrapper and set `outline:none`; both restore
a `Highlight` ring under `@media (forced-colors: active)`, where the border
and box-shadow standing in for it are discarded.

`check_focus_ring` guards all of it, including telling a dark room from a dark
control by asking the built HTML whether the class ever appears on something
focusable.

### Headings

One `h1` per page, no level skipped, on all twenty pages
(`check_heading_order`). Footer column labels are `h2` with a class, not `h4`
chosen for its size.

### What a "checked" date means

Two tools stamp it, and between them they cover every row —
`check_every_row_has_someone_to_verify_it` fails if one falls through:

- **`verify_phones.py`** asks each organisation's own site whether the number
  we print is its number. It owns every row with a ten-digit number in it.
- **`check_links_live.py --stamp`** owns the rest: a row whose "phone" is 311,
  or `Text FOOD to 726879`, or nothing at all. For those, verifying can only
  mean *the site is live and still on the organisation's own domain* — so that
  is what their date means, and this is the paragraph that says so.

A row whose number the sweep could not confirm keeps its older date. It is
never stamped on a guess: 31 rows still read June for that reason, and the
pages say "Checked June–August 2026" rather than rounding up.

### Tap targets

**44px minimum on every control**, not the 24 of WCAG 2.5.8: this is read on a
phone by somebody who is frightened, often one-handed, often in a hurry. The
exception is a link inside a sentence — the 911 in a translated paragraph —
which 2.5.8 exempts and which cannot grow without breaking the line.

Stacked links get **real padding**, not a widened pseudo-element: growing them
invisibly makes adjacent targets overlap, which trades a small target for a
mis-hit. Standalone controls (the wordmark on a phone) get the pseudo-element,
which leaves the glyph and the layout untouched. `check_tap_targets` names
seven controls and fails on any under 44.

### Reflow

At 320px with text at 200% — the narrowest screen at the largest type — no
page may scroll or be dragged sideways. `html, body { overflow-x: clip }` on
the narrative side: `hidden` on one axis coerces the other from `visible` to
`auto`, which makes body its own scroll container and leaves the document
element scrolling instead. `clip` clips without creating a scroll container,
so every `position: sticky` on the page keeps working.

Nothing is hidden by a physical offset. `left: -9999px` is off the *end* on a
right-to-left page, not off-screen — it made help-ur.html 10,695px wide. The
skip link and the spam honeypot are clipped to a 1px box instead.

### Text Sizing & Readability

- Minimum font-size: 12px for labels (uppercase, high contrast)
- Body text: 17px with 1.6 line-height (ample breathing room)
- Display headings: 2.6rem–6.4rem with tight leading (1.02) for visual hierarchy

### The ten language pages

Each of New York's ten Local Law 30 languages has **a page**, not a panel:
`help-es.html`, `help-zh.html`, `help-ru.html`, `help-bn.html`, `help-ht.html`,
`help-ko.html`, `help-ar.html`, `help-ur.html`, `help-fr.html`, `help-pl.html`.

They were panels — a heading, three sentences and a Close link, revealed by
`:target` under an otherwise English page. A blurb *about* the page rather
than the page. Somebody who reads only Bengali got a paragraph in Bengali and
then two hundred resources in English.

Each page carries what the English front page carries, **in the same order and
the same components**: masthead over the painted valley, four emergency
numbers, seventeen kinds of help with places named and dialable under each,
the promise, the footer. `i18n.py` holds every word — about 70 strings and 17
blurbs per language — and is the file a translator gets handed.

**What is not translated, and why.** The 340 resource descriptions are English
and this site has no way to check 3,400 translations of them. So the cards name
places and dial them — a proper noun and a number are the same in every
language — and one quiet card near the top says the detail pages are in English
and that 311 puts an interpreter on the line free, at any hour. Every link
carries the language through (`help-food.html?lang=bengali`), so the filter is
already applied when the reader lands, the chip is visibly pressed, and the
English page shows the same sentence in their language so the words do not
change mid-journey with nothing to say why.

**Formatting adapted, not redesigned:**

| script | what it needs | why |
|---|---|---|
| Korean | `word-break: keep-all` | breaks between eojeol; the default split 묻지 않/습니다 |
| Bengali | leading 1.85 | a headline (matra) and ascenders English does not have |
| Arabic, Urdu | leading 1.9, `dir="rtl"` | glyphs hang well below the baseline |
| Chinese, Korean | measure 44ch, not 68 | no word spaces for the eye to rest on |
| CJK, Bengali, Arabic, Urdu | `<b>` not `<em>` | Fraunces has a drawn italic; these have none, and a browser asked for one slants by matrix |

Per-script CSS may set **typography and nothing else** — leading, tracking,
word breaking, the measure. Never padding, margin, gap, radius or box size:
those are the page's rhythm, and a language page is the English page in
another language, not another design of it. Measured at 1280px, Spanish,
Chinese, Bengali and Arabic come back with the same 26px from the language row
to the masthead, the same 37px to the emergency panel, the same 60px to the
promise, and the same 24px card padding and 16px radius as English.
(`check_language_spacing_is_shared`)

Month names and date spans are per-language too (`i18n.MONTHS`,
`i18n.DATE_SPAN`) — Chinese and Korean put the year first, Spanish takes "de".
A date is the one thing on that line a reader actually checks.

Right-to-left is nearly free because the whole stylesheet is written in logical
properties. The four things that must **not** mirror — a phone number, an
organisation's name, the wordmark, an email — carry `dir="ltr"` in the markup.

Guarded by `check_directory_languages`, `check_language_header`,
`check_language_round_trip`, `check_language_print`, `check_language_voice`
and `check_script_typography`.

### Multilingual & Plain Language

- Vocabulary kept simple; no jargon
- Generous spacing for better scannability (especially for older adults)
- All form labels clearly associated with inputs
- Alt text and ARIA labels on interactive elements
- **Numbers dial in every language.** `dial()` links 911, 988 and 311 inside
  the translated sentences at build time, so the ten language panels tap
  through like the rest of the site rather than printing digits to memorise
  (`check_language_numbers_dial`).

## The resident side — eighteen generated pages

The whole verified NYC resource directory, grouped by the sentence somebody
arrives with rather than by the categories the agencies use. It is the only
part of the site that is generated, and `python3 build_help.py` writes all of
it in one go.

```
help.html            the way in: one cluster per kind of help, three examples each
help-<need>.html     one page per kind of help, with everything in it
```

**To change anything in it, edit the source and rebuild:**

```
python3 build_help.py
```

- **Resource data** lives in `data/resources.csv` — one row per resource, with
  the columns the original NYC directory used. Add, correct, or remove rows
  there. New rows go through `merge_rows.py`, which refuses one with a missing
  column, no verification date, or no way to reach it, and skips duplicates.
- **Everything else** — the needs and their wording, the second-level buckets,
  the search vocabulary, the emergency numbers, the ten in-language panels —
  lives in tables at the top of `build_help.py`, each with a comment saying
  what it is for.
- **Never hand-edit a generated page.** A fix typed into one survives until
  the next build and then disappears. `check.py` compares every one of them
  against the generator's output and fails if any differs.
- The build also rewrites one block of `index.html`: the list of what the
  directory holds. That list is the directory's table of contents rendered on
  the other side of the site, and hand-maintaining it is how it came to offer
  eight of sixteen kinds of help.

### Why it is split, and where the split falls

It used to be one page carrying every resource: 250 KB of markup, sixteen
headings deep, opened by somebody frightened, on a phone, looking for one
phone number. Now:

- **The front page is a way in, not the directory.** One cluster per need —
  icon, the sentence, three real places with real numbers, and a link to that
  need's own page. Nobody has to read past the cluster that matches their
  sentence.
- **Each category page is built to be skimmed**: a rail of what is on it with
  counts, resources in named buckets ("somewhere to sleep tonight" / "stop an
  eviction" / "money for the rent") rather than one run of forty, a Start here
  block holding the best first call, and every neighbouring kind of help one
  tap away.
- **Everything on a category page is bucketed by subject**, whether it got
  there through its own category or through a cross-reference keyword. These
  used to be two sections, with cross-references collected at the bottom under
  "Also worth calling"; on a need that cuts across everything that made the
  page five rows and then a heap.

Two rules that are not obvious and are load-bearing:

- **A cross-reference keyword matches at a word start, never anywhere.**
  Plain substring matching put a soup kitchen, a diaper bank and a
  hospital-bill charity on the disability page, because `ssi` is inside
  a-ssi-stance, mi-ssi-on and a-ssi-stors.
- **A row is filed by what it IS — its name and subcategory — never by its
  tags.** Tags are search vocabulary and are deliberately generous; a health
  centre is tagged "dental" so a search for a dentist finds it. Letting that
  decide where rows file put sixteen general clinics under "Teeth".

### Why generated rather than fetched

The reader is plausibly on a six-year-old Android, on transit data, at a
locked-down library terminal, or using a screen reader. Fetching JSON and
templating every row in the browser fails all four. So the rows are baked in
once, here, and on a category page `help.js` only ever *hides* them — the
worst case when the script fails to load is that somebody sees the whole list,
which is what they came for.

The front page is the one exception, and a deliberate one: it carries clusters
of three, not the whole directory, so its search runs off a compact index in
the document (`<script type="application/json" id="ix">`) and builds results
from it — using the same `.r` markup a real row uses, so there is one resource
card design on this site and not two. `check.py` holds the line: the index
must cover every resource, every result must link to an anchor that exists,
and `help.js` may write markup in at most two places.

### Search

The search box, the result count, the print button and the filters are **one
card, three zones divided by hairlines**: what you type, what that got you, and
how to narrow it further. They were four separate objects — a labelled box, an
orphaned grey line under it, a bordered card of chips, and, below the lot and
outside everything, the count on the left with the print button on the right.
All four did the same job and none looked related to any other.

The count sits directly under the box that changes it. The scope note beside it
no longer repeats the number standing next to it, which is one fewer place for
a count to go stale.

#### How a row is scored

Six fields, weighted, best match per word:

| field | weight | what it is |
|---|---|---|
| name | 6 | the organisation's name |
| kind | 4 | the subcategory line under it |
| tags | 3 | including whole sentences somebody would type |
| alias | 2 | synonyms the row's own words fired, plus its needs' ten-language vocabulary |
| body | 1 | the description |
| **cat** | **0.6** | synonyms its *category* fired — below the description on purpose |

Then three multipliers:

- **Exact ×1.5, prefix ×1, stem ×0.7.** A whole word beats a word start beats a
  match that needed the stemmer. "free counseling" used to open with Right to
  Counsel — the eviction lawyers — because stripping `-ing` leaves `counsel`,
  and English does not distinguish the legal root from the therapeutic one.
- **Inverse document frequency**, floored at 0.15. A word in half the rows is
  worth almost nothing; a word in one row is worth its full weight. Without it
  "free eyeglasses" opened with *Free* Naloxone and *Free* Eviction Defense,
  because "free" sat in their names and "eyeglasses" sat in somebody's alias.
- **Whole-phrase bonus +14**, if the query appears verbatim in the name, the
  alias **or the tags**. Tags are where this directory puts the exact sentence
  a reader types.

`check_critical_queries` models all of this in Python and asserts that 77
named searches come back **first**, not merely somewhere. Every constant is
read out of `help.js` by `_js_constants`, so the model cannot drift from the
code without changing with it or failing for a missing name. It is still a
model of another language's behaviour: it was checked against the live page on
twenty-two queries and agrees with the browser on all of them.

The `cat` field exists because a category is coarse. "Housing & Shelter"
contains the word *shelter*, so every row filed under it fired the shelter
synonyms, and Ronald McDonald House — which is for the family of a child in
cancer treatment — came back first for "somewhere to sleep tonight". Dropping
the category outright costs nineteen rows every synonym they have, including
the childcare ones whose names never say "childcare".


The people this is for do not type "domestic violence" or "substance use
disorder" — those are the words the agencies use about them afterwards. They
type "my husband hits me" and "heroin". So:

- **Every word must match, until that returns nothing.** Then the cut relaxes
  a word at a time until there is something worth showing, and stops relaxing
  the moment a row matches the whole query. The count says plainly when it was
  not matched in full.
- **Where a word matched decides the order**: a resource's name beats its
  subcategory beats the tags we filed it under beats the plain-English phrases
  we attached beats a paragraph about it. And a whole word beats a word start,
  which is why "who do i call" no longer opens with Callen-Lorde.
- **A phrase written into `SYNONYMS` is the strongest signal there is**,
  because those phrases were written down for exactly this.
- **A crude four-suffix stemmer**, because prefix matching only works one way:
  "dent" finds "dentist", and "abused" found nothing, because the page says
  "abuse".
- **Words that matched nothing are named**, not silently dropped.
- `check.py` carries the forty-six searches that must not stop working, each
  with the resource it has to reach. It checks the data, not the ranking: if
  the words are there `help.js` can find them.

### Register — one palette, two keys

`tokens.css` holds every brand hue, both typefaces, the easings and the radii,
and both stylesheets map onto it. Neither may restate a brand hue; `check.py`
fails if either does, because two copies of a colour are two colours as soon
as one is edited.

What each side chooses is only the key. The narrative site is a dark green
room you walk through — pinned scenes, a WebGL door, inertial scroll. The
directory is what is on the other side of that door, in daylight: cream
ground, near-black green ink, an 18px floor, 44px targets, nothing moving that
you did not touch.

Carried across on purpose, and each one guarded:

- the masthead is the same painted valley the door opens onto (`band.webp`,
  22 KB, budgeted at 40);
- headings turn gold and italic the same way;
- the brand lockup is the same 20px-over-9.5px lockup;
- the nav pill is the same pill, and gold means "the resident side" in both
  places;
- the footer is the same deep green.

What is **not** carried across is the machinery. No WebGL, no inertial scroll,
no pinned scenes, no scroll-driven anything.

### Things that are safety decisions, not content decisions

- **The emergency strip** (`SOS` in `build_help.py`) is hand-picked. A
  heuristic over tags and hours previously put a hospital switchboard and two
  copies of 988 in front of somebody in danger.
- **Phone numbers stay in Western digits in every language.** Bengali prose
  would normally write 311 as ৩১১ and Urdu as ۳۱۱; both are correct and both
  are useless against the keypad in somebody's hand.
- **The ten languages are Local Law 30's ten**, not a shortlist: Spanish,
  Chinese, Russian, Bengali, Haitian Creole, Korean, Arabic, Urdu, French,
  Polish. Each panel names every kind of help in that language, each opening
  its own page, and leads with 911 and 988 before the interpreter line.
- **The in-language panels have not been reviewed by native speakers.** They
  are short and carry nothing a reader must act on precisely, and the only
  instructions any of them give are "call 911 if you are in danger", "call 988
  to talk to somebody" and "call 311 and ask for an interpreter". Get them
  read before launch — the multilingual students are the obvious reviewers.
- **The honesty statement appears on every resident page and every printed
  sheet**, because a leave-behind is exactly where somebody mistakes a student
  for a professional.
- **A website that redirects off its own domain is treated as a takeover until
  a human says otherwise.** `check_links_live.py` found `ppgny.org` — Planned
  Parenthood of Greater New York — lapsed and redirecting to an unrelated
  commercial site, with the directory quietly sending people looking for
  reproductive health care there.
- **A resource whose HTTPS chain is broken is dropped.** A current desktop
  browser papers over a missing intermediate certificate; a six-year-old
  Android shows a full-screen security warning instead of the page.

### Print

The printed sheet is a real output — students hand people paper.

- **A category page prints what the filter is showing**, so narrowing to "I
  need food" in Brooklyn and printing gives exactly that sheet.
- **The front page prints its clusters**: every kind of help, three real
  places with numbers under each, in three columns. One or two sheets, not the
  forty the old single-page directory produced.
- `help.js` opens every disclosure on `beforeprint` and closes them after,
  because on paper the hours, address and languages are the useful lines and
  there is nothing to tap.
- The attribution and the "Checked <month>" line are on both, and the date is
  derived from the newest verification in the data. It used to be typed in
  three places, two of which said June while the third said August.


## Asset Libraries & References

### Images

- Landscape backgrounds: four crossfading layers, **`land1–land4.webp`** (the `.png` masters stay in the repo but are no longer shipped: 14.1 MB → 363 KB). `land1` is eager because the door needs it as a texture; the other three carry `data-src` and load on idle.
- `hero.png` and `weave.png` are unused.
- `check.py` enforces a per-file and total size budget on the shipped landscapes.

### External Resources

- **Google Fonts**: Fraunces + Inter (preconnected via `<link rel="preconnect">`). The only third-party origin the site touches, and it is disclosed in `privacy.html`.
- **Vendored, not CDN**: `assets/vendor/three.module.min.js` + `three.core.min.js` (three.js splits its build — both are required) and `lenis.min.js`, with versions recorded in `assets/vendor/VERSIONS.txt`. `python3 -m http.server` still serves the site directly — the generated files are the eighteen resident pages, and they are committed, so a clone with no Python run still serves the whole site (see **The resident side** above). Vendoring keeps the privacy disclosure honest and means no CDN outage can break the page.
- **Icons**: Inline SVG for logo (pin marker) and form controls (select dropdown arrow)

## Verification

`python3 check.py` prints the pass/fail total; add `-v` to list every passing
check. It covers dead links and anchors (including fragments into any local
page, not just the homepage), missing assets, the honesty statement present
verbatim on every surface that offers help, no surviving references to the
removed Schools chapter or the unlaunched Companionship track, no numeric
track-record claims, form completeness and labelling, the door's fallback
paths and transition invariants, the reel's roll geometry and released states,
the line's paired sentences and its undrawn rule, the doors' disclosure wiring
and equal-height contract, vendored dependency integrity, the asset-size
budget, and that `script.js`'s tracked nav sections match the markup.

On the resident side it covers: that every generated page still equals
`build_help.py`'s output and that no orphaned one survives a renamed need;
that every resource is reachable and every `tel:` will actually dial; that the
emergency strip leads with 911 and never repeats a number; the no-JavaScript
contract; that the front page's search index covers every resource and every
result links to an anchor that exists; that each cluster promises the number
its page holds and previews only resources that are really on it; that each
rail matches its page in order; that only the lead block says "Start here";
that all ten Local Law 30 languages are present in the bar, the panel and the
filter on every resident page, with real BCP-47 subtags, every kind of help
named in each, every panel carrying 911, 988 and 311, and no number left in
non-Western digits; that the forty-six searches which must not stop working
still reach what they are supposed to reach; that no prose counts something
the build already counts; that every "checked" date is the derived one; that
the palette lives only in `tokens.css` and the devices that make the two
halves one brand are all still there; that no grid can push the page sideways
at 320px; that print keeps the hours and the honesty statement; and that the
home page names the same kinds of help, in the same words, and still leads
with help rather than with a partner pitch.

A missing file is reported as a failed check rather than raised, so one absent page never costs you the rest of the report.

## Notes

- The palette strategy (deep green + gold) is intentionally committed to avoid clinical coldness while maintaining trust and credibility.
- All spacing uses fluid `clamp()` for smooth scaling across device sizes, no hard breakpoints except for layout restructuring.
- The landscape is the hero; UI chrome is minimal and transparent to let content and imagery speak.
- Every surface must answer "Who are these students? Can I trust them?" in 10 seconds. Design serves clarity over decoration.
