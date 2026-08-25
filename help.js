/* help.js — narrows a directory that is already fully rendered.

   Everything on these pages works before this file loads: every resource on a
   category page, in labelled groups, every phone number a real tel: link, the
   cluster index a set of plain anchors. That is the contract. On a category
   page this script only ever *hides* things, so the worst case when it fails
   to load, fails to parse, or is blocked outright is that somebody sees the
   whole list — which is the thing they came for anyway.

   Two pages, two modes:

   - CATEGORY (help-food.html and friends). Every resource for that need is in
     the markup. Filtering hides rows. Nothing is ever built here.

   - FRONT (help.html). The front page carries fifteen clusters of three
     examples, not the whole directory — that split is the entire reason the
     page is 117 KB instead of a quarter of a megabyte. So search there needs
     its own copy of the facts, which ships as <script type="application/json"
     id="ix"> at the bottom of the document, and results are built from it
     using exactly the same .r markup a real row uses. There is one resource
     card design on this site, not two.

   Hence the `hidden` attributes in the markup: the search-and-filter block,
   the "no matches" line and the print button are the controls that genuinely
   need JavaScript, so they ship hidden and this file reveals them, with a
   <noscript> beside them saying where they went. Nobody is offered a control
   that cannot work. check.py enforces both halves. */
