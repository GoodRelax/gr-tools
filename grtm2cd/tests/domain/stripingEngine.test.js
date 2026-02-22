import { describe, it, expect } from 'vitest';
import { stripe, weave } from '../../assets/js/domain/stripingEngine.js';

describe('stripe', () => {
  it('splits even-indexed bytes into evenBytes', () => {
    const data = new Uint8Array([10, 20, 30, 40, 50, 60]);
    const { evenBytes } = stripe(data);
    expect(Array.from(evenBytes)).toEqual([10, 30, 50]);
  });

  it('splits odd-indexed bytes into oddBytes', () => {
    const data = new Uint8Array([10, 20, 30, 40, 50, 60]);
    const { oddBytes } = stripe(data);
    expect(Array.from(oddBytes)).toEqual([20, 40, 60]);
  });

  it('even-length: evenLen === oddLen', () => {
    const { evenBytes, oddBytes } = stripe(new Uint8Array(6));
    expect(evenBytes.length).toBe(3);
    expect(oddBytes.length).toBe(3);
  });

  it('odd-length: evenLen = oddLen + 1', () => {
    const { evenBytes, oddBytes } = stripe(new Uint8Array(5));
    expect(evenBytes.length).toBe(3);
    expect(oddBytes.length).toBe(2);
  });
});

describe('weave', () => {
  it('interleaves evenBytes and oddBytes', () => {
    const result = weave(
      new Uint8Array([10, 30, 50]),
      new Uint8Array([20, 40, 60]),
    );
    expect(Array.from(result)).toEqual([10, 20, 30, 40, 50, 60]);
  });

  it('handles odd total length (evenBytes longer by 1)', () => {
    const result = weave(
      new Uint8Array([1, 3, 5]),
      new Uint8Array([2, 4]),
    );
    expect(Array.from(result)).toEqual([1, 2, 3, 4, 5]);
  });
});

describe('stripe → weave round-trip', () => {
  it('recovers original data (even length)', () => {
    const original = new Uint8Array([0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE]);
    const { evenBytes, oddBytes } = stripe(original);
    expect(Array.from(weave(evenBytes, oddBytes))).toEqual(Array.from(original));
  });

  it('recovers original data (odd length)', () => {
    const original = new Uint8Array([1, 2, 3, 4, 5]);
    const { evenBytes, oddBytes } = stripe(original);
    expect(Array.from(weave(evenBytes, oddBytes))).toEqual(Array.from(original));
  });

  it('recovers original data (large array, 1024 bytes)', () => {
    const original = new Uint8Array(1024);
    for (let i = 0; i < 1024; i++) original[i] = i % 256;
    const { evenBytes, oddBytes } = stripe(original);
    expect(Array.from(weave(evenBytes, oddBytes))).toEqual(Array.from(original));
  });
});
