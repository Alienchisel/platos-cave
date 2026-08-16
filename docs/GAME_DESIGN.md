# Plato's Cave — Game Design

**Status:** visuals prototyped at panel resolution in `tools/cave.py`. **Feel is
entirely unprototyped** — an autopilot flies the demo, so every constant below
governing gravity, thrust and pacing is a guess awaiting a thumb.

**Target:** M5StickS3, 240 × 135 landscape. See [HARDWARE.md](HARDWARE.md).

---

## 1. Concept

An SFCave-style one-button cave flyer. You are a point of light ascending out of
Plato's cave. Gravity pulls you down; holding the button thrusts you up; touching
rock ends the run.

**The game can be won**, and winning means going back down. Reaching the sun is
the halfway point; the return to the chains is the second half and the harder
one. See §3a.

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

Each stage takes 32–50% longer than the one before, so the sun is a 3½-minute
achievement rather than something you stumble into. Times assume uninterrupted
flight; they are *frame-rate independent* (see §9).

The sun is then **held for 3 000 distance (~30 s)** before the return begins —
the one stretch of the game that is a reward rather than a test, though it is
still at maximum speed and minimum gap.

---

## 3a. The return — how the game is won

Reaching the sun is not the end. In *Republic* ~516e–517a the freed prisoner is
obliged to go back down, and his eyes are now useless in the dark — he is worse
at reading shadows than those who never left. **The game is won by getting back
to the chains.**

| # | Region | Reached | Interval | Light (vs ascent) | Gap | View |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | **ΣΕΛΗΝΗ** | 4:02 | +30.0 s | 147 *(was 204)* | 28.3 | 1.99 s |
| 9 | **ΑΣΤΡΑ** | 4:33 | +30.4 s | 108 *(was 163)* | 26.5 | 1.80 s |
| 10 | **ΥΔΩΡ** | 4:57 | +24.4 s | 76 *(was 128)* | 24.9 | 1.67 s |
| 11 | **ΕΙΔΩΛΑ** | 5:16 | +19.5 s | 50 *(was 92)* | 23.5 | 1.57 s |
| 12 | **ΠΥΡ** | 5:33 | +16.1 s | 29 *(was 61)* | 22.3 | 1.49 s |
| 13 | **ΣΚΙΑΙ** | 5:46 | +13.2 s | 15 *(was 36)* | 21.2 | 1.43 s |

**Full run 5:46.** Ascent 3:32, sun 0:30, return 2:14.

### Why the return needs its own mechanics

Both ascent levers are **spent** by the time you reach the sun: the gap floors at
distance 12 000 and the speed caps at 16 000. Replaying the ascent would be
strictly *easier*, because by then you know it. So the descent uncaps them and
adds two more.

**1. Speed uncaps** — 100 → 145 columns/second. Speed is the primary descent
lever because the gap has a hard floor near the player's own height (~7 px)
while reaction time does not.

**2. The dazzle** — every region is dimmer coming down than it was going up, per
the table above. This is the text made mechanical, and it reuses the dither
density that already carries the whole rendering. The final ΣΚΙΑΙ sits at
**15/255** — about six percent of the passage lit.

That stays playable only because **the 1 px rock edge draws regardless of dither
density.** The edge carries legibility; the fill carries atmosphere. Remove the
edge and near-total darkness becomes unfair rather than brutal.

**3. The view closes in** — a darkness creeping from the right, eating forward
view directly rather than by proxy. It is applied *after* the rock edge is drawn
so the edge is occluded too; occlude only the fill and the passage ahead stays
readable and the mechanic does nothing.

**4. Intervals shrink** — 30, 30, 24, 20, 16, 13 s. The return is compressed as
well as darker, so the collapse accelerates. Ascent: long, escalating,
learnable. Return: compressed, dark, brutal.

### ΠΕΡΙΑΓΩΓΗ — the turn

*Republic* 518d: education is not putting sight into blind eyes but **turning the
whole soul around**. Plato's word for that is *periagoge*, and reaching the sun
and starting back down is precisely it.

So the turn gets its own banner — centred, larger than a region caption, held
1.6 s rather than 0.5 s. It is the only moment in the run that interrupts the
frame rather than annotating its corner, which is right: it is the hinge the
whole design turns on.

### Two deaths

Dying on the way up and dying on the way back are not the same event.

| | | |
| --- | --- | --- |
| **ΔΕΣΜΩΤΗΣ** | *prisoner* | died ascending — fire-orange |
| **ΤΥΦΛΟΣ** | *blind* | died returning — dazzled pale |

