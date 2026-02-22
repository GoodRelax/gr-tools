/**
 * @file matryoshkaPacker.js
 * @description Matryoshka binary frame construction and parsing for all 3 layers (SRS 8.1.4)
 * SRP: Binary frame management for the nested Matryoshka structure.
 */

import { GrtmError } from "./errors.js";
import { lsbDeinterleave } from "./lsbEngine.js";
import { N_LSB } from "./capacityCalc.js";

// ═══════════════════════════════════════════
//  ENCODE FUNCTIONS
// ═══════════════════════════════════════════

/**
 * Construct Layer 3 frame (plaintext payload).
 * Layout: actualLen(4 BE) + nameLen(1) + fileName + compressedTM + zeroPadding
 * Total size = layer3Capacity (pre-computed by encodeUseCase per §4.2.3).
 * Zero padding is statistically indistinguishable from white noise after AES-GCM encryption.
 *
 * @param {Uint8Array} compressedTM   - Compressed Treasure Map
 * @param {string}     fileName       - Original filename
 * @param {number}     layer3Capacity - Frame size = 2×capacityPerCarrier − 62 (§4.2.3)
 * @returns {Uint8Array}
 */
export function packLayer3(compressedTM, fileName, layer3Capacity) {
  const fileNameBytes = new TextEncoder().encode(fileName);
  const nameLen = fileNameBytes.length;
  const actualLen = 1 + nameLen + compressedTM.length; // nameLen(1) + fileName + compressedTM

  // Build frame — size is layer3Capacity (passed directly, ADR-28)
  // Uint8Array initializes to zero; remainder is zero padding (§4.3)
  const frame = new Uint8Array(layer3Capacity);
  const view = new DataView(frame.buffer);

  // actualLen (4 bytes, uint32 BE)
  view.setUint32(0, actualLen);

  // nameLen (1 byte, uint8)
  frame[4] = nameLen;

  // fileName
  frame.set(fileNameBytes, 5);

  // compressedTM
  frame.set(compressedTM, 5 + nameLen);

  return frame;
}

/**
 * Construct Layer 2 frame (encrypted stream).
 * Layout: Key(32) + IV(12) + Ciphertext
 *
 * @param {Uint8Array} key        - AES-256 key (32 bytes)
 * @param {Uint8Array} iv         - Initialization Vector (12 bytes)
 * @param {Uint8Array} ciphertext - Encrypted Layer 3 (includes auth tag)
 * @returns {Uint8Array}
 */
export function packLayer2(key, iv, ciphertext) {
  const out = new Uint8Array(32 + 12 + ciphertext.length);
  out.set(key, 0);
  out.set(iv, 32);
  out.set(ciphertext, 44);
  return out;
}

/**
 * Construct Layer 1 frame (carrier payload).
 * Layout: CarrierID(1) + StripedData
 *
 * @param {Uint8Array} stripedData - Striped portion of encrypted stream
 * @param {boolean}    isEven      - true for Cat (even ID), false for Dog (odd ID)
 * @param {Function}   randGen     - (n) → Uint8Array of n random bytes
 * @returns {Uint8Array}
 */
export function packLayer1(stripedData, isEven, randGen) {
  const out = new Uint8Array(1 + stripedData.length);

  // Generate random byte and force parity
  let idByte = randGen(1)[0];
  if (isEven) {
    idByte = (idByte & 0xfe); // Force even
  } else {
    idByte = (idByte | 0x01); // Force odd
  }
  out[0] = idByte;
  out.set(stripedData, 1);

  return out;
}

// ═══════════════════════════════════════════
//  DECODE FUNCTIONS
// ═══════════════════════════════════════════

/**
 * Read Carrier ID from each image's LSBs and assign Cat (even) / Dog (odd).
 * Only reads the first byte (8 bits → ceil(8/3) = 3 channel slots → 1 pixel's RGB)
 * from each image to determine the Carrier ID.
 *
 * @param {Uint8Array} pixels1         - RGBA pixel data of first image
 * @param {Uint8Array} pixels2         - RGBA pixel data of second image
 * @param {Function}   lsbDeinterleaveFn - lsbDeinterleave function
 * @returns {{ catPixels: Uint8Array, dogPixels: Uint8Array }}
 * @throws {GrtmError} ERR_HEADER_MISMATCH if both IDs have same parity
 */
export function unpackLayer1Id(pixels1, pixels2, lsbDeinterleaveFn) {
  // Extract first byte (8 bits) from each image
  const id1Bytes = lsbDeinterleaveFn(pixels1, 8, N_LSB);
  const id2Bytes = lsbDeinterleaveFn(pixels2, 8, N_LSB);

  const id1 = id1Bytes[0];
  const id2 = id2Bytes[0];

  const id1Even = (id1 % 2) === 0;
  const id2Even = (id2 % 2) === 0;

  if (id1Even === id2Even) {
    throw new GrtmError(
      "ERR_HEADER_MISMATCH",
      "Invalid pairing. Both images must belong to the same encoding session."
    );
  }

  // Cat = even ID, Dog = odd ID
  if (id1Even) {
    return { catPixels: pixels1, dogPixels: pixels2 };
  } else {
    return { catPixels: pixels2, dogPixels: pixels1 };
  }
}

/**
 * Strip the 1-byte Carrier ID prefix from extracted LSB bytes.
 *
 * @param {Uint8Array} lsbBytes - Full LSB byte stream (including ID byte)
 * @returns {Uint8Array} Striped data (without ID byte)
 */
export function unpackLayer1Data(lsbBytes) {
  return lsbBytes.slice(1);
}

/**
 * Unpack Layer 2: extract Key, IV, Ciphertext from encrypted stream.
 * Layout: Key(0..31) + IV(32..43) + Ciphertext(44..)
 *
 * @param {Uint8Array} encryptedStream
 * @returns {{ key: Uint8Array, iv: Uint8Array, ciphertext: Uint8Array }}
 */
export function unpackLayer2(encryptedStream) {
  const key = encryptedStream.slice(0, 32);
  const iv = encryptedStream.slice(32, 44);
  const ciphertext = encryptedStream.slice(44);
  return { key, iv, ciphertext };
}

/**
 * Unpack Layer 3: parse plaintext to extract filename and compressed Treasure Map.
 * Layout: actualLen(4 BE) + nameLen(1) + fileName + compressedTM [+ padding ignored]
 *
 * @param {Uint8Array} plaintext
 * @returns {{ fileName: string, compressedTM: Uint8Array }}
 */
export function unpackLayer3(plaintext) {
  const view = new DataView(plaintext.buffer, plaintext.byteOffset, plaintext.byteLength);

  const actualLen = view.getUint32(0); // uint32 BE
  const nameLen = plaintext[4];

  const fileNameBytes = plaintext.slice(5, 5 + nameLen);
  const fileName = new TextDecoder().decode(fileNameBytes);

  const compressedTMStart = 5 + nameLen;
  const compressedTMEnd = 4 + actualLen; // actualLen = 1 + nameLen + compressedTM.length
  // So compressedTM.length = actualLen - 1 - nameLen
  const compressedTM = plaintext.slice(compressedTMStart, compressedTMEnd);

  return { fileName, compressedTM };
}
