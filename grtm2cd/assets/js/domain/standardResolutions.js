/**
 * @file standardResolutions.js
 * @description Standard Resolution Table — data only (SRS §8.1.5, ADR-27)
 * SRP: Pure data module. No logic, no functions.
 * AR category is derived at runtime from w/h (DRY).
 * All entries are in landscape orientation (w >= h).
 */

/**
 * Frozen array of 17 standard resolution entries across 3 AR categories.
 * Ordered by pixel count ascending within each AR category.
 *
 * @type {ReadonlyArray<{w: number, h: number, label: string}>}
 */
export const STANDARD_RESOLUTIONS = Object.freeze([
  // ── 4:3 (AR ≈ 1.333) ──
  { w:  320, h:  240, label: "qVGA"       },
  { w:  640, h:  480, label: "VGA"        },
  { w:  800, h:  600, label: "SVGA"       },
  { w: 1024, h:  768, label: "XGA"        },
  { w: 1600, h: 1200, label: "UXGA"       },
  { w: 2048, h: 1536, label: "QXGA"       },
  { w: 4032, h: 3024, label: "iPhone 12MP"},

  // ── 16:9 (AR ≈ 1.778) ──
  { w:  640, h:  360, label: "360p"       },
  { w: 1280, h:  720, label: "720p"       },
  { w: 1920, h: 1080, label: "1080p"      },
  { w: 2560, h: 1440, label: "QHD"        },
  { w: 3840, h: 2160, label: "4K UHD"     },

  // ── 1:1 (AR = 1.000) ──
  { w:  256, h:  256, label: "256sq"      },
  { w:  512, h:  512, label: "512sq"      },
  { w: 1024, h: 1024, label: "1024sq"     },
  { w: 2048, h: 2048, label: "2048sq"     },
  { w: 4096, h: 4096, label: "4096sq"     },
]);
