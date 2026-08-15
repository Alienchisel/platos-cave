# Hardware Requirements

**Project:** Plato's Cave — a one-button cave-flyer for a pocket ESP32 device.
**Status:** hardware selected, **not yet purchased**. Nothing has been built on
real hardware; everything so far is prototyped in Python at panel resolution.

---

## 1. Target device

**M5Stack M5StickS3** (`SKU K150`) — ESP32-S3 Mini IoT Dev Kit.

Buy from [RobotShop Canada](https://ca.robotshop.com/products/m5sticks3-esp32s3-mini-iot-dev)
(~CA$35) or [M5Stack direct](https://shop.m5stack.com/products/m5sticks3-esp32s3-mini-iot-dev-kit).
[DigiKey Canada](https://www.digikey.ca/en/maker/platforms/m/m5stick) carries the
line as a backup.

### Nothing else is required

The StickS3 is a finished product: enclosure, battery, speaker, buttons and
USB-C are all included. You need a USB-C cable. **Do not pad the order** — there
is no accessory this project needs.

---

## 2. Confirmed specifications

| Item | Value |
| --- | --- |
| MCU | ESP32-S3-PICO-1-N8R8 |
| Flash | 8 MB |
| PSRAM | 8 MB |
| Display | 135 × 240 IPS TFT, **native portrait** |
| Display driver | ST7789V2, 16-bit colour (65,536) |
| Audio out | ES8311 mono codec + AW8737 amplifier + speaker |
| Audio in | MEMS microphone |
| IMU | BMI270, 6-axis |
| IR | transmit and receive |
| Battery | 250 mAh LiPo, internal, USB-C charging |
| USB | native USB-OTG (not a bridge chip) |
| Expansion | Grove port (4-pin), Hat2-Bus 16-pin header |
| Dimensions | 48 × 24 × 15 mm |
| Library | **M5Unified** |

M5Unified abstracts the pin map — `M5.Display`, `M5.BtnA`, `M5.Speaker`,
`M5.Power`. Raw GPIO numbers are therefore not needed and are deliberately not
recorded here; hard-coding them would only create a second source of truth.

---

## 3. Unverified — confirm on arrival

These are flagged because I could not confirm them from primary sources. The
official M5Stack docs page for this board returned 404, so the specs above come
from a third-party hardware reference and vendor listings.

### 3.1 Button count — this one matters

**I previously told you the StickS3 has three buttons. The reference I found
lists only two: Button A (front, below the screen) and Button B (power/side).**
If Button B is a dedicated power button rather than a freely programmable one,
this project effectively has **one** general-purpose button.

Impact if that's the case:

| Function | With 2 buttons | With 1 button |
| --- | --- | --- |
| Thrust | A | A — fine, SFCave needs exactly one |
| Start / restart | A | A — fine, context-dependent |
| **Initials entry** | A cycles, B confirms | short-press cycles, long-press confirms — workable but worse |
| Menu navigation | A next, B select | long-press to select |

Mitigations if it's genuinely one button: long-press, or the **BMI270 IMU** for
tilt-to-select, or external buttons on the Grove / Hat2-Bus header. None are
blocking, but the interaction design should not assume two until confirmed.

### 3.2 Other items to check

- **Deep-sleep wake source.** Which button can wake the device from deep sleep,
  and whether M5Unified exposes it. Only RTC-capable GPIOs can serve, and idle
  standby matters more than capacity for a handheld.
- **Battery runtime.** Estimated **3–5 hours** of active play from 250 mAh,
  reasoning from an S3 at 240 MHz with WiFi off plus backlight. This is an
  order-of-magnitude estimate, not a measurement. Measure it.
- **Usable app partition.** Assumed ~3 MB under a default 8 MB scheme,
  extendable toward ~6 MB with a single-app no-OTA scheme.

---

## 4. What the hardware dictates

- **The game runs landscape, 240 × 135**, by software rotation of the native
  portrait panel. Measured against the alternatives, this roughly doubles
  forward view (~199 px of warning vs ~106 px on a 128 × 128 square) while
  leaving vertical space — and therefore difficulty — essentially unchanged.
  The entire game flow stays in this orientation; rotating between title and
  gameplay would feel broken.
- **Audio should be synthesised, not sampled.** 8-bit 11 kHz mono runs ~11 KB
  per second, so a minute of music is 660 KB. Procedural tones cost ~0 bytes and
  suit the aesthetic better. Reserve samples for one or two signature sounds.
- **Build as a launcher plus game modules from day one.** With a shared base
  (~0.5–0.9 MB estimated) and ~20–50 KB per game, a 3 MB partition holds dozens.
  A common interface — init / update / draw / score — plus one high-score store
  keyed by game is cheap now and painful to retrofit.
- **High scores go in NVS**, via the `Preferences` library. A ten-entry table is
  ~70 bytes against a ~20 KB partition. **No SD card is needed or wanted.**
- Colour is free: 65k colours, and the renderer stays a 1-bit dither with a
  per-stage palette lookup, so nothing gets slower.

---

## 5. Devices considered and rejected

Recorded so these aren't re-argued later.

| Device | Why not |
| --- | --- |
| **LILYGO T-QT Pro** | The original target. 0.85" 128 × 128 GC9107, and all early art was built for it. Rejected once it emerged that it has **no battery socket** — only solder pads — and that its case (21 × 36 × 12.5 mm) physically cannot contain a battery: 2 mm of internal clearance against a 5 mm cell. Also 2 buttons and **no sound**. Still the smallest and cheapest option if soldering and silence are acceptable. |
| **M5Stack AtomS3 + Atomic Battery Base** | Identical 0.85" 128 × 128 GC9107 panel, so **zero art rework**, and the battery base clips on with no soldering. Rejected because its one programmable button *is the screen* — playing means covering the display. |
| **M5StickC PLUS2** | Was the front-runner. **End of life**; M5Stack's own successor is the StickS3. Its piezo buzzer is also inferior to the StickS3's real speaker. |
| **Pimoroni PicoSystem** | The best pure handheld — 240 × 240, d-pad, four buttons, internal LiPo, aluminium case. Rejected as the largest departure: RP2040, different toolchain, no WiFi, and a third aspect ratio to redesign for. Reconsider only if the games become the whole point. |

### The deciding factors, in order

1. **Speaker.** The T-QT Pro is silent and cannot be made otherwise without more
   soldering than the battery would have taken.
2. **Finished object.** Internal battery, enclosed, no soldering, no polarity
   gamble, no cell taped to the outside of a case that cannot hold it.
3. **Buttons positioned so a thumb doesn't cover the screen.**

The extra flash and PSRAM over the T-QT Pro were *not* a factor — this project
comes nowhere near either board's capacity.

### What was traded away

Size (48 × 24 × 15 mm vs the T-QT Pro's 21 × 36 × 12.5 mm), roughly double the
price, and an afternoon of re-laying art from 128 × 128 to 240 × 135.

---

## 6. Repository note

This directory is still named `plato-tqt` and its top-level `README.md` still
documents the **T-QT Pro point-cloud pipeline** — a rotating 3D bust, since
abandoned. That work is superseded but not deleted; the tools still run. Treat
`README.md` as historical until it is rewritten for the current target.
