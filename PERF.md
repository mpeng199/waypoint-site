# Performance

Waypoint's readers are, by design, the people with the worst phones and the
worst connections in New York. Page weight is not a vanity metric here; it is
whether someone with a medical bill they cannot pay ever sees the page that
tells them the help is free. Everything below is measured, not assumed.

## Where it stands

Lighthouse, mobile preset, simulated throttling, median of five runs against
`python3 serve.py`:

| | before | after |
|---|---:|---:|
| Performance | 43 | **84** |
| First Contentful Paint | 6.3s | 3.4s |
| Largest Contentful Paint | 7.5s | 3.5s |
| Total Blocking Time | 700ms | **0ms** |
| Speed Index | 6.3s | 3.4s |
| Time to Interactive | 8.0s | 3.5s |
| Transfer | 1547KB | 683KB |

Accessibility 100, Best Practices 100, SEO 100, CLS 0.

Other pages: `help.html` 85, `help-legal.html` (the largest directory page) 87,
both with 0ms blocking time.

Run a single measurement yourself with:

    python3 serve.py 8771
    npx lighthouse@12 http://localhost:8771/index.html --preset=perf \
      --form-factor=mobile --screenEmulation.mobile --quiet

Lighthouse is noisy — roughly one run in five comes back ~10 points low on an
otherwise identical build. Take a median of five before believing a regression.

## What actually cost the 41 points

**The WebGL door downloaded on every device.** `assets/door.js` statically
imported Three (750KB across `three.module.min.js` and the `three.core.min.js`
chunk it re-exports), and `index.html` preloaded it besides. The capability
gate that falls back to the CSS poster ran *after* that import, so it could
save the WebGL work but never the download. On a phone the doorstage is hidden
outright once it hands over to the scroll journey, so the bytes bought nothing
at all.

The import is now dynamic and behind the gate, which also grew: narrow
viewports, `prefers-reduced-motion`, `Save-Data`, 2g/3g, and under 4GB of
device memory all take the poster path. The poster is a finished CSS picture,
not a placeholder — it is the same fallback the no-WebGL case has always used.
Desktop is unchanged.

**Parser-blocking scripts.** `lenis.min.js` and `script.js` now carry `defer`.
`defer` preserves document order, so Lenis still initialises before
`script.js` reads `window.Lenis`.

**Comments shipped to phones.** These sources are about half prose, and that
prose is why the code is maintainable — but there is no reason to send it over
a cellular connection. `build_min.py` strips comments into `*.min.css` /
`*.min.js`, which is what the pages link. Brotli'd, the five files go from
60.9KB to 22.6KB.

**Lenis' frame loop never stopped.** It shipped as
`(function raf(t){ lenis.raf(t); rAF(raf); })(0)` — a frame callback for the
life of the page, on every device, including while the reader is just reading.
The scroll loop beside it already had a `busy()`/`wake()` idle condition; this
one now matches it, with 300ms of grace so momentum cannot be cut off by a
flickering `isScrolling`.

**Caching was off in production.** Cloudflare serves static assets as
`max-age=0, must-revalidate` unless told otherwise, so returning readers
re-validated all 750KB of Three, both stylesheets and every landscape on every
page view. `_headers` fixes it. Read the comment at the top of that file before
editing it: overlapping patterns *comma-join* their headers rather than
overriding, which produces a malformed `Cache-Control` that nothing reports.

Two smaller things: the 288KB of decorative scenery now honours `Save-Data`
like the door does, and the missing favicon (a 404 on every page view) is now
`favicon.svg`.

## What was deliberately not changed

Not every item on a performance checklist is a defect in a given codebase.

**Do not add a debounce to the directory search.** It was measured at 390px
with the CPU throttled 4x, median of seven per term: `"f"` 19.9ms, `"fo"`
15.5ms, `"foo"` 4.2ms, `"food"` 3.4ms. The first keystroke is the expensive
one, because one letter matches nearly every row. 19.9ms is one dropped frame
against a 200ms INP budget; a debounce long enough to coalesce real typing
would add more latency to every result than it ever removes. If it climbs, the
fix is to narrow the candidate set on the first letter, not to delay the
response. The reasoning is kept next to the handler in `help.js`.

**Loading skeletons have nowhere to go.** Nothing on the site renders an empty
region and fills it in later. The one deferred thing — landscape layers B, C
and D — sits at opacity 0 until you scroll to it, so it has no visible arrival,
and the door's CSS poster is already the skeleton pattern done properly: a
designed placeholder shown until the real thing is ready.

**Pagination has nothing to paginate.** The directory is already split into 28
static per-need pages. `help.html` is 717 DOM elements; the largest page,
`help-legal.html`, is 1,895 with 0ms blocking time. Static splitting beats
pagination on both performance and SEO.

**Code splitting would split 20KB.** `help.min.js` is 20.7KB and `script.min.js`
16.2KB. The only payload worth splitting was Three, which is now split off
entirely by the door gate.

**The database needs nothing.** `form_submissions` has one row. It already
carries three indexes, and Supabase's linter reports two of them as unused —
which is what Postgres does on a table this size, not a defect. There are no
N+1 queries: neither Edge Function issues a query inside a loop. Connection
pooling does not apply, because the functions reach Postgres through PostgREST
over HTTP and hold no connections of their own. The linter's other finding,
"RLS enabled, no policy", is the intended design: the table is written only by
the `submit` function with the service role, and adding a policy would widen
access rather than protect it.

**A load balancer is what Cloudflare already is.** The site is static assets on
an anycast edge.

**Text compression is already on.** The live site returns `content-encoding: br`.
Lighthouse reports it as an opportunity worth 3.3s only because `serve.py`
deliberately sends no compression and no caching locally.

## Working on this

After editing any of `styles.css`, `tokens.css`, `help.css`, `script.js` or
`help.js`:

    python3 build_min.py

`check.py` fails if you forget. That guard matters more than it looks: almost
every other check reads the readable source, while the browser is served the
minified copy — so without it you could edit `styles.css`, pass all 3,846
assertions, and ship the stylesheet from before your edit.

Two suites, both of which must be green:

    python3 check.py        # 3846 assertions, reads the source
    node check_runtime.js   # 18 assertions, drives a real Chrome

They cover different things, and the split is the point. `check.py` cannot see
what the browser fetches, so it cannot tell you that a re-added
`<link rel="modulepreload" href="assets/vendor/three.module.min.js">` has put
750KB back on every phone while every assertion still passes. `check_runtime.js`
loads the page in headless Chrome under four emulation profiles and asserts on
the actual request list, the console, and whether the two rAF loops come to
rest and wake again on a real wheel event.

## If you are about to make it faster

The remaining render-blocking cost is the Google Fonts stylesheet (~800ms
simulated) and the two stylesheets. Self-hosting the two families would remove
a third-party origin and a connection setup — but `privacy.html` discloses
Google Fonts by name and `check_vendored()` enforces that disclosure, so the
copy and the guard have to move with it.

There are also 23MB of unreferenced PNGs (`assets/land[1-4].png`,
`assets/band.png`, and `hero.png` / `weave.png`, each duplicated at the repo
root). Nothing links them — `check.py` forbids referencing them — but Cloudflare
serves the directory as-is, so they are in every deploy.
