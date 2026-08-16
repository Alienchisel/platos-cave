#!/usr/bin/env node
/*
 * Run web/index.html's game headlessly and check it against the Python model.
 *
 *     node tools/test_web.js
 *
 * The playable build only earns its keep if it is the same game as cave.py --
 * otherwise tuning done here transfers nothing. bake_web.py makes the constants
 * agree; this checks the behaviour does.
 *
 * Two harness notes:
 *
 *  - Drawing is stubbed out. draw() runs a 32k-pixel loop per frame and none of
 *    it is under test; leaving it in made a parameter sweep take minutes.
 *  - For timing comparisons the autopilot is *forgiven* collisions, recentring
 *    and carrying on. That is exactly what cave.simulate() does, so the two are
 *    measuring the same thing. Death is tested separately, on its own.
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const page = path.join(__dirname, '..', 'web', 'index.html');
const js = fs.readFileSync(page, 'utf8').split('<script>')[1].split('</script>')[0];

const noop = () => {};
const ctx2d = new Proxy({}, {
  get: (_, p) => {
    if (p === 'createImageData') return (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
    if (p === 'measureText') return () => ({ width: 10 });
    if (p === 'createLinearGradient') return () => ({ addColorStop: noop });
    return noop;
  },
  set: () => true,
});
const el = () => ({
  getContext: () => ctx2d, addEventListener: noop,
  set width(v) {}, get width() { return 240; },
  set height(v) {}, get height() { return 135; },
  set innerHTML(v) {},
});
const store = {};
const sandbox = {
  document: { getElementById: el, createElement: el },
  localStorage: { getItem: k => store[k] ?? null, setItem: (k, v) => store[k] = String(v) },
  addEventListener: noop, requestAnimationFrame: noop,
  performance: { now: () => 0 }, innerWidth: 1200, innerHeight: 800,
  Math, console,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(js + `
globalThis.__t = {
  frame, reset, press, regionAt, speedAt, gapAt,
  get S() { return S; },
  setHeld(v) { held = v; }, setLast(v) { last = v; },
  noDraw() { draw = () => {}; hud = () => {}; },
  REGIONS, WIN_DIST, DESCENT_START, ASCENT_COUNT, PLAYER_X, W, H,
};`, sandbox);

const T = sandbox.__t;
T.noDraw();

let fail = 0;
const ok = (cond, what) => {
  if (!cond) fail++;
  console.log(`  ${cond ? 'ok  ' : 'FAIL'}  ${what}`);
};
const near = (a, b, tol, what) =>
  ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b} (±${tol})`);

/* Mirrors cave.simulate(): aim at the passage centre, and on contact recentre
 * and continue rather than ending the run. */
function timedRun(seed, fps, seconds) {
  T.reset(seed); T.setLast(0); T.press();   // a run now waits for the first press
  const log = [];
  let prev = T.regionAt(0);
  for (let i = 1; i <= seconds * fps; i++) {
    const S = T.S;
    const [top, bot] = S.cave.bounds(T.PLAYER_X);
    T.setHeld(S.py > (top + bot) / 2 - 2);
    T.frame(i * 1000 / fps);
    const s = T.S;
    if (s.state === 'dead') {
      const [t2, b2] = s.cave.bounds(T.PLAYER_X);
      s.py = (t2 + b2) / 2; s.vy = 0; s.state = 'play';
    }
    const now = T.regionAt(s.dist);
    if (now !== prev) { log.push({ name: now.name, t: i / fps }); prev = now; }
    if (s.state === 'won') break;
  }
  return log;
}

// 1. Region timings must match what the Python model reports.
const EXPECTED = [
  ['ΠΥΡ', 12.5], ['ΕΙΔΩΛΑ', 31.3], ['ΥΔΩΡ', 57.0], ['ΑΣΤΡΑ', 95.2],
  ['ΣΕΛΗΝΗ', 145.7], ['ΗΛΙΟΣ', 212.6], ['ΣΕΛΗΝΗ', 242.6], ['ΑΣΤΡΑ', 273.0],
  ['ΥΔΩΡ', 297.4], ['ΕΙΔΩΛΑ', 316.9], ['ΠΥΡ', 333.1], ['ΣΚΙΑΙ', 346.2],
];
console.log('region timings vs the Python model (50 fps):');
const log50 = timedRun(3, 50, 400);
EXPECTED.forEach(([name, t], i) => {
  const got = log50[i];
  if (!got) return ok(false, `${name} never reached`);
  if (got.name !== name) return ok(false, `slot ${i}: ${got.name}, expected ${name}`);
  near(+got.t.toFixed(1), t, 0.3, name.padEnd(7));
});

