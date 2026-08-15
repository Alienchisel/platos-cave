#!/usr/bin/env python3
"""
The non-gameplay screens, at true panel resolution.

    python mockups.py

Writes title / scores / gameover / victory to docs/images at 240x135, plus a
labelled sheet at 3x for looking at. These are laid out at the size they will
actually occupy -- 135 px of height is the entire constraint and designing them
larger then shrinking would hide every crowding problem.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import cave
import imgutil

FONT = "C:/Windows/Fonts/consola.ttf"

# Placeholder table: initials and a distance. Names are the Republic's cast
# rather than AAA/BBB. The region is *derived* from the distance rather than
# typed alongside it -- hand-written pairs drift out of agreement the moment the
# thresholds are retuned, which they already had.
SCORES = [("ΜΕΓ", 33000), ("ΣΩΚ", 29140), ("ΓΛΑ", 24380), ("ΧΑΡ", 19510),
          ("ΑΔΕ", 15220), ("ΚΕΦ", 8640), ("ΘΡΑ", 3910), ("ΠΟΛ", 1180)]


def region_of(dist):
    """(label, returning, won) for a score, straight from the region table."""
    if dist >= cave.WIN_DIST:
        return "ΛΕΛΥΤΑΙ", False, True          # 'has been freed' -- a completed run
    idx = 0
    for i, r in enumerate(cave.REGIONS):
        if dist >= r[1]:
            idx = i
    return cave.REGIONS[idx][0], idx >= len(cave.STAGES), False


def fonts():
    return (ImageFont.truetype(FONT, 9), ImageFont.truetype(FONT, 10),
            ImageFont.truetype(FONT, 13), ImageFont.truetype(FONT, 21))


def title():
    bust = cave.dithered_bust(
        Path(__file__).parent.parent / "image" / "plato.png", cave.H - 12)
    return cave.title_frame(bust, blink=True)


def scores():
    """Eight rows fit 135px with a header. Nine do not."""
    img = Image.new("RGB", (cave.W, cave.H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    tiny, small, _, _ = fonts()

    hdr = "ΟΙ ΛΥΘΕΝΤΕΣ"
    d.text(((cave.W - d.textlength(hdr, font=small)) / 2, 2), hdr,
           font=small, fill=(255, 255, 255))
    d.line([10, 16, cave.W - 11, 16], fill=(80, 80, 80))

    for i, (ini, score) in enumerate(SCORES):
        y = 21 + i * 13
        region, returning, won = region_of(score)
        c = (255, 246, 214) if won else ((215, 215, 215) if i < 3 else (150,) * 3)
        d.text((10, y), f"{i + 1}", font=small, fill=(105, 105, 105))
        d.text((26, y), ini, font=small, fill=c)
        d.text((78, y), f"{score:>5}", font=small, fill=c)
        # A returning region carries the same name as an ascending one, so it
        # needs a marker: without it the table cannot tell a five-minute run
        # from a ninety-second one.
        d.text((138, y + 1), "↓" if returning else " ", font=tiny,
               fill=(180, 180, 190))
        d.text((148, y + 1), region, font=tiny,
               fill=(255, 235, 170) if won else (125, 125, 125))
    return img


def gameover():
    img = Image.new("RGB", (cave.W, cave.H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    tiny, small, med, big = fonts()

    w = d.textlength("ΔΕΣΜΩΤΗΣ", font=big)
    d.text(((cave.W - w) / 2, 26), "ΔΕΣΜΩΤΗΣ", font=big, fill=(232, 116, 36))
    g = "PRISONER"
    d.text(((cave.W - d.textlength(g, font=tiny)) / 2, 52), g, font=tiny,
           fill=(120, 90, 70))
    d.line([60, 68, cave.W - 61, 68], fill=(70, 50, 40))
    for i, (k, v) in enumerate((("REACHED", "ΑΣΤΡΑ  1:41"), ("BEST", "ΣΕΛΗΝΗ"))):
        d.text((62, 76 + i * 15), k, font=tiny, fill=(110, 110, 110))
        d.text((132, 76 + i * 15), v, font=small, fill=(200, 200, 200))
    m = "[ A ]"
    d.text(((cave.W - d.textlength(m, font=tiny)) / 2, 116), m, font=tiny,
           fill=(150, 150, 150))
    return img


def victory():
    """The Republic's first word is κατέβην -- 'I went down'. Which is both how
    the dialogue opens and, after the return, exactly what you have just done."""
    img = Image.new("RGB", (cave.W, cave.H), (6, 7, 11))
    d = ImageDraw.Draw(img)
    tiny, small, med, big = fonts()

    # Faint dither behind, at the light level of the final region: you have won,
    # and you are back in the dark.
    for y in range(0, cave.H, 3):
        for x in range((y // 3 % 2) * 6, cave.W, 12):
            d.point((x, y), fill=(26, 28, 34))

    w = d.textlength("ΚΑΤΕΒΗΝ", font=big)
    d.text(((cave.W - w) / 2, 24), "ΚΑΤΕΒΗΝ", font=big, fill=(238, 238, 245))
    g = "I WENT DOWN"
    d.text(((cave.W - d.textlength(g, font=tiny)) / 2, 50), g, font=tiny,
           fill=(120, 125, 140))
    d.line([46, 66, cave.W - 47, 66], fill=(70, 74, 88))

    d.text((48, 74), "THE CHAINS", font=tiny, fill=(110, 115, 130))
    d.text((150, 73), "5:46", font=small, fill=(235, 235, 245))
    d.text((48, 89), "SCORE", font=tiny, fill=(110, 115, 130))
    d.text((150, 88), "33000", font=small, fill=(235, 235, 245))
    m = "[ A ]"
    d.text(((cave.W - d.textlength(m, font=tiny)) / 2, 116), m, font=tiny,
           fill=(140, 145, 160))
    return img


SCREENS = (("title", title), ("scores", scores),
           ("gameover", gameover), ("victory", victory))


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="240x135")
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--out", type=Path, default=here.parent / "docs" / "images")
    args = ap.parse_args()

    pw, ph = (int(v) for v in args.panel.lower().split("x"))
    cave.configure(pw, ph)
    args.out.mkdir(parents=True, exist_ok=True)

    made = []
    for name, fn in SCREENS:
        img = fn()
        imgutil.save_compact(img, args.out / f"screen_{name}.png")
        made.append((name, img))
        print(f"  {name:<10} {img.width}x{img.height}  "
              f"{(args.out / f'screen_{name}.png').stat().st_size} bytes")

    z = args.zoom
    cw, ch = cave.W * z, cave.H * z
    sheet = Image.new("RGB", (cw * 2 + 24, (ch + 26) * 2 + 8), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 14)
    for i, (name, img) in enumerate(made):
        x, y = 8 + (i % 2) * (cw + 8), 8 + (i // 2) * (ch + 26)
        d.text((x, y), name.upper(), font=f, fill=(255, 200, 80))
        sheet.paste(img.resize((cw, ch), Image.NEAREST), (x, y + 18))
    sheet.save(args.out.parent.parent / "preview" / "screens_sheet.png")
    print(f"\nwrote {len(made)} screens -> {args.out}")


if __name__ == "__main__":
    main()
