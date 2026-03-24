export type PublicSupabaseConfig = {
  supabaseUrl: string;
  supabaseAnonKey: string;
};

function readEnvValue(env: Record<string, string | undefined>, name: string): string {
  return String(env[name] || '').trim();
}

export function parsePublicSupabaseConfigFromToml(
  tomlSource: string,
): PublicSupabaseConfig {
  let insideSupabaseSection = false;
  let supabaseUrl = '';
  let supabaseAnonKey = '';

  for (const line of tomlSource.split(/\r?\n/)) {
    const trimmedLine = line.trim();

    if (!trimmedLine) {
      continue;
    }

    if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
      insideSupabaseSection = trimmedLine === '[auth.supabase]';
      continue;
    }

    if (!insideSupabaseSection) {
      continue;
    }

    const urlMatch = line.match(/^\s*url\s*=\s*"([^"]*)"/);
    if (urlMatch) {
      supabaseUrl = String(urlMatch[1] || '').trim();
      continue;
    }

    const publishableKeyMatch = line.match(
      /^\s*publishable_key\s*=\s*"([^"]*)"/,
    );
    if (publishableKeyMatch) {
      supabaseAnonKey = String(publishableKeyMatch[1] || '').trim();
    }
  }

  return {
    supabaseUrl,
    supabaseAnonKey,
  };
}

export function resolveDocsSiteSupabaseConfig(
  env: Record<string, string | undefined>,
  tomlSource = '',
): PublicSupabaseConfig {
  const tomlConfig = parsePublicSupabaseConfigFromToml(tomlSource);

  return {
    supabaseUrl:
      readEnvValue(env, 'DOCS_SITE_SUPABASE_URL') ||
      readEnvValue(env, 'SB_INQUIRA_CE_URL') ||
      tomlConfig.supabaseUrl,
    supabaseAnonKey:
      readEnvValue(env, 'DOCS_SITE_SUPABASE_ANON_KEY') ||
      readEnvValue(env, 'SB_INQUIRA_CE_PUBLISHABLE_KEY') ||
      tomlConfig.supabaseAnonKey,
  };
}

export function isSupabaseSignupConfigured(
  config: PublicSupabaseConfig,
): boolean {
  return Boolean(config.supabaseUrl.trim() && config.supabaseAnonKey.trim());
}
