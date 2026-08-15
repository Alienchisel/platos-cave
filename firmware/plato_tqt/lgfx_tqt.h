// LovyanGFX display config for the LILYGO T-QT Pro (ESP32-S3FN4R2, GC9107).
//
// Everything lives in this header, so nothing inside the LovyanGFX library
// needs editing -- which is the reason to prefer it over TFT_eSPI here, where
// GC9107 support means patching GC9A01_Rotation.h by hand.
//
// Pin assignments cross-checked against the LilyGo schematic, the st7789py
// board config, and the TFT_eSPI GC9107 threads. See README.md for sources.

#pragma once
#define LGFX_USE_V1
#include <LovyanGFX.hpp>

class LGFX_TQT : public lgfx::LGFX_Device {
  lgfx::Panel_GC9107 _panel;
  lgfx::Bus_SPI      _bus;
  lgfx::Light_PWM    _light;

 public:
  LGFX_TQT() {
    {
      auto cfg = _bus.config();
      cfg.spi_host    = SPI2_HOST;
      cfg.spi_mode    = 0;
      cfg.freq_write  = 40000000;   // 40 MHz is the documented safe rate;
                                    // 80000000 usually works and doubles the
                                    // flush rate. Try it once the rest is good.
      cfg.freq_read   = 8000000;
      cfg.spi_3wire   = false;
      cfg.use_lock    = true;
      cfg.dma_channel = SPI_DMA_CH_AUTO;
      cfg.pin_sclk    = 3;
      cfg.pin_mosi    = 2;
      cfg.pin_miso    = -1;
      cfg.pin_dc      = 6;
      _bus.config(cfg);
      _panel.setBus(&_bus);
    }
    {
      auto cfg = _panel.config();
      cfg.pin_cs           = 5;
      cfg.pin_rst          = 1;
      cfg.pin_busy         = -1;
      cfg.panel_width      = 128;
      cfg.panel_height     = 128;
      // The GC9107's memory is 128x160; the visible window sits at this offset.
      cfg.offset_x         = 2;
      cfg.offset_y         = 1;
      cfg.offset_rotation  = 0;
      cfg.dummy_read_pixel = 8;
      cfg.dummy_read_bits  = 1;
      cfg.readable         = false;
      cfg.invert           = true;   // if colours come out negative, flip this
      cfg.rgb_order        = false;  // false = BGR, correct for this panel
      cfg.dlen_16bit       = false;
      cfg.bus_shared       = false;
      _panel.config(cfg);
    }
    {
      auto cfg = _light.config();
      cfg.pin_bl      = 10;   // leaving this low is the classic "black screen"
      cfg.invert      = false;
      cfg.freq        = 44100;
      cfg.pwm_channel = 7;
      _light.config(cfg);
      _panel.setLight(&_light);
    }
    setPanel(&_panel);
  }
};

// Buttons, active low, both need INPUT_PULLUP.
#define PIN_BTN_LEFT   0    // shared with BOOT
#define PIN_BTN_RIGHT  47
