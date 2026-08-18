/* ============================================================
   Waypoint — journey controller

   Owns: the hero pass-through (driving the WebGL door in assets/door.js),
   the painterly crossfade, the spiral, the tubelight nav, reveals,
   the progress rail, and the two forms.
   ============================================================ */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  /* Phones pay for this page in compositing, not in script: the tick itself
     measures 0.03ms. What costs is how many full-screen layers have to be
     re-rastered per frame. Everything gated on this query is a layer that
     stops being repainted below 900px. */
  var narrow = window.matchMedia("(max-width:900px)");
  var clamp = function (v, a, b) { return Math.min(b, Math.max(a, v)); };
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };
  var root = document.documentElement;

  /* smoothstep between two thresholds */
  function ramp(v, a, b) {
    if (b === a) return v >= b ? 1 : 0;
    var x = clamp((v - a) / (b - a), 0, 1);
    return x * x * (3 - 2 * x);
  }

  $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  var scenes = $$(".scene");

  /* ---------- inertial scrolling (vendored Lenis) ---------- */
  var lenis = null;
  if (window.Lenis && !reduced) {
    lenis = new window.Lenis({ lerp: 0.085, smoothWheel: true, touchMultiplier: 1.7 });
    (function raf(time) { lenis.raf(time); requestAnimationFrame(raf); })(0);
  }
  function goTo(target) {
    if (lenis) lenis.scrollTo(target, { offset: 0, duration: 1.25 });
    else if (typeof target === "number") window.scrollTo(0, target);
    else target.scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
  }
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a) return;
    var id = a.getAttribute("href").slice(1);
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    goTo(el);
    if (history.replaceState) history.replaceState(null, "", "#" + id);
  });

  /* ---------- nav chrome ---------- */
  var nav = $(".nav");
  function chrome() { if (nav) nav.classList.toggle("stuck", (window.scrollY || 0) > 40); }

  /* ---------- mobile menu ---------- */
  var tog = $(".nav__tog"), links = $(".nav__links");
  if (tog && links) {
    tog.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      tog.classList.toggle("open", open);
      tog.setAttribute("aria-expanded", String(open));
    });
    links.addEventListener("click", function (e) {
      if (e.target.closest("a")) { links.classList.remove("open"); tog.classList.remove("open"); tog.setAttribute("aria-expanded", "false"); }
    });
  }

  /* ============================================================
     THE DOOR — the hero's scroll drives it, and the closing scene
     brings it back with the camera on the far side.
     ============================================================ */
  var hero = $(".hero");
  var closeSec = $("#close");
  var thresh = $(".threshold");
  var doorLive = false;

  function heroT() {
    if (!hero) return 1;
    var span = hero.offsetHeight - window.innerHeight;
    if (span <= 0) return (window.scrollY || 0) > 0 ? 1 : 0;
    return clamp(((window.scrollY || 0) - hero.offsetTop) / span, 0, 1);
  }

  function closeT() {
    if (!closeSec) return -1;
    var r = closeSec.getBoundingClientRect(), vh = window.innerHeight;
    if (r.top > vh || r.bottom < 0) return -1;
    return clamp((vh - r.top) / (vh + r.height), 0, 1);
  }

  function doorFrame() {
    var t = heroT();
    var api = window.__waypointDoor;

    root.style.setProperty("--doorT", t.toFixed(4));
    root.classList.toggle("at-door", t < 0.9);

    var cT = closeT();
    // by t=0.95 the doorway is wider than the viewport, so the canvas and the
    // painted backdrop are showing the same thing: that is the only safe window
    // to hand over in, and parking anywhere inside it looks like one image
    var heroShow = 1 - ramp(t, 0.95, 1);
    var closeShow = cT < 0 ? 0 : ramp(cT, 0.04, 0.42) * (1 - ramp(cT, 0.86, 1));
    var show = Math.max(heroShow, closeShow);

    root.style.setProperty("--doorShow", show.toFixed(3));
    /* opacity:0 still keeps a full-screen layer — a WebGL canvas and six
       gradient divs — alive in the compositor. visibility lets it be skipped,
       and flips back the instant the closing scene brings the door round. */
    root.classList.toggle("door-gone", show < 0.001);
    root.style.setProperty("--worldShow", ramp(t, 0.96, 1).toFixed(3));

    // a brief warm swell across the threshold, not a white flash: it only has
    // to soften a crossfade between two framings of the same painting
    if (thresh && !reduced) {
      var x = clamp((t - 0.90) / 0.10, 0, 1);
      thresh.style.opacity = (Math.sin(Math.PI * x) * 0.45).toFixed(3);
    }

    if (api) {
      if (closeShow > heroShow && cT >= 0) api.set(cT, "out");
      else api.set(t, "in");
      var wantLive = show > 0.01;
      if (wantLive !== doorLive) { doorLive = wantLive; api.live(wantLive); }
    }
  }

  /* ---------- journey background: crossfade the stages AFTER the door ---------- */
  var layers = ["#layA", "#layB", "#layC", "#layD"].map(function (s) { return $(s); }).filter(Boolean);

  function progress() {
    var start = hero ? hero.offsetTop + hero.offsetHeight - window.innerHeight : 0;
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var span = max - start;
    return span > 0 ? clamp(((window.scrollY || 0) - start) / span, 0, 1) : 0;
  }

  function journey() {
    if (reduced) return;
    var P = progress(), N = layers.length;
    var pos = P * (N - 1);
    /* Opacity is a compositor property: crossfading the four landscapes is
       nearly free and it is the part that carries the journey. The slow zoom is
       not — changing scale on a background-image layer re-rasters it, and there
       are four of them at full screen. On a phone that is the single biggest
       cost on the page, and the movement it buys is barely perceptible at
       375px. The reduced-motion path has always rendered these static, so a
       still backdrop is a rendering this design already accepts. */
    var zoom = !narrow.matches;
    layers.forEach(function (l, i) {
      l.style.opacity = clamp(1 - Math.abs(pos - i), 0, 1);
      if (zoom) l.style.transform = "scale(" + (1.05 + P * 0.5 + i * 0.015) + ")";
      else if (l.style.transform) l.style.transform = "";   // crossing the breakpoint
    });
  }

  /* the later stages are not needed until the door is behind you */
  function loadStages() {
    $$(".stage__layer[data-src]").forEach(function (l) {
      l.style.backgroundImage = "url('" + l.getAttribute("data-src") + "')";
      l.removeAttribute("data-src");
    });
  }
  if ("requestIdleCallback" in window) requestIdleCallback(loadStages, { timeout: 2500 });
  else window.addEventListener("load", function () { setTimeout(loadStages, 400); });

  /* ---------- spiral that winds down through the scenery ---------- */
  var spiral = $("#spiral"), sctx = null, sw = 0, sh = 0;
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  function sresize() {
    if (!spiral) return;
    /* .spiral is display:none below 900px. Sizing it anyway allocates a
       backing store at device pixel ratio — several megabytes of GPU memory for
       something nobody can see, plus a full-surface clearRect every frame.
       Dropping sctx also makes drawSpiral bail on its first line. */
    if (narrow.matches) {
      if (spiral.width) { spiral.width = 0; spiral.height = 0; }
      sctx = null;
      return;
    }
    sw = window.innerWidth; sh = window.innerHeight;
    spiral.width = sw * dpr; spiral.height = sh * dpr;
    spiral.style.width = sw + "px"; spiral.style.height = sh + "px";
    sctx = spiral.getContext("2d"); sctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  /* The thread reshapes itself for whichever scene you are in: it swings wide
     opposite the text on the alternating scenes, and narrows to a quiet line
     down the gutter between the two columns of a hold scene. */
  var SPIRAL_REST = { cx: 0.5, amp: 0.055, turn: 0.66 };
  var spiralNow = { cx: 0.5, amp: 0.055, turn: 0.66 };

  function spiralTarget() {
    var mid = window.innerHeight * 0.5;
    for (var i = 0; i < scenes.length; i++) {
      var r = scenes[i].getBoundingClientRect();
      if (r.top > mid || r.bottom < mid) continue;
      var c = scenes[i].classList;
      if (c.contains("scene--pin")) return { cx: 0.5, amp: 0.012, turn: 1.35 };
      /* two columns, same as a hold scene: the thread narrows to the gutter
         rather than swinging through the middle of the composition */
      if (c.contains("scene--ways")) return { cx: 0.5, amp: 0.018, turn: 1.2 };
      /* the line section is a hold scene now, so this is what steers its
         thread: down the gutter between the two columns, never through the
         type. It used to need a scene--lane case above scene--pin for exactly
         that reason. */
      if (c.contains("scene--hold")) return { cx: 0.5, amp: 0.020, turn: 1.15 };
      if (c.contains("scene--center")) return { cx: 0.5, amp: 0.048, turn: 0.72 };
      if (c.contains("scene--left")) return { cx: 0.74, amp: 0.082, turn: 0.54 };
      if (c.contains("scene--right")) return { cx: 0.26, amp: 0.082, turn: 0.54 };
      break;
    }
    return SPIRAL_REST;
  }

  /* How much of the screen the closing scene has taken. The thread unwinds into
     that space and is gone before the door arrives: the last frame of the page
     is the door and one line, nothing else. */
  function closingRoom() {
    if (!closeSec) return 0;
    var r = closeSec.getBoundingClientRect(), vh = window.innerHeight;
    if (r.bottom <= 0 || r.top >= vh) return 0;
    var seen = Math.min(r.bottom, vh) - Math.max(r.top, 0);
    return clamp(seen / (vh * 0.6), 0, 1);
  }
  var openNow = 0;

  /* and it only exists while you are actually moving */
  var spiralAlpha = 0, lastMoveAt = -1e9, lastY = window.scrollY || 0;
  function spiralFade() {
    var y = window.scrollY || 0;
    if (Math.abs(y - lastY) > 0.5) { lastMoveAt = performance.now(); lastY = y; }
    openNow += (closingRoom() - openNow) * (reduced ? 1 : 0.08);
    var leaving = 1 - ramp(openNow, 0.10, 0.62);
    if (reduced) { spiralAlpha = leaving; }
    else {
      var want = (performance.now() - lastMoveAt < 700 ? 1 : 0) * leaving;
      spiralAlpha += (want - spiralAlpha) * 0.07;
    }
    root.style.setProperty("--spiralShow", spiralAlpha.toFixed(3));
  }

  function drawSpiral() {
    if (!sctx) return;
    sctx.clearRect(0, 0, sw, sh);
    if (window.matchMedia("(max-width:900px)").matches) return;
    if (spiralAlpha < 0.02) return;
    if (parseFloat(root.style.getPropertyValue("--worldShow") || "1") < 0.02) return;

    var want = spiralTarget(), k = reduced ? 1 : 0.055;
    spiralNow.cx += (want.cx - spiralNow.cx) * k;
    spiralNow.amp += (want.amp - spiralNow.amp) * k;
    spiralNow.turn += (want.turn - spiralNow.turn) * k;

    var P = progress();
    var cx = sw * spiralNow.cx;
    // as the closing scene arrives the coil opens out and unwinds, so it reads
    // as making way rather than simply switching off
    var amp = Math.min(sw * spiralNow.amp, 220) * (1 + openNow * 3.4);
    var turn = sh * spiralNow.turn * (1 + openNow * 1.8);
    var drift = reduced ? 0 : performance.now() * 0.012;
    var phase = P * sh * 4 + drift, step = 11;
    for (var y = -amp; y < sh + amp; y += step) {
      var ang = (y + phase) * (Math.PI * 2 / turn);
      var x = cx + amp * Math.cos(ang);
      var f = (Math.sin(ang) + 1) / 2;
      sctx.beginPath();
      sctx.fillStyle = "rgba(231,197,126," + (0.08 + f * 0.5) + ")";
      sctx.shadowColor = "rgba(231,197,126,0.7)";
      sctx.shadowBlur = f * 9;
      sctx.arc(x, y, 0.7 + f * 2.7, 0, 6.283);
      sctx.fill();
    }
    sctx.shadowBlur = 0;
  }

  /* ---------- reading veil: one fixed layer, opacity follows dense text ---------- */
  var denseScenes = $$(".scene--hold, .scene--vow, .scene--wide, .scene--pin, .scene--ways");
  var veilNow = 0;
  function readVeil() {
    var vh = window.innerHeight, want = 0;
    for (var i = 0; i < denseScenes.length; i++) {
      var r = denseScenes[i].getBoundingClientRect();
      if (r.bottom <= 0 || r.top >= vh) continue;
      var seen = Math.min(r.bottom, vh) - Math.max(r.top, 0);
      want = Math.max(want, clamp(seen / (vh * 0.55), 0, 1));
    }
    veilNow += (want - veilNow) * (reduced ? 1 : 0.09);
    root.style.setProperty("--readVeil", veilNow.toFixed(3));
  }

  /* ---------- pinned scenes ----------
     Each pinned section is taller than the viewport and holds a sticky child
     that fills it. Scrolling through the surplus height scrubs --t from 0 to 1,
     which is what actually opens the envelope, draws the wires and slides the
     lane. Lines arrive on their own thresholds and then stay, dimmed, so a
     reader who stops halfway can still see the beat they came from. */
  var pins = $$("[data-pin]").map(function (el) {
    return { el: el, lines: $$(".pin__line", el) };
  });

  function pinFrame() {
    for (var i = 0; i < pins.length; i++) {
      var p = pins[i], r = p.el.getBoundingClientRect(), vh = window.innerHeight;
      var span = p.el.offsetHeight - vh;
      var t = span > 0 ? clamp(-r.top / span, 0, 1) : (r.top <= 0 ? 1 : 0);
      p.el.style.setProperty("--t", t.toFixed(4));

      /* a line is on once its threshold is passed, and spent once the next arrives */
      for (var j = 0; j < p.lines.length; j++) {
        var at = parseFloat(p.lines[j].getAttribute("data-at")) || 0;
        var next = j + 1 < p.lines.length ? parseFloat(p.lines[j + 1].getAttribute("data-at")) : 2;
        p.lines[j].classList.toggle("on", t >= at);
        p.lines[j].classList.toggle("spent", t >= next);
      }
    }
  }

  /* ---------- the doors: click one open ----------
     Hover is handled entirely in CSS and only makes the header breathe; the
     description is a click, and one row is open at a time. The markup ships
     with no aria-expanded and the panels open, so a visitor with the script
     blocked gets four readable descriptions rather than four names and no way
     to reach what is under them. Taking the list over means both at once:
     add .ways--js, which closes the panels, and write the attribute that says
     so. Clicking the open row closes it, so the section can be put back to
     rest without reloading. */
  $$(".ways").forEach(function (list) {
    var rows = $$(".ways__row", list);
    if (!rows.length) return;
    rows.forEach(function (row) { row.setAttribute("aria-expanded", "false"); });
    /* the panels are open in the markup, so taking them over has to be a cut,
       not a transition: without --boot the reader watches four descriptions
       animate shut on load. Add both classes, force the closed state to be
       computed while transitions are off, then hand them back — the value is
       already 0fr by then, so nothing starts. Two forced reflows rather than a
       rAF, because a backgrounded tab never fires one. */
    list.classList.add("ways--js", "ways--boot");
    void list.offsetHeight;
    list.classList.remove("ways--boot");
    void list.offsetHeight;
    rows.forEach(function (row) {
      row.addEventListener("click", function () {
        var wasOpen = row.getAttribute("aria-expanded") === "true";
        rows.forEach(function (other) { other.setAttribute("aria-expanded", "false"); });
        if (!wasOpen) row.setAttribute("aria-expanded", "true");
      });
    });
  });

  /* ---------- tubelight nav ---------- */
  var lamp = $("#navLamp");
  var navSections = ["bills", "work", "students", "partners"].map(function (id) {
    return { id: id, el: document.getElementById(id), link: $('.nav__links a[href="#' + id + '"]') };
  }).filter(function (s) { return s.el && s.link; });

  function navActive() {
    if (!lamp || !navSections.length) return;
    if (window.matchMedia("(max-width:900px)").matches) {
      lamp.classList.remove("on");
      navSections.forEach(function (s) { s.link.classList.remove("current"); });
      return;
    }
    var center = (window.scrollY || 0) + window.innerHeight * 0.5;
    var active = null;
    navSections.forEach(function (s) { if (s.el.offsetTop <= center) active = s; });
    navSections.forEach(function (s) { s.link.classList.toggle("current", !!active && s.id === active.id); });
    if (active) {
      var L = active.link, pad = 6;
      lamp.style.left = (L.offsetLeft - pad) + "px";
      lamp.style.width = (L.offsetWidth + pad * 2) + "px";
      lamp.classList.add("on");
    } else {
      lamp.classList.remove("on");
    }
  }

  /* ---------- one loop drives everything scroll-linked ---------- */
  function tick() { doorFrame(); chrome(); journey(); pinFrame(); navActive(); readVeil(); spiralFade(); drawSpiral(); }
  /* exposed so the scroll choreography can be driven deterministically in tests,
     where requestAnimationFrame does not run (headless tabs report hidden) */
  window.__waypointTick = tick;

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { tick(); ticking = false; });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", function () { sresize(); tick(); });

  if (spiral && spiral.getContext) sresize();
  if (!reduced) { (function loop() { tick(); requestAnimationFrame(loop); })(); }
  else { tick(); }

  /* ---------- blur-to-focus reveals ---------- */
  var foci = $$(".focus-in");
  if ("IntersectionObserver" in window && !reduced) {
    var fo = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) e.target.classList.add("in");
        else if (e.target.getAttribute("data-once") === null) e.target.classList.remove("in");
      });
    }, { rootMargin: "-22% 0px -22% 0px", threshold: 0 });
    foci.forEach(function (el) { fo.observe(el); });
  } else {
    foci.forEach(function (el) { el.classList.add("in"); });
  }

  /* ---------- diamond rail ---------- */
  var rail = $(".rail");
  if (rail && scenes.length) {
    rail.innerHTML = "";
    var dots = scenes.map(function (sc, i) {
      var b = document.createElement("button");
      b.setAttribute("aria-label", "Go to part " + (i + 1));
      b.addEventListener("click", function () { goTo(sc); });
      rail.appendChild(b);
      return b;
    });
    if ("IntersectionObserver" in window) {
      var ro = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (e.isIntersecting) {
            var idx = scenes.indexOf(e.target);
            dots.forEach(function (d, k) { d.classList.toggle("on", k === idx); });
          }
        });
      }, { rootMargin: "-50% 0px -50% 0px", threshold: 0 });
      scenes.forEach(function (s) { ro.observe(s); });
    }
  }

  /* ---------- count up (used by the pitch pages) ---------- */
  $$("[data-count]").forEach(function (el) {
    var t = parseFloat(el.getAttribute("data-count")) || 0;
    if (reduced) { el.textContent = t; return; }
    var done = false;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting && !done) {
          done = true; var s = performance.now();
          (function step(now) {
            var p = clamp((now - s) / 1300, 0, 1), k = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(t * k);
            if (p < 1) requestAnimationFrame(step);
          })(s);
        }
      });
    }, { threshold: 0.6 });
    io.observe(el);
  });

  /* ---------- forms → Waypoint submit edge function ---------- */
  var SUBMIT_URL = "https://zzsqvztwbhdgrdvjpbrr.supabase.co/functions/v1/submit";
  var PAGE_LOAD_TIME = Date.now();

  $$("form[data-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var ok = form.querySelector(".form__ok");
      var err = form.querySelector(".form__err");
      var btn = form.querySelector('button[type="submit"]');
      var type = form.getAttribute("data-form");
      var fd = new FormData(form);
      var trap = (fd.get("trap") || "").toString();
      var name = (fd.get("name") || "").toString().trim();
      var email = (fd.get("email") || "").toString().trim();
      var payload = {};
      fd.forEach(function (v, k) {
        if (["name", "email", "trap"].indexOf(k) === -1) { v = v.toString().trim(); if (v) payload[k] = v; }
      });

      if (err) err.classList.remove("show");
      if (btn) { btn.disabled = true; btn.dataset.label = btn.dataset.label || btn.textContent; btn.textContent = "Sending…"; }

      fetch(SUBMIT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ form_type: type, name: name, email: email, payload: payload, trap: trap || null, elapsed: Date.now() - PAGE_LOAD_TIME })
      }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        if (ok) ok.classList.add("show");
        form.querySelectorAll(".field, .form__submit, .form__legal").forEach(function (el) { el.style.display = "none"; });
      }).catch(function () {
        if (btn) { btn.disabled = false; btn.textContent = btn.dataset.label || "Send"; }
        if (err) err.classList.add("show");
      });
    });
  });

  tick();
})();
