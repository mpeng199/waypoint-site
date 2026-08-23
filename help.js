/* help.js — narrows a directory that is already fully rendered.

   Everything on this page works before this file loads: every resource, in
   labelled groups, every phone number a real tel: link, the need index a set
   of plain anchors. That is the contract. This script only ever *hides*
   things, so the worst case when it fails to load, fails to parse, or is
   blocked outright is that somebody sees the whole list — which is the thing
   they came for anyway.

   Hence the `hidden` attributes in the markup: the search-and-filter block,
   the "no matches" line and the print button are the controls that genuinely
   need JavaScript, so they ship hidden and this file reveals them, with a
   <noscript> beside them saying where they went. Nobody is offered a control
   that cannot work. check.py enforces both halves. */
(function () {
  "use strict";

  var dir = document.getElementById("dir");
  if (!dir) return;

  var rows = Array.prototype.slice.call(dir.querySelectorAll(".r"));
  var groups = Array.prototype.slice.call(dir.querySelectorAll(".grp"));
  var needTiles = Array.prototype.slice.call(document.querySelectorAll(".need"));
  var q = document.getElementById("q");
  var countEl = document.querySelector(".find__count");
  var noneEl = document.querySelector(".dir__none");
  var clearBtn = document.querySelector(".find__clear");
  var resetBtn = document.querySelector(".find__filters .reset");

  // Search text, built once from the row's CONTENT — deliberately not its
  // textContent, which also carries the interface. Every row has a button
  // reading "Call" and one reading "Open website", and a disclosure reading
  // "More about this", so searching for any of those words matched all 125
  // rows; so did "checked" and "2026", from the verification line. Words the
  // page says about itself are not facts about the resource.
  //
  // data-find adds what is NOT on screen: the internal tags and category, and
  // the plain-English phrases SYNONYMS attaches — which is how "food stamps"
  // finds SNAP and "kicked out" finds an eviction hotline.
  var CONTENT = [".r__name", ".r__kind", ".r__what", ".r__badges",
                 ".r__facts dl", ".r__note"];
  rows.forEach(function (r) {
    var parts = [];
    CONTENT.forEach(function (sel) {
      var el = r.querySelector(sel);
      if (el) parts.push(el.textContent);
    });
    r._find = (parts.join(" ") + " " + (r.dataset.find || ""))
      .toLowerCase().replace(/\s+/g, " ");
    r._key = r.dataset.key;
  });

  // Unique resources, not rendered rows: a few are filed under two needs, so
  // counting <li> elements would overstate the directory by exactly the number
  // of things we cross-filed.
  var TOTAL = (function () {
    var seen = Object.create(null), n = 0;
    rows.forEach(function (r) { if (!seen[r._key]) { seen[r._key] = 1; n++; } });
    return n;
  })();

  var active = { boro: [], lang: [], flags: [] };
  var words = [];

  function matches(r) {
    for (var w = 0; w < words.length; w++) {
      if (!hasWord(r._find, words[w])) return false;
    }
    return facetsOk(r);
  }

  /* Is this row a closer match than the generic ones that also survived?
     Two facets have the same shape of problem: most rows answer them
     generically. 97 of the rows serve every borough, and most record their
     languages as "Multiple". Filtering by Staten Island or by Bengali is
     therefore honest but barely narrows anything — so the rows that answer
     SPECIFICALLY lead their group, and the generic ones follow.

     Nothing is hidden either way. "They are in your borough" and "they cover
     the whole city" are both useful; they are just not the same answer. */
  function isCloserMatch(r) {
    if (active.lang.length) {
      var langs = (r.dataset.lang || "").split(" ");
      if (active.lang.some(function (v) { return langs.indexOf(v) !== -1; })) return true;
    }
    if (active.boro.length) {
      var boros = (r.dataset.boro || "").split(" ");
      // A citywide row carries every borough plus the "citywide" marker, so
      // the absence of that marker is what makes a row local.
      if (boros.indexOf("citywide") === -1 &&
          active.boro.some(function (v) { return boros.indexOf(v) !== -1; })) return true;
    }
    return false;
  }

  function facetsOk(r) {
    for (var facet in active) {
      var want = active[facet];
      if (!want.length) continue;
      var has = (r.dataset[facet] || "").split(" ");
      // OR inside a facet, AND across facets: "Brooklyn or Queens" but
      // "Brooklyn AND Spanish". Anything else surprises people.
      // A language chip also matches a row that works in many languages
      // through an interpreter — see VAGUE_LANG in build_help.py. Without
      // this, filtering by a language hides most of the directory.
      var hit = want.some(function (v) {
        return has.indexOf(v) !== -1 ||
               (facet === "lang" && has.indexOf("many") !== -1);
      });
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
      r.style.order = isCloserMatch(r) ? "-1" : "";
    });

    // A group heading over nothing reads as "we have none of this", when the
    // truth is the filter excluded them. Hide the whole section instead.
    //
    // And while a search is running, order the surviving groups by how much
    // of each one matched. Unsearched, the fixed order is deliberate — the
    // things that get people hurt first, then the rest. Under a search that
    // order is just wrong: "i want to die" put a sexual assault hotline above
    // 988 because "safety" is printed before "crisis", and "job training" led
    // with a health clinic. Most-matched first is what somebody who typed
    // something specific is asking for.
    var perNeed = Object.create(null);
    groups.forEach(function (g) {
      var live = g.querySelectorAll(".r:not([hidden])").length;
      g.hidden = live === 0;
      perNeed[g.dataset.need] = live;
      g.style.order = words.length ? String(-live) : "";
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

  // ---- search. Filtering runs straight off the keystroke: a hidden-attribute
  // pass over every row against a prebuilt string, ~1ms on a slow phone.
  // Coalescing that into a frame would be debouncing something cheaper than
  // the debounce, and rAF does not fire at all in a background tab, which is
  // what made it untestable.
  /* Turning what somebody typed into terms to match on.

     Every word must appear, in any order, so "free food brooklyn" and "cheap
     dentist brooklyn" both work. Two rules earned by testing real queries:

     1. Words that appear in no row at all are dropped. "cant pay my con ed
        bill" returned nothing because of "my" and "cant". Ignoring a word
        that matches nothing can only widen the result, and a widened result
        beats the blank page somebody gets otherwise. If no word survives, the
        query really is unknown and the empty state is honest.
     2. Numbers shorter than three digits are dropped. "section 8" matched 71
        rows because "8" appears in every street address on the page. 311 and
        988 are real searches; 8 is not.

     There used to be a phrase-first pass here — if the whole query appeared
     verbatim in any row, only those rows matched. It was covering for
     substring matching, and it actively hid better answers: "homeless
     shelter" appears word-for-word in three descriptions, so it returned
     those three and never reached the city's actual shelter intake, which
     matches both words separately. Same for "job training" hiding
     Workforce1. Matching on word starts removed the reason it existed. */
  var STOP = (" i me my mine we our you your a an the is am are be been it its this that " +
    "to of for and or in on at with from about need needs help please do does did " +
    "how where what who can cant cannot get got some any my im ive have has had " +
    "there here now they them he she his her not no ").split(" ");

  function termsFor(raw) {
    var text = raw.toLowerCase().trim().replace(/[\u2019']/g, "");
    if (!text) return [];
    var all = text.split(/[^a-z0-9\-]+/).filter(Boolean);
    var content = all.filter(function (w) {
      if (STOP.indexOf(w) !== -1) return false;
      if (/^\d+$/.test(w) && w.length < 3) return false;
      // A lone letter matches the start of a quarter of the page. "pre k"
      // spent its "k" on every word beginning with one.
      if (w.length < 2) return false;
      return true;
    });
    if (!content.length) content = all;
    var useful = content.filter(function (w) {
      return rows.some(function (r) { return hasWord(r._find, w); });
    });
    return useful.length ? useful : content;
  }

  /* Match at word starts, not anywhere in the string.
     Plain substring matching made "ice detained" return 58 rows, because
     "ice" is inside serv*ice*, off*ice*, just*ice* and pr*ice*s — so somebody
     whose relative had just been detained got a food pantry and a DV hotline
     above the immigration lawyers. Anchoring to a word start keeps the useful
     looseness (a search for "dent" still finds "dental" and "dentist") and
     drops the noise. */
  var reCache = {};
  function hasWord(hay, word) {
    var re = reCache[word];
    if (!re) {
      var esc = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      re = reCache[word] = new RegExp("\\b" + esc);
    }
    return re.test(hay);
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

  // ---- reveal the controls that need this script to exist at all
  var findBlock = document.querySelector(".find");
  if (findBlock) findBlock.hidden = false;
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

  /* ---- printing.
     Whatever is on screen is what prints: the rows the filter hid carry the
     hidden attribute, so a sheet printed after narrowing to "I need food" in
     Brooklyn is exactly those places and nothing else. That is the leave-
     behind students actually need, and it costs no separate print view.

     The one thing screen and paper disagree about is the details disclosure.
     On screen "More about this" is closed, because a row that states its
     hours, address and languages up front is a row nobody scans. On paper
     those are the most useful lines on the sheet and there is nothing to tap,
     so every disclosure is opened for the print and put back afterwards.
     beforeprint covers Ctrl+P as well as the button. */
  var reopened = [];
  window.addEventListener("beforeprint", function () {
    reopened = [];
    Array.prototype.forEach.call(document.querySelectorAll(".r__more"), function (d) {
      if (!d.open) { d.open = true; reopened.push(d); }
    });
  });
  window.addEventListener("afterprint", function () {
    reopened.forEach(function (d) { d.open = false; });
    reopened = [];
  });

  var printBtn = document.querySelector(".printbtn");
  if (printBtn) {
    printBtn.hidden = false;
    printBtn.addEventListener("click", function () { window.print(); });
  }

  apply();
})();
