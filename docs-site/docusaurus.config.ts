import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Inquira',
  tagline: 'Desktop-first AI workspace for analysis, RAG, and enterprise data access',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://inquira.example.com',
  baseUrl: '/',
  organizationName: 'adarsh9780',
  projectName: 'inquira-ce',

  onBrokenLinks: 'throw',
  markdown: {
    mermaid: true,
  },
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  themes: ['@docusaurus/theme-mermaid'],

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
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Inquira',
      logo: {
        alt: 'Inquira logo',
        src: 'img/inquira-icon.png',
      },
      items: [
        {to: '/docs', label: 'Docs', position: 'left'},
        {to: '/pricing', label: 'Pricing', position: 'left'},
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
          title: 'Product',
          items: [
            {
              label: 'Overview',
              to: '/docs',
            },
            {
              label: 'Pricing',
              to: '/pricing',
            },
            {
              label: 'Download',
              to: '/download',
            },
          ],
        },
        {
          title: 'Resources',
          items: [
            {
              label: 'Architecture Notes',
              to: '/docs/architecture',
            },
            {
              label: 'Download Strategy',
              href: 'https://github.com/adarsh9780/inquira-ce/releases/latest',
            },
          ],
        },
        {
          title: 'Company',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/adarsh9780/inquira-ce',
            },
            {
              label: 'Future Accounts',
              to: '/docs/auth-strategy',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Inquira. Built with Docusaurus.`,
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
