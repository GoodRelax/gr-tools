/**
 * @file capacityCalc.js
 * @description Carrier dimension and capacity mathematics (SRS §8.1.6)
 * SRP: Resolution selection algorithm, capacity math, and domain constants.
 * Imports Standard Resolution Table from standardResolutions.js (SRP, SoC).
 * Re-exports STANDARD_RESOLUTIONS for main.js access (LOD).
 */

import { GrtmError } from "./errors.js";
import { STANDARD_RESOLUTIONS } from "./standardResolutions.js";

// ── Re-export for main.js (LOD: single import point for resolution concerns) ──
export { STANDARD_RESOLUTIONS };

// ── Domain Constants ──
export const N_LSB                  = 3;
export const CHANNELS               = 3;
export const MAX_CARRIER_PIXELS     = 16_777_216;   // C-8: iOS Safari limit
export const AES_OVERHEAD_BYTES     = 60;            // key(32) + iv(12) + authTag(16)
export const CARRIER_ID_TOTAL_BYTES = 2;             // 1 byte per carrier
export const HEADER_BYTES           = 5;             // actualLen(4) + nameLen(1)
export const MAX_FILENAME_BYTES     = 255;

// ── AR Category Boundaries (§4.2.2) ──
export const AR_BOUNDARY_LOW  = (1 + 4 / 3) / 2;       // ≈ 1.1667
export const AR_BOUNDARY_HIGH = (4 / 3 + 16 / 9) / 2;  // ≈ 1.5556

/**
 * Returns available embedding bytes for a carrier of given dimensions.
 * Formula: floor(H × W × C × N_LSB / 8) = floor(H × W × 9 / 8)
 *
 * @param {number} height
 * @param {number} width
 * @returns {number}
 */
export function availableBytes(height, width) {
  return Math.floor((height * width * CHANNELS * N_LSB) / 8);
}

/**
 * Select optimal standard resolution from the Standard Resolution Table (§4.2.3).
 *
 * @param {number} compressedTMLength  - Byte length of compressed Treasure Map
 * @param {number} fileNameByteLength  - Byte length of UTF-8 encoded filename
 * @param {number} catWidth            - Original Cat Image width in pixels
 * @param {number} catHeight           - Original Cat Image height in pixels
 * @returns {{ newWidth: number, newHeight: number, capacityPerCarrier: number, label: string }}
 * @throws {GrtmError} ERR_PAYLOAD_TOO_LARGE if no table entry can hold the payload
 */
export function selectResolution(
  compressedTMLength,
  fileNameByteLength,
  catWidth,
  catHeight,
) {
  // Step 1: Compute required capacity per carrier (§4.2.3)
  const minTotal =
    HEADER_BYTES +
    fileNameByteLength +
    compressedTMLength +
    AES_OVERHEAD_BYTES +
    CARRIER_ID_TOTAL_BYTES;
  const bytesPerCarrier = Math.ceil(minTotal / 2);

  // Step 2: Determine AR category and portrait flag (§4.2.2)
  const normalizedAR =
    catWidth >= catHeight
      ? catWidth / catHeight
      : catHeight / catWidth;
  const portrait = catWidth < catHeight;

  let arCategory;
  if (normalizedAR < AR_BOUNDARY_LOW) {
    arCategory = "1:1";
  } else if (normalizedAR < AR_BOUNDARY_HIGH) {
    arCategory = "4:3";
  } else {
    arCategory = "16:9";
  }

  // Step 3: Filter candidates
  const candidates = STANDARD_RESOLUTIONS.filter((entry) => {
    // Determine entry's AR category from w/h (DRY)
    const entryAR = entry.w / entry.h;
    let entryCat;
    if (entryAR < AR_BOUNDARY_LOW) {
      entryCat = "1:1";
    } else if (entryAR < AR_BOUNDARY_HIGH) {
      entryCat = "4:3";
    } else {
      entryCat = "16:9";
    }
    return entryCat === arCategory && availableBytes(entry.h, entry.w) >= bytesPerCarrier;
  });

  if (candidates.length === 0) {
    const actualMB = (compressedTMLength / (1024 * 1024)).toFixed(1);
    throw new GrtmError(
      "ERR_PAYLOAD_TOO_LARGE",
      `Compressed payload is ${actualMB} MB but maximum supported size is approximately 36 MB. Reduce payload size.`,
    );
  }

  // Step 4: Select best entry — smallest pixel count among candidates (§4.2.3)
  const selected = candidates.reduce((best, e) =>
    e.w * e.h < best.w * best.h ? e : best,
  );

  // Step 5: Apply portrait orientation
  const newWidth  = portrait ? selected.h : selected.w;
  const newHeight = portrait ? selected.w : selected.h;

  // Step 6: Return results (guard C-8)
  if (newWidth * newHeight > MAX_CARRIER_PIXELS) {
    const actualMB = (compressedTMLength / (1024 * 1024)).toFixed(1);
    throw new GrtmError(
      "ERR_PAYLOAD_TOO_LARGE",
      `Compressed payload is ${actualMB} MB but maximum supported size is approximately 36 MB. Reduce payload size.`,
    );
  }

  const capacityPerCarrier = availableBytes(selected.h, selected.w);

  return { newWidth, newHeight, capacityPerCarrier, label: selected.label };
}

/**
 * Find the entry with smallest pixel count across ALL 17 table entries
 * that satisfies the required capacity.
 * Used by main.js for the pre-carrier-drop "Required: ≥ {label}" hint (§5.4).
 * Does NOT throw.
 *
 * @param {number} bytesPerCarrier - Required bytes per carrier
 * @returns {{ w: number, h: number, label: string } | null}
 */
export function findMinimumEntry(bytesPerCarrier) {
  let best = null;
  for (const entry of STANDARD_RESOLUTIONS) {
    if (availableBytes(entry.h, entry.w) >= bytesPerCarrier) {
      if (best === null || entry.w * entry.h < best.w * best.h) {
        best = entry;
      }
    }
  }
  return best;
}
