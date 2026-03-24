import {createClient} from '@supabase/supabase-js';

export const DEFAULT_OPTIN_SIGNUP_TABLE = 'optin_user_signup';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type OptinSignupConfig = {
  supabaseUrl?: string;
  supabaseAnonKey?: string;
  tableName?: string;
};

export type OptinSignupResult =
  | {
      ok: true;
      normalizedEmail: string;
    }
  | {
      ok: false;
      message: string;
    };

type InsertOptinSignup = (email: string) => Promise<void>;

export function normalizeOptinEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function validateOptinEmail(email: string): string | null {
  if (!email) {
    return 'Enter your email before starting the macOS download.';
  }

  if (!EMAIL_PATTERN.test(email)) {
    return 'Enter a valid email address.';
  }

  return null;
}

export function resolveOptinSignupTableName(tableName?: string): string {
  const normalizedTableName = tableName?.trim();

  return normalizedTableName || DEFAULT_OPTIN_SIGNUP_TABLE;
}

export function createOptinSignupInserter(
  config: OptinSignupConfig,
): InsertOptinSignup | null {
  if (!config.supabaseUrl || !config.supabaseAnonKey) {
    return null;
  }

  const supabase = createClient(config.supabaseUrl, config.supabaseAnonKey);
  const tableName = resolveOptinSignupTableName(config.tableName);

  return async (email: string) => {
    const {error} = await supabase.from(tableName).insert({email});

    if (error) {
      throw error;
    }
  };
}

export async function submitOptinSignup({
  email,
  config,
  insertSignup,
}: {
  email: string;
  config: OptinSignupConfig;
  insertSignup?: InsertOptinSignup;
}): Promise<OptinSignupResult> {
  const normalizedEmail = normalizeOptinEmail(email);
  const validationError = validateOptinEmail(normalizedEmail);

  if (validationError) {
    return {
      ok: false,
      message: validationError,
    };
  }

  const activeInserter = insertSignup ?? createOptinSignupInserter(config);

  if (!activeInserter) {
    return {
      ok: false,
      message:
        'Mac download signups are not configured yet. Please try again later.',
    };
  }

  try {
    await activeInserter(normalizedEmail);
  } catch {
    return {
      ok: false,
      message: 'We could not save your email right now. Please try again.',
    };
  }

  return {
    ok: true,
    normalizedEmail,
  };
}
