# Plato's Cave

A one-button cave-flyer for a pocket ESP32 handheld. You are a point of light
ascending out of Plato's cave; gravity pulls you down, the button thrusts you
up, rock kills you, distance is score.

The allegory isn't decoration. Plato's ascent in *Republic* 514a–517a is an
ordered sequence of light sources — shadows, fire, carried images, reflections in
water, stars, moon, sun — and that sequence supplies the game's entire
progression structure *and* its palette. **The screen brightens as you climb.**
Your progress isn't a number in the corner; it's how much you can see.

And reaching the sun isn't the end. Plato's freed prisoner is obliged to go back
down, and his eyes no longer work in the dark. **You win by returning to the
chains** — through the same seven regions, each dimmer than it was on the way up,
with the view closing in. Roughly 5½ minutes of unbroken flight.

![the seven stages](preview/stage_palette.png)

---

## Status

**Nothing has been built.** No firmware is written and the hardware has not been
bought. Everything so far is prototyped in Python at exact panel resolution, so
the visuals are settled and the feel is entirely unknown.

| | |
| --- | --- |
| Target | M5Stack **M5StickS3**, 240 × 135 landscape — *not yet purchased* |
| Visuals | prototyped and rendered |
| Pacing | retuned, frame-rate independent, verified 30–144 fps |
| Physics feel | **never tested** — three constants awaiting a thumb |
| Firmware | not started |

---

## Documentation

| Doc | Contents |
| --- | --- |
| [docs/HARDWARE.md](docs/HARDWARE.md) | What to buy and why. Confirmed specs, unverified items, and a record of the four devices considered and rejected. |
| [docs/GAME_DESIGN.md](docs/GAME_DESIGN.md) | Rules, the seven stages, palette, pacing curve, open decisions. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Launcher-plus-modules structure, the input abstraction, build order. |
| [docs/ARCHIVE_POINTCLOUD.md](docs/ARCHIVE_POINTCLOUD.md) | The abandoned first direction, kept for its findings. |

**Read HARDWARE.md first if you're picking this up cold** — one open question
there (how many programmable buttons the StickS3 actually has) cascades into the
input design and the high-score entry screen.

---

## Tools

All prototypes. Only the asset bakers — *not yet written* — will feed the
firmware.

| | |
| --- | --- |
| `tools/cave.py` | The game. Simulates a run and renders it. **The reference implementation**: the C++ must match its math. |
| `tools/stage_sheet.py` | Reference sheet of the seven ascent regions with palettes, hex values and per-stage difficulty numbers. |
| `tools/model_descent.py` | The full run including the return: difficulty curves across all three levers, and every region shown ascending and returning. |
| `tools/image_treatments.py` | Renders a source image twelve ways at panel resolution — dithers, halftone, engraving, duotones. |
| `tools/preview.py` | 3D point-cloud renderer. Archived direction. |
| `tools/sample_points.py` | Mesh → point cloud → C header. Archived direction. |
| `tools/isolate_head.py` | Cuts a subject off a photographed background onto black, by largest connected component. Works when the subject is clearly brighter than the background; not when their tonal ranges overlap. |
| `tools/codec.py` | Metal Gear codec mockup. Explored and set aside. |

### Running it

```bash
python tools/cave.py --seconds 225 --fps 24 --scale 2
```

Writes a gameplay GIF, a title screen, and a one-frame-per-stage contact sheet to
`preview/`, and prints the stage timings.

```bash
python tools/image_treatments.py image/plato.png
```

Twelve treatments at 128 × 128 to `preview/treatments/`.

Requires `numpy`, `pillow`, and — for the archived 3D tools — `trimesh`,
`scipy`, `networkx`.

---

## How this got here

Worth recording, because the path explains the leftovers.

It began as a **rotating 3D Plato bust** for a LILYGO T-QT Pro, drawn as a point
cloud because marble shading collapses at 128 × 128. That worked — see
[the archive](docs/ARCHIVE_POINTCLOUD.md) — and produced some genuinely useful
findings about blue-noise sampling and dot coverage.

It then became a **Metal Gear codec display**, which was fun and is where the
Greek UI came from, before the rotating head was dropped in favour of treating a
still photograph.

It is now a **game**, which is the first version that gives the device a reason
to be picked up rather than glanced at.

The target board changed too, once it emerged that the T-QT Pro has no battery
socket, a case that physically cannot contain a battery, and no speaker.

---

## Credits

- **3D scan** (`mesh/plato.glb`), used by the archived point-cloud tools:
  *Plato*, Fitzwilliam Museum, object GR.23.1850, via
  [Sketchfab](https://sketchfab.com/3d-models/plato-1df8376b55e347fb9bb4cf49375d6e5a),
  CC BY 4.0.
- **The sculpture** throughout is the Vatican Museums' herm of Plato, Museo
  Pio-Clementino, Sala delle Muse, Inv. 305 — a Roman copy after a Greek
  original of the late 4th century BC. Its base is inscribed ΖΗΝΩΝ.

---

## Repository

<https://github.com/Alienchisel/platos-cave> — private.

`image/`, `mesh/` and `preview/` are excluded: ~26 MB of source images and
regenerable output, against ~450 KB of actual source.

`firmware/plato_tqt/` keeps its name because it holds the archived T-QT sketch,
named for the board it targeted. It was never compiled.
