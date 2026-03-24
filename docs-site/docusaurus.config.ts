import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

import {resolveDocsSiteSupabaseConfig} from './src/lib/supabaseConfig';

const inquiraTomlPath = path.resolve(__dirname, '..', 'inquira.toml');
const inquiraTomlSource = existsSync(inquiraTomlPath)
  ? readFileSync(inquiraTomlPath, 'utf-8')
  : '';
const publicSupabaseConfig = resolveDocsSiteSupabaseConfig(
  process.env,
  inquiraTomlSource,
);

const config: Config = {
  title: 'Inquira',
  tagline: 'Desktop-first AI workspace for analysis, RAG, and enterprise data access',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://docs.inquiraai.com',
  baseUrl: '/',
  organizationName: 'adarsh9780',
  projectName: 'inquira-ce',
  customFields: {
    supabaseUrl: publicSupabaseConfig.supabaseUrl,
    supabaseAnonKey: publicSupabaseConfig.supabaseAnonKey,
    optinSignupTable:
      process.env.DOCS_SITE_OPTIN_SIGNUP_TABLE ?? 'optin_user_signup',
  },

  onBrokenLinks: 'throw',
  markdown: {
    mermaid: true,
  },
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  themes: [
    '@docusaurus/theme-mermaid',
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        language: ['en'],
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/adarsh9780/inquira-ce/tree/main/docs-site/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/inquira-social-card.png',
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Inquira',
      logo: {
        alt: 'Inquira logo',
        src: 'img/inquira-logo-animated.svg',
      },
      items: [
        {to: '/docs', label: 'Docs', position: 'left'},

        {to: '/download', label: 'Download', position: 'left'},
        {
          href: 'https://github.com/adarsh9780/inquira-ce',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'light',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Overview',
              to: '/docs',
            },
            {
              label: 'Architecture',
              to: '/docs/architecture',
            },
            {
              label: 'Roadmap',
              to: '/docs/roadmap',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/adarsh9780/inquira-ce',
            },
          ],
        },
        {
          title: 'Legal',
          items: [
            {
              label: 'Privacy Policy',
              to: '/docs/privacy-policy',
            },
            {
              label: 'Terms & Conditions',
              to: '/docs/terms-of-service',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Inquira CE (Alpha). Built with Docusaurus.`,
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'neutral'},
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.github,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
