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
  set innerHTML(v) {}, set textContent(v) {}, set value(v) {}, get value() { return 0; },
  classList: { toggle: noop, add: noop, remove: noop },
  closest: () => null, blur: noop, focus: noop,
});
const store = {};
const sandbox = {
  document: { getElementById: el, createElement: el },
  localStorage: { getItem: k => store[k] ?? null, setItem: (k, v) => store[k] = String(v) },
  // The page reads the hash for a pinned seed and a saved tuning, and writes it
  // back through replaceState. Stub both rather than making the page defend
  // against an environment that only this harness creates.
  location: { hash: '', search: '', pathname: '/', reload: noop },
  history: { replaceState: noop },
  Element: function Element() {},
  addEventListener: noop, requestAnimationFrame: noop,
  // Controllable clock: the one-button initials scheme distinguishes a tap from
  // a hold by duration, so the harness has to be able to move time.
  performance: { now: () => clock }, innerWidth: 1200, innerHeight: 800,
  Math, console,
};
let clock = 0;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(js + `
globalThis.__t = {
  frame, reset, press, regionAt, speedAt, gapAt,
  get S() { return S; },
  setHeld(v) { held = v; }, setLast(v) { last = v; },
  noDraw() { draw = () => {}; hud = () => {}; },
  release, loadScores, saveScores, qualifies, commitScore,
  loadMyBest, noteRun, nextAbove,
  REGIONS, WIN_DIST, DESCENT_START, ASCENT_COUNT, PLAYER_X, W, H,
  TABLE_LEN, ALPHABET, LONG_MS,
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

// 5. Seeding. The whole point of ?seed= is that a tuning change can be judged
//    on identical terrain, which is worthless if seeds do not actually repeat.
console.log('\nseeding:');
const shape = (seed) => {
  T.reset(seed); T.setLast(0); T.press();
  const out = [];
  for (let i = 1; i <= 400; i++) {
    const S = T.S;
    const [t, b] = S.cave.bounds(T.PLAYER_X);
    T.setHeld(S.py > (t + b) / 2 - 2);
    T.frame(i * 20);
    if (T.S.state === 'dead') {
      const [a, c] = T.S.cave.bounds(T.PLAYER_X);
      T.S.py = (a + c) / 2; T.S.vy = 0; T.S.state = 'play';
    }
    if (i % 80 === 0) out.push(Math.round(T.S.cave.cols[T.W - 1][0]));
  }
  return out.join(',');
};
ok(shape(42) === shape(42), 'the same seed reproduces the same terrain');
ok(shape(42) !== shape(43), 'different seeds give different terrain');
T.reset(7); const s7 = T.S.seed;
ok(s7 === 7, `the run records its seed (${s7})`);
T.reset(); const r1 = T.S.seed; T.reset(); const r2 = T.S.seed;
ok(r1 !== r2, 'an unseeded run picks a fresh cave each time');

// 6. The score table. Bugs here silently lose the player's runs.
console.log('\nhigh-score table:');
delete store['pc_scores'];
const defaults = T.loadScores();
ok(defaults.length === T.TABLE_LEN, `defaults seed ${T.TABLE_LEN} entries`);
ok(defaults[0].ini === 'ΠΛΩ', `top of the default table is ΠΛΩ (${defaults[0].ini})`);
ok(!T.qualifies(500), 'a run below the last entry does not qualify');
ok(T.qualifies(1000), 'a run above the last entry qualifies');
ok(T.qualifies(T.WIN_DIST), 'a completed run always qualifies');

T.commitScore('ΤΕΣ', 25000);
const after = T.loadScores();
ok(after.length === T.TABLE_LEN, `table stays at ${T.TABLE_LEN} after an insert`);
ok(after.some(r => r.ini === 'ΤΕΣ'), 'the new entry is on the table');
ok(!after.some(r => r.ini === 'ΘΡΑ'), 'the lowest entry was pushed off');
ok(after.every((r, i) => i === 0 || after[i - 1].dist >= r.dist),
   'the table stays sorted');

// Corrupt storage must not brick the page -- it is a real thing that happens.
store['pc_scores'] = '{not json';
ok(T.loadScores().length === T.TABLE_LEN, 'corrupt storage falls back to defaults');
delete store['pc_scores'];

// Personal best is separate from the table's top. Conflating them showed the
// seeded ΠΛΩ 33000 as though the player had scored it.
console.log('\npersonal best:');
delete store['pc_mybest'];
ok(T.loadMyBest() === 0, 'a player who has never run has no best');
ok(T.loadScores()[0].dist === 33000, 'the table top is still ΠΛΩ 33000');
T.noteRun(988);
ok(T.loadMyBest() === 988, `a run below the table still counts (${T.loadMyBest()})`);
T.noteRun(400);
ok(T.loadMyBest() === 988, 'a worse run does not lower it');
T.noteRun(1500);
ok(T.loadMyBest() === 1500, 'a better run raises it');
const nxt = T.nextAbove(1500);
ok(nxt && nxt.ini === 'ΓΛΑ', `next target above 1500 is ΓΛΑ (${nxt && nxt.ini})`);
ok(T.nextAbove(99999) === null, 'nothing is above a maximal run');
delete store['pc_mybest'];

// 6. One-button initials entry: tap steps a letter, hold commits it.
console.log('\none-button initials entry:');
T.reset(3); T.setLast(0); T.press();
T.S.dist = 5000; T.S.state = 'dead'; T.S.pending = true;
clock = 1000; T.press();                       // enter the initials screen
ok(T.S.state === 'initials', `press on a qualifying death opens entry (${T.S.state})`);
ok(T.S.ini.join('') === 'ΑΑΑ', `starts at ΑΑΑ (${T.S.ini.join('')})`);

const tap = () => { clock += 10; T.press(); clock += 50; T.release(); };
const hold = () => { clock += 10; T.press(); clock += T.LONG_MS + 60; T.release(); };
tap(); tap();
ok(T.S.ini[0] === T.ALPHABET[2], `two taps reach ${T.ALPHABET[2]} (${T.S.ini[0]})`);
hold();
ok(T.S.slot === 1, `a hold advances to slot 2 (slot=${T.S.slot})`);
tap(); hold(); hold();
ok(T.S.state === 'scores', `three holds commit and show the table (${T.S.state})`);
ok(T.loadScores().some(r => r.dist === 5000), 'the run was written to the table');
clock += 10; T.press();
ok(T.S.state === 'ready', `press on the table starts a fresh run (${T.S.state})`);

// 7. Not a pass/fail -- a difficulty reading. A lookahead controller aiming at
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
