/* ============================================================
   Waypoint — landscape journey controller
   ============================================================ */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var clamp = function (v, a, b) { return Math.min(b, Math.max(a, v)); };
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* nav chrome */
  var nav = $(".nav");
  function chrome() { if (nav) nav.classList.toggle("stuck", (window.scrollY || 0) > 40); }

  /* mobile menu */
  var tog = $(".nav__tog"), links = $(".nav__links");
  if (tog && links) {
    tog.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      tog.classList.toggle("open", open);
      tog.setAttribute("aria-expanded", String(open));
    });
    links.addEventListener("click", function (e) { if (e.target.closest("a")) { links.classList.remove("open"); tog.classList.remove("open"); } });
  }

  /* ---------- journey background (crossfade through N landscape stages) ---------- */
  var layers = ["#layA", "#layB", "#layC", "#layD"].map(function (s) { return $(s); }).filter(Boolean);
  function progress() { var max = document.documentElement.scrollHeight - window.innerHeight; return max > 0 ? clamp((window.scrollY || 0) / max, 0, 1) : 0; }
  function journey() {
    if (reduced) return;
    var P = progress(), N = layers.length;
    var pos = P * (N - 1);                 // 0 .. N-1, current position in the stage sequence
    layers.forEach(function (l, i) {
      l.style.opacity = clamp(1 - Math.abs(pos - i), 0, 1);
      l.style.transform = "scale(" + (1.05 + P * 0.5 + i * 0.015) + ")";
    });
  }

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
    var P = progress();
    var cx = sw / 2, amp = Math.min(sw * 0.16, 200), turn = sh * 0.6;
    var drift = reduced ? 0 : performance.now() * 0.012;
    var phase = P * sh * 4 + drift, step = 11;
    for (var y = -amp; y < sh + amp; y += step) {
      var ang = (y + phase) * (Math.PI * 2 / turn);
      var x = cx + amp * Math.cos(ang);
      var f = (Math.sin(ang) + 1) / 2;            // 0 back .. 1 front
      sctx.beginPath();
      sctx.fillStyle = "rgba(231,197,126," + (0.08 + f * 0.5) + ")";
      sctx.shadowColor = "rgba(231,197,126,0.7)";
      sctx.shadowBlur = f * 9;
      sctx.arc(x, y, 0.7 + f * 2.7, 0, 6.283);
      sctx.fill();
    }
    sctx.shadowBlur = 0;
  }

  /* ---------- tubelight nav (lights the section you're in, slides between) ---------- */
  var lamp = $("#navLamp");
  var navSections = ["students", "partners", "schools"].map(function (id) {
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
    navSections.forEach(function (s) { s.link.classList.toggle("current", active && s.id === active.id); });
    if (active) {
      var L = active.link, pad = 6;
      lamp.style.left = (L.offsetLeft - pad) + "px";
      lamp.style.width = (L.offsetWidth + pad * 2) + "px";
      lamp.classList.add("on");
    } else {
      lamp.classList.remove("on");
    }
  }

  var ticking = false;
  function onScroll() { if (ticking) return; ticking = true; requestAnimationFrame(function () { chrome(); journey(); navActive(); ticking = false; }); }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", navActive);

  if (spiral && spiral.getContext) {
    sresize();
    window.addEventListener("resize", sresize);
    if (!reduced) { (function sloop() { journey(); navActive(); drawSpiral(); requestAnimationFrame(sloop); })(); }
    else drawSpiral();
  }

  /* ---------- blur-to-focus reveals ---------- */
  var foci = $$(".focus-in");
  if ("IntersectionObserver" in window && !reduced) {
    var fo = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) e.target.classList.add("in");
        else if (e.target.getAttribute("data-once") === null) e.target.classList.remove("in");
      });
    }, { rootMargin: "-28% 0px -28% 0px", threshold: 0 });
    foci.forEach(function (el) { fo.observe(el); });
  } else {
    foci.forEach(function (el) { el.classList.add("in"); });
  }

  /* ---------- diamond rail (active scene + click to travel) ---------- */
  var scenes = $$(".scene");
  var rail = $(".rail");
  if (rail && scenes.length) {
    rail.innerHTML = "";
    var dots = scenes.map(function (sc, i) {
      var b = document.createElement("button");
      b.setAttribute("aria-label", "Go to part " + (i + 1));
      b.addEventListener("click", function () { sc.scrollIntoView({ behavior: reduced ? "auto" : "smooth" }); });
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

  /* ---------- count up (subpages, optional) ---------- */
  $$("[data-count]").forEach(function (el) {
    var t = parseFloat(el.getAttribute("data-count")) || 0;
    if (reduced) { el.textContent = t; return; }
    var done = false;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting && !done) {
          done = true; var s = performance.now();
          (function tick(now) { var p = clamp((now - s) / 1300, 0, 1), k = 1 - Math.pow(1 - p, 3); el.textContent = Math.round(t * k); if (p < 1) requestAnimationFrame(tick); })(s);
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
      fd.forEach(function (v, k) { if (["name", "email", "trap"].indexOf(k) === -1) { v = v.toString().trim(); if (v) payload[k] = v; } });

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

  chrome(); journey(); navActive();
})();
