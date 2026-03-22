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
              Three editions, one desktop-first product line
            </h1>
            <p className={styles.sectionBody}>
              The Free tier should stay easy to try. Pro and Enterprise build on
              top of that foundation instead of replacing it.
            </p>
          </div>
          <div className={styles.editionGrid}>
            {editions.map(edition => (
              <article key={edition.name} className={styles.editionCard}>
                <div className={styles.editionName}>{edition.name}</div>
                <p className={styles.editionSummary}>{edition.summary}</p>
                <ul>
                  {edition.bullets.map(bullet => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>
        <section className={styles.ctaSection}>
          <div>
            <div className={styles.sectionEyebrow}>Next step</div>
            <h2 className={styles.sectionTitle}>
              Turn this into your public pricing page
            </h2>
            <p className={styles.sectionBody}>
              Replace the roadmap language with final packaging details once
              billing and account flows are ready.
            </p>
          </div>
          <div className={styles.ctaActions}>
            <Link className={styles.primaryCta} to="/download">
              View downloads
            </Link>
            <Link className={styles.secondaryCta} to="/docs/intro">
              Read docs
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
