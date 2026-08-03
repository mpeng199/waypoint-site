/* ============================================================
   Waypoint — the door
   A real-time WebGL centrepiece: a wall in darkness, a door ajar,
   warm light knifing through the gap, the sunlit valley beyond it.
   Scrolling carries the camera through the opening and hands off
   to the painterly journey.

   Loads after first paint. If WebGL is unavailable, the CSS poster
   underneath is the finished picture and nothing here runs.
   ============================================================ */
import * as THREE from "./vendor/three.module.min.js";

const OPEN_W = 1.9;                 // doorway width
const OPEN_H = 4.4;                 // doorway height
const HALF_W = OPEN_W / 2;          // 0.95 — hinge sits at -HALF_W
const MID_Y = OPEN_H * 0.5;         // vertical centre of the opening
const EYE_Y = 2.05;

const AJAR = 19 * Math.PI / 180;    // how far open at rest
const WIDE = 78 * Math.PI / 180;    // how far open at the threshold
const START_Z = 9.6;                // far enough back that the whole door reads

const canvas = document.getElementById("doorCanvas");
const stage = document.querySelector(".doorstage");
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const coarse = window.matchMedia("(max-width: 900px)").matches;

/* ---------- capability gate: leave the CSS poster in place on failure ---------- */
function webglOK() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (e) { return false; }
}
if (!canvas || !stage || !webglOK()) {
  document.documentElement.classList.add("no-gl");
  throw new Error("waypoint/door: no webgl, poster stands in");
}

/* ---------- renderer ---------- */
const renderer = new THREE.WebGLRenderer({ canvas, antialias: !coarse, powerPreference: "high-performance" });
renderer.setClearColor(0x080f0b, 1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.95;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 120);

/* ---------- materials & geometry ---------- */
const DARK = 0x0e1a13;

// the wall, with the doorway cut out of it, extruded so the opening has a jamb
const wallShape = new THREE.Shape();
wallShape.moveTo(-17, -3); wallShape.lineTo(17, -3); wallShape.lineTo(17, 15); wallShape.lineTo(-17, 15); wallShape.closePath();
const hole = new THREE.Path();
hole.moveTo(-HALF_W, 0); hole.lineTo(HALF_W, 0); hole.lineTo(HALF_W, OPEN_H); hole.lineTo(-HALF_W, OPEN_H); hole.closePath();
wallShape.holes.push(hole);

const wall = new THREE.Mesh(
  new THREE.ExtrudeGeometry(wallShape, { depth: 0.42, bevelEnabled: false }),
  new THREE.MeshStandardMaterial({ color: DARK, roughness: 0.94, metalness: 0.0 })
);
wall.position.z = -0.42;
scene.add(wall);

// raised casing around the opening: this is what makes it read as a door
// in a wall rather than a slot in a void
const casingMat = new THREE.MeshStandardMaterial({ color: 0x16241b, roughness: 0.88 });
const CASE_T = 0.19, CASE_D = 0.16, CX = HALF_W + CASE_T / 2, CY = OPEN_H + CASE_T / 2;
[
  [-CX, OPEN_H / 2, CASE_T, OPEN_H + CASE_T],
  [CX, OPEN_H / 2, CASE_T, OPEN_H + CASE_T],
  [0, CY, OPEN_W + CASE_T * 2, CASE_T],
].forEach(([x, y, w, h]) => {
  // only proud on the approach side: on the way out the door swings the other
  // way, and a casing there would intersect the sweeping panel
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, CASE_D), casingMat);
  m.position.set(x, y, CASE_D / 2);
  scene.add(m);
});

// the door itself, hinged at the left jamb
const hinge = new THREE.Group();
hinge.position.set(-HALF_W, 0, 0);
const panel = new THREE.Mesh(
  new THREE.BoxGeometry(OPEN_W, OPEN_H - 0.04, 0.09),
  new THREE.MeshStandardMaterial({ color: 0x0a1109, roughness: 0.86, metalness: 0.02 })
);
panel.position.set(HALF_W, MID_Y, 0.045);
hinge.add(panel);
scene.add(hinge);

