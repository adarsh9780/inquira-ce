import type {ReactNode} from 'react';
import {useEffect, useState} from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';

import styles from './index.module.css';
import {submitOptinSignup} from '../lib/optinSignup';

const RELEASE_API =
  'https://api.github.com/repos/adarsh9780/inquira-ce/releases/latest';
const RELEASE_TAG =
  'v0.5.7a12';
const MACOS_ASSET_NAME =
  'Inquira_0.5.7-alpha.12_aarch64.dmg';
const WINDOWS_ASSET_NAME =
  'Inquira_0.5.7-alpha.12_x64-setup.exe';
const MACOS_FALLBACK_URL =
  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a12/Inquira_0.5.7-alpha.12_aarch64.dmg';
const WINDOWS_FALLBACK_URL =
  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a12/Inquira_0.5.7-alpha.12_x64-setup.exe';

const MAC_ICON = (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M16.37 12.44c.02 2.46 2.16 3.28 2.18 3.29-.02.06-.34 1.17-1.12 2.32-.67 1-1.37 2-2.46 2.02-1.07.02-1.42-.64-2.65-.64-1.24 0-1.62.62-2.62.66-1.04.04-1.83-1.05-2.5-2.04-1.37-1.98-2.42-5.59-1.01-8.03.7-1.2 1.95-1.96 3.3-1.98 1.03-.02 2 .69 2.65.69.65 0 1.87-.85 3.16-.73.54.02 2.06.22 3.04 1.66-.08.05-1.82 1.06-1.8 2.78Zm-2.13-5.07c.56-.68.94-1.64.84-2.58-.81.03-1.79.54-2.37 1.22-.52.6-.98 1.57-.86 2.5.91.07 1.83-.46 2.39-1.14Z" />
  </svg>
);

const WINDOWS_ICON = (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M3 5.5 10.5 4.4v7.1H3V5.5Zm8.5-1.22L21 3v8.5h-9.5V4.28ZM3 12.5h7.5v7.1L3 18.5v-6Zm8.5 0H21V21l-9.5-1.33V12.5Z" />
  </svg>
);

