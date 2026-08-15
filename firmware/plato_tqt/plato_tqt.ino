// Rotating Plato head for the LILYGO T-QT Pro (ESP32-S3, 0.85" GC9107 128x128).
//
// The head is drawn as a spinning point cloud rather than a shaded surface.
// At this size -- the panel is about 15 mm across, so a pixel is ~0.12 mm --
// marble shading collapses into grey mush, while discrete high-contrast dots
// stay legible and let the eye rebuild the form from parallax as it turns.
//
// Everything is integer math. No floats, no PSRAM, ~18 KB of point data in
// flash. tools/preview.py reimplements this file's math exactly, so preview
// there first.
//
// Left button  (GPIO 0)  : cycle colour mode
// Right button (GPIO 47) : cycle spin speed, including stop

#include "lgfx_tqt.h"
#include "plato_points.h"

// ---- shared with tools/preview.py ----------------------------------------
static const int  W = 128, H = 128;
static const int  FIT = 58;          // pixel radius the longest axis maps to
static const int  CAM = 400;         // camera distance in point-units
static const int  TILT_STEPS = 8;    // fixed nod so the crown of the head shows
static const bool BACKFACE_CULL = true;
static const int8_t LX = -51, LY = 70, LZ = 93;   // marble key light, unit*127
// Culling leaves only the front hemisphere, so raw depth never uses the bottom
// half of its range. Stretch the visible band back over the full 0..255 or the
// colour ramp wastes most of its contrast on values that never occur.
static const int SHADE_LO = -32, SHADE_SPAN = 160;
// Dot size: MIN_DOT everywhere, +1 for the nearest surface. A 1 px minimum
// leaves ~46% of the head unlit, which reads as speckle rather than as dots;
// 2 px is the smallest that covers. Raising MIN_DOT to 3 goes fully solid.
static const int MIN_DOT = 2, SIZE_T1 = 215;
// Marble ramp: ambient floor, lambert weight, proximity lift. Sum <= 255.
static const int AMBIENT = 18, LAMBERT = 205, DEPTH_LIFT = 32;
// --------------------------------------------------------------------------

enum ColourMode { MODE_MARBLE, MODE_DEPTH, MODE_NORMAL, MODE_COUNT };

// Angle runs 0..255 per revolution, carried as 8.8 fixed point.
static const int SPIN_STEPS[] = {24, 48, 96, 8, 0};   // steps/sec; last = frozen

static LGFX_TQT   tft;
static LGFX_Sprite fb(&tft);

static int16_t sinTab[256], cosTab[256];

// Projected points, then bucketed by depth for a back-to-front draw.
struct Proj { int16_t x, y; uint16_t colour; uint8_t depth, tone; };
static Proj     proj[PLATO_NUM_POINTS];
static uint16_t bucketHead[256];                 // index + 1, 0 = empty
static uint16_t bucketNext[PLATO_NUM_POINTS];

static uint8_t  colourMode = MODE_MARBLE;
static uint8_t  spinIdx    = 0;
static uint16_t angleFp    = 0;

static void buildTrigTables() {
  for (int i = 0; i < 256; i++) {
    float a = i * 2.0f * PI / 256.0f;
    sinTab[i] = (int16_t)lrintf(sinf(a) * 32767.0f);
    cosTab[i] = (int16_t)lrintf(cosf(a) * 32767.0f);
  }
}

// HSV to RGB565. h, s, v are all 0..255.
static uint16_t hsv565(uint8_t h, uint8_t s, uint8_t v) {
  uint8_t region = h / 43;
  uint8_t rem    = (h - region * 43) * 6;
  uint8_t p = (v * (255 - s)) >> 8;
  uint8_t q = (v * (255 - ((s * rem) >> 8))) >> 8;
  uint8_t w = (v * (255 - ((s * (255 - rem)) >> 8))) >> 8;
  switch (region) {
    case 0:  return fb.color565(v, w, p);
    case 1:  return fb.color565(q, v, p);
    case 2:  return fb.color565(p, v, w);
    case 3:  return fb.color565(p, q, v);
    case 4:  return fb.color565(w, p, v);
    default: return fb.color565(v, p, q);
  }
}

static uint16_t shade(uint8_t tone, int nx, int ny, int nz) {
  switch (colourMode) {
    case MODE_DEPTH: {
      // The "pocket spheres" reading, but ordered so brightness rises with
      // proximity. A plain rainbow puts perceptually-bright yellow mid-range,
      // which makes the silhouette rim shout over the nose.
      uint8_t hue = (uint8_t)(((255 - tone) * 184) >> 8);   // far violet, near red
      uint8_t val = (uint8_t)(76 + ((tone * 179) >> 8));
      int sat = 255;
      if (tone > 191) sat = 255 - ((tone - 191) * 166) / 64;  // near goes white-hot
      return hsv565(hue, (uint8_t)sat, val);
    }
    case MODE_NORMAL:
      return fb.color565(nx + 127, ny + 127, nz + 127);

    default: {  // MODE_MARBLE -- lambert key light plus a depth lift
      int ndotl = (nx * LX + ny * LY + nz * LZ) / 127;
      if (ndotl < 0) ndotl = 0;
      if (ndotl > 127) ndotl = 127;
      int v = AMBIENT + (LAMBERT * ndotl) / 127 + (DEPTH_LIFT * tone) / 255;
      if (v > 255) v = 255;
      return fb.color565(v, (v * 249) >> 8, (v * 225) >> 8);
    }
  }
}

