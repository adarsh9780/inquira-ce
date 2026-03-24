import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {describe, expect, it} from 'vitest';

import {
  isSupabaseSignupConfigured,
  parsePublicSupabaseConfigFromToml,
  resolveDocsSiteSupabaseConfig,
} from './supabaseConfig';

describe('supabaseConfig', () => {
  it('parses the public Supabase settings from inquira.toml content', () => {
    const tomlSource = `
[auth.supabase]
url = "https://example.supabase.co"
publishable_key = "sb_publishable_example"
`;

    expect(parsePublicSupabaseConfigFromToml(tomlSource)).toEqual({
      supabaseUrl: 'https://example.supabase.co',
      supabaseAnonKey: 'sb_publishable_example',
    });
  });

  it('prefers docs-site env vars, then shared env vars, then toml fallback', () => {
    const tomlSource = `
[auth.supabase]
url = "https://toml.supabase.co"
publishable_key = "toml-key"
`;

    expect(
      resolveDocsSiteSupabaseConfig(
        {
          DOCS_SITE_SUPABASE_URL: 'https://docs-env.supabase.co',
          DOCS_SITE_SUPABASE_ANON_KEY: 'docs-env-key',
          SB_INQUIRA_CE_URL: 'https://shared-env.supabase.co',
          SB_INQUIRA_CE_PUBLISHABLE_KEY: 'shared-env-key',
        },
        tomlSource,
      ),
    ).toEqual({
      supabaseUrl: 'https://docs-env.supabase.co',
      supabaseAnonKey: 'docs-env-key',
    });

    expect(
      resolveDocsSiteSupabaseConfig(
        {
          SB_INQUIRA_CE_URL: 'https://shared-env.supabase.co',
          SB_INQUIRA_CE_PUBLISHABLE_KEY: 'shared-env-key',
        },
        tomlSource,
      ),
    ).toEqual({
      supabaseUrl: 'https://shared-env.supabase.co',
      supabaseAnonKey: 'shared-env-key',
    });

    expect(resolveDocsSiteSupabaseConfig({}, tomlSource)).toEqual({
      supabaseUrl: 'https://toml.supabase.co',
      supabaseAnonKey: 'toml-key',
    });
  });

  it('reports whether signup is configured', () => {
    expect(
      isSupabaseSignupConfigured({
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: 'public-key',
      }),
    ).toBe(true);

    expect(
      isSupabaseSignupConfigured({
        supabaseUrl: 'https://example.supabase.co',
        supabaseAnonKey: '',
      }),
    ).toBe(false);
  });

  it('keeps explicit hover text colors in the download page styles', () => {
    const cssSource = readFileSync(
      resolve(process.cwd(), 'src/pages/index.module.css'),
      'utf-8',
    );

    expect(cssSource).toMatch(
      /\.primaryCta:hover,\s*\.primaryCta:focus-visible\s*\{[\s\S]*?color:\s*#ffffff;/,
    );
    expect(cssSource).toMatch(
      /\.secondaryCta:hover,\s*\.secondaryCta:focus-visible\s*\{[\s\S]*?color:\s*#18181b;/,
    );
  });
});
