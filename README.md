# Plato's Cave

### ▶ [Play it](https://alienchisel.github.io/platos-cave/)

A one-button cave-flyer. Space or tap to thrust — hold to climb, release to
fall, and that is the whole control scheme. You are a point of light ascending
out of Plato's cave; gravity pulls you down, rock kills you, distance is score.

The allegory isn't decoration. Plato's ascent in *Republic* 514a–517a is an
ordered sequence of light sources — shadows, fire, carried images, reflections in
water, stars, moon, sun — and that sequence supplies the game's entire
progression structure *and* its palette. **The screen brightens as you climb.**
Your progress isn't a number in the corner; it's how much you can see.

And reaching the sun isn't the end. Plato's freed prisoner is obliged to go back
down, and his eyes no longer work in the dark. **You win by returning to the
chains** — back down through six of them, each dimmer than it was on the way up,
with the view closing in. Roughly 5¼ minutes of unbroken flight.

One more borrowing, from the *Phaedrus* rather than the *Republic*: thrust
against gravity, with you holding the balance, is already the charioteer and his
two horses. So the trail runs as two strands, whichever is being obeyed leading.

![gameplay](docs/images/gameplay.gif)

*Leaving the cave: ΕΙΔΩΛΑ into ΥΔΩΡ, the largest colour jump in the run. Real
time, at the panel's true 240 × 135 shown at 2×.*

---

![every region, ascending above and returning below](docs/images/descent_regions.png)

*All thirteen regions: the ascent along the top, the return below it. Every one
dimmer coming down than it was going up.*

---

## Screens

| | |
| --- | --- |
| ![title](docs/images/screen_title.png) | ![high scores](docs/images/screen_scores.png) |
| ![died ascending](docs/images/screen_gameover.png) | ![died returning](docs/images/screen_gameover_return.png) |
| ![victory](docs/images/screen_victory.png) | |

All at true 240 × 135, the panel's real resolution.

**ΚΑΤΕΒΗΝ** — *I went down* — is the first word of the *Republic*, and after the
return it is exactly what you have just done. Death has two words: **ΔΕΣΜΩΤΗΣ**,
*prisoner*, climbing; **ΤΥΦΛΟΣ**, *blind*, returning, because 516e says the
returning man's eyes are full of darkness. The pip row under each shows how far
you got, coloured by each region's own light, with a divider where the sun is.

The high-score table is headed **ΟΙ ΛΥΘΕΝΤΕΣ** — *those who were released* — and
seeded so the ordering carries a joke: the Neoplatonists above the *Republic*'s
cast, because the cast were never released. They only heard it described.

See also [the seven ascent regions in detail](docs/images/stages_reference.png)
and [the difficulty levers across a full run](docs/images/descent_curves.png).

## The build

`web/index.html` is the game: one self-contained file, no dependencies, no
network. It is what the link above serves, deployed straight from `web/` rather
than copied, because a second copy is a second thing to drift.

It began as a rig for finding four numbers with a thumb, and the rig is still
there behind the **tuning** toggle: live sliders for gravity, thrust, vy-max and
`VIEW_CLOSE`, so "it feels floaty" arrives attached to the number that causes it.
The first three were found that way, in play, and baked back into `cave.py`.
`VIEW_CLOSE` is still untested — it only bites on the return, four minutes in.

Press **f**, or the button top-right, for play mode: the furniture goes and the
canvas takes the viewport (and the browser chrome too, where the Fullscreen API
exists). Turn a phone sideways for it — the game is a landscape shape, so that
is where it pays.

Two things are drawn in the world rather than on a menu, and both are there to
make a run legible while you are inside it. **Score markers** are cut into the
rock at the distance of every score above you — yours in cream and doubled,
rivals single, with the next one named in the corner. And **the death word lands
over the frozen frame you died on**, dimmed, with the impact ringed, before the
stats card follows.

```bash
python tools/bake_web.py     # re-export cave.py's constants into the page
node tools/test_web.js       # check the web build against the Python model
python tools/regen.py --check   # are the committed artifacts still current?
```

`regen.py` reruns every generator and asks git whether anything moved. The
repository commits derived things — C headers, the reference screens, the
difficulty curves, the GIF above — and twice they came to describe a game that
no longer existed. Generation is byte-reproducible, so this catches it. CI runs
it on every push.

`test_web.js` runs the game headlessly and compares all twelve region transitions
against `cave.py`, at 30 / 50 / 72 / 144 fps. Generated constants keep the
numbers in step; this checks the behaviour is too. It also runs the real
renderer against a stub canvas in every screen state — otherwise the largest
body of code in the page would never execute under test at all.

