# Plato's Cave — Game Design

**Status:** visuals prototyped at panel resolution in `tools/cave.py`. **Feel is
entirely unprototyped** — an autopilot flies the demo, so every constant below
governing gravity, thrust and pacing is a guess awaiting a thumb.

**Target:** M5StickS3, 240 × 135 landscape. See [HARDWARE.md](HARDWARE.md).

---

## 1. Concept

An SFCave-style one-button cave flyer. You are a point of light ascending out of
Plato's cave. Gravity pulls you down; holding the button thrusts you up; touching
rock ends the run. Distance is score.

Tagline, shown on the title screen: **CAN YOU ESCAPE PLATO'S CAVE?**

The conceit is not decoration. Plato's ascent in *Republic* 514a–517a is an
ordered sequence of light sources, and that sequence supplies the game's entire
progression structure and palette.

---

## 2. Core mechanic

Classic SFCave, unchanged because it does not need changing:

- Constant horizontal scroll; the player's x position is fixed.
- Gravity accelerates the player downward every frame.
- Holding the button accelerates upward instead.
- Vertical velocity is clamped.
- Contact with rock, above or below, ends the run.
- The passage wanders vertically and narrows with distance.

One button is the whole control scheme. That is the reason this game suits the
hardware: see the button-count caveat in HARDWARE.md §3.1.

---

## 3. The ascent — seven stages

Straight from the allegory, in Plato's order. Each stage names its own light
source, which supplies its colour.

| # | Stage | Meaning | Light | Distance | Reached at | Interval |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **ΣΚΙΑΙ** | shadows on the wall | cold grey-blue, near-dark | 0 | 0 s | — |
| 2 | **ΠΥΡ** | the fire behind the prisoners | orange | 700 | 12.5 s | +12.5 |
| 3 | **ΕΙΔΩΛΑ** | the carried images | amber-gold | 1 800 | 31.3 s | +18.8 |
| 4 | **ΥΔΩΡ** | reflections in water | cyan | 3 400 | 57.0 s | +25.7 |
| 5 | **ΑΣΤΡΑ** | the stars | indigo | 6 000 | 95.1 s | +38.2 |
| 6 | **ΣΕΛΗΝΗ** | the moon | pale silver-blue | 9 900 | 145.6 s | +50.5 |
| 7 | **ΗΛΙΟΣ** | the sun | white-gold | 16 000 | 212.6 s | +66.9 |

Each stage takes roughly 35% longer than the one before, so the sun is a
3½-minute achievement rather than something you stumble into. Times assume
uninterrupted flight; they are *frame-rate independent* (see §9).

Two structural properties fall out of the text rather than being imposed:

- **A warm → cool → warm arc.** Firelight underground, night sky on first
  emerging, then the sun.
- **The largest colour jump lands on the narrative break.** Orange to cyan,
  between ΕΙΔΩΛΑ and ΥΔΩΡ, is the moment you leave the cave.

The stage name flashes briefly on transition; otherwise the HUD is just the
distance readout.

---

## 4. Visual design

### Brightness is the progress bar

The rock is always near-black. The **passage** is what fills with light, its
Bayer dither density rising with each stage. You begin threading a barely-visible
channel through darkness and end in blazing light. Progress is not a number in
the corner — it is how much you can see.

### Three tones per stage

1. **Rock** — near-black, tinted slightly toward the stage colour so it is never
   dead flat.
2. **Unlit passage** — the stage's glow colour at ~13%.
3. **Lit passage** — the stage's glow colour at full.

Plus a **1 px hard edge** in the glow colour along the rock boundary. This is
load-bearing: once dither density climbs, the fill alone stops carrying the
boundary and the passage becomes unreadable without it.

### Keep the dither

Two-tone dithering rather than smooth gradients is what makes this read as
deliberate rather than as a generic gradient game, and it keeps density-as-progress
legible. It is also cheap — the renderer stays effectively 1-bit with a per-stage
palette lookup.

### The player

A pure white 2 × 2 core inside a dark halo, with a short fading trail. White
because it must read against everything from near-darkness to full sun.

### Open: the sun erases the dither

At ΗΛΙΟΣ the light level reaches 1.0 and the dither disappears entirely — the
passage goes solid. Arguably correct: you have reached the sun, there are no more
shadows, and the texture that carried you the whole way is gone. But the final
stage then lacks the grain everything else has. Capping around 0.92 leaves a
trace. **Undecided.**

---

## 5. Orientation and layout

Everything in the game flow is **landscape 240 × 135**, by software rotation of
the native portrait panel. Rotating the device between title and gameplay would
feel broken.

Landscape roughly doubles forward view — ~199 px of warning against ~106 px on a
128 × 128 square — while leaving vertical space, and therefore difficulty,
essentially unchanged. It removes cheap deaths without making the game easier.

- **Title** — bust on the left, title stacked right, prompt and best score below
  a rule. An arcade attract screen.
- **Gameplay** — distance readout top-right; stage name flashes bottom-centre.
- **High scores** — the width buys real columns: rank, initials, score, and
  *stage reached*. That last column is what makes it a table rather than a list.

---

## 6. Game flow

```
TITLE ──A──► PLAY ──death──► GAME OVER ──► [INITIALS if qualifying] ──► HIGH SCORES ──A──► TITLE
```

### Title screen

