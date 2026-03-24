import {describe, expect, it, vi} from 'vitest';

import {
  DEFAULT_OPTIN_SIGNUP_TABLE,
  normalizeOptinEmail,
  resolveOptinSignupTableName,
  submitOptinSignup,
  validateOptinEmail,
} from './optinSignup';

describe('optinSignup', () => {
  it('normalizes email values before validation and insert', async () => {
    const insertSignup = vi.fn().mockResolvedValue(undefined);

    const result = await submitOptinSignup({
      email: '  Person@Example.COM ',
      config: {
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: 'public-anon-key',
      },
      insertSignup,
    });

    expect(result).toEqual({
      ok: true,
      normalizedEmail: 'person@example.com',
    });
    expect(insertSignup).toHaveBeenCalledWith('person@example.com');
  });

  it('rejects an empty email before trying Supabase', async () => {
    const insertSignup = vi.fn().mockResolvedValue(undefined);

    const result = await submitOptinSignup({
      email: '   ',
      config: {
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: 'public-anon-key',
      },
      insertSignup,
    });

    expect(result).toEqual({
      ok: false,
      message: 'Enter your email before starting the macOS download.',
    });
    expect(insertSignup).not.toHaveBeenCalled();
  });

  it('returns a friendly error when Supabase credentials are missing', async () => {
    const result = await submitOptinSignup({
      email: 'person@example.com',
      config: {},
    });

    expect(result).toEqual({
      ok: false,
      message:
        'Mac download signups are not configured yet. Please try again later.',
    });
  });

  it('returns a friendly error when the insert fails', async () => {
    const result = await submitOptinSignup({
      email: 'person@example.com',
      config: {
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: 'public-anon-key',
      },
      insertSignup: vi.fn().mockRejectedValue(new Error('boom')),
    });

    expect(result).toEqual({
      ok: false,
      message: 'We could not save your email right now. Please try again.',
    });
  });

  it('falls back to the default signup table name', () => {
    expect(resolveOptinSignupTableName()).toBe(DEFAULT_OPTIN_SIGNUP_TABLE);
    expect(resolveOptinSignupTableName('')).toBe(DEFAULT_OPTIN_SIGNUP_TABLE);
    expect(resolveOptinSignupTableName('custom_signup_table')).toBe(
      'custom_signup_table',
    );
  });

  it('validates email addresses consistently', () => {
    expect(normalizeOptinEmail('  Person@Example.COM ')).toBe(
      'person@example.com',
    );
    expect(validateOptinEmail('invalid-email')).toBe(
      'Enter a valid email address.',
    );
    expect(validateOptinEmail('person@example.com')).toBeNull();
  });
});