// 2. Frame-rate independence -- the property the pacing rewrite bought.
console.log('\nframe-rate independence:');
const base = log50.at(-1).t;
for (const fps of [30, 72, 144]) {
  const l = timedRun(3, fps, 400).at(-1);
  near(+l.t.toFixed(1), +base.toFixed(1), 0.4, `chains at ${fps} fps`);
}

// 3. The win condition, tested on its own rather than by requiring a flawless
//    pilot -- see the autopilot note below for why that would be a bad gate.
console.log('\nend conditions:');
// Collisions are forgiven here for the same reason as in timedRun: what is
// under test is the win *condition*, not whether a pilot can survive to it.
// Holding thrust instead simply flies into the ceiling and proves nothing.
T.reset(3); T.setLast(0); T.press();
T.S.dist = T.WIN_DIST - 200;
for (let i = 1; i <= 400 && T.S.state !== 'won'; i++) {
  const S = T.S;
  const [top, bot] = S.cave.bounds(T.PLAYER_X);
  T.setHeld(S.py > (top + bot) / 2 - 2);
  T.frame(i * 20);
  if (T.S.state === 'dead') {
    const [t2, b2] = T.S.cave.bounds(T.PLAYER_X);
    T.S.py = (t2 + b2) / 2; T.S.vy = 0; T.S.state = 'play';
  }
}
ok(T.S.state === 'won', `crossing ${T.WIN_DIST} wins (state=${T.S.state})`);

// 4. Collision must actually end a run.
T.reset(11); T.setLast(0); T.press();
let died = false;
for (let i = 1; i <= 900 && !died; i++) { T.setHeld(false); T.frame(i * 1000 / 60); died = T.S.state === 'dead'; }
ok(died, 'falling with no thrust dies');

// 5. Not a pass/fail -- a difficulty reading. A lookahead controller aiming at
//    the tightest point in the window ahead is a decent proxy for a good human.
function skilledRun(seed, look = 16, k = 10) {
  T.reset(seed); T.setLast(0); T.press();
  for (let i = 1; i <= 25000; i++) {
    const S = T.S;
    if (S.state !== 'play') return { dist: S.dist, t: i / 50, state: S.state };
    let lo = -1e9, hi = 1e9;
    for (let x = T.PLAYER_X; x < Math.min(T.W, T.PLAYER_X + look); x++) {
      const [t, b] = S.cave.bounds(x);
      if (t > lo) lo = t; if (b < hi) hi = b;
    }
    T.setHeld(S.vy > ((lo + hi) / 2 - S.py) * k);
    T.frame(i * 20);
  }
  return { dist: T.S.dist, t: 500, state: T.S.state };
}
console.log('\nautopilot reach (not a test -- a difficulty reading):');
let sum = 0, n = 0, won = 0;
for (const seed of [3, 7, 11, 42, 99]) {
  const r = skilledRun(seed);
  sum += r.dist; n++; if (r.state === 'won') won++;
  const reg = T.regionAt(r.dist);
  console.log(`  seed ${String(seed).padStart(3)}  ${r.state.padEnd(4)}  ` +
              `dist ${String(Math.round(r.dist)).padStart(5)}  ` +
              `${r.t.toFixed(0)}s  ${reg.name}`);
}
console.log(`  mean ${Math.round(sum / n)} of ${T.WIN_DIST} ` +
            `(${(sum / n / T.WIN_DIST * 100).toFixed(0)}%), ${won}/${n} completed`);

console.log(`\n${fail === 0 ? 'PASS' : fail + ' FAILURE(S)'}`);
process.exit(fail ? 1 : 0);
