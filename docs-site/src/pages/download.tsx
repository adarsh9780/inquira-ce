import type {ReactNode} from 'react';
import {useEffect, useState} from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';

import styles from './index.module.css';
import {submitOptinSignup} from '../lib/optinSignup';
import {isSupabaseSignupConfigured} from '../lib/supabaseConfig';

const RELEASE_API =
  'https://api.github.com/repos/adarsh9780/inquira-ce/releases/latest';
const RELEASE_TAG =
  'v0.5.7a18';
const MACOS_ASSET_NAME =
  'Inquira_0.5.7-alpha.18_aarch64.dmg';
const WINDOWS_ASSET_NAME =
  'Inquira_0.5.7-alpha.18_x64-setup.exe';
const MACOS_FALLBACK_URL =
  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a18/Inquira_0.5.7-alpha.18_aarch64.dmg';
const WINDOWS_FALLBACK_URL =
  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.7a18/Inquira_0.5.7-alpha.18_x64-setup.exe';
const DOWNLOAD_SOURCE = 'docs-site-download-page';

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

type DownloadPlatform = 'macOS' | 'Windows';

type DownloadTarget = {
  url: string;
  version: string;
};

function pickLatestAsset(
  assets: Array<{name?: string; browser_download_url?: string}>,
  assetName: string,
  fallbackUrl: string,
  releaseVersion: string,
  fallbackVersion: string,
): DownloadTarget {
  const directAsset = assets.find(
    asset => String(asset.name || '') === assetName && !/\.sig$/i.test(String(asset.name || '')),
  );

  if (directAsset?.browser_download_url) {
    return {
      url: directAsset.browser_download_url,
      version: releaseVersion,
    };
  }

  return {
    url: fallbackUrl,
    version: fallbackVersion,
  };
}

export default function DownloadPage(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  const customFields = (siteConfig.customFields || {}) as DownloadPageConfig;
  const signupConfig = {
    supabaseUrl: customFields.supabaseUrl || '',
    supabaseAnonKey: customFields.supabaseAnonKey || '',
  };
  const signupConfigured = isSupabaseSignupConfigured(signupConfig);
  const [downloadTargets, setDownloadTargets] = useState<Record<DownloadPlatform, DownloadTarget>>({
    macOS: {
      url: MACOS_FALLBACK_URL,
      version: RELEASE_TAG,
    },
    Windows: {
      url: WINDOWS_FALLBACK_URL,
      version: RELEASE_TAG,
    },
  });
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activePlatform, setActivePlatform] = useState<DownloadPlatform | null>(null);
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
        const releaseVersion =
          typeof release?.tag_name === 'string' && release.tag_name.trim()
            ? release.tag_name.trim()
            : RELEASE_TAG;

        if (!active) {
          return;
        }

        setDownloadTargets({
          macOS: pickLatestAsset(
            assets,
            MACOS_ASSET_NAME,
            MACOS_FALLBACK_URL,
            releaseVersion,
            RELEASE_TAG,
          ),
          Windows: pickLatestAsset(
            assets,
            WINDOWS_ASSET_NAME,
            WINDOWS_FALLBACK_URL,
            releaseVersion,
            RELEASE_TAG,
          ),
        });
      } catch {
        if (active) {
          setDownloadTargets({
            macOS: {
              url: MACOS_FALLBACK_URL,
              version: RELEASE_TAG,
            },
            Windows: {
              url: WINDOWS_FALLBACK_URL,
              version: RELEASE_TAG,
            },
          });
        }
      }
    }

    void loadReleaseLinks();

    return () => {
      active = false;
    };
  }, []);

  async function handleDownload(platform: DownloadPlatform) {
    if (isSubmitting) {
      return;
    }

    const selectedTarget = downloadTargets[platform];

    setIsSubmitting(true);
    setActivePlatform(platform);
    setStatusMessage('');
    setStatusTone('idle');

    if (!signupConfigured) {
      setStatusMessage(`Starting the ${platform} download.`);
      setStatusTone('success');
      setIsSubmitting(false);
      setActivePlatform(null);

      if (typeof window !== 'undefined') {
        window.location.assign(selectedTarget.url);
      }
      return;
    }

    const result = await submitOptinSignup({
      email,
      platform,
      source: DOWNLOAD_SOURCE,
      version: selectedTarget.version,
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
      window.location.assign(selectedTarget.url);
    }
  }

  return (
    <Layout
      title="Download"
      description="Download the latest Inquira desktop build.">
      <main className={styles.page}>
        <section className={styles.section}>
          <div className={styles.sectionIntro}>
            <div className={styles.sectionEyebrow}>Get Inquira</div>
            <h1 className={styles.sectionTitle}>
              Download the desktop workspace
            </h1>
            <p className={styles.sectionBody}>
              {signupConfigured
                ? 'Choose your platform to start the download. You can optionally provide your email to receive product updates and early access to new features.'
                : 'Direct downloads are available for macOS and Windows. Experience the full power of a local-first AI workspace today.'}
            </p>
          </div>
          <div className={styles.downloadGrid}>
            <a className={styles.downloadCard} href="#download-form">
              <span className={styles.downloadIcon}>{MAC_ICON}</span>
              <span className={styles.downloadLabel}>macOS (Apple Silicon)</span>
              <span className={styles.downloadHint}>
                Standard DMG installer
              </span>
            </a>
            <a className={styles.downloadCard} href="#download-form">
              <span className={styles.downloadIcon}>{WINDOWS_ICON}</span>
              <span className={styles.downloadLabel}>Windows</span>
              <span className={styles.downloadHint}>
                Standard Setup EXE
              </span>
            </a>
          </div>
          <div className={styles.cardGrid}>
            <article className={styles.infoCard}>
              <h3>Private by Design</h3>
              <p>
                Inquira runs entirely on your hardware. Your data, queries, and
                conversations never leave your machine.
              </p>
            </article>
            <article className={styles.infoCard}>
              <h3>Zero Cloud Latency</h3>
              <p>
                By processing everything locally, Inquira provides near-instant
                responses for analysis and data manipulation.
              </p>
            </article>
            <article className={styles.infoCard}>
              <h3>Full System Control</h3>
              <p>
                Leverage your local Python environment and databases with 
                direct, native speed.
              </p>
            </article>
          </div>
        </section>
        <section className={styles.ctaSection}>
          <div>
            <div className={clsx(styles.sectionEyebrow, styles.eyebrowDark)}>Stay Updated</div>
            <h2 className={styles.sectionTitle}>
              Optional product updates
            </h2>
            <p className={styles.sectionBody}>
              {signupConfigured
                ? 'Provide your email if you want to stay in the loop with the latest releases and community features.'
                : 'Email updates are currently being transitioned. Follow our GitHub for the latest release notes and project news.'}
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
                placeholder={
                  signupConfigured
                    ? 'you@company.com'
                    : 'Signup unavailable on this site'
                }
                value={email}
                onChange={event => setEmail(event.target.value)}
                disabled={isSubmitting || !signupConfigured}
              />
            </div>
            <p className={styles.formHint}>
              {signupConfigured
                ? 'Leave this blank to skip signup, or fill it in before downloading either installer.'
                : 'This input is disabled until Supabase public signup settings are configured for the docs site.'}
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
