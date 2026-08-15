# Archive — the rotating point-cloud bust

**Superseded.** This documents the project's first direction: a Plato bust
rendered as a rotating 3D point cloud on a LILYGO T-QT Pro. Both the technique
and the target device were later abandoned — see
[HARDWARE.md](HARDWARE.md) §5 for why the board was dropped, and the project
[README](../README.md) for the arc.

Kept because the tools still run and the findings are real. Nothing here is
needed to build Plato's Cave.

---

A spinning Plato bust on the 0.85" 128×128 GC9107 panel, drawn as a point cloud
rather than a shaded surface.

## Why a point cloud

The panel is about 15 mm across, so a pixel is roughly 0.12 mm and a head
filling the frame is under 12 mm tall. At that size marble shading collapses —
beard curls are 3–5 px, brow modelling lives entirely in mid-tone gradients, and
the whole thing reads as a grey lump that wobbles. Discrete high-contrast dots
stay legible, and the eye rebuilds the form from parallax as it turns.

It is also the cheaper build: ~10 KB of point data in flash instead of ~600 KB
of pre-rendered frames, no PSRAM, and the buttons can change things at runtime.

## Layout

```
tools/sample_points.py    mesh -> point cloud -> C header
tools/preview.py          renders the firmware's exact math to GIF + contact sheet
tools/make_test_mesh.py   crude stand-in head, for exercising the pipeline
firmware/plato_tqt/       Arduino sketch (LovyanGFX)
mesh/                     the downloaded scan
```

## 1. Get the mesh

[Plato, Fitzwilliam Museum, on Sketchfab](https://sketchfab.com/3d-models/plato-1df8376b55e347fb9bb4cf49375d6e5a)
— free download, **CC BY 4.0**, 380k triangles, scanned from an early Roman
marble head (object GR.23.1850). Sketchfab needs a login to download, so this
step is manual. Save it as `mesh/plato.glb`.

## 2. Sample it

```bash
python tools/sample_points.py mesh/plato.glb -n 9000 --crop-bottom 0.08 --smooth 12
```

This GLB needs **no orientation flags** — it arrives +Y up with the face toward
+Z, which is exactly what the firmware wants. (For a different mesh, preview
first and then adjust `--yaw` / `--pitch` / `--roll` in degrees, or `--z-up`.)

`--crop-bottom` cuts the ragged neck break; spinning a torn edge reads as a
glitch rather than an artefact.

`--smooth` is not optional on a raw scan. Each of the 380k faces is a sliver of
surface micro-detail, so its normal is near-random at the scale we care about,
and sampling those directly turns the lambert term into salt-and-pepper. Taubin
smoothing kills the high frequencies without collapsing the form.

### Point count and coverage

Both were measured, not guessed — see `preview/sweep.png` and `preview/fill.png`.

A bearded head needs far more points than a simple convex form. Below about 4000
the face stops reading at all. But raw count is only half of it: with a 1 px
minimum dot, 6000 points leaves **46% of the head unlit**, which the eye reads as
speckle rather than as dots — the render looks garbled even though the geometry
is correct.

| points | min dot | coverage | reads as |
| --- | --- | --- | --- |
| 6000 | 1 px | 54% | speckle |
| 6000 | 2 px | 64% | dotty, still gappy |
| **9000** | **2 px** | **73%** | **Plato, with visible dot texture** |
| 12000 | 2 px | 77% | near-solid, dots lost |

9000 costs 54 KB of flash and about 122 KB of RAM.

### Why sampling must be blue noise

Coverage is only half the story — *distribution* is the other half. The sampler
originally Poisson-disk sampled and then randomly discarded the surplus to hit
an exact point count. Random removal from an evenly-spaced set leaves clumped
voids, and at this scale those read as black blotches hovering over the face.

It looks exactly like a mesh defect, and it is not. Two hypotheses were tested
and both were wrong: inward-facing normals accounted for only 0.8% of the
surface, and although the raw GLB reports 4940 bodies (111 after
`merge_vertices` — the rest are texture-seam vertex splits, not real fragments),
decluttering them changed nothing. The tell is that the blotches **move when you
change the seed**. Geometry defects do not move.

`sample()` now bisects on the disk radius until the sampler lands near the
target and keeps every point it returns, so spacing stays even.

### Treatments

`marble` `gold` `bronze` `duotone` `iridescent` `rim` `contour` `depth` `normal`,
selected with `--mode`. See `preview/styles.png` for all of them side by side.
`gold` adds a specular term, which is what sells metal over chalk; `contour`
bands on model-space height so the rings stay fixed as the head turns; `rim` is
Fresnel-only against black.

There is a genuine tension here worth knowing about. The reference "pocket
spheres" look works because a sphere is simple enough to read from a sparse
lattice. A portrait head needs enough points to be recognisable that it stops
looking like a scatter of dots and starts looking like a stippled engraving.
9000 is the best compromise found, not a free lunch.

## 3. Preview

```bash
python tools/preview.py --mode marble
```

`preview.py` reimplements the sketch's fixed-point math step for step and reads
the generated header, so what it renders is what the panel shows.

⚠ The render constants at the top of `preview.py` and `plato_tqt.ino` are
duplicated with only a comment asking editors to keep them in sync — and they
drifted within a day. This is the mistake that
[ARCHITECTURE.md](ARCHITECTURE.md) §9 exists to prevent repeating.

## 4. Flash

Arduino IDE with [LovyanGFX](https://github.com/lovyan03/LovyanGFX). LovyanGFX
has a native `Panel_GC9107` and its config lives in `lgfx_tqt.h`, so nothing
inside the library needs editing — the reason to prefer it over TFT_eSPI here,
where GC9107 support means patching `GC9A01_Rotation.h` by hand.

| Setting | Value |
| --- | --- |
| Board | ESP32S3 Dev Module |
| USB CDC On Boot | Enabled |
| Flash Size | 4MB (32Mb) |
| PSRAM | QSPI PSRAM |

If upload fails, hold **BOOT** (GPIO 0), tap **RST**, release.

| Button | Action |
| --- | --- |
| Left (GPIO 0) | cycle colour mode |
| Right (GPIO 47) | cycle spin speed, including stop |

## Tuning

| Constant | Effect |
| --- | --- |
| `FIT` | pixel radius the model fills |
| `CAM` | camera distance; lower = stronger perspective |
| `TILT_STEPS` | fixed nod in 1/256ths of a turn |
| `BACKFACE_CULL` | off gives a transparent-shell look |
| `SHADE_LO` / `SHADE_SPAN` | stretches the visible depth band over the colour ramp |
| `MIN_DOT` / `SIZE_T1` | base dot size, and the tone at which it grows |
| `AMBIENT` / `LAMBERT` / `DEPTH_LIFT` | marble ramp weights, sum ≤ 255 |

Culling leaves only the front hemisphere, so raw depth never uses the bottom
half of its range — without the stretch, the ramp wastes most of its contrast on
values that never occur. That was the first bug worth catching here.

## Never verified

- **The sketch was never compiled** — no C++ toolchain was available.
- Pin assignments were cross-checked across three sources but never tested on
  hardware.
- Frame rate was never measured.

## Sources

- Pinout: [LilyGo T-QT repo](https://github.com/Xinyuan-LilyGO/T-QT/),
  [st7789py board config](https://russhughes.github.io/st7789py_mpy/configs/t_qt_pro.html),
  [TFT_eSPI GC9107 discussion](https://github.com/Bodmer/TFT_eSPI/discussions/2175)
