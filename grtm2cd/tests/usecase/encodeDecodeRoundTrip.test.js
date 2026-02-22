import { describe, it, expect, vi } from 'vitest';
import { execute as encodeExecute } from '../../assets/js/usecase/encodeUseCase.js';
import { execute as decodeExecute } from '../../assets/js/usecase/decodeUseCase.js';

// ─────────────────────────────────────────
//  テスト用アダプター
// ─────────────────────────────────────────

// globalThis.crypto を使うことで Node.js 18+ の Web Crypto API を確実に参照する
const testCryptoAdapter = {
  async encrypt(plaintext) {
    const key = globalThis.crypto.getRandomValues(new Uint8Array(32));
    const iv  = globalThis.crypto.getRandomValues(new Uint8Array(12));
    const cryptoKey = await globalThis.crypto.subtle.importKey(
      'raw', key, { name: 'AES-GCM' }, false, ['encrypt'],
    );
    const encrypted = await globalThis.crypto.subtle.encrypt(
      { name: 'AES-GCM', iv }, cryptoKey, plaintext,
    );
    return { key, iv, ciphertext: new Uint8Array(encrypted) };
  },

  async decrypt(ciphertext, key, iv) {
    const cryptoKey = await globalThis.crypto.subtle.importKey(
      'raw', key, { name: 'AES-GCM' }, false, ['decrypt'],
    );
    const decrypted = await globalThis.crypto.subtle.decrypt(
      { name: 'AES-GCM', iv }, cryptoKey, ciphertext,
    );
    return new Uint8Array(decrypted);
  },

  getRandomValues(length) {
    return globalThis.crypto.getRandomValues(new Uint8Array(length));
  },
};

// 圧縮なし(identity)コンプレッサー
const identityCompressor = {
  compress:   (data) => new Uint8Array(data),
  decompress: (data) => new Uint8Array(data),
};

// encode用: resizeStretch が要求サイズのピクセル配列を返す
function makeEncodeImageAdapter() {
  return {
    resizeStretch: vi.fn().mockImplementation(async (_fileBytes, w, h) =>
      new Uint8Array(w * h * 4).fill(0x80),
    ),
  };
}