(function () {
  "use strict";

  var ixEl = document.getElementById("ix");
  var dir = document.getElementById("dir");
  if (!ixEl && !dir) return;

  var q = document.getElementById("q");
  var countEl = document.querySelector(".find__count");
  var clearBtn = document.querySelector(".find__clear");
  var resetBtn = document.querySelector(".find__filters .reset");

  var active = { boro: [], lang: [], flags: [] };
  var words = [];

  /* ---------------------------------------------------------------- shared */

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

  function termsFor(raw, corpus) {
    var text = raw.toLowerCase().trim().replace(/[’']/g, "");
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
      return corpus.some(function (hay) { return hasWord(hay, w); });
    });
    return useful.length ? useful : content;
  }

  /* OR inside a facet, AND across facets: "Brooklyn or Queens" but
     "Brooklyn AND Spanish". Anything else surprises people.
     A language chip also matches a row that works in many languages through
     an interpreter — see VAGUE_LANG in build_help.py. Without this, filtering
     by a language hides most of the directory. */
  function facetsOk(get) {
    for (var facet in active) {
      var want = active[facet];
      if (!want.length) continue;
      var has = (get(facet) || "").split(" ");
      var hit = want.some(function (v) {
        return has.indexOf(v) !== -1 ||
               (facet === "lang" && has.indexOf("many") !== -1);
      });
      if (!hit) return false;
    }
    return true;
  }

  /* Is this row a closer match than the generic ones that also survived?
     Two facets have the same shape of problem: most rows answer them
     generically. 97 of the rows serve every borough, and most record their
     languages as "Multiple". Filtering by Staten Island or by Bengali is
     therefore honest but barely narrows anything — so the rows that answer
     SPECIFICALLY lead their group, and the generic ones follow.

     Nothing is hidden either way. "They are in your borough" and "they cover
     the whole city" are both useful; they are just not the same answer. */
  function isCloserMatch(get) {
    if (active.lang.length) {
      var langs = (get("lang") || "").split(" ");
      if (active.lang.some(function (v) { return langs.indexOf(v) !== -1; })) return true;
    }
    if (active.boro.length) {
      var boros = (get("boro") || "").split(" ");
      // A citywide row carries every borough plus the "citywide" marker, so
      // the absence of that marker is what makes a row local.
      if (boros.indexOf("citywide") === -1 &&
          active.boro.some(function (v) { return boros.indexOf(v) !== -1; })) return true;
    }
    return false;
  }

  function narrowed() {
    return !!(words.length || active.boro.length || active.lang.length ||
              active.flags.length);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ------------------------------------------------------------- the modes */
  var mode = ixEl ? front(JSON.parse(ixEl.textContent)) : category();

  /* --------------------------------------------------------------- FRONT */
  function front(ix) {
    var items = ix.rows;
    var clusters = document.querySelector(".clusters");
    var jump = document.querySelector(".jump");
    var results = document.getElementById("results");
    var resultRows = document.getElementById("resultRows");
    var resultsH = document.querySelector(".results__h");
    var noneEl = results.querySelector(".dir__none");
    var TOTAL = items.length;

    items.forEach(function (it) {
      it._find = (it.n + " " + it.k + " " + it.d + " " + it.s)
        .toLowerCase().replace(/\s+/g, " ");
    });
    var corpus = items.map(function (it) { return it._find; });

    var BADGES = [["free", "Free"], ["open-247", "Open 24/7"],
                  ["no-status", "No immigration status asked"]];

    /* Built here, but the same markup build_help.py writes for a real row, so
       every rule in help.css applies unchanged and there is one card design
       to maintain rather than two that drift. What a built row does NOT carry
       is the fact list — hours, address, languages are not in the index, on
       purpose, because they are what makes the index large. The last line is
       the way to the full entry. */
    function rowHTML(it) {
      var a = [];
      a.push('<li class="r" data-key="' + esc(it.i) + '">');
      a.push('<div class="r__head"><h3 class="r__name">' + esc(it.n) + "</h3>");
      if (it.k) a.push('<p class="r__kind">' + esc(it.k) + "</p>");
      a.push("</div>");
      a.push('<p class="r__what">' + esc(it.d) + "</p>");
      var flags = (it.f || "").split(" ");
      var bdg = BADGES.filter(function (b) { return flags.indexOf(b[0]) !== -1; })
        .map(function (b) { return '<span class="bdg bdg--' + b[0] + '">' + b[1] + "</span>"; });
      if (bdg.length) a.push('<p class="r__badges">' + bdg.join("") + "</p>");
      a.push('<div class="r__do">');
      if (it.c === "call") {
        a.push('<a class="call" href="tel:' + esc(it.h) + '">' +
          '<svg class="ico" aria-hidden="true"><use href="#i-phone"/></svg>' +
          "<span><small>Call</small>" + esc(it.p) + "</span></a>");
      } else if (it.c === "text") {
        a.push('<a class="call call--text" href="' + esc(it.h) + '">' +
          '<svg class="ico" aria-hidden="true"><use href="#i-text"/></svg>' +
          "<span><small>Text</small>" + esc(it.p) + "</span></a>");
      }
      if (it.w) {
        a.push('<a class="visit" href="' + esc(it.w) + '" rel="noopener">' +
          '<span class="visit__t">Open website</span>' +
          '<span class="arr" aria-hidden="true">&#8599;</span></a>');
      }
      a.push("</div>");
      a.push('<p class="r__where"><a href="' + esc(ix.page[it.g]) + "#r-" +
        esc(it.g) + "-" + esc(it.i) + '">Hours, address and more &mdash; under &ldquo;' +
        esc(ix.needs[it.g]) + '&rdquo;</a></p>');
      a.push("</li>");
      return a.join("");
    }

    function apply() {
      if (!narrowed()) {
        results.hidden = true;
        resultRows.innerHTML = "";
        clusters.hidden = false;
        countEl.textContent = TOTAL + " places to get help";
        if (clearBtn) clearBtn.hidden = true;
        if (resetBtn) resetBtn.hidden = true;
        return;
      }
      var hits = items.filter(function (it) {
        for (var w = 0; w < words.length; w++) {
          if (!hasWord(it._find, words[w])) return false;
        }
        return facetsOk(function (f) {
          return f === "boro" ? it.b : f === "lang" ? it.l : it.f;
        });
      });
      // Rows that answer the borough or the language *specifically* lead.
      hits.sort(function (a, b) {
        var A = isCloserMatch(function (f) {
          return f === "boro" ? a.b : f === "lang" ? a.l : a.f; }) ? 0 : 1;
        var B = isCloserMatch(function (f) {
          return f === "boro" ? b.b : f === "lang" ? b.l : b.f; }) ? 0 : 1;
        return A - B;
      });

      clusters.hidden = true;
      results.hidden = false;
      resultRows.innerHTML = hits.map(rowHTML).join("");
      resultsH.textContent = hits.length === 0
        ? "Nothing matched that"
        : hits.length + (hits.length === 1 ? " place matches" : " places match");
      noneEl.hidden = hits.length !== 0;
      countEl.textContent = hits.length === 0
        ? "Nothing matched"
        : "Showing " + hits.length + " of " + TOTAL + " places";
      if (clearBtn) clearBtn.hidden = !words.length;
      if (resetBtn) resetBtn.hidden = false;
    }

    return {
      apply: apply,
      terms: function (raw) { return termsFor(raw, corpus); },
      home: function () { return clusters; },
      jump: jump,
      total: TOTAL,
    };
  }

  /* ------------------------------------------------------------ CATEGORY */
  function category() {
    var rows = Array.prototype.slice.call(dir.querySelectorAll(".r"));
    var groups = Array.prototype.slice.call(dir.querySelectorAll(".grp"));
    var railLinks = Array.prototype.slice.call(document.querySelectorAll(".rail__nav a"));
    var noneEl = document.querySelector(".dir .dir__none");

    // Search text, built once from the row's CONTENT — deliberately not its
    // textContent, which also carries the interface. Every row has a button
    // reading "Call" and one reading "Open website", and a disclosure reading
    // "More about this", so searching for any of those words matched every
    // row; so did "checked" and "2026", from the verification line. Words the
    // page says about itself are not facts about the resource.
    //
    // data-find adds what is NOT on screen: the internal tags and category,
    // and the plain-English phrases SYNONYMS attaches — which is how "food
    // stamps" finds SNAP and "kicked out" finds an eviction hotline.
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

    // Unique resources, not rendered rows: a resource can appear both in its
    // own bucket and under "Also worth calling", so counting <li> elements
    // would overstate the page by exactly the number we cross-filed.
    var TOTAL = (function () {
      var seen = Object.create(null), n = 0;
      rows.forEach(function (r) { if (!seen[r._key]) { seen[r._key] = 1; n++; } });
      return n;
    })();

    var corpus = rows.map(function (r) { return r._find; });

    function apply() {
      var shown = Object.create(null);
      var n = 0;
      rows.forEach(function (r) {
        var ok = true;
        for (var w = 0; w < words.length; w++) {
          if (!hasWord(r._find, words[w])) { ok = false; break; }
        }
        if (ok) ok = facetsOk(function (f) { return r.dataset[f]; });
        r.hidden = !ok;
        if (ok && !shown[r._key]) { shown[r._key] = 1; n++; }
        r.style.order = isCloserMatch(function (f) { return r.dataset[f]; }) ? "-1" : "";
      });

      // A group heading over nothing reads as "we have none of this", when the
      // truth is the filter excluded them. Hide the whole section instead —
      // and take its rail entry with it, because a rail link to a hidden
      // section is a link to nowhere.
      var perGroup = Object.create(null);
      groups.forEach(function (g) {
        var live = g.querySelectorAll(".r:not([hidden])").length;
        g.hidden = live === 0;
        perGroup["#" + g.id] = live;
        g.style.order = words.length ? String(-live) : "";
      });
      railLinks.forEach(function (a) {
        var live = perGroup[a.getAttribute("href")];
        if (live === undefined) return;
        var el = a.querySelector(".rail__n");
        if (el) el.textContent = live;
        a.parentNode.hidden = live === 0;
      });

      countEl.textContent = !narrowed()
        ? TOTAL + (TOTAL === 1 ? " place on this page" : " places on this page")
        : n === 0 ? "Nothing matched"
                  : "Showing " + n + " of " + TOTAL;
      if (noneEl) noneEl.hidden = n !== 0;
      if (clearBtn) clearBtn.hidden = !words.length;
      if (resetBtn) resetBtn.hidden = !narrowed();
    }

    return {
      apply: apply,
      terms: function (raw) { return termsFor(raw, corpus); },
      home: function () { return document.querySelector(".cat__main"); },
      jump: null,
      total: TOTAL,
    };
  }

  /* -------------------------------------------------------------- wiring */
  function onType() {
    words = mode.terms(q.value);
    mode.apply();
  }

  if (q) {
    // Filtering runs straight off the keystroke: a pass over a prebuilt
    // string, ~1ms on a slow phone. Coalescing that into a frame would be
    // debouncing something cheaper than the debounce, and rAF does not fire
    // at all in a background tab, which is what made it untestable.
    q.addEventListener("input", onType);
    // Enter in a lone search field submits nothing here; stop the page jumping.
    q.addEventListener("keydown", function (e) {
      if (e.key === "Enter") e.preventDefault();
      if (e.key === "Escape") { q.value = ""; onType(); }
    });
  }

  var findBlock = document.querySelector(".find");
  if (findBlock) findBlock.hidden = false;

  /* The filters are a refinement, not the way in. Open where the space is
     free; closed on a phone, where nineteen chips is three screens between
     somebody arriving and the first phone number. Set once, from here rather
     than from the markup, because the markup has to be the same on every
     device and this is the one thing that should not be. */
  /* Open is the safe default: it hides nothing. Only a positive signal that
     the viewport is narrow closes it — asking a media query and trusting the
     answer fails in the wrong direction when layout has not happened yet
     (innerWidth is 0 in a backgrounded tab, every media query is false, and a
     desktop page ships with its filters shut for no visible reason).

     It re-syncs on rotation, which is a thing phones do mid-task, and stops
     the moment the reader touches the control themselves: after that the
     state is theirs and the viewport does not get a vote. */
  var filters = document.querySelector(".find__filters");
  var WIDE = "(min-width: 900px)";
  var mq = window.matchMedia ? window.matchMedia(WIDE) : null;
  var userSet = false;

  var syncing = false;
  function syncFilters() {
    if (!filters || userSet) return;
    var w = window.innerWidth || document.documentElement.clientWidth || 0;
    // `toggle` fires for our own writes too, and marking those as the
    // reader's choice would make the very first sync the last one.
    syncing = true;
    filters.open = !w || w >= 900;   // width unknown: hide nothing
    syncing = false;
  }
  if (filters) {
    syncFilters();
    filters.addEventListener("toggle", function () {
      if (!syncing) userSet = true;
    });
    if (mq && mq.addEventListener) mq.addEventListener("change", syncFilters);
    else if (mq && mq.addListener) mq.addListener(syncFilters);
  }

  /* Opening a filter from a language panel is useless if the filter is shut. */
  function revealFilters() { if (filters && !filters.open) filters.open = true; }

  document.addEventListener("click", function (e) {
    if (!e.target.closest) return;
    var chip = e.target.closest(".chip");
    if (chip) {
      var facet = chip.dataset.f, val = chip.dataset.v;
      var list = active[facet];
      var i = list.indexOf(val);
      if (i === -1) list.push(val); else list.splice(i, 1);
      chip.setAttribute("aria-pressed", i === -1 ? "true" : "false");
      mode.apply();
      return;
    }
    if (e.target.closest(".reset")) { reset(); return; }
    if (e.target === clearBtn) { q.value = ""; words = []; mode.apply(); q.focus(); }

    var go = e.target.closest(".langnote__go");
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
    revealFilters();
    mode.apply();
  }

  function reset() {
    words = [];
    if (q) q.value = "";
    active = { boro: [], lang: [], flags: [] };
    Array.prototype.forEach.call(
      document.querySelectorAll('.chip[aria-pressed="true"]'),
      function (c) { c.setAttribute("aria-pressed", "false"); });
    mode.apply();
    var home = mode.home();
    if (home) home.scrollIntoView({ block: "start" });
  }

  /* ---- printing.
     Whatever is on screen is what prints: the rows the filter hid carry the
     hidden attribute, so a sheet printed after narrowing a category page to
     Brooklyn is exactly those places and nothing else. That is the leave-
     behind students actually need, and it costs no separate print view. The
     front page prints its fifteen clusters with three numbers each, which is
     the one-or-two-sheet version somebody can hand across a table.

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

  mode.apply();
})();
