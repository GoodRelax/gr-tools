import { describe, it, expect } from 'vitest';
import { GrtmError } from '../../assets/js/domain/errors.js';

describe('GrtmError', () => {
  it('sets code correctly', () => {
    const err = new GrtmError('ERR_TEST', 'test message');
    expect(err.code).toBe('ERR_TEST');
  });

  it('sets message correctly', () => {
    const err = new GrtmError('ERR_TEST', 'test message');
    expect(err.message).toBe('test message');
  });

  it('is an instance of Error', () => {
    const err = new GrtmError('ERR_TEST', 'test message');
    expect(err).toBeInstanceOf(Error);
  });

  it('is an instance of GrtmError', () => {
    const err = new GrtmError('ERR_TEST', 'test message');
    expect(err).toBeInstanceOf(GrtmError);
  });
});
