/**
 * @file imageAdapter.js
 * @description Wraps Canvas API / File API (SRS 8.3.2)
 * SRP: Image loading, resizing, and PNG blob creation.
 */

import { GrtmError } from "../domain/errors.js";

// Accepted MIME types per C-9
const ACCEPTED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/bmp",
  "image/gif",
]);

/**
 * Create an ImageAdapter.
 * @returns {{ loadPixels, resizeKeepAspect, resizeStretch, toBlob, downscaleToLimit }}
 */
export function createImageAdapter() {
  /**
   * Helper: Load an image from raw bytes and return an HTMLImageElement.
   * @param {Uint8Array} fileBytes
   * @returns {Promise<HTMLImageElement>}
   */
  function loadImage(fileBytes) {
    return new Promise((resolve, reject) => {
      const blob = new Blob([fileBytes]);
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = () => {
        URL.revokeObjectURL(url);
        resolve(img);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(
          new GrtmError(
            "ERR_UNSUPPORTED_FORMAT",
            "Unsupported image format. Accepted formats: JPEG, PNG, WebP, BMP, GIF."
          )
        );
      };
      img.src = url;
    });
  }

  /**
   * Helper: Draw image to canvas at target dimensions and return RGBA pixel data.
   * @param {HTMLImageElement} img
   * @param {number} w
   * @param {number} h
   * @returns {Uint8Array}
   */
  function drawToPixels(img, w, h) {
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);
    const imageData = ctx.getImageData(0, 0, w, h);
    // Ensure all alpha values are 255
    const data = imageData.data;
    for (let i = 3; i < data.length; i += 4) {
      data[i] = 255;
    }
    return new Uint8Array(data.buffer);
  }

  return {
    /**
     * Load pixel data from raw image file bytes.
     * @param {Uint8Array} fileBytes
     * @returns {Promise<{pixels: Uint8Array, width: number, height: number}>}
     * @throws {GrtmError} ERR_UNSUPPORTED_FORMAT
     */
    async loadPixels(fileBytes) {
      const img = await loadImage(fileBytes);
      const w = img.naturalWidth;
      const h = img.naturalHeight;
      const pixels = drawToPixels(img, w, h);
      return { pixels, width: w, height: h };
    },

    /**
     * Resize image preserving aspect ratio to fit exactly targetW × targetH.
     * @param {Uint8Array} fileBytes
     * @param {number} targetW
     * @param {number} targetH
     * @returns {Promise<Uint8Array>} RGBA pixel data
     */
    async resizeKeepAspect(fileBytes, targetW, targetH) {
      const img = await loadImage(fileBytes);
      return drawToPixels(img, targetW, targetH);
    },

    /**
     * Resize image stretching to exact targetW × targetH (may distort).
     * @param {Uint8Array} fileBytes
     * @param {number} targetW
     * @param {number} targetH
     * @returns {Promise<Uint8Array>} RGBA pixel data
     */
    async resizeStretch(fileBytes, targetW, targetH) {
      const img = await loadImage(fileBytes);
      return drawToPixels(img, targetW, targetH);
    },

    /**
     * Convert RGBA pixels to a PNG Blob with no metadata.
     * @param {Uint8Array} pixels
     * @param {number} width
     * @param {number} height
     * @returns {Promise<Blob>}
     */
    async toBlob(pixels, width, height) {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      const imageData = new ImageData(
        new Uint8ClampedArray(pixels.buffer, pixels.byteOffset, pixels.byteLength),
        width,
        height
      );
      ctx.putImageData(imageData, 0, 0);
      return new Promise((resolve) => {
        canvas.toBlob(resolve, "image/png");
      });
    },

    /**
     * Downscale image if it exceeds maxPixels, preserving aspect ratio.
     * No-op if within limit.
     * @param {Uint8Array} fileBytes
     * @param {number} maxPixels
     * @returns {Promise<{pixels: Uint8Array, width: number, height: number, downscaled: boolean}>}
     */
    async downscaleToLimit(fileBytes, maxPixels) {
      const img = await loadImage(fileBytes);
      let w = img.naturalWidth;
      let h = img.naturalHeight;
      let downscaled = false;

      if (w * h > maxPixels) {
        const scale = Math.sqrt(maxPixels / (w * h));
        w = Math.floor(w * scale);
        h = Math.floor(h * scale);
        downscaled = true;
      }

      const pixels = drawToPixels(img, w, h);
      return { pixels, width: w, height: h, downscaled };
    },
  };
}
