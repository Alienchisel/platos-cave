#!/usr/bin/env python3
"""
Plato as a Metal Gear Solid codec transmission, at 128x128.

    python codec.py                 # animated GIF + contact sheet
    python codec.py --frames 64

Composites four things, in this order:
  1. the head, rotating, drawn from the same point cloud as the 3D build
  2. posterisation into a codec-green ramp -- few flat levels, not a gradient
  3. CRT scanlines, drifting slowly so the panel never looks frozen
  4. the frame and UI chrome on top, which must stay un-scanlined to read

The labels are Greek on purpose. The codec's MEMORY becomes MNHMH, since
Plato's account of learning is recollection; the frequency is 428.348, his
dates. It is a joke that only works if you do not explain it on the device.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import image_treatments
import preview

N = 128

# Codec palette: black-teal through mint to a near-white highlight. Posterising
# to a handful of flat steps is what makes it read as a phosphor display rather
# than a photograph that happens to be green.
RAMP = np.array([
    (2, 10, 8), (10, 34, 27), (24, 66, 52), (46, 108, 84),
    (86, 168, 132), (140, 220, 178), (198, 245, 216), (232, 255, 238),
], np.float32)

FRAME = (120, 210, 168)
DIM = (34, 84, 66)
FONT = "C:/Windows/Fonts/consola.ttf"

HEAD_TOP, HEAD_BOT = 19, 107     # vertical band the bust occupies
# The feather existed to hide the beard being clipped mid-rotation. With a still
# portrait the framing is under our control, so keep it minimal -- any more and
# it just dims the crown of the head for no reason.
FADE = 3


def band_mask() -> np.ndarray:
    """Vertical window for the bust, feathered at both ends.

    A hard cut chops the beard off mid-rotation and reads as a bug. Feathered,
    the same clip reads as the portrait dissolving into the bezel.
    """
    m = np.zeros(N, np.float32)
    m[HEAD_TOP:HEAD_BOT] = 1.0
    ramp = np.linspace(0, 1, FADE + 2)[1:-1]
    m[HEAD_TOP:HEAD_TOP + FADE] = ramp
    m[HEAD_BOT - FADE:HEAD_BOT] = ramp[::-1]
    return m[:, None, None]


def posterise(lum: np.ndarray, levels: int = 6) -> np.ndarray:
    """Luminance 0..1 -> codec ramp, quantised to `levels` flat steps."""
    # Lift the floor off pure black without crushing the midtones. Pushing the
    # gamma hard here looks right in the abstract and destroys the face: the
    # codec portraits are high contrast but still legible across the cheek.
    lum = np.clip((lum - 0.04) / 0.96, 0, 1) ** 1.1
    q = np.clip(np.floor(lum * levels) / (levels - 1), 0, 1)
    idx = q * (len(RAMP) - 1)
    lo = np.clip(idx.astype(np.int32), 0, len(RAMP) - 2)
    f = (idx - lo)[..., None]
    return RAMP[lo] * (1 - f) + RAMP[lo + 1] * f


def scanlines(rgb: np.ndarray, phase: int) -> np.ndarray:
    """Darken alternate rows. The drift is what sells it as a live signal."""
    rows = (np.arange(N) + phase) % 3
    gain = np.where(rows == 0, 0.45, 1.0).astype(np.float32)[:, None, None]
    return rgb * gain


def chrome(img: Image.Image, frame_i: int, frames: int) -> None:
    """Frame, labels, signal bars. Drawn last so scanlines never eat the text."""
    d = ImageDraw.Draw(img)
    small = ImageFont.truetype(FONT, 10)
    tiny = ImageFont.truetype(FONT, 9)

    d.rectangle([1, 1, N - 2, N - 2], outline=FRAME)
    d.rectangle([3, 3, N - 4, N - 4], outline=DIM)
    for cx, cy, dx, dy in ((3, 3, 1, 1), (N - 4, 3, -1, 1),
                           (3, N - 4, 1, -1), (N - 4, N - 4, -1, -1)):
        d.line([cx, cy, cx + dx * 7, cy], fill=(220, 255, 238))
        d.line([cx, cy, cx, cy + dy * 7], fill=(220, 255, 238))

    # Portrait box. The codec always frames the face; without it the head
    # floats and the composition reads as an accident.
    d.rectangle([8, 18, N - 9, N - 20], outline=(30, 78, 62))
    for cx, cy, dx, dy in ((8, 18, 1, 1), (N - 9, 18, -1, 1),
                           (8, N - 20, 1, -1), (N - 9, N - 20, -1, -1)):
        d.line([cx, cy, cx + dx * 4, cy], fill=(96, 180, 142))
        d.line([cx, cy, cx, cy + dy * 4], fill=(96, 180, 142))

    d.line([6, 16, N - 7, 16], fill=DIM)
    d.line([6, N - 17, N - 7, N - 17], fill=DIM)

    label = "ΜΝΗΜΗ"
    w = d.textlength(label, font=small)
    d.text(((N - w) / 2, 4), label, font=small, fill=FRAME)

    # Signal bars: a slow sweep, so something always moves even when paused.
    lit = 2 + int((np.sin(frame_i / frames * 2 * np.pi) + 1) * 1.5)
    for b in range(5):
        h = 3 + b * 2
        col = (150, 235, 190) if b < lit else (26, 62, 50)
        d.rectangle([7 + b * 5, N - 8 - h, 10 + b * 5, N - 8], fill=col)

    d.text((N - 50, N - 14), "428.348", font=tiny, fill=(210, 250, 228))


def photo_luminance(path: Path, gamma: float) -> np.ndarray:
    """The photo, scaled into the portrait box, on an otherwise black canvas.

    Softened slightly before it is posterised: at full sharpness the marble's
    fine detail straddles the quantisation steps and breaks into confetti.
    """
    h = HEAD_BOT - HEAD_TOP
    small = image_treatments.prepare(path, gamma, crop=True, size=h)
    small = np.asarray(Image.fromarray((small * 255).astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(0.5)), np.float32) / 255.0
    canvas = np.zeros((N, N), np.float32)
    x0 = (N - h) // 2
    canvas[HEAD_TOP:HEAD_BOT, x0:x0 + h] = small
    return canvas


def cloud_luminance(data: np.ndarray, angle: int) -> np.ndarray:
    """Fallback source: the point cloud, for when the head needs to turn."""
    preview.FIT = 37
    # Flatter, brighter key than the sculptural modes use. A strong raking light
    # is what you want for marble; a codec portrait wants the whole face lit.
    preview.AMBIENT, preview.LAMBERT, preview.DEPTH_LIFT = 58, 170, 27
    return np.asarray(preview.render(data, angle, "marble"),
                      np.float32).max(axis=2) / 255.0


def sweep(rgb: np.ndarray, frame_i: int, frames: int) -> np.ndarray:
    """A slow refresh band down the screen.

    With a still portrait the scanlines alone can read as a frozen image, so
    something has to travel. Kept subtle -- this is a hum, not a wipe.
    """
    pos = (frame_i / frames) * (N + 40) - 20
    dist = np.abs(np.arange(N) - pos)
    gain = 1.0 + 0.32 * np.clip(1.0 - dist / 14.0, 0, 1)
    return rgb * gain[:, None, None]


def render(lum: np.ndarray, frame_i: int, frames: int) -> Image.Image:
    rgb = posterise(lum) * band_mask()
    rgb = sweep(scanlines(rgb, frame_i), frame_i, frames)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    chrome(img, frame_i, frames)
    return img


def main() -> None:
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, default=here.parent / "image" / "plato.png",
                    help="portrait source; the still path, and the better one")
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--rotate", action="store_true",
                    help="use the point cloud and turn the head instead")
    ap.add_argument("--header", type=Path,
                    default=here.parent / "firmware" / "plato_tqt" / "plato_points.h")
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--out", type=Path, default=here.parent / "preview")
    args = ap.parse_args()
    # Before rendering, not after: a missing directory would otherwise discard
    # the whole run at the final write.
    args.out.mkdir(parents=True, exist_ok=True)

    if args.rotate:
        data = preview.load_header(args.header)
        print(f"rotating source: {len(data)} points")
        lums = [cloud_luminance(data, round(i * 256 / args.frames))
                for i in range(args.frames)]
    else:
        print(f"still source: {args.image.name}")
        still = photo_luminance(args.image, args.gamma)
        lums = [still] * args.frames

    frames = [render(lums[i], i, args.frames) for i in range(args.frames)]

    big = [f.resize((N * args.scale, N * args.scale), Image.NEAREST) for f in frames]
    gif = args.out / "codec.gif"
    big[0].save(gif, save_all=True, append_images=big[1:], duration=60, loop=0)

    # Index off len(frames) and clamp: at n=7 the unclamped expression rounds up
    # to len(frames) whenever fewer than 8 frames were rendered.
    sheet = Image.new("RGB", (N * 2 * 4, N * 2 * 2))
    for n in range(8):
        i = min(len(frames) - 1, round(n * len(frames) / 8))
        f = frames[i].resize((N * 2, N * 2), Image.NEAREST)
        sheet.paste(f, ((n % 4) * N * 2, (n // 4) * N * 2))
    png = args.out / "codec_sheet.png"
    sheet.save(png)
    print(f"wrote {gif}\nwrote {png}")


if __name__ == "__main__":
    main()