// ─────────────────────────────────────────
//  Encode → Decode ラウンドトリップ
// ─────────────────────────────────────────
describe('Encode → Decode round-trip', () => {
  it('TMバイト列とファイル名が完全に復元される', async () => {
    const tmBytes  = new Uint8Array([0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x02, 0x03]);
    const fileName = 'treasure.bin';

    const encodeResult = await encodeExecute({
      tmBytes,
      fileName,
      catRaw:    new Uint8Array([0]),
      dogRaw:    new Uint8Array([0]),
      catWidth:  320,
      catHeight: 240, // qVGA 4:3 → qVGA解像度が選ばれる
      deps: {
        compressor:   identityCompressor,
        imageAdapter: makeEncodeImageAdapter(),
        cryptoAdapter: testCryptoAdapter,
      },
    });

    // decode用: loadPixels がエンコード済みピクセルを返す
    const decodeImageAdapter = {
      loadPixels: vi.fn()
        .mockResolvedValueOnce({
          pixels: encodeResult.catStegoPixels,
          width:  encodeResult.width,
          height: encodeResult.height,
        })
        .mockResolvedValueOnce({
          pixels: encodeResult.dogStegoPixels,
          width:  encodeResult.width,
          height: encodeResult.height,
        }),
    };

    const decodeResult = await decodeExecute({
      file1Raw: new Uint8Array([0]),
      file2Raw: new Uint8Array([0]),
      deps: {
        imageAdapter:  decodeImageAdapter,
        cryptoAdapter: testCryptoAdapter,
        compressor:    identityCompressor,
      },
    });

    expect(decodeResult.fileName).toBe(fileName);
    expect(Array.from(decodeResult.treasureMapBytes)).toEqual(Array.from(tmBytes));
  });

  it('ファイル入力順序が逆でも復元される (Cat/Dog自動判定)', async () => {
    const tmBytes  = new Uint8Array([1, 2, 3, 4, 5]);
    const fileName = 'reversed.dat';

    const encodeResult = await encodeExecute({
      tmBytes,
      fileName,
      catRaw:    new Uint8Array([0]),
      dogRaw:    new Uint8Array([0]),
      catWidth:  320,
      catHeight: 240,
      deps: {
        compressor:   identityCompressor,
        imageAdapter: makeEncodeImageAdapter(),
        cryptoAdapter: testCryptoAdapter,
      },
    });

    // Dog を先に、Cat を後に渡す
    const decodeImageAdapter = {
      loadPixels: vi.fn()
        .mockResolvedValueOnce({
          pixels: encodeResult.dogStegoPixels,
          width:  encodeResult.width,
          height: encodeResult.height,
        })
        .mockResolvedValueOnce({
          pixels: encodeResult.catStegoPixels,
          width:  encodeResult.width,
          height: encodeResult.height,
        }),
    };

    const decodeResult = await decodeExecute({
      file1Raw: new Uint8Array([0]),
      file2Raw: new Uint8Array([0]),
      deps: {
        imageAdapter:  decodeImageAdapter,
        cryptoAdapter: testCryptoAdapter,
        compressor:    identityCompressor,
      },
    });

    expect(decodeResult.fileName).toBe(fileName);
    expect(Array.from(decodeResult.treasureMapBytes)).toEqual(Array.from(tmBytes));
  });

  it('UTF-8マルチバイトファイル名が復元される', async () => {
    const tmBytes  = new Uint8Array([10, 20, 30]);
    const fileName = '宝の地図.bin';

    const encodeResult = await encodeExecute({
      tmBytes,
      fileName,
      catRaw:    new Uint8Array([0]),
      dogRaw:    new Uint8Array([0]),
      catWidth:  320,
      catHeight: 240,
      deps: {
        compressor:   identityCompressor,
        imageAdapter: makeEncodeImageAdapter(),
        cryptoAdapter: testCryptoAdapter,
      },
    });

    const decodeImageAdapter = {
      loadPixels: vi.fn()
        .mockResolvedValueOnce({
          pixels: encodeResult.catStegoPixels,
          width:  encodeResult.width,
          height: encodeResult.height,
        })
        .mockResolvedValueOnce({
          pixels: encodeResult.dogStegoPixels,
          width:  encodeResult.width,
          height: encodeResult.height,
        }),
    };

    const decodeResult = await decodeExecute({
      file1Raw: new Uint8Array([0]),
      file2Raw: new Uint8Array([0]),
      deps: {
        imageAdapter:  decodeImageAdapter,
        cryptoAdapter: testCryptoAdapter,
        compressor:    identityCompressor,
      },
    });

    expect(decodeResult.fileName).toBe(fileName);
    expect(Array.from(decodeResult.treasureMapBytes)).toEqual(Array.from(tmBytes));
  });
});

// ─────────────────────────────────────────
//  encodeUseCase エラーハンドリング
// ─────────────────────────────────────────
describe('encodeUseCase error handling', () => {
  const baseArgs = {
    catRaw:    new Uint8Array([0]),
    dogRaw:    new Uint8Array([0]),
    catWidth:  320,
    catHeight: 240,
    deps: {
      compressor:   identityCompressor,
      imageAdapter: makeEncodeImageAdapter(),
      cryptoAdapter: testCryptoAdapter,
    },
  };

  it('throws ERR_EMPTY_PAYLOAD for empty tmBytes', async () => {
    let thrown;
    try {
      await encodeExecute({ ...baseArgs, tmBytes: new Uint8Array(0), fileName: 'x' });
    } catch (e) { thrown = e; }
    expect(thrown.code).toBe('ERR_EMPTY_PAYLOAD');
  });

  it('throws ERR_FILENAME_TOO_LONG for filename > 255 UTF-8 bytes', async () => {
    let thrown;
    try {
      await encodeExecute({ ...baseArgs, tmBytes: new Uint8Array([1]), fileName: 'a'.repeat(256) });
    } catch (e) { thrown = e; }
    expect(thrown.code).toBe('ERR_FILENAME_TOO_LONG');
  });
});
