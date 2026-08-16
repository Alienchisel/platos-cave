# Software Architecture

**Status:** design only. No firmware written. Targets M5StickS3 — see
[HARDWARE.md](HARDWARE.md); game rules in [GAME_DESIGN.md](GAME_DESIGN.md).

---

## 1. Principle: a thin shell, not an engine

The device will hold more than one game, so the shell exists from day one. But
it stays *small* — a six-method interface and a state machine, not a framework.
Building an engine for one game is the failure mode to avoid; the point is only
that adding the second game shouldn't require untangling globals out of a
single-purpose sketch.

---

## 2. Layers

```
M5Unified                 display, buttons, speaker, power, IMU
   └── platform/          our shim: logical input, clamped timing, canvas
        └── console/      state machine, menu, high scores, sleep
             └── games/   Game implementations
```

Nothing in `games/` touches M5Unified directly. That keeps the games portable if
the hardware changes again — which, given this project's history, is worth the
one layer of indirection.

---

## 3. The Game interface

```cpp
class Game {
 public:
  virtual ~Game() = default;
  virtual const char* id()    const = 0;   // NVS key, stable forever
  virtual const char* title() const = 0;   // menu label
  virtual void enter()                = 0; // reset to a fresh run
  virtual void update(float dt, const Input&) = 0;
  virtual void draw(Canvas&)          = 0;
  virtual bool finished() const       = 0;
  virtual uint32_t score() const      = 0;
  virtual const char* rank() const { return ""; }
};
```

`rank()` is the secondary achievement shown beside the score — for Plato's Cave
it returns the stage reached (ΣΕΛΗΝΗ and so on), which reads better on a table
than a bare number. Other games can return whatever suits or nothing at all.

`id()` becomes the NVS key and must never change, or high scores are orphaned.

---

## 4. Input — deliberately abstracted

**The button count is unresolved** (HARDWARE.md §3.1: possibly only one
programmable button). So games never see buttons, only intents:

```cpp
struct Input {
  bool thrust;       // held this frame
  bool confirm;      // pressed this frame (edge)
  bool back;         // pressed this frame (edge)
};
```

Physical mapping lives in exactly one file. If the device turns out to have one
usable button, `confirm` becomes a short press and `back` a long press, and
**nothing in any game changes.** If a second button exists, the mapping gets
simpler. This is the single highest-value abstraction in the design, because it
quarantines the one hardware unknown that could otherwise reach everywhere.

---

## 5. Timing

Variable delta time, **clamped**:

```cpp
float dt = min(now - last, 0.05f);   // 50 ms ceiling
```

The game logic is already per-second (GAME_DESIGN §9), so variable dt is safe.
The clamp matters: without it, one slow frame — a flash write, a WiFi wake —
integrates a huge dt and teleports the player through a wall. Clamping degrades
to slow-motion instead, which is survivable and honest.

---

## 6. Rendering

- One offscreen `M5Canvas` at 240 × 135, 16 bpp = **63 KB**. Comfortable in
  internal RAM; PSRAM is available if not.
- `setRotation()` once at boot for landscape. Games draw in landscape
  coordinates and never think about it.
- Draw to canvas, `pushSprite()` once per frame. Effectively double-buffered, no
  tearing.
- The cave renderer stays a **1-bit dither with a per-stage palette lookup** —
  three colours per stage, so colour costs nothing over monochrome.
- **The trail needs line drawing, not point plotting.** This is the one place the
  renderer cannot be point-wise: isolated pixels disappear into the dither. See
  GAME_DESIGN §4 — the constraint is baked into `constants.h` alongside the
  trail tuning so it cannot be missed at implementation time.

---

## 7. Persistence

NVS via `Preferences`, one namespace, keyed by `id()`.

```
plato.cave  -> [ {char ini[4]; uint32 score; char rank[10];} x 8 ]
```

~120 bytes per game against a ~20 KB partition. **No SD card** (HARDWARE.md §4).

⚠ **Don't tick "Erase All Flash Before Sketch Upload"** — it wipes NVS and the
high scores with it.

---

## 8. Audio

`M5.Speaker.tone()` — procedural only. Samples cost ~11 KB/second; synthesis
costs nothing and suits the aesthetic (GAME_DESIGN §8). A tiny sequencer helper
in `platform/` so games request "play cue N" rather than driving the speaker.

---

## 9. Asset pipeline

Python tools generate C headers. Existing tools are the **design prototype**,
not a build dependency — only the bakers feed the firmware.

| Tool | Output | Notes |
| --- | --- | --- |
| `bake_assets.py` | `assets/bust.h`, `assets/labels.h` | written |
| `bake_constants.py` | `assets/constants.h` | written — emits all 13 regions |
| `verify_bake.py` | round-trip + structural check | written — bust at 0 differing pixels, region table field-counted |
| `model_descent.py` | descent curves and region sheets | written |
| `cave.py` | design reference | already exists |

Total baked data is ~2.7 KB: bust 1 770 B, nine labels ~300 B, 24-glyph Greek
alphabet 672 B.