static void renderFrame(uint8_t angle) {
  const int16_t c  = cosTab[angle], s = sinTab[angle];
  const int16_t ct = cosTab[TILT_STEPS & 255], st = sinTab[TILT_STEPS & 255];
  const int32_t baseQ16 = ((int32_t)FIT << 16) / 127;

  memset(bucketHead, 0, sizeof(bucketHead));

  for (int i = 0; i < PLATO_NUM_POINTS; i++) {
    const int8_t *p = plato_points[i];

    // Normal first, so a culled point costs us almost nothing.
    int32_t nzr = (-(int32_t)p[3] * s + (int32_t)p[5] * c) >> 15;
    int32_t nyr = (int32_t)p[4];
    int32_t nz2 = (nyr * st + nzr * ct) >> 15;
    if (BACKFACE_CULL && nz2 <= 0) continue;
    int32_t nxr = ((int32_t)p[3] * c + (int32_t)p[5] * s) >> 15;
    int32_t ny2 = (nyr * ct - nzr * st) >> 15;

    int32_t xr = ((int32_t)p[0] * c + (int32_t)p[2] * s) >> 15;
    int32_t zr = (-(int32_t)p[0] * s + (int32_t)p[2] * c) >> 15;
    int32_t yr = (int32_t)p[1];
    int32_t y2 = (yr * ct - zr * st) >> 15;
    int32_t z2 = (yr * st + zr * ct) >> 15;

    int32_t perspQ8 = ((int32_t)CAM << 8) / (CAM + z2);
    int32_t sQ16    = (baseQ16 * perspQ8) >> 8;
    int32_t sx = (W / 2) + ((xr * sQ16) >> 16);
    int32_t sy = (H / 2) - ((y2 * sQ16) >> 16);
    if (sx < -3 || sy < -3 || sx >= W || sy >= H) continue;

    int32_t d = z2 + 128;                                   // draw order
    if (d < 0) d = 0;
    if (d > 255) d = 255;
    int32_t tone = (z2 - SHADE_LO) * 255 / SHADE_SPAN;       // colour ramp
    if (tone < 0) tone = 0;
    if (tone > 255) tone = 255;

    proj[i].x      = (int16_t)sx;
    proj[i].y      = (int16_t)sy;
    proj[i].depth  = (uint8_t)d;
    proj[i].tone   = (uint8_t)tone;
    proj[i].colour = shade((uint8_t)tone, nxr, ny2, nz2);

    bucketNext[i]     = bucketHead[d];
    bucketHead[d]     = i + 1;
  }

  fb.fillScreen(TFT_BLACK);

  // Painter's algorithm via an O(n) bucket sort on depth. Concavities -- the
  // eye sockets, the hollow under the beard -- need this even with culling on.
  for (int d = 0; d < 256; d++) {
    for (uint16_t n = bucketHead[d]; n; n = bucketNext[n - 1]) {
      const Proj &q = proj[n - 1];
      int size = MIN_DOT + (q.tone >= SIZE_T1);
      fb.fillRect(q.x, q.y, size, size, q.colour);
    }
  }

  fb.pushSprite(0, 0);
}

static void pollButtons() {
  static uint32_t lastPress = 0;
  static bool prevL = true, prevR = true;
  bool l = digitalRead(PIN_BTN_LEFT);
  bool r = digitalRead(PIN_BTN_RIGHT);
  uint32_t now = millis();

  if (now - lastPress > 200) {
    if (prevL && !l) { colourMode = (colourMode + 1) % MODE_COUNT; lastPress = now; }
    if (prevR && !r) {
      spinIdx = (spinIdx + 1) % (sizeof(SPIN_STEPS) / sizeof(SPIN_STEPS[0]));
      lastPress = now;
    }
  }
  prevL = l;
  prevR = r;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BTN_LEFT, INPUT_PULLUP);
  pinMode(PIN_BTN_RIGHT, INPUT_PULLUP);

  buildTrigTables();

  tft.init();
  tft.setRotation(0);
  tft.setBrightness(255);
  tft.fillScreen(TFT_BLACK);

  // 16 bpp sprite = 32 KB, comfortably inside internal RAM and DMA-friendly.
  fb.setColorDepth(16);
  if (!fb.createSprite(W, H)) {
    Serial.println("sprite alloc failed");
    while (true) delay(1000);
  }

  Serial.printf("plato: %d points, %d bytes in flash\n",
                PLATO_NUM_POINTS, PLATO_NUM_POINTS * 6);
}

void loop() {
  static uint32_t lastUs = micros();
  static uint32_t frames = 0, lastReport = 0;

  uint32_t nowUs = micros();
  uint32_t dtUs  = nowUs - lastUs;
  lastUs = nowUs;

  // 256 steps per revolution, so steps/sec * dt_us / 3906 lands in 8.8 fixed.
  angleFp += (uint16_t)((uint32_t)SPIN_STEPS[spinIdx] * dtUs / 3906);

  pollButtons();
  renderFrame((uint8_t)(angleFp >> 8));

  frames++;
  uint32_t elapsed = millis() - lastReport;
  if (elapsed > 2000) {
    Serial.printf("%.1f fps  mode=%d spin=%d\n",
                  frames * 1000.0 / elapsed, colourMode, spinIdx);
    frames = 0;
    lastReport = millis();
  }
}
