#!/usr/bin/env python3
"""
Render the point cloud exactly the way the firmware will, as a GIF + contact sheet.

This parses the generated plato_points.h rather than the mesh, and reimplements
the firmware's integer math step for step, so what you see here is what the
panel shows. Use it to settle point count, orientation, zoom and colour mode
before you flash anything.

    python preview.py --mode marble --out ../preview

The render constants below are duplicated in plato_tqt.ino. If you change one,
change the other -- there is no build step tying them together.
"""

import argparse
import re
from pathlib import Path

import numpy as np
from PIL import Image

# ---- shared with plato_tqt.ino -------------------------------------------
W = H = 128           # panel size
FIT = 58              # pixel radius the model's longest axis maps to at z=0
CAM = 400             # camera distance, in point-units (127 = model half-extent)
TILT_STEPS = 8        # fixed nod, in 1/256ths of a turn, so the crown shows
BACKFACE_CULL = True
LIGHT = np.array([-0.40, 0.55, 0.73])   # marble key light, upper-front-left
# Culling leaves only the front hemisphere, so raw depth never uses the bottom
# half of its range. Stretch the visible band back over the full 0..255 or the
# colour ramp wastes most of its contrast on values that never occur.
SHADE_LO, SHADE_SPAN = -32, 160
# Dot size: MIN_DOT everywhere, +1 for the nearest surface. A 1 px minimum
# leaves ~46% of the head unlit, which reads as speckle rather than as dots;
# 2 px is the smallest that covers. Raising MIN_DOT to 3 goes fully solid.
MIN_DOT, SIZE_T1 = 2, 215
# Marble ramp: ambient floor, lambert weight, proximity lift. Must sum <= 255.
AMBIENT, LAMBERT, DEPTH_LIFT = 18, 205, 32
# --------------------------------------------------------------------------

SIN = np.rint(np.sin(np.arange(256) / 256.0 * 2 * np.pi) * 32767).astype(np.int32)
COS = np.rint(np.cos(np.arange(256) / 256.0 * 2 * np.pi) * 32767).astype(np.int32)


def load_header(path: Path) -> np.ndarray:
    """Pull the int8 point array back out of the generated C header."""
    text = path.read_text(encoding="utf-8")
    rows = re.findall(r"\{\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,"
                      r"\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\}", text)
    if not rows:
        raise SystemExit(f"no points found in {path}; run sample_points.py first")
    return np.array(rows, dtype=np.int32)


def transform(data: np.ndarray, angle: int):
    """Y-turntable then a fixed X tilt, in the same fixed-point order as the MCU."""
    x, y, z, nx, ny, nz = (data[:, i] for i in range(6))
    c, s = COS[angle & 255], SIN[angle & 255]
    ct, st = COS[TILT_STEPS & 255], SIN[TILT_STEPS & 255]

    def rot(px, py, pz):
        xr = (px * c + pz * s) >> 15
        zr = (-px * s + pz * c) >> 15
        yr2 = (py * ct - zr * st) >> 15
        zr2 = (py * st + zr * ct) >> 15
        return xr, yr2, zr2

    return rot(x, y, z), rot(nx, ny, nz)


