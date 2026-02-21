/**
 * @file cryptoAdapter.js
 * @description Wraps Web Crypto API (SRS 8.3.3)
 * SRP: AES-256-GCM encryption/decryption and CSPRNG.
 */

import { GrtmError } from "../domain/errors.js";

/**
 * Create a CryptoAdapter.
 * @returns {{ encrypt: Function, decrypt: Function, getRandomValues: Function }}
 */
export function createCryptoAdapter() {
  return {
    /**
     * Encrypt plaintext with a one-time AES-256-GCM key.
     * @param {Uint8Array} plaintext
     * @returns {Promise<{key: Uint8Array, iv: Uint8Array, ciphertext: Uint8Array}>}
     *   ciphertext includes the 16-byte Auth Tag appended by Web Crypto.
     */
    async encrypt(plaintext) {
      const key = crypto.getRandomValues(new Uint8Array(32));
      const iv = crypto.getRandomValues(new Uint8Array(12));

      const cryptoKey = await crypto.subtle.importKey(
        "raw",
        key,
        { name: "AES-GCM" },
        false,
        ["encrypt"]
      );

      const encrypted = await crypto.subtle.encrypt(
        { name: "AES-GCM", iv },
        cryptoKey,
        plaintext
      );

      return {
        key,
        iv,
        ciphertext: new Uint8Array(encrypted),
      };
    },

    /**
     * Decrypt AES-256-GCM ciphertext.
     * @param {Uint8Array} ciphertext - Includes 16-byte Auth Tag
     * @param {Uint8Array} key        - 32-byte AES key
     * @param {Uint8Array} iv         - 12-byte IV
     * @returns {Promise<Uint8Array>} Decrypted plaintext
     * @throws {GrtmError} ERR_CRYPTO if auth tag validation fails
     */
    async decrypt(ciphertext, key, iv) {
      try {
        const cryptoKey = await crypto.subtle.importKey(
          "raw",
          key,
          { name: "AES-GCM" },
          false,
          ["decrypt"]
        );

        const decrypted = await crypto.subtle.decrypt(
          { name: "AES-GCM", iv },
          cryptoKey,
          ciphertext
        );

        return new Uint8Array(decrypted);
      } catch (e) {
        throw new GrtmError(
          "ERR_CRYPTO",
          "Decryption failed. Ensure both images are from the same encoding session and have not been modified or re-compressed."
        );
      }
    },

    /**
     * Generate cryptographically secure random bytes.
     * @param {number} length
     * @returns {Uint8Array}
     */
    getRandomValues(length) {
      return crypto.getRandomValues(new Uint8Array(length));
    },
  };
}
