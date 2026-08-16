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


def progress_pips(d, cx, y, reached, pip=7, gap=3, turn_gap=7):
    """One pip per region, in that region's own light colour, filled up to
    `reached`. The gap marks the sun -- ascent left of it, return right.

    A region name on its own says nothing about position, and with the return in
    place the same name occurs twice: ΑΣΤΡΑ is both region 5 and region 9. This
    makes the sequence legible without reading anything, and doubles as the
    palette ramp.
    """
    n_asc = len(cave.STAGES)
    total = len(cave.REGIONS)
    width = total * (pip + gap) - gap + turn_gap
    x0 = cx - width / 2
    x = x0
    for i, region in enumerate(cave.REGIONS):
        if i == n_asc:
            x += turn_gap
        glow = tuple(region[4])
        if i <= reached:
            d.rectangle([x, y, x + pip - 1, y + pip - 1], fill=glow)
        else:
            d.rectangle([x, y, x + pip - 1, y + pip - 1],
                        fill=tuple(int(v * 0.16) for v in glow),
                        outline=tuple(int(v * 0.34) for v in glow))
        x += pip + gap
    # Mark the turn with a divider standing in the gap. A tick underneath was
    # two pixels and simply did not register at this size.
    turn_x = x0 + n_asc * (pip + gap) + turn_gap / 2 - 1
    d.line([turn_x, y - 2, turn_x, y + pip + 1], fill=(255, 246, 214))


def region_line(dist):
    """'↓ΑΣΤΡΑ  9/13' -- name, direction and position in one string."""
    name, returning, won = region_of(dist)
    idx = 0
    for i, r in enumerate(cave.REGIONS):
        if dist >= r[1]:
            idx = i
    if won:
        return name, len(cave.REGIONS) - 1
    return ("↓" if returning else "") + name, idx


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


def gameover(died_at=8100, best=20400):
    """Two deaths, not one. Climbing you are still a prisoner; returning, your
    eyes are full of darkness (Republic 516e) and the word is ΤΥΦΛΟΣ."""
    img = Image.new("RGB", (cave.W, cave.H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    tiny, small, med, big = fonts()
    cx = cave.W / 2

    word = cave.death_word(died_at)
    gloss = "BLIND" if word == cave.DEATH_RETURN else "PRISONER"
    hue = (196, 202, 226) if word == cave.DEATH_RETURN else (232, 116, 36)
    dim = (96, 100, 118) if word == cave.DEATH_RETURN else (120, 90, 70)

    w = d.textlength(word, font=big)
    d.text((cx - w / 2, 12), word, font=big, fill=hue)
    d.text((cx - d.textlength(gloss, font=tiny) / 2, 38), gloss, font=tiny,
           fill=dim)

    label, idx = region_line(died_at)
    progress_pips(d, cx, 58, idx)

    line = f"{label}   {idx + 1}/{len(cave.REGIONS)}"
    d.text((cx - d.textlength(line, font=small) / 2, 76), line, font=small,
           fill=(225, 225, 225))
    d.text((cx - d.textlength("1:41", font=small) / 2, 90), "1:41", font=small,
           fill=(140, 140, 140))

    b_label, b_idx = region_line(best)
    b = f"BEST  {b_label}  {b_idx + 1}/{len(cave.REGIONS)}"
    d.text((cx - d.textlength(b, font=tiny) / 2, 106), b, font=tiny,
           fill=(120, 120, 120))
    m = "[ A ]"
    d.text((cx - d.textlength(m, font=tiny) / 2, 121), m, font=tiny,
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

    cx = cave.W / 2
    w = d.textlength("ΚΑΤΕΒΗΝ", font=big)
    d.text((cx - w / 2, 12), "ΚΑΤΕΒΗΝ", font=big, fill=(238, 238, 245))
    g = "I WENT DOWN"
    d.text((cx - d.textlength(g, font=tiny) / 2, 38), g, font=tiny,
           fill=(120, 125, 140))

    # Every pip lit: the whole ascent and the whole return.
    progress_pips(d, cx, 58, len(cave.REGIONS) - 1)

    line = "ΛΕΛΥΤΑΙ   13/13"
    d.text((cx - d.textlength(line, font=small) / 2, 76), line, font=small,
           fill=(255, 246, 214))
    d.text((cx - d.textlength("5:46", font=small) / 2, 90), "5:46", font=small,
           fill=(150, 155, 170))
    s = "SCORE  33000"
    d.text((cx - d.textlength(s, font=tiny) / 2, 106), s, font=tiny,
           fill=(120, 125, 140))
    m = "[ A ]"
    d.text((cx - d.textlength(m, font=tiny) / 2, 121), m, font=tiny,
           fill=(140, 145, 160))
    return img


SCREENS = (("title", title), ("scores", scores),
           ("gameover", gameover),
           ("gameover_return", lambda: gameover(died_at=26800, best=31000)),
           ("victory", victory))


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
    rows = (len(made) + 1) // 2
    sheet = Image.new("RGB", (cw * 2 + 24, (ch + 26) * rows + 8), (16, 16, 18))
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
