/**
 * @file compressorAdapter.js
 * @description Wraps pako.deflate / pako.inflate (SRS 8.3.1)
 * SRP: Compression/decompression adapter.
 */

import { GrtmError } from "../domain/errors.js";

/**
 * Create a CompressorAdapter using the provided pako instance.
 * @param {Object} pako - The pako library object
 * @returns {{ compress: Function, decompress: Function }}
 */
export function createCompressorAdapter(pako) {
  return {
    /**
     * Compress data using zlib (pako.deflate).
     * @param {Uint8Array} data - Data to compress (length > 0)
     * @returns {Uint8Array} Compressed bytes
     */
    compress(data) {
      return pako.deflate(data);
    },

    /**
     * Decompress zlib data (pako.inflate).
     * @param {Uint8Array} data - Compressed data
     * @returns {Uint8Array} Decompressed bytes
     * @throws {GrtmError} ERR_DECOMPRESS if inflation fails
     */
    decompress(data) {
      try {
        return pako.inflate(data);
      } catch (e) {
        throw new GrtmError(
          "ERR_DECOMPRESS",
          "Decompression failed. Data payload may be corrupt."
        );
      }
    },
  };
}
