# Previewing this branch

The site is not in the repo root. It is in this worktree:

    .claude/worktrees/website-accessibility-redesign-2b15ac

The repo root is still on the initial commit — it has an `index.html` from
August 3 and no `help.html` at all. A preview server started there shows a
version of the site from before the directory existed.

## Start it

    python3 serve.py 8753

or use the Browser pane's `waypoint` config, which `.claude/launch.json` now
points at this directory and at `serve.py`.

**Do not use `python3 -m http.server`.** It sends no `Cache-Control`, so the
browser caches every stylesheet and script and decides for itself when to look
again. Navigating to `index.html#bills` will serve the copy in memory without
asking whether the file changed — you edit a page, reload the page you are on
and see the change, click a nav tab, and land on a version from before the
edit. `serve.py` is the same server with `no-store` on every response.

## If you already have the stale version cached

One hard reload clears it — **Cmd+Shift+R** on macOS. After that `no-store`
keeps it from happening again.

## What to open

| URL | what it is |
| --- | --- |
| `localhost:8753/help.html` | the directory — search, filters, 351 places |
| `localhost:8753/help-food.html` | one of seventeen category pages |
| `localhost:8753/help-es.html` | one of ten language pages |
| `localhost:8753/index.html` | the narrative half |
| `localhost:8753/privacy.html` | a sub-page hero, for the no-JS fix |

Narrow the window to 320–390px for the header, tap-target and jump fixes; most
of this month's work is only visible at phone widths. The print fix needs a
print preview.

## Two things that look like bugs and are not

**A blank dark-green frame on `index.html`.** The hero is scroll-driven and the
in-app Browser pane often reports `visibilityState: "hidden"`, which pauses
`requestAnimationFrame`, so the scenes never get a frame to paint. The page is
fine in a real browser tab. To capture it anyway: hide the other sections,
scroll to 0, call `window.__waypointTick()`, then screenshot.

**`--head-h` staying empty.** Same cause — it is published by a
`ResizeObserver`, and those callbacks do not fire in a hidden tab either.