// what is on the other side: the valley, lit
const loader = new THREE.TextureLoader();
const beyond = new THREE.Mesh(
  new THREE.PlaneGeometry(46, 26),
  new THREE.MeshBasicMaterial({ color: 0x1b2a20, toneMapped: false })
);
beyond.position.set(0, 5, -11);
scene.add(beyond);
loader.load("assets/land1.webp", (tex) => {
  tex.colorSpace = THREE.SRGBColorSpace;
  beyond.material.map = tex;
  beyond.material.color.setHex(0xffffff);
  beyond.material.needsUpdate = true;
});

// floor: unlit, so the light behind the wall cannot spill onto it
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(60, 60),
  new THREE.MeshBasicMaterial({ color: 0x080d0a, toneMapped: false })
);
floor.rotation.x = -Math.PI / 2;
scene.add(floor);

// one warm source behind the wall: rakes the jamb and the back of the door,
// leaves everything facing the camera in darkness. No shadow maps needed.
const lamp = new THREE.PointLight(0xffd2a0, 90, 30, 2);
lamp.position.set(0, MID_Y + 0.2, -1.7);
scene.add(lamp);

// the spill: what bounces back onto the wall we are standing in front of.
// Short range, so the wall reads as a surface near the door and falls into dark.
const spill = new THREE.PointLight(0xffd6ab, 16, 9, 2);
spill.position.set(0.5, MID_Y - 0.4, 1.5);
scene.add(spill);
scene.add(new THREE.AmbientLight(0x16221b, 0.75));

/* ---------- shared GLSL: cheap value noise for dust density ---------- */
const NOISE = `
float hash(vec3 p){ p = fract(p*0.3183099 + vec3(0.11,0.17,0.23)); p *= 17.0;
  return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
float vnoise(vec3 x){ vec3 i=floor(x), f=fract(x); f=f*f*(3.0-2.0*f);
  return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x), mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x), f.y),
             mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x), mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x), f.y), f.z); }
`;

/* ---------- the light shaft: layered quads, additive, true volumetric build-up ---------- */
const LAYERS = coarse ? 26 : 54;
const SHAFT_LEN = 9.0;

