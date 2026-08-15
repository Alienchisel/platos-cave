#!/usr/bin/env python3
"""
Plato's Cave -- an SFCave-alike for the T-QT Pro, prototyped at 128x128 1-bit.

    python cave.py --seed 3

Renders title and gameplay to GIFs so the look and the difficulty curve can be
judged before any of it is written in C. A crude autopilot flies the demo; the
feel of gravity and thrust can only really be tuned on the hardware.

The ascent follows Republic 514a-517a in order: shadows, fire, carried images,
reflections in water, stars, moon, sun. Background dither density rises with
the stage, so the screen literally brightens as you climb, and the final stage
inverts -- you leave the cave into full light.
"""

import argparse
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "C:/Windows/Fonts/consola.ttf"

# Set by configure(). Kept as module globals so the whole file can be retargeted
# at a different panel without threading a config object through everything.
W = H = 128
PLAYER_X = 22
TILE = None

# 8x8 Bayer, the same matrix the image treatments use.
BAYER = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21],
], np.float32) / 64.0
def configure(w: int, h: int) -> None:
    """Retarget to a panel size. Everything geometric derives from H.

    The player sits a fixed fraction in from the left, so a wider screen buys
    forward view -- which is the whole reason a landscape panel plays better.
    """
    global W, H, PLAYER_X, TILE
    W, H = w, h
    PLAYER_X = max(8, round(w * 0.17))
    TILE = np.tile(BAYER, (h // 8 + 1, w // 8 + 1))[:h, :w]


configure(128, 128)

# The rock is always near-black and the passage is what fills with light, so the
# screen goes from near-dark to blazing across a run. The floor of 0.14 exists
# because a fully unlit passage against dark rock is unplayable.
#
# Each stage keeps its own light colour, because the allegory names its own light
# source at every step: firelight underground, then water and stars and moon at
# night outside, then the sun. That gives a warm-cool-warm arc for free.
#             name       from  light  rock          glow
STAGES = [("ΣΚΙΑΙ",     0, 0.14, (6, 7, 11),   (78, 88, 104)),    # shadows
          ("ΠΥΡ",     700, 0.24, (15, 7, 4),   (236, 116, 36)),   # the fire
          ("ΕΙΔΩΛΑ", 1800, 0.36, (17, 11, 4),  (248, 180, 74)),   # carried images
          ("ΥΔΩΡ",   3400, 0.50, (4, 13, 17),  (84, 198, 222)),   # water
          ("ΑΣΤΡΑ",  6000, 0.64, (7, 6, 18),   (152, 150, 242)),  # the stars
          ("ΣΕΛΗΝΗ", 9900, 0.80, (11, 13, 19), (206, 224, 255)),  # the moon
          ("ΗΛΙΟΣ", 16000, 1.00, (20, 15, 6),  (255, 246, 214))]  # the sun

# ---- pacing ---------------------------------------------------------------
# Everything here is per SECOND, never per frame. Frame-rate independence is not
# a nicety: at 3.2 distance/frame the original thresholds put the sun at ~25s on
# a 50 fps device and ~14s on a 90 fps one. The ascent has to mean the same thing
# whatever the hardware manages.
#
# Distance is measured in cave columns. Two difficulty levers run together:
# the passage narrows, and the scroll accelerates -- the latter shrinks forward
# view measured in *time*, from ~3.6 s of warning at the start to ~2.0 s at the
# sun, which is the reaction budget that actually governs difficulty.
SPEED_START, SPEED_END = 55.0, 100.0   # columns/second
SPEED_RAMP_END = 16000                 # distance at which SPEED_END is reached
GAP_START, GAP_MIN = 0.48, 0.21        # as a fraction of H
GAP_RAMP_END = 12000                   # distance at which GAP_MIN is reached

# Physics, scaled by H so the feel survives a change of panel. Thrust replaces
# gravity while held, it does not add to it.
GRAVITY = 7.8       # * H  px/s^2, downward
THRUST = -9.6       # * H  px/s^2, while the button is held
VY_MAX = 1.26       # * H  px/s


def speed_at(dist):
    """Scroll rate in columns/second at a given distance."""
    return SPEED_START + (SPEED_END - SPEED_START) * min(1.0, dist / SPEED_RAMP_END)


def gap_at(dist):
    """Passage height in pixels. A pure function of distance, so it cannot drift
    with frame rate the way an incremental shrink did."""
    t = min(1.0, dist / GAP_RAMP_END)
    return H * (GAP_START - (GAP_START - GAP_MIN) * t)


def stage_for(dist):
    s = STAGES[0]
    for cand in STAGES:
        if dist >= cand[1]:
            s = cand
    return s


class Cave:
    """Rolling column buffer: gap centre wanders, gap height shrinks."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.centre = H / 2
        self.gap = gap_at(0)
        self.drift = 0.0
        self.cols = [(self.centre, self.gap) for _ in range(W)]

    def step(self, dist):
        """Advance exactly one column. Called n times per frame by the caller,
        where n follows from scroll speed -- so the cave's shape per column is
        frame-rate independent by construction."""
        # Random walk with a restoring pull, so it wanders without escaping.
        self.drift += self.rng.uniform(-0.42, 0.42)
        self.drift = max(-2.6, min(2.6, self.drift)) * 0.94
        self.centre += self.drift
        self.gap = gap_at(dist)
        margin = self.gap / 2 + H * 0.06
        if self.centre < margin:
            self.centre, self.drift = margin, abs(self.drift)
        if self.centre > H - margin:
            self.centre, self.drift = H - margin, -abs(self.drift)
        self.cols.pop(0)
        self.cols.append((self.centre, self.gap))

    def bounds(self, x):
        c, g = self.cols[x]
        return c - g / 2, c + g / 2


def draw_frame(cave, py, trail, dist, flash):
    name, _, light, rock, glow = stage_for(dist)
    glow_a = np.array(glow, np.float32)
    unlit = (glow_a * 0.13).astype(np.uint8)      # passage where no dot falls

    # Three tones: rock, unlit passage, lit passage. Still a dither, just no
    # longer black and white -- the pattern is what makes it read as deliberate.
    canvas = np.empty((H, W, 3), np.uint8)
    canvas[:] = unlit
    canvas[TILE < light] = glow

    ys = np.arange(H)[:, None]
    tops = np.array([cave.bounds(x)[0] for x in range(W)])[None, :]
    bots = np.array([cave.bounds(x)[1] for x in range(W)])[None, :]
    canvas[(ys < tops) | (ys > bots)] = np.array(rock, np.uint8)

    img = Image.fromarray(canvas)
    d = ImageDraw.Draw(img)

    # A hard edge on the rock, so the passage still reads once the dither
    # density climbs and the fill alone stops carrying the boundary.
    for x in range(W):
        top, bot = cave.bounds(x)
        d.point((x, int(top)), fill=glow)
        d.point((x, int(bot)), fill=glow)

    trail_col = tuple((glow_a * 0.45).astype(int))
    for i, (tx, ty) in enumerate(trail):
        if i % 2 == 0:
            d.point((tx, ty), fill=trail_col)

    # Bright core inside a dark halo: reads against rock and against full sun.
    d.ellipse([PLAYER_X - 3, py - 3, PLAYER_X + 3, py + 3], fill=tuple(rock))
    d.rectangle([PLAYER_X - 1, py - 1, PLAYER_X + 1, py + 1], fill=(255, 255, 255))

    small = ImageFont.truetype(FONT, 10)
    label = f"{int(dist)}"
    d.text((W - 4 - d.textlength(label, font=small), 2), label,
           font=small, fill=glow)
    if flash > 0:
        w = d.textlength(name, font=small)
        d.rectangle([(W - w) / 2 - 4, H - 26, (W + w) / 2 + 3, H - 12],
                    fill=tuple(rock))
        d.text(((W - w) / 2, H - 25), name, font=small, fill=glow)
    return img


def dithered_bust(path, size):
    """Bayer-dither the photo at the size it will be shown.

    Dithering at 128 and then scaling down destroys the pattern -- nearest
    neighbour drops half the cells and the face turns to gravel. The dither has
    to be generated at the final resolution.
    """
    import image_treatments
    g = image_treatments.prepare(path, 1.0, crop=True, size=size)
    tile = np.tile(BAYER, (size // 8 + 1, size // 8 + 1))[:size, :size]
    bits = (g > tile).astype(np.uint8) * 255
    return Image.fromarray(np.dstack([bits] * 3))


def title_frame(bust, blink):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    img.paste(bust, ((W - bust.width) // 2, 4))
    d = ImageDraw.Draw(img)
    small = ImageFont.truetype(FONT, 10)
    tiny = ImageFont.truetype(FONT, 9)
    for i, line in enumerate(("CAN YOU ESCAPE", "PLATO'S CAVE?")):
        w = d.textlength(line, font=small)
        d.text(((W - w) / 2, 80 + i * 12), line, font=small, fill=(255,) * 3)
    if blink:
        msg = "[ PRESS UP ]"
        w = d.textlength(msg, font=tiny)
        d.text(((W - w) / 2, 110), msg, font=tiny, fill=(150,) * 3)
    return img


def simulate(seed, seconds, fps=50, render=True):
    """Run the game for `seconds` of wall-clock time at `fps`.

    Returns (frames, log). With render=False no images are produced, which makes
    it cheap enough to sweep frame rates and verify they agree.
    """
    cave = Cave(seed)
    py, vy = H / 2, 0.0
    dt = 1.0 / fps
    trail, out, log = [], [], []
    dist, col_accum, flash, prev = 0.0, 0.0, 0, STAGES[0][0]

    for step_i in range(int(seconds * fps)):
        top, bot = cave.bounds(PLAYER_X)
        target = (top + bot) / 2
        # Autopilot for the demo only; a human holds one button instead.
        thrust = py > target - 2
        vy += (THRUST if thrust else GRAVITY) * H * dt
        vy = max(-VY_MAX * H, min(VY_MAX * H, vy))
        py += vy * dt

        advance = speed_at(dist) * dt
        dist += advance
        col_accum += advance
        while col_accum >= 1.0:
            cave.step(dist)
            col_accum -= 1.0

        name = stage_for(dist)[0]
        if name != prev:
            log.append((name, step_i * dt, dist))
            flash = int(0.5 * fps)
        else:
            flash = max(0, flash - 1)
        prev = name

        if render:
            trail.append((PLAYER_X, int(py)))
            trail = trail[-16:]
            out.append(draw_frame(cave, py, trail, dist, flash))

        if py < top or py > bot:            # demo just keeps going
            py, vy = (top + bot) / 2, 0.0
    return out, log


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--seconds", type=float, default=230.0,
                    help="wall-clock run length; the full ascent is ~213 s")
    ap.add_argument("--fps", type=int, default=50)
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--bust", type=Path,
                    default=here.parent / "image" / "plato.png")
    ap.add_argument("--out", type=Path, default=here.parent / "preview")
    args = ap.parse_args()

    frames, log = simulate(args.seed, args.seconds, args.fps)
    print(f"simulated {len(frames)} frames = {args.seconds:.0f}s at {args.fps} fps")
    for name, t, d in log:
        print(f"  {name:<8} at {t:6.1f}s   dist {d:.0f}")

    # Subsample to a fixed budget: a full 213 s ascent is ~10k frames and would
    # otherwise produce a GIF of absurd size.
    keep = frames[::max(1, len(frames) // 220)]
    big = [f.resize((W * args.scale, H * args.scale), Image.NEAREST) for f in keep]
    gif = args.out / "cave.gif"
    big[0].save(gif, save_all=True, append_images=big[1:], duration=60, loop=0)

    bust = dithered_bust(args.bust, 74)
    tf = [title_frame(bust, b) for b in (True, True, False)]
    tbig = [f.resize((W * args.scale, H * args.scale), Image.NEAREST) for f in tf]
    tgif = args.out / "cave_title.gif"
    tbig[0].save(tgif, save_all=True, append_images=tbig[1:], duration=500, loop=0)

    # One frame per stage, to check the brightness ramp end to end. Indexed off
    # the transition log rather than recomputed, so it stays right when the
    # pacing is retuned.
    sheet = Image.new("RGB", (W * 2 * len(STAGES), H * 2))
    marks = [0] + [int(t * args.fps) for _, t, _ in log]
    for i in range(len(STAGES)):
        idx = min(len(frames) - 1, (marks[i] if i < len(marks) else 0) + 40)
        sheet.paste(frames[idx].resize((W * 2, H * 2), Image.NEAREST), (i * W * 2, 0))
    sheet.save(args.out / "cave_stages.png")

    print(f"wrote {gif}\nwrote {tgif}\nwrote {args.out / 'cave_stages.png'}")


if __name__ == "__main__":
    main()