**There is no C compiler in this environment**, so nothing catches malformed
generated output. `verify_bake.py` therefore field-counts the region table: a
missing separator once emitted `{LBL_SKIAI      0, 36, ...}`, which reads fine to
a human skimming it and is a syntax error. Check structure, don't trust the eye.

Two things must be baked rather than computed on device:

- **The title bust**, 1-bit at ~118 px. It must be dithered *at final size* —
  see the gotcha in GAME_DESIGN §11.
- **The Greek labels** (ΣΚΙΑΙ … ΗΛΙΟΣ, ΟΙ ΛΥΘΕΝΤΕΣ, ΔΕΣΜΩΤΗΣ) as 1-bit
  bitmaps, which avoids carrying a Greek-capable font in flash. Under 1 KB total.

### Generate the constants, don't retype them

`cave.py` holds the stage table, pacing constants and palette, and
`bake_constants.py` exports them. Nothing is typed twice.

This is not hypothetical tidiness. Earlier in this project the same values lived
in both `preview.py` and `plato_tqt.ino` with only a comment asking future
editors to keep them in sync — and they drifted within a day.

Three links enforce it now:

1. `bake_constants.py` imports `cave.py` directly, so no value is retyped.
2. It imports the label list from `bake_assets.py`, so a region cannot reference
   a label that was never baked — it fails loudly instead of emitting a dangling
   index.
3. **A completeness guard.** After emitting, it enumerates every ALL-CAPS numeric
   constant in `cave.py` and reports any that never reached the header. The
   default is "must be exported"; `NOT_BAKED` is the explicit opt-out.

The third exists because the same mistake happened **three times** — descent
constants, trail constants, region-texture constants — each added to `cave.py`
and silently left out of the export, each caught only by chance later. A comment
asking future editors to remember is precisely what had already failed, so the
check is mechanical.

---

## 10. Console state machine

```
BOOT ──► TITLE ──confirm──► [MENU]* ──► READY ──confirm──► PLAY ──┬─died──► GAMEOVER ─┐
  ▲                                            │                   │
  │                                            └─won───► VICTORY ──┤
  │                                                                │
  │                                                        qualifying?
  │                                                          │      │
  └────────── SCORES ◄──── INITIALS ◄─────────yes────────────┘      │
                 ▲                                                  │
                 └──────────────────────no─────────────────────────┘

* MENU skipped while only one game is registered.
```

**READY is not optional.** A run that begins on entry is unplayable: the opening
gap gives 248 ms before impact against ~250 ms of human reaction time. The world
holds frozen until `confirm`, and that same press is the first thrust. See
GAME_DESIGN §4. `Game` needs a way to express this — either a `ready()` phase
before `update()` starts advancing, or the console holding the first frame until
input arrives.

`Game::finished()` alone is not enough once the game is winnable — the console
has to know *how* it ended. Either add `Game::outcome()` returning
died/won, or let `rank()` carry it. The former is cleaner; VICTORY and GAMEOVER
are different screens and a win should always qualify for the table.

Idle in TITLE or SCORES past a timeout → **deep sleep**, waking on the button.
For a handheld this matters more than battery capacity: microamps asleep means
it survives weeks in a pocket and wakes instantly (HARDWARE.md §3.2 — the wake
pin still needs confirming).

---

## 11. Proposed layout

```
firmware/plato/
  platform.ino / main.cpp
  platform/   input.h  timing.h  canvas.h  audio.h
  console/    console.h/.cpp   scores.h/.cpp   menu.h/.cpp
  games/      game.h   cave.h/.cpp
  assets/     bust.h   labels.h   constants.h    (all generated)
tools/
  bake_assets.py   bake_constants.py             (to write)
  cave.py  preview.py  image_treatments.py       (design prototypes)
```

**Build with PlatformIO.** Arduino IDE works but handles multi-file C++ projects
poorly, and this is a multi-file project. M5Unified is in the PlatformIO
registry.

Partition: the default 8 MB scheme gives ~3 MB app, which holds dozens of games
at ~20–50 KB each. A single-app no-OTA scheme extends that toward ~6 MB if ever
needed.

---

## 12. Build order

1. Blink and draw — confirm the panel, rotation, and **the button count**.
2. `platform/` — input mapping, clamped timing, canvas.
3. Cave rendering, still-frame, no physics. Compare against
   `preview/cave_stages.png`.
4. Physics and collision. **Re-check gravity/thrust/clamp here** — they were
   tuned by playtest in the browser, but with a keyboard, not a thumb on a
   48 mm device. Start from the baked values; expect to move them.
5. Stage progression and palette. Verify against the timings in GAME_DESIGN §9.
6. Console shell: title, game over, scores, NVS.
7. Initials entry — last, because it depends on the button answer.
8. Audio.
9. Deep sleep.

Steps 1 and 4 are the ones that can invalidate design decisions, so they come
early.

---

## 13. Open

- Button count cascades into input mapping and initials entry (§4).
- Deep-sleep wake pin unconfirmed (§10).
- Whether `Canvas` wraps `M5Canvas` or aliases it. Start with an alias; wrap
  only if a second backend ever appears.
- Menu design deferred until a second game exists — the state machine skips it
  meanwhile.