**Pin the terrain when comparing tunings.** Append `#seed=42` (or `?seed=42`)
and every run replays the same cave. Without it, "that felt better" may only
mean the generator dealt an easier tunnel. The seed of the current run is always
shown under the canvas and is a link that pins it, so a run worth repeating can
be repeated.

The tunnel is procedurally generated per run, but only the *route* is random —
the gap is a pure function of distance, identical every time, so the difficulty
curve never varies and scores stay comparable. The noise is applied to the
passage's rate of change rather than its position, damped and clamped, which is
why it undulates rather than jitters.

It also reports a difficulty reading. A lookahead autopilot now **completes 5 of
5 runs**. It used to complete 0 of 5, and the change was not a difficulty tuning:
the passage's drift is applied per *column*, so as the scroll accelerated the
walls came to move vertically faster than the player could ever climb — 280 px/s
against a ceiling of 135. Late deaths were partly unavoidable, and no amount of
skill fixed it.

Read 5 of 5 as evidence that the game is *possible*, not that it is easy. The
autopilot has perfect reaction time and sees the exact bounds; a human playing
the same build reaches region 4 of 13.

## Status

**The web build is the game.** It is finished and it runs on a phone.

| | |
| --- | --- |
| Web build | complete — all thirteen regions, the return, scores, title |
| Ascent and return | 5 min 18 s end to end |
| Pacing | frame-rate independent, verified 30–144 fps |
| Physics feel | tuned by playtest |
| `VIEW_CLOSE` | **never tested** — it only bites four minutes in |
| Audio | not started |
| Handheld port | **deferred** — see below |

### The handheld, and why it is deferred

This began as firmware for a pocket ESP32, and the design still carries that
everywhere: 240 × 135, one button, an 8 × 8 ordered dither, three tones per
region, a 1-bit title bust. Then the browser build — built only to find four
numbers — turned out to be the whole game, on a device already in your pocket.

Nothing has been abandoned, because the firmware was never begun: there are zero
lines of game C++. What sits under `firmware/` is the archived point-cloud sketch
for a board that was rejected. `cave.py` is still the reference implementation,
`bake_constants.py` still emits `constants.h`, and
[docs/HARDWARE.md](docs/HARDWARE.md) still records the four devices considered.
A port stays available; it is simply not the plan.

⚠ **240 × 135 is now a decision, not a constraint.** It was inherited from a
panel, and with the panel deferred there is nothing to enforce it but intent.
The resolution, the dither, the three-tone palette and the single button *are*
the design — see [GAME_DESIGN.md §5](docs/GAME_DESIGN.md).

---

## Documentation

| Doc | Contents |
| --- | --- |
| [docs/HARDWARE.md](docs/HARDWARE.md) | *Deferred.* What a handheld port would need, and a record of the four devices considered and rejected. |
| [docs/GAME_DESIGN.md](docs/GAME_DESIGN.md) | Rules, the thirteen regions, the return, palette, pacing curve, open decisions. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | *Deferred.* Launcher-plus-modules structure for the firmware, the input abstraction, build order. |
| [docs/ARCHIVE_POINTCLOUD.md](docs/ARCHIVE_POINTCLOUD.md) | The abandoned first direction, kept for its findings. |

**Play it first if you're picking this up cold**, then read GAME_DESIGN.md — the
allegory drives the mechanics rather than decorating them, and almost nothing in
the design makes sense read the other way round.

---

## Tools

**The bakers feed the firmware. Everything else is design work.**

| | |
| --- | --- |
| `tools/cave.py` | The game. Simulates a run and renders it. **The reference implementation**: the C++ must match its math. |
| `tools/bake_assets.py` | Images and Greek text → 1-bit C headers. |
| `tools/bake_constants.py` | `cave.py` → `constants.h`. Also reports any constant that never reached the firmware. |
| `tools/verify_bake.py` | Parses the generated C back out and checks it. There is no compiler here, so nothing else would catch malformed output. |
| `tools/mockups.py` | The non-gameplay screens — title, high scores, both deaths, victory — at true 240 × 135. |
| `tools/readme_gif.py` | The gameplay loop above. Sized against a byte budget, since it is committed. |
| `tools/bake_web.py` | `cave.py` → the constants block in `web/index.html`. |
| `tools/test_web.js` | Runs the web build headlessly and checks it against the Python model. |
| `tools/stage_sheet.py` | Reference sheet of the seven ascent regions with palettes, hex values and per-stage difficulty numbers. |
| `tools/model_descent.py` | The full run including the return: difficulty curves across all three levers, and every region ascending and returning. |
| `tools/imgutil.py` | Palette-PNG saving for the committed reference images. |
| `tools/image_treatments.py` | Twelve treatments of a source image. Also supplies `prepare()`, which the bakers depend on. |
| `tools/isolate_head.py` | Cuts a subject off a photographed background onto black. Works when the subject is clearly brighter than the background; not when their tonal ranges overlap. |
| `tools/preview.py` · `sample_points.py` · `make_test_mesh.py` | The archived point-cloud direction. |

