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
