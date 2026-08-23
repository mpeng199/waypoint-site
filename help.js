/* help.js — narrows a directory that is already fully rendered.

   Everything on this page works before this file loads: 121 rows in 15
   labelled groups, every phone number a real tel: link, the need index a set
   of plain anchors. That is the contract. This script only ever *hides*
   things, so the worst case when it fails to load, fails to parse, or is
   blocked outright is that somebody sees the whole list — which is the thing
   they came for anyway.

   Hence the two `hidden` attributes in the markup: the filter chips and the
   "no matches" line are the only controls that genuinely need JavaScript, so
   they ship hidden and this file reveals them. Nobody is offered a control
   that cannot work. */
(function () {
  "use strict";

  var dir = document.getElementById("dir");
  if (!dir) return;

  var rows = Array.prototype.slice.call(dir.querySelectorAll(".r"));
  var groups = Array.prototype.slice.call(dir.querySelectorAll(".grp"));
  var needTiles = Array.prototype.slice.call(document.querySelectorAll(".need"));
  var q = document.getElementById("q");
  var filters = document.querySelector(".find__filters");
  var countEl = document.querySelector(".find__count");
  var noneEl = document.querySelector(".dir__none");
  var clearBtn = document.querySelector(".find__clear");
  var resetBtn = document.querySelector(".find__filters .reset");

  // Search text, built once. data-find carries only the vocabulary that is not
  // already on screen (tags, internal category); the rest comes from the row
  // itself, so "food stamps" finds SNAP and "eviction" finds a tenant hotline
  // without a synonym table to maintain.
  rows.forEach(function (r) {
    r._find = (r.textContent + " " + (r.dataset.find || ""))
      .toLowerCase().replace(/\s+/g, " ");
    r._key = r.dataset.key;
  });

  // Unique resources, not rendered rows: seven are filed under two needs, so
  // counting <li> elements would tell somebody there are 121 places when the
  // directory holds 114.
  var TOTAL = (function () {
    var seen = Object.create(null), n = 0;
    rows.forEach(function (r) { if (!seen[r._key]) { seen[r._key] = 1; n++; } });
    return n;
  })();

  var active = { boro: [], lang: [], flags: [] };
  var words = [];

  function matches(r) {
    for (var w = 0; w < words.length; w++) {
      if (r._find.indexOf(words[w]) === -1) return false;
    }
    return facetsOk(r);
  }

  function facetsOk(r) {
    for (var facet in active) {
      var want = active[facet];
      if (!want.length) continue;
      var has = (r.dataset[facet] || "").split(" ");
      // OR inside a facet, AND across facets: "Brooklyn or Queens" but
      // "Brooklyn AND Spanish". Anything else surprises people.
      var hit = want.some(function (v) { return has.indexOf(v) !== -1; });
      if (!hit) return false;
    }
    return true;
  }

  function apply() {
    var shown = Object.create(null);
    var n = 0;
    var loose = false;

    if (words.length > 1 && !rows.some(matches)) loose = true;

    rows.forEach(function (r) {
      var ok = loose ? (loosened(r) && facetsOk(r)) : matches(r);
      r.hidden = !ok;
      if (ok && !shown[r._key]) { shown[r._key] = 1; n++; }
    });

    // A group heading over nothing reads as "we have none of this", when the
    // truth is the filter excluded them. Hide the whole section instead.
    var perNeed = Object.create(null);
    groups.forEach(function (g) {
      var live = g.querySelectorAll(".r:not([hidden])").length;
      g.hidden = live === 0;
      perNeed[g.dataset.need] = live;
    });

    // The tile counts are a promise. Leaving them at their full-list numbers
    // while a filter is on sends somebody to a group that is now empty.
    needTiles.forEach(function (t) {
      var c = perNeed[t.dataset.need] || 0;
      var el = t.querySelector(".need__n");
      if (el) el.textContent = c + (c === 1 ? " place" : " places");
      t.parentNode.hidden = c === 0;
    });

    var narrowed = !!(words.length || active.boro.length || active.lang.length || active.flags.length);
    countEl.textContent = !narrowed
      ? TOTAL + " places to get help"
      : n === 0
        ? "Nothing matched"
        : loose
          ? "No exact match. Showing " + n + " places that are close."
          : "Showing " + n + " of " + TOTAL + " places";
    if (noneEl) noneEl.hidden = n !== 0;
    if (clearBtn) clearBtn.hidden = !words.length;
    if (resetBtn) resetBtn.hidden = !narrowed;
  }

  // ---- search. Filtering runs straight off the keystroke: it is a
  // hidden-attribute pass over 121 rows against a prebuilt string, ~1ms on a
  // slow phone. Coalescing that into a frame would be debouncing something
  // cheaper than the debounce, and rAF does not fire at all in a background
  // tab, which is what made this untestable.
  /* Turning what somebody typed into terms to match on.
     Three passes, because three different real queries each broke a simpler
     version of this:

     1. Phrase first. "green card" as two independent words matched 29 rows —
        every row containing "card" (MetroCard, referral cards) that also
        happened to contain "green". When the whole phrase appears somewhere,
        that is what they meant, so use it alone.
     2. Otherwise every word must appear, in any order, so "free food
        brooklyn" and "cheap dentist brooklyn" both work.
     3. But drop words that appear in no row at all. "cant pay my con ed bill"
        returned nothing because of "my" and "cant". Ignoring a word that
        matches nothing can only widen the result, and a widened result is
        always better than the blank page somebody gets otherwise. If no word
        survives, the query really is unknown and the empty state is honest. */
  var STOP = (" i me my mine we our you your a an the is am are be been it its this that " +
    "to of for and or in on at with from about need needs help please do does did " +
    "how where what who can cant cannot get got some any my im ive have has had " +
    "there here now they them he she his her not no ").split(" ");

  function termsFor(raw) {
    var text = raw.toLowerCase().trim().replace(/[’']/g, "");
    if (!text) return [];
    if (rows.some(function (r) { return r._find.indexOf(text) !== -1; })) return [text];

    var all = text.split(/[^a-z0-9\-]+/).filter(Boolean);
    var content = all.filter(function (w) { return STOP.indexOf(w) === -1; });
    if (!content.length) content = all;
    var useful = content.filter(function (w) {
      return rows.some(function (r) { return r._find.indexOf(w) !== -1; });
    });
    return useful.length ? useful : content;
  }

  /* Last resort before a blank page.
     "cant pay my con ed bill" leaves [pay, con, ed, bill] after the stop
     words, and no single row contains all four. Requiring every word is right
     for two or three keywords and wrong for a sentence, so when the strict
     pass empties the page, widen to "any of these words" rather than telling
     somebody who just described their problem that we have nothing. The
     count line says which pass they are looking at, so the result is never
     presented as more precise than it is. */
  function loosened(r) {
    for (var w = 0; w < words.length; w++) {
      if (r._find.indexOf(words[w]) !== -1) return true;
    }
    return false;
  }

  function onType() {
    words = termsFor(q.value);
    apply();
  }
  if (q) {
    q.addEventListener("input", onType);
    // Enter in a lone search field submits nothing here; stop the page jumping.
    q.addEventListener("keydown", function (e) {
      if (e.key === "Enter") e.preventDefault();
      if (e.key === "Escape") { q.value = ""; onType(); }
    });
  }

  // ---- chips
  if (filters) filters.hidden = false;
  document.addEventListener("click", function (e) {
    var chip = e.target.closest ? e.target.closest(".chip") : null;
    if (chip) {
      var facet = chip.dataset.f, val = chip.dataset.v;
      var list = active[facet];
      var i = list.indexOf(val);
      if (i === -1) list.push(val); else list.splice(i, 1);
      chip.setAttribute("aria-pressed", i === -1 ? "true" : "false");
      apply();
      return;
    }
    if (e.target.closest && e.target.closest(".reset")) {
      reset();
      return;
    }
    if (e.target === clearBtn) { q.value = ""; words = []; apply(); q.focus(); }

    var go = e.target.closest && e.target.closest(".langnote__go");
    if (go) useLanguage(go.dataset.lang);
  });

  /* The language panels open on :target with no help from here. What this
     adds is the follow-through: somebody who opened the Spanish panel and
     tapped "ver los lugares que atienden en español" means the list below
     should now be the Spanish-speaking places, and the matching chip should
     show as pressed so they can see why the list got shorter — and turn it
     off again. */
  function useLanguage(key) {
    if (active.lang.indexOf(key) === -1) active.lang.push(key);
    var chip = document.querySelector('.chip[data-f="lang"][data-v="' + key + '"]');
    if (chip) chip.setAttribute("aria-pressed", "true");
    apply();
  }

  function reset() {
    words = [];
    if (q) q.value = "";
    active = { boro: [], lang: [], flags: [] };
    Array.prototype.forEach.call(
      document.querySelectorAll('.chip[aria-pressed="true"]'),
      function (c) { c.setAttribute("aria-pressed", "false"); });
    apply();
    var needs = document.getElementById("needs");
    if (needs) needs.scrollIntoView({ block: "start" });
  }

  apply();
})();
