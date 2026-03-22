import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import styles from './index.module.css';

const editions = [
  {
    name: 'Free',
    summary: 'Desktop app access without forcing users through a login wall.',
    details:
      'Best for single-workspace usage today, with room for future multi-workspace support.',
  },
  {
    name: 'Pro',
    summary: 'Everything in Free, plus RAG and multiple workspaces.',
    details:
      'For teams and power users who need more retrieval context and project separation.',
  },
  {
    name: 'Enterprise',
    summary: 'Everything in Pro, plus data connectors and MCP support.',
    details:
      'Designed for controlled environments, internal systems, and broader integrations.',
  },
];

const productPillars = [
  {
    title: 'Desktop-first by design',
    body: 'The product experience starts on the desktop, not inside a browser tab. The site supports discovery, docs, and downloads without getting in the way.',
  },
  {
    title: 'Docs and downloads in one place',
    body: 'Users can read setup docs, compare plans, and download the latest build from the same domain.',
  },
  {
    title: 'Ready for future accounts',
    body: 'This site gives you a clean public surface now, while leaving room for account and license management later.',
  },
];

function HomePageContent(): ReactNode {
  const {siteConfig} = useDocusaurusContext();

  return (
    <main className={styles.page}>
      <section className={styles.heroSection}>
        <div className={styles.heroCopy}>
          <div className={styles.eyebrow}>Desktop AI workspace</div>
          <h1 className={styles.heroTitle}>{siteConfig.title}</h1>
          <p className={styles.heroTagline}>{siteConfig.tagline}</p>
          <p className={styles.heroBody}>
            Launch a public website for your desktop app without splitting docs,
            pricing, and downloads into separate systems too early.
          </p>
          <div className={styles.ctaActions}>
            <Link className={styles.primaryCta} to="/download">
              View downloads
            </Link>
            <Link className={styles.secondaryCta} to="/docs">
              Read the docs
            </Link>
          </div>
        </div>
        <div className={styles.heroPanel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelDot} />
            <span className={styles.panelLabel}>Inquira release channel</span>
          </div>
          <div className={styles.panelCard}>
            <p className={styles.panelTitle}>Free should feel open</p>
            <p className={styles.panelText}>
              Remove forced login for the base desktop experience. Keep the web
              layer for docs, downloads, and future account management.
            </p>
          </div>
          <div className={styles.panelGrid}>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Docs</span>
              <strong>Guides, setup, roadmap</strong>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Download</span>
              <strong>Latest desktop build</strong>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Future</span>
              <strong>Accounts, billing, workspaces</strong>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionIntro}>
          <div className={styles.sectionEyebrow}>Why this site exists</div>
          <h2 className={styles.sectionTitle}>
            Use the website for the public surface, not the full app shell
          </h2>
          <p className={styles.sectionBody}>
            That split keeps the desktop product simpler today while giving you
            a clean domain for documentation, releases, and future user account
            flows.
          </p>
        </div>
        <div className={styles.cardGrid}>
          {productPillars.map(pillar => (
            <article key={pillar.title} className={styles.infoCard}>
              <h3>{pillar.title}</h3>
              <p>{pillar.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionIntro}>
          <div className={styles.sectionEyebrow}>Plans</div>
          <h2 className={styles.sectionTitle}>
            A pricing structure that matches your roadmap
          </h2>
        </div>
        <div className={styles.editionGrid}>
          {editions.map(edition => (
            <article key={edition.name} className={styles.editionCard}>
              <div className={styles.editionName}>{edition.name}</div>
              <p className={styles.editionSummary}>{edition.summary}</p>
              <p className={styles.editionDetails}>{edition.details}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.ctaSection}>
        <div>
          <div className={styles.sectionEyebrow}>Next steps</div>
          <h2 className={styles.sectionTitle}>
            Ship the site now, plug in the real domain later
          </h2>
          <p className={styles.sectionBody}>
            Before deployment, replace the placeholder production URL in the
            Docusaurus config with your actual domain.
          </p>
        </div>
        <div className={styles.ctaActions}>
          <Link className={styles.primaryCta} to="/pricing">
            Review plans
          </Link>
          <Link
            className={styles.secondaryCta}
            to="https://github.com/adarsh9780/inquira-ce/releases/latest">
            Latest release
          </Link>
        </div>
      </section>
    </main>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();

  return (
    <Layout
      title={`${siteConfig.title} | Desktop AI Workspace`}
      description="Inquira documentation, downloads, pricing, and future account surface for the desktop app.">
      <HomePageContent />
    </Layout>
  );
}
