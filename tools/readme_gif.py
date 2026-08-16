#!/usr/bin/env python3
"""
The gameplay loop for the README.

    python readme_gif.py

Writes docs/images/gameplay.gif -- a committed asset, so size is the binding
constraint. Everything on screen scrolls, which means no two frames share
pixels and GIF's inter-frame compression has nothing to work with; the levers
are duration, scale and palette depth, in that order of effect.

The window is chosen deliberately: it straddles ΕΙΔΩΛΑ → ΥΔΩΡ, gold into cyan.
That is the largest colour jump in the run and the moment the allegory leaves
the cave, so a few seconds there show motion, the trail, the dither and the
palette shift at once. A clip inside a single region shows only the first two.
"""

import argparse
from pathlib import Path

from PIL import Image

import cave

# ΥΔΩΡ begins at 57.0 s on an uninterrupted run.
TRANSITION_S = 57.0


def build(seed, fps, before, after, zoom, colors):
    start = TRANSITION_S - before
    want = {int((start + i / fps) * fps) for i in range(int((before + after) * fps))}
    frames, _ = cave.simulate(seed, TRANSITION_S + after + 2, fps,
                              render=True, render_at=want)
    out = []
    for f in frames:
        big = f.resize((cave.W * zoom, cave.H * zoom), Image.NEAREST)
        out.append(big.convert("P", palette=Image.ADAPTIVE, colors=colors))
    return out


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--before", type=float, default=2.2, help="seconds of gold")
    ap.add_argument("--after", type=float, default=2.8, help="seconds of cyan")
    ap.add_argument("--zoom", type=int, default=2)
    ap.add_argument("--colors", type=int, default=32)
    ap.add_argument("--panel", default="240x135")
    ap.add_argument("--out", type=Path,
                    default=here.parent / "docs" / "images" / "gameplay.gif")
    args = ap.parse_args()

    pw, ph = (int(v) for v in args.panel.lower().split("x"))
    cave.configure(pw, ph)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    frames = build(args.seed, args.fps, args.before, args.after,
                   args.zoom, args.colors)
    frames[0].save(args.out, save_all=True, append_images=frames[1:],
                   duration=int(1000 / args.fps), loop=0, optimize=True)

    kb = args.out.stat().st_size / 1024
    print(f"{len(frames)} frames, {cave.W * args.zoom}x{cave.H * args.zoom}, "
          f"{args.colors} colours")
    print(f"wrote {args.out}  ({kb:.0f} KB)")
    if kb > 900:
        print("  large for a committed asset -- reduce --after or --zoom")


if __name__ == "__main__":
    main()