type DownloadPageConfig = {
  supabaseUrl?: string;
  supabaseAnonKey?: string;
  optinSignupTable?: string;
};

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
  const {siteConfig} = useDocusaurusContext();
  const customFields = (siteConfig.customFields || {}) as DownloadPageConfig;
  const [downloadLinks, setDownloadLinks] = useState<Record<string, string>>({
    macOS: MACOS_FALLBACK_URL,
    Windows: WINDOWS_FALLBACK_URL,
  });
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activePlatform, setActivePlatform] = useState<'macOS' | 'Windows' | null>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusTone, setStatusTone] = useState<'idle' | 'error' | 'success'>(
    'idle',
  );

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
            MACOS_ASSET_NAME,
            MACOS_FALLBACK_URL,
          ),
          Windows: pickLatestAsset(
            assets,
            WINDOWS_ASSET_NAME,
            WINDOWS_FALLBACK_URL,
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

  async function handleDownload(platform: 'macOS' | 'Windows') {
    if (isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setActivePlatform(platform);
    setStatusMessage('');
    setStatusTone('idle');

    const result = await submitOptinSignup({
      email,
      config: {
        supabaseUrl: customFields.supabaseUrl,
        supabaseAnonKey: customFields.supabaseAnonKey,
        tableName: customFields.optinSignupTable,
      },
    });

    if (result.ok === false) {
      setStatusMessage(result.message);
      setStatusTone('error');
      setIsSubmitting(false);
      setActivePlatform(null);
      return;
    }

    setEmail('');
    setStatusMessage(
      result.skipped
        ? `Starting the ${platform} download without email signup.`
        : `Email saved. Starting the ${platform} download.`,
    );
    setStatusTone('success');
    setIsSubmitting(false);
    setActivePlatform(null);

    if (typeof window !== 'undefined') {
      window.location.assign(downloadLinks[platform]);
    }
  }

  return (
    <Layout
      title="Download"
      description="Download the latest Inquira desktop build.">
      <main className={styles.page}>
        <section className={styles.section}>
          <div className={styles.sectionIntro}>
            <div className={styles.sectionEyebrow}>Download</div>
            <h1 className={styles.sectionTitle}>
              Show the same optional signup flow before both desktop downloads
            </h1>
            <p className={styles.sectionBody}>
              Enter an email if you want to opt in before downloading, or leave
              the field blank and continue directly. The same choice now exists
              for both macOS and Windows.
            </p>
          </div>
          <div className={styles.downloadGrid}>
            <a className={styles.downloadCard} href="#download-form">
              <span className={styles.downloadIcon}>{MAC_ICON}</span>
              <span className={styles.downloadLabel}>macOS</span>
              <span className={styles.downloadHint}>
                Optional email before installer download
              </span>
            </a>
            <a className={styles.downloadCard} href="#download-form">
              <span className={styles.downloadIcon}>{WINDOWS_ICON}</span>
              <span className={styles.downloadLabel}>Windows</span>
              <span className={styles.downloadHint}>
                Same optional email flow as macOS
              </span>
            </a>
          </div>
          <div className={styles.cardGrid}>
            <article className={styles.infoCard}>
              <h3>One flow for both platforms</h3>
              <p>
                Both download buttons now sit behind the same optional email
                field, so the page no longer treats Windows and macOS
                differently.
              </p>
            </article>
            <article className={styles.infoCard}>
              <h3>Optional means optional</h3>
              <p>
                If the email field is blank, the page skips Supabase and starts
                the installer immediately for whichever platform the user picks.
              </p>
            </article>
            <article className={styles.infoCard}>
              <h3>Why this fixes the bug</h3>
              <p>
                Before this change, Windows users never even saw the signup
                choice. Now both buttons expose the same lead-capture option.
              </p>
            </article>
          </div>
        </section>
        <section className={styles.ctaSection}>
          <div>
            <div className={styles.sectionEyebrow}>Optional opt-in</div>
            <h2 className={styles.sectionTitle}>
              Add an email if you want, or leave it blank and download directly
            </h2>
            <p className={styles.sectionBody}>
              If you provide an email, the page stores it in the
              `optin_user_signup` table by default. If release lookup fails,
              both download buttons still fall back to the GitHub asset URLs for
              `{RELEASE_TAG}`.
            </p>
          </div>
          <div id="download-form" className={styles.formShell}>
            <label className={styles.formLabel} htmlFor="optin-email">
              Email for product updates (optional)
            </label>
            <div className={styles.formRow}>
              <input
                id="optin-email"
                className={styles.formInput}
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={event => setEmail(event.target.value)}
                disabled={isSubmitting}
              />
            </div>
            <p className={styles.formHint}>
              Leave this blank to skip signup, or fill it in before downloading
              either installer.
            </p>
            <p
              className={clsx(
                styles.formStatus,
                statusTone === 'error' && styles.formStatusError,
                statusTone === 'success' && styles.formStatusSuccess,
              )}
              role="status"
              aria-live="polite">
              {statusMessage}
            </p>
            <div className={styles.ctaActions}>
              <button
                type="button"
                className={clsx(styles.primaryCta, styles.formButton)}
                disabled={isSubmitting}
                onClick={() => void handleDownload('macOS')}>
                {isSubmitting && activePlatform === 'macOS'
                  ? 'Saving...'
                  : 'Download for macOS'}
              </button>
              <button
                type="button"
                className={clsx(styles.secondaryCta, styles.formButton)}
                disabled={isSubmitting}
                onClick={() => void handleDownload('Windows')}>
                {isSubmitting && activePlatform === 'Windows'
                  ? 'Saving...'
                  : 'Download for Windows'}
              </button>
              <Link
                className={styles.secondaryCta}
                to="https://github.com/adarsh9780/inquira-ce/releases/latest">
                Open release page
              </Link>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
