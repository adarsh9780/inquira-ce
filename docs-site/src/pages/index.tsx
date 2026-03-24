import clsx from 'clsx';
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
  return (
    <main className={styles.page}>
      {/* Hero Section */}
      <section className={styles.heroSection}>
        <div className={styles.heroCopy}>
          <div className={styles.eyebrow}>Desktop-First AI Workspace</div>
          <h1 className={styles.heroTitle}>Analyze data at the speed of thought.</h1>
          <p className={styles.heroTagline}>
            The private-by-design workbench for SQL, Python, and local analysis.
          </p>
          <p className={styles.heroBody}>
            Inquira CE turns your local databases and spreadsheets into a 
            powerful, agentic environment. Zero cloud, zero latency, and 
            completely free for local use.
          </p>
          <div className={styles.ctaActions}>
            <Link className={styles.primaryCta} to="/download">
              Download Inquira
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

      {/* Features Grid */}
      <section className={styles.section}>
        <div className={styles.sectionIntro}>
          <div className={styles.sectionEyebrow}>Core Capabilities</div>
          <h2 className={styles.sectionTitle}>
            Built for privacy. Optimized for speed.
          </h2>
          <p className={styles.sectionBody}>
            Experience a modern data stack that fits on your machine.
            Designed for those who demand full control over their data and workflows.
          </p>
        </div>
        <div className={styles.cardGrid}>
          <article className={styles.infoCard}>
            <h3>Local-First Intelligence</h3>
            <p>Zero cloud latency. Zero data leakage. All analysis, code execution, and data storage happen strictly on your hardware.</p>
          </article>
          <article className={styles.infoCard}>
            <h3>Integrated Python Runtime</h3>
            <p>A managed Jupyter kernel built directly into your workspace. Go from raw SQL to interactive Plotly charts with one click.</p>
          </article>
          <article className={styles.infoCard}>
            <h3>Agentic Reasoning</h3>
            <p>Powered by LangGraph to reason through multi-step cleaning, joins, and analysis tasks until the result is exactly what you need.</p>
          </article>
        </div>
      </section>

      {/* CTA Section */}
      <section className={styles.section}>
        <div className={styles.ctaSection}>
          <div className={styles.sectionIntro}>
            <div className={clsx(styles.sectionEyebrow, styles.eyebrowDark)}>Open Source</div>
            <h2 className={styles.sectionTitle}>
              Join the local-first movement.
            </h2>
            <p className={styles.sectionBody}>
              Inquira Community Edition is free and open for local use. 
              Get the latest Alpha and start exploring your data today.
            </p>
          </div>
          <div className={styles.ctaActions}>
            <Link className={styles.primaryCta} to="/download">
              Get Started for Free
            </Link>
            <Link
              className={styles.secondaryCta}
              to="https://github.com/adarsh9780/inquira-ce">
              Star on GitHub
            </Link>
          </div>
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
      description="Inquira documentation, downloads, and the future of private data analysis.">
      <HomePageContent />
    </Layout>
  );
}
