import { describe, it, expect } from 'vitest';
import {
  packLayer3,
  packLayer2,
  packLayer1,
  unpackLayer1Id,
  unpackLayer1Data,
  unpackLayer2,
  unpackLayer3,
} from '../../assets/js/domain/matryoshkaPacker.js';
import { lsbInterleave, lsbDeinterleave } from '../../assets/js/domain/lsbEngine.js';
import { GrtmError } from '../../assets/js/domain/errors.js';

// --- helpers ---

function readUint32BE(arr, offset = 0) {
  return ((arr[offset] << 24) | (arr[offset + 1] << 16) | (arr[offset + 2] << 8) | arr[offset + 3]) >>> 0;
}

// 決定論的な擬似乱数(randGenモック)
const mockRandGen = (n) => {
  const arr = new Uint8Array(n);
  for (let i = 0; i < n; i++) arr[i] = (i * 37 + 5) % 256;
  return arr;
};

// idByteをLSBに埋め込んだピクセル配列を作る(unpackLayer1Idのテスト用)
function makePixelsWithId(idByte, pixelCount = 4) {
  const pixels = new Uint8Array(pixelCount * 4); // RGBA, all zeros
  return lsbInterleave(pixels, new Uint8Array([idByte]), 3);
}

// ─────────────────────────────────────────
//  packLayer3
// ─────────────────────────────────────────
describe('packLayer3', () => {
  it('output length equals layer3Capacity', () => {
    const frame = packLayer3(new Uint8Array(20), 'file.bin', 100);
    expect(frame.length).toBe(100);
  });

  it('actualLen field (bytes 0-3, uint32 BE) = 1 + nameLen + tmLen', () => {
    const tm = new Uint8Array(20);
    const fileName = 'hello.txt'; // 9 ASCII bytes
    const frame = packLayer3(tm, fileName, 200);
    expect(readUint32BE(frame, 0)).toBe(1 + 9 + 20);
  });

  it('nameLen field (byte 4) = UTF-8 byte length of fileName', () => {
    const frame = packLayer3(new Uint8Array(10), 'abc.txt', 100);
    expect(frame[4]).toBe(7);
  });

  it('fileName bytes are placed at bytes 5 to 5+nameLen', () => {
    const frame = packLayer3(new Uint8Array(5), 'test', 100);
    const expected = Array.from(new TextEncoder().encode('test'));
    expect(Array.from(frame.slice(5, 9))).toEqual(expected);
  });

  it('compressedTM bytes follow fileName', () => {
    const tm = new Uint8Array([10, 20, 30, 40]);
    const fileName = 'f.bin'; // 5 bytes → dataStart = 5+5 = 10
    const frame = packLayer3(tm, fileName, 100);
    expect(Array.from(frame.slice(10, 14))).toEqual([10, 20, 30, 40]);
  });

  it('padding region (after data) is all zeros', () => {
    const tm = new Uint8Array(10);
    const fileName = 'x'; // 1 byte → dataEnd = 5+1+10 = 16
    const frame = packLayer3(tm, fileName, 100);
    expect(frame.slice(16).every(b => b === 0)).toBe(true);
  });

  it('works when data exactly fills layer3Capacity (no padding)', () => {
    // dataEnd = 5 + 1 + tmLen = layer3Capacity → tmLen = cap - 6
    const cap = 50;
    const tm = new Uint8Array(cap - 6);
    const frame = packLayer3(tm, 'a', cap);
    expect(frame.length).toBe(cap);
  });
});

// ─────────────────────────────────────────
//  packLayer3 → unpackLayer3 round-trip
// ─────────────────────────────────────────
describe('packLayer3 → unpackLayer3 round-trip', () => {
  it('recovers fileName and compressedTM (ASCII)', () => {
    const tm = new Uint8Array([0xDE, 0xAD, 0xBE, 0xEF]);
    const fileName = 'secret.dat';
    const frame = packLayer3(tm, fileName, 200);
    const { fileName: gotName, compressedTM: gotTM } = unpackLayer3(frame);
    expect(gotName).toBe(fileName);
    expect(Array.from(gotTM)).toEqual(Array.from(tm));
  });

  it('recovers fileName and compressedTM (UTF-8 multi-byte)', () => {
    const tm = new Uint8Array(10);
    const fileName = '秘密.bin';
    const cap = 5 + new TextEncoder().encode(fileName).length + tm.length + 50;
    const frame = packLayer3(tm, fileName, cap);
    const { fileName: gotName, compressedTM: gotTM } = unpackLayer3(frame);
    expect(gotName).toBe(fileName);
    expect(Array.from(gotTM)).toEqual(Array.from(tm));
  });
});

