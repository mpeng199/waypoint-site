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
  var dropped = [];

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
  /* Unicode-aware where the browser allows it, and the old ASCII class where
     it does not — a six-year-old Android may predate \p{L} in regexes, and
     falling back to the previous behaviour is better than throwing. */
  var SPLIT = (function () {
    try { return new RegExp("[^\\p{L}\\p{N}\\-]+", "u"); }
    catch (e) { return /[^a-z0-9\-]+/; }
  })();
  var ASCII = /^[\x00-\x7F]*$/;

  var reCache = {};
  function starts(hay, word) {
    // \b is defined by ASCII word characters, so "\bкризис" can never match
    // and "\b食物" is meaningless. Anything outside ASCII matches plainly.
    if (!ASCII.test(word)) return hay.indexOf(word) !== -1;
    var re = reCache[word];
    if (!re) {
      var esc = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      re = reCache[word] = new RegExp("\\b" + esc);
    }
    return re.test(hay);
  }

  /* Prefix matching only works one way. "dent" finds "dentist" because the
     query is a prefix of the word on the page — but "abused" finds nothing,
     because the page says "abuse", and "my daughter is being abused" is not a
     query that may return a housing lottery.

     So the query word is also tried with a common English ending removed.
     Deliberately crude: no dictionary, no real stemmer, four suffixes, and
     only when at least four letters survive — enough for abus(ed), evict(ed),
     deni(ed), wage(s), meal(s), class(es), and short of anything that starts
     matching words it should not. */
  var stemCache = {};
  function stem(word) {
    if (word in stemCache) return stemCache[word];
    if (!ASCII.test(word)) return (stemCache[word] = word);
    var out = word;
    var cut = [["ing", 3], ["ies", 3], ["ed", 2], ["es", 2], ["s", 1], ["ly", 2]];
    for (var i = 0; i < cut.length; i++) {
      var suf = cut[i][0];
      if (word.length - cut[i][1] >= 4 &&
          word.slice(-suf.length) === suf) {
        out = word.slice(0, -suf.length);
        break;
      }
    }
    return (stemCache[word] = out);
  }

  function hasWord(hay, word) {
    if (starts(hay, word)) return true;
    var st = stem(word);
    return st !== word && starts(hay, st);
  }

  function termsFor(raw, corpus) {
    var text = raw.toLowerCase().trim().replace(/[’']/g, "");
    if (!text) return [];
    // Split on anything that is not a letter or a number IN ANY SCRIPT. The
    // old class was [^a-z0-9-], which silently deleted every Cyrillic,
    // Arabic, Bengali, Korean and Chinese character before matching — so the
    // ten languages the page offers could be read and not searched.
    var all = text.split(SPLIT).filter(Boolean);
    var content = all.filter(function (w) {
      if (STOP.indexOf(w) !== -1) return false;
      if (/^\d+$/.test(w) && w.length < 3) return false;
      // A lone Latin letter matches the start of a quarter of the page — "pre
      // k" spent its "k" on every word beginning with one. A lone CJK
      // character is a whole word.
      if (w.length < 2 && ASCII.test(w)) return false;
      return true;
    });
    if (!content.length) content = all;
    var useful = content.filter(function (w) {
      return corpus.some(function (hay) { return hasWord(hay, w); });
    });
    // Say which words went nowhere. Dropping a word that matches nothing can
    // only widen the result and beats the blank page — but doing it silently
    // is how "free wifi" returned a hundred and seventy-four places that are
    // free and none that have wifi, with no hint that half the question had
    // been thrown away.
    dropped = useful.length ? content.filter(function (w) {
      return useful.indexOf(w) === -1;
    }) : [];
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

  /* How well a row answers the query, and whether it answers it at all.

     Two things this has to get right, both learned from watching real
     phrasings fail:

     1. EVERY word matching is the ideal, and it is often too much to ask.
        "i cant pay my hospital bill" returned nothing, because no single row
        contains "pay" and "hospital" and "bill"; so did "landlord wont fix
        anything" and "my benefits were cut off". A blank page is the worst
        possible answer for somebody who has just typed a sentence about their
        life. So: all-words if anything matches, otherwise most-words-matched.
        Nothing is invented — every row shown really does match part of what
        they typed — and the count says plainly that it is not exact.

     2. WHERE the word matched decides the order. "i need food today" matched
        forty-two rows and opened with a benefits screener, because "food"
        appears in its description. A word in the resource's name is a much
        stronger signal than the same word in a paragraph about it, and a page
        that opens with the wrong three answers has failed even when the right
        one is eleventh. */
  /* Four fields, four weights. What a resource is CALLED is the strongest
     signal, what it calls itself next, the alternative words we attached to
     it next, and a paragraph about it weakest.

     The alias field earns its own weight rather than sharing the subcategory's
     because it is deliberately generous — every row tagged "disability"
     carries the words "blind", "deaf" and "wheelchair" so that those searches
     find something. Weighted equally, a meal-delivery service outranked
     Lighthouse Guild on the query "im blind". Explicit beats attached. */
  var W_NAME = 6, W_KIND = 4, W_TAG = 3, W_ALIAS = 2, W_BODY = 1;
  /* A whole word beats a word start. Prefix matching is what lets "dent"
     find "dentist", and it is also why "who do i call" opened with
     Callen-Lorde. */
  var EXACT = 1.5;
  /* And a query that appears verbatim in what we attached to a row is the
     strongest signal there is, because those phrases were written down FOR
     this — "cant pay my hospital bill", "who do i call", "i want to die". */
  var W_PHRASE = 14;

  var exactCache = {};
  function hasExact(hay, word) {
    if (!ASCII.test(word)) return hay.indexOf(word) !== -1;
    var re = exactCache[word];
    if (!re) {
      var esc = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      re = exactCache[word] = new RegExp("\\b" + esc + "\\b");
    }
    return re.test(hay);
  }

  function fieldScore(hay, w, weight) {
    if (!hasWord(hay, w)) return 0;
    return hasExact(hay, w) ? weight * EXACT : weight;
  }

  function score(row, ws, phrase) {
    var hits = 0, points = 0;
    for (var i = 0; i < ws.length; i++) {
      var w = ws[i];
      var p = fieldScore(row.name, w, W_NAME) ||
              fieldScore(row.kind, w, W_KIND) ||
              fieldScore(row.tags, w, W_TAG) ||
              fieldScore(row.alias, w, W_ALIAS) ||
              fieldScore(row.body, w, W_BODY);
      if (p) { hits++; points += p; }
    }
    if (hits && phrase && phrase.length > 6 &&
        (row.alias.indexOf(phrase) !== -1 || row.name.indexOf(phrase) !== -1)) {
      points += W_PHRASE;
    }
    return { hits: hits, points: points };
  }

  /* Rank, then cut.

     Every word matching is the ideal and is often too much to ask, so the cut
     starts at the best any row managed and relaxes a word at a time until
     there are enough answers to be worth showing. Exact matches still lead —
     relaxing adds rows below them, it never reorders them — and the count
     says plainly when the query was not matched in full. */
  var ENOUGH = 5;
  /* A loosened search is a guess, and a guess three screens long is not more
     helpful than a guess one screen long. "free wifi" matched "free" in a
     hundred and seventy-four rows. */
  var LOOSE_MAX = 24;

  function rank(rows, ws, phrase) {
    if (!ws.length) return { keep: rows.map(function (r) { return r.ref; }), loose: false };
    var scored = rows.map(function (r) {
      var s = score(r, ws, phrase);
      return { r: r, hits: s.hits, points: s.points };
    });
    var best = 0;
    scored.forEach(function (s) { if (s.hits > best) best = s.hits; });
    if (!best) return { keep: [], loose: false };

    var need = best;
    var kept = scored.filter(function (s) { return s.hits >= need; });
    // Relaxing exists to avoid a blank page, not to pad a good answer. If
    // something matched the whole query, that IS the answer, however few: "free
    // coat" found the coat drive, then relaxed to one word and returned a
    // hundred and seventy-four rows containing "free".
    while (best < ws.length && kept.length < ENOUGH && need > 1) {
      need--;
      kept = scored.filter(function (s) { return s.hits >= need; });
    }
    kept.sort(function (a, b) {
      if (b.hits !== a.hits) return b.hits - a.hits;
      return b.points - a.points;
    });
    var loose = need < ws.length;
    if (loose && kept.length > LOOSE_MAX) kept = kept.slice(0, LOOSE_MAX);
    return {
      keep: kept.map(function (s) { return s.r.ref; }),
      loose: loose,
    };
  }

  /* "Nothing here matched X." — said once, in front of whatever did match. */
  function missNote() {
    if (!dropped.length) return "";
    var q = dropped.map(function (w) { return "\u201c" + w + "\u201d"; });
    var list = q.length === 1 ? q[0]
             : q.slice(0, -1).join(", ") + " or " + q[q.length - 1];
    return "Nothing here matched " + list + ". ";
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

    // Three haystacks, not one, so the ranker can tell a name from a
    // paragraph. `s` — the internal tags and the plain-English synonyms
    // build_help.py attaches — counts as "what this is", which is how "food
    // stamps" reaches SNAP and "kicked out" reaches an eviction hotline.
    items.forEach(function (it) {
      it.name = (it.n || "").toLowerCase();
      it.kind = (it.k || "").toLowerCase();
      it.tags = (it.t || "").toLowerCase().replace(/\s+/g, " ");
      // The row's own synonyms plus the ten-language vocabulary for every
      // need it belongs to, composed here rather than repeated on the wire.
      it.alias = ((it.s || "") + " " +
        (it.k2 || [it.g]).map(function (k) { return ix.nw[k] || ""; }).join(" "))
        .toLowerCase().replace(/\s+/g, " ");
      it.body = (it.d || "").toLowerCase();
      it._find = (it.name + " " + it.kind + " " + it.tags + " " +
                  it.alias + " " + it.body);
      it.ref = it;
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
      var eligible = items.filter(function (it) {
        return facetsOk(function (f) {
          return f === "boro" ? it.b : f === "lang" ? it.l : it.f;
        });
      });
      var ranked = rank(eligible, words, mode.phrase());
      var hits = ranked.keep;
      // Rows that answer the borough or the language *specifically* lead,
      // without disturbing the relevance order among equals.
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
      resultsH.textContent = missNote() + (hits.length === 0
        ? "Nothing matched that"
        : ranked.loose
          ? "No exact match. Here are the " + hits.length + " closest."
          : hits.length + (hits.length === 1 ? " place matches" : " places match"));
      noneEl.hidden = hits.length !== 0;
      countEl.textContent = hits.length === 0
        ? "Nothing matched"
        : ranked.loose
          ? "No exact match. Showing the " + hits.length + " closest."
          : "Showing " + hits.length + " of " + TOTAL + " places";
      if (clearBtn) clearBtn.hidden = !words.length;
      if (resetBtn) resetBtn.hidden = false;
    }

    return {
      apply: apply,
      terms: function (raw) { return termsFor(raw, corpus); },
      home: function () { return clusters; },
      phrase: function () { return phrase; },
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
    // Every row on a category page answers that page's need, so the
    // ten-language vocabulary for it is shipped once, on the container.
    var pageWords = dir.dataset.nw || "";
    var BODY = [".r__what", ".r__badges", ".r__facts dl", ".r__note"];
    function textOf(r, sel) {
      var el = r.querySelector(sel);
      return el ? el.textContent : "";
    }
    rows.forEach(function (r) {
      r.name = textOf(r, ".r__name").toLowerCase();
      r.kind = textOf(r, ".r__kind").toLowerCase();
      r.tags = (r.dataset.tags || "").toLowerCase().replace(/\s+/g, " ");
      r.alias = ((r.dataset.find || "") + " " + pageWords)
        .toLowerCase().replace(/\s+/g, " ");
      r.body = BODY.map(function (sel) { return textOf(r, sel); })
        .join(" ").toLowerCase().replace(/\s+/g, " ");
      r._find = r.name + " " + r.kind + " " + r.tags + " " + r.alias +
                " " + r.body;
      r._key = r.dataset.key;
      r.ref = r;
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
      var eligible = rows.filter(function (r) {
        return facetsOk(function (f) { return r.dataset[f]; });
      });
      var ranked = rank(eligible, words, mode.phrase());
      var live = Object.create(null);
      ranked.keep.forEach(function (r, i) { r._rank = i; live[r.id] = 1; });

      rows.forEach(function (r) {
        var ok = !!live[r.id];
        r.hidden = !ok;
        if (ok && !shown[r._key]) { shown[r._key] = 1; n++; }
        // Relevance first, then a local answer ahead of a citywide one. Order
        // is a small integer so the two can be combined without a sort.
        r.style.order = words.length
          ? String((r._rank || 0) * 2 +
                   (isCloserMatch(function (f) { return r.dataset[f]; }) ? 0 : 1))
          : (isCloserMatch(function (f) { return r.dataset[f]; }) ? "-1" : "");
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
        : ranked.loose
          ? "No exact match. Showing the " + n + " closest."
          : "Showing " + n + " of " + TOTAL;
      if (noneEl) noneEl.hidden = n !== 0;
      if (clearBtn) clearBtn.hidden = !words.length;
      if (resetBtn) resetBtn.hidden = !narrowed();
    }

    return {
      apply: apply,
      terms: function (raw) { return termsFor(raw, corpus); },
      home: function () { return document.querySelector(".cat__main"); },
      phrase: function () { return phrase; },
      jump: null,
      total: TOTAL,
    };
  }

  /* -------------------------------------------------------------- wiring */
  var phrase = "";
  function onType() {
    phrase = q.value.toLowerCase().trim().replace(/[\u2019']/g, "").replace(/\s+/g, " ");
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
