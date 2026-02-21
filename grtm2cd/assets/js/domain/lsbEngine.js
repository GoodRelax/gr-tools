/**
 * @file lsbEngine.js
 * @description Bit-level LSB manipulation (SRS 8.1.2)
 * SRP: Embed/extract data in the least significant bits of RGBA pixel arrays.
 * Pure functions — no side effects, no DOM, no Browser API.
 *
 * Pixel layout: [R, G, B, A, R, G, B, A, ...]
 * Only R, G, B channels are used. Alpha is always skipped.
 */

/**
 * Embed payload bytes into the LSBs of carrier RGBA pixel data.
 *
 * @param {Uint8Array} carrier  - RGBA pixel data (4 bytes/pixel)
 * @param {Uint8Array} payload  - Bytes to embed
 * @param {number}     nLsb    - Number of LSBs to use per channel (e.g. 3)
 * @returns {Uint8Array} New RGBA array with payload embedded in R,G,B LSBs
 */
export function lsbInterleave(carrier, payload, nLsb) {
  const out = new Uint8Array(carrier);
  const mask = (0xff >> nLsb) << nLsb; // e.g. nLsb=3 → 0b11111000
  const totalBits = payload.length * 8;

  let bitIndex = 0;
  const pixelCount = carrier.length / 4;

  for (let px = 0; px < pixelCount && bitIndex < totalBits; px++) {
    const base = px * 4;
    for (let ch = 0; ch < 3 && bitIndex < totalBits; ch++) {
      // Extract nLsb bits from payload at current bitIndex
      let val = 0;
      for (let b = nLsb - 1; b >= 0; b--) {
        const byteIdx = Math.floor(bitIndex / 8);
        const bitOff = 7 - (bitIndex % 8);
        const bit = (payload[byteIdx] >> bitOff) & 1;
        val |= bit << b;
        bitIndex++;
        if (bitIndex >= totalBits) {
          // Remaining bits in this channel slot stay 0
          break;
        }
      }
      out[base + ch] = (out[base + ch] & mask) | val;
    }
  }

  return out;
}

/**
 * Extract bytes from the LSBs of stego RGBA pixel data.
 *
 * @param {Uint8Array} stego   - RGBA pixel data with embedded LSB data
 * @param {number}     numBits - Total number of bits to extract
 * @param {number}     nLsb    - Number of LSBs used per channel
 * @returns {Uint8Array} Extracted bytes
 */
export function lsbDeinterleave(stego, numBits, nLsb) {
  const totalBytes = Math.ceil(numBits / 8);
  const out = new Uint8Array(totalBytes);

  let bitIndex = 0;
  const pixelCount = stego.length / 4;

  for (let px = 0; px < pixelCount && bitIndex < numBits; px++) {
    const base = px * 4;
    for (let ch = 0; ch < 3 && bitIndex < numBits; ch++) {
      const channelVal = stego[base + ch];
      for (let b = nLsb - 1; b >= 0; b--) {
        if (bitIndex >= numBits) break;
        const bit = (channelVal >> b) & 1;
        const byteIdx = Math.floor(bitIndex / 8);
        const bitOff = 7 - (bitIndex % 8);
        out[byteIdx] |= bit << bitOff;
        bitIndex++;
      }
    }
  }

  return out;
}