function shaftGeometry(n) {
  const pos = new Float32Array(n * 6 * 3);
  const q = new Float32Array(n * 6 * 2);
  const az = new Float32Array(n * 6);
  const corners = [[-1, -1], [1, -1], [1, 1], [-1, -1], [1, 1], [-1, 1]];
  let k = 0;
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    for (let c = 0; c < 6; c++) {
      pos[k * 3] = corners[c][0]; pos[k * 3 + 1] = corners[c][1]; pos[k * 3 + 2] = 0;
      q[k * 2] = corners[c][0]; q[k * 2 + 1] = corners[c][1];
      az[k] = t; k++;
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("aQ", new THREE.BufferAttribute(q, 2));
  g.setAttribute("aZ", new THREE.BufferAttribute(az, 1));
  return g;
}

const shaftUniforms = {
  uTime: { value: 0 }, uGapX: { value: 0 }, uGapHW: { value: 0.1 },
  uMidY: { value: MID_Y }, uHalfH: { value: MID_Y }, uIntensity: { value: 0.5 },
  uSpread: { value: 0.52 }, uLen: { value: SHAFT_LEN },
};

const shaft = new THREE.Mesh(shaftGeometry(LAYERS), new THREE.ShaderMaterial({
  uniforms: shaftUniforms,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  vertexShader: `
    attribute vec2 aQ; attribute float aZ;
    uniform float uGapX, uGapHW, uMidY, uHalfH, uSpread, uLen;
    varying vec2 vQ; varying float vZ;
    void main(){
      vQ = aQ; vZ = aZ;
      float grow = 1.0 + uSpread * aZ;
      float hw = max(uGapHW, 0.028) * grow * 1.4;
      float hh = uHalfH * grow;
      float cx = uGapX * (1.0 - 0.28 * aZ);
      vec3 p = vec3(cx + aQ.x * hw, uMidY + aQ.y * hh, aZ * uLen);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
    }`,
  fragmentShader: NOISE + `
    uniform float uTime, uIntensity;
    varying vec2 vQ; varying float vZ;
    void main(){
      float soft = mix(0.10, 0.68, vZ);
      float mx = 1.0 - smoothstep(1.0 - soft, 1.0, abs(vQ.x));
      float my = 1.0 - smoothstep(1.0 - soft * 0.75, 1.0, abs(vQ.y));
      float m = mx * my;
      if (m <= 0.001) discard;
      float depth = pow(1.0 - vZ, 1.55);
      float dust = 0.70 + 0.30 * vnoise(vec3(vQ * 2.6, vZ * 7.0 + uTime * 0.06));
      float a = m * depth * dust * uIntensity;
      gl_FragColor = vec4(vec3(1.0, 0.80, 0.53) * a, a);
    }`,
}));
shaft.renderOrder = 3;
scene.add(shaft);

/* ---------- the pool of light it throws on the floor ---------- */
const poolUniforms = {
  uGapX: { value: 0 }, uGapHW: { value: 0.1 }, uIntensity: { value: 0.5 }, uLen: { value: SHAFT_LEN },
};
const pool = new THREE.Mesh(new THREE.PlaneGeometry(1, 1, 1, 1), new THREE.ShaderMaterial({
  uniforms: poolUniforms,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  vertexShader: `
    uniform float uGapX, uGapHW, uLen;
    varying vec2 vP;
    void main(){
      vP = position.xy + 0.5;                       // 0..1 along width, 0..1 along run
      float grow = 1.0 + 0.95 * vP.y;
      float hw = max(uGapHW, 0.05) * grow * 2.4;
      float cx = uGapX * (1.0 - 0.28 * vP.y);
      vec3 p = vec3(cx + (vP.x - 0.5) * 2.0 * hw, 0.012, vP.y * uLen);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
    }`,
  fragmentShader: `
    uniform float uIntensity;
    varying vec2 vP;
    void main(){
      float x = abs(vP.x - 0.5) * 2.0;
      float mx = 1.0 - smoothstep(0.35, 1.0, x);
      float my = pow(1.0 - vP.y, 2.1);
      float a = mx * my * uIntensity * 0.62;
      gl_FragColor = vec4(vec3(1.0, 0.79, 0.52) * a, a);
    }`,
}));
pool.frustumCulled = false;
pool.renderOrder = 2;
scene.add(pool);

/* ---------- bloom at the opening itself ---------- */
const glow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.ShaderMaterial({
  uniforms: { uIntensity: { value: 0.2 }, uW: { value: 0.5 }, uH: { value: 5.4 } },
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `
    uniform float uW, uH; varying vec2 vUv;
    void main(){ vUv = uv;
      vec3 p = vec3(position.x * uW, position.y * uH, 0.0);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }`,
  fragmentShader: `
    uniform float uIntensity; varying vec2 vUv;
    void main(){
      vec2 d = (vUv - 0.5) * vec2(4.4, 1.9);
      float a = exp(-dot(d,d) * 2.8) * uIntensity;
      if (a <= 0.002) discard;
      gl_FragColor = vec4(vec3(1.0, 0.85, 0.62) * a, a);
    }`,
}));
glow.position.set(0, MID_Y, -0.05);
glow.renderOrder = 1;
scene.add(glow);