def project(xr, yr, zr):
    base_q16 = (FIT << 16) // 127
    persp_q8 = (CAM << 8) // (CAM + zr)          # 256 at the model's centre
    s_q16 = (base_q16 * persp_q8) >> 8
    sx = (W // 2) + ((xr * s_q16) >> 16)
    sy = (H // 2) - ((yr * s_q16) >> 16)
    return sx, sy


MODES = ["marble", "gold", "bronze", "duotone", "iridescent", "rim",
         "contour", "depth", "normal"]

# Half-vector for the specular term, = normalize(LIGHT + view), view = +Z.
HALF = (LIGHT + np.array([0, 0, 1.0]))
HALF /= np.linalg.norm(HALF)


def _hsv(hue, sat, val):
    """Vectorised HSV to RGB; all inputs 0..1 arrays. Returns Nx3 uint8."""
    i = np.floor(hue * 6).astype(np.int32) % 6
    f = hue * 6 - np.floor(hue * 6)
    p, q, w = val * (1 - sat), val * (1 - sat * f), val * (1 - sat * (1 - f))
    r = np.choose(i, [val, q, p, p, w, val])
    g = np.choose(i, [w, val, val, q, p, p])
    b = np.choose(i, [p, p, w, val, val, q])
    return np.clip(np.stack([r, g, b], axis=1) * 255, 0, 255).astype(np.uint8)


def _ramp(t, shadow, light):
    """Interpolate a colour ramp; t is 0..1 per point."""
    shadow, light = np.array(shadow, np.float32), np.array(light, np.float32)
    return shadow + (light - shadow) * t[:, None]


def shade(mode, depth, nrot, orig):
    """depth: 0..255, 255 = nearest. Returns Nx3 uint8. Mirrors the .ino."""
    nx, ny, nz = (nrot[i].astype(np.float32) / 127.0 for i in range(3))
    lam = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    spec = np.clip(nx * HALF[0] + ny * HALF[1] + nz * HALF[2], 0, 1) ** 24
    d = depth.astype(np.float32) / 255.0

    if mode == "gold":
        # Polished metal: warm ramp plus a tight specular. The highlight is what
        # sells metal over chalk -- lambert alone always reads matte.
        rgb = _ramp(lam, (28, 14, 4), (255, 186, 74))
        return np.clip(rgb + spec[:, None] * np.array([255, 240, 200]),
                       0, 255).astype(np.uint8)

    if mode == "bronze":
        # Oxidised bronze: cold verdigris in shadow, warm metal where lit.
        rgb = _ramp(lam ** 0.8, (8, 34, 38), (196, 214, 168))
        return np.clip(rgb + spec[:, None] * np.array([255, 235, 180]) * 0.7,
                       0, 255).astype(np.uint8)

    if mode == "duotone":
        # Painterly: cool shadow, warm light. Costs nothing over greyscale and
        # reads far better at this size, because hue carries the form too.
        return np.clip(_ramp(lam, (18, 26, 88), (255, 226, 188)),
                       0, 255).astype(np.uint8)

    if mode == "iridescent":
        # Thin-film chrome: hue driven by viewing angle, the way real
        # interference films behave. Using atan2 of the normal instead gives a
        # hard seam where the angle wraps -- this is smooth and seamless.
        view = np.clip(nz, 0, 1)
        return _hsv((0.62 - 0.62 * view) % 1.0,
                    0.30 + 0.60 * (1 - view),
                    0.30 + 0.70 * lam)

    if mode == "rim":
        # Fresnel edge only: the head emerges from and dissolves into black.
        # The exponent has to be steep -- at 2.5 the interior sat at mid-grey
        # and the whole point of the treatment was lost.
        fres = (1.0 - np.clip(nz, 0, 1)) ** 5.0
        glow = np.clip(0.02 + 2.2 * fres, 0, 1)
        return np.clip(_ramp(glow, (0, 0, 0), (198, 232, 255)),
                       0, 255).astype(np.uint8)

    if mode == "contour":
        # Topographic bands on model-space height, so the rings stay put while
        # the head turns under them.
        y = orig[:, 1].astype(np.float32)
        band = np.abs(((y + 128) % 16) - 8) / 8.0        # 0 on a line, 1 between
        on = np.clip(1.0 - band * 2.2, 0, 1)
        return np.clip(_ramp(on * (0.3 + 0.7 * lam), (2, 4, 10), (120, 255, 210)),
                       0, 255).astype(np.uint8)

    if mode == "marble":
        v = np.clip(AMBIENT + LAMBERT * lam + DEPTH_LIFT * d, 0, 255)
        return np.stack([v, v * 0.97, v * 0.88], axis=1).astype(np.uint8)
    if mode == "normal":
        return np.stack([(nx + 1) * 127, (ny + 1) * 127, (nz + 1) * 127],
                        axis=1).astype(np.uint8)
    # depth-heat: the "pocket spheres" look, but ordered so brightness rises
    # with proximity. A plain rainbow puts perceptually-bright yellow in the
    # middle of the range, which makes the silhouette rim shout over the nose.
    return _hsv((1.0 - d) * 0.72,                            # far violet, near red
                1.0 - np.clip((d - 0.75) / 0.25, 0, 1) * 0.65,   # near goes white
                0.30 + 0.70 * d)


def render(data: np.ndarray, angle: int, mode: str) -> Image.Image:
    (xr, yr, zr), nrot = transform(data, angle)

    keep = nrot[2] > 0 if BACKFACE_CULL else np.ones(len(xr), bool)
    xr, yr, zr = xr[keep], yr[keep], zr[keep]
    nrot = [n[keep] for n in nrot]

    sx, sy = project(xr, yr, zr)
    depth = np.clip(zr + 128, 0, 255)                                  # draw order
    tone = np.clip((zr - SHADE_LO) * 255 // SHADE_SPAN, 0, 255)        # colour ramp
    rgb = shade(mode, tone, nrot, data[keep])

    # Painter's algorithm. A bucket sort by depth is O(n) and keeps concavities
    # -- eye sockets, the hollow behind the beard -- from punching through.
    order = np.argsort(depth, kind="stable")

    canvas = np.zeros((H, W, 3), np.uint8)
    for idx in order:
        size = MIN_DOT + (tone[idx] >= SIZE_T1)
        x0, y0 = int(sx[idx]), int(sy[idx])
        x1, y1 = max(0, x0), max(0, y0)
        x2, y2 = min(W, x0 + size), min(H, y0 + size)
        if x1 < x2 and y1 < y2:
            canvas[y1:y2, x1:x2] = rgb[idx]
    return Image.fromarray(canvas)


def main() -> None:
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--header", type=Path,
                    default=here.parent / "firmware" / "plato_tqt" / "plato_points.h")
    ap.add_argument("--mode", default="marble", choices=MODES)
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--scale", type=int, default=4, help="upscale for viewing only")
    ap.add_argument("--out", type=Path, default=here.parent / "preview")
    args = ap.parse_args()

    data = load_header(args.header)
    print(f"{len(data)} points, mode={args.mode}")
    args.out.mkdir(parents=True, exist_ok=True)

    frames = [render(data, round(i * 256 / args.frames), args.mode)
              for i in range(args.frames)]

    big = [f.resize((W * args.scale, H * args.scale), Image.NEAREST) for f in frames]
    gif = args.out / f"turntable_{args.mode}.gif"
    big[0].save(gif, save_all=True, append_images=big[1:], duration=50, loop=0)

    # Contact sheet: 8 evenly spaced angles, for judging the silhouette.
    sheet = Image.new("RGB", (W * 4 * 2, H * 2 * 2))
    for n in range(8):
        f = frames[round(n * args.frames / 8)].resize((W * 2, H * 2), Image.NEAREST)
        sheet.paste(f, ((n % 4) * W * 2, (n // 4) * H * 2))
    png = args.out / f"contact_{args.mode}.png"
    sheet.save(png)

    print(f"wrote {gif}\nwrote {png}")


if __name__ == "__main__":
    main()