Bayer-dithered Plato bust (dithered **at final size** — see §9), the tagline,
`[ PRESS A ]`, and the current best score.

### High-score table

Header: **ΟΙ ΛΥΘΕΝΤΕΣ** — roughly "those who were released." Plato describes the
prisoner being released from his bonds in the cave passage. *This phrase is a
formation for this project, not a quotation from the text.*

Eight entries at 13 px sit comfortably in 135 px with a header. Stored in NVS via
`Preferences`; ~70 bytes. Default entries are the *Republic*'s cast — ΣΩΚ, ΓΛΑ,
ΑΔΕ, ΚΕΦ, ΘΡΑ, ΠΟΛ — rather than AAA/BBB.

### Initials entry

Three Greek letters, arcade convention: one button cycles, one confirms.
**Blocked on the button-count question.** With a single programmable button this
becomes short-press to cycle, long-press to confirm — workable but worse.

---

## 7. Scoring

- Score is distance travelled.
- The table records score **and the stage reached**, which is the more legible
  achievement — "got to ΣΕΛΗΝΗ" reads better than a number.

---

## 8. Audio

Not yet designed. Constraints from HARDWARE.md: **synthesise, don't sample.**
8-bit 11 kHz mono runs ~11 KB/second; procedural tones cost ~0 bytes and suit the
aesthetic. Reserve samples for one or two signature sounds at most.

Obvious candidates: a thrust tone that pitches with velocity, a stage-transition
chime that shifts with the palette, a death sound, and a title jingle.

---

## 9. Pacing and constants

From `tools/cave.py`. **Every rate is per second, never per frame**, and every
geometric value derives from panel height `H`, so the game retargets to a
different panel or a different frame rate without changing character.

### Frame-rate independence is not optional here

The first pass accumulated distance per *frame*. That put the sun at ~25 s on a
50 fps device and ~14 s on a 90 fps one — the ascent would have meant something
different on every build. Verified fixed: stage timings across **30, 50, 70, 90
and 144 fps agree to 0.00%**.

### Two difficulty levers

| | Start | At the sun |
| --- | --- | --- |
| Passage height | 64.8 px | 28.3 px |
| Scroll rate | 55 col/s | 100 col/s |
| **Forward view** | **3.49 s** | **1.99 s** |

Forward view is the number that actually governs difficulty — it is the reaction
budget. The screen is a fixed width, so accelerating the scroll shrinks warning
time without touching the geometry. Narrowing alone would demand more precision;
narrowing *and* accelerating demands precision under pressure, which is the
better curve.

### Constants

| Constant | Value | |
| --- | --- | --- |
| `SPEED_START` → `SPEED_END` | 55 → 100 col/s | ramps over 16 000 distance |
| `GAP_START` → `GAP_MIN` | `0.48 H` → `0.21 H` | ramps over 12 000 distance |
| Centre drift | uniform ±0.42, clamped ±2.6, damped ×0.94 | per column |
| Wall margin | `gap/2 + H × 0.06` | |
| Player x | `W × 0.17` | |
| `GRAVITY` | `+7.8 H` px/s² | **guess** |
| `THRUST` | `−9.6 H` px/s² | **guess** — replaces gravity, doesn't add |
| `VY_MAX` | `±1.26 H` px/s | **guess** |

`gap_at(dist)` and `speed_at(dist)` are pure functions of distance, so they
cannot drift with frame rate the way an incremental shrink did.

The gap bottoms out at 12 000 distance (~170 s), before the sun at ~213 s, so the
last ~40 s is a plateau at minimum gap and maximum speed. That is the endurance
tail, and it is intentional.

**The three physics constants remain unvalidated.** They were converted from the
original per-frame guesses and have still never been driven by a human thumb.

---

## 10. Open decisions

1. **Death behaviour.** Pure restart is the SFCave contract, and "escape" wants
   it — you are dragged back to the chains. Checkpointing at your best stage is
   friendlier but softens the conceit. *Recommendation: pure restart.*
2. **Obstacles.** SFCave adds free-floating blocks once you are deep. Worth
   having, but they compete with the brightness arc for visual space.
   *Recommendation: introduce from ΥΔΩΡ onward, or not at all.*
3. **Death screen.** ΔΕΣΜΩΤΗΣ — *prisoner* — with distance and best. Blunt, but
   it lands.
4. **Dither at ΗΛΙΟΣ** — see §4.
5. **Initials entry scheme** — blocked on button count.

*Resolved: stage pacing. The ascent now runs 212.6 s and is frame-rate
independent; see §9. The three physics constants are still guesses.*

---

## 11. What exists

| | State |
| --- | --- |
| Cave generation, scrolling, collision bounds | prototyped, `tools/cave.py` |
| Seven-stage progression and palette | prototyped |
| Dither rendering, three-tone, hard edge | prototyped |
| Title screen | prototyped, both orientations |
| High-score table layout | mocked at 240 × 135 |
| Landscape/portrait comparison | rendered, `preview/orientation.png` |
| Pacing curve, frame-rate independent | verified across 30–144 fps |
| **Gravity/thrust feel** | **not prototyped** |
| Audio | not designed |
| Firmware | not written |

### Gotcha worth remembering

The title bust must be **Bayer-dithered at its final display size**. Dithering at
128 px and scaling down destroys the pattern — nearest-neighbour drops half the
cells and the face turns to gravel. `cave.dithered_bust()` does it correctly.
