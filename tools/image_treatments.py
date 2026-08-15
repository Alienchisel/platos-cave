#!/usr/bin/env python3
"""
Render a source image as a set of 128x128 treatments for the T-QT panel.

    python image_treatments.py ../image/plato.png

Writes one PNG per treatment plus a labelled contact sheet. Everything is
computed at panel resolution, so what you see is what the display gets.

At 128x128 a detailed photograph has to be simplified before it is stylised --
dithering a full-detail downscale just produces noise. So every treatment runs
on a contrast-normalised, gently sharpened 128x128 base.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

N = 128

# 8x8 Bayer matrix, normalised to 0..1. Ordered dithering holds a visible
# structure that random dithering does not, which reads as deliberate texture
# rather than noise at this size.
BAYER = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21],
], np.float32) / 64.0


def subject_mask(g: np.ndarray) -> np.ndarray:
    """Where the bust is, so the background stays black.

    Without this the tinted treatments paint their shadow colour across the
    whole frame and you get a coloured rectangle instead of a head floating in
    the dark -- which is most of the appeal on a small bright panel.
    """
    m = Image.fromarray(((g > 0.06) * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(5))
    return np.asarray(m.filter(ImageFilter.MaxFilter(3)), np.float32) / 255.0


def prepare(path: Path, gamma: float, crop: bool, size: int = N) -> np.ndarray:
    """Load, trim to content, square-pad, downscale. Returns size*size float 0..1."""
    img = Image.open(path).convert("L")
    if crop:
        # getbbox() bounds the NON-ZERO pixels, and the subject sits on black,
        # so threshold and use it directly. Inverting first (as this did
        # originally) bounds everything that is not pure white -- i.e. the whole
        # frame -- and silently does nothing.
        bbox = img.point(lambda v: 255 if v > 12 else 0).getbbox()
        if bbox:
            img = img.crop(bbox)
    w, h = img.size
    side = max(w, h)
    square = Image.new("L", (side, side), 0)
    square.paste(img, ((side - w) // 2, (side - h) // 2))

    # Sharpen before the downscale, not after: at 10:1 reduction the detail is
    # gone by the time you would otherwise reach for it.
    square = square.filter(ImageFilter.UnsharpMask(radius=side / 200, percent=90))
    small = ImageOps.autocontrast(square.resize((size, size), Image.LANCZOS),
                                  cutoff=1)
    return (np.asarray(small, np.float32) / 255.0) ** gamma


def _ramp(t, shadow, light):
    shadow, light = np.array(shadow, np.float32), np.array(light, np.float32)
    return np.clip(shadow + (light - shadow) * t[..., None], 0, 255).astype(np.uint8)


def _mono(bits):
    return np.repeat((bits * 255).astype(np.uint8)[..., None], 3, axis=2)


def t_bayer(g):
    """Ordered dither to pure black and white."""
    tile = np.tile(BAYER, (N // 8 + 1, N // 8 + 1))[:N, :N]
    return _mono(g > tile)


def t_floyd(g):
    """Floyd-Steinberg error diffusion: organic grain, no visible lattice."""
    w = g.copy()
    for y in range(N):
        for x in range(N):
            old = w[y, x]
            new = 1.0 if old > 0.5 else 0.0
            w[y, x] = new
            err = old - new
            if x + 1 < N:
                w[y, x + 1] += err * 7 / 16
            if y + 1 < N:
                if x:
                    w[y + 1, x - 1] += err * 3 / 16
                w[y + 1, x] += err * 5 / 16
                if x + 1 < N:
                    w[y + 1, x + 1] += err * 1 / 16
    return _mono(w > 0.5)


def t_halftone(g, cell=4):
    """Newsprint dots: one variable-radius disc per cell.

    The radius has to top out near half the cell. Any larger and neighbouring
    dots merge, the highlights flood to solid white and the face disappears --
    which is exactly what happened at 0.75. The exponent above 1 also pulls the
    midtones down, since a bright photo otherwise saturates most cells.
    """
    out = Image.new("RGB", (N * 4, N * 4), (0, 0, 0))
    d = ImageDraw.Draw(out)
    for cy in range(0, N, cell):
        for cx in range(0, N, cell):
            v = float(g[cy:cy + cell, cx:cx + cell].mean())
            r = (v ** 1.35) * cell * 0.56 * 4
            if r > 0.6:
                x, y = (cx + cell / 2) * 4, (cy + cell / 2) * 4
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 244, 224))
    return np.asarray(out.resize((N, N), Image.LANCZOS))


def t_engrave(g):
    """Line engraving: horizontal rules whose thickness tracks luminance."""
    out = np.zeros((N, N), np.float32)
    period = 3
    for y in range(N):
        phase = y % period
        thickness = g[y] * period            # 0..period
        out[y] = (phase < thickness).astype(np.float32)
    return _ramp(out * (0.35 + 0.65 * g), (4, 4, 8), (236, 232, 220))


def t_edges(g):
    """Difference of Gaussians: the bust as line art out of the void."""
    a = np.asarray(Image.fromarray((g * 255).astype(np.uint8))
                   .filter(ImageFilter.GaussianBlur(0.8)), np.float32)
    b = np.asarray(Image.fromarray((g * 255).astype(np.uint8))
                   .filter(ImageFilter.GaussianBlur(2.2)), np.float32)
    e = np.clip((a - b) / 18.0, 0, 1) ** 0.8
    return _ramp(e, (0, 0, 0), (208, 232, 255))


def t_posterize(g, levels=4):
    q = np.floor(g * levels) / (levels - 1)
    return _ramp(np.clip(q, 0, 1), (16, 16, 20), (245, 243, 236))


def t_gold(g):
    return _ramp(g ** 0.9, (26, 12, 3), (255, 202, 92))


def t_duotone(g):
    return _ramp(g, (16, 24, 84), (255, 228, 190))


def t_verdigris(g):
    return _ramp(g ** 0.85, (6, 28, 32), (206, 226, 176))


def t_heat(g):
    """Luminance through a monotonic heat ramp."""
    stops = np.array([[8, 4, 40], [90, 18, 120], [220, 60, 60],
                      [255, 170, 40], [255, 250, 220]], np.float32)
    idx = np.clip(g * (len(stops) - 1), 0, len(stops) - 1.001)
    lo = idx.astype(np.int32)
    f = (idx - lo)[..., None]
    return np.clip(stops[lo] * (1 - f) + stops[lo + 1] * f, 0, 255).astype(np.uint8)


def t_contour(g, bands=7):
    """Topographic banding on luminance -- the head as a level set.

    Needs the blur: banding amplifies high-frequency detail into confetti,
    because every tiny luminance wiggle crosses a band boundary.
    """
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8))
                   .filter(ImageFilter.GaussianBlur(2.6)), np.float32) / 255.0
    v = g * bands
    edge = np.abs(v - np.round(v))
    line = np.clip(1.0 - edge * 7.0, 0, 1)
    return _ramp(line * (0.3 + 0.7 * g), (2, 6, 10), (130, 255, 214))


def t_crt(g):
    """Phosphor scanlines, because the panel is already a tiny screen."""
    scan = np.ones((N, 1), np.float32)
    scan[::2] = 0.45
    return _ramp(np.clip(g * scan * 1.15, 0, 1), (2, 6, 4), (170, 255, 200))


TREATMENTS = {
    "bayer": t_bayer, "floyd": t_floyd, "halftone": t_halftone,
    "engrave": t_engrave, "edges": t_edges, "posterize": t_posterize,
    "gold": t_gold, "duotone": t_duotone, "verdigris": t_verdigris,
    "heat": t_heat, "contour": t_contour, "crt": t_crt,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--out", type=Path,
                    default=Path(__file__).parent.parent / "preview" / "treatments")
    ap.add_argument("--gamma", type=float, default=1.0,
                    help="<1 lifts shadows, >1 deepens them")
    ap.add_argument("--no-crop", action="store_true")
    ap.add_argument("--zoom", type=int, default=3, help="contact sheet scale")
    args = ap.parse_args()

    if not args.image.exists():
        sys.exit(f"error: {args.image} not found")

    g = prepare(args.image, args.gamma, not args.no_crop)
    mask = subject_mask(g)[..., None]
    args.out.mkdir(parents=True, exist_ok=True)

    Z, cols = args.zoom, 4
    rows = (len(TREATMENTS) + cols - 1) // cols
    sheet = Image.new("RGB", (N * Z * cols, (N * Z + 18) * rows), (16, 16, 16))
    d = ImageDraw.Draw(sheet)

    for i, (name, fn) in enumerate(TREATMENTS.items()):
        img = Image.fromarray((fn(g) * mask).astype(np.uint8))
        img.save(args.out / f"{name}.png")
        x, y = (i % cols) * N * Z, (i // cols) * (N * Z + 18)
        d.text((x + 4, y + 3), name, fill=(255, 200, 80))
        sheet.paste(img.resize((N * Z, N * Z), Image.NEAREST), (x, y + 18))
        print(name)

    sheet.save(args.out.parent / "treatments.png")
    print(f"\nwrote {len(TREATMENTS)} treatments -> {args.out}")
    print(f"wrote {args.out.parent / 'treatments.png'}")


if __name__ == "__main__":
    main()
