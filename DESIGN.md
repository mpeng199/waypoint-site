# Design System

A scroll-driven journey through a painterly landscape, with warm green + gold palette. Every surface is designed for clarity first: busy adults and vulnerable community members must understand the "what we are / what we are not" statement in under 10 seconds.

## The shape of the page

The homepage is one continuous journey. It opens on **the door** (real-time WebGL), carries you through it into the painted world, and closes on the same door seen from the far side.

Between those two doors, **no two beats are built the same way**. Five identical hold scenes and five identical phrase scenes told the whole story in two mechanisms, and a reader stops seeing a mechanism they have already met. Each beat now gets the device that carries its particular fact best, and the landscape crossfade — the thing that makes it one journey rather than a stack of sections — runs underneath all of them.

    door
      → the vanishing word          real, free, and invisible
      → a phrase                    so we carry it to people
      → [stop] THE ENVELOPE         the letter, and what is printed on its back
      → a column, and the ribbon    almost nobody uses it / where we take it
      → the transcript              what a referral looks like when it works
      → [stop] THE STATEMENT        the honesty statement, a sentence at a time
      → [stop] THE LINE             what a volunteer does, and never does
      → a column                    vetting, the reason about dates, the review
      → a phrase                    the second track
      → the word for help           multilingual reach, the directory, the counts
      → the struck ask              not money, not an endorsement, your materials
      → [stop] the admission        we have not done this yet
      → partner form → students → students form → the door, from the other side

Rules the page is built to, unchanged and now stricter: **no card grids, no numbered step lists, no section labels** (the eyebrows above each chapter are gone — a beat that needs a label has not earned its place), no visible boundary between beats. Each beat hands off to the next.

## The scrub engine, and stopping the world

Two mechanisms carry every set piece, and both live in `script.js`'s single `tick()`.

**`[data-scrub]` gives an element a `--p` that runs 0 → 1 as it crosses the viewport**, and each set piece is then a pure CSS function of that one number — no timers, no transitions, no state. This is the same discipline the door is built to: **wherever the scroll stops is a finished frame**, never a half-played animation. Three modes:

| Mode | `--p` runs | Used by |
|---|---|---|
| *(default)* | as the element's top enters to as its bottom leaves | the vanishing word, the ribbon, the word for help |
| `enter` | until the element's top reaches the ceiling | effects that must be over before the section settles (the struck ask, the admission) |
| `pin` | the travel of a sticky child through its tall wrapper | the three stages |

**`[data-world-hold]` stops the landscape.** The scroll a marked section consumes is subtracted from journey progress rather than spent on it, so the crossfade freezes on the frame it was on and picks up exactly there once the piece is behind you. The same measurement drives `--stop`, which deepens the reading veil and clears the thread out of the way, so a set piece plays in a quiet, dimmed room and the object in the frame is the only thing in it. Four beats stop the world: the envelope, the statement, the line, and the admission.

`.seq` is the shared reveal: children get `--r` from two `min()`'d clamps against the parent's `--n` (the count, less half an item) and their own `--i`. **The crossfade has to stay sharp** (`--sharp`, 5.5). Sequenced items are stacked on the same spot, so a lazy fade leaves two sentences at half opacity on top of each other, which is unreadable in a way neither of them is alone. The windows overlap for about 8% of an item's turn: long enough to read as a swap, short enough that it is never two things at once.

## The set pieces

**The envelope** (`#bills`). A flat mailer in real CSS 3D — `perspective` on the wrapper, `preserve-3d` on the group, the pocket nearest the lens at `translateZ(12px)` so the sheet is genuinely *inside* it rather than layered over it. The flap opens on a hinge at the top edge, the envelope falls away and fades, and the letter comes forward and turns over. The front is the bill: redaction bars and one italic line. The back is what New York already built. It is the argument of the whole chapter as one object — the help was on the other side of the page, and only one side ever arrives. The bars are bars and never a figure, because there is no figure we could invent honestly (`check.py` fails on dollar amounts anyway).

**The statement.** The one thing on the page that is never half-shown: sentences arrive cumulatively and all six are up by the end, so the finished frame is the whole statement. The two "we are not / we do not" sentences take a gold rule that draws down beside them. The text is verbatim and must stay contiguous — `check.py`'s fragments are tag-free runs, so a sentence may be wrapped but never split.

**The line.** A gold hairline pinned at the centre of the frame that does not move while six pairs cross it: what a volunteer does above, what they never do below. The mechanism is the meaning, and it puts the eight nevers at the same size and weight as the work rather than in the fine print, which is what "safety first" is supposed to look like.

**The transcript** (`#work`). A referral shown rather than described — the person's words in Fraunces italic gold, what the volunteer does in Inter against a gold rule, alternating. It replaced four stacked beats and is shorter than they were.

