/* What the browser actually does, which reading the source cannot tell you.
 *
 * Two claims are made elsewhere in this repo that no amount of source-reading
 * can verify, because both are about runtime behaviour:
 *
 *   1. the phone does not download Three at all (750KB across two chunks)
 *   2. no rAF loop runs while the reader is just reading
 *
 * Both regress silently. Put a
 * <link rel="modulepreload" href="assets/vendor/three.module.min.js"> back in
 * index.html and every check.py assertion still passes — the gate is still
 * there in door.js, still correct, still reachable — while every phone
 * downloads the 750KB again before the gate can run. Likewise, restoring
 * Lenis' original `(function raf(t){ lenis.raf(t); rAF(raf); })(0)` reads as
 * completely ordinary and puts a frame callback back on the main thread for
 * the life of the page. check.py sees neither. A real browser sees both.
 *
 *     node check_runtime.js [origin] [-v]     # default http://localhost:8771
 *
 * No dependencies: raw CDP over the WebSocket client built into Node 22+,
 * against whatever Chrome is on the machine.
 */
'use strict';
const { spawn } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const ORIGIN = process.argv.slice(2).find((a) => /^https?:\/\//.test(a)) || 'http://localhost:8771';
const THREE_RE = /three\.(module|core)\.min\.js/;

const CHROME = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].find((p) => { try { return fs.existsSync(p); } catch { return false; } });

let pass = 0, fail = 0;
const ok = (m) => { pass++; if (process.argv.includes('-v')) console.log('  ok   ' + m); };
const bad = (m) => { fail++; console.log('  FAIL ' + m); };

/* ---------------------------------------------------------------- CDP glue */
class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.waiting = new Map(); this.onEvent = () => {};
    ws.addEventListener('message', (e) => {
      const m = JSON.parse(e.data);
      if (m.id && this.waiting.has(m.id)) { this.waiting.get(m.id)(m); this.waiting.delete(m.id); }
      else if (m.method) this.onEvent(m);
    });
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    return new Promise((res, rej) => {
      this.waiting.set(id, (m) => (m.error ? rej(new Error(method + ': ' + m.error.message)) : res(m.result)));
      this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function connect(url) {
  const ws = new WebSocket(url);
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  return new CDP(ws);
}

/* Load one page under one emulation profile and report what it fetched. */
async function visit(cdp, { width, height, mobile, reducedMotion, saveData, settle = 2500 }) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });

  const requests = [], consoleErrors = [];
  cdp.onEvent = (m) => {
    if (m.sessionId !== sessionId) return;
    if (m.method === 'Network.requestWillBeSent') requests.push(m.params.request.url);
    // Uncaught exceptions and console.error both land here. The poster path is
    // the ordinary path for most readers, so it must be silent.
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params.exceptionDetails;
      consoleErrors.push(d.exception?.description || d.text || 'exception');
    }
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
      consoleErrors.push(m.params.entry.text);
    }
  };

  await cdp.send('Runtime.enable', {}, sessionId);
  await cdp.send('Log.enable', {}, sessionId);
  await cdp.send('Network.enable', {}, sessionId);
  await cdp.send('Page.enable', {}, sessionId);
  await cdp.send('Emulation.setDeviceMetricsOverride',
    { width, height, deviceScaleFactor: mobile ? 3 : 1, mobile }, sessionId);
  if (reducedMotion) {
    await cdp.send('Emulation.setEmulatedMedia',
      { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] }, sessionId);
  }
  if (saveData) {
    // Save-Data is a request header; the JS side reads navigator.connection.saveData,
    // so override the property itself before any page script runs.
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `Object.defineProperty(navigator, 'connection',
                 { get: () => ({ saveData: true, effectiveType: '4g' }), configurable: true });`,
    }, sessionId);
  }

  await cdp.send('Page.navigate', { url: ORIGIN + '/index.html' }, sessionId);
  await sleep(settle); // module graph, dynamic import and requestIdleCallback

  const evaluate = async (expr) => {
    const r = await cdp.send('Runtime.evaluate',
      { expression: expr, returnByValue: true, awaitPromise: true }, sessionId);
    return r.result.value;
  };
  const scenery = requests.filter((u) => /land[234]\.webp/.test(u));
  const state = await evaluate(`(${() => ({
    noGl: document.documentElement.classList.contains('no-gl'),
    glReady: document.documentElement.classList.contains('gl-ready'),
    hasDoorApi: typeof window.__waypointDoor !== 'undefined',
    posterPainted: (() => {
      const el = document.querySelector('.doorstage__poster');
      if (!el) return false;
      const cs = getComputedStyle(el);
      return cs.opacity !== '0' && cs.display !== 'none';
    })(),
  })})()`);

  await cdp.send('Target.closeTarget', { targetId });
  return { requests, three: requests.filter((u) => THREE_RE.test(u)), scenery,
           consoleErrors, ...state };
}

