/* ============================================================
   Waypoint — journey controller

   Owns: the hero pass-through (driving the WebGL door in assets/door.js),
   the painterly crossfade, the spiral, the tubelight nav, reveals,
   the progress rail, and the two forms.
   ============================================================ */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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
    var heroShow = 1 - ramp(t, 0.86, 0.99);
    var closeShow = cT < 0 ? 0 : ramp(cT, 0.04, 0.42) * (1 - ramp(cT, 0.86, 1));
    var show = Math.max(heroShow, closeShow);

    root.style.setProperty("--doorShow", show.toFixed(3));
    root.style.setProperty("--worldShow", ramp(t, 0.88, 1).toFixed(3));

    if (thresh && !reduced) {
      var x = clamp((t - 0.78) / 0.22, 0, 1);
      thresh.style.opacity = (Math.sin(Math.PI * x) * 0.92).toFixed(3);
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
    layers.forEach(function (l, i) {
      l.style.opacity = clamp(1 - Math.abs(pos - i), 0, 1);
      l.style.transform = "scale(" + (1.05 + P * 0.5 + i * 0.015) + ")";
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
    sw = window.innerWidth; sh = window.innerHeight;
    spiral.width = sw * dpr; spiral.height = sh * dpr;
    spiral.style.width = sw + "px"; spiral.style.height = sh + "px";
    sctx = spiral.getContext("2d"); sctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function drawSpiral() {
    if (!sctx) return;
    sctx.clearRect(0, 0, sw, sh);
    if (window.matchMedia("(max-width:900px)").matches) return;
    if (parseFloat(root.style.getPropertyValue("--worldShow") || "1") < 0.02) return;
    var P = progress();
    var cx = sw / 2, amp = Math.min(sw * 0.16, 200), turn = sh * 0.6;
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

  /* ---------- tubelight nav ---------- */
  var lamp = $("#navLamp");
  var navSections = ["work", "partners", "students"].map(function (id) {
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
  function tick() { doorFrame(); chrome(); journey(); navActive(); }
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
  if (!reduced) { (function loop() { tick(); drawSpiral(); requestAnimationFrame(loop); })(); }
  else { drawSpiral(); tick(); }

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
  var scenes = $$(".scene");
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
