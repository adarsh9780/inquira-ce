import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';

import styles from './index.module.css';

export default function DownloadPage(): ReactNode {
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
              This page is the public download surface. Right now it can point
              to GitHub Releases, and later it can be backed by your own release
              metadata endpoint.
            </p>
          </div>
          <div className={styles.cardGrid}>
            <article className={styles.infoCard}>
              <h3>Current delivery model</h3>
              <p>
                Link to the latest GitHub release while the product is still
                moving quickly.
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
                Users get a cleaner path from marketing site to installer, and
                you keep room for account-based entitlements later.
              </p>
            </article>
          </div>
        </section>
        <section className={styles.ctaSection}>
          <div>
            <div className={styles.sectionEyebrow}>Release source</div>
            <h2 className={styles.sectionTitle}>Use GitHub Releases for now</h2>
            <p className={styles.sectionBody}>
              Swap this link with your own release API once the site owns the
              full download flow.
            </p>
          </div>
          <div className={styles.ctaActions}>
            <Link
              className={styles.primaryCta}
              to="https://github.com/adarsh9780/inquira-ce/releases/latest">
              Open latest release
            </Link>
            <Link className={styles.secondaryCta} to="/pricing">
              Compare plans
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
