/**
 * @file capacityCalc.js
 * @description Carrier dimension and capacity mathematics (SRS 8.1.5)
 * SRP: All capacity-related calculations and domain constants.
 */

import { GrtmError } from "./errors.js";

// ── Domain Constants ──
export const N_LSB = 3;
export const CHANNELS = 3;
export const SNAP_UNIT = 16;
export const MAX_CARRIER_PIXELS = 16_777_216;
export const MAX_CARRIER_DIMENSION = 4096;
export const AES_OVERHEAD_BYTES = 60; // key(32) + iv(12) + authTag(16)
export const CARRIER_ID_TOTAL_BYTES = 2; // 1 byte per carrier
export const HEADER_BYTES = 5; // actualLen(4) + nameLen(1)
export const MAX_FILENAME_BYTES = 255;

/**
 * Returns available embedding bytes for a carrier of given dimensions.
 * Formula: floor(H × W × 9 / 8)
 * @param {number} height
 * @param {number} width
 * @returns {number}
 */
export function availableBytes(height, width) {
  return Math.floor((height * width * CHANNELS * N_LSB) / 8);
}

/**
 * Computes minimum target dimensions preserving Cat aspect ratio with 16px snap.
 *
 * @param {number} compressedTMLength - Byte length of compressed Treasure Map
 * @param {number} fileNameByteLength - Byte length of UTF-8 encoded filename
 * @param {number} catWidth  - Original Cat Image width in pixels
 * @param {number} catHeight - Original Cat Image height in pixels
 * @returns {{ newWidth: number, newHeight: number, totalCapacityBytes: number }}
 * @throws {GrtmError} ERR_PAYLOAD_TOO_LARGE if result exceeds MAX_CARRIER_PIXELS
 */
export function calculateTargetDimensions(
  compressedTMLength,
  fileNameByteLength,
  catWidth,
  catHeight
) {
  // Total bytes needed across both carriers (all 3 layers)
  const minTotal =
    HEADER_BYTES +
    fileNameByteLength +
    compressedTMLength +
    AES_OVERHEAD_BYTES +
    CARRIER_ID_TOTAL_BYTES;

  // Each carrier must hold at least half
  const bytesPerCarrier = Math.ceil(minTotal / 2);

  // Minimum pixels per carrier
  const minPixels = Math.ceil((bytesPerCarrier * 8) / (CHANNELS * N_LSB));

  // Scale Cat image maintaining aspect ratio
  const aspectRatio = catWidth / catHeight;

  // Derive dimensions: minPixels = W * H, W/H = aspectRatio
  // H = sqrt(minPixels / aspectRatio), W = H * aspectRatio
  let hCalc = Math.sqrt(minPixels / aspectRatio);
  let wCalc = hCalc * aspectRatio;

  // Snap up to 16px boundaries
  let newWidth = Math.ceil(wCalc / SNAP_UNIT) * SNAP_UNIT;
  let newHeight = Math.ceil(hCalc / SNAP_UNIT) * SNAP_UNIT;

  // Ensure minimum 16x16
  if (newWidth < SNAP_UNIT) newWidth = SNAP_UNIT;
  if (newHeight < SNAP_UNIT) newHeight = SNAP_UNIT;

  // Verify capacity is sufficient after snapping (snapping up should always suffice,
  // but verify to be safe)
  while (availableBytes(newHeight, newWidth) < bytesPerCarrier) {
    // Increase the smaller dimension by one snap unit
    if (newWidth <= newHeight) {
      newWidth += SNAP_UNIT;
    } else {
      newHeight += SNAP_UNIT;
    }
  }

  if (newWidth * newHeight > MAX_CARRIER_PIXELS) {
    const actualMB = (compressedTMLength / (1024 * 1024)).toFixed(1);
    throw new GrtmError(
      "ERR_PAYLOAD_TOO_LARGE",
      `Compressed payload is ${actualMB} MB but maximum supported size is approximately 36 MB. Reduce payload size.`
    );
  }

  const totalCapacityBytes = availableBytes(newHeight, newWidth);

  return { newWidth, newHeight, totalCapacityBytes };
}
