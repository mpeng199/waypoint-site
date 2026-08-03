# Design System

A scroll-driven journey through a painterly landscape, with warm green + gold palette. Every surface is designed for clarity first: busy adults and vulnerable community members must understand the "what we are / what we are not" statement in under 10 seconds.

## The shape of the page

The homepage is one continuous journey. It opens on **the door** (real-time WebGL), carries you through it into the painted world, and closes on the same door seen from the far side. In between, twelve beats alternate between the established phrase-per-screen rhythm and a denser **hold scene** used four times where a partner needs real depth.

    door → the gap → what we are → [hold] a Saturday morning → the honesty statement
      → [hold] who we send → [hold] who we reach → [hold] what we ask for
      → partner form → students → students form → the door, from the other side

Rules the page is built to: no card grids, no numbered step lists, no section labels, no visible boundary between beats. Each beat hands off to the next.

## The door (`assets/door.js`)

A wall in darkness with a door ajar, warm light knifing through the gap on the latch side, and the sunlit valley (`land1.webp`, the same asset the journey uses) beyond it. Scroll drives `t` from 0 to 1: the door swings wider, the beam brightens, and the camera dollies from `z 9.6` to `z -1.4`, through the opening. A bloom (`.threshold`) peaks at `t≈0.89` and covers the handover from canvas to the HTML landscape.

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

`window.__waypointDoor` exposes `set(t, mode)`, `live(on)` and `still()`; `window.__waypointTick` drives the scroll choreography. Both exist so `check.py` and browser verification can step through states deterministically.

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

`python3 check.py` (add `-v` to list passes). 170 checks covering dead links and anchors, missing assets, the honesty statement present verbatim on two surfaces, no surviving references to the removed Schools chapter or the unlaunched Companionship track, no numeric track-record claims, form completeness and labelling, the door's fallback paths, vendored dependency integrity, the asset-size budget, and that `script.js`'s tracked nav sections match the markup.

## Notes

- The palette strategy (deep green + gold) is intentionally committed to avoid clinical coldness while maintaining trust and credibility.
- All spacing uses fluid `clamp()` for smooth scaling across device sizes, no hard breakpoints except for layout restructuring.
- The landscape is the hero; UI chrome is minimal and transparent to let content and imagery speak.
- Every surface must answer "Who are these students? Can I trust them?" in 10 seconds. Design serves clarity over decoration.
