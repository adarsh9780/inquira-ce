import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import styles from './index.module.css';

const productFeatures = [
  {
    title: 'Local-First Intelligence',
    body: 'Zero cloud latency. Zero data leakage. All analysis, code execution, and data storage happen strictly on your hardware.',
  },
  {
    title: 'Integrated Python Runtime',
    body: 'A managed Jupyter kernel built directly into your workspace. Go from raw SQL to interactive Plotly charts with one click.',
  },
  {
    title: 'Agentic LangGraph Logic',
    body: 'Inquira does not just write SQL; it reasons through multi-step cleaning, joins, and analysis tasks until the result is correct.',
  },
];

function HomePageContent(): ReactNode {
  const {siteConfig} = useDocusaurusContext();

  return (
    <main className={styles.page}>
      <section className={styles.heroSection}>
        <div className={styles.heroCopy}>
          <div className={styles.eyebrow}>Local-First AI Workspace</div>
          <h1 className={styles.heroTitle}>Analyze your data at the speed of thought.</h1>
          <p className={styles.heroTagline}>
            The private-by-design desktop app for SQL, Python, and local files.
          </p>
          <p className={styles.heroBody}>
            Inquira CE turns your local databases and spreadsheets into a 
            powerful, agentic workbench. Zero-cloud, zero-latency, and 
            completely free for local analysis.
          </p>
          <div className={styles.ctaActions}>
            <Link className={styles.primaryCta} to="/download">
              Download for Mac/Windows
            </Link>
            <Link className={styles.secondaryCta} to="/docs">
              Get Started
            </Link>
          </div>
        </div>
        <div className={styles.heroLogoContainer}>
          <img
            src="img/inquira-logo-animated.svg"
            alt="Inquira Logo"
            className={styles.heroLogo}
          />
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionIntro}>
          <div className={styles.sectionEyebrow}>Core Capabilities</div>
          <h2 className={styles.sectionTitle}>
            Built for privacy. Optimized for speed.
          </h2>
          <p className={styles.sectionBody}>
            Experience a modern data stack that fits on your machine, not in 
            the cloud. Designed for Analysts, Data Scientists, and Developers 
            who demand full control over their workflows.
          </p>
        </div>
        <div className={styles.cardGrid}>
          {productFeatures.map(feature => (
            <article key={feature.title} className={styles.infoCard}>
              <h3>{feature.title}</h3>
              <p>{feature.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.ctaSection}>
        <div>
          <div className={styles.sectionEyebrow}>Community First</div>
          <h2 className={styles.sectionTitle}>
            Join the local-first movement.
          </h2>
          <p className={styles.sectionBody}>
            Inquira Community Edition is free and open for local use. 
            Download the latest Alpha and start exploring your data today.
          </p>
        </div>
        <div className={styles.ctaActions}>
          <Link className={styles.primaryCta} to="/docs/editions">
            View CE Features
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