### Running it

```bash
python tools/cave.py --seconds 225 --fps 24 --scale 2
```

Simulates a full ascent, writes a gameplay GIF and a per-region contact sheet to
`preview/`, and prints the stage timings.

```bash
python tools/bake_assets.py && python tools/bake_constants.py && python tools/verify_bake.py
```

Regenerates everything under `firmware/plato/assets/` and checks it round-trips.
Deterministic — re-running produces byte-identical headers.

```bash
python tools/model_descent.py
python tools/mockups.py
python tools/stage_sheet.py
```

Regenerate the committed reference images in `docs/images/`.

Requires `numpy` and `pillow`. The archived point-cloud tools additionally need
`trimesh`, `scipy` and `networkx`.

`bake_assets.py` and `mockups.py` need `image/plato.png`, the source photograph,
which is **not** in the repository — the assets baked from it are. Those two will
fail on a fresh clone; everything else runs.

---

## How this got here

Worth recording, because the path explains the leftovers.

It began as a **rotating 3D Plato bust** for a LILYGO T-QT Pro, drawn as a point
cloud because marble shading collapses at 128 × 128. That worked — see
[the archive](docs/ARCHIVE_POINTCLOUD.md) — and produced some genuinely useful
findings about blue-noise sampling and dot coverage.

It then became a **Metal Gear codec display**, which was fun and is where the
Greek UI came from, before the rotating head was dropped in favour of treating a
still photograph.

It is now a **game**, which is the first version that gives the device a reason
to be picked up rather than glanced at. It was endless until the *Republic*
pointed out that the ascent has an ending and the descent is the hard part, at
which point it became winnable.

The target board changed too, once it emerged that the T-QT Pro has no battery
socket, a case that physically cannot contain a battery, and no speaker.

And then it stopped being firmware. A browser build was made for one narrow
job — finding three physics constants against a real thumb, because they were
the decisions most likely to be wrong and the hardware had not been bought. It
worked; the constants were found. But the build kept acquiring the rest of the
game, and at some point it *was* the game, running on a phone already in a
pocket, against firmware that had never had a line written. So the pocket
handheld became the deferred port and the tuning rig became the product.

Its fingerprints are all over the design, which is the point: 240 × 135, one
button, an ordered dither and three colours a region are what a 48 mm device
asked for, and they are why the thing looks like itself.

---

## License

Code, documentation and the generated assets: **MIT** — see [LICENSE](LICENSE).

One exception, and it is not mine to relicense: `firmware/plato_tqt/plato_points.h`
is sampled from the CC BY 4.0 scan credited below, so that file carries CC BY 4.0
and its attribution travels with it.

---

## Credits

- **3D scan** — *Plato*, Fitzwilliam Museum, object GR.23.1850, via
  [Sketchfab](https://sketchfab.com/3d-models/plato-1df8376b55e347fb9bb4cf49375d6e5a),
  CC BY 4.0. The game does not use it: the title bust is dithered from the
  photograph below. The scan is credited because
  `firmware/plato_tqt/plato_points.h` — 8,872 points, committed — was sampled
  from it, so this line belongs to that file and should outlive it by nothing.
- **The sculpture** throughout is the Vatican Museums' herm of Plato, Museo
  Pio-Clementino, Sala delle Muse, Inv. 305 — a Roman copy after a Greek
  original of the late 4th century BC. Its base is inscribed ΖΗΝΩΝ.

---

## Repository

<https://github.com/Alienchisel/platos-cave>

**Development happens on a Linux box.** `image/plato.png` is committed and the
canonical font is DejaVu Sans Mono, so every tool runs — and is *checked* — on
any Linux machine and on CI. Consolas held that role until the work moved, and
while it did, five of the eight tools could only be verified on one computer.

`mesh/` and `preview/` are still excluded: ~32 MB of a 3D scan the archived
point-cloud tools need, plus regenerable scratch output. `mesh/plato.glb` lives
only on the machine that downloaded it, so those archived tools cannot run on a
fresh clone. Their output is committed and nothing else depends on them.

`firmware/plato_tqt/` keeps its name because it holds the archived T-QT sketch,
named for the board it targeted. It was never compiled.