516e says the returning man's eyes are full of darkness. Once you have been
freed you are not a prisoner any more, so the word changes, and so does the
colour. *This resolves the death-screen question that stood in §10.*

### Region texture

Two of the seven regions name something that **moves**, so they get more than a
colour. Both are keyed by name, so the return gets them too.

- **ΠΥΡ flickers.** Firelight is not steady. The dither density swings about 20
  levels either side of 61/255, at 0.8–2.1 Hz. Driven by *distance*, not frame
  count, so it flickers at the same rate whatever the frame rate.
- **ΑΣΤΡΑ has stars.** Sparse bright points scattered through the rock — which
  by that stage reads as sky, not stone. Placed by **world** position rather
  than screen position, or they would swim across the rock as the cave scrolls.
  Confined to the rock: the passage already has its dither, and stars in it
  would read as noise.

**ΥΔΩΡ has no texture — a reflection was built and rejected.** Recorded so it
isn't proposed again from scratch, and because one finding constrains any future
attempt.

The lower rock was made a pool, with a skim of broken light on its edge and the
player's double mirrored below, sinking as the player climbed. It worked
mechanically and was rejected on look.

The finding worth keeping: **there is no ceiling shape to reflect.** The cave's
walls are *parallel* — `top` and `bot` are both `centre ± gap/2` — so mirroring
the ceiling about the floor yields the floor's own curve translated downward, and
reads as a duplicate contour rather than as water. That was the first attempt.
Only the player moves independently of the walls, so only the player can be
mirrored legibly. Any future water idea has to start from that.

### Obstacles

Free-floating blocks belong **to the return only**, if they are used at all. On
the ascent they compete with the brightness arc for visual space; on the return
they have a home. *This resolves the open question that stood in §10.*

### ⚠ Tuning risk: the closing view may be unfair

`VIEW_CLOSE = 0.55` swallows 52% of the screen by the chains, leaving **83
columns = 0.60 s of clear warning**, against 3.62 s at the start. Simple visual
reaction time is ~0.25 s, so that is roughly a third of a second to decide *and*
execute.

`VIEW_CLOSE = 0.40` gives 0.82 s. **Unresolved until it is played** — it is the
first constant to revisit if the return proves unfair rather than merely hard.

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

### ⚠ A run must not begin until the player presses

**Required behaviour, found by playtest.** From a standing start the opening gap
leaves **248 ms before you hit the floor** — against a human simple visual
reaction time of about **250 ms**. A run that begins the moment it loads is
already lost, and the first playtest feedback was exactly that: *"I keep dying
within the first second."*

So a fresh run holds at the middle of the passage with the world frozen, and the
**first press both starts the run and counts as the first thrust** — by the time
gravity applies, the player is already climbing.

This is not a web-build nicety. The firmware needs it too, or the device is
unplayable on power-on.

For reference, time-to-floor from rest at each stage:

| | gap | from rest |
| --- | --- | --- |
| start | 64.8 px | 248 ms |
| ΕΙΔΩΛΑ | 59.3 px | 237 ms |
| ΣΕΛΗΝΗ | 34.7 px | 182 ms |
| the chains | 21.2 px | 142 ms |

The later figures are tighter still but are *not* a problem: by then the player
is flying, never at rest. Only the standing start is unfair.

### The player

A pure white 2 × 2 core inside a dark halo. White because it must read against
everything from near-darkness to full sun.

**It stays a dot.** A chariot sprite was drawn and tested: at 15 × 9 it nearly
fills the 21 px passage at the chains, leaving ~3 px of clearance either side,
and would need a hitbox far smaller than the drawing — which lies to the player,
the worst kind of difficulty. At 9 × 5 it is an unreadable blob. The dot is also
already the right image: a point of light in a cave.

### The trail — two horses

The *Phaedrus* (246a–254e) has the soul as a charioteer with two horses, one
noble and one unruly, pulling opposite ways. **That is already the control
scheme** — thrust against gravity, with the player holding the balance. So the
trail shows it rather than a sprite depicting it: two strands, whichever is being
obeyed running bright while the other lags, diverging with age like reins.

Note this is a second dialogue. The game's structure is the *Republic*'s cave;
the chariot is *Phaedrus*. Both are ascent myths about the soul, so the blend is
defensible, but it is a blend.

`TWIN_TRAIL = False` gives a single strand.

### ⚠ Two constraints the trail must honour

Both were discovered by the trail being invisible above ΥΔΩΡ, and **neither fix
alone was sufficient**:

