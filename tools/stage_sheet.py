#!/usr/bin/env python3
"""
Reference sheet: every region of the ascent, with its palette and timings.

    python stage_sheet.py

Writes preview/stages_reference.png -- one row per stage, laid out vertically so
the brightening from ΣΚΙΑΙ to ΗΛΙΟΣ reads as a single ramp down the page. That
progression is the game's core mechanic, so it is worth being able to see all of
it at once.

Runs the simulation twice: once without drawing to find where the transitions
fall, then again drawing only the seven frames wanted. A full ascent is ~10k
frames and rendering all of them would be the entire cost of the tool.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import cave
import imgutil

FONT = "C:/Windows/Fonts/consola.ttf"


def hexof(rgb):
    return "#%02X%02X%02X" % tuple(int(v) for v in rgb)


def swatch(d, x, y, w, h, rgb, label, value, f_lbl, f_val):
    d.rectangle([x, y, x + w, y + h], fill=tuple(int(v) for v in rgb),
                outline=(70, 70, 70))
    d.text((x + w + 8, y - 1), label, font=f_lbl, fill=(200, 200, 200))
    d.text((x + w + 8, y + 12), value, font=f_val, fill=(120, 120, 120))


def build(seed, fps, seconds, zoom):
    # Pass 1: no drawing, just find the transitions.
    _, log = cave.simulate(seed, seconds, fps, render=False)
    reached = {name: (t, dist) for name, t, dist in log}

    # A moment *into* each stage, not at its boundary, so the palette is settled.
    marks, order = {}, []
    for name, start, *_ in cave.STAGES:
        if name == cave.STAGES[0][0]:
            step = int(3.0 * fps)
        elif name in reached:
            step = int(reached[name][0] * fps) + int(2.5 * fps)
        else:
            continue
        marks[step] = name
        order.append((name, step))

    frames_wanted = set(marks)
    frames, _ = cave.simulate(seed, seconds, fps, render=True,
                              render_at=frames_wanted)
    by_step = dict(zip(sorted(frames_wanted), frames))
    print(f"reached {len(order)}/{len(cave.STAGES)} stages in {seconds:.0f}s")

    fw, fh = cave.W * zoom, cave.H * zoom
    pad, text_w, sw_w = 14, 250, 210
    row_h = max(fh, 118) + pad
    W = text_w + fw + sw_w + pad * 3
    H = row_h * len(order) + 58

    sheet = Image.new("RGB", (W, H), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    f_big = ImageFont.truetype(FONT, 22)
    f_gr = ImageFont.truetype(FONT, 19)
    f_md = ImageFont.truetype(FONT, 13)
    f_sm = ImageFont.truetype(FONT, 11)

    d.text((pad, 14), "PLATO'S CAVE  —  the ascent, region by region",
           font=f_big, fill=(230, 230, 230))
    d.line([pad, 46, W - pad, 46], fill=(60, 60, 60))

    for i, (name, step) in enumerate(order):
        _, start, light, rock, glow = next(s for s in cave.STAGES if s[0] == name)
        y = 58 + i * row_h
        t = reached[name][0] if name in reached else 0.0
        unlit = tuple(v * 0.13 for v in glow)

        d.text((pad, y + 4), f"{i + 1}", font=f_md, fill=(90, 90, 90))
        d.text((pad + 22, y), name, font=f_gr, fill=tuple(glow))
        d.text((pad + 22, y + 26), cave.GLOSSES.get(name, ""), font=f_sm,
               fill=(150, 150, 150))
        d.text((pad + 22, y + 46), f"from {start:>6}   at {t:6.1f}s",
               font=f_sm, fill=(120, 120, 120))
        d.text((pad + 22, y + 62),
               f"gap {cave.gap_at(start):5.1f}px", font=f_sm, fill=(120, 120, 120))
        d.text((pad + 22, y + 78),
               f"view {(cave.W - cave.PLAYER_X) / cave.speed_at(start):.2f}s",
               font=f_sm, fill=(120, 120, 120))

        fx = pad * 2 + text_w
        sheet.paste(by_step[step].resize((fw, fh), Image.NEAREST), (fx, y))
        d.rectangle([fx - 1, y - 1, fx + fw, y + fh], outline=(60, 60, 60))

        sx = fx + fw + pad
        for n, (rgb, lbl) in enumerate(((glow, "light"), (unlit, "unlit"),
                                        (rock, "rock"))):
            swatch(d, sx, y + n * 34, 30, 24, rgb, lbl, hexof(rgb), f_sm, f_sm)
        d.text((sx, y + 106), f"dither {round(light * 255)}/255",
               font=f_sm, fill=(110, 110, 110))

    return sheet


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--seconds", type=float, default=225.0)
    ap.add_argument("--panel", default="240x135")
    ap.add_argument("--zoom", type=int, default=2)
    ap.add_argument("--out", type=Path,
                    default=here.parent / "docs" / "images")
    args = ap.parse_args()

    try:
        pw, ph = (int(v) for v in args.panel.lower().split("x"))
    except ValueError:
        raise SystemExit(f"--panel must look like 240x135, got {args.panel!r}")
    cave.configure(pw, ph)
    args.out.mkdir(parents=True, exist_ok=True)

    sheet = build(args.seed, args.fps, args.seconds, args.zoom)
    dest = args.out / "stages_reference.png"
    kb = imgutil.save_compact(sheet, dest) // 1024
    print(f"wrote {dest}  ({sheet.width}x{sheet.height}, {kb} KB)")


if __name__ == "__main__":
    main()
