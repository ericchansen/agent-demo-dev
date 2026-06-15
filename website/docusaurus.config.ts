import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Fabric Sales Agent Accelerator',
  tagline:
    'A workshop for building AI agents that actually do work — connected to your data, your context, and real tools.',
  favicon: 'img/favicon.ico',
  future: {
    v4: true,
  },
  url: 'https://ericchansen.github.io',
  baseUrl: '/agent-demo-dev/',
  organizationName: 'ericchansen',
  projectName: 'agent-demo-dev',
  onBrokenLinks: 'throw',
  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/ericchansen/agent-demo-dev/edit/main/website/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],
  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Fabric Sales Agent Accelerator',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Workshop',
        },
        {
          href: 'https://github.com/ericchansen/agent-demo-dev',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Workshop',
          items: [
            {
              label: 'Workshop Overview',
              to: '/docs/intro',
            },
            {
              label: 'Start the Journey',
              to: '/docs/journey/from-chat-to-agent',
            },
            {
              label: 'Building Blocks',
              to: '/docs/building-blocks/fabric-data-agent',
            },
            {
              label: 'Architecture',
              to: '/docs/architecture/system-overview',
            },
          ],
        },
        {
          title: 'Resources',
          items: [
            {
              label: 'Setup Guide',
              to: '/docs/workshop/setup',
            },
            {
              label: 'GitHub Repository',
              href: 'https://github.com/ericchansen/agent-demo-dev',
            },
          ],
        },
        {
          title: 'Microsoft Docs',
          items: [
            {
              label: 'Microsoft Fabric',
              href: 'https://learn.microsoft.com/fabric/',
            },
            {
              label: 'Azure AI Foundry',
              href: 'https://learn.microsoft.com/en-us/azure/foundry/',
            },
            {
              label: 'GitHub Copilot CLI',
              href: 'https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers',
            },
            {
              label: 'MCP Specification',
              href: 'https://modelcontextprotocol.io/',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Eric Chansen. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'yaml', 'python'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
