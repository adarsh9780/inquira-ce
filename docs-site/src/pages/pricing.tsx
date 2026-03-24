import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';

import styles from './index.module.css';

const editions = [
  {
    name: 'Free',
    summary: 'Core desktop experience.',
    bullets: [
      'No forced login for basic usage',
      'Single-workspace experience today',
      'Possible support for multiple workspaces later',
    ],
  },
  {
    name: 'Pro',
    summary: 'Free plus advanced knowledge workflows.',
    bullets: [
      'Everything in Free',
      'RAG support',
      'Multiple workspaces',
    ],
  },
  {
    name: 'Enterprise',
    summary: 'Pro plus organizational integration.',
    bullets: [
      'Everything in Pro',
      'Data connectors',
      'MCP support',
    ],
  },
];

export default function PricingPage(): ReactNode {
  return (
    <Layout
      title="Pricing"
      description="Inquira plan structure for Free, Pro, and Enterprise editions.">
      <main className={styles.page}>
        <section className={styles.section}>
          <div className={styles.sectionIntro}>
            <div className={styles.sectionEyebrow}>Pricing</div>
            <h1 className={styles.sectionTitle}>
              Editions for every workload
            </h1>
            <p className={styles.sectionBody}>
              Inquira Community Edition is free forever for local analysis.
              Pro and Enterprise editions provide advanced collaboration and RAG features.
            </p>
          </div>
          <div className={styles.cardGrid}>
            {editions.map(edition => (
              <article key={edition.name} className={styles.infoCard}>
                <div className={styles.eyebrow} style={{ marginBottom: '1rem' }}>{edition.name}</div>
                <p style={{ fontWeight: 600, color: 'var(--ifm-font-color-base)', marginBottom: '1rem' }}>{edition.summary}</p>
                <ul style={{ paddingLeft: '1.25rem', color: 'var(--ifm-font-color-secondary)' }}>
                  {edition.bullets.map(bullet => (
                    <li key={bullet} style={{ marginBottom: '0.5rem' }}>{bullet}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>
        <section className={styles.ctaSection}>
          <div>
            <div className={styles.sectionEyebrow}>Get Started</div>
            <h2 className={styles.sectionTitle}>
              Start with Community Edition
            </h2>
            <p className={styles.sectionBody}>
              Download the latest Alpha release and experience the future of
              local-first data analysis.
            </p>
          </div>
          <div className={styles.ctaActions}>
            <Link className={styles.primaryCta} to="/download">
              View downloads
            </Link>
            <Link className={styles.secondaryCta} to="/docs">
              Read docs
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
