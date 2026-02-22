import { describe, it, expect } from 'vitest';
import { lsbInterleave, lsbDeinterleave } from '../../assets/js/domain/lsbEngine.js';

describe('lsbInterleave', () => {
  it('does not modify the original carrier (returns a copy)', () => {
    const carrier = new Uint8Array(10 * 4).fill(0x80);
    const original = new Uint8Array(carrier);
    lsbInterleave(carrier, new Uint8Array([0x42]), 3);
    expect(Array.from(carrier)).toEqual(Array.from(original));
  });

  it('alpha channel is never modified', () => {
    const carrier = new Uint8Array(10 * 4).fill(0xFF);
    const stego = lsbInterleave(carrier, new Uint8Array([0xAB, 0xCD]), 3);
    for (let i = 3; i < stego.length; i += 4) {
      expect(stego[i]).toBe(0xFF);
    }
  });

  it('preserves upper (non-LSB) bits of carrier', () => {
    // carrier all 0xFF, payload all 0x00 → upper 5 bits of RGB must stay 0xF8
    const carrier = new Uint8Array(10 * 4).fill(0xFF);
    const stego = lsbInterleave(carrier, new Uint8Array([0x00]), 3);
    for (let px = 0; px < 10; px++) {
      for (let ch = 0; ch < 3; ch++) {
        expect(stego[px * 4 + ch] & 0xF8).toBe(0xF8);
      }
    }
  });
});

describe('lsbInterleave → lsbDeinterleave round-trip (nLsb=3)', () => {
  it('recovers a single byte', () => {
    const carrier = new Uint8Array(4 * 4);
    const payload = new Uint8Array([0x5A]);
    const stego = lsbInterleave(carrier, payload, 3);
    const out = lsbDeinterleave(stego, 8, 3);
    expect(Array.from(out)).toEqual(Array.from(payload));
  });

  it('recovers all-zeros payload', () => {
    const carrier = new Uint8Array(20 * 4).fill(0xFF);
    const payload = new Uint8Array(4).fill(0x00);
    const stego = lsbInterleave(carrier, payload, 3);
    const out = lsbDeinterleave(stego, payload.length * 8, 3);
    expect(Array.from(out)).toEqual(Array.from(payload));
  });

  it('recovers all-ones payload', () => {
    const carrier = new Uint8Array(20 * 4);
    const payload = new Uint8Array(4).fill(0xFF);
    const stego = lsbInterleave(carrier, payload, 3);
    const out = lsbDeinterleave(stego, payload.length * 8, 3);
    expect(Array.from(out)).toEqual(Array.from(payload));
  });

  it('recovers arbitrary multi-byte payload', () => {
    const carrier = new Uint8Array(100 * 4);
    const payload = new Uint8Array([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0]);
    const stego = lsbInterleave(carrier, payload, 3);
    const out = lsbDeinterleave(stego, payload.length * 8, 3);
    expect(Array.from(out)).toEqual(Array.from(payload));
  });

  it('recovers large payload (100 bytes)', () => {
    const carrier = new Uint8Array(1000 * 4);
    const payload = new Uint8Array(100);
    for (let i = 0; i < 100; i++) payload[i] = (i * 13 + 7) % 256;
    const stego = lsbInterleave(carrier, payload, 3);
    const out = lsbDeinterleave(stego, payload.length * 8, 3);
    expect(Array.from(out)).toEqual(Array.from(payload));
  });
});