1. **Draw it as connected segments, never isolated points.** A single pixel
   cannot compete with a single-pixel dither — in a 50–80% lit field one
   differently-coloured pixel is simply another dither cell.
2. **Flip its polarity on the region's light.** Brighter than the passage below
   128/255, darker above. A trail that only brightens has nothing to brighten
   into once the passage is near-solid pale.

Verified from ΣΚΙΑΙ 36/255 through ΣΕΛΗΝΗ 204/255.

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

Eight entries at 13 px sit comfortably in 135 px with a header. Nine do not.
Stored in NVS via `Preferences`; ~70 bytes.

**Initials persist between runs.** Entry opens on the last name committed rather
than on ΑΑΑ, so a repeat player confirms with three holds instead of walking the
alphabet again. On one button, with runs ending around fifty seconds, retyping is
the single largest tax the shell imposes — and the name almost never changes.
Three more bytes in NVS. An unreadable stored value falls back to ΑΑΑ, since the
failure mode otherwise is an entry screen showing a letter no button can reach.

### The default table

Not AAA/BBB, and not arbitrary — **the ordering carries the joke.** The header
means *those who were released*, so the top of the table belongs to the people
who claimed to have made the ascent, and the bottom to the people who merely
heard it described.

| | | |
| --- | --- | --- |
| 1 | **ΠΛΩ** | Plotinus — a completed run |
| 2 | **ΠΟΡ** | Porphyry |
| 3 | **ΙΑΜ** | Iamblichus |
| 4 | **ΠΡΟ** | Proclus |
| 5 | **ΔΑΜ** | Damascius — last head of the Academy |
| 6 | **ΣΩΚ** | Socrates — he only described it |
| 7 | **ΓΛΑ** | Glaucon — he only listened |
| 8 | **ΘΡΑ** | Thrasymachus — he argued against the premise |

Every Neoplatonist is past the sun; nobody from the *Republic* reaches it. And
the distances were picked so ΣΕΛΗΝΗ lands at rows 5 and 6 — Damascius descending,
Socrates ascending — with ΠΥΡ likewise at rows 2 and 8. The same regions in
opposite directions, told apart only by the arrow, which is also the clearest
demonstration of why the arrow exists.

**Plato is deliberately absent.** He is the bust on the title screen, presiding
over the table rather than competing in it.

Porphyry (*Life of Plotinus* 23) reports his teacher reaching union four times in
their years together, and himself once at sixty-eight — which is what puts those
two at the top. It is his account of his own master written long after, so the
ranking is a joke resting on hagiography, not a claim about anything. That note
belongs in the code, not on the screen.

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

### Difficulty steps per region

Each region sets its **own** gap and scroll rate, eased in over `STEP_SPAN`
(120 distance, ~1.7 s) at the boundary. A region change is therefore a felt
mechanical event, not only a change of palette.

| region | gap | scroll | warning |
| --- | --- | --- | --- |
| ΣΚΙΑΙ | 64.8 px | 55 col/s | 3.62 s |
| ΠΥΡ | 56.7 | 66 | 3.02 |
| ΕΙΔΩΛΑ | 50.0 | 76 | 2.62 |
| ΥΔΩΡ | 44.6 | 84 | 2.37 |
| ΑΣΤΡΑ | 39.1 | 91 | 2.19 |
| ΣΕΛΗΝΗ | 35.1 | 97 | 2.05 |
| ΗΛΙΟΣ | 31.1 | 103 | 1.93 |
| ΣΕΛΗΝΗ ↓ | 29.0 | 110 | 1.81 |
| ΑΣΤΡΑ ↓ | 27.0 | 117 | 1.70 |
| ΥΔΩΡ ↓ | 25.0 | 124 | 1.60 |
| ΕΙΔΩΛΑ ↓ | 23.0 | 131 | 1.52 |
| ΠΥΡ ↓ | 21.6 | 138 | 1.44 |
| ΣΚΙΑΙ ↓ | 20.2 | 145 | 1.37 |

**Why this replaced continuous ramps.** Under the old scheme a typical run met
**17% of the narrowing and 8% of the acceleration** before it ended — the whole
escalation lived past where anyone actually played, and regions were colours
rather than difficulties. The same run now meets **33% and 23%**, and more
importantly the *first* boundary at 12.7 s is a real event: 64.8 → 56.7 px and
55 → 66 col/s, cutting the warning from 3.62 s to 3.02 s.

The table is **front-loaded** deliberately. Real play ends around region 3, so
the early steps must carry a meaningful share of the range or the curve still
never participates. Endpoints are unchanged (0.48 H → 0.15 H, 55 → 145 col/s);
only their distribution moved.