/* Both loops on this page must come to rest, and must come back when scrolled.
 *
 * A headless tab reports itself hidden and fires no frames of its own, which
 * is why both loops expose a probe instead of being observed from outside.
 * Scrolling here is a real wheel event through CDP, not scrollTo — Lenis
 * intercepts wheel input, and scrollTo would bypass the very path under test. */
async function idleLoops(cdp) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  await cdp.send('Page.enable', {}, sessionId);
  await cdp.send('Emulation.setDeviceMetricsOverride',
    { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
  await cdp.send('Page.navigate', { url: ORIGIN + '/index.html' }, sessionId);
  await sleep(2500);

  const evaluate = async (expr) => (await cdp.send('Runtime.evaluate',
    { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

  const probes = await evaluate(`({
    scroll: typeof window.__waypointProbe === 'function' ? window.__waypointProbe() : null,
    lenis:  typeof window.__waypointLenisProbe === 'function' ? window.__waypointLenisProbe() : null,
  })`);

  if (probes.scroll) ok('scroll loop exposes a probe');
  else bad('scroll loop has no probe — its idling cannot be verified');
  if (probes.lenis) ok('Lenis loop exposes a probe');
  else bad('Lenis loop has no probe — __waypointLenisProbe is gone, so whether '
         + 'it idles is unobservable and the next edit can restore the forever-loop unnoticed');

  // A headless tab throttles rAF, so drive the settle deterministically rather
  // than waiting on frames that may never come.
  await evaluate(`(async () => {
    for (let i = 0; i < 40; i++) { if (window.__waypointTick) window.__waypointTick();
      await new Promise(r => setTimeout(r, 25)); }
  })()`);
  const rest = await evaluate(`({
    scrollBusy: window.__waypointProbe ? window.__waypointProbe().busy : null,
    lenisLooping: window.__waypointLenisProbe ? window.__waypointLenisProbe().looping : null,
  })`);

  if (rest.scrollBusy === false) ok('scroll loop reports idle once nothing is moving');
  else bad(`scroll loop never settles (busy=${rest.scrollBusy}) — it is drawing while the reader reads`);
  if (rest.lenisLooping === false) ok('Lenis loop stops when no scroll is animating');
  else bad('Lenis loop is still running with nothing to scroll — the unconditional rAF is back');

  // and it must actually wake: a real wheel gesture has to move the page
  const before = await evaluate('window.scrollY');
  await cdp.send('Input.dispatchMouseEvent',
    { type: 'mouseWheel', x: 720, y: 450, deltaX: 0, deltaY: 600 }, sessionId);
  await sleep(900);
  const after = await evaluate('window.scrollY');
  if (after > before) ok(`a wheel gesture still scrolls (${before} to ${Math.round(after)})`);
  else bad(`a wheel gesture no longer scrolls (stuck at ${before}) — gating the Lenis `
         + 'loop broke the thing it was gating');

  await cdp.send('Target.closeTarget', { targetId });
}

/* Motion that only a pointer can prove.
 *
 * check.py can read that a rule says `scale:var(--press)` under :active; it
 * cannot read whether :active ever fires, whether the press lands on the
 * element under the finger rather than the card around it, whether a hover
 * lift is really absent on a touch screen, or whether a smooth scroll asked
 * for in script honours the reader's setting. These drive the real thing.
 * MOTION.md explains each rule; this only asks whether the browser agrees. */
async function motion(cdp) {
  const open = async (page, { width = 1440, height = 900, mobile = false, touch = false,
                              reduced = false, settle = 2200 } = {}) => {
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    await cdp.send('Page.enable', {}, sessionId);
    await cdp.send('Emulation.setDeviceMetricsOverride',
      { width, height, deviceScaleFactor: 1, mobile }, sessionId);
    if (touch) await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }, sessionId);
    await cdp.send('Emulation.setEmulatedMedia', { features: [
      { name: 'prefers-reduced-motion', value: reduced ? 'reduce' : 'no-preference' }] }, sessionId);
    await cdp.send('Page.navigate', { url: ORIGIN + '/' + page }, sessionId);
    await sleep(settle);
    const evaluate = async (expr) => (await cdp.send('Runtime.evaluate',
      { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;
    const mouse = (type, x, y) => cdp.send('Input.dispatchMouseEvent',
      { type, x, y, button: 'left', clickCount: 1 }, sessionId);
    /* Press the middle of the first visible match and report the computed
       `scale` while held, then after release. Scrolled into view only if it
       is not already (scrolling the hero would scroll it away; the directory
       centres instead, or the sticky bar takes the press), and released
       where it was pressed: dragging off a link starts a native drag that
       swallows every press after it. Clicks are cancelled and stopped, so
       neither the browser nor the page's own handlers (script.js glides to
       any #anchor it sees clicked) act on a test press. */
    const press = async (sel, block = 'nearest') => {
      const at = await evaluate(`(() => { const e = [...document.querySelectorAll(${JSON.stringify(sel)})]
          .find((n) => n.getClientRects().length); if (!e) return null;
        if (!window.__noFollow) { window.__noFollow = 1;
          document.addEventListener('click', (ev) => { ev.preventDefault(); ev.stopImmediatePropagation(); }, true); }
        e.scrollIntoView({ block: ${JSON.stringify(block)}, behavior: 'instant' }); const r = e.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
      if (!at) return null;
      await sleep(150);
      await mouse('mouseMoved', at.x, at.y);
      await mouse('mousePressed', at.x, at.y);
      await sleep(260);
      const held = await evaluate(`(() => { const e = document.elementFromPoint(${at.x}, ${at.y});
        const t = e && e.closest(${JSON.stringify(sel)}); return t ? getComputedStyle(t).scale : 'missed'; })()`);
      await mouse('mouseReleased', at.x, at.y);
      await mouse('mouseMoved', 2, 2);
      await sleep(260);
      const after = await evaluate(`(() => { const e = [...document.querySelectorAll(${JSON.stringify(sel)})]
          .find((n) => n.getClientRects().length); return e ? getComputedStyle(e).scale : null; })()`);
      return { held, after };
    };
    const close = () => cdp.send('Target.closeTarget', { targetId });
    return { evaluate, mouse, press, close, sessionId };
  };

  // 1. the press, on both halves, on the controls a reader actually presses
  const desk = await open('index.html');
  for (const [sel, want] of [['.hero__cta .btn--solid', '0.97'], ['.hero__cta .tlink', '0.97']]) {
    const r = await desk.press(sel);
    if (r && r.held === want && (r.after === 'none' || r.after === '1')) ok(`press: ${sel} gives to ${want} and comes back`);
    else bad(`press: ${sel} held at ${r && r.held}, released at ${r && r.after} (wanted ${want}, then none)`);
  }
  // the first frame arrives on a desk, and the lamp travels on transform
  const deskState = await desk.evaluate(`(() => {
    const META = ['offset', 'easing', 'composite', 'computedOffset'];
    const looping = document.getAnimations().filter((a) => a.playState === 'running' && a.animationName);
    const offMain = looping.flatMap((a) => a.effect.getKeyframes().flatMap((k) => Object.keys(k)))
      .filter((k) => !META.includes(k) && !['transform', 'opacity', 'filter', 'translate', 'scale', 'rotate'].includes(k));
    const h = document.getElementById('work'); scrollTo(0, h.offsetTop); window.__waypointTick && window.__waypointTick();
    const lamp = document.getElementById('navLamp');
    const stillLooping = document.getAnimations()
      .filter((a) => a.playState === 'running' && a.effect.getTiming().iterations === Infinity)
      .map((a) => a.animationName);
    const entrance = ['.hero__eye', '.hero__l', '.hero__r', '.hero__foot', '.hero__cue']
      .filter((s) => getComputedStyle(document.querySelector(s)).animationName === 'hero-in').length;
    const rail = [...document.querySelectorAll('.rail button')].map((b) => b.getAttribute('aria-label') || '');
    return { entrance, rail, running: looping.length, offMain,
             stillLooping, lampLeft: lamp.style.left, lampTransform: lamp.style.transform }; })()`);
  if (deskState.running && !deskState.offMain.length) ok(`desktop: the ${deskState.running} keyframe animation(s) running at the door are compositor-only`);
  else bad(`desktop: a running animation animates ${deskState.offMain.join(', ') || 'nothing measurable'} on the main thread`);
  if (!deskState.stillLooping.length) ok('desktop: past the door, nothing loops');
  else bad(`desktop: still looping past the door: ${deskState.stillLooping.join(', ')}`);
  if (deskState.rail.length && deskState.rail.every((n) => n && !/^Go to part/.test(n))) ok(`desktop: all ${deskState.rail.length} rail diamonds are named for their scenes`);
  else bad(`desktop: rail diamonds without a scene name: ${deskState.rail.filter((n) => !n || /^Go to part/.test(n)).length} of ${deskState.rail.length}`);
  if (deskState.entrance === 5) ok('desktop: the hero arrives in reading order (5 staggered entrances)');
  else bad(`desktop: expected 5 hero-in entrances, found ${deskState.entrance}`);
  if (/translate\(/.test(deskState.lampTransform) && !deskState.lampLeft) ok('the nav lamp travels on transform, not left');
  else bad(`the nav lamp is positioned by left="${deskState.lampLeft}" transform="${deskState.lampTransform}"`);
  await desk.close();

  const dir = await open('help.html');
  for (const [sel, want] of [['.sos__list a', '0.985'], ['.fev__card', '0.985'], ['.pv__call', '0.97'],
                             ['.langbar__list a', '0.97'], ['.jump a', '0.97']]) {
    const r = await dir.press(sel, 'center');
    if (r && r.held === want) ok(`press: ${sel} gives to ${want}`);
    else bad(`press: ${sel} held at ${r && r.held} (wanted ${want}) — either :active never reached it or the rule is gone`);
  }
  await dir.close();
  const cat = await open('help-food.html');
  {
    const r = await cat.press('.r__do .call', 'center');
    if (r && r.held === '0.97') ok('press: the Call button gives under the press');
    else bad(`press: the Call button held at ${r && r.held}; the most important tap target on the site gives no feedback`);
    // :active climbs to ancestors, which is why only leaves are pressable: the
    // card around a pressed Call button must not sink with it
    const card = await cat.evaluate(`getComputedStyle(document.querySelector('.r')).scale`);
    if (card === 'none' || card === '1') ok('press: a resource card does not sink when a button inside it is pressed');
    else bad(`press: the resource card scaled to ${card} under a press on its own button`);
  }
  await cat.close();

  // 2. a touch screen gets no hover motion and no blur on the way in
  const phone = await open('help.html', { width: 390, height: 844, mobile: true, touch: true });
  const touchState = await phone.evaluate(`(() => {
    const a = document.querySelector('.sos__list a'); const r = a.getBoundingClientRect();
    return { fine: matchMedia('(hover: hover) and (pointer: fine)').matches, x: r.left + 20, y: r.top + 20 }; })()`);
  if (!touchState.fine) ok('touch profile reports no fine hovering pointer');
  else bad('touch emulation still reports (hover:hover) and (pointer:fine); the hover checks below prove nothing');
  await phone.mouse('mouseMoved', touchState.x, touchState.y);
  await sleep(300);
  const lift = await phone.evaluate(`getComputedStyle(document.querySelector('.sos__list a')).transform`);
  if (lift === 'none') ok('touch: an emergency number does not lift under a hover it cannot have');
  else bad(`touch: the emergency number lifts on hover (${lift}); on a phone it sticks after the tap`);
  await phone.close();

  // 3. the far side of the door: on the poster path the slit is dimmed under
  //    the closing line
  const close = await open('index.html', { width: 390, height: 844, mobile: true });
  const glow = await close.evaluate(`(async () => {
    const c = document.getElementById('close');
    scrollTo(0, c.offsetTop + c.offsetHeight / 2 - innerHeight / 2);
    for (let i = 0; i < 8; i++) { window.__waypointTick && window.__waypointTick(); await new Promise((r) => setTimeout(r, 30)); }
    return { closing: document.documentElement.classList.contains('closing'),
             glow: +getComputedStyle(document.querySelector('.poster__glow')).opacity,
             entrance: ['.hero__eye', '.hero__l', '.hero__r', '.hero__foot', '.hero__cue']
               .filter((s) => getComputedStyle(document.querySelector(s)).animationName === 'hero-in').length }; })()`);
  if (glow.closing && glow.glow <= 0.3) ok(`phone: the closing door's slit is dimmed (${glow.glow}) behind the last line`);
  else bad(`phone: closing=${glow.closing}, slit opacity ${glow.glow}; the closing line sits on a bright slit again`);
  if (glow.entrance === 0) ok('phone: no hero entrance (Speed Index is the phone\'s budget)');
  else bad(`phone: ${glow.entrance} hero entrances run on a phone`);
  await close.close();

  // 4. scrolling asked for in script honours reduced motion
  for (const reduced of [true, false]) {
    const p = await open('help.html', { reduced });
    const r = await p.evaluate(`(async () => {
      const t = document.querySelector('.fev__track'), b = document.querySelector('[data-fev="next"]');
      if (!t || !b) return null;
      t.scrollIntoView({ block: 'center', behavior: 'instant' });
      b.click(); await new Promise((r) => setTimeout(r, 40));
      const early = t.scrollLeft; await new Promise((r) => setTimeout(r, 900));
      return { early, late: t.scrollLeft }; })()`);
    if (!r) { bad('carousel: no featured-events track to test'); await p.close(); continue; }
    if (reduced && r.early > 0 && Math.abs(r.early - r.late) < 2) ok('reduced motion: the carousel arrow jumps, it does not glide');
    else if (reduced) bad(`reduced motion: the carousel still glides (${r.early}px at 40ms, ${r.late}px settled)`);
    else if (r.late > 0) ok(`no preference: the carousel still scrolls (${Math.round(r.late)}px)`);
    else bad('no preference: the carousel arrow no longer scrolls at all');
    await p.close();
  }
}

/* Contrast against the ground that is actually there.
 *
 * Two lines on index.html sit on light no stylesheet describes: the hero on a
 * live WebGL door (or its CSS poster), the closing line on the poster's slit.
 * A contrast check that reads a background colour finds nothing to read. So
 * render the headline three times (whole, italic transparent, all transparent),
 * diff the renders to find the pixels each kind of glyph covers, and compare
 * the declared text colour with the composited pixel behind every one of
 * them. Text-shadow is switched off for all three: it is part of how the text
 * is drawn, not part of the ground, and earns nothing here, correctly.
 *
 * The limits are the measured values in styles.css's comments. The one
 * allowance is the desktop hero, where the gold italic of "No one" sits on
 * the slit's white-hot core for under 1% of its pixels: no scrim light enough
 * to keep the door clears that without darkening the door itself. */
async function contrast(cdp) {
  const MEASURE = (a, b, c, roman, em) => `(async () => {
    const load = (src) => new Promise((r) => { const i = new Image(); i.onload = () => r(i); i.src = src; });
    const [A, B, C] = await Promise.all([load('${a}'), load('${b}'), load('${c}')]);
    const W = A.width, H = A.height;
    const px = (img) => { const cv = new OffscreenCanvas(W, H), g = cv.getContext('2d'); g.drawImage(img, 0, 0); return g.getImageData(0, 0, W, H).data; };
    const pa = px(A), pb = px(B), pc = px(C);
    const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const L = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
    const ratio = (x, y) => (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
    const te = L(...${JSON.stringify(em)}), tr = L(...${JSON.stringify(roman)});
    const out = { em: [0, 0, 99], roman: [0, 0, 99] };   // [pixels, under 3:1, worst]
    for (let i = 0; i < pa.length; i += 4) {
      const dEm = Math.abs(pa[i] - pb[i]) + Math.abs(pa[i + 1] - pb[i + 1]) + Math.abs(pa[i + 2] - pb[i + 2]);
      const dRo = Math.abs(pb[i] - pc[i]) + Math.abs(pb[i + 1] - pc[i + 1]) + Math.abs(pb[i + 2] - pc[i + 2]);
      const k = dEm > 60 ? 'em' : dRo > 60 ? 'roman' : null;
      if (!k) continue;
      const r = ratio(k === 'em' ? te : tr, L(pc[i], pc[i + 1], pc[i + 2]));
      out[k][0]++; if (r < 3) out[k][1]++; if (r < out[k][2]) out[k][2] = r;
    }
    return out; })()`;
  const cases = [
    // [label, where, selector, width, height, max % of italic pixels under 3:1]
    ['hero', 'top', '.hero__head', 1440, 900, 1.5],
    ['hero', 'top', '.hero__head', 390, 844, 0],
    ['hero', 'top', '.hero__head', 320, 640, 0],
    ['closing line', 'close', '#close .phrase', 1440, 900, 0],
    ['closing line', 'close', '#close .phrase', 768, 1024, 0],
    ['closing line', 'close', '#close .phrase', 390, 844, 0],
    ['closing line', 'close', '#close .phrase', 375, 667, 0],
    ['closing line', 'close', '#close .phrase', 320, 640, 0],
  ];
  for (const [label, where, sel, width, height, allowEm] of cases) {
    const mobile = width < 900;
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    const evaluate = async (expr) => (await cdp.send('Runtime.evaluate',
      { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;
    await cdp.send('Page.enable', {}, sessionId);
    await cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile }, sessionId);
    await cdp.send('Page.navigate', { url: ORIGIN + '/index.html' }, sessionId);
    await sleep(2600);
    const y = await evaluate(`(async () => {
      if (${JSON.stringify(where)} === 'close') { const c = document.getElementById('close');
        scrollTo(0, c.offsetTop + c.offsetHeight / 2 - innerHeight / 2); }
      for (let i = 0; i < 10; i++) { window.__waypointTick && window.__waypointTick(); await new Promise((r) => setTimeout(r, 40)); }
      // the hero's entrance has to be over, and the door has to hold still
      document.getAnimations().forEach((a) => { try { a.finish(); } catch (e) {} });
      const d = window.__waypointDoor; if (d) { d.live(false); d.set = () => {}; d.live = () => {}; }
      return scrollY; })()`);
    await sleep(900);
    const box = await evaluate(`(() => { const e = document.querySelector(${JSON.stringify(sel)}), r = e.getBoundingClientRect();
      const rgb = (s) => s.match(/[\\d.]+/g).slice(0, 3).map(Number), em = e.querySelector('em');
      return { x: Math.max(0, r.left - 4), y: Math.max(0, r.top - 4), w: Math.min(innerWidth, r.width + 8),
               h: Math.min(innerHeight - Math.max(0, r.top - 4), r.height + 8),
               roman: rgb(getComputedStyle(e).color), em: rgb(getComputedStyle(em || e).color) }; })()`);
    const clip = { x: box.x, y: box.y + y, width: box.w, height: box.h, scale: 1 };
    const css = (extra) => evaluate(`(() => { let s = document.getElementById('__glyph'); if (!s) { s = document.createElement('style');
      s.id = '__glyph'; document.head.appendChild(s); } s.textContent = ${JSON.stringify(`${sel}, ${sel} *{ text-shadow:none !important; transition:none !important; }`)} + ${JSON.stringify(extra)}; return true; })()`);
    const snap = async () => 'data:image/png;base64,' + (await cdp.send('Page.captureScreenshot', { format: 'png', clip }, sessionId)).data;
    await css(''); await sleep(200); const a = await snap();
    await css(`${sel} em{ color:transparent !important; }`); await sleep(200); const b = await snap();
    await css(`${sel}, ${sel} *{ color:transparent !important; }`); await sleep(200); const c = await snap();
    const r = await evaluate(MEASURE(a, b, c, box.roman, box.em));
    await cdp.send('Target.closeTarget', { targetId });
    const pct = (k) => (r[k][0] ? (100 * r[k][1] / r[k][0]) : 0);
    const tag = `${label} at ${width}x${height}`;
    if (!r.em[0] || !r.roman[0]) { bad(`contrast: ${tag} found no glyphs to measure; the selector or the diff stopped seeing the type`); continue; }
    if (pct('roman') === 0) ok(`contrast: ${tag}, roman never under 3:1 (worst ${r.roman[2].toFixed(2)})`);
    else bad(`contrast: ${tag}, ${pct('roman').toFixed(1)}% of roman glyph pixels under 3:1, worst ${r.roman[2].toFixed(2)}:1`);
    if (pct('em') <= allowEm) ok(`contrast: ${tag}, italic ${pct('em').toFixed(1)}% under 3:1 (allowed ${allowEm}%, worst ${r.em[2].toFixed(2)})`);
    else bad(`contrast: ${tag}, ${pct('em').toFixed(1)}% of italic glyph pixels under 3:1 (allowed ${allowEm}%), worst ${r.em[2].toFixed(2)}:1`);
  }
}

/* The Find help menu, driven the way a reader drives it.
 *
 * check.py can read that every English header carries the same <details>; it
 * cannot read whether the panel fits a 320px screen, whether Escape gives the
 * keyboard its place back, or whether "Search for help" really leaves the
 * cursor in the box, from another page and from this one. */
async function findHelp(cdp) {
  const open = async (page, { width = 1440, height = 900, mobile = false, noScript = false } = {}) => {
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    await cdp.send('Page.enable', {}, sessionId);
    await cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile }, sessionId);
    if (noScript) await cdp.send('Emulation.setScriptExecutionDisabled', { value: true }, sessionId);
    await cdp.send('Page.navigate', { url: ORIGIN + '/' + page }, sessionId);
    await sleep(2200);
    const evaluate = async (expr) => (await cdp.send('Runtime.evaluate',
      { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;
    const click = async (x, y) => {
      for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
        await cdp.send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 }, sessionId);
    };
    const centre = (sel) => evaluate(`(() => { const e = document.querySelector(${JSON.stringify(sel)});
      if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
    const press = async (sel) => { const c = await centre(sel); if (c) await click(c.x, c.y); await sleep(350); return !!c; };
    const key = async (k) => {
      for (const type of ['keyDown', 'keyUp'])
        await cdp.send('Input.dispatchKeyEvent', { type, key: k, code: k, windowsVirtualKeyCode: k === 'Escape' ? 27 : 0 }, sessionId);
      await sleep(200);
    };
    const state = () => evaluate(`(() => { const d = document.querySelector('.findmenu'), l = d && d.querySelector('.findmenu__list');
      const r = l && d.open ? l.getBoundingClientRect() : null;
      return { open: !!(d && d.open), right: r ? r.right : 0, left: r ? r.left : 0,
               items: l ? [...l.querySelectorAll('a')].filter((a) => a.getClientRects().length).map((a) => a.textContent) : [],
               active: document.activeElement && (document.activeElement.id || document.activeElement.tagName.toLowerCase()),
               page: location.pathname + location.hash, sideways: document.documentElement.scrollWidth - innerWidth }; })()`);
    return { evaluate, click, press, key, state, sessionId, close: () => cdp.send('Target.closeTarget', { targetId }) };
  };

  // 1. it opens, offers all three, and gives the keyboard its place back
  let p = await open('index.html');
  await p.press('.findmenu > summary');
  let s = await p.state();
  if (s.open && s.items.join('|') === 'Search for help|What do you need help with?|Featured events')
    ok('find help: the pill opens a menu of the three ways in, in order');
  else bad(`find help: open=${s.open}, items=${JSON.stringify(s.items)}`);
  await p.key('Escape');
  s = await p.state();
  if (!s.open && s.active === 'summary') ok('find help: Escape closes it and leaves focus on the pill');
  else bad(`find help: after Escape open=${s.open}, focus on ${s.active}`);
  await p.press('.findmenu > summary');
  await p.click(700, 600);
  await sleep(250);
  s = await p.state();
  if (!s.open) ok('find help: a click anywhere else closes it');
  else bad('find help: the menu stays open over the page after a click elsewhere');
  // opened from the keyboard it appears without an entrance, and stays that
  // way as Tab walks into the list
  await p.evaluate("document.querySelector('.findmenu > summary').focus(); true");
  for (const [k, code, vk, text] of [['Enter', 'Enter', 13, '\r'], ['Tab', 'Tab', 9], ['Tab', 'Tab', 9]]) {
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code, windowsVirtualKeyCode: vk, text }, p.sessionId);
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk }, p.sessionId);
    await sleep(120);
  }
  const keyed = await p.evaluate(`({ open: document.querySelector('.findmenu').open,
    anim: getComputedStyle(document.querySelector('.findmenu__list')).animationName,
    at: document.activeElement.textContent.trim() })`);
  if (keyed.open && keyed.anim === 'none' && keyed.at === 'What do you need help with?')
    ok('find help: opened from the keyboard it appears without an entrance, and Tab walks the list');
  else bad(`find help: keyboard open=${keyed.open}, animation=${keyed.anim}, focus on "${keyed.at}"`);
  await p.key('Escape');
  // 2. from another page, search arrives with the cursor in the box
  await p.press('.findmenu > summary');
  await p.press('.findmenu__search a');
  await sleep(2400);
  s = await p.state();
  if (/^\/help(\.html)?#search$/.test(s.page) && s.active === 'q') ok('find help: from the narrative page, search arrives with the cursor in the box');
  else bad(`find help: Search for help landed on ${s.page} with focus on ${s.active}`);
  await p.close();

  // 3. on the directory itself: no page load, focus in the box, menu closed
  p = await open('help.html');
  await p.evaluate('window.__samePage = 1');
  await p.press('.findmenu > summary');
  await p.press('.findmenu__search a');
  s = await p.state();
  const stayed = await p.evaluate('window.__samePage === 1');
  if (stayed && s.active === 'q' && !s.open) ok('find help: on the directory, search focuses the box in place, with no page load');
  else bad(`find help: on help.html stayed=${stayed}, focus=${s.active}, open=${s.open}`);
  // 4. the other two land below the sticky bar, and the menu gets out of the way
  for (const [item, id] of [['a[href="help.html#needs"]', 'needs'], ['a[href="help.html#featured"]', 'featured']]) {
    await p.evaluate('scrollTo(0, 0); true');
    await p.press('.findmenu > summary');
    await p.press(`.findmenu__list ${item}`);
    await sleep(900);
    const land = await p.evaluate(`(() => { const t = document.getElementById('${id}'), h = document.querySelector('.sitehead');
      return { top: Math.round(t.getBoundingClientRect().top), bar: Math.round(h.getBoundingClientRect().bottom),
               open: document.querySelector('.findmenu').open }; })()`);
    if (!land.open && land.top >= land.bar - 2 && land.top < land.bar + 120)
      ok(`find help: "${id}" lands just below the bar (${land.top}px, bar ends ${land.bar}px)`);
    else bad(`find help: "${id}" landed at ${land.top}px against a bar ending at ${land.bar}px, menu open=${land.open}`);
  }
  await p.close();

  // 5. the narrowest screen: the panel fits, and nothing scrolls sideways
  p = await open('help.html', { width: 320, height: 640, mobile: true });
  await p.press('.findmenu > summary');
  s = await p.state();
  if (s.open && s.left >= 0 && s.right <= 320 && s.sideways <= 0) ok(`find help: at 320px the panel fits (${Math.round(s.left)} to ${Math.round(s.right)}px)`);
  else bad(`find help: at 320px the panel runs ${Math.round(s.left)} to ${Math.round(s.right)}px, page ${s.sideways}px wider than the screen`);
  await p.close();

  // 6. no script: it still opens, and offers no search it cannot run
  p = await open('help.html', { noScript: true });
  await p.press('.findmenu > summary');
  s = await p.state();
  if (s.open && s.items.join('|') === 'What do you need help with?|Featured events')
    ok('find help: with scripts off it still opens, without the search it could not run');
  else bad(`find help: with scripts off open=${s.open}, items=${JSON.stringify(s.items)}`);
  await p.close();
}

/* -------------------------------------------------------------------- main */
(async () => {
  if (!CHROME) { console.error('No Chrome found; skipping browser checks.'); process.exit(0); }

  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'waypoint-door-'));
  const chrome = spawn(CHROME, [
    '--headless=new', '--remote-debugging-port=0', '--no-first-run', '--no-default-browser-check',
    `--user-data-dir=${userDataDir}`,
    // A real GPU is not available headless; SwiftShader keeps getContext('webgl')
    // truthful so webglOK() reflects the gate under test, not the sandbox.
    '--enable-unsafe-swiftshader',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });

  const wsUrl = await new Promise((res, rej) => {
    let buf = '';
    const t = setTimeout(() => rej(new Error('Chrome did not report a debugger URL')), 15000);
    chrome.stderr.on('data', (d) => {
      buf += d;
      const m = buf.match(/ws:\/\/[^\s]+/);
      if (m) { clearTimeout(t); res(m[0]); }
    });
  });

  const cdp = await connect(wsUrl);
  try {
    console.log('runtime budget — what the browser really fetches, and what it keeps doing\n');

    // 1. desktop: the door is the centrepiece, Three is expected
    const desk = await visit(cdp, { width: 1440, height: 900, mobile: false });
    if (desk.three.length) ok(`desktop downloads Three (${desk.three.length} chunks)`);
    else bad('desktop no longer loads Three at all — the WebGL door is gone from the one place it was meant to run');
    if (desk.hasDoorApi) ok('desktop: __waypointDoor is live');
    else bad('desktop: door API missing — the scene never initialised');
    if (!desk.noGl) ok('desktop: not on the poster path');
    else bad('desktop: fell back to the poster; the gate is rejecting a capable machine');

    // 2. phone: the doorstage is hidden after handover, so the bytes are pure waste
    const phone = await visit(cdp, { width: 390, height: 844, mobile: true });
    if (!phone.three.length) ok('phone downloads no Three at all');
    else bad(`phone still downloads Three (${phone.three.length} chunks, ~750KB) — the modulepreload is probably back in index.html`);
    if (phone.noGl) ok('phone: no-gl set, poster stands in');
    else bad('phone: no-gl missing, so the CSS poster is not being shown');
    if (phone.posterPainted) ok('phone: the poster is actually painted');
    else bad('phone: no WebGL and no visible poster — the door area is blank');
    // The gate is the ordinary path on a phone, so taking it must be silent.
    // It used to `throw`, which put an uncaught error in the console of every
    // reader the poster is for and cost a Lighthouse best-practices point.
    if (!phone.consoleErrors.length) ok('phone: nothing logged to the console');
    else bad(`phone: ${phone.consoleErrors.length} console error(s) on the ordinary `
           + `poster path: ${phone.consoleErrors[0].slice(0, 90)}`);
    if (!desk.consoleErrors.length) ok('desktop: nothing logged to the console');
    else bad(`desktop: console error(s): ${desk.consoleErrors[0].slice(0, 90)}`);

    // 3. reduced motion: the scene renders one still frame; the poster IS one
    const still = await visit(cdp, { width: 1440, height: 900, mobile: false, reducedMotion: true });
    if (!still.three.length) ok('reduced-motion downloads no Three');
    else bad('reduced-motion still downloads 750KB to draw a single static frame');
    if (still.posterPainted) ok('reduced-motion: the poster is painted');
    else bad('reduced-motion: nothing is painted where the door should be');

    // 4. Save-Data is an explicit request from the reader, and it governs the
    //    scenery as well as the door — 288KB of aria-hidden backdrop.
    //    settle is past requestIdleCallback's 2500ms timeout, or the scenery
    //    would read as "not loaded" simply for not having got there yet.
    const lite = await visit(cdp,
      { width: 1440, height: 900, mobile: false, saveData: true, settle: 4000 });
    if (!lite.three.length) ok('Save-Data downloads no Three');
    else bad('Save-Data is set and the site still pulls 750KB of decoration');
    if (!lite.scenery.length) ok('Save-Data downloads no extra scenery');
    else bad(`Save-Data still pulls ${lite.scenery.length} landscape layer(s) — `
           + 'loadStages() is ignoring the reader asking for less');

    // the counterpart: on an ordinary connection the scenery must still arrive,
    // or the journey is one flat backdrop for everybody.
    const full = await visit(cdp, { width: 1440, height: 900, mobile: false, settle: 4000 });
    if (full.scenery.length === 3) ok('an ordinary connection still gets all three layers');
    else bad(`only ${full.scenery.length}/3 landscape layers loaded on a normal `
           + 'connection — the scroll journey has lost its backdrop');

    // 5. nothing may still be drawing once the reader stops
    await idleLoops(cdp);
    // 6. the press, the hover gate, the far side of the door, scripted scrolling
    await motion(cdp);
    // 7. the two headlines that sit on light, measured against that light
    await contrast(cdp);
    // 8. the header's Find help menu, driven by pointer and keyboard
    await findHelp(cdp);

    console.log(`\n${pass} passed, ${fail} failed`);
  } finally {
    try { cdp.ws.close(); } catch {}
    chrome.kill();
    // Chrome is still flushing its cache when kill() returns, so a immediate
    // rmSync races it and throws ENOTEMPTY. Wait for the process to actually
    // be gone, and treat a leftover temp profile as cosmetic either way.
    await new Promise((r) => { chrome.once('exit', r); setTimeout(r, 3000); });
    try { fs.rmSync(userDataDir, { recursive: true, force: true }); } catch {}
  }
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
