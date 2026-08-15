#!/usr/bin/env python3
"""
Cut the head out of a museum photograph and put it on black.

    python isolate_head.py image/plato_commons_pd.jpg -o image/plato_pd_head.png

The treatment pipeline assumes a subject on pure black -- that is what makes the
dithers and duotones read. A gallery photograph has a wall behind it, and here
the wall is mottled granite close in tone to the marble, so a plain luminance
threshold cuts the background in and the sculpture out in equal measure.

Instead: threshold, keep the largest connected component, fill its holes, then
close and feather. The sculpture is one big bright blob; the granite is speckled
and fragments into many small ones, which is exactly what largest-component
selection exploits.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


def isolate(img: Image.Image, thresh: int, close_px: int,
            feather: float) -> Image.Image:
    grey = np.asarray(img.convert("L").filter(ImageFilter.GaussianBlur(3)),
                      np.float32)

    mask = grey > thresh
    labels, n = ndimage.label(mask)
    if n == 0:
        raise SystemExit("nothing above threshold -- lower --thresh")
    # Largest component by area, ignoring label 0 (background).
    sizes = ndimage.sum(mask, labels, range(1, n + 1))
    mask = labels == (int(np.argmax(sizes)) + 1)
    print(f"  {n} components, largest covers {mask.mean() * 100:.1f}% of frame")

    mask = ndimage.binary_fill_holes(mask)
    if close_px:
        mask = ndimage.binary_closing(mask, np.ones((close_px, close_px)))
        mask = ndimage.binary_opening(mask, np.ones((close_px, close_px)))

    alpha = Image.fromarray((mask * 255).astype(np.uint8))
    if feather:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))

    out = Image.new("RGB", img.size, (0, 0, 0))
    out.paste(img.convert("RGB"), (0, 0), alpha)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--crop", type=int, nargs=4, metavar=("L", "T", "R", "B"),
                    default=[120, 70, 1300, 1790],
                    help="crop box before masking; must exclude the herm's "
                         "shoulders, which are the same marble as the head")
    ap.add_argument("--thresh", type=int, default=118)
    ap.add_argument("--close", type=int, default=9)
    ap.add_argument("--feather", type=float, default=1.5)
    args = ap.parse_args()

    img = Image.open(args.image).crop(tuple(args.crop))
    print(f"cropped to {img.size}")
    out = isolate(img, args.thresh, args.close, args.feather)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