/* ---------- dust in the beam ---------- */
const MOTES = coarse ? 260 : 900;
const mPos = new Float32Array(MOTES * 3);
const mSeed = new Float32Array(MOTES);
for (let i = 0; i < MOTES; i++) {
  mPos[i * 3] = (Math.random() - 0.5) * 5.2;
  mPos[i * 3 + 1] = Math.random() * 6.2;
  mPos[i * 3 + 2] = Math.random() * SHAFT_LEN;
  mSeed[i] = Math.random();
}
const moteGeo = new THREE.BufferGeometry();
moteGeo.setAttribute("position", new THREE.BufferAttribute(mPos, 3));
moteGeo.setAttribute("aSeed", new THREE.BufferAttribute(mSeed, 1));
const moteUniforms = {
  uTime: { value: 0 }, uGapX: { value: 0 }, uGapHW: { value: 0.1 },
  uMidY: { value: MID_Y }, uIntensity: { value: 0.5 }, uSize: { value: coarse ? 46 : 62 },
};
const motes = new THREE.Points(moteGeo, new THREE.ShaderMaterial({
  uniforms: moteUniforms,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `
    attribute float aSeed;
    uniform float uTime, uGapX, uGapHW, uMidY, uIntensity, uSize;
    varying float vA;
    void main(){
      vec3 p = position;
      p.y = mod(p.y + uTime * (0.045 + aSeed * 0.07), 6.2);
      p.x += sin(uTime * 0.30 + aSeed * 25.0) * 0.14;
      float grow = 1.0 + 0.85 * (p.z / ${SHAFT_LEN.toFixed(1)});
      float hw = max(uGapHW, 0.03) * grow * 1.6;
      float cx = uGapX * (1.0 - 0.28 * (p.z / ${SHAFT_LEN.toFixed(1)}));
      float inX = 1.0 - smoothstep(hw * 0.55, hw * 1.5, abs(p.x - cx));
      float inY = 1.0 - smoothstep(1.7, 3.3, abs(p.y - uMidY));
      float depth = pow(1.0 - clamp(p.z / ${SHAFT_LEN.toFixed(1)}, 0.0, 1.0), 1.3);
      vA = inX * inY * depth * uIntensity * (0.35 + aSeed * 0.65);
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      gl_PointSize = uSize * (0.5 + aSeed) / max(-mv.z, 0.6);
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: `
    varying float vA;
    void main(){
      float d = length(gl_PointCoord - 0.5);
      float a = (1.0 - smoothstep(0.16, 0.5, d)) * vA;
      if (a <= 0.002) discard;
      gl_FragColor = vec4(vec3(1.0, 0.86, 0.63) * a, a);
    }`,
}));
motes.frustumCulled = false;
motes.renderOrder = 4;
scene.add(motes);

/* ============================================================
   State: `t` runs 0 (at rest, door ajar) to 1 (through the opening).
   `mode` is "in" for the hero and "out" for the closing bookend,
   where the camera stands on the lit side and looks back into the dark.
   ============================================================ */
let t = 0, tShown = -1, mode = "in", modeShown = "";
let px = 0, py = 0, pxTarget = 0, pyTarget = 0;
let running = false, visible = true;

const lerp = (a, b, k) => a + (b - a) * k;
const clamp01 = (v) => v < 0 ? 0 : v > 1 ? 1 : v;
/* the walk toward a door: unhurried at first, then the threshold arrives fast */
const approach = (v) => Math.pow(v, 1.9);

function applyMode() {
  if (mode === modeShown) return;
  modeShown = mode;
  if (mode === "out") {
    // standing in the light now, looking back into the dark you came from
    beyond.material.map = null;
    beyond.material.color.setHex(0x070c09);
    beyond.material.needsUpdate = true;
    // the camera now stands on the far side (negative z), so the light has to
    // stand there with it, or we are looking at an unlit wall
    // a warm source off to one side of the room you are now standing in:
    // raking light, so the wall has a gradient instead of a flat fill
    lamp.position.set(-3.8, 1.6, -5.2);
    spill.position.set(3.0, MID_Y + 1.6, -6.4);
    spill.intensity = 22;
    shaft.visible = false; pool.visible = false; glow.visible = false;
  } else {
    lamp.position.set(0, MID_Y + 0.2, -1.7);
    spill.position.set(0.5, MID_Y - 0.4, 1.5);
    spill.intensity = 16;
    shaft.visible = true; pool.visible = true; glow.visible = true;
    if (beyond.userData.tex) {
      beyond.material.map = beyond.userData.tex;
      beyond.material.color.setHex(0xffffff);
    }
    beyond.material.needsUpdate = true;
  }
}
loader.manager.onLoad = () => { beyond.userData.tex = beyond.material.map; };

function renderOnce(now) {
  const time = now * 0.001;

  const e = approach(t);
  const inMode = mode === "in";
  const angle = inMode ? lerp(AJAR, WIDE, Math.pow(t, 0.75)) : lerp(58, 70, t) * Math.PI / 180;
  // always swings toward whichever side the camera is on: the light gets past it
  // on the way in, and the lit face of the panel is what you see on the way out
  hinge.rotation.y = inMode ? -angle : angle;

  // the gap a hinged door actually leaves: latch side, widening as it swings
  const cosA = Math.cos(angle);
  const gapHW = Math.max(0.02, HALF_W * (1 - cosA));
  const gapX = HALF_W * cosA;

  const glowT = inMode ? t : 1 - t * 0.55;
  const beam = inMode ? lerp(0.38, 1.2, Math.pow(t, 0.8)) : lerp(0.30, 0.62, t);

  shaftUniforms.uTime.value = time;
  shaftUniforms.uGapX.value = gapX; shaftUniforms.uGapHW.value = gapHW;
  shaftUniforms.uIntensity.value = beam;
  poolUniforms.uGapX.value = gapX; poolUniforms.uGapHW.value = gapHW;
  poolUniforms.uIntensity.value = beam;
  moteUniforms.uTime.value = time; moteUniforms.uGapX.value = gapX;
  moteUniforms.uGapHW.value = gapHW; moteUniforms.uIntensity.value = beam;
  glow.position.x = gapX;
  glow.material.uniforms.uW.value = Math.max(gapHW, 0.05) * 3.4;
  glow.material.uniforms.uIntensity.value = inMode ? lerp(0.55, 1.25, glowT) : 0.22;
  lamp.intensity = inMode ? lerp(78, 150, t) : lerp(150, 230, t);
  // the world beyond only resolves as you get close to it
  if (inMode && beyond.material.map) beyond.material.color.setScalar(lerp(0.52, 1.0, Math.pow(t, 0.7)));

  // pointer parallax, damped
  px = lerp(px, pxTarget, 0.055); py = lerp(py, pyTarget, 0.055);

  if (inMode) {
    camera.position.set(px * 0.42, EYE_Y + py * 0.26 + e * 0.18, lerp(START_Z, -1.4, e));
    camera.lookAt(px * 0.1, MID_Y - 0.2 + py * 0.18, -2.5);
  } else {
    camera.position.set(-0.5 + px * 0.34, EYE_Y + 0.25 + py * 0.22, lerp(-11.5, -8.6, e));
    camera.lookAt(0.1, MID_Y - 0.25 + py * 0.16, 0.2);
  }

  renderer.render(scene, camera);
}

function frame(now) {
  if (!running) return;
  renderOnce(now);
  requestAnimationFrame(frame);
}

/* exactly one frame, no loop: reduced motion, and verification */
function still() { renderOnce(performance.now()); }

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  const cap = coarse ? 1.6 : 2;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, cap));
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.fov = w / h < 0.85 ? 52 : 40;      // portrait needs a wider read
  camera.updateProjectionMatrix();
}

function start() {
  if (running) return;
  running = true;
  requestAnimationFrame(frame);
}
function stop() { running = false; }

resize();
window.addEventListener("resize", resize);

if (!reduced) {
  window.addEventListener("pointermove", (e) => {
    pxTarget = (e.clientX / window.innerWidth - 0.5) * 2;
    pyTarget = (e.clientY / window.innerHeight - 0.5) * -2;
  }, { passive: true });
  document.addEventListener("visibilitychange", () => {
    visible = !document.hidden;
    if (visible && stage.dataset.live === "1") start(); else stop();
  });
}

/* ---------- the handle the page drives ---------- */
const api = {
  set(next, nextMode) {
    const m = nextMode || "in";
    if (m !== mode) { mode = m; applyMode(); modeShown = m; }
    t = clamp01(next);
    if (reduced) { if (Math.abs(t - tShown) > 0.001) { tShown = t; still(); } return; }
    tShown = t;
  },
  live(on) {
    stage.dataset.live = on ? "1" : "0";
    if (reduced) { if (on) still(); return; }
    if (on && visible) start(); else stop();
  },
  still,      // render a single frame on demand (used by test/verification)
  reduced,
};

applyMode();
window.__waypointDoor = api;

if (reduced) { api.set(0.34, "in"); still(); }
else { api.live(true); }

document.documentElement.classList.add("gl-ready");
requestAnimationFrame(() => stage.classList.add("doorstage--on"));
