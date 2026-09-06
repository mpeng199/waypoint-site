# Previewing this branch

The site is not in the repo root. It is in this worktree:

    .claude/worktrees/website-accessibility-redesign-2b15ac

The repo root is still on the initial commit — it has an `about.html` from
August 3 and no `index.html` at all. A preview server started there shows a
version of the site from before the directory existed.

## Start it

    python3 serve.py 8753

or use the Browser pane's `waypoint` config, which `.claude/launch.json` now
points at this directory and at `serve.py`.

`serve.py` also binds IPv6 as well as IPv4: macOS Chrome tries `::1` before
`127.0.0.1`, and the stdlib server listens on IPv4 only.

**Do not use `python3 -m http.server`.** It sends no `Cache-Control`, so the
browser caches every stylesheet and script and decides for itself when to look
again. Navigating to `about.html#bills` will serve the copy in memory without
asking whether the file changed — you edit a page, reload the page you are on
and see the change, click a nav tab, and land on a version from before the
edit. `serve.py` is the same server with `no-store` on every response.

## If you already have the stale version cached

Open this once:

    http://localhost:8753/about.html?fresh=1

The query string means that URL has no cache entry, so the browser must go to
the network — and every HTML response from `serve.py` carries
`Clear-Site-Data: "cache"`, which throws away the whole origin's cache,
stale copies included. After that one load `no-store` keeps it clean.

Why anything is needed at all: a response cached earlier can be considered
fresh for *days*. The heuristic is a tenth of the file's age, and the stale
`about.html` was a month old, so Chrome will not even ask whether it changed.
It serves it from cache with no network request, so no header can reach it.
Something has to force one fetch.

## If the pages suddenly look old again

Check what the worktree is actually checked out to:

    git -C .claude/worktrees/website-accessibility-redesign-2b15ac rev-parse --abbrev-ref HEAD

It should say `claude/website-accessibility-redesign-2b15ac`. If another
session checks this worktree out to a different branch, the server keeps
serving the same directory and the files underneath it change — the preview
goes back in time with no error anywhere. **Uncommitted edits are lost in that
switch**, so commit before stepping away.

## What to open

| URL | what it is |
| --- | --- |
| `localhost:8753/index.html` | the directory — search, filters, 351 places |
| `localhost:8753/help-food.html` | one of seventeen category pages |
| `localhost:8753/help-es.html` | one of ten language pages |
| `localhost:8753/about.html` | the narrative half |
| `localhost:8753/privacy.html` | a sub-page hero, for the no-JS fix |

Narrow the window to 320–390px for the header, tap-target and jump fixes; most
of this month's work is only visible at phone widths. The print fix needs a
print preview.

## Two things that look like bugs and are not

**A blank dark-green frame on `about.html`.** The hero is scroll-driven and the
in-app Browser pane often reports `visibilityState: "hidden"`, which pauses
`requestAnimationFrame`, so the scenes never get a frame to paint. The page is
fine in a real browser tab. To capture it anyway: hide the other sections,
scroll to 0, call `window.__waypointTick()`, then screenshot.

**`--head-h` staying empty.** Same cause — it is published by a
`ResizeObserver`, and those callbacks do not fire in a hidden tab either.
