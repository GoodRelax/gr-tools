/**
 * @file errors.js
 * @description Domain error definitions (SRS 8.1.1)
 * SRP: Domain-specific error class and codes.
 */

export class GrtmError extends Error {
  /**
   * @param {string} code - Error code (e.g. 'ERR_EMPTY_PAYLOAD')
   * @param {string} message - Human-readable error message
   */
  constructor(code, message) {
    super(message);
    this.name = "GrtmError";
    this.code = code;
  }
}
