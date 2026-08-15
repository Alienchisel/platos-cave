#!/usr/bin/env python3
"""
Round-trip the baked headers: parse the C back out, unpack, and check.

    python verify_bake.py

A packing bug produces bitmaps that compile perfectly and render as garbage on
the device, where debugging costs a flash cycle each time. Checking here is free.
The bust is compared byte-for-byte against a freshly dithered reference; the
labels are rendered to a contact sheet to be eyeballed.
"""

import argparse
import re
from pathlib import Path

import numpy as np
from PIL import Image

import bake_assets

ASSETS = Path(__file__).parent.parent / "firmware" / "plato" / "assets"


def parse_array(text: str, name: str) -> bytes:
    m = re.search(rf"{name}\[\]\s*=\s*\{{(.*?)\}};", text, re.S)
    if not m:
        raise SystemExit(f"array {name} not found")
    return bytes(int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{2})", m.group(1)))


def unpack(data: bytes, w: int, h: int) -> np.ndarray:
    stride = (w + 7) // 8
    if len(data) != stride * h:
        raise SystemExit(f"size mismatch: {len(data)} bytes, expected {stride * h}")
    out = np.zeros((h, w), bool)
    for y in range(h):
        for x in range(w):
            out[y, x] = bool(data[y * stride + (x >> 3)] & (0x80 >> (x & 7)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path,
                    default=Path(__file__).parent.parent / "image" / "plato.png")
    ap.add_argument("--assets", type=Path, default=ASSETS)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent.parent / "preview")
    args = ap.parse_args()

    bust_h = (args.assets / "bust.h").read_text(encoding="utf-8")
    size = int(re.search(r"#define BUST_W (\d+)", bust_h).group(1))
    got = unpack(parse_array(bust_h, "BUST_BITS"), size, size)

    # Regenerate independently and compare. Any packing or ordering error shows
    # up as a nonzero difference.
    g = bake_assets.image_treatments.prepare(args.image, 1.0, crop=True, size=size)
    tile = np.tile(bake_assets.BAYER,
                   (size // 8 + 1, size // 8 + 1))[:size, :size]
    want = g > tile

    diff = int((got != want).sum())
    print(f"bust {size}x{size}: {diff} differing pixels "
          f"({'OK' if diff == 0 else 'MISMATCH'})")
    Image.fromarray((got * 255).astype(np.uint8)).resize(
        (size * 3, size * 3), Image.NEAREST).save(args.out / "verify_bust.png")

    labels_h = (args.assets / "labels.h").read_text(encoding="utf-8")
    rows = []
    for ident, text in bake_assets.LABELS:
        w, h, _ = re.search(
            rf"\{{\s*(\d+),\s*(\d+), LBL_{ident}_BITS\}}", labels_h
        ).groups() + (None,)
        rows.append((text, unpack(parse_array(labels_h, f"LBL_{ident}_BITS"),
                                  int(w), int(h))))

    gw = int(re.search(r"#define GREEK_GLYPH_W (\d+)", labels_h).group(1))
    gh = int(re.search(r"#define GREEK_GLYPH_H (\d+)", labels_h).group(1))
    gn = int(re.search(r"#define GREEK_GLYPH_COUNT (\d+)", labels_h).group(1))
    strip = unpack(parse_array(labels_h, "GREEK_GLYPHS"), gw, gh * gn)
    alpha = np.zeros((gh, gw * gn), bool)
    for i in range(gn):
        alpha[:, i * gw:(i + 1) * gw] = strip[i * gh:(i + 1) * gh]
    rows.append(("alphabet", alpha))

    Z = 3
    width = max(m.shape[1] for _, m in rows) * Z + 8
    height = sum(m.shape[0] * Z + 6 for _, m in rows) + 6
    sheet = Image.new("RGB", (width, height), (16, 16, 16))
    y = 4
    for text, m in rows:
        img = Image.fromarray((m * 255).astype(np.uint8)).convert("RGB")
        sheet.paste(img.resize((m.shape[1] * Z, m.shape[0] * Z), Image.NEAREST),
                    (4, y))
        y += m.shape[0] * Z + 6
        print(f"  {text:<14} {m.shape[1]:>3} x {m.shape[0]}")
    sheet.save(args.out / "verify_labels.png")

    print(f"\nwrote {args.out / 'verify_bust.png'}")
    print(f"wrote {args.out / 'verify_labels.png'}")
    if diff:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
