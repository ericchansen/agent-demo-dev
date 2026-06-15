import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

type JourneyStep = {
  emoji: string;
  title: string;
  description: string;
  link: string;
};

const JourneySteps: JourneyStep[] = [
  {
    emoji: '💬',
    title: 'From Chat to Agent',
    description:
      'Why agents that just talk aren\'t enough. What it takes to build one that actually does work alongside you.',
    link: '/docs/journey/from-chat-to-agent',
  },
  {
    emoji: '🗄️',
    title: 'Ground It in Data',
    description:
      'Connect a Fabric Data Agent to a Lakehouse. Your agent answers questions about real business data, not training data.',
    link: '/docs/journey/ground-it-in-data',
  },
  {
    emoji: '📬',
    title: 'Give It Context',
    description:
      'Connect WorkIQ for M365 activity signals. The agent knows your emails, meetings, and engagement — its answers become personal.',
    link: '/docs/journey/give-it-context',
  },
  {
    emoji: '🔧',
    title: 'Arm It with Tools',
    description:
      'Connect tools that produce real output — reports, forecasts, documents uploaded to OneDrive. The agent delivers, not just answers.',
    link: '/docs/journey/arm-it-with-tools',
  },
  {
    emoji: '🔁',
    title: 'Build Reusable Skills',
    description:
      'Compose data, context, and tools into repeatable workflows. Skills are shareable, versionable, and composable.',
    link: '/docs/journey/build-reusable-skills',
  },
  {
    emoji: '🚀',
    title: 'Ship It',
    description:
      'Deploy to where users work. CLI for developers. Foundry → M365 Copilot + Teams for business users. Same backend, different reach.',
    link: '/docs/journey/ship-it',
  },
];

type BlockInfo = {
  emoji: string;
  title: string;
  link: string;
};

const BuildingBlocks: BlockInfo[] = [
  {emoji: '🔀', title: 'Choose Your Data Platform', link: '/docs/building-blocks/choose-data-platform'},
  {emoji: '📊', title: 'Fabric Data Agent', link: '/docs/building-blocks/fabric-data-agent'},
  {emoji: '🧱', title: 'Databricks Genie', link: '/docs/building-blocks/databricks-genie'},
  {emoji: '📬', title: 'WorkIQ', link: '/docs/building-blocks/workiq'},
  {emoji: '🔌', title: 'MCP', link: '/docs/building-blocks/mcp'},
  {emoji: '🏭', title: 'Azure AI Foundry', link: '/docs/building-blocks/foundry'},
  {emoji: '⚡', title: 'Skills', link: '/docs/building-blocks/skills'},
  {emoji: '📄', title: 'Report Generation', link: '/docs/building-blocks/report-generation'},
  {emoji: '🗃️', title: 'WWI Dataset', link: '/docs/building-blocks/wwi-dataset'},
];

function JourneyCard({emoji, title, description, link}: JourneyStep) {
  return (
    <Link to={link} className={clsx(styles.journeyCard)}>
      <div className={styles.journeyEmoji}>{emoji}</div>
      <div>
        <Heading as="h3" className={styles.journeyTitle}>{title}</Heading>
        <p className={styles.journeyDescription}>{description}</p>
      </div>
    </Link>
  );
}

function BlockChip({emoji, title, link}: BlockInfo) {
  return (
    <Link to={link} className={styles.blockChip}>
      <span>{emoji}</span> {title}
    </Link>
  );
}

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();

  return (
    <header className={clsx('hero', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className={clsx('hero__subtitle', styles.heroSubtitle)}>
          {siteConfig.tagline}
        </p>
        <p className={styles.heroContext}>
          Built on Microsoft Fabric or Databricks, MCP, Azure AI Foundry, and the Wide World
          Importers sample dataset. Prototype in GitHub Copilot CLI. Deploy to M365 Copilot + Teams.
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--primary button--lg"
            to="/docs/intro">
            Start the Workshop
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/docs/workshop/setup">
            Setup Guide
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="Workshop"
      description="A workshop for building AI agents that actually do work — connected to your data, your context, and real tools.">
      <HomepageHeader />
      <main>
        <section className={styles.journeySection}>
          <div className="container">
            <Heading as="h2" className={styles.sectionTitle}>The Journey</Heading>
            <p className={styles.sectionSubtitle}>
              A two-day hands-on path: Day 1 grounds the agent in data and produces the first
              report; Day 2 ships the same workflow through Foundry, M365 Copilot, skills, and monitoring.
            </p>
            <div className={styles.journeyGrid}>
              {JourneySteps.map((step, idx) => (
                <JourneyCard key={idx} {...step} />
              ))}
            </div>
          </div>
        </section>

        <section className={styles.blocksSection}>
          <div className="container">
            <Heading as="h2" className={styles.sectionTitle}>Building Blocks</Heading>
            <p className={styles.sectionSubtitle}>
              Reference docs for each component — what it is, how it fits, and links to Microsoft docs.
            </p>
            <div className={styles.blocksGrid}>
              {BuildingBlocks.map((block, idx) => (
                <BlockChip key={idx} {...block} />
              ))}
            </div>
          </div>
        </section>

        <section className={styles.linksSection}>
          <div className="container">
            <div className={styles.linksGrid}>
              <Link to="/docs/architecture/system-overview" className={styles.linkCard}>
                <Heading as="h3">🏗️ Architecture</Heading>
                <p>System diagrams, auth patterns, and how the two surfaces connect.</p>
              </Link>
              <Link to="/docs/workshop/facilitator-guide" className={styles.linkCard}>
                <Heading as="h3">🛠️ Workshop Guide</Heading>
                <p>Facilitator pacing, setup prerequisites, demo scripts, and cost model.</p>
              </Link>
              <a href="https://github.com/ericchansen/agent-demo-dev" className={styles.linkCard}>
                <Heading as="h3">📦 Repository</Heading>
                <p>Source code, MCP servers, Foundry orchestrator, Bicep IaC, and tests.</p>
              </a>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
