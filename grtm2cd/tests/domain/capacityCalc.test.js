import { describe, it, expect } from 'vitest';
import {
  availableBytes,
  selectResolution,
  findMinimumEntry,
} from '../../assets/js/domain/capacityCalc.js';
import { GrtmError } from '../../assets/js/domain/errors.js';

describe('availableBytes', () => {
  it('qVGA (320×240): floor(76800 × 9/8) = 86400', () => {
    expect(availableBytes(240, 320)).toBe(86400);
  });

  it('256sq (256×256): floor(65536 × 9/8) = 73728', () => {
    expect(availableBytes(256, 256)).toBe(73728);
  });

  it('1×1: floor(9/8) = 1', () => {
    expect(availableBytes(1, 1)).toBe(1);
  });

  it('2×1: floor(18/8) = 2', () => {
    expect(availableBytes(1, 2)).toBe(2);
  });
});

describe('selectResolution', () => {
  // 解像度選択ルール(§4.2.3):
  // 1. catのARカテゴリに合う候補を絞る
  // 2. 候補の中で最小ピクセル数を選ぶ(§0.7.3: catサイズ非考慮)

  it('4:3 cat at qVGA size → qVGA (4:3カテゴリ最小)', () => {
    const r = selectResolution(10, 5, 320, 240);
    expect(r.label).toBe('qVGA');
    expect(r.newWidth).toBe(320);
    expect(r.newHeight).toBe(240);
  });

  it('4:3 cat at VGA size → qVGA (catサイズに関係なく最小を選ぶ)', () => {
    const r = selectResolution(10, 5, 640, 480);
    expect(r.label).toBe('qVGA');
    expect(r.newWidth).toBe(320);
    expect(r.newHeight).toBe(240);
  });

  it('4:3 cat at iPhone 12MP size → qVGA (大きいcatでも最小を選ぶ)', () => {
    const r = selectResolution(10, 5, 4032, 3024);
    expect(r.label).toBe('qVGA');
  });

  it('16:9 cat at 360p size → 360p', () => {
    const r = selectResolution(10, 5, 640, 360);
    expect(r.label).toBe('360p');
  });

  it('1:1 cat at 256sq size → 256sq', () => {
    const r = selectResolution(10, 5, 256, 256);
    expect(r.label).toBe('256sq');
  });

  it('portrait 4:3 cat → newWidth < newHeight', () => {
    // 480×640 (縦長) → 4:3カテゴリ、縦横スワップ
    const r = selectResolution(10, 5, 480, 640);
    expect(r.newWidth).toBeLessThan(r.newHeight);
  });

  it('capacityPerCarrier = availableBytes of selected resolution', () => {
    const r = selectResolution(10, 5, 320, 240); // qVGA
    expect(r.capacityPerCarrier).toBe(availableBytes(240, 320));
  });

  it('throws ERR_PAYLOAD_TOO_LARGE when payload exceeds all resolutions', () => {
    let thrown;
    try {
      selectResolution(40_000_000, 1, 100, 100);
    } catch (e) {
      thrown = e;
    }
    expect(thrown).toBeInstanceOf(GrtmError);
    expect(thrown.code).toBe('ERR_PAYLOAD_TOO_LARGE');
  });
});

describe('findMinimumEntry', () => {
  it('returns 256sq for capacity=1 (全17解像度で最小ピクセル数)', () => {
    const entry = findMinimumEntry(1);
    expect(entry.label).toBe('256sq');
  });

  it('256sqの容量(73728)を1超えると qVGA を返す', () => {
    // 256sq: availableBytes(256,256) = 73728 → 足りない
    // qVGA:  availableBytes(240,320) = 86400 → 十分、かつ最小ピクセル数
    const entry = findMinimumEntry(73729);
    expect(entry.label).toBe('qVGA');
  });

  it('returns null when no entry satisfies required capacity', () => {
    const entry = findMinimumEntry(100_000_000);
    expect(entry).toBeNull();
  });

  it('returned entry always satisfies required capacity', () => {
    const required = 50000;
    const entry = findMinimumEntry(required);
    expect(availableBytes(entry.h, entry.w)).toBeGreaterThanOrEqual(required);
  });
});
