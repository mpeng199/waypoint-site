/* What check.py cannot see: the page as it actually renders.

   check.py reads the source. It can tell you that a token pair contrasts and
   that a class declares min-height:44px. It cannot tell you that .reel__k
   resolves to 3.94:1 against the green actually behind it, or that a link is
   as tall as its own text because the rule widening it was scoped to list
   items. Both of those shipped.

   Paste this into the console on any page of the site, or run it through the
   preview tools. It loads every page in a hidden iframe at 390px and reports:

     1. text whose measured contrast is under AA against the background
        actually painted behind it, alpha composited;
     2. links whose real hit area — hit-tested with elementFromPoint, not
        read off the box — is under 24px in either direction;
     3. anchors that land under a sticky header when you jump to them;
     4. anything that makes the page drag sideways.

   It reports; it does not fix. Everything it has found so far is in the git
   log with the measurement that found it. */
window.waypointAudit = async function (pages, width) {
  pages = pages || ['index.html', 'help.html', 'help-food.html', 'help-crisis.html',
    'help-legal.html', 'help-money.html', 'help-senior.html', 'help-es.html',
    'help-ar.html', 'help-ru.html', 'help-zh.html', 'help-bn.html', 'help-ko.html',
    'help-ht.html', 'help-fr.html', 'help-pl.html', 'help-ur.html', 'privacy.html',
    'terms.html', 'partner-pitch.html', 'cohort-onboarding.html'];
  width = width || 390;
  var base = location.pathname.replace(/[^/]*$/, '');
  var parse = function (c) {
    var m = c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/);
    return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null;
  };
  var L = function (c) {
    var f = function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  var ratio = function (a, b) { var la = L(a), lb = L(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  var over = function (fg, bg) { return [0, 1, 2].map(function (i) { return Math.round(fg[i] * fg[3] + bg[i] * (1 - fg[3])); }); };
  var report = [];

  for (var pi = 0; pi < pages.length; pi++) {
    var p = pages[pi];
    var f = document.createElement('iframe');
    f.style.cssText = 'width:' + width + 'px;height:900px;border:0;position:fixed;left:0;top:0;opacity:0.01';
    document.body.appendChild(f);
    await new Promise(function (r) { f.onload = r; f.src = base + p + '?audit=' + Date.now(); });
    /* Let the page settle before measuring. Note a real limit of this
       harness: help.js publishes the measured --head-h through a
       ResizeObserver, and an offscreen iframe does not get its observer
       callbacks delivered — so on a page that has a script, the anchor test
       below reports every jump as landing under the header whether it does or
       not. It is right about the ten language pages, which have no script.
       For the scripted pages, navigate to them and run the anchor test there;
       that is how the .dir skip-link bug was confirmed. */
    await new Promise(function (r) { setTimeout(r, 400); });
    var d = f.contentDocument, cw = f.contentWindow, found = [];

    /* 1. contrast, against the ground actually behind it */
    var els = d.querySelectorAll('body *');
    for (var i = 0; i < els.length; i++) {
      var e = els[i], hasText = false;
      for (var n = 0; n < e.childNodes.length; n++)
        if (e.childNodes[n].nodeType === 3 && e.childNodes[n].textContent.trim().length > 1) hasText = true;
      if (!hasText) continue;
      var cs = cw.getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      var fg = parse(cs.color); if (!fg) continue;
      var bgEl = e, bg = null;
      while (bgEl) { var c = parse(cw.getComputedStyle(bgEl).backgroundColor);
        if (c && c[3] > 0.95) { bg = c.slice(0, 3); break; } bgEl = bgEl.parentElement; }
      if (!bg) continue;
      var r = ratio(over(fg, bg), bg);
      var size = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
      var need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
      if (r < need) found.push('contrast ' + r.toFixed(2) + '/' + need + ' — ' +
        e.tagName + '.' + (e.className.toString().split(' ')[0] || '') +
        ' "' + e.textContent.trim().slice(0, 30) + '"');
    }

    /* 2. hit areas, hit-tested */
    var links = d.querySelectorAll('a');
    for (var j = 0; j < links.length; j++) {
      var a = links[j], acs = cw.getComputedStyle(a);
      if (acs.display === 'none' || (!a.offsetParent && acs.position !== 'fixed')) continue;
      a.scrollIntoView({ block: 'center', behavior: 'instant' });
      var b = a.getBoundingClientRect();
      if (b.height >= 24 && b.width >= 24) continue;
      if (b.top < 0 || b.bottom > cw.innerHeight) continue;
      var cx = b.left + b.width / 2, grow = (24 - b.height) / 2;
      var reaches = function (el) { return el === a || (el && a.contains(el)) || (el && el.closest && el.closest('a') === a); };
      if (!(reaches(d.elementFromPoint(cx, b.top - grow + 1)) &&
            reaches(d.elementFromPoint(cx, b.bottom + grow - 1))))
        found.push('hit area ' + Math.round(b.width) + 'x' + Math.round(b.height) +
          ' — .' + (a.className || '(none)') + ' "' + a.textContent.trim().slice(0, 24) + '"');
    }

    /* 3. anchors that land under the header — see the note above: only
       meaningful on a page with no script. */
    var head = d.querySelector('.sitehead');
    if (head && !d.querySelector('script[src]')) {
      var seen = {}, as = d.querySelectorAll('a[href^="#"]');
      for (var k = 0; k < as.length && k < 40; k++) {
        var id = as[k].getAttribute('href');
        if (id.length < 2 || seen[id]) continue; seen[id] = 1;
        var t = d.querySelector(id); if (!t) continue;
        t.scrollIntoView({ behavior: 'instant', block: 'start' });
        var covered = Math.round(head.getBoundingClientRect().bottom - t.getBoundingClientRect().top);
        if (covered > 0) found.push('jump to ' + id + ' lands ' + covered + 'px under the header');
      }
    }

    /* 4. sideways drag */
    if (d.documentElement.scrollWidth > d.documentElement.clientWidth)
      found.push('page drags sideways: ' + d.documentElement.scrollWidth + ' > ' + d.documentElement.clientWidth);

    if (found.length) report.push({ page: p, found: found.filter(function (v, ix, arr) { return arr.indexOf(v) === ix; }) });
    f.remove();
  }
  return report.length ? report : 'clean at ' + width + 'px across ' + pages.length + ' pages';
};
