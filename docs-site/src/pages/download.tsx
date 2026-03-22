import type {ReactNode} from 'react';
import {useEffect, useState} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';

import styles from './index.module.css';

const RELEASE_API =
  'https://api.github.com/repos/adarsh9780/inquira-ce/releases/latest';
const RELEASE_TAG =
  'v0.5.7a10';
const MACOS_ASSET_NAME =
  'Inquira_0.5.7-alpha.10_aarch64.dmg';
const WINDOWS_ASSET_NAME =
  'Inquira_0.5.7-alpha.10_x64-setup.exe';
const MACOS_FALLBACK_URL =
  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a10/Inquira_0.5.7-alpha.10_aarch64.dmg';
const WINDOWS_FALLBACK_URL =
  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a10/Inquira_0.5.7-alpha.10_x64-setup.exe';

type DownloadCard = {
  title: string;
  icon: ReactNode;
  assetName: string;
  fallbackUrl: string;
};

const downloadCards: DownloadCard[] = [
  {
    title: 'macOS',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M16.37 12.44c.02 2.46 2.16 3.28 2.18 3.29-.02.06-.34 1.17-1.12 2.32-.67 1-1.37 2-2.46 2.02-1.07.02-1.42-.64-2.65-.64-1.24 0-1.62.62-2.62.66-1.04.04-1.83-1.05-2.5-2.04-1.37-1.98-2.42-5.59-1.01-8.03.7-1.2 1.95-1.96 3.3-1.98 1.03-.02 2 .69 2.65.69.65 0 1.87-.85 3.16-.73.54.02 2.06.22 3.04 1.66-.08.05-1.82 1.06-1.8 2.78Zm-2.13-5.07c.56-.68.94-1.64.84-2.58-.81.03-1.79.54-2.37 1.22-.52.6-.98 1.57-.86 2.5.91.07 1.83-.46 2.39-1.14Z" />
      </svg>
    ),
    assetName: MACOS_ASSET_NAME,
    fallbackUrl: MACOS_FALLBACK_URL,
  },
  {
    title: 'Windows',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 5.5 10.5 4.4v7.1H3V5.5Zm8.5-1.22L21 3v8.5h-9.5V4.28ZM3 12.5h7.5v7.1L3 18.5v-6Zm8.5 0H21V21l-9.5-1.33V12.5Z" />
      </svg>
    ),
    assetName: WINDOWS_ASSET_NAME,
    fallbackUrl: WINDOWS_FALLBACK_URL,
  },
];

function pickLatestAsset(
  assets: Array<{name?: string; browser_download_url?: string}>,
  assetName: string,
  fallbackUrl: string,
): string {
  const directAsset = assets.find(
    asset => String(asset.name || '') === assetName && !/\.sig$/i.test(String(asset.name || '')),
  );

  return directAsset?.browser_download_url || fallbackUrl;
}

export default function DownloadPage(): ReactNode {
  const [downloadLinks, setDownloadLinks] = useState<Record<string, string>>({
    macOS: MACOS_FALLBACK_URL,
    Windows: WINDOWS_FALLBACK_URL,
  });

  useEffect(() => {
    let active = true;

    async function loadReleaseLinks() {
      try {
        const response = await fetch(RELEASE_API);
        if (!response.ok) {
          throw new Error(`GitHub API returned ${response.status}`);
        }
        const release = await response.json();
        const assets = Array.isArray(release?.assets) ? release.assets : [];

        if (!active) {
          return;
        }

        setDownloadLinks({
          macOS: pickLatestAsset(
            assets,
            downloadCards[0].assetName,
            downloadCards[0].fallbackUrl,
          ),
          Windows: pickLatestAsset(
            assets,
            downloadCards[1].assetName,
            downloadCards[1].fallbackUrl,
          ),
        });
      } catch {
        if (active) {
          setDownloadLinks({
            macOS: MACOS_FALLBACK_URL,
            Windows: WINDOWS_FALLBACK_URL,
          });
        }
      }
    }

    void loadReleaseLinks();

    return () => {
      active = false;
    };
  }, []);

  return (
    <Layout
      title="Download"
      description="Download the latest Inquira desktop build.">
      <main className={styles.page}>
        <section className={styles.section}>
          <div className={styles.sectionIntro}>
            <div className={styles.sectionEyebrow}>Download</div>
            <h1 className={styles.sectionTitle}>
              Latest desktop release, without sending users through GitHub first
            </h1>
            <p className={styles.sectionBody}>
              Click the platform you want and the website resolves the latest
              installer directly from the current GitHub release assets.
            </p>
          </div>
          <div className={styles.downloadGrid}>
            {downloadCards.map(card => (
              <a
                key={card.title}
                className={styles.downloadCard}
                href={downloadLinks[card.title]}
                target="_blank"
                rel="noreferrer">
                <span className={styles.downloadIcon}>{card.icon}</span>
                <span className={styles.downloadLabel}>{card.title}</span>
                <span className={styles.downloadHint}>Direct latest installer</span>
              </a>
            ))}
          </div>
          <div className={styles.cardGrid}>
            <article className={styles.infoCard}>
              <h3>Current delivery model</h3>
              <p>
                The page fetches the latest release metadata and resolves the
                exact Tauri asset names for the current macOS `.dmg` and
                Windows `.exe` installers.
              </p>
            </article>
            <article className={styles.infoCard}>
              <h3>Future delivery model</h3>
              <p>
                Serve platform-aware downloads from your own domain once version
                management matures.
              </p>
            </article>
            <article className={styles.infoCard}>
              <h3>Why this matters</h3>
              <p>
                Users get a cleaner path from your domain to the installer, and
                you keep room for account-based entitlements later.
              </p>
            </article>
          </div>
        </section>
        <section className={styles.ctaSection}>
          <div>
            <div className={styles.sectionEyebrow}>Release source</div>
            <h2 className={styles.sectionTitle}>
              Direct installers first, release page second
            </h2>
            <p className={styles.sectionBody}>
              If asset lookup fails, the buttons fall back to the latest GitHub
              release assets for `{RELEASE_TAG}` instead of breaking.
            </p>
          </div>
          <div className={styles.ctaActions}>
            <Link className={styles.primaryCta} to={downloadLinks.macOS}>
              Download for macOS
            </Link>
            <Link className={styles.secondaryCta} to={downloadLinks.Windows}>
              Download for Windows
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