Steps **ease** rather than snap. Instant would be unfair as well as jarring — the
passage could narrow around a player already committed to a line.

*This does not make the game easier. It makes the difficulty arrive.*

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

### ⚠ The passage must not outrun the player

**Found by playtest, and it was a bug.** The drift is defined *per column*, but
the scroll accelerates — so the passage's vertical speed in **px/second** rose
with it. Measured before the fix:

| | scroll | passage 3σ | passage max | player ceiling |
| --- | --- | --- | --- | --- |
| start | 55 col/s | 110 px/s | 143 px/s | 135 px/s |
| ΣΕΛΗΝΗ | 83 col/s | 166 px/s | 215 px/s | 135 px/s |
| the chains | 140 col/s | **280 px/s** | **363 px/s** | 135 px/s |

From ΣΕΛΗΝΗ onward the cave could climb faster than any player could follow, and
by the chains roughly twice as fast. Late-game deaths were **partly unavoidable
rather than earned**, which is the one thing a difficulty curve may not be.

`Cave.step` now scales the drift by `SPEED_START / speed_at(dist)`, holding the
passage's px/second wander at its start-of-run value — a rate playtesting had
already shown to be fair. Difficulty is left to the two levers meant to carry it:
the narrowing gap and the shrinking forward view.

**The symptom that exposed it** was the autopilot preferring a *higher* velocity
clamp than the player did. It wasn't disagreeing about feel — it was chasing a
passage that moved too fast, and needed the speed to keep up.

**Consequence to watch:** the autopilot went from completing **0/5** runs to
**5/5**. That confirms the endgame was impossible rather than merely hard, but it
means the difficulty that remains is now entirely legitimate — and possibly not
enough. If the game now plays too easy, the fix is the gap or the scroll, not
restoring a generator that outran the player.

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

1. **⚠ Pacing may be far too long — the open question that matters most.**
   Real play reaches **region 3 of 13**, about 7% of the run. Everything from
   ΥΔΩΡ onward — the cyan of leaving the cave, the stars, ΠΕΡΙΑΓΩΓΗ, the entire
   return, ΤΥΦΛΟΣ, ΚΑΤΕΒΗΝ — has never been seen in ordinary play.

   | reach | time | region |
   | --- | --- | --- |
   | 1 000 | 0:17 | ΠΥΡ 2/13 |
   | **2 422** | **0:41** | **ΕΙΔΩΛΑ 3/13** ← observed |
   | 5 000 | 1:20 | ΥΔΩΡ 4/13 |
   | 9 900 | 2:25 | ΣΕΛΗΝΗ 6/13 |
   | 16 000 | 3:32 | ΗΛΙΟΣ 7/13 |

   This was predicted when the pacing was stretched 8× to fix the opposite
   problem — the note at the time read *"may have overshot the other way"* — and
   is now confirmed rather than suspected.

   **Do not retune on this data yet.** It predates the drift fix, which took the
   autopilot from 0/5 to 5/5 and may move a human's reach substantially. Gather
   post-fix numbers first. If compression is needed, the growth rate between
   regions (currently 32–50% per stage) is the dial, not the physics.
2. **Death behaviour.** Pure restart is the SFCave contract, and it bites harder
   now there is 5:46 to lose. Checkpointing at the sun would be merciful and
   would badly undercut the return. *Recommendation: pure restart.*
2. **Dither at ΗΛΙΟΣ** — see §4.
3. **`VIEW_CLOSE`** — see §3a. The most likely constant to be wrong.
4. **Initials entry scheme** — blocked on button count.

*Resolved: **stage pacing** — the ascent runs 212.6 s, frame-rate independent
(§9). **Win condition** — reaching the chains after the return (§3a).
**Obstacles** — the return only, if at all (§3a). **Death screen** — two words,
ΔΕΣΜΩΤΗΣ ascending and ΤΥΦΛΟΣ returning (§3a). **Win screen** — ΚΑΤΕΒΗΝ, the
Republic's first word.*

*Still guesses: the three physics constants, and now `VIEW_CLOSE`.*

---

## 11. What exists

| | State |
| --- | --- |
| Cave generation, scrolling, collision bounds | prototyped, `tools/cave.py` |
| Seven-stage ascent, progression and palette | prototyped |
| The return: dazzle, closing view, uncapped levers | modelled, `tools/model_descent.py` |
| Thirteen regions baked to `constants.h` | done, structurally verified |
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
