/**
 * @file encodeUseCase.js
 * @description Encode business flow orchestration (SRS §8.2.1)
 * SRP: Orchestrates the full encode pipeline.
 * Imports only from Domain layer. Adapters injected via deps.
 */

import { lsbInterleave } from "../domain/lsbEngine.js";
import { stripe } from "../domain/stripingEngine.js";
import {
  packLayer3,
  packLayer2,
  packLayer1,
} from "../domain/matryoshkaPacker.js";
import {
  selectResolution,
  AES_OVERHEAD_BYTES,
  CARRIER_ID_TOTAL_BYTES,
} from "../domain/capacityCalc.js";
import { GrtmError } from "../domain/errors.js";

/**
 * @param {Object} params
 * @param {Uint8Array} params.tmBytes    - Raw Treasure Map bytes (must be > 0)
 * @param {string}     params.fileName   - Original Treasure Map filename
 * @param {Uint8Array} params.catRaw     - Original Cat Image raw file bytes
 * @param {Uint8Array} params.dogRaw     - Original Dog Image raw file bytes
 * @param {number}     params.catWidth   - Original Cat Image width in pixels (after downscale if applied)
 * @param {number}     params.catHeight  - Original Cat Image height in pixels (after downscale if applied)
 * @param {Object}     params.deps       - Injected dependencies
 * @param {Object}     params.deps.compressor    - { compress(Uint8Array) → Uint8Array }
 * @param {Object}     params.deps.imageAdapter  - { resizeStretch(...) }
 * @param {Object}     params.deps.cryptoAdapter - { encrypt(Uint8Array), getRandomValues(number) }
 * @returns {Promise<{catStegoPixels: Uint8Array, dogStegoPixels: Uint8Array, width: number, height: number, compressedSize: number, label: string}>}
 * @throws {GrtmError} ERR_EMPTY_PAYLOAD, ERR_PAYLOAD_TOO_LARGE, ERR_FILENAME_TOO_LONG
 */
export async function execute({
  tmBytes,
  fileName,
  catRaw,
  dogRaw,
  catWidth,
  catHeight,
  deps: { compressor, imageAdapter, cryptoAdapter },
}) {
  if (tmBytes.length === 0) {
    throw new GrtmError(
      "ERR_EMPTY_PAYLOAD",
      "Treasure Map file is empty. Please select a file with content.",
    );
  }

  const fileNameBytes = new TextEncoder().encode(fileName);
  if (fileNameBytes.length > 255) {
    throw new GrtmError(
      "ERR_FILENAME_TOO_LONG",
      `Filename is too long (${fileNameBytes.length} bytes). Maximum is 255 UTF-8 bytes.`,
    );
  }

  // 1. Compress
  const compressedTM = compressor.compress(tmBytes);

  // 2. Select standard resolution (may throw ERR_PAYLOAD_TOO_LARGE)
  const { newWidth, newHeight, capacityPerCarrier, label } = selectResolution(
    compressedTM.length,
    fileNameBytes.length,
    catWidth,
    catHeight,
  );

  // 3. Stretch both carriers to selected standard resolution (ADR-24)
  const resizedCatPixels = await imageAdapter.resizeStretch(
    catRaw,
    newWidth,
    newHeight,
  );
  const resizedDogPixels = await imageAdapter.resizeStretch(
    dogRaw,
    newWidth,
    newHeight,
  );

  // 4. Layer 3: Pack plaintext with zero padding (§4.3).
  // layer3Capacity fills exactly both carriers to 100% capacity (§4.2.3, ADR-28).
  const layer3Capacity =
    2 * capacityPerCarrier - AES_OVERHEAD_BYTES - CARRIER_ID_TOTAL_BYTES;
  const randGen = cryptoAdapter.getRandomValues;
  const plaintext = packLayer3(compressedTM, fileName, layer3Capacity);

  // 5. Layer 2: AES-256-GCM encryption
  const { key, iv, ciphertext } = await cryptoAdapter.encrypt(plaintext);
  const encryptedStream = packLayer2(key, iv, ciphertext);

  // 6. Layer 1: Stripe and add Carrier IDs
  const { evenBytes, oddBytes } = stripe(encryptedStream);
  const catPayload = packLayer1(evenBytes, true, randGen);
  const dogPayload = packLayer1(oddBytes, false, randGen);

  // 7. LSB embed
  const catStegoPixels = lsbInterleave(resizedCatPixels, catPayload, 3);
  const dogStegoPixels = lsbInterleave(resizedDogPixels, dogPayload, 3);

  return {
    catStegoPixels,
    dogStegoPixels,
    width: newWidth,
    height: newHeight,
    compressedSize: compressedTM.length,
    label,
  };
}
