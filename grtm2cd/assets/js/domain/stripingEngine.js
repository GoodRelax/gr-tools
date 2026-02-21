/**
 * @file stripingEngine.js
 * @description Byte-level array striping and weaving (SRS 8.1.3)
 * SRP: Split/merge byte arrays by alternating index.
 * Pure functions — no side effects.
 */

/**
 * Split data into even-indexed and odd-indexed byte arrays.
 *
 * @param {Uint8Array} data
 * @returns {{ evenBytes: Uint8Array, oddBytes: Uint8Array }}
 */
export function stripe(data) {
  const evenLen = Math.ceil(data.length / 2);
  const oddLen = Math.floor(data.length / 2);
  const evenBytes = new Uint8Array(evenLen);
  const oddBytes = new Uint8Array(oddLen);

  for (let i = 0; i < data.length; i++) {
    if (i % 2 === 0) {
      evenBytes[i >> 1] = data[i];
    } else {
      oddBytes[i >> 1] = data[i];
    }
  }

  return { evenBytes, oddBytes };
}

/**
 * Merge two arrays by alternating bytes: even[0], odd[0], even[1], odd[1], ...
 *
 * @param {Uint8Array} evenBytes
 * @param {Uint8Array} oddBytes
 * @returns {Uint8Array}
 */
export function weave(evenBytes, oddBytes) {
  const totalLen = evenBytes.length + oddBytes.length;
  const out = new Uint8Array(totalLen);

  for (let i = 0; i < evenBytes.length; i++) {
    out[i * 2] = evenBytes[i];
  }
  for (let i = 0; i < oddBytes.length; i++) {
    out[i * 2 + 1] = oddBytes[i];
  }

  return out;
}
