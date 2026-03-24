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
      platform: 'macOS',
      source: 'docs-site-download-page',
      version: 'v1.2.3',
      config: {
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: 'public-anon-key',
      },
      insertSignup,
    });

    expect(result).toEqual({
      ok: true,
      normalizedEmail: 'person@example.com',
      skipped: false,
    });
    expect(insertSignup).toHaveBeenCalledWith({
      email: 'person@example.com',
      platform: 'macOS',
      source: 'docs-site-download-page',
      version: 'v1.2.3',
    });
  });

  it('allows a blank email and skips Supabase entirely', async () => {
    const insertSignup = vi.fn().mockResolvedValue(undefined);

    const result = await submitOptinSignup({
      email: '   ',
      platform: 'Windows',
      source: 'docs-site-download-page',
      version: 'v1.2.3',
      config: {
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: 'public-anon-key',
      },
      insertSignup,
    });

    expect(result).toEqual({
      ok: true,
      normalizedEmail: '',
      skipped: true,
    });
    expect(insertSignup).not.toHaveBeenCalled();
  });

  it('returns a friendly error when Supabase credentials are missing', async () => {
    const result = await submitOptinSignup({
      email: 'person@example.com',
      platform: 'macOS',
      source: 'docs-site-download-page',
      version: 'v1.2.3',
      config: {},
    });

    expect(result).toEqual({
      ok: false,
      message:
        'Optional download signup is not configured yet. Clear the email field to continue without it.',
    });
  });

  it('returns a friendly error when the insert fails', async () => {
    const result = await submitOptinSignup({
      email: 'person@example.com',
      platform: 'Windows',
      source: 'docs-site-download-page',
      version: 'v1.2.3',
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
      'Enter a valid email address, or leave the field blank to skip signup.',
    );
    expect(validateOptinEmail('')).toBeNull();
    expect(validateOptinEmail('person@example.com')).toBeNull();
  });

  it('keeps platform and version metadata per signup event', async () => {
    const insertSignup = vi.fn().mockResolvedValue(undefined);

    await submitOptinSignup({
      email: 'person@example.com',
      platform: 'Windows',
      source: 'docs-site-download-page',
      version: 'v9.9.9',
      config: {
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: 'public-anon-key',
      },
      insertSignup,
    });

    expect(insertSignup).toHaveBeenCalledWith({
      email: 'person@example.com',
      platform: 'Windows',
      source: 'docs-site-download-page',
      version: 'v9.9.9',
    });
  });
});
