/**
 * @file decodeUseCase.js
 * @description Decode business flow orchestration (SRS §8.2.2)
 * SRP: Orchestrates the full decode pipeline.
 * Imports only from Domain layer. Adapters injected via deps.
 */

import { lsbDeinterleave } from "../domain/lsbEngine.js";
import { weave } from "../domain/stripingEngine.js";
import {
  unpackLayer1Id,
  unpackLayer1Data,
  unpackLayer2,
  unpackLayer3,
} from "../domain/matryoshkaPacker.js";
import { N_LSB, CHANNELS } from "../domain/capacityCalc.js";
import { GrtmError } from "../domain/errors.js";

/**
 * @param {Object} params
 * @param {Uint8Array} params.file1Raw - First dropped file (raw bytes)
 * @param {Uint8Array} params.file2Raw - Second dropped file (raw bytes)
 * @param {Object}     params.deps     - Injected dependencies
 * @param {Object}     params.deps.imageAdapter  - { loadPixels(Uint8Array) → {pixels, width, height} }
 * @param {Object}     params.deps.cryptoAdapter - { decrypt(ciphertext, key, iv) → Uint8Array }
 * @param {Object}     params.deps.compressor    - { decompress(Uint8Array) → Uint8Array }
 * @returns {Promise<{fileName: string, treasureMapBytes: Uint8Array}>}
 * @throws {GrtmError} ERR_HEADER_MISMATCH, ERR_CRYPTO, ERR_DECOMPRESS
 */
export async function execute({
  file1Raw,
  file2Raw,
  deps: { imageAdapter, cryptoAdapter, compressor },
}) {
  // 1. Load pixel data
  const img1 = await imageAdapter.loadPixels(file1Raw);
  const img2 = await imageAdapter.loadPixels(file2Raw);

  // 2. Identify Cat and Dog by Carrier ID parity (may throw ERR_HEADER_MISMATCH)
  const { catPixels, dogPixels } = unpackLayer1Id(
    img1.pixels,
    img2.pixels,
    lsbDeinterleave,
  );

  // 3. Extract full LSB streams.
  // numBits = floor(pixels.length / 4) × CHANNELS × N_LSB
  // (pixels.length / 4 = pixel count in RGBA; floor guards non-multiple-of-4 edge cases)
  const catTotalBits = Math.floor(catPixels.length / 4) * CHANNELS * N_LSB;
  const dogTotalBits = Math.floor(dogPixels.length / 4) * CHANNELS * N_LSB;
  const catLsbBytes = lsbDeinterleave(catPixels, catTotalBits, N_LSB);
  const dogLsbBytes = lsbDeinterleave(dogPixels, dogTotalBits, N_LSB);

  // 4. Strip Carrier ID prefix
  const catStripedData = unpackLayer1Data(catLsbBytes);
  const dogStripedData = unpackLayer1Data(dogLsbBytes);

  // 5. Weave striped data back together.
  // Result length = 2 × capacityPerCarrier − 2 = exact encryptedStream length (§4.2.3).
  const encryptedStream = weave(catStripedData, dogStripedData);

  // 6. Unpack Layer 2
  const { key, iv, ciphertext } = unpackLayer2(encryptedStream);

  // 7. Decrypt (may throw ERR_CRYPTO)
  const plaintext = await cryptoAdapter.decrypt(ciphertext, key, iv);

  // 8. Unpack Layer 3
  const { fileName, compressedTM } = unpackLayer3(plaintext);

  // 9. Decompress (may throw ERR_DECOMPRESS)
  const treasureMapBytes = compressor.decompress(compressedTM);

  return { fileName, treasureMapBytes };
}