// ─────────────────────────────────────────
//  packLayer2
// ─────────────────────────────────────────
describe('packLayer2', () => {
  it('output length = 32 + 12 + ciphertext.length', () => {
    const frame = packLayer2(new Uint8Array(32), new Uint8Array(12), new Uint8Array(50));
    expect(frame.length).toBe(94);
  });

  it('key is at bytes 0–31', () => {
    const key = new Uint8Array(32).fill(0x11);
    const frame = packLayer2(key, new Uint8Array(12), new Uint8Array(10));
    expect(Array.from(frame.slice(0, 32))).toEqual(Array.from(key));
  });

  it('iv is at bytes 32–43', () => {
    const iv = new Uint8Array(12).fill(0x22);
    const frame = packLayer2(new Uint8Array(32), iv, new Uint8Array(10));
    expect(Array.from(frame.slice(32, 44))).toEqual(Array.from(iv));
  });

  it('ciphertext starts at byte 44', () => {
    const ct = new Uint8Array([1, 2, 3, 4, 5]);
    const frame = packLayer2(new Uint8Array(32), new Uint8Array(12), ct);
    expect(Array.from(frame.slice(44))).toEqual([1, 2, 3, 4, 5]);
  });
});

// ─────────────────────────────────────────
//  packLayer2 → unpackLayer2 round-trip
// ─────────────────────────────────────────
describe('packLayer2 → unpackLayer2 round-trip', () => {
  it('recovers key, iv, and ciphertext', () => {
    const key = new Uint8Array(32).fill(0xA1);
    const iv = new Uint8Array(12).fill(0xB2);
    const ct = new Uint8Array(100).fill(0xC3);
    const frame = packLayer2(key, iv, ct);
    const { key: k, iv: i, ciphertext: c } = unpackLayer2(frame);
    expect(Array.from(k)).toEqual(Array.from(key));
    expect(Array.from(i)).toEqual(Array.from(iv));
    expect(Array.from(c)).toEqual(Array.from(ct));
  });
});

// ─────────────────────────────────────────
//  packLayer1
// ─────────────────────────────────────────
describe('packLayer1', () => {
  it('output length = 1 + stripedData.length', () => {
    const out = packLayer1(new Uint8Array(50), true, mockRandGen);
    expect(out.length).toBe(51);
  });

  it('isEven=true → carrier ID byte is even (LSB = 0)', () => {
    const out = packLayer1(new Uint8Array(10), true, mockRandGen);
    expect(out[0] % 2).toBe(0);
  });

  it('isEven=false → carrier ID byte is odd (LSB = 1)', () => {
    const out = packLayer1(new Uint8Array(10), false, mockRandGen);
    expect(out[0] % 2).toBe(1);
  });

  it('striped data is placed at bytes 1+', () => {
    const data = new Uint8Array([1, 2, 3, 4]);
    const out = packLayer1(data, true, mockRandGen);
    expect(Array.from(out.slice(1))).toEqual([1, 2, 3, 4]);
  });
});

// ─────────────────────────────────────────
//  unpackLayer1Id
// ─────────────────────────────────────────
describe('unpackLayer1Id', () => {
  it('image1=even → catPixels=image1, dogPixels=image2', () => {
    const evenPixels = makePixelsWithId(0x00); // LSB=0, even
    const oddPixels  = makePixelsWithId(0x01); // LSB=1, odd
    const { catPixels, dogPixels } = unpackLayer1Id(evenPixels, oddPixels, lsbDeinterleave);
    expect(catPixels).toBe(evenPixels);
    expect(dogPixels).toBe(oddPixels);
  });

  it('image1=odd → catPixels=image2, dogPixels=image1 (順序不問)', () => {
    const evenPixels = makePixelsWithId(0x02); // even
    const oddPixels  = makePixelsWithId(0x03); // odd
    const { catPixels, dogPixels } = unpackLayer1Id(oddPixels, evenPixels, lsbDeinterleave);
    expect(catPixels).toBe(evenPixels);
    expect(dogPixels).toBe(oddPixels);
  });

  it('throws ERR_HEADER_MISMATCH when both IDs are even', () => {
    const p1 = makePixelsWithId(0x00);
    const p2 = makePixelsWithId(0x02);
    let thrown;
    try { unpackLayer1Id(p1, p2, lsbDeinterleave); } catch (e) { thrown = e; }
    expect(thrown).toBeInstanceOf(GrtmError);
    expect(thrown.code).toBe('ERR_HEADER_MISMATCH');
  });

  it('throws ERR_HEADER_MISMATCH when both IDs are odd', () => {
    const p1 = makePixelsWithId(0x01);
    const p2 = makePixelsWithId(0x03);
    let thrown;
    try { unpackLayer1Id(p1, p2, lsbDeinterleave); } catch (e) { thrown = e; }
    expect(thrown).toBeInstanceOf(GrtmError);
    expect(thrown.code).toBe('ERR_HEADER_MISMATCH');
  });
});

// ─────────────────────────────────────────
//  unpackLayer1Data
// ─────────────────────────────────────────
describe('unpackLayer1Data', () => {
  it('strips the first byte', () => {
    expect(Array.from(unpackLayer1Data(new Uint8Array([0xFF, 1, 2, 3])))).toEqual([1, 2, 3]);
  });

  it('returns empty array for single-byte input', () => {
    expect(unpackLayer1Data(new Uint8Array([0xFF])).length).toBe(0);
  });
});
