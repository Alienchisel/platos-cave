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
  // fitCanvas sets an explicit display size, so the stub needs a style object.
  style: {},
  // Real storage rather than a fixed 240x135: fitCanvas sizes the backing store
  // deliberately, and draw() reads it back to scale into.
  _w: 240, _h: 135,
  set width(v) { this._w = v; }, get width() { return this._w; },
  set height(v) { this._h = v; }, get height() { return this._h; },
  set innerHTML(v) {}, set textContent(v) {}, set value(v) {}, get value() { return 0; },
  // A real classList, not a set of no-ops: play mode is a body class and
  // fitCanvas reads it back, so a stub that forgets makes the mode untestable.
  classList: (() => {
    const set = new Set();
    return {
      add: c => set.add(c), remove: c => set.delete(c),
      contains: c => set.has(c),
      toggle: (c, on) => (on === undefined ? (set.has(c) ? set.delete(c) : set.add(c))
                                           : (on ? set.add(c) : set.delete(c)), set.has(c)),
    };
  })(),
  closest: () => null, blur: noop, focus: noop,
});
const store = {};
const bodyEl = el(), rootEl = el();
const sandbox = {
  document: {
    getElementById: el, createElement: el,
    body: bodyEl, documentElement: rootEl,
    // No requestFullscreen on rootEl: this stub stands in for the browser that
    // matters most here, iPhone Safari, which has never shipped the API. The
    // page must work with the class alone.
    fullscreenElement: null, fullscreenEnabled: false,
  },
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
  atob: b64 => Buffer.from(b64, 'base64').toString('binary'),
  performance: { now: () => clock }, innerWidth: 1200, innerHeight: 800,
  devicePixelRatio: 2,
  Math, console,
};
let clock = 0;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(js + `
// Captured before noDraw() replaces the binding, so the smoke test can still
// reach the real renderer.
const __draw = draw;
globalThis.__t = {
  smokeDraw: () => __draw(),
  frame, reset, press, regionAt, speedAt, gapAt,
  get S() { return S; },
  setHeld(v) { held = v; }, setLast(v) { last = v; },
  noDraw() { draw = () => {}; hud = () => {}; },
  release, loadScores, saveScores, qualifies, commitScore, loadIni,
  loadMyBest, noteRun, nextAbove, buildTargets,
  REGIONS, WIN_DIST, DESCENT_START, ASCENT_COUNT, PLAYER_X, W, H,
  TABLE_LEN, ALPHABET, LONG_MS, DEATH_HOLD,
  fitCanvas, setMax, get view() { return view; },
  BUST_W, BUST_H, BUST_B64,
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
// From the Python model. Twelve entries: ΣΕΛΗΝΗ's return was missing from every
// earlier table because the turn lands on that boundary and the ΠΕΡΙΑΓΩΓΗ branch
// was swallowing the log entry.
const EXPECTED = [
  ['ΠΥΡ', 12.7], ['ΕΙΔΩΛΑ', 29.6], ['ΥΔΩΡ', 50.7], ['ΑΣΤΡΑ', 81.8],
  ['ΣΕΛΗΝΗ', 124.7], ['ΗΛΙΟΣ', 187.6], ['ΣΕΛΗΝΗ', 216.8], ['ΑΣΤΡΑ', 245.9],
  ['ΥΔΩΡ', 269.8], ['ΕΙΔΩΛΑ', 289.2], ['ΠΥΡ', 305.3], ['ΣΚΙΑΙ', 318.4],
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
delete store['pc_ini'];
const tap = () => { clock += 10; T.press(); clock += 50; T.release(); };
const hold = () => { clock += 10; T.press(); clock += T.LONG_MS + 60; T.release(); };
// Park a qualifying death and press through to the entry screen.
function toEntry(dist) {
  T.reset(3); T.setLast(0); T.press();
  T.S.dist = dist; T.S.state = 'dead'; T.S.pending = true;
  T.S.deadT = T.DEATH_HOLD;          // past the frozen frame; see section 8
  clock += 1000; T.press();
}

toEntry(5000);
ok(T.S.state === 'initials', `press on a qualifying death opens entry (${T.S.state})`);
ok(T.S.ini.join('') === 'ΑΑΑ', `a first-time player starts at ΑΑΑ (${T.S.ini.join('')})`);

tap(); tap();
ok(T.S.ini[0] === T.ALPHABET[2], `two taps reach ${T.ALPHABET[2]} (${T.S.ini[0]})`);
hold();
ok(T.S.slot === 1, `a hold advances to slot 2 (slot=${T.S.slot})`);
tap(); hold(); hold();
ok(T.S.state === 'scores', `three holds commit and show the table (${T.S.state})`);
ok(T.loadScores().some(r => r.dist === 5000), 'the run was written to the table');
clock += 10; T.press();
ok(T.S.state === 'ready', `press on the table starts a fresh run (${T.S.state})`);

// Persistence: dying fifty seconds in should not cost you the name each time.
ok(store['pc_ini'] === 'ΓΒΑ', `the committed name is remembered (${store['pc_ini']})`);
toEntry(6000);
ok(T.S.ini.join('') === 'ΓΒΑ', `entry reopens on your last name (${T.S.ini.join('')})`);
hold(); hold(); hold();
ok(T.loadScores().some(r => r.ini === 'ΓΒΑ' && r.dist === 6000),
   'three holds re-enter it unchanged');

// Storage is editable and shared with whatever else uses this origin; a bad
// value must not strand you on a screen with no letter you can reach.
for (const bad of ['', 'ΑΒ', 'ΑΒΓΔ', 'ABC', 'ΑΒς', '{not json']) {
  store['pc_ini'] = bad;
  ok(T.loadIni().join('') === 'ΑΑΑ', `${JSON.stringify(bad)} falls back to ΑΑΑ`);
}
delete store['pc_ini'];

// 8. The frozen death frame. It has to be skippable, but the press that skips
//    it must not also advance past it, or one impatient tap eats the screen.
console.log('\nfrozen death frame:');
T.reset(3); T.setLast(0); T.press();
T.S.dist = 5000; T.S.state = 'dead'; T.S.pending = true; T.S.deadT = 0;
clock += 10; T.press();
ok(T.S.state === 'dead', `a press during the hold does not advance (${T.S.state})`);
ok(T.S.deadT >= T.DEATH_HOLD, 'but it does skip the hold');
clock += 10; T.press();
ok(T.S.state === 'initials', `the next press opens entry (${T.S.state})`);
// A non-qualifying death must still reach a fresh run in two presses.
T.reset(3); T.setLast(0); T.press();
T.S.dist = 100; T.S.state = 'dead'; T.S.pending = false; T.S.deadT = T.DEATH_HOLD;
clock += 10; T.press();
ok(T.S.state === 'ready', `a held-out death restarts on one press (${T.S.state})`);
// The ring must mark where you actually hit. Clamping it onto the panel made it
// point at a place the player never was.
T.reset(3); T.setLast(0); T.press();
T.setHeld(false);
for (let i = 1; i <= 400 && T.S.state !== 'dead'; i++) T.frame(i * 1000 / 60);
ok(T.S.state === 'dead' && T.S.hitY === T.S.py,
   `the impact ring sits on the true impact point (hitY ${T.S.hitY.toFixed(1)}` +
   ` vs py ${T.S.py.toFixed(1)})`);

// 9. Chase targets: the table plus your own best, in ascending order.
console.log('\nin-tunnel markers:');
delete store['pc_mybest']; delete store['pc_scores']; delete store['pc_ini'];
let tg = T.buildTargets();
ok(tg.length === T.TABLE_LEN, `no personal best yet: ${T.TABLE_LEN} targets (${tg.length})`);
ok(tg.every((m, i) => i === 0 || tg[i - 1].at <= m.at), 'targets are sorted ascending');
ok(tg.every(m => !m.mine), 'none of the seeded names is marked as yours');
T.noteRun(1500); store['pc_ini'] = 'ΧΑΡ';
tg = T.buildTargets();
const mine = tg.filter(m => m.mine);
ok(mine.length === 1 && mine[0].at === 1500 && mine[0].ini === 'ΧΑΡ',
   `your best joins the targets as ΧΑΡ 1500 (${mine.map(m => m.ini + ' ' + m.at)})`);

// A best can exist before a name does: any run under ΘΡΑ's 940 sets one without
// ever opening initials entry, and a cream marker reading ΑΑΑ looks like a rival.
delete store['pc_ini'];
ok(T.buildTargets().find(m => m.mine).ini === 'ΣΥ',
   `an unnamed player's own marker reads ΣΥ (${T.buildTargets().find(m => m.mine).ini})`);
store['pc_ini'] = 'ΧΑΡ';

// A qualifying run leaves a table entry exactly on your best. Two markers on
// one pixel, both with your initials, and the chase could name the rival.
delete store['pc_scores']; delete store['pc_mybest'];
T.noteRun(5000); T.commitScore('ΧΑΡ', 5000);
tg = T.buildTargets();
ok(tg.filter(m => m.at === 5000).length === 1,
   `one marker per distance after a qualifying run ` +
   `(${tg.filter(m => m.at === 5000).map(m => m.ini + (m.mine ? '/cream' : '/glow'))})`);
ok(tg.find(m => m.at === 5000).mine, 'and the one kept is yours, not the copy');
// A genuine tie with a seeded name collapses the same way.
delete store['pc_scores']; delete store['pc_mybest'];
T.noteRun(7200);                                   // exactly ΓΛΑ's seeded score
tg = T.buildTargets();
ok(tg.filter(m => m.at === 7200).length === 1 && tg.find(m => m.at === 7200).mine,
   'tying a seeded score leaves your marker, not theirs');
delete store['pc_scores']; delete store['pc_mybest'];
// Armed on the first playing frame, so a practice start does not fire eight
// overtakes on the way in.
T.reset(3); T.S.dist = 20000; T.S.practice = true; T.setLast(0); T.press();
T.setHeld(true); T.frame(20);
ok(T.S.targets.filter(m => m.at < 20000).every(m => m.done),
   'targets below a jumped start are armed as already passed');
ok(!T.S.capt, 'and no overtake is announced for them');
delete store['pc_mybest']; delete store['pc_ini'];

// 10. Render smoke. Every other test stubs drawing out for speed, which means
//     the renderer -- the largest body of code here -- is otherwise never run
//     at all. The canvas is a stub, so this proves the paths execute, not that
//     they look right; the PIL mockups are what settle appearance.
console.log('\nrender smoke (real draw(), stub canvas):');
function smoke(what, setup) {
  T.reset(3); T.setLast(0); T.press();
  T.S.dist = 3000;
  setup(T.S);
  let err = null;
  try { T.smokeDraw(); } catch (e) { err = e; }
  ok(!err, `${what}${err ? ' -- ' + err.message : ''}`);
}
for (const st of ['ready', 'play', 'scores']) smoke(`draw() in '${st}'`, S => S.state = st);
smoke("draw() in 'initials'",
      S => { S.state = 'initials'; S.slot = 0; S.ini = ['Α', 'Α', 'Α']; });
// Both band positions: the word moves to the half the body is not in.
smoke('impact card, body high', S => { S.state = 'dead'; S.deadT = 0; S.hitY = 20; });
smoke('impact card, body low', S => { S.state = 'dead'; S.deadT = 0; S.hitY = 115; });
smoke('impact card on a win',
      S => { S.state = 'won'; S.dist = T.WIN_DIST; S.deadT = 0; });
smoke('stats card after the hold',
      S => { S.state = 'dead'; S.deadT = T.DEATH_HOLD + 1; });
// A marker on screen, one off it, and one of each ownership.
smoke('markers on screen', S => {
  S.state = 'play';
  S.targets = [{ at: 3050, ini: 'ΓΛΑ', mine: false, done: false },
               { at: 3150, ini: 'ΧΑΡ', mine: true, done: false },
               { at: 9999, ini: 'ΠΛΩ', mine: false, done: false }];
});
// A marker whose walls sit hard against the panel edge: the label has nowhere
// to go and the ticks clip. It must still draw.
smoke('marker with no room for a label', S => {
  S.state = 'play';
  S.cave.cols = S.cave.cols.map(() => [T.H / 2, T.H * 0.98]);
  S.targets = [{ at: 3050, ini: 'ΓΛΑ', mine: true, done: false }];
});
smoke('overtake caption', S => { S.state = 'play'; S.capt = 'ΠΑΡΗΛΘΕΣ'; S.captT = 1; });
// The descent, where the occlusion gradient and the markers coincide.
smoke('markers under the closing view', S => {
  S.state = 'play'; S.dist = 26000;
  S.targets = [{ at: 26060, ini: 'ΔΑΜ', mine: false, done: false }];
});

// 11. Canvas fit. Integer-only scaling floored to 1x below 480 css px, so a
//     portrait phone got the raw 240x135 while four times that fitted.
console.log('\ncanvas fit:');
const fitAt = (iw, ih, dpr) => {
  sandbox.innerWidth = iw; sandbox.innerHeight = ih; sandbox.devicePixelRatio = dpr;
  T.fitCanvas();
  return { css: parseInt(T.view.style.width, 10), backing: T.view.width };
};
const phone = fitAt(390, 844, 3);
ok(phone.css >= T.W * 1.4,
   `a portrait phone gets a usable canvas (${phone.css} css px, was ${T.W})`);
const desk = fitAt(1440, 900, 2);
ok(desk.css === T.W * 4,
   `desktop still snaps to a whole 4x (${desk.css} css px)`);
ok(desk.backing === T.W * 8,
   `and its backing store is exactly 4x at dpr 2 (${desk.backing})`);
// The dither is an 8x8 pattern; a non-integer backing store would moire it.
for (const [iw, ih, dpr] of [[390, 844, 3], [844, 390, 3], [320, 568, 2],
                             [768, 1024, 2], [1440, 900, 2], [2560, 1440, 1]]) {
  const f = fitAt(iw, ih, dpr);
  ok(f.backing % T.W === 0 && f.backing >= f.css * dpr,
     `backing store at ${iw}x${ih}@${dpr}x is a whole multiple and covers the ` +
     `display (${f.backing} for ${f.css} css px)`);
}
// Play mode hides the rig, so the canvas gets the whole viewport. This is the
// half that has to work on iPhone, where the Fullscreen API does not exist --
// the stub deliberately offers no requestFullscreen.
const beforeMax = fitAt(390, 844, 3);
T.setMax(true);
const afterMax = fitAt(390, 844, 3);
ok(afterMax.css > beforeMax.css,
   `play mode grows the canvas (${beforeMax.css} -> ${afterMax.css} css px)`);
ok(afterMax.backing % T.W === 0, 'and its backing store is still a whole multiple');
T.setMax(false);
ok(fitAt(390, 844, 3).css === beforeMax.css, 'leaving play mode restores the fit');
// Landscape is where it pays: the game is a landscape shape, height is the
// binding constraint there, and hiding the rig is exactly height.
const landRig = fitAt(915, 412, 2.625);
T.setMax(true);
const landPlay = fitAt(915, 412, 2.625);
ok(landPlay.css >= landRig.css * 1.3,
   `landscape play mode is the real win (${landRig.css} -> ${landPlay.css} css px)`);
T.setMax(false);

fitAt(1200, 800, 2);                       // restore the harness default

// 12. The title screen. The bust travels as base64 in the generated block, so
//     the thing to check is that it survives the trip at the right size.
console.log('\ntitle screen:');
ok(T.BUST_B64.length > 0, 'the bust reached the page');
const bustBytes = Buffer.from(T.BUST_B64, 'base64').length;
const wantBytes = ((T.BUST_W + 7) >> 3) * T.BUST_H;
ok(bustBytes === wantBytes,
   `${T.BUST_W}x${T.BUST_H} unpacks to the right length ` +
   `(${bustBytes} bytes, want ${wantBytes})`);
// A blank or fully-lit bust would still be the right length, so check it is a
// picture: a dithered face lands nowhere near either extreme.
const lit = Buffer.from(T.BUST_B64, 'base64')
  .reduce((n, b) => n + ((b * 0x08040201 >> 3) & 0x11111111).toString(2)
    .replace(/0/g, '').length, 0);
const litPct = lit / (T.BUST_W * T.BUST_H) * 100;
ok(litPct > 5 && litPct < 60, `and is a picture, not a blank (${litPct.toFixed(0)}% lit)`);

T.reset(3);
ok(T.S.state === 'ready', 'a reset run opens at the standing start, not the title');
T.S.state = 'title';
clock += 10; T.press();
ok(T.S.state === 'ready', `a press leaves the title (${T.S.state})`);
smoke("draw() in 'title'", S => S.state = 'title');

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
