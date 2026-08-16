#!/usr/bin/env python3
"""
Model the full run: ascent, the sun, and the return.

    python model_descent.py

Prints the region timings and writes two sheets to preview/:

  descent_curves.png    speed, gap and light plotted across the whole run, so
                        the two ascent levers running out at the sun -- and the
                        new ones taking over -- are visible in one picture.
  descent_regions.png   a frame from every region, ascent above, return below,
                        so the dazzle can be compared against the same region
                        on the way up.

Nothing here is committed to. It exists to see whether the numbers are sane
before they become the design.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import cave
import imgutil

FONT = "C:/Windows/Fonts/consola.ttf"


def timings(seed, fps, seconds):
    _, log = cave.simulate(seed, seconds, fps, render=False)
    return log


def curve_sheet(w=900, h=340):
    """Speed, gap and light against distance, over the whole run."""
    img = Image.new("RGB", (w, h), (14, 14, 16))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 12)
    f_hd = ImageFont.truetype(FONT, 16)
    d.text((14, 10), "difficulty levers across the full run", font=f_hd,
           fill=(230, 230, 230))

    x0, y0, pw, ph = 60, 46, w - 190, h - 96   # room for the legend on the right
    xs = np.linspace(0, cave.WIN_DIST, 700)

    series = [
        ("speed  col/s", [cave.speed_at(v) for v in xs], (255, 170, 60), 160.0),
        ("gap    px",    [cave.gap_at(v) for v in xs], (120, 210, 255), 70.0),
        ("light  0-1",   [cave.stage_for(v)[2] for v in xs], (180, 255, 190), 1.0),
    ]

    # The turn, and where each ascent lever expires.
    for dist, label, col in ((cave.REGIONS[cave.region_index(15999)][1],
                              "last ascent step", (70, 90, 110)),
                             (cave.REGIONS[len(cave.STAGES) - 1][1], "sun",
                              (110, 100, 60)),
                             (cave.DESCENT_START, "turn back", (150, 80, 80))):
        px = x0 + pw * dist / cave.WIN_DIST
        d.line([px, y0, px, y0 + ph], fill=col)
        d.text((px + 4, y0 + ph + 4), label, font=f, fill=col)

    for n, (label, vals, col, top) in enumerate(series):
        pts = [(x0 + pw * xs[i] / cave.WIN_DIST,
                y0 + ph - ph * min(1.0, vals[i] / top))
               for i in range(len(xs))]
        d.line(pts, fill=col, width=2)
        d.text((x0 + pw + 10, y0 + n * 18), label, font=f, fill=col)

    d.rectangle([x0, y0, x0 + pw, y0 + ph], outline=(60, 60, 60))
    d.text((x0, y0 + ph + 22), "0", font=f, fill=(120, 120, 120))
    d.text((x0 + pw - 40, y0 + ph + 22), f"{cave.WIN_DIST}", font=f,
           fill=(120, 120, 120))
    d.text((x0 + pw / 2 - 70, h - 18), "distance (cave columns)", font=f,
           fill=(120, 120, 120))
    return img


def region_sheet(seed, fps, seconds, zoom=2):
    log = timings(seed, fps, seconds)
    reached = {}
    for i, (name, t, dist) in enumerate(log):
        reached.setdefault(i, (name, t, dist))

    # One sample per region, taken a little way in so the palette has settled.
    marks, rows = {}, []
    steps = [int(3.0 * fps)] + [int((t + 2.0) * fps) for _, t, _ in log]
    names = [cave.REGIONS[0][0]] + [n for n, _, _ in log]
    times = [0.0] + [t for _, t, _ in log]
    for s, n, t in zip(steps, names, times):
        marks[s] = n
        rows.append((n, s, t))

    frames, _ = cave.simulate(seed, seconds, fps, render=True,
                              render_at=set(marks))
    by_step = dict(zip(sorted(marks), frames))

    n_asc = len(cave.STAGES)
    fw, fh = cave.W * zoom, cave.H * zoom
    cols = max(n_asc, len(rows) - n_asc)
    sheet = Image.new("RGB", (cols * (fw + 8) + 8, 2 * (fh + 40) + 30),
                      (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 13)
    f_gr = ImageFont.truetype(FONT, 15)
    f_hd = ImageFont.truetype(FONT, 17)

    d.text((8, 6), "ASCENT", font=f_hd, fill=(220, 220, 220))
    d.text((8, fh + 46), "THE RETURN  —  same regions, dazzled eye, closing view",
           font=f_hd, fill=(220, 180, 180))

    for i, (name, step, t) in enumerate(rows):
        band = 0 if i < n_asc else 1
        c = i if band == 0 else i - n_asc
        x = 8 + c * (fw + 8)
        y = 28 + band * (fh + 40)
        light = cave.stage_for(cave.REGIONS[i][1] + 1)[2]
        d.text((x, y), name, font=f_gr, fill=tuple(cave.REGIONS[i][4]))
        d.text((x, y + 18), f"{int(t)//60}:{int(t)%60:02d}   {light*255:.0f}/255",
               font=f, fill=(140, 140, 140))
        if step in by_step:
            sheet.paste(by_step[step].resize((fw, fh), Image.NEAREST), (x, y + 34))
    return sheet, rows


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--seconds", type=float, default=420.0)
    ap.add_argument("--panel", default="240x135")
    ap.add_argument("--out", type=Path,
                    default=here.parent / "docs" / "images")
    args = ap.parse_args()

    pw, ph = (int(v) for v in args.panel.lower().split("x"))
    cave.configure(pw, ph)
    args.out.mkdir(parents=True, exist_ok=True)

    log = timings(args.seed, args.fps, args.seconds)
    n_asc = len(cave.STAGES)

    print(f"{'region':<10}{'phase':<9}{'reached':>9}{'mm:ss':>8}"
          f"{'interval':>10}{'light':>8}{'gap':>8}{'view':>8}")
    print("-" * 70)
    prev = 0.0
    print(f"{cave.REGIONS[0][0]:<10}{'ascent':<9}{0.0:>8.1f}s{'0:00':>8}"
          f"{'--':>10}{cave.REGIONS[0][2]*255:>7.0f}"
          f"{cave.gap_at(0):>7.1f}{(cave.W-cave.PLAYER_X)/cave.speed_at(0):>7.2f}")
    for i, (name, t, dist) in enumerate(log):
        phase = "ascent" if i + 1 < n_asc else ("sun" if i + 1 == n_asc else "RETURN")
        mmss = f"{int(t)//60}:{int(t)%60:02d}"
        print(f"{name:<10}{phase:<9}{t:>8.1f}s{mmss:>8}{t-prev:>9.1f}s"
              f"{cave.stage_for(dist+1)[2]*255:>7.0f}"
              f"{cave.gap_at(dist):>7.1f}"
              f"{(cave.W-cave.PLAYER_X)/cave.speed_at(dist):>7.2f}")
        prev = t

    total = log[-1][1]
    print(f"\nreached the chains at {total:.0f}s = {int(total)//60}m "
          f"{int(total)%60:02d}s")
    print(f"ascent was {log[n_asc-2][1]:.0f}s; the return adds "
          f"{total - log[n_asc-2][1]:.0f}s")

    imgutil.save_compact(curve_sheet(), args.out / "descent_curves.png")
    sheet, _ = region_sheet(args.seed, args.fps, args.seconds)
    imgutil.save_compact(sheet, args.out / "descent_regions.png")
    print()
    for n in ("descent_curves.png", "descent_regions.png"):
        print("wrote " + imgutil.report(args.out / n))


if __name__ == "__main__":
    main()