**The word for help.** One sentence that holds while the word inside it changes through the languages our students speak. The slot is `aria-hidden` with a visually-hidden "help" beside it, so the sentence reads correctly aloud.

**The ribbon.** Two rows of place-kinds drifting in opposite directions under the distribution beat, masked at both edges. It is `aria-hidden`: it repeats what the beat above it already says, and a screen reader does not need it twice.

**The vanishing word** and **the struck ask** are the two small ones — a fill that drains out of "And invisible." leaving a gold outline, and a rule drawn through "Not money. Not an endorsement." The drained fill floors at 32% on purpose: the point is that the help is still there and you cannot see it, not that the word becomes unreadable.

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

- **Hero** (`.hero`): 240vh tall (190vh on phones, 100svh under reduced motion) with a `position:sticky` inner frame. Type is arranged around the doorway in a 2×2 grid: headline split top-left / bottom-right, lede and CTAs bottom-left, scroll cue bottom-right. The whole `.hero__ui` fades, scales and blurs as a function of `--doorT`, so the type falls away as the camera moves through the opening. On phones the split headline stacks into one left-aligned column.
- **Stages** (`.scene--stage`): a tall `.stagewrap` (240–320vh) giving the scroll length, and a `.stagefix` sticky 100svh frame inside it holding the phrase, the object and one caption slot. The wrapper carries `data-scrub="pin"`; the section carries `data-world-hold`. Sticky is constrained by the section's *content* box, so the scene's own 50vh paddings still buy the clear space either side.
- **Hold scenes** (`.scene--hold`): two columns. `.hold__anchor` is `position:sticky` and keeps the phrase in place while `.hold__stream` moves past it at its own rate. `.scene--hold-r` mirrors the columns. Now used once, for the partner ask, where a reader genuinely is scanning a list of asks against a fixed heading. Below 900px the anchor stops holding and everything flows in one column.
- **Columns** (`.scene--flow`): one centred 680px column of beats with nothing else in the frame, used for the prose tails that follow a set piece. Deliberately plainer than a hold scene — after a pinned object, a quiet page is the contrast.
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
- **Journey progress** is measured from the *end of the hero* to the end of the document, so adding the 240vh door section does not compress the landscape crossfade. Scroll spent inside a `[data-world-hold]` section is subtracted from both the numerator and the span, so a set piece costs the crossfade nothing.
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
- Focus indicators available on buttons and form fields

### Text Sizing & Readability

- Minimum font-size: 12px for labels (uppercase, high contrast)
- Body text: 17px with 1.6 line-height (ample breathing room)
- Display headings: 2.6rem–6.4rem with tight leading (1.02) for visual hierarchy

### Multilingual & Plain Language

- Vocabulary kept simple; no jargon
- Generous spacing for better scannability (especially for older adults)
- All form labels clearly associated with inputs
- Alt text and ARIA labels on interactive elements

## Asset Libraries & References

### Images

- Landscape backgrounds: four crossfading layers, **`land1–land4.webp`** (the `.png` masters stay in the repo but are no longer shipped: 14.1 MB → 363 KB). `land1` is eager because the door needs it as a texture; the other three carry `data-src` and load on idle.
- `hero.png` and `weave.png` are unused.
- `check.py` enforces a per-file and total size budget on the shipped landscapes.

### External Resources

- **Google Fonts**: Fraunces + Inter (preconnected via `<link rel="preconnect">`). The only third-party origin the site touches, and it is disclosed in `privacy.html`.
- **Vendored, not CDN**: `assets/vendor/three.module.min.js` + `three.core.min.js` (three.js splits its build — both are required) and `lenis.min.js`, with versions recorded in `assets/vendor/VERSIONS.txt`. No build step; `python3 -m http.server` still serves the site. Vendoring keeps the privacy disclosure honest and means no CDN outage can break the page.
- **Icons**: Inline SVG for logo (pin marker) and form controls (select dropdown arrow)

## Verification

`python3 check.py` prints the pass/fail total; add `-v` to list every passing check. It covers dead links and anchors (including fragments into any local page, not just the homepage), missing assets, the honesty statement present verbatim on two surfaces, no surviving references to the removed Schools chapter or the unlaunched Companionship track, no numeric track-record claims, form completeness and labelling, the door's fallback paths and transition invariants, vendored dependency integrity, the asset-size budget, and that `script.js`'s tracked nav sections match the markup. A missing file is reported as a failed check rather than raised, so one absent page never costs you the rest of the report.

## Notes

- The palette strategy (deep green + gold) is intentionally committed to avoid clinical coldness while maintaining trust and credibility.
- All spacing uses fluid `clamp()` for smooth scaling across device sizes, no hard breakpoints except for layout restructuring.
- The landscape is the hero; UI chrome is minimal and transparent to let content and imagery speak.
- Every surface must answer "Who are these students? Can I trust them?" in 10 seconds. Design serves clarity over decoration.
